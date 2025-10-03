# Prompt Editor - Quick Reference

## Opening the Editor

```bash
cd /path/to/idt
python prompt_editor/prompt_editor.py
```

## Supported AI Providers

| Provider | Type | Cost | API Key Required | Models |
|----------|------|------|------------------|--------|
| **Ollama** | Local | Free | No | moondream, llama3.2-vision, llava |
| **OpenAI** | Cloud | Paid | Yes | gpt-4o, gpt-4o-mini, gpt-4-turbo |
| **ONNX** | Local | Free | No | florence-2-base, florence-2-large |
| **Copilot** | Cloud | Subscription | Via GitHub | gpt-4o, claude-3.5-sonnet |
| **HuggingFace** | Cloud | Free tier | Yes | Florence, BLIP models |

## Quick Setup

### For Ollama (Recommended for Local/Free)
1. Select provider: **ollama**
2. Click **Refresh**
3. Choose model: **moondream** (recommended)
4. Save

### For OpenAI (Recommended for Cloud/Quality)
1. Select provider: **openai**
2. Enter API key OR set `OPENAI_API_KEY` env var
3. Choose model: **gpt-4o-mini** (cost-effective)
4. Save

## Config File Location

```
scripts/image_describer_config.json
```

This file is used by:
- `scripts/image_describer.py`
- `scripts/workflow.py`
- `imagedescriber/imagedescriber.py` (GUI)

## Fields Managed

### Required
- `prompt_variations` - Prompt text for each style
- `default_prompt_style` - Which prompt to use by default

### Optional (New)
- `default_provider` - Which AI provider to use (defaults to "ollama")
- `api_key` - API key for cloud providers (falls back to env vars)
- `default_model` - Which model to use

### Legacy (Still Supported)
- `model_settings` - Temperature, top_p, etc. for Ollama
- `prompt_template` - Old-style single prompt
- `available_models` - Model descriptions

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+S | Save |
| Ctrl+Shift+S | Save As |
| Ctrl+O | Open |
| Ctrl+N | New Prompt |
| F5 | Reload |
| Ctrl+Q | Quit |

## Common Tasks

### Change AI Provider
1. Select provider from dropdown
2. Click **Refresh** to update models
3. Select model
4. Save

### Add API Key
1. Select cloud provider (OpenAI/HuggingFace)
2. API Key field appears
3. Enter key OR leave empty for env var
4. Click **Show** to verify
5. Save

### Create New Prompt Style
1. Click **Add Prompt**
2. Enter name (e.g., "scientific")
3. Edit prompt text
4. Save

### Set as Default
1. Edit prompt or select model
2. Choose from "Default Style" dropdown
3. Save

### Create Custom Config
1. Edit settings as needed
2. **Save As** (Ctrl+Shift+S)
3. Enter new filename (e.g., `scientific_config.json`)
4. Use with: `--config scientific_config.json`

## Command-Line Usage

### Use Config Defaults
```bash
python scripts/image_describer.py /path/to/images
```
Uses `default_provider`, `default_model`, `default_prompt_style` from config.

### Override Provider
```bash
python scripts/image_describer.py /path/to/images \
  --provider openai \
  --model gpt-4o-mini
```
Config says "ollama" but this run uses OpenAI.

### Override Everything
```bash
python scripts/image_describer.py /path/to/images \
  --provider openai \
  --model gpt-4o-mini \
  --prompt-style detailed \
  --api-key-file openai_key.txt
```
Ignores most config, uses CLI values.

## Security Best Practices

### API Keys

**Option 1: Environment Variable (Recommended)**
```bash
export OPENAI_API_KEY="sk-..."
# Leave API Key field empty in editor
```

**Option 2: Separate File (Most Secure)**
```bash
echo "sk-..." > openai_key.txt
chmod 600 openai_key.txt
# Use --api-key-file flag, don't put in config
```

**Option 3: Config File (Convenient)**
```
Enter in API Key field in editor
Saved to config as plain text
Good for personal use only
```

## Troubleshooting

### "AI providers not available"
**Cause**: Running from wrong directory
**Fix**: Run from project root: `python prompt_editor/prompt_editor.py`

### "Ollama not available"
**Cause**: Ollama not installed or not running
**Fix**: Install from https://ollama.ai, pull models with `ollama pull moondream`

### Models not showing after Refresh
**Cause**: Provider not available or no models installed
**Fix**: Install provider, pull/download models, or use predefined list

### API key not working
**Cause**: Invalid key or no credits
**Fix**: 
- Verify key at provider website
- Check account has credits/quota
- Try using `--api-key-file` instead
- Set environment variable instead

### Changes not taking effect
**Cause**: Not saving or scripts using different config
**Fix**:
- Save (Ctrl+S) after changes
- Check scripts use correct config file
- Verify CLI flags not overriding config

## Example Workflows

### Setup for Local Development
1. Provider: **ollama**
2. Model: **moondream**
3. Prompt: **narrative**
4. No API key needed
5. Free and fast

### Setup for Production/Quality
1. Provider: **openai**
2. Model: **gpt-4o-mini**
3. Prompt: **detailed**
4. API key via env var
5. Best quality/cost ratio

### Setup for Maximum Quality
1. Provider: **openai**
2. Model: **gpt-4o**
3. Prompt: **detailed**
4. API key via separate file
5. Highest quality, higher cost

### Setup for Scientific Use
1. Create custom prompt "scientific"
2. Provider: **openai**
3. Model: **gpt-4o**
4. Save as `scientific_config.json`
5. Use: `--config scientific_config.json`

## Testing Your Setup

```bash
# Test the editor works
python prompt_editor/test_prompt_editor.py

# Test image description with your config
python scripts/image_describer.py test_image.jpg
```

## Getting Help

- **Full guide**: `prompt_editor/MULTI_PROVIDER_UPDATE.md`
- **Update summary**: `docs/PROMPT_EDITOR_UPDATE.md`
- **General README**: `prompt_editor/README.md`
- **OpenAI setup**: `docs/OPENAI_SETUP_GUIDE.md`
