"""
Ollama provider — local models (llava, qwen2-vl, llama3.2-vision, etc.)
Connects to a running Ollama instance; default host is localhost:11434.
"""
from __future__ import annotations

import base64
from typing import Optional

from .base import BaseProvider, DescriptionResult

try:
    from idt_core.config import DEFAULT_OLLAMA_MODEL as DEFAULT_MODEL  # dev
except ImportError:
    try:
        from config import DEFAULT_OLLAMA_MODEL as DEFAULT_MODEL        # frozen
    except ImportError:
        DEFAULT_MODEL = "llama3.2-vision"                               # fallback
DEFAULT_HOST = "http://localhost:11434"

# model name -> True/False, or absent when we could not determine it.
# /api/show is one request per model and pickers list ~20, so cache per process.
_VISION_CACHE: dict[str, bool] = {}

# model name -> context length in tokens. Successful lookups only; a failed
# probe is retried next call because Ollama may simply not be running yet.
_CONTEXT_CACHE: dict[str, int] = {}

# model name -> lowercased capability list from /api/show. Successful lookups
# only, same reasoning as _CONTEXT_CACHE.
_CAPS_CACHE: dict[str, list] = {}


def model_capabilities(name: str, host: str = DEFAULT_HOST, client=None) -> Optional[list]:
    """Lowercased capability list from /api/show, or None when unavailable.

    Current servers report from {completion, vision, tools, thinking, insert,
    embedding}; older ones report nothing, in which case callers must decide
    their own fail-open/fail-closed policy — that is why this returns None
    instead of [].
    """
    if name in _CAPS_CACHE:
        return _CAPS_CACHE[name]
    try:
        if client is None:
            import ollama
            client = ollama.Client(host=host.rstrip("/"))
        info = client.show(name)
        caps = getattr(info, "capabilities", None)
        if caps is None and isinstance(info, dict):
            caps = info.get("capabilities")
    except Exception:
        return None
    if caps is None:
        return None
    result = [str(c).lower() for c in caps]
    _CAPS_CACHE[name] = result
    return result


def model_is_chat_capable(name: str, host: str = DEFAULT_HOST, client=None) -> bool:
    """True when the model can hold a conversation (`completion` capability).

    Fails OPEN like :func:`model_has_vision`, and for the same reason: a
    transient probe failure must never hide a working model from a picker.
    Excludes embedding-only models, which /api/tags lists but /api/chat
    rejects.
    """
    caps = model_capabilities(name, host=host, client=client)
    if caps is None:
        return True
    return "completion" in caps


def _parse_context_length(model_info, parameters) -> int:
    """Context length out of a /api/show response's fields, or 0."""
    for key, val in (model_info or {}).items():
        lowered = str(key).lower()
        if "context_length" in lowered or "context_window" in lowered:
            try:
                return int(val)
            except (TypeError, ValueError):
                continue
    for line in (parameters or "").splitlines():
        parts = line.strip().lower().split()
        if len(parts) >= 2 and parts[0] == "num_ctx":
            try:
                return int(parts[1])
            except ValueError:
                return 0
    return 0


