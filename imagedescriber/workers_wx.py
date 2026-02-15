#!/usr/bin/env python3
"""
workers_wx.py - Worker threads for ImageDescriber (wxPython)

Thread-safe worker classes for AI processing, batch operations, and workflow management.
Uses wx.lib.newevent for thread-to-GUI communication.
"""

import sys
import threading
import time
import json
import tempfile
import logging
import traceback
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

# Logger instance - configuration is done in imagedescriber_wx.py main()
# Use --debug flag to enable verbose file logging
logger = logging.getLogger(__name__)

import wx
import wx.lib.newevent

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

# Import config_loader for frozen mode compatibility
try:
    from config_loader import load_json_config
except ImportError:
    load_json_config = None

# Import web image downloader for URL downloads
try:
    from web_image_downloader import WebImageDownloader
except ImportError:
    try:
        from scripts.web_image_downloader import WebImageDownloader
    except ImportError:
        WebImageDownloader = None

# Import AI providers
try:
    from .ai_providers import get_available_providers
except ImportError:
    try:
        from ai_providers import get_available_providers
    except ImportError:
        get_available_providers = None

# Import metadata extractor and geocoder
MetadataExtractor = None
NominatimGeocoder = None
try:
    from metadata_extractor import MetadataExtractor, NominatimGeocoder
except ImportError:
    try:
        from scripts.metadata_extractor import MetadataExtractor, NominatimGeocoder
    except ImportError:
        pass

# Create custom event types for thread communication
ProgressUpdateEvent, EVT_PROGRESS_UPDATE = wx.lib.newevent.NewEvent()
ProcessingCompleteEvent, EVT_PROCESSING_COMPLETE = wx.lib.newevent.NewEvent()
ProcessingFailedEvent, EVT_PROCESSING_FAILED = wx.lib.newevent.NewEvent()
WorkflowCompleteEvent, EVT_WORKFLOW_COMPLETE = wx.lib.newevent.NewEvent()
WorkflowFailedEvent, EVT_WORKFLOW_FAILED = wx.lib.newevent.NewEvent()
ConversionCompleteEvent, EVT_CONVERSION_COMPLETE = wx.lib.newevent.NewEvent()
ConversionFailedEvent, EVT_CONVERSION_FAILED = wx.lib.newevent.NewEvent()

# Chat-specific event types
ChatUpdateEvent, EVT_CHAT_UPDATE = wx.lib.newevent.NewEvent()
ChatCompleteEvent, EVT_CHAT_COMPLETE = wx.lib.newevent.NewEvent()
ChatErrorEvent, EVT_CHAT_ERROR = wx.lib.newevent.NewEvent()

# Directory scanning event types (for async file loading)
FilesDiscoveredEvent, EVT_FILES_DISCOVERED = wx.lib.newevent.NewEvent()
ScanProgressEvent, EVT_SCAN_PROGRESS = wx.lib.newevent.NewEvent()
ScanCompleteEvent, EVT_SCAN_COMPLETE = wx.lib.newevent.NewEvent()
ScanFailedEvent, EVT_SCAN_FAILED = wx.lib.newevent.NewEvent()

# Workspace save event types
WorkspaceSaveCompleteEvent, EVT_WORKSPACE_SAVE_COMPLETE = wx.lib.newevent.NewEvent()
WorkspaceSaveFailedEvent, EVT_WORKSPACE_SAVE_FAILED = wx.lib.newevent.NewEvent()


# Custom event classes that properly store attributes
class ProcessingCompleteEventData(ProcessingCompleteEvent):
    """Event data for processing completion"""
    def __init__(self, file_path, description, provider, model, prompt_style, custom_prompt, metadata=None):
        ProcessingCompleteEvent.__init__(self)
        self.file_path = file_path
        self.description = description
        self.provider = provider
        self.model = model
        self.prompt_style = prompt_style
        self.custom_prompt = custom_prompt
        self.metadata = metadata or {}


class ProcessingFailedEventData(ProcessingFailedEvent):
    """Event data for processing failure"""
    def __init__(self, file_path, error):
        ProcessingFailedEvent.__init__(self)
        self.file_path = file_path
        self.error = error


class ProgressUpdateEventData(ProgressUpdateEvent):
    """Event data for progress updates"""
    def __init__(self, file_path, message, current=0, total=0):
        ProgressUpdateEvent.__init__(self)
        self.file_path = file_path
        self.message = message
        self.current = current
        self.total = total


class WorkflowCompleteEventData(WorkflowCompleteEvent):
    """Event data for workflow completion"""
    def __init__(self, input_dir, output_dir):
        WorkflowCompleteEvent.__init__(self)
        self.input_dir = input_dir
        self.output_dir = output_dir


class WorkflowFailedEventData(WorkflowFailedEvent):
    """Event data for workflow failure"""
    def __init__(self, error):
        WorkflowFailedEvent.__init__(self)
        self.error = error


class FilesDiscoveredEventData(FilesDiscoveredEvent):
    """Event data for file discovery during directory scan"""
    def __init__(self, files, batch_number, total_batches):
        FilesDiscoveredEvent.__init__(self)
        self.files = files  # List of Path objects
        self.batch_number = batch_number  # Current batch number
        self.total_batches = total_batches  # Total batches (may be estimate)


class ScanProgressEventData(ScanProgressEvent):
    """Event data for scan progress updates"""
    def __init__(self, message, files_found):
        ScanProgressEvent.__init__(self)
        self.message = message
        self.files_found = files_found


class ScanCompleteEventData(ScanCompleteEvent):
    """Event data for scan completion"""
    def __init__(self, total_files, elapsed_time):
        ScanCompleteEvent.__init__(self)
        self.total_files = total_files
        self.elapsed_time = elapsed_time


class ScanFailedEventData(ScanFailedEvent):
    """Event data for scan failure"""
    def __init__(self, error):
        ScanFailedEvent.__init__(self)
        self.error = error


