# Token Tracking Guide

**Last Updated:** October 7, 2025

---

## Overview

The Image Description Toolkit now tracks token usage and costs for all cloud AI providers (OpenAI and Claude). This guide explains how token tracking works, how to analyze costs, and how to optimize your AI spending.

---

## What Are Tokens?

**Tokens** are the units that AI models use to process text and images. Both input (prompts) and output (descriptions) consume tokens.

**Typical Token Counts:**
- Simple image description: 500-1,500 tokens
- Detailed image description: 1,500-3,000 tokens
- Complex scene with multiple objects: 3,000-8,000 tokens

**Image Encoding:**
- Images are converted to tokens by the AI provider
- Larger/higher-resolution images = more tokens
- Most of the tokens come from the image itself, not the prompt

---

## Two Tracking Approaches

The toolkit uses **two parallel approaches** for token tracking, optimized for different use cases:

### 1. Batch Scripts - Per-Workflow Totals

**Use Case:** Analyzing costs across entire workflow runs

**When to use:**
- Processing large batches of images
- Comparing costs between providers/models
- Budget planning for production runs
- Optimizing workflow efficiency

**Where to find:**
- Workflow logs: `Descriptions/wf_*/logs/image_describer_*.log`
- Analysis CSV: `analysis/workflow_analysis.csv`

### 2. GUI - Per-Description Properties

**Use Case:** Individual image analysis and detailed tracking

**When to use:**
- Processing individual images in ImageDescriber
- Detailed cost analysis per image
- Understanding token usage patterns
- Future GUI display features

**Where to find:**
- Workspace JSON files: `Descriptions/*/workspace.json`
- ImageDescriber GUI (stored with each description)

---

## Batch Script Token Tracking

### Per-Image Logging

When processing images, each description shows token usage:

```
Processing: IMG_1234.jpg
Generated description for IMG_1234.jpg (Provider: OpenAI, Model: gpt-4o)
Token usage: 3,865 total (3,156 prompt + 709 completion)
Estimated cost: $0.0150
```

**Token Breakdown:**
- **Prompt tokens** - Image encoding + text prompt
- **Completion tokens** - Generated description
- **Total tokens** - Sum of prompt + completion

### Workflow Summary

At the end of each workflow run:

```
============================================================
WORKFLOW SUMMARY
============================================================
Provider: openai
Model: gpt-4o
Prompt Style: narrative
Total images processed: 100
Newly processed: 100
Previously cached: 0
Failed: 0
Processing time: 8m 32s
Average time per image: 5.12s

TOKEN USAGE SUMMARY:
  Total tokens: 386,500
  Prompt tokens: 315,600
  Completion tokens: 70,900
  Average tokens per image: 3,865
  Estimated cost: $1.50
============================================================
```

### Cost Estimation

The toolkit includes pricing for common models (as of October 2025):

| Provider | Model | Input Cost | Output Cost |
|----------|-------|------------|-------------|
| OpenAI | gpt-4o | $0.0025/1K | $0.010/1K |
| OpenAI | gpt-4o-mini | $0.00015/1K | $0.0006/1K |
| OpenAI | gpt-5 | $0.005/1K | $0.015/1K |
| Claude | claude-3-7-sonnet | $0.003/1K | $0.015/1K |
| Claude | claude-opus-4 | $0.015/1K | $0.075/1K |
| Claude | claude-3-5-haiku | $0.001/1K | $0.005/1K |

**Note:** Costs are estimates. Actual costs may vary. Always check your provider's billing for exact charges.

### Analysis CSV Export

Run the analysis script to export token data to CSV:

```bash
cd analysis
python analyze_workflow_stats.py
```

**Output:** `analysis/workflow_analysis.csv`

**CSV Columns:**
```csv
Workflow Name,Provider,Model,Prompt Style,Total Images,Newly Processed,Failed,
Processing Time,Avg Time/Image,Total Tokens,Prompt Tokens,Completion Tokens,Estimated Cost ($)

wf_openai_gpt-4o_narrative_20251007,openai,gpt-4o,narrative,100,100,0,
512s,5.12s,386500,315600,70900,1.5000

wf_claude_sonnet-45_narrative_20251007,claude,claude-3-7-sonnet,narrative,100,100,0,
428s,4.28s,753200,637600,115600,3.6500
```

**Use Cases:**
- Compare costs across different providers
- Find the most cost-effective model for your images
- Track token usage trends over time
- Budget planning for large projects

---

## GUI Token Tracking

### Description Properties

When you generate a description in ImageDescriber GUI, token usage is stored with the description:

**ImageDescription Object:**
```python
{
  "id": "1728324018000",
  "text": "A beautiful sunset over the ocean with orange and pink hues...",
  "model": "gpt-4o",
  "provider": "openai",
  "prompt_style": "narrative",
  "created": "2025-10-07T14:20:18",
  "total_tokens": 986,
  "prompt_tokens": 789,
  "completion_tokens": 197
}
```

