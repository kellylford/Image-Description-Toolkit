# Building Image Description Toolkit for macOS

This guide covers building native macOS versions of all IDT applications and creating distribution packages.

## Overview

The Image Description Toolkit consists of five applications:

1. **idt** - Command-line interface (standalone binary)
2. **Viewer** - Workflow results browser (PyQt6 .app bundle)
3. **ImageDescriber** - Batch image processing GUI (PyQt6 .app bundle)
4. **Prompt Editor** - AI prompt template editor (PyQt6 .app bundle)
5. **IDT Configure** - Configuration management (PyQt6 .app bundle)

## Prerequisites

### System Requirements
- macOS 10.13 (High Sierra) or later
- Python 3.8 or later
- Xcode Command Line Tools (for packaging):
  ```bash
  xcode-select --install
  ```

### Python Dependencies
Each application has its own virtual environment:

```bash
# Main IDT (optional - can use system Python)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Viewer
cd viewer
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..

# ImageDescriber
cd imagedescriber
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..

# Prompt Editor
cd prompt_editor
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..

# IDT Configure
cd idtconfigure
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..
```

## Quick Start: Build Everything

Build all five applications with one command:

```bash
./BuildAndRelease/builditall_macos.sh
```

This will create:
- `dist/idt` - CLI tool
- `viewer/dist/viewer.app`
- `imagedescriber/dist/imagedescriber.app`
- `prompt_editor/dist/prompteditor.app`
- `idtconfigure/dist/idtconfigure.app`

## Building Individual Applications

### 1. IDT CLI Tool

```bash
./BuildAndRelease/build_idt_macos.sh
```

Output: `dist/idt` (standalone binary)

Test:
```bash
dist/idt version
dist/idt --help
```

### 2. Viewer

```bash
cd viewer
source .venv/bin/activate
./build_viewer_macos.sh
```

Output: `viewer/dist/viewer.app`

Test:
```bash
open viewer/dist/viewer.app
```

### 3. ImageDescriber

```bash
cd imagedescriber
source .venv/bin/activate
./build_imagedescriber_macos.sh
```

Output: `imagedescriber/dist/imagedescriber.app`

Test:
```bash
open imagedescriber/dist/imagedescriber.app
```

### 4. Prompt Editor

```bash
cd prompt_editor
source .venv/bin/activate
./build_prompt_editor_macos.sh
```

Output: `prompt_editor/dist/prompteditor.app`

Test:
```bash
open prompt_editor/dist/prompteditor.app
```

### 5. IDT Configure

```bash
cd idtconfigure
source .venv/bin/activate
./build_idtconfigure_macos.sh
```

Output: `idtconfigure/dist/idtconfigure.app`

Test:
```bash
open idtconfigure/dist/idtconfigure.app
```

## Consolidated Distribution Directory

After building all applications, the master build script **automatically consolidates** all outputs to:

```
dist_macos/
├── idt                    # CLI tool (25MB)
├── viewer.app             # Workflow browser (37MB)
├── prompteditor.app       # Prompt template editor (27MB)
├── imagedescriber.app     # Batch processing GUI (79MB)
└── idtconfigure.app       # Configuration manager (27MB)
```

This makes distribution easier - all built applications are in one location.

## Creating Distribution Packages

### Option 1: .pkg Installer (Recommended for System-Wide Install)

Creates a macOS package installer that installs:
- CLI tool to `/usr/local/bin/idt`
- GUI apps to `/Applications/`

```bash
# Build all apps first
./BuildAndRelease/builditall_macos.sh

# Create .pkg installer (uses dist_macos/ as source)
./BuildAndRelease/create_macos_installer.sh
```

Output: `BuildAndRelease/IDT-{version}.pkg`

**Installation:** Double-click the .pkg file

**Features:**
- Installs CLI tool system-wide
- Installs all apps to Applications folder
- Includes welcome/readme screens
- Accessibility metadata included

### Option 2: .dmg Disk Image (Recommended for Portable Install)

Creates a drag-and-drop disk image:

```bash
# Build all apps first
./BuildAndRelease/builditall_macos.sh

# Create .dmg disk image
./BuildAndRelease/create_macos_dmg.sh
```

Output: `BuildAndRelease/IDT-{version}.dmg`

**Installation:** 
1. Double-click .dmg to mount
2. Drag .app files to Applications folder
3. Run `INSTALL_CLI.sh` from "CLI Tools" folder for CLI access

**Features:**
- No admin password required (except for CLI install)
- Portable - can run from anywhere
- Includes README and install instructions
- Applications symlink for easy drag-and-drop

## Accessibility Features

All macOS builds include full accessibility support:

### Built-in Support (Automatic)
- **VoiceOver compatibility** - Native NSAccessibility through PyQt6
- **Keyboard navigation** - Full keyboard shortcuts and tab order
- **High contrast mode** - Respects system preferences
- **Dynamic type** - System font size preferences honored

### Tested Compatibility
- macOS VoiceOver screen reader
- Keyboard-only navigation (Tab, arrows, Enter, Cmd shortcuts)
- System accessibility preferences
- WCAG 2.2 AA conformance

### Testing Accessibility

Enable VoiceOver:
```bash
# System Preferences > Accessibility > VoiceOver
# Or press Cmd+F5
```

Test keyboard navigation:
- Tab through all controls
- Arrow keys for lists/tables
- Enter/Space to activate
- Cmd+shortcuts for menu items

## Code Signing (Optional but Recommended)

For distribution outside the Mac App Store, code sign your applications:

