# Phase 2, Step 2.3: Implementation Roadmap

**Date:** 2026-01-14  
**Status:** Complete  
**Purpose:** Detailed step-by-step guide for Phases 3-7

---

## Executive Summary

| Phase | Name | Duration | Blockers | Status |
|-------|------|----------|----------|--------|
| 3 | Critical Config Fixes | 4-5h | None | ⬜ Ready |
| 4 | Code Deduplication | 6-8h | Phase 3 | ⬜ Ready |
| 5 | Consolidation & Cleanup | 3-4h | Phase 4 | ⬜ Ready |
| 6 | Testing & Validation | 3-5h | Phase 5 | ⬜ Ready |
| 7 | Documentation | 2-3h | Phase 6 | ⬜ Ready |

**Total Timeline:** ~18-25 hours across 5-7 development sessions

---

## Phase 3: Critical Config Loading Fixes (4-5 hours)

**Objective:** Fix all frozen mode bugs that will crash PyInstaller executables

**Scope:** 23 instances across 8 files (CRITICAL priority)

**Success Criteria:**
- All instances of direct `json.load()` replaced with `config_loader`
- Root workflow.py hardcoded frozen check fixed
- All fixes tested by building and running idt.exe

### Phase 3 Detailed Steps

#### Step 3.1: Fix viewer/viewer_wx.py (1 hour)

**File:** `viewer/viewer_wx.py`  
**Instances to Fix:** 4 (lines 375-376, 546-547, 927, 1215)  
**Configs:** workflow_config.json, image_describer_config.json, workflow_metadata.json

**Before:**
```python
# Line 375-376
with open(config_path) as f:
    config = json.load(f)

# Line 546-547
with open(config_path) as f:
    config = json.load(f)

# Line 927
with open(metadata_path) as f:
    metadata = json.load(f)

# Line 1215
with open(metadata_path) as f:
    metadata = json.load(f)
```

**After:**
```python
from scripts.config_loader import load_json_config, load_json_file

# Line 375-376 (workflow_config.json)
config, config_path, source = load_json_config('workflow_config.json')

# Line 546-547 (image_describer_config.json)
config, config_path, source = load_json_config('image_describer_config.json')

# Line 927 & 1215 (workflow_metadata.json)
metadata = load_json_file(metadata_path)  # For files with explicit path
```

**Testing:**
```bash
cd viewer
build_viewer_wx.bat
dist\Viewer.exe  # Should launch without errors
```

**Estimated Time:** 1 hour (includes testing)

---

#### Step 3.2: Fix scripts/workflow.py (1 hour)

**File:** `scripts/workflow.py`  
**Instances to Fix:** 2 (lines 1430-1431, 2391-2392)  
**Configs:** workflow_config.json, image_describer_config.json

**Before:**
```python
# Line 1430-1431
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# Line 2391-2392
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)
```

**After:**
```python
from scripts.config_loader import load_json_config

# Line 1430-1431
config, _, _ = load_json_config('workflow_config.json')

# Line 2391-2392
config, _, _ = load_json_config('image_describer_config.json')
```

**Testing:**
```bash
cd idt
build_idt.bat
dist\idt.exe workflow testimages
# Should complete without config file errors
```

**Estimated Time:** 1 hour (includes testing)

---

#### Step 3.3: Fix scripts/workflow_utils.py (0.75 hours)

**File:** `scripts/workflow_utils.py`  
**Instances to Fix:** 2 (lines 41-42, 601)  
**Configs:** workflow_config.json

**Note:** This file contains `WorkflowConfig` class that loads config - needs careful attention

**Before:**
```python
# WorkflowConfig class, line 41-42
with open(config_path, 'r', encoding='utf-8') as f:
    return json.load(f)

# Line 601
with open(config_path, 'r', encoding='utf-8') as f:
    return json.load(f)
```

**After:**
```python
from scripts.config_loader import load_json_config, load_json_file

# In WorkflowConfig.load(), line 41-42
# Use explicit path if provided, otherwise use config_loader
if config_path:
    config = load_json_file(config_path)
else:
    config, _, _ = load_json_config('workflow_config.json')

# Line 601 (similar pattern)
```

**Testing:**
```bash
# Verify WorkflowConfig still loads correctly
python -c "from scripts.workflow_utils import WorkflowConfig; print('OK')"
```

**Estimated Time:** 0.75 hours

