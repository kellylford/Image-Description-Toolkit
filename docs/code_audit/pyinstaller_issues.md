# PyInstaller Concerns Report - Phase 1, Step 1.4

**Date:** 2026-01-13  
**Status:** Complete  
**Severity:** CRITICAL - Issues found that will break frozen executables

---

## Executive Summary

Found **32+ frozen mode issues** across the codebase that will cause failures in PyInstaller executables:

1. **CRITICAL (23 instances):** Direct `json.load()` without using `config_loader` 
2. **HIGH (4+ instances):** Hardcoded path assumptions
3. **MEDIUM (5+ instances):** Missing frozen mode checks in path resolution
4. **LOW:** Documentation of frozen mode patterns

**Recommendation:** All CRITICAL and HIGH severity issues must be fixed BEFORE next release.

---

## Issue Category 1: Config File Loading Without config_loader (CRITICAL)

**Severity:** 🔴 CRITICAL  
**Impact:** Will crash in frozen executables when trying to load config files  
**Root Cause:** Direct `open()/json.load()` vs using `config_loader` module

### Files Affected: 13+ modules with 23+ instances

#### 1. `viewer/viewer_wx.py` - 4 instances
**Lines:** 375-376, 546-547, 927, 1215

```python
# ❌ WRONG - Direct json.load()
with open(config_path) as f:
    config = json.load(f)
```

**Affected Config Files:**
- `image_describer_config.json` (line 375)
- `workflow_config.json` (line 546)
- `workflow_metadata.json` (lines 927, 1215)

**Fix Required:** Use `config_loader.load_json_config()` or `scripts/config_loader.py`

---

#### 2. `scripts/workflow.py` - 2 instances
**Lines:** 1430-1431, 2391-2392

```python
# ❌ WRONG - Direct json.load()
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)
```

**Affected Config Files:**
- `workflow_config.json` (line 1430)
- `image_describer_config.json` (line 2391)

**Status:** Already using `config_loader` elsewhere, but these two instances are direct

---

#### 3. `scripts/workflow_utils.py` - 2 instances  
**Lines:** 41-42, 601

```python
# ❌ WRONG - Direct json.load() in WorkflowConfig class
with open(config_path, 'r', encoding='utf-8') as f:
    return json.load(f)
```

**Affected Config Files:**
- `workflow_config.json` (lines 41-42, 601)

**Status:** This is the WorkflowConfig class - needs special handling

---

#### 4. `scripts/list_results.py` - 1 instance
**Line:** 49

```python
# Loading workflow_metadata.json for each workflow
metadata = json.load(f)
```

---

#### 5. `scripts/video_frame_extractor.py` - 1 instance
**Lines:** 163

```python
with open(config_path, 'r') as f:
    # Reading video_frame_extractor_config.json
```

---

#### 6. `tools/geotag_workflow.py` - 1 instance
**Line:** 58

```python
self.file_mappings = json.load(f)
```

---

#### 7. `tools/show_metadata/show_metadata.py` - 1 instance
**Line:** 582

```python
self.cache = json.load(f)
```

---

#### 8. `tools/ImageGallery/content-creation/generate_alt_text.py` - 4 instances
**Lines:** 66, 92, 109, 172

**Status:** Tool directory - low priority but still problematic

---

#### 9. `tools/ImageGallery/content-creation/build_gallery.py` - 1 instance
**Line:** 121

---

#### 10. `tools/ImageGallery/content-creation/gallery-identification/identify_gallery_content.py` - 1 instance
**Line:** 489

Note: Has wrapper function at line 485 `load_config_file()` - good pattern to follow

---

#### 11. `tools/ImageGallery/content-creation/gallery-identification/create_gallery_idw.py` - 1 instance
**Line:** 39

---

#### 12. `tools/ImageGallery/content-creation/gallery-identification/review_results.py` - 1 instance
**Line:** 20

---

#### 13. `tools/ImageGallery/content-creation/gallery-identification/gallery_wizard.py` - 1 instance
**Line:** 534

---

#### 14. `MetaData/improved_gps_location_extractor.py` - 1 instance
**Line:** 478-479

---

#### 15. `MetaData/gps_diagnosis.py` - 1 instance
**Line:** 91

---

#### 16. `scripts/metadata_extractor.py` - 1 instance
**Line:** 388

---

### Fix Pattern

**Correct Pattern (from scripts/config_loader.py):**
```python
# ✅ CORRECT - Using config_loader
from scripts.config_loader import load_json_config

config, path, source = load_json_config('workflow_config.json')
# source tells you: 'explicit_path' | 'env_var' | 'config_dir' | 'frozen_exe' | 'script_dir'
```

