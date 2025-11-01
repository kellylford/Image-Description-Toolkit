# Making IDT More Testable - Concrete Recommendations

**Date**: November 1, 2025  
**Goal**: Transform IDT from a manually-tested codebase to an automatically-testable one

## Executive Summary

This document provides **actionable refactoring recommendations** to make the Image Description Toolkit more testable. Each recommendation includes:
- **Why** it's a problem for testing
- **What** needs to change
- **How** to implement it
- **Priority** level

---

## Critical Testability Issues

### 1. God Functions in Core Modules

#### Problem: `workflow.py::main()` is 600+ lines

**Why this blocks testing**:
- Can't test individual steps without running entire pipeline
- Can't mock specific dependencies
- Failures don't point to specific component
- Can't reuse logic in different contexts

**Current Structure**:
```python
def main():
    """2800+ line function that does everything"""
    # Parse arguments
    # Validate configuration  
    # Discover files
    # Extract video frames
    # Convert images
    # Describe images
    # Generate HTML
    # Launch viewer
    # Handle all errors
```

**Refactoring Target**:
```python
class WorkflowOrchestrator:
    """Testable workflow coordinator"""
    
    def __init__(self, config: WorkflowConfig, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.results = WorkflowResults()
        
    def run_step_extract(self) -> StepResult:
        """Extract video frames - testable in isolation"""
        if not self.config.should_run_step('extract'):
            return StepResult.skipped('extract')
            
        try:
            extractor = VideoFrameExtractor(self.config.extract_config)
            frames = extractor.extract_from_directory(self.config.input_dir)
            self.results.frames_extracted = len(frames)
            return StepResult.success('extract', frames)
        except Exception as e:
            self.logger.error(f"Extraction failed: {e}")
            return StepResult.failure('extract', error=e)
    
    def run_step_convert(self) -> StepResult:
        """Convert images - testable in isolation"""
        # Similar structure
        pass
        
    def run_step_describe(self, provider: AIProvider = None) -> StepResult:
        """Describe images - injectable provider for testing"""
        provider = provider or self._get_ai_provider()
        # Process with injected provider
        pass
        
    def run_all_steps(self) -> WorkflowResults:
        """Run complete workflow"""
        for step_name in self.config.enabled_steps:
            result = getattr(self, f'run_step_{step_name}')()
            self.results.add_step_result(step_name, result)
            if result.failed and self.config.stop_on_error:
                break
        return self.results

# Test becomes trivial
def test_workflow_extraction_failure(tmp_path, mock_logger):
    config = WorkflowConfig(
        input_dir=tmp_path / "nonexistent",
        enabled_steps=['extract']
    )
    orchestrator = WorkflowOrchestrator(config, mock_logger)
    
    result = orchestrator.run_step_extract()
    
    assert result.failed
    assert "nonexistent" in str(result.error)
    mock_logger.error.assert_called_once()
```

**Migration Strategy**:
1. Create `WorkflowOrchestrator` class with empty methods
2. Extract one step at a time from `main()` into methods
3. Update tests as you extract
4. Eventually, `main()` becomes just:
   ```python
   def main():
       config = parse_args_and_load_config()
       orchestrator = WorkflowOrchestrator(config)
       results = orchestrator.run_all_steps()
       sys.exit(0 if results.all_passed else 1)
   ```

**Priority**: 🔴 CRITICAL - Blocking automated testing

**Estimated Effort**: 2-3 days

**Files Affected**:
- `scripts/workflow.py` (refactor main())
- `scripts/workflow_utils.py` (add WorkflowOrchestrator class)
- `pytest_tests/unit/test_workflow_orchestrator.py` (new)
- `pytest_tests/integration/test_workflow_steps.py` (new)

---

### 2. Hardcoded AI Provider Dependencies

#### Problem: Can't test AI description logic without calling real APIs

**Why this blocks testing**:
- Tests are slow (wait for API responses)
- Tests fail if API is down
- Tests cost money (API usage)
- Can't test error conditions (rate limits, timeouts)
- Can't test edge cases (specific response formats)

**Current Structure**:
```python
# image_describer.py
def describe_image(image_path: str, model: str, prompt: str) -> str:
    """Directly calls Ollama/OpenAI/Claude APIs"""
    if model.startswith('gpt'):
        import openai
        response = openai.ChatCompletion.create(...)  # Real API call
        return response.choices[0].message.content
    elif model.startswith('claude'):
        import anthropic
        response = anthropic.Anthropic().messages.create(...)  # Real API call
        return response.content[0].text
    # etc.
```

