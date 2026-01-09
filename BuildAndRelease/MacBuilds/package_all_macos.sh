#!/bin/bash
# ============================================================================
# Package All Applications for macOS
# ============================================================================
# Collects all built .app bundles into BuildAndRelease/MacBuilds/dist_all directory
# Prerequisites: Run builditall_wx.sh first
# ============================================================================

set -e

echo "========================================"
echo "PACKAGE ALL APPLICATIONS (macOS)"
echo "========================================"
echo ""

# Get script directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Create output directory
mkdir -p "dist_all"
mkdir -p "dist_all/Applications"

# Clean old files
echo "Cleaning old package..."
rm -rf dist_all/Applications/*.app
rm -f dist_all/*.md dist_all/*.txt dist_all/idt

# Copy IDT CLI
echo "Copying IDT CLI..."
if [ -f "../../idt/dist/idt" ]; then
    cp "../../idt/dist/idt" "dist_all/"
    chmod +x "dist_all/idt"
    echo "  ✓ idt"
else
    echo "  ✗ idt NOT FOUND"
fi

# Copy Viewer.app
echo "Copying Viewer..."
if [ -d "../../viewer/dist/Viewer.app" ]; then
    cp -R "../../viewer/dist/Viewer.app" "dist_all/Applications/"
    echo "  ✓ Viewer.app"
else
    echo "  ✗ Viewer.app NOT FOUND"
fi

# Copy PromptEditor.app
echo "Copying Prompt Editor..."
if [ -d "../../prompt_editor/dist/PromptEditor.app" ]; then
    cp -R "../../prompt_editor/dist/PromptEditor.app" "dist_all/Applications/"
    echo "  ✓ PromptEditor.app"
else
    echo "  ✗ PromptEditor.app NOT FOUND"
fi

# Copy ImageDescriber.app
echo "Copying ImageDescriber..."
if [ -d "../../imagedescriber/dist/ImageDescriber.app" ]; then
    cp -R "../../imagedescriber/dist/ImageDescriber.app" "dist_all/Applications/"
    echo "  ✓ ImageDescriber.app"
else
    echo "  ✗ ImageDescriber.app NOT FOUND"
fi

# Copy IDTConfigure.app
echo "Copying IDTConfigure..."
if [ -d "../../idtconfigure/dist/IDTConfigure.app" ]; then
    cp -R "../../idtconfigure/dist/IDTConfigure.app" "dist_all/Applications/"
    echo "  ✓ IDTConfigure.app"
else
    echo "  ✗ IDTConfigure.app NOT FOUND"
fi

# Copy documentation
echo ""
echo "Copying documentation..."
if [ -f "../../README.md" ]; then cp "../../README.md" "dist_all/"; fi
if [ -f "../../LICENSE" ]; then cp "../../LICENSE" "dist_all/"; fi
if [ -f "../../install_idt_macos.sh" ]; then 
    cp "../../install_idt_macos.sh" "dist_all/"
    chmod +x "dist_all/install_idt_macos.sh"
fi

echo ""
echo "========================================"
echo "PACKAGING COMPLETE"
echo "========================================"
echo ""
echo "All applications packaged in: BuildAndRelease/MacBuilds/dist_all/"
echo ""
echo "Contents:"
echo "  - dist_all/idt (CLI executable)"
echo "  - dist_all/Applications/ (GUI .app bundles)"
echo ""
echo "Ready for DMG creation or distribution."
echo ""
