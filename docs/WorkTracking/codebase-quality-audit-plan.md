# Codebase Quality Audit & Improvement Plan

**Status:** 🔄 In Progress  
**Started:** 2026-01-13  
**Current Phase:** Phase 1 - Discovery & Mapping  
**Last Updated:** 2026-01-13

---

## Session Management Strategy

**Recommended Approach:**
- ✅ **YES - Start new sessions between phases** - Each phase is substantial and should have fresh context
- ✅ **Save and commit after each completed phase** - Allows easy rollback if issues arise
- ⚠️ **Within a phase, continue same session** - Maintains context for related changes
- 📝 **Update this document at end of each session** - Check off completed items, note blockers

**To Resume:**
Say: "Continue codebase quality audit plan at Phase [X], Step [Y]"

---

## Quick Status Overview

| Phase | Status | Sessions Used | Blockers |
|-------|--------|---------------|----------|
| Phase 1: Discovery & Mapping | 🔄 In Progress | 1 | None |
| Phase 2: Analysis & Prioritization | ⬜ Not Started | 0 | None |
| Phase 3: Shared Utility Modules | ⬜ Not Started | 0 | None |
| Phase 4: Refactor Existing Code | ⬜ Not Started | 0 | None |
| Phase 5: Standardization | ⬜ Not Started | 0 | None |
| Phase 6: Testing & Validation | ⬜ Not Started | 0 | None |
| Phase 7: Documentation | ⬜ Not Started | 0 | None |

**Legend:** ⬜ Not Started | 🔄 In Progress | ✅ Complete | ⚠️ Blocked

---

## Phase 1: Discovery & Mapping (Est: 1-2 sessions)

**Objective:** Build a complete map of the codebase structure and identify problem areas

**Status:** 🔄 In Progress  
**Session Notes:** Started 2026-01-13. Completed Step 1.1 but need to add all 5 GUI apps (viewer, prompt_editor, idtconfigure) and idt dispatcher.

### Step 1.1: Create Module Dependency Map
- [x] Scan all Python files in `scripts/`, `analysis/`, `imagedescriber/`, `models/`
- [x] Scan all Python files in `viewer/`, `prompt_editor/`, `idtconfigure/`, `idt/`
- [x] Map all imports between modules (who imports whom)
- [x] Identify circular dependencies
- [x] Create visualization or detailed list
- [x] Document all 5 GUI applications
- [x] Output: `docs/code_audit/dependency_map.md`
- [x] Commit changes

### Step 1.2: Identify Duplicate Code
- [ ] Search for similar function signatures across all Python files
- [ ] Look for repeated logic patterns:
  - [ ] File discovery/scanning
  - [ ] Path resolution
  - [ ] Config loading
  - [ ] EXIF reading
  - [ ] Progress tracking
- [ ] Flag functions with >80% code similarity
- [ ] Use `grep_search` and `semantic_search` tools extensively
- [ ] Output: `docs/code_audit/duplicate_code_report.md`
- [ ] Commit changes

### Step 1.3: Catalog All Entry Points
- [ ] List all CLI commands in `idt/idt_cli.py`
- [ ] List all GUI applications (5 total: idt, viewer, imagedescriber, prompteditor, idtconfigure)
- [ ] Document what each entry point calls (direct dependencies)
- [ ] Map workflow: CLI → scripts → utilities
- [ ] Output: `docs/code_audit/entry_points.md`
- [ ] Commit changes

### Step 1.4: Find All PyInstaller Concerns
- [ ] Search for problematic import patterns:
  - [ ] `from scripts.X import Y`
  - [ ] `from imagedescriber.X import Y`
  - [ ] `from analysis.X import Y`
- [ ] Identify hardcoded paths instead of `config_loader` usage
- [ ] Find `open()` calls on config files without using `config_loader`
- [ ] Find file path operations that don't handle frozen mode
- [ ] Output: `docs/code_audit/pyinstaller_issues.md`
- [ ] Commit changes

