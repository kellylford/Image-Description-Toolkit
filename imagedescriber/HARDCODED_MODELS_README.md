# Development Mode: Hardcoded Models Implementation

## Overview
Implemented hardcoded model lists to bypass slow model detection during development and testing. This is a **temporary workaround** that should be removed before production release.

## System Query Results
Based on your system, the following models were detected and hardcoded:

### Ollama Local Models (7 models)
- `bakllava:latest` - 4.7GB
- `mistral-small3.1:latest` - 15GB  
- `gemma3:latest` - 3.3GB
- `moondream:latest` - 1.7GB
- `llava-llama3:latest` - 5.5GB
- `llama3.2-vision:latest` - 7.8GB
- `llava:latest` - 4.7GB

### Ollama Cloud Models (4 models)
- `gpt-oss:20b-cloud` - 20B parameters
- `deepseek-v3.1:671b-cloud` - 671B parameters
- `gpt-oss:120b-cloud` - 120B parameters  
- `qwen3-coder:480b-cloud` - 480B parameters

### OpenAI Models (5 models)
- `gpt-4o` - Latest multimodal model
- `gpt-4o-mini` - Faster, smaller version
- `gpt-4-turbo` - Enhanced GPT-4
- `gpt-4` - Standard GPT-4
- `gpt-4-vision-preview` - Vision-capable model

### HuggingFace Models (5 models)
- `Salesforce/blip-image-captioning-base` - BLIP base model
- `Salesforce/blip-image-captioning-large` - BLIP large model
- `microsoft/DialoGPT-medium` - Dialog model
- `microsoft/DialoGPT-large` - Large dialog model
- `facebook/blenderbot-400M-distill` - Distilled chatbot

## Implementation Details

### Code Changes
- **File**: `imagedescriber/ai_providers.py`
- **Flag**: `DEV_MODE_HARDCODED_MODELS = True`
- **Preservation**: All original detection code is preserved but bypassed

### Detection Logic
Each provider's `get_available_models()` method now follows this pattern:
```python
def get_available_models(self) -> List[str]:
    # DEVELOPMENT MODE: Return hardcoded models for faster testing
    if DEV_MODE_HARDCODED_MODELS:
        return DEV_[PROVIDER]_MODELS.copy()
    
    # ORIGINAL DETECTION CODE (preserved for when dev mode is disabled)
    # ... original caching and detection logic ...
```

## Performance Impact
- **Before**: 20-30 second delays for model selection
- **After**: Instant model population (hardcoded lists)
- **Trade-off**: Models may not reflect actual system state

## GitHub Issue Tracking
- **Issue #23**: https://github.com/kellylford/Image-Description-Toolkit/issues/23
- **Title**: "Remove hardcoded model lists for development testing"
- **Status**: Open - requires fixing underlying caching performance

## Next Steps

### For Continued Development
1. Model selection should now be instant
2. Chat feature works with all provider types
3. All UI components use consistent model lists

### Before Production Release
1. Fix caching performance issues
2. Set `DEV_MODE_HARDCODED_MODELS = False`
3. Test with real model detection
4. Remove hardcoded lists and dev mode flag
5. Verify UI performance is acceptable

## Reverting Changes
To revert to real model detection:
1. Open `imagedescriber/ai_providers.py`
2. Change `DEV_MODE_HARDCODED_MODELS = True` to `False`
3. Restart the application

## Testing Notes
- Application starts without errors
- Model selection should be instant
- All provider types (ollama, ollama_cloud, openai, huggingface) have models available
- Chat functionality should work with all providers
- Original detection code remains intact for future use

This implementation provides a clean development environment while preserving the ability to return to real model detection when performance issues are resolved.