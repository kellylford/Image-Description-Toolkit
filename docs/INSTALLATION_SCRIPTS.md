# IDT Installation Scripts Documentation

## Overview

The Image Description Toolkit includes automated installation scripts that set up the complete toolkit with proper directory structure from release packages.

## Files Created

### Installation Scripts

1. **`install_idt_amd64.bat`** - Installer for AMD64/x86_64 architecture (most Windows PCs)
2. **`install_idt_arm64.bat`** - Installer for ARM64 architecture (ARM-based Windows PCs)

### Supporting Documentation

3. **`RELEASES_README.md`** - Comprehensive installation guide (copied to `releases/README.md`)

## How It Works

### Automated Installation Process

The installation scripts perform the following steps:

1. **Package Detection**
   - Automatically finds all required release packages in the current directory
   - Validates that all four packages are present
   - Reports any missing packages

2. **Directory Structure Creation**
   ```
   idt/
   ├── (main toolkit files)
   ├── Viewer/
   ├── ImageDescriber/
   └── PromptEditor/
   ```

3. **Package Extraction**
   - Extracts `ImageDescriptionToolkit_v*.zip` to `idt/`
   - Extracts `viewer_v*_[arch].zip` to `idt/Viewer/`
   - Extracts `prompt_editor_v*_[arch].zip` to `idt/PromptEditor/`
   - Extracts `imagedescriber_v*_[arch].zip` to `idt/ImageDescriber/`

4. **Verification**
   - Reports success or failure for each extraction
   - Provides next steps and usage instructions

### Key Features

- **Version Agnostic**: Uses wildcards to match any version number
- **Architecture Specific**: Separate scripts for AMD64 and ARM64
- **Existing Installation Detection**: Warns if `idt/` directory exists
- **User Confirmation**: Prompts before overwriting existing installation
- **Error Handling**: Reports missing packages and extraction failures

## Package Naming Convention

The scripts expect these package naming patterns:

| Package | Naming Pattern | Example |
|---------|---------------|---------|
| Main Toolkit | `ImageDescriptionToolkit_v*.zip` | `ImageDescriptionToolkit_v1.0.0.zip` |
| Viewer (AMD64) | `viewer_v*_amd64.zip` | `viewer_v1.0.0_amd64.zip` |
| Viewer (ARM64) | `viewer_v*_arm64.zip` | `viewer_v1.0.0_arm64.zip` |
| Prompt Editor (AMD64) | `prompt_editor_v*_amd64.zip` | `prompt_editor_v1.0.0_amd64.zip` |
| Prompt Editor (ARM64) | `prompt_editor_v*_arm64.zip` | `prompt_editor_v1.0.0_arm64.zip` |
| ImageDescriber (AMD64) | `imagedescriber_v*_amd64.zip` | `imagedescriber_v1.0.0_amd64.zip` |
| ImageDescriber (ARM64) | `imagedescriber_v*_arm64.zip` | `imagedescriber_v1.0.0_arm64.zip` |

## Usage Instructions

### For End Users

1. Download the appropriate installer script for your architecture
2. Download all four release packages with matching version numbers
3. Place all files in an empty folder
4. Run the installer script

### AMD64 Example
```batch
install_idt_amd64.bat
```

### ARM64 Example
```batch
install_idt_arm64.bat
```

## Integration with Build Process

The installation scripts are automatically included in the release process:

### In `packageitall.bat`

```batch
[5/5] Copying installer scripts to releases...
- Copies install_idt_amd64.bat to releases/
- Copies install_idt_arm64.bat to releases/
- Copies RELEASES_README.md to releases/README.md
```

This ensures that every release includes the necessary installation tools.

## Architecture Detection

Users can determine their architecture by:

### PowerShell Method
```powershell
python -c "import platform; print(platform.machine())"
```

### Windows Settings
- Windows 11: Settings → System → About → System type
- Look for "x64-based processor" (AMD64) or "ARM64-based processor"

## Error Handling

### Missing Packages

If any required package is missing, the script will:
1. Report which packages are missing
2. List the expected filename pattern
3. Exit without creating any directories

