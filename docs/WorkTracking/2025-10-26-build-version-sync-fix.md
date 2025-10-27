# Build System Version Sync Fix

## Issue
`build_installer.bat` was hardcoded to look for version `3.0.1` files, but the `VERSION` file contains `3.0.0`, causing the installer build to fail with "file not found" errors.

## Root Cause
- `VERSION` file: `3.0.0`
- `build_installer.bat`: hardcoded to `3.0.1`
- `installer.iss`: hardcoded to `3.0.1`
- Mismatch prevented installer build from finding the packaged zip files

## Solution Applied

### 1. Fixed `build_installer.bat`
- Now reads version dynamically from `VERSION` file
- Uses `%VERSION%` variable throughout instead of hardcoded `3.0.1`
- Checks for files matching the actual version: `ImageDescriptionToolkit_v%VERSION%.zip`, etc.

### 2. Fixed `installer.iss`
- Changed from hardcoded `#define MyAppVersion "3.0.1"`
- Now reads dynamically: Opens VERSION file, reads content, trims whitespace
- All references to version now use the `{#MyAppVersion}` constant

## Files Changed
- `BuildAndRelease/build_installer.bat` - reads VERSION file, uses %VERSION% variable
- `BuildAndRelease/installer.iss` - uses FileOpen/FileRead to get version from VERSION file

## Testing
To verify the fix works:
```batch
cd BuildAndRelease
build_installer.bat
```

Should now find all `v3.0.0` files and build the installer successfully.

## For Future Releases
To bump version for a new release:
1. Edit `VERSION` file (single source of truth)
2. Run `releaseitall.bat` - all scripts now read from VERSION file
3. No need to edit build scripts manually

## Related to Metadata Changes
The metadata suffix changes in `scripts/image_describer.py` will be included in the frozen executable because:
- `final_working.spec` line 21: `('../scripts/image_describer.py', 'scripts')` - includes the Python source
- PyInstaller bundles the script into the executable
- When users run the frozen `idt.exe`, they get the updated metadata format
