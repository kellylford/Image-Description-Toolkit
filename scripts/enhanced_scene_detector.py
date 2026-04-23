#!/usr/bin/env python3
"""
Enhanced Scene Detection Module

Improves upon basic frame differencing with:
- Adaptive thresholding based on video content
- Motion analysis to distinguish camera movement from scene changes  
- Visual quality scoring (sharpness/blur detection)
- Smart temporal sampling with min/max frame guarantees
- Multi-pass analysis for better accuracy

Goals:
1. Extract meaningful frames that represent video content
2. Handle diverse video types (static, motion-heavy, interview-style, etc.)
3. Provide good coverage without excessive frames
4. Become the default extraction method
"""

import cv2
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
from collections import deque
import logging

logger = logging.getLogger(__name__)


@dataclass
class FrameInfo:
    """Information about a candidate frame"""
    frame_num: int
    timestamp: float
    change_score: float  # How different from previous frame (0-100)
    quality_score: float  # Sharpness/blur score (0-100)
    motion_type: str  # 'static', 'camera_pan', 'scene_change'
    is_keyframe: bool = False
    importance_score: float = 0.0  # Composite score used during frame reduction


class EnhancedSceneDetector:
    """
    Advanced scene detection for video frame extraction.
    
    Features:
    - Adaptive thresholding based on video statistics
    - Motion analysis to detect camera movement vs scene changes
    - Quality-based frame selection
    - Guaranteed minimum/maximum frame counts
    - Multi-pass analysis for robustness
    """
    
    def __init__(self, 
                 min_frames: int = 5,
                 max_frames: int = 50,
                 target_frames: int = 15,
                 min_scene_duration: float = 1.0,
                 adaptive_threshold: bool = True):
        """
        Initialize scene detector.
        
        Args:
            min_frames: Absolute minimum frames to extract (prevents empty results)
            max_frames: Absolute maximum frames to extract (prevents overload)
            target_frames: Ideal number of frames to aim for
            min_scene_duration: Minimum seconds between extracted frames
            adaptive_threshold: Whether to auto-tune threshold based on video content
        """
        self.min_frames = min_frames
        self.max_frames = max_frames
        self.target_frames = target_frames
        self.min_scene_duration = min_scene_duration
        self.adaptive_threshold = adaptive_threshold
        
        # Analysis parameters
        self.blur_threshold = 100  # Laplacian variance below this is considered blurry
        self.motion_window = 5  # Frames to analyze for motion patterns
        
    def detect_scenes(self, video_path: str, progress_callback=None) -> List[FrameInfo]:
        """
        Detect scenes in video and return list of FrameInfo objects.
        
        This is a two-pass process:
        1. First pass: Analyze video characteristics and collect candidate frames
        2. Second pass: Select final frames based on coverage and quality
        
        Args:
            video_path: Path to video file
            progress_callback: Optional callback(current, total, message)
            
        Returns:
            List of FrameInfo for frames to extract
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")
        
        reported_fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Determine real duration using AVI-ratio seeking — works on MPEG/AVI
        # containers that report fps=0 where total_frames/fps would be wrong.
        real_duration = self._get_real_duration(cap)
        
        # Estimate fps from real duration when the container doesn't report it.
        if reported_fps > 0:
            fps = reported_fps
        elif real_duration > 0 and total_frames > 0:
            fps = total_frames / real_duration
            logger.warning(
                f"Video reported fps=0; estimated {fps:.2f} fps from "
                f"real duration ({real_duration:.1f}s, {total_frames} frames)"
            )
        else:
            fps = 25.0  # last resort — container provides no timing info at all
            logger.warning("Cannot determine fps or duration; using 25.0 fps last-resort fallback")
        
        if real_duration <= 0:
            real_duration = total_frames / fps if fps > 0 else 0
        
        logger.info(f"Analyzing video: {real_duration:.1f}s, {total_frames} frames, {fps:.2f} fps")
        
        # Phase 1: Collect candidate frames with change detection.
        # Timestamps come from CAP_PROP_POS_MSEC after each read — these are
        # always in real wall-clock seconds regardless of the reported fps value.
        candidates = self._collect_candidates(cap, fps, total_frames, real_duration, progress_callback)
        
        cap.release()
        
        if not candidates:
            logger.warning("No candidate frames found, falling back to uniform sampling")
            return self._fallback_uniform_sampling(video_path, fps, total_frames)
        
        # Phase 2: Select final frames from candidates
        selected = self._select_final_frames(candidates, real_duration)
        
        logger.info(f"Selected {len(selected)} frames from {len(candidates)} candidates")
        return selected
    
    def _get_real_duration(self, cap) -> float:
        """Determine real video duration in seconds.
        
        Uses CAP_PROP_POS_AVI_RATIO to jump to the end and read the actual
        position — this works for MPEG, AVI, and most containers even when
        CAP_PROP_FPS reports 0.  Restores the original position before returning.
        """
        saved_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
        try:
            cap.set(cv2.CAP_PROP_POS_AVI_RATIO, 1.0)
            end_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
            if end_ms > 0:
                return end_ms / 1000.0
        except Exception:
            pass
        finally:
            cap.set(cv2.CAP_PROP_POS_MSEC, saved_ms)
        return 0.0
    
    def _collect_candidates(self, cap, fps: float, total_frames: int,
                            real_duration: float,
                           progress_callback=None) -> List[FrameInfo]:
        """
        First pass: Collect all potential scene change frames.
        
        Analyzes frame differences, motion patterns, and quality.
        Timestamps come from CAP_PROP_POS_MSEC (real wall-clock time) so
        they are correct even for containers that report fps=0 (MPEG/MPG).
        Frame sampling is based on elapsed real time, not frame count, so
        the check interval stays ~0.5 s regardless of reported fps.
        """
        candidates = []
        prev_gray = None
        
        # Motion history for detecting camera pans
        motion_history = deque(maxlen=self.motion_window)
        
        # Statistics for adaptive thresholding
        change_scores = []
        
        frame_num = 0
        # Sample every 0.5 real seconds — avoids analyzing 30× too many frames
        # when fps=1.0 fallback is active for a real 30fps container.
        check_interval_seconds = 0.5
        last_check_time = -check_interval_seconds  # ensure first frame is always checked
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Real timestamp from the container — correct for MPEG and all others.
            current_time = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
            
            # Only analyse every check_interval_seconds of real video time
            if current_time - last_check_time >= check_interval_seconds:
                last_check_time = current_time
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                if prev_gray is not None:
                    # Calculate frame difference
                    diff = cv2.absdiff(gray, prev_gray)
                    change_pixels = np.sum(diff > 30)
                    change_score = (change_pixels / diff.size) * 100
                    
                    # Calculate quality (sharpness)
                    quality_score = self._calculate_quality(gray)
                    
                    # Analyze motion type
                    motion_type = self._analyze_motion(diff, motion_history)
                    
                    # Store candidate — timestamp is always in real seconds
                    info = FrameInfo(
                        frame_num=frame_num,
                        timestamp=current_time,
                        change_score=change_score,
                        quality_score=quality_score,
                        motion_type=motion_type
                    )
                    candidates.append(info)
                    change_scores.append(change_score)
                    
                    # Update motion history
                    motion_history.append((frame_num, change_score))
                
                prev_gray = gray
            
            frame_num += 1
            
            # Progress update (based on real time when duration is known)
            if progress_callback and frame_num % 30 == 0:
                if real_duration > 0:
                    progress = min(100, (current_time / real_duration) * 100)
                elif total_frames > 0:
                    progress = (frame_num / total_frames) * 100
                else:
                    progress = 0
                progress_callback(frame_num, total_frames,
                                f"Analyzing: {progress:.0f}% ({len(candidates)} candidates)")
        
        # Calculate adaptive threshold if enabled
        if self.adaptive_threshold and change_scores:
            self._calculate_adaptive_threshold(change_scores)
        
        return candidates
    
    def _calculate_quality(self, gray_frame) -> float:
        """
        Calculate image quality score based on sharpness.
        
        Uses Laplacian variance to detect blur.
        Returns score 0-100 where higher is sharper.
        """
        # Laplacian for edge detection
        laplacian = cv2.Laplacian(gray_frame, cv2.CV_64F)
        variance = laplacian.var()
        
        # Normalize to 0-100 scale
        # Values below blur_threshold are considered blurry
        score = min(100, (variance / self.blur_threshold) * 50)
        return score
    
    def _analyze_motion(self, diff: np.ndarray, motion_history: deque) -> str:
        """
        Analyze motion type to distinguish camera movement from scene changes.
        
        Returns: 'static', 'camera_pan', or 'scene_change'
        """
        if len(motion_history) < 3:
            return 'static'
        
        # Calculate motion direction/flow
        # Simple heuristic: uniform motion = camera pan, chaotic = scene change
        recent_changes = [score for _, score in motion_history]
        
        # If changes are consistently high across multiple frames, likely camera pan
        avg_change = np.mean(recent_changes)
        std_change = np.std(recent_changes)
        
        if avg_change < 10:
            return 'static'
        elif std_change < 5 and avg_change > 20:
            return 'camera_pan'
        else:
            return 'scene_change'
    
    def _calculate_adaptive_threshold(self, change_scores: List[float]):
        """
        Calculate adaptive threshold based on video statistics.
        
        This prevents over-extraction from videos with lots of motion
        or under-extraction from slow-changing videos.
        """
        if not change_scores:
            return
        
        mean_change = np.mean(change_scores)
        std_change = np.std(change_scores)
        median_change = np.median(change_scores)
        
        # Set threshold based on video characteristics
        # Higher motion videos need higher threshold
        if mean_change > 30:  # High motion video
            self.adaptive_threshold_value = median_change + std_change * 0.5
        elif mean_change < 10:  # Low motion video
            self.adaptive_threshold_value = median_change * 0.5
        else:
            self.adaptive_threshold_value = median_change + std_change * 0.3
        
        # Clamp to reasonable range
        self.adaptive_threshold_value = max(5, min(50, self.adaptive_threshold_value))
        
        logger.info(f"Adaptive threshold set to {self.adaptive_threshold_value:.1f}% "
                   f"(mean={mean_change:.1f}, std={std_change:.1f}, median={median_change:.1f})")
    
    def _select_final_frames(self, candidates: List[FrameInfo], 
                            duration: float) -> List[FrameInfo]:
        """
        Second pass: Select final frames from candidates.
        
        Strategy:
        1. Always include first and last frame
        2. Select scene changes above threshold
        3. Ensure minimum coverage with uniform sampling if needed
        4. Prioritize quality when choosing between similar timestamps
        5. Enforce min_scene_duration between frames
        """
        if not candidates:
            return []
        
        # Get threshold (adaptive or default)
        threshold = getattr(self, 'adaptive_threshold_value', 15)
        
        # Filter to actual scene changes
        keyframes = [c for c in candidates 
                    if c.change_score > threshold and c.motion_type == 'scene_change']
        
        # Always include first and last
        first = candidates[0]
        last = candidates[-1]
        
        selected = [first]
        last_selected_time = first.timestamp
        
        # Add keyframes that meet duration requirements
        for frame in keyframes[1:]:  # Skip first (already added)
            if frame.frame_num == last.frame_num:
                continue  # Skip last (will add at end)
            
            # Check minimum duration
            if frame.timestamp - last_selected_time >= self.min_scene_duration:
                selected.append(frame)
                last_selected_time = frame.timestamp
        
        # Add last frame if not already included
        if last.timestamp - last_selected_time >= self.min_scene_duration:
            selected.append(last)
        
        # PHASE 2: Check coverage and fill gaps if needed
        selected = self._ensure_coverage(selected, candidates, duration)
        
        # PHASE 3: Quality optimization
        selected = self._optimize_quality(selected)
        
        return selected
    
    def _ensure_coverage(self, selected: List[FrameInfo], 
                        candidates: List[FrameInfo], 
                        duration: float) -> List[FrameInfo]:
        """
        Ensure we have enough frames to represent the video.
        
        If scene detection was too sparse, add uniform samples.
        """
        if len(selected) >= self.min_frames:
            return selected
        
        logger.info(f"Only {len(selected)} scenes detected, adding uniform samples")
        
        # Calculate how many more frames we need
        needed = self.min_frames - len(selected)
        
        # Find gaps in coverage
        gaps = []
        for i in range(len(selected) - 1):
            gap_duration = selected[i + 1].timestamp - selected[i].timestamp
            if gap_duration > self.min_scene_duration * 3:  # Large gap
                gaps.append((i, gap_duration))
        
        # Fill largest gaps first
        gaps.sort(key=lambda x: x[1], reverse=True)
        
        for gap_idx, gap_duration in gaps[:needed]:
            # Find middle of gap
            mid_time = (selected[gap_idx].timestamp + selected[gap_idx + 1].timestamp) / 2
            
            # Find best quality frame near this time
            best_frame = None
            best_quality = 0
            for c in candidates:
                if abs(c.timestamp - mid_time) < gap_duration / 3:
                    if c.quality_score > best_quality:
                        best_quality = c.quality_score
                        best_frame = c
            
            if best_frame:
                selected.insert(gap_idx + 1, best_frame)
        
        # If still not enough, add uniform frames
        while len(selected) < self.min_frames:
            # Add frame at 1/N intervals
            n = len(selected) + 1
            target_time = duration * (len(selected) / n)
            
            # Find nearest candidate
            best = min(candidates, key=lambda c: abs(c.timestamp - target_time))
            
            # Check not too close to existing
            can_add = True
            for s in selected:
                if abs(s.timestamp - best.timestamp) < self.min_scene_duration:
                    can_add = False
                    break
            
            if can_add:
                selected.append(best)
            else:
                break  # Can't add more without violating duration
        
        # Re-sort by timestamp
        selected.sort(key=lambda x: x.timestamp)
        
        return selected
    
    def _optimize_quality(self, selected: List[FrameInfo]) -> List[FrameInfo]:
        """
        Final optimization: when multiple frames are close together,
        prefer the sharpest one.
        
        Also ensure we don't exceed max_frames.
        """
        if len(selected) <= self.target_frames:
            return selected
        
        # If we have too many, need to reduce
        if len(selected) > self.max_frames:
            logger.info(f"Reducing {len(selected)} frames to {self.max_frames}")
            
            # Score each frame by importance
            for frame in selected:
                # Combine change score and quality
                frame.importance_score = (frame.change_score * 0.6 + 
                                         frame.quality_score * 0.4)
            
            # Sort by importance and take top max_frames
            selected.sort(key=lambda x: x.importance_score, reverse=True)
            selected = selected[:self.max_frames]
            
            # Re-sort by timestamp
            selected.sort(key=lambda x: x.timestamp)
        
        return selected
    
    def _fallback_uniform_sampling(self, video_path: str, fps: float, 
                                   total_frames: int) -> List[FrameInfo]:
        """
        Fallback when scene detection fails: uniform time sampling.
        
        Gets real duration from the container so that timestamps are seekable
        even when the container reports fps=0 (MPEG/MPG files).
        """
        # Get real duration so timestamps stay within the actual video length
        cap = cv2.VideoCapture(video_path)
        if cap.isOpened():
            real_duration = self._get_real_duration(cap)
            cap.release()
        else:
            real_duration = 0.0

        if real_duration <= 0:
            # Last resort: compute from fps (may be wrong for MPEG)
            if fps <= 0:
                fps = 25.0
            real_duration = total_frames / fps

        if fps <= 0:
            fps = total_frames / real_duration if real_duration > 0 else 25.0

        interval = real_duration / (self.target_frames + 1)
        
        frames = []
        for i in range(1, self.target_frames + 1):
            timestamp = i * interval
            frame_num = int(timestamp * fps)
            
            frames.append(FrameInfo(
                frame_num=frame_num,
                timestamp=timestamp,
                change_score=0,
                quality_score=50,  # Neutral quality
                motion_type='static',
                is_keyframe=False
            ))
        
        return frames


# Convenience function for direct use
def detect_scenes(video_path: str, **kwargs) -> List[Tuple[int, float]]:
    """
    Simple interface to detect scenes in a video.
    
    Returns list of (frame_num, timestamp) tuples.
    """
    detector = EnhancedSceneDetector(**kwargs)
    frames = detector.detect_scenes(video_path)
    return [(f.frame_num, f.timestamp) for f in frames]


if __name__ == "__main__":
    # Test on a video
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python enhanced_scene_detector.py <video_path>")
        sys.exit(1)
    
    video_path = sys.argv[1]
    
    detector = EnhancedSceneDetector(
        min_frames=5,
        max_frames=30,
        target_frames=15
    )
    
    def progress(current, total, msg):
        print(f"\r{msg}", end='', flush=True)
    
    frames = detector.detect_scenes(video_path, progress)
    print(f"\n\nDetected {len(frames)} scenes:")
    for f in frames:
        print(f"  Frame {f.frame_num} @ {f.timestamp:.2f}s "
              f"(change={f.change_score:.1f}%, quality={f.quality_score:.1f}, "
              f"type={f.motion_type})")
