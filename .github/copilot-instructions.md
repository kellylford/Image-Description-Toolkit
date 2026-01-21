# GitHub Copilot Instructions for Image-Description-Toolkit

**Agent Acknowledgment**: At the start of each response, identify yourself using your actual model name and confirm you understand and will follow these instructions.

# ⚠️ CRITICAL REMINDERS

**NEVER claim code is fixed without actually RUNNING it**
**PyInstaller frozen executables are NOT the same as Python scripts**
**`from scripts.X` ALWAYS fails in frozen mode - use module-level imports**
**Production code that's been working for months should be changed with EXTREME caution**
**INCOMPLETE REFACTORS caused 23% of commits to be fixes - ALWAYS check ALL callers**
**Changing function signatures REQUIRES updating ALL callers - search first, change later**

## 🚨 MANDATORY READING

**Before making ANY code changes**, review:
- **[Pre-Commit Verification Checklist](docs/worktracking/PRE_COMMIT_VERIFICATION_CHECKLIST.md)** - MANDATORY checklist to complete BEFORE any code changes
- **[AI Comprehensive Review Protocol](docs/worktracking/AI_COMPREHENSIVE_REVIEW_PROTOCOL.md)** - Required checklists for all changes
- **[Migration Audit](docs/worktracking/2026-01-20-MIGRATION-AUDIT.md)** - Known issues and patterns to avoid

**Failure to follow these protocols has caused critical production failures.**

## ⚠️ PRE-COMMIT VERIFICATION PROTOCOL

**BEFORE making ANY code change:**
1. ✅ Complete Phase 1: Read actual code, verify names exist
2. ✅ Complete Phase 2: Search for impacts, check all callers
3. ✅ Complete Phase 3: Make minimal changes only
4. ✅ Complete Phase 4: BUILD and TEST the executable
5. ✅ Complete Phase 5: Document actual results (not "should work")

**See [PRE_COMMIT_VERIFICATION_CHECKLIST.md](docs/worktracking/PRE_COMMIT_VERIFICATION_CHECKLIST.md) for full details.**

**DO NOT claim something is "fixed" or "done" without completing ALL phases.**

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

11. **MANDATORY Pre-Change Verification** (See AI_COMPREHENSIVE_REVIEW_PROTOCOL.md):
    - **Variable Renames**: Use `grep -r "variable_name"` to find ALL occurrences before changing ANY
    - **Function Signature Changes**: Use `list_code_usages` tool to find ALL callers before modifying
    - **Import Changes**: Verify PyInstaller compatibility with try/except fallback pattern
    - **Large Functions** (>500 lines): Assume high risk - extra scrutiny required
    - **Return Statements**: Verify all referenced variables are defined in scope
    - **Lambda Functions**: Check variable references in sort keys and filters

12. **MANDATORY Post-Change Testing**:
    - ✅ Syntax validation: `python -m py_compile <file>`
    - ✅ Development mode: Run actual command with test data
    - ✅ Build frozen exe: `cd idt && build_idt.bat`
    - ✅ Test frozen exe: `dist/idt.exe <command> testimages`
    - ✅ Check logs: `grep -i error wf_*/logs/*.log`
    - ❌ NEVER claim "fixed" without completing ALL of above

## Forbidden Code Patterns (PyInstaller Compatibility)

These patterns ALWAYS break in PyInstaller frozen mode:

❌ **NEVER use these imports:**
```python
from scripts.module_name import X
from imagedescriber.module import X
from analysis.module import X
```

✅ **ALWAYS use module-level imports with try/except:**
```python
# At module level (top of file)
try:
    from config_loader import load_json_config
except ImportError:
    load_json_config = None

# Then use the imported variable in functions
# DON'T re-import inside functions!
```

✅ **If you MUST import in a function (rare), use this pattern:**
```python
try:
    from module_name import X  # Frozen mode
except ImportError:
    from scripts.module_name import X  # Dev mode only
```

**Why this matters:** In frozen executables, PyInstaller flattens the directory structure. The `scripts` package doesn't exist in `_MEIPASS`. Code that works perfectly in development will crash in production if you use `from scripts.X`.

## Mandatory Testing Protocol for Core Files

**Files requiring BUILD + RUN testing before claiming complete:**
- `scripts/workflow.py`
- `scripts/image_describer.py`
- `idt/idt_cli.py`
- Any file included in PyInstaller .spec files

**Testing Protocol:**
1. Make code changes
2. Run `cd idt && build_idt.bat` (Windows) or full `builditall_wx.bat`
3. Run `dist\idt.exe workflow testimages` with actual test data
4. Verify it completes WITHOUT ERRORS (exit code 0)
5. Check log files in `wf_*/logs/` for actual errors
6. Read the workflow log AND the image_describer log
7. ONLY THEN claim the fix is complete

**Session Summary Requirements:**
Must include:
- **Build verification**: "Built idt.exe successfully: [YES/NO]"
- **Runtime testing**: "Tested with command: `[actual command]`"
- **Test results**: "Exit code: [X], Errors: [Y/N], Log file reviewed: [path]"
- **NOT tested**: Explicitly state what wasn't tested and why

**Never say "this should work" or "the fix looks correct" - PROVE it works.**

## Variable Renaming Safety Checklist

When renaming variables or refactoring:
1. Search for ALL usages: `grep -r "old_name" scripts/` or use `list_code_usages` tool
2. Check both the variable itself AND similar names (e.g., `unique_images` vs `unique_source_count`)
3. In functions with 500+ lines, assume high risk of missing references
4. Test after EVERY change, not just at the end
5. If renaming affects return values, check ALL callers

**Example of what goes wrong:** Renaming `unique_images` to `unique_source_count` in one place but missing it in return statements causes `NameError: name 'unique_source_count' is not defined`.

