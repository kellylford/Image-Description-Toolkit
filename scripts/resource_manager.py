"""
Resource Manager for IDT Executable
Handles config and resource loading for both development and PyInstaller contexts
"""
import os
import sys
from pathlib import Path

def get_resource_path(relative_path: str) -> Path:
    """
    Get absolute path to resource, works for both development and PyInstaller
    
    Args:
        relative_path: Path relative to the application root
        
    Returns:
        Absolute path to the resource
    """
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller executable
        # For outputs, always use relative to executable directory
        exe_dir = Path(sys.executable).parent
        resource_path = exe_dir / relative_path
        
        # For inputs, try bundle first, then relative to executable
        if not resource_path.exists() and not relative_path.startswith(('analysis/results', 'output', 'dist')):
            base_path = Path(sys._MEIPASS)
            bundled_path = base_path / relative_path
            if bundled_path.exists():
                resource_path = bundled_path
            
    else:
        # Running as Python script (development)
        base_path = Path(__file__).parent.parent
        resource_path = base_path / relative_path
        
    return resource_path

def load_config(config_name: str = "image_describer_config.json"):
    """
    Load configuration file with executable-aware path resolution
    
    Args:
        config_name: Name of config file
        
    Returns:
        Path to config file
    """
    # Try multiple locations in order of preference
    search_paths = [
        f"scripts/{config_name}",
        config_name,
        f"config/{config_name}"
    ]
    
    for search_path in search_paths:
        config_path = get_resource_path(search_path)
        if config_path.exists():
            return config_path
            
    # If not found, provide helpful error
    exe_context = "executable" if getattr(sys, 'frozen', False) else "development"
    raise FileNotFoundError(
        f"Config file '{config_name}' not found in {exe_context} context. "
        f"Searched: {[str(get_resource_path(p)) for p in search_paths]}"
    )

def get_executable_info():
    """Get information about current execution context"""
    return {
        "is_executable": getattr(sys, 'frozen', False),
        "executable_path": sys.executable if getattr(sys, 'frozen', False) else None,
        "base_path": get_resource_path(""),
        "python_version": sys.version,
        "platform": sys.platform
    }