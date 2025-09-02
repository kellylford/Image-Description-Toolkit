# Qt6 Image Description Viewer
# This app allows users to browse image descriptions from a completed workflow run.
# Accessibility best practices are followed throughout.

import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QLabel, QPushButton, QFileDialog, QMessageBox, QAbstractItemView, QTextEdit
)
from PyQt6.QtGui import QClipboard, QGuiApplication
from PyQt6.QtCore import Qt

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

        layout.addLayout(btn_layout)

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



def main():
    app = QApplication(sys.argv)
    viewer = ImageDescriptionViewer()
    viewer.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
