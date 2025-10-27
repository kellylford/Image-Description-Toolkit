"""
IDT Configure - Configuration Manager for Image Description Toolkit

A Qt6 GUI application for managing configuration files:
- image_describer_config.json
- video_frame_extractor_config.json
- workflow_config.json

Features:
- Menu-based categorization for accessibility
- Settings list with arrow navigation
- Change button for adjustments
- Screen reader readable explanations
- Save/Load functionality
- Professional, accessible interface
"""

import sys
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QTextEdit, QPushButton, QLabel, QMessageBox,
    QFileDialog, QDialog, QFormLayout, QLineEdit, QSpinBox,
    QDoubleSpinBox, QComboBox, QCheckBox, QDialogButtonBox,
    QGroupBox, QListWidgetItem, QMenu
)
from PyQt6.QtCore import Qt, QSettings, pyqtSignal
from PyQt6.QtGui import QAction, QFont, QKeySequence


class SettingEditDialog(QDialog):
    """Dialog for editing a single setting value"""
    
    def __init__(self, setting_name: str, current_value: Any, 
                 setting_info: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.setting_name = setting_name
        self.current_value = current_value
        self.setting_info = setting_info
        self.new_value = None
        
        self.setWindowTitle(f"Edit: {setting_name}")
        self.setup_ui()
        
    def setup_ui(self):
        """Create the dialog UI"""
        layout = QFormLayout(self)
        
        # Add description
        if "description" in self.setting_info:
            desc_label = QLabel(self.setting_info["description"])
            desc_label.setWordWrap(True)
            layout.addRow("Description:", desc_label)
        
        # Create appropriate editor based on setting type
        setting_type = self.setting_info.get("type", "string")
        
        if setting_type == "bool":
            self.editor = QCheckBox()
            self.editor.setChecked(bool(self.current_value))
            layout.addRow("Value:", self.editor)
            
        elif setting_type == "int":
            self.editor = QSpinBox()
            if "range" in self.setting_info:
                self.editor.setRange(self.setting_info["range"][0], 
                                   self.setting_info["range"][1])
            else:
                self.editor.setRange(-999999, 999999)
            self.editor.setValue(int(self.current_value or 0))
            layout.addRow("Value:", self.editor)
            
        elif setting_type == "float":
            self.editor = QDoubleSpinBox()
            if "range" in self.setting_info:
                self.editor.setRange(self.setting_info["range"][0],
                                   self.setting_info["range"][1])
            else:
                self.editor.setRange(-999999.0, 999999.0)
            self.editor.setDecimals(2)
            self.editor.setSingleStep(0.1)
            self.editor.setValue(float(self.current_value or 0.0))
            layout.addRow("Value:", self.editor)
            
        elif setting_type == "choice":
            self.editor = QComboBox()
            choices = self.setting_info.get("choices", [])
            self.editor.addItems(choices)
            if self.current_value in choices:
                self.editor.setCurrentText(str(self.current_value))
            layout.addRow("Value:", self.editor)
            
        else:  # string or other
            self.editor = QLineEdit()
            self.editor.setText(str(self.current_value or ""))
            layout.addRow("Value:", self.editor)
        
        # Add range/limits info if available
        if "range" in self.setting_info:
            range_label = QLabel(f"Range: {self.setting_info['range'][0]} to {self.setting_info['range'][1]}")
            layout.addRow("", range_label)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        
    def accept(self):
        """Save the new value"""
        setting_type = self.setting_info.get("type", "string")
        
        if setting_type == "bool":
            self.new_value = self.editor.isChecked()
        elif setting_type == "int":
            self.new_value = self.editor.value()
        elif setting_type == "float":
            self.new_value = self.editor.value()
        elif setting_type == "choice":
            self.new_value = self.editor.currentText()
        else:
            self.new_value = self.editor.text()
        
        super().accept()


class IDTConfigureApp(QMainWindow):
    """Main application window for IDT Configuration Manager"""
    
    def __init__(self):
        super().__init__()
        
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
        self.setWindowTitle("IDT Configure - Configuration Manager")
        self.setMinimumSize(900, 600)
        
        # Create UI
        self.setup_ui()
        self.setup_menus()
        
        # Load window state
        self.load_window_state()
        
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
    
    def setup_ui(self):
        """Create the main user interface"""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Header label
        header = QLabel("IDT Configuration Manager")
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header.setFont(header_font)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(header)
        
        # Category label
        self.category_label = QLabel("Select a category from the Settings menu")
        category_font = QFont()
        category_font.setPointSize(10)
        self.category_label.setFont(category_font)
        main_layout.addWidget(self.category_label)
        
        # Content layout (settings list + explanation)
        content_layout = QHBoxLayout()
        
        # Left side: Settings list
        left_panel = QVBoxLayout()
        
        settings_label = QLabel("Settings:")
        left_panel.addWidget(settings_label)
        
        self.settings_list = QListWidget()
        self.settings_list.setAccessibleName("Settings list")
        self.settings_list.setAccessibleDescription("List of configuration settings. Use arrow keys to navigate.")
        self.settings_list.currentItemChanged.connect(self.on_setting_selected)
        left_panel.addWidget(self.settings_list)
        
        # Change button
        self.change_button = QPushButton("Change Setting")
        self.change_button.setEnabled(False)
        self.change_button.clicked.connect(self.change_setting)
        self.change_button.setAccessibleDescription("Change the selected setting value")
        left_panel.addWidget(self.change_button)
        
        content_layout.addLayout(left_panel, 1)
        
        # Right side: Explanation panel
        right_panel = QVBoxLayout()
        
        explanation_label = QLabel("Explanation:")
        right_panel.addWidget(explanation_label)
        
        self.explanation_text = QTextEdit()
        self.explanation_text.setReadOnly(True)
        self.explanation_text.setAccessibleName("Setting explanation")
        self.explanation_text.setAccessibleDescription("Detailed explanation of the selected setting")
        right_panel.addWidget(self.explanation_text)
        
        content_layout.addLayout(right_panel, 1)
        
        main_layout.addLayout(content_layout)
        
        # Status bar
        self.statusBar().showMessage("Ready")
    
    def setup_menus(self):
        """Create the menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        reload_action = QAction("&Reload Configurations", self)
        reload_action.setShortcut(QKeySequence("Ctrl+R"))
        reload_action.triggered.connect(self.reload_configs)
        file_menu.addAction(reload_action)
        
        save_action = QAction("&Save All", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_all_configs)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        export_action = QAction("&Export Configuration...", self)
        export_action.triggered.connect(self.export_config)
        file_menu.addAction(export_action)
        
        import_action = QAction("&Import Configuration...", self)
        import_action.triggered.connect(self.import_config)
        file_menu.addAction(import_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Settings menu (categories)
        settings_menu = menubar.addMenu("&Settings")
        
        for category in self.settings_metadata.keys():
            action = QAction(category, self)
            action.triggered.connect(lambda checked, cat=category: self.load_category(cat))
            settings_menu.addAction(action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        help_action = QAction("&Help", self)
        help_action.setShortcut(QKeySequence.StandardKey.HelpContents)
        help_action.triggered.connect(self.show_help)
        help_menu.addAction(help_action)
    
    def load_all_configs(self):
        """Load all configuration files"""
        for name, path in self.config_files.items():
            try:
                if path.exists():
                    with open(path, 'r', encoding='utf-8') as f:
                        self.configs[name] = json.load(f)
                else:
                    self.configs[name] = {}
                    self.statusBar().showMessage(f"Warning: {path} not found", 5000)
            except Exception as e:
                self.configs[name] = {}
                QMessageBox.warning(self, "Load Error", 
                                  f"Error loading {path}:\n{str(e)}")
    
    def reload_configs(self):
        """Reload all configurations from disk"""
        self.load_all_configs()
        if self.current_category:
            self.load_category(self.current_category)
        self.statusBar().showMessage("Configurations reloaded", 3000)
    
    def save_all_configs(self):
        """Save all configuration files"""
        try:
            for name, config in self.configs.items():
                path = self.config_files[name]
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2)
            
            self.statusBar().showMessage("All configurations saved successfully", 3000)
            QMessageBox.information(self, "Saved", "All configurations saved successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", 
                               f"Error saving configurations:\n{str(e)}")
    
    def load_category(self, category: str):
        """Load settings for a specific category"""
        self.current_category = category
        self.category_label.setText(f"Category: {category}")
        
        # Clear current list
        self.settings_list.clear()
        self.explanation_text.clear()
        
        # Load settings for this category
        settings = self.settings_metadata.get(category, {})
        
        for setting_name, setting_info in settings.items():
            # Get current value
            current_value = self.get_setting_value(setting_info)
            
            # Format display text: "Setting Name: current_value"
            display_text = f"{setting_name}: {current_value}"
            
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, setting_name)
            self.settings_list.addItem(item)
        
        # Select first item if available
        if self.settings_list.count() > 0:
            self.settings_list.setCurrentRow(0)
        
        self.statusBar().showMessage(f"Loaded {category}", 3000)
    
    def on_setting_selected(self, current: QListWidgetItem, previous: QListWidgetItem):
        """Handle setting selection"""
        if not current:
            self.change_button.setEnabled(False)
            self.explanation_text.clear()
            return
        
        setting_name = current.data(Qt.ItemDataRole.UserRole)
        setting_info = self.settings_metadata[self.current_category][setting_name]
        
        # Show explanation with range/choices info
        description = setting_info.get("description", "No description available")
        
        # Add range info if available
        if "range" in setting_info:
            description += f"\n\nRange: {setting_info['range'][0]} to {setting_info['range'][1]}"
        
        # Add choices if available
        if "choices" in setting_info:
            description += f"\n\nOptions: {', '.join(setting_info['choices'])}"
        
        self.explanation_text.setText(description)
        
        self.change_button.setEnabled(True)
    
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
    
    def change_setting(self):
        """Open dialog to change the selected setting"""
        current_item = self.settings_list.currentItem()
        if not current_item:
            return
        
        setting_name = current_item.data(Qt.ItemDataRole.UserRole)
        setting_info = self.settings_metadata[self.current_category][setting_name]
        
        current_value = self.get_setting_value(setting_info)
        
        # Open edit dialog
        dialog = SettingEditDialog(setting_name, current_value, setting_info, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Update the value
            self.set_setting_value(setting_info, dialog.new_value)
            
            # Update the list item text to show new value
            display_text = f"{setting_name}: {dialog.new_value}"
            current_item.setText(display_text)
            
            # Refresh the display
            self.on_setting_selected(current_item, None)
            
            self.statusBar().showMessage(f"Changed {setting_name} to {dialog.new_value}", 3000)
    
    def export_config(self):
        """Export current configuration to a file"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Configuration", "", "JSON Files (*.json)"
        )
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(self.configs, f, indent=2)
                QMessageBox.information(self, "Exported", 
                                      f"Configuration exported to:\n{filename}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", str(e))
    
    def import_config(self):
        """Import configuration from a file"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Import Configuration", "", "JSON Files (*.json)"
        )
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    imported = json.load(f)
                
                # Merge or replace?
                reply = QMessageBox.question(
                    self, "Import Mode",
                    "Replace current configuration completely?\n\n"
                    "Yes = Replace all\nNo = Merge with current",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | 
                    QMessageBox.StandardButton.Cancel
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    self.configs = imported
                elif reply == QMessageBox.StandardButton.No:
                    # Merge
                    for key, value in imported.items():
                        if key in self.configs:
                            self.configs[key].update(value)
                        else:
                            self.configs[key] = value
                
                # Reload display
                if self.current_category:
                    self.load_category(self.current_category)
                
                QMessageBox.information(self, "Imported", "Configuration imported successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Import Error", str(e))
    
    def show_about(self):
        """Show about dialog"""
        about_text = """<h2>IDT Configure</h2>
        <p>Configuration Manager for Image Description Toolkit</p>
        <p><b>Version:</b> 1.0.0</p>
        <p><b>Features:</b></p>
        <ul>
        <li>Manage AI model settings</li>
        <li>Configure video extraction options</li>
        <li>Adjust workflow behavior</li>
        <li>Set processing preferences</li>
        <li>Full keyboard accessibility</li>
        </ul>
        <p><b>Keyboard Shortcuts:</b></p>
        <ul>
        <li>Ctrl+R: Reload configurations</li>
        <li>Ctrl+S: Save all</li>
        <li>F1: Help</li>
        </ul>
        """
        QMessageBox.about(self, "About IDT Configure", about_text)
    
    def show_help(self):
        """Show help dialog"""
        help_text = """<h2>IDT Configure Help</h2>
        
        <h3>Getting Started</h3>
        <p>1. Select a category from the Settings menu</p>
        <p>2. Navigate through settings using arrow keys</p>
        <p>3. Press "Change Setting" or Enter to edit</p>
        <p>4. Use File → Save All to save changes</p>
        
        <h3>Categories</h3>
        <p><b>AI Model Settings:</b> Temperature, tokens, and other AI parameters</p>
        <p><b>Prompt Styles:</b> Choose default description style</p>
        <p><b>Video Extraction:</b> Configure frame extraction from videos</p>
        <p><b>Processing Options:</b> Memory, delays, and optimization</p>
        <p><b>Workflow Settings:</b> Enable/disable workflow steps</p>
        <p><b>Output Format:</b> Control what's included in output</p>
        
        <h3>Tips</h3>
        <ul>
        <li>Hover over settings for more information</li>
        <li>Changes are not saved until you use File → Save All</li>
        <li>You can reload from disk with Ctrl+R</li>
        <li>Export/Import to backup or share configurations</li>
        </ul>
        
        <h3>Accessibility</h3>
        <p>This application is fully keyboard accessible:</p>
        <ul>
        <li>Use Tab to move between controls</li>
        <li>Arrow keys to navigate lists</li>
        <li>Enter to activate buttons</li>
        <li>Alt+letter to access menus</li>
        </ul>
        """
        msg = QMessageBox(self)
        msg.setWindowTitle("Help")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(help_text)
        msg.exec()
    
    def load_window_state(self):
        """Load saved window state"""
        settings = QSettings("IDT", "IDTConfigure")
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
    
    def save_window_state(self):
        """Save window state"""
        settings = QSettings("IDT", "IDTConfigure")
        settings.setValue("geometry", self.saveGeometry())
    
    def closeEvent(self, event):
        """Handle window close"""
        # Check for unsaved changes (simplified - could track modifications)
        self.save_window_state()
        event.accept()


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("IDT Configure")
    app.setOrganizationName("IDT")
    app.setOrganizationDomain("github.com/kellylford/Image-Description-Toolkit")
    
    window = IDTConfigureApp()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
