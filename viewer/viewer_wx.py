#!/usr/bin/env python3
"""
wxPython Image Description Viewer - COMPLETE VERSION
Full-featured port of the PyQt6 viewer with better VoiceOver support

Features:
- Browse and load workflow directories
- View image descriptions with previews
- Live monitoring of active workflows
- Copy descriptions/images to clipboard
- Redescribe individual images
- Redescribe entire workflows
- Resume incomplete workflows  
- Export functionality
- Full keyboard navigation
- Complete VoiceOver/accessibility support
"""

import sys
import os
import json
import subprocess
import re
import time
import threading
from pathlib import Path
from datetime import datetime

# Add project root to path for shared module imports
# Works in both development mode (running script) and frozen mode (PyInstaller exe)
if getattr(sys, 'frozen', False):
    # Frozen mode - executable directory is base
    _project_root = Path(sys.executable).parent
else:
    # Development mode - use __file__ relative path
    _project_root = Path(__file__).parent.parent

if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import wx
import wx.lib.scrolledpanel as scrolled

# Import shared utilities
try:
    from shared.wx_common import (
        find_scripts_directory,
        show_error,
        show_warning,
        show_info,
        ask_yes_no,
        select_directory_dialog,
        open_file_dialog,
        format_timestamp as format_timestamp_shared,
        DescriptionListBox,  # NEW: Import accessible listbox from shared module
    )
except ImportError as e:
    print(f"ERROR: Could not import shared.wx_common: {e}")
    print("This is a critical error. The viewer cannot function without shared utilities.")
    sys.exit(1)

# Import EXIF utilities
try:
    from shared.exif_utils import extract_exif_date_string
except ImportError:
    # Fallback for development mode
    extract_exif_date_string = None

# Import model registry and config loader for robust model/prompt resolution
try:
    from models.model_registry import list_models as registry_list_models
except Exception:
    registry_list_models = None

try:
    # Try frozen mode first (PyInstaller)
    from config_loader import load_json_config as loader_load_json_config
except ImportError:
    try:
        # Development mode fallback
        from scripts.config_loader import load_json_config as loader_load_json_config
    except Exception:
        loader_load_json_config = None

def get_scripts_directory():
    """Get the scripts directory (uses shared library)"""
    return find_scripts_directory()

# Import workflow scanning functions
scripts_dir = get_scripts_directory()
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

try:
    from list_results import (
        find_workflow_directories,
        count_descriptions,
        format_timestamp,
        parse_directory_name
    )
except ImportError as e:
    print(f"Warning: Could not import from list_results: {e}")
    find_workflow_directories = None
    count_descriptions = None
    format_timestamp = None
    parse_directory_name = None

try:
    import ollama
except ImportError:
    ollama = None


# Note: get_image_date() is now imported from shared.exif_utils above.
# This fallback implementation is used if the shared import fails.
def _get_image_date_fallback(image_path: str) -> str:
    """Fallback get_image_date implementation (used if shared import fails).
    
    See shared.exif_utils.extract_exif_date_string for full documentation.
    """
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS
        
        with Image.open(image_path) as img:
            exif_data = img.getexif()
            
            if exif_data:
                exif_dict = {}
                for tag_id, value in exif_data.items():
                    tag = TAGS.get(tag_id, tag_id)
                    exif_dict[tag] = value
                
                datetime_fields = ['DateTimeOriginal', 'DateTimeDigitized', 'DateTime']
                
                for field in datetime_fields:
                    if field in exif_dict:
                        dt_str = exif_dict[field]
                        if dt_str:
                            try:
                                dt = datetime.strptime(dt_str, '%Y:%m:%d %H:%M:%S')
                                hour = dt.hour
                                if hour == 0:
                                    hour_12 = 12
                                    suffix = 'A'
                                elif hour < 12:
                                    hour_12 = hour
                                    suffix = 'A'
                                elif hour == 12:
                                    hour_12 = 12
                                    suffix = 'P'
                                else:
                                    hour_12 = hour - 12
                                    suffix = 'P'
                                
                                return f"{dt.month}/{dt.day}/{dt.year} {hour_12}:{dt.minute:02d}{suffix}"
                            except:
                                pass
        
        # Fallback to file modification time
        stat = Path(image_path).stat()
        dt = datetime.fromtimestamp(stat.st_mtime)
        hour = dt.hour
        if hour == 0:
            hour_12 = 12
            suffix = 'A'
        elif hour < 12:
            hour_12 = hour
            suffix = 'A'
        elif hour == 12:
            hour_12 = 12
            suffix = 'P'
        else:
            hour_12 = hour - 12
            suffix = 'P'
        
        return f"{dt.month}/{dt.day}/{dt.year} {hour_12}:{dt.minute:02d}{suffix}"
    
    except Exception as e:
        return "Unknown date"


# Use shared version if available, fallback otherwise
if extract_exif_date_string is not None:
    get_image_date = extract_exif_date_string
else:
    get_image_date = _get_image_date_fallback


