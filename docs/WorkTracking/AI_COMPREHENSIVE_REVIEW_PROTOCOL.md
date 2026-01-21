# AI Agent Comprehensive Review Protocol
**Purpose**: Prevent incomplete refactors and ensure thorough code changes  
**Created**: January 20, 2026  
**Status**: MANDATORY for all AI agents working on IDT

## Problem Statement

During the WXMigration branch development, **multiple critical regressions** were introduced due to AI agents:
1. Renaming variables incompletely
2. Changing function signatures without updating callers
3. Moving code without updating imports
4. Not testing frozen executables before claiming "fixed"

**Result**: 23% of commits (17 of 74) were fixes for previous AI-introduced bugs.

## Root Causes

### Why AI Agents Create These Issues

1. **Pattern Matching Failures**
   - AI searches for obvious patterns (`unique_source_count`)
   - Misses variations (constructor calls, return statements, lambda functions)
   - Assumes "find and replace" catches everything

2. **Incomplete Context**
   - Reads function being changed but not all callers
   - Doesn't check related files
   - Focuses on immediate problem, not system-wide impact

3. **No Testing Protocol**
   - Claims "this should work" without running code
   - Tests in development mode, not frozen executable
   - Doesn't verify end-to-end workflows

4. **False Confidence**
   - "Looks correct" ≠ "Is correct"
   - Syntax validation ≠ Runtime validation
   - Unit tests passing ≠ Integration works

## Mandatory Review Checklist

### BEFORE Making Any Change

- [ ] **Full File Read**: Read ENTIRE file being modified (all 2400 lines if needed)
- [ ] **Find All References**: Use `list_code_usages` tool for functions/variables being changed
- [ ] **Check Callers**: Read every file that uses the code you're changing
- [ ] **Review Related Code**: Check for similar patterns elsewhere that need same fix
- [ ] **Understand Original Intent**: Why was it written this way? What will break if changed?

### DURING Code Changes

#### For Variable Renames

```bash
# MANDATORY: Search for ALL occurrences before renaming
grep -r "old_variable_name" scripts/
# Check these patterns:
# - Function parameters
# - Return statements  
# - Lambda functions
# - Dictionary keys
# - String formatting
# - Comments/docs
```

Example from real bug:
```python
# WRONG - Incomplete rename
unique_images = len(set(all_image_files))  # Defined as unique_images
...
return {"unique_images": unique_source_count}  # BUG: Returns undefined variable
```

#### For Function Signature Changes

```python
# If changing from:
def get_date(image_name: str, base_dir: Path) -> datetime:
    
# To:
def get_date(image_path: Path) -> datetime:

# MANDATORY STEPS:
# 1. Find ALL callers
list_code_usages("get_date")

# 2. Check each caller can provide new argument type
# 3. Update ALL callers or create wrapper
# 4. Test each caller after change
```

#### For Import Changes

When moving code from `scripts/module.py` to `shared/module.py`:

```python
# MANDATORY: Check PyInstaller compatibility
# Pattern 1: Try/except fallback (REQUIRED)
try:
    from shared.module import function
except ImportError:
    from scripts.module import function  # Frozen mode fallback

# Pattern 2: Module-level import (REQUIRED for large functions)
try:
    from shared.module import function
except ImportError:
    function = None  # Check before use

# NEVER use "from scripts.X" without fallback
```

### AFTER Code Changes

#### Testing Protocol (MANDATORY)

1. **Syntax Check**
   ```bash
   python -m py_compile scripts/workflow.py
   ```

2. **Development Mode Test**
   ```bash
   python scripts/workflow.py test_input --output test_output
   ```

3. **Build Frozen Executable**
   ```bash
   cd idt
   ./build_idt.bat
   ```

4. **Test Frozen Executable**
   ```bash
   dist/idt.exe workflow test_input --output test_output
   ```

5. **Verify Logs**
   ```bash
   # Check for errors in logs
   grep -i error test_output/wf_*/logs/*.log
   ```

6. **End-to-End Validation**
   - Descriptions generated?
   - HTML report created?
   - Stats correct?
   - No crashes?

#### Documentation Requirements

Update these in commit message:
```
TESTED:
✅ Built frozen exe successfully
✅ Ran test workflow: idt.exe workflow testimages --output test
✅ Verified 2 images described
✅ Checked logs: no errors
✅ HTML report generated

NOT TESTED:
❌ MacOS build (Windows only)
❌ Large dataset (>100 images)
```

## Function Refactoring Procedure

