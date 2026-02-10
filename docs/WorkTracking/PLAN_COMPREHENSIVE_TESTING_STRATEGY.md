# Comprehensive Testing Strategy for Image-Description-Toolkit

**Created**: February 10, 2026  
**Status**: Planning  
**Priority**: Critical  
**Branch**: wxpython

## Executive Summary

Image-Description-Toolkit has grown from a small tool to a multi-application suite with ~15,000+ lines of Python code across CLI tools and GUI applications. While foundational tests exist, critical gaps in AI provider logic (1,320 untested lines), GUI worker threads (4,000+ lines), and workflow orchestration create significant regression risk. This plan establishes a comprehensive testing strategy treating testing as a first-class citizen, with a phased approach prioritizing AI provider logic, followed by GUI worker automation, and culminating in full CI/CD integration.

**Key Metrics Goal**: 80% code coverage, <3 min test suite, 100% regression protection, automated pre-commit validation.

---

## Background: Why Comprehensive Testing Matters

### Current State
- ✅ **30+ test files exist** with pytest infrastructure
- ✅ **Regression suite** catches known bug patterns (imports, variable consistency)
- ✅ **Integration tests** cover EXIF preservation, workflow E2E
- ❌ **Critical gaps**: AI providers (1,320 lines untested), GUI logic (4,000+ lines), workflow steps
- ❌ **No CI/CD**: Tests run manually, easy to skip
- ❌ **No coverage tracking**: Unknown actual coverage percentage
- ❌ **No pre-commit hooks**: Breaking changes reach main branch

### Why This Matters
**Historical Regression Examples** (from migration audit):
1. Variable renaming bugs (`unique_source_count` undefined) in 2,768-line workflow.py
2. PyInstaller import breaks (23% of commits were fixes during migration)
3. EXIF metadata loss through conversion pipeline
4. GUI accessibility regressions (keyboard navigation)
5. Config resolution failures in frozen executables

**Cost of Regressions**:
- 🔴 **User Impact**: Data loss, crashes, broken workflows
- 🔴 **Developer Time**: 23% of commits fixing bugs that tests could have caught
- 🔴 **Release Confidence**: Cannot safely refactor large files (workflow.py = 2,768 lines)

---

## Testing Philosophy

### Test Pyramid for IDT

```
        ╱╲
       ╱  ╲ E2E/Smoke (~10%)
      ╱────╲ - Frozen executable runs
     ╱  In- ╲ - Critical user paths
    ╱ tegra- ╲ - Cross-platform builds
   ╱   tion   ╲
  ╱  (~20%)    ╲ Integration (~20%)
 ╱──────────────╲ - Multi-component workflows
╱                ╲ - Config cascading
──────────────────── - EXIF preservation
    Unit Tests      - Worker thread lifecycle
     (~70%)
  • Pure functions      
  • Data models         
  • AI provider logic   
  • Config resolution   
  • String utilities    
```

### CLI vs GUI Test Automation Potential

| Component | Automation Potential | Strategy |
|-----------|---------------------|----------|
| **CLI Tool (idt)** | **100%** | Pure functions + mocked external APIs |
| **Business Logic** | **100%** | Unit tests with dependency injection |
| **Worker Threads** | **90%** | Test thread logic without GUI rendering |
| **Dialogs/State** | **80%** | Test state management, mock wx events |
| **Visual UI** | **20%** | Manual accessibility audits only |

**Rationale**: wxPython UI test frameworks exist (wx.UIActionSimulator) but are fragile and slow. Focus automation on business logic and worker threads where most bugs occur.

---

## Comprehensive Testing Strategy

### 1. Test Infrastructure & Tooling

**Goal**: Establish robust test foundation with coverage tracking, fixtures, and mocking.

#### 1.1 Coverage Tracking
**Tool**: `pytest-cov` with HTML reports

**Configuration**: Add to `pyproject.toml`:
```toml
[tool.pytest.ini_options]
testpaths = ["pytest_tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "-v",
    "--cov=scripts",
    "--cov=imagedescriber",
    "--cov=viewer",
    "--cov=analysis",
    "--cov=models",
    "--cov=shared",
    "--cov-report=html:htmlcov",
    "--cov-report=term-missing",
    "--cov-fail-under=80"  # Enforce 80% coverage
]
markers = [
    "unit: Pure unit tests (no external dependencies)",
    "integration: Multi-component integration tests",
    "smoke: Quick smoke tests for critical paths",
    "slow: Tests taking >5 seconds",
    "gui: GUI-specific tests requiring wxPython",
    "frozen: Tests requiring built executable"
]
```

**Files**: Update existing [run_unit_tests.py](run_unit_tests.py) to use pytest-cov.

#### 1.2 Fixture Library Expansion
**Location**: [pytest_tests/conftest.py](pytest_tests/conftest.py)

**New Fixtures Needed**:
```python
# Mock AI Providers
@pytest.fixture
def mock_ollama_provider():
    """Returns mock OllamaProvider with configurable responses"""
    with patch('imagedescriber.ai_providers.OllamaProvider') as mock:
        mock.return_value.describe_image.return_value = "Test description"
        mock.return_value.is_available.return_value = True
        yield mock

@pytest.fixture
def mock_openai_provider():
    """Returns mock OpenAIProvider with token tracking"""
    with patch('imagedescriber.ai_providers.OpenAIProvider') as mock:
        mock_instance = MagicMock()
        mock_instance.describe_image.return_value = "Test description"
        mock_instance.last_token_usage = {'prompt': 10, 'completion': 20}
        mock.return_value = mock_instance
        yield mock

# Test Image Fixtures
@pytest.fixture
def test_image_jpg(tmp_path):
    """Create valid test JPEG with EXIF"""
    from PIL import Image
    import piexif
    
    img = Image.new('RGB', (100, 100), color='red')
    exif_dict = {
        "0th": {piexif.ImageIFD.DateTime: "2026:01:15 14:30:00"},
        "Exif": {piexif.ExifIFD.DateTimeOriginal: "2026:01:15 14:30:00"}
    }
    exif_bytes = piexif.dump(exif_dict)
    
    img_path = tmp_path / "test_image.jpg"
    img.save(str(img_path), "jpeg", exif=exif_bytes)
    return img_path

@pytest.fixture
def test_image_heic(tmp_path):
    """Create mock HEIC file for conversion testing"""
    # Use pillow_heif if available, otherwise return mock path
    try:
        from PIL import Image
        import pillow_heif
        pillow_heif.register_heif_opener()
        
        img = Image.new('RGB', (100, 100), color='blue')
        img_path = tmp_path / "test_image.heic"
        img.save(str(img_path), format='HEIF')
        return img_path
    except ImportError:
        # Return path for testing error handling
        return tmp_path / "mock.heic"

# Workspace Fixtures
@pytest.fixture
def empty_workspace(tmp_path):
    """Returns new ImageWorkspace with temp directory"""
    from imagedescriber.data_models import ImageWorkspace
    ws = ImageWorkspace()
    ws.workspace_dir = tmp_path
    return ws

@pytest.fixture
def workspace_with_images(tmp_path, test_image_jpg):
    """Returns workspace with test images loaded"""
    from imagedescriber.data_models import ImageWorkspace, ImageItem
    ws = ImageWorkspace()
    ws.workspace_dir = tmp_path
    
    # Add test images
    for i in range(3):
        item_path = tmp_path / f"image_{i}.jpg"
        shutil.copy(test_image_jpg, item_path)
        ws.items[str(item_path)] = ImageItem(str(item_path))
    
    return ws

# Config Fixtures
@pytest.fixture
def test_workflow_config(tmp_path):
    """Returns workflow config with test settings"""
    config = {
        "default_provider": "ollama",
        "default_model": "test-model",
        "default_prompt_style": "narrative",
        "video_extraction": {"fps": 1},
        "image_conversion": {"quality": 85}
    }
    config_path = tmp_path / "workflow_config.json"
    with open(config_path, 'w') as f:
        json.dump(config, f)
    return config_path
```

