# Copilot+ PC NPU Setup Guide

## 🎯 Your Hardware Status

**✅ DirectML NPU Detected and Ready!**

Your system has:
- Windows 11 ✅
- DirectML support ✅
- ONNX Runtime installed ✅
- Copilot+ PC NPU hardware detected ✅

## 📥 Download Florence-2 ONNX Model

Florence-2 is Microsoft's vision-language model optimized for NPU acceleration.

### Option 1: Manual Download (Recommended for now)

Since automated ONNX export requires additional setup, here's the manual approach:

1. **Visit HuggingFace Model Hub:**
   ```
   https://huggingface.co/microsoft/Florence-2-base
   ```

2. **Download Pre-exported ONNX (if available):**
   - Look for `model.onnx` or ONNX-related files
   - Download to `models/onnx/florence2/`

3. **Or Use PyTorch Version (Fallback):**
   ```bash
   pip install transformers torch
   python -c "from transformers import AutoModelForCausalLM; model = AutoModelForCausalLM.from_pretrained('microsoft/Florence-2-base', trust_remote_code=True); print('Downloaded!')"
   ```

### Option 2: Export to ONNX Yourself

If you want to export Florence-2 to ONNX for optimal NPU performance:

```bash
# Install export tools
pip install optimum onnx onnxruntime-directml

# Export Florence-2 to ONNX
python -m optimum.exporters.onnx --model microsoft/Florence-2-base --task image-to-text models/onnx/florence2/
```

**Note:** ONNX export can be complex for vision-language models. Microsoft may release official ONNX versions in the future.

## 🚀 Quick Test (Without Florence-2 Download)

You can test NPU detection now:

```bash
python -c "from models.copilot_npu import get_setup_instructions; print(get_setup_instructions())"
```

Expected output:
```
✅ Windows detected
✅ onnxruntime installed
✅ DirectML available
✅ transformers installed
✅ Pillow installed

✅ All requirements met! NPU acceleration ready.
```

## 🎨 Using Copilot+ PC in the GUI

Once Florence-2 is downloaded:

1. Launch Image Describer:
   ```bash
   python imagedescriber/imagedescriber.py
   ```

2. Select Provider:
   - Choose "Copilot+ PC (DirectML available)"

3. Select Model:
   - Choose "florence2-base"

4. Process Images:
   - NPU acceleration happens automatically!

## ⚡ Performance Expectations

With NPU acceleration:
- **Speed:** 2-5x faster than CPU
- **Power:** 50% less power consumption
- **Quality:** Same quality as CPU/GPU inference
- **Memory:** Lower memory usage

## 🔧 Troubleshooting

### "florence2-base (not downloaded)" in model list

**Solution:** Download Florence-2 ONNX model to `models/onnx/florence2/model.onnx`

### "DirectML not available"

**Possible causes:**
1. Not running Windows 11
2. Copilot+ PC hardware not present
3. onnxruntime-directml not installed

**Solution:**
```bash
pip install onnxruntime-directml
```

### Model runs but very slow

**Possible cause:** Falling back to CPU instead of NPU

**Solution:** Ensure:
1. DirectML provider is first in provider list
2. Model is in ONNX format (not PyTorch)
3. No conflicting GPU drivers

## 📊 Verify NPU Usage

To confirm NPU is being used:

1. Open Task Manager
2. Go to Performance tab
3. Look for NPU/DirectML activity during inference

Or use Windows AI DevKit:
```powershell
# Check DirectML device
dxdiag /t dxdiag_output.txt
# Look for DirectX 12 and NPU references
```

## 🔄 Alternative: Use Other Providers While Setting Up NPU

While setting up Florence-2, you can use:

- **Ollama** (free, local) - Already configured with 11 models
- **OpenAI** (cloud, API key required)
- **ONNX** (local, existing ONNX models)

These will work immediately while you download Florence-2 for NPU.

## 📚 Additional Resources

- **Florence-2 Paper:** https://arxiv.org/abs/2311.06242
- **DirectML Docs:** https://learn.microsoft.com/en-us/windows/ai/directml/
- **ONNX Runtime:** https://onnxruntime.ai/docs/execution-providers/DirectML-ExecutionProvider.html

## ✨ Future Improvements

Planned enhancements:
- Automated Florence-2 ONNX download
- Phi-3 Vision support
- Model quantization for faster NPU inference
- Batch processing optimization

---

**Status:** Your NPU is detected and ready. Download Florence-2 ONNX to unlock full NPU acceleration!
