# Models Directory Quick Reference

**Location:** `models/`

## Model Installation & Management Scripts

### 🔧 Installation Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `install_groundingdino.bat` | Install GroundingDINO for text-prompted object detection | `models\install_groundingdino.bat` |
| `download_onnx_models.bat` | Download ONNX models for hardware acceleration | `models\download_onnx_models.bat` |
| `download_florence2.py` | Download Florence-2 vision models | `python -m models.download_florence2` |

### 📊 Status Checking

| Script | Purpose | Usage |
|--------|---------|-------|
| `check_models.py` | Comprehensive model & provider status checker | `python -m models.check_models` |
| `checkmodels.bat` | Convenient wrapper for check_models.py | `models\checkmodels.bat` |

## Quick Commands

### Check All Providers
```bash
python -m models.check_models
# or
models\checkmodels.bat
```

### Check Specific Provider
```bash
python -m models.check_models --provider groundingdino
python -m models.check_models --provider ollama
python -m models.check_models --provider onnx
```

### Detailed Information
```bash
python -m models.check_models --verbose
```

### JSON Output (for scripting)
```bash
python -m models.check_models --json
```

## Supported Providers

The check_models.py script now checks:

1. **Ollama** (Local Models) - Local AI models for image descriptions
2. **Ollama Cloud** - Cloud-based Ollama models
3. **OpenAI** - GPT-4 Vision and other OpenAI models
4. **HuggingFace** - Transformers-based vision models (BLIP, ViT-GPT2, GIT)
5. **ONNX / Enhanced YOLO** - Hardware-accelerated models
6. **Copilot+ PC (NPU)** - NPU-accelerated models on Copilot+ PCs
7. **GroundingDINO** ⭐ - Text-prompted object detection (NEW!)

The manage_models.py script can install and manage:

1. **Ollama** - Pull/remove local vision models
2. **OpenAI** - Configure API keys
3. **HuggingFace** ⭐ - Install transformers, manage model cache (NEW!)
4. **YOLO** ⭐ - Install ultralytics package (NEW!)
5. **GroundingDINO** ⭐ - Run installation script (NEW!)

## Install Any Provider

### Ollama
```bash
# Download from https://ollama.ai
ollama pull llava:7b
# or use manage_models
python -m models.manage_models install llava:7b
```

### HuggingFace
```bash
# Install transformers package (models download on first use)
python -m models.manage_models install "Salesforce/blip-image-captioning-base"
# or manually
pip install transformers torch pillow
```

### GroundingDINO
```bash
# Using manage_models
python -m models.manage_models install groundingdino
# or directly
models\install_groundingdino.bat
```

### YOLO
```bash
# Using manage_models
python -m models.manage_models install yolo
# or manually
pip install ultralytics
```

### ONNX Models
```bash
models\download_onnx_models.bat
```

### OpenAI
```bash
# Create openai.txt with your API key
# or set OPENAI_API_KEY environment variable
```

## Python Module Structure

```
models/
├── __init__.py                  # Package initialization
├── check_models.py             # Status checker (all providers)
├── checkmodels.bat             # Wrapper script
├── model_registry.py           # Model metadata registry
├── provider_configs.py         # Provider capabilities
├── copilot_npu.py             # Copilot+ PC NPU support
├── download_florence2.py       # Florence-2 downloader
├── download_onnx_models.bat    # ONNX models downloader
├── install_groundingdino.bat   # GroundingDINO installer
└── manage_models.py           # Model management utilities
```

## From Python Code

```python
# Check model availability
from models.model_registry import is_model_installed
if is_model_installed("llava:7b"):
    print("Model is ready!")

# Get provider capabilities
from models.provider_configs import PROVIDER_CAPABILITIES
capabilities = PROVIDER_CAPABILITIES.get("ollama")

# Check GroundingDINO status programmatically
import subprocess
result = subprocess.run(
    ["python", "-m", "models.check_models", "--provider", "groundingdino", "--json"],
    capture_output=True, text=True
)
status = json.loads(result.stdout)
```

## Output Example

```
=== Image Description Toolkit - Model Status ===

Ollama (Local Models)
  [OK] Status: OK
  Models: 3 available
    • llava:7b
    • moondream
    • llama3.2-vision

GroundingDINO (Object Detection)
  [OK] Status: Fully configured
  Models: 1 available
    • GroundingDINO (Object Detection)

ONNX / Enhanced YOLO
  [OK] Status: OK
  Models: 1 available
    • Enhanced Ollama + YOLO (uses Ollama models)

=== Recommendations ===
  • [OK] Ollama is ready with 3 models
```

## See Also

- [MODEL_MANAGEMENT_REORGANIZATION.md](MODEL_MANAGEMENT_REORGANIZATION.md) - Details of the reorganization
- [GROUNDINGDINO_GUIDE.md](../docs/GROUNDINGDINO_GUIDE.md) - GroundingDINO usage guide
- [ONNX_GUIDE.md](../docs/ONNX_GUIDE.md) - ONNX provider guide
- [MODEL_SELECTION_GUIDE.md](../docs/MODEL_SELECTION_GUIDE.md) - Choosing the right model
