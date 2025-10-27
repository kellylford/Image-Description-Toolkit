# Image Description Toolkit (IDT) - User Guide

## Overview
The Image Description Toolkit (IDT) is a comprehensive, AI-driven suite for generating natural language descriptions from images and videos. It provides **multiple applications** to fit different workflows:

- **📋 Command Line Interface (CLI)** - Powerful batch processing with `idt.exe`
- **🖼️ GUI ImageDescriber** - Interactive, user-friendly desktop application
- **📝 Prompt Editor** - Visual prompt design and testing tool
- **📊 Results Viewer** - Real-time monitoring and results browsing

IDT supports both local (Ollama) and cloud (OpenAI, Claude) AI providers, and is distributed as standalone Windows executables—**no Python installation required**.

---

## Table of Contents
1. [Installation & Setup](#1-installation--setup)
2. [IDT Applications Overview](#2-idt-applications-overview)
3. [GUI ImageDescriber Application](#3-gui-imagedescriber-application)
4. [Prompt Editor Application](#4-prompt-editor-application)
5. [Getting Started: CLI Golden Path](#5-getting-started-cli-golden-path)
6. [Understanding Workflow Runs & Naming](#6-understanding-workflow-runs--naming)
7. [Prompt Customization](#7-prompt-customization)
8. [Advanced CLI Usage & Commands](#8-advanced-cli-usage--commands)
9. [Metadata Extraction & Geocoding](#9-metadata-extraction--geocoding) ⭐ NEW
10. [Analysis Tools](#10-analysis-tools)
11. [Results Viewer (Real-Time Monitoring)](#11-results-viewer-real-time-monitoring)
12. [Cloud Provider Setup](#12-cloud-provider-setup)
13. [Performance Tips](#13-performance-tips)
14. [Batch Files Reference](#14-batch-files-reference)
15. [Troubleshooting](#15-troubleshooting)

---

## 1. Installation & Setup

### Step 1: Download & Extract
1. Download the latest `ImageDescriptionToolkit_v[VERSION].zip` from GitHub Releases
2. Extract to a folder of your choice (e.g., `C:\IDT\`)
3. You'll find four main applications:
   - `idt.exe` - Command line interface for batch processing
   - `imagedescriber.exe` - GUI application for individual images
   - `prompt_editor.exe` - Visual prompt design and testing tool
   - `viewer.exe` - Results browser and monitoring application

### Step 2: Install Ollama (for local models)
**Ollama is recommended for most users** - it's free, private, and runs locally.

1. Download Ollama from [https://ollama.ai/download/windows](https://ollama.ai/download/windows)
   - **Or** install via winget: `winget install Ollama.Ollama`
2. After installation, Ollama runs as a background service automatically
3. Verify it's running: Open terminal and type `ollama list`

### Step 3: Download Your First Model
The **Moondream** model is recommended for beginners - it's fast, accurate, and only 1.7GB:

```bash
ollama pull moondream
```

**Other popular models:**
```bash
ollama pull llava:7b        # Good balance of speed/quality
ollama pull llava:13b       # Higher quality, slower
ollama pull llama3.2-vision # Latest Llama vision model (11GB)
```

To see all installed models:
```bash
ollama list
```

---

## 2. IDT Applications Overview

IDT provides four main applications, each designed for different use cases:

### 📋 Command Line Interface (CLI) - `idt.exe`
**Best for:** Batch processing, automation, advanced workflows, integration with scripts

**Key Features:**
- Process hundreds or thousands of images at once
- Powerful workflow automation with resume capability
- Advanced analysis and export tools
- Integration with batch scripts and automation
- Full control over all processing parameters

**When to use:** Large image collections, repeated workflows, production environments

### 🖼️ GUI ImageDescriber - `imagedescriber.exe`
**Best for:** Individual images, quick testing, visual workflow, beginners

**Key Features:**
- Workspace-based project management
- Paste images from clipboard (Ctrl+V)
- Visual model and prompt selection
- Interactive provider setup (Ollama/OpenAI/Claude)
- Immediate feedback and results
- Perfect for learning and experimentation

**When to use:** Single images, testing prompts/models, visual learners, quick tasks

### 📝 Prompt Editor - `prompt_editor.exe`
**Best for:** Managing prompts and configuration settings

**Key Features:**
- Edit and manage prompt styles in config file
- Add, delete, and duplicate custom prompts
- Configure default AI provider and model
- Manage API keys for cloud services
- Character count for prompt optimization

**When to use:** Setting up prompts, configuring providers, managing config files

### 📊 Results Viewer - `viewer.exe`
**Best for:** Browsing results, real-time monitoring, sharing outputs

**Key Features:**
- Browse all workflow results in one place
- Real-time monitoring of active workflows
- Search and filter descriptions
- Copy descriptions to clipboard
- View image metadata and processing details

**When to use:** Reviewing results, monitoring progress, sharing with others

---

## 3. GUI ImageDescriber Application

The **GUI ImageDescriber** (`imagedescriber.exe`) provides an intuitive, visual interface for describing individual images or small batches.

### Quick Start

1. **Launch:** Double-click `imagedescriber.exe` or run from command line
2. **Setup Provider:** Choose Ollama (local) or cloud provider (OpenAI/Claude)
3. **Load Image:** Paste from clipboard (Ctrl+V) or use "Browse" button
4. **Select Model & Prompt:** Choose from available options
5. **Generate:** Click "Describe Image" and see results instantly!

### Main Interface

**Image Panel:**
- Paste images from clipboard (Ctrl+V)
- Image preview with automatic scaling
- Support for all major formats (JPG, PNG, HEIC, etc.)
- File information display (size, dimensions, format)

**Provider Setup:**
- **Ollama Tab:** Automatic model detection, install new models
- **OpenAI Tab:** API key setup, model selection (GPT-4o, GPT-4o-mini)
- **Claude Tab:** API key setup, model selection (Opus, Sonnet, Haiku)
- Real-time connection testing and validation

**Prompt & Model Selection:**
- Visual prompt style picker with descriptions
- Model dropdown with performance/quality indicators
- Custom prompt text editing
- Prompt preview and validation

**Results Panel:**
- Description generation progress tracking
- Copy to clipboard functionality
- Save descriptions to file
- Processing time and model information

### Advanced Features

**Batch Processing:**
- Process multiple images in sequence
- Maintain settings across images
- Progress tracking for large batches
- Resume interrupted processing

**Settings & Preferences:**
- Remember last used provider and model
- Custom output directories
- Image processing options (resize, quality)
- Auto-save preferences

**Integration:**
- Export results compatible with CLI workflows
- Import custom prompts from Prompt Editor
- Launch Results Viewer for detailed browsing

### Use Cases

**Perfect for:**
- ✅ Testing new models or prompts on sample images
- ✅ Quick one-off image descriptions
- ✅ Learning how different providers/models work
- ✅ Visual users who prefer GUI interfaces
- ✅ Demonstrating capabilities to others
- ✅ Processing family photos or small collections

**Limitations:**
- Not optimized for hundreds/thousands of images
- Fewer automation features than CLI
- Limited to sequential processing

---

## 4. Prompt Editor Application

The **Prompt Editor** (`prompt_editor.exe`) is a configuration tool for managing prompt styles and AI provider settings in the `image_describer_config.json` file.

### Quick Start

1. **Launch:** Double-click `prompt_editor.exe`
2. **Select Prompt:** Choose a prompt style from the list
3. **Edit Prompt:** Modify the prompt text with character count display
4. **Configure Provider:** Set default AI provider and model
5. **Save:** Save changes to the configuration file

### Main Interface

**Prompt List (Left Panel):**
- View all available prompt styles
- Select a prompt to edit
- Add new prompt styles
- Delete or duplicate existing prompts
- Built-in prompts: narrative, detailed, concise, artistic, technical, colorful, simple

**Prompt Editor (Right Panel):**
- Edit prompt name
- Edit prompt text with real-time character count
- See validation feedback

**Default Settings:**
- Set default prompt style for CLI/GUI use
- Choose default AI provider (Ollama, OpenAI, Claude)
- Configure API keys for cloud providers
- Set default model (auto-discovered from selected provider)
- Refresh model list from provider

### Features

**Prompt Management:**
- Add new custom prompt styles
- Edit existing prompt text
- Duplicate prompts as starting points
- Delete unwanted prompts
- Character count for prompt optimization

**Provider Configuration:**
- Select default AI provider
- Auto-discover available models from Ollama
- Manual model entry for cloud providers
- Secure API key storage (password-masked input)
- Toggle API key visibility

**File Operations:**
- Save changes to current config file
- Save As to create new config files
- Open different config files
- Backup and restore functionality
- Auto-detects config file location

### Prompt Design Best Practices

**Structure Your Prompts:**
```
1. Context setting: "Analyze this image..."
2. Specific instructions: "Focus on colors, composition..."
3. Output format: "Provide a detailed paragraph..."
4. Constraints: "Avoid interpretation, stick to visible elements..."
```

**Use Effective Techniques:**
- Be specific about what to include/exclude
- Use action words ("describe", "analyze", "identify")
- Set the desired tone (formal, casual, technical)
- Specify output length or structure

**Test Iteratively:**
- Start with simple prompts and refine
- Test with diverse image types
- Compare results across different models
- Gather feedback from end users

### Use Cases

**Perfect for:**
- ✅ Creating and managing custom prompt styles
- ✅ Editing the default prompt for your workflow
- ✅ Organizing multiple prompt variations for different image types
- ✅ Configuring AI provider defaults (Ollama/OpenAI/Claude)
- ✅ Managing API keys for cloud providers
- ✅ Setting up the configuration before using CLI or GUI tools

**Note:** The Prompt Editor does NOT test prompts or generate descriptions. Use the GUI ImageDescriber application to test how prompts work with actual images.

---

## 5. Getting Started: CLI Golden Path

### Option 1: Interactive Guided Setup (Recommended for Beginners)

**The easiest way to get started!** The `guideme` command walks you through every step:

```bash
idt guideme

# Advanced: Pass workflow options for special cases
idt guideme --timeout 180              # For large/slow models (any value in seconds)
idt guideme --preserve-descriptions    # Skip already-described images
```

This wizard will:
1. ✅ Help you select a provider (Ollama/OpenAI/Claude)
2. ✅ Check for installed models or help set up API keys
3. ✅ Validate your image directory
4. ✅ Let you name your workflow run
5. ✅ Choose a prompt style
6. ✅ Show you the command before running
7. ✅ Run the workflow or save the command for later
8. ✅ **Automatically launch the viewer to watch progress in real-time!**

**Perfect for:**
- First-time users
- Testing different models
- Learning the command options
- Setting up cloud providers
- Watching your workflow progress live as images are processed

**💡 Pro Tip:** If you're using large vision models (like Qwen) that take longer to process each image, add `--timeout <seconds>` with an appropriate value (e.g., 180, 300, or higher) to avoid timeouts.

### Option 2: Direct Command (Quick & Simple)

Once you're familiar with the tool:

1. Put some images in a directory (e.g., `C:\Photos\`)
2. Open a terminal in the IDT folder
3. Run:
   ```bash
   idt workflow C:\Photos
   ```

That's it! Results appear in `Descriptions/workflow_[timestamp]/`

**After completion**, you'll be prompted:
```
Would you like to view the results in the viewer? (y/n):
```
Type `y` to automatically open the viewer and browse your results!

---

## 6. Understanding Workflow Runs & Naming

### What is a Workflow Run?

Each time you process images, IDT creates a **workflow run** - a complete package containing:
- Original or processed images
- Generated descriptions (`image_descriptions.txt`)
- HTML report (`index.html`)
- Statistics and metadata
- Log files

### Workflow Run Names

By default, workflow runs are named with timestamps:
```
Descriptions/workflow_2025-10-11_143022/
```

**You can provide a custom name** to make runs easier to identify:

```bash
idt workflow C:\Photos --name "family_vacation_2025"
```

This creates:
```
Descriptions/workflow_family_vacation_2025/
```

**Benefits of custom naming:**
- ✅ Easier to find specific runs
- ✅ Organize by project, date, or category
- ✅ Better for comparing multiple runs
- ✅ More meaningful in analysis reports

**Naming tips:**
- Use descriptive names: `summer_trip_photos`, `product_catalog_jan`
- Avoid spaces (use underscores or hyphens)
- Include dates or versions if needed: `headshots_v2`, `2025_Q1_marketing`

### Multiple Runs

You can have many workflow runs in the `Descriptions/` folder:
```
Descriptions/
├── workflow_family_vacation/
├── workflow_product_photos/
├── workflow_2025-10-11_143022/
└── workflow_test_run/
```

Each run is completely self-contained and independent.

---

## 7. Prompt Customization

**Prompt styles control HOW your images are described** - often more important than model selection!

### Default Style: Narrative

By default, IDT uses the `narrative` style:
> *"Provide a narrative description including objects, colors and detail. Avoid interpretation, just describe."*

### Changing Prompt Styles

Add `--prompt-style STYLE_NAME` to any command:

```bash
idt workflow C:\Photos --prompt-style artistic
idt guideme  # (wizard will let you choose)
```

### Available Prompt Styles

**Want to see all available prompts?** Use the `prompt-list` command:

```bash
# See prompt style names
idt prompt-list

# See names AND full prompt text
idt prompt-list --verbose
```

| Style Name | Best For | Description |
|------------|----------|-------------|
| **narrative** | General use (default) | Detailed, objective descriptions without interpretation |
| **detailed** | Metadata, cataloging | Comprehensive descriptions including all visual elements |
| **concise** | Quick summaries | Brief, essential descriptions |
| **artistic** | Art analysis | Focus on composition, color palette, style, emotional tone |
| **technical** | Photography | Camera settings, lighting quality, technical analysis |
| **colorful** | Color-focused | Emphasis on colors, lighting, visual atmosphere |
| **Simple** | Minimal | Just basic description |

### Custom Prompt Styles

You can add your own styles by editing `scripts/image_describer_config.json`:

```json
{
  "prompt_variations": {
    "your_style_name": "Your custom prompt text here..."
  }
}
```

---

## 8. Advanced CLI Usage & Commands

> **📖 Complete Reference:** For comprehensive documentation of all CLI commands with detailed options and examples, see [CLI_REFERENCE.md](CLI_REFERENCE.md).

### IDT Command Reference

#### Main Commands

```bash
# Interactive wizard (recommended for beginners)
idt guideme

# Run workflow
idt workflow <image_directory> [options]

# Launch results viewer (GUI)
idt viewer [directory]

# List available prompt styles
idt prompt-list [--verbose]

# Analyze workflow statistics
idt stats [workflow_directory]

# Review description quality
idt contentreview [workflow_directory]

# Combine multiple runs into CSV
idt combinedescriptions [options]

# Check installed Ollama models
idt check-models

# Extract frames from videos
idt extract-frames <video_file> [options]

# Convert HEIC images to JPG
idt convert-images <directory>

# Show version
idt version

# Show help
idt help
```

#### Workflow Command Options

```bash
idt workflow <directory> [options]

Options:
  --provider PROVIDER       AI provider: ollama, openai, claude (default: ollama)
  --model MODEL            Model name (default: moondream for ollama)
  --name NAME              Custom workflow run name
  --prompt-style STYLE     Prompt style (default: narrative)
  --api-key-file FILE      Path to API key file (for cloud providers)
  --output-dir DIR         Output directory (default: Descriptions)
  --steps STEPS            Comma-separated steps: video,convert,describe,html
  --timeout SECONDS        Ollama request timeout in seconds (default: 90)
  --recursive              Process subdirectories
  --max-files N            Limit number of files (for testing)
  --resume                 Resume interrupted workflow
  --batch                  Non-interactive mode (skip prompts - for sequential runs)
  --view-results           Auto-launch viewer to monitor progress
```

**Examples:**

```bash
# Basic usage with custom name
idt workflow C:\Photos --name summer_photos

# Use specific model and prompt style
idt workflow C:\Photos --model llava:13b --prompt-style artistic

# Cloud provider with custom name
idt workflow C:\Photos --provider openai --model gpt-4o --name portfolio_review

# Increase timeout for slower hardware or large models
idt workflow C:\Photos --timeout 120

# Only describe, skip HTML generation
idt workflow C:\Photos --steps describe --name quick_test

# Process subdirectories recursively
idt workflow C:\Photos --recursive --name all_photos

# Resume an interrupted run
idt workflow C:\Photos --resume

# Non-interactive mode (for running multiple workflows sequentially)
idt workflow C:\Photos --batch --name batch1
idt workflow C:\More_Photos --batch --name batch2

# Launch viewer automatically to watch progress
idt workflow C:\Photos --view-results --name live_monitoring
```

---

## 9. Metadata Extraction & Geocoding ⭐ NEW

IDT can automatically extract and include rich metadata from your images, adding context about **where and when** photos were taken.

### What is Metadata?

Metadata extraction pulls information from your image files including:
- **📅 Photo Date & Time** - When the photo was actually taken
- **📍 GPS Coordinates** - Where the photo was taken (latitude/longitude)
- **📷 Camera Information** - Device make/model, lens details
- **⚙️ Photo Settings** - ISO, aperture, shutter speed, focal length
- **🗺️ Location Names** - City, state, country (via geocoding)

### Description Format with Metadata

When metadata is enabled, descriptions include a **location/date prefix**:

```
Austin, TX Mar 25, 2025: A beautiful sunset over the lake with vibrant orange and pink hues reflecting on the calm water.

[3/25/2025 7:35P, iPhone 14, 30.2672°N, 97.7431°W]
```

**Format breakdown:**
- **Prefix:** `"Austin, TX Mar 25, 2025:"` - Human-readable location and date
- **Description:** The AI-generated image description
- **Metadata suffix:** Technical details in brackets

### Using Metadata in Workflows

**Basic metadata (enabled by default):**
```bash
idt workflow C:\Photos
# Includes dates, GPS coordinates, camera info
```

**Disable metadata:**
```bash
idt workflow C:\Photos --no-metadata
# No metadata extraction or prefix
```

**Enable geocoding (convert GPS to city/state):**
```bash
idt workflow C:\Photos --geocode
# Adds "Austin, TX" instead of just coordinates
```

**Custom geocoding cache:**
```bash
idt workflow C:\Photos --geocode --geocode-cache my_cache.json
# Stores geocoded locations for faster subsequent runs
```

### Interactive Wizard with Metadata

The `idt guideme` wizard includes metadata configuration:

```bash
idt guideme
```

You'll be prompted:
1. **Enable metadata extraction?** [Y/n] - Extracts photo data
2. **Enable geocoding?** [y/N] - Converts GPS to city/state (requires internet)
3. **Geocoding cache location?** - Where to save geocoded results

### How Geocoding Works

**Geocoding** converts raw GPS coordinates (30.2672, -97.7431) into readable locations (Austin, TX).

**Key points:**
- Uses **OpenStreetMap Nominatim API** (free, open-source)
- Requires **internet connection** during processing
- Results are **cached** to minimize API calls
- Respects **1-second delay** between requests (Nominatim policy)
- Works offline after locations are cached

**Example workflow:**
```bash
# First run: Downloads location data from OpenStreetMap
idt workflow C:\VacationPhotos --geocode

# Subsequent runs: Uses cached data (instant, no internet needed)
idt workflow C:\VacationPhotos --geocode
```

### Viewing Metadata

**Viewer Application:**
- Location/date prefix shown in **blue, bold text** with 📍 icon
- Full metadata visible in description text file

**ImageDescriber GUI:**
- Right-click image → **Properties**
- Shows: Location & Date, Camera Information, Photo Settings

**HTML Reports:**
- Location/date prefix highlighted at top of each description
- Full metadata in "Details" section (when using `--full` flag)

### Configuration

**Edit metadata settings in `image_describer_config.json`:**

```json
{
  "metadata": {
    "enabled": true,
    "include_location_prefix": true,
    "geocoding": {
      "enabled": false,
      "user_agent": "IDT/3.0 (+https://github.com/kellylford/Image-Description-Toolkit)",
      "delay_seconds": 1.0,
      "cache_file": "geocode_cache.json"
    }
  }
}
```

**Or use IDTConfigure GUI:**
1. Run `idtconfigure.exe`
2. Settings Menu → **Metadata Settings**
3. Adjust: metadata_enabled, geocoding_enabled, cache_file, etc.

### Example Scenarios

**Scenario 1: Travel Photos with Location Context**
```bash
idt workflow C:\Europe2025 --geocode --name europe_trip
# Descriptions: "Paris, France Jun 15, 2025: The Eiffel Tower..."
```

**Scenario 2: Event Photography (Date Only)**
```bash
idt workflow C:\Wedding --metadata
# Descriptions: "May 12, 2025: The bride and groom..."
# (No GPS data in studio photos, shows date only)
```

**Scenario 3: Privacy-Conscious (No Metadata)**
```bash
idt workflow C:\PersonalPhotos --no-metadata
# Clean descriptions without location/date information
```

**Scenario 4: Large Collection with Geocoding**
```bash
# Initial run builds geocoding cache
idt workflow C:\10000Photos --geocode --geocode-cache worldwide_cache.json

# Reuse cache for other collections
idt workflow C:\MorePhotos --geocode --geocode-cache worldwide_cache.json
```

---

## 10. Analysis Tools

After running workflows, use these tools to analyze and export results:

### Combine Descriptions (Export to CSV/TSV)

**The easiest way to get a readable, screen-reader-friendly export!**

```bash
idt combinedescriptions
```

By default, this:
- ✅ Finds your most recent workflow run
- ✅ **Sorts images chronologically (oldest to newest using EXIF dates)**
- ✅ Exports to `analysis/results/combined_descriptions.csv`
- ✅ Includes all descriptions with metadata
- ✅ Opens beautifully in Excel
- ✅ Works great with screen readers

**Options:**

```bash
# Use default chronological sorting (by image date)
idt combinedescriptions --sort date

# Sort alphabetically by filename instead
idt combinedescriptions --sort name

# Specify workflow directory with date sorting
idt combinedescriptions --input-dir Descriptions/workflow_summer_photos

# Change output format (CSV, TSV, or legacy @-separated)
idt combinedescriptions --output results.tsv --format tsv --sort date

# Custom output location with alphabetical sorting
idt combinedescriptions --output C:\Exports\my_descriptions.csv --sort name

# Combine multiple workflow runs (sorted by date)
idt combinedescriptions --input-dir Descriptions --sort date
```

**💡 New in v3.0:** Images are now sorted by their **actual photo dates** (from EXIF data) instead of filename. This means your vacation photos appear in the order you took them, not alphabetically! Use `--sort name` for the old alphabetical behavior.

**💡 Pro Tip:** After ANY workflow run, immediately run `combinedescriptions` to get a nice Excel-ready file. Perfect for sharing or archiving!

**📊 Screen Reader Tip:** If you ran only one workflow, `combinedescriptions` creates a great easy-to-read CSV that opens perfectly in Excel with screen readers. Each row is one image with its description and metadata.

### Workflow Statistics

Analyze performance, timing, and model usage:

```bash
idt stats

# Or specify a workflow
idt stats Descriptions/workflow_summer_photos
```

Output saved to: `analysis/results/workflow_stats_[timestamp].json`

**Shows:**
- Total images processed
- Processing time
- Average time per image
- Model used
- Provider details
- Success/failure counts

### Content Quality Review

Analyze description quality, word usage, and patterns:

```bash
idt contentreview

# Or specify a workflow
idt contentreview Descriptions/workflow_summer_photos
```

Output saved to: `analysis/results/content_analysis_[timestamp].txt`

**Shows:**
- Description length statistics
- Most common words and phrases
- Readability metrics
- Vocabulary diversity
- Quality indicators

### Analysis Output Location

All analysis results go to:
```
analysis/results/
├── combineddescriptions.csv          # Default combined export (date-sorted)
├── combined_descriptions.csv         # Legacy filename (if specified)
├── workflow_stats_[timestamp].json   # Performance statistics
└── content_analysis_[timestamp].txt  # Content quality analysis
```

**📁 File Organization:** The analysis tools create timestamped files to avoid overwriting previous analyses, except for `combineddescriptions.csv` which is the "current" export file.

---

## 11. Results Viewer (Real-Time Monitoring)

The **Results Viewer** is a GUI application that lets you browse, search, and monitor your workflow results in real-time.

### Automatic Launch

The viewer launches automatically in two scenarios:

#### 1. Using `guideme` (Recommended)
When you run a workflow through the interactive wizard:
```bash
idt guideme
```
The viewer **opens immediately** when the workflow starts, letting you watch progress in real-time as each image is processed!

#### 2. After Direct Workflow Completion
When you run `idt workflow` directly, you'll be prompted after successful completion:
```
Would you like to view the results in the viewer? (y/n): y
```
Type `y` and the viewer opens instantly.

### Manual Launch

You can also launch the viewer manually anytime:

```bash
# Open viewer with directory browser
idt viewer

# Browse Results button shows all available workflows
# - Lists all workflows with metadata
# - Keyboard navigation (arrows, Enter)
# - Single tab stop for accessibility

# Open specific workflow output
idt viewer C:\IDT\Descriptions\workflow_vacation_photos

# Or double-click the auto-generated launcher
# (found in each workflow directory)
Descriptions\workflow_*/view_results.bat
```

### Viewer Features

**Real-Time Monitoring:**
- Live updates as images are processed
- Progress tracking (shown in window title: "75%, 810 of 1077 images described (Live)")
- Automatic refresh when new descriptions appear

**Browse & Search:**
- Navigate through all processed images
- View descriptions alongside images
- Image date displayed (when photo was taken)
- Copy descriptions to clipboard
- Search and filter results

**Browse Results Dialog:**
- Browse all available workflows with one click
- See workflow metadata at a glance (Name, Prompt, Images, Model, Provider, Date)
- Keyboard accessible with single tab stop
- Auto-detects common workflow locations

**Workflow Information:**
- View metadata (model used, prompt style, etc.)
- See processing statistics in window title (always visible)
- Check completion status (100%, 64 of 64 images described)
- Human-friendly date/time formatting (3/25/2025 7:35P)

### Reusable Launcher

Every workflow automatically creates a `view_results.bat` file in its output directory:
```
Descriptions/
└── workflow_vacation_photos/
    ├── images/
    ├── image_descriptions.txt
    ├── index.html
    ├── logs/
    └── view_results.bat  ← Double-click to reopen results anytime!
```

**Benefits:**
- ✅ Quick access to view past results
- ✅ No need to remember viewer commands
- ✅ Create shortcuts or pin to Start menu
- ✅ Share with others to view your workflow outputs

### Viewer Modes

The viewer automatically detects two modes:

**HTML Mode** (Completed workflows):
- Full HTML report with thumbnails
- Complete navigation
- Static, finalized results

**Live Mode** (In-progress workflows):
- Real-time updates as descriptions are generated
- Progress indicators
- Auto-refresh on new content

---

### 11.1 Command Window Progress and Status Log (Convert + Describe)

When running workflows from the command line, IDT provides concise, screen-reader-friendly progress and a human-readable status log:

- Convert step (HEIC → JPG):
   - In-progress: "⟳ Image conversion in progress: X/Y HEIC → JPG (Z%)"
   - Complete:    "✓ Image conversion complete (Y HEIC → JPG)"
   - Progress file: `<workflow_dir>/logs/convert_images_progress.txt`

- Describe step (image descriptions):
   - In-progress: "⟳ Image description in progress: X/Y (Z%)"
   - Complete:    "✓ Image description complete (Y descriptions)"
   - Progress file: `<workflow_dir>/logs/image_describer_progress.txt`

- Aggregated status:
   - Human-readable summary at `<workflow_dir>/logs/status.log`
   - Updated every ~2 seconds while steps are running

Notes:
- Progress files are created when running via the workflow (which passes a `--log-dir` to child processes). Running converters directly without `--log-dir` won’t create progress files.

## 12. Cloud Provider Setup

### OpenAI (GPT-4o, GPT-4o-mini)

1. **Get API Key:** https://platform.openai.com/api-keys
2. **Save to file:** Create a file `openai.txt` with your API key
3. **Run workflow:**
   ```bash
   idt workflow C:\Photos --provider openai --model gpt-4o-mini --api-key-file openai.txt
   ```

**Or use environment variable:**
```bash
set OPENAI_API_KEY=sk-...
idt workflow C:\Photos --provider openai --model gpt-4o
```

**Available models:**
- `gpt-4o` - Best quality, higher cost
- `gpt-4o-mini` - Good quality, economical

### Claude (Anthropic)

1. **Get API Key:** https://console.anthropic.com/
2. **Save to file:** Create a file `claude.txt` with your API key
3. **Run workflow:**
   ```bash
   idt workflow C:\Photos --provider claude --model claude-sonnet-4-5-20250514 --api-key-file claude.txt
   ```

**Or use environment variable:**
```bash
set ANTHROPIC_API_KEY=sk-ant-...
idt workflow C:\Photos --provider claude --model claude-opus-4-20250514
```

**Available models:**
- `claude-opus-4-20250514` - Highest intelligence
- `claude-sonnet-4-5-20250514` - Best balance of speed/quality
- `claude-sonnet-4-20250514` - Fast and capable
- `claude-haiku-3-5-20250219` - Fastest, most economical

### Cost Considerations

- **Ollama:** Free, runs locally, no API costs
- **OpenAI:** Pay per image analyzed (~$0.01-0.10 per image depending on model)
- **Claude:** Pay per image analyzed (~$0.01-0.15 per image depending on model)

💡 **Tip:** Test with Ollama first, then use cloud providers for production or higher quality needs.

---

## 13. Performance Tips

### Adjusting Timeout Settings

The default timeout for Ollama requests is 90 seconds. You may need to adjust this based on your hardware and model size:

```bash
# Fast cloud Ollama (can decrease timeout)
idt workflow C:\Photos --timeout 60

# Standard local setup (default is fine)
idt workflow C:\Photos

# Slower hardware or large models (increase timeout)
idt workflow C:\Photos --timeout 120

# Very slow hardware or huge models (34B+)
idt workflow C:\Photos --timeout 300
```

**When to adjust timeout:**
- ⏱️ **Increase** if you see frequent timeout errors
- ⚡ **Increase** when using large models (13B, 34B parameters)
- 🐌 **Increase** on older hardware or CPU-only systems
- ☁️ **Decrease** when using fast cloud Ollama instances
- 🚀 **Keep default** for most local GPU setups with 7B models

**Symptoms of timeout too low:**
- Frequent "Request timed out after X seconds" errors
- Works for some images but fails on complex ones
- Model is processing but gets interrupted

**Symptoms of timeout too high:**
- Long waits when actual errors occur
- Hangs on genuinely failed requests

---

## 14. Batch Files Reference

The `bat/` folder contains pre-configured batch files for quick model testing.

### Ollama Batch Files

```bash
# Recommended models
bat\run_ollama_moondream.bat C:\Photos
bat\run_ollama_llava7b.bat C:\Photos
bat\run_ollama_llava13b.bat C:\Photos
bat\run_ollama_llama32vision.bat C:\Photos

# Specialized models
bat\run_ollama_bakllava.bat C:\Photos
bat\run_ollama_minicpmv.bat C:\Photos
bat\run_ollama_qwen2.5vl.bat C:\Photos
```

### Cloud Provider Batch Files

```bash
# OpenAI
bat\run_openai_gpt4o.bat C:\Photos
bat\run_openai_gpt4o_mini.bat C:\Photos

# Claude
bat\run_claude_opus4.bat C:\Photos
bat\run_claude_sonnet45.bat C:\Photos
bat\run_claude_haiku35.bat C:\Photos
```

### Setup Batch Files

```bash
# API Key Management
bat\setup_openai_key.bat          # Set up OpenAI API key
bat\setup_claude_key.bat          # Set up Claude API key
bat\remove_openai_key.bat         # Remove OpenAI key
bat\remove_claude_key.bat         # Remove Claude key

# Model Management
bat\install_ollama.bat            # Install Ollama
bat\install_vision_models.bat    # Download recommended models
```

### Testing Batch Files

```bash
# Test all cloud models
bat\allcloudtest.bat C:\Photos

# Test all Ollama models
bat\allmodeltest.bat C:\Photos
```

### ⚠️ Important Note About Batch Files

**Batch files do NOT support the `--name` parameter!**

The batch files are simple wrappers that call the workflow with specific models. They don't pass custom run names.

**To use custom names, use the `idt` command directly:**

```bash
# Instead of this:
bat\run_ollama_llava7b.bat C:\Photos

# Do this if you want a custom name:
idt workflow C:\Photos --model llava:7b --name my_custom_name
```

**Or use `idt guideme` which supports naming through the wizard.**

---

## 15. Troubleshooting

### Common Issues

#### "Ollama not running" or "Connection refused"
**Solution:**
1. Open terminal: `ollama serve`
2. Or restart the Ollama service
3. Check if `ollama list` works

#### "Model not found"
**Solution:**
```bash
ollama pull moondream  # Or your desired model
ollama list            # Verify it's installed
```

#### "API key not found" (OpenAI/Claude)
**Solution:**
1. Check your API key file exists and has the correct key
2. Or set environment variable:
   ```bash
   set OPENAI_API_KEY=sk-...
   set ANTHROPIC_API_KEY=sk-ant-...
   ```

#### "No images found in directory"
**Solution:**
1. Verify the directory path is correct
2. Check that it contains supported formats: `.jpg`, `.jpeg`, `.png`, `.bmp`, `.tiff`, `.webp`, `.heic`, `.heif`
3. Use `--recursive` to include subdirectories

#### Workflow output in wrong location
**Solution:**
- Use `--output-dir` to specify where outputs should go
- Default is `Descriptions/` in the current directory
- Or use `idt guideme` which sets this automatically

#### Applications won't run
**Solution:**
1. Make sure you extracted ALL files from the zip
2. Check that required folders exist next to the executables:
   - `scripts/` folder (required by all applications)
   - `imagedescriber/` folder (for GUI ImageDescriber)
   - `prompt_editor/` folder (for Prompt Editor)
   - `viewer/` folder (for Results Viewer)
3. Run from Command Prompt or PowerShell, not by double-clicking
4. Try each application individually to isolate the issue

#### GUI applications show errors or don't start
**Solution:**
1. Check that all required folders were extracted
2. Verify Ollama is running if using local models: `ollama list`
3. For cloud providers, verify API keys are set correctly
4. Try the CLI version first: `idt guideme` to test basic functionality
5. Check Windows Event Viewer for detailed error messages

### Getting Help

1. **Check the command help:**
   ```bash
   idt help
   idt workflow --help
   ```

2. **Review logs:**
   - Logs are in `Descriptions/workflow_*/logs/`
   - Check `workflow_[timestamp].log` for errors

3. **Test with different applications:**
   ```bash
   # Try CLI wizard first
   idt guideme
   
   # Test GUI ImageDescriber
   imagedescriber.exe
   
   # Test Prompt Editor
   prompt_editor.exe
   
   # Test Results Viewer
   viewer.exe
   ```

4. **GitHub Issues:**
   - Report bugs: https://github.com/kellylford/Image-Description-Toolkit/issues
   - Search existing issues first

---

## Quick Reference Card

### Application Launchers

**GUI Applications:**
```bash
# GUI ImageDescriber - Visual interface for individual images
imagedescriber.exe

# Prompt Editor - Design and test custom prompts
prompt_editor.exe

# Results Viewer - Browse and monitor workflow results
viewer.exe
```

**CLI Application:**
```bash
# Command line interface - Batch processing and automation
idt.exe
```

### Most Common CLI Commands

```bash
# Interactive wizard (start here!)
idt guideme

# Quick workflow with defaults
idt workflow C:\Photos

# Workflow with custom name
idt workflow C:\Photos --name project_alpha

# Use different model
idt workflow C:\Photos --model llava:13b --name detailed_run

# Change prompt style
idt workflow C:\Photos --prompt-style artistic --name art_analysis

# Export to CSV (after any run)
idt combinedescriptions

# View results in GUI (or use auto-prompt after workflow!)
idt viewer

# Launch viewer for specific workflow
idt viewer C:\IDT\Descriptions\workflow_photos

# Check installed models
idt check-models

# Get help
idt help
```

### Application Use Cases

**🖼️ Use GUI ImageDescriber when:**
- Processing individual images or small batches
- Learning different models and prompts
- Need visual feedback and drag-drop interface
- Testing settings before large CLI workflows

**📝 Use Prompt Editor when:**
- Editing or creating custom prompt styles
- Managing prompt variations in config file
- Configuring default AI provider and model
- Setting up API keys for cloud providers
- Preparing configuration before using CLI or GUI

**📋 Use CLI (idt.exe) when:**
- Processing hundreds or thousands of images
- Need automation and batch scripts
- Using advanced workflow features
- Production environments and repeated tasks

**📊 Use Results Viewer when:**
- Browsing completed workflow results
- Monitoring active workflows in real-time
- Searching and filtering descriptions
- Sharing results with others

### File Locations

- **CLI Executable:** `idt.exe`
- **GUI ImageDescriber:** `imagedescriber.exe`
- **Prompt Editor:** `prompt_editor.exe`
- **Results Viewer:** `viewer.exe`
- **Config:** `scripts/image_describer_config.json`
- **Workflow outputs:** `Descriptions/workflow_*/`
- **Analysis results:** `analysis/results/`
- **Logs:** `Descriptions/workflow_*/logs/`
- **Batch files:** `bat/`

---

## Results and output files

When you run image description workflows, IDT writes entries to a text file named `image_descriptions.txt` inside each workflow directory. Each entry typically contains:

- File and full Path
- Optional EXIF metadata block (Photo Date, Location, Camera, Settings)
- Provider, Model, and Prompt Style
- Description
- Timestamp
- Meta suffix (new)
- Separator line

### Meta suffix (new)

At the end of each entry, IDT appends a compact, parseable one-line suffix that surfaces the most useful original capture data for downstream tools:

- Format: `Meta: date=M/D/YYYY H:MMP; location=City, ST; coords=LAT,LON`
- Example: `Meta: date=3/25/2025 7:35P; location=Austin, TX; coords=30.267200,-97.743100`
- Only the fields available for a given image are included.
- If EXIF has no date, file modified time is used as a fallback.
- If GPS is missing but City/State/Country are present, `location=` is included without `coords=`.

### Date/time format standard

All dates shown in the new Meta suffix (and Photo Date when available) follow the project standard:

- M/D/YYYY H:MMP (no leading zeros on month/day/hour, A/P suffix)
- Examples: `3/25/2025 7:35P`, `10/16/2025 8:03A`

This keeps dates consistent across the CLI, the GUI viewer, and analysis tools.

### Backward compatibility

- The existing multi-line metadata block remains unchanged and continues to appear near the top of each entry when metadata is enabled.
- The new Meta suffix is additive and appears after the Timestamp line, before the separator.
- No existing scripts need to change; new consumers can parse the Meta line for quick access to original date/location.

### Example entry

```
File: IMG_1234.JPG
Path: C:/Photos/IMG_1234.JPG
Photo Date: 3/25/2025 7:35P
Location: GPS: 30.267200, -97.743100, Altitude: 165.0m
Camera: Apple iPhone 14 Pro, Lens: iPhone 14 Pro back triple camera 6.86mm f/1.78
Settings: Iso: 100, Aperture: f/1.8, Shutter Speed: 1/120s, Focal Length: 7mm
Provider: ollama
Model: moondream
Prompt Style: detailed
Description: A person on a bridge at sunset...
Timestamp: 2025-10-26 17:22:03
Meta: date=3/25/2025 7:35P; location=Austin, TX; coords=30.267200,-97.743100
--------------------------------------------------------------------------------
```

---

## Further Resources

- **GitHub:** https://github.com/kellylford/Image-Description-Toolkit

---

## Support

For help, bug reports, or feature requests:
- 📧 GitHub Issues: https://github.com/kellylford/Image-Description-Toolkit/issues
- 📖 Documentation: `docs/` folder
- 💬 Use `idt guideme` for step-by-step assistance

**Happy describing!** 🎉
