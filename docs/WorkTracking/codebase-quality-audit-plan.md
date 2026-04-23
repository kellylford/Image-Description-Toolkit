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
| Phase 1: Discovery & Mapping | ✅ Complete | 1 | None |
| Phase 2: Analysis & Prioritization | ✅ Complete | 1 | None |
| Phase 3: Fix CRITICAL Config Bugs | ✅ Complete | 1 | None |
| Phase 4: Code Deduplication | 🔄 In Progress | 1 (partial) | None |
| Phase 5: Standardization | ⬜ Not Started | 0 | Phase 4 |
| Phase 6: Testing & Validation | ⬜ Not Started | 0 | Phase 5 |
| Phase 7: Documentation | ⬜ Not Started | 0 | Phase 6 |

**Legend:** ⬜ Not Started | 🔄 In Progress | ✅ Complete | ⚠️ Blocked

---

## Phase 1: Discovery & Mapping (Est: 1-2 sessions)

**Objective:** Build a complete map of the codebase structure and identify problem areas

**Status:** ✅ COMPLETE (All 4 steps done)

### Phase 1 Deliverables
- [x] dependency_map.md - Module dependencies for all 45 files
- [x] duplicate_code_report.md - 7 duplicate patterns identified
- [x] entry_points.md - All 17 CLI commands and 5 GUI apps documented
- [x] pyinstaller_issues.md - 32+ frozen mode issues documented

### Step 1.1: Create Module Dependency Map ✅
- [x] Scan all Python files across 9 directories (45 files total)
- [x] Map all imports between modules
- [x] Identify circular dependencies (NONE found)
- [x] Create detailed dependency map
- [x] Output: `docs/code_audit/dependency_map.md`

### Step 1.2: Identify Duplicate Code ✅
- [x] Search for similar functions and logic patterns
- [x] Found 7 major duplicate code patterns
- [x] Output: `docs/code_audit/duplicate_code_report.md`

### Step 1.3: Catalog All Entry Points ✅
- [x] Documented all 17 CLI commands
- [x] Documented all 5 GUI applications
- [x] Removed 4 deprecated PyQt6 files (~1,200 lines)
- [x] Output: `docs/code_audit/entry_points.md`

### Step 1.4: Find All PyInstaller Concerns ✅
- [x] Search for problematic import patterns
- [x] Find hardcoded paths and frozen mode issues
- [x] Identify config loading without config_loader (23+ instances found)
- [x] Find file path operations not handling frozen mode
- [x] Output: `docs/code_audit/pyinstaller_issues.md`
- [ ] Commit changes

---

## Phase 2: Analysis & Prioritization (Est: 1 session)

**Objective:** Categorize findings and prioritize fixes

**Status:** ✅ COMPLETE (All 3 steps done)

### Phase 2 Deliverables
- [x] prioritized_issues.md - 38+ issues categorized by severity
- [x] quick_wins.md - 4 quick wins identified and documented
- [x] implementation_roadmap.md - Detailed step-by-step guide for Phases 3-7

### Step 2.1: Categorize Issues by Severity ✅
- [x] Review all Phase 1 outputs
- [x] Categorize by severity (Critical → High → Medium → Low)
- [x] Output: `docs/code_audit/prioritized_issues.md`

---, 1.4 | ~3.5 hours | **COMPLETE** - All Phase 1 steps done!

## Session Log

| Session # | Date | Phase | Steps Completed | Time Spent | Status |
|-----------|------|-------|---|---|---|
| 1 | 2026-01-13 | Phase 1 | 1.1, 1.2, 1.3, 1.4 | ~3 hours | Complete |
| 2 | 2026-01-14 | Phase 2 | 2.1, 2.2, 2.3 | ~2.5 hours | Complete |
| 3 | 2026-01-14 | Phase 3 | 3.1, 3.2, 3.3, 3.4, 3.5, 3.6 | ~1.5 hours | Complete |
| 4 | 2026-01-14 | Phase 4 | 4.1 (complete) | ~0.75 hours | In Progress |

---

## Key Findings from Phase 1 (COMPLETE)

### Critical Issues (Fix Immediately) 🔴
1. **23+ Frozen Mode Bugs:** Direct `json.load()` calls without config_loader
   - Files: viewer_wx.py, workflow.py, workflow_utils.py, scripts, tools, metadata
   - Impact: Will crash in PyInstaller executables
   - Solution: Use `config_loader` module for all config file access

2. **4 Hardcoded Path Issues:** Assumptions about directory structure
   - Files: workers_wx.py, imagedescriber_wx.py, rename_workflows.py, others
   - Impact: May fail if paths change or in unusual deployment scenarios
   - Solution: Use config_loader or dynamic path resolution

### High Priority Issues ⚠️
- **EXIF Extraction:** 4 implementations (consolidate in Phase 3)
- **Filename Sanitization:** 3 implementations (consolidate in Phase 3)
- **Window Title Builders:** 2 implementations (consolidate in Phase 3)

### Medium Priority Issues ⚠️
- **Workflow Directory Discovery:** 2 implementations (mostly centralized)
- **File DiscoverBegin Phase 2, Step 2.1 - Categorize Issues by Severity

---

## Phase 1 Completion Summary

✅ **Phase 1 is COMPLETE** - All discovery and mapping complete

**Total Issues Found:**
- Circular dependencies: 0 ✅
- Duplicate code patterns: 7 ⚠️
- Frozen mode bugs: 23+ 🔴
- Hardcoded path issues: 4 ⚠️
- Files removed: 4 (deprecated Qt6 files)

**Ready for Phase 2:** Analysis & Prioritization

---

**Last Updated:** 2026-01-14  
**Current Phase:** Phase 4 - Code Deduplication (In Progress)  
**Next Action:** Continue Phase 4, Step 4.2 - Create shared/exif_utils.py (3 hours)

**To Resume Phase 4.2:** Say "Continue codebase quality audit plan at Phase 4, Step 4.2"