class ProcessingWorker(threading.Thread):
    """Worker thread for AI processing of a single image
    
    Processes one image with the specified AI provider and model,
    emitting progress updates and results via wxPython events.
    
    Events:
        ProgressUpdateEvent: Progress messages during processing
        ProcessingCompleteEvent: Success with description
        ProcessingFailedEvent: Error during processing
    """
    
    def __init__(self, parent_window, file_path: str, provider: str, model: str, 
                 prompt_style: str, custom_prompt: str = "", 
                 detection_settings: dict = None, 
                 prompt_config_path: Optional[str] = None,
                 api_key: Optional[str] = None):
        """Initialize worker
        
        Args:
            parent_window: wxWindow to receive events
            file_path: Path to image file
            provider: AI provider name (ollama, openai, claude, etc.)
            model: Model name (gpt-4o, claude-sonnet-4, etc.)
            prompt_style: Prompt style name (narrative, detailed, etc.)
            custom_prompt: Custom prompt text (overrides prompt_style)
            detection_settings: Optional settings for object detection models
            prompt_config_path: Optional path to prompt config file
            api_key: Optional API key for cloud providers
        """
        super().__init__(daemon=True)
        self.parent_window = parent_window
        self.file_path = file_path
        self.provider = provider
        self.model = model
        self.prompt_style = prompt_style
        self.custom_prompt = custom_prompt
        self.detection_settings = detection_settings or {}
        self.api_key = api_key
        
        try:
            self._prompt_config_path = Path(prompt_config_path) if prompt_config_path else None
        except Exception:
            self._prompt_config_path = None
    
    def run(self):
        """Execute processing in background thread"""
        try:
            # Load prompt configuration
            config = self._load_prompt_config()
            
            # Get the actual prompt text
            if self.custom_prompt:
                prompt_text = self.custom_prompt
            else:
                # Check for both prompt_variations and prompts
                prompt_data = config.get("prompt_variations", config.get("prompts", {}))
                if self.prompt_style in prompt_data:
                    if isinstance(prompt_data[self.prompt_style], dict):
                        prompt_text = prompt_data[self.prompt_style].get("text", "Describe this image.")
                    else:
                        prompt_text = prompt_data[self.prompt_style]
                else:
                    prompt_text = "Describe this image."
            
            # Emit progress
            self._post_progress(f"Processing with {self.provider} {self.model}...")
            
            # Extract metadata from image
            metadata = self._extract_metadata(self.file_path)
            
            # Track processing time
            import time
            start_time = time.time()
            
            # Process the image with selected provider (passing API key)
            # Returns tuple: (description, provider_instance)
            description, provider_obj = self._process_with_ai(self.file_path, prompt_text, api_key=self.api_key)
            
            # Calculate processing duration
            processing_duration = time.time() - start_time
            metadata['processing_time_seconds'] = round(processing_duration, 2)
            
            # Extract diagnostic info from provider (for debugging empty responses - Issue #91)
            if hasattr(provider_obj, 'last_usage') and provider_obj.last_usage:
                usage = provider_obj.last_usage
                if 'finish_reason' in usage:
                    metadata['finish_reason'] = usage['finish_reason']
                if 'completion_tokens' in usage:
                    metadata['completion_tokens'] = usage['completion_tokens']
                if 'response_id' in usage:
                    metadata['response_id'] = usage['response_id']
            
            # Add location byline if geocoding data is available
            description = self._add_location_byline(description, metadata)
            
            # Add token usage info if available (for paid APIs), including processing time
            description = self._add_token_usage_info(description, provider_obj, processing_duration)
            
            # Emit success
            evt = ProcessingCompleteEventData(
                file_path=self.file_path,
                description=description,
                provider=self.provider,
                model=self.model,
                prompt_style=self.prompt_style,
                custom_prompt=self.custom_prompt,
                metadata=metadata
            )
            wx.PostEvent(self.parent_window, evt)
            
        except Exception as e:
            # Emit failure
            evt = ProcessingFailedEventData(file_path=self.file_path, error=str(e))
            wx.PostEvent(self.parent_window, evt)
    
    def _post_progress(self, message: str):
        """Post progress update to parent window"""
        evt = ProgressUpdateEventData(file_path=self.file_path, message=message)
        wx.PostEvent(self.parent_window, evt)
    
    def _load_prompt_config(self) -> dict:
        """Load prompt configuration
        
        Resolution order:
        1) Explicit path provided via prompt_config_path
        2) External scripts/image_describer_config.json (frozen)
        3) Bundled scripts/image_describer_config.json (frozen)
        4) Repository scripts/image_describer_config.json (dev)
        """
        try:
            # Use explicit override if available
            if self._prompt_config_path and self._prompt_config_path.exists():
                with open(self._prompt_config_path, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                    return self._normalize_prompt_config(cfg)

            # Try to find the config file
            config = None
            
            if load_json_config:
                # Use shared config_loader for frozen mode compatibility
                try:
                    config, _, _ = load_json_config('image_describer_config.json')
                except Exception:
                    config = None
            else:
                # Fallback: try to load directly from disk
                try:
                    config_path = None
                    
                    if getattr(sys, 'frozen', False):
                        # Running as executable - check external first
                        exe_dir = Path(sys.executable).parent
                        external_path = exe_dir.parent / "scripts" / "image_describer_config.json"
                        if external_path.exists():
                            config_path = external_path
                        else:
                            # Fall back to bundled config
                            config_path = Path(sys._MEIPASS) / "scripts" / "image_describer_config.json"
                    else:
                        # Running from source
                        config_path = Path(__file__).parent.parent / "scripts" / "image_describer_config.json"
                    
                    if config_path and config_path.exists():
                        with open(config_path, 'r', encoding='utf-8') as f:
                            config = json.load(f)
                except Exception:
                    config = None
            
            if config:
                return self._normalize_prompt_config(config)
        except Exception:
            pass
        
        # Return default config
        return {
            "prompts": {
                "detailed": {"text": "Provide a detailed description of this image."},
                "brief": {"text": "Briefly describe this image."},
                "creative": {"text": "Describe this image in a creative, engaging way."}
            }
        }
    
    def _normalize_prompt_config(self, config: dict) -> dict:
        """Normalize config to expose 'prompts' mapping"""
        try:
            if "prompt_variations" in config:
                prompts = {}
                for key, value in config["prompt_variations"].items():
                    if isinstance(value, dict):
                        prompts[key] = {"text": value.get("text", "Describe this image.")}
                    else:
                        prompts[key] = {"text": value}
                config = {**config, "prompts": prompts}
        except Exception:
            pass
        return config
    
    # Class-level provider cache for single-image mode (reduces initialization overhead)
    _provider_cache = {}
    _cache_lock = None  # Will be initialized on first use
    
    def _process_with_ai(self, image_path: str, prompt: str, api_key: Optional[str] = None) -> tuple:
        """Process image with selected AI provider
        
        Args:
            image_path: Path to image file
            prompt: Prompt text
            api_key: Optional API key for cloud providers (overrides provider's default)
            
        Returns:
            Tuple of (description_text, provider_instance) for token usage tracking
        """
        if not get_available_providers:
            raise Exception("AI providers module not available")
        
        # Use cached provider if available (reduces connection overhead for single-image mode)
        cache_key = f"{self.provider}_{self.model}_{api_key or ''}"
        if cache_key in ProcessingWorker._provider_cache:
            provider = ProcessingWorker._provider_cache[cache_key]
        else:
            # Get fresh provider instance
            providers = get_available_providers()
            
            if self.provider not in providers:
                raise Exception(f"Provider '{self.provider}' not available")
            
            provider = providers[self.provider]
            
            # Cache for future use (improves single-image performance)
            ProcessingWorker._provider_cache[cache_key] = provider
        
        # Inject API key if provided and provider supports it
        if api_key and hasattr(provider, 'api_key'):
            provider.api_key = api_key
            # Reinitialize client if provider has that capability
            if hasattr(provider, 'reload_api_key'):
                provider.reload_api_key()
        
        try:
            # Check if it's a HEIC file and convert if needed
            path_obj = Path(image_path)
            if path_obj.suffix.lower() in ['.heic', '.heif']:
                converted_path = self._convert_heic_to_jpeg(image_path)
                if converted_path:
                    image_path = converted_path
                else:
                    raise Exception("Failed to convert HEIC file")
            
            # Read and encode image with size limits
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # Check file size and resize if too large
            # Claude has 5MB limit, target 3.75MB to account for base64 encoding overhead
            max_size = 3.75 * 1024 * 1024  # 3.75MB
            temp_image_path = None
            
            if len(image_data) > max_size:
                # Resize and save to temporary file
                image_data = self._resize_image_data(image_data, max_size)
                
                # Create temp file with optimized image
                temp_dir = Path(tempfile.gettempdir())
                temp_image_path = temp_dir / f"temp_optimized_{int(time.time())}_{Path(image_path).stem}.jpg"
                with open(temp_image_path, 'wb') as f:
                    f.write(image_data)
                
                # Use temp file path for processing
                processing_path = str(temp_image_path)
            else:
                # Use original file path
                processing_path = image_path
            
            try:
                # Process with the selected provider
                if self.provider == "object_detection" and self.detection_settings:
                    description = provider.describe_image(processing_path, prompt, self.model, 
                                                         yolo_settings=self.detection_settings)
                elif self.provider in ["grounding_dino", "grounding_dino_hybrid"] and self.detection_settings:
                    description = provider.describe_image(processing_path, prompt, self.model, 
                                                         **self.detection_settings)
                else:
                    description = provider.describe_image(processing_path, prompt, self.model)
                
                # Return both description and provider instance for token usage tracking
                return (description, provider)
            finally:
                # Clean up temp file if created
                if temp_image_path and temp_image_path.exists():
                    try:
                        temp_image_path.unlink()
                    except Exception as e:
                        logging.warning(f"Could not delete temp file {temp_image_path}: {e}")
                
        except Exception as e:
            raise Exception(f"AI processing failed: {str(e)}")
    
    def _convert_heic_to_jpeg(self, heic_path: str) -> Optional[str]:
        """Convert HEIC file to JPEG"""
        try:
            from PIL import Image
            import pillow_heif
            
            # Register HEIF opener
            pillow_heif.register_heif_opener()
            
            # Open and convert
            image = Image.open(heic_path)
            if image.mode in ('RGBA', 'LA', 'P'):
                image = image.convert('RGB')
            
            # Create temporary JPEG file
            temp_dir = Path(tempfile.gettempdir())
            temp_path = temp_dir / f"temp_{int(time.time())}_{Path(heic_path).stem}.jpg"
            
            # Resize if too large
            max_dimension = 2048
            if max(image.size) > max_dimension:
                image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
            
            image.save(temp_path, 'JPEG', quality=85, optimize=True)
            return str(temp_path)
            
        except Exception as e:
            print(f"HEIC conversion error: {e}")
            return None
    
    def _resize_image_data(self, image_data: bytes, max_size: int) -> bytes:
        """Resize image data if it's too large"""
        try:
            from PIL import Image
            import io
            
            # Load image
            image = Image.open(io.BytesIO(image_data))
            
            # Calculate new size - iteratively reduce quality
            quality = 85
            while True:
                # Save with current quality
                output = io.BytesIO()
                if image.mode in ('RGBA', 'LA', 'P'):
                    image = image.convert('RGB')
                
                image.save(output, format='JPEG', quality=quality, optimize=True)
                output_data = output.getvalue()
                
                if len(output_data) <= max_size or quality <= 20:
                    return output_data
                
                quality -= 10
            
        except Exception as e:
            logging.error(f"Image resize error: {e}")
            return image_data  # Return original if resize fails
    
    def _extract_metadata(self, image_path: str) -> dict:
        """Extract EXIF metadata from image file
        
        Returns dictionary with metadata sections (datetime, location, camera, technical)
        """
        metadata = {}
        logging.info(f"Extracting metadata from: {image_path}")
        
        try:
            if not MetadataExtractor:
                logging.warning("MetadataExtractor not available")
                return metadata
            
            extractor = MetadataExtractor()
            metadata = extractor.extract_metadata(Path(image_path))
            
            # Add geocoding if GPS coordinates are present
            if NominatimGeocoder and 'location' in metadata:
                loc = metadata['location']
                logging.info(f"Found location in metadata: {loc}")
                # Try geocoding if we have GPS coords (geocoder handles caching internally)
                if 'latitude' in loc and 'longitude' in loc:
                    logging.info(f"GPS coords found: lat={loc['latitude']}, lon={loc['longitude']}")
                    try:
                        geocoder = self._get_geocoder()
                        logging.info(f"Got geocoder instance: {geocoder}")
                        if geocoder:
                            # Let the geocoder enrich the metadata (it will merge results)
                            logging.info(f"Calling geocoder.enrich_metadata()...")
                            metadata = geocoder.enrich_metadata(metadata)
                            logging.info(f"After geocoding, location = {metadata.get('location', {})}")
                    except Exception as e:
                        # Geocoding failed - continue without it
                        logging.error(f"Geocoding failed for {image_path}: {e}")
                        import traceback
                        logging.error(traceback.format_exc())
                else:
                    logging.info(f"No lat/lon in location data")
            elif not NominatimGeocoder:
                logging.warning(f"NominatimGeocoder not available")
            elif 'location' not in metadata:
                logging.info(f"No location key in metadata")
            
            # Ensure all metadata is JSON-serializable
            metadata = self._sanitize_for_json(metadata)
            
        except Exception as e:
            # Metadata extraction failed - return empty
            logging.error(f"Metadata extraction failed: {e}")
            import traceback
            logging.error(traceback.format_exc())
        
        # Add OSM attribution flag if geocoded data is present
        if metadata and 'location' in metadata:
            loc = metadata['location']
            # Check if geocoded data (city/state/country) is present
            if loc.get('city') or loc.get('state') or loc.get('country'):
                metadata['osm_attribution_required'] = True
                logging.info("OSM attribution required for geocoded location data")
        
        return metadata
    
    def _add_location_byline(self, description: str, metadata: dict) -> str:
        """Add location byline to description like a newspaper article
        
        Format: "City, State - [description]"
        
        Args:
            description: Original AI-generated description
            metadata: Metadata dict with location information
            
        Returns:
            Description with location byline prepended (if location available)
        """
        if not description or not metadata:
            return description
        
        location = metadata.get('location', {})
        if not location:
            return description
        
        # Build location string (matching format from format_image_metadata)
        city = location.get('city') or location.get('town')
        state = location.get('state')
        country = location.get('country')
        
        byline = None
        if city and state:
            byline = f"{city}, {state}"
        elif city and country:
            byline = f"{city}, {country}"
        elif state:
            byline = state
        elif country:
            byline = country
        
        if byline:
            logging.info(f"Adding location byline: {byline}")
            return f"{byline} - {description}"
        
        return description
    
    def _add_token_usage_info(self, description: str, provider, processing_duration: float = None) -> str:
        """Add token usage information and processing time to description
        
        Args:
            description: AI-generated description
            provider: AI provider instance
            processing_duration: Time taken in seconds (optional)
            
        Returns:
            Description with token usage and timing appended (if available)
        """
        if not description or not provider:
            return description
        
        info_parts = []
        
        # Check if provider has token usage info
        if hasattr(provider, 'last_usage') and provider.last_usage:
            usage = provider.last_usage
            prompt_tokens = usage.get('prompt_tokens', 0)
            completion_tokens = usage.get('completion_tokens', 0)
            total_tokens = usage.get('total_tokens', 0)
            
            if total_tokens > 0:
                token_info = f"Token Usage: {total_tokens:,} total ({prompt_tokens:,} prompt + {completion_tokens:,} completion)"
                info_parts.append(token_info)
                logging.info(f"Adding token usage info: {total_tokens} tokens")
        
        # Add processing time if available
        if processing_duration is not None:
            time_info = f"Time: {processing_duration:.2f}s"
            info_parts.append(time_info)
            logging.info(f"Adding processing time: {processing_duration:.2f}s")
        
        # Append combined info to description
        if info_parts:
            usage_text = "\n\n[" + " | ".join(info_parts) + "]"
            return description + usage_text
        
        return description
    
    def _sanitize_for_json(self, obj):
        """Recursively sanitize object to be JSON-serializable"""
        from datetime import datetime
        from pathlib import Path
        
        if isinstance(obj, dict):
            return {k: self._sanitize_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._sanitize_for_json(item) for item in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, Path):
            return str(obj)
        elif isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        else:
            # Convert unknown types to string
            return str(obj)
    
    def _get_geocoder(self):
        """Get or create a shared geocoder instance with caching"""
        # Use class-level cache for geocoder to share cache across images
        if not hasattr(ProcessingWorker, '_geocoder_instance'):
            if NominatimGeocoder:
                try:
                    # Check if requests module is available
                    try:
                        import requests
                        logging.info(f"requests module available: {requests.__version__}")
                    except ImportError as req_err:
                        logging.error(f"requests module NOT available: {req_err}")
                    
                    # Use a cache file in the user's temp directory or current directory
                    cache_path = Path('geocode_cache.json')
                    user_agent = 'IDT/4.0 (+https://github.com/kellylford/Image-Description-Toolkit)'
                    logging.info(f"Initializing geocoder with cache: {cache_path}")
                    ProcessingWorker._geocoder_instance = NominatimGeocoder(
                        user_agent=user_agent,
                        delay_seconds=1.0,
                        cache_path=cache_path
                    )
                    logging.info("Geocoder initialized successfully")
                except Exception as e:
                    logging.error(f"Failed to initialize geocoder: {e}")
                    import traceback
                    logging.error(traceback.format_exc())
                    ProcessingWorker._geocoder_instance = None
            else:
                logging.warning("NominatimGeocoder not available")
                ProcessingWorker._geocoder_instance = None
        
        return ProcessingWorker._geocoder_instance


class WorkflowProcessWorker(threading.Thread):
    """Worker thread for running the proven workflow system
    
    Executes external workflow command and monitors progress via subprocess.
    
    Events:
        ProgressUpdateEvent: Progress messages during workflow execution
        WorkflowCompleteEvent: Success with input/output directories
        WorkflowFailedEvent: Error during workflow execution
    """
    
    def __init__(self, parent_window, cmd, input_dir, output_dir):
        """Initialize workflow worker
        
        Args:
            parent_window: wxWindow to receive events
            cmd: Command list to execute (for subprocess.Popen)
            input_dir: Input directory path
            output_dir: Output directory path
        """
        super().__init__(daemon=True)
        self.parent_window = parent_window
        self.cmd = cmd
        self.input_dir = str(input_dir)
        self.output_dir = str(output_dir)
    
    def run(self):
        """Execute workflow command and monitor progress"""
        try:
            import subprocess
            
            # Start the workflow process
            self._post_progress("Starting workflow process...")
            
            process = subprocess.Popen(
                self.cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                universal_newlines=True
            )
            
            # Monitor output for progress
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    line = output.strip()
                    if line:
                        # Emit progress updates
                        self._post_progress(f"Workflow: {line}")
            
            # Check if process completed successfully
            return_code = process.poll()
            if return_code == 0:
                evt = WorkflowCompleteEventData(
                    input_dir=self.input_dir,
                    output_dir=self.output_dir
                )
                wx.PostEvent(self.parent_window, evt)
            else:
                evt = WorkflowFailedEventData(
                    error=f"Workflow process failed with code {return_code}"
                )
                wx.PostEvent(self.parent_window, evt)
                
        except Exception as e:
            evt = WorkflowFailedEventData(error=f"Error running workflow: {str(e)}")
            wx.PostEvent(self.parent_window, evt)
    
    def _post_progress(self, message: str):
        """Post progress update to parent window"""
        evt = ProgressUpdateEventData(file_path="", message=message)
        wx.PostEvent(self.parent_window, evt)


class ChatProcessingWorker(threading.Thread):
    """Worker thread for processing chat messages with AI providers
    
    Handles multi-turn conversations with context memory by maintaining
    a message history array and sending it to the AI provider.
    
    Events:
        ChatUpdateEvent: Incremental message chunks during streaming
        ChatCompleteEvent: Complete response with metadata
        ChatErrorEvent: Error during processing
    """
    
    def __init__(self, parent_window, image_path: Optional[str], provider: str, model: str, 
                 messages: list, api_key: str = None):
        """Initialize chat worker
        
        Args:
            parent_window: wxWindow to receive events
            image_path: Optional path to image file for context (None for text-only chat)
            provider: AI provider name (ollama, openai, claude)
            model: Model name
            messages: Full conversation history as list of message dicts
                     Format: [{'role': 'user', 'content': '...'}, ...]
            api_key: Optional API key for providers that require it
        """
        super().__init__(daemon=True)
        self.parent_window = parent_window
        self.image_path = image_path
        self.provider = provider.lower()
        self.model = model
        self.messages = messages
        self.api_key = api_key
        self._full_response = ""
    
    def run(self):
        """Execute chat processing in background thread"""
        try:
            # Route to provider-specific method
            if self.provider == 'ollama':
                self._chat_with_ollama()
            elif self.provider == 'openai':
                self._chat_with_openai()
            elif self.provider == 'claude':
                self._chat_with_claude()
            else:
                raise Exception(f"Unsupported chat provider: {self.provider}")
                
        except Exception as e:
            evt = ChatErrorEvent(error=str(e))
            wx.PostEvent(self.parent_window, evt)
    
    def _chat_with_ollama(self):
        """Handle Ollama chat with conversation history"""
        try:
            import ollama
            
            # Format messages for Ollama
            # If image_path provided: First message includes image, subsequent messages are text only
            # If no image_path: All messages are text only
            ollama_messages = []
            
            for i, msg in enumerate(self.messages):
                if i == 0 and msg['role'] == 'user' and self.image_path:
                    # First user message with image - include image
                    ollama_messages.append({
                        'role': 'user',
                        'content': msg['content'],
                        'images': [self.image_path]
                    })
                else:
                    # Subsequent messages or text-only mode - text only
                    ollama_messages.append({
                        'role': msg['role'],
                        'content': msg['content']
                    })
            
            # Stream response from Ollama
            response_stream = ollama.chat(
                model=self.model,
                messages=ollama_messages,
                stream=True
            )
            
            # Process streaming response
            for chunk in response_stream:
                if 'message' in chunk and 'content' in chunk['message']:
                    content = chunk['message']['content']
                    self._full_response += content
                    
                    # Emit update event for each chunk
                    evt = ChatUpdateEvent(message_chunk=content)
                    wx.PostEvent(self.parent_window, evt)
            
            # Emit completion event
            metadata = {
                'provider': 'ollama',
                'model': self.model,
                'tokens': {}  # Ollama doesn't provide token counts in streaming
            }
            evt = ChatCompleteEvent(full_response=self._full_response, metadata=metadata)
            wx.PostEvent(self.parent_window, evt)
            
        except Exception as e:
            raise Exception(f"Ollama chat error: {str(e)}")
    
    def _chat_with_openai(self):
        """Handle OpenAI chat.completions API with conversation history"""
        try:
            import openai
            import base64
            
            # Initialize OpenAI client
            api_key_to_use = self.api_key

            # Fallback to shared provider if no key provided
            if not api_key_to_use:
                try:
                    from .ai_providers import get_available_providers
                    providers = get_available_providers()
                    if 'openai' in providers:
                        api_key_to_use = providers['openai'].api_key
                except ImportError:
                    pass

            if api_key_to_use:
                client = openai.OpenAI(api_key=api_key_to_use)
            else:
                client = openai.OpenAI()  # Uses OPENAI_API_KEY env var
            
            # Format messages for OpenAI
            openai_messages = []
            
            for i, msg in enumerate(self.messages):
                if i == 0 and msg['role'] == 'user' and self.image_path:
                    # First user message with image - include image as base64
                    with open(self.image_path, 'rb') as f:
                        image_data = base64.b64encode(f.read()).decode('utf-8')
                    
                    openai_messages.append({
                        'role': 'user',
                        'content': [
                            {'type': 'text', 'text': msg['content']},
                            {
                                'type': 'image_url',
                                'image_url': {
                                    'url': f'data:image/jpeg;base64,{image_data}'
                                }
                            }
                        ]
                    })
                else:
                    # Subsequent messages or text-only mode - text only
                    openai_messages.append({
                        'role': msg['role'],
                        'content': msg['content']
                    })
            
            # Stream response from OpenAI
            response_stream = client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                stream=True
            )
            
            # Process streaming response
            for chunk in response_stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    self._full_response += content
                    
                    # Emit update event for each chunk
                    evt = ChatUpdateEvent(message_chunk=content)
                    wx.PostEvent(self.parent_window, evt)
            
            # Emit completion event
            metadata = {
                'provider': 'openai',
                'model': self.model,
                'tokens': {
                    # Note: Streaming doesn't provide token counts
                    # Would need separate API call to get usage
                }
            }
            evt = ChatCompleteEvent(full_response=self._full_response, metadata=metadata)
            wx.PostEvent(self.parent_window, evt)
            
        except Exception as e:
            raise Exception(f"OpenAI chat error: {str(e)}")
    
    def _chat_with_claude(self):
        """Handle Anthropic messages API with conversation history"""
        try:
            import anthropic
            import base64
            import os
            
            # Initialize Anthropic client
            api_key_to_use = self.api_key

            # Fallback checks if no key provided explicitly
            if not api_key_to_use and not os.getenv('ANTHROPIC_API_KEY'):
                # 1. Try shared provider instance (which might have loaded it from config/file)
                try:
                    # Robust import to handle frozen/dev differences
                    get_providers_func = None
                    try:
                        from .ai_providers import get_available_providers
                        get_providers_func = get_available_providers
                    except ImportError:
                        try:
                            from ai_providers import get_available_providers
                            get_providers_func = get_available_providers
                        except ImportError:
                            pass
                    
                    if get_providers_func:
                        providers = get_providers_func()
                        if 'claude' in providers and providers['claude'].api_key:
                            api_key_to_use = providers['claude'].api_key
                except Exception:
                    pass

                # 2. Try legacy file check (last resort)
                if not api_key_to_use:
                    try:
                        search_paths = [Path.cwd()]
                        if getattr(sys, 'frozen', False):
                            search_paths.append(Path(sys.executable).parent)
                        
                        for sp in search_paths:
                            for filename in ['claude.txt', 'anthropic.txt']:
                                fp = sp / filename
                                if fp.exists():
                                    with open(fp, 'r') as f:
                                        val = f.read().strip()
                                        if val:
                                            api_key_to_use = val
                                            break
                            if api_key_to_use: break
                    except Exception:
                        pass

            # Final validation - Fail fast if no key
            if not api_key_to_use and not os.getenv('ANTHROPIC_API_KEY'):
                raise ValueError("Claude API Key not found. Please configure it in Tools > Configure Settings, or ensure ANTHROPIC_API_KEY is set.")

            if api_key_to_use:
                client = anthropic.Anthropic(api_key=api_key_to_use)
            else:
                client = anthropic.Anthropic()  # Uses ANTHROPIC_API_KEY env var
            
            # Format messages for Claude
            claude_messages = []
            
            for i, msg in enumerate(self.messages):
                if i == 0 and msg['role'] == 'user' and self.image_path:
                    # First user message with image - include image as base64
                    with open(self.image_path, 'rb') as f:
                        image_data = base64.b64encode(f.read()).decode('utf-8')
                    
                    # Determine media type
                    ext = Path(self.image_path).suffix.lower()
                    media_types = {
                        '.jpg': 'image/jpeg',
                        '.jpeg': 'image/jpeg',
                        '.png': 'image/png',
                        '.gif': 'image/gif',
                        '.webp': 'image/webp'
                    }
                    media_type = media_types.get(ext, 'image/jpeg')
                    
                    claude_messages.append({
                        'role': 'user',
                        'content': [
                            {
                                'type': 'image',
                                'source': {
                                    'type': 'base64',
                                    'media_type': media_type,
                                    'data': image_data
                                }
                            },
                            {'type': 'text', 'text': msg['content']}
                        ]
                    })
                else:
                    # Subsequent messages or text-only mode - text only
                    claude_messages.append({
                        'role': msg['role'],
                        'content': msg['content']
                    })
            
            # Stream response from Claude
            with client.messages.stream(
                model=self.model,
                max_tokens=2048,
                messages=claude_messages
            ) as stream:
                for text_chunk in stream.text_stream:
                    self._full_response += text_chunk
                    
                    # Emit update event for each chunk
                    evt = ChatUpdateEvent(message_chunk=text_chunk)
                    wx.PostEvent(self.parent_window, evt)
            
            # Get final message for metadata
            final_message = stream.get_final_message()
            
            # Emit completion event
            metadata = {
                'provider': 'claude',
                'model': self.model,
                'tokens': {
                    'input_tokens': final_message.usage.input_tokens,
                    'output_tokens': final_message.usage.output_tokens,
                    'total_tokens': final_message.usage.input_tokens + final_message.usage.output_tokens
                }
            }
            evt = ChatCompleteEvent(full_response=self._full_response, metadata=metadata)
            wx.PostEvent(self.parent_window, evt)
            
        except Exception as e:
            raise Exception(f"Claude chat error: {str(e)}")