**Files Modified**: [pytest_tests/conftest.py](pytest_tests/conftest.py)

#### 1.3 Mock Response Library
**New File**: `pytest_tests/fixtures/mock_responses.py`

**Purpose**: Centralized realistic mock responses for AI providers, API calls, subprocess outputs.

```python
"""Mock responses for external dependencies"""

# AI Provider Responses
MOCK_OLLAMA_RESPONSE = {
    "model": "llava:7b",
    "created_at": "2026-02-10T10:30:00Z",
    "response": "A scenic mountain landscape with snow-capped peaks.",
    "done": True
}

MOCK_OPENAI_RESPONSE = {
    "id": "chatcmpl-test123",
    "object": "chat.completion",
    "created": 1707565800,
    "model": "gpt-4o",
    "choices": [{
        "index": 0,
        "message": {
            "role": "assistant",
            "content": "A modern office workspace with computers."
        },
        "finish_reason": "stop"
    }],
    "usage": {
        "prompt_tokens": 85,
        "completion_tokens": 12,
        "total_tokens": 97
    }
}

MOCK_CLAUDE_RESPONSE = {
    "id": "msg_test456",
    "type": "message",
    "role": "assistant",
    "content": [{
        "type": "text",
        "text": "A vibrant sunset over the ocean."
    }],
    "model": "claude-opus-4",
    "usage": {
        "input_tokens": 120,
        "output_tokens": 15
    }
}

# FFProbe Video Metadata
MOCK_FFPROBE_OUTPUT = {
    "format": {
        "duration": "10.5",
        "size": "1048576",
        "bit_rate": "800000"
    },
    "streams": [{
        "codec_type": "video",
        "width": 1920,
        "height": 1080,
        "r_frame_rate": "30/1"
    }]
}

# EXIF Data
MOCK_EXIF_DATA = {
    "datetime": {
        "DateTimeOriginal": "2026-01-15 14:30:00",
        "DateTimeDigitized": "2026-01-15 14:30:00"
    },
    "location": {
        "latitude": 47.6062,
        "longitude": -122.3321,
        "altitude": 50.0
    },
    "camera": {
        "make": "Apple",
        "model": "iPhone 15 Pro",
        "lens_model": "iPhone 15 Pro back camera"
    },
    "technical": {
        "iso": "100",
        "aperture": "f/1.78",
        "shutter_speed": "1/120",
        "focal_length": "6.86mm"
    }
}
```

**Files Created**: [pytest_tests/fixtures/mock_responses.py](pytest_tests/fixtures/mock_responses.py)

#### 1.4 Test Data Repository
**Location**: [test_data/](test_data/) (expand existing)

**Structure**:
```
test_data/
├── images/
│   ├── jpg/
│   │   ├── with_exif.jpg (100x100, full EXIF)
│   │   ├── without_exif.jpg (100x100, no metadata)
│   │   └── gps_tagged.jpg (100x100, GPS coords)
│   ├── heic/
│   │   ├── iphone_photo.heic (small test file)
│   │   └── corrupted.heic (test error handling)
│   └── png/
│       └── screenshot.png (no EXIF support)
├── videos/
│   ├── short_clip.mp4 (5 sec, 30fps)
│   └── variable_fps.mov (10 sec, variable framerate)
├── configs/
│   ├── valid_workflow_config.json
│   ├── minimal_config.json
│   └── invalid_config.json (test error handling)
└── workspaces/
    ├── empty.idw (new workspace)
    ├── single_image.idw (1 image with description)
    └── multi_directory.idw (complex workspace)
```

**Rationale**: Deterministic test data prevents flaky tests from filesystem variations.

---

### 2. CLI Tool Testing (100% Automation)

**Goal**: Comprehensive coverage of all CLI commands with mocked external dependencies.

#### 2.1 Command Routing Tests
**New File**: `pytest_tests/unit/test_idt_cli_commands.py`

**Coverage Target**: [idt/idt_cli.py](idt/idt_cli.py) (982 lines)

**Tests**:
```python
@pytest.mark.unit
class TestIDTCommandRouting:
    """Test CLI command parsing and routing"""
    
    def test_workflow_command_routes_correctly(self, monkeypatch):
        """Verify 'idt workflow' routes to scripts.workflow.main()"""
        with patch('scripts.workflow.main') as mock_main:
            sys.argv = ['idt', 'workflow', 'testimages']
            main()
            mock_main.assert_called_once()
    
    def test_guideme_command_routes_correctly(self):
        """Verify 'idt guideme' routes to guided_workflow"""
        with patch('scripts.guided_workflow.run_guided_workflow') as mock_guide:
            sys.argv = ['idt', 'guideme']
            main()
            mock_guide.assert_called_once()
    
    def test_stats_command_with_args(self):
        """Verify 'idt stats' passes args correctly"""
        with patch('analysis.stats_analysis.main') as mock_stats:
            sys.argv = ['idt', 'stats', 'wf_test_dir']
            main()
            mock_stats.assert_called_with(['wf_test_dir'])
    
    def test_invalid_command_shows_help(self, capsys):
        """Verify unknown command shows help and exits"""
        sys.argv = ['idt', 'invalid_command']
        with pytest.raises(SystemExit):
            main()
        captured = capsys.readouterr()
        assert "Available commands:" in captured.out
    
    def test_version_command(self, capsys):
        """Verify 'idt version' shows version info"""
        sys.argv = ['idt', 'version']
        main()
        captured = capsys.readouterr()
        assert "Image-Description-Toolkit" in captured.out
        # Version should match VERSION file
        with open('VERSION') as f:
            version = f.read().strip()
        assert version in captured.out
```

