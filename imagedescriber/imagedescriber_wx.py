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
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import wx
import wx.lib.newevent

# Import shared utilities
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
)

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

# Import shared metadata extraction module
try:
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
try:
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
    )
    from workers_wx import (
        ProcessingWorker,
        BatchProcessingWorker,
        WorkflowProcessWorker,
        VideoProcessingWorker,
        EVT_PROGRESS_UPDATE,
        EVT_PROCESSING_COMPLETE,
        EVT_PROCESSING_FAILED,
        EVT_WORKFLOW_COMPLETE,
        EVT_WORKFLOW_FAILED,
    )
except ImportError as e:
    print(f"Warning: Could not import AI modules: {e}")
    # Define fallbacks
    class ImageDescription:
        pass
    class ImageItem:
        pass
    class ImageWorkspace:
        pass
    WORKSPACE_VERSION = "1.0"
    DirectorySelectionDialog = None
    ApiKeyDialog = None
    ProcessingOptionsDialog = None
    ImageDetailDialog = None
    ProcessingWorker = None
    BatchProcessingWorker = None
    WorkflowProcessWorker = None
    VideoProcessingWorker = None
    EVT_PROGRESS_UPDATE = None
    EVT_PROCESSING_COMPLETE = None
    EVT_PROCESSING_FAILED = None
    EVT_WORKFLOW_COMPLETE = None
    EVT_WORKFLOW_FAILED = None

