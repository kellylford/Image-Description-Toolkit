#!/bin/bash
# Build ImageDescriber wxPython app

set -e  # Exit on error

echo "Building ImageDescriber (wxPython)..."

# Activate virtual environment
source .venv/bin/activate

# Run PyInstaller
pyinstaller imagedescriber_wx.spec --clean --noconfirm

echo "========================================"
echo "Build complete!"
echo "Application: dist/ImageDescriber.app"
echo "========================================"
