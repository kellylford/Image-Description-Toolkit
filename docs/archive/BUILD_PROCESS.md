# Executable Build Process - Step-by-Step Guide

## Overview
This guide shows you how to build and distribute the Image Description Toolkit as a standalone executable. **Your repository files are never modified** - all conversions happen in temporary staging directories.

---

## Prerequisites (One-Time Setup)

### 1. Install PyInstaller
```bash
pip install pyinstaller
```

### 2. Verify Installation
```bash
pyinstaller --version
# Should show version 5.x or higher
```

That's it! You're ready to build.

---

## Regular Build Process

### When to Build
- Before creating a new release
- After significant code changes
- When testing executable distribution
- Typically: Every few weeks or before major releases

### Build Steps (Takes ~5-10 minutes)

#### Step 1: Update Version (Optional)
If releasing a new version, edit `VERSION` file:
```
1.0.0  → 1.1.0
```

#### Step 2: Build the Executable
```bash
# From project root directory
build.bat
```

**What this does:**
- Cleans previous build artifacts (`build/`, `dist/`)
- Runs PyInstaller with `ImageDescriptionToolkit.spec`
- Creates `dist/ImageDescriptionToolkit.exe` (~150-200 MB)
- Tests the executable with `--version` command
- Reports file size

**Expected output:**
```
========================================================================
Building Image Description Toolkit Executable
========================================================================

[1/4] Checking PyInstaller installation...
    PyInstaller is installed.

[2/4] Cleaning previous builds...
    Done.

[3/4] Building executable with PyInstaller...
    [PyInstaller output...]
    Done.

[4/4] Verifying executable...
    Executable created successfully!
    File: dist\ImageDescriptionToolkit.exe
    Size: 187 MB

    Testing executable...
    Image Description Toolkit v1.0.0
    Executable works correctly!

========================================================================
Build Complete!
========================================================================
```

**Time:** ~3-5 minutes depending on your machine

#### Step 3: Create Distribution Package
```bash
# From project root directory
create_distribution.bat
```

**What this does:**
- Creates `releases/staging/` directory (temporary)
- Copies executable to staging
- Copies batch files to staging
- **Converts batch files** from `python workflow.py` → `ImageDescriptionToolkit.exe workflow`
  - ⚠️ **ONLY in staging directory, NOT in your repository!**
- Copies documentation
- Creates directory structure
- Bundles everything into `releases/ImageDescriptionToolkit_v1.0.0.zip`
- Deletes staging directory

**Expected output:**
```
========================================================================
Creating Distribution Package
========================================================================

[1/5] Copying executable...
    Done.

[2/5] Copying and updating batch files...
    Converting batch files to use executable...
    Done.

[3/5] Creating directory structure...
    Done.

[4/5] Copying documentation...
    Done.

[5/5] Creating ZIP archive...
    Done.

========================================================================
Distribution Package Created!
========================================================================

Package: releases\ImageDescriptionToolkit_v1.0.0.zip
Size: 95 MB (compressed)

This package includes:
  - ImageDescriptionToolkit.exe (single executable)
  - All batch files (ready to use)
  - Directory structure (Descriptions, analysis, etc.)
  - Documentation (README, QUICK_START, docs)
  - Sample configurations

Users can:
  1. Extract ZIP to any folder
  2. Install Ollama
  3. Run batch files immediately - no Python needed!

Ready for distribution!
```

**Time:** ~1-2 minutes

#### Step 4: Test the Distribution (Recommended)
```bash
# Extract to a test folder
cd C:\temp
unzip ImageDescriptionToolkit_v1.0.0.zip

# Test a batch file
cd ImageDescriptionToolkit
bat\run_ollama_llava.bat

# Verify it uses the exe, not Python
# (You'll see the exe unpacking on first run)
```

---

## What Gets Modified

### ✅ Your Repository (Git) - UNCHANGED
```
bat/
  run_ollama_llava.bat        → "python workflow.py ..."   ✅ Stays as-is
  run_claude_opus4.bat        → "python workflow.py ..."   ✅ Stays as-is
  (all other bat files)       → "python workflow.py ..."   ✅ Stays as-is

workflow.py                   ✅ Unchanged
stats_analysis.py             ✅ Unchanged
content_analysis.py           ✅ Unchanged
combine_workflow_descriptions.py  ✅ Unchanged
(all other Python files)      ✅ Unchanged
```

**Result:** You can continue using Python normally for development!

### 📦 Distribution ZIP - CONVERTED
```
bat/
  run_ollama_llava.bat        → "ImageDescriptionToolkit.exe workflow ..."
  run_claude_opus4.bat        → "ImageDescriptionToolkit.exe workflow ..."
  (all other bat files)       → "ImageDescriptionToolkit.exe workflow ..."

ImageDescriptionToolkit.exe   → Bundled executable
```

**Result:** End users get ready-to-run batch files with no Python needed!

---