class BatchProcessingWorker(threading.Thread):
    """Worker thread for batch processing multiple images
    
    Processes multiple images sequentially, emitting progress for each.
    Uses ProcessingWorker internally for each image but runs them sequentially.
    
    Phase 2: Enhanced with pause/resume/stop controls using threading.Event
    
    Events:
        ProgressUpdateEvent: Progress messages for each image
        ProcessingCompleteEvent: Success for each completed image
        ProcessingFailedEvent: Error for any failed image
        WorkflowCompleteEvent: All images completed
    """
    
    def __init__(self, parent_window, file_paths: list, provider: str, model: str,
                 prompt_style: str, custom_prompt: str = "",
                 detection_settings: dict = None,
                 prompt_config_path: Optional[str] = None,
                 skip_existing: bool = False,
                 progress_offset: int = 0):
        """Initialize batch worker
        
        Args:
            parent_window: wxWindow to receive events
            file_paths: List of image file paths to process
            provider: AI provider name
            model: Model name
            prompt_style: Prompt style name
            custom_prompt: Custom prompt text (overrides prompt_style)
            detection_settings: Optional settings for object detection
            prompt_config_path: Optional path to prompt config file
            skip_existing: Skip images that already have descriptions
            progress_offset: Offset to add to progress counter (for continuing after video extraction)
        """
        super().__init__(daemon=True)
        self.parent_window = parent_window
        self.file_paths = file_paths
        self.provider = provider
        self.model = model
        self.prompt_style = prompt_style
        self.custom_prompt = custom_prompt
        self.detection_settings = detection_settings
        self.prompt_config_path = prompt_config_path
        self.skip_existing = skip_existing
        self.progress_offset = progress_offset
        
        # Phase 2: Pause/Resume/Stop controls using threading.Event
        self._stop_event = threading.Event()  # Set = stopped
        self._pause_event = threading.Event()  # Set = running, cleared = paused
        self._pause_event.set()  # Start in running state
    
    def run(self):
        """Process all images sequentially"""
        try:
            total = len(self.file_paths)
            completed = 0
            failed = 0
            
            for i, file_path in enumerate(self.file_paths, 1):
                # Phase 2: Check if stopped
                if self._stop_event.is_set():
                    break
                
                # Phase 2: Wait if paused (blocks here until resume)
                self._pause_event.wait()
                
                # Phase 2: Double-check stop after unpause
                if self._stop_event.is_set():
                    break
                
                # Post progress with current/total counts (add offset for continuing from video extraction)
                current_progress = i + self.progress_offset
                total_progress = total + self.progress_offset
                evt = ProgressUpdateEventData(
                    file_path=file_path,
                    message=f"Processing {i}/{total}: {Path(file_path).name}",
                    current=current_progress,
                    total=total_progress
                )
                wx.PostEvent(self.parent_window, evt)
                
                # Create worker for this image
                worker = ProcessingWorker(
                    self.parent_window,
                    file_path,
                    self.provider,
                    self.model,
                    self.prompt_style,
                    self.custom_prompt,
                    self.detection_settings,
                    self.prompt_config_path
                )
                
                # Run synchronously and wait
                worker.start()
                worker.join()  # Wait for completion
                
                # Track completion (events are posted by ProcessingWorker)
                completed += 1
            
            # Post final completion
            evt = WorkflowCompleteEventData(
                input_dir=f"{completed}/{total} images",
                output_dir=""
            )
            wx.PostEvent(self.parent_window, evt)
            
        except Exception as e:
            # Comprehensive error logging for debugging frozen executables
            error_msg = f"FATAL ERROR in BatchProcessingWorker: {type(e).__name__}: {e}"
            tb_str = traceback.format_exc()
            
            print(f"\n{'='*60}", flush=True)
            print(error_msg, flush=True)
            print(tb_str, flush=True)
            print('='*60, flush=True)
            
            logger.error(error_msg, exc_info=True)
            
            # Write to dedicated crash log
            try:
                crash_log = Path.home() / 'imagedescriber_crash.log'
                with open(crash_log, 'a', encoding='utf-8') as f:
                    f.write(f"\n{'='*60}\n")
                    f.write(f"{datetime.now().isoformat()} - BatchProcessingWorker crash\n")
                    f.write(f"Processing {len(self.file_paths)} files\n")
                    f.write(f"Provider: {self.provider}, Model: {self.model}\n")
                    f.write(f"Error: {error_msg}\n")
                    f.write(f"Traceback:\n{tb_str}\n")
                    f.write('='*60 + '\n')
                logger.info(f"Crash details written to {crash_log}")
            except Exception as log_error:
                logger.error(f"Failed to write crash log: {log_error}")
            
            # Post failure event
            evt = WorkflowFailedEventData(error=f"Batch processing failed: {str(e)}")
            wx.PostEvent(self.parent_window, evt)
    
    def pause(self):
        """Pause batch processing after current image completes"""
        self._pause_event.clear()
    
    def resume(self):
        """Resume paused batch processing"""
        self._pause_event.set()
    
    def stop(self):
        """Stop batch processing (cannot resume)"""
        self._stop_event.set()
        self._pause_event.set()  # Unblock if paused
    
    def is_paused(self) -> bool:
        """Check if currently paused"""
        return not self._pause_event.is_set()
    
    def cancel(self):
        """Deprecated: Use stop() instead. Request cancellation of batch processing"""
        self.stop()


