# Viewer Launcher Implementation

## Summary
Added `idt viewer` command that launches the separate viewer executable as a GUI application.

## Changes Made

### 1. Added `viewer` Command Handler
**File**: `idt_cli.py` (lines ~470-523)

**Features**:
- Auto-detects system architecture (AMD64/ARM64)
- Searches multiple possible locations for viewer executable
- Launches viewer as detached process (doesn't block terminal)
- Provides helpful error message if viewer not found

**Search Locations** (in order):
1. `viewer_<arch>.exe` (e.g., `viewer_amd64.exe`)
2. `viewer.exe` (generic)
3. `viewer/viewer_<arch>.exe`
4. `viewer/viewer.exe`
5. `../viewer/viewer_<arch>.exe`
6. `../viewer/viewer.exe`

### 2. Updated Help Text
**File**: `idt_cli.py` (print_usage function)

**Changes**:
- Added `viewer` to commands list
- Added example: `idt viewer`
- Added note about building viewer separately

## Usage

### From Development Environment
```bash
python idt_cli.py viewer
```

### From Executable (after build)
```bash
idt.exe viewer
```

## Error Messages

### When Viewer Not Found
```
Error: Viewer executable not found.
Looked in: C:\Users\kelly\GitHub\idt
Expected: viewer_amd64.exe or viewer.exe

The viewer must be built separately using:
  cd viewer
  build_viewer.bat
```

## Building the Viewer

The viewer must be built separately before this command will work:

```bash
cd viewer
build_viewer.bat
```

This creates `viewer/dist/viewer/viewer_<arch>.exe`

## Distribution Setup

When distributing both executables together, use this structure:

```
idt-toolkit/
  idt.exe              # Main CLI (~10-20MB)
  viewer_amd64.exe     # Viewer GUI (~60-80MB)
  README.txt
```

## Technical Details

### Process Launch
- Uses `subprocess.Popen()` to launch as separate process
- On Windows, uses `CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS` flags
- Parent process (idt.exe) exits immediately after launch
- Viewer runs independently in background

### Architecture Detection
Uses `platform.machine()`:
- `aarch64` or `arm64` → looks for `viewer_arm64.exe`
- `amd64` or `x86_64` → looks for `viewer_amd64.exe`

### Future Enhancements (Optional)
- [ ] Support passing workflow directory: `idt viewer wf_claude_haiku/`
- [ ] Auto-download viewer if missing (from releases)
- [ ] Version compatibility checking between idt.exe and viewer.exe
- [ ] Support for `--wait` flag to keep terminal open until viewer closes

## Testing

### Test 1: Help Text
```bash
python idt_cli.py help
# Should show "viewer" command in list
```

### Test 2: Missing Executable
```bash
python idt_cli.py viewer
# Should show helpful error with build instructions
```

### Test 3: Launch Viewer (when built)
```bash
python idt_cli.py viewer
# Should launch viewer GUI and exit immediately
```

## Benefits

✅ **Unified Interface**: Users only need to remember `idt` command  
✅ **No Bloat**: Keeps executables separate and optimized  
✅ **Helpful Errors**: Clear instructions when viewer not found  
✅ **Flexible Deployment**: Viewer is optional, not required  
✅ **Architecture Aware**: Automatically finds correct executable for system  

## Implementation Date
October 11, 2025
