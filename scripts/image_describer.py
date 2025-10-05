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

# Make ollama optional for backwards compatibility
try:
    import ollama
except ImportError:
    ollama = None

from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

# Import AI providers from the main application
# Add parent directory to path to import from imagedescriber module
sys.path.insert(0, str(Path(__file__).parent.parent))
from imagedescriber.ai_providers import (
    OllamaProvider,
    OpenAIProvider,
    ClaudeProvider,
    ONNXProvider,
    CopilotProvider,
    HuggingFaceProvider,
    GroundingDINOProvider,
    GroundingDINOHybridProvider
)


# Configure basic logging (will be enhanced in main() if log-dir is provided)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_logging(log_dir: Optional[str] = None, verbose: bool = False) -> None:
    """
    Set up logging configuration for the image describer
    
    Args:
        log_dir: Directory to write log files to
        verbose: Whether to enable debug logging
    """
    global logger
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Set logging level
    level = logging.DEBUG if verbose else logging.INFO
    logger.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Console handler
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
                 log_dir: str = None, detection_query: str = None, confidence: float = 25.0):
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
        self.detection_query = detection_query  # For GroundingDINO providers
        self.confidence = confidence  # For GroundingDINO providers
        
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
                provider = OpenAIProvider()
                provider.api_key = self.api_key
                return provider
                
            elif self.provider_name == "claude":
                logger.info("Initializing Claude provider...")
                if not self.api_key:
                    raise ValueError("Claude provider requires an API key. Use --api-key-file option.")
                provider = ClaudeProvider()
                provider.api_key = self.api_key
                return provider
                
            elif self.provider_name == "onnx":
                logger.info("Initializing ONNX provider...")
                provider = ONNXProvider()
                return provider
                
            elif self.provider_name == "copilot":
                logger.info("Initializing Copilot+ PC provider...")
                provider = CopilotProvider()
                return provider
                
            elif self.provider_name == "huggingface":
                logger.info("Initializing HuggingFace provider...")
                if not self.api_key:
                    raise ValueError("HuggingFace provider requires an API key. Use --api-key-file option.")
                provider = HuggingFaceProvider()
                provider.api_key = self.api_key
                return provider
                
            elif self.provider_name == "groundingdino":
                logger.info("Initializing GroundingDINO provider...")
                provider = GroundingDINOProvider()
                if not provider.is_available():
                    raise RuntimeError("GroundingDINO not available. Install with: pip install groundingdino-py torch torchvision")
                return provider
                
            elif self.provider_name == "groundingdino+ollama" or self.provider_name == "groundingdino_ollama":
                logger.info("Initializing GroundingDINO + Ollama hybrid provider...")
                provider = GroundingDINOHybridProvider()
                if not provider.is_available():
                    raise RuntimeError("GroundingDINO hybrid not available. Ensure both GroundingDINO and Ollama are installed.")
                return provider
                
            else:
                raise ValueError(f"Unknown provider: {self.provider_name}. Supported: ollama, openai, claude, onnx, copilot, huggingface, groundingdino, groundingdino+ollama")
                
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
    
    def get_image_description(self, image_path: Path) -> Optional[str]:
        """
        Get description of an image using configured AI provider
        
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
                    
                # Clean up memory
                gc.collect()
                
                return description
            
        except Exception as e:
            logger.error(f"Error generating description for {image_path}: {e}")
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
        overall_start_time = time.time()
        
        for i, image_path in enumerate(image_files, 1):
            # Check if this image was already described (resume support)
            if str(image_path) in already_described:
                skip_count += 1
                logger.info(f"Skipping already-described image {i} of {len(image_files)}: {image_path.name}")
                success_count += 1  # Count as success since it's already done
                continue
            
            # Log progress and start time for this image
            logger.info(f"Describing image {i} of {len(image_files)}: {image_path.name}")
            image_start_time = time.time()
            logger.info(f"Start time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(image_start_time))}")
            
            # Extract metadata from image
            metadata = self.extract_metadata(image_path)
            if metadata:
                logger.debug(f"Extracted metadata for {image_path.name}: {metadata}")
            else:
                logger.debug(f"No metadata extracted for {image_path.name}")
            
            # Get description from Ollama
            description = self.get_image_description(image_path)
            
            # Log end time for this image
            image_end_time = time.time()
            processing_duration = image_end_time - image_start_time
            logger.info(f"End time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(image_end_time))}")
            logger.info(f"Processing duration: {processing_duration:.2f} seconds")
            
            if description:
                # Write description to file with metadata and base directory for relative paths
                if self.write_description_to_file(image_path, description, output_file, metadata, directory_path):
                    success_count += 1
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
                    logger.error(f"Failed to write description for: {image_path.name}")
            else:
                logger.error(f"Failed to generate description for: {image_path.name}")
            
            # Memory management: add delay and force garbage collection
            if self.batch_delay > 0:
                time.sleep(self.batch_delay)
            gc.collect()
        
        # Log overall completion summary
        overall_end_time = time.time()
        total_duration = overall_end_time - overall_start_time
        newly_processed = success_count - skip_count
        logger.info(f"Processing complete. Successfully processed {success_count}/{len(image_files)} images")
        if skip_count > 0:
            logger.info(f"Skipped {skip_count} already-described images, processed {newly_processed} new images")
        logger.info(f"Provider: {self.provider_name}, Model: {self.model_name}, Prompt Style: {self.prompt_style}")
        logger.info(f"Total processing time: {total_duration:.2f} seconds")
        if newly_processed > 0:
            logger.info(f"Average time per new image: {total_duration/newly_processed:.2f} seconds")
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
                return metadata
            
            with Image.open(image_path) as img:
                # Use getexif() instead of _getexif() (modern method)
                exif_data = img.getexif()
                
                if exif_data:
                    # Convert EXIF data to human-readable format
                    exif_dict = {}
                    for tag_id, value in exif_data.items():
                        tag = TAGS.get(tag_id, tag_id)
                        exif_dict[tag] = value
                    
                    # Extract all available metadata
                    datetime_info = self._extract_datetime(exif_dict)
                    if datetime_info:
                        metadata['datetime'] = datetime_info
                    
                    location_info = self._extract_location(exif_dict)
                    if location_info:
                        metadata['location'] = location_info
                    
                    camera_info = self._extract_camera_info(exif_dict)
                    if camera_info:
                        metadata['camera'] = camera_info
                    
                    technical_info = self._extract_technical_info(exif_dict)
                    if technical_info:
                        metadata['technical'] = technical_info
                            
        except Exception as e:
            logger.debug(f"Error extracting metadata from {image_path}: {e}")
        
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
    """
    Get the default prompt style from configuration file
    
    Args:
        config_file: Path to configuration file
        
    Returns:
        Default prompt style name
    """
    try:
        config_path = Path(config_file)
        if not config_path.is_absolute():
            script_dir = Path(__file__).parent
            config_path = script_dir / config_file
        
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            default_style = config.get('default_prompt_style', 'detailed')
            # Validate that the default style exists in prompt_variations (case-insensitive)
            prompt_variations = config.get('prompt_variations', {})
            lower_variations = {k.lower(): k for k, v in prompt_variations.items()}
            
            if default_style.lower() in lower_variations:
                return lower_variations[default_style.lower()]
            else:
                logger.warning(f"Default prompt style '{default_style}' not found in prompt_variations. Using 'detailed'.")
                # Try to find 'detailed' case-insensitively
                if 'detailed' in lower_variations:
                    return lower_variations['detailed']
                # Return first available style if any exist
                elif prompt_variations:
                    return list(prompt_variations.keys())[0]
                else:
                    return 'detailed'
    except:
        pass
    
    return "detailed"


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
    
    # Get available prompt styles and default from config
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
        choices=["ollama", "openai", "claude", "onnx", "copilot", "huggingface", "groundingdino", "groundingdino+ollama"],
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
        help="Path to file containing API key for cloud providers (OpenAI, HuggingFace)"
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
        "--detection-query",
        type=str,
        help="Detection query for GroundingDINO (separate items with ' . ')"
    )
    parser.add_argument(
        "--confidence",
        type=float,
        default=25.0,
        help="Confidence threshold for GroundingDINO detection (1-95, default: 25)"
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
    
    args = parser.parse_args()
    
    # Set up logging with log directory and verbosity
    setup_logging(log_dir=args.log_dir, verbose=args.verbose)
    
    # Convert directory path to Path object
    directory_path = Path(args.directory)
    
    # Load API key if provided
    api_key = None
    if args.api_key_file:
        try:
            api_key_path = Path(args.api_key_file).expanduser()
            with open(api_key_path, 'r', encoding='utf-8') as f:
                api_key = f.read().strip()
            logger.info(f"Loaded API key from {api_key_path}")
        except Exception as e:
            logger.error(f"Failed to load API key from {args.api_key_file}: {e}")
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
        log_dir=args.log_dir,
        detection_query=args.detection_query,
        confidence=args.confidence
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
