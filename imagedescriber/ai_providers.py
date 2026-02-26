"""
AI Provider classes for Image Describer

This module contains all AI provider implementations including
Ollama, OpenAI, and HuggingFace providers.
"""

import os
import sys
import requests
import json
import base64
import time
import random
import functools
from typing import List, Dict, Optional
from pathlib import Path
import platform
import subprocess
import logging

# Import PIL for image processing (PNG to JPEG conversion)
try:
    from PIL import Image
    import io
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Add project root to sys.path for shared module imports
# Works in both development mode (running script) and frozen mode (PyInstaller exe)
if getattr(sys, 'frozen', False):
    # Frozen mode - executable directory is base
    _project_root = Path(sys.executable).parent
else:
    # Development mode - use __file__ relative path
    _project_root = Path(__file__).parent.parent

if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# Try to import Windows Runtime for Copilot+ PC support (Windows only)
try:
    import winrt
    from winrt.windows.ai.machinelearning import LearningModelDeviceKind
    HAS_WINRT = True and platform.system() == "Windows"
except ImportError:
    winrt = None
    LearningModelDeviceKind = None
    HAS_WINRT = False

# Try to import AI provider SDKs at module level (required for PyInstaller)
try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    anthropic = None
    HAS_ANTHROPIC = False

try:
    import openai
    HAS_OPENAI = True
except ImportError:
    openai = None
    HAS_OPENAI = False

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

# Import OpenAI models from central configuration
# IMPORTANT: DO NOT define models here - use models/openai_models.py as single source of truth
try:
    from models.openai_models import OPENAI_MODELS as DEV_OPENAI_MODELS
except ImportError:
    # Fallback if models package not available — verified working 2026-02-23
    DEV_OPENAI_MODELS = [
        "gpt-5.2",
        "gpt-5.1",
        "gpt-5",
        "gpt-5-mini",
        "gpt-5-nano",
        "o4-mini",
        "o3",
        "o1",
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4.1",
        "gpt-4.1-mini",
        "gpt-4.1-nano",
        # Removed: gpt-5.2-pro, gpt-5-pro (404), o3-mini, gpt-4-turbo (no vision),
        #          chatgpt-4o-latest (deprecated), o1-mini/o1-preview (deprecated)
    ]

# Import Claude models from central configuration
# IMPORTANT: DO NOT define models here - use models/claude_models.py as single source of truth
try:
    from models.claude_models import (
        CLAUDE_MODELS as DEV_CLAUDE_MODELS,
        CLAUDE_MODEL_METADATA,
        get_claude_model_info,
        format_claude_model_for_display,
        get_claude_api_id_from_display,
    )
except ImportError:
    # Fallback if models package not available
    DEV_CLAUDE_MODELS = [
        "claude-opus-4-6",
        "claude-sonnet-4-5-20250929",
        "claude-haiku-4-5-20251001",
    ]
    CLAUDE_MODEL_METADATA = {
        "claude-opus-4-6":           {"name": "Claude Opus 4.6"},
        "claude-sonnet-4-5-20250929": {"name": "Claude Sonnet 4.5"},
        "claude-haiku-4-5-20251001":  {"name": "Claude Haiku 4.5"},
    }
    def get_claude_model_info(model_id: str):
        return CLAUDE_MODEL_METADATA.get(model_id, {"name": model_id})
    def format_claude_model_for_display(model_id: str, include_description: bool = False) -> str:
        return CLAUDE_MODEL_METADATA.get(model_id, {}).get("name", model_id)
    def get_claude_api_id_from_display(display_name_or_id: str) -> str:
        for api_id, meta in CLAUDE_MODEL_METADATA.items():
            if meta.get("name") == display_name_or_id:
                return api_id
        return display_name_or_id


def sort_claude_models(models: List[str]) -> List[str]:
    """
    Sort Claude models by tier (haiku -> sonnet -> opus) then by version.
    
    This puts cheaper models first and groups by capability tier,
    making it easier for users to find the right model for their budget.
    """
    def get_sort_key(model: str) -> tuple:
        # Extract tier and version from model name
        # Examples: claude-haiku-4-5-20251001, claude-3-5-sonnet-20241022
        lower = model.lower()
        
        # Determine tier (lower number = shown first)
        if 'haiku' in lower:
            tier = 0
        elif 'sonnet' in lower:
            tier = 1
        elif 'opus' in lower:
            tier = 2
        else:
            tier = 3  # Unknown tier goes last
        
        # Extract version numbers for sorting within tier
        # claude-haiku-4-5 -> (4, 5)
        # claude-3-5-haiku -> (3, 5)
        import re
        version_match = re.search(r'(\d+)[-.](\d+)', model)
        if version_match:
            major = int(version_match.group(1))
            minor = int(version_match.group(2))
        else:
            major, minor = 0, 0
        
        # Sort by tier first, then by version descending (newer first)
        return (tier, -major, -minor, model)
    
    return sorted(models, key=get_sort_key)


