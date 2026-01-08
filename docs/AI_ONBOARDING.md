# AI Agent Onboarding - Image Description Toolkit (wxPython Port)

**Last Updated**: 2026-01-08  
**Branch**: MacApp  
**Commit**: 5a08130 (Complete wxPython migration with accessibility fixes)

---

## Critical Status: Apps Not Loading Consistently

### Current Problem
The graphical applications are not loading reliably after builds. User frustration level is HIGH.

**Known Issues**:
1. ❌ Viewer.app - **CRITICAL BUG FIXED** but .app needs rebuild testing
   - Line 920 syntax error (`elif_stripped` typo) - **FIXED in source code**
   - .app bundle was rebuilt with fix (build in progress at session end)
   - Needs full user testing to confirm workflow loading works

2. ❌ ImageDescriber.app - needs testing
   - Built with all fixes (shared module imports, accessibility API fixes)
   - Missing update_window_title() method added
   - .app bundle ready but not tested by user

3. ❓ PromptEditor.app - not tested
4. ❓ IDTConfigure.app - not tested
5. ✅ `idt` command - works globally from any directory

### What Works (Verified)
- ✅ ImageDescriber in **development mode**: `python imagedescriber/imagedescriber_wx.py`
- ✅ Viewer in **development mode**: `python viewer/viewer_wx.py`
- ✅ idt CLI tool: Works globally via ~/.zshrc PATH entry

### What Might Be Broken
- ❌ .app bundles may have stale code or build issues
- ❌ Path resolution in frozen .app vs development mode
- ❌ Module imports in frozen executables (PyInstaller bundling)

---

## Session Context

### What We Accomplished (2026-01-08)

**Phase 1: Disk Space Crisis** ✅
- User's disk was 99% full (143MB free out of 926GB)
- Freed space, installed wxPython 4.2.4 in main `.venv`

**Phase 2: ImageDescriber Fixes** ✅
```python
# Fixed module imports (imagedescriber/imagedescriber_wx.py lines 31-35)
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# Fixed wxPython API differences (removed invalid calls)
# BEFORE:
label.SetAccessibleName("Images list")  # ❌ Doesn't exist in wxPython

# AFTER:
self.image_list = wx.ListBox(panel, name="Images in workspace", ...)  # ✅

# Added missing method (lines 223-230)
def update_window_title(self, app_name, document_name):
    if self.is_modified():
        title = f"{app_name} - {document_name} *"
    else:
        title = f"{app_name} - {document_name}"
    self.SetTitle(title)
```

**Phase 3: Viewer Fixes** ✅
```python
# Fixed Path vs string type mismatch (viewer/viewer_wx.py line 198)
# BEFORE:
workflows = find_workflow_directories(str(dir_path))  # ❌ Converts Path → str

# AFTER:
workflows = find_workflow_directories(dir_path)  # ✅ Pass Path directly

# Removed hardcoded Desktop path (lines 176-181)
# BEFORE:
if not default_dir:
    default_dir = str(Path.home() / "Desktop" / "Descriptions")
self.load_workflows(default_dir)

# AFTER:
if default_dir:
    self.load_workflows(default_dir)
else:
    wx.CallAfter(self.on_browse, None)  # Show directory picker
```

**Phase 4: CRITICAL Parser Bug Discovery** ✅
```python
# THE BUG - viewer/viewer_wx.py line 920 (FIXED)
# BEFORE:
elif_stripped = line.strip()  # ❌ TYPO - invalid variable name

# AFTER:
line_stripped = line.strip()  # ✅ CORRECT

# Impact: This syntax error prevented ALL description parsing in Viewer
# Also removed duplicate parsing code (lines 910-920 duplicated at 927-947)
```

**Phase 5: Rebuild Applications** ✅
- ImageDescriber.app: Built with all fixes
- Viewer.app: **Build completed with line 920 fix** (needs testing)

---

## Architecture Overview

### 5 Applications Structure

```
Image-Description-Toolkit/
├── idt/                    # CLI dispatcher
│   ├── idt_cli.py         # Main CLI entry point
│   ├── build_idt.sh       # Build script
│   └── idt.spec           # PyInstaller spec
│
├── viewer/                 # Workflow browser GUI
│   ├── viewer_wx.py       # Main wxPython app (1230 lines)
│   ├── build_viewer_wx.sh
│   └── viewer_wx.spec
│
├── imagedescriber/        # Batch processing GUI
│   ├── imagedescriber_wx.py   # Main frame (883 lines)
│   ├── dialogs_wx.py          # Dialog windows
│   ├── workers_wx.py          # Threading for AI processing
│   ├── build_imagedescriber_wx.sh
│   └── imagedescriber_wx.spec
│
├── prompt_editor/         # Prompt template editor
│   ├── prompt_editor_wx.py
│   ├── build_prompt_editor_wx.sh
│   └── prompt_editor_wx.spec
│
├── idtconfigure/          # Configuration manager
│   ├── idtconfigure_wx.py
│   ├── build_idtconfigure_wx.sh
│   └── idtconfigure_wx.spec
│
└── shared/                # Common utilities (NEW)
    ├── __init__.py
    └── wx_common.py       # Path resolution, dialogs, config management
```

