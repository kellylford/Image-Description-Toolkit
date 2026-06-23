"""
Anthropic Claude provider.
Reads ANTHROPIC_API_KEY from the environment (standard SDK behavior).
"""
from __future__ import annotations

import base64
from typing import Optional

from .base import BaseProvider, DescriptionResult

CLAUDE_MODELS = [
    "claude-opus-4-6",
    "claude-sonnet-4-6",
    "claude-sonnet-4-5-20250929",
    "claude-haiku-4-5-20251001",
    "claude-opus-4-5-20251101",
    "claude-opus-4-1-20250805",
    "claude-opus-4-20250514",
    "claude-sonnet-4-20250514",
    "claude-3-haiku-20240307",
]

DEFAULT_MODEL = "claude-opus-4-6"

CLAUDE_MODEL_METADATA: dict = {
    "claude-opus-4-6": {
        "name": "Claude Opus 4.6",
        "description": "Most intelligent model for agents and complex coding",
        "generation": "4.6", "context_window": 200000, "max_output": 128000,
        "supports_vision": True, "cost": "$$$", "recommended": True,
    },
    "claude-sonnet-4-6": {
        "name": "Claude Sonnet 4.6",
        "description": "Best combination of speed and intelligence",
        "generation": "4.6", "context_window": 200000, "max_output": 64000,
        "supports_vision": True, "cost": "$$", "recommended": True,
    },
    "claude-sonnet-4-5-20250929": {
        "name": "Claude Sonnet 4.5",
        "description": "Best combination of speed and intelligence",
        "generation": "4.5", "context_window": 200000, "max_output": 64000,
        "supports_vision": True, "cost": "$$", "recommended": True,
    },
    "claude-haiku-4-5-20251001": {
        "name": "Claude Haiku 4.5",
        "description": "Fastest model with near-frontier intelligence",
        "generation": "4.5", "context_window": 200000, "max_output": 64000,
        "supports_vision": True, "cost": "$", "recommended": True,
    },
    "claude-opus-4-5-20251101": {
        "name": "Claude Opus 4.5",
        "description": "Powerful model for complex challenges (Nov 2025)",
        "generation": "4.5", "context_window": 200000, "max_output": 32000,
        "supports_vision": True, "cost": "$$$", "recommended": False,
    },
    "claude-opus-4-1-20250805": {
        "name": "Claude Opus 4.1",
        "description": "High intelligence (legacy, prefer claude-opus-4-6)",
        "generation": "4.1", "context_window": 200000, "max_output": 32000,
        "supports_vision": True, "cost": "$$$", "recommended": False,
    },
    "claude-opus-4-20250514": {
        "name": "Claude Opus 4.0",
        "description": "Original 4th generation high intelligence (legacy)",
        "generation": "4.0", "context_window": 200000, "max_output": 32000,
        "supports_vision": True, "cost": "$$$", "recommended": False,
    },
    "claude-sonnet-4-20250514": {
        "name": "Claude Sonnet 4.0",
        "description": "Original 4th generation balanced performance (legacy)",
        "generation": "4.0", "context_window": 200000, "max_output": 64000,
        "supports_vision": True, "cost": "$$", "recommended": False,
    },
    "claude-3-haiku-20240307": {
        "name": "Claude Haiku 3",
        "description": "Claude 3 Haiku (shutting down April 19, 2026)",
        "generation": "3.0", "context_window": 200000, "max_output": 4096,
        "supports_vision": True, "cost": "$", "recommended": False,
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
