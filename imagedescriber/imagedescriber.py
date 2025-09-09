#!/usr/bin/env python3
"""
ImageDescriber - AI-Powered Image Description GUI

A Qt6-based standalone application for processing images and generating AI descriptions.
This app creates a document-based workspace where users can load directories of images,
process them individually or in batches, and manage multiple descriptions per image.

Features:
- Document-based workspace (save/load projects)
- Individual and batch image processing
- Multiple descriptions per image with editing/deletion
- Video frame extraction with nested display
- HEIC conversion support
- Menu-driven interface
- Built-in AI processing with configurable prompts
"""

import sys
import os
import json
import subprocess
import threading
import time
import base64
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime

try:
    import ollama
except ImportError:
    ollama = None

try:
    import cv2
except ImportError:
    cv2 = None

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QLabel, QTextEdit, QSplitter,
    QMenuBar, QMenu, QFileDialog, QMessageBox, QDialog, QDialogButtonBox,
    QComboBox, QProgressBar, QStatusBar, QTreeWidget, QTreeWidgetItem,
    QInputDialog, QPlainTextEdit, QCheckBox, QPushButton, QFormLayout,
    QSpinBox, QDoubleSpinBox, QRadioButton, QButtonGroup, QGroupBox, QLineEdit,
    QTextEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QMutex, QMutexLocker
from PyQt6.QtGui import (
    QAction, QKeySequence, QClipboard, QGuiApplication, QPixmap, QImage,
    QFont, QColor, QDoubleValidator, QIntValidator
)

# Document format for ImageDescriber workspace
WORKSPACE_VERSION = "1.0"


# ================================
# ACCESSIBILITY IMPROVEMENTS
# ================================

class AccessibleTreeWidget(QTreeWidget):
    """Enhanced QTreeWidget with better accessibility support"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAccessibilityMode(True)
    
    def setAccessibilityMode(self, enabled=True):
        """Enable enhanced accessibility features"""
        if enabled:
            # Ensure proper focus policy
            self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            
            # Enable better keyboard navigation
            self.setSelectionBehavior(QTreeWidget.SelectionBehavior.SelectRows)
            self.setUniformRowHeights(True)
            
            # Connect to selection changes for better announcements
            self.itemSelectionChanged.connect(self._announce_selection)
            
            # Connect to expand/collapse signals for state announcements
            self.itemExpanded.connect(self._announce_expanded)
            self.itemCollapsed.connect(self._announce_collapsed)
    
    def _announce_selection(self):
        """Provide enhanced announcements for screen readers"""
        current = self.currentItem()
        if current:
            # Get accessible description from the item
            accessible_desc = current.data(0, Qt.ItemDataRole.AccessibleDescriptionRole)
            if accessible_desc:
                # Set it as the widget's accessible description for immediate announcement
                self.setAccessibleDescription(f"Selected: {accessible_desc}")

    def _announce_expanded(self, item):
        """Provide announcement when an item is expanded."""
        if item:
            original_desc = item.data(0, Qt.ItemDataRole.AccessibleDescriptionRole) or item.text(0)
            # Clean up any previous state text
            if original_desc.startswith("Collapsed: "):
                original_desc = original_desc[11:]
            elif original_desc.startswith("Expanded: "):
                original_desc = original_desc[10:]
            
            # Prepend state to the description
            item.setData(0, Qt.ItemDataRole.AccessibleDescriptionRole, f"Expanded: {original_desc}")
            # Announce the change more forcefully by also updating the widget's description
            child_count = item.childCount()
            if child_count > 0:
                self.setAccessibleDescription(f"{original_desc} expanded, {child_count} items visible")
            else:
                self.setAccessibleDescription(f"{original_desc} expanded")

    def _announce_collapsed(self, item):
        """Provide announcement when an item is collapsed."""
        if item:
            original_desc = item.data(0, Qt.ItemDataRole.AccessibleDescriptionRole) or item.text(0)
            # Clean up previous state text before adding the new one
            if original_desc.startswith("Expanded: "):
                original_desc = original_desc[10:]
            elif original_desc.startswith("Collapsed: "):
                original_desc = original_desc[11:]
            
            # Prepend state to the description
            item.setData(0, Qt.ItemDataRole.AccessibleDescriptionRole, f"Collapsed: {original_desc}")
            # Announce the change with additional context
            child_count = item.childCount()
            if child_count > 0:
                self.setAccessibleDescription(f"{original_desc} collapsed, {child_count} items hidden")
            else:
                self.setAccessibleDescription(f"{original_desc} collapsed")

    def keyPressEvent(self, event):
        """Override to handle keyboard navigation for accessibility"""
        current = self.currentItem()
        
        if current and event.key() == Qt.Key.Key_Space:
            # Space bar toggles expand/collapse
            if current.childCount() > 0:
                if self.isItemExpanded(current):
                    self.collapseItem(current)
                else:
                    self.expandItem(current)
                event.accept()
                return
        elif current and event.key() == Qt.Key.Key_Return:
            # Enter key also toggles expand/collapse (alternative to space)
            if current.childCount() > 0:
                if self.isItemExpanded(current):
                    self.collapseItem(current)
                else:
                    self.expandItem(current)
                event.accept()
                return
        
        # For all other keys, use default behavior
        super().keyPressEvent(event)


class AccessibleNumericInput(QLineEdit):
    """Accessible numeric input that replaces QSpinBox/QDoubleSpinBox"""
    
    def __init__(self, parent=None, is_integer=False, minimum=None, maximum=None, suffix=""):
        super().__init__(parent)
        self.is_integer = is_integer
        self.suffix = suffix
        self._setup_validation(minimum, maximum)
        self._setup_accessibility()
        
    def _setup_validation(self, minimum, maximum):
        """Setup input validation"""
        if self.is_integer:
            validator = QIntValidator()
            if minimum is not None:
                validator.setBottom(int(minimum))
            if maximum is not None:
                validator.setTop(int(maximum))
        else:
            validator = QDoubleValidator()
            if minimum is not None:
                validator.setBottom(minimum)
            if maximum is not None:
                validator.setTop(maximum)
            validator.setDecimals(2)
        
        self.setValidator(validator)
        
    def _setup_accessibility(self):
        """Setup accessibility features"""
        # Improve focus policy and keyboard handling
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # Add placeholder text to help users understand the format
        if self.is_integer:
            self.setPlaceholderText(f"Enter number{self.suffix}")
        else:
            self.setPlaceholderText(f"Enter decimal number{self.suffix}")
    
    def setValue(self, value):
        """Set the numeric value"""
        if self.is_integer:
            self.setText(str(int(value)))
        else:
            self.setText(f"{value:.1f}")
    
    def value(self):
        """Get the numeric value"""
        text = self.text()
        if not text:
            return 0.0 if not self.is_integer else 0
        
        try:
            if self.is_integer:
                return int(text)
            else:
                return float(text)
        except ValueError:
            return 0.0 if not self.is_integer else 0


class AccessibleTextEdit(QPlainTextEdit):
    """Text edit with proper Tab key handling for accessibility"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_accessibility()
    
    def _setup_accessibility(self):
        """Setup accessibility and keyboard handling"""
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
    def keyPressEvent(self, event):
        """Override to handle Tab key properly for accessibility"""
        if event.key() == Qt.Key.Key_Tab:
            # Tab should move to next widget, not insert tab character
            # Use the parent widget's focus navigation
            parent = self.parent()
            if parent:
                parent.focusNextPrevChild(True)  # True = forward
            else:
                self.focusNextChild()
            event.accept()
        elif event.key() == Qt.Key.Key_Backtab:
            # Shift+Tab should move to previous widget
            parent = self.parent()
            if parent:
                parent.focusNextPrevChild(False)  # False = backward
            else:
                self.focusPreviousChild()
            event.accept()
        else:
            # For all other keys, use default behavior
            super().keyPressEvent(event)


# ================================
# EXISTING CLASSES (UNCHANGED)
# ================================


class ImageDescription:
    """Represents a single description for an image"""
    def __init__(self, text: str, model: str = "", prompt_style: str = "", 
                 created: str = "", custom_prompt: str = ""):
        self.text = text
        self.model = model
        self.prompt_style = prompt_style
        self.created = created or datetime.now().isoformat()
        self.custom_prompt = custom_prompt
        self.id = f"{int(time.time() * 1000)}"  # Unique ID
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "model": self.model,
            "prompt_style": self.prompt_style,
            "created": self.created,
            "custom_prompt": self.custom_prompt
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        desc = cls(
            text=data.get("text", ""),
            model=data.get("model", ""),
            prompt_style=data.get("prompt_style", ""),
            created=data.get("created", ""),
            custom_prompt=data.get("custom_prompt", "")
        )
        desc.id = data.get("id", desc.id)
        return desc


class ImageItem:
    """Represents an image or video in the workspace"""
    def __init__(self, file_path: str, item_type: str = "image"):
        self.file_path = file_path
        self.item_type = item_type  # "image", "video", "extracted_frame"
        self.descriptions: List[ImageDescription] = []
        self.batch_marked = False
        self.parent_video = None  # For extracted frames
        self.extracted_frames: List[str] = []  # For videos
        
    def add_description(self, description: ImageDescription):
        self.descriptions.append(description)
    
    def remove_description(self, desc_id: str):
        self.descriptions = [d for d in self.descriptions if d.id != desc_id]
    
    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "item_type": self.item_type,
            "descriptions": [d.to_dict() for d in self.descriptions],
            "batch_marked": self.batch_marked,
            "parent_video": self.parent_video,
            "extracted_frames": self.extracted_frames
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        item = cls(data["file_path"], data.get("item_type", "image"))
        item.descriptions = [ImageDescription.from_dict(d) for d in data.get("descriptions", [])]
        item.batch_marked = data.get("batch_marked", False)
        item.parent_video = data.get("parent_video")
        item.extracted_frames = data.get("extracted_frames", [])
        return item


class ImageWorkspace:
    """Document model for ImageDescriber workspace - Enhanced for multiple directories"""
    def __init__(self, new_workspace=False):
        self.version = WORKSPACE_VERSION
        self.directory_path = ""  # Keep for backward compatibility
        self.directory_paths: List[str] = []  # New: support multiple directories
        self.items: Dict[str, ImageItem] = {}
        self.created = datetime.now().isoformat()
        self.modified = self.created
        self.saved = new_workspace  # New workspaces start as saved
        
    def add_directory(self, directory_path: str):
        """Add a directory to the workspace"""
        abs_path = str(Path(directory_path).resolve())
        if abs_path not in self.directory_paths:
            self.directory_paths.append(abs_path)
            self.mark_modified()
            
        # Update legacy field for compatibility
        if not self.directory_path:
            self.directory_path = abs_path
    
    def remove_directory(self, directory_path: str):
        """Remove a directory from the workspace"""
        abs_path = str(Path(directory_path).resolve())
        if abs_path in self.directory_paths:
            self.directory_paths.remove(abs_path)
            self.mark_modified()
            
            # Remove items from this directory
            items_to_remove = [path for path, item in self.items.items() 
                             if Path(path).resolve().is_relative_to(Path(abs_path))]
            for item_path in items_to_remove:
                del self.items[item_path]
    
    def get_all_directories(self) -> List[str]:
        """Get all directories in workspace"""
        dirs = []
        if self.directory_path and self.directory_path not in dirs:
            dirs.append(self.directory_path)
        dirs.extend([d for d in self.directory_paths if d not in dirs])
        return dirs
        
    def add_item(self, item: ImageItem):
        self.items[item.file_path] = item
        self.mark_modified()
    
    def remove_item(self, file_path: str):
        if file_path in self.items:
            del self.items[file_path]
            self.mark_modified()
    
    def get_item(self, file_path: str) -> Optional[ImageItem]:
        return self.items.get(file_path)
    
    def mark_modified(self):
        self.modified = datetime.now().isoformat()
        self.saved = False
    
    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "directory_path": self.directory_path,  # Legacy compatibility
            "directory_paths": self.directory_paths,  # New multi-directory support
            "items": {path: item.to_dict() for path, item in self.items.items()},
            "created": self.created,
            "modified": self.modified
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        workspace = cls()
        workspace.version = data.get("version", WORKSPACE_VERSION)
        workspace.directory_path = data.get("directory_path", "")
        workspace.directory_paths = data.get("directory_paths", [])
        # Ensure backward compatibility
        if workspace.directory_path and workspace.directory_path not in workspace.directory_paths:
            workspace.directory_paths.append(workspace.directory_path)
        workspace.items = {path: ImageItem.from_dict(item_data) 
                          for path, item_data in data.get("items", {}).items()}
        workspace.created = data.get("created", workspace.created)
        workspace.modified = data.get("modified", workspace.modified)
        workspace.saved = True
        return workspace
        workspace.version = data.get("version", WORKSPACE_VERSION)
        workspace.directory_path = data.get("directory_path", "")
        workspace.items = {path: ImageItem.from_dict(item_data) 
                          for path, item_data in data.get("items", {}).items()}
        workspace.created = data.get("created", workspace.created)
        workspace.modified = data.get("modified", workspace.modified)
        workspace.saved = True
        return workspace


class ProcessingWorker(QThread):
    """Worker thread for AI processing"""
    progress_updated = pyqtSignal(str)
    processing_complete = pyqtSignal(str, str, str, str, str)  # file_path, description, model, prompt_style, custom_prompt
    processing_failed = pyqtSignal(str, str)  # file_path, error
    
    def __init__(self, file_path: str, model: str, prompt_style: str, custom_prompt: str = ""):
        super().__init__()
        self.file_path = file_path
        self.model = model
        self.prompt_style = prompt_style
        self.custom_prompt = custom_prompt
        
    def run(self):
        try:
            # Load prompt configuration
            config = self.load_prompt_config()
            
            # Get the actual prompt text
            if self.custom_prompt:
                prompt_text = self.custom_prompt
            else:
                # Check for both prompt_variations (actual config) and prompts (converted format)
                prompt_data = config.get("prompt_variations", config.get("prompts", {}))
                if self.prompt_style in prompt_data:
                    if isinstance(prompt_data[self.prompt_style], dict):
                        prompt_text = prompt_data[self.prompt_style].get("text", "Describe this image.")
                    else:
                        prompt_text = prompt_data[self.prompt_style]
                else:
                    prompt_text = "Describe this image."
            
            # Emit progress
            self.progress_updated.emit(f"Processing {Path(self.file_path).name} with {self.model}...")
            
            # Process the image with Ollama
            description = self.process_with_ollama(self.file_path, prompt_text)
            
            # Emit success
            self.processing_complete.emit(
                self.file_path, description, self.model, self.prompt_style, self.custom_prompt
            )
            
        except Exception as e:
            self.processing_failed.emit(self.file_path, str(e))
    
    def load_prompt_config(self) -> dict:
        """Load prompt configuration from the scripts directory"""
        try:
            # Try to find the config file
            if getattr(sys, 'frozen', False):
                config_path = Path(sys._MEIPASS) / "scripts" / "image_describer_config.json"
            else:
                config_path = Path(__file__).parent.parent / "scripts" / "image_describer_config.json"
            
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # Convert the config format to what we expect
                    if "prompt_variations" in config:
                        # Convert prompt_variations to our expected format
                        prompts = {}
                        for key, value in config["prompt_variations"].items():
                            prompts[key] = {"text": value}
                        config["prompts"] = prompts
                    return config
        except Exception as e:
            print(f"Failed to load config: {e}")
        
        # Return default config
        return {
            "prompts": {
                "detailed": {"text": "Provide a detailed description of this image."},
                "brief": {"text": "Briefly describe this image."},
                "creative": {"text": "Describe this image in a creative, engaging way."}
            }
        }
    
    def process_with_ollama(self, image_path: str, prompt: str) -> str:
        """Process image with Ollama"""
        if not ollama:
            raise Exception("Ollama not available")
        
        try:
            # Check if it's a HEIC file and convert if needed
            path_obj = Path(image_path)
            if path_obj.suffix.lower() in ['.heic', '.heif']:
                # Convert HEIC to JPEG first
                converted_path = self.convert_heic_to_jpeg(image_path)
                if converted_path:
                    image_path = converted_path
                else:
                    raise Exception("Failed to convert HEIC file")
            
            # Read and encode image with size limits
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # Check file size and resize if too large
            max_size = 10 * 1024 * 1024  # 10MB limit
            if len(image_data) > max_size:
                image_data = self.resize_image_data(image_data, max_size)
            
            # Encode to base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            print(f"Processing {path_obj.name} with model {self.model}")
            print(f"Image size: {len(image_data)} bytes")
            print(f"Prompt: {prompt[:100]}...")
            
            # Call Ollama with proper error handling
            response = ollama.chat(
                model=self.model,
                messages=[{
                    'role': 'user',
                    'content': prompt,
                    'images': [image_base64]
                }],
                options={
                    'temperature': 0.1,
                    'num_predict': 600
                }
            )
            
            if 'message' in response and 'content' in response['message']:
                content = response['message']['content']
                if content and content.strip():
                    return content.strip()
                else:
                    raise Exception("Empty response from model")
            else:
                raise Exception(f"Unexpected response format: {response}")
                
        except Exception as e:
            print(f"Ollama processing error: {str(e)}")
            print(f"Model: {self.model}")
            print(f"Image path: {image_path}")
            
            # Try to get more detailed error info
            try:
                import traceback
                traceback.print_exc()
            except:
                pass
            
            raise Exception(f"Ollama processing failed: {str(e)}")
    
    def convert_heic_to_jpeg(self, heic_path: str) -> str:
        """Convert HEIC file to JPEG"""
        try:
            from PIL import Image
            import pillow_heif
            
            # Register HEIF opener
            pillow_heif.register_heif_opener()
            
            # Open and convert
            image = Image.open(heic_path)
            if image.mode in ('RGBA', 'LA', 'P'):
                image = image.convert('RGB')
            
            # Create temporary JPEG file
            import tempfile
            temp_dir = Path(tempfile.gettempdir())
            temp_path = temp_dir / f"temp_{int(time.time())}_{Path(heic_path).stem}.jpg"
            
            # Resize if too large
            max_dimension = 2048
            if max(image.size) > max_dimension:
                image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
            
            image.save(temp_path, 'JPEG', quality=85, optimize=True)
            return str(temp_path)
            
        except Exception as e:
            print(f"HEIC conversion error: {e}")
            return None
    
    def resize_image_data(self, image_data: bytes, max_size: int) -> bytes:
        """Resize image data if it's too large"""
        try:
            from PIL import Image
            import io
            
            # Load image
            image = Image.open(io.BytesIO(image_data))
            
            # Calculate new size
            quality = 85
            while True:
                # Save with current quality
                output = io.BytesIO()
                if image.mode in ('RGBA', 'LA', 'P'):
                    image = image.convert('RGB')
                
                image.save(output, format='JPEG', quality=quality, optimize=True)
                output_data = output.getvalue()
                
                if len(output_data) <= max_size or quality <= 20:
                    return output_data
                
                quality -= 10
            
        except Exception as e:
            print(f"Image resize error: {e}")
            return image_data  # Return original if resize fails