class WorkflowBrowserDialog(wx.Dialog):
    """Dialog for browsing and selecting workflows"""
    
    def __init__(self, parent, default_dir=None):
        super().__init__(parent, title="Select Workflow", size=(800, 600))
        
        self.selected_workflow = None
        
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Instructions
        label = wx.StaticText(panel, label="Select a workflow to view:")
        sizer.Add(label, 0, wx.ALL, 10)
        
        # Status label
        self.status_label = wx.StaticText(panel, label="Loading...")
        sizer.Add(self.status_label, 0, wx.ALL, 10)
        
        # Workflow list
        self.workflow_list = wx.ListBox(panel, style=wx.LB_SINGLE)
        self.workflow_list.Bind(wx.EVT_LISTBOX_DCLICK, self.on_double_click)
        self.workflow_list.Bind(wx.EVT_KEY_DOWN, self.on_list_key_down)
        sizer.Add(self.workflow_list, 1, wx.ALL | wx.EXPAND, 10)
        
        # Browse button
        browse_btn = wx.Button(panel, label="Browse Different Directory...")
        browse_btn.Bind(wx.EVT_BUTTON, self.on_browse)
        sizer.Add(browse_btn, 0, wx.ALL | wx.EXPAND, 10)
        
        # OK/Cancel buttons
        btn_sizer = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(panel, wx.ID_OK, label="Open Workflow")
        cancel_btn = wx.Button(panel, wx.ID_CANCEL)
        btn_sizer.AddButton(ok_btn)
        btn_sizer.AddButton(cancel_btn)
        btn_sizer.Realize()
        sizer.Add(btn_sizer, 0, wx.ALL | wx.ALIGN_RIGHT, 10)
        
        panel.SetSizer(sizer)
        
        # Load workflows - start with browse dialog if no default
        if default_dir:
            self.load_workflows(default_dir)
        else:
            # Show file browser immediately
            wx.CallAfter(self.on_browse, None)
        
        ok_btn.Bind(wx.EVT_BUTTON, self.on_ok)
    
    def load_workflows(self, directory):
        """Load workflows from directory"""
        self.workflow_list.Clear()
        self.workflows = []
        
        dir_path = Path(directory)
        if not dir_path.exists():
            self.status_label.SetLabel(f"Directory not found: {directory}")
            return
        
        if not find_workflow_directories:
            self.status_label.SetLabel("Workflow scanner not available")
            return
        
        # find_workflow_directories returns list of (path, metadata) tuples
        workflow_tuples = find_workflow_directories(dir_path)
        if not workflow_tuples:
            self.status_label.SetLabel(f"No workflows found in: {directory}")
            return
        
        # Sort by path name
        workflow_tuples.sort(key=lambda x: x[0].name, reverse=True)
        
        for workflow_path, metadata in workflow_tuples:
            # Parse directory name
            name_parts = parse_directory_name(workflow_path.name) if parse_directory_name else {}
            provider = name_parts.get('provider', 'unknown')
            model = name_parts.get('model', 'unknown')
            prompt = name_parts.get('prompt_style', 'unknown')
            
            # Count descriptions - returns a dict with 'descriptions' key
            desc_count = 0
            if count_descriptions:
                desc_info = count_descriptions(workflow_path)
                # count_descriptions returns a dict
                if isinstance(desc_info, dict):
                    desc_count = desc_info.get('descriptions', 0)
                else:
                    desc_count = desc_info if isinstance(desc_info, int) else 0
            
            timestamp = metadata.get('timestamp', 'unknown')
            
            display_text = f"{workflow_path.name} | {prompt} | {desc_count} images | {model} | {provider} | {timestamp}"
            
            self.workflow_list.Append(display_text)
            self.workflows.append(workflow_path)
        
        self.status_label.SetLabel(f"Found {len(workflow_tuples)} workflow(s) in: {directory}")
        
        if self.workflow_list.GetCount() > 0:
            self.workflow_list.SetSelection(0)
    
    def on_browse(self, event):
        """Browse for different directory"""
        path = select_directory_dialog(self, "Select Descriptions Directory")
        if path:
            self.load_workflows(path)
    
    def on_double_click(self, event):
        """Handle double-click on workflow"""
        sel = self.workflow_list.GetSelection()
        if sel != wx.NOT_FOUND:
            self.selected_workflow = self.workflows[sel]
            self.EndModal(wx.ID_OK)
    
    def on_list_key_down(self, event):
        """Handle Enter key on workflow list"""
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_RETURN or keycode == wx.WXK_NUMPAD_ENTER:
            sel = self.workflow_list.GetSelection()
            if sel != wx.NOT_FOUND:
                self.selected_workflow = self.workflows[sel]
                self.EndModal(wx.ID_OK)
        else:
            event.Skip()
    
    def on_ok(self, event):
        """Handle OK button"""
        sel = self.workflow_list.GetSelection()
        if sel != wx.NOT_FOUND:
            self.selected_workflow = self.workflows[sel]
            self.EndModal(wx.ID_OK)
        else:
            show_warning(self, "Please select a workflow", "No Selection")


class RedescribeDialog(wx.Dialog):
    """Dialog for selecting model and prompt for redescribing an image"""
    
    def __init__(self, parent):
        super().__init__(parent, title="Redescribe Image", size=(500, 400))
        
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Instructions
        label = wx.StaticText(panel, label="Select model and prompt style to redescribe this image:")
        sizer.Add(label, 0, wx.ALL, 10)
        
        # Model selection
        model_label = wx.StaticText(panel, label="Model:")
        sizer.Add(model_label, 0, wx.ALL, 5)
        
        self.model_choice = wx.Choice(panel)
        sizer.Add(self.model_choice, 0, wx.ALL | wx.EXPAND, 5)
        
        # Prompt style selection
        prompt_label = wx.StaticText(panel, label="Prompt Style:")
        sizer.Add(prompt_label, 0, wx.ALL, 5)
        
        self.prompt_choice = wx.Choice(panel)
        sizer.Add(self.prompt_choice, 0, wx.ALL | wx.EXPAND, 5)
        
        # Load available models and prompts
        self.load_models()
        self.load_prompts()
        
        # OK/Cancel buttons
        btn_sizer = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(panel, wx.ID_OK)
        cancel_btn = wx.Button(panel, wx.ID_CANCEL)
        btn_sizer.AddButton(ok_btn)
        btn_sizer.AddButton(cancel_btn)
        btn_sizer.Realize()
        sizer.Add(btn_sizer, 0, wx.ALL | wx.ALIGN_RIGHT, 10)
        
        panel.SetSizer(sizer)
    
    def load_models(self):
        """Load available models using the central registry (provider: Ollama)."""
        self.model_choice.Clear()
        if registry_list_models:
            try:
                models = registry_list_models(provider="ollama", recommended_only=False)
                if models:
                    for m in models:
                        self.model_choice.Append(m)
                    self.model_choice.SetSelection(0)
                    return
            except Exception:
                pass
        # Fallback messaging if registry unavailable
        self.model_choice.Append("No models found (check models registry)")
    
    def load_prompts(self):
        """Load available prompt styles via layered config resolution."""
        self.prompt_choice.Clear()
        prompts_added = False
        # Preferred: use config_loader for robust path handling in dev/frozen
        if loader_load_json_config:
            try:
                cfg, path, source = loader_load_json_config('image_describer_config.json', env_var_file='IDT_IMAGE_DESCRIBER_CONFIG')
                if cfg:
                    prompts = cfg.get('prompt_variations', {})
                    for prompt_name in prompts.keys():
                        self.prompt_choice.Append(prompt_name)
                        prompts_added = True
            except Exception:
                pass
        # Fallback: direct path under scripts
        if not prompts_added:
            try:
                if loader_load_json_config:
                    config, _, _ = loader_load_json_config('image_describer_config.json')
                    prompts = config.get('prompt_variations', {})
                    for prompt_name in prompts.keys():
                        self.prompt_choice.Append(prompt_name)
                        prompts_added = True
            except Exception:
                pass
        # Final fallback
        if not prompts_added:
            self.prompt_choice.Append("narrative")
        # Select a sensible default
        if self.prompt_choice.GetCount() > 0:
            default_idx = self.prompt_choice.FindString("narrative")
            self.prompt_choice.SetSelection(default_idx if default_idx != wx.NOT_FOUND else 0)
    
    def get_selections(self):
        """Get selected model and prompt"""
        model = self.model_choice.GetStringSelection()
        prompt = self.prompt_choice.GetStringSelection()
        return model, prompt


