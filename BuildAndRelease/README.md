# Build and Release Scripts

This directory contains all the build and release automation scripts for the Image Description Toolkit project.

**All GUI applications now use wxPython.** See [BUILD_SYSTEM_REFERENCE.md](BUILD_SYSTEM_REFERENCE.md) for comprehensive documentation.

## Quick Start

### Windows

**Build all applications:**
```batch
BuildAndRelease\builditall_wx.bat
```

**Package all executables:**
```batch
BuildAndRelease\package_all_windows.bat
```

**Create Windows installer:**
```batch
BuildAndRelease\build_installer.bat
```

### macOS

**Build all applications (double-click or run in Terminal):**
```bash
BuildAndRelease/builditall_wx.command
```

**Package all .app bundles:**
```bash
BuildAndRelease/MacBuilds/package_all_macos.command
```

**Create .dmg installer:**
```bash
BuildAndRelease/MacBuilds/create_macos_dmg.command
```

## Script Overview

### Master Scripts (Windows)

- **`builditall_wx.bat`** - Build all five applications (wxPython version)
- **`package_all_windows.bat`** - Collect all executables to dist_all/bin/
- **`build_idt.bat`** - Build IDT CLI executable (PyInstaller)
- **`build_installer.bat`** - Build Windows installer (Inno Setup)

### Master Scripts (macOS)

Located in `MacBuilds/`:

- **`builditall_macos.command`** - Build all applications for macOS
- **`package_all_macos.command`** - Collect all .app bundles
- **`create_macos_dmg.command`** - Create .dmg installer

### Configuration Files

- **`installer.iss`** - Inno Setup configuration for Windows installer
- **`check_spec_completeness.py`** - Validates PyInstaller spec files
- **`validate_build.py`** - Post-build validation tool

### Documentation

- **`BUILD_SYSTEM_REFERENCE.md`** - Comprehensive build system documentation
- **`MacBuilds/README_MACOS.md`** - macOS-specific build instructions

## How It Works

### Windows Build Process

1. **Setup** (one-time): Run `winsetup.bat` from project root to create .winenv for each app
2. **Build**: Run `builditall_wx.bat` to build all executables
3. **Package**: Run `package_all_windows.bat` to collect to dist_all/bin/
4. **Installer**: Run `build_installer.bat` to create Windows installer

### macOS Build Process

1. **Setup** (one-time): Each app has its own .venv (created by individual build scripts)
2. **Build**: Run `builditall_wx.command` to build all .app bundles  
3. **Package**: Run `MacBuilds/package_all_macos.command` to collect apps
4. **DMG**: Run `MacBuilds/create_macos_dmg.command` to create installer

## Output Locations

### Windows
- Individual builds: `<app>/dist/<App>.exe`
- Packaged: `dist_all/bin/` (all executables together)
- Installer: `dist_all/ImageDescriptionToolkit_Setup_v{version}.exe`

### macOS
- Individual builds: `<app>/dist/<App>.app`
- Packaged: `MacBuilds/dist_all/Applications/` (all .app bundles)
- DMG: `MacBuilds/dist_all/ImageDescriptionToolkit-{version}.dmg`

## Prerequisites

### For Building Executables
- Python 3.10+ with virtual environments
- wxPython 4.2.0+ for GUI applications
- PyInstaller for creating executables
- All project dependencies installed

### Windows-Specific
- Run `winsetup.bat` from project root (one-time setup)
- Inno Setup 6 for creating installer: https://jrsoftware.org/isdl.php

### macOS-Specific
- Individual .venv created automatically by build scripts
- Xcode Command Line Tools (for some dependencies)
- create-dmg for DMG creation (installed by scripts if needed)

## Usage Examples

**Windows - Full workflow:**
```batch
cd /path/to/Image-Description-Toolkit
winsetup.bat
BuildAndRelease\builditall_wx.bat
BuildAndRelease\package_all_windows.bat
BuildAndRelease\build_installer.bat
```

**macOS - Full workflow:**
```bash
cd /path/to/Image-Description-Toolkit
BuildAndRelease/builditall_wx.command
BuildAndRelease/MacBuilds/package_all_macos.command
BuildAndRelease/MacBuilds/create_macos_dmg.command
```

**Build only IDT CLI:**
```bash
BuildAndRelease/build_idt.bat    # Windows
idt/build_idt.sh                 # macOS
```

## Troubleshooting

**Windows: "Virtual environment not found"**
- Run `winsetup.bat` from project root to create all .winenv directories
- Alternatively, manually create for specific app: `cd <app> && python -m venv .winenv && .winenv\Scripts\activate && pip install -r requirements.txt`

**macOS: "Virtual environment not found"**
- Individual build scripts create .venv automatically
- Or manually: `cd <app> && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`

**"wxPython not installed"**
- Windows: Activate .winenv and run `pip install wxPython>=4.2.0`
- macOS: Activate .venv and run `pip install wxPython>=4.2.0`

**"Inno Setup not found" (Windows only)**
- Install from https://jrsoftware.org/isdl.php
- Or update path in `build_installer.bat`

**macOS .app won't open: "damaged or can't be verified"**
- Run: `xattr -cr <path-to-app>`
- This removes quarantine attribute from unsigned app

## Notes

- **Virtual Environments:**
  - Windows: `.winenv` directories (allows coexistence with macOS .venv)
  - macOS: `.venv` directories
- **Cross-Platform Development:**
  - Same project directory can have both .venv (macOS) and .winenv (Windows)
  - See `WINDOWS_SETUP.md` for details on running Windows in VM on Mac
- Scripts automatically change to project root before executing
- Each app has its own isolated virtual environment and requirements.txt

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
