# Hugging Face Model Pre-downloading Guide

## Overview

Similar to how you can use `ollama pull` to download Ollama models ahead of time, you can now pre-download Hugging Face models for the Image Description Toolkit using the provided scripts.

## Why Pre-download?

- **Avoid waiting during processing**: Models can be 5-15GB and take 10-30 minutes to download
- **Better user experience**: No interruptions when you want to process images
- **Offline usage**: Once downloaded, models work without internet connection
- **Batch setup**: Download all models at once during off-hours

## Usage Methods

### 1. Python Script (Cross-platform)

```bash
# List available models
python download_hf_models.py --list

# Download a specific model
python download_hf_models.py --model blip2-opt
python download_hf_models.py --model llava

# Download all supported models (will take a long time!)
python download_hf_models.py --all
```

### 2. Windows Batch Script

```cmd
# List available models
download_hf_models.bat list

# Download a specific model
download_hf_models.bat blip2-opt
download_hf_models.bat llava

# Download all models
download_hf_models.bat all
```

## Available Models

| Short Name   | Full Repository                        | Description                           | Size  |
|--------------|----------------------------------------|---------------------------------------|-------|
| blip2-opt    | Salesforce/blip2-opt-2.7b            | BLIP-2 with OPT-2.7B language model  | ~5GB  |
| blip2-flan   | Salesforce/blip2-flan-t5-xl          | BLIP-2 with Flan-T5-XL               | ~11GB |
| instructblip | Salesforce/instructblip-vicuna-7b     | InstructBLIP with Vicuna-7B           | ~13GB |
| llava        | llava-hf/llava-1.5-7b-hf             | LLaVA 1.5 7B model                   | ~13GB |
| git-base     | microsoft/git-base-coco               | GIT model trained on COCO             | ~1GB  |
| minicpm      | openbmb/MiniCPM-V-2                   | MiniCPM-V-2 vision-language model    | ~8GB  |

## Storage Location

Models are stored in your Hugging Face cache directory:
- **Windows**: `C:\Users\{username}\.cache\huggingface\hub\`
- **Linux/Mac**: `~/.cache/huggingface/hub/`

## Manual Download Alternatives

### Using Hugging Face CLI
```bash
# Install HF CLI
pip install huggingface_hub

# Download specific model
huggingface-cli download Salesforce/blip2-opt-2.7b
huggingface-cli download llava-hf/llava-1.5-7b-hf
```

### Using Python Directly
```python
from transformers import AutoProcessor, AutoModelForVision2Seq

# This will download and cache the model
processor = AutoProcessor.from_pretrained("Salesforce/blip2-opt-2.7b")
model = AutoModelForVision2Seq.from_pretrained("Salesforce/blip2-opt-2.7b")
```

## Recommendations

1. **Start with smaller models**: Try `git-base` or `blip2-opt` first
2. **Check disk space**: All models combined need ~50GB
3. **Use good internet**: Download during fast connection times
4. **One at a time**: Don't download multiple large models simultaneously

## Troubleshooting

### Trust Remote Code Error
If you get a "trust_remote_code" error, the download script handles this automatically. The app has been updated to trust remote code for custom models.

### Disk Space
Check available space before downloading:
```bash
# Windows
dir C:\Users\%USERNAME%\.cache\huggingface\hub

# Linux/Mac  
du -sh ~/.cache/huggingface/hub
```

### Network Issues
- Large models may take 30+ minutes on slower connections
- Resume is automatic if download is interrupted
- Use `--resume-download` flag in manual downloads if needed

## Integration with the App

Once models are downloaded:
1. Restart the Image Description Toolkit
2. Models appear immediately in the provider dropdown
3. No download delay when first selected
4. Processing starts immediately

This is exactly like how `ollama pull llama3.2-vision` downloads the model ahead of time, so `ollama run llama3.2-vision` starts immediately without downloading.