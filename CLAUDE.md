# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Image Description Toolkit (IDT) is an AI-powered batch image/video description tool with two standalone applications:
- **`idt`** — CLI dispatcher (`idt/idt_cli.py`) routing to all sub-commands
- **`ImageDescriber`** — wxPython batch processing GUI (`imagedescriber/imagedescriber_wx.py`) with integrated viewer (`viewer_components.py`), chat (`chat_window_wx.py`), workspace manager (`workspace_manager.py`), prompt editor, and configuration manager

Supported AI providers: Ollama (local/cloud), OpenAI GPT-4o, Claude (Anthropic), HuggingFace Florence-2.

## Commands

### Testing
```bash
pytest pytest_tests/
python run_unit_tests.py        # Python 3.13-compatible alternative
pytest --cov=scripts pytest_tests/
pytest -m unit pytest_tests/   # markers: slow, integration, unit, regression
```

### Building (Windows)
```batch
BuildAndRelease\WinBuilds\builditall_wx.bat   # both apps
cd idt && build_idt.bat                        # CLI only
cd imagedescriber && build_imagedescriber_wx.bat
```

### Building (macOS)
```bash
./BuildAndRelease/MacBuilds/builditall_macos.command   # both apps
cd imagedescriber && ./build_imagedescriber_wx.sh
```

### Smoke Testing After Build
```bash
dist/idt.exe version          # Windows
dist/idt.exe --debug-paths
./dist/idt version            # macOS
```

### Syntax Validation
```bash
python -m py_compile <file>
```

## Architecture

### Dual Execution Model
All code must support both modes:
- **Development**: `python scripts/workflow.py`
- **Production**: PyInstaller frozen executables (`idt.exe workflow`)
- **Detection**: `getattr(sys, 'frozen', False)`
- **Paths**: Always use `config_loader.py` or `resource_manager.py`, never raw `Path()` or `open()` for config files

### Core Workflow Pipeline (`scripts/workflow.py`, 2468 lines)
Four sequential steps:
1. Video extraction → `video_frame_extractor.py`
2. HEIC conversion → `ConvertImage.py`
3. AI description → `image_describer.py`
4. HTML output → `descriptions_to_html.py`

Output directories: `wf_YYYY-MM-DD_HHMMSS_{model}_{prompt}`

### Configuration Resolution Order (`scripts/config_loader.py`)
1. Explicit path from caller
2. File environment variable (e.g., `IDT_IMAGE_DESCRIBER_CONFIG`)
3. `IDT_CONFIG_DIR` env var + filename
4. Frozen exe dir + `/scripts/<filename>` or `/<filename>`
5. Current working directory → bundled script dir (fallback)

### AI Model Registry (Single Source of Truth)
All model lists live in `models/`:
- `models/claude_models.py` — Claude versions (latest: claude-opus-4-6, claude-haiku-4-5-20251001)
- `models/openai_models.py` — OpenAI models (latest: gpt-4o, gpt-4o-mini, o1)
- `models/model_registry.py` — central metadata
- `models/provider_configs.py` — dynamic UI capabilities (`supports_prompts()`, `supports_custom_prompts()`)

Imported by CLI, GUI, and chat features. Never duplicate model lists elsewhere.

### Key Shared Utilities
- `scripts/list_results.py` — `find_workflow_directories()`, `count_descriptions()`, `format_timestamp()`, `parse_directory_name()`
- `scripts/workflow_utils.py` — `save_workflow_metadata()`, `load_workflow_metadata()` for `workflow_metadata.json` in each workflow dir
- `analysis/combine_workflow_descriptions.py` — `get_image_date_for_sorting()` (EXIF priority order)
- `shared/wx_common.py` — wxPython helpers
- `scripts/workflow.py` — `sanitize_name()` for filesystem-safe names

## Critical Rules

### PyInstaller Frozen Mode Imports
`from scripts.X`, `from imagedescriber.X`, `from analysis.X` **always fail in frozen mode**. Use:
```python
# At module level — NOT inside functions
try:
    from config_loader import load_json_config   # frozen mode
except ImportError:
    from scripts.config_loader import load_json_config  # dev mode
```

### wx Silent Failures
wxPython **swallows all exceptions** in event handlers. When a button/menu/handler silently does nothing, run in dev mode first:
```bash
cd imagedescriber && .winenv/Scripts/python imagedescriber_wx.py   # Windows
cd imagedescriber && python imagedescriber_wx.py                    # macOS
```
Reproduce the action — the exception prints to stderr immediately. Do not investigate architecture before doing this.

**Instructive example (8 hours wasted, April 2026):** A commit moved `logger = logging.getLogger(__name__)` from module scope into `main()`. Every event handler calling `logger.info(...)` silently raised `NameError`. `on_close`, `on_process_single`, and all other handlers appeared to do nothing; Alt+F4 was broken. Fix: 1 line. Discovery time in dev mode: under 30 seconds.

### Before Any Code Change
1. `grep -r "name"` to find ALL usages before renaming/changing signatures
2. Check all callers — incomplete refactors caused 23% of commits to be bug fixes
3. Verify PyInstaller compatibility with try/except import pattern
4. Functions >500 lines require extra scrutiny

### After Core File Changes
For changes to `scripts/workflow.py`, `scripts/image_describer.py`, `idt/idt_cli.py`, or any file listed in `hiddenimports` in the per-app `.spec` files (e.g., `imagedescriber/imagedescriber_wx.spec`, `idt/idt.spec`):
1. `python -m py_compile <file>`
2. Build the exe
3. Run with test data: `dist\idt.exe workflow testimages`
4. Check `wf_*/logs/*.log` for errors
5. Only then claim the fix is complete

### When Something Regresses
1. `git log v<tag>..HEAD --oneline -- <file>` to find the breaking commit
2. Run in dev mode, reproduce, read the exception
3. Only then look at architecture

## Conventions

### Virtual Environment
Windows virtual env uses `.winenv` (dot prefix), not `winenv`:
```batch
call .winenv\Scripts\activate.bat   ✓
call winenv\Scripts\activate.bat    ✗
```

### Date/Time Format
`M/D/YYYY H:MMP` — no leading zeros, A/P suffix. Examples: `3/25/2025 7:35P`, `10/16/2025 8:03A`.

EXIF priority: `DateTimeOriginal` > `DateTimeDigitized` > `DateTime` > file mtime.

### Window Titles
Always show stats: `"XX%, X of Y images described"`. Live mode adds `"(Live)"` suffix.

### Accessibility (WCAG 2.2 AA)
- Use `wx.ListBox` instead of `wx.ListCtrl` (single tab stop)
- Set `name=` parameter in widget constructors for screen reader labels
- `wx.ListBox` items: concatenate data into single strings (no multi-column)

### Session Summaries
Create `docs/WorkTracking/YYYY-MM-DD-session-summary.md` for non-trivial sessions. Include: files changed, decisions, test results, what was NOT tested.

## Additional Reference
- `docs/DEVELOPER_GUIDE.md` — comprehensive developer guide (architecture, `idt_core` inventory, CLI commands, build system, testing, conventions)
- `.github/copilot-instructions.md` — full agent guidelines and protocols
- `docs/WorkTracking/PRE_COMMIT_VERIFICATION_CHECKLIST.md` — pre-commit checklist
- `BuildAndRelease/BUILD_SYSTEM_REFERENCE.md` — build troubleshooting
