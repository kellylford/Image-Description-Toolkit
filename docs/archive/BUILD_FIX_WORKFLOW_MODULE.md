# Build Fix - Workflow Module Error

**Date:** October 8, 2025  
**Issue:** `ModuleNotFoundError: No module named 'workflow'`  
**Status:** ✅ Fixed

---

## Problem

When running the built executable `ImageDescriptionToolkit.exe`, users encountered this error:

```
~/your_secure_location/idt>ImageDescriptionToolkit.exe workflow --provider ollama --model gemma3

Traceback (most recent call last):
File "idt_cli.py", line 180, in <module>
File "idt_cli.py", line 43, in main
ModuleNotFoundError: No module named 'workflow'
[PYI-24112:ERROR] Failed to execute script 'idt_cli' due to unhandled exception!
```

---

## Root Cause

Two issues were found:

### 1. Stray Import Statement in `idt_cli.py`

**Line 43 in idt_cli.py:**
```python
import workflow  # ❌ This tried to import a non-existent module
```

The code had leftover comments and an `import workflow` statement that shouldn't have been there. The actual workflow script is at `scripts/workflow.py` and is executed via subprocess, not imported.

### 2. Missing Python Files in Build

The `.spec` file was not including the actual Python script files in the build, only configuration JSON files. This meant:
- `scripts/workflow.py` was not bundled
- `imagedescriber/*.py` modules were not bundled
- `analysis/*.py` scripts were not bundled

---

## Solution

### Fix 1: Remove Stray Import

**File:** `idt_cli.py`

**Before:**
```python
if command == 'workflow':
    # Import and run workflow
    # The workflow.py wrapper already handles everything correctly
    import workflow  # ❌ PROBLEM LINE
    # workflow.py runs as subprocess, so we just need to call it
    # Actually, let's call the scripts/workflow.py directly
    scripts_dir = base_dir / 'scripts'
    workflow_script = scripts_dir / 'workflow.py'
```

**After:**
```python
if command == 'workflow':
    # Run workflow script directly (no import needed, we use subprocess)
    scripts_dir = base_dir / 'scripts'
    workflow_script = scripts_dir / 'workflow.py'
```

### Fix 2: Include All Python Files in Build

**File:** `ImageDescriptionToolkit.spec`

**Before:**
```python
datas=[
    # Include configuration files from scripts directory
    ('scripts/*.json', 'scripts'),
    ('VERSION', '.'),
    ('models/*.py', 'models'),
],
```

**After:**
```python
datas=[
    # Include all Python scripts from scripts directory
    ('scripts/*.py', 'scripts'),
    
    # Include configuration files from scripts directory
    ('scripts/*.json', 'scripts'),
    
    # Include imagedescriber Python modules
    ('imagedescriber/*.py', 'imagedescriber'),
    
    # Include VERSION file
    ('VERSION', '.'),
    
    # Include model Python files
    ('models/*.py', 'models'),
    
    # Include analysis scripts
    ('analysis/*.py', 'analysis'),
],
```

---

## How to Rebuild

After these fixes, rebuild the executable:

```bash
# Clean previous build
rm -rf build/ dist/

# Rebuild with PyInstaller
pyinstaller ImageDescriptionToolkit.spec

# Test the new build
dist/ImageDescriptionToolkit.exe workflow --help
```

---

## Testing

The fixed build should now work:

```bash
# Test workflow command
ImageDescriptionToolkit.exe workflow --provider ollama --model llava /path/to/images

# Test other commands
ImageDescriptionToolkit.exe check-models
ImageDescriptionToolkit.exe analyze-stats
ImageDescriptionToolkit.exe version
```

All commands should execute without the `ModuleNotFoundError`.

---

## Files Modified

1. **`idt_cli.py`**
   - Removed stray `import workflow` statement
   - Cleaned up comments

2. **`ImageDescriptionToolkit.spec`**
   - Added `('scripts/*.py', 'scripts')` to include all workflow scripts
   - Added `('imagedescriber/*.py', 'imagedescriber')` to include AI provider modules
   - Added `('analysis/*.py', 'analysis')` to include analysis scripts

---

## Related Issues

This fix also resolves potential issues with:
- `analyze-stats` command (analysis scripts now included)
- `analyze-content` command (analysis scripts now included)
- Any workflow features that depend on imagedescriber modules

---

## Prevention

To prevent similar issues in the future:

1. **Never import modules that are run via subprocess**
   - `workflow.py` is executed as a subprocess, not imported
   - Use `subprocess.run()` instead of `import`

2. **Include all Python files in .spec file**
   - Use `('directory/*.py', 'directory')` patterns
   - Don't rely on PyInstaller auto-detection for non-standard layouts

3. **Test the build on a clean machine**
   - The development machine has all modules in the environment
   - The built executable must be self-contained
   - Test on a machine without Python installed

---

## Commit

```
commit 8995bbf
Author: [Your Name]
Date: October 8, 2025

Fix build: Remove stray workflow import and include all Python files

- Remove unused 'import workflow' that caused ModuleNotFoundError
- Add scripts/*.py to build to include workflow.py
- Add imagedescriber/*.py to bundle AI provider modules
- Add analysis/*.py to bundle analysis scripts

Fixes executable crash when running workflow command.
```

---

## Status

✅ **Fixed and committed**  
⏳ **Needs rebuild** - Users must rebuild the executable with the updated spec file  
📋 **Needs testing** - Test on clean machine after rebuild
