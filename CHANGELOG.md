# Changelog

All notable changes to the Image Description Toolkit will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.1] - 2025-10-21

### 🚀 Performance Improvements

**Major Ollama Cloud Optimizations**
- **75% faster retry recovery**: Reduced retry delays from [2s, 4s, 8s] to [0.5s, 1s, 2s]
- **90-second request timeout**: Prevents 2+ minute hangs, fail fast and retry sooner
- **Request throttling**: 3-second delays between Ollama requests to reduce server load
- **Better error handling**: Enhanced timeout detection and retry logic
- **Significant improvement**: 40-minute processing reduced to 15-20 minutes for large batches

### 🔧 Fixes

**Release Packaging**
- Fixed idt2.zip regression - now includes all 4 applications correctly
- Updated packaging scripts to include `imagedescriber_v3.0.1.zip`, `install_idt.bat`, and `README.md`
- All distribution packages now complete and tested

**Documentation**
- Comprehensive User Guide updates featuring GUI applications prominently
- Added dedicated sections for GUI ImageDescriber and Prompt Editor
- Updated application overview and use case guidance
- Enhanced troubleshooting for all four applications

### 📚 Documentation

**Enhanced User Guide**
- Featured GUI ImageDescriber and Prompt Editor as top-level applications
- Added comprehensive application comparison and use case guidance
- Updated installation instructions for all four tools
- Enhanced quick reference with application launchers

**Technical Documentation**
- Created detailed GitHub issue for Ollama performance analysis
- Documented root cause analysis of server 500 errors
- Added performance benchmarking data and optimization strategies

## [3.0.0] - 2025-10-20

### 🌟 Major Release - Complete Application Suite

**Four Standalone Applications**
- **CLI Toolkit (`idt.exe`)**: Advanced batch processing and automation
- **GUI ImageDescriber (`imagedescriber.exe`)**: Visual interface for individual images
- **Prompt Editor (`prompt_editor.exe`)**: Design and test custom prompts
- **Results Viewer (`viewer.exe`)**: Browse results and real-time monitoring

**Unified Distribution**
- Single master package (`idt2.zip`) containing all applications
- Automatic installer (`install_idt.bat`) for complete setup
- Cross-architecture support (AMD64 and ARM64 Windows)
- No Python installation required - all executables are standalone

**Enhanced CLI Features**
- Interactive wizard (`idt guideme`) for step-by-step setup
- Workflow naming and organization improvements
- Advanced analysis tools (`combinedescriptions`, `stats`, `contentreview`)
- Real-time results viewing integration
- Comprehensive batch file library for quick model testing

**GUI Applications**
- **ImageDescriber**: Drag-and-drop interface, real-time preview, visual provider setup
- **Prompt Editor**: A/B testing, prompt library management, live preview
- **Results Viewer**: Real-time monitoring, search/filter, accessibility optimized

**Provider Support**
- **Ollama**: Local models with automatic detection and installation helpers
- **OpenAI**: GPT-4o, GPT-4o-mini with cost optimization
- **Claude**: Full Anthropic model support with intelligent retry logic

**Analysis & Export**
- Chronological image sorting by EXIF date (not filename)
- Enhanced CSV/TSV export with metadata preservation
- Statistical analysis and performance benchmarking
- Content quality analysis and readability metrics

## [1.0.0] - 2025-09-02

### Initial Release

This is the first stable release of the Image Description Toolkit, featuring a complete AI-powered pipeline for generating descriptive text from images and videos using local language models via Ollama.

#### 🌟 Major Features

**Unified Workflow System**
- Complete pipeline from video → frames → images → descriptions → HTML reports
- Single command processing: `python workflow.py path/to/media`
- Automatic orchestration of all processing steps
- Timestamped output directories with organized results
- Professional logging with comprehensive statistics

**Comprehensive Model Testing System**
- `comprehensive_test.py` - Advanced model evaluation and comparison
- Automatic discovery of ALL installed Ollama models (including non-vision models)
- Tests every model with every prompt style through complete 4-step workflow
- Multiple report formats: interactive HTML, CSV data, performance statistics, failure analysis
- Data-driven model selection with detailed analytics

