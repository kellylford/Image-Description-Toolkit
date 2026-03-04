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

# Import shared window title builder
try:
    from shared.window_title_builder import build_window_title_from_context
except ImportError:
    build_window_title_from_context = None

# Import shared metadata extraction module
try:
    from metadata_extractor import MetadataExtractor, NominatimGeocoder
    METADATA_SUPPORT = True
except ImportError:
    METADATA_SUPPORT = False
    MetadataExtractor = None
    NominatimGeocoder = None


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

# Try to enable HEIC support for better metadata extraction from iPhone photos
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    HEIC_SUPPORT = True
except ImportError:
    HEIC_SUPPORT = False
    # Will warn user if HEIC files are encountered

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
    ClaudeProvider,
    HuggingFaceProvider,
    MLXProvider,
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
                 log_dir: str = None, workflow_name: str = None, timeout: int = 90, source_url: str = None):
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
            provider: AI provider to use (ollama, openai, claude, huggingface)
            api_key: API key for providers that require authentication
            log_dir: Directory where log files and progress tracking are stored
            workflow_name: Name of the workflow (for window title display)
            timeout: Timeout in seconds for Ollama API requests (default: 90)
            source_url: Source URL if images were downloaded from the web
        """
        # Load configuration first
        self.config = self.load_config(config_file)
        
        # Set model name with priority:
        # 1. Parameter (command-line argument)
        # 2. Config default_model (preferred)
        # 3. Config model_settings.model (legacy)
        # 4. Fallback to 'moondream'
        if model_name is not None:
            self.model_name = model_name
        else:
            # Try default_model first (new field)
            self.model_name = self.config.get('default_model')
            if not self.model_name:
                # Fallback to legacy model_settings.model
                self.model_name = self.config.get('model_settings', {}).get('model')
            if not self.model_name:
                # Final fallback
                self.model_name = 'moondream'
        
        # Set prompt style - parameter has already been resolved by argparse
        # (argparse loads config default if not specified on command line)
        self.prompt_style = prompt_style if prompt_style else 'detailed'
        
        # Set provider with priority:
        # 1. Parameter (command-line argument)  
        # 2. Config default_provider
        # 3. Fallback to 'ollama'
        if provider != "ollama":
            self.provider_name = provider.lower()
        else:
            # Check config for default provider
            config_default_provider = self.config.get('default_provider', 'ollama')
            self.provider_name = config_default_provider.lower()
        
        self.max_image_size = max_image_size
        self.enable_compression = enable_compression
        self.batch_delay = batch_delay
        self.output_dir = output_dir  # Custom output directory
        self.log_dir = log_dir  # Directory for logs and progress tracking
        self.api_key = api_key
        self.workflow_name = workflow_name  # Workflow name for window title
        self.timeout = timeout  # Timeout for Ollama requests
        self.source_url = source_url  # Source URL if downloaded from web
        # Notice flags (avoid repeating log spam)
        self._geocode_notice_logged = False
        
        # Set supported formats from config
        self.supported_formats = set(self.config.get('processing_options', {}).get('supported_formats', 
                                                    ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']))
        
        # Initialize metadata extractor and geocoder (if enabled)
        self.metadata_extractor = None
        self.geocoder = None
        if METADATA_SUPPORT:
            self.metadata_extractor = MetadataExtractor()
            
            # Initialize geocoder if enabled in config
            metadata_config = self.config.get('metadata', {})
            geocoding_config = metadata_config.get('geocoding', {})
            if geocoding_config.get('enabled', False):
                user_agent = geocoding_config.get('user_agent', 'IDT/3.0 (+https://github.com/kellylford/Image-Description-Toolkit)')
                delay = geocoding_config.get('delay_seconds', 1.0)
                cache_file = geocoding_config.get('cache_file', 'geocode_cache.json')
                cache_path = Path(cache_file) if cache_file else None
                self.geocoder = NominatimGeocoder(user_agent=user_agent, delay_seconds=delay, cache_path=cache_path)
                logger.info(f"Geocoding enabled with cache: {cache_path}")
        
        # Initialize the AI provider
        self.provider = self._initialize_provider()
        
        logger.info(f"Initialized ImageDescriber with provider: {self.provider_name}, model: {self.model_name}")
    
    def _build_window_title(self, progress_percent: int, current: int, total: int, suffix: str = "") -> str:
        """Build a descriptive window title with workflow context"""
        if build_window_title_from_context:
            return build_window_title_from_context(
                progress_percent=progress_percent,
                current=current,
                total=total,
                operation="Describing Images",
                workflow_name=self.workflow_name,
                prompt_style=self.prompt_style,
                model_name=self.model_name,
                suffix=suffix
            )
        else:
            return self._build_window_title_fallback(
                progress_percent=progress_percent,
                current=current,
                total=total,
                suffix=suffix
            )
    
    def _build_window_title_fallback(self, progress_percent: int, current: int, total: int, suffix: str = "") -> str:
        """Fallback window title builder (used when shared module unavailable)"""
        base_title = f"IDT - Describing Images ({progress_percent}%, {current} of {total})"
        
        # Add suffix if provided (e.g., " - Skipped", " - Validation Failed")
        if suffix:
            base_title += suffix
        
        # Add workflow context: workflow name, prompt style, and model
        context_parts = []
        if self.workflow_name:
            context_parts.append(self.workflow_name)
        if self.prompt_style:
            context_parts.append(self.prompt_style)
        if self.model_name:
            context_parts.append(self.model_name)
        
        if context_parts:
            base_title += f" - {' - '.join(context_parts)}"
        
        return base_title
    
    def _initialize_provider(self):
        """Initialize the AI provider based on configuration"""
        try:
            if self.provider_name == "ollama":
                logger.info("Initializing Ollama provider...")
                provider = OllamaProvider()
                # Verify model is available (guard if python client missing)
                try:
                    if ollama is not None and hasattr(ollama, 'list'):
                        models = ollama.list()
                        available_models = [model['name'] for model in models.get('models', [])]
                        # Smart model name matching: handle :latest suffix
                        model_found = self.model_name in available_models
                        if not model_found and ':' not in self.model_name:
                            # Try with :latest suffix
                            if f"{self.model_name}:latest" in available_models:
                                model_found = True
                            # Or check if any available model starts with this base name
                            else:
                                base_matches = [m for m in available_models if m.startswith(f"{self.model_name}:")]
                                if base_matches:
                                    model_found = True
                        
                        if not model_found:
                            logger.warning(f"Model '{self.model_name}' not found in Ollama")
                            logger.info(f"Available models: {', '.join(available_models)}")
                            logger.info(f"Tip: Install with 'ollama pull {self.model_name}'")
                    else:
                        # Try lightweight HTTP probe as a best-effort check
                        try:
                            import requests
                            tags = requests.get("http://127.0.0.1:11434/api/tags", timeout=3).json()
                            available_models = [m.get('name') for m in tags.get('models', []) if m.get('name')]
                            if available_models:
                                # Smart model name matching: handle :latest suffix
                                model_found = self.model_name in available_models
                                if not model_found and ':' not in self.model_name:
                                    # Try with :latest suffix or base name match
                                    if f"{self.model_name}:latest" in available_models:
                                        model_found = True
                                    else:
                                        base_matches = [m for m in available_models if m.startswith(f"{self.model_name}:")]
                                        if base_matches:
                                            model_found = True
                                
                                if not model_found:
                                    logger.warning(f"Model '{self.model_name}' not in tags list from Ollama HTTP API")
                        except Exception:
                            # Silent: availability is checked later during actual call
                            pass
                except Exception as e:
                    logger.warning(f"Could not verify Ollama models: {e}")
                return provider
                
            elif self.provider_name == "openai":
                logger.info("Initializing OpenAI provider...")
                # Pass api_key (may be None - provider will check config/env/files)
                provider = OpenAIProvider(api_key=self.api_key)
                if not provider.is_available():
                    raise ValueError(
                        "OpenAI provider requires an API key. Provide via:\n"
                        "  1. Config file: image_describer_config.json → api_keys.OpenAI\n"
                        "  2. Command line: --api-key-file /path/to/openai.txt\n"
                        "  3. Environment: export OPENAI_API_KEY=sk-...\n"
                        "  4. Text file: openai.txt in current directory"
                    )
                return provider
                
            elif self.provider_name == "claude":
                logger.info("Initializing Claude provider...")
                # Pass api_key (may be None - provider will check config/env/files)
                provider = ClaudeProvider(api_key=self.api_key)
                if not provider.is_available():
                    raise ValueError(
                        "Claude provider requires an API key. Provide via:\n"
                        "  1. Config file: image_describer_config.json → api_keys.Claude\n"
                        "  2. Command line: --api-key-file /path/to/claude.txt\n"
                        "  3. Environment: export ANTHROPIC_API_KEY=sk-ant-...\n"
                        "  4. Text file: claude.txt in current directory"
                    )
                logger.info(f"Claude provider initialized. API key set: {bool(provider.api_key)}, Client available: {bool(provider.client)}, Is available: {provider.is_available()}")
                print(f"INFO: Claude provider - API key set: {bool(provider.api_key)}, Client: {bool(provider.client)}, Available: {provider.is_available()}")
                if not provider.is_available():
                    raise ValueError("Claude provider requires an API key. Provide via --api-key-file, config file (image_describer_config.json), or ANTHROPIC_API_KEY environment variable.")
                return provider
                
            elif self.provider_name == "huggingface":
                logger.info("Initializing HuggingFace provider...")
                provider = HuggingFaceProvider()
                if not provider.is_available():
                    raise ValueError("HuggingFace provider requires Florence-2 dependencies. Install with: pip install 'transformers>=4.45.0' torch torchvision einops timm")
                return provider

            elif self.provider_name == "mlx":
                logger.info("Initializing MLX (Apple Metal) provider...")
                provider = MLXProvider()
                if not provider.is_available():
                    import platform as _platform
                    if _platform.system() != "Darwin":
                        raise ValueError(
                            "MLX provider is only available on macOS with Apple Silicon."
                        )
                    raise ValueError(
                        "MLX provider requires mlx-vlm. Install with:\n"
                        "  pip install mlx-vlm"
                    )
                logger.info(
                    f"MLX provider ready. Model will be loaded on first image "
                    f"and kept in Metal memory for the batch."
                )
                return provider

            else:
                raise ValueError(f"Unknown provider: {self.provider_name}. Supported: ollama, openai, claude, huggingface, mlx")
                
        except Exception as e:
            logger.error(f"Failed to initialize provider '{self.provider_name}': {e}")
            raise
    
    def load_config(self, config_file: str) -> dict:
        """
        Load configuration from JSON file.

        Uses config_loader for the full layered resolution (user config dir,
        bundled _MEIPASS defaults, explicit path, env vars) so this works
        correctly on both macOS and Windows in dev and frozen modes.

        Args:
            config_file: Filename (e.g. 'image_describer_config.json') or
                         absolute path.

        Returns:
            Dictionary with configuration settings
        """
        try:
            # If caller passed an absolute path that exists, use it directly.
            config_path = Path(config_file)
            if config_path.is_absolute() and config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logger.info(f"Loaded configuration from: {config_path}")
                return config

            # Otherwise delegate to the layered resolver so user-overridden
            # configs and bundled defaults are found in the right order on
            # every platform (macOS ~/Library/…, Windows %APPDATA%\…, etc.)
            try:
                from config_loader import load_json_config
                filename = config_path.name  # strip any relative prefix
                config, resolved_path, source = load_json_config(filename)
                if config:
                    logger.info(f"Loaded configuration from: {resolved_path} (source: {source})")
                    prompts = config.get('prompt_variations', {})
                    default_prompt = config.get('default_prompt_style', 'N/A')
                    logger.debug(f"Config has {len(prompts)} prompts, default={default_prompt}")
                    return config
            except Exception as cl_err:
                logger.debug(f"config_loader failed ({cl_err}), falling back to direct path")

            # Last-resort fallback: look in same directory as this script
            script_dir = Path(__file__).parent
            fallback = script_dir / config_path.name
            if fallback.exists():
                with open(fallback, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logger.info(f"Loaded configuration from fallback: {fallback}")
                return config

            logger.warning(f"Config file not found: {config_file}")
            return self.get_default_config()

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
            prompt_text = lower_variations[self.prompt_style.lower()]
            logger.debug(f"Using prompt style '{self.prompt_style}' ({len(prompt_text)} chars)")
            return prompt_text
        else:
            # Fallback to default prompt_template
            logger.warning(f"Prompt style '{self.prompt_style}' not found in config, using prompt_template fallback")
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
    
    def _get_output_file(self, base_dir: Path) -> Path:
        """Determine output file path for descriptions."""
        if self.output_dir:
            base = Path(self.output_dir)
        else:
            base = base_dir / "descriptions"
        return base / "image_descriptions.txt"

    def _write_description_entry(self, output_file: Path, image_path: Path, description: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Write a single viewer-compatible entry to the output file."""
        separator = '-' * 80
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        rel = image_path.name
        lines = [
            separator,
            f"File: {rel}",
            f"Path: {str(image_path.resolve())}",
            f"Provider: {self.provider_name}",
            f"Model: {self.model_name}",
            f"Prompt Style: {self.prompt_style}",
            f"Timestamp: {timestamp}",
        ]
        # Add source URL if available (for downloaded images)
        if self.source_url:
            lines.append(f"Source URL: {self.source_url}")
        # Optional compact metadata suffix (for human skim); main metadata block inclusion can be added later
        if metadata and self.config.get('output_format', {}).get('include_metadata', True):
            suffix = self._build_meta_suffix(image_path, metadata)
            if suffix:
                lines.append(suffix)
        # Description block
        first_line, *rest = (description or '').splitlines()
        lines.append(f"Description: {first_line or ''}")
        for extra in rest:
            lines.append(extra)
        lines.append('\n')
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with output_file.open('a', encoding='utf-8') as f:
            f.write('\n'.join(lines))

    def process_directory(self, directory_path: Path, recursive: bool = False, max_files: Optional[int] = None) -> None:
        """Process all supported images in a directory and write descriptions file."""
        if not directory_path.exists() or not directory_path.is_dir():
            raise ValueError(f"Input directory does not exist: {directory_path}")
        # Discover images
        patterns = ["*.jpg", "*.jpeg", "*.png", "*.bmp", "*.tiff", "*.webp"]
        files: list[Path] = []
        for pat in patterns:
            if recursive:
                files.extend(directory_path.rglob(pat))
            else:
                files.extend(directory_path.glob(pat))
        if max_files:
            files = files[:max_files]
        if not files:
            logger.warning("No supported images found to process.")
        out_file = self._get_output_file(directory_path)
        processed = 0
        for idx, img in enumerate(files, start=1):
            is_valid, err = self.validate_image_for_processing(img)
            if not is_valid:
                logger.warning(f"Skipping {img.name}: {err}")
                continue
            try:
                desc = self.get_image_description(img)
                if not desc:
                    logger.warning(f"No description for {img.name}")
                    continue
                # Extract basic metadata if enabled
                meta = None
                if METADATA_SUPPORT and self.config.get('processing_options', {}).get('extract_metadata', True):
                    try:
                        meta = self.metadata_extractor.extract_metadata(img)
                    except Exception:
                        meta = None
                self._write_description_entry(out_file, img, desc, meta)
                processed += 1
                # Delay to manage memory
                time.sleep(max(0.0, float(self.batch_delay)))
                # Progress title
                try:
                    pct = int((processed / max(1, len(files))) * 100)
                    set_console_title(self._build_window_title(pct, processed, len(files)))
                except Exception:
                    pass
            except Exception as e:
                logger.error(f"Failed to process {img.name}: {e}")
        logger.info(f"Processed {processed} images. Output: {out_file}")

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
            # WARNING: optimize_image_size modifies the file in-place!
            # This is safe here because:
            # 1. When called via workflow, files are copies in workflow_output directory
            # 2. When called standalone, user is responsible for working on copies
            # See workflow.py copy_or_link_images() for how workflow protects originals
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
            
            # For Ollama provider, use direct API call with fallback to HTTP if python client missing
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
                # Optimized retry delays for server 500 errors - faster recovery
                retry_delays = [0.5, 1.0, 2.0]  # Fixed delays instead of exponential backoff
                
                last_exception = None
                for attempt in range(max_retries + 1):  # +1 for initial attempt
                    try:
                        # Call Ollama API with configured settings and timeout
                        # Prefer python client when available; fallback to HTTP API
                        use_python_client = (ollama is not None and hasattr(ollama, 'chat'))
                        if use_python_client:
                            import signal
                            
                            def timeout_handler(signum, frame):
                                raise TimeoutError(f"Ollama request timed out after {self.timeout} seconds")
                            
                            # Set up timeout for Windows/Unix compatibility
                            try:
                                # For Windows, we'll use a different approach since signal.alarm doesn't work
                                import threading
                                import time
                                
                                response = None
                                exception_caught = None
                                
                                def make_request():
                                    nonlocal response, exception_caught
                                    try:
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
                                    except Exception as e:
                                        exception_caught = e
                                
                                # Start request in background thread
                                request_thread = threading.Thread(target=make_request)
                                request_thread.daemon = True
                                request_thread.start()
                                
                                # Wait for completion or timeout
                                request_thread.join(timeout=self.timeout)
                                
                                if request_thread.is_alive():
                                    # Request is still running - timeout occurred
                                    logger.warning(f"  [TIMEOUT] Request for {image_path.name} timed out after {self.timeout} seconds")
                                    raise TimeoutError(f"Ollama request timed out after {self.timeout} seconds")
                                
                                if exception_caught:
                                    raise exception_caught
                                    
                                if response is None:
                                    raise RuntimeError("Request completed but no response received")
                                    
                            except ImportError:
                                # Fallback to direct call if threading unavailable
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
                        else:
                            # HTTP fallback to Ollama API
                            import requests
                            http_response = requests.post(
                                "http://127.0.0.1:11434/api/chat",
                                json={
                                    'model': self.model_name,
                                    'messages': [
                                        {
                                            'role': 'user',
                                            'content': prompt,
                                            'images': [image_base64]
                                        }
                                    ],
                                    'options': model_settings,
                                    'stream': False
                                },
                                timeout=self.timeout
                            )
                            http_response.raise_for_status()
                            response = http_response.json()
                        
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
                            'connection' in error_msg.lower() or
                            isinstance(e, TimeoutError)  # Handle our custom timeout
                        )
                        
                        if is_retryable and attempt < max_retries:
                            # Use fixed retry delays optimized for server errors
                            import random
                            base_delay = retry_delays[min(attempt, len(retry_delays) - 1)]
                            jitter = random.uniform(0.1, 0.3) * base_delay  # Reduced jitter
                            sleep_time = base_delay + jitter
                            
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
                
                # Normalize response for both python client and HTTP JSON
                message = response['message'] if isinstance(response, dict) else response.get('message')
                if hasattr(message, 'content'):
                    description = message.content.strip()
                elif isinstance(message, dict) and 'content' in message:
                    description = str(message['content']).strip()
                else:
                    # Fallback: try to stringify whole response
                    description = str(response).strip()
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
                # WARNING: optimize_image_size modifies the file in-place!
                # Safe when files are in workflow directories (copies), but be cautious with standalone use
                if self.provider_name in ["claude", "openai"]:
                    current_size = image_path.stat().st_size
                    max_allowed = CLAUDE_MAX_SIZE if self.provider_name == "claude" else OPENAI_MAX_SIZE
                    if current_size > TARGET_MAX_SIZE:
                        logger.warning(f"Image {image_path.name} is {current_size/1024/1024:.2f}MB (over {TARGET_MAX_SIZE/1024/1024:.1f}MB limit). Attempting emergency optimization...")
                        success, orig_size, final_size = optimize_image_size(image_path, max_file_size=TARGET_MAX_SIZE)
                        if not success:
                            logger.error(f"Emergency optimization failed! Image may be rejected by {self.provider_name} API")
                
                # Call provider's describe_image method with correct signature.
                # Providers expect: describe_image(image_path: str, prompt: str, model: str)
                # Retry on empty only when finish_reason='length' (token budget exhausted).
                # Issue #91: gpt-5-nano has ~28% empty rate due to reasoning token use.
                # We skip retrying on finish_reason='stop' — it costs money and won't help.
                # When finish_reason is unavailable (Ollama) we allow one retry.
                MAX_EMPTY_RETRIES = 2
                description = None
                import time as _time
                for attempt in range(MAX_EMPTY_RETRIES + 1):
                    description = self.provider.describe_image(
                        image_path=str(image_path),
                        prompt=prompt,
                        model=self.model_name
                    )
                    if description and description.strip():
                        break

                    # Check finish_reason to decide whether retry will help
                    finish_reason = None
                    if hasattr(self.provider, 'last_usage') and self.provider.last_usage:
                        finish_reason = self.provider.last_usage.get('finish_reason')

                    should_retry = (finish_reason == 'length' or finish_reason is None)

                    if should_retry and attempt < MAX_EMPTY_RETRIES:
                        logger.warning(
                            f"  [EMPTY-RETRY] Empty response from {self.provider_name}/{self.model_name} "
                            f"finish_reason={finish_reason!r} "
                            f"(attempt {attempt + 1}/{MAX_EMPTY_RETRIES + 1}) for {image_path.name} — retrying..."
                        )
                        _time.sleep(1.0 * (attempt + 1))
                    else:
                        if not should_retry:
                            logger.warning(
                                f"  [EMPTY-RETRY] Empty response finish_reason={finish_reason!r} — "
                                f"not retrying for {image_path.name} (not a token-budget issue)."
                            )
                        else:
                            logger.warning(
                                f"  [EMPTY-RETRY] All {MAX_EMPTY_RETRIES + 1} attempts returned empty "
                                f"for {image_path.name} — keeping empty result."
                            )
                        break

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
                    entry = "File: " + str(relative_path) + "\n"
                except ValueError:
                    # Fallback if relative path calculation fails
                    entry = "File: " + image_path.name + "\n"
            else:
                entry = "File: " + image_path.name + "\n"
            
            if output_format.get('include_file_path', True):
                entry += "Path: " + str(image_path) + "\n"
            
            # Add source file info if available (video frames, converted images)
            if metadata and 'source_file' in metadata:
                source = metadata['source_file']
                if source.get('type') == 'video':
                    source_line = "Source: " + str(source.get('path', 'Unknown'))
                    if 'timestamp' in source:
                        source_line += " at " + str(source['timestamp'])
                    entry += source_line + "\n"
            
            # Add metadata if enabled and available
            if output_format.get('include_metadata', True) and metadata:
                metadata_str = self.format_metadata(metadata)
                if metadata_str:
                    entry += metadata_str + "\n"
            
            if output_format.get('include_model_info', True):
                entry += "Provider: " + str(self.provider_name) + "\n"
                entry += "Model: " + str(self.model_name) + "\n"
                entry += "Prompt Style: " + str(self.prompt_style) + "\n"
            
            # Add location/date prefix to description if enabled and metadata available
            formatted_description = description
            metadata_config = self.config.get('metadata', {})
            if metadata_config.get('include_location_prefix', True) and metadata and self.metadata_extractor:
                # Hint the user if GPS exists but geocoding is disabled
                try:
                    loc_hint = metadata.get('location', {}) if isinstance(metadata, dict) else {}
                except Exception:
                    loc_hint = {}
                if (not self._geocode_notice_logged and self.geocoder is None and isinstance(loc_hint, dict)
                        and (('latitude' in loc_hint and 'longitude' in loc_hint) or ('lat' in loc_hint and 'lon' in loc_hint))
                        and not (loc_hint.get('city') or loc_hint.get('state') or loc_hint.get('country'))):
                    logger.info("GPS detected but reverse geocoding is disabled. Use --geocode (or enable metadata.geocoding.enabled) to include city/state names.")
                    self._geocode_notice_logged = True
                location_prefix = self.metadata_extractor.format_location_prefix(metadata)
                if location_prefix:
                    # Use string concatenation to avoid f-string format errors from curly braces in description
                    formatted_description = location_prefix + ": " + description
            
            entry += "Description: " + formatted_description + "\n"
            
            if output_format.get('include_timestamp', True):
                entry += "Timestamp: " + time.strftime('%Y-%m-%d %H:%M:%S') + "\n"

            # Append compact metadata suffix at end for downstream reuse
            try:
                meta_suffix = self._build_meta_suffix(image_path, metadata or {})
                if meta_suffix:
                    entry += meta_suffix + "\n"
            except Exception:
                pass
            
            # Add OpenStreetMap attribution if geocoding was used
            if metadata and 'location' in metadata:
                loc = metadata['location']
                # Check if geocoded data (city/state/country) is present
                if loc.get('city') or loc.get('state') or loc.get('country'):
                    entry += "\nLocation data © OpenStreetMap contributors (https://www.openstreetmap.org/copyright)\n"
            
            entry += separator_char * 80 + "\n\n"
            
            # Append to the file
            with open(output_file, 'a', encoding='utf-8') as f:
                f.write(entry)
            
            logger.info("Successfully wrote description for " + image_path.name + " to " + output_file.name)
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
                    f.write("=" * 80 + "\n")
                    # Add separator line before first description entry so it's properly delimited
                    f.write("-" * 80 + "\n\n")
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
        
        # Check for HEIC files and warn if no support
        heic_files = [f for f in image_files if f.suffix.lower() in {'.heic', '.heif'}]
        if heic_files and not HEIC_SUPPORT:
            logger.warning(f"Found {len(heic_files)} HEIC/HEIF files, but pillow-heif is not installed")
            logger.warning("HEIC files contain GPS location and camera metadata that cannot be extracted")
            logger.warning("Install pillow-heif to enable full HEIC support: pip install pillow-heif")
            logger.warning("Without HEIC support, only file modification time will be available for these files")
        
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
                set_console_title(self._build_window_title(progress_percent, current_processed, len(image_files), " - Skipped"))
                continue
            
            # Log progress and start time for this image
            newly_processed += 1
            success_count += 1
            # Show cumulative progress: where we are in total work
            logger.info(f"Describing image {success_count} of {len(image_files)}: {image_path.name}")
            
            # Update window title with progress
            current_processed = success_count + failed_count
            progress_percent = int((current_processed / len(image_files)) * 100)
            set_console_title(self._build_window_title(progress_percent, current_processed, len(image_files)))
            
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
                set_console_title(self._build_window_title(progress_percent, current_processed, len(image_files), " - Validation Failed"))
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
            
            # Capture token usage from provider if available
            token_usage = None
            if hasattr(self.provider, 'get_last_token_usage'):
                token_usage = self.provider.get_last_token_usage()
            
            # Log end time for this image
            image_end_time = time.time()
            processing_duration = image_end_time - image_start_time
            logger.info(f"End time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(image_end_time))}")
            logger.info(f"Processing duration: {processing_duration:.2f} seconds")
            
            if description and not description.startswith("Error:"):
                # Add processing time to metadata
                if metadata is None:
                    metadata = {}
                metadata['processing_time_seconds'] = round(processing_duration, 2)
                
                # Add token usage to metadata if available
                if token_usage:
                    metadata['token_usage'] = token_usage
                
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
            
            # Additional throttling for Ollama to reduce server load
            if self.provider_name == "ollama" and i < len(image_files):  # Don't delay after last image
                ollama_throttle_delay = 3.0  # 3 seconds between Ollama requests
                logger.debug(f"Ollama throttling: waiting {ollama_throttle_delay}s before next request")
                time.sleep(ollama_throttle_delay)
            
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
        Extract EXIF metadata from an image file using shared metadata module
        
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
            
            # Check if metadata extractor is available
            if not self.metadata_extractor:
                logger.debug(f"Metadata extractor not available (install metadata_extractor module)")
                return metadata
            
            # Extract metadata using shared module
            metadata = self.metadata_extractor.extract_metadata(image_path)
            
            # Enrich with geocoding if available and enabled
            if self.geocoder and 'location' in metadata:
                loc = metadata['location']
                if 'latitude' in loc and 'longitude' in loc:
                    logger.debug(f"Geocoding coordinates for {image_path.name}")
                    metadata = self.geocoder.enrich_metadata(metadata)
            
            if metadata:
                sections = len([k for k in metadata.keys() if k in ('datetime', 'location', 'camera', 'technical')])
                if sections > 0:
                    logger.debug(f"Extracted {sections} metadata sections from {image_path.name}")
            else:
                logger.debug(f"No metadata extracted from {image_path.name}")
                            
        except Exception as e:
            logger.info(f"Could not extract metadata from {image_path.name}: {e}")
        
        return metadata

    def _format_mdy_ampm(self, dt: datetime) -> str:
        """Format datetime as M/D/YYYY H:MMP (no leading zero on hour, A/P)."""
        month = dt.month
        day = dt.day
        year = dt.year
        hour24 = dt.hour
        minute = dt.minute
        suffix = 'A' if hour24 < 12 else 'P'
        hour12 = hour24 % 12
        if hour12 == 0:
            hour12 = 12
        return f"{month}/{day}/{year} {hour12}:{minute:02d}{suffix}"
    
    def _extract_datetime(self, exif_data: dict) -> Optional[str]:
        """Extract date/time from EXIF using standard format.
        Priority: DateTimeOriginal > DateTimeDigitized > DateTime.
        """
        try:
            datetime_fields = ['DateTimeOriginal', 'DateTimeDigitized', 'DateTime']
            for field in datetime_fields:
                if field in exif_data:
                    dt_str = exif_data[field]
                    if not dt_str:
                        continue
                    for fmt in ('%Y:%m:%d %H:%M:%S', '%Y-%m-%d %H:%M:%S'):
                        try:
                            dt = datetime.strptime(dt_str, fmt)
                            return self._format_mdy_ampm(dt)
                        except ValueError:
                            continue
                    logger.debug(f"Could not parse datetime format: {dt_str}")
        except Exception as e:
            logger.debug(f"Error extracting datetime: {e}")
        return None
    
    def _extract_location(self, exif_data: dict) -> Optional[Dict[str, Any]]:
        """Extract GPS/location info including optional human-readable fields."""
        try:
            gps_info = exif_data.get('GPSInfo')
            if not gps_info:
                # Fallback: collect any textual location hints from EXIF
                text_loc = {}
                for key in ('City', 'State', 'Province', 'Country', 'CountryName', 'CountryCode'):
                    if key in exif_data and exif_data[key]:
                        k = key.lower()
                        if k == 'province':
                            k = 'state'
                        text_loc[k] = exif_data[key]
                return text_loc or None
            
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
            
            # Attach any human-readable tags if present
            for key in ('City', 'State', 'Province', 'Country', 'CountryName', 'CountryCode'):
                if key in exif_data and exif_data[key]:
                    k = key.lower()
                    if k == 'province':
                        k = 'state'
                    location[k] = exif_data[key]

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
                    technical_info['aperture'] = "f/" + "{:.1f}".format(f_value)
                else:
                    technical_info['aperture'] = "f/" + str(f_number)
            
            # Shutter speed
            if 'ExposureTime' in exif_data:
                exposure_time = exif_data['ExposureTime']
                if isinstance(exposure_time, tuple) and len(exposure_time) == 2:
                    if exposure_time[0] == 1:
                        technical_info['shutter_speed'] = "1/" + str(exposure_time[1]) + "s"
                    else:
                        exp_val = exposure_time[0]/exposure_time[1]
                        technical_info['shutter_speed'] = str(exp_val) + "s"
                else:
                    technical_info['shutter_speed'] = str(exposure_time) + "s"
            
            # Focal length
            if 'FocalLength' in exif_data:
                focal_length = exif_data['FocalLength']
                if isinstance(focal_length, tuple) and len(focal_length) == 2:
                    fl_value = focal_length[0] / focal_length[1]
                    technical_info['focal_length'] = "{:.0f}".format(fl_value) + "mm"
                else:
                    technical_info['focal_length'] = str(focal_length) + "mm"
            
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
        
        # Format datetime (handle both string and datetime object)
        if 'datetime_str' in metadata:
            lines.append("Photo Date: " + str(metadata['datetime_str']))
        elif 'datetime' in metadata:
            dt_val = metadata['datetime']
            if isinstance(dt_val, str):
                lines.append("Photo Date: " + str(dt_val))
            elif isinstance(dt_val, datetime):
                # Format using shared module if available
                if self.metadata_extractor:
                    formatted = self.metadata_extractor._format_mdy_ampm(dt_val)
                    lines.append("Photo Date: " + str(formatted))
        
        # Format location with geocoded city/state if available
        if 'location' in metadata:
            location = metadata['location']
            location_parts = []
            
            # Add city, state, country if available (from geocoding)
            city = location.get('city') or location.get('town')
            state = location.get('state')
            country = location.get('country')
            
            readable_parts = []
            if city:
                readable_parts.append(city)
            if state:
                readable_parts.append(state)
            if country:
                readable_parts.append(country)
            
            if readable_parts:
                location_parts.append("Location: " + ", ".join(readable_parts))
            
            # Add GPS coordinates
            if 'latitude' in location and 'longitude' in location:
                lat_str = "{:.6f}".format(location['latitude'])
                lon_str = "{:.6f}".format(location['longitude'])
                location_parts.append("GPS: " + lat_str + ", " + lon_str)
            
            if 'altitude' in location:
                alt_str = "{:.1f}".format(location['altitude'])
                location_parts.append("Altitude: " + alt_str + "m")
            
            if location_parts:
                lines.append(", ".join(location_parts))
        
        # Format camera info
        if 'camera' in metadata:
            camera = metadata['camera']
            camera_parts = []
            
            if 'make' in camera and 'model' in camera:
                camera_parts.append(str(camera['make']) + " " + str(camera['model']))
            
            if 'lens' in camera:
                camera_parts.append("Lens: " + str(camera['lens']))
            
            if camera_parts:
                lines.append("Camera: " + ", ".join(camera_parts))
        
        # Format processing time if available
        if 'processing_time_seconds' in metadata:
            proc_time = metadata['processing_time_seconds']
            lines.append(f"Processing Time: {proc_time:.2f} seconds")
        
        # Format token usage if available
        if 'token_usage' in metadata:
            usage = metadata['token_usage']
            prompt_tokens = usage.get('prompt_tokens', 0)
            completion_tokens = usage.get('completion_tokens', 0)
            total_tokens = usage.get('total_tokens', 0)
            if total_tokens > 0:
                lines.append(f"Tokens: {total_tokens:,} total ({prompt_tokens:,} prompt + {completion_tokens:,} completion)")
        
        return "\n".join(lines)

    def _build_meta_suffix(self, image_path: Path, metadata: Dict[str, Any]) -> str:
        """Build a compact, parseable one-line metadata suffix using shared module.
        Example: [3/25/2025 7:35P, iPhone 14, 30.2672°N, 97.7431°W, 150m]
        Only include fields that are available.
        """
        if self.metadata_extractor:
            # Use shared module method
            return self.metadata_extractor.build_meta_suffix(image_path, metadata)
        
        # Fallback to empty string if extractor not available
        return ""

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


