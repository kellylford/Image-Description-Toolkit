# Entry Points Catalog - Phase 1, Step 1.3

**Date:** 2026-01-13  
**Status:** Complete  
**Scope:** All CLI commands + 5 GUI applications

---

## CLI Commands (idt_cli.py dispatcher)

**Dispatcher Location:** [`idt/idt_cli.py`](../../idt/idt_cli.py)

All commands are routed through the unified dispatcher which handles both:
- **Development Mode:** Subprocess execution (python script)
- **Frozen Mode:** Direct module import (PyInstaller executable)

### Workflow Commands

#### 1. `guideme` - Interactive Guided Workflow
**Purpose:** Interactive wizard to guide users through workflow setup  
**Script Called:** `scripts/guided_workflow.py`  
**Type:** Script-based with user prompts  
**Usage:** `idt guideme`

#### 2. `workflow` - Main Image Description Workflow
**Purpose:** Core workflow orchestrator (video→frames→conversion→descriptions→HTML)  
**Script Called:** `scripts/workflow.py`  
**Type:** Orchestrator (2,468 lines)  
**Default Output:** `Descriptions/wf_*` directory  
**Usage:** `idt workflow [images_dir] --provider [ollama|openai|claude] --model [model_name]`

**Calls:**
- `scripts/video_frame_extractor.py` - Extract frames from videos
- `scripts/ConvertImage.py` - Convert HEIC to JPG
- `scripts/image_describer.py` - Generate AI descriptions
- `scripts/descriptions_to_html.py` - Create HTML reports

---

### Analysis Commands

#### 3. `stats` - Workflow Performance Analysis
**Purpose:** Analyze workflow timing, costs, and performance metrics  
**Script Called:** `analysis/stats_analysis.py`  
**Type:** Analysis tool  
**Usage:** `idt stats --input-dir [workflow_dir]`

#### 4. `contentreview` - Description Quality Review
**Purpose:** Analyze description content and quality metrics  
**Script Called:** `analysis/content_analysis.py`  
**Type:** Analysis tool  
**Usage:** `idt contentreview --input-dir [workflow_dir]`

#### 5. `combinedescriptions` - Export to CSV/Excel
**Purpose:** Combine descriptions from multiple workflows, sorted by EXIF date  
**Script Called:** `analysis/combine_workflow_descriptions.py`  
**Type:** Export tool  
**Usage:** `idt combinedescriptions --input-dir [workflows_dir] --output results.csv`

#### 6. `results-list` - List Available Workflows
**Purpose:** List all workflow directories with descriptions/status  
**Script Called:** `scripts/list_results.py`  
**Type:** List utility  
**Usage:** `idt results-list --input-dir [descriptions_dir]`

#### 7. `prompt-list` - List Available Prompts
**Purpose:** List all available prompt styles  
**Script Called:** `scripts/list_prompts.py`  
**Type:** List utility  
**Usage:** `idt prompt-list [--verbose]`

---

### Support Commands

#### 8. `extract-frames` - Video Frame Extraction (Standalone)
**Purpose:** Extract frames from video without full workflow  
**Script Called:** `scripts/video_frame_extractor.py`  
**Type:** Utility  
**Usage:** `idt extract-frames [video_dir] [--config video_config.json]`

#### 9. `convert-images` - Image Format Conversion (Standalone)
**Purpose:** Convert HEIC/HEIF images to JPG  
**Script Called:** `scripts/ConvertImage.py`  
**Type:** Utility  
**Usage:** `idt convert-images [images_dir] --output [output_dir]`

#### 10. `descriptions-to-html` - HTML Generation (Standalone)
**Purpose:** Generate HTML reports from descriptions  
**Script Called:** `scripts/descriptions_to_html.py`  
**Type:** Utility  
**Usage:** `idt descriptions-to-html [descriptions_dir] [--output output.html]`

#### 11. `check-models` - Check Installed Models
**Purpose:** Verify Ollama models are available  
**Script Called:** `models/check_models.py`  
**Type:** Verification tool  
**Usage:** `idt check-models`

---

### GUI Application Launchers

#### 12. `viewer` (alias: `view`) - Workflow Results Browser
**Executable:** `viewer/viewer_wx.exe` (wxPython)  
**Deprecated:** `viewer/viewer.py` (PyQt6)  
**Entry Point:** [`viewer/viewer_wx.py`](../../viewer/viewer_wx.py) main()  
**Lines of Code:** 1,335  
**Features:**
- Browse workflow directories
- View image descriptions with previews
- Live monitoring of active workflows
- Copy to clipboard
- Redescribe images/workflows
- Resume incomplete workflows
**Usage:**
- `idt viewer` - Launch empty
- `idt viewer [workflow_dir]` - Open specific directory
- `idt viewer --open` - Directory picker dialog

