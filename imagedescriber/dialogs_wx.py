"""
wxPython Dialog classes for Image Describer

This module contains all dialog windows used in the Image Describer wxPython application.
All dialogs use shared utilities and follow accessibility best practices.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any

import wx
import platform

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
        logging.error("Failed to import load_json_config from both scripts.config_loader and config_loader")

# Get logger for this module
logger = logging.getLogger(__name__)

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
        self.add_to_existing_cb.Bind(wx.EVT_CHECKBOX, self.on_add_to_existing_changed)
        options_sizer.Add(self.add_to_existing_cb, 0, wx.ALL, 5)
        
        main_sizer.Add(options_sizer, 0, wx.ALL | wx.EXPAND, 10)
        
        # Existing directories display
        self.existing_sizer = None  # Store reference for show/hide
        self.existing_list = None  # Store listbox reference
        if existing_directories:
            existing_box = wx.StaticBox(
                self,
                label=f"Current Workspace Directories ({len(existing_directories)})"
            )
            self.existing_sizer = wx.StaticBoxSizer(existing_box, wx.VERTICAL)
            
            # Use accessible ListBox instead of ScrolledWindow with StaticText
            # This allows screen readers to read each directory name properly
            self.existing_list = wx.ListBox(
                self,
                size=(-1, 150),
                name="Current workspace directories",
                style=wx.LB_SINGLE | wx.LB_NEEDED_SB
            )
            
            # Add directory names to listbox
            for directory in existing_directories:
                self.existing_list.Append(str(Path(directory).name), directory)
            
            self.existing_sizer.Add(self.existing_list, 1, wx.EXPAND | wx.ALL, 5)
            main_sizer.Add(self.existing_sizer, 1, wx.ALL | wx.EXPAND, 10)
            
            # Initially hide the existing directories list
            self.existing_sizer.ShowItems(False)
            self.existing_list.Show(False)
        
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
    
    def on_add_to_existing_changed(self, event):
        """Handle add to existing checkbox state change"""
        if self.existing_sizer and self.existing_list:
            # Show/hide existing directories list based on checkbox state
            show = self.add_to_existing_cb.GetValue()
            self.existing_sizer.ShowItems(show)
            self.existing_list.Show(show)
            self.Layout()
    
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


# ---------------------------------------------------------------------------
# Module-level helper — shared by ProcessingOptionsDialog and
# FollowupQuestionDialog to build the contextual description shown below the
# model dropdown.
# ---------------------------------------------------------------------------

def _get_model_description_text(provider: str, model_id: str) -> str:
    """Return a one-or-two-line guidance string for the selected model.

    Format (paid providers):
        [★ Recommended | ] <cost tier> | <description>
        [⚠ <notes>]

    Returns an empty string if metadata is unavailable.
    """
    provider = (provider or "").lower()

    if provider == "ollama":
        if not model_id:
            return "Local Ollama models have no API cost. Requires Ollama running locally."
        return f"{model_id} — Local AI model running via Ollama. No API key or cloud cost."

    if provider == "openai":
        try:
            from models.openai_models import OPENAI_MODEL_METADATA
        except ImportError:
            try:
                from openai_models import OPENAI_MODEL_METADATA
            except ImportError:
                return ""
        meta = OPENAI_MODEL_METADATA.get(model_id)
        if not meta:
            return f"{model_id} — OpenAI model. See openai.com/api/pricing for cost details."
        parts: list[str] = []
        if meta.get("recommended"):
            parts.append("★ Recommended")
        cost = meta.get("cost", "")
        if cost:
            parts.append(cost)
        desc = meta.get("description", "")
        if desc:
            parts.append(desc)
        line = " | ".join(parts)
        notes = meta.get("notes", "")
        if notes:
            line = (line + "\n⚠ " + notes) if line else ("⚠ " + notes)
        return line

    if provider == "claude":
        try:
            from models.claude_models import CLAUDE_MODEL_METADATA
        except ImportError:
            try:
                from claude_models import CLAUDE_MODEL_METADATA
            except ImportError:
                return ""
        meta = CLAUDE_MODEL_METADATA.get(model_id, {})
        if not meta:
            return f"{model_id} — Anthropic Claude model. See anthropic.com/pricing for costs."
        parts = []
        if meta.get("recommended"):
            parts.append("★ Recommended")
        cost = meta.get("cost", "")
        if cost:
            parts.append(cost)
        desc = meta.get("description", "")
        if desc:
            parts.append(desc)
        return " | ".join(parts)

    return ""


class FollowupQuestionDialog(wx.Dialog):
    """Dialog for asking follow-up questions with model selection"""
    
    def __init__(self, parent, original_provider: str, original_model: str, 
                 description_preview: str, config: dict, cached_ollama_models=None):
        super().__init__(
            parent,
            title="Ask Follow-up Question",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        
        self.original_provider = original_provider
        self.original_model = original_model
        self.config = config
        self.cached_ollama_models = cached_ollama_models  # Use cached models to avoid blocking
        self.question = ""
        self.selected_provider = original_provider
        self.selected_model = original_model
        
        self.init_ui(description_preview)
        self.SetSize((600, 500))
        self.Centre()
    
    def init_ui(self, description_preview: str):
        """Initialize the dialog UI"""
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Show existing description preview
        desc_box = wx.StaticBox(self, label="Existing Description (preview)")
        desc_sizer = wx.StaticBoxSizer(desc_box, wx.VERTICAL)
        
        desc_text = wx.TextCtrl(
            self,
            value=description_preview,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP
        )
        desc_text.SetMinSize((550, 100))
        set_accessible_name(desc_text, "Existing description preview")
        desc_sizer.Add(desc_text, 0, wx.ALL | wx.EXPAND, 5)
        
        main_sizer.Add(desc_sizer, 0, wx.ALL | wx.EXPAND, 10)
        
        # Model selection section
        model_box = wx.StaticBox(self, label="AI Model for Follow-up")
        model_sizer = wx.StaticBoxSizer(model_box, wx.VERTICAL)
        
        # Show original model with friendly display name for Claude models
        try:
            from ai_providers import format_claude_model_for_display
            original_model_display = (
                format_claude_model_for_display(self.original_model)
                if self.original_provider.lower() == 'claude'
                else self.original_model
            )
        except Exception:
            original_model_display = self.original_model
        original_label = wx.StaticText(
            self,
            label=f"Original: {self.original_provider.title()} - {original_model_display}"
        )
        original_label.SetFont(original_label.GetFont().MakeItalic())
        model_sizer.Add(original_label, 0, wx.ALL, 5)
        
        # Provider selection
        provider_sizer = wx.BoxSizer(wx.HORIZONTAL)
        provider_label = wx.StaticText(self, label="&Provider:")
        provider_sizer.Add(provider_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        
        self.provider_choice = wx.Choice(self, choices=["ollama", "openai", "claude"])
        self.provider_choice.SetStringSelection(self.original_provider)
        self.provider_choice.Bind(wx.EVT_CHOICE, self.on_provider_changed)
        set_accessible_name(self.provider_choice, "AI provider")
        provider_sizer.Add(self.provider_choice, 1, wx.EXPAND)
        
        model_sizer.Add(provider_sizer, 0, wx.ALL | wx.EXPAND, 5)
        
        # Model name input
        model_name_sizer = wx.BoxSizer(wx.HORIZONTAL)
        model_label = wx.StaticText(self, label="&Model:")
        model_name_sizer.Add(model_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        
        # ACCESSIBILITY FIX: Use wx.Choice instead of wx.ComboBox to avoid macOS VoiceOver crash
        # wx.ComboBox causes pointer authentication trap in objc_opt_respondsToSelector
        # when accessibility queries parent hierarchy during selection changes
        self.model_combo = wx.Choice(self)
        set_accessible_name(self.model_combo, "Model name")
        self.model_combo.Bind(wx.EVT_CHOICE, self.on_model_changed)
        model_name_sizer.Add(self.model_combo, 1, wx.EXPAND)

        model_sizer.Add(model_name_sizer, 0, wx.ALL | wx.EXPAND, 5)

        # Model description — read-only hint updated whenever provider or model changes.
        # Must have a visible border so it appears in the keyboard tab order for VoiceOver.
        self.model_desc_text = wx.TextCtrl(
            self,
            style=wx.TE_READONLY | wx.TE_MULTILINE | wx.TE_WORDWRAP | wx.TE_NO_VSCROLL,
            name="Model description and guidance"
        )
        self.model_desc_text.SetMinSize((-1, 52))
        set_accessible_name(self.model_desc_text, "Model description and guidance")
        model_sizer.Add(self.model_desc_text, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 5)

        main_sizer.Add(model_sizer, 0, wx.ALL | wx.EXPAND, 10)

        # Populate models for current provider
        self.populate_models()

        # Question input
        question_box = wx.StaticBox(self, label="Your Follow-up Question")
        question_sizer = wx.StaticBoxSizer(question_box, wx.VERTICAL)

        self.question_text = wx.TextCtrl(
            self,
            value="",
            style=wx.TE_MULTILINE | wx.TE_WORDWRAP,
            name="Follow-up question"
        )
        self.question_text.SetMinSize((550, 120))
        self.question_text.SetHint("Enter your question about this image...")
        set_accessible_name(self.question_text, "Follow-up question")
        question_sizer.Add(self.question_text, 1, wx.ALL | wx.EXPAND, 5)
        
        main_sizer.Add(question_sizer, 1, wx.ALL | wx.EXPAND, 10)
        
        # Dialog buttons
        btn_sizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        main_sizer.Add(btn_sizer, 0, wx.ALL | wx.EXPAND, 10)
        
        self.SetSizer(main_sizer)
        
        # Set focus to question input
        wx.CallAfter(self.question_text.SetFocus)
    
    def on_provider_changed(self, event):
        """Handle provider change - update available models"""
        self.populate_models()
        # update_model_description() is called at the end of populate_models()

    def on_model_changed(self, event):
        """Handle model selection change - refresh description hint"""
        self.update_model_description()

    def update_model_description(self):
        """Refresh the description text below the model choice widget."""
        if not hasattr(self, 'model_desc_text'):
            return
        provider = self.provider_choice.GetStringSelection().lower()
        selection = self.model_combo.GetSelection()
        model_id = ""
        if selection != wx.NOT_FOUND:
            try:
                client_data = self.model_combo.GetClientData(selection)
                model_id = client_data if client_data is not None else self.model_combo.GetStringSelection()
            except Exception:
                model_id = self.model_combo.GetStringSelection()
        text = _get_model_description_text(provider, model_id)
        self.model_desc_text.ChangeValue(text)
    
    def populate_models(self):
        """Populate model choice based on selected provider - uses cached models to avoid blocking UI"""
        provider = self.provider_choice.GetStringSelection()
        
        # Save current selection
        current_model = self.model_combo.GetStringSelection()
        
        # Clear choices
        self.model_combo.Clear()
        
        try:
            if provider == "ollama":
                # CRITICAL: Use cached models if available (passed from main app) to avoid blocking UI
                if self.cached_ollama_models:
                    # Sort models alphabetically for easier navigation
                    for model in sorted(self.cached_ollama_models):
                        self.model_combo.Append(model)
                else:
                    # Fallback to common defaults (don't fetch live - would block UI)
                    common_models = sorted(["moondream", "llava", "llama3.2-vision"])
                    for model in common_models:
                        self.model_combo.Append(model)
                        
            elif provider == "openai":
                # Load from canonical list - supports both frozen and dev mode
                try:
                    from ai_providers import DEV_OPENAI_MODELS
                except ImportError:
                    from imagedescriber.ai_providers import DEV_OPENAI_MODELS
                for model in DEV_OPENAI_MODELS:
                    self.model_combo.Append(model)
                    
            elif provider == "claude":
                # Import the official Claude models list with friendly display names
                from ai_providers import DEV_CLAUDE_MODELS, CLAUDE_MODEL_METADATA
                for model in DEV_CLAUDE_MODELS:
                    display = CLAUDE_MODEL_METADATA.get(model, {}).get("name", model)
                    self.model_combo.Append(display, model)  # client data = API ID
        except Exception as e:
            logger.warning(f"Error populating models: {e}")
        
        # Restore previous selection if it exists in new list, otherwise use first item
        if current_model and current_model in [self.model_combo.GetString(i) for i in range(self.model_combo.GetCount())]:
            self.model_combo.SetStringSelection(current_model)
        elif self.model_combo.GetCount() > 0:
            self.model_combo.SetSelection(0)
        else:
            # Fallback to original model - try to find and select it
            try:
                from ai_providers import CLAUDE_MODEL_METADATA
                display = CLAUDE_MODEL_METADATA.get(self.original_model, {}).get("name", self.original_model)
                self.model_combo.Append(display, self.original_model)
                self.model_combo.SetSelection(0)
            except:
                pass  # Silently ignore if can't set fallback

        # Always refresh the description hint after loading models
        self.update_model_description()

    def get_values(self):
        """Get the question and selected model/provider.
        Returns the API model ID (client data), not the friendly display name."""
        selection = self.model_combo.GetSelection()
        if selection != wx.NOT_FOUND:
            try:
                client_data = self.model_combo.GetClientData(selection)
                model = client_data if client_data is not None else self.model_combo.GetStringSelection()
            except Exception:
                # Items added without client data (Ollama, OpenAI) raise a C++ assertion
                model = self.model_combo.GetStringSelection()
        else:
            model = self.model_combo.GetStringSelection()
        return {
            'question': self.question_text.GetValue().strip(),
            'provider': self.provider_choice.GetStringSelection(),
            'model': model
        }


class ProcessingOptionsDialog(wx.Dialog):
    """Dialog for configuring processing options"""
    
    def __init__(self, current_config: Dict[str, Any], cached_ollama_models=None, parent=None):
        super().__init__(
            parent,
            title="Processing Options",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        
        self.config = current_config.copy()
        self.cached_ollama_models = cached_ollama_models  # Use cached models if available
        self.init_ui()
        self.SetSize((600, 400))
        self.Centre()
    
    def init_ui(self):
        """Initialize the dialog UI"""
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Create notebook for tabs
        self.notebook = wx.Notebook(self, style=wx.NB_TOP)
        set_accessible_name(self.notebook, "Processing options tabs")
        
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
        # Set from default_provider in config (case-insensitive match)
        default_provider = self.config.get('default_provider', 'ollama').lower()
        provider_map = {'ollama': 0, 'openai': 1, 'claude': 2}
        self.provider_choice.SetSelection(provider_map.get(default_provider, 0))
        self.provider_choice.Bind(wx.EVT_CHOICE, self.on_provider_changed)
        set_accessible_name(self.provider_choice, "AI provider")
        provider_sizer.Add(self.provider_choice, 0, wx.ALL | wx.EXPAND, 5)
        
        sizer.Add(provider_sizer, 0, wx.ALL | wx.EXPAND, 10)
        
        # Model selection
        model_box = wx.StaticBox(panel, label="Model")
        model_sizer = wx.StaticBoxSizer(model_box, wx.VERTICAL)
        
        model_label = wx.StaticText(panel, label="&Model name:")
        model_sizer.Add(model_label, 0, wx.ALL, 5)
        
        # ACCESSIBILITY FIX: Use wx.Choice instead of wx.ComboBox to avoid macOS VoiceOver crash
        self.model_combo = wx.Choice(panel)
        set_accessible_name(self.model_combo, "Model name")
        self.model_combo.Bind(wx.EVT_CHOICE, self.on_model_changed)
        model_sizer.Add(self.model_combo, 0, wx.ALL | wx.EXPAND, 5)

        # Model description — read-only hint that updates whenever the provider or model changes.
        # Must have a visible border so it appears in the keyboard tab order for VoiceOver.
        self.model_desc_text = wx.TextCtrl(
            panel,
            style=wx.TE_READONLY | wx.TE_MULTILINE | wx.TE_WORDWRAP | wx.TE_NO_VSCROLL,
            name="Model description and guidance"
        )
        self.model_desc_text.SetMinSize((-1, 52))
        set_accessible_name(self.model_desc_text, "Model description and guidance")
        model_sizer.Add(self.model_desc_text, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 5)

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
        # update_model_description() is invoked at the end of populate_models_for_provider()

    def on_model_changed(self, event):
        """Handle model selection change - refresh description hint"""
        self.update_model_description()

    def update_model_description(self):
        """Refresh the description text below the model choice widget."""
        if not hasattr(self, 'model_desc_text'):
            return
        provider = self.provider_choice.GetStringSelection().lower()
        selection = self.model_combo.GetSelection()
        model_id = ""
        if selection != wx.NOT_FOUND:
            try:
                client_data = self.model_combo.GetClientData(selection)
                model_id = client_data if client_data is not None else self.model_combo.GetStringSelection()
            except Exception:
                model_id = self.model_combo.GetStringSelection()
        text = _get_model_description_text(provider, model_id)
        self.model_desc_text.ChangeValue(text)
    
    def populate_models_for_provider(self):
        """Populate model list based on selected provider"""
        provider = self.provider_choice.GetStringSelection().lower()
        
        # Clear the model choices (wx.Choice is safe with VoiceOver, no focus workaround needed)
        self.model_combo.Clear()
        
        try:
            if provider == "ollama":
                # Use cached models if available, otherwise query Ollama
                models = None
                if self.cached_ollama_models is not None:
                    # Use cached models for instant loading
                    models = self.cached_ollama_models
                else:
                    # Auto-populate cache on first use (slower, but only happens once)
                    from ai_providers import get_available_providers
                    providers = get_available_providers()
                    if 'ollama' in providers:
                        ollama_provider = providers['ollama']
                        models = ollama_provider.get_available_models()
                        # Cache for next time (update passed reference)
                        self.cached_ollama_models = models
                
                if models:
                    # Sort models alphabetically for easier navigation
                    for model in sorted(models):
                        self.model_combo.Append(model)
                    # Set default if in list
                    default_model = self.config.get('default_model', 'moondream')
                    if default_model in models:
                        self.model_combo.SetStringSelection(default_model)
                    elif models:
                        self.model_combo.SetSelection(0)
                else:
                    self.model_combo.Append("moondream")
                    self.model_combo.SetSelection(0)
            elif provider == "openai":
                # Load from canonical list - supports both frozen and dev mode
                try:
                    from ai_providers import DEV_OPENAI_MODELS
                except ImportError:
                    from imagedescriber.ai_providers import DEV_OPENAI_MODELS
                for model in DEV_OPENAI_MODELS:
                    self.model_combo.Append(model)
                self.model_combo.SetStringSelection("gpt-4o")
            elif provider == "claude":
                # Import the official Claude models list with friendly display names
                from ai_providers import DEV_CLAUDE_MODELS, CLAUDE_MODEL_METADATA
                for model in DEV_CLAUDE_MODELS:
                    display = CLAUDE_MODEL_METADATA.get(model, {}).get("name", model)
                    self.model_combo.Append(display, model)  # client data = API ID
                # Set to first available model (list is ordered by recommendation)
                if self.model_combo.GetCount() > 0:
                    self.model_combo.SetSelection(0)
        except Exception as e:
            print(f"Error populating models: {e}")
            default = self.config.get('default_model', 'moondream')
            if default not in [self.model_combo.GetString(i) for i in range(self.model_combo.GetCount())]:
                self.model_combo.Append(default)
            if default:
                self.model_combo.SetStringSelection(default)

        # Always refresh the description hint after loading models
        self.update_model_description()

    def load_prompts(self):
        """Load available prompt styles from config file

        Uses load_json_config() (same as the CLI and main window) so the prompt
        list reflects the same config that will be used when describing images.
        find_config_file() was previously used here but it does not check the
        user config dir (%APPDATA%/IDT on Windows), leading to a mismatch.
        """
        self.prompt_choice.Clear()
        prompts_added = False
        default_style = "narrative"

        # Load using config_loader for consistent resolution with CLI / main window
        try:
            if load_json_config is None:
                raise ImportError("config_loader.load_json_config not available")
            cfg, config_path, _ = load_json_config('image_describer_config.json')
            if cfg and config_path:
                logger.debug(f"Loading prompts from: {config_path}")

                prompts = cfg.get('prompt_variations', {})
                default_style = cfg.get('default_prompt_style', 'narrative')
                
                if prompts:
                    for prompt_name in prompts.keys():
                        self.prompt_choice.Append(prompt_name)
                        prompts_added = True
                    logger.debug(f"Loaded {len(prompts)} prompts, default={default_style}")
                else:
                    logger.warning(f"Config file has no prompt_variations: {config_path}")
            else:
                logger.warning(f"Config file not found: image_describer_config.json")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {e}")
        except Exception as e:
            logger.error(f"Error loading prompts from config: {e}", exc_info=True)
        
        # Fallback to hardcoded prompts if config load failed
        if not prompts_added:
            logger.info("Using fallback hardcoded prompts")
            fallback_prompts = ["narrative", "detailed", "concise", "technical", "artistic"]
            for prompt in fallback_prompts:
                self.prompt_choice.Append(prompt)
            default_style = "narrative"
        
        # Select default prompt style
        if self.prompt_choice.GetCount() > 0:
            default_idx = self.prompt_choice.FindString(default_style)
            if default_idx != wx.NOT_FOUND:
                self.prompt_choice.SetSelection(default_idx)
                logger.debug(f"Selected default prompt: {default_style}")
            else:
                self.prompt_choice.SetSelection(0)
                logger.debug(f"Default prompt '{default_style}' not found, using first item")
    
    def get_config(self):
        """Get the configured options.
        Returns the API model ID (client data for Claude models), not the friendly display name."""
        selection = self.model_combo.GetSelection()
        if selection != wx.NOT_FOUND:
            try:
                client_data = self.model_combo.GetClientData(selection)
                model = client_data if client_data is not None else self.model_combo.GetStringSelection()
            except Exception:
                # Items added without client data (Ollama, OpenAI) raise a C++ assertion
                model = self.model_combo.GetStringSelection()
        else:
            model = self.model_combo.GetStringSelection()
        return {
            'skip_existing': self.skip_existing_cb.GetValue(),
            'provider': self.provider_choice.GetStringSelection().lower(),
            'model': model,
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
        
        # Create notebook for tabs
        self.detail_notebook = wx.Notebook(self, style=wx.NB_TOP)
        set_accessible_name(self.detail_notebook, "Image detail tabs")
        
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


class VideoExtractionDialog(wx.Dialog):
    """Dialog for configuring video frame extraction settings"""
    
    def __init__(self, parent=None, video_path: str = ""):
        super().__init__(
            parent,
            title="Extract Video Frames",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        
        self.video_path = video_path
        
        # Initialize settings with defaults
        self.extraction_mode = "time_interval"
        self.time_interval = 5.0
        self.scene_threshold = 30.0
        self.process_after_extraction = True
        
        self.init_ui()
        self.SetSize((500, 400))
        self.Centre()
        
        # Set initial focus to extraction mode for accessibility
        wx.CallAfter(self.time_radio.SetFocus)
    
    def init_ui(self):
        """Initialize the dialog UI"""
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Video info
        if self.video_path:
            video_name = Path(self.video_path).name
            info_label = wx.StaticText(panel, label=f"Video: {video_name}")
            info_label.SetFont(info_label.GetFont().Bold())
            main_sizer.Add(info_label, 0, wx.ALL, 10)
        
        # Extraction mode selection
        mode_box = wx.StaticBox(panel, label="Extraction Mode")
        mode_sizer = wx.StaticBoxSizer(mode_box, wx.VERTICAL)
        
        self.time_radio = wx.RadioButton(
            panel,
            label="Time Interval",
            style=wx.RB_GROUP,
            name="Time interval extraction mode"
        )
        self.time_radio.SetValue(True)
        mode_sizer.Add(self.time_radio, 0, wx.ALL, 5)
        
        # Time interval input
        time_panel = wx.Panel(panel)
        time_sizer = wx.BoxSizer(wx.HORIZONTAL)
        time_label = wx.StaticText(time_panel, label="Interval (seconds):")
        self.time_input = wx.SpinCtrlDouble(
            time_panel,
            value="5.0",
            min=0.1,
            max=60.0,
            inc=0.5,
            name="Time interval in seconds"
        )
        self.time_input.SetDigits(1)
        time_sizer.Add(time_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        time_sizer.Add(self.time_input, 0, wx.ALIGN_CENTER_VERTICAL)
        time_panel.SetSizer(time_sizer)
        mode_sizer.Add(time_panel, 0, wx.LEFT | wx.BOTTOM, 25)
        
        mode_sizer.AddSpacer(10)
        
        self.scene_radio = wx.RadioButton(
            panel,
            label="Scene Change Detection",
            name="Scene change detection mode"
        )
        mode_sizer.Add(self.scene_radio, 0, wx.ALL, 5)
        
        # Scene threshold input
        scene_panel = wx.Panel(panel)
        scene_sizer = wx.BoxSizer(wx.HORIZONTAL)
        scene_label = wx.StaticText(scene_panel, label="Threshold:")
        self.scene_input = wx.SpinCtrlDouble(
            scene_panel,
            value="30.0",
            min=1.0,
            max=100.0,
            inc=1.0,
            name="Scene change threshold"
        )
        self.scene_input.SetDigits(1)
        scene_sizer.Add(scene_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        scene_sizer.Add(self.scene_input, 0, wx.ALIGN_CENTER_VERTICAL)
        scene_panel.SetSizer(scene_sizer)
        mode_sizer.Add(scene_panel, 0, wx.LEFT | wx.BOTTOM, 25)
        
        main_sizer.Add(mode_sizer, 0, wx.ALL | wx.EXPAND, 10)
        
        # Processing option
        self.process_checkbox = wx.CheckBox(
            panel,
            label="Process extracted frames automatically",
            name="Auto-process frames checkbox"
        )
        self.process_checkbox.SetValue(True)
        main_sizer.Add(self.process_checkbox, 0, wx.ALL, 10)
        
        # Help text
        help_text = (
            "Time Interval: Extract frames at regular intervals (e.g., every 5 seconds)\n"
            "Scene Change: Extract frames when the scene changes significantly\n\n"
            "Extracted frames will appear in the workspace list after the video."
        )
        help_label = wx.StaticText(panel, label=help_text)
        help_label.SetForegroundColour(wx.Colour(100, 100, 100))
        main_sizer.Add(help_label, 0, wx.ALL, 10)
        
        # Buttons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_sizer.AddStretchSpacer()
        
        cancel_btn = wx.Button(panel, wx.ID_CANCEL, "Cancel")
        ok_btn = wx.Button(panel, wx.ID_OK, "Extract Frames")
        ok_btn.SetDefault()
        
        btn_sizer.Add(cancel_btn, 0, wx.ALL, 5)
        btn_sizer.Add(ok_btn, 0, wx.ALL, 5)
        
        main_sizer.Add(btn_sizer, 0, wx.ALL | wx.EXPAND, 10)
        
        panel.SetSizer(main_sizer)
        
        # Bind radio button events to enable/disable inputs
        self.time_radio.Bind(wx.EVT_RADIOBUTTON, self.on_mode_changed)
        self.scene_radio.Bind(wx.EVT_RADIOBUTTON, self.on_mode_changed)
        
        # Initialize enabled states
        self.on_mode_changed(None)
    
    def on_mode_changed(self, event):
        """Enable/disable inputs based on selected mode"""
        time_mode = self.time_radio.GetValue()
        self.time_input.Enable(time_mode)
        self.scene_input.Enable(not time_mode)
    
    def get_settings(self) -> dict:
        """Get extraction settings from dialog
        
        Returns:
            Dictionary with extraction settings
        """
        mode = "time_interval" if self.time_radio.GetValue() else "scene_change"
        
        settings = {
            "extraction_mode": mode,
            "process_after_extraction": self.process_checkbox.GetValue()
        }
        
        if mode == "time_interval":
            settings["time_interval_seconds"] = self.time_input.GetValue()
        else:
            settings["scene_change_threshold"] = self.scene_input.GetValue()
        
        return settings
