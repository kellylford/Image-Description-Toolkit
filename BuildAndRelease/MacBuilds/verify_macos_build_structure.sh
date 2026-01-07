#!/bin/bash
# ============================================================================
# Quick Test - Verify macOS Build System Structure
# ============================================================================
# This script verifies that all necessary files are in place for macOS builds
# without actually building (which requires dependencies installed)
# ============================================================================

set -u  # Exit on undefined variable

echo "========================================================================"
echo "macOS Build System Structure Verification"
echo "========================================================================"
echo ""

ERRORS=0
WARNINGS=0

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} Found: $1"
        return 0
    else
        echo -e "${RED}✗${NC} Missing: $1"
        ((ERRORS++))
        return 1
    fi
}

check_executable() {
    if [ -f "$1" ] && [ -x "$1" ]; then
        echo -e "${GREEN}✓${NC} Executable: $1"
        return 0
    elif [ -f "$1" ]; then
        echo -e "${YELLOW}⚠${NC} Not executable: $1"
        ((WARNINGS++))
        return 1
    else
        echo -e "${RED}✗${NC} Missing: $1"
        ((ERRORS++))
        return 1
    fi
}

echo "Checking build scripts..."
echo "------------------------"
check_executable "BuildAndRelease/builditall_macos.sh"
check_executable "BuildAndRelease/build_idt_macos.sh"
check_executable "BuildAndRelease/create_macos_installer.sh"
check_executable "BuildAndRelease/create_macos_dmg.sh"
echo ""

echo "Checking PyInstaller spec files..."
echo "-----------------------------------"
check_file "BuildAndRelease/MacBuilds/final_working_macos.spec"
check_file "viewer/viewer_macos.spec"
check_file "imagedescriber/imagedescriber_macos.spec"
check_file "prompt_editor/prompteditor_macos.spec"
check_file "idtconfigure/idtconfigure_macos.spec"
echo ""

echo "Checking app-specific build scripts..."
echo "---------------------------------------"
check_executable "viewer/build_viewer_macos.sh"
check_executable "imagedescriber/build_imagedescriber_macos.sh"
check_executable "prompt_editor/build_prompt_editor_macos.sh"
check_executable "idtconfigure/build_idtconfigure_macos.sh"
echo ""

echo "Checking source files..."
echo "------------------------"
check_file "idt_cli.py"
check_file "viewer/viewer.py"
check_file "imagedescriber/imagedescriber.py"
check_file "prompt_editor/prompt_editor.py"
check_file "idtconfigure/idtconfigure.py"
echo ""

echo "Checking requirements files..."
echo "------------------------------"
check_file "requirements.txt"
check_file "viewer/requirements.txt"
check_file "imagedescriber/requirements.txt"
check_file "prompt_editor/requirements.txt"
check_file "idtconfigure/requirements.txt"
echo ""

echo "Checking documentation..."
echo "-------------------------"
check_file "docs/BUILD_MACOS.md"
check_file "VERSION"
echo ""

echo "========================================================================"
echo "Verification Summary"
echo "========================================================================"
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo ""
    echo "macOS build system is ready. Next steps:"
    echo "  1. Install dependencies: pip3 install -r requirements.txt"
    echo "  2. Set up virtual environments for each app"
    echo "  3. Run: ./BuildAndRelease/builditall_macos.sh"
    echo ""
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠ ${WARNINGS} warning(s)${NC}"
    echo ""
    echo "Some files are not executable. Fix with:"
    echo "  chmod +x BuildAndRelease/*.sh viewer/*.sh imagedescriber/*.sh prompt_editor/*.sh idtconfigure/*.sh"
    echo ""
    exit 0
else
    echo -e "${RED}✗ ${ERRORS} error(s), ${WARNINGS} warning(s)${NC}"
    echo ""
    echo "Please ensure all build scripts and spec files are present."
    exit 1
fi
