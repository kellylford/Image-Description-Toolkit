# Inno Setup Installer Guide

This guide explains how to build the Windows installer for the Image Description Toolkit.

## Overview

The project uses **Inno Setup** to create a professional Windows installer that:
- Installs all toolkit components in one step
- Creates Start Menu shortcuts
- Optionally adds to PATH
- Provides clean uninstallation
- Supports both AMD64 and ARM64 Windows systems

## Prerequisites

### 1. Install Inno Setup

Download and install Inno Setup 6 (or later):
- **Download**: https://jrsoftware.org/isdl.php
- **Install to**: Default location (`C:\Program Files (x86)\Inno Setup 6\`)

### 2. Build Release Packages

Before building the installer, you must create all release packages:

```bash
packageitall.bat
```

This creates:
- `ImageDescriptionToolkit_v3.0.1.zip`
- `viewer_v3.0.1.zip`
- `imagedescriber_v3.0.1.zip`
- `prompt_editor_v3.0.1.zip`

## Building the Installer

### Option 1: Using the Batch Script (Recommended)

```bash
build_installer.bat
```

The script will:
1. Check if Inno Setup is installed
2. Verify all required files exist
3. Compile the installer
4. Output: `releases\ImageDescriptionToolkit_Setup_v3.0.1.exe`

### Option 2: Manual Compilation

1. Open **Inno Setup Compiler**
2. Open `installer.iss`
3. Click **Build > Compile** (or press F9)
4. Find the installer in `releases\`

## Installer Features

### Installation Process

The installer:
1. Extracts main toolkit to `Program Files\ImageDescriptionToolkit\`
2. Extracts Viewer to `ImageDescriptionToolkit\Viewer\`
3. Extracts ImageDescriber to `ImageDescriptionToolkit\ImageDescriber\`
4. Extracts Prompt Editor to `ImageDescriptionToolkit\PromptEditor\`
5. Creates Start Menu shortcuts
6. Optionally adds `idt.exe` to PATH
7. Shows Ollama installation reminder

### User Options

During installation, users can choose:
- **Desktop Icon**: Creates ImageDescriber desktop shortcut
- **Add to PATH**: Allows running `idt` from any command prompt

### Start Menu Shortcuts

Created shortcuts:
- **Image Description Toolkit (CLI)**: Opens command prompt in toolkit directory
- **ImageDescriber**: Launches GUI application
- **Viewer**: Launches description viewer
- **Prompt Editor**: Launches prompt editor
- **Documentation**: Opens docs folder
- **Uninstall**: Removes toolkit

### Ollama Reminder

The installer displays a page reminding users to install Ollama for AI functionality, with option to open the Ollama website.

## Customization

### Version Updates

To update for a new version, edit `installer.iss`:

```pascal
#define MyAppVersion "3.0.2"  ; Change this line
```

Then update all references to version numbers in the `[Files]` section.

### Installation Directory

Default: `C:\Program Files\ImageDescriptionToolkit\`

Users can change this during installation.

### Branding

To add an icon to the installer:
1. Create/obtain a `.ico` file
2. Update in `installer.iss`:
   ```pascal
   SetupIconFile=path\to\icon.ico
   ```

## File Structure

### Inno Setup Files

- **`installer.iss`**: Main Inno Setup script
- **`build_installer.bat`**: Automated build script
- **`docs/INSTALLER_GUIDE.md`**: This documentation

### Generated Files

After compilation:
- **`releases/ImageDescriptionToolkit_Setup_v3.0.1.exe`**: Windows installer (30-50 MB)

## Distribution

### Single Installer Approach

**Recommended**: Distribute only the installer executable
- Users download one file
- Double-click to install everything
- Professional, easy experience

### Legacy Zip Approach

**Alternative**: Continue providing individual zip files
- More flexible for advanced users
- Allows partial installations
- Maintains backward compatibility

### Hybrid Approach

**Best of both**: Provide both options
- Installer for most users
- Zip files for power users and automation

## Testing Checklist

Before releasing an installer:

- [ ] Install on clean Windows 10 system
- [ ] Install on Windows 11 system
- [ ] Test ARM64 compatibility (if available)
- [ ] Verify all shortcuts work
- [ ] Test PATH addition option
- [ ] Run `idt --help` from command prompt
- [ ] Launch all GUI applications
- [ ] Verify documentation accessible
- [ ] Test uninstaller
- [ ] Check uninstaller removes PATH entry

## Troubleshooting

### "Inno Setup not found"

- Install Inno Setup 6 from https://jrsoftware.org/isdl.php
- If installed to different location, edit `build_installer.bat` line 10

### "Required files not found"

- Run `packageitall.bat` first
- Verify files exist in `releases\` directory

### Installer too large

Current size ~30-50 MB is normal due to:
- Bundled Python runtime in executables
- Multiple Qt GUI applications
- PyInstaller overhead

To reduce size:
- Use UPX compression in PyInstaller specs
- Consider external downloads for large components

### PATH not working after install

- May require logging out/in or system restart
- Environment variables update on new processes
- Test in new command prompt window

## Future Enhancements

Potential improvements:
- [ ] Auto-update mechanism
- [ ] Ollama bundled installer
- [ ] Model downloader during installation
- [ ] Custom branding with icons
- [ ] Multiple language support
- [ ] Silent installation mode for enterprise
- [ ] Portable mode option

## Support

For installer issues:
- Check build logs in Inno Setup compiler
- Review `installer.iss` syntax
- See Inno Setup documentation: https://jrsoftware.org/ishelp/

For toolkit issues:
- See main project documentation
- GitHub Issues: https://github.com/kellylford/Image-Description-Toolkit