**AI-Powered Image Description**
- Support for multiple Ollama models: llava:7b, llama3.2-vision:11b, moondream, gemma2, etc.
- Multiple prompt styles: detailed, concise, artistic, technical, colorful, narrative
- Local processing with complete privacy (no cloud dependencies)
- EXIF data integration (camera settings, GPS, timestamps)
- Memory optimization for large image collections

**Video Frame Extraction**
- Support for MP4, MOV, AVI, MKV formats
- Time-based interval extraction (e.g., every 5 seconds)
- Configurable resolution and quality settings
- Organized frame numbering and folder structure

**Image Format Conversion**
- HEIC/HEIF to JPG conversion for iPhone/iOS photos
- Configurable compression settings
- EXIF metadata preservation
- Batch processing capabilities

**HTML Report Generation**
- Responsive, mobile-friendly web galleries
- Professional styling with clean, modern interface
- Interactive browsing and navigation features
- Side-by-side image and description display

**Qt6 Image Description Viewer**
- Interactive desktop application for viewing results
- Accessibility features and keyboard navigation
- Support for viewing descriptions alongside images
- Professional GUI for non-technical users

#### 🔧 Technical Features

**Configuration System**
- JSON-based configuration files for all components
- Flexible workflow step selection
- Customizable model and prompt settings
- Per-component configuration management

**Robust Error Handling**
- Continues processing despite individual file failures
- Comprehensive error logging and reporting
- Timeout protection for long-running operations
- Detailed failure analysis and troubleshooting information

**Performance Optimization**
- Smart memory management for large collections
- Batch processing optimizations
- Progress tracking with real-time statistics
- Background process support

**Quality Assurance**
- Comprehensive test suite with automated testing
- Model performance benchmarking
- Output validation and verification
- Cross-platform compatibility (Windows, macOS, Linux)

#### 📚 Documentation

**Complete Documentation Suite**
- Comprehensive README with quick start guide
- Detailed testing guide (`TESTING_GUIDE.md`)
- Individual component documentation in `docs/` directory
- Configuration examples and best practices
- Troubleshooting guides and FAQ

**Example Configurations**
- Pre-configured workflows for common use cases
- Model selection guidance based on performance testing
- Prompt optimization recommendations
- Performance tuning guidelines

#### 🧪 Testing & Validation

**Automated Testing Framework**
- Unit tests for all core components
- Integration tests for complete workflow
- Model compatibility testing
- Cross-platform validation

**Comprehensive Model Evaluation**
- Performance benchmarking across all available models
- Quality assessment with visual comparison reports
- Success rate analysis and failure investigation
- Data export for statistical analysis

#### 📦 Dependencies & Requirements

**Core Dependencies**
- Python 3.8+
- Ollama 0.3.0+ (required for AI functionality)
- PyQt6 6.4.0+ (for GUI viewer)
- Pillow 10.0.0+ with HEIF support
- OpenCV 4.8.0+ (for video processing)

**Optional Dependencies**
- tqdm for enhanced progress bars
- pytest for development testing
- numpy for numerical operations

#### 🚀 Getting Started

**Quick Installation**
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Install Ollama and pull a vision model
ollama pull llava:7b

# 3. Test your setup
cd tests && python run_tests.py

# 4. Find the best model for your images (recommended)
python comprehensive_test.py tests/test_files/images

# 5. Process your first media collection
python workflow.py path/to/your/media/files
```

#### 🎯 Use Cases

**Media Collection Processing**
- Family photo organization with automatic descriptions
- Digital asset management with searchable descriptions
- Content creation workflow automation
- Accessibility enhancement for visual content

**Development & Research**
- AI model comparison and evaluation
- Prompt engineering and optimization
- Performance benchmarking and analysis
- Custom workflow development

**Professional Applications**
- Content management systems integration
- Digital archives and libraries
- Media production workflows
- Accessibility compliance projects

#### 🔮 Future Roadmap

This 1.0 release establishes a solid foundation for future enhancements including:
- Additional AI model integrations
- Enhanced prompt engineering capabilities
- Advanced filtering and search features
- API development for integration projects
- Performance optimizations and scaling improvements

---

**Full Changelog**: https://github.com/kellylford/Image-Description-Toolkit/commits/v1.0.0
