#!/bin/bash
# ============================================================================
# Build All Applications - Master Build Script for macOS
# ============================================================================
# This script builds both applications in the Image Description Toolkit:
#   1. IDT (main command-line toolkit)
#   2. ImageDescriber (batch processing GUI with integrated Viewer Mode, prompt editor, and configuration)
#
# Prerequisites:
#   - Virtual environment set up for ImageDescriber app
#   - Main IDT dependencies installed in root .venv or system Python
#
# Output:
#   - dist/idt (CLI binary)
#   - imagedescriber/dist/ImageDescriber.app
# ============================================================================

set -e  # Exit on error
set -u  # Exit on undefined variable

echo ""
echo "========================================================================"
echo "BUILD ALL APPLICATIONS - macOS"
echo "========================================================================"
echo ""

# ============================================================================
# SETUP
# ============================================================================
# Change to project root directory FIRST (now two levels up since we're in MacBuilds/)
cd "$(dirname "$0")/../.."

echo "Cleaning build and dist directories..."
rm -rf build dist
echo ""

# ============================================================================
# PRE-BUILD VALIDATION
# ============================================================================
echo "Running pre-build validation checks..."
echo "This catches integration bugs before building (saves time later)"
echo ""

if python3 tools/pre_build_validation.py; then
    echo ""
    echo "Validation passed - proceeding with build..."
    echo ""
else
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 1 ]; then
        echo ""
        echo "========================================================================"
        echo "BUILD ABORTED - VALIDATION FAILED"
        echo "========================================================================"
        echo "Fix the issues above before building."
        echo "These bugs would only appear at runtime, wasting user testing time."
        echo ""
        exit 1
    elif [ $EXIT_CODE -eq 2 ]; then
        echo ""
        echo "========================================================================"
        echo "WARNINGS DETECTED - Review before release"
        echo "========================================================================"
        echo "Build will continue, but consider fixing warnings."
        echo ""
        sleep 3
    fi
fi

# Show composed build version and commit before starting
echo "--- Build Version Banner (pre-build) ---"
python3 idt/idt_cli.py version
echo "----------------------------------------"
echo ""

echo ""
echo "This script builds IDT and ImageDescriber."
echo "Viewer is now integrated into ImageDescriber (Viewer Mode)."
echo ""
echo "Applications to build:"
echo "  1. IDT (CLI)"
echo "  2. ImageDescriber (with integrated Viewer Mode and Tools menu)"
echo ""
echo "Make sure all virtual environments are set up before continuing."
echo ""

BUILD_ERRORS=0

# ============================================================================
# BUILD IN PARALLEL - Both apps are independent, run simultaneously
# ============================================================================
echo ""
echo "Building IDT and ImageDescriber in parallel..."
echo "========================================================================"
echo ""

IDT_LOG=$(mktemp /tmp/idt_build_XXXXXX)
IMAGEDESC_LOG=$(mktemp /tmp/imagedesc_build_XXXXXX)

# Start IDT build in background
(
    cd idt
    bash build_idt.sh
) > "$IDT_LOG" 2>&1 &
IDT_PID=$!

