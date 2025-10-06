"""
AI Provider classes for Image Describer

This module contains all AI provider implementations including
Ollama, OpenAI, and HuggingFace providers.
"""

import os
import requests
import json
import base64
import time
from typing import List, Dict, Optional
from pathlib import Path
import platform
import subprocess

# Try to import Windows Runtime for Copilot+ PC support (Windows only)
try:
    import winrt
    from winrt.windows.ai.machinelearning import LearningModelDeviceKind
    HAS_WINRT = True and platform.system() == "Windows"
except ImportError:
    winrt = None
    LearningModelDeviceKind = None
    HAS_WINRT = False

# DEVELOPMENT MODE: Disabled to show real installed models
# Use check_models.py to see what's installed
# Use manage_models.py to install/remove models
# Users should see only models they actually have, not hardcoded lists
DEV_MODE_HARDCODED_MODELS = False

# Hardcoded model lists based on system query results
DEV_OLLAMA_MODELS = [
    "bakllava:latest",
    "mistral-small3.1:latest", 
    "gemma3:latest",
    "moondream:latest",
    "llava-llama3:latest",
    "llama3.2-vision:latest",
    "llava:latest"
]

DEV_OLLAMA_CLOUD_MODELS = [
    "gpt-oss:20b-cloud",
    "deepseek-v3.1:671b-cloud", 
    "gpt-oss:120b-cloud",
    "qwen3-coder:480b-cloud"
]

DEV_OPENAI_MODELS = [
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-4",
    "gpt-4-vision-preview"
]

DEV_CLAUDE_MODELS = [
    # Claude 4 Series (Latest - 2025)
    "claude-sonnet-4-5-20250929",   # Claude Sonnet 4.5 (best for agents/coding) - RECOMMENDED
    "claude-opus-4-1-20250805",     # Claude Opus 4.1 (specialized complex tasks, superior reasoning)
    "claude-sonnet-4-20250514",     # Claude Sonnet 4 (high performance)
    "claude-opus-4-20250514",       # Claude Opus 4 (very high intelligence)
    # Claude 3.7
    "claude-3-7-sonnet-20250219",   # Claude Sonnet 3.7 (high performance with extended thinking)
    # Claude 3.5
    "claude-3-5-haiku-20241022",    # Claude Haiku 3.5 (fastest, most affordable)
    # Claude 3
    "claude-3-haiku-20240307",      # Claude Haiku 3 (fast and compact)
    # Note: All Claude 3+ models support vision. Claude 2.x excluded (no vision support)
]

from abc import ABC, abstractmethod


class AIProvider(ABC):
    """Base class for AI providers"""
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the name of this provider"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is available for use"""
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Get list of available models for this provider"""
        pass
    
    @abstractmethod
    def describe_image(self, image_path: str, prompt: str, model: str) -> str:
        """Generate description for an image"""
        pass


class OllamaProvider(AIProvider):
    """Ollama provider for local AI models"""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.timeout = 300  # 5 minutes timeout
        self._models_cache = None
        self._models_cache_time = 0
        self._cache_duration = 30  # Cache for 30 seconds
    
    def get_provider_name(self) -> str:
        return "Ollama"
    
    def is_available(self) -> bool:
        """Check if Ollama is available"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_available_models(self) -> List[str]:
        """Get list of available Ollama models (local only, excludes cloud models)"""
        # DEVELOPMENT MODE: Return hardcoded models for faster testing
        if DEV_MODE_HARDCODED_MODELS:
            return DEV_OLLAMA_MODELS.copy()
        
        # ORIGINAL DETECTION CODE (preserved for when dev mode is disabled)
        # Check cache first
        current_time = time.time()
        if (self._models_cache is not None and 
            current_time - self._models_cache_time < self._cache_duration):
            return self._models_cache
            
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            if response.status_code == 200:
                data = response.json()
                all_models = [model['name'] for model in data.get('models', [])]
                # Filter out cloud models (those ending with '-cloud')
                local_models = [model for model in all_models if not model.endswith('-cloud')]
                
                # Update cache
                self._models_cache = local_models
                self._models_cache_time = current_time
                return local_models
        except:
            pass
        return []
    
    def describe_image(self, image_path: str, prompt: str, model: str) -> str:
        """Generate description using Ollama"""
        try:
            # Read and encode image
            with open(image_path, 'rb') as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Prepare request
            payload = {
                "model": model,
                "prompt": prompt,
                "images": [image_data],
                "stream": False
            }
            
            # Make request
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json().get('response', 'No description generated')
            else:
                return f"Error: HTTP {response.status_code}"
                
        except Exception as e:
            return f"Error generating description: {str(e)}"


