# Debug Build Guide for ImageDescriber

**Audience:** Developers and contributors debugging frozen executable issues

## Overview

The ImageDescriber debug build creates an executable with console window output enabled, making it easy to diagnose silent failures, crashes, and other issues that are hard to debug in the standard windowed application.

## When to Use Debug Build

Use the debug build when you encounter:
- Silent failures (UI appears but nothing happens)
- Progress dialog freezes or doesn't update
- Crashes with no error message
- Unexpected behavior that's hard to reproduce
- Need to verify that code changes fixed an issue

## Building the Debug Version (Windows)

### Quick Start

```batch
cd BuildAndRelease\WinBuilds
build_imagedescriber_wx_debug.bat
```

This creates `C:\idt\ImageDescriber.exe` with console output enabled.

### What the Debug Build Script Does

1. Activates the `.winenv` virtual environment in `imagedescriber/`
2. Verifies PyInstaller is installed
3. Creates a temporary debug spec file (`imagedescriber_wx_debug.spec`)
   - Sets `console=True` instead of `console=False`
4. Runs PyInstaller with the debug spec
5. Copies the executable to `C:\idt\ImageDescriber.exe`
6. Cleans up the temporary spec file

### Manual Debug Build

If you need more control:

```batch
cd imagedescriber
call .winenv\Scripts\activate.bat

REM Create debug spec (temporary modification)
python -c "spec = open('imagedescriber_wx.spec').read().replace('console=False', 'console=True'); open('imagedescriber_wx_debug.spec', 'w').write(spec)"

REM Build with debug spec
pyinstaller --clean --noconfirm imagedescriber_wx_debug.spec

REM Clean up
del imagedescriber_wx_debug.spec
```

## Running the Debug Executable

```batch
C:\idt\ImageDescriber.exe
```

You'll see **two windows**:
1. **GUI window** - The normal ImageDescriber interface
2. **Console window** - Shows all print() statements and debug output

## Reading Debug Output

### Console Window Messages

The console shows real-time output:

```
=============================================================
on_process_all CALLED - skip_existing=True
Workspace items: 148
=============================================================
Scanning 148 workspace items...
  Item: IMG_3136.MOV, type=video, has_desc=False
    -> Adding to videos_to_extract
Result: 148 videos to extract, 1035 images to process
BRANCH: Starting video extraction flow
_extract_next_video_in_batch: count=0, total=148
Extracting video 1/148: IMG_3136.MOV
VideoProcessingWorker.run() STARTED for IMG_3136.MOV
Posting progress message...
Calling _extract_frames()...
_extract_frames() returned 1 frames
Posting WorkflowCompleteEventData...
WorkflowCompleteEventData posted
```

### Error Messages

Errors appear in the console with full details:

```
============================================================
FATAL ERROR in VideoProcessingWorker: TypeError: update_progress() got an unexpected keyword argument 'image_name'
Traceback (most recent call last):
  File "workers_wx.py", line 2179, in _extract_next_video_in_batch
    self.batch_progress_dialog.update_progress(
TypeError: update_progress() got an unexpected keyword argument 'image_name'
============================================================
```

This immediately shows:
- **What failed**: `update_progress()` method signature mismatch
- **Where it failed**: Line 2179 in `_extract_next_video_in_batch`
- **Why it failed**: Method doesn't accept `image_name` parameter

## Log Files

Even with the debug build, log files are still written:

### Main Log
```
%USERPROFILE%\imagedescriber_geocoding_debug.log
```

Contains:
- INFO, DEBUG, WARNING, ERROR messages
- Timestamped entries
- Function call sequences
- Configuration loading details

### Crash Log
```
%USERPROFILE%\imagedescriber_crash.log
```

Contains:
- Worker thread exceptions (VideoProcessingWorker, BatchProcessingWorker)
- Full stack traces
- Context (video path, provider, model, etc.)
- Created only when exceptions occur

**Example crash log entry:**

