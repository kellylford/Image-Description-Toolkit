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
from pathlib import Path
from typing import Optional, Dict, Any

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

# Import AI providers
try:
    from .ai_providers import get_available_providers
except ImportError:
    try:
        from ai_providers import get_available_providers
    except ImportError:
        get_available_providers = None

# Create custom event types for thread communication
ProgressUpdateEvent, EVT_PROGRESS_UPDATE = wx.lib.newevent.NewEvent()
ProcessingCompleteEvent, EVT_PROCESSING_COMPLETE = wx.lib.newevent.NewEvent()
ProcessingFailedEvent, EVT_PROCESSING_FAILED = wx.lib.newevent.NewEvent()
WorkflowCompleteEvent, EVT_WORKFLOW_COMPLETE = wx.lib.newevent.NewEvent()
WorkflowFailedEvent, EVT_WORKFLOW_FAILED = wx.lib.newevent.NewEvent()
ConversionCompleteEvent, EVT_CONVERSION_COMPLETE = wx.lib.newevent.NewEvent()
ConversionFailedEvent, EVT_CONVERSION_FAILED = wx.lib.newevent.NewEvent()


# Custom event classes that properly store attributes
class ProcessingCompleteEventData(ProcessingCompleteEvent):
    """Event data for processing completion"""
    def __init__(self, file_path, description, provider, model, prompt_style, custom_prompt):
        ProcessingCompleteEvent.__init__(self)
        self.file_path = file_path
        self.description = description
        self.provider = provider
        self.model = model
        self.prompt_style = prompt_style
        self.custom_prompt = custom_prompt


class ProcessingFailedEventData(ProcessingFailedEvent):
    """Event data for processing failure"""
    def __init__(self, file_path, error):
        ProcessingFailedEvent.__init__(self)
        self.file_path = file_path
        self.error = error


