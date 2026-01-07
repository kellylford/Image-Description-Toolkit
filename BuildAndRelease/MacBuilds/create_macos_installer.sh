#!/bin/bash
# ============================================================================
# Create macOS .pkg Installer for Image Description Toolkit
# ============================================================================
# Creates a macOS package installer that installs:
#   - idt CLI tool to /usr/local/bin/idt
#   - GUI applications to /Applications/
#
# Requirements:
#   - pkgbuild (included with Xcode Command Line Tools)
#   - productbuild (included with Xcode Command Line Tools)
#   - All applications must be built first
# ============================================================================

set -e  # Exit on error
set -u  # Exit on undefined variable

echo "========================================================================"
echo "Creating macOS .pkg Installer for IDT"
echo "========================================================================"
echo ""

# Change to project root
# Change to project root (now two levels up since we're in MacBuilds/)
cd "$(dirname "$0")/../.."

# Version information
VERSION=$(cat VERSION 2>/dev/null || echo "1.0.0")
INSTALL_NAME="IDT-${VERSION}"

echo "Building installer for version: $VERSION"
echo ""

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
STAGE_DIR="BuildAndRelease/MacBuilds/pkg_staging"
rm -rf "$STAGE_DIR"
mkdir -p "$STAGE_DIR/usr/local/bin"
mkdir -p "$STAGE_DIR/Applications"

# Copy CLI tool
echo "Copying CLI tool..."
cp "dist/idt" "$STAGE_DIR/usr/local/bin/idt"
chmod +x "$STAGE_DIR/usr/local/bin/idt"

# Copy GUI applications
echo "Copying GUI applications..."
cp -R "viewer/dist/viewer.app" "$STAGE_DIR/Applications/"
cp -R "imagedescriber/dist/imagedescriber.app" "$STAGE_DIR/Applications/"
cp -R "prompt_editor/dist/prompteditor.app" "$STAGE_DIR/Applications/"
cp -R "idtconfigure/dist/idtconfigure.app" "$STAGE_DIR/Applications/"

# Create component package
echo "Creating component package..."
PKG_DIR="BuildAndRelease/MacBuilds/pkg_output"
mkdir -p "$PKG_DIR"

pkgbuild \
    --root "$STAGE_DIR" \
    --identifier "com.idt.toolkit" \
    --version "$VERSION" \
    --install-location "/" \
    "$PKG_DIR/${INSTALL_NAME}-component.pkg"

# Create distribution XML
echo "Creating distribution file..."
cat > "$PKG_DIR/distribution.xml" << EOF
<?xml version="1.0" encoding="utf-8"?>
<installer-gui-script minSpecVersion="2">
    <title>Image Description Toolkit</title>
    <organization>com.idt</organization>
    <domains enable_localSystem="true"/>
    <options customize="never" require-scripts="false" hostArchitectures="arm64,x86_64"/>
    
    <welcome file="welcome.html" mime-type="text/html"/>
    <license file="license.txt"/>
    <readme file="readme.html" mime-type="text/html"/>
    
    <pkg-ref id="com.idt.toolkit"/>
    
    <options customize="never" require-scripts="false"/>
    
    <choices-outline>
        <line choice="default">
            <line choice="com.idt.toolkit"/>
        </line>
    </choices-outline>
    
    <choice id="default"/>
    
    <choice id="com.idt.toolkit" visible="false">
        <pkg-ref id="com.idt.toolkit"/>
    </choice>
    
    <pkg-ref id="com.idt.toolkit" version="$VERSION" onConclusion="none">
        ${INSTALL_NAME}-component.pkg
    </pkg-ref>
</installer-gui-script>
EOF

# Create welcome message
cat > "$PKG_DIR/welcome.html" << EOF
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: -apple-system, sans-serif; margin: 20px; }
        h1 { color: #333; }
    </style>
</head>
<body>
    <h1>Welcome to Image Description Toolkit</h1>
    <p>This installer will install the following applications:</p>
    <ul>
        <li><strong>idt</strong> - Command-line toolkit (/usr/local/bin/idt)</li>
        <li><strong>Viewer</strong> - Workflow results browser</li>
        <li><strong>ImageDescriber</strong> - Batch processing GUI</li>
        <li><strong>Prompt Editor</strong> - Prompt template editor</li>
        <li><strong>IDT Configure</strong> - Configuration manager</li>
    </ul>
    <p>All GUI applications will be installed to your Applications folder.</p>
    <p><strong>Accessibility:</strong> All applications are fully accessible with VoiceOver and keyboard navigation.</p>
</body>
</html>
EOF

# Create license file
if [ -f "LICENSE" ]; then
    cp LICENSE "$PKG_DIR/license.txt"
else
    cat > "$PKG_DIR/license.txt" << EOF
Image Description Toolkit License

See project documentation for full license terms.
EOF
fi

# Create readme
cat > "$PKG_DIR/readme.html" << EOF
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: -apple-system, sans-serif; margin: 20px; }
        h2 { color: #333; }
        code { background: #f0f0f0; padding: 2px 6px; border-radius: 3px; }
    </style>
</head>
<body>
    <h2>Getting Started</h2>
    <p>After installation, you can:</p>
    <ul>
        <li>Run <code>idt --help</code> from Terminal to see CLI options</li>
        <li>Launch applications from your Applications folder</li>
        <li>Open Viewer to browse existing workflow results</li>
        <li>Use ImageDescriber for batch processing images</li>
    </ul>
    
    <h2>Requirements</h2>
    <ul>
        <li>macOS 10.13 (High Sierra) or later</li>
        <li>For AI features: Ollama, OpenAI API key, or Anthropic API key</li>
    </ul>
    
    <h2>Accessibility</h2>
    <p>All applications support:</p>
    <ul>
        <li>Full VoiceOver compatibility</li>
        <li>Keyboard-only navigation</li>
        <li>WCAG 2.2 AA compliance</li>
    </ul>
    
    <h2>Support</h2>
    <p>For documentation and support, see the project repository.</p>
</body>
</html>
EOF

# Build final installer package
echo "Building final installer package..."
productbuild \
    --distribution "$PKG_DIR/distribution.xml" \
    --package-path "$PKG_DIR" \
    --resources "$PKG_DIR" \
    "BuildAndRelease/MacBuilds/${INSTALL_NAME}.pkg"

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================================================"
    echo "INSTALLER CREATED SUCCESSFULLY"
    echo "========================================================================"
    echo "Package: BuildAndRelease/MacBuilds/${INSTALL_NAME}.pkg"
    echo ""
    echo "To install: Double-click the .pkg file"
    echo "To test:    sudo installer -pkg BuildAndRelease/MacBuilds/${INSTALL_NAME}.pkg -target /"
    echo ""
    echo "NOTE: For distribution, you should code sign the package:"
    echo "  productsign --sign 'Developer ID Installer: Your Name' \\"
    echo "    BuildAndRelease/MacBuilds/${INSTALL_NAME}.pkg \\"
    echo "    BuildAndRelease/MacBuilds/${INSTALL_NAME}-signed.pkg"
    echo ""
else
    echo ""
    echo "ERROR: Failed to create installer package"
    exit 1
fi

# Clean up staging
echo "Cleaning up..."
rm -rf "$STAGE_DIR"

exit 0
