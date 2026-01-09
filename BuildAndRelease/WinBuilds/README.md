# Windows Build Scripts

This directory contains all Windows-specific build scripts for the Image Description Toolkit.

## Prerequisites

1. **Python 3.10+** with virtual environments
2. **Run setup script** from project root (one-time):
   ```batch
   winsetup.bat
   ```
3. **Inno Setup 6** (for installer creation): https://jrsoftware.org/isdl.php

## Quick Start

### Build All Applications

```batch
BuildAndRelease\WinBuilds\builditall_wx.bat
```

This builds all five IDT applications:
- `idt.exe` - CLI dispatcher
- `viewer.exe` - Workflow results browser
- `imagedescriber.exe` - Batch processing GUI
- `prompteditor.exe` - Prompt template editor
- `idtconfigure.exe` - Configuration manager

### Package All Executables

```batch
BuildAndRelease\WinBuilds\package_all_windows.bat
```

Collects all built executables to `dist_all/bin/`.

### Create Windows Installer

```batch
BuildAndRelease\WinBuilds\build_installer.bat
```

Creates `ImageDescriptionToolkit_Setup_v{version}.exe` in `dist_all/`.

## Individual Scripts

### `builditall_wx.bat`
Master build script that builds all five applications sequentially.

**Requirements:**
- Each app must have a `.winenv` directory (created by `winsetup.bat`)
- Each app must have `build_*_wx.bat` or `build_*.bat` in its directory

**Output:** Executables in each app's `dist/` folder

### `package_all_windows.bat`
Collects all built executables to a single distribution folder.

**Requirements:** All apps must be built first

**Output:** `dist_all/bin/` with all .exe files

### `build_installer.bat`
Creates Windows installer using Inno Setup.

**Requirements:**
- Inno Setup 6 installed
- All executables built and packaged
- `installer.iss` configuration file

**Output:** `dist_all/ImageDescriptionToolkit_Setup_v{version}.exe`

### `installer.iss`
Inno Setup configuration file defining:
- Installation directory
- File inclusions
- Start menu entries
- Uninstaller configuration
- Version information

## Full Workflow

```batch
cd C:\path\to\Image-Description-Toolkit

REM One-time setup
winsetup.bat

REM Build all applications
BuildAndRelease\WinBuilds\builditall_wx.bat

REM Package executables
BuildAndRelease\WinBuilds\package_all_windows.bat

REM Create installer
BuildAndRelease\WinBuilds\build_installer.bat
```

## Output Locations

- **Individual builds:** `<app>/dist/<App>.exe`
- **Packaged executables:** `dist_all/bin/`
- **Installer:** `dist_all/ImageDescriptionToolkit_Setup_v{version}.exe`

## Troubleshooting

### "Virtual environment not found"

Run setup from project root:
```batch
winsetup.bat
```

Or manually create for a specific app:
```batch
cd <app>
python -m venv .winenv
.winenv\Scripts\activate
pip install -r requirements.txt
```

### "wxPython not installed"

```batch
cd <app>
.winenv\Scripts\activate
pip install wxPython>=4.2.0
```

### "Inno Setup not found"

1. Install from https://jrsoftware.org/isdl.php
2. Or update path in `build_installer.bat` to match your installation

### Build fails with import errors

Verify all dependencies are installed:
```batch
cd <app>
.winenv\Scripts\activate
pip install -r requirements.txt
```

## Notes

- Windows uses `.winenv` directories (allows coexistence with macOS `.venv`)
- Each app has isolated dependencies via `requirements.txt`
- Scripts automatically change to project root before executing
- All GUI applications use wxPython (no Qt dependencies)
