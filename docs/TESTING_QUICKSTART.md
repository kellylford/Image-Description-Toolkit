# Testing Quick Start Guide

**Created**: November 1, 2025  
**For**: Image Description Toolkit Developers

## TL;DR - Just Want to Test My Changes?

### Before Committing Code

```bash
# Fast tests (30 seconds) - run these during development
pytest pytest_tests/ -m "not slow and not e2e" -v

# Or use the custom runner for Python 3.13
python run_unit_tests.py
```

### Before Building a Release

```bash
# Complete pipeline: test → build → verify (3-5 minutes)
test_and_build.bat
```

This script:
1. ✅ Runs all unit tests
2. ✅ Builds idt.exe
3. ✅ Smoke tests the executable
4. ✅ Runs a complete workflow with test images
5. ✅ Verifies outputs generated

**If it passes, your build is ready to ship.**

---

## What Tests to Run When

### 🚀 **During Development** (Every few minutes)

```bash
# Just the test file you're working on
pytest pytest_tests/unit/test_my_feature.py -v

# Or all unit tests (fast)
pytest pytest_tests/unit/ -v
```

**Time**: < 10 seconds  
**Purpose**: Catch bugs immediately

### 📝 **Before Committing** (Before git commit)

```bash
# All fast tests
pytest pytest_tests/ -m "not slow" -v

# With coverage
pytest pytest_tests/ -m "not slow" --cov=scripts --cov-report=html
```

**Time**: < 30 seconds  
**Purpose**: Ensure you didn't break anything

### 🏗️ **After Building** (After BuildAndRelease\build_idt.bat)

```bash
# E2E tests with frozen executable
pytest pytest_tests/e2e/ -v
```

**Time**: 2-3 minutes  
**Purpose**: Verify the frozen exe actually works

### 🚢 **Before Releasing** (Weekly/release prep)

```bash
# Complete automated pipeline
test_and_build.bat

# Or manually:
pytest pytest_tests/ -v  # All tests including slow ones
```

**Time**: 3-5 minutes  
**Purpose**: Full confidence before users get it

---

## Understanding Test Categories

### 🟢 Unit Tests (`pytest_tests/unit/`)
**Speed**: < 100ms each  
**Purpose**: Test individual functions in isolation  
**Run them**: Every few minutes during development

Examples:
- Name sanitization
- Configuration parsing
- Path generation
- Data validation

### 🟡 Integration Tests (`pytest_tests/integration/`)
**Speed**: 1-10 seconds each  
**Purpose**: Test components working together  
**Run them**: Before committing

Examples:
- EXIF preservation through conversion
- HTML generation from descriptions
- Video frame extraction
- Workflow metadata handling

### 🔴 E2E Tests (`pytest_tests/e2e/`)
**Speed**: 30-120 seconds each  
**Purpose**: Test frozen executable end-to-end  
**Run them**: After building, before releasing

Examples:
- Complete workflow with frozen exe
- All CLI commands
- Error handling
- Help text accessibility

### ⚪ Smoke Tests (`pytest_tests/smoke/`)
**Speed**: < 1 second each  
**Purpose**: Quick sanity checks  
**Run them**: After building (automatically in test_and_build.bat)

Examples:
- Executables exist
- Version command works
- Help commands accessible

---

## Common Testing Commands

### Run Specific Test

```bash
# Single test function
pytest pytest_tests/unit/test_path_generation.py::test_sanitize_removes_special_chars -v

# Single test class
pytest pytest_tests/unit/test_path_generation.py::TestSanitizeName -v

# Single file
pytest pytest_tests/unit/test_path_generation.py -v
```

### Skip Slow Tests

```bash
# Fast tests only (good for development)
pytest pytest_tests/ -m "not slow" -v
```

### Run Only E2E Tests

```bash
# Requires built executable!
pytest pytest_tests/e2e/ -v

# Or specific test
pytest pytest_tests/e2e/test_build_and_workflow.py -v
```

### Check Test Coverage

```bash
# Generate coverage report
pytest pytest_tests/ --cov=scripts --cov-report=html

# Open report in browser
start htmlcov/index.html  # Windows
```

### Debugging Failed Tests

```bash
# Show print statements
pytest pytest_tests/unit/test_my_feature.py -s

# Drop into debugger on failure
pytest pytest_tests/unit/test_my_feature.py --pdb

# Show more details
pytest pytest_tests/unit/test_my_feature.py -vv

# Show full error traceback
pytest pytest_tests/unit/test_my_feature.py --tb=long
```

---

## Writing New Tests

### 1. Choose the Right Directory

```
pytest_tests/
├── unit/          ← Test individual functions (< 100ms)
├── integration/   ← Test components together (1-10s)
├── e2e/          ← Test frozen executable (30-120s)
└── smoke/        ← Quick sanity checks (< 1s)
```

### 2. Use the Template

```python
"""
Brief description of what this test file covers.
"""

import pytest
import sys
from pathlib import Path

# Add scripts to path for unit/integration tests
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from my_module import my_function


@pytest.mark.unit  # or integration, e2e, smoke
def test_my_function_does_something():
    """Test that my_function does X when given Y"""
    result = my_function("input")
    assert result == "expected_output"


@pytest.mark.unit
def test_my_function_handles_errors():
    """Test error handling"""
    with pytest.raises(ValueError):
        my_function(None)
```

