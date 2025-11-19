# HuggingFace Provider Guide

The HuggingFace provider enables IDT to use vision-language models from the HuggingFace Hub, including Qwen2-VL and LLaVA-OneVision families.

## Quick Start

```bash
# Install dependencies
pip install 'transformers>=4.45.0' torch torchvision pillow

# Test provider (should show 4 available models)
python test_hf_provider.py

# Use with IDT workflow
idt workflow --provider huggingface --model "Qwen/Qwen2-VL-2B-Instruct"
```

## Supported Model Families

The provider automatically detects model family from the model ID and applies appropriate formatting:

### Qwen2-VL Family
- **Models**: `Qwen/Qwen2-VL-2B-Instruct`, `Qwen/Qwen2-VL-7B-Instruct`
- **Format**: Chat template with structured image/text content
- **Detection**: Model ID contains "qwen2-vl"
- **Best for**: Detailed descriptions, technical analysis

**Example**:
```python
messages = [{"role": "user", "content": [
    {"type": "image", "image": <PIL.Image>},
    {"type": "text", "text": "Describe this image in detail"}
]}]
```

### LLaVA Family  
- **Models**: `lmms-lab/llava-onevision-qwen2-0.5b-ov`, `lmms-lab/llava-onevision-qwen2-7b-ov`
- **Format**: Simple `<image>\n{prompt}` format
- **Detection**: Model ID contains "llava"
- **Best for**: Fast inference, narrative descriptions

**Example**:
```python
text = "<image>\nDescribe this image in detail"
```

### Generic Fallback
- **Models**: Any other HuggingFace vision-language model
- **Format**: Basic processor(text, images) call
- **Detection**: Default for unknown model types
- **Note**: May require manual testing for compatibility

## Available Models

### Recommended Models

| Model | Size | RAM | Speed | Quality | Use Case |
|-------|------|-----|-------|---------|----------|
| Qwen/Qwen2-VL-2B-Instruct | ~4GB | 8GB | Fast | High | General purpose, daily use |
| Qwen/Qwen2-VL-7B-Instruct | ~15GB | 16GB | Medium | Very High | Professional work, detailed analysis |

### Additional Models

| Model | Size | RAM | Speed | Quality | Use Case |
|-------|------|-----|-------|---------|----------|
| llava-onevision-0.5b-ov | ~1GB | 4GB | Very Fast | Good | Quick previews, testing |
| llava-onevision-7b-ov | ~15GB | 16GB | Medium | Very High | LLaVA architecture preference |

## Usage Examples

### Basic Workflow
```bash
# Using recommended 2B model (best balance)
idt workflow --provider huggingface --model "Qwen/Qwen2-VL-2B-Instruct" --images ./my_images/

# Using high-quality 7B model
idt workflow --provider huggingface --model "Qwen/Qwen2-VL-7B-Instruct" --images ./my_images/

# Using fast LLaVA model
idt workflow --provider huggingface --model "lmms-lab/llava-onevision-qwen2-0.5b-ov" --images ./my_images/
```

### With Custom Prompts
```bash
# Technical descriptions
idt workflow --provider huggingface \
  --model "Qwen/Qwen2-VL-7B-Instruct" \
  --prompt "technical" \
  --images ./technical_diagrams/

# Accessibility descriptions
idt workflow --provider huggingface \
  --model "Qwen/Qwen2-VL-2B-Instruct" \
  --prompt "accessibility" \
  --images ./website_images/
```

### Using Custom Model IDs
The provider supports any HuggingFace model ID:

```bash
# Use any compatible HF model
idt workflow --provider huggingface \
  --model "organization/custom-vision-model" \
  --images ./my_images/
```

**Note**: Custom models will use generic fallback formatting. Test compatibility first.

## Configuration

### Generation Parameters

Default settings in `HuggingFaceProvider`:
```python
max_new_tokens = 512      # Response length limit
temperature = 0.0         # Deterministic output (vs creative)
do_sample = False         # Greedy decoding (vs sampling)
```

To customize, modify `imagedescriber/ai_providers.py` lines ~1010-1020.

### Device Selection

Auto-detected based on availability:
- **CUDA available**: Uses GPU with float16 precision
- **CPU only**: Uses CPU with float32 precision

To force CPU mode:
```python
# In ai_providers.py HuggingFaceProvider.__init__()
self.device = torch.device("cpu")  # Add this line
self.dtype = torch.float32
```

## Troubleshooting

### "Provider unavailable" Error

**Cause**: transformers package not installed

**Solution**:
```bash
pip install 'transformers>=4.45.0' torch torchvision pillow

# Verify installation
python test_hf_provider.py
```

### Out of Memory (OOM) Errors

**Symptoms**: Process killed, CUDA out of memory

**Solutions**:
1. Use smaller model (0.5B or 2B instead of 7B)
2. Reduce batch size (process images one at a time)
3. Enable CPU offloading in code
4. Add more system RAM or use CUDA GPU

### Model Download Slow

**Cause**: Models are 1-15GB, first use downloads from HuggingFace

**Solutions**:
1. Pre-download: `huggingface-cli download Qwen/Qwen2-VL-2B-Instruct`
2. Use local cache: Models save to `~/.cache/huggingface/hub`
3. Use smaller model for testing (0.5B is ~1GB)

### Inference Very Slow

**Causes**:
- Running on CPU instead of GPU
- Using float32 instead of float16
- Model too large for hardware

**Solutions**:
1. Install CUDA-enabled PyTorch: `pip install torch --index-url https://download.pytorch.org/whl/cu118`
2. Use smaller model (2B instead of 7B)
3. Check device: Run test script to see if CUDA detected

## Performance Comparison

Approximate speeds on RTX 3090 (24GB VRAM):

