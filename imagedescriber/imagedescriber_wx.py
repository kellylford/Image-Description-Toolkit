#!/usr/bin/env python3
"""
ImageDescriber (wxPython) - AI-Powered Image Description GUI

wxPython port of the Qt6 ImageDescriber with improved macOS VoiceOver accessibility.
Document-based workspace for processing images and generating AI descriptions.

Features:
- Document-based workspace (save/load projects)
- Individual and batch image processing
- Multiple descriptions per image with editing/deletion
- Video frame extraction with nested display
- HEIC conversion support
- Menu-driven accessible interface
- Built-in AI processing with configurable prompts
- Full keyboard navigation and screen reader support
"""

import sys
import os
import json
import logging
import re
import subprocess
import threading
import time
import base64
import tempfile
import shutil
import webbrowser
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime

# Add project root to path for shared module imports
# Works in both development mode (running script) and frozen mode (PyInstaller exe)
if getattr(sys, 'frozen', False):
    # Frozen mode - executable directory is base
    _project_root = Path(sys.executable).parent
    _imagedescriber_dir = _project_root  # In frozen mode, all modules are at exe level
else:
    # Development mode - use __file__ relative path
    _project_root = Path(__file__).parent.parent
    _imagedescriber_dir = Path(__file__).parent

if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
if str(_imagedescriber_dir) not in sys.path:
    sys.path.insert(0, str(_imagedescriber_dir))

import wx
import wx.lib.newevent

# Import shared utilities
try:
    from shared.wx_common import (
        find_config_file,
        find_scripts_directory,
        ConfigManager,
        ModifiedStateMixin,
        show_error,
        show_warning,
        show_info,
        ask_yes_no,
        ask_yes_no_cancel,
        open_file_dialog,
        save_file_dialog,
        select_directory_dialog,
        show_about_dialog,
        get_app_version,
        DescriptionListBox,  # NEW: Accessible listbox for descriptions with full text in screen readers
    )
    from shared.exif_utils import extract_exif_datetime
except ImportError as e:
    print(f"ERROR: Could not import shared utilities: {e}")
    print("This is a critical error. ImageDescriber cannot function without shared utilities.")
    sys.exit(1)

# Optional imports with graceful fallback
try:
    import ollama
except ImportError:
    ollama = None

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import openai
except ImportError:
    openai = None

# Import integrated tools (PromptEditor and Configure dialogs)
try:
    from prompt_editor_dialog import PromptEditorDialog
except ImportError:
    PromptEditorDialog = None

try:
    from configure_dialog import ConfigureDialog
except ImportError:
    ConfigureDialog = None

try:
    from download_dialog import DownloadSettingsDialog
except ImportError:
    DownloadSettingsDialog = None

# Phase 3: Import batch progress dialog
try:
    from batch_progress_dialog import BatchProgressDialog
except ImportError:
    BatchProgressDialog = None

# Import chat feature components
try:
    from chat_window_wx import ChatDialog, ChatWindow
except ImportError as e:
    import traceback
    # Write error to file for debugging frozen exe
    try:
        with open('chat_import_error.log', 'w') as f:
            f.write(f"CHAT IMPORT ERROR: {e}\n")
            f.write(traceback.format_exc())
    except:
        pass
    print(f"CHAT IMPORT ERROR: {e}")
    print(traceback.format_exc())
    ChatDialog = None
    ChatWindow = None

# Import Viewer components
try:
    from viewer_components import ViewerPanel
except ImportError:
    ViewerPanel = None

# Import shared metadata extraction module
try:
    if getattr(sys, 'frozen', False):
        scripts_dir = Path(sys.executable).parent / "scripts"
    else:
        scripts_dir = Path(__file__).parent.parent / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    from metadata_extractor import MetadataExtractor, NominatimGeocoder
except ImportError:
    MetadataExtractor = None
    NominatimGeocoder = None

# Versioning utilities
try:
    from versioning import log_build_banner, get_full_version
except Exception:
    log_build_banner = None
    get_full_version = None

# Import refactored AI provider modules
# In frozen mode, modules are at top level; in dev mode, use relative imports
if getattr(sys, 'frozen', False):
    # Frozen: import directly without package prefix
    from ai_providers import (
        AIProvider, OllamaProvider, OpenAIProvider, ClaudeProvider,
        get_available_providers, get_all_providers
    )
    from data_models import ImageDescription, ImageItem, ImageWorkspace, WORKSPACE_VERSION
    from workspace_manager import (
        get_default_workspaces_root, get_next_untitled_name, create_workspace_structure,
        is_untitled_workspace, get_workspace_files_directory, propose_workspace_name_from_url
    )
    from dialogs_wx import (
        DirectorySelectionDialog,
        ApiKeyDialog,
        ProcessingOptionsDialog,
        ImageDetailDialog,
        VideoExtractionDialog,
    )
    from workers_wx import (
        ProcessingWorker,
        BatchProcessingWorker,
        WorkflowProcessWorker,
        VideoProcessingWorker,
        HEICConversionWorker,
        EVT_PROGRESS_UPDATE,
        EVT_PROCESSING_COMPLETE,
        EVT_PROCESSING_FAILED,
        EVT_WORKFLOW_COMPLETE,
        EVT_WORKFLOW_FAILED,
        EVT_CONVERSION_COMPLETE,
        EVT_CONVERSION_FAILED,
    )
else:
    # Development: try relative imports first, fall back to absolute
    try:
        from .ai_providers import (
            AIProvider, OllamaProvider, OpenAIProvider, ClaudeProvider,
            get_available_providers, get_all_providers
        )
        from .data_models import ImageDescription, ImageItem, ImageWorkspace, WORKSPACE_VERSION
        from .workspace_manager import (
            get_default_workspaces_root, get_next_untitled_name, create_workspace_structure,
            is_untitled_workspace, get_workspace_files_directory, propose_workspace_name_from_url
        )
        from .dialogs_wx import (
            DirectorySelectionDialog,
            ApiKeyDialog,
            ProcessingOptionsDialog,
            ImageDetailDialog,
            VideoExtractionDialog,
        )
        from .workers_wx import (
            ProcessingWorker,
            BatchProcessingWorker,
            WorkflowProcessWorker,
            VideoProcessingWorker,
            HEICConversionWorker,
            EVT_PROGRESS_UPDATE,
            EVT_PROCESSING_COMPLETE,
            EVT_PROCESSING_FAILED,
            EVT_WORKFLOW_COMPLETE,
            EVT_WORKFLOW_FAILED,
            EVT_CONVERSION_COMPLETE,
            EVT_CONVERSION_FAILED,
        )
    except ImportError as e_rel:
        print(f"[DEBUG] Relative import failed, trying absolute: {e_rel}")
        from ai_providers import (
            AIProvider, OllamaProvider, OpenAIProvider, ClaudeProvider,
            get_available_providers, get_all_providers
        )
        from data_models import ImageDescription, ImageItem, ImageWorkspace, WORKSPACE_VERSION
        from workspace_manager import (
            get_default_workspaces_root, get_next_untitled_name, create_workspace_structure,
            is_untitled_workspace, get_workspace_files_directory, propose_workspace_name_from_url
        )
        from dialogs_wx import (
            DirectorySelectionDialog,
            ApiKeyDialog,
            ProcessingOptionsDialog,
            ImageDetailDialog,
            VideoExtractionDialog,
        )
        from workers_wx import (
            ProcessingWorker,
            BatchProcessingWorker,
            WorkflowProcessWorker,
            VideoProcessingWorker,
            HEICConversionWorker,
            EVT_PROGRESS_UPDATE,
            EVT_PROCESSING_COMPLETE,
            EVT_PROCESSING_FAILED,
            EVT_WORKFLOW_COMPLETE,
            EVT_WORKFLOW_FAILED,
            EVT_CONVERSION_COMPLETE,
            EVT_CONVERSION_FAILED,
        )

# Import provider capabilities
try:
    # Use the same project root resolution as above
    if getattr(sys, 'frozen', False):
        _models_path = Path(sys.executable).parent / 'models'
    else:
        _models_path = Path(__file__).parent.parent / 'models'
    
    if str(_models_path) not in sys.path:
        sys.path.insert(0, str(_models_path))
    
    from provider_configs import supports_prompts, supports_custom_prompts, get_provider_capabilities
    from model_options import get_all_options_for_provider, get_default_value
except ImportError:
    supports_prompts = lambda p: True
    supports_custom_prompts = lambda p: False
    get_provider_capabilities = lambda p: {}
    get_all_options_for_provider = lambda p: {}
    get_default_value = lambda p, o: None


# Custom events for thread communication
DescriptionCompleteEvent, EVT_DESCRIPTION_COMPLETE = wx.lib.newevent.NewEvent()
ProcessingProgressEvent, EVT_PROCESSING_PROGRESS = wx.lib.newevent.NewEvent()
ProcessingErrorEvent, EVT_PROCESSING_ERROR = wx.lib.newevent.NewEvent()


def format_image_metadata(metadata: dict) -> list:
    """Format image metadata (GPS, EXIF) for display
    
    Args:
        metadata: Dictionary containing datetime, location, camera, technical sections
        
    Returns:
        List of formatted metadata strings to display
    """
    if not metadata:
        return []
    
    lines = []
    
    # DateTime information
    if 'datetime_str' in metadata and metadata['datetime_str']:
        lines.append(f"Captured: {metadata['datetime_str']}")
    elif 'datetime' in metadata and metadata['datetime']:
        # Fallback to ISO format if formatted version not available
        lines.append(f"Date: {metadata['datetime']}")
    
    # GPS/Location information  
    if 'location' in metadata and metadata['location']:
        loc_info = metadata['location']
        
        # Show city/state first if available (like command line version)
        city = loc_info.get('city') or loc_info.get('town')
        state = loc_info.get('state')
        country = loc_info.get('country')
        
        if city and state:
            lines.append(f"Location: {city}, {state}")
        elif city and country:
            lines.append(f"Location: {city}, {country}")
        elif state:
            lines.append(f"Location: {state}")
        elif country:
            lines.append(f"Location: {country}")
        
        # Show GPS coordinates after location name
        if 'latitude' in loc_info and 'longitude' in loc_info:
            lat = loc_info['latitude']
            lon = loc_info['longitude']
            lines.append(f"GPS: {lat:.6f}, {lon:.6f}")
    
    # Camera information
    if 'camera' in metadata and metadata['camera']:
        cam_info = metadata['camera']
        if 'Make' in cam_info and 'Model' in cam_info:
            lines.append(f"Camera: {cam_info['Make']} {cam_info['Model']}")
        elif 'Model' in cam_info:
            lines.append(f"Camera: {cam_info['Model']}")
    
    return lines


# Logger instance - configuration is done in main() when --debug flag is used
logger = logging.getLogger(__name__)


