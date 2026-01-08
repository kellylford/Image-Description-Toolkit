"""
Shared utilities for IDT wxPython applications.

This package provides common functionality across all GUI applications:
- Path resolution (frozen vs development mode)
- Config file management with backup/restore
- Modified state tracking for document windows
- Standardized dialogs (file, message, about)
- Accessible widgets for VoiceOver compatibility
"""

from .wx_common import (
    # Path resolution
    get_base_directory,
    find_file,
    find_scripts_directory,
    find_config_file,
    
    # Config management
    ConfigManager,
    
    # Modified state tracking
    ModifiedStateMixin,
    
    # Dialogs
    show_error,
    show_warning,
    show_info,
    ask_yes_no,
    ask_yes_no_cancel,
    open_file_dialog,
    save_file_dialog,
    select_directory_dialog,
    show_about_dialog,
    
    # Utilities
    sanitize_filename,
    format_timestamp,
    get_app_version,
)

__all__ = [
    # Path resolution
    'get_base_directory',
    'find_file',
    'find_scripts_directory',
    'find_config_file',
    
    # Config management
    'ConfigManager',
    
    # Modified state tracking
    'ModifiedStateMixin',
    
    # Dialogs
    'show_error',
    'show_warning',
    'show_info',
    'ask_yes_no',
    'ask_yes_no_cancel',
    'open_file_dialog',
    'save_file_dialog',
    'select_directory_dialog',
    'show_about_dialog',
    
    # Utilities
    'sanitize_filename',
    'format_timestamp',
    'get_app_version',
]
