# Build System Reference - wxPython Version

## Overview

The Image Description Toolkit build system supports creating distributable packages for both Windows and macOS. All five applications use wxPython for GUI components.

## Applications

1. **idt** - Command-line interface (no GUI framework)
2. **Viewer** - Workflow results browser (wxPython)
3. **PromptEditor** - Visual prompt template editor (wxPython)
4. **ImageDescriber** - Batch processing GUI (wxPython)
5. **IDTConfigure** - Configuration management (wxPython)

## Quick Start

### Windows

```batch
REM Build all applications
BuildAndRelease\builditall_wx.bat

REM Collect executables to dist_all\bin\
BuildAndRelease\package_all_windows.bat

REM Create Windows installer (Inno Setup required)
BuildAndRelease\build_installer.bat
```

### macOS

```bash
# Build all applications (double-click in Finder or run in Terminal)
BuildAndRelease/builditall_wx.command

# Collect .app bundles to MacBuilds/dist_all/Applications/
BuildAndRelease/MacBuilds/package_all_macos.command

# Create .dmg installer
BuildAndRelease/MacBuilds/create_macos_dmg.command
```

## Build Scripts by Application

### Individual App Builds

Each application has three build scripts in its directory:

| Application | Windows | macOS (Terminal) | macOS (Finder) |
|------------|---------|------------------|----------------|
| idt | `build_idt.bat` | `build_idt.sh` | `build_idt_macos.command` |
| Viewer | `build_viewer_wx.bat` | `build_viewer_wx.sh` | `build_viewer_macos.command` |
| PromptEditor | `build_prompt_editor_wx.bat` | `build_prompt_editor_wx.sh` | `build_prompt_editor_macos.command` |
| ImageDescriber | `build_imagedescriber_wx.bat` | `build_imagedescriber_wx.sh` | `build_imagedescriber_macos.command` |
| IDTConfigure | `build_idtconfigure_wx.bat` | `build_idtconfigure_wx.sh` | `build_idtconfigure_macos.command` |

**Note**: `.command` files can be double-clicked in macOS Finder. `.sh` files require Terminal.

### Master Build Scripts

Located in `BuildAndRelease/`:

| Purpose | Windows | macOS (Terminal) | macOS (Finder) |
|---------|---------|------------------|----------------|
| Build all apps | `builditall_wx.bat` | `builditall_wx.sh` | `builditall_wx.command` |
| Package all apps | `package_all_windows.bat` | (See MacBuilds below) | |

Located in `BuildAndRelease/MacBuilds/`:

| Purpose | macOS (Terminal) | macOS (Finder) |
|---------|------------------|----------------|
| Package all apps | `package_all_macos.sh` | `package_all_macos.command` |
| Create DMG | `create_macos_dmg.sh` | `create_macos_dmg.command` |

## Output Locations

### Windows

After `builditall_wx.bat`:
```
idt/dist/idt.exe
viewer/dist/Viewer.exe
prompt_editor/dist/PromptEditor.exe
imagedescriber/dist/ImageDescriber.exe
idtconfigure/dist/IDTConfigure.exe
```

After `package_all_windows.bat`:
```
BuildAndRelease/dist_all/bin/
  ├── idt.exe
  ├── Viewer.exe
  ├── PromptEditor.exe
  ├── ImageDescriber.exe
  └── IDTConfigure.exe
```

### macOS

After `builditall_wx.sh`:
```
idt/dist/idt
viewer/dist/Viewer.app
prompt_editor/dist/PromptEditor.app
imagedescriber/dist/ImageDescriber.app
idtconfigure/dist/IDTConfigure.app
```

After `package_all_macos.sh`:
```
BuildAndRelease/MacBuilds/dist_all/
  ├── idt (CLI executable)
  └── Applications/
      ├── Viewer.app
      ├── PromptEditor.app
      ├── ImageDescriber.app
      └── IDTConfigure.app
```

After `create_macos_dmg.sh`:
```
BuildAndRelease/MacBuilds/dist_macos/
  └── IDT-{VERSION}.dmg
```

## Virtual Environments

Each GUI application requires its own virtual environment with wxPython:

```bash
# Setup example for Viewer
cd viewer
python -m venv .venv

# Windows
.venv\Scripts\activate
pip install -r requirements.txt

# macOS/Linux
source .venv/bin/activate
pip install -r requirements.txt
```

**Note**: The build scripts automatically activate the correct virtual environment.

## Prerequisites

### Windows
- Python 3.10+
- Virtual environments for each GUI app (`.venv` in each app directory)
- Inno Setup (for installer creation, optional)

### macOS
- Python 3.10+
- Virtual environments for each GUI app (`.venv` in each app directory)
- Xcode Command Line Tools (for code signing, optional)

## Distribution Workflow

### Windows

1. **Build**: `BuildAndRelease\builditall_wx.bat`
2. **Package**: `BuildAndRelease\package_all_windows.bat`
3. **Create Installer**: `BuildAndRelease\build_installer.bat` (optional)
4. **Test**: Run executables from `dist_all\bin\`
5. **Distribute**: Share `dist_all\` folder or installer

### macOS

1. **Build**: `BuildAndRelease/builditall_wx.command` (double-click or run in Terminal)
2. **Package**: `BuildAndRelease/MacBuilds/package_all_macos.command`
3. **Create DMG**: `BuildAndRelease/MacBuilds/create_macos_dmg.command`
4. **Test**: Mount DMG and test applications
5. **Code Sign** (optional but recommended for distribution):
   ```bash
   codesign --deep --force --verify --verbose \
     --sign "Developer ID Application: Your Name" \
     Viewer.app ImageDescriber.app PromptEditor.app IDTConfigure.app
   ```
6. **Distribute**: Share `.dmg` file

## Troubleshooting

### "Virtual environment not found"
- Ensure each GUI app has a `.venv` directory
- Run: `cd <app_dir> && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`

### "PyInstaller not found"
- Activate the correct virtual environment
- Run: `pip install pyinstaller`

### "wxPython not found"
- Activate the correct virtual environment
- Run: `pip install -r requirements.txt`

### macOS: ".command file won't run"
- Make executable: `chmod +x BuildAndRelease/builditall_wx.command`
- Or: Right-click → Open (first time only)

### Windows: "Build failed for app X"
- Check if `.venv\Scripts\activate.bat` exists in that app's directory
- Verify requirements.txt contains `wxPython>=4.2.0`
- Try building that app individually first

## Testing Builds

### Quick Test (Windows)
```batch
dist_all\bin\idt.exe version
dist_all\bin\Viewer.exe
dist_all\bin\ImageDescriber.exe
```

### Quick Test (macOS)
```bash
BuildAndRelease/MacBuilds/dist_all/idt version
open BuildAndRelease/MacBuilds/dist_all/Applications/Viewer.app
open BuildAndRelease/MacBuilds/dist_all/Applications/ImageDescriber.app
```

## Migration from PyQt6

The build system was updated from PyQt6 to wxPython. Changes include:

- **Old**: `build_viewer.bat` → **New**: `build_viewer_wx.bat`
- **Old**: `viewer.app` → **New**: `Viewer.app`
- **Old**: Single spec file per app → **New**: `*_wx.spec` for wxPython versions

The old `builditall.bat` has been updated to call the new `_wx` build scripts.

## Additional Resources

- **PyInstaller docs**: https://pyinstaller.org/
- **wxPython docs**: https://wxpython.org/
- **DMG creation guide**: See comments in `create_macos_dmg.sh`
- **Inno Setup**: https://jrsoftware.org/isinfo.php (Windows installer)
