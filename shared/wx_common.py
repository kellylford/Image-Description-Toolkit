"""
Common utilities for IDT wxPython applications.

Provides standardized functionality for:
- Path resolution in frozen and development modes
- JSON config file management with backup/restore
- Modified state tracking for document-based windows
- Standardized dialogs (file, directory, message, about)
- Utility functions for timestamps and filename sanitization
"""

import wx
import wx.adv
import json
import shutil
import sys
import re
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from datetime import datetime


# ==================== PATH RESOLUTION ====================

def get_base_directory() -> Path:
    """
    Get the base directory of the application.
    
    In frozen mode (PyInstaller), returns the directory containing the executable.
    In development mode, returns the project root directory.
    
    Returns:
        Path: Base directory path
    """
    if getattr(sys, 'frozen', False):
        # Frozen mode - return exe directory
        return Path(sys.executable).parent
    else:
        # Development mode - assume we're in a subdirectory, go to parent
        # This works for scripts in viewer/, prompt_editor/, etc.
        return Path(__file__).parent.parent


def find_file(filename: str, search_dirs: List[Union[str, Path]] = None) -> Optional[Path]:
    """
    Find a file by searching multiple directories.
    
    Args:
        filename: Name of file to find
        search_dirs: List of directories to search (default: common locations)
        
    Returns:
        Path to file if found, None otherwise
    """
    if search_dirs is None:
        base = get_base_directory()
        search_dirs = [
            base,
            base / 'scripts',
            base / 'models',
            Path.cwd(),
        ]
    
    # Convert all to Path objects
    search_dirs = [Path(d) for d in search_dirs]
    
    for directory in search_dirs:
        if not directory.exists():
            continue
            
        file_path = directory / filename
        if file_path.exists() and file_path.is_file():
            return file_path
    
    return None


def find_scripts_directory() -> Optional[Path]:
    """
    Find the scripts directory in frozen or development mode.
    
    Returns:
        Path to scripts directory if found, None otherwise
    """
    base = get_base_directory()
    
    if getattr(sys, 'frozen', False):
        # Frozen mode - check for bundled scripts
        candidates = [
            Path(sys._MEIPASS) / 'scripts',  # PyInstaller temp directory
            base / 'scripts',                 # Next to exe
            base.parent / 'scripts',          # One level up
        ]
    else:
        # Development mode
        candidates = [
            base / 'scripts',
            base.parent / 'scripts',
        ]
    
    for path in candidates:
        if path.exists() and path.is_dir():
            return path
    
    return None


def find_config_file(filename: str) -> Optional[Path]:
    """
    Find a configuration file using standard search order.
    
    Search order:
    1. scripts/ directory (most common location)
    2. Base directory (exe directory or project root)
    3. Current working directory
    4. PyInstaller temp directory (frozen mode only)
    
    Args:
        filename: Config filename (e.g., 'image_describer_config.json')
        
    Returns:
        Path to config file if found, None otherwise
    """
    scripts_dir = find_scripts_directory()
    base_dir = get_base_directory()
    
    candidates = []
    
    # Add scripts directory if found
    if scripts_dir:
        candidates.append(scripts_dir / filename)
    
    # Add base directory
    candidates.append(base_dir / filename)
    
    # Add current directory
    candidates.append(Path.cwd() / filename)
    
    # In frozen mode, also check PyInstaller temp directory
    if getattr(sys, 'frozen', False):
        candidates.append(Path(sys._MEIPASS) / filename)
        candidates.append(Path(sys._MEIPASS) / 'scripts' / filename)
    
    # Return first existing file
    for path in candidates:
        if path.exists() and path.is_file():
            return path
    
    return None


# ==================== CONFIG MANAGEMENT ====================