class ApiKeyDialog(wx.Dialog):
    """Dialog for entering API key file path"""
    
    def __init__(self, provider_name, parent):
        super().__init__(parent, title=f"{provider_name} API Key", size=(500, 200))
        
        self.api_key_file = None
        
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Instructions
        label = wx.StaticText(panel, label=f"Enter the path to your {provider_name} API key file:")
        sizer.Add(label, 0, wx.ALL, 10)
        
        # File path entry
        file_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.file_text = wx.TextCtrl(panel)
        file_sizer.Add(self.file_text, 1, wx.ALL | wx.EXPAND, 5)
        
        browse_btn = wx.Button(panel, label="Browse...")
        browse_btn.Bind(wx.EVT_BUTTON, self.on_browse)
        file_sizer.Add(browse_btn, 0, wx.ALL, 5)
        
        sizer.Add(file_sizer, 0, wx.ALL | wx.EXPAND, 5)
        
        # OK/Cancel buttons
        btn_sizer = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(panel, wx.ID_OK)
        cancel_btn = wx.Button(panel, wx.ID_CANCEL)
        btn_sizer.AddButton(ok_btn)
        btn_sizer.AddButton(cancel_btn)
        btn_sizer.Realize()
        sizer.Add(btn_sizer, 0, wx.ALL | wx.ALIGN_RIGHT, 10)
        
        panel.SetSizer(sizer)
    
    def on_browse(self, event):
        """Browse for API key file"""
        path = open_file_dialog(self, "Select API Key File")
        if path:
            self.file_text.SetValue(path)
    
    def get_api_key_file(self):
        """Get the API key file path"""
        return self.file_text.GetValue()


class RedescribeWorkflowDialog(wx.Dialog):
    """Dialog for selecting provider, model, and prompt for redescribing entire workflow"""
    
    def __init__(self, parent):
        super().__init__(parent, title="Redescribe Workflow", size=(500, 450))
        
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Instructions
        label = wx.StaticText(panel, label="Select provider, model, and prompt to redescribe all images:")
        sizer.Add(label, 0, wx.ALL, 10)
        
        # Provider selection
        provider_label = wx.StaticText(panel, label="Provider:")
        sizer.Add(provider_label, 0, wx.ALL, 5)
        
        self.provider_choice = wx.Choice(panel, choices=["Ollama", "Ollama Cloud", "OpenAI", "Claude"])
        self.provider_choice.SetSelection(0)
        self.provider_choice.Bind(wx.EVT_CHOICE, self.on_provider_changed)
        sizer.Add(self.provider_choice, 0, wx.ALL | wx.EXPAND, 5)
        
        # Model selection
        model_label = wx.StaticText(panel, label="Model:")
        sizer.Add(model_label, 0, wx.ALL, 5)
        
        self.model_choice = wx.Choice(panel)
        sizer.Add(self.model_choice, 0, wx.ALL | wx.EXPAND, 5)
        
        # Prompt style selection
        prompt_label = wx.StaticText(panel, label="Prompt Style:")
        sizer.Add(prompt_label, 0, wx.ALL, 5)
        
        self.prompt_choice = wx.Choice(panel)
        sizer.Add(self.prompt_choice, 0, wx.ALL | wx.EXPAND, 5)
        
        # Load available prompts
        self.load_prompts()
        
        # Load initial provider models
        self.on_provider_changed(None)
        
        # OK/Cancel buttons
        btn_sizer = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(panel, wx.ID_OK)
        cancel_btn = wx.Button(panel, wx.ID_CANCEL)
        btn_sizer.AddButton(ok_btn)
        btn_sizer.AddButton(cancel_btn)
        btn_sizer.Realize()
        sizer.Add(btn_sizer, 0, wx.ALL | wx.ALIGN_RIGHT, 10)
        
        panel.SetSizer(sizer)
    
    def on_provider_changed(self, event):
        """Handle provider change using model registry lists."""
        provider = self.provider_choice.GetStringSelection()
        self.model_choice.Clear()
        provider_map = {
            "Ollama": "ollama",
            "Ollama Cloud": "ollama",  # Cloud uses same model names
            "OpenAI": "openai",
            "Claude": "claude"
        }
        prov_key = provider_map.get(provider, provider.lower())
        if registry_list_models:
            try:
                models = registry_list_models(provider=prov_key, recommended_only=False)
                for m in models:
                    self.model_choice.Append(m)
            except Exception:
                pass
        # Sensible defaults if registry unavailable
        if self.model_choice.GetCount() == 0:
            if prov_key == "openai":
                self.model_choice.Append("gpt-4o")
                self.model_choice.Append("gpt-4o-mini")
            elif prov_key == "claude":
                self.model_choice.Append("claude-3-5-sonnet-20241022")
                self.model_choice.Append("claude-3-5-haiku-20241022")
        if self.model_choice.GetCount() > 0:
            self.model_choice.SetSelection(0)
    
    def load_prompts(self):
        """Load available prompt styles via layered config resolution."""
        self.prompt_choice.Clear()
        prompts_added = False
        if loader_load_json_config:
            try:
                cfg, path, source = loader_load_json_config('image_describer_config.json', env_var_file='IDT_IMAGE_DESCRIBER_CONFIG')
                if cfg:
                    prompts = cfg.get('prompt_variations', {})
                    for prompt_name in prompts.keys():
                        self.prompt_choice.Append(prompt_name)
                        prompts_added = True
            except Exception:
                pass
        if not prompts_added:
            try:
                if loader_load_json_config:
                    config, _, _ = loader_load_json_config('image_describer_config.json')
                    prompts = config.get('prompt_variations', {})
                    for prompt_name in prompts.keys():
                        self.prompt_choice.Append(prompt_name)
                        prompts_added = True
            except Exception:
                pass
        if not prompts_added:
            self.prompt_choice.Append("narrative")
        if self.prompt_choice.GetCount() > 0:
            narrative_idx = self.prompt_choice.FindString("narrative")
            self.prompt_choice.SetSelection(narrative_idx if narrative_idx != wx.NOT_FOUND else 0)
    
    def get_selections(self):
        """Get selected provider, model, and prompt"""
        provider = self.provider_choice.GetStringSelection()
        model = self.model_choice.GetStringSelection()
        prompt = self.prompt_choice.GetStringSelection()
        return provider, model, prompt