#### 13. `prompteditor` - Prompt Template Editor
**Executable:** `prompt_editor/prompteditor_wx.exe` (wxPython)  
**Deprecated:** `prompt_editor/prompt_editor.py` (PyQt6)  
**Entry Point:** [`prompt_editor/prompt_editor_wx.py`](../../prompt_editor/prompt_editor_wx.py) main()  
**Lines of Code:** ~800  
**Features:**
- Visual prompt template editor
- Save/load custom prompts
- Test prompts with AI providers
- Template variables and formatting
**Usage:** `idt prompteditor`

#### 14. `imagedescriber` - Batch Image Processing GUI
**Executable:** `imagedescriber/imagedescriber_wx.exe` (wxPython)  
**Deprecated:** `imagedescriber/imagedescriber.py` (PyQt6)  
**Entry Point:** [`imagedescriber/imagedescriber_wx.py`](../../imagedescriber/imagedescriber_wx.py) main()  
**Lines of Code:** 2,289  
**Features:**
- Document-based workspace
- Batch image processing
- Multiple descriptions per image
- Video frame extraction support
- HEIC conversion integration
- Menu-driven keyboard navigation
- Full VoiceOver accessibility
**Usage:** `idt imagedescriber`

#### 15. `configure` (alias: `config`) - Configuration Manager
**Executable:** `idtconfigure/idtconfigure_wx.exe` (wxPython)  
**Deprecated:** `idtconfigure/idtconfigure.py` (PyQt6)  
**Entry Point:** [`idtconfigure/idtconfigure_wx.py`](../../idtconfigure/idtconfigure_wx.py) main()  
**Lines of Code:** ~1,200  
**Features:**
- Visual configuration editor
- AI provider settings
- Prompt management
- Workflow orchestration settings
- EXIF and metadata options
**Usage:** `idt configure`

---

### Utility Commands

#### 16. `version` (alias: `-v`, `--version`)
**Purpose:** Show version information  
**Script Called:** `scripts/versioning.py` module  
**Type:** Information  
**Output:** Version number, git commit, build mode (dev/frozen)  
**Usage:** `idt version`

#### 17. `help` (alias: `-h`, `--help`)
**Purpose:** Show help message  
**Type:** Information  
**Output:** Command list with usage examples  
**Usage:** `idt help`

---

## Workflow Chains (Call Graph)

### Main Workflow Chain
```
CLI: idt workflow [images] 
  └─→ scripts/workflow.py main()
      ├─→ scripts/workflow_utils.py (WorkflowConfig, FileDiscovery, WorkflowLogger)
      ├─→ scripts/video_frame_extractor.py (if videos present)
      │   └─→ scripts/video_frame_extractor_config.json
      ├─→ scripts/ConvertImage.py (if HEIC present)
      │   ├─→ ImageMagick/PIL
      │   └─→ scripts/exif_embedder.py (preserve EXIF)
      ├─→ scripts/image_describer.py
      │   ├─→ imagedescriber/ai_providers.py (Ollama, OpenAI, Claude, HuggingFace)
      │   ├─→ scripts/config_loader.py (load image_describer_config.json)
      │   └─→ imagedescriber/data_models.py (data classes)
      ├─→ scripts/descriptions_to_html.py
      │   └─→ scripts/description_utils.py
      ├─→ scripts/workflow_utils.py (create helper batch files)
      └─→ Output: wf_[timestamp]_[model]_[prompt] directory
          ├─── extracted_frames/ (if videos)
          ├─── converted_images/ (if HEIC)
          ├─── descriptions/ (text files)
          ├─── html_reports/
          ├─── logs/ (status.log, workflow_*.log, image_describer_*.log)
          ├─── view_results.bat
          ├─── resume_workflow.bat
          ├─── run_stats.bat
          └─── workflow_metadata.json
```

### Analysis Chain
```
CLI: idt combinedescriptions [workflows_dir]
  └─→ analysis/combine_workflow_descriptions.py main()
      ├─→ scripts/list_results.py (find_workflow_directories())
      ├─→ analysis/combine_workflow_descriptions.py (get_image_date_for_sorting)
      │   └─→ MetaData/enhanced_metadata_extraction.py (EXIF extraction)
      └─→ Output: CSV file with sorted image descriptions
```