class ConfigManager:
    """
    Manage JSON configuration files with backup/restore functionality.
    
    Features:
    - Load/save JSON configs with error handling
    - Automatic backup before save (.bak suffix)
    - Timestamp-based backups for archival
    - Get/set nested values by path
    - Restore from backup
    
    Example:
        config = ConfigManager(Path('config.json'))
        config.load()
        value = config.get_value(['section', 'key'], default='default')
        config.set_value(['section', 'key'], 'new_value')
        config.save()  # Creates config.json.bak automatically
    """
    
    def __init__(self, config_file: Path):
        """
        Initialize config manager.
        
        Args:
            config_file: Path to config JSON file
        """
        self.config_file = Path(config_file)
        self.config_data = {}
    
    def load(self) -> Dict[str, Any]:
        """
        Load configuration from file.
        
        Returns:
            Dict containing config data
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            json.JSONDecodeError: If config file is invalid JSON
        """
        if not self.config_file.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_file}")
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config_data = json.load(f)
            return self.config_data
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(
                f"Invalid JSON in config file: {self.config_file}",
                e.doc, e.pos
            )
    
    def save(self, create_backup: bool = True):
        """
        Save configuration to file.
        
        Args:
            create_backup: If True, create .bak file before saving
            
        Raises:
            IOError: If file cannot be written
        """
        # Create backup if requested and file exists
        if create_backup and self.config_file.exists():
            self.create_backup()
        
        # Ensure parent directory exists
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Save config
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise IOError(f"Failed to save config file: {e}")
    
    def create_backup(self, timestamp: bool = False) -> Path:
        """
        Create a backup of the config file.
        
        Args:
            timestamp: If True, append timestamp to backup name
            
        Returns:
            Path to backup file
        """
        if not self.config_file.exists():
            raise FileNotFoundError(f"Cannot backup non-existent file: {self.config_file}")
        
        if timestamp:
            # Create timestamped backup: config_backup_20260108_143022.json
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{self.config_file.stem}_backup_{timestamp_str}{self.config_file.suffix}"
            backup_path = self.config_file.parent / backup_name
        else:
            # Create simple .bak backup: config.json.bak
            backup_path = self.config_file.with_suffix(self.config_file.suffix + '.bak')
        
        shutil.copy2(self.config_file, backup_path)
        return backup_path
    
    def restore_backup(self, backup_file: Optional[Path] = None):
        """
        Restore configuration from backup.
        
        Args:
            backup_file: Path to backup file (default: use .bak file)
            
        Raises:
            FileNotFoundError: If backup file doesn't exist
        """
        if backup_file is None:
            backup_file = self.config_file.with_suffix(self.config_file.suffix + '.bak')
        
        backup_file = Path(backup_file)
        if not backup_file.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_file}")
        
        shutil.copy2(backup_file, self.config_file)
        self.load()  # Reload from restored file
    
    def get_value(self, path: List[str], default: Any = None) -> Any:
        """
        Get a value from nested config using path.
        
        Args:
            path: List of keys to traverse (e.g., ['section', 'subsection', 'key'])
            default: Default value if path doesn't exist
            
        Returns:
            Value at path, or default if not found
            
        Example:
            value = config.get_value(['model_settings', 'temperature'], default=0.7)
        """
        current = self.config_data
        
        for key in path:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        
        return current
    
    def set_value(self, path: List[str], value: Any):
        """
        Set a value in nested config using path.
        
        Creates intermediate dictionaries as needed.
        
        Args:
            path: List of keys to traverse (e.g., ['section', 'subsection', 'key'])
            value: Value to set
            
        Example:
            config.set_value(['model_settings', 'temperature'], 0.9)
        """
        if not path:
            raise ValueError("Path cannot be empty")
        
        current = self.config_data
        
        # Navigate to parent of target
        for key in path[:-1]:
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]
        
        # Set final value
        current[path[-1]] = value
    
    def get_data(self) -> Dict[str, Any]:
        """Get the entire config data dictionary."""
        return self.config_data
    
    def set_data(self, data: Dict[str, Any]):
        """Set the entire config data dictionary."""
        self.config_data = data


# ==================== MODIFIED STATE TRACKING ====================

class ModifiedStateMixin:
    """
    Mixin class for tracking modified state in document-based windows.
    
    Provides:
    - modified flag tracking
    - Window title updates with * indicator
    - Unsaved changes confirmation dialog
    
    Usage:
        class MyFrame(wx.Frame, ModifiedStateMixin):
            def __init__(self):
                wx.Frame.__init__(self, None, title="My App")
                ModifiedStateMixin.__init__(self)
                self.original_title = "My App"
                
            def on_edit(self, event):
                self.mark_modified()
                
            def on_save(self, event):
                # ... save logic ...
                self.clear_modified()
    """
    
    def __init__(self):
        """Initialize modified state tracking."""
        self.modified = False
        self.original_title = ""
    
    def mark_modified(self):
        """Mark document as modified and update window title."""
        if not self.modified:
            self.modified = True
            self._update_title()
    
    def clear_modified(self):
        """Clear modified flag and update window title."""
        if self.modified:
            self.modified = False
            self._update_title()
    
    def _update_title(self):
        """Update window title to reflect modified state."""
        if hasattr(self, 'original_title') and self.original_title:
            title = self.original_title
        else:
            title = self.GetTitle().rstrip(' *')
            self.original_title = title
        
        if self.modified:
            self.SetTitle(f"{title} *")
        else:
            self.SetTitle(title)
    
    def confirm_unsaved_changes(self, parent=None) -> bool:
        """
        Show confirmation dialog if there are unsaved changes.
        
        Args:
            parent: Parent window (default: self)
            
        Returns:
            True if OK to proceed (saved or discarded changes)
            False if cancelled
        """
        if not self.modified:
            return True
        
        if parent is None:
            parent = self
        
        result = ask_yes_no_cancel(
            parent,
            "You have unsaved changes. Save before closing?",
            "Unsaved Changes"
        )
        
        if result == wx.ID_YES:
            # Call save method if it exists
            if hasattr(self, 'on_save'):
                self.on_save(None)
                return True
            elif hasattr(self, 'save'):
                self.save()
                return True
            else:
                return True
        elif result == wx.ID_NO:
            return True
        else:  # CANCEL
            return False