### Workspace Persistence

Token data is automatically saved to workspace JSON files:

**Location:** `Descriptions/[workspace_name]/workspace.json`

**Example:**
```json
{
  "current_index": 0,
  "image_files": ["IMG_1234.jpg"],
  "image_descriptions": {
    "IMG_1234.jpg": [
      {
        "text": "A beautiful sunset...",
        "model": "gpt-4o",
        "provider": "openai",
        "total_tokens": 986,
        "prompt_tokens": 789,
        "completion_tokens": 197,
        "created": "2025-10-07T14:20:18"
      }
    ]
  }
}
```

### Data Flow

1. **AI Provider** - OpenAI or Claude SDK returns token usage
2. **ProcessingWorker** - Retrieves via `get_last_token_usage()`
3. **Signal Emission** - Passes token data to GUI
4. **ImageDescription** - Stores tokens as properties
5. **Workspace Save** - Persists to JSON file

**Benefits:**
- Historical tracking of token usage per image
- Compare different descriptions of the same image
- Future GUI display capabilities
- Detailed cost analysis

---

## Cost Optimization Tips

### 1. Choose the Right Model

**For simple descriptions:** Use the smallest model that meets your needs
- OpenAI: gpt-4o-mini (6x cheaper than gpt-4o)
- Claude: claude-3-5-haiku (5x cheaper than Claude Opus)

**For detailed descriptions:** Balance quality vs cost
- OpenAI: gpt-4o (good balance)
- Claude: claude-3-7-sonnet (latest features)

**Example Cost Comparison (100 images @ ~4,000 tokens each):**
```
gpt-4o:           $1.50
gpt-4o-mini:      $0.25  (6x cheaper)
claude-opus-4:    $7.50  (5x more expensive)
claude-3-5-haiku: $1.00  (1.5x cheaper than gpt-4o)
```

### 2. Optimize Your Prompts

**Shorter prompts = fewer tokens:**
```python
# Higher cost (verbose prompt)
"Please provide a detailed and comprehensive description of this image, 
including all objects, people, colors, and the overall scene"

# Lower cost (concise prompt)
"Describe this image in detail"
```

**Note:** Most tokens come from the image itself, so prompt optimization has limited impact.

### 3. Use Prompt Caching

The toolkit automatically caches descriptions:
- Reprocessing the same image with the same settings = **FREE** (uses cached description)
- Token costs only apply to newly generated descriptions

**Example:**
```
Total images processed: 100
Newly processed: 25  (cost: $0.38)
Previously cached: 75 (cost: $0.00)
Total cost: $0.38
```

### 4. Monitor Token Usage

**Check logs regularly:**
```bash
# Find high-cost images
grep -i "token usage" Descriptions/wf_*/logs/image_describer*.log | sort -k5 -rn | head -10
```

**Analyze trends:**
```bash
# Generate analysis CSV
cd analysis
python analyze_workflow_stats.py

# Review costs across workflows
```

### 5. Test Before Production

**Use small test runs to estimate costs:**
```bash
# Process 10 test images
python scripts/image_describer.py test_images/ --provider openai --model gpt-4o-mini

# Check TOKEN USAGE SUMMARY in logs
# Multiply by (total_images / 10) for production estimate
```

---

## Real-World Examples

### Example 1: Photo Album Processing

**Scenario:** 500 family photos, narrative descriptions

**Test Run (10 images):**
```
Model: gpt-4o-mini
Total tokens: 38,650
Prompt tokens: 31,560
Completion tokens: 7,090
Average per image: 3,865 tokens
Estimated cost: $0.025
```

**Production Estimate:**
- 500 images × $0.0025 per image = **$1.25 total**
- Processing time: ~42 minutes (5s per image)

**Cost Optimization:**
- Switch to gpt-4o-mini if quality acceptable
- Use caching for reprocessing (free)

### Example 2: Professional Photography Catalog

**Scenario:** 1,000 high-res product photos, detailed descriptions

**Test Run (10 images):**
```
Model: gpt-4o
Total tokens: 75,320
Prompt tokens: 63,760
Completion tokens: 11,560
Average per image: 7,532 tokens
Estimated cost: $0.37
```

**Production Estimate:**
- 1,000 images × $0.037 per image = **$37.00 total**
- Processing time: ~85 minutes (5s per image)

**Cost Optimization:**
- Test claude-3-5-haiku (3.7x cheaper: ~$10 total)
- Compare quality vs cost trade-off

### Example 3: Medical Image Analysis

**Scenario:** 200 X-rays, technical descriptions

**Test Run (10 images):**
```
Model: gpt-4o (highest quality)
Total tokens: 98,650
Prompt tokens: 85,600
Completion tokens: 13,050
Average per image: 9,865 tokens
Estimated cost: $0.48
```

