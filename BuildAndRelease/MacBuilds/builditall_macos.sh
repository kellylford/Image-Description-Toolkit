#!/bin/bash
# ============================================================================
# Build All Applications - Master Build Script for macOS
# ============================================================================
# This script builds all five applications in the Image Description Toolkit:
#   1. IDT (main command-line toolkit)
#   2. Viewer (image description viewer GUI)
#   3. Prompt Editor (prompt configuration GUI)
#   4. ImageDescriber (batch processing GUI)
#   5. IDTConfigure (configuration management GUI)
#
# Prerequisites:
#   - Virtual environment set up for each GUI app (viewer, prompt_editor, imagedescriber, idtconfigure)
#   - Main IDT dependencies installed in root .venv or system Python
#
# Output:
#   - dist/idt (CLI binary)
#   - viewer/dist/viewer.app
#   - prompt_editor/dist/prompt_editor.app
#   - imagedescriber/dist/ImageDescriber.app
#   - idtconfigure/dist/idtconfigure.app
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

echo "Cleaning PyInstaller cache to ensure fresh build..."
python3 -c "import shutil; from pathlib import Path; cache_dir = Path.home() / 'Library' / 'Caches' / 'pyinstaller'; shutil.rmtree(cache_dir, ignore_errors=True); print(f'Cleaned: {cache_dir}')"

echo "Cleaning build and dist directories..."
rm -rf build dist
echo "Build cache cleaned successfully."
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
echo "This will build all five applications:"
echo "  1. IDT (main toolkit)"
echo "  2. Viewer"
echo "  3. Prompt Editor"
echo "  4. ImageDescriber"
echo "  5. IDTConfigure"
echo ""
echo "Make sure all virtual environments are set up before continuing."
echo ""

BUILD_ERRORS=0

# ============================================================================
echo ""
echo "[1/5] Building IDT (main toolkit)..."
echo "========================================================================"
echo ""

cd idt
if bash build_idt.sh; then
    echo "SUCCESS: IDT built successfully"
else
    echo "ERROR: IDT build failed!"
    ((BUILD_ERRORS++))
fi
cd ..

# ============================================================================
echo ""
echo "[2/5] Building Viewer..."
echo "========================================================================"
echo ""

cd viewer
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    if bash build_viewer_wx.sh; then
        echo "SUCCESS: Viewer built successfully"
    else
        echo "ERROR: Viewer build failed!"
        ((BUILD_ERRORS++))
    fi
    deactivate
else
    echo "ERROR: Viewer virtual environment not found at viewer/.venv"
    echo "Please run: cd viewer && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    ((BUILD_ERRORS++))
fi
cd ..

# ============================================================================
echo ""
echo "[3/5] Building Prompt Editor..."
echo "========================================================================"
echo ""

cd prompt_editor
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    if bash build_prompt_editor_wx.sh; then
        echo "SUCCESS: Prompt Editor built successfully"
    else
        echo "ERROR: Prompt Editor build failed!"
        ((BUILD_ERRORS++))
    fi
    deactivate
else
    echo "ERROR: Prompt Editor virtual environment not found at prompt_editor/.venv"
    echo "Please run: cd prompt_editor && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    ((BUILD_ERRORS++))
fi
cd ..

# ============================================================================
echo ""
echo "[4/5] Building ImageDescriber..."
echo "========================================================================"
echo ""

cd imagedescriber
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    if bash build_imagedescriber_wx.sh; then
        echo "SUCCESS: ImageDescriber built successfully"
    else
        echo "ERROR: ImageDescriber build failed!"
        ((BUILD_ERRORS++))
    fi
    deactivate
else
    echo "ERROR: ImageDescriber virtual environment not found at imagedescriber/.venv"
    echo "Please run: cd imagedescriber && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    ((BUILD_ERRORS++))
fi
cd ..

# ============================================================================
echo ""
echo "[5/5] Building IDTConfigure..."
echo "========================================================================"
echo ""

cd idtconfigure
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    if bash build_idtconfigure_wx.sh; then
        echo "SUCCESS: IDTConfigure built successfully"
    else
        echo "ERROR: IDTConfigure build failed!"
        ((BUILD_ERRORS++))
    fi
    deactivate
else
    echo "ERROR: IDTConfigure virtual environment not found at idtconfigure/.venv"
    echo "Please run: cd idtconfigure && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    ((BUILD_ERRORS++))
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

# Show version from built CLI if available
if [ -f "dist/idt" ]; then
    echo ""
    echo "--- Built Executable Version ---"
    dist/idt version
    echo "--------------------------------"
fi

# ============================================================================
# COLLECT ALL BUILDS TO CENTRAL LOCATION
# ============================================================================
if [ $BUILD_ERRORS -eq 0 ]; then
    echo ""
    echo "========================================================================"
    echo "COLLECTING BUILDS TO CENTRAL LOCATION"
    echo "========================================================================"
    echo ""
    
    # Create central distribution directory
    DIST_MACOS="dist_macos"
    rm -rf "$DIST_MACOS"
    mkdir -p "$DIST_MACOS"
    
    echo "Copying built applications to $DIST_MACOS/..."
    
    # Copy IDT CLI
    if [ -f "dist/idt" ]; then
        cp "dist/idt" "$DIST_MACOS/"
        echo "✓ Copied idt (CLI)"
    fi
    
    # Copy Viewer.app
    if [ -d "viewer/dist/viewer.app" ]; then
        cp -R "viewer/dist/viewer.app" "$DIST_MACOS/"
        echo "✓ Copied viewer.app"
    fi
    
    # Copy Prompt Editor.app
    if [ -d "prompt_editor/dist/prompteditor.app" ]; then
        cp -R "prompt_editor/dist/prompteditor.app" "$DIST_MACOS/"
        echo "✓ Copied prompteditor.app"
    fi
    
    # Copy ImageDescriber.app
    if [ -d "imagedescriber/dist/imagedescriber.app" ]; then
        cp -R "imagedescriber/dist/imagedescriber.app" "$DIST_MACOS/"
        echo "✓ Copied imagedescriber.app"
    fi
    
    # Copy IDTConfigure.app
    if [ -d "idtconfigure/dist/idtconfigure.app" ]; then
        cp -R "idtconfigure/dist/idtconfigure.app" "$DIST_MACOS/"
        echo "✓ Copied idtconfigure.app"
    fi
    
    echo ""
    echo "All applications collected in: $DIST_MACOS/"
    echo ""
    ls -lh "$DIST_MACOS/"
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
