# Session Summary: 2026-01-07
## Virtual Environment Setup for macOS

### Overview
Set up isolated virtual environments for all FIVE applications in the Image Description Toolkit, matching the Windows development pattern. This ensures clean dependency management and prevents pollution of the system Python environment.

### Changes Made

#### 1. Created/Updated Virtual Environments
Created `.venv` directories for all applications:
- **.venv** (root) - IDT CLI dispatcher (idt command)
- **viewer/.venv** - Image Description Viewer
- **imagedescriber/.venv** - ImageDescriber GUI
- **prompt_editor/.venv** - Prompt Editor
- **idtconfigure/.venv** - IDT Configuration Tool

Each virtual environment was created using Python 3.14.2 and populated with application-specific dependencies from their respective `requirements.txt` files.

#### 2. Updated Build Scripts
Modified build scripts to use isolated virtual environments:

**[viewer/build_viewer_macos.sh](viewer/build_viewer_macos.sh)**
- Added virtual environment creation check
- Updated to activate `.venv` before building
- Changed to use `pip install -r requirements.txt` instead of individual packages
- Now uses `python` instead of `python3` (from activated venv)

**[prompt_editor/build_prompt_editor_macos.sh](prompt_editor/build_prompt_editor_macos.sh)**
- Updated to install from `requirements.txt` instead of hardcoded packages
- Ensures consistent dependency versions

**[idtconfigure/build_idtconfigure_macos.sh](idtconfigure/build_idtconfigure_macos.sh)**
- Updated to install from `requirements.txt` instead of hardcoded packages
- Ensures pyinstaller is installed from requirements file

**Note:** [imagedescriber/build_imagedescriber_macos.sh](imagedescriber/build_imagedescriber_macos.sh) already used virtual environments correctly.

#### 3. Updated Requirements Files
**[idtconfigure/requirements.txt](idtconfigure/requirements.txt)**
- Added `pyinstaller>=6.0.0` to ensure build tool is included

**[imagedescriber/requirements.txt](imagedescriber/requirements.txt)**
- Added `piexif>=1.1.3` for EXIF metadata embedding in video frame extraction
- This was missing and would have caused video extraction to fail when trying to preserve GPS/date metadata

All other requirements files already had complete dependencies documented.

#### 4. Updated .gitignore
**[.gitignore](.gitignore)**
- Added `.venv/` pattern to ignore virtual environment directories
- Ensures app-specific virtual environments won't be committed to git

### System Python Environment
The default Python environment (Homebrew-managed Python 3.14.2) was assessed and found to be externally managed per PEP 668. Current packages in system Python:
- `pip==25.3`
- `wheel==0.45.1`
- `setuptools==80.9.0`
- Plus some Homebrew-installed packages (numpy, pydantic, etc.)