class VideoProcessingWorker(threading.Thread):
    """Worker thread for video frame extraction
    
    Extracts frames from video files using OpenCV, supporting both
    time-based intervals and scene change detection.
    
    Events:
        ProgressUpdateEvent: Progress messages during extraction
        WorkflowCompleteEvent: Success with extracted frame paths
        WorkflowFailedEvent: Error during extraction
    """
    
    def __init__(self, parent_window, video_path: str, extraction_config: dict):
        """Initialize video extraction worker
        
        Args:
            parent_window: wxWindow to receive events
            video_path: Path to video file
            extraction_config: Dictionary with extraction settings:
                - extraction_mode: "time_interval" or "scene_detection"
                - time_interval_seconds: Interval between frames (time mode)
                - start_time_seconds: Start time in video
                - end_time_seconds: Optional end time
                - max_frames_per_video: Optional maximum frames
                - scene_change_threshold: Sensitivity 0-100 (scene mode)
                - min_scene_duration_seconds: Minimum scene length (scene mode)
        """
        super().__init__(daemon=True)
        self.parent_window = parent_window
        self.video_path = video_path
        self.extraction_config = extraction_config
    
    def run(self):
        """Extract frames from video"""
        print(f"VideoProcessingWorker.run() STARTED for {Path(self.video_path).name}", flush=True)
        logger.info(f"VideoProcessingWorker.run() started for {self.video_path}")
        logger.debug(f"Extraction config: {self.extraction_config}")
        
        try:
            print(f"Posting progress message...", flush=True)
            self._post_progress(f"Extracting frames from: {Path(self.video_path).name}")
            logger.debug("Starting _extract_frames()")
            
            print(f"Calling _extract_frames()...", flush=True)
            # Extract frames and get video metadata
            extracted_frames, video_metadata = self._extract_frames()
            print(f"_extract_frames() returned {len(extracted_frames)} frames", flush=True)
            logger.info(f"_extract_frames() completed: {len(extracted_frames)} frames extracted")
            
            if extracted_frames:
                self._post_progress(f"Extracted {len(extracted_frames)} frames")
                evt = WorkflowCompleteEventData(
                    input_dir=self.video_path,
                    output_dir=str(Path(extracted_frames[0]).parent)
                )
                # Attach video metadata to event
                evt.video_metadata = video_metadata
                print(f"Posting WorkflowCompleteEventData...", flush=True)
                logger.debug(f"Posting WorkflowCompleteEventData to parent window")
                wx.PostEvent(self.parent_window, evt)
                print(f"WorkflowCompleteEventData posted", flush=True)
                logger.debug("WorkflowCompleteEventData posted successfully")
            else:
                print(f"WARNING: No frames extracted!", flush=True)
                logger.warning("No frames were extracted from video")
                evt = WorkflowFailedEventData(error="No frames were extracted from video")
                wx.PostEvent(self.parent_window, evt)
                
        except Exception as e:
            # Comprehensive error logging for debugging frozen executables
            error_msg = f"FATAL ERROR in VideoProcessingWorker: {type(e).__name__}: {e}"
            tb_str = traceback.format_exc()
            
            print(f"\n{'='*60}", flush=True)
            print(error_msg, flush=True)
            print(tb_str, flush=True)
            print('='*60, flush=True)
            
            logger.error(error_msg, exc_info=True)
            
            # Write to dedicated crash log for frozen executable debugging
            try:
                crash_log = Path.home() / 'imagedescriber_crash.log'
                with open(crash_log, 'a', encoding='utf-8') as f:
                    f.write(f"\n{'='*60}\n")
                    f.write(f"{datetime.now().isoformat()} - VideoProcessingWorker crash\n")
                    f.write(f"Video: {self.video_path}\n")
                    f.write(f"Error: {error_msg}\n")
                    f.write(f"Traceback:\n{tb_str}\n")
                    f.write('='*60 + '\n')
                logger.info(f"Crash details written to {crash_log}")
            except Exception as log_error:
                logger.error(f"Failed to write crash log: {log_error}")
            
            evt = WorkflowFailedEventData(error=f"Video processing failed: {str(e)}")
            wx.PostEvent(self.parent_window, evt)
    
    def _post_progress(self, message: str):
        """Post progress update"""
        evt = ProgressUpdateEventData(file_path=self.video_path, message=message)
        wx.PostEvent(self.parent_window, evt)
    
    def _extract_frames(self) -> tuple:
        """Extract frames from video based on configuration
        
        Returns:
            tuple: (list of extracted frame paths, video metadata dict)
        """
        try:
            import cv2
        except ImportError:
            raise Exception("OpenCV (cv2) not available. Please install opencv-python.")
        
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            raise Exception("Could not open video file")
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0
        
        # Store metadata
        video_metadata = {
            'fps': fps,
            'total_frames': frame_count,
            'duration': duration
        }
        
        # Create output directory in workspace (NOT in source directory)
        video_path_obj = Path(self.video_path)
        
        # Get workspace directory from parent window
        if hasattr(self.parent_window, 'get_workspace_directory'):
            workspace_dir = self.parent_window.get_workspace_directory()
            extracted_frames_dir = workspace_dir / "extracted_frames"
            video_dir = extracted_frames_dir / f"{video_path_obj.stem}"
        else:
            # Fallback for older code or if method not available
            toolkit_dir = video_path_obj.parent / "imagedescriptiontoolkit"
            video_dir = toolkit_dir / f"{video_path_obj.stem}_frames"
        
        video_dir.mkdir(parents=True, exist_ok=True)
        
        # Extract based on mode
        extraction_mode = self.extraction_config.get("extraction_mode", "time_interval")
        if extraction_mode == "scene_change":
            extracted_paths = self._extract_by_scene_detection(cap, fps, video_dir)
        else:
            # Default to time_interval if mode not recognized
            extracted_paths = self._extract_by_time_interval(cap, fps, video_dir)
        
        cap.release()
        return extracted_paths, video_metadata
    
    def _extract_by_time_interval(self, cap, fps: float, output_dir: Path) -> list:
        """Extract frames at regular time intervals"""
        import cv2
        
        interval_seconds = self.extraction_config.get("time_interval_seconds", 5)
        start_time = self.extraction_config.get("start_time_seconds", 0)
        end_time = self.extraction_config.get("end_time_seconds")
        
        total_frames_in_video = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_interval = max(1, int(fps * interval_seconds))  # Minimum 1 frame
        start_frame = int(fps * start_time)
        
        # Calculate end point (either user-specified or video end)
        if end_time:
            end_frame = int(fps * end_time)
        else:
            end_frame = total_frames_in_video
        
        # EMERGENCY: Safety limit
        safety_limit = total_frames_in_video + 10
        
        # Log extraction parameters for debugging
        self._post_progress(f"FPS: {fps:.2f}, Interval: {interval_seconds}s = {frame_interval} frames")
        self._post_progress(f"Video: {total_frames_in_video} frames total, extracting frames {start_frame} to {end_frame}")
        
        extracted_paths = []
        frame_num = start_frame
        extract_count = 0
        
        video_stem = Path(self.video_path).stem
        
        # Use CLI logic: check frame position in while condition
        while frame_num < end_frame:
            # EMERGENCY STOP (shouldn't be needed, but keep as safety)
            if extract_count >= safety_limit:
                self._post_progress(f"SAFETY STOP: Extracted {extract_count} frames from {total_frames_in_video}-frame video!")
                break
            
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ret, frame = cap.read()
            
            if not ret:
                break
            
            # Calculate timestamp (matches CLI convention)
            timestamp = frame_num / fps
            
            # Save frame with timestamp in filename (matches CLI: video_0.00s.jpg)
            frame_filename = f"{video_stem}_{timestamp:.2f}s.jpg"
            frame_path = output_dir / frame_filename
            cv2.imwrite(str(frame_path), frame)
            extracted_paths.append(str(frame_path))
            
            extract_count += 1
            frame_num += frame_interval
            
            if extract_count % 10 == 0:
                self._post_progress(f"Extracted {extract_count} frames...")
        
        return extracted_paths
    
    def _extract_by_scene_detection(self, cap, fps: float, output_dir: Path) -> list:
        """Extract frames based on scene changes"""
        import cv2
        
        threshold = self.extraction_config.get("scene_change_threshold", 30) / 100.0
        min_duration = self.extraction_config.get("min_scene_duration_seconds", 1)
        
        extracted_paths = []
        prev_frame = None
        last_extract_frame = -1
        min_frame_gap = int(fps * min_duration)
        frame_num = 0
        extract_count = 0
        
        video_stem = Path(self.video_path).stem
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Calculate difference from previous frame
            if prev_frame is not None:
                # Convert to grayscale for comparison
                gray_current = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray_prev = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
                
                # Calculate mean squared difference
                diff = cv2.absdiff(gray_current, gray_prev)
                mean_diff = diff.mean() / 255.0
                
                # Check if scene change detected and minimum duration passed
                if (mean_diff > threshold and 
                    frame_num - last_extract_frame >= min_frame_gap):
                    
                    # Calculate timestamp (matches CLI convention)
                    timestamp = frame_num / fps
                    
                    # Save frame with scene number and timestamp (matches CLI: video_scene_0001_5.23s.jpg)
                    frame_filename = f"{video_stem}_scene_{extract_count:04d}_{timestamp:.2f}s.jpg"
                    frame_path = output_dir / frame_filename
                    cv2.imwrite(str(frame_path), frame)
                    extracted_paths.append(str(frame_path))
                    
                    last_extract_frame = frame_num
                    extract_count += 1
                    
                    if extract_count % 10 == 0:
                        self._post_progress(f"Extracted {extract_count} scenes...")
            
            prev_frame = frame.copy()
            frame_num += 1
        
        return extracted_paths


