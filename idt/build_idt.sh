#!/bin/bash
# Build IDT CLI for macOS/Linux
# Run this from the idt directory

set -e

echo "Building IDT CLI..."
echo ""

# Activate virtual environment
if [ -f "../.venv/bin/activate" ]; then
    source ../.venv/bin/activate
else
    echo "Error: Virtual environment not found at ../.venv"
    exit 1
fi

# Run PyInstaller
pyinstaller --noconfirm idt.spec

# macOS code signing fix - remove conflicting signatures and re-sign
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Fixing macOS code signatures..."
    echo "  Removing existing signatures..."
    # Remove existing signatures from shared libraries
    find dist/idt -type f \( -name "*.so" -o -name "*.dylib" \) 2>/dev/null | while read lib; do
        codesign --remove-signature "$lib" 2>/dev/null || true
    done
    # Remove signature from executable
    codesign --remove-signature dist/idt 2>/dev/null || true
    
    # Ad-hoc sign all libraries individually first
    echo "  Signing libraries..."
    find dist/idt -type f \( -name "*.so" -o -name "*.dylib" \) 2>/dev/null | while read lib; do
        codesign --force --sign - "$lib" 2>/dev/null || true
    done
    
    # Finally sign the executable
    echo "  Signing executable..."
    codesign --force --sign - dist/idt
    
    # Verify
    echo "  Verifying signature..."
    codesign --verify --verbose=2 dist/idt 2>&1 || echo "Warning: Signature verification had warnings (may still work)"
fi

echo ""
echo "========================================"
echo "Build complete!"
echo "Executable: dist/idt"
echo "========================================"
