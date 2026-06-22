# Image Description Toolkit v4.5 — Developer Guide

## Architecture Overview

IDT is a dual-app suite built on a shared library:

- **`idt`** — CLI tool at `cli/main.py` with 13 commands (describe, embed, watch, combine, export, etc.)
- **`ImageDescriber`** — wxPython GUI batch processor at `imagedescriber/imagedescriber_wx.py`
- **`idt_core`** — Shared library: configuration, workspace, image/video detection, AI provider interface, embedder, exporter

Both apps open and write the same `.idtw` bundle format. Users' source images are never modified — copies are stored in the bundle with full provenance.

### Supported AI Providers

- Ollama (local/cloud models: llama3.2-vision, qwen2-vl, llava, etc.)
- OpenAI (GPT-4o, GPT-4o-mini)
- Anthropic Claude (claude-opus-4-6, claude-haiku-4-5-20251001)
- HuggingFace Florence-2

### Dual Execution Model

All code must support two modes:

1. **Development**: `python cli/main.py describe ...` or `python imagedescriber/imagedescriber_wx.py`
2. **Production**: PyInstaller frozen executables (`idt.exe` on Windows, `./idt` on macOS)

Detection: `getattr(sys, 'frozen', False)`

**Critical import pattern for PyInstaller compatibility** (applies to `idt_core`, `cli`, `imagedescriber` modules):

```python
# At module level — NOT inside functions
try:
    from config_loader import load_json_config   # frozen mode
except ImportError:
    from scripts.config_loader import load_json_config  # dev mode
```

## `idt_core` Module Inventory

### `config.py`

Central configuration system shared across CLI, GUI, and workspace.

**`UserConfig` class:**
- `default_provider` — "ollama", "anthropic", "openai", "florence"
- `default_model` — model name for the provider
- `default_prompt_name` — built-in prompt key ("narrative", "detailed", etc.)
- `custom_prompts` — user-defined prompt overrides
- `workspace_root` — custom workspace location (defaults to `~/Documents/idt`)

**Methods:**
- `UserConfig.load()` — read from `~/.idt/config.json`
- `.save()` — write configuration
- `.get_prompt_text(name)` — resolve a prompt by name (custom overrides built-ins)
- `.list_prompts()` — all available prompts

**Module-level constants** (loaded once at import from `scripts/image_describer_config.json`):
- `BUILT_IN_PROMPTS` — dict of prompt name → text
- `DEFAULT_PROMPT_NAME` — default prompt key
- `DEFAULT_OLLAMA_MODEL` — fallback Ollama model (e.g., "llama3.2-vision")

### `workspace.py`

The `.idtw` bundle — a self-contained directory holding images, descriptions, chats, and metadata.

**Core classes:**

- **`WorkspaceDescription`** — one AI-generated description with provider/model/prompt metadata, token counts, UUID, and timestamp. Supports tool-specific `extra` fields for lossless round-trips.

- **`WorkspaceItem`** — one image in the bundle:
  - `image` — filename in `images/` subdirectory (the primary key)
  - `source_path` — original absolute path (provenance only)
  - `descriptions` — list of `WorkspaceDescription`
  - `active_description_id` — which description is currently selected
  - `exif_datetime`, `file_mtime` — EXIF priority: DateTimeOriginal > DateTimeDigitized > DateTime > mtime
  - `metadata`, `tags`, `notes` — user annotations
  - `embedded_at` — timestamp of last embed-to-image operation
  - `extra` — tool-specific fields (e.g., GUI batch state)

- **`Workspace`** — the bundle itself:
  - `.idtw/manifest.json` — format version, name, created/modified timestamps, defaults, CLI command history
  - `.idtw/images/` — copies of source images (collision-safe names)
  - `.idtw/descriptions/` — JSON sidecars, one per image
  - `.idtw/chats/` — chat session JSON files
  - `.idtw/derived/` — generated artifacts (frames/, converted/, etc.)
  - `.idtw/logs/` — operation logs

**Key methods:**
- `Workspace.create(path)` — create new bundle
- `Workspace.open(path)` — open existing or create if missing
- `.add_image(source_path)` — copy image into bundle (idempotent)
- `.add_source_folder(folder, recursive=True)` — batch scan and add
- `.items()` — list all `WorkspaceItem` in the bundle
- `.status()` — quick stats (total, described, undescribed)