**Phase 1 Complete:** ⬜  
**Deliverables Created:** [x] dependency_map.md [ ] duplicate_code_report.md [ ] entry_points.md [ ] pyinstaller_issues.md

**Notes:** Step 1.1 completed 2026-01-13. Discovered all 5 GUI apps properly use shared/wx_common.py. Found 5 deprecated Qt6 files that can be removed in Phase 2.

---

## Phase 2: Analysis & Prioritization (Est: 1 session)

**Objective:** Categorize findings and prioritize fixes

**Status:** ⬜ Not Started  
**Session Notes:** [Add notes here]

### Step 2.1: Categorize Issues by Severity
- [ ] Review all Phase 1 outputs
- [ ] Categorize each issue as:
  - [ ] **Critical:** Bugs that break frozen executables (fix immediately)
  - [ ] **High:** Code duplication causing maintenance burden
  - [ ] **Medium:** Non-modular code that could be refactored
  - [ ] **Low:** Style/documentation improvements
- [ ] Create prioritized fix list
- [ ] Update: `docs/code_audit/prioritized_issues.md`
- [ ] Commit changes

### Step 2.2: Create Refactoring Opportunities List
- [ ] Find functions used in 3+ places that should be in shared utilities
- [ ] Identify config/path resolution code that should use `config_loader`
- [ ] Note error handling patterns that should be standardized
- [ ] List progress tracking implementations that could be unified
- [ ] Output: `docs/code_audit/refactoring_candidates.md`
- [ ] Commit changes

### Step 2.3: Identify Missing Shared Utilities
- [ ] List common patterns without a shared function:
  - [ ] EXIF date extraction
  - [ ] File discovery
  - [ ] Progress tracking
  - [ ] Path resolution
  - [ ] Config loading
- [ ] Propose new utility modules structure
- [ ] Output: `docs/code_audit/missing_utilities.md`
- [ ] Commit changes

**Phase 2 Complete:** ⬜  
**Deliverables Created:** [ ] prioritized_issues.md [ ] refactoring_candidates.md [ ] missing_utilities.md

---

## Phase 3: Create Shared Utility Modules (Est: 2-3 sessions)

**Objective:** Build central utility modules to eliminate duplication

**Status:** ⬜ Not Started  
**Session Notes:** [Add notes here]

### Step 3.1: Create `shared/file_utils.py`
- [ ] Design API for common file operations
- [ ] Consolidate file discovery logic from multiple scripts
- [ ] Standardize recursive directory scanning
- [ ] Single source of truth for supported file formats
- [ ] Implement frozen/dev mode compatibility
- [ ] Add comprehensive docstrings
- [ ] Add type hints
- [ ] Create unit tests in `pytest_tests/test_file_utils.py`
- [ ] Update `idt/idt.spec` hiddenimports: `'shared.file_utils'`
- [ ] Build and test: `cd idt && build_idt.bat`
- [ ] Commit changes

### Step 3.2: Create `shared/path_utils.py`
- [ ] Design API for path resolution
- [ ] Centralize path resolution (leveraging `config_loader`)
- [ ] Handle frozen vs dev mode consistently
- [ ] Workspace/workflow path utilities
- [ ] Add comprehensive docstrings
- [ ] Add type hints
- [ ] Create unit tests in `pytest_tests/test_path_utils.py`
- [ ] Update `idt/idt.spec` hiddenimports: `'shared.path_utils'`
- [ ] Build and test: `cd idt && build_idt.bat`
- [ ] Commit changes

### Step 3.3: Create `shared/exif_utils.py`
- [ ] Design API for EXIF operations
- [ ] Consolidate EXIF reading/writing from multiple places
- [ ] Single date extraction function (DateTimeOriginal > DateTimeDigitized > DateTime > mtime)
- [ ] GPS coordinate parsing
- [ ] Handle missing EXIF data gracefully
- [ ] Add comprehensive docstrings
- [ ] Add type hints
- [ ] Create unit tests in `pytest_tests/test_exif_utils.py`
- [ ] Update `idt/idt.spec` hiddenimports: `'shared.exif_utils'`
- [ ] Build and test: `cd idt && build_idt.bat`
- [ ] Commit changes

