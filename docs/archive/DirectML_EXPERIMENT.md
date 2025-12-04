# DirectML NPU Experiment - Quick Start

## What This Does
Tests Florence-2 with NPU/GPU acceleration using ONNX Runtime DirectML to see if we get the speed improvement (40s → <1s).

## Installation (One-Time)

```bash
# Install ONNX Runtime with DirectML support
pip install onnxruntime-directml

# Install HuggingFace Optimum for automatic ONNX conversion
pip install optimum

# Already installed in your .venv:
# - transformers, pillow, torch, torchvision
```

## Run the Test

```bash
# Test with a single image
python test_directml_experiment.py testimages/blue_circle.jpg

# Or just run without arguments (uses blue_circle.jpg by default)
python test_directml_experiment.py
```

## What to Expect

**First Run**:
- Takes 1-2 minutes to export Florence-2 to ONNX format
- Cached after that (subsequent runs are instant)
- May fail if Florence-2 custom code isn't ONNX-compatible

**If It Works**:
- You'll see "DmlExecutionProvider" as available provider
- Generation should be <1 second per image (instead of 40 seconds)
- Quality should be identical to CPU version

**If It Doesn't Work**:
- Florence-2 might not support automatic ONNX export via optimum
- The custom model code with `trust_remote_code=True` may not be compatible
- Would need manual ONNX conversion (much more complex)

## Alternative Approach

If optimum export doesn't work, we could:
1. Use a different model that has pre-converted ONNX versions (BLIP-2, etc.)
2. Manually convert Florence-2 to ONNX (complex)
3. Wait for torch-directml Python 3.13 support (easiest long-term)

## Notes

- This is **experimental** - testing if quick ONNX conversion works
- Does NOT modify your main codebase
- Safe to try - worst case it fails and we learn Florence-2 needs manual conversion
- If successful, we can integrate this approach into ONNXProvider

## Expected Output

```
======================================================================
Florence-2 DirectML NPU Acceleration Test
======================================================================
✓ onnxruntime version: 1.23.0
✓ optimum and transformers installed

Image: testimages/blue_circle.jpg
----------------------------------------------------------------------

Available ONNX Runtime providers: ['DmlExecutionProvider', 'CPUExecutionProvider']
✓ DirectML provider available - NPU/GPU acceleration ready!

Using provider: DmlExecutionProvider
----------------------------------------------------------------------

1. Loading Florence-2 model...
   (First run will export to ONNX - takes 1-2 minutes)
   ✓ Model loaded in 95.32 seconds

2. Loading image...
   ✓ Image loaded: (500, 500)

3. Generating descriptions...
======================================================================

Simple Description (<CAPTION>):
----------------------------------------------------------------------
Time: 0.15 seconds  ← This is what we're hoping for!
Description: a blue circle

[... more descriptions ...]
```

Compare to current CPU performance: ~40 seconds per image
