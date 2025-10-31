# GitHub Copilot Instructions for Image-Description-Toolkit

**Agent Acknowledgment**: At the start of each response, identify yourself using your actual model name and confirm you understand and will follow these instructions.

Follow these guidelines for all coding work on this project.

## Code Quality Standards

1. **Professional Quality:** Code should be professional quality and tested before calling something complete and ready for submission.

2. **Planning and Tracking:** Planning and tracking documents should go in the `docs/worktracking/` directory and kept current as work is completed.

3. **Session Summaries:** Create and maintain a session summary document in `docs/worktracking/` with format `YYYY-MM-DD-session-summary.md`. Update it throughout the session with:
   - Changes made (files modified, features added)
   - Technical decisions and rationale
   - Testing results
   - User-friendly summaries of what was accomplished
   - Keep it updated until explicitly told to stop

4. **Accessibility:** All coding should be WCAG 2.2 AA conformant. This should be a given for this project, so being accessible doesn't need to be highlighted in documentation unless it is something especially unique.

5. **Dual Support:** Work needs to keep in mind that we want to keep support for both the script-based approach for image descriptions and the GUI ImageDescriber app.

6. **No Shortcuts:** Avoid the typical behavior of AI of taking shortcuts, not scanning files completely, and more. This has already resulted in duplicate code at times and extensive time debugging. The project has become too large for constant testing.

7. **Repository Hygiene:** Keep the repository clean and organized. Remove unused files, fix broken links, and ensure that documentation is up to date.

8. **Finished includes tested now and forever:** Ensure that all code is thoroughly tested before considering it finished. This includes unit tests, integration tests, and any other relevant testing methodologies completed along with the change.

9. **Test Before Claiming Complete:** Before stating that code is fixed or a feature is implemented:
   - Actually BUILD the executable if changes affect compiled code
   - RUN the code with realistic test scenarios (not just theoretical analysis)
   - VERIFY the fix works end-to-end, not just that syntax is correct
   - Do NOT ask the user to test - YOU test first, then report results
   - If you cannot test (missing environment/data), explicitly state what you CAN'T verify
   
   **Example from config system debugging:** Agent made 7 fixes across multiple files but kept saying "it should work now" without testing. Each fix broke something new because related code wasn't checked. The correct approach: After each fix, rebuild idt.exe, run with test data, verify the actual error is gone, check for NEW errors, repeat until genuinely working.

10. **Comprehensive Impact Analysis:** When making changes:
    - Search for ALL usages of the function/variable/pattern being changed
    - Check for duplicate implementations that need the same fix
    - Look for related code that depends on the changed behavior
    - Verify argument parsers don't have conflicting flags (e.g., two `-c` arguments)
    - Check if frozen executable vs dev mode have different code paths
    - Assume there ARE related bugs you haven't found yet - actively hunt for them



## Architecture Overview

### Multi-Application Structure
IDT consists of five standalone applications, each with isolated dependencies:
- **`idt.exe`** - CLI dispatcher (routes to all commands via `idt_cli.py`)
- **`viewer.exe`** - PyQt6 workflow results browser with live monitoring
- **`imagedescriber.exe`** - PyQt6 batch processing GUI (10k+ lines)
- **`prompteditor.exe`** - Visual prompt template editor
- **`idtconfigure.exe`** - Configuration management interface

Each GUI application has its own `.venv` and build scripts in its directory.

### Dual Execution Model
All code must support both development and production modes:
- **Development**: Run as Python scripts (`python scripts/workflow.py`)
- **Production**: Run as PyInstaller frozen executables (`idt.exe workflow`)
- **Detection**: Use `getattr(sys, 'frozen', False)` to check mode
- **Resource Paths**: Always use `config_loader.py` or `resource_manager.py` for path resolution

### Core Workflow System
The workflow orchestrator (`scripts/workflow.py`, 2468 lines) coordinates four steps:
1. **Video Extraction** → `video_frame_extractor.py` (with EXIF embedding via `exif_embedder.py`)
2. **Image Conversion** → `ConvertImage.py` (HEIC to JPG, preserves GPS)
3. **AI Description** → `image_describer.py` (multi-provider support)
4. **HTML Generation** → `descriptions_to_html.py`

Workflow directories: `wf_YYYY-MM-DD_HHMMSS_{model}_{prompt}` (via `get_path_identifier_2_components()`)

### Configuration System
Layered resolution via `scripts/config_loader.py` (search order):
1. Explicit path passed by caller
2. File environment variable (e.g., `IDT_IMAGE_DESCRIBER_CONFIG`)
3. `IDT_CONFIG_DIR` env var + filename
4. Frozen exe dir `/scripts/<filename>`
5. Frozen exe dir `/<filename>`
6. Current working directory
7. Bundled script directory (fallback)

**Key configs**: `workflow_config.json`, `image_describer_config.json`

### AI Provider System
Multi-provider abstraction in `imagedescriber/ai_providers.py`:
- **Ollama** (local + cloud): Via `ollama` Python SDK
- **OpenAI**: GPT-4o, official SDK with retry logic
- **Claude**: Anthropic SDK with streaming support
- **Provider Registry**: `models/model_registry.py` - central model metadata
- **Capabilities**: `models/provider_configs.py` - dynamic UI based on `supports_prompts()`, `supports_custom_prompts()`

### Build & Release System
- **Master Build**: `BuildAndRelease/builditall.bat` - builds all 5 apps sequentially
- **Spec File**: `BuildAndRelease/final_working.spec` - PyInstaller config with explicit imports
- **Per-App Builds**: Each GUI has `build_*.bat` in its directory
- **Critical**: Update `hiddenimports` in spec file when adding modules

## Development Workflows

