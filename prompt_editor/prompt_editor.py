#!/usr/bin/env python3
"""
Prompt Editor - User-friendly Qt6 application for editing image description prompts

This standalone application allows users to easily view, edit, add, and manage
prompt variations in the image_describer_config.json file without needing to
manually edit JSON. Features include:

- Visual list of all available prompts
- Easy editing with character count
- Add new prompt styles
- Delete existing prompts
- Set default prompt style
- Multi-provider AI support (Ollama, OpenAI, ONNX, Copilot, HuggingFace)
- Set default AI provider and model
- API key configuration for cloud providers (OpenAI, HuggingFace)
- Live model discovery from selected AI provider
- Save and Save As functionality for creating custom configurations
- Open different configuration files
- Backup and restore functionality
- Input validation and error handling
- Accessible design with screen reader support
- Real-time window title updates showing current file and modification status
"""

import sys
import os
import json
import shutil
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QListWidget, QTextEdit, QLineEdit, QPushButton, QLabel, 
    QMessageBox, QSplitter, QGroupBox, QComboBox, QStatusBar,
    QMenuBar, QMenu, QFileDialog, QDialog, QDialogButtonBox,
    QListWidgetItem, QInputDialog, QCheckBox, QFormLayout
)
from PyQt6.QtGui import QAction, QFont, QTextCharFormat, QTextCursor
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

# Import ollama for model discovery (backwards compatibility)
try:
    import ollama
except ImportError:
    ollama = None

# Import AI providers for multi-provider support
import sys
from pathlib import Path
# Add parent directory to path to import imagedescriber package
sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from imagedescriber.ai_providers import (
        OllamaProvider,
        OpenAIProvider,
        ONNXProvider,
        CopilotProvider,
        HuggingFaceProvider
    )
    AI_PROVIDERS_AVAILABLE = True
except ImportError as e:
    AI_PROVIDERS_AVAILABLE = False
    print(f"Warning: AI providers not available: {e}")


