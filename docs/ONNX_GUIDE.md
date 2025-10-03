# ONNX Setup Guide for Image Description

## Overview

ONNX (Open Neural Network Exchange) is a **free, local, optimized AI provider** that runs Microsoft's Florence-2 vision models on your computer. This guide shows you how to set up and use ONNX for image description in the Image Description Toolkit.

## Why Use ONNX?

✅ **Advantages:**
- **Free** - No API costs or subscriptions
- **Private** - Images never leave your computer
- **Optimized** - ONNX Runtime provides hardware-accelerated inference
- **High Quality** - Florence-2 models from Microsoft are excellent for image understanding
- **Offline** - Works without internet (after initial model download)
- **No limits** - Process unlimited images
- **Cross-platform** - Works on CPU, NVIDIA GPU, AMD GPU, Apple Silicon

❌ **Considerations:**
- Initial model download (~700MB for florence-2-large)
- Requires local resources (RAM/GPU)
- Slightly slower than cloud APIs on CPU-only systems
- Limited to Florence-2 models (but they're very good!)

## Requirements

- **Operating System**: Windows, macOS, or Linux
- **Python**: 3.8 or higher
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 2GB free space for model cache
- **GPU**: Optional but recommended (NVIDIA, AMD, or Apple Silicon)

## Installation

### Step 1: Install ONNX Runtime

ONNX Runtime provides the inference engine:

```bash
pip install onnxruntime
```

**For GPU acceleration** (optional but recommended):

**NVIDIA GPU:**
```bash
pip install onnxruntime-gpu
```

**AMD GPU or Apple Silicon:**
```bash
# Use standard onnxruntime (includes DirectML on Windows, CoreML on macOS)
pip install onnxruntime
```

### Step 2: Verify Installation

```bash
python -c "import onnxruntime; print(f'ONNX Runtime {onnxruntime.__version__} installed')"
```

Should output:
```
ONNX Runtime 1.x.x installed
```

### Step 3: Model Download (Automatic)

The Florence-2 model downloads automatically on first use:
- **florence-2-base**: ~350MB (faster, good quality)
- **florence-2-large**: ~700MB (slower, better quality)

Model is cached in:
- Windows: `C:\Users\YourName\.cache\torch\hub\checkpoints\`
- macOS/Linux: `~/.cache/torch/hub/checkpoints/`

**No manual download needed!** The batch file handles this automatically.

## Using the Batch File

### Quick Start

1. **Edit the batch file**
   - Open `run_onnx.bat` in a text editor
   - Set `IMAGE_PATH` to your image or folder
   - Example: `set IMAGE_PATH=C:\Users\YourName\Pictures\photo.jpg`

2. **Run the batch file**
   - Double-click `run_onnx.bat`
   - OR run from command prompt: `run_onnx.bat`
   - First run downloads model (~700MB, one-time only)

3. **Find your results**
   - Look for `wf_onnx_florence-2-large_narrative_*` folder
   - Open `descriptions.txt` to see image descriptions

### Configuration Options

Edit these settings in the batch file:

```batch
REM Path to image or folder
set IMAGE_PATH=C:\path\to\your\images

REM Steps to run
set STEPS=describe
REM Or: set STEPS=extract,describe,html,viewer

REM Model to use
set MODEL=florence-2-large
REM Or: set MODEL=florence-2-base (faster but slightly lower quality)

REM Prompt style
set PROMPT_STYLE=narrative
REM Options: narrative, detailed, concise, artistic, technical, colorful
```

## Command-Line Usage

You can also run the workflow directly from the command line:

### Single Image
```bash
python workflow.py "C:\path\to\image.jpg" --provider onnx --model florence-2-large --prompt-style narrative
```

### Folder of Images
```bash
python workflow.py "C:\path\to\images" --provider onnx --model florence-2-large --prompt-style narrative
```

### Full Workflow
```bash
python workflow.py "C:\path\to\images" --steps extract,describe,html,viewer --provider onnx --model florence-2-large --prompt-style narrative
```

## Model Comparison

| Model | Size | Speed | Quality | RAM Required | Best For |
|-------|------|-------|---------|--------------|----------|
| **florence-2-base** | 350MB | Faster | Good | 4-6GB | Quick processing, CPU systems |
| **florence-2-large** | 700MB | Slower | Excellent | 6-8GB | Best quality, GPU systems |

**Recommendation**: Use `florence-2-large` unless:
- You're on a CPU-only system (use base)
- You have limited RAM (use base)
- You need maximum speed (use base)

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

## Troubleshooting

### "ONNX Runtime not found"

**Cause**: onnxruntime not installed

**Solution**:
```bash
pip install onnxruntime
```

The batch file will try to auto-install, but you can do it manually.

### Model Download Fails

**Cause**: Network issues or insufficient disk space

**Solutions**:
1. Check internet connection
2. Free up disk space (2GB minimum)
3. Try again - the script will resume download
4. Check firewall isn't blocking downloads
5. Try manual download from Hugging Face

### Out of Memory Errors

**Cause**: Not enough RAM for model

**Solutions**:
1. Use `florence-2-base` instead of `florence-2-large`
2. Close other applications
3. Process smaller images or one at a time
4. Upgrade RAM if possible (16GB recommended)

### Slow Processing on CPU

**Cause**: Running on CPU instead of GPU

**Solutions**:
1. Use `florence-2-base` (faster model)
2. Install GPU-accelerated ONNX Runtime:
   - NVIDIA: `pip install onnxruntime-gpu`
   - AMD/Apple: Already optimized in standard `onnxruntime`
3. Process images in smaller batches
4. Consider using Ollama with moondream for CPU-only systems

### "Module not found" Errors

**Cause**: Missing dependencies

**Solution**:
```bash
pip install -r requirements.txt
```

Ensure all project dependencies are installed.

### Cache Directory Issues

**Cause**: No write permissions to cache directory

**Solutions**:
1. Run command prompt as administrator (Windows)
2. Check permissions on `~/.cache/` directory
3. Manually create directory:
   ```bash
   mkdir -p ~/.cache/torch/hub/checkpoints/
   ```

## Performance Tips

### For CPU-Only Systems

```batch
REM Use faster model
set MODEL=florence-2-base

REM Process fewer images at once
set IMAGE_PATH=C:\path\to\single_image.jpg

REM Use concise prompts for speed
set PROMPT_STYLE=concise
```

### For GPU Systems

```batch
REM Use best quality model
set MODEL=florence-2-large

REM Can process larger batches
set IMAGE_PATH=C:\path\to\image_folder

REM Use detailed prompts
set PROMPT_STYLE=detailed
```

### First-Time Setup

**First run will take longer** due to model download:
- florence-2-base: ~5 minutes download
- florence-2-large: ~10-15 minutes download

**Subsequent runs are much faster** - model is cached!

## GPU Acceleration

### NVIDIA GPU

1. **Install CUDA Toolkit** (if not already installed)
   - Download from: https://developer.nvidia.com/cuda-downloads
   - Version 11.8 or 12.x recommended

2. **Install GPU-accelerated ONNX Runtime**
   ```bash
   pip uninstall onnxruntime
   pip install onnxruntime-gpu
   ```

3. **Verify GPU is detected**
   ```bash
   python -c "import onnxruntime as ort; print(ort.get_available_providers())"
   ```
   Should include `'CUDAExecutionProvider'`

### AMD GPU (Windows)

1. **Standard ONNX Runtime includes DirectML**
   ```bash
   pip install onnxruntime
   ```

2. **DirectML auto-detects AMD GPUs** on Windows

### Apple Silicon (M1/M2/M3)

1. **Standard ONNX Runtime includes CoreML**
   ```bash
   pip install onnxruntime
   ```

2. **CoreML auto-optimizes** for Apple Silicon

## Cost Comparison

| Provider | Cost per 1,000 Images |
|----------|----------------------|
| **ONNX** | **$0.00 (Free!)** |
| **Ollama** | $0.00 (Free!) |
| OpenAI gpt-4o-mini | ~$1-2 |
| OpenAI gpt-4o | ~$10-20 |
| HuggingFace | ~$0-5 (varies) |

ONNX is completely free - only initial setup and electricity costs!

## Comparison with Other Providers

### ONNX vs Ollama

| Feature | ONNX | Ollama |
|---------|------|--------|
| **Cost** | Free | Free |
| **Quality** | Excellent (Florence-2) | Good-Excellent (varies by model) |
| **Speed** | Fast (optimized) | Medium-Fast |
| **Models** | Florence-2 only | Many models available |
| **Setup** | Minimal | Requires Ollama install |
| **RAM Usage** | 4-8GB | 4-16GB (varies) |

**Choose ONNX if you want**:
- Optimized performance
- Specific Florence-2 model
- Minimal setup

**Choose Ollama if you want**:
- Multiple model options
- Flexibility to switch models
- Larger ecosystem

### ONNX vs OpenAI

| Feature | ONNX | OpenAI |
|---------|------|--------|
| **Cost** | Free | Paid ($0.01-0.20 per image) |
| **Privacy** | Fully private | Data sent to cloud |
| **Speed** | Medium | Very fast |
| **Quality** | Excellent | Excellent |
| **Internet** | Not needed (after download) | Required |

## Advanced Usage

### Batch Processing Large Folders

For processing many images efficiently:

```batch
REM Use faster model for large batches
set MODEL=florence-2-base
set IMAGE_PATH=C:\Photos\LargeCollection
set STEPS=describe
```

### High-Quality Single Image

For best possible description:

```batch
REM Use best model and detailed prompt
set MODEL=florence-2-large
set PROMPT_STYLE=detailed
set IMAGE_PATH=C:\important_image.jpg
```

### Integration with Workflow

Full workflow with HTML gallery:

```batch
set STEPS=extract,describe,html,viewer
set MODEL=florence-2-large
set PROMPT_STYLE=narrative
set IMAGE_PATH=C:\PhotoShoot_2025
```

## Example Workflows

### Photography Organization

```batch
REM Process entire photoshoot with metadata extraction
set IMAGE_PATH=C:\Photos\Photoshoot_2025
set STEPS=extract,describe,html,viewer
set MODEL=florence-2-large
set PROMPT_STYLE=detailed
```

### Quick Batch Description

```batch
REM Fast description of many images
set IMAGE_PATH=C:\Photos\Batch
set STEPS=describe
set MODEL=florence-2-base
set PROMPT_STYLE=concise
```

### Art Gallery Catalog

```batch
REM Artistic analysis of artwork
set IMAGE_PATH=C:\Art\Gallery
set STEPS=describe,html
set MODEL=florence-2-large
set PROMPT_STYLE=artistic
```

## Getting Help

- **ONNX Runtime Docs**: https://onnxruntime.ai/docs/
- **Florence-2 Model**: https://huggingface.co/microsoft/Florence-2-large
- **IDT Documentation**: See `docs/` folder
- **Ollama Guide** (alternative): `docs/OLLAMA_GUIDE.md`
- **OpenAI Guide** (cloud option): `docs/OPENAI_SETUP_GUIDE.md`

## Summary

ONNX provides **free, optimized, local AI** for image description:

1. ✅ Install ONNX Runtime: `pip install onnxruntime`
2. ✅ Edit `run_onnx.bat` with your image path
3. ✅ Run batch file (model downloads automatically on first use)
4. ✅ Find results in `wf_onnx_*` folder
5. ✅ Subsequent runs are faster (model cached)

Perfect for users who want:
- 💰 Zero cost
- 🔒 Privacy and security
- ⚡ Optimized performance
- 🎯 High-quality Florence-2 models
- ♾️ Unlimited usage

Happy describing! 🖼️
