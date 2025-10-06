# Copilot+ PC Provider - Setup Guide

## What is the Copilot+ PC Provider?

The **Copilot+ PC provider** enables AI image description using dedicated **NPU (Neural Processing Unit)** hardware acceleration on Copilot+ PC devices. This provides ultra-fast AI processing using specialized hardware instead of CPU/GPU.

## Current Status

**Status:** ⚠️ **Partially Implemented - Requires Copilot+ PC Hardware**

The provider is implemented in the codebase but requires:
1. **Copilot+ PC hardware** with dedicated NPU chip
2. **Windows 11** operating system
3. **Windows Runtime (WinRT)** Python libraries

## Requirements

### Hardware Requirements

**You MUST have a Copilot+ PC to use this provider:**

Copilot+ PCs are specific devices with dedicated NPU chips from:
- **Qualcomm Snapdragon X Elite/Plus** (ARM-based)
- **Intel Core Ultra (Series 2)** processors with NPU
- **AMD Ryzen AI** processors with NPU

**Common Copilot+ PC Devices:**
- Microsoft Surface Laptop (7th Edition, Snapdragon)
- Microsoft Surface Pro (11th Edition, Snapdragon)
- Dell XPS 13 (9345, Snapdragon)
- HP EliteBook Ultra G1q
- Lenovo ThinkPad T14s Gen 6
- Samsung Galaxy Book4 Edge
- ASUS Vivobook S 15

### Software Requirements

1. **Windows 11** (version 24H2 or later)
   - Earlier versions may not have NPU support
   
2. **Python 3.9+** with Windows Runtime support

3. **WinRT Python Package:**
   ```bash
   pip install winrt
   ```

4. **ONNX Runtime DirectML** (for NPU acceleration):
   ```bash
   pip install onnxruntime-directml
   ```

## How to Check if You Have a Copilot+ PC

### Method 1: Check Device Specifications
1. Open **Settings** → **System** → **About**
2. Look for processor name containing:
   - "Snapdragon X Elite" or "Snapdragon X Plus"
   - "Core Ultra" with Series 2 designation
   - "Ryzen AI" designation

### Method 2: Check for Copilot Key
- Copilot+ PCs have a dedicated **Copilot key** on the keyboard
- Usually located near the spacebar or function keys

### Method 3: Run the Check Script
```bash
python check_models.py --provider copilot
```

**Expected output if you have Copilot+ PC:**
```
Copilot+ PC (NPU)
  [OK] Status: NPU available
  Models: 3 available
    • copilot-vision-small
    • copilot-vision-medium
    • copilot-caption-fast
```

**Expected output if you DON'T have Copilot+ PC:**
```
Copilot+ PC (NPU)
  [--] Status: Copilot+ PC NPU not detected (Windows 11 + NPU required)
```

## Installation Steps (For Copilot+ PC Owners)

### Step 1: Verify Windows 11
```bash
# Check Windows version
winver
```
You need **Windows 11 version 24H2** or later.

### Step 2: Install WinRT
```bash
pip install winrt
```

### Step 3: Install DirectML
```bash
pip install onnxruntime-directml
```

### Step 4: Verify NPU Detection
```bash
python check_models.py --provider copilot
```

If successful, you should see:
```
Copilot+ PC (NPU)
  [OK] Status: Copilot+ PC NPU Detected
  Models: 3 available
```

## Current Implementation Status

### ✅ What's Implemented

1. **NPU Detection**
   - Checks for Windows Runtime (WinRT)
   - Detects DirectX High Performance mode
   - Reports NPU availability

2. **Model Listing**
   - `copilot-vision-small` - Fast, lightweight
   - `copilot-vision-medium` - Balanced
   - `copilot-caption-fast` - Quick captions

3. **Provider Integration**
   - Listed in GUI dropdown
   - Appears in `check_models.py` output
   - Integrated with toolkit architecture

### ⚠️ What's NOT Yet Fully Implemented

1. **Actual NPU Model Execution**
   - Currently returns placeholder text
   - Needs ONNX models optimized for NPU
   - Requires DirectML session configuration

2. **NPU-Optimized Models**
   - No pre-trained models packaged yet
   - Would need Florence-2 or similar vision models converted to ONNX
   - Models must be optimized for DirectML execution

3. **Advanced NPU Features**
   - Real-time processing
   - Multi-model pipelines
   - NPU performance monitoring

## Why You Might Not Have Access

### Reason 1: No Copilot+ PC Hardware
**Solution:** This provider only works on specific Copilot+ PC devices with NPU chips.
- **Alternative:** Use Ollama (local), OpenAI (cloud), or ONNX (CPU/GPU) providers instead
- These work on ANY Windows/Mac/Linux machine

### Reason 2: Wrong Windows Version
**Solution:** Update to Windows 11 version 24H2 or later
```bash
# Check for updates
Settings → Windows Update → Check for updates
```

### Reason 3: Missing WinRT Package
**Solution:** Install WinRT support
```bash
pip install winrt
```

### Reason 4: NPU Drivers Not Installed
**Solution:** Update NPU drivers through Windows Update
```bash
Settings → Windows Update → Advanced options → Optional updates
```

## What to Use Instead

If you don't have a Copilot+ PC, here are your best alternatives:

