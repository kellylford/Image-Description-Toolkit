"""
Claude Models Configuration - Single Source of Truth

This file defines all available Claude models across the toolkit.
ALL components (IDT CLI, ImageDescriber GUI, scripts, etc.) MUST import from
this file. Do NOT hardcode Claude model IDs in other files.

Last updated: 2026-02-20
Source: https://www.anthropic.com/pricing

NOTE: Claude doesn't provide an API to list models dynamically, so we maintain
this hardcoded list and update it when new models are released or deprecated.
For current pricing, see the Anthropic pricing page — we store relative cost
tiers ($ / $$ / $$$) here rather than exact figures that change frequently.
"""

from typing import List, Dict, Any

# CLAUDE MODELS - Single source of truth for all toolkit components
# Format: Model ID as used in Claude API
CLAUDE_MODELS = [
    # ====================
    # CLAUDE 4.x SERIES (Latest - 2025)
    # ====================
    
    # Claude 4.6 - Latest generation (2025)
    "claude-opus-4-6",                  # Most intelligent - agents, complex coding, adaptive thinking
                                        # $5 input / $25 output per MTok
                                        # 200K context (1M beta), 128K max output
    "claude-sonnet-4-6",                # Best balance of speed and intelligence
                                        # $3 input / $15 output per MTok
                                        # 200K context (1M beta), 64K max output

    # Claude 4.5 - Fast and capable (Oct 2024 - Jan 2025)
    "claude-sonnet-4-5-20250929",       # Best balance - speed + intelligence (RECOMMENDED)
                                        # $3 input / $15 output per MTok
                                        # 200K context (1M beta), 64K max output
    
    "claude-haiku-4-5-20251001",        # Fastest - near-frontier intelligence
                                        # $1 input / $5 output per MTok
                                        # 200K context, 64K max output

    "claude-opus-4-5-20251101",         # Opus 4.5 (Nov 2025)

    # Claude 4.1 - Legacy
    "claude-opus-4-1-20250805",         # High intelligence (legacy, use 4-6 instead)
    
    # Claude 4.0 - Original 4th generation
    "claude-opus-4-20250514",           # High intelligence (legacy)
    "claude-sonnet-4-20250514",         # Balanced performance (legacy)

    # CLAUDE 3.x SERIES
    # claude-3-7-sonnet-20250219 - deprecated by Anthropic
    # claude-3-5-sonnet-20241022 - deprecated by Anthropic
    # claude-3-5-haiku-20241022 - returns 404 as of Feb 2026
    # claude-3-opus-20240229    - deprecated by Anthropic
    # claude-3-sonnet-20240229  - deprecated by Anthropic
    "claude-3-haiku-20240307",          # Shutting down April 19, 2026 - included until then
]

# Model aliases (some models have shorter aliases)
CLAUDE_MODEL_ALIASES = {
    "claude-opus-4-6": "claude-opus-4-6",
    "claude-sonnet-4-6": "claude-sonnet-4-6",
    "claude-sonnet-4-5": "claude-sonnet-4-5-20250929",
    "claude-haiku-4-5": "claude-haiku-4-5-20251001"
}

# Recommended models for different use cases
CLAUDE_RECOMMENDED = {
    "best_overall": "claude-opus-4-6",
    "best_balance": "claude-sonnet-4-6",
    "fastest": "claude-haiku-4-5-20251001",
    "most_affordable": "claude-haiku-4-5-20251001"
}