**Refactoring Target**:
```python
# ai_providers.py
from abc import ABC, abstractmethod
from typing import Protocol

class AIProvider(Protocol):
    """Interface that all AI providers must implement"""
    
    def describe_image(self, image_data: bytes, prompt: str) -> str:
        """Generate description from image data"""
        ...
    
    def get_model_name(self) -> str:
        """Return the model identifier"""
        ...
    
    def is_available(self) -> bool:
        """Check if provider is accessible"""
        ...

class OllamaProvider:
    """Real Ollama implementation"""
    def __init__(self, model: str, base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        
    def describe_image(self, image_data: bytes, prompt: str) -> str:
        import ollama
        response = ollama.chat(...)
        return response['message']['content']
    
    # ... rest of implementation

class MockProvider:
    """Test double for AI providers"""
    def __init__(self, responses: list[str] = None):
        self.responses = responses or ["A test image"]
        self.calls = []
        self._index = 0
        
    def describe_image(self, image_data: bytes, prompt: str) -> str:
        self.calls.append({'image_size': len(image_data), 'prompt': prompt})
        response = self.responses[self._index % len(self.responses)]
        self._index += 1
        return response
    
    def get_model_name(self) -> str:
        return "mock-model"
    
    def is_available(self) -> bool:
        return True

# image_describer.py (refactored)
def describe_images_batch(
    image_paths: list[Path],
    provider: AIProvider,  # Injected dependency
    output_dir: Path
) -> BatchResults:
    """Process images with any AI provider"""
    results = BatchResults()
    
    for image_path in image_paths:
        image_data = image_path.read_bytes()
        description = provider.describe_image(image_data, prompt="Describe this image")
        results.add(image_path, description)
    
    return results

# Testing becomes trivial
def test_describe_images_batch_success(tmp_path):
    images = [create_test_image(tmp_path / "test1.jpg")]
    mock_provider = MockProvider(responses=["A beautiful landscape"])
    
    results = describe_images_batch(images, mock_provider, tmp_path)
    
    assert len(results) == 1
    assert "beautiful landscape" in results[0].description
    assert len(mock_provider.calls) == 1

def test_describe_images_handles_provider_error(tmp_path):
    images = [create_test_image(tmp_path / "test.jpg")]
    
    class FailingProvider(MockProvider):
        def describe_image(self, image_data, prompt):
            raise APIError("Rate limit exceeded")
    
    failing_provider = FailingProvider()
    results = describe_images_batch(images, failing_provider, tmp_path)
    
    assert results[0].failed
    assert "Rate limit" in results[0].error_message
```

**Migration Strategy**:
1. Create `AIProvider` protocol in `models/ai_providers.py`
2. Extract existing provider code into separate classes
3. Add `provider` parameter to description functions (default to real provider)
4. Create `MockProvider` and `FailingProvider` test helpers
5. Update tests to use mock providers

**Priority**: 🔴 CRITICAL - Blocking fast, reliable tests

**Estimated Effort**: 2-3 days

**Files Affected**:
- `scripts/image_describer.py` (add provider parameter)
- `models/ai_providers.py` (new - provider interfaces)
- `models/mock_providers.py` (new - test doubles)
- `pytest_tests/unit/test_ai_providers.py` (new)
- `pytest_tests/integration/test_description_pipeline.py` (update)

---

### 3. Global Configuration State

#### Problem: Config loaded once at module import time

**Why this blocks testing**:
- Tests interfere with each other (shared state)
- Can't test different configurations in same test run
- Can't test config validation independently
- Hard to reproduce production issues

**Current Structure**:
```python
# Multiple files do this
from config_loader import load_json_config

# Loaded at import time - shared across all tests
CONFIG, CONFIG_PATH, _ = load_json_config('workflow_config.json')
DEFAULT_MODEL = CONFIG.get('default_model', 'llava:7b')

def process_workflow(input_dir):
    """Uses global CONFIG"""
    model = CONFIG.get('model', DEFAULT_MODEL)
    steps = CONFIG.get('steps', ['all'])
    # ... rest of function
```

