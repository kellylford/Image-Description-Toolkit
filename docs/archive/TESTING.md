# Testing Guide for Image Description Toolkit

## Overview

IDT has a comprehensive testing system using pytest with unit, integration, and smoke tests. Tests are organized to run quickly in CI/CD and catch regressions before deployment.

## Test Structure

```
pytest_tests/
├── conftest.py              # Shared fixtures and configuration
├── unit/                    # Fast tests, no dependencies
│   ├── test_metadata_safety.py
│   ├── test_workflow_config.py
│   ├── test_sanitization.py
│   └── test_status_log.py
├── integration/            # Slow tests, real operations
│   ├── test_exif_preservation.py
│   └── test_workflow_integration.py
└── smoke/                  # Entry point validation
    └── test_entry_points.py
```

## Test Categories

### Unit Tests (Fast)
**Purpose**: Test individual functions and logic without dependencies  
**Run time**: < 1 second per test  
**Dependencies**: None (uses mocks)

**Current coverage**:
- Format string injection safety (@pytest.mark.regression)
- Config file I/O and race conditions
- Input sanitization functions
- Status logging utilities

**When to run**: Every commit, before pushing code

### Integration Tests (Slow)
**Purpose**: Test full workflows with real file operations  
**Run time**: 1-10 seconds per test  
**Dependencies**: Test images, temporary directories, PIL/piexif

**Current coverage**:
- EXIF preservation through image optimization pipeline
- GPS coordinate accuracy after conversion
- End-to-end workflow execution (convert → describe → parse)
- Video frame source tracking

**When to run**: Before releases, after significant changes

### Smoke Tests (Quick Validation)
**Purpose**: Verify applications launch without crashing  
**Run time**: < 5 seconds total  
**Dependencies**: Built executables (frozen mode)

**Current coverage**:
- CLI entry points (idt.exe)
- GUI launches (viewer, imagedescriber, etc.)

**When to run**: After building executables

## Running Tests

### All Tests
```bash
pytest pytest_tests -v
```

### By Category
```bash
# Unit tests only (fast)
pytest pytest_tests/unit -v

# Integration tests only (slow)
pytest pytest_tests/integration -v

# Smoke tests only
pytest pytest_tests/smoke -v
```

### By Marker
```bash
# Only regression tests (for known bugs)
pytest pytest_tests -m regression -v

# Skip slow tests
pytest pytest_tests -m "not slow" -v
```

### With Coverage
```bash
# Coverage report in terminal
pytest pytest_tests --cov=scripts --cov-report=term-missing

# HTML coverage report
pytest pytest_tests --cov=scripts --cov-report=html
# Opens in browser: htmlcov/index.html
```

### Specific Test File
```bash
pytest pytest_tests/integration/test_exif_preservation.py -v
```

### Specific Test Function
```bash
pytest pytest_tests/integration/test_exif_preservation.py::test_exif_preserved_through_quality_reduction -v
```

## Test Markers

Defined in `pyproject.toml`:

- `@pytest.mark.unit` - Unit tests (fast, no dependencies)
- `@pytest.mark.integration` - Integration tests (slow, real operations)
- `@pytest.mark.slow` - Tests taking >1 second
- `@pytest.mark.regression` - Tests for specific bug fixes (should never fail)

**Usage**:
```python
@pytest.mark.regression
@pytest.mark.unit
def test_format_string_safety():
    """Test that format strings don't cause KeyError with user data."""
    # Test implementation
```

## Shared Fixtures

Available to all tests via `pytest_tests/conftest.py`:

- `project_root_path` - Path to project root directory
- `scripts_path` - Path to scripts/ directory
- `test_fixtures_path` - Path to test fixtures
- `temp_workflow_dir` - Temporary workflow directory structure
- `mock_args` - Mock command-line arguments object

**Usage**:
```python
def test_something(temp_workflow_dir):
    """Test using temporary workflow directory."""
    assert temp_workflow_dir.exists()
    # Test implementation
```

## Writing New Tests

### Unit Test Template
```python
"""Test module description."""

import pytest

@pytest.mark.unit
def test_function_name():
    """Test description explaining what is tested."""
    # Arrange
    input_data = "test data"
    
    # Act
    result = function_to_test(input_data)
    
    # Assert
    assert result == expected_value
```

### Integration Test Template
```python
"""Integration test module description."""

import pytest
from pathlib import Path

@pytest.mark.integration
def test_workflow_step(tmp_path):
    """Test description explaining workflow step."""
    # Arrange - Create test files
    test_image = tmp_path / "test.jpg"
    # ... create test image with EXIF
    
    # Act - Run workflow step
    result = workflow_function(test_image)
    
    # Assert - Verify results
    assert result.exists()
    # ... verify EXIF, content, etc.
```

