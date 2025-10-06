# OpenAI Provider Setup Guide

## Overview
The Image Description Toolkit supports OpenAI's GPT vision models for generating image descriptions. This guide explains how to set up and use OpenAI as your AI provider.

## Supported OpenAI Models

### Recommended Models (as of October 2025)

1. **gpt-4o** - Latest and most capable vision model
   - Best quality descriptions
   - Fastest processing
   - Cost-effective

2. **gpt-4o-mini** - Smaller, faster version
   - Good quality descriptions
   - Lower cost
   - Faster response times
   - **Recommended for most users**

3. **gpt-4-turbo** - Previous generation turbo model
   - High quality
   - Good balance of speed and quality

4. **gpt-4-vision-preview** - Original vision model
   - Still available but older
   - May be deprecated soon

5. **gpt-4** - Base GPT-4 with vision
   - High quality but slower
   - More expensive

## Setting Up Your API Key

You have **three options** for providing your OpenAI API key:

### Option 1: API Key File (Recommended)

Create a text file containing your API key and reference it with `--api-key-file`:

```bash
# Create the key file (do this once)
echo "sk-your-api-key-here" > ~/openai_key.txt

# Use it with the script
python image_describer.py photos/ --provider openai --model gpt-4o-mini --api-key-file ~/openai_key.txt
```

**Advantages:**
- Secure (not in command history)
- Easy to manage multiple keys
- Can use different keys for different projects

### Option 2: Environment Variable

Set the `OPENAI_API_KEY` environment variable:

**Windows (PowerShell):**
```powershell
$env:OPENAI_API_KEY = "sk-your-api-key-here"
python image_describer.py photos/ --provider openai --model gpt-4o-mini
```

**Windows (Command Prompt):**
```cmd
set OPENAI_API_KEY=sk-your-api-key-here
python image_describer.py photos/ --provider openai --model gpt-4o-mini
```

**Linux/Mac:**
```bash
export OPENAI_API_KEY="sk-your-api-key-here"
python image_describer.py photos/ --provider openai --model gpt-4o-mini
```

**Make it Permanent (Linux/Mac):**
Add to your `~/.bashrc` or `~/.zshrc`:
```bash
export OPENAI_API_KEY="sk-your-api-key-here"
```

### Option 3: Local File in Current Directory

Create a file named `openai.txt` in the directory where you run the script:

```bash
# Create the file
echo "sk-your-api-key-here" > openai.txt

# Run without specifying key (it will auto-detect)
python image_describer.py photos/ --provider openai --model gpt-4o-mini
```

**Note:** This file should be gitignored to avoid accidentally committing your API key.

## Getting Your OpenAI API Key

