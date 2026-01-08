# Full wxPython Migration - Comprehensive Analysis
**Date:** January 8, 2026
**Scope:** Complete migration to wxPython with project restructuring

## Executive Summary

This analysis covers:
1. ImageDescriber architecture (10,524 lines - most complex app)
2. Shared library opportunities across all apps
3. Project restructuring plan (idt CLI consolidation)
4. Build script updates needed
5. Path dependency mapping

---

## 1. ImageDescriber Architecture Analysis

### File Statistics
- **Total Lines:** 10,524
- **Imports:** 80+ lines
- **Classes:** 20 classes
- **Threading:** 5 QThread workers
- **Dialogs:** 8 dialog classes
- **Main Window:** 1 (ImageDescriberGUI)

### Class Breakdown

#### Core Classes (imported from data_models.py):
1. **ImageDescription** (line 457) - Stores single description
   - Fields: text, model, prompt_style, created, provider
   - Methods: to_dict(), from_dict()
   
2. **ImageItem** (line 504) - Represents one image
   - Fields: path, item_type, descriptions[], metadata
   - Methods: add_description(), remove_description(), get_latest_description()
   
3. **ImageWorkspace** (line 543) - Workspace container
   - Fields: items[], workspace_file, imported_workflow_dir
   - Methods: add_item(), remove_item(), save(), load()

#### Accessibility Widgets (WCAG 2.2 AA compliance):
4. **AccessibleTreeWidget** (line 125) - Enhanced QTreeWidget
   - Features: Keyboard navigation, accessible names, combined text for screen readers
   - Methods: keyPressEvent(), focusInEvent(), setAccessibleName()
   
5. **AccessibleNumericInput** (line 224) - Enhanced QLineEdit for numbers
   - Features: Validation, accessible descriptions
   
6. **AccessibleTextEdit** (line 285) - Enhanced QPlainTextEdit
   - Features: Character count, accessible feedback

#### Worker Threads (All inherit QThread):
7. **ProcessingWorker** (line 635) - Single image processing
   - Signals: progress, finished, error
   - Methods: run(), _process_ollama(), _process_openai(), _process_claude()
   - **CRITICAL:** 246 lines of AI provider logic
   
8. **WorkflowProcessWorker** (line 881) - Batch workflow processing
   - Signals: progress, finished, error
   - Methods: run() - orchestrates workflow steps
   - **CRITICAL:** 50 lines of batch processing logic
   
9. **ConversionWorker** (line 931) - HEIC conversion
   - Signals: progress, finished, error
   - Methods: run() - uses PIL for conversion
   - **CRITICAL:** 87 lines of image conversion logic
   
10. **VideoProcessingWorker** (line 1018) - Video frame extraction
    - Signals: progress, finished, error
    - Methods: run() - uses cv2 for video processing
    - **CRITICAL:** 162 lines of video processing logic
    
11. **ChatProcessingWorker** (line 1180) - Chat mode processing
    - Signals: message_update, finished, error
    - Methods: run(), _process_chat_ollama(), _process_chat_openai(), _process_chat_claude()
    - **CRITICAL:** 511 lines of chat logic (most complex worker!)

#### Dialog Classes:
12. **DirectorySelectionDialog** (line 1691) - Select image directories
    - Features: Directory tree, recursive checkbox
    - **94 lines**
    
13. **WorkspaceDirectoryManager** (line 1785) - Manage workspace directories
    - Features: Add/remove directories, list widget
    - **168 lines**
    
14. **ProcessingDialog** (line 2545) - Main processing dialog
    - Features: Model selection, prompt customization, provider settings, batch options
    - **592 lines** - VERY COMPLEX
    
15. **ChatDialog** (line 2545) - Simple chat mode selector
    - Features: Model/provider selection
    - **192 lines**
    
16. **ChatWindow** (line 2737) - Full chat interface
    - Features: Conversation history, image preview, message sending
    - **285 lines**
    
