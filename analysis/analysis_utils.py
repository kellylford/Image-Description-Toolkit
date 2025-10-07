#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Common utilities for analysis scripts.
"""

from pathlib import Path


def get_safe_filename(filepath: Path) -> Path:
    """
    Get a safe filename that doesn't overwrite existing files.
    If file exists, adds _1, _2, etc. to the filename.
    
    Args:
        filepath: The desired output file path
        
    Returns:
        A Path object that won't overwrite existing files
        
    Example:
        >>> get_safe_filename(Path("output.csv"))
        Path("output.csv")  # if doesn't exist
        
        >>> get_safe_filename(Path("output.csv"))
        Path("output_1.csv")  # if output.csv exists
    """
    if not filepath.exists():
        return filepath
    
    # Split name and extension
    stem = filepath.stem
    suffix = filepath.suffix
    parent = filepath.parent
    
    # Try numbered versions
    counter = 1
    while True:
        new_path = parent / f"{stem}_{counter}{suffix}"
        if not new_path.exists():
            return new_path
        counter += 1
        
        # Safety limit to prevent infinite loop
        if counter > 9999:
            raise ValueError(f"Too many existing files with base name: {stem}")


def ensure_directory(dirpath: Path) -> Path:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        dirpath: The directory path to create
        
    Returns:
        The directory path
    """
    dirpath.mkdir(parents=True, exist_ok=True)
    return dirpath
