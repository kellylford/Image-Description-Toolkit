# Release Notes: v4.0.0 Beta 2

**Release Date:** March 28, 2026  
**Version:** 4.0.0 Beta 2  
**Status:** 🧪 Beta — feedback welcome

---

## Overview

Beta 2 delivers one major new capability — **Apple on-device AI** via the MLX / Metal provider — alongside a significantly improved image browsing experience in ImageDescriber, richer video support, and several bug fixes.

---

## What's New

### Apple On-Device AI (macOS Apple Silicon only)

ImageDescriber and the `idt` CLI now support running AI vision models locally on Apple Silicon Macs using [mlx-vlm](https://github.com/Blaizzy/mlx-vlm). No API key, no cloud, no data leaves your machine.

**7 models included:**
- Qwen2-VL-2B-Instruct-4bit *(recommended, fast)*
- LLaVA-1.5-7B-4bit
- Phi-3.5-Vision-Instruct-4bit
- Gemma-3-4B-IT-QAT-4bit
- SmolVLM-Instruct-4bit *(smallest/fastest)*
- LLaMA-3.2-11B-Vision-Instruct-4bit *(requires 32 GB RAM)*

Models download automatically on first use from Hugging Face. Each model card in the UI shows download size, speed characteristics, and hardware requirements.

> **Requirements:** macOS, Apple Silicon (M1 or later). MLX is not available on Windows or Intel Macs.

---

### ImageDescriber GUI: Search & Improved Image Preview

The image list in ImageDescriber has been significantly reworked for larger workspaces:

- **Search/filter bar** (Ctrl+F) with live filtering; supports simple AND/OR keywords
- **Resizable preview panel** — drag the splitter to give more space to the image or description list
- **Dynamic image scaling** — preview redraws cleanly at any panel size
- **Side-by-side layout** — preview and description list sit next to each other
- **Video frame preview** — shows the first extracted frame for video items
- Improved keyboard navigation (Up/Down in image list, correct tab order, shortcuts not intercepted while typing)

---

### Video: GPS/EXIF Embedding in GUI Extraction

When extracting frames from video through ImageDescriber, GPS coordinates, capture datetime, and camera metadata from the video file are now embedded as EXIF data in the extracted JPEG frames — matching what the CLI has long done. Previously this only worked via the CLI workflow.

Also in video:
- Status bar shows video duration during frame extraction
- Crash fix when a video reports fps ≤ 0
- New **Tools → Install FFmpeg** menu item with platform-specific install instructions (winget on Windows, brew on macOS)

---

### Bug Fixes

- **Prompt editor** was saving prompts inside the application bundle instead of the user config directory — prompts were lost on reinstall. Fixed.
- **Update Image List (F5)** — added to the Process menu. During a batch run the image list is not refreshed per-image (intentional, avoids UI lag at scale). F5 lets you manually trigger a refresh at any point to see which images have been described so far (`d1`, `d2` prefixes).
- Integration test suite stabilized for CI reliability.

---

### Setup & Packaging

- **Windows setup** (`winsetup.bat`) simplified — now installs IDT CLI and ImageDescriber only (PromptEditor and IDTConfigure are now integrated into ImageDescriber's Tools menu)
- **Windows installer filename** now reflects the `VERSION` file automatically — no longer hardcoded to Beta 1
- **macOS setup** updated to document MLX/Metal provider dependencies
- MLX dependencies (`mlx-vlm`, `torch`) are platform-gated — Windows/Linux builds are unaffected

---

## Known Issues / Beta Notes

- MLX model downloads are large (1–7 GB). Ensure adequate disk space before selecting a model for the first time.
- The LLaMA 3.2 11B model requires 32 GB RAM; on 16 GB systems it may swap heavily or fail to load.

---

## Installation

### Windows
Download `ImageDescriptionToolkitSetup_4.0.0Beta2_bld1.exe` and run the installer.

### macOS
Download `IDT-4.0.0Beta2 bld1.dmg`, open it, and drag the apps to your Applications folder.
