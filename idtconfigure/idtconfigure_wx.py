#!/usr/bin/env python3
"""
IDT Configure (wxPython) - Configuration Manager for Image Description Toolkit

wxPython port of the Qt6 IDT Configure with improved macOS VoiceOver accessibility.
Manages configuration files:
- image_describer_config.json
- video_frame_extractor_config.json
- workflow_config.json

Features:
- Menu-based categorization for accessibility
- Settings list with arrow navigation
- Type-specific editors (bool, int, float, choice, string)
- Screen reader readable explanations
- Save/Load functionality
- Export/Import configurations
- Professional, accessible interface
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


class IDTConfigureFrame(wx.Frame):
    """Main application window for IDT Configuration Manager"""
    
    def __init__(self):
        super().__init__(None, title="IDT Configure - Configuration Manager", size=(900, 600))
        
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
        
        # Current category being viewed
        self.current_category = None
        
        # Settings metadata for each category
        self.settings_metadata = self.build_settings_metadata()
        
        # Load all configs
        self.load_all_configs()
        
        # UI setup
        self.init_ui()
        self.create_menu_bar()
        self.create_status_bar()
        
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
        """Create the main user interface"""
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Header label
        header = wx.StaticText(panel, label="IDT Configuration Manager")
        font = wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        header.SetFont(font)
        main_sizer.Add(header, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        
        # Category label
        self.category_label = wx.StaticText(panel, label="Select a category from the Settings menu")
        cat_font = wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.category_label.SetFont(cat_font)
        main_sizer.Add(self.category_label, 0, wx.ALL, 5)
        
        # Content layout (settings list + explanation)
        content_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # Left side: Settings list
        left_box = wx.StaticBox(panel, label="Settings:")
        left_sizer = wx.StaticBoxSizer(left_box, wx.VERTICAL)
        
        self.settings_list = wx.ListBox(left_box, style=wx.LB_SINGLE | wx.LB_NEEDED_SB)
        self.settings_list.Bind(wx.EVT_LISTBOX, self.on_setting_selected)
        left_sizer.Add(self.settings_list, 1, wx.EXPAND | wx.ALL, 5)
        
        # Change button
        self.change_button = wx.Button(left_box, label="Change Setting")
        self.change_button.Enable(False)
        self.change_button.Bind(wx.EVT_BUTTON, self.change_setting)
        left_sizer.Add(self.change_button, 0, wx.EXPAND | wx.ALL, 5)
        
        content_sizer.Add(left_sizer, 1, wx.EXPAND | wx.ALL, 5)
        
        # Right side: Explanation panel
        right_box = wx.StaticBox(panel, label="Explanation:")
        right_sizer = wx.StaticBoxSizer(right_box, wx.VERTICAL)
        
        self.explanation_text = wx.TextCtrl(right_box, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP)
        right_sizer.Add(self.explanation_text, 1, wx.EXPAND | wx.ALL, 5)
        
        content_sizer.Add(right_sizer, 1, wx.EXPAND | wx.ALL, 5)
        
        main_sizer.Add(content_sizer, 1, wx.EXPAND | wx.ALL, 5)
        
        panel.SetSizer(main_sizer)
    
    def create_menu_bar(self):
        """Create the menu bar"""
        menubar = wx.MenuBar()
        
        # File menu
        file_menu = wx.Menu()
        
        reload_item = file_menu.Append(wx.ID_REFRESH, "Reload Configurations\tCtrl+R")
        self.Bind(wx.EVT_MENU, self.reload_configs, reload_item)
        
        save_item = file_menu.Append(wx.ID_SAVE, "Save All\tCtrl+S")
        self.Bind(wx.EVT_MENU, self.save_all_configs, save_item)
        
        file_menu.AppendSeparator()
        
        export_item = file_menu.Append(wx.ID_ANY, "Export Configuration...")
        self.Bind(wx.EVT_MENU, self.export_config, export_item)
        
        import_item = file_menu.Append(wx.ID_ANY, "Import Configuration...")
        self.Bind(wx.EVT_MENU, self.import_config, import_item)
        
        file_menu.AppendSeparator()
        
        exit_item = file_menu.Append(wx.ID_EXIT, "Exit\tCtrl+Q")
        self.Bind(wx.EVT_MENU, lambda e: self.Close(), exit_item)
        
        menubar.Append(file_menu, "&File")
        
        # Settings menu (categories)
        settings_menu = wx.Menu()
        
        for category in self.settings_metadata.keys():
            item = settings_menu.Append(wx.ID_ANY, category)
            self.Bind(wx.EVT_MENU, lambda e, cat=category: self.load_category(cat), item)
        
        menubar.Append(settings_menu, "&Settings")
        
        # Help menu
        help_menu = wx.Menu()
        
        about_item = help_menu.Append(wx.ID_ABOUT, "About")
        self.Bind(wx.EVT_MENU, self.show_about, about_item)
        
        help_item = help_menu.Append(wx.ID_HELP, "Help\tF1")
        self.Bind(wx.EVT_MENU, self.show_help, help_item)
        
        menubar.Append(help_menu, "&Help")
        
        self.SetMenuBar(menubar)
    
    def create_status_bar(self):
        """Create the status bar"""
        self.CreateStatusBar()
        self.SetStatusText("Ready")
    
    def load_all_configs(self):
        """Load all configuration files"""
        for name, path in self.config_files.items():
            try:
                if path.exists():
                    with open(path, 'r', encoding='utf-8') as f:
                        self.configs[name] = json.load(f)
                else:
                    self.configs[name] = {}
                    self.SetStatusText(f"Warning: {path} not found")
            except Exception as e:
                self.configs[name] = {}
                show_warning(self, f"Error loading {path}:\n{str(e)}")
    
    def reload_configs(self, event):
        """Reload all configurations from disk"""
        self.load_all_configs()
        if self.current_category:
            self.load_category(self.current_category)
        self.SetStatusText("Configurations reloaded")
    
    def save_all_configs(self, event):
        """Save all configuration files"""
        try:
            for name, config in self.configs.items():
                path = self.config_files[name]
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2)
            
            self.SetStatusText("All configurations saved successfully")
            show_info(self, "All configurations saved successfully!")
        except Exception as e:
            show_error(self, f"Error saving configurations:\\n{str(e)}")
    
    def load_category(self, category: str):
        """Load settings for a specific category"""
        self.current_category = category
        self.category_label.SetLabel(f"Category: {category}")
        
        # Clear current list
        self.settings_list.Clear()
        self.explanation_text.Clear()
        
        # Load settings for this category
        settings = self.settings_metadata.get(category, {})
        
        for setting_name, setting_info in settings.items():
            # Get current value
            current_value = self.get_setting_value(setting_info)
            
            # Format display text: "Setting Name: current_value"
            display_text = f"{setting_name}: {current_value}"
            
            self.settings_list.Append(display_text, setting_name)
        
        # Select first item if available
        if self.settings_list.GetCount() > 0:
            self.settings_list.SetSelection(0)
            self.on_setting_selected(None)
        
        self.SetStatusText(f"Loaded {category}")
    
    def on_setting_selected(self, event):
        """Handle setting selection"""
        selection = self.settings_list.GetSelection()
        if selection == wx.NOT_FOUND:
            self.change_button.Enable(False)
            self.explanation_text.Clear()
            return
        
        setting_name = self.settings_list.GetClientData(selection)
        setting_info = self.settings_metadata[self.current_category][setting_name]
        
        # Show explanation with range/choices info
        description = setting_info.get("description", "No description available")
        
        # Add range info if available
        if "range" in setting_info:
            description += f"\n\nRange: {setting_info['range'][0]} to {setting_info['range'][1]}"
        
        # Add choices if available
        if "choices" in setting_info:
            description += f"\n\nOptions: {', '.join(setting_info['choices'])}"
        
        self.explanation_text.SetValue(description)
        
        self.change_button.Enable(True)
    
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
    
    def change_setting(self, event):
        """Open dialog to change the selected setting"""
        selection = self.settings_list.GetSelection()
        if selection == wx.NOT_FOUND:
            return
        
        setting_name = self.settings_list.GetClientData(selection)
        setting_info = self.settings_metadata[self.current_category][setting_name]
        
        current_value = self.get_setting_value(setting_info)
        
        # Open edit dialog
        dialog = SettingEditDialog(self, setting_name, current_value, setting_info)
        if dialog.ShowModal() == wx.ID_OK:
            # Update the value
            new_value = dialog.GetValue()
            self.set_setting_value(setting_info, new_value)
            
            # Update the list item text to show new value
            display_text = f"{setting_name}: {new_value}"
            self.settings_list.SetString(selection, display_text)
            
            # Refresh the display
            self.on_setting_selected(None)
            
            self.SetStatusText(f"Changed {setting_name} to {new_value}")
        
        dialog.Destroy()
    
    def export_config(self, event):
        """Export current configuration to a file"""
        export_path = save_file_dialog(
            self,
            "Export Configuration",
            wildcard="JSON Files (*.json)|*.json",
            default_dir="",
            default_file="idt_config_export.json"
        )
        
        if export_path:
            try:
                with open(export_path, 'w', encoding='utf-8') as f:
                    json.dump(self.configs, f, indent=2)
                show_info(self, f"Configuration exported to:\\n{export_path}")
            except Exception as e:
                show_error(self, str(e))
    
    def import_config(self, event):
        """Import configuration from a file"""
        import_path = open_file_dialog(
            self,
            "Import Configuration",
            wildcard="JSON Files (*.json)|*.json",
            default_dir=""
        )
        
        if import_path:
            try:
                with open(import_path, 'r', encoding='utf-8') as f:
                    imported = json.load(f)
                
                # Merge or replace?
                msg = wx.MessageDialog(self, 
                                      "Replace current configuration completely?\n\n"
                                      "Yes = Replace all\nNo = Merge with current",
                                      "Import Mode",
                                      wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION)
                reply = msg.ShowModal()
                msg.Destroy()
                
                if reply == wx.ID_YES:
                    self.configs = imported
                elif reply == wx.ID_NO:
                    # Merge
                    for key, value in imported.items():
                        if key in self.configs:
                            self.configs[key].update(value)
                        else:
                            self.configs[key] = value
                
                # Reload display
                if self.current_category:
                    self.load_category(self.current_category)
                
                show_info(self, "Configuration imported successfully!")
            except Exception as e:
                show_error(self, str(e))
    
    def show_about(self, event):
        """Show about dialog"""
        show_about_dialog(
            self,
            "IDT Configure",
            get_app_version(),
            "Configuration Manager for Image Description Toolkit\n\n"
            "Features:\n"
            "• Manage AI model settings\n"
            "• Configure video extraction options\n"
            "• Adjust workflow behavior\n"
            "• Set processing preferences\n"
            "• Full keyboard accessibility"
        )
    
    def show_help(self, event):
        """Show help dialog"""
        help_text = """IDT Configure Help

Getting Started:
1. Select a category from the Settings menu
2. Navigate through settings using arrow keys
3. Press "Change Setting" or Enter to edit
4. Use File → Save All to save changes

Categories:
• AI Model Settings: Temperature, tokens, and other AI parameters
• Prompt Styles: Choose default description style
• Video Extraction: Configure frame extraction from videos
• Processing Options: Memory, delays, and optimization
• Workflow Settings: Enable/disable workflow steps
• Output Format: Control what's included in output

Tips:
• Hover over settings for more information
• Changes are not saved until you use File → Save All
• You can reload from disk with Ctrl+R
• Export/Import to backup or share configurations

Accessibility:
This application is fully keyboard accessible:
• Use Tab to move between controls
• Arrow keys to navigate lists
• Enter to activate buttons
• Alt+letter to access menus"""
        
        show_info(self, help_text, "Help")


def main():
    """Main entry point"""
    app = wx.App()
    app.SetAppName("IDT Configure")
    
    frame = IDTConfigureFrame()
    frame.Show()
    
    app.MainLoop()


if __name__ == "__main__":
    main()