### Step 3.4: Create `shared/progress_utils.py`
- [ ] Design API for progress tracking
- [ ] Standardized progress file writing/reading
- [ ] Background monitoring thread pattern
- [ ] Status.log update utilities
- [ ] Add comprehensive docstrings
- [ ] Add type hints
- [ ] Create unit tests in `pytest_tests/test_progress_utils.py`
- [ ] Update `idt/idt.spec` hiddenimports: `'shared.progress_utils'`
- [ ] Build and test: `cd idt && build_idt.bat`
- [ ] Commit changes

### Step 3.5: Verify All Builds
- [ ] Run `BuildAndRelease/WinBuilds/builditall_wx.bat`
- [ ] Verify all 5 executables build successfully
- [ ] Check for warnings in build logs
- [ ] Quick smoke test each executable
- [ ] Commit any spec file updates

**Phase 3 Complete:** ⬜  
**Deliverables Created:** [ ] shared/file_utils.py [ ] shared/path_utils.py [ ] shared/exif_utils.py [ ] shared/progress_utils.py [ ] Unit tests for all

---

## Phase 4: Refactor Existing Code (Est: 3-4 sessions)

**Objective:** Replace duplicate code with shared utilities

**Status:** ⬜ Not Started  
**Session Notes:** [Add notes here]

**⚠️ CRITICAL:** Test frozen build and run after EACH step in this phase

### Step 4.1: Refactor `scripts/workflow.py`
- [ ] Review current file discovery implementations
- [ ] Replace inline file discovery with `shared.file_utils`
- [ ] Build and test: `dist\idt.exe workflow testimages`
- [ ] Replace path resolution with `shared.path_utils`
- [ ] Build and test: `dist\idt.exe workflow testimages`
- [ ] Replace progress monitoring with `shared.progress_utils`
- [ ] Build and test: `dist\idt.exe workflow testimages`
- [ ] Verify workflow logs show no errors
- [ ] Run full workflow with multiple image types
- [ ] Commit changes

### Step 4.2: Refactor `scripts/image_describer.py`
- [ ] Replace EXIF operations with `shared.exif_utils`
- [ ] Build and test frozen executable
- [ ] Replace file discovery with `shared.file_utils`
- [ ] Build and test frozen executable
- [ ] Run standalone: `dist\idt.exe image_describer testimages`
- [ ] Verify descriptions are generated correctly
- [ ] Commit changes

### Step 4.3: Refactor Analysis Scripts
- [ ] Update `analysis/combine_workflow_descriptions.py`:
  - [ ] Use `shared.exif_utils` for date extraction
  - [ ] Use `shared.file_utils` for file scanning
  - [ ] Test: `dist\idt.exe combinedescriptions <workflow_dir>`
- [ ] Update `analysis/stats_analysis.py`:
  - [ ] Use `shared.file_utils`
  - [ ] Test: `dist\idt.exe stats <workflow_dir>`
- [ ] Update `analysis/content_analysis.py`:
  - [ ] Use `shared.file_utils`
  - [ ] Test: `dist\idt.exe contentreview <workflow_dir>`
- [ ] Commit changes

### Step 4.4: Refactor GUI Applications (if applicable)
- [ ] Review `imagedescriber/imagedescriber_wx.py` for opportunities
- [ ] Review `viewer/viewer_wx.py` for opportunities
- [ ] Apply shared utilities where they don't break GUI-specific logic
- [ ] Build each GUI: `build_imagedescriber_wx.bat`, `build_viewer_wx.bat`
- [ ] Test each GUI application
- [ ] Commit changes

**Phase 4 Complete:** ⬜  
**Files Refactored:** [ ] workflow.py [ ] image_describer.py [ ] Analysis scripts [ ] GUI apps

---

## Phase 5: Standardization (Est: 2 sessions)

**Objective:** Enforce consistent patterns across the codebase

