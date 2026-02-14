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

# ============================================================================
# CODE SIGNING SETUP
# ============================================================================

# Detect Developer ID certificate
SIGNING_IDENTITY=$(security find-identity -v -p codesigning | grep "Developer ID Application" | head -1 | sed 's/.*"\(.*\)"/\1/')

if [ -z "$SIGNING_IDENTITY" ]; then
    echo "⚠️  No Developer ID certificate found - building unsigned DMG"
    echo ""
    SIGN_CODE=0
    NOTARIZE=0
else
    echo "Found Developer ID certificate: $SIGNING_IDENTITY"
    SIGN_CODE=1
    
    # Check for stored notarization credentials
    PROFILE_NAME=""
    for profile in "idt" "notarize" "notarytool-password" "notarytool"; do
        if xcrun notarytool history --keychain-profile "$profile" >/dev/null 2>&1; then
            PROFILE_NAME="$profile"
            break
        fi
    done
    
    if [ -n "$PROFILE_NAME" ]; then
        echo "Found notarization credentials (profile: $PROFILE_NAME)"
        echo "✓ Code signing enabled"
        echo "✓ Notarization enabled"
        NOTARIZE=1
    else
        echo "✓ Code signing enabled"
        echo "⚠️  No notarization credentials found - DMG will be signed but not notarized"
        echo "   To set up: xcrun notarytool store-credentials --apple-id 'your@apple.id' --team-id 'P887QF74N8'"
        NOTARIZE=0
    fi
fi

echo ""

# Create dist directory in MacBuilds if it doesn't exist
mkdir -p BuildAndRelease/MacBuilds/dist

# Check if all applications are built
MISSING_APPS=0

if [ ! -f "idt/dist/idt" ]; then
    echo "ERROR: idt/dist/idt not found. Please build the CLI tool first."
    MISSING_APPS=1
fi

if [ ! -d "imagedescriber/dist/ImageDescriber.app" ]; then
    echo "ERROR: imagedescriber/dist/ImageDescriber.app not found. Please build ImageDescriber first."
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

# Create IDT folder to contain all applications and CLI tool
echo "Creating IDT folder structure..."
mkdir -p "$DMG_STAGING/IDT"

# Copy GUI applications into IDT folder
echo "Copying GUI applications..."
# Use ditto instead of cp to preserve extended attributes and code signatures
ditto "imagedescriber/dist/ImageDescriber.app" "$DMG_STAGING/IDT/ImageDescriber.app"

# Copy CLI tool directly into IDT folder
echo "Copying CLI tool..."
# Use ditto to preserve code signatures and extended attributes
ditto "idt/dist/idt" "$DMG_STAGING/IDT/idt"
chmod +x "$DMG_STAGING/IDT/idt"

