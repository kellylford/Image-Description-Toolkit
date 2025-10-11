# Qt6 Image Description Viewer
# This app allows users to browse image descriptions from a completed workflow run.
# Accessibility best practices are followed throughout.

import sys
import os
import json
import subprocess
import re
import time
from pathlib import Path

def get_scripts_directory():
    """Get the scripts directory path, handling both development and bundled scenarios."""
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller executable
        print(f"Running as bundled executable from: {sys.executable}")
        
        # First try: Scripts directory should be bundled alongside the executable
        base_dir = Path(sys.executable).parent
        scripts_dir = base_dir / "scripts"
        print(f"Checking for scripts at: {scripts_dir}")
        
        # If scripts not found next to executable, try in the bundled resources
        if not scripts_dir.exists():
            print("Scripts not found next to executable, checking bundled resources...")
            # PyInstaller stores bundled data in sys._MEIPASS
            if hasattr(sys, '_MEIPASS'):
                scripts_dir = Path(sys._MEIPASS) / "scripts"
                print(f"Checking bundled scripts at: {scripts_dir}")
        
        if scripts_dir.exists():
            print(f"Found scripts directory at: {scripts_dir}")
        else:
            print(f"WARNING: Scripts directory not found! Tried: {base_dir / 'scripts'}")
            if hasattr(sys, '_MEIPASS'):
                print(f"Also tried: {Path(sys._MEIPASS) / 'scripts'}")
        
        return scripts_dir
    else:
        # Running in development mode
        scripts_dir = Path(__file__).parent.parent / "scripts"
        print(f"Development mode - scripts directory: {scripts_dir}")
        return scripts_dir

try:
    import ollama
except ImportError:
    ollama = None
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QLabel, QPushButton, 
    QFileDialog, QMessageBox, QAbstractItemView, QTextEdit, QDialog, QComboBox, QDialogButtonBox, QProgressBar, QStatusBar, QPlainTextEdit, QCheckBox
)
from PyQt6.QtGui import QClipboard, QGuiApplication, QPixmap, QImage
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QFileSystemWatcher

class DescriptionFileParser:
    """Parser for live description text files"""
    
    def __init__(self):
        self.entries = []
        self.last_modified = 0
        self.current_progress = {"current": 0, "total": 0}
    
    def parse_file(self, file_path: Path) -> list:
        """Parse the descriptions file and return list of entries"""
        entries = []
        
        if not file_path.exists():
            return entries
        
        try:
            # Check if file has been modified
            stat = file_path.stat()
            if stat.st_mtime <= self.last_modified:
                return self.entries
            
            self.last_modified = stat.st_mtime
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split by separator lines
            separator = '-' * 80
            sections = content.split(separator)
            
            # Skip header section (first section before any separator)
            for section in sections[1:]:
                if not section.strip():
                    continue
                
                entry = self._parse_entry(section.strip())
                if entry:
                    entries.append(entry)
            
            self.entries = entries
            self._update_progress_from_entries(entries)
            return entries
            
        except Exception as e:
            print(f"Error parsing descriptions file: {e}")
            return self.entries
    
    def _parse_entry(self, section: str) -> dict:
        """Parse a single entry section"""
        lines = section.split('\n')
        entry = {
            'file_path': '',
            'relative_path': '',
            'description': '',
            'model': '',
            'prompt_style': '',
            'metadata': {}
        }
        
        description_started = False
        description_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                if description_started:
                    description_lines.append('')
                continue
            
            if line.startswith('File: '):
                entry['relative_path'] = line[6:].strip()
            elif line.startswith('Path: '):
                entry['file_path'] = line[6:].strip()
            elif line.startswith('Model: '):
                entry['model'] = line[7:].strip()
            elif line.startswith('Prompt Style: '):
                entry['prompt_style'] = line[14:].strip()
            elif line.startswith('Description: '):
                description_started = True
                description_lines.append(line[13:].strip())
            elif line.startswith('Timestamp: '):
                entry['metadata']['timestamp'] = line[11:].strip()
            elif description_started and not line.startswith(('Timestamp:', 'File:', 'Path:', 'Model:', 'Prompt Style:')):
                description_lines.append(line)
        
        if description_lines:
            entry['description'] = '\n'.join(description_lines).strip()
        
        return entry if entry['description'] else None
    
    def _update_progress_from_entries(self, entries):
        """Update progress tracking from parsed entries"""
        self.current_progress["current"] = len(entries)
        # Try to extract total from log files if available
    
    def get_progress(self) -> dict:
        """Get current progress information"""
        return self.current_progress.copy()


