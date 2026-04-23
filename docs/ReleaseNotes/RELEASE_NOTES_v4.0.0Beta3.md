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
- When you process a folder node, a confirmation dialog summarizes the image count and context before the run begins. The button is labeled **Process All** to make the scope clear.
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

The follow-up question dialog (chat window) now lists only the AI providers actually available on the current machine, rather than always showing all four. Apple Silicon Macs also see MLX in the provider dropdown. HuggingFace is only offered in the development environment — it is not shown in the installed application to avoid bundling large model dependencies.

The follow-up question is now asked about the description you have **currently selected** in the description list, rather than always defaulting to the most recent one. This makes it practical to ask follow-up questions about an older description while newer ones are also present in the workspace.

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
- **Image processing race condition on macOS** — when a folder node was processed, `EVT_TREE_SEL_CHANGED` could fire during the modal confirmation dialog and clear the current image reference, causing the run to start with no target. Fixed by capturing the image item into a local variable before opening any dialog.

---

### Prompt Library: Existing Prompts Revised, New Prompts Added

IDT now ships with **12 built-in prompt styles**, up from 7 in Beta 1.

**Existing prompts revised:** All original prompt styles have been rewritten for Beta 3. The revisions address common failure modes from earlier versions: vague structural guidance, over-permissive language that encouraged hallucination, and inconsistent output across models. Each prompt now has a tighter behavioral contract and per-style model settings (temperature, output length) tuned to match its intent.

**New prompts added:** Four prompt styles are new in Beta 3 — **accessibility**, **comparison**, **mood**, and **functional** — covering structured screen-reader output, analogy-based description, emotional atmosphere, and action/purpose-focused description respectively. An experimental twelfth prompt, **aialttext**, generates three lengths of website alt text (25, 50, and 100 words) in a single pass, intended as a starting draft for human review.

All 12 prompts (as they are sent to the AI model):

**narrative**
> Describe this image in a narrative style. Start with the overall scene, then describe specific objects and people from left to right. Include colors, clothing details, and spatial relationships. Mention what's in the foreground, middle ground, and background. Use concrete, specific language without metaphor or interpretation.

**detailed**
> Provide a structured description of this image:
>
> SUBJECT: Identify the main subject(s) and what they're doing
> SETTING: Describe the environment/location/background
> COLORS: Note dominant colors, lighting conditions, and color contrasts
> COMPOSITION: Mention perspective, depth, framing, and spatial relationships
> DETAILS: Include notable textures, patterns, or distinctive features
>
> Keep descriptions informative and organized. Avoid flowery language.

**concise**
> In 2-3 sentences, describe: what's in this image, where it is, and what's happening. Be brief but specific.

**artistic**
> Describe this image with attention to its visual qualities:
>
> • What draws the eye first and why
> • How light and shadow interact
> • Color relationships and their effect
> • The overall visual mood or feeling
> • What makes this image visually compelling
>
> Use clear, accessible language. No art jargon unless it's genuinely helpful.

**technical**
> Provide a concise technical evaluation of this image:
> - Subject identification: What is shown and its apparent purpose
> - Orientation and alignment: Whether the image is level, tilted, or crooked. Note if horizons are slanted or vertical lines are leaning
> - Lighting characteristics: Quality, direction, natural/artificial source, contrast
> - Composition approach: Framing, spatial organization, visual hierarchy
> - Image clarity and detail: Sharpness, resolution, exposure quality
> - Notable strengths or limitations: What works well or presents challenges (including if image needs straightening)
>
> Skip camera equipment speculation entirely.

**colorful**
> Describe this image with visual accuracy. State what the image depicts, then detail the color palette using specific names (crimson, navy, ivory, slate, amber, charcoal, ochre, teal, coral, emerald). Mention lighting direction and quality. End with one sentence about the atmosphere. Keep it grounded and concrete. Avoid words like 'stunning', 'breathtaking', 'mesmerizing', or 'ethereal'.

**simple**
> Provide a simple, brief description of this image in one sentence.

**accessibility**
> Describe this image for a screen reader user. Start with the main subject and overall scene. Then describe objects and people from left to right, including their colors, sizes, and positions relative to each other. Mention foreground, middle ground, and background elements. Use concrete, specific language without metaphor or visual-only references.

**comparison**
> Describe this image by comparing elements to familiar everyday objects, experiences, or well-known references. Use analogies like 'shaped like a...', 'resembles...', 'similar to...', 'about the size of...' to help someone understand what they're seeing. Make space imagery and abstract concepts relatable.

**mood**
> Describe the emotional atmosphere and mood of this image. What feelings does it evoke? What is the psychological tone? Describe the emotional quality of the lighting, the mood conveyed by the composition, and the overall feeling or atmosphere in rich, evocative language.

**functional**
> Describe what is happening in this image by focusing on function, purpose, and action. What are the objects FOR? What are they DOING? What is their utility or role? Describe actions, processes, relationships of use, and functional meaning. Focus on verbs: illuminates, supports, connects, transforms, protects, enables.

**aialttext** *(experimental)*
> Generate three instances of website alt text for this image of differing lengths:
> - 25 words
> - 50 words
> - 100 words

---

## Internal / Developer Changes

- Utility scripts reorganized into `tools/` directory.
- `idt stats` now parses frame extractor log files for extracted-frame counts; new unit tests added for this path.
- macOS performance checker: corrected Rosetta detection on Intel Macs and improved package architecture inspection.
- CI: Node.js updated from 20 to 24 in GitHub Actions (required before June 2026 deprecation).
- **Ollama cloud retry logic overhauled** — two-tier retry: an outer empty-response retry loop handles intermittent truncated responses from cloud-hosted models; an inner transport/server retry handles connectivity issues. `num_predict` is no longer forwarded to cloud-tagged models, which was causing server-side output truncation.
- **CLI integration test suite** — 60 new tests in `pytest_tests/integration/test_idt_cli.py` cover command routing, help contract, aliases, per-command `--help`, and regression guards against removed commands. A new CI workflow (`cli-validation.yml`) runs the suite on every push and PR. Total passing tests: 311.

---

## Post-Tag Updates (since bld1)

### AI Alt Text Prompt Now Official

The **aialttext** prompt style is now fully registered in `image_describer_config.json`:

- Added to `prompt_variations`, `prompt_model_settings`, `documentation.prompt_styles`, and `prompt_style_recommendations`
- Added to the `best_for` arrays for Kimi-K2.5 and Gemma4 models, which produced the best results in testing
- Config version bumped to 3.2 (2026-04-18)

The User Guide has been updated to document all 12 prompt styles (previously listed 7), with a new choosing guide covering accessibility, comparison, mood, functional, and aialttext.

### Claude Model Version Recognition Expanded

`idt combinedescriptions` and the label-formatting logic now correctly identify and display friendly labels for newer Claude variants: Haiku 4.5, Sonnet 4.6, and Opus 4.7/4.6/4.5. Previously these were shown as unrecognized or fell through to the wrong label. Matching order has been adjusted so more specific version checks take precedence over fallbacks, preserving existing labels for older models (Haiku 3/3.5, Sonnet 3.7/4/4.5, Opus 4/4.1).

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
