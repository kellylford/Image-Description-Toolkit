# Image Description Toolkit

An AI-powered toolkit for generating descriptive text from images using local language models via Ollama. The toolkit provides a unified workflow system that orchestrates the entire pipeline from video frame extraction through HTML report generation, making it simple to process large collections of media files.

## 🌟 Features

- **🔄 Unified Workflow System**: Complete pipeline from video → frames → images → descriptions → HTML reports
- **🤖 AI-Powered Descriptions**: Generate natural language descriptions using local Ollama models
- **⚡ Enhanced ONNX Provider**: YOLOv8x object detection + Ollama hybrid workflow for maximum accuracy
- **🎯 Spatial Object Detection**: Precise location analysis (top/middle/bottom + left/center/right) and size classification
- **🧪 Comprehensive Model Testing**: Automatically test all available Ollama models with all prompt styles to find optimal combinations
- **📊 Advanced Performance Analytics**: Detailed reporting with timing, success rates, and quality metrics across all model/prompt combinations
- **🎥 Video Frame Extraction**: Extract frames from videos for analysis
- **🖼️ Image Format Conversion**: Convert HEIC images to JPG automatically
- **📄 HTML Report Generation**: Create beautiful web galleries with descriptions
- **⚡ Batch Processing**: Handle multiple files and directories efficiently
- **📱 Interactive Visual Reports**: Comprehensive HTML reports with side-by-side model comparisons
- **📋 Professional Logging**: Complete logging with statistics and progress tracking
- **🛠️ Individual Script Access**: Use components separately when needed

## 📞 Support & Documentation

