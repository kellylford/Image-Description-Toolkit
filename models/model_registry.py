"""
Model Registry - Central registry for all AI models

Provides a unified interface to query model information across all providers.
"""

from typing import Dict, List, Optional, Any
from pathlib import Path
import json


class ModelRegistry:
    """Central registry for all AI models across providers."""
    
    def __init__(self):
        self._models = {}
        self._load_metadata()
    
    def _load_metadata(self):
        """Load model metadata from various sources."""
        # Load from manage_models.py metadata
        from models.manage_models import MODEL_METADATA
        self._models.update(MODEL_METADATA)
        
        # Load from config files if available
        config_path = Path("scripts/image_describer_config.json")
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    models_info = config.get('available_models', {})
                    # Merge with existing metadata
                    for model_name, info in models_info.items():
                        if model_name not in self._models:
                            self._models[model_name] = info
            except Exception as e:
                pass  # Ignore errors loading config
    
    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific model.
        
        Args:
            model_name: Name of the model
            
        Returns:
            Dictionary of model information, or None if not found
        """
        return self._models.get(model_name)
    
    def list_models(self, provider: Optional[str] = None, 
                   recommended_only: bool = False) -> List[str]:
        """
        List all models, optionally filtered by provider.
        
        Args:
            provider: Filter by provider name (e.g., "ollama", "openai")
            recommended_only: Only return recommended models
            
        Returns:
            List of model names
        """
        models = []
        for model_name, metadata in self._models.items():
            # Filter by provider
            if provider and metadata.get('provider') != provider:
                continue
            
            # Filter by recommended
            if recommended_only and not metadata.get('recommended', False):
                continue
            
            models.append(model_name)
        
        return sorted(models)
    
    def get_models_by_provider(self, provider: str) -> Dict[str, Dict[str, Any]]:
        """
        Get all models for a specific provider.
        
        Args:
            provider: Provider name
            
        Returns:
            Dictionary of {model_name: metadata}
        """
        provider_models = {}
        for model_name, metadata in self._models.items():
            if metadata.get('provider') == provider:
                provider_models[model_name] = metadata
        return provider_models
    
    def get_recommended_models(self, provider: Optional[str] = None) -> List[str]:
        """
        Get list of recommended models.
        
        Args:
            provider: Optional provider filter
            
        Returns:
            List of recommended model names
        """
        return self.list_models(provider=provider, recommended_only=True)
    
    def is_model_installed(self, model_name: str) -> bool:
        """
        Check if a model is installed (for Ollama models).
        
        Args:
            model_name: Name of the model
            
        Returns:
            True if installed, False otherwise
        """
        metadata = self.get_model_info(model_name)
        if not metadata:
            return False
        
        provider = metadata.get('provider')
        
        if provider == 'ollama':
            # Check if Ollama model is installed
            try:
                import requests
                response = requests.get("http://localhost:11434/api/tags", timeout=2)
                if response.status_code == 200:
                    data = response.json()
                    installed = [m['name'] for m in data.get('models', [])]
                    return model_name in installed
            except:
                pass
        
        # For other providers, assume available if configured
        return True
    
    def search_models(self, query: str) -> List[str]:
        """
        Search for models by name or description.
        
        Args:
            query: Search query
            
        Returns:
            List of matching model names
        """
        query = query.lower()
        matches = []
        
        for model_name, metadata in self._models.items():
            # Search in model name
            if query in model_name.lower():
                matches.append(model_name)
                continue
            
            # Search in description
            description = metadata.get('description', '').lower()
            if query in description:
                matches.append(model_name)
                continue
            
            # Search in tags
            tags = metadata.get('tags', [])
            if any(query in tag.lower() for tag in tags):
                matches.append(model_name)
        
        return sorted(matches)


# Global registry instance
_registry = None


def get_registry() -> ModelRegistry:
    """Get the global model registry instance."""
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
    return _registry


def get_model_info(model_name: str) -> Optional[Dict[str, Any]]:
    """Convenience function to get model info."""
    return get_registry().get_model_info(model_name)


def list_models(provider: Optional[str] = None, 
               recommended_only: bool = False) -> List[str]:
    """Convenience function to list models."""
    return get_registry().list_models(provider, recommended_only)


def get_recommended_models(provider: Optional[str] = None) -> List[str]:
    """Convenience function to get recommended models."""
    return get_registry().get_recommended_models(provider)


def is_model_installed(model_name: str) -> bool:
    """Convenience function to check if model is installed."""
    return get_registry().is_model_installed(model_name)


def search_models(query: str) -> List[str]:
    """Convenience function to search models."""
    return get_registry().search_models(query)
