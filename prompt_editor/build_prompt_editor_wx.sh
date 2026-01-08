#!/bin/bash
# Build Prompt Editor wxPython for macOS

set -e

echo "Building Prompt Editor (wxPython)..."
echo ""

# Activate virtual environment
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
else
    echo "Error: Virtual environment not found at .venv"
    exit 1
fi

# Build with PyInstaller
pyinstaller --noconfirm prompt_editor_wx.spec

echo ""
echo "========================================"
echo "Build complete!"
echo "Application: dist/PromptEditor.app"
echo "========================================"