class WorkflowMonitor(QThread):
    """Monitor workflow progress from log files"""
    progress_updated = pyqtSignal(dict)  # Emits progress info
    
    def __init__(self, workflow_dir: Path):
        super().__init__()
        self.workflow_dir = workflow_dir
        self.running = False
        self.log_file = None
        self._find_log_file()
    
    def _find_log_file(self):
        """Find the image describer log file"""
        logs_dir = self.workflow_dir / "logs"
        if not logs_dir.exists():
            return
        
        # Find the most recent image_describer log
        log_files = list(logs_dir.glob("image_describer_*.log"))
        if log_files:
            self.log_file = max(log_files, key=lambda f: f.stat().st_mtime)
    
    def run(self):
        """Monitor log file for progress updates"""
        self.running = True
        
        while self.running:
            if self.log_file and self.log_file.exists():
                try:
                    progress = self._parse_progress()
                    if progress:
                        self.progress_updated.emit(progress)
                except Exception as e:
                    print(f"Error monitoring progress: {e}")
            
            self.msleep(2000)  # Check every 2 seconds
    
    def _parse_progress(self) -> dict:
        """Parse progress from log file"""
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Look for "Describing image X of Y" patterns
            pattern = r'Describing image (\d+) of (\d+):'
            matches = list(re.finditer(pattern, content))
            
            if matches:
                last_match = matches[-1]
                current = int(last_match.group(1))
                total = int(last_match.group(2))
                
                # Check if workflow is still active
                lines = content.split('\n')
                last_lines = lines[-10:]  # Check last 10 lines
                recent_timestamp = None
                
                for line in reversed(last_lines):
                    if ' - INFO - ' in line and 'Describing image' in line:
                        # Extract timestamp from log line
                        timestamp_match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                        if timestamp_match:
                            timestamp_str = timestamp_match.group(1)
                            try:
                                from datetime import datetime
                                recent_timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                                break
                            except:
                                pass
                
                # Determine if workflow is still active (recent activity within 5 minutes)
                is_active = False
                if recent_timestamp:
                    from datetime import datetime, timedelta
                    now = datetime.now()
                    is_active = (now - recent_timestamp) < timedelta(minutes=5)
                
                return {
                    'current': current,
                    'total': total,
                    'active': is_active,
                    'last_update': recent_timestamp.isoformat() if recent_timestamp else None
                }
            
            return None
            
        except Exception as e:
            print(f"Error parsing progress: {e}")
            return None
    
    def stop(self):
        """Stop monitoring"""
        self.running = False


class RedescribeWorker(QThread):
    """Worker thread for image redescription to avoid blocking the UI"""
    finished = pyqtSignal(str)  # Emits the new description
    error = pyqtSignal(str)     # Emits error message

    def __init__(self, image_path, model, prompt_style, custom_prompt=None):
        super().__init__()
        self.image_path = image_path
        self.model = model
        self.prompt_style = prompt_style
        self.custom_prompt = custom_prompt

    def run(self):
        try:
            # Import the ImageDescriber class
            scripts_dir = get_scripts_directory()
            sys.path.insert(0, str(scripts_dir))
            
            # Change to scripts directory so config file is found correctly
            import os
            original_cwd = os.getcwd()
            os.chdir(scripts_dir)
            
            try:
                if self.custom_prompt:
                    # Use custom prompt directly with ollama
                    from image_describer import ImageDescriber
                    describer = ImageDescriber(model_name=self.model, config_file="image_describer_config.json")
                    
                    # Get the image as base64
                    image_base64 = describer.encode_image_to_base64(Path(self.image_path))
                    if not image_base64:
                        self.error.emit("Failed to encode image")
                        return
                    
                    # Get model settings
                    model_settings = describer.get_model_settings()
                    
                    # Call ollama directly with custom prompt
                    response = ollama.chat(
                        model=self.model,
                        messages=[
                            {
                                'role': 'user',
                                'content': self.custom_prompt,
                                'images': [image_base64]
                            }
                        ],
                        options=model_settings
                    )
                    
                    description = response['message']['content'].strip()
                    if description:
                        self.finished.emit(description)
                    else:
                        self.error.emit("Failed to generate description")
                else:
                    # Use standard ImageDescriber with prompt style
                    from image_describer import ImageDescriber

                    # Create describer instance with specified model and prompt
                    describer = ImageDescriber(
                        model_name=self.model,
                        prompt_style=self.prompt_style,
                        config_file="image_describer_config.json"
                    )

                    # Generate new description
                    description = describer.get_image_description(Path(self.image_path))
                    if description:
                        self.finished.emit(description)
                    else:
                        self.error.emit("Failed to generate description")
            finally:
                # Restore original working directory
                os.chdir(original_cwd)

        except Exception as e:
            self.error.emit(f"Error: {str(e)}")