---

#### Step 3.4: Fix remaining 5 core files (1 hour total)

**Files:**
- `scripts/list_results.py` (line 49) - 0.25h
- `scripts/video_frame_extractor.py` (line 163) - 0.25h
- `scripts/metadata_extractor.py` (line 388) - 0.25h
- `shared/wx_common.py` (line 199) - 0.25h

**Pattern:** All are simple one-instance replacements following same pattern as Step 3.1-3.3

**Testing:** Run each affected script to verify config loading works

**Estimated Time:** 1 hour total for all 4 files

---

#### Step 3.5: Fix Root workflow.py Hardcoded Frozen Check (0.25 hours)

**File:** `workflow.py` (in repository root)  
**Lines:** 10, 13, 39  
**Type:** QUICK WIN #1

**Before:**
```python
if sys._MEIPASS:  # ❌ Hardcoded, may raise AttributeError
    return os.path.join(sys._MEIPASS, relative_path)
```

**After:**
```python
if getattr(sys, 'frozen', False):  # ✅ Safe in all modes
    return os.path.join(sys._MEIPASS, relative_path)
```

**Testing:**
```bash
python workflow.py  # Should run without AttributeError
```

**Estimated Time:** 0.25 hours

---

#### Step 3.6: Build and Integration Test (0.5-1 hour)

**Objective:** Verify all fixes work in actual executables

**Tests to Run:**

1. **Build All Applications:**
```bash
BuildAndRelease\WinBuilds\builditall_wx.bat
# Should complete without errors
```

2. **Test idt.exe CLI:**
```bash
dist\idt.exe workflow testimages --model qwen --provider ollama
# Should complete workflow without config errors
# Check logs in wf_*/logs/ for any issues
```

3. **Test Viewer.exe:**
```bash
dist\Viewer.exe
# Should launch and display workflows without file not found errors
```

4. **Test ImageDescriber.exe:**
```bash
dist\ImageDescriber.exe
# Should launch and display config options
```

**Success Criteria:**
- All builds complete without errors
- All executables launch without file-not-found errors
- Workflow completes without config loading errors
- Exit codes are 0 for successful runs

**Estimated Time:** 0.5-1 hour

---

### Phase 3 Summary

**Files Changed:** 8 files, 23 instances fixed  
**Total Time:** 4-5 hours  
**Critical Path Item:** Yes - Must complete before Phase 4  
**Testing Required:** Integration testing with actual executables  

**Completion Checklist:**
- [ ] All 23 direct json.load() calls replaced
- [ ] Root workflow.py hardcoded check fixed
- [ ] builditall_wx.bat completes successfully
- [ ] idt.exe runs workflow without errors
- [ ] Viewer.exe, ImageDescriber.exe launch without errors
- [ ] All changes committed to branch

---

## Phase 4: Code Deduplication (6-8 hours)

**Objective:** Consolidate duplicate code into shared utility modules

**Scope:** 3 major deduplication categories + supporting fixes

**Success Criteria:**
- All duplicate code consolidated to shared/ directory
- All imports updated to use shared versions
- Existing tests pass, new tests added
- No functionality changes, only refactoring

### Phase 4 Detailed Steps

#### Step 4.1: Create shared/utility_functions.py (1.5 hours)

**Objective:** Consolidate filename sanitization functions

**New File:** `shared/utility_functions.py`

**Functions to Implement:**
```python
def sanitize_name(name: str, preserve_case: bool = True) -> str:
    """
    Convert names to filesystem-safe strings.
    
    EXIF field name priority:
    1. DateTimeOriginal - Most reliable, set by camera
    2. DateTimeDigitized - When image was digitized
    3. DateTime - Generic datetime
    4. File mtime - Last resort fallback
    """

def format_timestamp_standard(timestamp_str: str) -> str:
    """Format EXIF timestamp to M/D/YYYY H:MMP format"""

def extract_workflow_name_from_path(workflow_path: Path) -> str:
    """Extract workflow name from wf_YYYY-MM-DD_HHMMSS_* directory"""
```

**Implementation:**
1. Copy `sanitize_name()` from `scripts/workflow.py` (lines 73-76)
2. Add docstring explaining filesystem safety
3. Copy regex pattern and logic
4. Create unit tests in `pytest_tests/unit/test_shared_utilities.py`

