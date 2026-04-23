#!/usr/bin/env python3
"""
Video Description Module

Provides AI-powered video description capabilities. Unlike video_frame_extractor 
which extracts frames for later processing, this module sends videos (or 
representative frames) directly to AI models for a single cohesive description.

Features:
- Extract key frames from video and send to vision models
- Support for multiple AI providers (Ollama, OpenAI, Claude)
- Scene change detection for intelligent frame selection
- Batch processing of videos
- Preserves video metadata (GPS, timestamp) in descriptions
"""

import cv2
import os
import json
import argparse
import numpy as np
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import time
import sys
import base64
from io import BytesIO

# Add script directory to path for frozen executables
_script_dir = Path(__file__).parent.resolve()
if str(_script_dir) not in sys.path:
    sys.path.insert(0, str(_script_dir))

# Also add parent directory (for imagedescriber/ai_providers access)
_parent_dir = _script_dir.parent
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))

# Import frame extraction logic from existing module
try:
    from video_frame_extractor import VideoFrameExtractor
except ImportError:
    try:
        from scripts.video_frame_extractor import VideoFrameExtractor
    except ImportError:
        VideoFrameExtractor = None

# Import metadata extraction
try:
    from video_metadata_extractor import VideoMetadataExtractor
    from exif_embedder import ExifEmbedder
    VIDEO_METADATA_AVAILABLE = True
except ImportError:
    try:
        from scripts.video_metadata_extractor import VideoMetadataExtractor
        from scripts.exif_embedder import ExifEmbedder
        VIDEO_METADATA_AVAILABLE = True
    except ImportError:
        VIDEO_METADATA_AVAILABLE = False
        VideoMetadataExtractor = None
        ExifEmbedder = None

# Import AI providers - try multiple locations
try:
    from ai_providers import get_available_providers
    AI_PROVIDERS_AVAILABLE = True
except ImportError:
    try:
        from imagedescriber.ai_providers import get_available_providers
        AI_PROVIDERS_AVAILABLE = True
    except ImportError:
        try:
            from scripts.ai_providers import get_available_providers
            AI_PROVIDERS_AVAILABLE = True
        except ImportError:
            AI_PROVIDERS_AVAILABLE = False
            get_available_providers = None

import logging

logger = logging.getLogger(__name__)