class WorkflowProcessWorker(QThread):
    """Worker thread for running the proven workflow system"""
    progress_updated = pyqtSignal(str)
    workflow_complete = pyqtSignal(str, str)  # input_dir, output_dir
    workflow_failed = pyqtSignal(str)  # error
    
    def __init__(self, cmd, input_dir, output_dir):
        super().__init__()
        self.cmd = cmd
        self.input_dir = str(input_dir)
        self.output_dir = str(output_dir)
    
    def run(self):
        """Run the workflow command and monitor progress"""
        try:
            import subprocess
            
            # Start the workflow process
            self.progress_updated.emit("Starting workflow process...")
            
            process = subprocess.Popen(
                self.cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                universal_newlines=True
            )
            
            # Monitor output for progress
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    line = output.strip()
                    if line:
                        # Emit progress updates
                        self.progress_updated.emit(f"Workflow: {line}")
            
            # Check if process completed successfully
            return_code = process.poll()
            if return_code == 0:
                self.workflow_complete.emit(self.input_dir, self.output_dir)
            else:
                self.workflow_failed.emit(f"Workflow process failed with code {return_code}")
                
        except Exception as e:
            self.workflow_failed.emit(f"Error running workflow: {str(e)}")


class ConversionWorker(QThread):
    """Worker thread for file conversions"""
    progress_updated = pyqtSignal(str)
    conversion_complete = pyqtSignal(str, list)  # original_path, converted_paths
    conversion_failed = pyqtSignal(str, str)  # original_path, error
    
    def __init__(self, file_path: str, conversion_type: str):
        super().__init__()
        self.file_path = file_path
        self.conversion_type = conversion_type  # "heic" or "video"
        
    def run(self):
        try:
            if self.conversion_type == "heic":
                self.convert_heic()
            elif self.conversion_type == "video":
                self.extract_video_frames()
        except Exception as e:
            self.conversion_failed.emit(self.file_path, str(e))
    
    def convert_heic(self):
        """Convert HEIC image to JPEG"""
        try:
            from PIL import Image
            import pillow_heif
            
            self.progress_updated.emit(f"Converting {Path(self.file_path).name}...")
            
            # Register HEIF opener
            pillow_heif.register_heif_opener()
            
            # Open and convert
            image = Image.open(self.file_path)
            if image.mode in ('RGBA', 'LA', 'P'):
                image = image.convert('RGB')
            
            # Save as JPEG
            output_path = str(Path(self.file_path).with_suffix('.jpg'))
            image.save(output_path, 'JPEG', quality=95)
            
            self.conversion_complete.emit(self.file_path, [output_path])
            
        except Exception as e:
            self.conversion_failed.emit(self.file_path, f"HEIC conversion failed: {str(e)}")
    
    def extract_video_frames(self):
        """Extract frames from video"""
        try:
            import cv2
            
            self.progress_updated.emit(f"Extracting frames from {Path(self.file_path).name}...")
            
            cap = cv2.VideoCapture(self.file_path)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            # Extract frames at 1 frame per second
            extracted_paths = []
            frame_interval = max(1, int(fps))
            
            video_stem = Path(self.file_path).stem
            # Create frames in imagedescriptiontoolkit folder
            video_parent = Path(self.file_path).parent
            toolkit_dir = video_parent / "imagedescriptiontoolkit"
            video_dir = toolkit_dir / f"{video_stem}_frames"
            video_dir.mkdir(parents=True, exist_ok=True)
            
            frame_num = 0
            while frame_num < frame_count:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                ret, frame = cap.read()
                
                if ret:
                    frame_filename = f"{video_stem}_frame_{frame_num // frame_interval:04d}.jpg"
                    frame_path = video_dir / frame_filename
                    cv2.imwrite(str(frame_path), frame)
                    extracted_paths.append(str(frame_path))
                
                frame_num += frame_interval
            
            cap.release()
            self.conversion_complete.emit(self.file_path, extracted_paths)
            
        except Exception as e:
            self.conversion_failed.emit(self.file_path, f"Video frame extraction failed: {str(e)}")


class VideoProcessingWorker(QThread):
    """Worker thread for video processing with frame extraction and description"""
    
    progress_updated = pyqtSignal(str, str)  # message, details
    extraction_complete = pyqtSignal(str, list, dict)  # video_path, extracted_frames, processing_config  
    processing_failed = pyqtSignal(str, str)  # file_path, error_message
    
    def __init__(self, video_path: str, extraction_config: dict, processing_config: dict):
        super().__init__()
        self.video_path = video_path
        self.extraction_config = extraction_config
        self.processing_config = processing_config
    
    def run(self):
        """Extract frames from video and optionally process them"""
        try:
            self.progress_updated.emit("Extracting frames from video...", f"Processing: {Path(self.video_path).name}")
            
            # Extract frames based on configuration
            extracted_frames = self.extract_frames()
            
            if extracted_frames:
                self.progress_updated.emit(f"Extracted {len(extracted_frames)} frames", "Frame extraction complete")
                self.extraction_complete.emit(self.video_path, extracted_frames, self.processing_config)
            else:
                self.processing_failed.emit(self.video_path, "No frames were extracted from video")
                
        except Exception as e:
            self.processing_failed.emit(self.video_path, f"Video processing failed: {str(e)}")
    
    def extract_frames(self) -> list:
        """Extract frames from video based on configuration"""
        try:
            if not cv2:
                raise Exception("OpenCV (cv2) not available. Please install opencv-python.")
            
            cap = cv2.VideoCapture(self.video_path)
            if not cap.isOpened():
                raise Exception("Could not open video file")
            
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0
            
            # Create output directory in imagedescriptiontoolkit folder
            video_path = Path(self.video_path)
            toolkit_dir = video_path.parent / "imagedescriptiontoolkit"
            video_dir = toolkit_dir / f"{video_path.stem}_frames"
            video_dir.mkdir(parents=True, exist_ok=True)
            
            extracted_paths = []
            
            # Extract based on mode
            if self.extraction_config["extraction_mode"] == "time_interval":
                extracted_paths = self.extract_by_time_interval(cap, fps, video_dir)
            else:
                extracted_paths = self.extract_by_scene_detection(cap, fps, video_dir)
            
            cap.release()
            return extracted_paths
            
        except Exception as e:
            raise Exception(f"Frame extraction failed: {str(e)}")
    
    def extract_by_time_interval(self, cap, fps: float, output_dir: Path) -> list:
        """Extract frames at regular time intervals"""
        interval_seconds = self.extraction_config["time_interval_seconds"]
        start_time = self.extraction_config["start_time_seconds"]
        end_time = self.extraction_config.get("end_time_seconds")
        max_frames = self.extraction_config.get("max_frames_per_video")
        
        frame_interval = int(fps * interval_seconds)
        start_frame = int(fps * start_time)
        
        extracted_paths = []
        frame_num = start_frame
        extract_count = 0
        
        video_stem = Path(self.video_path).stem
        
        while True:
            if max_frames and extract_count >= max_frames:
                break
                
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ret, frame = cap.read()
            
            if not ret:
                break
            
            # Check end time limit
            current_time = frame_num / fps
            if end_time and current_time > end_time:
                break
            
            # Save frame
            frame_filename = f"{video_stem}_frame_{extract_count:04d}.jpg"
            frame_path = output_dir / frame_filename
            cv2.imwrite(str(frame_path), frame)
            extracted_paths.append(str(frame_path))
            
            extract_count += 1
            frame_num += frame_interval
        
        return extracted_paths
    
    def extract_by_scene_detection(self, cap, fps: float, output_dir: Path) -> list:
        """Extract frames based on scene changes"""
        # This is a simplified scene detection - in a full implementation,
        # you'd use more sophisticated algorithms
        
        threshold = self.extraction_config["scene_change_threshold"] / 100.0
        min_duration = self.extraction_config["min_scene_duration_seconds"]
        max_frames = self.extraction_config.get("max_frames_per_video")
        
        extracted_paths = []
        prev_frame = None
        last_extract_frame = -1
        min_frame_gap = int(fps * min_duration)
        frame_num = 0
        extract_count = 0
        
        video_stem = Path(self.video_path).stem
        
        while True:
            if max_frames and extract_count >= max_frames:
                break
                
            ret, frame = cap.read()
            if not ret:
                break
            
            # Calculate difference from previous frame
            if prev_frame is not None:
                # Convert to grayscale for comparison
                gray_current = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray_prev = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
                
                # Calculate mean squared difference
                diff = cv2.absdiff(gray_current, gray_prev)
                mean_diff = diff.mean() / 255.0
                
                # Check if scene change detected and minimum duration passed
                if (mean_diff > threshold and 
                    frame_num - last_extract_frame >= min_frame_gap):
                    
                    # Save frame
                    frame_filename = f"{video_stem}_scene_{extract_count:04d}.jpg"
                    frame_path = output_dir / frame_filename
                    cv2.imwrite(str(frame_path), frame)
                    extracted_paths.append(str(frame_path))
                    
                    last_extract_frame = frame_num
                    extract_count += 1
            
            prev_frame = frame.copy()
            frame_num += 1
        
        return extracted_paths


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
            self.add_to_existing_checkbox.setToolTip(f"Add to existing directories:\n" + 
                                                    "\n".join([f"{Path(d).name}" for d in existing_directories[:5]]))
        else:
            self.add_to_existing_checkbox.setToolTip("No existing directories in workspace")
            self.add_to_existing_checkbox.setEnabled(False)
        options_layout.addWidget(self.add_to_existing_checkbox)
        
        layout.addWidget(options_group)
        
        # Existing directories display
        if existing_directories:
            existing_group = QGroupBox(f"Current Workspace Directories ({len(existing_directories)})")
            existing_layout = QVBoxLayout(existing_group)
            
            for directory in existing_directories[:10]:  # Show max 10
                dir_item = QLabel(f"{Path(directory).name}")
                dir_item.setToolTip(directory)
                existing_layout.addWidget(dir_item)
            
            if len(existing_directories) > 10:
                more_label = QLabel(f"... and {len(existing_directories) - 10} more")
                more_label.setStyleSheet("color: gray; font-style: italic;")
                existing_layout.addWidget(more_label)
            
            layout.addWidget(existing_group)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | 
                                     QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        # Initially disable OK until directory is selected
        self.ok_button = button_box.button(QDialogButtonBox.StandardButton.Ok)
        self.ok_button.setEnabled(False)
        
        layout.addWidget(button_box)
    
    def browse_directory(self):
        """Browse for directory"""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Image Directory", str(Path.home())
        )
        
        if directory:
            self.selected_directory = directory
            self.dir_label.setText(f"{Path(directory).name}")
            self.dir_label.setToolTip(directory)
            self.ok_button.setEnabled(True)
    
    def accept(self):
        """Accept dialog and store settings"""
        self.recursive_search = self.recursive_checkbox.isChecked()
        self.add_to_existing = self.add_to_existing_checkbox.isChecked()
        super().accept()


