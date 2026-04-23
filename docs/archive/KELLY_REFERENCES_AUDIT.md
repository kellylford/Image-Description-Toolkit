# Audit: "kelly" References in Codebase

**Date**: October 15, 2025  
**Purpose**: Identify all references to "kelly" in the codebase for cleanup before distribution

---

## Summary

Total matches: **113 references** to "kelly" across the codebase

### Categories:

1. ✅ **OK - GitHub Repository URLs** (49 references)
2. ⚠️ **NEEDS REVIEW - Hardcoded Paths in Code** (3 references)
3. ⚠️ **NEEDS REVIEW - Hardcoded Paths in Documentation** (5 references)
4. ✅ **OK - Example Paths in Documentation** (45+ references)
5. ✅ **OK - Personal References** (5 references)
6. ✅ **OK - Git Ignore** (1 reference)
7. ✅ **OK - Copyright/License** (1 reference)
8. ✅ **OK - AI Instructions** (1 reference)

---

## Category 1: ✅ GitHub Repository URLs (OK - Do Not Change)

These are legitimate references to the GitHub repository `kellylford/Image-Description-Toolkit`. These should **remain unchanged**.

**Files with GitHub URLs (49 total):**
- `CHANGELOG.md` (1)
- `RELEASES_README.md` (1)
- `LICENSE` (1 - copyright)
- `docs/USER_GUIDE.md` (3)
- `docs/packaging/DISTRIBUTION_CHECKLIST.md` (3)
- `imagedescriber/imagedescriber.py` (4)
- `imagedescriber/package_imagedescriber.bat` (1)
- `imagedescriber/setup_imagedescriber.bat` (2)
- `imagedescriber/dist_templates/` (6)
- `imagedescriber/USER_SETUP_GUIDE.md` (2)
- `prompt_editor/prompt_editor.py` (1)
- `prompt_editor/package_prompt_editor.bat` (1)
- `viewer/package_viewer.bat` (1)
- `tools/bootstrap.bat` (2)
- `tools/INVENTORY.md` (1)
- `tools/GITHUB_ACTIONS_BUILD.md` (2)
- `bat/README.md` (0 - but has paths)
- `docs/archive/` files (19+)

**Decision**: ✅ **KEEP ALL** - These are the correct repository URLs.

---

## Category 2: ⚠️ Hardcoded Paths in Code (NEEDS REVIEW)

These are hardcoded default paths in **executable Python code** that reference `C:\Users\kelly\`. These should be reviewed and potentially changed to relative paths or removed.

### 🔴 HIGH PRIORITY - Active Code

#### 1. `tools/analyze_workflow_naming.py` (Lines 259-260)
```python
default_hold_dir = r"C:\Users\kelly\GitHub\idt\idtexternal\idt\descriptions\hold"
default_output = r"C:\Users\kelly\GitHub\idt\workflow_naming_analysis.csv"
```

**Issue**: Hardcoded default paths in tool script  
**Used**: Yes, this is an active tool in `tools/` directory  
**Fix Required**: Change to relative paths or use user's home directory  
**Suggested Fix**:
```python
default_hold_dir = os.path.join(os.path.expanduser("~"), "idt", "descriptions", "hold")
default_output = "workflow_naming_analysis.csv"
```

#### 2. `tools/rename_workflows_with_paths.py` (Lines 299-300)
```python
default=r'C:\Users\kelly\GitHub\idt\idtexternal\idt\descriptions\hold',
help='Path to directory containing workflow directories (default: C:\\Users\\kelly\\GitHub\\idt\\idtexternal\\idt\\descriptions\\hold)'
```

**Issue**: Hardcoded default path in argparse default  
**Used**: Yes, this is an active tool  
**Fix Required**: Change to relative path or user home  
**Suggested Fix**:
```python
default=os.path.join(os.path.expanduser("~"), "idt", "descriptions", "hold"),
help='Path to directory containing workflow directories (default: ~/idt/descriptions/hold)'
```

### 🟡 MEDIUM PRIORITY - Documentation Code

#### 3. `scripts/workflow_utils.py` (Line 514)
```python
        C:\\Users\\kelly\\photos\\2025\\07 -> "2025_07"
