#!/usr/bin/env python3
"""
Workflow Utilities

Shared utilities for the Image Description Toolkit workflow system.
Provides common functionality for path management, configuration, and logging
across all workflow steps.
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Union


class WorkflowConfig:
    """Manages workflow configuration and path resolution"""
    
    def __init__(self, config_file: str = "workflow_config.json"):
        """
        Initialize workflow configuration
        
        Args:
            config_file: Path to workflow configuration file
        """
        self.config_file = config_file
        self.config = self.load_config()
        self._base_output_dir = None
        
    def load_config(self) -> Dict[str, Any]:
        """Load workflow configuration from JSON file"""
        try:
            config_path = Path(self.config_file)
            if not config_path.is_absolute():
                script_dir = Path(__file__).parent
                config_path = script_dir / self.config_file
            
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # Return default config if file doesn't exist
                return self.get_default_config()
                
        except Exception as e:
            # Use basic logging here since we don't have access to the WorkflowLogger yet
            import logging
            logging.warning(f"Could not load workflow config: {e}")
            return self.get_default_config()
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get default workflow configuration"""
        return {
            "workflow": {
                "base_output_dir": "workflow_output",
                "preserve_structure": True,
                "cleanup_intermediate": False,
                "steps": {
                    "video_extraction": {"enabled": True, "output_subdir": "extracted_frames"},
                    "image_conversion": {"enabled": True, "output_subdir": "converted_images"},
                    "image_description": {"enabled": True, "output_subdir": "descriptions"},
                    "html_generation": {"enabled": True, "output_subdir": "html_reports"}
                }
            },
            "file_patterns": {
                "videos": [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v"],
                "images": [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"],
                "heic": [".heic", ".heif"],
                "descriptions": ["image_descriptions.txt"]
            }
        }
    
    @property
    def base_output_dir(self) -> Path:
        """Get the base output directory path"""
        if self._base_output_dir is None:
            base_dir = self.config.get("workflow", {}).get("base_output_dir", "workflow_output")
            self._base_output_dir = Path(base_dir).resolve()
        return self._base_output_dir
    
    def set_base_output_dir(self, path: Union[str, Path]) -> None:
        """Set a custom base output directory"""
        self._base_output_dir = Path(path).resolve()
    
    def get_step_output_dir(self, step_name: str, create: bool = True) -> Path:
        """
        Get output directory for a specific workflow step
        
        Args:
            step_name: Name of the workflow step
            create: Whether to create the directory if it doesn't exist
            
        Returns:
            Path to the step's output directory
        """
        step_config = self.config.get("workflow", {}).get("steps", {}).get(step_name, {})
        subdir = step_config.get("output_subdir", step_name)
        
        output_dir = self.base_output_dir / subdir
        
        if create:
            output_dir.mkdir(parents=True, exist_ok=True)
            
        return output_dir
    
    def is_step_enabled(self, step_name: str) -> bool:
        """Check if a workflow step is enabled"""
        return self.config.get("workflow", {}).get("steps", {}).get(step_name, {}).get("enabled", True)
    
    def get_step_config(self, step_name: str) -> Dict[str, Any]:
        """Get configuration for a specific step"""
        return self.config.get("workflow", {}).get("steps", {}).get(step_name, {})
    
    def get_file_patterns(self, pattern_type: str) -> List[str]:
        """Get file patterns for a specific type"""
        return self.config.get("file_patterns", {}).get(pattern_type, [])


class WorkflowLogger:
    """Centralized logging for workflow operations"""
    
    def __init__(self, name: str = "workflow", log_level: str = "INFO", log_to_file: bool = True, base_output_dir: Optional[Path] = None):
        """
        Initialize workflow logger
        
        Args:
            name: Logger name
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
            log_to_file: Whether to log to file
            base_output_dir: Base output directory for log files (if None, uses workflow_output)
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handler
        if log_to_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Create logs directory in base_output_dir or workflow_output if it doesn't exist
            if base_output_dir:
                logs_dir = base_output_dir / "logs"
            else:
                logs_dir = Path("workflow_output") / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)
            log_filename = logs_dir / f"workflow_{timestamp}.log"
            file_handler = logging.FileHandler(log_filename, encoding='utf-8')
            file_handler.setLevel(getattr(logging, log_level.upper()))
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
            
            self.logger.info(f"Workflow log file: {log_filename.absolute()}")
    
    def info(self, message: str) -> None:
        """Log info message"""
        self.logger.info(message)
    
    def warning(self, message: str) -> None:
        """Log warning message"""
        self.logger.warning(message)
    
    def error(self, message: str) -> None:
        """Log error message"""
        self.logger.error(message)
    
    def debug(self, message: str) -> None:
        """Log debug message"""
        self.logger.debug(message)


class FileDiscovery:
    """Utilities for discovering and categorizing files"""
    
    def __init__(self, config: WorkflowConfig):
        self.config = config
    
    def find_files_by_type(self, directory: Path, file_type: str, recursive: bool = True) -> List[Path]:
        """
        Find files of a specific type in directory
        
        Args:
            directory: Directory to search
            file_type: Type of files to find (videos, images, heic, descriptions)
            recursive: Whether to search recursively
            
        Returns:
            List of file paths
        """
        patterns = self.config.get_file_patterns(file_type)
        if not patterns:
            return []
        
        files = []
        search_pattern = "**/*" if recursive else "*"
        
        for pattern in patterns:
            if recursive:
                files.extend(directory.rglob(f"*{pattern}"))
            else:
                files.extend(directory.glob(f"*{pattern}"))
        
        # Sort and remove duplicates
        return sorted(list(set(files)))
    
    def categorize_files(self, directory: Path, recursive: bool = True) -> Dict[str, List[Path]]:
        """
        Categorize all files in directory by type
        
        Args:
            directory: Directory to search
            recursive: Whether to search recursively
            
        Returns:
            Dictionary mapping file types to lists of paths
        """
        categories = {}
        
        for file_type in ["videos", "images", "heic", "descriptions"]:
            categories[file_type] = self.find_files_by_type(directory, file_type, recursive)
        
        return categories
    
    def get_relative_path_structure(self, file_path: Path, base_path: Path) -> Path:
        """
        Get relative path structure for preserving directory hierarchy
        
        Args:
            file_path: Full path to file
            base_path: Base directory path
            
        Returns:
            Relative path structure
        """
        try:
            return file_path.relative_to(base_path)
        except ValueError:
            # If file is not relative to base, just return filename
            return Path(file_path.name)


def create_workflow_paths(base_output_dir: Path, preserve_structure: bool = True) -> Dict[str, Path]:
    """
    Create standard workflow directory structure
    
    Args:
        base_output_dir: Base output directory
        preserve_structure: Whether to preserve input directory structure
        
    Returns:
        Dictionary mapping step names to their output directories
    """
    paths = {}
    
    # Standard workflow directories
    steps = [
        "extracted_frames",
        "converted_images", 
        "descriptions",
        "html_reports",
        "logs"
    ]
    
    for step in steps:
        step_dir = base_output_dir / step
        step_dir.mkdir(parents=True, exist_ok=True)
        paths[step] = step_dir
    
    return paths


def get_script_compatibility_args(script_name: str, workflow_config: WorkflowConfig, 
                                input_dir: Path, output_dir: Path) -> List[str]:
    """
    Generate command-line arguments for existing scripts to maintain compatibility
    
    Args:
        script_name: Name of the script to generate args for
        workflow_config: Workflow configuration
        input_dir: Input directory
        output_dir: Output directory for this step
        
    Returns:
        List of command-line arguments
    """
    args = []
    
    if script_name == "video_frame_extractor.py":
        args = [str(input_dir)]
        step_config = workflow_config.get_step_config("video_extraction")
        if "config_file" in step_config:
            args.extend(["--config", step_config["config_file"]])
    
    elif script_name == "ConvertImage.py":
        args = [str(input_dir)]
        args.extend(["--output", str(output_dir)])
        step_config = workflow_config.get_step_config("image_conversion")
        if "quality" in step_config:
            args.extend(["--quality", str(step_config["quality"])])
        if not step_config.get("keep_metadata", True):
            args.append("--no-metadata")
    
    elif script_name == "image_describer.py":
        args = [str(input_dir)]
        step_config = workflow_config.get_step_config("image_description")
        if "config_file" in step_config:
            args.extend(["--config", step_config["config_file"]])
        if "model" in step_config and step_config["model"]:
            args.extend(["--model", step_config["model"]])
        if "prompt_style" in step_config and step_config["prompt_style"]:
            args.extend(["--prompt-style", step_config["prompt_style"]])
    
    elif script_name == "descriptions_to_html.py":
        # This will be handled differently as it needs specific input file
        pass
    
    return args


def get_workflow_output_dir(script_name: str, fallback_dir: Optional[Path] = None) -> Optional[Path]:
    """
    Get workflow-consistent output directory for individual scripts
    
    Args:
        script_name: Name of the script requesting output directory
        fallback_dir: Fallback directory if workflow config not found
        
    Returns:
        Path to use for output, or None if should use script default
    """
    try:
        # Load workflow config if it exists
        config = WorkflowConfig()
        
        # Map script names to workflow steps
        step_mapping = {
            "video_frame_extractor.py": "video_extraction",
            "ConvertImage.py": "image_conversion", 
            "image_describer.py": "image_description",
            "descriptions_to_html.py": "html_generation"
        }
        
        step_name = step_mapping.get(script_name)
        if step_name:
            # Get workflow output directory
            output_dir = config.get_step_output_dir(step_name, create=False)
            
            # Only use workflow dir if base workflow directory exists or fallback is provided
            if config.base_output_dir.exists() or fallback_dir:
                return output_dir
    
    except Exception:
        # If anything goes wrong, fall back to script defaults
        pass
    
    return fallback_dir