# ==================== DIALOGS ====================

def show_error(parent, message: str, title: str = "Error"):
    """
    Show an error message dialog.
    
    Args:
        parent: Parent window
        message: Error message to display
        title: Dialog title
    """
    wx.MessageBox(message, title, wx.OK | wx.ICON_ERROR, parent)


def show_warning(parent, message: str, title: str = "Warning"):
    """
    Show a warning message dialog.
    
    Args:
        parent: Parent window
        message: Warning message to display
        title: Dialog title
    """
    wx.MessageBox(message, title, wx.OK | wx.ICON_WARNING, parent)


def show_info(parent, message: str, title: str = "Information"):
    """
    Show an information message dialog.
    
    Args:
        parent: Parent window
        message: Info message to display
        title: Dialog title
    """
    wx.MessageBox(message, title, wx.OK | wx.ICON_INFORMATION, parent)


def ask_yes_no(parent, message: str, title: str = "Confirm") -> bool:
    """
    Show a yes/no confirmation dialog.
    
    Args:
        parent: Parent window
        message: Question to ask
        title: Dialog title
        
    Returns:
        True if user clicked Yes, False if No
    """
    result = wx.MessageBox(message, title, wx.YES_NO | wx.ICON_QUESTION, parent)
    return result == wx.YES


def ask_yes_no_cancel(parent, message: str, title: str = "Confirm") -> int:
    """
    Show a yes/no/cancel confirmation dialog.
    
    Args:
        parent: Parent window
        message: Question to ask
        title: Dialog title
        
    Returns:
        wx.ID_YES, wx.ID_NO, or wx.ID_CANCEL
    """
    dlg = wx.MessageDialog(parent, message, title, wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION)
    result = dlg.ShowModal()
    dlg.Destroy()
    return result


def open_file_dialog(parent, message: str = "Open File", wildcard: str = "All files (*.*)|*.*",
                     default_dir: str = "", default_file: str = "") -> Optional[str]:
    """
    Show a file open dialog.
    
    Args:
        parent: Parent window
        message: Dialog title
        wildcard: File filter wildcard
        default_dir: Default directory
        default_file: Default filename
        
    Returns:
        Selected file path, or None if cancelled
        
    Example:
        path = open_file_dialog(self, "Open Config",
                               wildcard="JSON files (*.json)|*.json")
    """
    dlg = wx.FileDialog(
        parent, message,
        defaultDir=default_dir,
        defaultFile=default_file,
        wildcard=wildcard,
        style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
    )
    
    if dlg.ShowModal() == wx.ID_OK:
        path = dlg.GetPath()
        dlg.Destroy()
        return path
    
    dlg.Destroy()
    return None


def save_file_dialog(parent, message: str = "Save File", wildcard: str = "All files (*.*)|*.*",
                     default_dir: str = "", default_file: str = "") -> Optional[str]:
    """
    Show a file save dialog.
    
    Args:
        parent: Parent window
        message: Dialog title
        wildcard: File filter wildcard
        default_dir: Default directory
        default_file: Default filename
        
    Returns:
        Selected file path, or None if cancelled
        
    Example:
        path = save_file_dialog(self, "Save Config",
                               wildcard="JSON files (*.json)|*.json",
                               default_file="config.json")
    """
    dlg = wx.FileDialog(
        parent, message,
        defaultDir=default_dir,
        defaultFile=default_file,
        wildcard=wildcard,
        style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
    )
    
    if dlg.ShowModal() == wx.ID_OK:
        path = dlg.GetPath()
        dlg.Destroy()
        return path
    
    dlg.Destroy()
    return None


