#!/usr/bin/env python3
"""Quick diagnostic: Check if 841 frames is correct for the video"""

import cv2
from pathlib import Path
import sys

# Find the video file
workspace = Path("C:/idt/oct_workspace")
video_candidates = list(workspace.parent.glob("**/IMG_4276.*"))

if not video_candidates:
    # Try to infer from extracted frames directory
    print("Video file not found. Checking extracted frames directory...")
    extracted_dir = workspace / "extracted_frames" / "IMG_4276"
    if extracted_dir.exists():
        frame_count = len(list(extracted_dir.glob("*.jpg")))
        print(f"\n{'='*60}")
        print(f"Extracted frames: {frame_count}")
        print(f"\nWith 5-second interval:")
        print(f"  Expected video duration: {frame_count * 5 / 60:.1f} minutes")
        print(f"{'='*60}")
        print("\nUnable to verify - source video not found.")
        print("Is the video ~70 minutes long? If yes, extraction is CORRECT.")
        print("If video is much shorter, there's a bug.")
    sys.exit(1)

for video_path in video_candidates:
    if video_path.suffix.lower() in ['.mp4', '.mov', '.avi', '.m4v']:
        print(f"Analyzing: {video_path}\n")
        
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            print(f"Could not open {video_path}")
            continue
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_seconds = total_frames / fps if fps > 0 else 0
        duration_minutes = duration_seconds / 60
        
        cap.release()
        
        # Calculate expected frames with 5-second interval
        interval_seconds = 5.0
        expected_frames = int(duration_seconds / interval_seconds)
        
        # Count actual extracted frames
        extracted_dir = workspace / "extracted_frames" / "IMG_4276"
        actual_frames = len(list(extracted_dir.glob("*.jpg"))) if extracted_dir.exists() else 0
        
        print(f"{'='*60}")
        print(f"VIDEO PROPERTIES:")
        print(f"  FPS: {fps:.2f}")
        print(f"  Total frames in video: {total_frames}")
        print(f"  Duration: {duration_minutes:.1f} minutes ({duration_seconds:.0f} seconds)")
        print(f"\nEXTRACTION ANALYSIS (5-second interval):")
        print(f"  Expected extractions: {expected_frames}")
        print(f"  Actual extractions: {actual_frames}")
        print(f"\nRESULT:")
        
        if abs(actual_frames - expected_frames) <= 2:
            print(f"  ✓ CORRECT - Extraction working as designed")
            print(f"    ({actual_frames} frames from {duration_minutes:.1f} min video @ 5s intervals)")
        else:
            print(f"  ✗ BUG DETECTED!")
            print(f"    Expected ~{expected_frames} frames, got {actual_frames}")
            print(f"    Ratio: {actual_frames / expected_frames:.1f}x")
            
            # Calculate what interval was actually used
            if actual_frames > 0:
                actual_interval = duration_seconds / actual_frames
                print(f"    Actual interval: {actual_interval:.2f} seconds")
                
                # Calculate frame interval
                frame_interval_used = total_frames / actual_frames
                frame_interval_expected = fps * interval_seconds
                print(f"    Frame interval: {frame_interval_used:.1f} (expected {frame_interval_expected:.0f})")
        
        print(f"{'='*60}")
        break
