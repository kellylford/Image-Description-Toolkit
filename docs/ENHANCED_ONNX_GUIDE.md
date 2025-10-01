# Enhanced ONNX Provider - YOLO + Ollama Integration Guide

## Overview

The Enhanced ONNX Provider combines **YOLOv8x object detection** with **Ollama language models** to create the most accurate image descriptions possible. This hybrid approach first detects objects with precise spatial information, then uses that data to enhance the prompts sent to Ollama for natural language generation.

## 🎯 Key Features

### YOLOv8x Object Detection
- **Maximum Accuracy**: Uses YOLOv8x (130MB) - the most accurate YOLO model
- **Automatic Fallback**: Falls back to YOLOv8n if YOLOv8x unavailable
- **Hardware Acceleration**: Automatically uses GPU/NPU when available
- **80+ Object Classes**: Detects people, vehicles, animals, furniture, electronics, etc.

### Spatial Analysis
- **Location Detection**: Objects classified as top/middle/bottom + left/center/right
- **Size Classification**: Objects categorized as large/medium/small/tiny based on image percentage
- **Confidence Scoring**: Only includes objects with high detection confidence (>50%)
- **Smart Limiting**: Focuses on top 15 most significant objects to avoid overwhelming

### Enhanced Prompting
- **Object-Aware Descriptions**: Prompts include detected object data for context
- **Spatial Context**: Descriptions include where objects are located in the image  
- **Size Relationships**: Understanding of relative object sizes and importance
- **Natural Integration**: YOLO data seamlessly integrated into natural language prompts

## 🚀 Getting Started

### Prerequisites
```bash
# Install required packages
pip install ultralytics>=8.0.0
pip install onnxruntime>=1.16.0

# OR run the automated setup
setup.bat  # Installs everything automatically
```

### Using Enhanced ONNX Provider

1. **Launch ImageDescriber GUI**:
   ```bash
   cd imagedescriber
   python imagedescriber.py
   ```

2. **Select Enhanced ONNX Provider**:
   - In the "AI Provider" dropdown, select "Enhanced ONNX"
   - Status will show hardware acceleration type (CPU/GPU/NPU)

3. **Choose Ollama Model**:
   - Select any Ollama model from the dropdown
   - Models will show "(YOLO Enhanced)" suffix
   - Recommended: `llava:7b`, `llama3.2-vision:11b`, or `gemma2:latest`

4. **Process Images**:
   - Add images to your workspace
   - Click "Process" or use batch processing
   - Enhanced descriptions will include spatial object information

## 📊 How It Works

### 1. YOLO Detection Phase
```
Image → YOLOv8x → Object Detection Results
                  ├── Person (large, middle-left, 94% confidence)
                  ├── Car (medium, bottom-center, 87% confidence)  
                  └── Tree (large, top-right, 92% confidence)
```

### 2. Spatial Analysis Phase
```
Detection Results → Spatial Processing → Enhanced Object Data
                                        ├── "large person in middle-left area"
                                        ├── "medium car in bottom-center area"
                                        └── "large tree in top-right area"
```

### 3. Enhanced Prompting Phase
```
Object Data + User Prompt → Enhanced Prompt → Ollama Model → Description
"Detected objects: large person in middle-left area, medium car in bottom-center area..."
```

### 4. Natural Description Output
```
Final Result: "The image shows a person standing in the left portion of the frame, 
with a car visible in the lower center area and a large tree in the upper right..."
```

## 🎛️ Configuration Options

### Hardware Acceleration
The Enhanced ONNX provider automatically detects and uses:
- **CUDA GPU**: For NVIDIA graphics cards
- **DirectML**: For AMD/Intel graphics cards  
- **NPU**: For Copilot+ PC neural processing units
- **CPU**: Fallback when no acceleration available

### YOLO Model Selection
- **Default**: YOLOv8x (most accurate, 130MB)
- **Fallback**: YOLOv8n (fastest, 6MB) if YOLOv8x fails to download
- **Automatic**: No user configuration needed - handles model selection automatically

