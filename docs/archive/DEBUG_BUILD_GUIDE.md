# Debug Build Guide for ImageDescriber

**Audience:** Developers and contributors debugging frozen executable issues

## Overview

ImageDescriber offers two debugging approaches:

1. **--debug flag** (For end users) - Enhanced file logging, no console window
2. **Debug build** (For developers) - Live console output, full visibility

This guide covers both approaches and when to use each.

## Quick Start: --debug Flag (Recommended for Users)

If you're experiencing issues, start by enabling debug logging:

```batch
ImageDescriber.exe --debug
```

This creates a verbose debug log at:
```
%USERPROFILE%\imagedescriber_verbose_debug.log
```

**Advantages:**
- No rebuild required
- Professional UI (no console window)
- Detailed logging for troubleshooting
- Easy to share log files when reporting issues

**Usage:**
```batch
# Default location
ImageDescriber.exe --debug

# Custom log location
ImageDescriber.exe --debug --debug-file C:\Temp\my_debug.log

# With workspace path and debug mode
ImageDescriber.exe --debug C:\MyWorkspace

# Viewer mode with debug logging
ImageDescriber.exe --debug --viewer
```

### Debug Log Output Format

The verbose debug log includes:

```
============================================================
DEBUG MODE ENABLED
Verbose logging to: C:\Users\YourName\imagedescriber_verbose_debug.log
ImageDescriber version: 4.1.0
Python: 3.12.8 (tags/v3.12.8:2dc476b, Dec  3 2024, 19:30:04) [MSC v.1942 64 bit (AMD64)]
wxPython: 4.2.2 msw (phoenix) wxWidgets 3.2.6
Frozen mode: True
============================================================
2026-02-11 14:32:15,123 - INFO - __main__:4120 - Starting ImageDescriber
2026-02-11 14:32:15,234 - DEBUG - workers_wx:1210 - VideoProcessingWorker.run() started for \\server\IMG_3136.MOV
2026-02-11 14:32:15,345 - DEBUG - workers_wx:1220 - Extraction config: {'extraction_mode': 'time_interval', 'time_interval_seconds': 5.0}
2026-02-11 14:32:16,456 - INFO - workers_wx:1223 - _extract_frames() completed: 12 frames extracted
2026-02-11 14:32:16,567 - ERROR - imagedescriber_wx:2179 - FATAL ERROR: TypeError: update_progress() got unexpected keyword
2026-02-11 14:32:16,678 - ERROR - imagedescriber_wx:2180 - Traceback (most recent call last):...
```

Each line shows:
- **Timestamp**: When the event occurred
- **Level**: DEBUG, INFO, WARNING, ERROR
- **Module**: Which file the log came from
- **Line number**: Exact location in code
- **Message**: What happened

## Comparison: --debug Flag vs Debug Build

| Feature | --debug Flag | Debug Build |
|---------|-------------|-------------|
| **Rebuild required** | ❌ No | ✅ Yes (~2-3 min) |
| **Console window** | ❌ No | ✅ Yes |
| **Live output** | ❌ No (file only) | ✅ Yes (console) |
| **Detailed logs** | ✅ Yes | ✅ Yes |
| **Professional appearance** | ✅ Yes | ❌ No (console visible) |
| **Best for** | End users, bug reports | Developers, active debugging |
| **When to use** | Troubleshooting issues | Development, live debugging |

## When to Use Debug Build

Use the debug build (developers/contributors only) when you need:
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

Log files are created when using the --debug flag:

### Verbose Debug Log (--debug flag)
```
%USERPROFILE%\imagedescriber_verbose_debug.log
```

Contains:
- INFO, DEBUG, WARNING, ERROR messages
- Timestamped entries
- Function call sequences
- Configuration loading details
- Startup banner with version info

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
