# Image Description Toolkit - Installation Guide

This folder contains all the release packages for the Image Description Toolkit (IDT).

## Quick Installation (Recommended)

1. Download all files with matching version numbers:
   - `ImageDescriptionToolkit_v[VERSION].zip`
   - `viewer_v[VERSION].zip`
   - `imagedescriber_v[VERSION].zip` (includes integrated prompt editor and configuration)
   - `install_idt.bat`

2. Place all files in an empty folder

3. Run `install_idt.bat`

The installer will:
- Create an `idt\` directory
- Extract all packages to the correct locations
- Set up the complete toolkit structure

**Note:** All executables work on both AMD64 and ARM64 Windows systems. No need to choose an architecture-specific installer!

## Installation Result

After running the installer, you'll have:

```
idt\
├── idt.exe                    Main toolkit executable
├── bat\                       Example batch files
├── docs\                      Documentation
├── scripts\                   Configuration files
├── Viewer\
│   └── viewer.exe            Standalone viewer application
└── ImageDescriber\
    └── imagedescriber.exe    GUI for describing images (includes prompt editor and configuration)
```

## Manual Installation (Alternative)

If you prefer to install manually or the batch installer doesn't work:

1. Create this directory structure:
   ```
   idt\
   idt\Viewer\
   idt\ImageDescriber\
   ```

2. Extract each package:
   - `ImageDescriptionToolkit_v*.zip` → Extract to `idt\`
   - `viewer_v*.zip` → Extract to `idt\Viewer\`
   - `imagedescriber_v*.zip` → Extract to `idt\ImageDescriber\`

## Next Steps After Installation

1. **Install Ollama** (Required for AI features)
   - Download from: https://ollama.com
   - Install and start Ollama

2. **Pull a Vision Model**
   ```
   ollama pull llava
   ```
   
   Or explore other models:
   ```
   ollama search vision
   ```

3. **Run the Interactive Guide**
   ```
   cd idt
   idt guideme
   ```

4. **Explore the Tools**
   - `idt.exe` - Main CLI toolkit (see `idt --help`)
   - `Viewer\viewer.exe` - Browse image descriptions
   - `ImageDescriber\imagedescriber.exe` - GUI for batch processing (Tools menu includes prompt editor and configuration)

## Package Contents

## Package Contents

### Main Toolkit (`ImageDescriptionToolkit_v*.zip`)
- Command-line interface (`idt.exe`)
- Example batch files for common workflows
- Configuration files
- Complete documentation

### Viewer (`viewer_v*.zip`)
- Standalone viewer for browsing descriptions
- Works with HTML output from workflows
- Real-time monitoring mode
- Screen reader accessible
- Works on both AMD64 and ARM64 Windows

### ImageDescriber (`imagedescriber_v*.zip`)
- GUI application for describing images
- Workspace-based project management
- Video frame extraction
- Multiple AI provider support
- Works on both AMD64 and ARM64 Windows

### Prompt Editor (`prompt_editor_v*.zip`)
- Visual editor for AI prompts
- Preview and test prompts
- Manage prompt libraries
- Works on both AMD64 and ARM64 Windows

## System Requirements

- **Operating System:** Windows 10 or later
- **Architecture:** AMD64 (x64) or ARM64
- **Prerequisites:** None (all dependencies bundled)
- **Optional:** Ollama for local AI models

## Support

- **Documentation**: See `idt\docs\` after installation
- **GitHub**: https://github.com/kellylford/Image-Description-Toolkit
- **Quick Start**: See `idt\QUICK_START.md`

## License

See LICENSE file included in each package.
