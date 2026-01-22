"""
wxPython Dialog classes for Image Describer

This module contains all dialog windows used in the Image Describer wxPython application.
All dialogs use shared utilities and follow accessibility best practices.
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Optional, Any

import wx

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

# Import shared utilities
from shared.wx_common import (
    show_error,
    show_warning,
    show_info,
    ask_yes_no,
    select_directory_dialog,
    open_file_dialog,
    save_file_dialog,
)

# Import config loader for prompt loading
try:
    from scripts.config_loader import load_json_config
except ImportError:
    try:
        from config_loader import load_json_config
    except ImportError:
        load_json_config = None

# Import data models (framework-independent) from same directory
try:
    from .data_models import ImageDescription, ImageItem, ImageWorkspace
except ImportError:
    # Fallback for direct execution
    from data_models import ImageDescription, ImageItem, ImageWorkspace


def set_accessible_name(widget, name):
    """Safely set accessible name if supported"""
    if hasattr(widget, 'SetAccessibleName'):
        try:
            widget.SetAccessibleName(name)
        except Exception:
            pass  # Silently ignore if not supported


def set_accessible_description(widget, desc):
    """Safely set accessible description if supported"""
    if hasattr(widget, 'SetAccessibleDescription'):
        try:
            widget.SetAccessibleDescription(desc)
        except Exception:
            pass  # Silently ignore if not supported


class DirectorySelectionDialog(wx.Dialog):
    """Dialog for selecting directory with options for recursive search and multiple directories"""
    
    def __init__(self, existing_directories: List[str], parent=None):
        super().__init__(
            parent,
            title="Select Image Directory",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        
        self.selected_directory = ""
        self.recursive_search = False
        self.add_to_existing = False
        
        self.init_ui(existing_directories)
        self.SetSize((600, 500))
        self.Centre()
        
        # Set initial focus to browse button for accessibility
        wx.CallAfter(self.browse_btn.SetFocus)
    
    def init_ui(self, existing_directories: List[str]):
        """Initialize the dialog UI"""
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Directory selection group
        dir_box = wx.StaticBox(self, label="Directory Selection")
        dir_sizer = wx.StaticBoxSizer(dir_box, wx.VERTICAL)
        
        self.dir_label = wx.StaticText(self, label="No directory selected")
        set_accessible_name(self.dir_label, "Selected directory")
        dir_sizer.Add(self.dir_label, 0, wx.ALL | wx.EXPAND, 5)
        
        self.browse_btn = wx.Button(self, label="&Browse for Directory...")
        set_accessible_name(self.browse_btn, "Browse for directory")
        set_accessible_description(self.browse_btn, "Open directory chooser to select an image directory")
        self.browse_btn.Bind(wx.EVT_BUTTON, self.on_browse)
        dir_sizer.Add(self.browse_btn, 0, wx.ALL | wx.EXPAND, 5)
        
        main_sizer.Add(dir_sizer, 0, wx.ALL | wx.EXPAND, 10)
        
        # Options group
        options_box = wx.StaticBox(self, label="Options")
        options_sizer = wx.StaticBoxSizer(options_box, wx.VERTICAL)
        
        self.recursive_cb = wx.CheckBox(self, label="&Search subdirectories recursively")
        self.recursive_cb.SetToolTip("When checked, searches all subdirectories for images")
        set_accessible_name(self.recursive_cb, "Search subdirectories recursively")
        options_sizer.Add(self.recursive_cb, 0, wx.ALL, 5)
        
        self.add_to_existing_cb = wx.CheckBox(self, label="&Add to existing workspace")
        set_accessible_name(self.add_to_existing_cb, "Add to existing workspace")
        if existing_directories:
            tip = "Add to existing directories:\n" + "\n".join([Path(d).name for d in existing_directories[:5]])
            self.add_to_existing_cb.SetToolTip(tip)
        else:
            self.add_to_existing_cb.SetToolTip("No existing directories in workspace")
            self.add_to_existing_cb.Enable(False)
        options_sizer.Add(self.add_to_existing_cb, 0, wx.ALL, 5)
        
        main_sizer.Add(options_sizer, 0, wx.ALL | wx.EXPAND, 10)
        
        # Existing directories display
        if existing_directories:
            existing_box = wx.StaticBox(
                self,
                label=f"Current Workspace Directories ({len(existing_directories)})"
            )
            existing_sizer = wx.StaticBoxSizer(existing_box, wx.VERTICAL)
            
            # Use scrolled window for many directories
            scroll = wx.ScrolledWindow(self, size=(-1, 150))
            scroll.SetScrollRate(5, 5)
            scroll_sizer = wx.BoxSizer(wx.VERTICAL)
            
            for directory in existing_directories[:10]:  # Show up to 10
                dir_label = wx.StaticText(scroll, label=str(Path(directory).name))
                dir_label.SetToolTip(str(directory))
                scroll_sizer.Add(dir_label, 0, wx.ALL, 2)
            
            if len(existing_directories) > 10:
                more_label = wx.StaticText(
                    scroll,
                    label=f"... and {len(existing_directories) - 10} more"
                )
                scroll_sizer.Add(more_label, 0, wx.ALL, 2)
            
            scroll.SetSizer(scroll_sizer)
            existing_sizer.Add(scroll, 1, wx.EXPAND | wx.ALL, 5)
            main_sizer.Add(existing_sizer, 1, wx.ALL | wx.EXPAND, 10)
        
        # Dialog buttons
        btn_sizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        main_sizer.Add(btn_sizer, 0, wx.ALL | wx.EXPAND, 10)
        
        self.SetSizer(main_sizer)
        
        # Update button state (disable OK until directory selected)
        self.update_ok_button()
        
        # Enable tab traversal for all controls
        self.browse_btn.SetCanFocus(True)
        self.recursive_cb.SetCanFocus(True)
        self.add_to_existing_cb.SetCanFocus(True)
    
    def on_browse(self, event):
        """Browse for directory"""
        dir_path = select_directory_dialog(self, "Select Image Directory")
        if dir_path:
            self.selected_directory = dir_path
            self.dir_label.SetLabel(str(Path(dir_path).name))
            self.dir_label.SetToolTip(dir_path)
            self.update_ok_button()
    
    def update_ok_button(self):
        """Enable/disable OK button based on selection"""
        ok_btn = self.FindWindowById(wx.ID_OK)
        if ok_btn:
            ok_btn.Enable(bool(self.selected_directory))
    
    def get_selection(self):
        """Get the user's selections"""
        return {
            'directory': self.selected_directory,
            'recursive': self.recursive_cb.GetValue(),
            'add_to_existing': self.add_to_existing_cb.GetValue()
        }


