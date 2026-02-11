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

# Check log file
from pathlib import Path
log_path = Path.home() / 'imagedescriber_geocoding_debug.log'
if log_path.exists():
    print(f"\n📋 Log file exists: {log_path}")
    print(f"   Size: {log_path.stat().st_size:,} bytes")
    print("\nLast 50 lines of log:")
    print("-" * 60)
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
        for line in lines[-50:]:
            print(line.rstrip())
else:
    print(f"\n📋 Log file not found: {log_path}")
