"""
Shared test fixtures and utilities for the Image Description Toolkit test suite.

This module provides reusable pytest fixtures and helper functions to avoid
duplication across test files.
"""

import pytest
from pathlib import Path
from PIL import Image
import piexif
import json
from datetime import datetime
from typing import Optional, Dict, Any


@pytest.fixture
def test_image_with_exif(tmp_path) -> Path:
    """
    Create a test image with realistic EXIF data.
    
    Returns:
        Path to the created test image
    """
    image_path = tmp_path / "test_image.jpg"
    
    exif_dict = {
        "0th": {
            piexif.ImageIFD.Make: b"Apple",
            piexif.ImageIFD.Model: b"iPhone 15 Pro",
            piexif.ImageIFD.DateTime: b"2024:10:29 08:30:00",
        },
        "Exif": {
            piexif.ExifIFD.DateTimeOriginal: b"2024:10:29 08:30:00",
            piexif.ExifIFD.DateTimeDigitized: b"2024:10:29 08:30:00",
        },
        "GPS": {
            piexif.GPSIFD.GPSLatitudeRef: b"N",
            piexif.GPSIFD.GPSLatitude: ((43, 1), (4, 1), (20, 1)),
            piexif.GPSIFD.GPSLongitudeRef: b"W",
            piexif.GPSIFD.GPSLongitude: ((89, 1), (23, 1), (45, 1)),
        },
    }
    
    exif_bytes = piexif.dump(exif_dict)
    img = Image.new('RGB', (800, 600), color=(100, 150, 200))
    img.save(image_path, 'JPEG', quality=95, exif=exif_bytes)
    
    return image_path


@pytest.fixture
def test_image_large(tmp_path) -> Path:
    """
    Create a large test image for testing size optimization.
    
    Returns:
        Path to the created large test image
    """
    image_path = tmp_path / "large_image.jpg"
    
    # Create a large image that will trigger optimization
    img = Image.new('RGB', (4000, 3000), color=(100, 150, 200))
    img.save(image_path, 'JPEG', quality=100)
    
    return image_path


@pytest.fixture
def test_image_no_exif(tmp_path) -> Path:
    """
    Create a test image without EXIF data.
    
    Returns:
        Path to the created test image
    """
    image_path = tmp_path / "no_exif_image.png"
    img = Image.new('RGB', (800, 600), color=(200, 100, 150))
    img.save(image_path, 'PNG')
    
    return image_path


@pytest.fixture
def mock_ai_provider():
    """
    Mock AI provider for testing without API calls.
    
    Returns:
        MockProvider instance that tracks calls and returns test responses
    """
    class MockProvider:
        def __init__(self):
            self.calls = []
            self.response = "A test description of the image."
        
        def describe_image(self, image_path, prompt):
            """Mock description method"""
            self.calls.append({'image': str(image_path), 'prompt': prompt})
            return self.response
        
        def is_available(self):
            """Mock availability check"""
            return True
        
        def get_model_name(self):
            """Mock model name"""
            return "mock-model"
        
        def set_response(self, response: str):
            """Set the response for next call"""
            self.response = response
    
    return MockProvider()


@pytest.fixture
def sample_workflow_directory(tmp_path, test_image_with_exif) -> Path:
    """
    Create a complete workflow directory structure with sample data.
    
    Returns:
        Path to the workflow directory
    """
    workflow_dir = tmp_path / "wf_test_model_narrative_20241029_083000"
    workflow_dir.mkdir()
    
    # Create subdirectories
    (workflow_dir / "converted_images").mkdir()
    (workflow_dir / "descriptions").mkdir()
    (workflow_dir / "html_reports").mkdir()
    (workflow_dir / "logs").mkdir()
    
    # Add sample image
    import shutil
    dest_image = workflow_dir / "converted_images" / "image1.jpg"
    shutil.copy(test_image_with_exif, dest_image)
    
    # Add sample description
    desc_file = workflow_dir / "descriptions" / "image1.txt"
    desc_file.write_text("""File: image1.jpg
Date: 2024-10-29 08:30:00
Camera: iPhone 15 Pro
Location: Madison, Wisconsin

Description:
A test description of the image showing sample content.
""")
    
    # Add workflow metadata
    metadata_file = workflow_dir / "workflow_metadata.json"
    metadata = {
        "timestamp": "2024-10-29 08:30:00",
        "model": "test-model",
        "prompt_style": "narrative",
        "steps_completed": ["extract", "convert", "describe", "html"]
    }
    metadata_file.write_text(json.dumps(metadata, indent=2))
    
    return workflow_dir


