# HuggingFace Setup Guide for Image Description

## Overview

HuggingFace is a **cloud AI platform** with a free tier that provides access to thousands of AI models via the Inference API. This guide shows you how to set up and use HuggingFace for image description in the Image Description Toolkit.

## Why Use HuggingFace?

✅ **Advantages:**
- **Free tier available** - Limited free usage per month
- **High quality** - Access to state-of-the-art models like Florence-2
- **No local resources** - Processing happens in the cloud
- **Many models** - Access to thousands of vision models
- **Easy setup** - Just need an API token
- **Flexible** - Can switch between different models easily

❌ **Considerations:**
- Requires internet connection
- Images are sent to HuggingFace servers (privacy consideration)
- Free tier has rate limits (~1,000 requests/month)
- May have cold start delays when model loads
- Paid tier for higher limits

## Requirements

- **Internet connection** - Required for all operations
- **HuggingFace account** - Free at https://huggingface.co
- **API token** - Free from your account settings
- **Python 3.8+** - With required packages

## Installation

### Step 1: Create HuggingFace Account

1. **Sign up** at https://huggingface.co/join
2. **Verify email** (check spam folder)
3. **Free account** is sufficient for basic usage

### Step 2: Get API Token

1. **Log in** to HuggingFace
2. **Go to Settings** → **Access Tokens**
   - Direct link: https://huggingface.co/settings/tokens
3. **Create new token**
   - Name: "Image Description"
   - Type: "Read" (sufficient for inference)
4. **Copy token** (starts with `hf_...`)
5. **Save token securely**

### Step 3: Store API Token

**Option 1: Token File (Recommended for batch file)**

Create a text file with your token:

```batch
REM Create token file
echo hf_YourTokenHere > huggingface_token.txt
```

**Option 2: Environment Variable**

```batch
REM Set environment variable (temporary)
set HUGGINGFACE_TOKEN=hf_YourTokenHere

REM Or add permanently via System Properties → Environment Variables
```

**Option 3: In Config File**

Edit `scripts/image_describer_config.json`:
```json
{
  "api_key": "hf_YourTokenHere",
  ...
}
```

## Using the Batch File

### Quick Start

1. **Get your token** from https://huggingface.co/settings/tokens

2. **Save token to file**
   ```
   C:\Users\YourName\GitHub\idt\huggingface_token.txt
   ```
   Just paste the token in the file (one line, no extra text)

3. **Edit the batch file**
   - Open `run_huggingface.bat` in text editor
   - Set `IMAGE_PATH` to your image or folder
   - Set `TOKEN_FILE` to your token file path
   - Example:
     ```batch
     set IMAGE_PATH=C:\Users\YourName\Pictures\photo.jpg
     set TOKEN_FILE=C:\Users\YourName\huggingface_token.txt
     ```

4. **Run the batch file**
   - Double-click `run_huggingface.bat`
   - OR run from command prompt: `run_huggingface.bat`

5. **Find your results**
   - Look for `wf_huggingface_*_narrative_*` folder
   - Open `descriptions.txt` to see image descriptions

### Configuration Options

Edit these settings in the batch file:

```batch
REM Path to image or folder
set IMAGE_PATH=C:\path\to\your\images

REM Path to token file (or empty for environment variable)
set TOKEN_FILE=C:\path\to\huggingface_token.txt
REM Or: set TOKEN_FILE=

REM Steps to run
set STEPS=describe
REM Or: set STEPS=extract,describe,html,viewer

REM Model to use
set MODEL=microsoft/Florence-2-large
REM Or: set MODEL=microsoft/Florence-2-base
REM Or: set MODEL=Salesforce/blip2-opt-2.7b

REM Prompt style
set PROMPT_STYLE=narrative
REM Options: narrative, detailed, concise, artistic, technical, colorful
```

## Command-Line Usage

### Using Token File

```bash
python workflow.py "C:\path\to\image.jpg" --provider huggingface --model microsoft/Florence-2-large --prompt-style narrative --api-key-file huggingface_token.txt
```

### Using Environment Variable

```bash
set HUGGINGFACE_TOKEN=hf_YourTokenHere
python workflow.py "C:\path\to\image.jpg" --provider huggingface --model microsoft/Florence-2-large --prompt-style narrative
```

### Full Workflow

```bash
python workflow.py "C:\path\to\images" --steps extract,describe,html,viewer --provider huggingface --model microsoft/Florence-2-large --prompt-style narrative --api-key-file huggingface_token.txt
```

