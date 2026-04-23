# Module Dependency Map

**Generated:** 2026-01-13  
**Purpose:** Map all import relationships between modules to identify coupling and circular dependencies

---

## Summary

- **Total Python Files Scanned:** 45
  - scripts/: 16 files
  - analysis/: 4 files  
  - imagedescriber/: 9 files (includes deprecated Qt6 files)
  - models/: 6 files
  - viewer/: 3 files (GUI app)
  - prompt_editor/: 3 files (GUI app)
  - idtconfigure/: 3 files (GUI app)
  - idt/: 2 files (CLI dispatcher)
  - shared/: 2 files (wx_common.py, accessible list components)

- **Key Findings:**
  - ✅ No circular dependencies detected
  - ⚠️ High coupling in `workflow.py` (depends on 3 local modules)
  - ⚠️ `image_describer.py` imports from `imagedescriber/` package (cross-directory)
  - ✅ Clean separation in `analysis/` and `models/` directories
  - ✅ All 5 wxPython GUI apps share `shared/wx_common.py` (good pattern)
  - ⚠️ Deprecated Qt6 versions still exist for 3 GUI apps

---

## Directory Structure Overview

```
idt/              - CLI dispatcher (routes commands to scripts) (2 files)
scripts/          - Core workflow and processing scripts (16 files)
analysis/         - Analysis and reporting tools (4 files)
imagedescriber/   - GUI application and AI providers (9 files: 6 wx, 3 deprecated Qt6)
viewer/           - Workflow results browser GUI (3 files: 2 wx, 1 deprecated Qt6)
prompt_editor/    - Prompt template editor GUI (3 files: 2 wx, 1 deprecated Qt6)
idtconfigure/     - Configuration management GUI (3 files: 2 wx, 1 deprecated Qt6)
models/           - Model registry and configuration (6 files)
shared/           - Shared utilities (wx_common.py, accessible widgets)
```

**Note:** All GUI apps have been migrated to wxPython. Legacy Qt6 versions can be removed.

---

## Dependency Graph (Local Modules Only)

### scripts/ Directory

#### workflow.py (Core Orchestrator)
**Imports:**
- ✅ `workflow_utils` → WorkflowConfig, WorkflowLogger, FileDiscovery, path utilities
- ✅ `image_describer` → get_default_prompt_style(), get_default_model()
- ⚠️ `config_loader` → load_json_config() (conditionally imported)
- ⚠️ `versioning` → log_build_banner() (conditionally imported)
- ⚠️ **Function-level import:** `web_image_downloader` → WebImageDownloader (in download_images())

**Imported By:** None directly (entry point via CLI)

**Notes:** 
- Central orchestrator with highest coupling
- Spawns subprocesses for: `image_describer.py`, `video_frame_extractor.py`, `ConvertImage.py`, `descriptions_to_html.py`
- Uses try/except for optional imports (good pattern)

---

#### image_describer.py (AI Description Engine)
**Imports:**
- ⚠️ `metadata_extractor` → MetadataExtractor, NominatimGeocoder (optional)
- ⚠️ `ConvertImage` → optimize_image_size(), size constants
- ⚠️ **Cross-directory:** `imagedescriber.ai_providers` → OllamaProvider, OpenAIProvider, ClaudeProvider, HuggingFaceProvider

**Imported By:**
- `workflow.py` → get_default_prompt_style(), get_default_model()

**Notes:**
- Cross-directory import breaks clean separation
- Should ideally import from `scripts/` only
- Heavy external dependencies: PIL, ollama, anthropic, openai

---

#### guided_workflow.py
**Imports:**
- ✅ `config_loader` → load_json_config()

**Imported By:** None (CLI entry point)

**Notes:** Clean, minimal dependencies

---

#### workflow_utils.py (Shared Workflow Utilities)
**Imports:** None (only standard library)

**Imported By:**
- `workflow.py`

**Notes:** ✅ Excellent - pure utility module with no local dependencies

---

#### config_loader.py (Configuration Loader)
**Imports:** None (only standard library)

**Imported By:**
- `workflow.py` (conditionally)
- `guided_workflow.py`

**Notes:** ✅ Excellent - pure utility module, PyInstaller-aware

---

#### ConvertImage.py (Image Conversion)
**Imports:** None (only PIL, piexif, pillow_heif)