class HEICConversionWorker(threading.Thread):
    """Worker thread for converting HEIC files to JPEG
    
    Converts HEIC/HEIF images to JPEG format in-place, preserving metadata.
    Emits progress updates and results via wxPython events.
    
    Events:
        ProgressUpdateEvent: Progress messages during conversion
        ConversionCompleteEvent: Successful conversion (count, converted_files)
        ConversionFailedEvent: Conversion error (error message)
    """
    
    def __init__(self, parent_window, heic_files: list, quality: int = 95):
        """Initialize HEIC conversion worker
        
        Args:
            parent_window: Parent wxPython window for event posting
            heic_files: List of HEIC file paths to convert
            quality: JPEG quality (1-100, default 95)
        """
        super().__init__(daemon=True)
        self.parent = parent_window
        self.heic_files = heic_files
        self.quality = quality
        self._stop_event = threading.Event()
    
    def run(self):
        """Convert HEIC files to JPEG"""
        try:
            # Import conversion function from scripts
            sys.path.insert(0, str(_project_root / 'scripts'))
            from ConvertImage import convert_heic_to_jpg
            
            converted = []
            failed = []
            total = len(self.heic_files)
            
            for i, heic_path in enumerate(self.heic_files, 1):
                if self._stop_event.is_set():
                    break
                
                heic_file = Path(heic_path)
                self._post_progress(f"Converting {i}/{total}: {heic_file.name}")
                
                # Convert in-place (HEIC -> JPG in same directory)
                output_path = heic_file.with_suffix('.jpg')
                
                try:
                    success = convert_heic_to_jpg(
                        heic_file,
                        output_path,
                        quality=self.quality,
                        keep_metadata=True
                    )
                    
                    if success:
                        converted.append(str(output_path))
                        # NOTE: Original HEIC file is preserved (not deleted)
                        # This follows IDT's rule: never modify originals in original location
                    else:
                        failed.append(heic_file.name)
                
                except Exception as e:
                    failed.append(f"{heic_file.name} ({str(e)})")
            
            # Post completion event
            evt = ConversionCompleteEvent(
                converted_count=len(converted),
                failed_count=len(failed),
                converted_files=converted,
                failed_files=failed
            )
            wx.PostEvent(self.parent, evt)
        
        except Exception as e:
            # Post failure event
            evt = ConversionFailedEvent(error=str(e))
            wx.PostEvent(self.parent, evt)
    
    def _post_progress(self, message: str):
        """Post progress update to parent window"""
        evt = ProgressUpdateEvent(file_path=None, message=message)
        wx.PostEvent(self.parent, evt)
    
    def stop(self):
        """Request worker to stop"""
        self._stop_event.set()


