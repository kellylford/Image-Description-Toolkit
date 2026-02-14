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

# macOS code signing fix - remove conflicting signatures and re-sign
echo "Fixing macOS code signatures..."
# Remove existing signatures from Python framework
find dist/Viewer.app -name "*.so" -o -name "*.dylib" | while read lib; do
    codesign --remove-signature "$lib" 2>/dev/null || true
done
# Remove signature from Python framework if present
if [ -f "dist/Viewer.app/Contents/Frameworks/Python.framework/Versions/3.14/Python" ]; then
    codesign --remove-signature "dist/Viewer.app/Contents/Frameworks/Python.framework/Versions/3.14/Python" 2>/dev/null || true
fi
# Ad-hoc sign the entire app bundle
codesign --force --deep --sign - dist/Viewer.app

echo ""
echo "========================================"
echo "Build complete!"
echo "Application: dist/Viewer.app"
echo "========================================