### `scanner.py`

Image and video detection without descending into `.idt*` or hidden directories.

- `scan_images(directory, include_videos=False)` — recursive generator of supported media paths
- `is_image(path)`, `is_video(path)` — extension checks
- `IMAGE_EXTENSIONS`, `VIDEO_EXTENSIONS` — frozensets of supported types (JPEG, PNG, WebP, TIFF, HEIC/HEIF, GIF, BMP, MP4, MOV, AVI, MKV, etc.)

### `providers/` — AI Provider Interface

Base provider signature at `providers/base.py`:

```python
class BaseProvider:
    @property
    def provider_name(self) -> str: ...        # "ollama", "anthropic", etc.
    
    @property
    def model_name(self) -> str: ...           # "gpt-4o", "llama3.2-vision", etc.
    
    def describe(self, image_bytes: bytes, mime_type: str, prompt: str) -> DescriptionResult:
        """Return DescriptionResult(text, model, provider, tokens, etc.)"""
    
    def list_models(self) -> list[str]:        # available models for this provider
```

**Implementations:**
- `ollama.py` — connects to `http://localhost:11434`
- `openai_provider.py` — reads `OPENAI_API_KEY` from environment
- `claude.py` — reads `ANTHROPIC_API_KEY`
- `florence.py` — local HuggingFace model

### `embedder.py`

Embeds AI descriptions into image EXIF metadata (PNG/JPEG) and metadata sidecar files.

- `EmbedStrategy` — target location for embed (image file, sidecar, etc.)
- `embed_descriptions(workspace, item_ids, strategy)` — applies descriptions to images

### `exporter.py`

Exports workspace to HTML (with gallery, search, EXIF display, styling options).

- `export_workspace(workspace, output_path, formats)` — generates viewer HTML and optional data JSON

### `downloader.py`

Downloads images from URLs (used by `idt download` command).

### `pipeline.py`

Orchestrates the full describe pipeline: load images, call provider, save results.

### `video.py`

Extracts frames from video files using OpenCV.

### `metadata.py`

Reads and writes EXIF metadata (DateTimeOriginal, DateTimeDigitized, DateTime, custom tags).

### `converter.py`

Handles HEIC/HEIF → JPEG conversion for providers that don't support HEIC natively.

## `.idtw` Workspace Bundle Format

Location: User's workspace root (default: `~/Documents/idt/MyProject.idtw`)

```
MyProject.idtw/
├── manifest.json           # Bundle metadata (format version, created, defaults)
├── images/
│   ├── photo1.jpg
│   ├── vacation__photo2.png
│   └── IMG_001_1.heic      # Collision-safe names for duplicates
├── descriptions/
│   ├── photo1.jpg.json     # One sidecar per image
│   └── IMG_001_1.heic.json
├── chats/
│   └── chat_abc123.json    # Chat sessions not tied to images
├── derived/
│   ├── frames/             # Extracted video frames
│   └── converted/          # HEIC→JPEG conversions
└── logs/
    └── idt_describe_20250622.log
```

**manifest.json schema:**

```json
{
  "format": "idtw",
  "version": "1.0",
  "name": "MyProject",
  "created": "2025-06-22T15:30:00+00:00",
  "modified": "2025-06-22T15:35:00+00:00",
  "sources": [
    { "path": "/Users/kelly/Pictures", "recursive": true, "added": "2025-06-22T15:30:00+00:00" }
  ],
  "defaults": {
    "provider": "ollama",
    "model": "llama3.2-vision",
    "prompt_name": "detailed",
    "prompt_text": ""
  },
  "has_any_descriptions": true,
  "batch_state": { ... },
  "cached_ollama_models": [ "llama3.2-vision", "qwen2-vl" ],
  "geocode_enabled": false,
  "cli_commands": [
    { "command": "idt describe . --model gpt-4o", "timestamp": "2025-06-22T15:30:00+00:00" }
  ]
}
```

**description sidecar schema:**