# Import provider capabilities
try:
    models_path = Path(__file__).parent.parent / 'models'
    if str(models_path) not in sys.path:
        sys.path.insert(0, str(models_path))
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
        
        # Supported image extensions
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic'}
        self.video_extensions = {'.mp4', '.mov', '.avi', '.mkv'}
        
        # Configuration
        self.load_config()
        
        # Setup UI
        self.init_ui()
        self.create_menu_bar()
        self.create_status_bar()
        
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
        
        # Update window title
        self.update_window_title("ImageDescriber", "Untitled")
        
        # Log startup banner
        if log_build_banner:
            try:
                log_build_banner()
            except Exception:
                pass
    
    def update_window_title(self, app_name, document_name):
        """Update window title with app name and document name"""
        if self.modified:
            title = f"{app_name} - {document_name} *"
        else:
            title = f"{app_name} - {document_name}"
        self.SetTitle(title)
    
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
    
    def init_ui(self):
        """Initialize the user interface"""
        # Main panel
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Create splitter for resizable panels
        splitter = wx.SplitterWindow(panel, style=wx.SP_LIVE_UPDATE)
        
        # Left panel - Image list
        left_panel = self.create_image_list_panel(splitter)
        
        # Right panel - Description editor
        right_panel = self.create_description_panel(splitter)
        
        # Set up splitter
        splitter.SplitVertically(left_panel, right_panel, 400)
        splitter.SetMinimumPaneSize(200)
        
        # Add to main sizer
        main_sizer.Add(splitter, 1, wx.EXPAND | wx.ALL, 5)
        
        panel.SetSizer(main_sizer)
    
    def create_image_list_panel(self, parent):
        """Create the left panel with image list"""
        panel = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Label
        label = wx.StaticText(panel, label="Images:")
        sizer.Add(label, 0, wx.ALL, 5)
        
        # Image list (using ListBox for accessibility - single tab stop)
        self.image_list = wx.ListBox(panel, name="Images in workspace", style=wx.LB_SINGLE | wx.LB_NEEDED_SB)
        self.image_list.Bind(wx.EVT_LISTBOX, self.on_image_selected)
        sizer.Add(self.image_list, 1, wx.EXPAND | wx.ALL, 5)
        
        # Buttons
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.load_dir_btn = wx.Button(panel, label="Load Directory")
        self.load_dir_btn.Bind(wx.EVT_BUTTON, self.on_load_directory)
        button_sizer.Add(self.load_dir_btn, 0, wx.ALL, 2)
        
        self.process_all_btn = wx.Button(panel, label="Process All")
        self.process_all_btn.Bind(wx.EVT_BUTTON, self.on_process_all)
        self.process_all_btn.Enable(False)
        button_sizer.Add(self.process_all_btn, 0, wx.ALL, 2)
        
        sizer.Add(button_sizer, 0, wx.ALL, 5)
        
        panel.SetSizer(sizer)
        return panel
    
    def create_description_panel(self, parent):
        """Create the right panel with description editor"""
        panel = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Image info label
        self.image_info_label = wx.StaticText(panel, label="No image selected")
        sizer.Add(self.image_info_label, 0, wx.ALL, 5)
        
        # Description text editor
        label = wx.StaticText(panel, label="Description:")
        sizer.Add(label, 0, wx.ALL, 5)
        
        self.description_text = wx.TextCtrl(
            panel,
            name="Image description editor",
            style=wx.TE_MULTILINE | wx.TE_WORDWRAP | wx.TE_RICH2
        )
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
        
        file_menu.AppendSeparator()
        
        exit_item = file_menu.Append(wx.ID_EXIT, "E&xit\tCtrl+Q")
        self.Bind(wx.EVT_MENU, self.on_close, exit_item)
        
        menubar.Append(file_menu, "&File")
        
        # Edit menu
        edit_menu = wx.Menu()
        
        # Empty for now - can add copy/paste/undo later if needed
        
        menubar.Append(edit_menu, "&Edit")
        
        # Process menu
        process_menu = wx.Menu()
        
        process_single_item = process_menu.Append(wx.ID_ANY, "Process &Current Image\tCtrl+P")
        self.Bind(wx.EVT_MENU, self.on_process_single, process_single_item)
        
        process_all_item = process_menu.Append(wx.ID_ANY, "Process &All Images\tCtrl+Shift+P")
        self.Bind(wx.EVT_MENU, self.on_process_all, process_all_item)
        process_menu.AppendSeparator()
        
        extract_video_item = process_menu.Append(wx.ID_ANY, "Extract &Video Frames\tCtrl+E")
        self.Bind(wx.EVT_MENU, self.on_extract_video, extract_video_item)
        
        
        menubar.Append(process_menu, "&Process")
        
        # Help menu
        help_menu = wx.Menu()
        
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
                self.process_btn.Enable(True)
                self.save_desc_btn.Enable(True)
    
    def display_image_info(self, image_item: ImageItem):
        """Display information about selected image"""
        file_path = Path(image_item.file_path)
        
        # Update info label
        desc_count = len(image_item.descriptions)
        info = f"Selected: {file_path.name}"
        if desc_count > 0:
            info += f" ({desc_count} description{'s' if desc_count != 1 else ''})"
        self.image_info_label.SetLabel(info)
        
        # Load latest description if exists
        if image_item.descriptions:
            latest_desc = image_item.descriptions[-1]
            self.description_text.SetValue(latest_desc.text)
        else:
            self.description_text.SetValue("")
    
    def on_load_directory(self, event):
        """Load a directory of images"""
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
    
    def load_directory(self, dir_path, recursive=False):
        """Load images from directory"""
        try:
            dir_path = Path(dir_path)
            if not dir_path.exists():
                show_error(self, f"Directory not found: {dir_path}")
                return
            
            # Add directory to workspace
            self.workspace.add_directory(str(dir_path))
            
            # Find all images
            images_found = []
            
            if recursive:
                # Recursive search
                for ext in self.image_extensions:
                    images_found.extend(dir_path.rglob(f"*{ext}"))
                    images_found.extend(dir_path.rglob(f"*{ext.upper()}"))
            else:
                # Non-recursive
                for ext in self.image_extensions:
                    images_found.extend(dir_path.glob(f"*{ext}"))
                    images_found.extend(dir_path.glob(f"*{ext.upper()}"))
            
            # Add to workspace
            for image_path in sorted(images_found):
                image_path_str = str(image_path)
                if image_path_str not in self.workspace.items:
                    item = ImageItem(image_path_str, "image")
                    self.workspace.add_item(item)
            
            # Update UI
            self.refresh_image_list()
            self.mark_modified()
            
            count = len(images_found)
            self.SetStatusText(f"Loaded {count} images from {dir_path.name}", 0)
            self.SetStatusText(f"{len(self.workspace.items)} total images", 1)
            self.process_all_btn.Enable(count > 0)
            
        except Exception as e:
            show_error(self, f"Error loading directory:\n{e}")
    
    def refresh_image_list(self):
        """Refresh the image list display"""
        self.image_list.Clear()
        
        for file_path in sorted(self.workspace.items.keys()):
            item = self.workspace.items[file_path]
            display_name = Path(file_path).name
            
            # Add description count indicator
            desc_count = len(item.descriptions)
            if desc_count > 0:
                display_name = f"✓ {display_name} ({desc_count})"
            
            self.image_list.Append(display_name, file_path)  # Store file_path as client data
    
    def on_process_single(self, event):
        """Process single selected image"""
        if not self.current_image_item:
            show_warning(self, "No image selected")
            return
        
        if not ProcessingWorker:
            show_error(self, "Processing worker not available")
            return
        
        # Show processing options dialog
        if ProcessingOptionsDialog:
            dialog = ProcessingOptionsDialog(self.config, self)
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
        worker = ProcessingWorker(
            self,
            self.current_image_item.file_path,
            options['provider'],
            options['model'],
            options['prompt_style'],
            options.get('custom_prompt', ''),
            None,  # detection_settings
            None   # prompt_config_path
        )
        worker.start()
        
        self.SetStatusText(f"Processing: {Path(self.current_image_item.file_path).name}...", 0)
    
    def on_process_all(self, event):
        """Process all images"""
        if not self.workspace or not self.workspace.items:
            show_warning(self, "No images in workspace")
            return
        
        if not BatchProcessingWorker:
            show_error(self, "Batch processing worker not available")
            return
        
        # Show processing options dialog
        if ProcessingOptionsDialog:
            dialog = ProcessingOptionsDialog(self.config, self)
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
        
        # Get files to process
        if options.get('skip_existing', False):
            to_process = [item.file_path for item in self.workspace.items.values() 
                         if not item.descriptions]
        else:
            to_process = [item.file_path for item in self.workspace.items.values()]
        
        if not to_process:
            show_info(self, "All images already have descriptions")
            return
        
        # Start batch processing worker
        worker = BatchProcessingWorker(
            self,
            to_process,
            options['provider'],
            options['model'],
            options['prompt_style'],
            options.get('custom_prompt', ''),
            None,  # detection_settings
            None,  # prompt_config_path
            options.get('skip_existing', False)
        )
        worker.start()
        
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
        self.process_all_btn.Enable(False)
        self.process_btn.Enable(False)
        self.save_desc_btn.Enable(False)
        self.clear_modified()
    
    def on_open_workspace(self, event):
        """Open existing workspace"""
        if not self.confirm_unsaved_changes():
            return
        
        file_path = open_file_dialog(
            self,
            "Open Workspace",
            None,
            "ImageDescriber Workspace (*.idw)|*.idw|All files (*.*)|*.*"
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
            
            # Update UI
            self.refresh_image_list()
            self.update_window_title("ImageDescriber", Path(file_path).name)
            
            # Update status
            count = len(self.workspace.items)
            self.SetStatusText(f"Workspace loaded: {Path(file_path).name}", 0)
            self.SetStatusText(f"{count} images", 1)
            self.process_all_btn.Enable(count > 0)
            self.clear_modified()
            
        except Exception as e:
            show_error(self, f"Error loading workspace:\n{e}")
    
    def on_save_workspace(self, event):
        """Save current workspace"""
        if self.workspace_file:
            self.save_workspace(self.workspace_file)
        else:
            self.on_save_workspace_as(event)
    
    def on_save_workspace_as(self, event):
        """Save workspace to new file"""
        file_path = save_file_dialog(
            self,
            "Save Workspace As",
            None,
            "untitled.idw",
            "ImageDescriber Workspace (*.idw)|*.idw"
        )
        
        if file_path:
            self.save_workspace(file_path)
    
    def save_workspace(self, file_path):
        """Save workspace to file"""
        try:
            # Update workspace metadata
            self.workspace.file_path = file_path
            self.workspace.modified = datetime.now().isoformat()
            
            # Save to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.workspace.to_dict(), f, indent=2)
            
            self.workspace_file = file_path
            self.workspace.saved = True
            self.clear_modified()
            
            self.update_window_title("ImageDescriber", Path(file_path).name)
            self.SetStatusText(f"Workspace saved: {Path(file_path).name}", 0)
            
        except Exception as e:
            show_error(self, f"Error saving workspace:\n{e}")
    
    def on_worker_progress(self, event):
        """Handle progress updates from worker threads"""
        self.SetStatusText(event.message, 0)
    
    def on_worker_complete(self, event):
        """Handle successful processing completion"""
        # Find the image item and add description
        if event.file_path in self.workspace.items:
            image_item = self.workspace.items[event.file_path]
            desc = ImageDescription(
                text=event.description,
                model=event.model,
                prompt_style=event.prompt_style,
                custom_prompt=event.custom_prompt,
                provider=event.provider
            )
            image_item.add_description(desc)
            self.mark_modified()
            self.refresh_image_list()
            
            # Update display if this is the current image
            if self.current_image_item == image_item:
                self.display_image_info(image_item)
            
            self.SetStatusText(f"Completed: {Path(event.file_path).name}", 0)
    
    def on_worker_failed(self, event):
        """Handle processing failures"""
        show_error(self, f"Processing failed for {Path(event.file_path).name}:\n{event.error}")
        self.SetStatusText(f"Error: {Path(event.file_path).name}", 0)
    
    def on_workflow_complete(self, event):
        """Handle workflow completion"""
        show_info(self, f"Workflow complete!\n{event.input_dir}")
        self.SetStatusText("Workflow complete", 0)
        self.refresh_image_list()
    
    def on_workflow_failed(self, event):
        """Handle workflow failures"""
        show_error(self, f"Workflow failed:\n{event.error}")
        self.SetStatusText("Workflow failed", 0)
    
    def on_extract_video(self, event):
        """Extract frames from video file"""
        if not VideoProcessingWorker:
            show_error(self, "Video processing not available (OpenCV not installed)")
            return
        
        # Select video file
        file_path = open_file_dialog(
            self,
            "Select Video File",
            None,
            "Video files (*.mp4;*.mov;*.avi;*.mkv)|*.mp4;*.mov;*.avi;*.mkv|All files (*.*)|*.*"
        )
        
        if not file_path:
            return
        
        # Get extraction settings (simplified - using defaults)
        extraction_config = {
            "extraction_mode": "time_interval",
            "time_interval_seconds": 5,
            "start_time_seconds": 0,
            "end_time_seconds": None,
            "max_frames_per_video": 100
        }
        
        # Start extraction worker
        worker = VideoProcessingWorker(self, file_path, extraction_config)
        worker.start()
        
        self.SetStatusText(f"Extracting frames from: {Path(file_path).name}...", 0)
    
    def on_description_complete(self, event):
        """Handle description completion from worker thread (legacy)"""
        pass
    
    def on_processing_progress(self, event):
        """Handle processing progress updates (legacy)"""
        pass
    
    def on_processing_error(self, event):
        """Handle processing errors (legacy)"""
        pass
    
    def on_about(self, event):
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
    # Log standardized build banner at startup
    if log_build_banner:
        try:
            log_build_banner()
        except Exception:
            pass
    
    app = wx.App()
    frame = ImageDescriberFrame()
    frame.Show()
    app.MainLoop()


if __name__ == "__main__":
    main()
