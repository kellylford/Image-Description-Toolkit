#!/bin/bash
# Build ImageDescriber wxPython app

set -e  # Exit on error

echo "Building ImageDescriber (wxPython)..."

# ----------------------------------------------------------------------------
# Virtual environment.
#
# Checked explicitly rather than relying on "source .venv/bin/activate" to fail
# under set -e: that produced a bare "No such file or directory" with no hint
# that macsetup.sh is what creates this. Mirrors the handling in
# chatapp/build_chatapp.sh, which fell back and reported properly while this
# script did not.
# ----------------------------------------------------------------------------
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif [ -f "../.venv/bin/activate" ]; then
    echo "imagedescriber/.venv not found; using root .venv"
    source ../.venv/bin/activate
else
    echo "ERROR: no virtual environment found."
    echo "Expected imagedescriber/.venv (or root .venv)."
    echo "Run ./macsetup.sh from the project root first."
    exit 1
fi

# Fail early rather than after minutes of PyInstaller work. wxPython is the
# dependency that actually goes missing, and without this check the resulting
# failure points at the spec file instead of at the environment.
python -c "import wx" 2>/dev/null || {
    echo "ERROR: wxPython is not installed in the active environment."
    echo "Run: pip install -r requirements.txt"
    exit 1
}

# Run PyInstaller
pyinstaller imagedescriber_wx.spec --clean --noconfirm

# macOS code signing fix - remove conflicting signatures and re-sign
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

# Now ad-hoc sign everything (required on modern macOS)
echo "  Ad-hoc signing Python.framework..."
find dist/ImageDescriber.app/Contents/Frameworks -type f -name "Python" 2>/dev/null | while read pylib; do
    codesign --force --sign - "$pylib" 2>/dev/null || true
done

echo "  Ad-hoc signing libraries..."
find dist/ImageDescriber.app/Contents/Frameworks -type f \( -name "*.so" -o -name "*.dylib" \) 2>/dev/null | while read lib; do
    codesign --force --sign - "$lib" 2>/dev/null || true
done

echo "  Ad-hoc signing app bundle..."
codesign --force --deep --sign - dist/ImageDescriber.app

echo "  ✓ App signed with ad-hoc signature (allows local development)"

echo "========================================"
echo "Build complete!"
echo "Application: dist/ImageDescriber.app"
echo "========================================"
