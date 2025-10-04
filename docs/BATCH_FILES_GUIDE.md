# Workflow Batch File Examples

These batch files demonstrate how to use the **end-to-end workflow** with different AI providers.

## Quick Start

1. **Pick the provider you want to use** (see comparison below)
2. **Edit the `.bat` file** - change `INPUT_DIR` to your images folder
3. **Double-click the `.bat` file** to run
4. **View results** in the auto-opened viewer

---

## Provider Comparison

| Provider | Cost | Location | Speed | Quality | Notes |
|----------|------|----------|-------|---------|-------|
| **Ollama** | FREE | Local | Fast | Good | Best for privacy, offline use |
| **ONNX** | FREE | Local | Very Fast | Good | Uses YOLO + Ollama hybrid |
| **HuggingFace** | FREE | Local | Medium | OK | BLIP/GIT models, no prompts |
| **OpenAI** | $$ | Cloud | Fast | Excellent | Requires API key, costs money |

**Recommendation for most users: Start with Ollama**

---

## Available Batch Files

### 1. `run_ollama.bat` - Ollama Provider (Local AI)
**Best for**: Privacy, offline use, most common choice

**What you need**:
- Install Ollama from https://ollama.ai
- Pull a model: `ollama pull llava`
- Make sure Ollama is running

**How it works**:
- Runs completely on your computer
- No internet needed (after model download)
- No API keys required
- Free forever

**Models to try**:
- `llava` - Most popular (4GB)
- `llava:13b` - Better quality (8GB)
- `moondream` - Fastest/smallest (2GB)

---

### 2. `run_onnx.bat` - ONNX Provider (Hardware-Accelerated)
**Best for**: Speed, accuracy, object detection

**What you need**:
- Ollama installed and running (it uses Ollama for descriptions)
- Python packages: `pip install onnxruntime ultralytics`

**How it works**:
- **Step 1**: YOLO detects objects in image (super fast)
- **Step 2**: Passes detected objects to Ollama
- **Step 3**: Ollama writes description using object info
- **Result**: More accurate, detailed descriptions

**Hardware acceleration**:
- DirectML (Windows GPU/NPU)
- CUDA (NVIDIA GPU)
- CPU fallback

---

### 3. `run_openai.bat` - OpenAI Provider (Cloud AI)
**Best for**: Best possible quality, willing to pay

**What you need**:
- OpenAI API key from https://platform.openai.com/api-keys
- Save API key to a text file
- Internet connection

**How it works**:
- Sends images to OpenAI servers
- Uses GPT-4o vision model
- Returns descriptions

**Cost** (approximate):
- `gpt-4o-mini`: $0.003 per image
- `gpt-4o`: $0.01 per image

**Example**: 100 images with gpt-4o-mini = $0.30

---

### 4. `run_huggingface.bat` - HuggingFace Provider (Local AI)
**Best for**: Experimenting with different models

**What you need**:
- Python packages: `pip install transformers torch pillow`
- Good RAM (8GB+)

**How it works**:
- Uses BLIP, GIT, or ViT models
- Models run locally (no API key!)
- First run downloads model (~1-2GB)
- Subsequent runs are faster

**Important**: HuggingFace models do NOT support custom prompts. They generate captions based on how they were trained.

**Models available**:
- `Salesforce/blip-image-captioning-base` (recommended)
- `Salesforce/blip-image-captioning-large` (better quality)
- `microsoft/git-base-coco`

---

### 5. `run_complete_workflow.bat` - Full End-to-End
**Best for**: Videos + images in one go

**What it does**:
1. Extracts frames from videos
2. Converts HEIC images to JPG
3. Generates descriptions
4. Creates HTML gallery
5. Opens viewer

**Use case**: You have vacation videos and want to extract frames, get descriptions, and browse everything in a gallery.

---

## How to Customize

### 1. Edit Settings at Top of .bat File

Every `.bat` file has a section like this:
```batch
REM ======== EDIT THESE SETTINGS ========

REM Where are your images?
set INPUT_DIR=C:\Users\kelly\Pictures\TestPhotos

REM Which model?
set MODEL=llava

REM What style?
set PROMPT_STYLE=narrative
```

### 2. Common Settings

**INPUT_DIR**: 
- Can be a folder: `C:\Users\kelly\Pictures\Hawaii`
- Can be a single image: `C:\Users\kelly\Desktop\photo.jpg`
- Can contain videos (for `run_complete_workflow.bat`)

**MODEL**:
- **Ollama**: llava, llava:13b, moondream, llava:latest
- **ONNX**: llava (used for Ollama descriptions)
- **OpenAI**: gpt-4o-mini, gpt-4o
- **HuggingFace**: Salesforce/blip-image-captioning-base, etc.

**PROMPT_STYLE**:
- `narrative` - Story-like, natural descriptions
- `detailed` - Comprehensive, everything visible
- `concise` - Short, to the point
- `technical` - Camera settings, composition
- `accessibility` - For screen readers

### 3. Workflow Steps

Default is: `--steps describe,html,viewer`

