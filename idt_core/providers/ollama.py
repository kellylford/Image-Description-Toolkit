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
