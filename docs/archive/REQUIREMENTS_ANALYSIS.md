# Requirements Files Analysis

## Executive Summary

After analyzing the codebase, I recommend **consolidating to a single `requirements.txt` file** with optional dependencies clearly marked. The current two-file system creates confusion without meaningful benefit.

**Key Finding:** The `openai` and `anthropic` packages listed in requirements are **NOT actually used by the code**. The AI providers use direct HTTP requests via the `requests` library instead.

---

## Current State

### requirements.txt (16 dependencies)
```
ollama>=0.3.0
PyQt6>=6.4.0
Pillow>=10.0.0
pillow-heif>=0.13.0
opencv-python>=4.8.0
numpy>=1.24.0
pyexiv2>=2.15.0
ExifRead>=3.0.0
requests>=2.25.0
geopy>=2.4.0
openai>=1.0.0           # NOT ACTUALLY USED
anthropic>=0.18.0       # NOT ACTUALLY USED
pywin32>=306; sys_platform == "win32"
tqdm>=4.60.0
pytest>=6.0.0
pytest-mock>=3.6.0
```

### requirements-python313.txt (10 dependencies)
```
ollama>=0.3.0
PyQt6>=6.4.0
Pillow>=10.0.0
opencv-python>=4.8.0
numpy>=1.24.0
requests>=2.25.0
openai>=1.0.0           # NOT ACTUALLY USED
anthropic>=0.18.0       # NOT ACTUALLY USED
pywin32>=306; sys_platform == "win32"
tqdm>=4.60.0

# Missing: pillow-heif, pyexiv2, ExifRead, geopy, pytest, pytest-mock
```

---

## Dependency Usage by Component

### Core Script Dependencies (REQUIRED for all workflows)
- **Pillow** - Image processing (all components)
- **requests** - HTTP requests for AI providers (Ollama, OpenAI, Claude)
- **ollama** - Ollama Python client library

### GUI-Specific Dependencies
- **PyQt6** - GUI framework
  - Used by: `imagedescriber/imagedescriber.py`, `viewer/viewer.py`, `prompt_editor/prompt_editor.py`
- **pywin32** (Windows only) - System integration

### Video Processing (scripts/video_frame_extractor.py only)
- **opencv-python** - Video frame extraction
- **numpy** - Array operations for video processing

### HEIC Image Support (scripts/ConvertImage.py only)
- **pillow-heif** - HEIC/HEIF image format support
  - Used by: `scripts/ConvertImage.py`, `MetaData/raw_exif_parser.py`

### Metadata Extraction (MetaData/ directory only)
- **pyexiv2** - Advanced EXIF metadata extraction (NOT USED in core workflows)
- **ExifRead** - Fallback EXIF reader (NOT USED in core workflows)
- **geopy** - GPS coordinate reverse geocoding (NOT USED in core workflows)
  - Only used in: `MetaData/improved_gps_location_extractor.py`

### Development/Testing
- **pytest** - Unit testing framework
- **pytest-mock** - Mocking for tests
- **tqdm** - Progress bars (nice-to-have)

### UNUSED Dependencies (Should Remove)
- **openai>=1.0.0** - NOT imported anywhere
- **anthropic>=0.18.0** - NOT imported anywhere

**Why they're listed:** Likely added initially thinking official SDKs would be used, but the code uses direct HTTP requests via `requests` library instead.

**Evidence:**
```python
# imagedescriber/ai_providers.py - OpenAI implementation
headers = {
    "Authorization": f"Bearer {self.api_key}",
    "Content-Type": "application/json"
}
response = requests.post(
    f"{self.base_url}/chat/completions",
    headers=headers,
    json=payload,
    timeout=300
)
```

Same pattern for Claude - direct HTTP requests, no SDK.

---

## Component Breakdown

### imagedescriber/ (GUI)
**Required:**
- PyQt6, Pillow, requests, ollama, pywin32 (Windows)

**Optional:**
- None (self-contained GUI)

### viewer/ (GUI)
**Required:**
- PyQt6, Pillow

**Optional:**
- None (simple viewer)

### prompt_editor/ (GUI)
**Required:**
- PyQt6

**Optional:**
- None (text editor)

### scripts/ (Command-line tools)
**Core scripts (workflow.py, image_describer.py, descriptions_to_html.py):**
- Pillow, requests, ollama

**ConvertImage.py:**
- Pillow, **pillow-heif**

**video_frame_extractor.py:**
- **opencv-python**, **numpy**, Pillow

### MetaData/ (Separate utilities)
**Not part of main workflow**
- pyexiv2, ExifRead, geopy, pillow-heif
- These are standalone metadata extraction tools

---

## Python 3.13 Compatibility

### Compatible Dependencies
✅ All core dependencies work with Python 3.13:
- ollama, PyQt6, Pillow, opencv-python, numpy, requests, pywin32, tqdm

### Potentially Incompatible
⚠️ **pillow-heif** - Check PyPI for Python 3.13 wheels (as of 2025, likely available)
⚠️ **pyexiv2** - May require C++ compilation (note in requirements-python313.txt)

### Impact Assessment
- **If pillow-heif unavailable:** HEIC conversion won't work, but workflow can continue (JPEG/PNG still supported)
- **If pyexiv2 unavailable:** No impact on core workflow (only affects MetaData utilities)

---

## Recommendations

### Option 1: Single Consolidated File (RECOMMENDED)

