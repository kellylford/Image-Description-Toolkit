#!/bin/bash
# ============================================================================
# Build Image Description Viewer for macOS
# ============================================================================
# Creates viewer.app in dist/
# ============================================================================

set -e  # Exit on error
set -u  # Exit on undefined variable

# Change to script's directory first
cd "$(dirname "$0")"

echo "========================================================================"
echo "Building Image Description Viewer for macOS"
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
    echo "Installing viewer dependencies..."
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
    echo "The redescribe feature will not work in the bundled executable."
    echo "However, the viewer will still work for viewing HTML/Live modes."
    echo ""
    echo "Continuing to build viewer WITHOUT scripts bundled..."
    echo ""
    
    pyinstaller --onefile \
        --windowed \
        --name "viewer" \
        --distpath "dist" \
        --workpath "build" \
        --specpath "build" \
        --hidden-import PyQt6.QtCore \
        --hidden-import PyQt6.QtGui \
        --hidden-import PyQt6.QtWidgets \
        viewer.py
else
    echo "Scripts directory found: $SCRIPTS_DIR"
    echo "Building viewer WITH scripts bundled (redescribe feature enabled)..."
    echo ""
    
    # Use macOS-specific spec file with .app bundle
    pyinstaller viewer_macos.spec
fi

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================================================"
    echo "BUILD SUCCESSFUL"
    echo "========================================================================"
    echo "Application created: dist/viewer.app"
    echo ""
    echo "To test: open dist/viewer.app"
    echo ""
else
    echo ""
    echo "========================================================================"
    echo "BUILD FAILED"
    echo "========================================================================"
    exit 1
fi
