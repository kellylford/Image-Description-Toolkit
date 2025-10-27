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
