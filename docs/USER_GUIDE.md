# Image Description Toolkit (IDT) - User Guide

## Overview
The Image Description Toolkit (IDT) is a powerful, AI-driven tool for generating natural language descriptions from images and videos. It supports both local (Ollama) and cloud (OpenAI, Claude) AI providers, and is distributed as a standalone Windows executable—**no Python installation required**.

---

## Table of Contents
1. [Installation & Setup](#1-installation--setup)
2. [Getting Started: The Golden Path](#2-getting-started-the-golden-path)
3. [Understanding Workflow Runs & Naming](#3-understanding-workflow-runs--naming)
4. [Prompt Customization](#4-prompt-customization)
5. [Advanced Usage & Commands](#5-advanced-usage--commands)
6. [Analysis Tools](#6-analysis-tools)
7. [Results Viewer (Real-Time Monitoring)](#65-results-viewer-real-time-monitoring)
8. [Cloud Provider Setup](#7-cloud-provider-setup)
9. [Batch Files Reference](#8-batch-files-reference)
10. [Troubleshooting](#9-troubleshooting)

---

## 1. Installation & Setup

### Step 1: Download & Extract
1. Download the latest `ImageDescriptionToolkit_v[VERSION].zip` from GitHub Releases
2. Extract to a folder of your choice (e.g., `C:\IDT\`)
3. The executable is `idt.exe`

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

## 2. Getting Started: The Golden Path

### Option 1: Interactive Guided Setup (Recommended for Beginners)

**The easiest way to get started!** The `guideme` command walks you through every step:

```bash
idt guideme
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

## 3. Understanding Workflow Runs & Naming

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

## 4. Prompt Customization

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

## 5. Advanced Usage & Commands

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

## 6. Analysis Tools

After running workflows, use these tools to analyze and export results:

### Combine Descriptions (Export to CSV/TSV)

**The easiest way to get a readable, screen-reader-friendly export!**

```bash
idt combinedescriptions
```

By default, this:
- ✅ Finds your most recent workflow run
- ✅ Exports to `analysis/results/combined_descriptions.csv`
- ✅ Includes all descriptions with metadata
- ✅ Opens beautifully in Excel
- ✅ Works great with screen readers

**Options:**

```bash
# Specify workflow directory
idt combinedescriptions --workflow-dir Descriptions/workflow_summer_photos

# Change output format
idt combinedescriptions --output results.tsv --format tsv

# Include multiple workflow runs
idt combinedescriptions --workflow-dir Descriptions/workflow_1 Descriptions/workflow_2

# Custom output location
idt combinedescriptions --output C:\Exports\my_descriptions.csv
```

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
├── combined_descriptions.csv
├── workflow_stats_[timestamp].json
└── content_analysis_[timestamp].txt
```

---

## 6.5. Results Viewer (Real-Time Monitoring)

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

## 7. Cloud Provider Setup

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

## 8. Batch Files Reference

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

## 9. Troubleshooting

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

#### Executable won't run
**Solution:**
1. Make sure you extracted ALL files from the zip
2. Check that `scripts/` folder exists next to `idt.exe`
3. Run from Command Prompt or PowerShell, not by double-clicking

### Getting Help

1. **Check the command help:**
   ```bash
   idt help
   idt workflow --help
   ```

2. **Review logs:**
   - Logs are in `Descriptions/workflow_*/logs/`
   - Check `workflow_[timestamp].log` for errors

3. **Test with guideme:**
   ```bash
   idt guideme
   ```
   The wizard validates everything before running

4. **GitHub Issues:**
   - Report bugs: https://github.com/kellylford/Image-Description-Toolkit/issues
   - Search existing issues first

---

## Quick Reference Card

### Most Common Commands

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

### File Locations

- **Executable:** `idt.exe`
- **Config:** `scripts/image_describer_config.json`
- **Workflow outputs:** `Descriptions/workflow_*/`
- **Analysis results:** `analysis/results/`
- **Logs:** `Descriptions/workflow_*/logs/`
- **Batch files:** `bat/`

---

## Further Resources

- **Quick Start Guide:** `QUICK_START.md` (in root folder)
- **Cloud Providers Guide:** `docs/CLOUD_PROVIDERS_GUIDE.md`
- **Configuration Guide:** `docs/CONFIG_OVERRIDES.md`
- **Token Tracking:** `docs/TOKEN_TRACKING_GUIDE.md`
- **FAQ:** `docs/EXECUTABLE_FAQ.md`
- **GitHub:** https://github.com/kellylford/Image-Description-Toolkit

---

## Support

For help, bug reports, or feature requests:
- 📧 GitHub Issues: https://github.com/kellylford/Image-Description-Toolkit/issues
- 📖 Documentation: `docs/` folder
- 💬 Use `idt guideme` for step-by-step assistance

**Happy describing!** 🎉
