#!/bin/bash
# Build Viewer wxPython for macOS

set -e

echo "Building Viewer (wxPython)..."
echo ""

# Activate virtual environment
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
else
    echo "Error: Virtual environment not found at .venv"
    exit 1
fi

# Build with PyInstaller
pyinstaller --noconfirm viewer_wx.spec

echo ""
echo "========================================"
echo "Build complete!"
echo "Application: dist/Viewer.app"
echo "========================================"
