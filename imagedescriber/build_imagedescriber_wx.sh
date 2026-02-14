#!/bin/bash
# Build ImageDescriber wxPython app

set -e  # Exit on error

echo "Building ImageDescriber (wxPython)..."

# Activate virtual environment
source .venv/bin/activate

# Run PyInstaller
pyinstaller imagedescriber_wx.spec --clean --noconfirm

# macOS code signing fix - remove conflicting signatures and re-sign
echo "Fixing macOS code signatures..."
# Remove existing signatures from Python framework
find dist/ImageDescriber.app -name "*.so" -o -name "*.dylib" | while read lib; do
    codesign --remove-signature "$lib" 2>/dev/null || true
done
# Remove signature from Python framework if present
if [ -f "dist/ImageDescriber.app/Contents/Frameworks/Python.framework/Versions/3.14/Python" ]; then
    codesign --remove-signature "dist/ImageDescriber.app/Contents/Frameworks/Python.framework/Versions/3.14/Python" 2>/dev/null || true
fi
# Ad-hoc sign the entire app bundle
codesign --force --deep --sign - dist/ImageDescriber.app

echo "========================================"
echo "Build complete!"
echo "Application: dist/ImageDescriber.app"
echo "========================================"