```json
{
  "image": "photo1.jpg",
  "source_path": "/absolute/path/to/original.jpg",
  "storage": "copy",
  "item_type": "image",
  "descriptions": [
    {
      "id": "uuid-abc123",
      "text": "A sunny beach scene with...",
      "provider": "ollama",
      "model": "llama3.2-vision",
      "prompt_name": "detailed",
      "prompt_text": "Describe this image...",
      "created": "2025-06-22T15:30:00+00:00",
      "input_tokens": 500,
      "output_tokens": 150,
      "metadata_context": "..."
    }
  ],
  "active_description_id": "uuid-abc123",
  "exif_datetime": "2025-06-22T14:25:00",
  "embedded_at": "2025-06-22T15:32:00+00:00"
}
```

## CLI Command Surface

### Main Commands

- **`idt guideme`** — Interactive setup wizard (recommends models, API keys, workspace location)
- **`idt describe <directory> [--model X] [--prompt Y] [--provider Z]`** — Batch describe images in a workspace
- **`idt download <url> <workspace>`** — Download image(s) from URL into workspace
- **`idt status <workspace>`** — Show stats (total images, described count, undescribed)
- **`idt show <workspace|image>`** — Display workspace or individual image in viewer
- **`idt embed <workspace> [--deduplicate]`** — Embed descriptions into image EXIF metadata
- **`idt export <workspace> [--format html] [--output /path]`** — Export to HTML gallery
- **`idt watch <directory>`** — Monitor directory for new images and auto-describe
- **`idt combine <directory> [--output report.html]`** — Merge descriptions from multiple workflow runs
- **`idt video <directory> [--fps N] [--format jpg]`** — Extract frames from video files
- **`idt models [--provider NAME]`** — List available models (local Ollama or cloud API)
- **`idt prompts`** — List all available prompts
- **`idt config [--set key=value]`** — View or modify user configuration

Implementation: `cli/main.py` (command dispatcher), `cli/guide.py` (wizard)

## Changing the Default Model

Default model is loaded **once at import time** from `scripts/image_describer_config.json`:

```json
{
  "default_model": "llama3.2-vision",
  "default_prompt_style": "detailed",
  "prompt_variations": { ... }
}
```

**To change the default across all surfaces (CLI + GUI):**

1. Edit `scripts/image_describer_config.json` → set `"default_model"` to your choice
2. Edit `BuildAndRelease/WinBuilds/installer.iss` → update the bundled config in the installer (search for `[InstallDelete]` section)
3. Rebuild the executables

**All Python code picks up the new default automatically** — no code changes needed. The pre-build validation script (`tools/pre_build_validation.py`) checks that the JSON is well-formed and the model is recognized.

## Model Registry

Central model lists live in `models/`:

- `models/claude_models.py` — Claude versions (latest: claude-opus-4-6, claude-haiku-4-5-20251001)
- `models/openai_models.py` — OpenAI models (latest: gpt-4o, gpt-4o-mini, o1)
- `models/model_registry.py` — unified interface to query models by provider

**Never duplicate model lists elsewhere.** The CLI, GUI, and provider factory all import from these files.

## Build System

### PyInstaller Spec Files

- `idt/idt.spec` — CLI executable (13 commands powered by `cli/main.py` + `idt_core`)
- `imagedescriber/imagedescriber_wx.spec` — GUI executable

Both specs:
- Bundle `idt_core/` as importable package
- Include `scripts/image_describer_config.json` and `scripts/workflow_config.json`
- List provider dependencies (ollama, openai, anthropic, etc.) in `hiddenimports`
- On macOS, optionally include MLX libraries for on-device acceleration

### Windows Build

```batch
BuildAndRelease\WinBuilds\builditall_wx.bat   # both apps
cd idt && build_idt.bat                        # CLI only
cd imagedescriber && build_imagedescriber_wx.bat
```

### macOS Build

```bash
./BuildAndRelease/MacBuilds/builditall_macos.command   # both apps
cd imagedescriber && ./build_imagedescriber_wx.sh
```

### Smoke Test

```bash
dist/idt.exe version                          # Windows
./dist/idt version                            # macOS
dist/idt.exe --debug-paths                    # Show import resolution
```

### Post-Build Validation

The pre-build validation script (`tools/pre_build_validation.py`) ensures:
- Config JSON is well-formed
- Default model is recognized
- Required dependencies are installed
- No syntax errors in core files

## Testing

