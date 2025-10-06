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
import re
import subprocess
import threading
import time
import base64
import tempfile
import shutil
import webbrowser
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

try:
    import openai
except ImportError:
    openai = None

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QLabel, QTextEdit, QSplitter,
    QMenuBar, QMenu, QFileDialog, QMessageBox, QDialog, QDialogButtonBox,
    QComboBox, QProgressBar, QProgressDialog, QStatusBar, QTreeWidget, QTreeWidgetItem,
    QInputDialog, QPlainTextEdit, QCheckBox, QPushButton, QFormLayout,
    QSpinBox, QDoubleSpinBox, QRadioButton, QButtonGroup, QGroupBox, QLineEdit,
    QTextEdit, QTabWidget, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QMutex, QMutexLocker
from PyQt6.QtGui import (
    QAction, QKeySequence, QClipboard, QGuiApplication, QPixmap, QImage,
    QFont, QColor, QDoubleValidator, QIntValidator
)

# Import our refactored modules
from ai_providers import (
    AIProvider, OllamaProvider, OpenAIProvider, ClaudeProvider, ONNXProvider, CopilotProvider, ObjectDetectionProvider,
    get_available_providers, get_all_providers, _ollama_provider, _ollama_cloud_provider, _openai_provider, _claude_provider, _onnx_provider, _copilot_provider, _object_detection_provider, _grounding_dino_provider, _grounding_dino_hybrid_provider
)
from data_models import ImageDescription, ImageItem, ImageWorkspace, WORKSPACE_VERSION

# Import provider capabilities for dynamic UI
try:
    import sys
    from pathlib import Path
    # Add models directory to path for provider_configs import
    models_path = Path(__file__).parent.parent / 'models'
    if str(models_path) not in sys.path:
        sys.path.insert(0, str(models_path))
    from provider_configs import supports_prompts, supports_custom_prompts, get_provider_capabilities
    from model_options import get_all_options_for_provider, get_default_value
except ImportError:
    # Fallback if provider_configs not available
    def supports_prompts(provider_name: str) -> bool:
        return provider_name not in ["ONNX", "HuggingFace", "Object Detection", "Grounding DINO"]
    def supports_custom_prompts(provider_name: str) -> bool:
        return provider_name not in ["ONNX", "HuggingFace", "Object Detection", "Grounding DINO"]
    def get_provider_capabilities(provider_name: str) -> dict:
        return {}
    def get_all_options_for_provider(provider_name: str) -> dict:
        return {}
    def get_default_value(option_config: dict) -> any:
        return option_config.get("default")
from worker_threads import (
    ProcessingWorker, WorkflowProcessWorker, ConversionWorker, 
    VideoProcessingWorker, ChatProcessingWorker
)
from ui_components import AccessibleTreeWidget, AccessibleNumericInput, AccessibleTextEdit
from dialogs import DirectorySelectionDialog, ProcessingDialog, ChatWindow


# ================================
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
        """Override to handle Tab key properly for accessibility and pass special keys to parent"""
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
        elif event.key() == Qt.Key.Key_Z and event.modifiers() == Qt.KeyboardModifier.NoModifier:
            # Pass Z key to parent ImageDescriber for auto-rename functionality
            print("DEBUG: AccessibleTreeWidget received Z key, passing to parent")
            parent = self.parent()
            while parent:
                if hasattr(parent, 'auto_rename_item'):
                    print("DEBUG: Found ImageDescriber parent, calling auto_rename_item")
                    parent.auto_rename_item()
                    event.accept()
                    return
                parent = parent.parent()
            # If no parent with auto_rename_item found, use default behavior
            super().keyPressEvent(event)
        else:
            # For all other keys, use default behavior
            super().keyPressEvent(event)


# ================================
# EXISTING CLASSES (UNCHANGED)
# ================================


class ImageDescription:
    """Represents a single description for an image"""
    def __init__(self, text: str, model: str = "", prompt_style: str = "", 
                 created: str = "", custom_prompt: str = "", provider: str = ""):
        self.text = text
        self.model = model
        self.prompt_style = prompt_style
        self.created = created or datetime.now().isoformat()
        self.custom_prompt = custom_prompt
        self.provider = provider
        self.id = f"{int(time.time() * 1000)}"  # Unique ID
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "model": self.model,
            "prompt_style": self.prompt_style,
            "created": self.created,
            "custom_prompt": self.custom_prompt,
            "provider": self.provider
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        desc = cls(
            text=data.get("text", ""),
            model=data.get("model", ""),
            prompt_style=data.get("prompt_style", ""),
            created=data.get("created", ""),
            custom_prompt=data.get("custom_prompt", ""),
            provider=data.get("provider", "")
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
        self.display_name = ""  # Custom display name for this version
        
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
            "extracted_frames": self.extracted_frames,
            "display_name": self.display_name
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        item = cls(data["file_path"], data.get("item_type", "image"))
        item.descriptions = [ImageDescription.from_dict(d) for d in data.get("descriptions", [])]
        item.batch_marked = data.get("batch_marked", False)
        item.parent_video = data.get("parent_video")
        item.extracted_frames = data.get("extracted_frames", [])
        item.display_name = data.get("display_name", "")
        return item


class ImageWorkspace:
    """Document model for ImageDescriber workspace - Enhanced for multiple directories"""
    def __init__(self, new_workspace=False):
        self.version = WORKSPACE_VERSION
        self.directory_path = ""  # Keep for backward compatibility
        self.directory_paths: List[str] = []  # New: support multiple directories
        self.items: Dict[str, ImageItem] = {}
        self.chat_sessions: Dict[str, dict] = {}  # New: chat sessions storage
        self.created = datetime.now().isoformat()
        self.modified = self.created
        self.saved = new_workspace  # New workspaces start as saved
        self.file_path = None  # Path to the workspace file
        
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
            "chat_sessions": getattr(self, 'chat_sessions', {}),  # Include chat sessions
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
        workspace.chat_sessions = data.get("chat_sessions", {})  # Load chat sessions
        workspace.created = data.get("created", workspace.created)
        workspace.modified = data.get("modified", workspace.modified)
        workspace.saved = True
        return workspace
        workspace.saved = True
        return workspace


class ProcessingWorker(QThread):
    """Worker thread for AI processing"""
    progress_updated = pyqtSignal(str, str)  # file_path, message
    processing_complete = pyqtSignal(str, str, str, str, str, str)  # file_path, description, provider, model, prompt_style, custom_prompt
    processing_failed = pyqtSignal(str, str)  # file_path, error
    
    def __init__(self, file_path: str, provider: str, model: str, prompt_style: str, custom_prompt: str = "", yolo_settings: dict = None, detection_settings: dict = None):
        super().__init__()
        self.file_path = file_path
        self.provider = provider
        self.model = model
        self.prompt_style = prompt_style
        self.custom_prompt = custom_prompt
        # Support both old yolo_settings and new detection_settings parameters for backward compatibility
        self.detection_settings = detection_settings or yolo_settings or {}
        
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
            self.progress_updated.emit(self.file_path, f"Processing with {self.provider} {self.model}...")
            
            # Process the image with selected provider
            description = self.process_with_ai(self.file_path, prompt_text)
            
            # Emit success
            self.processing_complete.emit(
                self.file_path, description, self.provider, self.model, self.prompt_style, self.custom_prompt
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
    
    def process_with_ai(self, image_path: str, prompt: str) -> str:
        """Process image with selected AI provider"""
        # Get available providers
        providers = get_available_providers()
        
        if self.provider not in providers:
            raise Exception(f"Provider '{self.provider}' not available")
        
        provider = providers[self.provider]
        
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
            
            print(f"Processing {path_obj.name} with {self.provider} {self.model}")
            print(f"Image size: {len(image_data)} bytes")
            print(f"Prompt: {prompt[:100]}...")
            
            # Process with the selected provider
            def progress_callback(message, details=""):
                self.progress_updated.emit(self.file_path, f"{message}")
            
            # Pass detection settings if using detection provider
            if self.provider == "object_detection" and self.detection_settings:
                description = provider.describe_image(image_path, prompt, self.model, yolo_settings=self.detection_settings)
            elif self.provider in ["grounding_dino", "grounding_dino_hybrid"] and self.detection_settings:
                # Pass GroundingDINO settings
                description = provider.describe_image(image_path, prompt, self.model, **self.detection_settings)
            else:
                description = provider.describe_image(image_path, prompt, self.model)
            
            return description
                
        except Exception as e:
            print(f"AI processing error: {str(e)}")
            print(f"Provider: {self.provider}")
            print(f"Model: {self.model}")
            print(f"Image path: {image_path}")
            
            # Try to get more detailed error info
            try:
                import traceback
                traceback.print_exc()
            except:
                pass
            
            raise Exception(f"AI processing failed: {str(e)}")
    
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
    progress_updated = pyqtSignal(str, str)  # file_path, message
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
            
            self.progress_updated.emit(self.file_path, "Converting to JPG...")
            
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
            
            self.progress_updated.emit(self.file_path, "Extracting video frames...")
            
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


class ChatProcessingWorker(QThread):
    """Worker thread for processing chat messages with AI"""
    chat_response = pyqtSignal(str, str)  # chat_id, response
    chat_failed = pyqtSignal(str, str)    # chat_id, error
    
    def __init__(self, chat_session: dict, message: str):
        super().__init__()
        self.chat_session = chat_session
        self.message = message
        self._stop_requested = False
        
    def stop(self):
        """Request the worker to stop"""
        self._stop_requested = True
        
    def run(self):
        try:
            if self._stop_requested:
                return
                
            response = self.process_chat_with_ai(self.chat_session, self.message)
            
            if not self._stop_requested:
                self.chat_response.emit(self.chat_session['id'], response)
        except Exception as e:
            if not self._stop_requested:
                self.chat_failed.emit(self.chat_session['id'], str(e))
    
    def process_chat_with_ai(self, chat_session: dict, message: str) -> str:
        """Process chat message with AI provider"""
        provider = chat_session['provider']
        model = chat_session['model']
        
        # Check if this is a detection query for GroundingDINO
        detection_query = self.parse_detection_query(message)
        if detection_query:
            return self.process_detection_query(chat_session, message, detection_query)
        
        # Build conversation context from chat history
        conversation_context = self.build_conversation_context(chat_session, message)
        
        if provider == "ollama":
            return self.process_with_ollama_chat(model, chat_session, conversation_context)
        elif provider == "ollama_cloud":
            return self.process_with_ollama_chat(model, chat_session, conversation_context)
        elif provider == "openai":
            return self.process_with_openai_chat(model, chat_session, conversation_context)
        elif provider == "claude":
            return self.process_with_claude_chat(model, chat_session, conversation_context)
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    def build_conversation_context(self, chat_session: dict, current_message: str) -> str:
        """Build conversation context from chat history for providers that use simple prompts"""
        conversation = chat_session.get('conversation', [])
        provider = chat_session['provider']
        
        # Get context limits based on provider
        context_config = self.get_context_config(provider)
        max_messages = context_config['max_messages']
        max_chars = context_config['max_chars']
        
        # Get recent conversation history (excluding the current message which isn't added yet)
        recent_messages = conversation[-max_messages:] if len(conversation) > max_messages else conversation
        
        # Build context string
        context_parts = []
        
        # Add conversation history
        if recent_messages:
            context_parts.append("Previous conversation:")
            
            # Add messages, but truncate if too long
            total_chars = 0
            messages_to_include = []
            
            # Work backwards to prioritize recent messages
            for msg in reversed(recent_messages):
                msg_text = f"{'User' if msg['type'] == 'user' else 'Assistant'}: {msg['content']}"
                msg_chars = len(msg_text)
                
                if total_chars + msg_chars > max_chars:
                    # If this message would exceed the limit, try to include a truncated version
                    remaining_chars = max_chars - total_chars
                    if remaining_chars > 100:  # Only include if we have reasonable space
                        truncated_content = msg['content'][:remaining_chars-50] + "... [truncated]"
                        msg_text = f"{'User' if msg['type'] == 'user' else 'Assistant'}: {truncated_content}"
                        messages_to_include.insert(0, msg_text)
                    break
                
                messages_to_include.insert(0, msg_text)
                total_chars += msg_chars
            
            context_parts.extend(messages_to_include)
            context_parts.append("")  # Empty line for separation
        
        # Add current message
        context_parts.append(f"User: {current_message}")
        context_parts.append("Assistant:")
        
        return "\n".join(context_parts)
    
    def get_context_config(self, provider: str) -> dict:
        """Get context configuration based on provider type"""
        if provider == "ollama":
            # Local models - more generous with context
            return {
                'max_messages': 20,
                'max_chars': 8000,  # ~2000 tokens
                'strategy': 'generous'
            }
        elif provider == "ollama_cloud":
            # Cloud models - very generous with context (large parameter models)
            return {
                'max_messages': 25,
                'max_chars': 12000,  # ~3000 tokens
                'strategy': 'very_generous'
            }
        elif provider == "openai":
            # Paid API - more conservative
            return {
                'max_messages': 15,
                'max_chars': 4000,  # ~1000 tokens
                'strategy': 'conservative'
            }
        elif provider == "claude":
            # Claude API - similar to OpenAI, paid API with good context handling
            return {
                'max_messages': 15,
                'max_chars': 4000,  # ~1000 tokens
                'strategy': 'conservative'
            }
        else:
            # Default conservative approach
            return {
                'max_messages': 10,
                'max_chars': 2000,
                'strategy': 'conservative'
            }
    
    def build_openai_messages(self, chat_session: dict, current_message: str) -> list:
        """Build OpenAI-format messages array with conversation history"""
        conversation = chat_session.get('conversation', [])
        
        # Use context config for OpenAI
        context_config = self.get_context_config('openai')
        max_messages = context_config['max_messages']
        
        # Get recent conversation history
        recent_messages = conversation[-max_messages:] if len(conversation) > max_messages else conversation
        
        # Build OpenAI messages format
        messages = []
        
        # Add system message if this is the start of conversation
        if not recent_messages:
            messages.append({
                "role": "system",
                "content": "You are a helpful AI assistant. Please provide clear, accurate, and helpful responses to the user's questions."
            })
        
        # Add conversation history with token awareness
        total_estimated_tokens = 0
        max_tokens = 3000  # Conservative limit for context
        
        for msg in recent_messages:
            estimated_tokens = len(msg['content']) // 4  # Rough estimate: 4 chars per token
            if total_estimated_tokens + estimated_tokens > max_tokens:
                # Truncate older messages if needed
                break
                
            if msg['type'] == 'user':
                messages.append({"role": "user", "content": msg['content']})
            else:
                messages.append({"role": "assistant", "content": msg['content']})
            
            total_estimated_tokens += estimated_tokens
        
        # Add current message
        messages.append({"role": "user", "content": current_message})
        
        return messages
    
    def build_claude_messages(self, chat_session: dict, current_message: str) -> list:
        """Build Claude-format messages array with conversation history"""
        conversation = chat_session.get('conversation', [])
        
        # Use context config for Claude (similar to OpenAI)
        context_config = self.get_context_config('claude')
        max_messages = context_config['max_messages']
        
        # Get recent conversation history
        recent_messages = conversation[-max_messages:] if len(conversation) > max_messages else conversation
        
        # Build Claude messages format (Anthropic API uses similar structure to OpenAI)
        messages = []
        
        # Add conversation history with token awareness
        total_estimated_tokens = 0
        max_tokens = 3000  # Conservative limit for context
        
        for msg in recent_messages:
            estimated_tokens = len(msg['content']) // 4  # Rough estimate: 4 chars per token
            if total_estimated_tokens + estimated_tokens > max_tokens:
                # Truncate older messages if needed
                break
                
            if msg['type'] == 'user':
                messages.append({"role": "user", "content": msg['content']})
            else:
                messages.append({"role": "assistant", "content": msg['content']})
            
            total_estimated_tokens += estimated_tokens
        
        # Add current message
        messages.append({"role": "user", "content": current_message})
        
        return messages
    
    def parse_detection_query(self, message: str) -> str:
        """
        Parse message to detect if it's a GroundingDINO detection query.
        Returns the detection query string if it's a detection request, None otherwise.
        """
        import re
        
        message_lower = message.lower()
        
        # Detection keywords that suggest the user wants object detection
        detection_keywords = [
            r'\bfind\b', r'\bdetect\b', r'\blocate\b', r'\bshow\b', 
            r'\bidentify\b', r'\bsearch for\b', r'\blook for\b',
            r'\bwhere is\b', r'\bwhere are\b', r'\bcount\b', r'\bhow many\b'
        ]
        
        # Check if any detection keyword is present
        has_detection_keyword = any(re.search(keyword, message_lower) for keyword in detection_keywords)
        
        if not has_detection_keyword:
            return None
        
        # Extract what they want to detect
        # Common patterns:
        # "find red cars and blue trucks"
        # "detect people wearing hats"
        # "show me all the safety signs"
        # "locate fire exits"
        
        # Remove the keyword and get the object/query part
        for keyword_pattern in detection_keywords:
            match = re.search(keyword_pattern, message_lower)
            if match:
                # Get everything after the keyword
                query_part = message[match.end():].strip()
                
                # Clean up common words
                query_part = re.sub(r'^(the|all|any|me)\b', '', query_part, flags=re.IGNORECASE).strip()
                
                if query_part:
                    return query_part
        
        return None
    
    def process_detection_query(self, chat_session: dict, original_message: str, detection_query: str) -> str:
        """
        Process a detection query using GroundingDINO.
        Returns formatted detection results as a chat response.
        """
        try:
            # Check if GroundingDINO is available
            providers = get_available_providers()
            if 'grounding_dino' not in providers:
                return ("I understand you want to detect objects, but GroundingDINO is not currently available. "
                        "To use text-prompted object detection, please install: pip install groundingdino-py torch torchvision")
            
            # Get the context image path if provided in the message metadata
            # Chat sessions can optionally have a 'context_image' field set by the main window
            context_image = chat_session.get('context_image')
            
            if not context_image:
                return (f"🎯 **Detection Request Recognized**\n\n"
                        f"I understand you want to find: **{detection_query}**\n\n"
                        f"However, I need an image context to perform detection. "
                        f"Please select an image in the workspace first, then ask me to detect objects in it.\n\n"
                        f"**Tip:** You can also use the 'Process Image' button with GroundingDINO provider for direct detection.")
            
            # Run GroundingDINO detection
            provider = providers['grounding_dino']
            
            # Format the query for GroundingDINO (replace spaces with periods if needed)
            formatted_query = detection_query.replace(" and ", " . ").replace(", ", " . ")
            
            # Run detection with custom query
            detection_result = provider.describe_image(
                image_path=context_image,
                prompt="",  # Not used for GroundingDINO
                model="",   # Not used for GroundingDINO
                mode='custom',
                query=formatted_query,
                confidence_threshold=0.25
            )
            
            # Format results for chat
            response = f"🎯 **Detection Results for: {detection_query}**\n\n"
            response += f"📷 Image: {Path(context_image).name}\n\n"
            response += detection_result
            
            return response
        
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            return (f"❌ **Error processing detection query**\n\n"
                    f"Query: {detection_query}\n"
                    f"Error: {str(e)}\n\n"
                    f"Please ensure GroundingDINO is properly installed:\n"
                    f"`pip install groundingdino-py torch torchvision`")
    
    def process_with_ollama_chat(self, model: str, chat_session: dict, context: str) -> str:
        """Process chat with Ollama using conversation context"""
        try:
            import ollama
            
            # Use ollama.generate with full conversation context
            response = ollama.generate(
                model=model,
                prompt=context
            )
            
            if self._stop_requested:
                return "Processing stopped"
            
            if hasattr(response, 'response'):
                return response.response
            elif isinstance(response, dict) and 'response' in response:
                return response['response']
            else:
                return str(response)
                
        except Exception as e:
            raise Exception(f"Ollama processing failed: {str(e)}")
    
    def process_with_openai_chat(self, model: str, chat_session: dict, context: str) -> str:
        """Process chat with OpenAI using conversation history"""
        try:
            # Use the global OpenAI provider that handles API key loading
            global _openai_provider
            
            if not _openai_provider.is_available():
                raise Exception("OpenAI is not available or API key not found. Please ensure openai.txt file contains your API key.")
            
            if self._stop_requested:
                return "Processing stopped"
            
            # Extract the current message from the context
            # The context ends with "User: {message}\nAssistant:"
            current_message = context.split("User: ")[-1].split("\nAssistant:")[0].strip()
            
            # Build OpenAI messages format
            messages = self.build_openai_messages(chat_session, current_message)
            
            response = _openai_provider.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=1000
            )
            
            if response.choices and response.choices[0].message:
                return response.choices[0].message.content
            else:
                raise Exception("Empty response from OpenAI")
            
        except Exception as e:
            if "API key" in str(e).lower():
                raise Exception(f"OpenAI API key error: {str(e)}. Please check that openai.txt file exists and contains a valid API key.")
            else:
                raise Exception(f"OpenAI processing failed: {str(e)}")
    
    def process_with_claude_chat(self, model: str, chat_session: dict, context: str) -> str:
        """Process chat with Claude using conversation history"""
        try:
            # Use the global Claude provider that handles API key loading
            global _claude_provider
            
            if not _claude_provider.is_available():
                raise Exception("Claude is not available or API key not found. Please ensure claude.txt file contains your API key or ANTHROPIC_API_KEY is set.")
            
            if self._stop_requested:
                return "Processing stopped"
            
            # Extract the current message from the context
            # The context ends with "User: {message}\nAssistant:"
            current_message = context.split("User: ")[-1].split("\nAssistant:")[0].strip()
            
            # Build Claude messages format
            messages = self.build_claude_messages(chat_session, current_message)
            
            # Call Claude API using Anthropic Messages API format
            import requests
            
            headers = {
                "x-api-key": _claude_provider.api_key,
                "anthropic-version": _claude_provider.api_version,
                "content-type": "application/json"
            }
            
            payload = {
                "model": model,
                "max_tokens": 1000,
                "messages": messages
            }
            
            response = requests.post(
                f"{_claude_provider.base_url}/messages",
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                raise Exception(f"Claude API error: {response.status_code} - {response.text}")
            
            response_data = response.json()
            
            # Extract text from Claude's response format
            if response_data.get('content') and len(response_data['content']) > 0:
                return response_data['content'][0]['text']
            else:
                raise Exception("Empty response from Claude")
            
        except Exception as e:
            if "API key" in str(e).lower() or "api key" in str(e).lower():
                raise Exception(f"Claude API key error: {str(e)}. Please check that claude.txt file exists and contains a valid API key, or set ANTHROPIC_API_KEY environment variable.")
            else:
                raise Exception(f"Claude processing failed: {str(e)}")
    
    
    # Keep original methods for backward compatibility with image descriptions
    def process_with_ollama(self, model: str, prompt: str) -> str:
        """Process with Ollama (for image descriptions)"""
        try:
            import ollama
            
            # Use ollama.generate for simpler text generation (more reliable than chat)
            response = ollama.generate(
                model=model,
                prompt=prompt
            )
            
            if self._stop_requested:
                return "Processing stopped"
            
            if hasattr(response, 'response'):
                return response.response
            elif isinstance(response, dict) and 'response' in response:
                return response['response']
            else:
                return str(response)
                
        except Exception as e:
            raise Exception(f"Ollama processing failed: {str(e)}")
    
    def process_with_openai(self, model: str, prompt: str) -> str:
        """Process with OpenAI (for image descriptions)"""
        try:
            # Use the global OpenAI provider that handles API key loading
            global _openai_provider
            
            if not _openai_provider.is_available():
                raise Exception("OpenAI is not available or API key not found. Please ensure openai.txt file contains your API key.")
            
            if self._stop_requested:
                return "Processing stopped"
            
            response = _openai_provider.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000
            )
            
            if response.choices and response.choices[0].message:
                return response.choices[0].message.content
            else:
                raise Exception("Empty response from OpenAI")
            
        except Exception as e:
            if "API key" in str(e).lower():
                raise Exception(f"OpenAI API key error: {str(e)}. Please check that openai.txt file exists and contains a valid API key.")
            else:
                raise Exception(f"OpenAI processing failed: {str(e)}")
    
    def process_with_huggingface(self, model: str, prompt: str) -> str:
        """This provider has been removed. Use Ollama, OpenAI, or Claude instead."""
        return "Error: HuggingFace provider has been removed from this version."


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
        self.resize(400, 350)
        
        layout = QVBoxLayout(self)
        
        # Provider selection
        layout.addWidget(QLabel("AI Provider:"))
        self.provider_combo = QComboBox()
        self.populate_providers()
        layout.addWidget(self.provider_combo)
        
        # Model selection
        layout.addWidget(QLabel("AI Model:"))
        self.model_combo = QComboBox()
        layout.addWidget(self.model_combo)
        
        # Connect provider change to update models
        self.provider_combo.currentTextChanged.connect(self.on_provider_changed)
        
        # Prompt style selection (hidden for object detection)
        self.prompt_label = QLabel("Prompt Style:")
        layout.addWidget(self.prompt_label)
        self.prompt_combo = QComboBox()
        self.populate_prompts()
        layout.addWidget(self.prompt_combo)
        
        # Custom prompt option (hidden for object detection)
        self.custom_checkbox = QCheckBox("Use custom prompt")
        layout.addWidget(self.custom_checkbox)
        
        self.custom_prompt = AccessibleTextEdit()
        self.custom_prompt.setMaximumHeight(100)
        self.custom_prompt.setEnabled(False)
        self.custom_prompt.setAccessibleName("Custom Prompt")
        self.custom_prompt.setAccessibleDescription("Enter custom prompt text. Tab key moves to next field.")
        layout.addWidget(self.custom_prompt)
        
        self.custom_checkbox.toggled.connect(self.custom_prompt.setEnabled)
        
        # YOLO Object Detection Settings (shown only for object detection provider)
        self.yolo_settings_label = QLabel("🎯 Object Detection Settings:")
        self.yolo_settings_label.setStyleSheet("font-weight: bold; color: #2b5aa0;")
        layout.addWidget(self.yolo_settings_label)
        
        # Confidence threshold setting
        confidence_layout = QHBoxLayout()
        confidence_layout.addWidget(QLabel("Confidence Threshold:"))
        self.confidence_spin = QSpinBox()
        self.confidence_spin.setRange(1, 95)
        self.confidence_spin.setValue(10)
        self.confidence_spin.setSuffix("%")
        self.confidence_spin.setToolTip("Minimum confidence level for object detection (1-95%)")
        confidence_layout.addWidget(self.confidence_spin)
        confidence_layout.addStretch()
        confidence_widget = QWidget()
        confidence_widget.setLayout(confidence_layout)
        layout.addWidget(confidence_widget)
        self.confidence_widget = confidence_widget
        
        # Max objects setting
        max_objects_layout = QHBoxLayout()
        max_objects_layout.addWidget(QLabel("Maximum Objects:"))
        self.max_objects_spin = QSpinBox()
        self.max_objects_spin.setRange(1, 100)
        self.max_objects_spin.setValue(20)
        self.max_objects_spin.setToolTip("Maximum number of objects to detect and report")
        max_objects_layout.addWidget(self.max_objects_spin)
        max_objects_layout.addStretch()
        max_objects_widget = QWidget()
        max_objects_widget.setLayout(max_objects_layout)
        layout.addWidget(max_objects_widget)
        self.max_objects_widget = max_objects_widget
        
        # YOLO model selection
        yolo_model_layout = QHBoxLayout()
        yolo_model_layout.addWidget(QLabel("YOLO Model:"))
        self.yolo_model_combo = QComboBox()
        self.yolo_model_combo.addItem("yolov8n.pt (Fast, smaller file)")
        self.yolo_model_combo.addItem("yolov8s.pt (Balanced)")
        self.yolo_model_combo.addItem("yolov8m.pt (More accurate)")
        self.yolo_model_combo.addItem("yolov8l.pt (Large, slower)")
        self.yolo_model_combo.addItem("yolov8x.pt (Best accuracy)")
        self.yolo_model_combo.setCurrentIndex(4)  # Default to yolov8x
        self.yolo_model_combo.setToolTip("YOLO model size vs accuracy tradeoff")
        yolo_model_layout.addWidget(self.yolo_model_combo)
        yolo_model_layout.addStretch()
        yolo_model_widget = QWidget()
        yolo_model_widget.setLayout(yolo_model_layout)
        layout.addWidget(yolo_model_widget)
        self.yolo_model_widget = yolo_model_widget
        
        # Initially hide YOLO settings
        self.yolo_settings_label.hide()
        self.confidence_widget.hide()
        self.max_objects_widget.hide()
        self.yolo_model_widget.hide()
        
        # GroundingDINO Settings (shown only for grounding_dino providers)
        self.grounding_dino_settings_label = QLabel("🎯 GroundingDINO Detection Settings:")
        self.grounding_dino_settings_label.setStyleSheet("font-weight: bold; color: #2b5aa0;")
        layout.addWidget(self.grounding_dino_settings_label)
        
        # Detection mode radio buttons
        mode_group_box = QGroupBox("Detection Mode")
        mode_layout = QVBoxLayout()
        self.grounding_dino_auto_radio = QRadioButton("Automatic (Use Preset)")
        self.grounding_dino_custom_radio = QRadioButton("Custom Query")
        self.grounding_dino_auto_radio.setChecked(True)
        mode_layout.addWidget(self.grounding_dino_auto_radio)
        mode_layout.addWidget(self.grounding_dino_custom_radio)
        mode_group_box.setLayout(mode_layout)
        layout.addWidget(mode_group_box)
        self.grounding_dino_mode_widget = mode_group_box
        
        # Preset dropdown (shown when Automatic mode selected)
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Detection Preset:"))
        self.grounding_dino_preset_combo = QComboBox()
        self.grounding_dino_preset_combo.addItem("Comprehensive Scan", "comprehensive")
        self.grounding_dino_preset_combo.addItem("Indoor Objects", "indoor")
        self.grounding_dino_preset_combo.addItem("Outdoor Scene", "outdoor")
        self.grounding_dino_preset_combo.addItem("Workplace/Office", "workplace")
        self.grounding_dino_preset_combo.addItem("Safety & Hazards", "safety")
        self.grounding_dino_preset_combo.addItem("Retail/Inventory", "retail")
        self.grounding_dino_preset_combo.addItem("Document/Text Elements", "document")
        self.grounding_dino_preset_combo.setToolTip("Select a predefined detection preset for common scenarios")
        preset_layout.addWidget(self.grounding_dino_preset_combo)
        preset_layout.addStretch()
        preset_widget = QWidget()
        preset_widget.setLayout(preset_layout)
        layout.addWidget(preset_widget)
        self.grounding_dino_preset_widget = preset_widget
        
        # Custom query input (shown when Custom mode selected)
        custom_query_layout = QVBoxLayout()
        custom_query_layout.addWidget(QLabel("Custom Detection Query:"))
        self.grounding_dino_query_input = QLineEdit()
        self.grounding_dino_query_input.setPlaceholderText("Enter objects to detect (e.g., 'red car . person wearing hat . bicycle')")
        self.grounding_dino_query_input.setToolTip(
            "Enter what you want to detect. Separate multiple items with ' . '\n"
            "Examples:\n"
            "  • red car . blue truck . motorcycle\n"
            "  • person wearing glasses . person with backpack\n"
            "  • dangerous equipment . safety signs . fire exits"
        )
        custom_query_layout.addWidget(self.grounding_dino_query_input)
        help_label = QLabel(
            "💡 <i>Tip: Be specific! Use colors, attributes, states. Separate items with ' . '</i>"
        )
        help_label.setWordWrap(True)
        help_label.setStyleSheet("color: #666; font-size: 10px;")
        custom_query_layout.addWidget(help_label)
        custom_query_widget = QWidget()
        custom_query_widget.setLayout(custom_query_layout)
        layout.addWidget(custom_query_widget)
        self.grounding_dino_query_widget = custom_query_widget
        
        # Confidence threshold for GroundingDINO
        gd_confidence_layout = QHBoxLayout()
        gd_confidence_layout.addWidget(QLabel("Detection Confidence:"))
        self.grounding_dino_confidence_spin = QSpinBox()
        self.grounding_dino_confidence_spin.setRange(1, 95)
        self.grounding_dino_confidence_spin.setValue(25)
        self.grounding_dino_confidence_spin.setSuffix("%")
        self.grounding_dino_confidence_spin.setToolTip("Minimum confidence threshold for detections (1-95%)")
        gd_confidence_layout.addWidget(self.grounding_dino_confidence_spin)
        gd_confidence_layout.addStretch()
        gd_confidence_widget = QWidget()
        gd_confidence_widget.setLayout(gd_confidence_layout)
        layout.addWidget(gd_confidence_widget)
        self.grounding_dino_confidence_widget = gd_confidence_widget
        
        # Connect radio buttons to show/hide preset vs custom query
        self.grounding_dino_auto_radio.toggled.connect(
            lambda checked: self.grounding_dino_preset_widget.setVisible(checked)
        )
        self.grounding_dino_custom_radio.toggled.connect(
            lambda checked: self.grounding_dino_query_widget.setVisible(checked)
        )
        
        # Initially hide GroundingDINO settings
        self.grounding_dino_settings_label.hide()
        self.grounding_dino_mode_widget.hide()
        self.grounding_dino_preset_widget.hide()
        self.grounding_dino_query_widget.hide()
        self.grounding_dino_confidence_widget.hide()
        
        # Provider status info
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.status_label)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        # Initialize models for default provider
        self.on_provider_changed()
    
    def populate_providers(self):
        """Populate available AI providers"""
        self.provider_combo.clear()
        
        # Check if we're in development mode with hardcoded models
        from ai_providers import DEV_MODE_HARDCODED_MODELS
        
        # Always show all providers for consistency with ProcessingDialog
        all_providers = get_all_providers()
        
        for provider_key, provider in all_providers.items():
            if provider is None:
                continue  # Skip None providers
            try:
                display_name = provider.get_provider_name()
                # Skip availability check in dev mode for faster loading
                if not DEV_MODE_HARDCODED_MODELS and not provider.is_available():
                    display_name += " (Not Available)"
                self.provider_combo.addItem(display_name, provider_key)
            except Exception as e:
                print(f"Warning: Failed to add provider {provider_key}: {e}")
                continue
    
    def on_provider_changed(self):
        """Handle provider selection change"""
        current_data = self.provider_combo.currentData()
        if not current_data:
            self.model_combo.clear()
            self.status_label.setText("No provider selected.")
            return
        
        # Map provider internal names to display names for capability lookup
        # ONNX provider shows as "Enhanced Ollama" so it should support prompts
        provider_display_names = {
            "ollama": "Ollama",
            "ollama_cloud": "Ollama Cloud",
            "openai": "OpenAI",
            "claude": "Claude",
            "onnx": "Enhanced Ollama (CPU + YOLO)",  # Use capability name for ONNX
            "huggingface": "HuggingFace",
            "copilot": "Copilot+ PC",
            "object_detection": "Object Detection",
            "grounding_dino": "Grounding DINO",
            "grounding_dino_hybrid": "Grounding DINO"
        }
        
        provider_name = provider_display_names.get(current_data, current_data)
        
        # Show/hide settings based on provider type (keep legacy detection for UI-specific providers)
        is_object_detection = current_data == "object_detection"
        is_grounding_dino = current_data in ["grounding_dino", "grounding_dino_hybrid"]
        
        # Use dynamic capability checking for prompt support
        provider_supports_prompts = supports_prompts(provider_name)
        provider_supports_custom = supports_custom_prompts(provider_name)
        
        # Hide/show prompt-related controls based on provider capabilities
        self.prompt_label.setVisible(provider_supports_prompts)
        self.prompt_combo.setVisible(provider_supports_prompts)
        self.custom_checkbox.setVisible(provider_supports_custom)
        self.custom_prompt.setVisible(provider_supports_custom)
        
        # Hide/show YOLO settings
        self.yolo_settings_label.setVisible(is_object_detection)
        self.confidence_widget.setVisible(is_object_detection)
        self.max_objects_widget.setVisible(is_object_detection)
        self.yolo_model_widget.setVisible(is_object_detection)
        
        # Hide/show GroundingDINO settings
        self.grounding_dino_settings_label.setVisible(is_grounding_dino)
        self.grounding_dino_mode_widget.setVisible(is_grounding_dino)
        self.grounding_dino_confidence_widget.setVisible(is_grounding_dino)
        
        # Show preset or custom query based on radio button selection
        if is_grounding_dino:
            self.grounding_dino_preset_widget.setVisible(self.grounding_dino_auto_radio.isChecked())
            self.grounding_dino_query_widget.setVisible(self.grounding_dino_custom_radio.isChecked())
        else:
            self.grounding_dino_preset_widget.hide()
            self.grounding_dino_query_widget.hide()
        
        # Update models for selected provider
        self.populate_models(current_data)
        
        # Update status information based on provider availability
        all_providers = get_all_providers()
        
        if current_data in all_providers:
            provider = all_providers[current_data]
            if provider is None:
                return  # Skip None providers
            if current_data == "ollama":
                if provider.is_available():
                    self.status_label.setText("Ollama: Local AI processing. Install models with 'ollama pull <model_name>'")
                else:
                    self.status_label.setText("Ollama not available. Please install Ollama from https://ollama.ai")
            elif current_data == "ollama_cloud":
                if provider.is_available():
                    self.status_label.setText("Ollama Cloud: Massive cloud models (200B-671B parameters). Sign in with 'ollama signin'")
                else:
                    self.status_label.setText("Ollama Cloud not available. Run: ollama signin, then ollama pull <model>:cloud")
            elif current_data == "openai":
                if provider.is_available():
                    self.status_label.setText("OpenAI: Cloud AI processing. Requires API key in openai.txt file.")
                else:
                    self.status_label.setText("OpenAI not available. Install with: pip install openai. Requires API key in openai.txt file.")
            elif current_data == "claude":
                if provider.is_available():
                    self.status_label.setText("Claude (Anthropic): Cloud AI processing with advanced reasoning. Requires API key in claude.txt file or ANTHROPIC_API_KEY env var.")
                else:
                    self.status_label.setText("Claude not available. Requires API key in claude.txt file (current directory, ~/, or ~/onedrive/), or set ANTHROPIC_API_KEY environment variable.")
            elif current_data == "onnx":
                if provider.is_available():
                    self.status_label.setText(f"ONNX Runtime: Hardware-accelerated AI models. Status: {provider.hardware_type}. Run download_onnx_models.bat to get models.")
                else:
                    self.status_label.setText("ONNX Runtime not available. Install with: pip install onnxruntime onnx huggingface-hub")
            elif current_data == "copilot":
                if provider.is_available():
                    self.status_label.setText(f"Copilot+ PC: Native Windows AI acceleration. Status: {provider.npu_info}")
                else:
                    self.status_label.setText("Copilot+ PC not available. Requires Windows 11 and Copilot+ PC hardware (NPU with 40+ TOPS)")
            elif current_data == "grounding_dino":
                if provider.is_available():
                    self.status_label.setText("GroundingDINO: Text-prompted detection with unlimited classes. Configure detection mode below. Model (~700MB) auto-downloads on first use - no manual download needed!")
                else:
                    self.status_label.setText("GroundingDINO not available. Install with: pip install groundingdino-py torch torchvision")
            elif current_data == "grounding_dino_hybrid":
                if provider.is_available():
                    self.status_label.setText("GroundingDINO Hybrid: Detection + Ollama descriptions. Configure detection below. Model auto-downloads on first use.")
                else:
                    self.status_label.setText("GroundingDINO Hybrid not available. Install: pip install groundingdino-py torch torchvision + Ollama")
            else:
                self.status_label.setText(f"Using {provider.get_provider_name()} provider")
    
    def populate_models(self, provider_key: str):
        """Populate models for selected provider"""
        self.model_combo.clear()
        
        # GroundingDINO standalone doesn't use traditional "models" - settings are in the detection controls
        if provider_key == "grounding_dino":
            self.model_combo.addItem("Detection configured below")
            self.model_combo.setEnabled(False)
            return
        
        # GroundingDINO Hybrid needs to show Ollama models for the description part
        if provider_key == "grounding_dino_hybrid":
            # Show Ollama models since hybrid mode uses Ollama for descriptions
            provider = _ollama_provider
            models = provider.get_available_models()
            self.model_combo.setEnabled(True)
            
            if models:
                for model in models:
                    self.model_combo.addItem(model)
                print(f"Hybrid mode: Found {len(models)} Ollama models for descriptions")
            else:
                self.model_combo.addItem("No Ollama models available")
                print("Warning: Hybrid mode requires Ollama models. Install with: ollama pull llava")
            return
        
        self.model_combo.setEnabled(True)
        
        # Use the global provider instances (with caching) directly instead of get_available_providers()
        all_providers = {
            'ollama': _ollama_provider,
            'ollama_cloud': _ollama_cloud_provider,
            'openai': _openai_provider,
            'claude': _claude_provider,
            'onnx': _onnx_provider,
            'copilot': _copilot_provider,
            'object_detection': _object_detection_provider
        }
        
        if provider_key not in all_providers:
            self.model_combo.addItem("No models available")
            return
        
        provider = all_providers[provider_key]
        models = provider.get_available_models()
        
        if models:
            for model in models:
                self.model_combo.addItem(model)
            print(f"Found {len(models)} {provider.get_provider_name()} models: {models}")
        else:
            self.model_combo.addItem("No models available")
            if provider_key == "ollama":
                print("Warning: No Ollama models detected. Please install vision models with 'ollama pull <model_name>'")
            elif provider_key == "ollama_cloud":
                print("Warning: No Ollama Cloud models detected. Please sign in with 'ollama signin' and pull cloud models.")
            elif provider_key == "openai":
                print("Warning: OpenAI models not available. Check API key in openai.txt")
            elif provider_key == "claude":
                print("Warning: Claude models not available. Check API key in claude.txt file or ANTHROPIC_API_KEY environment variable")
            elif provider_key == "onnx":
                print("Warning: No ONNX models found. Run download_onnx_models.bat to download models.")
            elif provider_key == "copilot":
                print("Warning: Copilot+ PC hardware not detected or Windows AI APIs not available.")
            elif provider_key == "object_detection":
                print("Warning: YOLO object detection not available. Install with: pip install ultralytics")
    
    def get_selected_provider(self) -> str:
        """Get the selected provider key"""
        return self.provider_combo.currentData() or "none"
    
    def get_selected_model(self) -> str:
        """Get the selected model"""
        return self.model_combo.currentText()
    
    def get_selected_prompt_style(self) -> str:
        """Get the selected prompt style"""
        return self.prompt_combo.currentText()
    
    def get_custom_prompt(self) -> str:
        """Get custom prompt if enabled"""
        if self.custom_checkbox.isChecked():
            return self.custom_prompt.toPlainText()
        return ""
    
    def get_yolo_settings(self) -> dict:
        """Get YOLO object detection settings"""
        return {
            'confidence_threshold': self.confidence_spin.value() / 100.0,  # Convert to 0.0-1.0 range
            'max_objects': self.max_objects_spin.value(),
            'yolo_model': self.yolo_model_combo.currentText().split(' ')[0]  # Extract just the model name
        }
    
    def get_grounding_dino_settings(self) -> dict:
        """Get GroundingDINO detection settings"""
        settings = {
            'confidence_threshold': self.grounding_dino_confidence_spin.value() / 100.0,  # Convert to 0.0-1.0 range
        }
        
        # Add detection mode and query/preset
        if self.grounding_dino_auto_radio.isChecked():
            # Automatic mode with preset
            settings['mode'] = 'automatic'
            settings['preset'] = self.grounding_dino_preset_combo.currentData()
        else:
            # Custom query mode
            settings['mode'] = 'custom'
            settings['query'] = self.grounding_dino_query_input.text().strip()
        
        return settings
    
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
                # Add defaults if no prompts found - must match config file case exactly
                default_prompts = ["detailed", "concise", "Narrative", "artistic", "technical", "colorful", "Social"]
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
        """Get selected provider, model, prompt style, custom prompt, and detection settings"""
        provider = self.get_selected_provider()
        model = self.get_selected_model()
        prompt_style = self.get_selected_prompt_style()
        custom_prompt = self.get_custom_prompt()
        
        # Get detection settings based on provider type
        detection_settings = {}
        if provider == "object_detection":
            detection_settings = self.get_yolo_settings()
        elif provider in ["grounding_dino", "grounding_dino_hybrid"]:
            detection_settings = self.get_grounding_dino_settings()
        
        return provider, model, prompt_style, custom_prompt, detection_settings
    
    def accept(self):
        """Validate selections before accepting dialog"""
        provider = self.get_selected_provider()
        model = self.get_selected_model()
        
        # Validation: Check for invalid model selections
        invalid_models = ["No models available", "Detection configured below", ""]
        
        if model in invalid_models:
            if provider == "grounding_dino_hybrid":
                QMessageBox.warning(
                    self,
                    "Invalid Configuration",
                    "GroundingDINO + Ollama requires an Ollama model for descriptions.\n\n"
                    "Please:\n"
                    "1. Ensure Ollama is running\n"
                    "2. Install a vision model: ollama pull llava\n"
                    "3. Select the model from the dropdown"
                )
                return
            elif provider == "grounding_dino":
                # Standalone GroundingDINO is OK with "Detection configured below"
                if model == "Detection configured below":
                    super().accept()
                    return
            else:
                QMessageBox.warning(
                    self,
                    "Invalid Configuration",
                    f"No valid model selected for {provider}.\n\n"
                    f"Please select a valid model from the dropdown."
                )
                return
        
        # Validation: Check if provider is available
        all_providers = get_all_providers()
        if provider in all_providers:
            provider_obj = all_providers[provider]
            if not provider_obj.is_available():
                QMessageBox.warning(
                    self,
                    "Provider Not Available",
                    f"{provider_obj.get_provider_name()} is not currently available.\n\n"
                    f"Please check the setup requirements and try again."
                )
                return
        
        # All validations passed
        super().accept()


