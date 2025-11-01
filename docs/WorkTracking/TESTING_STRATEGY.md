# Image Description Toolkit - Testing Strategy

**Status**: Comprehensive Overhaul (November 2025)  
**Goal**: Establish automated, scalable testing that eliminates manual regression testing

## Executive Summary

This document defines the complete testing strategy for IDT after identifying that the current ad-hoc approach doesn't scale. The project has grown to where adding features requires "manually testing dozens of areas" - this strategy eliminates that burden through automation.

### Core Principle
**Every feature must be testable without manual intervention.** If a change requires manual testing of "dozens of areas," the architecture needs refactoring.

---

## Testing Pyramid

```
                /\
               /  \
              /E2E \          ← 5-10 critical path tests
             /------\
            /        \
           /Integration\      ← 20-30 workflow tests
          /------------\
         /              \
        /   Unit Tests   \    ← 100+ fast, isolated tests
       /------------------\
```

### Test Categories

#### 1. **Unit Tests** (`pytest_tests/unit/`)
**Purpose**: Test individual functions and classes in isolation  
**Speed**: < 100ms per test  
**Coverage Target**: 80%+ of business logic

**What to test**:
- Configuration loading and validation
- Path sanitization and naming
- Metadata extraction logic
- Prompt template rendering
- File discovery algorithms
- Data transformations

**What NOT to test**:
- Third-party library internals
- Simple property getters/setters
- Trivial pass-through functions

**Example Structure**:
```python
def test_sanitize_name_removes_special_chars():
    """Test filesystem name sanitization"""
    assert sanitize_name("GPT-4 Vision!@#") == "GPT-4Vision"
    assert sanitize_name("model:tag") == "modeltag"
```

#### 2. **Integration Tests** (`pytest_tests/integration/`)
**Purpose**: Test component interactions without full deployment  
**Speed**: 1-10 seconds per test  
**Coverage Target**: All critical workflows

**What to test**:
- Video extraction → EXIF embedding pipeline
- Image conversion → metadata preservation
- Workflow orchestrator → step coordination
- Config resolution across multiple sources
- AI provider fallback and retry logic

**Example Structure**:
```python
@pytest.mark.integration
def test_conversion_preserves_exif(temp_dir):
    """Verify EXIF survives conversion + optimization"""
    source = create_image_with_exif(temp_dir / "source.jpg")
    convert_heic_to_jpg(source, temp_dir / "output.jpg", keep_metadata=True)
    assert_exif_preserved(temp_dir / "output.jpg")
```

#### 3. **End-to-End Tests** (`pytest_tests/e2e/`)
**Purpose**: Test complete frozen executable workflows  
**Speed**: 30-120 seconds per test  
**Coverage Target**: All user-facing commands