**Decision:** Did NOT attempt to clean system Python because:
1. macOS Python 3.14 is externally managed by Homebrew (PEP 668)
2. Attempting to modify could break system tools
3. All project work now uses isolated virtual environments
4. No user-site packages were found (`~/Library/Python/3.14/lib/python/site-packages/` doesn't exist)

This follows macOS best practices for Homebrew-managed Python installations.

### Testing Results
Verified all FIVE virtual environments are working correctly:
- ✓ .venv (root) - All IDT CLI dependencies verified:
  - Core: Pillow, ollama, openai, anthropic, psutil, piexif, PyInstaller
  - Video: opencv-python (cv2), numpy, piexif, exif_embedder module
  - HuggingFace/Florence-2: transformers (4.57.3), torch (2.9.1), torchvision, einops (0.8.1), timm (1.0.24)
  - VideoFrameExtractor successfully instantiates
- ✓ viewer/.venv - PyQt6 and dependencies available
- ✓ imagedescriber/.venv - PyQt6, anthropic, openai, ollama, opencv-python, piexif available
- ✓ prompt_editor/.venv - PyQt6, ollama available
- ✓ idtconfigure/.venv - PyQt6, PyInstaller available

**Build Testing (All 5 Applications):**
All applications successfully built from their new locations:
- ✅ **idt CLI** - 192 MB executable built from BuildAndRelease/MacBuilds/build_idt_macos.sh
  - Fixed path issues in final_working_macos.spec (updated all `../` to `../../`)
  - Successfully references all scripts, models, and analysis directories
- ✅ **Viewer** - viewer.app built from viewer/build_viewer_macos.sh
  - Added dist/build cleanup to prevent "directory not empty" errors
  - Successfully creates viewer.app bundle (38.7 MB)
- ✅ **ImageDescriber** - imagedescriber.app built from imagedescriber/build_imagedescriber_macos.sh
  - Added `cd "$(dirname "$0")"` to ensure correct working directory
  - Successfully creates imagedescriber.app bundle (82.4 MB)
- ✅ **Prompt Editor** - prompteditor.app built from prompt_editor/build_prompt_editor_macos.sh
  - Added `cd "$(dirname "$0")"` to ensure correct working directory
  - Successfully creates prompteditor.app bundle (34.9 MB)
- ✅ **IDTConfigure** - idtconfigure.app built from idtconfigure/build_idtconfigure_macos.sh
  - Added `cd "$(dirname "$0")"` to ensure correct working directory
  - Successfully creates idtconfigure.app bundle (28.3 MB)

### Technical Details

#### Virtual Environment Structure
Each application now has its own isolated Python environment:
```
viewer/.venv/
├── bin/
│   ├── activate
│   ├── pip
│   └── python -> python3.14
└── lib/python3.14/site-packages/
    └── [app-specific packages]
```

#### Build Workflow
The updated build process:
1. Check if `.venv` exists, create if needed
2. Activate virtual environment
3. Install dependencies from `requirements.txt`
4. Clean PyInstaller cache
5. Build executable using PyInstaller

#### Dependency Isolation
Each application's dependencies are now completely isolated:
- **idt (root .venv)**: Full toolkit dependencies - Pillow, requests, ollama, openai, anthropic, psutil, pillow-heif, piexif, beautifulsoup4, opencv-python, numpy, PyQt6, transformers, torch, torchvision, tqdm, pytest, pyinstaller
- **viewer**: PyQt6, Pillow, requests, ollama, beautifulsoup4, pyinstaller
- **imagedescriber**: PyQt6, Pillow, pillow-heif, opencv-python, numpy, piexif (NEW), AI providers (ollama, openai, anthropic), requests, beautifulsoup4, tqdm, pyinstaller
- **prompt_editor**: PyQt6, ollama, openai, anthropic, requests, beautifulsoup4, pyinstaller
- **idtconfigure**: PyQt6, pyinstaller

### Benefits
1. **Clean Dependency Management**: Each app has only the packages it needs
2. **No Conflicts**: Different apps can use different versions of the same package if needed
3. **Reproducible Builds**: Each app builds in a known, isolated environment
4. **Protected System**: System Python remains clean and unmodified
5. **Video Extraction Fixed**: Both CLI and GUI now have piexif for EXIF metadata embedding
6. **HuggingFace Support**: Florence-2 local vision model dependencies (transformers, torch, einops, timm) verified in root .venv

### Usage Instructions
Developers should:
- Never install packages to system Python
- Always work within the app-specific virtual environment when developing
- Build scripts automatically handle virtual environment activation
- Requirements files document all dependencies for each application

**Building Applications:**
- **From Terminal**: Run the `.sh` scripts directly (e.g., `./build_viewer_macos.sh`)
- **From Finder**: Double-click the `.command` files (e.g., `build_viewer_macos.command`)
- Both methods do the same thing - use whichever is more convenient

### Files Modified
- [viewer/build_viewer_macos.sh](viewer/build_viewer_macos.sh) - Added venv support, dist/build cleanup, and `cd` to script directory
- [prompt_editor/build_prompt_editor_macos.sh](prompt_editor/build_prompt_editor_macos.sh) - Updated to use requirements.txt, added dist/build cleanup, and `cd` to script directory
- [idtconfigure/build_idtconfigure_macos.sh](idtconfigure/build_idtconfigure_macos.sh) - Updated to use requirements.txt, added dist/build cleanup, and `cd` to script directory
- [imagedescriber/build_imagedescriber_macos.sh](imagedescriber/build_imagedescriber_macos.sh) - Added dist/build cleanup and `cd` to script directory
- [BuildAndRelease/MacBuilds/build_idt_macos.sh](BuildAndRelease/MacBuilds/build_idt_macos.sh) - Updated paths for MacBuilds location (`cd` goes up 2 levels)
- [BuildAndRelease/MacBuilds/builditall_macos.sh](BuildAndRelease/MacBuilds/builditall_macos.sh) - Fixed path to build_idt_macos.sh
- [BuildAndRelease/MacBuilds/final_working_macos.spec](BuildAndRelease/MacBuilds/final_working_macos.spec) - Updated all paths from `../` to `../../` for MacBuilds depth
- [idtconfigure/requirements.txt](idtconfigure/requirements.txt) - Added pyinstaller
- [imagedescriber/requirements.txt](imagedescriber/requirements.txt) - Added piexif for video frame extraction
- [.gitignore](.gitignore) - Added .venv/ pattern

### Files Created
**Finder-compatible .command launchers** (double-clickable):
- [BuildAndRelease/MacBuilds/build_idt_macos.command](BuildAndRelease/MacBuilds/build_idt_macos.command) - Launch IDT CLI build from Finder
- [BuildAndRelease/MacBuilds/builditall_macos.command](BuildAndRelease/MacBuilds/builditall_macos.command) - Build all 5 applications from Finder
- [BuildAndRelease/MacBuilds/create_macos_dmg.command](BuildAndRelease/MacBuilds/create_macos_dmg.command) - Create DMG installer from Finder
- [viewer/build_viewer_macos.command](viewer/build_viewer_macos.command) - Launch Viewer build from Finder
- [imagedescriber/build_imagedescriber_macos.command](imagedescriber/build_imagedescriber_macos.command) - Launch ImageDescriber build from Finder
- [prompt_editor/build_prompt_editor_macos.command](prompt_editor/build_prompt_editor_macos.command) - Launch Prompt Editor build from Finder
- [idtconfigure/build_idtconfigure_macos.command](idtconfigure/build_idtconfigure_macos.command) - Launch IDTConfigure build from Finder

Each `.command` file is a wrapper that calls the corresponding `.sh` script and keeps the terminal open after completion.

### Files Reorganized
**Created BuildAndRelease/MacBuilds/ subfolder** to organize macOS-specific build files:
- Moved all macOS build scripts (.sh) into MacBuilds/
- Moved all macOS .command launchers into MacBuilds/
- Moved final_working_macos.spec into MacBuilds/
- Moved README_MACOS.md into MacBuilds/
- Updated all path references in scripts to account for new location (one level deeper)

### Virtual Environments Created/Updated
- .venv/ (root - updated for idt CLI)
- viewer/.venv/ (new)
- imagedescriber/.venv/ (new)
- prompt_editor/.venv/ (new)
- idtconfigure/.venv/ (new)

---
**Session Date:** January 7, 2026  
**Agent:** Claude Sonnet 4.5  
**Status:** Complete ✓
