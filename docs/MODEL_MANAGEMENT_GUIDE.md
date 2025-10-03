# Model Management Quick Reference

## Overview

The Image Description Toolkit provides **standalone model management tools** that work independently of the GUI and scripts. You can manage models separately, then use them in your workflows.

## Key Philosophy

✅ **Command-line flexibility preserved** - All scripts still accept `--model` and `--prompt-style` arguments  
✅ **Standalone model management** - Check, install, and manage models without running the main tools  
✅ **No functionality lost** - Everything you can do now, you still can  
✅ **Better visibility** - Know what's on your system at a glance  

---

## Quick Commands

### Check What's Installed

```bash
# Check all providers and models
python check_models.py

# Check specific provider
python check_models.py --provider ollama

# Show detailed model info
python check_models.py --verbose

# Get JSON output (for scripting)
python check_models.py --json
```

### Manage Models

```bash
# List all available models
python manage_models.py list

# List only installed models
python manage_models.py list --installed

# Install a specific model
python manage_models.py install llava:7b

# Remove a model
python manage_models.py remove llava:7b

# Get detailed info about a model
python manage_models.py info llava:7b

# Show recommendations
python manage_models.py recommend

# Install all recommended models
python manage_models.py install --recommended
```

---

## Using Models in Scripts

### Command-Line Override (Preserved)

All scripts **still accept** `--model` and `--prompt-style` arguments:

```bash
# Use specific model (overrides config)
python scripts/image_describer.py photos/ --model llava:7b

# Use specific prompt style
python scripts/image_describer.py photos/ --prompt-style technical

# Combine both
python scripts/image_describer.py photos/ --model moondream --prompt-style detailed

# All other options still work
python scripts/image_describer.py photos/ --model llama3.2-vision:11b \
    --prompt-style creative \
    --max-size 2048 \
    --recursive \
    --verbose
```

### Workflow Configuration

Workflows can specify models in `workflow_config.json`:

```json
{
  "steps": {
    "image_description": {
      "model": "llava:7b",
      "prompt_style": "detailed"
    }
  }
}
```

Or leave as `null` to use defaults from `image_describer_config.json`.

---

## Typical Workflow

### 1. Check System Status

```bash
python check_models.py
```

**Output:**
```
=== Image Description Toolkit - Model Status ===

Ollama (Local Models)
  ✓ Status: OK
  Models: 3 available
    • llava:7b
    • moondream:latest
    • llama3.2-vision:11b

OpenAI
  ✗ Status: API key not configured
  → Add OpenAI API key to 'openai.txt' or OPENAI_API_KEY env var

=== Recommendations ===
  • ✓ Ollama is ready with 3 models
  • Optional: Configure OpenAI for cloud-based models
```

### 2. Explore Available Models

```bash
python manage_models.py list
```

See all models with descriptions, sizes, and installation commands.

### 3. Install What You Need

```bash
# Install a recommended model
python manage_models.py install llava:7b

# Or install all recommended models
python manage_models.py install --recommended
```

### 4. Use in Your Scripts

```bash
# Use installed model
python scripts/image_describer.py photos/ --model llava:7b

# Or use GUI - it will show only installed models
python imagedescriber/imagedescriber.py
```

---

## Model Selection Guide

### For Quick Testing
```bash
python manage_models.py install moondream
# Smallest (1.7GB), fastest
```

### For General Use
```bash
python manage_models.py install llava:7b
# Balanced (4.7GB), good quality
```

### For Maximum Quality
```bash
python manage_models.py install llama3.2-vision:11b
# Most accurate (7.5GB), slower
```

### For Cloud Processing
```bash
# Add API key to openai.txt
# Then use: --model gpt-4o-mini
```

---

## Advanced Usage

### Get Model Information

```bash
python manage_models.py info llava:7b
```

**Output:**
```
=== Model Information ===

Name: llava:7b
Provider: ollama
Description: LLaVA 7B - Good balance of speed and quality
Size: 4.7GB
Minimum RAM: 8GB
Tags: vision, multimodal, recommended
Recommended: Yes

Status: ✓ INSTALLED
```

