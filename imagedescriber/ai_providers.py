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

DEV_OPENAI_MODELS = [
    "gpt-5",
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
                return response.json().get('response', 'No description generated')
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


class OpenAIProvider(AIProvider):
    """OpenAI provider for GPT models using official SDK"""
    
    def __init__(self, api_key: Optional[str] = None):
        # Try multiple sources for API key in order of preference:
        # 1. Explicitly passed key
        # 2. Environment variable  
        # 3. openai.txt file in current directory
        self.api_key = api_key or os.getenv('OPENAI_API_KEY') or self._load_api_key_from_file()
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
    
    def get_available_models(self) -> List[str]:
        """Get list of available OpenAI models"""
        # DEVELOPMENT MODE: Return hardcoded models for faster testing
        if DEV_MODE_HARDCODED_MODELS:
            return DEV_OPENAI_MODELS.copy() if self.is_available() else []
        
        # ORIGINAL DETECTION CODE (preserved for when dev mode is disabled)
        if not self.is_available():
            return []
        
        try:
            # Use SDK to list models
            models_response = self.client.models.list()
            vision_models = [
                model.id for model in models_response.data
                if 'vision' in model.id or model.id.startswith('gpt-4')
            ]
            return sorted(vision_models)
        except:
            pass
        
        # Fallback to known vision models
        return ['gpt-4-vision-preview', 'gpt-4o', 'gpt-4o-mini']
    
    @retry_on_api_error(max_retries=3, base_delay=2.0, max_delay=30.0)
    def describe_image(self, image_path: str, prompt: str, model: str) -> str:
        """Generate description using OpenAI SDK with automatic retry and token tracking"""
        if not self.is_available():
            return "Error: OpenAI API key not configured or SDK not installed"
        
        try:
            # Read and encode image
            with open(image_path, 'rb') as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Use official SDK - handles retry logic, rate limits, and errors automatically
            # Build request parameters
            request_params = {
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
                ]
            }
            
            # GPT-5 and newer models (o1, o3, gpt-5) use max_completion_tokens instead of max_tokens
            # Older models (GPT-4, GPT-3.5) use max_tokens
            if model.startswith('gpt-5') or model.startswith('o1') or model.startswith('o3'):
                request_params["max_completion_tokens"] = 1000
            else:
                request_params["max_tokens"] = 1000
            
            response = self.client.chat.completions.create(**request_params)
            
            # Store token usage for cost tracking and logging
            self.last_usage = {
                'prompt_tokens': response.usage.prompt_tokens,
                'completion_tokens': response.usage.completion_tokens,
                'total_tokens': response.usage.total_tokens,
                'model': model
            }
            
            return response.choices[0].message.content
                
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
        # 2. Environment variable  
        # 3. claude.txt file in current directory
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY') or self._load_api_key_from_file()
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


# Global provider instances
_ollama_provider = OllamaProvider()
_ollama_cloud_provider = OllamaCloudProvider()
_openai_provider = OpenAIProvider()
_claude_provider = ClaudeProvider()
_huggingface_provider = HuggingFaceProvider()


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
    
    return providers


def get_all_providers() -> Dict[str, AIProvider]:
    """Get all AI providers (available and unavailable)"""
    return {
        'ollama': _ollama_provider,
        'ollama_cloud': _ollama_cloud_provider,
        'openai': _openai_provider,
        'claude': _claude_provider,
        'huggingface': _huggingface_provider
    }