class ProgressUpdateEventData(ProgressUpdateEvent):
    """Event data for progress updates"""
    def __init__(self, file_path, message):
        ProgressUpdateEvent.__init__(self)
        self.file_path = file_path
        self.message = message


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
                 prompt_config_path: Optional[str] = None):
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
        """
        super().__init__(daemon=True)
        self.parent_window = parent_window
        self.file_path = file_path
        self.provider = provider
        self.model = model
        self.prompt_style = prompt_style
        self.custom_prompt = custom_prompt
        self.detection_settings = detection_settings or {}
        
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
            
            # Process the image with selected provider
            description = self._process_with_ai(self.file_path, prompt_text)
            
            # Emit success
            evt = ProcessingCompleteEventData(
                file_path=self.file_path,
                description=description,
                provider=self.provider,
                model=self.model,
                prompt_style=self.prompt_style,
                custom_prompt=self.custom_prompt
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
    
    def _process_with_ai(self, image_path: str, prompt: str) -> str:
        """Process image with selected AI provider"""
        if not get_available_providers:
            raise Exception("AI providers module not available")
        
        # Get available providers
        providers = get_available_providers()
        
        if self.provider not in providers:
            raise Exception(f"Provider '{self.provider}' not available")
        
        provider = providers[self.provider]
        
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
            if len(image_data) > max_size:
                image_data = self._resize_image_data(image_data, max_size)
            
            # Process with the selected provider
            if self.provider == "object_detection" and self.detection_settings:
                description = provider.describe_image(image_path, prompt, self.model, 
                                                     yolo_settings=self.detection_settings)
            elif self.provider in ["grounding_dino", "grounding_dino_hybrid"] and self.detection_settings:
                description = provider.describe_image(image_path, prompt, self.model, 
                                                     **self.detection_settings)
            else:
                description = provider.describe_image(image_path, prompt, self.model)
            
            return description
                
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
            print(f"Image resize error: {e}")
            return image_data  # Return original if resize fails


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


class BatchProcessingWorker(threading.Thread):
    """Worker thread for batch processing multiple images
    
    Processes multiple images sequentially, emitting progress for each.
    Uses ProcessingWorker internally for each image but runs them sequentially.
    
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
                 skip_existing: bool = False):
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
        self._cancel = False
    
    def run(self):
        """Process all images sequentially"""
        total = len(self.file_paths)
        completed = 0
        failed = 0
        
        for i, file_path in enumerate(self.file_paths, 1):
            if self._cancel:
                break
            
            # Post progress
            evt = ProgressUpdateEventData(
                file_path=file_path,
                message=f"Processing {i}/{total}: {Path(file_path).name}"
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
    
    def cancel(self):
        """Request cancellation of batch processing"""
        self._cancel = True


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
        try:
            self._post_progress(f"Extracting frames from: {Path(self.video_path).name}")
            
            # Extract frames
            extracted_frames = self._extract_frames()
            
            if extracted_frames:
                self._post_progress(f"Extracted {len(extracted_frames)} frames")
                evt = WorkflowCompleteEventData(
                    input_dir=self.video_path,
                    output_dir=str(Path(extracted_frames[0]).parent)
                )
                wx.PostEvent(self.parent_window, evt)
            else:
                evt = WorkflowFailedEventData(error="No frames were extracted from video")
                wx.PostEvent(self.parent_window, evt)
                
        except Exception as e:
            evt = WorkflowFailedEventData(error=f"Video processing failed: {str(e)}")
            wx.PostEvent(self.parent_window, evt)
    
    def _post_progress(self, message: str):
        """Post progress update"""
        evt = ProgressUpdateEventData(file_path=self.video_path, message=message)
        wx.PostEvent(self.parent_window, evt)
    
    def _extract_frames(self) -> list:
        """Extract frames from video based on configuration"""
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
        
        # Create output directory
        video_path = Path(self.video_path)
        toolkit_dir = video_path.parent / "imagedescriptiontoolkit"
        video_dir = toolkit_dir / f"{video_path.stem}_frames"
        video_dir.mkdir(parents=True, exist_ok=True)
        
        # Extract based on mode
        if self.extraction_config.get("extraction_mode") == "time_interval":
            extracted_paths = self._extract_by_time_interval(cap, fps, video_dir)
        else:
            extracted_paths = self._extract_by_scene_detection(cap, fps, video_dir)
        
        cap.release()
        return extracted_paths
    
    def _extract_by_time_interval(self, cap, fps: float, output_dir: Path) -> list:
        """Extract frames at regular time intervals"""
        import cv2
        
        interval_seconds = self.extraction_config.get("time_interval_seconds", 5)
        start_time = self.extraction_config.get("start_time_seconds", 0)
        end_time = self.extraction_config.get("end_time_seconds")
        max_frames = self.extraction_config.get("max_frames_per_video")
        
        frame_interval = int(fps * interval_seconds)
        start_frame = int(fps * start_time)
        
        extracted_paths = []
        frame_num = start_frame
        extract_count = 0
        
        video_stem = Path(self.video_path).stem
        
        while True:
            if max_frames and extract_count >= max_frames:
                break
            
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ret, frame = cap.read()
            
            if not ret:
                break
            
            # Check end time limit
            current_time = frame_num / fps
            if end_time and current_time > end_time:
                break
            
            # Save frame
            frame_filename = f"{video_stem}_frame_{extract_count:04d}.jpg"
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
        max_frames = self.extraction_config.get("max_frames_per_video")
        
        extracted_paths = []
        prev_frame = None
        last_extract_frame = -1
        min_frame_gap = int(fps * min_duration)
        frame_num = 0
        extract_count = 0
        
        video_stem = Path(self.video_path).stem
        
        while True:
            if max_frames and extract_count >= max_frames:
                break
            
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
                    
                    # Save frame
                    frame_filename = f"{video_stem}_scene_{extract_count:04d}.jpg"
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