**Testing:**
```bash
pytest pytest_tests/unit/test_shared_utilities.py -v
pytest pytest_tests/unit/test_sanitization.py -v  # Existing tests should still pass
```

**Estimated Time:** 1.5 hours

---

#### Step 4.2: Create shared/exif_utils.py (3 hours)

**Objective:** Consolidate EXIF date extraction functions

**New File:** `shared/exif_utils.py`

**Functions to Implement:**
```python
def extract_exif_date_string(image_path: Union[str, Path]) -> str:
    """
    Extract date from image EXIF data, return as string.
    Format: M/D/YYYY H:MMP (e.g., "3/25/2025 7:35P")
    
    Field priority: DateTimeOriginal > DateTimeDigitized > DateTime > file mtime
    """

def extract_exif_datetime(image_path: Union[str, Path]) -> datetime:
    """
    Extract date from image EXIF data, return as datetime object.
    
    Field priority: DateTimeOriginal > DateTimeDigitized > DateTime > file mtime
    """

def extract_exif_data(image_path: Union[str, Path]) -> Dict[str, Any]:
    """Extract all EXIF data from image including GPS coordinates."""

def extract_exif_gps(exif_data: Dict[str, Any]) -> Optional[Dict[str, float]]:
    """Extract GPS coordinates from EXIF data."""
```

**Implementation Steps:**

1. **Analyze current implementations:**
   - `viewer/viewer_wx.py` `get_image_date()` (lines 97-115)
   - `tools/show_metadata/show_metadata.py` `_extract_datetime()` (lines 62-80)
   - `analysis/combine_workflow_descriptions.py` `get_image_date_for_sorting()` (~40 lines)
   - `MetaData/enhanced_metadata_extraction.py` `parse_exifread_gps()` (lines 176-220)

2. **Consolidate logic:**
   - Use `PIL.Image` for basic EXIF
   - Use `piexif` or `exifread` for extended EXIF (check existing imports)
   - Implement field priority correctly
   - Support fallback to file mtime

3. **Create comprehensive unit tests:**
   - Test each extraction function
   - Test field priority (DateTimeOriginal preferred)
   - Test format consistency
   - Test fallback to file mtime
   - Test GPS extraction

4. **Update imports in affected files:**
   - `viewer/viewer_wx.py` - use `extract_exif_date_string()`
   - `tools/show_metadata/show_metadata.py` - use `extract_exif_date_string()`
   - `analysis/combine_workflow_descriptions.py` - use `extract_exif_datetime()`
   - `MetaData/enhanced_metadata_extraction.py` - use `extract_exif_data()`

**Testing:**
```bash
pytest pytest_tests/unit/test_exif_utils.py -v
# Run full viewer tests to ensure GUI still works
python -m pytest -k "viewer" -v
```

**Estimated Time:** 3 hours (implementation + testing)

---

#### Step 4.3: Create shared/window_title_builder.py (1.5 hours)

**Objective:** Consolidate window title builder functions

**New File:** `shared/window_title_builder.py`

**Functions to Implement:**
```python
def build_window_title(
    app_name: str,
    progress_percent: int,
    current: int,
    total: int,
    workflow_name: str = None,
    prompt_style: str = None,
    model_name: str = None,
    suffix: str = ""
) -> str:
    """
    Build standardized window title for IDT applications.
    
    Format: "app_name - (progress_percent%, current of total) [context]"
    Example: "IDT - Describing Images (35%, 7 of 20) [GPT-4 Vision, detailed]"
    """
```

**Implementation:**

1. **Review current implementations:**
   - `scripts/image_describer.py` `_build_window_title()` (lines 243-258) - Complex
   - `scripts/video_frame_extractor.py` `_build_window_title()` (lines 76-78) - Simplified

2. **Consolidate into single function:**
   - Supports optional context (workflow, prompt, model)
   - Formats consistently
   - Returns string ready for display

3. **Update both files to use shared builder:**
   ```python
   # In image_describer.py and video_frame_extractor.py
   from shared.window_title_builder import build_window_title
   
   # Replace _build_window_title() methods with call to shared function
   title = build_window_title(
       app_name="IDT - Describing Images",
       progress_percent=progress_percent,
       current=current,
       total=total,
       workflow_name=self.workflow_name,
       prompt_style=self.prompt_style,
       model_name=self.model_name
   )
   ```

4. **Create unit tests:**
   - Test basic format
   - Test with and without context
   - Test percentage formatting
   - Test suffix handling

