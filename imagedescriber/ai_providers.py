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
        """Load API key from claude.txt file - checks multiple locations"""
        # Check multiple common locations
        possible_paths = [
            'claude.txt',  # Current directory
            os.path.expanduser('~/claude.txt'),  # Home directory
            os.path.expanduser('~/onedrive/claude.txt'),  # OneDrive
            os.path.join(os.path.expanduser('~'), 'OneDrive', 'claude.txt'),  # OneDrive (capitalized)
        ]
        
        for path in possible_paths:
            try:
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        api_key = f.read().strip()
                        if api_key:
                            return api_key
            except (FileNotFoundError, IOError):
                continue
        
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



class ObjectDetectionProvider(AIProvider):
    """Pure object detection provider using YOLO without additional AI processing"""
    
    def __init__(self):
        self.yolo_model = None
        self.yolo_available = False
        self._yolo_initialized = False  # Track if we've attempted initialization
        # Don't initialize YOLO on import - do it lazily when needed
        # self._initialize_yolo_detection()
    
    def _ensure_yolo_initialized(self):
        """Lazy initialization of YOLO - only loads when actually needed"""
        if self._yolo_initialized:
            return  # Already attempted initialization
        
        self._yolo_initialized = True
        self._initialize_yolo_detection()
    
    def _initialize_yolo_detection(self):
        """Initialize YOLO for object detection"""
        try:
            from ultralytics import YOLO
            # Try to load YOLOv8 extra-large model (most accurate), fallback to nano if needed
            try:
                print("ObjectDetection: Loading YOLOv8x (most accurate model)...")
                self.yolo_model = YOLO('yolov8x.pt')
                self.yolo_model.model_name = 'yolov8x.pt'  # Store model name for reference
                print("ObjectDetection: YOLO v8x initialized for pure object detection")
            except (Exception, KeyboardInterrupt) as e:
                print(f"ObjectDetection: YOLOv8x download failed, falling back to YOLOv8n: {e}")
                self.yolo_model = YOLO('yolov8n.pt')
                self.yolo_model.model_name = 'yolov8n.pt'  # Store model name for reference
                print("ObjectDetection: YOLO v8n initialized for fast object detection")
            
            self.yolo_available = True
        except ImportError:
            self.yolo_model = None
            self.yolo_available = False
            print("ObjectDetection: YOLO not available (pip install ultralytics)")
        except Exception as e:
            self.yolo_model = None
            self.yolo_available = False
            print(f"ObjectDetection: YOLO initialization failed: {e}")
    
    def _get_object_location(self, bbox, img_width, img_height):
        """Determine spatial location of object in image"""
        x1, y1, x2, y2 = bbox
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        
        # Determine horizontal position
        if center_x < img_width * 0.33:
            h_pos = "left"
        elif center_x > img_width * 0.67:
            h_pos = "right"
        else:
            h_pos = "center"
        
        # Determine vertical position
        if center_y < img_height * 0.33:
            v_pos = "top"
        elif center_y > img_height * 0.67:
            v_pos = "bottom"
        else:
            v_pos = "middle"
        
        return f"{v_pos}-{h_pos}"
    
    def _get_object_size(self, bbox, img_width, img_height):
        """Determine relative size of object in image"""
        x1, y1, x2, y2 = bbox
        obj_width = x2 - x1
        obj_height = y2 - y1
        obj_area = obj_width * obj_height
        img_area = img_width * img_height
        area_ratio = obj_area / img_area
        
        if area_ratio > 0.3:
            return "large"
        elif area_ratio > 0.1:
            return "medium"
        elif area_ratio > 0.02:
            return "small"
        else:
            return "tiny"
    
    def get_provider_name(self) -> str:
        return "Object Detection"
    
    def is_available(self) -> bool:
        """Check if YOLO is available for object detection"""
        return self.yolo_available
    
    def get_available_models(self) -> List[str]:
        """Get list of available detection modes"""
        if not self.yolo_available:
            return [
                "YOLO not available - Install with: pip install ultralytics"
            ]
        
        # Return actual model names that can be selected
        model_name = getattr(self.yolo_model, 'model_name', 'yolov8x.pt')
        return [
            f"YOLOv8 Standard Detection ({model_name})",
            f"YOLOv8 Spatial Analysis ({model_name})", 
            f"YOLOv8 Detailed Analysis ({model_name})",
            f"YOLOv8 Debug Mode ({model_name})"
        ]
    
    def describe_image(self, image_path: str, prompt: str, model: str, **kwargs) -> str:
        """Generate object detection results with configurable settings"""
        
        # Extract YOLO settings from kwargs (passed from ProcessingDialog)
        yolo_settings = kwargs.get('yolo_settings', {})
        confidence_threshold = yolo_settings.get('confidence_threshold', 0.10)
        max_objects = yolo_settings.get('max_objects', 20)
        preferred_model = yolo_settings.get('yolo_model', 'yolov8x.pt')
        
        # Handle info/error messages - check for model names without YOLOv8 prefix
        if "not available" in model or not model.startswith("YOLOv8"):
            return "Please select an object detection mode above."
        
        # Lazy initialization: only load YOLO when actually needed
        self._ensure_yolo_initialized()
        
        if not self.yolo_available or not self.yolo_model:
            return ("YOLO object detection not available.\n\n"
                   "Install with: pip install ultralytics\n\n"
                   "This will automatically download YOLOv8 models for object detection.")
        
        try:
            print(f"Running YOLO object detection: {model}")
            print(f"🔧 Settings: confidence={confidence_threshold:.2f}, max_objects={max_objects}, model={preferred_model}")
            
            # Switch YOLO model if user selected a different one
            current_model_name = getattr(self.yolo_model, 'model_name', 'yolov8x.pt')
            if preferred_model != current_model_name:
                print(f"🔄 Switching from {current_model_name} to {preferred_model}...")
                try:
                    from ultralytics import YOLO
                    self.yolo_model = YOLO(preferred_model)
                    self.yolo_model.model_name = preferred_model  # Store for future reference
                    print(f"✅ Successfully loaded {preferred_model}")
                except Exception as e:
                    print(f"⚠️ Failed to load {preferred_model}, using current model: {e}")
            
            # Run YOLO detection with user-configured settings
            print("🔍 Running YOLO detection with user settings...")
            results = self.yolo_model(image_path, verbose=True, conf=confidence_threshold)
            
            # Get image dimensions
            from PIL import Image
            with Image.open(image_path) as img:
                img_width, img_height = img.size
            
            print(f"📐 Image dimensions: {img_width}×{img_height}px")
            
            # Collect detected objects with user-configurable filtering
            detected_objects = []
            total_detections = 0
            min_filter_confidence = max(0.01, confidence_threshold * 0.5)  # Filter at half the detection threshold
            
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    total_detections += len(boxes)
                    print(f"📊 YOLO found {len(boxes)} raw detections")
                    
                    for i, box in enumerate(boxes):
                        conf = float(box.conf[0])
                        cls_id = int(box.cls[0])
                        name = self.yolo_model.names[cls_id]
                        bbox = box.xyxy[0].tolist()  # [x1, y1, x2, y2]
                        
                        print(f"  Detection {i+1}: {name} ({conf:.3f} confidence)")
                        
                        # Use user-configured filtering threshold
                        if conf > min_filter_confidence:
                            # Calculate spatial information
                            location = self._get_object_location(bbox, img_width, img_height)
                            size = self._get_object_size(bbox, img_width, img_height)
                            
                            detected_objects.append({
                                'name': name,
                                'confidence': conf * 100,
                                'bbox': bbox,
                                'location': location,
                                'size': size
                            })
                        else:
                            print(f"    ↳ Filtered out (confidence {conf:.3f} < {min_filter_confidence:.3f})")
                        
                        # Stop if we've reached the max objects limit
                        if len(detected_objects) >= max_objects:
                            print(f"🛑 Reached maximum objects limit ({max_objects})")
                            break
                    
                    # Break outer loop too if max reached
                    if len(detected_objects) >= max_objects:
                        break
            
            print(f"🎯 Total raw detections: {total_detections}")
            print(f"✅ Objects after filtering: {len(detected_objects)}")
            
            # Sort by confidence
            detected_objects = sorted(detected_objects, key=lambda x: x['confidence'], reverse=True)
            
            print(f"🔍 Final YOLO results: {len(detected_objects)} objects detected")
            
            # Format output based on selected model
            if "Object Detection Only" in model:
                return self._format_simple_detection(detected_objects)
            elif "Object + Spatial Detection" in model:
                return self._format_spatial_detection(detected_objects)
            elif "Detailed Object Analysis" in model:
                return self._format_detailed_analysis(detected_objects, img_width, img_height)
            elif "Debug Mode" in model:
                return self._format_debug_analysis(detected_objects, total_detections, img_width, img_height)
            else:
                return self._format_spatial_detection(detected_objects)  # Default
                
        except Exception as e:
            return f"Object detection failed: {str(e)}\n\nMake sure ultralytics is installed: pip install ultralytics"
    
    def _format_simple_detection(self, objects):
        """Format simple object list"""
        if not objects:
            return "No objects detected in this image."
        
        result = f"🎯 OBJECT DETECTION RESULTS\n"
        result += f"Found {len(objects)} objects:\n\n"
        
        for i, obj in enumerate(objects[:20], 1):  # Top 20 objects
            result += f"{i:2d}. {obj['name']} ({obj['confidence']:.1f}%)\n"
        
        return result
    
    def _format_spatial_detection(self, objects):
        """Format objects with spatial information"""
        if not objects:
            return "No objects detected in this image."
        
        result = f"📍 OBJECT + SPATIAL DETECTION RESULTS\n"
        result += f"Found {len(objects)} objects with locations:\n\n"
        
        for i, obj in enumerate(objects[:15], 1):  # Top 15 with spatial data
            result += f"{i:2d}. {obj['name']} ({obj['confidence']:.1f}%) - {obj['size']}, {obj['location']}\n"
        
        if len(objects) > 15:
            result += f"\n... and {len(objects) - 15} more objects detected"
        
        return result
    
    def _format_detailed_analysis(self, objects, img_width, img_height):
        """Format detailed analysis with bounding boxes"""
        if not objects:
            return "No objects detected in this image."
        
        result = f"🔍 DETAILED OBJECT ANALYSIS\n"
        result += f"Image dimensions: {img_width}×{img_height}px\n"
        result += f"Found {len(objects)} objects:\n\n"
        
        for i, obj in enumerate(objects[:10], 1):  # Top 10 with full details
            bbox = obj['bbox']
            x1, y1, x2, y2 = bbox
            width = x2 - x1
            height = y2 - y1
            
            result += f"{i:2d}. {obj['name']}\n"
            result += f"    Confidence: {obj['confidence']:.1f}%\n"
            result += f"    Size: {obj['size']} ({width:.0f}×{height:.0f}px)\n"
            result += f"    Location: {obj['location']}\n"
            result += f"    Bounding box: ({x1:.0f}, {y1:.0f}) to ({x2:.0f}, {y2:.0f})\n\n"
        
        if len(objects) > 10:
            result += f"... and {len(objects) - 10} more objects detected\n"
        
        # Add summary statistics
        result += f"\n📊 DETECTION SUMMARY:\n"
        result += f"Total objects: {len(objects)}\n"
        result += f"High confidence (>80%): {len([o for o in objects if o['confidence'] > 80])}\n"
        result += f"Medium confidence (50-80%): {len([o for o in objects if 50 <= o['confidence'] <= 80])}\n"
        result += f"Low confidence (15-50%): {len([o for o in objects if 15 <= o['confidence'] < 50])}\n"
        
        # Most common objects
        object_counts = {}
        for obj in objects:
            object_counts[obj['name']] = object_counts.get(obj['name'], 0) + 1
        
        most_common = sorted(object_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        if most_common:
            result += f"\nMost common objects: {', '.join([f'{name} ({count})' for name, count in most_common])}"
        
        return result
    
    def _format_debug_analysis(self, objects, total_raw_detections, img_width, img_height):
        """Format comprehensive debug analysis"""
        result = f"🔧 DEBUG MODE - COMPREHENSIVE YOLO ANALYSIS\n"
        result += f"Image dimensions: {img_width}×{img_height}px\n"
        result += f"Raw YOLO detections: {total_raw_detections}\n"
        result += f"Objects after filtering: {len(objects)}\n\n"
        
        if not objects:
            result += "❌ NO OBJECTS DETECTED\n\n"
            result += "Possible reasons:\n"
            result += "• Image contains objects YOLO wasn't trained on\n"
            result += "• Objects are too small, blurry, or occluded\n"
            result += "• Lighting/contrast issues\n"
            result += "• YOLO model may not recognize artistic objects (statues, etc.)\n"
            result += "• Try different YOLO model (yolov8s, yolov8m) if available\n"
            return result
        
        # Show ALL detected objects with full details
        result += "🎯 ALL DETECTED OBJECTS (sorted by confidence):\n"
        for i, obj in enumerate(objects, 1):
            bbox = obj['bbox']
            x1, y1, x2, y2 = bbox
            width = x2 - x1
            height = y2 - y1
            area_pct = (width * height) / (img_width * img_height) * 100
            
            result += f"\n{i:2d}. {obj['name'].upper()}\n"
            result += f"    📊 Confidence: {obj['confidence']:.2f}%\n"
            result += f"    📐 Size: {obj['size']} ({width:.0f}×{height:.0f}px = {area_pct:.1f}% of image)\n"
            result += f"    📍 Location: {obj['location']}\n"
            result += f"    🎯 Bounding box: ({x1:.0f}, {y1:.0f}) → ({x2:.0f}, {y2:.0f})\n"
            
            # Add confidence assessment
            if obj['confidence'] > 80:
                result += f"    ✅ High confidence detection\n"
            elif obj['confidence'] > 50:
                result += f"    ⚠️  Medium confidence detection\n"
            elif obj['confidence'] > 20:
                result += f"    🔍 Low confidence detection\n"
            else:
                result += f"    ❓ Very low confidence detection\n"
        
        # Add comprehensive statistics
        result += f"\n📈 DETECTION STATISTICS:\n"
        result += f"Total objects: {len(objects)}\n"
        result += f"Confidence distribution:\n"
        result += f"  • >80%: {len([o for o in objects if o['confidence'] > 80])} objects\n"
        result += f"  • 50-80%: {len([o for o in objects if 50 <= o['confidence'] <= 80])} objects\n"
        result += f"  • 20-50%: {len([o for o in objects if 20 <= o['confidence'] < 50])} objects\n"
        result += f"  • 5-20%: {len([o for o in objects if 5 <= o['confidence'] < 20])} objects\n"
        
        # Size distribution
        result += f"Size distribution:\n"
        result += f"  • Large: {len([o for o in objects if o['size'] == 'large'])} objects\n"
        result += f"  • Medium: {len([o for o in objects if o['size'] == 'medium'])} objects\n"
        result += f"  • Small: {len([o for o in objects if o['size'] == 'small'])} objects\n"
        result += f"  • Tiny: {len([o for o in objects if o['size'] == 'tiny'])} objects\n"
        
        # Object types
        object_counts = {}
        for obj in objects:
            object_counts[obj['name']] = object_counts.get(obj['name'], 0) + 1
        
        most_common = sorted(object_counts.items(), key=lambda x: x[1], reverse=True)
        result += f"Object types: {', '.join([f'{name}({count})' for name, count in most_common])}\n"
        
        # Add YOLO model info
        result += f"\n🤖 YOLO MODEL INFO:\n"
        result += f"Model type: YOLOv8 (probably yolov8x.pt or yolov8n.pt)\n"
        result += f"Detection threshold: 5% confidence minimum\n"
        result += f"Trained classes: {len(self.yolo_model.names)} total COCO classes\n"
        
        # Add suggestions
        result += f"\n💡 SUGGESTIONS:\n"
        if len(objects) < 3:
            result += f"• Try lowering confidence threshold further\n"
            result += f"• Check if objects are in YOLO's training classes\n"
            result += f"• Museum artifacts may not be well-represented in COCO dataset\n"
        
        if any(obj['confidence'] < 30 for obj in objects):
            result += f"• Low confidence suggests challenging detection conditions\n"
            result += f"• Consider better lighting or different angle\n"
        
        return result


class GroundingDINOProvider(AIProvider):
    """
    Text-prompted zero-shot object detection using GroundingDINO.
    
    Unlike YOLO (limited to 80 classes), GroundingDINO can detect ANY object
    you describe in natural language:
    - "red cars"
    - "people wearing hats"
    - "safety equipment"
    - "damaged items"
    - "text and signs"
    
    Supports both automatic comprehensive scanning and custom user queries.
    """
    
    def __init__(self):
        self.model = None
        self.processor = None
        self.device = None
        self.grounding_dino_available = False
        
        # Default detection prompts for different scenarios
        self.default_prompts = {
            'comprehensive': "objects . people . animals . vehicles . furniture . electronics . plants . text . signs",
            'indoor': "people . furniture . electronics . decorations . appliances . lighting . windows . doors . text",
            'outdoor': "people . vehicles . buildings . trees . sky . roads . signs . animals . landscape . nature",
            'workplace': "people . computers . desks . chairs . equipment . safety gear . tools . machinery . monitors",
            'safety': "fire extinguisher . exit signs . safety equipment . hazards . emergency lights . first aid . warning signs",
            'retail': "products . shelves . people . checkout . displays . signage . packaging . prices . carts",
            'document': "text . logos . diagrams . tables . images . signatures . stamps . barcodes . headings"
        }
        
        # Check availability
        try:
            import groundingdino
            from groundingdino.util.inference import Model as GroundingDINOModel
            self.grounding_dino_available = True
        except ImportError:
            self.grounding_dino_available = False
    
    def get_provider_name(self) -> str:
        return "GroundingDINO"
    
    def is_available(self) -> bool:
        return self.grounding_dino_available
    
    def get_available_models(self) -> List[str]:
        """Return available detection modes"""
        if not self.grounding_dino_available:
            return []
        
        return [
            "Comprehensive Detection (Auto)",
            "Indoor Scene Detection",
            "Outdoor Scene Detection",
            "Workplace Safety Detection",
            "Retail/Store Detection",
            "Document/Text Detection",
            "Custom Query (User-Defined)"
        ]
    
    def _load_model(self):
        """Load GroundingDINO model"""
        if self.model is not None:
            return self.model
        
        try:
            import groundingdino
            from groundingdino.util.inference import Model as GroundingDINOModel
            import torch
            import urllib.request
            
            # Determine device
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            
            # Get absolute path to config file in the installed package
            package_path = os.path.dirname(groundingdino.__file__)
            config_path = os.path.join(package_path, "config", "GroundingDINO_SwinT_OGC.py")
            
            # Set up checkpoint path in torch hub cache
            cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "torch", "hub", "checkpoints")
            os.makedirs(cache_dir, exist_ok=True)
            checkpoint_path = os.path.join(cache_dir, "groundingdino_swint_ogc.pth")
            
            # Download checkpoint from GitHub if not already cached (~700MB on first use)
            if not os.path.exists(checkpoint_path):
                checkpoint_url = "https://github.com/IDEA-Research/GroundingDINO/releases/download/v0.1.0-alpha/groundingdino_swint_ogc.pth"
                print(f"Downloading GroundingDINO model (~700MB)...")
                print(f"This is a one-time download, will be cached at: {checkpoint_path}")
                urllib.request.urlretrieve(checkpoint_url, checkpoint_path)
                print("Download complete!")
            
            # Initialize model
            self.model = GroundingDINOModel(
                model_config_path=config_path,
                model_checkpoint_path=checkpoint_path,
                device=self.device
            )
            
            return self.model
            
        except Exception as e:
            raise RuntimeError(f"Failed to load GroundingDINO model: {str(e)}")
    
    def _get_detection_prompt(self, model: str, custom_query: str = None) -> str:
        """Get the appropriate detection prompt based on model/mode"""
        if custom_query:
            return custom_query
        
        # Map model selection to prompt
        model_lower = model.lower()
        if "comprehensive" in model_lower or "auto" in model_lower:
            return self.default_prompts['comprehensive']
        elif "indoor" in model_lower:
            return self.default_prompts['indoor']
        elif "outdoor" in model_lower:
            return self.default_prompts['outdoor']
        elif "workplace" in model_lower or "safety" in model_lower:
            return self.default_prompts['workplace']
        elif "retail" in model_lower or "store" in model_lower:
            return self.default_prompts['retail']
        elif "document" in model_lower or "text" in model_lower:
            return self.default_prompts['document']
        else:
            return self.default_prompts['comprehensive']
    
    def _describe_location(self, box, image_width, image_height) -> str:
        """Describe where the object is located in the image"""
        x_center = (box[0] + box[2]) / 2
        y_center = (box[1] + box[3]) / 2
        
        # Normalize to 0-1
        x_norm = x_center / image_width
        y_norm = y_center / image_height
        
        # Vertical position
        if y_norm < 0.33:
            v_pos = "top"
        elif y_norm < 0.67:
            v_pos = "middle"
        else:
            v_pos = "bottom"
        
        # Horizontal position
        if x_norm < 0.33:
            h_pos = "left"
        elif x_norm < 0.67:
            h_pos = "center"
        else:
            h_pos = "right"
        
        return f"{v_pos}-{h_pos}"
    
    def _calculate_size(self, box, image_width, image_height) -> str:
        """Determine relative size of detected object"""
        width = box[2] - box[0]
        height = box[3] - box[1]
        area = (width * height) / (image_width * image_height)
        
        if area > 0.3:
            return "large"
        elif area > 0.1:
            return "medium"
        else:
            return "small"
    
    def describe_image(self, image_path: str, prompt: str, model: str, **kwargs) -> str:
        """
        Detect objects in image using text prompts.
        
        Args:
            image_path: Path to image file
            prompt: User's description prompt (used for context in results)
            model: Detection mode (Comprehensive, Indoor, Custom, etc.)
            **kwargs: Additional parameters
                - custom_query: Custom detection query string
                - box_threshold: Confidence threshold (default 0.35)
                - text_threshold: Text matching threshold (default 0.25)
                - return_detections: Return raw detection data (default False)
        """
        try:
            # Load model
            if self.model is None:
                self.model = self._load_model()
            
            # Get custom query from kwargs
            custom_query = kwargs.get('custom_query', None)
            box_threshold = kwargs.get('box_threshold', 0.35)
            text_threshold = kwargs.get('text_threshold', 0.25)
            return_detections = kwargs.get('return_detections', False)
            
            # Determine detection prompt
            detection_prompt = self._get_detection_prompt(model, custom_query)
            
            # Load and prepare image
            from PIL import Image
            import numpy as np
            
            image = Image.open(image_path)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            image_np = np.array(image)
            image_width, image_height = image.size
            
            # Run detection
            detections = self.model.predict_with_classes(
                image=image_np,
                classes=detection_prompt.split(' . '),
                box_threshold=box_threshold,
                text_threshold=text_threshold
            )
            
            # Parse detections
            results = []
            if detections is not None:
                boxes = detections.xyxy  # [x1, y1, x2, y2] format
                confidences = detections.confidence
                class_ids = detections.class_id
                labels = [detection_prompt.split(' . ')[int(id)] for id in class_ids]
                
                for box, conf, label in zip(boxes, confidences, labels):
                    location = self._describe_location(box, image_width, image_height)
                    size = self._calculate_size(box, image_width, image_height)
                    
                    results.append({
                        'label': label.strip(),
                        'confidence': float(conf),
                        'box': box.tolist(),
                        'location': location,
                        'size': size
                    })
            
            # Return raw detections if requested (for hybrid providers)
            if return_detections:
                return results
            
            # Format results as human-readable description
            return self._format_detection_results(results, detection_prompt, custom_query)
            
        except Exception as e:
            return f"GroundingDINO detection failed: {str(e)}\n\nTroubleshooting:\n" \
                   f"1. Install: pip install groundingdino-py\n" \
                   f"2. Model will auto-download on first use (~700MB)\n" \
                   f"3. GPU recommended but CPU works (slower)\n" \
                   f"4. Check image is valid: {image_path}"
    
    def _format_detection_results(self, results: List[dict], prompt: str, custom_query: str = None) -> str:
        """Format detection results as readable text"""
        if not results:
            query_text = custom_query if custom_query else prompt
            return f"No objects detected matching query: '{query_text}'\n\n" \
                   f"Try adjusting:\n" \
                   f"- Query terms (be more general or specific)\n" \
                   f"- Confidence threshold (lower to find more)\n" \
                   f"- Image quality (better lighting, clearer view)"
        
        # Group by label
        grouped = {}
        for det in results:
            label = det['label']
            if label not in grouped:
                grouped[label] = []
            grouped[label].append(det)
        
        # Build output
        output = "GroundingDINO Detection Results\n"
        output += "=" * 60 + "\n\n"
        
        if custom_query:
            output += f"Query: '{custom_query}'\n\n"
        
        output += f"Summary: Found {len(results)} objects across {len(grouped)} categories\n\n"
        
        # List each category
        for label, detections in sorted(grouped.items(), key=lambda x: -len(x[1])):
            count = len(detections)
            avg_conf = sum(d['confidence'] for d in detections) / count
            
            output += f"{label.title()}: {count} instance(s) [avg confidence: {avg_conf:.1%}]\n"
            
            # Show details for each instance
            for i, det in enumerate(detections, 1):
                if count > 1:
                    output += f"  #{i}: "
                else:
                    output += f"  "
                output += f"Location: {det['location']}, "
                output += f"Size: {det['size']}, "
                output += f"Confidence: {det['confidence']:.1%}\n"
            
            output += "\n"
        
        return output


