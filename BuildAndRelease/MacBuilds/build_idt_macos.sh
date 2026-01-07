#!/bin/bash
# ============================================================================
# Build IDT (main toolkit) for macOS
# ============================================================================
# Creates standalone CLI binary in dist/idt
# ============================================================================

set -e  # Exit on error
set -u  # Exit on undefined variable

echo "========================================================================"
echo "Building IDT (main toolkit) for macOS"
echo "========================================================================"
echo ""

# Change to project root (now two levels up since we're in MacBuilds/)
cd "$(dirname "$0")/../.."

# Check if virtual environment exists, create if needed
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Ensure PyInstaller is installed
if ! python -c "import PyInstaller" 2>/dev/null; then
    echo "PyInstaller not found. Installing..."
    pip install -q pyinstaller
    echo ""
fi

# Clean previous builds
echo "Cleaning previous build artifacts..."
rm -rf build dist
echo ""

# Build using PyInstaller spec file
echo "Building with PyInstaller..."
echo ""

pyinstaller BuildAndRelease/MacBuilds/final_working_macos.spec

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================================================"
    echo "BUILD SUCCESSFUL"
    echo "========================================================================"
    echo "Executable created: dist/idt"
    echo ""
    echo "To test: dist/idt version"
    echo ""
else
    echo ""
    echo "========================================================================"
    echo "BUILD FAILED"
    echo "========================================================================"
    exit 1
fi
