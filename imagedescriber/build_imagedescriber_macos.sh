#!/bin/bash
# ============================================================================
# Build ImageDescriber GUI Application for macOS
# ============================================================================
# Creates imagedescriber.app in dist/
# ============================================================================

set -e  # Exit on error
set -u  # Exit on undefined variable

# Change to script's directory first
cd "$(dirname "$0")"

echo "========================================================================"
echo "Building ImageDescriber GUI Application for macOS"
echo "========================================================================"
echo ""

# Check if virtual environment exists, create if not
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    echo ""
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate
echo ""

# Clean PyInstaller cache for fresh build
echo "Cleaning PyInstaller cache..."
python -c "import shutil; from pathlib import Path; cache_dir = Path.home() / 'Library' / 'Caches' / 'pyinstaller'; shutil.rmtree(cache_dir, ignore_errors=True); print(f'Cleaned: {cache_dir}')"
echo ""

# Clean previous build artifacts
echo "Cleaning previous build artifacts..."
rm -rf dist build
echo ""

# Check if PyInstaller is installed
if ! python -c "import PyInstaller" 2>/dev/null; then
    echo "Installing ImageDescriber dependencies..."
    pip install -q -r requirements.txt pyinstaller
    echo ""
fi

# Create output directory
mkdir -p dist

# Get absolute paths
SCRIPTS_DIR="$(cd .. && pwd)/scripts"
MODELS_DIR="$(cd .. && pwd)/models"

# Check if scripts directory exists
if [ ! -d "$SCRIPTS_DIR" ]; then
    echo "ERROR: Scripts directory not found at: $SCRIPTS_DIR"
    echo "ImageDescriber requires the scripts directory."
    exit 1
fi

echo "Scripts directory found: $SCRIPTS_DIR"
echo "Models directory: $MODELS_DIR"
echo ""
echo "Building ImageDescriber with all dependencies..."
echo ""

# Build the executable using macOS-specific spec file
pyinstaller imagedescriber_macos.spec

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================================================"
    echo "BUILD SUCCESSFUL"
    echo "========================================================================"
    echo "Application created: dist/imagedescriber.app"
    echo ""
    echo "To test: open dist/imagedescriber.app"
    echo ""
else
    echo ""
    echo "========================================================================"
    echo "BUILD FAILED"
    echo "========================================================================"
    exit 1
fi