class WorkspaceDirectoryManager(QDialog):
    """Dialog for managing multiple directories in workspace"""
    def __init__(self, workspace: 'ImageWorkspace', parent=None):
        super().__init__(parent)
        self.workspace = workspace
        self.setWindowTitle("Workspace Directory Manager")
        self.setModal(True)
        self.resize(700, 500)
        
        layout = QVBoxLayout(self)
        
        # Info header
        info_label = QLabel(f"Managing {len(self.workspace.items)} items across {len(self.workspace.get_all_directories())} directories")
        info_label.setStyleSheet("font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(info_label)
        
        # Directory list
        self.directory_list = QTreeWidget()
        self.directory_list.setHeaderLabels(["Directory", "Files", "Path"])
        self.directory_list.setAlternatingRowColors(True)
        self.directory_list.setRootIsDecorated(False)
        
        # Populate directory list
        self.populate_directory_list()
        
        layout.addWidget(self.directory_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.add_button = QPushButton("Add Directory...")
        self.add_button.clicked.connect(self.add_directory)
        button_layout.addWidget(self.add_button)
        
        self.remove_button = QPushButton("Remove Selected")
        self.remove_button.clicked.connect(self.remove_directory)
        self.remove_button.setEnabled(False)
        button_layout.addWidget(self.remove_button)
        
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_directory)
        button_layout.addWidget(self.refresh_button)
        
        button_layout.addStretch()
        
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
        
        # Selection handling
        self.directory_list.itemSelectionChanged.connect(self.on_selection_changed)
    
    def populate_directory_list(self):
        """Populate the directory list with current workspace directories"""
        self.directory_list.clear()
        
        for directory in self.workspace.get_all_directories():
            dir_path = Path(directory)
            
            # Count files in this directory
            file_count = sum(1 for item_path in self.workspace.items.keys() 
                           if Path(item_path).parent == dir_path or 
                              str(Path(item_path).resolve()).startswith(str(dir_path.resolve())))
            
            # Create tree item
            item = QTreeWidgetItem([
                dir_path.name,
                str(file_count),
                str(directory)
            ])
            
            # Set tooltips
            item.setToolTip(0, str(directory))
            item.setToolTip(1, f"{file_count} files from this directory")
            item.setToolTip(2, str(directory))
            
            self.directory_list.addTopLevelItem(item)
        
        # Resize columns to content
        for i in range(3):
            self.directory_list.resizeColumnToContents(i)
    
    def on_selection_changed(self):
        """Handle selection change"""
        has_selection = bool(self.directory_list.selectedItems())
        self.remove_button.setEnabled(has_selection and len(self.workspace.get_all_directories()) > 1)
    
    def add_directory(self):
        """Add a new directory"""
        dialog = DirectorySelectionDialog(self.workspace.get_all_directories(), self)
        dialog.add_to_existing_checkbox.setChecked(True)
        dialog.add_to_existing_checkbox.setEnabled(False)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            directory = dialog.selected_directory
            recursive = dialog.recursive_search
            
            if directory:
                # Add to workspace
                self.workspace.add_directory(directory)
                
                # Load images (this will be handled by the parent)
                self.parent().load_images_from_directory(directory, recursive=recursive)
                
                # Refresh the list
                self.populate_directory_list()
    
    def remove_directory(self):
        """Remove selected directory"""
        selected_items = self.directory_list.selectedItems()
        if not selected_items:
            return
        
        directory = selected_items[0].text(2)
        dir_name = Path(directory).name
        
        # Count files that will be removed
        files_to_remove = [path for path, item in self.workspace.items.items() 
                          if Path(path).resolve().is_relative_to(Path(directory).resolve())]
        
        # Confirm removal
        reply = QMessageBox.question(
            self, "Remove Directory",
            f"Remove directory '{dir_name}' from workspace?\n\n"
            f"This will remove {len(files_to_remove)} files from the workspace.\n"
            f"The actual files will not be deleted from disk.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.workspace.remove_directory(directory)
            self.populate_directory_list()
            
            # Update selection state
            self.on_selection_changed()
    
    def refresh_directory(self):
        """Refresh selected directory"""
        selected_items = self.directory_list.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "Refresh", 
                                  "Please select a directory to refresh.")
            return
        
        directory = selected_items[0].text(2)
        
        # Ask for recursive option
        reply = QMessageBox.question(
            self, "Refresh Directory",
            f"Refresh directory '{Path(directory).name}'?\n\n"
            f"Search subdirectories recursively?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Cancel:
            recursive = reply == QMessageBox.StandardButton.Yes
            
            # Reload images from this directory
            self.parent().load_images_from_directory(directory, recursive=recursive)
            
            # Refresh the list
            self.populate_directory_list()


class ProcessingDialog(QDialog):
    """Dialog for selecting processing options"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Processing Options")
        self.setModal(True)
        self.resize(400, 300)
        
        layout = QVBoxLayout(self)
        
        # Model selection
        layout.addWidget(QLabel("AI Model:"))
        self.model_combo = QComboBox()
        self.populate_models()
        layout.addWidget(self.model_combo)
        
        # Prompt style selection
        layout.addWidget(QLabel("Prompt Style:"))
        self.prompt_combo = QComboBox()
        self.populate_prompts()
        layout.addWidget(self.prompt_combo)
        
        # Custom prompt option
        self.custom_checkbox = QCheckBox("Use custom prompt")
        layout.addWidget(self.custom_checkbox)
        
        self.custom_prompt = AccessibleTextEdit()
        self.custom_prompt.setMaximumHeight(100)
        self.custom_prompt.setEnabled(False)
        self.custom_prompt.setAccessibleName("Custom Prompt")
        self.custom_prompt.setAccessibleDescription("Enter custom prompt text. Tab key moves to next field.")
        layout.addWidget(self.custom_prompt)
        
        self.custom_checkbox.toggled.connect(self.custom_prompt.setEnabled)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def populate_models(self):
        """Populate available Ollama models"""
        self.model_combo.clear()
        
        try:
            if ollama:
                # Get list of installed models
                models_response = ollama.list()
                available_models = []
                
                if 'models' in models_response:
                    for model in models_response['models']:
                        model_name = model.get('name', '')
                        if model_name:
                            available_models.append(model_name)
                            self.model_combo.addItem(model_name)
                
                # If no models found, add some common vision models as options
                if not available_models:
                    default_models = ['moondream', 'gemma3', 'llava']
                    for model in default_models:
                        self.model_combo.addItem(model)
                    
                    # Show warning
                    print("Warning: No Ollama models detected. Please install vision models with 'ollama pull <model_name>'")
                
                print(f"Found {len(available_models)} Ollama models: {available_models}")
                
            else:
                # Ollama not available, add default options
                default_models = ['moondream', 'gemma3', 'llava']
                for model in default_models:
                    self.model_combo.addItem(model)
                print("Warning: Ollama not available. Please install Ollama and vision models.")
                
        except Exception as e:
            print(f"Error loading Ollama models: {e}")
            # Add fallback models
            default_models = ['moondream', 'llava', 'llama3.2-vision', 'bakllava']
            for model in default_models:
                self.model_combo.addItem(model)
        
        # Set default model from config if available
        try:
            config = self.load_config()
            default_model = config.get("default_model", "moondream")
            
            # Find and select the default model
            for i in range(self.model_combo.count()):
                if self.model_combo.itemText(i) == default_model:
                    self.model_combo.setCurrentIndex(i)
                    break
        except Exception:
            pass
    
    def populate_prompts(self):
        """Populate prompt styles from config"""
        self.prompt_combo.clear()
        
        try:
            config = self.load_config()
            
            # Check for both prompt_variations (actual config) and prompts (converted format)
            prompt_data = config.get("prompt_variations", config.get("prompts", {}))
            
            if prompt_data:
                for prompt_name in prompt_data.keys():
                    self.prompt_combo.addItem(prompt_name)
                print(f"Loaded {len(prompt_data)} prompt styles: {list(prompt_data.keys())}")
            else:
                # Add defaults if no prompts found
                default_prompts = ["detailed", "concise", "Narrative", "artistic", "technical", "colorful", "social"]
                for prompt in default_prompts:
                    self.prompt_combo.addItem(prompt)
                print("Warning: No prompts found in config, using defaults")
            
            # Set default prompt style
            default_style = config.get("default_prompt_style", "Narrative")
            for i in range(self.prompt_combo.count()):
                if self.prompt_combo.itemText(i) == default_style:
                    self.prompt_combo.setCurrentIndex(i)
                    break
                    
        except Exception as e:
            print(f"Error loading prompts: {e}")
            # Add defaults if error
            default_prompts = ["detailed", "concise", "Narrative", "artistic", "technical", "colorful", "social"]
            for prompt in default_prompts:
                self.prompt_combo.addItem(prompt)
    
    def load_config(self):
        """Load configuration from scripts directory"""
        try:
            if getattr(sys, 'frozen', False):
                config_path = Path(sys._MEIPASS) / "scripts" / "image_describer_config.json"
            else:
                config_path = Path(__file__).parent.parent / "scripts" / "image_describer_config.json"
            
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Failed to load config: {e}")
        
        return {}
    
    def get_selections(self):
        """Get selected model, prompt style, and custom prompt"""
        model = self.model_combo.currentText()
        prompt_style = self.prompt_combo.currentText()
        custom_prompt = self.custom_prompt.toPlainText() if self.custom_checkbox.isChecked() else ""
        return model, prompt_style, custom_prompt


class VideoProcessingDialog(QDialog):
    """Dialog for configuring video frame extraction and processing options"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Video Processing Options")
        self.setModal(True)
        self.resize(500, 600)
        
        layout = QVBoxLayout(self)
        
        # Frame extraction options
        extraction_group = QGroupBox("Frame Extraction")
        extraction_layout = QFormLayout(extraction_group)
        
        # Extraction mode
        self.extraction_mode_group = QButtonGroup()
        self.time_interval_radio = QRadioButton("Time Interval")
        self.scene_detection_radio = QRadioButton("Scene Detection")
        self.time_interval_radio.setChecked(True)
        
        self.extraction_mode_group.addButton(self.time_interval_radio, 0)
        self.extraction_mode_group.addButton(self.scene_detection_radio, 1)
        
        extraction_layout.addRow("Extraction Mode:", self.time_interval_radio)
        extraction_layout.addRow("", self.scene_detection_radio)
        
        # Time interval settings
        self.time_interval = AccessibleNumericInput(minimum=0.1, maximum=3600.0, suffix=" seconds")
        self.time_interval.setValue(5.0)
        self.time_interval.setAccessibleName("Time Interval")
        self.time_interval.setAccessibleDescription("Interval between frame extractions in seconds")
        extraction_layout.addRow("Time Interval:", self.time_interval)
        
        # Scene detection settings
        self.scene_threshold = AccessibleNumericInput(minimum=1.0, maximum=100.0, suffix="%")
        self.scene_threshold.setValue(30.0)
        self.scene_threshold.setAccessibleName("Scene Change Threshold")
        self.scene_threshold.setAccessibleDescription("Percentage threshold for detecting scene changes")
        extraction_layout.addRow("Scene Change Threshold:", self.scene_threshold)
        
        self.min_scene_duration = AccessibleNumericInput(minimum=0.1, maximum=60.0, suffix=" seconds")
        self.min_scene_duration.setValue(1.0)
        self.min_scene_duration.setAccessibleName("Minimum Scene Duration")
        self.min_scene_duration.setAccessibleDescription("Minimum duration for a scene in seconds")
        extraction_layout.addRow("Min Scene Duration:", self.min_scene_duration)
        
        # Time range
        self.start_time = AccessibleNumericInput(minimum=0.0, maximum=86400.0, suffix=" seconds")
        self.start_time.setValue(0.0)
        self.start_time.setAccessibleName("Start Time")
        self.start_time.setAccessibleDescription("Start time for frame extraction in seconds")
        extraction_layout.addRow("Start Time:", self.start_time)
        
        self.end_time = AccessibleNumericInput(minimum=0.0, maximum=86400.0, suffix=" seconds")
        self.end_time.setValue(0.0)
        self.end_time.setAccessibleName("End Time")
        self.end_time.setAccessibleDescription("End time for frame extraction in seconds (0 or empty means end of video)")
        extraction_layout.addRow("End Time (0=end):", self.end_time)
        
        # Max frames limit
        self.max_frames = AccessibleNumericInput(is_integer=True, minimum=0, maximum=10000, suffix=" frames")
        self.max_frames.setValue(0)
        self.max_frames.setAccessibleName("Maximum Frames")
        self.max_frames.setAccessibleDescription("Maximum number of frames to extract (0 means no limit)")
        extraction_layout.addRow("Max Frames:", self.max_frames)
        
        layout.addWidget(extraction_group)
        
        # Processing options
        processing_group = QGroupBox("Processing Options")
        processing_layout = QFormLayout(processing_group)
        
        # Processing checkbox first
        self.process_after_extraction = QCheckBox("Process frames immediately after extraction")
        self.process_after_extraction.setChecked(True)
        processing_layout.addRow(self.process_after_extraction)
        
        # Model selection
        self.model_combo = QComboBox()
        processing_layout.addRow("Model:", self.model_combo)
        
        # Prompt selection
        self.prompt_combo = QComboBox()
        processing_layout.addRow("Prompt Style:", self.prompt_combo)
        
        # Custom prompt option
        self.custom_checkbox = QCheckBox("Use custom prompt")
        self.custom_checkbox.setChecked(False)  # Default unchecked
        processing_layout.addRow(self.custom_checkbox)
        
        # Custom prompt
        self.custom_prompt = AccessibleTextEdit()
        self.custom_prompt.setMaximumHeight(100)
        self.custom_prompt.setPlaceholderText("Enter custom prompt (used when 'Custom' is selected)")
        self.custom_prompt.setEnabled(False)  # Start disabled
        self.custom_prompt.setAccessibleName("Custom Prompt")
        self.custom_prompt.setAccessibleDescription("Enter custom prompt text. Tab key moves to next field.")
        processing_layout.addRow("Custom Prompt:", self.custom_prompt)
        
        # Connect checkbox to enable/disable custom prompt
        self.custom_checkbox.toggled.connect(self.custom_prompt.setEnabled)
        
        layout.addWidget(processing_group)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Enable/disable controls based on extraction mode
        self.extraction_mode_group.buttonToggled.connect(self.on_extraction_mode_changed)
        self.on_extraction_mode_changed()
    
    def on_extraction_mode_changed(self):
        """Update UI based on extraction mode"""
        time_mode = self.time_interval_radio.isChecked()
        
        self.time_interval.setEnabled(time_mode)
        self.scene_threshold.setEnabled(not time_mode)
        self.min_scene_duration.setEnabled(not time_mode)
    
    def get_extraction_config(self):
        """Get the extraction configuration"""
        return {
            "extraction_mode": "time_interval" if self.time_interval_radio.isChecked() else "scene_detection",
            "time_interval_seconds": self.time_interval.value(),
            "scene_change_threshold": self.scene_threshold.value(),
            "min_scene_duration_seconds": self.min_scene_duration.value(),
            "start_time_seconds": self.start_time.value(),
            "end_time_seconds": self.end_time.value() if self.end_time.value() > 0 else None,
            "max_frames_per_video": self.max_frames.value() if self.max_frames.value() > 0 else None,
            "image_quality": 95,
            "preserve_directory_structure": False,
            "skip_existing": False,
            "log_progress": True
        }
    
    def get_processing_config(self):
        """Get the processing configuration"""
        return {
            "model": self.model_combo.currentText(),
            "prompt_style": self.prompt_combo.currentText(),
            "custom_prompt": self.custom_prompt.toPlainText() if self.custom_checkbox.isChecked() else "",
            "process_immediately": self.process_after_extraction.isChecked()
        }
    
    def populate_models(self, models):
        """Populate the model combo box"""
        self.model_combo.clear()
        self.model_combo.addItems(models)
        # Set default to moondream if available
        if "moondream" in models:
            self.model_combo.setCurrentText("moondream")
    
    def populate_prompts(self, prompts):
        """Populate the prompt combo box"""
        self.prompt_combo.clear()
        self.prompt_combo.addItems(prompts)
        # Set default to Narrative if available
        if "Narrative" in prompts:
            self.prompt_combo.setCurrentText("Narrative")


class AllDescriptionsDialog(QDialog):
    """Dialog to show all descriptions in a single list for easy browsing"""
    
    def __init__(self, descriptions_data, parent=None):
        super().__init__(parent)
        self.descriptions_data = descriptions_data
        self.setWindowTitle("All Descriptions")
        self.setModal(True)
        self.resize(800, 600)
        
        layout = QVBoxLayout(self)
        
        # Instructions
        instructions = QLabel("Use arrow keys to navigate through all descriptions:")
        layout.addWidget(instructions)
        
        # List widget
        self.list_widget = QListWidget()
        self.list_widget.setAccessibleName("All Descriptions List")
        self.list_widget.setAccessibleDescription("List of all image descriptions. Use arrow keys to navigate.")
        
        # Populate list
        for desc_data in descriptions_data:
            item = QListWidgetItem(f"{desc_data['file_name']}: {desc_data['display_text'][:100]}...")
            item.setData(Qt.ItemDataRole.UserRole, desc_data)
            # Set full text for screen readers
            item.setData(Qt.ItemDataRole.AccessibleTextRole, 
                        f"{desc_data['file_name']}: {desc_data['display_text']}")
            self.list_widget.addItem(item)
        
        self.list_widget.itemSelectionChanged.connect(self.on_selection_changed)
        layout.addWidget(self.list_widget)
        
        # Text area for full description
        self.text_area = AccessibleTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.setAccessibleName("Full Description Text")
        layout.addWidget(self.text_area)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.close)
        layout.addWidget(button_box)
        
        # Set initial selection
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)
    
    def on_selection_changed(self):
        """Handle selection change in the list"""
        current_item = self.list_widget.currentItem()
        if current_item:
            desc_data = current_item.data(Qt.ItemDataRole.UserRole)
            self.text_area.setText(desc_data['description'].text)