```bash
pytest pytest_tests/                      # run all tests
python run_unit_tests.py                  # Python 3.13-compatible runner
pytest --cov=scripts pytest_tests/        # coverage report
pytest -m unit pytest_tests/              # run tests by marker (unit/slow/integration/regression)
```

## Key Conventions & Gotchas

### PyInstaller Frozen Mode Imports

When working with `idt_core/`, `cli/`, or `imagedescriber/` modules:

```python
# Correct pattern
try:
    from config_loader import load_json_config          # frozen mode
except ImportError:
    from scripts.config_loader import load_json_config  # dev mode
```

Frozen-mode imports fail if you use `from scripts.X` — the `scripts/` directory is not on the path inside frozen exes.

### wxPython Silent Failures

**wxPython swallows all exceptions** in event handlers. A button click that does nothing probably raised an exception silently.

**When debugging GUI issues:**

1. Run in dev mode to see the exception:
   ```bash
   cd imagedescriber && .winenv/Scripts/python imagedescriber_wx.py   # Windows
   cd imagedescriber && python imagedescriber_wx.py                    # macOS
   ```
2. Reproduce the action (click the button, select menu, etc.)
3. The exception prints to stderr immediately
4. Fix and test again

Example: If a logger is initialized inside a function instead of at module level, all event handlers calling `logger.info(...)` silently fail with `NameError`. Discovery time in dev mode: under 30 seconds.

### Date Format

All timestamps use ISO 8601 format for JSON storage (`2025-06-22T15:30:00+00:00`).

When displaying to users, format as: **`M/D/YYYY H:MMP`** (no leading zeros, A/P suffix)
- ✓ `3/25/2025 7:35P`
- ✓ `10/16/2025 8:03A`
- ✗ `03/25/2025 19:35` (leading zeros, 24-hour format)

### EXIF Datetime Priority

Extract image EXIF date in this order:
1. `DateTimeOriginal` (preferred — captured time)
2. `DateTimeDigitized` (edited time)
3. `DateTime` (generic datetime)
4. File `mtime` (fallback)

See `metadata.py` for implementation.

### Virtual Environment (Windows)

On Windows, the virtual env directory uses a **dot prefix**: `.winenv`

```batch
call .winenv\Scripts\activate.bat   ✓ Correct
call winenv\Scripts\activate.bat    ✗ Wrong (ignores the dot)
```

### Window Titles (GUI)

Always show progress stats in window titles:

- `"45%, 45 of 100 images described"` — normal mode
- `"45%, 45 of 100 images described (Live)"` — live watch mode

### Configuration Resolution Order

When `idt_core.config` loads a config file:

1. Explicit path from caller
2. Environment variable (e.g., `IDT_IMAGE_DESCRIBER_CONFIG`)
3. `IDT_CONFIG_DIR` env var + filename
4. Frozen exe directory + `/scripts/<filename>` or `/<filename>`
5. Current working directory → bundled script directory (fallback)

See `scripts/config_loader.py` for full details.

### Before Any Code Change

1. **Find all usages** — `grep -r "name"` before renaming or changing signatures
2. **Check all callers** — incomplete refactors caused 23% of past bugs
3. **Verify PyInstaller compatibility** — test the frozen import pattern
4. **Extra scrutiny for functions >500 lines** — core files like `workspace.py` are complex

### After Core File Changes

For changes to `idt_core/`, `cli/main.py`, `imagedescriber/imagedescriber_wx.py`:

1. `python -m py_compile <file>` — syntax check
2. Build the executable
3. Run with test data: `dist\idt.exe describe testimages/`
4. Check logs in `wf_*/logs/` for errors
5. Only then claim the fix is complete

### When Something Regresses

1. Find the breaking commit: `git log v<tag>..HEAD --oneline -- <file>`
2. Run in dev mode, reproduce, read the exception
3. Only then look at architecture

## Additional Reference

- `CLAUDE.md` — AI agent guidelines, critical rules, and architecture principles
- `.github/copilot-instructions.md` — full agent protocols
- `docs/worktracking/PRE_COMMIT_VERIFICATION_CHECKLIST.md` — pre-commit checklist
- `BuildAndRelease/BUILD_SYSTEM_REFERENCE.md` — build troubleshooting
- `docs/archive/AI_AGENT_REFERENCE.md` — CLI reference, image optimization, provider limits