### Key Files for AI Processing
```
scripts/
├── workflow.py               # Orchestrates 4-step process (2468 lines)
├── image_describer.py        # AI description generation
├── video_frame_extractor.py  # Extract frames from videos
├── ConvertImage.py           # HEIC → JPG conversion
├── descriptions_to_html.py   # HTML report generation
└── list_results.py           # Workflow scanning utilities

models/
├── model_registry.py         # Central model metadata
└── provider_configs.py       # Provider capabilities

imagedescriber/
├── ai_providers.py           # Multi-provider abstraction
└── data_models.py            # Shared data structures
```

---

## Build System

### Development Mode (Python Scripts)
```bash
# Activate main environment
source .venv/bin/activate

# Run apps directly
python viewer/viewer_wx.py
python imagedescriber/imagedescriber_wx.py
python prompt_editor/prompt_editor_wx.py

# Run idt CLI
python idt/idt_cli.py version
```

### Production Mode (.app Bundles)
```bash
# Build individual apps
cd viewer && ./build_viewer_wx.sh
cd imagedescriber && ./build_imagedescriber_wx.sh

# Build all apps
./BuildAndRelease/builditall_wx.sh

# Run built apps
open viewer/dist/Viewer.app
open imagedescriber/dist/ImageDescriber.app

# Use idt globally (installed via install_idt_macos.sh)
idt version
idt workflow --help
```

### Path Resolution Pattern
All apps use **shared/wx_common.py** for consistent path finding:

```python
from shared.wx_common import (
    get_base_directory,      # Handles frozen vs dev mode
    find_config_file,        # Multi-location search
    find_scripts_directory,  # Locate bundled scripts
)

# Usage example
config_file = find_config_file('image_describer_config.json')
# Searches: scripts/, base/, cwd/, PyInstaller temp dir
```

---

## Critical Bugs Fixed This Session

### 1. Line 920 Parser Bug (Viewer)
**File**: `viewer/viewer_wx.py`  
**Impact**: **ALL** description parsing failed silently  
**Fix**: Changed `elif_stripped = line.strip()` → `line_stripped = line.strip()`  
**Status**: ✅ Fixed in source, Viewer.app rebuilt

### 2. Path Type Mismatch (Viewer)
**File**: `viewer/viewer_wx.py` line 198  
**Impact**: `AttributeError: 'str' object has no attribute 'exists'`  
**Fix**: Pass Path objects directly, don't convert to string  
**Status**: ✅ Fixed

### 3. wxPython API Differences (ImageDescriber)
**File**: `imagedescriber/imagedescriber_wx.py`  
**Impact**: App crashed on launch  
**Fix**: Removed `SetAccessibleName()` calls, use `name=` parameter instead  
**Status**: ✅ Fixed

### 4. Module Import Errors (Both Apps)
**Files**: `viewer/viewer_wx.py`, `imagedescriber/imagedescriber_wx.py`  
**Impact**: `ModuleNotFoundError: No module named 'shared'`  
**Fix**: Added project root to sys.path at module load  
**Status**: ✅ Fixed

### 5. Hardcoded Desktop Path (Viewer)
**File**: `viewer/viewer_wx.py` lines 176-181  
**Impact**: Ignored user's actual directory selection  
**Fix**: Show browse dialog instead of assuming Desktop  
**Status**: ✅ Fixed

---

## Testing Checklist for Next Session

### Immediate Tests (High Priority)
- [ ] **Test Viewer.app with fixed parser** - Load valid workflow and verify descriptions load
- [ ] **Test ImageDescriber.app** - Launch and verify no crashes
- [ ] Verify workflow directory structure detection works
- [ ] Test description file parsing with real data
- [ ] Confirm image previews load correctly

### Workflow Tests (Medium Priority)
- [ ] **Browse Workflows dialog** - Select and open workflows
- [ ] **Live monitoring mode** - Watch for new descriptions
- [ ] **Copy functions** - Copy description, path, image to clipboard
- [ ] **Redescribe features** - Single image and full workflow

### Integration Tests (Medium Priority)
- [ ] Run idt workflow command from terminal
- [ ] Verify config file loading in frozen apps
- [ ] Test video frame extraction
- [ ] Test HEIC conversion

### Build System (Lower Priority)
- [ ] Test PromptEditor.app
- [ ] Test IDTConfigure.app
- [ ] Verify all .app bundles launch without errors
- [ ] Test install script (install_idt_macos.sh)

