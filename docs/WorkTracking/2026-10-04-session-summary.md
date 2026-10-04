# 2026-10-04 — ImageDescriber saves descriptions during a batch

## Problem
During a batch, `on_worker_complete` added each description to the in-memory
workspace and marked it modified, and that was all. The bundle was written only
when the batch finished (`on_workflow_complete`), on Stop, or on a manual Save.
In a 10,000-image run, a crash lost everything since the last manual Save, and
`batch_state` (which resume reads) was never on disk during the run.

A full save after every image isn't an option: `_save_bundle` rewrites one
sidecar per item, which takes minutes on a large workspace.

## Fix
- `idt_core/gui_bridge.py`
  - `gui_item_to_ws_item()`: the GUI-item → bundle-sidecar merge, pulled
    out of `_save_bundle` so the full save and the checkpoint writer share it.
    It now looks in the item's own subfolder before the name-only lookup, which
    globs the whole `descriptions/` tree.
  - `BundleCheckpointWriter`: one background thread that writes the
    sidecar of each finished item, and refreshes the manifest (batch_state)
    every 25 items or 30 s, or on request (pause). Snapshots are numbered on the
    main thread (`snapshot_seq`); a sidecar is written only if its snapshot is
    newer than the last one written for that item (`claim`, under `lock`), so a
    slow full save and the writer can't overwrite each other's newer data.
    It never recreates a bundle that has disappeared.
- `imagedescriber/imagedescriber_wx.py`
  - `on_worker_complete` → `_checkpoint_item()` (main-thread snapshot,
    background write).
  - `_save_bundle(snap_seq=)` uses the shared helper and the claim check; both
    threaded callers (Save, pre-describe save) pass a snapshot number.
  - The complete, stop and close paths call `_flush_checkpoints()` before the
    final save. Without that, a late manifest write could put back a cleared
    `batch_state` and offer to resume a batch that had finished.
  - Pause queues a manifest write.

## Tests
- New `pytest_tests/unit/test_batch_checkpoint.py` (9 tests): writer
  saves an item, periodic and on-request manifest writes, ordering in both
  directions, subfolder targeting, missing bundle not recreated, a bad job
  doesn't stop the writer, and the real frame's `on_worker_complete` writing to
  disk without a Save. The frame test fails with the `_checkpoint_item` call
  removed.
- Full suite: 1854 passed, 47 skipped.
- End-to-end dev run (`--autostart`, Ollama moondream, 20 images): described
  sidecars appeared on disk mid-run; after the process was force-killed, 8/20
  descriptions survived, batch_state was in the manifest, and the other 12 items
  were `pending`, so resume would offer to pick up at image 9. A 3-image run to
  completion ended with 3/3 described and batch_state cleared.

## Not tested
- The resume prompt itself in the GUI after a crash (the data it reads was
  checked, not the modal dialog).
- A frozen build. `gui_bridge` was already in `imagedescriber_wx.spec`
  hiddenimports and no new module was added.
- macOS.
- The user's in-progress 10,000-image run still uses the old code.
