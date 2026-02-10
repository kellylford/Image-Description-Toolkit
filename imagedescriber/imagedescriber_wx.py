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
except ImportError as e:
    print(f"ERROR: Could not import shared.wx_common: {e}")
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
        
        # Application state
        self.workspace = ImageWorkspace(new_workspace=True)
        self.current_directory = None
        self.workspace_file = None
        self.processing_thread = None
        self.current_image_item = None
        self.current_filter = "all"  # View filter: all, described, undescribed
        self.show_image_previews = True  # View option: show/hide image preview panel
        self.processing_items = {}  # Track items being processed: {file_path: {provider, model}}
        self.batch_progress = None  # Track batch processing: {current: N, total: M, file_path: "..."}
        
        # Phase 3: Batch processing management
        self.batch_worker: Optional[BatchProcessingWorker] = None  # Store worker reference
        self.batch_progress_dialog: Optional[BatchProgressDialog] = None  # Progress dialog
        self.batch_start_time: Optional[float] = None  # For avg time calculation
        self.batch_processing_times: List[float] = []  # Track times per image
        
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
        self.update_window_title("ImageDescriber", "Untitled")
        
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
        """Get the workspace data directory for extracted frames, etc.
        
        Returns the directory structure:
        - If workspace saved: {workspace_dir}/{workspace_stem}_workspace/
        - If unsaved: {home}/ImageDescriber_Workspaces/untitled_workspace/
        """
        if self.workspace_file:
            # Use workspace file location and name
            ws_path = Path(self.workspace_file)
            ws_name = ws_path.stem  # e.g., "my_project" from "my_project.idw"
            workspace_dir = ws_path.parent / f"{ws_name}_workspace"
        else:
            # Use temp location for unsaved workspace
            workspaces_root = Path.home() / "ImageDescriber_Workspaces"
            workspace_dir = workspaces_root / "untitled_workspace"
        
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
        
        # Extract frames at time intervals
        interval_seconds = extraction_config.get("time_interval_seconds", 5)
        start_time = extraction_config.get("start_time_seconds", 0)
        end_time = extraction_config.get("end_time_seconds")
        max_frames = extraction_config.get("max_frames_per_video", 100)
        
        frame_interval = int(fps * interval_seconds)
        start_frame = int(fps * start_time)
        
        extracted_paths = []
        frame_num = start_frame
        extract_count = 0
        
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
            frame_filename = f"{video_path_obj.stem}_frame_{extract_count:05d}.jpg"
            frame_path = video_dir / frame_filename
            cv2.imwrite(str(frame_path), frame)
            extracted_paths.append(str(frame_path))
            
            extract_count += 1
            frame_num += frame_interval
        
        cap.release()
        return extracted_paths, video_metadata
    
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
        
        # Sort all categories
        videos.sort(key=lambda x: x[0])
        regular_images.sort(key=lambda x: x[0])
        for parent in frames:
            frames[parent].sort(key=lambda x: x[0])
        
        # Add items to list: videos with their frames, then regular images
        items_to_display = []
        
        # Add videos and their frames
        for file_path, item in videos:
            items_to_display.append((file_path, item, 0))  # indent level 0
            
            # Add extracted frames immediately after parent video
            if file_path in frames:
                for frame_path, frame_item in frames[file_path]:
                    items_to_display.append((frame_path, frame_item, 1))  # indent level 1
        
        # Add regular images
        for file_path, item in regular_images:
            items_to_display.append((file_path, item, 0))  # indent level 0
        
        # Display all items
        for file_path, item, indent_level in items_to_display:
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
            
            # Combine prefix and display name with indentation
            indent = "  " * indent_level  # Two spaces per level
            if prefix_parts:
                prefix = "".join(prefix_parts)
                display_name = f"{indent}{prefix} {base_name}"
            else:
                display_name = f"{indent}{base_name}"
            
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
        if not self.workspace or not self.workspace.items:
            show_warning(self, "No images in workspace")
            return
        
        if not BatchProcessingWorker:
            show_error(self, "Batch processing worker not available")
            return
        
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
        
        for item in self.workspace.items.values():
            if item.item_type == "video":
                # Check if video needs extraction
                if not hasattr(item, 'extracted_frames') or not item.extracted_frames:
                    videos_to_extract.append(item.file_path)
            elif skip_existing:
                if not item.descriptions:
                    images_to_process.append(item.file_path)
            else:
                images_to_process.append(item.file_path)
        
        # Auto-extract video frames with default settings (1 frame every 5 seconds)
        if videos_to_extract:
            self.SetStatusText(f"Extracting frames from {len(videos_to_extract)} video(s)...", 0)
            
            for video_idx, video_path in enumerate(videos_to_extract, 1):
                video_name = Path(video_path).name
                self.SetStatusText(f"Extracting frames from {video_name} ({video_idx}/{len(videos_to_extract)})...", 0)
                
                try:
                    # Extract frames using default settings
                    extraction_config = {
                        "extraction_mode": "time_interval",
                        "time_interval_seconds": 5,  # Default: 1 frame every 5 seconds
                        "start_time_seconds": 0,
                        "end_time_seconds": None,
                        "max_frames_per_video": 100
                    }
                    
                    extracted_frames, video_metadata = self._extract_video_frames_sync(video_path, extraction_config)
                    
                    if extracted_frames:
                        # Update video item with extracted frames
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
                                
                                # Add to processing queue if not already described
                                if skip_existing and not frame_item.descriptions:
                                    images_to_process.append(frame_path)
                                elif not skip_existing:
                                    images_to_process.append(frame_path)
                        
                        self.SetStatusText(f"Extracted {len(extracted_frames)} frames from {video_name}", 0)
                except Exception as e:
                    show_error(self, f"Failed to extract frames from {video_name}:\n{str(e)}")
                    # Continue with other videos
            
            self.refresh_image_list()
            self.mark_modified()
        
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
            skip_existing  # Phase 5: Use parameter instead of options
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
        default_dir = ""
        default_file = "untitled.idw"
        if self.workspace_file:
            default_dir = str(Path(self.workspace_file).parent)
            default_file = Path(self.workspace_file).name

        file_path = save_file_dialog(
            self,
            "Save Workspace As",
            "ImageDescriber Workspace (*.idw)|*.idw|All files (*.*)|*.*",
            default_dir,
            default_file
        )

        if file_path:
            self.save_workspace(file_path)

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
        
        show_error(self, f"Processing failed for {Path(event.file_path).name}:\n{event.error}")
        self.SetStatusText(f"Error: {Path(event.file_path).name}", 0)
    
    def on_workflow_complete(self, event):
        """Handle workflow completion (including video extraction)"""
        # Check if this was a video extraction
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
                        show_info(self, f"Extracted {len(extracted_frames)} frames from video.\n\nFrames have been added to the workspace.")
                
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
        
        # Save workspace
        if self.workspace_file:
            self.save_workspace(self.workspace_file)
        
        show_info(self, f"Workflow complete!\n{event.input_dir}")
        self.SetStatusText("Workflow complete", 0)
        self.refresh_image_list()
    
    def on_workflow_failed(self, event):
        """Handle workflow failures"""
        show_error(self, f"Workflow failed:\n{event.error}")
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
        
        self.SetStatusText("Batch processing stopped", 0)
        show_info(self, "Batch processing stopped.\n\nCompleted descriptions have been saved.")
    
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
        
        # Add defaults for extractor
        extraction_config = {
            "start_time_seconds": 0,
            "end_time_seconds": None,
            "max_frames_per_video": 100,
            **settings
        }
        
        # Store settings for potential auto-processing
        self.last_extraction_settings = {
            'video_path': selected_video,
            'process_after': process_after,
            'extraction_config': extraction_config
        }
        
        # Start extraction worker
        worker = VideoProcessingWorker(self, selected_video, extraction_config)
        worker.start()
        
        self.SetStatusText(f"Extracting frames from: {Path(selected_video).name}...", 0)
    
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
            show_info(self, f"Extraction complete! {len(frame_paths)} frames added to workspace.\n\nYou can process them later with 'Process All Undescribed'.")
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
            show_info(self, msg)
            self.SetStatusText(msg, 0)
        else:
            msg = f"Converted {converted_count} file(s), {failed_count} failed"
            show_warning(self, msg + f"\n\nFailed files:\n" + "\n".join(event.failed_files))
            self.SetStatusText(msg, 0)
    
    def on_conversion_failed(self, event):
        """Handle HEIC conversion failure"""
        error_msg = f"HEIC conversion failed: {event.error}"
        show_error(self, error_msg)
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
        user_guide_url = "https://github.com/kellylford/Image-Description-Toolkit/blob/main/docs/USER_GUIDE.md"
        try:
            webbrowser.open(user_guide_url)
        except Exception as e:
            show_error(self, f"Could not open user guide:\n{e}")
    
    def on_about(self):
        """Show about dialog"""
        show_about_dialog(
            self,
            "ImageDescriber",
            get_app_version(),
            "AI-Powered Image Description GUI\n\n"
            "Features:\n"
            "• Document-based workspace\n"
            "• Individual and batch processing\n"
            "• Multiple AI providers (Ollama, OpenAI, Claude)\n"
            "• Video frame extraction\n"
            "• HEIC conversion\n"
            "• Full keyboard accessibility"
        )
    
    def on_close(self, event):
        """Handle application close"""
        if self.confirm_unsaved_changes():
            self.Destroy()
        elif event.CanVeto():
            event.Veto()
    
    def on_save(self, event):
        """Wrapper for ModifiedStateMixin"""
        self.on_save_workspace(event)


def main():
    """Main application entry point"""
    import argparse
    
    # Log standardized build banner at startup
    if log_build_banner:
        try:
            log_build_banner()
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Image Describer Tool")
    parser.add_argument('path', nargs='?', help="Directory or workspace to load")
    parser.add_argument('--viewer', action='store_true', help="Start in viewer mode")
    args = parser.parse_args()

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
        try:
            with open("crash_log.txt", "w") as f:
                f.write(error_msg)
            print("Error logged to crash_log.txt")
        except:
            print("Could not write crash log")
        
        input("Application crashed. Press Enter to exit...")
