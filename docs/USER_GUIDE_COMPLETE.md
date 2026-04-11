# Image Description Toolkit — User Guide

**Version 4.0.0Beta2**

---

## Table of Contents

1. [What IDT Is (and Is Not)](#1-what-idt-is-and-is-not)
2. [Installation](#2-installation)
3. [Setting Up AI Providers](#3-setting-up-ai-providers)
4. [Your First Descriptions — The `guideme` Wizard](#4-your-first-descriptions--the-guideme-wizard)
5. [Opening the ImageDescriber App](#5-opening-the-imagedescriber-app)
6. [Processing Images in ImageDescriber](#6-processing-images-in-imagedescriber)
7. [Follow-Up Questions](#7-follow-up-questions)
8. [AI Chat](#8-ai-chat)
9. [Downloading Images from the Web](#9-downloading-images-from-the-web)
10. [Viewing and Managing Results](#10-viewing-and-managing-results)
11. [Built-In Tools (Prompt Editor and Configuration Manager)](#11-built-in-tools-prompt-editor-and-configuration-manager)
12. [Exporting Descriptions](#12-exporting-descriptions)
13. [CLI Fundamentals](#13-cli-fundamentals)
14. [Running Workflows from the CLI](#14-running-workflows-from-the-cli)
15. [CLI Utility Commands](#15-cli-utility-commands)
16. [Analysis and Export Commands](#16-analysis-and-export-commands)
17. [Configuration Files](#17-configuration-files)
18. [Environment Variables and Key Files](#18-environment-variables-and-key-files)
19. [Prompt Styles — Built-In Options](#19-prompt-styles--built-in-options)
20. [Writing Custom Prompts](#20-writing-custom-prompts)
21. [Advanced Prompt Techniques](#21-advanced-prompt-techniques)
22. [Video Support](#22-video-support)
23. [Web Image Downloads](#23-web-image-downloads)
24. [HEIC/HEIF Support](#24-heicheif-support)
25. [Geocoding and Location Metadata](#25-geocoding-and-location-metadata)
26. [Monitoring Costs for Cloud Models](#26-monitoring-costs-for-cloud-models)
27. [Understanding Workflow Output](#27-understanding-workflow-output)
28. [Performance Tips](#28-performance-tips)
29. [Quick Command Reference](#29-quick-command-reference)
30. [ImageDescriber Keyboard Shortcuts](#30-imagedescriber-keyboard-shortcuts)
31. [Troubleshooting](#31-troubleshooting)
32. [Getting Help](#32-getting-help)

---

## 1. What IDT Is (and Is Not)

Countless apps exist for getting an image described. Most are aimed at describing one or two images at a time, and many require you to re-describe the image each time you want a result. IDT is not meant to replace those experiences.

IDT is for the situation where you have **dozens, hundreds, or thousands of photos or videos** you want described, with those descriptions stored permanently alongside the images. You can generate multiple descriptions for the same image using different AI models and prompts, compare them side by side, ask follow-up questions, and export the results to spreadsheets or HTML reports.

**Two tools are included:**

| Tool | Best For |
|---|---|
| **IDT** (`idt` / `idt.exe`) | Command-line batch workflows, automation, large-scale processing |
| **ImageDescriber** | Interactive sessions: per-image control, multiple descriptions, follow-up questions, built-in chat |

Both tools support local AI models (free, private, no internet required) and cloud AI models (OpenAI, Claude, and Ollama cloud models). The same images can be processed through multiple models and prompts; results accumulate rather than overwrite.

---

## 2. Installation

### macOS

**System requirements:** macOS 10.13 (High Sierra) or later.

1. Download the latest release from the [GitHub Releases page](https://github.com/kellylford/Image-Description-Toolkit/releases).
2. Open the downloaded file and drag or copy **ImageDescriber** to your Applications folder (or any location you prefer).
3. Copy the **`idt`** command-line tool to `/usr/local/bin/` so it is available in Terminal from any directory.
4. Verify the installation by opening Terminal and running:

   ```
   idt version
   ```

Both applications are code-signed for macOS and should open without any security prompts. If macOS asks you to confirm opening the app, click Open.

### Windows

**System requirements:** Windows 10 or 11.

1. Download `ImageDescriptionToolkit_Setup_vX.X.X.exe` from the [GitHub Releases page](https://github.com/kellylford/Image-Description-Toolkit/releases).
2. Run the installer. The default installation path is `C:\IDT\`.
3. The installer places these files in the install directory:
   - `idt.exe` — command-line interface
   - `imagedescriber.exe` — GUI application
4. The installer will offer to download and install **Ollama** during setup. Accept this if you want to use free local AI models (recommended for most users).
5. Verify the installation by opening a Command Prompt, changing to `C:\IDT\`, and running:

   ```
   idt version
   ```

> **Windows SmartScreen:** The application is not code-signed for Windows at this time. If SmartScreen warns you, click "More info" then "Run anyway."

---

## 3. Setting Up AI Providers

IDT supports both local and cloud AI providers. You can switch between them at any time.

### Ollama — Local, Free (Recommended Starting Point)

Ollama runs AI models entirely on your machine. No API key, no internet connection, no per-image cost. Your images never leave your computer.

**Install Ollama:**
- macOS: Download from [ollama.ai](https://ollama.ai) and run the installer.
- Windows: The IDT installer can install Ollama for you, or download from [ollama.ai](https://ollama.ai). Alternatively: `winget install Ollama.Ollama`

After installation, Ollama runs as a background service automatically.

**Download your first model.** Moondream is recommended for new users — it is fast and only 1.7 GB. Run this in Terminal (macOS) or Command Prompt (Windows):

```
ollama pull moondream
```

Other models to consider:

| Model | Size | Speed | Quality |
|---|---|---|---|
| moondream | 1.7 GB | Fastest | Good |
| llava:7b | ~4 GB | Fast | Better |
| llava:13b | ~8 GB | Moderate | High |
| llama3.2-vision | 11 GB | Slow | Excellent |
| qwen3-vl:7b | ~5 GB | Moderate | Very Good |

To see all models you have installed: `ollama list`

> **Apple Silicon (M1/M2/M3/M4 Mac):** IDT also supports the MLX provider, which runs vision models natively using Apple's Metal framework and is optimized for Apple Silicon. MLX is available as a provider option within ImageDescriber and delivers fast, high-quality results without Ollama. See Section 19 for more on choosing providers.

### Ollama Cloud Models — Free Tier and Subscription

Although Ollama started by making AI models available for local use, and this remains a cornerstone of what they offer, Ollama is increasingly making cloud models available. These run entirely in Ollama's infrastructure, so processing is not limited by the memory or hardware of your local computer — making high-quality models accessible on virtually any machine.

Ollama cloud models include a limited amount of free use and a significantly greater allowance with a subscription (around $20/month — check [ollama.com](https://ollama.com) for current pricing). Token allowances reset on a rolling basis. As a rough example, one test run of 10,000 images used approximately 9% of a weekly token allowance — but Ollama does not publish specific limits, so treat this as illustrative.

**Once set up, Ollama cloud models work identically to local models in IDT.** You select them from the same model list, use them with the same prompts, and see results the same way. There is no distinction in the interface.

Browse available cloud models at: [ollama.com/search?c=cloud](https://ollama.com/search?c=cloud)

A standout example is `kimi-k2.5` — it produces exceptionally detailed, high-quality descriptions at approximately 15 seconds per image, regardless of your local hardware.

**First-time setup for an Ollama cloud model:**

1. In Terminal (macOS) or Command Prompt (Windows), run:

   ```
   ollama run kimi-k2.5:cloud
   ```

2. The first time you use a cloud model, Ollama will display a URL. Open it in your browser to authorize your machine against your Ollama account.
3. After authorization, pull and use cloud models exactly like local ones — select them by name in IDT.

### OpenAI — Cloud, Paid

1. Create an account at [platform.openai.com](https://platform.openai.com) and obtain an API key.
2. Make the key available to IDT using any of these methods:
   - **ImageDescriber:** Open `Tools → Configure Settings` and enter your key in the OpenAI section. This is the easiest option.
   - **Environment variable:**
     - macOS: `export OPENAI_API_KEY="sk-..."` (add to `~/.zprofile` for persistence)
     - Windows: Set `OPENAI_API_KEY` in System → Environment Variables
   - **Key file:** Create a file named `openai.txt` in your home directory containing only the key (no quotes, no extra spaces or newlines).
3. Available models include GPT-4o and GPT-4o mini. Both appear in the model selector once a valid key is present.

Token usage (and therefore cost) is recorded with each description. See [Section 26](#26-monitoring-costs-for-cloud-models).

### Anthropic Claude — Cloud, Paid

1. Create an account at [console.anthropic.com](https://console.anthropic.com) and obtain an API key.
2. Make the key available using any of these methods:
   - **ImageDescriber:** Open `Tools → Configure Settings` and enter your key in the Claude section. This is the easiest option.
   - **Environment variable:** `ANTHROPIC_API_KEY`
   - **Key file:** `~/claude.txt` containing only the key
3. Available models include Claude 3.5 Haiku (fast, economical), Claude 3.5 Sonnet (balanced), and Claude Opus (highest quality).

---

## 4. Your First Descriptions — The `guideme` Wizard

The fastest way to get started with the command-line tool is `guideme`. It asks you a series of questions and then runs a complete workflow.

```
idt guideme
```

The wizard will ask:
1. Where are your images? (path to a folder, **or a website URL**)
2. Which AI provider? (Ollama, OpenAI, Claude)
3. Which model?
4. Which prompt style?

**Tip:** At the image folder step, you can type a URL (e.g. `https://example.com/gallery`) instead of a local path. `guideme` will download the images automatically and continue with the downloaded folder. No extra flags needed.

After you answer, IDT processes all images in your chosen folder and creates a workflow results directory inside a `Descriptions/` folder in your current working directory. The directory is named:

```
wf_{name}_{provider}_{model}_{prompt}_{timestamp}/
```

For example: `Descriptions/wf_Vacation2025_ollama_moondream_narrative_2026-03-31_120000/`

Inside you will find:
- `image_descriptions.txt` — all descriptions as plain text, one block per image
- `image_descriptions.html` — a browsable HTML report with thumbnails; open it in any browser
- `workflow_metadata.json` — a machine-readable summary of the run
- `logs/` — detailed per-step logs

That is all there is to a basic workflow. Run `guideme` again with a different model or prompt style and a new `wf_*` directory is created alongside the first. Nothing is ever overwritten.

---

## 5. Opening the ImageDescriber App

- **macOS:** Double-click ImageDescriber in your Applications folder.
- **Windows:** Start Menu → IDT → ImageDescriber.

**Loading images:**
- `File → Load Directory` (or `Ctrl+L`) — loads all images from a folder
- Drag and drop a folder or individual images onto the window
- `File → Open Workspace` — reloads a previously saved `.idw` workspace file

**What you see:** Image list on the left, description panel on the right.

**Status indicators** appear as a prefix on each image name in the list:
- `d{N}` — the image has N descriptions (e.g. `d1`, `d3`)
- `P` — the image is currently being processed
- `.` — the image is queued in an active batch run
- `!` — the image was paused mid-batch
- `X` — processing failed for this image

---

## 6. Processing Images in ImageDescriber

### Single Image

Select an image in the list, then press `P` or choose `Process → Process Current Image`. A dialog appears where you select the provider, model, and prompt style. The default is Ollama / Moondream / Narrative.

The description appears in the right panel when processing is complete.

### Batch Processing

**Run a batch:**
- `Process → Process Undescribed Images` — processes every image in the workspace that has no description yet (safe default; never re-processes already-described images)
- `Process → Redescribe All Images` — processes all images again, adding new descriptions alongside existing ones

The window title shows live progress: `XX%, X of Y - ImageDescriber`. During a batch run, use `Process → Show Batch Progress` to open the progress dialog, which includes a Stop button to cancel gracefully after the current image finishes.

### Multiple Descriptions per Image

Running the same image again with a different model or prompt **adds** a new description; it does not replace the existing one. An image can accumulate many descriptions from different runs. Use the description list in the right panel to navigate between them, or open `Descriptions → Show All Descriptions...` to browse descriptions across all images at once.

### Choosing Model and Prompt Style

Use the dropdowns in the sidebar before pressing `P`. To change the permanent default, use `Tools → Configure Settings`.

---

## 7. Follow-Up Questions

After an image is described, you can ask follow-up questions without re-processing the full description. This is one of the more powerful features for iterative work.

**How to use it:**
1. Select an image or an existing description.
2. Press `F`, or choose `Descriptions → Ask Followup Question`.
3. A dialog appears. Type your question — for example: "What colors are dominant?", "List all visible text in this image", or "How many people are in this photo?"
4. You can select a different model for the follow-up than was used for the original description.
5. The response is appended as a new entry in the description list.

This approach is more efficient than crafting one giant prompt upfront. Start with a narrative description to get the full scene, then use follow-up questions to drill into specific details you care about.

---

## 8. AI Chat

ImageDescriber includes a general-purpose AI chat interface. It does not require any images to be loaded.

**How to use it:**
1. Press `C`, or choose `Processing → Chat`.
2. Select your model.
3. Type your question and receive a response.
4. Press `Shift+Tab` to move to the chat history.

**Saving a chat session:** Press `Ctrl+A` to select all, then `Ctrl+C` to copy everything and paste it into another application. Full chat-to-workspace save is planned for a future release.

Chat is useful for testing a model's capabilities, asking general questions while working, or getting AI assistance without involving specific images.

---

## 9. Downloading Images from the Web

Both tools can download images from a web page and describe them.

**In ImageDescriber:** Press `Ctrl+U` or choose `File → Load Images From URL...`. Enter the URL of any web page. IDT downloads all images found on the page and loads them into the workspace for description.

**In the CLI:**
```
idt workflow https://example.com/gallery
```

IDT downloads all images from the page, processes them through your chosen model and prompt, and creates a workflow results directory. The source URL is recorded in the description metadata.

For more detail on web download behaviour and options, see `docs/WEB_DOWNLOAD_GUIDE.md`.

---

## 10. Viewing and Managing Results

**Filter bar (View menu):** Switch between viewing all images, described images only, undescribed images only, or videos only.

**Tree view:** Video files appear as parent items with their extracted frames as children. You can expand/collapse the tree to focus on specific videos.

**All Descriptions dialog:** Browse every description across all images in the workspace in one place — use `Descriptions → Show All Descriptions...` to open it. Useful for comparing results across models and prompts.

**Saving your workspace:** Press `Ctrl+S` to save a `.idw` workspace file. This persists all descriptions and processing state. Reopen the file later and pick up exactly where you left off. Workspace files are valuable for large batch jobs — save frequently.

---

## 11. Built-In Tools (Prompt Editor and Configuration Manager)

The Prompt Editor and Configuration Manager are built into ImageDescriber's Tools menu.

**`Tools → Edit Prompts`** — Prompt Editor:
- View all existing prompt templates
- Edit prompt text for any built-in style
- Add new named prompt styles
- Changes take effect immediately in the model/prompt selector

**`Tools → Configure Settings`** — Configuration Manager:
- Set API keys (OpenAI, Claude)
- Choose the default AI provider and model
- Set the default prompt style
- Adjust workflow preferences (batch delay, image size, logging)
- Provides a form-based interface that validates settings before saving

---

## 12. Exporting Descriptions

**HTML report:** Created automatically in each `wf_*` directory. Open `image_descriptions.html` in any browser. Images appear with thumbnails and their descriptions side by side.

**Plain text:** `image_descriptions.txt` in each `wf_*` directory. One block per image, with a metadata header (timestamp, model, prompt style, EXIF information). Copy and paste into any application.

**CSV or spreadsheet export:** Use `idt combinedescriptions` in a directory that contains one or more `wf_*` subdirectories. This merges all workflow runs into a single spreadsheet — see [Section 16](#16-analysis-and-export-commands) for full details.

---

## 13. CLI Fundamentals

```
idt <command> [options]
idt help
idt <command> --help
idt version
```

- **macOS:** `idt` (installed to `/usr/local/bin/idt` by default)
- **Windows:** `idt.exe` from `C:\IDT\`, or `idt` if `C:\IDT\` is in your PATH

Every command supports `--help` for detailed option documentation:

```
idt workflow --help
idt combinedescriptions --help
```

---

## 14. Running Workflows from the CLI

### Interactive — `idt guideme`

```
idt guideme
```

Prompts you for source folder or URL, provider, model, and prompt style. Recommended when you are not sure which settings to use.

### Direct — `idt workflow` / `idt describe`

```
# Process a local folder with defaults
idt describe ~/Photos/Vacation2025

# Windows
idt describe C:\Photos\Vacation2025

# idt workflow and idt describe are identical — use whichever feels natural
idt workflow ~/Photos/Vacation2025

# Specify model and prompt style
idt workflow ~/Photos --model llava:7b --prompt-style detailed

# Show live progress in the terminal
idt workflow ~/Photos --progress-status

# Process a web page (downloads images, then describes them)
idt workflow https://example.com/gallery
```

### Re-describing — `idt redescribe`

Re-run AI description on an existing workflow's images using a different model, provider, or prompt — without re-copying or re-converting images.

```bash
# Re-describe with a different model (shorthand)
idt redescribe wf_Vacation2025_ollama_moondream_narrative_20260101_120000 --model llava:13b

# Full form (identical result)
idt workflow --redescribe wf_Vacation2025_ollama_moondream_narrative_20260101_120000 --model llava:13b

# Re-describe with a cloud model, using symlinks to avoid duplicating image files
idt redescribe wf_Vacation2025_ollama_moondream_narrative_20260101_120000 \
  --provider openai --model gpt-4o --link-images

# Force a full copy instead of linking
idt redescribe wf_Vacation2025_ollama_moondream_narrative_20260101_120000 \
  --provider claude --model claude-sonnet-4-5 --force-copy
```

A new `wf_*` directory is created for the redescription run. The original workflow is untouched.

**`--link-images`** uses symlinks (macOS/Linux) or hardlinks (Windows) instead of copying image files into the new workflow directory. This saves disk space with no impact on results. Use `--force-copy` to override this and always copy.

**Output:** A `wf_{name}_{provider}_{model}_{prompt}_{timestamp}/` directory is created inside a `Descriptions/` subdirectory of the current working directory. The source folder is not modified.

Running the same command again creates a new `wf_*` directory — existing results are never overwritten. Run as many times as you like with different models or prompts to build up a collection of descriptions for comparison.

**Additional workflow flags:**

| Flag | Description |
|---|---|
| `--name <label>` | Custom label appended to the workflow directory name |
| `--steps <list>` | Run only specific steps, e.g. `--steps describe,html` (default: `video,convert,describe,html`) |
| `--timeout <seconds>` | Ollama request timeout; increase for slow hardware (default: 90) |
| `--api-key-file <file>` | Path to a file containing your API key (OpenAI or Claude) |
| `--url <url>` | Alternative to providing a URL as the positional argument |
| `--min-size <size>` | Minimum image size to download, e.g. `100KB` or `1MB` |
| `--max-images <n>` | Cap the number of images downloaded from a URL |
| `--no-alt-text` | Exclude the web page's alt-text from descriptions when downloading |
| `--no-geocode` | Disable reverse geocoding even when GPS data is present |
| `--geocode-cache <file>` | Custom path for the geocoding cache file (default: `geocode_cache.json`) |
| `--dry-run` | Show what would happen without executing |
| `--batch` | Non-interactive mode — skip post-run prompts (useful in scripts) |
| `--progress-status` | Stream INFO log lines to the terminal for live progress visibility |
| `--view-results` | After completion, print the output path and instructions for opening in ImageDescriber |
| `--config-workflow` / `--config-wf` | Path to a custom `workflow_config.json` |
| `--config-image-describer` / `--config-id` | Path to a custom `image_describer_config.json` |
| `--config-video` | Path to a custom `video_frame_extractor_config.json` |

**What the workflow does automatically:**
1. Extracts frames from any video files found in the source folder
2. Converts HEIC/HEIF images to JPEG (preserving GPS metadata)
3. Describes each image using the chosen model and prompt
4. Generates an HTML report

Individual steps can be enabled or disabled in `workflow_config.json` (see [Section 17](#17-configuration-files)).

---

## 15. CLI Utility Commands

```bash
# Extract frames from a video without running a full workflow
idt extract-frames myvideo.mp4

# Extract frames every 5 seconds
idt extract-frames myvideo.mp4 --time 5 --output-dir frames/

# Extract frames using scene-change detection (lower threshold = more frames)
idt extract-frames myvideo.mp4 --scene 30 --output-dir frames/

# Generate an AI description for a standalone video (without a full workflow)
idt describe-video myvideo.mp4 --provider ollama --model llava
idt describe-video myvideo.mp4 --frames 10 --prompt "Describe the key events in this video"

# Convert all HEIC/HEIF images in a folder to JPEG (preserves GPS metadata)
idt convert-images ~/Photos/iPhone

# Convert recursively with custom quality
idt convert-images ~/Photos/iPhone --recursive --quality 90

# Regenerate the HTML report from existing descriptions (no new AI calls)
idt descriptions-to-html Descriptions/wf_2026-03-28_ollama_moondream_narrative_120000/image_descriptions.txt

# Check all configured AI providers (Ollama, OpenAI, Claude)
idt check-models

# Check only one provider
idt check-models --provider ollama
idt check-models --provider openai --verbose

# List, install, and manage AI models
idt manage-models list
idt manage-models list --installed
idt manage-models install llava:7b
idt manage-models remove llava:7b
idt manage-models recommend

# List available prompt styles
idt prompt-list
idt prompt-list --verbose

# List all workflow result directories in the current folder
idt results-list
idt results-list --input-dir /path/to/Descriptions
```

---

## 16. Analysis and Export Commands

These commands work on the `wf_*` directories that workflow runs create. Run them from the directory that contains your workflow results.

### `idt combinedescriptions`

Merges all workflow runs in the current directory into a single spreadsheet.

```bash
# Default: sorted by photo date from EXIF data (DateTimeOriginal)
idt combinedescriptions

# Sorted alphabetically by filename instead
idt combinedescriptions --sort name

# Specify output filename
idt combinedescriptions --output my_archive.csv

# Tab-separated format
idt combinedescriptions --format tsv
```

The output is a CSV file with one row per image and one column per workflow run. Images are sorted chronologically by the date they were actually taken (from EXIF), not by filename — making this particularly useful for chronological photo archives, travel journals, or event documentation.

When you run the same images through different models or prompt styles across multiple workflow runs, `combinedescriptions` lets you compare the results side by side in a spreadsheet.

### `idt stats`

Analyzes performance and cost across all workflow runs in the current directory.

```bash
idt stats
```

Reports include: per-image timing, total throughput, token counts for cloud model runs, and estimated API costs based on published pricing for OpenAI and Claude. Run this after a cloud-model workflow to understand what you spent and extrapolate cost for larger jobs.

### `idt contentreview`

Analyzes description quality across workflow runs.

```bash
idt contentreview

# Specify input file and output location
idt contentreview --input analysis/results/combineddescriptions.csv --output my_review.csv
```

Reports vocabulary richness, description length statistics, and style consistency. Useful for comparing the output quality of different models or evaluating a new custom prompt before running it on thousands of images.

### `idt results-list`

Lists all `wf_*` workflow directories found in the current folder (or a specified directory).

```bash
idt results-list
idt results-list --input-dir /path/to/Descriptions
idt results-list --sort-by provider
idt results-list --output my_results_index.csv
```

Useful for auditing which workflows have been run, what models were used, and what percentage of images have descriptions.

---

## 17. Configuration Files

Three JSON files control toolkit behaviour. They live alongside the executables and can be edited with any text editor. The Configuration Manager (`Tools → Configure Settings` in ImageDescriber) provides a form-based interface that validates settings before saving — recommended if you are not comfortable editing JSON directly.

### `image_describer_config.json`

Controls AI model settings, prompt defaults, and image processing.

Key settings:
- `default_model` — the model used when none is specified (e.g., `moondream:latest`)
- `default_prompt_style` — the prompt style used when none is specified (e.g., `narrative`)
- `image_max_size` — maximum image dimension before sending to AI; reduces token count and cost with minimal quality impact
- `batch_delay` — seconds to wait between images; useful for avoiding rate limits with cloud providers
- `output_format` — what metadata is included alongside descriptions in output files (timestamp, model name, EXIF data)

### `workflow_config.json`

Controls the workflow pipeline.

Key settings:
- Enable or disable individual steps (video extraction, HEIC conversion, HTML generation)
- Base output directory for workflow runs
- File patterns for videos and images
- Logging verbosity

### `video_frame_extractor_config.json`

Controls frame extraction from videos.

Key settings:
- Frame extraction rate (e.g., 1 frame per second, 1 frame per 5 seconds)
- Output subdirectory name within the workflow directory

### Configuration Priority

Settings are resolved in this order (highest wins):
1. Command-line argument (e.g., `--model llava:7b`)
2. Custom config file specified at runtime
3. Config file in the IDT install directory
4. Built-in defaults

---

## 18. Environment Variables and Key Files

**API keys:**

| Method | OpenAI | Claude |
|---|---|---|
| Environment variable | `OPENAI_API_KEY` | `ANTHROPIC_API_KEY` |
| Key file in home directory | `~/openai.txt` | `~/claude.txt` |

The key file approach is often simpler for GUI users — create a plain text file containing only the key (no quotes, no extra characters).

**Configuration location:**

| Variable | Purpose |
|---|---|
| `IDT_CONFIG_DIR` | Directory to search for config files instead of the install directory |
| `IDT_IMAGE_DESCRIBER_CONFIG` | Full path to a specific `image_describer_config.json` |

---

## 19. Prompt Styles — Built-In Options

IDT includes seven built-in prompt styles. The prompt text shown below is sent verbatim to the AI model along with the image.

### narrative (Default)

**Prompt text:**
```
Provide a narrative description including objects, colors and detail.
Avoid interpretation, just describe.
```

Natural, flowing prose. The best default for personal photo archives, alt text, and general-purpose use. Output reads well when spoken aloud. Typical length: 200–400 words.

---

### detailed

**Prompt text:**
```
Describe this image in detail, including:
- Main subjects/objects
- Setting/environment
- Key colors and lighting
- Notable activities or composition
Keep it comprehensive and informative for metadata.
```

Structured output with sections. Best for digital asset management, photo databases, and anywhere you need searchable, consistent metadata. Models that support structured output (GPT-4o, Claude, qwen3-vl) will generate markdown-formatted sections. Smaller local models will produce narrative text regardless.  Typical length: 400–800 words.

---

### concise

**Prompt text:**
```
Describe this image concisely, including:
- Main subjects/objects
- Setting/environment
- Key colors and lighting
- Notable activities or composition.
```

Covers all essential elements in a shorter form. Good for large batches where storage or processing cost matters, or when you want a quick overview without extensive detail. Typical length: 100–200 words.

---

### artistic

**Prompt text:**
```
Analyze this image from an artistic perspective, describing:
- Visual composition and framing
- Color palette and lighting mood
- Artistic style or technique
- Emotional tone or atmosphere
- Subject matter and symbolism
```

Interpretive and analytical. Discusses composition, technique, mood, and may reference art movements. Best for art collections, photography portfolios, and museum catalogs. Typical length: 300–500 words.

---

### technical

**Prompt text:**
```
Provide a technical analysis of this image:
- Camera settings and photographic technique
- Lighting conditions and quality
- Composition and framing
- Image quality and clarity
- Technical strengths or weaknesses
```

Focuses on photographic technique, inferred camera settings, lighting, and image quality. Best for photography education, technical reviews, and quality control workflows. Typical length: 250–400 words.

---

### colorful

**Prompt text:**
```
Give me a rich, vivid description emphasizing colors, lighting, and visual
atmosphere. Focus on the palette, color relationships, and how colors contribute
to the mood and composition.
```

Emphasizes color vocabulary, palette relationships, and visual atmosphere. Best for interior design documentation, fashion and product photography, and visual mood boards. Typical length: 200–400 words.

---

### simple

**Prompt text:**
```
Describe.
```

Gives the model no structure or direction. Output is entirely model-dependent — typically 50–150 words of unguided description. Useful for testing a model's baseline behaviour or for very lightweight processing. Output quality and format vary widely across models.

---

### Choosing a Prompt Style

Quick decision guide:

| Your goal | Recommended style |
|---|---|
| General personal photo archive | `narrative` |
| Digital asset management / cataloging | `detailed` |
| Large-scale processing, cost-sensitive | `concise` or `simple` |
| Art or photography portfolio | `artistic` |
| Camera / image quality review | `technical` |
| Interior design, color analysis | `colorful` |
| Testing a model baseline | `simple` |

**Match prompt complexity to model capability.** Small local models (moondream, llava:7b) will not follow the structure in `detailed` or `technical` — they will produce narrative text regardless. Reserve complex prompts for larger models (llama3.2-vision, GPT-4o, Claude, qwen3-vl).

---

## 20. Writing Custom Prompts

You can write any prompt you want in place of the built-in styles.

**In ImageDescriber:** Type directly in the Custom Prompt field in the sidebar before pressing `P`. To save it as a named style for future use, open `Tools → Edit Prompts`.

**In the CLI:** There is no inline `--custom-prompt` flag. To use a custom prompt from the CLI, add it to the config file first (see below) and then pass its name with `--prompt-style`.

**In the config file:** Set `prompt_template` in `image_describer_config.json` to change the default for all runs.

### Adding a Named Custom Prompt Style

Open `scripts/image_describer_config.json`, locate the `"prompt_variations"` section, and add your prompt:

```json
{
  "prompt_variations": {
    "narrative": "...",
    "my_custom_prompt": "Your custom instruction text here."
  }
}
```

Use it with: `idt workflow ~/Photos --prompt-style my_custom_prompt`

### Custom Prompt Examples

**E-commerce product listings:**
```
Describe this product image for an online store. Include: product type, key features,
colors, materials, and any text visible on the product. Focus on details a buyer
needs to make a purchase decision.
```

**Historical photo archives:**
```
Describe this historical photograph. Note: time period indicators (clothing, vehicles,
architecture), number of people and their activities, location details, and any text
or signage. Remain objective; avoid speculation about context not visible in the image.
```

**Real estate:**
```
Describe this property image emphasizing: room type, size, condition, style and finishes,
lighting, furnishings, and special features. Highlight positive aspects while remaining
accurate.
```

**Scientific or medical imaging:**
```
Provide a factual, objective description. Include: specimen or subject type, visible
structures, scale indicators, labeling or annotations, imaging technique (if evident),
and notable characteristics. Use appropriate technical terminology.
```

### Tips for Effective Custom Prompts

- Be specific about what to include ("focus on people and their expressions")
- Specify output format when it matters ("respond as a numbered list", "one sentence only")
- Include context that shapes interpretation ("this is for a museum exhibit on 1970s fashion")
- Keep prompts under 200 words — longer prompts don't reliably improve results and increase token cost
- Avoid contradictions ("be concise" followed by "provide comprehensive detail")
- Test on 5–10 sample images before running thousands

---

## 21. Advanced Prompt Techniques

### Prompt Chaining

Process the same images multiple times with different prompts to build layered descriptions:

```bash
# First pass: general scene
idt workflow ~/Photos --prompt-style narrative --model moondream

# Second pass: color and atmosphere
idt workflow ~/Photos --prompt-style colorful --model llava:13b

# Third pass: metadata for cataloging
idt workflow ~/Photos --prompt-style detailed --model llama3.2-vision
```

Each run creates a separate `wf_*` directory. Run `idt combinedescriptions` afterward to merge all three into a spreadsheet with one column per run.

### Using Multiple Models on the Same Images

Run the same prompt through different models to compare quality:

```bash
idt workflow ~/Photos --prompt-style detailed --model moondream
idt workflow ~/Photos --prompt-style detailed --model llava:13b
idt workflow ~/Photos --prompt-style detailed --model llama3.2-vision
```

Use `idt combinedescriptions` to compare the three descriptions for each image side by side.

### Follow-Up Questions for Iterative Detail

Rather than crafting one complex prompt, start with `narrative` to get the overall scene, then use follow-up questions (press `F` in ImageDescriber) to explore specific aspects:

1. Run `narrative` on all images
2. Open ImageDescriber and load the workspace
3. For any image, press `F` and ask: "What text is visible in this image?"
4. Ask another follow-up: "Estimate how many people are present"

Follow-up responses are appended to the description list and saved with the workspace.

### Prompt Tuning for Specific Models

Some models respond better to specific phrasing:

**For moondream (simple models, keep it minimal):**
```
Describe what you see in this image.
```

**For qwen3-vl or GPT-4o (use structure to get structure):**
```
Provide a comprehensive description with these sections:
1. Main subjects
2. Environment
3. Colors and lighting
4. Composition
5. Notable details
```

**For Claude (be precise and systematic):**
```
Analyze this image systematically: visual elements, spatial relationships, color palette,
lighting, compositional technique, and contextual details. Use clear section headings.
```

---

## 22. Video Support

Drop video files (MP4, MOV, AVI, MKV, and others) into your source folder alongside images. The workflow handles them automatically:

1. Frames are extracted at a configurable rate
2. Each frame inherits the video's timestamp as EXIF data
3. Frames are described using the same model and prompt as your images

In ImageDescriber, video files appear as parent items in the image tree with their extracted frames as children. Select the parent to process all frames at once.

**Standalone frame extraction** (without running a full workflow):
```bash
idt extract-frames myvideo.mp4
idt extract-frames myvideo.mp4 --time 5 --output-dir frames/
idt extract-frames myvideo.mp4 --scene 30
```

**Standalone video description** (describe a video file directly, without a full workflow):
```bash
idt describe-video myvideo.mp4
idt describe-video myvideo.mp4 --provider openai --model gpt-4o --frames 10
idt describe-video myvideo.mp4 --prompt "Describe the key events in this video"
```

Extracts frames, sends them to the AI model, and returns a description. Output can be written to a `.txt` or `.json` file with `--output`.

Frame rate and output directory configuration: `video_frame_extractor_config.json` (see [Section 17](#17-configuration-files)).

---

## 23. Web Image Downloads

Both tools can download images from a public web page and describe them.

**CLI:**
```
idt workflow https://example.com/gallery
```

**ImageDescriber:** Press `Ctrl+U` or choose `File → Open URL`, then enter the page address.

IDT downloads all images found on the page. The source URL is recorded in the description metadata. Downloads are rate-limited.

For advanced options: see `docs/WEB_DOWNLOAD_GUIDE.md`.

---

## 24. HEIC/HEIF Support

Photos shot on iPhone, iPad, or most modern cameras often arrive as HEIC files. IDT converts them automatically before describing:

- **In a workflow:** HEIC images are converted to JPEG (with GPS metadata preserved) transparently. You do not need to do anything.
- **Standalone conversion:** `idt convert-images ~/Photos/iPhone` converts an entire folder without running a full workflow.

HEIC images are treated identically to JPEG throughout the toolkit.

---

## 25. Geocoding and Location Metadata

When images contain GPS coordinates, IDT can reverse-geocode those coordinates into human-readable place names (e.g., "Eiffel Tower, Paris, France") and include the location in descriptions and metadata.

Enable this via the `metadata_extraction` setting in `image_describer_config.json`, or through `Tools → Configure Settings`.

Results are cached in `geocode_cache.json` — running the same images again does not make additional geocoding API calls.

---

## 26. Monitoring Costs for Cloud Models

After processing with OpenAI or Claude, the number of input tokens (prompt + image) and output tokens (description) is stored with each image's metadata. View these in ImageDescriber's description panel.

Estimated costs are pre-calculated by `idt stats`. Cross-reference with published pricing:
- OpenAI: [platform.openai.com/docs/pricing](https://platform.openai.com/docs/pricing)
- Anthropic: [anthropic.com/pricing](https://anthropic.com/pricing)

**Approximate cost per 100 images (October 2025 pricing):**

| Model | Cost per 100 images |
|---|---|
| GPT-4o | $0.50–$2.00 |
| GPT-4o mini | $0.05–$0.20 |
| Claude Opus | $3.00–$6.00 |
| Claude Sonnet 3.5 | $0.50–$1.50 |
| Claude Haiku 3.5 | $0.10–$0.40 |
| Any Ollama model | Free |

**Tips for managing cost:**
- Use `concise` or `narrative` prompt styles instead of `detailed` — detailed prompts generate 2–3× more output tokens
- Use `image_max_size` in config to reduce image resolution before encoding — often no impact on description quality
- Test on 10 images before committing a large batch to a cloud model
- Use `idt stats` after any cloud run to see actual token counts

---

## 27. Understanding Workflow Output

Every workflow run creates a self-contained directory:

```
wf_2026-03-28_ollama_moondream_narrative_120000/
├── image_descriptions.txt     ← one block per image, with metadata header
├── image_descriptions.html    ← open in browser; thumbnails + descriptions
├── workflow_metadata.json     ← model, prompt, timestamps, image count
└── logs/
    ├── workflow.log
    └── image_describer.log
```

Multiple runs on the same folder produce independent `wf_*` directories. Nothing is overwritten. This lets you:
- Compare the same images described by different models
- Iterate on prompt style and see the effect without losing previous results
- Always have a record of every run for auditing or comparison

`idt combinedescriptions` merges these into a single spreadsheet: one row per image, one column per workflow run.

---

## 28. Performance Tips

### Local Models (Ollama)

- Moondream: 0.5–2 seconds per image on most modern hardware
- LLaVA 7B: 2–3 seconds per image
- LLaVA 13B: 3–5 seconds per image
- llama3.2-vision: 5–15 seconds per image depending on hardware
- First request after Ollama has been idle causes a model reload. This is normal; subsequent requests are fast.

### Ollama Cloud Models

- Processing happens in Ollama's cloud, so local hardware has no impact on speed or model availability
- `kimi-k2.5`: approximately 15 seconds per image, exceptional description quality
- Token allowances reset on a rolling basis; limits are not publicly documented — as one example, 10,000 images used approximately 9% of a weekly allowance (see [ollama.com](https://ollama.com) for current plan details)

### Cloud Models

- Use `batch_delay` (2–5 seconds in config) to avoid rate limit errors on large batches
- GPT-4o mini and Claude Haiku 3.5 offer the best cost-to-quality ratio for large-scale cloud processing
- Set `image_max_size` in config to reduce token count — images are resized before encoding with minimal impact on description quality

### Large Jobs

- Test your prompt and model on 10 images before running thousands
- `Processing → Process All Undescribed` fills gaps in a partially-processed workspace rather than re-describing everything
- Save your `.idw` workspace file frequently — it lets you resume interrupted batch jobs exactly where you left off
- Use `idt results-list` to get an overview of all workflow runs and their status

---

## 29. Quick Command Reference

| Command | Description |
|---|---|
| `idt guideme` | Interactive wizard — best starting point |
| `idt workflow <path>` | Run workflow on a local folder or URL |
| `idt describe <path>` | Alias for `idt workflow` — same flags, same behavior |
| `idt redescribe <wf_dir>` | Re-describe an existing workflow with a different model/provider |
| `idt extract-frames <video>` | Extract frames from a video file |
| `idt describe-video <video>` | Generate an AI description for a standalone video file |
| `idt convert-images <dir>` | Convert HEIC/HEIF images to JPEG |
| `idt descriptions-to-html <file.txt>` | Regenerate HTML report from existing descriptions |
| `idt combinedescriptions` | Export all workflows to a CSV or TSV spreadsheet |
| `idt stats` | Performance and cost analysis across workflow runs |
| `idt contentreview` | Description quality and vocabulary analysis |
| `idt results-list` | List all workflow result directories in current folder |
| `idt check-models` | Check available AI models (Ollama, OpenAI, Claude) |
| `idt manage-models list` | List known models across all providers |
| `idt manage-models install <model>` | Install an Ollama model by name |
| `idt manage-models recommend` | Show recommended models for this system |
| `idt prompt-list` | List available prompt styles |
| `idt version` | Show version information |
| `idt help` | Show all commands |

---

## 30. ImageDescriber Keyboard Shortcuts

| Key | Action |
|---|---|
| `P` | Process current image |
| `R` or `F2` | Rename selected item |
| `M` | Add a manual description to selected image |
| `F` | Ask a follow-up question about selected image |
| `C` | Open AI chat |
| `Ctrl+L` | Load a folder |
| `Ctrl+U` | Load images from a URL |
| `Ctrl+S` | Save workspace |
| `Ctrl+V` | Paste image from clipboard |

---

## 31. Troubleshooting

**Ollama not responding / models not loading**

- Verify Ollama is running: `ollama list`
- Start it manually: `ollama serve`
- Check whether a firewall is blocking port 11434

**API key not recognized**

- macOS: `echo $OPENAI_API_KEY` — verify the variable is set and not empty
- Windows: `echo %OPENAI_API_KEY%`
- Check for trailing spaces or a newline in `~/openai.txt`
- Verify the key is active in the provider's dashboard (platform.openai.com or console.anthropic.com)

**Descriptions are empty or very short**

- Image may be below the minimum usable size (~224×224 pixels); IDT will still attempt it but results may be poor
- For HEIC files: try `idt convert-images <dir>` first, then re-describe the converted JPEGs
- For Ollama: the first request after a long idle period causes a model reload; wait a moment and retry
- Check `logs/image_describer.log` in the workflow directory for specific error messages

**Workflow output directory not found**

- Output is created in the directory where you ran `idt workflow`, not in the source image folder
- Run `idt results-list` to find all `wf_*` directories in the current folder
- Check `logs/workflow.log` for the full path that was written

**Batch job appears stuck**

- The window title should show `XX%, X of Y - ImageDescriber` with an incrementing count
- Very large images take longer; the count does not update until an image finishes
- Check `logs/image_describer.log` for errors
- Open `Process → Show Batch Progress` for a progress dialog with a Stop button to cancel gracefully after the current image

**HEIC images not processing**

- Run the installed application, not a development Python script — HEIC support requires the `pillow-heif` library which is bundled in the executable but must be separately installed in development environments

---

## 32. Getting Help

- `idt help` — show all available commands
- `idt <command> --help` — detailed options for any command
- `logs/` inside any `wf_*` directory — detailed per-step log files
- **Report an issue from within the app:** `Help → Report an Issue`
- **GitHub Issues:** [github.com/kellylford/Image-Description-Toolkit/issues](https://github.com/kellylford/Image-Description-Toolkit/issues)
- **Known issues:** [github.com/kellylford/Image-Description-Toolkit/issues](https://github.com/kellylford/Image-Description-Toolkit/issues)
