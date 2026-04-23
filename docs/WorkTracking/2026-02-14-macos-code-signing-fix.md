# macOS Code Signing Fix - Session Summary
**Date**: February 14, 2026  
**Branch**: mac  
**Issue**: ImageDescriber.app silently failing to launch on macOS

## Problem

User reported that after building from the mac branch, ImageDescriber.app wouldn't open when double-clicked. No visible crash dialog appeared, making debugging difficult.

### Root Cause

When launching the app from terminal with error capture, the following error was revealed:

```
[PYI-4326:ERROR] Failed to load Python shared library '/var/folders/.../Python': 
dlopen(...): code signature in '/private/var/folders/.../Python.framework/Versions/3.14/Python' 
not valid for use in process: mapping process and mapped file (non-platform) have different Team IDs
```

**Explanation**: PyInstaller bundles the Python framework into the .app bundle. The embedded Python framework had a code signature with a different Team ID than the macOS app trying to load it. macOS security policies reject this for safety reasons, causing silent launch failures.

## Solution

Added post-build code signing step to all macOS build scripts:

1. **Remove conflicting signatures** from embedded libraries (`.so`, `.dylib`, Python framework)
2. **Ad-hoc sign** the entire app bundle with `-` (dash) identity for development use

### Code Signing Steps Added

```bash
# Remove existing signatures from Python framework
find dist/App.app -name "*.so" -o -name "*.dylib" | while read lib; do
    codesign --remove-signature "$lib" 2>/dev/null || true
done

# Remove signature from Python framework if present
if [ -f "dist/App.app/Contents/Frameworks/Python.framework/Versions/3.14/Python" ]; then
    codesign --remove-signature "dist/App.app/Contents/Frameworks/Python.framework/Versions/3.14/Python" 2>/dev/null || true
fi

# Ad-hoc sign the entire app bundle
codesign --force --deep --sign - dist/App.app
```

## Files Modified

1. **[imagedescriber/build_imagedescriber_wx.sh](../../imagedescriber/build_imagedescriber_wx.sh)**
   - Added code signing fix after PyInstaller build
   - Tested and verified working

2. **[idt/build_idt.sh](../../idt/build_idt.sh)**
   - Added code signing with macOS detection (`if [[ "$OSTYPE" == "darwin"* ]]`)
   - Only runs on macOS (CLI executables need signing too)

## Testing Results

### Before Fix
- ❌ `open /Applications/idt/ImageDescriber.app` - Silent failure, no app window
- ❌ Error: `code signature ... different Team IDs`

### After Fix
- ✅ `open dist/ImageDescriber.app` - App launched successfully
- ✅ Verified running: `ps aux | grep ImageDescriber` shows 2 processes (normal for macOS apps)
- ✅ No code signature errors in console logs

## Technical Notes

- **Python 3.14.3**: Build uses homebrew Python 3.14
- **PyInstaller 6.18.0**: Current version at time of fix
- **Ad-hoc signing (`-`)**: Sufficient for development/local use
- **Distribution**: For App Store or notarized distribution, would need actual Apple Developer certificate

## Impact

This fix resolves silent launch failures for both active macOS applications:
- **ImageDescriber.app** - Batch processing GUI with integrated Viewer Mode and Tools menu
- **idt** - CLI executable

_(Note: Viewer.app is deprecated - functionality now integrated into ImageDescriber as Viewer Mode)_

## Build Verification

To verify the fix works:

```bash
# Build the app
cd imagedescriber
./build_imagedescriber_wx.sh

# Launch it
open dist/ImageDescriber.app

# Verify it's running
ps aux | grep ImageDescriber
```

Expected: App window appears, no errors.

## Future Considerations

- Master build script ([BuildAndRelease/MacBuilds/builditall_macos.sh](../../BuildAndRelease/MacBuilds/builditall_macos.sh)) calls individual build scripts for idt and imagedescriber, so it inherits the fix automatically
- For official releases, consider using a proper Apple Developer certificate instead of ad-hoc signing
- Monitor for changes in future PyInstaller or macOS versions that might affect signing requirements

## References

- **PyInstaller Issue**: Code signature conflicts are a known issue when bundling Python frameworks on macOS
- **macOS Security**: Team ID validation was strengthened in recent macOS versions
- **Solution Pattern**: Remove + re-sign is the standard workaround for PyInstaller macOS builds