### 🥇 **Best Alternative: Ollama (Local)**
```bash
# Install Ollama
# Download from: https://ollama.ai

# Install a model
ollama pull llava:7b

# Use in toolkit
python scripts/image_describer.py photos/ --model llava:7b
```

**Advantages:**
- Works on ANY computer (Windows/Mac/Linux)
- Free and private
- Good quality
- Multiple models available

### 🥈 **Cloud Alternative: OpenAI**
```bash
# Add API key to openai.txt
echo "your-api-key" > openai.txt

# Use in toolkit
python scripts/image_describer.py photos/ --model gpt-4o-mini
```

**Advantages:**
- No local hardware requirements
- Highest quality descriptions
- Fast processing

**Disadvantages:**
- Costs money per API call
- Requires internet connection

### 🥉 **GPU Alternative: ONNX with CUDA**
If you have an NVIDIA GPU:
```bash
# Install CUDA-enabled ONNX
pip install onnxruntime-gpu

# Use ONNX provider
python imagedescriber/imagedescriber.py
# Select "ONNX (CPU/GPU)" from dropdown
```

## Future Enhancements for Copilot+ PC

### Planned Features (Not Yet Implemented)

1. **Florence-2 Model Integration**
   - Download Florence-2 ONNX model
   - Configure for DirectML execution
   - Enable real NPU acceleration

2. **Phi-3 Vision Support**
   - Microsoft's lightweight vision-language model
   - Optimized for NPU execution
   - Fast local processing

3. **Real-time Processing**
   - Video frame analysis
   - Live camera feeds
   - Ultra-low latency

4. **NPU Performance Monitoring**
   - Show NPU utilization
   - Inference speed metrics
   - Power consumption data

## Technical Details

### How NPU Detection Works

```python
class CopilotProvider(AIProvider):
    def __init__(self):
        self.npu_info = "Not Available"
        self.is_npu_available = False
        
        # Try to detect NPU hardware
        if HAS_WINRT and platform.system() == "Windows":
            self._detect_npu_hardware()
    
    def _detect_npu_hardware(self):
        """Detect NPU hardware on Copilot+ PC"""
        try:
            # Check for NPU availability through Windows RT
            device_kind = LearningModelDeviceKind.DirectX_HighPerformance
            self.npu_info = "Copilot+ PC NPU Detected"
            self.is_npu_available = True
        except Exception:
            self.npu_info = "NPU Not Available"
            self.is_npu_available = False
```

### Why It Shows as Unavailable

The provider checks for:
1. **Windows OS** - Must be Windows 11
2. **WinRT Library** - Must be installed
3. **NPU Hardware** - Must have Copilot+ PC chip

If ANY of these is missing, it shows as unavailable.

## FAQ

### Q: I have Windows 11. Why doesn't it work?
**A:** You need a **Copilot+ PC** with a dedicated NPU chip. Regular Windows 11 PCs don't have this hardware.

### Q: Can I add an NPU to my existing PC?
**A:** No. NPUs are integrated into the processor chip. You need to buy a Copilot+ PC device.

### Q: Is the Copilot+ provider better than Ollama?
**A:** Potentially faster due to dedicated NPU hardware, but currently Ollama is more mature and has better model selection.

### Q: When will the Copilot+ provider be fully functional?
**A:** It requires:
- NPU-optimized ONNX models (Florence-2, Phi-3 Vision)
- DirectML session configuration
- Testing on actual Copilot+ PC hardware

This is planned for future development but requires Copilot+ PC hardware for testing.

### Q: Should I buy a Copilot+ PC just for this?
**A:** **No.** Ollama works great on any PC and is already fully functional. Only get a Copilot+ PC if you want one for other reasons.

### Q: What's the toolkit's recommendation?
**A:** Use **Ollama** for local processing - it works on any computer and is fully supported.

## Summary

| Feature | Copilot+ PC | Ollama | OpenAI |
|---------|------------|--------|--------|
| **Hardware Required** | Copilot+ PC only | Any PC | Any PC |
| **Cost** | Free (hardware expensive) | Free | Pay per use |
| **Speed** | Very Fast (NPU) | Fast (CPU/GPU) | Fast (cloud) |
| **Privacy** | Local/Private | Local/Private | Cloud/Less private |
| **Setup Difficulty** | Hard (need specific HW) | Easy | Easy |
| **Model Selection** | Limited (3 models) | Excellent (100+ models) | Good (5+ models) |
| **Current Status** | ⚠️ Partial | ✅ Full | ✅ Full |
| **Recommendation** | Wait for updates | ⭐ **Use This** | Good alternative |

## Bottom Line

**Don't worry about Copilot+ PC provider not working!**

The toolkit works great without it using:
- ✅ **Ollama** - Best option for most users
- ✅ **OpenAI** - Best for cloud processing
- ✅ **ONNX** - Best for GPU acceleration
- ✅ **HuggingFace** - Best for experimentation

The Copilot+ PC provider is a **future enhancement** for users who happen to have the specialized hardware. You're not missing out on anything critical.

---

**Related Documentation:**
- `check_models.py` - Check provider availability
- `manage_models.py` - Install Ollama models
- `docs/MODEL_MANAGEMENT_GUIDE.md` - Full model management guide
