# Test Structure Reorganization Plan

**Date**: November 1, 2025  
**Goal**: Reorganize existing tests and add missing critical tests

## Current State Assessment

### Existing Tests Inventory

**Unit Tests** (`pytest_tests/unit/` - 8 files):
- ✅ `test_configuration_system.py` - Config loading
- ✅ `test_guided_workflow.py` - Guided workflow logic  
- ✅ `test_metadata_safety.py` - Metadata handling
- ✅ `test_sanitization.py` - Name sanitization
- ✅ `test_status_log.py` - Status logging
- ✅ `test_versioning.py` - Version info
- ✅ `test_web_image_downloader.py` - Web downloads
- ✅ `test_workflow_config.py` - Workflow configuration

**Smoke Tests** (`pytest_tests/smoke/` - 1 file):
- ✅ `test_entry_points.py` - Entry point accessibility

**Integration Tests** (`pytest_tests/integration/` - 4 files):
- ✅ `test_exif_preservation.py` - EXIF through pipeline
- ✅ `test_frozen_executable.py` - Frozen exe functionality
- ✅ `test_guideme_integration.py` - Guideme workflow
- ✅ `test_workflow_integration.py` - Complete workflow

### What's Missing

#### Critical Gaps
1. ❌ **No E2E test that builds + runs workflow** (user's #1 need)
2. ❌ **No AI provider interface tests** (can't test without API)
3. ❌ **No HTML generation tests** (output quality)
4. ❌ **No video extraction tests** (frame extraction logic)
5. ❌ **No image optimization tests** (size reduction)

#### Coverage Gaps
6. ❌ Path identifier generation (`get_path_identifier_2_components`)
7. ❌ Prompt validation and templating
8. ❌ Model registry lookups
9. ❌ Workflow metadata save/load
10. ❌ File discovery logic

---

## Proposed New Structure

```
pytest_tests/
├── conftest.py                      # Shared fixtures
├── test_helpers.py                  # Test utilities (NEW)
│
├── unit/                            # Fast, isolated tests (< 100ms)
│   ├── test_configuration_system.py          ✅ Keep
│   ├── test_sanitization.py                  ✅ Keep
│   ├── test_versioning.py                    ✅ Keep
│   ├── test_workflow_config.py               ✅ Keep
│   ├── test_metadata_safety.py               ✅ Keep
│   ├── test_status_log.py                    ✅ Keep
│   ├── test_path_generation.py               🆕 NEW - Path naming
│   ├── test_prompt_validation.py             🆕 NEW - Prompt handling
│   ├── test_model_registry.py                🆕 NEW - Model lookups
│   ├── test_validation_functions.py          🆕 NEW - Input validation
│   └── test_workflow_metadata.py             🆕 NEW - Metadata I/O
│
├── integration/                     # Component interaction (1-10s)
│   ├── test_exif_preservation.py             ✅ Keep (good test!)
│   ├── test_workflow_integration.py          ⚠️  Update (use mock provider)
│   ├── test_image_optimization.py            🆕 NEW - Size reduction
│   ├── test_video_extraction.py              🆕 NEW - Frame extraction
│   ├── test_html_generation.py               🆕 NEW - Report creation
│   ├── test_description_pipeline.py          🆕 NEW - End-to-end describe
│   ├── test_config_resolution.py             🆕 NEW - Multi-source config
│   └── test_workflow_orchestrator.py         🆕 NEW (after refactor)
│
├── e2e/                             # Full frozen exe tests (30-120s)
│   ├── test_frozen_executable.py             ⚠️  Move from integration/
│   ├── test_build_and_workflow.py            🆕 NEW - User's #1 priority
│   ├── test_cli_commands.py                  🆕 NEW - All CLI commands
│   ├── test_multi_provider_workflows.py      🆕 NEW - Provider switching
│   └── test_viewer_integration.py            🆕 NEW - Viewer can parse
│
└── smoke/                           # Quick sanity checks (< 5s)
    ├── test_entry_points.py                  ✅ Keep
    ├── test_executables_launch.py            🆕 NEW - All 5 apps launch
    └── test_help_commands.py                 🆕 NEW - All --help work
```

---

## New Test File Specifications

### 1. `pytest_tests/e2e/test_build_and_workflow.py` (User's #1 Priority)

```python
"""
End-to-end test that builds the frozen executable and runs a complete workflow.

This is the user's #1 testing priority - automated verification that:
1. The project builds successfully
2. The frozen executable runs a workflow
3. The workflow generates expected results

This test takes 1-3 minutes to run and should be part of the release process.
"""

import pytest
import subprocess
import shutil
from pathlib import Path


@pytest.fixture(scope="module")
def built_executable(tmp_path_factory):
    """Build idt.exe once for all tests in this module"""
    project_root = Path(__file__).parent.parent.parent
    exe_path = project_root / "dist" / "idt.exe"
    
    # Only build if not already built or if code changed
    if not exe_path.exists():
        print("\n[Building idt.exe - this takes 1-2 minutes...]")
        result = subprocess.run(
            ["BuildAndRelease\\build_idt.bat"],
            cwd=project_root,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            pytest.fail(f"Build failed:\n{result.stderr}")
    
    assert exe_path.exists(), "Build succeeded but executable not found"
    return exe_path


@pytest.fixture
def test_images_dir():
    """Path to test images"""
    return Path(__file__).parent.parent.parent / "test_data"


@pytest.mark.e2e
@pytest.mark.slow
def test_frozen_exe_runs_complete_workflow(built_executable, test_images_dir, tmp_path):
    """
    CRITICAL TEST: Verify frozen executable can run a complete workflow
    
    This is the primary automated verification that the build is functional.
    """
    output_dir = tmp_path / "workflow_output"
    
    # Run workflow with frozen executable
    result = subprocess.run(
        [
            str(built_executable),
            "workflow",
            str(test_images_dir),
            "--output", str(output_dir),
            "--model", "moondream",  # Fast local model
            "--prompt-style", "concise",
            "--steps", "describe,html",
            "--no-view"
        ],
        capture_output=True,
        text=True,
        timeout=300  # 5 minute timeout
    )
    
    # Verify successful execution
    assert result.returncode == 0, f"Workflow failed:\n{result.stderr}"
    
    # Verify workflow directory created
    workflow_dirs = list(output_dir.glob("wf_*"))
    assert len(workflow_dirs) == 1, f"Expected 1 workflow dir, found {len(workflow_dirs)}"
    
    workflow_dir = workflow_dirs[0]
    
    # Verify descriptions generated
    descriptions_dir = workflow_dir / "descriptions"
    assert descriptions_dir.exists(), "Descriptions directory not created"
    
    description_files = list(descriptions_dir.glob("*.txt"))
    assert len(description_files) > 0, "No description files generated"
    
    # Verify HTML report generated
    html_report = workflow_dir / "html_reports" / "index.html"
    assert html_report.exists(), "HTML report not generated"
    
    # Verify HTML content
    html_content = html_report.read_text()
    assert "Image Description Report" in html_content, "HTML missing expected title"
    
    # Verify at least one description appears in HTML
    first_description = description_files[0].read_text()
    # HTML should contain some part of the description (accounting for truncation)
    description_snippet = first_description[:50]
    # Note: HTML may transform the text, so we check for any overlap
    assert any(word in html_content for word in description_snippet.split()), \
        "Description content not found in HTML"
    
    print(f"\n✓ Workflow generated {len(description_files)} descriptions")
    print(f"✓ Output: {workflow_dir}")


@pytest.mark.e2e  
@pytest.mark.slow
def test_frozen_exe_handles_no_images_gracefully(built_executable, tmp_path):
    """Verify workflow handles empty directory without crashing"""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    output_dir = tmp_path / "output"
    
    result = subprocess.run(
        [
            str(built_executable),
            "workflow",
            str(empty_dir),
            "--output", str(output_dir),
            "--model", "moondream",
            "--no-view"
        ],
        capture_output=True,
        text=True,
        timeout=30
    )
    
    # Should handle gracefully (may exit with error code, but shouldn't crash)
    assert "No images found" in result.stdout or "No images found" in result.stderr, \
        "Should report no images found"
```

### 2. `pytest_tests/integration/test_html_generation.py`

```python
"""Test HTML report generation from descriptions"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from descriptions_to_html import generate_html_report, parse_description_file


@pytest.fixture
def sample_descriptions(tmp_path):
    """Create sample description files"""
    desc_dir = tmp_path / "descriptions"
    desc_dir.mkdir()
    
    # Create sample description
    desc_file = desc_dir / "image1.txt"
    desc_file.write_text("""
File: image1.jpg
Date: 2024-10-29 08:30:00
Camera: iPhone 15 Pro
Location: Madison, Wisconsin

Description:
A beautiful landscape showing trees and sky.
""")
    
    return desc_dir


@pytest.mark.integration
def test_generate_html_from_descriptions(sample_descriptions, tmp_path):
    """Test HTML generation creates valid output"""
    output_dir = tmp_path / "html"
    
    generate_html_report(
        descriptions_dir=sample_descriptions,
        output_dir=output_dir
    )
    
    # Verify HTML file created
    html_file = output_dir / "index.html"
    assert html_file.exists()
    
    # Verify content
    html = html_file.read_text()
    assert "<html" in html.lower()
    assert "image1.jpg" in html
    assert "beautiful landscape" in html


@pytest.mark.unit
def test_parse_description_file():
    """Test description file parsing"""
    content = """
File: test.jpg
Date: 2024-10-29
Camera: Test Camera

Description:
Test description content
"""
    
    result = parse_description_file(content)
    
    assert result['file'] == "test.jpg"
    assert "Test description" in result['description']
```

### 3. `pytest_tests/unit/test_path_generation.py`

```python
"""Test workflow path and directory naming"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from workflow import sanitize_name, get_path_identifier_2_components


class TestSanitizeName:
    """Test filesystem-safe name generation"""
    
    def test_sanitize_removes_special_chars(self):
        assert sanitize_name("GPT-4 Vision!") == "GPT-4Vision"
        assert sanitize_name("model:tag@version") == "modeltagversion"
    
    def test_sanitize_preserves_valid_chars(self):
        assert sanitize_name("model_name-v2.1") == "model_name-v2.1"
    
    def test_sanitize_handles_empty_string(self):
        assert sanitize_name("") == "unknown"
        assert sanitize_name(None) == "unknown"
    
    def test_sanitize_case_preservation(self):
        assert sanitize_name("GPT4", preserve_case=True) == "GPT4"
        assert sanitize_name("GPT4", preserve_case=False) == "gpt4"


class TestPathIdentifier:
    """Test workflow directory naming"""
    
    def test_path_identifier_format(self):
        """Test that path identifier has correct format"""
        model = "llava_7b"
        prompt = "narrative"
        
        identifier = get_path_identifier_2_components(model, prompt)
        
        # Should be model_prompt format
        assert "_" in identifier
        parts = identifier.split("_")
        assert len(parts) >= 2
        assert model.replace(":", "").replace("-", "") in identifier
        assert prompt in identifier
    
    def test_path_identifier_sanitizes_inputs(self):
        """Test that special characters are handled"""
        identifier = get_path_identifier_2_components(
            "model:with:colons",
            "prompt-with-dashes"
        )
        
        assert ":" not in identifier
        assert identifier.replace("_", "").replace("-", "").isalnum()
```

### 4. `pytest_tests/integration/test_video_extraction.py`

```python
"""Test video frame extraction pipeline"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from video_frame_extractor import VideoFrameExtractor


@pytest.fixture
def sample_video(tmp_path):
    """Create or reference a sample video file"""
    # Use existing test video if available
    test_video = Path(__file__).parent.parent.parent / "test_data" / "IMG_3136.MOV"
    if test_video.exists():
        return test_video
    
    # Otherwise skip this test
    pytest.skip("Test video not available")


@pytest.mark.integration
@pytest.mark.slow
def test_video_frame_extraction(sample_video, tmp_path):
    """Test extracting frames from video"""
    output_dir = tmp_path / "frames"
    output_dir.mkdir()
    
    extractor = VideoFrameExtractor(
        output_directory=output_dir,
        fps=1  # Extract 1 frame per second for speed
    )
    
    frames = extractor.extract_frames(sample_video)
    
    # Should extract at least one frame
    assert len(frames) > 0
    
    # Frames should exist
    for frame_path in frames:
        assert frame_path.exists()
        assert frame_path.suffix.lower() == '.jpg'


@pytest.mark.integration
def test_video_extraction_with_exif_embedding(sample_video, tmp_path):
    """Test that extracted frames get EXIF data embedded"""
    output_dir = tmp_path / "frames"
    output_dir.mkdir()
    
    extractor = VideoFrameExtractor(
        output_directory=output_dir,
        fps=1,
        embed_video_metadata=True
    )
    
    frames = extractor.extract_frames(sample_video)
    
    # Check that EXIF data was embedded
    from PIL import Image
    import piexif
    
    if frames:
        img = Image.open(frames[0])
        exif_dict = piexif.load(img.info.get('exif', b''))
        
        # Should have some EXIF data
        assert len(exif_dict) > 0
```

---

## Migration Steps

### Week 1: Foundation
1. ✅ Create `test_and_build.bat` (DONE)
2. 🆕 Create `pytest_tests/e2e/test_build_and_workflow.py`
3. 🆕 Create `pytest_tests/test_helpers.py` with shared utilities
4. ⚠️ Move `test_frozen_executable.py` to `e2e/` directory

### Week 2: Unit Test Coverage
1. 🆕 Create `test_path_generation.py`
2. 🆕 Create `test_prompt_validation.py`
3. 🆕 Create `test_model_registry.py`
4. 🆕 Create `test_workflow_metadata.py`
5. ⚠️ Run coverage report, identify remaining gaps

### Week 3: Integration Tests
1. 🆕 Create `test_html_generation.py`
2. 🆕 Create `test_video_extraction.py`
3. 🆕 Create `test_image_optimization.py`
4. ⚠️ Update `test_workflow_integration.py` to use mock provider

### Week 4: E2E and Smoke Tests
1. 🆕 Create `test_cli_commands.py`
2. 🆕 Create `test_executables_launch.py`
3. 🆕 Create `test_help_commands.py`
4. ⚠️ Set up CI pipeline

---

## Test Fixtures Library

Create `pytest_tests/test_helpers.py` with reusable fixtures:

```python
"""Shared test fixtures and utilities"""

import pytest
from pathlib import Path
from PIL import Image
import piexif


@pytest.fixture
def test_image_with_exif(tmp_path):
    """Create a test image with realistic EXIF data"""
    image_path = tmp_path / "test_image.jpg"
    
    exif_dict = {
        "0th": {
            piexif.ImageIFD.Make: b"Apple",
            piexif.ImageIFD.Model: b"iPhone 15 Pro",
            piexif.ImageIFD.DateTime: b"2024:10:29 08:30:00",
        },
        "Exif": {
            piexif.ExifIFD.DateTimeOriginal: b"2024:10:29 08:30:00",
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
def mock_ai_provider():
    """Mock AI provider for testing without API calls"""
    class MockProvider:
        def __init__(self):
            self.calls = []
        
        def describe_image(self, image_path, prompt):
            self.calls.append({'image': image_path, 'prompt': prompt})
            return "A test description of the image."
        
        def is_available(self):
            return True
    
    return MockProvider()


@pytest.fixture
def sample_workflow_directory(tmp_path, test_image_with_exif):
    """Create a complete workflow directory structure"""
    workflow_dir = tmp_path / "wf_test_model_narrative_20241029_083000"
    workflow_dir.mkdir()
    
    # Create subdirectories
    (workflow_dir / "converted_images").mkdir()
    (workflow_dir / "descriptions").mkdir()
    (workflow_dir / "html_reports").mkdir()
    (workflow_dir / "logs").mkdir()
    
    # Add sample image
    import shutil
    shutil.copy(test_image_with_exif, workflow_dir / "converted_images" / "image1.jpg")
    
    # Add sample description
    desc_file = workflow_dir / "descriptions" / "image1.txt"
    desc_file.write_text("""
File: image1.jpg
Date: 2024-10-29 08:30:00
Camera: iPhone 15 Pro

Description:
A test description.
""")
    
    return workflow_dir
```

---

## Test Execution Commands

### Run All Tests (CI/CD)
```bash
pytest pytest_tests/ -v --cov=scripts --cov-report=html
```

### Run Only Fast Tests (Development)
```bash
pytest pytest_tests/ -m "not slow" -v
```

### Run Only Unit Tests
```bash
pytest pytest_tests/unit/ -v
```

### Run Integration Tests
```bash
pytest pytest_tests/integration/ -v
```

### Run E2E Tests (Before Release)
```bash
pytest pytest_tests/e2e/ -v
```

### Run Specific Test
```bash
pytest pytest_tests/e2e/test_build_and_workflow.py::test_frozen_exe_runs_complete_workflow -v
```

---

## Success Criteria

### Phase 1 Complete When:
- ✅ `test_and_build.bat` runs successfully
- ✅ `test_build_and_workflow.py` passes
- ✅ No manual testing required to verify build

### Full Migration Complete When:
- ✅ 80%+ code coverage on `scripts/`
- ✅ All critical paths have tests
- ✅ CI runs all tests on every PR
- ✅ Flaky tests eliminated
- ✅ Test suite runs in < 5 minutes

---

**Last Updated**: November 1, 2025  
**Status**: Plan created, implementation starting
