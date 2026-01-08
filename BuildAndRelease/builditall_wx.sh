#!/bin/bash
# Build ALL IDT applications (macOS)
# Run from project root

set -e

echo "========================================"
echo "Building ALL IDT Applications (macOS)"
echo "========================================"
echo ""

# Get script directory (project root)
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR/.."  # Go to project root

# Activate main venv
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
else
    echo "Error: Main virtual environment not found at .venv"
    exit 1
fi

# Build IDT CLI
echo "1/5: Building IDT CLI..."
cd idt
./build_idt.sh
cd ..
echo ""

# Build Viewer
echo "2/5: Building Viewer..."
cd viewer
./build_viewer_wx.sh
cd ..
echo ""

# Build Prompt Editor
echo "3/5: Building Prompt Editor..."
cd prompt_editor
./build_prompt_editor_wx.sh
cd ..
echo ""

# Build IDTConfigure
echo "4/5: Building IDTConfigure..."
cd idtconfigure
./build_idtconfigure_wx.sh
cd ..
echo ""

# Build ImageDescriber
echo "5/5: Building ImageDescriber..."
cd imagedescriber
./build_imagedescriber_wx.sh
cd ..
echo ""

echo "========================================"
echo "ALL BUILDS COMPLETE!"
echo "========================================"
echo ""
echo "Executables:"
echo "  - idt/dist/idt"
echo "  - viewer/dist/Viewer.app"
echo "  - prompt_editor/dist/PromptEditor.app"
echo "  - idtconfigure/dist/IDTConfigure.app"
echo "  - imagedescriber/dist/ImageDescriber.app"
echo ""
echo "All apps have been successfully migrated to wxPython!"
echo "========================================"
