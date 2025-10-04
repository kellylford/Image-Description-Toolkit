# BLIP Quickstart for Copilot+ PC Users

## 1. Install ONNX Runtime DirectML (Python 3.13)
```bash
pip install onnxruntime-directml
```

## 2. Convert BLIP to ONNX (One-time, Python 3.11)
```bash
# Create Python 3.11 environment
py -3.11 -m venv .venv311
.venv311\Scripts\activate
pip install optimum[exporters] transformers torch
python models/convert_blip_to_onnx.py
```
- The ONNX model will be saved to `models/onnx/blip/`
- After conversion, return to your main environment:
```bash
deactivate
.venv\Scripts\activate
```

## 3. Run Image Describer
```bash
python imagedescriber/imagedescriber.py
```
- Select "Copilot+ PC" provider
- Choose "BLIP-base NPU (Fast Captions)" or "BLIP-base NPU (Detailed Mode)"
- Process images for fast NPU-accelerated captions

## Troubleshooting
- If no BLIP model choices appear, ensure ONNX model exists at `models/onnx/blip/model.onnx`
- If you see errors, check that DirectML is installed and you are using Python 3.13 for runtime
- For conversion, always use Python 3.11 (transformers not supported on 3.13)

## For Other Users
- All steps above are documented in `docs/COPILOT_NPU_BLIP_SOLUTION.md`
- No instructional/setup text will appear in the model dropdowns
- Only actual model choices are shown

---

_Last updated: October 4, 2025_