class ChatDialog(QDialog):
    """Dialog for starting a new chat session with an AI model"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Start Chat Session")
        self.setModal(True)
        self.resize(450, 400)
        
        layout = QVBoxLayout(self)
        
        # Header
        header_label = QLabel("Start a new chat session with an AI model")
        header_label.setStyleSheet("font-weight: bold; font-size: 12px; padding: 10px;")
        layout.addWidget(header_label)
        
        # Provider selection
        layout.addWidget(QLabel("AI Provider:"))
        self.provider_combo = QComboBox()
        self.populate_providers()
        layout.addWidget(self.provider_combo)
        
        # Model selection
        layout.addWidget(QLabel("AI Model:"))
        self.model_combo = QComboBox()
        layout.addWidget(self.model_combo)
        
        # Connect provider change to update models
        self.provider_combo.currentTextChanged.connect(self.on_provider_changed)
        
        # Initial prompt
        layout.addWidget(QLabel("Initial Prompt:"))
        self.prompt_text = AccessibleTextEdit()
        self.prompt_text.setMaximumHeight(150)
        self.prompt_text.setAccessibleName("Initial Chat Prompt")
        self.prompt_text.setAccessibleDescription("Enter your initial question or prompt to start the chat conversation")
        self.prompt_text.setPlaceholderText("Enter your question or prompt here...")
        layout.addWidget(self.prompt_text)
        
        # Chat session name (optional)
        layout.addWidget(QLabel("Session Name (optional):"))
        self.session_name = QLineEdit()
        self.session_name.setAccessibleName("Chat Session Name")
        self.session_name.setAccessibleDescription("Optional name for this chat session")
        self.session_name.setPlaceholderText("Leave blank for auto-generated name")
        layout.addWidget(self.session_name)
        
        # Provider status info
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.status_label)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        # Initialize with first provider
        self.on_provider_changed()
        
        # Set focus to prompt text
        self.prompt_text.setFocus()
    
    def populate_providers(self):
        """Populate provider combo box"""
        self.provider_combo.clear()
        
        # Check if we're in development mode with hardcoded models
        from ai_providers import DEV_MODE_HARDCODED_MODELS
        
        # Always show all providers, regardless of availability
        # This allows users to see what's possible and get setup instructions
        all_providers = {
            'ollama': _ollama_provider,
            'ollama_cloud': _ollama_cloud_provider,
            'openai': _openai_provider,
            'claude': _claude_provider,
            'onnx': _onnx_provider,
            'copilot': _copilot_provider,
            'object_detection': _object_detection_provider
        }
        
        for provider_key, provider in all_providers.items():
            display_name = provider.get_provider_name()
            # Skip availability check in dev mode for faster loading
            if not DEV_MODE_HARDCODED_MODELS and not provider.is_available():
                display_name += " (Not Available)"
            self.provider_combo.addItem(display_name, provider_key)
    
    def on_provider_changed(self):
        """Update models when provider changes"""
        provider = self.get_selected_provider()
        self.populate_models(provider)
        self.update_status_info(provider)
    
    def populate_models(self, provider):
        """Populate model combo based on provider"""
        self.model_combo.clear()
        
        # Use the global provider instances (with caching) directly
        all_providers = {
            'ollama': _ollama_provider,
            'ollama_cloud': _ollama_cloud_provider,
            'openai': _openai_provider,
            'claude': _claude_provider,
            'onnx': _onnx_provider,
            'copilot': _copilot_provider,
            'object_detection': _object_detection_provider
        }
        
        if provider in all_providers:
            provider_instance = all_providers[provider]
            models = provider_instance.get_available_models()
            
            if models:
                for model in models:
                    self.model_combo.addItem(model)
            else:
                self.model_combo.addItem("No models available")
        else:
            self.model_combo.addItem("Unknown provider")
    
    def update_status_info(self, provider):
        """Update status information for the selected provider"""
        if provider == "ollama":
            if _ollama_provider.is_available():
                self.status_label.setText("Using local Ollama models. Make sure Ollama is running.")
            else:
                self.status_label.setText("Ollama not available. Please install Ollama from https://ollama.ai")
        elif provider == "ollama_cloud":
            if _ollama_cloud_provider.is_available():
                self.status_label.setText("Using Ollama Cloud models. Massive models (200B-671B parameters) running on datacenter hardware.")
            else:
                self.status_label.setText("Ollama Cloud not available. Run: ollama signin, then ollama pull <model>:cloud")
        elif provider == "openai":
            if _openai_provider.is_available():
                self.status_label.setText("Using OpenAI API. Requires API key configuration.")
            else:
                self.status_label.setText("OpenAI not available. Install with: pip install openai. Requires API key in openai.txt file.")
        elif provider == "claude":
            if _claude_provider.is_available():
                self.status_label.setText("Using Claude (Anthropic) API. Advanced reasoning and vision capabilities. Requires API key.")
            else:
                self.status_label.setText("Claude not available. Requires API key in claude.txt file or ANTHROPIC_API_KEY environment variable.")
        elif provider == "onnx":
            if _onnx_provider.is_available():
                self.status_label.setText(f"Using ONNX Runtime models. Hardware acceleration: {_onnx_provider.hardware_type}. Run download_onnx_models.bat to get models.")
            else:
                self.status_label.setText("ONNX Runtime not available. Install with: pip install onnxruntime onnx huggingface-hub")
        elif provider == "copilot":
            if _copilot_provider.is_available():
                self.status_label.setText(f"Using Copilot+ PC hardware acceleration. Status: {_copilot_provider.npu_info}")
            else:
                self.status_label.setText("Copilot+ PC not available. Requires Windows 11 and Copilot+ PC hardware (NPU with 40+ TOPS)")
        elif provider == "object_detection":
            if _object_detection_provider.is_available():
                self.status_label.setText("Using YOLO object detection. Fast processing without LLM overhead. Choose detection mode from models.")
            else:
                self.status_label.setText("Object detection not available. Install with: pip install ultralytics")
        else:
            self.status_label.setText("")
    
    def get_selected_provider(self):
        """Get the currently selected provider"""
        return self.provider_combo.currentData() or "ollama"
    
    def get_selected_model(self):
        """Get the currently selected model"""
        return self.model_combo.currentText()
    
    def get_initial_prompt(self):
        """Get the initial prompt text"""
        return self.prompt_text.toPlainText().strip()
    
    def get_session_name(self):
        """Get the session name"""
        return self.session_name.text().strip()
    
    def set_provider_model(self, provider: str, model: str):
        """Set the provider and model selection"""
        # Find and set provider
        provider_index = self.provider_combo.findText(provider)
        if provider_index >= 0:
            self.provider_combo.setCurrentIndex(provider_index)
            # Update models for this provider
            self.on_provider_changed()
            # Find and set model
            model_index = self.model_combo.findText(model)
            if model_index >= 0:
                self.model_combo.setCurrentIndex(model_index)
    
    def set_initial_prompt(self, prompt: str):
        """Set the initial prompt text"""
        self.prompt_text.setPlainText(prompt)
    
    def set_session_name(self, name: str):
        """Set the session name"""
        self.session_name.setText(name)
    
    def get_chat_config(self):
        """Get all chat configuration"""
        return {
            'provider': self.get_selected_provider(),
            'model': self.get_selected_model(),
            'initial_prompt': self.get_initial_prompt(),
            'session_name': self.get_session_name()
        }


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
        
        # Main content area with splitter
        splitter = QSplitter(Qt.Orientation.Vertical)
        layout.addWidget(splitter)
        
        # Chat history area
        history_widget = QWidget()
        history_layout = QVBoxLayout(history_widget)
        history_layout.setContentsMargins(0, 0, 0, 0)
        
        history_label = QLabel("Conversation History:")
        history_label.setStyleSheet("font-weight: bold; margin-bottom: 5px;")
        history_layout.addWidget(history_label)
        
        # Chat history list
        self.history_list = QListWidget()
        self.history_list.setAccessibleName("Chat History")
        self.history_list.setAccessibleDescription("List of messages in this conversation. Use arrow keys to navigate, Tab to move to input box.")
        self.history_list.setAlternatingRowColors(True)
        self.history_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        
        # Connect selection change to show full message
        self.history_list.currentItemChanged.connect(self.on_history_selection_changed)
        
        history_layout.addWidget(self.history_list)
        
        # Message detail area (shows full text of selected message)
        self.message_detail = AccessibleTextEdit()
        self.message_detail.setAccessibleName("Message Detail")
        self.message_detail.setAccessibleDescription("Full text of the selected message")
        self.message_detail.setReadOnly(True)
        self.message_detail.setMaximumHeight(150)
        history_layout.addWidget(self.message_detail)
        
        splitter.addWidget(history_widget)
        
        # Input area
        input_widget = QWidget()
        input_layout = QVBoxLayout(input_widget)
        input_layout.setContentsMargins(0, 0, 0, 0)
        
        input_label = QLabel("Your Message:")
        input_label.setStyleSheet("font-weight: bold; margin-bottom: 5px;")
        input_layout.addWidget(input_label)
        
        # Message input box
        self.input_box = AccessibleTextEdit()
        self.input_box.setAccessibleName("Message Input")
        self.input_box.setAccessibleDescription("Type your message here. Press Enter to send, Tab to navigate to send button and history.")
        self.input_box.setPlaceholderText("Type your message here...")
        self.input_box.setMaximumHeight(100)
        
        # Override keyPressEvent for input box to handle Enter key
        def input_key_press(event):
            if event.key() == Qt.Key.Key_Return and not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
                # Enter sends message (unless Shift+Enter for new line)
                self.send_message()
            else:
                AccessibleTextEdit.keyPressEvent(self.input_box, event)
        
        self.input_box.keyPressEvent = input_key_press
        input_layout.addWidget(self.input_box)
        
        # Button area
        button_layout = QHBoxLayout()
        
        self.send_button = QPushButton("Send Message")
        self.send_button.setAccessibleName("Send Message")
        self.send_button.setAccessibleDescription("Send your message to the AI")
        self.send_button.clicked.connect(self.send_message)
        self.send_button.setDefault(True)
        
        self.clear_button = QPushButton("Clear Input")
        self.clear_button.setAccessibleName("Clear Input")
        self.clear_button.setAccessibleDescription("Clear the message input box")
        self.clear_button.clicked.connect(self.clear_input)
        
        button_layout.addWidget(self.send_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addStretch()
        
        input_layout.addLayout(button_layout)
        
        splitter.addWidget(input_widget)
        
        # Set splitter proportions (70% history, 30% input)
        splitter.setSizes([420, 180])
        
        # Set up proper tab order for accessibility: input → send → clear → history
        self.setTabOrder(self.input_box, self.send_button)
        self.setTabOrder(self.send_button, self.clear_button)
        self.setTabOrder(self.clear_button, self.history_list)
        self.setTabOrder(self.history_list, self.input_box)
        
        # Keep send and clear buttons in tab flow (remove ClickFocus restriction)
        self.send_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.clear_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # Message detail is read-only and not part of main navigation
        self.message_detail.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    
    def get_short_model_name(self, model_name):
        """Extract short, readable model name from full model name"""
        if not model_name:
            return "Unknown"
        
        # Common model name mappings
        model_mappings = {
            'llama': 'Llama',
            'moondream': 'Moondream', 
            'mistral': 'Mistral',
            'phi': 'Phi',
            'gemma': 'Gemma',
            'qwen': 'Qwen',
            'gpt-4': 'GPT-4',
            'gpt-3.5': 'GPT-3.5',
            'gpt-4o': 'GPT-4o',
            'claude': 'Claude',
            'blip': 'BLIP',
            'git-base': 'GIT',
            'instructblip': 'InstructBLIP'
        }
        
        model_lower = model_name.lower()
        
        # Check for exact matches first
        for key, value in model_mappings.items():
            if key in model_lower:
                return value
        
        # If no mapping found, try to extract a reasonable short name
        # Remove common prefixes and suffixes
        short_name = model_name
        if '/' in short_name:
            short_name = short_name.split('/')[-1]  # Take last part after slash
        
        # Remove version numbers and common suffixes
        for suffix in ['-chat', '-instruct', '-base', '-7b', '-13b', '-70b', '-2.7b', '-opt']:
            if suffix in short_name.lower():
                short_name = short_name.replace(suffix, '').replace(suffix.upper(), '')
        
        # Capitalize first letter
        return short_name.capitalize()
    
    def load_conversation(self):
        """Load the conversation history into the list"""
        self.history_list.clear()
        
        for i, msg in enumerate(self.chat_session.get('conversation', [])):
            if msg['type'] == 'user':
                # For display: "You: message content (timestamp)"
                display_text = f"You: {msg['content']} ({msg['timestamp']})"
                full_text = f"You: {msg['content']} ({msg['timestamp']})"
                color = QColor(0, 120, 0)  # Green for user
                accessible_desc = "Your message"
            else:
                provider = msg.get('provider', 'AI')
                model = msg.get('model', 'Model')
                short_model = self.get_short_model_name(model)
                
                # For display: "ShortModel: message content (timestamp)"
                display_text = f"{short_model}: {msg['content']} ({msg['timestamp']})"
                full_text = f"{short_model}: {msg['content']} ({msg['timestamp']})"
                color = QColor(0, 0, 150)  # Blue for AI
                accessible_desc = f"AI response from {short_model}"
            
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, full_text)
            # Set full text for screen readers - this is what accessibility tools will read
            item.setData(Qt.ItemDataRole.AccessibleTextRole, full_text)
            # Set accessible description for additional context
            item.setData(Qt.ItemDataRole.AccessibleDescriptionRole, accessible_desc)
            
            item.setForeground(color)
            item.setToolTip(full_text)
            
            self.history_list.addItem(item)
        
        # Select the last message if any exist
        if self.history_list.count() > 0:
            self.history_list.setCurrentRow(self.history_list.count() - 1)
    
    def on_history_selection_changed(self, current, previous):
        """Handle history selection change"""
        if current:
            full_text = current.data(Qt.ItemDataRole.UserRole)
            self.message_detail.setPlainText(full_text)
            
            # Update accessibility for screen readers
            char_count = len(full_text)
            preview = full_text[:200] + "..." if len(full_text) > 200 else full_text
            self.message_detail.setAccessibleDescription(
                f"Selected message with {char_count} characters: {preview}"
            )
            
            # Announce to screen reader when AI message is selected
            if "AI" in full_text or any(model in full_text for model in ["Llama", "Moondream", "GPT", "Claude", "BLIP"]):
                # Extract just the message content for announcement
                if ": " in full_text:
                    message_content = full_text.split(": ", 1)[1].split(" (")[0]  # Remove timestamp
                    self.announce_to_screen_reader(f"AI message: {message_content}")
        else:
            self.message_detail.clear()
            self.message_detail.setAccessibleDescription("No message selected.")
    
    def send_message(self):
        """Send the message in the input box"""
        message = self.input_box.toPlainText().strip()
        if not message:
            return
        
        # Clear input box
        self.input_box.clear()
        
        # Add user message to conversation display immediately
        self.add_message_to_display('user', message)
        
        # Emit signal to parent to process the message
        self.message_sent.emit(self.chat_id, message)
        
        # Announce message sent to screen reader
        self.announce_to_screen_reader(f"Message sent: {message}")
    
    def clear_input(self):
        """Clear the input box"""
        self.input_box.clear()
        self.input_box.setFocus()
    
    def add_message_to_display(self, msg_type, content, timestamp=None, provider=None, model=None):
        """Add a new message to the display"""
        if not timestamp:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if msg_type == 'user':
            # Show "You: message content (timestamp)"
            display_text = f"You: {content} ({timestamp})"
            full_text = f"You: {content} ({timestamp})"
            color = QColor(0, 120, 0)  # Green for user
            accessible_desc = "Your message"
        else:
            short_model = self.get_short_model_name(model)
            # Show "ShortModel: message content (timestamp)"
            display_text = f"{short_model}: {content} ({timestamp})"
            full_text = f"{short_model}: {content} ({timestamp})"
            color = QColor(0, 0, 150)  # Blue for AI
            accessible_desc = f"AI response from {short_model}"
        
        item = QListWidgetItem(display_text)
        item.setData(Qt.ItemDataRole.UserRole, full_text)
        # Set full text for screen readers
        item.setData(Qt.ItemDataRole.AccessibleTextRole, full_text)
        # Set accessible description for additional context
        item.setData(Qt.ItemDataRole.AccessibleDescriptionRole, accessible_desc)
        
        item.setForeground(color)
        item.setToolTip(full_text)
        
        self.history_list.addItem(item)
        
        # Select the new message
        self.history_list.setCurrentRow(self.history_list.count() - 1)
        
        # For AI responses, announce to screen reader
        if msg_type != 'user':
            self.announce_to_screen_reader(f"AI response received: {content}")
    
    def announce_to_screen_reader(self, text):
        """Announce text to screen reader"""
        try:
            # Set a temporary status on the window title - screen readers will announce title changes
            self.setWindowTitle(f"Chat: {self.chat_session['name']} - {text[:50]}...")
            
            # Reset title after a moment
            QTimer.singleShot(3000, lambda: self.setWindowTitle(f"Chat: {self.chat_session['name']}"))
            
        except Exception:
            # Fallback: just update window title
            self.setWindowTitle(f"Chat: {self.chat_session['name']} - {text[:50]}...")
            QTimer.singleShot(3000, lambda: self.setWindowTitle(f"Chat: {self.chat_session['name']}"))
    
    def update_conversation_data(self, conversation):
        """Update the conversation data and refresh display"""
        self.chat_session['conversation'] = conversation
        self.load_conversation()


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
            "provider": "ollama",  # Default to ollama for video processing for now
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


class ModelManagerDialog(QDialog):
    """Dialog for managing Ollama models - browse, search, and install"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Model Manager")
        self.setModal(True)
        self.resize(900, 700)
        
        # Track installation processes
        self.installation_processes = {}
        
        layout = QVBoxLayout(self)
        
        # Create tab widget for different views
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Tab 1: Installed Models
        self.setup_installed_tab()
        
        # Tab 2: Available Models  
        self.setup_available_tab()
        
        # Tab 3: Model Search
        self.setup_search_tab()
        
        # Status bar at bottom
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("padding: 5px; border-top: 1px solid #ccc;")
        layout.addWidget(self.status_label)
        
        # Close button
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.close)
        layout.addWidget(button_box)
        
        # Load initial data
        self.installed_models = []  # List to store installed model names
        self.refresh_installed_models()
        
        # Initialize the comprehensive model database
        self.init_model_database()
        
        # Trigger initial filter display
        self.filter_installed_models()
        self.filter_available_models()
    
    def init_model_database(self):
        """Initialize comprehensive model database with categories"""
        self.model_database = {
            "Vision Models": [
                {
                    "name": "moondream",
                    "description": "A small vision language model (1.7B params) designed to run efficiently on edge devices. Perfect for basic image understanding tasks with minimal resource requirements.",
                    "size": "~1.7GB",
                    "capabilities": "Image understanding, basic Q&A, efficient on CPU, low memory usage",
                    "use_cases": "Quick image descriptions, edge devices, resource-constrained environments"
                },
                {
                    "name": "llava", 
                    "description": "Large Language and Vision Assistant. The original and most popular multimodal model with excellent image analysis capabilities.",
                    "size": "~4.1GB",
                    "capabilities": "Advanced image analysis, detailed descriptions, complex visual reasoning",
                    "use_cases": "Professional image analysis, detailed descriptions, visual Q&A"
                },
                {
                    "name": "llava:7b",
                    "description": "7B parameter version of LLaVA. Provides an excellent balance between performance and resource usage for most applications.",
                    "size": "~4.1GB",
                    "capabilities": "High-quality image descriptions, visual reasoning, good performance/size ratio",
                    "use_cases": "General-purpose vision tasks, balanced performance needs"
                },
                {
                    "name": "llava:13b",
                    "description": "13B parameter version of LLaVA. Offers the highest quality results but requires more computational resources and memory.",
                    "size": "~7.3GB", 
                    "capabilities": "Excellent image analysis, very detailed descriptions, advanced reasoning, professional quality",
                    "use_cases": "High-quality image analysis, professional applications, detailed reports"
                },
                {
                    "name": "llava:34b",
                    "description": "34B parameter version of LLaVA. The largest and most capable version, suitable for professional applications with high-end hardware.",
                    "size": "~19GB",
                    "capabilities": "Professional-grade image analysis, extremely detailed descriptions, sophisticated reasoning",
                    "use_cases": "Professional/research applications, highest quality requirements"
                },
                {
                    "name": "bakllava",
                    "description": "BakLLaVA is an improved vision-language model based on LLaVA architecture with enhanced training methodology and better performance.",
                    "size": "~4.1GB",
                    "capabilities": "Enhanced image understanding, improved visual Q&A, detailed descriptions, stable performance",
                    "use_cases": "Improved LLaVA alternative, stable image analysis"
                },
                {
                    "name": "llava-llama3",
                    "description": "LLaVA model based on Llama 3 architecture. Combines the visual capabilities of LLaVA with the improved language understanding of Llama 3.",
                    "size": "~4.1GB",
                    "capabilities": "Modern architecture, improved language understanding, excellent vision-language integration",
                    "use_cases": "Latest architecture benefits, improved language reasoning"
                },
                {
                    "name": "llava-phi3",
                    "description": "Compact vision model based on Microsoft's Phi-3 architecture. Offers good performance in a smaller package.",
                    "size": "~2.2GB",
                    "capabilities": "Compact size, efficient processing, good balance of capabilities and resource usage",
                    "use_cases": "Resource-efficient vision tasks, smaller deployments"
                },
                {
                    "name": "llama3.2-vision",
                    "description": "Meta's latest vision model based on Llama 3.2. State-of-the-art multimodal capabilities with excellent performance.",
                    "size": "~7.8GB",
                    "capabilities": "State-of-the-art vision understanding, advanced reasoning, latest architecture",
                    "use_cases": "Cutting-edge vision tasks, latest model capabilities"
                }
            ],
            "Language Models": [
                {
                    "name": "llama3.2",
                    "description": "Meta's latest language model with improved reasoning and instruction following capabilities.",
                    "size": "~4.1GB",
                    "capabilities": "Advanced text generation, reasoning, instruction following, multilingual",
                    "use_cases": "General text generation, chatbots, content creation"
                },
                {
                    "name": "llama3.1",
                    "description": "Previous generation Llama model with excellent performance for text tasks.",
                    "size": "~4.1GB",
                    "capabilities": "Text generation, reasoning, creative writing, analysis",
                    "use_cases": "Text generation, analysis, creative tasks"
                },
                {
                    "name": "gemma2",
                    "description": "Google's Gemma 2 model with improved efficiency and performance.",
                    "size": "~3.3GB",
                    "capabilities": "Efficient text generation, good reasoning, compact size",
                    "use_cases": "Efficient text tasks, resource-conscious applications"
                },
                {
                    "name": "qwen2.5",
                    "description": "Alibaba's Qwen 2.5 model with strong multilingual capabilities.",
                    "size": "~4.1GB",
                    "capabilities": "Multilingual text generation, reasoning, cultural understanding",
                    "use_cases": "Multilingual applications, international content"
                },
                {
                    "name": "phi3",
                    "description": "Microsoft's Phi-3 small language model with impressive capabilities for its size.",
                    "size": "~2.2GB",
                    "capabilities": "Compact size, efficient reasoning, good performance per parameter",
                    "use_cases": "Resource-efficient text tasks, edge deployment"
                }
            ],
            "Code Models": [
                {
                    "name": "codellama",
                    "description": "Meta's specialized model for code generation and understanding based on Llama 2.",
                    "size": "~4.1GB",
                    "capabilities": "Code generation, completion, explanation, debugging assistance",
                    "use_cases": "Programming assistance, code review, learning programming"
                },
                {
                    "name": "codegemma",
                    "description": "Google's specialized code model based on Gemma architecture.",
                    "size": "~3.3GB",
                    "capabilities": "Code generation, completion, multiple programming languages",
                    "use_cases": "Programming tasks, code completion, development assistance"
                },
                {
                    "name": "starcoder2",
                    "description": "Advanced code generation model with support for many programming languages.",
                    "size": "~4.1GB",
                    "capabilities": "Multi-language code generation, repository-level understanding",
                    "use_cases": "Professional development, code generation, refactoring"
                },
                {
                    "name": "deepseek-coder",
                    "description": "Specialized coding model with strong performance on programming tasks.",
                    "size": "~4.1GB",
                    "capabilities": "Code generation, debugging, algorithm design, competitive programming",
                    "use_cases": "Complex programming tasks, algorithm development"
                }
            ],
            "Embedding Models": [
                {
                    "name": "nomic-embed-text",
                    "description": "High-quality text embedding model for semantic search and similarity tasks.",
                    "size": "~274MB",
                    "capabilities": "Text embeddings, semantic search, similarity comparison, clustering",
                    "use_cases": "Search applications, document similarity, text clustering"
                },
                {
                    "name": "mxbai-embed-large",
                    "description": "Large embedding model with excellent performance for various text tasks.",
                    "size": "~669MB",
                    "capabilities": "High-quality embeddings, multilingual support, various text lengths",
                    "use_cases": "Professional search systems, multilingual applications"
                },
                {
                    "name": "all-minilm",
                    "description": "Compact embedding model suitable for various similarity tasks.",
                    "size": "~133MB",
                    "capabilities": "Compact embeddings, fast processing, good general performance",
                    "use_cases": "Resource-efficient similarity tasks, quick prototyping"
                }
            ],
            "Specialized Models": [
                {
                    "name": "dolphin-mistral",
                    "description": "Uncensored chat model based on Mistral with enhanced conversational abilities.",
                    "size": "~4.1GB",
                    "capabilities": "Uncensored conversations, creative writing, roleplay, open discussions",
                    "use_cases": "Open conversations, creative projects, research"
                },
                {
                    "name": "neural-chat",
                    "description": "Model optimized for conversational AI with friendly and helpful responses.",
                    "size": "~4.1GB",
                    "capabilities": "Conversational AI, helpful responses, balanced personality",
                    "use_cases": "Chatbots, virtual assistants, customer service"
                },
                {
                    "name": "wizardlm",
                    "description": "Model trained with complex instruction following for advanced reasoning tasks.",
                    "size": "~4.1GB",
                    "capabilities": "Complex reasoning, instruction following, problem solving",
                    "use_cases": "Complex analysis tasks, educational applications"
                },
                {
                    "name": "orca-mini",
                    "description": "Compact model with strong reasoning abilities trained on high-quality data.",
                    "size": "~2.2GB",
                    "capabilities": "Strong reasoning in compact size, logical thinking, problem solving",
                    "use_cases": "Efficient reasoning tasks, educational applications"
                }
            ]
        }
    
    def filter_installed_models(self):
        """Filter installed models by selected category"""
        category = self.installed_category_combo.currentText()
        
        # Clear current display
        self.installed_text.clear()
        
        if not self.installed_models:
            self.installed_text.setPlainText("No models are currently installed.\n\nUse the 'Available Models' tab to browse and install models.")
            return
        
        if category == "All Categories":
            # Show all installed models
            text = "Installed Models:\n\n"
            for i, model in enumerate(self.installed_models, 1):
                # Find model details from database
                model_details = self.find_model_in_database(model)
                if model_details:
                    text += f"{i}. {model}\n"
                    text += f"   Category: {model_details['category']}\n"
                    text += f"   Description: {model_details['info']['description']}\n"
                    text += f"   Size: {model_details['info']['size']}\n"
                    text += f"   Capabilities: {model_details['info']['capabilities']}\n\n"
                else:
                    # Model not in database - show basic info
                    text += f"{i}. {model}\n"
                    text += f"   Status: Installed locally\n\n"
        else:
            # Filter by category
            filtered_models = []
            for model in self.installed_models:
                model_details = self.find_model_in_database(model)
                if model_details and model_details['category'] == category:
                    filtered_models.append((model, model_details))
            
            if filtered_models:
                text = f"Installed {category}:\n\n"
                for i, (model, details) in enumerate(filtered_models, 1):
                    text += f"{i}. {model}\n"
                    text += f"   Description: {details['info']['description']}\n"
                    text += f"   Size: {details['info']['size']}\n"
                    text += f"   Capabilities: {details['info']['capabilities']}\n\n"
            else:
                text = f"No installed models found in category: {category}"
        
        self.installed_text.setPlainText(text)
    
    def filter_available_models(self):
        """Filter available models by selected category"""
        category = self.available_category_combo.currentText()
        
        # Clear current display
        self.available_text.clear()
        
        if category == "All Categories":
            # Show all available models
            text = "Available Models for Installation:\n\n"
            for category_name, models in self.model_database.items():
                text += f"=== {category_name} ===\n\n"
                for i, model in enumerate(models, 1):
                    text += f"{i}. {model['name']}\n"
                    text += f"   Description: {model['description']}\n"
                    text += f"   Size: {model['size']}\n"
                    text += f"   Capabilities: {model['capabilities']}\n"
                    text += f"   Use Cases: {model['use_cases']}\n\n"
                text += "\n"
        else:
            # Show specific category
            if category in self.model_database:
                models = self.model_database[category]
                text = f"Available {category}:\n\n"
                for i, model in enumerate(models, 1):
                    text += f"{i}. {model['name']}\n"
                    text += f"   Description: {model['description']}\n"
                    text += f"   Size: {model['size']}\n"
                    text += f"   Capabilities: {model['capabilities']}\n"
                    text += f"   Use Cases: {model['use_cases']}\n\n"
            else:
                text = f"No models found in category: {category}"
        
        self.available_text.setPlainText(text)
    
    def find_model_in_database(self, model_name):
        """Find a model in the database and return its details with category"""
        for category, models in self.model_database.items():
            for model_info in models:
                if model_info['name'] == model_name or model_name.startswith(model_info['name']):
                    return {
                        'category': category,
                        'info': model_info
                    }
        return None
        
    def setup_installed_tab(self):
        """Setup the installed models tab"""
        installed_widget = QWidget()
        layout = QVBoxLayout(installed_widget)
        
        # Header with refresh button
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Installed Models:"))
        
        # Category filter for installed models
        header_layout.addWidget(QLabel("Category:"))
        self.installed_category_combo = QComboBox()
        self.installed_category_combo.addItems([
            "All Categories",
            "Vision Models", 
            "Language Models",
            "Code Models",
            "Embedding Models",
            "Specialized Models"
        ])
        self.installed_category_combo.currentTextChanged.connect(self.filter_installed_models)
        self.installed_category_combo.setAccessibleName("Installed Models Category Filter")
        self.installed_category_combo.setAccessibleDescription("Filter installed models by category")
        header_layout.addWidget(self.installed_category_combo)
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_installed_models)
        header_layout.addWidget(refresh_btn)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Models overview text area
        layout.addWidget(QLabel("Models Overview:"))
        self.installed_text = QTextEdit()
        self.installed_text.setReadOnly(True)
        self.installed_text.setAccessibleName("Installed Models Overview")
        self.installed_text.setAccessibleDescription("Overview of installed models filtered by category. Use arrow keys to navigate through the text.")
        self.installed_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard)
        self.installed_text.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.installed_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        layout.addWidget(self.installed_text)
        
        # Models list
        self.installed_list = QListWidget()
        self.installed_list.setAccessibleName("Installed Models List")
        self.installed_list.setAccessibleDescription("List of locally installed Ollama models")
        self.installed_list.itemSelectionChanged.connect(self.on_installed_selection_changed)
        layout.addWidget(self.installed_list)
        
        # Model details area
        layout.addWidget(QLabel("Model Details:"))
        self.installed_details = QTextEdit()
        self.installed_details.setReadOnly(True)
        self.installed_details.setMaximumHeight(150)
        self.installed_details.setAccessibleName("Installed Model Details")
        self.installed_details.setAccessibleDescription("Details about the selected installed model. Use arrow keys to navigate through the text.")
        self.installed_details.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard)
        self.installed_details.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.installed_details.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        layout.addWidget(self.installed_details)
        
        # Action buttons for installed models
        installed_buttons = QHBoxLayout()
        
        self.delete_btn = QPushButton("Delete Model")
        self.delete_btn.clicked.connect(self.delete_selected_model)
        self.delete_btn.setEnabled(False)
        installed_buttons.addWidget(self.delete_btn)
        
        installed_buttons.addStretch()
        layout.addLayout(installed_buttons)
        
        self.tab_widget.addTab(installed_widget, "Installed")
    
    def setup_available_tab(self):
        """Setup the available models tab"""
        available_widget = QWidget()
        layout = QVBoxLayout(available_widget)
        
        # Header with load button
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Available Models:"))
        
        # Category filter for available models
        header_layout.addWidget(QLabel("Category:"))
        self.available_category_combo = QComboBox()
        self.available_category_combo.addItems([
            "All Categories",
            "Vision Models",
            "Language Models", 
            "Code Models",
            "Embedding Models",
            "Specialized Models"
        ])
        self.available_category_combo.currentTextChanged.connect(self.filter_available_models)
        self.available_category_combo.setAccessibleName("Available Models Category Filter")
        self.available_category_combo.setAccessibleDescription("Filter available models by category")
        header_layout.addWidget(self.available_category_combo)
        
        load_btn = QPushButton("Load Available Models")
        load_btn.clicked.connect(self.load_available_models)
        header_layout.addWidget(load_btn)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Available models overview text area
        layout.addWidget(QLabel("Available Models Overview:"))
        self.available_text = QTextEdit()
        self.available_text.setReadOnly(True)
        self.available_text.setAccessibleName("Available Models Overview")
        self.available_text.setAccessibleDescription("Overview of available models filtered by category. Use arrow keys to navigate through the text.")
        self.available_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard)
        self.available_text.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.available_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        layout.addWidget(self.available_text)
        
        # Available models list
        self.available_list = QListWidget()
        self.available_list.setAccessibleName("Available Models List")
        self.available_list.setAccessibleDescription("List of popular vision models available for download")
        self.available_list.itemSelectionChanged.connect(self.on_available_selection_changed)
        layout.addWidget(self.available_list)
        
        # Model info area
        layout.addWidget(QLabel("Model Information:"))
        self.available_details = QTextEdit()
        self.available_details.setReadOnly(True)
        self.available_details.setMaximumHeight(150)
        self.available_details.setAccessibleName("Available Model Information")
        self.available_details.setAccessibleDescription("Information about the selected available model. Use arrow keys to navigate through the text.")
        self.available_details.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard)
        self.available_details.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.available_details.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        layout.addWidget(self.available_details)
        
        # Install button
        available_buttons = QHBoxLayout()
        
        self.install_btn = QPushButton("Install Selected Model")
        self.install_btn.clicked.connect(self.install_selected_model)
        self.install_btn.setEnabled(False)
        available_buttons.addWidget(self.install_btn)
        
        available_buttons.addStretch()
        layout.addLayout(available_buttons)
        
        # Load popular models initially
        self.load_enhanced_popular_models()
        
        self.tab_widget.addTab(available_widget, "Available")
    
    def setup_search_tab(self):
        """Setup the search tab"""
        search_widget = QWidget()
        layout = QVBoxLayout(search_widget)
        
        # Search input
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search models:"))
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter search term (e.g., 'vision', 'llava', 'moondream')")
        self.search_input.returnPressed.connect(self.search_models)
        search_layout.addWidget(self.search_input)
        
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self.search_models)
        search_layout.addWidget(search_btn)
        
        layout.addLayout(search_layout)
        
        # Search results
        layout.addWidget(QLabel("Search Results:"))
        self.search_results = QListWidget()
        self.search_results.setAccessibleName("Search Results List")
        self.search_results.setAccessibleDescription("Search results for Ollama models")
        self.search_results.itemSelectionChanged.connect(self.on_search_selection_changed)
        layout.addWidget(self.search_results)
        
        # Search result details
        layout.addWidget(QLabel("Model Details:"))
        self.search_details = QTextEdit()
        self.search_details.setReadOnly(True)
        self.search_details.setMaximumHeight(150)
        self.search_details.setAccessibleName("Search Result Details")
        self.search_details.setAccessibleDescription("Details about the selected search result. Use arrow keys to navigate through the text.")
        self.search_details.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard)
        self.search_details.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.search_details.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        layout.addWidget(self.search_details)
        
        # Install from search
        search_buttons = QHBoxLayout()
        
        self.install_search_btn = QPushButton("Install Selected Model")
        self.install_search_btn.clicked.connect(self.install_search_selected_model)
        self.install_search_btn.setEnabled(False)
        search_buttons.addWidget(self.install_search_btn)
        
        search_buttons.addStretch()
        layout.addLayout(search_buttons)
        
        self.tab_widget.addTab(search_widget, "Search")
    
    def refresh_installed_models(self):
        """Refresh the list of installed models"""
        self.installed_list.clear()
        self.installed_details.clear()
        self.delete_btn.setEnabled(False)
        self.installed_models = []  # Reset the models list
        
        try:
            if not ollama:
                self.status_label.setText("Ollama Python package not available")
                if hasattr(self, 'installed_text'):
                    self.installed_text.setPlainText("Error: Ollama Python package is not installed.\n\nPlease install it with: pip install ollama")
                return
            
            self.status_label.setText("Loading installed models...")
            
            # Test Ollama connection first
            try:
                # Get installed models
                models_response = ollama.list()
            except Exception as conn_error:
                error_msg = str(conn_error).lower()
                if "connection" in error_msg or "refused" in error_msg:
                    self.status_label.setText("Ollama server not running")
                    if hasattr(self, 'installed_text'):
                        self.installed_text.setPlainText("Error: Cannot connect to Ollama server.\n\nPlease ensure Ollama is running:\n1. Open a terminal/command prompt\n2. Run: ollama serve\n3. Or start Ollama from your system tray")
                elif "timeout" in error_msg:
                    self.status_label.setText("Ollama connection timeout")
                    if hasattr(self, 'installed_text'):
                        self.installed_text.setPlainText("Error: Ollama server connection timed out.\n\nThe server may be busy or not responding properly.")
                else:
                    self.status_label.setText(f"Ollama error: {str(conn_error)}")
                    if hasattr(self, 'installed_text'):
                        self.installed_text.setPlainText(f"Error connecting to Ollama:\n{str(conn_error)}\n\nPlease check that Ollama is properly installed and running.")
                return
            
            models = []
            
            if hasattr(models_response, 'models'):
                for model in models_response.models:
                    if hasattr(model, 'model'):
                        models.append(model)
                    elif hasattr(model, 'name'):
                        # Create a model-like object for consistency
                        class ModelInfo:
                            def __init__(self, name):
                                self.model = name
                                self.name = name
                        models.append(ModelInfo(model.name))
            elif 'models' in models_response:
                for model in models_response['models']:
                    class ModelInfo:
                        def __init__(self, data):
                            self.model = data.get('model', data.get('name', ''))
                            self.name = self.model
                            self.size = data.get('size', 0)
                            self.modified_at = data.get('modified_at', '')
                    models.append(ModelInfo(model))
            
            # Populate list and store model names
            for model in models:
                model_name = getattr(model, 'model', getattr(model, 'name', 'Unknown'))
                self.installed_models.append(model_name)  # Store the model name
                
                # Create list item
                item = QListWidgetItem(model_name)
                item.setData(Qt.ItemDataRole.UserRole, model)
                
                # Add visual indicator for vision models
                if any(vision_term in model_name.lower() for vision_term in ['llava', 'moondream', 'vision', 'bakllava']):
                    item.setText(f"Vision: {model_name} (Vision)")
                    item.setData(Qt.ItemDataRole.AccessibleTextRole, f"Vision model {model_name}")
                else:
                    item.setData(Qt.ItemDataRole.AccessibleTextRole, f"Model {model_name}")
                
                self.installed_list.addItem(item)
            
            self.status_label.setText(f"Found {len(models)} installed models")
            
            # Trigger filter update if filter methods exist
            if hasattr(self, 'filter_installed_models'):
                self.filter_installed_models()
            
        except Exception as e:
            error_msg = str(e).lower()
            if "connection" in error_msg or "refused" in error_msg:
                self.status_label.setText("Ollama server not running")
                if hasattr(self, 'installed_text'):
                    self.installed_text.setPlainText("Error: Cannot connect to Ollama server.\n\nPlease ensure Ollama is running:\n1. Open a terminal/command prompt\n2. Run: ollama serve\n3. Or start Ollama from your system tray")
            elif "timeout" in error_msg:
                self.status_label.setText("Ollama connection timeout")
                if hasattr(self, 'installed_text'):
                    self.installed_text.setPlainText("Error: Ollama server connection timed out.\n\nThe server may be busy or not responding properly.")
            elif "not found" in error_msg or "no such file" in error_msg:
                self.status_label.setText("Ollama not installed")
                if hasattr(self, 'installed_text'):
                    self.installed_text.setPlainText("Error: Ollama is not installed on this system.\n\nPlease install Ollama from: https://ollama.ai")
            else:
                self.status_label.setText(f"Error loading models: {str(e)}")
                if hasattr(self, 'installed_text'):
                    self.installed_text.setPlainText(f"Error loading models:\n{str(e)}\n\nPlease check your Ollama installation and try again.")
    
    def load_available_models(self):
        """Load available models using ollama search (if possible)"""
        self.status_label.setText("Checking for search capability...")
        
        try:
            # Check if search command is available
            result = subprocess.run(['ollama', 'search', '--help'], 
                                  capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                self.status_label.setText("Search capability detected")
                # Search is available - could implement actual search here
            else:
                self.status_label.setText("Search not available in this Ollama version - showing curated list")
                
        except subprocess.TimeoutExpired:
            self.status_label.setText("Search check timed out - showing curated list")
        except FileNotFoundError:
            self.status_label.setText("Ollama not found - showing curated list")
        except Exception as e:
            self.status_label.setText(f"Search unavailable - showing curated list")
        
        # Always show the enhanced curated list
        self.load_enhanced_popular_models()
    
    def load_enhanced_popular_models(self):
        """Load an enhanced curated list of popular vision models"""
        enhanced_models = [
            {
                "name": "moondream",
                "description": "A small vision language model (1.7B params) designed to run efficiently on edge devices. Great for basic image understanding tasks with minimal resource requirements.",
                "size": "~1.7GB",
                "capabilities": "Image understanding, basic Q&A, efficient on CPU"
            },
            {
                "name": "llava", 
                "description": "Large Language and Vision Assistant. The original and most popular multimodal model with excellent image analysis capabilities.",
                "size": "~4.1GB",
                "capabilities": "Advanced image analysis, detailed descriptions, complex visual reasoning"
            },
            {
                "name": "llava:7b",
                "description": "7B parameter version of LLaVA. Provides an excellent balance between performance and resource usage for most applications.",
                "size": "~4.1GB",
                "capabilities": "High-quality image descriptions, visual reasoning, good performance/size ratio"
            },
            {
                "name": "llava:13b",
                "description": "13B parameter version of LLaVA. Offers the highest quality results but requires more computational resources and memory.",
                "size": "~7.3GB", 
                "capabilities": "Excellent image analysis, very detailed descriptions, advanced reasoning, professional quality"
            },
            {
                "name": "llava:34b",
                "description": "34B parameter version of LLaVA. The largest and most capable version, suitable for professional applications with high-end hardware.",
                "size": "~19GB",
                "capabilities": "Professional-grade image analysis, extremely detailed descriptions, sophisticated reasoning"
            },
            {
                "name": "bakllava",
                "description": "BakLLaVA is an improved vision-language model based on LLaVA architecture with enhanced training methodology and better performance.",
                "size": "~4.1GB",
                "capabilities": "Enhanced image understanding, improved visual Q&A, detailed descriptions, stable performance"
            },
            {
                "name": "llava-llama3",
                "description": "LLaVA model based on Llama 3 architecture. Combines the visual capabilities of LLaVA with the improved language understanding of Llama 3.",
                "size": "~4.1GB",
                "capabilities": "Modern architecture, improved language understanding, excellent vision-language integration"
            },
            {
                "name": "llava-phi3",
                "description": "Compact vision model based on Microsoft's Phi-3 architecture. Offers good performance in a smaller package.",
                "size": "~2.2GB",
                "capabilities": "Compact size, efficient processing, good balance of capabilities and resource usage"
            }
        ]
        
        self.available_list.clear()
        for model_info in enhanced_models:
            # Create display name with visual indicator
            display_name = f"Vision: {model_info['name']}"
            
            # Add recommendation badges
            if model_info['name'] == 'llava:7b':
                display_name += " (Recommended)"
            elif model_info['name'] == 'moondream':
                display_name += " (Lightweight)"
            elif model_info['name'] == 'llava:13b':
                display_name += " (High Quality)"
            
            item = QListWidgetItem(display_name)
            item.setData(Qt.ItemDataRole.UserRole, model_info)
            item.setData(Qt.ItemDataRole.AccessibleTextRole, f"Vision model {model_info['name']}")
            self.available_list.addItem(item)
    
    def search_models(self):
        """Search for models using the search term"""
        search_term = self.search_input.text().strip()
        if not search_term:
            QMessageBox.information(self, "Search", "Please enter a search term.")
            return
        
        self.search_results.clear()
        self.search_details.clear()
        self.install_search_btn.setEnabled(False)
        
        self.status_label.setText(f"Searching for '{search_term}'...")
        
        try:
            # Try to use ollama search if available
            result = subprocess.run(['ollama', 'search', search_term], 
                                  capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0:
                # Parse the search results
                lines = result.stdout.strip().split('\n')
                
                # Skip header line if present
                model_lines = [line for line in lines if line.strip() and not line.startswith('NAME')]
                
                if model_lines:
                    for line in model_lines:
                        # Parse model line (format may vary)
                        parts = line.split()
                        if parts:
                            model_name = parts[0]
                            item = QListWidgetItem(model_name)
                            item.setData(Qt.ItemDataRole.UserRole, {'name': model_name, 'search_line': line})
                            self.search_results.addItem(item)
                    
                    self.status_label.setText(f"Found {len(model_lines)} models matching '{search_term}'")
                else:
                    self.status_label.setText(f"No models found matching '{search_term}'")
                    self.search_results.addItem(QListWidgetItem("No models found"))
            else:
                # Search command failed - show alternative
                self.show_search_alternative(search_term)
                
        except subprocess.TimeoutExpired:
            self.status_label.setText("Search timed out")
            self.show_search_alternative(search_term)
        except FileNotFoundError:
            self.status_label.setText("Ollama command not found - is Ollama installed?")
            self.show_search_alternative(search_term)
        except Exception as e:
            self.status_label.setText(f"Search unavailable in this Ollama version")
            self.show_search_alternative(search_term)
    
    def show_search_alternative(self, search_term):
        """Show alternative search results when ollama search is not available"""
        self.search_results.clear()
        
        # Add informational message
        info_item = QListWidgetItem("Search not available in this Ollama version")
        info_item.setData(Qt.ItemDataRole.UserRole, None)
        self.search_results.addItem(info_item)
        
        # Show alternative instructions
        alt_item = QListWidgetItem("Tip: Try browsing available models in the 'Available' tab")
        alt_item.setData(Qt.ItemDataRole.UserRole, None)
        self.search_results.addItem(alt_item)
        
        # Try to match against our curated list
        curated_matches = []
        enhanced_models = [
            "moondream", "llava", "llava:7b", "llava:13b", "llava:34b", 
            "bakllava", "llava-llama3", "llava-phi3"
        ]
        
        for model_name in enhanced_models:
            if search_term.lower() in model_name.lower():
                curated_matches.append(model_name)
        
        if curated_matches:
            match_item = QListWidgetItem("--- Matches from curated list ---")
            match_item.setData(Qt.ItemDataRole.UserRole, None)
            self.search_results.addItem(match_item)
            
            for match in curated_matches:
                item = QListWidgetItem(f"Vision: {match}")
                item.setData(Qt.ItemDataRole.UserRole, {'name': match, 'source': 'curated'})
                self.search_results.addItem(item)
            
            self.status_label.setText(f"Found {len(curated_matches)} matches in curated models")
        else:
            # Suggest manual model name entry
            manual_item = QListWidgetItem(f"Manual: Try installing '{search_term}' directly")
            manual_item.setData(Qt.ItemDataRole.UserRole, {'name': search_term, 'source': 'manual'})
            self.search_results.addItem(manual_item)
            
            self.status_label.setText("No matches found - you can try installing the exact model name")
    
    def on_installed_selection_changed(self):
        """Handle selection change in installed models"""
        current_item = self.installed_list.currentItem()
        if current_item:
            model = current_item.data(Qt.ItemDataRole.UserRole)
            self.delete_btn.setEnabled(True)
            
            # Show model details
            details = f"Model: {getattr(model, 'model', 'Unknown')}\n"
            if hasattr(model, 'size'):
                details += f"Size: {self.format_size(model.size)}\n"
            if hasattr(model, 'modified_at'):
                details += f"Modified: {model.modified_at}\n"
            
            self.installed_details.setPlainText(details)
        else:
            self.delete_btn.setEnabled(False)
            self.installed_details.clear()
    
    def on_available_selection_changed(self):
        """Handle selection change in available models"""
        current_item = self.available_list.currentItem()
        if current_item:
            model_info = current_item.data(Qt.ItemDataRole.UserRole)
            self.install_btn.setEnabled(True)
            
            # Show model information
            details = f"Model: {model_info['name']}\n"
            details += f"Description: {model_info['description']}\n"
            details += f"Estimated Size: {model_info['size']}\n"
            details += f"Capabilities: {model_info['capabilities']}\n"
            
            self.available_details.setPlainText(details)
        else:
            self.install_btn.setEnabled(False)
            self.available_details.clear()
    
    def on_search_selection_changed(self):
        """Handle selection change in search results"""
        current_item = self.search_results.currentItem()
        if current_item:
            model_data = current_item.data(Qt.ItemDataRole.UserRole)
            if model_data and 'name' in model_data:
                self.install_search_btn.setEnabled(True)
                
                # Show search result details
                details = f"Model: {model_data['name']}\n"
                if 'search_line' in model_data:
                    details += f"Search Result: {model_data['search_line']}\n"
                
                self.search_details.setPlainText(details)
            else:
                self.install_search_btn.setEnabled(False)
                self.search_details.clear()
        else:
            self.install_search_btn.setEnabled(False)
            self.search_details.clear()
    
    def install_selected_model(self):
        """Install the selected model from available list"""
        current_item = self.available_list.currentItem()
        if current_item:
            model_info = current_item.data(Qt.ItemDataRole.UserRole)
            self.install_model(model_info['name'])
    
    def install_search_selected_model(self):
        """Install the selected model from search results"""
        current_item = self.search_results.currentItem()
        if current_item:
            model_data = current_item.data(Qt.ItemDataRole.UserRole)
            if model_data and 'name' in model_data:
                self.install_model(model_data['name'])
    
    def install_model(self, model_name):
        """Install a model using ollama pull"""
        reply = QMessageBox.question(
            self, "Install Model",
            f"Install model '{model_name}'?\n\n"
            f"This will download the model which may be several GB in size.\n"
            f"The download may take some time depending on your internet connection.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.status_label.setText(f"Installing {model_name}...")
                
                # Start installation process
                process = subprocess.Popen(
                    ['ollama', 'pull', model_name],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    universal_newlines=True
                )
                
                self.installation_processes[model_name] = process
                
                # Show progress dialog
                progress_dialog = QMessageBox(self)
                progress_dialog.setWindowTitle("Installing Model")
                progress_dialog.setText(f"Installing {model_name}...\n\nThis may take several minutes.")
                progress_dialog.setStandardButtons(QMessageBox.StandardButton.Cancel)
                progress_dialog.setIcon(QMessageBox.Icon.Information)
                
                # Check if we can monitor the process (simplified version)
                # In a full implementation, we'd use QThread for proper async handling
                if progress_dialog.exec() == QMessageBox.StandardButton.Cancel:
                    # User cancelled
                    if model_name in self.installation_processes:
                        self.installation_processes[model_name].terminate()
                        del self.installation_processes[model_name]
                    self.status_label.setText("Installation cancelled")
                else:
                    # Wait for completion (simplified)
                    return_code = process.wait()
                    if return_code == 0:
                        self.status_label.setText(f"Successfully installed {model_name}")
                        self.refresh_installed_models()
                        QMessageBox.information(self, "Success", f"Model '{model_name}' installed successfully!")
                    else:
                        self.status_label.setText(f"Installation of {model_name} failed")
                        QMessageBox.warning(self, "Installation Failed", f"Failed to install '{model_name}'.")
                
            except FileNotFoundError:
                QMessageBox.critical(self, "Error", "Ollama command not found. Please ensure Ollama is installed and in your PATH.")
                self.status_label.setText("Ollama not found")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Installation failed: {str(e)}")
                self.status_label.setText(f"Installation error: {str(e)}")
    
    def delete_selected_model(self):
        """Delete the selected installed model"""
        current_item = self.installed_list.currentItem()
        if current_item:
            model = current_item.data(Qt.ItemDataRole.UserRole)
            model_name = getattr(model, 'model', getattr(model, 'name', 'Unknown'))
            
            reply = QMessageBox.question(
                self, "Delete Model",
                f"Delete model '{model_name}'?\n\n"
                f"This will permanently remove the model from your system.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    self.status_label.setText(f"Deleting {model_name}...")
                    
                    result = subprocess.run(['ollama', 'rm', model_name], 
                                          capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        self.status_label.setText(f"Successfully deleted {model_name}")
                        self.refresh_installed_models()
                        QMessageBox.information(self, "Success", f"Model '{model_name}' deleted successfully!")
                    else:
                        self.status_label.setText(f"Failed to delete {model_name}")
                        QMessageBox.warning(self, "Deletion Failed", f"Failed to delete '{model_name}': {result.stderr}")
                        
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Deletion failed: {str(e)}")
                    self.status_label.setText(f"Deletion error: {str(e)}")
    
    def format_size(self, size_bytes):
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "Unknown size"
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"


class ImageDescriberGUI(QMainWindow):
    """Main ImageDescriber application window"""
    
    def __init__(self):
        super().__init__()
        
        # Application state
        self.workspace = ImageWorkspace(new_workspace=True)  # Start as saved to avoid false "unsaved changes"
        self.current_workspace_file = None
        self._skip_verification = True  # Skip verification by default
        
        # Processing state
        self.processing_workers: List[ProcessingWorker] = []
        self.conversion_workers: List[ConversionWorker] = []
        self.batch_queue: List[str] = []
        self.processing_items: set = set()  # Track items being processed
        self.processing_status: dict = {}  # Track detailed status for each processing item
        
        # Batch processing tracking
        self.batch_total: int = 0
        self.batch_completed: int = 0
        self.batch_processing: bool = False
        
        # Filter settings
        self.filter_mode: str = "all"  # "all", "described", "undescribed", "batch", "videos", "images", or "processing"
        
        # Sorting settings
        self.sort_order: str = "date_oldest"  # "filename", "date_oldest", or "date_newest"
        
        # View mode settings
        self.view_mode: str = "tree"  # "tree" or "flat"
        
        # Navigation mode settings
        self.navigation_mode: str = "tree"  # "tree" or "master_detail"
        
        # Processing control
        self.stop_processing_requested: bool = False
        
        # Clipboard handling
        self.clipboard = QApplication.clipboard()
        self.paste_counter = 0  # For generating unique names
        
        # UI setup
        self.setup_ui()
        self.setup_menus()
        self.setup_shortcuts()
        self.setup_clipboard_monitoring()
        self.setup_tab_order()  # Set proper tab navigation order
        
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
        
        # Image preview panel (initially hidden) - add AFTER descriptions
        self.image_preview_panel = self.create_image_preview_widget()
        self.tree_splitter.addWidget(self.image_preview_panel)
        self.image_preview_panel.hide()  # Start hidden

        # Set splitter proportions (image list narrower, descriptions and preview get more space)
        # When preview is hidden: [250, 750] gives 25% to images, 75% to descriptions
        # When preview is shown: [250, 400, 350] gives reasonable distribution
        self.tree_splitter.setSizes([250, 750, 0])  # 0 for hidden preview initially

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

    def setup_tab_order(self):
        """Set up the tab order for keyboard navigation"""
        # Tab order for tree view: image list → description list → description text → image preview
        self.setTabOrder(self.image_list, self.description_list)
        self.setTabOrder(self.description_list, self.description_text)
        if hasattr(self, 'image_preview_label'):
            self.setTabOrder(self.description_text, self.image_preview_label)
        
        # Tab order for master-detail view
        self.setTabOrder(self.media_list, self.frames_list)
        self.setTabOrder(self.frames_list, self.description_list_md)
        self.setTabOrder(self.description_list_md, self.description_text_md)

    def create_image_preview_widget(self):
        """Create the image preview widget with fullscreen capability"""
        from PyQt6.QtWidgets import QLabel
        from PyQt6.QtGui import QPixmap
        from PyQt6.QtCore import Qt, QEvent as QtEvent
        
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        preview_layout.addWidget(QLabel("Image Preview:"))
        
        # Create image label with scaling
        self.image_preview_label = QLabel()
        self.image_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_preview_label.setScaledContents(False)
        self.image_preview_label.setStyleSheet("QLabel { background-color: #2b2b2b; border: 1px solid #555; }")
        self.image_preview_label.setMinimumSize(200, 200)
        self.image_preview_label.setAccessibleName("Image Preview")
        self.image_preview_label.setAccessibleDescription("Preview of the currently selected image. Press Enter for fullscreen, Escape to exit fullscreen.")
        self.image_preview_label.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.image_preview_label.setTabletTracking(True)
        
        # Install event filter to handle Enter/Escape keys
        self.image_preview_label.installEventFilter(self)
        
        # Store original pixmap for fullscreen display
        self.current_preview_pixmap = None
        self.is_fullscreen_preview = False
        
        preview_layout.addWidget(self.image_preview_label)
        
        return preview_widget
    
    def eventFilter(self, obj, event):
        """Event filter to handle Enter/Escape on image preview"""
        from PyQt6.QtCore import QEvent
        if obj == self.image_preview_label and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
                self.show_fullscreen_preview()
                return True
            elif event.key() == Qt.Key.Key_Escape and self.is_fullscreen_preview:
                self.hide_fullscreen_preview()
                return True
        return super().eventFilter(obj, event)
    
    def show_fullscreen_preview(self):
        """Show the current image in fullscreen"""
        if not self.current_preview_pixmap or self.current_preview_pixmap.isNull():
            return
        
        # Create fullscreen dialog
        self.fullscreen_dialog = QDialog(self)
        self.fullscreen_dialog.setWindowTitle("Image Preview - Press Escape to Exit")
        self.fullscreen_dialog.setWindowState(Qt.WindowState.WindowFullScreen)
        self.fullscreen_dialog.setStyleSheet("background-color: black;")
        
        layout = QVBoxLayout(self.fullscreen_dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        
        fullscreen_label = QLabel()
        fullscreen_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fullscreen_label.setPixmap(self.current_preview_pixmap.scaled(
            self.fullscreen_dialog.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        ))
        fullscreen_label.setAccessibleName("Fullscreen Image Preview")
        fullscreen_label.setAccessibleDescription("Fullscreen view of the image. Press Escape to exit.")
        
        layout.addWidget(fullscreen_label)
        
        # Handle Escape key
        def keyPressEvent(event):
            if event.key() == Qt.Key.Key_Escape:
                self.hide_fullscreen_preview()
        
        self.fullscreen_dialog.keyPressEvent = keyPressEvent
        self.is_fullscreen_preview = True
        self.fullscreen_dialog.exec()
    
    def hide_fullscreen_preview(self):
        """Hide the fullscreen preview and return to normal view"""
        if hasattr(self, 'fullscreen_dialog'):
            self.fullscreen_dialog.close()
            self.is_fullscreen_preview = False
    
    def _update_preview_accessible_name(self, file_path: str):
        """Update the preview's accessible name with the display name or filename"""
        try:
            # Try to get the custom display name from workspace
            workspace_item = self.workspace.get_item(file_path)
            if workspace_item and workspace_item.display_name:
                display_name = workspace_item.display_name
            else:
                # Fall back to filename
                display_name = Path(file_path).name
            
            # Set accessible name and description
            self.image_preview_label.setAccessibleName(f"Image Preview: {display_name}")
            self.image_preview_label.setAccessibleDescription(
                f"Preview of {display_name}. Press Enter for fullscreen, Escape to exit fullscreen."
            )
        except Exception as e:
            # Fallback to generic name if anything fails
            print(f"Warning: Could not update preview accessible name: {e}")
            self.image_preview_label.setAccessibleName("Image Preview")
    
    def update_image_preview(self):
        """Update the image preview with the currently selected image"""
        if not hasattr(self, 'image_preview_label') or not self.show_image_preview_action.isChecked():
            return
        
        file_path = self.get_current_selected_file_path()
        if not file_path or not Path(file_path).exists():
            self.image_preview_label.setText("No image selected")
            self.current_preview_pixmap = None
            return
        
        try:
            from PIL import Image
            from PyQt6.QtGui import QImage
            import io
            
            # Handle HEIC files
            file_path_obj = Path(file_path)
            if file_path_obj.suffix.lower() in ['.heic', '.heif']:
                try:
                    import pillow_heif
                    pillow_heif.register_heif_opener()
                except ImportError:
                    self.image_preview_label.setText("HEIC support not available\nInstall pillow-heif")
                    self.current_preview_pixmap = None
                    return
            
            # Load image with PIL (supports more formats including HEIC)
            try:
                pil_image = Image.open(file_path)
                
                # Convert to RGB if necessary (for transparency, CMYK, etc.)
                if pil_image.mode not in ('RGB', 'RGBA', 'L'):
                    pil_image = pil_image.convert('RGB')
                
                # Convert PIL Image to QPixmap via QImage
                # First convert to bytes
                image_data = io.BytesIO()
                
                # Save as PNG to preserve quality
                if pil_image.mode == 'RGBA':
                    pil_image.save(image_data, format='PNG')
                    qimage = QImage()
                    qimage.loadFromData(image_data.getvalue())
                else:
                    # For RGB and grayscale, convert to bytes
                    if pil_image.mode == 'L':
                        pil_image = pil_image.convert('RGB')
                    
                    # Convert to RGB bytes
                    img_bytes = pil_image.tobytes('raw', 'RGB')
                    qimage = QImage(img_bytes, pil_image.width, pil_image.height, 
                                   pil_image.width * 3, QImage.Format.Format_RGB888)
                
                if qimage.isNull():
                    self.image_preview_label.setText("Unable to convert image format")
                    self.current_preview_pixmap = None
                    return
                
                # Convert QImage to QPixmap
                from PyQt6.QtGui import QPixmap
                pixmap = QPixmap.fromImage(qimage)
                
                if pixmap.isNull():
                    self.image_preview_label.setText("Unable to create pixmap")
                    self.current_preview_pixmap = None
                    return
                
                # Store original for fullscreen
                self.current_preview_pixmap = pixmap
                
                # Scale to fit preview area
                scaled_pixmap = pixmap.scaled(
                    self.image_preview_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                
                self.image_preview_label.setPixmap(scaled_pixmap)
                
                # Update accessible name to use the display name or filename
                self._update_preview_accessible_name(file_path)
                
            except Exception as img_error:
                # If PIL fails, try direct QPixmap load as fallback
                print(f"PIL loading failed: {img_error}, trying QPixmap directly")
                from PyQt6.QtGui import QPixmap
                pixmap = QPixmap(file_path)
                if pixmap.isNull():
                    self.image_preview_label.setText(f"Unable to load image:\n{file_path_obj.name}")
                    self.current_preview_pixmap = None
                    return
                
                self.current_preview_pixmap = pixmap
                scaled_pixmap = pixmap.scaled(
                    self.image_preview_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.image_preview_label.setPixmap(scaled_pixmap)
                
                # Update accessible name to use the display name or filename
                self._update_preview_accessible_name(file_path)
            
        except Exception as e:
            self.image_preview_label.setText(f"Error loading image:\n{str(e)}")
            self.current_preview_pixmap = None
            print(f"Image preview error for {file_path}: {e}")
            import traceback
            traceback.print_exc()
    
    def toggle_image_preview(self):
        """Toggle the visibility of the image preview panel"""
        if self.show_image_preview_action.isChecked():
            self.image_preview_panel.show()
            # Adjust splitter sizes to give preview meaningful space
            # Distribution: 25% images, 40% descriptions, 35% preview
            total_width = self.tree_splitter.width()
            self.tree_splitter.setSizes([
                int(total_width * 0.25),  # Image list (narrower)
                int(total_width * 0.40),  # Descriptions
                int(total_width * 0.35)   # Preview (meaningful size)
            ])
            # Update tab order to include preview
            if hasattr(self, 'image_preview_label'):
                self.setTabOrder(self.description_text, self.image_preview_label)
            self.update_image_preview()
        else:
            self.image_preview_panel.hide()
            # Restore two-panel layout when preview is hidden
            # Distribution: 25% images, 75% descriptions
            total_width = self.tree_splitter.width()
            self.tree_splitter.setSizes([
                int(total_width * 0.25),  # Image list
                int(total_width * 0.75),  # Descriptions
                0                          # Preview hidden
            ])
            # Tab order stops at description_text when preview is hidden
            # (preview is not in focus chain when hidden)
    
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
        file_menu = menubar.addMenu("&File")
        
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
        
        import_workflow_action = QAction("Import Workflow...", self)
        import_workflow_action.triggered.connect(self.import_workflow)
        file_menu.addAction(import_workflow_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Workspace menu
        workspace_menu = menubar.addMenu("&Workspace")
        
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
        process_menu = menubar.addMenu("&Processing")
        
        process_sel_action = QAction("Process Selected", self)
        process_sel_action.setShortcut(QKeySequence("P"))
        process_sel_action.triggered.connect(self.process_selected)
        process_menu.addAction(process_sel_action)
        
        batch_mark_action = QAction("Mark for Batch", self)
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
        
        chat_action = QAction("Chat with Model", self)
        chat_action.setShortcut(QKeySequence("C"))
        chat_action.triggered.connect(self.start_chat_session)
        process_menu.addAction(chat_action)
        
        view_chats_action = QAction("View Chat Sessions", self)
        view_chats_action.triggered.connect(self.view_chat_sessions)
        process_menu.addAction(view_chats_action)
        
        process_menu.addSeparator()
        
        # Workflow integration
        self.import_workflow_action = QAction("Import Workflow...", self)
        self.import_workflow_action.triggered.connect(self.import_workflow_results)
        self.import_workflow_action.setToolTip("Import results from workflow processing")
        process_menu.addAction(self.import_workflow_action)
        
        self.update_workflow_action = QAction("Update from Workflow...", self)
        self.update_workflow_action.triggered.connect(self.update_from_workflow)
        self.update_workflow_action.setToolTip("Update workspace with new workflow results")
        self.update_workflow_action.setEnabled(False)  # Initially disabled
        process_menu.addAction(self.update_workflow_action)
        
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
        
        rename_action = QAction("Rename Item", self)
        rename_action.setShortcut(QKeySequence("R"))
        rename_action.triggered.connect(self.rename_item)
        process_menu.addAction(rename_action)
        
        process_menu.addSeparator()
        
        # Descriptions menu
        desc_menu = menubar.addMenu("&Descriptions")
        
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
        view_menu = menubar.addMenu("&View")
        
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
        
        self.filter_undescribed_action = QAction("Show Undescribed Only", self)
        self.filter_undescribed_action.setCheckable(True)
        self.filter_undescribed_action.triggered.connect(lambda: self.set_filter("undescribed"))
        filter_menu.addAction(self.filter_undescribed_action)
        
        self.filter_batch_action = QAction("Show Batch Items Only", self)
        self.filter_batch_action.setCheckable(True)
        self.filter_batch_action.triggered.connect(lambda: self.set_filter("batch"))
        filter_menu.addAction(self.filter_batch_action)
        
        self.filter_videos_action = QAction("Show Videos Only", self)
        self.filter_videos_action.setCheckable(True)
        self.filter_videos_action.triggered.connect(lambda: self.set_filter("videos"))
        filter_menu.addAction(self.filter_videos_action)
        
        self.filter_images_action = QAction("Show Images Only", self)
        self.filter_images_action.setCheckable(True)
        self.filter_images_action.triggered.connect(lambda: self.set_filter("images"))
        filter_menu.addAction(self.filter_images_action)
        
        self.filter_processing_action = QAction("Show Processing Only", self)
        self.filter_processing_action.setCheckable(True)
        self.filter_processing_action.triggered.connect(lambda: self.set_filter("processing"))
        filter_menu.addAction(self.filter_processing_action)
        
        view_menu.addSeparator()
        
        # View Mode submenu
        view_mode_menu = view_menu.addMenu("View Mode")
        
        self.view_mode_tree_action = QAction("Image Tree", self)
        self.view_mode_tree_action.setCheckable(True)
        self.view_mode_tree_action.setChecked(True)  # Default
        self.view_mode_tree_action.triggered.connect(lambda: self.set_view_mode("tree"))
        view_mode_menu.addAction(self.view_mode_tree_action)
        
        self.view_mode_flat_action = QAction("Flat Image List", self)
        self.view_mode_flat_action.setCheckable(True)
        self.view_mode_flat_action.triggered.connect(lambda: self.set_view_mode("flat"))
        view_mode_menu.addAction(self.view_mode_flat_action)
        
        view_menu.addSeparator()
        
        # Sort submenu
        sort_menu = view_menu.addMenu("Sort by")
        
        self.sort_filename_action = QAction("Filename", self)
        self.sort_filename_action.setCheckable(True)
        self.sort_filename_action.triggered.connect(lambda: self.set_sort_order("filename"))
        sort_menu.addAction(self.sort_filename_action)
        
        self.sort_date_oldest_action = QAction("Date (Oldest First)", self)
        self.sort_date_oldest_action.setCheckable(True)
        self.sort_date_oldest_action.setChecked(True)  # Default
        self.sort_date_oldest_action.triggered.connect(lambda: self.set_sort_order("date_oldest"))
        sort_menu.addAction(self.sort_date_oldest_action)
        
        self.sort_date_newest_action = QAction("Date (Newest First)", self)
        self.sort_date_newest_action.setCheckable(True)
        self.sort_date_newest_action.triggered.connect(lambda: self.set_sort_order("date_newest"))
        sort_menu.addAction(self.sort_date_newest_action)
        
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
        
        # Image Preview toggle
        self.show_image_preview_action = QAction("Show Image Preview", self)
        self.show_image_preview_action.setCheckable(True)
        self.show_image_preview_action.setChecked(False)  # Default off
        self.show_image_preview_action.triggered.connect(self.toggle_image_preview)
        view_menu.addAction(self.show_image_preview_action)
        
        view_menu.addSeparator()
        
        # Show all descriptions in list
        show_all_descriptions_action = QAction("Show All Descriptions in List", self)
        show_all_descriptions_action.triggered.connect(self.show_all_descriptions_dialog)
        view_menu.addAction(show_all_descriptions_action)
        
        view_menu.addSeparator()
        
        # Properties menu item
        properties_action = QAction("Properties", self)
        properties_action.triggered.connect(self.show_image_properties)
        view_menu.addAction(properties_action)
        
        # Description Properties - NEW DIAGNOSTIC FEATURE
        desc_properties_action = QAction("Description Properties", self)
        desc_properties_action.setShortcut("Ctrl+Shift+P")
        desc_properties_action.triggered.connect(self.show_description_properties)
        view_menu.addAction(desc_properties_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        model_manager_action = QAction("Model Management Tools...", self)
        model_manager_action.setStatusTip("Information about external model management tools (check_models.py, manage_models.py)")
        model_manager_action.triggered.connect(self.show_model_manager)
        help_menu.addAction(model_manager_action)
        
        help_menu.addSeparator()
        
        readme_action = QAction("Readme", self)
        readme_action.triggered.connect(self.open_readme)
        help_menu.addAction(readme_action)
        
        download_ollama_action = QAction("Download Ollama", self)
        download_ollama_action.triggered.connect(self.open_ollama_download)
        help_menu.addAction(download_ollama_action)
        
        help_menu.addSeparator()
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)
    
    def setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        # Additional shortcuts not in menus
        pass
    
    def get_short_model_name(self, model_name):
        """Extract short, readable model name from full model name"""
        if not model_name:
            return "Unknown"
        
        # Common model name mappings
        model_mappings = {
            'llama': 'Llama',
            'moondream': 'Moondream', 
            'mistral': 'Mistral',
            'phi': 'Phi',
            'gemma': 'Gemma',
            'qwen': 'Qwen',
            'gpt-4': 'GPT-4',
            'gpt-3.5': 'GPT-3.5',
            'gpt-4o': 'GPT-4o',
            'claude': 'Claude',
            'blip': 'BLIP',
            'git-base': 'GIT',
            'instructblip': 'InstructBLIP'
        }
        
        model_lower = model_name.lower()
        
        # Check for exact matches first
        for key, value in model_mappings.items():
            if key in model_lower:
                return value
        
        # If no mapping found, try to extract a reasonable short name
        # Remove common prefixes and suffixes
        short_name = model_name
        if '/' in short_name:
            short_name = short_name.split('/')[-1]  # Take last part after slash
        
        # Remove version numbers and common suffixes
        for suffix in ['-chat', '-instruct', '-base', '-7b', '-13b', '-70b', '-2.7b', '-opt']:
            if suffix in short_name.lower():
                short_name = short_name.replace(suffix, '').replace(suffix.upper(), '')
        
        # Capitalize first letter
        return short_name.capitalize()
    
    def setup_clipboard_monitoring(self):
        """Setup clipboard monitoring for paste functionality"""
        # Connect to clipboard change signal
        self.clipboard.dataChanged.connect(self.on_clipboard_changed)
        
    def on_clipboard_changed(self):
        """Handle clipboard content changes - called when clipboard content changes"""
        # We don't auto-paste on clipboard change, only on explicit Ctrl+V
        pass
    
    def keyPressEvent(self, event):
        """Handle global key presses including Ctrl+V for paste"""
        print(f"DEBUG: ImageDescriber keyPressEvent called with key: {event.key()}")
        if event.key() == Qt.Key.Key_V and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            # Handle Ctrl+V paste
            self.handle_paste_from_clipboard()
        elif event.key() == Qt.Key.Key_F2:
            self.rename_item()
        elif event.key() == Qt.Key.Key_F and event.modifiers() == Qt.KeyboardModifier.NoModifier:
            # F key for followup question
            self.ask_followup_question()
        elif event.key() == Qt.Key.Key_Z and event.modifiers() == Qt.KeyboardModifier.NoModifier:
            # Auto-rename using AI-generated caption (hidden feature)
            print("DEBUG: Z key pressed in ImageDescriber, calling auto_rename_item")
            self.auto_rename_item()
        else:
            super().keyPressEvent(event)
    
    def handle_paste_from_clipboard(self):
        """Handle Ctrl+V paste operation - extract image/video from clipboard and add to workspace"""
        try:
            mimeData = self.clipboard.mimeData()
            
            # Check if clipboard has image data
            if mimeData.hasImage():
                # Get the image from clipboard
                image = self.clipboard.image()
                if not image.isNull():
                    self.process_pasted_image(image)
                    return
            
            # Check for file URLs (drag & drop or copy from file manager)
            if mimeData.hasUrls():
                urls = mimeData.urls()
                if urls:
                    # Process first URL if it's a local file
                    url = urls[0]
                    if url.isLocalFile():
                        file_path = url.toLocalFile()
                        if self.is_supported_media_file(file_path):
                            self.add_file_to_workspace(file_path, is_pasted=True)
                            return
            
            # If we get here, no supported content was found
            self.status_bar.showMessage("No image or supported media found in clipboard", 3000)
            
        except Exception as e:
            QMessageBox.warning(self, "Paste Error", f"Failed to paste from clipboard:\n{e}")
    
    def process_pasted_image(self, qimage):
        """Process a QImage from clipboard and save it to workspace"""
        try:
            # Generate unique filename
            self.paste_counter += 1
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"pasted_image_{self.paste_counter}_{timestamp}.png"
            
            # Create temp directory if it doesn't exist
            temp_dir = Path(tempfile.gettempdir()) / "ImageDescriber_Pasted"
            temp_dir.mkdir(exist_ok=True)
            
            # Save the image to temp file
            temp_file_path = temp_dir / filename
            success = qimage.save(str(temp_file_path), "PNG")
            
            if success:
                # Add to workspace and process
                self.add_file_to_workspace(str(temp_file_path), is_pasted=True)
                self.status_bar.showMessage(f"Pasted image added as {filename}", 3000)
            else:
                raise Exception("Failed to save image to temporary file")
                
        except Exception as e:
            QMessageBox.warning(self, "Paste Error", f"Failed to process pasted image:\n{e}")
    
    def is_supported_media_file(self, file_path):
        """Check if file is a supported image or video format"""
        ext = Path(file_path).suffix.lower()
        image_exts = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.heic', '.heif'}
        video_exts = {'.mp4', '.mov', '.avi', '.mkv', '.wmv'}
        return ext in (image_exts | video_exts)
    
    def add_file_to_workspace(self, file_path, is_pasted=False):
        """Add a file to the current workspace and optionally trigger processing"""
        try:
            # Check if already in workspace
            if file_path in self.workspace.items:
                self.status_bar.showMessage(f"File already in workspace: {Path(file_path).name}", 3000)
                return
            
            # Determine file type
            ext = Path(file_path).suffix.lower()
            video_exts = {'.mp4', '.mov', '.avi', '.mkv', '.wmv'}
            item_type = "video" if ext in video_exts else "image"
            
            # Create and add the item
            item = ImageItem(file_path, item_type)
            self.workspace.add_item(item)
            
            # Refresh the display
            self.refresh_view()
            
            # Select the new item
            for i in range(self.image_list.count()):
                list_item = self.image_list.item(i)
                if list_item.data(Qt.ItemDataRole.UserRole) == file_path:
                    self.image_list.setCurrentItem(list_item)
                    break
            
            # If it's a pasted item, trigger immediate processing with defaults
            if is_pasted:
                print(f"DEBUG: Triggering automatic processing for pasted file: {file_path}")
                self.trigger_automatic_processing(file_path)
                
        except Exception as e:
            QMessageBox.warning(self, "Add File Error", f"Failed to add file to workspace:\n{e}")
    
    def trigger_automatic_processing(self, file_path):
        """Trigger automatic processing of a pasted file with current defaults"""
        print(f"DEBUG: trigger_automatic_processing called for {file_path}")
        try:
            # Load configuration defaults
            config = self.load_prompt_config()
            default_prompt_style = config.get("default_prompt_style", "Narrative")
            prompt_variations = config.get("prompt_variations", {})
            model_settings = config.get("model_settings", {})
            
            # Get default prompt text
            if default_prompt_style in prompt_variations:
                custom_prompt = prompt_variations[default_prompt_style]
            else:
                custom_prompt = config.get("prompt_template", "Describe this image in detail.")
            
            # Get default model from config
            config_model = model_settings.get("model", "moondream")
            
            # Find first available provider with models (use global instances)
            providers = {
                "ollama": _ollama_provider,
                "openai": _openai_provider,
                "claude": _claude_provider
            }
            
            provider_instance = None
            provider_name = None
            model_name = None
            
            print(f"DEBUG: Checking providers for automatic processing...")
            for name, instance in providers.items():
                print(f"DEBUG: Checking provider {name}, available: {instance.is_available()}")
                if instance.is_available():
                    try:
                        models = instance.get_models()
                        print(f"DEBUG: Provider {name} has {len(models) if models else 0} models")
                        if models and len(models) > 0:
                            provider_instance = instance
                            provider_name = name
                            # Try to use config model first, fallback to first available
                            if name == "ollama" and config_model in models:
                                model_name = config_model
                            else:
                                model_name = models[0]
                            print(f"DEBUG: Selected provider {name} with model {model_name}")
                            break
                    except Exception as e:
                        print(f"DEBUG: Error checking provider {name}: {e}")
                        continue
            
            if not provider_instance or not model_name:
                # Debug information for troubleshooting
                available_providers = []
                for name, instance in providers.items():
                    try:
                        if instance.is_available():
                            models = instance.get_models()
                            available_providers.append(f"{name}: {len(models) if models else 0} models")
                        else:
                            available_providers.append(f"{name}: not available")
                    except Exception as e:
                        available_providers.append(f"{name}: error - {e}")
                
                debug_info = "; ".join(available_providers)
                self.status_bar.showMessage(f"No AI providers available for auto-processing. Status: {debug_info}", 5000)
                return
            
            # Start processing directly without dialog
            self.processing_items.add(file_path)
            self.update_window_title()
            
            worker = ProcessingWorker(file_path, provider_name, model_name, default_prompt_style, custom_prompt)
            worker.progress_updated.connect(self.on_processing_progress)
            worker.processing_complete.connect(self.on_processing_complete)
            worker.processing_failed.connect(self.on_processing_failed)
            
            self.processing_workers.append(worker)
            worker.start()
            
            self.status_bar.showMessage(f"Auto-processing with {provider_name}: {model_name} ({default_prompt_style})", 5000)
            
            # Refresh view to show processing indicator
            self.refresh_view()
                
        except Exception as e:
            # Don't show error dialog for auto-processing failures, just status message
            self.status_bar.showMessage(f"Auto-processing failed: {str(e)[:100]}...", 5000)
    
    def update_window_title(self, custom_status=None):
        """Update the window title with optional custom status message"""
        # Start with filter status
        filter_display = {
            "all": "All",
            "described": "Described", 
            "batch": "Batch",
            "videos": "Videos",
            "images": "Images",
            "processing": "Processing"
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
        # Check for unsaved changes before opening
        if not self.workspace.saved:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "You have unsaved changes. Continue without saving?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
        
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
                self.update_menu_states()  # Update menu states after loading workspace
                
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
    
    def ensure_workspace_saved_for_chat(self):
        """Ensure workspace is saved when using chat features"""
        if not self.current_workspace_file:
            # Create a default workspace file for chat sessions
            from datetime import datetime
            default_name = f"chat_workspace_{datetime.now().strftime('%Y%m%d_%H%M%S')}.idw"
            default_path = Path.home() / "Documents" / default_name
            
            try:
                self.save_workspace_to_file(str(default_path))
                self.current_workspace_file = str(default_path)
                self.status_bar.showMessage(f"Auto-saved workspace to {default_path.name}", 3000)
                self.refresh_view()
            except Exception as e:
                # If auto-save fails, show warning but don't block chat
                print(f"Warning: Could not auto-save workspace: {e}")
                self.status_bar.showMessage("Warning: Chat history may not persist - please save workspace manually", 5000)
    
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
    
    def import_workflow(self):
        """Import descriptions from a workflow directory into the current workspace"""
        from datetime import datetime
        
        # Select workflow directory
        workflow_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Workflow Directory",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        
        if not workflow_dir:
            return
        
        workflow_path = Path(workflow_dir)
        desc_file = workflow_path / "descriptions" / "image_descriptions.txt"
        
        if not desc_file.exists():
            QMessageBox.warning(
                self,
                "Import Failed",
                f"Could not find image_descriptions.txt in workflow directory.\n\n"
                f"Expected: {desc_file}"
            )
            return
        
        try:
            # Disable auto-refresh during import to prevent crashes
            self.image_list.setUpdatesEnabled(False)
            
            # Load file path mapping if it exists
            mapping_file = workflow_path / "descriptions" / "file_path_mapping.json"
            file_path_mapping = {}
            original_source_dir = None
            video_to_frames = {}  # Map original video path -> list of extracted frame paths
            
            if mapping_file.exists():
                try:
                    import json
                    with open(mapping_file, 'r', encoding='utf-8') as f:
                        file_path_mapping = json.load(f)
                    self.status_bar.showMessage(f"Loaded {len(file_path_mapping)} file path mappings", 2000)
                except Exception as e:
                    QMessageBox.warning(
                        self,
                        "Mapping File Warning",
                        f"Could not load file_path_mapping.json.\n"
                        f"Some files may not be found.\n\n"
                        f"Error: {str(e)}"
                    )
            else:
                # No mapping file - try to parse workflow log for original source directory
                workflow_logs = list(workflow_path.glob("logs/workflow_*.log"))
                if workflow_logs:
                    try:
                        with open(workflow_logs[0], 'r', encoding='utf-8') as f:
                            for line in f:
                                if "Input directory:" in line:
                                    # Extract the directory path from log line
                                    original_source_dir = line.split("Input directory:")[-1].strip()
                                    self.status_bar.showMessage(f"Found original source: {original_source_dir}", 3000)
                                    break
                    except Exception as e:
                        pass
                
                if not original_source_dir:
                    self.status_bar.showMessage("No file mapping found - some files from original sources may be missing", 3000)
            
            # Parse frame extractor log to find original videos
            # Strategy: Scan extracted_frames directory and reconstruct video paths
            extracted_frames_dir = workflow_path / "extracted_frames"
            if extracted_frames_dir.exists():
                for video_dir in extracted_frames_dir.iterdir():
                    if video_dir.is_dir():
                        video_name = video_dir.name  # e.g., "IMG_3136" or "video-10898_singular_display"
                        
                        # Find frames in this directory
                        frame_files = list(video_dir.glob("*.jpg")) + list(video_dir.glob("*.png"))
                        if not frame_files:
                            continue
                        
                        # Try to find the original video path
                        video_path = None
                        
                        # 1. Check frame extractor log for explicit path
                        frame_extractor_logs = list(workflow_path.glob("logs/frame_extractor_*.log"))
                        if frame_extractor_logs:
                            try:
                                with open(frame_extractor_logs[0], 'r', encoding='utf-8') as f:
                                    for line in f:
                                        if "Found video file:" in line and video_name in line:
                                            video_path = line.split("Found video file:")[-1].strip()
                                            break
                            except:
                                pass
                        
                        # 2. If not in log, try to reconstruct from original source directory
                        if not video_path and original_source_dir:
                            # Try common video extensions
                            for ext in ['.MOV', '.mov', '.mp4', '.MP4', '.avi', '.AVI', '.mkv', '.MKV']:
                                candidate = Path(original_source_dir) / f"{video_name}{ext}"
                                if candidate.exists():
                                    video_path = str(candidate)
                                    break
                        
                        # Store the mapping if we found the video
                        if video_path:
                            video_to_frames[video_path] = [str(f) for f in frame_files]
            
            # Read and parse the descriptions file
            with open(desc_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split by separator (80 dashes)
            entries = content.split('-' * 80)
            
            imported_count = 0
            duplicate_count = 0
            missing_file_count = 0
            error_count = 0
            directories_to_add = set()  # Track unique directories
            
            # Show progress dialog
            from PyQt6.QtWidgets import QProgressDialog
            progress = QProgressDialog(
                f"Importing descriptions from workflow...", 
                "Cancel", 0, len(entries), self
            )
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.show()
            
            for i, entry in enumerate(entries):
                if progress.wasCanceled():
                    break
                
                entry = entry.strip()
                if not entry:
                    continue
                
                try:
                    # Parse entry fields
                    lines = entry.split('\n')
                    file_path = None
                    provider = None
                    model = None
                    prompt_style = None
                    description_lines = []
                    
                    reading_description = False
                    for line in lines:
                        if line.startswith('File: '):
                            file_path = line[6:].strip()
                        elif line.startswith('Provider: '):
                            provider = line[10:].strip()
                        elif line.startswith('Model: '):
                            model = line[7:].strip()
                        elif line.startswith('Prompt Style: '):
                            prompt_style = line[14:].strip()
                        elif line.startswith('Description: '):
                            reading_description = True
                            description_lines.append(line[13:].strip())
                        elif reading_description and line.strip():
                            description_lines.append(line.strip())
                    
                    if not all([file_path, provider, model, prompt_style, description_lines]):
                        error_count += 1
                        continue
                    
                    description = ' '.join(description_lines)
                    
                    # Map file path to actual location
                    actual_path = None
                    
                    # Normalize the file path (handle backslashes on Windows)
                    file_path_normalized = file_path.replace('\\', '/')
                    
                    # 1. Check file path mapping first (for files from temp_combined_images)
                    if file_path in file_path_mapping:
                        mapped_path = Path(file_path_mapping[file_path])
                        if mapped_path.exists():
                            actual_path = str(mapped_path.resolve())
                    elif file_path_normalized in file_path_mapping:
                        mapped_path = Path(file_path_mapping[file_path_normalized])
                        if mapped_path.exists():
                            actual_path = str(mapped_path.resolve())
                    
                    # 2. If not in mapping, check if it's a relative path within workflow
                    if not actual_path:
                        relative_path = Path(file_path_normalized)
                        if len(relative_path.parts) > 0 and relative_path.parts[0] in ['converted_images', 'extracted_frames']:
                            candidate = workflow_path / file_path_normalized
                            if candidate.exists():
                                actual_path = str(candidate.resolve())
                    
                    # 3. If we have original source directory, try to reconstruct path
                    #    This handles files like "09\IMG_3137.PNG" from temp_combined_images
                    if not actual_path and original_source_dir:
                        try:
                            # Extract just the filename from paths like "09\IMG_3137.PNG"
                            file_parts = Path(file_path_normalized).parts
                            if len(file_parts) >= 2:
                                # Try: original_source_dir / filename
                                candidate = Path(original_source_dir) / file_parts[-1]
                                if candidate.exists():
                                    actual_path = str(candidate.resolve())
                        except:
                            pass
                    
                    # 4. If still not found, try as absolute path
                    if not actual_path:
                        try:
                            candidate_path = Path(file_path)
                            if candidate_path.exists():
                                actual_path = str(candidate_path.resolve())
                        except:
                            pass
                    
                    # If still not found, skip this entry
                    if not actual_path:
                        missing_file_count += 1
                        continue
                    
                    # Get or create ImageItem
                    if actual_path in self.workspace.items:
                        item = self.workspace.items[actual_path]
                    else:
                        # Determine item type
                        item_type = "image"
                        if Path(actual_path).suffix.lower() in {'.mp4', '.mov', '.avi', '.mkv', '.wmv'}:
                            item_type = "video"
                        
                        item = ImageItem(actual_path, item_type)
                        self.workspace.add_item(item)
                        
                        # Track parent directory to add later
                        parent_dir = str(Path(actual_path).parent)
                        directories_to_add.add(parent_dir)
                    
                    # Create ImageDescription
                    desc_obj = ImageDescription(
                        text=description,
                        model=model,
                        prompt_style=prompt_style,
                        provider=provider,
                        created=datetime.now().isoformat()
                    )
                    
                    # Ensure item.descriptions is a list
                    if not hasattr(item, 'descriptions') or item.descriptions is None:
                        item.descriptions = []
                    
                    # Add description if not duplicate
                    is_duplicate = any(
                        d.text == description and d.model == model and d.provider == provider
                        for d in item.descriptions
                    )
                    
                    if not is_duplicate:
                        item.descriptions.append(desc_obj)
                        imported_count += 1
                    else:
                        duplicate_count += 1
                
                except Exception as e:
                    # Silently count errors during parsing
                    error_count += 1
                    continue
                
                # Update progress less frequently to avoid UI issues
                if i % 10 == 0:
                    progress.setValue(i + 1)
                    QApplication.processEvents()
            
            # Final progress update
            progress.setValue(len(entries))
            progress.close()
            
            # Add original video items with their extracted frames
            videos_added = 0
            for video_path, frame_paths in video_to_frames.items():
                try:
                    if Path(video_path).exists():
                        video_path_str = str(Path(video_path).resolve())
                        
                        # Create or get video item
                        if video_path_str not in self.workspace.items:
                            video_item = ImageItem(video_path_str, "video")
                            self.workspace.add_item(video_item)
                            
                            # Add parent directory
                            video_parent = str(Path(video_path_str).parent)
                            directories_to_add.add(video_parent)
                            
                            videos_added += 1
                        else:
                            video_item = self.workspace.items[video_path_str]
                        
                        # Link extracted frames to video
                        for frame_path in frame_paths:
                            frame_path_resolved = str(Path(frame_path).resolve())
                            if frame_path_resolved in self.workspace.items:
                                # Mark frame as extracted from this video
                                frame_item = self.workspace.items[frame_path_resolved]
                                frame_item.parent_video = video_path_str
                                frame_item.item_type = "extracted_frame"
                                
                                # Add frame to video's extracted_frames list
                                if frame_path_resolved not in video_item.extracted_frames:
                                    video_item.extracted_frames.append(frame_path_resolved)
                except Exception as e:
                    pass  # Skip videos that can't be found
            
            # Add all collected directories to workspace
            for directory in directories_to_add:
                if directory not in self.workspace.directory_paths:
                    self.workspace.add_directory(directory)
            
            # Re-enable updates and refresh view
            self.image_list.setUpdatesEnabled(True)
            
            try:
                self.refresh_view()
                self.update_window_title()
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                # Try a simpler refresh
                self.image_list.clear()
                QMessageBox.warning(
                    self,
                    "Display Warning",
                    f"Import completed but there was an error refreshing the display.\n"
                    f"Try closing and reopening the workspace.\n\n"
                    f"Error: {str(e)}\n\n"
                    f"Imported {imported_count} descriptions successfully."
                )
            
            # Show import summary
            summary = f"Import Complete!\n\n"
            summary += f"Imported: {imported_count} descriptions\n"
            if videos_added > 0:
                summary += f"Videos added: {videos_added}\n"
            if duplicate_count > 0:
                summary += f"Duplicates skipped: {duplicate_count}\n"
            if missing_file_count > 0:
                summary += f"Missing files: {missing_file_count}\n"
            if error_count > 0:
                summary += f"Parse errors: {error_count}\n"
            
            QMessageBox.information(self, "Workflow Import", summary)
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            self.image_list.setUpdatesEnabled(True)  # Re-enable updates on error
            QMessageBox.critical(
                self,
                "Import Error",
                f"Failed to import workflow:\n{str(e)}\n\nDetails:\n{error_details[:500]}"
            )
        finally:
            # Ensure updates are always re-enabled
            self.image_list.setUpdatesEnabled(True)
    
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
        # Check view mode and call appropriate refresh method
        if self.view_mode == "flat":
            self.refresh_flat_view()
        else:
            self.refresh_tree_view()
    
    def refresh_tree_view(self):
        """Refresh the image list in tree view mode (original view)"""
        self.image_list.clear()
        
        # Collect items to display
        items_to_display = []
        
        for file_path, item in self.workspace.items.items():
            # Skip extracted frames - they'll be shown as children
            if item.item_type == "extracted_frame":
                continue
            
            # Apply filter
            if self.filter_mode == "described" and not item.descriptions:
                continue
            elif self.filter_mode == "undescribed" and item.descriptions:
                continue
            elif self.filter_mode == "batch" and not item.batch_marked:
                continue
            elif self.filter_mode == "videos" and item.item_type != "video":
                continue
            elif self.filter_mode == "images" and item.item_type == "video":
                continue
            elif self.filter_mode == "processing" and file_path not in self.processing_items:
                continue
                
            items_to_display.append((file_path, item))
        
        # Sort items based on current sort order
        if self.sort_order == "filename":
            items_to_display.sort(key=lambda x: Path(x[0]).name.lower())
        elif self.sort_order == "date_oldest":
            # Sort by file modification time (oldest first)
            def get_file_date(file_path):
                try:
                    return Path(file_path).stat().st_mtime
                except:
                    return 0
            items_to_display.sort(key=lambda x: get_file_date(x[0]), reverse=False)
        elif self.sort_order == "date_newest":
            # Sort by file modification time (newest first)
            def get_file_date(file_path):
                try:
                    return Path(file_path).stat().st_mtime
                except:
                    return 0
            items_to_display.sort(key=lambda x: get_file_date(x[0]), reverse=True)
        
        # Add sorted and filtered items to the list
        for file_path, item in items_to_display:
            # Create top-level item - start with filename or custom name
            file_name = Path(file_path).name
            # Use custom display name if set, otherwise use filename
            base_name = item.display_name if item.display_name else file_name
            display_name = base_name
            
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
                # Get detailed status if available
                if file_path in self.processing_status:
                    status_msg = self.processing_status[file_path]
                    # Truncate long status messages for display
                    if len(status_msg) > 50:
                        status_msg = status_msg[:47] + "..."
                    prefix_parts.append(f"p [{status_msg}]")
                else:
                    prefix_parts.append("p")
                
            # 4. Video extraction status
            if item.item_type == "video" and item.extracted_frames:
                frame_count = len(item.extracted_frames)
                prefix_parts.append(f"E{frame_count}")
            
            # Combine prefix and display name
            if prefix_parts:
                prefix = "".join(prefix_parts)
                display_name = f"{prefix} {base_name}"
            
            # Create list item
            list_item = QListWidgetItem(display_name)
            list_item.setData(Qt.ItemDataRole.UserRole, file_path)
            
            # Set accessibility properties
            self.set_item_accessibility(list_item, file_path, display_name)
            
            # Mark batch items with accessible colors
            if item.batch_marked:
                # Use light blue background (#E3F2FD) which provides good contrast with black text
                list_item.setBackground(QColor(227, 242, 253))  # Light blue
            
            self.image_list.addItem(list_item)
            
            # Add extracted frames as children for videos (also sorted)
            if item.item_type == "video" and item.extracted_frames:
                frame_items = []
                
                for frame_path in item.extracted_frames:
                    frame_workspace_item = self.workspace.get_item(frame_path)
                    # Only add frames that exist in workspace
                    if frame_workspace_item:
                        frame_items.append((frame_path, frame_workspace_item))
                
                # Sort frames based on current sort order  
                if self.sort_order == "filename":
                    frame_items.sort(key=lambda x: Path(x[0]).name.lower())
                elif self.sort_order == "date":
                    def get_file_date(file_path):
                        try:
                            return Path(file_path).stat().st_mtime
                        except:
                            return 0
                    frame_items.sort(key=lambda x: get_file_date(x[0]), reverse=True)
                
                for frame_path, frame_workspace_item in frame_items:
                    frame_name = Path(frame_path).name
                    
                    # Build frame prefix indicators
                    frame_prefix_parts = []
                    
                    # Check if frame has descriptions
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
        
        # Add chat sessions to the list
        if hasattr(self.workspace, 'chat_sessions'):
            for chat_id, chat_session in self.workspace.chat_sessions.items():
                chat_name = chat_session.get('name', 'Chat Session')
                timestamp = chat_session.get('timestamp', '')
                conversation_count = len(chat_session.get('conversation', []))
                
                # Build chat display name with indicators
                display_name = f"Chat: {chat_name}"
                if conversation_count > 0:
                    display_name = f"c{conversation_count} {display_name}"
                
                # Create chat item
                chat_item = QListWidgetItem(display_name)
                chat_item.setData(Qt.ItemDataRole.UserRole, chat_id)
                chat_item.setData(Qt.ItemDataRole.UserRole + 1, "chat_session")  # Mark as chat
                chat_item.setToolTip(f"Chat session: {chat_name}\nProvider: {chat_session.get('provider', 'Unknown')}\nModel: {chat_session.get('model', 'Unknown')}\nMessages: {conversation_count}")
                
                # Set chat icon and styling
                chat_item.setForeground(QColor(0, 100, 200))  # Blue color for chats
                
                self.image_list.addItem(chat_item)
        
        self.update_batch_label()
        
        # Also refresh master-detail view if it's the current mode
        if self.navigation_mode == "master_detail":
            self.refresh_master_detail_view()
    
    def refresh_view_preserving_chat_selection(self, active_chat_id):
        """Refresh the image list view while preserving chat selection"""
        # Store current selection if it's a chat
        current_item = self.image_list.currentItem()
        current_chat_id = None
        if current_item and current_item.data(Qt.ItemDataRole.UserRole) == active_chat_id:
            current_chat_id = active_chat_id
        
        # Do the normal refresh
        self.refresh_view()
        
        # Restore chat selection if it was active
        if current_chat_id:
            try:
                for i in range(self.image_list.count()):
                    item = self.image_list.item(i)
                    if item and item.data(Qt.ItemDataRole.UserRole) == current_chat_id:
                        self.image_list.setCurrentItem(item)
                        break
            except Exception as e:
                print(f"Warning: Could not restore chat selection: {e}")
                # Fall back to regular refresh behavior
    
    def refresh_flat_view(self):
        """Refresh the image list in flat view mode - shows all descriptions in a single list"""
        self.image_list.clear()
        
        # Collect all items with their descriptions
        all_descriptions = []
        
        for file_path, item in self.workspace.items.items():
            # Skip extracted frames - they'll be shown with their descriptions
            if item.item_type == "extracted_frame":
                continue
            
            # Apply filter
            if self.filter_mode == "described" and not item.descriptions:
                continue
            elif self.filter_mode == "undescribed" and item.descriptions:
                continue
            elif self.filter_mode == "batch" and not item.batch_marked:
                continue
            elif self.filter_mode == "videos" and item.item_type != "video":
                continue
            elif self.filter_mode == "images" and item.item_type == "video":
                continue
            elif self.filter_mode == "processing" and file_path not in self.processing_items:
                continue
            
            # For items with descriptions, add each description
            if item.descriptions:
                for desc in item.descriptions:
                    all_descriptions.append({
                        'file_path': file_path,
                        'item': item,
                        'description': desc
                    })
            
            # For videos, also include descriptions from extracted frames
            if item.item_type == "video" and item.extracted_frames:
                for frame_path in item.extracted_frames:
                    frame_item = self.workspace.get_item(frame_path)
                    if frame_item and frame_item.descriptions:
                        for desc in frame_item.descriptions:
                            all_descriptions.append({
                                'file_path': frame_path,
                                'item': frame_item,
                                'description': desc
                            })
        
        # Sort descriptions based on file date or filename
        if self.sort_order == "filename":
            all_descriptions.sort(key=lambda x: Path(x['file_path']).name.lower())
        elif self.sort_order == "date_oldest":
            def get_file_date(file_path):
                try:
                    return Path(file_path).stat().st_mtime
                except:
                    return 0
            all_descriptions.sort(key=lambda x: get_file_date(x['file_path']), reverse=False)
        elif self.sort_order == "date_newest":
            def get_file_date(file_path):
                try:
                    return Path(file_path).stat().st_mtime
                except:
                    return 0
            all_descriptions.sort(key=lambda x: get_file_date(x['file_path']), reverse=True)
        
        # Add descriptions to the list
        for entry in all_descriptions:
            file_path = entry['file_path']
            item = entry['item']
            desc = entry['description']
            
            file_name = Path(file_path).name
            
            # Format: "Description text - filename"
            # Truncate very long descriptions for display
            desc_text = desc.text
            if len(desc_text) > 200:
                desc_text = desc_text[:197] + "..."
            
            display_name = f"{desc_text} - {file_name}"
            
            # Create list item
            list_item = QListWidgetItem(display_name)
            # Store both file path and description ID for retrieval
            list_item.setData(Qt.ItemDataRole.UserRole, file_path)
            list_item.setData(Qt.ItemDataRole.UserRole + 1, desc.id)  # Description ID
            
            # Build accessibility description
            accessibility_desc = f"Description: {desc_text}. Image: {file_name}"
            
            # Add model info if available
            if desc.model:
                accessibility_desc += f". Model: {desc.model}"
            
            list_item.setData(Qt.ItemDataRole.AccessibleDescriptionRole, accessibility_desc)
            list_item.setToolTip(f"File: {file_name}\nDescription: {desc.text}\nModel: {desc.model or 'Unknown'}\nPrompt: {desc.prompt_style or 'Unknown'}")
            
            # Mark batch items with accessible colors
            if item.batch_marked:
                list_item.setBackground(QColor(227, 242, 253))  # Light blue
            
            self.image_list.addItem(list_item)
        
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
        
        # Collect items to display
        items_to_display = []
        
        # Populate media list with videos and standalone images
        for file_path, item in self.workspace.items.items():
            # Skip extracted frames - they'll be shown in frames list
            if item.item_type == "extracted_frame":
                continue
                
            # Apply filter
            if self.filter_mode == "described" and not item.descriptions:
                continue
            elif self.filter_mode == "undescribed" and item.descriptions:
                continue
            elif self.filter_mode == "batch" and not item.batch_marked:
                continue
            elif self.filter_mode == "videos" and item.item_type != "video":
                continue
            elif self.filter_mode == "images" and item.item_type == "video":
                continue
            elif self.filter_mode == "processing" and file_path not in self.processing_items:
                continue
                
            items_to_display.append((file_path, item))
        
        # Sort items based on current sort order
        if self.sort_order == "filename":
            items_to_display.sort(key=lambda x: Path(x[0]).name.lower())
        elif self.sort_order == "date":
            # Sort by file modification time (most recent first)
            def get_file_date(file_path):
                try:
                    return Path(file_path).stat().st_mtime
                except:
                    return 0
            items_to_display.sort(key=lambda x: get_file_date(x[0]), reverse=True)
        
        # Add sorted and filtered items to the list
        for file_path, item in items_to_display:
            # Create list item
            file_name = Path(file_path).name
            # Use custom display name if set, otherwise use filename  
            base_name = item.display_name if item.display_name else file_name
            display_name = base_name
            accessibility_desc = base_name
            
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

    def rename_item(self):
        """Rename the currently selected item"""
        # Check if this is a chat session
        current_item = self.image_list.currentItem() if self.navigation_mode == "tree" else None
        if current_item:
            item_type = current_item.data(Qt.ItemDataRole.UserRole + 1)
            if item_type == "chat_session":
                # Handle chat session rename
                chat_id = current_item.data(Qt.ItemDataRole.UserRole)
                if not hasattr(self.workspace, 'chat_sessions') or chat_id not in self.workspace.chat_sessions:
                    QMessageBox.warning(self, "Rename", "Chat session not found.")
                    return
                
                chat_session = self.workspace.chat_sessions[chat_id]
                current_name = chat_session.get('name', 'Unnamed Chat')
                
                # Show rename dialog
                new_name, ok = QInputDialog.getText(
                    self, 
                    "Rename Chat Session", 
                    "Enter new chat name:",
                    text=current_name
                )
                
                if ok and new_name.strip():
                    # Update the chat session name
                    chat_session['name'] = new_name.strip()
                    
                    # Mark workspace as modified
                    self.workspace.modified = True
                    
                    # Refresh the current view to show the new name
                    self.refresh_current_view()
                    
                    self.statusBar().showMessage(f"Renamed chat to '{new_name.strip()}'", 3000)
                return
        
        # Handle regular image/file rename
        file_path = self.get_current_selected_file_path()
        if not file_path:
            QMessageBox.information(self, "Rename", "Please select an item to rename.")
            return
            
        item = self.workspace.get_item(file_path)
        if not item:
            QMessageBox.warning(self, "Rename", "Selected item not found in workspace.")
            return
        
        # Get current display name or filename
        current_name = item.display_name if item.display_name else Path(file_path).name
        
        # Show rename dialog
        new_name, ok = QInputDialog.getText(
            self, 
            "Rename Item", 
            "Enter new display name:\n(This only changes how the item appears in the workspace)",
            text=current_name
        )
        
        if ok and new_name.strip():
            # Update the display name
            item.display_name = new_name.strip()
            
            # Mark workspace as modified
            self.workspace.modified = True
            
            # Refresh the current view to show the new name
            self.refresh_current_view()
            
            self.statusBar().showMessage(f"Renamed item to '{new_name.strip()}'", 3000)

    def auto_rename_item(self):
        """Auto-rename the currently selected item using AI-generated caption (hidden feature)"""
        print("DEBUG: auto_rename_item called")
        file_path = self.get_current_selected_file_path()
        print(f"DEBUG: file_path = {file_path}")
        if not file_path:
            print("DEBUG: No file path, returning")
            return
            
        item = self.workspace.get_item(file_path)
        print(f"DEBUG: item = {item}")
        if not item:
            print("DEBUG: No item found, returning")
            return
        
        # Only work with image files
        if not self._is_image_file(file_path):
            print("DEBUG: Not an image file, returning")
            return
        
        print("DEBUG: All checks passed, proceeding with caption generation")
        
        # Store current selection and focus
        current_selection = self.image_list.currentRow()
        
        try:
            # Show brief status message
            self.statusBar().showMessage("Generating AI caption...", 0)
            print("DEBUG: Status message set")
            
            # Process events to show the status message
            QApplication.processEvents()
            
            # Generate short caption using fast model
            print("DEBUG: Calling _generate_short_caption")
            caption = self._generate_short_caption(file_path)
            print(f"DEBUG: Generated caption: '{caption}'")
            
            if caption:
                # Sanitize caption for use as display name
                sanitized_caption = self._sanitize_caption_for_display(caption)
                
                # Update the display name
                item.display_name = sanitized_caption
                
                # Mark workspace as modified
                self.workspace.modified = True
                
                # Refresh the current view to show the new name
                self.refresh_current_view()
                
                # Restore selection and focus
                if current_selection >= 0 and current_selection < self.image_list.count():
                    self.image_list.setCurrentRow(current_selection)
                    self.image_list.setFocus()
                
                self.statusBar().showMessage(f"Auto-renamed to: {sanitized_caption}", 3000)
            else:
                self.statusBar().showMessage("Failed to generate caption", 3000)
                
        except Exception as e:
            self.statusBar().showMessage(f"Error during auto-rename: {str(e)}", 3000)
            # Restore selection and focus even on error
            if current_selection >= 0 and current_selection < self.image_list.count():
                self.image_list.setCurrentRow(current_selection)
                self.image_list.setFocus()

    def _generate_short_caption(self, image_path: str) -> str:
        """Generate a short caption suitable for display name using fast AI model"""
        print(f"DEBUG: _generate_short_caption called with {image_path}")
        try:
            # Use microsoft/git-base-coco model for fast captioning
            model_name = "microsoft/git-base-coco"
            print(f"DEBUG: Using model {model_name}")
            
            # Check if HuggingFace provider is available and has the model
            print(f"DEBUG: HuggingFace available: {self.huggingface_provider.is_available()}")
            if not self.huggingface_provider.is_available():
                # Fallback to Ollama if HuggingFace not available
                if not self.ollama_provider.is_available():
                    return ""
                
                # Use a fast Ollama model as fallback
                available_models = self.ollama_provider.get_available_models()
                vision_models = [m for m in available_models if any(keyword in m.lower() for keyword in ['moondream', 'llava', 'phi', 'minicpm'])]
                if not vision_models:
                    return ""
                model_name = vision_models[0]
                
                # Create a prompt for short captioning
                prompt = "Describe this image in 3-5 words. Be concise and focus on the main subject."
                
                # Generate caption using Ollama
                caption = self.ollama_provider.describe_image(image_path, prompt, model_name)
            else:
                # Use HuggingFace microsoft/git-base-coco model
                available_models = self.huggingface_provider.get_available_models()
                if model_name not in available_models:
                    # Fallback to Ollama if microsoft/git-base-coco not available
                    if self.ollama_provider.is_available():
                        available_ollama_models = self.ollama_provider.get_available_models()
                        vision_models = [m for m in available_ollama_models if any(keyword in m.lower() for keyword in ['moondream', 'llava', 'phi', 'minicpm'])]
                        if vision_models:
                            prompt = "Describe this image in 3-5 words. Be concise and focus on the main subject."
                            caption = self.ollama_provider.describe_image(image_path, prompt, vision_models[0])
                        else:
                            return ""
                    else:
                        return ""
                else:
                    # Use the microsoft model with HuggingFace provider
                    # Use Narrative prompt style as requested
                    prompt = self.get_prompt_text("Narrative")
                    caption = self.huggingface_provider.describe_image(image_path, prompt, model_name)
            
            return caption.strip()
            
        except Exception as e:
            print(f"Error generating caption: {e}")
            return ""
    
    def _sanitize_caption_for_display(self, caption: str) -> str:
        """Sanitize AI-generated caption for use as display name"""
        if not caption:
            return "AI Caption"
        
        # Remove common AI response prefixes
        prefixes_to_remove = [
            "this image shows",
            "the image shows",
            "this is a",
            "this shows",
            "i can see",
            "the photo shows",
            "the picture shows",
            "here is",
            "this depicts",
            "the scene shows"
        ]
        
        caption_lower = caption.lower().strip()
        for prefix in prefixes_to_remove:
            if caption_lower.startswith(prefix):
                caption = caption[len(prefix):].strip()
                break
        
        # Remove punctuation from the end
        caption = caption.rstrip('.,!?;:')
        
        # Capitalize first letter
        if caption:
            caption = caption[0].upper() + caption[1:]
        
        # Limit length
        if len(caption) > 50:
            caption = caption[:47] + "..."
        
        return caption if caption else "AI Caption"

    def update_menu_states(self):
        """Update menu item states based on workspace state"""
        # Enable/disable Update from Workflow based on whether a workflow was imported
        if hasattr(self, 'update_workflow_action') and self.workspace:
            has_imported_workflow = bool(getattr(self.workspace, 'imported_workflow_dir', None))
            self.update_workflow_action.setEnabled(has_imported_workflow)

    def _is_image_file(self, file_path: str) -> bool:
        """Check if file is a supported image format"""
        ext = Path(file_path).suffix.lower()
        image_exts = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.heic', '.heif'}
        return ext in image_exts

    # Event handlers
    def on_image_selection_changed(self):
        """Handle image selection change"""
        current_item = self.image_list.currentItem()
        if current_item:
            # Check if this is a chat session
            item_type = current_item.data(Qt.ItemDataRole.UserRole + 1)
            
            # In flat view mode, the item contains both file_path and description_id
            if self.view_mode == "flat" and item_type and item_type != "chat_session":
                # This is a flat view item with a specific description
                file_path = current_item.data(Qt.ItemDataRole.UserRole)
                desc_id = item_type  # In flat view, UserRole+1 stores description ID
                
                # Clear description list and show just this description
                self.description_list.clear()
                
                # Find and display the specific description
                workspace_item = self.workspace.get_item(file_path)
                if workspace_item:
                    for desc in workspace_item.descriptions:
                        if desc.id == desc_id:
                            # Format text for better screen reader accessibility
                            formatted_text = self.format_description_for_accessibility(desc.text)
                            self.description_text.setPlainText(formatted_text)
                            
                            # Update accessibility description
                            char_count = len(desc.text)
                            preview = formatted_text[:200] + "..." if len(formatted_text) > 200 else formatted_text
                            self.description_text.setAccessibleDescription(
                                f"Image description with {char_count} characters from {desc.model}: {preview}"
                            )
                            break
            elif item_type == "chat_session":
                chat_id = current_item.data(Qt.ItemDataRole.UserRole)
                # Display chat conversation in the description area
                self.display_chat_conversation(chat_id)
            else:
                # Regular tree view - image file
                file_path = current_item.data(Qt.ItemDataRole.UserRole)
                self.load_descriptions_for_image(file_path)
        
        # Update image preview if enabled
        self.update_image_preview()
    
    def display_chat_conversation(self, chat_id: str):
        """Display chat conversation in the description area"""
        if not hasattr(self.workspace, 'chat_sessions') or chat_id not in self.workspace.chat_sessions:
            self.description_list.clear()
            self.description_text.setPlainText("Chat session not found.")
            return
        
        chat_session = self.workspace.chat_sessions[chat_id]
        
        # Clear description list and populate with conversation
        self.description_list.clear()
        
        for i, msg in enumerate(chat_session['conversation']):
            if msg['type'] == 'user':
                # Truncate long messages for the list view
                preview = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
                item_text = f"You: {preview}"
                full_text = f"You: {msg['content']} ({msg['timestamp']})"
            else:
                # Use short model name for better readability
                provider = msg.get('provider', 'AI')
                model = msg.get('model', 'Model')
                short_model = self.get_short_model_name(f"{provider}_{model}")
                
                # Truncate long messages for the list view
                preview = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
                item_text = f"{short_model}: {preview}"
                full_text = f"{short_model}: {msg['content']} ({msg['timestamp']})"
            
            list_item = QListWidgetItem(item_text)
            list_item.setData(Qt.ItemDataRole.UserRole, i)  # Store message index
            list_item.setData(Qt.ItemDataRole.UserRole + 1, full_text)  # Store full text
            list_item.setToolTip(full_text)
            
            # Color coding
            if msg['type'] == 'user':
                list_item.setForeground(QColor(0, 100, 0))  # Green for user
            else:
                list_item.setForeground(QColor(0, 0, 150))  # Blue for AI
            
            self.description_list.addItem(list_item)
        
        # If there are messages, select the last one
        if self.description_list.count() > 0:
            self.description_list.setCurrentRow(self.description_list.count() - 1)
    
    def on_description_selection_changed(self):
        """Handle description selection change"""
        current_item = self.description_list.currentItem()
        
        if current_item:
            # Check if we're in a chat session
            image_item = self.image_list.currentItem()
            if image_item and image_item.data(Qt.ItemDataRole.UserRole + 1) == "chat_session":
                # This is a chat message selection
                full_text = current_item.data(Qt.ItemDataRole.UserRole + 1)
                self.description_text.setPlainText(full_text)
                self.description_text.setAccessibleDescription(f"Chat message: {full_text[:200]}...")
                return
            
            # Regular description handling
            desc_id = current_item.data(Qt.ItemDataRole.UserRole)
            
            # Find the description
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
            provider, model, prompt_style, custom_prompt, detection_settings = dialog.get_selections()
            
            # Start processing (skip old verification logic for now)
            self.processing_items.add(file_path)  # Mark as processing
            self.update_window_title()  # Update title to show processing status
            worker = ProcessingWorker(file_path, provider, model, prompt_style, custom_prompt, detection_settings=detection_settings)
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
                # Handle both old dict format and new object format  
                if hasattr(models_response, 'models'):
                    # New format: models_response.models is a list of model objects
                    for model in models_response.models:
                        if hasattr(model, 'model'):
                            model_name = model.model
                        else:
                            model_name = getattr(model, 'name', '')
                        if model_name:
                            models.append(model_name)
                elif 'models' in models_response:
                    # Old dict format: models_response['models']
                    for model in models_response['models']:
                        model_name = model.get('model', model.get('name', ''))
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
    
    def process_batch(self):
        """Process all batch-marked images"""
        batch_items = [item for item in self.workspace.items.values() if item.batch_marked]
        
        if not batch_items:
            QMessageBox.information(self, "No Batch Items", "No images are marked for batch processing.")
            return
        
        # Show processing dialog first
        dialog = ProcessingDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            provider, model, prompt_style, custom_prompt, detection_settings = dialog.get_selections()
            
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
                
            worker = ProcessingWorker(item.file_path, provider, model, prompt_style, custom_prompt, detection_settings=detection_settings)
            worker.progress_updated.connect(self.on_processing_progress)
            worker.processing_complete.connect(self.on_batch_item_complete)
            worker.processing_failed.connect(self.on_batch_item_failed)
            
            self.processing_workers.append(worker)
            worker.start()
        
        # Refresh view to show processing indicators
        self.refresh_view()
        self.update_stop_button_state()
    
    def start_chat_session(self):
        """Start a new chat session with an AI model"""
        dialog = ChatDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            config = dialog.get_chat_config()
            self.create_chat_session_from_config(config)
    
    def create_chat_session_from_config(self, config):
        """Create and start a chat session from configuration"""
        if not config['initial_prompt']:
            QMessageBox.warning(self, "No Prompt", "Please enter an initial prompt to start the chat.")
            return
        
        # Create chat session
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Create descriptive session name with proper provider display
        provider_display = config['provider']
        if config['provider'] == 'ollama_cloud':
            provider_display = f"Ollama Cloud ({config['model']})"
        elif config['provider'] == 'ollama':
            provider_display = f"Ollama ({config['model']})"
        elif config['provider'] == 'openai':
            provider_display = f"OpenAI ({config['model']})"
        elif config['provider'] == 'huggingface':
            provider_display = f"HuggingFace ({config['model']})"
        else:
            provider_display = f"{config['provider'].upper()} ({config['model']})"
            
        session_name = config['session_name'] or f"{provider_display} Chat"
        
        # Create a unique chat ID
        chat_id = f"chat_{int(datetime.now().timestamp())}"
        
        # Create chat session data
        chat_session = {
            'id': chat_id,
            'name': session_name,
            'provider': config['provider'],
            'model': config['model'],
            'timestamp': timestamp,
            'conversation': [],
            'is_chat': True
        }
        
        # Add initial prompt to conversation
        chat_session['conversation'].append({
            'type': 'user',
            'content': config['initial_prompt'],
            'timestamp': timestamp
        })
        
        # Add to workspace chat sessions
        self.workspace.chat_sessions = getattr(self.workspace, 'chat_sessions', {})
        self.workspace.chat_sessions[chat_id] = chat_session
        self.workspace.mark_modified()
        
        # Refresh the view to show the new chat session in the list
        self.refresh_view()
        
        # Select the new chat session in the list
        for i in range(self.image_list.count()):
            item = self.image_list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == chat_id:
                self.image_list.setCurrentItem(item)
                break
        
        # Initialize chat windows dict if not exists
        if not hasattr(self, 'chat_windows'):
            self.chat_windows = {}
        
        # Create and show new chat window
        chat_window = ChatWindow(chat_session, self)
        chat_window.message_sent.connect(self.handle_chat_message)
        
        # Store the window reference
        self.chat_windows[chat_id] = chat_window
        
        # Clean up window reference when closed (but keep chat in image list)
        def cleanup_window():
            if chat_id in self.chat_windows:
                del self.chat_windows[chat_id]
        chat_window.finished.connect(cleanup_window)
        
        # Show the window
        chat_window.show()
        
        # Start processing the initial prompt
        self.process_chat_message(chat_id, config['initial_prompt'])
    
    def handle_chat_message(self, chat_id, message):
        """Handle a message sent from a chat window"""
        try:
            if not hasattr(self.workspace, 'chat_sessions') or chat_id not in self.workspace.chat_sessions:
                print(f"Warning: Chat session {chat_id} not found")
                return
            
            # Add user message to conversation
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            chat_session = self.workspace.chat_sessions[chat_id]
            
            chat_session['conversation'].append({
                'type': 'user',
                'content': message,
                'timestamp': timestamp
            })
            
            self.workspace.mark_modified()
            
            # Auto-save the workspace to persist chat history
            if self.current_workspace_file:
                try:
                    self.save_workspace_to_file(self.current_workspace_file)
                    # Refresh the view to update conversation count, but preserve chat selection
                    try:
                        self.refresh_view_preserving_chat_selection(chat_id)
                    except Exception as e:
                        print(f"Warning: Chat selection preservation failed: {e}")
                        self.refresh_view()
                except Exception as e:
                    print(f"Warning: Failed to save workspace during chat: {e}")
                    # Continue anyway - don't block the chat
            else:
                # If no workspace file is set, prompt user to save or create auto-save
                try:
                    self.ensure_workspace_saved_for_chat()
                except Exception as e:
                    print(f"Warning: Failed to ensure workspace saved: {e}")
                    # Continue anyway - don't block the chat
            
            # Process the message
            self.process_chat_message(chat_id, message)
            
        except Exception as e:
            print(f"Error in handle_chat_message: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Chat Error", f"An error occurred while processing your message:\n{str(e)}")
    
    def open_existing_chat_session(self, chat_id):
        """Open an existing chat session in a new window"""
        if not hasattr(self.workspace, 'chat_sessions') or chat_id not in self.workspace.chat_sessions:
            QMessageBox.warning(self, "Chat Error", "Chat session not found.")
            return
        
        # Check if window is already open
        if hasattr(self, 'chat_windows') and chat_id in self.chat_windows:
            # Bring existing window to front
            self.chat_windows[chat_id].raise_()
            self.chat_windows[chat_id].activateWindow()
            return
        
        # Initialize chat windows dict if not exists
        if not hasattr(self, 'chat_windows'):
            self.chat_windows = {}
        
        # Get chat session data
        chat_session = self.workspace.chat_sessions[chat_id]
        
        # Create and show chat window
        chat_window = ChatWindow(chat_session, self)
        chat_window.message_sent.connect(self.handle_chat_message)
        
        # Store the window reference
        self.chat_windows[chat_id] = chat_window
        
        # Clean up window reference when closed
        def cleanup_window():
            if chat_id in self.chat_windows:
                del self.chat_windows[chat_id]
        chat_window.finished.connect(cleanup_window)
        
        # Show the window
        chat_window.show()
        
        # Select the chat in the image list so user knows which chat is active
        for i in range(self.image_list.count()):
            item = self.image_list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == chat_id:
                self.image_list.setCurrentItem(item)
                break
    
    def view_chat_sessions(self):
        """Show a dialog to view and reopen existing chat sessions"""
        if not hasattr(self.workspace, 'chat_sessions') or not self.workspace.chat_sessions:
            QMessageBox.information(self, "No Chat Sessions", "No chat sessions found in the current workspace.")
            return
        
        # Create dialog to show chat sessions
        dialog = QDialog(self)
        dialog.setWindowTitle("Chat Sessions")
        dialog.setModal(True)
        dialog.resize(600, 400)
        
        layout = QVBoxLayout(dialog)
        
        # Header
        header_label = QLabel("Select a chat session to open:")
        header_label.setStyleSheet("font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(header_label)
        
        # Chat sessions list
        sessions_list = QListWidget()
        sessions_list.setAccessibleName("Chat Sessions List")
        sessions_list.setAccessibleDescription("List of available chat sessions. Double-click or press Enter to open.")
        
        # Populate with chat sessions
        for chat_id, session in self.workspace.chat_sessions.items():
            display_text = f"{session['name']} ({session['timestamp']})"
            short_model = self.get_short_model_name(session['model'])
            provider_info = f"{session['provider'].upper()} {short_model}"
            msg_count = len(session.get('conversation', []))
            tooltip = f"Session: {session['name']}\nProvider: {provider_info}\nMessages: {msg_count}\nCreated: {session['timestamp']}"
            
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, chat_id)
            item.setToolTip(tooltip)
            
            # Add status indicator if window is already open
            if hasattr(self, 'chat_windows') and chat_id in self.chat_windows:
                item.setText(display_text + " (Already Open)")
                item.setForeground(QColor(0, 150, 0))  # Green for open sessions
            
            sessions_list.addItem(item)
        
        layout.addWidget(sessions_list)
        
        # Info label
        info_label = QLabel("Double-click a session to open it, or use the buttons below.")
        info_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(info_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        open_button = QPushButton("Open Session")
        open_button.setAccessibleName("Open Chat Session")
        open_button.setAccessibleDescription("Open the selected chat session")
        open_button.setDefault(True)
        
        close_button = QPushButton("Close")
        close_button.setAccessibleName("Close Dialog")
        
        button_layout.addWidget(open_button)
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        
        # Connect signals
        def open_selected_session():
            current_item = sessions_list.currentItem()
            if current_item:
                chat_id = current_item.data(Qt.ItemDataRole.UserRole)
                self.open_existing_chat_session(chat_id)
                dialog.accept()
        
        open_button.clicked.connect(open_selected_session)
        close_button.clicked.connect(dialog.reject)
        sessions_list.itemDoubleClicked.connect(lambda: open_selected_session())
        
        # Handle Enter key
        def handle_enter(event):
            if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
                open_selected_session()
            else:
                QListWidget.keyPressEvent(sessions_list, event)
        
        sessions_list.keyPressEvent = handle_enter
        
        # Select first item if any
        if sessions_list.count() > 0:
            sessions_list.setCurrentRow(0)
            sessions_list.setFocus()
        
        dialog.exec()
    
    def process_chat_message(self, chat_id, message):
        """Process a chat message and get AI response"""
        try:
            if not hasattr(self.workspace, 'chat_sessions') or chat_id not in self.workspace.chat_sessions:
                QMessageBox.warning(self, "Chat Error", "Chat session not found.")
                return
            
            chat_session = self.workspace.chat_sessions[chat_id]
            
            # Set context image if an image is currently selected in the workspace
            # This allows detection queries to reference the selected image
            current_item = self.image_list.currentItem()
            if current_item:
                file_path = current_item.data(Qt.ItemDataRole.UserRole)
                workspace_item = self.workspace.get_item(file_path)
                # Only set context if it's an actual image (not a chat or video)
                if workspace_item and workspace_item.item_type == "image":
                    chat_session['context_image'] = file_path
                elif 'context_image' in chat_session:
                    # Clear stale context if no image is selected
                    del chat_session['context_image']
            
            # Initialize chat workers list if not exists
            if not hasattr(self, 'chat_workers'):
                self.chat_workers = []
            
            # Start processing worker for chat
            worker = ChatProcessingWorker(chat_session, message)
            worker.chat_response.connect(self.on_chat_response)
            worker.chat_failed.connect(self.on_chat_failed)
            worker.finished.connect(lambda: self.cleanup_chat_worker(worker))
            
            # Track the worker to prevent premature destruction
            self.chat_workers.append(worker)
            worker.start()
            
            # Show processing indicator
            self.show_chat_processing(chat_id)
            
        except Exception as e:
            print(f"Error in process_chat_message: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Chat Processing Error", f"Failed to process chat message:\n{str(e)}")
    
    def cleanup_chat_worker(self, worker):
        """Clean up finished chat worker"""
        if hasattr(self, 'chat_workers') and worker in self.chat_workers:
            self.chat_workers.remove(worker)
            worker.deleteLater()
    
    def on_chat_response(self, chat_id, response):
        """Handle chat response from AI"""
        if not hasattr(self.workspace, 'chat_sessions') or chat_id not in self.workspace.chat_sessions:
            return
        
        chat_session = self.workspace.chat_sessions[chat_id]
        
        # Add AI response to conversation
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        chat_session['conversation'].append({
            'type': 'assistant',
            'content': response,
            'timestamp': timestamp,
            'provider': chat_session['provider'],
            'model': chat_session['model']
        })
        
        self.workspace.mark_modified()
        
        # Auto-save the workspace to persist chat history
        if self.current_workspace_file:
            self.save_workspace_to_file(self.current_workspace_file)
            # Refresh the view to update conversation count
            self.refresh_view()
        else:
            # If no workspace file is set, prompt user to save or create auto-save
            self.ensure_workspace_saved_for_chat()
        
        # Update the chat window if it's open
        if hasattr(self, 'chat_windows') and chat_id in self.chat_windows:
            chat_window = self.chat_windows[chat_id]
            # Add the AI response to the window display
            chat_window.add_message_to_display(
                'assistant', 
                response, 
                timestamp, 
                chat_session['provider'], 
                chat_session['model']
            )
        
        # Hide processing indicator (this might not be needed anymore but keeping for compatibility)
        self.hide_chat_processing(chat_id)
    
    def on_chat_failed(self, chat_id, error):
        """Handle chat processing failure"""
        # Show error in chat window if it's open
        if hasattr(self, 'chat_windows') and chat_id in self.chat_windows:
            chat_window = self.chat_windows[chat_id]
            # Add error message to the chat window
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            chat_window.add_message_to_display(
                'assistant', 
                f"Error: {error}", 
                timestamp, 
                "System", 
                "Error"
            )
        else:
            # Fallback to message box if window is not open
            QMessageBox.warning(self, "Chat Error", f"Failed to get response: {error}")
        
        self.hide_chat_processing(chat_id)
    
    def show_chat_processing(self, chat_id):
        """Show processing indicator for chat"""
        # Find the chat item in the list and add processing indicator
        for i in range(self.image_list.count()):
            item = self.image_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == chat_id:
                original_text = item.text()
                if not original_text.endswith(" (processing...)"):
                    item.setText(original_text + " (processing...)")
                break
    
    def hide_chat_processing(self, chat_id):
        """Hide processing indicator for chat"""
        for i in range(self.image_list.count()):
            item = self.image_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == chat_id:
                original_text = item.text()
                if original_text.endswith(" (processing...)"):
                    item.setText(original_text.replace(" (processing...)", ""))
                break
    
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
                        prompt_style="manual",
                        provider="manual"
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
    
    def build_followup_context_prompt(self, workspace_item, selected_desc, follow_up_question):
        """Build a context-aware prompt for follow-up questions that includes previous Q&As"""
        # Get all descriptions for this image, sorted by creation time
        all_descriptions = sorted(workspace_item.descriptions, key=lambda d: d.created)
        
        # Find the index of the selected description
        selected_index = -1
        for i, desc in enumerate(all_descriptions):
            if desc.id == selected_desc.id:
                selected_index = i
                break
        
        if selected_index == -1:
            # Fallback to simple prompt if we can't find the description
            return f"""Here is the original description of this image:
"{selected_desc.text}"

Follow-up question: {follow_up_question}

Please answer the follow-up question about this image, taking into account the context from the original description."""
        
        # Build context with original description and relevant follow-ups
        context_parts = []
        context_parts.append("Here is the conversation history about this image:")
        context_parts.append("")
        
        # Add the original description
        context_parts.append(f"Original description ({selected_desc.model}):")
        context_parts.append(f'"{selected_desc.text}"')
        context_parts.append("")
        
        # Add any follow-up Q&As that came after the selected description
        follow_ups_found = 0
        for desc in all_descriptions[selected_index + 1:]:
            if desc.prompt_style == "follow-up" and desc.custom_prompt:
                # Extract the question from the custom prompt
                if "Follow-up question:" in desc.custom_prompt:
                    question_part = desc.custom_prompt.split("Follow-up question:")[1].split("\n")[0].strip()
                    context_parts.append(f"Follow-up question: {question_part}")
                    context_parts.append(f"Answer ({desc.model}): {desc.text}")
                    context_parts.append("")
                    follow_ups_found += 1
                    # Limit context to avoid token bloat
                    if follow_ups_found >= 3:  # Include up to 3 previous follow-ups
                        break
        
        # Add current question
        context_parts.append(f"New follow-up question: {follow_up_question}")
        context_parts.append("")
        context_parts.append("IMPORTANT: Please examine the image directly to answer this new question. Use the conversation history above only as context, but focus on what you can actually see in the image to provide specific, detailed information based on your direct visual analysis.")
        
        return "\n".join(context_parts)
    
    def ask_followup_question(self):
        """Ask a follow-up question - show selection dialog to choose what to follow up on"""
        # Check if there are any items or chats to follow up on
        available_items = []
        
        # Add chat sessions
        if hasattr(self.workspace, 'chat_sessions'):
            for chat_id, chat_session in self.workspace.chat_sessions.items():
                chat_name = chat_session.get('name', 'Chat Session')
                conversation_count = len(chat_session.get('conversation', []))
                available_items.append({
                    'type': 'chat',
                    'id': chat_id,
                    'name': f"Chat: {chat_name} ({conversation_count} messages)",
                    'data': chat_session
                })
        
        # Add images with descriptions
        for file_path, item in self.workspace.items.items():
            if item.descriptions:  # Only items with descriptions
                item_name = item.display_name if item.display_name else Path(file_path).name
                desc_count = len(item.descriptions)
                available_items.append({
                    'type': 'image',
                    'id': file_path,
                    'name': f"Image: {item_name} ({desc_count} descriptions)",
                    'data': item
                })
        
        if not available_items:
            QMessageBox.information(
                self, "No Items Available",
                "No chat sessions or described images available for follow-up questions.\n\n"
                "Create a chat session or add descriptions to images first."
            )
            return
        
        # Show selection dialog
        self.show_followup_selection_dialog(available_items)

    def show_followup_selection_dialog(self, available_items):
        """Show dialog to select what to ask a follow-up question about"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Ask Follow-up Question")
        dialog.setModal(True)
        dialog.resize(500, 400)
        
        layout = QVBoxLayout(dialog)
        
        # Header
        header_label = QLabel("Select what you want to ask a follow-up question about:")
        header_label.setStyleSheet("font-weight: bold; font-size: 12px; padding: 10px;")
        layout.addWidget(header_label)
        
        # Selection list
        selection_list = QListWidget()
        selection_list.setAccessibleName("Follow-up Items")
        selection_list.setAccessibleDescription("List of available chats and images to ask follow-up questions about")
        
        for item in available_items:
            list_item = QListWidgetItem(item['name'])
            list_item.setData(Qt.ItemDataRole.UserRole, item)
            selection_list.addItem(list_item)
        
        # Set selection mode and select first item by default
        selection_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        if available_items:
            selection_list.setCurrentRow(0)
        
        layout.addWidget(selection_list)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        # Set tab order
        dialog.setTabOrder(selection_list, button_box)
        
        # Show dialog and process selection
        if dialog.exec() == QDialog.DialogCode.Accepted:
            current_item = selection_list.currentItem()
            if current_item:
                selected_item = current_item.data(Qt.ItemDataRole.UserRole)
                self.handle_followup_selection(selected_item)
            else:
                QMessageBox.information(self, "No Selection", "Please select an item to ask a follow-up question about.")

    def handle_followup_selection(self, selected_item):
        """Handle the selected item for follow-up question"""
        if selected_item['type'] == 'chat':
            # For chat sessions, open the chat window to continue the conversation
            chat_id = selected_item['id']
            self.open_existing_chat_session(chat_id)
        elif selected_item['type'] == 'image':
            # For images, show follow-up dialog that adds to existing descriptions
            file_path = selected_item['id']
            workspace_item = selected_item['data']
            self.show_image_followup_dialog(file_path, workspace_item)
    
    def show_image_followup_dialog(self, file_path: str, workspace_item):
        """Show dialog for asking follow-up questions about an image"""
        # Filter AI-generated descriptions only
        ai_descriptions = [desc for desc in workspace_item.descriptions if desc.model != "manual"] if workspace_item.descriptions else []
        
        if not ai_descriptions:
            QMessageBox.information(
                self, "No AI Descriptions Found",
                "This image has no AI-generated descriptions. Please add a description first before asking follow-up questions."
            )
            return
        
        # Create follow-up dialog
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Ask Follow-up Question - {Path(file_path).name}")
        dialog.setModal(True)
        dialog.resize(600, 400)
        
        layout = QVBoxLayout(dialog)
        
        # Header
        header_label = QLabel(f"Ask a follow-up question about {Path(file_path).name}")
        header_label.setStyleSheet("font-weight: bold; font-size: 12px; padding: 10px;")
        layout.addWidget(header_label)
        
        # Show recent descriptions for context
        context_label = QLabel("Recent descriptions (for context):")
        layout.addWidget(context_label)
        
        # Context display (recent descriptions)
        context_display = QTextEdit()
        context_display.setReadOnly(True)
        context_display.setMaximumHeight(120)
        context_display.setAccessibleName("Recent Descriptions")
        context_display.setAccessibleDescription("Recent AI descriptions of this image for context")
        
        # Show last 2-3 descriptions for context
        recent_descriptions = sorted(ai_descriptions, key=lambda d: d.created)[-3:]
        context_text = []
        for desc in recent_descriptions:
            short_model = self.get_short_model_name(desc.model)
            context_text.append(f"• {short_model}: {desc.text[:200]}{'...' if len(desc.text) > 200 else ''}")
        
        context_display.setPlainText("\n\n".join(context_text))
        layout.addWidget(context_display)
        
        # Provider/Model selection (use latest description's settings as default)
        latest_desc = sorted(ai_descriptions, key=lambda d: d.created)[-1]  # Get most recent
        
        provider_label = QLabel("AI Provider:")
        layout.addWidget(provider_label)
        provider_combo = QComboBox()
        
        # Populate provider combo
        all_providers = {
            'ollama': _ollama_provider,
            'ollama_cloud': _ollama_cloud_provider,
            'openai': _openai_provider,
            'claude': _claude_provider,
            'onnx': _onnx_provider,
            'copilot': _copilot_provider,
            'object_detection': _object_detection_provider
        }
        
        for provider_key, provider in all_providers.items():
            display_name = provider.get_provider_name()
            if not provider.is_available():
                display_name += " (Not Available)"
            provider_combo.addItem(display_name, provider_key)
        
        # Set to latest description's provider
        provider_index = provider_combo.findData(latest_desc.provider or "ollama")
        if provider_index >= 0:
            provider_combo.setCurrentIndex(provider_index)
        layout.addWidget(provider_combo)
        
        model_label = QLabel("AI Model:")
        layout.addWidget(model_label)
        model_combo = QComboBox()
        
        # Populate model combo for current provider
        def populate_models_for_provider(provider_key):
            model_combo.clear()
            if provider_key in all_providers:
                provider = all_providers[provider_key]
                if provider.is_available():
                    try:
                        models = provider.get_available_models()
                        for model in models:
                            model_combo.addItem(model)
                    except Exception as e:
                        model_combo.addItem("Error loading models")
                else:
                    model_combo.addItem("Provider not available")
        
        # Initial model population
        current_provider = provider_combo.currentData() or "ollama"
        populate_models_for_provider(current_provider)
        
        # Set to latest description's model
        model_index = model_combo.findText(latest_desc.model)
        if model_index >= 0:
            model_combo.setCurrentIndex(model_index)
        layout.addWidget(model_combo)
        
        # Connect provider change to update models
        provider_combo.currentTextChanged.connect(lambda: populate_models_for_provider(provider_combo.currentData()))
        
        # Follow-up question
        question_label = QLabel("Your follow-up question:")
        layout.addWidget(question_label)
        
        question_edit = AccessibleTextEdit()
        question_edit.setAccessibleName("Follow-up Question")
        question_edit.setAccessibleDescription("Enter your follow-up question about this image")
        question_edit.setPlaceholderText("e.g., What colors are most prominent? Can you describe the lighting? What mood does this convey?")
        question_edit.setMaximumHeight(80)
        layout.addWidget(question_edit)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        # Set tab order
        dialog.setTabOrder(context_display, provider_combo)
        dialog.setTabOrder(provider_combo, model_combo)
        dialog.setTabOrder(model_combo, question_edit)
        dialog.setTabOrder(question_edit, button_box)
        
        # Show dialog and process if accepted
        if dialog.exec() == QDialog.DialogCode.Accepted:
            follow_up_question = question_edit.toPlainText().strip()
            
            if not follow_up_question:
                QMessageBox.information(self, "Empty Question", "Please enter a follow-up question.")
                return
            
            selected_provider = provider_combo.currentData() or "ollama"
            selected_model = model_combo.currentText()
            
            # Create context-aware prompt using existing method
            custom_prompt = self.build_followup_context_prompt(workspace_item, latest_desc, follow_up_question)
            
            # Debug output for follow-up
            print("=== IMAGE FOLLOW-UP DEBUG ===")
            print(f"Image path: {file_path}")
            print(f"Provider: {selected_provider}")
            print(f"Model: {selected_model}")
            print(f"Follow-up question: {follow_up_question}")
            print(f"Custom prompt length: {len(custom_prompt)} characters")
            print(f"Custom prompt preview: {custom_prompt[:200]}...")
            print("============================")
            
            # Process as a follow-up description (gets added to image descriptions)
            self.processing_items.add(file_path)
            self.update_window_title()
            
            worker = ProcessingWorker(file_path, selected_provider, selected_model, "follow-up", custom_prompt)
            worker.progress_updated.connect(self.on_processing_progress)
            worker.processing_complete.connect(self.on_processing_complete)
            worker.processing_failed.connect(self.on_processing_failed)
            
            self.processing_workers.append(worker)
            worker.start()
            self.update_stop_button_state()
            
            # Refresh view to show processing indicator
            self.refresh_view()
            
            self.status_bar.showMessage(f"Processing follow-up question with {selected_model}...", 3000)
    
    def start_image_chat_session(self, file_path: str, workspace_item):
        """Start a new chat session focused on an image"""
        # Get the best description to use as context (prefer AI-generated)
        descriptions = workspace_item.descriptions if workspace_item.descriptions else []
        ai_descriptions = [desc for desc in descriptions if desc.model != "manual"]
        
        # Build initial context about the image
        image_name = Path(file_path).name
        context_parts = [f"I'd like to ask questions about the image '{image_name}'."]
        
        if ai_descriptions:
            # Use the most recent AI description as context
            latest_desc = max(ai_descriptions, key=lambda d: d.created)
            context_parts.append(f"Here's what I know about this image: {latest_desc.text}")
            context_parts.append("What would you like to know about this image?")
            
            # Use the same provider/model as the latest description
            provider = latest_desc.provider or "ollama"
            model = latest_desc.model
        else:
            context_parts.append("What would you like to know about this image?")
            # Default to Ollama if no previous descriptions
            provider = "ollama"
            model = "llama3.2-vision"  # Good default for image Q&A
        
        initial_prompt = "\n".join(context_parts)
        
        # Create chat dialog with pre-filled context
        dialog = ChatDialog(self)
        dialog.set_provider_model(provider, model)
        dialog.set_initial_prompt(initial_prompt)
        dialog.set_session_name(f"Questions about {image_name}")
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Start the chat session normally
            config = dialog.get_chat_config()
            self.create_chat_session_from_config(config)
    
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
        self.filter_undescribed_action.setChecked(mode == "undescribed")
        self.filter_batch_action.setChecked(mode == "batch")
        self.filter_videos_action.setChecked(mode == "videos")
        self.filter_images_action.setChecked(mode == "images")
        self.filter_processing_action.setChecked(mode == "processing")
        
        # Refresh the view with filter applied
        self.refresh_view()
        
        # Update window title to show current filter
        self.update_window_title()

    def set_sort_order(self, order: str):
        """Set the sort order and refresh view"""
        self.sort_order = order
        
        # Update checkable actions
        self.sort_filename_action.setChecked(order == "filename")
        self.sort_date_oldest_action.setChecked(order == "date_oldest")
        self.sort_date_newest_action.setChecked(order == "date_newest")
        
        # Refresh the view with new sort order applied
        self.refresh_view()
        
        # Show temporary status message
        order_display = order.replace("_", " ").title()
        self.status_bar.showMessage(f"Sorted by {order_display}", 2000)

    def set_view_mode(self, mode: str):
        """Set the view mode (tree or flat) and refresh view"""
        self.view_mode = mode
        
        # Update checkable actions
        self.view_mode_tree_action.setChecked(mode == "tree")
        self.view_mode_flat_action.setChecked(mode == "flat")
        
        # Refresh the view with new mode applied
        self.refresh_view()
        
        # Show temporary status message
        mode_display = "Image Tree" if mode == "tree" else "Flat Image List"
        self.status_bar.showMessage(f"View mode: {mode_display}", 2000)

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
        
        provider, model, prompt_style, custom_prompt, yolo_settings = dialog.get_selections()
        
        # Optional verification
        if not getattr(self, '_skip_verification', True):
            if not self.check_ollama_status():
                return
            if not self.verify_model_available(model):
                return
        
        # Start comprehensive processing
        self._start_comprehensive_processing(provider, model, prompt_style, custom_prompt)
    
    def _start_comprehensive_processing(self, provider, model, prompt_style, custom_prompt):
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
            if getattr(sys, 'frozen', False):
                workflow_path = Path(sys._MEIPASS) / "scripts" / "workflow.py"
            else:
                workflow_path = Path(__file__).parent.parent / "scripts" / "workflow.py"
            
            cmd = [
                sys.executable, 
                str(workflow_path),
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
    
    def _process_images_with_live_updates(self, image_paths, provider, model, prompt_style, custom_prompt):
        """Process images with live updates like the viewer app"""
        if not image_paths:
            return
        
        # Set up live processing with immediate UI updates
        self.processing_items.update(image_paths)
        self.refresh_view()  # Show processing indicators immediately
        
        # Start processing first image
        self._current_process_all_queue = image_paths.copy()
        self._current_process_all_provider = provider
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
            self._current_process_all_provider,
            self._current_process_all_model, 
            self._current_process_all_prompt, 
            self._current_process_all_custom
        )
        
        # Connect signals for live updates
        worker.processing_complete.connect(lambda fp, desc, provider, model, prompt, custom: self._on_process_all_item_complete(fp, desc, provider, model, prompt, custom))
        worker.processing_failed.connect(lambda fp, error: self._on_process_all_item_failed(fp, error))
        
        # Store reference and start
        self.workers.append(worker)
        worker.start()
    
    def _on_process_all_item_complete(self, file_path, description, provider, model, prompt_style, custom_prompt):
        """Handle completion of single item in Process All - with live updates"""
        # Add description to workspace
        workspace_item = self.workspace.get_item(file_path)
        if workspace_item:
            desc = ImageDescription(description, model, prompt_style, custom_prompt=custom_prompt, provider=provider)
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
    
    def _process_all_images_live(self, provider, model, prompt_style, custom_prompt):
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
            worker = ProcessingWorker(item.file_path, provider, model, prompt_style, custom_prompt)
            worker.progress_updated.connect(self.on_processing_progress)
            worker.processing_complete.connect(self._on_live_processing_complete)
            worker.processing_failed.connect(self._on_live_processing_failed)
            
            self.processing_workers.append(worker)
            worker.start()
        
        self.update_stop_button_state()
    
    def _on_live_processing_complete(self, file_path: str, description: str, provider: str, model: str, prompt_style: str, custom_prompt: str):
        """Handle processing completion with live updates"""
        # Call the regular completion handler
        self.on_processing_complete(file_path, description, provider, model, prompt_style, custom_prompt)
        
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
    
    def get_display_name(self, item, file_path: str) -> str:
        """Generate display name for an item with all prefixes"""
        file_name = os.path.basename(file_path)
        
        # Use custom display name if set, otherwise use filename
        base_name = item.display_name if item.display_name else file_name
        display_name = base_name
        
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
            # Get detailed status if available
            if file_path in self.processing_status:
                status_msg = self.processing_status[file_path]
                # Truncate long status messages for visual display only
                if len(status_msg) > 50:
                    status_msg = status_msg[:47] + "..."
                prefix_parts.append(f"p [{status_msg}]")
            else:
                prefix_parts.append("p")
            
        # 4. Video extraction status
        if item.item_type == "video" and item.extracted_frames:
            frame_count = len(item.extracted_frames)
            prefix_parts.append(f"E{frame_count}")
        
        # Combine prefix and display name
        if prefix_parts:
            prefix = "".join(prefix_parts)
            display_name = f"{prefix} {base_name}"
            
        return display_name
    
    def set_item_accessibility(self, list_item, file_path: str, display_name: str):
        """Set accessibility properties for a list item"""
        # Set basic accessible name
        list_item.setData(Qt.ItemDataRole.AccessibleTextRole, display_name)
        
        # If item is processing, provide full status message for screen readers
        if file_path in self.processing_status:
            full_status = self.processing_status[file_path]
            # Create accessible description with full status
            accessible_name = display_name
            if "p [" in display_name and "..." in display_name:
                # Replace truncated status with full status for accessibility
                accessible_name = display_name.replace(
                    f"p [{full_status[:47]}...]" if len(full_status) > 50 else f"p [{full_status}]",
                    f"processing: {full_status}"
                )
            # Set tooltip and accessible description
            list_item.setToolTip(f"Status: {full_status}")
            list_item.setData(Qt.ItemDataRole.AccessibleDescriptionRole, accessible_name)
    
    def update_specific_item_display(self, file_path: str):
        """Update display text for a specific item without losing focus"""
        # Find the item in the current list
        for i in range(self.image_list.count()):
            item = self.image_list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == file_path:
                # Get the workspace item to rebuild the display name
                workspace_item = self.workspace.get_item(file_path)
                if workspace_item:
                    display_name = self.get_display_name(workspace_item, file_path)
                    item.setText(display_name)
                    # Set accessibility properties with full status
                    self.set_item_accessibility(item, file_path, display_name)
                break
    
    # Worker event handlers
    def on_processing_progress(self, *args):
        """Handle processing progress updates - supports both (file_path, message) and (message) formats"""
        if len(args) == 2:
            # New format: file_path, message
            file_path, message = args
            self.status_bar.showMessage(message)
            
            # Store the detailed status for this file
            self.processing_status[file_path] = message
            
            # Update only the specific item without losing focus
            self.update_specific_item_display(file_path)
        else:
            # Old format: just message (for workflow, conversion, etc.)
            message = args[0]
            self.status_bar.showMessage(message)
    
    def on_processing_complete(self, file_path: str, description: str, provider: str, model: str, prompt_style: str, custom_prompt: str):
        """Handle successful processing completion"""
        # Remove from processing set and status
        self.processing_items.discard(file_path)
        self.processing_status.pop(file_path, None)  # Remove status entry
        
        workspace_item = self.workspace.get_item(file_path)
        if not workspace_item:
            workspace_item = ImageItem(file_path)
            self.workspace.add_item(workspace_item)
        
        # Add the new description
        desc = ImageDescription(description, model, prompt_style, custom_prompt=custom_prompt, provider=provider)
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
        
        # Remove from processing set and status
        self.processing_items.discard(file_path)
        self.processing_status.pop(file_path, None)  # Remove status entry
        
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

    def on_batch_item_complete(self, file_path: str, description: str, provider: str, model: str, prompt_style: str, custom_prompt: str):
        """Handle batch item completion"""
        # Call the regular completion handler first
        self.on_processing_complete(file_path, description, provider, model, prompt_style, custom_prompt)
        
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
        provider = processing_config.get("provider", "ollama")  # Default to ollama for backward compatibility
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
            worker = ProcessingWorker(frame_path, provider, model, prompt_style, custom_prompt)
            
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

    def open_readme(self):
        """Open the GitHub README file for the imagedescriber directory"""
        try:
            # Determine the current branch dynamically
            try:
                # Try to get current branch from git
                result = subprocess.run(
                    ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                    capture_output=True,
                    text=True,
                    cwd=Path(__file__).parent.parent  # Go to repo root
                )
                if result.returncode == 0:
                    current_branch = result.stdout.strip()
                else:
                    current_branch = "main"  # fallback
            except:
                current_branch = "main"  # fallback if git not available
            
            # Build the GitHub URL
            readme_url = f"https://github.com/kellylford/Image-Description-Toolkit/blob/{current_branch}/imagedescriber/README.md"
            
            # Open in default browser
            webbrowser.open(readme_url)
            self.status_bar.showMessage("Opening README in browser...", 3000)
            
        except Exception as e:
            QMessageBox.warning(
                self, "Error",
                f"Failed to open README:\n{str(e)}\n\n"
                f"You can manually visit:\n"
                f"https://github.com/kellylford/Image-Description-Toolkit/blob/main/imagedescriber/README.md"
            )

    def open_ollama_download(self):
        """Open the Ollama download page"""
        try:
            webbrowser.open("https://ollama.ai/download")
            self.status_bar.showMessage("Opening Ollama download page...", 3000)
        except Exception as e:
            QMessageBox.warning(
                self, "Error",
                f"Failed to open Ollama download page:\n{str(e)}\n\n"
                f"You can manually visit: https://ollama.ai/download"
            )

    def show_about_dialog(self):
        """Show the About dialog with version information"""
        try:
            # Read version from VERSION file
            version_file = Path(__file__).parent.parent / "VERSION"
            if version_file.exists():
                version = version_file.read_text().strip()
            else:
                version = "Unknown"
        except:
            version = "Unknown"
        
        about_text = f"""<h2>ImageDescriber</h2>
<p><strong>Version:</strong> {version}</p>
<p><strong>Part of:</strong> Image Description Toolkit</p>

<p>AI-powered image description application with support for:</p>
<ul>
<li>Multiple AI providers (Ollama, OpenAI)</li>
<li>Batch processing</li>
<li>Video frame extraction</li>
<li>Document-based workspaces</li>
<li>Accessibility features</li>
</ul>

<p><strong>GitHub Repository:</strong><br>
<a href="https://github.com/kellylford/Image-Description-Toolkit">
https://github.com/kellylford/Image-Description-Toolkit</a></p>

<p>© 2025 Image Description Toolkit</p>"""
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("About ImageDescriber")
        msg_box.setTextFormat(Qt.TextFormat.RichText)
        msg_box.setText(about_text)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.exec()

    def show_model_manager(self):
        """Show information about external model management tools"""
        message = (
            "<h3>Model Management Tools</h3>"
            "<p>Model management is now handled by external command-line tools that support all AI providers:</p>"
            "<ul>"
            "<li><b>check_models.py</b> - View installed and available models for any provider</li>"
            "<li><b>manage_models.py</b> - Interactive model installation and management</li>"
            "</ul>"
            "<h4>Quick Examples:</h4>"
            "<p><b>View Ollama models:</b><br>"
            "<code>python check_models.py --provider ollama</code></p>"
            "<p><b>Search for models:</b><br>"
            "<code>python check_models.py --search vision</code></p>"
            "<p><b>Interactive management:</b><br>"
            "<code>python manage_models.py</code></p>"
            "<p><b>List all providers:</b><br>"
            "<code>python check_models.py --list-providers</code></p>"
            "<h4>Benefits of External Tools:</h4>"
            "<ul>"
            "<li>Support all providers (Ollama, OpenAI, ONNX, Copilot+ PC, HuggingFace)</li>"
            "<li>Can be used independently of GUI or in scripts</li>"
            "<li>Better search and filtering capabilities</li>"
            "<li>Recommended models clearly marked</li>"
            "<li>View model installation status across all providers</li>"
            "</ul>"
            "<p><b>Documentation:</b> See docs/MODEL_SELECTION_GUIDE.md for complete details.</p>"
        )
        
        QMessageBox.information(
            self,
            "Model Management Tools",
            message
        )

    def show_image_properties(self):
        """Show properties and metadata for the currently selected image"""
        file_path = self.get_current_selected_file_path()
        
        if not file_path:
            QMessageBox.information(
                self, "No Image Selected",
                "Please select an image first to view its properties."
            )
            return
        
        # Check if file exists
        if not Path(file_path).exists():
            QMessageBox.warning(
                self, "File Not Found",
                f"The selected file does not exist:\n{file_path}"
            )
            return
        
        # Extract properties
        properties = self.extract_image_properties(file_path)
        
        # Create properties dialog
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Properties - {Path(file_path).name}")
        dialog.setModal(True)
        dialog.resize(600, 500)
        
        layout = QVBoxLayout(dialog)
        
        # Create scrollable text area for properties
        properties_text = QTextEdit()
        properties_text.setReadOnly(True)
        properties_text.setAccessibleName("Image Properties")
        properties_text.setAccessibleDescription("List of image properties and metadata. Use arrow keys to navigate.")
        properties_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard)
        properties_text.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        properties_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        
        # Format properties as text
        properties_text.setPlainText(self.format_properties_text(properties))
        
        layout.addWidget(properties_text)
        
        # Close button
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(dialog.close)
        layout.addWidget(button_box)
        
        dialog.exec()

    def extract_image_properties(self, file_path: str) -> dict:
        """Extract comprehensive properties from an image file"""
        properties = {}
        file_path_obj = Path(file_path)
        
        try:
            # Basic file properties
            stat = file_path_obj.stat()
            file_size = stat.st_size
            
            properties["File Properties"] = {
                "File name": file_path_obj.name,
                "File path": str(file_path_obj),
                "File size": self.format_file_size(file_size),
                "File type": file_path_obj.suffix.upper().lstrip('.') or "Unknown",
                "Date created": self.format_timestamp(stat.st_ctime),
                "Date modified": self.format_timestamp(stat.st_mtime)
            }
            
            # Try to load image with PIL for detailed properties
            try:
                # Handle HEIC files
                if file_path_obj.suffix.lower() in ['.heic', '.heif']:
                    try:
                        import pillow_heif
                        pillow_heif.register_heif_opener()
                    except ImportError:
                        properties["Error"] = {"HEIC Support": "pillow_heif not available for HEIC files"}
                        return properties
                
                from PIL import Image
                from PIL.ExifTags import TAGS, GPSTAGS
                
                with Image.open(file_path) as img:
                    # Basic image properties
                    properties["Image Properties"] = {
                        "Dimensions": f"{img.width} x {img.height} pixels",
                        "Color mode": img.mode,
                        "Format": img.format or "Unknown",
                        "Has transparency": "Yes" if img.mode in ('RGBA', 'LA') or 'transparency' in img.info else "No"
                    }
                    
                    # Additional format-specific info
                    if hasattr(img, 'info') and img.info:
                        info_props = {}
                        
                        # DPI/Resolution
                        if 'dpi' in img.info:
                            dpi = img.info['dpi']
                            if isinstance(dpi, tuple):
                                info_props["Resolution (DPI)"] = f"{dpi[0]} x {dpi[1]}"
                            else:
                                info_props["Resolution (DPI)"] = str(dpi)
                        
                        # JPEG quality
                        if 'quality' in img.info:
                            info_props["JPEG Quality"] = str(img.info['quality'])
                        
                        # PNG info
                        if img.format == 'PNG':
                            if 'gamma' in img.info:
                                info_props["Gamma"] = str(img.info['gamma'])
                            if 'transparency' in img.info:
                                info_props["Transparency"] = str(img.info['transparency'])
                        
                        # GIF info
                        if img.format == 'GIF':
                            if hasattr(img, 'is_animated'):
                                info_props["Animated"] = "Yes" if img.is_animated else "No"
                                if img.is_animated and hasattr(img, 'n_frames'):
                                    info_props["Frame count"] = str(img.n_frames)
                        
                        if info_props:
                            properties["Format Details"] = info_props
                    
                    # EXIF data
                    if hasattr(img, '_getexif') and img._getexif():
                        exif_data = {}
                        exif = img._getexif()
                        
                        for tag_id, value in exif.items():
                            tag = TAGS.get(tag_id, tag_id)
                            
                            # Format specific EXIF values
                            if tag == "DateTime":
                                exif_data["Date taken"] = str(value)
                            elif tag == "Make":
                                exif_data["Camera make"] = str(value)
                            elif tag == "Model":
                                exif_data["Camera model"] = str(value)
                            elif tag == "ExifImageWidth":
                                exif_data["EXIF width"] = f"{value} pixels"
                            elif tag == "ExifImageHeight":
                                exif_data["EXIF height"] = f"{value} pixels"
                            elif tag == "Orientation":
                                orientation_map = {
                                    1: "Normal", 2: "Mirrored horizontal", 3: "Rotated 180°",
                                    4: "Mirrored vertical", 5: "Mirrored horizontal, rotated 270°",
                                    6: "Rotated 90°", 7: "Mirrored horizontal, rotated 90°", 8: "Rotated 270°"
                                }
                                exif_data["Orientation"] = orientation_map.get(value, f"Unknown ({value})")
                            elif tag == "Flash":
                                flash_map = {0: "No flash", 1: "Flash fired", 5: "Flash fired, no return",
                                           7: "Flash fired, return detected", 9: "Flash fired, compulsory",
                                           13: "Flash fired, compulsory, no return", 15: "Flash fired, compulsory, return detected",
                                           16: "No flash, compulsory", 24: "No flash, auto", 25: "Flash fired, auto",
                                           29: "Flash fired, auto, no return", 31: "Flash fired, auto, return detected"}
                                exif_data["Flash"] = flash_map.get(value, f"Unknown flash mode ({value})")
                            elif tag == "ISOSpeedRatings":
                                exif_data["ISO"] = str(value)
                            elif tag == "FNumber":
                                if isinstance(value, tuple) and len(value) == 2:
                                    f_number = value[0] / value[1] if value[1] != 0 else value[0]
                                    exif_data["Aperture"] = f"f/{f_number:.1f}"
                                else:
                                    exif_data["Aperture"] = str(value)
                            elif tag == "ExposureTime":
                                if isinstance(value, tuple) and len(value) == 2:
                                    if value[1] == 1:
                                        exif_data["Shutter speed"] = f"{value[0]}s"
                                    else:
                                        exif_data["Shutter speed"] = f"{value[0]}/{value[1]}s"
                                else:
                                    exif_data["Shutter speed"] = str(value)
                            elif tag == "FocalLength":
                                if isinstance(value, tuple) and len(value) == 2:
                                    focal = value[0] / value[1] if value[1] != 0 else value[0]
                                    exif_data["Focal length"] = f"{focal:.1f}mm"
                                else:
                                    exif_data["Focal length"] = str(value)
                            elif tag == "GPSInfo":
                                # GPS data is complex, extract basic coordinates if available
                                gps_data = {}
                                for gps_tag_id, gps_value in value.items():
                                    gps_tag = GPSTAGS.get(gps_tag_id, gps_tag_id)
                                    if gps_tag in ["GPSLatitude", "GPSLongitude", "GPSLatitudeRef", "GPSLongitudeRef"]:
                                        gps_data[gps_tag] = gps_value
                                
                                if len(gps_data) >= 4:  # Need all 4 components for coordinates
                                    try:
                                        lat = self.convert_gps_coordinate(gps_data.get("GPSLatitude", []))
                                        lon = self.convert_gps_coordinate(gps_data.get("GPSLongitude", []))
                                        lat_ref = gps_data.get("GPSLatitudeRef", "")
                                        lon_ref = gps_data.get("GPSLongitudeRef", "")
                                        
                                        if lat_ref == "S":
                                            lat = -lat
                                        if lon_ref == "W":
                                            lon = -lon
                                        
                                        exif_data["GPS coordinates"] = f"{lat:.6f}, {lon:.6f}"
                                    except:
                                        exif_data["GPS data"] = "Present but could not parse"
                            elif isinstance(value, (str, int, float)) and len(str(value)) < 100:
                                # Include other simple EXIF tags
                                exif_data[str(tag)] = str(value)
                        
                        if exif_data:
                            properties["EXIF Metadata"] = exif_data
                    
                    # Color profile information
                    if hasattr(img, 'info') and 'icc_profile' in img.info:
                        try:
                            import io
                            from PIL import ImageCms
                            icc_profile = img.info['icc_profile']
                            profile = ImageCms.ImageCmsProfile(io.BytesIO(icc_profile))
                            properties["Color Profile"] = {
                                "Profile description": profile.profile.profile_description.strip(),
                                "Color space": profile.profile.colorspace,
                                "Device class": profile.profile.device_class
                            }
                        except Exception:
                            properties["Color Profile"] = {"ICC Profile": "Present but could not parse"}
            
            except Exception as e:
                properties["Image Analysis Error"] = {"Error": f"Could not analyze image: {str(e)}"}
        
        except Exception as e:
            properties["File Access Error"] = {"Error": f"Could not access file: {str(e)}"}
        
        return properties

    def convert_gps_coordinate(self, coord_tuple):
        """Convert GPS coordinate from EXIF format to decimal degrees"""
        if not coord_tuple or len(coord_tuple) != 3:
            return 0.0
        
        degrees = coord_tuple[0]
        minutes = coord_tuple[1]
        seconds = coord_tuple[2]
        
        # Handle tuple format (numerator, denominator)
        if isinstance(degrees, tuple):
            degrees = degrees[0] / degrees[1] if degrees[1] != 0 else degrees[0]
        if isinstance(minutes, tuple):
            minutes = minutes[0] / minutes[1] if minutes[1] != 0 else minutes[0]
        if isinstance(seconds, tuple):
            seconds = seconds[0] / seconds[1] if seconds[1] != 0 else seconds[0]
        
        return degrees + minutes/60 + seconds/3600

    def format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format"""
        if size_bytes < 1024:
            return f"{size_bytes} bytes"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    def format_timestamp(self, timestamp: float) -> str:
        """Format timestamp as readable date/time"""
        try:
            from datetime import datetime
            return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        except:
            return "Unknown"

    def format_properties_text(self, properties: dict) -> str:
        """Format properties dictionary as readable text"""
        lines = []
        
        for category, props in properties.items():
            lines.append(f"=== {category} ===")
            lines.append("")
            
            if isinstance(props, dict):
                for key, value in props.items():
                    lines.append(f"{key}: {value}")
            else:
                lines.append(str(props))
            
            lines.append("")
        
        return "\n".join(lines)

    def show_description_properties(self):
        """Show diagnostic properties for the currently selected description"""
        try:
            # Get currently selected description based on navigation mode
            if self.navigation_mode == "tree":
                descriptions_list = self.description_list
            elif self.navigation_mode == "master_detail":
                descriptions_list = self.description_list_md
            else:
                QMessageBox.information(
                    self, "No Navigation Mode",
                    "Unable to determine current navigation mode."
                )
                return
            
            if not descriptions_list or descriptions_list.currentRow() < 0:
                QMessageBox.information(
                    self, "No Description Selected",
                    "Please select a description first to view its properties."
                )
                return
            
            current_item = descriptions_list.currentItem()
            if not current_item:
                return
            
            # Extract description data
            description_data = current_item.data(Qt.ItemDataRole.UserRole)
            if not description_data:
                QMessageBox.information(
                    self, "No Description Data",
                    "The selected description has no associated data."
                )
                return
            
            # Get the selected image file path for additional context
            try:
                file_path = self.get_current_selected_file_path()
            except Exception as e:
                file_path = None
                print(f"Warning: Could not get file path: {e}")
            
            # Extract diagnostic properties
            properties = self.extract_description_properties(description_data, file_path)
            
            # Create properties dialog
            dialog = QDialog(self)
            dialog.setWindowTitle("Description Properties (Diagnostic)")
            dialog.setModal(True)
            dialog.resize(700, 600)
            
            layout = QVBoxLayout(dialog)
            
            # Create scrollable text area for properties
            properties_text = QTextEdit()
            properties_text.setReadOnly(True)
            properties_text.setAccessibleName("Description Properties")
            properties_text.setAccessibleDescription("Diagnostic information about the selected description including YOLO detection data, model info, and processing details.")
            properties_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard)
            properties_text.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            properties_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
            
            # Format properties as text
            properties_text.setPlainText(self.format_description_properties_text(properties))
            
            layout.addWidget(properties_text)
            
            # Close button
            button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
            button_box.rejected.connect(dialog.close)
            layout.addWidget(button_box)
            
            dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(
                self, "Properties Error", 
                f"Failed to display description properties:\n{str(e)}"
            )

    def extract_description_properties(self, description_data, file_path: str = None) -> dict:
        """Extract comprehensive diagnostic properties from a description"""
        import re
        properties = {}
        
        try:
            # Handle different data formats
            if isinstance(description_data, str):
                # If it's just a string, create a minimal dict structure
                description_dict = {
                    "text": description_data,
                    "id": "Unknown",
                    "created": "Unknown",
                    "model": "Unknown",
                    "provider": "Unknown",
                    "prompt_style": "Unknown",
                    "custom_prompt": ""
                }
            elif isinstance(description_data, dict):
                description_dict = description_data
            else:
                # Try to convert to dict if it has a to_dict method
                if hasattr(description_data, 'to_dict'):
                    description_dict = description_data.to_dict()
                else:
                    raise ValueError(f"Unsupported description data type: {type(description_data)}")
            
            # Get description text and handle emoji/large text issues
            description_text = description_dict.get("text", "")
            
            # Remove emojis for display (they can cause rendering issues)
            def remove_emojis(text):
                # Keep emoji characters in the data but flag them
                emoji_pattern = re.compile(
                    "["
                    u"\U0001F600-\U0001F64F"  # emoticons
                    u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                    u"\U0001F680-\U0001F6FF"  # transport & map symbols
                    u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                    u"\U00002702-\U000027B0"
                    u"\U000024C2-\U0001F251"
                    "]+", flags=re.UNICODE)
                return emoji_pattern.sub(r'', text)
            
            # Count emojis before removing
            emoji_count = len(description_text) - len(remove_emojis(description_text))
            
            # Basic Description Info
            basic_info = {
                "Description ID": str(description_dict.get("id", "Unknown")),
                "Created": str(description_dict.get("created", "Unknown")),
                "Model": str(description_dict.get("model", "Unknown")),
                "Provider": str(description_dict.get("provider", "Unknown")),
                "Prompt Style": str(description_dict.get("prompt_style", "Unknown")),
                "Custom Prompt": str(description_dict.get("custom_prompt", "") or "None"),
                "Text Length": f"{len(description_text)} characters",
                "Contains Emojis": f"Yes ({emoji_count} emoji characters)" if emoji_count > 0 else "No",
                "Data Type": str(type(description_data).__name__),
            }
            properties["Basic Information"] = basic_info
            
            # AI Provider Analysis
            provider_info = {}
            model_name = description_dict.get("model", "")
            provider = description_dict.get("provider", "")
            
            provider_info["Provider Type"] = provider
            provider_info["Model Name"] = model_name
            
            # Check for YOLO enhancement indicators (no emojis)
            yolo_indicators = []
            if "YOLO Enhanced" in model_name:
                yolo_indicators.append("Model name contains YOLO Enhanced indicator")
            if "ENHANCED OLLAMA" in model_name:
                yolo_indicators.append("Enhanced Ollama header detected")
            
            # Check description text for YOLO data
            if "YOLO" in description_text:
                yolo_indicators.append("Description text contains YOLO references")
            if "detected objects" in description_text.lower():
                yolo_indicators.append("Description mentions detected objects")
            if any(location in description_text for location in ["top-left", "top-center", "top-right", "middle-left", "middle-center", "middle-right", "bottom-left", "bottom-center", "bottom-right"]):
                yolo_indicators.append("Description contains spatial location data")
            if any(size in description_text for size in ["large", "medium", "small", "tiny"]):
                yolo_indicators.append("Description contains object size data")
            
            provider_info["YOLO Enhancement Detected"] = "Yes" if yolo_indicators else "No"
            if yolo_indicators:
                provider_info["YOLO Indicators"] = "; ".join(yolo_indicators)
            
            properties["AI Provider Analysis"] = provider_info
            
            # Enhanced Processing Detection (for ONNX/Object Detection providers)
            if provider in ["onnx", "object_detection"]:
                enhanced_info = {}
                
                try:
                    # Analyze for object detection patterns
                    # Look for confidence percentages
                    confidence_pattern = r'(\d+)%'
                    confidences = re.findall(confidence_pattern, description_text)
                    
                    if confidences:
                        enhanced_info["Objects with Confidence Scores"] = len(confidences)
                        enhanced_info["Confidence Range"] = f"{min(map(int, confidences))}% - {max(map(int, confidences))}%"
                    
                    # Count spatial location references
                    spatial_terms = ["top", "bottom", "middle", "left", "right", "center"]
                    spatial_count = sum(description_text.lower().count(term) for term in spatial_terms)
                    enhanced_info["Spatial References Count"] = spatial_count
                    
                    # Look for YOLO model references
                    if "YOLOv8x" in description_text:
                        enhanced_info["YOLO Model"] = "YOLOv8x (Maximum Accuracy)"
                    elif "YOLOv8" in description_text:
                        enhanced_info["YOLO Model"] = "YOLOv8 (Detected)"
                    elif "YOLO" in description_text:
                        enhanced_info["YOLO Model"] = "YOLO (Generic Reference)"
                    else:
                        enhanced_info["YOLO Model"] = "Not Detected"
                    
                    # Check for dimension information
                    dimension_pattern = r'(\d+)×(\d+)px'
                    dimensions = re.findall(dimension_pattern, description_text)
                    if dimensions:
                        enhanced_info["Image Dimensions"] = f"{dimensions[0][0]}×{dimensions[0][1]}px"
                        
                except Exception as e:
                    enhanced_info["Analysis Error"] = f"Pattern matching failed: {str(e)[:100]}"
                    
                properties["Enhanced Processing"] = enhanced_info
            
            # Prompt Analysis
            prompt_info = {}
            prompt_style = description_dict.get("prompt_style", "")
            custom_prompt = description_dict.get("custom_prompt", "")
            
            prompt_info["Style"] = prompt_style if prompt_style else "None"
            prompt_info["Custom Prompt Used"] = "Yes" if custom_prompt else "No"
            if custom_prompt:
                # Truncate long custom prompts
                prompt_info["Custom Prompt Length"] = f"{len(custom_prompt)} characters"
                if len(custom_prompt) > 100:
                    prompt_info["Custom Prompt Preview"] = custom_prompt[:100] + "..."
                else:
                    prompt_info["Custom Prompt"] = custom_prompt
                
            properties["Prompt Information"] = prompt_info
            
            # Description Text Preview (truncated for large texts, emoji-cleaned)
            text_info = {}
            if description_text:
                # Remove emojis for cleaner display
                clean_text = remove_emojis(description_text)
                
                # Truncate to reasonable length
                max_preview_length = 500
                if len(clean_text) > max_preview_length:
                    text_info["Text Preview"] = clean_text[:max_preview_length] + f"\n\n... (truncated, showing first {max_preview_length} of {len(clean_text)} characters)"
                else:
                    text_info["Text Preview"] = clean_text
                
                text_info["Full Text Length"] = f"{len(description_text)} characters"
                text_info["Contains YOLO Keywords"] = "Yes" if ("YOLOv8" in description_text or "detected objects" in description_text.lower()) else "No"
                
                # Look for object detection patterns in text
                detection_keywords = ["confidence", "location", "bounding box", "detected", "spatial"]
                found_keywords = [kw for kw in detection_keywords if kw in description_text.lower()]
                
                if found_keywords:
                    text_info["Detection Keywords Found"] = ", ".join(found_keywords)
            
            properties["Description Text Analysis"] = text_info
            
            # File Context (if available)
            if file_path:
                try:
                    from pathlib import Path
                    context_info = {
                        "Source Image": Path(file_path).name if file_path else "Unknown",
                        "Image Path": file_path if file_path else "Unknown",
                        "Image Type": Path(file_path).suffix.upper().lstrip('.') if file_path else "Unknown"
                    }
                    properties["File Context"] = context_info
                except Exception as e:
                    properties["File Context"] = {"Error": f"Could not analyze file: {str(e)}"}
            
        except Exception as e:
            properties["Error"] = {"Message": f"Property extraction failed: {str(e)}", "Data Type": str(type(description_data))}
        
        return properties

    def format_description_properties_text(self, properties: dict) -> str:
        """Format description properties dictionary as readable diagnostic text"""
        try:
            lines = []
            lines.append("DESCRIPTION DIAGNOSTIC PROPERTIES")
            lines.append("=" * 50)
            lines.append("")
            
            for category, props in properties.items():
                lines.append(f"{category}")
                lines.append("-" * len(category))
                
                if isinstance(props, dict):
                    for key, value in props.items():
                        try:
                            # Format boolean values with indicators
                            if isinstance(value, bool):
                                value = "Yes" if value else "No"
                            elif key == "YOLO Enhancement Detected":
                                value = value if value == "Yes" else value
                            elif key == "YOLO Model" and "Not Detected" in str(value):
                                value = str(value)
                            elif key == "YOLO Model" and "v8x" in str(value):
                                value = str(value)
                            elif key == "Objects with Spatial Data" and value:
                                value = "Yes"
                                
                            lines.append(f"  {key}: {value}")
                        except Exception as e:
                            lines.append(f"  {key}: [Error formatting: {str(e)}]")
                else:
                    lines.append(f"  {props}")
                
                lines.append("")
            
            lines.append("Use this information to diagnose if YOLO enhancement is working properly.")
            lines.append("Look for YOLO indicators, spatial data, and object detection patterns.")
            
            return "\n".join(lines)
            
        except Exception as e:
            return f"Error formatting properties: {str(e)}\n\nRaw data:\n{str(properties)}"

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

    def import_workflow_results(self):
        """Import results from a workflow processing directory"""
        from pathlib import Path
        
        # Select workflow directory
        workflow_dir = QFileDialog.getExistingDirectory(
            self, 
            "Select Workflow Results Directory",
            str(Path.home()),
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks
        )
        
        if not workflow_dir:
            return
            
        try:
            # Validate workflow directory structure
            workflow_path = Path(workflow_dir)
            descriptions_file = workflow_path / "descriptions" / "image_descriptions.txt"
            converted_images_dir = workflow_path / "converted_images"
            
            if not descriptions_file.exists():
                QMessageBox.warning(self, "Invalid Workflow Directory", 
                                  f"Could not find descriptions file:\n{descriptions_file}")
                return
                
            if not converted_images_dir.exists():
                QMessageBox.warning(self, "Invalid Workflow Directory",
                                  f"Could not find converted images directory:\n{converted_images_dir}")
                return
            
            # Start import process
            self._import_workflow_with_progress(workflow_path, is_update=False)
            
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to import workflow results:\n{e}")

    def _import_workflow_with_progress(self, workflow_path, descriptions_file=None, converted_images_dir=None, is_update=False):
        """Import workflow results with progress indication"""
        import re
        from datetime import datetime
        
        # Support both old and new calling patterns
        if descriptions_file is None:
            descriptions_file = workflow_path / "descriptions" / "image_descriptions.txt"
        if converted_images_dir is None:
            converted_images_dir = workflow_path / "converted_images"
        
        # Validate files exist
        if not descriptions_file.exists():
            error_msg = f"Could not find descriptions file:\n{descriptions_file}"
            title = "Update Error" if is_update else "Invalid Workflow Directory"
            QMessageBox.warning(self, title, error_msg)
            return
            
        if not converted_images_dir.exists():
            error_msg = f"Could not find converted images directory:\n{converted_images_dir}"
            title = "Update Error" if is_update else "Invalid Workflow Directory"
            QMessageBox.warning(self, title, error_msg)
            return
        
        # Create progress dialog
        action_name = "Updating" if is_update else "Importing"
        progress = QProgressDialog(f"{action_name} workflow results...", "Cancel", 0, 100, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.show()
        
        try:
            # Parse descriptions file
            progress.setLabelText("Parsing descriptions file...")
            progress.setValue(10)
            QApplication.processEvents()
            
            descriptions_data = self._parse_workflow_descriptions(descriptions_file)
            
            if progress.wasCanceled():
                return
                
            # Create or update workspace
            progress.setLabelText("Setting up workspace...")
            progress.setValue(20)
            QApplication.processEvents()
            
            if not self.workspace:
                self.new_workspace()
            
            # Import images and descriptions
            total_items = len(descriptions_data)
            imported_count = 0
            skipped_count = 0
            
            for i, (file_path, description_info) in enumerate(descriptions_data.items()):
                if progress.wasCanceled():
                    break
                    
                progress.setLabelText(f"Importing image {i+1} of {total_items}...")
                progress.setValue(20 + int((i / total_items) * 70))
                QApplication.processEvents()
                
                # Find corresponding image in converted_images
                image_file = self._find_workflow_image(workflow_path, file_path)
                
                if image_file:
                    # Import this image and description
                    if self._import_single_workflow_item(image_file, description_info):
                        imported_count += 1
                    else:
                        skipped_count += 1
                else:
                    skipped_count += 1
                    print(f"Warning: Could not find image file for {file_path}")
            
            # Refresh UI
            progress.setLabelText("Updating display...")
            progress.setValue(95)
            QApplication.processEvents()
            
            self.refresh_view()
            
            progress.setValue(100)
            
            # Save the workflow directory for future updates (only for new imports)
            if not is_update:
                self.workspace.imported_workflow_dir = str(workflow_path)
                self.workspace.mark_modified()
                # Update menu states
                self.update_menu_states()
            
            # Show summary
            action_name = "Update" if is_update else "Import"
            title = f"{action_name} Complete"
            message = f"Successfully {'updated' if is_update else 'imported'} {imported_count} images from workflow.\n"
            message += f"Skipped: {skipped_count}\n"
            message += f"Workflow directory: {workflow_path.name}"
            
            QMessageBox.information(self, title, message)
            
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Error during import:\n{e}")
        finally:
            progress.close()

    def _parse_workflow_descriptions(self, descriptions_file):
        """Parse workflow descriptions.txt file and return structured data"""
        descriptions_data = {}
        
        with open(descriptions_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split by separator lines
        sections = content.split('--------------------------------------------------------------------------------')
        
        for section in sections:
            section = section.strip()
            if not section or 'Generated on:' in section:
                continue
                
            # Extract file path
            file_match = re.search(r'File: (.+)', section)
            if not file_match:
                continue
                
            file_path = file_match.group(1).strip()
            
            # Extract model
            model_match = re.search(r'Model: (.+)', section)
            model = model_match.group(1).strip() if model_match else "unknown"
            
            # Extract prompt style
            prompt_match = re.search(r'Prompt Style: (.+)', section)
            prompt_style = prompt_match.group(1).strip() if prompt_match else "unknown"
            
            # Extract description (everything after "Description:")
            desc_match = re.search(r'Description: (.+)', section, re.DOTALL)
            description = desc_match.group(1).strip() if desc_match else ""
            
            descriptions_data[file_path] = {
                'model': model,
                'prompt_style': prompt_style,
                'description': description,
                'created': datetime.now().isoformat()
            }
        
        return descriptions_data

    def _find_workflow_image(self, workflow_path, original_path):
        """Find the actual image file corresponding to the description path"""
        from pathlib import Path
        
        # The original_path comes from the descriptions file and could be:
        # 1. "202509_a\IMG_3137.PNG" (from original images in temp structure)
        # 2. "converted_images\AAZT1776.jpg" (from converted images in temp structure)
        # 3. "extracted_frames\video_frame.jpg" (from video frames in temp structure)
        
        original_filename = Path(original_path).name
        
        # Check multiple possible locations for the actual file
        search_dirs = [
            workflow_path / "converted_images",
            workflow_path / "extracted_frames",
            workflow_path / "temp_combined_images" / "202509_a",  # Original images from temp structure
            workflow_path / "temp_combined_images" / "converted_images",  # Converted images from temp structure
            workflow_path / "temp_combined_images" / "extracted_frames",  # Extracted frames from temp structure
        ]
        
        # Add dynamic search for any subdirectories in temp_combined_images
        temp_combined_dir = workflow_path / "temp_combined_images"
        if temp_combined_dir.exists():
            for subdir in temp_combined_dir.iterdir():
                if subdir.is_dir() and subdir not in search_dirs:
                    search_dirs.append(subdir)
        
        # If the original path includes "converted_images", try exact filename match first
        if "converted_images" in original_path:
            converted_images_dir = workflow_path / "converted_images"
            if converted_images_dir.exists():
                exact_match = converted_images_dir / original_filename
                if exact_match.exists():
                    return exact_match
        
        # Handle temp directory paths like "202509_a\IMG_3137.PNG"
        if "\\" in original_path or "/" in original_path:
            # Try to reconstruct the full path within temp_combined_images
            temp_path = workflow_path / "temp_combined_images" / original_path.replace("\\", "/")
            if temp_path.exists():
                return temp_path
        
        # For all search directories, try to find the image
        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
                
            # Try exact filename match
            exact_match = search_dir / original_filename
            if exact_match.exists():
                return exact_match
            
            # Try case-insensitive match
            for image_file in search_dir.iterdir():
                if image_file.is_file() and image_file.name.lower() == original_filename.lower():
                    return image_file
            
            # Try matching by stem (filename without extension) for converted files
            original_stem = Path(original_filename).stem.lower()
            for image_file in search_dir.iterdir():
                if image_file.is_file() and image_file.stem.lower() == original_stem:
                    return image_file
        
        # If still no match found, look for any images with similar names
        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
                
            # Look for partial matches in the filename
            for image_file in search_dir.iterdir():
                if image_file.is_file() and image_file.suffix.lower() in {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}:
                    # Check if original filename (without path prefix) contains some common elements
                    if len(original_filename) > 4:  # Avoid matching very short names
                        # This is a fallback - try to match based on creation time or file size if needed
                        # For now, we'll just log that we couldn't find a match
                        pass
        
        # No match found
        print(f"Warning: Could not find image file for description path: {original_path}")
        return None

    def _import_single_workflow_item(self, image_file, description_info):
        """Import a single image and its description into the workspace"""
        try:
            # Create ImageItem
            item = ImageItem(str(image_file), "image")
            
            # Create ImageDescription
            from data_models import ImageDescription
            description = ImageDescription(
                text=description_info['description'],
                model=description_info['model'],
                prompt_style=description_info['prompt_style'],
                created=description_info['created'],
                provider="workflow_import"
            )
            
            item.add_description(description)
            
            # Add to workspace
            self.workspace.add_item(item)
            
            return True
            
        except Exception as e:
            print(f"Error importing {image_file}: {e}")
            return False

    def update_from_workflow(self):
        """Update workspace with new results from the previously imported workflow directory"""
        if not self.workspace:
            QMessageBox.warning(self, "No Workspace", "Please create or open a workspace first.")
            return
            
        # Check if we have a saved workflow directory
        if not hasattr(self.workspace, 'imported_workflow_dir') or not self.workspace.imported_workflow_dir:
            QMessageBox.information(self, "No Workflow Import", 
                                  "No workflow has been imported yet. Use 'Import Workflow...' first.")
            return
        
        workflow_path = Path(self.workspace.imported_workflow_dir)
        
        # Check if the workflow directory still exists
        if not workflow_path.exists():
            QMessageBox.warning(self, "Workflow Directory Not Found", 
                              f"The previously imported workflow directory no longer exists:\n{workflow_path}\n\n"
                              f"Use 'Import Workflow...' to select a new workflow directory.")
            return
        
        try:
            # Import/update from the saved workflow directory
            self._import_workflow_with_progress(workflow_path, is_update=True)
            
        except Exception as e:
            QMessageBox.critical(self, "Update Error", f"Failed to update from workflow:\n{e}")


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
