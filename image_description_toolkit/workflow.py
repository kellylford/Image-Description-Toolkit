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
from .workflow_utils import WorkflowConfig, WorkflowLogger, FileDiscovery, create_workflow_paths
from .image_describer import get_default_prompt_style


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
            
            total_processed = 0
            
            # Process each directory that contains images
            for i, search_dir in enumerate(search_dirs):
                dir_image_files = self.discovery.find_files_by_type(search_dir, "images")
                if not dir_image_files:
                    continue
                    
                self.logger.info(f"Processing {len(dir_image_files)} images from: {search_dir}")
                
                # Build command for this directory
                cmd = [
                    sys.executable, "image_describer.py",
                    str(search_dir),
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
                
                # For first directory, create new file; for subsequent directories, the script will append automatically
                self.logger.info(f"Running: {' '.join(cmd)}")
                
                result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
                
                # Log the subprocess output for transparency
                if result.stdout.strip():
                    self.logger.info(f"image_describer.py output:\n{result.stdout}")
                if result.stderr.strip():
                    self.logger.warning(f"image_describer.py stderr:\n{result.stderr}")
                
                if result.returncode == 0:
                    self.logger.info(f"Image description completed for {search_dir}")
                    total_processed += len(dir_image_files)
                else:
                    self.logger.error(f"Image description failed for {search_dir}: {result.stderr}")
                    return {"success": False, "error": f"Failed processing {search_dir}: {result.stderr}"}
            
            # All directories processed successfully
            self.logger.info("Image description completed successfully")
            
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
        "--original-cwd",
        help=argparse.SUPPRESS  # Hidden argument for wrapper communication
    )
    
    args = parser.parse_args()
    
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
        # Create timestamped workflow output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = (Path(original_cwd) / f"workflow_output_{timestamp}").resolve()
    
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
            orchestrator.config.config["workflow"]["steps"]["image_description"]["prompt_style"] = args.prompt_style
        
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
