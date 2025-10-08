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
import shlex

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


def validate_prompt_style(style: str, config_file: str = "image_describer_config.json") -> str:
    """Validate and normalize prompt style with case-insensitive lookup"""
    if not style:
        return "detailed"
    
    try:
        import json
        config_paths = [
            config_file,
            "image_describer_config.json",
            "scripts/image_describer_config.json"
        ]
        
        for config_path in config_paths:
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    prompt_variations = config.get('prompt_variations', {})
                    
                    # Create case-insensitive lookup
                    lower_variations = {k.lower(): k for k in prompt_variations.keys()}
                    
                    # Check if style exists (case-insensitive)
                    if style.lower() in lower_variations:
                        return lower_variations[style.lower()]
                    
                    break  # Found config file, exit loop
            except (FileNotFoundError, json.JSONDecodeError):
                continue
                
    except Exception:
        pass
        
    # Fallback to detailed if style not found
    return "detailed"


def get_effective_prompt_style(args, config_file: str = "workflow_config.json") -> str:
    """Determine which prompt style will actually be used"""
    # Command line argument takes precedence
    if hasattr(args, 'prompt_style') and args.prompt_style:
        return validate_prompt_style(args.prompt_style)
    
    # Check workflow config file
    try:
        config = WorkflowConfig(config_file)
        workflow_prompt = config.config.get("workflow", {}).get("steps", {}).get("image_description", {}).get("prompt_style")
        if workflow_prompt:
            return validate_prompt_style(workflow_prompt)
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
                return validate_prompt_style(default_style)
            except (FileNotFoundError, ImportError):
                continue
                
    except Exception:
        pass
        
    return "detailed"