17. **VideoProcessingDialog** (line 3022) - Video extraction settings
    - Features: Time interval, scene detection, quality settings
    - **166 lines**
    
18. **AllDescriptionsDialog** (line 3188) - View all descriptions
    - Features: Table view, export functionality
    - **56 lines**
    
19. **ModelManagerDialog** (line 3244) - Manage AI models
    - Features: Provider selection, model list, install/remove
    - **1010 lines** - EXTREMELY COMPLEX

#### Main Window:
20. **ImageDescriberGUI** (line 4254) - Main application window
    - Features: Menu system, workspace tree, description editor, image preview, status bar
    - **6271 lines** - MASSIVE (60% of entire file!)
    - Major methods:
      - `init_ui()` - UI construction (200+ lines)
      - `create_menus()` - Menu bar setup (150+ lines)
      - `process_images()` - Batch processing logic
      - `save_workspace()`, `load_workspace()` - Persistence
      - `import_workflow()` - Import from workflow directory
      - Event handlers for tree clicks, description edits, etc.

### Dependency Analysis

#### External Dependencies:
- **ollama** (optional) - Ollama model discovery and processing
- **openai** (optional) - OpenAI API
- **anthropic** (implied via ai_providers) - Claude API
- **cv2/opencv** (optional) - Video frame extraction
- **PIL/Pillow** - Image conversion
- **PyQt6** - UI framework (TO BE REPLACED)

#### Internal Dependencies:
- **ai_providers.py** - Multi-provider abstraction (critical)
- **data_models.py** - Data structures (ImageDescription, ImageItem, ImageWorkspace)
- **../scripts/metadata_extractor.py** - EXIF/GPS extraction
- **../scripts/versioning.py** - Build banners
- **../models/provider_configs.py** - Provider capabilities
- **../models/model_options.py** - Model-specific options

#### Path Dependencies:
```python
# Add scripts directory
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

# Add models directory
models_path = Path(__file__).parent.parent / 'models'
sys.path.insert(0, str(models_path))
```

**CRITICAL:** ImageDescriber assumes it lives in `imagedescriber/` with `scripts/` and `models/` at parent level.

### Threading Model

PyQt6 threading uses:
- `QThread` base class
- `pyqtSignal` for communication
- `self.run()` method override
- Signals: progress, finished, error

wxPython threading will use:
- `threading.Thread` base class
- `wx.lib.newevent` for custom events
- `wx.CallAfter()` for UI updates
- Event types: `EVT_PROGRESS`, `EVT_FINISHED`, `EVT_ERROR`

### Migration Complexity Assessment

| Component | Lines | Complexity | Risk | Priority |
|-----------|-------|------------|------|----------|
| Main Window | 6271 | EXTREME | HIGH | 1 |
| ChatProcessingWorker | 511 | HIGH | MEDIUM | 3 |
| ProcessingWorker | 246 | MEDIUM | MEDIUM | 4 |
| ModelManagerDialog | 1010 | HIGH | HIGH | 2 |
| ProcessingDialog | 592 | HIGH | MEDIUM | 5 |
| ChatWindow | 285 | MEDIUM | LOW | 6 |
| Other Dialogs | ~700 | LOW-MEDIUM | LOW | 7 |
| Accessibility Widgets | ~300 | MEDIUM | MEDIUM | 8 |
| Other Workers | ~300 | MEDIUM | MEDIUM | 9 |

**Recommendation:** Migrate in 4 phases:
1. **Phase 1:** Main window + simple dialogs (no threading)
2. **Phase 2:** Processing dialogs + model manager
3. **Phase 3:** All worker threads
4. **Phase 4:** Accessibility widgets + final polish

---

## 2. Shared Library Analysis

### Current Code Duplication

Comparing `viewer_wx_full.py`, `prompt_editor_wx.py`, `idtconfigure_wx.py`:

#### Pattern 1: Config File Loading (100% duplicated)
```python
def find_config_file(self, filename):
    """Find config file in frozen vs dev mode"""
    if getattr(sys, 'frozen', False):
        # Try multiple paths
        exe_dir = Path(sys.executable).parent
        # Check exe_dir/scripts/filename
        # Check exe_dir/filename
    # Try relative paths
    # Fallback to current directory
```

**Found in:** All 3 apps (viewer, prompt_editor, idtconfigure)
**Lines duplicated:** ~30 lines × 3 = 90 lines

#### Pattern 2: Scripts Directory Resolution (100% duplicated)
```python
def find_scripts_directory(self):
    """Find scripts directory in frozen vs dev mode"""
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).parent
        # Try exe_dir/scripts
        # Try exe_dir/../scripts
    # Try relative ../scripts
```

**Found in:** idtconfigure, prompt_editor
**Lines duplicated:** ~20 lines × 2 = 40 lines

#### Pattern 3: Modified State Tracking (100% duplicated)
```python
def mark_modified(self):
    if not self.modified:
        self.modified = True
        self.update_window_title()
        self.save_btn.Enable(True)

def update_window_title(self):
    if self.modified:
        self.SetTitle(f"{title} *")
    else:
        self.SetTitle(title)
```

**Found in:** prompt_editor, idtconfigure
**Lines duplicated:** ~20 lines × 2 = 40 lines

#### Pattern 4: Save with Backup (100% duplicated)
```python
# Create backup
if config_file.exists():
    backup = config_file.with_suffix('.bak')
    shutil.copy2(config_file, backup)

# Save file
with open(config_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
```

**Found in:** prompt_editor, idtconfigure
**Lines duplicated:** ~15 lines × 2 = 30 lines

#### Pattern 5: Unsaved Changes Confirmation (90% similar)
```python
if self.modified:
    dlg = wx.MessageDialog(self, "Save changes?",
                          "Unsaved Changes", wx.YES_NO | wx.CANCEL)
    result = dlg.ShowModal()
    if result == wx.ID_YES:
        self.save_config()
    elif result == wx.ID_CANCEL:
        return False
```

**Found in:** prompt_editor, idtconfigure, viewer (slightly different)
**Lines duplicated:** ~15 lines × 3 = 45 lines

#### Pattern 6: About Dialog (80% similar)
```python
info = wx.adv.AboutDialogInfo()
info.SetName("App Name")
info.SetVersion("1.0.0")
info.SetDescription("Description")
info.AddDeveloper("Developer")
wx.adv.AboutBox(info)
```

**Found in:** All 3 apps
**Lines duplicated:** ~10 lines × 3 = 30 lines

#### Pattern 7: File/Directory Dialogs (70% similar)
```python
dlg = wx.FileDialog(self, "Open File",
                   wildcard="JSON files (*.json)|*.json",
                   style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
if dlg.ShowModal() == wx.ID_OK:
    path = dlg.GetPath()
    # Process file
```

**Found in:** All 3 apps (different wildcards)
**Lines duplicated:** ~10 lines × 3 = 30 lines

### Total Duplication Estimate: ~305 lines

### Proposed Shared Library Design

**File:** `shared/wx_common.py` (or `shared/idt_wx_utils.py`)