class LiveMonitorThread(threading.Thread):
    """Background thread for monitoring workflow progress"""
    
    def __init__(self, viewer, workflow_dir):
        super().__init__(daemon=True)
        self.viewer = viewer
        self.workflow_dir = Path(workflow_dir)
        self.running = True
        # Check multiple possible locations for the descriptions file
        possible_locations = [
            self.workflow_dir / "descriptions" / "image_descriptions.txt",
            self.workflow_dir / "descriptions.txt",
            self.workflow_dir / "image_descriptions.txt",
        ]
        self.descriptions_file = None
        for loc in possible_locations:
            if loc.exists():
                self.descriptions_file = loc
                break
        if not self.descriptions_file:
            # Default to most likely location
            self.descriptions_file = self.workflow_dir / "descriptions" / "image_descriptions.txt"
        self.last_modified = 0
    
    def run(self):
        """Monitor descriptions file for changes"""
        while self.running:
            try:
                if self.descriptions_file.exists():
                    stat = self.descriptions_file.stat()
                    if stat.st_mtime > self.last_modified:
                        self.last_modified = stat.st_mtime
                        # Notify viewer to refresh
                        wx.CallAfter(self.viewer.on_live_update)
            except:
                pass
            
            time.sleep(2)  # Check every 2 seconds
    
    def stop(self):
        """Stop monitoring"""
        self.running = False


