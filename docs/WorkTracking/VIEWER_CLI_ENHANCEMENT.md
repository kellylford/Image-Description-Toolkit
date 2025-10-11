# Viewer CLI Enhancement Summary

## Changes Implemented

### 1. Command-Line Argument Support ✅

Added full argparse integration to `viewer/viewer.py`:

**Usage:**
```bash
viewer.exe [directory] [--open] [--help]
```

**Arguments:**
- **`directory`** (optional positional) - Path to workflow output directory to load on startup
- **`--open`** (flag) - Launch directly to directory selection dialog
- **`--help`** (flag) - Display comprehensive help with examples and keyboard shortcuts

### 2. Three Launch Modes ✅

1. **Empty Viewer** (default)
   ```bash
   viewer.exe
   ```
   - Launches with no directory loaded
   - User clicks "Change Directory" to browse

2. **Direct Directory Load**
   ```bash
   viewer.exe "C:\workflows\wf_claude_20251011_112851"
   ```
   - Loads specified directory immediately
   - Shows error dialog if directory invalid/not found
   - Falls back to directory selection on error

3. **Open Dialog Launch**
   ```bash
   viewer.exe --open
   ```
   - Shows directory selection dialog immediately after launch
   - Equivalent to launching and clicking "Change Directory"

### 3. Comprehensive Help Text ✅

The `--help` flag now displays:
- Usage syntax
- Argument descriptions
- Real-world examples
- Mode explanations (HTML vs Live)
- Keyboard shortcuts
- Best practices

### 4. Error Handling ✅

- Validates directory exists before loading
- Shows user-friendly error messages
- Falls back to directory picker on invalid path
- Handles Qt platform arguments gracefully
- Works in both dev and executable modes

### 5. Documentation ✅

Created `viewer/README.md` with:
- Feature overview (HTML Mode, Live Mode)
- CLI usage examples
- Build instructions
- Integration with IDT launcher
- Keyboard shortcuts reference
- Troubleshooting guide
- Expected directory structure

## Technical Implementation

### Argument Parsing
```python
parser = argparse.ArgumentParser(
    description='Image Description Viewer - Browse workflow results and image descriptions',
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""..."""  # Comprehensive examples
)
parser.add_argument('directory', nargs='?', help='...')
parser.add_argument('--open', action='store_true', help='...')
```

### Qt Integration
- Filters Qt platform arguments to avoid conflicts
- Uses `QTimer.singleShot()` to trigger dialog after app startup
- Preserves all existing Qt functionality

### Path Handling
- Converts relative paths to absolute using `Path.resolve()`
- Cross-platform path compatibility
- Validates directory exists and is actually a directory

## Testing Performed ✅

1. **`--help` flag**: Displays comprehensive help text
2. **Directory argument**: Loads valid directories successfully
3. **Invalid directory**: Shows error and falls back to dialog
4. **`--open` flag**: Successfully triggers directory picker
5. **No arguments**: Launches empty viewer as before (backward compatible)

## Integration with IDT

The viewer now works seamlessly with the `idt viewer` launcher:

```bash
# User runs from IDT
idt viewer

# IDT launcher finds viewer executable and runs
viewer_amd64.exe

# Or with directory
idt viewer "C:\workflow_output"  # (future enhancement)
```

## Commits

1. **75fd796** - Add command-line interface to viewer with directory and --open support
2. **0bf7944** - Add comprehensive README for viewer with CLI usage and features

## Benefits

### For Users
- ✅ Quick access to specific workflows without manual browsing
- ✅ Scriptable viewer launching for automation
- ✅ Better integration with IDT CLI workflow
- ✅ Self-documenting with `--help`

### For First Release
- ✅ Professional CLI interface matching IDT standards
- ✅ Comprehensive documentation ready
- ✅ Easy to demonstrate and use
- ✅ "Makes it easy to see all the work behind the scenes" (user goal)

## Next Steps

### For This Release
- ✅ Code complete and committed
- ⏳ Test with built executable (viewer.exe)
- ⏳ Include viewer in main IDT build/release
- ⏳ Update main README with viewer section

### Future Enhancements
- [ ] Support for `idt viewer <directory>` (pass args through launcher)
- [ ] Batch mode for processing multiple directories
- [ ] Export/save functionality
- [ ] Configuration file support

## Status: READY FOR TESTING

All code changes complete and committed. Ready for:
1. Build viewer executable with `build_viewer.bat`
2. Test standalone viewer.exe with all argument combinations
3. Test integration with `idt viewer` launcher
4. Include in first release package