Example output:
```
ERROR: Viewer package not found (viewer_v*_amd64.zip)
ERROR: 1 package(s) missing!
```

### Existing Installation

If `idt/` directory already exists:
1. Warns the user
2. Prompts: "Do you want to remove it and reinstall [Y/N]?"
3. User can choose to cancel or proceed with reinstallation

### Extraction Failures

If any extraction fails:
1. Reports specific package that failed
2. Exits with error code
3. Partial installation may exist (can be removed manually)

## Post-Installation Steps

The installer provides clear next steps:

1. **Install Ollama**
   - Required for AI features
   - Download from https://ollama.com

2. **Pull Vision Model**
   ```
   ollama pull llava
   ```

3. **Run Interactive Guide**
   ```
   cd idt
   idt guideme
   ```

4. **Optional: Add to PATH**
   - For easy access to `idt.exe` from anywhere

## Testing the Installers

### Manual Test Procedure

1. Run `packageitall.bat` to create all packages
2. Navigate to `releases/` directory
3. Copy all `.zip` files and `install_idt_amd64.bat` to a test folder
4. Run the installer
5. Verify directory structure
6. Test each executable

### Automated Test (Future Enhancement)

Could create a test script that:
- Creates temp directory
- Copies release files
- Runs installer
- Validates structure
- Cleans up

## Differences Between AMD64 and ARM64 Scripts

The only difference between the two scripts is the `ARCH` variable:

- **AMD64**: `set ARCH=amd64`
- **ARM64**: `set ARCH=arm64`

This affects:
- Package name matching patterns
- Error messages
- Display output

All other logic is identical.

## Maintenance Notes

### When Adding New Components

If adding new GUI applications:
1. Create package in corresponding build script
2. Add package to `packageitall.bat`
3. Update both installer scripts to:
   - Add new directory creation
   - Add package detection
   - Add extraction step
   - Update summary display

### When Changing Package Names

If package naming conventions change:
1. Update the `for %%f in (...)` patterns in both installers
2. Update RELEASES_README.md
3. Update this documentation

### Version Number Changes

No changes needed - scripts use wildcards to match any version.

## Future Enhancements

Potential improvements:

1. **Single Installer with Auto-Detection**
   - Detect architecture automatically
   - Use single script for both architectures

2. **Linux/macOS Support**
   - Shell script equivalents
   - Cross-platform installation

3. **Checksum Verification**
   - Verify package integrity before extraction
   - Include checksums in release

4. **Uninstaller Script**
   - Clean removal of IDT installation
   - Preserve user data/workspaces

5. **Update Script**
   - In-place updates without full reinstall
   - Preserve configuration files

## Related Files

- `packageitall.bat` - Creates all packages and copies installers
- `package_idt.bat` - Packages main toolkit
- `viewer/package_viewer.bat` - Packages viewer
- `prompt_editor/package_prompt_editor.bat` - Packages prompt editor
- `imagedescriber/package_imagedescriber.bat` - Packages imagedescriber
- `RELEASES_README.md` - End-user installation guide

## Accessibility Considerations

The installers are designed to be accessible:

1. **Clear Console Output**
   - Step-by-step progress indicators
   - Clear success/error messages

2. **User Confirmation**
   - Pauses at end for review
   - Prompts before destructive operations

3. **Error Messages**
   - Specific and actionable
   - Indicate exact missing packages

## Troubleshooting

### "Package not found" errors

**Cause**: Missing or incorrectly named package files

**Solution**: 
- Ensure all packages are in the same directory as installer
- Verify package names match expected patterns
- Check version numbers match across all packages

### "Failed to extract" errors

**Cause**: Corrupted package or PowerShell issues

**Solution**:
- Re-download the package
- Verify ZIP file is not corrupted
- Ensure PowerShell is available
- Try manual extraction

### Installer runs but programs don't work

**Cause**: Architecture mismatch

**Solution**:
- Verify you used the correct installer (amd64 vs arm64)
- Check your system architecture
- Use matching packages

## License

These installation scripts are part of the Image Description Toolkit and are subject to the same license as the main project.