**Refactoring Target**:
```python
# Config as explicit parameter with sensible defaults
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class WorkflowConfig:
    """Explicit configuration object"""
    input_dir: Path
    output_dir: Optional[Path] = None
    model: str = 'llava:7b'
    prompt_style: str = 'narrative'
    steps: list[str] = field(default_factory=lambda: ['all'])
    max_workers: int = 4
    timeout: int = 300
    
    @classmethod
    def from_file(cls, config_path: Path) -> 'WorkflowConfig':
        """Load from JSON file"""
        with open(config_path) as f:
            data = json.load(f)
        return cls(**data)
    
    @classmethod
    def from_args(cls, args: argparse.Namespace) -> 'WorkflowConfig':
        """Create from CLI arguments"""
        return cls(
            input_dir=Path(args.input_dir),
            output_dir=Path(args.output) if args.output else None,
            model=args.model or cls.model,
            steps=args.steps.split(',') if args.steps else ['all']
        )
    
    def validate(self) -> list[str]:
        """Return list of validation errors"""
        errors = []
        if not self.input_dir.exists():
            errors.append(f"Input directory not found: {self.input_dir}")
        if self.max_workers < 1:
            errors.append(f"max_workers must be >= 1, got {self.max_workers}")
        return errors

def process_workflow(config: WorkflowConfig):
    """Config is explicit parameter"""
    errors = config.validate()
    if errors:
        raise ValueError(f"Invalid config: {', '.join(errors)}")
    
    # Use config values
    model = config.model
    steps = config.steps
    # ... rest of function

# Testing becomes trivial
def test_workflow_with_custom_config(tmp_path):
    config = WorkflowConfig(
        input_dir=tmp_path / "images",
        model="test-model",
        steps=['describe']
    )
    
    result = process_workflow(config)
    
    assert result.model_used == "test-model"

def test_config_validation_fails_for_missing_dir():
    config = WorkflowConfig(
        input_dir=Path("/nonexistent/directory")
    )
    
    errors = config.validate()
    
    assert len(errors) > 0
    assert "not found" in errors[0]
```

**Migration Strategy**:
1. Create `WorkflowConfig` dataclass in `workflow_utils.py`
2. Keep global config for backward compatibility initially
3. Add `config` parameter to functions (default to global)
4. Update one module at a time
5. Remove global config once all code uses explicit config

**Priority**: 🟡 HIGH - Improves test isolation and reliability

**Estimated Effort**: 2 days

**Files Affected**:
- `scripts/workflow_utils.py` (add WorkflowConfig class)
- `scripts/workflow.py` (use explicit config)
- `scripts/image_describer.py` (use explicit config)
- All test files (update to use explicit config)

---

### 4. Filesystem Operations Throughout Code

#### Problem: Direct filesystem access makes testing brittle

**Why this blocks testing**:
- Tests require real files on disk
- Hard to test error conditions (permissions, disk full)
- Tests are slower (disk I/O)
- Race conditions in parallel tests
- Cleanup is error-prone

**Current Structure**:
```python
def process_directory(input_dir: str):
    """Directly accesses filesystem"""
    files = []
    for file in Path(input_dir).iterdir():
        if file.suffix.lower() in ['.jpg', '.png']:
            files.append(file)
    
    for file in files:
        data = file.read_bytes()
        result = process_image(data)
        output_path = Path(input_dir) / "processed" / file.name
        output_path.parent.mkdir(exist_ok=True)
        output_path.write_text(result)
```