class OpenAIProvider(AIProvider):
    """OpenAI provider for GPT models"""
    
    def __init__(self, api_key: Optional[str] = None):
        # Try multiple sources for API key in order of preference:
        # 1. Explicitly passed key
        # 2. Environment variable  
        # 3. openai.txt file in current directory
        self.api_key = api_key or os.getenv('OPENAI_API_KEY') or self._load_api_key_from_file()
        self.base_url = "https://api.openai.com/v1"
        self.timeout = 300
    
    def _load_api_key_from_file(self) -> Optional[str]:
        """Load API key from openai.txt file"""
        try:
            with open('openai.txt', 'r') as f:
                api_key = f.read().strip()
                return api_key if api_key else None
        except (FileNotFoundError, IOError):
            return None
    
    def get_provider_name(self) -> str:
        return "OpenAI"
    
    def is_available(self) -> bool:
        """Check if OpenAI is available (has API key from env var or openai.txt file)"""
        return bool(self.api_key)
    
    def get_available_models(self) -> List[str]:
        """Get list of available OpenAI models"""
        # DEVELOPMENT MODE: Return hardcoded models for faster testing
        if DEV_MODE_HARDCODED_MODELS:
            return DEV_OPENAI_MODELS.copy() if self.is_available() else []
        
        # ORIGINAL DETECTION CODE (preserved for when dev mode is disabled)
        if not self.is_available():
            return []
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(
                f"{self.base_url}/models",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                # Filter for vision-capable models
                vision_models = [
                    model['id'] for model in data.get('data', [])
                    if 'vision' in model['id'] or model['id'].startswith('gpt-4')
                ]
                return sorted(vision_models)
        except:
            pass
        
        # Fallback to known vision models
        return ['gpt-4-vision-preview', 'gpt-4o', 'gpt-4o-mini']
    
    def describe_image(self, image_path: str, prompt: str, model: str) -> str:
        """Generate description using OpenAI"""
        if not self.is_available():
            return "Error: OpenAI API key not configured"
        
        try:
            # Read and encode image
            with open(image_path, 'rb') as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Prepare request
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 1000
            }
            
            # Make request
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return data['choices'][0]['message']['content']
            else:
                return f"Error: HTTP {response.status_code} - {response.text}"
                
        except Exception as e:
            return f"Error generating description: {str(e)}"


