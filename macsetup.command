#!/bin/bash
# ============================================================================
# macOS Environment Setup for Image Description Toolkit (Finder Executable)
# ============================================================================
# Creates separate virtual environments (.venv) for each GUI app
# 
# Double-click this file in Finder to run the setup
# ============================================================================

echo ""
echo "========================================================================"
echo "macOS Environment Setup for Image Description Toolkit"
echo "========================================================================"
echo ""
echo "This will create .venv directories for each application and"
echo "install all required dependencies."
echo ""
echo "Applications to set up:"
echo "  - IDT (CLI)"
echo "  - ImageDescriber (with integrated Viewer Mode, prompt editor, and configuration manager)"
echo ""
read -p "Press Enter to continue or Ctrl+C to cancel..."

SETUP_ERRORS=0
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# ============================================================================
echo ""
echo "[1/2] Setting up Root Environment (for IDT CLI)..."
echo "========================================================================"
echo ""

cd "$SCRIPT_DIR" || exit 1

if [ -d ".venv" ]; then
    echo "Removing old .venv..."
    rm -rf .venv
fi

echo "Creating virtual environment..."
python3 -m venv .venv
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to create virtual environment in root"
    ((SETUP_ERRORS++))
else
    echo "Installing core dependencies..."
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to install root dependencies"
        ((SETUP_ERRORS++))
    else
        echo "SUCCESS: Root environment setup complete"
    fi
    deactivate
fi

# ============================================================================
echo ""
echo "[2/2] Setting up ImageDescriber..."
echo "========================================================================"
echo ""

cd "$SCRIPT_DIR/imagedescriber" || exit 1

if [ -d ".venv" ]; then
    echo "Removing old .venv..."
    rm -rf .venv
fi

echo "Creating virtual environment..."
python3 -m venv .venv
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to create virtual environment for ImageDescriber"
    ((SETUP_ERRORS++))
else
    echo "Installing dependencies..."
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to install dependencies for ImageDescriber"
        ((SETUP_ERRORS++))
    else
        echo "SUCCESS: ImageDescriber setup complete"
    fi
    deactivate
fi

# ============================================================================
echo ""
echo "========================================================================"
echo "SETUP SUMMARY"
echo "========================================================================"
echo ""

if [ $SETUP_ERRORS -eq 0 ]; then
    echo "SUCCESS: All macOS environments set up successfully!"
    echo ""
    echo "Virtual environments created:"
    echo "  - .venv (root - for IDT CLI build)"
    echo "  - imagedescriber/.venv"
    echo ""
    echo "Next steps:"
    echo "  1. Build all applications: ./BuildAndRelease/MacBuilds/builditall_macos.command"
    echo "  2. Test executable: open imagedescriber/dist/ImageDescriber.app"
    echo ""
else
    echo "ERRORS: $SETUP_ERRORS setup failures encountered"
    echo "Please review the errors above and try again."
    echo ""
fi

echo "NOTE: These .venv directories are for macOS only."
echo "Windows uses .winenv directories which can coexist in the same project."
echo ""

read -p "Press Enter to close..."
exit $SETUP_ERRORS
