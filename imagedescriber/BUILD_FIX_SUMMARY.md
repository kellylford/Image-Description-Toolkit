# ImageDescriber PyInstaller Build Fix

## Problem Summary

The PyInstaller builds for both ARM64 and AMD64 were failing due to subprocess crashes during the dependency analysis phase. PyInstaller was trying to import certain modules that caused crashes.

## Root Causes

1. **onnx.reference module crash** - PyInstaller subprocess died when trying to import `onnx.reference` and related ONNX testing modules
2. **polars module crash** - PyInstaller subprocess crashed when importing `polars` (a dependency pulled in by ultralytics)
3. **Other testing modules** - `torch.testing`, `pytest`, `thop`, `scipy.signal` also caused issues

### Error Pattern

```
PyInstaller.isolated._parent.SubprocessDiedError: Isolated subprocess crashed while importing package 'onnx.reference'!
PyInstaller.isolated._parent.SubprocessDiedError: Isolated subprocess crashed while importing package 'polars'!
```

## Solution Applied

Added `--exclude-module` flags to both build scripts to prevent PyInstaller from analyzing these problematic modules:

### Modules Excluded

- `onnx.reference` - ONNX reference implementation (not needed for runtime)
- `onnx.reference.ops` - ONNX reference operators (not needed for runtime)
- `torch.testing` - PyTorch testing utilities (not needed)
- `pytest` - Python testing framework (not needed)
- `polars` - Data frame library (ultralytics dependency, not used by imagedescriber)
- `thop` - PyTorch operations profiler (ultralytics dependency, not used)
- `scipy.signal` - Signal processing (can cause import issues)

### Files Modified

1. **build_imagedescriber_arm.bat** - Added 7 `--exclude-module` flags
2. **build_imagedescriber_amd.bat** - Added 7 `--exclude-module` flags

### Updated Build Commands

Both scripts now include these exclusions in the PyInstaller command:

```bat
--exclude-module "onnx.reference" ^
--exclude-module "onnx.reference.ops" ^
--exclude-module "torch.testing" ^
--exclude-module "pytest" ^
--exclude-module "polars" ^
--exclude-module "thop" ^
--exclude-module "scipy.signal" ^
```

## Impact

### Functionality
- **No functionality lost** - All excluded modules are:
  - Testing/development tools not needed in production
  - Optional dependencies from ultralytics not used by imagedescriber
  - Reference implementations not used at runtime

### Benefits
- Builds can now complete without subprocess crashes
- Smaller executable size (excluded unnecessary modules)
- Faster build times (fewer modules to analyze)

## Testing Needed

Both build scripts should now work:

1. **ARM64 Build**: `imagedescriber\build_imagedescriber_arm.bat`
2. **AMD64 Build**: `imagedescriber\build_imagedescriber_amd.bat`

### Expected Behavior
- Build process should complete without PyInstaller subprocess crashes
- Executable should be created in `dist\imagedescriber\`
- All imagedescriber functionality should work normally

### Verify These Features Work
- ✓ GUI launches
- ✓ Image loading and display
- ✓ All AI providers (OpenAI, Claude, Ollama, Hugging Face, ONNX, GroundingDINO)
- ✓ Prompt selection
- ✓ Chat functionality
- ✓ Export features

## Technical Notes

### Why These Modules Were Being Imported

PyInstaller performs static analysis to find all imports. Even if imagedescriber doesn't directly import these modules, they can be pulled in as:

1. **Transitive dependencies**: ultralytics → polars, thop
2. **Conditional imports**: torch → torch.testing (in development mode)
3. **Optional features**: onnxruntime → onnx.reference (for validation)

### Alternative Solutions Considered

1. ~~Create custom import hooks~~ - Too complex, maintenance burden
2. ~~Modify source to avoid imports~~ - Would affect development/testing
3. **✓ Exclude at build time** - Clean, simple, no source changes

## Future Considerations

If more modules cause similar issues:
- Add them to the `--exclude-module` list
- Document in this file
- Consider if the module is actually needed for runtime

## Build Environment

- **PyInstaller**: 6.16.0
- **Python**: 3.13.7
- **Platform**: Windows 11
- **Virtual Environment**: `.venv` in project root
