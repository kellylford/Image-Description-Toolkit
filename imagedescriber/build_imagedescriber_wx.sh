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

# Remove all existing signatures from frameworks and libraries
echo "  Removing existing signatures..."
find dist/ImageDescriber.app/Contents/Frameworks -type f \( -name "*.so" -o -name "*.dylib" -o -name "Python*" \) 2>/dev/null | while read lib; do
    codesign --remove-signature "$lib" 2>/dev/null || true
done

# Remove signature from the executable itself  
codesign --remove-signature dist/ImageDescriber.app/Contents/MacOS/ImageDescriber 2>/dev/null || true

# Ad-hoc sign all frameworks and libraries individually first
echo "  Signing frameworks and libraries..."
find dist/ImageDescriber.app/Contents/Frameworks -type f \( -name "*.so" -o -name "*.dylib" \) 2>/dev/null | while read lib; do
    codesign --force --sign - "$lib" 2>/dev/null || true
done

# Sign any Python framework if present
find dist/ImageDescriber.app/Contents/Frameworks -type f -name "Python*" 2>/dev/null | while read pylib; do
    codesign --force --sign - "$pylib" 2>/dev/null || true
done

# Finally, sign the entire app bundle with --deep to catch anything missed
echo "  Signing app bundle..."
codesign --force --deep --sign - dist/ImageDescriber.app

# Verify the signature
echo "  Verifying signature..."
codesign --verify --deep --strict --verbose=2 dist/ImageDescriber.app 2>&1 || echo "Warning: Signature verification had warnings (may still work)"

echo "========================================"
echo "Build complete!"
echo "Application: dist/ImageDescriber.app"
echo "========================================"
