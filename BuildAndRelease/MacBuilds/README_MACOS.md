# macOS Build System - README

This directory contains the complete macOS build infrastructure for Image Description Toolkit.

## Quick Start

### 1. Verify Setup
```bash
./verify_macos_build_structure.sh
```

### 2. Build All Applications
```bash
./builditall_macos.sh
```

### 3. Create Installer Package
```bash
# Option A: .pkg installer (system-wide)
./create_macos_installer.sh

# Option B: .dmg disk image (portable)
./create_macos_dmg.sh
```

## What Gets Built

1. **dist/idt** - Command-line interface (standalone binary)
2. **imagedescriber/dist/ImageDescriber.app** - Batch processing GUI with integrated:
   - Viewer Mode (workflow results browser)
   - Prompt Editor (Tools → Edit Prompts)
   - Configuration Manager (Tools → Configure Settings)

## Prerequisites

### System Requirements
- macOS 10.13+ (High Sierra or later)
- Python 3.8+
- Xcode Command Line Tools (for packaging):
  ```bash
  xcode-select --install
  ```

### Python Dependencies

Set up virtual environment for ImageDescriber:

```bash
# Main IDT (optional - uses system Python by default)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
deactivate

# ImageDescriber GUI
cd imagedescriber
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
deactivate
cd ..
```

## Build Scripts

### Master Build
- **builditall_macos.sh** - Builds both applications sequentially
  - Runs pre-build validation
  - Cleans PyInstaller cache
  - Builds each app in its virtual environment
  - Runs post-build validation

### Individual Builds
- **idt/build_idt.sh** - CLI tool only
- **imagedescriber/build_imagedescriber_wx.sh** - ImageDescriber GUI

### Installer Creation
- **create_macos_dmg.sh** - Creates .dmg disk image
  - Drag-and-drop installation
  - Portable app
  - Optional CLI installation script

### Utilities
- **verify_macos_build_structure.sh** - Verifies all files present
- **check_spec_completeness.py** - Validates PyInstaller specs
- **validate_build.py** - Tests built executables

## PyInstaller Spec Files

### CLI Tool
- **idt/idt.spec** - IDT command-line interface
  - Creates standalone binary (no .app bundle)
  - Bundles all scripts and dependencies
  - Console mode enabled

### GUI Application
- **imagedescriber/imagedescriber_wx.spec** - ImageDescriber with wxPython
  - Info.plist with accessibility metadata
  - Bundle identifier (com.idt.imagedescriber)
  - High resolution support (Retina)
  - Minimum macOS version (10.13)
  - NSAccessibility descriptions

## Accessibility Features

All builds include full accessibility support:

### Automatic (via PyQt6)
- VoiceOver compatibility
- Keyboard navigation
- High contrast mode
- Dynamic type support

### Custom (in source code)
- Accessible names on all widgets
- Accessible descriptions for complex controls
- Optimized tab order
- WCAG 2.2 AA compliance

## Architecture Support

All builds support both Intel and Apple Silicon:
- Auto-detects architecture at build time
- Native performance on M1/M2/M3 Macs
- Backward compatible with Intel Macs

## Testing

### Build Verification
```bash
# Check structure before building
./verify_macos_build_structure.sh

# After building, test CLI
dist/idt version
dist/idt --help

# Test GUI app with integrated modes
open imagedescriber/dist/ImageDescriber.app
# Switch between Editor Mode and Viewer Mode tabs
# Test Tools → Edit Prompts
# Test Tools → Configure Settings
```

### Accessibility Testing
```bash
# Enable VoiceOver
# System Preferences > Accessibility > VoiceOver
# Or press Cmd+F5

# Test keyboard navigation
# Tab through controls
# Arrow keys in lists
# Enter to activate
# Cmd+Q to quit
```

### Installer Testing
```bash
# .dmg disk image
open IDT-4.1.0.dmg
# Drag ImageDescriber.app to Applications
# Run CLI Tools/INSTALL_CLI.sh
idt version  # Should work from any directory
```

## Build Output

### Success Indicators
```
========================================================================
BUILD SUMMARY
========================================================================

BUILD COMPLETE
SUCCESS: All applications built successfully

--- Built Executable Version ---
IDT v3.6.0
Built: 2026-01-06
Commit: <hash>
Python: 3.14.2
--------------------------------
```

### Expected Sizes
- IDT CLI: ~80MB
- ImageDescriber.app: ~250MB (includes all integrated features)

## Code Signing (Optional)

For distribution, sign with Developer ID:

```bash
# Sign individual app
codesign --deep --force --verify --verbose \
  --sign "Developer ID Application: Your Name (TEAM_ID)" \
  imagedescriber/dist/ImageDescriber.app

# Sign DMG
codesign --force --sign "Developer ID Application: Your Name (TEAM_ID)" \
  IDT-4.1.0.dmg

# Notarize with Apple
xcrun notarytool submit IDT-4.1.0.dmg \
  --apple-id your@email.com \
  --team-id TEAM_ID \
  --wait

# Staple ticket
xcrun stapler staple IDT-4.1.0.dmg
```

## Troubleshooting

### Build Fails - Missing Dependencies
```bash
pip install pyinstaller
pip install -r requirements.txt
```

### Build Fails - Virtual Environment
```bash
cd <app_directory>
source .venv/bin/activate
pip install -r requirements.txt
```

### "Cannot open" or "App is damaged"
```bash
# Remove quarantine (for testing only)
xattr -cr imagedescriber/dist/ImageDescriber.app

# Or right-click > Open > Open (recommended)
```

### CLI Not in PATH
```bash
echo 'export PATH="/usr/local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

## Documentation

- **[BUILD_MACOS.md](../docs/BUILD_MACOS.md)** - Comprehensive build guide
- **[MACOS_USER_GUIDE.md](../docs/MACOS_USER_GUIDE.md)** - End-user installation guide
- **[MACOS_BUILD_IMPLEMENTATION.md](../docs/worktracking/MACOS_BUILD_IMPLEMENTATION.md)** - Technical implementation details

## Differences from Windows

| Feature | Windows | macOS |
|---------|---------|-------|
| Build Script | `.bat` | `.sh` |
| Executable | `.exe` | (none) or `.app` |
| Installer | (zip) | `.dmg` |
| CLI Install | User choice | `/usr/local/bin/` |
| GUI Install | Program Files | `/Applications/` |

## Maintenance

### Adding New Modules
1. Update `hiddenimports` in relevant spec file
2. Rebuild and test

### Version Updates
1. Update `../VERSION` file
2. Rebuild all apps
3. Update Info.plist versions in spec files
4. Regenerate installers

### Adding New Apps
1. Create `appname/build_appname.sh`
2. Create `appname/appname.spec`
3. Add to `builditall_macos.sh`
4. Update DMG script
5. Update documentation

## Support

For build issues:
1. Check build logs for errors
2. Verify dependencies installed
3. Test in development mode first
4. Review PyInstaller spec files
5. See main documentation

---

**Ready to build?** Run `./builditall_macos.sh` and grab a coffee! ☕

Build time: ~10 minutes on Apple Silicon, ~20 minutes on Intel