```

**Issue**: Example path in code comment  
**Impact**: Low - it's just a docstring example  
**Fix Required**: Optional - change to generic example  
**Suggested Fix**:
```python
        C:\\Users\\username\\photos\\2025\\07 -> "2025_07"
```

---

## Category 3: ⚠️ Hardcoded Paths in Documentation (NEEDS REVIEW)

These are paths in documentation files that may confuse users if they see `kelly` in the paths.

### Documentation Files with User-Specific Paths:

#### 1. `tools/README.md` (Line 72)
```markdown
**Default directory**: `C:\Users\kelly\GitHub\idt\idtexternal\idt\descriptions\hold`
```
**Fix**: Change to generic example or explain it's user-specific

#### 2. `bat/README.md` (Lines 160, 166, 174, 182, 196)
Multiple references to `C:\Users\Kelly\GitHub\idt\bat`

**Fix**: Change to `C:\Users\<YourUsername>\GitHub\idt\bat` or similar

#### 3. `docs/WorkTracking/ANALYSIS_TOOLS_ENHANCEMENT_COMPLETE.md` (Line 6)
```markdown
- **Location:** `c:\Users\kelly\GitHub\idt\analysis\`
```
**Fix**: Change to relative path or generic example

#### 4. `docs/packaging/DISTRIBUTION_CHECKLIST.md` (Lines 27, 43, 85)
```
cd c:\Users\kelly\GitHub\idt\imagedescriber
```
**Fix**: Change to relative paths or generic `cd <toolkit-directory>`

#### 5. `instructions.md` (Line 8)
```markdown
6. Keep a running log of chat conversations in ~/your_secure_location/VSCodeAIChat.md
```
**Fix**: This is AI instruction file - probably keep as-is since it's internal

---

## Category 4: ✅ Example Paths in Archive Documentation (OK)

These are in **archived documentation** (`docs/archive/`) and serve as historical examples. Since they're archived, they're less critical to fix.

**Files**: 45+ references across:
- `BATCH_FILES_GUIDE.md` (9 examples)
- `CLOUD_PROVIDERS_GUIDE.md` (5 examples)
- `GUI_VENV_SETUP.md` (4 examples)
- `LOGGING_IMPROVEMENTS.md` (3 examples)
- `PHASE_3_*.md` files (4 examples)
- `SDK_MIGRATION_COMPLETE.md` (4 examples)
- `WORKFLOW_NAMING_ANALYSIS.md` (5 examples)
- And others...

**Decision**: ✅ **LOW PRIORITY** - These are archived historical documents. Can fix if time permits, but not critical.

---

## Category 5: ✅ Personal/Name References (OK)

These are legitimate personal name references:

1. **`docs/WorkTracking/ISSUE_SHARED_INFRASTRUCTURE.md`** (Lines 397, 402, 425)
   - "Kelly (October 12, 2025)" - conversation attribution
   - "Reporter: Kelly Ford" - issue reporter name
   - ✅ **KEEP** - These are legitimate attributions

2. **`docs/WorkTracking/SESSION_NOTES.md`** (Line 9)
   - "Kelly has determined..." - user reference
   - ✅ **KEEP** - This is fine

3. **`docs/archive/REFACTORING_COMPLETE_SUMMARY.md`** (Line 321)
   - "User: Kelly (Testing, Bug Discovery, Requirements)"
   - ✅ **KEEP** - Project history

---

## Category 6: ✅ Git Ignore (OK)

**`.gitignore` (Line 13)**:
```
tools/kelly_*.bat
```

**Purpose**: Ignores personal workflow scripts  
**Decision**: ✅ **KEEP** - This is correct; it prevents personal scripts from being committed

---

## Category 7: ✅ Copyright/License (OK)

**`LICENSE` (Line 3)**:
```
Copyright (c) 2025 kellylford
```

**Decision**: ✅ **KEEP** - This is the correct copyright holder

---

## Category 8: ✅ AI Instructions (Personal)

