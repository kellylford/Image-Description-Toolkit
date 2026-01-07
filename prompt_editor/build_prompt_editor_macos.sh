#!/bin/bash
# ============================================================================
# Build Image Description Prompt Editor for macOS
# ============================================================================
# Creates prompteditor.app in dist/
# ============================================================================

set -e  # Exit on error
set -u  # Exit on undefined variable

# Change to script's directory first
cd "$(dirname "$0")"

echo "========================================================================"
echo "Building Image Description Prompt Editor for macOS"
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
    echo "Installing prompt editor dependencies..."
    pip install -q -r requirements.txt
    echo ""
fi

# Create output directory
mkdir -p dist

# Get absolute path to scripts directory (one level up)
SCRIPTS_DIR="$(cd .. && pwd)/scripts"

# Check if scripts directory exists
if [ ! -d "$SCRIPTS_DIR" ]; then
    echo "WARNING: Scripts directory not found at: $SCRIPTS_DIR"
    echo ""
    echo "The prompt editor needs scripts/image_describer_config.json to function."
    echo "Build cannot continue without scripts directory."
    echo ""
    exit 1
fi

echo "Scripts directory found: $SCRIPTS_DIR"
echo "Building prompt editor WITH scripts bundled..."
echo ""

# Build the executable using macOS-specific spec file
pyinstaller prompteditor_macos.spec

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================================================"
    echo "BUILD SUCCESSFUL"
    echo "========================================================================"
    echo "Application created: dist/prompteditor.app"
    echo ""
    echo "To test: open dist/prompteditor.app"
    echo ""
else
    echo ""
    echo "========================================================================"
    echo "BUILD FAILED"
    echo "========================================================================"
    exit 1
fi
