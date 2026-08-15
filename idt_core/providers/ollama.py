"""
Ollama provider — local models (llava, qwen2-vl, llama3.2-vision, etc.)
Connects to a running Ollama instance; default host is localhost:11434.
"""
from __future__ import annotations

import base64
import os
import time
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

# (host, model) -> the /api/show payload, or None when the probe failed.
#
# ONE cache for one endpoint. Capabilities, context length and vision all come
# from the same /api/show response, so probing them separately meant a single
# chat turn issued two or three round trips for the same model before the first
# token. Keyed by host as well as name: the same model name on a local and a
# remote server is not the same model, and a cached answer from one must never
# be served for the other.
_SHOW_CACHE: dict[tuple[str, str], Optional[dict]] = {}

# Failures are cached too, but only briefly. Not caching them at all meant an
# unreachable daemon was re-probed on every single turn, each attempt waiting
# out its own timeout; caching them forever would mean Ollama starting up later
# in the session was never noticed. A short TTL gets both.
_NEGATIVE_TTL_SECONDS = 30.0
_NEGATIVE_AT: dict[tuple[str, str], float] = {}


def _resolve_host(host: Optional[str]) -> str:
    """The Ollama base URL to talk to.

    ``None`` means "whatever the SDK would use", i.e. ``OLLAMA_HOST`` when it is
    set. Passing an explicit host and letting the raw-REST fallback default to
    localhost is what made remote-Ollama users silently fall back to a 32k
    context window while their chat turns went to the real server.
    """
    resolved = (host or os.environ.get("OLLAMA_HOST") or DEFAULT_HOST).strip()
    if not resolved.startswith(("http://", "https://")):
        resolved = f"http://{resolved}"
    return resolved.rstrip("/")


def _show(name: str, host: Optional[str] = None, client=None) -> Optional[dict]:
    """The /api/show payload for ``name``, as a plain dict, or None.

    Tries the SDK first, then raw REST, because the ``ollama`` package drops
    ``model_info`` entirely in some released versions. Results are cached per
    (host, model); failures are cached for ``_NEGATIVE_TTL_SECONDS``.
    """
    resolved = _resolve_host(host)
    key = (resolved, name)
    if key in _SHOW_CACHE:
        payload = _SHOW_CACHE[key]
        if payload is not None:
            return payload
        if time.monotonic() - _NEGATIVE_AT.get(key, 0.0) < _NEGATIVE_TTL_SECONDS:
            return None
        # TTL expired — fall through and probe again.

    own_client = client is None
    info = None
    try:
        if client is None:
            import ollama
            client = ollama.Client(host=resolved)
        info = client.show(name)
    except Exception:
        info = None

    def _field(key_name):
        if info is None:
            return None
        value = getattr(info, key_name, None)
        if value is None and isinstance(info, dict):
            value = info.get(key_name)
        return value

    payload = {
        "model_info": _field("model_info"),
        "parameters": _field("parameters"),
        "capabilities": _field("capabilities"),
    }

    # The SDK drops `model_info` entirely in some released versions while still
    # returning `capabilities`, so the trigger is that specific field being
    # absent — not the whole response being empty. Getting this wrong means
    # context discovery silently returns None on exactly the servers the REST
    # fallback was written for. An injected client is a test double or a shared
    # listing client, so only a client we made talks to the real server.
    if own_client and payload["model_info"] is None:
        try:
            raw = _show_via_rest(name, resolved)
            for field in ("model_info", "parameters", "capabilities"):
                if payload[field] is None:
                    payload[field] = raw.get(field)
        except Exception:
            pass

    if not any(v is not None for v in payload.values()):
        _SHOW_CACHE[key] = None
        _NEGATIVE_AT[key] = time.monotonic()
        return None

    _SHOW_CACHE[key] = payload
    _NEGATIVE_AT.pop(key, None)
    return payload


def model_capabilities(name: str, host: Optional[str] = None, client=None) -> Optional[list]:
    """Lowercased capability list from /api/show, or None when unavailable.

    Current servers report from {completion, vision, tools, thinking, insert,
    embedding}; older ones report nothing, in which case callers must decide
    their own fail-open/fail-closed policy — that is why this returns None
    instead of [].
    """
    payload = _show(name, host=host, client=client)
    if payload is None:
        return None
    caps = payload.get("capabilities")
    if caps is None:
        return None
    return [str(c).lower() for c in caps]


def model_is_chat_capable(name: str, host: Optional[str] = None, client=None) -> bool:
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


def model_context_length(name: str, host: Optional[str] = None, client=None) -> Optional[int]:
    """Context length Ollama reports for a model, or None when unavailable.

    Reads /api/show. Newer servers expose ``model_info`` with an
    architecture-prefixed key (``llama.context_length``); older ones only
    mention ``num_ctx`` in the ``parameters`` string. Both are tried, in that
    order. Shared by the chat token budgeter and ImageDescriber's token gauge
    so there is one implementation of this parsing.
    """
    payload = _show(name, host=host, client=client)
    if payload is None:
        return None
    size = _parse_context_length(payload.get("model_info"), payload.get("parameters"))
    return size if size > 0 else None


def model_has_vision(name: str, host: Optional[str] = None, client=None) -> bool:
    """True when Ollama reports `vision` among the model's capabilities.

    Fails OPEN: if the capability query itself errors we return True and keep the
    model. Only a *successful* query that omits `vision` excludes it — a transient
    API problem must never silently hide a working model from the picker.
    """
    caps = model_capabilities(name, host=host, client=client)
    if caps is None:
        return True                          # unreachable/silent — do not exclude
    return "vision" in caps


class OllamaProvider(BaseProvider):
    def __init__(self, model: str = DEFAULT_MODEL, host: Optional[str] = None):
        try:
            import ollama  # noqa: F401
        except ImportError:
            raise ImportError(
                "ollama package is required: pip install ollama"
            )
        self._model = model
        # None means "let the SDK decide", which is how OLLAMA_HOST reaches us.
        # Hardcoding localhost here sent every capability/context probe to the
        # local daemon while the chat turns themselves went to the real server.
        self._host = host.rstrip("/") if host else None

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
