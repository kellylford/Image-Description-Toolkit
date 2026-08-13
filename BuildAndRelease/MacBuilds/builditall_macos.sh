#!/bin/bash
# ============================================================================
# Build All Applications - Master Build Script for macOS
# ============================================================================
# This script builds both applications in the Image Description Toolkit:
#   1. IDT (main command-line toolkit)
#   2. ImageDescriber (batch processing GUI with integrated Viewer Mode, prompt editor, and configuration)
#   3. IDT Chat (standalone accessible chat client)
#
# Prerequisites:
#   - Virtual environment set up for ImageDescriber app
#   - Main IDT dependencies installed in root .venv or system Python
#
# Output:
#   - dist/idt (CLI binary)
#   - imagedescriber/dist/ImageDescriber.app
#   - chatapp/dist/IDTChat.app
# ============================================================================

set -e  # Exit on error
set -u  # Exit on undefined variable

echo ""
echo "========================================================================"
echo "BUILD ALL APPLICATIONS - macOS"
echo "========================================================================"
echo ""

# ============================================================================
# CLEAN BUILD CACHE
# ============================================================================
# Change to project root directory FIRST (now two levels up since we're in MacBuilds/)
cd "$(dirname "$0")/../.."

# Each build script passes --clean to PyInstaller, which cleans its own
# build directory and the shared PyInstaller cache immediately before that
# build runs. No separate pre-cleaning step is needed here.
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

echo ""
echo "This script builds IDT and ImageDescriber."
echo "Viewer is now integrated into ImageDescriber (Viewer Mode)."
echo ""
echo "Make sure all virtual environments are set up before continuing."
echo ""

BUILD_ERRORS=0

# ----------------------------------------------------------------------------
# Increment helper.
#
# Do NOT use the bash post-increment form here. It evaluates to the OLD value,
# so when the counter is 0 the arithmetic result is 0, which bash reports as
# exit status 1 -- and under "set -e" that aborts the whole script. The first
# build failure would kill the run before the second build or the summary,
# making the "ERRORS: N build failures" branch unreachable.
# ----------------------------------------------------------------------------
count_error() {
    BUILD_ERRORS=$((BUILD_ERRORS + 1))
}

# ----------------------------------------------------------------------------
# Remove the previous run's artifacts before building. Without this, a build
# that fails (or succeeds without emitting anything) leaves the old binary in
# dist/, and the packaging step below ships it -- a stale app in the DMG,
# reported as a clean build.
# ----------------------------------------------------------------------------
rm -f  "idt/dist/idt"
rm -rf "imagedescriber/dist/ImageDescriber.app"
rm -rf "chatapp/dist/IDTChat.app"

# ============================================================================
echo ""
echo "[1/3] Building IDT (main toolkit)..."
echo "========================================================================"
echo ""

cd idt
if bash build_idt.sh; then
    echo "SUCCESS: IDT built successfully"
else
    echo "ERROR: IDT build failed!"
    count_error
fi
cd ..

# ============================================================================
echo ""
echo "[2/3] Building ImageDescriber..."
echo "========================================================================"
echo ""

cd imagedescriber
# build_imagedescriber_wx.sh activates its own .venv — no need to do it here
if bash build_imagedescriber_wx.sh; then
    echo "SUCCESS: ImageDescriber built successfully"
else
    echo "ERROR: ImageDescriber build failed!"
    count_error
fi
cd ..

# ============================================================================
echo ""
echo "[3/3] Building IDT Chat (standalone accessible chat client)..."
echo "========================================================================"
echo ""

cd chatapp
# build_chatapp.sh picks a venv itself: chatapp/.venv, else imagedescriber/.venv
if bash build_chatapp.sh; then
    echo "SUCCESS: IDT Chat built successfully"
else
    echo "ERROR: IDT Chat build failed!"
    count_error
fi
cd ..

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

    # Copy IDT CLI. A missing artifact is fatal: a build step can exit 0 without
    # emitting anything, and shipping a DMG built from nothing (or from the
    # previous run's leftovers) is worse than failing here.
    if [ ! -f "idt/dist/idt" ]; then
        echo "✗ idt NOT FOUND - the build did not produce an executable"
        exit 1
    fi
    cp "idt/dist/idt" "$DIST_ALL/"
    chmod +x "$DIST_ALL/idt"
    echo "✓ idt (CLI)"

    # Copy ImageDescriber.app (includes integrated Viewer Mode, prompt editor and configuration)
    if [ ! -d "imagedescriber/dist/ImageDescriber.app" ]; then
        echo "✗ ImageDescriber.app NOT FOUND - the build did not produce an app bundle"
        exit 1
    fi
    cp -R "imagedescriber/dist/ImageDescriber.app" "$DIST_ALL/Applications/"
    echo "✓ ImageDescriber.app (with integrated Viewer Mode and Tools menu)"

    # Copy IDTChat.app (standalone accessible chat client)
    if [ ! -d "chatapp/dist/IDTChat.app" ]; then
        echo "✗ IDTChat.app NOT FOUND - the build did not produce an app bundle"
        exit 1
    fi
    cp -R "chatapp/dist/IDTChat.app" "$DIST_ALL/Applications/"
    echo "✓ IDTChat.app (accessible chat client)"
    
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
if [ -f "idt/dist/idt" ]; then
    echo ""
    echo "[Post-Build Check] Validating built executable..."
    if ! python3 BuildAndRelease/validate_build.py; then
        echo ""
        echo "WARNING: Build validation found issues!"
        echo "The executable may not work correctly in production."
        echo "Review the errors above and rebuild after fixing."
        echo ""
        count_error
    fi
fi

echo ""

if [ $BUILD_ERRORS -ne 0 ]; then
    echo ""
    echo "Build completed with $BUILD_ERRORS error(s)."
    exit 1
fi

exit 0