class WorkflowOrchestrator:
    """Main workflow orchestrator class"""
    
    def __init__(self, config_file: str = "workflow_config.json", base_output_dir: Optional[Path] = None, 
                 model: Optional[str] = None, prompt_style: Optional[str] = None, provider: str = "ollama", 
                 api_key_file: str = None):
        """
        Initialize the workflow orchestrator
        
        Args:
            config_file: Path to workflow configuration file
            base_output_dir: Base output directory for the workflow
            model: Override model name
            prompt_style: Override prompt style
            provider: AI provider to use (ollama, openai, claude)
            api_key_file: Path to API key file for cloud providers
        """
        self.config = WorkflowConfig(config_file)
        if base_output_dir:
            self.config.set_base_output_dir(base_output_dir)
        self.logger = WorkflowLogger("workflow_orchestrator", base_output_dir=self.config.base_output_dir)
        self.discovery = FileDiscovery(self.config)
        
        # Store override settings for resume functionality
        self.override_model = model
        self.override_prompt_style = prompt_style
        self.provider = provider
        self.api_key_file = api_key_file
        
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
        
    def _update_status_log(self) -> None:
        """Update the simple status.log file with current progress"""
        status_lines = []
        
        # Add overall progress
        total_steps = len(self.statistics['steps_completed']) + len(self.statistics['steps_failed'])
        if total_steps > 0:
            status_lines.append(f"Workflow Progress: {len(self.statistics['steps_completed'])}/{total_steps} steps completed")
        
        # Add step-specific status
        if 'video' in self.statistics['steps_completed']:
            status_lines.append(f"✓ Video extraction complete ({self.statistics['total_videos_processed']} videos)")
        elif 'video' in self.statistics['steps_failed']:
            status_lines.append(f"✗ Video extraction failed")
            
        if 'convert' in self.statistics['steps_completed']:
            status_lines.append(f"✓ Image conversion complete ({self.statistics['total_conversions']} images)")
        elif 'convert' in self.statistics['steps_failed']:
            status_lines.append(f"✗ Image conversion failed")
            
        if 'describe' in self.statistics['steps_completed']:
            status_lines.append(f"✓ Image description complete ({self.statistics['total_descriptions']} descriptions)")
        elif 'describe' in self.step_results.get('describe', {}).get('in_progress'):
            # Check if we have progress data
            desc_result = self.step_results.get('describe', {})
            if 'processed' in desc_result and 'total' in desc_result:
                status_lines.append(f"⟳ Image description in progress: {desc_result['processed']}/{desc_result['total']} images described")
            else:
                status_lines.append(f"⟳ Image description in progress...")
        elif 'describe' in self.statistics['steps_failed']:
            status_lines.append(f"✗ Image description failed")
            
        if 'html' in self.statistics['steps_completed']:
            status_lines.append(f"✓ HTML generation complete")
        elif 'html' in self.statistics['steps_failed']:
            status_lines.append(f"✗ HTML generation failed")
        
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
            # Get the path to image_describer.py in the scripts directory
            scripts_dir = Path(__file__).parent
            image_describer_path = scripts_dir / "image_describer.py"
            
            cmd = [
                sys.executable, str(image_describer_path),
                str(temp_combined_dir),
                "--recursive",
                "--output-dir", str(output_dir),
                "--log-dir", str(self.config.base_output_dir / "logs")
            ]
            
            # Add provider parameter
            if self.provider:
                cmd.extend(["--provider", self.provider])
                self.logger.info(f"Using AI provider: {self.provider}")
            
            # Add API key file if provided
            if self.api_key_file:
                cmd.extend(["--api-key-file", self.api_key_file])
                self.logger.info(f"Using API key file: {self.api_key_file}")
            
            # Add optional parameters
            if "config_file" in step_config:
                cmd.extend(["--config", step_config["config_file"]])
            
            # Use override model if provided (for resume), otherwise use config
            if self.override_model:
                cmd.extend(["--model", self.override_model])
                self.logger.info(f"Using override model for resume: {self.override_model}")
            elif "model" in step_config and step_config["model"]:
                cmd.extend(["--model", step_config["model"]])
            
            # Handle prompt style - use override if provided (for resume), otherwise use config
            if self.override_prompt_style:
                validated_style = validate_prompt_style(self.override_prompt_style)
                cmd.extend(["--prompt-style", validated_style])
                self.logger.info(f"Using override prompt style for resume: {self.override_prompt_style}")
            elif "prompt_style" in step_config and step_config["prompt_style"]:
                validated_style = validate_prompt_style(step_config["prompt_style"])
                cmd.extend(["--prompt-style", validated_style])
            else:
                # Get default prompt style from image describer config
                config_file = step_config.get("config_file", "image_describer_config.json")
                default_style = get_default_prompt_style(config_file)
                validated_style = validate_prompt_style(default_style)
                if validated_style != "detailed":  # Only add if different from hardcoded default
                    cmd.extend(["--prompt-style", validated_style])
            
            # Single call to image_describer.py with all images
            self.logger.info(f"Running single image description process: {' '.join(cmd)}")
            
            # Store total images for status updates
            self.step_results['describe'] = {
                'in_progress': True,
                'total': len(combined_image_list),
                'processed': 0
            }
            self._update_status_log()
            
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            
            # Log the subprocess output for transparency
            if result.stdout.strip():
                self.logger.info(f"image_describer.py output:\n{result.stdout}")
            if result.stderr.strip():
                self.logger.warning(f"image_describer.py stderr:\n{result.stderr}")
            
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
        
        # Update initial status
        self._update_status_log()
        
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
                    
                    # Update status log after successful step
                    self._update_status_log()
                    
                    # Update input directory for next step if this step produced outputs
                    if step in ["video", "convert"] and step_result.get("output_dir"):
                        current_input_dir = step_result["output_dir"]
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
                state["steps"] = [s.strip() for s in steps_part.split(',')]
            
            elif "Input directory:" in line:
                # Extract input directory
                input_part = line.split("Input directory:")[1].strip()
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
  python workflow.py media_folder
  python workflow.py media_folder --output-dir results
  python workflow.py photos --steps describe,html
  python workflow.py videos --steps video,describe,html --model llava:7b
  
  # OpenAI
  python workflow.py photos --provider openai --model gpt-4o-mini --api-key-file ~/openai.txt
  python workflow.py media --provider openai --model gpt-4o --steps describe,html
  
  # Claude (Anthropic)
  python workflow.py photos --provider claude --model claude-sonnet-4-5-20250929 --api-key-file ~/claude.txt
  python workflow.py media --provider claude --model claude-3-5-haiku-20241022 --steps describe,html
  
  # Configuration
  python workflow.py mixed_media --output-dir analysis --config my_workflow.json
  
