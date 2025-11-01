"""
Pytest configuration and shared fixtures for IDT test suite.

This file contains fixtures that are available to all tests.
"""

import sys
from pathlib import Path
import pytest

# Add project root to Python path so tests can import from scripts/
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Add pytest_tests to path for test_helpers
sys.path.insert(0, str(Path(__file__).parent))

# Import fixtures from test_helpers to make them available globally
try:
    from test_helpers import (
        test_image_with_exif,
        test_image_large,
        test_image_no_exif,
        mock_ai_provider,
        sample_workflow_directory,
        sample_config_file,
        sample_description_files,
        project_root,
        test_data_dir,
        dist_dir,
        create_test_image_with_size,
        verify_exif_preserved,
        count_files_in_directory,
        find_workflow_directory,
    )
except ImportError as e:
    # If test_helpers not available, define minimal fixtures
    print(f"Warning: Could not import test_helpers: {e}")
    
    @pytest.fixture
    def project_root():
        return Path(__file__).parent.parent
    
    @pytest.fixture
    def test_data_dir(project_root):
        return project_root / "test_data"
    
    @pytest.fixture
    def dist_dir(project_root):
        return project_root / "dist"

@pytest.fixture
def project_root_path():
    """Return the project root directory path."""
    return Path(__file__).parent.parent

@pytest.fixture
def scripts_path(project_root_path):
    """Return the scripts directory path."""
    return project_root_path / "scripts"

@pytest.fixture
def test_fixtures_path():
    """Return the test fixtures directory path."""
    return Path(__file__).parent / "fixtures"

@pytest.fixture
def temp_workflow_dir(tmp_path):
    """Create a temporary workflow directory structure for testing."""
    workflow_dir = tmp_path / "test_workflow"
    workflow_dir.mkdir()
    
    # Create typical subdirectories
    (workflow_dir / "logs").mkdir()
    (workflow_dir / "Descriptions").mkdir()
    (workflow_dir / "converted_images").mkdir()
    
    return workflow_dir

@pytest.fixture
def mock_args():
    """Return a mock args object for testing."""
    class MockArgs:
        def __init__(self, **kwargs):
            # Set defaults
            self.name = None
            self.provider = "ollama"
            self.model = None
            self.config = None
            self.prompt_style = None
            self.output_dir = None
            self.video = False
            self.geocode = False
            self.metadata = False
            
            # Override with provided kwargs
            for key, value in kwargs.items():
                setattr(self, key, value)
    
    return MockArgs