| Model | Size | Images/min | Quality | Notes |
|-------|------|------------|---------|-------|
| llava-0.5b-ov | 1GB | ~40 | Good | Fastest, basic descriptions |
| Qwen2-VL-2B | 4GB | ~15 | High | Best balance |
| Qwen2-VL-7B | 15GB | ~8 | Very High | Professional quality |
| llava-7b-ov | 15GB | ~10 | Very High | Alternative to Qwen2-VL |

CPU performance (32 core Xeon):
- 0.5B: ~2-3 images/min
- 2B: ~0.5-1 images/min  
- 7B: ~0.1-0.2 images/min

## Architecture Details

### Model Family Detection
```python
def _detect_model_family(self, model_id: str) -> str:
    model_lower = model_id.lower()
    if 'qwen2-vl' in model_lower or 'qwen/qwen2-vl' in model_lower:
        return 'qwen2-vl'
    elif 'llava' in model_lower:
        return 'llava'
    else:
        return 'unknown'
```

Detection happens at model load time (once per session).

### Input Preparation Pipeline

1. **Load image**: PIL.Image.open()
2. **Detect family**: Check model ID string
3. **Prepare inputs**: Family-specific method
   - Qwen2-VL: `apply_chat_template()` with structured content
   - LLaVA: Simple text concatenation
   - Generic: Basic processor call
4. **Generate**: Model inference with fixed parameters
5. **Clean output**: Extract assistant response from generation

### Output Cleaning

Removes:
- System/user prefixes from chat format
- Extra whitespace and newlines
- Model-specific formatting artifacts

Example:
```
Raw: "user: describe this\nassistant: A photo of a sunset over mountains."
Cleaned: "A photo of a sunset over mountains."
```

## Comparison with ONNX Provider

| Feature | HuggingFace Provider | ONNX Provider |
|---------|---------------------|---------------|
| **Models** | Any HF vision model | Florence-2 only |
| **Format** | Family-specific prompts | Task tokens (`<CAPTION>`) |
| **Customization** | Full prompt control | Fixed tasks |
| **Performance** | GPU/CPU, float16/32 | Optimized ONNX runtime |
| **Size** | 1-15GB models | ~250MB model |
| **Quality** | Varies by model | Good (Florence-2) |
| **Best for** | Flexibility, quality | Speed, consistency |

**When to use HuggingFace**:
- Need detailed, customized descriptions
- Want to try different model architectures
- Have GPU available for acceleration
- Require specific prompt styles

**When to use ONNX (Florence-2)**:
- Need fast, consistent results
- Limited RAM/disk space
- CPU-only environment
- Standard captions sufficient

## Adding Custom Models

To add a new HuggingFace model to the registry:

1. **Edit `models/manage_models.py`**:
```python
MODEL_METADATA = {
    # ... existing models ...
    "organization/model-name": {
        "provider": "huggingface",
        "description": "Brief description of model capabilities",
        "size": "~XGB",
        "recommended": True,  # or False
        "min_ram": "XGB",
        "tags": ["vision", "local", "multimodal"]
    }
}
```

2. **Test the model**:
```bash
python test_hf_provider.py  # Should show in registry
idt workflow --provider huggingface --model "organization/model-name" --images test_data/
```

3. **Document behavior**: Note which family it uses (check logs during first run)

## Technical Specifications

### System Requirements

**Minimum** (0.5B model):
- CPU: 4+ cores
- RAM: 4GB
- Disk: 5GB free
- OS: Windows/Linux/macOS

**Recommended** (2B model):
- CPU: 8+ cores or CUDA GPU
- RAM: 8-16GB (CPU) or 8GB VRAM (GPU)
- Disk: 10GB free
- OS: Linux/Windows with CUDA

**Professional** (7B model):
- GPU: NVIDIA with 16GB+ VRAM
- RAM: 16GB system RAM
- Disk: 25GB free
- OS: Linux preferred

### Dependencies

```txt
transformers>=4.45.0  # Model loading and inference
torch>=2.0.0          # Neural network runtime
torchvision>=0.15.0   # Image preprocessing
pillow>=10.0.0        # Image loading
```

**Optional**:
- `accelerate` - Multi-GPU and offloading support
- `bitsandbytes` - 8-bit/4-bit quantization for lower VRAM

## FAQ

**Q: Can I use quantized models (4-bit, 8-bit)?**  
A: Yes, but requires code modifications. Add `load_in_4bit=True` to `from_pretrained()` call and install `bitsandbytes`.

**Q: How do I use my own fine-tuned model?**  
A: Upload to HuggingFace Hub or use local path: `--model "/path/to/local/model"`

**Q: Does this work offline?**  
A: Yes, after first download. Models cache to `~/.cache/huggingface/hub`

**Q: Can I batch process images?**  
A: Currently processes one image at a time. Batching would require code changes.

**Q: Which model is fastest?**  
A: `llava-onevision-0.5b-ov` (~40 images/min on GPU)

**Q: Which model is most accurate?**  
A: `Qwen2-VL-7B-Instruct` for general use, but depends on your specific task.

## Related Documentation

- [Main README](../README.md) - General IDT usage
- [AI_AGENT_REFERENCE](./archive/AI_AGENT_REFERENCE.md) - Complete technical reference  
- [ONNX Provider](./ONNX_PROVIDER.md) - Alternative provider (Florence-2)
- [Workflow Guide](./WORKFLOW_GUIDE.md) - Complete workflow documentation

## Support

**Issues**: https://github.com/yourusername/Image-Description-Toolkit/issues  
**Discussions**: Use GitHub Discussions for questions about model selection

**Created**: 2025-01-18  
**Version**: IDT 4.0.0+  
**Status**: Production ready