class PromptEditorMainWindow(QMainWindow):
    """Main window for the prompt editor application"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Description Prompt Editor")
        self.setMinimumSize(900, 600)
        
        # Find the config file
        self.config_file = self.find_config_file()
        self.config_data = {}
        self.current_prompt_name = None
        self.modified = False
        
        # Setup UI
        self.init_ui()
        self.create_menu_bar()
        self.create_status_bar()
        
        # Load initial data
        self.load_config()
        self.update_window_title()
        
        # Remove auto-save timer - only save when user explicitly requests it
        # Auto-save was causing unwanted file modifications without user consent
        
    def update_window_title(self):
        """Update the window title to show current file"""
        file_name = self.config_file.name
        base_title = "Image Description Prompt Editor"
        if self.modified:
            self.setWindowTitle(f"{base_title} - {file_name} *")
        else:
            self.setWindowTitle(f"{base_title} - {file_name}")
        
    def find_config_file(self):
        """Find the image_describer_config.json file"""
        # Look in scripts directory relative to current location
        possible_paths = [
            Path("scripts/image_describer_config.json"),
            Path("../scripts/image_describer_config.json"),
            Path("./image_describer_config.json"),
        ]
        
        for path in possible_paths:
            if path.exists():
                return path.resolve()
        
        # If not found, default to scripts directory
        scripts_dir = Path("scripts")
        scripts_dir.mkdir(exist_ok=True)
        return scripts_dir / "image_describer_config.json"
    
    def init_ui(self):
        """Initialize the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel - Prompt list and controls
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - Prompt editor
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        # Set initial splitter sizes (30% left, 70% right)
        splitter.setSizes([300, 600])
        
        # Set proper tab order for accessibility
        self.set_tab_order()
        
    def set_tab_order(self):
        """Set the logical tab order for keyboard navigation"""
        # Tab order: List -> Name Edit -> Text Edit -> Buttons
        self.setTabOrder(self.prompt_list, self.prompt_name_edit)
        self.setTabOrder(self.prompt_name_edit, self.prompt_text_edit)
        self.setTabOrder(self.prompt_text_edit, self.add_prompt_btn)
        self.setTabOrder(self.add_prompt_btn, self.delete_prompt_btn)
        self.setTabOrder(self.delete_prompt_btn, self.duplicate_prompt_btn)
        self.setTabOrder(self.duplicate_prompt_btn, self.default_prompt_combo)
        self.setTabOrder(self.default_prompt_combo, self.provider_combo)
        self.setTabOrder(self.provider_combo, self.api_key_edit)
        self.setTabOrder(self.api_key_edit, self.default_model_combo)
        self.setTabOrder(self.default_model_combo, self.refresh_models_btn)
        self.setTabOrder(self.refresh_models_btn, self.save_btn)
        self.setTabOrder(self.save_btn, self.save_as_btn)
        self.setTabOrder(self.save_as_btn, self.reload_btn)
        
    def create_left_panel(self):
        """Create the left panel with prompt list and controls"""
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # Prompt list group
        list_group = QGroupBox("Available Prompts")
        list_layout = QVBoxLayout(list_group)
        
        self.prompt_list = QListWidget()
        self.prompt_list.setAccessibleName("Prompt List")
        self.prompt_list.setAccessibleDescription("List of available prompt styles. Select one to edit.")
        self.prompt_list.currentItemChanged.connect(self.on_prompt_selected)
        # Improve focus visibility
        self.prompt_list.setStyleSheet("""
            QListWidget:focus {
                border: 2px solid #0078d4;
                background-color: #f0f8ff;
            }
        """)
        list_layout.addWidget(self.prompt_list)
        
        # Prompt list buttons
        list_buttons_layout = QHBoxLayout()
        
        self.add_prompt_btn = QPushButton("Add New")
        self.add_prompt_btn.setAccessibleDescription("Add a new prompt style")
        self.add_prompt_btn.clicked.connect(self.add_new_prompt)
        list_buttons_layout.addWidget(self.add_prompt_btn)
        
        self.delete_prompt_btn = QPushButton("Delete")
        self.delete_prompt_btn.setAccessibleDescription("Delete the selected prompt style")
        self.delete_prompt_btn.clicked.connect(self.delete_prompt)
        self.delete_prompt_btn.setEnabled(False)
        list_buttons_layout.addWidget(self.delete_prompt_btn)
        
        self.duplicate_prompt_btn = QPushButton("Duplicate")
        self.duplicate_prompt_btn.setAccessibleDescription("Create a copy of the selected prompt")
        self.duplicate_prompt_btn.clicked.connect(self.duplicate_prompt)
        self.duplicate_prompt_btn.setEnabled(False)
        list_buttons_layout.addWidget(self.duplicate_prompt_btn)
        
        list_layout.addLayout(list_buttons_layout)
        left_layout.addWidget(list_group)
        
        # Default prompt group
        default_group = QGroupBox("Default Settings")
        default_layout = QVBoxLayout(default_group)
        
        default_form = QFormLayout()
        
        # Default prompt style
        self.default_prompt_combo = QComboBox()
        self.default_prompt_combo.setAccessibleDescription("Select which prompt style to use as default")
        self.default_prompt_combo.currentTextChanged.connect(self.on_default_changed)
        default_form.addRow("Default Style:", self.default_prompt_combo)
        
        # AI Provider selection
        provider_layout = QVBoxLayout()
        self.provider_combo = QComboBox()
        self.provider_combo.setAccessibleDescription("Select which AI provider to use as default")
        self.provider_combo.addItems(["ollama", "openai", "onnx", "copilot", "huggingface"])
        self.provider_combo.currentTextChanged.connect(self.on_provider_changed)
        provider_layout.addWidget(self.provider_combo)
        
        # Add info label
        provider_info = QLabel("(Can be overridden with --provider flag)")
        provider_info.setStyleSheet("color: gray; font-size: 9pt;")
        provider_layout.addWidget(provider_info)
        
        default_form.addRow("AI Provider:", provider_layout)
        
        # API Key field (for OpenAI and HuggingFace)
        self.api_key_layout = QHBoxLayout()
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText("Enter API key or leave empty to use environment variable")
        self.api_key_edit.setAccessibleDescription("API key for cloud providers (OpenAI, HuggingFace)")
        self.api_key_edit.textChanged.connect(self.on_default_changed)
        self.api_key_layout.addWidget(self.api_key_edit)
        
        self.show_api_key_btn = QPushButton("Show")
        self.show_api_key_btn.setMaximumWidth(60)
        self.show_api_key_btn.setCheckable(True)
        self.show_api_key_btn.clicked.connect(self.toggle_api_key_visibility)
        self.api_key_layout.addWidget(self.show_api_key_btn)
        
        self.api_key_widget = QWidget()
        self.api_key_widget.setLayout(self.api_key_layout)
        default_form.addRow("API Key:", self.api_key_widget)
        
        # Default model with refresh button
        model_layout = QHBoxLayout()
        self.default_model_combo = QComboBox()
        self.default_model_combo.setAccessibleDescription("Select which AI model to use as default")
        self.default_model_combo.currentTextChanged.connect(self.on_default_changed)
        model_layout.addWidget(self.default_model_combo)
        
        self.refresh_models_btn = QPushButton("Refresh")
        self.refresh_models_btn.setMaximumWidth(60)
        self.refresh_models_btn.setAccessibleDescription("Refresh available models from selected provider")
        self.refresh_models_btn.clicked.connect(self.populate_model_combo)
        model_layout.addWidget(self.refresh_models_btn)
        
        default_form.addRow("Default Model:", model_layout)
        
        default_layout.addLayout(default_form)
        
        left_layout.addWidget(default_group)
        
        # Action buttons
        action_group = QGroupBox("Actions")
        action_layout = QVBoxLayout(action_group)
        
        # Save buttons in horizontal layout
        save_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("Save")
        self.save_btn.setAccessibleDescription("Save changes to the current configuration file")
        self.save_btn.clicked.connect(self.save_config)
        self.save_btn.setEnabled(False)
        save_layout.addWidget(self.save_btn)
        
        self.save_as_btn = QPushButton("Save As...")
        self.save_as_btn.setAccessibleDescription("Save configuration to a new file")
        self.save_as_btn.clicked.connect(self.save_as_config)
        save_layout.addWidget(self.save_as_btn)
        
        action_layout.addLayout(save_layout)
        
        self.reload_btn = QPushButton("Reload from File")
        self.reload_btn.setAccessibleDescription("Discard changes and reload from configuration file")
        self.reload_btn.clicked.connect(self.reload_config)
        action_layout.addWidget(self.reload_btn)
        
        left_layout.addWidget(action_group)
        
        # Add stretch to push everything to top
        left_layout.addStretch()
        
        return left_widget
    
    def create_right_panel(self):
        """Create the right panel with prompt editor"""
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Prompt name editor
        name_group = QGroupBox("Prompt Name")
        name_layout = QVBoxLayout(name_group)
        
        self.prompt_name_edit = QLineEdit()
        self.prompt_name_edit.setAccessibleDescription("Edit the name/key for this prompt style")
        self.prompt_name_edit.textChanged.connect(self.on_prompt_name_changed)
        # Improve focus visibility
        self.prompt_name_edit.setStyleSheet("""
            QLineEdit:focus {
                border: 2px solid #0078d4;
                background-color: #f0f8ff;
            }
        """)
        name_layout.addWidget(self.prompt_name_edit)
        
        right_layout.addWidget(name_group)
        
        # Prompt text editor
        text_group = QGroupBox("Prompt Text")
        text_layout = QVBoxLayout(text_group)
        
        self.prompt_text_edit = QTextEdit()
        self.prompt_text_edit.setAccessibleDescription("Edit the prompt text that will be sent to the AI model")
        self.prompt_text_edit.setTabChangesFocus(True)  # Tab advances focus instead of inserting tabs
        self.prompt_text_edit.textChanged.connect(self.on_prompt_text_changed)
        # Improve focus visibility
        self.prompt_text_edit.setStyleSheet("""
            QTextEdit:focus {
                border: 2px solid #0078d4;
                background-color: #f0f8ff;
            }
        """)
        
        # Set a monospace font for better editing
        font = QFont("Consolas", 10)
        if not font.exactMatch():
            font = QFont("Courier New", 10)
        self.prompt_text_edit.setFont(font)
        
        text_layout.addWidget(self.prompt_text_edit)
        
        # Character count label
        self.char_count_label = QLabel("Characters: 0")
        self.char_count_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        text_layout.addWidget(self.char_count_label)
        
        right_layout.addWidget(text_group)
        
        return right_widget
    
    def create_menu_bar(self):
        """Create the menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        new_action = QAction("New Prompt", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.add_new_prompt)
        file_menu.addAction(new_action)
        
        file_menu.addSeparator()
        
        save_action = QAction("Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_config)
        file_menu.addAction(save_action)
        
        save_as_action = QAction("Save As...", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_as_config)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        open_action = QAction("Open...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_config)
        file_menu.addAction(open_action)
        
        reload_action = QAction("Reload", self)
        reload_action.setShortcut("F5")
        reload_action.triggered.connect(self.reload_config)
        file_menu.addAction(reload_action)
        
        file_menu.addSeparator()
        
        backup_action = QAction("Create Backup", self)
        backup_action.triggered.connect(self.create_backup)
        file_menu.addAction(backup_action)
        
        restore_action = QAction("Restore from Backup", self)
        restore_action.triggered.connect(self.restore_backup)
        file_menu.addAction(restore_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("Edit")
        
        duplicate_action = QAction("Duplicate Prompt", self)
        duplicate_action.setShortcut("Ctrl+D")
        duplicate_action.triggered.connect(self.duplicate_prompt)
        edit_menu.addAction(duplicate_action)
        
        delete_action = QAction("Delete Prompt", self)
        delete_action.setShortcut("Delete")
        delete_action.triggered.connect(self.delete_prompt)
        edit_menu.addAction(delete_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        tips_action = QAction("Prompt Writing Tips", self)
        tips_action.triggered.connect(self.show_tips)
        help_menu.addAction(tips_action)
    
    def create_status_bar(self):
        """Create the status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    def load_config(self):
        """Load the configuration file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config_data = json.load(f)
            else:
                # Create default config if file doesn't exist
                self.config_data = self.create_default_config()
                self.save_config()
            
            # Load provider and API key if present
            provider = self.config_data.get('default_provider', 'ollama')
            self.provider_combo.setCurrentText(provider)
            
            api_key = self.config_data.get('api_key', '')
            self.api_key_edit.setText(api_key)
            
            # Update API key field visibility
            self.on_provider_changed(provider)
            
            self.populate_prompt_list()
            self.populate_default_combo()
            self.populate_model_combo()
            self.modified = False
            self.update_ui_state()
            self.status_bar.showMessage(f"Loaded configuration from {self.config_file.name}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load configuration file:\n{e}")
            self.config_data = self.create_default_config()
    
    def create_default_config(self):
        """Create a default configuration with basic prompts"""
        return {
            "default_prompt_style": "detailed",
            "default_provider": "ollama",  # Optional - scripts use --provider CLI argument by default
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
        self.prompt_list.clear()
        prompt_variations = self.config_data.get('prompt_variations', {})
        
        for name in sorted(prompt_variations.keys()):
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.prompt_list.addItem(item)
    
    def populate_default_combo(self):
        """Populate the default prompt combo box"""
        self.default_prompt_combo.clear()
        prompt_variations = self.config_data.get('prompt_variations', {})
        self.default_prompt_combo.addItems(sorted(prompt_variations.keys()))
        
        # Set current default with case-insensitive matching
        default_style = self.config_data.get('default_prompt_style', '')
        if default_style:
            # Create case-insensitive lookup
            lower_variations = {k.lower(): k for k in prompt_variations.keys()}
            if default_style.lower() in lower_variations:
                actual_key = lower_variations[default_style.lower()]
                self.default_prompt_combo.setCurrentText(actual_key)
    
    def populate_model_combo(self):
        """Populate the default model combo box with models from the selected provider"""
        self.default_model_combo.clear()
        
        provider = self.provider_combo.currentText()
        
        try:
            # Get models based on selected provider
            if provider == "ollama":
                # Use legacy Ollama module if available
                if ollama is None:
                    raise ImportError("Ollama module not available")
                models_response = ollama.list()
                available_models = [model.model for model in models_response['models']]
                
            elif provider == "openai":
                # OpenAI models - return predefined list since API doesn't have discovery
                available_models = [
                    "gpt-4o",
                    "gpt-4o-mini",
                    "gpt-4-turbo",
                    "gpt-4-vision-preview",
                    "gpt-4"
                ]
                
            elif provider == "onnx":
                # ONNX models - check for local models
                if AI_PROVIDERS_AVAILABLE:
                    try:
                        onnx_provider = ONNXProvider()
                        available_models = onnx_provider.get_available_models()
                    except Exception as e:
                        print(f"Error getting ONNX models: {e}")
                        available_models = ["florence-2-base", "florence-2-large"]  # Default fallback
                else:
                    available_models = ["florence-2-base", "florence-2-large"]
                    
            elif provider == "copilot":
                # Copilot - uses GitHub Copilot models
                available_models = ["gpt-4o", "claude-3.5-sonnet", "o1-preview", "o1-mini"]
                
            elif provider == "huggingface":
                # HuggingFace - return common vision models
                available_models = [
                    "microsoft/Florence-2-large",
                    "microsoft/Florence-2-base",
                    "Salesforce/blip-image-captioning-large",
                    "Salesforce/blip2-opt-2.7b"
                ]
            else:
                available_models = []
            
            if not available_models:
                self.default_model_combo.addItem("No models available", None)
                self.default_model_combo.setEnabled(False)
                return
            
            self.default_model_combo.setEnabled(True)
            
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
                
                self.default_model_combo.addItem(display_text, model_name)
            
            # Set current default
            default_model = self.config_data.get('default_model', '')
            if default_model:
                # Find the index of the model
                for i in range(self.default_model_combo.count()):
                    if self.default_model_combo.itemData(i) == default_model:
                        self.default_model_combo.setCurrentIndex(i)
                        break
                        
        except Exception as e:
            # Fallback on error
            error_msg = f"{provider.title()} not available: {e}"
            print(f"Warning: {error_msg}")
            self.default_model_combo.addItem(error_msg, None)
            self.default_model_combo.setEnabled(False)
    
    def on_prompt_selected(self, current, previous):
        """Handle prompt selection change"""
        if current:
            prompt_name = current.data(Qt.ItemDataRole.UserRole)
            self.load_prompt(prompt_name)
            self.delete_prompt_btn.setEnabled(True)
            self.duplicate_prompt_btn.setEnabled(True)
        else:
            self.clear_editor()
            self.delete_prompt_btn.setEnabled(False)
            self.duplicate_prompt_btn.setEnabled(False)
    
    def load_prompt(self, prompt_name):
        """Load a prompt into the editor with case-insensitive lookup"""
        self.current_prompt_name = prompt_name
        prompt_variations = self.config_data.get('prompt_variations', {})
        
        # Case-insensitive lookup
        lower_variations = {k.lower(): v for k, v in prompt_variations.items()}
        prompt_text = lower_variations.get(prompt_name.lower(), '')
        
        # Temporarily disconnect signals to avoid triggering changes
        self.prompt_name_edit.blockSignals(True)
        self.prompt_text_edit.blockSignals(True)
        
        self.prompt_name_edit.setText(prompt_name)
        self.prompt_text_edit.setPlainText(prompt_text)
        
        # Reconnect signals
        self.prompt_name_edit.blockSignals(False)
        self.prompt_text_edit.blockSignals(False)
        
        self.update_char_count()
    
    def clear_editor(self):
        """Clear the editor"""
        self.current_prompt_name = None
        self.prompt_name_edit.clear()
        self.prompt_text_edit.clear()
        self.char_count_label.setText("Characters: 0")
    
    def on_prompt_name_changed(self):
        """Handle prompt name change"""
        if self.current_prompt_name:
            self.mark_modified()
    
    def on_prompt_text_changed(self):
        """Handle prompt text change"""
        if self.current_prompt_name:
            self.mark_modified()
            self.update_char_count()
    
    def on_default_changed(self):
        """Handle default prompt change"""
        self.mark_modified()
    
    def on_provider_changed(self, provider):
        """Handle AI provider change"""
        # Show/hide API key field based on provider
        needs_api_key = provider in ["openai", "huggingface"]
        self.api_key_widget.setVisible(needs_api_key)
        
        # Refresh the model list for the new provider
        self.populate_model_combo()
        
        # Mark as modified
        self.mark_modified()
    
    def toggle_api_key_visibility(self):
        """Toggle API key visibility between password and plain text"""
        if self.show_api_key_btn.isChecked():
            self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_api_key_btn.setText("Hide")
        else:
            self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_api_key_btn.setText("Show")
    
    def update_char_count(self):
        """Update the character count label"""
        count = len(self.prompt_text_edit.toPlainText())
        self.char_count_label.setText(f"Characters: {count}")
    
    def mark_modified(self):
        """Mark the configuration as modified"""
        if not self.modified:
            self.modified = True
            self.update_window_title()
            self.save_btn.setEnabled(True)
    
    def update_ui_state(self):
        """Update UI state based on current data"""
        self.update_window_title()
        if self.modified:
            self.save_btn.setEnabled(True)
        else:
            self.save_btn.setEnabled(False)
    
    def add_new_prompt(self):
        """Add a new prompt"""
        name, ok = QInputDialog.getText(self, "New Prompt", "Enter prompt name:")
        if ok and name.strip():
            name = name.strip()
            
            # Check if name already exists
            if name in self.config_data.get('prompt_variations', {}):
                QMessageBox.warning(self, "Warning", f"Prompt '{name}' already exists.")
                return
            
            # Add new prompt with default text
            if 'prompt_variations' not in self.config_data:
                self.config_data['prompt_variations'] = {}
            
            self.config_data['prompt_variations'][name] = "Describe this image focusing on [add your specific requirements here]."
            
            self.populate_prompt_list()
            self.populate_default_combo()
            self.populate_model_combo()
            
            # Select the new prompt
            for i in range(self.prompt_list.count()):
                item = self.prompt_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == name:
                    self.prompt_list.setCurrentItem(item)
                    # Trigger the selection to load the prompt text
                    self.on_prompt_selected(item, None)
                    # Focus the text editor so user can immediately start typing
                    self.prompt_text_edit.setFocus()
                    break
            
            self.mark_modified()
    
    def duplicate_prompt(self):
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
        for i in range(self.prompt_list.count()):
            item = self.prompt_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == new_name:
                self.prompt_list.setCurrentItem(item)
                break
        
        self.mark_modified()
    
    def delete_prompt(self):
        """Delete the selected prompt"""
        if not self.current_prompt_name:
            return
        
        reply = QMessageBox.question(self, "Delete Prompt", 
                                   f"Are you sure you want to delete the prompt '{self.current_prompt_name}'?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
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
    
    def save_config(self):
        """Save the configuration to file"""
        try:
            # Update the current prompt if one is being edited
            if self.current_prompt_name and self.prompt_name_edit.text().strip():
                new_name = self.prompt_name_edit.text().strip()
                new_text = self.prompt_text_edit.toPlainText()
                
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
            self.config_data['default_prompt_style'] = self.default_prompt_combo.currentText()
            
            # Update default provider
            self.config_data['default_provider'] = self.provider_combo.currentText()
            
            # Update API key (only if not empty)
            api_key = self.api_key_edit.text().strip()
            if api_key:
                self.config_data['api_key'] = api_key
            elif 'api_key' in self.config_data:
                # Remove api_key if it's now empty
                del self.config_data['api_key']
            
            # Update default model
            if self.default_model_combo.currentData():
                self.config_data['default_model'] = self.default_model_combo.currentData()
            
            # Create backup before saving
            if self.config_file.exists():
                backup_path = self.config_file.with_suffix('.bak')
                shutil.copy2(self.config_file, backup_path)
            
            # Save to file
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=2, ensure_ascii=False)
            
            self.modified = False
            self.update_ui_state()
            
            # Block signals during UI updates to prevent marking as modified
            self.prompt_list.blockSignals(True)
            self.default_prompt_combo.blockSignals(True)
            self.default_model_combo.blockSignals(True)
            
            self.populate_prompt_list()
            self.populate_default_combo()
            self.populate_model_combo()
            
            # Re-select current prompt
            if self.current_prompt_name:
                for i in range(self.prompt_list.count()):
                    item = self.prompt_list.item(i)
                    if item.data(Qt.ItemDataRole.UserRole) == self.current_prompt_name:
                        self.prompt_list.setCurrentItem(item)
                        break
            
            # Restore signals
            self.prompt_list.blockSignals(False)
            self.default_prompt_combo.blockSignals(False)
            self.default_model_combo.blockSignals(False)
            
            self.status_bar.showMessage("Configuration saved successfully", 3000)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save configuration:\n{e}")
    
    def save_as_config(self):
        """Save the configuration to a new file"""
        try:
            # Get file path from user
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Configuration As",
                str(self.config_file.parent / "custom_prompts.json"),
                "JSON files (*.json);;All files (*.*)"
            )
            
            if not file_path:
                return
            
            # Update the current prompt if one is being edited
            if self.current_prompt_name and self.prompt_name_edit.text().strip():
                new_name = self.prompt_name_edit.text().strip()
                new_text = self.prompt_text_edit.toPlainText()
                
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
            
            # Update default prompt style and model
            self.config_data['default_prompt_style'] = self.default_prompt_combo.currentText()
            if self.default_model_combo.currentData():
                self.config_data['default_model'] = self.default_model_combo.currentData()
            
            # Save to the new file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=2, ensure_ascii=False)
            
            # Update current file reference
            self.config_file = Path(file_path)
            self.modified = False
            self.update_ui_state()
            self.update_window_title()
            
            self.status_bar.showMessage(f"Configuration saved as {file_path}", 3000)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save configuration:\n{e}")
    
    def open_config(self):
        """Open a different configuration file"""
        if self.modified:
            reply = QMessageBox.question(self, "Open Configuration",
                                       "You have unsaved changes. Are you sure you want to open a different file?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        try:
            # Get file path from user
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Open Configuration",
                str(self.config_file.parent),
                "JSON files (*.json);;All files (*.*)"
            )
            
            if not file_path:
                return
            
            # Update current file reference
            self.config_file = Path(file_path)
            
            # Load the new configuration
            self.load_config()
            self.clear_editor()
            self.update_window_title()
            
            self.status_bar.showMessage(f"Opened {file_path}", 3000)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open configuration:\n{e}")

    def reload_config(self):
        """Reload configuration from file"""
        if self.modified:
            reply = QMessageBox.question(self, "Reload Configuration",
                                       "You have unsaved changes. Are you sure you want to reload?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        self.load_config()
        self.clear_editor()
    
    def create_backup(self):
        """Create a backup of the configuration file"""
        if not self.config_file.exists():
            QMessageBox.warning(self, "Warning", "Configuration file does not exist.")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"image_describer_config_backup_{timestamp}.json"
        backup_path, _ = QFileDialog.getSaveFileName(self, "Save Backup", backup_name, "JSON files (*.json)")
        
        if backup_path:
            try:
                shutil.copy2(self.config_file, backup_path)
                QMessageBox.information(self, "Success", f"Backup created: {backup_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create backup:\n{e}")
    
    def restore_backup(self):
        """Restore from a backup file"""
        backup_path, _ = QFileDialog.getOpenFileName(self, "Restore from Backup", "", "JSON files (*.json)")
        
        if backup_path:
            reply = QMessageBox.question(self, "Restore Backup",
                                       "This will replace the current configuration. Continue?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    shutil.copy2(backup_path, self.config_file)
                    self.load_config()
                    self.clear_editor()
                    QMessageBox.information(self, "Success", "Configuration restored from backup.")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to restore backup:\n{e}")
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(self, "About Prompt Editor",
                         "Image Description Prompt Editor\n\n"
                         "A user-friendly tool for editing AI prompt variations\n"
                         "used by the Image Description Toolkit.\n\n"
                         "Features:\n"
                         "• Visual prompt editing\n"
                         "• Add, edit, delete prompts\n"
                         "• Set default prompt style\n"
                         "• Backup and restore\n"
                         "• Real-time preview\n\n"
                         "Built with PyQt6")
    
    def show_tips(self):
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
        
        QMessageBox.information(self, "Prompt Writing Tips", tips)
    
    def closeEvent(self, event):
        """Handle application close"""
        if self.modified:
            reply = QMessageBox.question(self, "Unsaved Changes",
                                       "You have unsaved changes. Save before closing?",
                                       QMessageBox.StandardButton.Save | 
                                       QMessageBox.StandardButton.Discard | 
                                       QMessageBox.StandardButton.Cancel)
            
            if reply == QMessageBox.StandardButton.Save:
                self.save_config()
                event.accept()
            elif reply == QMessageBox.StandardButton.Discard:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("Prompt Editor")
    app.setApplicationVersion("1.0")
    
    # Set application properties for accessibility
    app.setOrganizationName("Image Description Toolkit")
    app.setOrganizationDomain("github.com/kellylford/Image-Description-Toolkit")
    
    window = PromptEditorMainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