class ImageDescriberGUI(QMainWindow):
    """Main ImageDescriber application window"""
    
    def __init__(self):
        super().__init__()
        
        # Application state
        self.workspace = ImageWorkspace()
        self.current_workspace_file = None
        self._skip_verification = True  # Skip verification by default
        
        # Processing state
        self.processing_workers: List[ProcessingWorker] = []
        self.conversion_workers: List[ConversionWorker] = []
        self.batch_queue: List[str] = []
        self.processing_items: set = set()  # Track items being processed
        
        # Batch processing tracking
        self.batch_total: int = 0
        self.batch_completed: int = 0
        self.batch_processing: bool = False
        
        # Filter settings
        self.filter_mode: str = "all"  # "all", "described", or "batch"
        
        # Navigation mode settings
        self.navigation_mode: str = "tree"  # "tree" or "master_detail"
        
        # Processing control
        self.stop_processing_requested: bool = False
        
        # UI setup
        self.setup_ui()
        self.setup_menus()
        self.setup_shortcuts()
        
        # Update window title
        self.update_window_title()
        
    def setup_ui(self):
        """Setup the user interface"""
        self.setWindowTitle("ImageDescriber")
        self.setMinimumSize(1000, 700)

        # Central widget with splitter
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        # Status bar
        self.status_bar = QStatusBar()
        self.status_bar.setAccessibleName("Status Bar")
        self.status_bar.setAccessibleDescription("Shows current operation status and progress.")
        self.status_bar.showMessage("Ready - Model verification disabled by default")
        self.setStatusBar(self.status_bar)

        # Create both UI layouts but show only one at a time
        self.setup_tree_view_ui(layout)
        self.setup_master_detail_ui(layout)
        
        # Start with tree view
        self.switch_navigation_mode("tree")

    def setup_tree_view_ui(self, parent_layout):
        """Setup the traditional tree view UI"""
        # Main splitter for tree view
        self.tree_splitter = QSplitter(Qt.Orientation.Horizontal)
        parent_layout.addWidget(self.tree_splitter)

        # Left panel - Image tree
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        left_layout.addWidget(QLabel("Images:"))
        self.image_list = QListWidget()
        self.image_list.setAccessibleName("Image List")
        self.image_list.setAccessibleDescription("List of images and video frames in the workspace. Use arrow keys to navigate, P to process selected image, B to mark for batch.")
        self.image_list.itemSelectionChanged.connect(self.on_image_selection_changed)
        # Enable proper focus tracking
        self.image_list.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        left_layout.addWidget(self.image_list)

        # Batch info
        self.batch_label = QLabel("Batch Queue: 0 items")
        left_layout.addWidget(self.batch_label)

        self.tree_splitter.addWidget(left_panel)

        # Right panel - Descriptions
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        right_layout.addWidget(QLabel("Descriptions:"))
        self.description_list = QListWidget()
        self.description_list.setAccessibleName("Description List")
        self.description_list.setAccessibleDescription("List of descriptions for the selected image. Use arrow keys to navigate and view different descriptions.")
        self.description_list.itemSelectionChanged.connect(self.on_description_selection_changed)
        # Enable proper focus tracking
        self.description_list.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        right_layout.addWidget(self.description_list)

        # Description text
        right_layout.addWidget(QLabel("Description Text:"))
        self.description_text = QTextEdit()
        self.description_text.setReadOnly(True)
        self.description_text.setAccessibleName("Description Text")
        self.description_text.setAccessibleDescription("Displays the full image description. Use arrow keys to navigate through the text.")
        # Enable text selection and copy with Ctrl+C (like viewer app)
        self.description_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard)
        # Set focus policy to ensure it can receive focus for screen readers
        self.description_text.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        # Set word wrap for better readability
        self.description_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        right_layout.addWidget(self.description_text)

        self.tree_splitter.addWidget(right_panel)

        # Set splitter proportions
        self.tree_splitter.setSizes([400, 600])

    def setup_master_detail_ui(self, parent_layout):
        """Setup the master-detail view UI"""
        # Main splitter for master-detail view
        self.master_detail_splitter = QSplitter(Qt.Orientation.Horizontal)
        parent_layout.addWidget(self.master_detail_splitter)

        # Left panel - Media list (videos + standalone images)
        media_panel = QWidget()
        media_layout = QVBoxLayout(media_panel)

        media_layout.addWidget(QLabel("Media Files:"))
        self.media_list = QListWidget()
        self.media_list.setAccessibleName("Media List")
        self.media_list.setAccessibleDescription("List of all media files (videos and images). Select to view frames or descriptions.")
        self.media_list.itemSelectionChanged.connect(self.on_media_selection_changed)
        self.media_list.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        media_layout.addWidget(self.media_list)

        # Batch info (shared with tree view)
        self.batch_label_md = QLabel("Batch Queue: 0 items")
        media_layout.addWidget(self.batch_label_md)

        self.master_detail_splitter.addWidget(media_panel)

        # Right side - Frames/Details and descriptions
        right_side = QWidget()
        right_side_layout = QVBoxLayout(right_side)

        # Frames/Details panel
        right_side_layout.addWidget(QLabel("Frames/Details:"))
        self.frames_list = QListWidget()
        self.frames_list.setAccessibleName("Frames List")
        self.frames_list.setAccessibleDescription("List of frames from selected video or details for selected image.")
        self.frames_list.itemSelectionChanged.connect(self.on_frame_selection_changed)
        self.frames_list.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        right_side_layout.addWidget(self.frames_list)

        # Descriptions panel (use list widget)
        right_side_layout.addWidget(QLabel("Descriptions:"))
        self.description_list_md = QListWidget()
        self.description_list_md.setAccessibleName("Description List")
        self.description_list_md.setAccessibleDescription("List of descriptions for the selected frame or image.")
        self.description_list_md.itemSelectionChanged.connect(self.on_description_selection_changed_md)
        self.description_list_md.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        right_side_layout.addWidget(self.description_list_md)

        # Description text (separate from tree view)
        right_side_layout.addWidget(QLabel("Description Text:"))
        self.description_text_md = QTextEdit()
        self.description_text_md.setReadOnly(True)
        self.description_text_md.setAccessibleName("Description Text")
        self.description_text_md.setAccessibleDescription("Displays the full description. Use arrow keys to navigate through the text.")
        self.description_text_md.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard)
        self.description_text_md.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.description_text_md.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        right_side_layout.addWidget(self.description_text_md)

        self.master_detail_splitter.addWidget(right_side)

        # Set splitter proportions (media list smaller, details larger)
        self.master_detail_splitter.setSizes([300, 700])

    def switch_navigation_mode(self, mode):
        """Switch between tree view and master-detail view"""
        self.navigation_mode = mode
        
        # Update menu checkboxes (only if they exist - they're created in setup_menus)
        if hasattr(self, 'tree_view_action'):
            self.tree_view_action.setChecked(mode == "tree")
        if hasattr(self, 'master_detail_action'):
            self.master_detail_action.setChecked(mode == "master_detail")
        
        if mode == "tree":
            self.tree_splitter.setVisible(True)
            self.master_detail_splitter.setVisible(False)
            # Update current data
            self.refresh_view()
        elif mode == "master_detail":
            self.tree_splitter.setVisible(False)
            self.master_detail_splitter.setVisible(True)
            # Update master-detail view
            self.refresh_master_detail_view()

    def setup_menus(self):
        """Setup application menus"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        new_action = QAction("New Workspace", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self.new_workspace)
        file_menu.addAction(new_action)
        
        open_action = QAction("Open Workspace...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_workspace)
        file_menu.addAction(open_action)
        
        save_action = QAction("Save Workspace", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_workspace)
        file_menu.addAction(save_action)
        
        save_as_action = QAction("Save Workspace As...", self)
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_action.triggered.connect(self.save_workspace_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        load_dir_action = QAction("Load Image Directory...", self)
        load_dir_action.triggered.connect(self.load_image_directory)
        file_menu.addAction(load_dir_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Workspace menu
        workspace_menu = menubar.addMenu("Workspace")
        
        manage_dirs_action = QAction("Manage Directories...", self)
        manage_dirs_action.triggered.connect(self.manage_directories)
        manage_dirs_action.setToolTip("Add, remove, or view directories in workspace")
        workspace_menu.addAction(manage_dirs_action)
        
        workspace_menu.addSeparator()
        
        add_dir_action = QAction("Add Directory...", self)
        add_dir_action.triggered.connect(self.add_directory)
        add_dir_action.setToolTip("Add another directory to current workspace")
        workspace_menu.addAction(add_dir_action)
        
        # Processing menu
        process_menu = menubar.addMenu("Processing")
        
        process_sel_action = QAction("Process Selected (P)", self)
        process_sel_action.setShortcut(QKeySequence("P"))
        process_sel_action.triggered.connect(self.process_selected)
        process_menu.addAction(process_sel_action)
        
        batch_mark_action = QAction("Mark for Batch (B)", self)
        batch_mark_action.setShortcut(QKeySequence("B"))
        batch_mark_action.triggered.connect(self.toggle_batch_mark)
        process_menu.addAction(batch_mark_action)
        
        batch_process_action = QAction("Process Batch", self)
        batch_process_action.triggered.connect(self.process_batch)
        process_menu.addAction(batch_process_action)
        
        clear_batch_action = QAction("Clear Batch Processing", self)
        clear_batch_action.triggered.connect(self.clear_batch_selection)
        process_menu.addAction(clear_batch_action)
        
        self.stop_processing_action = QAction("Stop Processing", self)
        self.stop_processing_action.setEnabled(False)  # Disabled by default
        self.stop_processing_action.triggered.connect(self.stop_processing)
        process_menu.addAction(self.stop_processing_action)
        
        process_menu.addSeparator()
        
        skip_verification_action = QAction("Skip Model Verification", self)
        skip_verification_action.setCheckable(True)
        skip_verification_action.setChecked(True)  # Default to checked (skip verification)
        skip_verification_action.triggered.connect(self.toggle_skip_verification)
        process_menu.addAction(skip_verification_action)
        
        process_menu.addSeparator()
        
        convert_heic_action = QAction("Convert HEIC Files", self)
        convert_heic_action.triggered.connect(self.convert_heic_files)
        process_menu.addAction(convert_heic_action)
        
        extract_frames_action = QAction("Extract Video Frames", self)
        extract_frames_action.triggered.connect(self.extract_video_frames)
        process_menu.addAction(extract_frames_action)
        
        process_menu.addSeparator()
        
        add_all_to_batch_action = QAction("Add All to Batch", self)
        add_all_to_batch_action.triggered.connect(self.add_all_to_batch)
        process_menu.addAction(add_all_to_batch_action)
        
        # Descriptions menu
        desc_menu = menubar.addMenu("Descriptions")
        
        add_manual_desc_action = QAction("Add Manual Description", self)
        add_manual_desc_action.setShortcut(QKeySequence("M"))
        add_manual_desc_action.triggered.connect(self.add_manual_description)
        desc_menu.addAction(add_manual_desc_action)
        
        followup_question_action = QAction("Ask Follow-up Question", self)
        followup_question_action.setShortcut(QKeySequence("F"))
        followup_question_action.triggered.connect(self.ask_followup_question)
        desc_menu.addAction(followup_question_action)
        
        desc_menu.addSeparator()
        
        edit_desc_action = QAction("Edit Description", self)
        edit_desc_action.triggered.connect(self.edit_description)
        desc_menu.addAction(edit_desc_action)
        
        delete_desc_action = QAction("Delete Description", self)
        delete_desc_action.triggered.connect(self.delete_description)
        desc_menu.addAction(delete_desc_action)
        
        copy_desc_action = QAction("Copy Description", self)
        copy_desc_action.triggered.connect(self.copy_description)
        desc_menu.addAction(copy_desc_action)
        
        copy_image_action = QAction("Copy Image", self)
        copy_image_action.triggered.connect(self.copy_image)
        desc_menu.addAction(copy_image_action)
        
        copy_path_action = QAction("Copy Image Path", self)
        copy_path_action.triggered.connect(self.copy_image_path)
        desc_menu.addAction(copy_path_action)
        
        # View menu
        view_menu = menubar.addMenu("View")
        
        refresh_action = QAction("Refresh", self)
        refresh_action.setShortcut(QKeySequence.StandardKey.Refresh)
        refresh_action.triggered.connect(self.refresh_view)
        view_menu.addAction(refresh_action)
        
        view_menu.addSeparator()
        
        # Filter submenu
        filter_menu = view_menu.addMenu("Filter")
        
        self.filter_all_action = QAction("Show All", self)
        self.filter_all_action.setCheckable(True)
        self.filter_all_action.setChecked(True)
        self.filter_all_action.triggered.connect(lambda: self.set_filter("all"))
        filter_menu.addAction(self.filter_all_action)
        
        self.filter_described_action = QAction("Show Described Only", self)
        self.filter_described_action.setCheckable(True)
        self.filter_described_action.triggered.connect(lambda: self.set_filter("described"))
        filter_menu.addAction(self.filter_described_action)
        
        self.filter_batch_action = QAction("Show Batch Items Only", self)
        self.filter_batch_action.setCheckable(True)
        self.filter_batch_action.triggered.connect(lambda: self.set_filter("batch"))
        filter_menu.addAction(self.filter_batch_action)
        
        view_menu.addSeparator()
        
        # Navigation mode submenu
        navigation_menu = view_menu.addMenu("Navigation Mode")
        
        self.tree_view_action = QAction("Tree View", self)
        self.tree_view_action.setCheckable(True)
        self.tree_view_action.setChecked(True)  # Default mode
        self.tree_view_action.triggered.connect(lambda: self.switch_navigation_mode("tree"))
        navigation_menu.addAction(self.tree_view_action)
        
        # Master-Detail View temporarily hidden but code preserved for future use
        # self.master_detail_action = QAction("Master-Detail View", self)
        # self.master_detail_action.setCheckable(True)
        # self.master_detail_action.triggered.connect(lambda: self.switch_navigation_mode("master_detail"))
        # navigation_menu.addAction(self.master_detail_action)
        
        view_menu.addSeparator()
        
        # Show all descriptions in list
        show_all_descriptions_action = QAction("Show All Descriptions in List", self)
        show_all_descriptions_action.triggered.connect(self.show_all_descriptions_dialog)
        view_menu.addAction(show_all_descriptions_action)
    
    def setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        # Additional shortcuts not in menus
        pass
    
    def update_window_title(self, custom_status=None):
        """Update the window title with optional custom status message"""
        # Start with filter status
        filter_display = {
            "all": "All",
            "described": "Described", 
            "batch": "Batch"
        }
        title = f"[{filter_display.get(self.filter_mode, 'All')}] ImageDescriber"
        
        if self.current_workspace_file:
            title += f" - {Path(self.current_workspace_file).name}"
            if not self.workspace.saved:
                title += " *"
        else:
            # Show directory information
            all_dirs = self.workspace.get_all_directories()
            if len(all_dirs) == 1:
                title += f" - {Path(all_dirs[0]).name}"
            elif len(all_dirs) > 1:
                title += f" - {len(all_dirs)} directories"
            
            if not self.workspace.saved:
                title += " *"
        
        # Add processing status - use custom status if provided
        if custom_status:
            title += f" - {custom_status}"
        elif self.batch_processing:
            title += f" - Batch Processing: {self.batch_completed} of {self.batch_total}"
        elif self.processing_items:
            # Show individual processing status
            num_processing = len(self.processing_items)
            if num_processing == 1:
                title += " - Processing 1 item..."
            else:
                title += f" - Processing {num_processing} items..."
        
        self.setWindowTitle(title)
    
    # Workspace management methods
    def new_workspace(self):
        """Create a new workspace"""
        if not self.workspace.saved:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "You have unsaved changes. Continue without saving?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
        
        self.workspace = ImageWorkspace(new_workspace=True)  # Explicitly mark as new workspace
        self.current_workspace_file = None
        self.batch_queue.clear()
        self.image_list.clear()
        self.description_list.clear()
        self.description_text.clear()
        self.update_window_title()
        self.update_batch_label()
        
    def open_workspace(self):
        """Open an existing workspace"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Workspace", "", "ImageDescriber Workspace (*.idw);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.workspace = ImageWorkspace.from_dict(data)
                self.current_workspace_file = file_path
                self.batch_queue.clear()
                
                # Load the workspace content
                self.refresh_view()
                self.update_window_title()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open workspace:\n{str(e)}")
    
    def save_workspace(self):
        """Save the current workspace"""
        if self.current_workspace_file:
            self.save_workspace_to_file(self.current_workspace_file)
        else:
            self.save_workspace_as()
    
    def save_workspace_as(self):
        """Save the workspace with a new name"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Workspace As", "", "ImageDescriber Workspace (*.idw);;All Files (*)"
        )
        
        if file_path:
            if not file_path.endswith('.idw'):
                file_path += '.idw'
            self.save_workspace_to_file(file_path)
            self.current_workspace_file = file_path
            self.update_window_title()
    
    def save_workspace_to_file(self, file_path: str):
        """Save workspace to specific file"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.workspace.to_dict(), f, indent=2)
            
            self.workspace.saved = True
            self.update_window_title()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save workspace:\n{str(e)}")
    
    def load_image_directory(self):
        """Load images from a directory with options for recursive search"""
        # Create custom dialog for directory selection with options
        dialog = DirectorySelectionDialog(self.workspace.get_all_directories(), self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            directory = dialog.selected_directory
            recursive = dialog.recursive_search
            add_to_existing = dialog.add_to_existing
            
            if directory:
                if not add_to_existing:
                    # Clear existing directories if not adding
                    self.workspace.directory_paths.clear()
                    self.workspace.items.clear()
                
                self.workspace.add_directory(directory)
                self.load_images_from_directory(directory, recursive=recursive)
                self.refresh_view()
                self.update_window_title()
    
    def load_images_from_directory(self, directory: str, recursive: bool = False):
        """Load all images from directory into workspace
        
        Args:
            directory: Directory path to scan
            recursive: If True, search subdirectories recursively
        """
        directory_path = Path(directory)
        
        # Supported extensions
        image_exts = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.heic', '.heif'}
        video_exts = {'.mp4', '.mov', '.avi', '.mkv', '.wmv'}
        all_exts = image_exts | video_exts
        
        # Count files for progress tracking
        file_paths = []
        if recursive:
            # Use rglob for recursive search
            for ext in all_exts:
                file_paths.extend(directory_path.rglob(f"*{ext}"))
        else:
            # Use iterdir for single directory
            file_paths = [f for f in directory_path.iterdir() 
                         if f.is_file() and f.suffix.lower() in all_exts]
        
        # Show progress dialog for large operations
        if len(file_paths) > 10:
            from PyQt6.QtWidgets import QProgressDialog
            progress = QProgressDialog(f"Loading images from {directory_path.name}...", 
                                     "Cancel", 0, len(file_paths), self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.show()
        else:
            progress = None
        
        loaded_count = 0
        for i, file_path in enumerate(file_paths):
            if progress and progress.wasCanceled():
                break
                
            if str(file_path) not in self.workspace.items:
                item_type = "video" if file_path.suffix.lower() in video_exts else "image"
                item = ImageItem(str(file_path), item_type)
                self.workspace.add_item(item)
                loaded_count += 1
            
            if progress:
                progress.setValue(i + 1)
                QApplication.processEvents()
        
        if progress:
            progress.close()
        
        # Show summary
        search_type = "recursively" if recursive else "in directory"
        QMessageBox.information(self, "Directory Loaded", 
                               f"Loaded {loaded_count} new files {search_type}\n"
                               f"Total files in workspace: {len(self.workspace.items)}")
        
        self.workspace.mark_modified()
    
    def add_directory(self):
        """Add another directory to the current workspace"""
        dialog = DirectorySelectionDialog(self.workspace.get_all_directories(), self)
        dialog.add_to_existing_checkbox.setChecked(True)
        dialog.add_to_existing_checkbox.setEnabled(False)  # Force adding to existing
        dialog.setWindowTitle("Add Directory to Workspace")
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            directory = dialog.selected_directory
            recursive = dialog.recursive_search
            
            if directory:
                self.workspace.add_directory(directory)
                self.load_images_from_directory(directory, recursive=recursive)
                self.refresh_view()
                self.update_window_title()
    
    def manage_directories(self):
        """Show dialog to manage workspace directories"""
        dialog = WorkspaceDirectoryManager(self.workspace, self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Refresh view if directories were modified
            self.refresh_view()
            self.update_window_title()
    
    # UI update methods
    def refresh_view(self):
        """Refresh the image list view"""
        self.image_list.clear()
        
        for file_path, item in self.workspace.items.items():
            # Skip extracted frames - they'll be shown as children
            if item.item_type == "extracted_frame":
                continue
            
            # Apply filter
            if self.filter_mode == "described" and not item.descriptions:
                continue
            elif self.filter_mode == "batch" and not item.batch_marked:
                continue
                
            # Create top-level item - start with just the filename
            file_name = Path(file_path).name
            display_name = file_name
            
            # Build prefix indicators in order
            prefix_parts = []
            
            # 1. Batch marker
            if item.batch_marked:
                prefix_parts.append("b")
            
            # 2. Description count (only if descriptions exist)
            if item.descriptions:
                desc_count = len(item.descriptions)
                prefix_parts.append(f"d{desc_count}")
                
            # 3. Processing indicator
            if file_path in self.processing_items:
                prefix_parts.append("p")
                
            # 4. Video extraction status
            if item.item_type == "video" and item.extracted_frames:
                frame_count = len(item.extracted_frames)
                prefix_parts.append(f"E{frame_count}")
            
            # Combine prefix and filename
            if prefix_parts:
                prefix = "".join(prefix_parts)
                display_name = f"{prefix} {file_name}"
            
            # Create list item
            list_item = QListWidgetItem(display_name)
            list_item.setData(Qt.ItemDataRole.UserRole, file_path)
            
            # Mark batch items with accessible colors
            if item.batch_marked:
                # Use light blue background (#E3F2FD) which provides good contrast with black text
                list_item.setBackground(QColor(227, 242, 253))  # Light blue
            
            self.image_list.addItem(list_item)
            
            # Add extracted frames as children for videos
            if item.item_type == "video" and item.extracted_frames:
                for frame_path in item.extracted_frames:
                    frame_name = Path(frame_path).name
                    
                    # Build frame prefix indicators
                    frame_prefix_parts = []
                    
                    # Check if frame has descriptions
                    frame_workspace_item = self.workspace.get_item(frame_path)
                    if frame_workspace_item and frame_workspace_item.descriptions:
                        desc_count = len(frame_workspace_item.descriptions)
                        frame_prefix_parts.append(f"d{desc_count}")
                    
                    # Add processing indicator for frame
                    if frame_path in self.processing_items:
                        frame_prefix_parts.append("p")
                    
                    # Build display name with indentation
                    if frame_prefix_parts:
                        prefix = "".join(frame_prefix_parts)
                        frame_display = f"    {prefix} {frame_name}"
                    else:
                        frame_display = f"    {frame_name}"
                    
                    frame_item = QListWidgetItem(frame_display)
                    frame_item.setData(Qt.ItemDataRole.UserRole, frame_path)
                    
                    # Mark batch frames with same color as parent
                    if frame_workspace_item and frame_workspace_item.batch_marked:
                        frame_item.setBackground(QColor(227, 242, 253))  # Light blue
                    
                    self.image_list.addItem(frame_item)
        
        self.update_batch_label()
        
        # Also refresh master-detail view if it's the current mode
        if self.navigation_mode == "master_detail":
            self.refresh_master_detail_view()
    
    def update_batch_label(self):
        """Update the batch queue label"""
        batch_count = sum(1 for item in self.workspace.items.values() if item.batch_marked)
        self.batch_label.setText(f"Batch Queue: {batch_count} items")
        # Also update master-detail batch label
        if hasattr(self, 'batch_label_md'):
            self.batch_label_md.setText(f"Batch Queue: {batch_count} items")

    def refresh_master_detail_view(self):
        """Refresh the master-detail view"""
        # Clear media list
        self.media_list.clear()
        
        # Populate media list with videos and standalone images
        for file_path, item in self.workspace.items.items():
            # Skip extracted frames - they'll be shown in frames list
            if item.item_type == "extracted_frame":
                continue
                
            # Apply filter
            if self.filter_mode == "described" and not item.descriptions:
                continue
            elif self.filter_mode == "batch" and not item.batch_marked:
                continue
            
            # Create list item
            file_name = Path(file_path).name
            display_name = file_name
            accessibility_desc = file_name
            
            # Add type indicator
            if item.item_type == "video":
                accessibility_desc = f"Video: {accessibility_desc}"
                # Add frame count info
                if item.extracted_frames:
                    frame_count = len(item.extracted_frames)
                    display_name += f" ({frame_count} frames)"
                    accessibility_desc += f" with {frame_count} extracted frames"
            else:
                accessibility_desc = f"Image: {accessibility_desc}"
            
            # Add processing indicator
            if file_path in self.processing_items:
                accessibility_desc = f"Processing: {accessibility_desc}"
            
            # Add description count
            if item.descriptions:
                desc_count = len(item.descriptions)
                display_name += f" ({desc_count} desc)"
                accessibility_desc += f" with {desc_count} descriptions"
            else:
                accessibility_desc += " with no descriptions"
            
            # Add batch indicator to accessibility description only
            if item.batch_marked:
                accessibility_desc = f"Batch marked: {accessibility_desc}"
            
            list_item = QListWidgetItem(display_name)
            list_item.setData(Qt.ItemDataRole.UserRole, file_path)
            list_item.setData(Qt.ItemDataRole.AccessibleDescriptionRole, accessibility_desc)
            self.media_list.addItem(list_item)
        
        # Clear frames list and descriptions initially
        self.frames_list.clear()
        self.description_list_md.clear()
        self.description_text_md.clear()
        
        self.update_batch_label()

    def on_media_selection_changed(self):
        """Handle media selection change in master-detail view"""
        current_item = self.media_list.currentItem()
        if not current_item:
            self.frames_list.clear()
            self.description_tree_md.clear()
            self.description_text_md.clear()
            return
            
        file_path = current_item.data(Qt.ItemDataRole.UserRole)
        workspace_item = self.workspace.get_item(file_path)
        
        if not workspace_item:
            return
        
        # Clear frames list and descriptions
        self.frames_list.clear()
        self.description_list_md.clear()
        self.description_text_md.clear()
        
        if workspace_item.item_type == "video":
            # Show extracted frames
            for frame_path in workspace_item.extracted_frames:
                frame_item = self.workspace.get_item(frame_path)
                if not frame_item:
                    continue
                    
                frame_name = Path(frame_path).name
                display_name = frame_name
                accessibility_desc = f"Frame: {frame_name}"
                
                # Add processing indicator
                if frame_path in self.processing_items:
                    accessibility_desc = f"Processing: {accessibility_desc}"
                
                # Add description count
                if frame_item.descriptions:
                    desc_count = len(frame_item.descriptions)
                    display_name += f" ({desc_count} desc)"
                    accessibility_desc += f" with {desc_count} descriptions"
                else:
                    accessibility_desc += " with no descriptions"
                
                list_item = QListWidgetItem(display_name)
                list_item.setData(Qt.ItemDataRole.UserRole, frame_path)
                list_item.setData(Qt.ItemDataRole.AccessibleDescriptionRole, accessibility_desc)
                self.frames_list.addItem(list_item)
        else:
            # For standalone images, show the image itself in frames list
            file_name = Path(file_path).name
            display_name = file_name
            accessibility_desc = f"Image: {file_name}"
            
            # Add processing indicator
            if file_path in self.processing_items:
                accessibility_desc = f"Processing: {accessibility_desc}"
            
            # Add description count
            if workspace_item.descriptions:
                desc_count = len(workspace_item.descriptions)
                display_name += f" ({desc_count} desc)"
                accessibility_desc += f" with {desc_count} descriptions"
            else:
                accessibility_desc += " with no descriptions"
            
            list_item = QListWidgetItem(display_name)
            list_item.setData(Qt.ItemDataRole.UserRole, file_path)
            list_item.setData(Qt.ItemDataRole.AccessibleDescriptionRole, accessibility_desc)
            self.frames_list.addItem(list_item)
            
            # Auto-select the image to show its descriptions
            self.frames_list.setCurrentItem(list_item)

    def on_frame_selection_changed(self):
        """Handle frame selection change in master-detail view"""
        current_item = self.frames_list.currentItem()
        if not current_item:
            self.description_list_md.clear()
            self.description_text_md.clear()
            return
            
        file_path = current_item.data(Qt.ItemDataRole.UserRole)
        self.load_descriptions_for_image_md(file_path)

    def on_description_selection_changed_md(self):
        """Handle description selection change in master-detail view"""
        current_item = self.description_list_md.currentItem()
        if current_item:
            desc_id = current_item.data(Qt.ItemDataRole.UserRole)
            
            # Find the description
            frame_item = self.frames_list.currentItem()
            if frame_item:
                file_path = frame_item.data(Qt.ItemDataRole.UserRole)
                workspace_item = self.workspace.get_item(file_path)
                
                if workspace_item:
                    for desc in workspace_item.descriptions:
                        if desc.id == desc_id:
                            # Format text for better screen reader accessibility
                            formatted_text = self.format_description_for_accessibility(desc.text)
                            self.description_text_md.setPlainText(formatted_text)
                            break
        else:
            self.description_text_md.clear()

    def load_descriptions_for_image_md(self, file_path: str):
        """Load descriptions for the selected image in master-detail view"""
        self.description_list_md.clear()
        self.description_text_md.clear()
        
        workspace_item = self.workspace.get_item(file_path)
        if not workspace_item or not workspace_item.descriptions:
            return
        
        # Load descriptions (same logic as tree view but simplified for list)
        for i, desc in enumerate(workspace_item.descriptions):
            # Show model and prompt type
            model_text = desc.model if desc.model else "Unknown Model"
            
            if desc.prompt_style == "follow-up":
                prompt_text = "Follow-up"
            elif desc.prompt_style == "manual":
                prompt_text = "Manual"
            elif desc.custom_prompt and desc.prompt_style == "custom":
                prompt_text = "Custom"
            elif desc.prompt_style:
                prompt_text = desc.prompt_style.title()
            else:
                prompt_text = "Default"
            
            # Truncate description for display
            desc_preview = desc.text[:50] + "..." if len(desc.text) > 50 else desc.text
            desc_preview = desc_preview.replace('\n', ' ')  # Remove newlines for display
            
            # Handle date formatting
            if hasattr(desc.created, 'strftime'):
                created_date = desc.created.strftime("%Y-%m-%d %H:%M")
            else:
                created_date = desc.created.split('T')[0] if 'T' in desc.created else desc.created
            
            display_text = f"{model_text} {prompt_text}: {desc_preview}"
            list_item = QListWidgetItem(display_text)
            list_item.setData(Qt.ItemDataRole.UserRole, desc.id)
            
            # Set accessibility text
            list_item.setData(Qt.ItemDataRole.AccessibleTextRole,
                            f"{model_text} {prompt_text}: {desc.text}. Created {created_date}")
            list_item.setData(Qt.ItemDataRole.AccessibleDescriptionRole,
                            f"{model_text} {prompt_text}")
            
            self.description_list_md.addItem(list_item)
        
        # Select first description if available
        if self.description_list_md.count() > 0:
            self.description_list_md.setCurrentRow(0)
    
    def clear_batch_selection(self):
        """Clear all batch marked items"""
        for item in self.workspace.items.values():
            item.batch_marked = False
        self.update_batch_label()
        self.refresh_view()
    
    def show_batch_completion_dialog(self, total_processed: int, has_errors: bool = False):
        """Show batch completion confirmation dialog"""
        if has_errors:
            title = "Batch Processing Finished with Errors"
            message = f"Batch processing completed with some errors.\n{total_processed} items were processed.\n\nWould you like to clear the batch selection?"
        else:
            title = "Batch Processing Complete"
            message = f"Batch processing completed successfully.\n{total_processed} items were processed.\n\nWould you like to clear the batch selection?"
        
        reply = QMessageBox.question(
            self, 
            title,
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.clear_batch_selection()
        
        return reply == QMessageBox.StandardButton.Yes
    
    # Helper methods for navigation mode compatibility
    def get_current_selected_file_path(self):
        """Get currently selected file path regardless of navigation mode"""
        if self.navigation_mode == "tree":
            current_item = self.image_list.currentItem()
            if current_item:
                return current_item.data(Qt.ItemDataRole.UserRole)
        elif self.navigation_mode == "master_detail":
            # In master-detail, we need the selected frame/image, not the media item
            current_frame = self.frames_list.currentItem()
            if current_frame:
                return current_frame.data(Qt.ItemDataRole.UserRole)
        return None
    
    def refresh_current_view(self):
        """Refresh the currently active view"""
        if self.navigation_mode == "tree":
            self.refresh_view()
        elif self.navigation_mode == "master_detail":
            self.refresh_master_detail_view()

    # Event handlers
    def on_image_selection_changed(self):
        """Handle image selection change"""
        current_item = self.image_list.currentItem()
        if current_item:
            file_path = current_item.data(Qt.ItemDataRole.UserRole)
            self.load_descriptions_for_image(file_path)
    
    def on_description_selection_changed(self):
        """Handle description selection change"""
        current_item = self.description_list.currentItem()
        
        if current_item:
            desc_id = current_item.data(Qt.ItemDataRole.UserRole)
            
            # Find the description
            image_item = self.image_list.currentItem()
            if image_item:
                file_path = image_item.data(Qt.ItemDataRole.UserRole)
                workspace_item = self.workspace.get_item(file_path)
                
                if workspace_item:
                    for desc in workspace_item.descriptions:
                        if desc.id == desc_id:
                            # Format text for better screen reader accessibility
                            formatted_text = self.format_description_for_accessibility(desc.text)
                            self.description_text.setPlainText(formatted_text)
                            # Update accessibility description with character count and preview
                            char_count = len(desc.text)
                            preview = formatted_text[:200] + "..." if len(formatted_text) > 200 else formatted_text
                            self.description_text.setAccessibleDescription(
                                f"Image description with {char_count} characters from {desc.model}: {preview}"
                            )
                            return
            
            self.description_text.clear()
            self.description_text.setAccessibleDescription("No description selected.")
        else:
            self.description_text.clear()
            self.description_text.setAccessibleDescription("No description selected.")
    
    def load_descriptions_for_image(self, file_path: str):
        """Load descriptions for the selected image"""
        self.description_list.clear()
        
        workspace_item = self.workspace.get_item(file_path)
        if workspace_item and workspace_item.descriptions:
            # Sort descriptions by creation time to ensure chronological order
            # This ensures follow-ups appear after their original descriptions
            sorted_descriptions = sorted(workspace_item.descriptions, key=lambda d: d.created)
            
            for i, desc in enumerate(sorted_descriptions):
                # Show model and prompt type FIRST - simplified format
                model_text = desc.model if desc.model else "Unknown Model"
                
                # Check prompt_style first to properly handle follow-ups
                if desc.prompt_style == "follow-up":
                    prompt_text = "Follow-up"  # Capitalized for better readability
                elif desc.prompt_style == "manual":
                    prompt_text = "Manual"
                elif desc.custom_prompt and desc.prompt_style == "custom":
                    prompt_text = "Custom"
                elif desc.prompt_style:
                    prompt_text = desc.prompt_style.title()  # Capitalize first letter
                else:
                    prompt_text = "Default"
                
                # Show description preview after model info
                desc_preview = desc.text[:100] + "..." if len(desc.text) > 100 else desc.text
                created_date = desc.created.split('T')[0] if 'T' in desc.created else desc.created
                
                # Create list widget item with formatted display
                display_text = f"{model_text} {prompt_text}: {desc_preview}"
                list_item = QListWidgetItem(display_text)
                list_item.setData(Qt.ItemDataRole.UserRole, desc.id)
                
                # Set full text for screen readers - just model, prompt, description, then date
                list_item.setData(Qt.ItemDataRole.AccessibleTextRole,
                                f"{model_text} {prompt_text}: {desc.text}. Created {created_date}")
                # Set AccessibleDescriptionRole for additional context
                list_item.setData(Qt.ItemDataRole.AccessibleDescriptionRole,
                                f"{model_text} {prompt_text}")
                
                self.description_list.addItem(list_item)
            
            # Auto-select the first description
            if self.description_list.count() > 0:
                self.description_list.setCurrentRow(0)
        else:
            self.description_text.clear()
            self.description_text.setAccessibleDescription("No description available.")
    
    # Processing methods
    def toggle_skip_verification(self, checked: bool):
        """Toggle skipping of model verification"""
        if checked:
            self._skip_verification = True
            self.status_bar.showMessage("Model verification disabled - processing will proceed without checks", 3000)
        else:
            self._skip_verification = False
            self.status_bar.showMessage("Model verification enabled", 3000)
    
    def stop_processing(self):
        """Stop all active processing gracefully"""
        self.stop_processing_requested = True
        self.stop_processing_action.setEnabled(False)
        
        # Stop all active workers
        for worker in self.processing_workers[:]:  # Use slice copy to avoid modification during iteration
            try:
                worker.terminate()
                worker.wait()  # Wait for thread to actually stop
            except:
                pass
        
        for worker in self.conversion_workers[:]:
            try:
                worker.terminate()
                worker.wait()
            except:
                pass
        
        # Clear worker lists
        self.processing_workers.clear()
        self.conversion_workers.clear()
        
        # Clear processing state
        self.processing_items.clear()
        
        # Reset batch processing state
        if self.batch_processing:
            self.batch_processing = False
            self.batch_total = 0
            self.batch_completed = 0
            self.update_window_title()
        
        # Update UI
        self.refresh_view()
        self.status_bar.showMessage("Processing stopped by user", 3000)
    
    def update_stop_button_state(self):
        """Enable/disable stop button based on active workers"""
        has_active_workers = bool(self.processing_workers or self.conversion_workers)
        self.stop_processing_action.setEnabled(has_active_workers)
    
    def process_selected(self):
        """Process the currently selected image or video"""
        current_item = self.image_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select an image or video to process.")
            return
        
        file_path = current_item.data(Qt.ItemDataRole.UserRole)
        workspace_item = self.workspace.get_item(file_path)
        
        # Check if it's a video file
        if workspace_item and workspace_item.item_type == "video":
            self.process_video(file_path)
        else:
            self.process_image(file_path)
    
    def process_image(self, file_path: str):
        """Process a single image"""
        # Show processing dialog first
        dialog = ProcessingDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            model, prompt_style, custom_prompt = dialog.get_selections()
            
            # Optional verification - user can skip if they know their setup works
            if not getattr(self, '_skip_verification', True):  # Default to skip
                if not self.check_ollama_status():
                    return
                if not self.verify_model_available(model):
                    return
            
            # Start processing
            self.processing_items.add(file_path)  # Mark as processing
            self.update_window_title()  # Update title to show processing status
            worker = ProcessingWorker(file_path, model, prompt_style, custom_prompt)
            worker.progress_updated.connect(self.on_processing_progress)
            worker.processing_complete.connect(self.on_processing_complete)
            worker.processing_failed.connect(self.on_processing_failed)
            
            self.processing_workers.append(worker)
            worker.start()
            self.update_stop_button_state()
            
            # Preserve current selection before refresh
            current_item = self.image_list.currentItem()
            current_file_path = current_item.data(Qt.ItemDataRole.UserRole) if current_item else None
            
            # Refresh view to show processing indicator
            self.refresh_view()
            
            # Restore focus after refresh
            if current_file_path:
                def restore_focus():
                    for i in range(self.image_list.count()):
                        item = self.image_list.item(i)
                        if item and item.data(Qt.ItemDataRole.UserRole) == current_file_path:
                            self.image_list.setCurrentItem(item)
                            break
                QTimer.singleShot(0, restore_focus)
    
    def process_video(self, file_path: str):
        """Process a video file with frame extraction options"""
        # Show video processing dialog
        dialog = VideoProcessingDialog(self)
        
        # Populate model and prompt options using the same logic as ProcessingDialog
        self.populate_video_dialog_options(dialog)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            extraction_config = dialog.get_extraction_config()
            processing_config = dialog.get_processing_config()
            
            # Mark video as processing and update UI
            self.processing_items.add(file_path)
            self.update_window_title()  # Show processing status in title
            self.refresh_view()  # Show processing indicator in list
            
            # Start video processing with frame extraction
            worker = VideoProcessingWorker(file_path, extraction_config, processing_config)
            worker.progress_updated.connect(self.on_processing_progress)
            worker.extraction_complete.connect(self.on_video_extraction_complete)
            worker.processing_failed.connect(self.on_processing_failed)
            
            self.processing_workers.append(worker)
            worker.start()
    
    def populate_video_dialog_options(self, dialog):
        """Populate model and prompt options for video processing dialog"""
        # Get available models
        models = []
        try:
            if ollama:
                models_response = ollama.list()
                if 'models' in models_response:
                    for model in models_response['models']:
                        model_name = model.get('name', '')
                        if model_name:
                            models.append(model_name)
                
                if not models:
                    models = ['moondream', 'gemma3', 'llava']
            else:
                models = ['moondream', 'gemma3', 'llava']
        except Exception:
            models = ['moondream', 'gemma3', 'llava']
        
        # Get available prompts - same as ProcessingDialog
        prompts = ['detailed', 'concise', 'Narrative', 'artistic', 'technical', 'colorful', 'social', 'Custom']
        
        dialog.populate_models(models)
        dialog.populate_prompts(prompts)
    
    def check_ollama_status(self) -> bool:
        """Check if Ollama is available and responsive"""
        try:
            if not ollama:
                reply = QMessageBox.question(
                    self, "Ollama Not Available",
                    "Ollama Python package is not installed or imported.\n\nWould you like to proceed anyway?\n(Processing will likely fail)",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                return reply == QMessageBox.StandardButton.Yes
            
            # Test Ollama connection with a simple call
            models = ollama.list()
            print(f"Ollama connection successful. Found {len(models.get('models', []))} models.")
            
            if not models.get('models'):
                reply = QMessageBox.question(
                    self, "No Models Available",
                    "No Ollama models are installed.\n\nWould you like to proceed anyway?\n(You can install models with: ollama pull moondream)",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                return reply == QMessageBox.StandardButton.Yes
            
            return True
            
        except Exception as e:
            print(f"Ollama status check error: {str(e)}")
            reply = QMessageBox.question(
                self, "Ollama Connection Issue",
                f"Failed to connect to Ollama:\n{str(e)}\n\nWould you like to proceed anyway?\n(Please ensure Ollama is running)",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            return reply == QMessageBox.StandardButton.Yes
    
    def verify_model_available(self, model_name: str) -> bool:
        """Verify that the selected model is available"""
        try:
            if not ollama:
                return True  # Skip verification if ollama not available, let processing handle it
            
            models = ollama.list()
            available_models = [m['name'] for m in models.get('models', [])]
            
            print(f"Available models: {available_models}")
            print(f"Requested model: {model_name}")
            
            # Check exact match first
            if model_name in available_models:
                return True
            
            # Check for partial matches (e.g., "llava" might match "llava:latest")
            for available in available_models:
                if model_name in available or available.startswith(model_name + ':'):
                    print(f"Found partial match: {available} for {model_name}")
                    return True
            
            # Model not found - ask user what to do
            reply = QMessageBox.question(
                self, "Model Not Found",
                f"Model '{model_name}' is not installed.\n\nAvailable models: {', '.join(available_models)}\n\nWould you like to proceed anyway?\n(Processing might fail if the model is truly unavailable)",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            return reply == QMessageBox.StandardButton.Yes
            
        except Exception as e:
            print(f"Model verification error: {str(e)}")
            # If verification fails, ask user if they want to proceed
            reply = QMessageBox.question(
                self, "Model Verification Failed",
                f"Could not verify model availability:\n{str(e)}\n\nWould you like to proceed anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            return reply == QMessageBox.StandardButton.Yes
    
    def toggle_batch_mark(self):
        """Toggle batch marking for selected image"""
        current_item = self.image_list.currentItem()
        if not current_item:
            return
        
        file_path = current_item.data(Qt.ItemDataRole.UserRole)
        workspace_item = self.workspace.get_item(file_path)
        
        if workspace_item:
            workspace_item.batch_marked = not workspace_item.batch_marked
            self.workspace.mark_modified()
            
            # Update UI colors directly without full refresh for better performance
            if workspace_item.batch_marked:
                # Use light blue background (#E3F2FD) which provides good contrast with black text
                current_item.setBackground(QColor(227, 242, 253))  # Light blue
            else:
                current_item.setBackground(Qt.GlobalColor.transparent)
            
            # Update the batch count label
            self.update_batch_label()
    
    def add_all_to_batch(self):
        """Add all images in the workspace to batch processing"""
        if not self.workspace.items:
            QMessageBox.information(self, "No Images", "No images found in the workspace.")
            return
        
        # Count how many items will be added
        count = 0
        for item in self.workspace.items.values():
            # Skip extracted frames - they should be processed with their parent videos
            if item.item_type == "extracted_frame":
                continue
            if not item.batch_marked:
                count += 1
        
        if count == 0:
            QMessageBox.information(self, "All Marked", "All images are already marked for batch processing.")
            return
        
        # Confirm the action
        reply = QMessageBox.question(
            self, "Add All to Batch",
            f"This will add {count} items to the batch queue.\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Mark all items for batch processing
            for item in self.workspace.items.values():
                # Skip extracted frames
                if item.item_type == "extracted_frame":
                    continue
                item.batch_marked = True
            
            self.workspace.mark_modified()
            self.refresh_view()  # Refresh to show all the batch markings
            
            QMessageBox.information(self, "Batch Updated", f"Added {count} items to batch queue.")
    
    def process_batch(self):
        """Process all batch-marked images"""
        batch_items = [item for item in self.workspace.items.values() if item.batch_marked]
        
        if not batch_items:
            QMessageBox.information(self, "No Batch Items", "No images are marked for batch processing.")
            return
        
        # Show processing dialog first
        dialog = ProcessingDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            model, prompt_style, custom_prompt = dialog.get_selections()
            
            # Optional verification - user can skip if they know their setup works
            if not getattr(self, '_skip_verification', True):  # Default to skip
                if not self.check_ollama_status():
                    return
                if not self.verify_model_available(model):
                    return
            
        # Process each batch item
        self.batch_total = len(batch_items)
        self.batch_completed = 0
        self.batch_processing = True
        self.stop_processing_requested = False  # Reset stop flag
        self.update_window_title()
        
        for item in batch_items:
            # Check if stop was requested
            if self.stop_processing_requested:
                break
            
            # Add to processing items to show "p" indicator
            self.processing_items.add(item.file_path)
                
            worker = ProcessingWorker(item.file_path, model, prompt_style, custom_prompt)
            worker.progress_updated.connect(self.on_processing_progress)
            worker.processing_complete.connect(self.on_batch_item_complete)
            worker.processing_failed.connect(self.on_batch_item_failed)
            
            self.processing_workers.append(worker)
            worker.start()
        
        # Refresh view to show processing indicators
        self.refresh_view()
        self.update_stop_button_state()

    def convert_heic_files(self):
        """Convert all HEIC files in the workspace"""
        heic_items = [item for item in self.workspace.items.values() 
                     if Path(item.file_path).suffix.lower() in ['.heic', '.heif']]
        
        if not heic_items:
            QMessageBox.information(self, "No HEIC Files", "No HEIC files found in workspace.")
            return
        
        for item in heic_items:
            worker = ConversionWorker(item.file_path, "heic")
            worker.progress_updated.connect(self.on_processing_progress)
            worker.conversion_complete.connect(self.on_conversion_complete)
            worker.conversion_failed.connect(self.on_processing_failed)
            
            self.conversion_workers.append(worker)
            worker.start()
    
    def extract_video_frames(self):
        """Extract frames from selected video or batch-marked videos"""
        # First check if there's a currently selected video
        current_item = self.image_list.currentItem()
        if current_item:
            file_path = current_item.data(Qt.ItemDataRole.UserRole)
            workspace_item = self.workspace.get_item(file_path)
            
            if workspace_item and workspace_item.item_type == "video":
                # Extract frames from the selected video
                self.extract_frames_from_video(file_path)
                return
        
        # No video selected, check for batch-marked videos
        batch_videos = [item for item in self.workspace.items.values() 
                       if item.item_type == "video" and item.batch_marked]
        
        if batch_videos:
            # Extract frames from all batch-marked videos
            for item in batch_videos:
                self.extract_frames_from_video(item.file_path)
            return
        
        # No selection and no batch-marked videos
        video_count = len([item for item in self.workspace.items.values() if item.item_type == "video"])
        if video_count == 0:
            QMessageBox.information(self, "No Videos", "No video files found in workspace.")
        else:
            QMessageBox.information(
                self, "No Video Selected", 
                "Please select a video or mark videos for batch processing before extracting frames."
            )
    
    def extract_frames_from_video(self, file_path: str):
        """Extract frames from a single video file"""
        worker = ConversionWorker(file_path, "video")
        worker.progress_updated.connect(self.on_processing_progress)
        worker.conversion_complete.connect(self.on_conversion_complete)
        worker.conversion_failed.connect(self.on_processing_failed)
        
        self.conversion_workers.append(worker)
        worker.start()
    
    # Description management
    def add_manual_description(self):
        """Add a manual description entered by the user"""
        file_path = self.get_current_selected_file_path()
        
        if not file_path:
            QMessageBox.information(
                self, "No Image Selected",
                "Please select an image first to add a manual description."
            )
            return
        
        # Create a custom dialog with proper Tab handling
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Manual Description")
        dialog.setModal(True)
        dialog.resize(500, 300)
        
        layout = QVBoxLayout(dialog)
        
        # Add label
        label = QLabel("Enter your description for this image:")
        layout.addWidget(label)
        
        # Add text edit with proper Tab handling (using AccessibleTextEdit)
        text_edit = AccessibleTextEdit()
        text_edit.setPlaceholderText("Enter description here...")
        layout.addWidget(text_edit)
        
        # Add buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        # Show dialog and get result
        if dialog.exec() == QDialog.DialogCode.Accepted:
            description_text = text_edit.toPlainText().strip()
            
            if description_text:
                workspace_item = self.workspace.get_item(file_path)
                
                if workspace_item:
                    # Create manual description with "manual" as model and prompt_style
                    manual_desc = ImageDescription(
                        text=description_text,
                        model="manual",
                        prompt_style="manual"
                    )
                    
                    workspace_item.add_description(manual_desc)
                    self.workspace.mark_modified()
                    
                    # Refresh BOTH the descriptions view AND the main view (for count update)
                    if self.navigation_mode == "tree":
                        self.load_descriptions_for_image(file_path)
                        self.refresh_view()  # This updates the description count in the tree
                        
                        # Select the newly added description
                        for i in range(self.description_list.count()):
                            item = self.description_list.item(i)
                            if item.data(Qt.ItemDataRole.UserRole) == manual_desc.id:
                                self.description_list.setCurrentItem(item)
                                break
                    elif self.navigation_mode == "master_detail":
                        self.load_descriptions_for_image_md(file_path)
                        self.refresh_master_detail_view()  # This updates the description count
                        
                        # Select the newly added description
                        for i in range(self.description_list_md.count()):
                            item = self.description_list_md.item(i)
                            if item.data(Qt.ItemDataRole.UserRole) == manual_desc.id:
                                self.description_list_md.setCurrentItem(item)
                                break
                    
                    self.status_bar.showMessage("Manual description added successfully", 3000)
            else:
                QMessageBox.information(self, "Empty Description", "Please enter a description.")
    
    def format_description_for_accessibility(self, text: str) -> str:
        """Format description text for better screen reader accessibility"""
        if not text:
            return text
        
        # Split long sentences at sentence boundaries for better navigation
        # Replace periods followed by spaces with periods and newlines
        formatted = text.replace('. ', '.\n')
        
        # Also split on other sentence endings
        formatted = formatted.replace('! ', '!\n')
        formatted = formatted.replace('? ', '?\n')
        
        # Remove any double newlines that might have been created
        formatted = formatted.replace('\n\n', '\n')
        
        # Remove leading/trailing whitespace from each line
        lines = [line.strip() for line in formatted.split('\n') if line.strip()]
        
        # Join with single newlines and apply viewer's technique for blank lines
        joined_text = '\n'.join(lines)
        
        # Process the text to ensure blank lines are properly handled for screen readers
        # (technique learned from the viewer app)
        processed_lines = []
        for line in joined_text.split('\n'):
            if line.strip() == '':  # If line is empty or just whitespace
                processed_lines.append('\u00A0')  # Use non-breaking space for screen readers
            else:
                processed_lines.append(line)
        
        return '\n'.join(processed_lines)
    
    def ask_followup_question(self):
        """Ask a follow-up question about an existing description using the same AI engine"""
        current_image_item = self.image_list.currentItem()
        
        if not current_image_item:
            QMessageBox.information(
                self, "No Image Selected",
                "Please select an image first to ask a follow-up question."
            )
            return
        
        file_path = current_image_item.data(Qt.ItemDataRole.UserRole)
        workspace_item = self.workspace.get_item(file_path)
        
        if not workspace_item or not workspace_item.descriptions:
            QMessageBox.information(
                self, "No Descriptions Found",
                "This image has no existing descriptions. Please add a description first."
            )
            return
        
        # Filter out manual descriptions (only AI-generated descriptions can have follow-ups)
        ai_descriptions = [desc for desc in workspace_item.descriptions if desc.model != "manual"]
        
        if not ai_descriptions:
            QMessageBox.information(
                self, "No AI Descriptions Found",
                "This image has no AI-generated descriptions. Follow-up questions can only be asked about AI-generated descriptions."
            )
            return
        
        # Get currently selected description (if any) to pre-select in combo box
        current_desc_item = self.description_list.currentItem()
        current_desc_id = current_desc_item.data(Qt.ItemDataRole.UserRole) if current_desc_item else None
        
        # Create follow-up dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Ask Follow-up Question")
        dialog.setModal(True)
        dialog.resize(600, 500)
        
        layout = QVBoxLayout(dialog)
        
        # Description selection section
        desc_label = QLabel("Select description to ask follow-up question about:")
        layout.addWidget(desc_label)
        
        desc_combo = QComboBox()
        default_index = 0  # Default to first item if no match found
        
        for i, desc in enumerate(ai_descriptions):
            preview = desc.text[:100] + "..." if len(desc.text) > 100 else desc.text
            desc_combo.addItem(f"{desc.model} - {preview}", desc)
            
            # Check if this is the currently selected description
            if current_desc_id and desc.id == current_desc_id:
                default_index = i
        
        desc_combo.setCurrentIndex(default_index)
        layout.addWidget(desc_combo)
        
        # Selected description display
        layout.addWidget(QLabel("Full description:"))
        desc_display = QTextEdit()
        desc_display.setReadOnly(True)
        desc_display.setMaximumHeight(150)
        desc_display.setAccessibleName("Selected Description Display")
        desc_display.setAccessibleDescription("Full text of the selected description. Use arrow keys to navigate through the text.")
        # Apply viewer app's accessibility settings
        desc_display.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard)
        desc_display.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        desc_display.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        layout.addWidget(desc_display)
        
        # Update description display when selection changes
        def update_description():
            selected_desc = desc_combo.currentData()
            if selected_desc:
                # Format text for better screen reader accessibility
                formatted_text = self.format_description_for_accessibility(selected_desc.text)
                desc_display.setPlainText(formatted_text)
                # Update accessible description with dynamic content
                desc_display.setAccessibleDescription(f"Description from {selected_desc.model}: {formatted_text[:200]}{'...' if len(formatted_text) > 200 else ''}")
        
        desc_combo.currentTextChanged.connect(update_description)
        update_description()  # Set initial text
        
        # Follow-up question section
        layout.addWidget(QLabel("Enter your follow-up question:"))
        info_label = QLabel("This will create a new 'Follow-up' description using the same AI model.")
        info_label.setStyleSheet("color: #666; font-style: italic; margin-bottom: 5px;")
        layout.addWidget(info_label)
        question_edit = AccessibleTextEdit()
        question_edit.setPlaceholderText("e.g., What colors are prominent in this image? Can you describe the lighting? What mood does this convey?")
        question_edit.setMaximumHeight(100)
        layout.addWidget(question_edit)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        # Set explicit tab order to ensure proper navigation
        dialog.setTabOrder(desc_combo, desc_display)
        dialog.setTabOrder(desc_display, question_edit)
        dialog.setTabOrder(question_edit, button_box)
        
        # Show dialog and process if accepted
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_desc = desc_combo.currentData()
            follow_up_question = question_edit.toPlainText().strip()
            
            if not follow_up_question:
                QMessageBox.information(self, "Empty Question", "Please enter a follow-up question.")
                return
            
            # Create a custom prompt that includes the original description and the follow-up question
            custom_prompt = f"""Here is the original description of this image:
"{selected_desc.text}"

Follow-up question: {follow_up_question}

Please answer the follow-up question about this image, taking into account the context from the original description."""
            
            # Start processing with the same model as the original description
            self.processing_items.add(file_path)
            self.update_window_title()  # Update title to show processing status
            worker = ProcessingWorker(file_path, selected_desc.model, "follow-up", custom_prompt)
            worker.progress_updated.connect(self.on_processing_progress)
            worker.processing_complete.connect(self.on_processing_complete)
            worker.processing_failed.connect(self.on_processing_failed)
            
            self.processing_workers.append(worker)
            worker.start()
            self.update_stop_button_state()
            
            # Preserve current selection before refresh
            current_item = self.image_list.currentItem()
            current_file_path = current_item.data(Qt.ItemDataRole.UserRole) if current_item else None
            
            # Refresh view to show processing indicator
            self.refresh_view()
            
            # Restore focus after refresh
            if current_file_path:
                def restore_focus():
                    for i in range(self.image_list.count()):
                        item = self.image_list.item(i)
                        if item and item.data(Qt.ItemDataRole.UserRole) == current_file_path:
                            self.image_list.setCurrentItem(item)
                            break
                QTimer.singleShot(0, restore_focus)
            
            self.status_bar.showMessage(f"Processing follow-up question with {selected_desc.model}...", 3000)
    
    def edit_description(self):
        """Edit the selected description"""
        current_desc_item = self.description_list.currentItem()
        current_image_item = self.image_list.currentItem()
        
        if not current_desc_item or not current_image_item:
            return
        
        desc_id = current_desc_item.data(Qt.ItemDataRole.UserRole)
        file_path = current_image_item.data(Qt.ItemDataRole.UserRole)
        workspace_item = self.workspace.get_item(file_path)
        
        if workspace_item:
            for desc in workspace_item.descriptions:
                if desc.id == desc_id:
                    # Create custom dialog with proper Tab handling
                    dialog = QDialog(self)
                    dialog.setWindowTitle("Edit Description")
                    dialog.setModal(True)
                    dialog.resize(500, 300)
                    
                    layout = QVBoxLayout(dialog)
                    
                    # Add label
                    label = QLabel("Description:")
                    layout.addWidget(label)
                    
                    # Add text edit with proper Tab handling
                    text_edit = AccessibleTextEdit()
                    text_edit.setPlainText(desc.text)
                    layout.addWidget(text_edit)
                    
                    # Add buttons
                    button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
                    button_box.accepted.connect(dialog.accept)
                    button_box.rejected.connect(dialog.reject)
                    layout.addWidget(button_box)
                    
                    # Show dialog and get result
                    if dialog.exec() == QDialog.DialogCode.Accepted:
                        new_text = text_edit.toPlainText()
                        if new_text.strip():
                            desc.text = new_text
                            self.workspace.mark_modified()
                            self.load_descriptions_for_image(file_path)
                            # Format text for better screen reader accessibility
                            formatted_text = self.format_description_for_accessibility(new_text)
                            self.description_text.setPlainText(formatted_text)
                    break
    
    def delete_description(self):
        """Delete the selected description"""
        current_desc_item = self.description_list.currentItem()
        current_image_item = self.image_list.currentItem()
        
        if not current_desc_item or not current_image_item:
            return
        
        reply = QMessageBox.question(
            self, "Delete Description",
            "Are you sure you want to delete this description?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            desc_id = current_desc_item.data(Qt.ItemDataRole.UserRole)
            file_path = current_image_item.data(Qt.ItemDataRole.UserRole)
            workspace_item = self.workspace.get_item(file_path)
            
            if workspace_item:
                workspace_item.remove_description(desc_id)
                self.workspace.mark_modified()
                self.load_descriptions_for_image(file_path)
                self.refresh_view()
    
    def copy_description(self):
        """Copy the current description to clipboard"""
        text = self.description_text.toPlainText()
        if text:
            QGuiApplication.clipboard().setText(text)
            self.status_bar.showMessage("Description copied to clipboard", 2000)
    
    def copy_image(self):
        """Copy the selected image to clipboard"""
        current_item = self.image_list.currentItem()
        if current_item:
            file_path = current_item.data(Qt.ItemDataRole.UserRole)
            try:
                # Load image and copy to clipboard
                pixmap = QPixmap(file_path)
                if not pixmap.isNull():
                    QGuiApplication.clipboard().setPixmap(pixmap)
                    self.status_bar.showMessage("Image copied to clipboard", 2000)
                else:
                    QMessageBox.warning(self, "Copy Failed", "Failed to load image for copying.")
            except Exception as e:
                QMessageBox.warning(self, "Copy Failed", f"Failed to copy image:\n{str(e)}")
    
    def copy_image_path(self):
        """Copy the selected image path to clipboard"""
        current_item = self.image_list.currentItem()
        if current_item:
            file_path = current_item.data(Qt.ItemDataRole.UserRole)
            QGuiApplication.clipboard().setText(file_path)
            self.status_bar.showMessage("Image path copied to clipboard", 2000)
    
    # View operations
    def set_filter(self, mode: str):
        """Set the filter mode and refresh view"""
        self.filter_mode = mode
        
        # Update checkable actions
        self.filter_all_action.setChecked(mode == "all")
        self.filter_described_action.setChecked(mode == "described")
        self.filter_batch_action.setChecked(mode == "batch")
        
        # Refresh the view with filter applied
        self.refresh_view()
        
        # Update window title to show current filter
        self.update_window_title()

    def process_all(self):
        """Process all images with automatic HEIC conversion and video frame extraction"""
        if not self.workspace.items:
            QMessageBox.information(self, "No Items", "No images or videos found in workspace.")
            return
        
        # Count what needs processing
        image_count = sum(1 for item in self.workspace.items.values() if item.item_type == "image")
        video_count = sum(1 for item in self.workspace.items.values() if item.item_type == "video")
        heic_count = sum(1 for item in self.workspace.items.values() 
                        if item.item_type == "image" and item.file_path.lower().endswith(('.heic', '.heif')))
        
        # Show confirmation with what will be processed
        message = f"Process All will:\n\n"
        if heic_count > 0:
            message += f"Convert {heic_count} HEIC files to JPEG\n"
        if video_count > 0:
            message += f"Extract frames from {video_count} videos (using default settings)\n"
        if image_count > 0:
            message += f"Generate descriptions for {image_count} images\n"
        message += f"\nDescriptions will appear as they are generated (like the viewer app).\n\nContinue?"
        
        reply = QMessageBox.question(
            self, "Process All", message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Show processing dialog for AI model/prompt selection
        dialog = ProcessingDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        
        model, prompt_style, custom_prompt = dialog.get_selections()
        
        # Optional verification
        if not getattr(self, '_skip_verification', True):
            if not self.check_ollama_status():
                return
            if not self.verify_model_available(model):
                return
        
        # Start comprehensive processing
        self._start_comprehensive_processing(model, prompt_style, custom_prompt)
    
    def _start_comprehensive_processing(self, model, prompt_style, custom_prompt):
        """Start comprehensive processing using the proven workflow system"""
        if not self.workspace.directory_path:
            QMessageBox.warning(self, "No Directory", "Please load a directory first.")
            return
        
        try:
            # Use the existing proven workflow system instead of reinventing
            import subprocess
            import sys
            from pathlib import Path
            
            input_dir = Path(self.workspace.directory_path)
            output_dir = input_dir / "workflow_output"
            
            # Build workflow command with current settings
            cmd = [
                sys.executable, 
                str(Path(__file__).parent.parent / "scripts" / "workflow.py"),
                str(input_dir),
                "--output-dir", str(output_dir),
                "--steps", "video,convert,describe",  # Skip HTML for now
                "--model", model,
                "--prompt-style", prompt_style
            ]
            
            if custom_prompt:
                cmd.extend(["--custom-prompt", custom_prompt])
            
            self.status_bar.showMessage("Starting comprehensive processing with proven workflow...")
            
            # Start the workflow as a background process
            self._start_workflow_process(cmd, input_dir, output_dir)
            
        except Exception as e:
            self.status_bar.showMessage(f"Error starting workflow: {str(e)}", 5000)
    
    def _start_workflow_process(self, cmd, input_dir, output_dir):
        """Start the workflow process and monitor for completion"""
        try:
            # Create a worker to run the workflow
            self.workflow_worker = WorkflowProcessWorker(cmd, input_dir, output_dir)
            self.workflow_worker.progress_updated.connect(self._on_workflow_progress)
            self.workflow_worker.workflow_complete.connect(self._on_workflow_complete)
            self.workflow_worker.workflow_failed.connect(self._on_workflow_failed)
            
            self.workflow_worker.start()
            
        except Exception as e:
            self.status_bar.showMessage(f"Error starting workflow process: {str(e)}", 5000)
    
    def _on_workflow_progress(self, message):
        """Handle workflow progress updates"""
        self.status_bar.showMessage(message, 2000)
    
    def _on_workflow_complete(self, input_dir, output_dir):
        """Handle workflow completion - reload directory to show new files"""
        try:
            # Reload the directory to pick up new converted images and descriptions
            self.load_directory_path(str(input_dir))
            self.status_bar.showMessage("Comprehensive processing complete! Directory reloaded with new content.", 5000)
            
        except Exception as e:
            self.status_bar.showMessage(f"Workflow completed but reload failed: {str(e)}", 5000)
    
    def _on_workflow_failed(self, error):
        """Handle workflow failure"""
        self.status_bar.showMessage(f"Workflow failed: {error}", 5000)
    
    def _extract_video_frames_with_defaults(self, video_path):
        """Extract video frames using default settings"""
        try:
            # Use default settings: 5 second intervals, full video duration
            self.extract_video_frames(
                video_path=video_path,
                time_interval=5.0,
                start_time=0.0,
                end_time=0.0,  # 0 means full video
                max_frames=0,  # 0 means no limit
                use_scene_detection=False
            )
        except Exception as e:
            self.status_bar.showMessage(f"Error extracting frames from {Path(video_path).name}: {str(e)}", 5000)
    
    def _process_images_with_live_updates(self, image_paths, model, prompt_style, custom_prompt):
        """Process images with live updates like the viewer app"""
        if not image_paths:
            return
        
        # Set up live processing with immediate UI updates
        self.processing_items.update(image_paths)
        self.refresh_view()  # Show processing indicators immediately
        
        # Start processing first image
        self._current_process_all_queue = image_paths.copy()
        self._current_process_all_model = model
        self._current_process_all_prompt = prompt_style
        self._current_process_all_custom = custom_prompt
        
        # Process first image
        if self._current_process_all_queue:
            first_image = self._current_process_all_queue.pop(0)
            self.status_bar.showMessage(f"Processing {Path(first_image).name}... ({len(image_paths) - len(self._current_process_all_queue)} of {len(image_paths)})")
            self._process_single_for_process_all(first_image)
    
    def _process_single_for_process_all(self, file_path):
        """Process a single image as part of Process All with live updates"""
        # Create and start worker thread
        worker = ProcessingWorker(
            file_path, 
            self._current_process_all_model, 
            self._current_process_all_prompt, 
            self._current_process_all_custom
        )
        
        # Connect signals for live updates
        worker.processing_complete.connect(lambda fp, desc, model, prompt, custom: self._on_process_all_item_complete(fp, desc, model, prompt, custom))
        worker.processing_failed.connect(lambda fp, error: self._on_process_all_item_failed(fp, error))
        
        # Store reference and start
        self.workers.append(worker)
        worker.start()
    
    def _on_process_all_item_complete(self, file_path, description, model, prompt_style, custom_prompt):
        """Handle completion of single item in Process All - with live updates"""
        # Add description to workspace
        workspace_item = self.workspace.get_item(file_path)
        if workspace_item:
            desc = ImageDescription(description, model, prompt_style, custom_prompt=custom_prompt)
            workspace_item.descriptions.append(desc)
            self.workspace.mark_modified()
        
        # Remove from processing items
        self.processing_items.discard(file_path)
        self.update_window_title()  # Update title to remove processing status
        
        # Refresh view immediately to show new description (like viewer app)
        self.refresh_view()
        
        # Update status
        remaining = len(self._current_process_all_queue)
        total = len(getattr(self, '_current_process_all_queue', [])) + 1
        processed = total - remaining
        
        if remaining > 0:
            # Process next image
            next_image = self._current_process_all_queue.pop(0)
            self.status_bar.showMessage(f"Processing {Path(next_image).name}... ({processed} of {total} complete)")
            self._process_single_for_process_all(next_image)
        else:
            # All done
            self.status_bar.showMessage(f"Process All complete! {processed} images processed.", 5000)
            # Clean up
            if hasattr(self, '_current_process_all_queue'):
                delattr(self, '_current_process_all_queue')
            if hasattr(self, '_current_process_all_model'):
                delattr(self, '_current_process_all_model')
            if hasattr(self, '_current_process_all_prompt'):
                delattr(self, '_current_process_all_prompt')
            if hasattr(self, '_current_process_all_custom'):
                delattr(self, '_current_process_all_custom')
    
    def _on_process_all_item_failed(self, file_path, error):
        """Handle failure of single item in Process All"""
        # Remove from processing items
        self.processing_items.discard(file_path)
        
        # Refresh view to remove processing indicator
        self.refresh_view()
        
        # Log error but continue processing
        self.status_bar.showMessage(f"Error processing {Path(file_path).name}: {error}", 3000)
        
        # Continue with next image
        remaining = len(getattr(self, '_current_process_all_queue', []))
        if remaining > 0:
            next_image = self._current_process_all_queue.pop(0)
            self.status_bar.showMessage(f"Processing {Path(next_image).name}... (continuing after error)")
            self._process_single_for_process_all(next_image)
        else:
            # All done (even with errors)
            self.status_bar.showMessage("Process All complete (some items had errors).", 5000)
    
    def convert_heic_files(self):
        """Convert HEIC files to JPEG format using existing functionality"""
        try:
            # Get all HEIC files
            heic_items = [item for item in self.workspace.items.values() 
                         if item.item_type == "image" and item.file_path.lower().endswith(('.heic', '.heif'))]
            
            if not heic_items:
                return
            
            # Use existing ConvertImage functionality
            from scripts.ConvertImage import convert_heic_to_jpg
            
            for item in heic_items:
                try:
                    # Convert the file (returns True/False, not path)
                    success = convert_heic_to_jpg(item.file_path)
                    if success:
                        # Generate the expected output path
                        input_path = Path(item.file_path)
                        output_path = input_path.with_suffix('.jpg')
                        
                        if output_path.exists():
                            # Add converted file to workspace
                            converted_item = ImageItem(str(output_path), "image")
                            self.workspace.add_item(converted_item)
                            self.status_bar.showMessage(f"Converted {input_path.name}", 2000)
                        else:
                            self.status_bar.showMessage(f"Conversion succeeded but file not found: {output_path.name}", 3000)
                    else:
                        self.status_bar.showMessage(f"Failed to convert {Path(item.file_path).name}", 3000)
                except Exception as e:
                    self.status_bar.showMessage(f"Failed to convert {Path(item.file_path).name}: {str(e)}", 3000)
            
            self.workspace.mark_modified()
            
        except Exception as e:
            self.status_bar.showMessage(f"HEIC conversion error: {str(e)}", 5000)
    
    def _process_all_images_live(self, model, prompt_style, custom_prompt):
        """Process all images with live updates like the viewer"""
        # Get all processable images
        all_images = []
        for item in self.workspace.items.values():
            if item.item_type in ["image", "extracted_frame"]:
                all_images.append(item)
        
        if not all_images:
            self.status_bar.showMessage("No images to process", 3000)
            return
        
        # Set up batch processing with live updates
        self.batch_total = len(all_images)
        self.batch_completed = 0
        self.batch_processing = True
        self.update_window_title()
        
        self.status_bar.showMessage(f"Processing {len(all_images)} images with live updates...")
        
        # Process images one by one to show live updates
        for item in all_images:
            worker = ProcessingWorker(item.file_path, model, prompt_style, custom_prompt)
            worker.progress_updated.connect(self.on_processing_progress)
            worker.processing_complete.connect(self._on_live_processing_complete)
            worker.processing_failed.connect(self._on_live_processing_failed)
            
            self.processing_workers.append(worker)
            worker.start()
        
        self.update_stop_button_state()
    
    def _on_live_processing_complete(self, file_path: str, description: str, model: str, prompt_style: str, custom_prompt: str):
        """Handle processing completion with live updates"""
        # Call the regular completion handler
        self.on_processing_complete(file_path, description, model, prompt_style, custom_prompt)
        
        # Update batch progress
        self.batch_completed += 1
        self.update_window_title()
        
        # Refresh view immediately to show new description (like viewer app)
        self.refresh_view()
        
        # Auto-select the newly processed item if nothing else is selected
        current_item = self.image_list.currentItem()
        if not current_item:
            # Find and select the processed item
            for i in range(self.image_list.count()):
                item = self.image_list.item(i)
                if item:
                    item_path = item.data(Qt.ItemDataRole.UserRole)
                    if item_path == file_path:
                        self.image_list.setCurrentItem(item)
                        break
        
        # Show status update
        self.status_bar.showMessage(
            f"Processed {self.batch_completed} of {self.batch_total}: {Path(file_path).name}", 
            2000
        )
        
        # Check if batch is complete
        if self.batch_completed >= self.batch_total:
            self.batch_processing = False
            total_processed = self.batch_total
            self.batch_total = 0
            self.batch_completed = 0
            self.update_window_title()
            self.status_bar.showMessage(f"Process All complete: {total_processed} items processed", 5000)
            
            # Show completion dialog
            self.show_batch_completion_dialog(total_processed, has_errors=False)
    
    def _on_live_processing_failed(self, file_path: str, error: str):
        """Handle processing failure with live updates"""
        # Call the regular failure handler
        self.on_processing_failed(file_path, error)
        
        # Update batch progress
        self.batch_completed += 1
        self.update_window_title()
        
        # Show status update
        self.status_bar.showMessage(
            f"Failed {self.batch_completed} of {self.batch_total}: {Path(file_path).name}", 
            3000
        )
        
        # Check if batch is complete
        if self.batch_completed >= self.batch_total:
            self.batch_processing = False
            total_processed = self.batch_total
            self.batch_total = 0
            self.batch_completed = 0
            self.update_window_title()
            self.status_bar.showMessage(f"Process All finished with errors: {total_processed} items processed", 5000)
            
            # Show completion dialog
            self.show_batch_completion_dialog(total_processed, has_errors=True)

    def show_all_descriptions_dialog(self):
        """Show all descriptions in a single list for easy browsing"""
        # Collect all descriptions from all items
        all_descriptions = []
        for item in self.workspace.items.values():
            for desc in item.descriptions:
                all_descriptions.append({
                    'file_path': item.file_path,
                    'file_name': Path(item.file_path).name,
                    'description': desc,
                    'display_text': f"{desc.model if desc.model else 'Unknown'} {desc.prompt_style if desc.prompt_style else 'default'}: {desc.text}"
                })
        
        if not all_descriptions:
            QMessageBox.information(self, "No Descriptions", "No descriptions found in workspace.")
            return
        
        # Create dialog
        dialog = AllDescriptionsDialog(all_descriptions, self)
        dialog.exec()
    
    # Worker event handlers
    def on_processing_progress(self, message: str):
        """Handle processing progress updates"""
        self.status_bar.showMessage(message)
    
    def on_processing_complete(self, file_path: str, description: str, model: str, prompt_style: str, custom_prompt: str):
        """Handle successful processing completion"""
        # Remove from processing set
        self.processing_items.discard(file_path)
        
        workspace_item = self.workspace.get_item(file_path)
        if not workspace_item:
            workspace_item = ImageItem(file_path)
            self.workspace.add_item(workspace_item)
        
        # Add the new description
        desc = ImageDescription(description, model, prompt_style, custom_prompt=custom_prompt)
        workspace_item.add_description(desc)
        self.workspace.mark_modified()
        
        # Update window title to reflect current processing status
        remaining_processing = len(self.processing_items)
        if remaining_processing > 0:
            self.update_window_title(f"Processing: {remaining_processing} items remaining")
        else:
            # All processing complete - clear custom status
            self.update_window_title()
        
        # Update UI - but DON'T restore focus during batch frame processing
        # Only restore focus if this was a single item or the last item in a batch
        is_frame_processing = any("frame_" in str(item) for item in self.processing_items)
        
        if is_frame_processing and remaining_processing > 0:
            # Still processing frames - just refresh without focus restoration to prevent jumping
            self.refresh_view()
        else:
            # Single item processing or batch complete - safe to restore focus
            # PRESERVE FOCUS: Remember currently selected item before refresh
            current_item = self.image_list.currentItem()
            current_file_path = current_item.data(Qt.ItemDataRole.UserRole) if current_item else None
            
            self.refresh_view()
            
            # RESTORE FOCUS: Find and select the same item after refresh
            if current_file_path:
                # Use QTimer.singleShot to ensure focus restoration happens after UI update
                def restore_focus():
                    for i in range(self.image_list.count()):
                        item = self.image_list.item(i)
                        if item and item.data(Qt.ItemDataRole.UserRole) == current_file_path:
                            self.image_list.setCurrentItem(item)
                            self.image_list.scrollToItem(item)  # Ensure it's visible
                            break
                
                QTimer.singleShot(0, restore_focus)
        
        # Remove completed worker from list
        sender_worker = self.sender()
        if sender_worker in self.processing_workers:
            self.processing_workers.remove(sender_worker)
        self.update_stop_button_state()
        
        # If this is the currently selected image, refresh descriptions
        if current_file_path == file_path:
            self.load_descriptions_for_image(file_path)
        
        self.status_bar.showMessage(f"Processing complete: {Path(file_path).name}", 3000)
    
    def on_processing_failed(self, file_path: str, error: str):
        """Handle processing failure"""
        # Preserve focus
        current_item = self.image_list.currentItem()
        current_file_path = current_item.data(Qt.ItemDataRole.UserRole) if current_item else None
        
        # Remove from processing set
        self.processing_items.discard(file_path)
        
        # Update window title to reflect current processing status
        remaining_processing = len(self.processing_items)
        if remaining_processing > 0:
            self.update_window_title(f"Processing: {remaining_processing} items remaining")
        else:
            # All processing complete - clear custom status
            self.update_window_title()
        
        # Remove failed worker from list
        sender_worker = self.sender()
        if sender_worker in self.processing_workers:
            self.processing_workers.remove(sender_worker)
        self.update_stop_button_state()
        
        self.refresh_view()  # Update display
        
        # Restore focus - find and select the same item after refresh
        if current_file_path:
            # Use QTimer.singleShot to ensure focus restoration happens after UI update
            def restore_focus():
                for i in range(self.image_list.count()):
                    item = self.image_list.item(i)
                    if item and item.data(Qt.ItemDataRole.UserRole) == current_file_path:
                        self.image_list.setCurrentItem(item)
                        self.image_list.scrollToItem(item)  # Ensure it's visible
                        break
            
            QTimer.singleShot(0, restore_focus)
        
        error_msg = f"Failed to process {Path(file_path).name}:\n{error}"
        
        # Show detailed error information
        details = f"""Processing failed for: {file_path}

Error: {error}

Troubleshooting steps:
1. Check that Ollama is running: ollama list
2. Verify the selected model is installed
3. Try a different model
4. Check image file is not corrupted
5. Ensure sufficient disk space and memory

You can check Ollama logs for more details."""
        
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setWindowTitle("Processing Failed")
        msg_box.setText(error_msg)
        msg_box.setDetailedText(details)
        msg_box.exec()
        
        self.status_bar.showMessage("Processing failed", 3000)

    def on_batch_item_complete(self, file_path: str, description: str, model: str, prompt_style: str, custom_prompt: str):
        """Handle batch item completion"""
        # Call the regular completion handler first
        self.on_processing_complete(file_path, description, model, prompt_style, custom_prompt)
        
        # Update batch progress
        self.batch_completed += 1
        self.update_window_title()
        
        # Check if batch is complete
        if self.batch_completed >= self.batch_total:
            self.batch_processing = False
            total_processed = self.batch_total
            self.batch_total = 0
            self.batch_completed = 0
            self.update_window_title()
            self.status_bar.showMessage(f"Batch processing complete: {total_processed} items processed", 5000)
            
            # Show confirmation dialog for clearing batch selection
            self.show_batch_completion_dialog(total_processed, has_errors=False)

    def on_batch_item_failed(self, file_path: str, error: str):
        """Handle batch item failure"""
        # Call the regular failure handler first
        self.on_processing_failed(file_path, error)
        
        # Update batch progress
        self.batch_completed += 1
        self.update_window_title()
        
        # Check if batch is complete
        if self.batch_completed >= self.batch_total:
            self.batch_processing = False
            total_processed = self.batch_total
            self.batch_total = 0
            self.batch_completed = 0
            self.update_window_title()
            self.status_bar.showMessage(f"Batch processing finished with errors: {total_processed} items processed", 5000)
            
            # Show confirmation dialog for clearing batch selection
            self.show_batch_completion_dialog(total_processed, has_errors=True)
    
    def on_conversion_complete(self, original_path: str, converted_paths: list):
        """Handle successful conversion completion"""
        original_item = self.workspace.get_item(original_path)
        
        # Add converted files to workspace
        for converted_path in converted_paths:
            if converted_path not in self.workspace.items:
                new_item = ImageItem(converted_path, "image")
                if original_item and original_item.item_type == "video":
                    new_item.parent_video = original_path
                    original_item.extracted_frames.append(converted_path)
                self.workspace.add_item(new_item)
        
        self.workspace.mark_modified()
        self.refresh_view()
        self.status_bar.showMessage(f"Conversion complete: {len(converted_paths)} files created", 3000)
    
    def on_video_extraction_complete(self, video_path: str, extracted_frames: list, processing_config: dict):
        """Handle completion of video frame extraction"""
        # Remove video from processing items and mark as extracted
        if video_path in self.processing_items:
            self.processing_items.remove(video_path)
        
        # PRESERVE FOCUS: Remember currently selected item before refresh
        current_item = self.image_list.currentItem()
        current_file_path = current_item.data(Qt.ItemDataRole.UserRole) if current_item else None
        
        # Add extracted frames to workspace
        workspace_item = self.workspace.get_item(video_path)
        if workspace_item:
            workspace_item.extracted_frames = extracted_frames
            
            # Add individual frame items to workspace
            for frame_path in extracted_frames:
                frame_item = ImageItem(frame_path, "extracted_frame")
                frame_item.parent_video = video_path
                self.workspace.add_item(frame_item)
        
        self.workspace.mark_modified()
        
        # Update title and refresh view
        self.update_window_title()
        self.refresh_view()
        
        # RESTORE FOCUS: Find and select the same item after refresh
        if current_file_path:
            # Use QTimer.singleShot to ensure focus restoration happens after UI update
            def restore_focus():
                for i in range(self.image_list.count()):
                    item = self.image_list.item(i)
                    if item and item.data(Qt.ItemDataRole.UserRole) == current_file_path:
                        self.image_list.setCurrentItem(item)
                        self.image_list.scrollToItem(item)  # Ensure it's visible
                        break
            
            QTimer.singleShot(0, restore_focus)
        
        # If immediate processing is requested, start processing frames
        if processing_config.get("process_immediately", False):
            self.process_extracted_frames(extracted_frames, processing_config)
        
        self.status_bar.showMessage(f"Video extraction complete: {len(extracted_frames)} frames created", 3000)
    
    def process_extracted_frames(self, frame_paths: list, processing_config: dict):
        """Process all extracted frames with the specified configuration"""
        model = processing_config["model"]
        prompt_style = processing_config["prompt_style"]
        custom_prompt = processing_config["custom_prompt"]
        
        # Sort frame paths to ensure sequential processing (frame_0001, frame_0002, etc.)
        frame_paths = sorted(frame_paths)
        
        # PRESERVE FOCUS: Remember currently selected item before processing
        current_selection = self.image_list.currentRow()
        current_item = self.image_list.currentItem()
        current_file_path = current_item.data(Qt.ItemDataRole.UserRole) if current_item else None
        
        # Track frame processing for accurate title bar progress
        total_frames = len(frame_paths)
        
        # Process each frame
        for i, frame_path in enumerate(frame_paths):
            self.processing_items.add(frame_path)  # Mark as processing
            worker = ProcessingWorker(frame_path, model, prompt_style, custom_prompt)
            
            # Enhanced progress callback to show frame progress
            def make_progress_callback(frame_index, total):
                def on_progress(message):
                    # Update window title with frame progress
                    progress_msg = f"Processing: {frame_index + 1} of {total} frames - {message}"
                    self.update_window_title(progress_msg)
                return on_progress
            
            worker.progress_updated.connect(make_progress_callback(i, total_frames))
            worker.processing_complete.connect(self.on_processing_complete)
            worker.processing_failed.connect(self.on_processing_failed)
            
            self.processing_workers.append(worker)
            worker.start()
        
        # Update title to show processing status
        self.update_window_title(f"Processing: {total_frames} frames")
        
        # Refresh view to show processing indicators
        self.refresh_view()
        
        # RESTORE FOCUS: Find and select the same item after refresh
        if current_file_path:
            # Use QTimer.singleShot to ensure focus restoration happens after UI update
            def restore_focus():
                for i in range(self.image_list.count()):
                    item = self.image_list.item(i)
                    if item and item.data(Qt.ItemDataRole.UserRole) == current_file_path:
                        self.image_list.setCurrentItem(item)
                        self.image_list.scrollToItem(item)  # Ensure it's visible
                        break
            
            QTimer.singleShot(0, restore_focus)

    def closeEvent(self, event):
        """Handle application close - check for unsaved changes"""
        if self.workspace and not self.workspace.saved:
            # Ask user if they want to save changes
            reply = QMessageBox.question(
                self, 
                "Unsaved Changes", 
                "You have unsaved changes in your workspace. Do you want to save before closing?",
                QMessageBox.StandardButton.Save | 
                QMessageBox.StandardButton.Discard | 
                QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save
            )
            
            if reply == QMessageBox.StandardButton.Save:
                # Try to save the workspace
                if self.workspace.file_path:
                    try:
                        self.workspace.save()
                        event.accept()
                    except Exception as e:
                        QMessageBox.critical(self, "Save Error", f"Failed to save workspace:\n{e}")
                        event.ignore()
                else:
                    # Need to save as new file
                    if self.save_workspace_as():
                        event.accept()
                    else:
                        event.ignore()
            elif reply == QMessageBox.StandardButton.Discard:
                event.accept()
            else:  # Cancel
                event.ignore()
        else:
            # No changes or no workspace, close normally
            event.accept()


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("ImageDescriber")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Image Description Toolkit")
    
    # Create and show main window
    window = ImageDescriberGUI()
    window.show()
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
