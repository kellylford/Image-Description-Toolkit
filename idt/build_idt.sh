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
    # Remove existing signatures from shared libraries
    find dist/idt -type f \( -name "*.so" -o -name "*.dylib" \) 2>/dev/null | while read lib; do
        codesign --remove-signature "$lib" 2>/dev/null || true
    done
    # Ad-hoc sign the executable
    codesign --force --deep --sign - dist/idt 2>/dev/null || true
fi

echo ""
echo "========================================"
echo "Build complete!"
echo "Executable: dist/idt"
echo "========================================"
