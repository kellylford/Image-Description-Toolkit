# Build and Release Scripts

This directory contains all the build and release automation scripts for the Image Description Toolkit project.

## Quick Start

**Build everything and create release packages:**
```bash
BuildAndRelease/releaseitall.bat
```

**Build Windows installer:**
```bash
BuildAndRelease/build_installer.bat
```

## Script Overview

### Master Scripts

- **`releaseitall.bat`** - Complete release process (build → package → create master ZIP)
- **`builditall.bat`** - Build all four applications
- **`packageitall.bat`** - Package all applications into distribution ZIPs

### Individual Build Scripts

- **`build_idt.bat`** - Build IDT CLI executable (PyInstaller)
- **`build_installer.bat`** - Build Windows installer (Inno Setup)

### Individual Package Scripts

- **`package_idt.bat`** - Package IDT CLI into distribution ZIP

### Configuration Files

- **`installer.iss`** - Inno Setup configuration for Windows installer
- **`final_working.spec`** - PyInstaller specification for IDT CLI executable

### Linux/macOS Scripts

- **`build_executable.sh`** - Build IDT executable on Unix systems
- **`release.sh`** - Release automation for Unix systems

## How It Works

All scripts automatically change to the project root directory before executing, so they work correctly from the `BuildAndRelease/` subdirectory.

### Build Process

1. **Build Phase** (`builditall.bat`)
   - Builds `idt.exe` from Python source
   - Builds `viewer.exe` from Qt application
   - Builds `prompt_editor.exe` from Qt application
   - Builds `imagedescriber.exe` from Qt application

2. **Package Phase** (`packageitall.bat`)
   - Creates distribution ZIPs for each application
   - Includes executables, configs, documentation
   - Places all packages in `releases/` directory

3. **Master Package** (`releaseitall.bat`)
   - Creates `idt_v[VERSION].zip` containing all individual packages
   - Includes `install_idt.bat` for easy installation
   - Ready for GitHub release upload

### Installer Build

The Windows installer (`build_installer.bat`) requires:
- All four application ZIPs in `releases/` directory
- Inno Setup 6 installed at default location
- Runs from project root after changing directory

Output: `releases/ImageDescriptionToolkit_Setup_v3.0.1.exe`

## Prerequisites

### For Building Executables
- Python virtual environment with PyInstaller
- Qt for Python (PySide6) for GUI applications
- All project dependencies installed

### For Building Installer
- Inno Setup 6: https://jrsoftware.org/isdl.php
- All distribution packages built first

## Usage Examples

**Full release build:**
```bash
cd /path/to/Image-Description-Toolkit
BuildAndRelease/releaseitall.bat
```

**Build only IDT CLI:**
```bash
cd /path/to/Image-Description-Toolkit
BuildAndRelease/build_idt.bat
```

**Build installer after packages are ready:**
```bash
cd /path/to/Image-Description-Toolkit
BuildAndRelease/build_installer.bat
```

## Output Locations

All build outputs go to the project root directories:

- **Executables:** `dist/`, `viewer/dist/`, `prompt_editor/dist/`, `imagedescriber/dist/`
- **Packages:** `releases/`
- **Installer:** `releases/ImageDescriptionToolkit_Setup_v3.0.1.exe`

## Troubleshooting

**"Virtual environment not found"**
- Ensure `.venv` exists in project root and GUI app directories
- Run: `python -m venv .venv` and install requirements

**"PyInstaller not installed"**
- Activate venv and run: `pip install pyinstaller`

**"Inno Setup not found"**
- Install from https://jrsoftware.org/isdl.php
- Or update `INNO_PATH` in `build_installer.bat`

**"Package not found"**
- Run `BuildAndRelease/releaseitall.bat` to build everything
- Or run build and package steps individually

## Notes

- Scripts use relative paths and automatically change to project root
- All scripts can be run from anywhere in the project
- Windows batch files use `cd /d "%~dp0.."` to find project root
- PyInstaller spec file uses `../` paths for all sources