def retry_on_api_error(max_retries=3, base_delay=1.0, max_delay=60.0, backoff_multiplier=2.0):
    """
    Retry decorator for API calls with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_multiplier: Multiplier for exponential backoff
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):  # +1 for initial attempt
                try:
                    result = func(*args, **kwargs)
                    
                    # Check if result indicates a retryable error
                    if isinstance(result, str) and result.startswith("Error:"):
                        # Extract status code if present
                        if "status code: 5" in result or "status code: 429" in result or "timeout" in result.lower():
                            if attempt < max_retries:
                                delay = min(base_delay * (backoff_multiplier ** attempt), max_delay)
                                # Add jitter to prevent thundering herd
                                jitter = random.uniform(0.1, 0.5) * delay
                                sleep_time = delay + jitter
                                
                                print(f"  [RETRY] Attempt {attempt + 1}/{max_retries + 1} failed, retrying in {sleep_time:.1f}s...")
                                time.sleep(sleep_time)
                                continue
                            else:
                                print(f"  [RETRY] All {max_retries + 1} attempts failed")
                                return result
                    
                    # Success or non-retryable error
                    if attempt > 0:
                        print(f"  [RETRY] Success on attempt {attempt + 1}")
                    return result
                    
                except Exception as e:
                    last_exception = e
                    
                    # Determine if error is retryable
                    error_type = type(e).__name__
                    error_msg = str(e).lower()
                    is_retryable = (
                        'timeout' in error_msg or
                        'connectionerror' in error_type.lower() or
                        'httperror' in error_type.lower() or
                        'ratelimiterror' in error_type.lower() or
                        hasattr(e, 'status_code') and (e.status_code >= 500 or e.status_code == 429)
                    )
                    
                    if is_retryable and attempt < max_retries:
                        delay = min(base_delay * (backoff_multiplier ** attempt), max_delay)
                        jitter = random.uniform(0.1, 0.5) * delay
                        sleep_time = delay + jitter
                        
                        print(f"  [RETRY] Attempt {attempt + 1}/{max_retries + 1} failed ({error_type}), retrying in {sleep_time:.1f}s...")
                        time.sleep(sleep_time)
                        continue
                    else:
                        # Non-retryable error or max retries reached
                        if attempt > 0:
                            print(f"  [RETRY] All {max_retries + 1} attempts failed")
                        raise e
            
            # This should not be reached, but just in case
            if last_exception:
                raise last_exception
            return None
            
        return wrapper
    return decorator


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
        self.last_usage = None  # Token usage tracking (similar to OpenAI/Claude)
    
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
            return sorted(DEV_OLLAMA_MODELS.copy())
        
        # ORIGINAL DETECTION CODE (preserved for when dev mode is disabled)
        # Check cache first
        current_time = time.time()
        if (self._models_cache is not None and 
            current_time - self._models_cache_time < self._cache_duration):
            return sorted(self._models_cache)
            
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            if response.status_code == 200:
                data = response.json()
                all_models = [model['name'] for model in data.get('models', [])]
                # Filter out cloud models (those ending with '-cloud')
                local_models = sorted([model for model in all_models if not model.endswith('-cloud')])
                
                # Update cache
                self._models_cache = local_models
                self._models_cache_time = current_time
                return local_models
        except:
            pass
        return []
    
    @retry_on_api_error(max_retries=3, base_delay=2.0, max_delay=30.0)
    def describe_image(self, image_path: str, prompt: str, model: str) -> str:
        """Generate description using Ollama with automatic retry"""
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
                result = response.json()
                
                # Extract token usage if available (for cost/performance tracking)
                if 'prompt_eval_count' in result or 'eval_count' in result:
                    self.last_usage = {
                        'prompt_tokens': result.get('prompt_eval_count', 0),
                        'completion_tokens': result.get('eval_count', 0),
                        'total_tokens': result.get('prompt_eval_count', 0) + result.get('eval_count', 0),
                        'model': model
                    }
                
                return result.get('response', 'No description generated')
            else:
                # Enhanced error logging for Ollama HTTP errors
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
                
                # Log detailed error information
                print(f"[ERROR] Ollama API failure - {timestamp}")
                print(f"  Image: {Path(image_path).name}")
                print(f"  Model: {model}")
                print(f"  Status Code: {response.status_code}")
                print(f"  Response: {response.text[:500] if hasattr(response, 'text') else 'No response text'}")
                
                # Also log to file if possible
                try:
                    import json
                    error_details = {
                        'timestamp': timestamp,
                        'provider': 'Ollama',
                        'model': model,
                        'image_path': image_path,
                        'status_code': response.status_code,
                        'response_text': response.text if hasattr(response, 'text') else None,
                        'error_type': 'HTTP_ERROR'
                    }
                    log_file = Path('api_errors.log')
                    with open(log_file, 'a', encoding='utf-8') as f:
                        f.write(json.dumps(error_details) + '\n')
                except Exception as log_error:
                    print(f"  Warning: Could not write to error log: {log_error}")
                
                return f"Error: HTTP {response.status_code} - ({timestamp})"
                
        except Exception as e:
            # Enhanced error logging for Ollama exceptions
            from datetime import datetime
            import traceback
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
            
            # Log comprehensive error details
            print(f"[ERROR] Ollama exception - {timestamp}")
            print(f"  Image: {Path(image_path).name}")
            print(f"  Model: {model}")
            print(f"  Error Type: {type(e).__name__}")
            print(f"  Error Message: {str(e)}")
            
            # Also log to file if possible
            try:
                import json
                error_details = {
                    'timestamp': timestamp,
                    'provider': 'Ollama',
                    'model': model,
                    'image_path': image_path,
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                    'traceback': traceback.format_exc()
                }
                log_file = Path('api_errors.log')
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(error_details) + '\n')
            except Exception as log_error:
                print(f"  Warning: Could not write to error log: {log_error}")
            
            return f"Error generating description: {str(e)} - ({timestamp})"
    
    def get_last_token_usage(self) -> Optional[Dict]:
        """Return token usage from last API call (if available)"""
        return self.last_usage


class OpenAIProvider(AIProvider):
    """OpenAI provider for GPT models using official SDK"""
    
    def __init__(self, api_key: Optional[str] = None):
        # Try multiple sources for API key in order of preference:
        # 1. Explicitly passed key
        # 2. Config file (image_describer_config.json)
        # 3. Environment variable  
        # 4. openai.txt file in current directory
        self.api_key = api_key or self._load_api_key_from_config() or os.getenv('OPENAI_API_KEY') or self._load_api_key_from_file()
        self.timeout = 300
        
        # Initialize OpenAI client with SDK
        self.client = None
        if self.api_key and HAS_OPENAI:
            try:
                self.client = openai.OpenAI(
                    api_key=self.api_key,
                    timeout=self.timeout,
                    max_retries=3  # Automatic retry with exponential backoff
                )
            except Exception as e:
                print(f"Warning: Failed to initialize OpenAI client: {e}")
        elif self.api_key and not HAS_OPENAI:
            print("Warning: openai package not installed. Install with: pip install openai>=1.0.0")
        
        # Token usage tracking (for cost estimation and logging)
        self.last_usage = None
    
    def _load_api_key_from_config(self) -> Optional[str]:
        """Load API key with robust fallback for frozen executables"""
        import sys  # Ensure sys is available in this scope
        
        # 1. Try standard config_loader import
        load_json_config = None
        try:
            # Import config_loader if available
            try:
                from config_loader import load_json_config
            except ImportError:
                try:
                    from scripts.config_loader import load_json_config
                except ImportError:
                    load_json_config = None

            if load_json_config:
                config, _, _ = load_json_config('image_describer_config.json')
                if config:
                    api_keys = config.get('api_keys', {})
                    for key in ['OpenAI', 'openai', 'OPENAI']:
                        if key in api_keys and api_keys[key]:
                            return api_keys[key].strip()
        except Exception as e:
            pass  # Silently continue to fallback

        # 2. Manual Fallback
        try:
            candidates = []
            if getattr(sys, 'frozen', False):
                base_dir = Path(sys.executable).parent
                candidates.append(base_dir / 'image_describer_config.json')
                candidates.append(base_dir / 'scripts' / 'image_describer_config.json')
                if hasattr(sys, '_MEIPASS'):
                    candidates.append(Path(sys._MEIPASS) / 'scripts' / 'image_describer_config.json')
            else:
                base_dir = Path(__file__).parent.parent
                candidates.append(base_dir / 'scripts' / 'image_describer_config.json')
            
            # Also check the platform user config dir (AppData on Windows,
            # ~/Library/Application Support/IDT on macOS) — this is where
            # Configure Settings writes the key in the frozen exe.
            try:
                from config_loader import get_user_config_dir
            except ImportError:
                try:
                    from scripts.config_loader import get_user_config_dir
                except ImportError:
                    get_user_config_dir = None
            if get_user_config_dir:
                candidates.append(get_user_config_dir() / 'image_describer_config.json')

            candidates.append(Path.cwd() / 'image_describer_config.json')
            
            for path in candidates:
                if path.exists():
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            api_keys = data.get('api_keys', {})
                            for k in ['OpenAI', 'openai', 'OPENAI']:
                                if k in api_keys and api_keys[k]:
                                    return api_keys[k].strip()
                    except Exception:
                        continue
        except Exception:
            pass

        return None
    
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
        """Check if OpenAI is available (has API key and SDK)"""
        return bool(self.api_key and self.client)
    
    def reload_api_key(self, explicit_key: Optional[str] = None):
        """Reload API key from all sources and reinitialize client
        
        Call this after API keys are updated via Configure dialog to
        refresh the provider without restarting the application.
        
        Args:
            explicit_key: If provided, use this key directly instead of
                          re-reading from config.  This prevents a keyless
                          config file (e.g. via IDT_CONFIG_DIR) from
                          overwriting a key the caller has already loaded.
        """
        # Use the explicit key if supplied; otherwise re-read from all sources
        if explicit_key:
            self.api_key = explicit_key
        else:
            self.api_key = self._load_api_key_from_config() or os.getenv('OPENAI_API_KEY') or self._load_api_key_from_file()
        
        # Reinitialize client if we have a key
        self.client = None
        if self.api_key and HAS_OPENAI:
            try:
                self.client = openai.OpenAI(
                    api_key=self.api_key,
                    timeout=self.timeout,
                    max_retries=3
                )
            except Exception as e:
                print(f"Warning: Failed to reinitialize OpenAI client: {e}")
    
    def get_available_models(self) -> List[str]:
        """Get list of available OpenAI models"""
        # DEVELOPMENT MODE: Return hardcoded models for faster testing
        if DEV_MODE_HARDCODED_MODELS:
            # Return in defined order (newest/best first) without sorting
            return DEV_OPENAI_MODELS.copy() if self.is_available() else []
        
        # ORIGINAL DETECTION CODE (preserved for when dev mode is disabled)
        if not self.is_available():
            return []
        
        try:
            # Use SDK to list models
            models_response = self.client.models.list()
            # Filter for vision-capable models only
            # As of 2026: gpt-5.x, gpt-4o, gpt-4.1, gpt-4-turbo, o1 support vision
            # Plain gpt-4 does NOT support vision
            # Filter to only known-good vision models by matching our canonical list
            known_good = set(DEV_OPENAI_MODELS)
            vision_models = [model.id for model in models_response.data if model.id in known_good]
            # Sort to match our preferred order
            vision_models.sort(key=lambda m: DEV_OPENAI_MODELS.index(m) if m in DEV_OPENAI_MODELS else 999)
            return vision_models if vision_models else DEV_OPENAI_MODELS.copy()
        except:
            pass
        
        # Fallback to known vision models (in preference order)
        return DEV_OPENAI_MODELS.copy()
    
    @retry_on_api_error(max_retries=3, base_delay=2.0, max_delay=30.0)
    def describe_image(self, image_path: str, prompt: str, model: str) -> str:
        """Generate description using OpenAI SDK with automatic retry and token tracking"""
        if not self.is_available():
            return "Error: OpenAI API key not configured or SDK not installed"
        
        try:
            # Normalise every image to a resized JPEG before sending to OpenAI.
            # Reasons:
            #   - PNG failure rate is 59% vs 26% for JPEG.
            #   - All full-size images (JPEG, HEIC, PNG …) are resized to ≤1600px to
            #     keep bandwidth low. The token count is tile-based server-side so the
            #     resize itself does not change the token bill, but it reduces upload
            #     time and avoids hitting per-request body-size limits.
            #   - gpt-4o-mini uses 2,833+5,667 tokens/tile (vs 85+170 for gpt-4o).
            #     Resizing a large image from ≥2048px to ≤1600px may reduce tile
            #     count from 9→4, saving ~28k tokens per image with that model.
            image_data = None
            file_ext = Path(image_path).suffix.lower()
            
            if HAS_PIL:
                # Attempt PIL-based conversion/resize for every format
                try:
                    img = Image.open(image_path)
                    
                    # Flatten alpha / convert to RGB
                    if img.mode in ('RGBA', 'LA', 'P'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                        img = background
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Resize to ≤1600px on the longest side.  At 1600×1200 a photo
                    # maps to a 2×2 tile grid (4 tiles) under OpenAI's high-detail
                    # algorithm, which is the minimum for most landscape photos.
                    max_dim = 1600
                    if max(img.size) > max_dim:
                        img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
                    
                    # Encode as JPEG
                    buffer = io.BytesIO()
                    img.save(buffer, format='JPEG', quality=85, optimize=True)
                    image_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
                    
                    logger = logging.getLogger(__name__)
                    logger.info(f"Prepared image for OpenAI ({img.size[0]}×{img.size[1]} JPEG, ext={file_ext}): {image_path}")
                except Exception as e:
                    # PIL failed (unsupported format, corrupt file, etc.) – fall back to raw read
                    logger = logging.getLogger(__name__)
                    logger.warning(f"PIL image preparation failed for {image_path}: {e} — sending raw bytes")
                    image_data = None
            
            # Fallback: read raw bytes (no PIL available, or PIL failed above)
            if image_data is None:
                with open(image_path, 'rb') as image_file:
                    image_data = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Use official SDK - handles retry logic, rate limits, and errors automatically
            # Build request parameters with optimized settings
            request_params = {
                "model": model,
                # NOTE: gpt-5-nano does NOT support custom temperature (only default=1)
                # ChatGPT recommended temperature=0.2 but this causes 400 error:
                # "Unsupported value: 'temperature' does not support 0.2 with this model."
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
                ]
            }
            
            # GPT-5 and reasoning models (o1, o3, o4, gpt-5) use max_completion_tokens
            # Older models (GPT-4, GPT-3.5) use max_tokens
            #
            # IMPORTANT: Reasoning models consume tokens internally before producing
            # visible output. At 300, reasoning models (gpt-5, gpt-5-mini, gpt-5-nano,
            # o4-mini, o1) exhaust their budget on reasoning and return empty content
            # with finish_reason=length. Verified 2026-02-23: gpt-5 used 192 reasoning
            # tokens + 63 visible = 255 total — 300 left no room for visible output.
            # 1500 gives ~1200 headroom after typical reasoning budgets.
            if (model.startswith('gpt-5') or model.startswith('o1') or
                    model.startswith('o3') or model.startswith('o4')):
                request_params["max_completion_tokens"] = 1500
            else:
                request_params["max_tokens"] = 300
            
            response = self.client.chat.completions.create(**request_params)
            
            # Extract response details for comprehensive logging
            content = response.choices[0].message.content or ""
            finish_reason = response.choices[0].finish_reason
            response_id = response.id
            
            # DEBUG: Log raw response structure for debugging empty responses (Issue #91)
            logger = logging.getLogger(__name__)
            logger.debug(
                f"RAW RESPONSE | "
                f"id={response_id} | "
                f"model={response.model} | "
                f"choices[0].message.content={repr(content[:100] if content else content)} | "
                f"choices[0].message.role={response.choices[0].message.role} | "
                f"choices[0].finish_reason={finish_reason} | "
                f"usage.prompt_tokens={response.usage.prompt_tokens} | "
                f"usage.completion_tokens={response.usage.completion_tokens}"
            )
            
            # Store token usage for cost tracking and logging
            self.last_usage = {
                'prompt_tokens': response.usage.prompt_tokens,
                'completion_tokens': response.usage.completion_tokens,
                'total_tokens': response.usage.total_tokens,
                'model': model,
                'finish_reason': finish_reason,
                'response_id': response_id
            }
            
            # Log empty responses for debugging (Issue #91: 28% empty response rate with gpt-5-nano)
            logger = logging.getLogger(__name__)
            if not content.strip():
                logger.warning(
                    f"EMPTY RESPONSE from {model} | "
                    f"finish_reason={finish_reason} | "
                    f"completion_tokens={response.usage.completion_tokens} | "
                    f"prompt_tokens={response.usage.prompt_tokens} | "
                    f"response_id={response_id} | "
                    f"image={image_path}"
                )
            else:
                # Log successful responses at debug level
                logger.debug(
                    f"Success: {model} | "
                    f"finish_reason={finish_reason} | "
                    f"completion_tokens={response.usage.completion_tokens} | "
                    f"response_id={response_id}"
                )
            
            return content
                
        except Exception as e:
            # Enhanced error logging with detailed diagnostics
            from datetime import datetime
            import traceback
            
            # Get current timestamp for error logging
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
            
            # Extract detailed error information
            error_type = type(e).__name__
            error_msg = str(e)
            
            # Log comprehensive error details for debugging
            error_details = {
                'timestamp': timestamp,
                'provider': 'OpenAI',
                'model': model,
                'image_path': image_path,
                'error_type': error_type,
                'error_message': error_msg,
                'traceback': traceback.format_exc()
            }
            
            # Try to extract HTTP status code and response details if available
            status_code = None
            response_text = None
            if hasattr(e, 'status_code'):
                status_code = e.status_code
                error_details['status_code'] = status_code
            if hasattr(e, 'response') and e.response:
                try:
                    response_text = e.response.text if hasattr(e.response, 'text') else str(e.response)
                    error_details['response_text'] = response_text
                except:
                    pass
            
            # Log to console with structured format for easy parsing
            print(f"[ERROR] OpenAI API failure - {timestamp}")
            print(f"  Image: {Path(image_path).name}")
            print(f"  Model: {model}")
            print(f"  Error Type: {error_type}")
            if status_code:
                print(f"  Status Code: {status_code}")
            print(f"  Error Message: {error_msg}")
            if response_text and len(response_text) < 500:
                print(f"  Response: {response_text}")
            
            # Also log to file if possible
            try:
                import json
                log_file = Path('api_errors.log')
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(error_details) + '\n')
            except Exception as log_error:
                print(f"  Warning: Could not write to error log: {log_error}")
            
            # Provide user-friendly error messages based on error type and status code
            if 'RateLimitError' in error_type or (status_code and status_code == 429):
                return f"Rate limit exceeded (status code: {status_code or 'unknown'}) - ({timestamp})"
            elif 'AuthenticationError' in error_type or (status_code and status_code == 401):
                return f"Authentication failed - check API key (status code: {status_code or 'unknown'}) - ({timestamp})"
            elif 'InvalidRequestError' in error_type or (status_code and status_code == 400):
                return f"Invalid request - {error_msg} (status code: {status_code or 'unknown'}) - ({timestamp})"
            elif status_code and status_code >= 500:
                return f"Server error from OpenAI API (status code: {status_code}) - ({timestamp})"
            elif 'TimeoutError' in error_type or 'timeout' in error_msg.lower():
                return f"Request timeout - try again later (status code: {status_code or 'timeout'}) - ({timestamp})"
            else:
                return f"Error generating description: {error_msg} (status code: {status_code or 'unknown'}) - ({timestamp})"
    
    def get_last_token_usage(self) -> Optional[Dict]:
        """Get token usage from last API call (for cost tracking and logging)"""
        return self.last_usage


class ClaudeProvider(AIProvider):
    """Anthropic Claude provider for Claude models using official SDK"""
    
    def __init__(self, api_key: Optional[str] = None):
        # Try multiple sources for API key in order of preference:
        # 1. Explicitly passed key
        # 2. Config file (image_describer_config.json)
        # 3. Environment variable  
        # 4. claude.txt file in current directory
        self.api_key = api_key or self._load_api_key_from_config() or os.getenv('ANTHROPIC_API_KEY') or self._load_api_key_from_file()
        self.timeout = 300
        
        # Initialize Anthropic client with SDK
        self.client = None
        if self.api_key and HAS_ANTHROPIC:
            try:
                self.client = anthropic.Anthropic(
                    api_key=self.api_key,
                    timeout=self.timeout,
                    max_retries=3  # Automatic retry with exponential backoff
                )
            except Exception as e:
                print(f"Warning: Failed to initialize Anthropic client: {e}")
        elif self.api_key and not HAS_ANTHROPIC:
            print("Warning: anthropic package not installed. Install with: pip install anthropic>=0.18.0")
        
        # Token usage tracking (for cost estimation and logging)
        self.last_usage = None
    
    def _load_api_key_from_config(self) -> Optional[str]:
        """Load API key with robust fallback for frozen executables"""
        import sys  # Ensure sys is available in this scope
        
        # 1. Try standard config_loader import
        load_json_config = None
        try:
            # Import config_loader if available
            try:
                from config_loader import load_json_config
            except ImportError:
                try:
                    from scripts.config_loader import load_json_config
                except ImportError:
                    load_json_config = None

            if load_json_config:
                config, p, s = load_json_config('image_describer_config.json')
                if config:
                    api_keys = config.get('api_keys', {})
                    for key in ['Claude', 'claude', 'CLAUDE']:
                        if key in api_keys and api_keys[key]:
                            return api_keys[key].strip()
        except Exception as e:
            pass  # Silently continue to fallback

        # 2. Manual Fallback: Search for JSON file directly
        # This bypasses import issues in frozen builds
        try:
            candidates = []
            if getattr(sys, 'frozen', False):
                base_dir = Path(sys.executable).parent
                candidates.append(base_dir / 'image_describer_config.json')
                candidates.append(base_dir / 'scripts' / 'image_describer_config.json')
                if hasattr(sys, '_MEIPASS'):
                    candidates.append(Path(sys._MEIPASS) / 'scripts' / 'image_describer_config.json')
            else:
                base_dir = Path(__file__).parent.parent
                candidates.append(base_dir / 'scripts' / 'image_describer_config.json')
            
            # Also check the platform user config dir (AppData on Windows) —
            # this is where Configure Settings writes the key in the frozen exe.
            try:
                from config_loader import get_user_config_dir
            except ImportError:
                try:
                    from scripts.config_loader import get_user_config_dir
                except ImportError:
                    get_user_config_dir = None
            if get_user_config_dir:
                candidates.append(get_user_config_dir() / 'image_describer_config.json')

            candidates.append(Path.cwd() / 'image_describer_config.json')
            
            for path in candidates:
                if path.exists():
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            api_keys = data.get('api_keys', {})
                            for k in ['Claude', 'claude', 'CLAUDE']:
                                if k in api_keys and api_keys[k]:
                                    return api_keys[k].strip()
                    except Exception:
                        continue
        except Exception:
            pass

        return None
    
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
        """Check if Claude is available (has API key and SDK)"""
        return bool(self.api_key and self.client)
    
    def reload_api_key(self, explicit_key: Optional[str] = None):
        """Reload API key from all sources and reinitialize client
        
        Call this after API keys are updated via Configure dialog to
        refresh the provider without restarting the application.
        
        Args:
            explicit_key: If provided, use this key directly instead of
                          re-reading from config.  This prevents a keyless
                          config file (e.g. via IDT_CONFIG_DIR) from
                          overwriting a key the caller has already loaded.
        """
        # Use the explicit key if supplied; otherwise re-read from all sources
        if explicit_key:
            self.api_key = explicit_key
        else:
            self.api_key = self._load_api_key_from_config() or os.getenv('ANTHROPIC_API_KEY') or self._load_api_key_from_file()
        
        # Reinitialize client if we have a key
        self.client = None
        if self.api_key and HAS_ANTHROPIC:
            try:
                self.client = anthropic.Anthropic(
                    api_key=self.api_key,
                    timeout=self.timeout,
                    max_retries=3
                )
            except Exception as e:
                print(f"Warning: Failed to reinitialize Anthropic client: {e}")
    
    def get_available_models(self) -> List[str]:
        """Get list of available Claude models"""
        # DEVELOPMENT MODE: Return hardcoded models for faster testing
        if DEV_MODE_HARDCODED_MODELS:
            # Use smart sorting: haiku -> sonnet -> opus (cheapest to most expensive)
            return sort_claude_models(DEV_CLAUDE_MODELS.copy()) if self.is_available() else []
        
        # ORIGINAL DETECTION CODE (preserved for when dev mode is disabled)
        if not self.is_available():
            return []
        
        # Claude doesn't have a models endpoint, so we return the known models
        # All Claude models support vision natively
        # Sort by tier and version for easier selection
        return sort_claude_models(DEV_CLAUDE_MODELS.copy())
    
    @retry_on_api_error(max_retries=3, base_delay=2.0, max_delay=30.0)
    def describe_image(self, image_path: str, prompt: str, model: str) -> str:
        """Generate description using Claude SDK with automatic retry and token tracking"""
        if not self.is_available():
            return "Error: Claude API key not configured or SDK not installed"
        
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
            
            # Use official SDK - handles retry logic, rate limits, and errors automatically
            message = self.client.messages.create(
                model=model,
                max_tokens=1024,
                messages=[
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
            )
            
            # Store token usage for cost tracking and logging
            self.last_usage = {
                'prompt_tokens': message.usage.input_tokens,
                'completion_tokens': message.usage.output_tokens,
                'total_tokens': message.usage.input_tokens + message.usage.output_tokens,
                'model': model
            }
            
            # Extract text from content
            if message.content and len(message.content) > 0:
                return message.content[0].text
            return "Error: No content in response"
                
        except Exception as e:
            # Enhanced error logging with detailed diagnostics
            from datetime import datetime
            import traceback
            
            # Get current timestamp for error logging
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
            
            # Extract detailed error information
            error_type = type(e).__name__
            error_msg = str(e)
            
            # Log comprehensive error details for debugging
            error_details = {
                'timestamp': timestamp,
                'provider': 'Claude',
                'model': model,
                'image_path': image_path,
                'error_type': error_type,
                'error_message': error_msg,
                'traceback': traceback.format_exc()
            }
            
            # Try to extract HTTP status code and response details if available
            status_code = None
            response_text = None
            if hasattr(e, 'status_code'):
                status_code = e.status_code
                error_details['status_code'] = status_code
            if hasattr(e, 'response') and e.response:
                try:
                    response_text = e.response.text if hasattr(e.response, 'text') else str(e.response)
                    error_details['response_text'] = response_text
                except:
                    pass
            
            # Log to console with structured format for easy parsing
            print(f"[ERROR] Claude API failure - {timestamp}")
            print(f"  Image: {Path(image_path).name}")
            print(f"  Model: {model}")
            print(f"  Error Type: {error_type}")
            if status_code:
                print(f"  Status Code: {status_code}")
            print(f"  Error Message: {error_msg}")
            if response_text and len(response_text) < 500:
                print(f"  Response: {response_text}")
            
            # Also log to file if possible
            try:
                import json
                log_file = Path('api_errors.log')
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(error_details) + '\n')
            except Exception as log_error:
                print(f"  Warning: Could not write to error log: {log_error}")
            
            # Provide user-friendly error messages based on error type and status code
            if 'RateLimitError' in error_type or (status_code and status_code == 429):
                return f"Rate limit exceeded (status code: {status_code or 'unknown'}) - ({timestamp})"
            elif 'AuthenticationError' in error_type or (status_code and status_code == 401):
                return f"Authentication failed - check API key (status code: {status_code or 'unknown'}) - ({timestamp})"
            elif 'InvalidRequestError' in error_type or (status_code and status_code == 400):
                return f"Invalid request - {error_msg} (status code: {status_code or 'unknown'}) - ({timestamp})"
            elif status_code and status_code >= 500:
                return f"Server error from Claude API (status code: {status_code}) - ({timestamp})"
            elif 'TimeoutError' in error_type or 'timeout' in error_msg.lower():
                return f"Request timeout - try again later (status code: {status_code or 'timeout'}) - ({timestamp})"
            else:
                return f"Error generating description: {error_msg} (status code: {status_code or 'unknown'}) - ({timestamp})"
    
    def get_last_token_usage(self) -> Optional[Dict]:
        """Get token usage from last API call (for cost tracking and logging)"""
        return self.last_usage


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

# Try to import transformers for Florence-2 (optional dependency)
# When running as frozen executable, delay import to allow system-installed packages
HAS_TRANSFORMERS = False
AutoProcessor = None
AutoModelForCausalLM = None
PILImage = None
torch = None

def _check_transformers_available():
    """Check if transformers is available at runtime
    
    For frozen executables, this will try to import from system Python
    by temporarily adding site-packages to sys.path.
    """
    # If running as frozen executable, add system site-packages to path
    if getattr(sys, 'frozen', False):
        try:
            import site
            import sysconfig
            
            # Get system site-packages directories
            user_site = site.getusersitepackages()
            global_site = sysconfig.get_path('purelib')
            
            # Temporarily add to path if not already there
            paths_to_add = []
            if user_site and user_site not in sys.path:
                paths_to_add.append(user_site)
            if global_site and global_site not in sys.path:
                paths_to_add.append(global_site)
            
            # Add paths temporarily
            for p in paths_to_add:
                sys.path.insert(0, p)
            
            # Try to import
            try:
                from transformers import AutoProcessor, AutoModelForCausalLM
                from PIL import Image as PILImage
                import torch
                return True
            except ImportError:
                return False
            finally:
                # Remove added paths
                for p in paths_to_add:
                    if p in sys.path:
                        sys.path.remove(p)
        except Exception:
            return False
    else:
        # Not frozen, use normal import
        try:
            from transformers import AutoProcessor, AutoModelForCausalLM
            from PIL import Image as PILImage
            import torch
            return True
        except ImportError:
            return False

# Try import if not running as frozen executable
if not getattr(sys, 'frozen', False):
    try:
        from transformers import AutoProcessor, AutoModelForCausalLM
        from PIL import Image as PILImage
        import torch
        HAS_TRANSFORMERS = True
    except ImportError:
        pass

from pathlib import Path
import platform
import subprocess


class HuggingFaceProvider(AIProvider):
    """HuggingFace provider for local Florence-2 vision models with NPU acceleration"""
    
    # Florence-2 task types for different levels of detail
    TASK_CAPTION = "<CAPTION>"
    TASK_DETAILED = "<DETAILED_CAPTION>"
    TASK_MORE_DETAILED = "<MORE_DETAILED_CAPTION>"
    
    # Prompt style to task mapping
    PROMPT_TO_TASK = {
        "simple": TASK_CAPTION,
        "narrative": TASK_MORE_DETAILED,
        "detailed": TASK_MORE_DETAILED,
        "technical": TASK_DETAILED,
    }
    
    def __init__(self):
        self.model = None
        self.processor = None
        self.device = None
        self.model_name = None
        self._available_models = [
            "microsoft/Florence-2-base",
            "microsoft/Florence-2-large"
        ]
    
    def get_provider_name(self) -> str:
        return "HuggingFace"
    
    def is_available(self) -> bool:
        """Check if Florence-2 dependencies are available"""
        # For frozen executables, check at runtime instead of import time
        if getattr(sys, 'frozen', False):
            return _check_transformers_available()
        return HAS_TRANSFORMERS
    
    def get_available_models(self) -> List[str]:
        """Get list of available Florence-2 models"""
        # Check availability at runtime for frozen executables
        if getattr(sys, 'frozen', False):
            if not _check_transformers_available():
                return []
        elif not HAS_TRANSFORMERS:
            return []
        return self._available_models.copy()
    
    def _load_model(self, model: str):
        """Load Florence-2 model if not already loaded"""
        if self.model is not None and self.model_name == model:
            return  # Already loaded
        
        # Import transformers at runtime (needed for frozen executables)
        global AutoProcessor, AutoModelForCausalLM, torch, PILImage
        if AutoProcessor is None:
            # Add system site-packages for frozen executables
            paths_added = []
            if getattr(sys, 'frozen', False):
                try:
                    import site
                    import sysconfig
                    user_site = site.getusersitepackages()
                    global_site = sysconfig.get_path('purelib')
                    
                    if user_site and user_site not in sys.path:
                        sys.path.insert(0, user_site)
                        paths_added.append(user_site)
                    if global_site and global_site not in sys.path:
                        sys.path.insert(0, global_site)
                        paths_added.append(global_site)
                except Exception:
                    pass
            
            try:
                from transformers import AutoProcessor as AP, AutoModelForCausalLM as AM
                from PIL import Image as PI
                import torch as t
                AutoProcessor = AP
                AutoModelForCausalLM = AM
                PILImage = PI
                torch = t
            except ImportError as e:
                # Clean up added paths
                for p in paths_added:
                    if p in sys.path:
                        sys.path.remove(p)
                raise ImportError(
                    f"Florence-2 requires transformers>=4.45.0, torch, and Pillow.\n"
                    f"Install with: pip install 'transformers>=4.45.0' torch torchvision pillow\n"
                    f"Error: {str(e)}"
                )
        
        try:
            # Determine device (NPU/GPU/CPU)
            if torch.cuda.is_available():
                self.device = "cuda"
            else:
                self.device = "cpu"
            
            # Load model and processor
            print(f"Loading {model} on {self.device}...")
            self.processor = AutoProcessor.from_pretrained(model, trust_remote_code=True)
            self.model = AutoModelForCausalLM.from_pretrained(
                model, 
                trust_remote_code=True,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                attn_implementation="eager"  # Use eager attention to avoid SDPA compatibility issues
            ).to(self.device)
            self.model_name = model
            print(f"Model loaded successfully on {self.device}")
            
        except Exception as e:
            raise RuntimeError(f"Failed to load Florence-2 model: {str(e)}")
    
    def _get_task_for_prompt(self, prompt: str) -> str:
        """Convert prompt style to Florence-2 task type
        
        Florence-2 only supports 3 task types regardless of custom prompts:
        - simple/brief → <CAPTION>
        - technical → <DETAILED_CAPTION>  
        - narrative/detailed → <MORE_DETAILED_CAPTION>
        """
        # Extract prompt style from the prompt text by keyword matching
        prompt_lower = prompt.lower()
        
        # Check for explicit task keywords in the prompt
        # Order matters: check specific keywords before general ones
        if "technical" in prompt_lower:
            return self.TASK_DETAILED
        elif "simple" in prompt_lower or "brief" in prompt_lower or "concise" in prompt_lower:
            return self.TASK_CAPTION
        elif "detailed" in prompt_lower or "comprehensive" in prompt_lower or "narrative" in prompt_lower:
            return self.TASK_MORE_DETAILED
        
        # Default to most detailed description
        return self.TASK_MORE_DETAILED
    
    def describe_image(self, image_path: str, prompt: str, model: str) -> str:
        """Generate description for an image using Florence-2"""
        try:
            # Load model if needed
            self._load_model(model)
            
            # Load image
            image = PILImage.open(image_path).convert('RGB')
            
            # Determine task type based on prompt
            task = self._get_task_for_prompt(prompt)
            
            # Prepare inputs - Florence-2 uses task as the text prompt
            inputs = self.processor(
                text=task,
                images=image,
                return_tensors="pt"
            )
            
            # Move inputs to device (handle tensors only, skip None values)
            device_inputs = {}
            for k, v in inputs.items():
                if v is not None and hasattr(v, 'to'):
                    device_inputs[k] = v.to(self.device)
                else:
                    device_inputs[k] = v
            
            # Generate description - Florence-2 expects all inputs passed as kwargs
            # Note: use_cache=False is required due to Florence-2 incompatibility with
            # transformers 4.57+ EncoderDecoderCache format. This makes generation slower
            # but ensures compatibility. See: https://github.com/huggingface/transformers/issues/xxxxx
            generated_ids = self.model.generate(
                **device_inputs,
                max_new_tokens=1024,
                use_cache=False,  # Required for transformers 4.57+ compatibility
                do_sample=False
            )
            
            # Decode output
            generated_text = self.processor.batch_decode(
                generated_ids, 
                skip_special_tokens=False
            )[0]
            
            # Extract the actual description (remove task prefix)
            parsed_answer = self.processor.post_process_generation(
                generated_text,
                task=task,
                image_size=(image.width, image.height)
            )
            
            # Get the description text
            description = parsed_answer.get(task, "")
            
            if not description:
                return "⚠️ Florence-2 generated no description for this image."
            
            return description
            
        except ImportError as e:
            return f"⚠️ Florence-2 dependencies not installed: {str(e)}"
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"⚠️ Error generating description with Florence-2: {str(e)}"


# ---------------------------------------------------------------------------
# MLX Provider — Apple Metal inference via mlx-vlm
# macOS + Apple Silicon only; gracefully unavailable on other platforms.
# ---------------------------------------------------------------------------

# Module-level import attempt so PyInstaller can bundle the package when present.
try:
    import mlx_vlm as _mlx_vlm_module
    from mlx_vlm import load as _mlx_load, generate as _mlx_generate
    from mlx_vlm.utils import load_config as _mlx_load_config
    from mlx_vlm.prompt_utils import apply_chat_template as _mlx_apply_chat_template
    HAS_MLX_VLM = True
except ImportError:
    _mlx_vlm_module = None
    HAS_MLX_VLM = False


class MLXProvider(AIProvider):
    """Apple Metal (MLX) provider for on-device vision inference.

    Uses mlx-vlm to run Qwen2-VL and compatible models directly on the
    Apple Silicon GPU via the Metal framework.  No API key required.

    Availability:
        - macOS with Apple Silicon only
        - Requires:  pip install mlx-vlm

    Model lifecycle:
        The loaded model stays in unified memory for the lifetime of this
        instance (mirrors Ollama's hot-model behaviour).  Switching models
        triggers a reload; within a batch all calls reuse the same weights.

    HEIC / format handling:
        MLX requires a JPEG path on disk.  Any non-JPEG input (HEIC, PNG,
        TIFF …) is converted to a temporary JPEG and cleaned up after each
        call.  pillow-heif is used automatically when available.
    """

    # Known-good models from MLX Community Hub (tested with mlx-vlm).
    # Listed from smallest/fastest to largest/most capable.
    KNOWN_MODELS: List[str] = [
        "mlx-community/Qwen2-VL-2B-Instruct-4bit",
        "mlx-community/Qwen2.5-VL-3B-Instruct-4bit",
        "mlx-community/Qwen2.5-VL-7B-Instruct-4bit",
        "mlx-community/llava-1.5-7b-4bit",
    ]

    # Tokens to generate per image — matches production Ollama num_predict setting.
    MAX_TOKENS = 600

    def __init__(self) -> None:
        self._model = None
        self._processor = None
        self._mlx_config = None
        self._loaded_model_id: Optional[str] = None
        self.last_usage: Optional[Dict] = None

    # ------------------------------------------------------------------
    # AIProvider interface
    # ------------------------------------------------------------------

    def get_provider_name(self) -> str:
        return "MLX"

    def is_available(self) -> bool:
        """MLX is only available on macOS (any version) with mlx-vlm installed."""
        if platform.system() != "Darwin":
            return False
        return HAS_MLX_VLM

    def get_available_models(self) -> List[str]:
        if not self.is_available():
            return []
        return list(self.KNOWN_MODELS)

    def describe_image(self, image_path: str, prompt: str, model: str) -> str:
        """Run Metal-accelerated vision inference and return a description string."""
        if not self.is_available():
            return (
                "Error: MLX provider not available. "
                "Requires macOS with Apple Silicon and: pip install mlx-vlm"
            )

        temp_jpeg: Optional[str] = None
        try:
            # ---- apply transformers monkey-patch (safety net for some versions) ----
            self._patch_transformers_video_bug()

            # ---- load / recall model in unified memory ----
            self._ensure_model_loaded(model)

            # ---- convert to JPEG if needed (MLX requires a JPEG path on disk) ----
            path_obj = Path(image_path)
            if path_obj.suffix.lower() not in {'.jpg', '.jpeg'}:
                temp_jpeg = self._to_jpeg_tempfile(image_path)
                if not temp_jpeg:
                    return (
                        f"Error: Could not convert {path_obj.suffix.upper()} "
                        f"to JPEG for MLX inference"
                    )
                use_path = temp_jpeg
            else:
                use_path = image_path

            # ---- format prompt for the model's chat template ----
            formatted_prompt = _mlx_apply_chat_template(
                self._processor, self._mlx_config, prompt, num_images=1
            )

            # ---- run inference on Metal ----
            t0 = time.time()
            output = _mlx_generate(
                self._model,
                self._processor,
                formatted_prompt,
                image=[use_path],
                max_tokens=self.MAX_TOKENS,
                verbose=False,
            )
            elapsed = time.time() - t0

            # GenerationResult exposes .text, .generation_tokens, .generation_tps
            text = getattr(output, 'text', None) or str(output)
            tokens_out = getattr(output, 'generation_tokens', 0) or 0
            tps = getattr(output, 'generation_tps', 0.0) or 0.0

            self.last_usage = {
                'prompt_tokens': 0,          # mlx-vlm does not expose prompt tokens
                'completion_tokens': tokens_out,
                'total_tokens': tokens_out,
                'model': model,
                'elapsed_s': elapsed,
                'tokens_per_s': tps,
                'finish_reason': 'stop',     # assume stop; no length info from mlx-vlm
            }

            return text.strip() if text else "Error: MLX returned empty response"

        except Exception as exc:
            import traceback
            error_type = type(exc).__name__
            error_msg = str(exc)
            print(f"[ERROR] MLX inference error — {error_type}: {error_msg}")
            traceback.print_exc()
            return f"Error generating description (MLX/{model}): {error_msg}"

        finally:
            if temp_jpeg:
                try:
                    Path(temp_jpeg).unlink()
                except Exception:
                    pass

    def get_last_token_usage(self) -> Optional[Dict]:
        return self.last_usage

    def reload_api_key(self, explicit_key: Optional[str] = None) -> None:
        """No-op — MLX requires no API key."""
        pass

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_model_loaded(self, model_id: str) -> None:
        """Load model weights into Metal unified memory if not already loaded.

        Subsequent calls with the same model_id are instant (no reload).
        A model switch triggers a full reload.
        """
        if self._loaded_model_id == model_id and self._model is not None:
            return

        print(f"  [MLX] Loading {model_id} into Metal memory …")
        t0 = time.time()
        self._model, self._processor = _mlx_load(model_id)
        self._mlx_config = _mlx_load_config(model_id)
        self._loaded_model_id = model_id
        dt = time.time() - t0
        print(f"  [MLX] Model ready in {dt:.1f}s (stays in Metal memory until exit)")

    @staticmethod
    def _patch_transformers_video_bug() -> None:
        """Work around a transformers bug present in some versions.

        transformers.models.auto.video_processing_auto.video_processor_class_from_name
        raises TypeError('argument of type NoneType is not iterable') when the
        extractors mapping is None.  This monkey-patch makes the call safe.
        The patch is idempotent — applying it multiple times is harmless.
        """
        try:
            import transformers.models.auto.video_processing_auto as _vpa
            _orig = _vpa.video_processor_class_from_name
            if getattr(_orig, '_mlx_patched', False):
                return  # already patched

            def _safe(class_name, extractors=None):
                try:
                    return _orig(class_name, extractors)
                except TypeError:
                    return None

            _safe._mlx_patched = True
            _vpa.video_processor_class_from_name = _safe
        except Exception:
            pass

    @staticmethod
    def _to_jpeg_tempfile(image_path: str) -> Optional[str]:
        """Convert any supported image (incl. HEIC) to a temp JPEG on disk.

        Returns the temp file path, or None on failure.
        The caller is responsible for unlinking the file when done.
        """
        try:
            # Enable HEIC support when pillow-heif is available
            try:
                import pillow_heif
                pillow_heif.register_heif_opener()
            except ImportError:
                pass

            from PIL import Image as _PILImage
            import tempfile

            max_dim = 1024
            quality = 85

            with _PILImage.open(image_path) as img:
                img = img.convert("RGB")
                w, h = img.size
                if max(w, h) > max_dim:
                    scale = max_dim / max(w, h)
                    img = img.resize((int(w * scale), int(h * scale)), _PILImage.LANCZOS)
                tmp = tempfile.NamedTemporaryFile(
                    suffix=".jpg", delete=False, prefix="mlx_idt_"
                )
                img.save(tmp, format="JPEG", quality=quality)
                tmp.close()
                return tmp.name
        except Exception as exc:
            print(f"  [MLX] JPEG conversion failed for {image_path}: {exc}")
            return None


# ---------------------------------------------------------------------------
# Global provider instances
# ---------------------------------------------------------------------------

_ollama_provider = OllamaProvider()
_ollama_cloud_provider = OllamaCloudProvider()
_openai_provider = OpenAIProvider()
_claude_provider = ClaudeProvider()
_huggingface_provider = HuggingFaceProvider()
_mlx_provider = MLXProvider()


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

    if _huggingface_provider.is_available():
        providers['huggingface'] = _huggingface_provider

    if _mlx_provider.is_available():
        providers['mlx'] = _mlx_provider

    return providers


def get_all_providers() -> Dict[str, AIProvider]:
    """Get all AI providers (available and unavailable)"""
    return {
        'ollama': _ollama_provider,
        'ollama_cloud': _ollama_cloud_provider,
        'openai': _openai_provider,
        'claude': _claude_provider,
        'huggingface': _huggingface_provider,
        'mlx': _mlx_provider,
    }