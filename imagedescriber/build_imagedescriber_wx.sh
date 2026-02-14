#!/bin/bash
# Build ImageDescriber wxPython app

set -e  # Exit on error

echo "Building ImageDescriber (wxPython)..."

# Activate virtual environment
source .venv/bin/activate

# Run PyInstaller
pyinstaller imagedescriber_wx.spec --clean --noconfirm

# macOS code signing fix - remove conflicting signatures
echo "Fixing macOS code signatures..."

# Critical: Find and remove signature from Python framework (has python.org TeamID)
echo "  Removing Python.framework signatures..."
find dist/ImageDescriber.app/Contents/Frameworks -type f -name "Python" 2>/dev/null | while read pylib; do
    echo "    Removing signature from: $pylib"
    codesign --remove-signature "$pylib" 2>/dev/null || true
done

# Remove signatures from all other libraries
echo "  Removing signatures from libraries..."
find dist/ImageDescriber.app/Contents/Frameworks -type f \( -name "*.so" -o -name "*.dylib" \) 2>/dev/null | while read lib; do
    codesign --remove-signature "$lib" 2>/dev/null || true
done

# Remove signature from the executable itself  
codesign --remove-signature dist/ImageDescriber.app/Contents/MacOS/ImageDescriber 2>/dev/null || true

# Remove signature from the app bundle
codesign --remove-signature dist/ImageDescriber.app 2>/dev/null || true

echo "  All signatures removed. App will run unsigned (macOS will quarantine but allow after confirmation)"

echo "========================================"
echo "Build complete!"
echo "Application: dist/ImageDescriber.app"
echo "========================================"
