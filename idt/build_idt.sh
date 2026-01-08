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

echo ""
echo "========================================"
echo "Build complete!"
echo "Executable: dist/idt"
echo "========================================"
