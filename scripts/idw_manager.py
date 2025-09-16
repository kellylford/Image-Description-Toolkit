#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IDW Manager - Thread-safe Image Description Workspace file management

This module provides atomic operations for IDW files with support for:
- Resume capability for large batch processing
- Live monitoring of ongoing workflows
- Thread-safe concurrent access
- Atomic updates with corruption recovery
- Comprehensive error handling and validation

Author: Image Description Toolkit
Date: September 16, 2025
"""

import json
import threading
import time
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import hashlib
import os

# Platform-specific imports for file locking
try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False

try:
    import msvcrt
    HAS_MSVCRT = True
except ImportError:
    HAS_MSVCRT = False

# Configure logging
logger = logging.getLogger(__name__)


class ProcessingStatus(Enum):
    """Processing status for IDW items"""
    NOT_STARTED = "not_started"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ProcessingMode(Enum):
    """IDW processing modes"""
    BATCH = "batch"
    INTERACTIVE = "interactive"
    MONITORING = "monitoring"


@dataclass
class ProcessingInfo:
    """Processing information for an IDW item"""
    status: ProcessingStatus
    processed_at: Optional[str] = None
    processing_time_ms: Optional[int] = None
    source_type: Optional[str] = None  # image, video_frame, converted_heic
    conversion_applied: Optional[str] = None
    extraction_source: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class UserModifications:
    """User modifications to an IDW item"""
    renamed: bool = False
    custom_description: bool = False
    tags: List[str] = None
    rating: int = 0
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class ItemMetadata:
    """Metadata for an IDW item"""
    file_size: Optional[int] = None
    dimensions: Optional[List[int]] = None
    creation_date: Optional[str] = None
    camera_model: Optional[str] = None
    
    
@dataclass
class IDWItem:
    """Complete IDW item representation"""
    item_id: str
    original_file: str
    display_file: str
    description: str = ""
    metadata: Optional[ItemMetadata] = None
    processing_info: Optional[ProcessingInfo] = None
    user_modifications: Optional[UserModifications] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = ItemMetadata()
        if self.processing_info is None:
            self.processing_info = ProcessingInfo(status=ProcessingStatus.NOT_STARTED)
        if self.user_modifications is None:
            self.user_modifications = UserModifications()


class IDWFormatError(Exception):
    """Raised when IDW file format is invalid"""
    pass


class IDWCorruptionError(Exception):
    """Raised when IDW file is corrupted"""
    pass


class IDWLockError(Exception):
    """Raised when unable to acquire IDW file lock"""
    pass


class IDWFileLock:
    """Context manager for file locking with timeout"""
    
    def __init__(self, file_path: Path, timeout: float = 10.0):
        self.file_path = file_path
        self.timeout = timeout
        self.lock_file = None
        self.acquired = False
    
    def __enter__(self):
        lock_path = self.file_path.with_suffix('.lock')
        try:
            self.lock_file = open(lock_path, 'w')
            start_time = time.time()
            
            while time.time() - start_time < self.timeout:
                try:
                    if HAS_MSVCRT and os.name == 'nt':  # Windows
                        msvcrt.locking(self.lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                    elif HAS_FCNTL:  # Unix-like systems
                        fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    else:
                        # Fallback for systems without proper locking
                        # Use file existence as a simple lock mechanism
                        pass
                    
                    self.acquired = True
                    return self
                except (IOError, OSError):
                    time.sleep(0.1)  # Brief pause before retry
            
            raise IDWLockError(f"Unable to acquire lock for {self.file_path} within {self.timeout}s")
            
        except Exception as e:
            if self.lock_file:
                self.lock_file.close()
            raise IDWLockError(f"Failed to create lock file: {e}")
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.lock_file:
            try:
                if self.acquired:
                    if HAS_MSVCRT and os.name == 'nt':
                        msvcrt.locking(self.lock_file.fileno(), msvcrt.LK_UNLCK, 1)
                    elif HAS_FCNTL:
                        fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
                self.lock_file.close()
                
                # Clean up lock file
                lock_path = self.file_path.with_suffix('.lock')
                if lock_path.exists():
                    lock_path.unlink()
            except Exception as e:
                logger.warning(f"Error releasing lock: {e}")


class IDWManager:
    """
    Thread-safe IDW file management with atomic operations
    
    Provides:
    - Atomic updates for resume safety
    - Thread-safe concurrent access
    - Live monitoring capabilities
    - Corruption recovery
    - Resume checkpoint management
    """
    
    def __init__(self, idw_path: Union[str, Path], mode: str = "read"):
        """
        Initialize IDW manager
        
        Args:
            idw_path: Path to IDW file
            mode: Access mode ("read", "write", "append")
        """
        self.idw_path = Path(idw_path)
        self.mode = mode
        self._lock = threading.RLock()
        self._data_cache: Optional[Dict[str, Any]] = None
        self._cache_timestamp: Optional[float] = None
        self._change_callbacks: List[Callable[[List[str]], None]] = []
        self._monitoring = False
        
        # Validate mode
        if mode not in ["read", "write", "append"]:
            raise ValueError(f"Invalid mode: {mode}. Must be 'read', 'write', or 'append'")
        
        # Ensure directory exists for write/append modes
        if mode in ["write", "append"]:
            self.idw_path.parent.mkdir(parents=True, exist_ok=True)
            
        # Initialize file if in write mode and doesn't exist
        if mode == "write" and not self.idw_path.exists():
            self._initialize_empty_idw()
    
    def _initialize_empty_idw(self) -> None:
        """Initialize an empty IDW file with default structure"""
        empty_data = {
            "workspace_info": {
                "version": "2.0",
                "created": datetime.now(timezone.utc).isoformat(),
                "last_modified": datetime.now(timezone.utc).isoformat(),
                "source_directory": "",
                "processing_mode": ProcessingMode.INTERACTIVE.value
            },
            "workflow_progress": {
                "total_files": 0,
                "completed_files": 0,
                "failed_files": 0,
                "skipped_files": 0,
                "last_processed": None,
                "batch_id": None,
                "is_complete": False,
                "resume_checkpoint": None
            },
            "processing_config": {
                "model": None,
                "prompt_style": None,
                "provider": None,
                "custom_prompt": None,
                "conversion_settings": {
                    "heic_to_jpeg": True,
                    "video_frame_extraction": True
                }
            },
            "items": {},
            "batch_statistics": {
                "files_by_type": {},
                "processing_times": {
                    "average_ms": 0,
                    "fastest_ms": 0,
                    "slowest_ms": 0
                },
                "errors": {}
            }
        }
        
        self._save_idw_data(empty_data)
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file for integrity checking"""
        hasher = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            logger.warning(f"Could not calculate hash for {file_path}: {e}")
            return ""
    
    def _load_idw_data(self, use_cache: bool = True) -> Dict[str, Any]:
        """
        Load IDW data with caching and validation
        
        Args:
            use_cache: Whether to use cached data if available
            
        Returns:
            IDW data dictionary
            
        Raises:
            IDWCorruptionError: If file is corrupted
            IDWFormatError: If file format is invalid
        """
        if not self.idw_path.exists():
            if self.mode == "read":
                raise FileNotFoundError(f"IDW file not found: {self.idw_path}")
            else:
                self._initialize_empty_idw()
        
        # Check cache validity
        current_mtime = self.idw_path.stat().st_mtime
        if (use_cache and self._data_cache is not None and 
            self._cache_timestamp is not None and 
            current_mtime <= self._cache_timestamp):
            return self._data_cache
        
        try:
            with open(self.idw_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate basic structure
            self._validate_idw_structure(data)
            
            # Update cache
            self._data_cache = data
            self._cache_timestamp = current_mtime
            
            return data
            
        except json.JSONDecodeError as e:
            # Try backup recovery
            backup_path = self.idw_path.with_suffix('.bak')
            if backup_path.exists():
                logger.warning(f"IDW file corrupted, attempting backup recovery: {e}")
                try:
                    with open(backup_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    self._validate_idw_structure(data)
                    
                    # Restore from backup
                    shutil.copy2(backup_path, self.idw_path)
                    logger.info("Successfully recovered from backup")
                    
                    self._data_cache = data
                    self._cache_timestamp = self.idw_path.stat().st_mtime
                    return data
                    
                except Exception as backup_error:
                    logger.error(f"Backup recovery failed: {backup_error}")
            
            raise IDWCorruptionError(f"IDW file corrupted and no valid backup found: {e}")
        
        except Exception as e:
            raise IDWFormatError(f"Failed to load IDW file: {e}")
    
    def _validate_idw_structure(self, data: Dict[str, Any]) -> None:
        """
        Validate IDW file structure
        
        Args:
            data: IDW data to validate
            
        Raises:
            IDWFormatError: If structure is invalid
        """
        required_sections = ["workspace_info", "workflow_progress", "processing_config", "items"]
        
        for section in required_sections:
            if section not in data:
                raise IDWFormatError(f"Missing required section: {section}")
        
        # Validate workspace_info
        workspace_info = data["workspace_info"]
        if "version" not in workspace_info:
            raise IDWFormatError("Missing version in workspace_info")
        
        # Check version compatibility
        version = workspace_info["version"]
        if not version.startswith("2."):
            logger.warning(f"IDW version {version} may not be fully compatible")
        
        # Validate items structure
        items = data["items"]
        if not isinstance(items, dict):
            raise IDWFormatError("Items section must be a dictionary")
    
    def _save_idw_data(self, data: Dict[str, Any]) -> None:
        """
        Atomically save IDW data with backup
        
        Args:
            data: IDW data to save
        """
        if self.mode == "read":
            raise PermissionError("Cannot save in read-only mode")
        
        # Update modification timestamp
        data["workspace_info"]["last_modified"] = datetime.now(timezone.utc).isoformat()
        
        with IDWFileLock(self.idw_path):
            # Create backup if original exists
            backup_path = self.idw_path.with_suffix('.bak')
            if self.idw_path.exists():
                shutil.copy2(self.idw_path, backup_path)
            
            # Write to temporary file first
            temp_path = self.idw_path.with_suffix('.tmp')
            
            try:
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                # Atomic move
                if os.name == 'nt':  # Windows
                    if self.idw_path.exists():
                        self.idw_path.unlink()
                shutil.move(str(temp_path), str(self.idw_path))
                
                # Update cache
                self._data_cache = data
                self._cache_timestamp = self.idw_path.stat().st_mtime
                
                logger.debug(f"Successfully saved IDW file: {self.idw_path}")
                
            except Exception as e:
                # Clean up temp file
                if temp_path.exists():
                    temp_path.unlink()
                raise IDWFormatError(f"Failed to save IDW file: {e}")
    
    def add_item(self, item: IDWItem) -> bool:
        """
        Add or update an IDW item atomically
        
        Args:
            item: IDW item to add/update
            
        Returns:
            True if successful
        """
        with self._lock:
            data = self._load_idw_data()
            
            # Convert item to dictionary format with proper enum handling
            item_dict = {
                "original_file": item.original_file,
                "display_file": item.display_file,
                "description": item.description,
                "metadata": self._serialize_dataclass(item.metadata) if item.metadata else {},
                "processing_info": self._serialize_dataclass(item.processing_info) if item.processing_info else {},
                "user_modifications": self._serialize_dataclass(item.user_modifications) if item.user_modifications else {}
            }
            
            # Add item
            was_new = item.item_id not in data["items"]
            data["items"][item.item_id] = item_dict
            
            # Update progress counters
            if was_new:
                data["workflow_progress"]["total_files"] = len(data["items"])
            
            # Update completion count
            completed_count = sum(1 for item_data in data["items"].values() 
                                if item_data.get("processing_info", {}).get("status") == ProcessingStatus.COMPLETED.value)
            data["workflow_progress"]["completed_files"] = completed_count
            
            # Save atomically
            self._save_idw_data(data)
            
            # Notify change callbacks
            self._notify_changes([item.item_id])
            
            return True
    
    def _serialize_dataclass(self, obj: Any) -> Dict[str, Any]:
        """
        Serialize a dataclass to dictionary with enum value conversion
        
        Args:
            obj: Dataclass object to serialize
            
        Returns:
            Dictionary with enum values converted to strings
        """
        if obj is None:
            return {}
            
        data = asdict(obj)
        
        # Convert enum values to their string values
        def convert_enums(item):
            if isinstance(item, dict):
                return {k: convert_enums(v) for k, v in item.items()}
            elif isinstance(item, list):
                return [convert_enums(v) for v in item]
            elif hasattr(item, 'value'):  # Enum check
                return item.value
            else:
                return item
        
        return convert_enums(data)
    
    def mark_completed(self, item_id: str, description: str, 
                      processing_time_ms: Optional[int] = None,
                      metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Mark an item as completed atomically
        
        Args:
            item_id: Item identifier
            description: Generated description
            processing_time_ms: Processing time in milliseconds
            metadata: Additional metadata
            
        Returns:
            True if successful
        """
        with self._lock:
            data = self._load_idw_data()
            
            if item_id not in data["items"]:
                logger.warning(f"Attempted to mark non-existent item as completed: {item_id}")
                return False
            
            # Update item
            item_data = data["items"][item_id]
            item_data["description"] = description
            
            # Update processing info
            if "processing_info" not in item_data:
                item_data["processing_info"] = {}
            
            item_data["processing_info"].update({
                "status": ProcessingStatus.COMPLETED.value,
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "processing_time_ms": processing_time_ms
            })
            
            # Update metadata if provided
            if metadata:
                if "metadata" not in item_data:
                    item_data["metadata"] = {}
                item_data["metadata"].update(metadata)
            
            # Update progress
            completed_count = sum(1 for item in data["items"].values() 
                                if item.get("processing_info", {}).get("status") == ProcessingStatus.COMPLETED.value)
            data["workflow_progress"]["completed_files"] = completed_count
            data["workflow_progress"]["last_processed"] = item_id
            
            # Update batch statistics
            if processing_time_ms:
                self._update_processing_statistics(data, processing_time_ms)
            
            # Save atomically
            self._save_idw_data(data)
            
            # Notify change callbacks
            self._notify_changes([item_id])
            
            return True
    
    def mark_failed(self, item_id: str, error_message: str) -> bool:
        """
        Mark an item as failed atomically
        
        Args:
            item_id: Item identifier
            error_message: Error description
            
        Returns:
            True if successful
        """
        with self._lock:
            data = self._load_idw_data()
            
            if item_id not in data["items"]:
                logger.warning(f"Attempted to mark non-existent item as failed: {item_id}")
                return False
            
            # Update item
            item_data = data["items"][item_id]
            
            if "processing_info" not in item_data:
                item_data["processing_info"] = {}
            
            item_data["processing_info"].update({
                "status": ProcessingStatus.FAILED.value,
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "error_message": error_message
            })
            
            # Update progress
            failed_count = sum(1 for item in data["items"].values() 
                             if item.get("processing_info", {}).get("status") == ProcessingStatus.FAILED.value)
            data["workflow_progress"]["failed_files"] = failed_count
            
            # Update error statistics
            self._update_error_statistics(data, error_message)
            
            # Save atomically
            self._save_idw_data(data)
            
            # Notify change callbacks
            self._notify_changes([item_id])
            
            return True
    
    def get_resume_checkpoint(self) -> Optional[str]:
        """
        Get the next item to process for resume capability
        
        Returns:
            Item ID to resume from, or None if complete
        """
        data = self._load_idw_data()
        
        # Find first item that is not completed, failed, or skipped
        for item_id, item_data in data["items"].items():
            status = item_data.get("processing_info", {}).get("status", ProcessingStatus.NOT_STARTED.value)
            if status in [ProcessingStatus.NOT_STARTED.value, ProcessingStatus.PROCESSING.value]:
                return item_id
        
        return None
    
    def get_remaining_items(self) -> List[str]:
        """
        Get list of items that still need processing
        
        Returns:
            List of item IDs that need processing
        """
        data = self._load_idw_data()
        remaining = []
        
        for item_id, item_data in data["items"].items():
            status = item_data.get("processing_info", {}).get("status", ProcessingStatus.NOT_STARTED.value)
            if status in [ProcessingStatus.NOT_STARTED.value, ProcessingStatus.PROCESSING.value]:
                remaining.append(item_id)
        
        return remaining
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get current processing statistics
        
        Returns:
            Statistics dictionary
        """
        data = self._load_idw_data()
        return {
            "workflow_progress": data["workflow_progress"],
            "batch_statistics": data["batch_statistics"]
        }
    
    def _update_processing_statistics(self, data: Dict[str, Any], processing_time_ms: int) -> None:
        """Update processing time statistics"""
        stats = data["batch_statistics"]["processing_times"]
        
        # Update average (simple running average)
        current_avg = stats.get("average_ms", 0)
        completed_count = data["workflow_progress"]["completed_files"]
        
        if completed_count > 1:
            stats["average_ms"] = ((current_avg * (completed_count - 1)) + processing_time_ms) // completed_count
        else:
            stats["average_ms"] = processing_time_ms
        
        # Update min/max
        if stats.get("fastest_ms", 0) == 0 or processing_time_ms < stats["fastest_ms"]:
            stats["fastest_ms"] = processing_time_ms
        
        if processing_time_ms > stats.get("slowest_ms", 0):
            stats["slowest_ms"] = processing_time_ms
    
    def _update_error_statistics(self, data: Dict[str, Any], error_message: str) -> None:
        """Update error statistics"""
        errors = data["batch_statistics"]["errors"]
        
        # Categorize error
        error_type = "unknown"
        error_msg_lower = error_message.lower()
        
        if "timeout" in error_msg_lower:
            error_type = "timeout"
        elif "memory" in error_msg_lower:
            error_type = "memory"
        elif "connection" in error_msg_lower:
            error_type = "connection"
        elif "file" in error_msg_lower and ("not found" in error_msg_lower or "missing" in error_msg_lower):
            error_type = "file_not_found"
        elif "permission" in error_msg_lower:
            error_type = "permission"
        
        errors[error_type] = errors.get(error_type, 0) + 1
    
    def add_change_callback(self, callback: Callable[[List[str]], None]) -> None:
        """
        Add callback for live monitoring of changes
        
        Args:
            callback: Function to call when items change
        """
        self._change_callbacks.append(callback)
    
    def _notify_changes(self, changed_items: List[str]) -> None:
        """Notify all change callbacks of updates"""
        for callback in self._change_callbacks:
            try:
                callback(changed_items)
            except Exception as e:
                logger.warning(f"Error in change callback: {e}")
    
    def start_monitoring(self, poll_interval: float = 1.0) -> None:
        """
        Start monitoring file for changes (for live updates)
        
        Args:
            poll_interval: How often to check for changes in seconds
        """
        if self._monitoring:
            return
        
        self._monitoring = True
        
        def monitor_loop():
            last_mtime = 0
            while self._monitoring:
                try:
                    if self.idw_path.exists():
                        current_mtime = self.idw_path.stat().st_mtime
                        if current_mtime > last_mtime:
                            # File changed, reload and notify
                            self._data_cache = None  # Force reload
                            self._load_idw_data(use_cache=False)
                            
                            # For now, notify that all items may have changed
                            # In the future, we could be more specific
                            data = self._load_idw_data()
                            all_items = list(data["items"].keys())
                            self._notify_changes(all_items)
                            
                            last_mtime = current_mtime
                    
                    time.sleep(poll_interval)
                except Exception as e:
                    logger.warning(f"Error in monitoring loop: {e}")
                    time.sleep(poll_interval)
        
        # Start monitoring in background thread
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
    
    def stop_monitoring(self) -> None:
        """Stop monitoring file for changes"""
        self._monitoring = False
    
    def close(self) -> None:
        """Clean up resources"""
        self.stop_monitoring()
        self._change_callbacks.clear()
        self._data_cache = None