## Regression Prevention Rules

Before "fixing" working code:
1. **Verify the bug exists** - Don't fix based on theory alone
2. **Test the current behavior** - What actually happens vs. what should happen?
3. **Minimal changes only** - Don't refactor while fixing bugs
4. **One problem at a time** - Don't fix multiple issues in one commit
5. **Production code caution** - If code has been working in production for months, be EXTREMELY cautious about "improvements"

If the user reports something "has been working for months," your first assumption should be: **The code is probably correct, and the issue is elsewhere.**



## Architecture Overview

### Multi-Application Structure
IDT consists of five standalone applications, each with isolated dependencies:
- **`idt.exe`** / **`idt`** - CLI dispatcher (routes to all commands via `idt_cli.py`)
- **`viewer.exe`** / **`Viewer.app`** - wxPython workflow results browser with live monitoring
- **`imagedescriber.exe`** / **`ImageDescriber.app`** - wxPython batch processing GUI (883 lines main frame)
- **`prompteditor.exe`** / **`PromptEditor.app`** - Visual prompt template editor
- **`idtconfigure.exe`** / **`IDTConfigure.app`** - Configuration management interface

Each GUI application has its own `.venv` and build scripts in its directory. All GUI apps migrated from PyQt6 to **wxPython** for cross-platform compatibility (Windows/macOS).

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
- **Windows Master Build**: `BuildAndRelease/WinBuilds/builditall_wx.bat` - builds all 5 apps sequentially
- **macOS Master Build**: `BuildAndRelease/MacBuilds/builditall_macos.command` - builds all 5 .app bundles
- **Spec Files**: Each app directory has its own `.spec` file (e.g., `viewer/viewer_wx.spec`)
- **Per-App Builds**: Each app has platform-specific build scripts
  - Windows: `build_*_wx.bat`
  - macOS Terminal: `build_*_wx.sh`
  - macOS Finder: `build_*_macos.command` (double-clickable)
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


**Windows:**
```batch
REM Build all applications (recommended)
BuildAndRelease\WinBuilds\builditall_wx.bat

REM Build individual apps
cd idt && build_idt.bat
cd viewer && build_viewer_wx.bat
cd imagedescriber && build_imagedescriber_wx.bat
```

**macOS:**
```bash
# Build all applications (recommended)
./BuildAndRelease/MacBuilds/builditall_macos.command


**Windows:**
```batch
REM Quick smoke test
dist\idt.exe version

REM Path debugging
dist\idt.exe --debug-paths

REM Test GUI apps
dist\Viewer.exe
```

**macOS:**
```bash
# Quick smoke test
./dist/idt version

# Path debugging
./dist/idt --debug-paths

# Test GUI apps
open dist/Viewer.apps
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
wxPython)

### Accessibility Requirements (WCAG 2.2 AA)
- **Single Tab Stops**: Use `wx.ListBox` instead of `wx.ListCtrl` when possible
- **Combined Text**: Concatenate data into single strings for list items (not multiple columns)
- **Screen Reader Support**: Set `name=` parameter in widget constructors for accessible labels
  ```python
  # CORRECT
  self.image_list = wx.ListBox(panel, name="Images in workspace")
  
  # WRONG - wxPython doesn't have SetAccessibleName()
  label.SetAccessibleName("Images list")  # ❌ Invalid API
  ``

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
- **Single Tab Stops*the app-specific `.spec` file in each app directory
```python
# Example: viewer/viewer_wx.spec
hiddenimports=[
    'scripts.new_module',  # Add your module here
    'anthropic._client',   # Include submodules for SDKs
    'shared.wx_common',    # Shared wxPython utilitie
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

### Virtual Environment Path Inconsistency (CRITICAL)
**Problem**: Build scripts fail with "winenv not found" error
**Root Cause**: Windows uses `.winenv` directory (with dot prefix), not `winenv`
**Solution**: ALL build scripts must reference `.winenv\Scripts\activate.bat`
```batch
REM WRONG - missing dot prefix
call winenv\Scripts\activate.bat

REM CORRECT - includes dot prefix
call .winenv\Scripts\activate.bat
```
**Historical Context**: The idt/build_idt.bat had this bug, causing builditall_wx.bat to fail on step 1/5. All other apps were already correct. This is easy to miss because the directory appears as `winenv` in some tools that hide dotfiles.

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

## Platform-Specific Considerations

### macOS Development
- **Module Imports**: Always add project root to `sys.path` for shared modules:
  ```python
  _project_root = Path(__file__).parent.parent
  if str(_project_root) not in sys.path:
      sys.path.insert(0, str(_project_root))
  ```
- **Path Resolution**: Pass `Path` objects directly to utilities (don't convert to strings unnecessarily)
- **Default Directories**: Never hardcode `~/Desktop` paths - use directory picker dialogs
- **Build Scripts**: `.command` files can be double-clicked in Finder; `.sh` files require Terminal

### Windows Development
- **UTF-8 Encoding**: Console output uses UTF-8 wrapper in workflow scripts
- **Console Titles**: Use `ctypes.windll.kernel32.SetConsoleTitleW()` for progress visibility
- **Path Separators**: Use `Path()` for cross-platform compatibility

## Additional Resources

For in-depth technical details, see:
- **[docs/archive/AI_AGENT_REFERENCE.md](docs/archive/AI_AGENT_REFERENCE.md)** - Complete CLI command reference, image optimization math, provider limits
- **[docs/AI_ONBOARDING.md](docs/AI_ONBOARDING.md)** - Current development status, active issues, session context
- **[BuildAndRelease/BUILD_SYSTEM_REFERENCE.md](BuildAndRelease/BUILD_SYSTEM_REFERENCE.md)** - Build system architecture and troubleshooting

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

