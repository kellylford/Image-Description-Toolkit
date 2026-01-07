#!/bin/bash
# ============================================================================
# Create macOS .dmg Disk Image for Image Description Toolkit
# ============================================================================
# Creates a drag-and-drop .dmg installer with all applications
#
# Requirements:
#   - hdiutil (included with macOS)
#   - All applications must be built first
# ============================================================================

set -e  # Exit on error
set -u  # Exit on undefined variable

echo "========================================================================"
echo "Creating macOS .dmg Disk Image for IDT"
echo "========================================================================"
echo ""

# Change to project root (now two levels up since we're in MacBuilds/)
cd "$(dirname "$0")/../.."

# Version information
VERSION=$(cat VERSION 2>/dev/null || echo "1.0.0")
DMG_NAME="IDT-${VERSION}"

echo "Building disk image for version: $VERSION"
echo ""

# Create dist_macos directory if it doesn't exist
mkdir -p dist_macos

# Check if all applications are built
MISSING_APPS=0

if [ ! -f "dist/idt" ]; then
    echo "ERROR: dist/idt not found. Please build the CLI tool first."
    MISSING_APPS=1
fi

if [ ! -d "viewer/dist/viewer.app" ]; then
    echo "ERROR: viewer/dist/viewer.app not found. Please build Viewer first."
    MISSING_APPS=1
fi

if [ ! -d "imagedescriber/dist/imagedescriber.app" ]; then
    echo "ERROR: imagedescriber/dist/imagedescriber.app not found. Please build ImageDescriber first."
    MISSING_APPS=1
fi

if [ ! -d "prompt_editor/dist/prompteditor.app" ]; then
    echo "ERROR: prompt_editor/dist/prompteditor.app not found. Please build PromptEditor first."
    MISSING_APPS=1
fi

if [ ! -d "idtconfigure/dist/idtconfigure.app" ]; then
    echo "ERROR: idtconfigure/dist/idtconfigure.app not found. Please build IDTConfigure first."
    MISSING_APPS=1
fi

if [ $MISSING_APPS -ne 0 ]; then
    echo ""
    echo "Please run: ./BuildAndRelease/MacBuilds/builditall_macos.sh"
    exit 1
fi

# Create staging directory
echo "Creating staging directory..."
DMG_STAGING="BuildAndRelease/MacBuilds/dmg_staging"
rm -rf "$DMG_STAGING"
mkdir -p "$DMG_STAGING"

# Copy GUI applications
echo "Copying GUI applications..."
cp -R "viewer/dist/viewer.app" "$DMG_STAGING/"
cp -R "imagedescriber/dist/imagedescriber.app" "$DMG_STAGING/"
cp -R "prompt_editor/dist/prompteditor.app" "$DMG_STAGING/"
cp -R "idtconfigure/dist/idtconfigure.app" "$DMG_STAGING/"

# Create CLI Tools folder
echo "Creating CLI Tools folder..."
mkdir -p "$DMG_STAGING/CLI Tools"
cp "dist/idt" "$DMG_STAGING/CLI Tools/idt"
chmod +x "$DMG_STAGING/CLI Tools/idt"

# Create install script for CLI tool
cat > "$DMG_STAGING/CLI Tools/INSTALL_CLI.sh" << 'EOF'
#!/bin/bash
# Install idt CLI tool to /usr/local/bin
echo "Installing idt CLI tool..."
sudo cp "$(dirname "$0")/idt" /usr/local/bin/idt
sudo chmod +x /usr/local/bin/idt
echo "Installed idt to /usr/local/bin/idt"
echo "You can now run: idt --help"
EOF
chmod +x "$DMG_STAGING/CLI Tools/INSTALL_CLI.sh"

# Create README
cat > "$DMG_STAGING/README.txt" << EOF
Image Description Toolkit v${VERSION}
=====================================

INSTALLATION INSTRUCTIONS:

GUI Applications:
  Drag the .app files to your Applications folder (or anywhere you like)

CLI Tool:
  1. Open the "CLI Tools" folder
  2. Run INSTALL_CLI.sh (it will ask for your password)
  OR
  3. Manually copy 'idt' to /usr/local/bin/

WHAT'S INCLUDED:

  viewer.app          - View and monitor image description workflows
  imagedescriber.app  - Batch process images with AI descriptions  
  prompteditor.app    - Edit AI prompt templates
  idtconfigure.app    - Configure toolkit settings
  idt (CLI)           - Command-line interface for all features

ACCESSIBILITY:

All applications are fully accessible:
  - VoiceOver compatible
  - Full keyboard navigation
  - WCAG 2.2 AA compliant

REQUIREMENTS:

  - macOS 10.13 (High Sierra) or later
  - For AI features: Ollama, OpenAI API, or Anthropic Claude API

GETTING STARTED:

  1. Drag .app files to Applications folder
  2. Run INSTALL_CLI.sh from "CLI Tools" folder
  3. Open Viewer to browse existing workflows
  4. Use ImageDescriber for batch processing
  5. Run 'idt --help' in Terminal for CLI options

For documentation and support, see the project repository.
EOF

# Create Applications symlink for easy drag-and-drop
ln -s /Applications "$DMG_STAGING/Applications"

# Create temporary DMG
echo "Creating temporary DMG..."
TEMP_DMG="dist_macos/${DMG_NAME}-temp.dmg"
rm -f "$TEMP_DMG"

hdiutil create \
    -srcfolder "$DMG_STAGING" \
    -volname "Image Description Toolkit" \
    -fs HFS+ \
    -fsargs "-c c=64,a=16,e=16" \
    -format UDRW \
    -size 500m \
    "$TEMP_DMG"

echo "Skipping Finder customization (can be done manually after mounting)..."

# Convert to compressed read-only image immediately
echo "Compressing DMG..."
FINAL_DMG="dist_macos/${DMG_NAME}.dmg"
rm -f "$FINAL_DMG"

hdiutil convert \
    "$TEMP_DMG" \
    -format UDZO \
    -imagekey zlib-level=9 \
    -o "$FINAL_DMG"

# Clean up
echo "Cleaning up..."
rm -f "$TEMP_DMG"
rm -rf "$DMG_STAGING"

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================================================"
    echo "DISK IMAGE CREATED SUCCESSFULLY"
    echo "========================================================================"
    echo "Disk Image: dist_macos/${DMG_NAME}.dmg"
    echo ""
    echo "To distribute: Double-click to mount, then drag apps to Applications"
    echo ""
    echo "NOTE: For distribution, you should code sign the applications first:"
    echo "  codesign --deep --force --verify --verbose \\"
    echo "    --sign 'Developer ID Application: Your Name' \\"
    echo "    viewer.app"
    echo ""
else
    echo ""
    echo "ERROR: Failed to create disk image"
    exit 1
fi

exit 0
