# Session Summary — 7/26/2026

## Part 1: Local git repo recovery

The `main` → `archive` / `v4.5` → `main` branch rename done on another machine left this
clone mid-merge with 6 conflicted files and `main` still on the old lineage.

**Audited for local-only work before discarding the clone:**

| Item | Outcome |
|---|---|
| `PeopleIdentification` (4 commits, ~4,700 lines, face ID feature) | Remote branch was deleted — **pushed to GitHub** |
| macOS 27 on-device research doc (in `stash@{0}`) | Not on any remote — **extracted and restored** |
| `.claude/settings.local.json` | Gitignored — **extracted and restored** |
| `claude/angry-nightingale-0f9fbc` (pbcopy fix) | Content already in `origin/main` — dropped |
| `refs/original/refs/heads/MacApp` | filter-branch backup of deliberately-rewritten history — dropped |
| 3 worktrees under `.claude/worktrees/` | All clean; commit `1a4318b` reachable from origin — dropped |
| Dangling commits (`git fsck`) | None |

Clone was deleted and re-cloned; both rescued files restored.

## Part 2: Progress UI for all processing stages

### Problem

`BatchProgressDialog` was only ever wired to the **describe** stage. The copy/save and
video-extraction stages ran with effectively no feedback:

- **Extraction** — one static `SetStatusText` line, never updated per video. The dialog
  wasn't created until `_launch_batch`, which runs *after* all extraction finished.
- **Save/copy** — `gui_workspace_to_bundle()` had no progress hook at all, and ran on the
  **main thread**. A blocked main thread means no repaint, so the status bar physically
  could not update and screen readers announced nothing.

### Changes

**`imagedescriber/batch_progress_dialog.py`**
- Added stage state (`stage_name`, `stage_index`, `stage_count`) and `separator_indices`
  to `__init__` (previously only created in `update_progress`, so `mark_complete` could
  raise `AttributeError` if it ran first).
- New `begin_stage(name, total, stage_index, stage_count, can_interrupt)` — resets the
  item counter and gauge per stage, sets the window title so screen readers announce the
  transition, and disables Pause/Stop for stages that aren't interruptible.
- `update_progress` now renders a `Stage:` row.

**`idt_core/gui_bridge.py`**
- `gui_workspace_to_bundle(..., progress=None)` — fires `progress(done, total, name)` per
  item. Chat items now also count (previously `continue`d past the counter).

**`imagedescriber/imagedescriber_wx.py`**
- `_save_bundle(progress=None)` — reports per item; passing `progress` also marks the save
  as off-thread, routing every wx call through `wx.CallAfter`.
- New helpers: `_ensure_progress_dialog()`, `_begin_stage()`, `_stage_progress()`,
  `_close_progress_dialog()`.
- `_stage_progress` throttles repaints to ~8/sec (`update_progress` rebuilds the entire
  ListBox; per-item repaints would swamp the event loop on a large workspace) but always
  paints the final item so each stage ends on an exact count.
- Dialog now opens at the *start* of a run, not at describe time.
- The pre-describe save moved off the main thread into a "Saving workspace" stage.
- CHECKPOINT 4's inline auto-save deferred into that stage — also means cancelling the
  options dialog no longer costs a pointless save.
- Both video-extraction paths (`on_process_all` and the folder-batch path) report per video.

### Stage model

Per-stage reset (each stage counts 0..N independently), 2 or 3 stages depending on videos:

```
Extracting frames (step 1 of 3)  →  Saving workspace (step 2 of 3)  →  Describing (step 3 of 3)
```

Pause/Stop are disabled outside the describe stage — only that stage runs under
`BatchProcessingWorker` and can actually honour them.

### Testing

- `python3 -m py_compile` on all 3 changed files — clean.
- Full unit suite: **260 passed** (258 before + 2 new).
- 2 new regression tests in `pytest_tests/unit/test_gui_bridge.py` covering the progress
  callback's count/total correctness and its optionality.
- Headless wx harness exercising `begin_stage` across all 3 stages: verified per-stage
  gauge reset, title text, Pause/Stop enable/disable, `Stage:`/`Items Processed:` rows,
  and that `mark_complete` still works after staging.
- `imagedescriber_wx.py` imports cleanly with all new helpers present.

### NOT tested

- **No end-to-end GUI run.** The app was never launched against real images, so the actual
  visual/screen-reader behaviour of the staged dialog during a live batch is unverified.
- No test with real videos — the extraction stage's per-video reporting is unexercised.
- Not tested on Windows.
- Not rebuilt as a frozen executable; PyInstaller behaviour unverified.
- The `_auto_save_bundle` / `_prompt_and_create_bundle` copy paths now pass a progress
  callback, but they still run on the main thread. When they're reached before the dialog
  exists (CHECKPOINT 3), progress still can't paint. **Addressed in Part 3 below.**

## Part 3: Save Workspace hang on a large network workspace

### Evidence

From `~/Library/Logs/ImageDescriber/ImageDescriber.log`, using the build from Part 2
against an iPhone photo library on a network share:

```
21:08:02  Directory scan complete: 7674 files in 17.41s
21:10:04  Saved workspace bundle: /Users/kellyford/Documents/idt/iPhone.idtw
```

**122 seconds with no output of any kind** — 7,674 items at ~16ms each over the share.
The "Saved workspace bundle" wording identifies this as `_prompt_and_create_bundle`,
which had only a `wx.BusyCursor()`: a cursor change conveys nothing to a screen reader,
and the blocked main thread meant nothing could repaint anyway.

### Changes (`imagedescriber/imagedescriber_wx.py`)

- New `_run_with_progress(stage_name, total, work)` — runs `work(progress_cb)` on a
  worker thread while the main thread pumps the event loop via `wx.SafeYield(dlg, True)`
  until it completes. This keeps the callers **synchronous** (seven callers branch on
  `_prompt_and_create_bundle`'s bool return) while letting the dialog repaint. SafeYield
  disables every window except the progress dialog, so the pumped loop cannot re-enter
  another handler. Return values pass through; exceptions re-raise on the main thread.
- `_prompt_and_create_bundle`, `_auto_save_bundle`, and the plain Save path in
  `on_save_workspace` all route through it. The GUI model is snapshotted with
  `to_dict()` on the main thread before the hand-off.
- A standalone save passes `stage_count=0` so the title omits "step N of M"; when a batch
  already owns the dialog it is reused and its stage numbering continues.

### Separate bug fixed along the way

`imagedescriber_wx.py:2664` called `_prompt_and_create_bundle("Save Workspace for
Downloads", proposed_name)` with two positional arguments, but the signature accepted
only `title` — a `TypeError` on every web download started without a saved workspace,
silently swallowed by wx. Added the `proposed_name` parameter it was already being
passed. An explicit name now wins over the source-folder-derived default.

### Testing

- Full unit suite: 260 passed.
- Headless harness against the real methods, covering: return-value pass-through, work
  actually running off the main thread, exception propagation with cleanup, and dialog
  ownership (an existing batch dialog is reused and its stage numbering continues rather
  than being closed out from under the batch).
- Repaint harness sampling the dialog *during* a simulated 400-item save: gauge observed
  at 19% → 45% → 69% mid-run, confirming updates reach the dialog while work proceeds.

### NOT tested (Part 3)

- Still no real GUI run — not reproduced against the actual 7,674-file network share.
- `_save_bundle` calls `workspace.to_dict()` inside the worker thread. It is a pure data
  read with no wx calls, and during the pump every window but the dialog is disabled, so
  a concurrent mutation is unlikely — but it is not formally guarded.
