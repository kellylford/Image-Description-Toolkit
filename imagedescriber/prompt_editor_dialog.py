#!/usr/bin/env python3
"""
Prompt Editor Dialog for ImageDescriber

Dialog version of the Prompt Editor for integration into ImageDescriber.
Allows users to view, edit, add, and manage prompt variations in the 
image_describer_config.json file.

Features:
- Visual list of all available prompts
- Easy editing with character count
- Add new prompt styles
- Delete existing prompts
- Duplicate prompts
- Set default prompt style
- Multi-provider AI support (Ollama, OpenAI, Claude)
- Set default AI provider and model
- API key configuration for cloud providers
- Live model discovery from selected AI provider
- Input validation and error handling
- Accessible design with screen reader support
- Dialog buttons: OK (save & close), Cancel (discard), Apply (save & continue)
"""

import sys
import os
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

import wx

# Ensure project root is on sys.path so sibling modules (shared/, imagedescriber/) import in dev and frozen modes
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
        ModifiedStateMixin,
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

# Import ollama for model discovery (optional)
try:
    import ollama
except ImportError:
    ollama = None

# Import AI providers for multi-provider support (optional)
try:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from imagedescriber.ai_providers import (
        OllamaProvider,
        OpenAIProvider,
        ClaudeProvider,
        DEV_CLAUDE_MODELS
    )
    AI_PROVIDERS_AVAILABLE = True
except ImportError as e:
    AI_PROVIDERS_AVAILABLE = False
    print(f"Warning: AI providers not available: {e}")