**Testing:**
```bash
pytest pytest_tests/unit/test_window_title_builder.py -v
# Run full workflow tests to ensure progress display still works
```

**Estimated Time:** 1.5 hours

---

#### Step 4.4: Update imagedescriber/ modules (1 hour)

**Objective:** Replace hardcoded paths with config_loader in GUI apps

**Files to Update:**
- `imagedescriber/workers_wx.py` (lines 211, 214)
- `imagedescriber/imagedescriber_wx.py` (config path references)

**Changes:**

Before (hardcoded paths):
```python
if getattr(sys, 'frozen', False):
    config_path = Path(sys._MEIPASS) / "scripts" / "image_describer_config.json"
else:
    config_path = Path(__file__).parent.parent / "scripts" / "image_describer_config.json"
```

After (using config_loader):
```python
from scripts.config_loader import load_json_config

config, config_path, source = load_json_config('image_describer_config.json')
# source tells us where it was loaded from for debugging
```

**Testing:**
```bash
cd imagedescriber
build_imagedescriber_wx.bat
dist\ImageDescriber.exe
# Verify config loads and GUI displays correctly
```

**Estimated Time:** 1 hour

---

#### Step 4.5: Integration Testing (1-2 hours)

**Objective:** Verify all deduplication changes work end-to-end

**Tests to Run:**

1. **Unit Tests:**
```bash
pytest pytest_tests/ -v
# All existing tests should pass
# New shared utility tests should pass
```

2. **Build Verification:**
```bash
BuildAndRelease\WinBuilds\builditall_wx.bat
# All executables should build successfully
```

3. **Functional Testing:**
```bash
# Test CLI workflow
dist\idt.exe workflow testimages --model qwen --provider ollama

# Test GUI apps
dist\Viewer.exe
dist\ImageDescriber.exe
dist\PromptEditor.exe
dist\IDTConfigure.exe
```

4. **Code Review Checklist:**
- [ ] No more duplicate functions in source
- [ ] All duplicate implementations deleted/replaced
- [ ] All imports updated to use shared versions
- [ ] No broken imports or missing modules
- [ ] Test coverage increased for shared utilities

**Success Criteria:**
- All tests pass
- All builds successful
- All GUI apps launch without errors
- All workflows complete without errors

**Estimated Time:** 1-2 hours

---

### Phase 4 Summary

**Files Changed:**
- Created: 3 new shared utility files
- Modified: 7 files (remove duplicate code, add imports)
- Tests Added: 3 new test files in pytest_tests/

**Total Time:** 6-8 hours  
**Critical Path Item:** Yes - Phase 5 depends on this  
**Testing Required:** Unit tests + integration testing  

**Completion Checklist:**
- [ ] shared/utility_functions.py created and tested
- [ ] shared/exif_utils.py created and tested
- [ ] shared/window_title_builder.py created and tested
- [ ] All duplicate code removed from original files
- [ ] All imports updated
- [ ] All tests pass
- [ ] All executables build and run
- [ ] All changes committed to branch

---

## Phase 5: Consolidation & Cleanup (3-4 hours)

**Objective:** Remove deprecated files, consolidate remaining utilities, verify repository cleanliness

**Scope:** Remove deprecated code, investigate edge cases, finalize cleanup

### Phase 5 Detailed Steps

#### Step 5.1: Delete Deprecated Qt6 GUI Files (0.5 hours)

**Files to Delete:**
1. `imagedescriber/imagedescriber_qt6.py`
2. `viewer/viewer_qt6.py`
3. `prompt_editor/prompt_editor_qt6.py`
4. `idtconfigure/idtconfigure_qt6.py`

**Pre-Deletion Verification:**
```bash
# Verify no imports reference these files
grep -r "imagedescriber_qt6" .
grep -r "viewer_qt6" .
grep -r "prompt_editor_qt6" .
grep -r "idtconfigure_qt6" .

# Verify .spec files don't reference them
grep -r "qt6" BuildAndRelease/
grep -r "_qt6" --include="*.spec"
```

**Expected Result:** All grep searches return 0 results

**Action:** Delete the 4 files

**Post-Deletion Testing:**
```bash
BuildAndRelease\WinBuilds\builditall_wx.bat
# Should still build successfully without these files
```

**Estimated Time:** 0.5 hours

---