# Start ImageDescriber build in background
(
    cd imagedescriber
    if [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
        bash build_imagedescriber_wx.sh
        EXIT_CODE=$?
        deactivate
        exit $EXIT_CODE
    else
        echo "ERROR: ImageDescriber virtual environment not found at imagedescriber/.venv"
        echo "Please run: cd imagedescriber && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
        exit 1
    fi
) > "$IMAGEDESC_LOG" 2>&1 &
IMAGEDESC_PID=$!

# Wait for both builds to finish
echo "Waiting for IDT build (PID $IDT_PID) and ImageDescriber build (PID $IMAGEDESC_PID)..."
set +e  # Disable exit-on-error so we can capture both exit codes
wait $IDT_PID
IDT_EXIT=$?
wait $IMAGEDESC_PID
IMAGEDESC_EXIT=$?
set -e

# Show IDT output
echo ""
echo "========================================================================"
echo "IDT BUILD OUTPUT"
echo "========================================================================"
cat "$IDT_LOG"
rm -f "$IDT_LOG"

# Show ImageDescriber output
echo ""
echo "========================================================================"
echo "IMAGEDESCRIBER BUILD OUTPUT"
echo "========================================================================"
cat "$IMAGEDESC_LOG"
rm -f "$IMAGEDESC_LOG"

echo ""
echo "========================================================================"
if [ $IDT_EXIT -eq 0 ]; then
    echo "SUCCESS: IDT built successfully"
else
    echo "ERROR: IDT build failed!"
    ((BUILD_ERRORS++))
fi
if [ $IMAGEDESC_EXIT -eq 0 ]; then
    echo "SUCCESS: ImageDescriber built successfully"
else
    echo "ERROR: ImageDescriber build failed!"
    ((BUILD_ERRORS++))
fi

# ============================================================================
echo ""
echo "========================================================================"
echo "BUILD SUMMARY"
echo "========================================================================"
echo ""

echo "BUILD COMPLETE"
if [ $BUILD_ERRORS -eq 0 ]; then
    echo "SUCCESS: All applications built successfully"
else
    echo "ERRORS: $BUILD_ERRORS build failures encountered"
fi

# Show version from built CLI if available
if [ -f "dist/idt" ]; then
    echo ""
    echo "--- Built Executable Version ---"
    dist/idt version
    echo "--------------------------------"
fi

# ============================================================================
# COLLECT ALL BUILDS TO CENTRAL LOCATION (PACKAGING)
# ============================================================================
if [ $BUILD_ERRORS -eq 0 ]; then
    echo ""
    echo "========================================================================"
    echo "PACKAGING ALL APPLICATIONS"
    echo "========================================================================"
    echo ""
    
    # Create distribution directory in BuildAndRelease/MacBuilds
    DIST_ALL="BuildAndRelease/MacBuilds/dist_all"
    rm -rf "$DIST_ALL"
    mkdir -p "$DIST_ALL"
    mkdir -p "$DIST_ALL/Applications"
    
    echo "Packaging applications to $DIST_ALL/..."
    echo ""
    
    # Copy IDT CLI
    if [ -f "idt/dist/idt" ]; then
        cp "idt/dist/idt" "$DIST_ALL/"
        chmod +x "$DIST_ALL/idt"
        echo "✓ idt (CLI)"
    else
        echo "✗ idt NOT FOUND"
    fi
    
    # Copy ImageDescriber.app (includes integrated Viewer Mode, prompt editor and configuration)
    if [ -d "imagedescriber/dist/ImageDescriber.app" ]; then
        cp -R "imagedescriber/dist/ImageDescriber.app" "$DIST_ALL/Applications/"
        echo "✓ ImageDescriber.app (with integrated Viewer Mode and Tools menu)"
    else
        echo "✗ ImageDescriber.app NOT FOUND"
    fi
    
    # Copy documentation
    echo ""
    echo "Copying documentation..."
    if [ -f "README.md" ]; then cp "README.md" "$DIST_ALL/"; fi
    if [ -f "LICENSE" ]; then cp "LICENSE" "$DIST_ALL/"; fi
    if [ -f "install_idt_macos.sh" ]; then 
        cp "install_idt_macos.sh" "$DIST_ALL/"
        chmod +x "$DIST_ALL/install_idt_macos.sh"
    fi
    
    echo ""
    echo "========================================================================"
    echo "PACKAGING COMPLETE"
    echo "========================================================================"
    echo ""
    echo "All applications packaged in: $DIST_ALL/"
    echo ""
    echo "Contents:"
    echo "  - dist_all/idt (CLI executable)"
    echo "  - dist_all/Applications/ (GUI .app bundles)"
    echo ""
    echo "Ready for DMG creation or distribution."
    echo ""
fi

# Post-build validation: Test the built executable
if [ -f "dist/idt" ]; then
    echo ""
    echo "[Post-Build Check] Validating built executable..."
    if ! python3 BuildAndRelease/validate_build.py; then
        echo ""
        echo "WARNING: Build validation found issues!"
        echo "The executable may not work correctly in production."
        echo "Review the errors above and rebuild after fixing."
        echo ""
        ((BUILD_ERRORS++))
    fi
fi

echo ""

if [ $BUILD_ERRORS -ne 0 ]; then
    echo ""
    echo "Build completed with $BUILD_ERRORS error(s)."
    exit 1
fi

exit 0