**Files Created**: [pytest_tests/unit/test_idt_cli_commands.py](pytest_tests/unit/test_idt_cli_commands.py)

#### 2.2 Workflow Orchestration Tests
**New File**: `pytest_tests/unit/test_workflow_orchestrator.py`

**Coverage Target**: [scripts/workflow.py](scripts/workflow.py) (2,768 lines)

**Critical Functions to Test**:
1. `main()` - Full workflow orchestration
2. `parse_workflow_state()` - Resume logic
3. `get_effective_model()` - Config resolution
4. `get_effective_prompt_style()` - Prompt resolution
5. `sanitize_name()` - Filename sanitization
6. `get_path_identifier_2_components()` - Workflow dir naming

**Tests**:
```python
@pytest.mark.unit
class TestWorkflowOrchestration:
    """Test workflow.py orchestration logic"""
    
    def test_effective_model_command_line_overrides_config(self):
        """CLI --model arg should override config default"""
        config = {"default_model": "config-model"}
        result = get_effective_model("cli-model", config)
        assert result == "cli-model"
    
    def test_effective_model_uses_config_default(self):
        """Use config default_model when no CLI override"""
        config = {"default_model": "config-model"}
        result = get_effective_model(None, config)
        assert result == "config-model"
    
    def test_workflow_directory_naming_convention(self):
        """Workflow dirs should be: wf_YYYYMMDD_HHMMSS_model_prompt"""
        model = "GPT-4o"
        prompt = "Detailed Description"
        
        result = get_path_identifier_2_components(model, prompt)
        
        # Should sanitize special characters
        assert "GPT-4o" in result
        assert "Detailed-Description" in result or "DetailedDescription" in result
        assert " " not in result  # No spaces
    
    def test_parse_workflow_state_finds_completed_steps(self, tmp_path):
        """Should detect which workflow steps completed"""
        workflow_dir = tmp_path / "wf_test"
        workflow_dir.mkdir()
        
        # Create markers for completed steps
        (workflow_dir / "input_images").mkdir()
        (workflow_dir / "logs").mkdir()
        (workflow_dir / "descriptions.txt").touch()
        
        state = parse_workflow_state(workflow_dir)
        
        assert state['has_extracted_frames'] is False  # No video processing
        assert state['has_converted_images'] is True  # input_images exists
        assert state['has_descriptions'] is True  # descriptions.txt exists
```

**Files Created**: [pytest_tests/unit/test_workflow_orchestrator.py](pytest_tests/unit/test_workflow_orchestrator.py)

#### 2.3 Analysis Tool Tests
**New Files**:
- `pytest_tests/unit/test_stats_analysis.py`
- `pytest_tests/unit/test_content_analysis.py`
- `pytest_tests/unit/test_combine_descriptions.py`

**Coverage Targets**:
- [analysis/stats_analysis.py](analysis/stats_analysis.py)
- [analysis/content_analysis.py](analysis/content_analysis.py)
- [analysis/combine_workflow_descriptions.py](analysis/combine_workflow_descriptions.py)

**Sample Test**:
```python
@pytest.mark.unit
def test_stats_calculation_from_workflow(test_workflow_dir):
    """Calculate accurate stats from workflow directory"""
    # Mock workflow with 3 images, known token counts
    # ... setup ...
    
    stats = calculate_workflow_stats(test_workflow_dir)
    
    assert stats['total_images'] == 3
    assert stats['total_tokens'] == 300  # 100 per image
    assert stats['avg_tokens_per_image'] == 100
    assert stats['estimated_cost'] > 0  # For paid providers
```

---

### 3. AI Provider Testing (Priority #1)

**Goal**: Comprehensive coverage of AI provider logic with mocked API calls.

#### 3.1 Provider Unit Tests
**New File**: `pytest_tests/unit/test_ai_providers.py`

**Coverage Target**: [imagedescriber/ai_providers.py](imagedescriber/ai_providers.py) (1,320 lines)

