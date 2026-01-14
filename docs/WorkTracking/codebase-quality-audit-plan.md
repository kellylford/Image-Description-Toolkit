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

**Status:** ✅ COMPLETE (3 of 4 steps done, Step 1.4 in progress)

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

### Step 1.4: Find All PyInstaller Concerns ⏳
- [ ] Search for problematic import patterns
- [ ] Find hardcoded paths
- [ ] Output: `docs/code_audit/pyinstaller_issues.md`

---

## Phase 2: Analysis & Prioritization (Est: 1 session)

**Objective:** Categorize findings and prioritize fixes

**Status:** ⬜ Not Started  

### Step 2.1: Categorize Issues by Severity
- [ ] Review all Phase 1 outputs
- [ ] Categorize by severity (Critical → High → Medium → Low)
- [ ] Output: `docs/code_audit/prioritized_issues.md`

---

## Session Log

| Session # | Date | Phase | Steps Completed | Time Spent | Status |
|-----------|------|-------|---|---|---|
| 1 | 2026-01-13 | Phase 1 | 1.1, 1.2, 1.3 | ~2.5 hours | Complete (1.4 ready for next session) |

---

## Key Findings from Phase 1

### Critical Issues (Fix Immediately) 🔴
- **15+ Frozen Mode Bugs:** Direct `json.load()` calls without using `config_loader`
  - Affects: viewer, tools, shared code
  - Impact: Will fail in PyInstaller executables
  - Solution: Replace with `config_loader_safe()` wrapper

### High Priority Issues ⚠️
- **EXIF Extraction:** 4 implementations (viewer, tools, analysis, metadata)
- **Filename Sanitization:** 3 implementations  
- **Window Title Builders:** 2 implementations

### Medium Priority Issues ⚠️
- **Workflow Directory Discovery:** 2 implementations (mostly centralized)
- **File Discovery Logic:** 3 implementations

---

**Last Updated:** 2026-01-13  
**Next Action:** Continue at Phase 1, Step 1.4
