# Plan: Image Description Toolkit — Comprehensive User Guide

**Date:** March 28, 2026  
**Status:** Ready for review  
**Author:** GitHub Copilot (Claude Sonnet 4.6)

---

## Problem Statement

IDT ships with documentation scattered across 20+ files in various states of accuracy and completeness. Users have no obvious starting point and must piece together knowledge from a Windows-centric user guide, a brief macOS quick-start, an outdated CLI reference (v2.0 naming), and several provider-specific guides. The toolkit is genuinely powerful — batch processing of thousands of images, multi-provider AI support, EXIF-aware exports, follow-up questions, built-in chat, web downloads — but that depth is invisible to most users.

**Resources reviewed for this plan:**
- All existing docs in `docs/` and root
- Full source survey of `idt/idt_cli.py`, `scripts/`, `imagedescriber/`, `analysis/`, `models/`
- Blog post: https://theideaplace.net/introducing-idt-4-0-beta-1-an-enhanced-way-to-describe-your-digital-images/

---

## Proposed Output

**`docs/USER_GUIDE_COMPLETE.md`** — a single authoritative user guide that:
- Covers both macOS and Windows in one document (platform callouts via blockquotes)
- Goes from zero to fully productive across both the CLI and GUI
- Covers every significant feature the tool actually has
- Replaces three outdated documents with deprecation notices pointing to itself
- Can be included in `.dmg`/`.pkg` and `.exe` installers as-is (Markdown renders on GitHub; can be pandoc'd to PDF for offline users)

---

## Recommended Structure

### Part 1 — Getting Started

**Section 1: What IDT Is (and Is Not)**

Lead with the key distinction from the blog post: countless apps let you describe one or two images on the fly. IDT is for when you have dozens, hundreds, or thousands of photos you want described, with descriptions stored permanently and queryable later. Frame the two modes:

- **CLI (`idt`)** — batch workflows, automation, scripting, large-scale processing
- **GUI (ImageDescriber)** — interactive session, per-image control, multi-description comparison, follow-up questions, chat

Brief summary table of the three applications (ImageDescriber, Viewer, `idt` CLI) with one-line description of each.
KF: There are only two apps, ImageDescriber (GUI) and IDT (cmd line)

**Section 2: Installation**

*macOS:*
- System requirements: macOS 10.13 (High Sierra) or later
KF:We do not have anything like this for the Mac and don't need it. - Option A: `.pkg` installer — wizard installs apps to `/Applications/`, CLI to `/usr/local/bin/idt`
KF: This is the standard Mac install and what we should use. But be inclusive with langauge and say drag/copy. - Option B: `.dmg` — drag apps to Applications, double-click `INSTALL_CLI.sh` for CLI access
- Post-install check: `idt version` in Terminal
- Gatekeeper note: right-click → Open on first launch (app is not yet code-signed) KF: What app isn't code signed on the Mac. Everything is supposed to be.


*Windows:*
- System requirements: Windows 10 or 11
- Run `ImageDescriptionToolkit_Setup_vX.X.X.exe`
- Default install path: `C:\IDT\`
- Apps in install dir: `idt.exe`, `imagedescriber.exe`, `viewer.exe`
- Post-install check: open Command Prompt, `cd C:\IDT`, then `idt version`
- SmartScreen/defender note: app is not code-signed; allow it through the warning

**Section 3: Setting Up AI Providers**

*Ollama (local, free — recommended for first-time users):*
- What Ollama is: a local AI runtime; all processing stays on your machine; no API key needed
- Install from ollama.ai (or `winget install Ollama.Ollama` on Windows)
- Pull Moondream (fast, 1.7 GB, recommended first model): `ollama pull moondream`
- Model trade-off table:
KF: Redminder, we offer to grab this on Windows during install.

  | Model | Size | Speed | Quality |
  |---|---|---|---|
  | moondream | 1.7 GB | Fastest | Good |
  | llava:7b | ~4 GB | Fast | Better |
  | llava:13b | ~8 GB | Moderate | High |
  | llama3.2-vision | 11 GB | Slow | Highest |

- Verify installed models: `ollama list`
- Ollama runs as a background service; no manual start needed after first install

*OpenAI (cloud, paid):*
- Get API key at platform.openai.com
- Set environment variable:
  - macOS/Linux: `export OPENAI_API_KEY="sk-..."` (add to `~/.zprofile` for persistence)
  - Windows: System → Environment Variables, or `set OPENAI_API_KEY=...` in session
- Alternative: create `~/openai.txt` containing only the key (no quotes, no newline)
- Models: GPT-4o, GPT-4o mini

*Anthropic Claude (cloud, paid):*
- Get API key at console.anthropic.com
- Same pattern: `ANTHROPIC_API_KEY` env var, or `~/claude.txt`
- Models: Claude 3.5 Haiku (fast/cheap), Claude 3.5 Sonnet (balanced), Claude Opus (highest quality)
- Token usage for both OpenAI and Claude is displayed in image metadata after processing — use this to monitor costs

*HuggingFace / Florence-2 (local, specialized):*
- Mention briefly; link to `docs/HUGGINGFACE_PROVIDER_GUIDE.md` for setup
- Good for object detection without cloud costs

---

Don't forget about metal on Mac just added.


### Part 2 — Your First Descriptions

**Section 4: The `guideme` Wizard (Recommended First Run)**

Start here before anything else. The wizard asks questions and picks safe defaults.

```
idt guideme
```

Walk the user through each prompt:
1. Source directory or URL?
2. Which AI provider?
3. Which model?
4. Which prompt style?

What gets created: a `wf_YYYY-MM-DD_HHMMSS_model_prompt/` directory containing:
- `image_descriptions.txt` — all descriptions as plain text
- `descriptions.html` — browsable HTML report with thumbnails
- `workflow_metadata.json` — run metadata
- `logs/` — detailed per-step logs

Open results immediately: `idt viewer wf_<tab-complete>`

**Section 5: Opening the ImageDescriber App**

- **macOS:** Applications → ImageDescriber, or `idt imagedescriber` in Terminal
- **Windows:** Start Menu → IDT → ImageDescriber, or `idt imagedescriber` in Command Prompt

Load images:
- `File → Open Folder` (or `Ctrl+L`) — loads all images from a folder
- Drag and drop a folder onto the window
- `File → Open Workspace` — reload a saved `.idw` workspace file

What you see: image list on the left, description panel on the right.

Status indicators on each image in the list:
- `d` — has at least one description
- `b` — marked for batch processing
- `p` — currently processing

---

### Part 3 — The ImageDescriber GUI (Full Walkthrough)

**Section 6: Processing Images**

*Single image:*
- Select image → press `P`, or `Processing → Process Selected`
- A dialog prompts for provider, model, and prompt style
- Default: Ollama / Moondream / Narrative
- Description appears in the right panel

*Batch processing:*
- Select images → press `B` to mark for batch (light blue highlight, "b" prefix)
- `Processing → Process Batch` — runs all marked images
- `Processing → Process All Undescribed` — processes everything in the folder that has no description yet
- Window title shows live progress: "Batch Processing: X of Y"
- `Processing → Stop` for graceful cancellation at any time

*Each run appends* — running the same image again with a different model/prompt adds a new description rather than replacing the previous one. An image can accumulate many descriptions for comparison.

*Choosing prompt style and model:*
- Use the sidebar dropdowns before pressing P
- Or use `Tools → Configure Settings` to set a permanent default

**Section 7: Follow-Up Questions**

One of the more powerful hidden features: after an image is described, you can ask follow-up questions without re-running the full description.

- Select an image or description → press `F`, or `Processing → Follow Up`
- A dialog appears; type your question (e.g., "What colors are dominant?" or "List all people in this image")
- You can choose a different model for the follow-up than was used for the original description
- The follow-up response is appended as an additional entry

This is useful for iterative exploration: get a narrative description first, then drill into specific details.

**Section 8: AI Chat (No Image Required)**

ImageDescriber includes a basic AI chat that works without any loaded images.

- Press `C`, or `Processing → Chat`
- Select your model
- Type your question and receive a response
- `Shift+Tab` moves to chat history
- To save: `Ctrl+A` → `Ctrl+C` to copy all and paste into another app (full chat save to workspace is a planned future feature)

Useful for: testing a model's capabilities, asking general questions, or getting AI assistance while working with your images.

**Section 9: Downloading Images from the Web**

ImageDescriber can download images from a web page and describe them directly.

- `Ctrl+U` or `File → Open URL`
- Enter the URL of a web page
- IDT downloads all images from the page and loads them into the workspace for description

Equivalent CLI command: `idt workflow <url>`

**Section 10: Viewing and Managing Results**

- **Filter bar:** All / Described Only / Batch-Marked Only
- **Tree view:** videos show extracted frames as child items
- **All Descriptions dialog:** browse every description across all images in the workspace
- **Multiple descriptions per image:** each run appends; use the description list to navigate between them
- **Save workspace:** `Ctrl+S` — persists all batch marks, descriptions, and processing state to a `.idw` file; reopen later and pick up where you left off

**Section 11: Built-In Tools**

Previously these were standalone applications. They are now integrated into ImageDescriber's Tools menu.

- `Tools → Edit Prompts` — Prompt Editor: create, edit, and save named prompt templates
- `Tools → Configure Settings` — Configuration Manager: API keys, default model, default prompt style, workflow preferences

**Section 12: Exporting from the GUI**

- **HTML report:** generated automatically in each `wf_*` directory; open `descriptions.html` in any browser
- **CSV/Excel export:** `idt combinedescriptions` from the CLI (see Section 19)
- **Plain text:** `image_descriptions.txt` in each `wf_*` directory is plain text; copy/paste at will

---

### Part 4 — The CLI

**Section 13: CLI Fundamentals**

```
idt <command> [options]
idt help
idt <command> --help
idt version
```

- **macOS:** `idt` (installed to `/usr/local/bin/idt`)
- **Windows:** `idt` from `C:\IDT\` directory, or `idt.exe` anywhere if in PATH

**Section 14: Running Workflows**

```bash
# Interactive wizard — prompts for all settings
idt guideme

# Direct run — uses defaults for model and prompt
idt workflow ~/Photos/Vacation2025
idt workflow C:\Photos\Vacation2025

# With specific model and prompt
idt workflow ~/Photos --model llava:7b --prompt-style detailed

# With live progress in terminal
idt workflow ~/Photos --progress-status

# Web page — downloads images then describes them
idt workflow https://example.com/gallery
```

Output directory: `wf_YYYY-MM-DD_HHMMSS_{model}_{prompt}/` created in the current working directory.

Each workflow directory contains:
- `image_descriptions.txt` — all descriptions with metadata headers
- `descriptions.html` — browsable report
- `workflow_metadata.json` — machine-readable run summary
- `logs/` — per-step detailed logs

Multiple workflow runs on the same source folder create separate `wf_*` directories — nothing is overwritten. This lets you build up a collection of descriptions using different models and prompts for comparison.

**Section 15: Launcher Commands**

```bash
idt viewer                    # Open Viewer GUI
idt viewer ~/Photos/wf_2026*  # Open Viewer pointed at a directory
idt imagedescriber            # Open ImageDescriber GUI
idt imagedescriber ~/Photos   # Open ImageDescriber with folder loaded
idt prompteditor              # Open Prompt Editor
idt configure                 # Open Configuration Manager
```

**Section 16: Utility Commands**

```bash
# Extract frames from a video file (without running a full workflow)
idt extract-frames myvideo.mp4

# Convert a folder of HEIC/HEIF images to JPEG (preserves GPS metadata)
idt convert-images ~/Photos/iPhone

# Regenerate HTML report from existing descriptions (no new AI calls)
idt descriptions-to-html wf_2026-03-28_120000_moondream_narrative

# List AI models Ollama has installed
idt check-models

# List available prompt styles
idt prompt-list

# List all workflow result directories in the current folder
idt results-list
```

**Section 17: Analysis & Export Commands**

These commands are powerful post-processing tools that are largely undiscovered by most users.

```bash
# Combine all workflow runs into a single spreadsheet
idt combinedescriptions

# Sorted by photo date (EXIF DateTimeOriginal — default and most useful for photo archives)
idt combinedescriptions --sort date

# Sorted alphabetically by filename
idt combinedescriptions --sort name

# Specify output file and format
idt combinedescriptions --output my_descriptions.csv --format csv
idt combinedescriptions --output my_descriptions.tsv --format tsv

# Analyze performance, timing, and estimated API costs
idt stats

# Review description quality: vocabulary, length, style patterns
idt contentreview
```

`combinedescriptions` is especially valuable for photo archives: it merges all `wf_*` directories into a single spreadsheet with one row per image, columns for each workflow run's description, and the images sorted by the date they were actually taken (from EXIF data) rather than by filename. Perfect for chronological photo journals or event documentation.

`stats` shows token counts and estimated costs for OpenAI and Claude runs, cross-referencing published pricing. Useful for budgeting before scaling up.

---

### Part 5 — Configuration

**Section 18: Configuration Files**

Three JSON files control toolkit behavior. They live alongside the executables and can be edited with any text editor. The Configuration Manager GUI (`idt configure` or `Tools → Configure Settings`) provides a form-based interface that validates JSON before saving — recommended for beginners.

*`image_describer_config.json`:*
- `default_model` — e.g., `moondream:latest`
- `default_prompt_style` — narrative, detailed, technical, creative, colorful, concise, simple
- `image_max_size` — resize limit before sending to AI (reduces tokens/cost)
- `batch_delay` — seconds to wait between images (prevents rate limiting with cloud providers)
- `output_format` — what metadata is included in description files (timestamp, model name, EXIF)

*`workflow_config.json`:*
- Enable/disable workflow steps: video extraction, HEIC conversion, HTML generation
- Base output directory
- Logging verbosity

*`video_frame_extractor_config.json`:*
- Frame extraction rate (e.g., one frame per second, one per 5 seconds)
- Output subdirectory name within the workflow directory

Configuration priority (highest to lowest):
1. Command-line argument (e.g., `--model`)
2. Custom config file path (e.g., `--config-image-describer myconfig.json`)
3. Config file in the IDT install directory
4. Built-in defaults

**Section 19: Environment Variables**

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | OpenAI API key |
| `ANTHROPIC_API_KEY` | Anthropic/Claude API key |
| `IDT_CONFIG_DIR` | Directory to search for config files |
| `IDT_IMAGE_DESCRIBER_CONFIG` | Full path to a specific image_describer_config.json |

Key file alternatives (simpler for GUI users):
- `~/openai.txt` — file containing only the OpenAI key
- `~/claude.txt` — file containing only the Claude key

---

### Part 6 — Prompt Customization

**Section 20: Built-In Prompt Styles**

| Style | Best For |
|---|---|
| `narrative` | Natural, story-like descriptions — good default for photos |
| `detailed` | Thorough, comprehensive descriptions of all elements |
| `technical` | Image quality, composition, technical properties |
| `creative` | Evocative, expressive language; mood and atmosphere |
| `colorful` | Emphasis on colors, palettes, and visual tone |
| `concise` | Short one-or-two sentence summaries |
| `simple` | Plain language, minimal jargon |

Select at run time: `--prompt-style colorful`, or in the GUI sidebar before pressing P. Set a permanent default in `image_describer_config.json` or via the Configuration Manager.
KF: we should include the text al all existing prompts.


**Section 21: Writing Custom Prompts**

You can write any prompt you want:

- **GUI:** type in the Custom Prompt field in the sidebar, or use `Tools → Edit Prompts` to save named templates
- **CLI:** `idt workflow ~/Photos --custom-prompt "List all objects in this image as bullet points"`
- **Config file:** set `prompt_template` in `image_describer_config.json`

Tips for effective prompts:
- Be specific about the subject matter ("focus on people and their expressions")
- Specify output format when it matters ("respond as a numbered list", "one sentence only")
- Include context that shapes interpretation ("this is for a museum exhibit on 1970s fashion")
- Use the follow-up (`F`) feature to drill into specifics after getting a general description — more efficient than crafting one giant prompt up front
- Test on a 5-10 image sample before running thousands

See `docs/PROMPT_WRITING_GUIDE.md` for a comprehensive reference on prompt engineering for image description.

---

### Part 7 — Advanced Topics

**Section 22: Video Support**

Drop video files (MP4, MOV, AVI, MKV, and others) into your source folder. The workflow automatically:
1. Extracts frames at a configurable rate
2. Embeds the video's timestamp into each frame's EXIF data
3. Describes each frame using your chosen model and prompt

In the ImageDescriber GUI, video files appear as parent nodes in the tree with their extracted frames as children. Process the parent to process all frames.

Standalone frame extraction (no description): `idt extract-frames myvideo.mp4`

Frame rate and output directory are configurable in `video_frame_extractor_config.json`.

**Section 23: Web Image Downloads**

Both tools can scrape images from a web page:

- **CLI:** `idt workflow https://example.com/gallery`
- **GUI:** `Ctrl+U` or `File → Open URL`, enter the page address

IDT downloads all images found on the page and either loads them into the workflow (CLI) or into the ImageDescriber workspace (GUI). The source URL appears in the description metadata.

For detailed options and rate limiting: see `docs/WEB_DOWNLOAD_GUIDE.md`.

**Section 24: HEIC/HEIF Support**

Photos from iPhone and many modern cameras arrive as HEIC files. IDT handles these automatically:

- Workflow auto-converts HEIC → JPEG before describing, GPS metadata preserved
- Standalone: `idt convert-images ~/iPhone/Photos` converts an entire folder with no workflow run

No manual intervention needed; HEIC is treated identically to JPEG throughout.

**Section 25: Geocoding and Location Metadata**

When images contain GPS coordinates (iPhone photos, GPS-enabled cameras), IDT can reverse-geocode those coordinates into place names ("Eiffel Tower, Paris, France") and include them in descriptions.

Enable via `metadata_extraction` in `image_describer_config.json`. Results are cached in `geocode_cache.json` to avoid redundant API calls across runs — running the same images twice doesn't re-geocode.

**Section 26: Monitoring Costs for Cloud Models**

After processing with OpenAI or Claude, the number of input tokens (prompt + image encoding) and output tokens (description) is stored in the image metadata. View these in ImageDescriber's description panel. Cross-reference with published pricing from OpenAI (platform.openai.com/docs/pricing) or Anthropic (anthropic.com/pricing) to calculate your actual cost per image.

`idt stats` aggregates this across an entire workflow run with cost estimates pre-calculated.

Rules of thumb:
- GPT-4o mini cost is typically $0.001–0.003 per image
- Claude 3.5 Haiku is similar
- Ollama (local) is always free

**Section 27: Understanding Workflow Output**

Every workflow run creates a self-contained directory:

```
wf_2026-03-28_120000_moondream_narrative/
├── image_descriptions.txt     ← plain text, one block per image
├── descriptions.html           ← open in browser; thumbnails + descriptions
├── workflow_metadata.json      ← model, prompt, timestamps, image count
└── logs/
    ├── workflow.log
    └── image_describer.log
```

Multiple runs on the same folder create independent `wf_*` directories. Nothing is overwritten. This design lets you:
- Compare two models side by side on the same photos
- Recount with a better prompt after seeing initial results
- Always have a record of every run

`idt combinedescriptions` merges these into a single spreadsheet with one row per unique image and one column per workflow run.

**Section 28: Performance Tips**

*Local models (Ollama):*
- Moondream averages 2–5 seconds per image on modern hardware
- LLaVA 7B averages 8–15 seconds per image
- Mac Apple Silicon and NVIDIA GPUs significantly accelerate Ollama — no configuration needed; it's automatic
- Leave Ollama running between sessions; first request after a long idle causes a model reload

*Cloud models:*
- Use a small `batch_delay` (2–5 seconds) in config to avoid rate limit errors on large batches
- GPT-4o mini and Claude 3.5 Haiku are the most cost-effective cloud options
- `image_max_size` in config reduces image resolution before encoding — often no quality loss in descriptions

*Large jobs:*
- Test prompt and model on 10 images before committing to thousands
- `Processing → Process All Undescribed` fills gaps instead of re-describing everything
- Save a `.idw` workspace file frequently — it lets you resume an interrupted batch job

---

### Part 8 — Reference and Troubleshooting

**Section 29: Quick Command Reference**

| Command | Description |
|---|---|
| `idt guideme` | Interactive wizard — best starting point |
| `idt workflow <path>` | Run workflow on a folder or URL |
| `idt viewer [path]` | Open Viewer GUI |
| `idt imagedescriber [path]` | Open ImageDescriber GUI |
| `idt prompteditor` | Open Prompt Editor |
| `idt configure` | Open Configuration Manager |
| `idt extract-frames <video>` | Extract frames from a video |
| `idt convert-images <dir>` | Convert HEIC to JPEG |
| `idt descriptions-to-html <dir>` | Rebuild HTML report |
| `idt combinedescriptions` | Export all workflows to CSV/Excel |
| `idt stats` | Performance and cost analysis |
| `idt contentreview` | Description quality analysis |
| `idt results-list` | List workflow directories |
| `idt check-models` | List installed Ollama models |
| `idt prompt-list` | List available prompt styles |
| `idt version` | Show version |
| `idt help` | Show help |

**Section 30: ImageDescriber Keyboard Shortcuts**

| Key | Action |
|---|---|
| `P` | Process selected image |
| `B` | Toggle batch mark on selected image |
| `F` | Ask follow-up question about selected image |
| `C` | Open AI chat |
| `Ctrl+L` | Load a folder |
| `Ctrl+U` | Open URL (download images from web page) |
| `Ctrl+S` | Save workspace |

**Section 31: Troubleshooting**

*Ollama not responding / models not loading:*
- Verify Ollama is running: `ollama list`
- Start it manually: `ollama serve`
- Firewall may be blocking port 11434

*App won't open on macOS (Gatekeeper blocks it):*
- Right-click the app → Open → Open (bypasses Gatekeeper for unsigned apps)
- Done once; subsequent launches work normally

*SmartScreen warning on Windows:*
- Click "More info" → "Run anyway"
- The app is not code-signed; this is expected at this stage

*API key not recognized:*
- Check the variable is set: `echo $OPENAI_API_KEY` (macOS) or `echo %OPENAI_API_KEY%` (Windows)
- Watch for trailing spaces or newlines in `~/openai.txt`
- Verify the key is active at the provider's dashboard

*Descriptions are empty or very short:*
- Image may be below minimum size (~224×224 px recommended)
- Try converting format: `idt convert-images <dir>` then retry
- For Ollama: first run after a long idle causes a model reload delay — wait and retry

*Workflow output directory not found:*
- Output lands in the directory where you ran `idt workflow`, not the source folder
- Run `idt results-list` to find all `wf_*` directories in the current folder
- Check `logs/workflow.log` in the output directory for the actual paths used

*HEIC images not converting:*
- Ensure you are running the installed executable, not a development Python script without dependencies
- In the executable, HEIC support is bundled; in dev mode, `pillow-heif` must be installed

*Batch job appears stuck:*
- Check the window title — it should show "Batch Processing: X of Y" with an incrementing count
- Check `logs/image_describer.log` in the workflow output directory
- Very large images take longer; the progress bar may not update between images

**Section 32: Getting Help**

- `idt help` and `idt <command> --help`
- Check `logs/` inside any `wf_*` directory for detailed error context
- GitHub Issues: https://github.com/kellylford/Image-Description-Toolkit/issues
- Report from within the app: `Help → Report an Issue`
- Known issues list: https://github.com/kellylford/Image-Description-Toolkit/issues

---

## Files to Create / Modify

| Action | File | Notes |
|---|---|---|
| **Create** | `docs/USER_GUIDE_COMPLETE.md` | Primary output of this plan; the new authoritative guide |
| **Update** | `docs/DOCUMENTATION_INDEX.md` | Place new guide at the top |
| **Update** | `README.md` | Change docs link to point to new guide |
| **Retire** | `docs/USER_GUIDE.md` | Add deprecation banner → new guide |
| **Retire** | `docs/MACOS_USER_GUIDE.md` | Add deprecation banner → new guide |
| **Retire** | `docs/CLI_REFERENCE.md` | Outdated (v2.0 naming); add deprecation banner → new guide |

"Retire" = add this one-liner at the very top of the file:

```
> ⚠️ This document has been superseded by [USER_GUIDE_COMPLETE.md](USER_GUIDE_COMPLETE.md).
```

---

## Verification Steps

After the guide is written, verify before publishing:

1. **Installation walk-through:** Follow Section 2 on macOS from a clean state — `idt version` should succeed
2. **Guideme wizard:** Follow Section 4 end-to-end — a `wf_*` directory should be created with descriptions
3. **CLI flags:** For each flag listed in Part 4, run `idt <command> --help` and confirm the flag exists and the description matches
4. **ImageDescriber keyboard shortcuts:** Open the app and test every shortcut listed in Section 30
5. **Web download:** Test `Ctrl+U` with a real URL and confirm images load
6. **Follow-up questions:** Press `F` after describing an image; confirm a follow-up dialog appears
7. **combinedescriptions:** Run after a few workflow runs; confirm CSV output is sorted by EXIF date
8. **Outdated content check:** Grep for `PyQt6`, `prompteditor.exe` (standalone), `v2.0` — none should appear in the new guide

---

## Decisions and Scope

- **Single Markdown file** — no mkdocs site, no multi-page structure. One file ships in the installer, renders natively on GitHub, and can be pandoc'd to PDF for offline bundling.
- **Platform callouts via blockquotes** — `> **macOS:**` / `> **Windows:**` within each section, rather than duplicating entire sections per platform.
- **No dedicated accessibility section** — accessibility is built in; it is not a feature to tout.
- **Advanced/experimental providers** (HuggingFace, MLX, NPU, Grounding DINO) — brief mention only; link to their dedicated guides. They are not ready for the typical user path.
- **Prompt Writing Guide stays separate** — `PROMPT_WRITING_GUIDE.md` is reference material worth keeping standalone; Section 21 summarizes it and links to it.
- **Build/developer docs excluded** — `BUILD_MACOS.md`, `BUILD_SYSTEM_REFERENCE.md`, `AI_ONBOARDING.md`, etc. are out of scope for a user guide.
- **Analysis tools get full coverage** — `idt stats`, `idt contentreview`, `idt combinedescriptions` are real power features currently buried; they deserve prominent placement in Part 4.

## Open Questions

1. **Version header** — Should the guide say "v4.1.0" (what docs reference) or match `VERSION` file (`4.0.0 Beta 2`)? Recommend: confirm the current shipping version and hardcode it; update as part of each release process.
2. **Installer bundling** — Should `USER_GUIDE_COMPLETE.md` be included in the `.pkg`/`.exe` as a PDF for offline users, or is the GitHub link sufficient? Recommend: include a PDF export in the DMG and as an optional install option on Windows — one `pandoc` command at build time.
3. **Prompt Editor as standalone vs. integrated** — The blog post and some docs still reference `prompteditor.exe` as a standalone. Confirm whether it still ships as standalone or is now only accessible via `Tools → Edit Prompts`. This affects Sections 11 and 15.
