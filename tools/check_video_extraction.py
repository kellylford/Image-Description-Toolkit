#!/usr/bin/env python3
"""Diagnostic script to check video extraction settings"""

import cv2
from pathlib import Path

# Find the video in oct_workspace
workspace = Path("C:/idt/oct_workspace")
extracted_frames = workspace / "extracted_frames" / "IMG_4276"

# Count extracted frames
frame_count = len(list(extracted_frames.glob("*.jpg")))
print(f"Extracted frames: {frame_count}")

# Try to find the source video
video_candidates = list(workspace.parent.glob("**/IMG_4276.*"))
print(f"\nSearching for source video...")
print(f"Candidates found: {len(video_candidates)}")

for video_path in video_candidates:
    print(f"\nChecking: {video_path}")
    cap = cv2.VideoCapture(str(video_path))
    
    if cap.isOpened():
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        
        print(f"  FPS: {fps}")
        print(f"  Total frames: {total_frames}")
        print(f"  Duration: {duration:.2f} seconds")
        
        # Calculate what we SHOULD have extracted
        interval_seconds = 5.0
        expected_frames = int(duration / interval_seconds)
        
        print(f"\n  With 5-second interval:")
        print(f"    Expected frames: {expected_frames}")
        print(f"    Actual frames: {frame_count}")
        print(f"    Ratio: {frame_count / expected_frames:.1f}x too many") if frame_count > expected_frames else None
        
        # Calculate what interval was ACTUALLY used
        if frame_count > 0:
            actual_interval = duration / frame_count
            print(f"    Actual interval used: {actual_interval:.3f} seconds")
            
            # Calculate frame interval in frames
            actual_frame_interval = total_frames / frame_count
            print(f"    Actual frame interval: {actual_frame_interval:.1f} frames")
        
        cap.release()
        break
else:
    print("\nNo video file found. Please check the source directory.")
