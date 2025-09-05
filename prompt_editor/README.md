# Image Description Prompt Editor

A user-friendly Qt6 application for editing image description prompts and configuration settings without needing to manually edit JSON files.

## Features

### Prompt Management
- **Visual prompt list** - Browse all available prompt styles in an easy-to-read list
- **Add new prompts** - Create custom prompt styles for different use cases
- **Edit existing prompts** - Modify prompt text with live character count
- **Delete prompts** - Remove unwanted prompt styles
- **Duplicate prompts** - Copy existing prompts as templates for new ones

### Default Settings
- **Default prompt style** - Set which prompt style to use by default
- **Default AI model** - Choose which Ollama model to use for image descriptions
- **Live model discovery** - Automatically detects installed Ollama models
- **Model refresh** - Update model list when new models are installed
- **Visual selection** - Dropdown menus show available options with descriptions

### File Operations
- **Save** - Save changes to current configuration file
- **Save As** - Create new configuration files for different workflows
- **Open** - Load different configuration files
- **Reload** - Discard changes and reload from file
- **Auto-backup** - Automatic backup files created before saving

### User Experience
- **Accessible design** - Screen reader support and keyboard navigation
- **Real-time feedback** - Character counts, modification indicators
- **Window title updates** - Shows current file and unsaved changes (*)
- **Input validation** - Prevents invalid configurations
- **Error handling** - Clear error messages for file operations

## Installation

### Prerequisites
- Python 3.8 or higher
- PyQt6 (automatically installed with requirements)
- Ollama installed and running (for model selection)

### Setup
1. Ensure you're in the project root directory
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Ensure Ollama is installed and running:
   ```bash
   ollama --version
   ```

## Usage

### Starting the Editor
```bash
# From project root
python prompt_editor/prompt_editor.py
```

### Basic Workflow
1. **Edit prompts** - Select a prompt from the list and modify the text
2. **Set defaults** - Choose default prompt style and AI model
3. **Save changes** - Use Save (Ctrl+S) to save to current file
4. **Create custom configs** - Use Save As (Ctrl+Shift+S) for new files

### Keyboard Shortcuts
- **Ctrl+S** - Save changes
- **Ctrl+Shift+S** - Save As (create new file)
- **Ctrl+O** - Open different configuration file
- **Ctrl+N** - Add new prompt
- **F5** - Reload from file
- **Ctrl+Q** - Exit application
- **Tab/Shift+Tab** - Navigate between controls

### Working with Multiple Configurations

Since the workflow system supports custom configuration files:

#### Workflow Level
```bash
python workflow.py --config my_custom_workflow.json
```

#### Step Level (in workflow_config.json)
```json
{
  "image_description": {
    "config_file": "scientific_prompts.json"
  }
}
```

#### Direct Script Level
```bash
python image_describer.py --config artistic_prompts.json
```

You can create specialized prompt configurations:
- `scientific_prompts.json` - Technical and detailed descriptions
- `artistic_prompts.json` - Creative and aesthetic focus
- `accessibility_prompts.json` - Screen reader optimized
- `social_media_prompts.json` - Engagement focused

## Configuration File Format

The editor works with JSON configuration files containing:

```json
{
  "default_prompt_style": "detailed",
  "default_model": "moondream",
  "prompt_variations": {
    "detailed": "Describe this image in detail...",
    "concise": "Describe this image concisely...",
    "artistic": "Analyze this image artistically..."
  },
  "available_models": {
    "moondream": {
      "description": "Compact and efficient for image analysis",
      "recommended": true
    }
  }
}
```

## Building Standalone Executable

### Using PyInstaller
```bash
# Install PyInstaller
pip install pyinstaller

# Build for current architecture
pyinstaller --onefile --windowed --add-data "scripts;scripts" prompt_editor/prompt_editor.py

# The executable will be in dist/prompt_editor.exe
```

### Using Build Scripts (Windows)
```bash
# For current architecture
prompt_editor/build_prompt_editor.bat

# For specific architecture
prompt_editor/build_prompt_editor_arm.bat   # ARM64
prompt_editor/build_prompt_editor_amd.bat   # AMD64
```

## Integration with Workflow System

The prompt editor seamlessly integrates with the Image Description Toolkit workflow:

1. **Create custom prompts** for different projects or use cases
2. **Save configurations** with descriptive names
3. **Reference in workflow** by specifying the config file
4. **Switch between configs** easily for different image sets

Example workflow usage:
```bash
# Process scientific images with technical prompts
python workflow.py --config workflows/scientific.json

# Process artwork with artistic prompts  
python workflow.py --config workflows/artistic.json
```

Where each workflow config references different prompt files:
```json
{
  "image_description": {
    "config_file": "prompts/scientific_prompts.json"
  }
}
```

## Troubleshooting

### Common Issues

**Editor won't start**
- Check Python version (requires 3.8+)
- Install PyQt6: `pip install PyQt6`
- Verify all dependencies: `pip install -r requirements.txt`

**Can't find configuration file**
- The editor looks for `scripts/image_describer_config.json`
- Will create a default configuration if none exists
- Use "Open" menu to browse for configuration files

**Changes not saving**
- Check file permissions in the scripts directory
- Verify the configuration file isn't read-only
- Look for error messages in the status bar

**Model dropdown is empty**
- Ensure Ollama is installed and running: `ollama --version`
- Try clicking the refresh button (🔄) next to the model dropdown
- Install vision models: `ollama pull moondream` or `ollama pull llava`
- Check Ollama service status: `ollama list`

**Model selection shows "Ollama not available"**
- Install Ollama from https://ollama.ai
- Start the Ollama service
- Verify Python ollama package: `pip install ollama`
- Restart the prompt editor after installing Ollama

## Development

### File Structure
```
prompt_editor/
├── prompt_editor.py    # Main application
├── README.md          # This documentation
├── build_prompt_editor.bat       # Build script
├── build_prompt_editor_arm.bat   # ARM64 build
└── build_prompt_editor_amd.bat   # AMD64 build
```

### Dependencies
- **PyQt6** - GUI framework
- **pathlib** - Path handling
- **json** - Configuration file parsing
- **shutil** - File operations
- **datetime** - Timestamp generation

### Contributing
When modifying the prompt editor:
1. Test with various configuration files
2. Verify keyboard navigation works
3. Check accessibility features
4. Test file operations (save, load, backup)
5. Ensure integration with workflow system

## License

This project is licensed under the MIT License - see the main project LICENSE file for details.