**Tests for Each Provider**:
```python
@pytest.mark.unit
class TestOllamaProvider:
    """Test OllamaProvider without external dependencies"""
    
    @patch('requests.post')
    def test_describe_image_success(self, mock_post, test_image_jpg):
        """Ollama API success returns description"""
        from imagedescriber.ai_providers import OllamaProvider
        from pytest_tests.fixtures.mock_responses import MOCK_OLLAMA_RESPONSE
        
        # Mock successful API response
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = MOCK_OLLAMA_RESPONSE
        
        provider = OllamaProvider()
        description = provider.describe_image(
            str(test_image_jpg), 
            "Describe this image", 
            "llava:7b"
        )
        
        assert description == MOCK_OLLAMA_RESPONSE["response"]
        assert mock_post.called
    
    @patch('requests.post')
    def test_describe_image_retry_on_500_error(self, mock_post, test_image_jpg):
        """Ollama should retry on HTTP 500 errors"""
        # First call fails, second succeeds
        mock_post.side_effect = [
            MagicMock(status_code=500, text="Internal Server Error"),
            MagicMock(status_code=200, json=lambda: MOCK_OLLAMA_RESPONSE)
        ]
        
        provider = OllamaProvider()
        description = provider.describe_image(
            str(test_image_jpg), 
            "Describe", 
            "llava:7b"
        )
        
        assert description == MOCK_OLLAMA_RESPONSE["response"]
        assert mock_post.call_count == 2  # Retried once
    
    @patch('requests.post')
    def test_describe_image_max_retries_exceeded(self, mock_post, test_image_jpg):
        """Should fail after max retries"""
        # All calls fail
        mock_post.return_value.status_code = 500
        mock_post.return_value.text = "Server Error"
        
        provider = OllamaProvider()
        
        with pytest.raises(Exception) as exc_info:
            provider.describe_image(str(test_image_jpg), "Describe", "llava:7b")
        
        assert "HTTP 500" in str(exc_info.value) or "retry" in str(exc_info.value).lower()
        assert mock_post.call_count == 3  # Max retries = 3
    
    @patch('requests.get')
    def test_get_available_models_success(self, mock_get):
        """Should return list of local models"""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "models": [
                {"name": "llava:7b"},
                {"name": "mistral:latest"},
                {"name": "phi3-cloud"}  # Should be filtered out
            ]
        }
        
        provider = OllamaProvider()
        models = provider.get_available_models()
        
        assert "llava:7b" in models
        assert "mistral:latest" in models
        assert "phi3-cloud" not in models  # Cloud models filtered

@pytest.mark.unit
class TestOpenAIProvider:
    """Test OpenAIProvider with mocked SDK"""
    
    @patch('openai.OpenAI')
    def test_describe_image_with_token_tracking(self, mock_openai, test_image_jpg):
        """OpenAI should return description and track tokens"""
        from imagedescriber.ai_providers import OpenAIProvider
        from pytest_tests.fixtures.mock_responses import MOCK_OPENAI_RESPONSE
        
        # Mock OpenAI client
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = MagicMock(
            **MOCK_OPENAI_RESPONSE
        )
        mock_openai.return_value = mock_client
        
        provider = OpenAIProvider(api_key="test-key")
        description = provider.describe_image(
            str(test_image_jpg),
            "Describe this",
            "gpt-4o"
        )
        
        assert description == MOCK_OPENAI_RESPONSE["choices"][0]["message"]["content"]
        assert provider.last_token_usage["prompt_tokens"] == 85
        assert provider.last_token_usage["completion_tokens"] == 12
    
    @patch('openai.OpenAI')
    def test_describe_image_rate_limit_retry(self, mock_openai, test_image_jpg):
        """Should retry on rate limit errors"""
        mock_client = MagicMock()
        
        # First call raises rate limit error, second succeeds
        from openai import RateLimitError
        mock_client.chat.completions.create.side_effect = [
            RateLimitError("Rate limit exceeded"),
            MagicMock(**MOCK_OPENAI_RESPONSE)
        ]
        mock_openai.return_value = mock_client
        
        provider = OpenAIProvider(api_key="test-key")
        description = provider.describe_image(
            str(test_image_jpg),
            "Describe",
            "gpt-4o"
        )
        
        assert description is not None
        assert mock_client.chat.completions.create.call_count == 2

@pytest.mark.unit
class TestClaudeProvider:
    """Test ClaudeProvider with mocked SDK"""
    
    @patch('anthropic.Anthropic')
    def test_describe_image_success(self, mock_anthropic, test_image_jpg):
        """Claude should return description"""
        from imagedescriber.ai_providers import ClaudeProvider
        from pytest_tests.fixtures.mock_responses import MOCK_CLAUDE_RESPONSE
        
        mock_client = MagicMock()
        mock_client.messages.create.return_value = MagicMock(
            **MOCK_CLAUDE_RESPONSE
        )
        mock_anthropic.return_value = mock_client
        
        provider = ClaudeProvider(api_key="test-key")
        description = provider.describe_image(
            str(test_image_jpg),
            "Describe",
            "claude-opus-4"
        )
        
        assert description == MOCK_CLAUDE_RESPONSE["content"][0]["text"]
        assert provider.last_token_usage["input_tokens"] == 120
```

**Files Created**: [pytest_tests/unit/test_ai_providers.py](pytest_tests/unit/test_ai_providers.py)

#### 3.2 Retry Logic Verification
**Focus**: Exponential backoff, max retries, error handling

**Test Pattern**:
```python
@pytest.mark.unit
def test_retry_decorator_exponential_backoff():
    """Verify exponential backoff timing"""
    call_times = []
    
    @retry_on_api_error(max_retries=3, base_delay=1.0)
    def failing_function():
        call_times.append(time.time())
        raise Exception("API Error")
    
    with pytest.raises(Exception):
        failing_function()
    
    # Check delays approximately follow exponential backoff
    assert len(call_times) == 3  # Initial + 2 retries
    delay1 = call_times[1] - call_times[0]
    delay2 = call_times[2] - call_times[1]
    
    assert 0.9 < delay1 < 1.1  # ~1s delay
    assert 1.9 < delay2 < 2.1  # ~2s delay (exponential)
```

---

### 4. Data Model Testing

**Goal**: Ensure workspace serialization, multi-directory operations, and chat sessions work correctly.

#### 4.1 Data Model Unit Tests
**New File**: `pytest_tests/unit/test_data_models.py`

**Coverage Target**: [imagedescriber/data_models.py](imagedescriber/data_models.py) (278 lines)

**Tests**:
```python
@pytest.mark.unit
class TestImageDescription:
    """Test ImageDescription serialization"""
    
    def test_to_dict_serialization(self):
        """Serialize description to dict"""
        from imagedescriber.data_models import ImageDescription
        
        desc = ImageDescription(
            description="Test description",
            provider="ollama",
            model="llava:7b",
            prompt_style="narrative"
        )
        
        result = desc.to_dict()
        
        assert result["description"] == "Test description"
        assert result["provider"] == "ollama"
        assert result["model"] == "llava:7b"
        assert "timestamp" in result
    
    def test_from_dict_deserialization(self):
        """Deserialize description from dict"""
        from imagedescriber.data_models import ImageDescription
        
        data = {
            "description": "Test",
            "provider": "openai",
            "model": "gpt-4o",
            "prompt_style": "detailed",
            "timestamp": "2026-02-10T10:30:00"
        }
        
        desc = ImageDescription.from_dict(data)
        
        assert desc.description == "Test"
        assert desc.provider == "openai"
        assert desc.timestamp == "2026-02-10T10:30:00"

@pytest.mark.unit
class TestImageWorkspace:
    """Test ImageWorkspace operations"""
    
    def test_add_directory(self, tmp_path, test_image_jpg):
        """Add directory should load all images"""
        from imagedescriber.data_models import ImageWorkspace
        
        # Create test directory with images
        test_dir = tmp_path / "test"
        test_dir.mkdir()
        for i in range(3):
            shutil.copy(test_image_jpg, test_dir / f"image_{i}.jpg")
        
        ws = ImageWorkspace()
        ws.add_directory(str(test_dir))
        
        assert len(ws.items) == 3
        assert ws.workspace_dir == str(test_dir)
    
    def test_workspace_serialization_roundtrip(self, workspace_with_images):
        """Save and load workspace preserves all data"""
        from imagedescriber.data_models import ImageWorkspace
        
        # Add some descriptions
        for item in workspace_with_images.items.values():
            item.add_description("Test desc", "ollama", "llava:7b", "narrative")
        
        # Serialize
        data = workspace_with_images.to_dict()
        
        # Deserialize
        restored = ImageWorkspace.from_dict(data)
        
        assert len(restored.items) == len(workspace_with_images.items)
        for original_item, restored_item in zip(
            workspace_with_images.items.values(),
            restored.items.values()
        ):
            assert len(restored_item.descriptions) == len(original_item.descriptions)
    
    def test_multi_directory_workspace(self, tmp_path, test_image_jpg):
        """Workspace can handle images from multiple directories"""
        from imagedescriber.data_models import ImageWorkspace
        
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir1.mkdir()
        dir2.mkdir()
        
        shutil.copy(test_image_jpg, dir1 / "img1.jpg")
        shutil.copy(test_image_jpg, dir2 / "img2.jpg")
        
        ws = ImageWorkspace()
        ws.add_directory(str(dir1))
        ws.add_directory(str(dir2))
        
        assert len(ws.items) == 2
        # Workspace dir should be common parent
        assert Path(ws.workspace_dir) in [tmp_path, Path.cwd()]
```

