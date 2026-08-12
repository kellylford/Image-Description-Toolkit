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
VERSION_CLEAN=$(echo "$VERSION" | tr ' ' '_')
DMG_NAME="IDT-${VERSION_CLEAN}"

echo "Building disk image for version: $VERSION"
echo ""

# ============================================================================
# CODE SIGNING SETUP
# ============================================================================

# Signing is OPT-IN. With no environment set, this script behaves exactly as it
# always has: ad-hoc signatures, unsigned DMG, users right-click -> Open.
#
#   IDT_SIGN_CODE=1   Sign the apps and the DMG with a Developer ID certificate
#   IDT_NOTARIZE=1    Submit the finished DMG to Apple (implies IDT_SIGN_CODE=1)
#
# See sign_macos.sh and notarize_macos.sh for the credentials each one needs.
#
# Historical note: this block previously hardcoded SIGN_CODE=0 with a comment
# saying Developer ID signing conflicted with the bundled Python.framework's
# python.org signature. That does not apply to the current specs -- both apps
# are onefile builds (EXE with no COLLECT), so there is no Python.framework
# inside the bundle to conflict with.

SIGN_CODE="${IDT_SIGN_CODE:-0}"
NOTARIZE="${IDT_NOTARIZE:-0}"

# Notarization is meaningless without a Developer ID signature.
if [ "$NOTARIZE" = "1" ]; then
    SIGN_CODE=1
fi

SIGNING_IDENTITY="${IDT_SIGNING_IDENTITY:-}"

if [ "$SIGN_CODE" = "1" ]; then
    if [ -z "$SIGNING_IDENTITY" ]; then
        SIGNING_IDENTITY=$(security find-identity -v -p codesigning \
            | grep "Developer ID Application" \
            | head -1 \
            | sed 's/.*"\(.*\)"/\1/') || true
    fi

    if [ -z "$SIGNING_IDENTITY" ]; then
        echo "ERROR: IDT_SIGN_CODE=1 but no Developer ID Application certificate found."
        echo "       Set IDT_SIGNING_IDENTITY explicitly, or import the certificate."
        exit 1
    fi

    echo "Code signing ENABLED"
    echo "  Identity:  $SIGNING_IDENTITY"
    echo "  Notarize:  $NOTARIZE"
    echo ""
else
    echo "Code signing disabled (set IDT_SIGN_CODE=1 to enable)"
    echo "  Apps keep their ad-hoc signatures."
    echo "  Users must right-click -> Open the first time."
    echo ""
fi

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

# Copy user guide with versioned filename
if [ -f "docs/USER_GUIDE_COMPLETE.md" ]; then
    echo "Copying user guide..."
    cp "docs/USER_GUIDE_COMPLETE.md" "$DMG_STAGING/IDT/IDT_User_Guide_${VERSION_CLEAN}.md"
else
    echo "⚠️  WARNING: docs/USER_GUIDE_COMPLETE.md not found — user guide will not be included in DMG"
    echo "   Make sure you are on the feature/video-description branch or later."
fi

