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
        "supported_attachments": ["image/jpeg", "image/png", "image/gif", "image/webp"],
        "description": "Local LLM server for running vision models"
    },
    "Ollama Cloud": {
        "supports_prompts": True,
        "supports_custom_prompts": True,
        "prompt_styles": ["detailed", "technical", "creative", "accessibility"],
        "requires_api_key": False,  # Uses Ollama Cloud login
        "is_cloud": True,
        "supports_options": True,
        "supported_attachments": [],  # Ollama Cloud has no vision support
        "description": "Cloud-based Ollama models"
    },
    "OpenAI": {
        "supports_prompts": True,
        "supports_custom_prompts": True,
        "prompt_styles": ["detailed", "technical", "creative", "accessibility"],
        "requires_api_key": True,
        "is_cloud": True,
        "supports_options": True,
        "supported_attachments": ["image/jpeg", "image/png", "image/gif", "image/webp"],
        "description": "GPT-4o and other OpenAI vision models"
    },
    "Claude": {
        "supports_prompts": True,
        "supports_custom_prompts": True,
        "prompt_styles": ["detailed", "technical", "creative", "accessibility"],
        "requires_api_key": True,
        "is_cloud": True,
        "supports_options": True,
        "supported_attachments": ["image/jpeg", "image/png", "image/gif", "image/webp",
                                   "application/pdf"],
        "description": "Claude 4.x series from Anthropic with advanced reasoning"
    },
    "HuggingFace": {
        "supports_prompts": True,
        "supports_custom_prompts": False,
        "prompt_styles": ["simple", "narrative", "detailed", "technical"],
        "requires_api_key": False,
        "is_cloud": False,
        "supports_options": True,
        "supported_attachments": ["image/jpeg", "image/png", "image/gif", "image/webp",
                                   "image/bmp", "image/tiff"],
        "description": "Local Florence-2 vision models with NPU acceleration support"
    },
    "Object Detection": {
        "supports_prompts": False,
        "supports_custom_prompts": False,
        "prompt_styles": [],
        "requires_api_key": False,
        "is_cloud": False,
        "supports_options": True,
        "supported_attachments": [],
        "description": "YOLO-based object detection"
    },
    "Enhanced Ollama (CPU + YOLO)": {
        "supports_prompts": True,
        "supports_custom_prompts": True,
        "prompt_styles": ["detailed", "technical", "creative", "accessibility"],
        "requires_api_key": False,
        "is_cloud": False,
        "supports_options": True,
        "supported_attachments": ["image/jpeg", "image/png", "image/gif", "image/webp"],
        "description": "Combines Ollama with YOLO object detection"
    },
    "Grounding DINO": {
        "supports_prompts": False,
        "supports_custom_prompts": False,
        "prompt_styles": [],
        "requires_api_key": False,
        "is_cloud": False,
        "supports_options": True,
        "supported_attachments": [],
        "description": "Zero-shot object detection with text prompts"
    },
    "Copilot+ PC": {
        "supports_prompts": True,
        "supports_custom_prompts": True,
        "prompt_styles": ["detailed", "quick"],
        "requires_api_key": False,
        "is_cloud": False,
        "supports_options": True,
        "supported_attachments": ["image/jpeg", "image/png", "image/gif", "image/webp"],
        "description": "NPU-accelerated vision models (DirectML)"
    },
    "MLX": {
        "supports_prompts": True,
        "supports_custom_prompts": True,
        "prompt_styles": ["detailed", "technical", "creative", "narrative", "colorful", "accessibility"],
        "requires_api_key": False,
        "is_cloud": False,
        "supports_options": True,
        "supported_attachments": ["image/jpeg", "image/png", "image/gif", "image/webp"],
        "description": "Apple Metal GPU inference on Apple Silicon (macOS only). No API key or cloud cost."
    }
}


def get_provider_capabilities(provider_name: str) -> Dict[str, Any]:
    """
    Get capabilities for a specific provider.

    Lookup is case-insensitive: "mlx", "MLX", and "Mlx" all resolve to the
    same entry so callers do not need to know the exact key capitalisation.

    Args:
        provider_name: Name of the provider

    Returns:
        Dictionary of capabilities, or empty dict if provider not found
    """
    # Exact match first (fastest path, preserves behaviour for existing callers)
    if provider_name in PROVIDER_CAPABILITIES:
        return PROVIDER_CAPABILITIES[provider_name]
    # Case-insensitive fallback
    lower = provider_name.lower()
    for key, caps in PROVIDER_CAPABILITIES.items():
        if key.lower() == lower:
            return caps
    return {}


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


# Maps MIME type to the file extension glob(s) used in wx.FileDialog wildcards.
_MIME_TO_EXTENSIONS: Dict[str, str] = {
    "image/jpeg": "*.jpg;*.jpeg",
    "image/png": "*.png",
    "image/gif": "*.gif",
    "image/webp": "*.webp",
    "image/bmp": "*.bmp",
    "image/tiff": "*.tif;*.tiff",
    "application/pdf": "*.pdf",
}


def get_supported_attachments(provider_name: str) -> List[str]:
    """Return the list of MIME types the provider accepts as chat attachments."""
    caps = get_provider_capabilities(provider_name)
    return caps.get("supported_attachments", [])


def supports_attachments(provider_name: str) -> bool:
    """Return True if the provider accepts any file attachments in chat."""
    return bool(get_supported_attachments(provider_name))


def get_attachment_wildcard(provider_name: str) -> str:
    """Build a wx.FileDialog wildcard string from the provider's supported MIME types.

    Returns groups: "Images (*.jpg;*.png)|*.jpg;*.png", "PDF (*.pdf)|*.pdf",
    and a combined "All supported" entry.  Falls back to a plain all-files
    wildcard when the provider has no attachment support.
    """
    mime_types = get_supported_attachments(provider_name)
    if not mime_types:
        return "All files (*.*)|*.*"

    image_exts: List[str] = []
    pdf_exts: List[str] = []
    other_exts: List[str] = []

    for mime in mime_types:
        exts_str = _MIME_TO_EXTENSIONS.get(mime, "")
        if not exts_str:
            continue
        exts = exts_str.split(";")
        if mime.startswith("image/"):
            image_exts.extend(exts)
        elif mime == "application/pdf":
            pdf_exts.extend(exts)
        else:
            other_exts.extend(exts)

    parts: List[str] = []
    all_exts: List[str] = []

    if image_exts:
        ext_str = ";".join(image_exts)
        parts.append(f"Images ({ext_str})|{ext_str}")
        all_exts.extend(image_exts)

    if pdf_exts:
        ext_str = ";".join(pdf_exts)
        parts.append(f"PDF ({ext_str})|{ext_str}")
        all_exts.extend(pdf_exts)

    if other_exts:
        ext_str = ";".join(other_exts)
        parts.append(f"Other ({ext_str})|{ext_str}")
        all_exts.extend(other_exts)

    all_ext_str = ";".join(all_exts)
    parts.append(f"All supported ({all_ext_str})|{all_ext_str}")

    return "|".join(parts)


def supports_options(provider_name: str) -> bool:
    """Check if provider supports configuration options."""
    caps = get_provider_capabilities(provider_name)
    return caps.get("supports_options", False)
