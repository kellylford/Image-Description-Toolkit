"""
OpenAI Models Configuration - Single Source of Truth

This file defines all available OpenAI models across the toolkit.
ALL components (IDT CLI, ImageDescriber GUI, etc.) MUST import from this file.

Last updated: 2026-02-23
Source: https://developers.openai.com/api/docs/models
Verified: Live API query (client.models.list()) on 2026-02-23

NOTE: Only models with confirmed image/vision input support via Chat Completions
are included. Audio-only, TTS, transcription, image-generation, embedding,
realtime, and codex-only models are excluded.
"""

from typing import List, Dict, Any

# OPENAI MODELS - Single source of truth for all toolkit components
# Format: Model ID as used in OpenAI API
# Only includes models with vision capabilities for image description tasks
# Verified present in live API on 2026-02-23
OPENAI_MODELS = [
    # ====================
    # GPT-5 SERIES (Frontier - 2025/2026)
    # ====================
    "gpt-5.2",          # Best model; vision confirmed via live test 2026-02-23
    "gpt-5.1",          # Mid-tier GPT-5 reasoning model; vision confirmed
    "gpt-5",            # Flagship; reasoning tokens—needs max_completion_tokens=1500
    "gpt-5-mini",       # Faster, cost-efficient GPT-5; vision confirmed
    "gpt-5-nano",       # Fastest, most affordable GPT-5; vision confirmed

    # ====================
    # O-SERIES REASONING MODELS (2024-2025)
    # ====================
    "o4-mini",          # Fast cost-efficient reasoning; needs max_completion_tokens=1500
    "o3",               # Reasoning model for complex tasks; vision confirmed
    "o1",               # Full o-series reasoning; needs max_completion_tokens=1500

    # ====================
    # GPT-4o SERIES (Omni - 2024)
    # ====================
    "gpt-4o",           # Fast, intelligent, flexible — RECOMMENDED for most tasks
    "gpt-4o-mini",      # Affordable, fast — RECOMMENDED for budget use

    # ====================
    # GPT-4.1 SERIES (2025)
    # ====================
    "gpt-4.1",          # Smartest non-reasoning model; vision confirmed
    "gpt-4.1-mini",     # Smaller GPT-4.1; vision confirmed
    "gpt-4.1-nano",     # Ultra-budget GPT-4.1; vision confirmed
]
# Total: 13 verified vision-capable models as of 2026-02-23

_EXCLUDED_MODELS_2026 = [
    # EXCLUDED (verified 2026-02-23):
    # gpt-5.2-pro      — HTTP 404, not accessible at this API tier
    # gpt-5-pro        — HTTP 404, not accessible at this API tier
    # o3-mini          — returns 'image_url is only supported by certain models'
    # gpt-4-turbo      — returns 'image_url is only supported by certain models'
    # o1-mini          — deprecated
    # o1-preview       — deprecated
    # o1-pro           — Responses API only, not Chat Completions
    # o3-pro           — Responses API only
    # chatgpt-4o-latest — deprecated wrapper, not for API use
    # gpt-4-turbo-preview — deprecated alias
    # gpt-4 plain      — no vision support
]

# Recommended models for different use cases
OPENAI_RECOMMENDED = {
    "best_overall": "gpt-4o",
    "best_balance": "gpt-4o",
    "fastest": "gpt-4o-mini",
    "most_affordable": "gpt-4o-mini"
}