### Regression Test Template
```python
"""Regression test for bug #123."""

import pytest

@pytest.mark.regression
@pytest.mark.unit
def test_bug_123_format_string():
    """
    Regression test for format string bug.
    
    Bug: User EXIF data with {} characters caused KeyError.
    Fix: Use % formatting instead of .format()
    """
    # Test implementation ensuring bug doesn't reoccur
```

## Test Data

### Creating Test Images
```python
from PIL import Image
import piexif

def create_test_image_with_exif(output_path, width=1000, height=800):
    """Create a test JPEG with EXIF metadata."""
    # Create image
    img = Image.new('RGB', (width, height), color='blue')
    
    # Create EXIF data
    exif_dict = {
        "0th": {
            piexif.ImageIFD.Make: "Test Camera",
            piexif.ImageIFD.Model: "Test Model",
        },
        "Exif": {
            piexif.ExifIFD.DateTimeOriginal: "2025:10:29 12:00:00",
        },
        "GPS": {
            piexif.GPSIFD.GPSLatitude: ((42, 1), (21, 1), (36, 1)),
            piexif.GPSIFD.GPSLatitudeRef: 'N',
        }
    }
    
    exif_bytes = piexif.dump(exif_dict)
    img.save(output_path, "JPEG", exif=exif_bytes)
```

### Test Image Sizes
- **Small**: < 1MB (no optimization needed)
- **Medium**: 1-3MB (quality reduction needed)
- **Large**: > 5MB (aggressive resize needed)

## CI/CD Integration

### GitHub Actions (Planned)
See `docs/WorkTracking/ISSUE-automated-testing-cicd.md` for full roadmap.

**Phase 2** (GitHub cloud runners):
- Syntax checking (pyflakes, flake8)
- Import validation
- Unit tests
- Build verification

**Phase 3** (Self-hosted runner):
- Integration tests with real images
- Full workflow validation
- Ollama model inference tests
- Executable smoke tests

### Pre-Commit Checklist
Before committing code:
1. Run unit tests: `pytest pytest_tests/unit -v`
2. Run affected integration tests
3. Check syntax: `python -m py_compile scripts/your_file.py`
4. Run regression tests: `pytest -m regression -v`

### Pre-Release Checklist
Before creating a release:
1. Run full test suite: `pytest pytest_tests -v`
2. Run with coverage: `pytest pytest_tests --cov=scripts`
3. Build all executables: `BuildAndRelease\builditall.bat`
4. Run smoke tests on built executables
5. Manually test critical workflows

## Troubleshooting Tests

### ImportError: No module named 'scripts'
**Solution**: Run from project root, not from `pytest_tests/` directory.
```bash
# Wrong
cd pytest_tests && pytest .

# Right
pytest pytest_tests
```

### PIL/Pillow Import Warnings
**Expected**: Integration tests use PIL for EXIF manipulation.  
**Action**: Ignore import warnings during test execution.

### Test Fails Only in CI
**Check**:
- Path resolution (frozen vs dev mode)
- Environment variables
- Temporary directory permissions
- Dependencies installed correctly

### Tests Pass But Bug Exists
**Common causes**:
- Test data doesn't match real-world data
- Test uses mocks that don't reflect actual behavior
- Test coverage gap (add integration test)
- Race condition not reproduced in test

## Coverage Goals

- **Unit Tests**: 60%+ coverage of core functions
- **Integration Tests**: Critical workflows fully tested
- **Regression Tests**: Every fixed bug has a test

**Current priority**: Image processing pipeline (conversion, EXIF, optimization)

## Known Testing Gaps

As of 2025-10-29:

- ✅ Format string safety (covered)
- ✅ Config file race conditions (covered)
- ✅ EXIF preservation (NEW - added today)
- ⏳ Geocoding API integration (planned)
- ⏳ AI model inference (needs self-hosted runner)
- ⏳ GUI automation (PyQt6 testing)
- ⏳ Performance benchmarks (timing, memory)

## References

- **pytest docs**: https://docs.pytest.org/
- **Coverage.py**: https://coverage.readthedocs.io/
- **CI/CD Roadmap**: `docs/WorkTracking/ISSUE-automated-testing-cicd.md`
- **Test configuration**: `pyproject.toml`

---

**Questions?** See CI/CD roadmap issue or ask in session summaries.