### Running Tests
```bash
# Pytest (standard)
pytest pytest_tests/

# Custom runner (Python 3.13 compatibility)
python run_unit_tests.py

# Coverage
pytest --cov=scripts pytest_tests/
```

**Test structure**: `pytest_tests/unit/` and `pytest_tests/smoke/`
**Config**: `pyproject.toml` (pytest options, coverage settings)

### Building Executables
```bash
# Build all applications (recommended)
BuildAndRelease\builditall.bat

# Build IDT CLI only
BuildAndRelease\build_idt.bat

# Build individual GUI apps
cd viewer && build_viewer.bat
cd imagedescriber && build_imagedescriber.bat
```

### Testing Executable After Build
```bash
# Quick smoke test
dist\idt.exe version

# Path debugging
dist\idt.exe --debug-paths
```

## Project-Specific Conventions

### Filesystem Sanitization
Use `sanitize_name()` from `scripts/workflow.py` for model/prompt names:
- Removes non-alphanumeric chars (except `_`, `-`, `.`)
- Preserves case by default (pass `preserve_case=False` to lowercase)
- Example: `"GPT-4 Vision"` → `"GPT-4Vision"`

### Prompt Style Handling
- Prompt variations stored in `image_describer_config.json`
- **Case-insensitive lookup**: `validate_prompt_style()` uses `lower_variations` dict
- Default style: `"narrative"`
- Access via `get_default_prompt_style()` in `scripts/image_describer.py`

### Workflow Metadata
- **Metadata file**: `workflow_metadata.json` in each workflow directory
- **Functions**: `save_workflow_metadata()`, `load_workflow_metadata()` in `workflow_utils.py`
- **Contains**: Timestamp, model, prompt style, step configurations

### Code Reuse Pattern
**Always check for existing implementations before creating new code:**
- **Workflow scanning**: Import from `scripts/list_results.py`
  - `find_workflow_directories()` - scans for `wf_*` directories
  - `count_descriptions()` - counts images vs descriptions
  - `format_timestamp()` - consistent date formatting
  - `parse_directory_name()` - extracts components from workflow dir names
- **Date extraction**: Use `get_image_date_for_sorting()` from `analysis/combine_workflow_descriptions.py`
  - Priority: DateTimeOriginal > DateTimeDigitized > DateTime > file mtime

### Analysis Tools
All accessible via `idt` commands:
- **`idt combinedescriptions`** - Export workflows to CSV/Excel (date-sorted by EXIF)
- **`idt stats`** - Performance analysis (tokens, timing, costs)
- **`idt contentreview`** - Description quality review

## GUI Development (PyQt6)

### Accessibility Requirements (WCAG 2.2 AA)
- **Single Tab Stops**: Use `QListWidget` instead of `QTableWidget` when possible
- **Combined Text**: Concatenate data into single strings for list items (not multiple columns)
- **Screen Reader Support**: Always set `setAccessibleName()` and `setAccessibleDescription()`
- **Keyboard Navigation**: All functionality must work via keyboard (arrows, Enter, Tab)

### Date/Time Formatting Standard
**Format**: `M/D/YYYY H:MMP` (no leading zeros, A/P suffix)
- Examples: `3/25/2025 7:35P`, `10/16/2025 8:03A`
- **EXIF Priority**: DateTimeOriginal > DateTimeDigitized > DateTime > file mtime
- **Consistency**: Use same format for workflow timestamps and image dates

### Window Title Guidelines
- **Always show stats**: `"XX%, X of Y images described"` (integer percentage)
- **Live mode**: Add `"(Live)"` suffix when monitoring
- **Context**: Include workflow name for screen reader clarity

### Error Handling Pattern
```python
# Graceful degradation - always provide fallbacks
try:
    from optional_module import feature
except ImportError:
    feature = None  # Fallback to basic behavior

# Don't crash on missing data
try:
    date = extract_exif_date(image)
except Exception:
    date = datetime.fromtimestamp(image_path.stat().st_mtime)
```

## Common Pitfalls

### PyInstaller Hidden Imports
**Problem**: Modules not found in frozen executable
**Solution**: Update `BuildAndRelease/final_working.spec` `hiddenimports` list
```python
hiddenimports=[
    'scripts.new_module',  # Add your module here
    'anthropic._client',   # Include submodules for SDKs
]
```

### Config File Not Found in Executable
**Problem**: Config loads in dev but not in executable
**Solution**: Use `config_loader.py`, not raw `Path()` or `open()`
```python
# WRONG
config_path = Path("scripts/workflow_config.json")

# RIGHT
from config_loader import load_json_config
config, path, source = load_json_config('workflow_config.json')
```

### Duplicate Code Detection
**Problem**: Functionality exists elsewhere but not discovered
**Solution**: Search before implementing
```bash
# Semantic search for similar functionality
grep -r "function_name" scripts/
grep -r "similar_concept" *.py

# Check for existing workflow utilities
grep -r "find_workflow\|count_descriptions\|format_timestamp" scripts/
```

## Documentation Requirements

### Session Summaries
Location: `docs/worktracking/YYYY-MM-DD-session-summary.md`
**Include**:
- Changes made (files modified, features added)
- Technical decisions and rationale  
- Testing results
- User-friendly summary of accomplishments

### Code Comments
- **"Why" not "what"**: Document intent and design decisions
- **PyInstaller notes**: Flag frozen-specific code with comments
- **Accessibility notes**: Document screen reader considerations

## Additional Resources

For in-depth technical details, see `docs/archive/AI_AGENT_REFERENCE.md` covering:
- Complete CLI command reference with usage patterns
- Image optimization math and provider limits (3.75MB base64 encoding)
- Build troubleshooting guide and historical context
- Detailed GUI application specifications
- Virtual environment strategy and architecture detection