**Critical Tests**:
1. **Build + Workflow Test** (user's #1 priority)
   - Build idt.exe
   - Run workflow on test images
   - Verify descriptions generated
   - Verify HTML output
   - Verify viewer can parse results

2. **CLI Command Tests**
   - `idt version` (verify frozen mode)
   - `idt workflow` (with all providers)
   - `idt combinedescriptions`
   - `idt stats`
   - `idt guideme`

3. **Multi-Provider Tests**
   - Ollama (if available)
   - OpenAI (mock API)
   - Claude (mock API)

**Example Structure**:
```python
@pytest.mark.e2e
@pytest.mark.slow
def test_frozen_workflow_end_to_end(test_images, temp_output):
    """Build and run complete workflow with frozen executable"""
    # Build if not already built
    ensure_executable_built()
    
    # Run workflow
    result = run_executable([
        "workflow", str(test_images),
        "--output", str(temp_output),
        "--model", "test-model"
    ])
    
    # Verify success
    assert result.returncode == 0
    assert (temp_output / "descriptions").exists()
    assert count_descriptions(temp_output) > 0
    assert (temp_output / "html_reports" / "index.html").exists()
```

#### 4. **Smoke Tests** (`pytest_tests/smoke/`)
**Purpose**: Quick sanity checks after deployment  
**Speed**: < 5 seconds total  
**Coverage Target**: All entry points accessible

**What to test**:
- All executables launch without crashing
- `--help` works for all commands
- Config files are accessible
- Required directories can be created

---

## Test Infrastructure

### Test Data Management

**Location**: `test_data/`

**Contents**:
```
test_data/
├── images/
│   ├── jpeg_with_exif.jpg      # Standard EXIF test
│   ├── heic_iphone.HEIC        # Apple format test
│   ├── png_no_metadata.png     # Minimal metadata test
│   └── large_image.jpg         # Size optimization test
├── videos/
│   ├── sample_30fps.mp4        # Frame extraction test
│   └── iphone_recording.MOV    # Apple video format test
├── configs/
│   ├── minimal_config.json     # Bare minimum config
│   ├── full_config.json        # All options specified
│   └── invalid_config.json     # Error handling test
└── expected_outputs/
    ├── sample_description.txt  # Golden file comparison
    └── sample_html.html        # HTML structure test
```

**Principles**:
1. **Small files**: Keep test images < 500KB
2. **Diverse formats**: Cover all supported types
3. **Golden files**: Store expected outputs for comparison
4. **Version control**: All test data committed to repo
5. **No external dependencies**: Tests don't download or require internet

### Mock Strategies

#### AI Provider Mocking
```python
# pytest_tests/conftest.py
@pytest.fixture
def mock_ollama_api(monkeypatch):
    """Mock Ollama API for deterministic testing"""
    def fake_chat(*args, **kwargs):
        return {
            "message": {
                "content": "A test image showing a sample scene."
            }
        }
    monkeypatch.setattr("ollama.chat", fake_chat)
```

#### Filesystem Isolation
```python
@pytest.fixture
def isolated_workspace(tmp_path):
    """Create isolated temp directory for tests"""
    workspace = tmp_path / "test_workspace"
    workspace.mkdir()
    (workspace / "images").mkdir()
    (workspace / "output").mkdir()
    yield workspace
    # Automatic cleanup by pytest tmp_path
```

---

## Continuous Integration Strategy

### GitHub Actions Workflow

**File**: `.github/workflows/test.yml`

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      - run: pip install -r requirements.txt
      - run: python run_unit_tests.py
      
  integration-tests:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: pip install -r requirements.txt
      - run: pytest pytest_tests/integration/ -v
      
  build-and-e2e:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: pip install -r requirements.txt
      - run: BuildAndRelease\build_idt.bat
      - run: pytest pytest_tests/e2e/ -v --e2e-executable=dist/idt.exe
```

### Local Pre-Commit Hook

**File**: `.git/hooks/pre-commit`

```bash
#!/bin/bash
# Run fast tests before allowing commit
python run_unit_tests.py
if [ $? -ne 0 ]; then
    echo "Unit tests failed! Fix before committing."
    exit 1
fi
```

---

## Build-Time Testing

### Current Problems
1. `builditall.bat` builds but doesn't test
2. `build-test-deploy.bat` tests before build (catches dev issues, not build issues)
3. No verification that frozen executables work

### New Approach: Test-Build-Test

```
1. Pre-Build Tests (Fast)
   ├─ Unit tests (Python environment)
   └─ Integration tests (Python environment)
   
2. Build
   ├─ PyInstaller executable creation
   └─ Spec file validation
   
3. Post-Build Tests (Critical)
   ├─ Smoke test: exe launches
   ├─ E2E test: run workflow with frozen exe
   └─ Regression test: compare with known good output
```

**Implementation**: See `test_and_build.bat` (created separately)

---

## Making Code More Testable

### Current Testability Issues

#### Issue 1: Massive God Functions
**Example**: `workflow.py::main()` - 600+ lines handling everything

**Problem**: Can't test individual workflow steps without running entire pipeline

**Solution**: Refactor into testable components
```python
# BEFORE (untestable)
def main():
    # 600 lines of mixed concerns
    parse_args()
    validate_config()
    discover_files()
    extract_frames()
    convert_images()
    describe_images()
    generate_html()

# AFTER (testable)
class WorkflowOrchestrator:
    def __init__(self, config: WorkflowConfig):
        self.config = config
        self.logger = setup_logger(config)
        
    def run_step_extract(self) -> StepResult:
        """Extract video frames - testable in isolation"""
        pass
        
    def run_step_convert(self) -> StepResult:
        """Convert images - testable in isolation"""
        pass
```

#### Issue 2: Hardcoded Dependencies
**Example**: Direct filesystem access throughout

**Problem**: Tests require real files, can't test error conditions

**Solution**: Dependency injection
```python
# BEFORE (untestable)
def process_image(path: str):
    img = Image.open(path)  # Hardcoded filesystem
    metadata = extract_metadata(path)  # Hardcoded

# AFTER (testable)
def process_image(path: str, filesystem: FileSystem = None):
    fs = filesystem or RealFileSystem()
    img = fs.open_image(path)
    metadata = fs.extract_metadata(path)

# In tests
def test_process_image_missing_file():
    mock_fs = MockFileSystem(raise_on_open=FileNotFoundError)
    with pytest.raises(FileNotFoundError):
        process_image("test.jpg", filesystem=mock_fs)
```

#### Issue 3: Global State
**Example**: Config loaded once at module import

**Problem**: Tests interfere with each other, can't test different configs

**Solution**: Explicit config passing
```python
# BEFORE (untestable)
CONFIG = load_config()  # Global at import time

def describe_image(path):
    model = CONFIG['model']  # Uses global

# AFTER (testable)
def describe_image(path, config: dict = None):
    cfg = config or load_default_config()
    model = cfg['model']
```

#### Issue 4: Side Effects in Functions
**Example**: Functions that modify filesystem, send API calls, AND log

**Problem**: Can't test logic without triggering side effects

**Solution**: Separate concerns
```python
# BEFORE (untestable)
def convert_image(source, dest):
    img = Image.open(source)
    img = optimize(img)
    img.save(dest)  # Side effect
    log.info(f"Saved {dest}")  # Side effect
    send_metric("image_converted")  # Side effect

# AFTER (testable)
def optimize_image(img: Image) -> Image:
    """Pure function - testable"""
    return apply_optimizations(img)

def convert_image(source, dest, logger=None, metrics=None):
    """Orchestrator - dependencies injected"""
    img = Image.open(source)
    img = optimize_image(img)
    img.save(dest)
    if logger:
        logger.info(f"Saved {dest}")
    if metrics:
        metrics.increment("image_converted")
```

### Refactoring Priorities

**High Priority** (blocking test automation):
1. ✅ Extract `WorkflowOrchestrator` class from `workflow.py::main()`
2. ⚠️ Make AI provider calls mockable (interface/protocol)
3. ⚠️ Separate config loading from business logic
4. ⚠️ Make filesystem operations injectable

**Medium Priority** (improves test quality):
5. Extract validation logic into testable functions
6. Separate logging from business logic
7. Make retry logic configurable (don't wait 60s in tests)

**Low Priority** (nice to have):
8. Add type hints to all public functions
9. Document preconditions/postconditions
10. Extract constants to configuration

---

## Test Execution Guide

### Daily Development

```bash
# Before committing: Run fast tests
python run_unit_tests.py

# Optional: Run integration tests for affected area
pytest pytest_tests/integration/test_workflow_integration.py -v
```

### Before Merging PR

```bash
# Run all tests except slow E2E
pytest pytest_tests/ -m "not slow" -v

# Check coverage
pytest pytest_tests/unit/ --cov=scripts --cov-report=html
# Open htmlcov/index.html to review
```

### Before Release

```bash
# Complete test suite including E2E
python test_and_build.bat

# This runs:
# 1. Unit tests
# 2. Integration tests  
# 3. Build executable
# 4. E2E tests with frozen exe
# 5. Smoke tests on all entry points
```

### Debugging Failed Tests

```bash
# Run specific test with verbose output
pytest pytest_tests/unit/test_workflow_config.py::test_specific_function -vv

# Show print statements
pytest pytest_tests/unit/test_workflow_config.py -s

# Drop into debugger on failure
pytest pytest_tests/unit/test_workflow_config.py --pdb

# Run only failed tests from last run
pytest --lf
```

---

## Success Metrics

### Quantitative Goals
- ✅ Unit test coverage > 80%
- ✅ All PRs pass CI before merge
- ✅ E2E test suite runs in < 5 minutes
- ✅ Zero manual regression testing for new features

### Qualitative Goals
- ✅ Developers confident to refactor without breaking things
- ✅ Bugs caught by tests, not users
- ✅ New features come with tests (not added later)
- ✅ Test failures point to exact problem location

---

## Migration Plan

### Phase 1: Foundation (Week 1) ✅ 
- [x] Create this strategy document
- [x] Set up E2E test infrastructure
- [x] Create `test_and_build.bat` script
- [x] Add critical path E2E test

### Phase 2: Coverage (Week 2)
- [ ] Audit existing code for testability
- [ ] Add unit tests for core utilities (target: 80% coverage)
- [ ] Refactor `WorkflowOrchestrator` for testability
- [ ] Mock AI provider interfaces

### Phase 3: Integration (Week 3)
- [ ] Add integration tests for all workflow steps
- [ ] Add regression tests for past bugs
- [ ] Set up GitHub Actions CI
- [ ] Configure pre-commit hooks

### Phase 4: Maintenance (Ongoing)
- [ ] All new code requires tests
- [ ] Review test failures before production
- [ ] Monitor and improve flaky tests
- [ ] Update test data as needed

---

## FAQ

**Q: Do I really need to write tests for simple functions?**  
A: Not every function needs a test. Skip tests for:
- Simple getters/setters
- Pass-through functions
- Code that's just glue to external libraries

Do write tests for:
- Business logic
- Anything with conditionals
- Data transformations
- Error handling

**Q: My test is slow (> 1 second). What do I do?**  
A: 
1. Mark it with `@pytest.mark.slow`
2. Consider if it's really a unit test or should be integration/e2e
3. Look for ways to mock expensive operations
4. Ensure you're not hitting disk/network unnecessarily

**Q: How do I test code that calls external APIs?**  
A: 
1. Use `monkeypatch` or `unittest.mock` to replace the API call
2. Return realistic fake data
3. Test both success and failure paths
4. Consider using recorded HTTP responses (VCR.py)

**Q: Should tests share setup code?**  
A: Use pytest fixtures in `conftest.py` for shared setup. Avoid test interdependencies.

**Q: What if a test fails intermittently?**  
A: Flaky tests are worse than no tests. Debug immediately:
1. Check for timing issues (add explicit waits)
2. Check for filesystem race conditions
3. Check for shared global state
4. Consider marking `@pytest.mark.flaky` while debugging

---

## References

- [Pytest Documentation](https://docs.pytest.org/)
- [Testing Python Applications](https://realpython.com/pytest-python-testing/)
- [Effective Python Testing](https://testdriven.io/blog/testing-python/)
- Project: `pytest_tests/` for examples
- Project: `run_unit_tests.py` for custom runner

---

**Last Updated**: November 1, 2025  
**Next Review**: After Phase 2 completion
