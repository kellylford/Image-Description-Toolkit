# Ollama Setup Guide for Image Description

## Overview

Ollama is a **free, local AI provider** that runs models on your own computer. This guide shows you how to set up and use Ollama for image description in the Image Description Toolkit.

## Why Use Ollama?

✅ **Advantages:**
- **Free** - No API costs or subscriptions
- **Private** - Images never leave your computer
- **Fast** - Local processing, no network latency
- **Offline** - Works without internet connection
- **No limits** - Process unlimited images

❌ **Considerations:**
- Requires local GPU/CPU resources
- Model quality varies (usually good for image description)
- Initial model download (~2GB for moondream)
- Slower than cloud providers on CPU-only systems

## Requirements

- **Operating System**: Windows, macOS, or Linux
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 5GB free space for models
- **GPU**: Optional but recommended (NVIDIA, AMD, or Apple Silicon)

## Installation

### Step 1: Install Ollama

1. **Download Ollama**
   - Visit: https://ollama.ai
   - Download installer for your OS
   - Run installer and follow prompts

2. **Verify Installation**
   ```bash
   ollama --version
   ```
   Should show version number (e.g., `ollama version 0.1.x`)

### Step 2: Install Models

**Recommended Model: moondream**
- Best for image description
- Small size (~2GB)
- Good balance of speed and quality

```bash
ollama pull moondream
```

**Alternative Models:**

```bash
# Llama 3.2 Vision - Higher quality, larger size (~7GB)
ollama pull llama3.2-vision

# LLaVA - Good general-purpose vision model (~4GB)
ollama pull llava
```

### Step 3: Verify Model Installation

```bash
ollama list
```

Should show your installed models:
```
NAME                    ID              SIZE
moondream:latest       a3b...          2.0 GB
```

## Using the Batch File

### Quick Start

1. **Edit the batch file**
   - Open `run_ollama.bat` in a text editor
   - Set `IMAGE_PATH` to your image or folder
   - Example: `set IMAGE_PATH=C:\Users\YourName\Pictures\photo.jpg`

2. **Run the batch file**
   - Double-click `run_ollama.bat`
   - OR run from command prompt: `run_ollama.bat`

3. **Find your results**
   - Look for `wf_ollama_moondream_narrative_*` folder
   - Open `descriptions.txt` to see image descriptions

### Configuration Options

Edit these settings in the batch file:

```batch
REM Path to image or folder
set IMAGE_PATH=C:\path\to\your\images

REM Steps to run (describe only, or full workflow)
set STEPS=describe
REM Or: set STEPS=extract,describe,html,viewer

REM Model to use
set MODEL=moondream
REM Or: set MODEL=llama3.2-vision
REM Or: set MODEL=llava

REM Prompt style
set PROMPT_STYLE=narrative
REM Options: narrative, detailed, concise, artistic, technical, colorful
```

## Command-Line Usage

You can also run the workflow directly from the command line:

### Single Image
```bash
python workflow.py "C:\path\to\image.jpg" --provider ollama --model moondream --prompt-style narrative
```

### Folder of Images
```bash
python workflow.py "C:\path\to\images" --provider ollama --model moondream --prompt-style narrative
```

### Full Workflow (Extract metadata, describe, generate HTML, open viewer)
```bash
python workflow.py "C:\path\to\images" --steps extract,describe,html,viewer --provider ollama --model moondream --prompt-style narrative
```

## Prompt Styles

Choose the prompt style that fits your needs:

| Style | Best For | Description Length |
|-------|----------|-------------------|
| **narrative** | General use, balanced | Medium - detailed but readable |
| **detailed** | Maximum information | Long - comprehensive metadata |
| **concise** | Quick summaries | Short - main subjects only |
| **artistic** | Creative analysis | Medium - focuses on composition/mood |
| **technical** | Photography analysis | Medium - camera settings, technique |
| **colorful** | Color-focused | Medium - emphasizes palette and lighting |

## Model Comparison

| Model | Size | Speed | Quality | Best For |
|-------|------|-------|---------|----------|
| **moondream** | 2GB | Fast | Good | General image description (recommended) |
| **llama3.2-vision** | 7GB | Medium | Excellent | High-quality descriptions |
| **llava** | 4GB | Medium | Very Good | Balanced quality/size |

## Troubleshooting

### "Ollama is not running or not installed"

