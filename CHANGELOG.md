## [4.1.0] - 2026-01-14

### ✨ Major Updates

**wxPython GUI Migration Complete**
- **Replaced PyQt6 with wxPython**: Cross-platform compatibility (Windows, macOS) improved
- **Enhanced accessibility**: Full WCAG 2.2 AA compliance with screen reader support
- **Improved VoiceOver/NVDA**: Better keyboard navigation and accessible widget implementations
- **Streamlined GUIs**: Simplified interface while maintaining all functionality

**Code Quality Improvements**
- **Eliminated code duplication**: ~190 lines of duplicate code consolidated into shared modules
- **Created 114+ unit tests**: Comprehensive test coverage with 100% pass rate
- **3 new shared utility modules**: `utility_functions.py`, `exif_utils.py`, `window_title_builder.py`
- **Improved frozen mode support**: PyInstaller compatibility validated across all applications

### 🔧 Critical Bug Fixes (31+ Issues)

**Frozen Mode Compatibility (24 CRITICAL)**
- Fixed hardcoded frozen mode checks throughout codebase
- Fixed config file path resolution in frozen executables
- Fixed JSON file loading in frozen mode
- Fixed resource path resolution for PyInstaller bundles
- Enhanced fallback patterns for dev/frozen modes

**Code Quality (7 HIGH)**
- Consolidated EXIF extraction (4 implementations → 1 shared module)
- Consolidated window title building (2 implementations → 1 shared module)
- Removed duplicate utility functions
- Fixed import patterns across all applications
- Improved error handling and logging

### 📦 Build System Enhancements

**Executable Quality**
- All 3 applications build successfully with zero errors
- PyInstaller spec files optimized and verified
- Shared modules properly bundled in all executables
- Configuration files correctly embedded

**Build Artifacts** (Updated v4.2.0)
- `idt.exe` - CLI dispatcher, fully functional
- `Viewer.exe` - Workflow results browser
- `ImageDescriber.exe` - Batch processing GUI with integrated prompt editor and configuration manager (formerly 5 apps, now 3)

### ✅ Testing & Validation

**Comprehensive Testing**
- All 114+ unit tests passing (100% pass rate)
- Code quality review - EXCELLENT across all metrics
- Build testing - All 3 executables compile successfully
- Integration testing - All imports validated
- Frozen mode testing - PyInstaller compatibility verified

**Zero Regressions**
- 100% backward compatibility maintained
- No breaking changes introduced
- All existing workflows continue to work
- All configuration files compatible

### 📚 Documentation Updates

**User Guides**
- Updated installation instructions
- Documented new accessibility features
- Enhanced configuration guide
- Added wxPython-specific notes

**Developer Documentation**
- Documented shared utility modules
- Added frozen mode guidelines
- Updated import patterns documentation
- Included testing methodology

### 🎯 Performance Optimizations

**Code Consolidation Benefits**
- Reduced memory footprint from duplicate code
- Improved maintainability with single source of truth
- Faster development and bug fixes
- Better error handling consistency

**Expected Improvements**
- Startup time: Consolidated code improves efficiency
- Memory usage: Reduced code size in executables
- Maintainability: Single implementations easier to maintain
- Reliability: Consistent behavior across all apps

### ⚙️ Internal Improvements

**Codebase Quality**
- Zero syntax errors in all files
- All imports properly validated
- Comprehensive error handling
- Professional code organization

**Build System**
- Automated build verification
- Consistent PyInstaller configuration
- Optimized spec files
- Streamlined build process

**Repository Management**
- Clean repository structure
- Organized documentation
- Archived deprecated files
- Current status clearly documented

---

## [3.6.0] - 2025-12-04

### 🎯 Major Features

**HuggingFace Provider with Florence-2 Models**
- **Local AI vision models**: Microsoft Florence-2-base and Florence-2-large models
- **Self-contained**: No need to install Ollama or external AI servers
- **Zero cost**: No API keys, no cloud costs
- **Privacy-focused**: All processing happens locally on your hardware
- **Three prompt styles**: Simple, Technical, and Narrative descriptions
- **CLI-only in GUI installer**: Available via command-line to keep installer size reasonable (~100MB vs ~2GB)
- **Comprehensive documentation**: See [HUGGINGFACE_PROVIDER_GUIDE.md](docs/HUGGINGFACE_PROVIDER_GUIDE.md)