# Sign applications if code signing is enabled
if [ "$SIGN_CODE" = "1" ]; then
    echo ""
    echo "Signing applications with Developer ID..."

    # Delegated to sign_macos.sh, which signs inside-out and applies the
    # hardened runtime plus entitlements. The previous inline version used
    # `codesign --deep`, which Apple deprecated: it applies the same
    # entitlements to every nested binary and silently skips code it does
    # not recognise.
    SIGN_TARGETS=()
    for APP in "$DMG_STAGING/IDT"/*.app; do
        [ -d "$APP" ] && SIGN_TARGETS+=("$APP")
    done
    [ -f "$DMG_STAGING/IDT/idt" ] && SIGN_TARGETS+=("$DMG_STAGING/IDT/idt")

    if [ ${#SIGN_TARGETS[@]} -eq 0 ]; then
        echo "ERROR: signing enabled but nothing to sign in $DMG_STAGING/IDT"
        exit 1
    fi

    IDT_SIGNING_IDENTITY="$SIGNING_IDENTITY" \
        bash "$(dirname "$0")/sign_macos.sh" "${SIGN_TARGETS[@]}"

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

  IDT_User_Guide_${VERSION_CLEAN}.md
                     - Complete user guide (open with any Markdown viewer
                       or plain text editor)

  Config & Logs      - All configuration files and logs stay in this folder
                        Keeps your Applications folder clean and organized

ACCESSIBILITY:

All applications are fully accessible:
  - VoiceOver compatible
  - Full keyboard navigation
  - WCAG 2.2 AA compliant

REQUIREMENTS:

  - An Apple Silicon Mac
  - For AI features: Ollama, OpenAI API, or Anthropic Claude API

GETTING STARTED:

  1. Drag IDT folder to Applications
  2. Open Applications/IDT/ImageDescriber.app
  3. Switch to Viewer Mode tab to browse existing workflows
  4. Use Editor Mode for batch processing of images
  5. Run ~/Applications/IDT/idt --help for CLI options

For documentation and support, see the project repository.
EOF

# NOTE: The Applications symlink is NOT added to staging here.
# hdiutil create -srcfolder follows symlinks, so a symlink to /Applications
# causes it to try to copy the entire protected /Applications directory and fail.
# Instead we create the symlink directly on the mounted UDRW volume below.

# ============================================================================
# FINDER CUSTOMIZATION - Background image + icon layout
# ============================================================================

# Create background image using pure Python (no PIL dependency)
# Dark charcoal (35, 35, 40) background, 580×360 pixels
echo "Creating DMG background image..."
BG_IMAGE="/tmp/idt_dmg_bg_$$.png"
python3 << PYEOF
import struct, zlib

w, h = 580, 360
r, g, b = 35, 35, 40  # dark charcoal

row = b'\x00' + bytes([r, g, b] * w)  # filter byte + RGB pixels
raw = row * h

def chunk(t, d):
    c = t + d
    return struct.pack('>I', len(d)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)

png = (b'\x89PNG\r\n\x1a\n'
       + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
       + chunk(b'IDAT', zlib.compress(raw, 9))
       + chunk(b'IEND', b''))

with open('${BG_IMAGE}', 'wb') as f:
    f.write(png)
print("Background image created: ${BG_IMAGE}")
PYEOF

# Detach any stale mount from a previous failed run
VOLUME_NAME="Image Description Toolkit"
MOUNT_POINT="/Volumes/${VOLUME_NAME}"
hdiutil detach "$MOUNT_POINT" 2>/dev/null || true

# ── Step 1: create read-only UDZO from staging (srcfolder works here) ────────
echo "Creating initial compressed DMG from staging..."
TEMP_RO="BuildAndRelease/MacBuilds/dist/${DMG_NAME}-ro.dmg"
TEMP_DMG="BuildAndRelease/MacBuilds/dist/${DMG_NAME}-temp.dmg"
FINAL_DMG="BuildAndRelease/MacBuilds/dist/${DMG_NAME}.dmg"
rm -f "$TEMP_RO" "$TEMP_DMG" "$FINAL_DMG"

hdiutil create \
    -srcfolder "$DMG_STAGING" \
    -volname "${VOLUME_NAME}" \
    -fs APFS \
    -format UDZO \
    -imagekey zlib-level=1 \
    "$TEMP_RO"

# ── Step 2: convert to read-write UDRW so we can customise it ────────────────
echo "Converting to writable image for Finder customization..."
hdiutil convert "$TEMP_RO" -format UDRW -o "$TEMP_DMG"
rm -f "$TEMP_RO"

# ── Step 3: mount the writable image ─────────────────────────────────────────
echo "Mounting writable DMG..."
hdiutil attach -readwrite -noverify -noautoopen "$TEMP_DMG"
sleep 2

if [ ! -d "$MOUNT_POINT" ]; then
    echo "ERROR: DMG did not mount at: $MOUNT_POINT"
    rm -f "$TEMP_DMG" "$BG_IMAGE"
    exit 1
fi

# ── Step 4: add Applications symlink, hidden background image ───────────────
echo "Adding Applications symlink..."
ln -s /Applications "$MOUNT_POINT/Applications"

echo "Copying background image..."
mkdir -p "$MOUNT_POINT/.background"
cp "$BG_IMAGE" "$MOUNT_POINT/.background/background.png"
rm -f "$BG_IMAGE"

# Apply Finder layout via AppleScript:
#   • Window: 580×360 (bounds 200,100 → 780,460)
#   • IDT folder:    left  (165, 185)
#   • Applications:  right (415, 185)
#   • README.txt:    bottom centre (290, 315)
# The Finder layout is cosmetic. It needs a live Aqua session and Automation
# permission, neither of which exists on a headless CI runner, where the
# osascript call fails or hangs indefinitely. Skip it there; the DMG is fully
# functional without it, just plainly laid out.
#
#   IDT_DMG_SKIP_LAYOUT=1   force skip
#   IDT_DMG_SKIP_LAYOUT=0   force attempt
#   unset                   skip when $CI is set or there is no Aqua session
SKIP_LAYOUT="${IDT_DMG_SKIP_LAYOUT:-}"
if [ -z "$SKIP_LAYOUT" ]; then
    if [ -n "${CI:-}" ]; then
        SKIP_LAYOUT=1
    elif ! /bin/launchctl managername 2>/dev/null | grep -q "Aqua"; then
        SKIP_LAYOUT=1
    else
        SKIP_LAYOUT=0
    fi
fi

if [ "$SKIP_LAYOUT" = "1" ]; then
    echo "Skipping Finder layout (no GUI session)."
    echo "  DMG will use the default Finder view. Contents are unaffected."
else
    echo "Applying Finder layout via AppleScript..."
    # Non-fatal: a cosmetic step must not fail an otherwise good build.
    if ! osascript << 'APPLESCRIPT'
tell application "Finder"
    tell disk "Image Description Toolkit"
        open
        set current view of container window to icon view
        set toolbar visible of container window to false
        set statusbar visible of container window to false
        set the bounds of container window to {200, 100, 780, 460}
        set theViewOptions to the icon view options of container window
        set arrangement of theViewOptions to not arranged
        set icon size of theViewOptions to 72
        set background picture of theViewOptions to file ".background:background.png"
        delay 1
        set position of item "IDT" of container window to {165, 185}
        set position of item "Applications" of container window to {415, 185}
        set position of item "README.txt" of container window to {290, 315}
        close
        open
        update without registering applications
        delay 2
    end tell
end tell
APPLESCRIPT
    then
        echo "WARNING: Finder layout failed. Continuing with the default view."
    fi
fi

# Sync filesystem and detach
echo "Syncing and unmounting..."
sync
hdiutil detach "$MOUNT_POINT" -force

# Convert to compressed read-only DMG
echo "Compressing DMG (UDZO)..."
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

# Notarize if enabled.
#
# The previous inline implementation passed --keychain-profile "$PROFILE_NAME",
# but PROFILE_NAME was never assigned anywhere in this script. Under `set -u`
# that would have aborted here. It was unreachable in practice because
# SIGN_CODE was hardcoded to 0.
if [ "$SIGN_CODE" = "1" ] && [ "$NOTARIZE" = "1" ]; then
    bash "$(dirname "$0")/notarize_macos.sh" "$FINAL_DMG"
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