### Safe Refactoring Steps

1. **Create New Function**
   - Add new function with new signature
   - Don't touch old function yet
   ```python
   # Old function (keep for now)
   def old_func(arg1, arg2):
       return result
   
   # New function
   def new_func(arg1):
       return result
   ```

2. **Update Callers Incrementally**
   - Find all callers: `grep -r "old_func(" .`
   - Update one at a time
   - Test after each update

3. **Deprecate Old Function**
   ```python
   def old_func(arg1, arg2):
       warnings.warn("old_func deprecated, use new_func", DeprecationWarning)
       return new_func(arg1)
   ```

4. **Remove After Verification**
   - Only after all callers updated
   - Only after full test suite passes
   - Document removal in CHANGELOG

### NEVER Do This

```python
# WRONG: Refactor in place without checking callers
- def get_date(name, dir):
+ def get_date(path):  # BREAKS ALL CALLERS

# WRONG: Find/replace without testing
grep -r "old_name" | xargs sed -i 's/old_name/new_name/g'  # NO!

# WRONG: "This should work"
# Made change, looks good ✓  # NOT ACCEPTABLE
```

## Variable Scope Analysis

### Before Renaming Variables in Large Functions

Use Python AST to find all references:

```python
import ast

with open('scripts/workflow.py') as f:
    tree = ast.parse(f.read())

# Find all uses of variable
class VariableVisitor(ast.NodeVisitor):
    def __init__(self, varname):
        self.varname = varname
        self.locations = []
    
    def visit_Name(self, node):
        if node.id == self.varname:
            self.locations.append(node.lineno)

visitor = VariableVisitor('unique_images')
visitor.visit(tree)
print(f"Variable used at lines: {visitor.locations}")
```

## PyInstaller Compatibility Verification

### Checking Frozen Mode Issues

1. **Import Pattern Check**
   ```bash
   # Find dangerous imports
   grep -r "from scripts\." scripts/ analysis/ idt/
   # Each MUST have except ImportError fallback
   ```

2. **Resource Path Check**
   ```bash
   # Find hardcoded paths
   grep -r "Path(__file__)" scripts/
   # Should use get_resource_path() instead
   ```

3. **Module Availability Check**
   ```python
   # In frozen code, check before use
   if function_name is None:
       raise ImportError("Required module not available")
   ```

## Regression Detection

### Pre-Commit Checks

Run these before EVERY commit:

```bash
# 1. Undefined variable check
python -c "import ast; exec(open('scripts/workflow.py').read())"

# 2. Import validation
python scripts/workflow.py --help

# 3. Quick smoke test
python scripts/workflow.py testimages --output test --provider ollama --model moondream:latest

# 4. Frozen mode test (if code in scripts/ changed)
cd idt && ./build_idt.bat && dist/idt.exe version
```

### Automated Testing

Create `scripts/validate_changes.py`:

```python
#!/usr/bin/env python3
"""Validate code changes before commit"""
import ast
import subprocess
import sys

def check_undefined_variables(filepath):
    """Use AST to find undefined variables"""
    with open(filepath) as f:
        try:
            tree = ast.parse(f.read())
            # Analysis logic here
            return True
        except SyntaxError as e:
            print(f"Syntax error in {filepath}: {e}")
            return False

def check_imports(filepath):
    """Verify all imports have fallbacks"""
    with open(filepath) as f:
        content = f.read()
        # Check for "from scripts." without try/except
        # Return False if found

def check_frozen_mode():
    """Build and test frozen executable"""
    result = subprocess.run(['idt/build_idt.bat'], capture_output=True)
    if result.returncode != 0:
        print("Build failed!")
        return False
    
    result = subprocess.run(['idt/dist/idt.exe', 'version'], capture_output=True)
    return result.returncode == 0

if __name__ == '__main__':
    all_pass = True
    all_pass &= check_undefined_variables('scripts/workflow.py')
    all_pass &= check_imports('scripts/workflow.py')
    all_pass &= check_frozen_mode()
    
    sys.exit(0 if all_pass else 1)
```

## Communication Guidelines

### What AI Should Say

❌ **WRONG**:
- "This should work now"
- "The fix looks correct"
- "I've updated the code"

✅ **CORRECT**:
- "TESTED: Built exe, ran workflow, verified 10 images described, no errors in logs"
- "NOT TESTED: MacOS build, large datasets >100 images"
- "CHANGED: 5 files modified, searched for 'function_name' in 23 files, updated 8 callers"

### Required Information in Responses

Every code change must include:

1. **What Changed**
   - Files modified
   - Functions/variables renamed
   - Number of locations updated

2. **Verification Performed**
   - ✅ Code compiles
   - ✅ Unit tests pass
   - ✅ Integration test run
   - ✅ Frozen exe built and tested
   
3. **Known Limitations**
   - What wasn't tested
   - Platform-specific issues
   - Edge cases not covered

## Review Cadence

### When to Do Full Review

- **Every commit**: Quick validation (syntax, imports, undefined vars)
- **Before build**: Frozen executable test
- **Before release**: Full integration test suite
- **After AI session**: Human review of all changes

### Red Flags for Human Review

Alert user if:
- Function signature changed
- Variable renamed in function >500 lines
- Import pattern changed
- >50 lines modified in single commit
- Test results show new errors
- Frozen build fails

## Recovery Protocol

### When You Find a Regression

1. **Stop Immediately**
   - Don't make more changes
   - Document the regression

2. **Root Cause Analysis**
   ```
   What broke:
   Why it broke:
   When it broke (git log):
   Impact:
   Related issues:
   ```

3. **Comprehensive Fix**
   - Fix the immediate bug
   - Search for similar bugs
   - Add test to prevent recurrence
   - Update this protocol

4. **Verification**
   - Test the fix
   - Test related code
   - Build frozen exe
   - Run full workflow

## Success Metrics

Track these for each AI session:

- **Changes Made**: Files/functions/lines
- **Testing**: Dev mode + Frozen mode + Integration
- **Regressions**: Bugs introduced this session
- **Fix Rate**: % of commits that are fixes
- **Coverage**: % of callers updated when changing function

**Target**:
- Fix Rate < 5% (current: 23% ❌)
- All changes tested in frozen mode
- Zero incomplete refactors

## Examples from Real Bugs

### Bug 1: unique_source_count

**What Happened**:
```python
# Commit 03cd2b3 - Renamed variable incompletely
unique_images = len(set(all_image_files))  # Line 1635
...
return {"unique_images": unique_source_count}  # Line 2042 - BUG!
```

**Should Have Done**:
```bash
# 1. Search for ALL occurrences
grep -rn "unique_images\|unique_source" scripts/workflow.py

# 2. Check return statements specifically
grep -n "return.*unique" scripts/workflow.py

# 3. Verify with AST analysis
python -c "import ast; ..."  # Find all Name nodes

# 4. Test frozen exe
cd idt && ./build_idt.bat && dist/idt.exe workflow test
```

### Bug 2: get_image_date_for_sorting

**What Happened**:
```python
# Old signature (2 args)
def get_image_date_for_sorting(image_name: str, base_dir: Path):
    
# Moved to shared.exif_utils with new signature (1 arg)
def get_image_date_for_sorting(image_path: Path):

# But callers still use old signature
get_image_date_for_sorting(image_name, base_dir)  # CRASH!
```

**Should Have Done**:
```bash
# 1. Find all callers BEFORE changing signature
grep -r "get_image_date_for_sorting(" .

# 2. Create bridge/wrapper for backward compatibility
def get_image_date_for_sorting(image_name, base_dir):
    image_path = find_image(image_name, base_dir)
    return _shared_get_image_date(image_path)

# 3. Update callers one at a time, testing each
# 4. Only remove wrapper after ALL callers updated
```

### Bug 3: Viewer Keyboard Navigation

**What Happened**:
```python
# Created widget but forgot to add to layout
self.desc_list = DescriptionListBox(...)
# Missing: left_sizer.Add(self.desc_list, ...)

# Also forgot event binding
# Missing: self.desc_list.Bind(wx.EVT_LISTBOX, ...)
```

**Should Have Done**:
```python
# Complete integration in single commit:
self.desc_list = DescriptionListBox(...)
self.desc_list.Bind(wx.EVT_LISTBOX, self.on_select)  # ✅
left_sizer.Add(self.desc_list, 1, wx.EXPAND)  # ✅

# Then test:
# 1. Run app
# 2. Press Tab - does focus reach listbox?
# 3. Press arrow keys - does selection change?
# 4. Build exe and test again
```

## Conclusion

**The goal is not to avoid mistakes entirely** - it's to:
1. Catch them before they reach production
2. Learn from each mistake
3. Prevent the same mistake twice

**Every AI agent must**:
- Read this document before starting
- Follow the checklists
- Test thoroughly
- Document limitations
- Ask for human review when uncertain

**Remember**: "Works in dev mode" ≠ "Works in production"