**Note**: HuggingFace provider is **not available in ImageDescriber GUI** to avoid bundling 2GB of transformers/PyTorch dependencies. Use CLI commands instead:
```bash
idt describe image.jpg --provider huggingface --model microsoft/Florence-2-base
idt workflow --provider huggingface --model microsoft/Florence-2-base
```

**Redescribe Feature - Workflow Reuse**
- **Re-describe with different AI**: Test multiple models/prompts on identical images
- **Efficient image reuse**: Hardlinks, symlinks, or copy - reuses extracted frames and converted images
- **Model comparison**: Compare Ollama, OpenAI, Claude, and HuggingFace outputs side-by-side
- **Workflow metadata**: Tracks original settings and changes for traceability
- **Design documentation**: [redescribe-feature-design.md](docs/WorkTracking/redescribe-feature-design.md)
- **Example**: `idt workflow --redescribe wf_photos_ollama_llava --provider huggingface --model microsoft/Florence-2-base`

---

## [4.0.0] - 2025-11-18

### ⚠️ Note
This version introduced Florence-2 support under the "ONNX" provider name, which was renamed to "HuggingFace" in v3.6.0 for accuracy.

### 🎯 Major Features

**HuggingFace Provider with Florence-2 Models** (originally named "ONNX" in this version)
- **CPU-only AI vision models**: Microsoft Florence-2-base and Florence-2-large models
- **No GPU required**: Production-ready transformers library execution on any CPU
- **Three prompt styles**: Simple (8 words), Technical (40+ words), Narrative (70+ words)
- **Comprehensive documentation**: See [HUGGINGFACE_PROVIDER_GUIDE.md](docs/HUGGINGFACE_PROVIDER_GUIDE.md)
- **Performance benchmarking**: 8.63s to 145.16s per image depending on model/prompt
- **Production tested**: Validated on 1000+ image workflows

**Redescribe Feature - Workflow Reuse**
- **Re-describe with different AI**: Test multiple models/prompts on identical images
- **Efficient image reuse**: Hardlinks, symlinks, or copy - reuses extracted frames and converted images
- **Model comparison**: Compare Ollama, OpenAI, Claude, and HuggingFace outputs side-by-side
- **Workflow metadata**: Tracks original settings and changes for traceability
- **Design documentation**: [redescribe-feature-design.md](docs/WorkTracking/redescribe-feature-design.md)
- **Example**: `idt workflow --redescribe wf_photos_ollama_llava --provider huggingface --model microsoft/Florence-2-base`

### ��� Critical Bug Fixes

**File Discovery**
- **Fixed uppercase extension handling**: Now correctly finds .PNG, .HEIC, .MOV files (not just lowercase)
- **Impact**: Workflows were missing images with uppercase extensions
- **Root cause**: Windows filesystems can be case-sensitive in some contexts (WSL, network shares)

**Workflow Duplication Prevention**
- **Fixed massive duplication bug**: Workflows were creating 2817 descriptions instead of 1793 (1.6x duplication)
- **Root cause**: Describe step was scanning converted_images/ as a source directory
- **Solution**: Added safety check to skip workflow subdirectories, corrected input directory handling

**Path Resolution**
- **Fixed redescribe WinError 32**: Resolved path comparison failure with relative vs absolute paths
- **Impact**: Redescribe mode failed with "file in use" error
- **Solution**: Use Path().resolve() for absolute path comparison before workflow mode detection

### ���️ Build & Quality Improvements

**Build System**
- **PyInstaller cache cleaning**: All build scripts now clean cache to prevent stale code issues
- **Pre-build validation**: New tools/pre_build_validation.py validates code before building
- **Build reliability**: Significantly reduced "works in dev but not in executable" issues

**Testing**
- **Integration tests**: New test_workflow_file_types.py validates video/image/HEIC handling
- **Unit tests**: New test_workflow_redescribe.py (348 lines) for redescribe feature
- **Total new test coverage**: 529 lines across 3 new test files

**Code Quality**
- **Pre-commit hook**: tools/pre-commit-hook.sh for validation before commits
- **UTF-8 enforcement**: Consistent encoding across all build and validation scripts
- **Better error messages**: Enhanced logging throughout workflow orchestration

### ��� Documentation

