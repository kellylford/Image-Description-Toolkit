# Master Build and Package Scripts

**Location:** Root of repository  
**Purpose:** Build and package all four applications in one command

---

## Quick Start

### Complete Release (Build + Package):
```bash
releaseitall.bat
```

### Build Everything:
```bash
builditall.bat
```

### Package Everything:
```bash
packageitall.bat
```

### Typical Workflow:
```bash
# One command does it all!
releaseitall.bat

# Or step by step:
builditall.bat       # Build first
packageitall.bat     # Package after
```

---

## What Gets Built

### 1. IDT (Main Toolkit)
- **Build script:** `build_idt.bat`
- **Output:** `dist/idt.exe`
- **Uses:** Root Python environment or `.venv`

### 2. Viewer
- **Build script:** `viewer/build_viewer.bat`
- **Output:** `viewer/dist/viewer_<arch>.exe`
- **Uses:** `viewer/.venv` virtual environment

### 3. Prompt Editor
- **Build script:** `prompt_editor/build_prompt_editor.bat`
- **Output:** `prompt_editor/dist/prompt_editor_<arch>.exe`
- **Uses:** `prompt_editor/.venv` virtual environment

### 4. ImageDescriber
- **Build script:** `imagedescriber/build_imagedescriber.bat`
- **Output:** `imagedescriber/dist/ImageDescriber_<arch>.exe`
- **Uses:** `imagedescriber/.venv` virtual environment

---

## What Gets Packaged

### 1. IDT Distribution
- **Package script:** `package_idt.bat`
- **Output:** `releases/ImageDescriptionToolkit_v[VERSION].zip`
- **Contains:** idt.exe, bat files, docs, all distribution files

### 2. Viewer Distribution
- **Package script:** `viewer/package_viewer.bat`
- **Output:** `releases/viewer_v[VERSION]_[ARCH].zip`
- **Contains:** viewer.exe, README.txt, LICENSE.txt

### 3. Prompt Editor Distribution
- **Package script:** `prompt_editor/package_prompt_editor.bat`
- **Output:** `releases/prompt_editor_v[VERSION]_[ARCH].zip`
- **Contains:** prompt_editor.exe, README.txt, LICENSE.txt

### 4. ImageDescriber Distribution
- **Package script:** `imagedescriber/package_imagedescriber.bat`
- **Output:** `releases/imagedescriber_v[VERSION]_[ARCH].zip`
- **Contains:** ImageDescriber.exe, README.txt, LICENSE.txt, setup files

---

## Prerequisites

### Before First Build:

1. **Set up virtual environments for GUI apps:**
   ```bash
   # Viewer
   cd viewer
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   deactivate
   
   # Prompt Editor
   cd ../prompt_editor
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   deactivate
   
   # ImageDescriber
   cd ../imagedescriber
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   deactivate
   ```

2. **Install main IDT dependencies:**
   ```bash
   cd ..
   pip install -r requirements.txt
   pip install pyinstaller
   ```

---

## Build Process Flow

### builditall.bat does:

1. ✅ Builds IDT using `build_idt.bat`
2. ✅ Activates `viewer/.venv` and builds viewer
3. ✅ Activates `prompt_editor/.venv` and builds prompt editor
4. ✅ Activates `imagedescriber/.venv` and builds imagedescriber
5. ✅ Deactivates each venv after building
6. ✅ Shows summary of what succeeded/failed

### packageitall.bat does:

1. ✅ Packages IDT using `package_idt.bat`
2. ✅ Packages viewer and moves ZIP to `releases/`
3. ✅ Packages prompt editor and moves ZIP to `releases/`
4. ✅ Packages imagedescriber and moves ZIP to `releases/`
5. ✅ Shows all packages in `releases/` directory

---

## Output Directory Structure

After running both scripts:

