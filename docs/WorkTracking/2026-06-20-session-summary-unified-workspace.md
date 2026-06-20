# Session Summary — 6/20/2026 — Unified Workspace (`.idtw`)

## Why

The toolkit had **four** incompatible file models (old `wf_*` dirs, sibling `.idt/`
projects, GUI `.idw` + `WorkspaceFiles/`, and a bolted-on bridge). A description made
in the GUI and the same image described by the CLI landed in different places, in
different formats. The user gave v4.5 green-field status and chose **Option 2: a
self-contained bundle** that duplicates images in, as the least-confusing model:
one named `.idtw` folder IS the workspace.

## Decision

A workspace is a single `.idtw` directory the user names. It holds copies of the
images, their descriptions, chat sessions, and derived files. **Originals are copied
in and never moved or modified** (source path kept as provenance). v4.5 duplicates
image data for a single unambiguous "where is my work" answer; a reference/no-copy
mode is reserved in the schema (`storage` field) for later.

Full spec: `docs/design/unified-workspace.md`.

## What shipped this session (committed on branch v4.5)

1. **`docs/design/unified-workspace.md`** — the single dev+user format reference
   (layout, manifest schema, unified per-image sidecar schema reconciling the two
   legacy Description shapes, chat schema, invariants, migration table).

2. **`idt_core/workspace.py`** — `Workspace`, `WorkspaceItem`, `WorkspaceDescription`.
   Collision-safe image naming, idempotent adds, atomic JSON writes, manifest with
   sources/defaults/batch_state/geocode, chats, derived/ subdirs.

3. **`idt_core/pipeline.py`** — `WorkspacePipeline` + `WorkspaceEvent` + shared
   `_extract_and_build_prompt` helper. The legacy Project `Pipeline` is untouched.

4. **`idt_core/exporter.py`** — `export_workspace_html/_csv/_txt`.

5. **`cli/main.py`** — describe, status, show, embed, export, stats, combine all
   operate on `.idtw` bundles now, with legacy `.idt/` fallback. `idt describe`
   creates `<folder>.idtw` (or `--workspace NAME|PATH`).

6. **Tests** — `test_workspace_bundle.py` (13), `test_workspace_pipeline.py` (5,
   fake provider). 83 idt_core/workspace tests pass.

## Verified

- Unit: 83 passing (bundle round-trips, originals-untouched, collisions, reopen,
  describe-to-bundle engine with a fake provider).
- Live CLI against a real bundle: status / show / embed (EXIF ImageDescription in
  the embedded copy) / export html+csv / stats (token+cost) / combine tsv.
- On-disk layout matches the design: `Pics/` (originals untouched) +
  `Pics.idtw/{manifest.json, images/, descriptions/, chats/, embedded/, reports/}`.

## NOT done yet (remaining work)

- **GUI (task #20, the big one):** ImageDescriber still reads/writes `.idw` +
  `WorkspaceFiles/`. Needs: open/save `.idtw` bundles, migrate existing `.idw`
  on open (non-destructive), remove the bolted-on "Save/Import idt Project"
  actions, move derived artifacts into `<bundle>/derived/`, update the GUI spec
  hiddenimports for `idt_core.workspace`. HIGH regression risk (wx silent
  failures) — must be tested in dev mode.
- **CLI watch/video** — still on the Project model; bring onto bundles with the
  GUI work.
- **Docs (task #21):** rewrite `release-notes-v4.5.md` to lead with the unified
  workspace (correcting the false "old CLI was limited / 14 new commands"
  framing — the old CLI had ~16 commands), and update `USER_GUIDE_COMPLETE.md`.

## Commits

- `ead877b` workspace bundle foundation + design doc + tests
- `3074891` CLI describe/status/show/embed → bundles
- `702a60d` CLI export/stats/combine → bundles