**`instructions.md` (Line 8)**:
```
6. Keep a running log of chat conversations in ~/your_secure_location/VSCodeAIChat.md
```

**Purpose**: Internal AI instructions for development  
**Decision**: ✅ **KEEP** - This is an internal development file, not distributed

---

## Action Items

### 🔴 HIGH PRIORITY (Must Fix Before Distribution)

1. **`tools/analyze_workflow_naming.py`** (Lines 259-260)
   - Change hardcoded paths to user-agnostic defaults
   
2. **`tools/rename_workflows_with_paths.py`** (Lines 299-300)
   - Change hardcoded paths to user-agnostic defaults

### 🟡 MEDIUM PRIORITY (Should Fix)

3. **`tools/README.md`** (Line 72)
   - Update default directory example to be generic

4. **`bat/README.md`** (Lines 160, 166, 174, 182, 196)
   - Change example paths to generic format

5. **`docs/packaging/DISTRIBUTION_CHECKLIST.md`** (Lines 27, 43, 85)
   - Use relative paths or generic placeholders

6. **`docs/WorkTracking/ANALYSIS_TOOLS_ENHANCEMENT_COMPLETE.md`** (Line 6)
   - Use relative path

### 🟢 LOW PRIORITY (Nice to Have)

7. **`scripts/workflow_utils.py`** (Line 514)
   - Update docstring example to generic username

8. **Archive documentation** (`docs/archive/*.md`)
   - Update examples if time permits
   - Not critical since these are archived

### ✅ NO ACTION NEEDED

- All GitHub repository URLs (`github.com/kellylford/...`) - **KEEP**
- Copyright and license references - **KEEP**
- Personal name attributions in work tracking - **KEEP**
- `.gitignore` entry for personal scripts - **KEEP**
- `instructions.md` AI instructions - **KEEP** (internal file)

---

## Recommended Fixes

### Fix 1: `tools/analyze_workflow_naming.py`

**Current:**
```python
default_hold_dir = r"C:\Users\kelly\GitHub\idt\idtexternal\idt\descriptions\hold"
default_output = r"C:\Users\kelly\GitHub\idt\workflow_naming_analysis.csv"
```

**Proposed:**
```python
default_hold_dir = os.path.join(os.path.expanduser("~"), "idt", "descriptions", "hold")
default_output = "workflow_naming_analysis.csv"  # Current directory
```

### Fix 2: `tools/rename_workflows_with_paths.py`

**Current:**
```python
default=r'C:\Users\kelly\GitHub\idt\idtexternal\idt\descriptions\hold',
help='Path to directory containing workflow directories (default: C:\\Users\\kelly\\GitHub\\idt\\idtexternal\\idt\\descriptions\\hold)'
```

**Proposed:**
```python
default=os.path.join(os.path.expanduser("~"), "idt", "descriptions", "hold"),
help='Path to directory containing workflow directories (default: ~/idt/descriptions/hold)'
```

### Fix 3: Documentation Examples

Replace specific paths like:
```markdown
cd C:\Users\kelly\GitHub\idt\bat
```

With generic placeholders:
```markdown
cd <INSTALL_DIR>\bat
# or
cd C:\Users\<USERNAME>\idt\bat
```

---

## Testing After Fixes

After making changes to the Python files, test:

1. **`tools/analyze_workflow_naming.py`**:
   ```bash
   python tools/analyze_workflow_naming.py --help
   # Verify default path shown is user-agnostic
   ```

2. **`tools/rename_workflows_with_paths.py`**:
   ```bash
   python tools/rename_workflows_with_paths.py --help
   # Verify default path shown is user-agnostic
   ```

3. **Verify no runtime errors** when tools run without arguments

---

## Conclusion

**Total "kelly" references: 113**
- ✅ OK to keep: ~100 references (GitHub URLs, copyright, attributions, archived docs)
- ⚠️ Need fixing: **7 references** (2 HIGH priority, 5 MEDIUM priority)

**Main concerns**:
1. Two active tools with hardcoded paths
2. A few documentation files with specific paths that might confuse users

The majority of references (GitHub URLs, copyright) are **completely appropriate and should not be changed**.