### Object Detection Tuning
Current settings (optimized for accuracy):
- **Confidence Threshold**: 50% (only high-confidence detections)
- **Max Objects**: 15 (prevents prompt overflow)
- **Size Thresholds**: Large >10%, Medium 3-10%, Small 1-3%, Tiny <1%

## 🔧 Troubleshooting

### "YOLO not available" Message
```bash
# Install YOLO detection
pip install ultralytics>=8.0.0

# Test YOLO installation
python -c "from ultralytics import YOLO; print('YOLO available')"
```

### "ONNX Runtime not available" Message  
```bash
# Install ONNX Runtime
pip install onnxruntime>=1.16.0 onnx>=1.15.0

# For GPU acceleration (optional)
pip install onnxruntime-gpu>=1.16.0
```

### Hardware Acceleration Not Working
```bash
# Check available providers
python -c "import onnxruntime as ort; print('Available providers:', ort.get_available_providers())"

# Expected providers:
# - CUDAExecutionProvider (NVIDIA GPU)
# - DmlExecutionProvider (DirectML - AMD/Intel)
# - CPUExecutionProvider (CPU fallback)
```

### Model Download Issues
- **YOLOv8x**: Downloads automatically on first use (130MB)
- **YOLOv8n**: Fallback if YOLOv8x fails (6MB)  
- **Internet Required**: Initial download only - works offline afterward
- **Storage Location**: Models cached in user directory

## 📈 Performance Comparison

### Standard Ollama vs Enhanced ONNX
| Feature | Standard Ollama | Enhanced ONNX |
|---------|-----------------|---------------|
| **Object Detection** | Basic (text only) | YOLOv8x precision |
| **Spatial Awareness** | Limited | Precise locations |
| **Object Confidence** | None | 50%+ confidence |
| **Size Relationships** | Approximate | Measured percentages |
| **Hardware Acceleration** | CPU only | GPU/NPU support |
| **Description Accuracy** | Good | Excellent |

### Expected Improvements
- **More Accurate Object Counts**: "3 people" instead of "several people"
- **Precise Locations**: "person in top-left" instead of "person somewhere"
- **Size Awareness**: "large dog, small cat" with actual size relationships
- **Confidence**: Only mentions objects that are definitely present
- **Spatial Context**: Understands scene composition and layout

## 🛠️ Development Notes

### Architecture
```
Image Input
    ↓
YOLOv8x Detection → Spatial Analysis → Enhanced Prompts
    ↓                      ↓                 ↓
Object List → Location + Size Data → Ollama Model → Final Description
```

### Integration Points
- **GUI Integration**: Seamless provider selection in ImageDescriber
- **Workspace Support**: Works with .idw project files
- **Batch Processing**: Processes multiple images efficiently  
- **Error Handling**: Graceful fallbacks when components unavailable
- **Diagnostic Tools**: Description Properties shows YOLO enhancement status

### Future Enhancements
- **Custom YOLO Models**: Support for specialized object detection
- **Confidence Tuning**: User-adjustable detection thresholds
- **Additional Spatial Analysis**: Depth, occlusion, relationships
- **Performance Optimization**: Model quantization, caching improvements

## 📞 Support

For Enhanced ONNX provider issues:
1. **Check Prerequisites**: Ensure `ultralytics` and `onnxruntime` installed
2. **Verify Ollama**: Must have Ollama running with vision models
3. **Hardware Check**: GPU/NPU acceleration is optional but recommended
4. **Diagnostic Feature**: Use "Description Properties" in GUI to troubleshoot
5. **GitHub Issues**: Report bugs with system information and error messages

## 🏆 Best Practices

1. **Model Selection**: Use `llava:7b` or `llama3.2-vision:11b` for best results
2. **Image Quality**: Higher resolution images = better object detection
3. **Batch Processing**: Process similar images together for consistency
4. **Hardware**: Use GPU/NPU acceleration for faster processing
5. **Testing**: Try Enhanced ONNX vs standard Ollama on sample images to see improvement