#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Image Description Toolkit - Workflow Orchestrator

This script provides a complete workflow that can process videos and images
through the entire pipeline: video frame extraction, image conversion, 
AI description generation, and HTML report creation.

The workflow maintains compatibility with all existing scripts while providing
a streamlined interface for end-to-end processing.

Usage:
    python workflow.py <input_source> [options]
    
Examples:
    # Describe images in a local directory
    python workflow.py photos
    python workflow.py /path/to/media --model llava:7b
    
    # Download and describe images from a website
    python workflow.py example.com
    python workflow.py https://mywebsite.com --max-images 20
    python workflow.py --download https://example.com
    
    # Advanced options
    python workflow.py photos --steps describe,html --timeout 120
"""

import sys
import os
import argparse
import subprocess
import shutil
import shlex
from urllib.parse import urlparse

# Set UTF-8 encoding for console output on Windows
if sys.platform.startswith('win'):
    import codecs
    # Fix for PyInstaller executable - only detach if method exists
    if hasattr(sys.stdout, 'detach'):
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    if hasattr(sys.stderr, 'detach'):
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())
import logging
import json
import platform
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Import our workflow utilities
from workflow_utils import (
    WorkflowConfig, WorkflowLogger, FileDiscovery, create_workflow_paths,
    get_path_identifier_2_components, save_workflow_metadata, load_workflow_metadata,
    create_workflow_helper_files
)
from image_describer import get_default_prompt_style, get_default_model
try:
    from config_loader import load_json_config
except ImportError:
    load_json_config = None
import re
try:
    # Versioning utilities for logging banner
    from versioning import log_build_banner
except Exception:
    log_build_banner = None


def sanitize_name(name: str, preserve_case: bool = True) -> str:
    """Convert model/prompt names to filesystem-safe strings
    
    Args:
        name: The name to sanitize
        preserve_case: If True, preserve the original case. If False, convert to lowercase.
    
    Returns:
        Sanitized name safe for filesystem use
    """
    if not name:
        return "unknown"
    # Remove characters that are not letters, numbers, underscore, hyphen, or dot
    # Spaces and punctuation are removed (not replaced) to satisfy naming tests
    safe_name = re.sub(r'[^A-Za-z0-9_\-.]', '', str(name))
    # Convert to lowercase unless case preservation is requested
    return safe_name if preserve_case else safe_name.lower()


def get_effective_model(args, config_file: str = "workflow_config.json") -> str:
    """Determine which model will actually be used for directory naming
    
    Priority:
    1. Command-line --model argument
    2. Custom image describer config default model (if --config-id provided)
    3. workflow_config.json step config
    4. Default image_describer_config.json
    """
    # Command line argument takes precedence
    if hasattr(args, 'model') and args.model:
        return sanitize_name(args.model)
    
    # Check custom image describer config if provided
    if hasattr(args, 'config_image_describer') and args.config_image_describer:
        try:
            custom_model = get_default_model(args.config_image_describer)
            if custom_model:
                return sanitize_name(custom_model)
        except Exception:
            pass
    
    # Check workflow config file
    try:
        config = WorkflowConfig(config_file)
        workflow_model = config.config.get("workflow", {}).get("steps", {}).get("image_description", {}).get("model")
        if workflow_model:
            return sanitize_name(workflow_model)
    except Exception:
        pass
    
    # Fall back to default image_describer_config.json
    try:
        import json
        # Try different possible paths for the config file
        config_paths = [
            "image_describer_config.json",
            "scripts/image_describer_config.json"
        ]
        
        for config_path in config_paths:
            try:
                with open(config_path, 'r') as f:
                    img_config = json.load(f)
                    default_model = img_config.get("default_model")
                    if default_model:
                        return sanitize_name(default_model)
                    # Fallback to old structure
                    model = img_config.get("model_settings", {}).get("model")
                    if model:
                        return sanitize_name(model)
            except FileNotFoundError:
                continue
                
    except Exception:
        pass
        
    return "unknown"


def validate_prompt_style(style: str, config_file: str = "image_describer_config.json") -> str:
    """Validate and normalize prompt style with case-insensitive lookup
    
    Uses config_loader for PyInstaller-compatible path resolution.
    """
    if not style:
        return "detailed"
    
    try:
        # Import at module level to avoid repeated imports
        from scripts.config_loader import load_json_config
    except ImportError:
        try:
            from config_loader import load_json_config
        except ImportError:
            # Fallback: config_loader not available, return style as-is if it looks valid
            if style and len(style) > 0:
                return style
            return "detailed"
    
    try:
        cfg, path, source = load_json_config('image_describer_config.json', 
                                              explicit=config_file if config_file != 'image_describer_config.json' else None,
                                              env_var_file='IDT_IMAGE_DESCRIBER_CONFIG')
        if cfg:
            prompt_variations = cfg.get('prompt_variations', {})
            
            # Create case-insensitive lookup
            lower_variations = {k.lower(): k for k in prompt_variations.keys()}
            
            # Check if style exists (case-insensitive)
            if style.lower() in lower_variations:
                return lower_variations[style.lower()]
                
    except Exception as e:
        # If config loading fails, return the style as-is (trust the caller)
        pass
        
    # If style not found in config but was provided, return it anyway
    # (allows custom/unknown styles to pass through)
    if style:
        return style
        
    # Final fallback
    return "detailed"


def get_effective_prompt_style(args, config_file: str = "workflow_config.json") -> str:
    """Determine which prompt style will actually be used for directory naming
    
    Priority:
    1. Command-line --prompt-style argument
    2. Custom image describer config default prompt style (if --config-id provided)
    3. workflow_config.json step config
    4. Default image_describer_config.json
    """
    # Command line argument takes precedence
    if hasattr(args, 'prompt_style') and args.prompt_style:
        return validate_prompt_style(args.prompt_style)
    
    # Check custom image describer config if provided
    if hasattr(args, 'config_image_describer') and args.config_image_describer:
        try:
            custom_style = get_default_prompt_style(args.config_image_describer)
            if custom_style:
                return validate_prompt_style(custom_style)
        except Exception:
            pass
    
    # Check workflow config file
    try:
        config = WorkflowConfig(config_file)
        workflow_prompt = config.config.get("workflow", {}).get("steps", {}).get("image_description", {}).get("prompt_style")
        if workflow_prompt:
            return validate_prompt_style(workflow_prompt)
    except Exception:
        pass
    
    # Fall back to default image_describer_config.json
    try:
        # Try different possible paths for the config file
        config_paths = [
            "image_describer_config.json",
            "scripts/image_describer_config.json"
        ]
        
        for config_path in config_paths:
            try:
                default_style = get_default_prompt_style(config_path)
                return validate_prompt_style(default_style)
            except (FileNotFoundError, ImportError):
                continue
                
    except Exception:
        pass
        
    return "detailed"


def log_environment_info(log_dir: Path, workflow_name: str = "workflow") -> Dict[str, Any]:
    """
    Capture and log comprehensive environment and machine information.
    
    Args:
        log_dir: Directory where the environment log will be saved
        workflow_name: Name of the workflow (used in filename)
        
    Returns:
        Dictionary containing all environment information
    """
    import socket
    
    # Gather all environment information
    env_info = {
        "timestamp": datetime.now().isoformat(),
        "workflow_name": workflow_name,
        
        # System Information
        "system": {
            "hostname": platform.node(),
            "fqdn": socket.getfqdn(),
            "os": platform.system(),
            "os_release": platform.release(),
            "os_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
        },
        
        # Python Information
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "compiler": platform.python_compiler(),
            "build": platform.python_build(),
            "executable": sys.executable,
            "frozen": getattr(sys, 'frozen', False),
        },
        
        # Hardware Information
        "hardware": {
            "cpu_count": os.cpu_count(),
        },
        
        # User/Environment
        "environment": {
            "username": os.environ.get('USERNAME') or os.environ.get('USER', 'unknown'),
            "computername": os.environ.get('COMPUTERNAME') or platform.node(),
            "home_dir": str(Path.home()),
            "cwd": os.getcwd(),
        },
    }
    
    # Get hardware information using psutil
    try:
        import psutil
        
        # Memory information
        mem = psutil.virtual_memory()
        env_info["hardware"]["memory_total_gb"] = round(mem.total / (1024**3), 2)
        env_info["hardware"]["memory_available_gb"] = round(mem.available / (1024**3), 2)
        env_info["hardware"]["memory_percent_used"] = mem.percent
        
        # CPU frequency
        cpu_freq = psutil.cpu_freq()
        if cpu_freq:
            env_info["hardware"]["cpu_freq_current_mhz"] = round(cpu_freq.current, 1)
            env_info["hardware"]["cpu_freq_max_mhz"] = round(cpu_freq.max, 1)
        
        # Disk usage
        disk = psutil.disk_usage('/')
        env_info["hardware"]["disk_total_gb"] = round(disk.total / (1024**3), 2)
        env_info["hardware"]["disk_free_gb"] = round(disk.free / (1024**3), 2)
        env_info["hardware"]["disk_percent_used"] = disk.percent
        
        # CPU load at workflow start
        env_info["hardware"]["cpu_percent_at_start"] = psutil.cpu_percent(interval=0.1)
        
    except Exception as e:
        env_info["hardware"]["psutil_error"] = str(e)
    
    # GPU/NPU detection (Windows PowerShell)
    try:
        result = subprocess.run(
            ["powershell", "-Command", 
             "Get-CimInstance Win32_VideoController | Select-Object Name, VideoProcessor | ConvertTo-Json"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            import json
            gpu_data = json.loads(result.stdout)
            if not isinstance(gpu_data, list):
                gpu_data = [gpu_data]
            
            gpu_list = []
            for gpu in gpu_data:
                if gpu.get('Name'):
                    gpu_info_str = gpu['Name']
                    if gpu.get('VideoProcessor'):
                        gpu_info_str += f" ({gpu['VideoProcessor']})"
                    gpu_list.append(gpu_info_str)
            
            if gpu_list:
                env_info["hardware"]["gpu"] = gpu_list
                
                # Check for NPU indicators (Qualcomm, Snapdragon)
                gpu_str = " ".join(gpu_list).lower()
                if any(term in gpu_str for term in ["qualcomm", "snapdragon", "adreno", "hexagon"]):
                    env_info["hardware"]["npu_detected"] = True
                    env_info["hardware"]["copilot_plus_pc"] = "Likely"
    except Exception as e:
        env_info["hardware"]["gpu_detection_error"] = str(e)
    
    # Ollama version detection
    try:
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True,
            text=True,
            timeout=3
        )
        if result.returncode == 0:
            env_info["software"] = {"ollama_version": result.stdout.strip()}
    except Exception:
        pass  # Ollama not installed or not in PATH
    
    # Save to log file
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"environment_{workflow_name}_{timestamp}.log"
    
    try:
        with open(log_file, 'w', encoding='utf-8') as f:
            # Write header
            f.write("=" * 80 + "\n")
            f.write("IMAGE DESCRIPTION TOOLKIT - ENVIRONMENT LOG\n")
            f.write("=" * 80 + "\n\n")
            
            # Write formatted information
            f.write(f"Timestamp: {env_info['timestamp']}\n")
            f.write(f"Workflow:  {env_info['workflow_name']}\n\n")
            
            f.write("-" * 80 + "\n")
            f.write("SYSTEM INFORMATION\n")
            f.write("-" * 80 + "\n")
            for key, value in env_info["system"].items():
                f.write(f"  {key.replace('_', ' ').title():<20}: {value}\n")
            
            f.write("\n" + "-" * 80 + "\n")
            f.write("PYTHON INFORMATION\n")
            f.write("-" * 80 + "\n")
            for key, value in env_info["python"].items():
                f.write(f"  {key.replace('_', ' ').title():<20}: {value}\n")
            
            f.write("\n" + "-" * 80 + "\n")
            f.write("HARDWARE INFORMATION\n")
            f.write("-" * 80 + "\n")
            for key, value in env_info["hardware"].items():
                if key == "gpu" and isinstance(value, list):
                    f.write(f"  {key.upper():<20}:\n")
                    for gpu in value:
                        f.write(f"    - {gpu}\n")
                else:
                    f.write(f"  {key.replace('_', ' ').title():<20}: {value}\n")
            
            # Software section (optional)
            if "software" in env_info:
                f.write("\n" + "-" * 80 + "\n")
                f.write("SOFTWARE INFORMATION\n")
                f.write("-" * 80 + "\n")
                for key, value in env_info["software"].items():
                    f.write(f"  {key.replace('_', ' ').title():<20}: {value}\n")
            
            f.write("\n" + "-" * 80 + "\n")
            f.write("ENVIRONMENT\n")
            f.write("-" * 80 + "\n")
            for key, value in env_info["environment"].items():
                f.write(f"  {key.replace('_', ' ').title():<20}: {value}\n")
            
            # Write raw JSON at the end for machine parsing
            f.write("\n" + "=" * 80 + "\n")
            f.write("RAW JSON DATA (for machine parsing)\n")
            f.write("=" * 80 + "\n")
            json.dump(env_info, f, indent=2)
            f.write("\n")
        
        print(f"Environment log saved: {log_file}")
        
    except Exception as e:
        print(f"Warning: Could not save environment log: {e}")
    
    return env_info


# ============================================================================
# REDESCRIBE WORKFLOW FUNCTIONS
# ============================================================================

def validate_redescribe_args(args, source_dir: Path) -> Dict[str, Any]:
    """
    Validate arguments for redescribe operation
    
    Args:
        args: Parsed command-line arguments
        source_dir: Path to source workflow directory
        
    Returns:
        Source workflow metadata
        
    Raises:
        ValueError: If validation fails
    """
    # Check for incompatible arguments
    if args.input_source:
        raise ValueError("Cannot specify input_source with --redescribe. The source workflow provides the images.")
    
    if args.resume:
        raise ValueError("Cannot use --resume with --redescribe. Use one or the other.")
    
    if args.download:
        raise ValueError("Cannot use --download with --redescribe. Use --redescribe to reuse existing images.")
    
    # Validate source workflow exists
    if not source_dir.exists():
        raise ValueError(f"Source workflow not found: {source_dir}")
    
    if not source_dir.is_dir():
        raise ValueError(f"Source workflow is not a directory: {source_dir}")
    
    # Load source metadata
    source_metadata = load_workflow_metadata(source_dir)
    if not source_metadata:
        raise ValueError(
            f"Invalid workflow directory (no metadata found): {source_dir}\n"
            f"Hint: Use 'idt list' to see available workflows"
        )
    
    # Check for required directories - at least one must exist
    converted_images = source_dir / "converted_images"
    extracted_frames = source_dir / "extracted_frames"
    
    has_images = converted_images.exists() and any(converted_images.iterdir())
    has_frames = extracted_frames.exists() and any(extracted_frames.iterdir())
    
    if not has_images and not has_frames:
        raise ValueError(
            f"Source workflow has no processed images:\n"
            f"  Missing or empty: converted_images/\n"
            f"  Missing or empty: extracted_frames/\n"
            f"Run the source workflow to completion before redescribing."
        )
    
    # Require at least one changed parameter
    source_provider = source_metadata.get("provider", "")
    source_model = source_metadata.get("model", "")
    source_prompt = source_metadata.get("prompt_style", "")
    
    same_provider = args.provider == source_provider
    same_model = (args.model or get_default_model(args.provider)) == source_model
    same_prompt = (args.prompt_style or "narrative") == source_prompt
    same_config = not args.config_image_describer  # No custom config specified
    
    if same_provider and same_model and same_prompt and same_config:
        raise ValueError(
            f"Redescribe requires at least one change in AI settings.\n"
            f"Source workflow: {source_provider} / {source_model} / {source_prompt}\n"
            f"Your settings: {args.provider} / {args.model or get_default_model(args.provider)} / {args.prompt_style or 'narrative'}\n"
            f"Hint: Specify --provider, --model, --prompt-style, or --config-image-describer"
        )
    
    return source_metadata


def determine_reusable_steps(source_dir: Path, source_metadata: Dict) -> List[str]:
    """
    Analyze source workflow to determine which steps can be reused
    
    Args:
        source_dir: Path to source workflow directory
        source_metadata: Source workflow metadata
        
    Returns:
        List of step names that can be reused (e.g., ['video', 'convert'])
    """
    reusable = []
    
    # Check for extracted video frames (may be in subdirectories by video name)
    extracted_frames = source_dir / "extracted_frames"
    if extracted_frames.exists():
        frame_files = list(extracted_frames.rglob("*.jpg")) + list(extracted_frames.rglob("*.png"))
        if frame_files:
            reusable.append("video")
            print(f"  ✓ Found {len(frame_files)} extracted video frames")
    
    # Check for converted images  
    converted_images = source_dir / "converted_images"
    if converted_images.exists():
        image_files = (list(converted_images.glob("*.jpg")) + 
                      list(converted_images.glob("*.jpeg")) +
                      list(converted_images.glob("*.png")))
        if image_files:
            reusable.append("convert")
            print(f"  ✓ Found {len(image_files)} converted images")
    
    # Check for input images (regular images copied to workflow)
    input_images = source_dir / "input_images"
    if input_images.exists():
        image_files = (list(input_images.glob("*.jpg")) + 
                      list(input_images.glob("*.jpeg")) +
                      list(input_images.glob("*.png")))
        if image_files:
            reusable.append("input")
            print(f"  ✓ Found {len(image_files)} input images")
    
    return reusable


def can_create_hardlinks(source_parent: Path, dest_parent: Path) -> bool:
    """Check if hardlinks can be created between two directories"""
    try:
        # Hardlinks require same filesystem
        source_stat = os.stat(str(source_parent))
        dest_stat = os.stat(str(dest_parent))
        
        # On Windows, check if on same drive
        if sys.platform.startswith('win'):
            return str(source_parent.resolve())[0].upper() == str(dest_parent.resolve())[0].upper()
        else:
            # On Unix, check if same device
            return source_stat.st_dev == dest_stat.st_dev
    except Exception:
        return False


def can_create_symlinks() -> bool:
    """Check if symlinks can be created on this system"""
    if sys.platform.startswith('win'):
        # Windows requires admin privileges or Developer Mode for symlinks
        try:
            test_dir = Path.cwd() / ".symlink_test_dir"
            test_link = Path.cwd() / ".symlink_test_link"
            
            test_dir.mkdir(exist_ok=True)
            try:
                test_link.symlink_to(test_dir, target_is_directory=True)
                test_link.unlink()
                test_dir.rmdir()
                return True
            except (OSError, NotImplementedError):
                if test_dir.exists():
                    test_dir.rmdir()
                return False
        except Exception:
            return False
    else:
        # Unix systems support symlinks by default
        return True


def reuse_images(source_dir: Path, dest_dir: Path, method: str = "auto") -> str:
    """
    Reuse images from source workflow in destination workflow
    Preserves the original directory structure (extracted_frames, converted_images, input_images)
    
    Args:
        source_dir: Source workflow directory
        dest_dir: Destination workflow directory
        method: "auto", "link", "copy", or "force-copy"
    
    Returns:
        Method used: "hardlink", "symlink", or "copy"
    """
    # Find all image directories in source workflow
    image_dirs_to_copy = []
    
    # Check for extracted video frames
    source_extracted = source_dir / "extracted_frames"
    if source_extracted.exists() and any(source_extracted.iterdir()):
        image_dirs_to_copy.append(("extracted_frames", source_extracted))
    
    # Check for converted images  
    source_converted = source_dir / "converted_images"
    if source_converted.exists() and any(source_converted.iterdir()):
        image_dirs_to_copy.append(("converted_images", source_converted))
    
    # Check for input images (regular images copied to workflow)
    source_input = source_dir / "input_images"
    if source_input.exists() and any(source_input.iterdir()):
        image_dirs_to_copy.append(("input_images", source_input))
    
    if not image_dirs_to_copy:
        raise ValueError("No images found in source workflow")
    
    # Determine method (check using first directory as reference)
    first_dir_name, first_source = image_dirs_to_copy[0]
    if method == "force-copy" or method == "copy":
        use_method = "copy"
    elif method == "link":
        # User requested linking - try hardlink first, then symlink
        if can_create_hardlinks(first_source.parent, dest_dir):
            use_method = "hardlink"
        elif can_create_symlinks():
            use_method = "symlink"
        else:
            print("  ⚠ Linking not available on this system, falling back to copy")
            use_method = "copy"
    else:  # auto
        # Auto-detect best method
        if can_create_hardlinks(first_source.parent, dest_dir):
            use_method = "hardlink"
        elif can_create_symlinks():
            use_method = "symlink"
        else:
            use_method = "copy"
    
    print(f"  → Reusing images via {use_method}")
    
    total_count = 0
    total_size = 0
    
    # Process each directory, preserving structure
    for dir_name, source_images in image_dirs_to_copy:
        dest_images = dest_dir / dir_name
        
        # Get all files in the directory (recursively for subdirectories)
        # extracted_frames may have subdirectories by video name
        if dir_name == "extracted_frames":
            files_to_process = list(source_images.rglob("*"))
        else:
            files_to_process = [f for f in source_images.iterdir() if f.is_file()]
        
        if use_method == "symlink":
            # Create symlink to entire directory (preserves all subdirectories)
            dest_images.symlink_to(source_images.resolve(), target_is_directory=True)
            # Count actual image files for reporting
            image_count = len([f for f in files_to_process if f.is_file()])
            total_count += image_count
            print(f"  ✓ Symlinked {dir_name}/ ({image_count} images)")
            
        else:
            # Create destination directory
            dest_images.mkdir(parents=True, exist_ok=True)
            
            # Copy or hardlink each file, preserving subdirectory structure
            for item in files_to_process:
                if not item.is_file():
                    continue
                
                # Calculate relative path from source directory to maintain structure
                rel_path = item.relative_to(source_images)
                dest_file = dest_images / rel_path
                
                # Create parent directories if needed (for extracted_frames subdirs)
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                
                if use_method == "hardlink":
                    try:
                        os.link(str(item), str(dest_file))
                        total_count += 1
                    except Exception as e:
                        # If hardlink fails, fall back to copy
                        print(f"  ⚠ Hardlink failed for {item.name}, copying instead: {e}")
                        shutil.copy2(str(item), str(dest_file))
                        total_count += 1
                        total_size += item.stat().st_size
                else:  # copy
                    shutil.copy2(str(item), str(dest_file))
                    total_count += 1
                    total_size += item.stat().st_size
            
            if use_method == "hardlink":
                if dir_name == "extracted_frames":
                    dir_count = len([f for f in dest_images.rglob("*") if f.is_file()])
                else:
                    dir_count = len([f for f in dest_images.iterdir() if f.is_file()])
                print(f"  ✓ Hardlinked {dir_name}/ ({dir_count} images)")
            else:
                if dir_name == "extracted_frames":
                    dir_count = len([f for f in dest_images.rglob("*") if f.is_file()])
                else:
                    dir_count = len([f for f in dest_images.iterdir() if f.is_file()])
                print(f"  ✓ Copied {dir_name}/ ({dir_count} images)")

    
    # Print summary
    if use_method == "symlink":
        print(f"  ✓ Total: {total_count} images symlinked (0 MB disk space used)")
    elif use_method == "hardlink":
        print(f"  ✓ Total: {total_count} images hardlinked (0 MB disk space used)")
    else:
        size_mb = total_size / (1024 * 1024)
        print(f"  ✓ Total: {total_count} images copied ({size_mb:.1f} MB disk space used)")
    
    return use_method


class WorkflowOrchestrator:
    """Main workflow orchestrator class"""
    
    def __init__(self, config_file: str = "workflow_config.json", base_output_dir: Optional[Path] = None, 
                 model: Optional[str] = None, prompt_style: Optional[str] = None, provider: str = "ollama", 
                 api_key_file: str = None, preserve_descriptions: bool = False, workflow_name: str = None,
                 timeout: int = 90, enable_metadata: bool = True, enable_geocoding: bool = True, 
                 geocode_cache: str = "geocode_cache.json", url: str = None, min_size: str = None,
                 max_images: int = None, progress_status: bool = False,
                 image_describer_config: Optional[str] = None, video_config: Optional[str] = None):
        """
        Initialize the workflow orchestrator
        
        Args:
            config_file: Path to workflow orchestration configuration file
            image_describer_config: Path to image describer config (prompts, AI, metadata)
            video_config: Path to video extraction config
        Args:
            config_file: Path to workflow configuration file
            base_output_dir: Base output directory for the workflow
            model: Override model name
            prompt_style: Override prompt style
            provider: AI provider to use (ollama, openai, claude, onnx)
            api_key_file: Path to API key file for cloud providers
            preserve_descriptions: If True, skip describe step if descriptions already exist
            workflow_name: Name of the workflow (for display purposes)
            timeout: Timeout in seconds for Ollama API requests (default: 90)
            enable_metadata: Whether to extract metadata (GPS, dates, camera info)
            enable_geocoding: Whether to reverse geocode GPS coordinates to city/state/country
            geocode_cache: Path to geocoding cache file
            url: URL to download images from (enables web download step)
            min_size: Minimum image size filter (e.g. "100KB", "1MB")
            max_images: Maximum number of images to download
            progress_status: Enable live progress status updates to console
        """
        self.config = WorkflowConfig(config_file)
        self.config_file = config_file  # Workflow orchestration config
        self.image_describer_config = image_describer_config  # Image describer config (optional)
        self.video_config = video_config  # Video extraction config (optional)
        
        if base_output_dir:
            self.config.set_base_output_dir(base_output_dir)
        self.logger = WorkflowLogger("workflow_orchestrator", base_output_dir=self.config.base_output_dir)
        # Log standardized build banner at the start of any log we create
        try:
            if log_build_banner is not None:
                # WorkflowLogger wraps a real logger in .logger
                log_build_banner(self.logger.logger)
        except Exception:
            pass
        self.discovery = FileDiscovery(self.config)
        
        # Store override settings for resume functionality
        self.override_model = model
        self.override_prompt_style = prompt_style
        self.provider = provider
        self.api_key_file = api_key_file
        self.preserve_descriptions = preserve_descriptions
        self.workflow_name = workflow_name
        self.timeout = timeout
        self.enable_metadata = enable_metadata
        self.enable_geocoding = enable_geocoding
        self.geocode_cache = geocode_cache
        self.url = url
        self.min_size = min_size
        self.max_images = max_images
        self.progress_status = progress_status
        
        # Available workflow steps
        self.available_steps = {
            "download": "download_images",
            "video": "extract_video_frames",
            "convert": "convert_images", 
            "describe": "describe_images",
            "html": "generate_html"
        }
        
        # Track processing results
        self.step_results = {}
        
        # Track workflow statistics
        self.statistics = {
            'start_time': None,
            'end_time': None,
            'total_files_processed': 0,
            'total_videos_processed': 0,
            'total_images_processed': 0,
            'total_downloads': 0,
            'total_conversions': 0,
            'total_descriptions': 0,
            'errors_encountered': 0,
            'steps_completed': [],
            'steps_failed': []
        }
        
    def _download_progress_callback(self, processed: int, total: int, status: str = ""):
        """Callback for download progress updates"""
        if 'download' in self.step_results:
            self.step_results['download'].update({
                'processed': processed,
                'total': total,
                'current_status': status
            })
            self._update_status_log()
            
            # Also log to console if progress_status is enabled
            if self.progress_status:
                if total > 0:
                    percentage = int((processed / total) * 100)
                    self.logger.info(f"[ACTIVE] Image download in progress: {processed}/{total} ({percentage}%) - {status}")
                else:
                    self.logger.info(f"[ACTIVE] Image download in progress: {processed} - {status}")

    def _update_status_log(self) -> None:
        """Update the simple status.log file with current progress"""
        status_lines = []
        
        # Safety check - ensure lists are not None
        if self.statistics.get('steps_completed') is None:
            self.statistics['steps_completed'] = []
        if self.statistics.get('steps_failed') is None:
            self.statistics['steps_failed'] = []
        
        # Add overall progress
        total_steps = len(self.statistics['steps_completed']) + len(self.statistics['steps_failed'])
        if total_steps > 0:
            status_lines.append(f"Workflow Progress: {len(self.statistics['steps_completed'])}/{total_steps} steps completed")
        
        # Add step-specific status
        # Preparation (copy images to temp directory) status
        if self.step_results.get('prepare', {}).get('in_progress', False):
            prep = self.step_results.get('prepare', {})
            if 'processed' in prep and 'total' in prep:
                processed = prep['processed']
                total = prep['total']
                if total > 0:
                    percentage = int((processed / total) * 100)
                    status_lines.append(f"[ACTIVE] Preparing images for description: {processed}/{total} ({percentage}%)")
                else:
                    status_lines.append(f"[ACTIVE] Preparing images for description: {processed}/{total}")
            else:
                status_lines.append("[ACTIVE] Preparing images for description...")
        elif 'prepare' in self.step_results and not self.step_results.get('prepare', {}).get('in_progress', True):
            # Only show a DONE line if we have totals to report
            prep = self.step_results.get('prepare', {})
            if 'total' in prep:
                status_lines.append(f"[DONE] Image preparation complete ({prep.get('total', 0)} files prepared)")

        if 'download' in self.statistics['steps_completed']:
            status_lines.append(f"[DONE] Image download complete ({self.statistics['total_downloads']} images)")
        elif self.step_results.get('download', {}).get('in_progress', False):
            download_result = self.step_results.get('download', {})
            if 'processed' in download_result and 'total' in download_result:
                processed = download_result['processed']
                total = download_result['total']
                if total > 0:
                    percentage = int((processed / total) * 100)
                    status = download_result.get('current_status', '')
                    status_lines.append(f"[ACTIVE] Image download in progress: {processed}/{total} ({percentage}%) - {status}")
                else:
                    status = download_result.get('current_status', '')
                    status_lines.append(f"[ACTIVE] Image download in progress: {processed} - {status}")
            else:
                status_lines.append("[ACTIVE] Image download in progress...")
        elif 'download' in self.statistics['steps_failed']:
            status_lines.append(f"[FAILED] Image download failed")
            
        if 'video' in self.statistics['steps_completed']:
            status_lines.append(f"[DONE] Video extraction complete ({self.statistics['total_videos_processed']} videos)")
        elif self.step_results.get('video', {}).get('in_progress', False):
            vid_result = self.step_results.get('video', {})
            if 'processed' in vid_result and 'total' in vid_result:
                processed = vid_result['processed']
                total = vid_result['total']
                if total > 0:
                    percentage = int((processed / total) * 100)
                    status_lines.append(f"[ACTIVE] Video extraction in progress: {processed}/{total} videos ({percentage}%)")
                else:
                    status_lines.append(f"[ACTIVE] Video extraction in progress: {processed}/{total} videos")
            else:
                status_lines.append("[ACTIVE] Video extraction in progress...")
        elif 'video' in self.statistics['steps_failed']:
            status_lines.append(f"[FAILED] Video extraction failed")
            
        if 'convert' in self.statistics['steps_completed']:
            status_lines.append(f"[DONE] Image conversion complete ({self.statistics['total_conversions']} HEIC to JPG)")
        elif self.step_results.get('convert', {}).get('in_progress', False):
            conv_result = self.step_results.get('convert', {})
            if 'processed' in conv_result and 'total' in conv_result:
                processed = conv_result['processed']
                total = conv_result['total']
                if total > 0:
                    percentage = int((processed / total) * 100)
                    status_lines.append(f"[ACTIVE] Image conversion in progress: {processed}/{total} HEIC to JPG ({percentage}%)")
                else:
                    status_lines.append(f"[ACTIVE] Image conversion in progress: {processed}/{total} HEIC to JPG")
            else:
                status_lines.append("[ACTIVE] Image conversion in progress...")
        elif 'convert' in self.statistics['steps_failed']:
            status_lines.append(f"[FAILED] Image conversion failed")
            
        if 'describe' in self.statistics['steps_completed']:
            status_lines.append(f"[DONE] Image description complete ({self.statistics['total_descriptions']} descriptions)")
        elif self.step_results.get('describe', {}).get('in_progress', False):
            # Check if we have progress data
            desc_result = self.step_results.get('describe', {})
            if 'processed' in desc_result and 'total' in desc_result:
                processed = desc_result['processed']
                total = desc_result['total']
                if total > 0:
                    percentage = int((processed / total) * 100)
                    status_lines.append(f"[ACTIVE] Image description in progress: {processed}/{total} images described ({percentage}%)")
                    
                    # Add estimated time remaining if we have enough data
                    if processed > 0 and self.statistics.get('start_time'):
                        try:
                            start_time = datetime.fromisoformat(self.statistics['start_time'])
                            elapsed_seconds = (datetime.now() - start_time).total_seconds()
                            avg_time_per_image = elapsed_seconds / processed
                            remaining_images = total - processed
                            estimated_remaining_seconds = remaining_images * avg_time_per_image
                            
                            if estimated_remaining_seconds > 0:
                                if estimated_remaining_seconds > 3600:  # > 1 hour
                                    eta_str = f"{estimated_remaining_seconds/3600:.1f}h"
                                elif estimated_remaining_seconds > 60:  # > 1 minute
                                    eta_str = f"{estimated_remaining_seconds/60:.1f}m"
                                else:
                                    eta_str = f"{estimated_remaining_seconds:.0f}s"
                                status_lines.append(f"   Estimated time remaining: {eta_str}")
                        except Exception:
                            pass  # Don't break status updates on ETA calculation errors
                else:
                    status_lines.append(f"[ACTIVE] Image description in progress: {processed}/{total} images described")
            else:
                status_lines.append(f"[ACTIVE] Image description in progress...")
        elif 'describe' in self.statistics['steps_failed']:
            status_lines.append(f"[FAILED] Image description failed")
            
        if 'html' in self.statistics['steps_completed']:
            status_lines.append(f"[DONE] HTML generation complete")
        elif 'html' in self.statistics['steps_failed']:
            status_lines.append(f"[FAILED] HTML generation failed")
        
        # Add error count if any
        if self.statistics['errors_encountered'] > 0:
            status_lines.append(f"⚠ Errors encountered: {self.statistics['errors_encountered']}")
        
        # Add timing info if available
        if self.statistics['start_time']:
            start_time = datetime.fromisoformat(self.statistics['start_time'])
            elapsed = (datetime.now() - start_time).total_seconds()
            status_lines.append(f"\nElapsed time: {elapsed/60:.1f} minutes")
        
        # Update the status log
        self.logger.update_status(status_lines)
        
        # If progress-status mode is enabled, also print to console
        if self.progress_status:
            print("\n" + "="*60)
            print("WORKFLOW PROGRESS STATUS")
            print("="*60)
            for line in status_lines:
                print(line)
            print("="*60)
        
    def download_images(self, input_dir: Path, output_dir: Path) -> Dict[str, Any]:
        """
        Download images from a URL using web_image_downloader.py
        
        Args:
            input_dir: Input directory (not used for download step, but required for interface consistency)
            output_dir: Output directory for downloaded images
            
        Returns:
            Dict containing download results and statistics
        """
        from scripts.web_image_downloader import WebImageDownloader
        
        if not self.url:
            raise ValueError("URL is required for download step")
            
        print(f"\n{'='*80}")
        print("DOWNLOADING IMAGES")
        print(f"{'='*80}")
        print(f"URL: {self.url}")
        print(f"Output directory: {output_dir}")
        
        # Parse min_size parameter if provided
        min_width, min_height = 0, 0
        if self.min_size:
            # Parse formats like "100KB" -> ignore for now, focus on dimensions
            # For now, we'll ignore min_size and use default 0x0
            pass
        
        try:
            # Initialize progress tracking
            self.step_results['download'] = {
                'in_progress': True,
                'processed': 0,
                'total': 0,
                'current_status': 'Initializing download...'
            }
            self._update_status_log()
            
            # Create downloader with proper parameters
            downloader = WebImageDownloader(
                url=self.url,
                output_dir=output_dir,
                min_width=min_width,
                min_height=min_height,
                max_images=self.max_images,
                verbose=True,
                progress_callback=self._download_progress_callback if self.progress_status else None
            )
            
            # Download images
            downloaded_count, skipped_count = downloader.download()
            
            # Mark download as complete
            self.step_results['download'] = {
                'in_progress': False,
                'processed': downloaded_count,
                'total': downloaded_count + skipped_count,
                'current_status': f'Download complete: {downloaded_count} images'
            }
            self._update_status_log()
            
            print(f"\nDownload completed successfully!")
            print(f"Downloaded {downloaded_count} images")
            if skipped_count > 0:
                print(f"Skipped {skipped_count} images (duplicates/too small)")
            
            return {
                'success': True,
                'downloaded_count': downloaded_count,
                'skipped_count': skipped_count,
                'count': downloaded_count,
                'processed': downloaded_count,
                'output_dir': str(output_dir)
            }
            
        except Exception as e:
            error_msg = f"Download failed: {str(e)}"
            print(f"\nERROR: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'downloaded_count': 0,
                'skipped_count': 0,
                'count': 0,
                'processed': 0,
                'output_dir': str(output_dir)
            }
        
    def extract_video_frames(self, input_dir: Path, output_dir: Path) -> Dict[str, Any]:
        """
        Extract frames from videos using video_frame_extractor.py
        
        Args:
            input_dir: Directory containing videos
            output_dir: Output directory for extracted frames
            
        Returns:
            Dictionary with step results
        """
        self.logger.info("Starting video frame extraction...")
        
        # Find video files
        video_files = self.discovery.find_files_by_type(input_dir, "videos")
        
        if not video_files:
            self.logger.info("No video files found to process")
            return {"success": True, "processed": 0}
        
        self.logger.info(f"Found {len(video_files)} video files")
        
        # Update frame extractor config to use our output directory
        step_config = self.config.get_step_config("video_extraction")
        
        # Use explicit video_config if provided, otherwise use step config or default
        if self.video_config:
            config_file = self.video_config
            self.logger.info(f"Using custom video extraction config: {self.video_config}")
        else:
            config_file = step_config.get("config_file", "video_frame_extractor_config.json")
        
        # Temporarily modify the frame extractor config
        self._update_frame_extractor_config(config_file, output_dir)
        
        try:
            # Detect if running as PyInstaller executable
            if getattr(sys, 'frozen', False):
                # Running as executable - use unified CLI
                cmd = [
                    sys.executable, "extract-frames",
                    str(input_dir),
                    "--config", config_file,
                    "--output-dir", str(output_dir),
                    "--log-dir", str(self.config.base_output_dir),
                    "--quiet"  # Suppress subprocess console output to avoid duplicates
                ]
            else:
                # Running as Python script - use direct script call
                cmd = [
                    sys.executable, "video_frame_extractor.py",
                    str(input_dir),
                    "--config", config_file,
                    "--output-dir", str(output_dir),
                    "--log-dir", str(self.config.base_output_dir),
                    "--quiet"  # Suppress subprocess console output to avoid duplicates
                ]
            
            # Prepare progress monitoring
            total_videos = len(video_files)
            self.step_results['video'] = {
                'in_progress': True,
                'total': total_videos,
                'processed': 0
            }
            self._update_status_log()

            # Determine progress file location (based on --log-dir)
            progress_file = None
            for arg_i, arg in enumerate(cmd):
                if arg == "--log-dir" and arg_i + 1 < len(cmd):
                    progress_file = Path(cmd[arg_i + 1]) / "logs" / "video_extraction_progress.txt"
                    self.logger.info(f"Video extraction progress file: {progress_file}")
                    break
            if progress_file is None:
                progress_file = self.config.base_output_dir / "logs" / "video_extraction_progress.txt"
                self.logger.info(f"Video extraction progress file (fallback): {progress_file}")

            # Start background monitor similar to convert/describe steps
            import threading
            import time

            def monitor_video_progress():
                last_count = 0
                checks_without_file = 0
                iteration = 0
                self.logger.info("Video extraction progress monitoring thread started")
                while self.step_results.get('video', {}).get('in_progress', False):
                    iteration += 1
                    try:
                        if progress_file.exists():
                            if checks_without_file > 0:
                                self.logger.info(f"Video extraction progress file appeared after {checks_without_file} checks: {progress_file}")
                                checks_without_file = 0
                            with open(progress_file, 'r', encoding='utf-8') as f:
                                lines = [ln.strip() for ln in f.readlines() if ln.strip()]
                                current_count = len(lines)
                            if iteration % 5 == 0:
                                self.logger.debug(f"Video extraction monitor check #{iteration}: {current_count}/{total_videos} processed")
                            if current_count != last_count:
                                self.step_results['video']['processed'] = current_count
                                self._update_status_log()
                                if current_count - last_count >= 5 or (last_count == 0 and current_count > 0):
                                    self.logger.info(f"Progress update: {current_count}/{total_videos} videos processed, status.log updated")
                                last_count = current_count
                        else:
                            checks_without_file += 1
                            if checks_without_file == 1:
                                self.logger.info(f"Waiting for video extraction progress file to be created: {progress_file}")
                            elif checks_without_file % 10 == 0:
                                self.logger.warning(f"Video extraction progress file still not found after {checks_without_file} checks ({checks_without_file * 10}s)")
                        time.sleep(10)
                    except Exception as e:
                        self.logger.warning(f"Video extraction progress monitoring error: {e}")
                        time.sleep(10)
                self.logger.info(f"Video extraction progress monitoring thread ending after {iteration} iterations")

            monitor_thread = threading.Thread(target=monitor_video_progress, daemon=True)
            monitor_thread.start()
            
            self.logger.info(f"Running: {' '.join(cmd)}")
            # Stream output directly to terminal for real-time progress feedback
            result = subprocess.run(cmd, text=True, encoding='utf-8', errors='replace')
            
            # Stop monitoring
            if 'video' in self.step_results:
                self.step_results['video']['in_progress'] = False
            
            # Final progress update
            if progress_file and progress_file.exists():
                with open(progress_file, 'r', encoding='utf-8') as f:
                    lines = [ln.strip() for ln in f.readlines() if ln.strip()]
                    final_count = len(lines)
                if 'video' in self.step_results:
                    self.step_results['video']['processed'] = final_count
            
            if result.returncode == 0:
                self.logger.info("Video frame extraction completed successfully")
                
                # Count extracted frames
                extracted_frames = self.discovery.find_files_by_type(output_dir, "images")
                
                return {
                    "success": True,
                    "processed": len(video_files),
                    "output_dir": output_dir,
                    "extracted_frames": len(extracted_frames)
                }
            else:
                self.logger.error(f"Video frame extraction failed with exit code {result.returncode}")
                return {"success": False, "error": f"Process failed with exit code {result.returncode}. Check log file for details."}
                
        except Exception as e:
            self.logger.error(f"Error during video frame extraction: {e}")
            return {"success": False, "error": str(e)}
    
    def convert_images(self, input_dir: Path, output_dir: Path) -> Dict[str, Any]:
        """
        Convert HEIC images to JPG using ConvertImage.py
        
        Args:
            input_dir: Directory containing HEIC images
            output_dir: Output directory for converted images
            
        Returns:
            Dictionary with step results
        """
        self.logger.info("Starting image conversion...")
        
        # Find HEIC files
        heic_files = self.discovery.find_files_by_type(input_dir, "heic")
        
        if not heic_files:
            self.logger.info("No HEIC files found to convert")
            return {"success": True, "processed": 0}
        
        self.logger.info(f"Found {len(heic_files)} HEIC files")
        
        try:
            # Get conversion settings
            step_config = self.config.get_step_config("image_conversion")
            
            # Run image converter - handle both frozen and script modes
            if getattr(sys, 'frozen', False):
                # Running as executable - use unified CLI
                cmd = [
                    sys.executable, "convert-images",
                    str(input_dir),
                    "--output", str(output_dir),
                    "--recursive",
                    "--quality", str(step_config.get("quality", 95)),
                    "--log-dir", str(self.config.base_output_dir / "logs"),
                    "--quiet"  # Suppress subprocess console output to avoid duplicates
                ]
            else:
                # Running as Python script - use direct script call
                cmd = [
                    sys.executable, "ConvertImage.py",
                    str(input_dir),
                    "--output", str(output_dir),
                    "--recursive",
                    "--quality", str(step_config.get("quality", 95)),
                    "--log-dir", str(self.config.base_output_dir / "logs"),
                    "--quiet"  # Suppress subprocess console output to avoid duplicates
                ]
            
            if not step_config.get("keep_metadata", True):
                cmd.append("--no-metadata")
            
            # Prepare progress monitoring
            total_to_convert = len(heic_files)
            self.step_results['convert'] = {
                'in_progress': True,
                'total': total_to_convert,
                'processed': 0
            }
            self._update_status_log()

            # Determine progress file location (based on --log-dir)
            progress_file = None
            for arg_i, arg in enumerate(cmd):
                if arg == "--log-dir" and arg_i + 1 < len(cmd):
                    progress_file = Path(cmd[arg_i + 1]) / "convert_images_progress.txt"
                    self.logger.info(f"Conversion progress file: {progress_file}")
                    break
            if progress_file is None:
                progress_file = self.config.base_output_dir / "logs" / "convert_images_progress.txt"
                self.logger.info(f"Conversion progress file (fallback): {progress_file}")

            # Start background monitor similar to describe step
            import threading
            import time

            def monitor_conversion_progress():
                last_count = 0
                checks_without_file = 0
                iteration = 0
                self.logger.info("Conversion progress monitoring thread started")
                while self.step_results.get('convert', {}).get('in_progress', False):
                    iteration += 1
                    try:
                        if progress_file.exists():
                            if checks_without_file > 0:
                                self.logger.info(f"Conversion progress file appeared after {checks_without_file} checks: {progress_file}")
                                checks_without_file = 0
                            with open(progress_file, 'r', encoding='utf-8') as f:
                                lines = [ln.strip() for ln in f.readlines() if ln.strip()]
                                current_count = len(lines)
                            if iteration % 5 == 0:
                                self.logger.debug(f"Conversion monitor check #{iteration}: {current_count}/{total_to_convert} converted")
                            if current_count != last_count:
                                self.step_results['convert']['processed'] = current_count
                                self._update_status_log()
                                if current_count - last_count >= 10 or (last_count == 0 and current_count > 0):
                                    self.logger.info(f"Progress update: {current_count}/{total_to_convert} HEIC to JPG converted, status.log updated")
                                last_count = current_count
                        else:
                            checks_without_file += 1
                            if checks_without_file == 1:
                                self.logger.info(f"Waiting for conversion progress file to be created: {progress_file}")
                            elif checks_without_file % 10 == 0:
                                self.logger.warning(f"Conversion progress file still not found after {checks_without_file} checks ({checks_without_file * 10}s)")
                        time.sleep(10)
                    except Exception as e:
                        self.logger.warning(f"Conversion progress monitoring error: {e}")
                        time.sleep(10)
                self.logger.info(f"Conversion progress monitoring thread ending after {iteration} iterations")

            monitor_thread = threading.Thread(target=monitor_conversion_progress, daemon=True)
            monitor_thread.start()

            self.logger.info(f"Running: {' '.join(cmd)}")
            # Stream output directly to terminal for real-time progress feedback (conversion tool runs quiet)
            result = subprocess.run(cmd, text=True, encoding='utf-8', errors='replace')
            
            # Mark conversion as no longer in progress and final update
            if 'convert' in self.step_results:
                self.step_results['convert']['in_progress'] = False
                # Final read of progress file
                try:
                    if progress_file.exists():
                        with open(progress_file, 'r', encoding='utf-8') as f:
                            lines = [ln.strip() for ln in f.readlines() if ln.strip()]
                            self.step_results['convert']['processed'] = len(lines)
                except Exception:
                    pass
                self._update_status_log()

            if result.returncode == 0:
                self.logger.info("Image conversion completed successfully")
                
                # Count converted images
                converted_images = self.discovery.find_files_by_type(output_dir, "images")
                # Update statistics
                self.statistics['total_conversions'] = len(converted_images)
                
                return {
                    "success": True,
                    "processed": len(heic_files),
                    "output_dir": output_dir,
                    "converted_images": len(converted_images)
                }
            else:
                self.logger.error(f"Image conversion failed with exit code {result.returncode}")
                return {"success": False, "error": f"Process failed with exit code {result.returncode}. Check log file for details."}
                
        except Exception as e:
            self.logger.error(f"Error during image conversion: {e}")
            return {"success": False, "error": str(e)}
    
    def _configure_metadata_settings(self, config_file: str = "image_describer_config.json") -> None:
        """
        Update image_describer_config.json with metadata settings from workflow args.
        This allows workflow to control metadata extraction and geocoding dynamically.
        
        Args:
            config_file: Path to image_describer config file
        """
        try:
            # In frozen mode, resolve config path relative to the executable's directory
            if getattr(sys, 'frozen', False):
                # Frozen: use the directory containing the executable
                base_dir = Path(sys.executable).parent
                config_path = base_dir / "scripts" / config_file
            else:
                # Development: use the script's directory
                config_path = Path(__file__).parent / config_file
            
            if not config_path.exists():
                self.logger.warning(f"Config file not found: {config_path}, skipping metadata configuration")
                return
            
            # Load current config
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Update metadata settings
            if 'metadata' not in config:
                config['metadata'] = {}
            
            config['metadata']['enabled'] = self.enable_metadata
            config['metadata']['include_location_prefix'] = self.enable_metadata
            
            if 'geocoding' not in config['metadata']:
                config['metadata']['geocoding'] = {}
            
            config['metadata']['geocoding']['enabled'] = self.enable_geocoding
            if self.geocode_cache:
                config['metadata']['geocoding']['cache_file'] = self.geocode_cache
            
            # Update processing_options to enable metadata extraction
            if 'processing_options' not in config:
                config['processing_options'] = {}
            config['processing_options']['extract_metadata'] = self.enable_metadata
            
            # Save updated config
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
                f.flush()  # Ensure buffer is written
                os.fsync(f.fileno())  # Force OS to write to disk
            
            # Small delay to ensure file system has fully committed the write
            import time
            time.sleep(0.1)
            
            self.logger.info(f"Updated metadata config: enabled={self.enable_metadata}, geocoding={self.enable_geocoding}")
            
        except Exception as e:
            self.logger.warning(f"Failed to update metadata configuration: {e}")
    
    def describe_images(self, input_dir: Path, output_dir: Path) -> Dict[str, Any]:

        """
        Generate AI descriptions for images using image_describer.py
        
        Args:
            input_dir: Original input directory containing images
            output_dir: Output directory for descriptions
            
        Returns:
            Dictionary with step results
        """
        self.logger.info("Starting image description...")
        
        # Configure metadata settings before running image_describer
        self._configure_metadata_settings()
        
        # Check if preserve_descriptions flag is set and descriptions already exist
        if self.preserve_descriptions:
            # Look for existing descriptions file
            desc_output_dir = self.config.get_step_output_dir("image_description")
            existing_desc_file = desc_output_dir / "descriptions.csv"
            
            if existing_desc_file.exists():
                # Count existing descriptions
                try:
                    import csv
                    with open(existing_desc_file, 'r', encoding='utf-8') as f:
                        reader = csv.reader(f)
                        next(reader)  # Skip header
                        desc_count = sum(1 for row in reader)
                    
                    self.logger.info(f"Preserve flag is set and {desc_count} descriptions already exist")
                    print(f"INFO: Preserve flag is set - skipping describe step ({desc_count} existing descriptions)")
                    
                    # Return success result with existing file
                    return {
                        "success": True,
                        "processed": desc_count,
                        "output_dir": desc_output_dir,
                        "description_file": str(existing_desc_file),
                        "skipped": True,
                        "reason": "preserve_descriptions flag enabled"
                    }
                except Exception as e:
                    self.logger.warning(f"Could not read existing descriptions file: {e}")
                    # Continue with normal processing if we can't read the file
        
        # Build list of directories to search for images
        # Track unique source images to avoid double-counting HEIC + converted JPG
        converted_dir = self.config.get_step_output_dir("image_conversion")
        frames_dir = self.config.get_step_output_dir("video_extraction")
        input_images_dir = self.config.base_output_dir / "input_images"
        
        # Check if we're in a workflow directory (redescribe mode)
        # In this case, input_dir == base_output_dir and we should scan the workflow subdirectories
        is_workflow_dir = (input_dir == self.config.base_output_dir or 
                          (converted_dir.exists() or frames_dir.exists() or input_images_dir.exists()))
        
        # Build the list of images to process
        all_image_files = []
        unique_source_count = 0  # Track unique source images
        conversion_count = 0  # Track format conversions
        
        if is_workflow_dir:
            # We're processing a workflow directory (redescribe mode)
            # Scan the three possible image directories directly
            self.logger.info("Scanning workflow directory for images...")
            
            # Check input_images directory
            if input_images_dir.exists() and any(input_images_dir.iterdir()):
                existing_images = self.discovery.find_files_by_type(input_images_dir, "images")
                all_image_files.extend(existing_images)
                unique_source_count += len(existing_images)
                self.logger.info(f"Found {len(existing_images)} image(s) in: {input_images_dir}")
            
            # Check converted_images directory
            if converted_dir.exists() and any(converted_dir.iterdir()):
                converted_images = self.discovery.find_files_by_type(converted_dir, "images")
                all_image_files.extend(converted_images)
                unique_source_count += len(converted_images)
                conversion_count = len(converted_images)
                self.logger.info(f"Found {len(converted_images)} converted image(s) in: {converted_dir}")
            
            # Check extracted_frames directory
            if frames_dir.exists() and any(frames_dir.iterdir()):
                frame_images = self.discovery.find_files_by_type(frames_dir, "images")
                all_image_files.extend(frame_images)
                unique_source_count += len(frame_images)
                self.logger.info(f"Found {len(frame_images)} extracted frame(s) in: {frames_dir}")
        
        else:
            # Normal mode: process original input directory
            # Find HEIC files in input directory that will/were converted
            heic_files_in_input = self.discovery.find_files_by_type(input_dir, "heic")
            has_conversions = converted_dir.exists() and any(converted_dir.iterdir())
            
            # Find regular (non-HEIC) images in input directory
            all_input_images = self.discovery.find_files_by_type(input_dir, "images")
            regular_input_images = [img for img in all_input_images if img not in heic_files_in_input]
            
            # Copy regular (non-HEIC) images to workflow input_images/ directory
            # This makes workflows self-contained and consistent with extracted_frames/converted_images
            if regular_input_images:
                input_images_dir.mkdir(parents=True, exist_ok=True)
                self.logger.info(f"Copying {len(regular_input_images)} regular image(s) to workflow directory...")
                for img in regular_input_images:
                    dest = input_images_dir / img.name
                    shutil.copy2(str(img), str(dest))
                    all_image_files.append(dest)
                unique_source_count += len(regular_input_images)
                self.logger.info(f"Copied {len(regular_input_images)} images to: {input_images_dir}")
            
            # Add converted images OR HEIC files (not both)
            if has_conversions:
                converted_images = self.discovery.find_files_by_type(converted_dir, "images")
                all_image_files.extend(converted_images)
                unique_source_count += len(converted_images)
                conversion_count = len(converted_images)
                self.logger.info(f"Including {len(converted_images)} converted image(s) from: {converted_dir}")
            elif heic_files_in_input:
                # If conversion hasn't run yet, include HEIC files directly
                all_image_files.extend(heic_files_in_input)
                unique_source_count += len(heic_files_in_input)
                self.logger.info(f"Found {len(heic_files_in_input)} HEIC image(s) in input directory (not yet converted)")
            
            # Add extracted frames from videos
            if frames_dir.exists() and any(frames_dir.iterdir()):
                frame_images = self.discovery.find_files_by_type(frames_dir, "images")
                all_image_files.extend(frame_images)
                unique_source_count += len(frame_images)
                self.logger.info(f"Including {len(frame_images)} extracted frame(s) from: {frames_dir}")
        
        if not all_image_files:
            self.logger.info("No image files found to describe")
            return {"success": True, "processed": 0, "unique_images": 0, "conversions": 0, "output_dir": output_dir}
        
        self.logger.info(f"Total unique images to describe: {unique_source_count}")
        if conversion_count > 0:
            self.logger.info(f"Format conversions included: {conversion_count} (HEIC to JPG)")
        
        try:
            # Get description settings
            step_config = self.config.get_step_config("image_description")
            
            # Create a temporary directory to combine all images from all directories
            # This ensures image_describer.py only runs once and doesn't overwrite descriptions
            temp_combined_dir = self.config.base_output_dir / "temp_combined_images"
            temp_combined_dir.mkdir(parents=True, exist_ok=True)
            
            # Preserve full directory structure in temp dir to prevent collisions
            combined_image_list = []
            total_copy_failures = 0

            # Initialize preparation (copy) progress so the user sees activity before describe starts
            self.step_results['prepare'] = {
                'in_progress': True,
                'processed': 0,
                'total': len(all_image_files)
            }
            self.logger.info(f"Preparing {len(all_image_files)} images for description (copying to temp workspace)...")
            self._update_status_log()
            
            # Copy all unique images to temporary directory
            for idx, image_file in enumerate(all_image_files, start=1):
                try:
                    # Determine which source directory this file came from
                    source_dir = None
                    if image_file.is_relative_to(input_images_dir):
                        source_dir = input_images_dir
                    elif image_file.is_relative_to(converted_dir):
                        source_dir = converted_dir
                    elif image_file.is_relative_to(frames_dir):
                        source_dir = frames_dir
                    elif image_file.is_relative_to(input_dir):
                        source_dir = input_dir
                    else:
                        # Fallback to using parent directory
                        source_dir = image_file.parent
                    
                    # Calculate relative path from source_dir to image_file
                    try:
                        relative_path = image_file.relative_to(source_dir)
                    except ValueError:
                        # If relative path fails, just use filename
                        relative_path = Path(image_file.name)
                    
                    # Create a safe name for the source directory to use as root in temp structure
                    safe_source_name = source_dir.name.replace(" ", "_").replace(":", "")
                    
                    # Create temp path preserving directory structure under source name
                    temp_image_path = temp_combined_dir / safe_source_name / relative_path
                    
                    # Ensure parent directories exist
                    temp_image_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Copy file to temp location preserving structure
                    shutil.copy2(image_file, temp_image_path)
                    combined_image_list.append((temp_image_path, image_file))  # (temp_path, original_path)
                    self.logger.debug(f"Copied {image_file} to {temp_image_path}")

                    # Update preparation progress counters and status periodically
                    if 'prepare' in self.step_results:
                        self.step_results['prepare']['processed'] += 1
                        # Update every 25 files or on last item
                        if (idx % 25 == 0) or (self.step_results['prepare']['processed'] == self.step_results['prepare']['total']):
                            self._update_status_log()
                            if self.progress_status:
                                proc = self.step_results['prepare']['processed']
                                tot = self.step_results['prepare']['total']
                                pct = int((proc / tot) * 100) if tot > 0 else 0
                                self.logger.info(f"[ACTIVE] Preparing images for description: {proc}/{tot} ({pct}%)")
                    
                except Exception as e:
                    self.logger.warning(f"Failed to copy {image_file}: {e}")
                    total_copy_failures += 1
                    continue
            
            # Log comprehensive copy summary
            self.logger.info(f"Copy Summary: Successfully prepared {len(combined_image_list)}/{len(all_image_files)} images for processing")
            if total_copy_failures > 0:
                self.logger.warning(f"Copy Summary: Failed to copy {total_copy_failures} images")
                self.logger.warning(f"Copy Summary: Success rate: {(len(combined_image_list) / len(all_image_files) * 100):.1f}%")
            
            # Mark preparation as complete in status tracking
            if 'prepare' in self.step_results:
                self.step_results['prepare']['in_progress'] = False
                # Ensure final status update after completion
                self._update_status_log()
                self.logger.info(f"Image preparation complete: {len(combined_image_list)}/{len(all_image_files)} files ready")

            if not combined_image_list:
                self.logger.info("No images were successfully prepared for processing")
                return {"success": True, "processed": 0, "output_dir": output_dir}
                
            self.logger.info(f"Prepared {len(combined_image_list)} images for single processing run")
            
            # Verification step: Check that image_describer.py can find the files
            self.logger.info("Verifying temp directory structure for image_describer.py compatibility...")
            
            # Test the same discovery logic that image_describer.py uses
            discoverable_files = []
            supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
            
            for file_path in temp_combined_dir.glob("**/*"):
                if file_path.is_file() and file_path.suffix.lower() in supported_formats:
                    discoverable_files.append(file_path)
            
            if len(discoverable_files) != len(combined_image_list):
                self.logger.warning(f"Discovery mismatch: Copied {len(combined_image_list)} files but image_describer.py will find {len(discoverable_files)} files")
                self.logger.warning("This may indicate a file format or path issue")
                
                # Log some examples of the discrepancy
                copied_names = {temp_path.name for temp_path, _ in combined_image_list}
                discovered_names = {f.name for f in discoverable_files}
                
                only_copied = copied_names - discovered_names
                only_discovered = discovered_names - copied_names
                
                if only_copied:
                    self.logger.warning(f"Files copied but not discoverable (first 5): {list(only_copied)[:5]}")
                if only_discovered:
                    self.logger.warning(f"Files discoverable but not in copy list (first 5): {list(only_discovered)[:5]}")
            else:
                self.logger.info(f"Verification successful: All {len(combined_image_list)} copied files are discoverable by image_describer.py")
            
            # Build command for the combined directory - single call to image_describer
            if getattr(sys, 'frozen', False):
                # In frozen mode rely on dispatcher supporting 'image_describer' alias
                cmd = [sys.executable, 'image_describer', str(temp_combined_dir), '--recursive',
                       '--output-dir', str(output_dir), '--log-dir', str(self.config.base_output_dir / 'logs'),
                       '--quiet']  # Suppress subprocess console output to avoid duplicates
            else:
                scripts_dir = Path(__file__).parent
                image_describer_path = scripts_dir / 'image_describer.py'
                cmd = [sys.executable, str(image_describer_path), str(temp_combined_dir), '--recursive',
                       '--output-dir', str(output_dir), '--log-dir', str(self.config.base_output_dir / 'logs'),
                       '--quiet']  # Suppress subprocess console output to avoid duplicates
            
            # Add provider parameter
            if self.provider:
                cmd.extend(["--provider", self.provider])
                self.logger.info(f"Using AI provider: {self.provider}")
            
            # Add API key file if provided
            if self.api_key_file:
                cmd.extend(["--api-key-file", self.api_key_file])
                self.logger.info(f"Using API key file: {self.api_key_file}")
            
            # Add optional parameters
            # Use explicit image_describer_config if provided
            config_to_use = None
            if self.image_describer_config:
                # User specified explicit image describer config
                config_to_use = self.image_describer_config
                self.logger.info(f"Using custom image describer config: {self.image_describer_config}")
            elif "config_file" in step_config:
                config_to_use = step_config["config_file"]
            else:
                # Use default image_describer_config.json
                config_to_use = str(Path(__file__).parent / "image_describer_config.json")
            
            cmd.extend(["--config", config_to_use])
            
            # Model selection priority:
            # 1. Command-line --model argument (highest priority - explicit user choice)
            # 2. Custom image describer config default model (if --config-id provided)
            # 3. workflow_config.json step config model (fallback)
            # 4. Let image_describer.py use its own defaults (no --model passed)
            model_to_use = None
            model_source = None
            
            if self.override_model:
                # Priority 1: Command-line argument
                model_to_use = self.override_model
                model_source = "command-line argument"
            elif self.image_describer_config:
                # Priority 2: Custom image describer config default model
                custom_model = get_default_model(self.image_describer_config)
                if custom_model:
                    model_to_use = custom_model
                    model_source = f"custom config '{self.image_describer_config}'"
            
            if not model_to_use and "model" in step_config and step_config["model"]:
                # Priority 3: workflow_config.json step config
                model_to_use = step_config["model"]
                model_source = "workflow_config.json"
            
            if model_to_use:
                cmd.extend(["--model", model_to_use])
                self.logger.info(f"Using model '{model_to_use}' from {model_source}")
            
            # Prompt style selection priority (same pattern as model):
            # 1. Command-line --prompt-style argument (highest priority - explicit user choice)
            # 2. Custom image describer config default prompt style (if --config-id provided)
            # 3. workflow_config.json step config prompt style (fallback)
            # 4. Let image_describer.py use its own defaults (no --prompt-style passed)
            prompt_style_to_use = None
            prompt_source = None
            
            if self.override_prompt_style:
                # Priority 1: Command-line argument
                prompt_style_to_use = self.override_prompt_style
                prompt_source = "command-line argument"
            elif self.image_describer_config:
                # Priority 2: Custom image describer config default prompt style
                custom_style = get_default_prompt_style(self.image_describer_config)
                if custom_style:
                    prompt_style_to_use = custom_style
                    prompt_source = f"custom config '{self.image_describer_config}'"
            
            if not prompt_style_to_use and "prompt_style" in step_config and step_config["prompt_style"]:
                # Priority 3: workflow_config.json step config
                prompt_style_to_use = step_config["prompt_style"]
                prompt_source = "workflow_config.json"
            
            if prompt_style_to_use:
                validated_style = validate_prompt_style(prompt_style_to_use)
                cmd.extend(["--prompt-style", validated_style])
                self.logger.info(f"Using prompt style '{validated_style}' from {prompt_source}")
            
            # Add timeout parameter for Ollama requests
            if self.timeout != 90:  # Only add if non-default
                cmd.extend(["--timeout", str(self.timeout)])
                self.logger.info(f"Using custom timeout: {self.timeout} seconds")
            
            # Add workflow name if available (for window title identification)
            if self.workflow_name:
                cmd.extend(["--workflow-name", self.workflow_name])
            
            # Add metadata configuration
            # Note: The config file controls metadata by default; we update it dynamically before running
            # This allows the workflow to control metadata settings
            if not self.enable_metadata:
                # If metadata explicitly disabled, we could pass a custom config
                # For now, metadata is handled via the config file which defaults to enabled
                pass
            
            # Single call to image_describer.py with all images
            self.logger.info(f"Running single image description process: {' '.join(cmd)}")
            
            # Store total images for status updates
            self.step_results['describe'] = {
                'in_progress': True,
                'total': len(combined_image_list),
                'processed': 0
            }
            self._update_status_log()
            
            # Determine progress file location (same logic as image_describer.py)
            # IMPORTANT: Check --log-dir FIRST because that's where image_describer.py writes it
            progress_file = None
            for arg_i, arg in enumerate(cmd):
                if arg == "--log-dir" and arg_i + 1 < len(cmd):
                    progress_file = Path(cmd[arg_i + 1]) / "image_describer_progress.txt"
                    self.logger.info(f"Progress file location from --log-dir: {progress_file}")
                    break
            
            # Fallback to --output-dir if --log-dir not found
            if progress_file is None:
                for arg_i, arg in enumerate(cmd):
                    if arg == "--output-dir" and arg_i + 1 < len(cmd):
                        progress_file = Path(cmd[arg_i + 1]) / "image_describer_progress.txt"
                        self.logger.info(f"Progress file location from --output-dir: {progress_file}")
                        break
            
            if progress_file is None:
                # Final fallback to output directory
                progress_file = self.config.base_output_dir / "descriptions" / "image_describer_progress.txt"
                self.logger.info(f"Progress file location (fallback): {progress_file}")
            
            # Start the subprocess with real-time progress monitoring
            import threading
            import time
            
            def monitor_progress():
                """Monitor the progress file and update status in real-time"""
                last_count = 0
                last_status_update = 0
                checks_without_file = 0
                iteration = 0
                self.logger.info("Progress monitoring thread started")
                while self.step_results.get('describe', {}).get('in_progress', False):
                    iteration += 1
                    try:
                        if progress_file.exists():
                            if checks_without_file > 0:
                                self.logger.info(f"Progress file appeared after {checks_without_file} checks: {progress_file}")
                                checks_without_file = 0
                            # Count lines in progress file (each line = one completed image)
                            with open(progress_file, 'r', encoding='utf-8') as f:
                                lines = f.readlines()
                                current_count = len([line.strip() for line in lines if line.strip()])
                            
                            # Log every 5 checks to see if thread is running
                            if iteration % 5 == 0:
                                self.logger.debug(f"Monitoring check #{iteration}: {current_count}/{self.step_results['describe']['total']} images")
                            
                            if current_count != last_count:
                                # Update step results
                                self.step_results['describe']['processed'] = current_count
                                # Update status log
                                self._update_status_log()
                                # Log every 10 images or when transitioning from 0
                                if current_count - last_status_update >= 10 or (last_count == 0 and current_count > 0):
                                    self.logger.info(f"Progress update: {current_count}/{self.step_results['describe']['total']} images described, status.log updated")
                                    last_status_update = current_count
                                elif current_count > 0:  # Log less frequently for intermediate updates
                                    self.logger.debug(f"Progress: {current_count}/{self.step_results['describe']['total']} images")
                                last_count = current_count
                        else:
                            checks_without_file += 1
                            if checks_without_file == 1:
                                self.logger.info(f"Waiting for progress file to be created: {progress_file}")
                            elif checks_without_file % 10 == 0:  # Log every 100 seconds
                                self.logger.warning(f"Progress file still not found after {checks_without_file} checks ({checks_without_file * 10}s)")
                        
                        time.sleep(10)  # Check every 10 seconds
                    except Exception as e:
                        self.logger.warning(f"Progress monitoring error: {e}")
                        import traceback
                        self.logger.warning(f"Traceback: {traceback.format_exc()}")
                        time.sleep(5)  # Wait longer on error
                
                self.logger.info(f"Progress monitoring thread ending after {iteration} iterations")
            
            # Start progress monitoring in background thread
            self.logger.info(f"Starting progress monitoring thread (checking {progress_file} every 2 seconds)")
            self.logger.info(f"Monitoring will track: {len(combined_image_list)} total images")
            progress_thread = threading.Thread(target=monitor_progress, daemon=True)
            progress_thread.start()
            
            # Stream output directly to terminal for real-time progress feedback
            result = subprocess.run(cmd, text=True, encoding='utf-8', errors='replace')
            
            # Mark description as no longer in progress
            if 'describe' in self.step_results:
                self.step_results['describe']['in_progress'] = False
                # Final update with actual completion count
                if progress_file.exists():
                    try:
                        with open(progress_file, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                            final_count = len([line.strip() for line in lines if line.strip()])
                        self.step_results['describe']['processed'] = final_count
                    except Exception as e:
                        self.logger.debug(f"Error reading final progress count: {e}")
                self._update_status_log()
            
            # Mark description as no longer in progress
            if 'describe' in self.step_results:
                self.step_results['describe']['in_progress'] = False
            
            # Save file path mapping before cleaning up temp directory
            # This allows import tools to map temp paths back to originals
            mapping_file = self.config.base_output_dir / "descriptions" / "file_path_mapping.json"
            try:
                import json
                mapping = {}
                for temp_path, original_path in combined_image_list:
                    # Store relative temp path as key, absolute original path as value
                    try:
                        temp_relative = temp_path.relative_to(temp_combined_dir)
                        mapping[str(temp_relative)] = str(original_path)
                    except ValueError:
                        # Fallback if relative path fails
                        mapping[str(temp_path.name)] = str(original_path)
                
                with open(mapping_file, 'w', encoding='utf-8') as f:
                    json.dump(mapping, f, indent=2)
                self.logger.info(f"Saved file path mapping to {mapping_file}")
            except Exception as e:
                self.logger.warning(f"Failed to save file path mapping: {e}")
            
            # Clean up temporary directory
            try:
                shutil.rmtree(temp_combined_dir)
                self.logger.debug(f"Cleaned up temporary directory: {temp_combined_dir}")
            except Exception as e:
                self.logger.warning(f"Failed to clean up temporary directory {temp_combined_dir}: {e}")
            
            if result.returncode == 0:
                self.logger.info("Image description completed successfully")
                total_processed = len(combined_image_list)
                
                # Validate that we described the expected number of images
                if total_processed != unique_source_count:
                    self.logger.warning(f"Description count mismatch: processed {total_processed} but expected {unique_source_count} unique images")
                else:
                    self.logger.info(f"Validation: All {unique_source_count} unique images were described")
            else:
                self.logger.error(f"Image description failed: {result.stderr}")
                return {
                    "success": False, 
                    "error": f"Image description process failed: {result.stderr}",
                    "unique_images": unique_source_count,
                    "conversions": conversion_count
                }
            
            # Check if description file was created
            target_desc_file = output_dir / "image_descriptions.txt"
            
            if target_desc_file.exists():
                self.logger.info(f"Descriptions saved to: {target_desc_file}")
                
                return {
                    "success": True,
                    "processed": total_processed,
                    "unique_images": unique_source_count,
                    "conversions": conversion_count,
                    "output_dir": output_dir,
                    "description_file": target_desc_file
                }
            else:
                self.logger.warning("Description file was not created")
                return {
                    "success": False, 
                    "error": "Description file not created",
                    "unique_images": unique_source_count,
                    "conversions": conversion_count
                }
                
        except Exception as e:
            self.logger.error(f"Error during image description: {e}")
            return {
                "success": False, 
                "error": str(e),
                "unique_images": unique_source_count if 'unique_source_count' in locals() else 0,
                "conversions": conversion_count if 'conversion_count' in locals() else 0
            }
    
    def generate_html(self, input_dir: Path, output_dir: Path, description_file: Optional[Path] = None) -> Dict[str, Any]:
        """
        Generate HTML report from descriptions using descriptions_to_html.py
        
        Args:
            input_dir: Directory that was processed
            output_dir: Output directory for HTML report
            description_file: Specific description file to process
            
        Returns:
            Dictionary with step results
        """
        self.logger.info("Starting HTML generation...")
        
        # Find description file
        if description_file and description_file.exists():
            desc_file = description_file
        else:
            # Look for description files in input directory
            desc_files = self.discovery.find_files_by_type(input_dir, "descriptions")
            
            # Also check the standard descriptions output directory
            descriptions_dir = self.config.get_step_output_dir("image_description")
            if not desc_files and descriptions_dir.exists():
                desc_files = self.discovery.find_files_by_type(descriptions_dir, "descriptions")
            
            if not desc_files:
                # Check if descriptions were created in a previous step
                if "describe" in self.step_results and self.step_results["describe"].get("description_file"):
                    desc_file = self.step_results["describe"]["description_file"]
                else:
                    self.logger.warning("No description files found for HTML generation")
                    return {"success": True, "processed": 0, "output_dir": output_dir}
            else:
                desc_file = desc_files[0]  # Use first found file
        
        self.logger.info(f"Using description file: {desc_file}")
        
        try:
            # Get HTML generation settings
            step_config = self.config.get_step_config("html_generation")
            
            # Create output file path
            output_dir.mkdir(parents=True, exist_ok=True)
            html_file = output_dir / "image_descriptions.html"
            
            # Build command
            if getattr(sys, 'frozen', False):
                # Use dispatcher alias inside frozen exe
                cmd = [
                    sys.executable, "descriptions-to-html",
                    str(desc_file),
                    str(html_file),
                    "--title", step_config.get("title", "Image Analysis Report"),
                    "--log-dir", str(self.config.base_output_dir / "logs")
                ]
            else:
                cmd = [
                    sys.executable, "descriptions_to_html.py",
                    str(desc_file),
                    str(html_file),
                    "--title", step_config.get("title", "Image Analysis Report"),
                    "--log-dir", str(self.config.base_output_dir / "logs")
                ]
            
            if step_config.get("include_details", False):
                cmd.append("--full")
            
            self.logger.info(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, text=True, encoding='utf-8', errors='replace')
            
            if result.returncode == 0:
                self.logger.info("HTML generation completed successfully")
                
                return {
                    "success": True,
                    "processed": 1,
                    "output_dir": output_dir,
                    "html_file": html_file
                }
            else:
                self.logger.error(f"HTML generation failed with exit code {result.returncode}")
                return {"success": False, "error": f"Process failed with exit code {result.returncode}. Check log file for details."}
                
        except Exception as e:
            self.logger.error(f"Error during HTML generation: {e}")
            return {"success": False, "error": str(e)}
    
    def run_workflow(self, input_dir: Path, output_dir: Path, steps: List[str], 
                     workflow_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Run the complete workflow
        
        Args:
            input_dir: Input directory containing media files
            output_dir: Base output directory
            steps: List of workflow steps to execute
            workflow_metadata: Optional metadata to save about this workflow
            
        Returns:
            Dictionary with overall workflow results
        """
        self.logger.info(f"Starting workflow with steps: {', '.join(steps)}")
        self.logger.info(f"Input directory: {input_dir}")
        self.logger.info(f"Output directory: {output_dir}")
        
        # Log environment information
        workflow_name = workflow_metadata.get('workflow_name', 'workflow') if workflow_metadata else 'workflow'
        log_dir = output_dir / "logs"
        log_environment_info(log_dir, workflow_name)
        
        # Initialize workflow statistics
        start_time = datetime.now()
        self.statistics['start_time'] = start_time.isoformat()
        
        # Update initial status
        self._update_status_log()
        
        # Set base output directory in config
        self.config.set_base_output_dir(output_dir)
        
        # Create workflow directory structure
        workflow_paths = create_workflow_paths(output_dir)
        
        # Create helper batch files immediately (view_results.bat and resume_workflow.bat)
        create_workflow_helper_files(output_dir)
        self.logger.info("Created workflow helper files: view_results.bat and resume_workflow.bat")
        
        # Save workflow metadata if provided
        if workflow_metadata:
            save_workflow_metadata(output_dir, workflow_metadata)
            self.logger.info(f"Workflow name: {workflow_metadata.get('workflow_name', 'N/A')}")
        
        workflow_results = {
            "success": True,
            "steps_completed": [],
            "steps_failed": [],
            "input_dir": str(input_dir),
            "output_dir": str(output_dir),
            "start_time": start_time.isoformat()
        }
        
        # Keep track of where processed files are for next steps
        current_input_dir = input_dir
        
        # Execute workflow steps
        for step in steps:
            if step not in self.available_steps:
                self.logger.error(f"Unknown workflow step: {step}")
                workflow_results["steps_failed"].append(step)
                continue
            
            step_method = getattr(self, self.available_steps[step])
            step_output_dir = self.config.get_step_output_dir(
                {"download": "image_download", "video": "video_extraction", "convert": "image_conversion", 
                 "describe": "image_description", "html": "html_generation"}[step]
            )
            
            try:
                # Special handling for different steps
                if step == "html":
                    # HTML generation needs description file
                    desc_file = None
                    if "describe" in self.step_results and self.step_results["describe"].get("description_file"):
                        desc_file = self.step_results["describe"]["description_file"]
                    step_result = step_method(current_input_dir, step_output_dir, desc_file)
                elif step == "describe":
                    # Description step should look at current input directory (after download/convert)
                    step_result = step_method(current_input_dir, step_output_dir)
                elif step == "convert":
                    # Convert step should always work on original input directory
                    step_result = step_method(input_dir, step_output_dir)
                else:
                    # Video step and others use current_input_dir
                    step_result = step_method(current_input_dir, step_output_dir)
                
                self.step_results[step] = step_result
                
                # Update statistics based on step results
                self._update_statistics(step, step_result)
                
                if step_result["success"]:
                    self.statistics['steps_completed'].append(step)
                    workflow_results["steps_completed"].append(step)
                    self.logger.info(f"Step '{step}' completed successfully")
                    
                    # Update status log after successful step
                    self._update_status_log()
                    
                    # Update input directory for next step if this step produced outputs
                    if step in ["download", "video", "convert"] and step_result.get("output_dir"):
                        current_input_dir = Path(step_result["output_dir"])
                else:
                    self.statistics['steps_failed'].append(step)
                    workflow_results["steps_failed"].append(step)
                    workflow_results["success"] = False
                    self.logger.error(f"Step '{step}' failed: {step_result.get('error', 'Unknown error')}")
                    
                    # Update status log after failed step
                    self._update_status_log()
                    
            except Exception as e:
                self.statistics['errors_encountered'] += 1
                self.statistics['steps_failed'].append(step)
                self.logger.error(f"Error executing step '{step}': {e}")
                workflow_results["steps_failed"].append(step)
                workflow_results["success"] = False
                self.step_results[step] = {"success": False, "error": str(e)}
                
                # Update status log after error
                self._update_status_log()
        
        # Finalize statistics and logging
        end_time = datetime.now()
        self.statistics['end_time'] = end_time.isoformat()
        workflow_results["end_time"] = end_time.isoformat()
        workflow_results["step_results"] = self.step_results
        
        # Log comprehensive final statistics
        self._log_final_statistics(start_time, end_time)
        
        # Final status update
        self._update_status_log()
        
        return workflow_results
    
    def _update_statistics(self, step: str, step_result: Dict[str, Any]) -> None:
        """Update workflow statistics based on step results"""
        if step_result.get("success"):
            processed = step_result.get("processed", 0)
            if step == "download":
                count = step_result.get("count", 0)
                self.statistics['total_downloads'] += count
                self.statistics['total_files_processed'] += count
            elif step == "video":
                self.statistics['total_videos_processed'] += processed
            elif step == "convert":
                self.statistics['total_conversions'] += processed
                # Don't count conversions as images processed - they're format conversions of existing images
            elif step == "describe":
                # Use unique_images count if available, otherwise fall back to processed
                unique_images = step_result.get("unique_images", processed)
                conversions = step_result.get("conversions", 0)
                
                self.statistics['total_descriptions'] += processed
                self.statistics['total_images_processed'] += unique_images
                
                # Track conversions if not already tracked in convert step
                if conversions > 0 and self.statistics['total_conversions'] == 0:
                    self.statistics['total_conversions'] = conversions
            
            # For total files processed, count unique items not duplicates
            if step == "video":
                self.statistics['total_files_processed'] += processed
            elif step == "describe":
                unique_images = step_result.get("unique_images", processed)
                self.statistics['total_files_processed'] += unique_images
    
    def _log_final_statistics(self, start_time: datetime, end_time: datetime) -> None:
        """Log comprehensive final workflow statistics"""
        total_time = (end_time - start_time).total_seconds()
        
        self.logger.info("\n" + "="*60)
        self.logger.info("FINAL WORKFLOW STATISTICS")
        self.logger.info("="*60)
        
        # Configuration information
        self.logger.info(f"AI Provider: {self.provider}")
        if self.override_model:
            self.logger.info(f"Model: {self.override_model}")
        if self.override_prompt_style:
            self.logger.info(f"Prompt Style: {self.override_prompt_style}")
        
        # Time statistics
        self.logger.info(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"Total execution time: {total_time:.2f} seconds ({total_time/60:.1f} minutes)")
        
        # File processing statistics
        self.logger.info(f"Total files processed: {self.statistics['total_files_processed']}")
        if self.statistics['total_downloads'] > 0:
            self.logger.info(f"Images downloaded: {self.statistics['total_downloads']}")
        self.logger.info(f"Videos processed: {self.statistics['total_videos_processed']}")
        self.logger.info(f"Unique images processed: {self.statistics['total_images_processed']}")
        if self.statistics['total_conversions'] > 0:
            self.logger.info(f"Format conversions (HEIC to JPG): {self.statistics['total_conversions']}")
        self.logger.info(f"Descriptions generated: {self.statistics['total_descriptions']}")
        
        # Step completion statistics
        self.logger.info(f"Steps completed: {len(self.statistics['steps_completed'])}")
        if self.statistics['steps_completed']:
            self.logger.info(f"Completed steps: {', '.join(self.statistics['steps_completed'])}")
        
        if self.statistics['steps_failed']:
            self.logger.info(f"Steps failed: {len(self.statistics['steps_failed'])}")
            self.logger.info(f"Failed steps: {', '.join(self.statistics['steps_failed'])}")
        
        # Performance metrics
        if total_time > 0 and self.statistics['total_files_processed'] > 0:
            files_per_second = self.statistics['total_files_processed'] / total_time
            self.logger.info(f"Average processing rate: {files_per_second:.2f} files/second")
        
        # Error tracking
        self.logger.info(f"Errors encountered: {self.statistics['errors_encountered']}")
        
        self.logger.info("="*60)
    
    def _update_frame_extractor_config(self, config_file: str, output_dir: Path) -> None:
        """
        Temporarily update frame extractor config to use workflow output directory
        
        Args:
            config_file: Path to frame extractor config file
            output_dir: Desired output directory
        """
        try:
            # Load current config
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            # Update output directory
            config["output_directory"] = str(output_dir)
            
            # Save updated config
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=4)
                
            self.logger.debug(f"Updated frame extractor config: {config_file}")
            
        except Exception as e:
            self.logger.warning(f"Could not update frame extractor config: {e}")


