#!/usr/bin/env python3
"""
Workspace Manager for ImageDescriber

Handles workspace directory structure, naming, and file management.
Default structure:
  ~/Documents/ImageDescriptionToolkit/workspaces/           - IDW workspace files
  ~/Documents/ImageDescriptionToolkit/WorkSpaceFiles/       - Actual image/data files
"""

import sys
import re
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime


def get_default_workspaces_root() -> Path:
    """
    Get platform-appropriate default workspace root directory.
    
    Returns:
        Path to workspaces directory (where .idw files are saved)
    """
    if sys.platform == 'win32':
        # Windows: ~\Documents\ImageDescriptionToolkit\workspaces
        return Path.home() / "Documents" / "ImageDescriptionToolkit" / "workspaces"
    elif sys.platform == 'darwin':
        # macOS: ~/Documents/ImageDescriptionToolkit/workspaces
        return Path.home() / "Documents" / "ImageDescriptionToolkit" / "workspaces"
    else:
        # Linux: ~/Documents/ImageDescriptionToolkit/workspaces or ~/.local/share/IDT/workspaces
        docs = Path.home() / "Documents"
        if docs.exists():
            return docs / "ImageDescriptionToolkit" / "workspaces"
        return Path.home() / ".local" / "share" / "IDT" / "workspaces"


def get_workspace_files_root() -> Path:
    """
    Get workspace files storage root (where images/data are stored).
    
    Returns:
        Path to WorkSpaceFiles directory
    """
    return get_default_workspaces_root().parent / "WorkSpaceFiles"


def get_next_untitled_name(workspace_root: Optional[Path] = None) -> str:
    """
    Get next available Untitled workspace name (Untitled, Untitled 1, Untitled 2, etc.).
    
    Args:
        workspace_root: Root directory to check for existing Untitled workspaces
                       (defaults to get_default_workspaces_root())
    
    Returns:
        Next available Untitled name (e.g., "Untitled", "Untitled 1", "Untitled 2")
    """
    if workspace_root is None:
        workspace_root = get_default_workspaces_root()
    
    workspace_root.mkdir(parents=True, exist_ok=True)
    
    # Check for existing Untitled workspaces
    existing_untitled = []
    for file in workspace_root.glob("Untitled*.idw"):
        name = file.stem  # Get filename without .idw extension
        existing_untitled.append(name)
    
    # Also check WorkSpaceFiles directory for Untitled folders
    files_root = get_workspace_files_root()
    if files_root.exists():
        for folder in files_root.glob("Untitled*"):
            if folder.is_dir():
                existing_untitled.append(folder.name)
    
    # Parse existing numbers
    existing_numbers = set()
    for name in existing_untitled:
        if name == "Untitled":
            existing_numbers.add(0)
        else:
            # Match "Untitled 1", "Untitled 2", etc.
            match = re.match(r'^Untitled\s+(\d+)$', name)
            if match:
                existing_numbers.add(int(match.group(1)))
    
    # Find next available number
    if 0 not in existing_numbers:
        return "Untitled"
    
    # Find first gap in sequence
    counter = 1
    while counter in existing_numbers:
        counter += 1
    
    return f"Untitled {counter}"


def propose_workspace_name_from_url(url: str) -> str:
    """
    Generate workspace name from URL with timestamp.
    
    Args:
        url: URL to generate name from
    
    Returns:
        Sanitized workspace name (e.g., "nytimes_20260211_143025")
    """
    from urllib.parse import urlparse
    
    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path
    domain = domain.replace('www.', '').replace('https://', '').replace('http://', '')
    
    # Take first part of domain (e.g., "nytimes.com" -> "nytimes")
    domain = domain.split('/')[0].split('.')[0]
    
    # Sanitize for filename
    safe_name = re.sub(r'[^\w\-]', '_', domain)
    safe_name = safe_name.strip('_')
    
    # Add date and time suffix for uniqueness (allows multiple downloads per day)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    return f"{safe_name}_{timestamp}"


def propose_workspace_name_from_directory(directory_path: Path) -> str:
    """
    Generate workspace name from directory path.
    
    Args:
        directory_path: Directory to generate name from
    
    Returns:
        Sanitized workspace name
    """
    # Use last component of path
    name = directory_path.name
    
    # Sanitize for filename
    safe_name = re.sub(r'[^\w\-]', '_', name)
    safe_name = safe_name.strip('_')
    
    # Limit length
    if len(safe_name) > 50:
        safe_name = safe_name[:50]
    
    return safe_name


def create_workspace_structure(workspace_name: str) -> Tuple[Path, Path]:
    """
    Create workspace directory structure.
    
    Args:
        workspace_name: Name of the workspace (without .idw extension)
    
    Returns:
        Tuple of (workspace_file_path, workspace_data_directory)
    """
    workspace_root = get_default_workspaces_root()
    files_root = get_workspace_files_root()
    
    # Create directories
    workspace_root.mkdir(parents=True, exist_ok=True)
    files_root.mkdir(parents=True, exist_ok=True)
    
    # Workspace file path
    workspace_file = workspace_root / f"{workspace_name}.idw"
    
    # Workspace data directory
    workspace_data_dir = files_root / workspace_name
    workspace_data_dir.mkdir(parents=True, exist_ok=True)
    
    return workspace_file, workspace_data_dir


def is_untitled_workspace(workspace_name: str) -> bool:
    """
    Check if workspace name is an Untitled workspace.
    
    Args:
        workspace_name: Workspace name to check
    
    Returns:
        True if Untitled workspace, False otherwise
    """
    if workspace_name == "Untitled":
        return True
    return bool(re.match(r'^Untitled\s+\d+$', workspace_name))


def sanitize_workspace_name(name: str) -> str:
    """
    Sanitize workspace name for filesystem use.
    
    Args:
        name: Proposed workspace name
    
    Returns:
        Sanitized name safe for filesystem
    """
    # Remove invalid characters
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', name)
    
    # Remove leading/trailing whitespace and dots
    safe_name = safe_name.strip(' .')
    
    # Limit length
    if len(safe_name) > 100:
        safe_name = safe_name[:100]
    
    # Ensure not empty
    if not safe_name:
        safe_name = "workspace"
    
    return safe_name


def get_workspace_files_directory(workspace_file_path: Path) -> Path:
    """
    Get the WorkSpaceFiles directory for a given workspace file.
    
    Args:
        workspace_file_path: Path to .idw workspace file
    
    Returns:
        Path to corresponding WorkSpaceFiles directory
    """
    workspace_name = workspace_file_path.stem  # Remove .idw extension
    files_root = get_workspace_files_root()
    return files_root / workspace_name
