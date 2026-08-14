"""
OpenAI provider (GPT-4o, GPT-4o-mini, o1).
Reads OPENAI_API_KEY from the environment.
"""
from __future__ import annotations

import base64
from typing import Optional

from .base import BaseProvider, DescriptionResult

# Model list sourced from the OpenAI Python SDK model definitions.
# Only vision-capable models are included (IDT describes images).
# Updated July 2026.
DEFAULT_MODEL = "gpt-5.2"

OPENAI_MODELS = [
    # Current generation — GPT-5.x
    "gpt-5.2", "gpt-5.1", "gpt-5", "gpt-5-mini", "gpt-5-nano",
    # Reasoning models
    "o4-mini", "o3",
    # Legacy (still functional, users may have old descriptions referencing them)
    "gpt-4o", "gpt-4o-mini",
    "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano",
    "o1",
]

# context_window / max_output are the platform-documented figures. They feed
# the chat token budgeter and the context gauge; before they were recorded,
# registry.model_limits() returned (None, None) for every OpenAI model and
# budgeting fell back to a flat 128k guess regardless of model.
OPENAI_MODEL_METADATA: dict = {
    # --- GPT-5.x --- (400k context, 128k max output across the family)
    "gpt-5.2": {"name": "GPT-5.2", "description": "Best available model — highest quality vision and reasoning.", "cost": "$$$$", "supports_vision": True, "recommended": True,
                "context_window": 400_000, "max_output": 128_000},
    "gpt-5.1": {"name": "GPT-5.1", "description": "High-quality GPT-5 with strong reasoning.", "cost": "$$$", "supports_vision": True, "recommended": False,
                "context_window": 400_000, "max_output": 128_000},
    "gpt-5": {"name": "GPT-5", "description": "Flagship GPT-5 reasoning model.", "cost": "$$$", "supports_vision": True, "recommended": False,
              "context_window": 400_000, "max_output": 128_000},
    "gpt-5-mini": {"name": "GPT-5 Mini", "description": "Faster, efficient GPT-5.", "cost": "$$", "supports_vision": True, "recommended": False,
                   "context_window": 400_000, "max_output": 128_000},
    "gpt-5-nano": {"name": "GPT-5 Nano", "description": "Fastest and most affordable GPT-5.", "cost": "$", "supports_vision": True, "recommended": False,
                   "context_window": 400_000, "max_output": 128_000},
    # --- Reasoning models ---
    "o4-mini": {"name": "O4 Mini", "description": "Fast cost-efficient reasoning.", "cost": "$$", "supports_vision": True, "recommended": False,
                "context_window": 200_000, "max_output": 100_000},
    "o3": {"name": "O3", "description": "Powerful reasoning for complex tasks.", "cost": "$$$", "supports_vision": True, "recommended": False,
           "context_window": 200_000, "max_output": 100_000},
    # --- Legacy (still functional) ---
    "gpt-4o": {"name": "GPT-4o", "description": "Legacy — still works well for vision tasks.", "cost": "$$", "supports_vision": True, "recommended": False,
               "context_window": 128_000, "max_output": 16_384},
    "gpt-4o-mini": {"name": "GPT-4o Mini", "description": "Legacy — affordable and fast.", "cost": "$", "supports_vision": True, "recommended": False,
                    "context_window": 128_000, "max_output": 16_384},
    "gpt-4.1": {"name": "GPT-4.1", "description": "Legacy — last non-reasoning GPT-4 generation.", "cost": "$$", "supports_vision": True, "recommended": False,
                "context_window": 1_047_576, "max_output": 32_768},
    "gpt-4.1-mini": {"name": "GPT-4.1 Mini", "description": "Legacy — compact GPT-4.1.", "cost": "$", "supports_vision": True, "recommended": False,
                     "context_window": 1_047_576, "max_output": 32_768},
    "gpt-4.1-nano": {"name": "GPT-4.1 Nano", "description": "Legacy — ultra-budget GPT-4.1.", "cost": "$", "supports_vision": True, "recommended": False,
                     "context_window": 1_047_576, "max_output": 32_768},
    "o1": {"name": "O1", "description": "Legacy — original full reasoning model.", "cost": "$$$", "supports_vision": True, "recommended": False,
           "context_window": 200_000, "max_output": 100_000},
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
