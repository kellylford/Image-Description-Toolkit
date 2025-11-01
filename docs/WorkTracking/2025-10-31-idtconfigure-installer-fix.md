# IDTConfigure Missing from Installer - FIXED

## Issue
IDTConfigure was being built and packaged correctly, but was **not included in the Inno Setup installer** (`ImageDescriptionToolkit_Setup_v*.exe`). 

When users ran the installer, they got:
- ✓ IDT CLI
- ✓ Viewer
- ✓ ImageDescriber  
- ✓ Prompt Editor
- ✗ **IDTConfigure** (missing)

## Root Cause
The Inno Setup script (`BuildAndRelease/installer.iss`) was missing:
1. The IDTConfigure zip file in the `[Files]` section
2. The extraction command in the `CurStepChanged` procedure
3. A Start Menu shortcut for IDTConfigure

## Fix Applied
Updated `BuildAndRelease/installer.iss` to:

1. **Add IDTConfigure package to Files section:**
```iss
; IDTConfigure
Source: "..\releases\idtconfigure_v{#MyAppVersion}.zip"; DestDir: "{tmp}"; Flags: deleteafterinstall
```

2. **Add extraction command:**
```iss
// Extract IDTConfigure
Exec('powershell.exe', '-NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Path ''' + ExpandConstant('{tmp}\idtconfigure_v{#MyAppVersion}.zip') + ''' -DestinationPath ''' + ExpandConstant('{app}\IDTConfigure') + ''' -Force"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
```

3. **Add Start Menu shortcut:**
```iss
Name: "{group}\Configure"; Filename: "{app}\IDTConfigure\idtconfigure.exe"; WorkingDir: "{app}\IDTConfigure"
```

## Additional Fixes
Corrected step counters in build scripts to show accurate progress:

**builditall.bat**: Changed "[1/4]" through "[4/4]" → "[1/5]" through "[5/5]"
**packageitall.bat**: Changed "[1/4]" through "[4/4]" → "[1/5]" through "[5/5]"

## Files Modified
- `BuildAndRelease/installer.iss` - Added IDTConfigure extraction and shortcuts
- `BuildAndRelease/builditall.bat` - Fixed step counters (1/5 through 5/5)
- `BuildAndRelease/packageitall.bat` - Fixed step counters (1/5 through 5/5)

## Verification
After this fix, the installer will:
1. Extract `idtconfigure_v*.zip` to `C:\idt\IDTConfigure\`
2. Create Start Menu shortcut: "Configure"
3. Users can launch IDTConfigure from Start Menu or by running `C:\idt\IDTConfigure\idtconfigure.exe`

## Next Steps
1. Rebuild the installer: Run `BuildAndRelease\releaseitall.bat` (or compile installer.iss manually)
2. Test installation on clean system
3. Verify IDTConfigure appears in Start Menu and runs correctly

## Note
The batch file installer (`install_idt.bat`) already worked correctly - it was only the Inno Setup installer that was missing IDTConfigure.
