# sys.path Import Verification - All Apps

## Date: 2026-01-09

## Status: ✅ ALL APPS VERIFIED

All wxPython applications have proper sys.path setup to import shared modules.

### Files with sys.path Setup (7 files)

#### Main App Files (4 files)
1. ✅ `viewer/viewer_wx.py` - Lines 29-32
2. ✅ `prompt_editor/prompt_editor_wx.py` - Lines 39-42
3. ✅ `idtconfigure/idtconfigure_wx.py` - Lines 30-33
4. ✅ `imagedescriber/imagedescriber_wx.py` - Lines 30-37

#### ImageDescriber Support Modules (3 files)
5. ✅ `imagedescriber/dialogs_wx.py` - Lines 14-17
6. ✅ `imagedescriber/workers_wx.py` - Lines 19-22
7. ✅ `imagedescriber/ai_providers.py` - Lines 18-21

### Standard Pattern Used

```python
# Add project root to sys.path for shared module imports
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
```

### Import Testing Results

```bash
✅ viewer imports OK
✅ prompt_editor imports OK
✅ idtconfigure imports OK
✅ imagedescriber (all 4 modules) imports OK
```

### Why This Matters

**Problem**: Relative imports fail when:
- Running from different directories
- Building frozen executables with PyInstaller
- Support modules need to import from parent (shared/)

**Solution**: Every Python file that imports from a parent directory needs to set up sys.path **independently**. Don't rely on the entry point doing it.

### Build Verification

When building executables, verify:
1. ✅ All .spec files include hiddenimports for shared.wx_common
2. ✅ All .spec files bundle shared/ directory as data
3. ✅ Test frozen executable launches without ModuleNotFoundError

### Reference

See session summary: `docs/worktracking/2026-01-09-session-summary.md` Part 5 for details on why support modules need their own sys.path setup.
