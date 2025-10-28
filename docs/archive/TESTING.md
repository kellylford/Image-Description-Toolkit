# Image Description Toolkit - Testing Guide

## Overview

This document describes the testing strategy and guidelines for the Image Description Toolkit (IDT).

## Test Directory Structure

```
tests/
├── conftest.py              # Shared pytest fixtures and configuration  
├── __init__.py              # Package marker
├── unit/                    # Fast, isolated unit tests
│   ├── test_sanitization.py   # Name sanitization and case preservation
│   └── test_status_log.py     # ASCII-only status output
├── integration/             # Multi-component integration tests
│   └── (coming soon)
└── fixtures/                # Test data and mock responses
```

## Quick Start

### Install Dependencies

```bash
pip install -r requirements.txt
```

This installs pytest, pytest-cov, and pytest-mock.

### Run Tests

```bash
# From project root
pytest

# With verbose output
pytest -v

# With coverage
pytest --cov=scripts --cov-report=html
```

### View Coverage Report

```bash
# Generate HTML coverage report
pytest --cov=scripts --cov-report=html

# Open in browser
# Windows:
start htmlcov/index.html

# Linux/Mac:
open htmlcov/index.html
```

## Test Categories

### Unit Tests (`tests/unit/`)

Fast, isolated tests for individual functions:

- **test_sanitization.py** - Name sanitization (`sanitize_name()`)
  - Tests case preservation with `preserve_case=True`
  - Tests lowercasing with `preserve_case=False`
  - Tests special character handling
  - Tests workflow directory naming
  - **Regression prevention**: Ensures `--name MyRunHasUpperCase` isn't lowercased

- **test_status_log.py** - Status log output formatting
  - Tests ASCII-only symbols (`[ACTIVE]`, `[DONE]`, `[FAILED]`)
  - Tests absence of Unicode symbols (⟳, ✓, ✗, →)
  - Tests screen reader compatibility
  - **Regression prevention**: Ensures no Unicode garbage in status logs

### Integration Tests (`tests/integration/`)

Tests that verify multiple components working together (coming soon):

- Workflow execution end-to-end
- CLI command parsing and execution
- File conversion pipelines
- Metadata extraction and geocoding

### End-to-End Tests

Full pipeline tests on real/realistic data (coming soon):

- Complete workflow with video, HEIC, and JPG files
- HTML gallery generation
- Analysis tools (CombineDescriptions, stats)

## Running Specific Tests

### By File

```bash
pytest tests/unit/test_sanitization.py -v
pytest tests/unit/test_status_log.py -v
```

### By Class

```bash
pytest tests/unit/test_sanitization.py::TestSanitizeName -v
pytest tests/unit/test_status_log.py::TestStatusLogASCIISymbols -v
```

### By Method

```bash
pytest tests/unit/test_sanitization.py::TestSanitizeName::test_sanitize_name_preserves_case_when_requested -v
```

### By Keyword

```bash
# Run all tests with "case" in the name
pytest -k case -v

# Run all tests with "ascii" in the name
pytest -k ascii -v
```

## Writing Tests

### Test Structure

```python
import pytest
from scripts.your_module import your_function

class TestYourFeature:
    """Test your feature description."""
    
    def test_basic_functionality(self):
        """Test that basic case works correctly."""
        result = your_function("input")
        assert result == "expected", "Descriptive error message"
    
    def test_edge_case(self):
        """Test that edge case is handled properly."""
        result = your_function("")
        assert isinstance(result, str), "Should return string even for empty input"
```

### Using Fixtures

Fixtures from `conftest.py` are available to all tests:

```python
def test_with_temp_directory(temp_workflow_dir):
    """Test that uses temporary workflow directory."""
    assert temp_workflow_dir.exists()
    logs_dir = temp_workflow_dir / "logs"
    assert logs_dir.exists()
```

### Custom Fixtures

Add reusable fixtures to `conftest.py`:

```python
@pytest.fixture
def sample_image():
    """Return path to a sample test image."""
    return Path(__file__).parent / "fixtures" / "sample.jpg"
```

## Best Practices

### 1. Name Tests Descriptively

❌ Bad:
```python
def test_name():
    ...
```

✅ Good:
```python
def test_sanitize_name_preserves_case_when_preserve_case_true():
    ...
```

### 2. Test One Thing Per Test

❌ Bad:
```python
def test_everything(self):
    # Tests 10 different things
    assert sanitize_name("A") == "A"
    assert sanitize_name("B") == "B"
    # ... 8 more assertions
```

✅ Good:
```python
def test_preserves_uppercase_letters(self):
    result = sanitize_name("ABC", preserve_case=True)
    assert result == "ABC"

def test_converts_to_lowercase_when_requested(self):
    result = sanitize_name("ABC", preserve_case=False)
    assert result == "abc"
```

### 3. Include Helpful Assertion Messages

❌ Bad:
```python
assert result == expected
```

✅ Good:
```python
assert result == expected, \
    f"sanitize_name should preserve case, got '{result}' instead of '{expected}'"
```

### 4. Test Behavior, Not Implementation

❌ Bad:
```python
def test_uses_regex_to_remove_special_chars(self):
    # Tests how it's implemented
    ...
```

✅ Good:
```python
def test_removes_special_characters_from_name(self):
    # Tests what it does
    result = sanitize_name("Run!@#$Name")
    assert result == "RunName"
```

### 5. Cover Edge Cases

Test the happy path AND edge cases:

```python
def test_handles_empty_string(self):
    result = sanitize_name("")
    assert isinstance(result, str)

def test_handles_only_special_characters(self):
    result = sanitize_name("!@#$%")
    assert isinstance(result, str)

def test_handles_very_long_names(self):
    long_name = "A" * 1000
    result = sanitize_name(long_name)
    assert isinstance(result, str)
```

## Regression Testing

**Every time you fix a bug, write a test for it.**

### Process:

1. **Write a test that reproduces the bug**
   ```python
   def test_name_case_preserved_in_directory(self):
       """Regression test for bug where --name was lowercased."""
       result = sanitize_name("MyRunHasUpperCase", preserve_case=True)
       assert result == "MyRunHasUpperCase"  # This would fail with the bug
   ```

2. **Verify the test fails** (confirms it catches the bug)
   ```bash
   pytest tests/unit/test_sanitization.py::test_name_case_preserved_in_directory -v
   # Should FAIL initially
   ```

3. **Fix the bug** in the code

4. **Verify the test passes**
   ```bash
   pytest tests/unit/test_sanitization.py::test_name_case_preserved_in_directory -v
   # Should PASS now
   ```

5. **Commit both the fix and the test**
   ```bash
   git add scripts/workflow.py tests/unit/test_sanitization.py
   git commit -m "Fix: preserve case in --name parameter with test"
   ```

### Current Regression Tests

- ✅ **Case preservation bug** (Oct 27, 2025)
  - Test: `test_sanitization.py::TestWorkflowNameHandling`
  - Bug: `--name MyRunHasUpperCase` was lowercased in directory name
  - Fix: Use `preserve_case=True` for both display and directory

- ✅ **Unicode symbols bug** (Oct 27, 2025)
  - Test: `test_status_log.py::TestStatusLogASCIISymbols`
  - Bug: Unicode symbols (⟳, ✓, ✗, →) rendered as garbage for screen readers
  - Fix: Replace with ASCII equivalents (`[ACTIVE]`, `[DONE]`, `[FAILED]`, "to")

## Test-Driven Development (TDD)

For new features, write tests FIRST:

### TDD Workflow:

1. **Write the test** (it will fail - feature doesn't exist yet)
   ```python
   def test_new_feature_works(self):
       result = new_feature("input")
       assert result == "expected output"
   ```

2. **Run the test** (confirm it fails)
   ```bash
   pytest tests/unit/test_new_feature.py -v
   # FAIL: NameError: name 'new_feature' is not defined
   ```

3. **Write minimal code to make it pass**
   ```python
   def new_feature(input):
       return "expected output"  # Simplest implementation
   ```

4. **Run the test** (confirm it passes)
   ```bash
   pytest tests/unit/test_new_feature.py -v
   # PASS
   ```

5. **Refactor** (improve code without breaking tests)

6. **Repeat** for more complex cases

## Coverage Goals

### Targets:

- **Minimum**: 60% overall coverage
- **Goal**: 80% coverage
- **Critical modules**: 90%+ coverage
  - `workflow.py`
  - `ConvertImage.py`
  - `video_frame_extractor.py`
  - `idt_cli.py`
  - `idt_runner.py`

### Check Coverage:

```bash
# Generate report
pytest --cov=scripts --cov-report=term-missing

# See which lines aren't covered
pytest --cov=scripts --cov-report=html
# Open htmlcov/index.html
```

### Don't Aim for 100%:

- Some code is hard to test (GUI event loops, main entry points)
- Some code isn't worth testing (trivial getters/setters)
- Focus on **critical business logic** and **regression prevention**

## Continuous Integration

Tests run automatically via GitHub Actions on every push.

### Workflow File: `.github/workflows/tests.yml`

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest --cov=scripts --cov-report=html
      - uses: actions/upload-artifact@v3
        with:
          name: coverage-report
          path: htmlcov/
```

### CI Requirements:

- All tests must pass before merging PRs
- Coverage should not decrease significantly
- New features should include tests

## Mocking External Dependencies

Use `pytest-mock` for external dependencies:

### Example: Mocking API Calls

```python
def test_geocoding_with_mock_api(mocker):
    """Test geocoding without hitting real API."""
    # Mock the requests.get function
    mock_response = mocker.Mock()
    mock_response.json.return_value = {"lat": 40.7128, "lon": -74.0060}
    mock_response.status_code = 200
    
    mocker.patch('requests.get', return_value=mock_response)
    
    # Now test geocoding function
    result = geocode_location("New York")
    assert result["lat"] == 40.7128
```

### Example: Mocking File I/O

```python
def test_file_processing(mocker, tmp_path):
    """Test file processing with temporary files."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")
    
    result = process_file(test_file)
    assert result == "processed: test content"
```

## Debugging Failed Tests

### Run with More Detail:

```bash
# Show print statements
pytest -s

# Show local variables on failure
pytest -l

# Stop on first failure
pytest -x

# Enter debugger on failure
pytest --pdb
```

### Common Issues:

1. **Import errors**: Run from project root, not `tests/` directory
2. **File not found**: Use `tmp_path` fixture or `test_fixtures_path`
3. **Tests pass locally but fail in CI**: Check for hardcoded paths, platform differences

## Performance

### Keep Tests Fast:

- Unit tests should complete in milliseconds
- Use mocks instead of real APIs/files
- Use `tmp_path` for temporary files
- Avoid sleep() in tests

### Slow Tests:

Mark slow tests so they can be skipped:

```python
@pytest.mark.slow
def test_long_running_operation():
    ...
```

Run fast tests only:
```bash
pytest -m "not slow"
```

## Resources

- **pytest documentation**: https://docs.pytest.org/
- **pytest-cov**: https://pytest-cov.readthedocs.io/
- **pytest-mock**: https://pytest-mock.readthedocs.io/
- **Test example**: `tools/ImageGallery/.../test_identify_gallery_content.py`

## Questions?

- Check test examples in `tests/unit/`
- Review `conftest.py` for available fixtures
- See `.github/ISSUE_AUTOMATED_TEST_SYSTEM.md` for overall testing strategy

---

**Created**: October 27, 2025  
**Framework**: pytest 6.0+  
**Coverage**: pytest-cov  
**Mocking**: pytest-mock  
**CI**: GitHub Actions