## Available Models

### Recommended Models

| Model | Size | Quality | Speed | Best For |
|-------|------|---------|-------|----------|
| **microsoft/Florence-2-large** | Large | Excellent | Medium | Best overall quality |
| **microsoft/Florence-2-base** | Medium | Good | Fast | Faster processing |
| **Salesforce/blip2-opt-2.7b** | Medium | Good | Fast | General captions |
| **Salesforce/blip-image-captioning-large** | Medium | Good | Fast | Simple captions |

### Model Performance

**Florence-2-large** (Recommended):
- Best quality image understanding
- Detailed, accurate descriptions
- May have cold start delay (~30 seconds first time)
- Best value for quality

**Florence-2-base**:
- Faster than large
- Still very good quality
- Less cold start delay
- Good for large batches

## Prompt Styles

| Style | Best For | Description Length |
|-------|----------|-------------------|
| **narrative** | General use | Medium - balanced |
| **detailed** | Maximum info | Long - comprehensive |
| **concise** | Quick summaries | Short - essentials only |
| **artistic** | Art analysis | Medium - composition focus |
| **technical** | Photography | Medium - technical details |
| **colorful** | Color analysis | Medium - palette focus |

## Rate Limits & Pricing

### Free Tier

- **~1,000 requests per month** (rate-limited)
- **Cold starts** - Model loads when first accessed
- **Best for**: Testing, small projects, personal use

### Pro Tier ($9/month)

- **Higher rate limits** - More requests per month
- **Faster loading** - Priority model loading
- **Best for**: Regular use, small businesses

### Enterprise

- **Unlimited usage** - Based on your plan
- **Dedicated resources** - No cold starts
- **Best for**: Production workloads

## Troubleshooting

### "Invalid or expired token"

**Cause**: Token is wrong, expired, or has insufficient permissions

**Solutions**:
1. Generate new token at https://huggingface.co/settings/tokens
2. Ensure token type is "Read" or "Write"
3. Check token is copied correctly (starts with `hf_`)
4. Make sure no extra spaces in token file

### "Rate limit exceeded"

**Cause**: Free tier monthly limit reached

**Solutions**:
1. Wait until next month (limits reset monthly)
2. Upgrade to Pro tier ($9/month)
3. Use local provider (Ollama or ONNX) instead
4. Space out your requests over time

### "Model is loading" or Long Delays

**Cause**: Model cold start - HuggingFace loads model on first request

**Solutions**:
1. Wait ~30-60 seconds for model to load
2. Subsequent requests will be faster (model cached ~15 minutes)
3. Use smaller model (Florence-2-base) for faster loading
4. Pro tier has faster/priority loading

### "Connection timeout" or "Network error"

**Cause**: Network connectivity issues

**Solutions**:
1. Check internet connection
2. Check firewall isn't blocking HuggingFace
3. Try again later (may be temporary HF issue)
4. Use VPN if HuggingFace is blocked in your region

### "Model not found" Error

**Cause**: Model name incorrect or model removed

**Solutions**:
1. Check model name spelling: `microsoft/Florence-2-large`
2. Visit https://huggingface.co/models to browse available models
3. Use recommended models from this guide

### Token File Not Found

**Cause**: Path to token file is incorrect

**Solutions**:
1. Use absolute path: `C:\Users\YourName\huggingface_token.txt`
2. Check file exists: `type huggingface_token.txt`
3. Or use environment variable instead

## Security Best Practices

### Protecting Your API Token

**DO:**
- ✅ Store token in separate file
- ✅ Add token file to `.gitignore`
- ✅ Use environment variables for production
- ✅ Regenerate token if exposed
- ✅ Use Read-only tokens when possible

**DON'T:**
- ❌ Commit token to Git
- ❌ Share token publicly
- ❌ Use same token for multiple projects (security risk)
- ❌ Store in config files that get committed

### .gitignore Entry

Add to your `.gitignore`:
```
huggingface_token.txt
*.token
*_token.txt
```

## Cost Comparison

| Provider | Cost per 1,000 Images | Privacy | Internet Required |
|----------|----------------------|---------|-------------------|
| **HuggingFace Free** | **$0** (rate limited) | Cloud | Yes |
| **HuggingFace Pro** | **~$9/month** (unlimited) | Cloud | Yes |
| OpenAI gpt-4o-mini | ~$1-2 | Cloud | Yes |
| OpenAI gpt-4o | ~$10-20 | Cloud | Yes |
| Ollama | $0 (unlimited) | Private | No |
| ONNX | $0 (unlimited) | Private | No |