class RedescribeDialog(QDialog):
    """Dialog for selecting model and prompt style for redescription"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Redescribe Image")
        self.setModal(True)
        self.setMinimumSize(400, 300)
        
        self.available_models = []
        self.available_prompts = []
        self.prompt_variations = {}  # Store the actual prompt texts
        
        self.init_ui()
        self.load_available_options()
    
    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Model selection
        layout.addWidget(QLabel("Select AI Model:"))
        self.model_combo = QComboBox()
        self.model_combo.setAccessibleName("Model Selection")
        self.model_combo.setAccessibleDescription("Choose the AI model to use for generating the new description.")
        layout.addWidget(self.model_combo)
        
        # Prompt style selection
        layout.addWidget(QLabel("Select Prompt Style:"))
        self.prompt_combo = QComboBox()
        self.prompt_combo.setAccessibleName("Prompt Style Selection")
        self.prompt_combo.setAccessibleDescription("Choose the style of description to generate.")
        self.prompt_combo.currentTextChanged.connect(self.update_prompt_preview)
        layout.addWidget(self.prompt_combo)
        
        # Prompt preview and editing
        layout.addWidget(QLabel("Prompt Text (you can edit this):"))
        self.prompt_edit = QPlainTextEdit()
        self.prompt_edit.setAccessibleName("Prompt Text Editor")
        self.prompt_edit.setAccessibleDescription("Edit the prompt that will be sent to the AI model.")
        self.prompt_edit.setMaximumHeight(120)
        # Override key press to make Tab exit the field
        self.prompt_edit.keyPressEvent = self.prompt_edit_key_press
        layout.addWidget(self.prompt_edit)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
    
    def load_available_options(self):
        """Load available models and prompt styles"""
        try:
            # Load available models from Ollama
            if ollama is None:
                raise ImportError("Ollama module not available")
            
            models_response = ollama.list()
            # Fix: models have .model attribute, not ['name'] key
            self.available_models = [model.model for model in models_response['models']]
            self.model_combo.addItems(self.available_models)
            
            # Load prompt styles from config
            scripts_dir = get_scripts_directory()
            config_file = scripts_dir / "image_describer_config.json"
            
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                prompt_variations = config.get('prompt_variations', {})
                self.prompt_variations = prompt_variations  # Store for later use
                self.available_prompts = list(prompt_variations.keys())
                self.prompt_combo.addItems(self.available_prompts)
                
                # Set default selections
                default_model = config.get('default_model', '')
                # Try to match default model with available models (handles version tags)
                for model in self.available_models:
                    if default_model in model:
                        self.model_combo.setCurrentText(model)
                        break
                
                default_prompt = config.get('default_prompt_style', 'detailed')
                if default_prompt in self.available_prompts:
                    self.prompt_combo.setCurrentText(default_prompt)
                
                # Set initial prompt text
                self.update_prompt_preview()
            
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Could not load available options: {e}")
            # Provide fallback options only if we couldn't load real ones
            if not self.available_models:
                self.model_combo.addItems(["moondream", "llava:7b", "llama3.2-vision:11b"])
            if not self.available_prompts:
                self.prompt_combo.addItems(["detailed", "concise", "narrative", "artistic", "technical"])
    
    def update_prompt_preview(self):
        """Update the prompt text preview when selection changes"""
        current_style = self.prompt_combo.currentText()
        
        # Case-insensitive lookup in loaded prompt variations
        if hasattr(self, 'prompt_variations') and self.prompt_variations:
            lower_variations = {k.lower(): v for k, v in self.prompt_variations.items()}
            if current_style.lower() in lower_variations:
                prompt_text = lower_variations[current_style.lower()]
                self.prompt_edit.setPlainText(prompt_text)
                return
        
        if current_style:
            # Fallback for unknown prompt styles with case-insensitive lookup
            fallback_prompts = {
                "detailed": "Describe this image in detail, including main subjects, setting, colors, and activities.",
                "concise": "Provide a brief description of this image.",
                "narrative": "Provide a narrative description including objects, colors and detail. Avoid interpretation, just describe.",
                "artistic": "Analyze this image from an artistic perspective, describing composition, colors, and mood.",
                "technical": "Provide a technical analysis of this image including photographic technique and quality."
            }
            # Case-insensitive fallback lookup
            lower_fallbacks = {k.lower(): v for k, v in fallback_prompts.items()}
            prompt_text = lower_fallbacks.get(current_style.lower(), "Describe this image.")
            self.prompt_edit.setPlainText(prompt_text)
    
    def get_selections(self):
        """Return the selected model, prompt style, and custom prompt text"""
        return self.model_combo.currentText(), self.prompt_combo.currentText(), self.prompt_edit.toPlainText()
    
    def set_processing(self, processing=True):
        """Show/hide progress indicator and disable/enable buttons"""
        self.progress_bar.setVisible(processing)
        if processing:
            self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.button_box.setEnabled(not processing)
        self.model_combo.setEnabled(not processing)
        self.prompt_combo.setEnabled(not processing)
    
    def prompt_edit_key_press(self, event):
        """Custom key press handler for prompt edit box"""
        from PyQt6.QtCore import Qt
        if event.key() == Qt.Key.Key_Tab:
            # Tab key pressed - move focus to next widget (the buttons)
            self.focusNextChild()
        else:
            # For all other keys, use the default behavior
            QPlainTextEdit.keyPressEvent(self.prompt_edit, event)

class ImageDescriptionViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Description Viewer")
        self.setMinimumSize(800, 600)
        self.setAccessibleName("Main Window")
        self.setAccessibleDescription("Main window for browsing image descriptions and images.")
        self.current_dir = None
        self.image_files = []
        self.descriptions = []
        self.descriptions_updated = []  # Track which descriptions have been updated
        self.redescribing_rows = set()  # Track which rows are currently being redescribed
        
        # Live monitoring components
        self.live_mode = False
        self.description_parser = DescriptionFileParser()
        self.workflow_monitor = None
        self.file_watcher = QFileSystemWatcher()
        self.file_watcher.fileChanged.connect(self.on_file_changed)
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_live_content)
        
        # Focus management for accessibility
        self.last_focused_widget = None
        self.preserve_selection = True
        self.updating_content = False
        
        # Progress tracking
        self.progress_info = {"current": 0, "total": 0, "active": False}
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Directory selection and mode controls
        dir_layout = QHBoxLayout()
        self.dir_label = QLabel("No directory loaded.")
        self.dir_label.setAccessibleName("Directory Label")
        self.dir_label.setAccessibleDescription("Shows the currently loaded workflow output directory.")
        dir_layout.addWidget(self.dir_label)
        
        # Live mode checkbox
        self.live_mode_checkbox = QCheckBox("Live Mode")
        self.live_mode_checkbox.setAccessibleName("Live Mode Toggle")
        self.live_mode_checkbox.setAccessibleDescription("Enable live monitoring of workflow progress. Updates descriptions in real-time as they are generated.")
        self.live_mode_checkbox.stateChanged.connect(self.toggle_live_mode)
        dir_layout.addWidget(self.live_mode_checkbox)
        
        # Refresh button (for live mode)
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setAccessibleName("Refresh Button")
        self.refresh_btn.setAccessibleDescription("Manually refresh the live content to check for new descriptions. Will preserve your current position.")
        self.refresh_btn.clicked.connect(self.manual_refresh)
        self.refresh_btn.setVisible(False)
        dir_layout.addWidget(self.refresh_btn)
        
        self.change_dir_btn = QPushButton("Change Directory")
        self.change_dir_btn.setAccessibleName("Change Directory Button")
        self.change_dir_btn.setAccessibleDescription("Button to change the loaded workflow output directory.")
        self.change_dir_btn.clicked.connect(self.change_directory)
        dir_layout.addWidget(self.change_dir_btn)
        layout.addLayout(dir_layout)

        # List of descriptions
        self.list_widget = QListWidget()
        self.list_widget.setAccessibleName("Descriptions List")
        self.list_widget.setAccessibleDescription("List of image descriptions. Use arrow keys to navigate. Each entry contains the full description for screen readers.")
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list_widget.currentRowChanged.connect(self.display_description)
        layout.addWidget(self.list_widget)

        # Image preview
        self.image_label = QLabel()
        self.image_label.setAccessibleName("Image Preview")
        self.image_label.setAccessibleDescription("Shows a preview of the selected image.")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumHeight(200)
        self.image_label.setFocusPolicy(Qt.FocusPolicy.TabFocus)  # Make it focusable with tab
        layout.addWidget(self.image_label)

        # Description display
        self.description_text = QTextEdit()
        self.description_text.setReadOnly(True)
        self.description_text.setAccessibleName("Description Text")
        self.description_text.setAccessibleDescription("Displays the full image description. Use arrow keys to navigate through the text.")
        # Enable text selection and copy with Ctrl+C
        self.description_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard)
        # Set focus policy to ensure it can receive focus for screen readers
        self.description_text.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        # Set word wrap for better readability
        self.description_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        layout.addWidget(self.description_text)

        # Buttons for clipboard actions
        btn_layout = QHBoxLayout()
        self.copy_desc_btn = QPushButton("Copy Description")
        self.copy_desc_btn.setAccessibleName("Copy Description Button")
        self.copy_desc_btn.setAccessibleDescription("Copy the selected description to the clipboard.")
        self.copy_desc_btn.clicked.connect(self.copy_description)
        btn_layout.addWidget(self.copy_desc_btn)

        self.copy_img_path_btn = QPushButton("Copy Image Path")
        self.copy_img_path_btn.setAccessibleName("Copy Image Path Button")
        self.copy_img_path_btn.setAccessibleDescription("Copy the selected image file path to the clipboard.")
        self.copy_img_path_btn.clicked.connect(self.copy_image_file_path)
        btn_layout.addWidget(self.copy_img_path_btn)

        self.copy_img_btn = QPushButton("Copy Image")
        self.copy_img_btn.setAccessibleName("Copy Image Button")
        self.copy_img_btn.setAccessibleDescription("Copy the selected image to the clipboard.")
        self.copy_img_btn.clicked.connect(self.copy_image_to_clipboard)
        btn_layout.addWidget(self.copy_img_btn)

        self.redescribe_btn = QPushButton("Redescribe")
        self.redescribe_btn.setAccessibleName("Redescribe Button")
        self.redescribe_btn.setAccessibleDescription("Generate a new description for the selected image using a chosen model and prompt.")
        self.redescribe_btn.clicked.connect(self.redescribe_image)
        btn_layout.addWidget(self.redescribe_btn)

        layout.addLayout(btn_layout)

        # Status bar
        self.status_bar = QStatusBar()
        self.status_bar.setAccessibleName("Status: Ready")
        self.status_bar.setAccessibleDescription("Shows current operation status and progress.")
        self.status_bar.showMessage("Ready")
        layout.addWidget(self.status_bar)

    def toggle_live_mode(self, checked):
        """Toggle between live mode and HTML mode"""
        self.live_mode = checked
        self.refresh_btn.setVisible(checked)
        
        if checked:
            self.status_bar.showMessage("Live mode enabled - monitoring for updates")
            if self.current_dir:
                self.start_live_monitoring()
        else:
            self.status_bar.showMessage("Live mode disabled - using final HTML output")
            self.stop_live_monitoring()
            # Reload from HTML if available
            if self.current_dir:
                self.load_descriptions(self.current_dir)
    
    def start_live_monitoring(self):
        """Start monitoring the descriptions file for changes"""
        if not self.current_dir:
            return
        
        descriptions_file = Path(self.current_dir) / "descriptions" / "image_descriptions.txt"
        
        if descriptions_file.exists():
            # Add file to watcher
            self.file_watcher.addPath(str(descriptions_file))
            
            # Start workflow monitor
            if self.workflow_monitor:
                self.workflow_monitor.stop()
                self.workflow_monitor.wait()
            
            self.workflow_monitor = WorkflowMonitor(Path(self.current_dir))
            self.workflow_monitor.progress_updated.connect(self.update_progress)
            self.workflow_monitor.start()
            
            # Start refresh timer for regular updates
            self.refresh_timer.start(15000)  # Refresh every 15 seconds (less aggressive)
            
            # Load initial content
            self.refresh_live_content()
        else:
            self.status_bar.showMessage("Descriptions file not found - live mode unavailable")
            self.live_mode_checkbox.setChecked(False)
    
    def stop_live_monitoring(self):
        """Stop monitoring for live updates"""
        if self.workflow_monitor:
            self.workflow_monitor.stop()
            self.workflow_monitor.wait()
            self.workflow_monitor = None
        
        self.refresh_timer.stop()
        self.file_watcher.removePaths(self.file_watcher.files())
        
        # Reset title to remove progress
        self.setWindowTitle("Image Description Viewer")
    
    def update_progress(self, progress_info):
        """Update progress information and title bar"""
        self.progress_info = progress_info
        self.update_title()
    
    def update_title(self):
        """Update window title with progress information for screen readers"""
        base_title = "Image Description Viewer"
        
        if self.live_mode and self.progress_info.get("total", 0) > 0:
            current = self.progress_info.get("current", 0)
            total = self.progress_info.get("total", 0)
            active = self.progress_info.get("active", False)
            
            status = "Processing" if active else "Completed"
            title = f"{base_title} - {status}: {current} of {total} images"
            
            if active:
                title += " (Live)"
            
            self.setWindowTitle(title)
        else:
            self.setWindowTitle(base_title)
    
    def on_file_changed(self, path):
        """Handle file system changes with focus preservation"""
        if self.live_mode and not self.updating_content:
            # Only update if user isn't actively interacting
            focused_widget = QApplication.focusWidget()
            if focused_widget in [self.list_widget, self.description_text]:
                # User is actively navigating - defer update
                QTimer.singleShot(5000, self.refresh_live_content)  # Try again in 5 seconds
            else:
                # Safe to update
                QTimer.singleShot(1000, self.refresh_live_content)
    
    def refresh_live_content(self):
        """Refresh content from live descriptions file with focus preservation"""
        if not self.live_mode or not self.current_dir:
            return
        
        # Check if user is actively interacting - if so, defer update
        focused_widget = QApplication.focusWidget()
        if focused_widget in [self.list_widget, self.description_text]:
            # User is actively using the interface - don't disrupt them
            return
        
        descriptions_file = Path(self.current_dir) / "descriptions" / "image_descriptions.txt"
        
        if not descriptions_file.exists():
            return
        
        try:
            # Set updating flag to prevent recursive updates
            self.updating_content = True
            
            # Save current state before updating
            current_row = self.list_widget.currentRow()
            current_item_count = self.list_widget.count()
            was_focused_on_list = focused_widget == self.list_widget
            
            # Parse the file
            entries = self.description_parser.parse_file(descriptions_file)
            
            if not entries:
                return
            
            # Check if there are actually new entries to avoid unnecessary updates
            if len(entries) == current_item_count:
                # No new entries, just update progress info
                parser_progress = self.description_parser.get_progress()
                if parser_progress["current"] > 0:
                    self.progress_info.update(parser_progress)
                    self.update_title()
                return
            
            # Update progress from parser
            parser_progress = self.description_parser.get_progress()
            if parser_progress["current"] > 0:
                self.progress_info.update(parser_progress)
                self.update_title()
            
            # Only add new entries, don't clear existing ones
            # This prevents jumping back to the top
            new_entries = entries[current_item_count:]
            
            if new_entries:
                # Base directory for resolving image paths
                base_dir = Path(self.current_dir)
                
                # Add only new entries
                for entry in new_entries:
                    # Resolve image path
                    rel_path = entry['relative_path']
                    
                    # Try different possible locations
                    possible_paths = [
                        base_dir / "temp_combined_images" / rel_path,
                        base_dir / "converted_images" / rel_path,
                        base_dir / "extracted_frames" / rel_path,
                        base_dir / rel_path
                    ]
                    
                    image_path = None
                    for possible_path in possible_paths:
                        if possible_path.exists():
                            image_path = str(possible_path)
                            break
                    
                    if not image_path:
                        # Use the first possibility even if it doesn't exist
                        image_path = str(possible_paths[0])
                    
                    self.image_files.append(image_path)
                    self.descriptions.append(entry['description'])
                    self.descriptions_updated.append(False)
                    
                    # Create list item
                    truncated = entry['description'][:100] + ("..." if len(entry['description']) > 100 else "")
                    from PyQt6.QtWidgets import QListWidgetItem
                    item = QListWidgetItem(truncated)
                    item.setData(Qt.ItemDataRole.AccessibleTextRole, entry['description'].strip())
                    self.list_widget.addItem(item)
                
                # Update status quietly (no focus disruption)
                count = len(entries)
                active_status = " (Active)" if self.progress_info.get("active", False) else ""
                self.status_bar.showMessage(f"Live mode: {count} descriptions loaded{active_status}")
                
                # Preserve current selection - don't change focus or selection unless there was nothing selected
                if current_row >= 0:
                    # Keep current selection
                    self.list_widget.setCurrentRow(current_row)
                elif not was_focused_on_list and len(entries) == len(new_entries):
                    # This is the first load - set initial selection but don't steal focus
                    self.list_widget.setCurrentRow(0)
                    
        except Exception as e:
            self.status_bar.showMessage(f"Error refreshing live content: {e}")
        finally:
            # Clear updating flag
            self.updating_content = False

    def change_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Workflow Output Directory")
        if dir_path:
            self.load_descriptions(dir_path)

    def load_descriptions(self, dir_path):
        """Load descriptions from either HTML or live file based on mode"""
        self.current_dir = dir_path
        self.dir_label.setText(f"Loaded: {dir_path}")
        
        # Stop any existing monitoring
        self.stop_live_monitoring()
        
        # Check if live mode should be auto-enabled
        descriptions_file = Path(dir_path) / "descriptions" / "image_descriptions.txt"
        html_file = Path(dir_path) / "html_reports" / "image_descriptions.html"
        
        # Auto-enable live mode if descriptions file exists but HTML doesn't
        if descriptions_file.exists() and not html_file.exists():
            self.live_mode_checkbox.setChecked(True)
            self.live_mode = True
        
        if self.live_mode:
            self.start_live_monitoring()
        else:
            self.load_html_descriptions(dir_path)
    
    def load_html_descriptions(self, dir_path):
        """Load descriptions from HTML file (original behavior)"""
        html_path = os.path.join(dir_path, "html_reports", "image_descriptions.html")
        self.image_files = []
        self.descriptions = []
        self.descriptions_updated = []  # Reset updated tracking
        self.redescribing_rows = set()  # Reset redescribing tracking
        self.list_widget.clear()
        
        if os.path.isfile(html_path):
            try:
                with open(html_path, "r", encoding="utf-8") as f:
                    html = f.read()
                import re
                entry_pattern = re.compile(r'<div class="entry" id="entry-\d+">.*?<h2>(.*?)</h2>.*?<h4>Description</h4>.*?<p>(.*?)</p>', re.DOTALL)
                entries = entry_pattern.findall(html)
                from PyQt6.QtWidgets import QListWidgetItem
                for img_path, desc in entries:
                    img_path = img_path.replace('\\', os.sep).replace('/', os.sep)
                    desc = re.sub(r'<br\s*/?>', '\n', desc)
                    desc = re.sub(r'&[a-zA-Z0-9#]+;', lambda m: {
                        '&quot;': '"', '&#x27;': "'", '&amp;': '&', '&lt;': '<', '&gt;': '>'
                    }.get(m.group(0), m.group(0)), desc)
                    self.image_files.append(os.path.join(dir_path, img_path))
                    self.descriptions.append(desc.strip())
                    self.descriptions_updated.append(False)  # Track that this is original description
                    truncated = desc[:100] + ("..." if len(desc) > 100 else "")
                    item = QListWidgetItem(truncated)
                    from PyQt6.QtCore import Qt
                    item.setData(Qt.ItemDataRole.AccessibleTextRole, desc.strip())
                    self.list_widget.addItem(item)
                if self.descriptions:
                    self.list_widget.setCurrentRow(0)
                    # Set focus to the list so users can immediately start navigating
                    # But only if no other widget currently has focus
                    if not QApplication.focusWidget():
                        self.list_widget.setFocus()
                else:
                    QMessageBox.information(self, "No Descriptions", "No image descriptions found in HTML report.")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to parse HTML report: {e}")
        else:
            # Try live mode if HTML not available
            descriptions_file = Path(dir_path) / "descriptions" / "image_descriptions.txt"
            if descriptions_file.exists():
                reply = QMessageBox.question(self, "HTML Not Found", 
                                           "HTML report not found, but live descriptions file is available. Switch to live mode?",
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.Yes:
                    self.live_mode_checkbox.setChecked(True)
                    self.live_mode = True
                    self.start_live_monitoring()
                    return
            
            QMessageBox.warning(self, "Error", "HTML report not found. Please select a valid workflow output directory.")

    def manual_refresh(self):
        """Manually refresh content, preserving focus and position"""
        focused_widget = QApplication.focusWidget()
        current_row = self.list_widget.currentRow()
        
        # Force refresh by temporarily clearing the last modified time
        if hasattr(self.description_parser, 'last_modified'):
            self.description_parser.last_modified = 0
        
        # Do the refresh
        self.refresh_live_content()
        
        # Restore focus and position
        if current_row >= 0 and current_row < self.list_widget.count():
            self.list_widget.setCurrentRow(current_row)
        
        if focused_widget:
            focused_widget.setFocus()
        
        # Update status to show manual refresh happened
        self.status_bar.showMessage("Manually refreshed - content updated")
        QTimer.singleShot(3000, lambda: self.status_bar.showMessage("Ready"))

    def display_description(self, row):
        # Don't update if we're in the middle of content updates
        if self.updating_content:
            return
            
        # Show description
        if 0 <= row < len(self.descriptions):
            description = self.descriptions[row]
            
            # Process the text to ensure blank lines are properly handled for screen readers
            # Split into lines and process each blank line
            lines = description.split('\n')
            processed_lines = []
            
            for line in lines:
                if line.strip() == '':  # If line is empty or just whitespace
                    processed_lines.append('\u00A0')  # Use non-breaking space
                else:
                    processed_lines.append(line)
            
            processed_description = '\n'.join(processed_lines)
            
            # Only update text if it's actually different to avoid cursor jumping
            if self.description_text.toPlainText() != processed_description:
                # Save cursor position if description_text has focus
                cursor_position = None
                if self.description_text.hasFocus():
                    cursor = self.description_text.textCursor()
                    cursor_position = cursor.position()
                
                self.description_text.setPlainText(processed_description)
                
                # Restore cursor position if we saved it
                if cursor_position is not None:
                    cursor = self.description_text.textCursor()
                    cursor.setPosition(min(cursor_position, len(processed_description)))
                    self.description_text.setTextCursor(cursor)
                else:
                    # Only move to beginning if not focused
                    cursor = self.description_text.textCursor()
                    cursor.movePosition(cursor.MoveOperation.Start)
                    self.description_text.setTextCursor(cursor)
            
            # Update accessible description for screen readers without stealing focus
            self.description_text.setAccessibleDescription(f"Image description with {len(description)} characters: {description}")
            
        else:
            if self.description_text.toPlainText():  # Only clear if there's content
                self.description_text.clear()
                self.description_text.setAccessibleDescription("No description selected.")
                
        # Show image preview
        if 0 <= row < len(self.image_files):
            img_path = self.image_files[row]
            filename = os.path.basename(img_path)
            if os.path.isfile(img_path):
                pixmap = QPixmap(img_path)
                if not pixmap.isNull():
                    # Scale image to fit label
                    scaled = pixmap.scaled(self.image_label.width(), self.image_label.height(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    self.image_label.setPixmap(scaled)
                    self.image_label.setText("")
                    # Set accessible name with filename and preview
                    self.image_label.setAccessibleName(f"{filename} preview")
                    self.image_label.setAccessibleDescription(f"Preview of image file {filename}")
                else:
                    self.image_label.setPixmap(QPixmap())
                    self.image_label.setText("Could not load image.")
                    self.image_label.setAccessibleName(f"{filename} preview - failed to load")
                    self.image_label.setAccessibleDescription(f"Could not load image file {filename}")
            else:
                self.image_label.setPixmap(QPixmap())
                self.image_label.setText("Image not found.")
                self.image_label.setAccessibleName(f"{filename} preview - not found")
                self.image_label.setAccessibleDescription(f"Image file {filename} not found")
        else:
            self.image_label.setPixmap(QPixmap())
            self.image_label.setText("")
            self.image_label.setAccessibleName("Image Preview")
            self.image_label.setAccessibleDescription("No image selected")

    def copy_description(self):
        row = self.list_widget.currentRow()
        if 0 <= row < len(self.descriptions):
            clipboard = QGuiApplication.clipboard()
            clipboard.clear()
            from PyQt6.QtGui import QClipboard
            clipboard.setText(self.descriptions[row], mode=QClipboard.Mode.Clipboard)
            # Removed success message - clipboard operation is silent

    def copy_image_file_path(self):
        row = self.list_widget.currentRow()
        if 0 <= row < len(self.image_files):
            img_path = self.image_files[row]
            clipboard = QGuiApplication.clipboard()
            clipboard.clear()
            from PyQt6.QtGui import QClipboard
            clipboard.setText(img_path, mode=QClipboard.Mode.Clipboard)
            # Removed success message - clipboard operation is silent

    def copy_image_to_clipboard(self):
        row = self.list_widget.currentRow()
        if 0 <= row < len(self.image_files):
            img_path = self.image_files[row]
            if os.path.isfile(img_path):
                image = QImage(img_path)
                if not image.isNull():
                    clipboard = QGuiApplication.clipboard()
                    clipboard.clear()
                    clipboard.setImage(image, mode=QClipboard.Mode.Clipboard)
                    # Removed success message - clipboard operation is silent
                else:
                    QMessageBox.warning(self, "Error", "Could not load image for clipboard.")
            else:
                QMessageBox.warning(self, "Error", "Image file not found.")

    def redescribe_image(self):
        """Open dialog to redescribe the current image with selected model and prompt"""
        row = self.list_widget.currentRow()
        if not (0 <= row < len(self.image_files)):
            QMessageBox.information(self, "No Selection", "Please select an image to redescribe.")
            return
        
        # Check if this image is already being redescribed
        if row in self.redescribing_rows:
            QMessageBox.information(self, "Already Processing", 
                                  "This image is already being redescribed. Please wait for it to complete.")
            return
        
        # Check if Ollama is available
        try:
            if ollama is None:
                raise ImportError("Ollama module not available")
            ollama.list()
        except Exception as e:
            QMessageBox.critical(self, "Ollama Not Available", 
                               f"Ollama is not available or not running.\nError: {e}\n\n"
                               "Please make sure Ollama is installed and running.")
            return
        
        # Show dialog for model and prompt selection
        dialog = RedescribeDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            model, prompt_style, custom_prompt = dialog.get_selections()
            
            if not model:
                QMessageBox.warning(self, "Invalid Selection", "Please select a model.")
                return
            
            # Track that this row is being processed
            self.redescribing_rows.add(row)
            
            # Add processing indicator to list item
            current_item = self.list_widget.item(row)
            if current_item:
                current_text = current_item.text()
                # Remove any existing emoji prefixes first
                if current_text.startswith("🔄 "):
                    current_text = current_text[2:]
                elif current_text.startswith("⏳ "):
                    current_text = current_text[2:]
                
                # Add processing emoji
                processing_text = "⏳ " + current_text
                current_item.setText(processing_text)
                
                # Update accessible text to indicate processing
                accessible_text = f"Processing: {self.descriptions[row]}"
                current_item.setData(Qt.ItemDataRole.AccessibleTextRole, accessible_text)
            
            # Update status bar
            img_filename = os.path.basename(self.image_files[row])
            status_message = f"Redescribing {img_filename} with {model}..."
            self.status_bar.showMessage(status_message)
            # Update accessible name for screen readers
            self.status_bar.setAccessibleName(f"Status: {status_message}")
            
            img_path = self.image_files[row]
            
            # Create and start worker thread
            self.worker = RedescribeWorker(img_path, model, prompt_style, custom_prompt)
            self.worker.finished.connect(lambda desc: self.on_redescribe_finished(desc, row))
            self.worker.error.connect(lambda err: self.on_redescribe_error(err, row))
            self.worker.start()
    
    def on_redescribe_finished(self, new_description, row):
        """Handle successful redescription"""
        # Remove from processing set
        self.redescribing_rows.discard(row)
        
        # Update status bar
        status_message = "Redescription completed successfully!"
        self.status_bar.showMessage(status_message)
        # Update accessible name for screen readers
        self.status_bar.setAccessibleName(f"Status: {status_message}")
        
        # Update the description in memory
        self.descriptions[row] = new_description
        self.descriptions_updated[row] = True  # Mark as updated
        
        # Update the list item text with emoji marker
        from PyQt6.QtWidgets import QListWidgetItem
        from PyQt6.QtCore import Qt
        emoji_prefix = "🔄 "  # Emoji to indicate updated description
        truncated = new_description[:97] + ("..." if len(new_description) > 97 else "")
        display_text = emoji_prefix + truncated
        
        item = self.list_widget.item(row)
        item.setText(display_text)
        # Include "Updated" status in accessible text for screen readers
        accessible_text = f"Updated: {new_description.strip()}"
        item.setData(Qt.ItemDataRole.AccessibleTextRole, accessible_text)
        
        # Update the description display if this row is currently selected
        if self.list_widget.currentRow() == row:
            self.display_description(row)
        
        # Clear status message after a few seconds
        QApplication.processEvents()
        import threading
        def clear_status():
            import time
            time.sleep(3)
            ready_message = "Ready"
            self.status_bar.showMessage(ready_message)
            self.status_bar.setAccessibleName(f"Status: {ready_message}")
        threading.Thread(target=clear_status, daemon=True).start()
    
    def on_redescribe_error(self, error_message, row):
        """Handle redescription error"""
        # Remove from processing set
        self.redescribing_rows.discard(row)
        
        # Clear processing indicator from list item
        item = self.list_widget.item(row)
        if item:
            current_text = item.text()
            # Remove processing emoji if present
            if current_text.startswith("⏳ "):
                original_text = current_text[2:]
                item.setText(original_text)
                # Restore original accessible text
                item.setData(Qt.ItemDataRole.AccessibleTextRole, self.descriptions[row])
        
        # Update status bar
        status_message = "Redescription failed"
        self.status_bar.showMessage(status_message)
        self.status_bar.setAccessibleName(f"Status: {status_message}")
        
        # Show error message
        QMessageBox.critical(self, "Redescription Failed", f"Failed to redescribe image:\n{error_message}")
        
        # Clear status message
        ready_message = "Ready"
        self.status_bar.showMessage(ready_message)
        self.status_bar.setAccessibleName(f"Status: {ready_message}")

    def closeEvent(self, event):
        """Handle application closing to clean up resources"""
        self.stop_live_monitoring()
        event.accept()


def main():
    import argparse
    
    # Create parser for command-line arguments
    parser = argparse.ArgumentParser(
        description='Image Description Viewer - Browse workflow results and image descriptions',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Launch viewer with directory browser
  viewer.exe
  
  # Open specific workflow output directory
  viewer.exe C:\\path\\to\\workflow_output
  
  # Launch directly to directory selection dialog
  viewer.exe --open
  
  # Show help
  viewer.exe --help

The viewer supports two modes:
  - HTML Mode: View completed workflows with full HTML reports
  - Live Mode: Monitor workflows in progress with real-time updates

Keyboard shortcuts:
  Up/Down Arrow: Navigate between images
  Ctrl+C: Copy current description to clipboard
  Ctrl+R: Redescribe current image (requires Ollama)
"""
    )
    
    parser.add_argument(
        'directory',
        nargs='?',
        help='Workflow output directory to load on startup (optional)'
    )
    
    parser.add_argument(
        '--open',
        action='store_true',
        help='Launch directly to the directory selection dialog'
    )
    
    # Filter out Qt arguments before parsing
    # Qt can add its own args like -platform, etc.
    import sys
    filtered_args = [arg for arg in sys.argv if not arg.startswith('-platform')]
    args = parser.parse_args(filtered_args[1:])  # Skip program name
    
    # Create Qt application
    app = QApplication(sys.argv)
    viewer = ImageDescriptionViewer()
    
    # Handle command-line options
    if args.open:
        # Show the directory dialog immediately
        viewer.show()
        QTimer.singleShot(100, viewer.change_directory)
    elif args.directory:
        # Load the specified directory
        dir_path = Path(args.directory).resolve()
        if dir_path.exists() and dir_path.is_dir():
            viewer.load_descriptions(str(dir_path))
            viewer.show()
        else:
            print(f"Error: Directory not found: {args.directory}", file=sys.stderr)
            QMessageBox.critical(None, "Directory Not Found", 
                               f"The specified directory does not exist:\n{args.directory}\n\nPlease select a valid workflow output directory.")
            viewer.show()
            QTimer.singleShot(100, viewer.change_directory)
    else:
        # Normal startup - show empty viewer
        viewer.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
