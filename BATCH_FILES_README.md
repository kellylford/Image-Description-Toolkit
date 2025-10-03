# AI Provider Batch Files - Complete Guide

This directory contains batch files for running the Image Description Toolkit with different AI providers. Each batch file is pre-configured for a specific provider with recommended settings.

## Available Batch Files

### Single-Step Processing

| Batch File | Provider | Model | Cost | Setup Difficulty |
|------------|----------|-------|------|------------------|
| `run_ollama.bat` | Ollama | moondream | Free | Medium (local install) |
| `run_onnx.bat` | ONNX | florence-2-large | Free | Easy (pip install) |
| `run_openai_gpt4o.bat` | OpenAI | gpt-4o | Paid | Easy (API key) |
| `run_huggingface.bat` | HuggingFace | Florence-2-large | Free tier | Easy (API token) |
| `run_copilot.bat` | GitHub Copilot | gpt-4o | Subscription | Medium (GitHub CLI) |
| `run_groundingdino.bat` | GroundingDINO | comprehensive | Free | Medium (pip install) |

### Multi-Step Workflows

| Batch File | Purpose | Models Used | Best For |
|------------|---------|-------------|----------|
| `run_onnx_workflow.bat` | Fast baseline then enhance | ONNX → Other models | Cost-effective bulk processing |
| `run_groundingdino_workflow.bat` | Detection + descriptions | GroundingDINO ± Ollama | Comprehensive object analysis |

**See [docs/WORKFLOW_EXAMPLES.md](docs/WORKFLOW_EXAMPLES.md) for detailed multi-step workflow patterns.**

## Quick Start

### 1. Choose Your Provider

**For Free & Local:**
- **Ollama** - Best for privacy, unlimited use, needs GPU/RAM
- **ONNX** - Best for optimization, one-time model download

**For Free Cloud (with limits):**
- **HuggingFace** - ~1,000 requests/month free tier

**For Paid Cloud:**
- **OpenAI** - Best quality/speed, pay-per-use (~$0.01-0.02/image)
- **GitHub Copilot** - $10-19/month, includes other Copilot features

### 2. Edit Batch File

Open your chosen batch file and edit the configuration:

```batch
REM Set your image or folder path
set IMAGE_PATH=C:\Users\YourName\Pictures\photo.jpg

REM For cloud providers, set API key file path
set API_KEY_FILE=C:\path\to\your\api_key.txt
```

### 3. Run

Double-click the batch file or run from command prompt:

```bash
run_ollama.bat
```

### 4. Find Results

Look for the workflow directory:

```
wf_<provider>_<model>_<prompt>_<timestamp>/
├── descriptions/
│   └── descriptions.txt        ← Your image descriptions here
├── logs/
│   └── workflow.log
└── [other files depending on steps]
```

## Batch File Details

### run_ollama.bat

**Provider:** Ollama (Local AI)  
**Model:** moondream (2GB, fast, accurate)  
**Cost:** Free  
**Internet:** Not needed (after model download)

**Setup:**
1. Install Ollama from https://ollama.ai
2. Pull model: `ollama pull moondream`
3. Edit `IMAGE_PATH` in batch file
4. Run

**Best For:**
- Privacy-sensitive work
- Unlimited processing
- Offline use
- No API costs

**Guide:** `docs/OLLAMA_GUIDE.md`

---

### run_onnx.bat

**Provider:** ONNX Runtime (Local AI)  
**Model:** florence-2-large (700MB, Microsoft Florence-2)  
**Cost:** Free  
**Internet:** Only for first-time model download

**Setup:**
1. Install ONNX Runtime: `pip install onnxruntime`
2. Edit `IMAGE_PATH` in batch file
3. Run (model auto-downloads on first use)

**Best For:**
- Optimized performance
- High-quality Florence-2 model
- Cross-platform compatibility
- No API management

**Guide:** `docs/ONNX_GUIDE.md`

---

### run_openai_gpt4o.bat

**Provider:** OpenAI (Cloud AI)  
**Model:** gpt-4o (GPT-4 Omni)  
**Cost:** ~$0.01-0.02 per image  
**Internet:** Required

**Setup:**
1. Get API key from https://platform.openai.com/api-keys
2. Save key to file: `echo sk-your-key > openai_key.txt`
3. Edit `IMAGE_PATH` and `API_KEY_FILE` in batch file
4. Run

