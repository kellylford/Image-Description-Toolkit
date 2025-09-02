# Qt6 Image Description Viewer
# This app allows users to browse image descriptions from a completed workflow run.
# Accessibility best practices are followed throughout.

import sys
import os
import json
import subprocess
from pathlib import Path
try:
    import ollama
except ImportError:
    ollama = None
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QLabel, QPushButton, 
    QFileDialog, QMessageBox, QAbstractItemView, QTextEdit, QDialog, QComboBox, QDialogButtonBox, QProgressBar, QStatusBar, QPlainTextEdit
)
from PyQt6.QtGui import QClipboard, QGuiApplication
from PyQt6.QtCore import Qt, QThread, pyqtSignal

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
            scripts_dir = Path(__file__).parent.parent / "scripts"
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
            scripts_dir = Path(__file__).parent.parent / "scripts"
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
        if current_style in self.prompt_variations:
            prompt_text = self.prompt_variations[current_style]
            self.prompt_edit.setPlainText(prompt_text)
        elif current_style:
            # Fallback for unknown prompt styles
            fallback_prompts = {
                "detailed": "Describe this image in detail, including main subjects, setting, colors, and activities.",
                "concise": "Provide a brief description of this image.",
                "narrative": "Provide a narrative description including objects, colors and detail. Avoid interpretation, just describe.",
                "artistic": "Analyze this image from an artistic perspective, describing composition, colors, and mood.",
                "technical": "Provide a technical analysis of this image including photographic technique and quality."
            }
            prompt_text = fallback_prompts.get(current_style, "Describe this image.")
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
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Directory selection
        dir_layout = QHBoxLayout()
        self.dir_label = QLabel("No directory loaded.")
        self.dir_label.setAccessibleName("Directory Label")
        self.dir_label.setAccessibleDescription("Shows the currently loaded workflow output directory.")
        dir_layout.addWidget(self.dir_label)
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

    def change_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Workflow Output Directory")
        if dir_path:
            self.load_descriptions(dir_path)

    def load_descriptions(self, dir_path):
        html_path = os.path.join(dir_path, "html_reports", "image_descriptions.html")
        self.current_dir = dir_path
        self.dir_label.setText(f"Loaded: {dir_path}")
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
                    self.list_widget.setFocus()
                else:
                    QMessageBox.information(self, "No Descriptions", "No image descriptions found in HTML report.")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to parse HTML report: {e}")
        else:
            QMessageBox.warning(self, "Error", "HTML report not found. Please select a valid workflow output directory.")

    def display_description(self, row):
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
            
            self.description_text.setPlainText(processed_description)
            
            # Update accessible description for screen readers without stealing focus
            self.description_text.setAccessibleDescription(f"Image description with {len(description)} characters: {description}")
            
            # Move cursor to beginning for reading, but don't steal focus
            cursor = self.description_text.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            self.description_text.setTextCursor(cursor)
            
        else:
            self.description_text.clear()
            self.description_text.setAccessibleDescription("No description selected.")
        # Show image preview
        if 0 <= row < len(self.image_files):
            img_path = self.image_files[row]
            filename = os.path.basename(img_path)
            from PyQt6.QtGui import QPixmap
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
            from PyQt6.QtGui import QImage, QPixmap, QClipboard, QGuiApplication
            img_path = self.image_files[row]
            if os.path.isfile(img_path):
                image = QImage(img_path)
                if not image.isNull():
                    clipboard = QGuiApplication.clipboard()
                    clipboard.clear()
                    from PyQt6.QtGui import QClipboard
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


def main():
    app = QApplication(sys.argv)
    viewer = ImageDescriptionViewer()
    viewer.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
