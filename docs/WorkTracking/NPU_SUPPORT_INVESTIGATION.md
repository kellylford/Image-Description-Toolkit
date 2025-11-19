# NPU Support Investigation
**Date**: 2025-11-19  
**Platform**: Windows ARM64 (Qualcomm, Copilot+ PC)  
**Goal**: Enable NPU acceleration for vision models

## Findings

### DirectML is Available ✅
- **Package**: `onnxruntime-directml` (installed successfully)
- **Provider**: `DmlExecutionProvider` available
- **Status**: Ready to use for ONNX models
- **Platform**: Works on ARM64 Windows

### PyTorch DirectML is NOT Available ❌
- **Package**: `torch-directml` (not available for ARM64)
- **Issue**: Only built for x64 Windows
- **Impact**: Can't use DirectML directly with PyTorch models

## NPU Support Paths

### Path 1: ONNX Runtime + DirectML (WORKING)
**Requirements**:
```bash
pip install onnxruntime-directml  # ✅ Installed
```

**Process**:
1. Export HuggingFace model to ONNX format using Optimum
2. Load ONNX model with `DmlExecutionProvider`
3. DirectML routes computation to NPU

**Status**: ✅ Infrastructure ready, but...

### Path 2: Qwen2-VL ONNX Export (BLOCKED)
**Issue**: Qwen2-VL is too new for Optimum ONNX export

**Error**:
```
ValueError: Trying to export a qwen2_vl model, that is a custom or 
unsupported architecture
```

**Reason**: Qwen2-VL released in 2024, Optimum doesn't have export config yet

**Options**:
1. Wait for Optimum to add Qwen2-VL support
2. Write custom ONNX export configuration (complex)
3. Try with older/different vision models that Optimum supports

### Path 3: Florence-2 Models (BEST CURRENT OPTION)
Florence-2 models in ONNX provider could potentially use DirectML, but current implementation uses PyTorch backend which doesn't support DirectML on ARM64.

**To enable**:
1. Export Florence-2 to ONNX format (if Optimum supports it)
2. Use `onnxruntime-directml` instead of PyTorch
3. Modify ONNXProvider to use actual ONNX Runtime sessions

## Supported Model Architectures in Optimum
Optimum currently supports 33 model architectures for ONNX export, but **qwen2_vl is not one of them**.

Common vision models that MAY be supported:
- CLIP variants
- ViT (Vision Transformer)
- BERT-like models
- Some older multimodal models

**Action needed**: Check which vision-language models Optimum can export.

## Recommendations

### Short Term
- Keep HuggingFace provider as CPU-only for now
- ONNX provider already works (even if on CPU)
- Document NPU limitation

### Medium Term  
- Monitor Optimum releases for Qwen2-VL support
- Test Florence-2 ONNX export when available
- Consider adding older vision models that Optimum supports

### Long Term
- Write custom ONNX export config for Qwen2-VL
- Contribute back to Optimum project
- Explore alternative NPU runtimes (QNN SDK for Qualcomm?)

## Technical Details

### Working Components
```python
import onnxruntime as ort

# ✅ This works
providers = ort.get_available_providers()
# Returns: ['DmlExecutionProvider', 'CPUExecutionProvider']

# ✅ Can create sessions with DirectML
session = ort.InferenceSession(
    model_path,
    providers=['DmlExecutionProvider', 'CPUExecutionProvider']
)
```

### Blocked Components
```python
# ❌ This doesn't work on ARM64
import torch_directml
device = torch_directml.device()  # Not available

# ❌ This doesn't work for Qwen2-VL
from optimum.exporters.onnx import main_export
main_export(model="Qwen/Qwen2-VL-2B-Instruct")  # Unsupported architecture
```

## Next Steps

1. ✅ Installed `onnxruntime-directml` 
2. ✅ Confirmed DirectML provider available
3. ❌ Cannot export Qwen2-VL to ONNX (blocked by Optimum)
4. ⏳ Need to either:
   - Wait for Optimum support
   - Try different models
   - Write custom export config

## Conclusion

**NPU support is technically possible** but blocked by model compatibility:
- DirectML infrastructure: ✅ Ready
- ONNX Runtime: ✅ Working
- Model export: ❌ Qwen2-VL not supported
- PyTorch DirectML: ❌ Not available on ARM64

The hardware and runtime are ready, but we need models that Optimum can export to ONNX format.
