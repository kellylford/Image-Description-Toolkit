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
    python workflow.py input_directory [options]
    
Examples:
    python workflow.py media_folder
    python workflow.py media_folder --output-dir results --steps video,convert,describe,html
    python workflow.py photos --steps describe,html --model llava:7b
"""

import sys
import os
import argparse
import subprocess
import shutil

# Set UTF-8 encoding for console output on Windows
if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())
import logging
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Import our workflow utilities
from workflow_utils import WorkflowConfig, WorkflowLogger, FileDiscovery, create_workflow_paths
from image_describer import get_default_prompt_style
import re

# Import ollama for model validation
try:
    import ollama
except ImportError:
    ollama = None


def sanitize_name(name: str) -> str:
    """Convert model/prompt names to filesystem-safe strings"""
    if not name:
        return "unknown"
    # Remove special characters, replace with underscores
    safe_name = re.sub(r'[^\w\-_.]', '_', str(name))
    # Remove multiple consecutive underscores
    safe_name = re.sub(r'_+', '_', safe_name)
    # Remove leading/trailing underscores
    return safe_name.strip('_').lower()


def get_effective_model(args, config_file: str = "workflow_config.json") -> str:
    """Determine which model will actually be used"""
    # Command line argument takes precedence
    if hasattr(args, 'model') and args.model:
        return sanitize_name(args.model)
    
    # Check workflow config file
    try:
        config = WorkflowConfig(config_file)
        workflow_model = config.config.get("workflow", {}).get("steps", {}).get("image_description", {}).get("model")
        if workflow_model:
            return sanitize_name(workflow_model)
    except Exception:
        pass
    
    # Fall back to image_describer_config.json default
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
                    return sanitize_name(img_config.get("model_settings", {}).get("model", "unknown"))
            except FileNotFoundError:
                continue
                
    except Exception:
        pass
        
    return "unknown"


def get_effective_prompt_style(args, config_file: str = "workflow_config.json") -> str:
    """Determine which prompt style will actually be used"""
    # Command line argument takes precedence
    if hasattr(args, 'prompt_style') and args.prompt_style:
        return sanitize_name(args.prompt_style)
    
    # Check workflow config file
    try:
        config = WorkflowConfig(config_file)
        workflow_prompt = config.config.get("workflow", {}).get("steps", {}).get("image_description", {}).get("prompt_style")
        if workflow_prompt:
            return sanitize_name(workflow_prompt)
    except Exception:
        pass
    
    # Fall back to image_describer_config.json default
    try:
        # Try different possible paths for the config file
        config_paths = [
            "image_describer_config.json",
            "scripts/image_describer_config.json"
        ]
        
        for config_path in config_paths:
            try:
                default_style = get_default_prompt_style(config_path)
                return sanitize_name(default_style)
            except (FileNotFoundError, ImportError):
                continue
                
    except Exception:
        pass
        
    return "detailed"


def validate_model_availability(model_name: str) -> tuple[bool, list[str]]:
    """
    Validate that the specified model is available in Ollama
    
    Args:
        model_name: Name of the model to validate
        
    Returns:
        Tuple of (is_valid, available_models)
    """
    if not ollama:
        # If ollama module is not available, we can't validate but shouldn't block
        return True, []
    
    try:
        # Check if Ollama is running
        models_response = ollama.list()
        
        # Handle both old and new ollama response formats
        if hasattr(models_response, 'models'):
            # New format: models_response.models is a list of Model objects
            available_models = [model.model for model in models_response.models]
        else:
            # Old format: models_response is a dict with 'models' key
            available_models = [model['name'] for model in models_response.get('models', [])]
        
        # Check if the specified model is available
        is_valid = model_name in available_models
        return is_valid, available_models
        
    except Exception as e:
        # If we can't connect to Ollama, we can't validate but shouldn't block
        # The actual image_describer.py will handle this error appropriately
        return True, []


def handle_resume_workflow(args):
    """Handle workflow resume functionality"""
    resume_dir = Path(args.resume)
    
    if not resume_dir.exists():
        print(f"Error: Resume directory does not exist: {resume_dir}")
        sys.exit(1)
    
    if not resume_dir.is_dir():
        print(f"Error: Resume path is not a directory: {resume_dir}")
        sys.exit(1)
    
    # Validate workflow directory structure
    descriptions_file = resume_dir / "descriptions" / "image_descriptions.txt"
    logs_dir = resume_dir / "logs"
    
    if not logs_dir.exists():
        print(f"Error: Invalid workflow directory - missing logs: {logs_dir}")
        sys.exit(1)
    
    print(f"Resuming workflow from: {resume_dir}")
    
    try:
        # Find the original workflow log to extract parameters
        workflow_logs = list(logs_dir.glob("workflow_*.log"))
        if not workflow_logs:
            print("Error: Could not find original workflow log file")
            sys.exit(1)
        
        # Parse original workflow parameters
        original_params = parse_workflow_log(workflow_logs[0])
        
        if not original_params:
            print("Error: Could not extract original workflow parameters")
            sys.exit(1)
        
        print(f"Original input directory: {original_params.get('input_dir')}")
        print(f"Original steps: {original_params.get('steps', [])}")
        print(f"Original model: {original_params.get('model', 'default')}")
        print(f"Original prompt style: {original_params.get('prompt_style', 'default')}")
        
        # Determine which steps need to be resumed
        remaining_steps = analyze_workflow_completion(resume_dir, original_params)
        
        if not remaining_steps:
            print("✅ Workflow appears to be complete - nothing to resume")
            print("If you believe this is incorrect, you can:")
            print("  1. Delete the descriptions file to force re-description")
            print("  2. Check the log files for any errors")
            print("  3. Run the workflow from scratch with a new output directory")
            return 0
        
        print(f"📋 Steps to resume: {', '.join(remaining_steps)}")
        
        # Provide more detailed feedback about what will be done
        for step in remaining_steps:
            if step == 'describe':
                desc_file = resume_dir / "descriptions" / "image_descriptions.txt"
                if desc_file.exists():
                    print(f"   → Description step: Will continue from existing {desc_file}")
                else:
                    print(f"   → Description step: Will create new descriptions file")
            elif step == 'html':
                print(f"   → HTML step: Will generate reports from descriptions")
            elif step == 'video':
                print(f"   → Video step: Will extract frames from videos")
            elif step == 'convert':
                print(f"   → Convert step: Will convert HEIC images to JPG")
        
        # Create orchestrator with resume directory as output
        orchestrator = WorkflowOrchestrator(args.config, base_output_dir=resume_dir)
        
        # Override configuration with original parameters
        if original_params.get('model'):
            orchestrator.config.config["workflow"]["steps"]["image_description"]["model"] = original_params['model']
        if original_params.get('prompt_style'):
            orchestrator.config.config["workflow"]["steps"]["image_description"]["prompt_style"] = original_params['prompt_style']
        
        # Set logging level
        if args.verbose:
            orchestrator.logger.logger.setLevel(logging.DEBUG)
        
        # Resume workflow
        input_dir = Path(original_params['input_dir'])
        if not input_dir.exists():
            print(f"Warning: Original input directory no longer exists: {input_dir}")
            input_dir_input = input("Enter new input directory path (or press Enter to abort): ").strip()
            if not input_dir_input:
                print("Resume aborted")
                sys.exit(1)
            input_dir = Path(input_dir_input)
            if not input_dir.exists():
                print(f"Error: New input directory does not exist: {input_dir}")
                sys.exit(1)
        
        orchestrator.logger.info(f"Resuming workflow with steps: {', '.join(remaining_steps)}")
        print(f"Resuming workflow with steps: {', '.join(remaining_steps)}")
        
        results = orchestrator.run_workflow(input_dir, resume_dir, remaining_steps)
        
        # Log and print summary
        orchestrator.logger.info("\n" + "="*60)
        orchestrator.logger.info("RESUME WORKFLOW SUMMARY")
        orchestrator.logger.info("="*60)
        orchestrator.logger.info(f"Input directory: {results['input_dir']}")
        orchestrator.logger.info(f"Output directory: {results['output_dir']}")
        orchestrator.logger.info(f"Overall success: {'✅ YES' if results['success'] else '❌ NO'}")
        orchestrator.logger.info(f"Steps completed: {', '.join(results['steps_completed']) if results['steps_completed'] else 'None'}")
        
        if results['steps_failed']:
            orchestrator.logger.warning(f"Steps failed: {', '.join(results['steps_failed'])}")
        
        print("\n" + "="*60)
        print("RESUME WORKFLOW SUMMARY")
        print("="*60)
        print(f"Input directory: {results['input_dir']}")
        print(f"Output directory: {results['output_dir']}")
        print(f"Overall success: {'✅ YES' if results['success'] else '❌ NO'}")
        print(f"Steps completed: {', '.join(results['steps_completed']) if results['steps_completed'] else 'None'}")
        
        if results['steps_failed']:
            print(f"Steps failed: {', '.join(results['steps_failed'])}")
        
        # Exit with appropriate code
        sys.exit(0 if results['success'] else 1)
        
    except KeyboardInterrupt:
        print("\nWorkflow resume interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"Error during resume: {e}")
        sys.exit(1)


def parse_workflow_log(log_file):
    """Parse workflow log file to extract original parameters"""
    params = {}
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract input directory
        input_match = re.search(r'Input directory: (.+)', content)
        if input_match:
            params['input_dir'] = input_match.group(1).strip()
        
        # Extract steps
        steps_match = re.search(r'Starting workflow with steps: (.+)', content)
        if steps_match:
            params['steps'] = [step.strip() for step in steps_match.group(1).split(',')]
        
        # Extract model (look in image_describer log if available)
        model_match = re.search(r'Model: (.+)', content)
        if model_match:
            params['model'] = model_match.group(1).strip()
        
        # Extract prompt style
        prompt_match = re.search(r'Prompt Style: (.+)', content)
        if prompt_match:
            params['prompt_style'] = prompt_match.group(1).strip()
            
    except Exception as e:
        print(f"Warning: Error parsing workflow log: {e}")
        
    return params


def check_descriptions_completeness(workflow_dir, descriptions_file):
    """
    Check if the descriptions file contains entries for all available images
    
    Args:
        workflow_dir: Path to workflow directory
        descriptions_file: Path to descriptions file
        
    Returns:
        bool: True if descriptions are incomplete and need to be regenerated
    """
    try:
        # Ensure we're working with Path objects
        workflow_dir = Path(workflow_dir)
        descriptions_file = Path(descriptions_file)
        
        # Count existing descriptions
        with open(descriptions_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Count "File: " entries in the descriptions file
        existing_descriptions = content.count('\nFile: ')
        # Add 1 if the file starts with "File: " (first entry won't have preceding newline)
        if content.startswith('File: '):
            existing_descriptions += 1
        
        # Count total images available for description across all relevant directories
        # Use a set to avoid counting duplicates and track unique images
        unique_images = set()
        supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
        
        # Check original input directory (from workflow log)
        workflow_logs = list((workflow_dir / "logs").glob("workflow_*.log"))
        original_input_dir = None
        
        if workflow_logs:
            try:
                with open(workflow_logs[0], 'r', encoding='utf-8') as f:
                    log_content = f.read()
                    import re
                    input_match = re.search(r'Input directory: (.+)', log_content)
                    if input_match:
                        original_input_dir = Path(input_match.group(1).strip())
            except Exception:
                pass
        
        # Priority order: converted_images > extracted_frames > original input
        # This matches the workflow's processing logic
        
        # First, add images from converted_images directory (highest priority)
        converted_dir = workflow_dir / "converted_images"
        if converted_dir.exists():
            for file_path in converted_dir.rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in supported_formats:
                    # Use relative path from converted_dir as unique identifier
                    relative_path = file_path.relative_to(converted_dir)
                    unique_images.add(('converted', str(relative_path)))
        
        # Then, add images from extracted_frames directory
        frames_dir = workflow_dir / "extracted_frames"
        if frames_dir.exists():
            for file_path in frames_dir.rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in supported_formats:
                    relative_path = file_path.relative_to(frames_dir)
                    # Only add if we don't already have a converted version
                    frame_id = ('frames', str(relative_path))
                    # Check if this might be a duplicate of a converted image
                    stem_name = file_path.stem.lower()
                    is_duplicate = any(
                        source == 'converted' and stem_name in path.lower() 
                        for source, path in unique_images
                    )
                    if not is_duplicate:
                        unique_images.add(frame_id)
        
        # Finally, add images from original input directory (lowest priority)
        if original_input_dir and original_input_dir.exists():
            for file_path in original_input_dir.rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in supported_formats:
                    try:
                        relative_path = file_path.relative_to(original_input_dir)
                        # Only add if we don't already have processed versions
                        stem_name = file_path.stem.lower()
                        is_duplicate = any(
                            stem_name in path.lower() 
                            for source, path in unique_images
                        )
                        if not is_duplicate:
                            unique_images.add(('original', str(relative_path)))
                    except ValueError:
                        # Handle case where file_path is not relative to original_input_dir
                        continue
        
        total_images = len(unique_images)
        
        print(f"Descriptions check: Found {existing_descriptions} descriptions for {total_images} images")
        
        # If we have significantly fewer descriptions than images, we need to continue
        # Use a threshold to account for potential edge cases
        completion_threshold = 0.95  # 95% completion
        if total_images > 0 and (existing_descriptions / total_images) < completion_threshold:
            print(f"Descriptions incomplete: {existing_descriptions}/{total_images} = {existing_descriptions/total_images:.1%}")
            return True
        
        if total_images == 0:
            print("Warning: No images found to describe")
            return False
        
        print(f"Descriptions appear complete: {existing_descriptions}/{total_images}")
        return False
        
    except Exception as e:
        print(f"Warning: Could not check description completeness: {e}")
        # If we can't check, assume incomplete to be safe
        return True


def analyze_workflow_completion(workflow_dir, original_params):
    """Analyze workflow directory to determine which steps still need to be completed"""
    remaining_steps = []
    original_steps = original_params.get('steps', ['video', 'convert', 'describe', 'html'])
    
    # Check each step completion
    for step in original_steps:
        if step == 'video':
            # Check if video extraction is complete
            extracted_frames_dir = workflow_dir / "extracted_frames"
            if not extracted_frames_dir.exists() or not any(extracted_frames_dir.glob('*')):
                remaining_steps.append('video')
        
        elif step == 'convert':
            # Check if image conversion is complete
            converted_images_dir = workflow_dir / "converted_images"
            if not converted_images_dir.exists() or not any(converted_images_dir.glob('*')):
                remaining_steps.append('convert')
        
        elif step == 'describe':
            # Check if descriptions are complete
            descriptions_file = workflow_dir / "descriptions" / "image_descriptions.txt"
            if not descriptions_file.exists():
                remaining_steps.append('describe')
            else:
                # Check if descriptions are actually complete by comparing with available images
                needs_describe = check_descriptions_completeness(workflow_dir, descriptions_file)
                if needs_describe:
                    remaining_steps.append('describe')
        
        elif step == 'html':
            # Check if HTML reports are complete
            html_dir = workflow_dir / "html_reports"
            if not html_dir.exists() or not any(html_dir.glob('*.html')):
                remaining_steps.append('html')
    
    return remaining_steps


class WorkflowOrchestrator:
    """Main workflow orchestrator class"""
    
    def __init__(self, config_file: str = "workflow_config.json", base_output_dir: Optional[Path] = None):
        """
        Initialize the workflow orchestrator
        
        Args:
            config_file: Path to workflow configuration file
            base_output_dir: Base output directory for the workflow
        """
        self.config = WorkflowConfig(config_file)
        if base_output_dir:
            self.config.set_base_output_dir(base_output_dir)
        self.logger = WorkflowLogger("workflow_orchestrator", base_output_dir=self.config.base_output_dir)
        self.discovery = FileDiscovery(self.config)
        
        # Available workflow steps
        self.available_steps = {
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
            'total_conversions': 0,
            'total_descriptions': 0,
            'errors_encountered': 0,
            'steps_completed': [],
            'steps_failed': []
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
            return {"success": True, "processed": 0, "output_dir": output_dir}
        
        self.logger.info(f"Found {len(video_files)} video files")
        
        # Update frame extractor config to use our output directory
        step_config = self.config.get_step_config("video_extraction")
        config_file = step_config.get("config_file", "video_frame_extractor_config.json")
        
        # Temporarily modify the frame extractor config
        self._update_frame_extractor_config(config_file, output_dir)
        
        try:
            # Run video frame extractor
            cmd = [
                sys.executable, "video_frame_extractor.py",
                str(input_dir),
                "--config", config_file,
                "--log-dir", str(self.config.base_output_dir)
            ]
            
            self.logger.info(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            
            # Log the subprocess output for transparency
            if result.stdout.strip():
                self.logger.info(f"video_frame_extractor.py output:\n{result.stdout}")
            if result.stderr.strip():
                self.logger.warning(f"video_frame_extractor.py stderr:\n{result.stderr}")
            
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
                self.logger.error(f"Video frame extraction failed: {result.stderr}")
                return {"success": False, "error": result.stderr}
                
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
            return {"success": True, "processed": 0, "output_dir": output_dir}
        
        self.logger.info(f"Found {len(heic_files)} HEIC files")
        
        try:
            # Get conversion settings
            step_config = self.config.get_step_config("image_conversion")
            
            # Run image converter
            cmd = [
                sys.executable, "ConvertImage.py",
                str(input_dir),
                "--output", str(output_dir),
                "--recursive",
                "--quality", str(step_config.get("quality", 95)),
                "--log-dir", str(self.config.base_output_dir / "logs")
            ]
            
            if not step_config.get("keep_metadata", True):
                cmd.append("--no-metadata")
            
            self.logger.info(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            
            # Log the subprocess output for transparency
            if result.stdout.strip():
                self.logger.info(f"ConvertImage.py output:\n{result.stdout}")
            if result.stderr.strip():
                self.logger.warning(f"ConvertImage.py stderr:\n{result.stderr}")
            
            if result.returncode == 0:
                self.logger.info("Image conversion completed successfully")
                
                # Count converted images
                converted_images = self.discovery.find_files_by_type(output_dir, "images")
                
                return {
                    "success": True,
                    "processed": len(heic_files),
                    "output_dir": output_dir,
                    "converted_images": len(converted_images)
                }
            else:
                self.logger.error(f"Image conversion failed: {result.stderr}")
                return {"success": False, "error": result.stderr}
                
        except Exception as e:
            self.logger.error(f"Error during image conversion: {e}")
            return {"success": False, "error": str(e)}
    
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
        
        # Build list of directories to search for images
        search_dirs = [input_dir]
        
        # Add converted images directory if it exists and has content
        converted_dir = self.config.get_step_output_dir("image_conversion")
        if converted_dir.exists() and any(converted_dir.iterdir()):
            search_dirs.append(converted_dir)
            self.logger.info(f"Including converted images from: {converted_dir}")
        
        # Add extracted frames directory if it exists and has content
        frames_dir = self.config.get_step_output_dir("video_extraction")
        if frames_dir.exists() and any(frames_dir.iterdir()):
            search_dirs.append(frames_dir)
            self.logger.info(f"Including extracted frames from: {frames_dir}")
        
        # Find image files in all search directories
        all_image_files = []
        for search_dir in search_dirs:
            image_files = self.discovery.find_files_by_type(search_dir, "images")
            all_image_files.extend(image_files)
        
        if not all_image_files:
            self.logger.info("No image files found to describe")
            return {"success": True, "processed": 0, "output_dir": output_dir}
        
        self.logger.info(f"Found {len(all_image_files)} image files across {len(search_dirs)} directories")
        
        try:
            # Get description settings
            step_config = self.config.get_step_config("image_description")
            
            # Create a temporary directory to combine all images from all directories
            # This ensures image_describer.py only runs once and doesn't overwrite descriptions
            temp_combined_dir = self.config.base_output_dir / "temp_combined_images"
            temp_combined_dir.mkdir(parents=True, exist_ok=True)
            
            # Preserve full directory structure in temp dir to prevent collisions
            combined_image_list = []
            total_files_found = 0
            total_copy_failures = 0
            
            for search_dir in search_dirs:
                dir_image_files = self.discovery.find_files_by_type(search_dir, "images")
                if not dir_image_files:
                    continue
                    
                total_files_found += len(dir_image_files)
                self.logger.info(f"Found {len(dir_image_files)} images from: {search_dir}")
                
                # Create a safe name for the source directory to use as root in temp structure
                safe_source_name = search_dir.name.replace(" ", "_").replace(":", "")
                
                # Copy images while preserving their original directory structure
                files_copied_from_dir = 0
                files_failed_from_dir = 0
                
                for image_file in dir_image_files:
                    try:
                        # Calculate relative path from search_dir to image_file
                        relative_path = image_file.relative_to(search_dir)
                        
                        # Create temp path preserving directory structure under source name
                        temp_image_path = temp_combined_dir / safe_source_name / relative_path
                        
                        # Ensure parent directories exist
                        temp_image_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        # Copy file to temp location preserving structure
                        shutil.copy2(image_file, temp_image_path)
                        combined_image_list.append((temp_image_path, image_file))  # (temp_path, original_path)
                        files_copied_from_dir += 1
                        self.logger.debug(f"Copied {image_file} to {temp_image_path}")
                        
                    except ValueError as e:
                        # Handle case where image_file is not relative to search_dir
                        self.logger.warning(f"Could not determine relative path for {image_file}: {e}")
                        # Fallback to original flattened approach for this file
                        safe_filename = f"{safe_source_name}_{image_file.name}"
                        temp_image_path = temp_combined_dir / safe_source_name / safe_filename
                        temp_image_path.parent.mkdir(parents=True, exist_ok=True)
                        try:
                            shutil.copy2(image_file, temp_image_path)
                            combined_image_list.append((temp_image_path, image_file))
                            files_copied_from_dir += 1
                            self.logger.debug(f"Copied {image_file} to {temp_image_path} (fallback)")
                        except Exception as e2:
                            self.logger.warning(f"Failed to copy {image_file} (fallback): {e2}")
                            files_failed_from_dir += 1
                            total_copy_failures += 1
                            continue
                    except Exception as e:
                        self.logger.warning(f"Failed to copy {image_file}: {e}")
                        files_failed_from_dir += 1
                        total_copy_failures += 1
                        continue
                
                self.logger.info(f"Successfully copied {files_copied_from_dir}/{len(dir_image_files)} images from {search_dir}")
                if files_failed_from_dir > 0:
                    self.logger.warning(f"Failed to copy {files_failed_from_dir} images from {search_dir}")
            
            # Log comprehensive copy summary
            self.logger.info(f"Copy Summary: Found {total_files_found} images total")
            self.logger.info(f"Copy Summary: Successfully copied {len(combined_image_list)} images")
            if total_copy_failures > 0:
                self.logger.warning(f"Copy Summary: Failed to copy {total_copy_failures} images")
                self.logger.warning(f"Copy Summary: Success rate: {(len(combined_image_list) / total_files_found * 100):.1f}%")
            
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
            
            # Build command for the combined directory - single call to image_describer.py
            cmd = [
                sys.executable, "image_describer.py",
                str(temp_combined_dir),
                "--recursive",
                "--output-dir", str(output_dir),
                "--log-dir", str(self.config.base_output_dir / "logs")
            ]
            
            # Add optional parameters
            if "config_file" in step_config:
                cmd.extend(["--config", step_config["config_file"]])
            
            if "model" in step_config and step_config["model"]:
                cmd.extend(["--model", step_config["model"]])
            
            # Handle prompt style - use config file default if not explicitly set
            if "prompt_style" in step_config and step_config["prompt_style"]:
                cmd.extend(["--prompt-style", step_config["prompt_style"]])
            else:
                # Get default prompt style from image describer config
                config_file = step_config.get("config_file", "image_describer_config.json")
                default_style = get_default_prompt_style(config_file)
                if default_style != "detailed":  # Only add if different from hardcoded default
                    cmd.extend(["--prompt-style", default_style])
            
            # Single call to image_describer.py with all images
            self.logger.info(f"Running single image description process: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            
            # Log the subprocess output for transparency
            if result.stdout.strip():
                self.logger.info(f"image_describer.py output:\n{result.stdout}")
            if result.stderr.strip():
                self.logger.warning(f"image_describer.py stderr:\n{result.stderr}")
            
            # Clean up temporary directory
            try:
                shutil.rmtree(temp_combined_dir)
                self.logger.debug(f"Cleaned up temporary directory: {temp_combined_dir}")
            except Exception as e:
                self.logger.warning(f"Failed to clean up temporary directory {temp_combined_dir}: {e}")
            
            if result.returncode == 0:
                self.logger.info("Image description completed successfully")
                total_processed = len(combined_image_list)
            else:
                self.logger.error(f"Image description failed: {result.stderr}")
                return {"success": False, "error": f"Image description process failed: {result.stderr}"}
            
            # Check if description file was created
            target_desc_file = output_dir / "image_descriptions.txt"
            
            if target_desc_file.exists():
                self.logger.info(f"Descriptions saved to: {target_desc_file}")
                
                return {
                    "success": True,
                    "processed": total_processed,
                    "output_dir": output_dir,
                    "description_file": target_desc_file
                }
            else:
                self.logger.warning("Description file was not created")
                return {"success": False, "error": "Description file not created"}
                
        except Exception as e:
            self.logger.error(f"Error during image description: {e}")
            return {"success": False, "error": str(e)}
    
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
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            
            # Log the subprocess output for transparency
            if result.stdout.strip():
                self.logger.info(f"descriptions_to_html.py output:\n{result.stdout}")
            if result.stderr.strip():
                self.logger.warning(f"descriptions_to_html.py stderr:\n{result.stderr}")
            
            if result.returncode == 0:
                self.logger.info("HTML generation completed successfully")
                
                return {
                    "success": True,
                    "processed": 1,
                    "output_dir": output_dir,
                    "html_file": html_file
                }
            else:
                self.logger.error(f"HTML generation failed: {result.stderr}")
                return {"success": False, "error": result.stderr}
                
        except Exception as e:
            self.logger.error(f"Error during HTML generation: {e}")
            return {"success": False, "error": str(e)}
    
    def run_workflow(self, input_dir: Path, output_dir: Path, steps: List[str]) -> Dict[str, Any]:
        """
        Run the complete workflow
        
        Args:
            input_dir: Input directory containing media files
            output_dir: Base output directory
            steps: List of workflow steps to execute
            
        Returns:
            Dictionary with overall workflow results
        """
        self.logger.info(f"Starting workflow with steps: {', '.join(steps)}")
        self.logger.info(f"Input directory: {input_dir}")
        self.logger.info(f"Output directory: {output_dir}")
        
        # Initialize workflow statistics
        start_time = datetime.now()
        self.statistics['start_time'] = start_time.isoformat()
        
        # Set base output directory in config
        self.config.set_base_output_dir(output_dir)
        
        # Create workflow directory structure
        workflow_paths = create_workflow_paths(output_dir)
        
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
                {"video": "video_extraction", "convert": "image_conversion", 
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
                    # Description step should look at multiple potential image sources
                    step_result = step_method(input_dir, step_output_dir)
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
                    
                    # Update input directory for next step if this step produced outputs
                    if step in ["video", "convert"] and step_result.get("output_dir"):
                        current_input_dir = step_result["output_dir"]
                else:
                    self.statistics['steps_failed'].append(step)
                    workflow_results["steps_failed"].append(step)
                    workflow_results["success"] = False
                    self.logger.error(f"Step '{step}' failed: {step_result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                self.statistics['errors_encountered'] += 1
                self.statistics['steps_failed'].append(step)
                self.logger.error(f"Error executing step '{step}': {e}")
                workflow_results["steps_failed"].append(step)
                workflow_results["success"] = False
                self.step_results[step] = {"success": False, "error": str(e)}
        
        # Finalize statistics and logging
        end_time = datetime.now()
        self.statistics['end_time'] = end_time.isoformat()
        workflow_results["end_time"] = end_time.isoformat()
        workflow_results["step_results"] = self.step_results
        
        # Log comprehensive final statistics
        self._log_final_statistics(start_time, end_time)
        
        return workflow_results
    
    def _update_statistics(self, step: str, step_result: Dict[str, Any]) -> None:
        """Update workflow statistics based on step results"""
        if step_result.get("success"):
            processed = step_result.get("processed", 0)
            if step == "video":
                self.statistics['total_videos_processed'] += processed
            elif step == "convert":
                self.statistics['total_conversions'] += processed
                self.statistics['total_images_processed'] += processed
            elif step == "describe":
                self.statistics['total_descriptions'] += processed
                self.statistics['total_images_processed'] += processed
            
            self.statistics['total_files_processed'] += processed
    
    def _log_final_statistics(self, start_time: datetime, end_time: datetime) -> None:
        """Log comprehensive final workflow statistics"""
        total_time = (end_time - start_time).total_seconds()
        
        self.logger.info("\n" + "="*60)
        self.logger.info("FINAL WORKFLOW STATISTICS")
        self.logger.info("="*60)
        
        # Time statistics
        self.logger.info(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"Total execution time: {total_time:.2f} seconds ({total_time/60:.1f} minutes)")
        
        # File processing statistics
        self.logger.info(f"Total files processed: {self.statistics['total_files_processed']}")
        self.logger.info(f"Videos processed: {self.statistics['total_videos_processed']}")
        self.logger.info(f"Images processed: {self.statistics['total_images_processed']}")
        self.logger.info(f"HEIC conversions: {self.statistics['total_conversions']}")
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
  python workflow.py media_folder
  python workflow.py media_folder --output-dir results
  python workflow.py photos --steps describe,html
  python workflow.py videos --steps video,describe,html --model llava:7b
  python workflow.py mixed_media --output-dir analysis --config my_workflow.json
        """
    )
    
    parser.add_argument(
        "input_dir",
        nargs='?',  # Make input_dir optional
        help="Input directory containing media files to process"
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
    
    parser.add_argument(
        "--config", "-c",
        default="workflow_config.json",
        help="Workflow configuration file (default: workflow_config.json)"
    )
    
    parser.add_argument(
        "--model",
        help="Override AI model for image description"
    )
    
    parser.add_argument(
        "--prompt-style",
        help="Override prompt style for image description"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without executing"
    )
    
    parser.add_argument(
        "--resume",
        help="Resume processing from a previous workflow directory"
    )
    
    parser.add_argument(
        "--original-cwd",
        help=argparse.SUPPRESS  # Hidden argument for wrapper communication
    )
    
    args = parser.parse_args()
    
    # Validate that either input_dir or resume is provided
    if not args.input_dir and not args.resume:
        parser.error("Either input_dir or --resume must be provided")
    
    if args.input_dir and args.resume:
        parser.error("Cannot specify both input_dir and --resume")
    
    # Handle resume functionality
    if args.resume:
        return handle_resume_workflow(args)
    
    # Handle original working directory if called from wrapper
    original_cwd = args.original_cwd if args.original_cwd else os.getcwd()
    
    # Validate input directory (resolve relative to original working directory)
    input_dir = Path(args.input_dir)
    if not input_dir.is_absolute():
        input_dir = (Path(original_cwd) / input_dir).resolve()
    
    if not input_dir.exists():
        # Can't use logger yet since orchestrator isn't created
        print(f"Error: Input directory does not exist: {input_dir}")
        sys.exit(1)
    
    # Set output directory (resolve relative to original working directory)
    if args.output_dir:
        output_dir = Path(args.output_dir)
        if not output_dir.is_absolute():
            output_dir = (Path(original_cwd) / output_dir).resolve()
    else:
        # Create timestamped workflow output directory with model and prompt info
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Get model and prompt info for directory naming
        model_name = get_effective_model(args, args.config)
        prompt_style = get_effective_prompt_style(args, args.config)
        
        # Create descriptive directory name
        output_dir = (Path(original_cwd) / f"workflow_{model_name}_{prompt_style}_{timestamp}").resolve()
    
    # Parse workflow steps
    steps = [step.strip() for step in args.steps.split(",")]
    
    # Validate steps
    valid_steps = ["video", "convert", "describe", "html"]
    invalid_steps = [step for step in steps if step not in valid_steps]
    if invalid_steps:
        # Can't use logger yet since orchestrator isn't created
        print(f"Error: Invalid workflow steps: {', '.join(invalid_steps)}")
        print(f"Valid steps: {', '.join(valid_steps)}")
        sys.exit(1)
    
    # Create orchestrator first to get access to logging
    try:
        orchestrator = WorkflowOrchestrator(args.config, base_output_dir=output_dir)
        
        if args.dry_run:
            orchestrator.logger.info("Dry run mode - showing what would be executed:")
            orchestrator.logger.info(f"Input directory: {input_dir}")
            orchestrator.logger.info(f"Output directory: {output_dir}")
            orchestrator.logger.info(f"Workflow steps: {', '.join(steps)}")
            orchestrator.logger.info(f"Configuration: {args.config}")
            # Also print to console for immediate feedback
            print("Dry run mode - showing what would be executed:")
            print(f"Input directory: {input_dir}")
            print(f"Output directory: {output_dir}")
            print(f"Workflow steps: {', '.join(steps)}")
            print(f"Configuration: {args.config}")
            sys.exit(0)
        
        # Override configuration if specified
        if args.model:
            orchestrator.config.config["workflow"]["steps"]["image_description"]["model"] = args.model
        
        if args.prompt_style:
            # Validate and correct prompt style case to match image_describer.py expectations
            valid_prompt_styles = {
                "detailed": "detailed",
                "concise": "concise", 
                "narrative": "Narrative",  # Convert lowercase to proper case
                "artistic": "artistic",
                "technical": "technical",
                "colorful": "colorful",
                "social": "Social"  # Convert lowercase to proper case
            }
            
            corrected_style = valid_prompt_styles.get(args.prompt_style.lower(), args.prompt_style)
            orchestrator.config.config["workflow"]["steps"]["image_description"]["prompt_style"] = corrected_style
            
            if corrected_style != args.prompt_style:
                print(f"Note: Corrected prompt style '{args.prompt_style}' to '{corrected_style}' for compatibility")
        
        # Validate model availability if describe step is included
        if "describe" in steps:
            # Determine which model will be used
            if args.model:
                model_to_validate = args.model
            else:
                # Get the model from config
                model_to_validate = orchestrator.config.config.get("workflow", {}).get("steps", {}).get("image_description", {}).get("model")
                if not model_to_validate:
                    # Fall back to image_describer_config.json
                    try:
                        config_paths = [
                            "image_describer_config.json",
                            "scripts/image_describer_config.json"
                        ]
                        for config_path in config_paths:
                            try:
                                with open(config_path, 'r', encoding='utf-8') as f:
                                    img_config = json.load(f)
                                    model_to_validate = img_config.get("model_settings", {}).get("model")
                                    if model_to_validate:
                                        break
                            except FileNotFoundError:
                                continue
                    except Exception:
                        model_to_validate = None
            
            # Validate the model if we found one
            if model_to_validate:
                print(f"Validating model availability: {model_to_validate}")
                is_valid, available_models = validate_model_availability(model_to_validate)
                
                if not is_valid and available_models:
                    orchestrator.logger.error(f"Model '{model_to_validate}' is not available in Ollama")
                    orchestrator.logger.error(f"Available models: {', '.join(available_models)}")
                    orchestrator.logger.info(f"You can install the model with: ollama pull {model_to_validate}")
                    print(f"Error: Model '{model_to_validate}' is not available in Ollama")
                    print(f"Available models: {', '.join(available_models)}")
                    print(f"You can install the model with: ollama pull {model_to_validate}")
                    sys.exit(1)
                elif is_valid and available_models:
                    print(f"✅ Model '{model_to_validate}' is available")
                    orchestrator.logger.info(f"Validated model: {model_to_validate}")
            else:
                print("Warning: Could not determine which model will be used for validation")
        
        # Set logging level
        if args.verbose:
            orchestrator.logger.logger.setLevel(logging.DEBUG)
        
        # Run workflow
        results = orchestrator.run_workflow(input_dir, output_dir, steps)
        
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
        
        # Exit with appropriate code
        sys.exit(0 if results['success'] else 1)
        
    except KeyboardInterrupt:
        print("\nWorkflow interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
