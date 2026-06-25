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
        """Return names of vision-capable models available in this Ollama instance."""
        import ollama
        client = ollama.Client(host=self._host)
        try:
            models = client.list()
            return [m.model for m in models.models]
        except Exception:
            return []