### Sign Individual Apps

```bash
codesign --deep --force --verify --verbose \
  --sign "Developer ID Application: Your Name (TEAM_ID)" \
  viewer/dist/viewer.app
  
# Repeat for other apps
```

### Sign CLI Tool

```bash
codesign --force --verify --verbose \
  --sign "Developer ID Application: Your Name (TEAM_ID)" \
  dist/idt
```

### Sign Package Installer

```bash
productsign \
  --sign "Developer ID Installer: Your Name (TEAM_ID)" \
  BuildAndRelease/IDT-{version}.pkg \
  BuildAndRelease/IDT-{version}-signed.pkg
```

### Notarization (Required for Gatekeeper)

For distribution, notarize with Apple:

```bash
# Upload for notarization
xcrun notarytool submit BuildAndRelease/IDT-{version}-signed.pkg \
  --apple-id your@email.com \
  --team-id TEAM_ID \
  --wait

# Staple notarization ticket
xcrun stapler staple BuildAndRelease/IDT-{version}-signed.pkg
```

## Architecture Support

All builds support both Intel and Apple Silicon:

- **Universal binaries:** PyInstaller auto-detects architecture
- **Native performance:** Runs natively on M1/M2/M3 Macs
- **Intel Macs:** Fully supported (10.13+)

To verify architecture:

```bash
file dist/idt
# Output should show: Mach-O 64-bit executable arm64 (or x86_64)

file viewer/dist/viewer.app/Contents/MacOS/viewer
```

## Troubleshooting

### Build Fails with Missing Dependencies

```bash
# Ensure virtual environment is activated
cd <app_directory>
source .venv/bin/activate
pip install -r requirements.txt
```

### PyQt6 Import Errors

```bash
# Reinstall PyQt6
pip uninstall PyQt6 PyQt6-Qt6 PyQt6-sip
pip install PyQt6
```

### "App is Damaged" Error

This occurs if the app isn't code signed. Options:
1. Code sign the app (recommended)
2. Remove quarantine attribute:
   ```bash
   xattr -cr viewer/dist/viewer.app
   ```

### CLI Tool Not Found After Install

Add `/usr/local/bin` to your PATH:

```bash
echo 'export PATH="/usr/local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### App Won't Open (Gatekeeper)

If unsigned:
```bash
# Right-click app, select "Open", then "Open" again
# Or disable Gatekeeper temporarily (not recommended):
sudo spctl --master-disable
```

## File Structure

```
BuildAndRelease/
  builditall_macos.sh           # Master build script
  build_idt_macos.sh            # Build CLI tool
  create_macos_installer.sh     # Create .pkg
  create_macos_dmg.sh           # Create .dmg
  final_working_macos.spec      # PyInstaller spec for CLI

viewer/
  build_viewer_macos.sh         # Build viewer
  viewer_macos.spec             # PyInstaller spec
  dist/viewer.app               # Built application

imagedescriber/
  build_imagedescriber_macos.sh
  imagedescriber_macos.spec
  dist/imagedescriber.app

prompt_editor/
  build_prompt_editor_macos.sh
  prompteditor_macos.spec
  dist/prompteditor.app

idtconfigure/
  build_idtconfigure_macos.sh
  idtconfigure_macos.spec
  dist/idtconfigure.app
```

## Development vs Production

### Development Mode
Run as Python scripts:
```bash
python3 scripts/workflow.py
python3 viewer/viewer.py
```

### Production Mode
Run as frozen executables:
```bash
dist/idt workflow
open viewer/dist/viewer.app
```

All code uses `getattr(sys, 'frozen', False)` to detect mode and adjust paths accordingly.

## Differences from Windows Build

| Feature | Windows | macOS |
|---------|---------|-------|
| CLI extension | `.exe` | (none) |
| GUI package | `.exe` | `.app` bundle |
| Path separator | `\` | `/` |
| Virtual env | `.venv\Scripts\` | `.venv/bin/` |
| System install | Program Files | `/Applications/` |
| CLI install | (varies) | `/usr/local/bin/` |
| Installer | `.msi` / `.exe` | `.pkg` / `.dmg` |
| Code signing | Authenticode | Developer ID |

## Best Practices

1. **Always build all apps together** - Ensures version consistency
2. **Test in clean environment** - Use separate user account or VM
3. **Code sign before distribution** - Prevents Gatekeeper issues
4. **Test with VoiceOver** - Ensure accessibility before release
5. **Include README in packages** - Users need installation instructions
6. **Version consistently** - Update VERSION file before building

## Next Steps

After building:

1. **Test thoroughly** - See [Testing Checklist](#testing-checklist)
2. **Create release notes** - Document changes
3. **Code sign** - If distributing publicly
4. **Notarize** - Required for Gatekeeper acceptance
5. **Upload release** - GitHub releases or distribution site

## Testing Checklist

- [ ] CLI tool runs: `dist/idt version`
- [ ] All apps launch without errors
- [ ] VoiceOver announces app name and controls
- [ ] Keyboard navigation works (Tab, arrows, Enter)
- [ ] File operations work (open, save, export)
- [ ] AI providers connect (if configured)
- [ ] Workflow creation and monitoring
- [ ] Configuration saves persist
- [ ] Install/uninstall cleanly

## Support

For issues specific to macOS builds:
1. Check build logs for errors
2. Verify Python dependencies installed
3. Test in development mode first
4. Check PyInstaller spec files
5. Review accessibility with VoiceOver

See main project documentation for feature-specific support.
