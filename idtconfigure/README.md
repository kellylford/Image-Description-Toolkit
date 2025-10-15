# IDT Configure - Configuration Manager

A graphical configuration manager for the Image Description Toolkit, providing an easy-to-use interface for adjusting all configuration settings without manually editing JSON files.

## Features

### Configuration Categories

- **AI Model Settings**: Temperature, tokens, top_k, top_p, repeat penalty, and default model selection
- **Prompt Styles**: Choose default description styles (detailed, concise, narrative, artistic, technical, colorful, simple)
- **Video Extraction**: Configure frame extraction modes (time interval vs. scene change), timing, quality, and directory structure
- **Processing Options**: Adjust max image size, batch delays, compression, metadata extraction, and sorting
- **Workflow Settings**: Enable/disable workflow steps, set output directories, manage intermediate file cleanup
- **Output Format**: Control what information is included in output files (timestamps, model info, file paths, metadata)

### User Interface

- **Menu-Based Navigation**: Accessible menus for selecting configuration categories
- **Settings List**: Keyboard-navigable list of all settings in the current category
- **Explanation Panel**: Detailed descriptions of each setting
- **Current Value Display**: See current values before making changes
- **Change Dialog**: Appropriate editor for each setting type (checkboxes, spinboxes, dropdowns, text fields)

### File Management

- **Save All**: Save all configuration changes to disk (Ctrl+S)
- **Reload**: Reload configurations from disk, discarding unsaved changes (Ctrl+R)
- **Export**: Export current configurations to a backup file
- **Import**: Import configurations from a previously exported file

### Accessibility

- **Full Keyboard Support**: Navigate and edit all settings using only the keyboard
- **Screen Reader Compatible**: All controls have accessible names and descriptions
- **Clear Focus Indicators**: Visual feedback for keyboard navigation
- **Keyboard Shortcuts**: 
  - Ctrl+R: Reload configurations
  - Ctrl+S: Save all changes
  - F1: Help
  - Alt+F: File menu
  - Alt+S: Settings menu

## Requirements

### Standalone Executable

- Windows 10 or later
- No Python installation required

### Development Mode

- Python 3.8 or later
- PyQt6 6.4.0 or later

Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Running the Application

**Standalone Executable:**
```bash
idtconfigure.exe
```

**From idt CLI:**
```bash
idt configure
```

**Development Mode:**
```bash
python idtconfigure.py
```

### Changing Settings

1. **Select a Category**: Use the Settings menu to choose a category (e.g., "AI Model Settings")
2. **Navigate Settings**: Use Up/Down arrow keys or click to select a setting
3. **View Details**: The explanation panel shows details about the selected setting
4. **Change Value**: Press the "Change Setting" button or press Enter
5. **Adjust Value**: Use the appropriate control (spinbox, checkbox, dropdown, etc.)
6. **Save Changes**: Use File → Save All (Ctrl+S)

### Configuration Files

IDT Configure manages these JSON files in the `scripts/` directory:

- `image_describer_config.json`: AI model parameters, prompt styles, processing options, and output format settings
- `video_frame_extractor_config.json`: Video frame extraction mode, timing, quality, and directory settings
- `workflow_config.json`: Workflow step configuration, output directories, and cleanup options

**Important**: Changes are not automatically saved! You must use File → Save All to persist changes.

## Configuration Details

### AI Model Settings

- **Temperature** (0.0 - 2.0): Controls randomness in AI responses. Lower = more focused, higher = more creative
- **Max Tokens** (50 - 1000): Maximum number of tokens in generated descriptions
- **Top K** (1 - 100): Limits vocabulary to top K most likely tokens
- **Top P** (0.0 - 1.0): Nucleus sampling threshold
- **Repeat Penalty** (1.0 - 2.0): Penalty for repeating tokens
- **Default Model**: Which AI model to use by default

### Video Extraction

- **Extraction Mode**: 
  - `time_interval`: Extract frames at regular time intervals
  - `scene_change`: Extract frames when scene changes are detected
- **Time Interval Seconds** (0.5 - 30.0): Seconds between extracted frames (time_interval mode)
- **Scene Change Threshold** (1.0 - 100.0): Sensitivity for scene detection (scene_change mode)
- **Image Quality** (1 - 100): JPEG quality for extracted frames
- **Preserve Directory Structure**: Whether to maintain source directory structure in output

### Workflow Settings

Enable or disable individual workflow steps:
- Video extraction
- Image conversion
- Image description
- HTML generation

Configure output locations and intermediate file cleanup.

## Building

### Build Executable

```bash
build_idtconfigure.bat
```

This creates `dist\idtconfigure\idtconfigure.exe` using PyInstaller.

### Package for Distribution

```bash
package_idtconfigure.bat
```

This creates a ZIP file with:
- Executable and dependencies
- README.txt
- QUICK_START.txt
- Version information

## Tips

- **Unsaved Changes**: Changes are not saved until you use File → Save All. The title bar shows an asterisk (*) when there are unsaved changes.
- **Reload vs. Restart**: Use File → Reload (Ctrl+R) to discard unsaved changes without restarting the application.
- **Export/Import**: Create backups of your configuration before making major changes. You can also share configurations with others.
- **Manual Editing**: You can still edit configuration files manually. Use Ctrl+R to reload after manual edits.
- **Help Text**: Each setting includes a detailed explanation. Take time to read them to understand the impact of each setting.

## Troubleshooting

### Application Won't Launch

- Verify you're using Windows 10 or later
- Check that all files from the ZIP are extracted together
- Try running from Command Prompt to see error messages

### Changes Not Taking Effect

- Make sure you saved changes (File → Save All or Ctrl+S)
- If using the application while other tools are running, you may need to restart those tools to pick up the new configuration

### Configuration Files Not Found

- IDT Configure looks for configuration files in the `scripts/` directory
- Make sure IDTConfigure is in the correct location within the toolkit directory structure
- The application should be in `<toolkit_dir>/idtconfigure/`

## Documentation

For more information about the Image Description Toolkit:
- [Main Documentation](https://github.com/kellylford/Image-Description-Toolkit)
- [Issue Tracker](https://github.com/kellylford/Image-Description-Toolkit/issues)

## License

Same license as Image Description Toolkit.