- **⚡ Enhanced ONNX Guide**: See `docs/ENHANCED_ONNX_GUIDE.md` for YOLOv8x + Ollama integration details
- **📋 Comprehensive Testing Guide**: See `TESTING_GUIDE.md` for complete model testing documentation
- **📚 Documentation**: Detailed guides available in the `docs/` directory
- **🐛 Issues**: Report bugs or request features via [GitHub Issues](https://github.com/kellylford/Image-Description-Toolkit/issues)
- **💬 Discussions**: Join conversations in [GitHub Discussions](https://github.com/kellylford/Image-Description-Toolkit/discussions)
- **🧪 Testing**: Run `cd tests && python run_tests.py` to verify your setup

## 🚀 **Ready to Get Started?**

### Option 1: Automated Setup (Recommended)
```cmd
# Windows users - run the automated setup script
setup.bat
```

### Option 2: Manual Setup
```bash
# 1. Install dependencies (includes YOLO detection)
pip install -r requirements.txt

# 2. Install Ollama and pull a vision model  
ollama pull llava:7b

# 3. Test your setup
cd tests && python run_tests.py

# 4. Find the best model for your images (recommended)
python comprehensive_test.py tests/test_files/images

# 5. Process your first media collection
python workflow.py path/to/your/media/files

# 6. Check the timestamped output directory for results!

# ✨ Bonus: Resume interrupted workflows
python workflow.py --resume workflow_output_directory
```

**🎉 That's it!** The workflow system will handle the rest automatically. 

**📋 For detailed setup instructions, see [QUICK_START.md](QUICK_START.md)**

**💡 Pro Tip**: Always run the comprehensive testing first to discover which models work best with your specific types of images. You might be surprised which models perform excellently!

## 🔧 System Requirements

**Ollama is required for vision model inference and must be installed and running for the toolkit to function.**

### ⚡ **Copilot+ PC High-Performance Setup** (Recommended)

**For fastest performance with NPU acceleration:**

1. **Hardware Requirements**:
   - NPU with 40+ TOPS (AMD Ryzen AI 300, Intel Core Ultra 200V, Snapdragon X)
   - Windows 11 (22H2 or later)
   - 16GB+ RAM

2. **Quick Setup**:
   ```bash
   # Run the automated setup script
   setup_windows.bat
   
   # Or verify existing setup
   python verify_system.py
   ```

3. **Performance Results**:
   - **<100ms response times** with NPU acceleration
   - **5-10x more detailed** descriptions than standard AI
   - **Completely local** - no internet required after setup
   - **Professional quality** image analysis

**📋 See [COPILOT_PC_SETUP_GUIDE.md](COPILOT_PC_SETUP_GUIDE.md) for detailed Copilot+ PC installation guide.**

### Install Ollama

**macOS/Linux:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

**Windows:**
Download and install from [https://ollama.ai/download/windows](https://ollama.ai/download/windows)

### Start Ollama Server

```bash
ollama serve
```

### Verify Ollama is Running

```bash
curl http://localhost:11434/api/version
```

If Ollama is running properly, you should see a JSON response with version information.

**⚠️ Important**: The Image Description Toolkit will not function unless Ollama is installed and running. Make sure to start the Ollama server before using any of the toolkit's AI-powered features.

## 📁 Project Structure

```
Image-Description-Toolkit/
├── setup.bat                 # 🔧 Automated setup script (Windows)
├── QUICK_START.md            # 📋 Quick setup guide
├── workflow.py               # 🎯 Main entry point - workflow wrapper
├── comprehensive_test.py     # 🧪 Comprehensive model testing and comparison
├── scripts/                  # 🔧 Core processing scripts
│   ├── workflow.py           #    Workflow orchestrator (main engine)
│   ├── video_frame_extractor.py #    Extract frames from videos
│   ├── ConvertImage.py       #    Convert HEIC to JPG
│   ├── image_describer.py    #    AI image description
│   ├── descriptions_to_html.py #    Generate HTML reports
│   ├── workflow_utils.py     #    Workflow utilities
│   ├── workflow_config.json  #    Workflow configuration
│   ├── image_describer_config.json # AI model settings
│   └── video_frame_extractor_config.json # Video processing config
├── docs/                     # 📚 Documentation
├── tests/                    # 🧪 Test suite and test files
├── TESTING_GUIDE.md          # 📋 Comprehensive testing documentation
├── requirements.txt          # 📦 Python dependencies
├── .gitignore               # 🚫 Git ignore rules
└── README.md                # 📖 This file
```

## 🚀 Quick Start

### Primary Usage (Recommended)

The **workflow system** is the main way to use this toolkit:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Install Ollama and a vision model
# Download from https://ollama.ai/
ollama pull llava:7b  # or llama3.2-vision:11b, moondream, etc.

# 3. Process your media files (videos + images)
python workflow.py path/to/your/media

# 4. Find results in timestamped output directory
# -> workflow_output_YYYYMMDD_HHMMSS/
```

### Model Testing & Optimization (New!)

Before processing large collections, use the comprehensive testing system to find the optimal AI model for your needs:

```bash
# Test all available models with all prompt styles
python comprehensive_test.py path/to/sample/images

# Generates detailed reports:
# - comprehensive_test_visual_report.html (interactive comparison)
# - comprehensive_test_data.csv (spreadsheet analysis)
# - test_statistics.txt (performance analytics)
# - failure_analysis.txt (troubleshooting)
```

This powerful testing capability:
- **Discovers all installed Ollama models** (not just vision-labeled ones)
- **Tests every model/prompt combination** through the complete workflow
- **Generates comprehensive performance analytics** with timing and success rates
- **Creates interactive HTML reports** for visual model comparison
- **Provides data-driven model selection** based on your specific images

### GUI Application (Project Management)

For ongoing project management and iterative description work:

```bash
# Launch the ImageDescriber GUI
cd imagedescriber
python imagedescriber.py

# Features:
# - Create/save/load workspace projects (.idw files)
# - Batch processing with enterprise-level controls  
# - Advanced filtering (all/described/batch/videos)
# - Full keyboard navigation (R/F2=rename, P=process, B=batch)
# - Support for both Ollama local and OpenAI cloud AI
```

### Workflow Steps

The workflow automatically handles:
1. **Video Processing** → Extract frames from MP4, MOV, AVI files  
2. **Image Conversion** → Convert HEIC to JPG  
3. **AI Description** → Generate descriptions using Ollama models  
4. **HTML Generation** → Create beautiful web gallery with descriptions

### Advanced Workflow Usage

```bash
# Process only specific steps
python workflow.py media/ --steps describe,html

# Use custom output directory
python workflow.py media/ --output-dir my_results

# Override AI model
python workflow.py media/ --model llama3.2-vision:11b

# Dry run (see what would be processed)
python workflow.py media/ --dry-run

# Verbose logging
python workflow.py media/ --verbose
```

### Individual Script Usage (Advanced)

When you need fine-grained control, you can use scripts directly:

```bash
# Video frame extraction
cd scripts
python video_frame_extractor.py path/to/videos

# Image format conversion  
python ConvertImage.py path/to/heic/files --output converted/

# AI image descriptions
python image_describer.py path/to/images --model llava:7b

# HTML report generation
python descriptions_to_html.py descriptions.txt report.html
```

## 🧪 Testing

### Comprehensive Model Testing

Run the comprehensive testing system to evaluate all available models:

```bash
# Test all models with sample images
python comprehensive_test.py tests/test_files/images

# Custom output directory
python comprehensive_test.py sample_images/ --output-dir my_test_results
```

The testing system generates multiple report formats:
- **Interactive HTML report** - Visual comparison of all models and prompts
- **CSV data** - Raw performance data for spreadsheet analysis  
- **Performance statistics** - Model timing and success rate analytics
- **Failure analysis** - Detailed troubleshooting information

See `TESTING_GUIDE.md` for complete testing documentation.

### Basic Testing

```bash
# Run test suite
cd tests
python run_tests.py

# Test individual components
python test_workflow.py
```

## 🛠️ Core Components

### Comprehensive Testing System (`comprehensive_test.py`) **NEW!**
Advanced model evaluation and comparison system:
- **🤖 Model Discovery**: Automatically finds all installed Ollama models (including non-vision models like gemma2)
- **📊 Complete Testing**: Tests every model with every prompt style through the full 4-step workflow
- **📈 Performance Analytics**: Detailed timing, success rates, and failure analysis
- **📋 Multiple Report Formats**: Interactive HTML, CSV data, statistics, and failure reports  
- **🎯 Data-Driven Selection**: Make informed decisions about which models work best for your images
- **💡 Model Discovery**: Often reveals that non-vision models work excellently for image descriptions

### Workflow System (`workflow.py` → `scripts/workflow.py`)
The main orchestrator that provides a unified processing pipeline:
- **🎯 Simple Entry Point**: Just run `python workflow.py media_folder`
- **🔄 Complete Pipeline**: Handles video→frames→conversion→descriptions→HTML
- **📊 Progress Tracking**: Real-time logging with comprehensive statistics  
- **🛡️ Error Resilience**: Continues processing despite individual file failures
- **⚙️ Flexible Configuration**: Support for custom models, output directories, and step selection
- **📋 Professional Logging**: Timestamped logs with detailed statistics and summaries

### Video Frame Extractor (`scripts/video_frame_extractor.py`)
Extract frames from videos for image analysis:
- **🎬 Multiple Formats**: MP4, MOV, AVI, MKV support
- **⏱️ Flexible Extraction**: Time-based intervals (e.g., every 5 seconds)
- **🖼️ Quality Control**: Configurable resolution and image quality
- **📁 Organized Output**: Systematic frame numbering and folder structure

### Image Converter (`scripts/ConvertImage.py`)  
Convert HEIC images to JPG for broader compatibility:
- **📱 HEIC/HEIF Support**: Handle iPhone/iOS photos seamlessly
- **🔧 Quality Controls**: Configurable compression settings  
- **📋 Metadata Preservation**: Maintains EXIF data during conversion
- **⚡ Batch Processing**: Convert entire directories efficiently

### AI Image Describer (`scripts/image_describer.py`)
Generate natural language descriptions using local Ollama models:
- **🤖 Multiple Models**: llava:7b, llama3.2-vision:11b, moondream, bakllava
- **💬 Custom Prompts**: Configurable description styles (detailed, brief, technical)
- **🏠 Local Processing**: No cloud dependencies, complete privacy
- **📊 EXIF Integration**: Include camera settings, GPS, timestamps in output
- **🧠 Memory Optimization**: Smart processing for large image collections

### ImageDescriber GUI (`imagedescriber/imagedescriber.py`)
Professional graphical interface for managing image description projects:
- **📁 Workspace System**: Save/load projects as `.idw` files for long-term management
- **🎯 Batch Processing**: Enterprise-level controls for processing multiple images
- **🔍 Advanced Filtering**: View all, described, batch-marked, or videos-only items
- **♿ Accessibility**: WCAG-compliant design with full keyboard navigation and screen reader support  
- **⌨️ Keyboard Shortcuts**: R/F2 for rename, P for process, B for batch marking
- **📝 Rename Functionality**: Custom display names within workspace (files unchanged)
- **🎥 Video Support**: Frame extraction and management integrated
- **📊 Real-time Status**: Live processing indicators and description counts
- **🌐 Dual AI Support**: Both Ollama local and OpenAI cloud providers
- **⚡ Enhanced ONNX Provider**: YOLOv8x object detection + Ollama hybrid workflow

### Enhanced ONNX Provider (`imagedescriber/ai_providers.py`) **NEW!**
Advanced AI provider combining YOLO object detection with Ollama language models:
- **🎯 YOLOv8x Integration**: Maximum accuracy object detection (130MB model)
- **📍 Spatial Analysis**: Precise object location (top/middle/bottom + left/center/right)
- **📏 Size Classification**: Object size analysis (large/medium/small/tiny)
- **🔄 Hybrid Workflow**: YOLO detection → Enhanced prompts → Ollama descriptions
- **🏷️ Model Labeling**: Shows "YOLO Enhanced" suffix on Ollama models
- **🎛️ Hardware Acceleration**: Uses available hardware (GPU/NPU) when possible
- **📊 Enhanced Prompts**: Includes detected object data for more accurate descriptions
- **🔧 Diagnostic Tools**: Description Properties feature for troubleshooting

### HTML Report Generator (`scripts/descriptions_to_html.py`)
Create beautiful web galleries from descriptions:
- **🌐 Responsive Design**: Mobile-friendly layouts
- **🎨 Professional Styling**: Clean, modern web interface
- **🔍 Interactive Features**: Easy browsing and navigation

## ⚙️ Configuration

Configuration files are located in the `scripts/` directory:

- **`scripts/workflow_config.json`** - Main workflow settings, step configuration, and output preferences
- **`scripts/image_describer_config.json`** - AI model selection, prompts, and processing parameters  
- **`scripts/video_frame_extractor_config.json`** - Video processing settings and frame extraction options

### Example Workflow Configuration

```json
{
  "workflow": {
    "default_steps": ["video", "convert", "describe", "html"],
    "steps": {
      "video_extraction": {
        "config_file": "video_frame_extractor_config.json"
      },
      "image_conversion": {
        "quality": 95,
        "keep_metadata": true
      },
      "image_description": {
        "model": "llava:7b",
        "prompt_style": "detailed",
        "config_file": "image_describer_config.json"
      },
      "html_generation": {
        "title": "Image Analysis Report",
        "include_details": false
      }
    }
  }
}
```

## 🔧 Advanced Usage

### Model Testing and Selection

```bash
# Comprehensive model testing (recommended first step)
python comprehensive_test.py /path/to/sample/images

# View results in generated HTML report
# Open: comprehensive_test_YYYYMMDD_HHMMSS/comprehensive_test_visual_report.html

# Analyze performance data in spreadsheet
# Import: comprehensive_test_YYYYMMDD_HHMMSS/comprehensive_test_data.csv
```

### Workflow Examples

```bash
# Process entire media collection (videos + images)
python workflow.py /path/to/media/collection

# Only generate descriptions and HTML (skip video/conversion)
python workflow.py /path/to/images --steps describe,html

# Use different AI model (based on testing results)
python workflow.py /path/to/images --model llama3.2-vision:11b

# Custom output location
python workflow.py /path/to/images --output-dir /custom/output/path

# Preview what will be processed
python workflow.py /path/to/images --dry-run

# Get detailed logging
python workflow.py /path/to/images --verbose
```

### Custom AI Models

```bash
# Install additional Ollama models
ollama pull llama3.2-vision:11b  # Larger, more capable model
ollama pull moondream:latest     # Lightweight alternative
ollama pull bakllava:latest      # Another vision model option

# Update scripts/image_describer_config.json to use your preferred model
```

### Output Structure

When you run the workflow, it creates a timestamped output directory:

```
workflow_output_20250721_143022/
├── logs/                     # Detailed processing logs
│   ├── workflow_orchestrator_20250721_143022.log
│   ├── video_frame_extractor_20250721_143023.log
│   ├── image_converter_20250721_143024.log
│   └── image_describer_20250721_143025.log
├── extracted_frames/         # Video frames (if processing videos)
├── converted_images/         # HEIC→JPG conversions (if needed)
├── descriptions/            # AI-generated descriptions
│   └── image_descriptions.txt
└── reports/                 # HTML reports
    └── image_descriptions.html
```

## 🤝 Contributing

We welcome contributions! Here's how to get started:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Install development dependencies**: `pip install -r requirements.txt`
4. **Test your setup**: `cd tests && python run_tests.py`
5. **Make your changes**
6. **Test the workflow**: `python workflow.py tests/test_files/ --dry-run`
7. **Update documentation** if needed
8. **Submit a pull request**

### Development Guidelines
- Follow PEP 8 style guidelines
- Add tests for new functionality  
- Ensure the workflow system continues to work end-to-end
- Update documentation for new features
- Test with multiple Python versions (3.8+)

## 📞 Support & Documentation

- **� Documentation**: Detailed guides available in the `docs/` directory
- **🐛 Issues**: Report bugs or request features via [GitHub Issues](https://github.com/kellylford/Image-Description-Toolkit/issues)
- **� Discussions**: Join conversations in [GitHub Discussions](https://github.com/kellylford/Image-Description-Toolkit/discussions)
- **🧪 Testing**: Run `cd tests && python run_tests.py` to verify your setup

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## � **Ready to Get Started?**

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Install Ollama and pull a vision model  
ollama pull llava:7b

# 3. Test your setup
cd tests && python run_tests.py

# 4. Process your first media collection
python workflow.py path/to/your/media/files

# 5. Check the timestamped output directory for results!
```

**🎉 That's it!** The workflow system will handle the rest automatically.