@pytest.fixture
def sample_config_file(tmp_path) -> Path:
    """
    Create a sample workflow configuration file.
    
    Returns:
        Path to the config file
    """
    config_path = tmp_path / "test_workflow_config.json"
    config = {
        "default_model": "llava:7b",
        "default_prompt_style": "narrative",
        "default_steps": ["all"],
        "timeout": 300,
        "max_workers": 4
    }
    config_path.write_text(json.dumps(config, indent=2))
    return config_path


@pytest.fixture
def sample_description_files(tmp_path) -> Path:
    """
    Create a directory with sample description files.
    
    Returns:
        Path to the descriptions directory
    """
    desc_dir = tmp_path / "descriptions"
    desc_dir.mkdir()
    
    # Create multiple sample descriptions
    for i in range(3):
        desc_file = desc_dir / f"image{i+1}.txt"
        desc_file.write_text(f"""File: image{i+1}.jpg
Date: 2024-10-{29+i:02d} 08:30:00
Camera: iPhone 15 Pro
Location: Test Location {i+1}

Description:
Test description {i+1} with sample content showing various elements.
This is a longer description to test text handling.
""")
    
    return desc_dir


def create_test_image_with_size(path: Path, width: int, height: int, 
                                quality: int = 95, exif: bool = True) -> Path:
    """
    Helper function to create a test image with specific dimensions.
    
    Args:
        path: Output path for the image
        width: Image width in pixels
        height: Image height in pixels
        quality: JPEG quality (1-100)
        exif: Whether to include EXIF data
    
    Returns:
        Path to the created image
    """
    img = Image.new('RGB', (width, height), color=(100, 150, 200))
    
    if exif:
        exif_dict = {
            "0th": {
                piexif.ImageIFD.Make: b"Test Camera",
                piexif.ImageIFD.Model: b"Test Model",
            },
            "Exif": {
                piexif.ExifIFD.DateTimeOriginal: b"2024:10:29 08:30:00",
            }
        }
        exif_bytes = piexif.dump(exif_dict)
        img.save(path, 'JPEG', quality=quality, exif=exif_bytes)
    else:
        img.save(path, 'JPEG', quality=quality)
    
    return path


def verify_exif_preserved(image_path: Path, expected_make: str = None, 
                          expected_model: str = None) -> bool:
    """
    Helper function to verify EXIF data is present in an image.
    
    Args:
        image_path: Path to the image to check
        expected_make: Expected camera make (optional)
        expected_model: Expected camera model (optional)
    
    Returns:
        True if EXIF data is present and matches expectations
    """
    try:
        img = Image.open(image_path)
        exif_dict = piexif.load(img.info.get('exif', b''))
        
        # Check that EXIF data exists
        if not exif_dict or not exif_dict.get('0th'):
            return False
        
        # Check specific fields if requested
        if expected_make:
            actual_make = exif_dict['0th'].get(piexif.ImageIFD.Make, b'').decode()
            if actual_make != expected_make:
                return False
        
        if expected_model:
            actual_model = exif_dict['0th'].get(piexif.ImageIFD.Model, b'').decode()
            if actual_model != expected_model:
                return False
        
        return True
        
    except Exception as e:
        print(f"Error checking EXIF: {e}")
        return False


def count_files_in_directory(directory: Path, pattern: str = "*") -> int:
    """
    Helper function to count files matching a pattern in a directory.
    
    Args:
        directory: Directory to search
        pattern: Glob pattern (default: all files)
    
    Returns:
        Number of matching files
    """
    if not directory.exists():
        return 0
    return len(list(directory.glob(pattern)))


def find_workflow_directory(output_dir: Path) -> Optional[Path]:
    """
    Helper function to find the workflow directory (wf_*) in an output directory.
    
    Args:
        output_dir: Output directory to search
    
    Returns:
        Path to workflow directory, or None if not found
    """
    workflow_dirs = list(output_dir.glob("wf_*"))
    return workflow_dirs[0] if workflow_dirs else None


@pytest.fixture
def project_root() -> Path:
    """
    Get the project root directory.
    
    Returns:
        Path to the project root
    """
    return Path(__file__).parent.parent


@pytest.fixture
def test_data_dir(project_root) -> Path:
    """
    Get the test_data directory.
    
    Returns:
        Path to test_data directory
    """
    return project_root / "test_data"


@pytest.fixture
def dist_dir(project_root) -> Path:
    """
    Get the dist directory where executables are built.
    
    Returns:
        Path to dist directory
    """
    return project_root / "dist"