#### Step 5.2: Consolidate Workflow Discovery Utilities (1 hour)

**Objective:** Move workflow discovery to shared utilities if not already there

**Check Current Status:**
- Is `find_workflow_directories()` in `scripts/list_results.py`?
- Are there duplicate implementations in tools/?

**If Consolidation Needed:**
1. Move `find_workflow_directories()` to `shared/workflow_utils.py`
2. Update imports in all files that use it:
   - viewer/viewer_wx.py
   - tools/gallery/ scripts
   - analysis/ scripts
3. Verify no duplicate `parse_workflow_dirname()` implementations

**Testing:**
```bash
# Verify workflow discovery still works
dist\Viewer.exe
# Should still find and display workflows
```

**Estimated Time:** 1 hour

---

#### Step 5.3: Investigate Root workflow.py Usage (1.5 hours)

**Objective:** Understand if root `workflow.py` is used or legacy code

**Investigation Steps:**

1. **Check Git History:**
```bash
git log --oneline -- workflow.py | head -20
# When was it last modified?
git blame workflow.py | head -20
# Who last modified it and why?
```

2. **Check All References:**
```bash
grep -r "import workflow" . --include="*.py"
grep -r "from workflow" . --include="*.py"
grep -r "workflow\.py" . --include="*.py"
# Are there any imports of this file?
```

3. **Check CLI Dispatcher:**
- Is it referenced in `idt_cli.py`?
- Is it used as an entry point?

4. **Decision:**
   - **If unused:** Mark for removal in Phase 7, or remove now
   - **If used:** Understand why and consolidate with `scripts/workflow.py`
   - **If deprecated:** Document deprecation and timeline for removal

**Documentation:**
- Add finding to Phase 2 output
- Update prioritized_issues.md if new information discovered
- Create MEDIUM #3 supplement if needed

**Estimated Time:** 1.5 hours

---

#### Step 5.4: Repository Cleanliness Verification (0.5 hours)

**Checklist:**

1. **No Broken Imports:**
```bash
python -c "import scripts.workflow; print('OK')"
python -c "import imagedescriber.imagedescriber_wx; print('OK')"
python -c "import viewer.viewer_wx; print('OK')"
# All major modules should import without error
```

2. **No Orphaned Files:**
```bash
# Verify no Qt6 files remain
find . -name "*qt6*" -o -name "*Qt6*"
# Should return 0 results
```

3. **Build System Consistency:**
```bash
# Verify all .spec files are consistent
ls -la idt/*.spec imagedescriber/*.spec viewer/*.spec
# Should have matching _wx.spec versions
```

4. **No Circular Imports:**
```bash
python -c "import importlib.metadata; print('OK')"
# Try importing all main modules
```

**Estimated Time:** 0.5 hours

---

### Phase 5 Summary

**Files Changed:**
- Deleted: 4 deprecated Qt6 GUI files
- Moved: workflow discovery utilities (if needed)
- Updated: Import references

**Total Time:** 3-4 hours  
**Critical Path Item:** No - Independent of future phases  
**Testing Required:** Integration testing  

**Completion Checklist:**
- [ ] 4 Qt6 files deleted
- [ ] No references to deleted files remain
- [ ] Workflow discovery consolidated (if needed)
- [ ] Root workflow.py status documented
- [ ] All imports work correctly
- [ ] Build system still functions
- [ ] All changes committed to branch

---

## Phase 6: Testing & Validation (3-5 hours)

**Objective:** Comprehensive testing to ensure all changes work correctly

**Scope:** Unit testing, integration testing, build testing, quality checks

### Phase 6 Detailed Steps

#### Step 6.1: Run Full Test Suite (1 hour)

**Command:**
```bash
pytest pytest_tests/ -v --cov=scripts --cov=shared --cov=analysis --cov=imagedescriber
```

**Expected Results:**
- All existing tests pass
- New shared utility tests pass
- Code coverage maintained or improved
- No warnings or errors

**If Tests Fail:**
- Review failures
- Fix issues before proceeding
- Don't move to next step until all green

**Estimated Time:** 1 hour

---

#### Step 6.2: Full Build Testing (1.5 hours)

**Command:**
```bash
cd BuildAndRelease\WinBuilds
builditall_wx.bat
```

**Expected Results:**
- idt.exe builds successfully
- Viewer.exe builds successfully
- ImageDescriber.exe builds successfully
- PromptEditor.exe builds successfully
- IDTConfigure.exe builds successfully

