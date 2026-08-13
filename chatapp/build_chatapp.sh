#!/bin/bash
# Build IDT Chat (macOS .app bundle)
#
# Mirrors imagedescriber/build_imagedescriber_wx.sh, including the signature
# dance below, which is not optional on modern macOS.

set -e  # Exit on error

echo "Building IDT Chat (wxPython)..."

# ----------------------------------------------------------------------------
# Virtual environment.
#
# chatapp's dependencies are a strict subset of ImageDescriber's, so rather
# than require a third environment to exist we use whichever is available:
# chatapp/.venv if someone made one, else imagedescriber/.venv, else the root
# .venv. CI creates imagedescriber/.venv already, so this needs no new step
# and no second wxPython download.
# ----------------------------------------------------------------------------
if [ -f ".venv/bin/activate" ]; then
    echo "Using chatapp/.venv"
    source .venv/bin/activate
elif [ -f "../imagedescriber/.venv/bin/activate" ]; then
    echo "Using imagedescriber/.venv (chatapp deps are a subset)"
    source ../imagedescriber/.venv/bin/activate
elif [ -f "../.venv/bin/activate" ]; then
    echo "Using root .venv"
    source ../.venv/bin/activate
else
    echo "ERROR: no virtual environment found."
    echo "Expected one of: chatapp/.venv, imagedescriber/.venv, .venv"
    exit 1
fi

# Fail early rather than after minutes of PyInstaller work.
python -c "import wx" 2>/dev/null || {
    echo "ERROR: wxPython is not installed in the active environment."
    echo "Run: pip install -r requirements.txt"
    exit 1
}
python -c "import sys; sys.path.insert(0, '..'); import idt_core.chat" 2>/dev/null || {
    echo "ERROR: idt_core.chat is not importable from the project root."
    echo "IDT Chat cannot be built without the chat engine."
    exit 1
}
echo "Chat engine found."

# Run PyInstaller
pyinstaller chatapp.spec --clean --noconfirm

APP="dist/IDTChat.app"

if [ ! -d "$APP" ]; then
    echo "ERROR: PyInstaller reported success but $APP is missing."
    exit 1
fi

# ----------------------------------------------------------------------------
# macOS code signing fix.
#
# PyInstaller copies libraries that already carry signatures from whoever
# built them -- the Python framework is signed by python.org, with a different
# TeamID. macOS refuses to load a bundle whose nested code is signed by
# someone other than the bundle signer, so every inherited signature is
# stripped and everything is re-signed ad-hoc. Release builds are then
# properly signed with the Developer ID by sign_macos.sh.
# ----------------------------------------------------------------------------
echo "Fixing macOS code signatures..."

echo "  Removing Python.framework signatures..."
find "$APP/Contents/Frameworks" -type f -name "Python" 2>/dev/null | while read -r pylib; do
    codesign --remove-signature "$pylib" 2>/dev/null || true
done

echo "  Removing signatures from libraries..."
find "$APP/Contents/Frameworks" -type f \( -name "*.so" -o -name "*.dylib" \) 2>/dev/null | while read -r lib; do
    codesign --remove-signature "$lib" 2>/dev/null || true
done

codesign --remove-signature "$APP/Contents/MacOS/IDTChat" 2>/dev/null || true
codesign --remove-signature "$APP" 2>/dev/null || true

echo "  Ad-hoc signing Python.framework..."
find "$APP/Contents/Frameworks" -type f -name "Python" 2>/dev/null | while read -r pylib; do
    codesign --force --sign - "$pylib" 2>/dev/null || true
done

echo "  Ad-hoc signing libraries..."
find "$APP/Contents/Frameworks" -type f \( -name "*.so" -o -name "*.dylib" \) 2>/dev/null | while read -r lib; do
    codesign --force --sign - "$lib" 2>/dev/null || true
done

echo "  Ad-hoc signing app bundle..."
codesign --force --deep --sign - "$APP"

echo "  ✓ App signed with ad-hoc signature (allows local development)"

echo "========================================"
echo "Build complete!"
echo "Application: $APP"
echo "========================================"