## Build Artifacts (Created During Build)

### Temporary Files (Auto-Deleted)
```
build/                        → Deleted after build
releases/staging/             → Deleted after ZIP creation
```

### Permanent Files (Kept)
```
dist/
  ImageDescriptionToolkit.exe → The built executable (Git-ignored)

releases/
  ImageDescriptionToolkit_v1.0.0.zip  → Distribution package (Git-ignored)
```

**Note:** These are in `.gitignore` so they won't be committed to git.

---

## Common Scenarios

### Scenario 1: Regular Development
**What you do:**
```bash
# Edit Python code
# Test with Python
python workflow.py --model ollama/llava ...

# Or use batch files (they call Python)
bat\run_ollama_llava.bat
```

**No build needed!** Your batch files call Python directly.

### Scenario 2: Preparing a Release
**What you do:**
```bash
# 1. Update version
echo 1.1.0 > VERSION

# 2. Build executable
build.bat

# 3. Create distribution
create_distribution.bat

# 4. Upload to GitHub Releases
# Upload releases/ImageDescriptionToolkit_v1.1.0.zip
```

**Your repository:** Still uses Python version, unchanged.
**Distribution ZIP:** Contains executable version for users.

### Scenario 3: Testing Executable Locally
**What you do:**
```bash
# Build the executable
build.bat

# Test it directly
dist\ImageDescriptionToolkit.exe workflow --model ollama/llava ...

# Or create full distribution and test
create_distribution.bat
# Extract releases/ImageDescriptionToolkit_v1.0.0.zip to test folder
# Test batch files
```

**Your repository:** Still unchanged, you're just testing the exe.

---

## File Size Breakdown

### Executable Size: ~150-200 MB
**Why so large?**
- Python runtime: ~50 MB
- PIL/Pillow: ~20 MB
- OpenCV: ~40 MB
- Anthropic SDK: ~10 MB
- OpenAI SDK: ~10 MB
- Ollama SDK: ~5 MB
- Other dependencies: ~30 MB
- Your code + models: ~10 MB

This is **normal and expected** for bundled executables.

### Distribution ZIP: ~90-100 MB (Compressed)
- Executable compresses well due to similar code patterns
- ~50% compression ratio

---

## Troubleshooting

### "PyInstaller not found"
```bash
pip install pyinstaller
```

### "Executable too large"
Already optimized with:
- UPX compression
- Excluded GUI frameworks (PyQt, tkinter)
- Excluded unnecessary libraries

Can't make it much smaller without breaking functionality.

### "Build failed" during PyInstaller
Check:
1. All dependencies installed: `pip install -r requirements.txt`
2. No syntax errors: `python workflow.py --help`
3. PyInstaller version: `pyinstaller --version` (should be 5.x+)

### "Executable doesn't run"
On first run, the exe unpacks itself (~1-2 seconds). This is normal.

If it fails:
1. Check Windows Defender didn't quarantine it
2. Run from Command Prompt to see error messages
3. Verify all dependencies in `ImageDescriptionToolkit.spec` are correct

---

## CI/CD Integration (Future)

You can automate this with GitHub Actions:

```yaml
# .github/workflows/release.yml
name: Build Release
on:
  push:
    tags:
      - 'v*'
jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pip install pyinstaller
      - run: build.bat
      - run: create_distribution.bat
      - uses: actions/upload-artifact@v3
        with:
          name: ImageDescriptionToolkit
          path: releases/*.zip
```

---

## Quick Reference Card

### Build Commands
```bash
# Full build process (from project root)
build.bat                    # Step 1: Build exe (~3-5 min)
create_distribution.bat      # Step 2: Create ZIP (~1-2 min)

# Testing
dist\ImageDescriptionToolkit.exe --version  # Test exe directly
```

### What Gets Changed
- ✅ Your repository: **NOTHING** (unchanged)
- 📦 Distribution ZIP: Batch files converted to call `.exe`
- 🗑️ Temporary staging: Created and deleted automatically

### Build Frequency
- ⏰ Before releases (when ready to ship)
- ⏰ After major code changes (to test)
- ⏰ Every few weeks if actively releasing

### File Locations
```
dist/ImageDescriptionToolkit.exe          # Built executable
releases/ImageDescriptionToolkit_v*.zip   # Distribution package
bat/*.bat                                  # Your files (Python version)
```

---

## Summary

**The Key Point:** Your repository **never changes**. The batch file conversion happens only when creating the distribution ZIP, in a temporary staging directory that gets deleted afterwards.

**Your workflow:**
1. Develop with Python (as always)
2. When ready to release: Run `build.bat` → `create_distribution.bat`
3. Upload the ZIP to GitHub Releases
4. Continue developing with Python (as always)

**User workflow:**
1. Download ZIP
2. Extract
3. Run batch files (which call the bundled exe)
4. No Python installation needed!

**Both workflows coexist perfectly!** 🎉