You can customize:
- `describe` - Only generate descriptions
- `describe,html` - Descriptions + HTML gallery
- `video,describe,html` - Extract frames, describe, gallery
- `video,convert,describe,html,viewer` - Everything!

---

## Troubleshooting

### "ERROR: Ollama is not running"
- Check system tray for Ollama icon
- If not there, download from https://ollama.ai
- Start Ollama before running the script

### "Model not found"
The script will try to download it automatically. If that fails:
```bash
ollama pull llava
```

### "ERROR: Input directory does not exist"
- Edit the `.bat` file
- Change `INPUT_DIR` to a real folder on your computer
- Use full path like `C:\Users\YourName\Pictures\Photos`

### "HuggingFace transformers not installed"
```bash
pip install transformers torch pillow
```

### "OpenAI API key invalid"
- Check your API key file contains ONLY the key (no extra text)
- Make sure you have credits: https://platform.openai.com/account/billing
- API key should look like: `sk-proj-...`

---

## Output

All workflows create a folder like:
```
wf_<provider>_<model>_<style>_<timestamp>/
```

Examples:
- `wf_ollama_llava_narrative_20251004_143022/`
- `wf_onnx_llava_detailed_20251004_150315/`
- `wf_openai_gpt-4o-mini_technical_20251004_152045/`

Inside you'll find:
- `logs/` - Processing logs
- `descriptions.txt` - All descriptions in one file
- `gallery.html` - Browseable gallery
- Individual image description files

---

## Examples

### Example 1: Describe vacation photos with Ollama
1. Edit `run_ollama.bat`
2. Set `INPUT_DIR=C:\Users\kelly\Pictures\Vacation`
3. Set `MODEL=llava`
4. Set `PROMPT_STYLE=narrative`
5. Double-click `run_ollama.bat`

### Example 2: Fast object detection with ONNX
1. Edit `run_onnx.bat`
2. Set `INPUT_DIR=C:\Users\kelly\Pictures\Products`
3. Set `MODEL=llava`
4. Set `PROMPT_STYLE=detailed`
5. Double-click `run_onnx.bat`

### Example 3: Best quality with OpenAI
1. Get API key from https://platform.openai.com/api-keys
2. Save to `C:\Users\kelly\Desktop\openai_key.txt`
3. Edit `run_openai.bat`
4. Set `API_KEY_FILE=C:\Users\kelly\Desktop\openai_key.txt`
5. Set `INPUT_DIR=C:\Users\kelly\Pictures\Portfolio`
6. Set `MODEL=gpt-4o`
7. Double-click `run_openai.bat`

### Example 4: Process videos
1. Edit `run_complete_workflow.bat`
2. Set `INPUT_DIR=C:\Users\kelly\Videos\Presentation`
3. Set `FPS=1` (1 frame per second)
4. Set `MODEL=llava`
5. Double-click `run_complete_workflow.bat`

---

## Tips

1. **Start small**: Test with a folder of 5-10 images first
2. **Check logs**: If something fails, look in the `logs/` folder
3. **Try different prompts**: narrative, detailed, technical, etc.
4. **Compare providers**: Run same images through Ollama, ONNX, OpenAI
5. **Save your edits**: Once you customize a `.bat`, save a copy

---

## What These Scripts Do vs. What They Don't Do

### ✅ These Scripts DO:
- Run the **end-to-end workflow** 
- Process folders of images
- Generate descriptions using AI
- Create HTML galleries
- Open viewer automatically
- Show examples of different providers

### ❌ These Scripts DON'T:
- Replace the GUI (ImageDescriber.py is still the main app)
- Show all possible options (see `python workflow.py --help`)
- Handle resume/error recovery (workflow.py does that)
- Replace manual command-line usage

**Purpose**: These are **EXAMPLES** showing common use cases. For advanced usage, use the command line directly or the GUI.

---

## Command Line Reference

If you want more control than the batch files provide:

```bash
# Basic workflow
python workflow.py <folder> --provider ollama --model llava

# With all options
python workflow.py <folder> \
  --steps describe,html,viewer \
  --provider onnx \
  --model llava \
  --prompt-style narrative \
  --config workflow_config.json

# Video extraction
python workflow.py <folder> \
  --steps video,describe,html \
  --provider ollama \
  --model moondream

# OpenAI with API key
python workflow.py <folder> \
  --provider openai \
  --model gpt-4o-mini \
  --api-key-file C:\path\to\key.txt
```

---

## Files in This Directory

- `run_ollama.bat` - Ollama (local, free, most popular)
- `run_onnx.bat` - ONNX + YOLO (fast, accurate)
- `run_openai.bat` - OpenAI GPT-4o (best quality, costs money)
- `run_huggingface.bat` - HuggingFace BLIP (local, alternative)
- `run_complete_workflow.bat` - Full pipeline (videos to gallery)
- `README.md` - This file

---

## Last Updated
October 4, 2025

## Questions?
These batch files are **examples only**. For the full GUI experience, use `ImageDescriber.py`. For maximum flexibility, use `workflow.py` from the command line.