class DownloadProcessingWorker(threading.Thread):
    """
    Worker thread for downloading images from URLs.
    
    Uses WebImageDownloader to fetch images from web pages and stores them
    in the workspace's downloaded_images/ directory.
    """
    
    def __init__(self, parent_window, url: str, workspace_dir: Path, settings: dict):
        """
        Initialize download worker.
        
        Args:
            parent_window: Parent window for event posting
            url: URL to download images from
            workspace_dir: Workspace directory (base path)
            settings: Download settings dict with keys:
                - min_width: Minimum image width
                - min_height: Minimum image height
                - max_images: Maximum images to download (None for unlimited)
                - auto_add: Whether to auto-add to workspace
        """
        super().__init__(daemon=True)
        self.parent_window = parent_window
        self.url = url
        self.workspace_dir = workspace_dir
        self.settings = settings
        self.output_dir = workspace_dir / "downloaded_images"
    
    def run(self):
        """Run the download process."""
        try:
            # Create output directory
            self.output_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Starting image download from: {self.url}")
            logger.info(f"Output directory: {self.output_dir}")
            
            # Check if WebImageDownloader is available
            if WebImageDownloader is None:
                error_msg = "WebImageDownloader not available. Missing BeautifulSoup4 library."
                logger.error(error_msg)
                evt = WorkflowFailedEventData(error=error_msg)
                wx.PostEvent(self.parent_window, evt)
                return
            
            # Create downloader instance
            downloader = WebImageDownloader(
                url=self.url,
                output_dir=self.output_dir,
                min_width=self.settings.get('min_width', 0),
                min_height=self.settings.get('min_height', 0),
                max_images=self.settings.get('max_images', None),
                progress_callback=self._post_progress,
                verbose=True
            )
            
            # Download images
            downloaded_count, failed_count = downloader.download()
            
            logger.info(f"Download complete: {downloaded_count} images downloaded, {failed_count} failed")
            
            # Post completion event
            evt = WorkflowCompleteEventData(
                input_dir=str(self.url),
                output_dir=str(self.output_dir)
            )
            # Add download-specific attributes
            evt.step_name = "download"
            evt.files_processed = downloaded_count
            wx.PostEvent(self.parent_window, evt)
            
        except Exception as e:
            logger.error(f"Download error: {e}", exc_info=True)
            
            # Write crash log
            try:
                crash_log_path = Path.home() / "imagedescriber_crash.log"
                with open(crash_log_path, 'a', encoding='utf-8') as f:
                    f.write(f"\n{'='*80}\n")
                    f.write(f"Download Worker Crash: {datetime.now().isoformat()}\n")
                    f.write(f"URL: {self.url}\n")
                    f.write(f"{'='*80}\n")
                    f.write(traceback.format_exc())
                    f.write(f"\n{'='*80}\n\n")
                logger.error(f"Crash log written to: {crash_log_path}")
            except Exception as log_err:
                logger.error(f"Could not write crash log: {log_err}")
            
            # Post failure event
            evt = WorkflowFailedEventData(error=str(e))
            wx.PostEvent(self.parent_window, evt)
    
    def _post_progress(self, current: int, total: int, status: str):
        """
        Post progress update to main window.
        
        Args:
            current: Current image number
            total: Total images found
            status: Status message
        """
        try:
            evt = ProgressUpdateEventData(
                file_path="",  # No specific file path for download progress
                message=status,
                current=current,
                total=total
            )
            wx.PostEvent(self.parent_window, evt)
        except Exception as e:
            logger.warning(f"Could not post progress update: {e}")


