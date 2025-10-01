# Image Description Toolkit - Quick Setup Guide

## 🚀 Automated Setup (Recommended)

### Windows Users:
```cmd
# Run the automated setup script
setup.bat
```

### Manual Setup:
```bash
# 1. Install Python dependencies (includes YOLO object detection)
pip install -r requirements.txt

# 2. Install and start Ollama
# Download from: https://ollama.ai/download/windows
ollama serve

# 3. Download a vision model
ollama pull llava:7b

# 4. Test your setup
cd tests && python run_tests.py

# 5. Process your first collection
python workflow.py tests/test_files/
```

## 📋 What You Get

After setup, you can use:

### Enhanced ONNX Provider (NEW!)
```bash
# Use YOLOv8x object detection + Ollama for maximum accuracy
# Available in ImageDescriber GUI - select "Enhanced ONNX" provider
cd imagedescriber && python imagedescriber.py

# Features:
# - YOLOv8x object detection (130MB, maximum accuracy)
# - Spatial analysis (object locations and sizes)
# - Enhanced prompts with detected object data
# - Hardware acceleration (GPU/NPU when available)
```

### Main Workflow System
```bash
# Process videos + images → descriptions → HTML reports
python workflow.py path/to/your/media
```

### GUI Applications
```bash
# Image Description GUI (project management)
cd imagedescriber && python imagedescriber.py

# Prompt Editor
cd prompt_editor && python prompt_editor.py

# Description Viewer
cd viewer && python viewer.py
```

### Model Testing & Optimization
```bash
# Test all available models to find the best one
python comprehensive_test.py path/to/sample/images
```

### Individual Scripts
```bash
# Video frame extraction
cd scripts && python video_frame_extractor.py videos/

# HEIC to JPG conversion
cd scripts && python ConvertImage.py heic_photos/

# AI image descriptions only
cd scripts && python image_describer.py images/ --model llava:7b

# Generate HTML reports
cd scripts && python descriptions_to_html.py descriptions.txt report.html
```

## 🔧 Building Applications

Each application has build scripts for creating standalone executables:

```cmd
# Build Image Describer GUI
cd imagedescriber
build_imagedescriber.bat

# Build Prompt Editor
cd prompt_editor  
build_prompt_editor.bat

# Build Viewer
cd viewer
build_viewer.bat
```

## 📚 Documentation

- **README.md** - Complete user guide
- **docs/ENHANCED_ONNX_GUIDE.md** - YOLOv8x + Ollama integration guide
- **docs/CONFIGURATION.md** - Configuration options
- **docs/HUGGING_FACE_DOWNLOAD_GUIDE.md** - Pre-download AI models
- **docs/TESTING_README.md** - Model testing guide

## 🆘 Troubleshooting

### Ollama Not Found
```bash
# Check if Ollama is running
curl http://localhost:11434/api/version

# If not running, start it
ollama serve
```

### No Vision Models
```bash
# List installed models
ollama list

# Install a vision model
ollama pull llava:7b
# or
ollama pull llama3.2-vision:11b
```

### Python Dependencies
```bash
# Update pip first
python -m pip install --upgrade pip

# Install requirements (includes YOLO detection)
pip install -r requirements.txt

# Test YOLO installation
python -c "from ultralytics import YOLO; print('YOLO available')"
```

### Enhanced ONNX Provider Issues
```bash
# Check YOLO installation
pip install ultralytics>=8.0.0

# Check ONNX Runtime
pip install onnxruntime>=1.16.0

# Test Enhanced ONNX provider
cd imagedescriber && python imagedescriber.py
# Select "Enhanced ONNX" provider in GUI
```

### Test Suite Failures
```bash
# Run tests for specific component
cd tests
python test_workflow.py
python test_image_describer.py
```

## ⚡ Performance Tips

1. **Find the best model for your images**:
   ```bash
   python comprehensive_test.py sample_images/
   ```

2. **Use Enhanced ONNX Provider** for maximum accuracy:
   - Launch ImageDescriber GUI: `cd imagedescriber && python imagedescriber.py`
   - Select "Enhanced ONNX" as AI provider
   - Choose any Ollama model (will show "YOLO Enhanced" suffix)
   - Gets YOLOv8x object detection + enhanced prompts automatically

3. **For Copilot+ PCs** (NPU acceleration):
   - See `docs/COPILOT_PC_SETUP_GUIDE.md`
   - Enhanced ONNX provider automatically uses NPU when available

4. **For large collections**:
   - Start with small test batches
   - Use `--dry-run` to preview processing
   - Enable verbose logging with `--verbose`

## 📞 Need Help?

- **GitHub Issues**: Report bugs or request features
- **GitHub Discussions**: Ask questions and share tips
- **Documentation**: Check the `docs/` directory for guides