**Files Created**: [pytest_tests/unit/test_data_models.py](pytest_tests/unit/test_data_models.py)

---

### 5. GUI Worker Thread Testing (Moderate Automation)

**Goal**: Test worker thread business logic without rendering GUI.

#### 5.1 Worker Thread Unit Tests
**New File**: `pytest_tests/unit/test_gui_workers.py`

**Coverage Target**: [imagedescriber/workers_wx.py](imagedescriber/workers_wx.py) (1,421 lines)

**Strategy**: Mock wx.PostEvent, test worker logic in isolation.

**Tests**:
```python
@pytest.mark.gui
class TestProcessingWorker:
    """Test ProcessingWorker without GUI rendering"""
    
    @patch('wx.PostEvent')
    @patch('imagedescriber.ai_providers.get_available_providers')
    def test_worker_success_posts_complete_event(
        self, 
        mock_providers, 
        mock_post_event,
        test_image_jpg
    ):
        """Worker should post ProcessingCompleteEvent on success"""
        from imagedescriber.workers_wx import ProcessingWorker
        
        # Mock AI provider
        mock_provider = MagicMock()
        mock_provider.describe_image.return_value = "Test description"
        mock_providers.return_value = {"ollama": mock_provider}
        
        # Create worker
        mock_parent = MagicMock()
        worker = ProcessingWorker(
            mock_parent,
            str(test_image_jpg),
            "ollama",
            "llava:7b",
            "narrative"
        )
        
        # Run worker
        worker.run()
        
        # Verify event posted
        assert mock_post_event.called
        posted_event = mock_post_event.call_args[0][1]
        assert posted_event.description == "Test description"
        assert posted_event.file_path == str(test_image_jpg)
    
    @patch('wx.PostEvent')
    @patch('imagedescriber.ai_providers.get_available_providers')
    def test_worker_failure_posts_failed_event(
        self,
        mock_providers,
        mock_post_event,
        test_image_jpg
    ):
        """Worker should post ProcessingFailedEvent on error"""
        from imagedescriber.workers_wx import ProcessingWorker
        
        # Mock AI provider that fails
        mock_provider = MagicMock()
        mock_provider.describe_image.side_effect = Exception("API Error")
        mock_providers.return_value = {"ollama": mock_provider}
        
        mock_parent = MagicMock()
        worker = ProcessingWorker(
            mock_parent,
            str(test_image_jpg),
            "ollama",
            "llava:7b",
            "narrative"
        )
        
        worker.run()
        
        # Verify failure event posted
        assert mock_post_event.called
        posted_event = mock_post_event.call_args[0][1]
        assert hasattr(posted_event, 'error')
        assert "API Error" in str(posted_event.error)

@pytest.mark.gui
class TestBatchProcessingWorker:
    """Test BatchProcessingWorker orchestration"""
    
    @patch('wx.PostEvent')
    @patch('imagedescriber.workers_wx.ProcessingWorker')
    def test_batch_worker_processes_all_images(
        self,
        mock_worker_class,
        mock_post_event,
        workspace_with_images
    ):
        """Batch worker should process each image sequentially"""
        from imagedescriber.workers_wx import BatchProcessingWorker
        
        file_paths = list(workspace_with_images.items.keys())
        
        # Mock individual workers
        mock_worker_instance = MagicMock()
        mock_worker_class.return_value = mock_worker_instance
        
        mock_parent = MagicMock()
        batch_worker = BatchProcessingWorker(
            mock_parent,
            file_paths,
            "ollama",
            "llava:7b",
            "narrative"
        )
        
        batch_worker.run()
        
        # Verify worker created for each image
        assert mock_worker_class.call_count == len(file_paths)
        assert mock_worker_instance.start.call_count == len(file_paths)
    
    @patch('wx.PostEvent')
    def test_batch_worker_cancel_stops_processing(self, mock_post_event):
        """Calling cancel() should stop batch processing"""
        from imagedescriber.workers_wx import BatchProcessingWorker
        
        file_paths = ["img1.jpg", "img2.jpg", "img3.jpg"]
        
        mock_parent = MagicMock()
        batch_worker = BatchProcessingWorker(
            mock_parent,
            file_paths,
            "ollama",
            "llava:7b",
            "narrative"
        )
        
        # Cancel immediately
        batch_worker.cancel()
        batch_worker.run()
        
        # Should not process images after cancel
        # (implementation detail: check _cancel flag)
        assert batch_worker._cancel is True
```

**Files Created**: [pytest_tests/unit/test_gui_workers.py](pytest_tests/unit/test_gui_workers.py)

#### 5.2 Dialog State Management Tests
**New File**: `pytest_tests/unit/test_gui_dialogs.py`

**Coverage Target**: [imagedescriber/dialogs_wx.py](imagedescriber/dialogs_wx.py)

**Strategy**: Test dialog state logic without showing GUI.

**Sample Test**:
```python
@pytest.mark.gui
class TestProcessingOptionsDialog:
    """Test ProcessingOptionsDialog state management"""
    
    def test_dialog_initializes_with_config(self):
        """Dialog should populate from config"""
        # Note: May need wx.App() context
        # Testing state management, not visual rendering
        pass  # Implementation depends on dialog refactoring
```

---

### 6. Integration Testing

**Goal**: Test multi-component interactions with realistic scenarios.

#### 6.1 Full Workflow Integration Tests
**Expand**: [pytest_tests/integration/test_workflow_integration.py](pytest_tests/integration/test_workflow_integration.py)

**New Tests**:
```python
@pytest.mark.integration
@pytest.mark.slow
def test_workflow_with_mixed_file_types(tmp_path, test_image_jpg, test_image_heic):
    """Workflow should handle JPG + HEIC + video"""
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    
    # Mix of file types
    shutil.copy(test_image_jpg, input_dir / "photo.jpg")
    shutil.copy(test_image_heic, input_dir / "iphone.heic")
    # Create mock video (not actually testing video extraction here)
    
    with patch('imagedescriber.ai_providers.get_available_providers') as mock:
        mock_provider = MagicMock()
        mock_provider.describe_image.return_value = "Test description"
        mock.return_value = {"ollama": mock_provider}
        
        result = run_workflow(
            input_dir=str(input_dir),
            provider="ollama",
            model="llava:7b",
            prompt_style="narrative"
        )
        
        # Verify workflow completed
        assert result['success'] is True
        assert result['images_processed'] == 2  # JPG + converted HEIC

@pytest.mark.integration
def test_config_cascading_cli_overrides_file(tmp_path, test_workflow_config):
    """CLI args should override config file settings"""
    # Set environment variable
    os.environ['IDT_CONFIG_DIR'] = str(tmp_path)
    
    # Config file says "model-from-file"
    # CLI says "model-from-cli"
    # CLI should win
    
    result = get_effective_model("model-from-cli", config_path=test_workflow_config)
    
    assert result == "model-from-cli"
```

