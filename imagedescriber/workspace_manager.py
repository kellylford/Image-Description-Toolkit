#!/usr/bin/env python3
"""
Workspace Manager for ImageDescriber

Naming and path utilities for .idtw workspace bundles.
"""

import sys
import re
from pathlib import Path
from typing import Optional
from datetime import datetime


def get_default_workspaces_root() -> Path:
    """Return platform-appropriate default directory for suggesting bundle locations.

    Matches the CLI default (~/Documents/idt) so bundles are always local,
    never on network shares next to the source files.
    """
    docs = Path.home() / "Documents"
    return docs / "idt"


def get_next_untitled_name(workspace_root: Optional[Path] = None) -> str:
    """Return the next available 'Untitled' name, checking for .idtw bundles."""
    if workspace_root is None:
        workspace_root = get_default_workspaces_root()

    workspace_root.mkdir(parents=True, exist_ok=True)

    existing_numbers = set()
    for bundle in workspace_root.glob("Untitled*.idtw"):
        name = bundle.stem
        if name == "Untitled":
            existing_numbers.add(0)
        else:
            match = re.match(r'^Untitled\s+(\d+)$', name)
            if match:
                existing_numbers.add(int(match.group(1)))

    if 0 not in existing_numbers:
        return "Untitled"

    counter = 1
    while counter in existing_numbers:
        counter += 1
    return f"Untitled {counter}"


def propose_workspace_name_from_url(url: str) -> str:
    """Generate a workspace name from a URL."""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path
    domain = domain.replace('www.', '').split('/')[0].split('.')[0]
    safe_name = re.sub(r'[^\w\-]', '_', domain).strip('_')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{safe_name}_{timestamp}"


def propose_workspace_name_from_directory(directory_path: Path) -> str:
    """Generate a workspace name from a directory path."""
    name = directory_path.name
    safe_name = re.sub(r'[^\w\-]', '_', name).strip('_')
    return safe_name[:50] if len(safe_name) > 50 else safe_name


def is_untitled_workspace(workspace_name: str) -> bool:
    """True if the name matches the Untitled / Untitled N pattern."""
    if workspace_name == "Untitled":
        return True
    return bool(re.match(r'^Untitled\s+\d+$', workspace_name))


def sanitize_workspace_name(name: str) -> str:
    """Return a filesystem-safe workspace name."""
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', name).strip(' .')
    safe_name = safe_name[:100] if len(safe_name) > 100 else safe_name
    return safe_name or "workspace"