1. Go to [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Sign in or create an account
3. Click "Create new secret key"
4. Copy the key (starts with `sk-`)
5. Store it securely using one of the methods above

**Important:** Never share your API key or commit it to version control!

## Usage Examples

### Basic Usage

```bash
# Using API key file
python image_describer.py photos/ --provider openai --model gpt-4o-mini --api-key-file ~/openai_key.txt

# Using environment variable (after setting it)
python image_describer.py photos/ --provider openai --model gpt-4o-mini

# Using local openai.txt file
python image_describer.py photos/ --provider openai --model gpt-4o-mini
```

### With Custom Prompt Style

```bash
python image_describer.py photos/ \
  --provider openai \
  --model gpt-4o-mini \
  --prompt-style artistic \
  --api-key-file ~/openai_key.txt
```

### Full Workflow with OpenAI

```bash
python workflow.py \
  --input photos/ \
  --steps video,convert,describe,html \
  --provider openai \
  --model gpt-4o-mini \
  --prompt-style narrative \
  --api-key-file ~/openai_key.txt
```

### Processing Specific Image Types

```bash
# Process only HEIC files
python image_describer.py photos/ \
  --provider openai \
  --model gpt-4o \
  --api-key-file ~/openai_key.txt \
  --recursive
```

## Cost Considerations

OpenAI charges per token (both input and output). Vision models have additional costs for image processing.

### Approximate Costs (as of October 2025)

**gpt-4o-mini** (recommended):
- Input: $0.15 per 1M tokens
- Output: $0.60 per 1M tokens
- Images: ~$0.001-0.002 per image
- **Estimated: $0.10-0.20 per 100 images**

**gpt-4o**:
- Input: $2.50 per 1M tokens
- Output: $10.00 per 1M tokens
- Images: ~$0.01-0.02 per image
- **Estimated: $1-2 per 100 images**

**gpt-4-turbo**:
- Input: $10.00 per 1M tokens
- Output: $30.00 per 1M tokens
- **Estimated: $3-5 per 100 images**

**Tips to Reduce Costs:**
- Use `gpt-4o-mini` for most tasks
- Use concise prompt styles
- Process fewer images during testing
- Set up billing alerts in OpenAI dashboard

## Checking Available Models

List all available OpenAI models you have access to:

```bash
python image_describer.py --list-providers
```

This will show:
- Which providers are available
- Which models you can use
- Whether your API key is working

## Troubleshooting

### "Provider 'openai' requires an API key"

**Solution:** Set your API key using one of the three methods above.

### "Error: HTTP 401" or "Unauthorized"

**Causes:**
- Invalid API key
- Expired API key
- API key not set correctly

**Solution:** 
- Verify your API key at [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
- Make sure there are no extra spaces or characters in your key file
- Check that the environment variable is set correctly

### "Error: HTTP 429" or "Rate limit exceeded"

**Causes:**
- Exceeded free tier limits
- Too many requests too quickly

**Solution:**
- Add billing information to your OpenAI account
- Add `--batch-delay` to slow down requests:
  ```bash
  python image_describer.py photos/ --provider openai --model gpt-4o-mini --batch-delay 2.0
  ```
- Process fewer images at once

### "Error: HTTP 404" or "Model not found"

**Causes:**
- Model name typo
- Model not available to your account
- Model deprecated

**Solution:**
- Check available models with `--list-providers`
- Use one of the current models: `gpt-4o-mini`, `gpt-4o`, `gpt-4-turbo`
- Verify your account has access to vision models

### Slow Processing

OpenAI API calls take 2-10 seconds per image depending on:
- Model selected (mini is faster)
- Prompt complexity
- OpenAI server load

**Tips:**
- Use `gpt-4o-mini` for faster processing
- Use `--verbose` to see progress
- Be patient - cloud processing takes time

## Comparison with Other Providers

| Feature | OpenAI | Ollama | ONNX |
|---------|--------|--------|------|
| **Speed** | Moderate (2-10s/image) | Fast (1-3s/image) | Very Fast (<1s/image) |
| **Quality** | Excellent | Very Good | Good |
| **Cost** | Pay per use | Free (local) | Free (local) |
| **Setup** | API key required | Model download | Model download |
| **Internet** | Required | Not required | Not required |
| **Privacy** | Images sent to cloud | Fully local | Fully local |
| **Hardware** | None | GPU recommended | CPU/GPU |

**When to use OpenAI:**
- Need highest quality descriptions
- Don't have powerful local hardware
- Don't mind cloud processing
- Have API credits/budget

**When to use Ollama/ONNX:**
- Want privacy (local processing)
- Have good hardware
- Processing many images (no per-image cost)
- No internet or want offline capability

## Security Best Practices

1. **Never commit API keys to git**
   - Use `.gitignore` for `openai.txt` and key files
   - Don't put keys in scripts

2. **Use environment variables in production**
   - Better than files for server deployments
   - Easier to manage in CI/CD

3. **Rotate keys regularly**
   - Create new keys every few months
   - Delete old keys from OpenAI dashboard

4. **Set spending limits**
   - Configure in OpenAI dashboard
   - Get alerts before hitting limits

5. **Use separate keys for testing and production**
   - Easier to track costs
   - Limit exposure if compromised

## Example Workflow

Complete workflow using OpenAI for a photo collection:

```bash
# 1. Set up API key (one time)
echo "sk-your-key-here" > ~/openai_key.txt

# 2. Test with a few images
python image_describer.py test_photos/ \
  --provider openai \
  --model gpt-4o-mini \
  --api-key-file ~/openai_key.txt \
  --max-files 5

# 3. Check the output
cat test_photos/image_descriptions.txt

# 4. Run full workflow
python workflow.py \
  --input photos/2025/ \
  --steps video,convert,describe,html \
  --provider openai \
  --model gpt-4o-mini \
  --prompt-style narrative \
  --api-key-file ~/openai_key.txt

# 5. View results
open wf_openai_gpt-4o-mini_narrative_*/html_reports/image_descriptions.html
```

## Additional Resources

- **OpenAI API Documentation:** https://platform.openai.com/docs/guides/vision
- **OpenAI Pricing:** https://openai.com/pricing
- **OpenAI Platform:** https://platform.openai.com/
- **Rate Limits:** https://platform.openai.com/docs/guides/rate-limits
- **Best Practices:** https://platform.openai.com/docs/guides/production-best-practices
