# Release Notes: v4.0.0 Beta 3

**Release Date:** April 2026  
**Version:** 4.0.0 Beta 3  
**Status:** Beta — feedback welcome

---

## Overview

Beta 3 is a substantial release across both apps. In ImageDescriber, the image list becomes a proper folder tree, web-downloaded images get their alt text captured automatically as a ready-made description, and the HTML export engine has been completely rewritten. On the command line, `idt` gains friendlier top-level commands (`idt describe`, `idt redescribe`, `idt manage-models`), the guided workflow gains the ability to start from a URL, and live description output while a run is in progress. Reliability of Ollama cloud models is significantly improved, and a new automated CLI test suite (311 tests) validates the complete command surface on every change.

---

## What's New

### ImageDescriber: Folder Tree Image List

The image list has been converted from a flat file list to a structured **folder tree**:

- Images are grouped under their parent subfolder. Loading a directory recursively builds folder nodes automatically; nested paths (e.g. `Vacation/Beach`) produce nested nodes.
- Select a **folder node** to queue all images it contains for processing — no need to select images individually.
- The scan root is always visible as the top-level node, giving context for the full directory.
- Folder expand/collapse state is preserved across workspace refreshes.
- Existing flat workspaces (no subfolders) display correctly without change.

---

### ImageDescriber: Website Alt Text Captured as a Description

When you download images from a web page, ImageDescriber now reads the HTML `alt` attribute for each image and stores it as a **"Website Alt Text"** description entry — with no AI processing required:

- The alt text appears in the workspace the moment the download finishes, before any AI run.
- It is stored in `alt_text_mapping.json` alongside the images and reloaded automatically when the workspace is reopened.
- When auto-process is enabled, a **Processing Options dialog** appears before the download begins, letting you decide whether to run AI descriptions in addition to the captured alt text, or skip AI entirely and rely on the alt text alone.
- Alt text and AI descriptions are treated as separate description sources per image and both appear in HTML exports.

This means images with good existing alt text — documentation sites, news sites, institutional photo libraries — can be useful immediately without a single API call.

---

### ImageDescriber: Rewritten HTML Export

File → Export Descriptions to HTML has been completely rewritten:

- HTML is generated directly from workspace items — no temporary files are created or left behind.
- Images are sorted by capture date. Where an image has multiple descriptions (e.g. alt text plus an AI description), they are grouped together under a single entry.
- Image metadata is embedded: capture date, GPS coordinates, camera make/model.
- An auto-generated table of contents is added for large exports.
- OpenStreetMap attribution is appended when location data is present.

---

### ImageDescriber: Follow-up Chat Shows Only Configured Providers

The follow-up question dialog (chat window) now lists only the AI providers actually available on the current machine, rather than always showing all four. Apple Silicon Macs also see MLX in the provider dropdown.

---

### CLI: `idt describe` — a More Natural Command Name

`idt describe <folder>` is a full alias for `idt workflow`. Every flag, `--help`, and all scripting patterns work identically. The intent reads clearly in documentation and scripts without needing to know that IDT calls the process a "workflow" internally. Existing `idt workflow` commands are unaffected.

---

### CLI: `idt redescribe` — Re-run AI on an Existing Workflow

`idt redescribe <workflow_dir>` is a top-level shorthand for `idt workflow --redescribe`. It takes the processed images from an existing workflow run and sends them through a different model, provider, or prompt style — without re-downloading or re-converting anything. All workflow flags are supported.

---

### CLI: `idt manage-models` — Install and Manage Ollama Models

New top-level command for working with Ollama models without leaving the terminal:

- `idt manage-models list` — show installed models
- `idt manage-models install <model>` — pull a model
- `idt manage-models remove <model>` — delete a model
- `idt manage-models info <model>` — details for a specific model
- `idt manage-models recommend` — suggest models for common use cases

---

### CLI: `idt guideme` Accepts a URL at the Image Folder Step

At Step 4 of the guided workflow, you can now enter a website URL instead of a local folder path. `guideme` downloads images from the page automatically and continues the workflow with the downloaded folder. If no images are found at the URL, or if download dependencies are missing, you get a clear error message rather than a silent failure.

Downloaded image sets land in a subfolder named `{domain} - {page title} - {timestamp}` inside `downloaded_images/`, so the source is identifiable at a glance.

---

### CLI: `--show-descriptions on` — Watch Descriptions as They Are Written

The new `--show-descriptions on` flag streams each AI-generated description to the terminal as it is produced, with a `--- filename.jpg ---` header before each one. The default is `off`, preserving the existing progress-bar-only output for unattended runs.

---

## Bug Fixes

- **Console windows on Windows** — video frame extraction no longer flashes a console window during processing.
- **Add to existing workspace** — opening a second folder into an already-open workspace was overwriting the image list instead of appending to it. Fixed.
- **UI freeze during batch processing** — a selection-changed event fired during processing could trigger a full list refresh and freeze the UI. Guarded against this.
- **`idt guideme` offered MLX on Windows (issue #111)** — MLX is now only listed as a provider option on macOS.
- **HuggingFace `NameError` on systems without transformers installed (issue #113)** — `HAS_TRANSFORMERS` was never initialized to `False`, so calling `is_available()` on systems without the `transformers`/`torch` packages raised `NameError` instead of returning `False`. Fixed by initializing at module level before the conditional import.
- **`idt redescribe` failed on URL-downloaded workflows** — `--redescribe` now uses `descriptions/file_path_mapping.json` as the primary image source, fixing "Source workflow has no processed images" errors on runs that started from a URL. Falls back to directory scanning for older workflows.
- **`idt combinedescriptions` showed `unknown` for four prompt styles** — accessibility, comparison, mood, and functional were defined in the config but missing from the recognition list in the export code. All four are now recognized correctly.
- **`idt combinedescriptions` wrong model labels for URL-downloaded workflows** — model labels were derived by splitting the workflow directory name on underscores, which broke when the workflow name itself contained underscores (e.g. a downloaded page title). Labels are now read from `workflow_metadata.json` and only fall back to name parsing for legacy workflows without metadata.
- **`--show-descriptions` flag had no effect (issue #115)** — the flag was accepted but not forwarded to the subprocess. Fixed.

---

## Internal / Developer Changes

- Utility scripts reorganized into `tools/` directory.
- `idt stats` now parses frame extractor log files for extracted-frame counts; new unit tests added for this path.
- macOS performance checker: corrected Rosetta detection on Intel Macs and improved package architecture inspection.
- CI: Node.js updated from 20 to 24 in GitHub Actions (required before June 2026 deprecation).
- **Ollama cloud retry logic overhauled** — two-tier retry: an outer empty-response retry loop handles intermittent truncated responses from cloud-hosted models; an inner transport/server retry handles connectivity issues. `num_predict` is no longer forwarded to cloud-tagged models, which was causing server-side output truncation.
- **CLI integration test suite** — 60 new tests in `pytest_tests/integration/test_idt_cli.py` cover command routing, help contract, aliases, per-command `--help`, and regression guards against removed commands. A new CI workflow (`cli-validation.yml`) runs the suite on every push and PR. Total passing tests: 311.

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
