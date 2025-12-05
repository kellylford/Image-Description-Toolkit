# Image Description Prompt Editor

A user-friendly Qt6 application for editing image description prompts and configuration settings without needing to manually edit JSON files. **Now with multi-provider AI support!**

## Features

### Prompt Management
- **Visual prompt list** - Browse all available prompt styles in an easy-to-read list
- **Add new prompts** - Create custom prompt styles for different use cases
- **Edit existing prompts** - Modify prompt text with live character count
- **Delete prompts** - Remove unwanted prompt styles
- **Duplicate prompts** - Copy existing prompts as templates for new ones

### AI Provider Support (NEW!)
- **Multi-provider selection** - Choose from Ollama, OpenAI, Claude, Copilot, or HuggingFace
- **API key management** - Secure storage for cloud provider credentials
- **Provider-specific models** - Model list updates based on selected provider
- **Live model discovery** - Automatically detects available models for each provider
- **Command-line override** - Provider selection can be overridden via CLI flags

### Default Settings
- **Default prompt style** - Set which prompt style to use by default
- **Default AI provider** - Choose which AI provider to use (Ollama, OpenAI, etc.)
- **Default AI model** - Select the specific model for the chosen provider
- **Model refresh** - Update model list when new models are available
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
- At least one AI provider installed:
  - **Ollama** - For local models (free)
  - **OpenAI** - For cloud models (requires API key)
  - **HuggingFace** - For local Florence-2 models (free)
  - **HuggingFace** - For cloud models (requires token)
  - **Copilot** - For GitHub Copilot models (requires access)

### Setup
1. Ensure you're in the project root directory
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up your preferred AI provider:
   
   **For Ollama (local):**
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
1. **Select AI provider** - Choose Ollama, OpenAI, Claude, Copilot, or HuggingFace
2. **Configure API key** (if needed) - Enter key for OpenAI/HuggingFace or leave empty for env vars
3. **Refresh models** - Click Refresh to load available models for selected provider
4. **Edit prompts** - Select a prompt from the list and modify the text
5. **Set defaults** - Choose default prompt style, provider, and AI model
6. **Save changes** - Use Save (Ctrl+S) to save to current file
7. **Create custom configs** - Use Save As (Ctrl+Shift+S) for new files

### Provider-Specific Setup

#### Using Ollama (Local, Free)
1. Select **ollama** from AI Provider dropdown
2. Click **Refresh** to load installed models
3. Select your preferred model (e.g., moondream, llama3.2-vision)
4. No API key needed
5. Models run locally on your machine

#### Using OpenAI (Cloud, Paid)
1. Select **openai** from AI Provider dropdown
2. API Key field appears automatically
3. Enter your OpenAI API key OR leave empty to use `OPENAI_API_KEY` env var
4. Model list shows: gpt-4o, gpt-4o-mini, gpt-4-turbo, etc.
5. Select model (recommend gpt-4o-mini for cost-effectiveness)
6. Save configuration

#### Using HuggingFace (Local, Free)
1. Select **huggingface** from AI Provider dropdown
2. Model list shows: microsoft/Florence-2-base, microsoft/Florence-2-large
3. No API key needed
4. Models run locally via transformers library
5. First use will download model (~700MB)

#### Using HuggingFace Cloud (Requires Token)
1. Select **huggingface** from AI Provider dropdown
2. API Key field appears (for HuggingFace token)
3. Enter token OR leave empty to use `HUGGINGFACE_TOKEN` env var
4. Select from available vision models
5. Save configuration

#### Using Copilot (GitHub Copilot Required)
1. Select **copilot** from AI Provider dropdown
2. Requires GitHub Copilot access
3. Shows available Copilot models
4. Authentication handled via GitHub CLI

### Command-Line Override

The provider and model set in the editor are **defaults** that can be overridden:

```bash
# Config says "ollama" but you want to use OpenAI for this run
python scripts/image_describer.py /path/to/images \
  --provider openai \
  --model gpt-4o-mini \
  --api-key-file openai_key.txt \
  --prompt-style narrative
```

This flexibility allows you to:
- Set safe defaults in config (e.g., free local Ollama)
- Override for specific jobs (e.g., use OpenAI for important batches)
- Test different providers without changing config

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
- Try clicking the "Refresh" button next to the model dropdown
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
