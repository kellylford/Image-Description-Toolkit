# Session Summary — 2026-06-30

## Focus
Consistent image-handling model across CLI and GUI: copy-vs-reference as an
explicit option (default off), bundle folders mirroring source structure, and a
design document capturing the full lifecycle.

## Design work
- **New:** [`docs/design/image-handling-lifecycle.md`](../design/image-handling-lifecycle.md)
  — lifecycle from "user gives a directory" to "done"; three-folder model
  (`images/` copy, `derived/` convert/extract, `embedded/` embed); the copy
  option; resolved decisions (§9); deferred items (cleanup/duplication,
  portable-bundle export).
- **Amended:** [`docs/design/unified-workspace.md`](../design/unified-workspace.md)
  — added a "superseded on image copying" banner pointing to the lifecycle doc.
  Its copy-by-default / flat-naming statements are no longer current; manifest,
  sidecar, chat, and migration sections remain accurate.

### Decisions locked this session
1. Copy originals is **off by default** for both CLI and GUI.
2. `images/`, `derived/`, `embedded/` **mirror source subfolder structure** (as
   `descriptions/` already does); the flat `Day2__beach.jpg` collision scheme is retired.
3. The copy setting is **stored per-workspace** in `manifest.json`, seeded from
   user config at creation, overridable per run.
4. GUI copying reuses the **existing batch-progress experience**.
5. Missing referenced originals: **skip + report count**; grey out in GUI. No prompt.

## Code changes
| File | Change |
|---|---|
| `idt_core/config.py` | `UserConfig.copy_originals` (default False); load/save in `~/.idt/config.json` |
| `idt_core/workspace.py` | per-workspace `copy_originals` (manifest); `add_image`/`add_source_folder` `copy` param; reference mode; mirrored `images/`; `_unique_image_name` + `_image_copy_path` replace `_bundle_name_for`; mirror-aware `image_path` |
| `idt_core/pipeline.py` | queue **skips missing-on-disk items** and marks `is_missing` (single source of truth) |
| `idt_core/exporter.py` | report `<img src>` via `image_path()` + relative-path calc (works for copy and reference) |
| `idt_core/gui_bridge.py` | threads copy flag into `add_image`; records `copy_originals` in manifest |
| `cli/main.py` | `--copy-originals` / `--no-copy-originals`; seed new ws from config; frames added as reference (no dup into `images/`); missing count in pre-run + summary; "Copy mode:" line |
| `imagedescriber/dialogs_wx.py` | ProcessingOptionsDialog "Copy original images into the workspace" checkbox; in `get_config()` |
| `imagedescriber/imagedescriber_wx.py` | `_resolve_copy_originals()`; both bundle-save paths honor it; persist choice in `_persist_processing_options` |
| `pytest_tests/unit/test_workspace_bundle.py` | updated to new default (reference) + mirrored naming; added reference-default, mirrored-naming, copy_originals-persist assertions |

## Testing
- `py_compile` on all changed files. **244/244 unit tests pass.**
- **End-to-end with real Ollama:**
  - Copy mode: `images/` mirrors nested structure (`Day1/beach.jpg`, `Day2/beach.jpg`), manifest `copy_originals: true`.
  - Default = reference: `images/` empty, `image_path()` → originals.
  - Per-workspace memory: re-running a copy workspace with no flag stays copy.
  - Missing original (reference): re-run with `--redescribe` → `1 described`, **no error**, "Skipped 1 missing" reported.
- Exporter emits correct relative `img src` for copy (`../images/Day2/beach.jpg`) and reference (`../../src/Day2/beach.jpg`).
- Headless wx: `ProcessingOptionsDialog` constructs; checkbox default reads config / falls back to UserConfig; `get_config()` returns `copy_originals`.
- `gui_bridge` copy/reference both verified (manifest flag + `images/` population).

## GUI-as-CLI-layer (`--showgui`)
- **New design doc:** [`docs/design/gui-as-cli-layer.md`](../design/gui-as-cli-layer.md)
  — "the GUI is part of the CLI once invited in"; Move 1 (launcher, done) vs Move 2
  (engine unification — retire the GUI's parallel `BatchProcessingWorker` loop and
  `ImageWorkspace`/`gui_bridge` in favour of `WorkspacePipeline` + `idt_core.Workspace`).
- **Move 1 implemented:** `idt describe <dir> --showgui` launches the ImageDescriber
  GUI on the directory, auto-starts the batch with the run's options, shows live
  progress, and the CLI waits on it (closing the GUI ends the command).
  - `cli/main.py`: `--showgui` flag; `_resolve_gui_launch()` (frozen sibling exe / dev
    script) + `_launch_gui_describe()` (forwards provider/model/prompt/geocode/copy);
    early hand-off in `cmd_describe` (no double execution).
  - `imagedescriber_wx.py`: `main()` gains `--autostart/--provider/--model/--prompt/`
    `--geocode/--copy-originals`; `autostart_batch()`; `on_process_all(preset_options=)`
    threads through the scan-defer + `on_scan_complete`, bypassing the save prompt
    (silent `_auto_save_bundle`) and the options dialog.
- **Verified end-to-end (real launch, timeout-capped):** log shows `autostart_batch`
  → deferred resume → silent bundle save → options dialog skipped → 2 images queued;
  bundle created at `~/Documents/idt/guitest.idtw` with mirrored sidecars, `storage:
  reference`, `copy_originals: false`, and **both images actually described**.

## NOT tested / follow-ups
- **Full GUI not driven interactively.** Dialog constructed headlessly, but the
  save-after-batch flow with the checkbox should be run once in dev mode
  (`cd imagedescriber && .winenv/Scripts/python imagedescriber_wx.py`) since wx
  swallows event-handler exceptions.
- **No exe build/run this session.** Core files changed that are in the `.spec`
  hiddenimports (`workspace.py`, `pipeline.py`, `cli/main.py`); a Windows build +
  `dist/idt.exe describe testimages` smoke test is still owed before release.
- **Deferred by design:** cleanup/de-duplication model for copy mode; portable
  bundle export (`idt package`); per-workspace-vs-config precedence UI in a GUI
  settings dialog (currently config file + per-run checkbox only).