# Sign applications if code signing is enabled
if [ "$SIGN_CODE" = "1" ]; then
    echo ""
    echo "Signing applications..."
    for APP in "$DMG_STAGING/IDT"/*.app; do
        if [ -d "$APP" ]; then
            APP_NAME=$(basename "$APP")
            echo "  Preparing $APP_NAME for signing..."
            
            # Critical: Remove Python.framework signature (has python.org Team ID)
            find "$APP/Contents/Frameworks" -type f -name "Python" 2>/dev/null | while read pylib; do
                echo "    Removing Python.framework signature"
                codesign --remove-signature "$pylib" 2>/dev/null || true
            done
            
            # Remove all other signatures
            find "$APP/Contents/Frameworks" -type f \( -name "*.so" -o -name "*.dylib" \) 2>/dev/null | while read lib; do
                codesign --remove-signature "$lib" 2>/dev/null || true
            done
            codesign --remove-signature "$APP/Contents/MacOS"/* 2>/dev/null || true
            codesign --remove-signature "$APP" 2>/dev/null || true
            
            # Now sign with our Developer ID
            echo "  Signing $APP_NAME with Developer ID..."
            codesign --force --deep \
                --options runtime \
                --timestamp \
                --sign "$SIGNING_IDENTITY" \
                "$APP"
            codesign --verify --verbose "$APP"
        fi
    done
    
    # Sign CLI tool
    echo "  Signing idt CLI..."
    codesign --remove-signature "$DMG_STAGING/IDT/idt" 2>/dev/null || true
    if codesign --force \
        --options runtime \
        --timestamp \
        --sign "$SIGNING_IDENTITY" \
        "$DMG_STAGING/IDT/idt" 2>/dev/null; then
        codesign --verify --verbose "$DMG_STAGING/IDT/idt"
        echo "  ✓ CLI tool signed"
    else
        echo "  ⚠️  CLI tool signing failed"
    fi
    
    echo "✓ All applications signed"
    echo ""
else
    echo ""
    echo "⚠️  Code signing disabled - apps will be unsigned"
    echo "   Users will need to right-click → Open first time"
    echo ""
fi

# Create install script for CLI tool (optional - for users who want it in PATH)
cat > "$DMG_STAGING/IDT/INSTALL_CLI_TO_PATH.sh" << 'EOF'
#!/bin/bash
# Install idt CLI tool to /usr/local/bin (adds to PATH)
echo "Installing idt CLI tool to /usr/local/bin..."
sudo cp "$(dirname "$0")/idt" /usr/local/bin/idt
sudo chmod +x /usr/local/bin/idt
echo "✓ Installed idt to /usr/local/bin/idt"
echo "You can now run 'idt --help' from any directory"
EOF
chmod +x "$DMG_STAGING/IDT/INSTALL_CLI_TO_PATH.sh"

# Create README
cat > "$DMG_STAGING/README.txt" << EOF
Image Description Toolkit v${VERSION}
=====================================

INSTALLATION INSTRUCTIONS:

  1. Drag the IDT folder to your Applications folder (or anywhere you prefer)
  
  That's it! All applications, the CLI tool, and their config/log files 
  will stay organized inside the IDT folder.

USING THE CLI FROM ANY DIRECTORY (OPTIONAL):

  To use 'idt' command from Terminal anywhere:
  1. Open the IDT folder in Applications
  2. Run INSTALL_CLI_TO_PATH.sh (it will ask for your password)
  
  This creates a link from /usr/local/bin/idt to ~/Applications/IDT/idt

WHAT'S INCLUDED IN THE IDT FOLDER:

  ImageDescriber.app  - Batch process images with AI descriptions
                        Includes integrated:
                        • Editor Mode (batch processing)
                        • Viewer Mode (monitor workflows)
                        • Prompt Editor (Tools → Edit Prompts)
                        • Configuration Manager (Tools → Configure Settings)

  idt                - Command-line interface for all features
                        Can be run directly: ~/Applications/IDT/idt --help

  Config & Logs      - All configuration files and logs stay in this folder
                        Keeps your Applications folder clean and organized

ACCESSIBILITY:

All applications are fully accessible:
  - VoiceOver compatible
  - Full keyboard navigation
  - WCAG 2.2 AA compliant

REQUIREMENTS:

  - macOS 10.13 (High Sierra) or later
  - For AI features: Ollama, OpenAI API, or Anthropic Claude API

GETTING STARTED:

  1. Drag IDT folder to Applications
  2. Open Applications/IDT/ImageDescriber.app
  3. Switch to Viewer Mode tab to browse existing workflows
  4. Use Editor Mode for batch processing of images
  5. Run ~/Applications/IDT/idt --help for CLI options

For documentation and support, see the project repository.
EOF

# Create Applications symlink for easy drag-and-drop
ln -s /Applications "$DMG_STAGING/Applications"

# Create temporary DMG
echo "Creating temporary DMG..."
TEMP_DMG="BuildAndRelease/MacBuilds/dist/${DMG_NAME}-temp.dmg"
rm -f "$TEMP_DMG"

hdiutil create \
    -srcfolder "$DMG_STAGING" \
    -volname "Image Description Toolkit" \
    -fs HFS+ \
    -fsargs "-c c=64,a=16,e=16" \
    -format UDRW \
    -size 1500m \
    "$TEMP_DMG"

echo "Skipping Finder customization (can be done manually after mounting)..."

# Convert to compressed read-only image immediately
echo "Compressing DMG..."
FINAL_DMG="BuildAndRelease/MacBuilds/dist/${DMG_NAME}.dmg"
rm -f "$FINAL_DMG"

hdiutil convert \
    "$TEMP_DMG" \
    -format UDZO \
    -imagekey zlib-level=9 \
    -o "$FINAL_DMG"

# Clean up
echo "Cleaning up temporary files..."
rm -f "$TEMP_DMG"
rm -rf "$DMG_STAGING"

# Sign the DMG if code signing is enabled
if [ "$SIGN_CODE" = "1" ]; then
    echo ""
    echo "Signing DMG..."
    codesign --force --sign "$SIGNING_IDENTITY" "$FINAL_DMG"
    codesign --verify --verbose "$FINAL_DMG"
    echo "✓ DMG signed"
fi

# Notarize if enabled
if [ "$SIGN_CODE" = "1" ] && [ "$NOTARIZE" = "1" ]; then
    echo ""
    echo "========================================================================"
    echo "NOTARIZING WITH APPLE"
    echo "========================================================================"
    echo "Submitting to Apple (this takes 2-5 minutes)..."
    echo ""
    
    SUBMIT_OUTPUT=$(xcrun notarytool submit "$FINAL_DMG" \
        --keychain-profile "$PROFILE_NAME" \
        --wait 2>&1)
    
    echo "$SUBMIT_OUTPUT"
    
    if echo "$SUBMIT_OUTPUT" | grep -q "status: Accepted"; then
        echo ""
        echo "✓ Notarization successful!"
        echo ""
        echo "Stapling notarization ticket..."
        xcrun stapler staple "$FINAL_DMG"
        xcrun stapler validate "$FINAL_DMG"
        echo "✓ Notarization ticket stapled"
    else
        echo ""
        echo "❌ Notarization failed - see output above"
        exit 1
    fi
fi

# Success summary
echo ""
echo "========================================================================"
echo "BUILD COMPLETE"
echo "========================================================================"
echo "DMG: BuildAndRelease/MacBuilds/dist/${DMG_NAME}.dmg"
echo ""

if [ "$SIGN_CODE" = "1" ]; then
    echo "✓ Code signed"
    if [ "$NOTARIZE" = "1" ]; then
        echo "✓ Notarized and stapled"
        echo ""
        echo "This DMG is ready for public distribution!"
    else
        echo "⚠️  Not notarized - users will see security warnings"
    fi
else
    echo "⚠️  Unsigned - users must right-click → Open each app"
fi

echo ""
exit 0
