"""
Models Package - Image Description Toolkit

This package contains all model-related functionality:
- Model status checking (check_models.py)
- Model management utilities (manage_models.py)

Supported Providers:
- Ollama (local vision models)
- Ollama Cloud (cloud-based Ollama)
- OpenAI (GPT-4o, gpt-4o-mini)
- Claude (Anthropic - claude-3.5-sonnet, etc.)

Usage:
    # Check model status
    python -m models.check_models
    python -m models.check_models --provider ollama
    
    # Manage models
    python -m models.manage_models list
    python -m models.manage_models install llava:7b
    python -m models.manage_models recommend
"""

__version__ = "1.0.0"
