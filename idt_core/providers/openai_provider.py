"""
OpenAI provider (GPT-4o, GPT-4o-mini, o1).
Reads OPENAI_API_KEY from the environment.
"""
from __future__ import annotations

import base64
from typing import Optional

from .base import BaseProvider, DescriptionResult

DEFAULT_MODEL = "gpt-4o"

OPENAI_MODELS = [
    "gpt-5.2", "gpt-5.1", "gpt-5", "gpt-5-mini", "gpt-5-nano",
    "o4-mini", "o3", "o1",
    "gpt-4o", "gpt-4o-mini",
    "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano",
]

OPENAI_MODEL_METADATA: dict = {
    "gpt-5.2": {"name": "GPT-5.2", "description": "Best available model.", "cost": "$$$$", "supports_vision": True, "recommended": False},
    "gpt-5.1": {"name": "GPT-5.1", "description": "High-quality GPT-5 with strong reasoning.", "cost": "$$$", "supports_vision": True, "recommended": False},
    "gpt-5": {"name": "GPT-5", "description": "Flagship GPT-5 reasoning model.", "cost": "$$$", "supports_vision": True, "recommended": False},
    "gpt-5-mini": {"name": "GPT-5 Mini", "description": "Faster, efficient GPT-5.", "cost": "$$", "supports_vision": True, "recommended": False},
    "gpt-5-nano": {"name": "GPT-5 Nano", "description": "Fastest GPT-5.", "cost": "$", "supports_vision": True, "recommended": False},
    "o4-mini": {"name": "O4 Mini", "description": "Fast cost-efficient reasoning.", "cost": "$$", "supports_vision": True, "recommended": False},
    "o3": {"name": "O3", "description": "Powerful reasoning for complex tasks.", "cost": "$$$", "supports_vision": True, "recommended": False},
    "o1": {"name": "O1", "description": "Original full reasoning model.", "cost": "$$$", "supports_vision": True, "recommended": False},
    "gpt-4o": {"name": "GPT-4o", "description": "Fast, intelligent, flexible — best for most tasks.", "cost": "$$", "supports_vision": True, "recommended": True},
    "gpt-4o-mini": {"name": "GPT-4o Mini", "description": "Affordable and fast.", "cost": "$", "supports_vision": True, "recommended": False},
    "gpt-4.1": {"name": "GPT-4.1", "description": "Latest non-reasoning GPT-4.1.", "cost": "$$", "supports_vision": True, "recommended": False},
    "gpt-4.1-mini": {"name": "GPT-4.1 Mini", "description": "Compact GPT-4.1.", "cost": "$", "supports_vision": True, "recommended": False},
    "gpt-4.1-nano": {"name": "GPT-4.1 Nano", "description": "Ultra-budget GPT-4.1.", "cost": "$", "supports_vision": True, "recommended": False},
}


def get_openai_model_info(model_id: str) -> dict:
    return OPENAI_MODEL_METADATA.get(model_id, {"name": model_id, "supports_vision": True})


# Alias kept for import compatibility
DEV_OPENAI_MODELS = OPENAI_MODELS


class OpenAIProvider(BaseProvider):
    def __init__(self, model: str = DEFAULT_MODEL, api_key: Optional[str] = None):
        try:
            from openai import OpenAI  # noqa: F401
        except ImportError:
            raise ImportError(
                "openai package is required: pip install openai"
            )
        from openai import OpenAI
        self._model = model
        # api_key=None → SDK reads OPENAI_API_KEY from environment
        self._client = OpenAI(api_key=api_key)

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model

    def describe(self, image_bytes: bytes, mime_type: str, prompt: str) -> DescriptionResult:
        b64 = base64.standard_b64encode(image_bytes).decode("ascii")
        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{b64}"},
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )
        usage = response.usage
        return DescriptionResult(
            text=response.choices[0].message.content,
            model=self._model,
            provider="openai",
            input_tokens=usage.prompt_tokens if usage else None,
            output_tokens=usage.completion_tokens if usage else None,
        )
