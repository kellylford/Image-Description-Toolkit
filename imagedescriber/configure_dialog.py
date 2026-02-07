#!/usr/bin/env python3
"""
Configure Dialog for ImageDescriber

Dialog version of IDT Configure for integration into ImageDescriber.
Manages configuration files:
- image_describer_config.json
- video_frame_extractor_config.json
- workflow_config.json

Features:
- Tabbed interface for configuration categories
- Settings list with arrow navigation
- Type-specific editors (bool, int, float, choice, string)
- Screen reader readable explanations
- Save/Load functionality
- Professional, accessible interface
- Dialog buttons: OK (save & close), Cancel (discard), Apply (save & continue)
"""

import sys
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

import wx
import wx.lib.masked as masked

# Ensure project root is on sys.path so sibling modules (shared/) import in dev and frozen modes
# Works in both development mode (running script) and frozen mode (PyInstaller exe)
if getattr(sys, 'frozen', False):
    # Frozen mode - executable directory is base
    _project_root = Path(sys.executable).parent
else:
    # Development mode - use __file__ relative path
    _project_root = Path(__file__).parent.parent

if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# Import shared utilities
try:
    from shared.wx_common import (
        find_config_file,
        ConfigManager,
        show_error,
        show_warning,
        show_info,
        open_file_dialog,
        save_file_dialog,
        show_about_dialog,
        get_app_version,
    )
except ImportError as e:
    print(f"ERROR: Cannot import shared.wx_common: {e}")
    print("This indicates a PyInstaller build issue or missing dependency.")
    sys.exit(1)


class SettingEditDialog(wx.Dialog):
    """Dialog for editing a single setting value"""
    
    def __init__(self, parent, setting_name: str, current_value: Any, setting_info: Dict[str, Any]):
        super().__init__(parent, title=f"Edit: {setting_name}", size=(450, 250))
        
        self.setting_name = setting_name
        self.current_value = current_value
        self.setting_info = setting_info
        self.new_value = None
        
        self.setup_ui()
    
    def setup_ui(self):
        """Create the dialog UI"""
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Add description
        if "description" in self.setting_info:
            desc_text = wx.StaticText(panel, label=self.setting_info["description"])
            desc_text.Wrap(400)
            sizer.Add(desc_text, 0, wx.ALL, 10)
        
        # Create appropriate editor based on setting type
        setting_type = self.setting_info.get("type", "string")
        
        form_sizer = wx.FlexGridSizer(rows=2, cols=2, vgap=5, hgap=5)
        form_sizer.AddGrowableCol(1, 1)
        
        form_sizer.Add(wx.StaticText(panel, label="Value:"), 0, wx.ALIGN_CENTER_VERTICAL)
        
        if setting_type == "bool":
            self.editor = wx.CheckBox(panel)
            self.editor.SetValue(bool(self.current_value))
            form_sizer.Add(self.editor, 0, wx.EXPAND)
            
        elif setting_type == "int":
            self.editor = wx.SpinCtrl(panel)
            if "range" in self.setting_info:
                self.editor.SetRange(self.setting_info["range"][0], self.setting_info["range"][1])
            else:
                self.editor.SetRange(-999999, 999999)
            self.editor.SetValue(int(self.current_value or 0))
            form_sizer.Add(self.editor, 0, wx.EXPAND)
            
        elif setting_type == "float":
            self.editor = wx.TextCtrl(panel)
            self.editor.SetValue(str(float(self.current_value or 0.0)))
            form_sizer.Add(self.editor, 0, wx.EXPAND)
            
        elif setting_type == "choice":
            self.editor = wx.Choice(panel)
            choices = self.setting_info.get("choices", [])
            self.editor.Append(choices)
            if self.current_value in choices:
                self.editor.SetStringSelection(str(self.current_value))
            form_sizer.Add(self.editor, 0, wx.EXPAND)
            
        else:  # string or other
            self.editor = wx.TextCtrl(panel)
            self.editor.SetValue(str(self.current_value or ""))
            form_sizer.Add(self.editor, 0, wx.EXPAND)
        
        # Add range/limits info if available
        if "range" in self.setting_info:
            form_sizer.Add(wx.StaticText(panel, label=""), 0)
            range_label = wx.StaticText(panel, label=f"Range: {self.setting_info['range'][0]} to {self.setting_info['range'][1]}")
            form_sizer.Add(range_label, 0)
        
        sizer.Add(form_sizer, 0, wx.EXPAND | wx.ALL, 10)
        
        # Buttons
        btn_sizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 10)
        
        panel.SetSizer(sizer)
        self.Fit()
    
    def GetValue(self):
        """Get the new value from the editor"""
        setting_type = self.setting_info.get("type", "string")
        
        if setting_type == "bool":
            return self.editor.GetValue()
        elif setting_type == "int":
            return self.editor.GetValue()
        elif setting_type == "float":
            try:
                return float(self.editor.GetValue())
            except ValueError:
                return 0.0
        elif setting_type == "choice":
            return self.editor.GetStringSelection()
        else:
            return self.editor.GetValue()


