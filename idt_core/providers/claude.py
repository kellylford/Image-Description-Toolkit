"""
Anthropic Claude provider.
Reads ANTHROPIC_API_KEY from the environment (standard SDK behavior).
"""
from __future__ import annotations

import base64
from typing import Optional

from .base import BaseProvider, DescriptionResult

# Model list sourced from the Anthropic SDK (anthropic.types.model).
# All Claude models support vision natively. Updated July 2026.
CLAUDE_MODELS = [
    # Current generation — 5.x
    "claude-opus-5",
    "claude-sonnet-5",
    "claude-fable-5",
    "claude-mythos-5",
    "claude-mythos-preview",
    # Current generation — 4.x (still supported)
    "claude-opus-4-8",
    "claude-opus-4-7",
    "claude-opus-4-6",
    "claude-sonnet-4-6",
    "claude-haiku-4-5-20251001",
    # Legacy (still in SDK, users may have old descriptions referencing them)
    "claude-opus-4-5-20251101",
    "claude-sonnet-4-5-20250929",
    "claude-opus-4-1-20250805",
]

DEFAULT_MODEL = "claude-opus-4-8"

CLAUDE_MODEL_METADATA: dict = {
    # --- Generation 5 ---
    "claude-opus-5": {
        "name": "Claude Opus 5",
        "description": "Flagship — highest intelligence and description depth",
        "generation": "5.0", "context_window": 200000, "max_output": 128000,
        "supports_vision": True, "cost": "$$$$", "recommended": True,
    },
    "claude-sonnet-5": {
        "name": "Claude Sonnet 5",
        "description": "Best balance of speed and intelligence",
        "generation": "5.0", "context_window": 200000, "max_output": 64000,
        "supports_vision": True, "cost": "$$$", "recommended": True,
    },
    "claude-fable-5": {
        "name": "Claude Fable 5",
        "description": "Creative model with strong visual storytelling",
        "generation": "5.0", "context_window": 200000, "max_output": 64000,
        "supports_vision": True, "cost": "$$", "recommended": False,
    },
    "claude-mythos-5": {
        "name": "Claude Mythos 5",
        "description": "Specialized model for complex visual analysis",
        "generation": "5.0", "context_window": 200000, "max_output": 128000,
        "supports_vision": True, "cost": "$$$", "recommended": False,
    },
    "claude-mythos-preview": {
        "name": "Claude Mythos (Preview)",
        "description": "Preview model — experimental, may change",
        "generation": "5.0", "context_window": 200000, "max_output": 128000,
        "supports_vision": True, "cost": "$$$", "recommended": False,
    },
    # --- Generation 4.x (current, still supported) ---
    "claude-opus-4-8": {
        "name": "Claude Opus 4.8",
        "description": "Most intelligent 4.x model for complex coding and analysis",
        "generation": "4.8", "context_window": 200000, "max_output": 128000,
        "supports_vision": True, "cost": "$$$", "recommended": True,
    },
    "claude-opus-4-7": {
        "name": "Claude Opus 4.7",
        "description": "High intelligence, strong value",
        "generation": "4.7", "context_window": 200000, "max_output": 128000,
        "supports_vision": True, "cost": "$$$", "recommended": False,
    },
    "claude-opus-4-6": {
        "name": "Claude Opus 4.6",
        "description": "Intelligent model for agents and complex coding",
        "generation": "4.6", "context_window": 200000, "max_output": 128000,
        "supports_vision": True, "cost": "$$$", "recommended": False,
    },
    "claude-sonnet-4-6": {
        "name": "Claude Sonnet 4.6",
        "description": "Best combination of speed and intelligence (4.x)",
        "generation": "4.6", "context_window": 200000, "max_output": 64000,
        "supports_vision": True, "cost": "$$", "recommended": False,
    },
    "claude-haiku-4-5-20251001": {
        "name": "Claude Haiku 4.5",
        "description": "Fastest model with near-frontier intelligence",
        "generation": "4.5", "context_window": 200000, "max_output": 64000,
        "supports_vision": True, "cost": "$", "recommended": True,
    },
    # --- Legacy (still in SDK, not recommended for new work) ---
    "claude-opus-4-5-20251101": {
        "name": "Claude Opus 4.5",
        "description": "Legacy — prefer claude-opus-4-8 or claude-opus-5",
        "generation": "4.5", "context_window": 200000, "max_output": 32000,
        "supports_vision": True, "cost": "$$$", "recommended": False,
    },
    "claude-sonnet-4-5-20250929": {
        "name": "Claude Sonnet 4.5",
        "description": "Legacy — prefer claude-sonnet-5 or claude-sonnet-4-6",
        "generation": "4.5", "context_window": 200000, "max_output": 64000,
        "supports_vision": True, "cost": "$$", "recommended": False,
    },
    "claude-opus-4-1-20250805": {
        "name": "Claude Opus 4.1",
        "description": "Legacy — prefer claude-opus-4-8 or claude-opus-5",
        "generation": "4.1", "context_window": 200000, "max_output": 32000,
        "supports_vision": True, "cost": "$$$", "recommended": False,
    },
}


def get_claude_model_info(model_id: str) -> dict:
    return CLAUDE_MODEL_METADATA.get(model_id, {"name": model_id, "supports_vision": True})


def format_claude_model_for_display(model_id: str, include_description: bool = False) -> str:
    info = get_claude_model_info(model_id)
    name = info.get("name", model_id)
    if include_description and "description" in info:
        return f"{name} ({info['description']})"
    return name


def get_claude_api_id_from_display(display_name_or_id: str) -> str:
    for api_id, meta in CLAUDE_MODEL_METADATA.items():
        if meta.get("name") == display_name_or_id:
            return api_id
    return display_name_or_id


# Alias kept for import compatibility
DEV_CLAUDE_MODELS = CLAUDE_MODELS


class ClaudeProvider(BaseProvider):
    def __init__(self, model: str = DEFAULT_MODEL, api_key: Optional[str] = None):
        try:
            import anthropic
        except ImportError:
            raise ImportError(
                "anthropic package is required for Claude: pip install anthropic"
            )
        self._model = model
        # api_key=None → SDK reads ANTHROPIC_API_KEY from environment
        self._client = __import__("anthropic").Anthropic(api_key=api_key)

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def model_name(self) -> str:
        return self._model

    def describe(self, image_bytes: bytes, mime_type: str, prompt: str) -> DescriptionResult:
        b64 = base64.standard_b64encode(image_bytes).decode("ascii")
        message = self._client.messages.create(
            model=self._model,
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime_type,
                                "data": b64,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )
        return DescriptionResult(
            text=message.content[0].text,
            model=self._model,
            provider="anthropic",
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
        )
