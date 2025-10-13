# Issue: Viewer Build Fails for ARM64 and AMD64 - Separate Distribution Needed

## Status
🔴 **OPEN** - Build scripts broken, need redesign for multi-architecture support

## Priority
**MEDIUM** - Viewer should be distributed separately from main idt executable

## Description
The viewer application (`viewer/viewer.py`) build scripts for ARM64 and AMD64 are broken. They used to work but now fail due to PyInstaller changes. The viewer needs to be packaged and distributed separately from the main idt toolkit.

## Current State

### Viewer Application
- **Location**: `viewer/viewer.py`
- **Purpose**: Standalone GUI for browsing image descriptions
- **Dependencies**: PyQt6, ollama (optional)
- **Features**:
  - HTML mode for completed workflows
  - Live mode for in-progress workflows  
  - Real-time updates
  - Redescribe images with Ollama
  - Keyboard shortcuts

### Current Build Scripts (BROKEN ❌)
1. `viewer/build_viewer_arm.bat` - ARM64 build
2. `viewer/build_viewer_amd.bat` - AMD64 build
3. `viewer/build_viewer.bat` - Default build

### Environment
- **Python**: 3.10+
- **PyQt6**: 6.9.1 (confirmed installed)
- **PyInstaller**: 6.16.0 (confirmed installed)
- **Platform**: Windows

## Root Cause

### PyInstaller --target-architecture is macOS Only

**From PyInstaller 6.16.0 help:**
```
--target-architecture, --target-arch ARCH
    Target architecture (macOS only; valid values: x86_64,
    arm64, universal2). Enables switching between
    universal2 and single-arch version of frozen
    target architecture). If not target architecture is
    not specified, the current running architecture is
    targeted.
```

**The Problem:**
- Build scripts use `--target-architecture arm64` and `--target-architecture amd64`
- **These flags only work on macOS!**
- On Windows, PyInstaller builds for the architecture of the **running Python interpreter**
- You cannot cross-compile on Windows (x64 Python → ARM64 exe)

### Example from build_viewer_arm.bat (Lines 23-35):
```batch
pyinstaller --onefile ^
    --windowed ^
    --name "viewer_arm64" ^
    --distpath "dist\viewer" ^
    --workpath "build\viewer_arm64" ^
    --specpath "build" ^
    --add-data "../scripts;scripts" ^
    --hidden-import PyQt6.QtCore ^
    --hidden-import PyQt6.QtGui ^
    --hidden-import PyQt6.QtWidgets ^
    --target-architecture arm64 ^  ❌ Windows doesn't support this
    viewer.py
```

**Error message:**
```
ARM64 build failed!
Note: Cross-compilation to ARM64 may require an ARM64 host system.
```

This message is correct - you **do** need an ARM64 host system to build for ARM64 on Windows.

## Why It Used to Work

**Hypothesis 1: PyInstaller Version Change**
- Older PyInstaller versions may have accepted the flag and ignored it
- Or the flag worked differently in earlier versions
- Current version (6.16.0) is strict about macOS-only

**Hypothesis 2: It Never Actually Worked**
- The build may have "succeeded" but produced x64 binaries
- User may not have tested on actual ARM64 systems
- The `--name` changing to `viewer_arm64` doesn't change the architecture

## Solutions

### Solution A: Native Builds on Target Architecture (RECOMMENDED)

Build each architecture on a matching system:

**For AMD64 (x64):**
```batch
# Run on x64 Windows system
pyinstaller --onefile ^
    --windowed ^
    --name "viewer_amd64" ^
    --distpath "dist\viewer" ^
    viewer.py
```

**For ARM64:**
```batch
# Run on ARM64 Windows system (or Windows on ARM VM)
pyinstaller --onefile ^
    --windowed ^
    --name "viewer_arm64" ^
    --distpath "dist\viewer" ^
    viewer.py
```