class ClaudeProvider(AIProvider):
    """Anthropic Claude provider for Claude models"""
    
    def __init__(self, api_key: Optional[str] = None):
        # Try multiple sources for API key in order of preference:
        # 1. Explicitly passed key
        # 2. Environment variable  
        # 3. claude.txt file in current directory
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY') or self._load_api_key_from_file()
        self.base_url = "https://api.anthropic.com/v1"
        self.timeout = 300
        self.api_version = "2023-06-01"  # Anthropic API version
    
    def _load_api_key_from_file(self) -> Optional[str]:
        """Load API key from claude.txt file in current directory only"""
        try:
            with open('claude.txt', 'r') as f:
                api_key = f.read().strip()
                return api_key if api_key else None
        except (FileNotFoundError, IOError):
            return None
    
    def get_provider_name(self) -> str:
        return "Claude"
    
    def is_available(self) -> bool:
        """Check if Claude is available (has API key from env var or claude.txt file)"""
        return bool(self.api_key)
    
    def get_available_models(self) -> List[str]:
        """Get list of available Claude models"""
        # DEVELOPMENT MODE: Return hardcoded models for faster testing
        if DEV_MODE_HARDCODED_MODELS:
            return DEV_CLAUDE_MODELS.copy() if self.is_available() else []
        
        # ORIGINAL DETECTION CODE (preserved for when dev mode is disabled)
        if not self.is_available():
            return []
        
        # Claude doesn't have a models endpoint, so we return the known models
        # All Claude models support vision natively
        return DEV_CLAUDE_MODELS.copy()
    
    def describe_image(self, image_path: str, prompt: str, model: str) -> str:
        """Generate description using Claude"""
        if not self.is_available():
            return "Error: Claude API key not configured"
        
        try:
            # Read and encode image
            with open(image_path, 'rb') as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Determine media type from file extension
            ext = Path(image_path).suffix.lower()
            media_type_map = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.webp': 'image/webp'
            }
            media_type = media_type_map.get(ext, 'image/jpeg')
            
            # Prepare request (Anthropic Messages API format)
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": self.api_version,
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": model,
                "max_tokens": 1024,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_data
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            }
            
            # Make request
            response = requests.post(
                f"{self.base_url}/messages",
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                # Extract text from content array
                content = data.get('content', [])
                if content and len(content) > 0:
                    return content[0].get('text', '')
                return "Error: No content in response"
            else:
                return f"Error: HTTP {response.status_code} - {response.text}"
                
        except Exception as e:
            return f"Error generating description: {str(e)}"


class OllamaCloudProvider(AIProvider):
    """Ollama Cloud provider for large cloud-hosted models"""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.timeout = 300  # 5 minutes timeout for cloud models
        self._models_cache = None
        self._models_cache_time = 0
        self._cache_duration = 30  # Cache for 30 seconds
        self.cloud_models = [
            "qwen3-coder:480b-cloud",
            "gpt-oss:120b-cloud", 
            "gpt-oss:20b-cloud",
            "deepseek-v3.1:671b-cloud"
        ]
    
    def get_provider_name(self) -> str:
        return "Ollama Cloud"
    
    def is_available(self) -> bool:
        """Check if Ollama is available and user is signed in for cloud models"""
        try:
            # First check if Ollama is running
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code != 200:
                return False
            
            # Check if any cloud models are available (indicating user is signed in)
            data = response.json()
            available_models = [model['name'] for model in data.get('models', [])]
            
            # Check if any of our known cloud models are present
            for cloud_model in self.cloud_models:
                if cloud_model in available_models:
                    return True
            
            return False
            
        except:
            return False
    
    def get_available_models(self) -> List[str]:
        """Get list of available Ollama cloud models"""
        # DEVELOPMENT MODE: Return hardcoded models for faster testing
        if DEV_MODE_HARDCODED_MODELS:
            return DEV_OLLAMA_CLOUD_MODELS.copy()
        
        # ORIGINAL DETECTION CODE (preserved for when dev mode is disabled)
        # Check cache first
        current_time = time.time()
        if (self._models_cache is not None and 
            current_time - self._models_cache_time < self._cache_duration):
            return self._models_cache
            
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            if response.status_code == 200:
                data = response.json()
                available_models = [model['name'] for model in data.get('models', [])]
                
                # Filter for cloud models only
                cloud_models = [model for model in available_models if model.endswith('-cloud')]
                
                # Update cache
                self._models_cache = cloud_models
                self._models_cache_time = current_time
                return cloud_models
        except:
            pass
        return []
    
    def describe_image(self, image_path: str, prompt: str, model: str) -> str:
        """Generate description using Ollama Cloud - NOTE: Vision not supported yet"""
        # Cloud models don't support vision yet (as of Sep 2025)
        return f"⚠️ Ollama Cloud model '{model}' doesn't support vision capabilities yet.\n\n" \
               f"💡 Try these local vision models instead:\n" \
               f"• llava:latest (7B parameters)\n" \
               f"• llava-llama3:latest (8B parameters)\n" \
               f"• bakllava:latest (7B parameters)\n" \
               f"• moondream:latest (1.8B parameters)\n\n" \
               f"Cloud models are excellent for text-only tasks but vision support is coming soon!"


# Try to import ONNX Runtime (optional dependency)
try:
    import onnxruntime as ort
    import numpy as np
    HAS_ONNX = True
except ImportError:
    ort = None
    np = None
    HAS_ONNX = False

from pathlib import Path
import platform
import subprocess




# Global provider instances
_ollama_provider = OllamaProvider()
_ollama_cloud_provider = OllamaCloudProvider()
_openai_provider = OpenAIProvider()
_claude_provider = ClaudeProvider()


def get_available_providers() -> Dict[str, AIProvider]:
    """Get all available AI providers"""
    providers = {}
    
    if _ollama_provider.is_available():
        providers['ollama'] = _ollama_provider
    
    if _ollama_cloud_provider.is_available():
        providers['ollama_cloud'] = _ollama_cloud_provider
    
    if _openai_provider.is_available():
        providers['openai'] = _openai_provider
    
    if _claude_provider.is_available():
        providers['claude'] = _claude_provider
    
    return providers


def get_all_providers() -> Dict[str, AIProvider]:
    """Get all AI providers (available and unavailable)"""
    return {
        'ollama': _ollama_provider,
        'ollama_cloud': _ollama_cloud_provider,
        'openai': _openai_provider,
        'claude': _claude_provider
    }