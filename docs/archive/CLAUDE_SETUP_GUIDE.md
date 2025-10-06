# Claude (Anthropic) Setup Guide

Complete guide for using Claude AI models with the Image Description Workflow tool.

## Table of Contents
- [Overview](#overview)
- [Getting Started](#getting-started)
- [API Key Setup](#api-key-setup)
- [Available Models](#available-models)
- [Usage Examples](#usage-examples)
- [Pricing](#pricing)
- [Troubleshooting](#troubleshooting)

## Overview

**Claude** is Anthropic's family of large language models with advanced vision capabilities. This integration supports:
- ✅ All current Claude 3.5 and 3.0 models
- ✅ Vision/image description capabilities
- ✅ Interactive chat mode
- ✅ CLI and GUI interfaces
- ✅ Batch processing via workflow

**Provider Type:** Cloud (paid API)  
**Company:** Anthropic  
**Models:** 7 vision-capable models (Claude 4.x, 3.7, 3.5, 3.0 series)  
**Best For:** High-quality image descriptions, detailed analysis, conversational chat

## Getting Started

### Prerequisites
1. **Anthropic API Account**
   - Visit: https://console.anthropic.com/
   - Sign up for an account
   - Add billing information (pay-as-you-go)

2. **API Key**
   - Create API key in console
   - Save securely (cannot be viewed again)

3. **Python Environment**
   - Python 3.8 or higher
   - Dependencies installed (`pip install -r requirements.txt`)

### Quick Start
```bash
# 1. Save your API key to a file
echo "sk-ant-api03-YOUR-KEY-HERE" > ~/onedrive/claude.txt

# 2. Test with a single image (Claude 4.5 - best quality)
python workflow.py path/to/image.jpg --provider claude --model claude-sonnet-4-5-20250929

# 3. Process a folder (Claude 3.5 Haiku - fast & affordable)
python workflow.py path/to/images --provider claude --model claude-3-5-haiku-20241022 --steps describe,html
```

## API Key Setup

### Method 1: API Key File (Recommended)

Save your API key to a text file with **just the key, one line, no quotes**:

**Supported locations** (checked in order):
1. `claude.txt` (current directory)
2. `~/claude.txt` (home directory)
3. `~/onedrive/claude.txt` (OneDrive)
4. `~/OneDrive/claude.txt` (OneDrive, capitalized)

**Example:**
```bash
# Linux/Mac
echo "sk-ant-api03-YOUR-KEY-HERE" > ~/onedrive/claude.txt

# Windows (PowerShell)
"sk-ant-api03-YOUR-KEY-HERE" | Out-File -FilePath "$env:USERPROFILE\onedrive\claude.txt" -Encoding ASCII
```

### Method 2: Environment Variable

Set the `ANTHROPIC_API_KEY` environment variable:

**Linux/Mac:**
```bash
export ANTHROPIC_API_KEY="sk-ant-api03-YOUR-KEY-HERE"
```

**Windows (Command Prompt):**
```cmd
set ANTHROPIC_API_KEY=sk-ant-api03-YOUR-KEY-HERE
```

**Windows (PowerShell):**
```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-api03-YOUR-KEY-HERE"
```

### Method 3: Specify API Key File Path

Use `--api-key-file` argument:
```bash
python workflow.py images --provider claude --api-key-file /path/to/my-claude-key.txt
```

## Available Models

All Claude 3.x and 4.x models support vision and can describe images. The following 7 models are available:

### Claude 4 Series (Latest - 2025, Recommended)

| Model | ID | Best For | Speed | Cost |
|-------|-----|----------|-------|------|
| **Claude Sonnet 4.5** | `claude-sonnet-4-5-20250929` | Agents, coding, highest intelligence | Fast | $$ |
| **Claude Opus 4.1** | `claude-opus-4-1-20250805` | Specialized complex tasks | Moderate | $$$ |
| **Claude Sonnet 4** | `claude-sonnet-4-20250514` | High performance, balanced | Fast | $$ |
| **Claude Opus 4** | `claude-opus-4-20250514` | Very high intelligence | Moderate | $$$ |

### Claude 3.7

| Model | ID | Best For | Speed | Cost |
|-------|-----|----------|-------|------|
| **Claude Sonnet 3.7** | `claude-3-7-sonnet-20250219` | Extended thinking capability | Fast | $$ |

### Claude 3.5 & 3.0

| Model | ID | Best For | Speed | Cost |
|-------|-----|----------|-------|------|
| **Claude Haiku 3.5** | `claude-3-5-haiku-20241022` | Fastest, most affordable | Very Fast | $ |
| **Claude Haiku 3** | `claude-3-haiku-20240307` | Fast and compact | Very Fast | $ |

### Note on Legacy Models

Claude 3.5 Sonnet and Claude 3 Opus/Sonnet models from 2024 are now deprecated in favor of Claude 4 series. Claude 2.x models are excluded (no vision support).

### Model Selection Guide

**For Production:**
- **claude-sonnet-4-5-20250929** - Best overall (highest intelligence, agents/coding)
- **claude-3-5-haiku-20241022** - Best value (fast + affordable)

**For Testing:**
- **claude-3-5-haiku-20241022** - Lowest cost per image
- **claude-3-haiku-20240307** - Even cheaper

**For Maximum Quality:**
- **claude-opus-4-1-20250805** - Exceptional reasoning, specialized tasks
- **claude-sonnet-4-5-20250929** - Best for most use cases

**For Extended Thinking:**
- **claude-3-7-sonnet-20250219** - Supports extended thinking mode

## Usage Examples

### Command Line (workflow.py)

**Basic usage:**
```bash
python workflow.py photos --provider claude --model claude-sonnet-4-5-20250929
```

**With API key file:**
```bash
python workflow.py images --provider claude --model claude-3-5-haiku-20241022 --api-key-file ~/onedrive/claude.txt
```

**Custom prompt style:**
```bash
python workflow.py media --provider claude --model claude-sonnet-4-5-20250929 --prompt-style detailed
```

**Specific workflow steps:**
```bash
python workflow.py videos --provider claude --model claude-3-5-haiku-20241022 --steps video,describe,html
```

**With output directory:**
```bash
python workflow.py photos --provider claude --model claude-opus-4-1-20250805 --output-dir results/claude_descriptions
```

### Batch File (Windows)

**Using pre-configured batch file:**

1. Edit `BatForScripts/run_claude.bat`
2. Set `IMAGE_PATH` to your images
3. Set `API_KEY_FILE` to your key location
4. Choose `MODEL` (default: `claude-3-5-sonnet-20241022`)
5. Run the batch file

**Example configuration:**
```batch
set IMAGE_PATH=C:\Users\YourName\Pictures\VacationPhotos
set API_KEY_FILE=C:\Users\YourName\onedrive\claude.txt
set MODEL=claude-sonnet-4-5-20250929
```

### GUI (imagedescriber.py)

**Using the graphical interface:**

1. Launch: `python imagedescriber/imagedescriber.py`
2. Select **Provider:** "claude" from dropdown
3. Select **Model:** (e.g., "claude-sonnet-4-5-20250929")
4. **Image Tab:** Load images and generate descriptions
5. **Chat Tab:** Interactive conversation with Claude

**Chat features:**
- Upload images in chat
- Ask questions about images
- Conversational context maintained
- Supports all Claude models

## Pricing

### Pay-As-You-Go Pricing (Approximate)

**Per 1000 images (estimated):**

| Model | Input Cost | Output Cost | Est. per Image |
|-------|------------|-------------|----------------|
| Claude 3.5 Sonnet | ~$3-15 | ~$15-75 | $0.003-0.015 |
| Claude 3.5 Haiku | ~$0.80-4 | ~$4-20 | $0.0008-0.004 |
| Claude 3 Opus | ~$15-75 | ~$75-375 | $0.015-0.075 |
| Claude 3 Sonnet | ~$3-15 | ~$15-75 | $0.003-0.015 |
| Claude 3 Haiku | ~$0.25-1.25 | ~$1.25-6.25 | $0.0003-0.001 |

**Notes:**
- Costs vary based on image size and description length
- Prices subject to change (check console.anthropic.com/pricing)
- Haiku models offer best value for batch processing
- Opus models best for critical quality needs

### Cost Optimization Tips

1. **Use Haiku for testing:** Start with `claude-3-5-haiku-20241022`
2. **Batch processing:** Process multiple images in one workflow run
3. **Monitor usage:** Check console.anthropic.com for usage dashboard
4. **Choose appropriate model:** Don't use Opus if Sonnet suffices
5. **Limit description length:** Shorter prompts = lower costs

## Troubleshooting

### API Key Not Found

**Error:** `Claude is not available or API key not found`

**Solutions:**
1. Check file exists: `ls ~/onedrive/claude.txt`
2. Verify file contains only the key (no quotes, one line)
3. Try environment variable: `export ANTHROPIC_API_KEY="your-key"`
4. Use `--api-key-file` to specify explicit path

### Invalid API Key

**Error:** `Claude API key error` or `401 Unauthorized`

**Solutions:**
1. Verify key is correct (starts with `sk-ant-api`)
2. Check key hasn't expired
3. Ensure billing is set up at console.anthropic.com
4. Generate new key if needed

### Rate Limiting

**Error:** `429 Too Many Requests`

**Solutions:**
1. Slow down request rate
2. Process smaller batches
3. Check rate limits in console
4. Upgrade account tier if needed

### Network Errors

**Error:** `Network connection problem` or timeout

**Solutions:**
1. Check internet connection
2. Verify no firewall blocking api.anthropic.com
3. Try again (may be temporary)
4. Check Anthropic status page

### Model Not Found

**Error:** `Model name incorrect` or `404 Not Found`

**Solutions:**
1. Use exact model ID from table above
2. Check for typos (e.g., `claude-3-5-sonnet-20241022` not `claude-3.5-sonnet`)
3. Verify model is still available (legacy models may be deprecated)

### Insufficient Credits

**Error:** `Insufficient API credits`

**Solutions:**
1. Add credits at console.anthropic.com
2. Set up billing/payment method
3. Check usage limits

## Advanced Features

### Chat Mode

**Interactive conversation with images:**

```python
# In GUI: Use Chat tab
1. Load an image (optional)
2. Type message
3. Claude responds with context
4. Continue conversation
```

**Features:**
- Maintains conversation history (15 messages)
- Supports image uploads
- Context-aware responses
- All Claude models supported

### Integration with Other Tools

**Combine with GroundingDINO:**
```bash
# Object detection + Claude descriptions
python workflow.py images --provider groundingdino+ollama
# Then use Claude for final descriptions
python workflow.py images --provider claude --model claude-3-5-sonnet-20241022
```

**Resume interrupted workflows:**
```bash
# Start workflow
python workflow.py large_folder --provider claude --model claude-3-5-haiku-20241022

# If interrupted, resume with:
python workflow.py --resume wf_claude_*
```

## Best Practices

### For Image Description

1. **Choose right model:**
   - Testing: `claude-3-5-haiku-20241022`
   - Production: `claude-3-5-sonnet-20241022`
   - Critical quality: `claude-3-opus-20240229`

2. **Optimize prompts:**
   - Use built-in prompt styles (narrative, detailed, etc.)
   - Be specific about what you want described
   - Shorter prompts = lower costs

3. **Batch processing:**
   - Process folders, not individual images
   - Use workflow steps: `video,convert,describe,html`
   - Monitor progress with HTML reports

### For Chat

1. **Context management:**
   - Keep conversations focused
   - Start new chat for different topics
   - Clear chat when switching images

2. **Model selection:**
   - Haiku for quick questions
   - Sonnet for detailed analysis
   - Opus for complex reasoning

## Getting Help

### Documentation
- **Main README:** `README.md`
- **Model Selection:** `docs/MODEL_SELECTION_GUIDE.md`
- **Workflow Guide:** `docs/WORKFLOW_README.md`

### Support
- **Anthropic Docs:** https://docs.anthropic.com/
- **API Reference:** https://docs.anthropic.com/claude/reference/
- **Console:** https://console.anthropic.com/

### Common Questions

**Q: Which Claude model should I use?**  
A: For most use cases, `claude-sonnet-4-5-20250929` (Claude 4.5) offers the best performance. Use Claude 3.5 Haiku for cost-sensitive applications.

**Q: How much will it cost to process 1000 images?**  
A: With Claude 3 Haiku: ~$0.25-1.25, with Claude 3.5 Haiku: ~$0.80-4, with Sonnet 4.5: ~$3-15, with Opus 4.1: ~$15-75 (varies by image size/description length)

**Q: Can I use Claude offline?**  
A: No, Claude requires internet connection and API access.

**Q: Does Claude support video?**  
A: Claude describes individual frames. Use `--steps video` to extract frames first.

**Q: How does Claude compare to OpenAI?**  
A: Generally comparable quality. Claude often produces more detailed, thoughtful descriptions. Pricing similar.

**Q: Can I use my own prompts?**  
A: Yes, use `--prompt-style` or create custom prompts in the GUI.

---

**Last Updated:** October 2024  
**Version:** 1.0  
**Provider:** Claude (Anthropic)