**Pros:**
- Native builds are most reliable
- Best performance
- Full compatibility guaranteed

**Cons:**
- Requires access to ARM64 Windows system
- Need separate build environments
- More complex CI/CD pipeline

### Solution B: Use GitHub Actions for Multi-Architecture Builds

Set up CI/CD with matrix builds:

```yaml
# .github/workflows/build-viewer.yml
name: Build Viewer
on: [push, workflow_dispatch]

jobs:
  build:
    strategy:
      matrix:
        arch: [x64, ARM64]
    runs-on: windows-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
          architecture: ${{ matrix.arch }}
      
      - name: Install dependencies
        run: |
          pip install PyQt6 pyinstaller
      
      - name: Build viewer
        run: |
          cd viewer
          pyinstaller --onefile --windowed --name viewer_${{ matrix.arch }} viewer.py
      
      - name: Upload artifact
        uses: actions/upload-artifact@v3
        with:
          name: viewer-${{ matrix.arch }}
          path: viewer/dist/viewer_${{ matrix.arch }}.exe
```

**Pros:**
- Automated builds
- No local ARM64 system needed
- Consistent build environment
- Can build on every commit

**Cons:**
- Requires GitHub Actions setup
- Build time on cloud runners
- May need Windows ARM64 runners (availability?)

### Solution C: Single Universal Build (x64 only)

Only build for x64 (most common architecture):

**Pros:**
- Simple and works now
- Covers 95%+ of users
- No cross-compilation issues

**Cons:**
- No native ARM64 support
- ARM64 users must use x64 emulation (slower)
- Not future-proof as ARM64 adoption grows

### Solution D: Emulation Build (Not Recommended)

Try to build ARM64 using emulation or VMs:

**Cons:**
- Complex setup
- Slow builds
- Unreliable
- Not worth the effort

## Recommended Approach

### Phase 1: Fix AMD64 Build (Immediate) ✅

Update `build_viewer_amd.bat`:
```batch
@echo off
echo Building Image Description Viewer for AMD64...
echo.
echo NOTE: Building for architecture of current Python interpreter
echo.

REM Check Python architecture
python -c "import platform; print(f'Python architecture: {platform.machine()}')"
if errorlevel 1 (
    echo Warning: Could not detect Python architecture
)

REM Check if PyInstaller is installed
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    pip install pyinstaller
    if errorlevel 1 (
        echo Failed to install PyInstaller. Exiting.
        pause
        exit /b 1
    )
)

REM Create output directory
if not exist "dist" mkdir dist
if not exist "dist\viewer" mkdir dist\viewer

REM Build the executable
echo Building viewer executable...
echo.

pyinstaller --onefile ^
    --windowed ^
    --name "viewer" ^
    --distpath "dist" ^
    --workpath "build" ^
    --specpath "build" ^
    --hidden-import PyQt6.QtCore ^
    --hidden-import PyQt6.QtGui ^
    --hidden-import PyQt6.QtWidgets ^
    --icon=../../idt.ico ^
    viewer.py

if errorlevel 1 (
    echo Build failed!
    pause
    exit /b 1
)

echo.
echo Build completed successfully!
echo Executable created: dist\viewer.exe
echo.
pause
```