### Viewer Chain
```
CLI: idt viewer [dir]
  └─→ viewer/viewer_wx.exe (subprocess launch)
      └─→ viewer/viewer_wx.py main()
          ├─→ shared/wx_common.py (UI helpers, config loading)
          ├─→ scripts/list_results.py (find_workflow_directories)
          ├─→ viewer/viewer_wx.py (get_image_date for sorting)
          └─→ Live monitoring: poll wf_*/logs/status.log
```

---

## GUI Application Architecture

All 5 GUI applications follow identical pattern:

```
[App Name]
├─── [app]_wx.py (wxPython - CURRENT)
│    ├─── Imports shared/wx_common.py
│    ├─── Handles frozen mode path resolution
│    └─── Full keyboard + screen reader support
├─── [app].py (PyQt6 - DEPRECATED)
│    └─── Legacy version - can be deleted
├─── build_[app]_wx.bat (Windows build)
├─── build_[app]_wx.sh (Linux/macOS build)
├─── [app]_wx.spec (PyInstaller spec - frozen build)
└─── requirements.txt (dependencies)
```

**Applications:**
1. `imagedescriber/` - Image description GUI
2. `viewer/` - Workflow results viewer
3. `prompt_editor/` - Prompt template editor
4. `idtconfigure/` - Configuration manager
5. `idt/` - CLI dispatcher (main entry point)

---

## Shared Infrastructure

**Location:** [`shared/`](../../shared/)

### Key Shared Modules
- **`shared/wx_common.py`** (909 lines) - Shared wxPython utilities
  - `SortedListBox` - Accessible list widget
  - `open_config_file_dialog()` - File picker with filtering
  - `sanitize_filename()` - Path/filename safety
  - `StatusDisplayFrame` - Progress display
  - Logging and error handling utilities

- **`scripts/config_loader.py`** - Configuration loading (frozen-mode safe)
  - Handles dev vs PyInstaller executable modes
  - Searches: explicit path → env var → config dir → bundled dir

- **`scripts/workflow_utils.py`** - Workflow utilities
  - `WorkflowConfig` - Parse workflow configurations
  - `WorkflowLogger` - Unified logging
  - `FileDiscovery` - File scanning utilities

---

## Command Categorization

| Category | Commands | Type |
|----------|----------|------|
| **Workflow** | guideme, workflow | Orchestrators |
| **Analysis** | stats, contentreview, combinedescriptions, results-list | Analysis tools |
| **GUI Apps** | viewer, prompteditor, imagedescriber, configure | Executables |
| **Utilities** | extract-frames, convert-images, descriptions-to-html | Standalone tools |
| **Information** | check-models, prompt-list, version, help | Information |

---

## Entry Points Summary

| Type | Count | Examples |
|------|-------|----------|
| CLI Commands | 17 | workflow, viewer, stats, etc. |
| GUI Applications | 5 | viewer, imagedescriber, prompteditor, idtconfigure, idt |
| Scripts Called | 15+ | workflow.py, image_describer.py, stats_analysis.py, etc. |
| Analysis Modules | 3 | stats_analysis.py, content_analysis.py, combine_descriptions.py |
| Shared Libraries | 3+ | wx_common.py, config_loader.py, workflow_utils.py |

---

## Files to Delete (Deprecated Qt6 Versions)

The following PyQt6 versions are deprecated and should be removed:

1. **`imagedescriber/imagedescriber.py`** (deprecated)
   - Replaced by: `imagedescriber/imagedescriber_wx.py`
   - Status: Dead code (~2,200 lines)

2. **`prompt_editor/prompt_editor.py`** (deprecated)
   - Replaced by: `prompt_editor/prompt_editor_wx.py`
   - Status: Dead code (~800 lines)

3. **`idtconfigure/idtconfigure.py`** (deprecated)
   - Replaced by: `idtconfigure/idtconfigure_wx.py`
   - Status: Dead code (~1,200 lines)

4. **`viewer/viewer.py`** (deprecated, if exists)
   - Replaced by: `viewer/viewer_wx.py`
   - Status: Dead code

**Total Deprecated Code:** ~1,500+ lines
**Safe to Delete:** YES - All wxPython versions are complete and tested
**Build Impact:** None - build scripts already use _wx versions

---

**Report Generated:** 2026-01-13  
**Phase:** Phase 1, Step 1.3 Complete  
**Next:** Phase 1, Step 1.4 - PyInstaller Concerns