**Refactoring Target**:
```python
from abc import ABC, abstractmethod
from pathlib import Path

class FileSystem(ABC):
    """Abstract filesystem interface"""
    
    @abstractmethod
    def list_directory(self, path: Path) -> list[Path]:
        pass
    
    @abstractmethod
    def read_bytes(self, path: Path) -> bytes:
        pass
    
    @abstractmethod
    def write_text(self, path: Path, content: str) -> None:
        pass
    
    @abstractmethod
    def mkdir(self, path: Path, exist_ok: bool = True) -> None:
        pass

class RealFileSystem(FileSystem):
    """Production filesystem implementation"""
    
    def list_directory(self, path: Path) -> list[Path]:
        return list(path.iterdir())
    
    def read_bytes(self, path: Path) -> bytes:
        return path.read_bytes()
    
    def write_text(self, path: Path, content: str) -> None:
        path.write_text(content)
    
    def mkdir(self, path: Path, exist_ok: bool = True) -> None:
        path.mkdir(parents=True, exist_ok=exist_ok)

class MemoryFileSystem(FileSystem):
    """In-memory filesystem for testing"""
    
    def __init__(self):
        self.files: dict[Path, bytes] = {}
        self.dirs: set[Path] = set()
    
    def list_directory(self, path: Path) -> list[Path]:
        return [p for p in self.files.keys() if p.parent == path]
    
    def read_bytes(self, path: Path) -> bytes:
        if path not in self.files:
            raise FileNotFoundError(f"No such file: {path}")
        return self.files[path]
    
    def write_text(self, path: Path, content: str) -> None:
        self.files[path] = content.encode()
    
    def mkdir(self, path: Path, exist_ok: bool = True) -> None:
        if path in self.dirs and not exist_ok:
            raise FileExistsError(f"Directory exists: {path}")
        self.dirs.add(path)

def process_directory(input_dir: Path, fs: FileSystem = None):
    """Filesystem is injected dependency"""
    fs = fs or RealFileSystem()
    
    files = [f for f in fs.list_directory(input_dir) 
             if f.suffix.lower() in ['.jpg', '.png']]
    
    for file in files:
        data = fs.read_bytes(file)
        result = process_image(data)
        output_path = input_dir / "processed" / file.name
        fs.mkdir(output_path.parent)
        fs.write_text(output_path, result)

# Testing becomes trivial
def test_process_directory_creates_output():
    fs = MemoryFileSystem()
    input_dir = Path("/input")
    fs.mkdir(input_dir)
    fs.files[input_dir / "test.jpg"] = b"fake image data"
    
    process_directory(input_dir, fs)
    
    output_file = input_dir / "processed" / "test.jpg"
    assert output_file in fs.files
    assert len(fs.files[output_file]) > 0

def test_process_directory_handles_missing_dir():
    fs = MemoryFileSystem()
    
    with pytest.raises(FileNotFoundError):
        process_directory(Path("/nonexistent"), fs)
```

**Note**: This is a more advanced pattern. Start with critical paths only.

**Migration Strategy**:
1. Identify critical file operations (read/write descriptions, load configs)
2. Create `FileSystem` interface for those operations
3. Inject filesystem only in testable functions
4. Don't refactor one-off scripts unless they need testing

**Priority**: 🟢 MEDIUM - Nice to have for complex file operations

**Estimated Effort**: 3-4 days (only for critical paths)

**Files Affected**:
- `scripts/filesystem.py` (new - filesystem abstraction)
- `scripts/workflow.py` (inject filesystem for output operations)
- `scripts/image_describer.py` (inject filesystem for description writing)
- Test files (use MemoryFileSystem)

---

### 5. Mixing Logging with Business Logic

#### Problem: Functions that do work AND log can't be tested cleanly

**Why this blocks testing**:
- Tests are polluted with log output
- Can't test logic without triggering logging
- Hard to assert on log messages
- Logging configuration leaks between tests

**Current Structure**:
```python
def convert_image(source: Path, dest: Path) -> bool:
    """Mixes conversion logic with logging"""
    logging.info(f"Converting {source} to {dest}")
    
    try:
        img = Image.open(source)
        logging.debug(f"Image size: {img.size}")
        
        if needs_optimization(img):
            logging.info("Optimizing image size")
            img = optimize_image(img)
        
        img.save(dest)
        logging.info(f"Saved to {dest}")
        return True
        
    except Exception as e:
        logging.error(f"Conversion failed: {e}")
        return False
```

**Refactoring Target**:
```python
@dataclass
class ConversionResult:
    """Result of image conversion"""
    success: bool
    input_path: Path
    output_path: Path
    optimized: bool = False
    error: Optional[Exception] = None
    
    def log_result(self, logger: logging.Logger):
        """Separate logging concern"""
        if self.success:
            msg = f"Converted {self.input_path} to {self.output_path}"
            if self.optimized:
                msg += " (optimized)"
            logger.info(msg)
        else:
            logger.error(f"Failed to convert {self.input_path}: {self.error}")

def convert_image(source: Path, dest: Path) -> ConversionResult:
    """Pure business logic - no logging"""
    try:
        img = Image.open(source)
        
        optimized = False
        if needs_optimization(img):
            img = optimize_image(img)
            optimized = True
        
        img.save(dest)
        
        return ConversionResult(
            success=True,
            input_path=source,
            output_path=dest,
            optimized=optimized
        )
        
    except Exception as e:
        return ConversionResult(
            success=False,
            input_path=source,
            output_path=dest,
            error=e
        )

# Caller handles logging
def convert_directory(input_dir: Path, output_dir: Path, logger: logging.Logger):
    """Orchestrator handles logging"""
    for image_file in find_images(input_dir):
        output_file = output_dir / image_file.name
        result = convert_image(image_file, output_file)
        result.log_result(logger)

# Testing is clean
def test_convert_image_optimizes_large_images(tmp_path):
    source = create_large_image(tmp_path / "large.jpg")
    dest = tmp_path / "output.jpg"
    
    result = convert_image(source, dest)
    
    assert result.success
    assert result.optimized
    assert dest.stat().st_size < source.stat().st_size
    # No log pollution in test output!
```

