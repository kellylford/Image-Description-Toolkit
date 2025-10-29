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

## Versioning and Build Numbers

This project uses a simple, consistent build version format and logs it at the start of every workflow log:

- Format: `"<base> bldNNN"` (for example: `"3.5beta bld012"`)
- Base version comes from the top‑level `VERSION` file
- Build number source (in order of precedence):
   1. Environment variable `IDT_BUILD_NUMBER`
   2. GitHub Actions `GITHUB_RUN_NUMBER` (CI)
   3. Local counter in `build/BUILD_TRACKER.json` (per base version)

Implementation details:

- Module: `scripts/versioning.py`
   - `get_full_version()` returns the composed string (e.g., `"3.5beta bld007"`)
   - `log_build_banner(logger)` writes a standardized banner (Version, Commit, Mode, UTC time)
- Workflow: `scripts/workflow.py` logs the banner right after the logger is created
- CLI: `idt version` prints the full version, commit, and mode

Environment overrides (optional):

- `IDT_BUILD_BASE` — override base version (otherwise read from `VERSION`)
- `IDT_BUILD_NUMBER` — force a specific build number (useful for custom pipelines)

Local vs CI behavior:

- CI builds default to using `GITHUB_RUN_NUMBER` for the build number (no repo writes)
- Local builds increment a per‑base counter in `build/BUILD_TRACKER.json`
- Changing the base version in `VERSION` naturally resets the local counter for that base

Viewing the version:

```bash
idt version
```

Log banner example (at the top of workflow logs):

```
Image Description Toolkit
Version: 3.5beta bld012
Commit: abc1234
Mode: Dev
Start: 2025-10-29T01:23:45Z
```

Notes:

- No changes to your existing `releaseitall.bat` / `build_installer.bat` flow are required
- The version banner appears automatically in logs and the CLI version output