#### Module Structure:
```python
# shared/wx_common.py

import wx
import wx.adv
import json
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List

# ==================== PATH RESOLUTION ====================

def get_base_directory() -> Path:
    """Get base directory (frozen vs dev mode)"""
    
def find_file(filename: str, search_dirs: List[str] = None) -> Optional[Path]:
    """Find file in multiple locations"""
    
def find_scripts_directory() -> Path:
    """Find scripts directory"""
    
def find_config_file(filename: str) -> Optional[Path]:
    """Find config file with standard search order"""

# ==================== CONFIG MANAGEMENT ====================

class ConfigManager:
    """Manage JSON config files with backup/restore"""
    
    def __init__(self, config_file: Path):
        self.config_file = config_file
        self.config_data = {}
        
    def load(self) -> Dict[str, Any]:
        """Load config with error handling"""
        
    def save(self, create_backup: bool = True):
        """Save config with optional backup"""
        
    def create_backup(self, timestamp: bool = False) -> Path:
        """Create backup file"""
        
    def restore_backup(self, backup_file: Path):
        """Restore from backup"""
        
    def get_value(self, path: List[str], default: Any = None) -> Any:
        """Get nested value by path"""
        
    def set_value(self, path: List[str], value: Any):
        """Set nested value by path"""

# ==================== MODIFIED STATE TRACKING ====================

class ModifiedStateMixin:
    """Mixin for tracking and displaying modified state"""
    
    def __init__(self):
        self.modified = False
        self.original_title = ""
        
    def mark_modified(self):
        """Mark as modified and update title"""
        
    def clear_modified(self):
        """Clear modified flag and update title"""
        
    def confirm_unsaved_changes(self) -> bool:
        """Show confirmation dialog for unsaved changes"""

# ==================== DIALOGS ====================

def show_error(parent, message: str, title: str = "Error"):
    """Show error message dialog"""
    
def show_warning(parent, message: str, title: str = "Warning"):
    """Show warning message dialog"""
    
def show_info(parent, message: str, title: str = "Information"):
    """Show info message dialog"""
    
def ask_yes_no(parent, message: str, title: str = "Confirm") -> bool:
    """Show yes/no confirmation dialog"""
    
def ask_yes_no_cancel(parent, message: str, title: str = "Confirm") -> int:
    """Show yes/no/cancel dialog. Returns wx.ID_YES, wx.ID_NO, or wx.ID_CANCEL"""

def open_file_dialog(parent, message: str, wildcard: str = "*.*",
                    default_dir: str = "", default_file: str = "") -> Optional[str]:
    """Show file open dialog, return path or None"""
    
def save_file_dialog(parent, message: str, wildcard: str = "*.*",
                    default_dir: str = "", default_file: str = "") -> Optional[str]:
    """Show file save dialog, return path or None"""
    
def select_directory_dialog(parent, message: str = "Select Directory",
                           default_path: str = "") -> Optional[str]:
    """Show directory selection dialog, return path or None"""

def show_about_dialog(parent, app_name: str, version: str,
                     description: str, developers: List[str] = None):
    """Show standardized About dialog"""

# ==================== ACCESSIBLE WIDGETS ====================

class AccessibleListBox(wx.ListBox):
    """ListBox with enhanced accessibility for VoiceOver"""
    
    def __init__(self, parent, id=wx.ID_ANY, choices=None, **kwargs):
        # Enhanced keyboard navigation
        # Accessible names and descriptions
        
class AccessibleTextCtrl(wx.TextCtrl):
    """TextCtrl with character count and accessibility"""
    
    def __init__(self, parent, id=wx.ID_ANY, **kwargs):
        # Character count label
        # Accessible descriptions

# ==================== UTILITIES ====================

def sanitize_filename(filename: str) -> str:
    """Remove invalid characters from filename"""
    
def format_timestamp(dt) -> str:
    """Format timestamp consistently: M/D/YYYY H:MMP"""
    
def get_app_version() -> str:
    """Get application version from VERSION file or versioning module"""
```

#### Usage Example:
```python
# In prompt_editor_wx.py
from shared.wx_common import (
    ConfigManager, ModifiedStateMixin,
    show_error, ask_yes_no_cancel,
    open_file_dialog, save_file_dialog,
    show_about_dialog
)

class PromptEditorFrame(wx.Frame, ModifiedStateMixin):
    def __init__(self):
        wx.Frame.__init__(self, None, title="Prompt Editor")
        ModifiedStateMixin.__init__(self)
        
        # Config management
        self.config = ConfigManager(find_config_file('image_describer_config.json'))
        self.config.load()
        
    def on_save(self, event):
        self.config.save(create_backup=True)
        self.clear_modified()
        
    def on_close(self, event):
        if not self.confirm_unsaved_changes():
            return
        self.Destroy()
```