class ConfigureDialog(wx.Dialog):
    """Dialog for managing IDT configuration settings"""
    
    def __init__(self, parent):
        super().__init__(parent, title="IDT Configure - Configuration Manager", size=(900, 650))
        
        # Find config files
        self.scripts_dir = self.find_scripts_directory()
        
        # Configuration file paths
        self.config_files = {
            "image_describer": self.scripts_dir / "image_describer_config.json",
            "video_extractor": self.scripts_dir / "video_frame_extractor_config.json",
            "workflow": self.scripts_dir / "workflow_config.json"
        }
        
        # Current configuration data
        self.configs = {}
        
        # Settings metadata for each category
        self.settings_metadata = self.build_settings_metadata()
        
        # Category tab widgets (for refreshing on changes)
        self.category_widgets = {}
        
        # Load all configs
        self.load_all_configs()
        
        # UI setup
        self.init_ui()
        
        # Bind close event
        self.Bind(wx.EVT_CLOSE, self.on_dialog_close)
    
    def find_scripts_directory(self) -> Path:
        """Find the scripts directory containing config files"""
        # Try relative to executable
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            app_dir = Path(sys.executable).parent
        else:
            # Running as script
            app_dir = Path(__file__).parent.parent
        
        scripts_dir = app_dir / "scripts"
        if scripts_dir.exists():
            return scripts_dir
        
        # Try current directory
        scripts_dir = Path.cwd() / "scripts"
        if scripts_dir.exists():
            return scripts_dir
        
        # Default fallback
        return Path.cwd()
    
    def build_settings_metadata(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Build metadata for all settings organized by category"""
        return {
            "AI Model Settings": {
                "default_model": {
                    "file": "image_describer",
                    "path": ["default_model"],
                    "type": "string",
                    "description": "Default Ollama model to use for image descriptions. Examples: moondream:latest, llama3.2-vision, llava"
                },
                "temperature": {
                    "file": "image_describer",
                    "path": ["model_settings", "temperature"],
                    "type": "float",
                    "range": [0.0, 2.0],
                    "description": "Controls randomness in AI responses (0.0 = deterministic/consistent, 2.0 = very creative/random). Recommended: 0.1-0.3 for consistent image descriptions."
                },
                "max_tokens": {
                    "file": "image_describer",
                    "path": ["model_settings", "num_predict"],
                    "type": "int",
                    "range": [50, 1000],
                    "description": "Maximum length of generated descriptions in tokens. Higher = longer descriptions. Recommended: 200-600 for balanced detail."
                },
                "top_k": {
                    "file": "image_describer",
                    "path": ["model_settings", "top_k"],
                    "type": "int",
                    "range": [1, 100],
                    "description": "Number of top tokens to consider. Lower = more focused, higher = more diverse. Recommended: 40."
                },
                "top_p": {
                    "file": "image_describer",
                    "path": ["model_settings", "top_p"],
                    "type": "float",
                    "range": [0.0, 1.0],
                    "description": "Cumulative probability cutoff for nucleus sampling. Lower = more focused, higher = more diverse. Recommended: 0.9."
                },
                "repeat_penalty": {
                    "file": "image_describer",
                    "path": ["model_settings", "repeat_penalty"],
                    "type": "float",
                    "range": [1.0, 2.0],
                    "description": "Penalty for repeating words/phrases. Higher = less repetition. Recommended: 1.1-1.3."
                }
            },
            "Prompt Styles": {
                "default_prompt_style": {
                    "file": "image_describer",
                    "path": ["default_prompt_style"],
                    "type": "choice",
                    "choices": ["detailed", "concise", "narrative", "artistic", "technical", "colorful", "Simple"],
                    "description": "Default prompt style for image descriptions. 'narrative' provides objective, detailed descriptions. 'artistic' focuses on composition and mood. 'technical' analyzes photographic aspects."
                }
            },
            "Video Extraction": {
                "extraction_mode": {
                    "file": "video_extractor",
                    "path": ["extraction_mode"],
                    "type": "choice",
                    "choices": ["time_interval", "scene_change"],
                    "description": "How to extract frames from videos. 'time_interval' extracts at regular intervals. 'scene_change' detects scene changes and extracts key frames."
                },
                "time_interval_seconds": {
                    "file": "video_extractor",
                    "path": ["time_interval_seconds"],
                    "type": "float",
                    "range": [0.5, 30.0],
                    "description": "Seconds between frame extractions when using time_interval mode. Lower = more frames. Recommended: 3-5 seconds for most videos."
                },
                "scene_change_threshold": {
                    "file": "video_extractor",
                    "path": ["scene_change_threshold"],
                    "type": "float",
                    "range": [10.0, 50.0],
                    "description": "Sensitivity for scene change detection (higher = less sensitive). Recommended: 30 for most videos."
                },
                "image_quality": {
                    "file": "video_extractor",
                    "path": ["image_quality"],
                    "type": "int",
                    "range": [50, 100],
                    "description": "JPEG quality for extracted frames (1-100). Higher = better quality but larger files. Recommended: 85-95."
                },
                "preserve_directory_structure": {
                    "file": "video_extractor",
                    "path": ["preserve_directory_structure"],
                    "type": "bool",
                    "description": "Preserve the directory structure when extracting frames. If true, maintains folder hierarchy from source videos."
                }
            },
            "Processing Options": {
                "max_image_size": {
                    "file": "image_describer",
                    "path": ["processing_options", "default_max_image_size"],
                    "type": "int",
                    "range": [512, 2048],
                    "description": "Maximum image dimension (width or height) in pixels. Larger images use more memory. Recommended: 1024."
                },
                "batch_delay": {
                    "file": "image_describer",
                    "path": ["processing_options", "default_batch_delay"],
                    "type": "float",
                    "range": [0.0, 10.0],
                    "description": "Delay in seconds between processing images. Helps prevent memory buildup. Recommended: 1-3 seconds."
                },
                "compression_enabled": {
                    "file": "image_describer",
                    "path": ["processing_options", "default_compression"],
                    "type": "bool",
                    "description": "Compress images before processing to reduce memory usage. Recommended: enabled for large images."
                },
                "extract_metadata": {
                    "file": "image_describer",
                    "path": ["processing_options", "extract_metadata"],
                    "type": "bool",
                    "description": "Extract EXIF metadata from images and include in output. Provides camera settings, GPS, timestamps, etc."
                },
                "chronological_sorting": {
                    "file": "image_describer",
                    "path": ["processing_options", "chronological_sorting", "enabled_by_default"],
                    "type": "bool",
                    "description": "Automatically sort images by file modification time before processing. Ensures chronological order for photo collections."
                }
            },
            "Metadata Settings": {
                "metadata_enabled": {
                    "file": "image_describer",
                    "path": ["metadata", "enabled"],
                    "type": "bool",
                    "description": "Enable metadata extraction from images (GPS coordinates, dates, camera info). Adds location/date prefix to descriptions."
                },
                "include_location_prefix": {
                    "file": "image_describer",
                    "path": ["metadata", "include_location_prefix"],
                    "type": "bool",
                    "description": "Include location and date as prefix in descriptions (e.g., 'Austin, TX Mar 25, 2025: ...'). Requires metadata_enabled."
                },
                "geocoding_enabled": {
                    "file": "image_describer",
                    "path": ["metadata", "geocoding", "enabled"],
                    "type": "bool",
                    "description": "Enable reverse geocoding to convert GPS coordinates to city/state/country. Requires internet access and adds API delay. Results are cached."
                },
                "geocoding_user_agent": {
                    "file": "image_describer",
                    "path": ["metadata", "geocoding", "user_agent"],
                    "type": "string",
                    "description": "User agent string for geocoding API requests. Must follow OpenStreetMap Nominatim usage policy."
                },
                "geocoding_delay": {
                    "file": "image_describer",
                    "path": ["metadata", "geocoding", "delay_seconds"],
                    "type": "float",
                    "range": [0.5, 5.0],
                    "description": "Delay in seconds between geocoding API requests. Minimum 1.0 second required by Nominatim usage policy."
                },
                "geocoding_cache_file": {
                    "file": "image_describer",
                    "path": ["metadata", "geocoding", "cache_file"],
                    "type": "string",
                    "description": "Path to geocoding cache file. Stores geocoded locations to minimize API calls."
                }
            },
            "Workflow Settings": {
                "base_output_directory": {
                    "file": "workflow",
                    "path": ["workflow", "base_output_dir"],
                    "type": "string",
                    "description": "Base directory for workflow output. Relative paths are relative to current directory."
                },
                "preserve_structure": {
                    "file": "workflow",
                    "path": ["workflow", "preserve_structure"],
                    "type": "bool",
                    "description": "Preserve input directory structure in output. Maintains folder organization from source."
                },
                "cleanup_intermediate": {
                    "file": "workflow",
                    "path": ["workflow", "cleanup_intermediate"],
                    "type": "bool",
                    "description": "Delete intermediate files after workflow completes. Saves disk space but removes debugging information."
                },
                "enable_video_extraction": {
                    "file": "workflow",
                    "path": ["workflow", "steps", "video_extraction", "enabled"],
                    "type": "bool",
                    "description": "Enable video frame extraction step in workflow."
                },
                "enable_image_conversion": {
                    "file": "workflow",
                    "path": ["workflow", "steps", "image_conversion", "enabled"],
                    "type": "bool",
                    "description": "Enable HEIC/HEIF to JPEG conversion step in workflow."
                },
                "enable_image_description": {
                    "file": "workflow",
                    "path": ["workflow", "steps", "image_description", "enabled"],
                    "type": "bool",
                    "description": "Enable AI image description step in workflow."
                },
                "enable_html_generation": {
                    "file": "workflow",
                    "path": ["workflow", "steps", "html_generation", "enabled"],
                    "type": "bool",
                    "description": "Enable HTML report generation step in workflow."
                },
                "conversion_quality": {
                    "file": "workflow",
                    "path": ["workflow", "steps", "image_conversion", "quality"],
                    "type": "int",
                    "range": [50, 100],
                    "description": "JPEG quality for HEIC/HEIF conversion (1-100). Higher = better quality but larger files."
                },
                "html_report_title": {
                    "file": "workflow",
                    "path": ["workflow", "steps", "html_generation", "title"],
                    "type": "string",
                    "description": "Title for generated HTML reports."
                }
            },
            "Output Format": {
                "include_timestamp": {
                    "file": "image_describer",
                    "path": ["output_format", "include_timestamp"],
                    "type": "bool",
                    "description": "Include processing timestamp in output files."
                },
                "include_model_info": {
                    "file": "image_describer",
                    "path": ["output_format", "include_model_info"],
                    "type": "bool",
                    "description": "Include AI model name and settings in output files."
                },
                "include_file_path": {
                    "file": "image_describer",
                    "path": ["output_format", "include_file_path"],
                    "type": "bool",
                    "description": "Include full file path in descriptions output."
                },
                "include_metadata": {
                    "file": "image_describer",
                    "path": ["output_format", "include_metadata"],
                    "type": "bool",
                    "description": "Include extracted EXIF metadata in descriptions output."
                }
            }
        }
    
    def init_ui(self):
        """Create the main user interface with tabbed categories"""
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Header label
        header = wx.StaticText(panel, label="IDT Configuration Manager")
        font = wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        header.SetFont(font)
        main_sizer.Add(header, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        
        # Create notebook with tabs for each category
        self.notebook = wx.Notebook(panel, name="Configuration categories")
        
        # Create a tab for each category
        for category in self.settings_metadata.keys():
            tab_panel = self.create_category_tab(self.notebook, category)
            self.notebook.AddPage(tab_panel, category)
        
        main_sizer.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 5)
        
        # Dialog buttons
        btn_sizer = self.create_dialog_buttons(panel)
        main_sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        panel.SetSizer(main_sizer)
    
    def create_category_tab(self, parent, category: str) -> wx.Panel:
        """Create a tab panel for a specific category"""
        panel = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # Left side: Settings list
        left_box = wx.StaticBox(panel, label="Settings:")
        left_sizer = wx.StaticBoxSizer(left_box, wx.VERTICAL)
        
        settings_list = wx.ListBox(left_box, style=wx.LB_SINGLE | wx.LB_NEEDED_SB, name=f"{category} settings")
        settings_list.Bind(wx.EVT_LISTBOX, lambda e: self.on_setting_selected(category, e))
        left_sizer.Add(settings_list, 1, wx.EXPAND | wx.ALL, 5)
        
        # Change button
        change_button = wx.Button(left_box, label="Change Setting")
        change_button.Enable(False)
        change_button.Bind(wx.EVT_BUTTON, lambda e: self.change_setting(category, e))
        left_sizer.Add(change_button, 0, wx.EXPAND | wx.ALL, 5)
        
        sizer.Add(left_sizer, 1, wx.EXPAND | wx.ALL, 5)
        
        # Right side: Explanation panel
        right_box = wx.StaticBox(panel, label="Explanation:")
        right_sizer = wx.StaticBoxSizer(right_box, wx.VERTICAL)
        
        explanation_text = wx.TextCtrl(right_box, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP, name=f"{category} explanation")
        right_sizer.Add(explanation_text, 1, wx.EXPAND | wx.ALL, 5)
        
        sizer.Add(right_sizer, 1, wx.EXPAND | wx.ALL, 5)
        
        panel.SetSizer(sizer)
        
        # Store references to widgets for later access
        self.category_widgets[category] = {
            'panel': panel,
            'settings_list': settings_list,
            'change_button': change_button,
            'explanation_text': explanation_text
        }
        
        # Populate the settings list
        self.load_category_settings(category)
        
        return panel
    
    def create_dialog_buttons(self, parent):
        """Create OK, Cancel, Apply buttons for the dialog"""
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        btn_sizer.AddStretchSpacer()
        
        # OK, Cancel, Apply buttons
        self.ok_btn = wx.Button(parent, wx.ID_OK, label="OK")
        self.ok_btn.Bind(wx.EVT_BUTTON, self.on_ok)
        btn_sizer.Add(self.ok_btn, 0, wx.ALL, 5)
        
        self.cancel_btn = wx.Button(parent, wx.ID_CANCEL, label="Cancel")
        self.cancel_btn.Bind(wx.EVT_BUTTON, self.on_cancel)
        btn_sizer.Add(self.cancel_btn, 0, wx.ALL, 5)
        
        self.apply_btn = wx.Button(parent, wx.ID_APPLY, label="Apply")
        self.apply_btn.Bind(wx.EVT_BUTTON, self.on_apply)
        btn_sizer.Add(self.apply_btn, 0, wx.ALL, 5)
        
        return btn_sizer
    
    def load_all_configs(self):
        """Load all configuration files"""
        for name, path in self.config_files.items():
            try:
                if path.exists():
                    with open(path, 'r', encoding='utf-8') as f:
                        self.configs[name] = json.load(f)
                else:
                    self.configs[name] = {}
                    print(f"Warning: {path} not found")
            except Exception as e:
                self.configs[name] = {}
                show_warning(self, f"Error loading {path}:\n{str(e)}")
    
    def load_category_settings(self, category: str):
        """Load settings for a specific category into its tab"""
        widgets = self.category_widgets.get(category)
        if not widgets:
            return
        
        settings_list = widgets['settings_list']
        explanation_text = widgets['explanation_text']
        
        # Clear current list
        settings_list.Clear()
        explanation_text.Clear()
        
        # Load settings for this category
        settings = self.settings_metadata.get(category, {})
        
        for setting_name, setting_info in settings.items():
            # Get current value
            current_value = self.get_setting_value(setting_info)
            
            # Format display text: "Setting Name: current_value"
            display_text = f"{setting_name}: {current_value}"
            
            settings_list.Append(display_text, setting_name)
        
        # Select first item if available
        if settings_list.GetCount() > 0:
            settings_list.SetSelection(0)
            self.on_setting_selected(category, None)
    
    def on_setting_selected(self, category: str, event):
        """Handle setting selection in a category tab"""
        widgets = self.category_widgets.get(category)
        if not widgets:
            return
        
        settings_list = widgets['settings_list']
        change_button = widgets['change_button']
        explanation_text = widgets['explanation_text']
        
        selection = settings_list.GetSelection()
        if selection == wx.NOT_FOUND:
            change_button.Enable(False)
            explanation_text.Clear()
            return
        
        setting_name = settings_list.GetClientData(selection)
        setting_info = self.settings_metadata[category][setting_name]
        
        # Show explanation with range/choices info
        description = setting_info.get("description", "No description available")
        
        # Add range info if available
        if "range" in setting_info:
            description += f"\n\nRange: {setting_info['range'][0]} to {setting_info['range'][1]}"
        
        # Add choices if available
        if "choices" in setting_info:
            description += f"\n\nOptions: {', '.join(setting_info['choices'])}"
        
        explanation_text.SetValue(description)
        
        change_button.Enable(True)
    
    def get_setting_value(self, setting_info: Dict[str, Any]) -> Any:
        """Get current value for a setting"""
        config_name = setting_info["file"]
        path = setting_info["path"]
        
        config = self.configs.get(config_name, {})
        
        # Navigate through nested path
        value = config
        for key in path:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        
        return value
    
    def set_setting_value(self, setting_info: Dict[str, Any], new_value: Any):
        """Set a new value for a setting"""
        config_name = setting_info["file"]
        path = setting_info["path"]
        
        config = self.configs.get(config_name, {})
        
        # Navigate to the parent of the target key
        current = config
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        # Set the value
        current[path[-1]] = new_value
    
    def change_setting(self, category: str, event):
        """Open dialog to change the selected setting in a category"""
        widgets = self.category_widgets.get(category)
        if not widgets:
            return
        
        settings_list = widgets['settings_list']
        
        selection = settings_list.GetSelection()
        if selection == wx.NOT_FOUND:
            return
        
        setting_name = settings_list.GetClientData(selection)
        setting_info = self.settings_metadata[category][setting_name]
        
        current_value = self.get_setting_value(setting_info)
        
        # Open edit dialog
        dialog = SettingEditDialog(self, setting_name, current_value, setting_info)
        if dialog.ShowModal() == wx.ID_OK:
            # Update the value
            new_value = dialog.GetValue()
            self.set_setting_value(setting_info, new_value)
            
            # Update the list item text to show new value
            display_text = f"{setting_name}: {new_value}"
            settings_list.SetString(selection, display_text)
            
            # Refresh the display
            self.on_setting_selected(category, None)
        
        dialog.Destroy()
    
    def save_all_configs(self):
        """Save all configuration files"""
        try:
            for name, config in self.configs.items():
                path = self.config_files[name]
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2)
            
            return True
        except Exception as e:
            show_error(self, f"Error saving configurations:\n{str(e)}")
            return False
    
    def on_ok(self, event):
        """Handle OK button - save and close"""
        if self.save_all_configs():
            self.EndModal(wx.ID_OK)
    
    def on_cancel(self, event):
        """Handle Cancel button - discard changes and close"""
        # Could add confirmation dialog here if tracking modifications
        self.EndModal(wx.ID_CANCEL)
    
    def on_apply(self, event):
        """Handle Apply button - save but keep dialog open"""
        if self.save_all_configs():
            show_info(self, "All configurations saved successfully!")
    
    def on_dialog_close(self, event):
        """Handle dialog close event"""
        # Could add unsaved changes check here
        if event.CanVeto():
            self.EndModal(wx.ID_CANCEL)
        else:
            self.Destroy()