def get_default_model(config_file: str = "image_describer_config.json") -> str:
    """Get default model from image describer config using config_loader.
    
    Args:
        config_file: Path to configuration file
        
    Returns:
        Default model name, or None if not specified in config
    """
    # Try config_loader first (proper resolution with search paths)
    try:
        from config_loader import load_json_config
        cfg, path, source = load_json_config(
            'image_describer_config.json', 
            explicit=config_file if config_file != 'image_describer_config.json' else None,
            env_var_file='IDT_IMAGE_DESCRIBER_CONFIG'
        )
        if cfg:
            default_model = cfg.get('default_model')
            if default_model:
                try:
                    logger.debug(f"Resolved default model '{default_model}' from {path} (source={source})")
                except Exception:
                    pass
                return default_model
            # Try old structure as fallback
            old_model = cfg.get('model_settings', {}).get('model')
            if old_model:
                return old_model
    except Exception:
        pass
    
    # Fallback: Direct file loading (for absolute paths)
    try:
        config_path = Path(config_file)
        if not config_path.is_absolute():
            config_path = Path(__file__).parent / config_file
        
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            default_model = cfg.get('default_model')
            if default_model:
                return default_model
            # Try old structure
            old_model = cfg.get('model_settings', {}).get('model')
            if old_model:
                return old_model
    except Exception:
        pass
    
    return None
    return None


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
        print("             Models: gpt-5.2, gpt-5, gpt-4o, gpt-4o-mini, etc.")
        print("             Requires: API key via --api-key-file, config file, or OPENAI_API_KEY")
        print()
        print("claude       - Anthropic Claude models")
        print("             Models: claude-opus-4-6, claude-sonnet-4-5, claude-haiku-4-5, etc.")
        print("             Requires: API key via --api-key-file, config file, or ANTHROPIC_API_KEY")
        print()
        print("copilot      - Copilot+ PC NPU acceleration (experimental)")
        print("             Models: florence-2")
        print("             Requires: Copilot+ PC with NPU, DirectML")
        print()
        print("huggingface  - Local HuggingFace Florence-2 models")
        print("             Models: microsoft/Florence-2-base, microsoft/Florence-2-large")
        print("             Requires: No API key (runs locally)")
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
        description="""Process images with AI vision models and save descriptions to a text file

⚠️  IMPORTANT: For cloud providers (OpenAI, Claude), large images may be optimized in-place
    to meet file size limits. Always use the workflow command or work on copies of your photos!
    
    Recommended: Use 'idt workflow' instead to ensure originals are never modified.
    Direct use: Only run this on copies in a workflow output directory.""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Available prompt styles: {', '.join(available_styles)}
Default prompt style: {default_style}

Examples:
  # Ollama (default provider)
  python {Path(__file__).name} exportedphotos
  python {Path(__file__).name} exportedphotos --prompt-style artistic --model llava:7b
  python {Path(__file__).name} exportedphotos --model llava:13b --prompt-style technical
  
  # OpenAI (API key from file)
  python {Path(__file__).name} exportedphotos --provider openai --model gpt-4o-mini --api-key-file ~/openai.txt
  
  # OpenAI (API key from config)
  python {Path(__file__).name} exportedphotos --provider openai --model gpt-4-vision-preview
  
  # Claude (API key from file)
  python {Path(__file__).name} exportedphotos --provider claude --model claude-sonnet-4-5-20250929 --api-key-file ~/claude.txt
  
  # Claude (API key from config)
  python {Path(__file__).name} exportedphotos --provider claude --model claude-haiku-4-5-20251001
  
  # HuggingFace (Local Florence-2 models)
  python {Path(__file__).name} exportedphotos --provider huggingface --model microsoft/Florence-2-base
  python {Path(__file__).name} exportedphotos --provider huggingface --model microsoft/Florence-2-large --prompt-style narrative
  
  # Copilot+ PC NPU (experimental)
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
        choices=["ollama", "openai", "claude", "huggingface", "mlx"],
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
        help="Path to file containing API key for cloud providers (OpenAI, Claude). "
             "If not specified, checks config file (image_describer_config.json), "
             "environment variables (OPENAI_API_KEY/ANTHROPIC_API_KEY), or .txt files."
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
        "--config-image-describer",
        "--config-id",
        "--config",
        "-c",
        type=str,
        default="image_describer_config.json",
        dest="config",
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
        help=f"Style of prompt to use (from config file). Default: {default_style}"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=90,
        help="Timeout in seconds for Ollama API requests (default: 90). Increase for slower hardware or large models."
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
    parser.add_argument(
        "--workflow-name",
        type=str,
        help="Workflow name (displayed in window title for identification)"
    )
    parser.add_argument(
        "--source-url",
        type=str,
        help="Source URL if images were downloaded from the web (for attribution)"
    )
    
    args = parser.parse_args()
    
    # If custom config specified, reload to get available prompt styles for validation
    if args.config:
        try:
            from config_loader import load_json_config
            cfg_dict, cfg_path, cfg_source = load_json_config('image_describer_config.json', explicit=args.config)
            if cfg_dict:
                variations = cfg_dict.get('prompt_variations', {})
                config_available_styles = list(variations.keys()) if variations else get_available_prompt_styles()
                
                # Validate prompt style against config-specific styles
                if args.prompt_style:
                    lower_map = {k.lower(): k for k in config_available_styles}
                    if args.prompt_style.lower() not in lower_map:
                        logger.error(f"Invalid prompt style '{args.prompt_style}' for config {cfg_path}")
                        logger.error(f"Available styles in {cfg_path}: {', '.join(config_available_styles)}")
                        print(f"ERROR: Invalid prompt style '{args.prompt_style}'")
                        print(f"Available styles in {cfg_path}: {', '.join(config_available_styles)}")
                        sys.exit(1)
        except Exception as e:
            logger.warning(f"Could not validate prompt style with custom config: {e}")
    
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
    # Note: If still no API key, the provider will check config file (image_describer_config.json)
    # and .txt files (openai.txt / claude.txt) during initialization
    if not api_key and args.provider in ["openai", "claude"]:
        if args.provider == "openai":
            env_var = "OPENAI_API_KEY"
        elif args.provider == "claude":
            env_var = "ANTHROPIC_API_KEY"
        
        api_key = os.environ.get(env_var)
        if api_key:
            logger.info(f"Using API key from environment variable {env_var}")
        else:
            logger.info(f"No API key provided via --api-key-file or {env_var}. Will check config file and .txt files.")
    
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
        log_dir=args.log_dir,
        workflow_name=args.workflow_name,
        timeout=args.timeout,
        source_url=args.source_url
    )
    
    # Override metadata extraction if disabled via command line
    if args.no_metadata:
        describer.config['processing_options']['extract_metadata'] = False
        describer.config['output_format']['include_metadata'] = False
    
    # Check provider availability (only for Ollama to maintain backward compatibility)
    if args.provider == "ollama":
        available_models = []
        ollama_ok = False
        # Try python client first
        if ollama is not None and hasattr(ollama, 'list'):
            try:
                models = ollama.list()
                
                # Robustly handle different response structures (dict vs object)
                model_list = []
                if isinstance(models, dict):
                    model_list = models.get('models', [])
                elif hasattr(models, 'models'):
                    model_list = models.models
                
                available_models = []
                for model in model_list:
                    # Handle dict vs object model items
                    name = None
                    if isinstance(model, dict):
                        name = model.get('name') or model.get('model')
                    else:
                        name = getattr(model, 'name', None) or getattr(model, 'model', None)
                    
                    if name:
                        available_models.append(name)
                        
                ollama_ok = True
                logger.info(f"Ollama is available (python client, found {len(available_models)} models)")
            except Exception as e:
                logger.warning(f"Ollama python client check failed: {e}")
        # Fallback to HTTP API
        if not ollama_ok:
            try:
                import requests
                tags = requests.get("http://127.0.0.1:11434/api/tags", timeout=3)
                tags.raise_for_status()
                data = tags.json()
                available_models = [m.get('name') for m in data.get('models', []) if m.get('name')]
                ollama_ok = True
                logger.info("Ollama is available (HTTP)")
            except Exception as e:
                logger.error(f"Ollama is not available or not running: {e}")
                logger.error("Please make sure Ollama is installed and running")
                sys.exit(1)

        # Check if the specified model is available (best effort)
        try:
            if available_models:
                # Smart model name matching: handle :latest suffix
                model_found = describer.model_name in available_models
                if not model_found:
                    # Try with :latest suffix
                    if f"{describer.model_name}:latest" in available_models:
                        model_found = True
                    # Or check if model_name has a tag and base name matches
                    elif ':' not in describer.model_name:
                        # Check if any available model starts with this base name
                        base_matches = [m for m in available_models if m.startswith(f"{describer.model_name}:")]
                        if base_matches:
                            model_found = True
                
                if not model_found:
                    logger.error(f"Model '{describer.model_name}' is not available")
                    logger.error(f"Available models: {', '.join(available_models)}")
                    logger.info(f"You can install the model with: ollama pull {describer.model_name}")
                    sys.exit(1)
            
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
