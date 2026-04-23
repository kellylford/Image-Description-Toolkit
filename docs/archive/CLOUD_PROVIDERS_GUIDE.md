# Cloud AI Providers Guide

**Last Updated:** October 7, 2025

---

## Overview

The Image Description Toolkit supports both **local** (Ollama, ONNX) and **cloud** AI providers (OpenAI, Claude). This guide focuses on using cloud providers with official SDK integration, automatic retry logic, and comprehensive token tracking.

---

## Supported Cloud Providers

### OpenAI (GPT Models)

**Latest Models (October 2025):**
- **gpt-4o** - Latest flagship model, best quality/speed balance
- **gpt-4o-mini** - Smaller, faster, 6x cheaper than gpt-4o
- **gpt-5** - Newest reasoning model (uses `max_completion_tokens`)
- **gpt-4-turbo** - Previous generation (still excellent)

**Pricing (as of October 2025):**
| Model | Input (per 1K tokens) | Output (per 1K tokens) |
|-------|----------------------|------------------------|
| gpt-4o | $0.0025 | $0.010 |
| gpt-4o-mini | $0.00015 | $0.0006 |
| gpt-5 | $0.005 | $0.015 |

**When to Use:**
- General purpose image descriptions
- Good balance of cost and quality
- Fastest response times
- Excellent for batch processing

### Anthropic (Claude Models)

**Latest Models (October 2025):**
- **claude-3-7-sonnet-20250219** - Latest Sonnet (Feb 2025)
- **claude-opus-4-20250514** - Latest Opus, highest quality
- **claude-3-5-haiku-20241022** - Fast and affordable
- **claude-3-5-sonnet-20241022** - Previous Sonnet (stable)

**Pricing (as of October 2025):**
| Model | Input (per 1K tokens) | Output (per 1K tokens) |
|-------|----------------------|------------------------|
| claude-3-7-sonnet | $0.003 | $0.015 |
| claude-opus-4 | $0.015 | $0.075 |
| claude-3-5-haiku | $0.001 | $0.005 |

**When to Use:**
- Detailed, nuanced descriptions
- Complex scene analysis
- High-quality requirements
- Alternative to OpenAI

---

## Setup & Configuration

### 1. Get API Keys

