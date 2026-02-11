# Image Description Toolkit (IDT) - User Guide

## Overview
The Image Description Toolkit (IDT) is a comprehensive, AI-driven suite for generating natural language descriptions from images and videos. It provides **two applications** to fit different workflows:

- **📋 Command Line Interface (CLI) - `idt.exe`** - Powerful batch processing for automation and large collections
- **🖼️ GUI ImageDescriber - `imagedescriber.exe`** - Interactive desktop application with integrated viewer, prompt editor, and configuration manager

IDT supports both local (Ollama) and cloud (OpenAI, Claude) AI providers, and is distributed as a standalone Windows program—**no Python installation required**.

Note: Ollama must be installed with Ollama models downloaded to use Ollama as an AI option. Visit http://ollama.ai.

---

## Table of Contents
1. [Installation & Setup](#1-installation--setup)
2. [IDT Applications Overview](#2-idt-applications-overview)
3. [Quick Start: GUI Golden Path](#3-quick-start-gui-golden-path)
4. [Quick Start: CLI Golden Path](#4-quick-start-cli-golden-path)
5. [GUI ImageDescriber Application](#5-gui-imagedescriber-application)
6. [Understanding Workflow Runs & Naming](#6-understanding-workflow-runs--naming)
7. [Prompt Customization](#7-prompt-customization)
8. [Advanced CLI Usage & Commands](#8-advanced-cli-usage--commands)
9. [Web Image Downloads](#9-web-image-downloads)
10. [Metadata Extraction & Geocoding](#10-metadata-extraction--geocoding)
11. [Analysis Tools](#11-analysis-tools)
12. [Cloud Provider Setup](#12-cloud-provider-setup)
13. [Performance Tips](#13-performance-tips)
14. [Troubleshooting](#14-troubleshooting)

---

## 1. Installation & Setup

### Step 1: Download & Install
1. Download the latest installer from [GitHub Releases](https://github.com/kellylford/Image-Description-Toolkit/releases)
   - **Windows:** `ImageDescriptionToolkit_Setup_v[VERSION].exe`
   - **macOS:** `IDT-[VERSION].pkg` or `IDT-[VERSION].dmg`
2. Run the installer - it installs to `C:\IDT\` by default (Windows)
3. You'll find two applications in the installation folder:
   - `idt.exe` - Command line interface for batch processing
   - `imagedescriber.exe` - GUI application with integrated viewer

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

IDT provides two applications, each designed for different use cases:

### 📋 Command Line Interface (CLI) - `idt.exe`
**Best for:** Batch processing, automation, advanced workflows, integration with scripts

**Key Features:**
- Process thousands of images at once
- Powerful workflow automation with resume capability
- Advanced analysis and export tools
- Integration with batch scripts and automation
- Full control over all processing parameters
- Interactive `guideme` mode for beginners

**When to use:** Large image collections, repeated workflows, production environments, automation

### 🖼️ GUI ImageDescriber - `imagedescriber.exe`
**Best for:** Individual images, quick testing, visual workflow, beginners

**Key Features:**
- Workspace-based project management  
- Load directories of images for batch processing
- Process All Undescribed from Processing menu
- Visual model and prompt selection
- Interactive provider setup (Ollama/OpenAI/Claude)
- **Switch to Viewer mode** to browse all workflow results with live monitoring
- **Integrated Tools menu:**
  - **Edit Prompts** - Manage custom prompt styles
  - **Configure Settings** - Set default provider, model, and API keys
- Immediate feedback and results
- Perfect for learning and experimentation

**When to use:** Processing directories of images, testing prompts/models, browsing results, visual learners, monitoring active workflows

---

## 3. Quick Start: GUI Golden Path

**The easiest way to get started with ImageDescriber!**

### Step-by-Step Guide

1. **Install Image Description Toolkit**
   - Download and run the installer from the [releases page](https://github.com/kellylford/Image-Description-Toolkit/releases)
   - Default installation location: `C:\IDT\`

2. **Launch ImageDescriber**
   - Activate `imagedescriber.exe` from the installation folder
   - Or use the Start Menu shortcut

3. **Choose a Directory of Images**
   - Click **File → Load Directory** (or press `Ctrl+O`)
   - Browse to a folder containing images you want to describe
   - The images will appear in the workspace

4. **Select Processing Options**
   - Choose your AI **Provider** (Ollama recommended for beginners)
   - Select a **Model** (e.g., `moondream`, `llava:7b`)
   - Pick a **Prompt Style** (e.g., "narrative", "detailed", "concise")

5. **Process All Undescribed Images**
   - Click **Processing → Process All Undescribed** 
   - Watch the progress as images are described
   - Descriptions appear automatically in the list

6. **Review and Export**
   - Click on any image to view its descriptions
   - Edit descriptions if needed
   - Export to HTML using **File → Export to HTML**
   - Or switch to **Viewer mode** using **File → Switch to Viewer** to browse all workflows

**That's it!** You've successfully described your first batch of images.

### Tips for GUI Users

- **View All Results:** Use **File → Switch to Viewer** to see all workflow results in one place with live monitoring
- **Configure Prompts:** Use **Tools → Edit Prompts** to customize description styles
- **Configure Settings:** Use **Tools → Configure IDT** to set default provider and API keys
- **Save Workspace:** Use **File → Save Workspace** to preserve your work
- **Monitor Progress:** The title bar shows completion percentage (e.g., "45%, 9 of 20 images described")

---

## 4. Quick Start: CLI Golden Path

### Option 1: Interactive Guided Setup (Recommended for Beginners)

**The easiest way to get started from the command line!**

1. **Open a Command Prompt**
   - Press `Win+R`, type `cmd`, press Enter
   - Or search for "Command Prompt" in the Start Menu

2. **Change to the Install Directory**
   ```cmd
   cd C:\IDT
   ```
   *(Replace with your actual installation path if different)*

3. **Run the Guided Setup**
   ```cmd
   idt guideme
   ```

4. **Answer the Prompts**
   - The wizard will guide you through:
     - Selecting a provider (Ollama/OpenAI/Claude)
     - Checking for installed models
     - Choosing your image directory
     - Naming your workflow
     - Selecting a prompt style
     - Running the workflow or saving the command

**That's it!** Your images are described and ready to view.

### Option 2: Direct Command (For Experienced Users)

If you already know what you want:

```cmd
cd C:\IDT
idt workflow C:\MyPhotos
```

This runs the full workflow with default settings. Results appear in the `Descriptions/` folder.

---

## 5. GUI ImageDescriber Application

The **GUI ImageDescriber** (`imagedescriber.exe`) provides an intuitive, visual interface for describing images in batch or individually, with an integrated viewer mode for browsing all workflow results.

### Quick Start

1. **Launch:** Double-click `imagedescriber.exe` or run from command line
2. **Load Directory:** File → Load Directory to add images to workspace
3. **Setup Provider:** Choose Ollama (local) or cloud provider (OpenAI/Claude) from tabs
4. **Select Model & Prompt:** Choose from available options
5. **Process:** Use Processing → Process All Undescribed and watch progress!

### Main Interface (Workspace Mode)

**Image Panel (Left):**
- List of all images in the workspace
- Shows processing state (✓ described, • pending, ! paused)
- Click to select and view
- Supports all major formats (JPG, PNG, HEIC, videos)
- **Sorted chronologically** by EXIF date (oldest first)

**Description Panel (Right):**
- View all descriptions for selected image
- Edit, delete, or add new descriptions
- Timestamps and model information
- Full-text display for screen readers

**Provider Tabs:**
- **Ollama Tab:** Automatic model detection, install new models
- **OpenAI Tab:** API key setup, model selection (GPT-4o, GPT-4o-mini)
- **Claude Tab:** API key setup, model selection (Opus, Sonnet, Haiku)
- Real-time connection testing and validation

**Processing Controls:**
- Model and prompt selection dropdowns
- Process selected image or all undescribed
- Pause/Resume batch processing
- Progress tracking in title bar

### Menu Features

**File Menu:**
- **New Workspace** - Start fresh project
- **Load Directory** - Add images from folder
- **Load Workspace** - Open saved .idt project
- **Save/Save As** - Preserve workspace state
- **Export to HTML** - Generate web-viewable results
- **Switch to Viewer** - Browse all workflow results with live monitoring
- **Switch to Workspace** - Return to processing mode

**Processing Menu:**
- **Process Selected Image** - Describe current image
- **Process All Undescribed** - Batch process all pending images
- **Pause Batch** - Temporarily stop processing
- **Resume Batch** - Continue paused workflow

**Tools Menu:**
- **Edit Prompts** - Opens prompt editor dialog
  - Manage custom prompt styles
  - Add, edit, duplicate, or delete prompts
  - Set default prompt style
- **Configure IDT** - Opens configuration dialog
  - Set default AI provider and model
  - Manage API keys for cloud services
  - Configure workflow settings
- **Export Configuration** - Save settings to file
- **Import Configuration** - Load settings from file

**Help Menu:**
- **User Guide** - Opens this guide on GitHub
- **About** - Version and feature information

### Viewer Mode

ImageDescriber's integrated **Viewer Mode** lets you browse all workflow results in one place:

1. **Switch Modes:** Use **File → Switch to Viewer**
2. **Select Workflow:** Choose from all completed and active workflows
3. **Browse Images:** See all images and their descriptions chronologically
4. **Live Monitoring:** Enable to watch active workflows in real-time
5. **Search/Filter:** Find specific images or descriptions
6. **Copy/Export:** Copy descriptions or export results

**Viewer Features:**
- Browse all workflow directories in one interface
- Real-time monitoring of active processing with progress in title bar (e.g., "75%, 810 of 1077 images described (Live)")
- Search across all descriptions
- View image metadata and EXIF data
- Copy descriptions to clipboard
- Access HTML reports
- Filter by workflow, date, or model
- Images displayed in chronological order by EXIF date

**Switching Back:** Use **File → Switch to Workspace** to return to processing mode.

### Video Processing
- Drag and drop video files into workspace
- Automatically extract frames
- Describe each frame individually
- Nested display in image list

### Use Cases

**Perfect for:**
- ✅ Processing directories of photos for organization
- ✅ Batch describing family photo collections
- ✅ Testing new models or prompts on sample images
- ✅ Visual users who prefer GUI interfaces
- ✅ Demonstrating capabilities to others
- ✅ Learning how different providers/models work
- ✅ Managing small to medium image collections (1-1000 images)
- ✅ Browsing all workflow results in one place
- ✅ Monitoring active workflows in real-time

**When to use CLI instead:**
- Processing thousands of images
- Automated workflows and scripting
- Headless server environments
- Need for advanced export/analysis tools

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

**Via GUI ImageDescriber:**
1. Click **Tools → Edit Prompts**
2. Browse available prompts
3. Set default style or create new ones

**Via CLI:**
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

### Creating Effective Custom Prompts

**Best Practices:**
1. **Be Specific:** Clearly state what to include/exclude
2. **Set Context:** Define the purpose ("for accessibility", "for archiving")
3. **Specify Format:** Request paragraph, bullet points, or structured output
4. **Use Examples:** Show the AI what you want (within the prompt itself)
5. **Test Iteratively:** Refine based on actual results

**Example Custom Prompt:**
```
Describe this image for a photo archive. Focus on:
- Main subject and activity
- Location and environment details
- Notable colors and lighting
- Any text or dates visible
Provide a clear paragraph without speculation.
```

### Testing Prompts

1. Use **ImageDescriber GUI** to test prompts on sample images
2. Try the same image with different prompts to compare
3. Check results across different models
4. Refine prompt text based on output quality

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
  --batch                  Non-interactive mode (skip prompts)
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
```

---

## 9. Web Image Downloads

IDT can download images directly from web pages, making it easy to process online galleries, portfolios, or any webpage containing images.

### Simplified Usage

**Just specify the website directly** - IDT automatically detects URLs and sets up the right workflow:

```bash
# Simple website downloads  
idt workflow example.com
idt workflow mywebsite.com
idt workflow https://portfolio.com

# With options
idt workflow gallery.com --max-images 20
idt workflow --download https://site.com/photos --provider openai --model gpt-4o
```

### How It Works

1. **🌐 URL Detection**: IDT automatically recognizes websites vs local directories
2. **🔄 Smart Steps**: Automatically uses `download,describe,html` steps for websites  
3. **📥 Download Step**: Fetches the webpage, parses HTML, downloads all images found
4. **🔍 Duplicate Detection**: Images are checked for duplicates using content hashing
5. **🤖 AI Processing**: Downloaded images are described by your chosen AI model

### Command Options

- `--download URL` - Explicitly download images from this web page
- `--max-images N` - Limit the total number of images downloaded
- `--progress-status` - Show live download and processing progress

### Use Cases

- **Portfolio Analysis**: `idt workflow artistsite.com`
- **Product Catalogs**: `idt workflow shop.com --max-images 50 --provider openai`
- **Gallery Documentation**: `idt workflow gallery.com --name "art_analysis"`

**Note**: Always respect website terms of service and robots.txt when downloading images.

---

## 10. Metadata Extraction & Geocoding

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

### How Geocoding Works

**Geocoding** converts raw GPS coordinates (30.2672, -97.7431) into readable locations (Austin, TX).

**Key points:**
- Uses **OpenStreetMap Nominatim API** (free, open-source)
- Requires **internet connection** during processing
- Results are **cached** to minimize API calls
- Respects **1-second delay** between requests (Nominatim policy)
- Works offline after locations are cached

---

## 11. Analysis Tools

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
```

**💡 Pro Tip:** After ANY workflow run, immediately run `combinedescriptions` to get a nice Excel-ready file. Perfect for sharing or archiving!

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

---

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

---

## 14. Troubleshooting

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

#### Silent failures or "nothing happens" in ImageDescriber
**Problem:** Progress dialog appears but doesn't update, or processing appears to start but freezes.

**Solution:**

1. **Run with debug logging enabled:**
   
   Close ImageDescriber and restart with the `--debug` flag:
   ```batch
   imagedescriber.exe --debug
   ```
   
   This creates a detailed log file at:
   ```
   %USERPROFILE%\imagedescriber_verbose_debug.log
   ```
   Example: `C:\Users\YourName\imagedescriber_verbose_debug.log`

2. **Reproduce the issue** with debug mode enabled, then check the verbose debug log for detailed information.

3. **Log files created with --debug flag**:
   
   **Verbose debug log** (detailed diagnostics):
   ```
   %USERPROFILE%\imagedescriber_verbose_debug.log
   ```
   
   **Crash log** (only if worker thread crashes):
   ```
   %USERPROFILE%\imagedescriber_crash.log
   ```

4. **What to look for in logs:**
   - `ERROR` or `FATAL` lines showing what failed
   - Missing dependencies (e.g., "No module named 'cv2'")
   - File permission errors
   - API connection failures
   - Stack traces showing where code failed

5. **Common fixes:**
   - Restart the application
   - Verify your workspace directory is accessible
   - Check that source files haven't been moved/deleted
   - For API providers, verify your API key is valid

6. **Report the issue:**
   - Include relevant error messages from the verbose debug log
   - GitHub Issues: https://github.com/kellylford/Image-Description-Toolkit/issues

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
   ```

4. **GitHub Issues:**
   - Report bugs: https://github.com/kellylford/Image-Description-Toolkit/issues
   - Search existing issues first

---

## Quick Reference Card

### Application Launchers

**GUI Application:**
```bash
# ImageDescriber - Visual interface with integrated viewer mode
imagedescriber.exe
```

**CLI Commands:**
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

# Check installed models
idt check-models

# Get help
idt help
```

### Application Use Cases

**🖼️ Use ImageDescriber GUI when:**
- Processing directories of images visually
- Testing different models and prompts
- Want immediate visual feedback
- Prefer point-and-click interface
- Browsing workflow results in viewer mode
- Monitoring active workflows in real-time
- Managing small to medium image collections (1-1000 images)

**📋 Use CLI (idt.exe) when:**
- Processing hundreds or thousands of images
- Need automation and batch scripts
- Using advanced workflow features
- Production environments and repeated tasks
- Headless server environments

### File Locations

- **CLI Executable:** `C:\IDT\idt.exe`
- **GUI ImageDescriber:** `C:\IDT\imagedescriber.exe`
- **Config Files:** `C:\IDT\scripts\*.json`
- **Workflow Outputs:** `C:\IDT\Descriptions\workflow_*/`
- **Analysis Results:** `C:\IDT\analysis\results\`

---

## Support

For help, bug reports, or feature requests:
- 📧 GitHub Issues: https://github.com/kellylford/Image-Description-Toolkit/issues
- 📖 Documentation: `docs/` folder
- 💬 Use `idt guideme` for step-by-step assistance

**Happy describing!** 🎉