**If Build Fails:**
- Check error messages
- Verify all imports are correct
- Check for missing modules in .spec files
- Update hiddenimports if needed
- Don't move to next step until all build

**Estimated Time:** 1.5 hours (builds can take time)

---

#### Step 6.3: Functional Testing (1-1.5 hours)

**Test idt.exe:**
```bash
dist\idt.exe version
# Should print version without errors

dist\idt.exe workflow testimages --model qwen --provider ollama
# Should complete workflow with no errors
# Check wf_*/logs/ for any issues
```

**Test Viewer.exe:**
```bash
dist\Viewer.exe
# Should launch GUI
# Should display existing workflows
# Should not crash on config loading
```

**Test ImageDescriber.exe:**
```bash
dist\ImageDescriber.exe
# Should launch GUI
# Should load config options
# Should allow batch processing
```

**Test PromptEditor.exe:**
```bash
dist\PromptEditor.exe
# Should launch GUI
# Should display and edit prompts
```

**Test IDTConfigure.exe:**
```bash
dist\IDTConfigure.exe
# Should launch GUI
# Should display configuration options
```

**Success Criteria:**
- All executables launch without errors
- All workflows complete successfully
- No FileNotFoundError for configs
- All GUIs display correctly
- All logs are clean (no errors)

**Estimated Time:** 1-1.5 hours

---

#### Step 6.4: Code Quality Review (0.5 hours)

**Checklist:**

1. **Code Style:**
```bash
pylint scripts/ --disable=all --enable=E,F
# Should have 0 errors
```

2. **Type Hints (if used):**
```bash
# Check if mypy is configured
mypy scripts/ --ignore-missing-imports
```

3. **Docstrings:**
- All new functions have docstrings
- All shared utilities are documented
- Comments explain frozen mode considerations

4. **Import Cleanliness:**
```bash
# No unused imports
# No circular imports
# All imports are from correct modules
```

**Estimated Time:** 0.5 hours

---

#### Step 6.5: Performance Verification (Optional, 0.5 hours)

**Objective:** Ensure deduplication didn't slow anything down

**Tests:**
1. Workflow performance test with sample images
2. GUI startup time
3. Config loading time
4. Memory usage comparison (if baseline exists)

**Note:** This is optional but recommended

**Estimated Time:** 0.5 hours (optional)

---

### Phase 6 Summary

**Total Time:** 3-5 hours  
**Critical Path Item:** Yes - Should complete before Phase 7  
**Testing Required:** Comprehensive automated + manual testing

**Completion Checklist:**
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] All executables build successfully
- [ ] All executables run without errors
- [ ] GUI apps launch and function correctly
- [ ] Workflows complete successfully
- [ ] No console errors or warnings
- [ ] Code quality checks pass
- [ ] All changes documented
- [ ] All changes committed to branch

---

## Phase 7: Documentation & Polish (2-3 hours)

**Objective:** Final documentation, comments, and cleanup

**Scope:** Code comments, developer documentation, release notes

### Phase 7 Detailed Steps

#### Step 7.1: Add Frozen Mode Comments (0.5 hours)

**Type:** QUICK WIN #3 & #4

**Add to Core Files:**
1. `scripts/workflow.py` - Add frozen mode explanation at top
2. `viewer/viewer_wx.py` - Add comment at config loading section
3. `scripts/config_loader.py` - Enhance existing documentation
4. `shared/utility_functions.py` - Add docstrings explaining each function

**Example Comment Block:**
```python
"""
Workflow orchestrator for image description pipeline.

FROZEN MODE SUPPORT:
- This module works in both development (python scripts/workflow.py)
  and frozen (idt.exe workflow) modes
- Config files are loaded via config_loader.py which handles both modes
- See config_loader.py for path resolution details
- Resource paths use config_loader for cross-platform compatibility
"""
```

**Estimated Time:** 0.5 hours

---

#### Step 7.2: Update Developer Documentation (1 hour)

**Files to Create/Update:**

1. **docs/FROZEN_MODE_GUIDE.md** - New file
   - Explanation of frozen mode detection
   - Pattern for config loading
   - Pattern for resource paths
   - Troubleshooting guide