**Migration Strategy**:
1. Identify functions that mix logging with logic
2. Extract pure business logic into separate functions
3. Return result objects instead of logging
4. Add `.log_result()` methods to result objects
5. Update callers to handle logging

**Priority**: 🟢 MEDIUM - Improves test clarity

**Estimated Effort**: 2-3 days

**Files Affected**:
- `scripts/ConvertImage.py`
- `scripts/image_describer.py`
- `scripts/workflow.py`
- Test files (cleaner, no log capture needed)

---

## Quick Wins (Low-Hanging Fruit)

### 6. Extract Validation Functions

Many places validate inputs inline. Extract to testable functions:

```python
# BEFORE: Inline validation
def process_workflow(input_dir: str, model: str):
    if not os.path.exists(input_dir):
        print("ERROR: Input directory not found")
        sys.exit(1)
    
    if model not in ['llava', 'gpt-4', 'claude']:
        print(f"ERROR: Unknown model: {model}")
        sys.exit(1)
    
    # ... actual work

# AFTER: Testable validation
def validate_input_directory(path: str) -> Optional[str]:
    """Return error message if invalid, None if valid"""
    if not os.path.exists(path):
        return f"Input directory not found: {path}"
    if not os.path.isdir(path):
        return f"Path is not a directory: {path}"
    return None

def validate_model_name(model: str, available_models: list[str]) -> Optional[str]:
    """Return error message if invalid, None if valid"""
    if model not in available_models:
        return f"Unknown model '{model}'. Available: {', '.join(available_models)}"
    return None

def process_workflow(input_dir: str, model: str):
    """Validation extracted and testable"""
    if error := validate_input_directory(input_dir):
        print(f"ERROR: {error}")
        sys.exit(1)
    
    if error := validate_model_name(model, get_available_models()):
        print(f"ERROR: {error}")
        sys.exit(1)
    
    # ... actual work

# Easy to test
def test_validate_model_name_rejects_unknown():
    error = validate_model_name('unknown', ['llava', 'gpt-4'])
    assert error is not None
    assert 'unknown' in error
    assert 'llava' in error  # Shows available models
```

**Priority**: 🟢 LOW - Easy but valuable

**Estimated Effort**: 1 day

---

### 7. Make Retry Logic Configurable

Don't make tests wait for real retry delays:

```python
# BEFORE: Hardcoded waits
def call_api_with_retry(url: str, data: dict) -> dict:
    for attempt in range(3):
        try:
            return requests.post(url, json=data).json()
        except RequestException:
            if attempt < 2:
                time.sleep(30)  # Tests wait 60 seconds!
            raise

# AFTER: Configurable delays
def call_api_with_retry(
    url: str,
    data: dict,
    max_attempts: int = 3,
    retry_delay: float = 30.0
) -> dict:
    for attempt in range(max_attempts):
        try:
            return requests.post(url, json=data).json()
        except RequestException:
            if attempt < max_attempts - 1:
                time.sleep(retry_delay)
            raise

# Tests run instantly
def test_api_retry_logic():
    with mock_api_failing_twice():
        result = call_api_with_retry(
            "http://api.test/endpoint",
            {"test": "data"},
            max_attempts=3,
            retry_delay=0.01  # 10ms instead of 30s!
        )
        assert result is not None
```

**Priority**: 🟢 LOW - Quick improvement

**Estimated Effort**: 2 hours

---

## Implementation Roadmap

### Phase 1: Critical Path (Week 1-2)
**Goal**: Enable automated E2E testing

1. ✅ Create end-to-end test script (`test_and_build.bat`)
2. ⚠️ Refactor `WorkflowOrchestrator` from `workflow.py::main()`
3. ⚠️ Create `AIProvider` interface and mock implementations
4. ✅ Add critical E2E tests that use mock providers

