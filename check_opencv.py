#!/usr/bin/env python3
"""Quick check if OpenCV is available"""

import sys

print("Checking OpenCV availability...")
print(f"Python: {sys.version}")
print()

try:
    import cv2
    print("✓ OpenCV (cv2) is INSTALLED")
    print(f"  Version: {cv2.__version__}")
except ImportError as e:
    print("✗ OpenCV (cv2) is NOT INSTALLED")
    print(f"  Error: {e}")
    print()
    print("To install OpenCV, run:")
    print("  pip install opencv-python")
    sys.exit(1)

# Check log files
from pathlib import Path

log_files = [
    Path.home() / 'imagedescriber_verbose_debug.log',  # Created with --debug flag
    Path.home() / 'imagedescriber_crash.log',  # Created on worker thread crash
]

found_logs = False
for log_path in log_files:
    if log_path.exists():
        found_logs = True
        print(f"\n📋 Log file exists: {log_path}")
        print(f"   Size: {log_path.stat().st_size:,} bytes")
        print(f"\nLast 50 lines of {log_path.name}:")
        print("-" * 60)
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            for line in lines[-50:]:
                print(line.rstrip())
        print()

if not found_logs:
    print(f"\n📋 No log files found. Run ImageDescriber with --debug flag to enable logging.")