Resume Examples:
  python workflow.py --resume workflow_output_20250919_153443
  python workflow.py --resume /path/to/interrupted/workflow
  
  # ⚠️ Cloud providers require API key when resuming:
  python workflow.py --resume wf_openai_gpt-4o-mini_20251005_122700 --api-key-file ~/openai.txt
  python workflow.py --resume wf_claude_sonnet-4-5_20251005_150328 --api-key-file ~/claude.txt
  # See docs/WORKFLOW_RESUME_API_KEY.md for details
        """
    )
    
    parser.add_argument(
        "input_dir",
        nargs='?',  # Make input_dir optional when using --resume
        help="Input directory containing media files to process"
    )
    
    parser.add_argument(
        "--resume", "-r",
        help="Resume an interrupted workflow from the specified output directory"
    )
    
    parser.add_argument(
        "--preserve-descriptions",
        action="store_true",
        help="When resuming, preserve existing descriptions and skip describe step if substantial progress exists"
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
        "--provider",
        choices=["ollama", "openai", "claude"],
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
        "--original-cwd",
        help=argparse.SUPPRESS  # Hidden argument for wrapper communication
    )
    
    args = parser.parse_args()
    
    # Handle resume mode
    if args.resume:
        # Resume mode - validate resume directory and extract workflow state
        resume_dir = Path(args.resume)
        
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
        
        # Override with state from logs
        if workflow_state["model"]:
            args.model = workflow_state["model"]
        if workflow_state["prompt_style"]:
            args.prompt_style = workflow_state["prompt_style"]
        if workflow_state["provider"]:
            args.provider = workflow_state["provider"]
        if workflow_state["config"]:
            args.config = workflow_state["config"]
        
        # Filter steps to only include those not yet completed
        remaining_steps = []
        for step in steps:
            if step not in workflow_state["completed_steps"]:
                # Special handling for partially completed describe step
                if step == "describe" and step in workflow_state.get("partially_completed_steps", []):
                    desc_count = workflow_state.get('describe_progress', 0)
                    if desc_count > 0:
                        print(f"INFO: Describe step was partially completed ({desc_count} descriptions exist)")
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
        
    else:
        # Normal mode - validate input directory is provided
        if not args.input_dir:
            print("Error: input_dir is required when not using --resume")
            parser.print_help()
            sys.exit(1)
        
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
        # Create timestamped workflow output directory with provider, model, and prompt info
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Get provider, model and prompt info for directory naming
        provider_name = args.provider if args.provider else "ollama"
        model_name = get_effective_model(args, args.config)
        prompt_style = get_effective_prompt_style(args, args.config)
        
        # Create descriptive directory name (wf = workflow)
        wf_dirname = f"wf_{provider_name}_{model_name}_{prompt_style}_{timestamp}"
        
        if args.output_dir:
            # User specified output directory - create wf_ directory inside it
            base_dir = Path(args.output_dir)
            if not base_dir.is_absolute():
                base_dir = (Path(original_cwd) / base_dir).resolve()
            output_dir = (base_dir / wf_dirname).resolve()
        else:
            # No output directory specified - create wf_ directory in current directory
            output_dir = (Path(original_cwd) / wf_dirname).resolve()
        
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
        orchestrator = WorkflowOrchestrator(
            args.config, 
            base_output_dir=output_dir, 
            model=args.model, 
            prompt_style=args.prompt_style, 
            provider=args.provider, 
            api_key_file=args.api_key_file
        )
        
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
            orchestrator.config.config["workflow"]["steps"]["image_description"]["prompt_style"] = args.prompt_style
        
        # Set logging level
        if args.verbose:
            orchestrator.logger.logger.setLevel(logging.DEBUG)
        
        # Run workflow
        results = orchestrator.run_workflow(input_dir, output_dir, steps)
        
        # Log original command for resume functionality
        if not args.resume:  # Only log original command for new workflows
            original_cmd = ["python", "workflow.py", str(input_dir)]
            if args.output_dir:
                original_cmd.extend(["--output-dir", args.output_dir])
            if args.steps != "video,convert,describe,html":
                original_cmd.extend(["--steps", args.steps])
            if args.model:
                original_cmd.extend(["--model", args.model])
            if args.prompt_style:
                original_cmd.extend(["--prompt-style", args.prompt_style])
            if args.config != "workflow_config.json":
                original_cmd.extend(["--config", args.config])
            if args.verbose:
                original_cmd.append("--verbose")
            
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