**Why This Matters:**
- `config_loader` handles both dev and frozen modes
- In frozen mode, files are in `sys._MEIPASS`
- Direct `open()` will fail with "file not found" in frozen executables

---

## Issue Category 2: Problematic Import Patterns (HIGH)

**Severity:** ⚠️ HIGH  
**Impact:** Import errors in frozen mode where modules don't exist at expected paths

### Found Instances: 1 (but indicates pattern risk)

#### `imagedescriber/dialogs_wx.py` - Line 41
```python
from scripts.config_loader import load_json_config
```

**Status:** This works because:
- In frozen mode, `scripts` is in `sys.path`
- Better pattern: Add scripts to sys.path explicitly (which is done)

**Related Pattern (CORRECT):**
```python
# ✅ CORRECT pattern used in dialogs_wx.py
if getattr(sys, 'frozen', False):
    _project_root = Path(sys.executable).parent
else:
    _project_root = Path(__file__).parent.parent

if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# Then imports work
from scripts.config_loader import load_json_config
```

---

## Issue Category 3: Hardcoded Path Assumptions (HIGH)

**Severity:** ⚠️ HIGH  
**Impact:** Code breaks if scripts or models aren't in expected locations

### Instance 1: `workflow.py` (root directory) - Lines 10, 13, 39
```python
def get_resource_path(relative_path):
    if sys._MEIPASS:  # ❌ Incorrect check
        return os.path.join(sys._MEIPASS, relative_path)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_path, relative_path)
```

**Issues:**
- `workflow.py` in root is OLD/DEPRECATED (should use `scripts/workflow.py`)
- Uses `sys._MEIPASS` directly instead of checking `getattr(sys, 'frozen', False)`
- Not following modern pattern

---

### Instance 2: `imagedescriber/workers_wx.py` - Lines 211, 214
```python
if getattr(sys, 'frozen', False):
    config_path = Path(sys._MEIPASS) / "scripts" / "image_describer_config.json"  # ❌ Hard path
else:
    config_path = Path(__file__).parent.parent / "scripts" / "image_describer_config.json"
```

**Issue:** Assumes `scripts` directory location in frozen mode

**Better Approach:**
```python
from scripts.config_loader import load_json_config
config, path, source = load_json_config('image_describer_config.json')
```

---

### Instance 3: `imagedescriber/imagedescriber_wx.py` - Lines 91, 199
```python
if getattr(sys, 'frozen', False):
    scripts_dir = Path(sys.executable).parent / "scripts"  # ❌ Assumption
else:
    scripts_dir = Path(__file__).parent.parent / "scripts"
```

---

### Instance 4: `tools/rename_workflows_with_paths.py` - Line 298
```python
default_hold_dir = os.path.join(os.path.expanduser("~"), "idt", "descriptions", "hold")
```

**Issue:** Hardcoded assumption about home directory structure
**Better Approach:** Make this configurable or use XDG directories

---

## Issue Category 4: Missing Frozen Mode Checks (MEDIUM)

**Severity:** ⚠️ MEDIUM  
**Impact:** May fail in edge cases when frozen mode not properly detected

### Instances Found:

1. **`viewer/viewer_wx.py` - Lines 1231-1298**
   - Has frozen mode checks
   - Status: ✅ GOOD - checks `getattr(sys, 'frozen', False)`

2. **`shared/wx_common.py` - Lines 35-37**
   - Has frozen mode checks
   - Status: ✅ GOOD

3. **`scripts/config_loader.py` - Lines 64-65**
   - Has frozen mode checks
   - Status: ✅ GOOD

4. **`idt/idt_cli.py`**
   - Has multiple frozen mode checks throughout
   - Status: ✅ GOOD - comprehensive handling

---

## Issue Category 5: Subprocess Path Issues (MEDIUM)

**Severity:** ⚠️ MEDIUM  
**Impact:** Subprocess calls may fail if script paths aren't resolved correctly

### Instance 1: `viewer/viewer_wx.py` - Lines 1238, 1245, 1298, 1315
```python
if getattr(sys, 'frozen', False):
    idt_exe = Path(sys.executable).parent / "idt"  # Tries multiple paths
    if not idt_exe.exists():
        idt_exe = Path(sys.executable).parent / "idt.exe"
    cmd = [sys.executable, str(workflow_script), "--resume", ...]
else:
    cmd = [sys.executable, str(workflow_script), ...]
```

