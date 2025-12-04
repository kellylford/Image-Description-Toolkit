# HuggingFace Provider Guide - Florence-2 Local Vision Models

## Overview

The HuggingFace provider enables local AI-powered image descriptions using Microsoft's Florence-2 vision models. Run entirely on your hardware with zero API costs and no internet connection required (after initial model download).

## Features

- **Zero Cost**: No API keys, no cloud costs
- **Privacy**: All processing happens locally
- **Python 3.13 Compatible**: Works with latest Python
- **Three Detail Levels**: Simple, detailed, and narrative descriptions
- **Two Model Sizes**: Base (230MB, faster) and Large (700MB, better quality)

## Usage

### GUI (ImageDescriber)

1. Open ImageDescriber application
2. Select **Provider**: `HuggingFace`
3. Select **Model**: `microsoft/Florence-2-base` or `microsoft/Florence-2-large`
4. Select **Prompt Style**: 
   - `simple` - Brief captions
   - `detailed` - Technical descriptions  
   - `narrative` - Comprehensive descriptions
5. Process images normally

### CLI (idt command)

```bash
# Basic usage with HuggingFace provider
idt workflow --provider huggingface --model microsoft/Florence-2-base --prompt-style narrative input_folder/

# With specific output directory
idt workflow --provider huggingface --model microsoft/Florence-2-large --output results/ images/

# Single image
idt describe --provider huggingface --model microsoft/Florence-2-base image.jpg
```

### Python API

```python
from imagedescriber.ai_providers import HuggingFaceProvider

provider = HuggingFaceProvider()

# Check availability
if provider.is_available():
    print("Florence-2 dependencies installed")
    
# Get available models
models = provider.get_available_models()
# Returns: ['microsoft/Florence-2-base', 'microsoft/Florence-2-large']

# Generate description
description = provider.describe_image(
    image_path='photo.jpg',
    prompt='Create a narrative comprehensive description',
    model='microsoft/Florence-2-base'
)

print(description)
```

## Model Comparison

| Model | Size | Speed | Quality | Best For |
|-------|------|-------|---------|----------|
| **Florence-2-base** | 230MB | Faster | Good | Testing, bulk processing |
| **Florence-2-large** | 700MB | Slower | Better | Final production, quality-critical |

### Detail Level Examples

**Test Image**: Red square on white background

**Simple** (`<CAPTION>`):
> "a red background with a white border"

**Detailed** (`<DETAILED_CAPTION>`):
> "The image shows a red background with a white border, creating a striking contrast between the two colors. The red color is vibrant and stands out against the white background, making it the focal point of the image."

**Narrative** (`<MORE_DETAILED_CAPTION>`):
> "The image is a solid red color with a smooth and uniform texture. The color is a deep, rich shade of red that stands out against the background. The image has a simple and minimalistic design, with no other elements present. The overall color scheme is predominantly red, with some areas being lighter and others being darker."

## Performance

### Current (CPU Only)

- **First Load**: 3-5 seconds (model download + initialization)
- **Subsequent Loads**: Instant (model cached)
- **Generation**: 5-10 seconds per image (CPU)
- **Memory**: ~2GB RAM for base model, ~4GB for large

### Future (NPU Acceleration - Phase 2)

- **Expected**: 10-20x faster (~0.5-1 second per image)
- **Hardware**: Copilot+ PC with NPU
- **Requirements**: DirectML + onnxruntime-directml

## Technical Details

### Compatibility Workaround

Florence-2 uses `use_cache=False` in generation due to incompatibility between the model's cache handling (designed for transformers <4.57) and the new `EncoderDecoderCache` format in transformers 4.57+.

**Impact**: 10-20% slower generation but ensures Python 3.13 compatibility.

**Tracking**: This workaround will be removed when Florence-2's model code is updated on HuggingFace Hub.

### Prompt Style Mapping

IDT prompt styles map to Florence-2 tasks:

| IDT Style | Florence-2 Task | Description |
|-----------|-----------------|-------------|
| `simple` | `<CAPTION>` | Brief, one-sentence captions |
| `technical` | `<DETAILED_CAPTION>` | Technical, factual descriptions |
| `detailed` | `<MORE_DETAILED_CAPTION>` | Comprehensive narratives |
| `narrative` | `<MORE_DETAILED_CAPTION>` | Comprehensive narratives |

### Device Detection

The provider automatically selects the best available device:
1. **CUDA** (NVIDIA GPU) if available
2. **CPU** as fallback

Phase 2 will add:
3. **NPU** (Copilot+ PC) via DirectML

## Troubleshooting

### "Florence-2 dependencies not installed"

Install missing dependencies:
```bash
pip install 'transformers>=4.45.0' torch torchvision einops timm
```

### "Model download failed"

Check internet connection. Models download from HuggingFace Hub (~230-700MB).

### "Out of memory"

- Use `Florence-2-base` instead of `large`
- Close other applications
- Ensure 4GB+ RAM available

### Slow generation

This is normal on CPU (5-10 seconds per image). Phase 2 will add NPU acceleration for 10-20x speedup.

## Limitations

### Current (Phase 1)

- ✅ CPU only (no GPU/NPU acceleration yet)
- ✅ No custom prompts (uses fixed Florence-2 tasks)
- ✅ Slower than cloud APIs (but free and private)
- ✅ Requires ~4GB RAM

### Planned (Phase 2)

- 🔄 NPU acceleration via DirectML
- 🔄 Hardware detection and automatic switching
- 🔄 Performance benchmarking
- 🔄 UI indicators for hardware status

## Support

- **Issues**: Report on GitHub: https://github.com/kellylford/Image-Description-Toolkit/issues
- **Documentation**: See `docs/` directory
- **Model Info**: https://huggingface.co/microsoft/Florence-2-base

## Version History

- **v3.6.0** (2025-12-04): Renamed from ONNX to HuggingFace provider
  - Provider renamed to accurately reflect HuggingFace transformers usage
  - All references updated across codebase (CLI, GUI, documentation)
  - Florence-2 models now correctly identified as HuggingFace models
  - Python 3.13 compatible
  - Three detail levels
  - Base and large models

---

**Next**: Phase 2 will add NPU acceleration for Copilot+ PCs with 10-20x performance improvement.
