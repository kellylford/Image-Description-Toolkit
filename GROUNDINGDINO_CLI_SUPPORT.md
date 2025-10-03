# GroundingDINO Command-Line Support - Implementation Summary

## What Was Added

GroundingDINO support has been successfully integrated into the command-line scripts (`workflow.py` and `image_describer.py`), making it available alongside other providers like Ollama, ONNX, OpenAI, etc.

## Files Modified

### 1. `scripts/image_describer.py`

**Changes:**
- Added imports for `GroundingDINOProvider` and `GroundingDINOHybridProvider`
- Added `detection_query` and `confidence` parameters to `__init__`
- Added provider initialization for:
  - `groundingdino` - Standalone detection
  - `groundingdino+ollama` - Hybrid detection + descriptions
- Added command-line arguments:
  - `--detection-query` - Text query for objects to detect
  - `--confidence` - Detection confidence threshold (1-95, default 25)

**Code:**
```python
# Import section
from imagedescriber.ai_providers import (
    OllamaProvider,
    OpenAIProvider,
    ONNXProvider,
    CopilotProvider,
    HuggingFaceProvider,
    GroundingDINOProvider,          # NEW
    GroundingDINOHybridProvider     # NEW
)

# Provider initialization
elif self.provider_name == "groundingdino":
    logger.info("Initializing GroundingDINO provider...")
    provider = GroundingDINOProvider()
    if not provider.is_available():
        raise RuntimeError("GroundingDINO not available. Install with: pip install groundingdino-py torch torchvision")
    return provider
    
elif self.provider_name == "groundingdino+ollama" or self.provider_name == "groundingdino_ollama":
    logger.info("Initializing GroundingDINO + Ollama hybrid provider...")
    provider = GroundingDINOHybridProvider()
    if not provider.is_available():
        raise RuntimeError("GroundingDINO hybrid not available. Ensure both GroundingDINO and Ollama are installed.")
    return provider
```

### 2. `scripts/workflow.py`

**Changes:**
- Added `groundingdino` and `groundingdino+ollama` to provider choices
- Added `detection_query` and `confidence` parameters to `WorkflowOrchestrator`
- Added command-line arguments for detection configuration
- Pass detection parameters to `image_describer.py`

**Code:**
```python
# Provider choices
parser.add_argument(
    "--provider",
    choices=["ollama", "openai", "onnx", "copilot", "huggingface", 
             "groundingdino", "groundingdino+ollama"],  # NEW
    default="ollama",
    help="AI provider to use for image description (default: ollama)"
)

# New arguments
parser.add_argument(
    "--detection-query",
    help="Detection query for GroundingDINO (separate items with ' . ')"
)

parser.add_argument(
    "--confidence",
    type=float,
    default=25.0,
    help="Confidence threshold for GroundingDINO detection (1-95, default: 25)"
)
```

### 3. `run_groundingdino.bat`

**Updated** to use the command-line workflow instead of GUI-only instructions.

**Key Configuration:**
```batch
set IMAGE_PATH=C:\path\to\your\image.jpg
set DETECTION_QUERY=objects . people . vehicles . furniture . animals . text
set CONFIDENCE=25
set PROVIDER=groundingdino
```

## Usage Examples

### Standalone GroundingDINO Detection

```bash
# Basic usage
python scripts/workflow.py images/ --steps describe --provider groundingdino --detection-query "cars . trucks . motorcycles"

# With custom confidence
python scripts/workflow.py images/ --steps describe --provider groundingdino --detection-query "people . safety equipment" --confidence 30

# Safety inspection example
python scripts/workflow.py inspection_photos/ \
    --steps describe,html \
    --provider groundingdino \
    --detection-query "fire extinguisher . exit signs . safety vests . hazards" \
    --confidence 25
```

### Hybrid Mode (GroundingDINO + Ollama)

```bash
# Detection + rich descriptions
python scripts/workflow.py images/ \
    --steps describe,html \
    --provider groundingdino+ollama \
    --model moondream \
    --detection-query "vehicles . people . signs" \
    --confidence 25

# Detailed analysis
python scripts/workflow.py photos/ \
    --steps describe,html \
    --provider groundingdino+ollama \
    --model llava \
    --detection-query "damaged items . defects . missing parts" \
    --confidence 30 \
    --prompt-style narrative
```

### Using image_describer.py Directly

```bash
# Standalone detection
python scripts/image_describer.py images/ \
    --provider groundingdino \
    --detection-query "people . vehicles . buildings" \
    --confidence 25

# Hybrid mode
python scripts/image_describer.py images/ \
    --provider groundingdino+ollama \
    --model moondream \
    --detection-query "objects . text . signs" \
    --confidence 25
```

### Using Batch File

```batch
# Edit run_groundingdino.bat
set IMAGE_PATH=C:\Photos\Inspection
set DETECTION_QUERY=fire extinguisher . exit signs . safety equipment
set CONFIDENCE=25

# Run it
run_groundingdino.bat
```

## Detection Query Syntax

Detection queries use ` . ` (space-period-space) as separator:

