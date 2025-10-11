#!/usr/bin/env python3
"""
Video Frame Extractor
Extracts frames from video files based on configurable options including scene change detection.
"""

import cv2
import os
import json
import argparse
import numpy as np
from pathlib import Path
from typing import List
import time
import logging
from datetime import datetime

class VideoFrameExtractor:
    def __init__(self, config_file: str = "video_frame_extractor_config.json", log_dir: str = None):
        self.supported_formats = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
        self.config_file = config_file  # Store for logging
        self.log_dir = log_dir
        self.setup_logging()  # Set up logging first
        self.config = self.load_config(config_file)  # Now we can use logger in load_config
        self.logger.info("VideoFrameExtractor initialized successfully")
        self.logger.info(f"Supported video formats: {', '.join(sorted(self.supported_formats))}")
        self.logger.info(f"Extraction mode: {self.config.get('extraction_mode', 'unknown')}")
        
        # Initialize processing statistics
        self.statistics = {
            "total_videos_found": 0,
            "total_videos_processed": 0,
            "total_videos_skipped": 0,
            "total_frames_extracted": 0,
            "frames_saved": 0,
            "videos_processed": 0,
            "start_time": None,
            "end_time": None,
            "errors": []
        }
        
    def setup_logging(self):
        """Set up logging to both console and file"""
        # Create log filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Use provided log directory or try to detect workflow directory
        if self.log_dir:
            logs_dir = Path(self.log_dir) / "logs"
        else:
            # Try to get workflow base output directory
            try:
                from workflow_utils import WorkflowConfig
                config = WorkflowConfig()
                logs_dir = config.base_output_dir / "logs"
            except:
                # Fallback to relative path
                logs_dir = Path("workflow_output") / "logs"
                
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_filename = logs_dir / f"frame_extractor_{timestamp}.log"
        
        # Create logger
        self.logger = logging.getLogger(f"frame_extractor_{timestamp}")
        self.logger.setLevel(logging.INFO)
        
        # Clear any existing handlers to avoid duplicates
        self.logger.handlers.clear()
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # Create file handler
        file_handler = logging.FileHandler(log_filename, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        # Add handlers to logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        self.logger.info(f"Video Frame Extractor started")
        self.logger.info(f"Log file: {log_filename.absolute()}")
        self.logger.info(f"Working directory: {os.getcwd()}")
        self.logger.info(f"Configuration loaded from: {os.path.abspath(self.config_file) if hasattr(self, 'config_file') else 'default'}")
        
    def load_config(self, config_file: str) -> dict:
        """Load configuration from JSON file"""
        try:
            config_path = Path(config_file)
            if not config_path.is_absolute():
                # Look for config file in script directory first
                script_dir = Path(__file__).parent
                config_path = script_dir / config_file
            
            if not config_path.exists():
                self.logger.warning(f"Config file not found: {config_path}")
                return self.get_default_config()
                
            with open(config_path, 'r') as f:
                content = f.read().strip()
                if not content:
                    self.logger.info(f"Config file {config_path} is empty. Using default config.")
                    return self.get_default_config()
                config = json.loads(content)
                self.logger.info(f"Configuration loaded from: {config_path}")
                return config
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing config file {config_file}: {e}")
            self.logger.info("Using default config.")
            return self.get_default_config()
        except Exception as e:
            self.logger.error(f"Error loading config file {config_file}: {e}")
            self.logger.info("Using default config.")
            return self.get_default_config()
    
    def get_default_config(self) -> dict:
        """Get the default configuration without creating a file"""
        
        # Use workflow output directory by default
        default_output_dir = "extracted_frames"
        try:
            from workflow_utils import WorkflowConfig
            config = WorkflowConfig()
            workflow_output_dir = config.get_step_output_dir("video_extraction", create=False)
            default_output_dir = str(workflow_output_dir)
        except ImportError:
            # workflow_utils not available, use default
            pass
        
        default_config = {
            "extraction_mode": "time_interval",
            "time_interval_seconds": 5.0,
            "scene_change_threshold": 30.0,
            "min_scene_duration_seconds": 1.0,
            "output_directory": default_output_dir,
            "preserve_directory_structure": False,
            "image_quality": 95,
            "resize_width": None,
            "resize_height": None,
            "frame_prefix": "frame",
            "start_time_seconds": 0,
            "end_time_seconds": None,
            "max_frames_per_video": None,
            "skip_existing": False,
            "log_progress": True
        }
        
        self.logger.info("Using default configuration settings.")
        return default_config
    
    def create_default_config_file(self, config_file: str) -> dict:
        """Create a default configuration file and return the config (for manual config file creation)"""
        
        default_config = self.get_default_config()
        
        try:
            with open(config_file, 'w') as f:
                json.dump(default_config, f, indent=4, ensure_ascii=False)
            
            self.logger.info(f"Created default config file: {config_file}")
            self.logger.info("You can edit this file to customize extraction settings.")
        except Exception as e:
            self.logger.warning(f"Could not create config file {config_file}: {e}")
            self.logger.info("Using default configuration in memory.")
        
        return default_config
    
    def calculate_scene_change(self, frame1: np.ndarray, frame2: np.ndarray) -> float:
        """Calculate the difference between two frames as a percentage"""
        if frame1 is None or frame2 is None:
            return 0.0

        # Convert to grayscale for comparison
        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
        
        # Calculate absolute difference
        diff = cv2.absdiff(gray1, gray2)
        
        # Calculate percentage of pixels that changed significantly
        threshold = 30  # Pixel difference threshold
        changed_pixels = np.sum(diff > threshold)
        total_pixels = diff.shape[0] * diff.shape[1]
        
        return (changed_pixels / total_pixels) * 100
    
    def extract_frames_time_interval(self, video_path: str, output_dir: str) -> List[str]:
        """Extract frames at regular time intervals"""
        self.logger.info("Using time interval extraction mode")
        
        # Extract video name for frame naming
        video_name = Path(video_path).stem
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            error_msg = f"Could not open video {video_path}"
            self.logger.error(error_msg)
            return []
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        
        interval_frames = int(fps * self.config["time_interval_seconds"])
        start_frame = int(fps * self.config["start_time_seconds"])
        end_frame = int(fps * self.config["end_time_seconds"]) if self.config["end_time_seconds"] else total_frames
        
        self.logger.info(f"Video properties: duration={duration:.1f}s, fps={fps:.1f}, total_frames={total_frames}")
        self.logger.info(f"Extraction settings: interval={self.config['time_interval_seconds']}s, start={self.config['start_time_seconds']}s")
        self.logger.info(f"Frame range: {start_frame} to {end_frame} (every {interval_frames} frames)")
        
        estimated_frames = (end_frame - start_frame) // interval_frames
        if self.config["max_frames_per_video"]:
            estimated_frames = min(estimated_frames, self.config["max_frames_per_video"])
        self.logger.info(f"Estimated frames to extract: {estimated_frames}")
        
        extracted_files = []
        frame_count = 0
        current_frame = start_frame
        
        while current_frame < end_frame:
            if self.config["max_frames_per_video"] and frame_count >= self.config["max_frames_per_video"]:
                self.logger.info(f"Reached maximum frames limit: {self.config['max_frames_per_video']}")
                break
                
            cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
            ret, frame = cap.read()
            
            if not ret:
                self.logger.warning(f"Failed to read frame at position {current_frame}")
                break
            
            # Resize if specified
            if self.config["resize_width"] or self.config["resize_height"]:
                frame = self.resize_frame(frame)
            
            # Save frame with video name for clear source attribution
            timestamp = current_frame / fps
            filename = f"{video_name}_{timestamp:.2f}s.jpg"
            output_path = os.path.join(output_dir, filename)
            
            success = cv2.imwrite(output_path, frame, [cv2.IMWRITE_JPEG_QUALITY, self.config["image_quality"]])
            if success:
                extracted_files.append(output_path)
                frame_count += 1
                
                # Preserve video timestamp on frame file for chronological sorting
                try:
                    video_stat = os.stat(video_path)
                    os.utime(output_path, (video_stat.st_atime, video_stat.st_mtime))
                except OSError as e:
                    self.logger.debug(f"Could not preserve timestamp on {output_path}: {e}")
            else:
                self.logger.error(f"Failed to save frame to {output_path}")
            
            current_frame += interval_frames
            
            # Progress logging every 10 frames or at specific intervals
            if frame_count % 10 == 0 or frame_count == estimated_frames:
                progress = (frame_count / estimated_frames * 100) if estimated_frames > 0 else 0
                self.logger.info(f"Progress: {frame_count}/{estimated_frames} frames ({progress:.1f}%)")
        
        cap.release()
        self.logger.info(f"Time interval extraction completed: {len(extracted_files)} frames extracted")
        return extracted_files
    
    def extract_frames_scene_change(self, video_path: str, output_dir: str) -> List[str]:
        """Extract frames when scene changes are detected"""
        self.logger.info("Using scene change detection mode")
        start_time = time.time()
        
        # Extract video name for frame naming
        video_name = Path(video_path).stem
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            error_msg = f"Could not open video {video_path}"
            self.logger.error(error_msg)
            return []
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        
        start_frame = int(fps * self.config["start_time_seconds"])
        end_frame = int(fps * self.config["end_time_seconds"]) if self.config["end_time_seconds"] else total_frames
        min_scene_frames = int(fps * self.config["min_scene_duration_seconds"])
        
        self.logger.info(f"Video properties: duration={duration:.1f}s, fps={fps:.1f}, total_frames={total_frames}")
        self.logger.info(f"Scene detection settings: threshold={self.config['scene_change_threshold']}%, min_duration={self.config['min_scene_duration_seconds']}s")
        self.logger.info(f"Frame range: {start_frame} to {end_frame}")
        
        extracted_files = []
        frame_count = 0
        last_scene_frame = start_frame
        prev_frame = None
        scenes_detected = 0
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        
        for current_frame_num in range(start_frame, end_frame):
            if self.config["max_frames_per_video"] and frame_count >= self.config["max_frames_per_video"]:
                self.logger.info(f"Reached maximum frames limit: {self.config['max_frames_per_video']}")
                break
            
            ret, frame = cap.read()
            if not ret:
                self.logger.warning(f"Failed to read frame at position {current_frame_num}")
                break
            
            # Check for scene change
            if prev_frame is not None:
                change_percentage = self.calculate_scene_change(prev_frame, frame)
                
                # If significant change and minimum time has passed
                if (change_percentage > self.config["scene_change_threshold"] and 
                    current_frame_num - last_scene_frame >= min_scene_frames):
                    
                    scenes_detected += 1
                    timestamp = current_frame_num / fps
                    self.logger.info(f"Scene change detected at {timestamp:.2f}s (frame {current_frame_num}): {change_percentage:.1f}% change")
                    
                    # Resize if specified
                    save_frame = frame
                    if self.config["resize_width"] or self.config["resize_height"]:
                        save_frame = self.resize_frame(frame)
                    
                    # Save frame with video name for clear source attribution
                    filename = f"{video_name}_scene_{scenes_detected:04d}_{timestamp:.2f}s.jpg"
                    output_path = os.path.join(output_dir, filename)
                    
                    success = cv2.imwrite(output_path, save_frame, [cv2.IMWRITE_JPEG_QUALITY, self.config["image_quality"]])
                    if success:
                        extracted_files.append(output_path)
                        self.statistics['frames_saved'] += 1
                        frame_count += 1
                        last_scene_frame = current_frame_num
                        self.logger.info(f"Saved frame: {os.path.abspath(output_path)}")
                        
                        # Preserve video timestamp on frame file for chronological sorting
                        try:
                            video_stat = os.stat(video_path)
                            os.utime(output_path, (video_stat.st_atime, video_stat.st_mtime))
                        except OSError as e:
                            self.logger.debug(f"Could not preserve timestamp on {output_path}: {e}")
                    else:
                        self.logger.error(f"Failed to save frame to {output_path}")
            
            prev_frame = frame.copy()
            
            # Progress logging every 1000 frames
            if current_frame_num % 1000 == 0:
                progress = ((current_frame_num - start_frame) / (end_frame - start_frame) * 100)
                self.logger.info(f"Progress: {current_frame_num}/{end_frame} frames processed ({progress:.1f}%), {scenes_detected} scenes detected")
        
        cap.release()
        
        # Final statistics
        elapsed_time = time.time() - start_time
        self.statistics['total_frames_processed'] = current_frame_num
        self.statistics['processing_time'] = elapsed_time
        
        self.logger.info(f"Scene change extraction completed: {len(extracted_files)} frames extracted from {scenes_detected} scenes")
        self.logger.info(f"Processing time: {elapsed_time:.2f} seconds")
        if elapsed_time > 0:
            self.logger.info(f"Frames per second: {current_frame_num / elapsed_time:.2f}")
        
        return extracted_files
    
    def resize_frame(self, frame: np.ndarray) -> np.ndarray:
        """Resize frame based on config settings"""
        height, width = frame.shape[:2]
        new_width = self.config["resize_width"]
        new_height = self.config["resize_height"]
        
        if new_width and new_height:
            return cv2.resize(frame, (new_width, new_height))
        elif new_width:
            ratio = new_width / width
            new_height = int(height * ratio)
            return cv2.resize(frame, (new_width, new_height))
        elif new_height:
            ratio = new_height / height
            new_width = int(width * ratio)
            return cv2.resize(frame, (new_width, new_height))
        
        return frame
    
    def process_video(self, video_path: str) -> List[str]:
        """Process a single video file"""
        video_start_time = time.time()
        video_name = Path(video_path).stem
        
        self.logger.info(f"Processing video: {video_path}")
        self.logger.info(f"Video name: {video_name}")
        
        # Create output directory
        if self.config["preserve_directory_structure"]:
            # Get relative path from current directory
            rel_path = os.path.relpath(video_path)
            self.logger.debug(f"Relative path from current dir: {rel_path}")
            self.logger.debug(f"Directory part: {os.path.dirname(rel_path)}")
            output_subdir = os.path.join(
                self.config["output_directory"],
                os.path.dirname(rel_path),
                video_name
            )
        else:
            # Simple flat structure: just output_directory/video_name
            output_subdir = os.path.join(
                self.config["output_directory"],
                video_name
            )
        
        self.logger.info(f"Output directory: {os.path.abspath(output_subdir)}")
        os.makedirs(output_subdir, exist_ok=True)
        
        # Check if we should skip existing
        if self.config["skip_existing"]:
            existing_files = os.listdir(output_subdir)
            if existing_files:
                self.logger.info(f"Skipping video: Output directory not empty")
                self.logger.info(f"Found {len(existing_files)} existing files in: {os.path.abspath(output_subdir)}")
                self.logger.debug(f"First few files: {existing_files[:5]}")
                self.statistics["total_videos_skipped"] += 1
                return []
        
        # Extract frames based on mode
        try:
            if self.config["extraction_mode"] == "time_interval":
                extracted_files = self.extract_frames_time_interval(video_path, output_subdir)
            elif self.config["extraction_mode"] == "scene_change":
                extracted_files = self.extract_frames_scene_change(video_path, output_subdir)
            else:
                error_msg = f"Unknown extraction mode '{self.config['extraction_mode']}'"
                self.logger.error(error_msg)
                self.statistics["errors"].append(f"{video_name}: {error_msg}")
                return []
        except Exception as e:
            error_msg = f"Error processing video {video_name}: {str(e)}"
            self.logger.error(error_msg)
            self.statistics["errors"].append(error_msg)
            return []
        
        # Calculate processing time and log summary
        video_end_time = time.time()
        processing_time = video_end_time - video_start_time
        
        if extracted_files:
            self.logger.info(f"Successfully extracted {len(extracted_files)} frames")
            self.logger.info(f"Processing time: {processing_time:.2f} seconds")
            self.logger.info(f"First frame: {os.path.basename(extracted_files[0])}")
            self.logger.info(f"Last frame: {os.path.basename(extracted_files[-1])}")
            self.statistics["total_frames_extracted"] += len(extracted_files)
            self.statistics["total_videos_processed"] += 1
        else:
            self.logger.warning(f"No frames extracted from {video_name}")
        
        return extracted_files
    
    def log_final_summary(self):
        """Log comprehensive final statistics"""
        if 'start_time' not in self.statistics:
            return
            
        total_time = time.time() - self.statistics['start_time']
        
        self.logger.info("")
        self.logger.info("="*60)
        self.logger.info("FINAL PROCESSING SUMMARY")
        self.logger.info("="*60)
        
        # Video processing statistics
        self.logger.info(f"Videos processed: {self.statistics.get('videos_processed', 0)}")
        self.logger.info(f"Total frames extracted: {self.statistics.get('total_frames_extracted', 0)}")
        self.logger.info(f"Total frames saved: {self.statistics.get('frames_saved', 0)}")
        self.logger.info(f"Total frames processed: {self.statistics.get('total_frames_processed', 0)}")
        
        # Timing statistics
        self.logger.info(f"Total processing time: {total_time:.2f} seconds")
        if self.statistics.get('total_frames_processed', 0) > 0:
            fps = self.statistics['total_frames_processed'] / total_time
            self.logger.info(f"Overall processing rate: {fps:.2f} frames/second")
        
        # Configuration summary
        self.logger.info(f"Extraction mode: {self.config['extraction_mode']}")
        if self.config['extraction_mode'] == 'time_interval':
            self.logger.info(f"Time interval: {self.config['time_interval_seconds']} seconds")
        else:
            self.logger.info(f"Scene change threshold: {self.config['scene_change_threshold']}%")
        
        self.logger.info(f"Output directory: {os.path.abspath(self.config['output_directory'])}")
        self.logger.info("="*60)
    
    def find_video_files(self, directory: str) -> List[str]:
        """Find all video files in directory and subdirectories"""
        video_files = []
        abs_directory = os.path.abspath(directory)
        
        self.logger.info(f"Searching for video files in: {abs_directory}")
            
        if not os.path.exists(directory):
            self.logger.error(f"Directory does not exist: {abs_directory}")
            return video_files
            
        dir_count = 0
        total_files_checked = 0
        
        for root, dirs, files in os.walk(directory):
            dir_count += 1
            total_files_checked += len(files)
            
            # Log progress every 10 directories
            if dir_count % 10 == 1:
                self.logger.info(f"Checking directory {dir_count}: {root}")
            
            for file in files:
                file_suffix = Path(file).suffix.lower()
                if file_suffix in self.supported_formats:
                    full_path = os.path.join(root, file)
                    video_files.append(full_path)
                    # Log first 10 found videos, then show summary
                    if len(video_files) <= 10:
                        self.logger.info(f"Found video file: {full_path}")
                    elif len(video_files) == 11:
                        self.logger.info("... (additional videos found, showing count only)")
        
        self.logger.info(f"Search complete: {dir_count} directories, {total_files_checked} files checked")
        self.logger.info(f"Total video files found: {len(video_files)}")
            
        return video_files
    
    def run(self, input_path: str):
        """Main execution method"""
        self.statistics['start_time'] = time.time()
        start_time = self.statistics['start_time']
        
        self.logger.info("Video Frame Extractor")
        self.logger.info("===================")
        self.logger.info(f"Mode: {self.config['extraction_mode']}")
        self.logger.info(f"Output directory: {self.config['output_directory']}")
        self.logger.info(f"Full output path: {os.path.abspath(self.config['output_directory'])}")
        self.logger.info("")
        
        # Find video files
        if os.path.isfile(input_path):
            if Path(input_path).suffix.lower() in self.supported_formats:
                video_files = [input_path]
            else:
                self.logger.error(f"{input_path} is not a supported video format")
                return
        else:
            video_files = self.find_video_files(input_path)
        
        if not video_files:
            self.logger.warning("No video files found.")
            return
        
        self.logger.info(f"Found {len(video_files)} video file(s)")
        for i, video in enumerate(video_files, 1):
            self.logger.info(f"  {i}. {video}")
        self.logger.info("")
        
        # Process videos
        total_extracted = 0
        self.statistics['videos_processed'] = 0
        
        for i, video_path in enumerate(video_files, 1):
            self.logger.info(f"[{i}/{len(video_files)}] Processing video: {os.path.basename(video_path)}")
            extracted = self.process_video(video_path)
            total_extracted += len(extracted)
            self.statistics['videos_processed'] += 1
            
            self.logger.info(f"  Extracted {len(extracted)} frames from {os.path.basename(video_path)}")
        
        # Summary
        elapsed_time = time.time() - start_time
        self.statistics['total_extraction_time'] = elapsed_time
        self.statistics['total_frames_extracted'] = total_extracted
        
        self.logger.info("Summary")
        self.logger.info("=======")
        self.logger.info(f"Processed {len(video_files)} video(s)")
        self.logger.info(f"Extracted {total_extracted} frame(s)")
        self.logger.info(f"Time elapsed: {elapsed_time:.1f} seconds")
        self.logger.info(f"Output directory: {os.path.abspath(self.config['output_directory'])}")
        
        # Help user find the files
        if total_extracted > 0:
            self.logger.info("\n" + "="*50)
            self.logger.info("WHERE TO FIND YOUR EXTRACTED FRAMES:")
            self.logger.info("="*50)
            
            # Check if output directory exists and list its contents
            output_dir = os.path.abspath(self.config['output_directory'])
            if os.path.exists(output_dir):
                self.logger.info(f"Main output directory: {output_dir}")
                
                # List all subdirectories
                try:
                    for root, dirs, files in os.walk(output_dir):
                        if files:  # Only show directories that contain files
                            self.logger.info(f"  Directory: {root}")
                            self.logger.info(f"    Contains {len(files)} files")
                            if files:
                                self.logger.info(f"    Sample files: {files[:3]}")
                except Exception as e:
                    self.logger.error(f"Error listing directories: {e}")
            else:
                self.logger.warning(f"Output directory {output_dir} does not exist!")
            
            self.logger.info("\nTo open the directory in Windows Explorer:")
            self.logger.info(f'explorer "{output_dir}"')
            self.logger.info("="*50)
        
        # Log final comprehensive summary
        self.log_final_summary()

def main():
    parser = argparse.ArgumentParser(description="Extract frames from video files")
    parser.add_argument("input", nargs='?', help="Input video file or directory")
    parser.add_argument("-c", "--config", default="video_frame_extractor_config.json",
                       help="Path to config file (default: video_frame_extractor_config.json)")
    parser.add_argument("--log-dir", help="Directory for log files (default: auto-detect workflow directory)")
    parser.add_argument("--output-dir", help="Output directory for extracted frames (overrides config)")
    parser.add_argument("--create-config", action="store_true",
                       help="Create a default config file and exit")
    
    # Extraction mode options (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--time", type=float, metavar="SECONDS",
                           help="Use time interval extraction mode with specified interval in seconds (overrides config)")
    mode_group.add_argument("--scene", type=float, metavar="THRESHOLD",
                           help="Use scene change detection mode with specified threshold percentage (overrides config)")
    
    args = parser.parse_args()
    
    # Handle config file creation
    if args.create_config:
        extractor = VideoFrameExtractor(args.config, log_dir=args.log_dir)
        extractor.create_default_config_file(args.config)
        print(f"Default config file created: {args.config}")
        return
    
    # Require input for normal operation
    if not args.input:
        parser.error("Input file or directory is required unless using --create-config")
    
    extractor = VideoFrameExtractor(args.config, log_dir=args.log_dir)
    
    # Override output directory if specified
    if args.output_dir:
        extractor.config["output_directory"] = args.output_dir
        extractor.logger.info(f"Command line override: Using output directory: {args.output_dir}")
    
    # Override extraction mode based on command line arguments
    if args.time is not None:
        extractor.config["extraction_mode"] = "time_interval"
        extractor.config["time_interval_seconds"] = args.time
        extractor.logger.info(f"Command line override: Using time interval extraction mode ({args.time}s intervals)")
    elif args.scene is not None:
        extractor.config["extraction_mode"] = "scene_change"
        extractor.config["scene_change_threshold"] = args.scene
        extractor.logger.info(f"Command line override: Using scene change detection mode ({args.scene}% threshold)")
    
    extractor.run(args.input)

if __name__ == "__main__":
    main()