```
releases/
  ├── ImageDescriptionToolkit_v[VERSION].zip          (IDT main package)
  ├── viewer_v[VERSION]_arm64.zip                     (Viewer)
  ├── prompt_editor_v[VERSION]_arm64.zip              (Prompt Editor)
  └── imagedescriber_v[VERSION]_arm64.zip             (ImageDescriber)
```

**All packages in one place!** ✅

---

## Error Handling

### If a build fails:

The script will:
- ✅ Continue building other apps
- ✅ Count total errors
- ✅ Show which builds failed
- ✅ Still create packages for successful builds

### Common issues:

**"Virtual environment not found"**
- Solution: Set up the venv for that app (see Prerequisites)

**"Build failed"**
- Solution: Check the error output, usually missing dependencies
- Fix: `cd <app> && .venv\Scripts\activate && pip install -r requirements.txt`

**"Packaging failed"**
- Solution: Build the app first with `builditall.bat`

---

## Individual Build/Package

If you only want to build/package one app:

```bash
# Just IDT
build_idt.bat
package_idt.bat

# Just Viewer
cd viewer
.venv\Scripts\activate
build_viewer.bat
package_viewer.bat
deactivate

# Just Prompt Editor
cd prompt_editor
.venv\Scripts\activate
build_prompt_editor.bat
package_prompt_editor.bat
deactivate

# Just ImageDescriber
cd imagedescriber
.venv\Scripts\activate
build_imagedescriber.bat
package_imagedescriber.bat
deactivate
```

---

## Typical Workflow

### Full Release Process (RECOMMENDED):

```bash
# 1. Update VERSION file
echo 1.2.3 > VERSION

# 2. Build and package everything in one command
releaseitall.bat

# 3. Verify packages in releases/ directory
dir releases\*.zip

# 4. Upload to GitHub
# All ZIPs are ready in releases/ directory
```

### Step-by-Step Process:

```bash
# 1. Update VERSION file
echo 1.2.3 > VERSION

# 2. Build all applications
builditall.bat

# 3. Test executables
dist\idt.exe --version
viewer\dist\viewer_arm64.exe
prompt_editor\dist\prompt_editor_arm64.exe
imagedescriber\dist\ImageDescriber_arm64.exe

# 4. Package all applications
packageitall.bat

# 5. Upload releases
# All ZIPs are in releases/ directory ready to upload to GitHub
```

### Quick Test Build:

```bash
# Build only (no packaging)
builditall.bat

# Test manually
# Then package when ready
packageitall.bat
```

---

## Time Estimates

**releaseitall.bat:** ~10-15 minutes (complete build + package)
- Fully automated, no prompts
- Runs builditall.bat + packageitall.bat

**builditall.bat:** ~5-10 minutes (depending on system)
- IDT: ~2-3 minutes
- Viewer: ~1-2 minutes
- Prompt Editor: ~1 minute
- ImageDescriber: ~2-3 minutes
- No user interaction required

**packageitall.bat:** ~1-2 minutes
- Mostly file copying and ZIP creation
- Very fast
- No prompts

**Total release time:** ~10-15 minutes from start to finish ✅  
**User interaction:** NONE - Completely automated ✅

---

## Benefits

✅ **One command for complete release** - `releaseitall.bat`  
✅ **No user prompts** - Completely automated  
✅ **All releases in one directory** - `releases/`  
✅ **Automatic venv activation/deactivation**  
✅ **Error tracking across all builds**  
✅ **Continues on non-fatal errors**  
✅ **Clear status messages**  
✅ **Perfect for CI/CD workflows**

---

## Status Messages

The scripts show clear status:
- `[1/4] Building IDT...` - Progress indicator
- `SUCCESS: IDT built successfully` - Build succeeded
- `ERROR: Viewer build failed!` - Build failed
- `BUILD SUMMARY` - Final results
- `All packages in releases\` - Where to find outputs

---

**Ready to use!** Just run `builditall.bat` followed by `packageitall.bat` and you'll have all four distribution packages in the `releases/` directory. 🚀
