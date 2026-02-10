"""
OpenAI Models Configuration - Single Source of Truth

This file defines all available OpenAI models across the toolkit.
ALL components (IDT CLI, ImageDescriber GUI, etc.) MUST import from this file.

Last updated: 2026-02-09
Source: https://platform.openai.com/docs/models

NOTE: OpenAI provides an API to list models dynamically (client.models.list()),
but we maintain this hardcoded list for:
1. Better control over which models are shown to users
2. Consistent ordering and metadata
3. Filtering out non-vision models from the list
"""

from typing import List, Dict, Any

# OPENAI MODELS - Single source of truth for all toolkit components
# Format: Model ID as used in OpenAI API
# Only includes models with vision capabilities for image description tasks
OPENAI_MODELS = [
    # ====================
    # O1 SERIES (Latest reasoning models - 2024)
    # ====================
    "o1",                               # Latest reasoning model
    "o1-mini",                          # Smaller reasoning model
    "o1-preview",                       # Preview of o1 capabilities
    
    # ====================
    # GPT-4o SERIES (Omni - multimodal, 2024)
    # ====================
    "gpt-4o",                           # Latest GPT-4 Omni (RECOMMENDED)
                                        # Fast, multimodal, 128K context
    
    "gpt-4o-mini",                      # Smaller, faster, more affordable
                                        # Great for most image description tasks
    
    "chatgpt-4o-latest",                # Latest ChatGPT model
    
    # ====================
    # GPT-4 TURBO (Enhanced GPT-4, 2023-2024)
    # ====================
    "gpt-4-turbo",                      # Latest GPT-4 Turbo with vision
    "gpt-4-turbo-preview",              # Preview version
    
    # ====================
    # GPT-4 (Original, 2023)
    # ====================
    "gpt-4",                            # Original GPT-4
    "gpt-4-vision-preview"              # GPT-4 with vision (legacy)
]

# Recommended models for different use cases
OPENAI_RECOMMENDED = {
    "best_overall": "gpt-4o",
    "best_balance": "gpt-4o",
    "fastest": "gpt-4o-mini",
    "most_affordable": "gpt-4o-mini"
}

# Model metadata for display in UIs
OPENAI_MODEL_METADATA: Dict[str, Dict[str, Any]] = {
    "gpt-4o": {
        "name": "GPT-4o",
        "description": "Latest multimodal model",
        "supports_vision": True,
        "context_window": 128000,
        "recommended": True
    },
    "gpt-4o-mini": {
        "name": "GPT-4o Mini",
        "description": "Fast and affordable",
        "supports_vision": True,
        "context_window": 128000,
        "recommended": True
    },
    "o1": {
        "name": "O1",
        "description": "Advanced reasoning",
        "supports_vision": True,
        "recommended": False
    }
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