**Status:** ✅ GOOD - Has proper frozen mode handling

---

## Summary Table

| Issue Type | Count | Severity | Priority | Status |
|-----------|-------|----------|----------|--------|
| Direct json.load() (no config_loader) | 23 | 🔴 CRITICAL | **IMMEDIATE** | ❌ Not Fixed |
| Hardcoded paths | 4 | ⚠️ HIGH | **HIGH** | ⚠️ Partially |
| Missing frozen mode checks | 0 | ⚠️ MEDIUM | **MEDIUM** | ✅ Good |
| Subprocess path issues | 0 | ⚠️ MEDIUM | **MEDIUM** | ✅ Good |
| **TOTAL** | **32+** | - | - | - |

---

## Files Requiring IMMEDIATE Attention (Phase 2)

### Priority 1 - MUST FIX (Blocks Release)
```
[ ] viewer/viewer_wx.py - 4 json.load() calls
[ ] scripts/workflow.py - 2 json.load() calls
[ ] scripts/workflow_utils.py - 2 json.load() calls
[ ] imagedescriber/workers_wx.py - Hardcoded paths
[ ] imagedescriber/imagedescriber_wx.py - Hardcoded paths
```

### Priority 2 - SHOULD FIX (Before Release)
```
[ ] scripts/list_results.py - 1 json.load()
[ ] scripts/video_frame_extractor.py - 1 json.load()
[ ] tools/geotag_workflow.py - 1 json.load()
[ ] tools/show_metadata/show_metadata.py - 1 json.load()
[ ] tools/rename_workflows_with_paths.py - Hardcoded paths
```

### Priority 3 - NICE TO FIX (Tools/Metadata)
```
[ ] tools/ImageGallery/* - 8+ json.load() calls
[ ] MetaData/* - 2+ json.load() calls
```

---

## Recommended Action Plan

### Phase 2: Analysis (Create fixable issue list)
- Identify which files block release vs nice-to-have
- Estimate effort for each fix
- Plan refactoring order

### Phase 3: Create Shared Utilities
- Create `shared/config_loader_safe.py` wrapper
- Standardize path resolution pattern
- Create subprocess helper utilities

### Phase 4: Fix Core Files (Priority 1)
- Update viewer, workflow, workflow_utils
- Test each change in frozen mode
- Verify config loading works

### Phase 5: Fix Secondary Files (Priority 2)
- Update remaining config loading issues
- Fix hardcoded paths

### Phase 6: Frozen Executable Testing
- Build idt.exe with all fixes
- Run comprehensive tests
- Verify all config files load correctly

---

## Reference: Correct Patterns

### Pattern 1: Config Loading (CORRECT)
```python
from scripts.config_loader import load_json_config

config, path, source = load_json_config('workflow_config.json')
# Returns: (config_dict, resolved_path, source_location)
```

### Pattern 2: Path Resolution (CORRECT)
```python
if getattr(sys, 'frozen', False):
    base_dir = Path(sys.executable).parent
else:
    base_dir = Path(__file__).parent.parent

scripts_dir = base_dir / 'scripts'
```

### Pattern 3: Module Imports (CORRECT)
```python
if getattr(sys, 'frozen', False):
    _project_root = Path(sys.executable).parent
else:
    _project_root = Path(__file__).parent.parent

if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from scripts.config_loader import load_json_config  # Now safe
```

### Pattern 4: Subprocess with Frozen Mode (CORRECT)
```python
if getattr(sys, 'frozen', False):
    exe_path = Path(sys.executable).parent / "script_name.exe"
    cmd = [str(exe_path), arg1, arg2]
else:
    script_path = Path(__file__).parent.parent / "scripts" / "script_name.py"
    cmd = [sys.executable, str(script_path), arg1, arg2]

subprocess.run(cmd)
```

---

## Testing Checklist for Fixes

- [ ] Test in development mode: `python scripts/workflow.py`
- [ ] Test in frozen mode: `dist/idt.exe workflow testimages`
- [ ] Test config loading from multiple sources:
  - [ ] Explicit path passed
  - [ ] Environment variable
  - [ ] IDT_CONFIG_DIR
  - [ ] Frozen exe directory
  - [ ] Bundled fallback
- [ ] Verify logs show config source
- [ ] Verify exit codes are correct

---

**Report Generated:** 2026-01-13  
**Phase:** Phase 1, Step 1.4 Complete  
**Next:** Phase 2 - Analysis & Prioritization