**Production Estimate:**
- 200 images × $0.048 per image = **$9.60 total**
- Processing time: ~17 minutes (5s per image)

**Recommendation:**
- Use highest quality model (gpt-4o or claude-opus-4)
- Cost is minimal compared to accuracy requirements
- Token tracking helps budget for larger datasets

---

## Troubleshooting

### Token Data Not Appearing

**Issue:** Workflow completes but no TOKEN USAGE SUMMARY

**Possible Causes:**
1. **SDKs not installed in .venv**
   ```bash
   # Check installation
   .venv\Scripts\pip.exe list | findstr "openai anthropic"
   
   # Install if missing
   .venv\Scripts\pip.exe install openai>=1.0.0 anthropic>=0.18.0
   ```

2. **Using older provider code**
   - Update to latest code with SDK integration
   - Check that `get_last_token_usage()` method exists

3. **Provider doesn't support token tracking**
   - Only OpenAI and Claude return token data
   - Local providers (Ollama, ONNX) don't have token costs

### Incorrect Cost Estimates

**Issue:** Estimated costs don't match actual billing

**Possible Causes:**
1. **Pricing changed** - Providers update pricing regularly
   - Check current pricing at provider websites
   - Update cost calculation in `scripts/image_describer.py`

2. **Different model version** - Some models have usage-based pricing tiers
   - Verify exact model name in logs
   - Check provider billing dashboard for actual costs

3. **Additional fees** - Some providers charge extra for:
   - API access tiers
   - Rate limit increases
   - Premium support

**Solution:** Always verify costs in your provider's billing dashboard. Toolkit estimates are for planning purposes only.

### GUI Token Data Not Saving

**Issue:** Token usage not in workspace.json

**Possible Causes:**
1. **Old workspace format** - Created before token tracking
   - Solution: Process a new image to update format
   - Old descriptions won't have token data (that's normal)

2. **Signal handler not updated**
   - Verify `on_processing_complete` receives token_usage parameter
   - Check ProcessingWorker emits token data in signal

3. **Provider error** - Description generated but token retrieval failed
   - Check logs for provider errors
   - Verify `get_last_token_usage()` returns data

---

## API Reference

### Token Usage Object

```python
{
    'total_tokens': int,        # Total tokens used
    'prompt_tokens': int,       # Input tokens (image + prompt)
    'completion_tokens': int,   # Output tokens (description)
    'model': str               # Model name used
}
```

### Provider Methods

**OpenAIProvider:**
```python
provider = OpenAIProvider(api_key, timeout=60)
description = provider.describe_image(image_path, prompt, model)
token_usage = provider.get_last_token_usage()
# Returns: {'total_tokens': 3865, 'prompt_tokens': 3156, 'completion_tokens': 709, 'model': 'gpt-4o'}
```

**ClaudeProvider:**
```python
provider = ClaudeProvider(api_key, timeout=60)
description = provider.describe_image(image_path, prompt, model)
token_usage = provider.get_last_token_usage()
# Returns: {'total_tokens': 7532, 'prompt_tokens': 6376, 'completion_tokens': 1156, 'model': 'claude-3-7-sonnet'}
```

### ImageDescription Properties

```python
class ImageDescription:
    total_tokens: int = None      # Total tokens used
    prompt_tokens: int = None     # Input tokens
    completion_tokens: int = None # Output tokens
```

---

## Future Enhancements

### Planned Features

1. **GUI Token Display**
   - Show token counts in description list
   - Display cost estimates in properties panel
   - Aggregate costs for all descriptions in workspace

2. **Token Budget Alerts**
   - Set per-workflow cost limits
   - Warning when approaching budget
   - Stop processing at threshold

3. **Cost Analytics Dashboard**
   - Visual charts of token usage trends
   - Provider cost comparisons
   - Model efficiency metrics

4. **Token Optimization**
   - Automatic model selection based on budget
   - Smart caching to minimize reprocessing
   - Prompt optimization suggestions

### Contributing Ideas

Have suggestions for token tracking improvements? 
- Open an issue: [GitHub Issues](https://github.com/kellylford/Image-Description-Toolkit/issues)
- Start a discussion: [GitHub Discussions](https://github.com/kellylford/Image-Description-Toolkit/discussions)

---

## Summary

**Key Takeaways:**

✅ **Batch Scripts** - Track total tokens/costs per workflow run
✅ **GUI** - Store token data with each description
✅ **Analysis CSV** - Export for detailed cost analysis
✅ **Cost Estimation** - Built-in pricing for common models
✅ **Optimization** - Choose right model for your budget

**Token tracking helps you:**
- Understand AI costs before large runs
- Choose the most cost-effective models
- Budget accurately for production workloads
- Optimize prompts and workflows

**Next Steps:**
1. Process a test batch to see token tracking in action
2. Review TOKEN USAGE SUMMARY in logs
3. Generate analysis CSV to compare providers
4. Choose optimal model for your use case

Happy optimizing! 🚀