# Model metadata for display in UIs.
# cost: "$" = cheapest, "$$" = moderate, "$$$" = expensive, "$$$$" = highest
# For exact pricing see https://openai.com/api/pricing
OPENAI_MODEL_METADATA: Dict[str, Dict[str, Any]] = {

    # GPT-5 SERIES
    "gpt-5.2": {
        "name": "GPT-5.2",
        "description": "Best available model. Highest quality image descriptions.",
        "cost": "$$$$",
        "use_case": "Most detailed results",
        "supports_vision": True,
        "recommended": False,
    },
    "gpt-5.1": {
        "name": "GPT-5.1",
        "description": "High-quality GPT-5 with strong reasoning capabilities.",
        "cost": "$$$",
        "use_case": "Complex scenes",
        "supports_vision": True,
        "recommended": False,
    },
    "gpt-5": {
        "name": "GPT-5",
        "description": "Flagship GPT-5 reasoning model. Thorough, deliberate analysis.",
        "cost": "$$$",
        "use_case": "Detailed reasoning",
        "supports_vision": True,
        "context_window": 128000,
        "recommended": False,
    },
    "gpt-5-mini": {
        "name": "GPT-5 Mini",
        "description": "Faster, efficient GPT-5. Good balance of quality and cost.",
        "cost": "$$",
        "use_case": "Good balance",
        "supports_vision": True,
        "recommended": False,
    },
    "gpt-5-nano": {
        "name": "GPT-5 Nano",
        "description": "Fastest GPT-5. May occasionally return empty responses on long outputs.",
        "cost": "$",
        "use_case": "Speed over quality",
        "supports_vision": True,
        "recommended": False,
        "notes": "May return empty responses on long outputs; the app retries automatically.",
    },

    # O-SERIES REASONING
    "o4-mini": {
        "name": "O4 Mini",
        "description": "Fast cost-efficient reasoning. Good for structured, detailed analysis.",
        "cost": "$$",
        "use_case": "Reasoning at moderate cost",
        "supports_vision": True,
        "recommended": False,
    },
    "o3": {
        "name": "O3",
        "description": "Powerful reasoning for complex tasks. Slower but very thorough.",
        "cost": "$$$",
        "use_case": "Complex analysis",
        "supports_vision": True,
        "recommended": False,
    },
    "o1": {
        "name": "O1",
        "description": "Original full reasoning model. Careful, deliberate analysis.",
        "cost": "$$$",
        "use_case": "Deliberate analysis",
        "supports_vision": True,
        "context_window": 128000,
        "recommended": False,
    },

    # GPT-4o SERIES
    "gpt-4o": {
        "name": "GPT-4o",
        "description": "Fast, intelligent, flexible. Best choice for most image description tasks.",
        "cost": "$$",
        "use_case": "Best general choice",
        "supports_vision": True,
        "context_window": 128000,
        "recommended": True,
    },
    "gpt-4o-mini": {
        "name": "GPT-4o Mini",
        "description": "Affordable and fast, but charges more image tokens per photo than GPT-4o.",
        "cost": "$",
        "use_case": "Quick / budget",
        "supports_vision": True,
        "context_window": 128000,
        "recommended": False,
        "notes": "Despite the 'mini' label, gpt-4o-mini uses ~25 k image tokens vs gpt-4o's ~865 — "
                 "making gpt-4o the better value for image tasks.",
    },

    # GPT-4.1 SERIES
    "gpt-4.1": {
        "name": "GPT-4.1",
        "description": "Latest non-reasoning GPT-4.1. High quality descriptions.",
        "cost": "$$",
        "use_case": "High quality",
        "supports_vision": True,
        "recommended": False,
    },
    "gpt-4.1-mini": {
        "name": "GPT-4.1 Mini",
        "description": "Compact GPT-4.1. Good quality at reduced cost.",
        "cost": "$",
        "use_case": "Budget quality",
        "supports_vision": True,
        "recommended": False,
    },
    "gpt-4.1-nano": {
        "name": "GPT-4.1 Nano",
        "description": "Ultra-budget GPT-4.1. Fastest and cheapest; less detailed.",
        "cost": "$",
        "use_case": "Cheapest option",
        "supports_vision": True,
        "recommended": False,
    },
}


def get_openai_models() -> List[str]:
    """
    Get the complete list of OpenAI models with vision support.
    
    Returns:
        List of OpenAI model IDs
    """
    return OPENAI_MODELS.copy()


def get_recommended_openai_models() -> List[str]:
    """
    Get recommended OpenAI models for image description tasks.
    
    Returns:
        List of recommended model IDs
    """
    return [
        "gpt-4o",
        "gpt-4o-mini"
    ]


def get_openai_model_info(model_id: str) -> Dict[str, Any]:
    """
    Get metadata for a specific OpenAI model.
    
    Args:
        model_id: OpenAI model ID
        
    Returns:
        Dictionary of model metadata, or basic info if not found
    """
    return OPENAI_MODEL_METADATA.get(model_id, {
        "name": model_id,
        "description": "OpenAI model",
        "supports_vision": True
    })


def format_openai_model_for_display(model_id: str, include_description: bool = True) -> str:
    """
    Format an OpenAI model ID for display in UIs.
    
    Args:
        model_id: OpenAI model ID
        include_description: Whether to include description in parentheses
        
    Returns:
        Formatted string for display
    """
    info = get_openai_model_info(model_id)
    
    if include_description and "description" in info:
        return f"{model_id} ({info['description']})"
    
    return model_id


# For backwards compatibility with existing code
DEV_OPENAI_MODELS = OPENAI_MODELS