```
============================================================
2026-02-11T14:32:15.123456 - VideoProcessingWorker crash
Video: \\server\photos\IMG_1234.MOV
Error: FATAL ERROR in VideoProcessingWorker: FileNotFoundError: [Errno 2] No such file or directory: 'C:\\workspace\\extracted_frames'
Traceback:
  File "workers_wx.py", line 1285, in _extract_frames
    video_dir.mkdir(parents=True, exist_ok=True)
  File "pathlib.py", line 1323, in mkdir
    self._accessor.mkdir(self, mode)
FileNotFoundError: [Errno 2] No such file or directory: 'C:\\workspace\\extracted_frames'
============================================================
```

## Common Issues Revealed by Debug Output

### 1. Missing Dependencies

**Console shows:**
```
ModuleNotFoundError: No module named 'cv2'
```

**Fix:** OpenCV not installed in virtual environment
```batch
cd imagedescriber
.winenv\Scripts\activate.bat
pip install opencv-python
```

### 2. Method Signature Mismatches

**Console shows:**
```
TypeError: update_progress() got an unexpected keyword argument 'image_name'
```

**Cause:** Code calling method with parameters it doesn't accept  
**Fix:** Update method signature to accept the parameters or change the caller

### 3. File Permission Errors

**Console shows:**
```
PermissionError: [WinError 32] The process cannot access the file because it is being used by another process
```

**Fix:** Close other programs accessing the file, or check antivirus isn't locking it

### 4. Configuration File Issues

**Console shows:**
```
WARNING: Config file not found: C:\idt\scripts\image_describer_config.json
```

**Fix:** Ensure config files are in the correct location relative to the executable

## Switching Back to Normal Build

After debugging, rebuild without console output for distribution:

```batch
cd imagedescriber
build_imagedescriber_wx.bat
```

Or for the master build:

```batch
cd BuildAndRelease\WinBuilds
builditall_wx.bat
```

## Debugging Workflow

**Step-by-step debugging process:**

1. **Reproduce the issue** in the regular build
2. **Build debug version** (`build_imagedescriber_wx_debug.bat`)
3. **Run debug executable** and reproduce the issue
4. **Watch console output** for error messages
5. **Check log files** for additional context
6. **Identify the root cause** from error messages and stack traces
7. **Fix the issue** in source code
8. **Test with debug build** to verify the fix
9. **Rebuild normal version** for distribution

## Advanced Debugging

### Temporarily Add Print Statements

In source code, add debug output:

```python
def _extract_next_video_in_batch(self):
    print(f"DEBUG: _batch_video_extraction={self._batch_video_extraction}", flush=True)
    print(f"DEBUG: worker type: {type(self.video_worker)}", flush=True)
    # ... rest of function
```

The `flush=True` ensures output appears immediately in the console.

### Check Event Handler Bindings

```python
print(f"DEBUG: EVT_WORKFLOW_COMPLETE bound: {hasattr(self, 'on_workflow_complete')}", flush=True)
```

### Verify Variable State

```python
print(f"DEBUG: videos_to_extract={len(self._videos_to_extract)}", flush=True)
print(f"DEBUG: current count={self._extracted_video_count}", flush=True)
```

## Comparison: Debug vs Normal Build

| Feature | Debug Build | Normal Build |
|---------|------------|--------------|
| Console window | ✅ Visible | ❌ Hidden |
| Print statements | ✅ Visible | ❌ Lost |
| Exception messages | ✅ Console + logs | ⚠️ Logs only |
| File size | Same | Same |
| Performance | Same | Same |
| Distribution | ❌ No (ugly console) | ✅ Yes (clean UI) |

## See Also

- [Build System Reference](../../BuildAndRelease/BUILD_SYSTEM_REFERENCE.md)
- [AI Onboarding](../AI_ONBOARDING.md) - Current development context
- [User Guide Troubleshooting](../USER_GUIDE.md#troubleshooting) - End user troubleshooting steps