**New Documentation**
- **ONNX Provider Guide**: 213-line comprehensive guide with examples and benchmarks
- **Redescribe Design Doc**: 626-line design document with implementation details
- **Florence-2 Analysis**: Performance and quality comparison across 6 model configurations
- **DirectML Experiments**: GPU acceleration research and findings

### ��� Other Improvements

**Workflow Enhancements**
- **Preserve frame subdirectories**: Video frame extraction maintains original structure
- **Enhanced metadata**: Save original (unsanitized) model names in workflow metadata
- **Resume improvements**: Better provider detection when resuming interrupted workflows
- **Guided workflow**: Enhanced Florence-2 model support in interactive mode

**Configuration**
- **Better config loading**: More robust path resolution for PyInstaller executables
- **Command logging**: --provider logged in original command for accurate resume

### ��� Dependencies

**New Dependencies**
- `optimum[onnxruntime]>=1.23.3` - ONNX model optimization
- `onnxruntime>=1.20.1` - ONNX Runtime for model execution
- `transformers>=4.47.1` - Hugging Face transformers for Florence-2
- `torch>=2.5.1` - PyTorch backend for model loading
- Plus 8 additional supporting packages

**Note**: Total installation size increases by ~2-3 GB with PyTorch and ONNX Runtime

### ⚠️ Breaking Changes

None - all changes are backward compatible

### ��� Performance

**Florence-2 Benchmarks** (per image, 5 test images):
- Florence-2-base + Simple: 8.63s (fastest)
- Florence-2-base + Technical: 26.09s (balanced)
- Florence-2-base + Narrative: 73.59s
- Florence-2-large + Simple: 23.81s
- Florence-2-large + Technical: 56.44s
- Florence-2-large + Narrative: 145.16s (highest quality)
- Moondream + Narrative: 17.29s (best quality-per-second)

**Key Finding**: Prompt complexity has 6-8x more impact on speed than model size (2-3x)

### ��� Testing Credits

Extensive testing and bug discovery by Kelly Ford across:
- 6 Florence-2 model configurations
- Case-insensitive file handling validation
- Large-scale duplication detection (1793 image workflow)
- Redescribe feature validation
- Cross-model quality comparison

---

# Changelog

All notable changes to the Image Description Toolkit will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.5.0] - 2025-11-11

### 🌐 New Features

**Web Image Download**
- **Download images from websites**: Process images directly from URLs without manual downloading
- **Simplified interface**: Just use `idt workflow example.com` to download and describe images from any website
- **Smart URL detection**: Automatically recognizes URLs and configures the correct workflow steps
- **BeautifulSoup4 HTML parsing**: Extracts images from `<img>` tags, `<picture>` elements, and direct links
- **Duplicate detection**: MD5 content hashing prevents downloading the same image multiple times
- **Progress tracking**: Real-time progress updates with formatted console output
- **Filtering options**: `--max-images` to limit download count
- **Safe filenames**: Automatically sanitizes filenames for cross-platform compatibility
- **Image validation**: Verifies downloaded files are valid images using PIL/Pillow
- **Rate limiting**: Respectful 0.5s delays between downloads to avoid overwhelming servers

### 📚 Documentation

**New Web Download Guide**
- **[WEB_DOWNLOAD_GUIDE.md](docs/WEB_DOWNLOAD_GUIDE.md)** - Complete guide to downloading images from websites
- Usage examples with various workflow configurations
- Technical details on supported formats and validation
- Troubleshooting section for common issues
- Limitations and legal considerations

**Enhanced User Guide**
- Added web download examples and use cases
- Simplified workflow syntax examples: `idt workflow mywebsite.com`
- Auto-detection behavior documentation

**Updated CLI Reference**
- Complete `--url` parameter documentation
- Web download workflow examples
- Integration with existing workflow steps

### 🔧 Bug Fixes

**Resume Mode**
- Fixed `UnboundLocalError` for `workflow_name_display` variable in `--resume` mode
- Corrected initialization in both code paths (metadata file and directory name fallback)
- Enhanced error handling for resume workflows

### 🛠️ Technical Details

**Dependencies**
- Added `beautifulsoup4>=4.9.0` for HTML parsing
- Updated PyInstaller spec with BeautifulSoup4 support (`collect_all`, hidden imports)
- Maintained backward compatibility with existing requirements

**Build System**
- Updated `final_working.spec` with BeautifulSoup4 data collection
- Tested with both Python development mode and PyInstaller frozen executable
- Verified resource path resolution in both modes

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