**Cause**: Ollama service not running or not in PATH

**Solutions**:
1. Make sure Ollama is installed: https://ollama.ai
2. Restart your computer after installation
3. Check Ollama is running: `ollama list`
4. Try starting Ollama manually

### "moondream model not found"

**Cause**: Model not downloaded

**Solution**:
```bash
ollama pull moondream
```

The batch file will try to auto-install, but you can do it manually.

### Slow Processing

**Cause**: Running on CPU instead of GPU

**Solutions**:
1. Use smaller model (moondream instead of llama3.2-vision)
2. Check GPU is available: Ollama will auto-detect NVIDIA/AMD GPU
3. Close other applications to free up resources
4. Process images in smaller batches

### "Connection refused" or "Connection error"

**Cause**: Ollama service not running

**Solutions**:
1. Start Ollama from command line: `ollama serve`
2. On Windows, Ollama runs as background service after install
3. Restart computer to ensure service is running
4. Check firewall isn't blocking Ollama (port 11434)

### Model Download Failed

**Cause**: Network issues or insufficient disk space

**Solutions**:
1. Check internet connection
2. Free up disk space (5GB minimum)
3. Try again: `ollama pull moondream`
4. Use VPN if downloads are blocked in your region

### Out of Memory Errors

**Cause**: Not enough RAM for model

**Solutions**:
1. Close other applications
2. Use smaller model (moondream is smallest)
3. Upgrade to 16GB RAM if possible
4. Process one image at a time instead of batches

## Advanced Usage

### Using Different Models per Project

Create custom batch files for different models:

**run_ollama_llava.bat** - For higher quality
```batch
set MODEL=llava
```

**run_ollama_vision.bat** - For maximum quality
```batch
set MODEL=llama3.2-vision
```

### Custom Prompts

Edit prompts in `scripts/image_describer_config.json`:
```json
{
  "prompt_variations": {
    "my_custom_style": "Your custom prompt here..."
  }
}
```

Then use:
```batch
set PROMPT_STYLE=my_custom_style
```

### Performance Optimization

**For CPU-only systems:**
- Use moondream (smallest, fastest)
- Process images one at a time
- Close other applications

**For GPU systems:**
- Use llama3.2-vision (best quality)
- Can process larger batches
- GPU acceleration automatic

## Cost Comparison

| Provider | Cost per 1,000 Images |
|----------|----------------------|
| **Ollama** | **$0.00 (Free!)** |
| OpenAI gpt-4o-mini | ~$1-2 |
| OpenAI gpt-4o | ~$10-20 |
| HuggingFace | ~$0-5 (varies) |

Ollama is completely free - only initial setup time and electricity costs!

## Example Workflow

### Photography Organization

```batch
REM Batch process all photos from a photoshoot
set IMAGE_PATH=C:\Photos\Photoshoot_2025
set STEPS=extract,describe,html,viewer
set MODEL=llama3.2-vision
set PROMPT_STYLE=detailed
```

Process folder → Extract EXIF → Describe images → Generate HTML gallery → Open viewer

### Quick Single Image

```batch
REM Just describe one image quickly
set IMAGE_PATH=C:\Downloads\image.jpg
set STEPS=describe
set MODEL=moondream
set PROMPT_STYLE=concise
```

Fast description with minimal overhead.

### Artistic Analysis

```batch
REM Analyze artwork with artistic focus
set IMAGE_PATH=C:\Art\Paintings
set STEPS=describe
set MODEL=llama3.2-vision
set PROMPT_STYLE=artistic
```

Detailed artistic analysis of composition, color, mood.

## Getting Help

- **Ollama Documentation**: https://github.com/ollama/ollama/blob/main/docs/README.md
- **Model Library**: https://ollama.ai/library
- **IDT Documentation**: See `docs/` folder
- **OpenAI Guide** (for comparison): `docs/OPENAI_SETUP_GUIDE.md`

## Summary

Ollama provides **free, private, local AI** for image description:

1. ✅ Install Ollama from https://ollama.ai
2. ✅ Pull model: `ollama pull moondream`
3. ✅ Edit `run_ollama.bat` with your image path
4. ✅ Run batch file
5. ✅ Find results in `wf_ollama_*` folder

Perfect for users who want:
- 💰 Zero cost
- 🔒 Privacy and security
- ⚡ Offline processing
- ♾️ Unlimited usage

Happy describing! 🖼️