class GroundingDINOHybridProvider(AIProvider):
    """
    Hybrid provider combining GroundingDINO detection with Ollama descriptions.
    
    Workflow:
    1. GroundingDINO detects objects with text prompts
    2. Detection results passed to Ollama as context
    3. Ollama generates natural language description incorporating detections
    
    This combines precise object detection with natural language understanding.
    """
    
    def __init__(self):
        self.grounding_dino = GroundingDINOProvider()
        self.ollama = OllamaProvider()
    
    def get_provider_name(self) -> str:
        return "GroundingDINO + Ollama"
    
    def is_available(self) -> bool:
        return self.grounding_dino.is_available() and self.ollama.is_available()
    
    def get_available_models(self) -> List[str]:
        """Return Ollama models (detection mode is separate setting)"""
        if not self.is_available():
            return []
        
        return self.ollama.get_available_models()
    
    def describe_image(self, image_path: str, prompt: str, model: str, **kwargs) -> str:
        """
        Generate description using both GroundingDINO and Ollama.
        
        Args:
            image_path: Path to image
            prompt: User's description prompt
            model: Ollama model to use
            **kwargs: Additional parameters
                - detection_mode: Which GroundingDINO mode (default: "Comprehensive Detection (Auto)")
                - custom_query: Custom detection query
                - box_threshold: Detection confidence threshold
        """
        try:
            # Step 1: Run GroundingDINO detection
            detection_mode = kwargs.get('detection_mode', "Comprehensive Detection (Auto)")
            custom_query = kwargs.get('custom_query', None)
            box_threshold = kwargs.get('box_threshold', 0.35)
            
            # Get raw detections
            detections = self.grounding_dino.describe_image(
                image_path=image_path,
                prompt=prompt,
                model=detection_mode,
                custom_query=custom_query,
                box_threshold=box_threshold,
                return_detections=True  # Get structured data, not formatted text
            )
            
            # Step 2: Format detection summary for Ollama
            detection_summary = self._format_detections_for_ollama(detections, custom_query)
            
            # Step 3: Enhance prompt with detection context
            enhanced_prompt = f"""{prompt}

DETECTED OBJECTS:
{detection_summary}

Please provide a comprehensive description that incorporates these detected objects. Describe the scene naturally, mentioning where things are located and how they relate to each other."""
            
            # Step 4: Get description from Ollama
            try:
                description = self.ollama.describe_image(
                    image_path=image_path,
                    prompt=enhanced_prompt,
                    model=model
                )
                
                # Check if Ollama returned an error
                if description.startswith("Error:"):
                    description += f"\n\nDebug info:\n" \
                                 f"- Model requested: {model}\n" \
                                 f"- Ollama URL: {self.ollama.base_url}\n" \
                                 f"- Try: Verify Ollama is running and model '{model}' is installed\n" \
                                 f"- Available models: {', '.join(self.ollama.get_available_models()[:5])}"
            except Exception as ollama_error:
                description = f"Error: {str(ollama_error)}\n\n" \
                            f"Debug info:\n" \
                            f"- Model requested: {model}\n" \
                            f"- Ollama URL: {self.ollama.base_url}"
            
            # Step 5: Combine results
            result = "🔍 GroundingDINO + Ollama Analysis\n"
            result += "=" * 60 + "\n\n"
            result += f"📊 Detection Summary ({len(detections)} objects found):\n"
            result += self._format_detection_list(detections)
            result += "\n\n"
            result += "📝 Detailed Description:\n"
            result += description
            
            return result
            
        except Exception as e:
            return f"Hybrid detection failed: {str(e)}\n\n" \
                   f"Troubleshooting:\n" \
                   f"• Ensure GroundingDINO is installed: pip install groundingdino-py\n" \
                   f"• Ensure Ollama is running with a vision model\n" \
                   f"• Check image path is valid"
    
    def _format_detections_for_ollama(self, detections: List[dict], custom_query: str = None) -> str:
        """Format detections for Ollama context"""
        if not detections:
            return "No objects detected."
        
        # Group by label
        grouped = {}
        for det in detections:
            label = det['label']
            if label not in grouped:
                grouped[label] = []
            grouped[label].append(det)
        
        # Format concisely
        lines = []
        for label, dets in sorted(grouped.items(), key=lambda x: -len(x[1])):
            count = len(dets)
            locations = [d['location'] for d in dets]
            lines.append(f"- {label}: {count}x (at {', '.join(set(locations))})")
        
        return '\n'.join(lines)
    
    def _format_detection_list(self, detections: List[dict]) -> str:
        """Format detection list for display"""
        if not detections:
            return "None"
        
        # Group and count
        grouped = {}
        for det in detections:
            label = det['label']
            grouped[label] = grouped.get(label, 0) + 1
        
        # Format
        items = [f"{label}: {count}" for label, count in sorted(grouped.items(), key=lambda x: -x[1])]
        return ", ".join(items)


# Global provider instances
_ollama_provider = OllamaProvider()
_ollama_cloud_provider = OllamaCloudProvider()
_openai_provider = OpenAIProvider()
_claude_provider = ClaudeProvider()
_object_detection_provider = ObjectDetectionProvider()
_grounding_dino_provider = GroundingDINOProvider()
_grounding_dino_hybrid_provider = GroundingDINOHybridProvider()


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
    
    if _object_detection_provider.is_available():
        providers['object_detection'] = _object_detection_provider
    
    if _grounding_dino_provider.is_available():
        providers['grounding_dino'] = _grounding_dino_provider
    
    if _grounding_dino_hybrid_provider.is_available():
        providers['grounding_dino_hybrid'] = _grounding_dino_hybrid_provider
    
    return providers


def get_all_providers() -> Dict[str, AIProvider]:
    """Get all AI providers (available and unavailable)"""
    return {
        'ollama': _ollama_provider,
        'ollama_cloud': _ollama_cloud_provider,
        'openai': _openai_provider,
        'claude': _claude_provider,
        'object_detection': _object_detection_provider,
        'grounding_dino': _grounding_dino_provider,
        'grounding_dino_hybrid': _grounding_dino_hybrid_provider
    }