**Status:** ⬜ Not Started  
**Session Notes:** [Add notes here]

### Step 5.1: Standardize Error Handling
- [ ] Document error handling patterns in `docs/CODE_STYLE_GUIDE.md`
- [ ] Create standard try/except patterns with fallbacks
- [ ] Define when to use INFO vs WARNING vs ERROR logging
- [ ] Update all scripts to follow patterns
- [ ] Build and test all executables
- [ ] Commit changes

### Step 5.2: Standardize Import Patterns
- [ ] Enforce module-level imports with try/except fallbacks
- [ ] Review all imports in `scripts/`, `analysis/`, `imagedescriber/`
- [ ] Fix any remaining `from scripts.X` patterns
- [ ] Ensure consistent handling of optional dependencies
- [ ] Build and test all executables
- [ ] Commit changes

### Step 5.3: Standardize Configuration Access
- [ ] Verify all config loading uses `config_loader.py`
- [ ] Remove any direct `open()` or `json.load()` for config files
- [ ] Standardize environment variable usage
- [ ] Document config patterns in style guide
- [ ] Build and test all executables
- [ ] Commit changes

### Step 5.4: Add Type Hints
- [ ] Add type hints to all public functions in shared utilities
- [ ] Add type hints to critical workflow functions
- [ ] Add type hints to image_describer functions
- [ ] Run mypy if available: `mypy scripts/ --ignore-missing-imports`
- [ ] Commit changes

**Phase 5 Complete:** ⬜  
**Standardization Applied:** [ ] Error handling [ ] Imports [ ] Config access [ ] Type hints

---

## Phase 6: Testing & Validation (Est: 2 sessions)

**Objective:** Verify all changes work in both dev and frozen modes

**Status:** ⬜ Not Started  
**Session Notes:** [Add notes here]

### Step 6.1: Build All Executables
- [ ] Run `BuildAndRelease/WinBuilds/builditall_wx.bat`
- [ ] Verify all 5 executables build without errors:
  - [ ] idt.exe
  - [ ] viewer.exe
  - [ ] imagedescriber.exe
  - [ ] prompteditor.exe
  - [ ] idtconfigure.exe
- [ ] Check build logs for warnings
- [ ] Document build time and any issues

### Step 6.2: Test All CLI Commands
Test each command with the frozen executable:
- [ ] `dist\idt.exe version` - Check version displays
- [ ] `dist\idt.exe workflow testimages` - Full workflow test
  - [ ] Verify exit code 0
  - [ ] Check workflow log for errors
  - [ ] Check image_describer log
  - [ ] Verify HTML output created
- [ ] `dist\idt.exe stats <workflow_dir>` - Stats analysis
- [ ] `dist\idt.exe combinedescriptions <workflow_dir>` - CSV export
- [ ] `dist\idt.exe contentreview <workflow_dir>` - Content review
- [ ] `dist\idt.exe check-models` - Model checking
- [ ] Document results for each command

### Step 6.3: Test All GUI Applications
- [ ] Launch `dist\viewer.exe`
  - [ ] Load a workflow directory
  - [ ] Verify images display
  - [ ] Test live monitoring
- [ ] Launch `dist\imagedescriber.exe`
  - [ ] Load directory of images
  - [ ] Process a few images
  - [ ] Verify descriptions generated
- [ ] Launch `dist\prompteditor.exe`
  - [ ] Open prompt editor
  - [ ] Test basic functionality
- [ ] Launch `dist\idtconfigure.exe`
  - [ ] Open configuration
  - [ ] Test basic functionality
- [ ] Document any console errors or warnings

### Step 6.4: Run Unit Tests
- [ ] Run `python run_unit_tests.py`
  - [ ] Document pass/fail counts
  - [ ] Fix any newly broken tests
- [ ] Run `pytest pytest_tests/`
  - [ ] Document coverage if available
- [ ] All tests passing: ⬜

### Step 6.5: Create Regression Test Suite
- [ ] Document test scenarios in `docs/code_audit/regression_tests.md`
- [ ] Include commands that should always work
- [ ] Include edge cases discovered during audit
- [ ] Create simple test script if possible
- [ ] Commit changes