### 3. Use Shared Fixtures

```python
def test_with_test_image(test_image_with_exif):
    """Fixtures from test_helpers.py are available"""
    # test_image_with_exif is automatically created
    assert test_image_with_exif.exists()


def test_with_workflow_directory(sample_workflow_directory):
    """Pre-populated workflow directory"""
    descriptions = sample_workflow_directory / "descriptions"
    assert descriptions.exists()
```

See `pytest_tests/test_helpers.py` for all available fixtures.

### 4. Mark Tests Appropriately

```python
@pytest.mark.unit       # Fast isolated test
@pytest.mark.integration # Component interaction
@pytest.mark.e2e        # Frozen executable test
@pytest.mark.slow       # Takes > 10 seconds
@pytest.mark.regression # Tests a specific bug fix
```

---

## Troubleshooting

### "pytest: command not found"

Use the virtual environment:
```bash
.venv/Scripts/python.exe -m pytest pytest_tests/ -v
```

Or use the custom runner:
```bash
python run_unit_tests.py
```

### "ModuleNotFoundError: No module named 'my_module'"

Add scripts to Python path at top of test file:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
```

### "E2E tests all skip"

E2E tests require built executable:
```bash
# Build first
BuildAndRelease\build_idt.bat

# Then run E2E tests
pytest pytest_tests/e2e/ -v
```

### "Tests pass locally but fail in CI"

Common issues:
- Missing dependencies in requirements.txt
- Hardcoded paths (use fixtures)
- Timing issues (add waits)
- State leaking between tests (use tmp_path fixture)

### "Test is flaky (sometimes passes, sometimes fails)"

Red flags:
- Uses `time.sleep()` instead of proper waits
- Modifies global state
- Depends on filesystem timing
- Has race conditions

Fix by:
- Using fixtures for isolation
- Mocking time-dependent code
- Making tests deterministic

---

## Best Practices

### ✅ DO

- ✅ Write tests for new features BEFORE committing
- ✅ Use descriptive test names (`test_converts_heic_to_jpg_preserving_exif`)
- ✅ Test both success and error cases
- ✅ Use fixtures for setup/teardown
- ✅ Keep tests fast (mock slow operations)
- ✅ Make assertions specific and clear
- ✅ Run tests before pushing code

### ❌ DON'T

- ❌ Skip writing tests ("I'll add them later")
- ❌ Test implementation details (test behavior)
- ❌ Share mutable state between tests
- ❌ Call real APIs in unit tests
- ❌ Leave commented-out tests
- ❌ Ignore flaky tests
- ❌ Commit if tests fail

---

## Getting Help

### Documentation

- **Testing Strategy**: `docs/worktracking/TESTING_STRATEGY.md`
- **Testability Guide**: `docs/worktracking/TESTABILITY_RECOMMENDATIONS.md`
- **Test Structure**: `docs/worktracking/TEST_STRUCTURE_PLAN.md`
- **E2E README**: `pytest_tests/e2e/README.md`

### Examples

Look at existing tests:
- `pytest_tests/unit/test_path_generation.py` - Well-structured unit tests
- `pytest_tests/e2e/test_build_and_workflow.py` - E2E test example
- `pytest_tests/integration/test_html_generation.py` - Integration test example

### Common Patterns

```python
# Test with temporary directory
def test_creates_output_file(tmp_path):
    output_file = tmp_path / "output.txt"
    my_function(output_file)
    assert output_file.exists()

# Test exception handling
def test_raises_on_invalid_input():
    with pytest.raises(ValueError, match="invalid"):
        my_function("bad input")

# Test with mock
def test_calls_api_correctly(mock_ai_provider):
    result = describe_image("image.jpg", provider=mock_ai_provider)
    assert len(mock_ai_provider.calls) == 1
    assert mock_ai_provider.calls[0]['image'] == "image.jpg"

# Parameterized test
@pytest.mark.parametrize("input,expected", [
    ("test", "test"),
    ("TEST", "test"),
    ("t e s t", "test"),
])
def test_sanitize_name(input, expected):
    assert sanitize_name(input) == expected
```

---

## Quick Reference Card

```
┌────────────────────────────────────────────────────────────────┐
│                    TESTING QUICK REFERENCE                     │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  DURING DEVELOPMENT:                                           │
│    pytest pytest_tests/unit/ -v                                │
│    (or) python run_unit_tests.py                               │
│                                                                 │
│  BEFORE COMMIT:                                                │
│    pytest pytest_tests/ -m "not slow" -v                       │
│                                                                 │
│  AFTER BUILD:                                                  │
│    pytest pytest_tests/e2e/ -v                                 │
│                                                                 │
│  COMPLETE PIPELINE:                                            │
│    test_and_build.bat                                          │
│                                                                 │
│  CHECK COVERAGE:                                               │
│    pytest --cov=scripts --cov-report=html                      │
│                                                                 │
│  DEBUG FAILURES:                                               │
│    pytest <test_file> -s --pdb -vv                             │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

---

**Questions? Check `docs/worktracking/TESTING_STRATEGY.md` for details.**

**Happy Testing! 🧪**
