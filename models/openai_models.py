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
    # GPT-5 SERIES (Latest - 2025/2026)
    # ====================
    "gpt-5.2",                          # Latest flagship for coding and agentic tasks
                                        # $1.75 input / $14 output per MTok
                                        # Supports vision (Image input only)
    
    "gpt-5.2-pro",                      # Premium tier GPT-5.2
                                        # Higher capability for complex tasks
    
    "gpt-5.1",                          # Mid-tier GPT-5 reasoning model
                                        # Balanced performance between 5.2 and 5
                                        # Supports vision (Image input only)
    
    "gpt-5",                            # Standard GPT-5 reasoning model
                                        # $1.25 input / $10 output per MTok
                                        # Supports vision (Image input only)
    
    "gpt-5-pro",                        # Premium tier GPT-5
                                        # Higher capability for complex tasks
    
    "gpt-5-mini",                       # Faster, cost-efficient GPT-5
                                        # $0.25 input / $2 output per MTok
                                        # Supports vision (Image input only)
    
    "gpt-5-nano",                       # Ultra-budget GPT-5
                                        # Most affordable GPT-5 tier
                                        # Supports vision (Image input only)
    
    # ====================
    # O1 SERIES (Reasoning models - 2024)
    # ====================
    "o1",                               # Previous o-series reasoning model
    "o1-mini",                          # Smaller reasoning model
    "o1-preview",                       # Preview of o1 capabilities
    
    # ====================
    # GPT-4o SERIES (Omni - multimodal, 2024)
    # ====================
    "gpt-4o",                           # GPT-4 Omni (RECOMMENDED for non-reasoning tasks)
                                        # Fast, multimodal, 128K context
    
    "gpt-4o-mini",                      # Smaller, faster, most affordable
                                        # Great for most image description tasks
    
    "chatgpt-4o-latest",                # Latest ChatGPT model
    
    # ====================
    # GPT-4.1 SERIES (Enhanced, 2025)
    # ====================
    "gpt-4.1",                          # GPT-4.1 standard
    "gpt-4.1-mini",                     # Smaller GPT-4.1
    "gpt-4.1-nano",                     # Ultra-budget GPT-4.1
    
    # ====================
    # GPT-4 TURBO (Enhanced GPT-4, 2023-2024)
    # ====================
    "gpt-4-turbo",                      # GPT-4 Turbo with vision (older)
    "gpt-4-turbo-preview",              # Preview version
    
    # ====================
    # GPT-4 (Original, 2023)
    # ====================
    # NOTE: Plain "gpt-4" does NOT support images (text-only)
    # gpt-4-vision-preview is deprecated/removed as of 2026
    # Use gpt-4o, gpt-5 series, or gpt-4-turbo for vision tasks
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