class ImageDescriptionViewer(wx.Frame):
    """Main viewer window with complete functionality"""
    
    def __init__(self, auto_load_dir=None):
        super().__init__(None, title="Image Description Viewer", size=(1200, 800))
        
        self.current_dir = None
        self.workflow_name = None
        self.image_files = []
        self.descriptions = []
        self.current_index = -1
        self.monitor_thread = None
        self.is_live = False
        
        # Create menu bar
        self.create_menu()
        
        # Create main panel with splitter
        splitter = wx.SplitterWindow(self)
        
        # Left panel - list of descriptions
        left_panel = wx.Panel(splitter)
        left_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Controls
        controls_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        refresh_btn = wx.Button(left_panel, label="Refresh")
        refresh_btn.Bind(wx.EVT_BUTTON, self.on_refresh)
        controls_sizer.Add(refresh_btn, 0, wx.ALL, 5)
        
        self.live_checkbox = wx.CheckBox(left_panel, label="Live Mode")
        self.live_checkbox.Bind(wx.EVT_CHECKBOX, self.on_live_toggle)
        controls_sizer.Add(self.live_checkbox, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        
        left_sizer.Add(controls_sizer, 0, wx.ALL | wx.EXPAND, 5)
        
        # Description list
        list_label = wx.StaticText(left_panel, label="Descriptions:")
        left_sizer.Add(list_label, 0, wx.ALL, 5)
        
        # Use custom accessible listbox that provides full descriptions to screen readers
        # while displaying truncated text visually (100 chars)
        # See ACCESSIBLE_LISTBOX_PATTERN.txt for details
        self.desc_list = DescriptionListBox(left_panel, style=wx.LB_SINGLE)
        self.desc_list.Bind(wx.EVT_LISTBOX, self.on_description_selected)
        left_sizer.Add(self.desc_list, 1, wx.ALL | wx.EXPAND, 5)
        
        left_panel.SetSizer(left_sizer)
        
        # Right panel - description details
        right_panel = wx.Panel(splitter)
        right_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Image preview
        # Use a focusable StaticBitmap for proper screen reader announcement
        self.image_panel = wx.Panel(right_panel, style=wx.BORDER_SIMPLE)
        self.image_panel.SetMinSize((400, 300))
        
        image_sizer = wx.BoxSizer(wx.VERTICAL)
        # Add label for filename display
        self.image_filename_label = wx.StaticText(self.image_panel, label="")
        self.image_filename_label.SetForegroundColour(wx.Colour(0, 102, 204))
        image_sizer.Add(self.image_filename_label, 0, wx.ALL | wx.ALIGN_CENTER, 2)
        
        # StaticBitmap for the actual image (non-focusable - it's just a static display)
        self.image_label = wx.StaticBitmap(self.image_panel)
        image_sizer.Add(self.image_label, 1, wx.ALL | wx.ALIGN_CENTER, 5)
        self.image_panel.SetSizer(image_sizer)
        
        right_sizer.Add(self.image_panel, 0, wx.ALL | wx.ALIGN_CENTER, 5)
        
        # Metadata label
        self.metadata_label = wx.StaticText(right_panel, label="")
        self.metadata_label.SetForegroundColour(wx.Colour(0, 102, 204))
        font = self.metadata_label.GetFont()
        font.MakeBold()
        self.metadata_label.SetFont(font)
        right_sizer.Add(self.metadata_label, 0, wx.ALL | wx.EXPAND, 5)
        
        # Description text
        desc_label = wx.StaticText(right_panel, label="Description:")
        right_sizer.Add(desc_label, 0, wx.ALL, 5)
        
        self.desc_text = wx.TextCtrl(right_panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP)
        right_sizer.Add(self.desc_text, 1, wx.ALL | wx.EXPAND, 5)
        
        # Button panel
        btn_panel = wx.Panel(right_panel)
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        copy_desc_btn = wx.Button(btn_panel, label="Copy Description")
        copy_desc_btn.Bind(wx.EVT_BUTTON, self.on_copy_description)
        btn_sizer.Add(copy_desc_btn, 0, wx.ALL, 5)
        
        copy_path_btn = wx.Button(btn_panel, label="Copy Image Path")
        copy_path_btn.Bind(wx.EVT_BUTTON, self.on_copy_path)
        btn_sizer.Add(copy_path_btn, 0, wx.ALL, 5)
        
        copy_img_btn = wx.Button(btn_panel, label="Copy Image")
        copy_img_btn.Bind(wx.EVT_BUTTON, self.on_copy_image)
        btn_sizer.Add(copy_img_btn, 0, wx.ALL, 5)
        
        btn_panel.SetSizer(btn_sizer)
        right_sizer.Add(btn_panel, 0, wx.ALL | wx.EXPAND, 5)
        
        # Workflow action buttons
        workflow_panel = wx.Panel(right_panel)
        workflow_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        redescribe_btn = wx.Button(workflow_panel, label="Redescribe Image")
        redescribe_btn.Bind(wx.EVT_BUTTON, self.on_redescribe_image)
        workflow_sizer.Add(redescribe_btn, 0, wx.ALL, 5)
        
        resume_btn = wx.Button(workflow_panel, label="Resume Workflow")
        resume_btn.Bind(wx.EVT_BUTTON, self.on_resume_workflow)
        workflow_sizer.Add(resume_btn, 0, wx.ALL, 5)
        
        redescribe_workflow_btn = wx.Button(workflow_panel, label="Redescribe Workflow")
        redescribe_workflow_btn.Bind(wx.EVT_BUTTON, self.on_redescribe_workflow)
        workflow_sizer.Add(redescribe_workflow_btn, 0, wx.ALL, 5)
        
        workflow_panel.SetSizer(workflow_sizer)
        right_sizer.Add(workflow_panel, 0, wx.ALL | wx.EXPAND, 5)
        
        right_panel.SetSizer(right_sizer)
        
        # Setup splitter
        splitter.SplitVertically(left_panel, right_panel)
        splitter.SetSashPosition(400)
        splitter.SetMinimumPaneSize(200)
        
        # Status bar
        self.CreateStatusBar()
        self.SetStatusText("Ready - No workflow loaded")
        
        # Auto-load if specified
        if auto_load_dir:
            wx.CallAfter(self.load_descriptions, auto_load_dir)
        
        self.Bind(wx.EVT_CLOSE, self.on_close)
        # Bind key events for navigation shortcuts
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)
    
    def create_menu(self):
        """Create menu bar"""
        menubar = wx.MenuBar()
        
        # File menu
        file_menu = wx.Menu()
        browse_item = file_menu.Append(wx.ID_ANY, "Browse Workflows...\tCtrl+B")
        open_item = file_menu.Append(wx.ID_OPEN, "Open Directory...\tCtrl+O")
        change_item = file_menu.Append(wx.ID_ANY, "Change Directory...\tCtrl+D")
        file_menu.AppendSeparator()
        quit_item = file_menu.Append(wx.ID_EXIT, "Quit\tCtrl+Q")
        
        menubar.Append(file_menu, "&File")
        
        # View menu
        view_menu = wx.Menu()
        refresh_item = view_menu.Append(wx.ID_REFRESH, "Refresh\tF5")
        live_item = view_menu.AppendCheckItem(wx.ID_ANY, "Live Mode\tCtrl+L")
        
        menubar.Append(view_menu, "&View")
        
        # Workflow menu
        workflow_menu = wx.Menu()
        redesc_img_item = workflow_menu.Append(wx.ID_ANY, "Redescribe Image\tCtrl+R")
        resume_item = workflow_menu.Append(wx.ID_ANY, "Resume Workflow")
        redesc_wf_item = workflow_menu.Append(wx.ID_ANY, "Redescribe Workflow")
        
        menubar.Append(workflow_menu, "&Workflow")
        
        self.SetMenuBar(menubar)
        
        # Bind menu events
        self.Bind(wx.EVT_MENU, self.on_browse_workflows, browse_item)
        self.Bind(wx.EVT_MENU, self.on_open_directory, open_item)
        self.Bind(wx.EVT_MENU, self.on_change_directory, change_item)
        self.Bind(wx.EVT_MENU, self.on_quit, quit_item)
        self.Bind(wx.EVT_MENU, self.on_refresh, refresh_item)
        self.Bind(wx.EVT_MENU, lambda e: self.live_checkbox.SetValue(not self.live_checkbox.GetValue()), live_item)
        self.Bind(wx.EVT_MENU, self.on_redescribe_image, redesc_img_item)
        self.Bind(wx.EVT_MENU, self.on_resume_workflow, resume_item)
        self.Bind(wx.EVT_MENU, self.on_redescribe_workflow, redesc_wf_item)
    
    def on_browse_workflows(self, event):
        """Open workflow browser dialog"""
        dlg = WorkflowBrowserDialog(self)
        if dlg.ShowModal() == wx.ID_OK and dlg.selected_workflow:
            self.load_descriptions(str(dlg.selected_workflow))
        dlg.Destroy()
    
    def on_open_directory(self, event):
        """Open directory picker"""
        path = select_directory_dialog(self, "Select Workflow Directory")
        if path:
            self.load_descriptions(path)
    
    def on_change_directory(self, event):
        """Change to different directory"""
        self.on_open_directory(event)
    
    def on_quit(self, event):
        """Quit application"""
        self.Close()
    
    def on_close(self, event):
        """Handle window close"""
        # Stop monitoring thread
        if self.monitor_thread:
            self.monitor_thread.stop()
            self.monitor_thread = None
        event.Skip()
    
    def on_char_hook(self, event):
        """Handle keyboard shortcuts for navigation"""
        keycode = event.GetKeyCode()
        
        # Check for Cmd+Left/Right (macOS) or Alt+Left/Right (Windows)
        if keycode in (wx.WXK_LEFT, wx.WXK_RIGHT):
            # macOS: Cmd key, Windows: Alt key
            if event.CmdDown() or event.AltDown():
                # Remember if focus is in description text box
                focused_widget = wx.Window.FindFocus()
                preserve_focus = (focused_widget == self.desc_text)
                
                current_sel = self.desc_list.GetSelection()
                if current_sel != wx.NOT_FOUND:
                    if keycode == wx.WXK_LEFT:
                        # Previous image
                        new_sel = max(0, current_sel - 1)
                    else:
                        # Next image
                        new_sel = min(self.desc_list.GetCount() - 1, current_sel + 1)
                    
                    if new_sel != current_sel:
                        self.desc_list.SetSelection(new_sel)
                        self.display_description(new_sel)
                        
                        # Restore focus to description text if it was there
                        if preserve_focus:
                            self.desc_text.SetFocus()
                
                return  # Don't skip - we handled it
        
        event.Skip()  # Let other handlers process the event
    
    def on_refresh(self, event):
        """Manually refresh descriptions"""
        if self.current_dir:
            current_sel = self.desc_list.GetSelection()
            self.load_descriptions(self.current_dir, preserve_selection=current_sel)
    
    def on_live_toggle(self, event):
        """Toggle live monitoring mode"""
        self.is_live = self.live_checkbox.GetValue()
        
        if self.is_live:
            # Start monitoring thread
            if self.current_dir and not self.monitor_thread:
                self.monitor_thread = LiveMonitorThread(self, self.current_dir)
                self.monitor_thread.start()
            self.SetStatusText("Live Mode: Monitoring for changes...")
        else:
            # Stop monitoring thread
            if self.monitor_thread:
                self.monitor_thread.stop()
                self.monitor_thread = None
            self.SetStatusText("Live Mode: Off")
    
    def get_progress_info(self):
        """Get description progress from progress file.
        
        Returns:
            Tuple of (completed_count, total_count) or (desc_count, desc_count) if progress file not found
        """
        # Try to read progress from image_describer_progress.txt
        progress_file = self.current_dir / 'logs' / 'image_describer_progress.txt'
        if progress_file.exists():
            try:
                with open(progress_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    # Last line has format: "Processed X of Y images"
                    if lines:
                        last_line = lines[-1].strip()
                        import re
                        match = re.search(r'Processed (\d+) of (\d+)', last_line)
                        if match:
                            completed = int(match.group(1))
                            total = int(match.group(2))
                            return (completed, total)
            except Exception:
                pass
        
        # Fallback: return current description count as both values
        desc_count = len(self.descriptions)
        return (desc_count, desc_count)
    
    def on_live_update(self):
        """Called by monitoring thread when file changes - incrementally adds new entries"""
        if not self.is_live or not self.current_dir:
            return
        
        # Check if user is actively interacting - if so, defer update
        focused_widget = wx.Window.FindFocus()
        if focused_widget in [self.desc_list, self.desc_text]:
            # User is actively using the interface - don't disrupt them
            return
        
        # Save current state
        current_sel = self.desc_list.GetSelection()
        current_count = len(self.descriptions)
        
        # Find and parse the descriptions file
        desc_file = None
        possible_locations = [
            self.current_dir / "descriptions" / "image_descriptions.txt",
            self.current_dir / "descriptions.txt",
            self.current_dir / "image_descriptions.txt",
        ]
        
        for loc in possible_locations:
            if loc.exists():
                desc_file = loc
                break
        
        if not desc_file:
            return
        
        # Parse all entries
        entries = self.parse_descriptions_file(desc_file)
        
        if not entries or len(entries) <= current_count:
            # No new entries
            return
        
        # Add only new entries (incremental update)
        new_entries = entries[current_count:]
        
        for entry in new_entries:
            self.descriptions.append(entry['description'])
            self.image_files.append(entry['file_path'])
        
        # Add new entries to listbox without clearing
        for entry in new_entries:
            # Append to the existing DescriptionListBox
            description = entry.get('description', '')
            truncated = (description[:100] + "..." 
                        if len(description) > 100 
                        else description)
            self.desc_list.Append(truncated)
            # Also update the internal data
            self.desc_list.descriptions_data.append(entry)
        
        # Update window title with progress - get actual counts from progress file
        desc_count = len(self.descriptions)
        completed, total = self.get_progress_info()
        
        if total > 0:
            percentage = int((completed / total) * 100)
            title = f"{percentage}%, {completed} of {total} images described (Live)"
        else:
            # Fallback if no progress info
            percentage = 100
            title = f"{percentage}%, {desc_count} of {desc_count} images described (Live)"
        
        self.SetTitle(f"{title} - {self.workflow_name}")
        
        # Update status
        self.SetStatusText(f"Live update: {desc_count} descriptions (+{len(new_entries)} new)")
        
        # Preserve current selection
        if current_sel >= 0 and current_sel < self.desc_list.GetCount():
            self.desc_list.SetSelection(current_sel)
    
    def on_description_selected(self, event):
        """Handle selection change in description list"""
        index = self.desc_list.GetSelection()
        if index != wx.NOT_FOUND:
            self.display_description(index)
    
    def load_descriptions(self, directory, preserve_selection=-1):
        """Load descriptions from workflow directory"""
        self.current_dir = Path(directory)
        prev_count = len(self.descriptions)
        self.descriptions = []
        self.image_files = []
        
        # Find descriptions file - check multiple possible locations
        possible_locations = [
            self.current_dir / "descriptions" / "image_descriptions.txt",  # Standard location
            self.current_dir / "Descriptions" / "image_descriptions.txt",  # Capitalized subdirectory
            self.current_dir / "image_descriptions.txt",  # Root of workflow
        ]
        
        desc_file = None
        for location in possible_locations:
            if location.exists():
                desc_file = location
                break
        
        if not desc_file:
            # Show what we found to help debug
            msg = f"No image_descriptions.txt file found.\n\nSearched in:\n{self.current_dir}\n\n"
            msg += "Checked locations:\n"
            for loc in possible_locations:
                msg += f"  • {loc.relative_to(self.current_dir) if loc.is_relative_to(self.current_dir) else loc}\n"
            
            # List what files ARE in the directory
            if self.current_dir.exists():
                msg += f"\nContents of {self.current_dir.name}:\n"
                try:
                    items = sorted(self.current_dir.iterdir(), key=lambda x: (not x.is_dir(), x.name))[:20]
                    for item in items:
                        if item.is_dir():
                            msg += f"  📁 {item.name}/\n"
                        else:
                            msg += f"  📄 {item.name}\n"
                    if len(list(self.current_dir.iterdir())) > 20:
                        msg += f"  ... and {len(list(self.current_dir.iterdir())) - 20} more items\n"
                except:
                    msg += "  (Unable to list directory contents)\n"
            
            show_warning(self, msg, "Descriptions File Not Found")
            self.SetStatusText("No workflow loaded")
            return
        
        # Load workflow metadata
        metadata_file = self.current_dir / "workflow_metadata.json"
        if metadata_file.exists():
            try:
                if loader_load_json_config:
                    metadata, _, _ = loader_load_json_config(explicit=str(metadata_file))
                    self.workflow_name = metadata.get('name', self.current_dir.name)
                else:
                    self.workflow_name = self.current_dir.name
            except:
                self.workflow_name = self.current_dir.name
        else:
            self.workflow_name = self.current_dir.name
        
        # Parse descriptions file
        entries = self.parse_descriptions_file(desc_file)
        self.descriptions = [e['description'] for e in entries]
        self.image_files = [e['file_path'] for e in entries]
        
        # Load descriptions using custom accessible listbox
        # This shows truncated text (100 chars) visually but provides full descriptions to screen readers
        # Replaces the old Clear() + Append() loop
        self.desc_list.LoadDescriptions(entries)

        # Update window title with progress - get actual counts from progress file
        desc_count = len(self.descriptions)
        completed, total = self.get_progress_info()
        
        # Check if we have real progress info (progress file exists and has different value)
        progress_file = self.current_dir / 'logs' / 'image_describer_progress.txt'
        has_progress_file = progress_file.exists()
        
        if has_progress_file and total > 0 and completed < total:
            # In-progress workflow with actual progress tracking
            percentage = int((completed / total) * 100)
            title = f"{percentage}%, {completed} of {total} images described"
        else:
            # Complete workflow or no progress tracking
            percentage = 100
            title = f"{percentage}%, {desc_count} of {desc_count} images described"
        
        if self.is_live:
            title += " (Live)"
        
        self.SetTitle(f"{title} - {self.workflow_name}")
        
        # Update status
        if self.is_live and desc_count > prev_count:
            self.SetStatusText(f"Live update: {desc_count} descriptions (+{desc_count - prev_count})")
        else:
            self.SetStatusText(f"Loaded {desc_count} descriptions from {self.workflow_name}")
        
        # Restore or set selection
        if preserve_selection >= 0 and preserve_selection < self.desc_list.GetCount():
            self.desc_list.SetSelection(preserve_selection)
            self.display_description(preserve_selection)
        elif self.desc_list.GetCount() > 0:
            self.desc_list.SetSelection(0)
            self.display_description(0)
        
        # Set focus to the description list for immediate keyboard navigation
        if self.desc_list.GetCount() > 0:
            self.desc_list.SetFocus()
    
    def parse_descriptions_file(self, file_path):
        """Parse the descriptions.txt file"""
        descriptions = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            separator = '-' * 80
            sections = content.split(separator)
            
            # Parse all sections, not just sections[1:] - this handles both old and new file formats
            # The first section may contain only the header, or header + first description (in older files)
            for section in sections:
                if not section.strip():
                    continue
                
                # Skip sections that are pure header with no image entries
                # Pure headers contain metadata but no "File:" entries for actual images
                section_lower = section.lower()
                if ('image descriptions generated' in section_lower and 'file:' not in section_lower):
                    continue
                
                desc = self.parse_entry(section.strip())
                if desc:
                    descriptions.append(desc)
        
        except Exception as e:
            print(f"Error parsing descriptions: {e}")
        
        return descriptions
    
    def parse_entry(self, section):
        """Parse a single description entry"""
        lines = section.split('\n')
        entry = {
            'file_path': '',
            'relative_path': '',
            'description': '',
            'model': '',
            'prompt_style': '',
            'photo_date': '',
            'camera': '',
            'source': ''
        }
        
        description_started = False
        description_lines = []
        
        for line in lines:
            line_stripped = line.strip()
            
            if not line_stripped:
                if description_started:
                    description_lines.append('')
                continue
            
            # Parse metadata fields
            if line_stripped.startswith('File: '):
                entry['relative_path'] = line_stripped[6:].strip()
            elif line_stripped.startswith('Path: '):
                entry['file_path'] = line_stripped[6:].strip()
            elif line_stripped.startswith('Model: '):
                entry['model'] = line_stripped[7:].strip()
            elif line_stripped.startswith('Prompt Style: '):
                entry['prompt_style'] = line_stripped[14:].strip()
            elif line_stripped.startswith('Photo Date: '):
                entry['photo_date'] = line_stripped[12:].strip()
            elif line_stripped.startswith('Camera: '):
                entry['camera'] = line_stripped[8:].strip()
            elif line_stripped.startswith('Source: '):
                entry['source'] = line_stripped[8:].strip()
            elif line_stripped.startswith('Provider: '):
                pass  # Ignore provider line
            elif line_stripped.startswith('Timestamp: '):
                pass  # Ignore timestamp line
            elif line_stripped.startswith('Description: '):
                description_started = True
                desc_text = line_stripped[13:].strip()
                if desc_text:
                    description_lines.append(desc_text)
            elif line_stripped.startswith('[') and line_stripped.endswith(']'):
                # Skip summary lines like "[12/31/2001 8:00A, CAMERA]"
                continue
            elif description_started and not line_stripped.startswith(('Timestamp:', 'File:', 'Path:', 'Source:', 'Model:', 'Prompt Style:', 'Photo Date:', 'Camera:', 'Provider:')):
                # This is part of the description
                description_lines.append(line_stripped)
        
        if description_lines:
            entry['description'] = '\n'.join(description_lines).strip()
        
        # Return entry only if it has both a file path and description
        return entry if (entry['description'] and entry['file_path']) else None
    
    def on_description_selected(self, event):
        """Handle description selection"""
        sel = self.desc_list.GetSelection()
        if sel != wx.NOT_FOUND:
            self.display_description(sel)
    
    def on_list_key_down(self, event):
        """Handle keyboard navigation in list"""
        keycode = event.GetKeyCode()
        
        if keycode == wx.WXK_UP or keycode == wx.WXK_DOWN:
            event.Skip()  # Let default handling work
            wx.CallAfter(self.update_after_key_nav)
        elif keycode == wx.WXK_RETURN:
            # Enter key - just display current
            sel = self.desc_list.GetSelection()
            if sel != wx.NOT_FOUND:
                self.display_description(sel)
        else:
            event.Skip()
    
    def update_after_key_nav(self):
        """Update display after keyboard navigation"""
        sel = self.desc_list.GetSelection()
        if sel != wx.NOT_FOUND:
            self.display_description(sel)
    
    def display_description(self, index):
        """Display the selected description"""
        if 0 <= index < len(self.descriptions):
            self.current_index = index
            desc = self.descriptions[index]
            
            # Display description text
            self.desc_text.SetValue(desc)
            
            # Update metadata if available
            # (would need to parse from entry dict - simplified here)
            self.metadata_label.SetLabel("")
            
            # Load and display image
            image_path = self.image_files[index]
            if image_path and Path(image_path).exists():
                # Set accessible name and label on the image bitmap for proper screen reader announcement
                img_filename = Path(image_path).name
                self.image_filename_label.SetLabel(img_filename)
                
                # Set the image label (StaticBitmap) properties for screen reader
                self.image_label.SetName(img_filename)
                self.image_label.SetLabel(f"Graphic: {img_filename}")
                
                self.load_image(image_path)
            else:
                self.image_filename_label.SetLabel("")
                self.image_label.SetName("")
                self.image_label.SetLabel("")
                self.image_label.SetBitmap(wx.NullBitmap)
    
    def load_image(self, image_path):
        """Load and display image with size constraint"""
        try:
            img = wx.Image(image_path, wx.BITMAP_TYPE_ANY)
            
            # Scale to max 500x500 while maintaining aspect ratio
            max_size = 500
            width, height = img.GetWidth(), img.GetHeight()
            
            if width > max_size or height > max_size:
                if width > height:
                    new_width = max_size
                    new_height = int(height * (max_size / width))
                else:
                    new_height = max_size
                    new_width = int(width * (max_size / height))
                
                img = img.Scale(new_width, new_height, wx.IMAGE_QUALITY_HIGH)
            
            bitmap = wx.Bitmap(img)
            self.image_label.SetBitmap(bitmap)
        
        except Exception as e:
            print(f"Error loading image: {e}")
            self.image_label.SetBitmap(wx.NullBitmap)
    
    def on_copy_description(self, event):
        """Copy description to clipboard"""
        if self.current_index >= 0:
            desc = self.descriptions[self.current_index]
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(wx.TextDataObject(desc))
                wx.TheClipboard.Close()
                self.SetStatusText("Description copied to clipboard")
    
    def on_copy_path(self, event):
        """Copy image path to clipboard"""
        if self.current_index >= 0:
            path = self.image_files[self.current_index]
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(wx.TextDataObject(path))
                wx.TheClipboard.Close()
                self.SetStatusText("Image path copied to clipboard")
    
    def on_copy_image(self, event):
        """Copy image to clipboard"""
        if self.current_index >= 0:
            image_path = self.image_files[self.current_index]
            if Path(image_path).exists():
                try:
                    img = wx.Image(image_path, wx.BITMAP_TYPE_ANY)
                    bitmap = wx.Bitmap(img)
                    
                    if wx.TheClipboard.Open():
                        wx.TheClipboard.SetData(wx.BitmapDataObject(bitmap))
                        wx.TheClipboard.Close()
                        self.SetStatusText("Image copied to clipboard")
                except:
                    show_error(self, "Failed to copy image", "Error")
    
    def on_redescribe_image(self, event):
        """Redescribe the current image"""
        if self.current_index < 0:
            show_info(self, "Please select an image first", "No Selection")
            return
        
        if not ollama:
            show_error(self, "Ollama is not available. Please install Ollama to redescribe images.", 
                      "Ollama Not Available")
            return
        
        dlg = RedescribeDialog(self)
        if dlg.ShowModal() == wx.ID_OK:
            model, prompt = dlg.get_selections()
            if model and prompt:
                self.redescribe_image_with_model(self.image_files[self.current_index], model, prompt)
        dlg.Destroy()
    
    def redescribe_image_with_model(self, image_path, model, prompt_style):
        """Redescribe image with specified model and prompt"""
        # This would need to call the image_describer module
        # For now, show a message
        show_info(self, f"Redescribing with {model} and {prompt_style}\n\n"
                 "This feature requires integration with image_describer module.")
    
    def on_resume_workflow(self, event):
        """Resume the current workflow"""
        if not self.current_dir:
            show_info(self, "Please load a workflow first")
            return
        
        # Load metadata to determine provider
        metadata_file = self.current_dir / "workflow_metadata.json"
        if not metadata_file.exists():
            show_error(self, "Could not find workflow metadata")
            return
        
        try:
            if loader_load_json_config:
                metadata, _, _ = loader_load_json_config(explicit=str(metadata_file))
            else:
                # Fallback if config_loader not available
                with open(metadata_file) as f:
                    metadata = json.load(f)
            
            provider = metadata.get('provider', 'ollama')
            
            # Check if API key needed
            api_key_file = None
            if provider.lower() in ['openai', 'claude']:
                dlg = ApiKeyDialog(provider.capitalize(), self)
                if dlg.ShowModal() == wx.ID_OK:
                    api_key_file = dlg.get_api_key_file()
                else:
                    dlg.Destroy()
                    return
                dlg.Destroy()
            
            # Build command
            if getattr(sys, 'frozen', False):
                idt_exe = Path(sys.executable).parent / "idt"
                if not idt_exe.exists():
                    idt_exe = Path(sys.executable).parent / "idt.exe"
                cmd = [str(idt_exe), "workflow", "--resume", str(self.current_dir)]
            else:
                workflow_script = get_scripts_directory() / "workflow.py"
                cmd = [sys.executable, str(workflow_script), "--resume", str(self.current_dir)]
            
            if api_key_file:
                cmd.extend(["--api-key-file", api_key_file])
            
            # Confirm
            if ask_yes_no(self, f"Resume workflow: {self.workflow_name}?\n\nProvider: {provider}"):
                subprocess.Popen(cmd, cwd=str(self.current_dir.parent))
                show_info(self, "Workflow resume launched")
        
        except Exception as e:
            show_error(self, f"Failed to resume workflow:\n{e}")
    
    def on_redescribe_workflow(self, event):
        """Redescribe entire workflow"""
        if not self.current_dir:
            show_info(self, "Please load a workflow first")
            return
        
        dlg = RedescribeWorkflowDialog(self)
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()
            return
        
        provider, model, prompt_style = dlg.get_selections()
        dlg.Destroy()
        
        if not provider or not model or not prompt_style:
            show_warning(self, "Please select all options")
            return
        
        # Check if API key needed
        api_key_file = None
        provider_lower = provider.lower()
        if 'openai' in provider_lower or 'claude' in provider_lower:
            dlg = ApiKeyDialog(provider, self)
            if dlg.ShowModal() == wx.ID_OK:
                api_key_file = dlg.get_api_key_file()
            else:
                dlg.Destroy()
                return
            dlg.Destroy()
        
        # Map provider names
        provider_map = {
            "Ollama": "ollama",
            "Ollama Cloud": "ollama-cloud",
            "OpenAI": "openai",
            "Claude": "claude"
        }
        provider_cmd = provider_map.get(provider, provider.lower())
        
        # Build command
        if getattr(sys, 'frozen', False):
            idt_exe = Path(sys.executable).parent / "idt"
            if not idt_exe.exists():
                idt_exe = Path(sys.executable).parent / "idt.exe"
            cmd = [str(idt_exe), "workflow", "--redescribe", str(self.current_dir)]
        else:
            workflow_script = get_scripts_directory() / "workflow.py"
            cmd = [sys.executable, str(workflow_script), "--redescribe", str(self.current_dir)]
        
        cmd.extend([
            "--provider", provider_cmd,
            "--model", model,
            "--prompt-style", prompt_style
        ])
        
        if api_key_file:
            cmd.extend(["--api-key-file", api_key_file])
        
        # Confirm
        if ask_yes_no(self,
            f"Redescribe all images in: {self.workflow_name}?\n\n"
            f"Provider: {provider}\nModel: {model}\nPrompt: {prompt_style}\n\n"
            f"This will create a new workflow directory."):
            try:
                subprocess.Popen(cmd, cwd=str(self.current_dir.parent))
                show_info(self, "Redescribe workflow launched")
            except Exception as e:
                show_error(self, f"Failed to launch redescribe:\n{e}")


def main():
    app = wx.App()
    
    frame = ImageDescriptionViewer()
    frame.Show()
    
    # Check for command-line argument (workflow directory path)
    if len(sys.argv) > 1:
        workflow_path = Path(sys.argv[1])
        if workflow_path.exists() and workflow_path.is_dir():
            # Load the specified workflow directly
            wx.CallAfter(frame.load_workflow, workflow_path)
        else:
            show_error(frame, f"Invalid workflow path: {workflow_path}", "Invalid Path")
            wx.CallAfter(frame.on_browse_workflows, None)
    else:
        # No argument - show browse dialog on startup
        wx.CallAfter(frame.on_browse_workflows, None)
    
    app.MainLoop()


if __name__ == "__main__":
    main()