class PromptEditorDialog(wx.Dialog, ModifiedStateMixin):
    """Dialog for editing image description prompts"""
    
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, title="Image Description Prompt Editor", size=(900, 650))
        ModifiedStateMixin.__init__(self)
        
        # Find the config file
        self.config_file = find_config_file('image_describer_config.json')
        self.config_data = {}
        self.current_prompt_name = None
        
        # Setup UI
        self.init_ui()
        
        # Load initial data
        self.load_config()
        # Initialize window title context (app name + current file)
        self.update_window_title("Image Description Prompt Editor", self.config_file.name if self.config_file else "(No config)")
    
    def init_ui(self):
        """Initialize the user interface"""
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Create splitter for resizable panels
        splitter = wx.SplitterWindow(panel, style=wx.SP_LIVE_UPDATE)
        
        # Left panel - Prompt list and controls
        left_panel = self.create_left_panel(splitter)
        
        # Right panel - Prompt editor
        right_panel = self.create_right_panel(splitter)
        
        # Set initial splitter sizes (30% left, 70% right)
        splitter.SplitVertically(left_panel, right_panel, 300)
        splitter.SetMinimumPaneSize(200)
        
        main_sizer.Add(splitter, 1, wx.EXPAND | wx.ALL, 5)
        
        # Dialog buttons
        btn_sizer = self.create_dialog_buttons(panel)
        main_sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        panel.SetSizer(main_sizer)
        
        # Bind close event
        self.Bind(wx.EVT_CLOSE, self.on_dialog_close)
    
    def create_left_panel(self, parent):
        """Create the left panel with prompt list and controls"""
        panel = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Prompt list group
        list_box = wx.StaticBox(panel, label="Available Prompts")
        list_sizer = wx.StaticBoxSizer(list_box, wx.VERTICAL)
        
        self.prompt_list = wx.ListBox(list_box, style=wx.LB_SINGLE | wx.LB_NEEDED_SB, name="Available prompts")
        self.prompt_list.Bind(wx.EVT_LISTBOX, self.on_prompt_selected)
        list_sizer.Add(self.prompt_list, 1, wx.EXPAND | wx.ALL, 5)
        
        # Prompt list buttons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.add_btn = wx.Button(list_box, label="Add New")
        self.add_btn.Bind(wx.EVT_BUTTON, self.add_new_prompt)
        btn_sizer.Add(self.add_btn, 1, wx.ALL, 2)
        
        self.delete_btn = wx.Button(list_box, label="Delete")
        self.delete_btn.Bind(wx.EVT_BUTTON, self.delete_prompt)
        self.delete_btn.Enable(False)
        btn_sizer.Add(self.delete_btn, 1, wx.ALL, 2)
        
        self.duplicate_btn = wx.Button(list_box, label="Duplicate")
        self.duplicate_btn.Bind(wx.EVT_BUTTON, self.duplicate_prompt)
        self.duplicate_btn.Enable(False)
        btn_sizer.Add(self.duplicate_btn, 1, wx.ALL, 2)
        
        list_sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 5)
        sizer.Add(list_sizer, 1, wx.EXPAND | wx.ALL, 5)
        
        # Default settings group
        default_box = wx.StaticBox(panel, label="Default Settings")
        default_sizer = wx.StaticBoxSizer(default_box, wx.VERTICAL)
        
        form_sizer = wx.FlexGridSizer(rows=4, cols=2, vgap=5, hgap=5)
        form_sizer.AddGrowableCol(1, 1)
        
        # Default prompt style
        form_sizer.Add(wx.StaticText(default_box, label="Default Style:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.default_prompt_combo = wx.Choice(default_box)
        self.default_prompt_combo.Bind(wx.EVT_CHOICE, self.on_default_changed)
        form_sizer.Add(self.default_prompt_combo, 1, wx.EXPAND)
        
        # AI Provider selection
        form_sizer.Add(wx.StaticText(default_box, label="AI Provider:"), 0, wx.ALIGN_CENTER_VERTICAL)
        provider_panel = wx.Panel(default_box)
        provider_sizer = wx.BoxSizer(wx.VERTICAL)
        self.provider_combo = wx.Choice(provider_panel, choices=["ollama", "openai", "claude"])
        self.provider_combo.Bind(wx.EVT_CHOICE, self.on_provider_changed)
        provider_sizer.Add(self.provider_combo, 0, wx.EXPAND)
        provider_info = wx.StaticText(provider_panel, label="(Can be overridden with --provider flag)")
        provider_info.SetForegroundColour(wx.Colour(128, 128, 128))
        provider_sizer.Add(provider_info, 0, wx.TOP, 2)
        provider_panel.SetSizer(provider_sizer)
        form_sizer.Add(provider_panel, 1, wx.EXPAND)
        
        # API Key field
        form_sizer.Add(wx.StaticText(default_box, label="API Key:"), 0, wx.ALIGN_CENTER_VERTICAL)
        api_key_panel = wx.Panel(default_box)
        api_key_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.api_key_text = wx.TextCtrl(api_key_panel, style=wx.TE_PASSWORD)
        self.api_key_text.SetHint("Enter API key or leave empty to use environment variable")
        self.api_key_text.Bind(wx.EVT_TEXT, self.on_default_changed)
        api_key_sizer.Add(self.api_key_text, 1, wx.EXPAND)
        self.show_api_key_btn = wx.ToggleButton(api_key_panel, label="Show", size=(60, -1))
        self.show_api_key_btn.Bind(wx.EVT_TOGGLEBUTTON, self.toggle_api_key_visibility)
        api_key_sizer.Add(self.show_api_key_btn, 0, wx.LEFT, 5)
        api_key_panel.SetSizer(api_key_sizer)
        self.api_key_panel = api_key_panel
        form_sizer.Add(api_key_panel, 1, wx.EXPAND)
        
        # Default model with refresh button
        form_sizer.Add(wx.StaticText(default_box, label="Default Model:"), 0, wx.ALIGN_CENTER_VERTICAL)
        model_panel = wx.Panel(default_box)
        model_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.default_model_combo = wx.Choice(model_panel)
        self.default_model_combo.Bind(wx.EVT_CHOICE, self.on_default_changed)
        model_sizer.Add(self.default_model_combo, 1, wx.EXPAND)
        self.refresh_models_btn = wx.Button(model_panel, label="Refresh", size=(60, -1))
        self.refresh_models_btn.Bind(wx.EVT_BUTTON, lambda e: self.populate_model_combo())
        model_sizer.Add(self.refresh_models_btn, 0, wx.LEFT, 5)
        model_panel.SetSizer(model_sizer)
        form_sizer.Add(model_panel, 1, wx.EXPAND)
        
        default_sizer.Add(form_sizer, 0, wx.EXPAND | wx.ALL, 5)
        sizer.Add(default_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        panel.SetSizer(sizer)
        return panel
    
    def create_right_panel(self, parent):
        """Create the right panel with prompt editor"""
        panel = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Prompt name editor
        name_box = wx.StaticBox(panel, label="Prompt Name")
        name_sizer = wx.StaticBoxSizer(name_box, wx.VERTICAL)
        
        self.prompt_name_text = wx.TextCtrl(name_box)
        self.prompt_name_text.Bind(wx.EVT_TEXT, self.on_prompt_name_changed)
        name_sizer.Add(self.prompt_name_text, 0, wx.EXPAND | wx.ALL, 5)
        
        sizer.Add(name_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        # Prompt text editor
        text_box = wx.StaticBox(panel, label="Prompt Text")
        text_sizer = wx.StaticBoxSizer(text_box, wx.VERTICAL)
        
        self.prompt_text_edit = wx.TextCtrl(text_box, style=wx.TE_MULTILINE | wx.TE_WORDWRAP, name="Prompt text")
        self.prompt_text_edit.Bind(wx.EVT_TEXT, self.on_prompt_text_changed)
        
        # Set monospace font for better editing
        font = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.prompt_text_edit.SetFont(font)
        
        text_sizer.Add(self.prompt_text_edit, 1, wx.EXPAND | wx.ALL, 5)
        
        # Character count label
        self.char_count_label = wx.StaticText(text_box, label="Characters: 0")
        text_sizer.Add(self.char_count_label, 0, wx.ALIGN_RIGHT | wx.ALL, 5)
        
        sizer.Add(text_sizer, 1, wx.EXPAND | wx.ALL, 5)
        
        panel.SetSizer(sizer)
        return panel
    
    def create_dialog_buttons(self, parent):
        """Create OK, Cancel, Apply buttons for the dialog"""
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # Tips button on the left
        self.tips_btn = wx.Button(parent, label="Prompt Writing Tips")
        self.tips_btn.Bind(wx.EVT_BUTTON, self.show_tips)
        btn_sizer.Add(self.tips_btn, 0, wx.ALL, 5)
        
        btn_sizer.AddStretchSpacer()
        
        # OK, Cancel, Apply buttons on the right
        self.ok_btn = wx.Button(parent, wx.ID_OK, label="OK")
        self.ok_btn.Bind(wx.EVT_BUTTON, self.on_ok)
        btn_sizer.Add(self.ok_btn, 0, wx.ALL, 5)
        
        self.cancel_btn = wx.Button(parent, wx.ID_CANCEL, label="Cancel")
        self.cancel_btn.Bind(wx.EVT_BUTTON, self.on_cancel)
        btn_sizer.Add(self.cancel_btn, 0, wx.ALL, 5)
        
        self.apply_btn = wx.Button(parent, wx.ID_APPLY, label="Apply")
        self.apply_btn.Bind(wx.EVT_BUTTON, self.on_apply)
        self.apply_btn.Enable(False)
        btn_sizer.Add(self.apply_btn, 0, wx.ALL, 5)
        
        return btn_sizer
    
    def load_config(self):
        """Load the configuration file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config_data = json.load(f)
            else:
                # Create default config if file doesn't exist
                self.config_data = self.create_default_config()
                self.save_config_internal()
            
            # Load provider and API key if present
            provider = self.config_data.get('default_provider', 'ollama')
            self.provider_combo.SetStringSelection(provider)
            
            api_key = self.config_data.get('api_key', '')
            self.api_key_text.SetValue(api_key)
            
            # Update API key field visibility
            self.on_provider_changed(None)
            
            self.populate_prompt_list()
            self.populate_default_combo()
            self.populate_model_combo()
            self.modified = False
            self.update_ui_state()
            
        except Exception as e:
            show_error(self, f"Failed to load configuration file:\n{e}")
            self.config_data = self.create_default_config()
    
    def create_default_config(self):
        """Create a default configuration with basic prompts"""
        return {
            "default_prompt_style": "detailed",
            "default_provider": "ollama",
            "prompt_variations": {
                "detailed": "Describe this image in detail, including:\n- Main subjects/objects\n- Setting/environment\n- Key colors and lighting\n- Notable activities or composition\nKeep it comprehensive and informative for metadata.",
                "concise": "Describe this image concisely, including the main subjects, setting, and key visual elements.",
                "narrative": "Provide a narrative description including objects, colors and detail. Avoid interpretation, just describe what you see.",
                "artistic": "Analyze this image from an artistic perspective, describing composition, colors, mood, and visual technique.",
                "technical": "Provide a technical analysis of this image including photographic technique, lighting, and image quality."
            },
            "model_settings": {
                "model": "moondream",
                "temperature": 0.1,
                "num_predict": 600,
                "top_k": 40,
                "top_p": 0.9
            }
        }
    
    def populate_prompt_list(self):
        """Populate the prompt list widget"""
        self.prompt_list.Clear()
        prompt_variations = self.config_data.get('prompt_variations', {})
        
        for name in sorted(prompt_variations.keys()):
            self.prompt_list.Append(name)
    
    def populate_default_combo(self):
        """Populate the default prompt combo box"""
        self.default_prompt_combo.Clear()
        prompt_variations = self.config_data.get('prompt_variations', {})
        self.default_prompt_combo.Append(sorted(prompt_variations.keys()))
        
        # Set current default with case-insensitive matching
        default_style = self.config_data.get('default_prompt_style', '')
        if default_style:
            # Create case-insensitive lookup
            lower_variations = {k.lower(): k for k in prompt_variations.keys()}
            if default_style.lower() in lower_variations:
                actual_key = lower_variations[default_style.lower()]
                self.default_prompt_combo.SetStringSelection(actual_key)
    
    def populate_model_combo(self):
        """Populate the default model combo box with models from the selected provider"""
        self.default_model_combo.Clear()
        
        provider = self.provider_combo.GetStringSelection()
        
        try:
            # Get models based on selected provider
            if provider == "ollama":
                # Use legacy Ollama module if available
                if ollama is None:
                    raise ImportError("Ollama module not available")
                models_response = ollama.list()
                available_models = [model.model for model in models_response['models']]
                
            elif provider == "openai":
                # OpenAI models - return predefined list
                available_models = [
                    "gpt-4o",
                    "gpt-4o-mini",
                    "gpt-4-turbo",
                    "gpt-4-vision-preview",
                    "gpt-4"
                ]
                
            elif provider == "claude":
                # Claude models - sourced from central registry via ai_providers
                available_models = list(DEV_CLAUDE_MODELS) if AI_PROVIDERS_AVAILABLE else []
            else:
                available_models = []
            
            if not available_models:
                self.default_model_combo.Append("No models available")
                self.default_model_combo.SetSelection(0)
                self.default_model_combo.Enable(False)
                return
            
            self.default_model_combo.Enable(True)
            
            # Add models to combo box
            for model_name in available_models:
                # Check if we have info about this model in config
                model_info = self.config_data.get('available_models', {}).get(model_name, {})
                description = model_info.get('description', '')
                recommended = model_info.get('recommended', False)
                
                display_text = f"{model_name}"
                if recommended:
                    display_text += " (Recommended)"
                if description:
                    display_text += f" - {description}"
                
                self.default_model_combo.Append(display_text, model_name)
            
            # Set current default
            default_model = self.config_data.get('default_model', '')
            if default_model:
                # Find the model in the combo
                for i in range(self.default_model_combo.GetCount()):
                    if self.default_model_combo.GetClientData(i) == default_model:
                        self.default_model_combo.SetSelection(i)
                        break
                        
        except Exception as e:
            # Fallback on error
            error_msg = f"{provider.title()} not available: {e}"
            print(f"Warning: {error_msg}")
            self.default_model_combo.Append(error_msg)
            self.default_model_combo.SetSelection(0)
            self.default_model_combo.Enable(False)
    
    def on_prompt_selected(self, event):
        """Handle prompt selection change"""
        selection = self.prompt_list.GetSelection()
        if selection != wx.NOT_FOUND:
            prompt_name = self.prompt_list.GetString(selection)
            self.load_prompt(prompt_name)
            self.delete_btn.Enable(True)
            self.duplicate_btn.Enable(True)
        else:
            self.clear_editor()
            self.delete_btn.Enable(False)
            self.duplicate_btn.Enable(False)
    
    def load_prompt(self, prompt_name):
        """Load a prompt into the editor with case-insensitive lookup"""
        self.current_prompt_name = prompt_name
        prompt_variations = self.config_data.get('prompt_variations', {})
        
        # Case-insensitive lookup
        lower_variations = {k.lower(): v for k, v in prompt_variations.items()}
        prompt_text = lower_variations.get(prompt_name.lower(), '')
        
        # Temporarily disconnect signals to avoid triggering changes
        self.prompt_name_text.ChangeValue(prompt_name)
        self.prompt_text_edit.ChangeValue(prompt_text)
        
        self.update_char_count()
    
    def clear_editor(self):
        """Clear the editor"""
        self.current_prompt_name = None
        self.prompt_name_text.Clear()
        self.prompt_text_edit.Clear()
        self.char_count_label.SetLabel("Characters: 0")
    
    def on_prompt_name_changed(self, event):
        """Handle prompt name change"""
        if self.current_prompt_name:
            self.mark_modified()
    
    def on_prompt_text_changed(self, event):
        """Handle prompt text change"""
        if self.current_prompt_name:
            self.mark_modified()
            self.update_char_count()
    
    def on_default_changed(self, event):
        """Handle default prompt change"""
        self.mark_modified()
    
    def on_provider_changed(self, event):
        """Handle AI provider change"""
        provider = self.provider_combo.GetStringSelection()
        # Show/hide API key field based on provider
        needs_api_key = provider in ["openai", "huggingface"]
        self.api_key_panel.Show(needs_api_key)
        self.Layout()
        
        # Refresh the model list for the new provider
        self.populate_model_combo()
        
        # Mark as modified
        self.mark_modified()
    
    def toggle_api_key_visibility(self, event):
        """Toggle API key visibility between password and plain text"""
        if self.show_api_key_btn.GetValue():
            self.api_key_text.SetWindowStyle(wx.TE_LEFT)
            self.show_api_key_btn.SetLabel("Hide")
        else:
            self.api_key_text.SetWindowStyle(wx.TE_PASSWORD)
            self.show_api_key_btn.SetLabel("Show")
        self.api_key_text.Refresh()
    
    def update_char_count(self):
        """Update the character count label"""
        count = len(self.prompt_text_edit.GetValue())
        self.char_count_label.SetLabel(f"Characters: {count}")
    
    def update_ui_state(self):
        """Update UI state based on current data"""
        self.update_window_title("Image Description Prompt Editor", self.config_file.name)
        self.apply_btn.Enable(self.modified)
    
    def add_new_prompt(self, event):
        """Add a new prompt"""
        dlg = wx.TextEntryDialog(self, "Enter prompt name:", "New Prompt")
        if dlg.ShowModal() == wx.ID_OK:
            name = dlg.GetValue().strip()
            
            if not name:
                dlg.Destroy()
                return
            
            # Check if name already exists
            if name in self.config_data.get('prompt_variations', {}):
                show_warning(self, f"Prompt '{name}' already exists.")
                dlg.Destroy()
                return
            
            # Add new prompt with default text
            if 'prompt_variations' not in self.config_data:
                self.config_data['prompt_variations'] = {}
            
            self.config_data['prompt_variations'][name] = "Describe this image focusing on [add your specific requirements here]."
            
            self.populate_prompt_list()
            self.populate_default_combo()
            self.populate_model_combo()
            
            # Select the new prompt
            idx = self.prompt_list.FindString(name)
            if idx != wx.NOT_FOUND:
                self.prompt_list.SetSelection(idx)
                self.on_prompt_selected(None)
                self.prompt_text_edit.SetFocus()
            
            self.mark_modified()
        
        dlg.Destroy()
    
    def duplicate_prompt(self, event):
        """Duplicate the selected prompt"""
        if not self.current_prompt_name:
            return
        
        base_name = self.current_prompt_name
        new_name = f"{base_name}_copy"
        
        # Find unique name
        counter = 1
        while new_name in self.config_data.get('prompt_variations', {}):
            counter += 1
            new_name = f"{base_name}_copy_{counter}"
        
        # Get the current prompt text
        prompt_variations = self.config_data.get('prompt_variations', {})
        original_text = prompt_variations.get(self.current_prompt_name, '')
        
        # Add the duplicate
        self.config_data['prompt_variations'][new_name] = original_text
        
        self.populate_prompt_list()
        self.populate_default_combo()
        self.populate_model_combo()
        
        # Select the new prompt
        idx = self.prompt_list.FindString(new_name)
        if idx != wx.NOT_FOUND:
            self.prompt_list.SetSelection(idx)
            self.on_prompt_selected(None)
        
        self.mark_modified()
    
    def delete_prompt(self, event):
        """Delete the selected prompt"""
        if not self.current_prompt_name:
            return
        
        dlg = wx.MessageDialog(self, 
                              f"Are you sure you want to delete the prompt '{self.current_prompt_name}'?",
                              "Delete Prompt",
                              wx.YES_NO | wx.ICON_QUESTION)
        
        if dlg.ShowModal() == wx.ID_YES:
            # Remove from config
            if 'prompt_variations' in self.config_data:
                self.config_data['prompt_variations'].pop(self.current_prompt_name, None)
            
            # If this was the default, choose a new default
            if self.config_data.get('default_prompt_style') == self.current_prompt_name:
                remaining_prompts = list(self.config_data.get('prompt_variations', {}).keys())
                if remaining_prompts:
                    self.config_data['default_prompt_style'] = remaining_prompts[0]
                else:
                    self.config_data['default_prompt_style'] = ''
            
            self.populate_prompt_list()
            self.populate_default_combo()
            self.populate_model_combo()
            self.clear_editor()
            self.mark_modified()
        
        dlg.Destroy()
    
    def save_config_internal(self):
        """Internal method to save configuration to file"""
        try:
            # Update the current prompt if one is being edited
            if self.current_prompt_name and self.prompt_name_text.GetValue().strip():
                new_name = self.prompt_name_text.GetValue().strip()
                new_text = self.prompt_text_edit.GetValue()
                
                # Handle name change
                if new_name != self.current_prompt_name:
                    # Remove old entry
                    self.config_data['prompt_variations'].pop(self.current_prompt_name, None)
                    
                    # Update default if it was pointing to the old name
                    if self.config_data.get('default_prompt_style') == self.current_prompt_name:
                        self.config_data['default_prompt_style'] = new_name
                
                # Set new/updated entry
                self.config_data['prompt_variations'][new_name] = new_text
                self.current_prompt_name = new_name
            
            # Update default prompt style
            self.config_data['default_prompt_style'] = self.default_prompt_combo.GetStringSelection()
            
            # Update default provider
            self.config_data['default_provider'] = self.provider_combo.GetStringSelection()
            
            # Update API key (only if not empty)
            api_key = self.api_key_text.GetValue().strip()
            if api_key:
                self.config_data['api_key'] = api_key
            elif 'api_key' in self.config_data:
                # Remove api_key if it's now empty
                del self.config_data['api_key']
            
            # Update default model
            selection = self.default_model_combo.GetSelection()
            if selection != wx.NOT_FOUND:
                model_data = self.default_model_combo.GetClientData(selection)
                if model_data:
                    self.config_data['default_model'] = model_data
            
            # Create backup before saving
            if self.config_file.exists():
                backup_path = self.config_file.with_suffix('.bak')
                shutil.copy2(self.config_file, backup_path)
            
            # Save to file
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=2, ensure_ascii=False)
            
            self.modified = False
            self.update_ui_state()
            
            self.populate_prompt_list()
            self.populate_default_combo()
            self.populate_model_combo()
            
            # Re-select current prompt
            if self.current_prompt_name:
                idx = self.prompt_list.FindString(self.current_prompt_name)
                if idx != wx.NOT_FOUND:
                    self.prompt_list.SetSelection(idx)
            
            return True
            
        except Exception as e:
            show_error(self, f"Failed to save configuration:\n{e}")
            return False
    
    def on_save(self, event):
        """Wrapper for save_config_internal to work with ModifiedStateMixin"""
        return self.save_config_internal()
    
    def show_tips(self, event):
        """Show prompt writing tips"""
        tips = """Prompt Writing Tips:

1. BE SPECIFIC
   • Tell the AI exactly what to focus on
   • Use bullet points or numbered lists
   • Specify desired detail level

2. STRUCTURE YOUR PROMPTS
   • Start with main instruction
   • Add specific requirements
   • End with style/format guidance

3. EXAMPLES OF GOOD PROMPTS
   • "Describe this image in detail, including: [list]"
   • "Analyze this image focusing on [specific aspect]"
   • "Provide a [style] description of this image"

4. AVOID AMBIGUITY
   • Use clear, concrete language
   • Avoid subjective terms
   • Be consistent in terminology

5. TEST AND ITERATE
   • Use the comprehensive test tool
   • Compare results across different prompts
   • Refine based on actual output quality

6. CONSIDER YOUR USE CASE
   • Academic: formal, detailed analysis
   • Creative: vivid, engaging descriptions
   • Technical: focus on composition, lighting
   • Accessibility: clear, structured descriptions"""
        
        show_info(self, tips, "Prompt Writing Tips")
    
    def on_ok(self, event):
        """Handle OK button - save and close"""
        if self.modified:
            if self.save_config_internal():
                self.EndModal(wx.ID_OK)
        else:
            self.EndModal(wx.ID_OK)
    
    def on_cancel(self, event):
        """Handle Cancel button - discard changes and close"""
        if self.modified:
            if not self.confirm_unsaved_changes():
                return
        self.EndModal(wx.ID_CANCEL)
    
    def on_apply(self, event):
        """Handle Apply button - save but keep dialog open"""
        if self.save_config_internal():
            show_info(self, "Configuration saved successfully")
    
    def on_dialog_close(self, event):
        """Handle dialog close event"""
        if self.modified:
            if not self.confirm_unsaved_changes():
                if event.CanVeto():
                    event.Veto()
                return
        
        if event.CanVeto():
            self.EndModal(wx.ID_CANCEL)
        else:
            self.Destroy()