---

### 7. Frozen Executable Testing

**Goal**: Verify PyInstaller builds work correctly.

#### 7.1 Build Verification Tests
**Expand**: [pytest_tests/integration/test_frozen_executable.py](pytest_tests/integration/test_frozen_executable.py)

**Tests**:
```python
@pytest.mark.frozen
@pytest.mark.slow
def test_idt_exe_workflow_command(built_executable_path):
    """Test idt.exe workflow command runs"""
    result = subprocess.run(
        [str(built_executable_path), 'workflow', '--help'],
        capture_output=True,
        text=True,
        timeout=30
    )
    
    assert result.returncode == 0
    assert "workflow" in result.stdout.lower()

@pytest.mark.frozen
def test_import_patterns_frozen_mode():
    """Verify no 'from scripts.X' imports in production code"""
    # Scan codebase for forbidden import patterns
    forbidden_patterns = [
        r"from scripts\.\w+ import",
        r"from imagedescriber\.\w+ import",
        r"from analysis\.\w+ import"
    ]
    
    violations = []
    for pattern in forbidden_patterns:
        results = grep_for_pattern(pattern, exclude=['pytest_tests'])
        violations.extend(results)
    
    assert len(violations) == 0, f"Found forbidden imports: {violations}"
```

---

### 8. CI/CD Integration (GitHub Actions)

**Goal**: Automated testing on every push and PR.

#### 8.1 GitHub Actions Workflow
**New File**: `.github/workflows/test.yml`

```yaml
name: Test Suite

on:
  push:
    branches: [ wxpython, main ]
  pull_request:
    branches: [ wxpython, main ]

jobs:
  unit-tests:
    name: Unit Tests
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: ['3.11', '3.12', '3.13']
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-xdist
      
      - name: Run unit tests
        run: |
          pytest pytest_tests/unit -v --cov=scripts --cov=imagedescriber --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          flags: unittests
          name: codecov-${{ matrix.os }}-${{ matrix.python-version }}

  integration-tests:
    name: Integration Tests
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-xdist
      
      - name: Run integration tests
        run: |
          pytest pytest_tests/integration -v -n auto

  smoke-tests:
    name: Smoke Tests
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Run smoke tests
        run: |
          pytest pytest_tests/smoke -v

  build-verification:
    name: Build Executable
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [windows-latest, macos-latest]
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Build idt executable
        run: |
          cd idt
          pip install -r requirements.txt
          pyinstaller idt.spec
      
      - name: Test executable
        run: |
          ./idt/dist/idt version
          ./idt/dist/idt --help
```

**Files Created**: [.github/workflows/test.yml](.github/workflows/test.yml)

#### 8.2 Pre-commit Hooks
**New File**: `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-json
  
  - repo: local
    hooks:
      - id: pytest-unit
        name: Run fast unit tests
        entry: pytest pytest_tests/unit -v -x --maxfail=3
        language: system
        pass_filenames: false
        always_run: true
      
      - id: forbidden-imports
        name: Check for PyInstaller-incompatible imports
        entry: python -c "import sys; import re; forbidden = [r'from scripts\\.\\w+ import', r'from imagedescriber\\.\\w+ import']; violations = []; [violations.extend([(f.name, line) for line in open(f).readlines() if re.search(pat, line)]) for f in [f for f in __import__('pathlib').Path('.').rglob('*.py') if 'pytest_tests' not in str(f)] for pat in forbidden]; sys.exit(1) if violations else sys.exit(0)"
        language: system
        pass_filenames: false
```

**Files Created**: [.pre-commit-config.yaml](.pre-commit-config.yaml)

---

## Implementation Plan: Phased Approach

### Phase 1: Foundation (Week 1-2) - **PRIORITY**

**Goal**: Establish test infrastructure and cover AI providers (highest risk area).

**Tasks**:
1. ✅ Update `pyproject.toml` with pytest-cov configuration
2. ✅ Expand [pytest_tests/conftest.py](pytest_tests/conftest.py) with new fixtures
3. ✅ Create [pytest_tests/fixtures/mock_responses.py](pytest_tests/fixtures/mock_responses.py)
4. ✅ Expand [test_data/](test_data/) with realistic test images/videos
5. ✅ **Create [pytest_tests/unit/test_ai_providers.py](pytest_tests/unit/test_ai_providers.py)** (300+ lines)
   - Test all providers: Ollama, OpenAI, Claude, HuggingFace
   - Test retry logic with exponential backoff
   - Test error handling for API failures
6. ✅ Run coverage analysis: `pytest --cov --cov-report=html`

**Deliverables**:
- Comprehensive AI provider test suite
- Test fixtures for all providers
- Coverage baseline report

**Verification**:
- `pytest pytest_tests/unit/test_ai_providers.py -v` passes
- Coverage report shows >90% for `ai_providers.py`

---

### Phase 2: CLI Tool Coverage (Week 3-4)

**Goal**: Achieve 100% automation of CLI tool testing.

**Tasks**:
1. ✅ Create [pytest_tests/unit/test_idt_cli_commands.py](pytest_tests/unit/test_idt_cli_commands.py)
   - Test all command routing
   - Test argument parsing
2. ✅ Create [pytest_tests/unit/test_workflow_orchestrator.py](pytest_tests/unit/test_workflow_orchestrator.py)
   - Test config resolution
   - Test workflow state parsing
   - Test directory naming
3. ✅ Create analysis tool tests:
   - `test_stats_analysis.py`
   - `test_content_analysis.py`
   - `test_combine_descriptions.py`
4. ✅ Expand integration tests for full workflow scenarios

**Deliverables**:
- 100% CLI command coverage
- Workflow orchestration tested
- Analysis tools tested

**Verification**:
- `pytest pytest_tests/unit -v -m "not gui"` passes
- Coverage for `scripts/` >80%

---

### Phase 3: Data Models & Core Logic (Week 5)

**Goal**: Ensure workspace serialization and core utilities are bulletproof.

