# Python Packaging Setup for Image Description Toolkit

This document explains the Python packaging setup that has been implemented for the Image Description Toolkit.

## Package Structure

The repository has been restructured to support proper Python packaging:

```
Image-Description-Toolkit/
├── image_description_toolkit/          # Main Python package
│   ├── __init__.py                    # Package initialization and exports
│   ├── workflow.py                    # Main workflow orchestrator
│   ├── image_describer.py             # AI image description functionality  
│   ├── video_frame_extractor.py       # Video frame extraction
│   ├── convert_image.py               # HEIC to JPG conversion
│   ├── descriptions_to_html.py        # HTML report generation
│   ├── workflow_utils.py              # Workflow utilities
│   └── *.json                         # Configuration files
├── pyproject.toml                     # PEP 517 build configuration
├── setup.py                          # Setuptools configuration (backup)
├── MANIFEST.in                        # Package file inclusion rules
├── requirements.txt                   # Project dependencies
├── workflow.py                        # Legacy entry point (maintained for compatibility)
├── .github/workflows/build-and-test.yml  # CI/CD automation
└── test_packaging.py                  # Package testing script
```

## Installation Options

### From Source (Development)
```bash
# Clone the repository
git clone https://github.com/kellylford/Image-Description-Toolkit.git
cd Image-Description-Toolkit

# Install in editable mode
pip install -e .

# Or install dependencies manually
pip install -r requirements.txt
```

### From Built Package
```bash
# Build the package
python -m build

# Install from wheel
pip install dist/image_description_toolkit-0.1.0-py3-none-any.whl
```

## Package Features

### Console Script Entry Point
After installation, the toolkit is available as a console command:
```bash
image-description-toolkit --help
image-description-toolkit /path/to/media --output-dir results
```

### Python API Access
```python
# Import the main workflow
from image_description_toolkit.workflow import main as workflow_main

# Import individual components
from image_description_toolkit import (
    ImageDescriber,
    VideoFrameExtractor, 
    convert_heic_to_jpg,
    get_default_prompt_style
)

# Use the workflow programmatically
import sys
sys.argv = ['workflow', '/path/to/media', '--steps', 'describe,html']
workflow_main()
```

## Build Configuration

### pyproject.toml (PEP 517)
- Uses setuptools as build backend
- Defines package metadata and dependencies
- Configures console script entry points
- Includes package data (JSON configuration files)

### Dependencies
All dependencies are specified in `requirements.txt` and automatically included:
- `ollama>=0.3.0` - AI model interface
- `Pillow>=10.0.0` - Image processing
- `opencv-python>=4.8.0` - Video processing
- `numpy>=1.24.0` - Numerical computations
- Plus additional utilities and development dependencies

## GitHub Actions CI/CD

The `.github/workflows/build-and-test.yml` workflow:
- Tests on Python 3.8-3.12
- Verifies package imports and functionality
- Builds source and wheel distributions
- Tests installation in clean environments
- Validates console script entry points

## Testing

### Package Functionality Test
```bash
python test_packaging.py
```
This script verifies:
- Package imports work correctly
- Metadata is accessible
- Configuration files are included
- Classes can be instantiated
- Workflow help system functions

### Manual Testing
```bash
# Test package imports
python -c "import image_description_toolkit; print('Success!')"

# Test workflow entry point
python -c "from image_description_toolkit.workflow import main; main()" --help

# Test console script (after installation)
image-description-toolkit --help
```

## Backwards Compatibility

The original `workflow.py` entry point is maintained for compatibility:
```bash
# Still works as before
python workflow.py /path/to/media
```

## Package Distribution

### Building Packages
```bash
# Install build tools
pip install build

# Build source and wheel distributions
python -m build

# Build with setuptools directly (alternative)
python setup.py sdist bdist_wheel
```

### Distribution Files
- Source distribution: `image-description-toolkit-0.1.0.tar.gz`
- Wheel distribution: `image_description_toolkit-0.1.0-py3-none-any.whl`

## Configuration

Package-level configuration files are included in the distribution:
- `workflow_config.json` - Main workflow settings
- `image_describer_config.json` - AI model configuration
- `video_frame_extractor_config.json` - Video processing settings

These files are automatically accessible to the package components and can be customized after installation.

## Development Workflow

1. Make changes to the code in `image_description_toolkit/`
2. Test changes: `python test_packaging.py`
3. Build package: `python -m build`
4. Test installation: `pip install dist/*.whl`
5. Verify functionality: `image-description-toolkit --help`

The packaging setup ensures that all functionality remains available while providing standard Python packaging and distribution capabilities.