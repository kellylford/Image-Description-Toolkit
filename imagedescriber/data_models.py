"""
Data models for Image Describer

This module contains the core data structures for managing
images, descriptions, and workspaces.
"""

import time
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

# Constants
WORKSPACE_VERSION = "3.0"


class ImageDescription:
    """Represents a single description for an image"""
    def __init__(self, text: str, model: str = "", prompt_style: str = "", 
                 created: str = "", custom_prompt: str = "", provider: str = "", detection_data: List[dict] = None):
        self.text = text
        self.model = model
        self.prompt_style = prompt_style
        self.created = created or datetime.now().isoformat()
        self.custom_prompt = custom_prompt
        self.provider = provider
        self.detection_data = detection_data or []  # List of detected objects with bounding boxes
        self.id = f"{int(time.time() * 1000)}"  # Unique ID
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "model": self.model,
            "prompt_style": self.prompt_style,
            "created": self.created,
            "custom_prompt": self.custom_prompt,
            "provider": self.provider,
            "detection_data": self.detection_data
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        desc = cls(
            text=data.get("text", ""),
            model=data.get("model", ""),
            prompt_style=data.get("prompt_style", ""),
            created=data.get("created", ""),
            custom_prompt=data.get("custom_prompt", ""),
            provider=data.get("provider", ""),
            detection_data=data.get("detection_data", [])
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
        self.imported_workflow_dir: Optional[str] = None  # Track imported workflow directory for updates
        self.cached_ollama_models: Optional[List[str]] = None  # Cached Ollama models for faster dialog loading
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
            "imported_workflow_dir": getattr(self, 'imported_workflow_dir', None),  # Track workflow imports
            "cached_ollama_models": getattr(self, 'cached_ollama_models', None),  # Cached Ollama models
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
        workspace.imported_workflow_dir = data.get("imported_workflow_dir", None)  # Load workflow dir
        workspace.cached_ollama_models = data.get("cached_ollama_models", None)  # Load cached models
        workspace.created = data.get("created", workspace.created)
        workspace.modified = data.get("modified", workspace.modified)
        workspace.saved = True
        return workspace