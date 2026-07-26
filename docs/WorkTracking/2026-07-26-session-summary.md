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
  exists (CHECKPOINT 3), progress still can't paint. Left as-is — those are explicit
  user-initiated saves, not the batch path.