def parse_workflow_state(output_dir: Path) -> Dict[str, Any]:
    """
    Parse workflow logs to determine completion state and original parameters
    
    Args:
        output_dir: Workflow output directory containing logs
        
    Returns:
        Dictionary with workflow state information
    """
    state = {
        "valid": False,
        "input_dir": None,
        "steps": [],
        "completed_steps": [],
        "failed_steps": [],
        "partially_completed_steps": [],
        "model": None,
        "prompt_style": None,
        "provider": None,
        "config": None,
        "can_resume": False,
        "resume_from_step": None,
        "describe_progress": None
    }
    
    # Find workflow log file
    logs_dir = output_dir / "logs"
    if not logs_dir.exists():
        return state
    
    workflow_logs = list(logs_dir.glob("workflow_*.log"))
    if not workflow_logs:
        return state
    
    # Find the log file with actual workflow data (not dry-run logs)
    workflow_log = None
    for log_file in workflow_logs:
        try:
            with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                # Look for actual workflow start, not dry-run
                if "Starting workflow with steps:" in content and "Dry run mode" not in content:
                    workflow_log = log_file
                    break
        except Exception:
            continue
    
    # If no valid workflow log found, use most recent as fallback
    if not workflow_log:
        workflow_log = max(workflow_logs, key=lambda x: x.stat().st_mtime)
    
    try:
        with open(workflow_log, 'r', encoding='utf-8', errors='replace') as f:
            log_content = f.read()
        
        # Extract basic workflow info from log
        lines = log_content.split('\n')
        
        for line in lines:
            if "Starting workflow with steps:" in line:
                # Extract steps: "Starting workflow with steps: video, convert, describe, html"
                steps_part = line.split("Starting workflow with steps:")[1].strip()
                # Remove timestamp if present (format: " - (2025-10-12 21:42:28,443)")
                if " - (" in steps_part:
                    steps_part = steps_part.split(" - (")[0].strip()
                state["steps"] = [s.strip() for s in steps_part.split(',')]
            
            elif "Input directory:" in line:
                # Extract input directory
                input_part = line.split("Input directory:")[1].strip()
                # Remove timestamp if present (format: " - (2025-10-12 21:42:28,443)")
                if " - (" in input_part:
                    input_part = input_part.split(" - (")[0].strip()
                state["input_dir"] = input_part
            
            elif "Step '" in line and ("' completed successfully" in line or "' completed" in line):
                # Extract completed steps - handle both old and new log formats
                if "' completed successfully" in line:
                    step_name = line.split("Step '")[1].split("' completed successfully")[0]
                else:
                    step_name = line.split("Step '")[1].split("' completed")[0]
                if step_name not in state["completed_steps"]:
                    state["completed_steps"].append(step_name)
            
            elif "Step '" in line and "' failed:" in line:
                # Extract failed steps
                step_name = line.split("Step '")[1].split("'")[0]
                if step_name not in state["failed_steps"]:
                    state["failed_steps"].append(step_name)
        
        # Check for partial completion of describe step
        if "describe" in state["steps"] and "describe" not in state["completed_steps"] and "describe" not in state["failed_steps"]:
            # Check if descriptions file exists and has content
            desc_file = output_dir / "descriptions" / "image_descriptions.txt"
            if desc_file.exists():
                try:
                    with open(desc_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Count actual image descriptions by counting "File:" entries
                        existing_descriptions = content.count("File: ")
                    if existing_descriptions > 0:
                        state["partially_completed_steps"].append("describe")
                        state["describe_progress"] = existing_descriptions
                except Exception:
                    pass
        
        # Parse command line from log to extract model and other parameters
        for line in lines:
            if "Original command:" in line:
                # This is the logged original command
                cmd_line = line.split("Original command:")[1].strip()
                
                # Parse command line arguments
                import shlex
                try:
                    cmd_args = shlex.split(cmd_line)
                    # Find workflow.py and parse arguments after it
                    for i, arg in enumerate(cmd_args):
                        if arg.endswith("workflow.py"):
                            remaining_args = cmd_args[i+1:]
                            # Parse the arguments
                            for j, arg in enumerate(remaining_args):
                                if arg == "--model" and j+1 < len(remaining_args):
                                    state["model"] = remaining_args[j+1]
                                elif arg == "--prompt-style" and j+1 < len(remaining_args):
                                    state["prompt_style"] = remaining_args[j+1]
                                elif arg == "--provider" and j+1 < len(remaining_args):
                                    state["provider"] = remaining_args[j+1]
                                elif arg == "--config" and j+1 < len(remaining_args):
                                    state["config"] = remaining_args[j+1]
                            break
                except Exception:
                    pass  # Ignore parsing errors
        

        # Also try to extract model and prompt from subprocess commands (for older logs)
        if not state["model"] or not state["prompt_style"] or not state["provider"]:
            for line in lines:
                if "image_describer.py" in line and ("--model" in line or "--provider" in line):
                    # Extract from subprocess command lines like:
                    # python.exe image_describer.py ... --model gemma3 --prompt-style artistic --provider ollama
                    import shlex
                    try:
                        # Find the part after image_describer.py
                        parts = line.split('image_describer.py', 1)
                        if len(parts) > 1:
                            args_part = parts[1].strip()
                            # Use shlex to properly parse the arguments
                            tokens = shlex.split(args_part)
                            for i, token in enumerate(tokens):
                                if token == "--model" and i+1 < len(tokens) and not state["model"]:
                                    state["model"] = tokens[i+1]
                                elif token == "--prompt-style" and i+1 < len(tokens) and not state["prompt_style"]:
                                    state["prompt_style"] = tokens[i+1]
                                elif token == "--provider" and i+1 < len(tokens) and not state["provider"]:
                                    state["provider"] = tokens[i+1]
                    except Exception:
                        pass  # Ignore parsing errors

        # Determine if workflow can be resumed
        if state["steps"] and state["input_dir"]:
            state["valid"] = True
            
            # Check if workflow is incomplete
            total_steps = len(state["steps"])
            completed_steps = len(state["completed_steps"])
            
            if completed_steps < total_steps and not state["failed_steps"]:
                state["can_resume"] = True
                
                # Find the next step to resume from
                for step in state["steps"]:
                    if step not in state["completed_steps"]:
                        state["resume_from_step"] = step
                        break
    
    except Exception as e:
        # Log parsing failed
        print(f"Warning: Could not parse workflow state: {e}")
    
    return state


def prompt_view_results() -> bool:
    """
    Prompt user if they want to view workflow results in the viewer.
    Returns True if user wants to view results, False otherwise.
    """
    try:
        response = input("\nWould you like to view the results in the viewer? (y/n): ").strip().lower()
        return response in ('y', 'yes')
    except (EOFError, KeyboardInterrupt):
        return False


def launch_viewer(output_dir, logger: logging.Logger) -> None:
    """
    Launch the viewer application with the specified output directory.
    Also creates a reusable .bat file for future viewing.
    
    Args:
        output_dir: Path to the workflow output directory (Path object or string)
        logger: Logger instance for recording actions
    """
    try:
        # Ensure output_dir is a Path object
        if not isinstance(output_dir, Path):
            output_dir = Path(output_dir)
        
        # Get the base path (for both dev and executable scenarios)
        if getattr(sys, 'frozen', False):
            # Running as executable
            base_dir = Path(sys.executable).parent
            viewer_exe = base_dir / "viewer" / "viewer.exe"
        else:
            # Running from source
            base_dir = Path(__file__).parent.parent
            viewer_exe = base_dir / "viewer" / "viewer.py"
        
        # Create a reusable .bat file in the output directory
        bat_file = output_dir / "view_results.bat"
        try:
            with open(bat_file, 'w', encoding='utf-8') as f:
                f.write("@echo off\n")
                f.write("REM Auto-generated batch file to view workflow results\n")
                f.write("REM Double-click this file to reopen the results in the viewer\n\n")
                
                if getattr(sys, 'frozen', False):
                    # For executable deployment
                    f.write(f'"{viewer_exe}" "{output_dir}"\n')
                else:
                    # For development (need Python)
                    python_exe = sys.executable
                    f.write(f'"{python_exe}" "{viewer_exe}" "{output_dir}"\n')
                
                f.write("\nREM If viewer closes immediately, run this from a command prompt to see any errors\n")
            
            logger.info(f"Created reusable viewer launcher: {bat_file}")
            print(f"INFO: Created reusable launcher: {bat_file}")
            print("      Double-click this file anytime to view results again.")
        except Exception as e:
            logger.warning(f"Failed to create .bat file: {e}")
        
        # Launch the viewer
        if viewer_exe.exists():
            logger.info(f"Launching viewer with directory: {output_dir}")
            print(f"\nINFO: Launching viewer...")
            
            if getattr(sys, 'frozen', False):
                # Launch executable
                subprocess.Popen([str(viewer_exe), str(output_dir)], 
                               creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
            else:
                # Launch Python script
                subprocess.Popen([sys.executable, str(viewer_exe), str(output_dir)])
            
            logger.info("Viewer launched successfully")
            print("INFO: Viewer launched successfully")
        else:
            logger.error(f"Viewer not found at: {viewer_exe}")
            print(f"ERROR: Viewer not found at: {viewer_exe}")
    
    except Exception as e:
        logger.error(f"Failed to launch viewer: {e}")
        print(f"ERROR: Failed to launch viewer: {e}")


def normalize_model_name(model: str, provider: str) -> str:
    """
    Normalize model name by stripping provider prefix if present.
    
    Users might specify: ollama:llama3.2-vision:11b
    But Ollama API expects: llama3.2-vision:11b
    
    Args:
        model: Model name that may include provider prefix
        provider: Provider name (ollama, openai, claude, onnx)
    
    Returns:
        Model name with provider prefix stripped if it matches the provider
    """
    if not model:
        return model
    
    # Strip provider prefix if present (e.g., "ollama:llama3.2-vision:11b" -> "llama3.2-vision:11b")
    prefix = f"{provider}:"
    if model.startswith(prefix):
        return model[len(prefix):]
    
    return model


def main():
    """Main function for command-line usage"""
    parser = argparse.ArgumentParser(
        description="Image Description Toolkit - Complete Workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Workflow Steps:
  video   - Extract frames from video files
  convert - Convert HEIC images to JPG
  describe - Generate AI descriptions for images  
  html    - Create HTML report from descriptions

Examples:
  # Ollama (default)
  idt workflow media_folder
  idt workflow media_folder --output-dir results
  idt workflow photos --steps describe,html
  idt workflow videos --steps video,describe,html --model llava:7b
  
  # OpenAI
  idt workflow photos --provider openai --model gpt-4o-mini --api-key-file openai.txt
  idt workflow media --provider openai --model gpt-4o --steps describe,html
  
  # Claude (Anthropic)
  idt workflow photos --provider claude --model claude-sonnet-4-5-20250929 --api-key-file claude.txt
  idt workflow media --provider claude --model claude-3-5-haiku-20241022 --steps describe,html
  
  # Custom Configuration Files
  idt workflow photos --config-image-describer scripts/my_prompts.json --prompt-style artistic
  idt workflow photos --config-id scripts/my_prompts.json  # Short form
  idt workflow photos --config scripts/my_prompts.json     # Deprecated but still works
  
Resume Examples:
  idt workflow --resume workflow_output_20250919_153443
  idt workflow --resume /path/to/interrupted/workflow
  
  # ⚠️ Cloud providers require API key when resuming:
  idt workflow --resume wf_openai_gpt-4o-mini_20251005_122700 --api-key-file openai.txt
  idt workflow --resume wf_claude_sonnet-4-5_20251005_150328 --api-key-file claude.txt
  # See docs/WORKFLOW_RESUME_API_KEY.md for details

Redescribe Examples (reuse images with different AI settings):
  # Compare different models on same images (skips video/convert steps)
  idt workflow --redescribe wf_photos_ollama_llava_narrative_20251115_100000 \\
    --provider openai --model gpt-4o
  
  # Try different prompt styles
  idt workflow --redescribe wf_photos_ollama_llava_narrative_20251115_100000 \\
    --prompt-style technical
  
  # Test local ONNX model vs cloud
  idt workflow --redescribe wf_photos_openai_gpt-4o_narrative_20251115_100000 \\
    --provider onnx --model microsoft/Florence-2-base
  
  # Use symlinks to save disk space (faster, 0 MB used)
  idt workflow --redescribe wf_photos_ollama_llava_narrative_20251115_100000 \\
    --provider claude --model claude-sonnet-4-5 --link-images
  
Viewing Results:
  # Launch viewer automatically at workflow start (recommended for long batches):
  idt workflow photos --view-results
  idt workflow --resume wf_photos --view-results
  
  # Or you'll be prompted after successful completion
  # Or launch it manually anytime:
  idt viewer [workflow_directory]
        """
    )
    
    parser.add_argument(
        "input_source",
        nargs='?',  # Make input_source optional when using --resume
        help="Input directory containing media files, or URL to download images from (e.g., https://example.com)"
    )
    
    parser.add_argument(
        "--download", "-d",
        help="Explicitly download images from this URL (alternative to providing URL as input_source)"
    )
    
    parser.add_argument(
        "--resume", "-r",
        help="Resume an interrupted workflow from the specified output directory"
    )
    
    parser.add_argument(
        "--redescribe",
        help="Re-describe images from an existing workflow with different AI settings, skipping video/image conversion"
    )
    
    parser.add_argument(
        "--preserve-descriptions",
        action="store_true",
        help="When resuming, preserve existing descriptions and skip describe step if substantial progress exists"
    )
    
    parser.add_argument(
        "--link-images",
        action="store_true",
        help="When redescribing, use symlinks/hardlinks instead of copying images (faster, no space duplication)"
    )
    
    parser.add_argument(
        "--force-copy",
        action="store_true",
        help="When redescribing, always copy images even if linking is available"
    )
    
    parser.add_argument(
        "--output-dir", "-o",
        help="Output directory for workflow results (default: workflow_output)"
    )
    
    parser.add_argument(
        "--steps", "-s",
        default="video,convert,describe,html",
        help="Comma-separated list of workflow steps (default: video,convert,describe,html)"
    )
    
    # Configuration file arguments (explicit types)
    parser.add_argument(
        "--config-workflow", "--config-wf",
        default="workflow_config.json",
        help="Path to workflow orchestration config file (default: workflow_config.json)"
    )
    
    parser.add_argument(
        "--config-image-describer", "--config-id",
        help="Path to image describer config file (prompts, AI settings, metadata)"
    )
    
    parser.add_argument(
        "--config-video",
        help="Path to video frame extraction config file"
    )
    
    # Deprecated: Keep for backward compatibility
    parser.add_argument(
        "--config",
        dest="_deprecated_config",
        help="[DEPRECATED] Use --config-image-describer instead. This alias will be removed in v4.0."
    )
    
    parser.add_argument(
        "--model",
        help="Override AI model for image description"
    )
    
    parser.add_argument(
        "--provider",
        choices=["ollama", "openai", "claude", "onnx"],
        default="ollama",
        help="AI provider to use for image description (default: ollama)"
    )
    
    parser.add_argument(
        "--api-key-file",
        help="Path to file containing API key for cloud providers (OpenAI, Claude, HuggingFace)"
    )
    
    parser.add_argument(
        "--prompt-style",
        help="Override prompt style for image description"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=90,
        help="Timeout in seconds for Ollama API requests (default: 90). Increase for slower hardware or large models."
    )
    
    parser.add_argument(
        "--name",
        help="Custom workflow name identifier (e.g., 'VacationPhotos' or 'TestingExample'). Case is preserved in metadata/display. If not provided, auto-generates from input directory path."
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--progress-status",
        action="store_true",
        help="Enable live progress status updates in console (shows all INFO messages and status.log updates)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without executing"
    )
    
    parser.add_argument(
        "--view-results",
        action="store_true",
        help="Automatically launch viewer to monitor workflow progress in real-time"
    )
    
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Non-interactive mode - skip prompts (useful for running multiple workflows sequentially)"
    )
    
    parser.add_argument(
        "--metadata",
        action="store_true",
        default=None,
        help="Enable metadata extraction (GPS, dates, camera info). Enabled by default if not specified."
    )
    
    parser.add_argument(
        "--no-metadata",
        action="store_true",
        help="Disable metadata extraction"
    )
    
    parser.add_argument(
        "--no-geocode",
        action="store_true",
        help="Disable reverse geocoding (geocoding is enabled by default to convert GPS coordinates to city/state/country)"
    )
    
    parser.add_argument(
        "--geocode-cache",
        default="geocode_cache.json",
        help="Path to geocoding cache file (default: geocode_cache.json)"
    )
    
    # Web image download arguments
    parser.add_argument(
        "--url",
        help="URL to download images from (enables web download step)"
    )
    
    parser.add_argument(
        "--min-size",
        help="Minimum image size filter (e.g. '100KB', '1MB')"
    )
    
    parser.add_argument(
        "--max-images",
        type=int,
        help="Maximum number of images to download"
    )
    
    parser.add_argument(
        "--original-cwd",
        help=argparse.SUPPRESS  # Hidden argument for wrapper communication
    )
    
    args = parser.parse_args()
    
    # Handle deprecated --config argument
    if hasattr(args, '_deprecated_config') and args._deprecated_config:
        print("WARNING: --config is deprecated and will be removed in v4.0.")
        print("         Use --config-image-describer (or --config-id) instead.")
        print(f"         Treating '{args._deprecated_config}' as image describer config.")
        if not args.config_image_describer:
            args.config_image_describer = args._deprecated_config
    
    # Handle resume mode
    if args.resume:
        # Resume mode - validate resume directory and extract workflow state
        resume_dir = Path(args.resume)
        
        # Initialize variables that may not be set in resume mode
        url = None  # Resume mode doesn't use URL downloads
        
        if not resume_dir.is_absolute():
            # Use original working directory if provided, otherwise current directory
            base_dir = Path(args.original_cwd) if args.original_cwd else Path(os.getcwd())
            resume_dir = (base_dir / resume_dir).resolve()
        
        if not resume_dir.exists():
            print(f"ERROR: Resume directory does not exist: {resume_dir}")
            sys.exit(1)
        
        # Parse workflow state from logs
        workflow_state = parse_workflow_state(resume_dir)
        
        if not workflow_state["valid"]:
            print(f"ERROR: Cannot determine workflow state from: {resume_dir}")
            print("This directory does not appear to contain a valid workflow.")
            sys.exit(1)
        
        if not workflow_state["can_resume"]:
            if workflow_state["failed_steps"]:
                print(f"ERROR: Workflow has failed steps: {', '.join(workflow_state['failed_steps'])}")
                print("Cannot resume a failed workflow.")
            else:
                print(f"INFO: Workflow appears to be already complete.")
                print(f"Completed steps: {', '.join(workflow_state['completed_steps'])}")
                print("Nothing to resume.")
            sys.exit(0)
        
        # Set up resume parameters
        input_dir = Path(workflow_state["input_dir"])
        output_dir = resume_dir
        steps = workflow_state["steps"]
        
        # Load existing workflow metadata if it exists
        existing_metadata = load_workflow_metadata(resume_dir)
        
        if existing_metadata:
            # Use existing metadata
            workflow_name = existing_metadata.get("workflow_name", "resumed")
            workflow_name_display = workflow_name  # Preserve case from metadata
            provider_name = existing_metadata.get("provider", "ollama")
            model_name = existing_metadata.get("model", "unknown")
            prompt_style = existing_metadata.get("prompt_style", "narrative")
            timestamp = existing_metadata.get("timestamp", datetime.now().strftime("%Y%m%d_%H%M%S"))
        else:
            # Fallback: Extract from directory name or use defaults
            # Directory format: wf_NAME_PROVIDER_MODEL_PROMPT_TIMESTAMP
            dir_parts = resume_dir.name.split('_')
            if len(dir_parts) >= 5 and dir_parts[0] == 'wf':
                workflow_name = dir_parts[1]
                workflow_name_display = workflow_name  # Preserve case from directory name
                provider_name = dir_parts[2]
                model_name = dir_parts[3]
                prompt_style = dir_parts[4]
                timestamp = dir_parts[5] if len(dir_parts) > 5 else datetime.now().strftime("%Y%m%d_%H%M%S")
            else:
                # Ultimate fallback
                workflow_name = "resumed"
                workflow_name_display = "resumed"
                provider_name = "ollama"
                model_name = "unknown"
                prompt_style = "narrative"
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Override with state from logs
        if workflow_state["model"]:
            args.model = workflow_state["model"]
            model_name = workflow_state["model"]
        if workflow_state["prompt_style"]:
            args.prompt_style = workflow_state["prompt_style"]
            prompt_style = workflow_state["prompt_style"]
        if workflow_state["provider"]:
            args.provider = workflow_state["provider"]
            provider_name = workflow_state["provider"]
        if workflow_state["config"]:
            # Old workflow_state used single "config" - map to image_describer_config for backward compatibility
            args.config_image_describer = workflow_state["config"]
        
        # Restore custom config paths from metadata (new format)
        workflow_metadata = load_workflow_metadata(resume_dir)
        if workflow_metadata:
            if workflow_metadata.get("config_workflow"):
                args.config_workflow = workflow_metadata["config_workflow"]
            if workflow_metadata.get("config_image_describer"):
                args.config_image_describer = workflow_metadata["config_image_describer"]
            if workflow_metadata.get("config_video"):
                args.config_video = workflow_metadata["config_video"]
        
        # Filter steps to only include those not yet completed
        remaining_steps = []
        for step in steps:
            if step not in workflow_state["completed_steps"]:
                # Special handling for partially completed describe step
                if step == "describe" and step in workflow_state.get("partially_completed_steps", []):
                    desc_count = workflow_state.get('describe_progress', 0)
                    if desc_count > 0:
                        print(f"INFO: Describe step was partially completed ({desc_count} descriptions exist)")
                        
                        # Auto-enable preserve-descriptions for partial resumes to prevent data loss
                        if not args.preserve_descriptions:
                            print(f"INFO: Auto-enabling --preserve-descriptions to protect existing work")
                            args.preserve_descriptions = True
                        
                        print(f"Will continue describing remaining images (existing descriptions will be preserved)")
                
                remaining_steps.append(step)
        
        steps = remaining_steps
        
        if not steps:
            print("All workflow steps are already completed. Nothing to resume.")
            sys.exit(0)
        
        print(f"Resuming workflow from: {resume_dir}")
        print(f"Original input: {input_dir}")
        print(f"Completed steps: {', '.join(workflow_state['completed_steps'])}")
        print(f"Remaining steps: {', '.join(steps)}")
        
    elif args.redescribe:
        # Redescribe mode - reuse images from existing workflow with new AI settings
        source_dir = Path(args.redescribe)
        
        if not source_dir.is_absolute():
            # Use original working directory if provided, otherwise current directory
            base_dir = Path(args.original_cwd) if args.original_cwd else Path(os.getcwd())
            source_dir = (base_dir / source_dir).resolve()
        
        print("=" * 80)
        print("REDESCRIBE WORKFLOW")
        print("=" * 80)
        print()
        
        try:
            # Validate arguments and get source metadata
            source_metadata = validate_redescribe_args(args, source_dir)
            
            print(f"Source Workflow: {source_dir.name}")
            print(f"  Original Provider: {source_metadata.get('provider', 'unknown')}")
            print(f"  Original Model: {source_metadata.get('model', 'unknown')}")
            print(f"  Original Prompt: {source_metadata.get('prompt_style', 'unknown')}")
            print()
            
            # Determine new AI settings
            new_provider = args.provider
            new_model = args.model or get_default_model(new_provider)
            new_prompt = args.prompt_style or source_metadata.get("prompt_style", "narrative")
            
            print(f"New AI Configuration:")
            print(f"  Provider: {new_provider}")
            print(f"  Model: {new_model}")
            print(f"  Prompt Style: {new_prompt}")
            print()
            
            # Determine what can be reused
            print("Analyzing source workflow...")
            reusable_steps = determine_reusable_steps(source_dir, source_metadata)
            
            if not reusable_steps:
                print("ERROR: No reusable content found in source workflow")
                sys.exit(1)
            
            # Create new workflow directory
            workflow_name = source_metadata.get("workflow_name", "redescribe")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Sanitize components for directory name
            provider_sanitized = sanitize_name(new_provider)
            model_sanitized = sanitize_name(new_model)
            prompt_sanitized = sanitize_name(new_prompt)
            
            dir_name = f"wf_{workflow_name}_{provider_sanitized}_{model_sanitized}_{prompt_sanitized}_{timestamp}"
            
            # Determine output location
            if args.output_dir:
                output_base = Path(args.output_dir)
            else:
                # Use same parent directory as source workflow
                output_base = source_dir.parent
            
            output_dir = output_base / dir_name
            
            try:
                output_dir.mkdir(parents=True, exist_ok=False)
            except FileExistsError:
                print(f"ERROR: Output directory already exists: {output_dir}")
                sys.exit(1)
            
            print()
            print(f"New Workflow Directory: {output_dir.name}")
            print()
            
            # Reuse images
            print("Reusing processed images...")
            link_method = "link" if args.link_images else "force-copy" if args.force_copy else "auto"
            reuse_method = reuse_images(source_dir, output_dir, method=link_method)
            print()
            
            # Build redescribe metadata
            redescribe_metadata = {
                "is_redescribe": True,
                "source_workflow": str(source_dir.resolve()),
                "source_workflow_name": source_dir.name,
                "reused_steps": reusable_steps,
                "images_linked": reuse_method in ["hardlink", "symlink"],
                "link_method": reuse_method,
                "source_metadata": {
                    "original_provider": source_metadata.get("provider"),
                    "original_model": source_metadata.get("model"),
                    "original_prompt": source_metadata.get("prompt_style"),
                    "original_timestamp": source_metadata.get("timestamp")
                },
                "redescribe_timestamp": datetime.now().isoformat()
            }
            
            # Build full workflow metadata
            metadata = {
                "workflow_name": workflow_name,
                "provider": new_provider,
                "model": new_model,
                "prompt_style": new_prompt,
                "timestamp": timestamp,
                "redescribe_operation": redescribe_metadata,
                "steps_executed": ["describe", "html"],
                "config_workflow": args.config_workflow,
                "config_image_describer": args.config_image_describer
            }
            
            # Save metadata
            save_workflow_metadata(output_dir, metadata)
            
            # Set up for workflow execution
            # The orchestrator will scan all image directories in output_dir
            # (extracted_frames, converted_images, input_images)
            input_dir = output_dir
            steps = ["describe", "html"]  # Only run these steps
            
            # Store workflow info for later use
            workflow_name_display = workflow_name
            provider_name = new_provider
            model_name = new_model
            prompt_style = new_prompt
            url = None  # No URL downloads in redescribe mode
            
            print("Running workflow steps...")
            print(f"  Steps: {', '.join(steps)}")
            print()
            
        except ValueError as e:
            print(f"ERROR: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"ERROR: Unexpected error during redescribe setup: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        
    else:
        # Normal mode - determine input source and mode
        url = None
        input_dir = None
        
        # Check for URL input (either as input_source or --download flag)
        if args.download:
            url = args.download
            input_dir = Path.cwd()  # Use current directory as base for URL downloads
        elif args.input_source and (args.input_source.startswith('http://') or 
                                  args.input_source.startswith('https://') or 
                                  '.' in args.input_source and not Path(args.input_source).exists()):
            # Input looks like a URL - treat as web download
            url = args.input_source
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url  # Add https:// if not specified
            input_dir = Path.cwd()
        elif args.input_source:
            # Input is a directory path
            input_dir = Path(args.input_source)
        else:
            print("Error: Please provide either:")
            print("  - A directory path: python workflow.py /path/to/images")
            print("  - A website URL: python workflow.py example.com")
            print("  - Or use --download: python workflow.py --download https://example.com")
            sys.exit(1)
        
        # Handle original working directory if called from wrapper
        original_cwd = args.original_cwd if args.original_cwd else os.getcwd()
        
        # Validate input directory if it's a local path
        if not url and input_dir:
            if not input_dir.is_absolute():
                input_dir = (Path(original_cwd) / input_dir).resolve()
                
            if not input_dir.exists():
                print(f"ERROR: Input directory does not exist: {input_dir}")
                sys.exit(1)
        
        # Auto-detect appropriate workflow steps based on input type
        if url:
            # For web download: download,describe,html
            if not args.steps or args.steps == "video,convert,describe,html":
                steps = ["download", "describe", "html"]
                print(f"🌐 Web download mode detected - using steps: {','.join(steps)}")
            else:
                steps = args.steps.split(',')
        else:
            # For local files: keep default or user-specified steps
            steps = args.steps.split(',') if args.steps else ["video", "convert", "describe", "html"]
        
        # Set output directory (resolve relative to original working directory)
        # Create timestamped workflow output directory with provider, model, and prompt info
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Get provider, model and prompt info for directory naming
        provider_name = args.provider if args.provider else "ollama"
        model_name = get_effective_model(args, args.config_workflow)
        prompt_style = get_effective_prompt_style(args, args.config_workflow)
        
        # Determine workflow name identifier
        if args.name:
            # User provided a custom name - preserve case for display and directory
            workflow_name_display = sanitize_name(args.name, preserve_case=True)
            workflow_name = workflow_name_display  # Use same case-preserved name
        elif url:
            # Auto-generate from URL domain
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            domain = parsed_url.netloc or parsed_url.path
            workflow_name_display = sanitize_name(domain.replace('www.', ''), preserve_case=True)
            workflow_name = workflow_name_display
        else:
            # Auto-generate from input directory path (2 components)
            workflow_name_display = get_path_identifier_2_components(str(input_dir))
            workflow_name = workflow_name_display  # Already lowercase from auto-generation
        
        # Create descriptive directory name (wf = workflow)
        # Format: wf_NAME_PROVIDER_MODEL_PROMPT_TIMESTAMP
        wf_dirname = f"wf_{workflow_name}_{provider_name}_{model_name}_{prompt_style}_{timestamp}"
        
        if args.output_dir:
            # User specified output directory - create wf_ directory inside it
            base_dir = Path(args.output_dir)
            if not base_dir.is_absolute():
                base_dir = (Path(original_cwd) / base_dir).resolve()
            output_dir = (base_dir / wf_dirname).resolve()
        else:
            # No output directory specified - use default from config (usually "Descriptions/")
            default_base = Path(original_cwd) / "Descriptions"
            output_dir = (default_base / wf_dirname).resolve()
        
        # Parse workflow steps (steps was already processed in auto-detection above)
        if isinstance(steps, list):
            # Already processed as list from auto-detection
            pass  
        else:
            # Convert string to list
            steps = [step.strip() for step in steps.split(",")]
    
    # Validate steps
    valid_steps = ["download", "video", "convert", "describe", "html"]
    invalid_steps = [step for step in steps if step not in valid_steps]
    if invalid_steps:
        # Can't use logger yet since orchestrator isn't created
        print(f"Error: Invalid workflow steps: {', '.join(invalid_steps)}")
        print(f"Valid steps: {', '.join(valid_steps)}")
        sys.exit(1)
    
    # Normalize model name - strip provider prefix if present
    # (e.g., "ollama:llama3.2-vision:11b" -> "llama3.2-vision:11b")
    normalized_model = normalize_model_name(args.model, args.provider) if args.model else None
    
    # Determine which config files to use
    workflow_config = args.config_workflow if args.config_workflow else "workflow_config.json"
    image_describer_config = args.config_image_describer  # Can be None (will use defaults)
    video_config = args.config_video  # Can be None (will use defaults)
    
    # Create orchestrator first to get access to logging
    try:
        orchestrator = WorkflowOrchestrator(
            workflow_config,  # Explicit workflow config 
            base_output_dir=output_dir, 
            model=normalized_model, 
            prompt_style=args.prompt_style, 
            provider=args.provider, 
            api_key_file=args.api_key_file,
            preserve_descriptions=args.preserve_descriptions,
            workflow_name=workflow_name,
            timeout=args.timeout,
            enable_metadata=not args.no_metadata,  # Default True unless --no-metadata specified
            enable_geocoding=not args.no_geocode,  # Default True unless --no-geocode specified
            geocode_cache=args.geocode_cache,
            url=url,  # Use detected URL from argument processing
            min_size=args.min_size,
            max_images=args.max_images,
            progress_status=args.progress_status,
            image_describer_config=image_describer_config,  # NEW: explicit image describer config
            video_config=video_config  # NEW: explicit video config
        )
        
        if args.dry_run:
            orchestrator.logger.info("Dry run mode - showing what would be executed:")
            orchestrator.logger.info(f"Input directory: {input_dir}")
            orchestrator.logger.info(f"Output directory: {output_dir}")
            orchestrator.logger.info(f"Workflow steps: {', '.join(steps)}")
            orchestrator.logger.info(f"Workflow config: {workflow_config}")
            if image_describer_config:
                orchestrator.logger.info(f"Image describer config: {image_describer_config}")
            if video_config:
                orchestrator.logger.info(f"Video config: {video_config}")
            # Also print to console for immediate feedback
            print("Dry run mode - showing what would be executed:")
            print(f"Input directory: {input_dir}")
            print(f"Output directory: {output_dir}")
            print(f"Workflow steps: {', '.join(steps)}")
            print(f"Workflow config: {workflow_config}")
            if image_describer_config:
                print(f"Image describer config: {image_describer_config}")
            if video_config:
                print(f"Video config: {video_config}")
            sys.exit(0)
        
        # Override configuration if specified
        # Only update workflow config if it has the workflow structure
        if normalized_model and "workflow" in orchestrator.config.config:
            orchestrator.config.config["workflow"]["steps"]["image_description"]["model"] = normalized_model
        
        if args.prompt_style and "workflow" in orchestrator.config.config:
            orchestrator.config.config["workflow"]["steps"]["image_description"]["prompt_style"] = args.prompt_style
        
        # Set logging level
        if args.verbose:
            orchestrator.logger.logger.setLevel(logging.DEBUG)
        elif args.progress_status:
            orchestrator.logger.logger.setLevel(logging.INFO)
            # Also set console handler to INFO level to show progress messages
            for handler in orchestrator.logger.logger.handlers:
                if hasattr(handler, 'stream') and handler.stream.name == '<stdout>':
                    handler.setLevel(logging.INFO)
        
        # Prepare workflow metadata
        metadata = {
            "workflow_name": workflow_name_display,  # Use case-preserved name for display
            "input_directory": str(input_dir),
            "provider": provider_name,
            "model": model_name,
            "prompt_style": prompt_style,
            "timestamp": timestamp,
            "steps": steps,
            "user_provided_name": bool(args.name),
            # Save custom config paths for resume (only if non-default)
            "config_workflow": args.config_workflow if args.config_workflow != "workflow_config.json" else None,
            "config_image_describer": args.config_image_describer,
            "config_video": args.config_video
        }
        
        # Launch viewer if requested (before workflow starts for real-time monitoring)
        if args.view_results:
            orchestrator.logger.info(f"Launching viewer for real-time monitoring: {output_dir}")
            launch_viewer(output_dir, orchestrator.logger)
        
        # Run workflow
        results = orchestrator.run_workflow(input_dir, output_dir, steps, workflow_metadata=metadata)
        
        # Log original command for resume functionality
        if not args.resume:  # Only log original command for new workflows
            # For redescribe, log the --redescribe argument; for normal workflows, log input_dir
            if args.redescribe:
                original_cmd = ["python", "workflow.py", "--redescribe", str(args.redescribe)]
            else:
                original_cmd = ["python", "workflow.py", str(input_dir)]
            
            if args.output_dir:
                original_cmd.extend(["--output-dir", args.output_dir])
            if args.steps != "video,convert,describe,html":
                original_cmd.extend(["--steps", args.steps])
            if args.provider and args.provider != "ollama":
                original_cmd.extend(["--provider", args.provider])
            if args.model:
                original_cmd.extend(["--model", args.model])
            if args.prompt_style:
                original_cmd.extend(["--prompt-style", args.prompt_style])
            # Log config arguments (use new explicit names)
            if args.config_image_describer and args.config_image_describer != "image_describer_config.json":
                original_cmd.extend(["--config-image-describer", args.config_image_describer])
            if args.config_workflow and args.config_workflow != "workflow_config.json":
                original_cmd.extend(["--config-workflow", args.config_workflow])
            if args.config_video and args.config_video != "video_frame_extractor_config.json":
                original_cmd.extend(["--config-video", args.config_video])
            if args.verbose:
                original_cmd.append("--verbose")
            if args.progress_status:
                original_cmd.append("--progress-status")
            
            orchestrator.logger.info(f"Original command: {' '.join(original_cmd)}")
        else:
            orchestrator.logger.info(f"Resuming workflow from: {resume_dir}")
            orchestrator.logger.info(f"Original input directory: {input_dir}")
            orchestrator.logger.info(f"Completed steps before resume: {', '.join(workflow_state['completed_steps'])}")
        
        # Log and print summary
        orchestrator.logger.info("\n" + "="*60)
        orchestrator.logger.info("WORKFLOW SUMMARY")
        orchestrator.logger.info("="*60)
        orchestrator.logger.info(f"Input directory: {results['input_dir']}")
        orchestrator.logger.info(f"Output directory: {results['output_dir']}")
        orchestrator.logger.info(f"Overall success: {'✅ YES' if results['success'] else '❌ NO'}")
        orchestrator.logger.info(f"Steps completed: {', '.join(results['steps_completed']) if results['steps_completed'] else 'None'}")
        
        if results['steps_failed']:
            orchestrator.logger.warning(f"Steps failed: {', '.join(results['steps_failed'])}")
        
        orchestrator.logger.info(f"\nDetailed results saved in workflow log file.")
        
        # Also print to console for immediate user feedback
        print("\n" + "="*60)
        print("WORKFLOW SUMMARY")
        print("="*60)
        print(f"Input directory: {results['input_dir']}")
        print(f"Output directory: {results['output_dir']}")
        print(f"Overall success: {'✅ YES' if results['success'] else '❌ NO'}")
        print(f"Steps completed: {', '.join(results['steps_completed']) if results['steps_completed'] else 'None'}")
        
        if results['steps_failed']:
            print(f"Steps failed: {', '.join(results['steps_failed'])}")
        
        print(f"\nDetailed results saved in workflow log file.")
        
        # Offer to view results if workflow was successful and viewer wasn't already launched
        # Skip prompt if --batch mode is enabled (for sequential workflow runs)
        if results['success'] and results['output_dir'] and not args.view_results and not args.batch:
            view_results = prompt_view_results()
            if view_results:
                launch_viewer(results['output_dir'], orchestrator.logger)
        elif args.view_results:
            print(f"\nViewer is already running for this workflow.")
        
        # Exit with appropriate code
        sys.exit(0 if results['success'] else 1)
        
    except KeyboardInterrupt:
        print("\nWorkflow interrupted by user")
        sys.exit(130)
    except Exception as e:
        import traceback
        print(f"Error: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