# Model metadata for display in UIs.
# cost: "$" = cheapest, "$$" = mid-range, "$$$" = most expensive
# For exact pricing see https://www.anthropic.com/pricing
CLAUDE_MODEL_METADATA: Dict[str, Dict[str, Any]] = {
    "claude-opus-4-6": {
        "name": "Claude Opus 4.6",
        "description": "Most intelligent model for agents and complex coding",
        "generation": "4.6",
        "context_window": 200000,
        "max_output": 128000,
        "supports_vision": True,
        "supports_adaptive_thinking": True,
        "cost": "$$$",
        "recommended": True
    },
    "claude-sonnet-4-6": {
        "name": "Claude Sonnet 4.6",
        "description": "Best combination of speed and intelligence",
        "generation": "4.6",
        "context_window": 200000,
        "max_output": 64000,
        "supports_vision": True,
        "supports_adaptive_thinking": True,
        "cost": "$$",
        "recommended": True
    },
    "claude-sonnet-4-5-20250929": {
        "name": "Claude Sonnet 4.5",
        "description": "Best combination of speed and intelligence",
        "generation": "4.5",
        "context_window": 200000,
        "max_output": 64000,
        "supports_vision": True,
        "supports_adaptive_thinking": False,
        "cost": "$$",
        "recommended": True
    },
    "claude-haiku-4-5-20251001": {
        "name": "Claude Haiku 4.5",
        "description": "Fastest model with near-frontier intelligence",
        "generation": "4.5",
        "context_window": 200000,
        "max_output": 64000,
        "supports_vision": True,
        "supports_adaptive_thinking": False,
        "cost": "$",
        "recommended": True
    },
    "claude-opus-4-1-20250805": {
        "name": "Claude Opus 4.1",
        "description": "High intelligence (legacy, prefer claude-opus-4-6)",
        "generation": "4.1",
        "context_window": 200000,
        "max_output": 32000,
        "supports_vision": True,
        "supports_adaptive_thinking": False,
        "cost": "$$$",
        "recommended": False
    },
    "claude-opus-4-20250514": {
        "name": "Claude Opus 4.0",
        "description": "Original 4th generation high intelligence (legacy)",
        "generation": "4.0",
        "context_window": 200000,
        "max_output": 32000,
        "supports_vision": True,
        "supports_adaptive_thinking": False,
        "cost": "$$$",
        "recommended": False
    },
    "claude-sonnet-4-20250514": {
        "name": "Claude Sonnet 4.0",
        "description": "Original 4th generation balanced performance (legacy)",
        "generation": "4.0",
        "context_window": 200000,
        "max_output": 64000,
        "supports_vision": True,
        "supports_adaptive_thinking": False,
        "cost": "$$",
        "recommended": False
    },
    "claude-opus-4-5-20251101": {
        "name": "Claude Opus 4.5",
        "description": "Powerful model for complex challenges (Nov 2025)",
        "generation": "4.5",
        "context_window": 200000,
        "max_output": 32000,
        "supports_vision": True,
        "supports_adaptive_thinking": False,
        "cost": "$$$",
        "recommended": False
    },
    "claude-3-haiku-20240307": {
        "name": "Claude Haiku 3",
        "description": "Claude 3 Haiku (shutting down April 19, 2026)",
        "generation": "3.0",
        "context_window": 200000,
        "max_output": 4096,
        "supports_vision": True,
        "supports_adaptive_thinking": False,
        "cost": "$",
        "recommended": False
    },
}


def get_claude_models() -> List[str]:
    """
    Get the complete list of Claude models.
    
    Returns:
        List of Claude model IDs
    """
    return CLAUDE_MODELS.copy()


def get_recommended_claude_models() -> List[str]:
    """
    Get recommended Claude models for image description tasks.

    Returns:
        List of recommended model IDs (from CLAUDE_MODELS, preserving order)
    """
    return [m for m in CLAUDE_MODELS if CLAUDE_MODEL_METADATA.get(m, {}).get("recommended", False)]


def get_claude_model_info(model_id: str) -> Dict[str, Any]:
    """
    Get metadata for a specific Claude model.

    Args:
        model_id: Claude model ID

    Returns:
        Dictionary of model metadata, or basic info if model is not in the registry
    """
    return CLAUDE_MODEL_METADATA.get(model_id, {
        "name": model_id,
        "description": "Claude model",
        "supports_vision": True
    })


def format_claude_model_for_display(model_id: str, include_description: bool = False) -> str:
    """
    Format a Claude model ID as a user-friendly display name.

    Uses the 'name' field from CLAUDE_MODEL_METADATA (e.g. "Claude Sonnet 4.5")
    rather than the raw API ID (e.g. "claude-sonnet-4-5-20250929").

    Args:
        model_id: Claude model API ID
        include_description: If True, appends the description in parentheses

    Returns:
        Friendly display string, e.g. "Claude Sonnet 4.5" or
        "Claude Sonnet 4.5 (Best combination of speed and intelligence)"
    """
    info = get_claude_model_info(model_id)
    friendly_name = info.get("name", model_id)

    if include_description and "description" in info:
        return f"{friendly_name} ({info['description']})"

    return friendly_name


def get_claude_api_id_from_display(display_name_or_id: str) -> str:
    """
    Reverse-map a friendly display name (or existing API ID) back to the API ID.

    Handles:
    - Friendly names:  "Claude Sonnet 4.5"  → "claude-sonnet-4-5-20250929"
    - Raw API IDs:     "claude-sonnet-4-5-20250929" → "claude-sonnet-4-5-20250929"
    - Unknown strings: returned unchanged (safe fallback for saved configs)

    Args:
        display_name_or_id: Friendly display name or raw API model ID

    Returns:
        Claude API model ID string
    """
    # Build reverse map from friendly name → API ID
    for api_id, meta in CLAUDE_MODEL_METADATA.items():
        if meta.get("name") == display_name_or_id:
            return api_id

    # If it's already a known API ID, return it directly
    if display_name_or_id in CLAUDE_MODEL_METADATA:
        return display_name_or_id

    # Unknown string — return as-is so saved configs don't break
    return display_name_or_id


# For backwards compatibility with existing code
DEV_CLAUDE_MODELS = CLAUDE_MODELS
