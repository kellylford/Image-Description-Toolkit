# GroundingDINO Setup and Usage Guide

## Overview

**GroundingDINO** is a revolutionary AI model for **text-prompted zero-shot object detection**. Unlike traditional object detectors that are limited to pre-defined classes (like YOLO's 80 classes), GroundingDINO can detect **ANY object you describe in natural language**.

### Why Use GroundingDINO?

**Traditional Object Detectors:**
- ❌ Limited to ~80 pre-trained classes (person, car, dog, etc.)
- ❌ Can't detect custom objects without retraining
- ❌ No flexibility for specific use cases

**GroundingDINO:**
- ✅ Detects ANY object you describe ("red sports car", "person wearing helmet")
- ✅ Zero-shot - works immediately without training
- ✅ Natural language queries ("damaged equipment", "safety violations")
- ✅ Precise bounding boxes with confidence scores
- ✅ Free and runs locally (after initial model download)

### Key Features

| Feature | Description |
|---------|-------------|
| **Zero-Shot Detection** | Detect new objects without training data |
| **Natural Language** | Use plain English to describe what to find |
| **Precision** | Accurate bounding boxes with confidence scores |
| **Flexibility** | Combine multiple detection targets in one query |
| **Attributes** | Detect objects by color, state, condition, etc. |
| **Free & Local** | No API costs, runs on your machine |

---

## Installation

### Prerequisites

- **Python**: 3.8 or later
- **Free Disk Space**: ~2GB (700MB model + dependencies)
- **RAM**: 8GB minimum, 16GB recommended
- **GPU**: Optional but recommended (NVIDIA GPU with CUDA support)

### Quick Installation

Run the provided batch file:

```bash
# From the project root directory
run_groundingdino.bat
```

The script will:
1. Check if GroundingDINO is installed
2. Offer to install it automatically if missing
3. Download the model on first use (~700MB)

### Manual Installation

If you prefer manual installation:

```bash
# Install GroundingDINO
pip install groundingdino-py

# Install PyTorch (for GPU with CUDA 11.8)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# Or for CPU-only
pip install torch torchvision
```

**Verify Installation:**

```bash
python -c "import groundingdino; print('GroundingDINO installed successfully!')"
```

### Model Download

The GroundingDINO model (~700MB) downloads **automatically on first use**:

- **Size**: ~700MB
- **Location**: `C:\Users\<YourName>\.cache\torch\hub\checkpoints\`
- **Download Time**: 2-10 minutes (depending on internet speed)
- **After First Download**: Works offline, instant startup

---

## Basic Usage

### Using the Batch File

**1. Configure the batch file:**

Edit `run_groundingdino.bat`:

```batch
REM Set your image path
set IMAGE_PATH=C:\Users\YourName\Pictures\photo.jpg

REM Describe what to detect (separate items with " . ")
set DETECTION_QUERY=objects . people . vehicles . furniture . animals . text

REM Set confidence threshold (1-95, default 25)
set CONFIDENCE=25
```

**2. Run it:**

```bash
run_groundingdino.bat
```

**3. Check the output:**

Look for `.txt` files in the same directory as your image with detected objects and locations.

### Common Detection Queries

#### General Purpose

```batch
# Comprehensive detection
set DETECTION_QUERY=objects . people . animals . vehicles . furniture . electronics . plants . text . signs

# Indoor scenes
set DETECTION_QUERY=people . furniture . electronics . decorations . appliances . lighting . windows . doors

# Outdoor scenes
set DETECTION_QUERY=people . vehicles . buildings . trees . sky . roads . signs . landscape . nature
```

#### Specific Use Cases

```batch
# Vehicle detection with details
set DETECTION_QUERY=red cars . blue trucks . motorcycles . bicycles . vans

# Safety inspection
set DETECTION_QUERY=fire extinguisher . exit signs . safety equipment . hazards . emergency lights . first aid . warning signs

# Workplace safety
set DETECTION_QUERY=people wearing helmets . safety vests . hard hats . protective equipment . machinery . tools

# Retail/inventory
set DETECTION_QUERY=products . shelves . displays . signage . packaging . prices . barcodes

# Document analysis
set DETECTION_QUERY=text . logos . diagrams . tables . images . signatures . stamps . barcodes . headings

# Damage assessment
set DETECTION_QUERY=damaged items . broken parts . cracks . dents . missing components . wear marks
```

### Using with Python Scripts

**Direct API usage:**

```python
from scripts.workflow import run_workflow

# Run detection
run_workflow(
    image_path="path/to/image.jpg",
    steps=["describe"],
    provider="groundingdino",
    model="comprehensive",
    detection_query="red cars . people wearing hats . safety equipment",
    confidence=25
)
```

---

## Detection Query Syntax

### Basic Format

Separate detection targets with ` . ` (space-period-space):

```
item1 . item2 . item3
```

### Using Attributes

Be specific with colors, states, and conditions:

```batch
# Colors
red cars . blue shirts . yellow signs

# States
damaged equipment . broken windows . worn tires

# Conditions  
people wearing helmets . items with labels . vehicles with lights on
```

### Plural vs Singular

- Use **plural** for multiple items: `people wearing hats`
- Use **singular** for specific items: `person with umbrella`

### Examples

**Good queries:**
```
✅ red sports cars . motorcycles . people wearing helmets
✅ fire extinguisher . exit signs . emergency lighting
✅ damaged packages . broken items . missing labels
```

**Poor queries:**
```
❌ stuff  (too vague)
❌ things,objects,items  (wrong separator, use " . ")
❌ carsmotorcyclestrucks  (missing separators)
```

---

## Confidence Threshold

The confidence threshold determines how certain the model must be before reporting a detection.

| Threshold | Detection Behavior | Best For |
|-----------|-------------------|----------|
| **10-15%** | Very permissive, many detections | Exploratory analysis, ensuring nothing is missed |
| **20-30%** | **Balanced (recommended)** | General purpose detection |
| **35-50%** | Stricter, fewer false positives | Precision-critical applications |
| **50%+** | Very strict, only obvious objects | High-confidence requirements only |

**Default: 25%** - Good balance between detection rate and accuracy

**Adjust in batch file:**

```batch
set CONFIDENCE=25
```

---

## Hybrid Mode: GroundingDINO + Ollama

Combine GroundingDINO's detection precision with Ollama's natural language descriptions!

### Setup

**1. Install both providers:**

```bash
# Install GroundingDINO (see above)
pip install groundingdino-py torch torchvision

# Install Ollama
# Download from: https://ollama.ai
# Then: ollama pull moondream
```

**2. Use hybrid provider:**

```batch
REM In your batch file, change provider to:
set PROVIDER=groundingdino+ollama
set MODEL=moondream
```

### Benefits

- **Detection**: GroundingDINO finds and locates objects with bounding boxes
- **Description**: Ollama provides natural language descriptions of each object
- **Rich Output**: Get both structured detection data AND readable descriptions

**Example output:**

```
Detections:
- red car (top-left, 92% confidence) - A sporty red sedan with chrome wheels
- person wearing helmet (center-right, 88% confidence) - A cyclist in safety gear
- fire exit sign (top-right, 95% confidence) - Green emergency exit sign with arrow
```

---

## Performance Optimization

### GPU Acceleration

**Check GPU availability:**

```python
import torch
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
```

**Install CUDA-enabled PyTorch:**

```bash
# For CUDA 11.8
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# For CUDA 12.1
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

### Speed Comparison

| Hardware | Processing Time* |
|----------|-----------------|
| **CPU (Intel i7)** | 5-10 seconds |
| **GPU (NVIDIA RTX 2060)** | 1-2 seconds |
| **GPU (NVIDIA RTX 4090)** | 0.5-1 second |

*Per image, 1024x1024 resolution

### Memory Optimization

**For low-memory systems:**

1. **Reduce image size**:
   ```python
   # Resize images before processing
   from PIL import Image
   img = Image.open("large_image.jpg")
   img.thumbnail((1024, 1024))
   img.save("resized_image.jpg")
   ```

2. **Process in batches**:
   - Process fewer images at once
   - Clear cache between batches

3. **Use CPU mode**:
   - Slower but uses less VRAM
   - Better for systems with limited GPU memory

---

## Troubleshooting

### Installation Issues

**Problem**: `pip install groundingdino-py` fails

**Solutions**:
1. Update pip: `python -m pip install --upgrade pip`
2. Install build tools (Windows):
   - Install Visual Studio Build Tools
   - Or: Install Microsoft C++ Build Tools
3. Try alternative installation:
   ```bash
   pip install groundingdino-py --no-build-isolation
   ```

**Problem**: Import error `No module named 'groundingdino'`

**Solution**:
```bash
# Verify installation
pip list | grep groundingdino

# Reinstall if needed
pip uninstall groundingdino-py
pip install groundingdino-py
```

### Model Download Issues

**Problem**: Model download fails or times out

**Solutions**:
1. **Check internet connection**
2. **Manual download**:
   - Download from: https://github.com/IDEA-Research/GroundingDINO/releases/download/v0.1.0-alpha/groundingdino_swint_ogc.pth
   - Save to: `C:\Users\<YourName>\.cache\torch\hub\checkpoints\groundingdino_swint_ogc.pth`
3. **Use VPN** if download is blocked in your region

**Problem**: "Config file not found" error

**Solution**:
- Reinstall groundingdino-py: `pip install --force-reinstall groundingdino-py`
- The config file should be in the package installation

### Detection Issues

**Problem**: No objects detected

**Solutions**:
1. **Lower confidence threshold**: Try `CONFIDENCE=15`
2. **Adjust detection query**: Be more specific or more general
3. **Check image quality**: Ensure image is clear and objects are visible
4. **Verify query syntax**: Use ` . ` (space-period-space) to separate items

**Problem**: Too many false positives

**Solutions**:
1. **Raise confidence threshold**: Try `CONFIDENCE=35`
2. **Be more specific**: Use attributes (colors, states, conditions)
3. **Use narrower queries**: Fewer, more specific items

**Problem**: Detections in wrong locations

**Solution**:
- This is rare with GroundingDINO
- Verify image is not rotated or flipped
- Check if query matches what's actually in the image

### Performance Issues

**Problem**: Very slow processing (>30 seconds per image)

**Solutions**:
1. **Use GPU**: Install CUDA-enabled PyTorch
2. **Reduce image size**: Resize to 1024x1024 or smaller
3. **Simplify query**: Fewer detection targets = faster processing
4. **Close other applications**: Free up RAM/VRAM

**Problem**: Out of memory errors

**Solutions**:
1. **Resize images**: Use smaller resolution
2. **Use CPU mode**: Set `CUDA_VISIBLE_DEVICES=""`
3. **Process one at a time**: Don't batch process
4. **Close other applications**: Especially GPU-intensive ones

---

## Best Practices

### Query Design

1. **Be specific when needed**:
   - ✅ "red fire extinguisher" vs ❌ "stuff"
   - ✅ "person wearing hard hat" vs ❌ "worker"

2. **Use appropriate generalization**:
   - ✅ "vehicles" for cars, trucks, buses
   - ✅ "safety equipment" for helmets, vests, gloves

3. **Include relevant attributes**:
   - Colors: "red signs", "blue uniforms"
   - States: "damaged items", "worn parts"
   - Conditions: "with lights on", "in use"

### Confidence Tuning

Start with default (25%) then adjust:

- **Missing expected objects?** → Lower threshold (20%, 15%)
- **Too many false positives?** → Raise threshold (30%, 35%)
- **Critical applications?** → Use higher threshold (40%+)

### Workflow Integration

1. **Detection only**: Use standalone GroundingDINO
2. **Detection + description**: Use hybrid mode (GroundingDINO + Ollama)
3. **Batch processing**: Process multiple images with same query
4. **Custom workflows**: Chain detection with other processing steps

---

## Use Cases

### Safety Inspection

```batch
REM Workplace safety audit
set DETECTION_QUERY=people wearing helmets . safety vests . hard hats . fire extinguisher . exit signs . emergency equipment . warning signs . hazards

REM Results: Identifies safety compliance and violations
```

### Inventory Management

```batch
REM Retail stock check
set DETECTION_QUERY=products on shelves . empty spaces . damaged items . missing labels . price tags . barcodes

REM Results: Inventory status, damaged goods, missing items
```

### Damage Assessment

```batch
REM Post-incident inspection
set DETECTION_QUERY=damaged equipment . broken windows . cracks . dents . missing components . water damage . fire damage

REM Results: Detailed damage catalog with locations
```

### Traffic Analysis

```batch
REM Road monitoring
set DETECTION_QUERY=cars . trucks . motorcycles . bicycles . pedestrians . traffic lights . road signs . lane markings

REM Results: Vehicle counts, types, and positions
```

### Security Monitoring

```batch
REM Perimeter security
set DETECTION_QUERY=people . vehicles . open doors . broken windows . unauthorized items . security cameras . locks

REM Results: Security status and potential issues
```

### Document Processing

```batch
REM Document analysis
set DETECTION_QUERY=text blocks . logos . signatures . stamps . tables . diagrams . barcodes . QR codes . headings

REM Results: Document structure and key elements
```

---

## Comparison with Other Providers

### GroundingDINO vs YOLO

| Feature | GroundingDINO | YOLO |
|---------|--------------|------|
| **Detection Classes** | Unlimited (text-prompted) | 80 pre-defined classes |
| **Custom Objects** | ✅ Yes, any description | ❌ Requires retraining |
| **Accuracy** | Very high | High |
| **Speed** | 1-5 sec/image (GPU) | 0.1-0.5 sec/image (GPU) |
| **Setup** | Simple pip install | More complex setup |
| **Use Case** | Flexible, custom detection | General purpose, speed-critical |

### GroundingDINO vs Vision Language Models (Ollama, GPT-4o)

| Feature | GroundingDINO | VLMs (Ollama/GPT-4o) |
|---------|--------------|----------------------|
| **Output** | Bounding boxes + labels | Natural language descriptions |
| **Precision** | Exact object locations | General descriptions |
| **Detection Focus** | Specific objects | Scene understanding |
| **Cost** | Free (local) | Free (Ollama) / Paid (GPT-4o) |
| **Best For** | Object location & counting | Scene description & context |

**Best of both worlds**: Use **hybrid mode** (GroundingDINO + Ollama) for precise detection AND rich descriptions!

---

## Cost Comparison

| Provider | Setup Cost | Per-Image Cost | Monthly Cost (1000 images) |
|----------|-----------|----------------|---------------------------|
| **GroundingDINO** | Free | $0 | $0 |
| **Ollama (local)** | Free | $0 | $0 |
| **ONNX (local)** | Free | $0 | $0 |
| **OpenAI GPT-4o** | Free | ~$0.02-0.05 | ~$20-50 |
| **HuggingFace (free tier)** | Free | $0 (rate limited) | $0 |
| **GitHub Copilot** | $10-19/month | $0 (included) | $10-19 |

**GroundingDINO Advantages:**
- ✅ **Zero cost** after initial setup
- ✅ **No API limits** or rate limiting
- ✅ **Offline capable** after model download
- ✅ **Privacy** - data stays on your machine
- ✅ **Unlimited usage** - process millions of images

---

## Advanced Configuration

### Custom Model Paths

Override default cache location:

```python
import os
os.environ['TORCH_HOME'] = 'D:/Models/torch'  # Custom cache directory
```

### Batch Processing Script

Process multiple images with the same query:

```batch
@echo off
set QUERY=red cars . people . traffic signs
set CONFIDENCE=25

for %%f in (C:\Images\*.jpg) do (
    echo Processing: %%f
    python scripts/workflow.py "%%f" --steps describe --provider groundingdino --detection-query "%QUERY%" --confidence %CONFIDENCE%
)
```

### Integration with Other Tools

Export detection results as JSON:

```python
from scripts.workflow import run_workflow

results = run_workflow(
    image_path="image.jpg",
    provider="groundingdino",
    detection_query="objects . people",
    output_format="json"
)

# results contains structured detection data
for detection in results['detections']:
    print(f"{detection['label']}: {detection['confidence']:.2%} at {detection['box']}")
```

---

## Additional Resources

### Documentation

- **Quick Reference**: `imagedescriber/GROUNDINGDINO_QUICK_REFERENCE.md`
- **Implementation Details**: `imagedescriber/GROUNDINGDINO_IMPLEMENTATION_COMPLETE.md`
- **Project Documentation**: Official GroundingDINO GitHub repository

### Support

- **Issues**: Check project GitHub issues
- **Community**: GroundingDINO community forums
- **Local Help**: See batch file comments and error messages

### Learning Resources

- **Example Queries**: See "Common Detection Queries" section above
- **Test Images**: Use `tests/test_files/images/` for experimentation
- **Tutorial Workflows**: `docs/WORKFLOW_README.md`

---

## Summary

**GroundingDINO** is a powerful, flexible, and free solution for object detection that works with natural language queries. It excels at:

✅ **Detecting custom objects** without training
✅ **Flexible queries** with attributes and conditions  
✅ **Precise localization** with bounding boxes
✅ **Zero cost** for unlimited usage
✅ **Privacy-focused** with local processing

**Perfect for:**
- Safety inspections and audits
- Inventory and retail management
- Damage assessment
- Security monitoring
- Document analysis
- Any scenario requiring flexible object detection

**Get started now:**
```batch
run_groundingdino.bat
```

Happy detecting! 🎯
