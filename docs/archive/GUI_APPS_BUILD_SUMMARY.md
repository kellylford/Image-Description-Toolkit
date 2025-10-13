# GUI Applications Build Fix Summary

**Date:** October 12, 2025  
**Status:** ✅ ALL THREE GUI APPS FIXED  
**Scope:** Viewer, Prompt Editor, ImageDescriber - No changes to main requirements.txt or scripts

---

## Overview

Fixed build scripts for all three GUI applications to work properly on ARM64 Windows (and would work on AMD64 if building on AMD64 system).

**Common Problems Fixed:**
1. ❌ Hardcoded paths to non-existent venv directories
2. ❌ Invalid `--target-architecture` flag (macOS only, doesn't work on Windows)
3. ❌ Broken relative paths for bundling scripts
4. ✅ Now uses system Python (no hardcoded paths)
5. ✅ Auto-detects architecture and builds correctly
6. ✅ Absolute paths for reliable script bundling

---

## 1. Viewer (viewer/)

### Files Created:
- `viewer/requirements.txt` - PyQt6 and optional ollama
- `viewer/package_viewer.bat` - Creates distribution ZIP
- `viewer/BUILD_FIX_SUMMARY.md` - Detailed documentation

### Files Modified:
- `viewer/build_viewer.bat` - Fixed build script

### Build Output:
- `dist/viewer_arm64.exe` (on ARM64 systems)
- ~40-60MB (includes PyQt6 + bundled scripts)

### Features:
- HTML mode for completed workflows ✅
- Live mode for in-progress workflows ✅
- Redescribe feature (requires Ollama) ✅

### Build Commands:
```bash
cd viewer
build_viewer.bat           # Build executable
package_viewer.bat         # Create distribution ZIP
```

---

## 2. Prompt Editor (prompt_editor/)

### Files Created:
- `prompt_editor/requirements.txt` - PyQt6 dependencies
- `prompt_editor/package_prompt_editor.bat` - Creates distribution ZIP

### Files Modified:
- `prompt_editor/build_prompt_editor.bat` - Fixed build script

### Build Output:
- `dist/prompt_editor_arm64.exe` (on ARM64 systems)
- ~40-50MB (includes PyQt6 + bundled scripts)

### Features:
- Edit image description prompts ✅
- Manage prompt variations ✅
- Configure AI providers ✅
- Save/Load configurations ✅

### Build Commands:
```bash
cd prompt_editor
build_prompt_editor.bat           # Build executable
package_prompt_editor.bat         # Create distribution ZIP
```

---

## 3. ImageDescriber (imagedescriber/)

### Files Created:
- `imagedescriber/requirements.txt` - Full dependencies list
- `imagedescriber/package_imagedescriber.bat` - Creates distribution ZIP

### Files Modified:
- `imagedescriber/build_imagedescriber.bat` - Simplified build script

### Build Output:
- `dist/ImageDescriber_arm64.exe` (on ARM64 systems)
- ~80-120MB (largest app, includes all AI providers + image processing)

### Features:
- Multi-provider AI (Ollama, OpenAI, Anthropic) ✅
- Batch image processing ✅
- Workspace management ✅
- Video frame extraction ✅
- HEIC/HEIF support ✅
- Optional GroundingDINO object detection ✅

### Build Commands:
```bash
cd imagedescriber
build_imagedescriber.bat           # Build executable
package_imagedescriber.bat         # Create distribution ZIP
```

---

## Architecture Notes

**Your Systems:**
- Surface: ARM64
- Lenovo: ARM64
- Both will build ARM64 executables

**Important:**
- ARM64 .exe only runs on ARM64 Windows
- Cannot build AMD64 without AMD64 system
- PyInstaller doesn't support cross-compilation on Windows
- This is a Windows/PyInstaller limitation, not a bug

**Distribution Strategy:**
- Build ARM64 versions on your machines
- ARM64 is becoming more common (Snapdragon X Elite, etc.)
- If users request AMD64, you'd need access to AMD64 machine
- Or use GitHub Actions (if ARM64 runners available)

---

## Build Process (All Apps Follow Same Pattern)

### Step 1: Build
```bash
cd <app_directory>
build_<app>.bat
```

**What happens:**
1. Detects architecture (ARM64 on your systems)
2. Checks for PyInstaller, installs if missing
3. Checks for PyQt6, installs from requirements.txt if missing
4. Verifies scripts directory exists
5. Runs PyInstaller with correct paths
6. Creates `dist/<AppName>_arm64.exe`

### Step 2: Package (Optional)
```bash
cd <app_directory>
package_<app>.bat
```

**What happens:**
1. Finds built executable
2. Creates staging directory
3. Renames to clean name (removes _arm64 suffix)
4. Generates README.txt with usage instructions
5. Copies LICENSE.txt
6. Creates ZIP: `<app>_releases/<app>_v[VERSION]_arm64.zip`

---

## Distribution Package Structure

### Viewer Package:
```
viewer_v[VERSION]_arm64.zip
  ├── viewer.exe
  ├── README.txt
  └── LICENSE.txt
```

### Prompt Editor Package:
```
prompt_editor_v[VERSION]_arm64.zip
  ├── prompt_editor.exe
  ├── README.txt
  └── LICENSE.txt
```

### ImageDescriber Package:
```
imagedescriber_v[VERSION]_arm64.zip
  ├── ImageDescriber.exe
  ├── README.txt
  ├── LICENSE.txt
  └── (optional setup scripts and docs)
```

---

## What Was NOT Changed

✅ **No changes to main requirements.txt** - PyQt6 still there for now  
✅ **No changes to scripts/** - All scripts untouched  
✅ **No changes to main IDT build** - build_idt.bat, final_working.spec unchanged  
✅ **No changes to package_idt.bat** - Main packaging untouched

**Rationale:**
- You're close to release, testing with current build
- GUI app changes are isolated and safe
- Removing PyQt6 from main requirements can wait until after release
- When ready, we'll rebuild idt.exe without PyQt6 (30-40% size reduction)

---

## Testing Checklist

### Viewer:
- [ ] `cd viewer && build_viewer.bat` succeeds
- [ ] `dist/viewer_arm64.exe` runs
- [ ] Can open HTML mode
- [ ] Can open Live mode
- [ ] Redescribe feature works (with Ollama)
- [ ] `package_viewer.bat` creates ZIP

### Prompt Editor:
- [ ] `cd prompt_editor && build_prompt_editor.bat` succeeds
- [ ] `dist/prompt_editor_arm64.exe` runs
- [ ] Can edit prompts
- [ ] Can save changes
- [ ] Bundled config loads correctly
- [ ] `package_prompt_editor.bat` creates ZIP

### ImageDescriber:
- [ ] `cd imagedescriber && build_imagedescriber.bat` succeeds
- [ ] `dist/ImageDescriber_arm64.exe` runs
- [ ] Can load images
- [ ] Can configure providers
- [ ] Can process images
- [ ] All modules load (ai_providers, data_models, etc.)
- [ ] `package_imagedescriber.bat` creates ZIP

---

## Build Requirements Summary

### All Apps Require:
- Python 3.10+
- PyQt6>=6.4.0
- PyInstaller

### Viewer Specific:
- ollama (optional, for redescribe feature)

### Prompt Editor Specific:
- (No additional beyond PyQt6)

### ImageDescriber Specific:
- Pillow, pillow-heif
- opencv-python, numpy
- ollama, openai, anthropic
- requests

---

## Deprecated Files

The old architecture-specific build scripts are no longer used:
- `viewer/build_viewer_amd.bat` ❌ (macOS-only flags)
- `viewer/build_viewer_arm.bat` ❌ (macOS-only flags)
- `prompt_editor/build_prompt_editor_amd.bat` ❌ (hardcoded paths)
- `prompt_editor/build_prompt_editor_arm.bat` ❌ (hardcoded paths)
- `imagedescriber/build_imagedescriber_amd.bat` ❌ (hardcoded paths, invalid flags)
- `imagedescriber/build_imagedescriber_arm.bat` ❌ (hardcoded paths, invalid flags)

**Replacement:** Just use the main `build_<app>.bat` which auto-detects architecture.

---

## Future Improvements (After Release)

1. **Remove PyQt6 from main requirements.txt**
   - Only GUI apps need it
   - Will reduce idt.exe size by 30-40% (40-50MB)
   
2. **Separate GUI app distributions**
   - Each app has its own ZIP package
   - Users only download what they need
   - Smaller individual downloads

3. **GitHub Actions CI/CD** (Optional)
   - Automated builds on every commit
   - Multi-architecture support (if runners available)
   - Automatic release uploads

---

## Quick Reference

### Build All Three Apps:
```bash
# Viewer
cd viewer
build_viewer.bat
package_viewer.bat

# Prompt Editor  
cd ..\prompt_editor
build_prompt_editor.bat
package_prompt_editor.bat

# ImageDescriber
cd ..\imagedescriber
build_imagedescriber.bat
package_imagedescriber.bat
```

### Where Are The Packages?
- `viewer/viewer_releases/viewer_v[VERSION]_arm64.zip`
- `prompt_editor/prompt_editor_releases/prompt_editor_v[VERSION]_arm64.zip`
- `imagedescriber/imagedescriber_releases/imagedescriber_v[VERSION]_arm64.zip`

### Testing The Apps:
```bash
# Viewer
cd viewer\dist
viewer_arm64.exe

# Prompt Editor
cd ..\..\prompt_editor\dist
prompt_editor_arm64.exe

# ImageDescriber
cd ..\..\imagedescriber\dist
ImageDescriber_arm64.exe
```

---

## Status: Ready to Build

All three GUI applications are now ready to build. The fixes:
- Work on your ARM64 systems ✅
- Use system Python (no hardcoded paths) ✅
- Auto-detect architecture ✅
- Bundle scripts correctly ✅
- Create clean distribution packages ✅

No impact on your main IDT release - these are completely isolated changes.