**Tasks**:
1. ✅ Create [pytest_tests/unit/test_data_models.py](pytest_tests/unit/test_data_models.py)
   - Test all serialization round-trips
   - Test multi-directory workspaces
   - Test chat session management
2. ✅ Expand existing utility tests:
   - `test_sanitization.py` - More edge cases
   - `test_exif_utils.py` - Date extraction priority
   - `test_window_title_builder.py` - Accessibility patterns

**Deliverables**:
- Data model test suite
- Enhanced utility tests

**Verification**:
- `pytest pytest_tests/unit/test_data_models.py -v` passes
- Coverage for `data_models.py` >95%

---

### Phase 4: GUI Worker Threads (Week 6-7)

**Goal**: Test GUI business logic without rendering.

**Tasks**:
1. ✅ Create [pytest_tests/unit/test_gui_workers.py](pytest_tests/unit/test_gui_workers.py)
   - Test ProcessingWorker with mocked wx.PostEvent
   - Test BatchProcessingWorker orchestration
   - Test VideoProcessingWorker
   - Test HEICConversionWorker
2. ✅ Create [pytest_tests/unit/test_gui_dialogs.py](pytest_tests/unit/test_gui_dialogs.py)
   - Test dialog state management
   - Test configuration dialogs

**Deliverables**:
- GUI worker thread test suite
- Dialog state management tests

**Verification**:
- `pytest pytest_tests/unit -v -m gui` passes
- Coverage for `workers_wx.py` >70%

---

### Phase 5: Integration & E2E Testing (Week 8)

**Goal**: Comprehensive end-to-end scenarios.

**Tasks**:
1. ✅ Expand [pytest_tests/integration/test_workflow_integration.py](pytest_tests/integration/test_workflow_integration.py)
   - Mixed file type workflows
   - Config cascading scenarios
   - EXIF preservation through pipeline
2. ✅ Expand [pytest_tests/integration/test_frozen_executable.py](pytest_tests/integration/test_frozen_executable.py)
   - Build verification tests
   - Import pattern validation
3. ✅ Create realistic E2E scenarios:
   - Directory with 100+ images
   - Multiple AI providers in sequence
   - Resume interrupted workflows

**Deliverables**:
- Comprehensive integration test suite
- E2E smoke tests

**Verification**:
- `pytest pytest_tests/integration -v` passes
- E2E scenarios complete successfully

---

### Phase 6: CI/CD & Automation (Week 9-10)

**Goal**: Automated testing on every commit.

**Tasks**:
1. ✅ Create [.github/workflows/test.yml](.github/workflows/test.yml)
   - Matrix testing: Windows/macOS/Ubuntu × Python 3.11/3.12/3.13
   - Separate jobs: unit/integration/smoke/build
   - Coverage reporting to Codecov
2. ✅ Create [.pre-commit-config.yaml](.pre-commit-config.yaml)
   - Fast unit tests (<30s)
   - Forbidden import pattern checks
   - Code quality checks
3. ✅ Set up branch protection rules:
   - Require tests to pass before merge
   - Require coverage >80%

**Deliverables**:
- GitHub Actions CI pipeline
- Pre-commit hooks installed
- Branch protection enabled

**Verification**:
- Push to branch triggers CI
- Pre-commit prevents bad commits
- Coverage reports to Codecov

---

### Phase 7: Regression Prevention & Monitoring (Ongoing)

**Goal**: Maintain test quality over time.

**Tasks**:
1. ✅ Expand [pytest_tests/regression/test_regression_idt.py](pytest_tests/regression/test_regression_idt.py)
   - Add test for each bug fixed going forward
   - Maintain regression test suite
2. ✅ Monthly coverage review:
   - Identify new untested code
   - Add tests for new features
3. ✅ Performance testing:
   - Track test suite execution time
   - Optimize slow tests
4. ✅ Accessibility testing:
   - Manual WCAG audits quarterly
   - Automated keyboard navigation checks

**Deliverables**:
- Living regression test suite
- Coverage trend monitoring
- Performance benchmarks

**Verification**:
- Coverage never drops below 80%
- Test suite remains <5 min for full run
- Regression tests catch known patterns

---

## Testing Best Practices & Guidelines

### 1. Test Naming Conventions

```python
# Unit tests - test_{component}_{function}_{scenario}_{expected}
def test_workflow_get_effective_model_cli_arg_overrides_config():
    """CLI --model arg should override config default_model"""
    pass

# Integration tests - test_{workflow}_{scenario}
def test_full_workflow_with_mixed_file_types():
    """Workflow handles JPG + HEIC + video in single run"""
    pass

# Regression tests - test_regression_{issue_number}_{bug_summary}
def test_regression_gh74_unique_source_count_undefined():
    """Prevent NameError from incomplete variable rename"""
    pass
```

### 2. Test Organization

```
pytest_tests/
├── unit/               # Fast, isolated, no external dependencies
│   ├── test_ai_providers.py
│   ├── test_data_models.py
│   ├── test_workflow_orchestrator.py
│   └── ...
├── integration/        # Multi-component, mocked externals
│   ├── test_workflow_integration.py
│   ├── test_exif_preservation.py
│   └── ...
├── smoke/             # Quick end-to-end checks
│   └── test_entry_points.py
├── regression/        # Tests for fixed bugs
│   └── test_regression_idt.py
├── fixtures/          # Shared test data
│   └── mock_responses.py
└── conftest.py        # Shared fixtures
```

### 3. Mocking Strategy

**When to Mock**:
- ✅ External APIs (Ollama, OpenAI, Claude)
- ✅ File system for destructive operations
- ✅ System calls (subprocess, ctypes)
- ✅ Time-dependent operations (sleep, datetime.now)
- ✅ wxPython UI events (wx.PostEvent)

**When NOT to Mock**:
- ❌ Pure functions (string manipulation, math)
- ❌ Data models (test real serialization)
- ❌ Config loaders (test real file resolution)

### 4. Coverage Goals

| Component | Target Coverage | Current | Rationale |
|-----------|----------------|---------|-----------|
| **AI Providers** | 95% | 0% | Complex logic, high risk |
| **Data Models** | 95% | 30% | Serialization critical |
| **Workflow Orchestration** | 85% | 50% | Core business logic |
| **CLI Commands** | 90% | 40% | User-facing, high impact |
| **GUI Workers** | 75% | 0% | Threading complexity |
| **Utilities** | 90% | 70% | Widely used |
| **Analysis Tools** | 80% | 20% | Lower risk, fewer dependencies |

**Overall Target**: 80% line coverage, 70% branch coverage

### 5. Test Execution Strategy