## Comparison with Other Providers

### HuggingFace vs OpenAI

| Feature | HuggingFace | OpenAI |
|---------|-------------|--------|
| **Free tier** | Yes (~1K/month) | No ($5 minimum) |
| **Quality** | Excellent | Excellent |
| **Speed** | Medium | Fast |
| **Models** | Many options | GPT models only |
| **Cold starts** | Yes | No |

**Choose HuggingFace if**:
- Want free tier option
- Need access to many models
- Building prototype/testing
- Low to medium volume

**Choose OpenAI if**:
- Need maximum speed
- Have budget for API costs
- Want most reliable service
- High volume processing

### HuggingFace vs Ollama/ONNX

| Feature | HuggingFace | Ollama/ONNX |
|---------|-------------|-------------|
| **Cost** | Free tier + paid | Completely free |
| **Privacy** | Cloud (data sent to HF) | Fully private (local) |
| **Setup** | Just API token | Requires local install |
| **Resources** | None (cloud) | Requires RAM/GPU |
| **Internet** | Required | Optional (after setup) |

**Choose HuggingFace if**:
- Don't have powerful computer
- Want zero setup
- Internet always available
- Fine with cloud processing

**Choose Ollama/ONNX if**:
- Need complete privacy
- Have capable hardware
- Want offline capability
- No budget for API costs

## Advanced Usage

### Batch Processing with Rate Limits

For large batches on free tier:

```batch
REM Process in smaller chunks
set IMAGE_PATH=C:\Photos\Batch1
run_huggingface.bat

REM Wait a bit, then next batch
timeout /t 300
set IMAGE_PATH=C:\Photos\Batch2
run_huggingface.bat
```

### Using Different Models

Try different models for comparison:

```batch
REM High quality
set MODEL=microsoft/Florence-2-large

REM Faster processing
set MODEL=microsoft/Florence-2-base

REM Alternative model
set MODEL=Salesforce/blip2-opt-2.7b
```

### Programmatic Usage

For integration in scripts:

```python
from imagedescriber.ai_providers import HuggingFaceProvider

# Initialize with token
provider = HuggingFaceProvider(api_key="hf_YourToken")

# Or use environment variable
import os
provider = HuggingFaceProvider(api_key=os.getenv("HUGGINGFACE_TOKEN"))

# Describe image
description = provider.describe_image(image_path, model="microsoft/Florence-2-large")
```

## Example Workflows

### Free Tier Budget Management

```batch
REM Use for important images only (stay under rate limit)
set IMAGE_PATH=C:\ImportantPhotos\client_project.jpg
set MODEL=microsoft/Florence-2-large
set PROMPT_STYLE=detailed
```

### Testing Before Production

```batch
REM Test with free tier, then switch to local for production
set IMAGE_PATH=C:\TestImages
set STEPS=describe
set MODEL=microsoft/Florence-2-base
```

### High-Quality Cloud Processing

```batch
REM Pro tier: unlimited high-quality processing
set IMAGE_PATH=C:\Photos\Photoshoot
set STEPS=extract,describe,html,viewer
set MODEL=microsoft/Florence-2-large
set PROMPT_STYLE=detailed
```

## Getting Help

- **HuggingFace Docs**: https://huggingface.co/docs/api-inference/
- **Inference API**: https://huggingface.co/docs/api-inference/detailed_parameters
- **Model Hub**: https://huggingface.co/models?pipeline_tag=image-to-text
- **IDT Documentation**: See `docs/` folder
- **Support**: https://huggingface.co/support

## Summary

HuggingFace provides **cloud AI with free tier** for image description:

1. ✅ Sign up at https://huggingface.co/join (free)
2. ✅ Get API token from https://huggingface.co/settings/tokens
3. ✅ Save token to `huggingface_token.txt`
4. ✅ Edit `run_huggingface.bat` with your image path
5. ✅ Run batch file
6. ✅ Find results in `wf_huggingface_*` folder

Perfect for users who want:
- 🆓 Free tier option for testing
- ☁️ Cloud processing (no local resources)
- 🎯 Access to cutting-edge models
- 🚀 Easy setup (just API token)
- 📈 Scalable (upgrade to Pro for higher limits)

Happy describing! 🖼️
