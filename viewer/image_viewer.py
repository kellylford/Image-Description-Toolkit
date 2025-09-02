# Qt6 Image Description Viewer
# This app allows users to browse image descriptions from a completed workflow run.
# Accessibility best practices are followed throughout.

import sys
import os
import re
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QLabel, 
    QPushButton, QFileDialog, QMessageBox, QAbstractItemView, QTextEdit, 
    QListWidgetItem, QSplitter
)
from PyQt6.QtGui import QGuiApplication, QPixmap, QImage
from PyQt6.QtCore import Qt

class ImageDescriptionViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Description Viewer")
        self.setMinimumSize(1000, 700)
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

        # Main content splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # Left side - List of descriptions
        self.list_widget = QListWidget()
        self.list_widget.setAccessibleName("Descriptions List")
        self.list_widget.setAccessibleDescription("List of image descriptions. Use arrow keys to navigate. Each entry contains the full description for screen readers.")
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list_widget.currentRowChanged.connect(self.display_description)
        self.list_widget.setMaximumWidth(400)
        splitter.addWidget(self.list_widget)

        # Right side - Image and description
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Image preview
        self.image_label = QLabel()
        self.image_label.setAccessibleName("Image Preview")
        self.image_label.setAccessibleDescription("Shows a preview of the selected image.")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumHeight(300)
        self.image_label.setStyleSheet("border: 1px solid gray;")
        self.image_label.setText("Select an image to preview")
        self.image_label.setFocusPolicy(Qt.FocusPolicy.TabFocus)  # Make it focusable with tab
        right_layout.addWidget(self.image_label)

        # Description display
        self.description_text = QTextEdit()
        self.description_text.setReadOnly(True)
        self.description_text.setAccessibleName("Description Text")
        self.description_text.setAccessibleDescription("Displays the full image description.")
        self.description_text.setMinimumHeight(150)
        right_layout.addWidget(self.description_text)

        # Buttons for clipboard actions
        btn_layout = QHBoxLayout()
        self.copy_desc_btn = QPushButton("Copy Description")
        self.copy_desc_btn.setAccessibleName("Copy Description Button")
        self.copy_desc_btn.setAccessibleDescription("Copy the selected description to the clipboard.")
        self.copy_desc_btn.clicked.connect(self.copy_description)
        self.copy_desc_btn.setEnabled(False)
        btn_layout.addWidget(self.copy_desc_btn)

        self.copy_img_btn = QPushButton("Copy Image")
        self.copy_img_btn.setAccessibleName("Copy Image Button")
        self.copy_img_btn.setAccessibleDescription("Copy the selected image to the clipboard.")
        self.copy_img_btn.clicked.connect(self.copy_image)
        self.copy_img_btn.setEnabled(False)
        btn_layout.addWidget(self.copy_img_btn)

        right_layout.addLayout(btn_layout)
        splitter.addWidget(right_widget)

    def change_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Workflow Output Directory")
        if dir_path:
            self.load_descriptions(dir_path)

    def load_descriptions(self, dir_path):
        html_path = os.path.join(dir_path, "html_reports", "image_descriptions.html")
        self.current_dir = dir_path
        self.dir_label.setText(f"Loaded: {os.path.basename(dir_path)}")
        self.image_files = []
        self.descriptions = []
        self.list_widget.clear()
        
        if os.path.isfile(html_path):
            try:
                with open(html_path, "r", encoding="utf-8") as f:
                    html = f.read()
                
                entry_pattern = re.compile(r'<div class="entry" id="entry-\d+">.*?<h2>(.*?)</h2>.*?<h4>Description</h4>.*?<p>(.*?)</p>', re.DOTALL)
                entries = entry_pattern.findall(html)
                
                for img_path, desc in entries:
                    # Clean up paths and descriptions
                    img_path = img_path.replace('\\', os.sep).replace('/', os.sep)
                    desc = re.sub(r'<br\s*/?>', '\n', desc)
                    desc = re.sub(r'&quot;', '"', desc)
                    desc = re.sub(r'&#x27;', "'", desc)
                    desc = re.sub(r'&amp;', '&', desc)
                    desc = re.sub(r'&lt;', '<', desc)
                    desc = re.sub(r'&gt;', '>', desc)
                    
                    full_img_path = os.path.join(dir_path, img_path)
                    self.image_files.append(full_img_path)
                    self.descriptions.append(desc.strip())
                    
                    # Create list item with truncated display text but full accessible text
                    display_text = os.path.basename(img_path)
                    item = QListWidgetItem(display_text)
                    item.setToolTip(desc.strip())  # Show full description on hover
                    item.setData(Qt.ItemDataRole.AccessibleTextRole, desc.strip())
                    self.list_widget.addItem(item)
                
                if self.descriptions:
                    self.list_widget.setCurrentRow(0)
                    self.copy_desc_btn.setEnabled(True)
                    self.copy_img_btn.setEnabled(True)
                else:
                    QMessageBox.information(self, "No Descriptions", "No image descriptions found in HTML report.")
                    
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to parse HTML report: {e}")
        else:
            QMessageBox.warning(self, "Error", "HTML report not found. Please select a valid workflow output directory.")

    def display_description(self, row):
        if 0 <= row < len(self.descriptions):
            # Show full description in text box
            self.description_text.setPlainText(self.descriptions[row])
            
            # Show image preview
            img_path = self.image_files[row]
            if os.path.isfile(img_path):
                pixmap = QPixmap(img_path)
                if not pixmap.isNull():
                    # Scale image to fit preview area while maintaining aspect ratio
                    scaled = pixmap.scaled(
                        self.image_label.size(), 
                        Qt.AspectRatioMode.KeepAspectRatio, 
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self.image_label.setPixmap(scaled)
                else:
                    self.image_label.clear()
                    self.image_label.setText("Could not load image.")
            else:
                self.image_label.clear()
                self.image_label.setText("Image file not found.")
        else:
            self.description_text.clear()
            self.image_label.clear()
            self.image_label.setText("Select an image to preview")

    def copy_description(self):
        row = self.list_widget.currentRow()
        if 0 <= row < len(self.descriptions):
            clipboard = QGuiApplication.clipboard()
            clipboard.setText(self.descriptions[row])

    def copy_image(self):
        row = self.list_widget.currentRow()
        if 0 <= row < len(self.image_files):
            img_path = self.image_files[row]
            if os.path.isfile(img_path):
                image = QImage(img_path)
                if not image.isNull():
                    clipboard = QGuiApplication.clipboard()
                    clipboard.setImage(image)
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
