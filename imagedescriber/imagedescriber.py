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
    QSpinBox, QDoubleSpinBox, QRadioButton, QButtonGroup, QGroupBox, QLineEdit
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
    
    def _announce_selection(self):
        """Provide enhanced announcements for screen readers"""
        current = self.currentItem()
        if current:
            # Get accessible description from the item
            accessible_desc = current.data(0, Qt.ItemDataRole.AccessibleDescriptionRole)
            if accessible_desc:
                # Set it as the widget's accessible description for immediate announcement
                self.setAccessibleDescription(f"Selected: {accessible_desc}")


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
            self.focusNextChild()
            event.accept()
        elif event.key() == Qt.Key.Key_Backtab:
            # Shift+Tab should move to previous widget
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
    """Document model for ImageDescriber workspace"""
    def __init__(self):
        self.version = WORKSPACE_VERSION
        self.directory_path = ""
        self.items: Dict[str, ImageItem] = {}
        self.created = datetime.now().isoformat()
        self.modified = self.created
        self.saved = False
        
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
            "directory_path": self.directory_path,
            "items": {path: item.to_dict() for path, item in self.items.items()},
            "created": self.created,
            "modified": self.modified
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        workspace = cls()
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
        self.end_time.setAccessibleDescription("End time for frame extraction in seconds (0 means end of video)")
        extraction_layout.addRow("End Time:", self.end_time)
        
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
        
        # Processing options
        self.process_after_extraction = QCheckBox("Process frames immediately after extraction")
        self.process_after_extraction.setChecked(True)
        processing_layout.addRow(self.process_after_extraction)
        
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
    
    def populate_prompts(self, prompts):
        """Populate the prompt combo box"""
        self.prompt_combo.clear()
        self.prompt_combo.addItems(prompts)


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
        self.text_area = QTextEdit()
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
        
        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # Left panel - Image list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        left_layout.addWidget(QLabel("Images:"))
        self.image_tree = AccessibleTreeWidget()
        self.image_tree.setHeaderLabels(["File", "Status"])
        self.image_tree.setAccessibleName("Image List")
        self.image_tree.setAccessibleDescription("List of images in the workspace. Use arrow keys to navigate, P to process selected image, B to mark for batch.")
        self.image_tree.itemSelectionChanged.connect(self.on_image_selection_changed)
        # Enable proper focus tracking
        self.image_tree.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        left_layout.addWidget(self.image_tree)
        
        # Batch info
        self.batch_label = QLabel("Batch Queue: 0 items")
        left_layout.addWidget(self.batch_label)
        
        splitter.addWidget(left_panel)
        
        # Right panel - Descriptions
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        right_layout.addWidget(QLabel("Descriptions:"))
        self.description_tree = AccessibleTreeWidget()
        self.description_tree.setHeaderLabels(["Description", "Model", "Created"])
        self.description_tree.setAccessibleName("Description List")
        self.description_tree.setAccessibleDescription("List of descriptions for the selected image. Use arrow keys to navigate and view different descriptions.")
        self.description_tree.itemSelectionChanged.connect(self.on_description_selection_changed)
        # Enable proper focus tracking
        self.description_tree.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        right_layout.addWidget(self.description_tree)
        
        # Description text
        right_layout.addWidget(QLabel("Description Text:"))
        self.description_text = QTextEdit()
        self.description_text.setReadOnly(True)
        self.description_text.setAccessibleName("Description Text")
        self.description_text.setAccessibleDescription("Displays the full image description. Use arrow keys to navigate through the text.")
        right_layout.addWidget(self.description_text)
        
        splitter.addWidget(right_panel)
        
        # Set splitter proportions
        splitter.setSizes([400, 600])
        
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
        
        process_all_action = QAction("Process All", self)
        process_all_action.triggered.connect(self.process_all)
        process_menu.addAction(process_all_action)
        
        # Descriptions menu
        desc_menu = menubar.addMenu("Descriptions")
        
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
        
        expand_action = QAction("Expand All", self)
        expand_action.triggered.connect(self.expand_all)
        view_menu.addAction(expand_action)
        
        collapse_action = QAction("Collapse All", self)
        collapse_action.triggered.connect(self.collapse_all)
        view_menu.addAction(collapse_action)
        
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
        
        # Show all descriptions in list
        show_all_descriptions_action = QAction("Show All Descriptions in List", self)
        show_all_descriptions_action.triggered.connect(self.show_all_descriptions_dialog)
        view_menu.addAction(show_all_descriptions_action)
    
    def setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        # Additional shortcuts not in menus
        pass
    
    def update_window_title(self):
        """Update the window title"""
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
        elif self.workspace.directory_path:
            title += f" - {Path(self.workspace.directory_path).name}"
            if not self.workspace.saved:
                title += " *"
        
        # Add batch processing progress if active
        if self.batch_processing:
            title += f" - Batch Processing: {self.batch_completed} of {self.batch_total}"
        
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
        
        self.workspace = ImageWorkspace()
        self.current_workspace_file = None
        self.batch_queue.clear()
        self.image_tree.clear()
        self.description_tree.clear()
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
        """Load images from a directory"""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Image Directory", self.workspace.directory_path or str(Path.home())
        )
        
        if directory:
            self.workspace.directory_path = directory
            self.workspace.mark_modified()
            self.load_images_from_directory(directory)
            self.refresh_view()
            self.update_window_title()
    
    def load_images_from_directory(self, directory: str):
        """Load all images from directory into workspace"""
        directory_path = Path(directory)
        
        # Supported extensions
        image_exts = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.heic', '.heif'}
        video_exts = {'.mp4', '.mov', '.avi', '.mkv', '.wmv'}
        
        for file_path in directory_path.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in (image_exts | video_exts):
                if str(file_path) not in self.workspace.items:
                    item_type = "video" if file_path.suffix.lower() in video_exts else "image"
                    item = ImageItem(str(file_path), item_type)
                    self.workspace.add_item(item)
    
    # UI update methods
    def refresh_view(self):
        """Refresh the image tree view"""
        self.image_tree.clear()
        
        for file_path, item in self.workspace.items.items():
            # Skip extracted frames - they'll be shown as children
            if item.item_type == "extracted_frame":
                continue
            
            # Apply filter
            if self.filter_mode == "described" and not item.descriptions:
                continue
            elif self.filter_mode == "batch" and not item.batch_marked:
                continue
                
            # Create top-level item
            tree_item = QTreeWidgetItem(self.image_tree)
            
            # Build display name with status indicators
            file_name = Path(file_path).name
            display_name = file_name
            accessibility_desc = file_name
            
            # Add processing indicator
            if file_path in self.processing_items:
                display_name = f"p {display_name}"
                accessibility_desc = f"p {accessibility_desc} - processing"
            
            # Add description indicator
            if item.descriptions:
                desc_count = len(item.descriptions)
                if file_path not in self.processing_items:  # Don't duplicate if already has 'p'
                    display_name = f"d{desc_count} {display_name}"
                    accessibility_desc = f"d {accessibility_desc} - has {desc_count} descriptions"
                else:
                    accessibility_desc += f" - has {desc_count} descriptions"
                tree_item.setText(1, f"{desc_count} descriptions")
            else:
                tree_item.setText(1, "No descriptions")
                if file_path not in self.processing_items:
                    accessibility_desc += " - no descriptions"
            
            # Add batch indicator
            if item.batch_marked:
                if file_path not in self.processing_items:  # Don't duplicate if already has 'p'
                    display_name = f"b {display_name}"
                    accessibility_desc = f"b {accessibility_desc} - marked for batch processing"
                else:
                    accessibility_desc += " - marked for batch processing"
                    
            tree_item.setText(0, display_name)
            tree_item.setData(0, Qt.ItemDataRole.AccessibleDescriptionRole, accessibility_desc)
            tree_item.setData(0, Qt.ItemDataRole.UserRole, file_path)
            
            # Mark batch items with accessible colors
            if item.batch_marked:
                # Use light blue background (#E3F2FD) which provides good contrast with black text
                tree_item.setBackground(0, QColor(227, 242, 253))  # Light blue
                tree_item.setBackground(1, QColor(227, 242, 253))
            
            # Add extracted frames as children for videos
            if item.item_type == "video" and item.extracted_frames:
                for frame_path in item.extracted_frames:
                    frame_item = QTreeWidgetItem(tree_item)
                    frame_name = Path(frame_path).name
                    
                    # Build frame display name with indicators
                    frame_display = f"  └─ {frame_name}"
                    frame_accessibility = f"{frame_name} - frame"
                    
                    # Add processing indicator for frame
                    if frame_path in self.processing_items:
                        frame_display = f"  └─ p {frame_name}"
                        frame_accessibility = f"p {frame_name} - frame processing"
                    
                    # Check if frame has descriptions
                    frame_workspace_item = self.workspace.get_item(frame_path)
                    if frame_workspace_item and frame_workspace_item.descriptions:
                        desc_count = len(frame_workspace_item.descriptions)
                        if frame_path not in self.processing_items:
                            frame_display = f"  └─ d{desc_count} {frame_name}"
                            frame_accessibility = f"d {frame_name} - frame with {desc_count} descriptions"
                        else:
                            frame_accessibility += f" with {desc_count} descriptions"
                        frame_item.setText(1, f"{desc_count} descriptions")
                    else:
                        frame_item.setText(1, "No descriptions")
                        if frame_path not in self.processing_items:
                            frame_accessibility += " with no descriptions"
                    
                    frame_item.setText(0, frame_display)
                    frame_item.setData(0, Qt.ItemDataRole.AccessibleDescriptionRole, frame_accessibility)
                    frame_item.setData(0, Qt.ItemDataRole.UserRole, frame_path)
        
        self.image_tree.expandAll()
        self.update_batch_label()
    
    def update_batch_label(self):
        """Update the batch queue label"""
        batch_count = sum(1 for item in self.workspace.items.values() if item.batch_marked)
        self.batch_label.setText(f"Batch Queue: {batch_count} items")
    
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
    
    # Event handlers
    def on_image_selection_changed(self):
        """Handle image selection change"""
        current_item = self.image_tree.currentItem()
        if current_item:
            file_path = current_item.data(0, Qt.ItemDataRole.UserRole)
            self.load_descriptions_for_image(file_path)
    
    def on_description_selection_changed(self):
        """Handle description selection change"""
        current_item = self.description_tree.currentItem()
        
        if current_item:
            desc_id = current_item.data(0, Qt.ItemDataRole.UserRole)
            
            # Find the description
            image_item = self.image_tree.currentItem()
            if image_item:
                file_path = image_item.data(0, Qt.ItemDataRole.UserRole)
                workspace_item = self.workspace.get_item(file_path)
                
                if workspace_item:
                    for desc in workspace_item.descriptions:
                        if desc.id == desc_id:
                            self.description_text.setPlainText(desc.text)
                            # Update accessibility description with character count
                            char_count = len(desc.text)
                            self.description_text.setAccessibleDescription(
                                f"Image description with {char_count} characters: {desc.text}"
                            )
                            return
            
            self.description_text.clear()
            self.description_text.setAccessibleDescription("No description selected.")
        else:
            self.description_text.clear()
            self.description_text.setAccessibleDescription("No description selected.")
    
    def load_descriptions_for_image(self, file_path: str):
        """Load descriptions for the selected image"""
        self.description_tree.clear()
        
        workspace_item = self.workspace.get_item(file_path)
        if workspace_item and workspace_item.descriptions:
            for i, desc in enumerate(workspace_item.descriptions):
                tree_item = QTreeWidgetItem(self.description_tree)
                
                # Show model and prompt type FIRST - simplified format
                model_text = desc.model if desc.model else "Unknown Model"
                if desc.custom_prompt:
                    prompt_text = "custom"
                elif desc.prompt_style:
                    prompt_text = desc.prompt_style
                else:
                    prompt_text = "default"
                
                # Show description preview after model info
                desc_preview = desc.text[:100] + "..." if len(desc.text) > 100 else desc.text
                created_date = desc.created.split('T')[0] if 'T' in desc.created else desc.created
                
                tree_item.setText(0, f"{model_text} {prompt_text}: {desc_preview}")
                tree_item.setText(1, model_text)
                tree_item.setText(2, created_date)
                tree_item.setData(0, Qt.ItemDataRole.UserRole, desc.id)
                
                # Set full text for screen readers - just model, prompt, description, then date
                tree_item.setData(0, Qt.ItemDataRole.AccessibleTextRole,
                                f"{model_text} {prompt_text}: {desc.text}. Created {created_date}")
                # Set AccessibleDescriptionRole for additional context
                tree_item.setData(0, Qt.ItemDataRole.AccessibleDescriptionRole,
                                f"{model_text} {prompt_text}")
            
            # Auto-select the first description
            if self.description_tree.topLevelItemCount() > 0:
                first_item = self.description_tree.topLevelItem(0)
                self.description_tree.setCurrentItem(first_item)
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
        current_item = self.image_tree.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select an image or video to process.")
            return
        
        file_path = current_item.data(0, Qt.ItemDataRole.UserRole)
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
            worker = ProcessingWorker(file_path, model, prompt_style, custom_prompt)
            worker.progress_updated.connect(self.on_processing_progress)
            worker.processing_complete.connect(self.on_processing_complete)
            worker.processing_failed.connect(self.on_processing_failed)
            
            self.processing_workers.append(worker)
            worker.start()
            self.update_stop_button_state()
            
            # Refresh view to show processing indicator
            self.refresh_view()
    
    def process_video(self, file_path: str):
        """Process a video file with frame extraction options"""
        # Show video processing dialog
        dialog = VideoProcessingDialog(self)
        
        # Populate model and prompt options using the same logic as ProcessingDialog
        self.populate_video_dialog_options(dialog)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            extraction_config = dialog.get_extraction_config()
            processing_config = dialog.get_processing_config()
            
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
        current_item = self.image_tree.currentItem()
        if not current_item:
            return
        
        file_path = current_item.data(0, Qt.ItemDataRole.UserRole)
        workspace_item = self.workspace.get_item(file_path)
        
        if workspace_item:
            workspace_item.batch_marked = not workspace_item.batch_marked
            self.workspace.mark_modified()
            
            # Update UI with accessible colors
            if workspace_item.batch_marked:
                # Use light blue background (#E3F2FD) which provides good contrast with black text
                current_item.setBackground(0, QColor(227, 242, 253))  # Light blue
                current_item.setBackground(1, QColor(227, 242, 253))
            else:
                current_item.setBackground(0, Qt.GlobalColor.transparent)
                current_item.setBackground(1, Qt.GlobalColor.transparent)
            
            self.update_batch_label()
    
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
                
            worker = ProcessingWorker(item.file_path, model, prompt_style, custom_prompt)
            worker.progress_updated.connect(self.on_processing_progress)
            worker.processing_complete.connect(self.on_batch_item_complete)
            worker.processing_failed.connect(self.on_batch_item_failed)
            
            self.processing_workers.append(worker)
            worker.start()
        
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
        """Extract frames from all videos in the workspace"""
        video_items = [item for item in self.workspace.items.values() if item.item_type == "video"]
        
        if not video_items:
            QMessageBox.information(self, "No Videos", "No video files found in workspace.")
            return
        
        for item in video_items:
            worker = ConversionWorker(item.file_path, "video")
            worker.progress_updated.connect(self.on_processing_progress)
            worker.conversion_complete.connect(self.on_conversion_complete)
            worker.conversion_failed.connect(self.on_processing_failed)
            
            self.conversion_workers.append(worker)
            worker.start()
    
    # Description management
    def edit_description(self):
        """Edit the selected description"""
        current_desc_item = self.description_tree.currentItem()
        current_image_item = self.image_tree.currentItem()
        
        if not current_desc_item or not current_image_item:
            return
        
        desc_id = current_desc_item.data(0, Qt.ItemDataRole.UserRole)
        file_path = current_image_item.data(0, Qt.ItemDataRole.UserRole)
        workspace_item = self.workspace.get_item(file_path)
        
        if workspace_item:
            for desc in workspace_item.descriptions:
                if desc.id == desc_id:
                    new_text, ok = QInputDialog.getMultiLineText(
                        self, "Edit Description", "Description:", desc.text
                    )
                    if ok:
                        desc.text = new_text
                        self.workspace.mark_modified()
                        self.load_descriptions_for_image(file_path)
                        self.description_text.setPlainText(new_text)
                    break
    
    def delete_description(self):
        """Delete the selected description"""
        current_desc_item = self.description_tree.currentItem()
        current_image_item = self.image_tree.currentItem()
        
        if not current_desc_item or not current_image_item:
            return
        
        reply = QMessageBox.question(
            self, "Delete Description",
            "Are you sure you want to delete this description?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            desc_id = current_desc_item.data(0, Qt.ItemDataRole.UserRole)
            file_path = current_image_item.data(0, Qt.ItemDataRole.UserRole)
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
        current_item = self.image_tree.currentItem()
        if current_item:
            file_path = current_item.data(0, Qt.ItemDataRole.UserRole)
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
        current_item = self.image_tree.currentItem()
        if current_item:
            file_path = current_item.data(0, Qt.ItemDataRole.UserRole)
            QGuiApplication.clipboard().setText(file_path)
            self.status_bar.showMessage("Image path copied to clipboard", 2000)
    
    # View operations
    def expand_all(self):
        """Expand all tree items"""
        self.image_tree.expandAll()
    
    def collapse_all(self):
        """Collapse all tree items"""
        self.image_tree.collapseAll()

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
        """Process all images and extract video frames"""
        if not self.workspace.items:
            QMessageBox.information(self, "No Items", "No images or videos found in workspace.")
            return
        
        # Show processing dialog first
        dialog = ProcessingDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            model, prompt_style, custom_prompt = dialog.get_selections()
            
            # Optional verification
            if not getattr(self, '_skip_verification', True):
                if not self.check_ollama_status():
                    return
                if not self.verify_model_available(model):
                    return
            
            # Collect all items for processing
            all_items = []
            video_items = []
            
            for item in self.workspace.items.values():
                if item.item_type == "image":
                    all_items.append(item)
                elif item.item_type == "video":
                    video_items.append(item)
            
            # Extract frames from videos first
            for video_item in video_items:
                if not video_item.extracted_frames:
                    # TODO: Implement automatic video frame extraction
                    pass
            
            # Process all images (including extracted frames)
            if all_items:
                self.batch_total = len(all_items)
                self.batch_completed = 0
                self.batch_processing = True
                self.update_window_title()
                
                for item in all_items:
                    worker = ProcessingWorker(item.file_path, model, prompt_style, custom_prompt)
                    worker.progress_updated.connect(self.on_processing_progress)
                    worker.processing_complete.connect(self.on_batch_item_complete)
                    worker.processing_failed.connect(self.on_batch_item_failed)
                    
                    self.processing_workers.append(worker)
                    worker.start()
                
                self.update_stop_button_state()

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
        
        # Update UI
        self.refresh_view()
        
        # Remove completed worker from list
        sender_worker = self.sender()
        if sender_worker in self.processing_workers:
            self.processing_workers.remove(sender_worker)
        self.update_stop_button_state()
        
        # If this is the currently selected image, refresh descriptions
        current_item = self.image_tree.currentItem()
        if current_item and current_item.data(0, Qt.ItemDataRole.UserRole) == file_path:
            self.load_descriptions_for_image(file_path)
        
        self.status_bar.showMessage(f"Processing complete: {Path(file_path).name}", 3000)
    
    def on_processing_failed(self, file_path: str, error: str):
        """Handle processing failure"""
        # Remove from processing set
        self.processing_items.discard(file_path)
        
        # Remove failed worker from list
        sender_worker = self.sender()
        if sender_worker in self.processing_workers:
            self.processing_workers.remove(sender_worker)
        self.update_stop_button_state()
        
        self.refresh_view()  # Update display
        
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
        self.refresh_view()
        
        # If immediate processing is requested, start processing frames
        if processing_config.get("process_immediately", False):
            self.process_extracted_frames(extracted_frames, processing_config)
        
        self.status_bar.showMessage(f"Video extraction complete: {len(extracted_frames)} frames created", 3000)
    
    def process_extracted_frames(self, frame_paths: list, processing_config: dict):
        """Process all extracted frames with the specified configuration"""
        model = processing_config["model"]
        prompt_style = processing_config["prompt_style"]
        custom_prompt = processing_config["custom_prompt"]
        
        # Process each frame
        for frame_path in frame_paths:
            self.processing_items.add(frame_path)  # Mark as processing
            worker = ProcessingWorker(frame_path, model, prompt_style, custom_prompt)
            worker.progress_updated.connect(self.on_processing_progress)
            worker.processing_complete.connect(self.on_processing_complete)
            worker.processing_failed.connect(self.on_processing_failed)
            
            self.processing_workers.append(worker)
            worker.start()
        
        # Refresh view to show processing indicators
        self.refresh_view()

    def closeEvent(self, event):
        """Handle application close - check for unsaved changes"""
        if self.workspace and self.workspace.is_modified():
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