**Imported By:**
- `image_describer.py` → optimize_image_size(), constants

**Notes:** ✅ Clean utility module, could be in shared/

---

#### metadata_extractor.py (EXIF/GPS Extraction)
**Imports:** None (only PIL, piexif)

**Imported By:**
- `image_describer.py` (optional)

**Notes:** ✅ Clean utility module, duplicate EXIF logic exists elsewhere

---

#### Other scripts/ files (Standalone)
The following have **no local imports** (only standard library + external packages):
- ✅ `descriptions_to_html.py`
- ✅ `video_frame_extractor.py`
- ✅ `video_metadata_extractor.py`
- ✅ `exif_embedder.py`
- ✅ `web_image_downloader.py`
- ✅ `versioning.py`
- ✅ `resource_manager.py`
- ✅ `list_results.py`
- ✅ `list_prompts.py`

**Notes:** All these are self-contained tools - excellent modular design

---

### analysis/ Directory

#### Analysis Module Dependencies
All three analysis scripts follow the same pattern:

**stats_analysis.py**
**combine_workflow_descriptions.py**
**content_analysis.py**

**All import:**
- ✅ `analysis_utils` → get_safe_filename(), ensure_directory()

**analysis_utils.py**
- Imports: None (only standard library)

**Dependency Pattern:**
```
analysis_utils.py  (base utility)
    ↑
    ├── stats_analysis.py
    ├── combine_workflow_descriptions.py
    └── content_analysis.py
```

**Notes:** ✅ Excellent - clean tree structure, no circular dependencies, shared utilities properly factored out

---

### imagedescriber/ Directory (GUI Application)

#### imagedescriber_wx.py (Main GUI)
**Imports:**
- ✅ `shared.wx_common` → Shared wxPython utilities

**Imported By:** None (GUI entry point)

---

#### dialogs_wx.py (GUI Dialogs)
**Imports:**
- ✅ `shared.wx_common` → Shared wxPython utilities

---

#### workers_wx.py (Background Workers)
**Imports:** None (only wx)

---

#### ai_providers.py (AI Provider Abstractions)
**Imports:** None (only external: ollama, anthropic, openai, huggingface)

**Imported By:**
- ⚠️ `scripts/image_describer.py` (cross-directory)
- ✅ `imagedescriber/worker_threads.py`

**Notes:** This is a shared module used by both CLI and GUI

---

#### Legacy Qt6 Files (Deprecated)
- `dialogs.py` → Imports `data_models`, `ui_components` (PyQt6 versions)
- `worker_threads.py` → Imports `ai_providers`
- `ui_components.py` → No local imports

**Notes:** ⚠️ These can likely be removed after wx migration is complete

---

### models/ Directory