**Phase 6 Complete:** ⬜  
**All Tests Passing:** ⬜

---

## Phase 7: Documentation (Est: 1 session)

**Objective:** Update documentation to reflect improvements

**Status:** ⬜ Not Started  
**Session Notes:** [Add notes here]

### Step 7.1: Update Architecture Documentation
- [ ] Update `docs/ARCHITECTURE.md` (create if doesn't exist)
- [ ] Document new `shared/` utilities and their purpose
- [ ] Update import patterns in `.github/copilot-instructions.md`
- [ ] Update `docs/archive/AI_AGENT_REFERENCE.md` with new patterns
- [ ] Commit changes

### Step 7.2: Create Code Style Guide
- [ ] Create `docs/CODE_STYLE_GUIDE.md`
- [ ] Document import patterns (frozen mode compatible)
- [ ] Document error handling standards
- [ ] Document frozen mode compatibility rules
- [ ] Document type hint conventions
- [ ] Commit changes

### Step 7.3: Add Inline Documentation
- [ ] Verify all shared utility functions have docstrings
- [ ] Add comments explaining PyInstaller-specific code
- [ ] Add "why" comments for non-obvious patterns
- [ ] Review critical files (workflow.py, image_describer.py) for clarity
- [ ] Commit changes

### Step 7.4: Update Project README
- [ ] Update main README.md if architecture changed significantly
- [ ] Ensure build instructions are still accurate
- [ ] Update any outdated information
- [ ] Commit changes

**Phase 7 Complete:** ⬜  
**Documentation Updated:** [ ] ARCHITECTURE.md [ ] CODE_STYLE_GUIDE.md [ ] README.md [ ] Inline docs

---

## Completion Checklist

When all phases are complete, verify:

- [ ] All 7 phases marked as ✅ Complete
- [ ] All deliverable documents created in `docs/code_audit/`
- [ ] All 5 executables build successfully
- [ ] All CLI commands tested and working
- [ ] All GUI applications tested and working
- [ ] Unit tests passing
- [ ] Documentation updated
- [ ] Code committed and pushed
- [ ] No regressions introduced (old functionality still works)

**Audit Completed:** ⬜  
**Completion Date:** [Date]

---

## Notes & Discoveries

### Blockers Encountered
[Document any blockers here as they arise]

### Key Findings
- ✅ No circular dependencies found in entire codebase (45 files checked)
- ✅ All 5 wxPython GUI apps properly share `shared/wx_common.py`
- ⚠️ Cross-directory dependency: `scripts/image_describer.py` imports from `imagedescriber/ai_providers.py`
  - Recommendation: Move ai_providers.py to shared/ directory
- ⚠️ Found 5 deprecated Qt6 files (imagedescriber, prompt_editor, idtconfigure)
  - Total ~1,500+ lines of deprecated code
  - Can be safely removed after wx version is verified stable
- ✅ Clean module design in analysis/ and models/ directories (tree structure, no circular deps)
- ⚠️ Duplicate EXIF reading logic exists in 4 different files
- ⚠️ Duplicate file discovery logic across multiple scripts

### Decisions Made
[Document architectural or refactoring decisions here]

### Follow-up Items
[Items that arose during audit but are out of scope]

---

## Session LogContinue Phase 1, Step 1.2 - Identify Duplicate Code (in next session

| Session # | Date | Phase Worked | Tasks Completed | Time Spent | Notes |
|-----------|------|--------------|-----------------|------------|-------|
| 1 | 2026-01-13 | Phase 1, Step 1.1 | Module dependency map created, all 45 Python files scanned, all 5 GUI apps documented | ~1 hour | Found no circular dependencies. Identified ai_providers.py cross-directory dependency. Documented 5 deprecated Qt6 files for removal in Phase 2. |

---

**Last Updated:** 2026-01-13  
**Next Action:** Start Phase 1, Step 1.1 (Module Dependency Map)