Create one `requirements.txt` with clear sections:

```txt
# Image Description Toolkit - Dependencies
# ===========================================

# Core Dependencies (REQUIRED for all usage)
Pillow>=10.0.0
requests>=2.25.0
ollama>=0.3.0

# GUI Applications (imagedescriber, viewer, prompt_editor)
PyQt6>=6.4.0
pywin32>=306; sys_platform == "win32"  # Windows GUI integration

# Video Processing (scripts/video_frame_extractor.py)
opencv-python>=4.8.0  # Only needed for video frame extraction
numpy>=1.24.0         # Required by opencv-python

# HEIC Image Support (scripts/ConvertImage.py)
pillow-heif>=0.13.0  # Only needed for HEIC/HEIF image conversion

# Development/Testing
tqdm>=4.60.0          # Progress bars (optional)
pytest>=6.0.0         # Testing framework
pytest-mock>=3.6.0    # Test mocking

# Metadata Utilities (MetaData/ directory - not required for core workflow)
# pyexiv2>=2.15.0     # Advanced EXIF extraction (may require compilation)
# ExifRead>=3.0.0     # Alternative EXIF reader
# geopy>=2.4.0        # GPS reverse geocoding
```

**Installation commands:**
```bash
# Minimal (scripts only, no HEIC, no video)
pip install Pillow requests ollama

# GUI applications
pip install Pillow requests ollama PyQt6 pywin32

# Full installation (all features)
pip install -r requirements.txt

# Metadata utilities (optional)
pip install pyexiv2 ExifRead geopy
```

### Option 2: Component-Specific Files

```
requirements-core.txt          # Pillow, requests, ollama
requirements-gui.txt           # PyQt6, pywin32
requirements-video.txt         # opencv-python, numpy
requirements-heic.txt          # pillow-heif
requirements-metadata.txt      # pyexiv2, ExifRead, geopy
requirements-dev.txt           # pytest, pytest-mock, tqdm
```

**Pros:** Very granular control
**Cons:** Complex installation process, harder to maintain

### Option 3: Keep Two Files (NOT RECOMMENDED)

**Problem:** Current split doesn't align with actual Python 3.13 compatibility issues. Both files include unused dependencies (`openai`, `anthropic`).

---

## Action Items

### Immediate Changes

1. **Remove unused dependencies** from both files:
   - ❌ `openai>=1.0.0` (not imported anywhere)
   - ❌ `anthropic>=0.18.0` (not imported anywhere)

2. **Consolidate to single `requirements.txt`** (Option 1 above)

3. **Delete `requirements-python313.txt`** (no longer needed with cleaner organization)

4. **Update documentation:**
   - README.md installation section
   - Add "Minimal Installation" instructions
   - Add "Full Installation" instructions
   - Document optional features (HEIC, video, metadata)

### Future Enhancements

5. **Create `pyproject.toml`** for proper package structure:
   ```toml
   [project]
   name = "image-description-toolkit"
   dependencies = [
       "Pillow>=10.0.0",
       "requests>=2.25.0",
       "ollama>=0.3.0",
   ]
   
   [project.optional-dependencies]
   gui = ["PyQt6>=6.4.0", "pywin32>=306; sys_platform == 'win32'"]
   video = ["opencv-python>=4.8.0", "numpy>=1.24.0"]
   heic = ["pillow-heif>=0.13.0"]
   metadata = ["pyexiv2>=2.15.0", "ExifRead>=3.0.0", "geopy>=2.4.0"]
   dev = ["pytest>=6.0.0", "pytest-mock>=3.6.0", "tqdm>=4.60.0"]
   ```

   Then users can install with:
   ```bash
   pip install -e .               # Core only
   pip install -e ".[gui]"        # With GUI
   pip install -e ".[gui,video]"  # GUI + video processing
   pip install -e ".[all]"        # Everything
   ```

6. **Component-specific requirements** (if needed):
   - Create `imagedescriber/requirements.txt` if it becomes a standalone package
   - Create `viewer/requirements.txt` if viewer becomes standalone
   - For now, single root file is sufficient

---

## Migration Guide

### For Current Users

```bash
# 1. Remove old virtual environment
deactivate  # if active
rm -rf .venv

# 2. Create new virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# 3. Install from new requirements.txt
pip install -r requirements.txt

# 4. Verify installation
python -c "import PyQt6, PIL, ollama, requests; print('✓ Core dependencies OK')"
```

### For Script-Only Users (No GUI)

```bash
# Minimal installation
pip install Pillow requests ollama

# Add HEIC support if needed
pip install pillow-heif

# Add video support if needed
pip install opencv-python numpy
```

---

## Summary

**Do we need two requirements files?**
❌ No. The Python 3.13 file is redundant and incorrectly organized.

**Do they represent what's needed for scripts?**
❌ No. They include unused dependencies (`openai`, `anthropic`) and don't clearly separate optional components.

**Should components have their own requirements?**
⚠️ Not yet. Current components aren't distributed separately. Single root file with clear sections is sufficient.

**Recommended action:**
1. Consolidate to single `requirements.txt` with clear sections
2. Remove unused `openai` and `anthropic` packages
3. Mark optional dependencies clearly (video, HEIC, metadata, dev)
4. Update README with installation options
5. Delete `requirements-python313.txt`

This gives users flexibility (minimal vs full install) without the complexity of managing multiple files.
