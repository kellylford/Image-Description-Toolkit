#!/usr/bin/env python3
"""
ImageDescriber - AI-Powered Image Analysis Tool

This script processes directories of image files using Ollama's vision models
to generate detailed descriptions and extract metadata. Features include:

- AI-powered image descriptions using various Ollama vision models
- EXIF metadata extraction (camera settings, GPS, timestamps)
- Configurable prompt styles for different analysis needs
- Memory optimization for processing large image collections
- Comprehensive text file output with metadata integration
- Support for multiple image formats (JPG, PNG, BMP, TIFF, WebP)

The tool outputs descriptions to text files with comprehensive metadata
including camera settings, GPS coordinates, timestamps, and AI-generated
descriptions using configurable prompt styles.
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
import base64
import json
import gc
import time
from datetime import datetime


def set_console_title(title):
    """Set the Windows console title."""
    if sys.platform == 'win32':
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleTitleW(title)
        except Exception:
            # Silently fail if unable to set title
            pass

# Make ollama optional for backwards compatibility
try:
    import ollama
except ImportError:
    ollama = None

from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

# Import ConvertImage utilities for image size optimization
try:
    from ConvertImage import optimize_image_size, TARGET_MAX_SIZE, CLAUDE_MAX_SIZE, OPENAI_MAX_SIZE
except ImportError:
    # If direct import fails, try from current directory
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from ConvertImage import optimize_image_size, TARGET_MAX_SIZE, CLAUDE_MAX_SIZE, OPENAI_MAX_SIZE

# Import AI providers from the main application
# Add parent directory to path to import from imagedescriber module
sys.path.insert(0, str(Path(__file__).parent.parent))
from imagedescriber.ai_providers import (
    OllamaProvider,
    OpenAIProvider,
    ClaudeProvider
)


# Configure basic logging with screen reader friendly format
# Format: LEVEL - message - (timestamp)
# This provides a fallback before setup_logging() is called
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s - (%(asctime)s)'
)
logger = logging.getLogger(__name__)


def setup_logging(log_dir: Optional[str] = None, verbose: bool = False, quiet: bool = False) -> None:
    """
    Set up logging configuration for the image describer
    
    Args:
        log_dir: Directory to write log files to
        verbose: Whether to enable debug logging
        quiet: Whether to suppress console output (for subprocess calls)
    """
    global logger
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Set logging level
    level = logging.DEBUG if verbose else logging.INFO
    logger.setLevel(level)
    
    # Create formatter
    # Format: LEVEL - message - (timestamp)
    # Screen reader friendly: reads important info first, timestamp last
    formatter = logging.Formatter('%(levelname)s - %(message)s - (%(asctime)s)')
    
    # Console handler (skip if quiet mode for subprocess calls)
    if not quiet:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler if log_dir is provided
    if log_dir:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        log_filename = log_path / f"image_describer_{timestamp}.log"
        
        file_handler = logging.FileHandler(log_filename, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        logger.info(f"Image describer log file: {log_filename.absolute()}")


class ImageDescriber:
    """Class to handle image description using various AI providers"""
    
    def __init__(self, model_name: str = None, max_image_size: int = 1024, 
                 enable_compression: bool = True, batch_delay: float = 2.0, 
                 config_file: str = "image_describer_config.json", prompt_style: str = "detailed",
                 output_dir: str = None, provider: str = "ollama", api_key: str = None,
                 log_dir: str = None):
        """
        Initialize the ImageDescriber
        
        Args:
            model_name: Name of the vision model to use (overrides config if specified)
            max_image_size: Maximum image dimension (width or height) in pixels
            enable_compression: Whether to compress images before processing
            batch_delay: Delay between processing images to prevent memory buildup
            config_file: Path to the JSON configuration file
            prompt_style: Style of prompt to use (detailed, concise, artistic, technical)
            output_dir: Custom output directory (default: same as input directory)
            provider: AI provider to use (ollama, onnx, openai, huggingface)
            api_key: API key for providers that require authentication
            log_dir: Directory where log files and progress tracking are stored
        """
        # Load configuration first
        self.config = self.load_config(config_file)
        
        # Set model name - use parameter if provided, otherwise use config, otherwise default
        if model_name is not None:
            self.model_name = model_name
        else:
            self.model_name = self.config.get('model_settings', {}).get('model', 'moondream')
        
        self.max_image_size = max_image_size
        self.enable_compression = enable_compression
        self.batch_delay = batch_delay
        self.prompt_style = prompt_style
        self.output_dir = output_dir  # Custom output directory
        self.log_dir = log_dir  # Directory for logs and progress tracking
        self.provider_name = provider.lower()
        self.api_key = api_key
        
        # Set supported formats from config
        self.supported_formats = set(self.config.get('processing_options', {}).get('supported_formats', 
                                                    ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']))
        
        # Initialize the AI provider
        self.provider = self._initialize_provider()
        
        logger.info(f"Initialized ImageDescriber with provider: {self.provider_name}, model: {self.model_name}")
    
    def _initialize_provider(self):
        """Initialize the AI provider based on configuration"""
        try:
            if self.provider_name == "ollama":
                logger.info("Initializing Ollama provider...")
                provider = OllamaProvider()
                # Verify model is available
                try:
                    models = ollama.list()
                    available_models = [model['name'] for model in models.get('models', [])]
                    if self.model_name not in available_models:
                        logger.warning(f"Model '{self.model_name}' not found in Ollama")
                        logger.info(f"Available models: {', '.join(available_models)}")
                        logger.info(f"Tip: Install with 'ollama pull {self.model_name}'")
                except Exception as e:
                    logger.warning(f"Could not verify Ollama models: {e}")
                return provider
                
            elif self.provider_name == "openai":
                logger.info("Initializing OpenAI provider...")
                if not self.api_key:
                    raise ValueError("OpenAI provider requires an API key. Use --api-key-file option.")
                # Pass api_key to constructor so client initializes correctly
                provider = OpenAIProvider(api_key=self.api_key)
                return provider
                
            elif self.provider_name == "claude":
                logger.info("Initializing Claude provider...")
                if not self.api_key:
                    raise ValueError("Claude provider requires an API key. Use --api-key-file option.")
                # Pass api_key to constructor so client initializes correctly
                provider = ClaudeProvider(api_key=self.api_key)
                logger.info(f"Claude provider initialized. API key set: {bool(provider.api_key)}, Client available: {bool(provider.client)}, Is available: {provider.is_available()}")
                print(f"INFO: Claude provider - API key set: {bool(provider.api_key)}, Client: {bool(provider.client)}, Available: {provider.is_available()}")
                return provider
                
            else:
                raise ValueError(f"Unknown provider: {self.provider_name}. Supported: ollama, openai, claude")
                
        except Exception as e:
            logger.error(f"Failed to initialize provider '{self.provider_name}': {e}")
            raise
    
    def load_config(self, config_file: str) -> dict:
        """
        Load configuration from JSON file
        
        Args:
            config_file: Path to the JSON configuration file
            
        Returns:
            Dictionary with configuration settings
        """
        try:
            config_path = Path(config_file)
            if not config_path.is_absolute():
                # Look for config file in script directory
                script_dir = Path(__file__).parent
                config_path = script_dir / config_file
            
            if not config_path.exists():
                logger.warning(f"Config file not found: {config_path}")
                return self.get_default_config()
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            logger.info(f"Loaded configuration from: {config_path}")
            return config
            
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
            logger.info("Using default configuration")
            return self.get_default_config()
    
    def get_default_config(self) -> dict:
        """
        Get default configuration if config file is not available
        
        Returns:
            Dictionary with default configuration settings
        """
        return {
            "model_settings": {
                "model": "moondream",
                "temperature": 0.1,
                "num_predict": 600,
                "top_k": 40,
                "top_p": 0.9
            },
            "prompt_template": "Describe this image in detail, including:\n- Main subjects/objects\n- Setting/environment\n- Key colors and lighting\n- Notable activities or composition\nKeep it comprehensive and informative for metadata.",
            "default_prompt_style": "detailed",
            "prompt_variations": {
                "detailed": "Describe this image in detail, including:\n- Main subjects/objects\n- Setting/environment\n- Key colors and lighting\n- Notable activities or composition\nKeep it comprehensive and informative for metadata.",
                "concise": "Describe this image concisely, including:\n- Main subjects/objects\n- Setting/environment\n- Key colors and lighting\n- Notable activities or composition.",
                "narrative": "Provide a narrative description including objects, colors and detail. Avoid interpretation, just describe.",
                "artistic": "Analyze this image from an artistic perspective, describing:\n- Visual composition and framing\n- Color palette and lighting mood\n- Artistic style or technique\n- Emotional tone or atmosphere\n- Subject matter and symbolism",
                "technical": "Provide a technical analysis of this image:\n- Camera settings and photographic technique\n- Lighting conditions and quality\n- Composition and framing\n- Image quality and clarity\n- Technical strengths or weaknesses",
                "colorful": "Give me a rich, vivid description emphasizing colors, lighting, and visual atmosphere. Focus on the palette, color relationships, and how colors contribute to the mood and composition."
            },
            "output_format": {
                "include_timestamp": True,
                "include_model_info": True,
                "include_file_path": True,
                "include_metadata": True,
                "separator": "-"
            },
            "processing_options": {
                "default_max_image_size": 1024,
                "default_batch_delay": 2.0,
                "default_compression": True,
                "extract_metadata": True,
                "supported_formats": [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"]
            }
        }
    
    def get_prompt(self) -> str:
        """
        Get the prompt based on the selected style with case-insensitive lookup
        
        Returns:
            Prompt string
        """
        prompt_variations = self.config.get('prompt_variations', {})
        
        # Case-insensitive lookup
        lower_variations = {k.lower(): v for k, v in prompt_variations.items()}
        
        if self.prompt_style.lower() in lower_variations:
            return lower_variations[self.prompt_style.lower()]
        else:
            # Fallback to default prompt_template
            return self.config.get('prompt_template', 
                                 "Describe this image in detail, including the main subjects, setting, colors, and composition.")
    
    def get_model_settings(self) -> dict:
        """
        Get model settings from configuration (excluding model name)
        
        Returns:
            Dictionary with model settings for ollama API call
        """
        model_settings = self.config.get('model_settings', {
            "temperature": 0.1,
            "num_predict": 400
        })
        
        # Remove model name from settings as it's passed separately to ollama
        settings = model_settings.copy()
        settings.pop('model', None)
        
        return settings
        
    def is_supported_image(self, file_path: Path) -> bool:
        """Check if the file is a supported image format"""
        return file_path.suffix.lower() in self.supported_formats
    
    def optimize_image(self, image_path: Path) -> Optional[bytes]:
        """
        Optimize image for processing by resizing and compressing
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Optimized image bytes or None if failed
        """
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Resize if too large
                if self.enable_compression and (img.width > self.max_image_size or img.height > self.max_image_size):
                    img.thumbnail((self.max_image_size, self.max_image_size), Image.Resampling.LANCZOS)
                    logger.info(f"Resized image {image_path.name} to {img.width}x{img.height}")
                
                # Save to bytes with compression
                import io
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=85, optimize=True)
                return buffer.getvalue()
                
        except Exception as e:
            logger.error(f"Error optimizing image {image_path}: {e}")
            return None
    
    def encode_image_to_base64(self, image_path: Path) -> str:
        """
        Encode image to base64 string with optimization
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Base64 encoded string of the image
        """
        try:
            # Try optimized approach first
            if self.enable_compression:
                optimized_bytes = self.optimize_image(image_path)
                if optimized_bytes:
                    return base64.b64encode(optimized_bytes).decode('utf-8')
            
            # Fallback to original method
            with open(image_path, 'rb') as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
                
        except Exception as e:
            logger.error(f"Error encoding image {image_path}: {e}")
            return None
    
    def validate_image_for_processing(self, image_path: Path) -> tuple[bool, str]:
        """
        Validate image before processing to catch issues early.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        try:
            # Check if file exists and is readable
            if not image_path.exists():
                return False, "File does not exist"
            
            if not image_path.is_file():
                return False, "Path is not a file"
            
            # Check file size
            file_size = image_path.stat().st_size
            if file_size == 0:
                return False, "File is empty (0 bytes)"
            
            # Check if image format is supported
            if not self.is_supported_image(image_path):
                return False, f"Unsupported image format: {image_path.suffix}"
            
            # Check size limits for cloud providers
            if self.provider_name in ["claude", "openai"]:
                max_size = CLAUDE_MAX_SIZE if self.provider_name == "claude" else OPENAI_MAX_SIZE
                if file_size > max_size:
                    return False, f"Image too large ({file_size/1024/1024:.1f}MB > {max_size/1024/1024:.1f}MB limit for {self.provider_name})"
            
            # Try to open and validate the image with PIL
            try:
                from PIL import Image
                with Image.open(image_path) as img:
                    # Verify image integrity
                    img.verify()
                    
                # Re-open to get image info (verify() makes image unusable)
                with Image.open(image_path) as img:
                    width, height = img.size
                    
                    # Check if image dimensions are reasonable
                    if width < 1 or height < 1:
                        return False, f"Invalid image dimensions: {width}x{height}"
                    
                    # Check for extremely large dimensions that might cause memory issues
                    if width > 10000 or height > 10000:
                        return False, f"Image dimensions too large: {width}x{height} (may cause memory issues)"
                    
                    # Check total pixel count (memory usage estimation)
                    total_pixels = width * height
                    if total_pixels > 50_000_000:  # 50 megapixels
                        return False, f"Image too large: {total_pixels/1_000_000:.1f} megapixels (max 50 MP recommended)"
            
            except Exception as pil_error:
                return False, f"Invalid or corrupted image file: {str(pil_error)}"
            
            # All checks passed
            return True, ""
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def get_image_description(self, image_path: Path) -> Optional[str]:
        """
        Get description of an image using configured AI provider with retry logic
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Description string or None if failed
        """
        try:
            # Check if image is supported
            if not self.is_supported_image(image_path):
                logger.warning(f"Unsupported image format: {image_path}")
                return None
            
            # Optimize image size for cloud providers (Claude 5MB limit, OpenAI 20MB)
            if self.provider_name in ["claude", "openai"]:
                # Determine appropriate size limit based on provider
                max_size = CLAUDE_MAX_SIZE if self.provider_name == "claude" else OPENAI_MAX_SIZE
                # Use slightly smaller target to ensure we're under the limit (accounting for base64 encoding)
                target_size = TARGET_MAX_SIZE  # 3.75MB safe margin (accounts for ~33% base64 overhead)
                
                success, original_size, final_size = optimize_image_size(image_path, max_file_size=target_size)
                
                if original_size > target_size:
                    if success:
                        logger.info(f"Optimized {image_path.name} for {self.provider_name}: {original_size/1024/1024:.2f}MB -> {final_size/1024/1024:.2f}MB")
                    else:
                        logger.warning(f"Could not optimize {image_path.name} below {target_size/1024/1024:.1f}MB limit. Proceeding with {final_size/1024/1024:.2f}MB (may fail)")
            
            # Get prompt from configuration
            prompt = self.get_prompt()
            logger.debug(f"Using prompt: {repr(prompt)}")
            
            # For Ollama provider, use legacy direct API call for backward compatibility
            if self.provider_name == "ollama":
                # Encode image to base64
                image_base64 = self.encode_image_to_base64(image_path)
                if not image_base64:
                    return None
                
                # Get model settings from configuration
                model_settings = self.get_model_settings()
                logger.debug(f"Using model settings: {model_settings}")
                
                # Implement retry logic for Ollama API calls
                max_retries = 3
                base_delay = 2.0
                max_delay = 30.0
                backoff_multiplier = 2.0
                
                last_exception = None
                for attempt in range(max_retries + 1):  # +1 for initial attempt
                    try:
                        # Call Ollama API with configured settings
                        response = ollama.chat(
                            model=self.model_name,
                            messages=[
                                {
                                    'role': 'user',
                                    'content': prompt,
                                    'images': [image_base64]
                                }
                            ],
                            options=model_settings
                        )
                        
                        # If we get here, the call succeeded
                        if attempt > 0:
                            logger.info(f"  [RETRY] Success on attempt {attempt + 1} for {image_path.name}")
                        break
                        
                    except Exception as e:
                        last_exception = e
                        error_msg = str(e).lower()
                        error_type = type(e).__name__
                        
                        # Check if this is a retryable error
                        is_retryable = (
                            'server error' in error_msg or
                            'status code: 5' in error_msg or
                            '500' in error_msg or
                            'unmarshal' in error_msg or
                            'invalid character' in error_msg or
                            'timeout' in error_msg or
                            'connection' in error_msg.lower()
                        )
                        
                        if is_retryable and attempt < max_retries:
                            # Calculate delay with exponential backoff and jitter
                            import random
                            delay = min(base_delay * (backoff_multiplier ** attempt), max_delay)
                            jitter = random.uniform(0.1, 0.5) * delay
                            sleep_time = delay + jitter
                            
                            logger.warning(f"  [RETRY] Attempt {attempt + 1}/{max_retries + 1} failed for {image_path.name} ({error_type}): {str(e)[:100]}...")
                            logger.warning(f"  [RETRY] Retrying in {sleep_time:.1f}s...")
                            time.sleep(sleep_time)
                            continue
                        else:
                            # Non-retryable error or max retries reached
                            if attempt > 0:
                                logger.error(f"  [RETRY] All {max_retries + 1} attempts failed for {image_path.name}")
                            raise e
                else:
                    # This should not be reached, but handle it just in case
                    if last_exception:
                        raise last_exception
                
                logger.debug(f"Raw response: {response}")
                logger.debug(f"Response type: {type(response)}")
                logger.debug(f"Response keys: {response.keys() if hasattr(response, 'keys') else 'no keys'}")
                if 'message' in response:
                    logger.debug(f"Message: {response['message']}")
                    logger.debug(f"Message type: {type(response['message'])}")
                    if hasattr(response['message'], 'content'):
                        logger.debug(f"Message content: {repr(response['message'].content)}")
                    elif 'content' in response['message']:
                        logger.debug(f"Message content dict: {repr(response['message']['content'])}")
                
                description = response['message']['content'].strip()
                logger.info(f"Generated description for {image_path.name} (Provider: {self.provider_name}, Model: {self.model_name})")
                logger.debug(f"Description content: {repr(description)}")
                logger.debug(f"Description length: {len(description)}")
                logger.debug(f"Description bool: {bool(description)}")
                
                # Clean up memory
                del image_base64, response
                gc.collect()
                
                return description
            
            else:
                # Use provider's describe_image method for other providers
                logger.debug(f"Using provider: {self.provider_name}")
                
                # SAFETY CHECK: Ensure image size is under limit before sending to provider
                # This is a fallback in case the earlier optimization didn't run
                if self.provider_name in ["claude", "openai"]:
                    current_size = image_path.stat().st_size
                    max_allowed = CLAUDE_MAX_SIZE if self.provider_name == "claude" else OPENAI_MAX_SIZE
                    if current_size > TARGET_MAX_SIZE:
                        logger.warning(f"Image {image_path.name} is {current_size/1024/1024:.2f}MB (over {TARGET_MAX_SIZE/1024/1024:.1f}MB limit). Attempting emergency optimization...")
                        success, orig_size, final_size = optimize_image_size(image_path, max_file_size=TARGET_MAX_SIZE)
                        if not success:
                            logger.error(f"Emergency optimization failed! Image may be rejected by {self.provider_name} API")
                
                # Call provider's describe_image method with correct signature
                # Providers expect: describe_image(image_path: str, prompt: str, model: str)
                description = self.provider.describe_image(
                    image_path=str(image_path),
                    prompt=prompt,
                    model=self.model_name
                )
                
                if description:
                    logger.info(f"Generated description for {image_path.name} (Provider: {self.provider_name}, Model: {self.model_name})")
                    logger.debug(f"Description content: {repr(description)}")
                    
                    # Log token usage if provider supports it (OpenAI, Claude SDKs)
                    if hasattr(self.provider, 'get_last_token_usage'):
                        token_usage = self.provider.get_last_token_usage()
                        if token_usage:
                            logger.info(
                                f"Token usage: {token_usage['total_tokens']} total "
                                f"({token_usage['prompt_tokens']} prompt + "
                                f"{token_usage['completion_tokens']} completion)"
                            )
                            # Store for workflow-level statistics
                            if not hasattr(self, 'total_tokens'):
                                self.total_tokens = 0
                                self.total_prompt_tokens = 0
                                self.total_completion_tokens = 0
                            self.total_tokens += token_usage['total_tokens']
                            self.total_prompt_tokens += token_usage['prompt_tokens']
                            self.total_completion_tokens += token_usage['completion_tokens']
                    
                # Clean up memory
                gc.collect()
                
                return description
            
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
            logger.error(f"Error generating description for {image_path.name}: {error_type}: {error_msg}")
            
            # Check for specific Ollama issues
            if 'unmarshal' in error_msg and 'invalid character' in error_msg:
                logger.error(f"  This appears to be an Ollama server error returning HTML instead of JSON")
                logger.error(f"  Try restarting Ollama: 'ollama serve' or check Ollama logs")
            elif 'status code: 5' in error_msg:
                logger.error(f"  This is a server error (5xx) - the issue is with Ollama server, not your images")
            elif 'connection' in error_msg.lower():
                logger.error(f"  Connection issue - check if Ollama is running: 'ollama list'")
            
            # Also log to file if possible for debugging
            try:
                import json
                error_details = {
                    'timestamp': timestamp,
                    'provider': self.provider_name,
                    'model': self.model_name,
                    'image_path': str(image_path),
                    'error_type': error_type,
                    'error_message': error_msg,
                    'traceback': traceback.format_exc()
                }
                log_file = Path('api_errors.log')
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(error_details) + '\n')
                logger.debug(f"  Detailed error logged to: {log_file}")
            except Exception as log_error:
                logger.debug(f"  Warning: Could not write to error log: {log_error}")
            
            # Clean up memory on error
            gc.collect()
            return None
    
    def write_description_to_file(self, image_path: Path, description: str, output_file: Path, metadata: Dict[str, Any] = None, base_directory: Path = None) -> bool:
        """
        Write description to a text file
        
        Args:
            image_path: Path to the image file
            description: Description to write
            output_file: Path to the output text file
            metadata: Optional metadata dictionary to include
            base_directory: Base directory for calculating relative paths
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get output format settings
            output_format = self.config.get('output_format', {})
            separator_char = output_format.get('separator', '-')
            
            # Calculate relative path if base directory is provided
            if base_directory:
                try:
                    relative_path = image_path.relative_to(base_directory)
                    entry = f"File: {relative_path}\n"
                except ValueError:
                    # Fallback if relative path calculation fails
                    entry = f"File: {image_path.name}\n"
            else:
                entry = f"File: {image_path.name}\n"
            
            if output_format.get('include_file_path', True):
                entry += f"Path: {image_path}\n"
            
            # Add metadata if enabled and available
            if output_format.get('include_metadata', True) and metadata:
                metadata_str = self.format_metadata(metadata)
                if metadata_str:
                    entry += f"{metadata_str}\n"
            
            if output_format.get('include_model_info', True):
                entry += f"Provider: {self.provider_name}\n"
                entry += f"Model: {self.model_name}\n"
                entry += f"Prompt Style: {self.prompt_style}\n"
            
            entry += f"Description: {description}\n"
            
            if output_format.get('include_timestamp', True):
                entry += f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            
            entry += separator_char * 80 + "\n\n"
            
            # Append to the file
            with open(output_file, 'a', encoding='utf-8') as f:
                f.write(entry)
            
            logger.info(f"Successfully wrote description for {image_path.name} to {output_file.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error writing description to file: {e}")
            return False
    
    def process_directory(self, directory_path: Path, recursive: bool = False, 
                         max_files: Optional[int] = None) -> None:
        """
        Process all images in a directory with memory optimization
        
        Args:
            directory_path: Path to the directory containing images
            recursive: Whether to process subdirectories recursively
            max_files: Maximum number of files to process (for testing)
        """
        if not directory_path.exists():
            logger.error(f"Directory does not exist: {directory_path}")
            return
        
        if not directory_path.is_dir():
            logger.error(f"Path is not a directory: {directory_path}")
            return
        
        # Create output file path - use custom output dir or workflow structure
        if self.output_dir:
            # User specified custom output directory
            output_dir = Path(self.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / "image_descriptions.txt"
        else:
            # Use workflow output structure
            try:
                from workflow_utils import WorkflowConfig
                config = WorkflowConfig()
                output_dir = config.get_step_output_dir("image_description", create=True)
                output_file = output_dir / "image_descriptions.txt"
                logger.info(f"Using workflow output directory: {output_dir}")
            except ImportError:
                # Fallback to local directory if workflow_utils not available
                output_file = directory_path / "image_descriptions.txt"
        
        # Check for existing descriptions (resume capability)
        already_described = set()
        file_mode = 'w'  # Default to overwrite
        
        # Use a progress file to track completed images for reliable resume
        # Put it in the logs directory if available, otherwise next to output file
        if self.log_dir:
            progress_file = Path(self.log_dir) / "image_describer_progress.txt"
        else:
            progress_file = output_file.parent / "image_describer_progress.txt"
        
        if progress_file.exists():
            logger.info(f"Found progress file: {progress_file}")
            try:
                with open(progress_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        image_path_str = line.strip()
                        if image_path_str:
                            already_described.add(image_path_str)
                logger.info(f"Found {len(already_described)} already-described images in progress file, will skip them")
                file_mode = 'a'  # Append to existing file
            except Exception as e:
                logger.warning(f"Error reading progress file: {e}, will start fresh")
                file_mode = 'w'
        
        # Initialize or append to the output file with a header
        try:
            if file_mode == 'w':
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write("Image Descriptions Generated by Ollama Vision Model\n")
                    f.write("=" * 80 + "\n")
                    f.write(f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Model used: {self.model_name}\n")
                    f.write(f"Prompt style: {self.prompt_style}\n")
                    f.write(f"Directory: {directory_path}\n")
                    f.write(f"Runtime Configuration: Model='{self.model_name}', Prompt='{self.prompt_style}'\n")
                    f.write(f"Config File Model Settings: {self.config.get('model_settings', {})}\n")
                    f.write("=" * 80 + "\n\n")
                logger.info(f"Created output file: {output_file}")
                # Create new progress file
                progress_file.write_text("")
                logger.info(f"Created progress file: {progress_file}")
            else:
                logger.info(f"Appending to existing output file: {output_file}")
                logger.info(f"Using existing progress file for resume: {progress_file}")
        except Exception as e:
            logger.error(f"Error creating output file: {e}")
            return
        
        # Get all image files with timestamps for chronological sorting
        pattern = "**/*" if recursive else "*"
        image_files_with_time = []
        
        for file_path in directory_path.glob(pattern):
            if file_path.is_file() and self.is_supported_image(file_path):
                try:
                    # Use file modification time for chronological sorting
                    mtime = file_path.stat().st_mtime
                    image_files_with_time.append((mtime, file_path))
                except OSError as e:
                    # If stat fails, use current time as fallback
                    logger.debug(f"Could not get timestamp for {file_path}: {e}")
                    image_files_with_time.append((time.time(), file_path))
        
        if not image_files_with_time:
            logger.info("No supported image files found in the directory")
            return
        
        # Sort chronologically (oldest first)
        image_files_with_time.sort(key=lambda x: x[0])
        image_files = [f[1] for f in image_files_with_time]
        
        logger.info(f"Found {len(image_files)} image files")
        logger.info("Sorted files chronologically by modification time (oldest first)")
        
        # Limit files if specified
        if max_files and len(image_files) > max_files:
            image_files = image_files[:max_files]
            logger.info(f"Limited to first {max_files} files for processing")
        
        logger.info(f"Processing {len(image_files)} image files")
        
        # Process each image with memory management
        success_count = 0
        skip_count = 0
        failed_count = 0  # Track failed image descriptions
        newly_processed = 0  # Track images processed in this run (not skipped)
        failed_images = []  # Track details of failed images for summary
        overall_start_time = time.time()
        
        # Calculate how many images we expect to process (not skip)
        already_done_count = len(already_described)
        
        for i, image_path in enumerate(image_files, 1):
            # Check if this image was already described (resume support)
            if str(image_path) in already_described:
                skip_count += 1
                success_count += 1  # Count as success since it's already done
                logger.info(f"Skipping already-described image {success_count} of {len(image_files)}: {image_path.name}")
                
                # Update window title for skipped images too
                current_processed = success_count + failed_count
                progress_percent = int((current_processed / len(image_files)) * 100)
                set_console_title(f"IDT - Describing Images ({progress_percent}%, {current_processed} of {len(image_files)}) - Skipped")
                continue
            
            # Log progress and start time for this image
            newly_processed += 1
            success_count += 1
            # Show cumulative progress: where we are in total work
            logger.info(f"Describing image {success_count} of {len(image_files)}: {image_path.name}")
            
            # Update window title with progress
            current_processed = success_count + failed_count
            progress_percent = int((current_processed / len(image_files)) * 100)
            set_console_title(f"IDT - Describing Images ({progress_percent}%, {current_processed} of {len(image_files)})")
            
            image_start_time = time.time()
            logger.info(f"Start time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(image_start_time))}")
            
            # Validate image before processing
            is_valid, validation_error = self.validate_image_for_processing(image_path)
            if not is_valid:
                failed_count += 1
                success_count -= 1  # Adjust success count since we incremented it earlier
                failed_images.append({
                    'image': image_path.name,
                    'reason': 'Validation Failed',
                    'error_details': validation_error
                })
                logger.error(f"Validation failed for {image_path.name}: {validation_error}")
                
                # Update window title to reflect validation failure
                current_processed = success_count + failed_count
                progress_percent = int((current_processed / len(image_files)) * 100)
                set_console_title(f"IDT - Describing Images ({progress_percent}%, {current_processed} of {len(image_files)}) - Validation Failed")
                continue
            
            # Extract metadata from image
            metadata = self.extract_metadata(image_path)
            metadata_status = ""
            if metadata:
                sections = len(metadata)
                metadata_status = f" ({sections} metadata section{'s' if sections != 1 else ''})"
                logger.info(f"Extracted {sections} metadata section{'s' if sections != 1 else ''} for {image_path.name}")
            else:
                metadata_status = " (no metadata)"
                logger.debug(f"No metadata extracted for {image_path.name}")
            
            # Get description from AI provider
            logger.info(f"Getting AI description for {image_path.name}{metadata_status}")
            description = self.get_image_description(image_path)
            
            # Log end time for this image
            image_end_time = time.time()
            processing_duration = image_end_time - image_start_time
            logger.info(f"End time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(image_end_time))}")
            logger.info(f"Processing duration: {processing_duration:.2f} seconds")
            
            if description and not description.startswith("Error:"):
                # Write description to file with metadata and base directory for relative paths
                if self.write_description_to_file(image_path, description, output_file, metadata, directory_path):
                    # Update progress file immediately after successful write
                    try:
                        with open(progress_file, 'a', encoding='utf-8') as pf:
                            pf.write(f"{image_path}\n")
                        logger.debug(f"Updated progress file with: {image_path}")
                    except Exception as e:
                        logger.warning(f"Failed to update progress file: {e}")
                    # Log with relative path for better readability
                    try:
                        relative_path = image_path.relative_to(directory_path)
                        logger.info(f"Successfully processed: {relative_path}")
                    except ValueError:
                        logger.info(f"Successfully processed: {image_path.name}")
                else:
                    # File write failure
                    failed_count += 1
                    success_count -= 1  # Adjust success count since we incremented it earlier
                    failed_images.append({
                        'image': image_path.name,
                        'reason': 'File write failed',
                        'error_details': 'Could not write description to output file'
                    })
                    logger.error(f"Failed to write description for: {image_path.name}")
            else:
                # Description generation failure
                failed_count += 1
                success_count -= 1  # Adjust success count since we incremented it earlier
                error_reason = description if description else "No description generated"
                
                # Extract more specific error information
                if description and description.startswith("Error:"):
                    # Parse error message for better categorization
                    if "status code: 5" in description:
                        error_category = "Server Error"
                    elif "status code: 429" in description:
                        error_category = "Rate Limit"
                    elif "status code: 401" in description:
                        error_category = "Authentication"
                    elif "timeout" in description.lower():
                        error_category = "Timeout"
                    elif "Invalid request" in description:
                        error_category = "Invalid Request"
                    else:
                        error_category = "API Error"
                else:
                    error_category = "Unknown Error"
                
                failed_images.append({
                    'image': image_path.name,
                    'reason': error_category,
                    'error_details': error_reason
                })
                logger.error(f"Failed to generate description for: {image_path.name} - {error_reason}")
            
            # Memory management: add delay and force garbage collection
            if self.batch_delay > 0:
                time.sleep(self.batch_delay)
            gc.collect()
        
        # Log overall completion summary
        overall_end_time = time.time()
        total_duration = overall_end_time - overall_start_time
        
        # Update window title to show completion
        if failed_count > 0:
            set_console_title(f"IDT - Image Description Complete ({success_count} success, {failed_count} failed)")
        else:
            set_console_title(f"IDT - Image Description Complete ({success_count}/{len(image_files)} images)")
        
        logger.info(f"Processing complete. Successfully processed {success_count}/{len(image_files)} images")
        if skip_count > 0:
            logger.info(f"Skipped {skip_count} already-described images, processed {newly_processed} new images")
        if failed_count > 0:
            logger.info(f"Failed to process {failed_count} images")
        logger.info(f"Provider: {self.provider_name}, Model: {self.model_name}, Prompt Style: {self.prompt_style}")
        logger.info(f"Total processing time: {total_duration:.2f} seconds")
        if newly_processed > 0:
            logger.info(f"Average time per new image: {total_duration/newly_processed:.2f} seconds")
        
        # Generate comprehensive failure summary if there were failures
        if failed_count > 0:
            logger.info("=" * 80)
            logger.info("FAILURE SUMMARY:")
            logger.info(f"Total failed images: {failed_count}")
            
            # Group failures by reason for better analysis
            failure_categories = {}
            for failure in failed_images:
                category = failure['reason']
                if category not in failure_categories:
                    failure_categories[category] = []
                failure_categories[category].append(failure)
            
            # Report each category
            for category, failures in failure_categories.items():
                logger.info(f"\n{category} ({len(failures)} images):")
                for failure in failures[:5]:  # Show first 5 of each category
                    logger.info(f"  - {failure['image']}: {failure['error_details']}")
                if len(failures) > 5:
                    logger.info(f"  ... and {len(failures) - 5} more {category.lower()} failures")
            
            # Provide actionable recommendations
            logger.info("\nRECOMMENDATIONS:")
            for category, failures in failure_categories.items():
                if category == "Server Error":
                    logger.info(f"  - {category}: Cloud provider having issues. Try again later or switch providers.")
                elif category == "Rate Limit":
                    logger.info(f"  - {category}: Reduce processing speed or upgrade API plan.")
                elif category == "Authentication":
                    logger.info(f"  - {category}: Check your API key configuration.")
                elif category == "Timeout":
                    logger.info(f"  - {category}: Images may be too large. Try resizing or use different model.")
                elif category == "Invalid Request":
                    logger.info(f"  - {category}: Check image formats and sizes. May need conversion.")
                else:
                    logger.info(f"  - {category}: Check error details above and try reprocessing.")
            
            # Create failure report file
            try:
                failure_report_file = output_file.parent / f"failure_report_{time.strftime('%Y%m%d_%H%M%S')}.txt"
                with open(failure_report_file, 'w', encoding='utf-8') as f:
                    f.write(f"Image Processing Failure Report\n")
                    f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Provider: {self.provider_name}, Model: {self.model_name}\n")
                    f.write(f"Total failed: {failed_count}/{len(image_files)} images\n\n")
                    
                    for category, failures in failure_categories.items():
                        f.write(f"{category} ({len(failures)} images):\n")
                        for failure in failures:
                            f.write(f"  {failure['image']}: {failure['error_details']}\n")
                        f.write("\n")
                
                logger.info(f"\nDetailed failure report saved to: {failure_report_file}")
            except Exception as e:
                logger.warning(f"Could not create failure report file: {e}")
            
            logger.info("=" * 80)
        
        # Log token usage summary if available (OpenAI, Claude with SDK)
        if hasattr(self, 'total_tokens') and self.total_tokens > 0:
            logger.info("=" * 60)
            logger.info("TOKEN USAGE SUMMARY:")
            logger.info(f"  Total tokens: {self.total_tokens:,}")
            logger.info(f"  Prompt tokens: {self.total_prompt_tokens:,}")
            logger.info(f"  Completion tokens: {self.total_completion_tokens:,}")
            if newly_processed > 0:
                logger.info(f"  Average tokens per image: {self.total_tokens/newly_processed:.0f}")
            
            # Estimate costs (approximate rates as of 2025)
            cost_per_1k = {
                'gpt-4o': {'input': 0.0025, 'output': 0.010},
                'gpt-4o-mini': {'input': 0.00015, 'output': 0.0006},
                'claude-sonnet-4': {'input': 0.003, 'output': 0.015},
                'claude-opus-4': {'input': 0.015, 'output': 0.075},
                'claude-3-5-haiku': {'input': 0.001, 'output': 0.005}
            }
            
            # Try to estimate cost based on model name
            estimated_cost = None
            for model_key, rates in cost_per_1k.items():
                if model_key in self.model_name.lower():
                    input_cost = (self.total_prompt_tokens / 1000) * rates['input']
                    output_cost = (self.total_completion_tokens / 1000) * rates['output']
                    estimated_cost = input_cost + output_cost
                    break
            
            if estimated_cost:
                logger.info(f"  Estimated cost: ${estimated_cost:.4f}")
            logger.info("=" * 60)
        
        logger.info(f"Descriptions saved to: {output_file}")
    
    def extract_metadata(self, image_path: Path) -> Dict[str, Any]:
        """
        Extract EXIF metadata from an image file
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary containing extracted metadata
        """
        metadata = {}
        
        try:
            # Check if metadata extraction is enabled
            if not self.config.get('processing_options', {}).get('extract_metadata', False):
                logger.debug(f"Metadata extraction disabled for {image_path.name}")
                return metadata
            
            with Image.open(image_path) as img:
                # Use getexif() instead of _getexif() (modern method)
                exif_data = img.getexif()
                
                if not exif_data:
                    logger.debug(f"No EXIF data found in {image_path.name} (this is normal for screenshots, web images, etc.)")
                    return metadata
                
                if exif_data:
                    # Convert EXIF data to human-readable format
                    exif_dict = {}
                    for tag_id, value in exif_data.items():
                        tag = TAGS.get(tag_id, tag_id)
                        exif_dict[tag] = value
                    
                    metadata_sections = 0
                    
                    # Extract all available metadata
                    datetime_info = self._extract_datetime(exif_dict)
                    if datetime_info:
                        metadata['datetime'] = datetime_info
                        metadata_sections += 1
                    
                    location_info = self._extract_location(exif_dict)
                    if location_info:
                        metadata['location'] = location_info
                        metadata_sections += 1
                    
                    camera_info = self._extract_camera_info(exif_dict)
                    if camera_info:
                        metadata['camera'] = camera_info
                        metadata_sections += 1
                    
                    technical_info = self._extract_technical_info(exif_dict)
                    if technical_info:
                        metadata['technical'] = technical_info
                        metadata_sections += 1
                    
                    if metadata_sections > 0:
                        logger.debug(f"Extracted {metadata_sections} metadata sections from {image_path.name}")
                    else:
                        logger.debug(f"EXIF data present but no usable metadata extracted from {image_path.name}")
                            
        except Exception as e:
            logger.info(f"Could not extract metadata from {image_path.name}: {e} (image may not support EXIF)")
        
        return metadata
    
    def _extract_datetime(self, exif_data: dict) -> Optional[str]:
        """Extract date and time from EXIF data"""
        try:
            # Try different datetime fields
            datetime_fields = ['DateTime', 'DateTimeOriginal', 'DateTimeDigitized']
            
            for field in datetime_fields:
                if field in exif_data:
                    dt_str = exif_data[field]
                    if dt_str:
                        # Parse and format the datetime
                        try:
                            dt = datetime.strptime(dt_str, '%Y:%m:%d %H:%M:%S')
                            return dt.strftime('%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            # Try alternative format
                            try:
                                dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
                                return dt.strftime('%Y-%m-%d %H:%M:%S')
                            except ValueError:
                                logger.debug(f"Could not parse datetime format: {dt_str}")
                                continue
        except Exception as e:
            logger.debug(f"Error extracting datetime: {e}")
        
        return None
    
    def _extract_location(self, exif_data: dict) -> Optional[Dict[str, Any]]:
        """Extract GPS location from EXIF data"""
        try:
            gps_info = exif_data.get('GPSInfo')
            if not gps_info:
                return None
            
            # Convert GPS info to readable format
            gps_dict = {}
            for tag_id, value in gps_info.items():
                tag = GPSTAGS.get(tag_id, tag_id)
                gps_dict[tag] = value
            
            location = {}
            
            # Extract latitude
            if 'GPSLatitude' in gps_dict and 'GPSLatitudeRef' in gps_dict:
                lat = self._convert_gps_coordinate(gps_dict['GPSLatitude'])
                if gps_dict['GPSLatitudeRef'] == 'S':
                    lat = -lat
                location['latitude'] = lat
            
            # Extract longitude
            if 'GPSLongitude' in gps_dict and 'GPSLongitudeRef' in gps_dict:
                lon = self._convert_gps_coordinate(gps_dict['GPSLongitude'])
                if gps_dict['GPSLongitudeRef'] == 'W':
                    lon = -lon
                location['longitude'] = lon
            
            # Extract altitude
            if 'GPSAltitude' in gps_dict:
                altitude = float(gps_dict['GPSAltitude'])
                if 'GPSAltitudeRef' in gps_dict and gps_dict['GPSAltitudeRef'] == 1:
                    altitude = -altitude
                location['altitude'] = altitude
            
            return location if location else None
            
        except Exception as e:
            logger.debug(f"Error extracting location: {e}")
        
        return None
    
    def _extract_camera_info(self, exif_data: dict) -> Optional[Dict[str, str]]:
        """Extract camera information from EXIF data"""
        try:
            camera_info = {}
            
            # Camera make and model
            if 'Make' in exif_data:
                camera_info['make'] = exif_data['Make']
            if 'Model' in exif_data:
                camera_info['model'] = exif_data['Model']
            
            # Lens information
            if 'LensModel' in exif_data:
                camera_info['lens'] = exif_data['LensModel']
            
            return camera_info if camera_info else None
            
        except Exception as e:
            logger.debug(f"Error extracting camera info: {e}")
        
        return None
    
    def _extract_technical_info(self, exif_data: dict) -> Optional[Dict[str, Any]]:
        """Extract technical camera settings from EXIF data"""
        try:
            technical_info = {}
            
            # ISO
            if 'ISOSpeedRatings' in exif_data:
                technical_info['iso'] = exif_data['ISOSpeedRatings']
            elif 'ISO' in exif_data:
                technical_info['iso'] = exif_data['ISO']
            
            # Aperture
            if 'FNumber' in exif_data:
                f_number = exif_data['FNumber']
                if isinstance(f_number, tuple) and len(f_number) == 2:
                    f_value = f_number[0] / f_number[1]
                    technical_info['aperture'] = f"f/{f_value:.1f}"
                else:
                    technical_info['aperture'] = f"f/{f_number}"
            
            # Shutter speed
            if 'ExposureTime' in exif_data:
                exposure_time = exif_data['ExposureTime']
                if isinstance(exposure_time, tuple) and len(exposure_time) == 2:
                    if exposure_time[0] == 1:
                        technical_info['shutter_speed'] = f"1/{exposure_time[1]}s"
                    else:
                        technical_info['shutter_speed'] = f"{exposure_time[0]/exposure_time[1]}s"
                else:
                    technical_info['shutter_speed'] = f"{exposure_time}s"
            
            # Focal length
            if 'FocalLength' in exif_data:
                focal_length = exif_data['FocalLength']
                if isinstance(focal_length, tuple) and len(focal_length) == 2:
                    fl_value = focal_length[0] / focal_length[1]
                    technical_info['focal_length'] = f"{fl_value:.0f}mm"
                else:
                    technical_info['focal_length'] = f"{focal_length}mm"
            
            return technical_info if technical_info else None
            
        except Exception as e:
            logger.debug(f"Error extracting technical info: {e}")
        
        return None
    
    def _convert_gps_coordinate(self, coord_tuple) -> float:
        """Convert GPS coordinate from tuple format to decimal degrees"""
        try:
            degrees = float(coord_tuple[0])
            minutes = float(coord_tuple[1])
            seconds = float(coord_tuple[2])
            return degrees + (minutes / 60.0) + (seconds / 3600.0)
        except:
            return 0.0
    
    def format_metadata(self, metadata: Dict[str, Any]) -> str:
        """
        Format metadata for display in output file
        
        Args:
            metadata: Dictionary containing metadata
            
        Returns:
            Formatted metadata string
        """
        if not metadata:
            return ""
        
        lines = []
        
        # Format datetime
        if 'datetime' in metadata:
            lines.append(f"Photo Date: {metadata['datetime']}")
        
        # Format location
        if 'location' in metadata:
            location = metadata['location']
            location_parts = []
            
            if 'latitude' in location and 'longitude' in location:
                location_parts.append(f"GPS: {location['latitude']:.6f}, {location['longitude']:.6f}")
            
            if 'altitude' in location:
                location_parts.append(f"Altitude: {location['altitude']:.1f}m")
            
            if location_parts:
                lines.append("Location: " + ", ".join(location_parts))
        
        # Format camera info
        if 'camera' in metadata:
            camera = metadata['camera']
            camera_parts = []
            
            if 'make' in camera and 'model' in camera:
                camera_parts.append(f"{camera['make']} {camera['model']}")
            
            if 'lens' in camera:
                camera_parts.append(f"Lens: {camera['lens']}")
            
            if camera_parts:
                lines.append("Camera: " + ", ".join(camera_parts))
        
        # Format technical info
        if 'technical' in metadata:
            technical = metadata['technical']
            technical_parts = []
            
            for key, value in technical.items():
                technical_parts.append(f"{key.replace('_', ' ').title()}: {value}")
            
            if technical_parts:
                lines.append("Settings: " + ", ".join(technical_parts))
        
        return "\n".join(lines)

    # ...existing code...
def get_default_prompt_style(config_file: str = "image_describer_config.json") -> str:
    """Layered resolution default prompt style using config_loader.

    Falls back to previous behavior if config_loader not available.
    """
    try:
        from config_loader import load_json_config
        cfg, path, source = load_json_config('image_describer_config.json', explicit=config_file if config_file != 'image_describer_config.json' else None, env_var_file='IDT_IMAGE_DESCRIBER_CONFIG')
        if cfg:
            default_style = cfg.get('default_prompt_style', 'detailed')
            prompt_variations = cfg.get('prompt_variations', {})
            lower_variations = {k.lower(): k for k in prompt_variations}
            if default_style.lower() in lower_variations:
                resolved = lower_variations[default_style.lower()]
            elif 'detailed' in lower_variations:
                resolved = lower_variations['detailed']
            elif prompt_variations:
                resolved = list(prompt_variations.keys())[0]
            else:
                resolved = 'detailed'
            try:
                logger.debug(f"Resolved default prompt style '{resolved}' from {path} (source={source})")
            except Exception:
                pass
            return resolved
    except Exception:
        pass
    # Fallback legacy path
    try:
        config_path = Path(config_file)
        if not config_path.is_absolute():
            config_path = Path(__file__).parent / config_file
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            default_style = cfg.get('default_prompt_style', 'detailed')
            prompt_variations = cfg.get('prompt_variations', {})
            lower_variations = {k.lower(): k for k in prompt_variations}
            if default_style.lower() in lower_variations:
                return lower_variations[default_style.lower()]
            if 'detailed' in lower_variations:
                return lower_variations['detailed']
            if prompt_variations:
                return list(prompt_variations.keys())[0]
    except Exception:
        pass
    return 'detailed'


def get_available_prompt_styles(config_file: str = "image_describer_config.json") -> list:
    """
    Get available prompt styles from configuration file
    
    Args:
        config_file: Path to configuration file
        
    Returns:
        List of available prompt style names
    """
    try:
        config_path = Path(config_file)
        if not config_path.is_absolute():
            script_dir = Path(__file__).parent
            config_path = script_dir / config_file
        
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return list(config.get('prompt_variations', {}).keys())
    except:
        pass
    
    # Default fallback
    return ["detailed", "concise", "artistic", "technical"]


def main():
    """Main function to run the image description script"""
    
    # Quick check for --list-providers before full argument parsing
    if '--list-providers' in sys.argv:
        print("Available AI Providers:")
        print("=" * 60)
        print()
        print("ollama       - Local Ollama models (default)")
        print("             Models: llava, llava:7b, llava:13b, moondream, etc.")
        print("             Requires: Ollama running locally")
        print()
        print("openai       - OpenAI cloud models")
        print("             Models: gpt-4o, gpt-4o-mini, gpt-4-vision-preview")
        print("             Requires: API key (--api-key-file or OPENAI_API_KEY)")
        print()
        print("onnx         - Enhanced Ollama with YOLO object detection")
        print("             Models: Same as Ollama")
        print("             Features: NPU acceleration, spatial awareness")
        print()
        print("copilot      - Copilot+ PC NPU acceleration")
        print("             Models: florence-2")
        print("             Requires: Copilot+ PC with NPU, DirectML")
        print()
        print("huggingface  - HuggingFace Inference API")
        print("             Models: Various vision models on HF")
        print("             Requires: API key (--api-key-file or HUGGINGFACE_API_KEY)")
        print()
        print("=" * 60)
        sys.exit(0)
    
    # Get available prompt styles and default from config with override support
    # Try layered config resolution (env var or external dir). Fallback silently to existing helpers on failure.
    try:
        from config_loader import load_json_config
        cfg_dict, cfg_path, cfg_source = load_json_config('image_describer_config.json', explicit=None, env_var_file='IDT_IMAGE_DESCRIBER_CONFIG')
        if cfg_dict:
            variations = cfg_dict.get('prompt_variations', {})
            available_styles = list(variations.keys()) or get_available_prompt_styles()
            declared_default = cfg_dict.get('default_prompt_style') or get_default_prompt_style()
            lower_map = {k.lower(): k for k in available_styles}
            default_style = lower_map.get(declared_default.lower(), declared_default if declared_default in available_styles else get_default_prompt_style())
            logger.info(f"Using image_describer_config from {cfg_path} (source={cfg_source}); default style '{default_style}'")
        else:
            available_styles = get_available_prompt_styles()
            default_style = get_default_prompt_style()
    except Exception:
        available_styles = get_available_prompt_styles()
        default_style = get_default_prompt_style()
    
    parser = argparse.ArgumentParser(
        description="Process images with AI vision models and save descriptions to a text file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Available prompt styles: {', '.join(available_styles)}
Default prompt style: {default_style}

Examples:
  # Ollama (default provider)
  python {Path(__file__).name} exportedphotos
  python {Path(__file__).name} exportedphotos --prompt-style artistic --model llava:7b
  python {Path(__file__).name} exportedphotos --model llava:13b --prompt-style technical
  
  # OpenAI
  python {Path(__file__).name} exportedphotos --provider openai --model gpt-4o-mini --api-key-file ~/openai.txt
  python {Path(__file__).name} exportedphotos --provider openai --model gpt-4-vision-preview
  
  # Claude (Anthropic)
  python {Path(__file__).name} exportedphotos --provider claude --model claude-sonnet-4-5-20250929 --api-key-file ~/claude.txt
  python {Path(__file__).name} exportedphotos --provider claude --model claude-3-5-haiku-20241022
  
  # ONNX (Enhanced Ollama with YOLO detection)
  python {Path(__file__).name} exportedphotos --provider onnx --model llava:latest
  
  # Copilot+ PC NPU
  python {Path(__file__).name} exportedphotos --provider copilot --model florence-2

Configuration:
  Use config_helper.py to manage settings:
    python config_helper.py help    - Show configuration help
    python config_helper.py show    - Show current configuration  
    python config_helper.py modify  - Interactive configuration editor
        """
    )
    parser.add_argument(
        "directory",
        type=str,
        help="Directory containing images to process"
    )
    parser.add_argument(
        "--provider",
        type=str,
        default="ollama",
        choices=["ollama", "openai", "claude"],
        help="AI provider to use (default: ollama)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Model name to use (default: from image_describer_config.json or provider default)"
    )
    parser.add_argument(
        "--api-key-file",
        type=str,
        help="Path to file containing API key for cloud providers (OpenAI, Claude)"
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Process subdirectories recursively"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--max-size",
        type=int,
        default=1024,
        help="Maximum image dimension for processing (default: 1024)"
    )
    parser.add_argument(
        "--no-compression",
        action="store_true",
        help="Disable image compression"
    )
    parser.add_argument(
        "--batch-delay",
        type=float,
        default=2.0,
        help="Delay between processing images in seconds (default: 2.0)"
    )
    parser.add_argument(
        "--max-files",
        type=int,
        help="Maximum number of files to process (for testing)"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="image_describer_config.json",
        help="Path to JSON configuration file (default: image_describer_config.json)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        help="Output directory for description file (default: workflow_output/descriptions/)"
    )
    parser.add_argument(
        "--log-dir",
        type=str,
        help="Directory for log files (default: uses workflow output/logs)"
    )
    parser.add_argument(
        "--prompt-style",
        type=str,
        default=default_style,
        choices=available_styles,
        help=f"Style of prompt to use. Available: {', '.join(available_styles)} (default: {default_style})"
    )
    parser.add_argument(
        "--no-metadata",
        action="store_true",
        help="Disable metadata extraction from image files"
    )
    parser.add_argument(
        "--list-providers",
        action="store_true",
        help="List available AI providers and exit"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress console output (log to file only)"
    )
    
    args = parser.parse_args()
    
    # Set up logging with log directory, verbosity, and quiet mode
    setup_logging(log_dir=args.log_dir, verbose=args.verbose, quiet=args.quiet)
    
    # Convert directory path to Path object
    directory_path = Path(args.directory)
    
    # Load API key if provided
    api_key = None
    if args.api_key_file:
        try:
            api_key_path = Path(args.api_key_file).expanduser()
            logger.info(f"Attempting to load API key from: {api_key_path}")
            logger.info(f"File exists: {api_key_path.exists()}")
            logger.info(f"Absolute path: {api_key_path.resolve()}")
            with open(api_key_path, 'r', encoding='utf-8') as f:
                api_key = f.read().strip()
            logger.info(f"Successfully loaded API key from {api_key_path} (length: {len(api_key)})")
            # Print to console for immediate feedback
            print(f"INFO: Loaded API key from {api_key_path} (length: {len(api_key)})")
        except Exception as e:
            logger.error(f"Failed to load API key from {args.api_key_file}: {e}")
            print(f"ERROR: Failed to load API key from {args.api_key_file}: {e}")
            sys.exit(1)
    
    # Check for API key in environment variables if not provided via file
    if not api_key and args.provider in ["openai", "huggingface", "claude"]:
        if args.provider == "openai":
            env_var = "OPENAI_API_KEY"
        elif args.provider == "claude":
            env_var = "ANTHROPIC_API_KEY"
        else:
            env_var = "HUGGINGFACE_API_KEY"
        
        api_key = os.environ.get(env_var)
        if api_key:
            logger.info(f"Using API key from environment variable {env_var}")
        else:
            logger.error(f"Provider '{args.provider}' requires an API key.")
            logger.error(f"Provide it via --api-key-file or set {env_var} environment variable")
            sys.exit(1)
    
    # Create ImageDescriber instance with memory optimization
    describer = ImageDescriber(
        model_name=args.model,
        max_image_size=args.max_size,
        enable_compression=not args.no_compression,
        batch_delay=args.batch_delay,
        config_file=args.config,
        prompt_style=args.prompt_style,
        output_dir=args.output_dir,
        provider=args.provider,
        api_key=api_key,
        log_dir=args.log_dir
    )
    
    # Override metadata extraction if disabled via command line
    if args.no_metadata:
        describer.config['processing_options']['extract_metadata'] = False
        describer.config['output_format']['include_metadata'] = False
    
    # Check provider availability (only for Ollama to maintain backward compatibility)
    if args.provider == "ollama":
        try:
            ollama.list()
            logger.info("Ollama is available")
        except Exception as e:
            logger.error(f"Ollama is not available or not running: {e}")
            logger.error("Please make sure Ollama is installed and running")
            sys.exit(1)
        
        # Check if the specified model is available
        try:
            models = ollama.list()
            available_models = [model['name'] for model in models.get('models', [])]
            if describer.model_name not in available_models:
                logger.error(f"Model '{describer.model_name}' is not available")
                logger.error(f"Available models: {', '.join(available_models)}")
                logger.info(f"You can install the model with: ollama pull {describer.model_name}")
                sys.exit(1)
            else:
                logger.info(f"Using provider: {describer.provider_name}, model: {describer.model_name}")
        except Exception as e:
            logger.warning(f"Could not check available models: {e}")
    
    # Process the directory
    try:
        describer.process_directory(directory_path, recursive=args.recursive, 
                                   max_files=args.max_files)
    except KeyboardInterrupt:
        logger.info("Processing interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
