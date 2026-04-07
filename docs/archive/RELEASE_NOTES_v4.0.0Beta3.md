# Release Notes: v4.0.0 Beta 3

**Release Date:** April 7, 2026  
**Version:** 4.0.0 Beta 3  
**Status:** Beta — feedback welcome

---

## Overview

Beta 3 brings two major improvements to the ImageDescriber GUI: a full tree-view image list that organizes images by folder, and automatic capture of website alt text as a ready-made description entry when downloading images from the web. It also ships a rewritten HTML export engine and  several bug fixes.

---

## What's New

### ImageDescriber GUI: Tree View Image List

The image list in ImageDescriber has been converted from a flat list to a proper **folder-based tree view**:

- Images are grouped under their parent subfolder in the tree. Loading a directory recursively creates folder nodes automatically; nested paths (e.g. `Vacation/Beach`) produce nested nodes.
- Select a **folder node** to process all images it contains in one action — no need to select images individually.
- The top-level scan root appears as the root folder node so the overall directory context is always visible.
- Folder **expand/collapse state** is preserved across workspace refreshes.
- Existing flat workspaces (no subfolders) continue to display correctly.

---

### Website Image Download: Alt Text as Description

When downloading images from a web page, ImageDescriber now captures the HTML `alt` attribute, where it exists,  for each image and creates a **"Website Alt Text"** description entry automatically:

- No AI processing required — the alt text is available the moment the download completes.
- Alt text is stored in `alt_text_mapping.json` alongside the downloaded images and reloaded with the workspace.
- A **Processing Options dialog** is shown before a download begins (when auto-process is enabled), letting you choose which AI steps to run in addition to — or instead of — the captured alt text.

---

### HTML Export: Rewritten Inline Generator

The HTML export (File → Export Descriptions to HTML) has been completely rewritten:

- Generates HTML directly from workspace items — no temporary files created or cleaned up.
- Sorts images by date and groups **multiple descriptions per image** (e.g. alt text + AI description) into a single entry.
- Embeds image metadata: capture date, GPS coordinates, camera make/model.
- Adds an auto-generated **table of contents** for exports with many images.
- Appends OpenStreetMap attribution when location data is included.

---

### Follow-up Chat: Dynamic Provider List

The follow-up question dialog (chat window) now shows only the AI providers that are actually configured on the current machine, instead of always listing all four. MLX models are also available in the follow-up provider dropdown on Apple Silicon Macs.

---

## Bug Fixes

- **Console windows on Windows** — video frame extraction no longer flashes a console window on Windows.
- **Add to existing workspace** — loading a second directory into an already-open workspace was incorrectly overwriting the existing image list instead of appending. Fixed.
- **UI freeze during processing** — a `EVT_TREE_SEL_CHANGED` event fired during batch processing could trigger a full list refresh and freeze the UI. Guarded against this.
- **`idt stats` CI flag** — the `--input-dir` flag was missing in the CI integration test step.

---

## Internal / Developer Changes

- Utility scripts moved to `tools/` directory.
- `idt stats` now parses `frame_extractor` log files for extracted-frame counts; new unit tests added.
- macOS performance checker: corrected Rosetta detection on Intel Macs and improved package architecture inspection.
- CI: Node.js 20 → 24 in GitHub Actions (required before June 2026 deprecation).

---

## Known Issues / Beta Notes

- MLX model downloads are large (1–7 GB). Ensure adequate disk space before selecting a model for the first time.
- The LLaMA 3.2 11B model requires 32 GB RAM; on 16 GB systems it may swap heavily or fail to load.

---

## Installation

### Windows
Download `ImageDescriptionToolkitSetup_4.0.0Beta3_bld1.exe` and run the installer.

### macOS
Download `IDT-4.0.0Beta3 bld1.dmg`, open it, and copy/drag the apps to your Applications folder.
