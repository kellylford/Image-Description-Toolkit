# Requirements Files Consolidation

## Overview
Consolidated multiple requirements files into a single, comprehensive `requirements.txt` file for better maintainability and user experience.

## Changes Made

### Files Removed
- `workflow_requirements.txt` (redundant)
- `VideoFrameExtractorRequirements.txt` (redundant)

### Files Updated
- `requirements.txt` - Now contains all dependencies for the complete toolkit

## Consolidated Dependencies

The new `requirements.txt` includes all dependencies needed for:

### Core Functionality
- `ollama>=0.3.0` - AI vision model interface
- `requests>=2.31.0` - HTTP requests
- `Pillow>=10.0.0` - Image processing

### Image Format Support
- `pillow-heif>=0.13.0` - HEIC/HEIF conversion support

### Video Processing
- `opencv-python>=4.8.0` - Video frame extraction
- `numpy>=1.24.0` - Numerical operations

### Compatibility & Utilities
- `typing-extensions>=4.0.0` - Type hints for older Python versions
- `pathlib2>=2.3.5` - Path handling for older Python versions

### Optional Features
- `tqdm>=4.60.0` - Progress bars
- `pytest>=6.0.0` - Testing framework
- `pytest-mock>=3.6.0` - Testing utilities

## Installation

Users now only need to run:
```bash
pip install -r requirements.txt
```

This single command installs everything needed for:
- ✅ Image description (`image_describer.py`)
- ✅ Video frame extraction (`video_frame_extractor.py`)
- ✅ HEIC conversion (`ConvertImage.py`)
- ✅ HTML report generation (`descriptions_to_html.py`)
- ✅ Complete workflow system (`workflow.py`)

## Documentation Updated

All references to multiple requirements files have been updated in:
- `README.md`
- `WORKFLOW_README.md`
- `IMPLEMENTATION_SUMMARY.md`
- `test_workflow.py`
- `demo_workflow.py`

## Benefits

1. **Simplified Installation**: Single command installs everything
2. **No Version Conflicts**: Consistent dependency versions across all tools
3. **Easier Maintenance**: One file to update instead of three
4. **Better User Experience**: No confusion about which requirements file to use
5. **Comprehensive Coverage**: All functionality available with one installation