**Success Criteria**: Can run `test_and_build.bat` and get full E2E verification

### Phase 2: Core Testability (Week 3-4)
**Goal**: High-coverage unit tests

1. Extract validation functions
2. Make retry logic configurable
3. Add `WorkflowConfig` dataclass
4. Write unit tests for all extracted functions
5. Achieve 80%+ coverage on core modules

**Success Criteria**: `pytest --cov` shows 80%+ coverage on `scripts/`

### Phase 3: Test Isolation (Week 5-6)
**Goal**: Eliminate test interference

1. Remove global config state
2. Separate logging from business logic
3. Fix flaky tests
4. Add filesystem abstraction for critical paths

**Success Criteria**: All tests pass consistently in parallel

### Phase 4: Maintenance (Ongoing)
**Goal**: Keep tests valuable

1. All new features include tests
2. All bugs include regression tests
3. Flaky tests fixed immediately
4. Test suite runs in CI

**Success Criteria**: Zero manual testing for new features

---

## Anti-Patterns to Avoid

### ❌ Don't Mock What You Don't Own

**Bad**:
```python
def test_image_processing(monkeypatch):
    # Mocking PIL internals is fragile
    monkeypatch.setattr("PIL.Image.open", fake_open)
```

**Good**:
```python
# Wrap third-party code in own interface
class ImageLoader:
    def load(self, path: Path) -> Image:
        return Image.open(path)

# Mock your interface
def test_image_processing():
    class FakeImageLoader:
        def load(self, path: Path) -> Image:
            return create_fake_image()
```

### ❌ Don't Test Implementation Details

**Bad**:
```python
def test_workflow_calls_steps_in_order():
    # Brittle - breaks if implementation changes
    with mock.patch.object(workflow, '_step1') as m1, \
         mock.patch.object(workflow, '_step2') as m2:
        workflow.run()
        assert m1.call_count == 1
        assert m2.call_count == 1
        assert m1.called_before(m2)
```

**Good**:
```python
def test_workflow_produces_expected_output():
    # Tests behavior, not implementation
    result = workflow.run(test_input)
    assert result.has_descriptions
    assert result.has_html_report
```

### ❌ Don't Share Mutable State Between Tests

**Bad**:
```python
# Module-level fixture - shared between tests!
TEST_CONFIG = WorkflowConfig(...)

def test_workflow_1():
    TEST_CONFIG.model = 'model-a'
    # ...

def test_workflow_2():
    # BUG: TEST_CONFIG.model might still be 'model-a' from test_workflow_1!
    assert TEST_CONFIG.model == 'default-model'
```

**Good**:
```python
@pytest.fixture
def workflow_config():
    # Fresh config for each test
    return WorkflowConfig(model='default-model')

def test_workflow_1(workflow_config):
    workflow_config.model = 'model-a'
    # Isolated - doesn't affect other tests
```

---

## Measuring Success

### Before Refactoring
- ❌ Manual testing required for each feature
- ❌ Bugs found by users, not tests
- ❌ Fear of refactoring (might break things)
- ❌ "It worked on my machine" syndrome

### After Refactoring
- ✅ Automated tests catch bugs before users
- ✅ Confident refactoring with tests as safety net
- ✅ New features include tests from day 1
- ✅ CI prevents broken code from merging

### Metrics to Track
- **Test Coverage**: Target 80%+ on core modules
- **Test Speed**: Unit tests < 10s, full suite < 5min
- **Build Reliability**: 0 manual steps to verify build
- **Bug Escape Rate**: Bugs caught by tests vs. users

---

## Getting Help

### Resources
- [Effective Python Testing](https://testdriven.io/blog/testing-python/)
- [Writing Testable Code](https://testing.googleblog.com/2008/08/by-miko-hevery-so-you-decided-to.html)
- [Dependency Injection in Python](https://python-dependency-injector.ets-labs.org/)

### Code Review Checklist
When reviewing new code, ask:
- [ ] Can this be tested without external dependencies?
- [ ] Are dependencies injected or hardcoded?
- [ ] Does this function do one thing well?
- [ ] Would I be able to write a test for this in 5 minutes?

If answer is "no" to any → needs refactoring before merge.

---

**Last Updated**: November 1, 2025  
**Next Review**: After Phase 1 completion
