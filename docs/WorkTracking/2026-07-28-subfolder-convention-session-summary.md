# 2026-07-28 — One subfolder convention for the CLI and the GUI

A workspace bundle made by `idt describe` opened correctly in ImageDescriber —
images listed, descriptions picked up, newly added images recognised — but the
tree had **no top-level folder node** for the source folder. Because every
folder-scoped command resolves its scope from the selected folder node, none of
them could run.

## Root cause

`subfolder` decides two things at once: how the GUI groups the tree, and where
sidecars and image copies land inside the bundle. Four places computed it, and
they used two different anchors.

| Site | Anchor | `\\ford\...\2026\05\IMG.HEIC` becomes |
|---|---|---|
| `idt_core/workspace.py` `add_source_folder` | the source folder | `None` |
| `cli/main.py` `_cmd_describe_stdin` | the source folder | `None` |
| `cli/main.py` `cmd_watch._add_source_images` | the source folder | `None` |
| `imagedescriber_wx.py` `on_files_discovered` | the source folder's **parent** | `"05"` |
| `imagedescriber_wx.py` `_apply_rescan_results` | the source folder's **parent** | `"05"` |

The tree builder groups purely on `subfolder`, treating `None`/`""` as "hang off
the invisible root" (`imagedescriber_wx.py:3049`). So a CLI bundle put all 181
items at the root and created no folder node at all, while a GUI bundle of the
same folder created one named `05`.

This was visible on disk in the user's own workspaces:

```
05.idtw/descriptions/   IMG_3983.HEIC.json, IMG_4060.HEIC.json, ...   (flat — CLI)
07.idtw/descriptions/   07/, mcp_video-...jpg.json                    (nested — GUI)
```

Downstream of the missing node:

* Both folder-scoped Process commands stopped at "Select a folder in the image
  tree first" (`_process_selected_folder`, `imagedescriber_wx.py:4410`).
* P-on-a-folder had no folder to act on.
* "Refresh Folder from Disk" stayed permanently disabled — it enables only when
  a folder node is selected (`imagedescriber_wx.py:1420`).
* `idt embed --output` and the GUI's embed wrote to different layouts for the
  same images, since both mirror `subfolder` into the output directory.

Latent and worse than the display bug: opening a CLI bundle in the GUI and
hitting Refresh would have assigned the *new* files `"05"` while the existing
ones kept `None` — one source folder split across two tree groups, with new
sidecars in `descriptions/05/` beside the old flat ones.

## Fix

One function, `source_relative_subfolder(file_path, source_root)` in
`idt_core/workspace.py`, is now the only definition of the rule. All five sites
call it.

The parent-anchored convention won, for three reasons:

1. The top-level node falls out of the data. The alternative — anchoring at the
   source folder and synthesising a node from `manifest.sources` — puts
   per-item source lookup inside `refresh_image_list`, which already runs over
   thousands of items.
2. `descriptions/` and `images/` inside the bundle then mirror "the folder I
   added", which is what a user browsing the bundle expects.
3. It is what the GUI already did, and bundle `07.idtw` is the existing proof
   that folder nodes, folder-scoped processing and rescan all work under it.

Edge cases the helper handles, which the five inline copies variously did not:
a file outside the source root returns `None` rather than raising, and a source
root that is itself a drive or UNC share (no name of its own) returns `None`
instead of inventing a component.

## Changes

* **`idt_core/workspace.py`** — added `source_relative_subfolder()`;
  `add_source_folder` now calls it.
* **`cli/main.py`** — `_cmd_describe_stdin` and `cmd_watch._add_source_images`
  use it instead of their own inline copies.
* **`imagedescriber/imagedescriber_wx.py`** — `on_files_discovered` and
  `_apply_rescan_results` use it; imported at module scope (the scan handler
  calls it once per discovered file) behind the file's usual `try/except
  ImportError` guard.
* **`pytest_tests/unit/test_workspace_bundle.py`** — updated the existing
  provenance test for the new anchor, plus three new tests: that the source
  folder is anchored as a top-level component and nothing is stranded at the
  tree root, the rule itself (direct / nested / outside), and the
  filesystem-root case.

## Testing

* Full suite: **863 passed, 14 skipped**, 0 failures.
* `python -m py_compile` on all three changed Python files.
* End-to-end through the real GUI load path: built a bundle with
  `add_source_folder`, ran it through `bundle_to_gui_workspace_dict`, and
  replicated the tree builder's grouping — one `05` top-level node with `Day2`
  nested under it, zero items stranded at the root. Sidecars landed at
  `descriptions/05/...`, matching what a GUI-created bundle produces.
* GUI module imported in dev mode to confirm the new module-scope import
  resolves and the helper is wired.
* Both executables rebuilt (`builditall_wx.bat`, exit 0, both artifacts fresh
  on disk) — `idt_core/workspace.py`, `cli/main.py` and `imagedescriber_wx.py`
  are all reachable from the specs' `hiddenimports`.
* **Frozen mode exercised for real**: `idt.exe describe` against a staged tree
  with one image at the top level and one in `Nested/`, ollama/moondream, into a
  fresh bundle. `2 described, errors=0`. The bundle it wrote:

  ```
  descriptions/SmokeSrc/coffee_desk.jpg.json
  descriptions/SmokeSrc/Nested/outdoor_scene.jpg.json
  ```

  Reopened through `bundle_to_gui_workspace_dict` and grouped as the tree
  builder does: one `SmokeSrc` top-level node, `Nested` under it, zero items
  stranded at the root, both descriptions intact.

## What was NOT tested

* **No GUI interaction.** `ImageDescriber.exe` was built but never launched. The
  tree was verified by replicating the grouping logic against real bundle data,
  not by opening the app and clicking a folder node. Confirming "Process
  Undescribed in Selected Folder" actually runs against a CLI-made bundle is a
  manual step still outstanding — as is the GUI-side scan path
  (`on_files_discovered`), which is covered only by the module-import check and
  the shared helper's own tests.
* **No macOS run.** Path handling is `pathlib`-only and the tests are
  separator-agnostic, but the change was exercised on Windows only.
* **Pre-existing bundles are not migrated.** Nothing has shipped, so no
  migration was written. Bundles created before this change (e.g. the user's
  `05.idtw` and `06.idtw`) still have flat `subfolder=None` items and will still
  show no folder node. They should be deleted and re-run rather than reopened —
  reopening and rescanning is exactly the half-migrated split described above.

## Known limitation

Two source folders with the same basename added to one bundle (e.g.
`\\ford\photos\2026\05` and `C:\Pictures\05`) both map to `"05"` and merge into
a single tree node. The previous convention collided too — worse, in fact, since
both merged at the tree root. Distinguishing them properly means keying items to
a source identity rather than a path prefix, which would change the on-disk
layout; deliberately deferred.