def _show_via_rest(name: str, host: str) -> dict:
    """Raw POST /api/show. The ``ollama`` Python package's ``show()`` drops
    ``model_info`` entirely in some released versions, so when the SDK comes
    back empty this asks the server directly."""
    import json
    import urllib.request

    request = urllib.request.Request(
        f"{host.rstrip('/')}/api/show",
        data=json.dumps({"model": name}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def model_context_length(name: str, host: str = DEFAULT_HOST, client=None) -> Optional[int]:
    """Context length Ollama reports for a model, or None when unavailable.

    Reads /api/show. Newer servers expose ``model_info`` with an
    architecture-prefixed key (``llama.context_length``); older ones only
    mention ``num_ctx`` in the ``parameters`` string. Both are tried, in that
    order, first through the SDK and then over raw REST (see
    :func:`_show_via_rest`). Shared by the chat token budgeter and
    ImageDescriber's token gauge so there is one implementation of this
    parsing.
    """
    if name in _CONTEXT_CACHE:
        return _CONTEXT_CACHE[name]

    own_client = client is None
    try:
        if client is None:
            import ollama
            client = ollama.Client(host=host.rstrip("/"))
        info = client.show(name)
    except Exception:
        return None

    def _field(key):
        value = getattr(info, key, None)
        if value is None and isinstance(info, dict):
            value = info.get(key)
        return value

    size = _parse_context_length(_field("model_info"), _field("parameters"))

    if size <= 0 and own_client:
        # An injected client is a test double or a shared listing client;
        # only fall back to raw REST when we are talking to a real server.
        try:
            raw = _show_via_rest(name, host)
            size = _parse_context_length(
                raw.get("model_info"), raw.get("parameters")
            )
        except Exception:
            size = 0

    if size <= 0:
        return None
    _CONTEXT_CACHE[name] = size
    return size


def model_has_vision(name: str, host: str = DEFAULT_HOST, client=None) -> bool:
    """True when Ollama reports `vision` among the model's capabilities.

    Fails OPEN: if the capability query itself errors we return True and keep the
    model. Only a *successful* query that omits `vision` excludes it — a transient
    API problem must never silently hide a working model from the picker.
    """
    if name in _VISION_CACHE:
        return _VISION_CACHE[name]

    try:
        if client is None:
            import ollama
            client = ollama.Client(host=host.rstrip("/"))
        info = client.show(name)
        caps = getattr(info, "capabilities", None)
        if caps is None and isinstance(info, dict):
            caps = info.get("capabilities")
        if caps is None:
            return True                      # nothing reported — do not exclude
        result = "vision" in [str(c).lower() for c in caps]
    except Exception:
        return True                          # unreachable — do not exclude

    _VISION_CACHE[name] = result
    return result


class OllamaProvider(BaseProvider):
    def __init__(self, model: str = DEFAULT_MODEL, host: str = DEFAULT_HOST):
        try:
            import ollama  # noqa: F401
        except ImportError:
            raise ImportError(
                "ollama package is required: pip install ollama"
            )
        self._model = model
        self._host = host.rstrip("/")

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return self._model

    def describe(self, image_bytes: bytes, mime_type: str, prompt: str) -> DescriptionResult:
        import ollama

        b64 = base64.standard_b64encode(image_bytes).decode("ascii")
        client = ollama.Client(host=self._host)
        response = client.chat(
            model=self._model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                    "images": [b64],
                }
            ],
        )
        return DescriptionResult(
            text=response.message.content,
            model=self._model,
            provider="ollama",
            input_tokens=getattr(response, "prompt_eval_count", None),
            output_tokens=getattr(response, "eval_count", None),
        )

    def list_models(self) -> list[str]:
        """Return names of vision-capable models available in this Ollama instance.

        Models without vision must not be offered for description. Ollama accepts
        an attached image for them and silently discards it, so the model writes a
        confident description from the prompt alone — a photo of boats at a dock
        came back as "a woman standing next to a white Porsche 911" (issue #227).
        Fluent, wrong, and nothing signals it.
        """
        import ollama
        client = ollama.Client(host=self._host)
        try:
            models = client.list()
        except Exception:
            return []

        out: list[str] = []
        for m in models.models:
            if model_has_vision(m.model, host=self._host, client=client):
                out.append(m.model)
        return out

    def list_chat_models(self) -> list[str]:
        """Names of chat-capable models — the picker filter for *chat*, where
        text-only models are often the strongest ones installed.

        The vision filter in :meth:`list_models` exists so describe never
        hands an image to a model that would silently discard it (issue #227);
        applying it to the chat picker hid every text-only model for no
        reason. Chat needs `completion`, nothing more.
        """
        import ollama
        client = ollama.Client(host=self._host)
        try:
            models = client.list()
        except Exception:
            return []

        return [
            m.model
            for m in models.models
            if model_is_chat_capable(m.model, host=self._host, client=client)
        ]