**Local Development**:
```bash
# Fast feedback loop (<30s)
pytest pytest_tests/unit -v -x --ff

# Pre-commit (~2-3 min)
pytest pytest_tests/unit pytest_tests/smoke -v

# Full suite before PR (~5-10 min)
pytest -v --cov --cov-report=html
```

**CI/CD**:
```bash
# Every push: unit + smoke (~5 min)
pytest pytest_tests/unit pytest_tests/smoke -v -n auto

# Nightly: full suite + frozen builds (~30 min)
pytest -v --cov --cov-report=xml
```

---

## Success Criteria

### Phase 1-3 (Weeks 1-5): Foundation & CLI
- ✅ AI provider test suite with >90% coverage
- ✅ CLI command routing 100% tested
- ✅ Data model serialization 95% coverage
- ✅ Test suite runs in <3 minutes
- ✅ Coverage baseline report published

### Phase 4-5 (Weeks 6-8): GUI & Integration
- ✅ GUI worker threads 75% covered
- ✅ Integration tests for all workflow scenarios
- ✅ E2E smoke tests for critical paths
- ✅ Frozen executable build verification

### Phase 6-7 (Weeks 9-10+): Automation & Maintenance
- ✅ GitHub Actions CI runs on all PRs
- ✅ Pre-commit hooks prevent regressions
- ✅ Branch protection requires passing tests
- ✅ Coverage tracked in Codecov
- ✅ Regression test suite catches known patterns

### Final State (End of Phase 7)
- 🎯 **80% overall code coverage** (line coverage)
- 🎯 **<5 min full test suite** execution time
- 🎯 **100% regression protection** - all historical bugs have tests
- 🎯 **Automated CI/CD** - tests run on every commit
- 🎯 **Pre-commit safety net** - catches issues before push
- 🎯 **Documentation** - all tests have clear docstrings
- 🎯 **Maintainable** - new features include tests

---

## Risks & Mitigations

### Risk 1: Test Suite Too Slow
**Impact**: Developers skip running tests locally.

**Mitigation**:
- Use pytest markers to run fast subset (`-m "not slow"`)
- Parallelize with `pytest-xdist` (`-n auto`)
- Mock expensive operations (API calls, file I/O)
- Move slow tests to nightly CI builds

### Risk 2: Flaky Tests
**Impact**: CI failures unrelated to code changes.

**Mitigation**:
- Use deterministic test data (no random generation)
- Mock time-dependent operations
- Use `tmp_path` fixtures for filesystem isolation
- Retry flaky tests 3 times before failing

### Risk 3: Test Maintenance Burden
**Impact**: Tests become outdated as code evolves.

**Mitigation**:
- Enforce "test with PR" policy
- Use coverage reports to identify untested new code
- Regular test review in monthly dev meetings
- Refactor tests alongside production code

### Risk 4: wxPython GUI Testing Complexity
**Impact**: GUI tests are fragile and slow.

**Mitigation**:
- Focus on **business logic** testing (workers, state management)
- **Avoid** testing visual appearance (manual only)
- Use dependency injection to test dialog logic without rendering
- Accept ~75% coverage for GUI (not 100%)

### Risk 5: Mock Drift from Real APIs
**Impact**: Tests pass but production fails.

**Mitigation**:
- Periodic "integration week" with real API calls (on test accounts)
- Document mock assumptions in comments
- Update mocks when API versions change
- End-to-end tests validate critical paths with real dependencies

---

## Documentation Requirements

### Test Documentation
**Location**: Each test file should have module-level docstring:

```python
"""
Unit tests for AI provider logic in ai_providers.py.

Covers:
- OllamaProvider API calls with retry logic
- OpenAIProvider token tracking
- ClaudeProvider error handling
- Provider availability detection

Mocking Strategy:
- requests.post for Ollama HTTP calls
- openai.OpenAI for OpenAI SDK
- anthropic.Anthropic for Claude SDK

Run with:
    pytest pytest_tests/unit/test_ai_providers.py -v
"""
```

### Coverage Reports
**Location**: `htmlcov/index.html` (generated by pytest-cov)

**Publish**: Upload to Codecov on every CI run.

### Test Metrics Dashboard
**Tools**: Codecov dashboard + GitHub Actions badges

**Metrics to Track**:
- Overall coverage percentage
- Coverage trend over time
- Test execution time
- Flaky test rate
- Pass/fail rate by environment

---

## Toolchain & Dependencies

### Required Packages (Add to requirements.txt)
```
pytest>=8.0.0
pytest-cov>=4.1.0
pytest-xdist>=3.5.0  # Parallel test execution
pytest-mock>=3.12.0  # Enhanced mocking
pytest-timeout>=2.2.0  # Timeout protection
```

### Optional Packages (Development)
```
coverage[toml]>=7.4.0
codecov>=2.1.13
pre-commit>=3.6.0
```

### CI/CD Tools
- **GitHub Actions** - Primary CI platform
- **Codecov** - Coverage reporting and trend tracking
- **pre-commit** - Local commit hooks

---

## Timeline Summary

| Phase | Duration | Focus | Deliverables |
|-------|----------|-------|--------------|
| **Phase 1** | 2 weeks | AI Providers | Provider test suite, fixtures, coverage baseline |
| **Phase 2** | 2 weeks | CLI Tool | Command routing, workflow orchestration, analysis tools |
| **Phase 3** | 1 week | Data Models | Serialization tests, workspace operations |
| **Phase 4** | 2 weeks | GUI Workers | Worker thread tests, dialog state management |
| **Phase 5** | 1 week | Integration | E2E scenarios, frozen build verification |
| **Phase 6** | 2 weeks | CI/CD | GitHub Actions, pre-commit hooks, branch protection |
| **Phase 7** | Ongoing | Maintenance | Regression prevention, coverage monitoring |

**Total Initial Implementation**: 10 weeks  
**Ongoing Maintenance**: Continuous

---

## References

- **Existing Test Infrastructure**: [pytest_tests/](pytest_tests/)
- **Regression Audit**: [docs/WorkTracking/2026-01-20-MIGRATION-AUDIT.md](docs/WorkTracking/2026-01-20-MIGRATION-AUDIT.md)
- **Review Protocol**: [docs/WorkTracking/AI_COMPREHENSIVE_REVIEW_PROTOCOL.md](docs/WorkTracking/AI_COMPREHENSIVE_REVIEW_PROTOCOL.md)
- **pytest Documentation**: https://docs.pytest.org/
- **pytest-cov**: https://pytest-cov.readthedocs.io/
- **Codecov**: https://docs.codecov.com/

---

**Last Updated**: February 10, 2026  
**Tracking Issue**: [GitHub Issue #76](https://github.com/kellylford/Image-Description-Toolkit/issues/76)  
**Implementation Branch**: `wxpython`