2. **docs/SHARED_UTILITIES_GUIDE.md** - New file
   - Documentation of shared/utility_functions.py
   - Documentation of shared/exif_utils.py
   - Documentation of shared/window_title_builder.py
   - How to use each function
   - Examples

3. **docs/code_audit/REFACTORING_COMPLETE.md** - Summary document
   - What was done in Phases 1-7
   - Key improvements
   - Performance impact (if any)
   - Future recommendations

**Estimated Time:** 1 hour

---

#### Step 7.3: Update Codebase Quality Audit Plan (0.5 hours)

**Update:** `docs/code_audit/codebase-quality-audit-plan.md`

**Changes:**
- Mark all phases complete
- Add session logs with times and results
- Update status table
- Add notes on lessons learned
- Recommendations for future audits

**Estimated Time:** 0.5 hours

---

#### Step 7.4: Create Release Notes (0.5 hours)

**File:** Create new entry in CHANGELOG.md

**Format:**
```markdown
## [Version X.X.X] - 2026-01-14

### Internal Improvements
- Fixed 23+ frozen mode bugs in config file loading
- Consolidated duplicate filename sanitization functions
- Consolidated duplicate EXIF date extraction functions
- Removed hardcoded path assumptions
- Consolidated window title builders
- Removed 4 deprecated PyQt6 GUI files (~1,200 lines)
- Improved code reusability via new shared utilities

### Testing
- All unit tests passing
- All integration tests passing
- Verified all executables build and run correctly
- No regressions detected

### Technical Debt Paid Down
- Eliminated code duplication in 3 major areas
- Fixed all frozen mode bugs (23+ instances)
- Improved maintainability and code clarity
```

**Estimated Time:** 0.5 hours

---

### Phase 7 Summary

**Total Time:** 2-3 hours  
**Critical Path Item:** No - Nice to have but not blocking  
**Testing Required:** Code review and documentation verification

**Completion Checklist:**
- [ ] Frozen mode comments added to core files
- [ ] New developer guides created
- [ ] Audit plan updated with completion status
- [ ] CHANGELOG.md updated with refactoring notes
- [ ] All documentation is clear and accurate
- [ ] All changes committed to branch
- [ ] Ready for code review and merge

---

## Timeline Summary

| Phase | Duration | Blockers | Cumulative |
|-------|----------|----------|------------|
| 1: Discovery | 2h | None | 2h ✅ |
| 2: Prioritization | 1h | None | 3h ✅ |
| 3: Config Fixes | 4-5h | None | 7-8h |
| 4: Deduplication | 6-8h | Phase 3 | 13-16h |
| 5: Cleanup | 3-4h | Phase 4 | 16-20h |
| 6: Testing | 3-5h | Phase 5 | 19-25h |
| 7: Documentation | 2-3h | Phase 6 | 21-28h |

**Recommended Session Breakdown:**
- Session 1: Phase 3 (4-5h) - Single session
- Session 2: Phase 4 part 1 (3-4h) - Shared utilities creation
- Session 3: Phase 4 part 2 (2-4h) - Deduplication completion
- Session 4: Phase 5 (3-4h) - Cleanup and consolidation
- Session 5: Phase 6 (3-5h) - Comprehensive testing
- Session 6: Phase 7 (2-3h) - Final documentation

**Total Sessions:** 5-6 sessions over 2-3 weeks

---

## Quality Gates

**Before moving to next phase:**
- [ ] All changes from current phase committed
- [ ] All tests pass
- [ ] All builds successful
- [ ] Code review complete (if applicable)
- [ ] No regressions detected

**Before merging to main:**
- [ ] All 7 phases complete
- [ ] All tests passing
- [ ] All executables built and tested
- [ ] Code review approved
- [ ] Release notes updated
- [ ] Documentation updated

---

## Risk Management

**High Risk Areas:**
- Phase 3: Config loading changes - Core system, must be tested thoroughly
- Phase 4: Deduplication - Risk of missing references
- Phase 6: Integration testing - Must verify all functions work together

**Mitigation:**
- Test after each file change in Phase 3
- Search for all usages before removing duplicate code
- Run comprehensive test suite multiple times

**Rollback Plan:**
- If any phase causes issues, can rollback to last commit
- Each phase has clear commit boundaries
- Keep working branch separate from main until Phase 6 passes

---

**Document Status:** Complete and ready for implementation  
**Next Action:** Begin Phase 3 when ready, or continue to other analysis in Phase 2