**Best For:**
- Production quality
- Fast processing
- Reliable service
- Latest AI models

**Guide:** `docs/OPENAI_SETUP_GUIDE.md`

---

### run_huggingface.bat

**Provider:** HuggingFace Inference API (Cloud AI)  
**Model:** microsoft/Florence-2-large  
**Cost:** Free tier (~1,000 requests/month), Pro $9/month  
**Internet:** Required

**Setup:**
1. Sign up at https://huggingface.co/join
2. Get token from https://huggingface.co/settings/tokens
3. Save token: `echo hf-your-token > huggingface_token.txt`
4. Edit `IMAGE_PATH` and `TOKEN_FILE` in batch file
5. Run

**Best For:**
- Testing/prototyping
- Low-volume use
- Model variety
- Budget-conscious cloud processing

**Guide:** `docs/HUGGINGFACE_GUIDE.md`

---

### run_copilot.bat

**Provider:** GitHub Copilot (Cloud AI)  
**Model:** gpt-4o (via GitHub Copilot)  
**Cost:** $10-19/month subscription  
**Internet:** Required

**Setup:**
1. Subscribe to GitHub Copilot: https://github.com/features/copilot
2. Install GitHub CLI: https://cli.github.com
3. Authenticate: `gh auth login`
4. Edit `IMAGE_PATH` in batch file
5. Run

**Best For:**
- Developers with Copilot subscription
- Access to multiple models (GPT, Claude, o1)
- No per-use fees
- Integrated workflow

**Guide:** `docs/COPILOT_GUIDE.md`

## Configuration Options

All batch files support these configuration options:

### Image Path

```batch
REM Single image
set IMAGE_PATH=C:\Photos\image.jpg

REM Folder of images
set IMAGE_PATH=C:\Photos\Vacation2025

REM Relative path (from project root)
set IMAGE_PATH=tests\test_files\images
```

### Workflow Steps

```batch
REM Just describe images
set STEPS=describe

REM Full workflow: extract metadata, describe, generate HTML, open viewer
set STEPS=extract,describe,html,viewer

REM Custom combination
set STEPS=extract,describe,html
```

### Prompt Styles

```batch
set PROMPT_STYLE=narrative     # Balanced, recommended
set PROMPT_STYLE=detailed      # Comprehensive information
set PROMPT_STYLE=concise       # Short summaries
set PROMPT_STYLE=artistic      # Art/composition focus
set PROMPT_STYLE=technical     # Photography analysis
set PROMPT_STYLE=colorful      # Color palette focus
```

### Model Selection

Some providers support multiple models. Edit the batch file:

```batch
REM Ollama options
set MODEL=moondream              # Recommended: fast, 2GB
set MODEL=llama3.2-vision        # Higher quality, 7GB
set MODEL=llava                  # Alternative, 4GB

REM ONNX options
set MODEL=florence-2-large       # Best quality, 700MB
set MODEL=florence-2-base        # Faster, 350MB

REM OpenAI options
set MODEL=gpt-4o                 # Best overall
set MODEL=gpt-4o-mini            # Cost-effective
set MODEL=gpt-4-turbo            # Previous generation

REM HuggingFace options
set MODEL=microsoft/Florence-2-large
set MODEL=microsoft/Florence-2-base
set MODEL=Salesforce/blip2-opt-2.7b

REM Copilot options
set MODEL=gpt-4o                 # OpenAI GPT-4 Omni
set MODEL=claude-3.5-sonnet      # Anthropic Claude
set MODEL=o1-preview             # OpenAI o1 (reasoning)
set MODEL=o1-mini                # OpenAI o1 mini
```

## Customization

### Creating Custom Batch Files

Copy an existing batch file and modify:

```batch
REM Copy
copy run_ollama.bat run_my_custom.bat

REM Edit to customize:
REM - Different model
REM - Different prompt style
REM - Different workflow steps
REM - Different provider
```

### Example: High-Quality Photography

```batch
@echo off
REM High-quality photography workflow

set IMAGE_PATH=C:\Photos\ClientShoot
set STEPS=extract,describe,html,viewer
set PROVIDER=openai
set MODEL=gpt-4o
set PROMPT_STYLE=detailed
set API_KEY_FILE=C:\keys\openai_key.txt

REM ... rest of batch file ...
```