**Changes:**
- ❌ Removed `--target-architecture amd64` (doesn't work on Windows)
- ✅ Added Python architecture detection for transparency
- ✅ Simplified output to just `viewer.exe`
- ✅ Added icon support (if icon exists)

### Phase 2: Separate Viewer Distribution 📦

**Create separate viewer package:**
1. Viewer builds independently of idt
2. Separate release artifacts
3. Independent versioning
4. Smaller download size

**Viewer package contents:**
```
viewer_v1.0/
  ├── viewer.exe          (standalone executable)
  ├── README.txt          (usage instructions)
  └── LICENSE.txt         (license file)
```

**Main IDT package:**
- Does NOT include viewer
- Reduces idt.exe size
- Viewer distributed separately

### Phase 3: ARM64 Support (Future/Optional) 🔮

**Option 1: GitHub Actions**
- Set up automated ARM64 builds
- Requires Windows ARM64 runner access

**Option 2: Manual ARM64 builds**
- Build on ARM64 Windows device when available
- Less frequent releases
- Document the process

**Option 3: Skip ARM64**
- x64 build works on ARM64 via emulation
- Good enough for now
- Revisit if users request it

## Dependencies Analysis

### Viewer-Specific Dependencies
```python
# Required
PyQt6>=6.4.0           # GUI framework (LARGE ~50MB)

# Optional
ollama                 # For redescribe feature
```

### Current Issue: PyQt6 in Main IDT
Looking at main `requirements.txt`:
```
PyQt6>=6.4.0                                # GUI framework
```

**Problem**: PyQt6 is included in main requirements but only used by viewer!

**Impact on idt.exe size:**
- PyQt6 adds ~40-50MB to executable
- Most users don't use the viewer
- Wastes space and build time

**Solution**: Remove PyQt6 from main requirements, keep only for viewer

## Implementation Plan

### Step 1: Fix Current Build Script ✅
- [ ] Update `build_viewer_amd.bat` to remove invalid flags
- [ ] Add architecture detection
- [ ] Test build on x64 Windows
- [ ] Verify executable works
- [ ] Add icon support

### Step 2: Remove PyQt6 from Main IDT 🎯
- [ ] Remove PyQt6 from `requirements.txt`
- [ ] Create `viewer/requirements.txt` with viewer deps only
- [ ] Update viewer README with separate install instructions
- [ ] Test that idt.exe builds without PyQt6
- [ ] Measure size reduction

### Step 3: Create Viewer Distribution Package 📦
- [ ] Create `viewer/package_viewer.bat` script
- [ ] Build viewer executable
- [ ] Copy README and LICENSE
- [ ] Create zip archive
- [ ] Document distribution process

### Step 4: Update Documentation 📝
- [ ] Update main README - viewer distributed separately
- [ ] Update viewer/README.md with install instructions
- [ ] Create VIEWER_DISTRIBUTION.md with packaging docs
- [ ] Update build documentation

### Step 5: Test Separation 🧪
- [ ] Build idt.exe without PyQt6
- [ ] Measure size before/after
- [ ] Build viewer.exe independently
- [ ] Test viewer with idt workflow outputs
- [ ] Verify all features work

### Step 6: ARM64 Support (Optional - Future) 🔮
- [ ] Research GitHub Actions ARM64 runners
- [ ] Set up CI/CD pipeline if available
- [ ] OR document manual ARM64 build process
- [ ] OR decide to skip ARM64 for now

## Build Script Updates Needed

### build_viewer.bat (Default Build)
```batch
@echo off
echo Building Image Description Viewer...
echo.

REM Show current Python architecture
python -c "import platform; print(f'Building for: {platform.machine()}')"
echo.

REM Check and install dependencies
if not exist "requirements.txt" (
    echo Creating viewer requirements.txt...
    echo PyQt6^>=6.4.0 > requirements.txt
)

pip install -r requirements.txt

REM Build
pyinstaller --onefile --windowed --name viewer viewer.py

if errorlevel 1 (
    echo Build failed!
    pause
    exit /b 1
)

echo.
echo Build completed: dist\viewer.exe
pause
```

### build_viewer_arm.bat (Document Limitation)
```batch
@echo off
echo ARM64 Build for Windows
echo.
echo IMPORTANT: Windows ARM64 builds require an ARM64 Windows system.
echo PyInstaller cannot cross-compile on Windows.
echo.
echo Options:
echo 1. Run this script on an ARM64 Windows device
echo 2. Use Windows ARM64 VM or cloud instance
echo 3. Use GitHub Actions with ARM64 runner
echo 4. Users can run x64 build via emulation
echo.
echo Current Python architecture:
python -c "import platform; print(f'  {platform.machine()}')"
echo.
echo Press any key to attempt build (will only work if running on ARM64)...
pause

REM Same build as default, just different name
pyinstaller --onefile --windowed --name viewer_arm64 viewer.py
```

## Files to Create/Modify

### New Files:
- [ ] `viewer/requirements.txt` - Viewer-specific dependencies
- [ ] `viewer/package_viewer.bat` - Create distribution package
- [ ] `VIEWER_DISTRIBUTION.md` - Distribution documentation
- [ ] `.github/workflows/build-viewer.yml` - CI/CD (optional)

### Modified Files:
- [ ] `requirements.txt` - Remove PyQt6
- [ ] `viewer/build_viewer.bat` - Fix build script
- [ ] `viewer/build_viewer_amd.bat` - Fix/document limitations
- [ ] `viewer/build_viewer_arm.bat` - Document ARM64 requirements
- [ ] `viewer/README.md` - Update with new build process
- [ ] `README.md` - Note separate viewer distribution

## Testing Checklist

- [ ] idt.exe builds without PyQt6
- [ ] idt.exe size reduced significantly
- [ ] viewer.exe builds successfully (x64)
- [ ] viewer.exe runs standalone
- [ ] viewer.exe opens HTML mode correctly
- [ ] viewer.exe opens Live mode correctly
- [ ] viewer.exe redescribe feature works (with Ollama)
- [ ] viewer.exe works with current workflow outputs
- [ ] No regression in idt.exe functionality

## Expected Size Reduction

**Current idt.exe** (estimated): ~150-200MB
**With PyQt6**: ~150-200MB
**Without PyQt6**: ~100-120MB (estimated 30-40% reduction)

**Viewer.exe** (separate): ~40-60MB

**User benefit:**
- Most users only download idt.exe (~100MB)
- Viewer users download both (~160MB total)
- Still smaller than bundling together
- Faster idt.exe downloads for non-viewer users

## ARM64 Decision Matrix

| Approach | Effort | Maintenance | User Coverage | Recommendation |
|----------|--------|-------------|---------------|----------------|
| Skip ARM64 | Low | None | 95%+ | ✅ Good for now |
| Manual builds | Medium | High | 100% | ⚠️ Only if requested |
| GitHub Actions | High | Medium | 100% | ⚠️ If ARM64 runners available |
| Emulation | High | High | 100% | ❌ Not recommended |

**Recommendation**: Skip native ARM64 for now. x64 build works on ARM64 via emulation. Revisit if users specifically request native ARM64 builds.

## Related Files
- `viewer/viewer.py` - Main viewer application (1291 lines)
- `viewer/build_viewer.bat` - Default build script
- `viewer/build_viewer_amd.bat` - AMD64 build (broken)
- `viewer/build_viewer_arm.bat` - ARM64 build (broken)
- `viewer/README.md` - Viewer documentation
- `requirements.txt` - Main IDT dependencies (includes PyQt6 ❌)

## Resolution Checklist

### Immediate (This Week):
- [ ] Fix build_viewer.bat (remove invalid flags)
- [ ] Create viewer/requirements.txt
- [ ] Test viewer build works
- [ ] Update viewer README

### Short Term (Next Release):
- [ ] Remove PyQt6 from main requirements.txt
- [ ] Rebuild idt.exe and measure size reduction
- [ ] Create viewer distribution package
- [ ] Update all documentation
- [ ] Release viewer as separate download

### Long Term (Future):
- [ ] Evaluate GitHub Actions for CI/CD
- [ ] Consider ARM64 if users request it
- [ ] Automated release packaging

---
**Created:** October 11, 2025
**Priority:** Medium (affects distribution strategy)
**Impact:** Reduces main idt.exe size by 30-40%
**User Benefit:** Faster downloads, separate viewer distribution