class DirectoryScanWorker(threading.Thread):
    """Worker thread for async directory scanning with progressive updates
    
    Scans directory for images/videos in background, emitting batches of discovered files
    as they're found. Critical for network share performance where synchronous scanning
    can take minutes for directories with thousands of files.
    
    Events:
        FilesDiscoveredEvent: Batch of files discovered (sent periodically during scan)
        ScanProgressEvent: Progress updates with file count
        ScanCompleteEvent: Scan finished with total count and time
        ScanFailedEvent: Error during scanning
    """
    
    # Supported image and video extensions
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic', '.heif', '.tiff', '.tif'}
    VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.m4v', '.webm', '.flv', '.wmv'}
    
    def __init__(self, parent_window, directory_path: Path, batch_size: int = 50, recursive: bool = True):
        """Initialize directory scanner
        
        Args:
            parent_window: wxWindow to receive events
            directory_path: Path object for directory to scan
            batch_size: Number of files to collect before sending batch event (default 50)
            recursive: Whether to scan subdirectories (default True)
        """
        super().__init__(daemon=True)
        self.parent_window = parent_window
        self.directory_path = Path(directory_path)
        self.batch_size = batch_size
        self.recursive = recursive
        self._stop_flag = False
        
    def stop(self):
        """Request worker to stop scanning"""
        self._stop_flag = True
    
    def run(self):
        """Execute directory scan in background thread"""
        start_time = time.time()
        all_files = []
        batch = []
        batch_number = 0
        
        try:
            # Post initial progress
            self._post_progress("Starting directory scan...", 0)
            
            # Determine scan pattern
            if self.recursive:
                scan_pattern = '**/*'
            else:
                scan_pattern = '*'
            
            # Scan directory
            for file_path in self.directory_path.glob(scan_pattern):
                # Check stop flag
                if self._stop_flag:
                    logger.info("Directory scan stopped by user")
                    return
                
                # Skip directories
                if file_path.is_dir():
                    continue
                
                # Check if file is image or video
                if file_path.suffix.lower() in self.IMAGE_EXTENSIONS or file_path.suffix.lower() in self.VIDEO_EXTENSIONS:
                    batch.append(file_path)
                    all_files.append(file_path)
                    
                    # Send batch when full
                    if len(batch) >= self.batch_size:
                        batch_number += 1
                        self._post_batch(batch, batch_number, all_files)
                        
                        # Post progress update
                        self._post_progress(f"Found {len(all_files)} files...", len(all_files))
                        
                        # Clear batch for next iteration
                        batch = []
            
            # Send final batch (if any)
            if batch:
                batch_number += 1
                self._post_batch(batch, batch_number, all_files)
            
            # Calculate elapsed time
            elapsed = time.time() - start_time
            
            # Post completion event
            logger.info(f"Directory scan complete: {len(all_files)} files in {elapsed:.2f}s")
            evt = ScanCompleteEventData(
                total_files=len(all_files),
                elapsed_time=elapsed
            )
            wx.PostEvent(self.parent_window, evt)
            
        except Exception as e:
            logger.error(f"Directory scan error: {e}", exc_info=True)
            evt = ScanFailedEventData(error=str(e))
            wx.PostEvent(self.parent_window, evt)
    
    def _post_batch(self, batch, batch_number, all_files):
        """Post batch of discovered files to main window"""
        try:
            # Estimate total batches (may change as scan progresses)
            total_batches = (len(all_files) // self.batch_size) + 1
            
            evt = FilesDiscoveredEventData(
                files=batch.copy(),  # Copy to avoid reference issues
                batch_number=batch_number,
                total_batches=total_batches
            )
            wx.PostEvent(self.parent_window, evt)
        except Exception as e:
            logger.warning(f"Could not post files discovered event: {e}")
    
    def _post_progress(self, message, files_found):
        """Post progress update to main window"""
        try:
            evt = ScanProgressEventData(
                message=message,
                files_found=files_found
            )
            wx.PostEvent(self.parent_window, evt)
        except Exception as e:
            logger.warning(f"Could not post scan progress: {e}")


class SaveWorkspaceWorker(threading.Thread):
    """Worker thread for saving workspace to file in background"""
    
    def __init__(self, parent_window, workspace_data, file_path, 
                 old_ws_dir, new_ws_dir, workspace_items):
        """Initialize workspace save worker
        
        Args:
            parent_window: Parent window to post events to
            workspace_data: Workspace dictionary to save
            file_path: Path to save workspace file
            old_ws_dir: Old workspace directory (or None)
            new_ws_dir: New workspace directory
            workspace_items: Dictionary of workspace items
        """
        super().__init__(daemon=True)
        self.parent_window = parent_window
        self.workspace_data = workspace_data
        self.file_path = file_path
        self.old_ws_dir = old_ws_dir
        self.new_ws_dir = new_ws_dir
        self.workspace_items = workspace_items
        
    def run(self):
        """Save workspace in background thread"""
        try:
            import json
            import shutil
            from pathlib import Path
            
            # Move extracted frames if workspace location changed
            workspace_changed = self.old_ws_dir is not None
            if workspace_changed and self.old_ws_dir and self.old_ws_dir.exists():
                old_extracted_frames = self.old_ws_dir / "extracted_frames"
                new_extracted_frames = self.new_ws_dir / "extracted_frames"
                
                if old_extracted_frames.exists():
                    # Move the entire extracted_frames directory
                    if new_extracted_frames.exists():
                        shutil.rmtree(new_extracted_frames)
                    shutil.move(str(old_extracted_frames), str(new_extracted_frames))
                    
                    # Update all extracted_frame item paths
                    for item in self.workspace_items.values():
                        if item.item_type == "extracted_frame":
                            old_path = Path(item.file_path)
                            # Reconstruct path in new location
                            relative_to_old = old_path.relative_to(old_extracted_frames)
                            new_path = new_extracted_frames / relative_to_old
                            item.file_path = str(new_path)
                        
                        # Update extracted_frames list for video items
                        if hasattr(item, 'extracted_frames') and item.extracted_frames:
                            updated_frames = []
                            for frame_path in item.extracted_frames:
                                old_frame_path = Path(frame_path)
                                try:
                                    relative_to_old = old_frame_path.relative_to(old_extracted_frames)
                                    new_frame_path = new_extracted_frames / relative_to_old
                                    updated_frames.append(str(new_frame_path))
                                except ValueError:
                                    # Path not relative to old location, keep as-is
                                    updated_frames.append(frame_path)
                            item.extracted_frames = updated_frames
                    
                    # Clean up old workspace directory if empty
                    try:
                        if self.old_ws_dir.exists() and not any(self.old_ws_dir.iterdir()):
                            self.old_ws_dir.rmdir()
                    except:
                        pass  # Ignore cleanup errors
            
            # Save to file with proper JSON encoding
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.workspace_data, f, indent=2, ensure_ascii=False, default=str)
            
            # Post success event
            evt = WorkspaceSaveCompleteEvent(file_path=self.file_path)
            wx.PostEvent(self.parent_window, evt)
            
        except Exception as e:
            logger.error(f"Workspace save failed: {e}", exc_info=True)
            evt = WorkspaceSaveFailedEvent(error=str(e))
            wx.PostEvent(self.parent_window, evt)
