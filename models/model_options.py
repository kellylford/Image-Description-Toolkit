"""
Model Options Configuration

Defines generic and provider-specific model options/parameters.
"""

from typing import Dict, Any, List

# Generic options available for most providers
GENERIC_OPTIONS: Dict[str, Dict[str, Any]] = {
    "temperature": {
        "type": "float",
        "range": [0.0, 2.0],
        "default": 0.7,
        "description": "Controls randomness in output (0=deterministic, 2=very random)",
        "applies_to": ["Ollama", "Ollama Cloud", "OpenAI", "Enhanced Ollama (CPU + YOLO)"]
    },
    "max_tokens": {
        "type": "int",
        "range": [50, 2000],
        "default": 500,
        "description": "Maximum response length in tokens",
        "applies_to": ["Ollama", "Ollama Cloud", "OpenAI", "Enhanced Ollama (CPU + YOLO)"]
    },
    "top_p": {
        "type": "float",
        "range": [0.0, 1.0],
        "default": 0.9,
        "description": "Nucleus sampling parameter (higher = more diverse)",
        "applies_to": ["Ollama", "Ollama Cloud", "OpenAI", "Enhanced Ollama (CPU + YOLO)"]
    },
    "timeout": {
        "type": "int",
        "range": [10, 300],
        "default": 60,
        "description": "Request timeout in seconds",
        "applies_to": ["Ollama", "Ollama Cloud", "OpenAI", "HuggingFace", "Copilot+ PC"]
    }
}

# Provider-specific options
PROVIDER_SPECIFIC_OPTIONS: Dict[str, Dict[str, Dict[str, Any]]] = {
    "Ollama": {
        "num_ctx": {
            "type": "int",
            "range": [1024, 8192],
            "default": 2048,
            "description": "Context window size for the model"
        },
        "num_predict": {
            "type": "int",
            "range": [50, 1000],
            "default": 500,
            "description": "Maximum number of tokens to predict"
        },
        "repeat_penalty": {
            "type": "float",
            "range": [1.0, 2.0],
            "default": 1.1,
            "description": "Penalty for repeating tokens"
        }
    },
    "Ollama Cloud": {
        "num_ctx": {
            "type": "int",
            "range": [1024, 8192],
            "default": 2048,
            "description": "Context window size for the model"
        }
    },
    "OpenAI": {
        "detail": {
            "type": "choice",
            "choices": ["auto", "low", "high"],
            "default": "auto",
            "description": "Image detail level (affects cost and quality)"
        }
    },
    "HuggingFace": {
        "use_gpu": {
            "type": "bool",
            "default": True,
            "description": "Use GPU acceleration if available"
        },
        "num_beams": {
            "type": "int",
            "range": [1, 10],
            "default": 3,
            "description": "Number of beams for beam search"
        }
    },
    "Object Detection": {
        "confidence_threshold": {
            "type": "float",
            "range": [0.1, 0.9],
            "default": 0.35,
            "description": "YOLO detection confidence threshold"
        },
        "iou_threshold": {
            "type": "float",
            "range": [0.1, 0.9],
            "default": 0.45,
            "description": "Intersection over Union threshold for NMS"
        },
        "max_detections": {
            "type": "int",
            "range": [10, 100],
            "default": 50,
            "description": "Maximum number of objects to detect"
        }
    },
    "Enhanced Ollama (CPU + YOLO)": {
        "yolo_confidence": {
            "type": "float",
            "range": [0.1, 0.9],
            "default": 0.35,
            "description": "YOLO detection confidence threshold"
        },
        "num_ctx": {
            "type": "int",
            "range": [1024, 8192],
            "default": 2048,
            "description": "Context window size for Ollama model"
        }
    },
    "Grounding DINO": {
        "box_threshold": {
            "type": "float",
            "range": [0.1, 0.9],
            "default": 0.35,
            "description": "Detection box confidence threshold"
        },
        "text_threshold": {
            "type": "float",
            "range": [0.1, 0.9],
            "default": 0.25,
            "description": "Text matching threshold"
        }
    },
    "HuggingFace": {
        "use_gpu": {
            "type": "bool",
            "default": True,
            "description": "Use GPU acceleration if available"
        }
    },
    "Copilot+ PC": {
        "use_npu": {
            "type": "bool",
            "default": True,
            "description": "Use NPU acceleration (DirectML)"
        },
        "max_new_tokens": {
            "type": "int",
            "range": [50, 500],
            "default": 200,
            "description": "Maximum number of new tokens to generate"
        }
    }
}


def get_generic_options_for_provider(provider_name: str) -> Dict[str, Dict[str, Any]]:
    """
    Get generic options applicable to a specific provider.
    
    Args:
        provider_name: Name of the provider
        
    Returns:
        Dictionary of applicable generic options
    """
    applicable_options = {}
    for opt_name, opt_config in GENERIC_OPTIONS.items():
        if provider_name in opt_config.get("applies_to", []):
            applicable_options[opt_name] = opt_config
    return applicable_options


def get_provider_specific_options(provider_name: str) -> Dict[str, Dict[str, Any]]:
    """
    Get provider-specific options.
    
    Args:
        provider_name: Name of the provider
        
    Returns:
        Dictionary of provider-specific options
    """
    return PROVIDER_SPECIFIC_OPTIONS.get(provider_name, {})


def get_all_options_for_provider(provider_name: str) -> Dict[str, Dict[str, Any]]:
    """
    Get all options (generic + specific) for a provider.
    
    Args:
        provider_name: Name of the provider
        
    Returns:
        Combined dictionary of all applicable options
    """
    options = {}
    options.update(get_generic_options_for_provider(provider_name))
    options.update(get_provider_specific_options(provider_name))
    return options


def get_default_value(option_config: Dict[str, Any]) -> Any:
    """Get the default value for an option."""
    return option_config.get("default")


def validate_option_value(option_config: Dict[str, Any], value: Any) -> bool:
    """
    Validate an option value against its configuration.
    
    Args:
        option_config: Option configuration dictionary
        value: Value to validate
        
    Returns:
        True if valid, False otherwise
    """
    opt_type = option_config.get("type")
    
    if opt_type == "float":
        if not isinstance(value, (int, float)):
            return False
        min_val, max_val = option_config.get("range", [float('-inf'), float('inf')])
        return min_val <= value <= max_val
    
    elif opt_type == "int":
        if not isinstance(value, int):
            return False
        min_val, max_val = option_config.get("range", [float('-inf'), float('inf')])
        return min_val <= value <= max_val
    
    elif opt_type == "bool":
        return isinstance(value, bool)
    
    elif opt_type == "choice":
        choices = option_config.get("choices", [])
        return value in choices
    
    return True
