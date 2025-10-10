# Executable Distribution Guide

## Overview
Image Description Toolkit is available as a standalone executable that requires **no Python installation**. Simply download, extract, and run!

## What You Get

The executable distribution (`ImageDescriptionToolkit_v[VERSION].zip`) includes:
- **ImageDescriptionToolkit.exe** - Single executable file containing all Python code
- **bat/** - Ready-to-use batch files for all supported models
- **docs/** - Complete documentation
- **scripts/** - Configuration files (JSON)
- **Descriptions/** - Output folder for workflow results
- **analysis/** - Analysis tools and results folder

## Quick Start

### 1. Download and Extract
1. Download `ImageDescriptionToolkit_v[VERSION].zip` from GitHub Releases
2. Extract to any folder (e.g., `C:\ImageDescriptionToolkit\`)
3. That's it! No installation needed.

### 2. Install Ollama (for local models)
```bash
# Download from https://ollama.ai
# Or use winget on Windows:
winget install Ollama.Ollama
```

### 3. Download Models
```bash
# Example: Download LLaVA model
ollama pull llava

# Example: Download other vision models
ollama pull llava:13b
ollama pull llava:34b
```

### 4. Run Your First Workflow
```bash
# Navigate to the extracted folder
cd C:\ImageDescriptionToolkit

# Run with Ollama model
bat\run_ollama_llava.bat

# Or with Claude (requires API key)
bat\run_claude_opus4.bat
```

## Using the Executable

### Command Line Interface

The executable provides the same CLI as the Python version:

```bash
# Run workflow
ImageDescriptionToolkit.exe workflow --model ollama/llava --images path/to/images

# Analyze statistics
ImageDescriptionToolkit.exe analyze-stats

# Analyze content
ImageDescriptionToolkit.exe analyze-content

# Combine descriptions
ImageDescriptionToolkit.exe combine

# Check models
ImageDescriptionToolkit.exe check-models

# Extract frames from video
ImageDescriptionToolkit.exe extract-frames path/to/video.mp4

# Show version
ImageDescriptionToolkit.exe version

# Show help
ImageDescriptionToolkit.exe help
```

### Using Batch Files (Recommended)

The easiest way to use the toolkit is through the provided batch files:

```bash
# Ollama models (local, free)
bat\run_ollama_llava.bat
bat\run_ollama_llava13b.bat
bat\run_ollama_bakllava.bat
bat\run_ollama_moondream.bat

# Cloud models (require API keys)
bat\run_claude_opus4.bat
bat\run_openai_gpt4o.bat
```

## Configuration

### JSON Configuration Files

All configuration files are in the `scripts/` directory:

- **scripts/workflow_config.json** - Main workflow settings
- **scripts/image_describer_config.json** - Image description settings
- **scripts/video_frame_extractor_config.json** - Video frame extraction settings

You can edit these files with any text editor to customize behavior.

### API Keys (for cloud models)

Set up API keys using the provided batch files:

```bash
# Claude/Anthropic
bat\setup_claude_key.bat

# OpenAI
bat\setup_openai_key.bat

# Remove keys
bat\remove_claude_key.bat
bat\remove_openai_key.bat
```

## Differences from Python Version

From a **user perspective**, there are **NO differences**:
- Same commands
- Same batch files
- Same configuration files
- Same output format
- Same features

The only difference is **under the hood**:
- Python version: Runs scripts directly with Python interpreter
- Executable version: Runs bundled executable (no Python needed)

## Analysis Tools

All analysis tools work the same way:

```bash
# Generate combined descriptions CSV
ImageDescriptionToolkit.exe combine

# Analyze workflow statistics
ImageDescriptionToolkit.exe analyze-stats

# Analyze description content
ImageDescriptionToolkit.exe analyze-content
```

Results are saved to `analysis/results/` by default.

## Troubleshooting

### Executable won't run
- **Windows SmartScreen**: Right-click → Properties → Unblock
- **Antivirus**: Add exception for ImageDescriptionToolkit.exe
- **Extract fully**: Don't run from inside ZIP file

### Models not found
```bash
# Check available Ollama models
ollama list

# Pull missing models
ollama pull llava
```

### API key errors
```bash
# For Claude
bat\setup_claude_key.bat

# For OpenAI
bat\setup_openai_key.bat
```

### Batch files open in editor
- Right-click → Open with → Command Prompt
- Or run from Command Prompt/PowerShell

### Results not found
- Check `Descriptions/` folder for workflow outputs
- Check `analysis/results/` for analysis results
- Ensure you ran workflows before analysis

## File Size Information

The executable is approximately **150-200 MB** because it includes:
- Python runtime
- All required libraries (PIL, OpenCV, Anthropic, OpenAI, Ollama SDKs)
- Model configurations
- Documentation

This is normal for bundled executables and allows zero-dependency distribution.

## Updating

To update to a new version:
1. Download new ZIP file
2. Extract to **new folder** (don't overwrite old version immediately)
3. Copy your custom configuration files from `scripts/` if you modified them
4. Test new version
5. Delete old version when satisfied

## Reverting to Python Version

If you prefer the Python version:
1. Install Python 3.8+
2. Clone repository from GitHub
3. Run `pip install -r requirements.txt`
4. Use `python workflow.py` instead of `ImageDescriptionToolkit.exe`

The Python and executable versions are fully compatible - you can switch between them at any time.

## Support

- **Documentation**: See `docs/` folder and `QUICK_START.md`
- **Issues**: GitHub Issues page
- **Questions**: GitHub Discussions

## Advanced Usage

### Custom Prompts

Edit `scripts/workflow_config.json` to customize prompts:

```json
{
  "prompts": {
    "detailed": "Provide a detailed description...",
    "technical": "Provide a technical analysis..."
  }
}
```

### Multiple Image Sets

Create separate folders for different image sets and run batch files multiple times:

```bash
# Process vacation photos
bat\run_ollama_llava.bat

# Process work diagrams  
bat\run_claude_opus4.bat
```

Each run creates a timestamped output folder in `Descriptions/`.

### Batch Processing

You can create your own batch files for custom workflows:

```batch
@echo off
REM Custom workflow for architecture photos
ImageDescriptionToolkit.exe workflow ^
  --model ollama/llava:34b ^
  --images "C:\Photos\Architecture" ^
  --prompt "technical" ^
  --output "Descriptions\architecture_analysis"
```

## What's Included in the Executable

The executable bundles:
- ✅ All Python code (workflow.py, analysis scripts, etc.)
- ✅ All required Python libraries
- ✅ Configuration file templates
- ✅ Model definitions
- ✅ Version information

NOT included (external dependencies):
- ❌ Ollama (must install separately)
- ❌ Ollama models (download with `ollama pull`)
- ❌ API keys (set with setup_*_key.bat)
- ❌ Your images/videos
- ❌ Your custom configurations

This design allows:
- **Small download size** (no huge model files)
- **Easy updates** (just replace exe)
- **Flexibility** (use any Ollama models)
- **Security** (no bundled API keys)

## Performance

The executable version has **identical performance** to the Python version:
- Same processing speed
- Same memory usage
- Same quality of results

The only difference is a **~1-2 second startup delay** while the executable unpacks itself (one-time per execution).

## License

Same license as the Python version - see `LICENSE` file.