class ImageDescriberFrame(wx.Frame, ModifiedStateMixin):
    """Main application window for ImageDescriber"""
    
    def __init__(self):
        wx.Frame.__init__(
            self,
            None,
            title="ImageDescriber - AI-Powered Image Description",
            size=(1400, 900)
        )
        ModifiedStateMixin.__init__(self)
        
        # Create Untitled workspace on startup
        untitled_name = get_next_untitled_name()
        workspace_file, workspace_data_dir = create_workspace_structure(untitled_name)
        
        # Application state
        self.workspace = ImageWorkspace(new_workspace=True)
        self.workspace.directory_path = str(workspace_data_dir)
        self.workspace.directory_paths = [str(workspace_data_dir)]
        self.current_directory = workspace_data_dir
        self.workspace_file = workspace_file
        self.processing_thread = None
        self.current_image_item = None
        self.current_filter = "all"  # View filter: all, described, undescribed
        self.show_image_previews = True  # View option: show/hide image preview panel
        self.processing_items = {}  # Track items being processed: {file_path: {provider, model}}
        self.batch_progress = None  # Track batch processing: {current: N, total: M, file_path: "..."}
        
        # Phase 3: Batch processing management
        self.batch_worker: Optional[BatchProcessingWorker] = None  # Store worker reference
        self.video_worker = None  # Store VideoProcessingWorker reference to prevent GC
        self.batch_progress_dialog: Optional[BatchProgressDialog] = None  # Progress dialog
        self.batch_start_time: Optional[float] = None  # For avg time calculation
        self.batch_processing_times: List[float] = []  # Track times per image
        
        # Batch video extraction state
        self._batch_video_extraction = False  # Flag for batch video extraction mode
        
        # AI Model caching (for faster dialog loading)
        self.cached_ollama_models = None  # Will be populated on first use or manual refresh
        
        # Supported image extensions
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic'}
        self.video_extensions = {'.mp4', '.mov', '.avi', '.mkv'}
        
        # Configuration
        self.load_config()
        
        # Setup UI
        self.init_ui()
        self.create_menu_bar()
        self.create_status_bar()
        
        # Set initial focus to image list for keyboard navigation
        wx.CallAfter(self.image_list.SetFocus)
        # TODO: Tab order needs different approach (controls in different panels)
        
        # Bind events
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(EVT_DESCRIPTION_COMPLETE, self.on_description_complete)
        self.Bind(EVT_PROCESSING_PROGRESS, self.on_processing_progress)
        self.Bind(EVT_PROCESSING_ERROR, self.on_processing_error)
        
        # Bind worker events if available
        if EVT_PROGRESS_UPDATE:
            self.Bind(EVT_PROGRESS_UPDATE, self.on_worker_progress)
        if EVT_PROCESSING_COMPLETE:
            self.Bind(EVT_PROCESSING_COMPLETE, self.on_worker_complete)
        if EVT_PROCESSING_FAILED:
            self.Bind(EVT_PROCESSING_FAILED, self.on_worker_failed)
        if EVT_WORKFLOW_COMPLETE:
            self.Bind(EVT_WORKFLOW_COMPLETE, self.on_workflow_complete)
        if EVT_WORKFLOW_FAILED:
            self.Bind(EVT_WORKFLOW_FAILED, self.on_workflow_failed)
        if EVT_CONVERSION_COMPLETE:
            self.Bind(EVT_CONVERSION_COMPLETE, self.on_conversion_complete)
        if EVT_CONVERSION_FAILED:
            self.Bind(EVT_CONVERSION_FAILED, self.on_conversion_failed)
        
        # Bind keyboard events for single-key shortcuts (matching Qt6 behavior)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key_press)
        
        # Update window title
        self.update_window_title("ImageDescriber", untitled_name)
        
        # Save initial workspace structure
        wx.CallAfter(self.save_workspace, self.workspace_file)
        
        # Log startup banner
        if log_build_banner:
            try:
                log_build_banner()
            except Exception:
                pass
        
        # Cache AI models on startup for faster dialog opening
        wx.CallAfter(self.refresh_ai_models_silent)
    
    # Note: update_window_title() is now provided by ModifiedStateMixin
    # It automatically handles the modified state indicator (*)
    # TODO: Implement proper tab order - requires controls to be siblings or NavigationEnabled
    
    def update_window_title(self, app_name="ImageDescriber", document_name=""):
        """Override to show processing status in title bar"""
        # Call parent for basic title formatting
        super().update_window_title(app_name, document_name)
        
        # Add processing status if items are being processed
        if self.processing_items:
            num_processing = len(self.processing_items)
            current_title = self.GetTitle()
            if num_processing == 1:
                self.SetTitle(f"{current_title} - Processing...")
            else:
                self.SetTitle(f"{current_title} - Processing {num_processing} items...")
    
    def load_config(self):
        """Load application configuration"""
        try:
            self.config_file = find_config_file('image_describer_config.json')
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load config: {e}")
            self.config = {
                'default_provider': 'ollama',
                'default_model': 'moondream',
                'default_prompt_style': 'narrative'
            }
    
    def get_api_key_for_provider(self, provider: str) -> str:
        """Get API key for a specific provider from config"""
        api_keys = self.config.get('api_keys', {})
        # Try case-insensitive lookup
        for key in [provider, provider.capitalize(), provider.upper(), provider.lower()]:
            if key in api_keys and api_keys[key]:
                return api_keys[key]
        # Check for openai/OpenAI/OPENAI
        if provider.lower() == 'openai':
            for key in ['OpenAI', 'openai', 'OPENAI']:
                if key in api_keys and api_keys[key]:
                    return api_keys[key]
        # Check for claude/Claude/CLAUDE
        elif provider.lower() == 'claude':
            for key in ['Claude', 'claude', 'CLAUDE', 'Anthropic', 'anthropic']:
                if key in api_keys and api_keys[key]:
                    return api_keys[key]
        return None

    def get_video_metadata(self, video_path: str) -> Optional[dict]:
        """Extract metadata from video file using cv2.
        
        Returns dict with {fps, duration, total_frames} or None if extraction fails.
        """
        try:
            import cv2
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return None
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0
            
            cap.release()
            
            return {
                'fps': fps,
                'duration': duration,
                'total_frames': total_frames
            }
        except Exception:
            # Silently handle missing cv2, corrupted videos, network issues
            return None
    
    def get_workspace_directory(self) -> Path:
        """Get the workspace data directory for extracted frames, downloaded images, etc.
        
        Returns the directory structure:
        ~/Documents/WorkSpaceFiles/{workspace_name}/
        """
        if self.workspace_file:
            # Use new workspace structure in WorkSpaceFiles
            workspace_dir = get_workspace_files_directory(Path(self.workspace_file))
        else:
            # Fallback (shouldn't happen with new Untitled workspace pattern)
            from workspace_manager import get_workspace_files_root
            workspace_dir = get_workspace_files_root() / "untitled_workspace"
        
        workspace_dir.mkdir(parents=True, exist_ok=True)
        return workspace_dir
    
    def _extract_video_frames_sync(self, video_path: str, extraction_config: dict) -> tuple:
        """Extract frames from video synchronously (for auto-extraction in Process All).
        
        Args:
            video_path: Path to video file
            extraction_config: Dict with extraction settings
        
        Returns:
            tuple: (list of extracted frame paths, video metadata dict)
        """
        try:
            import cv2
        except ImportError:
            raise Exception("OpenCV (cv2) not available. Please install opencv-python.")
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise Exception(f"Could not open video file: {video_path}")
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0
        
        video_metadata = {
            'fps': fps,
            'total_frames': frame_count,
            'duration': duration
        }
        
        # Create output directory in workspace (NOT in source directory)
        video_path_obj = Path(video_path)
        workspace_dir = self.get_workspace_directory()
        extracted_frames_dir = workspace_dir / "extracted_frames"
        video_dir = extracted_frames_dir / f"{video_path_obj.stem}"
        video_dir.mkdir(parents=True, exist_ok=True)
        
        # Extract based on mode (time_interval or scene_change)
        extraction_mode = extraction_config.get("extraction_mode", "time_interval")
        print(f"Video extraction mode: {extraction_mode}")
        print(f"Video: {frame_count} total frames, {duration:.1f}s, fps={fps:.2f}")
        
        if extraction_mode == "scene_change":
            extracted_paths = self._extract_by_scene_detection(cap, fps, video_dir, extraction_config, video_path_obj)
        else:
            extracted_paths = self._extract_by_time_interval(cap, fps, video_dir, extraction_config, video_path_obj)
        
        cap.release()
        return extracted_paths, video_metadata
    
    def _extract_by_time_interval(self, cap, fps: float, video_dir: Path, extraction_config: dict, video_path_obj: Path) -> list:
        """Extract frames at time intervals"""
        import cv2
        
        interval_seconds = extraction_config.get("time_interval_seconds", 5)
        start_time = extraction_config.get("start_time_seconds", 0)
        end_time = extraction_config.get("end_time_seconds")
        
        total_frames_in_video = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_interval = max(1, int(fps * interval_seconds))  # Minimum 1 frame
        start_frame = int(fps * start_time)
        
        # Calculate end point (either user-specified or video end)
        if end_time:
            end_frame = int(fps * end_time)
        else:
            end_frame = total_frames_in_video
        
        # EMERGENCY: Safety limit - can't extract more frames than exist in video!
        safety_limit = total_frames_in_video + 10  # Add small buffer for edge cases
        
        print(f"\n{'='*60}")
        print(f"EXTRACTION DEBUG: {video_path_obj.stem}")
        print(f"Video has {total_frames_in_video} total frames, {fps:.2f} fps")
        print(f"Time interval extraction: {interval_seconds}s = {frame_interval} frames")
        print(f"Frame range: {start_frame} to {end_frame}")
        print(f"Safety limit: {safety_limit} extractions max")
        print(f"{'='*60}\n")
        
        # Write to log file too
        log_file = video_dir / "_extraction_debug.log"
        with open(log_file, 'w') as f:
            f.write(f"Video: {video_path_obj.name}\n")
            f.write(f"Total frames in video: {total_frames_in_video}\n")
            f.write(f"FPS: {fps:.2f}\n")
            f.write(f"Interval: {interval_seconds}s = {frame_interval} frames\n")
            f.write(f"Start frame: {start_frame}\n")
            f.write(f"End frame: {end_frame}\n")
            f.write(f"\nExtraction log:\n")
        
        extracted_paths = []
        frame_num = start_frame
        extract_count = 0
        
        # Use CLI logic: check frame position in while condition
        while frame_num < end_frame:
            # EMERGENCY STOP (shouldn't be needed now, but keep as safety)
            if extract_count >= safety_limit:
                error_msg = f"SAFETY STOP: Extracted {extract_count} frames from {total_frames_in_video}-frame video!"
                print(f"\n*** {error_msg} ***\n")
                with open(log_file, 'a') as f:
                    f.write(f"\n*** {error_msg} ***\n")
                break
            
            # Log every extraction
            with open(log_file, 'a') as f:
                f.write(f"  [{extract_count}] Seeking to frame {frame_num}...")
            
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ret, frame = cap.read()
            
            if not ret:
                with open(log_file, 'a') as f:
                    f.write(f" FAILED (ret={ret})\n")
                print(f"Frame {frame_num} read failed, stopping extraction")
                break
            
            # Save frame
            frame_filename = f"{video_path_obj.stem}_frame_{extract_count:05d}.jpg"
            frame_path = video_dir / frame_filename
            cv2.imwrite(str(frame_path), frame)
            extracted_paths.append(str(frame_path))
            
            with open(log_file, 'a') as f:
                f.write(f" OK, saved as {frame_filename}\n")
            
            extract_count += 1
            old_frame_num = frame_num
            frame_num += frame_interval
            
            if extract_count % 10 == 0:
                print(f"Extracted {extract_count} frames (frame {old_frame_num} -> {frame_num})")
        
        print(f"\nExtraction complete: {extract_count} frames extracted")
        print(f"Debug log written to: {log_file}\n")
        
        return extracted_paths
    
    def _extract_by_scene_detection(self, cap, fps: float, video_dir: Path, extraction_config: dict, video_path_obj: Path) -> list:
        """Extract frames based on scene changes"""
        import cv2
        
        threshold = extraction_config.get("scene_change_threshold", 30.0) / 100.0
        min_duration = extraction_config.get("min_scene_duration_seconds", 1.0)
        
        print(f"Scene detection: threshold={threshold*100:.1f}%, min_duration={min_duration}s")
        
        extracted_paths = []
        prev_frame = None
        last_extract_frame = -1
        min_frame_gap = int(fps * min_duration)
        frame_num = 0
        extract_count = 0
        
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
                    
                    # Save frame
                    frame_filename = f"{video_path_obj.stem}_scene_{extract_count:04d}.jpg"
                    frame_path = video_dir / frame_filename
                    cv2.imwrite(str(frame_path), frame)
                    extracted_paths.append(str(frame_path))
                    
                    last_extract_frame = frame_num
                    extract_count += 1
            
            prev_frame = frame.copy()
            frame_num += 1
        
        return extracted_paths
    
    def init_ui(self):
        """Initialize the user interface with dual mode support"""
        self.current_mode = "editor" # 'editor' or 'viewer'

        # Main content container
        self.main_content_panel = wx.Panel(self)
        self.content_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # --- EDITOR MODE UI ---
        self.editor_container = wx.Panel(self.main_content_panel)
        self.editor_container.SetCanFocus(False)
        editor_sizer = wx.BoxSizer(wx.VERTICAL)

        # Create splitter for resizable panels
        splitter = wx.SplitterWindow(self.editor_container, style=wx.SP_LIVE_UPDATE)
        splitter.SetCanFocus(False)  # Keep focus on child controls for tab navigation
        
        # Left panel - Image list
        left_panel = self.create_image_list_panel(splitter)
        
        # Right panel - Description editor
        right_panel = self.create_description_panel(splitter)
        
        # Set up splitter
        splitter.SplitVertically(left_panel, right_panel, 400)
        splitter.SetMinimumPaneSize(200)
        
        editor_sizer.Add(splitter, 1, wx.EXPAND | wx.ALL, 5)
        self.editor_container.SetSizer(editor_sizer)
        
        # --- VIEWER MODE UI ---
        self.viewer_container = wx.Panel(self.main_content_panel)
        self.viewer_container.SetCanFocus(False)
        viewer_sizer = wx.BoxSizer(wx.VERTICAL)
        
        if ViewerPanel:
            self.viewer_panel = ViewerPanel(self.viewer_container, main_window=self)
            viewer_sizer.Add(self.viewer_panel, 1, wx.EXPAND)
        else:
            self.viewer_panel = None
            viewer_sizer.Add(wx.StaticText(self.viewer_container, label="Viewer component missing or failed to load"), 0, wx.ALL, 20)
            
        self.viewer_container.SetSizer(viewer_sizer)
        
        # Add both to content sizer mechanism
        self.content_sizer.Add(self.editor_container, 1, wx.EXPAND)
        self.content_sizer.Add(self.viewer_container, 1, wx.EXPAND)
        
        # Default to editor mode (Viewer hidden)
        self.viewer_container.Hide()
        self.content_sizer.Layout()
        
        self.main_content_panel.SetSizer(self.content_sizer)
        
    def switch_mode(self, mode, data=None):
        """Switch between Editor and Viewer modes.
        :param mode: 'editor' or 'viewer'
        :param data: Optional data to load (Path for directory, or just use current workspace)
        """
        if mode == self.current_mode and data is None:
            # If checking same mode without new data, do nothing
            return
            
        self.current_mode = mode
        
        if mode == 'viewer':
            self.editor_container.Hide()
            self.viewer_container.Show()
            
            if self.viewer_panel:
                if isinstance(data, Path):
                    # Load specific directory
                    self.viewer_panel.load_from_directory(data)
                elif data is not None:
                     # Attempt to load whatever object was passed if applicable (e.g. Workspace)
                    self.viewer_panel.load_from_workspace(data)
                elif self.workspace:
                    # Default: load current workspace
                    self.viewer_panel.load_from_workspace(self.workspace)
                else:
                    # Just show empty viewer
                    pass
                
            # Update menu checkmarks (if we stored references)
            # (Menu items are referenced in bind lambda, but we didn't store them as attributes
            #  but we can iterate or just rely on radio behavior if UI updates correctly)
                
        else: # editor
            self.viewer_container.Hide()
            self.editor_container.Show()
        
        self.main_content_panel.Layout()
    
    def create_image_list_panel(self, parent):
        """Create the left panel with image list"""
        panel = wx.Panel(parent)
        panel.SetCanFocus(False)  # Avoid panel stealing focus
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Label
        label = wx.StaticText(panel, label="Images:")
        sizer.Add(label, 0, wx.ALL, 5)
        
        # Image list (using ListBox for accessibility - single tab stop)
        self.image_list = wx.ListBox(panel, name="Images in workspace", style=wx.LB_SINGLE | wx.LB_NEEDED_SB)
        self.image_list.Bind(wx.EVT_LISTBOX, self.on_image_selected)
        self.image_list.Bind(wx.EVT_CHAR_HOOK, self.on_image_list_key)
        sizer.Add(self.image_list, 1, wx.EXPAND | wx.ALL, 5)
        
        panel.SetSizer(sizer)
        return panel
    
    def create_description_panel(self, parent):
        """
        Create the right panel with image preview, descriptions list, and editor.
        
        Layout:
        - TOP: Image preview panel (thumbnail of selected image)
        - MIDDLE: Descriptions ListBox (all descriptions for current image)
        - BOTTOM: Description editor TextCtrl (for editing selected description)
        """
        panel = wx.Panel(parent)
        panel.SetCanFocus(False)  # Avoid panel stealing focus
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Image info label
        self.image_info_label = wx.StaticText(panel, label="No image selected")
        sizer.Add(self.image_info_label, 0, wx.ALL, 5)
        
        # ===== TOP SECTION: IMAGE PREVIEW =====
        
        self.image_preview_label = wx.StaticText(panel, label="Image Preview:")
        sizer.Add(self.image_preview_label, 0, wx.ALL, 5)
        
        # Preview panel with fixed size for thumbnail display
        self.image_preview_panel = wx.Panel(panel, size=(250, 250))
        self.image_preview_panel.SetBackgroundColour(wx.Colour(200, 200, 200))
        self.image_preview_panel.SetName("Image preview panel")
        
        # Store bitmap for painting and initialize to None
        self.image_preview_bitmap = None
        
        # Bind paint event for displaying image
        self.image_preview_panel.Bind(wx.EVT_PAINT, self.on_paint_preview)
        
        sizer.Add(self.image_preview_panel, 0, wx.ALL | wx.EXPAND, 5)
        
        # ===== MIDDLE SECTION: DESCRIPTIONS LIST =====
        
        # Label for descriptions list
        desc_list_label = wx.StaticText(panel, label="Descriptions for this image:")
        sizer.Add(desc_list_label, 0, wx.ALL, 5)
        
        # Descriptions list using accessible pattern
        # Shows truncated text visually, full text to screen readers
        self.desc_list = DescriptionListBox(
            panel, 
            name="Description list for current image",
            style=wx.LB_SINGLE | wx.LB_NEEDED_SB
        )
        self.desc_list.Bind(wx.EVT_LISTBOX, self.on_description_selected)
        self.desc_list.Bind(wx.EVT_CHAR_HOOK, self.on_desc_list_key)
        sizer.Add(self.desc_list, 1, wx.EXPAND | wx.ALL, 5)
        
        # ===== BOTTOM SECTION: EDITOR =====
        
        # Label for editor
        editor_label = wx.StaticText(panel, label="Edit selected description:")
        sizer.Add(editor_label, 0, wx.ALL, 5)
        
        # Description text editor
        self.description_text = wx.TextCtrl(
            panel,
            name="Image description editor",
            style=wx.TE_MULTILINE | wx.TE_WORDWRAP | wx.TE_RICH2
        )
        self.description_text.Bind(wx.EVT_CHAR_HOOK, self.on_description_text_key)
        sizer.Add(self.description_text, 1, wx.EXPAND | wx.ALL, 5)
        
        # Buttons
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.process_btn = wx.Button(panel, label="Generate Description")
        self.process_btn.Bind(wx.EVT_BUTTON, self.on_process_single)
        self.process_btn.Enable(False)
        button_sizer.Add(self.process_btn, 0, wx.ALL, 2)
        
        self.save_desc_btn = wx.Button(panel, label="Save Description")
        self.save_desc_btn.Bind(wx.EVT_BUTTON, self.on_save_description)
        self.save_desc_btn.Enable(False)
        button_sizer.Add(self.save_desc_btn, 0, wx.ALL, 2)
        
        sizer.Add(button_sizer, 0, wx.ALL, 5)
        
        panel.SetSizer(sizer)
        return panel
    
    def create_menu_bar(self):
        """Create the application menu bar"""
        menubar = wx.MenuBar()
        
        # File menu
        file_menu = wx.Menu()
        
        new_item = file_menu.Append(wx.ID_NEW, "&New Workspace\tCtrl+N")
        self.Bind(wx.EVT_MENU, self.on_new_workspace, new_item)
        
        open_item = file_menu.Append(wx.ID_OPEN, "&Open Workspace\tCtrl+O")
        self.Bind(wx.EVT_MENU, self.on_open_workspace, open_item)
        
        save_item = file_menu.Append(wx.ID_SAVE, "&Save Workspace\tCtrl+S")
        self.Bind(wx.EVT_MENU, self.on_save_workspace, save_item)
        
        save_as_item = file_menu.Append(wx.ID_SAVEAS, "Save Workspace &As...")
        self.Bind(wx.EVT_MENU, self.on_save_workspace_as, save_as_item)
        
        file_menu.AppendSeparator()
        
        load_dir_item = file_menu.Append(wx.ID_ANY, "&Load Directory\tCtrl+L")
        self.Bind(wx.EVT_MENU, self.on_load_directory, load_dir_item)
        
        load_url_item = file_menu.Append(wx.ID_ANY, "Load Images From &URL...\tCtrl+U")
        self.Bind(wx.EVT_MENU, self.on_load_from_url, load_url_item)

        import_workflow_item = file_menu.Append(wx.ID_ANY, "&Import Workflow (to Workspace)...")
        self.Bind(wx.EVT_MENU, self.on_import_workflow, import_workflow_item)
        
        export_descriptions_item = file_menu.Append(wx.ID_ANY, "&Export Descriptions...")
        self.Bind(wx.EVT_MENU, self.on_export_descriptions, export_descriptions_item)
        
        open_workflow_result = file_menu.Append(wx.ID_ANY, "Open &Workflow Result (Viewer Mode)...")
        self.Bind(wx.EVT_MENU, self.on_open_workflow_result, open_workflow_result)
        
        file_menu.AppendSeparator()
        
        exit_item = file_menu.Append(wx.ID_EXIT, "E&xit\tCtrl+Q")
        self.Bind(wx.EVT_MENU, self.on_close, exit_item)
        
        menubar.Append(file_menu, "&File")
        
        # Edit menu
        edit_menu = wx.Menu()
        
        cut_item = edit_menu.Append(wx.ID_CUT, "&Cut\tCtrl+X")
        self.Bind(wx.EVT_MENU, self.on_cut, cut_item)
        
        copy_item = edit_menu.Append(wx.ID_COPY, "&Copy\tCtrl+C")
        self.Bind(wx.EVT_MENU, self.on_copy, copy_item)
        
        paste_item = edit_menu.Append(wx.ID_PASTE, "&Paste\tCtrl+V")
        self.Bind(wx.EVT_MENU, self.on_paste, paste_item)
        
        edit_menu.AppendSeparator()
        
        select_all_item = edit_menu.Append(wx.ID_SELECTALL, "Select &All\tCtrl+A")
        self.Bind(wx.EVT_MENU, self.on_select_all, select_all_item)
        
        menubar.Append(edit_menu, "&Edit")
        
        # Process menu
        process_menu = wx.Menu()
        
        process_single_item = process_menu.Append(wx.ID_ANY, "Process &Current Image\tP")
        self.Bind(wx.EVT_MENU, self.on_process_single, process_single_item)
        
        process_menu.AppendSeparator()
        
        # Phase 5: Split Process All into two options
        process_undesc_item = process_menu.Append(
            wx.ID_ANY,
            "Process &Undescribed Images",
            "Process only images without descriptions (safe default)"
        )
        self.Bind(wx.EVT_MENU, lambda e: self.on_process_all(e, skip_existing=True), process_undesc_item)
        
        redescribe_all_item = process_menu.Append(
            wx.ID_ANY,
            "&Redescribe All Images",
            "Process ALL images again (adds new descriptions)"
        )
        self.Bind(wx.EVT_MENU, lambda e: self.on_process_all(e, skip_existing=False), redescribe_all_item)
        
        process_menu.AppendSeparator()
        
        # Show Batch Progress menu item (enabled only during batch processing)
        self.show_batch_progress_item = process_menu.Append(
            wx.ID_ANY,
            "Show &Batch Progress",
            "Show batch processing progress dialog"
        )
        self.show_batch_progress_item.Enable(False)  # Disabled by default
        self.Bind(wx.EVT_MENU, self.on_show_batch_progress, self.show_batch_progress_item)
        
        process_menu.AppendSeparator()
        
        refresh_models_item = process_menu.Append(wx.ID_ANY, "Refresh AI &Models")
        self.Bind(wx.EVT_MENU, self.on_refresh_ai_models, refresh_models_item)
        
        process_menu.AppendSeparator()
        
        chat_item = process_menu.Append(wx.ID_ANY, "&Chat with AI Model\tC")
        self.Bind(wx.EVT_MENU, self.on_chat, chat_item)
        
        process_menu.AppendSeparator()
        
        convert_heic_item = process_menu.Append(wx.ID_ANY, "Convert &HEIC Files...")
        self.Bind(wx.EVT_MENU, self.on_convert_heic, convert_heic_item)
        
        extract_video_item = process_menu.Append(wx.ID_ANY, "Extract &Video Frames...")
        self.Bind(wx.EVT_MENU, self.on_extract_video, extract_video_item)
        
        process_menu.AppendSeparator()
        
        rename_item = process_menu.Append(wx.ID_ANY, "&Rename Item\tR")
        self.Bind(wx.EVT_MENU, self.on_rename_item, rename_item)
        
        menubar.Append(process_menu, "&Process")
        
        # Descriptions menu
        desc_menu = wx.Menu()
        
        add_manual_item = desc_menu.Append(wx.ID_ANY, "Add &Manual Description\tM")
        self.Bind(wx.EVT_MENU, self.on_add_manual_description, add_manual_item)
        
        followup_item = desc_menu.Append(wx.ID_ANY, "Ask &Followup Question\tF")
        self.Bind(wx.EVT_MENU, self.on_followup_question, followup_item)
        
        desc_menu.AppendSeparator()
        
        edit_desc_item = desc_menu.Append(wx.ID_ANY, "&Edit Description...")
        self.Bind(wx.EVT_MENU, self.on_edit_description, edit_desc_item)
        
        delete_desc_item = desc_menu.Append(wx.ID_ANY, "&Delete Description")
        self.Bind(wx.EVT_MENU, self.on_delete_description, delete_desc_item)
        
        desc_menu.AppendSeparator()
        
        copy_desc_item = desc_menu.Append(wx.ID_ANY, "&Copy Description")
        self.Bind(wx.EVT_MENU, self.on_copy_description, copy_desc_item)
        
        copy_path_item = desc_menu.Append(wx.ID_ANY, "Copy Image &Path")
        self.Bind(wx.EVT_MENU, self.on_copy_image_path, copy_path_item)
        
        desc_menu.AppendSeparator()
        
        show_all_item = desc_menu.Append(wx.ID_ANY, "&Show All Descriptions...")
        self.Bind(wx.EVT_MENU, self.on_show_all_descriptions, show_all_item)
        
        menubar.Append(desc_menu, "&Descriptions")
        
        # View menu
        view_menu = wx.Menu()
        
        # Mode switching
        mode_menu = wx.Menu()
        editor_mode_item = mode_menu.AppendRadioItem(wx.ID_ANY, "Editor Mode")
        viewer_mode_item = mode_menu.AppendRadioItem(wx.ID_ANY, "Viewer Mode")
        
        self.Bind(wx.EVT_MENU, lambda e: self.switch_mode('editor'), editor_mode_item)
        self.Bind(wx.EVT_MENU, lambda e: self.switch_mode('viewer', self.workspace if self.workspace else None), viewer_mode_item)
        
        view_menu.AppendSubMenu(mode_menu, "Application &Mode")
        view_menu.AppendSeparator()

        filter_all_item = view_menu.AppendRadioItem(wx.ID_ANY, "Filter: &All Items\tF5")
        self.Bind(wx.EVT_MENU, lambda e: self.on_set_filter("all"), filter_all_item)
        
        filter_desc_item = view_menu.AppendRadioItem(wx.ID_ANY, "Filter: &Described Only")
        self.Bind(wx.EVT_MENU, lambda e: self.on_set_filter("described"), filter_desc_item)
        
        filter_undesc_item = view_menu.AppendRadioItem(wx.ID_ANY, "Filter: &Undescribed Only")
        self.Bind(wx.EVT_MENU, lambda e: self.on_set_filter("undescribed"), filter_undesc_item)
        
        filter_videos_item = view_menu.AppendRadioItem(wx.ID_ANY, "Filter: &Videos Only")
        self.Bind(wx.EVT_MENU, lambda e: self.on_set_filter("videos"), filter_videos_item)
        
        filter_all_item.Check(True)  # Default to all items
        
        view_menu.AppendSeparator()
        
        # Image preview toggle
        self.show_preview_item = view_menu.AppendCheckItem(wx.ID_ANY, "Show &Image Previews")
        self.show_preview_item.Check(True)  # Default: show previews
        self.Bind(wx.EVT_MENU, self.on_toggle_image_previews, self.show_preview_item)
        
        menubar.Append(view_menu, "&View")
        
        # Tools menu
        tools_menu = wx.Menu()
        
        edit_prompts_item = tools_menu.Append(wx.ID_ANY, "Edit &Prompts...\tCtrl+P")
        self.Bind(wx.EVT_MENU, self.on_edit_prompts, edit_prompts_item)
        
        configure_item = tools_menu.Append(wx.ID_ANY, "&Configure Settings...\tCtrl+Shift+C")
        self.Bind(wx.EVT_MENU, self.on_configure_settings, configure_item)
        
        tools_menu.AppendSeparator()
        
        export_config_item = tools_menu.Append(wx.ID_ANY, "E&xport Configuration...")
        self.Bind(wx.EVT_MENU, self.on_export_configuration, export_config_item)
        
        import_config_item = tools_menu.Append(wx.ID_ANY, "&Import Configuration...")
        self.Bind(wx.EVT_MENU, self.on_import_configuration, import_config_item)
        
        menubar.Append(tools_menu, "&Tools")
        
        # Help menu
        help_menu = wx.Menu()
        
        user_guide_item = help_menu.Append(wx.ID_ANY, "&User Guide...")
        self.Bind(wx.EVT_MENU, self.on_user_guide, user_guide_item)
        
        help_menu.AppendSeparator()
        
        about_item = help_menu.Append(wx.ID_ABOUT, "&About")
        self.Bind(wx.EVT_MENU, self.on_about, about_item)
        
        menubar.Append(help_menu, "&Help")
        
        self.SetMenuBar(menubar)
    
    def create_status_bar(self):
        """Create the status bar"""
        self.statusbar = self.CreateStatusBar(2)
        self.statusbar.SetStatusWidths([-3, -1])
        self.SetStatusText("Ready", 0)
        self.SetStatusText("No workspace", 1)
    
    # Event handlers (stubs for now)
    
    def on_image_selected(self, event):
        """Handle image selection"""
        selection = self.image_list.GetSelection()
        if selection != wx.NOT_FOUND:
            file_path = self.image_list.GetClientData(selection)
            if file_path and file_path in self.workspace.items:
                self.current_image_item = self.workspace.items[file_path]
                self.display_image_info(self.current_image_item)
                # Load preview image
                self.load_preview_image(file_path)
                self.process_btn.Enable(True)
                self.save_desc_btn.Enable(True)
        else:
            # No selection - clear current item and disable buttons
            self.current_image_item = None
            self.image_preview_bitmap = None
            self.image_preview_panel.SetBackgroundColour(wx.Colour(200, 200, 200))
            self.image_preview_panel.Refresh()
            self.process_btn.Enable(False)
            self.save_desc_btn.Enable(False)

    # Explicit tab order: image_list -> desc_list -> description_text
    def on_image_list_key(self, event):
        if event.GetKeyCode() == wx.WXK_TAB and not event.ShiftDown():
            if self.desc_list:
                self.desc_list.SetFocus()
            return
        event.Skip()

    def on_desc_list_key(self, event):
        if event.GetKeyCode() == wx.WXK_TAB:
            if event.ShiftDown():
                if self.image_list:
                    self.image_list.SetFocus()
            else:
                if self.description_text:
                    self.description_text.SetFocus()
            return
        event.Skip()

    def on_description_text_key(self, event):
        if event.GetKeyCode() == wx.WXK_TAB and event.ShiftDown():
            if self.desc_list:
                self.desc_list.SetFocus()
            return
        event.Skip()
    
    def display_image_info(self, image_item: ImageItem):
        """
        Display information about selected image.
        
        Updates:
        1. Image info label with filename and description count
        2. Descriptions list with all descriptions for this image
        3. Editor with the first (or selected) description text
        """
        file_path = Path(image_item.file_path)
        
        # Update info label
        desc_count = len(image_item.descriptions)
        info = f"Selected: {file_path.name}"
        if desc_count > 0:
            info += f" ({desc_count} description{'s' if desc_count != 1 else ''})"
        
        # Add video metadata for videos
        if image_item.item_type == "video":
            metadata_parts = []
            if hasattr(image_item, 'video_metadata'):
                meta = image_item.video_metadata
                if meta.get('duration'):
                    duration_mins = int(meta['duration'] // 60)
                    duration_secs = int(meta['duration'] % 60)
                    metadata_parts.append(f"{duration_mins}m {duration_secs}s")
                if meta.get('fps'):
                    metadata_parts.append(f"{meta['fps']:.1f} fps")
                if meta.get('total_frames'):
                    metadata_parts.append(f"{meta['total_frames']} frames")
            if hasattr(image_item, 'extracted_frames') and image_item.extracted_frames:
                metadata_parts.append(f"{len(image_item.extracted_frames)} extracted")
            if metadata_parts:
                info += f"\n{' • '.join(metadata_parts)}"
        
        # Phase 6: Display error message if failed
        if hasattr(image_item, 'processing_state') and image_item.processing_state == "failed":
            if hasattr(image_item, 'processing_error') and image_item.processing_error:
                info += f"\n\n⚠️ Processing Failed: {image_item.processing_error}"
        
        self.image_info_label.SetLabel(info)
        
        # Populate descriptions list with accessible pattern
        if image_item.descriptions:
            # Build description list data with full text + metadata appended
            desc_data = []
            for desc in image_item.descriptions:
                # Format description with metadata appended for screen readers
                full_text = desc.text
                
                # Append metadata at the end (provider, model, prompt)
                metadata_lines = []
                metadata_lines.append("\n\n---")
                if desc.provider:
                    metadata_lines.append(f"Provider: {desc.provider}")
                if desc.model:
                    metadata_lines.append(f"Model: {desc.model}")
                if desc.prompt_style:
                    # If custom prompt was used, show 'custom' instead of base style
                    if desc.custom_prompt:
                        prompt_display = "custom"
                    else:
                        prompt_display = desc.prompt_style
                    metadata_lines.append(f"Prompt: {prompt_display}")
                if desc.created:
                    created_date = desc.created.split('T')[0] if 'T' in desc.created else desc.created
                    metadata_lines.append(f"Created: {created_date}")
                
                # Add download source info if available
                if hasattr(image_item, 'download_url') and image_item.download_url:
                    metadata_lines.append("\n--- Download Source ---")
                    metadata_lines.append(f"URL: {image_item.download_url}")
                    if hasattr(image_item, 'download_timestamp') and image_item.download_timestamp:
                        download_date = image_item.download_timestamp.split('T')[0] if 'T' in image_item.download_timestamp else image_item.download_timestamp
                        metadata_lines.append(f"Downloaded: {download_date}")
                
                # Add image metadata (GPS, EXIF, etc.) if available
                if desc.metadata:
                    image_metadata_lines = format_image_metadata(desc.metadata)
                    if image_metadata_lines:
                        metadata_lines.append("\n--- Image Info ---")
                        metadata_lines.extend(image_metadata_lines)
                
                full_text_with_metadata = full_text + "\n".join(metadata_lines)
                
                # Create dict with full description + metadata for accessibility
                entry = {
                    'description': full_text_with_metadata,  # Full text with metadata for screen readers
                    'model': desc.model,
                    'prompt_style': desc.prompt_style,
                    'created': desc.created,
                    'provider': desc.provider
                }
                desc_data.append(entry)
            
            # Load into accessible listbox (truncates visually, full text to screen readers)
            self.desc_list.LoadDescriptions(desc_data)
            
            # Show the first description in editor with metadata
            first_desc = image_item.descriptions[0]
            first_text = first_desc.text
            
            # Append metadata to first description for editor display
            metadata_lines = []
            metadata_lines.append("\n\n---")
            if first_desc.provider:
                metadata_lines.append(f"Provider: {first_desc.provider}")
            if first_desc.model:
                metadata_lines.append(f"Model: {first_desc.model}")
            if first_desc.prompt_style:
                if first_desc.custom_prompt:
                    prompt_display = "custom"
                else:
                    prompt_display = first_desc.prompt_style
                metadata_lines.append(f"Prompt: {prompt_display}")
            if first_desc.created:
                created_date = first_desc.created.split('T')[0] if 'T' in first_desc.created else first_desc.created
                metadata_lines.append(f"Created: {created_date}")
            
            # Add download source info if available
            if hasattr(image_item, 'download_url') and image_item.download_url:
                metadata_lines.append("\n--- Download Source ---")
                metadata_lines.append(f"URL: {image_item.download_url}")
                if hasattr(image_item, 'download_timestamp') and image_item.download_timestamp:
                    download_date = image_item.download_timestamp.split('T')[0] if 'T' in image_item.download_timestamp else image_item.download_timestamp
                    metadata_lines.append(f"Downloaded: {download_date}")
            
            # Add image metadata (GPS, EXIF, etc.) if available
            if first_desc.metadata:
                image_metadata_lines = format_image_metadata(first_desc.metadata)
                if image_metadata_lines:
                    metadata_lines.append("\n--- Image Info ---")
                    metadata_lines.extend(image_metadata_lines)
            
            first_text_with_metadata = first_text + "\n".join(metadata_lines)
            self.description_text.SetValue(first_text_with_metadata)
            
            # Enable save button
            self.save_desc_btn.Enable(True)
        else:
            # No descriptions yet
            self.desc_list.Clear()
            
            # For videos, show metadata in description area for accessibility
            if image_item.item_type == "video":
                metadata_text = "Video Metadata\n\n"
                
                if hasattr(image_item, 'video_metadata') and image_item.video_metadata:
                    meta = image_item.video_metadata
                    if meta.get('duration'):
                        duration_mins = int(meta['duration'] // 60)
                        duration_secs = int(meta['duration'] % 60)
                        metadata_text += f"Duration: {duration_mins} minutes {duration_secs} seconds\n"
                    if meta.get('fps'):
                        metadata_text += f"Frame rate: {meta['fps']:.2f} fps\n"
                    if meta.get('total_frames'):
                        metadata_text += f"Total frames: {meta['total_frames']}\n"
                
                if hasattr(image_item, 'extracted_frames') and image_item.extracted_frames:
                    metadata_text += f"\nExtracted frames: {len(image_item.extracted_frames)}\n"
                    
                    # List first few extracted frame paths
                    metadata_text += "\nExtracted frame files:\n"
                    for i, frame_path in enumerate(image_item.extracted_frames[:10]):
                        frame_name = Path(frame_path).name
                        metadata_text += f"  {i+1}. {frame_name}\n"
                    if len(image_item.extracted_frames) > 10:
                        metadata_text += f"  ... and {len(image_item.extracted_frames) - 10} more\n"
                
                if metadata_text == "Video Metadata\n\n":
                    metadata_text += "No metadata available.\nUse Process > Extract Video Frames to extract frames from this video."
                
                self.description_text.SetValue(metadata_text)
                
                # Also add to descriptions list for accessibility
                desc_data = [{
                    'description': metadata_text,
                    'model': 'Video Metadata',
                    'prompt_style': '',
                    'created': '',
                    'provider': 'System'
                }]
                self.desc_list.LoadDescriptions(desc_data)
            else:
                self.description_text.SetValue("")
            
            self.save_desc_btn.Enable(False)
    
    def on_description_selected(self, event):
        """Handle selection of a description from the descriptions list"""
        selection = self.desc_list.GetSelection()
        if selection != wx.NOT_FOUND and self.current_image_item:
            # Show the selected description in the editor
            if selection < len(self.current_image_item.descriptions):
                selected_desc = self.current_image_item.descriptions[selection]
                
                # Format description with metadata appended
                desc_text = selected_desc.text
                
                # Append metadata at the end (provider, model, prompt)
                metadata_lines = []
                metadata_lines.append("\n\n---")
                if selected_desc.provider:
                    metadata_lines.append(f"Provider: {selected_desc.provider}")
                if selected_desc.model:
                    metadata_lines.append(f"Model: {selected_desc.model}")
                if selected_desc.prompt_style:
                    # If custom prompt was used, show 'custom' instead of base style
                    if selected_desc.custom_prompt:
                        prompt_display = "custom"
                    else:
                        prompt_display = selected_desc.prompt_style
                    metadata_lines.append(f"Prompt: {prompt_display}")
                if selected_desc.created:
                    created_date = selected_desc.created.split('T')[0] if 'T' in selected_desc.created else selected_desc.created
                    metadata_lines.append(f"Created: {created_date}")
                
                # Add image metadata (GPS, EXIF, etc.) if available
                if selected_desc.metadata:
                    image_metadata_lines = format_image_metadata(selected_desc.metadata)
                    if image_metadata_lines:
                        metadata_lines.append("\n--- Image Info ---")
                        metadata_lines.extend(image_metadata_lines)
                
                full_text = desc_text + "\n".join(metadata_lines)
                self.description_text.SetValue(full_text)
                self.save_desc_btn.Enable(True)
    
    # Edit Menu Handlers
    
    def on_cut(self, event):
        """Handle cut from Edit menu"""
        control = self.FindFocus()
        if control and hasattr(control, 'Cut'):
            try:
                control.Cut()
            except Exception:
                pass
    
    def on_copy(self, event):
        """Handle copy from Edit menu"""
        control = self.FindFocus()
        if control and hasattr(control, 'Copy'):
            try:
                control.Copy()
            except Exception:
                pass
    
    def on_paste(self, event):
        """Handle paste from Edit menu"""
        control = self.FindFocus()
        if control and hasattr(control, 'Paste'):
            try:
                control.Paste()
            except Exception:
                pass
    
    def on_select_all(self, event):
        """Handle select all from Edit menu"""
        control = self.FindFocus()
        if control and hasattr(control, 'SelectAll'):
            try:
                control.SelectAll()
            except Exception:
                pass
    
    # Image Preview Handlers
    
    def on_paint_preview(self, event):
        """Paint the image preview on the preview panel"""
        dc = wx.PaintDC(self.image_preview_panel)
        if self.image_preview_bitmap:
            # Draw the bitmap at top-left corner
            dc.DrawBitmap(self.image_preview_bitmap, 0, 0)
    
    def resolve_image_path(self, file_path_str):
        """Resolve image path handling relative paths and moved workspaces"""
        path = Path(file_path_str)
        if path.exists():
            return path
            
        if self.workspace_file:
            ws_dir = Path(self.workspace_file).parent
            # Try relative to workspace
            try_rel = ws_dir / file_path_str
            if try_rel.exists(): return try_rel
            
            # Try filename in workspace dir
            try_flat = ws_dir / path.name
            if try_flat.exists(): return try_flat
            
            # Try common subfolders
            for sub in ['images', 'testimages', 'img']:
                try_sub = ws_dir / sub / path.name
                if try_sub.exists(): return try_sub
                
        return path

    def load_preview_image(self, file_path):
        """
        Load and display a preview thumbnail of the image.
        
        Args:
            file_path: Path to the image file to preview
        """
        # Skip loading if previews are disabled
        if not self.show_image_previews:
            return
        
        try:
            # Try to import PIL for image loading
            try:
                from PIL import Image
            except ImportError:
                # Fallback: PIL not available
                self.image_preview_bitmap = None
                self.image_preview_panel.SetBackgroundColour(wx.Colour(200, 200, 200))
                self.image_preview_panel.Refresh()
                return
            
            # Resolve path (handle moved workspaces)
            resolved_path = self.resolve_image_path(file_path)

            # Don't pre-check exists() for network paths - os.path.exists() can give
            # false negatives on network shares due to latency/caching.
            # Just try to load and fail silently if needed.
            img = Image.open(resolved_path)
            img.thumbnail((250, 250), Image.Resampling.LANCZOS)
            
            # Get dimensions
            width, height = img.size
            
            # Convert to RGB if needed (handle transparency, grayscale, etc.)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Convert PIL image to wx.Image
            wx_image = wx.Image(width, height)
            rgb_data = img.tobytes()
            wx_image.SetData(rgb_data)
            
            # Convert to bitmap for display
            self.image_preview_bitmap = wx.Bitmap(wx_image)
            
            # Update panel appearance
            self.image_preview_panel.SetBackgroundColour(wx.Colour(255, 255, 255))
            self.image_preview_panel.Refresh()
            
        except Exception as e:
            # If image can't be loaded, silently show grey placeholder
            # (No error dialogs for missing files, network errors, corrupt images, etc.)
            self.image_preview_bitmap = None
            self.image_preview_panel.SetBackgroundColour(wx.Colour(200, 200, 200))
            self.image_preview_panel.Refresh()

    def on_import_workflow(self, event):
        """Import descriptions from a completed workflow directory."""
        progress_dlg = None
        try:
            workflow_dir = select_directory_dialog(
                self,
                "Select Workflow Directory (e.g., wf_...)"
            )

            if not workflow_dir:
                return

            workflow_path = Path(workflow_dir)
            desc_file = workflow_path / "descriptions" / "image_descriptions.txt"
            if not desc_file.exists():
                show_error(
                    self,
                    "Not a valid workflow directory.\n\n"
                    "Expected: descriptions/image_descriptions.txt\n\n"
                    f"Selected: {workflow_dir}"
                )
                return

            if not self.workspace:
                self.workspace = ImageWorkspace(new_workspace=True)

            progress_dlg = wx.ProgressDialog(
                "Importing Workflow",
                "Reading workflow descriptions...",
                maximum=100,
                parent=self,
                style=wx.PD_APP_MODAL | wx.PD_AUTO_HIDE
            )

            mapping_file = workflow_path / "descriptions" / "file_path_mapping.json"
            file_mapping = {}
            if mapping_file.exists():
                with open(mapping_file, 'r', encoding='utf-8') as f:
                    file_mapping = json.load(f)

            with open(desc_file, 'r', encoding='utf-8') as f:
                content = f.read()

            entry_pattern = re.compile(
                r"File:\s*(.+?)\r?\n"
                r"Provider:\s*(.*?)\r?\n"
                r"Model:\s*(.*?)\r?\n"
                r"Prompt Style:\s*(.*?)\r?\n"
                r"Description:\s*([\s\S]*?)(?:\r?\n-{4,}|$)",
                re.MULTILINE
            )
            entries = entry_pattern.findall(content)

            if not entries:
                blocks = re.split(r'\r?\n-{40,}\r?\n', content)
                for block in blocks:
                    if not block.strip():
                        continue
                    file_match = re.search(r'^File:\s*(.+?)$', block, re.MULTILINE)
                    provider_match = re.search(r'^Provider:\s*(.+?)$', block, re.MULTILINE)
                    model_match = re.search(r'^Model:\s*(.+?)$', block, re.MULTILINE)
                    prompt_match = re.search(r'^Prompt Style:\s*(.+?)$', block, re.MULTILINE)
                    desc_start = block.find('Description:')
                    if file_match and desc_start != -1:
                        entries.append((
                            file_match.group(1).strip(),
                            provider_match.group(1).strip() if provider_match else "",
                            model_match.group(1).strip() if model_match else "",
                            prompt_match.group(1).strip() if prompt_match else "",
                            block[desc_start + 12:].strip()
                        ))

            imported = 0
            duplicates = 0
            missing = 0
            total_entries = len(entries)

            if progress_dlg:
                progress_dlg.Update(10, "Parsing descriptions...")

            for idx, entry in enumerate(entries):
                file_path_str, provider_val, model_val, prompt_val, desc_text = entry
                file_path_str = file_path_str.strip()
                desc_text = desc_text.strip()

                resolved_path = None
                if file_mapping:
                    for temp_path, orig_path in file_mapping.items():
                        if temp_path in file_path_str or Path(temp_path).name == Path(file_path_str).name:
                            resolved_path = Path(orig_path)
                            break

                if not resolved_path:
                    candidate = Path(file_path_str)
                    if candidate.exists():
                        resolved_path = candidate
                    else:
                        for subdir in ['converted_images', 'extracted_frames']:
                            test_path = workflow_path / subdir / Path(file_path_str).name
                            if test_path.exists():
                                resolved_path = test_path
                                break

                if not resolved_path or not resolved_path.exists():
                    missing += 1
                    continue

                item = self.workspace.items.get(str(resolved_path))
                if item:
                    desc_exists = any(d.text == desc_text for d in item.descriptions)
                    if desc_exists:
                        duplicates += 1
                        continue
                else:
                    item = ImageItem(str(resolved_path))
                    self.workspace.add_item(item)

                desc = ImageDescription(
                    text=desc_text,
                    model=model_val.strip() if model_val else "unknown",
                    prompt_style=prompt_val.strip() if prompt_val else "",
                    provider=provider_val.strip() if provider_val else "",
                    custom_prompt=""
                )
                item.add_description(desc)
                imported += 1

                if progress_dlg and total_entries:
                    pct = 10 + int(((idx + 1) / total_entries) * 80)
                    progress_dlg.Update(min(pct, 95), f"Imported {imported} of {total_entries}...")

            if progress_dlg:
                progress_dlg.Update(97, "Updating workspace...")

            self.workspace.imported_workflow_dir = str(workflow_path)
            self.workspace.mark_modified()
            self.mark_modified()
            self.refresh_image_list()

            if progress_dlg:
                progress_dlg.Update(100, "Complete!")
                progress_dlg.Destroy()
                progress_dlg = None

            summary = (
                "Import Complete\n\n"
                f"Imported: {imported}\n"
                f"Duplicates: {duplicates}\n"
                f"Missing Files: {missing}\n\n"
                f"Workflow: {workflow_path.name}"
            )
            show_info(self, summary)

        except Exception as e:
            if progress_dlg:
                progress_dlg.Destroy()
            show_error(self, f"Error importing workflow:\n{str(e)}")
    
    def on_open_workflow_result(self, event):
        """Open a workflow directory in Viewer Mode"""
        dlg = wx.DirDialog(self, "Select Workflow Directory to View", 
                          style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
        
        if dlg.ShowModal() == wx.ID_OK:
            path = Path(dlg.GetPath())
            self.switch_mode('viewer', path)
        dlg.Destroy()

    def on_load_directory(self, event):
        """Load a directory of images"""
        try:
            if DirectorySelectionDialog:
                existing_dirs = self.workspace.get_all_directories() if self.workspace else []
                dlg = DirectorySelectionDialog(existing_dirs, self)
                
                if dlg.ShowModal() == wx.ID_OK:
                    selection = dlg.get_selection()
                    dlg.Destroy()
                    
                    if selection['add_to_existing'] and not self.workspace:
                        self.workspace = ImageWorkspace(new_workspace=True)
                    elif not selection['add_to_existing']:
                        # Clear existing workspace
                        self.workspace = ImageWorkspace(new_workspace=True)
                    
                    self.load_directory(
                        selection['directory'],
                        recursive=selection['recursive']
                    )
                else:
                    dlg.Destroy()
            else:
                dir_path = select_directory_dialog(self, "Select Image Directory")
                if dir_path:
                    self.workspace = ImageWorkspace(new_workspace=True)
                    self.load_directory(dir_path)
        except Exception as e:
            show_error(self, f"Error loading directory:\n{str(e)}")
    
    def on_load_from_url(self, event=None):
        """Load images from a URL"""
        from workers_wx import WebImageDownloader, DownloadProcessingWorker
        
        # Check if WebImageDownloader is available
        if WebImageDownloader is None:
            show_error(self, "URL download functionality not available.\n"
                              "Missing required libraries (BeautifulSoup4).")
            return
        
        # Check if dialog is available
        if DownloadSettingsDialog is None:
            show_error(self, "Download settings dialog not available.")
            return
        
        # Show settings dialog
        dialog = DownloadSettingsDialog(self)
        if dialog.ShowModal() != wx.ID_OK:
            dialog.Destroy()
            return
        
        settings = dialog.get_settings()
        dialog.Destroy()
        
        # Check if we're in an Untitled workspace - prompt to save first
        if is_untitled_workspace(self.workspace_file.stem):
            # Propose a name based on the URL
            proposed_name = propose_workspace_name_from_url(settings['url'])
            
            # Show save dialog
            save_dialog = wx.FileDialog(
                self,
                message=f"Save workspace before downloading from {settings['url']}",
                defaultDir=str(get_default_workspaces_root()),
                defaultFile=f"{proposed_name}.idw",
                wildcard="IDT Workspace (*.idw)|*.idw",
                style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
            )
            
            if save_dialog.ShowModal() == wx.ID_OK:
                new_path = Path(save_dialog.GetPath())
                save_dialog.Destroy()
                
                # Rename workspace before proceeding
                new_name = new_path.stem
                if not self.rename_workspace(new_name):
                    show_error(self, "Failed to rename workspace. Download cancelled.")
                    return
            else:
                save_dialog.Destroy()
                # User cancelled - abort download
                return
        
        # Get workspace directory
        workspace_dir = self.get_workspace_directory()
        
        # Store settings for workflow completion handler
        self.current_download_settings = settings
        
        # Show progress dialog
        if BatchProgressDialog:
            self.batch_progress_dialog = BatchProgressDialog(
                self,
                total_images=settings.get('max_images', 100) if settings.get('max_images') else 100
            )
            self.batch_progress_dialog.Show()
        
        # Start worker thread (store as instance variable to prevent GC)
        self.download_worker = DownloadProcessingWorker(
            self, 
            settings['url'], 
            workspace_dir,
            settings
        )
        self.download_worker.start()
        
        # Show progress in status bar
        self.SetStatusText(f"Downloading images from {settings['url']}...", 0)
    
    def load_directory(self, dir_path, recursive=False, append=False):
        """Load images from directory
        
        Args:
            dir_path: Path to directory
            recursive: If True, search subdirectories
            append: If True, add to existing workspace. If False, create new workspace.
        """
        try:
            dir_path = Path(dir_path)
            if not dir_path.exists():
                show_error(self, f"Directory not found: {dir_path}")
                return
            
            # Create new workspace if not appending
            if not append:
                self.workspace = ImageWorkspace(new_workspace=True)
            
            # Add directory to workspace
            self.workspace.add_directory(str(dir_path))
            
            # Find all images and videos
            images_found = []
            videos_found = []
            
            if recursive:
                # Recursive search - images
                for ext in self.image_extensions:
                    images_found.extend(dir_path.rglob(f"*{ext}"))
                    images_found.extend(dir_path.rglob(f"*{ext.upper()}"))
                # Recursive search - videos
                for ext in self.video_extensions:
                    videos_found.extend(dir_path.rglob(f"*{ext}"))
                    videos_found.extend(dir_path.rglob(f"*{ext.upper()}"))
            else:
                # Non-recursive - images
                for ext in self.image_extensions:
                    images_found.extend(dir_path.glob(f"*{ext}"))
                    images_found.extend(dir_path.glob(f"*{ext.upper()}"))
                # Non-recursive - videos
                for ext in self.video_extensions:
                    videos_found.extend(dir_path.glob(f"*{ext}"))
                    videos_found.extend(dir_path.glob(f"*{ext.upper()}"))
            
            # Add images to workspace
            added_count = 0
            for image_path in sorted(images_found):
                image_path_str = str(image_path)
                if image_path_str not in self.workspace.items:
                    item = ImageItem(image_path_str, "image")
                    self.workspace.add_item(item)
                    added_count += 1
            
            # Add videos to workspace
            video_count = 0
            for video_path in sorted(videos_found):
                video_path_str = str(video_path)
                if video_path_str not in self.workspace.items:
                    item = ImageItem(video_path_str, "video")
                    # Get video metadata (duration, fps, frame count)
                    metadata = self.get_video_metadata(video_path_str)
                    if metadata:
                        item.video_metadata = metadata
                    self.workspace.add_item(item)
                    video_count += 1
                    added_count += 1
            
            # Update UI
            self.refresh_image_list()
            self.mark_modified()
            
            action = "Added" if append else "Loaded"
            if video_count > 0:
                self.SetStatusText(f"{action} {added_count - video_count} images, {video_count} videos from {dir_path.name}", 0)
            else:
                self.SetStatusText(f"{action} {added_count} images from {dir_path.name}", 0)
            self.SetStatusText(f"{len(self.workspace.items)} total items", 1)
            
        except Exception as e:
            show_error(self, f"Error loading directory:\n{e}")
    
    def refresh_image_list(self):
        """Refresh the image list display with videos and extracted frames grouped"""
        # PRESERVE FOCUS: Remember currently selected item before refresh
        current_selection = self.image_list.GetSelection()
        current_file_path = None
        if current_selection != wx.NOT_FOUND:
            current_file_path = self.image_list.GetClientData(current_selection)
        
        self.image_list.Clear()
        
        new_selection_index = wx.NOT_FOUND
        
        # Separate items into categories
        videos = []
        frames = {}  # parent_video -> list of frames
        regular_images = []
        
        for file_path, item in self.workspace.items.items():
            if item.item_type == "video":
                videos.append((file_path, item))
            elif item.item_type == "extracted_frame":
                parent = item.parent_video
                if parent not in frames:
                    frames[parent] = []
                frames[parent].append((file_path, item))
            else:
                regular_images.append((file_path, item))
        
        # Helper function to get datetime for sorting (EXIF date with fallback to mtime)
        def get_sort_date(file_path):
            """Get datetime for sorting: DateTimeOriginal → DateTimeDigitized → DateTime → mtime"""
            try:
                dt = extract_exif_datetime(file_path)
                if dt:
                    return dt
                # Fallback to epoch if extraction fails
                return datetime.fromtimestamp(0)
            except Exception:
                # Last resort: epoch time
                return datetime.fromtimestamp(0)
        
        # Sort all categories by EXIF date (oldest first)
        videos.sort(key=lambda x: get_sort_date(x[0]))
        regular_images.sort(key=lambda x: get_sort_date(x[0]))
        for parent in frames:
            # Sort frames by their timestamp in filename (video_5.00s.jpg)
            # This keeps them in extraction order
            frames[parent].sort(key=lambda x: x[0])
        
        # Merge videos and regular images in chronological order
        all_items = []
        
        # Combine and sort videos + regular images together by date
        mixed_items = videos + regular_images
        mixed_items.sort(key=lambda x: get_sort_date(x[0]))
        
        # Build display list: insert extracted frames right after their parent videos
        for file_path, item in mixed_items:
            all_items.append((file_path, item, 0))  # indent level 0
            
            # If this is a video with extracted frames, insert them immediately after
            if item.item_type == "video" and file_path in frames:
                for frame_path, frame_item in frames[file_path]:
                    all_items.append((frame_path, frame_item, 1))  # indent level 1
        
        # Display all items
        for file_path, item, indent_level in all_items:
            # Apply filters
            if self.current_filter == "described":
                if not item.descriptions:
                    continue
            elif self.current_filter == "undescribed":
                if item.descriptions:
                    continue
            elif self.current_filter == "videos":
                # Show videos and their extracted frames only
                if item.item_type not in ["video", "extracted_frame"]:
                    continue
            
            base_name = Path(file_path).name
            prefix_parts = []
            
            # 1. Description count
            desc_count = len(item.descriptions)
            if desc_count > 0:
                prefix_parts.append(f"d{desc_count}")
            
            # 2. Processing indicator (P)
            if file_path in self.processing_items:
                prefix_parts.append("P")
            # Phase 6: Batch processing state indicators
            elif hasattr(item, 'processing_state') and item.processing_state:
                if item.processing_state == "paused":
                    prefix_parts.append("!")  # Paused
                elif item.processing_state == "failed":
                    prefix_parts.append("X")  # Failed
                elif item.processing_state == "pending":
                    prefix_parts.append(".")  # Pending
            
            # 3. Video extraction status
            if item.item_type == "video" and hasattr(item, 'extracted_frames') and item.extracted_frames:
                frame_count = len(item.extracted_frames)
                prefix_parts.append(f"E{frame_count}")
            
            # 4. Item type icon indicator (removed for screen reader accessibility)
            type_icon = ""
            
            # Combine prefix and display name with indentation
            indent = "  " * indent_level  # Two spaces per level
            if prefix_parts:
                prefix = "".join(prefix_parts)
                display_name = f"{indent}{type_icon}{prefix} {base_name}"
            else:
                display_name = f"{indent}{type_icon}{base_name}"
            
            index = self.image_list.Append(display_name, file_path)  # Store file_path as client data
            
            # Track if this is the previously selected item
            if current_file_path and file_path == current_file_path:
                new_selection_index = index
        
        # RESTORE FOCUS: Select the same item after refresh
        if new_selection_index != wx.NOT_FOUND:
            self.image_list.SetSelection(new_selection_index)
            # Ensure it's visible
            self.image_list.EnsureVisible(new_selection_index)
        elif self.image_list.GetCount() > 0:
            # No previous selection - select first item (e.g., after loading directory)
            self.image_list.SetSelection(0)
            self.image_list.EnsureVisible(0)
            # Trigger selection event to update display
            first_file_path = self.image_list.GetClientData(0)
            if first_file_path and first_file_path in self.workspace.items:
                self.current_image_item = self.workspace.items[first_file_path]
                self.display_image_info(self.current_image_item)
    
    def on_process_single(self, event):
        """Process single selected image or extract video frames"""
        if not self.current_image_item:
            show_warning(self, "No image selected")
            return
        
        # If video, show extraction dialog instead
        if self.current_image_item.item_type == "video":
            self.on_extract_video(event)
            return
        
        if not ProcessingWorker:
            show_error(self, "Processing worker not available")
            return
        
        # Show processing options dialog with cached models
        if ProcessingOptionsDialog:
            dialog = ProcessingOptionsDialog(self.config, cached_ollama_models=self.cached_ollama_models, parent=self)
            if dialog.ShowModal() != wx.ID_OK:
                dialog.Destroy()
                return
            
            options = dialog.get_config()
            dialog.Destroy()
        else:
            # Use defaults
            options = {
                'provider': self.config.get('default_provider', 'ollama'),
                'model': self.config.get('default_model', 'moondream'),
                'prompt_style': self.config.get('default_prompt_style', 'narrative'),
                'custom_prompt': '',
                'skip_existing': False
            }
        
        # Start processing worker
        api_key = self.get_api_key_for_provider(options['provider'])
        worker = ProcessingWorker(
            self,
            self.current_image_item.file_path,
            options['provider'],
            options['model'],
            options['prompt_style'],
            options.get('custom_prompt', ''),
            None,  # detection_settings
            None,  # prompt_config_path
            api_key  # API key for cloud providers
        )
        
        # Mark as processing with provider/model info
        self.processing_items[self.current_image_item.file_path] = {
            'provider': options['provider'],
            'model': options['model']
        }
        self.refresh_image_list()
        
        # Update window title to show processing status
        self.update_window_title("ImageDescriber", Path(self.workspace_file).name if self.workspace_file else "Untitled")
        
        worker.start()
        
        self.SetStatusText(f"Processing: {Path(self.current_image_item.file_path).name}...", 0)
    
    def on_process_all(self, event, skip_existing: bool = True):
        """Process images in batch
        
        Args:
            event: Menu event
            skip_existing: If True, only process images without descriptions (default, safe)
                          If False, reprocess all images (show warning first)
        """
        print("="*60, flush=True)
        print(f"on_process_all CALLED - skip_existing={skip_existing}", flush=True)
        print(f"Workspace items: {len(self.workspace.items) if self.workspace else 0}", flush=True)
        print("="*60, flush=True)
        
        if not self.workspace or not self.workspace.items:
            show_warning(self, "No images in workspace")
            return
        
        if not BatchProcessingWorker:
            show_error(self, "Batch processing worker not available")
            return
        
        # Check if we're in an Untitled workspace - prompt to save first
        if is_untitled_workspace(self.workspace_file.stem):
            # Inform user they need to save first
            result = wx.MessageBox(
                "Batch processing requires a named workspace.\n\n"
                "Your current workspace is 'Untitled' and must be saved with a name before processing.\n\n"
                "Would you like to save the workspace now?",
                "Save Workspace Required",
                wx.YES_NO | wx.ICON_QUESTION
            )
            
            if result != wx.YES:
                return
            
            # Propose a name based on workspace content
            proposed_name = self._propose_workspace_name_from_content()
            
            # Show save dialog
            save_dialog = wx.FileDialog(
                self,
                message="Save workspace before batch processing",
                defaultDir=str(get_default_workspaces_root()),
                defaultFile=f"{proposed_name}.idw",
                wildcard="IDT Workspace (*.idw)|*.idw",
                style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
            )
            
            if save_dialog.ShowModal() == wx.ID_OK:
                new_path = Path(save_dialog.GetPath())
                save_dialog.Destroy()
                
                # Rename workspace before proceeding
                new_name = new_path.stem
                if not self.rename_workspace(new_name):
                    show_error(self, "Failed to rename workspace. Processing cancelled.")
                    return
            else:
                save_dialog.Destroy()
                # User cancelled the file dialog
                return
        
        # Auto-save before batch processing
        if self.modified:
            self.save_workspace(str(self.workspace_file))
        
        # Phase 5: Warn about redescribing all
        if not skip_existing:
            result = ask_yes_no(
                self,
                "Redescribe ALL images?\n\n"
                "This will ADD new descriptions to all images (including those already described).\n"
                "Existing descriptions will be kept - you'll have multiple descriptions per image.\n\n"
                "Continue?"
            )
            if not result:
                return
        
        # Show processing options dialog with cached models
        if ProcessingOptionsDialog:
            dialog = ProcessingOptionsDialog(self.config, cached_ollama_models=self.cached_ollama_models, parent=self)
            if dialog.ShowModal() != wx.ID_OK:
                dialog.Destroy()
                return
            
            options = dialog.get_config()
            dialog.Destroy()
        else:
            # Use defaults
            options = {
                'provider': self.config.get('default_provider', 'ollama'),
                'model': self.config.get('default_model', 'moondream'),
                'prompt_style': self.config.get('default_prompt_style', 'narrative'),
                'custom_prompt': '',
            }
        
        # Phase 5: Use skip_existing parameter instead of options
        # Get files to process - handle videos separately
        images_to_process = []
        videos_to_extract = []
        
        print(f"Scanning {len(self.workspace.items)} workspace items...", flush=True)
        
        for item in self.workspace.items.values():
            print(f"  Item: {Path(item.file_path).name}, type={item.item_type}, has_desc={bool(item.descriptions)}", flush=True)
            if item.item_type == "video":
                # Check if video needs extraction
                if not hasattr(item, 'extracted_frames') or not item.extracted_frames:
                    print(f"    -> Adding to videos_to_extract", flush=True)
                    videos_to_extract.append(item.file_path)
                else:
                    print(f"    -> Video already has {len(item.extracted_frames)} frames", flush=True)
            elif skip_existing:
                if not item.descriptions:
                    print(f"    -> Adding to images_to_process (no descriptions)", flush=True)
                    images_to_process.append(item.file_path)
                else:
                    print(f"    -> Skipping (has descriptions)", flush=True)
            else:
                print(f"    -> Adding to images_to_process (redescribe all)", flush=True)
                images_to_process.append(item.file_path)
        
        print(f"Result: {len(videos_to_extract)} videos to extract, {len(images_to_process)} images to process", flush=True)
        
        # Auto-extract video frames with default settings (1 frame every 5 seconds)
        if videos_to_extract:
            print(f"BRANCH: Starting video extraction flow", flush=True)
            logger.info(f"Starting batch video extraction: {len(videos_to_extract)} videos, {len(images_to_process)} images")
            logger.debug(f"Videos to extract: {videos_to_extract}")
            
            # Show progress dialog immediately
            total_items = len(videos_to_extract) + len(images_to_process)
            logger.debug(f"Creating progress dialog with {total_items} total items")
            if BatchProgressDialog:
                self.batch_progress_dialog = BatchProgressDialog(self, total_items)
                self.batch_progress_dialog.Show()
                logger.debug("Progress dialog shown")
                if hasattr(self, 'show_batch_progress_item'):
                    self.show_batch_progress_item.Enable(True)
            
            self.SetStatusText(f"Extracting frames from {len(videos_to_extract)} video(s)...", 0)
            
            # Store processing options and queue for after video extraction
            self._pending_batch_options = options
            self._pending_batch_queue = images_to_process.copy()  # FIX: Use images_to_process, not to_process
            self._pending_batch_skip_existing = skip_existing
            self._videos_to_extract = videos_to_extract
            self._extracted_video_count = 0
            
            # Start extracting first video
            print(f"About to call _extract_next_video_in_batch()...", flush=True)
            logger.debug("Calling _extract_next_video_in_batch() to start extraction")
            self._extract_next_video_in_batch()
            print(f"Returned from _extract_next_video_in_batch()", flush=True)
            logger.debug("Returned from _extract_next_video_in_batch(), waiting for background thread")
            return  # Will continue in video extraction event handler
        
        # No videos to extract, proceed directly to image processing
        print(f"BRANCH: No videos to extract, proceeding to image processing", flush=True)
        to_process = images_to_process
        
        if not to_process:
            show_info(self, "All images already have descriptions")
            return
        
        # Phase 3: Mark items as pending BEFORE starting batch
        queue_position = 0
        for file_path in to_process:
            if file_path in self.workspace.items:
                item = self.workspace.items[file_path]
                item.processing_state = "pending"
                item.batch_queue_position = queue_position
                queue_position += 1
        
        # Phase 3: Store batch parameters for resume
        self.workspace.batch_state = {
            "provider": options['provider'],
            "model": options['model'],
            "prompt_style": options.get('prompt_style', 'default'),
            "custom_prompt": options.get('custom_prompt'),
            "detection_settings": options.get('detection_settings'),
            "total_queued": len(to_process),
            "started": datetime.now().isoformat()
        }
        
        # Start batch processing worker - STORE REFERENCE (Phase 3: KEY FIX)
        self.batch_worker = BatchProcessingWorker(
            self,
            to_process,
            options['provider'],
            options['model'],
            options['prompt_style'],
            options.get('custom_prompt', ''),
            None,  # detection_settings
            None,  # prompt_config_path
            skip_existing,  # Phase 5: Use parameter instead of options
            progress_offset=0  # No offset when processing without video extraction
        )
        self.batch_worker.start()
        
        # Phase 3: Show progress dialog
        if BatchProgressDialog:
            self.batch_progress_dialog = BatchProgressDialog(self, len(to_process))
            self.batch_progress_dialog.Show()
            # Enable "Show Batch Progress" menu item
            if hasattr(self, 'show_batch_progress_item'):
                self.show_batch_progress_item.Enable(True)
        
        # Phase 3: Initialize timing
        self.batch_start_time = time.time()
        self.batch_processing_times = []
        
        # Save workspace (preserves batch_state)
        if self.workspace_file:
            self.save_workspace(self.workspace_file)
        
        self.SetStatusText(f"Processing {len(to_process)} images...", 0)
    
    def _extract_next_video_in_batch(self):
        """Extract next video in batch processing queue"""
        print(f"_extract_next_video_in_batch: count={self._extracted_video_count}, total={len(self._videos_to_extract)}", flush=True)
        logger.debug(f"_extract_next_video_in_batch called: count={self._extracted_video_count}, total={len(self._videos_to_extract)}")
        
        if self._extracted_video_count >= len(self._videos_to_extract):
            # All videos extracted, proceed to image processing
            print(f"All videos extracted, moving to image processing", flush=True)
            logger.info("All videos extracted, proceeding to image processing")
            self._start_batch_image_processing()
            return
        
        # Get next video
        video_path = self._videos_to_extract[self._extracted_video_count]
        video_name = Path(video_path).name
        print(f"Extracting video {self._extracted_video_count + 1}/{len(self._videos_to_extract)}: {video_name}", flush=True)
        logger.info(f"Extracting video {self._extracted_video_count + 1}/{len(self._videos_to_extract)}: {video_name}")
        
        # Update progress
        video_num = self._extracted_video_count + 1
        total_videos = len(self._videos_to_extract)
        if self.batch_progress_dialog:
            self.batch_progress_dialog.update_progress(
                current=video_num,
                total=len(self._videos_to_extract) + len(self._pending_batch_queue),
                image_name=f"Extracting video {video_name} ({video_num}/{total_videos})",
                provider="System",
                model="Video Extraction"
            )
        
        self.SetStatusText(f"Extracting frames from {video_name} ({video_num}/{total_videos})...", 0)
        
        # Load extraction config
        try:
            from config_loader import load_json_config
            video_config, _, _ = load_json_config('video_frame_extractor_config.json')
            if video_config:
                extraction_config = {
                    "extraction_mode": video_config.get("extraction_mode", "time_interval"),
                    "time_interval_seconds": video_config.get("time_interval_seconds", 5.0),
                    "scene_change_threshold": video_config.get("scene_change_threshold", 30.0),
                    "min_scene_duration_seconds": video_config.get("min_scene_duration_seconds", 1.0),
                    "start_time_seconds": video_config.get("start_time_seconds", 0),
                    "end_time_seconds": video_config.get("end_time_seconds")
                }
            else:
                raise Exception("Config not loaded")
        except Exception:
            extraction_config = {
                "extraction_mode": "time_interval",
                "time_interval_seconds": 5.0,
                "scene_change_threshold": 30.0,
                "min_scene_duration_seconds": 1.0,
                "start_time_seconds": 0,
                "end_time_seconds": None
            }
        
        # Check if cv2 is available before starting extraction
        if not cv2:
            error_msg = ("OpenCV (cv2) is not installed.\n\n"
                        "Video frame extraction requires OpenCV.\n"
                        "Please install it with: pip install opencv-python")
            logger.error("cv2 not available for video extraction")
            show_error(self, error_msg)
            # Clean up batch state
            self._batch_video_extraction = False
            if self.batch_progress_dialog:
                self.batch_progress_dialog.Close()
                self.batch_progress_dialog = None
            return
        
        # Mark this as a batch video extraction
        self._batch_video_extraction = True
        logger.debug(f"Set _batch_video_extraction=True, starting VideoProcessingWorker for {video_path}")
        logger.debug(f"Extraction config: {extraction_config}")
        
        # Start video extraction worker
        from workers_wx import VideoProcessingWorker
        self.video_worker = VideoProcessingWorker(self, video_path, extraction_config)
        logger.debug("Starting VideoProcessingWorker thread...")
        self.video_worker.start()
        logger.debug("VideoProcessingWorker thread started (non-blocking)")
    
    def _complete_batch_video_extraction(self, video_path, extracted_frames, video_metadata):
        """Handle completion of one video in batch extraction"""
        # Update video item
        if video_path in self.workspace.items:
            video_item = self.workspace.items[video_path]
            video_item.extracted_frames = extracted_frames
            if video_metadata:
                video_item.video_metadata = video_metadata
        
        # Add extracted frames as items to workspace
        for frame_path in extracted_frames:
            if frame_path not in self.workspace.items:
                frame_item = ImageItem(frame_path, "extracted_frame")
                frame_item.parent_video = video_path
                self.workspace.add_item(frame_item)
                
                # Add to processing queue if needed
                if self._pending_batch_skip_existing and not frame_item.descriptions:
                    self._pending_batch_queue.append(frame_path)
                elif not self._pending_batch_skip_existing:
                    self._pending_batch_queue.append(frame_path)
        
        # Move to next video
        self._extracted_video_count += 1
        self._extract_next_video_in_batch()
    
    def _start_batch_image_processing(self):
        """Start batch image processing after video extraction completes"""
        # Clean up video extraction state
        self._batch_video_extraction = False
        del self._videos_to_extract
        del self._extracted_video_count
        
        # Refresh UI
        self.refresh_image_list()
        self.mark_modified()
        
        # Get final processing queue
        to_process = self._pending_batch_queue
        options = self._pending_batch_options
        skip_existing = self._pending_batch_skip_existing
        
        # Clean up pending state
        del self._pending_batch_queue
        del self._pending_batch_options
        del self._pending_batch_skip_existing
        
        if not to_process:
            # Close progress dialog
            if self.batch_progress_dialog:
                self.batch_progress_dialog.Close()
                self.batch_progress_dialog = None
            show_info(self, "Video frames extracted.\nAll images already have descriptions.")
            return
        
        # Mark items as pending
        queue_position = 0
        for file_path in to_process:
            if file_path in self.workspace.items:
                item = self.workspace.items[file_path]
                item.processing_state = "pending"
                item.batch_queue_position = queue_position
                queue_position += 1
        
        # Store batch parameters
        self.workspace.batch_state = {
            "provider": options['provider'],
            "model": options['model'],
            "prompt_style": options.get('prompt_style', 'default'),
            "custom_prompt": options.get('custom_prompt'),
            "detection_settings": options.get('detection_settings'),
            "total_queued": len(to_process),
            "started": datetime.now().isoformat()
        }
        
        # Calculate progress offset (number of videos already extracted)
        progress_offset = len(self._videos_to_extract) if hasattr(self, '_videos_to_extract') else 0
        
        # Start batch processing worker with offset
        self.batch_worker = BatchProcessingWorker(
            self,
            to_process,
            options['provider'],
            options['model'],
            options['prompt_style'],
            options.get('custom_prompt', ''),
            None,  # detection_settings
            None,  # prompt_config_path
            skip_existing,
            progress_offset=progress_offset
        )
        self.batch_worker.start()
        
        # Update progress dialog for image processing (continue from where videos left off)
        if self.batch_progress_dialog:
            total_items = len(to_process) + progress_offset
            self.batch_progress_dialog.update_progress(
                current=progress_offset,
                total=total_items,
                image_name="Starting image processing...",
                provider=options['provider'],
                model=options['model']
            )
        
        # Initialize timing
        self.batch_start_time = time.time()
        self.batch_processing_times = []
        
        # Save workspace
        if self.workspace_file:
            self.save_workspace(self.workspace_file)
        
        self.SetStatusText(f"Processing {len(to_process)} images...", 0)
    
    def on_save_description(self, event):
        """Save edited description"""
        if not self.current_image_item:
            return
        
        new_text = self.description_text.GetValue().strip()
        if not new_text:
            show_warning(self, "Description is empty")
            return
        
        # Update the latest description or create new one
        if self.current_image_item.descriptions:
            # Update latest
            self.current_image_item.descriptions[-1].text = new_text
        else:
            # Create new description
            desc = ImageDescription(
                text=new_text,
                model="manual",
                prompt_style="edited"
            )
            self.current_image_item.add_description(desc)
        
        self.mark_modified()
        self.refresh_image_list()
        self.SetStatusText("Description saved", 0)
    
    def on_new_workspace(self, event):
        """Create new workspace"""
        if not self.confirm_unsaved_changes():
            return
        
        # Create new workspace
        self.workspace = ImageWorkspace(new_workspace=True)
        self.workspace_file = None
        self.current_image_item = None
        
        # Clear UI
        self.image_list.Clear()
        self.description_text.SetValue("")
        self.image_info_label.SetLabel("No image selected")
        
        # Update status
        self.SetStatusText("New workspace created", 0)
        self.SetStatusText("No images", 1)
        self.update_window_title("ImageDescriber", "Untitled")
        self.process_btn.Enable(False)
        self.save_desc_btn.Enable(False)
        self.clear_modified()
    
    def on_open_workspace(self, event):
        """Open existing workspace"""
        if not self.confirm_unsaved_changes():
            return
        
        default_dir = ""
        default_file = ""
        if self.workspace_file:
            default_dir = str(Path(self.workspace_file).parent)

        file_path = open_file_dialog(
            self,
            "Open Workspace",
            "ImageDescriber Workspace (*.idw)|*.idw|All files (*.*)|*.*",
            default_dir,
            default_file
        )
        
        if file_path:
            self.load_workspace(file_path)
    
    def load_workspace(self, file_path):
        """Load workspace from file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Create workspace from data
            self.workspace = ImageWorkspace.from_dict(data)
            self.workspace_file = file_path
            self.workspace.saved = True
            
            # Load cached Ollama models from workspace
            self.cached_ollama_models = self.workspace.cached_ollama_models
            
            # Update UI
            self.refresh_image_list()
            self.update_window_title("ImageDescriber", Path(file_path).name)
            
            # Update status
            count = len(self.workspace.items)
            self.SetStatusText(f"Workspace loaded: {Path(file_path).name}", 0)
            self.SetStatusText(f"{count} images", 1)
            self.clear_modified()
            
            # Phase 4: Check for resumable batch
            if self.workspace.batch_state:
                wx.CallAfter(self.prompt_resume_batch)
            
        except json.JSONDecodeError as e:
            show_error(self, f"Error loading workspace - Invalid JSON format:\n\nLine {e.lineno}, Column {e.colno}\n{e.msg}\n\nThe workspace file may be corrupted. Try opening it in a text editor to fix the JSON syntax error.")
        except Exception as e:
            show_error(self, f"Error loading workspace:\n{e}")
    
    def on_save_workspace_as(self, event):
        """Save workspace to new file"""
        # Use default workspaces directory
        default_dir = str(get_default_workspaces_root())
        
        # Propose a sensible default name
        if is_untitled_workspace(self.workspace_file.stem):
            default_file = f"{self._propose_workspace_name_from_content()}.idw"
        else:
            default_file = self.workspace_file.name

        file_path = save_file_dialog(
            self,
            "Save Workspace As",
            "ImageDescriber Workspace (*.idw)|*.idw|All files (*.*)|*.*",
            default_dir,
            default_file
        )

        if file_path:
            new_path = Path(file_path)
            new_name = new_path.stem
            
            # If name changed, use rename (moves data directory too)
            if new_name != self.workspace_file.stem:
                self.rename_workspace(new_name)
            else:
                # Same name, different location - just save
                self.save_workspace(str(new_path))

    def on_save_workspace(self, event):
        """Save current workspace"""
        if self.workspace_file:
            self.save_workspace(self.workspace_file)
        else:
            self.on_save_workspace_as(event)
    
    def save_workspace(self, file_path):
        """Save workspace to file"""
        try:
            # Check if workspace location changed (for moving extracted frames)
            old_workspace_file = self.workspace_file
            workspace_changed = old_workspace_file != file_path
            
            # Get old and new workspace directories
            if workspace_changed and old_workspace_file:
                old_ws_path = Path(old_workspace_file)
                old_ws_dir = old_ws_path.parent / f"{old_ws_path.stem}_workspace"
            else:
                old_ws_dir = None
            
            # Update workspace file path BEFORE getting new directory
            self.workspace_file = file_path
            new_ws_dir = self.get_workspace_directory()
            
            # Move extracted frames if workspace location changed
            if workspace_changed and old_ws_dir and old_ws_dir.exists():
                old_extracted_frames = old_ws_dir / "extracted_frames"
                new_extracted_frames = new_ws_dir / "extracted_frames"
                
                if old_extracted_frames.exists():
                    # Move the entire extracted_frames directory
                    import shutil
                    if new_extracted_frames.exists():
                        shutil.rmtree(new_extracted_frames)
                    shutil.move(str(old_extracted_frames), str(new_extracted_frames))
                    
                    # Update all extracted_frame item paths
                    for item in self.workspace.items.values():
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
                        if old_ws_dir.exists() and not any(old_ws_dir.iterdir()):
                            old_ws_dir.rmdir()
                    except:
                        pass  # Ignore cleanup errors
            
            # Update workspace metadata
            self.workspace.file_path = file_path
            self.workspace.modified = datetime.now().isoformat()
            
            # Sync cached models to workspace
            self.workspace.cached_ollama_models = self.cached_ollama_models
            
            # Save to file with proper JSON encoding
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.workspace.to_dict(), f, indent=2, ensure_ascii=False, default=str)
            
            self.workspace.saved = True
            self.clear_modified()
            
            self.update_window_title("ImageDescriber", Path(file_path).name)
            self.SetStatusText(f"Workspace saved: {Path(file_path).name}", 0)
            
        except Exception as e:
            show_error(self, f"Error saving workspace:\n{e}")
    
    def rename_workspace(self, new_name: str) -> bool:
        """Rename workspace and its data directory
        
        Args:
            new_name: New workspace name (without .idw extension)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            old_idw_path = self.workspace_file
            old_name = old_idw_path.stem
            
            # Create new paths
            new_idw_path = old_idw_path.parent / f"{new_name}.idw"
            old_data_dir = get_workspace_files_directory(old_idw_path)
            new_data_dir = old_data_dir.parent / new_name
            
            # Rename data directory first
            if old_data_dir.exists():
                old_data_dir.rename(new_data_dir)
            
            # Update all internal file paths in workspace items
            for item in self.workspace.items.values():
                item_path = Path(item.file_path)
                
                # Check if path is inside workspace data directory
                try:
                    relative = item_path.relative_to(old_data_dir)
                    # Update to new data directory
                    new_path = new_data_dir / relative
                    item.file_path = str(new_path)
                except ValueError:
                    # Path is external, keep as-is
                    pass
                
                # Update extracted_frames paths if they exist
                if hasattr(item, 'extracted_frames') and item.extracted_frames:
                    updated_frames = []
                    for frame_path in item.extracted_frames:
                        frame_path_obj = Path(frame_path)
                        try:
                            relative = frame_path_obj.relative_to(old_data_dir)
                            new_frame_path = new_data_dir / relative
                            updated_frames.append(str(new_frame_path))
                        except ValueError:
                            # External path, keep as-is
                            updated_frames.append(frame_path)
                    item.extracted_frames = updated_frames
            
            # Update workspace directory paths
            updated_dir_paths = []
            for dp in self.workspace.directory_paths:
                try:
                    dp_path = Path(dp)
                    relative = dp_path.relative_to(old_data_dir)
                    new_path = new_data_dir / relative
                    updated_dir_paths.append(str(new_path))
                except ValueError:
                    # External path, keep as-is
                    updated_dir_paths.append(dp)
            self.workspace.directory_paths = updated_dir_paths
            
            # Save workspace with current settings to new name
            self.save_workspace(str(new_idw_path))
            
            # Delete old IDW file
            if old_idw_path.exists() and old_idw_path != new_idw_path:
                old_idw_path.unlink()
            
            # Update instance variables
            self.workspace_file = new_idw_path
            self.current_directory = new_data_dir
            
            # Update window title
            self.update_window_title("ImageDescriber", f"{new_name}.idw")
            
            return True
        except Exception as e:
            logger.error(f"Error renaming workspace: {e}")
            show_error(self, f"Error renaming workspace:\n{e}")
            return False
    
    def _propose_workspace_name_from_content(self) -> str:
        """Propose a workspace name based on content
        
        Returns:
            str: Proposed workspace name
        """
        # Try to find most representative content
        
        # Option 1: If there are directory paths, use the first one
        if self.workspace.directory_paths:
            dir_path = Path(self.workspace.directory_paths[0])
            return f"{dir_path.name}_{datetime.now().strftime('%Y%m%d')}"
        
        # Option 2: If there are videos, use the first video name
        videos = [item for item in self.workspace.items.values() if item.item_type == "video"]
        if videos:
            video_name = Path(videos[0].file_path).stem
            return f"{video_name}_{datetime.now().strftime('%Y%m%d')}"
        
        # Option 3: If downloaded images, propose download_date
        downloads = [item for item in self.workspace.items.values() 
                    if hasattr(item, 'download_url') and item.download_url]
        if downloads:
            return f"downloads_{datetime.now().strftime('%Y%m%d')}"
        
        # Fallback: workspace_date
        return f"workspace_{datetime.now().strftime('%Y%m%d')}"
    
    def on_export_descriptions(self, event):
        """Export all descriptions to text or HTML file (like CLI output)"""
        if not self.workspace or not self.workspace.items:
            show_warning(self, "No descriptions to export. Add images and process them first.")
            return
        
        # Ask user where to save with format options
        default_dir = str(Path.home() / "Desktop")
        default_file = "exported_descriptions.txt"
        
        file_path = save_file_dialog(
            self,
            "Export Descriptions",
            "Text files (*.txt)|*.txt|HTML files (*.html)|*.html|All files (*.*)|*.*",
            default_dir,
            default_file
        )
        
        if not file_path:
            return  # User cancelled
        
        try:
            # Determine format by file extension
            path = Path(file_path)
            if path.suffix.lower() == '.html':
                self.export_descriptions_to_html(file_path)
            else:
                self.export_descriptions_to_text(file_path)
            show_info(self, f"Successfully exported descriptions to:\n{file_path}")
        except Exception as e:
            show_error(self, f"Error exporting descriptions:\n{e}")
    
    def export_descriptions_to_text(self, output_file: str):
        """Export workspace descriptions to text file in CLI format
        
        Handles multiple descriptions per image by creating separate sections
        for each description with its own model/prompt/timestamp information.
        
        Args:
            output_file: Path to output text file
        """
        separator = '-' * 80
        
        with open(output_file, 'w', encoding='utf-8') as f:
            # Write header
            f.write("Image Descriptions - Exported from ImageDescriber\n")
            f.write(f"Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Images: {len(self.workspace.items)}\n")
            f.write("=" * 80 + "\n\n")
            
            # Sort images by filename for consistent output
            sorted_items = sorted(self.workspace.items.items(), key=lambda x: Path(x[0]).name)
            
            for file_path, item in sorted_items:
                path = Path(file_path)
                
                # Skip images with no descriptions
                if not item.descriptions:
                    continue
                
                # Write entry for each description (handles multiple descriptions per image)
                for desc_index, desc in enumerate(item.descriptions, start=1):
                    # Note if multiple descriptions (FIRST - before file info)
                    if len(item.descriptions) > 1:
                        f.write(f"(Description {desc_index} of {len(item.descriptions)} for this image)\n\n")
                    
                    # File info
                    f.write(f"File: {path.name}\n")
                    f.write(f"Path: {file_path}\n")
                    
                    # Metadata if available
                    if desc.metadata:
                        metadata_str = self._format_metadata_for_export(desc.metadata)
                        if metadata_str:
                            f.write(metadata_str + "\n")
                    
                    # Processing info
                    f.write(f"Provider: {desc.provider}\n")
                    f.write(f"Model: {desc.model}\n")
                    f.write(f"Prompt Style: {desc.prompt_style}\n")
                    
                    # Token usage if available
                    if desc.metadata and 'token_usage' in desc.metadata:
                        usage = desc.metadata['token_usage']
                        prompt_tokens = usage.get('prompt_tokens', 0)
                        completion_tokens = usage.get('completion_tokens', 0)
                        total_tokens = usage.get('total_tokens', 0)
                        if total_tokens > 0:
                            f.write(f"Tokens: {total_tokens:,} total ({prompt_tokens:,} prompt + {completion_tokens:,} completion)\n")
                    
                    # Description text
                    f.write(f"Description: {desc.text}\n")
                    
                    # Timestamp
                    f.write(f"Timestamp: {desc.created}\n")
                    
                    # OSM attribution if needed
                    if desc.metadata and desc.metadata.get('osm_attribution_required'):
                        f.write("\nLocation data © OpenStreetMap contributors (https://www.openstreetmap.org/copyright)\n")
                    
                    f.write(separator + "\n\n")
    
    def export_descriptions_to_html(self, output_file: str):
        """Export workspace descriptions to HTML file using descriptions_to_html module
        
        Args:
            output_file: Path to output HTML file
        """
        # Create temporary text file
        temp_txt = None
        try:
            # Export to temporary text file first
            temp_txt = Path(tempfile.gettempdir()) / f"imagedescriber_export_{int(time.time())}.txt"
            self.export_descriptions_to_text(str(temp_txt))
            
            # Import HTML generation modules
            try:
                from scripts.descriptions_to_html import DescriptionsParser, HTMLGenerator
            except ImportError:
                # Try without scripts prefix (frozen mode)
                from descriptions_to_html import DescriptionsParser, HTMLGenerator
            
            # Parse the text file
            parser = DescriptionsParser(temp_txt)
            entries = parser.parse()
            
            if not entries:
                raise Exception("No description entries found to export")
            
            # Generate HTML with full details
            generator = HTMLGenerator(
                entries,
                title="Image Descriptions - Exported from ImageDescriber",
                include_details=True
            )
            html_content = generator.generate()
            
            # Write HTML file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
                
        finally:
            # Clean up temporary file
            if temp_txt and temp_txt.exists():
                try:
                    temp_txt.unlink()
                except Exception:
                    pass  # Ignore cleanup errors
    
    def _format_metadata_for_export(self, metadata: dict) -> str:
        """Format metadata for text export (matching CLI format)
        
        Args:
            metadata: Metadata dictionary
            
        Returns:
            Formatted metadata string
        """
        lines = []
        
        # Photo date
        if 'datetime_str' in metadata:
            lines.append(f"Photo Date: {metadata['datetime_str']}")
        elif 'datetime' in metadata:
            # Handle both string and datetime objects
            dt_val = metadata['datetime']
            if isinstance(dt_val, str):
                lines.append(f"Photo Date: {dt_val}")
        
        # Location
        if 'location' in metadata:
            location = metadata['location']
            location_parts = []
            
            # City, state, country
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
                location_parts.append(f"Location: {', '.join(readable_parts)}")
            
            # GPS coordinates
            if 'latitude' in location and 'longitude' in location:
                lat = location['latitude']
                lon = location['longitude']
                location_parts.append(f"GPS: {lat:.6f}, {lon:.6f}")
            
            if 'altitude' in location:
                alt = location['altitude']
                location_parts.append(f"Altitude: {alt:.1f}m")
            
            if location_parts:
                lines.append(", ".join(location_parts))
        
        # Camera
        if 'camera' in metadata:
            camera = metadata['camera']
            camera_parts = []
            
            if 'make' in camera and 'model' in camera:
                camera_parts.append(f"{camera['make']} {camera['model']}")
            
            if 'lens' in camera:
                camera_parts.append(f"Lens: {camera['lens']}")
            
            if camera_parts:
                lines.append(f"Camera: {', '.join(camera_parts)}")
        
        # Processing time
        if 'processing_time_seconds' in metadata:
            proc_time = metadata['processing_time_seconds']
            lines.append(f"Processing Time: {proc_time:.2f} seconds")
        
        return "\n".join(lines)
    
    def on_worker_progress(self, event):
        """Handle progress updates from worker threads"""
        self.SetStatusText(event.message, 0)
        
        # Track batch processing progress
        if hasattr(event, 'current') and hasattr(event, 'total') and event.current > 0:
            self.batch_progress = {
                'current': event.current,
                'total': event.total,
                'file_path': event.file_path
            }
            
            # Update title bar to show progress
            progress_percent = int(event.current * 100 / event.total) if event.total > 0 else 0
            doc_name = Path(self.workspace_file).name if self.workspace_file else "Untitled"
            self.SetTitle(f"{progress_percent}%, {event.current} of {event.total} - ImageDescriber - {doc_name}")
            
            # Mark current image being processed with "P"
            self.processing_items[event.file_path] = {'provider': '', 'model': ''}
            self.refresh_image_list()
            
            # Phase 3: Track processing time for this image
            if self.batch_start_time:
                elapsed = time.time() - self.batch_start_time
                self.batch_processing_times.append(elapsed)
                self.batch_start_time = time.time()  # Reset for next image
            
            # Phase 3: Calculate average time
            avg_time = (sum(self.batch_processing_times) / len(self.batch_processing_times)
                       if self.batch_processing_times else 0.0)
            
            # Phase 3: Update progress dialog
            if self.batch_progress_dialog and self.batch_progress:
                self.batch_progress_dialog.update_progress(
                    current=self.batch_progress['current'],
                    total=self.batch_progress['total'],
                    file_path=self.batch_progress['file_path'],
                    avg_time=avg_time
                )
        else:
            self.batch_progress = None
    
    def on_worker_complete(self, event):
        """Handle successful processing completion"""
        # Remove from processing items
        self.processing_items.pop(event.file_path, None)
        
        # Find the image item and add description
        if event.file_path in self.workspace.items:
            image_item = self.workspace.items[event.file_path]
            desc = ImageDescription(
                text=event.description,
                model=event.model,
                prompt_style=event.prompt_style,
                custom_prompt=event.custom_prompt,
                provider=event.provider,
                metadata=getattr(event, 'metadata', {})
            )
            image_item.add_description(desc)
            
            # Phase 3: Set processing state to completed
            image_item.processing_state = "completed"
            image_item.processing_error = None  # Clear any previous error
            
            self.mark_modified()
            self.refresh_image_list()
            
            # Update window title to reflect processing status (removes "Processing" when done)
            self.update_window_title("ImageDescriber", Path(self.workspace_file).name if self.workspace_file else "Untitled")
            
            # Update display if this is the current image
            if self.current_image_item == image_item:
                self.display_image_info(image_item)
            
            self.SetStatusText(f"Completed: {Path(event.file_path).name}", 0)
    
    def on_worker_failed(self, event):
        """Handle processing failures"""
        # Remove from processing items
        self.processing_items.pop(event.file_path, None)
        
        # Phase 3: Set processing state to failed and store error
        if event.file_path in self.workspace.items:
            image_item = self.workspace.items[event.file_path]
            image_item.processing_state = "failed"
            image_item.processing_error = event.error
            self.mark_modified()
        
        self.refresh_image_list()
        
        # Update window title to reflect processing status (removes "Processing" when failed)
        self.update_window_title("ImageDescriber", Path(self.workspace_file).name if self.workspace_file else "Untitled")
        
        # Ensure main window has focus before showing error dialog
        self.Raise()
        self.SetFocus()
        show_error(self, f"Processing failed for {Path(event.file_path).name}:\n{event.error}")
        # Restore focus after dialog
        self.SetFocus()
        self.SetStatusText(f"Error: {Path(event.file_path).name}", 0)
    
    def on_workflow_complete(self, event):
        """Handle workflow completion (including video extraction and downloads)"""
        logger.debug(f"on_workflow_complete called: input_dir={event.input_dir}, output_dir={event.output_dir}")
        logger.debug(f"_batch_video_extraction={getattr(self, '_batch_video_extraction', False)}")
        
        # Check if this is a download completion
        if hasattr(event, 'step_name') and event.step_name == "download":
            logger.info("Detected download completion")
            output_dir = Path(event.output_dir)
            
            # Close progress dialog
            if self.batch_progress_dialog:
                self.batch_progress_dialog.Close()
                self.batch_progress_dialog = None
            
            # Get all downloaded images
            valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff'}
            downloaded_images = sorted([
                f for f in output_dir.glob("*.*")
                if f.suffix.lower() in valid_extensions
            ])
            
            logger.debug(f"Found {len(downloaded_images)} downloaded images in {output_dir}")
            
            # Add all downloaded images to workspace (always add)
            for img_path in downloaded_images:
                item = ImageItem(str(img_path), "downloaded_image")
                item.download_url = event.input_dir  # Store source URL
                item.download_timestamp = datetime.now().isoformat()
                self.workspace.add_item(item)
            
            self.mark_modified()
            self.refresh_image_list()
            
            # Check if auto-processing is enabled
            process_after = False
            if hasattr(self, 'current_download_settings'):
                process_after = self.current_download_settings.get('process_after', False)
            
            # Clear download settings and worker
            if hasattr(self, 'current_download_settings'):
                del self.current_download_settings
            if hasattr(self, 'download_worker'):
                self.download_worker = None
            
            # If auto-process enabled, start batch processing
            if process_after and downloaded_images:
                # Use default settings for auto-processing (don't show dialog)
                self.auto_process_downloaded_images([str(img) for img in downloaded_images])
            else:
                # Show completion message only if not auto-processing
                # Reset window title to normal (download complete, no processing)
                doc_name = Path(self.workspace_file).name if self.workspace_file else "Untitled"
                self.update_window_title("ImageDescriber", doc_name)
                
                self.Raise()
                self.SetFocus()
                show_info(self, f"Downloaded {len(downloaded_images)} images from URL.\n\n"
                               f"Images saved to: {output_dir}")
                self.image_list.SetFocus()
            
            self.SetStatusText(f"Download complete: {len(downloaded_images)} images added", 0)
            return
        
        # Check if this is part of batch video extraction
        if hasattr(self, '_batch_video_extraction') and self._batch_video_extraction:
            logger.info("Detected batch video extraction completion")
            # Get extracted frames from output directory
            output_dir = Path(event.output_dir)
            extracted_frames = sorted([str(f) for f in output_dir.glob("*.jpg")])
            logger.debug(f"Found {len(extracted_frames)} extracted frames in {output_dir}")
            
            # Get video metadata from event if available
            video_metadata = event.video_metadata if hasattr(event, 'video_metadata') else None
            
            # Get the video path from input_dir (parent directory name)
            video_path = event.input_dir
            
            # Complete this video and move to next
            logger.debug(f"Calling _complete_batch_video_extraction for {video_path}")
            self._complete_batch_video_extraction(video_path, extracted_frames, video_metadata)
            return
        
        # Check if this was a manual video extraction
        if hasattr(self, 'last_extraction_settings') and self.last_extraction_settings:
            settings = self.last_extraction_settings
            video_path = settings['video_path']
            
            # Get list of extracted frames from output directory
            output_dir = Path(event.output_dir)
            extracted_frames = sorted([str(f) for f in output_dir.glob("*.jpg")])
            
            if extracted_frames:
                # Update parent video item
                if video_path in self.workspace.items:
                    video_item = self.workspace.items[video_path]
                    video_item.extracted_frames = extracted_frames
                    
                    # Store video metadata if available from event
                    if hasattr(event, 'video_metadata') and event.video_metadata:
                        video_item.video_metadata = event.video_metadata
                    
                    # Add extracted frames as individual items
                    for frame_path in extracted_frames:
                        if frame_path not in self.workspace.items:
                            frame_item = ImageItem(frame_path, "extracted_frame")
                            frame_item.parent_video = video_path
                            self.workspace.add_item(frame_item)
                    
                    self.mark_modified()
                    self.refresh_image_list()
                    
                    # If auto-process is enabled, start batch processing
                    if settings['process_after']:
                        self.auto_process_extracted_frames(extracted_frames)
                    else:
                        # Ensure main window has focus before showing dialog
                        self.Raise()
                        self.SetFocus()
                        show_info(self, f"Extracted {len(extracted_frames)} frames from video.\n\nFrames have been added to the workspace.")
                        # Restore focus to image list after dialog
                        self.image_list.SetFocus()
                
                self.SetStatusText(f"Extracted {len(extracted_frames)} frames", 0)
            
            # Clear extraction settings
            self.last_extraction_settings = None
            return
        
        # Phase 3: Clear batch state on successful completion
        if self.workspace.batch_state:
            self.workspace.batch_state = None
            
            # Reset item states (leave completed/failed as-is for history)
            for item in self.workspace.items.values():
                if item.processing_state in ["pending", "paused"]:
                    item.processing_state = None
                    item.batch_queue_position = None
        
        # Phase 3: Close progress dialog
        if self.batch_progress_dialog:
            self.batch_progress_dialog.Close()
            self.batch_progress_dialog = None
        
        # Phase 3: Clear worker reference
        self.batch_worker = None
        
        # Disable "Show Batch Progress" menu item
        if hasattr(self, 'show_batch_progress_item'):
            self.show_batch_progress_item.Enable(False)
        
        # Reset window title to normal (remove processing percentage)
        doc_name = Path(self.workspace_file).name if self.workspace_file else "Untitled"
        self.update_window_title("ImageDescriber", doc_name)
        
        # Save workspace
        if self.workspace_file:
            self.save_workspace(self.workspace_file)
        
        # Ensure main window has focus before showing completion dialog
        self.Raise()
        self.SetFocus()
        
        show_info(self, f"Workflow complete!\n{event.input_dir}")
        
        # Restore focus to image list after dialog dismissal
        self.image_list.SetFocus()
        
        self.SetStatusText("Workflow complete", 0)
        self.refresh_image_list()
    
    def on_workflow_failed(self, event):
        """Handle workflow failures"""
        # Ensure main window has focus before showing error dialog
        self.Raise()
        self.SetFocus()
        show_error(self, f"Workflow failed:\n{event.error}")
        # Restore focus to image list after dialog
        self.image_list.SetFocus()
        self.SetStatusText("Workflow failed", 0)
    
    # Phase 3: Batch control handlers
    def on_pause_batch(self):
        """Pause batch processing"""
        if not self.batch_worker:
            return
        
        self.batch_worker.pause()
        
        # Update title bar
        if self.batch_progress:
            current = self.batch_progress['current']
            total = self.batch_progress['total']
            percentage = int((current / total) * 100)
            doc_name = Path(self.workspace_file).name if self.workspace_file else "Untitled"
            self.SetTitle(f"(Paused) {percentage}%, {current} of {total} - ImageDescriber - {doc_name}")
        
        # Mark current item as paused
        if self.batch_progress and self.batch_progress.get('file_path'):
            file_path = self.batch_progress['file_path']
            if file_path in self.workspace.items:
                item = self.workspace.items[file_path]
                if item.processing_state == "pending":
                    item.processing_state = "paused"
        
        # Save workspace (preserves paused state)
        if self.workspace_file:
            self.save_workspace(self.workspace_file)
        
        self.SetStatusText("Batch processing paused", 0)
    
    def on_resume_batch(self):
        """Resume paused batch processing"""
        if not self.batch_worker:
            return
        
        self.batch_worker.resume()
        
        # Update title bar (remove "Paused")
        if self.batch_progress:
            current = self.batch_progress['current']
            total = self.batch_progress['total']
            percentage = int((current / total) * 100)
            doc_name = Path(self.workspace_file).name if self.workspace_file else "Untitled"
            self.SetTitle(f"{percentage}%, {current} of {total} - ImageDescriber - {doc_name}")
        
        # Unpause items
        for item in self.workspace.items.values():
            if item.processing_state == "paused":
                item.processing_state = "pending"
        
        self.SetStatusText("Batch processing resumed", 0)
    
    def on_show_batch_progress(self, event):
        """Show or raise the batch progress dialog"""
        if self.batch_progress_dialog:
            # Dialog exists - show and raise it
            if not self.batch_progress_dialog.IsShown():
                self.batch_progress_dialog.Show()
            self.batch_progress_dialog.Raise()
        else:
            # No dialog - shouldn't happen if menu item is properly disabled
            show_info(self, "No batch processing is currently running.")
    
    def on_stop_batch(self):
        """Stop batch processing permanently"""
        if not self.batch_worker:
            return
        
        # Call worker stop
        self.batch_worker.stop()
        
        # Clear batch state (won't resume automatically)
        self.workspace.batch_state = None
        
        # Reset item states (leave completed/failed as-is)
        for item in self.workspace.items.values():
            if item.processing_state in ["pending", "paused"]:
                item.processing_state = None
                item.batch_queue_position = None
        
        # Close progress dialog
        if self.batch_progress_dialog:
            self.batch_progress_dialog.Close()
            self.batch_progress_dialog = None
        
        # Save workspace
        if self.workspace_file:
            self.save_workspace(self.workspace_file)
        
        # Clear worker reference
        self.batch_worker = None
        
        # Disable "Show Batch Progress" menu item
        if hasattr(self, 'show_batch_progress_item'):
            self.show_batch_progress_item.Enable(False)
        
        # Reset window title to normal
        doc_name = Path(self.workspace_file).name if self.workspace_file else "Untitled"
        self.update_window_title("ImageDescriber", doc_name)
        
        self.SetStatusText("Batch processing stopped", 0)
        # Ensure main window has focus before showing dialog
        self.Raise()
        self.SetFocus()
        show_info(self, "Batch processing stopped.\n\nCompleted descriptions have been saved.")
        # Restore focus to image list after dialog
        self.image_list.SetFocus()
    
    # Phase 4: Resume functionality
    def prompt_resume_batch(self):
        """Show dialog to resume interrupted batch"""
        batch_state = self.workspace.batch_state
        
        # Count remaining items
        pending_items = [
            item for item in self.workspace.items.values()
            if item.processing_state in ["pending", "paused"]
        ]
        
        if not pending_items:
            # No items to resume - clear stale batch state
            self.workspace.batch_state = None
            return
        
        total = batch_state.get('total_queued', len(pending_items))
        completed = total - len(pending_items)
        
        message = (
            f"Resume batch processing?\n\n"
            f"Progress: {completed} of {total} images completed\n"
            f"Remaining: {len(pending_items)} images\n\n"
            f"Provider: {batch_state.get('provider', 'Unknown')}\n"
            f"Model: {batch_state.get('model', 'Unknown')}\n"
            f"Prompt: {batch_state.get('prompt_style', 'Unknown')}"
        )
        
        result = ask_yes_no(self, message)
        
        if result:
            self.resume_batch_processing()
        else:
            # User declined - clear batch state
            self.workspace.batch_state = None
            for item in self.workspace.items.values():
                if item.processing_state in ["pending", "paused"]:
                    item.processing_state = None
                    item.batch_queue_position = None
            if self.workspace_file:
                self.save_workspace(self.workspace_file)
    
    def resume_batch_processing(self):
        """Resume batch processing from saved state"""
        if not self.workspace.batch_state:
            return
        
        batch_state = self.workspace.batch_state
        
        # Collect items to process (pending or paused only)
        to_process_items = [
            item for item in self.workspace.items.values()
            if item.processing_state in ["pending", "paused"]
        ]
        
        # Sort by queue position to maintain original order
        to_process_items.sort(key=lambda item: item.batch_queue_position or 0)
        
        # Extract file paths
        file_paths = [item.file_path for item in to_process_items]
        
        if not file_paths:
            show_info(self, "No images to resume processing.")
            self.workspace.batch_state = None
            return
        
        # Recreate processing options from batch state
        provider = batch_state['provider']
        model = batch_state['model']
        prompt_style = batch_state.get('prompt_style', 'default')
        custom_prompt = batch_state.get('custom_prompt')
        detection_settings = batch_state.get('detection_settings')
        
        # Get prompt config path
        from shared.wx_common import find_config_file
        prompt_config_path = find_config_file('image_describer_config.json')
        
        # Reset items to pending (from paused)
        for item in to_process_items:
            item.processing_state = "pending"
        
        # Start worker - STORE REFERENCE
        self.batch_worker = BatchProcessingWorker(
            parent_window=self,
            file_paths=file_paths,
            provider=provider,
            model=model,
            prompt_style=prompt_style,
            custom_prompt=custom_prompt,
            detection_settings=detection_settings,
            prompt_config_path=str(prompt_config_path) if prompt_config_path else None,
            skip_existing=True  # Always skip completed
        )
        self.batch_worker.start()
        
        # Show progress dialog (starting from resumed position)
        total = batch_state.get('total_queued', len(file_paths))
        if BatchProgressDialog:
            self.batch_progress_dialog = BatchProgressDialog(self, total)
            self.batch_progress_dialog.Show()
            # Enable "Show Batch Progress" menu item
            if hasattr(self, 'show_batch_progress_item'):
                self.show_batch_progress_item.Enable(True)
        
        # Initialize timing
        self.batch_start_time = time.time()
        self.batch_processing_times = []
        
        self.SetStatusText(f"Resuming batch: {len(file_paths)} images remaining...", 0)
    
    def on_extract_video(self, event):
        """Extract frames from video file"""
        if not VideoProcessingWorker:
            show_error(self, "Video processing not available (OpenCV not installed)")
            return
        
        # Check if cv2 is available
        if not cv2:
            error_msg = ("OpenCV (cv2) is not installed.\n\n"
                        "Video frame extraction requires OpenCV.\n"
                        "Please install it with: pip install opencv-python")
            show_error(self, error_msg)
            return
        
        # Check if we have a selected video in the workspace
        selected_video = None
        if self.current_image_item and self.current_image_item.item_type == "video":
            selected_video = self.current_image_item.file_path
        
        # If no video selected, or want to process a different video
        if not selected_video:
            # Select video file
            file_path = open_file_dialog(
                self,
                "Select Video File",
                "Video files (*.mp4;*.mov;*.avi;*.mkv)|*.mp4;*.mov;*.avi;*.mkv|All files (*.*)|*.*",
                "",
                ""
            )
            
            if not file_path:
                return
            
            selected_video = file_path
            
            # Add video to workspace if not already present
            if selected_video not in self.workspace.items:
                item = ImageItem(selected_video, "video")
                self.workspace.add_item(item)
                self.refresh_image_list()
                self.mark_modified()
        
        # Show extraction dialog
        dialog = VideoExtractionDialog(self, selected_video)
        if dialog.ShowModal() != wx.ID_OK:
            dialog.Destroy()
            return
        
        settings = dialog.get_settings()
        process_after = settings.pop('process_after_extraction')
        dialog.Destroy()
        
        # Load defaults from config file, then overlay dialog settings
        try:
            from config_loader import load_json_config
            video_config, _, _ = load_json_config('video_frame_extractor_config.json')
            if video_config:
                extraction_config = {
                    # Defaults from config file
                    "start_time_seconds": video_config.get("start_time_seconds", 0),
                    "end_time_seconds": video_config.get("end_time_seconds"),
                    "time_interval_seconds": video_config.get("time_interval_seconds", 5.0),
                    "scene_change_threshold": video_config.get("scene_change_threshold", 30.0),
                    "min_scene_duration_seconds": video_config.get("min_scene_duration_seconds", 1.0),
                    **settings  # Dialog settings override config file
                }
            else:
                raise Exception("Config not loaded")
        except Exception:
            # Fallback to hardcoded defaults
            extraction_config = {
                "start_time_seconds": 0,
                "end_time_seconds": None,
                "time_interval_seconds": 5.0,
                "scene_change_threshold": 30.0,
                "min_scene_duration_seconds": 1.0,
                **settings
            }
        
        # Store settings for potential auto-processing
        self.last_extraction_settings = {
            'video_path': selected_video,
            'process_after': process_after,
            'extraction_config': extraction_config
        }
        
        # Start extraction worker
        self.video_worker = VideoProcessingWorker(self, selected_video, extraction_config)
        self.video_worker.start()
        
        self.SetStatusText(f"Extracting frames from: {Path(selected_video).name}...", 0)
    
    def auto_process_downloaded_images(self, image_paths: List[str]):
        """Auto-process downloaded images using default settings (no dialog)
        
        Args:
            image_paths: List of downloaded image file paths
        """
        # Use default settings from config
        options = {
            'provider': self.config.get('default_provider', 'ollama'),
            'model': self.config.get('default_model', 'moondream'),
            'prompt_style': self.config.get('default_prompt_style', 'narrative'),
            'custom_prompt': '',
            'skip_existing': True
        }
        
        logger.info(f"Auto-processing {len(image_paths)} downloaded images with defaults: {options['provider']}/{options['model']}")
        
        # Mark images as pending for batch processing
        for i, img_path in enumerate(image_paths):
            if img_path in self.workspace.items:
                img_item = self.workspace.items[img_path]
                img_item.processing_state = "pending"
                img_item.batch_queue_position = i
        
        # Create batch state
        self.workspace.batch_state = {
            "provider": options['provider'],
            "model": options['model'],
            "prompt_style": options['prompt_style'],
            "custom_prompt": options.get('custom_prompt'),
            "detection_settings": None,
            "total_queued": len(image_paths),
            "started": datetime.now().isoformat()
        }
        
        # Prepare images for processing
        to_process = []
        for img_path in image_paths:
            if img_path in self.workspace.items:
                img_item = self.workspace.items[img_path]
                # Skip if already has descriptions and skip_existing is True
                if options.get('skip_existing', True) and img_item.descriptions:
                    logger.debug(f"Skipping {Path(img_path).name} - already has description")
                    continue
                to_process.append(img_path)
        
        if not to_process:
            logger.info("No images to process (all already described)")
            show_info(self, "All downloaded images already have descriptions!")
            return
        
        # Show batch progress dialog
        if BatchProgressDialog:
            self.batch_progress_dialog = BatchProgressDialog(self, total_images=len(to_process))
            self.batch_progress_dialog.Show()
        
        # Get API key for the provider
        api_key = self.get_api_key_for_provider(options['provider'])
        
        # Start batch processing worker
        self.batch_worker = BatchProcessingWorker(
            self,
            to_process,
            options['provider'],
            options['model'],
            options['prompt_style'],
            options.get('custom_prompt', ''),
            None,  # detection_settings
            None,  # prompt_config_path
            options.get('skip_existing', True),
            progress_offset=0
        )
        self.batch_worker.start()
        
        # Initialize timing
        self.batch_start_time = time.time()
        self.batch_processing_times = []
        
        # Save workspace
        if self.workspace_file:
            self.save_workspace(self.workspace_file)
        
        self.SetStatusText(f"Processing {len(to_process)} downloaded images...", 0)
    
    def auto_process_extracted_frames(self, frame_paths: List[str]):
        """Auto-process extracted frames using default settings
        
        Args:
            frame_paths: List of extracted frame file paths
        """
        if not ProcessingOptionsDialog:
            show_error(self, "Processing dialog not available")
            return
        
        # Show processing options dialog
        dialog = ProcessingOptionsDialog(self.config, cached_ollama_models=self.cached_ollama_models, parent=self)
        if dialog.ShowModal() != wx.ID_OK:
            dialog.Destroy()
            # Ensure main window has focus before showing dialog
            self.Raise()
            self.SetFocus()
            show_info(self, f"Extraction complete! {len(frame_paths)} frames added to workspace.\n\nYou can process them later with 'Process All Undescribed'.")
            # Restore focus after dialog
            self.SetFocus()
            return
        
        options = dialog.get_config()
        dialog.Destroy()
        
        # Start batch processing for frames
        from shared.wx_common import find_config_file
        prompt_config_path = find_config_file('image_describer_config.json')
        
        # Mark frames as pending for batch processing
        for i, frame_path in enumerate(frame_paths):
            if frame_path in self.workspace.items:
                frame_item = self.workspace.items[frame_path]
                frame_item.processing_state = "pending"
                frame_item.batch_queue_position = i
        
        # Create batch state
        self.workspace.batch_state = {
            "provider": options['provider'],
            "model": options['model'],
            "prompt_style": options.get('prompt_style', 'default'),
            "custom_prompt": options.get('custom_prompt'),
            "detection_settings": options.get('detection_settings'),
            "total_queued": len(frame_paths),
            "started": datetime.now().isoformat()
        }
        
        # Start batch worker
        self.batch_worker = BatchProcessingWorker(
            parent_window=self,
            file_paths=frame_paths,
            provider=options['provider'],
            model=options['model'],
            prompt_style=options.get('prompt_style', 'default'),
            custom_prompt=options.get('custom_prompt'),
            detection_settings=options.get('detection_settings'),
            prompt_config_path=str(prompt_config_path) if prompt_config_path else None,
            skip_existing=True
        )
        self.batch_worker.start()
        
        # Show progress dialog
        if BatchProgressDialog:
            self.batch_progress_dialog = BatchProgressDialog(self, len(frame_paths))
            self.batch_progress_dialog.Show()
            # Enable "Show Batch Progress" menu item
            if hasattr(self, 'show_batch_progress_item'):
                self.show_batch_progress_item.Enable(True)
        
        # Initialize timing
        self.batch_start_time = time.time()
        self.batch_processing_times = []
        
        self.SetStatusText(f"Processing {len(frame_paths)} extracted frames...", 0)
    
    def on_description_complete(self, event):
        """Handle description completion from worker thread (legacy)"""
        pass
    
    def on_processing_progress(self, event):
        """Handle processing progress updates (legacy)"""
        pass
    
    def on_processing_error(self, event):
        """Handle processing errors (legacy)"""
        pass
    
    def on_key_press(self, event):
        """Handle keyboard shortcuts (matching Qt6 behavior)"""
        keycode = event.GetKeyCode()
        modifiers = event.GetModifiers()
        
        # Single-key shortcuts (no modifiers)
        if modifiers == wx.MOD_NONE:
            if keycode == ord('P'):
                # Process selected image
                self.on_process_single(event)
                return
            elif keycode == ord('R'):
                # Rename item
                self.on_rename_item(event)
                return
            elif keycode == ord('M'):
                # Add manual description
                self.on_add_manual_description(event)
                return
            elif keycode == ord('C'):
                # Chat with AI
                self.on_chat(event)
                return
            elif keycode == ord('F'):
                # Followup question
                self.on_followup_question(event)
                return
            elif keycode == ord('Z'):
                # Auto-rename (hidden feature)
                self.on_auto_rename(event)
                return
            elif keycode == wx.WXK_F2:
                # Rename (alternative)
                self.on_rename_item(event)
                return
        
        # Ctrl+V for paste
        elif modifiers == wx.MOD_CONTROL and keycode == ord('V'):
            self.on_paste_from_clipboard(event)
            return
        
        # Let event propagate if not handled
        event.Skip()
    
    def on_rename_item(self, event):
        """Rename selected item (R key or F2)"""
        if not self.current_image_item:
            show_warning(self, "No image selected")
            return
        
        # Get current name
        current_name = self.current_image_item.display_name or Path(self.current_image_item.file_path).stem
        
        # Show input dialog
        dlg = wx.TextEntryDialog(
            self,
            "Enter new display name:",
            "Rename Item",
            current_name
        )
        
        if dlg.ShowModal() == wx.ID_OK:
            new_name = dlg.GetValue().strip()
            if new_name:
                self.current_image_item.display_name = new_name
                self.mark_modified()
                self.refresh_image_list()
                self.SetStatusText(f"Renamed to: {new_name}", 0)
        
        dlg.Destroy()
    
    def on_add_manual_description(self, event):
        """Add manual description (M key)"""
        if not self.current_image_item:
            show_warning(self, "No image selected")
            return
        
        # Show multi-line text dialog
        dlg = wx.TextEntryDialog(
            self,
            "Enter description for this image:",
            "Add Manual Description",
            "",
            style=wx.OK | wx.CANCEL | wx.TE_MULTILINE
        )
        dlg.SetSize((500, 300))
        
        if dlg.ShowModal() == wx.ID_OK:
            text = dlg.GetValue().strip()
            if text:
                desc = ImageDescription(
                    text=text,
                    model="manual",
                    prompt_style="manual"
                )
                self.current_image_item.add_description(desc)
                self.mark_modified()
                self.display_image_info(self.current_image_item)
                self.SetStatusText("Manual description added", 0)
        
        dlg.Destroy()
    
    def on_chat(self, event):
        """Chat with AI (C key) - General purpose AI chat, no image required"""
        # Check if chat feature is available
        if ChatDialog is None or ChatWindow is None:
            show_error(self, "Chat feature is not available. The chat_window_wx module could not be loaded.")
            return
        
        try:
            # Show provider selection dialog (pass cached Ollama models for performance)
            chat_dialog = ChatDialog(self, self.config, cached_ollama_models=self.cached_ollama_models)
            if chat_dialog.ShowModal() == wx.ID_OK:
                selections = chat_dialog.get_selections()
                chat_dialog.Destroy()
                
                # Open chat window with selected settings (no image required)
                chat_window = ChatWindow(
                    parent=self,
                    workspace=self.workspace,
                    image_item=None,  # Chat doesn't require an image
                    provider=selections['provider'],
                    model=selections['model']
                )
                chat_window.ShowModal()
                chat_window.Destroy()
                
                # TODO: Refresh image list to show new chat session
                # self.load_workspace()  # This will reload all items including new chat
            else:
                chat_dialog.Destroy()
        except Exception as e:
            import traceback
            error_msg = f"Error opening chat:\n{str(e)}\n\n{traceback.format_exc()}"
            show_error(self, error_msg)
    
    def on_followup_question(self, event):
        """Ask followup question (F key)"""
        if not self.current_image_item:
            show_warning(self, "No image selected")
            return
        
        if not self.current_image_item.descriptions:
            show_info(self, "No existing description. Use 'P' to process first, or 'C' for chat.")
            return
        
        if not ProcessingWorker:
            show_error(self, "Processing worker not available")
            return
        
        # Get existing description for context
        last_description = self.current_image_item.descriptions[-1]
        existing_desc = last_description.text
        
        # Get original provider and model from the description
        # Default to config values if not stored in description
        original_provider = last_description.provider or self.config.get('default_provider', 'ollama')
        original_model = last_description.model or self.config.get('default_model', 'moondream')
        
        # Show dialog with model selection
        from dialogs_wx import FollowupQuestionDialog
        
        dlg = FollowupQuestionDialog(
            self,
            original_provider,
            original_model,
            existing_desc[:300] + ("..." if len(existing_desc) > 300 else ""),
            self.config
        )
        
        if dlg.ShowModal() == wx.ID_OK:
            values = dlg.get_values()
            question = values['question']
            
            if question:
                # Create prompt with context
                context_prompt = f"Previous description: {existing_desc}\n\nFollowup question: {question}"
                
                self.SetStatusText(f"Processing followup with {values['provider']}/{values['model']}...", 0)
                
                # Process with AI using selected model
                api_key = self.get_api_key_for_provider(values['provider'])
                worker = ProcessingWorker(
                    self,
                    self.current_image_item.file_path,
                    values['provider'],
                    values['model'],
                    'followup',
                    context_prompt,
                    None,
                    None,
                    api_key  # API key for cloud providers
                )
                worker.start()
        
        dlg.Destroy()
    
    def on_auto_rename(self, event):
        """Auto-rename using AI (Z key)"""
        if not self.current_image_item:
            show_warning(self, "No image selected")
            return
        
        if not ProcessingWorker:
            show_error(self, "Processing worker not available")
            return
        
        # Ask user to confirm
        if not ask_yes_no(self, "Generate a descriptive name for this image using AI?\n\nThis will use your default AI provider."):
            return
        
        # Use a special prompt for generating names
        rename_prompt = "Generate a short, descriptive filename for this image (2-5 words, no file extension). Be specific and concise."
        
        # Process with default settings
        options = {
            'provider': self.config.get('default_provider', 'ollama'),
            'model': self.config.get('default_model', 'moondream'),
        }
        
        self.SetStatusText("Generating name with AI...", 0)
        
        # Use processing worker but capture result for renaming
        try:
            # For now, show that the feature is available but needs completion
            show_info(self, "AI auto-rename is being processed.\n\nThe generated name will appear as a description.\nYou can then manually rename using that suggestion.")
            
            # Process to get description that could be used as name
            api_key = self.get_api_key_for_provider(options['provider'])
            worker = ProcessingWorker(
                self,
                self.current_image_item.file_path,
                options['provider'],
                options['model'],
                'brief',  # Use brief prompt style
                rename_prompt,
                None,
                None,
                api_key  # API key for cloud providers
            )
            worker.start()
        except Exception as e:
            show_error(self, f"Auto-rename failed: {str(e)}")
    
    def on_paste_from_clipboard(self, event):
        """Paste image from clipboard (Ctrl+V)"""
        if not self.workspace:
            self.workspace = ImageWorkspace(new_workspace=True)
        
        if wx.TheClipboard.Open():
            try:
                bitmap = None
                
                # Try multiple clipboard formats (in order of preference)
                # 1. Try DIB format first (Device Independent Bitmap - common on Windows)
                if wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_DIB)):
                    data = wx.BitmapDataObject()
                    if wx.TheClipboard.GetData(data):
                        bitmap = data.GetBitmap()
                
                # 2. Try standard bitmap format
                if not bitmap and wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_BITMAP)):
                    data = wx.BitmapDataObject()
                    if wx.TheClipboard.GetData(data):
                        bitmap = data.GetBitmap()
                
                # 3. Try file list (if user copied a file)
                if not bitmap and wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_FILENAME)):
                    file_data = wx.FileDataObject()
                    if wx.TheClipboard.GetData(file_data):
                        filenames = file_data.GetFilenames()
                        if filenames:
                            # Use the first file if it's an image
                            first_file = Path(filenames[0])
                            if first_file.suffix.lower() in {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.heic'}:
                                # Add the file directly instead of creating a copy
                                item = ImageItem(str(first_file))
                                self.workspace.add_item(item)
                                self.mark_modified()
                                self.refresh_image_list()
                                self.SetStatusText(f"Pasted image from clipboard: {first_file.name}", 0)
                                wx.TheClipboard.Close()
                                return
                
                if bitmap:
                    # Convert to image
                    image = bitmap.ConvertToImage()
                    
                    # Save to temporary file
                    import tempfile
                    import datetime
                    
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    temp_path = Path(tempfile.gettempdir()) / f"clipboard_image_{timestamp}.png"
                    
                    if image.SaveFile(str(temp_path), wx.BITMAP_TYPE_PNG):
                        # Add to workspace
                        item = ImageItem(str(temp_path))
                        item.display_name = f"Clipboard_{timestamp}"
                        self.workspace.add_item(item)
                        
                        self.mark_modified()
                        self.refresh_image_list()
                        self.SetStatusText(f"Pasted image from clipboard: {item.display_name}", 0)
                    else:
                        show_error(self, "Failed to save clipboard image")
                else:
                    show_warning(self, "Clipboard does not contain an image")
            finally:
                wx.TheClipboard.Close()
        else:
            show_error(self, "Could not access clipboard")
    
    # Workspace menu handlers
    # Process menu handlers (additional)
    def refresh_ollama_models(self):
        """Refresh cached Ollama models from the system"""
        try:
            from ai_providers import get_available_providers
            providers = get_available_providers()
            if 'ollama' in providers:
                ollama_provider = providers['ollama']
                models = ollama_provider.get_available_models()
                self.cached_ollama_models = models
                # Also update workspace cache
                if self.workspace:
                    self.workspace.cached_ollama_models = models
                return models
            else:
                self.cached_ollama_models = []
                if self.workspace:
                    self.workspace.cached_ollama_models = []
                return []
        except Exception as e:
            self.SetStatusText(f"Error refreshing models: {e}", 0)
            self.cached_ollama_models = None
            if self.workspace:
                self.workspace.cached_ollama_models = None
            return None
    
    def refresh_ai_models_silent(self):
        """Silently refresh AI model cache on startup (no dialogs)"""
        try:
            self.refresh_ollama_models()
        except Exception:
            pass  # Silent failure on startup
    
    def on_refresh_ai_models(self, event):
        """Handle menu item to refresh AI model cache"""
        wx.BeginBusyCursor()
        try:
            models = self.refresh_ollama_models()
            if models is not None:
                count = len(models)
                model_list = "\\n".join(models) if models else "No Ollama models found"
                show_info(self, f"Successfully refreshed {count} Ollama model(s):\\n\\n{model_list}")
                self.SetStatusText(f"Refreshed {count} Ollama model(s)", 0)
            else:
                show_warning(self, "Failed to refresh models", "Could not connect to Ollama. Make sure it's running.")
        finally:
            wx.EndBusyCursor()
    
    def on_convert_heic(self, event):
        """Convert HEIC files to JPEG format"""
        if not self.workspace or not self.workspace.items:
            show_warning(self, "No images in workspace")
            return
        
        # Find HEIC files
        heic_files = [item.file_path for item in self.workspace.items.values()
                      if Path(item.file_path).suffix.lower() in ['.heic', '.heif']]
        
        if not heic_files:
            show_info(self, "No HEIC files found in workspace")
            return
        
        msg = f"Found {len(heic_files)} HEIC file(s).\n\nConvert to JPEG format?\n\n"
        msg += "Note: Original HEIC files will be preserved. JPG copies will be created in the same directory."
        if not ask_yes_no(self, msg):
            return
        
        # Start HEIC conversion worker
        if HEICConversionWorker:
            worker = HEICConversionWorker(self, heic_files, quality=95)
            worker.start()
            self.SetStatusText(f"Converting {len(heic_files)} HEIC files...", 0)
        else:
            show_error(self, "HEIC conversion worker not available")
    
    def on_conversion_complete(self, event):
        """Handle HEIC conversion completion"""
        converted_count = event.converted_count
        failed_count = event.failed_count
        converted_files = event.converted_files
        
        # Reload workspace to include newly converted JPG files
        if converted_count > 0:
            # Add converted JPG files to workspace
            for jpg_path in converted_files:
                if jpg_path not in self.workspace.items:
                    from data_models import ImageItem
                    new_item = ImageItem(file_path=jpg_path)
                    self.workspace.items[jpg_path] = new_item
            
            # NOTE: HEIC files are preserved in workspace
            # Users can manually remove them if desired
            
            self.mark_modified()
            self.refresh_image_list()
        
        # Show completion message
        if failed_count == 0:
            msg = f"Successfully converted {converted_count} HEIC file(s) to JPEG"
            # Ensure main window has focus before showing dialog
            self.Raise()
            self.SetFocus()
            show_info(self, msg)
            # Restore focus after dialog
            self.SetFocus()
            self.SetStatusText(msg, 0)
        else:
            msg = f"Converted {converted_count} file(s), {failed_count} failed"
            # Ensure main window has focus before showing dialog
            self.Raise()
            self.SetFocus()
            show_warning(self, msg + f"\n\nFailed files:\n" + "\n".join(event.failed_files))
            # Restore focus after dialog
            self.SetFocus()
            self.SetStatusText(msg, 0)
    
    def on_conversion_failed(self, event):
        """Handle HEIC conversion failure"""
        error_msg = f"HEIC conversion failed: {event.error}"
        # Ensure main window has focus before showing error dialog
        self.Raise()
        self.SetFocus()
        show_error(self, error_msg)
        # Restore focus after dialog
        self.SetFocus()
        self.SetStatusText("Conversion failed", 0)
    
    # Descriptions menu handlers
    def on_edit_description(self, event):
        """Edit selected description"""
        if not self.current_image_item or not self.current_image_item.descriptions:
            show_warning(self, "No description to edit")
            return
        
        # Get the latest description
        desc = self.current_image_item.descriptions[-1]
        
        dlg = wx.TextEntryDialog(
            self,
            "Edit description:",
            "Edit Description",
            desc.text,
            style=wx.OK | wx.CANCEL | wx.TE_MULTILINE
        )
        dlg.SetSize((500, 300))
        
        if dlg.ShowModal() == wx.ID_OK:
            new_text = dlg.GetValue().strip()
            if new_text:
                desc.text = new_text
                self.mark_modified()
                self.display_image_info(self.current_image_item)
                self.SetStatusText("Description updated", 0)
        
        dlg.Destroy()
    
    def on_delete_description(self, event):
        """Delete selected description"""
        if not self.current_image_item or not self.current_image_item.descriptions:
            show_warning(self, "No description to delete")
            return
        
        if ask_yes_no(self, "Delete the most recent description?"):
            self.current_image_item.descriptions.pop()
            self.mark_modified()
            self.display_image_info(self.current_image_item)
            self.SetStatusText("Description deleted", 0)
    
    def on_copy_description(self, event):
        """Copy description to clipboard"""
        if not self.current_image_item or not self.current_image_item.descriptions:
            show_warning(self, "No description to copy")
            return
        
        desc = self.current_image_item.descriptions[-1].text
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(desc))
            wx.TheClipboard.Close()
            self.SetStatusText("Description copied to clipboard", 0)
    
    def on_copy_image_path(self, event):
        """Copy image path to clipboard"""
        if not self.current_image_item:
            show_warning(self, "No image selected")
            return
        
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(self.current_image_item.file_path))
            wx.TheClipboard.Close()
            self.SetStatusText("Image path copied to clipboard", 0)
    
    def on_show_all_descriptions(self, event):
        """Show all descriptions across all images"""
        if not self.workspace or not self.workspace.items:
            show_warning(self, "No images in workspace")
            return
        
        # Count images with descriptions
        described = [item for item in self.workspace.items.values() if item.descriptions]
        
        if not described:
            show_info(self, "No descriptions found in workspace")
            return
        
        # Build description summary
        summary_lines = []
        summary_lines.append(f"Descriptions Summary ({len(described)} of {len(self.workspace.items)} images)\n")
        summary_lines.append("=" * 60 + "\n\n")
        
        for item in described:
            summary_lines.append(f"File: {Path(item.file_path).name}\n")
            for i, desc in enumerate(item.descriptions, 1):
                summary_lines.append(f"  [{i}] {desc.model} ({desc.prompt_style}): {desc.text[:100]}...\n")
            summary_lines.append("\n")
        
        summary_text = "".join(summary_lines)
        
        # Show in a text dialog
        dlg = wx.Dialog(self, title="All Descriptions", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        dlg.SetSize((700, 500))
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        text_ctrl = wx.TextCtrl(dlg, value=summary_text, 
                               style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP)
        sizer.Add(text_ctrl, 1, wx.ALL | wx.EXPAND, 10)
        
        btn_sizer = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(dlg, wx.ID_OK)
        btn_sizer.AddButton(ok_btn)
        btn_sizer.Realize()
        sizer.Add(btn_sizer, 0, wx.ALL | wx.ALIGN_RIGHT, 10)
        
        dlg.SetSizer(sizer)
        dlg.Centre()
        dlg.ShowModal()
        dlg.Destroy()
    
    # View menu handlers
    def on_set_filter(self, filter_type):
        """Set view filter (all, described, undescribed)"""
        self.current_filter = filter_type
        self.refresh_image_list()
        self.SetStatusText(f"Filter: {filter_type}", 1)
    
    def on_toggle_image_previews(self, event):
        """Toggle image preview panel visibility"""
        self.show_image_previews = event.IsChecked()
        
        if self.show_image_previews:
            self.image_preview_label.Show()
            self.image_preview_panel.Show()
        else:
            self.image_preview_label.Hide()
            self.image_preview_panel.Hide()
        
        # Refresh layout
        self.Layout()
    
    # ========== Tools Menu Handlers ==========
    
    def on_edit_prompts(self, event):
        """Launch the Prompt Editor dialog"""
        if not PromptEditorDialog:
            show_error(self, "Prompt Editor module not available.\n\nThis may be a build configuration issue.")
            return
        
        try:
            dialog = PromptEditorDialog(self)
            dialog.ShowModal()
            dialog.Destroy()
            
            # Refresh cached data after editing
            self.cached_ollama_models = None  # Force reload on next use
            
            # Verify config file is readable after editing
            try:
                from shared.wx_common import find_config_file
                config_path = find_config_file('image_describer_config.json')
                if config_path and config_path.exists():
                    import json
                    with open(config_path, 'r', encoding='utf-8') as f:
                        cfg = json.load(f)
                    prompts = cfg.get('prompt_variations', {})
                    default = cfg.get('default_prompt_style', 'N/A')
                    logging.info(f"Config verified after prompt edit: {len(prompts)} prompts, default={default}")
                else:
                    logging.warning("Config file not found after prompt editor closed")
            except Exception as verify_error:
                logging.error(f"Failed to verify config after prompt edit: {verify_error}")
            
        except Exception as e:
            show_error(self, f"Error launching Prompt Editor:\n{e}")
    
    def on_configure_settings(self, event):
        """Launch the Configure Settings dialog"""
        if not ConfigureDialog:
            show_error(self, "Configure Settings module not available.\n\nThis may be a build configuration issue.")
            return
        
        try:
            dialog = ConfigureDialog(self)
            dialog.ShowModal()
            dialog.Destroy()
            
            # Refresh cached settings after editing
            self.cached_ollama_models = None  # Force reload on next use
            
        except Exception as e:
            show_error(self, f"Error launching Configure Settings:\n{e}")
    
    def on_export_configuration(self, event):
        """Export all configuration files as backup"""
        try:
            from datetime import datetime
            import shutil
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"idt_config_backup_{timestamp}.zip"
            
            file_path = save_file_dialog(
                self,
                "Export Configuration",
                wildcard="ZIP files (*.zip)|*.zip",
                default_file=default_name
            )
            
            if not file_path:
                return
            
            # Find scripts directory
            scripts_dir = find_scripts_directory()
            if not scripts_dir or not scripts_dir.exists():
                show_error(self, "Could not find scripts directory.")
                return
            
            # Create ZIP with all config files
            import zipfile
            with zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for config_file in ['image_describer_config.json', 'video_frame_extractor_config.json', 'workflow_config.json']:
                    config_path = scripts_dir / config_file
                    if config_path.exists():
                        zipf.write(config_path, config_file)
                
                # Also include geocode cache if it exists
                geocode_cache = scripts_dir / 'geocode_cache.json'
                if geocode_cache.exists():
                    zipf.write(geocode_cache, 'geocode_cache.json')
            
            show_info(self, f"Configuration exported successfully to:\n{file_path}")
            
        except Exception as e:
            show_error(self, f"Error exporting configuration:\n{e}")
    
    def on_import_configuration(self, event):
        """Import configuration files from backup"""
        try:
            file_path = open_file_dialog(
                self,
                "Import Configuration",
                wildcard="ZIP files (*.zip)|*.zip"
            )
            
            if not file_path:
                return
            
            # Confirm before overwriting
            if not ask_yes_no(self, "This will replace your current configuration files.\n\nContinue?", "Import Configuration"):
                return
            
            # Find scripts directory
            scripts_dir = find_scripts_directory()
            if not scripts_dir or not scripts_dir.exists():
                show_error(self, "Could not find scripts directory.")
                return
            
            # Extract ZIP
            import zipfile
            imported_count = 0
            with zipfile.ZipFile(file_path, 'r') as zipf:
                for filename in zipf.namelist():
                    if filename.endswith('.json'):
                        zipf.extract(filename, scripts_dir)
                        imported_count += 1
            
            if imported_count > 0:
                show_info(self, f"Successfully imported {imported_count} configuration file(s).\n\nRestart ImageDescriber to use the new settings.")
            else:
                show_warning(self, "No configuration files found in the selected archive.")
            
        except Exception as e:
            show_error(self, f"Error importing configuration:\n{e}")
    
    # ========== Help Menu Handlers ==========
    
    def on_user_guide(self, event):
        """Open user guide in web browser"""
        user_guide_url = "https://github.com/kellylford/Image-Description-Toolkit/blob/main/docs/USER_GUIDE_V4.md"
        try:
            webbrowser.open(user_guide_url)
        except Exception as e:
            show_error(self, f"Could not open user guide:\n{e}")
    
    def on_about(self, event=None):
        """Show about dialog with version and feature information"""
        try:
            show_about_dialog(
                self,
                "ImageDescriber",
                get_app_version(),
                "AI-Powered Image Description GUI\n\n"
                "Features:\n"
                "• Document-based workspace for project management\n"
                "• Individual and batch image processing\n"
                "• Multiple AI providers (Ollama, OpenAI, Claude)\n"
                "• Video frame extraction with nested display\n"
                "• HEIC image conversion support\n"
                "• Integrated viewer mode for browsing workflow results\n"
                "• Integrated prompt editor and configuration manager",
                developers=["Kelly Ford"],
                website="https://github.com/kellylford/Image-Description-Toolkit"
            )
        except Exception as e:
            logging.error(f"Error showing About dialog: {e}", exc_info=True)
            show_error(self, f"Could not show About dialog:\n{e}")
    
    def on_close(self, event):
        """Handle application close"""
        if self.confirm_unsaved_changes():
            # Clean up empty Untitled workspaces before closing
            if is_untitled_workspace(self.workspace_file.stem):
                # Check if workspace is empty (no items or only empty directories)
                if not self.workspace.items or len(self.workspace.items) == 0:
                    try:
                        # Delete workspace data directory
                        data_dir = get_workspace_files_directory(self.workspace_file)
                        if data_dir.exists():
                            import shutil
                            shutil.rmtree(data_dir)
                        
                        # Delete IDW file
                        if self.workspace_file.exists():
                            self.workspace_file.unlink()
                            
                        logger.info(f"Cleaned up empty Untitled workspace: {self.workspace_file.name}")
                    except Exception as e:
                        logger.warning(f"Failed to clean up Untitled workspace: {e}")
            
            self.Destroy()
        elif event.CanVeto():
            event.Veto()
    
    def on_save(self, event):
        """Wrapper for ModifiedStateMixin"""
        self.on_save_workspace(event)


def main():
    """Main application entry point"""
    import argparse
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Image Describer Tool")
    parser.add_argument('path', nargs='?', help="Directory or workspace to load")
    parser.add_argument('--viewer', action='store_true', help="Start in viewer mode")
    parser.add_argument('--debug', action='store_true', 
                       help='Enable verbose debug logging to file')
    parser.add_argument('--debug-file', 
                       default=str(Path.home() / 'imagedescriber_verbose_debug.log'),
                       help='Debug output file location (default: %(default)s)')
    args = parser.parse_args()
    
    # Check for debug mode via command-line flag OR environment variable
    debug_mode = args.debug or os.environ.get('IDT_DEBUG', '').lower() in ('1', 'true', 'yes')
    
    # Determine log file location - executable directory for frozen, CWD for dev
    if getattr(sys, 'frozen', False):
        # Frozen executable - put log next to the .exe
        exe_dir = Path(sys.executable).parent
        log_file = exe_dir / 'imagedescriber.log'
        if debug_mode:
            log_file = exe_dir / Path(args.debug_file).name
    else:
        # Development mode - use current directory
        log_file = Path('imagedescriber.log')
        if debug_mode:
            log_file = Path(args.debug_file)
    
    # Configure logging
    log_level = logging.DEBUG if debug_mode else logging.INFO
    
    if debug_mode:
        log_format = '%(levelname)s - %(message)s - (%(name)s:%(lineno)d) - (%(asctime)s)'
    else:
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
    
    try:
        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=[
                logging.FileHandler(str(log_file), mode='a', encoding='utf-8'),
                logging.StreamHandler(sys.stderr)
            ],
            force=True
        )
    except Exception as e:
        # If logging setup fails, at least print to stderr
        print(f"ERROR: Failed to configure logging to {log_file}: {e}", file=sys.stderr)
    
    logger = logging.getLogger(__name__)
    logger.info("="*60)
    logger.info(f"ImageDescriber Starting - {'DEBUG MODE' if debug_mode else 'NORMAL MODE'}")
    logger.info(f"Log file: {log_file}")
    logger.info(f"Version: {get_app_version() if get_app_version else 'unknown'}")
    logger.info(f"Python: {sys.version}")
    logger.info(f"wxPython: {wx.version()}")
    logger.info(f"Frozen mode: {getattr(sys, 'frozen', False)}")
    logger.info("="*60)
    
    # Log standardized build banner at startup
    if log_build_banner:
        try:
            log_build_banner()
        except Exception:
            pass

    app = wx.App()
    frame = ImageDescriberFrame()
    
    if args.viewer:
        if args.path:
            # If path provided, switch to viewer mode with that path
            # We need to defer this slightly to ensure UI is ready
            wx.CallAfter(lambda: frame.switch_mode('viewer', Path(args.path)))
        else:
            # Just switch to viewer mode
            wx.CallAfter(lambda: frame.switch_mode('viewer'))
    elif args.path:
        # Load directory or workspace normally
        path = Path(args.path)
        if path.suffix == '.idt':
            wx.CallAfter(lambda: frame.load_workspace(path))
        elif path.is_dir():
            wx.CallAfter(lambda: frame.load_directory(path))

    frame.Show()
    app.MainLoop()
            


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        error_msg = f"CRITICAL ERROR: {e}\n\n{traceback.format_exc()}"
        print(error_msg, file=sys.stderr)
        
        crash_log_path = "crash_log.txt"
        try:
            with open(crash_log_path, "w") as f:
                f.write(error_msg)
            print(f"Error logged to {crash_log_path}")
        except:
            print("Could not write crash log")
        
        # Show error dialog for GUI mode (don't use input() - breaks windowed executables)
        try:
            import wx
            app = wx.App()
            wx.MessageBox(
                f"Application crashed. Error logged to {crash_log_path}\n\n{str(e)}", 
                "Critical Error", 
                wx.OK | wx.ICON_ERROR
            )
        except:
            pass  # If wx fails too, just exit