class ApiKeyDialog(wx.Dialog):
    """Dialog for entering API key file path"""
    
    def __init__(self, provider_name: str, parent=None):
        super().__init__(
            parent,
            title=f"{provider_name} API Key",
            style=wx.DEFAULT_DIALOG_STYLE
        )
        
        self.api_key_file = ""
        self.init_ui(provider_name)
        self.SetSize((500, 200))
        self.Centre()
    
    def init_ui(self, provider_name: str):
        """Initialize the dialog UI"""
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Instructions
        info_text = wx.StaticText(
            self,
            label=f"{provider_name} requires an API key.\n"
                  f"Please select your API key file (or enter the API key directly):"
        )
        main_sizer.Add(info_text, 0, wx.ALL, 10)
        
        # File selection
        file_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.file_text = wx.TextCtrl(self)
        self.file_text.SetHint("Path to API key file or API key")
        file_sizer.Add(self.file_text, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        
        browse_btn = wx.Button(self, label="Browse...")
        browse_btn.Bind(wx.EVT_BUTTON, self.on_browse)
        file_sizer.Add(browse_btn, 0, wx.ALIGN_CENTER_VERTICAL)
        
        main_sizer.Add(file_sizer, 0, wx.ALL | wx.EXPAND, 10)
        
        # Dialog buttons
        btn_sizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        main_sizer.Add(btn_sizer, 0, wx.ALL | wx.EXPAND, 10)
        
        self.SetSizer(main_sizer)
    
    def on_browse(self, event):
        """Browse for API key file"""
        file_path = open_file_dialog(
            self,
            "Select API Key File",
            None,
            "Text files (*.txt)|*.txt|All files (*.*)|*.*"
        )
        if file_path:
            self.file_text.SetValue(file_path)
    
    def get_api_key_file(self):
        """Get the API key file path or key"""
        return self.file_text.GetValue().strip()


class ProcessingOptionsDialog(wx.Dialog):
    """Dialog for configuring processing options"""
    
    def __init__(self, current_config: Dict[str, Any], parent=None):
        super().__init__(
            parent,
            title="Processing Options",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        
        self.config = current_config.copy()
        self.init_ui()
        self.SetSize((600, 400))
        self.Centre()
    
    def init_ui(self):
        """Initialize the dialog UI"""
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Create notebook for tabs with keyboard navigation support
        self.notebook = wx.Notebook(self, style=wx.NB_TOP)
        set_accessible_name(self.notebook, "Processing options tabs")
        set_accessible_description(self.notebook, "Use left and right arrow keys to navigate between tabs")
        
        # General tab
        general_panel = self.create_general_panel(self.notebook)
        self.notebook.AddPage(general_panel, "&General")
        
        # AI Model tab
        ai_panel = self.create_ai_panel(self.notebook)
        self.notebook.AddPage(ai_panel, "&AI Model")
        
        main_sizer.Add(self.notebook, 1, wx.ALL | wx.EXPAND, 10)
        
        # Dialog buttons
        btn_sizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        main_sizer.Add(btn_sizer, 0, wx.ALL | wx.EXPAND, 10)
        
        self.SetSizer(main_sizer)
        
        # Set focus to AI provider control (the key area for user interaction)
        # Use CallAfter to ensure UI is fully initialized
        # CRITICAL: Must happen AFTER populate_models_for_provider to avoid race condition
        wx.CallAfter(self._set_initial_focus)
    
    def _set_initial_focus(self):
        """Set initial focus to AI provider choice on AI Model tab"""
        # Switch to AI Model tab (index 1)
        self.notebook.SetSelection(1)
        # CRITICAL: Don't set focus immediately after tab switch on macOS
        # The accessibility system needs time to process the tab change
        # Use CallAfter to defer focus setting to next event cycle
        wx.CallAfter(self.provider_choice.SetFocus)
    
    def create_general_panel(self, parent):
        """Create general options panel"""
        panel = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Batch processing
        batch_box = wx.StaticBox(panel, label="Batch Processing")
        batch_sizer = wx.StaticBoxSizer(batch_box, wx.VERTICAL)
        
        self.skip_existing_cb = wx.CheckBox(
            panel,
            label="&Skip images that already have descriptions"
        )
        self.skip_existing_cb.SetValue(self.config.get('skip_existing', False))
        set_accessible_name(self.skip_existing_cb, "Skip images that already have descriptions")
        batch_sizer.Add(self.skip_existing_cb, 0, wx.ALL, 5)
        
        sizer.Add(batch_sizer, 0, wx.ALL | wx.EXPAND, 10)
        
        panel.SetSizer(sizer)
        return panel
    
    def create_ai_panel(self, parent):
        """Create AI model options panel"""
        panel = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Provider selection
        provider_box = wx.StaticBox(panel, label="AI Provider")
        provider_sizer = wx.StaticBoxSizer(provider_box, wx.VERTICAL)
        
        provider_label = wx.StaticText(panel, label="&Provider:")
        provider_sizer.Add(provider_label, 0, wx.ALL, 5)
        
        self.provider_choice = wx.Choice(panel, choices=["Ollama", "OpenAI", "Claude"])
        self.provider_choice.SetSelection(0)
        self.provider_choice.Bind(wx.EVT_CHOICE, self.on_provider_changed)
        set_accessible_name(self.provider_choice, "AI provider")
        provider_sizer.Add(self.provider_choice, 0, wx.ALL | wx.EXPAND, 5)
        
        sizer.Add(provider_sizer, 0, wx.ALL | wx.EXPAND, 10)
        
        # Model selection
        model_box = wx.StaticBox(panel, label="Model")
        model_sizer = wx.StaticBoxSizer(model_box, wx.VERTICAL)
        
        model_label = wx.StaticText(panel, label="&Model name:")
        model_sizer.Add(model_label, 0, wx.ALL, 5)
        
        self.model_combo = wx.ComboBox(panel, style=wx.CB_DROPDOWN)
        self.model_combo.SetValue(self.config.get('model', 'moondream'))
        set_accessible_name(self.model_combo, "Model name")
        model_sizer.Add(self.model_combo, 0, wx.ALL | wx.EXPAND, 5)
        
        sizer.Add(model_sizer, 0, wx.ALL | wx.EXPAND, 10)
        
        # Prompt style
        prompt_box = wx.StaticBox(panel, label="Prompt Style")
        prompt_sizer = wx.StaticBoxSizer(prompt_box, wx.VERTICAL)
        
        prompt_label = wx.StaticText(panel, label="P&rompt style:")
        prompt_sizer.Add(prompt_label, 0, wx.ALL, 5)
        
        self.prompt_choice = wx.Choice(panel, choices=[])
        set_accessible_name(self.prompt_choice, "Prompt style")
        prompt_sizer.Add(self.prompt_choice, 0, wx.ALL | wx.EXPAND, 5)
        
        # Load prompts from config file
        wx.CallAfter(self.load_prompts)
        
        sizer.Add(prompt_sizer, 0, wx.ALL | wx.EXPAND, 10)
        
        # Custom prompt override
        custom_prompt_box = wx.StaticBox(panel, label="Custom Prompt (Optional)")
        custom_prompt_sizer = wx.StaticBoxSizer(custom_prompt_box, wx.VERTICAL)
        
        custom_prompt_label = wx.StaticText(
            panel,
            label="&Enter a custom prompt to override the selected style:"
        )
        custom_prompt_sizer.Add(custom_prompt_label, 0, wx.ALL, 5)
        
        self.custom_prompt_input = wx.TextCtrl(
            panel,
            value=self.config.get('custom_prompt', ''),
            style=wx.TE_MULTILINE | wx.TE_WORDWRAP,
            name="Custom prompt override"
        )
        self.custom_prompt_input.SetMinSize((400, 80))
        set_accessible_name(self.custom_prompt_input, "Custom prompt override")
        set_accessible_description(
            self.custom_prompt_input,
            "Leave blank to use the selected prompt style, or enter a custom prompt here"
        )
        custom_prompt_sizer.Add(self.custom_prompt_input, 0, wx.ALL | wx.EXPAND, 5)
        
        # Help text
        help_text = wx.StaticText(
            panel,
            label="Leave blank to use selected style; fill in to override with custom prompt"
        )
        help_text.SetFont(help_text.GetFont().MakeItalic())
        custom_prompt_sizer.Add(help_text, 0, wx.ALL, 5)
        
        sizer.Add(custom_prompt_sizer, 0, wx.ALL | wx.EXPAND, 10)
        
        panel.SetSizer(sizer)
        
        # CRITICAL: Populate models IMMEDIATELY, not deferred
        # CallAfter was causing race condition with focus management
        # Do this synchronously so model list is ready before any focus changes
        self.populate_models_for_provider()
        
        return panel
    
    def on_provider_changed(self, event):
        """Handle provider selection change - populate available models"""
        self.populate_models_for_provider()
    
    def populate_models_for_provider(self):
        """Populate model list based on selected provider"""
        provider = self.provider_choice.GetStringSelection().lower()
        
        # CRITICAL FIX: Save focus state before clearing combo box
        # Clearing a ComboBox while it has focus can crash VoiceOver/accessibility
        # on macOS due to accessibility API trying to query deallocated parent views
        focused_widget = self.FindFocus()
        had_focus = (focused_widget == self.model_combo)
        
        if had_focus:
            # Temporarily move focus to a stable control that won't be modified
            # Use the parent panel to avoid any control that might be in transition
            self.model_combo.GetParent().SetFocus()
        
        # Clear the combo box (safe now that focus is elsewhere)
        self.model_combo.Clear()
        
        try:
            if provider == "ollama":
                # Get installed Ollama models
                from ai_providers import get_available_providers
                providers = get_available_providers()
                if 'ollama' in providers:
                    ollama_provider = providers['ollama']
                    models = ollama_provider.get_available_models()
                    if models:
                        for model in models:
                            self.model_combo.Append(model)
                        # Set default if in list
                        default_model = self.config.get('model', 'moondream')
                        if default_model in models:
                            self.model_combo.SetValue(default_model)
                        elif models:
                            self.model_combo.SetValue(models[0])
                    else:
                        self.model_combo.SetValue("moondream")
                else:
                    self.model_combo.SetValue("moondream")
            elif provider == "openai":
                # Common OpenAI models
                models = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4"]
                for model in models:
                    self.model_combo.Append(model)
                self.model_combo.SetValue("gpt-4o")
            elif provider == "claude":
                # Claude models
                models = ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-opus-20240229"]
                for model in models:
                    self.model_combo.Append(model)
                self.model_combo.SetValue("claude-3-5-sonnet-20241022")
        except Exception as e:
            print(f"Error populating models: {e}")
            self.model_combo.SetValue(self.config.get('model', 'moondream'))
        
        # Restore focus to model combo if it had focus before
        # Use CallAfter to ensure combo box is fully populated and stable
        if had_focus:
            # Add a small delay to ensure all GUI updates are complete
            # This prevents accessibility crashes during rapid state changes
            wx.CallLater(50, self.model_combo.SetFocus)
    
    def load_prompts(self):
        """Load available prompt styles from config file"""
        self.prompt_choice.Clear()
        prompts_added = False
        default_style = "narrative"
        
        # Try to load from config file using config_loader
        if load_json_config:
            try:
                cfg, path, source = load_json_config(
                    'image_describer_config.json',
                    env_var_file='IDT_IMAGE_DESCRIBER_CONFIG'
                )
                if cfg:
                    prompts = cfg.get('prompt_variations', {})
                    default_style = cfg.get('default_prompt_style', 'narrative')
                    for prompt_name in prompts.keys():
                        self.prompt_choice.Append(prompt_name)
                        prompts_added = True
            except Exception:
                pass
        
        # Fallback to hardcoded prompts if config load failed
        if not prompts_added:
            fallback_prompts = ["narrative", "detailed", "concise", "technical", "artistic"]
            for prompt in fallback_prompts:
                self.prompt_choice.Append(prompt)
            default_style = "narrative"
        
        # Select default prompt style
        if self.prompt_choice.GetCount() > 0:
            default_idx = self.prompt_choice.FindString(default_style)
            if default_idx != wx.NOT_FOUND:
                self.prompt_choice.SetSelection(default_idx)
            else:
                self.prompt_choice.SetSelection(0)
    
    def get_config(self):
        """Get the configured options"""
        return {
            'skip_existing': self.skip_existing_cb.GetValue(),
            'provider': self.provider_choice.GetStringSelection().lower(),
            'model': self.model_combo.GetValue(),
            'prompt_style': self.prompt_choice.GetStringSelection(),
            'custom_prompt': self.custom_prompt_input.GetValue(),
        }


class ImageDetailDialog(wx.Dialog):
    """Dialog for viewing image details and metadata"""
    
    def __init__(self, image_item: ImageItem, parent=None):
        super().__init__(
            parent,
            title=f"Image Details - {Path(image_item.file_path).name}",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        
        self.image_item = image_item
        self.init_ui()
        self.SetSize((700, 600))
        self.Centre()
    
    def init_ui(self):
        """Initialize the dialog UI"""
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Create notebook for tabs with keyboard navigation support
        self.detail_notebook = wx.Notebook(self, style=wx.NB_TOP)
        set_accessible_name(self.detail_notebook, "Image detail tabs")
        set_accessible_description(self.detail_notebook, "Use left and right arrow keys to navigate between tabs")
        
        # Details tab
        details_panel = self.create_details_panel(self.detail_notebook)
        self.detail_notebook.AddPage(details_panel, "&Details")
        
        # Descriptions tab
        desc_panel = self.create_descriptions_panel(self.detail_notebook)
        self.detail_notebook.AddPage(desc_panel, "D&escriptions")
        
        main_sizer.Add(self.detail_notebook, 1, wx.ALL | wx.EXPAND, 10)
        
        # Dialog buttons
        btn_sizer = self.CreateButtonSizer(wx.CLOSE)
        main_sizer.Add(btn_sizer, 0, wx.ALL | wx.EXPAND, 10)
        
        self.SetSizer(main_sizer)
    
    def create_details_panel(self, parent):
        """Create details panel"""
        panel = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # File info
        file_path = Path(self.image_item.file_path)
        info_text = wx.TextCtrl(
            panel,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP,
            value=f"File: {file_path.name}\n"
                  f"Path: {file_path.parent}\n"
                  f"Type: {self.image_item.item_type}\n"
                  f"Descriptions: {len(self.image_item.descriptions)}"
        )
        sizer.Add(info_text, 1, wx.ALL | wx.EXPAND, 10)
        
        panel.SetSizer(sizer)
        return panel
    
    def create_descriptions_panel(self, parent):
        """Create descriptions panel"""
        panel = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        if not self.image_item.descriptions:
            no_desc_label = wx.StaticText(panel, label="No descriptions yet")
            sizer.Add(no_desc_label, 0, wx.ALL, 10)
        else:
            # List descriptions
            for i, desc in enumerate(self.image_item.descriptions, 1):
                desc_box = wx.StaticBox(panel, label=f"Description {i}")
                desc_sizer = wx.StaticBoxSizer(desc_box, wx.VERTICAL)
                
                # Metadata
                meta_text = f"Model: {desc.model}\nPrompt: {desc.prompt_style}\nCreated: {desc.created}"
                meta_label = wx.StaticText(panel, label=meta_text)
                desc_sizer.Add(meta_label, 0, wx.ALL, 5)
                
                # Description text
                desc_text = wx.TextCtrl(
                    panel,
                    style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP,
                    value=desc.text,
                    size=(-1, 100)
                )
                desc_sizer.Add(desc_text, 0, wx.ALL | wx.EXPAND, 5)
                
                sizer.Add(desc_sizer, 0, wx.ALL | wx.EXPAND, 5)
        
        panel.SetSizer(sizer)
        return panel