### Benefits of Shared Library:
1. **Code Reduction:** ~305 lines eliminated from individual apps
2. **Consistency:** All apps use same dialogs, same behavior
3. **Maintenance:** Fix bug once, all apps benefit
4. **Testing:** Test shared library once, all apps covered
5. **Future Apps:** New apps can reuse immediately

---

## 3. Project Restructuring Plan

### Current Structure (Root Directory):
```
/
├── idt_cli.py          # CLI dispatcher (800+ lines)
├── idt_runner.py       # Entry point wrapper
├── idt.spec            # Old PyInstaller spec?
├── idt_cli.spec        # Current PyInstaller spec
├── workflow.py         # Legacy script?
├── scripts/            # Core workflow scripts
├── analysis/           # Analysis scripts
├── viewer/             # Viewer app
├── prompt_editor/      # Prompt editor app
├── idtconfigure/       # Configure app
├── imagedescriber/     # Image describer app
├── models/             # Model registry
├── BuildAndRelease/    # Build scripts
└── ...other files
```

**Problems:**
1. Root directory cluttered with idt_* files
2. Inconsistent: GUI apps in folders, CLI in root
3. Confusing: Multiple spec files, workflow.py orphan

### Proposed Structure:
```
/
├── idt/                # NEW: CLI app directory
│   ├── idt_cli.py      # Moved from root
│   ├── idt_runner.py   # Moved from root
│   ├── idt.spec        # Consolidated spec file
│   └── build_idt.bat   # Build script
├── scripts/            # Core workflow scripts (unchanged)
├── analysis/           # Analysis scripts (unchanged)
├── models/             # Model registry (unchanged)
├── shared/             # NEW: Shared wxPython utilities
│   └── wx_common.py
├── viewer/             # Viewer app
│   ├── viewer_wx.py    # Moved from voiceover_test
│   ├── viewer.spec
│   └── build_viewer.bat
├── prompt_editor/      # Prompt editor app
│   ├── prompt_editor_wx.py  # Moved from voiceover_test
│   ├── prompt_editor.spec
│   └── build_prompt_editor.bat
├── idtconfigure/       # Configure app
│   ├── idtconfigure_wx.py   # Moved from voiceover_test
│   ├── idtconfigure.spec
│   └── build_idtconfigure.bat
├── imagedescriber/     # Image describer app
│   ├── imagedescriber_wx.py # To be created
│   ├── ai_providers.py      # Existing
│   ├── data_models.py       # Existing
│   ├── imagedescriber.spec
│   └── build_imagedescriber.bat
├── BuildAndRelease/    # Build scripts
│   ├── builditall.bat  # Updated for new structure
│   ├── builditall.sh   # NEW: macOS version
│   └── final_working.spec  # Updated
└── ...other files
```

### Path Dependency Updates Required:

#### idt_cli.py Changes:
```python
# OLD (in root):
def get_base_dir():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent

# NEW (in idt/ directory):
def get_base_dir():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent  # Go up to project root

# All script imports need to know about parent directory
scripts_path = get_base_dir() / 'scripts'
analysis_path = get_base_dir() / 'analysis'
```

#### PyInstaller Spec Changes:
```python
# OLD spec (from root):
datas=[
    ('scripts', 'scripts'),
    ('analysis', 'analysis'),
]

# NEW spec (from idt/ directory):
datas=[
    ('../scripts', 'scripts'),
    ('../analysis', 'analysis'),
    ('../models', 'models'),
]
```

#### Build Script Changes:
```bash
# OLD: BuildAndRelease/build_idt.bat
cd %~dp0\..
pyinstaller --noconfirm idt_cli.spec

# NEW: BuildAndRelease/build_idt.bat
cd %~dp0\..\idt
pyinstaller --noconfirm idt.spec
```