---

## Known Working vs Broken

### ✅ Verified Working
- Development mode for Viewer and ImageDescriber
- idt CLI command (globally accessible)
- Workflow directory scanning (list_results.py)
- Description file parsing (with line 920 fix)
- Path resolution in frozen mode (via shared library)

### ❌ Known Broken / Untested
- .app bundles not fully tested
- Redescribe functionality (needs AI provider integration)
- Video extraction in GUI apps
- Live monitoring thread reliability
- Export functionality

### ⚠️ Potential Issues
- PyInstaller bundling might miss some modules
- Config file paths in frozen mode may fail
- Image preview loading might fail for some formats
- API key handling for cloud providers

---

## User Feedback Patterns

### High Frustration Points
1. **"What a fucking joke!"** - Apps broken at fundamental level after migration
2. **"Nice fucking work AI"** - Sarcasm when app hangs immediately
3. **"What the fuck is so hard about this"** - Viewer not loading descriptions despite valid directory
4. **"Why is anything hard coded about my desktop"** - Complained about hardcoded paths

### User Expectations
- "Comprehensive migration, not corner cutting"
- Apps should work when pointing to valid directories
- No assumptions about file locations
- Professional quality, tested code
- Fix root causes, not symptoms

---

## Next Steps for AI Agent

### Immediate Actions (Do First)
1. **Test Viewer.app** - Load a valid workflow and verify line 920 fix works
2. **Test ImageDescriber.app** - Launch and verify no crashes
3. **Check build logs** - Look for PyInstaller warnings about missing imports
4. **Verify workflow structure** - Confirm description file paths match expectations

### If Apps Still Broken
1. **Run in development mode** - Verify source code works
2. **Check sys.path in frozen mode** - Print paths at startup
3. **Verify PyInstaller spec files** - Ensure all modules are bundled
4. **Test path resolution** - Use get_base_directory() and find_config_file()
5. **Check for missing imports** - Add to hiddenimports in .spec files

### Code Quality Priorities
1. **No shortcuts** - Scan files completely, don't duplicate code
2. **Test before claiming complete** - BUILD and RUN the executable
3. **Check ALL usages** - Search for duplicate implementations
4. **Comprehensive impact analysis** - Find related code that depends on changes

---

## File Locations Reference

### Configuration Files
```
scripts/image_describer_config.json    # Prompt templates, model settings
scripts/workflow_config.json           # Workflow orchestration settings
```

### Build Outputs
```
viewer/dist/Viewer.app                 # Viewer GUI bundle
imagedescriber/dist/ImageDescriber.app # ImageDescriber GUI bundle
idt/dist/idt                          # CLI executable
```

### Shared Code
```
shared/wx_common.py                    # Path resolution, dialogs, config
imagedescriber/ai_providers.py         # Multi-provider AI abstraction
imagedescriber/data_models.py          # ImageDescription, ImageItem, ImageWorkspace
```

### Workflow Structure
```
wf_YYYY-MM-DD_HHMMSS_{model}_{prompt}/
├── descriptions/
│   └── image_descriptions.txt        # Parsed by viewer
├── input_images/
├── workflow_metadata.json
└── [other outputs]
```

---

## Build Command Reference

```bash
# Build Viewer
cd viewer && source .venv/bin/activate && pyinstaller viewer_wx.spec --clean --noconfirm

# Build ImageDescriber
cd imagedescriber && source .venv/bin/activate && pyinstaller imagedescriber_wx.spec --clean --noconfirm

# Build all apps
./BuildAndRelease/builditall_wx.sh

# Install idt globally
./install_idt_macos.sh
# Choose option 3 (add to PATH in ~/.zshrc)
```

---

## Debug Commands

```bash
# Test in development mode
python viewer/viewer_wx.py
python imagedescriber/imagedescriber_wx.py

# Check if .app exists
test -f viewer/dist/Viewer.app/Contents/MacOS/Viewer && echo "EXISTS" || echo "MISSING"

# Run .app from terminal (see errors)
./viewer/dist/Viewer.app/Contents/MacOS/Viewer

# Check Python environment
source .venv/bin/activate && pip list | grep -i wx

# Verify project structure
ls -la shared/
ls -la imagedescriber/*.py
```

---

## Remember

1. **Development mode works** - Source code is correct
2. **PyInstaller may lag** - .app bundles need rebuild after every code change
3. **Test, don't assume** - Build and run the executable, don't just fix syntax
4. **User is frustrated** - Multiple rebuilds haven't fixed issues, be thorough
5. **Line 920 was THE bug** - But .app needs testing to confirm fix works in frozen mode

---

## Session Summary Location

Full detailed session notes: [docs/WorkTracking/2026-01-08-session-summary.md](WorkTracking/2026-01-08-session-summary.md)
