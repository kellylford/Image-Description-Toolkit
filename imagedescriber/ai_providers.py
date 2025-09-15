"""
AI Provider classes for Image Describer

This module contains all AI provider implementations including
Ollama, OpenAI, and HuggingFace providers.
"""

import os
import requests
import json
import base64
from typing import Dict, Optional, List, Any
from pathlib import Path
import time
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
        """Get list of available Ollama models"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            if response.status_code == 200:
                data = response.json()
                return [model['name'] for model in data.get('models', [])]
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
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.base_url = "https://api.openai.com/v1"
        self.timeout = 300
    
    def get_provider_name(self) -> str:
        return "OpenAI"
    
    def is_available(self) -> bool:
        """Check if OpenAI is available (has API key)"""
        return bool(self.api_key)
    
    def get_available_models(self) -> List[str]:
        """Get list of available OpenAI models"""
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


class HuggingFaceProvider(AIProvider):
    """HuggingFace provider for transformers models"""
    
    def __init__(self):
        self.available_models = []
        self._check_transformers()
    
    def _check_transformers(self):
        """Check if transformers library is available and load models"""
        try:
            from transformers import pipeline, BlipProcessor, BlipForConditionalGeneration
            self.has_transformers = True
            # Common vision models
            self.available_models = [
                "Salesforce/blip-image-captioning-base",
                "Salesforce/blip-image-captioning-large",
                "microsoft/git-base-coco",
                "nlpconnect/vit-gpt2-image-captioning"
            ]
        except ImportError:
            self.has_transformers = False
    
    def get_provider_name(self) -> str:
        return "HuggingFace"
    
    def is_available(self) -> bool:
        """Check if HuggingFace transformers is available"""
        return self.has_transformers
    
    def get_available_models(self) -> List[str]:
        """Get list of available HuggingFace models"""
        return self.available_models if self.has_transformers else []
    
    def describe_image(self, image_path: str, prompt: str, model: str) -> str:
        """Generate description using HuggingFace"""
        if not self.is_available():
            return "Error: HuggingFace transformers not available"
        
        try:
            from transformers import pipeline
            from PIL import Image
            
            # Load the model
            captioner = pipeline("image-to-text", model=model)
            
            # Open and process image
            image = Image.open(image_path)
            
            # Generate caption
            result = captioner(image)
            
            if result and len(result) > 0:
                return result[0].get('generated_text', 'No description generated')
            else:
                return 'No description generated'
                
        except Exception as e:
            return f"Error generating description: {str(e)}"


# Global provider instances
_ollama_provider = OllamaProvider()
_openai_provider = OpenAIProvider()
_huggingface_provider = HuggingFaceProvider()


def get_available_providers() -> Dict[str, AIProvider]:
    """Get all available AI providers"""
    providers = {}
    
    if _ollama_provider.is_available():
        providers['ollama'] = _ollama_provider
    
    if _openai_provider.is_available():
        providers['openai'] = _openai_provider
        
    if _huggingface_provider.is_available():
        providers['huggingface'] = _huggingface_provider
    
    return providers