### Files to Move:
1. **idt_cli.py** → idt/idt_cli.py
2. **idt_runner.py** → idt/idt_runner.py
3. **idt_cli.spec** → idt/idt.spec (rename)
4. **viewer_wx_full.py** → viewer/viewer_wx.py
5. **prompt_editor_wx.py** → prompt_editor/prompt_editor_wx.py
6. **idtconfigure_wx.py** → idtconfigure/idtconfigure_wx.py

### Files to Delete:
1. **idt.spec** (old/duplicate)
2. **workflow.py** (if orphaned/unused)
3. **voiceover_test/** (entire directory after migration)

---

## 4. Build Script Updates

### Current Build Scripts:

#### Windows:
- `BuildAndRelease/builditall.bat` - Builds all apps sequentially
- `BuildAndRelease/build_idt.bat` - Builds idt.exe
- Individual app build scripts in each directory
- Installer: `BuildAndRelease/build_installer.bat`

#### macOS:
- No unified build script currently
- Individual `build_*.bat` scripts (should be .sh)

### Required Updates:

#### 1. builditall.bat (Windows)
```batch
@echo off
echo Building all IDT applications...

REM Build CLI tool
cd /d %~dp0\..\idt
call build_idt.bat
if errorlevel 1 goto error

REM Build Viewer
cd /d %~dp0\..\viewer
call build_viewer.bat
if errorlevel 1 goto error

REM Build Prompt Editor
cd /d %~dp0\..\prompt_editor
call build_prompt_editor.bat
if errorlevel 1 goto error

REM Build IDTConfigure
cd /d %~dp0\..\idtconfigure
call build_idtconfigure.bat
if errorlevel 1 goto error

REM Build ImageDescriber
cd /d %~dp0\..\imagedescriber
call build_imagedescriber.bat
if errorlevel 1 goto error

echo.
echo ========================================
echo All builds completed successfully!
echo ========================================
goto end

:error
echo.
echo ========================================
echo Build failed!
echo ========================================
exit /b 1

:end
```

#### 2. builditall.sh (macOS) - NEW
```bash
#!/bin/bash
set -e

echo "Building all IDT applications..."

# Get script directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR/.."

# Build CLI tool
echo "Building idt..."
cd idt
./build_idt.sh
cd ..

# Build Viewer
echo "Building viewer..."
cd viewer
./build_viewer.sh
cd ..

# Build Prompt Editor
echo "Building prompt_editor..."
cd prompt_editor
./build_prompt_editor.sh
cd ..

# Build IDTConfigure
echo "Building idtconfigure..."
cd idtconfigure
./build_idtconfigure.sh
cd ..

# Build ImageDescriber
echo "Building imagedescriber..."
cd imagedescriber
./build_imagedescriber.sh
cd ..

echo ""
echo "========================================"
echo "All builds completed successfully!"
echo "========================================"
```

#### 3. Individual App Build Scripts
Each app directory needs:
- **build_<app>.bat** (Windows)
- **build_<app>.sh** (macOS)

Example `idt/build_idt.sh`:
```bash
#!/bin/bash
set -e

echo "Building idt..."

# Activate venv
source ../.venv/bin/activate

# Build with PyInstaller
pyinstaller --noconfirm idt.spec

echo "idt build complete!"
```

#### 4. Spec File Updates
Each spec file needs paths updated for new structure:

**idt/idt.spec:**
```python
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['idt_cli.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('../scripts', 'scripts'),
        ('../analysis', 'analysis'),
        ('../models', 'models'),
        ('../VERSION', '.'),
    ],
    hiddenimports=[
        'scripts.workflow',
        'scripts.image_describer',
        'analysis.stats_analysis',
        'analysis.combine_workflow_descriptions',
        'analysis.content_analysis',
    ],
    ...
)
```

**viewer/viewer.spec:**
```python
datas=[
    ('../scripts', 'scripts'),
    ('../models', 'models'),
    ('../VERSION', '.'),
],
```

Similar updates for all GUI app specs.

#### 5. Windows Installer Updates

`BuildAndRelease/installer_script.iss` (Inno Setup):
```iss
; OLD paths:
Source: "dist\idt.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\viewer.exe"; DestDir: "{app}"; Flags: ignoreversion

; NEW paths:
Source: "..\idt\dist\idt.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\viewer\dist\viewer.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\prompt_editor\dist\prompteditor.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\idtconfigure\dist\idtconfigure.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\imagedescriber\dist\imagedescriber.exe"; DestDir: "{app}"; Flags: ignoreversion
```

---

## 5. Migration Execution Plan

### Phase 1: Analysis & Shared Library (CURRENT)
- ✅ Analyze ImageDescriber architecture
- ✅ Identify shared library opportunities
- ⏳ Create shared/wx_common.py
- ⏳ Write unit tests for shared library

### Phase 2: Project Restructuring
- Move idt files to idt/ directory
- Update all path references in idt_cli.py
- Update idt.spec file
- Test idt.exe still works
- Move wxPython apps to production locations
- Update all spec files
- Test all builds

### Phase 3: Refactor with Shared Library
- Update viewer_wx.py to use shared/wx_common.py
- Update prompt_editor_wx.py to use shared/wx_common.py
- Update idtconfigure_wx.py to use shared/wx_common.py
- Remove duplicate code
- Test all apps work

### Phase 4: ImageDescriber Migration
- Create imagedescriber/imagedescriber_wx.py
- Migrate in 4 sub-phases:
  - 4a: Main window + simple dialogs
  - 4b: Processing dialogs + model manager
  - 4c: All worker threads
  - 4d: Accessibility widgets + final polish
- Build and test

### Phase 5: Build Script Updates
- Create macOS build scripts (.sh files)
- Update builditall.bat
- Create builditall.sh
- Update Windows installer
- Test complete build process

### Phase 6: Testing & Documentation
- Comprehensive testing of all 5 apps
- VoiceOver accessibility testing
- Windows compatibility testing
- Update all documentation
- Update AI_AGENT_REFERENCE.md

---

## 6. Risk Assessment

### High Risk Items:
1. **idt Path Dependencies** - Breaking CLI tool would break all workflows
2. **ImageDescriber Threading** - Complex async logic, easy to break
3. **Windows Builds** - No Windows machine to test on

### Medium Risk Items:
1. **Shared Library Bugs** - Would affect all apps
2. **Spec File Paths** - Easy to miss a path reference
3. **Build Script Paths** - Platform-specific path handling

### Low Risk Items:
1. **Viewer/PromptEditor/Configure** - Already migrated, just moving
2. **Documentation Updates** - Time-consuming but low risk

### Mitigation Strategies:
1. **Test after each phase** - Don't proceed until current phase works
2. **Keep backups** - Git branch protection
3. **Incremental changes** - Small commits, test frequently
4. **Document changes** - Track all path updates in checklist

---

## 7. Estimated Timeline

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| Phase 1 | Shared library creation | 3-4 hours |
| Phase 2 | Project restructuring | 2-3 hours |
| Phase 3 | Refactor with shared lib | 2-3 hours |
| Phase 4 | ImageDescriber migration | 12-15 hours |
| Phase 5 | Build script updates | 2-3 hours |
| Phase 6 | Testing & docs | 3-5 hours |
| **TOTAL** | | **24-33 hours** |

**Current Progress:** ~8 hours invested (3 apps migrated)
**Remaining:** ~16-25 hours

---

## Next Actions

1. ✅ Create this analysis document
2. ⏳ Create shared/wx_common.py
3. ⏳ Write unit tests for shared library
4. ⏳ Move idt to idt/ directory
5. ⏳ Test idt.exe with new structure
6. ⏳ Move wxPython apps to production locations
7. ⏳ Refactor apps to use shared library
8. ⏳ Begin ImageDescriber migration

