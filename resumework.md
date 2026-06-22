# v4.5 — Resume Work Document

*For AI agents picking up this branch. Read this + CLAUDE.md + docs/DEVELOPER_GUIDE.md before touching anything.*

---

## What This Branch Is

`v4.5` is a ground-up rewrite of the CLI layer. `main` still exists as the pre-v4.5 source of truth and should not be merged from — the two branches have diverged intentionally. At some point `main` will likely be renamed as a historical archive.

The central architectural change: a shared `idt_core/` library that both the CLI (`idt`) and the GUI (`ImageDescriber`) read and write. The on-disk artifact is now a `.idtw` workspace bundle — a self-contained directory with a `manifest.json`, source images, descriptions, embedded outputs, derived files, reports, and logs.

---

## What Was Done This Session (June 2026)

### New features / fixes landed (all committed, pushed to origin/v4.5)

| Area | What changed |
|------|-------------|
| Default model | Switched from moondream → **minicpm-v4.6** throughout. moondream was hallucinating ("ice") on blue/purple stage lighting at 1.8B scale. minicpm-v4.6 is 2× faster than llava, works on ARM Windows (Qualcomm Adreno X1-85), and is more honest about bad images. |
| Default model centralization | `scripts/image_describer_config.json` `"default_model"` is the single source of truth. `idt_core/config.py` exports `DEFAULT_OLLAMA_MODEL`; every other Python file imports the constant. Changing the JSON cascades everywhere automatically. |
| Pre-build validation | `tools/pre_build_validation.py` now has `check_default_model_sync()` — it reads the JSON and the installer and fails the build if they disagree. |
| Workspace path | Default bundle location is `~/Documents/idt/<leaf-name>.idtw` (e.g., `06.idtw`), not a full mirrored path. Function: `_mirror_source_path()` in `cli/main.py`. |
| CLI command logging | When `guideme` calls `cmd_describe`, `sys.argv` is still `["idt", "guideme"]`. Fixed by passing `_command_parts` through the `SimpleNamespace` args so the logged command shows the full describe invocation. |
| HEIC embed fix | HEIC files cannot hold JPEG-style metadata. The embedder now checks `is_heic()`, reads the pre-converted JPEG from `derived/converted/`, and writes to a `.jpg` path in `embedded/`. |
| Guideme model pull | If the user picks a model not installed in Ollama, guideme offers to pull it via `ollama pull`. |
| Documentation | Deleted ~280 pre-v4.5 docs (archive/, WorkTracking session logs, code_audit/, old release notes). Added `docs/DEVELOPER_GUIDE.md` (450 lines, v4.5 architecture). |
| Branch cleanup | Deleted: `1.0release`, `3.5release`, `40beta1`, `release/v3.0`, `release/3.6.0`, `v4beta2release`, `PeopleIdentification`. Remaining: `main`, `v4.5`. |

### Commits this session
- `bcf0e30` — functional changes (model, embed fix, guideme, workspace path, CLI logging)
- `b96ebc8` — docs cleanup + DEVELOPER_GUIDE.md

---

## Current State

### What works (tested)
- `idt guideme` end-to-end with Ollama/minicpm-v4.6 on Windows ARM
- `idt describe` on a .idtw bundle
- `idt embed` with JPEG images (HEIC path fixed but not re-tested post-fix)
- Workspace bundle created at `~/Documents/idt/<leaf>.idtw`
- Pre-build validation including model sync check

### What has NOT been tested since last changes
- `idt embed` end-to-end with HEIC source files (fix is in, not smoke-tested)
- GUI (ImageDescriber) with the new minicpm-v4.6 default — config loads from JSON so it should be fine, but not verified
- Mac build
- Full `idt workflow` pipeline end-to-end
- The logged CLI command appearing correctly in workspace artifacts after the `_command_parts` fix

### Known environment facts
- **User hardware**: Qualcomm Snapdragon X, Adreno X1-85, Windows 11 ARM, Ollama 0.30.10
- **Ollama architecture limitation**: `mllama` (llama3.2-vision) does NOT work on this hardware. minicpm-v4.6 and llava work fine.
- **`IDT_CONFIG_DIR`** env var is set to `C:\idt\scripts` (the installed exe's scripts dir). Dev runs pick this up; it points to the installed copy of `image_describer_config.json`, not the repo copy. Keep this in mind when testing config changes — you may need to copy the updated JSON to `C:\idt\scripts\` or unset the env var.
- **Virtual env**: `.winenv` (dot prefix) on Windows. `call .winenv\Scripts\activate.bat`
- **Build**: PowerShell, not bash, for the build bat files. `& ".winenv\Scripts\activate.ps1"` then `pyinstaller --clean --noconfirm idt.spec`

---

## Testing Plan (User's Intent)

1. **CLI first** — Kelly will use `idt guideme` and other CLI commands against real photo directories and report bugs. Fix issues until CLI is solid.
2. **GUI second** — Switch to ImageDescriber, same approach. Drive to closure.
3. **Mac third** — Repeat on macOS. Build, smoke test, find issues, close them.

### Things to watch for during CLI testing
- HEIC files going through embed — verify `embedded/` has `.jpg` files, not broken HEICs
- Logged CLI command in workspace metadata — open `manifest.json` or the log and verify it shows `idt describe ...` not `idt guideme`
- Workspace created at `~/Documents/idt/<leaf>.idtw` not a deep mirrored path
- Model not installed → pull prompt → model works after pull
- `idt embed` on a bundle that has descriptions — verify metadata visible in Windows Explorer file properties (Details tab → Comments or Subject)

### Things to watch for during GUI testing
- `imagedescriber_wx.py` has multiple `self.config.get('default_model', DEFAULT_OLLAMA_MODEL)` calls — they all import `DEFAULT_OLLAMA_MODEL` from `idt_core.config` now, so if config load fails the fallback is correct. Verify the model shown in the GUI matches minicpm-v4.6.
- wx silent failures: if a button does nothing, run in dev mode (`cd imagedescriber && .winenv\Scripts\python imagedescriber_wx.py`) and reproduce — exception will print to stderr immediately.

---

## Key Files Quick Reference

| File | Purpose |
|------|---------|
| `scripts/image_describer_config.json` | **Change `"default_model"` here** to switch default Ollama model. All Python picks it up at import time. |
| `BuildAndRelease/WinBuilds/installer.iss` | **Only other file to update** when changing default model (the `ollama pull` line). Pre-build validation catches mismatch. |
| `idt_core/config.py` | Exports `DEFAULT_OLLAMA_MODEL`, `BUILT_IN_PROMPTS`, `DEFAULT_PROMPT_NAME`, `UserConfig` |
| `idt_core/workspace.py` | `Workspace` class — open/create/save .idtw bundles |
| `cli/main.py` | All `idt` subcommands (`cmd_describe`, `cmd_embed`, `_do_embed_workspace`, etc.) |
| `cli/guide.py` | `guideme` wizard — interactive walk-through for new users |
| `imagedescriber/imagedescriber_wx.py` | Main GUI application |
| `tools/pre_build_validation.py` | Run before building — checks imports, scanner, default provider, model sync |
| `docs/DEVELOPER_GUIDE.md` | Full v4.5 architecture reference |
| `CLAUDE.md` | Coding conventions, critical rules, build commands |
