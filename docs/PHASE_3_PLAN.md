# Phase 3: Provider Integration in Scripts - Implementation Plan

## 🎯 Objective
Enable all AI providers (Ollama, OpenAI, ONNX, Copilot+ PC, etc.) in command-line scripts, not just the GUI.

## 📋 Current Status

### Scripts Analysis:
- **`scripts/image_describer.py`**: ❌ Ollama-only (hardcoded)
- **`scripts/workflow.py`**: ❌ Ollama-only (hardcoded)
- **`scripts/video_frame_extractor.py`**: ❌ Ollama-only (hardcoded)

### GUI Status:
- **`imagedescriber/imagedescriber.py`**: ✅ All providers available

## 🔧 Proposed Changes

### 1. Add `--provider` Flag to Scripts

```bash
# Current (Ollama only):
python scripts/image_describer.py photos/ --model llava:7b

# Proposed (All providers):
python scripts/image_describer.py photos/ --provider ollama --model llava:7b
python scripts/image_describer.py photos/ --provider openai --model gpt-4o-mini
python scripts/image_describer.py photos/ --provider onnx --model florence2
python scripts/image_describer.py photos/ --provider copilot --model florence2-base
```

### 2. Import Provider Classes from GUI

Reuse existing providers from `imagedescriber/ai_providers.py`:

```python
# Add to scripts/image_describer.py
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from imagedescriber.ai_providers import (
    OllamaProvider,
    OpenAIProvider,
    ONNXProvider,
    CopilotProvider,
    HuggingFaceProvider
)

def get_provider(provider_name: str):
    """Factory function to get provider instance"""
    providers = {
        'ollama': OllamaProvider,
        'openai': OpenAIProvider,
        'onnx': ONNXProvider,
        'copilot': CopilotProvider,
        'huggingface': HuggingFaceProvider
    }
    
    provider_class = providers.get(provider_name.lower())
    if not provider_class:
        raise ValueError(f"Unknown provider: {provider_name}")
    
    provider = provider_class()
    if not provider.is_available():
        raise RuntimeError(f"Provider '{provider_name}' is not available")
    
    return provider
```

### 3. Update Description Method

```python
class ImageDescriber:
    def __init__(self, provider='ollama', model_name=None, ...):
        self.provider = get_provider(provider)
        self.model_name = model_name
    
    def get_description(self, image_path, prompt):
        """Get description using configured provider"""
        return self.provider.describe_image(
            image_path,
            prompt,
            self.model_name
        )
```

### 4. Add Provider Discovery

```python
def list_available_providers():
    """Show available providers and their models"""
    from models.provider_configs import PROVIDER_CAPABILITIES
    
    print("Available Providers:\n")
    
    for provider_name in ['ollama', 'openai', 'onnx', 'copilot', 'huggingface']:
        provider = get_provider(provider_name)
        if provider.is_available():
            models = provider.get_available_models()
            print(f"✓ {provider.get_provider_name()}")
            for model in models[:5]:  # Show first 5
                print(f"    • {model}")
            if len(models) > 5:
                print(f"    ... and {len(models) - 5} more")
        else:
            print(f"✗ {provider_name} (not available)")
```

### 5. Update Config File Structure

**`scripts/image_describer_config.json`**:
```json
{
  "default_provider": "ollama",
  "providers": {
    "ollama": {
      "default_model": "llava:7b",
      "options": {
        "temperature": 0.7,
        "num_ctx": 2048
      }
    },
    "openai": {
      "default_model": "gpt-4o-mini",
      "options": {
        "temperature": 0.7,
        "max_tokens": 500
      }
    },
    "onnx": {
      "default_model": "Enhanced Ollama (NPU/GPU)",
      "options": {}
    },
    "copilot": {
      "default_model": "florence2-base",
      "options": {}
    }
  },
  "prompt_styles": {
    "detailed": "Provide a detailed description...",
    "technical": "Describe this image focusing on...",
    "accessibility": "Describe for visually impaired..."
  }
}
```

## 📊 Files to Modify

1. **`scripts/image_describer.py`** (1044 lines)
   - Add provider selection
   - Import provider classes
   - Update ImageDescriber class
   - Add `--provider` and `--list-providers` args

2. **`scripts/workflow.py`** 
   - Similar changes
   - Support provider in workflow config

3. **`scripts/image_describer_config.json`**
   - Add provider configurations

4. **`scripts/workflow_config.json`**
   - Add provider configurations

## ✅ Benefits

1. **Consistency**: Scripts and GUI use same provider code
2. **Flexibility**: Users can choose provider for batch processing
3. **Testing**: Easier to test providers without GUI
4. **Integration**: CI/CD pipelines can use different providers

## 🧪 Testing Plan

```bash
# Test Ollama (current default)
python scripts/image_describer.py test.jpg --provider ollama --model llava:7b

# Test OpenAI
python scripts/image_describer.py test.jpg --provider openai --model gpt-4o-mini --api-key-file openai.txt

# Test ONNX (Enhanced with YOLO)
python scripts/image_describer.py test.jpg --provider onnx --model "llava:latest (YOLO Enhanced)"

# Test Copilot+ PC
python scripts/image_describer.py test.jpg --provider copilot --model florence2-base

# List all available providers
python scripts/image_describer.py --list-providers
```

## ⏱️ Estimated Implementation Time

- **scripts/image_describer.py**: 2 hours
- **scripts/workflow.py**: 1.5 hours  
- **Config updates**: 0.5 hours
- **Testing**: 1 hour
- **Total**: ~5 hours

## 🚦 Decision Point

**Options:**
1. **Implement Phase 3 now** (add provider support to scripts)
2. **Skip to Phase 4** (remove GUI model manager - quick win)
3. **Skip to Phase 5** (prompt support consistency - medium priority)
4. **Skip to Phase 6** (model options framework - enhances all providers)

**Recommendation:**  
Since Phases 4-6 improve the existing GUI (which already works), and Phase 3 adds functionality to scripts, consider:
- **Quick wins first**: Phases 4 & 5 (cleanup + UX improvements)
- **Then Phase 6**: Options framework (benefits all providers)
- **Finally Phase 3**: Scripts provider support (new functionality)

This way you get immediate improvements while we figure out Florence-2 compatibility for Copilot+ PC.

## 📝 Notes

- All providers are already implemented in `imagedescriber/ai_providers.py`
- Just need to expose them in scripts
- Config file changes are backward compatible
- Current Ollama-only behavior would be default

---

**Current Status**: Plan documented, awaiting decision on implementation order.