def select_directory_dialog(parent, message: str = "Select Directory",
                            default_path: str = "") -> Optional[str]:
    """
    Show a directory selection dialog.
    
    Args:
        parent: Parent window
        message: Dialog title
        default_path: Default directory path
        
    Returns:
        Selected directory path, or None if cancelled
    """
    dlg = wx.DirDialog(
        parent, message,
        defaultPath=default_path,
        style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST
    )
    
    if dlg.ShowModal() == wx.ID_OK:
        path = dlg.GetPath()
        dlg.Destroy()
        return path
    
    dlg.Destroy()
    return None


def show_about_dialog(parent, app_name: str, version: str,
                     description: str, developers: List[str] = None,
                     website: str = ""):
    """
    Show a standardized About dialog.
    
    Args:
        parent: Parent window
        app_name: Application name
        version: Version string
        description: App description
        developers: List of developer names
        website: Website URL
        
    Example:
        show_about_dialog(self, "MyApp", "1.0.0",
                         "An amazing application",
                         developers=["John Doe"],
                         website="https://example.com")
    """
    info = wx.adv.AboutDialogInfo()
    info.SetName(app_name)
    info.SetVersion(version)
    info.SetDescription(description)
    
    if developers:
        for dev in developers:
            info.AddDeveloper(dev)
    
    if website:
        info.SetWebSite(website)
    
    # Add standard items
    info.SetLicence("Licensed under the terms of the project license.")
    
    wx.adv.AboutBox(info)


# ==================== UTILITIES ====================

def sanitize_filename(filename: str, preserve_case: bool = True) -> str:
    """
    Remove invalid characters from filename.
    
    Removes characters that are invalid in filenames across platforms:
    - Windows: < > : " / \\ | ? *
    - All: control characters
    
    Preserves: alphanumeric, underscore, hyphen, period
    
    Args:
        filename: Filename to sanitize
        preserve_case: If True, preserve case; if False, lowercase
        
    Returns:
        Sanitized filename
        
    Example:
        sanitize_filename("My File: (1).txt")  # "MyFile1.txt"
    """
    # Remove invalid characters
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', filename)
    
    # Replace spaces and other whitespace with nothing (or could use '_')
    cleaned = re.sub(r'\s+', '', cleaned)
    
    # Remove any remaining non-alphanumeric except . - _
    cleaned = re.sub(r'[^a-zA-Z0-9._-]', '', cleaned)
    
    if not preserve_case:
        cleaned = cleaned.lower()
    
    # Ensure not empty
    if not cleaned:
        cleaned = "file"
    
    return cleaned


def format_timestamp(dt: Union[datetime, str, None], include_seconds: bool = False) -> str:
    """
    Format timestamp consistently across all apps.
    
    Format: M/D/YYYY H:MMP (no leading zeros, A/P suffix)
    Examples: "3/25/2025 7:35P", "10/16/2025 8:03A"
    
    Args:
        dt: datetime object, ISO string, or None
        include_seconds: If True, include seconds in output
        
    Returns:
        Formatted timestamp string, or empty string if dt is None
    """
    if dt is None:
        return ""
    
    # Convert string to datetime if needed
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except (ValueError, TypeError):
            return dt  # Return original if can't parse
    
    # Format date: M/D/YYYY
    date_str = f"{dt.month}/{dt.day}/{dt.year}"
    
    # Format time: H:MM[SS]P/A
    hour_12 = dt.hour % 12
    if hour_12 == 0:
        hour_12 = 12
    
    am_pm = "A" if dt.hour < 12 else "P"
    
    if include_seconds:
        time_str = f"{hour_12}:{dt.minute:02d}:{dt.second:02d}{am_pm}"
    else:
        time_str = f"{hour_12}:{dt.minute:02d}{am_pm}"
    
    return f"{date_str} {time_str}"


def get_app_version() -> str:
    """
    Get application version from VERSION file or versioning module.
    
    Search order:
    1. scripts/versioning.py get_full_version()
    2. VERSION file in base directory
    3. Default "1.0.0"
    
    Returns:
        Version string
    """
    # Try versioning module first
    try:
        scripts_dir = find_scripts_directory()
        if scripts_dir:
            sys.path.insert(0, str(scripts_dir))
            from versioning import get_full_version
            return get_full_version()
    except (ImportError, Exception):
        pass
    
    # Try VERSION file
    try:
        version_file = find_file('VERSION')
        if version_file:
            return version_file.read_text().strip()
    except Exception:
        pass
    
    # Default
    return "1.0.0"