class VideoDescriber:
    """
    AI-powered video description generator.
    
    Unlike VideoFrameExtractor which extracts frames for later processing,
    VideoDescriber sends videos (or representative frames) directly to AI
    for a single cohesive description.
    """
    
    def __init__(self, config: Optional[Dict] = None, log_dir: Optional[str] = None):
        self.supported_formats = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg', '.3gp', '.3g2', '.mts', '.m2ts'}
        self.config = config or self.get_default_config()
        self.log_dir = log_dir or "."
        self.logger = logger

        # Initialize frame extractor for getting representative frames
        if VideoFrameExtractor:
            self.frame_extractor = VideoFrameExtractor()
        else:
            self.frame_extractor = None
            self.logger.warning("VideoFrameExtractor not available - using basic extraction")
        
        # Initialize metadata extractor
        self.video_metadata_extractor = None
        if VIDEO_METADATA_AVAILABLE and VideoMetadataExtractor:
            self.video_metadata_extractor = VideoMetadataExtractor()
        
        self.logger.info("VideoDescriber initialized")
        
        # Statistics
        self.statistics = {
            "total_videos": 0,
            "processed": 0,
            "failed": 0,
            "start_time": None,
            "end_time": None,
            "errors": []
        }
    
    def get_default_config(self) -> dict:
        """Get default configuration for video description"""
        return {
            # Frame extraction settings
            "frame_selection_mode": "key_frames",  # key_frames, uniform, scene_change
            "num_frames": 5,  # Number of frames to extract for description
            "time_interval_seconds": 5.0,  # For uniform mode
            "scene_change_threshold": 30.0,  # For scene_change mode
            
            # AI settings
            "provider": "ollama",
            "model": "llava",
            "prompt_style": "video_description",
            "custom_prompt": "",
            
            # Output settings
            "output_mode": "description_only",  # description_only, with_frames, detailed
            "include_metadata": True,
            "include_timestamps": True,
        }
    
    def extract_key_frames(self, video_path: str) -> List[Tuple[np.ndarray, float]]:
        """
        Extract key representative frames from video.
        
        Returns list of (frame_image, timestamp_seconds) tuples.
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise Exception(f"Could not open video: {video_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        
        self.logger.info(f"Video: {duration:.1f}s, {total_frames} frames, {fps:.2f} fps")
        
        frames = []
        mode = self.config.get("frame_selection_mode", "key_frames")
        num_frames = self.config.get("num_frames", 5)
        
        if mode == "uniform":
            # Extract evenly spaced frames
            interval = duration / (num_frames + 1)
            for i in range(1, num_frames + 1):
                timestamp = i * interval
                frame_num = int(timestamp * fps)
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                ret, frame = cap.read()
                if ret:
                    frames.append((frame, timestamp))
                    
        elif mode == "scene_change":
            # Extract frames at scene changes
            threshold = self.config.get("scene_change_threshold", 30.0)
            prev_frame = None
            scene_changes = []
            
            for frame_num in range(0, total_frames, int(fps)):  # Check every second
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                ret, frame = cap.read()
                if not ret:
                    break
                    
                if prev_frame is not None:
                    diff = self._calculate_frame_diff(prev_frame, frame)
                    if diff > threshold:
                        timestamp = frame_num / fps
                        scene_changes.append((frame, timestamp))
                        
                prev_frame = frame.copy()
                
                if len(scene_changes) >= num_frames:
                    break
            
            frames = scene_changes[:num_frames]
            
        else:  # key_frames - start, middle, end + scene changes
            key_points = [0.1, 0.3, 0.5, 0.7, 0.9]  # Percentages through video
            for pct in key_points[:num_frames]:
                timestamp = duration * pct
                frame_num = int(timestamp * fps)
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                ret, frame = cap.read()
                if ret:
                    frames.append((frame, timestamp))
        
        cap.release()
        
        # Ensure we have at least one frame
        if not frames:
            # Fallback to first frame
            cap = cv2.VideoCapture(video_path)
            ret, frame = cap.read()
            if ret:
                frames.append((frame, 0.0))
            cap.release()
        
        self.logger.info(f"Extracted {len(frames)} key frames")
        return frames
    
    def _calculate_frame_diff(self, frame1: np.ndarray, frame2: np.ndarray) -> float:
        """Calculate difference between two frames"""
        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
        diff = cv2.absdiff(gray1, gray2)
        return float(np.mean(diff))
    
    def frames_to_temp_files(self, frames: List[Tuple[np.ndarray, float]], 
                             quality: int = 85) -> List[Tuple[str, float, str]]:
        """
        Save frames as temporary JPEG files for AI processing.
        
        Returns list of (base64_string, timestamp, temp_path) tuples.
        The temp_path should be deleted after processing.
        """
        import tempfile
        import os
        
        results = []
        for frame, timestamp in frames:
            # Encode as JPEG
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
            _, buffer = cv2.imencode('.jpg', frame, encode_params)
            
            # Convert to base64 for metadata
            base64_str = base64.b64encode(buffer).decode('utf-8')
            
            # Save to temp file - AI providers expect file paths
            temp_fd, temp_path = tempfile.mkstemp(suffix='.jpg', prefix='video_frame_')
            try:
                with os.fdopen(temp_fd, 'wb') as f:
                    f.write(buffer)
                results.append((base64_str, timestamp, temp_path))
            except Exception as e:
                os.close(temp_fd)
                self.logger.error(f"Failed to save temp file: {e}")
                # Still include result but with empty path - caller should handle
                results.append((base64_str, timestamp, None))
        
        return results
    
    def describe_video(self, video_path: str, 
                      provider: Optional[str] = None,
                      model: Optional[str] = None,
                      custom_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate AI description for a video.
        
        Args:
            video_path: Path to video file
            provider: AI provider (ollama, openai, claude)
            model: Model name
            custom_prompt: Custom prompt override
            
        Returns:
            Dictionary with description, metadata, and frame info
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")
        
        self.logger.info(f"Describing video: {video_path.name}")
        start_time = time.time()
        
        # Extract key frames
        self.logger.info("Extracting key frames...")
        frames = self.extract_key_frames(str(video_path))
        
        if not frames:
            raise Exception("Could not extract frames from video")
        
        # Extract metadata
        video_metadata = {}
        if self.video_metadata_extractor and self.video_metadata_extractor.ffprobe_available:
            try:
                video_metadata = self.video_metadata_extractor.extract_metadata(video_path) or {}
                self.logger.info(f"Extracted metadata: GPS={('gps' in video_metadata)}, Date={('datetime' in video_metadata)}")
            except Exception as e:
                self.logger.warning(f"Could not extract video metadata: {e}")
        
        # Convert frames for AI - save to temp files
        self.logger.info("Preparing frames for AI...")
        frame_data = self.frames_to_temp_files(frames)
        
        # Clean up temp files when done
        temp_files = [path for _, _, path in frame_data if path]
        
        try:
            # Get AI provider
            if not AI_PROVIDERS_AVAILABLE or not get_available_providers:
                raise Exception("AI providers not available")
            
            providers = get_available_providers()
            provider_name = provider or self.config.get("provider", "ollama")
            
            if provider_name not in providers:
                raise Exception(f"Provider '{provider_name}' not available")
            
            ai_provider = providers[provider_name]
            model_name = model or self.config.get("model", "llava")
            
            # Build prompt
            prompt_style = custom_prompt or self.config.get("custom_prompt", "")
            if not prompt_style:
                prompt_style = self._build_default_video_prompt(len(frames), video_metadata)
            
            self.logger.info(f"Sending to {provider_name}/{model_name}...")
            
            # Call AI with multiple frames
            description = self._call_vision_model(
                ai_provider, model_name, frame_data, prompt_style, video_metadata
            )
            
        finally:
            # Clean up temp files
            for temp_path in temp_files:
                try:
                    if temp_path and os.path.exists(temp_path):
                        os.remove(temp_path)
                except Exception as e:
                    self.logger.warning(f"Failed to remove temp file {temp_path}: {e}")
        
        elapsed = time.time() - start_time
        
        result = {
            "video_path": str(video_path),
            "video_name": video_path.name,
            "description": description,
            "provider": provider_name,
            "model": model_name,
            "prompt": prompt_style,
            "num_frames_used": len(frames),
            "processing_time": elapsed,
            "video_metadata": video_metadata,
            "timestamps": [ts for _, ts, _ in frame_data],
        }
        
        self.logger.info(f"Description complete in {elapsed:.1f}s")
        return result
    
    def _build_default_video_prompt(self, num_frames: int, metadata: Dict) -> str:
        """Build default prompt for video description"""
        prompt = f"Describe this video based on {num_frames} key frames. "
        prompt += "Provide a cohesive narrative describing what happens, the setting, "
        prompt += "any people or objects visible, and the overall context. "
        prompt += "Frame timestamps are provided for reference."
        
        if metadata.get('datetime'):
            prompt += f"\n\nVideo recorded: {metadata['datetime']}"
        
        if metadata.get('gps'):
            prompt += f"\nLocation: {metadata['gps']}"
        
        return prompt
    
    def _call_vision_model(self, provider, model: str, 
                           frame_data: List[Tuple[str, float, str]], 
                           prompt: str, metadata: Dict) -> str:
        """
        Call vision model with multiple frames.
        
        Falls back to processing frames individually if multi-frame not supported.
        frame_data is list of (base64_str, timestamp, temp_file_path)
        """
        # Try multi-frame if provider supports it
        if hasattr(provider, 'describe_video'):
            # Provider has native video support
            return provider.describe_video(frame_data, prompt, model)
        
        # Otherwise, process as individual images with combined prompt
        return self._process_frames_as_batch(provider, model, frame_data, prompt)
    
    def _process_frames_as_batch(self, provider, model: str,
                                  frame_data: List[Tuple[str, float, str]], 
                                  prompt: str) -> str:
        """Process frames as individual images and combine descriptions"""
        descriptions = []
        
        for i, (base64_str, timestamp, temp_path) in enumerate(frame_data):
            frame_prompt = f"Frame {i+1} of {len(frame_data)} (timestamp: {timestamp:.1f}s)\n{prompt}"
            
            try:
                # Call provider's image description with file path
                if hasattr(provider, 'describe_image') and temp_path:
                    desc = provider.describe_image(temp_path, frame_prompt, model)
                    descriptions.append(f"[Frame {i+1} at {timestamp:.1f}s]: {desc}")
                elif temp_path:
                    # Fallback - try direct API call
                    desc = self._direct_api_call(provider, temp_path, frame_prompt, model)
                    descriptions.append(f"[Frame {i+1} at {timestamp:.1f}s]: {desc}")
                else:
                    raise Exception("No temp file path available")
            except Exception as e:
                self.logger.warning(f"Failed to describe frame {i+1}: {e}")
                descriptions.append(f"[Frame {i+1}]: Error processing frame")
        
        # Combine descriptions into cohesive narrative
        if hasattr(provider, 'combine_descriptions'):
            return provider.combine_descriptions(descriptions, prompt)
        
        # Simple concatenation with summary prompt
        combined = "\n\n".join(descriptions)
        summary_prompt = f"Based on these frame descriptions, provide a cohesive video summary:\n\n{combined}"
        
        # Try to get summary from provider
        try:
            if hasattr(provider, 'generate_text'):
                return provider.generate_text(summary_prompt, model)
        except:
            pass
        
        # Fallback: return combined descriptions
        return f"Video Summary:\n\n{combined}"
    
    def _direct_api_call(self, provider, image_path: str, prompt: str, model: str) -> str:
        """Direct API call fallback for providers without describe_image method"""
        # This is a simplified fallback - real implementation would use provider's native API
        raise NotImplementedError("Direct API call not implemented - provider must have describe_image method")
    
    def batch_describe(self, video_paths: List[str], 
                       progress_callback: Optional[callable] = None) -> List[Dict]:
        """
        Describe multiple videos in batch.
        
        Args:
            video_paths: List of video file paths
            progress_callback: Optional callback(current, total, video_name)
            
        Returns:
            List of result dictionaries
        """
        self.statistics["total_videos"] = len(video_paths)
        self.statistics["start_time"] = time.time()
        
        results = []
        
        for i, video_path in enumerate(video_paths, 1):
            try:
                if progress_callback:
                    progress_callback(i, len(video_paths), Path(video_path).name)
                
                result = self.describe_video(video_path)
                results.append(result)
                self.statistics["processed"] += 1
                
            except Exception as e:
                self.logger.error(f"Failed to describe {video_path}: {e}")
                results.append({
                    "video_path": video_path,
                    "error": str(e),
                    "description": "",
                })
                self.statistics["failed"] += 1
                self.statistics["errors"].append(f"{video_path}: {e}")
        
        self.statistics["end_time"] = time.time()
        return results
    
    def save_descriptions(self, results: List[Dict], output_file: str):
        """Save video descriptions to file"""
        output_path = Path(output_file)
        
        if output_path.suffix.lower() == '.json':
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
        else:
            # Text format
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("Video Descriptions\n")
                f.write("=" * 80 + "\n\n")
                
                for result in results:
                    if "error" in result:
                        f.write(f"Video: {result['video_path']}\n")
                        f.write(f"Error: {result['error']}\n")
                    else:
                        f.write(f"Video: {result['video_name']}\n")
                        f.write(f"Provider: {result['provider']}\n")
                        f.write(f"Model: {result['model']}\n")
                        f.write(f"Frames: {result['num_frames_used']}\n")
                        f.write(f"Time: {result['processing_time']:.1f}s\n")
                        f.write(f"\nDescription:\n{result['description']}\n")
                    
                    f.write("\n" + "-" * 80 + "\n\n")
        
        self.logger.info(f"Saved descriptions to: {output_file}")


def main():
    """Command-line entry point"""
    parser = argparse.ArgumentParser(
        description="Generate AI descriptions for videos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s video.mp4
  %(prog)s video.mp4 --provider openai --model gpt-4o
  %(prog)s video.mp4 --frames 10 --prompt "Describe the action in detail"
  %(prog)s *.mp4 --output video_descriptions.txt
        """
    )
    
    parser.add_argument("videos", nargs="+", help="Video file(s) to describe")
    parser.add_argument("--provider", default="ollama",
                       help="AI provider (ollama, openai, claude)")
    parser.add_argument("--model", default="llava",
                       help="Model name")
    parser.add_argument("--prompt", help="Custom description prompt")
    parser.add_argument("--frames", type=int, default=5,
                       help="Number of frames to extract (default: 5)")
    parser.add_argument("--mode", default="key_frames",
                       choices=["key_frames", "uniform", "scene_change"],
                       help="Frame selection mode (default: key_frames)")
    parser.add_argument("--output", "-o",
                       help="Output file (.txt or .json)")
    parser.add_argument("--config", "-c",
                       help="Config file path")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Load config if provided
    config = None
    if args.config:
        with open(args.config, 'r') as f:
            config = json.load(f)
    
    # Create describer
    describer = VideoDescriber(config=config)
    
    # Override config with CLI args
    describer.config["provider"] = args.provider
    describer.config["model"] = args.model
    describer.config["num_frames"] = args.frames
    describer.config["frame_selection_mode"] = args.mode
    if args.prompt:
        describer.config["custom_prompt"] = args.prompt
    
    # Process videos
    print(f"Describing {len(args.videos)} video(s)...")
    print(f"Provider: {args.provider}, Model: {args.model}")
    print(f"Frames: {args.frames}, Mode: {args.mode}")
    print("-" * 60)
    
    def progress(current, total, name):
        print(f"[{current}/{total}] {name}...")
    
    results = describer.batch_describe(args.videos, progress_callback=progress)
    
    # Print results
    print("\n" + "=" * 60)
    for result in results:
        if "error" in result:
            print(f"\n❌ {result['video_path']}")
            print(f"   Error: {result['error']}")
        else:
            print(f"\n[SUCCESS] {result['video_name']}")
            print(f"  Time: {result['processing_time']:.1f}s")
            desc_preview = result['description'][:300] if len(result['description']) > 300 else result['description']
            print(f"  Description:\n{desc_preview}")
    
    # Save if output specified
    if args.output:
        describer.save_descriptions(results, args.output)
        print(f"\nSaved to: {args.output}")
    
    # Summary
    print(f"\n{'=' * 60}")
    print(f"Processed: {describer.statistics['processed']}")
    print(f"Failed: {describer.statistics['failed']}")
    total_time = describer.statistics['end_time'] - describer.statistics['start_time'] if describer.statistics['end_time'] else 0
    print(f"Total time: {total_time:.1f}s")


if __name__ == "__main__":
    main()
