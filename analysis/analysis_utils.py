#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Common utilities for analysis scripts.
"""

import sys
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


def load_prompt_styles_from_config():
    """
    Load prompt styles dynamically from image_describer_config.json.
    
    Returns:
        List of lowercase prompt style names from the config file.
        Falls back to a default list if config cannot be loaded.
    """
    # Add parent directory to path for config_loader import
    current_dir = Path(__file__).parent
    parent_dir = current_dir.parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))
    
    try:
        from scripts.config_loader import load_json_config
        
        # Load the image describer config
        config, config_path, source = load_json_config('image_describer_config.json')
        
        # Extract prompt styles from prompt_variations
        if config and 'prompt_variations' in config:
            # Convert all keys to lowercase for case-insensitive matching
            prompt_styles = [key.lower() for key in config['prompt_variations'].keys()]
            return prompt_styles
    except Exception as e:
        # If anything goes wrong, fall back to a default list
        print(f"Warning: Could not load prompt styles from config: {e}")
    
    # Fallback list (this should match the most common prompt styles)
    return ['narrative', 'detailed', 'concise', 'technical', 'creative', 'colorful', 'artistic', 'simple']
