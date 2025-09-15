"""
Dialog classes for Image Describer

This module contains all dialog windows used in the Image Describer application.
"""

import os
import json
import subprocess
import webbrowser
from pathlib import Path
from typing import List, Dict, Optional, Any

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTextEdit, QListWidget, QListWidgetItem, QComboBox, QCheckBox,
    QGroupBox, QFormLayout, QSpinBox, QDoubleSpinBox, QRadioButton,
    QButtonGroup, QTabWidget, QScrollArea, QFrame, QFileDialog,
    QMessageBox, QDialogButtonBox, QProgressBar, QTreeWidget, QTreeWidgetItem,
    QPlainTextEdit, QSlider
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPixmap, QTextCursor

# Import our refactored modules
from data_models import ImageDescription, ImageItem, ImageWorkspace
from ui_components import AccessibleTreeWidget, AccessibleNumericInput, AccessibleTextEdit


class DirectorySelectionDialog(QDialog):
    """Dialog for selecting directory with options for recursive search and multiple directories"""
    def __init__(self, existing_directories: List[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Image Directory")
        self.setModal(True)
        self.resize(600, 400)
        
        self.selected_directory = ""
        self.recursive_search = False
        self.add_to_existing = False
        
        layout = QVBoxLayout(self)
        
        # Directory selection
        dir_group = QGroupBox("Directory Selection")
        dir_layout = QVBoxLayout(dir_group)
        
        self.dir_label = QLabel("No directory selected")
        dir_layout.addWidget(self.dir_label)
        
        self.browse_button = QPushButton("Browse for Directory...")
        self.browse_button.clicked.connect(self.browse_directory)
        dir_layout.addWidget(self.browse_button)
        
        layout.addWidget(dir_group)
        
        # Options
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout(options_group)
        
        self.recursive_checkbox = QCheckBox("Search subdirectories recursively")
        self.recursive_checkbox.setToolTip("When checked, searches all subdirectories for images")
        options_layout.addWidget(self.recursive_checkbox)
        
        self.add_to_existing_checkbox = QCheckBox("Add to existing workspace")
        if existing_directories:
            self.add_to_existing_checkbox.setToolTip(f"Add to existing directories:\\n" + 
                                                    "\\n".join([f"{Path(d).name}" for d in existing_directories[:5]]))
        else:
            self.add_to_existing_checkbox.setToolTip("No existing directories in workspace")
            self.add_to_existing_checkbox.setEnabled(False)
        options_layout.addWidget(self.add_to_existing_checkbox)
        
        layout.addWidget(options_group)
        
        # Existing directories display
        if existing_directories:
            existing_group = QGroupBox(f"Current Workspace Directories ({len(existing_directories)})")
            existing_layout = QVBoxLayout(existing_group)
            
            for directory in existing_directories[:10]:  # Show up to 10
                dir_label = QLabel(str(Path(directory).name))
                dir_label.setToolTip(str(directory))
                existing_layout.addWidget(dir_label)
            
            if len(existing_directories) > 10:
                more_label = QLabel(f"... and {len(existing_directories) - 10} more")
                existing_layout.addWidget(more_label)
            
            layout.addWidget(existing_group)
        
        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | 
                                    QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Update button state
        self.update_ok_button()
        button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        self.button_box = button_box
    
    def browse_directory(self):
        """Open directory selection dialog"""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Image Directory",
            "",
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks
        )
        
        if directory:
            self.selected_directory = directory
            self.dir_label.setText(f"Selected: {Path(directory).name}")
            self.dir_label.setToolTip(directory)
            self.update_ok_button()
    
    def update_ok_button(self):
        """Update OK button state based on selection"""
        if hasattr(self, 'button_box'):
            ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
            ok_button.setEnabled(bool(self.selected_directory))
    
    def accept(self):
        """Accept dialog and capture settings"""
        self.recursive_search = self.recursive_checkbox.isChecked()
        self.add_to_existing = self.add_to_existing_checkbox.isChecked()
        super().accept()


# Placeholder for other dialog classes that will be added in future iterations
class ProcessingDialog(QDialog):
    """Dialog for showing processing progress"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Processing...")
        self.setModal(True)
        self.resize(400, 200)
        
        layout = QVBoxLayout(self)
        
        self.status_label = QLabel("Initializing...")
        layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        layout.addWidget(self.progress_bar)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        layout.addWidget(self.cancel_button)
    
    def update_status(self, message: str):
        """Update the status message"""
        self.status_label.setText(message)
    
    def set_progress(self, value: int, maximum: int = 100):
        """Set progress bar value"""
        self.progress_bar.setRange(0, maximum)
        self.progress_bar.setValue(value)


# TODO: Add more dialog classes in the next iteration:
# - WorkspaceDirectoryManager
# - ChatDialog  
# - ChatWindow
# - VideoProcessingDialog
# - AllDescriptionsDialog
# - ModelManagerDialog

class ChatWindow(QDialog):
    """Dedicated chat window with message input and conversation history"""
    
    # Signal for when user sends a message
    message_sent = pyqtSignal(str, str)  # chat_id, message
    
    def __init__(self, chat_session, parent=None):
        super().__init__(parent)
        self.chat_session = chat_session
        self.chat_id = chat_session['id']
        
        self.setWindowTitle(f"Chat: {chat_session['name']}")
        self.setModal(False)  # Allow multiple chat windows
        self.resize(800, 600)
        
        # Make window resizable
        self.setMinimumSize(600, 400)
        
        self.setup_ui()
        self.load_conversation()
        
        # Set initial focus to input box
        self.input_box.setFocus()
    
    def setup_ui(self):
        """Set up the chat window UI"""
        layout = QVBoxLayout(self)
        
        # Header with chat info
        header_layout = QHBoxLayout()
        
        header_label = QLabel(f"Chat: {self.chat_session['name']}")
        header_label.setStyleSheet("font-weight: bold; font-size: 14px; padding: 5px;")
        header_layout.addWidget(header_label)
        
        info_label = QLabel(f"{self.chat_session['provider'].upper()} {self.chat_session['model']}")
        info_label.setStyleSheet("color: #666; font-size: 12px; padding: 5px;")
        header_layout.addWidget(info_label)
        
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Message input box (simplified for this extraction)
        self.input_box = AccessibleTextEdit()
        self.input_box.setAccessibleName("Message Input")
        self.input_box.setPlaceholderText("Type your message here...")
        self.input_box.setMaximumHeight(100)
        layout.addWidget(self.input_box)
        
        # Send button
        self.send_button = QPushButton("Send Message")
        self.send_button.clicked.connect(self.send_message)
        layout.addWidget(self.send_button)
        
        # History list (simplified)
        self.history_list = QListWidget()
        layout.addWidget(self.history_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)
    
    def send_message(self):
        """Send the current message"""
        message = self.input_box.toPlainText().strip()
        if message:
            self.message_sent.emit(self.chat_id, message)
            self.input_box.clear()
    
    def load_conversation(self):
        """Load conversation history (placeholder)"""
        pass