**OpenAI:**
1. Go to [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Sign in or create account
3. Click "Create new secret key"
4. Copy the key (starts with `sk-`)

**Claude (Anthropic):**
1. Go to [https://console.anthropic.com/](https://console.anthropic.com/)
2. Sign in or create account
3. Navigate to API Keys
4. Create new key
5. Copy the key (starts with `sk-ant-`)

### 2. Install SDK Dependencies

The toolkit uses official SDKs for reliability and token tracking:

```bash
# Install requirements (includes OpenAI and Claude SDKs)
pip install -r requirements.txt

# Or install individually
pip install openai>=1.0.0
pip install anthropic>=0.18.0
```

**For Batch Files (.venv environment):**
```bash
# Batch files use .venv Python environment
cd c:\Users\kelly\GitHub\idt
.venv\Scripts\pip.exe install openai>=1.0.0 anthropic>=0.18.0
```

### 3. Configure API Keys

You have **three options** for providing API keys:

#### Option 1: Environment Variables (Recommended for Development)

**Windows (PowerShell):**
```powershell
$env:OPENAI_API_KEY = "sk-your-key-here"
$env:ANTHROPIC_API_KEY = "sk-ant-your-key-here"
```

**Windows (Command Prompt):**
```cmd
set OPENAI_API_KEY=sk-your-key-here
set ANTHROPIC_API_KEY=sk-ant-your-key-here
```

**Linux/Mac:**
```bash
export OPENAI_API_KEY="sk-your-key-here"
export ANTHROPIC_API_KEY="sk-ant-your-key-here"
```

#### Option 2: API Key Files (Recommended for Production)

Create text files in your working directory:

```bash
# Create key files
echo "sk-your-openai-key" > openai.txt
echo "sk-ant-your-claude-key" > claude.txt

# Add to .gitignore (IMPORTANT - don't commit keys!)
echo "openai.txt" >> .gitignore
echo "claude.txt" >> .gitignore
```

**External Storage (Best Practice):**
```bash
# Store keys outside repository
~/your_secure_location/openai.txt
~/your_secure_location/claude.txt

# Reference with --api-key-file flag
python scripts/image_describer.py photos/ --provider openai --api-key-file ~/your_secure_location/openai.txt
```

#### Option 3: Command Line (Not Recommended)

```bash
# Keys appear in command history - use other methods instead
python scripts/image_describer.py photos/ --provider openai --api-key sk-your-key
```

---

## Usage Examples

### Batch Processing with Token Tracking

**OpenAI (GPT-4o-mini - Recommended for most use cases):**
```bash
cd scripts
python image_describer.py "C:\Photos\Vacation2024" --provider openai --model gpt-4o-mini --prompt-style narrative

# Output includes:
# TOKEN USAGE SUMMARY:
#   Total tokens: 42,620
#   Prompt tokens: 42,570
#   Completion tokens: 50
#   Average tokens per image: 426
#   Estimated cost: $0.03
```

**Claude (Haiku - Fast and affordable):**
```bash
python image_describer.py "C:\Photos\Vacation2024" --provider claude --model claude-3-5-haiku-20241022 --prompt-style detailed

# Output includes:
# TOKEN USAGE SUMMARY:
#   Total tokens: 70,300
#   Prompt tokens: 63,760
#   Completion tokens: 6,540
#   Average tokens per image: 703
#   Estimated cost: $0.10
```

### Using Batch Files

**Pre-configured batch files** in `bat/` directory:

**OpenAI Models:**
```cmd
# GPT-4o (best balance)
bat\run_openai_gpt4o.bat "C:\Photos\MyPhotos"

# GPT-4o-mini (most affordable)
bat\run_openai_gpt4o_mini.bat "C:\Photos\MyPhotos"

# GPT-5 (latest reasoning model)
bat\run_openai_gpt5.bat "C:\Photos\MyPhotos"
```

**Claude Models:**
```cmd
# Claude Sonnet 4.5 (latest)
bat\run_claude_sonnet45.bat "C:\Photos\MyPhotos"

# Claude Haiku (affordable)
bat\run_claude_haiku.bat "C:\Photos\MyPhotos"

# Claude Opus 4 (highest quality)
bat\run_claude_opus4.bat "C:\Photos\MyPhotos"
```

**Test All Models:**
```cmd
# Run all 10 cloud models on test directory
bat\allcloudtest.bat
```

### ImageDescriber GUI

**Single Image Processing:**
1. Launch ImageDescriber: `cd imagedescriber && python imagedescriber.py`
2. Open image or workspace
3. Select provider (OpenAI or Claude) from dropdown
4. Select model
5. Click "Process" or press P
6. Token usage stored with description

**Token Data in Workspace:**
```json
{
  "text": "A beautiful sunset over the ocean...",
  "model": "gpt-4o",
  "provider": "openai",
  "total_tokens": 986,
  "prompt_tokens": 789,
  "completion_tokens": 197
}
```

---

## Model Comparison & Selection

### Cost Comparison (100 images @ ~4,000 tokens average)

| Provider | Model | Estimated Cost | Speed | Quality |
|----------|-------|---------------|-------|---------|
| OpenAI | gpt-4o-mini | $0.25 | ⚡⚡⚡ Fast | ⭐⭐⭐ Good |
| OpenAI | gpt-4o | $1.50 | ⚡⚡ Fast | ⭐⭐⭐⭐ Excellent |
| OpenAI | gpt-5 | $3.00 | ⚡ Medium | ⭐⭐⭐⭐⭐ Best |
| Claude | claude-3-5-haiku | $1.00 | ⚡⚡⚡ Fast | ⭐⭐⭐ Good |
| Claude | claude-3-7-sonnet | $3.65 | ⚡⚡ Fast | ⭐⭐⭐⭐ Excellent |
| Claude | claude-opus-4 | $7.50 | ⚡ Slow | ⭐⭐⭐⭐⭐ Best |

### Recommendation Matrix

**Budget-Conscious (< $0.50 per 100 images):**
- ✅ **gpt-4o-mini** - Best value overall
- ✅ **claude-3-5-haiku** - Alternative with different style

**Balanced Quality/Cost ($1-2 per 100 images):**
- ✅ **gpt-4o** - Excellent all-rounder
- ✅ **claude-3-7-sonnet** - More detailed descriptions

**Maximum Quality (cost secondary):**
- ✅ **gpt-5** - Latest reasoning capabilities
- ✅ **claude-opus-4** - Highest quality output

**Large Batches (1,000+ images):**
- ✅ Start with **gpt-4o-mini** for testing
- ✅ Process 10-20 samples with multiple models
- ✅ Analyze quality vs cost trade-off
- ✅ Use analysis CSV to make data-driven decision

---

## Token Tracking & Cost Analysis

### Workflow Token Logging

**Per-Image Tracking:**
```
Processing: IMG_1234.jpg
Generated description for IMG_1234.jpg (Provider: OpenAI, Model: gpt-4o)
Token usage: 3,865 total (3,156 prompt + 709 completion)
```

**Workflow Summary:**
```
============================================================
TOKEN USAGE SUMMARY:
  Total tokens: 386,500
  Prompt tokens: 315,600
  Completion tokens: 70,900
  Average tokens per image: 3,865
  Estimated cost: $1.50
============================================================
```

### Analysis CSV Export

Extract token data from all workflow runs:

```bash
cd analysis
python analyze_workflow_stats.py
```

**Output:** `workflow_analysis.csv`

**Example Data:**
```csv
Workflow,Provider,Model,Total Tokens,Prompt Tokens,Completion Tokens,Estimated Cost ($)
wf_openai_gpt-4o_20251007,openai,gpt-4o,386500,315600,70900,1.5000
wf_claude_sonnet_20251007,claude,claude-3-7-sonnet,753200,637600,115600,3.6500
```

**Use Cases:**
- Compare providers across identical image sets
- Track token usage trends
- Budget planning for production runs
- Identify optimization opportunities

### GUI Token Storage

**Per-Description Tracking:**
- Token usage stored with each description
- Persists in workspace.json files
- Available for future GUI display features

**See:** `docs/TOKEN_TRACKING_GUIDE.md` for complete details

---

## SDK Features & Benefits

### Automatic Retry Logic

**Built-in Exponential Backoff:**
- Retries up to 3 times on transient failures
- Handles rate limits automatically
- No manual retry code needed

**Example:**
```python
# SDK automatically retries on:
# - Rate limit errors (429)
# - Network timeouts
# - Temporary server errors (500s)
```

### Better Error Handling

**Specific Error Types:**
```python
# OpenAI SDK
from openai import RateLimitError, AuthenticationError, APIError

# Claude SDK  
from anthropic import RateLimitError, AuthenticationError, APIError
```

**User-Friendly Messages:**
```
Error: OpenAI API rate limit exceeded. Retrying in 5 seconds...
Error: Invalid API key. Please check your OPENAI_API_KEY environment variable.
Error: Model 'gpt-4x' not found. Available models: gpt-4o, gpt-4o-mini, gpt-5
```

### Token Usage Tracking

**Automatic Tracking:**
- Every API call returns token usage
- Prompt tokens (input)
- Completion tokens (output)
- Total tokens (sum)

**Cost Calculation:**
```python
# Example: gpt-4o
prompt_cost = (prompt_tokens / 1000) * 0.0025
completion_cost = (completion_tokens / 1000) * 0.010
total_cost = prompt_cost + completion_cost
```

---

## Troubleshooting

### Issue: SDK Not Installed

**Error:**
```
Warning: openai package not installed. Install with: pip install openai>=1.0.0
```

**Solution:**
```bash
# For system Python
pip install -r requirements.txt

# For .venv (batch files)
.venv\Scripts\pip.exe install -r requirements.txt
```

**Verify Installation:**
```bash
# Check system Python
python -c "import openai; import anthropic; print('SDKs installed')"

# Check .venv
.venv\Scripts\python.exe -c "import openai; import anthropic; print('SDKs installed')"
```

### Issue: API Key Not Found

**Error:**
```
Error: OpenAI API key not configured or SDK not installed
```

**Solutions:**
1. **Check environment variable:**
   ```bash
   # Windows
   echo %OPENAI_API_KEY%
   
   # Linux/Mac
   echo $OPENAI_API_KEY
   ```

2. **Check for API key file:**
   ```bash
   # Should exist in current directory or specified path
   dir openai.txt
   type openai.txt  # Verify contents (should start with sk-)
   ```

3. **Use --api-key-file flag:**
   ```bash
   python scripts/image_describer.py photos/ --provider openai --api-key-file path/to/openai.txt
   ```

### Issue: GPT-5 Parameter Error

**Error:**
```
Error: Unsupported parameter: 'max_tokens' is not supported with this model. 
Use 'max_completion_tokens' instead.
```

**Solution:**
Update to latest code - GPT-5 fix is already implemented:
```python
# Code automatically detects and uses correct parameter
if model.startswith('gpt-5') or model.startswith('o1') or model.startswith('o3'):
    request_params["max_completion_tokens"] = 1000
else:
    request_params["max_tokens"] = 1000
```

### Issue: No Token Tracking in Logs

**Symptoms:**
- Workflow completes successfully
- Descriptions generated correctly
- Missing TOKEN USAGE SUMMARY in logs

**Possible Causes:**
1. **SDKs not installed in .venv** (batch files use .venv)
2. **Using older code** (before SDK migration)
3. **Provider doesn't support tokens** (Ollama, ONNX don't have tokens)

**Solution:**
```bash
# Install SDKs in .venv
.venv\Scripts\pip.exe install openai>=1.0.0 anthropic>=0.18.0

# Verify installation
.venv\Scripts\pip.exe list | findstr "openai anthropic"

# Should show:
# openai         1.x.x
# anthropic      0.x.x
```

### Issue: Rate Limiting

**Error:**
```
Error: Rate limit exceeded. Retrying in 20 seconds...
```

**Solutions:**
1. **Wait for automatic retry** - SDK handles this
2. **Reduce batch size** - Process fewer images per run
3. **Upgrade API tier** - Check provider for higher rate limits
4. **Add delays** - Use `--delay` flag (if available)

**OpenAI Rate Limits (Free Tier):**
- 3 requests per minute
- 200 requests per day

**Upgrade to Paid Tier:**
- Higher rate limits
- Better performance
- Priority access

---

## Best Practices

### 1. Test Before Production

**Small Sample First:**
```bash
# Test with 10-20 images
python scripts/image_describer.py sample_photos/ --provider openai --model gpt-4o-mini

# Check TOKEN USAGE SUMMARY
# Calculate: (total_cost / 10) * production_image_count
```

### 2. Use Cost-Effective Models

**Start with cheapest model:**
1. Test with gpt-4o-mini or claude-3-5-haiku
2. Evaluate description quality
3. Upgrade to better model only if needed

**Example Progression:**
```
gpt-4o-mini ($0.25) → Test quality
  ↓ (if quality insufficient)
gpt-4o ($1.50) → Test quality
  ↓ (if still insufficient)
gpt-5 ($3.00) → Maximum quality
```

### 3. Secure Your API Keys

**DO:**
- ✅ Store keys in external files (outside repository)
- ✅ Use environment variables
- ✅ Add key files to .gitignore
- ✅ Rotate keys periodically

**DON'T:**
- ❌ Commit keys to Git
- ❌ Share keys in screenshots
- ❌ Use keys in command line (visible in history)
- ❌ Store keys in code

### 4. Monitor Usage & Costs

**Check Provider Dashboards:**
- OpenAI: [https://platform.openai.com/usage](https://platform.openai.com/usage)
- Claude: [https://console.anthropic.com/settings/usage](https://console.anthropic.com/settings/usage)

**Use Toolkit Analysis:**
```bash
# Generate analysis CSV
cd analysis
python analyze_workflow_stats.py

# Review costs across all runs
```

### 5. Optimize Prompts

**Be concise:**
```python
# Good (concise)
"Describe this image in detail"

# Verbose (more tokens)
"Please provide a comprehensive, detailed description of this image including all objects, colors, people, and background elements"
```

**Note:** Image encoding dominates token count, so prompt optimization has limited impact.

---

## Advanced Usage

### Custom Model Configuration

Edit `scripts/image_describer_config.json`:

```json
{
  "providers": {
    "openai": {
      "models": ["gpt-4o", "gpt-4o-mini", "gpt-5"],
      "default_model": "gpt-4o-mini",
      "timeout": 60,
      "max_retries": 3
    },
    "claude": {
      "models": ["claude-3-7-sonnet-20250219", "claude-3-5-haiku-20241022"],
      "default_model": "claude-3-5-haiku-20241022",
      "timeout": 60,
      "max_retries": 3
    }
  }
}
```

### Programmatic Access

```python
from imagedescriber.ai_providers import OpenAIProvider, ClaudeProvider

# OpenAI
openai_provider = OpenAIProvider(api_key="sk-...", timeout=60)
description = openai_provider.describe_image("photo.jpg", "Describe this image", "gpt-4o")
token_usage = openai_provider.get_last_token_usage()
print(f"Used {token_usage['total_tokens']} tokens")

# Claude
claude_provider = ClaudeProvider(api_key="sk-ant-...", timeout=60)
description = claude_provider.describe_image("photo.jpg", "Describe this image", "claude-3-7-sonnet-20250219")
token_usage = claude_provider.get_last_token_usage()
print(f"Cost estimate: ${calculate_cost(token_usage):.4f}")
```

---

## Additional Resources

**Documentation:**
- [TOKEN_TRACKING_GUIDE.md](TOKEN_TRACKING_GUIDE.md) - Comprehensive token tracking and cost analysis
- [SDK_MIGRATION_COMPLETE.md](../SDK_MIGRATION_COMPLETE.md) - Technical details of SDK integration
- [WORKFLOW_EXAMPLES.md](archive/WORKFLOW_EXAMPLES.md) - Complete workflow examples

**Provider Documentation:**
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)
- [Anthropic API Reference](https://docs.anthropic.com/en/api)

**Community:**
- [GitHub Issues](https://github.com/kellylford/Image-Description-Toolkit/issues)
- [GitHub Discussions](https://github.com/kellylford/Image-Description-Toolkit/discussions)

---

## Summary

**Key Takeaways:**

✅ **Two Cloud Providers** - OpenAI (GPT) and Claude supported
✅ **Official SDKs** - Automatic retry, better errors, token tracking
✅ **Cost Visibility** - Track every token and estimate costs
✅ **Multiple Models** - Choose based on quality/cost trade-off
✅ **Flexible Configuration** - Environment vars, files, or command line
✅ **Production Ready** - Tested with 10 cloud models

**Getting Started:**
1. Get API keys from provider websites
2. Install requirements: `pip install -r requirements.txt`
3. Configure API keys (environment or file)
4. Test with small batch to estimate costs
5. Process production images with selected model

**Cost Optimization:**
- Start with cheapest models (gpt-4o-mini or claude-3-5-haiku)
- Test quality before committing to expensive models
- Use analysis CSV to compare providers
- Monitor token usage in logs

Happy describing! 💡