#### Model Registry System
**No inter-dependencies within models/**

All files are standalone:
- ✅ `model_registry.py` - No local imports
- ✅ `provider_configs.py` - No local imports
- ✅ `model_options.py` - No local imports
- ✅ `check_models.py` - No local imports (CLI tool)
- ✅ `manage_models.py` - No local imports (CLI tool)

**Notes:** ✅ Excellent modular design - all configuration files are independent

---

### shared/ Directory

#### wx_common.py (Shared wxPython Utilities)
**Imports:** None (only wx)

**Imported By:**
- `imagedescriber/imagedescriber_wx.py`
- `imagedescriber/dialogs_wx.py`
- `viewer/viewer_wx.py`
- `prompt_editor/prompt_editor_wx.py`
- `idtconfigure/idtconfigure_wx.py`

**Notes:** ✅ Perfect shared utility - used by all 5 wxPython apps

---

## GUI Applications (All 5 Apps)

### 1. idt/ - CLI Dispatcher

#### idt_cli.py (Command Router)
**Imports:** None (only standard library)

**Functionality:**
- Routes commands to scripts (workflow, stats, etc.)
- Routes to GUI apps (viewer, imagedescriber, etc.)
- Handles frozen vs development mode
- Provides --debug-paths flag

**Imported By:**
- `idt_runner.py` (entry point wrapper)

**Notes:** ✅ Clean dispatcher pattern, no local dependencies

---

#### idt_runner.py (Entry Point)
**Imports:**
- ✅ `idt_cli` → main()

**Notes:** ✅ Minimal wrapper to launch CLI

---

### 2. imagedescriber/ - Batch Image Processing GUI

#### imagedescriber_wx.py (Main GUI - wxPython)
**Imports:**
- ✅ `shared.wx_common` → Shared wxPython utilities

**Imported By:** None (GUI entry point)

**Notes:** ✅ wxPython version (current), no local script dependencies

---

#### dialogs_wx.py (GUI Dialogs - wxPython)
**Imports:**
- ✅ `shared.wx_common` → Shared wxPython utilities

---

#### workers_wx.py (Background Workers - wxPython)
**Imports:** None (only wx)

---

#### Deprecated Qt6 Files (Can Be Removed)
- ❌ `dialogs.py` - PyQt6 version (deprecated)
- ❌ `worker_threads.py` - PyQt6 version (deprecated)
- ❌ `ui_components.py` - PyQt6 version (deprecated)

**Recommendation:** Delete these 3 files after verifying wx version is stable

---

### 3. viewer/ - Workflow Results Browser GUI

#### viewer_wx.py (Main GUI - wxPython)
**Imports:**
- ✅ `shared.wx_common` → Shared wxPython utilities

**Imported By:** None (GUI entry point)

**Functionality:**
- Browse workflow directories
- Display descriptions and images
- Live monitoring of active workflows
- Progress tracking

**Notes:** ✅ Clean GUI app, uses shared utilities correctly

---

#### custom_accessible_listbox_viewer.py (Accessible Widget)
**Imports:** None (only wx)

**Notes:** ✅ Custom accessible widget for screen readers

---

### 4. prompt_editor/ - Prompt Template Editor GUI

#### prompt_editor_wx.py (Main GUI - wxPython)
**Imports:**
- ✅ `shared.wx_common` → Shared wxPython utilities

**Imported By:** None (GUI entry point)

**Functionality:**
- Visual editor for prompt templates
- Template validation
- Save/load prompt configurations

**Notes:** ✅ Clean GUI app, uses shared utilities correctly

---

#### prompt_editor.py (Deprecated Qt6 Version)
**Imports:** PyQt6 modules

**Recommendation:** ❌ Delete after verifying wx version is stable

---

### 5. idtconfigure/ - Configuration Management GUI

#### idtconfigure_wx.py (Main GUI - wxPython)
**Imports:**
- ✅ `shared.wx_common` → Shared wxPython utilities

**Imported By:** None (GUI entry point)

**Functionality:**
- Edit workflow_config.json
- Edit image_describer_config.json
- Manage API keys
- Configure providers and models

**Notes:** ✅ Clean GUI app, uses shared utilities correctly

---

#### idtconfigure.py (Deprecated Qt6 Version)
**Imports:** PyQt6 modules

**Recommendation:** ❌ Delete after verifying wx version is stable

---

## Dependency Summary by Category

### ✅ Well-Designed (No local imports)
**Pure Utilities:**
- `scripts/workflow_utils.py`
- `scripts/config_loader.py`
- `scripts/metadata_extractor.py`
- `scripts/ConvertImage.py`
- `analysis/analysis_utils.py`
- `shared/wx_common.py`

**Standalone Tools:**
- `scripts/descriptions_to_html.py`
- `scripts/video_frame_extractor.py`
- `scripts/exif_embedder.py`
- `scripts/web_image_downloader.py`
- All files in `models/`

### ⚠️ High Coupling (3+ local imports)
- `scripts/workflow.py` → 4 imports (workflow_utils, image_describer, config_loader, versioning)
  - **Justification:** Orchestrator role requires coordination

### ⚠️ Cross-Directory Dependencies
**Issue:** `scripts/image_describer.py` → `imagedescriber/ai_providers.py`

**Impact:**
- Breaks clean directory separation
- `ai_providers.py` is logically shared infrastructure
- Should potentially be in `shared/` directory

**Recommendation:** Consider moving `ai_providers.py` to `shared/` or creating `shared/ai/`

---

## Circular Dependency Analysis

**Status:** ✅ **No circular dependencies detected**

**Checked patterns:**
1. `workflow.py` ↔ `workflow_utils.py` - ✅ One-way only
2. `image_describer.py` ↔ `ai_providers.py` - ✅ One-way only
3. `analysis/` modules - ✅ All depend on `analysis_utils`, no cycles
4. `imagedescriber/` GUI modules - ✅ No circular deps

---

## Import Pattern Analysis

### Conditional Imports (Good Practice)
```python
# Pattern 1: Try/except with None fallback (CORRECT)
try:
    from config_loader import load_json_config
except ImportError:
    load_json_config = None
```
**Used in:** `workflow.py`, `image_describer.py`

### Function-Level Imports (Use Sparingly)
```python
# Pattern 2: Import inside function (ACCEPTABLE for optional features)
def download_images(...):
    try:
        from web_image_downloader import WebImageDownloader
    except ImportError:
        from scripts.web_image_downloader import WebImageDownloader
```
**Used in:** `workflow.py`
**Status:** ⚠️ Should be module-level for frozen mode safety

---

## External Package Dependencies by Module

### Heavy External Dependencies:
- **image_describer.py:** PIL, ollama, anthropic, openai, huggingface_hub
- **ai_providers.py:** ollama, anthropic, openai, huggingface_hub, requests
- **video_frame_extractor.py:** cv2 (OpenCV), numpy
- **ConvertImage.py:** PIL, piexif, pillow_heif
- **metadata_extractor.py:** PIL, piexif, requests (for geocoding)
- **web_image_downloader.py:** requests, beautifulsoup4

### Light External Dependencies:
- **All analysis scripts:** Standard library only
- **All model scripts:** Standard library + json
- **workflow_utils.py:** Standard library only

---

## Recommendations

### 1. ✅ Keep Existing Clean Modules
The following are excellent and should serve as templates:
- `workflow_utils.py`
- `config_loader.py`
- `analysis_utils.py`
- All `models/` files

### 2. ⚠️ Restructure Cross-Directory Import
**Issue:** `scripts/image_describer.py` imports from `imagedescriber/ai_providers.py`

**Options:**
- **Option A:** Move `ai_providers.py` to `shared/ai_providers.py`
- **Option B:** Move `ai_providers.py` to `scripts/ai_providers.py`
- **Option C:** Keep as-is but document the rationale

**Recommendation:** Option A - `ai_providers` is shared infrastructure

### 3. ⚠️ Consolidate Duplicate EXIF Logic
**Evidence:**
- `metadata_extractor.py` has EXIF reading
- `image_describer.py` also reads EXIF (PIL.ExifTags)
- `combine_workflow_descriptions.py` has its own EXIF date logic
- `exif_embedder.py` has EXIF writing

**Recommendation:** Create `shared/exif_utils.py` in Phase 3

### 4. ⚠️ Consolidate File Discovery Logic
**Duplicate Patterns:**
- `workflow.py` has file discovery: `find_files_by_type()` via `FileDiscovery`
- `image_describer.py` has its own file scanning with `Path.glob()`
- Analysis scripts each scan for workflow directories

**Recommendation:** Create `shared/file_utils.py` in Phase 3

### 5. ✅ Remove Deprecated Qt6 Files
After wx migration is verified stable (all 5 apps working):

**Files to delete:**
- `imagedescriber/dialogs.py` (PyQt6 version)
- `imagedescriber/worker_threads.py` (PyQt6 version)
- `imagedescriber/ui_components.py` (PyQt6 version)
- `prompt_editor/prompt_editor.py` (PyQt6 version)
- `idtconfigure/idtconfigure.py` (PyQt6 version)

**Impact:** ~1,500+ lines of deprecated code removed, reduced confusion

**Priority:** Medium - should do in Phase 2 or 3 after testing confirms wx stability

---

### 6. ✅ Document All 5 Applications
**Current Status:** All 5 wxPython GUI apps successfully migrated:
1. ✅ idt.exe - CLI dispatcher
2. ✅ imagedescriber.exe - Batch processing GUI
3. ✅ viewer.exe - Results browser with live monitoring  
4. ✅ prompteditor.exe - Template editor
5. ✅ idtconfigure.exe - Configuration management

**Shared Infrastructure:**
- All use `shared/wx_common.py` for common wxPython utilities
- Clean dependency pattern (no cross-imports between GUI apps)
- Each has its own .spec file for independent builds

---

## Visual Dependency Tree (Complete - All 5 Apps)

```
═══════════════════════════════════════════════════════════════════
ENTRY POINT 1: idt.exe (CLI Dispatcher)
═══════════════════════════════════════════════════════════════════
idt.exe
├── idt_runner.py
│   └── idt_cli.py (command router)
│       ├── Routes to scripts/
│       │   ├── workflow.py
│       │   │   ├── workflow_utils.py
│       │   │   ├── image_describer.py
│       │   │   │   ├── metadata_extractor.py
│       │   │   │   ├── ConvertImage.py
│       │   │   │   └── imagedescriber/ai_providers.py ⚠️ cross-directory
│       │   │   ├── config_loader.py
│       │   │   ├── versioning.py
│       │   │   └── (spawns subprocesses)
│       │   │       ├── video_frame_extractor.py
│       │   │       ├── ConvertImage.py
│       │   │       ├── image_describer.py
│       │   │       └── descriptions_to_html.py
│       │   ├── stats_analysis.py
│       │   │   └── analysis_utils.py
│       │   ├── content_analysis.py
│       │   │   └── analysis_utils.py
│       │   ├── combine_workflow_descriptions.py
│       │   │   └── analysis_utils.py
│       │   ├── guided_workflow.py
│       │   │   └── config_loader.py
│       │   └── [12 other standalone scripts]
│       └── Routes to GUI apps (launches as subprocesses)
│           ├── viewer.exe
│           ├── imagedescriber.exe
│           ├── prompteditor.exe
│           └── idtconfigure.exe

═══════════════════════════════════════════════════════════════════
ENTRY POINT 2: imagedescriber.exe (Batch Processing GUI)
═══════════════════════════════════════════════════════════════════
imagedescriber.exe
├── imagedescriber_wx.py (main frame - 883 lines)
│   └── shared/wx_common.py ✅
├── dialogs_wx.py (settings, preferences)
│   └── shared/wx_common.py ✅
├── workers_wx.py (background AI processing)
├── ai_providers.py (shared with CLI)
└── [deprecated Qt6 files - can remove]
    ├── dialogs.py ❌
    ├── worker_threads.py ❌
    └── ui_components.py ❌

═══════════════════════════════════════════════════════════════════
ENTRY POINT 3: viewer.exe (Results Browser GUI)
═══════════════════════════════════════════════════════════════════
viewer.exe
├── viewer_wx.py (main frame)
│   └── shared/wx_common.py ✅
└── custom_accessible_listbox_viewer.py (accessible widget)

═══════════════════════════════════════════════════════════════════
ENTRY POINT 4: prompteditor.exe (Template Editor GUI)
═══════════════════════════════════════════════════════════════════
prompteditor.exe
├── prompt_editor_wx.py (main frame)
│   └── shared/wx_common.py ✅
└── [deprecated Qt6 file]
    └── prompt_editor.py ❌

═══════════════════════════════════════════════════════════════════
ENTRY POINT 5: idtconfigure.exe (Config Management GUI)
═══════════════════════════════════════════════════════════════════
idtconfigure.exe
├── idtconfigure_wx.py (main frame)
│   └── shared/wx_common.py ✅
└── [deprecated Qt6 file]
    └── idtconfigure.py ❌

═══════════════════════════════════════════════════════════════════
SHARED INFRASTRUCTURE (Used Across Apps)
═══════════════════════════════════════════════════════════════════
shared/
├── wx_common.py (all 5 GUI apps) ✅
└── [accessible widget components]

imagedescriber/
└── ai_providers.py (used by CLI + GUI) ⚠️

scripts/
├── workflow_utils.py (workflow orchestration)
├── config_loader.py (configuration loading)
├── metadata_extractor.py (EXIF extraction)
└── ConvertImage.py (image optimization)

models/
├── model_registry.py (model metadata)
└── provider_configs.py (provider capabilities)

analysis/
└── analysis_utils.py (shared analysis utilities)
```

**Legend:**
- ✅ = Correct shared utility usage
- ⚠️ = Cross-directory dependency (needs attention)
- ❌ = Deprecated Qt6 file (can be removed)

---

## Phase 1 Deliverable Status
✅ **Step 1.1 Complete:** Module dependency map created

**Next Step:** Proceed to Step 1.2 - Identify Duplicate Code