### Check Specific Provider

```bash
# Check only Ollama
python check_models.py --provider ollama

# Check only OpenAI
python check_models.py --provider openai
```

### Script Integration

Use JSON output for automation:

```bash
# Get status as JSON
python check_models.py --json > models_status.json

# Parse in scripts
import json
with open('models_status.json') as f:
    status = json.load(f)
    if status['ollama']['available']:
        print(f"Found {len(status['ollama']['models'])} Ollama models")
```

---

## Configuration Files

### Model Metadata: `image_describer_config.json`

Contains default model settings and prompt styles:

```json
{
  "model_settings": {
    "default_model": "llava:7b",
    "temperature": 0.7,
    "max_tokens": 500
  },
  "prompt_variations": {
    "detailed": "Describe this image in detail...",
    "technical": "Provide technical analysis...",
    "creative": "Create an artistic description..."
  }
}
```

Scripts use this as default, but **command-line args always override**.

### Workflow Settings: `workflow_config.json`

Workflow-specific model configuration:

```json
{
  "steps": {
    "image_description": {
      "model": null,  // Use default from image_describer_config.json
      "prompt_style": "detailed"
    }
  }
}
```

---

## Troubleshooting

### Model Not Found

```bash
# Check if model is installed
python check_models.py

# Install it
python manage_models.py install llava:7b

# Verify installation
python check_models.py --verbose
```

### Ollama Not Running

```bash
# Check status
python check_models.py

# If Ollama not running, start it:
ollama serve
```

### Model List Empty

```bash
# Install a recommended model
python manage_models.py recommend
python manage_models.py install llava:7b
```

---

## Migration Notes

### What Changed

✅ **New:** Standalone `check_models.py` and `manage_models.py` tools  
✅ **Preserved:** All command-line arguments (`--model`, `--prompt-style`, etc.)  
✅ **Preserved:** Configuration files still work  
✅ **Preserved:** GUI model selection still works  
✅ **Improved:** Better visibility into what's installed  
✅ **Improved:** Easier model management  

### What Stayed the Same

All existing scripts work exactly as before:

```bash
# Still works
python scripts/image_describer.py photos/

# Still works
python scripts/image_describer.py photos/ --model llava:7b

# Still works
python imagedescriber/imagedescriber.py
```

---

## Examples

### Example 1: First-Time Setup

```bash
# 1. Check what's available
python check_models.py

# 2. See recommendations
python manage_models.py recommend

# 3. Install a model
python manage_models.py install llava:7b

# 4. Verify
python check_models.py

# 5. Use it
python scripts/image_describer.py photos/ --model llava:7b
```

### Example 2: Compare Models

```bash
# Install multiple models
python manage_models.py install moondream
python manage_models.py install llava:7b
python manage_models.py install llama3.2-vision:11b

# Test with different models
python scripts/image_describer.py test_photo.jpg --model moondream
python scripts/image_describer.py test_photo.jpg --model llava:7b
python scripts/image_describer.py test_photo.jpg --model llama3.2-vision:11b

# Remove ones you don't need
python manage_models.py remove moondream
```

### Example 3: Batch Processing Different Model Sizes

```bash
# Quick pass with fast model
python scripts/image_describer.py large_collection/ \
    --model moondream \
    --output-dir output/quick_pass

# Detailed pass with accurate model on selected images
python scripts/image_describer.py selected_images/ \
    --model llama3.2-vision:11b \
    --prompt-style detailed \
    --output-dir output/detailed_pass
```

---

## Summary

- **Model management is now standalone** - Use `check_models.py` and `manage_models.py`
- **All script functionality preserved** - `--model` and `--prompt-style` still work
- **Better visibility** - Know exactly what's installed
- **Easier troubleshooting** - Clear status and recommendations
- **Same flexibility** - Override configs anytime via command line

**The toolkit philosophy remains:** Give users the tools to manage AI models easily while preserving full command-line control.
