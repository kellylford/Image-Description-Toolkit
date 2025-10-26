# Prompt Editor - Multi-Provider Update

## Overview

The Prompt Editor has been updated to support multiple AI providers (Ollama, OpenAI, ONNX, Copilot, HuggingFace) in addition to managing prompt styles for the image description scripts.

## What Changed

### New Features

1. **AI Provider Selection**
   - Dropdown to select default provider: Ollama, OpenAI, ONNX, Copilot, or HuggingFace
   - Saved to config as `default_provider` field
   - Can be overridden via `--provider` command-line flag when running scripts

2. **API Key Configuration**
   - Input field for API keys (OpenAI, HuggingFace)
   - Auto-shows/hides based on selected provider
   - Password field with Show/Hide toggle
   - Saved to config as `api_key` field (optional)
   - Falls back to environment variables if not specified

3. **Multi-Provider Model Discovery**
   - **Ollama**: Queries local Ollama installation for available models
   - **OpenAI**: Shows predefined list (gpt-4o, gpt-4o-mini, gpt-4-turbo, etc.)
   - **ONNX**: Queries for local Florence-2 models
   - **Copilot**: Shows GitHub Copilot models (gpt-4o, claude-3.5-sonnet, etc.)
   - **HuggingFace**: Shows common vision models

## Config File Structure

The prompt editor reads and writes `scripts/image_describer_config.json`:

```json
{
  "default_prompt_style": "narrative",
  "default_provider": "ollama",
  "default_model": "moondream",
  "api_key": "sk-...",  // Optional, only for OpenAI/HuggingFace
  "prompt_variations": {
    "detailed": "Describe this image in detail...",
    "narrative": "Provide a narrative description...",
    "concise": "Describe this image concisely...",
    ...
  },
  "model_settings": {
    "model": "moondream",
    "temperature": 0.1,
    "num_predict": 600,
    ...
  }
}
```

## How Scripts Use This Config

### image_describer.py

```bash
# Uses config for prompts and model settings
python scripts/image_describer.py /path/to/images \
  --config image_describer_config.json \
  --prompt-style narrative \
  --provider openai \
  --model gpt-4o-mini
```

The script reads:
- `prompt_variations[prompt-style]` - The prompt text to use
- `default_provider` - Falls back to this if `--provider` not specified
- `default_model` - Falls back to this if `--model` not specified
- `api_key` - Uses for authentication if provider requires it

### workflow.py

```bash
# Workflow uses both workflow_config.json and image_describer_config.json
python workflow.py /path/to/images \
  --provider openai \
  --model gpt-4o-mini \
  --prompt-style narrative
```

Reads `image_describer_config.json` for:
- Prompt variations
- Default provider/model fallbacks

## Usage Guide

### Setting Up for Ollama (Local)

1. Open Prompt Editor
2. Select Provider: **ollama**
3. Click **Refresh** to load installed models
4. Select your preferred model (e.g., moondream)
5. API Key field hidden (not needed)
6. Save

### Setting Up for OpenAI (Cloud)

1. Open Prompt Editor
2. Select Provider: **openai**
3. Model list shows: gpt-4o, gpt-4o-mini, etc.
4. API Key field appears
5. Enter your OpenAI API key OR leave empty to use `OPENAI_API_KEY` env var
6. Select model (recommend gpt-4o-mini for cost)
7. Save

### Setting Up for ONNX (Local)

1. Open Prompt Editor
2. Select Provider: **onnx**
3. Model list shows: florence-2-base, florence-2-large
4. API Key field hidden (not needed)
5. Select model
6. Save

### Setting Up for HuggingFace (Cloud)

1. Open Prompt Editor
2. Select Provider: **huggingface**
3. Model list shows common vision models
4. API Key field appears
5. Enter HuggingFace API token OR leave empty for env var
6. Select model
7. Save

## Command-Line Override

The `default_provider` in config is just a fallback. You can always override:

```bash
# Config says "ollama" but you want to use OpenAI
python scripts/image_describer.py /path/to/images \
  --provider openai \
  --model gpt-4o-mini \
  --api-key-file openai_key.txt
```

## Backward Compatibility

- Existing config files without `default_provider` will default to "ollama"
- Existing config files without `api_key` will work fine (uses env vars)
- Old Ollama-only model discovery still works if ollama module available
- All existing prompt variations and model settings preserved

## Testing

Run the test script to verify everything works:

```bash
python prompt_editor/test_prompt_editor.py
```

Should show:
- ✓ AI providers imported successfully
- ✓ Each provider's model discovery working
- No import errors

## Security Notes

### API Keys in Config

**Option 1: Store in config** (convenient but less secure)
- Saved in `image_describer_config.json`
- Visible in plain text
- Good for personal/local use

**Option 2: Use environment variable** (more secure)
- Set `OPENAI_API_KEY` or `HUGGINGFACE_TOKEN`
- Leave API Key field empty in editor
- Good for shared systems

**Option 3: Use separate key file** (most secure)
- Store key in separate file (e.g., `openai_key.txt`)
- Use `--api-key-file` flag when running scripts
- Add key file to `.gitignore`
- Best for version control

## Known Limitations

1. **Ollama Model Discovery**: Requires `ollama` Python module installed
   - Falls back to error message if not available
   - Still allows manual model entry in config

2. **ONNX Model Discovery**: Requires ONNX provider initialized
   - Falls back to predefined list if error

3. **API Key Storage**: Stored in plain text in config
   - Consider using environment variables for production

## Troubleshooting

### "AI providers not available" warning
- The imagedescriber package is not in path
- Run from root directory: `python prompt_editor/prompt_editor.py`

### "Ollama not available" error
- Ollama not installed OR no models pulled
- Install: https://ollama.ai
- Pull models: `ollama pull moondream`

### Models not appearing after refresh
- Provider may not be running (Ollama)
- Check provider availability
- Use predefined model list as fallback

### API key not working
- Check key is valid and has credits
- Try using `--api-key-file` instead
- Set environment variable instead of config

## Summary

The Prompt Editor now:
- ✅ Supports 5 AI providers (Ollama, OpenAI, ONNX, Copilot, HuggingFace)
- ✅ Manages provider selection in config
- ✅ Handles API keys securely (with env var fallback)
- ✅ Discovers models from each provider
- ✅ Maintains backward compatibility
- ✅ Still edits prompt variations as before
- ✅ Integrates with workflow.py and image_describer.py

Scripts can use the config defaults or override via command-line flags.
