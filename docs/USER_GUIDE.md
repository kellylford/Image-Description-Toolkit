# Image Description Toolkit — User Guide

**Version 4.5** · [Report an issue](https://github.com/kellylford/Image-Description-Toolkit/issues)

---

## Overview

**Image Description Toolkit (IDT)** is a batch AI-powered tool for generating human-quality text descriptions of images and video frames. It supports accessibility workflows, alt-text authoring, image cataloging, and archival documentation.

IDT includes three standalone applications that share the same AI provider infrastructure:

| Application | What it is | Best for |
|---|---|---|
| **idt** | Command-line tool | Automation, scripting, batch pipelines, server use |
| **ImageDescriber** | Desktop GUI application | Interactive editing, reviewing, visual workflow |
| **IDT Chat** | Accessible chat client | Talking to any supported AI model, about anything |

`idt` and ImageDescriber produce the same workspace bundles (`.idtw`) — a `.idtw` bundle is a **folder** (directory), not a compressed archive. It contains image copies, description sidecars, logs, and reports. You can start a job in the CLI and review results in the GUI—or vice versa.

**IDT Chat is not about images.** It is a general-purpose chat client that happens to ship with an image toolkit, built for keyboard and screen reader use. See [Part 7](#part-7-idt-chat).

### Supported AI Providers

| Provider | CLI name | GUI name | Type | API Key | Available on |
|---|---|---|---|---|---|
| Ollama | `ollama` | `ollama` | Local | No | Windows, macOS |
| Ollama Cloud | — | `ollama_cloud` | Cloud (self-hosted) | No | GUI only |
| Anthropic Claude | `anthropic` | `claude` | Cloud | Yes | Windows, macOS |
| OpenAI GPT | `openai` | `openai` | Cloud | Yes | Windows, macOS |
| MLX (Apple Silicon) | — | `mlx` | Local | No | ImageDescriber only, macOS Apple Silicon |

---

## Part 1: Getting Started

### System Requirements

**Windows (both tools)**

- Windows 10 or 11 (64-bit)
- 4 GB RAM minimum; 8 GB recommended for local AI models
- Internet connection for cloud AI providers (Claude, GPT)
- Optional: NVIDIA GPU with CUDA for faster local models

**macOS (both tools)**

- Apple Silicon (M1/M2/M3) for the published build; Intel Macs need to build from source
- 8 GB RAM minimum; 16 GB recommended for local AI
- Internet connection for cloud AI providers

**For local Ollama models**

- Ollama installed: [https://ollama.com](https://ollama.com)
- At least one vision model pulled (e.g., `ollama pull minicpm-v4.6`)

**For HEIC/HEIF image support (iPhone photos)**

- `pillow-heif` Python package installed (`pip install pillow-heif`)
- Nothing else. `pillow-heif` bundles its own decoder, and the packaged Windows and
  macOS builds ship it, so HEIC works out of the box there

**For video support**

- FFmpeg installed (used for frame extraction and GPS metadata)

### Installation on Windows

**Option 1: Pre-built executables (recommended)**

1. Download `idt.exe` and `ImageDescriber.exe` from the [releases page](https://github.com/kellylford/Image-Description-Toolkit/releases).
2. Place them in any folder on your system—no installation required.
3. To run `idt` from any terminal: add the folder to your `PATH` environment variable (Control Panel → System → Advanced → Environment Variables).
4. Launch `ImageDescriber.exe` by double-clicking.

**Option 2: From source**

```bat
git clone https://github.com/kellylford/Image-Description-Toolkit.git
cd Image-Description-Toolkit

:: Create virtual environment
python -m venv .winenv
call .winenv\Scripts\activate.bat

:: Install dependencies
pip install -r requirements.txt

:: Run CLI
python idt/idt_cli.py describe --help

:: Run GUI
python imagedescriber/imagedescriber_wx.py
```

### Installation on macOS

**Option 1: Pre-built app bundle (recommended)**

1. Download `ImageDescriber.app` and `idt` from the [releases page](https://github.com/kellylford/Image-Description-Toolkit/releases).
2. Drag `ImageDescriber.app` to your `/Applications` folder.
3. Copy `idt` to `/usr/local/bin/` and mark it executable:
   ```bash
   sudo cp idt /usr/local/bin/idt
   sudo chmod +x /usr/local/bin/idt
   ```

**Option 2: From source**

```bash
git clone https://github.com/kellylford/Image-Description-Toolkit.git
cd Image-Description-Toolkit

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run CLI
python idt/idt_cli.py describe --help

# Run GUI
python imagedescriber/imagedescriber_wx.py
```

### Setting Up API Keys

IDT uses environment variables for API keys so they are never stored in your workspace bundles.

**Anthropic Claude**

1. Sign up at [console.anthropic.com](https://console.anthropic.com).
2. Create an API key.
3. Set the environment variable:
   - **Windows (permanent):** Control Panel → System → Environment Variables → New: `ANTHROPIC_API_KEY` = your key
   - **Windows (current session):** `set ANTHROPIC_API_KEY=sk-ant-...`
   - **macOS/Linux:** Add `export ANTHROPIC_API_KEY="sk-ant-..."` to `~/.zshrc` or `~/.bashrc`

**OpenAI GPT**

1. Sign up at [platform.openai.com](https://platform.openai.com).
2. Create an API key.
3. Set the environment variable: `OPENAI_API_KEY`

**Ollama (no key required)**

1. Install Ollama from [ollama.com](https://ollama.com).
2. Pull a vision-capable model:
   ```bash
   ollama pull minicpm-v4.6     # 1.6 GB, excellent on all hardware
   ollama pull llava             # 7 GB, higher quality
   ollama pull moondream:latest  # 1.8 GB, fastest
   ```
3. Ollama runs automatically as a background service once installed.

### Updating IDT

**Let IDT tell you (easiest)**

IDT checks for updates itself. Once a day at most, shortly after ImageDescriber
starts, it quietly asks GitHub whether a newer version exists. If there is nothing
new it says nothing; it only speaks up when there is an update. You can also ask at
any moment with **Help → Check for Updates...**, and turn the automatic check off
with **Help → Automatically Check for Updates** (the manual check still works when
it's off).

When an update is found you get three choices:

| Choice | What happens |
|---|---|
| Download | Fetches the new version (see below) |
| Skip This Version | You are never asked about that particular version again |
| Later | Ask again tomorrow |

- **Windows:** Download fetches the installer, closes ImageDescriber, and runs it.
  Windows asks for administrator permission, because IDT installs to the root of
  your system drive.
- **macOS:** Download saves the disk image to your Downloads folder and shows it in
  Finder. Quit ImageDescriber, then drag the new ImageDescriber to Applications.

**One update covers both tools.** The Windows installer and the macOS disk image each
contain `idt` *and* ImageDescriber, so updating from either one updates both.

From the command line, `idt update` reports your installed version, whether a newer
one exists, and where to get it. It does not install anything itself.

The check reads the public GitHub releases list and nothing else — no account, no
telemetry, no data sent.

**Installing an update by hand**

1. Download the latest installer (Windows) or disk image (macOS) from the [releases page](https://github.com/kellylford/Image-Description-Toolkit/releases).
2. Run the installer, or drag the new `ImageDescriber.app` to `/Applications`. If you use the standalone executables instead, replace the old `idt.exe` and `ImageDescriber.exe` in your folder.
3. Your existing `.idtw` workspace bundles and `~/.idt/config.json` settings are preserved — no migration needed.

**From source**

```bash
git pull origin main
pip install -r requirements.txt   # pick up any new dependencies
```

If you installed via a virtual environment, activate it first (`.winenv\Scripts\activate.bat` on Windows, `source venv/bin/activate` on macOS).

### Uninstalling IDT

**Pre-built executables**

1. Delete `idt.exe` and `ImageDescriber.exe` (or `ImageDescriber.app` on macOS) from your system.
2. To remove configuration and cache data, delete the `~/.idt/` directory:
   - **Windows:** `rmdir /s %USERPROFILE%\.idt`
   - **macOS/Linux:** `rm -rf ~/.idt`
3. Your `.idtw` workspace bundles are not removed — delete them manually if desired.

**From source**

1. Delete the cloned repository folder.
2. Remove the virtual environment folder (`.winenv` on Windows, `venv` on macOS).
3. Delete `~/.idt/` as above.

### Quick Start: Your First Description

**Using the CLI**

```bash
# Describe a single folder of images using Ollama (no API key needed)
idt describe ~/Pictures/Vacation

# With Claude for highest quality
idt describe ~/Pictures/Vacation --provider anthropic --model claude-opus-4-6

# If you've never run idt before, the interactive wizard walks you through everything
idt guideme
```

**Using the GUI**

1. Launch `ImageDescriber` (double-click the app or run `ImageDescriber.exe`).
2. Choose **File → New Workspace** (or press `Ctrl+N`).
3. Choose **File → Load Directory** (`Ctrl+L`) and select your image folder.
4. Choose **Process → Process Undescribed Images**.
5. Select your AI provider and model in the dialog, then click **OK**.
6. Watch the Batch Progress dialog as descriptions are generated.
7. When done, choose **File → Export Descriptions** or **File → Export HTML Gallery**.

---

## Part 2: The idt Command-Line Tool

### How idt Works

`idt` processes images in four automatic steps:

1. **Video extraction** — Any video files are converted to image frames (skippable with `--no-video`).
2. **HEIC conversion** — Apple HEIC/HEIF images are converted to JPEG in memory.
3. **AI description** — Each image is sent to the chosen AI provider.
4. **Output generation** — An HTML report is produced automatically (skippable with `--no-export`).

All results are stored in a workspace bundle (`.idtw` directory). Source images are **never modified**.

### Command Reference

#### idt describe — Generate Descriptions

The primary command. Processes every image in a folder (or workspace) and stores AI-generated descriptions.

```
idt describe <source> [options]
```

**Arguments**

| Argument | Description |
|---|---|
| `<source>` | Folder containing images, a `.idtw` workspace bundle, or `-` to read paths from stdin |

**Provider and Model Options**

| Option | Default | Description |
|---|---|---|
| `--provider {anthropic\|ollama\|openai}` | From config | AI provider to use |
| `--model NAME` | Provider default | Model name (e.g., `claude-opus-4-6`, `gpt-4o`, `minicpm-v4.6`) |
| `--ollama-host URL` | `http://localhost:11434` | Ollama server address |

**Prompt Options**

| Option | Default | Description |
|---|---|---|
| `--prompt NAME` | `detailed` | Named prompt style (see `idt prompts`) |
| `--prompt-text TEXT` | — | Custom prompt text; overrides `--prompt` |

**Metadata and Location**

| Option | Default | Description |
|---|---|---|
| `--no-metadata` | Off | Disable EXIF extraction |
| `--geocode` | Off | Reverse-geocode GPS coordinates to city/state (requires internet; ~1 second per unique location) |

**Processing Control**

| Option | Default | Description |
|---|---|---|
| `--limit N` | Unlimited | Stop after describing N images (useful for testing) |
| `--redescribe` | Off | Re-describe already-described images (adds new description, keeps old ones) |
| `--workspace PATH` | Auto-created | Path or name for the workspace bundle |
| `--no-video` | Off | Skip automatic video frame extraction |
| `--video-interval SECONDS` | 5.0 | Seconds between extracted video frames |
| `--show-descriptions` | Off | Print each description to the terminal as it's generated |
| `--quiet, -q` | Off | Minimal output; in stdin mode, prints `filename TAB description` |

**Output Control**

| Option | Default | Description |
|---|---|---|
| `--embed` | Off | Embed descriptions into image metadata copies after processing |
| `--no-export` | Off | Skip automatic HTML report generation |

**Examples**

```bash
# Describe all images in a folder using Claude
idt describe ~/Photos/Trip --provider anthropic --model claude-opus-4-6

# Resume an interrupted job (pass the workspace bundle)
idt describe ~/Photos/Trip.idtw

# Test with first 5 images only
idt describe ~/Photos/Trip --limit 5

# Use a custom prompt
idt describe ~/Photos/Trip --prompt-text "Describe this image for someone who cannot see it."

# Include GPS location in every description
idt describe ~/Photos/Trip --geocode

# Process, then embed descriptions into image copies automatically
idt describe ~/Photos/Trip --embed

# Suppress HTML export (faster for scripting)
idt describe ~/Photos/Trip --no-export --quiet
```

---

#### idt guideme — Interactive Setup Wizard

A screen-reader-friendly step-by-step wizard for first-time users. Guides you through selecting a provider, choosing images, and running your first description job.

```
idt guideme
```

The wizard uses numbered choices throughout, no ANSI codes, and supports pressing `b` to go back one step. When the job completes it offers to open the HTML report.

---

#### idt download — Download Web Images

Download images from a web page and optionally describe them in one step.

```
idt download <url> [directory] [options]
```

**Arguments**

| Argument | Description |
|---|---|
| `<url>` | Web page URL to scrape for images |
| `[directory]` | Workspace name or path (default: derived from the URL's domain, under the workspace root — see `idt config`) |

**Options**

| Option | Default | Description |
|---|---|---|
| `--max N` | Unlimited | Maximum number of images to download |
| `--min-size WxH` | None | Skip images smaller than this (e.g., `200x200`) |
| `--timeout SECONDS` | 30 | HTTP request timeout |
| `--describe` | Off | Automatically describe downloaded images |
| `--embed` | Off | Embed descriptions after describing (requires `--describe`) |
| `--preserve-alt-text` / `--no-preserve-alt-text` | From config (`preserve_alt_text`, on by default) | Save existing HTML alt text as its own description (model `Website Alt Text`), in addition to any AI-generated one |
| `--redescribe` / `--no-redescribe` | On | With `--describe`, generate an AI description even for images whose alt text was preserved as a description. Turn off to keep alt-text-only images and skip the AI call for them. |
| `--provider`, `--model`, `--prompt`, `--prompt-text` | — | AI options (same as `idt describe`) |
| `--quiet, -q` | Off | Minimal output |

**Where images land:** `idt download` uses the same `.idtw` workspace model as `idt describe` (see [Workspaces (.idtw)](#workspaces-idtw) below) — it never writes into an old-style `.idt` sibling folder. Downloaded images are copied into `<workspace>.idtw/derived/downloads/<page title>-<timestamp>/` and registered as workspace items, so `idt describe`, `idt status`, `idt show`, and the ImageDescriber GUI can all see them. With `[directory]` omitted, the workspace is named after the URL's domain (e.g. `nytimes.com.idtw`) and created under the workspace root (`~/Documents/idt` by default). Running `idt download` against the same site again reuses that same workspace — each run just adds a new timestamped batch — so history accumulates per site instead of scattering across one-off folders. Pass `[directory]` (a bare name or a full path) to target a different or explicitly named workspace, exactly like `idt describe --workspace`.

The command captures the original HTML `alt` attribute from each `<img>` tag alongside the downloaded image. By default (`preserve_alt_text` config, on) that alt text is stored two ways: as prompt context, and (when non-trivial — at least 3 characters and containing a space, to filter out bare filenames) as its own description entry, so it shows up in the workspace history alongside the AI-generated description for comparison.

**Examples**

```bash
# Download all images from a page
idt download https://example.com/gallery ./my-images

# Download and immediately describe, limit to 20 images
idt download https://news-site.com --max 20 --describe --prompt aialttext

# Download, describe, and embed in one pass
idt download https://news-site.com --describe --embed --provider anthropic
```

---

#### idt video — Extract Video Frames

Extract frames from video files, with optional AI description of the frames.

```
idt video <source> [options]
```

**Arguments**

| Argument | Description |
|---|---|
| `<source>` | A video file or directory containing video files |

**Extraction Options** (choose one)

| Option | Default | Description |
|---|---|---|
| `--interval SECONDS` | 5.0 | Extract one frame every N seconds (good for continuous footage) |
| `--scene THRESHOLD` | — | Scene-change detection (0–100; lower = more sensitive; good for events) |
| `--max-frames N` | Unlimited | Maximum frames to extract per video |

**Description Options**

| Option | Default | Description |
|---|---|---|
| `--describe` | Off | Describe extracted frames |
| `--provider`, `--model`, `--prompt`, `--prompt-text` | — | AI options |
| `--quiet, -q` | Off | Minimal output |

**Supported video formats:** `.mp4`, `.mov`, `.avi`, `.mkv`, `.m4v`, `.wmv`, `.mts`, `.m2ts`

**Examples**

```bash
# Extract a frame every 2 seconds from a concert video
idt video concert.mp4 --interval 2

# Extract scene changes only and describe them
idt video birthday.mp4 --scene 30 --describe --provider anthropic

# Extract frames from every video in a folder
idt video ~/Videos --interval 5 --describe
```

---

#### idt embed — Embed into Image Metadata

Copy described images and write AI descriptions into the image metadata so descriptions travel with the file.

```
idt embed <source> [options]
```

| Option | Description |
|---|---|
| `--force` | Re-embed even images already embedded |
| `--dry-run` | Show what would be embedded without writing files |
| `--quiet, -q` | Minimal output |

**Metadata written by file type**

| Format | Metadata fields written |
|---|---|
| JPEG / TIFF | EXIF `UserComment` (shows in Windows Explorer "Comments"), XMP `dc:description` |
| PNG | `tEXt` chunk "Description", `iTXt` XMP chunk |
| WebP | EXIF `UserComment`, XMP `dc:description` |
| HEIC | Converted to JPEG first; then JPEG fields written |

Embedded copies are saved to `<workspace>/embedded/`. Original source files are **never modified**.

**Examples**

```bash
# Preview what would be embedded
idt embed ~/Photos/Trip --dry-run

# Embed all described images
idt embed ~/Photos/Trip

# Force re-embed even if already done
idt embed ~/Photos/Trip --force
```

---

#### idt export — Generate Reports

Generate an HTML, CSV, or plain-text report from a workspace.

```
idt export <source> [--format {html|csv|txt}] [--quiet]
```

| Format | Description |
|---|---|
| `html` (default) | Accessible HTML report with skip navigation, landmark regions, image thumbnails, and full descriptions. Works without JavaScript. |
| `csv` | Spreadsheet-compatible; one row per image with columns: file, source\_path, workspace, description, model, provider, prompt\_name, timestamp, metadata\_context, input\_tokens, output\_tokens, alt\_text |
| `txt` | Plain text, one entry per image |

Reports are saved to `<workspace>/reports/`.

---

#### idt show — Print Descriptions

Print descriptions to the terminal. Useful for piping to other tools.

```
idt show <target> [options]
```

| Option | Description |
|---|---|
| `--json` | Output JSONL (one JSON object per line) |
| `--quiet, -q` | Suppress headers and separators |

**JSON output fields:** `file`, `source`, `described`, `description`, `model`, `provider`, `timestamp`, `metadata_context`, `metadata`, `alt_text`

**Examples**

```bash
# Show all descriptions in a folder
idt show ~/Photos/Trip

# Output as JSON for piping to jq or Python
idt show ~/Photos/Trip --json | jq '.description'

# Extract all descriptions to a text file
idt show ~/Photos/Trip --quiet > descriptions.txt
```

---

#### idt status — Check Progress

Show how many images have been described in a workspace or folder tree.

```
idt status <directory> [--all] [--json] [--quiet]
```

| Option | Description |
|---|---|
| `--all` | Scan all IDT workspaces under the given directory |
| `--json` | JSON output |
| `--quiet, -q` | Minimal output |

---

#### idt stats — Token Usage and Costs

Summarize token counts and estimated API costs across one or more workspaces.

```
idt stats <source> [--all] [--json]
```

Output includes: total images, descriptions written, per-provider token counts, and estimated cost in USD. Local models (Ollama) do not report token usage.

---

#### idt combine — Merge Multiple Projects

Walk a directory tree, find all IDT workspaces, and merge their descriptions into a single CSV or TSV file.

```
idt combine <directory> [options]
```

| Option | Default | Description |
|---|---|---|
| `--output FILE` | stdout | Output file path |
| `--format {csv\|tsv}` | `csv` | Output format |
| `--sort {date\|file\|timestamp}` | `timestamp` | Sort order |

The `date` sort uses EXIF `DateTimeOriginal` first, falling back to file modification time.

---

#### idt watch — Continuous Monitoring

Describe undescribed images in a folder, then keep polling for new files.

```
idt watch <directory> [options]
```

| Option | Default | Description |
|---|---|---|
| `--interval SECONDS` | 30 | Polling interval |
| `--provider`, `--model`, `--prompt` | — | AI options |
| `--quiet, -q` | Off | Tab-separated output for piping |

Press `Ctrl+C` to stop. Useful for monitoring a downloads folder or a folder receiving uploads.

---

#### idt models — List Available Models

Show which models are available from each provider.

```
idt models [--provider NAME] [--ollama-host URL] [--json] [--refresh] [--all]
```

**Options**

| Option | Description |
|---|---|
| `--provider` | `ollama`, `anthropic`, or `openai`. Omit to check all three |
| `--ollama-host URL` | Ollama service address. Default `http://localhost:11434` |
| `--json` | Machine-readable output |
| `--refresh` | Ignore the cached list and ask the APIs right now |
| `--all` | Include every model the API reports, skipping the filter that hides non-chat OpenAI models (speech, images, embeddings) |

Every provider is asked what *your account* can actually use, rather than showing a list built into the app:

- **Ollama** — queries the running Ollama service.
- **Claude and OpenAI** — query the provider's model list using your API key. The result is cached for 24 hours, so the command is instant after the first run and keeps working with no network. Without an API key you get the built-in list instead.

Models the app has no details for still appear, marked `new — details unknown`. That is deliberate: a model released today shows up today, rather than waiting for the next version of IDT. Token budgeting falls back to a conservative default for those until IDT records the real figures.

Models your account cannot use simply do not appear. Previously they stayed on the list and failed only when you tried to use them.

**Examples**

```bash
idt models
```

```bash
idt models --provider openai --refresh
```

Descriptions and costs come from IDT's own records. When a model is too new for IDT to know about, the row says so rather than guessing.

---

#### idt chat — Talk to a Model

Multi-turn conversation from the terminal. Unrelated to images: this is a general-purpose chat command that happens to share the toolkit's provider setup.

```
idt chat [--provider NAME] [--model ID] [--system TEXT] [--message TEXT]
         [--resume ID] [--list] [--no-save] [--max-tokens N]
         [--temperature F] [--quiet]
```

**Options**

| Option | Description |
|---|---|
| `--provider` | `ollama`, `claude` (or `anthropic`), or `openai`. Default `ollama` |
| `--model` | Model id. Defaults to the provider's default |
| `--system TEXT` | System prompt for the conversation |
| `--attach PATH` | Attach a file to the first message. Repeat for several. HEIC is converted to JPEG |
| `--message`, `-m` | Send one message and exit instead of going interactive |
| `--resume ID` | Continue a saved conversation |
| `--list` | List saved conversations and exit |
| `--no-save` | Do not write the conversation to disk |
| `--max-tokens N` | Cap the reply length |
| `--temperature F` | Sampling temperature |
| `--quiet`, `-q` | Suppress status notes on stderr |

**Examples**

```bash
idt chat
```

```bash
idt chat --provider claude --system "Answer in one sentence." --message "What is HEIC?"
```

```bash
idt chat --provider ollama --model llava --attach photo.jpg --message "What is in this picture?"
```

```bash
idt chat --list
```

```bash
idt chat --resume chat_a1b2c3d4e5f6
```

Responses stream as they arrive. `Ctrl+C` stops a reply and keeps what arrived; `Ctrl+D` or `/quit` exits. Inside an interactive session, `/system TEXT` sets the system prompt and `/tokens` reports usage.

Conversations are saved to `~/.idt/chats/` in the same format the GUI uses, so they can be opened in [IDT Chat](#part-7-idt-chat).

Ollama needs no API key. Claude and OpenAI read `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`, or a key configured in ImageDescriber.

---

#### idt prompts — List Prompt Styles

Print all available prompt names and descriptions.

```
idt prompts [--json]
```

---

#### idt config — User Configuration

View or update default settings.

```
idt config [--set KEY=VALUE]
```

**Valid keys**

| Key | Description |
|---|---|
| `default_provider` | AI provider: `anthropic`, `ollama`, `openai` |
| `default_model` | Model name for the provider |
| `default_prompt_name` | Default prompt style |
| `workspace_root` | Root folder for workspaces (default: `~/Documents/idt`) |

**Examples**

```bash
# Show current settings
idt config

# Set Claude as default
idt config --set default_provider=anthropic
idt config --set default_model=claude-opus-4-6

# Change workspace root
idt config --set workspace_root=~/MyDescriptions
```

Configuration is stored in `~/.idt/config.json`.

---

#### idt version — Display Version

```
idt version
```

Prints the application version, Python version, and executable path. Never touches
the network — use `idt update` to check for a newer release.

#### idt update — Check for a Newer Release

```
idt update
```

Asks GitHub whether a newer release exists and prints where to get it:

```
Installed: idt 4.5.0
Available: idt 4.5.1

Download:  https://github.com/kellylford/Image-Description-Toolkit/releases/download/v4.5.1/ImageDescriptionToolkitSetup-4.5.1-windows.exe
Installing it updates both idt and ImageDescriber.
```

This command is notify-only — it downloads and installs nothing. Run the installer
yourself, or use ImageDescriber's **Help → Check for Updates...**, which can download
and launch it for you. Either way, one installer updates both tools.

If the check fails (no internet, GitHub unreachable) it says so rather than claiming
you are up to date.

---

### Workspaces (.idtw)

A workspace is a folder ending in `.idtw` that holds all job state: image copies, description sidecars, logs, and reports. You never need to edit workspace files directly—both tools manage them automatically.

**Structure**

```
MyTrip.idtw/
  manifest.json          Job metadata, defaults, CLI command history
  images/                Copies of source images (originals untouched)
  descriptions/          JSON sidecars — one per image
  derived/
    converted/           HEIC → JPEG conversions
    frames/              Extracted video frames
  logs/                  Processing logs
  embedded/              Images with embedded metadata (created by idt embed)
  reports/               HTML, CSV, and TXT exports
```

**Resuming an interrupted job**

Pass the `.idtw` bundle path to `idt describe` to continue where you left off:

```bash
idt describe MyTrip.idtw
```

Only undescribed images are processed. Existing descriptions are preserved.

**Sharing workspaces**

The `.idtw` bundle is portable. If you include image copies (`images/` subfolder), you can zip and share the entire bundle and the recipient can open it in ImageDescriber or run `idt show` on it without having the original source folder.

---

### Metadata and Geocoding

By default, `idt describe` extracts EXIF metadata from each image and prepends context to the AI prompt:

```
Context: Munich, Germany  Sep 12, 2024  iPhone 14 Pro

[your prompt text]
```

This significantly improves description quality for photos taken with smartphones or DSLR cameras.

**Extracted fields:** capture date/time, GPS coordinates, camera make and model, lens model.

**Geocoding** (opt-in with `--geocode`) reverses GPS coordinates to a human-readable place name using OpenStreetMap Nominatim. It requires an internet connection and adds approximately one second per unique location. Results are cached in `~/.idt/geocode_cache.json`.

To disable all metadata extraction: `--no-metadata`.

---

### Environment Variables

| Variable | Used by | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | idt, GUI | Anthropic Claude API key |
| `OPENAI_API_KEY` | idt, GUI | OpenAI API key |
| `IDT_CONFIG_DIR` | idt, GUI | Override default config directory |
| `IDT_IMAGE_DESCRIBER_CONFIG` | idt, GUI | Explicit path to config file |

---

## Part 3: The ImageDescriber GUI

### Application Overview

ImageDescriber is a wxPython desktop application for interactively managing image descriptions. It shares the same workspace format as the CLI, so you can freely mix both tools.

The application has two modes:

- **Editor Mode** — Create workspaces, add images, process descriptions, and export results.
- **Viewer Mode** — Read-only review of descriptions from a completed workspace or CLI workflow.

### Menu Reference

#### File Menu

| Item | Shortcut | Description |
|---|---|---|
| New Workspace | Ctrl+N | Create a new empty workspace |
| Open Workspace (.idtw)... | Ctrl+O | Open a saved workspace bundle |
| Save Workspace | Ctrl+S | Save the current workspace |
| Save Workspace As... | — | Save with a new name |
| Load Directory | Ctrl+L | Add images from a folder |
| Refresh Folder from Disk... | Ctrl+Shift+R | Rescan a folder for new or missing files |
| Load Images From URL... | Ctrl+U | Download and import images from a web page |
| Import Workflow (to Workspace)... | — | Import descriptions from a CLI workflow output |
| Export Descriptions... | — | Save descriptions as text or HTML |
| Embed Descriptions into Images... | — | Write descriptions into image metadata |
| Export HTML Gallery... | Ctrl+Shift+H | Create an interactive HTML image gallery |
| Workspace Statistics... | Ctrl+I | Show statistics: counts, tokens, costs, providers |
| Open Workflow Result (Viewer Mode)... | — | Open a CLI workflow result in Viewer Mode |
| Exit | Ctrl+Q | Close the application |

#### Edit Menu

| Item | Shortcut | Description |
|---|---|---|
| Cut | Ctrl+X | Cut text from focused field |
| Copy | Ctrl+C | Copy selected text |
| Paste | Ctrl+V | Paste text or an image from clipboard |
| Select All | Ctrl+A | Select all text in focused field |

#### Process Menu

| Item | Description |
|---|---|
| Process Current Image | Generate a description for the selected image |
| Process Undescribed Images | Batch-process only images that have no description |
| Redescribe All Images | Re-process all images (adds new descriptions alongside existing ones) |
| Show Batch Progress | Show the batch progress dialog |
| Update Image List (F5) | Refresh the image list |
| Refresh AI Models | Reload available models from all providers |
| Chat with AI Model (Ctrl+T) | Open the interactive chat window |
| Convert HEIC Files... | Convert HEIC/HEIF images to JPEG |
| Extract Video Frames... | Extract frames from video files |
| Describe Video with AI... | Generate an AI description for a video |
| Rename Item | Rename the selected image or folder |

#### Descriptions Menu

| Item | Description |
|---|---|
| Add Manual Description | Type a description by hand |
| Ask Followup Question | Ask the AI a follow-up question about the selected image |
| Edit Description... | Edit an existing description |
| Delete Description | Remove a description |
| Copy Description | Copy description text to clipboard |
| Copy Image Path | Copy the file path to clipboard |
| Copy Image | Copy the image file to clipboard |
| Copy Image + Description | Copy both image and description text |
| Show All Descriptions... | List all descriptions in a dialog |

#### View Menu

| Item | Description |
|---|---|
| **Application Mode** → Editor Mode | Switch to the workspace editor |
| **Application Mode** → Viewer Mode | Switch to the read-only viewer |
| **Filter** → All Items | Show all images, videos, and chats (Ctrl+Shift+A) |
| **Filter** → Described Only | Show only images with at least one description (Ctrl+Shift+D) |
| **Filter** → Undescribed Only | Show only images lacking a description (Ctrl+Shift+U) |
| **Filter** → Videos Only | Show video files and their extracted frames |
| **Filter** → Chats Only | Show saved chat sessions |
| Show Image Previews | Toggle the image thumbnail panel |
| Find Images... (Ctrl+F) | Show or hide the search bar |

#### Tools Menu

| Item | Shortcut | Description |
|---|---|---|
| Edit Prompts... | Ctrl+Shift+P | Create, edit, and manage AI prompt templates |
| Configure Settings... | Ctrl+Shift+C | Open the settings dialog |
| Install Ollama... | — | Instructions for installing the local Ollama server |
| Install FFmpeg (for video GPS)... | — | Instructions for installing FFmpeg |
| Export Configuration... | — | Save settings to a file |
| Import Configuration... | — | Load settings from a file |
| **AI Info** → Ollama Models... | — | View installed Ollama models |
| **AI Info** → OpenAI Usage Dashboard... | — | Open OpenAI usage tracking |
| **AI Info** → Claude Usage Dashboard... | — | Open Anthropic usage tracking |
| **AI Info** → MLX Community Models... | — | Browse HuggingFace MLX models |

#### Help Menu

| Item | Description |
|---|---|
| User Guide... | Open this guide |
| Report an Issue... | Go to the GitHub issue tracker |
| Check for Updates... | Ask GitHub right now whether a newer version exists |
| Automatically Check for Updates | Toggle the once-a-day check at startup (on by default) |
| About | Show version information |

---

### The Main Window Layout

The main window is divided into three areas.

**Left panel: Image list**

A hierarchical tree showing all items in the workspace:

- Folder nodes (expandable) — represent subfolder groups from your source directory
- Video nodes (expandable) — videos with their extracted frames as child items
- Image items — individual files with status icons:
  - `[✓]` — has at least one description (screen readers announce "described")
  - `[ ]` — no description yet (screen readers announce "undescribed")
  - `[!]` — file no longer exists on disk (screen readers announce "missing"; descriptions preserved)
- Chat nodes — saved conversation sessions

Use **View → Find Images** (`Ctrl+F`) to show a search bar that filters by filename, description text, or metadata content. Supports `and` / `or` operators: for example, `house and garage or backyard`.

**Right panel: Description area**

When an image is selected:

- **Description list** — All descriptions for this image, showing provider/model and date. Click a description to view or edit its text.
- **Generate Description button** — Processes the selected image with the current AI settings.
- **Save Description button** — Saves edits made to the description text.

**Bottom right: Metadata and text editor**

- **Image preview** — Thumbnail of the selected image (toggle with **View → Show Image Previews**).
- **Description text editor** — Full text of the selected description. You can edit it directly and save with the **Save Description** button.
- Below the text: metadata appended automatically: provider, model, prompt style, creation date, capture date, GPS location, camera info, and token counts.

**Status bar**

The bar at the bottom of the window shows:
- Left: Current action or status message.
- Right: Workspace summary (e.g., "250 images, 180 described").

---

### Working with Workspaces

**Creating a workspace**

1. **File → New Workspace** creates an empty workspace named "Untitled".
2. **File → Load Directory** adds a folder of images. Check **Add to existing workspace** to add a second folder without starting over.
3. **File → Save Workspace As...** saves the bundle as `MyTrip.idtw` in the location you choose.

**Opening an existing workspace**

- **File → Open Workspace (.idtw)...** to browse for a bundle.
- Drag-and-drop a `.idtw` folder onto the application window.

**Refreshing after changes on disk**

If you add new images to the source folder after loading:

- **File → Refresh Folder from Disk...** (`Ctrl+Shift+R`) — rescans the folder and adds new files. Images marked `[!]` (file deleted) are noted but their descriptions are kept.

**Workspace statistics**

**File → Workspace Statistics...** (`Ctrl+I`) shows:

- Image and description counts
- Content metrics and description length distribution
- AI provider and model breakdown
- Token usage and estimated cost
- Location information summary
- Processing timeline

---

### Batch Processing

**Starting a batch job**

1. Choose **Process → Process Undescribed Images** (or **Redescribe All Images** to re-process everything).
2. The **Processing Options** dialog appears:
   - **Provider** — Ollama, OpenAI, Claude, or MLX.
   - **Model** — Populated from the chosen provider.
   - **Prompt Style** — Choose a built-in style or enter custom text.
   - **Enable Geocoding** — Reverse-geocode GPS coordinates to place names.
   - **Embed After Processing** — Automatically embed descriptions into image copies when the batch finishes.
3. Click **OK** to start. The **Batch Progress** dialog opens.

You can also right-click a folder node in the image list and choose **Process Folder** to batch only that folder.

**The Batch Progress dialog**

| Element | Description |
|---|---|
| Statistics display | Shows current count, average time per image, estimated time remaining, and current filename |
| Progress bar | Visual percentage complete |
| Pause / Resume | Temporarily pause and resume the batch |
| Stop | Cancel the batch (descriptions generated so far are kept) |
| Close | Hide the dialog; processing continues in the background |

**Video files in a batch**

Videos in the folder are automatically extracted to frames before the AI step. The default extraction interval is every 5 seconds; you can change this in **Tools → Configure Settings**.

---

### The Chat Window

Open with **Process → Chat with AI Model** (`Ctrl+T`). Choose a provider and model in the prompt dialog.

The chat window is a general-purpose, multi-turn conversation with the AI model of your choice. It is not limited to images — use it for anything, including:

- Asking follow-up questions about a description you generated
- Requesting alternative phrasing
- Exploring accessibility phrasing options
- Any other question you would ask a chat assistant

**Layout**

- **Conversation history** (ListBox) — All messages, navigable with arrow keys. Screen readers announce new messages automatically.
- **Message detail pane** — Full text of the selected message. Editable so you can select and copy from it; edits are not saved.
- **Input field** — Type your message. `Enter` sends; `Shift+Enter` starts a new line.
- **Attach Files** — Attach images to the conversation. Shown only for providers that accept attachments; Claude also accepts PDFs. You can also paste an image straight from the clipboard with `Ctrl+V`.
- **Change Model** — Switch provider or model mid-conversation. History is kept.
- **Token usage** — Shows how much of the model's context window the conversation is using.

**Starting a chat does not attach the image you have selected.** Every chat begins empty. To ask about a specific image, attach it with **Attach Files** or paste it from the clipboard.

Chat sessions are saved with the workspace and appear as chat items in the item list. Press `Enter` on a saved chat to resume it — the full conversation history is restored, so the model retains context. Attachments from earlier turns are not re-attached when resuming.

---

### Viewer Mode

**View → Application Mode → Viewer Mode** switches the application to a read-only display of all descriptions in the current workspace or workflow result.

This mode is also used when opening a CLI `idt describe` output via **File → Open Workflow Result (Viewer Mode)...**.

In Viewer Mode:
- Descriptions cannot be edited.
- **Live monitoring** is available: the view auto-refreshes when new descriptions arrive (useful when running `idt describe` in a terminal and watching progress in the GUI simultaneously).

---

### Export Options

**Export Descriptions (text or HTML)**

**File → Export Descriptions...** saves descriptions to:

- **Text file (.txt)** — Plain text with sections for each image: filename, capture date, and description.
- **HTML file (.html)** — Styled table with images and descriptions. Suitable for sharing in email or a web browser.

**Export HTML Gallery**

**File → Export HTML Gallery...** (`Ctrl+Shift+H`) produces an interactive gallery:

- Responsive design (works on desktop and mobile browsers)
- Thumbnails with full descriptions visible on click
- Search built in
- No server required; open directly in any browser
- Customizable title

**Embed Descriptions into Images**

**File → Embed Descriptions into Images...**

Options in the dialog:

| Option | Description |
|---|---|
| **Which description** → Latest | Embed the most recently generated description (recommended) |
| **Which description** → All Combined | Join all descriptions with a separator and embed the combined text |
| **Write mode** → Copy (recommended) | Create new image copies in the output folder; originals untouched |
| **Write mode** → In-place | Modify the original files directly (requires confirmation) |
| **Output folder** | Browse to choose where copies are saved |

Embedded copies mirror the subfolder structure of the source.

---

### Keyboard Shortcuts

See [Appendix D: Keyboard Shortcut Reference](#appendix-d-keyboard-shortcut-reference) for the full table.

**Tab order in the main window:**

Image list → Description list → Description text editor (Shift+Tab to move backward)

All menu items, buttons, and interactive controls are reachable by keyboard. Arrow keys navigate the image list and description list. Space activates checkboxes and radio items.

---

## Part 4: AI Providers

> **Provider names differ between CLI and GUI.** Use this mapping table as a quick reference:
>
> | CLI name | GUI name | Notes |
> |---|---|---|
> | `anthropic` | `claude` | Same provider; Anthropic Claude models |
> | `ollama` | `ollama` | Same name in both |
> | `openai` | `openai` | Same name in both |
> | — | `ollama_cloud` | GUI only; remote Ollama server |
> | — | `mlx` | GUI only; Apple Silicon local models |

### Ollama — Local (Windows and macOS)

Ollama runs AI models on your own machine. No internet connection is required after the model is downloaded. No data leaves your computer.

**CLI and GUI provider name:** `ollama`

**Setup**

1. Install Ollama from [ollama.com](https://ollama.com).
2. Pull a vision-capable model:

   ```bash
   # Recommended: best quality across all hardware (1.6 GB)
   ollama pull minicpm-v4.6

   # Highest quality (requires CUDA GPU or Apple Silicon, 7+ GB)
   ollama pull llama3.2-vision

   # Smallest / fastest (CPU-only, 1.8 GB)
   ollama pull moondream:latest
   ```

3. Ollama starts automatically as a background service.

**Using a remote Ollama server (CLI)**

```bash
idt describe ~/Photos --provider ollama --model minicpm-v4.6 --ollama-host http://192.168.1.100:11434
```

In the GUI, a separate **Ollama Cloud** provider (`ollama_cloud`) handles remote Ollama connections — configure the host URL in **Tools → Configure Settings**.

**Recommended models**

| Model | Size | Notes |
|---|---|---|
| `minicpm-v4.6` | 1.6 GB | Excellent quality; works on all hardware including ARM Windows |
| `llava` | 4–7 GB | Solid accuracy; CPU or GPU |
| `llama3.2-vision` | 7+ GB | Higher quality; best on Apple Silicon or CUDA GPU |
| `moondream:latest` | 1.8 GB | Fastest; CPU-only capable |
| `qwen2-vl:7b` | 7 GB | Good balance of speed and quality |

---

### Anthropic Claude — Cloud (Windows and macOS)

Claude models produce the highest quality, most detailed descriptions. Requires an internet connection and an Anthropic API key.

**CLI provider name:** `anthropic` · **GUI provider name:** `claude`

**Setup:** Set `ANTHROPIC_API_KEY` in your environment (see [Setting Up API Keys](#setting-up-api-keys)).

**Available models**

IDT asks Anthropic which models your account can use, so the list in every picker is the real one rather than a copy baked into the app. Run `idt models --provider anthropic` to see yours. A few of the common ones:

| Model | Characteristics |
|---|---|
| `claude-opus-5` | Flagship; highest intelligence and description depth |
| `claude-sonnet-5` | Best balance of speed and intelligence |
| `claude-opus-4-8` | Most intelligent 4.x model; strong value |
| `claude-haiku-4-5-20251001` | Fastest Claude model; very good quality |

Your account may show more or fewer than these. A model Anthropic has released since your copy of IDT was built appears too, marked `new — details unknown`.

**CLI example**

```bash
idt describe ~/Photos --provider anthropic --model claude-opus-5 --prompt detailed
```

---

### OpenAI GPT — Cloud (Windows and macOS)

Requires an OpenAI API key. Good for workflows already integrated with OpenAI.

**CLI and GUI provider name:** `openai`

**Setup:** Set `OPENAI_API_KEY` in your environment.

**Available models**

As with Claude, IDT asks OpenAI what your account can use. Run `idt models --provider openai` to see yours — most accounts have far more than the handful listed here.

| Model | Characteristics |
|---|---|
| `gpt-5.2` | Best available; highest quality vision and reasoning |
| `gpt-5-mini` | Faster, efficient GPT-5 |
| `gpt-5-nano` | Fastest and most affordable GPT-5 |
| `o4-mini` | Fast cost-efficient reasoning |
| `o3` | Powerful reasoning for complex tasks |

OpenAI's account list also contains speech, image-generation, embedding and moderation models, which cannot describe pictures or hold a conversation. IDT hides those so the picker stays usable with a keyboard and screen reader. If something you need is missing, `idt models --provider openai --all` shows the unfiltered list.

**CLI example**

```bash
idt describe ~/Photos --provider openai --model gpt-5.2
```

---

### MLX — Apple Silicon Local (ImageDescriber only, macOS)

MLX runs vision models directly on Apple Silicon (M1/M2/M3/M4) using Apple's Metal GPU via the `mlx-vlm` library. It is the fastest local option on Mac and produces quality comparable to small Ollama models. **MLX is only available in ImageDescriber.** It does not appear in the CLI, and IDT Chat does not offer it: that build deliberately omits the MLX libraries, which would take it from about 40 MB to around 350 MB. For chat that is a poor trade, because Ollama now runs several models through MLX on Apple Silicon itself — chatting with Ollama on a Mac already gets you the Metal acceleration. To chat with an MLX model directly, use ImageDescriber's own chat window. The picker hides the option rather than showing one that would fail when chosen.

**GUI provider name:** `mlx`

**Setup**

To enable it, install the `mlx-vlm` package into the same Python environment that runs ImageDescriber:

```bash
# Activate the GUI's virtual environment first, then:
pip install mlx-vlm
```

Models are downloaded automatically on first use from HuggingFace Hub and cached in `~/.cache/huggingface/hub/`.

**Available models (select in GUI; you can also type any HuggingFace MLX repo ID)**

| Model | Size | Notes |
|---|---|---|
| `mlx-community/Qwen3-VL-4B-Instruct-4bit` | ~3.1 GB | **Recommended default** — best quality/speed balance |
| `mlx-community/Qwen3-VL-8B-Instruct-4bit` | ~5.8 GB | Higher quality; 16 GB+ Mac recommended |
| `mlx-community/Qwen2-VL-2B-Instruct-4bit` | ~1.5 GB | Fastest Qwen option |
| `mlx-community/gemma-3-4b-it-qat-4bit` | ~2.5 GB | Strong English descriptions |
| `mlx-community/phi-3.5-vision-instruct-4bit` | ~2.5 GB | Good at text and fine detail |
| `mlx-community/SmolVLM-Instruct-4bit` | ~0.5 GB | Smallest; very fast, shorter descriptions |
| `mlx-community/Llama-3.2-11B-Vision-Instruct-4bit` | ~6.5 GB | High quality; 16 GB+ Mac recommended |

---

## Part 5: Prompts and Customization

### Built-In Prompt Styles

IDT ships with a library of prompt styles tuned for different use cases. List them with `idt prompts`.

| Name | Description |
|---|---|
| `narrative` | Flowing description with spatial organization (left-to-right, foreground/background) |
| `detailed` | Structured sections: SUBJECT, SETTING, COLORS, COMPOSITION, DETAILS |
| `concise` | Brief 2–3 sentence summary |
| `artistic` | Visual qualities with bullet points; accessible language |
| `technical` | Lighting, composition, and quality evaluation (no camera speculation) |
| `colorful` | Emphasizes specific color names (crimson, navy, ivory, etc.) |
| `simple` | One-sentence basic description |
| `accessibility` | Optimized for screen reader context; emphasizes spatial relationships |
| `comparison` | Uses analogies to familiar objects |
| `mood` | Emotional atmosphere and psychological tone |
| `functional` | Focuses on purpose, action, and utility |
| `aialttext` | Produces three website alt-text options at 25, 50, and 100 words |

**Sample outputs for the same image** (a photo of a golden retriever on a beach at sunset):

| Style | Sample output |
|---|---|
| `simple` | A golden retriever sits on a sandy beach at sunset. |
| `concise` | A golden retriever rests on a sandy beach, silhouetted against a warm orange sunset over calm ocean waters. |
| `detailed` | **SUBJECT:** A golden retriever sitting on sand. **SETTING:** Beach at sunset, ocean in background. **COLORS:** Golden fur, orange sky, blue-gray water, tan sand. **COMPOSITION:** Dog centered in foreground, horizon line in upper third. **DETAILS:** Dog faces the camera, tongue out, waves gently lapping at shoreline. |
| `narrative` | On the left, gentle waves roll onto a tan sandy beach. Centered in the foreground, a golden retriever sits facing the camera with its tongue out. Behind the dog, the ocean stretches to the horizon where a warm orange sunset fills the sky. |
| `aialttext` | **25 words:** Golden retriever sitting on sandy beach at sunset facing camera. **50 words:** A golden retriever with tongue out sits on a sandy beach in the foreground, silhouetted against a vibrant orange sunset over calm ocean waters. **100 words:** A golden retriever sits centered on a tan sandy beach, facing the camera with its tongue hanging out. Behind the dog, gentle waves lap at the shoreline. The ocean extends to the horizon where a warm orange and yellow sunset fills the sky. The lighting creates a silhouette effect on the dog's fur. |

---

### Creating Custom Prompts

**Via the CLI config file**

Add prompts to `~/.idt/config.json`:

```json
{
  "custom_prompts": {
    "museum_label": "Write a museum exhibit label for this artwork. Use 50–75 words. Begin with the most visually striking element.",
    "ecommerce": "Describe this product image for an e-commerce listing. Focus on visible features, materials, and condition. Avoid speculation about what is not visible."
  }
}
```

Then use them like any built-in style: `idt describe ~/Photos --prompt museum_label`

**Via the GUI Prompt Editor**

See [The Prompt Editor (GUI)](#the-prompt-editor-gui) below.

---

### The Prompt Editor (GUI)

**Tools → Edit Prompts...** (`Ctrl+Shift+P`) opens the prompt editor.

**Left panel:** List of all available prompts (built-in and custom).

**Right panel:** Editor showing:
- **Prompt name** — Editable; must be unique.
- **Prompt text** — Full text editor with character count.

**Buttons:**
- **Add New** — Create a new prompt from a blank template.
- **Duplicate** — Clone the selected prompt as a starting point.
- **Delete** — Remove a custom prompt (built-in prompts cannot be deleted, only overridden).

The **Default Settings** section at the bottom of the dialog lets you set the default provider, model, and prompt for all new batch jobs.

---

## Part 6: Advanced Features

### Video Frame Extraction

IDT extracts still frames from video files before describing them. The AI then describes each frame as an image.

**In the CLI:** Video extraction happens automatically when you run `idt describe` on a folder containing videos. Opt out with `--no-video`.

**In the GUI:** Videos appear in the image list as expandable nodes. Use **Process → Extract Video Frames...** to control extraction settings, or **Process → Describe Video with AI...** to run the full pipeline.

**Extraction modes**

| Mode | CLI flag | Best for |
|---|---|---|
| Time interval | `--video-interval SECONDS` | Continuous footage (surveillance, timelapse) |
| Scene detection | `--scene THRESHOLD` | Events, films, talks (extracts on natural cuts) |

**Video GPS metadata:** If FFmpeg is installed, GPS coordinates recorded in the video file are copied into each extracted frame's EXIF data, enabling geocoding to work on video frames just as it does for photos. Install FFmpeg via **Tools → Install FFmpeg (for video GPS)...** in the GUI.

---

### Downloading Web Images

Use `idt download` or **File → Load Images From URL...** in the GUI to fetch images from a web page.

The tool:
1. Scrapes all `<img>` elements from the page.
2. Filters by minimum size if `--min-size` is specified.
3. Downloads images into a `.idtw` workspace (see [Workspaces (.idtw)](#workspaces-idtw)).
4. Records the original HTML `alt` attribute alongside each image.
5. Optionally describes and embeds in the same pass.

**Where images land:** Both the CLI and the GUI put downloads inside the workspace bundle, at `<workspace>.idtw/derived/downloads/<page title>-<timestamp>/`, never in a separate folder next to the workspace. In the CLI, `idt download <url> [directory]` resolves the workspace exactly like `idt describe --workspace` does: omit `[directory]` and it's named after the URL's domain under the workspace root (`~/Documents/idt` by default, see `idt config`); pass a name or path to target a specific workspace. Run `idt download <url> --describe` and check the printed `Location:` and `Workspace:` lines for the exact path. In the GUI, **File → Load Images From URL...** downloads into the current bundle's `derived/downloads/` folder (prompting you to save a workspace first if none is open yet).

**Common use case:** Generate accessibility-compliant alt text for images on an existing web page, then compare the AI-generated description with the existing alt text stored in the workspace.

---

### HEIC/HEIF Conversion

HEIC is the default format for photos taken on iPhones running iOS 11 and later. IDT handles HEIC transparently:

- In the CLI: HEIC files are converted to JPEG in memory before being sent to the AI. The conversion is cached in the workspace's `derived/converted/` folder.
- In the GUI: **Process → Convert HEIC Files...** converts a batch to JPEG. Originals are preserved.

HEIC support requires `pillow-heif` to be installed (`pip install pillow-heif`).

---

### Geocoding — Location from GPS

When `--geocode` is used (CLI) or **Enable Geocoding** is checked (GUI), IDT reverse-geocodes GPS coordinates from image EXIF data to human-readable place names using the OpenStreetMap Nominatim API.

The location string is prepended to the AI prompt context:

```
Context: Paris, France  Jun 10, 2024  Canon EOS R5
```

Geocoding results are cached in `~/.idt/geocode_cache.json` so each unique location is only looked up once.

**Privacy note:** GPS coordinates are sent to the Nominatim API (run by the OpenStreetMap Foundation) to resolve place names. If location privacy is a concern, use `--no-metadata` to disable all EXIF extraction.

---

### Embedding Descriptions into Images

After generating descriptions, you can write them directly into the image file metadata so the description travels with the file everywhere it goes—File Explorer, Finder, Lightroom, macOS Spotlight, iOS Photos, and any other app that reads EXIF or XMP metadata.

**CLI:** `idt embed <workspace>` or add `--embed` to the `describe` command to embed automatically after processing.

**GUI:** **File → Embed Descriptions into Images...**

Key points:
- Original files are **never modified** in copy mode (the default).
- Embedded copies are saved to `<workspace>/embedded/` and mirror the original subfolder structure.
- HEIC sources are converted to JPEG before embedding (HEIC is a read-only format for this purpose).
- In-place mode (modify originals) requires explicit confirmation and is not recommended unless you have backups.

#### Where the Description Is Stored

Different image formats have different metadata containers, so IDT writes to whichever fields that format actually supports:

| Format | Fields written |
|--------|----------------|
| JPEG | EXIF UserComment, XMP `dc:description` |
| PNG | tEXt `Description` chunk, XMP `dc:description` |
| WebP | EXIF UserComment |
| TIFF | ImageDescription tag, XPComment tag |

This matters for the next two sections: which field a format gets determines where the description shows up on your desktop. PNG files, for example, have no EXIF at all, so the Windows **Comments** column stays empty for them and you need the **Title** column instead.

#### Reading Embedded Descriptions on Windows

File Explorer can show the description as a column in Details view, which means you can read every description in a folder by arrowing down the list.

1. Open the folder holding the embedded copies (`<workspace>/embedded/`).
2. Switch to **Details** view (**Ctrl+Shift+6**, or the **View** menu).
3. Press **Tab** until focus reaches the column headers.
4. Press **Shift+F10** for the context menu of available columns.
5. Turn on **Comments** (JPEG, WebP and TIFF) or **Title** (JPEG, PNG and TIFF).

If the column you want is not on the short list, choose **More...** at the bottom of that menu and find it in the full list.

Once the column is on, arrow through the file list and the description is announced along with the file name. To read a single file's description instead, select it and press **Alt+Enter** for **Properties**, then move to the **Details** tab—the description appears under **Description → Title** and **Comments**.

You can also search on the embedded text: type it into the Explorer search box and Windows matches against these fields, so `sunset` finds every photo whose description mentions one.

**Choosing a column:**

| Your files are | Turn on |
|----------------|---------|
| JPEG (the usual case) | **Comments** or **Title**—both are filled |
| PNG | **Title** (PNG has no EXIF, so **Comments** stays blank) |
| WebP | **Comments** |
| TIFF | **Comments** or **Title** |

#### Reading Embedded Descriptions on macOS

macOS has no Finder column for embedded descriptions—the **Comments** column in Finder's list view shows *Spotlight Comments*, which is a note stored separately by Finder, not the description inside the file. Turning it on will show nothing. Use one of these instead:

- **Finder Get Info** — select the file and press **Cmd+I**. The description appears in the **More Info** section. This is the quickest way to check a single file, and VoiceOver reads the field directly.
- **Preview** — open the image, then **Tools → Show Inspector** (**Cmd+I**). The **ⓘ** tab has **General**, **Exif** and **TIFF** panes showing the raw fields.
- **Spotlight search** — the description is indexed, so searching for a word from it finds the photo.
- **Terminal** — `mdls -name kMDItemDescription photo.jpg` prints the description for one file. To list a whole folder:

  ```bash
  for f in *.jpg; do echo "$f: $(mdls -raw -name kMDItemDescription "$f")"; done
  ```

- **Photos** — importing an embedded copy brings the description in as the photo's caption, where it is visible in the Info pane and searchable.

Unlike Windows, macOS needs no per-format advice here: Get Info and Preview read through ImageIO, which reports the description for JPEG, PNG, WebP and TIFF alike.

---

### Combining Multiple Workspaces

If you have descriptions spread across many workspace bundles—for example, one per event or per year—use `idt combine` to merge them into a single CSV for analysis, reporting, or import into another tool.

```bash
# Combine all workspaces under ~/Pictures into one CSV sorted by photo date
idt combine ~/Pictures --output all-photos.csv --sort date
```

The CSV includes all description fields: filename, source path, description text, provider, model, timestamp, metadata context, and token counts.

---

### Piping and Scripting with idt

`idt describe` accepts image file paths from stdin when you pass `-` as the source:

```bash
# Describe images listed by another script
get_images.sh | idt describe - --provider anthropic --quiet
```

In `--quiet` mode, stdin mode outputs `filename\tdescription` (tab-separated), making it easy to pipe into `awk`, `cut`, or a database import script.

```bash
# Extract only descriptions into a text file
idt show ~/Photos --json | python -c "
import sys, json
for line in sys.stdin:
    obj = json.loads(line)
    if obj.get('described'):
        print(obj['description'])
" > descriptions.txt
```

---

## Part 7: IDT Chat

IDT Chat is a standalone chat client for Ollama, Claude and OpenAI. It is not an image tool — attachments are supported, but the point is the conversation.

It exists because mainstream chat applications are poorly suited to screen reader use. The conversation is a list you arrow through, responses are announced once and completely rather than a token at a time, and every action has a keyboard shortcut.

### Starting a conversation

Launch **IDT Chat** from the Start menu (Windows) or from `Applications/IDT/IDTChat.app` (macOS).

The first time you send a message it asks for a provider and model. Ollama needs no API key, so it works with no setup as long as Ollama is running. Claude and OpenAI need a key — see [Setting Up API Keys](#setting-up-api-keys).

**MLX is not offered here, and that is deliberate.** ImageDescriber lists MLX on Apple Silicon and IDT Chat does not, which looks like an oversight and is not. MLX needs Apple's `mlx` and `mlx-vlm` libraries, which would take this app from about 40 MB to around 350 MB — worth paying in ImageDescriber, where describing a folder of photos locally is the whole point, and worth much less for chat, because Ollama now runs several models through MLX on Apple Silicon itself. Chatting with Ollama on a Mac already gets you the Metal acceleration. If you specifically want to chat with an MLX model, use the chat window inside ImageDescriber (**Process → Chat with AI Model**), which offers it. The picker hides MLX rather than listing an option that would fail the moment you chose it.

### The window

- **Conversations** (left) — every saved conversation. `Enter` opens one.
- **Conversation history** — the current exchange, one line per turn, each naming who spoke. Arrow keys move through it.
- **Selected message** — the full text of the highlighted turn. It is editable so you can select and copy from it; edits are not saved.
- **Your message** — `Enter` sends, `Shift+Enter` starts a new line.
- **Attachments** — files queued for the next message. The label states the count, so you can check it without moving focus.

### Attaching files

Use **Chat → Attach Files** (`Ctrl+Shift+A`), or paste an image straight from the clipboard with `Ctrl+Shift+V`. Select an attachment and press `Delete` to remove it.

Attachments are sent with your next message and then cleared — the model has seen them, so later turns do not re-upload them.

What each provider accepts:

| Provider | Accepts | Size limit |
|---|---|---|
| Ollama | JPEG, PNG, GIF, WebP | None published |
| OpenAI | JPEG, PNG, GIF, WebP | None published |
| Claude | JPEG, PNG, GIF, WebP, **PDF** | 5 MB per image, 32 MB per PDF |

**HEIC and HEIF photos from an iPhone are converted to JPEG automatically** — no provider reads HEIC directly.

If you select several files and one cannot be sent, the rest are still attached and a dialog explains which failed and why. The **Attach Files** command is unavailable for providers that take no attachments; switching to such a provider clears anything queued and says so, rather than silently dropping it later.

### How responses are announced

Streaming text is *not* read aloud as it arrives — that would flood a screen reader. Text accumulates silently, then is announced once when complete. Choose how much is said under **View**:

| Setting | What is announced |
|---|---|
| Announce the full response | The whole reply |
| Announce a summary | The first sentence and the word count |
| Announce nothing | Nothing; the status bar still updates |

Use **View → Read Last Response** (`Ctrl+Shift+R`) to hear a reply again at any time.

### Keyboard shortcuts

On macOS every `Ctrl` below is `Cmd`. The complete list for both applications,
including the Windows `Alt` keys, is in
[KEYBOARD_SHORTCUTS.md](KEYBOARD_SHORTCUTS.md); **Help → Keyboard Shortcuts**
(`F1`, or `Cmd+?` on a Mac) shows it in the app, named for the platform you
are on.

| Key | Action |
|---|---|
| `Enter` | Send message |
| `Shift+Enter` | New line in the message box |
| `Ctrl+Return` | Send from anywhere in the window |
| `Ctrl+N` | New chat |
| `Ctrl+Shift+M` | Change provider or model |
| `Ctrl+Shift+A` | Attach files |
| `Ctrl+Shift+V` | Paste an image from the clipboard |
| `Delete` | In the conversation list: delete that conversation (with confirmation). In the attachments list: remove that attachment |
| `Enter` | In the conversation list: open it. In the transcript: read the message again |
| `Ctrl+Shift+P` | Set the system prompt |
| `Ctrl+Shift+K` | Turn web search on or off (Ollama models with tool support) |
| `Ctrl+R` | Regenerate the last response |
| `Ctrl+.` | Stop the response in progress (and stop it being read aloud) |
| `Ctrl+Shift+R` | Read the last response again |
| `Ctrl+C` | Copy — the selection in a text box, or the selected message when the transcript has focus |
| `Ctrl+Shift+C` | Copy the whole conversation |
| `Ctrl+Shift+E` | Export the conversation |
| `Ctrl+T` | Token usage |
| `F1` | Shortcut list |

`Ctrl+Shift+M` rather than `Ctrl+M`, and `Ctrl+Shift+E` rather than `Ctrl+E`,
because wx maps every `Ctrl` accelerator to `Cmd` on macOS: `Cmd+M` minimises
the window and `Cmd+E` is "use selection for find". `Ctrl+C` is a normal Copy
so you can copy a selection out of the message box.

On Windows, `Alt` reaches the menus and the controls: `Alt+F` `Alt+E` `Alt+C`
`Alt+V` `Alt+H` for the five menus, and `Alt+O` conversations, `Alt+I`
transcript, `Alt+M` selected message, `Alt+Y` your message, `Alt+N`
attachments, `Alt+S` Send, `Alt+T` Stop, `Alt+A` Attach, `Alt+R` Remove.

### System prompts

**Chat → Set System Prompt** (`Ctrl+Shift+P`) sets standing instructions for the conversation — a persona, a required tone, a format to answer in. It is saved with the conversation and applies to every turn.

### Switching models mid-conversation

**Chat → Change Model** (`Ctrl+Shift+M`) switches provider or model without losing history. The new model receives everything said so far, and each turn records which model produced it, so the history shows who said what.

### Stopping a response

`Ctrl+.` or the **Stop** button ends a reply in progress. **The partial response is kept**, not discarded — you watched it arrive, so it stays in the transcript.

### Token usage

`Ctrl+T` shows two numbers, which are genuinely different:

- **Context window in use** — the most recent exchange, which is what occupies the model's context.
- **Billed this conversation** — the sum across every turn, which is what you pay for.

When a conversation outgrows the model's context window, the oldest turns are dropped and the app says so rather than doing it silently.

### Where conversations are stored

Conversations are saved automatically — there is no Save command — one JSON file per conversation:

| Platform | Location |
|---|---|
| Windows | `C:\Users\<you>\.idt\chats\` |
| macOS / Linux | `~/.idt/chats/` |

A conversation is written after **every turn**, so nothing is lost if the app closes unexpectedly. Files are named by conversation id, for example `chat_a1b2c3d4e5f6.json`.

They stay there until you delete them. **File → Delete Chat**, or selecting a conversation and pressing `Delete`, removes the file permanently after asking you to confirm. Nothing else prunes them: there is no age limit and no size cap.

The format is the same one ImageDescriber uses for chat items inside a `.idtw` bundle, so a conversation can be copied between them. Because they are plain JSON, you can also back them up, read them, or delete them with any file manager.

**Attachments are referenced, not copied.** A conversation records the path to a file you attached, not its contents. Moving or deleting the original means it cannot be re-sent, though the text of the conversation is unaffected.

### Chatting from the terminal

The same engine backs `idt chat`:

```bash
idt chat
```

```bash
idt chat --provider claude --system "Answer in one sentence." --message "What is HEIC?"
```

`idt chat --list` shows saved conversations and `idt chat --resume <id>` continues one. Responses stream to the terminal; `Ctrl+C` stops a reply and keeps what arrived.

---

## Part 8: Accessibility

### Screen Reader Compatibility

**ImageDescriber GUI**

| Screen reader | Platform | Support level |
|---|---|---|
| NVDA | Windows | Full (TreeCtrl with MSAA) |
| JAWS | Windows | Full (TreeCtrl with UIA) |
| VoiceOver | macOS | Full (custom NSOutlineView adapter) |
| Narrator | Windows | Tested and working |

The chat window and description list use `wx.ListBox` instead of tree controls, providing a single tab stop and reliable screen reader announcement of new content.

All interactive controls have accessible names set via `SetAccessibleName()`. Separator rows in lists are automatically skipped during keyboard navigation.

**idt CLI**

The CLI uses no ANSI color codes in interactive mode (`idt guideme`) and all output is plain text. Progress messages are written to stdout as plain lines. The `--quiet` flag reduces output to the minimum needed for piping.

---

### Keyboard Navigation

**All features in the GUI are reachable by keyboard.** No action requires a mouse.

**Image list:** Arrow keys to navigate, Enter to expand/collapse folders, Space to toggle checkboxes.

**Tab order:** Image list → Description list → Description text editor. Shift+Tab moves backward.

**Menu bar:** Alt (Windows) or Ctrl+F2 (macOS) activates the menu bar. All menu items have keyboard equivalents shown in the menu.

---

### Accessible Output

**HTML reports** generated by `idt export --format html` and **File → Export HTML Gallery** include:

- Skip navigation link at the top of the page
- Proper HTML5 landmark regions (`<main>`, `<nav>`, `<header>`, `<footer>`)
- Correct heading hierarchy (single H1 per page)
- All images have `alt` attributes set to the AI-generated description
- Tables use `<caption>` and `<th scope>` attributes
- No color-only information
- Works without JavaScript
- Passes WCAG 2.2 Level AA

---

## Part 9: Troubleshooting

### Common Issues

**No models showing in the GUI**

- Ollama: Open a terminal and run `ollama list`. If nothing appears, open `http://localhost:11434` in a browser. If that fails, restart Ollama or reinstall it.
- OpenAI / Claude: Check that the API key environment variable is set. Open **Tools → AI Info → Ollama Models...** to test connectivity.

**Processing completes but descriptions are blank or very short**

- Some models (especially small Ollama models on CPU) time out if the image is very large. Try resizing images to under 2048 × 2048 pixels before describing.
- Switch to a higher-quality model: `claude-opus-4-6` or `gpt-4o`.

**Video extraction fails**

- Check that `opencv-python` is installed: `pip install opencv-python`.
- For GPS from video: install FFmpeg via **Tools → Install FFmpeg (for video GPS)...** or from [ffmpeg.org](https://ffmpeg.org).

**HEIC images not recognized**

- Running from source: install `pillow-heif` (`pip install pillow-heif`).
- Using a packaged build: `pillow-heif` is already included, so a HEIC that isn't
  recognized is a bug worth reporting rather than a missing dependency.

**The GUI silently does nothing when I click a button**

- Run the application from the terminal to see error output:
  ```bat
  cd imagedescriber
  .winenv\Scripts\python imagedescriber_wx.py
  ```
  Reproduce the action. Any exception will appear in the terminal immediately.

**"Permission denied" errors on macOS**

- If you downloaded the app, macOS Gatekeeper may quarantine it. Open **System Settings → Privacy & Security** and allow the app to run, or right-click and choose **Open** the first time.

---

### Diagnostic Steps

1. Check the version: `idt version` — confirm you are running the expected version.
2. Check the log: look in `<workspace>/logs/*.log` for the last processing run.
3. Test with a single image and `--show-descriptions` to see the raw AI output:
   ```bash
   idt describe ~/Photos --limit 1 --show-descriptions
   ```
4. Test connectivity: `idt models` to verify providers respond.
5. Test config: `idt config` to see current defaults.

---

## Appendix A: Supported File Formats

### Image Formats

| Format | Extension(s) | Notes |
|---|---|---|
| JPEG | `.jpg`, `.jpeg` | Native; best supported |
| PNG | `.png` | Native |
| WebP | `.webp` | Native |
| GIF | `.gif` | Static frame only |
| TIFF | `.tiff`, `.tif` | Converted to JPEG before API |
| BMP | `.bmp` | Converted to JPEG before API |
| HEIC / HEIF | `.heic`, `.heif` | Requires `pillow-heif`; converted in memory |

### Video Formats

| Format | Extension(s) |
|---|---|
| MPEG-4 | `.mp4`, `.m4v` |
| QuickTime | `.mov` |
| AVI | `.avi` |
| Matroska | `.mkv` |
| Windows Media | `.wmv` |
| MPEG Transport Stream | `.mts`, `.m2ts` |

---

## Appendix B: Configuration File Reference

**Location:** `~/.idt/config.json`

```json
{
  "default_provider": "ollama",
  "default_model": "minicpm-v4.6",
  "default_prompt_name": "detailed",
  "workspace_root": "/home/yourname/Documents/idt",
  "custom_prompts": {
    "my_prompt": "Describe this image for a museum label. 50–75 words.",
    "product_shot": "E-commerce product description: visible features, materials, condition."
  }
}
```

| Key | Default | Description |
|---|---|---|
| `default_provider` | `ollama` | AI provider used when none is specified |
| `default_model` | Provider default | Model used when none is specified |
| `default_prompt_name` | `detailed` | Prompt style used by default |
| `workspace_root` | `~/Documents/idt` | Root folder where new workspaces are created |
| `custom_prompts` | `{}` | Dictionary of name → prompt text for user-defined styles |

---

## Appendix C: Workspace File Structure

```
MyTrip.idtw/                        Workspace bundle (a folder ending in .idtw)
  manifest.json                     Job metadata
  images/                           Copies of source images
  descriptions/                     JSON description sidecars
    vacation-photo-001.jpg.json
    vacation-photo-002.jpg.json
  derived/
    converted/                      HEIC → JPEG conversions
    frames/                         Extracted video frames
  logs/                             Processing logs (one per run)
  embedded/                         Images with embedded metadata
  reports/
    descriptions.html
    descriptions.csv
    descriptions.txt
```

**`manifest.json` key fields**

```json
{
  "format": "idtw",
  "version": "1.0",
  "name": "MyTrip",
  "created": "2024-09-12T10:00:00+00:00",
  "modified": "2024-09-12T11:30:00+00:00",
  "sources": [{"path": "/Users/you/Photos/Trip", "added": "2024-09-12T10:00:00+00:00"}],
  "defaults": {
    "provider": "anthropic",
    "model": "claude-opus-4-6",
    "prompt_name": "detailed"
  },
  "geocode_enabled": true,
  "cli_commands": [
    {"command": "idt describe /Users/you/Photos/Trip --provider anthropic", "timestamp": "..."}
  ]
}
```

**Description sidecar format** (`descriptions/photo.jpg.json`)

```json
{
  "image": "photo.jpg",
  "source_path": "/Users/you/Photos/Trip/photo.jpg",
  "descriptions": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "text": "A group of hikers resting on a mountain ridge...",
      "provider": "anthropic",
      "model": "claude-opus-4-6",
      "prompt_name": "detailed",
      "created": "2024-09-12T10:15:32+00:00",
      "input_tokens": 512,
      "output_tokens": 183,
      "metadata_context": "Zugspitze, Germany  Sep 12, 2024  iPhone 14 Pro"
    }
  ],
  "active_description_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

## Appendix D: Keyboard Shortcut Reference

The shortcuts you are most likely to reach for. For the complete set —
every menu item in both apps, every Alt mnemonic on Windows, and the
chords the operating systems have already claimed — see
[KEYBOARD_SHORTCUTS.md](KEYBOARD_SHORTCUTS.md), which is checked against
the source by the test suite.

### Global Shortcuts

| Action | Windows / Linux | macOS |
|---|---|---|
| New Workspace | Ctrl+N | Cmd+N |
| Open Workspace | Ctrl+O | Cmd+O |
| Save Workspace | Ctrl+S | Cmd+S |
| Load Directory | Ctrl+L | Cmd+L |
| Refresh Folder from Disk | Ctrl+Shift+R | Cmd+Shift+R |
| Load from URL | Ctrl+U | Cmd+U |
| Export HTML Gallery | Ctrl+Shift+H | Cmd+Shift+H |
| Workspace Statistics | Ctrl+I | Cmd+I |
| Exit / Quit | Ctrl+Q | Cmd+Q |

### Edit

| Action | Windows / Linux | macOS |
|---|---|---|
| Cut | Ctrl+X | Cmd+X |
| Copy | Ctrl+C | Cmd+C |
| Paste | Ctrl+V | Cmd+V |
| Select All | Ctrl+A | Cmd+A |

### View and Navigation

| Action | Shortcut |
|---|---|
| Update Image List | F5 |
| Filter: All Items | Ctrl+Shift+A |
| Filter: Described Only | Ctrl+Shift+D |
| Filter: Undescribed Only | Ctrl+Shift+U |
| Find Images (search bar) | Ctrl+F |
| Edit Prompts | Ctrl+Shift+P |
| Configure Settings | Ctrl+Shift+C |

### Image List Navigation

| Action | Key |
|---|---|
| Move up/down | Arrow keys |
| Expand folder | Right arrow |
| Collapse folder | Left arrow |
| Select item | Enter |
| Toggle checkbox | Space |

---

*Image Description Toolkit is an open-source project. Contributions, bug reports, and feedback are welcome at the [project repository](https://github.com/kellylford/Image-Description-Toolkit).*