**Examples:**
```
# General detection
"objects . people . vehicles . furniture . animals . text"

# Specific colors/attributes
"red cars . blue trucks . yellow signs"

# Safety/compliance
"people wearing helmets . safety vests . hard hats . fire extinguisher"

# Damage assessment
"damaged items . broken parts . cracks . dents . missing components"

# Retail/inventory
"products . shelves . empty spaces . price tags . barcodes"
```

## Confidence Threshold

| Value | Behavior | Use Case |
|-------|----------|----------|
| 10-15% | Very permissive | Exploratory analysis, catch everything |
| 20-30% | **Balanced (recommended)** | General purpose |
| 35-50% | Strict | Precision-critical applications |
| 50%+ | Very strict | High-confidence only |

## Provider Options

| Provider | Description | Use Case |
|----------|-------------|----------|
| `groundingdino` | Standalone object detection | Pure detection, bounding boxes, counts |
| `groundingdino+ollama` | Hybrid: detection + description | Comprehensive analysis with both |

## Workflow Integration

### Sequential Workflow

```bash
# Step 1: Extract frames from video
python scripts/workflow.py video.mp4 --steps video

# Step 2: Detect objects
python scripts/workflow.py video.mp4 --steps describe --provider groundingdino --detection-query "people . vehicles"

# Step 3: Add descriptions with premium model
python scripts/workflow.py video.mp4 --steps describe,html --provider openai --model gpt-4o
```

### Combined Workflow

```bash
# Video → Frames → Detection → Descriptions → HTML Report
python scripts/workflow.py training_video.mp4 \
    --steps video,describe,html \
    --provider groundingdino+ollama \
    --model llava \
    --detection-query "people . equipment . text . diagrams" \
    --confidence 25
```

## Requirements

### Installation

```bash
# Install GroundingDINO
pip install groundingdino-py torch torchvision

# For hybrid mode, also install Ollama
# Download from: https://ollama.ai
ollama pull moondream
```

### First Use

- Model downloads automatically (~700MB)
- Cached at: `C:\Users\<You>\.cache\torch\hub\checkpoints\`
- After first download: works offline

## Batch File Workflows

The workflow batch files have also been updated:

### `run_groundingdino_workflow.bat`

Supports two modes:
- **HYBRID**: Integrated detection + descriptions
- **SEQUENTIAL**: Detection first, then descriptions separately

```batch
# Edit the batch file
set WORKFLOW_MODE=HYBRID
set INPUT_PATH=C:\Photos\Inspection
set DETECTION_QUERY=safety equipment . hazards . violations
set DESCRIPTION_MODEL=llava

# Run it
run_groundingdino_workflow.bat
```

## Testing

```bash
# Test standalone detection
python scripts/workflow.py tests/test_files/images/ \
    --steps describe \
    --provider groundingdino \
    --detection-query "objects . nature . buildings" \
    --confidence 25

# Test hybrid mode
python scripts/workflow.py tests/test_files/images/ \
    --steps describe,html \
    --provider groundingdino+ollama \
    --model moondream \
    --detection-query "landscape . sky . water" \
    --confidence 25
```

## Comparison with Other Providers

| Feature | GroundingDINO | YOLO | VLMs (Ollama/GPT) |
|---------|---------------|------|-------------------|
| **Detection** | ✅ Text-prompted | ✅ 80 classes only | ❌ No bounding boxes |
| **Custom Objects** | ✅ Any description | ❌ Requires training | ✅ Describes anything |
| **Localization** | ✅ Precise boxes | ✅ Precise boxes | ❌ General description |
| **Cost** | Free (local) | Free (local) | Free (Ollama) / Paid (GPT) |
| **Best For** | Finding specific objects | Speed, standard objects | Scene understanding |

## Troubleshooting

### "GroundingDINO not available"

**Solution:**
```bash
pip install groundingdino-py torch torchvision
```

### "Invalid provider: groundingdino"

**Check:**
- Are you using the updated `scripts/workflow.py`?
- Try: `python scripts/workflow.py --help` and look for groundingdino in providers

### No detections found

**Try:**
- Lower confidence: `--confidence 15`
- Broader query: `"objects . items . things"`
- Check if query matches image content

### Hybrid mode fails

**Check:**
- Is Ollama installed and running?
- Is model pulled? `ollama pull moondream`
- Try standalone mode first to isolate issue

## Next Steps

1. **Test the integration:**
   ```bash
   run_groundingdino.bat
   ```

2. **Try hybrid mode:**
   ```bash
   run_groundingdino_workflow.bat
   ```

3. **Read full documentation:**
   - `docs/GROUNDINGDINO_GUIDE.md`
   - `docs/WORKFLOW_EXAMPLES.md`

4. **Experiment with queries:**
   - Try different detection queries
   - Adjust confidence thresholds
   - Compare standalone vs hybrid modes

## Summary

✅ **GroundingDINO is now fully integrated** into the command-line scripts  
✅ **Works like other providers** (ollama, onnx, openai, etc.)  
✅ **Supports both standalone and hybrid modes**  
✅ **Batch files updated and ready to use**  
✅ **Compatible with all workflow steps** (video, convert, describe, html)  

**Key Advantage:** Text-prompted detection of ANY object without training, now accessible via command-line for scripting and automation!
