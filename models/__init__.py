"""
Models Package - Image Description Toolkit

This package contains all model-related functionality:
- Model status checking (check_models.py)
- Model management utilities
- Model registry and metadata (model_registry.py)
- Provider capabilities (provider_configs.py)
- Copilot+ PC NPU support (copilot_npu.py)
- Model installation scripts:
  - install_groundingdino.bat - Install GroundingDINO for text-prompted detection
  - download_onnx_models.bat - Download ONNX models for performance
  - download_florence2.py - Download Florence-2 models
  - checkmodels.bat - Quick status check wrapper

Usage:
    # Check model status
    python -m models.check_models
    python -m models.check_models --provider groundingdino
    
    # From Python
    from models.provider_configs import PROVIDER_CAPABILITIES
    from models.model_registry import get_model_info
"""

__version__ = "1.0.0"