### Example: Quick Batch Processing

```batch
@echo off
REM Fast batch processing with local AI

set IMAGE_PATH=C:\Photos\ToProcess
set STEPS=describe
set PROVIDER=onnx
set MODEL=florence-2-base
set PROMPT_STYLE=concise

REM ... rest of batch file ...
```

### Example: Artistic Analysis

```batch
@echo off
REM Artistic analysis of artwork

set IMAGE_PATH=C:\Art\Gallery
set STEPS=describe,html
set PROVIDER=copilot
set MODEL=claude-3.5-sonnet
set PROMPT_STYLE=artistic

REM ... rest of batch file ...
```

## Troubleshooting

### Common Issues

**"Python is not installed or not in PATH"**
```bash
# Install Python 3.8+ from python.org
# Ensure "Add to PATH" is checked during installation
```

**"workflow.py not found"**
```bash
# Batch file must be in project root, or run from project root
cd C:\path\to\idt
run_ollama.bat
```

**"Image path does not exist"**
```batch
# Use absolute paths, check spelling
set IMAGE_PATH=C:\Users\YourName\Pictures\photo.jpg
# NOT: C:\Users\YourName\Pictures\photo.jpg  (check the path exists)
```

### Provider-Specific

See individual provider guides for detailed troubleshooting:
- `docs/OLLAMA_GUIDE.md`
- `docs/ONNX_GUIDE.md`
- `docs/OPENAI_SETUP_GUIDE.md`
- `docs/HUGGINGFACE_GUIDE.md`
- `docs/COPILOT_GUIDE.md`

## Testing

To verify a batch file works:

1. Use a test image from `tests/test_files/images/`
2. Edit batch file with test image path
3. Run batch file
4. Check for new `wf_*` directory
5. Open `wf_*/descriptions/descriptions.txt`
6. Verify description is relevant and accurate

See `docs/BATCH_FILES_TESTING.md` for detailed testing procedures.

## Command-Line Alternative

You can also run workflow.py directly:

```bash
python scripts/workflow.py "C:\path\to\image.jpg" \
  --provider ollama \
  --model moondream \
  --prompt-style narrative \
  --steps describe
```

Batch files are convenient wrappers around these commands.

## Best Practices

### For Privacy-Sensitive Work
- Use **Ollama** or **ONNX** (local processing)
- Images never leave your computer

### For Cost-Effective Processing
- Free & unlimited: **Ollama** or **ONNX**
- Free tier cloud: **HuggingFace**
- Subscription: **Copilot** (if you already have it)

### For Best Quality
- **OpenAI** gpt-4o (paid, fast)
- **Copilot** gpt-4o or claude-3.5-sonnet (subscription)
- **ONNX** florence-2-large (free, local)

### For Large Batches
- **Ollama** or **ONNX** (no API limits)
- Use `florence-2-base` for speed on ONNX
- Use `moondream` for speed on Ollama

### For Production
- **OpenAI** (reliable, scalable)
- **ONNX** (if local infrastructure available)
- Set up error handling and monitoring

## Integration

### Automation

Schedule batch files with Windows Task Scheduler:

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger (daily, weekly, etc.)
4. Set action: Start Program → Select batch file
5. Test task

### Scripts

Call batch files from other scripts:

```batch
REM Process multiple folders
call run_ollama.bat
call run_ollama_folder2.bat
call run_ollama_folder3.bat
```

```python
# Python integration
import subprocess
subprocess.run(["run_ollama.bat"], shell=True)
```

## Getting Help

- **Testing Guide**: `docs/BATCH_FILES_TESTING.md`
- **Provider Guides**: `docs/` directory
- **Workflow Documentation**: `docs/WORKFLOW_README.md`
- **Configuration**: `scripts/image_describer_config.json`
- **Prompt Editor**: `prompt_editor/prompt_editor.py`

## Summary

1. **Choose provider** based on your needs (free/paid, local/cloud)
2. **Edit batch file** with your image path and API keys
3. **Run batch file** - double-click or command prompt
4. **Find results** in `wf_*` directory
5. **Customize** as needed for your workflow

Each batch file is pre-configured with recommended settings for that provider. Just add your image path and API credentials (if needed), then run!

Happy describing! 🖼️
