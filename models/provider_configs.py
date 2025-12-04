"""
Provider Capabilities Configuration

Defines capabilities for each AI provider including:
- Prompt support
- Custom prompts
- Available prompt styles
- Model options support
"""

from typing import Dict, List, Any

# Provider capabilities database
PROVIDER_CAPABILITIES: Dict[str, Dict[str, Any]] = {
    "Ollama": {
        "supports_prompts": True,
        "supports_custom_prompts": True,
        "prompt_styles": ["detailed", "technical", "creative", "accessibility"],
        "requires_api_key": False,
        "is_cloud": False,
        "supports_options": True,
        "description": "Local LLM server for running vision models"
    },
    "Ollama Cloud": {
        "supports_prompts": True,
        "supports_custom_prompts": True,
        "prompt_styles": ["detailed", "technical", "creative", "accessibility"],
        "requires_api_key": False,  # Uses Ollama Cloud login
        "is_cloud": True,
        "supports_options": True,
        "description": "Cloud-based Ollama models"
    },
    "OpenAI": {
        "supports_prompts": True,
        "supports_custom_prompts": True,
        "prompt_styles": ["detailed", "technical", "creative", "accessibility"],
        "requires_api_key": True,
        "is_cloud": True,
        "supports_options": True,
        "description": "GPT-4o and other OpenAI vision models"
    },
    "Claude": {
        "supports_prompts": True,
        "supports_custom_prompts": True,
        "prompt_styles": ["detailed", "technical", "creative", "accessibility"],
        "requires_api_key": True,
        "is_cloud": True,
        "supports_options": True,
        "description": "Claude 4.x series from Anthropic with advanced reasoning"
    },
    "HuggingFace": {
        "supports_prompts": True,
        "supports_custom_prompts": False,
        "prompt_styles": ["simple", "narrative", "detailed", "technical"],
        "requires_api_key": False,
        "is_cloud": False,
        "supports_options": True,
        "description": "Local Florence-2 vision models with NPU acceleration support"
    },
    "Object Detection": {
        "supports_prompts": False,
        "supports_custom_prompts": False,
        "prompt_styles": [],
        "requires_api_key": False,
        "is_cloud": False,
        "supports_options": True,
        "description": "YOLO-based object detection"
    },
    "Enhanced Ollama (CPU + YOLO)": {
        "supports_prompts": True,
        "supports_custom_prompts": True,
        "prompt_styles": ["detailed", "technical", "creative", "accessibility"],
        "requires_api_key": False,
        "is_cloud": False,
        "supports_options": True,
        "description": "Combines Ollama with YOLO object detection"
    },
    "Grounding DINO": {
        "supports_prompts": False,
        "supports_custom_prompts": False,
        "prompt_styles": [],
        "requires_api_key": False,
        "is_cloud": False,
        "supports_options": True,
        "description": "Zero-shot object detection with text prompts"
    },
    "Copilot+ PC": {
        "supports_prompts": True,
        "supports_custom_prompts": True,
        "prompt_styles": ["detailed", "quick"],
        "requires_api_key": False,
        "is_cloud": False,
        "supports_options": True,
        "description": "NPU-accelerated vision models (DirectML)"
    }
}


def get_provider_capabilities(provider_name: str) -> Dict[str, Any]:
    """
    Get capabilities for a specific provider.
    
    Args:
        provider_name: Name of the provider
        
    Returns:
        Dictionary of capabilities, or empty dict if provider not found
    """
    return PROVIDER_CAPABILITIES.get(provider_name, {})


def supports_prompts(provider_name: str) -> bool:
    """Check if provider supports prompts."""
    caps = get_provider_capabilities(provider_name)
    return caps.get("supports_prompts", False)


def supports_custom_prompts(provider_name: str) -> bool:
    """Check if provider supports custom prompts."""
    caps = get_provider_capabilities(provider_name)
    return caps.get("supports_custom_prompts", False)


def get_prompt_styles(provider_name: str) -> List[str]:
    """Get available prompt styles for provider."""
    caps = get_provider_capabilities(provider_name)
    return caps.get("prompt_styles", [])


def requires_api_key(provider_name: str) -> bool:
    """Check if provider requires an API key."""
    caps = get_provider_capabilities(provider_name)
    return caps.get("requires_api_key", False)


def is_cloud_provider(provider_name: str) -> bool:
    """Check if provider is cloud-based."""
    caps = get_provider_capabilities(provider_name)
    return caps.get("is_cloud", False)


def supports_options(provider_name: str) -> bool:
    """Check if provider supports configuration options."""
    caps = get_provider_capabilities(provider_name)
    return caps.get("supports_options", False)
