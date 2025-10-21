# IDT Command Line Reference

Complete reference for the Image Description Toolkit CLI (`idt.exe` or `idt`)

> **📌 Note:** This document covers all CLI commands available in IDT v2.0. For getting started, see the [User Guide](USER_GUIDE.md).

## Table of Contents

1. [Basic Usage](#basic-usage)
2. [Core Workflow Commands](#core-workflow-commands)
3. [GUI Application Commands](#gui-application-commands)
4. [Analysis Tools](#analysis-tools)
5. [Utility Commands](#utility-commands)
6. [Information Commands](#information-commands)
7. [Legacy Commands](#legacy-commands)
8. [Global Options](#global-options)
9. [Environment Variables](#environment-variables)

---

## Basic Usage

```bash
idt <command> [options]
```

- **Windows:** Use `idt.exe` (standalone executable)
- **Development:** Use `python idt_cli.py` or just `idt` if in PATH
- **Help:** `idt help` or `idt <command> --help` for command-specific help

---

## Core Workflow Commands

### `guideme` - Interactive Workflow Wizard
**The recommended way to get started!**

```bash
idt guideme
```

**What it does:**
- Interactive step-by-step workflow setup
- Guides you through model selection, image directory, output location
- Handles API key setup if needed
- Launches viewer automatically for real-time monitoring
- Perfect for screen reader users with accessible prompts

**Options:**
- None - fully interactive

**Example:**
```bash
idt guideme
# Follow the prompts to set up your workflow
```

### `workflow` - Direct Workflow Execution

```bash
idt workflow <image_directory> [options]
```

**Required:**
- `<image_directory>` - Path to folder containing images/videos

**Options:**
```bash
--provider {ollama,openai,claude}     # AI provider (default: ollama)
--model MODEL_NAME                    # Specific model to use
--prompt-style {narrative,detailed,concise,technical,creative,colorful,artistic,simple}
--output-dir OUTPUT_PATH              # Where to save results (default: Descriptions/)
--name WORKFLOW_NAME                  # Custom name for this workflow run
--config CONFIG_FILE                  # Use custom config file
--view-results                        # Launch viewer after completion
--skip-existing                       # Skip images that already have descriptions
--dry-run                            # Show what would be processed without doing it
```

**Examples:**
```bash
# Basic Ollama workflow
idt workflow C:\Photos --model llava --prompt-style narrative

# OpenAI with custom name and viewer launch
idt workflow C:\Photos --provider openai --model gpt-4o --name "vacation_photos" --view-results

# Claude with custom output directory
idt workflow C:\Photos --provider claude --model claude-opus-4 --output-dir C:\Results

# Dry run to preview what will be processed
idt workflow C:\Photos --dry-run
```

---

## GUI Application Commands

### `viewer` / `view` - Results Viewer

```bash
idt viewer [directory] [options]
```

**Options:**
```bash
--open                    # Show directory picker dialog
directory                 # Open specific workflow directory directly
```

**Examples:**
```bash
# Launch viewer with directory browser
idt viewer

# Open specific workflow results
idt viewer C:\IDT\Descriptions\workflow_vacation_photos

# Launch with directory picker
idt viewer --open
```

**Features:**
- Real-time workflow monitoring
- Browse descriptions with keyboard navigation
- Accessible for screen readers
- Live updates during processing
- Redescribe functionality (if configured)

### `prompteditor` - Prompt Template Editor

```bash
idt prompteditor [config_file]
```

**Options:**
```bash
config_file               # Open specific config file (optional)
```

**Examples:**
```bash
# Launch prompt editor
idt prompteditor

# Edit specific config
idt prompteditor scripts/custom_config.json
```

**Features:**
- Visual prompt editing with live preview
- Live Ollama model discovery
- Template management
- Export/import functionality

### `imagedescriber` - Batch Processing GUI

```bash
idt imagedescriber
```

**Features:**
- Interactive batch processing interface
- Progress monitoring with accessibility features
- Manual description editing
- Filter and sort capabilities
- WCAG 2.2 AA compliant interface

---

## Analysis Tools

### `combinedescriptions` - Export to CSV/Excel

```bash
idt combinedescriptions [options]
```

**Options:**
```bash
--input-dir DIRECTORY     # Workflow directory (default: Descriptions/)
--output FILENAME         # Output file (default: analysis/results/combineddescriptions.csv)
--format {csv,tsv,atsv}   # Output format (default: csv)
--sort {date,name}        # Sort order (default: date - NEW in v2.0!)
```

**Sort Options:**
- `date` - **Chronological by photo date** (EXIF DateTimeOriginal → DateTimeDigitized → DateTime → file mtime)
- `name` - Alphabetical by filename (legacy behavior)

**Format Options:**
- `csv` - Standard comma-delimited, opens directly in Excel
- `tsv` - Tab-delimited, excellent Excel compatibility
- `atsv` - @-delimited legacy format

**Examples:**
```bash
# Default: CSV export sorted by photo date
idt combinedescriptions

# Sort alphabetically instead of by date
idt combinedescriptions --sort name

# TSV format with date sorting
idt combinedescriptions --format tsv --sort date --output vacation_results.tsv

# Process specific workflow directory
idt combinedescriptions --input-dir C:\Results\workflow_summer --sort date
```

### `stats` - Workflow Performance Analysis

```bash
idt stats [workflow_directory]
```

**Examples:**
```bash
# Analyze most recent workflow
idt stats

# Analyze specific workflow
idt stats Descriptions/workflow_vacation_photos
```

**Output:** `analysis/results/workflow_stats_[timestamp].json`

**Provides:**
- Processing time statistics
- Images processed counts
- Model performance metrics
- Success/failure rates
- Average time per image

### `contentreview` - Description Quality Analysis

```bash
idt contentreview [workflow_directory]
```

**Examples:**
```bash
# Review most recent workflow
idt contentreview

# Review specific workflow
idt contentreview Descriptions/workflow_summer_photos
```

**Output:** `analysis/results/content_analysis_[timestamp].txt`

**Analyzes:**
- Description length statistics
- Word frequency and patterns
- Readability metrics
- Vocabulary diversity scores
- Content quality indicators

---

## Utility Commands

### `extract-frames` - Video Frame Extraction

```bash
idt extract-frames <video_file> [options]
```

**Options:**
```bash
--output-dir OUTPUT_PATH  # Where to save frames
--fps RATE               # Frames per second to extract
--format {jpg,png}       # Output image format
```

**Examples:**
```bash
# Extract frames from video
idt extract-frames vacation_video.mp4 --fps 1 --output-dir frames/

# High quality PNG extraction
idt extract-frames movie.avi --fps 0.5 --format png
```

### `convert-images` - HEIC to JPG Conversion

```bash
idt convert-images <input_directory> [options]
```

**Options:**
```bash
--output-dir OUTPUT_PATH  # Where to save converted images
--quality QUALITY        # JPEG quality (1-100, default: 95)
--preserve-timestamps     # Keep original file timestamps
```

**Examples:**
```bash
# Convert HEIC images to JPG
idt convert-images C:\Photos\iPhone --output-dir C:\Photos\Converted

# High quality conversion with timestamp preservation
idt convert-images C:\Photos --quality 98 --preserve-timestamps
```

### `descriptions-to-html` - HTML Report Generation

```bash
idt descriptions-to-html <workflow_directory> [options]
```

**Options:**
```bash
--output OUTPUT_FILE      # HTML output file
--template TEMPLATE       # Custom HTML template
--include-metadata        # Include EXIF and processing metadata
```

**Examples:**
```bash
# Generate HTML report
idt descriptions-to-html Descriptions/workflow_vacation_photos

# Custom output with metadata
idt descriptions-to-html Descriptions/workflow_photos --output report.html --include-metadata
```

---

## Information Commands

### `results-list` - List Available Workflows

```bash
idt results-list [options]
```

**Options:**
```bash
--input-dir DIRECTORY     # Directory to scan (default: Descriptions/)
--verbose                 # Show detailed information
--format {table,json}     # Output format
```

**Examples:**
```bash
# List all workflows
idt results-list

# Detailed listing
idt results-list --verbose

# JSON output for scripting
idt results-list --format json
```

### `check-models` - List Available AI Models

```bash
idt check-models [options]
```

**Options:**
```bash
--provider {ollama,openai,claude}  # Check specific provider
--verbose                          # Show model details
```

**Examples:**
```bash
# Check all available models
idt check-models

# Check only Ollama models
idt check-models --provider ollama

# Detailed model information
idt check-models --verbose
```

### `prompt-list` - List Available Prompt Styles

```bash
idt prompt-list [options]
```

**Options:**
```bash
--verbose                 # Show full prompt text
--config CONFIG_FILE      # Use specific config file
```

**Examples:**
```bash
# List prompt styles
idt prompt-list

# Show full prompt text
idt prompt-list --verbose
```

### `version` - Show Version Information

```bash
idt version
idt --version
idt -v
```

**Shows:**
- IDT version number
- Build information
- Component versions

### `help` - Show Help Information

```bash
idt help
idt --help
idt -h
```

**Shows:**
- Command overview
- Usage examples
- Quick reference

---

## Global Options

These options work with most commands:

```bash
--debug                   # Enable debug output
--config CONFIG_FILE      # Use custom configuration file
--quiet                   # Suppress non-essential output
--original-cwd PATH       # Set original working directory context
```

---

## Environment Variables

### API Keys
```bash
# OpenAI
OPENAI_API_KEY=your_openai_key_here

# Anthropic (Claude)
ANTHROPIC_API_KEY=your_claude_key_here
```

### Configuration
```bash
# Default directories
IDT_CONFIG_DIR=C:\path\to\configs
IDT_OUTPUT_DIR=C:\path\to\outputs

# Debugging
IDT_DEBUG=1                # Enable debug mode
IDT_LOG_LEVEL=DEBUG        # Set logging level
```

---

## Exit Codes

```bash
0   # Success
1   # General error
2   # Invalid arguments
3   # Missing dependencies
4   # Permission denied
5   # File not found
```

---

## Examples by Use Case

### Getting Started
```bash
# Interactive setup (recommended)
idt guideme

# Quick Ollama workflow
idt workflow C:\Photos --model llava

# View results
idt viewer
```

### Power User Workflows
```bash
# Named workflow with custom output and viewer
idt workflow C:\Photos --provider claude --model claude-opus-4 \
    --name "professional_photos" --output-dir C:\Results --view-results

# Batch analysis
idt stats
idt contentreview  
idt combinedescriptions --sort date --format tsv
```

### Automation & Scripting
```bash
# Check for available models before processing
idt check-models --provider ollama

# Run workflow and export results
idt workflow C:\Photos --provider ollama --model llava --name "batch_$(date +%Y%m%d)"
idt combinedescriptions --sort date --output "results_$(date +%Y%m%d).csv"

# Generate comprehensive reports
idt stats > stats.json
idt contentreview > content_review.txt
idt descriptions-to-html Descriptions/workflow_batch_* --output full_report.html
```

---

## Troubleshooting

### Common Issues

1. **Command not found**
   ```bash
   # Make sure you're using the right executable name
   idt.exe help    # Windows executable
   python idt_cli.py help  # Development mode
   ```

2. **Permission errors**
   ```bash
   # Run as administrator if needed
   # Check that output directories are writable
   ```

3. **Model not found**
   ```bash
   # Check available models first
   idt check-models --provider ollama
   
   # Install missing Ollama models
   ollama pull llava
   ```

4. **API key issues**
   ```bash
   # Set environment variables properly
   set OPENAI_API_KEY=your_key_here     # Windows CMD
   $env:OPENAI_API_KEY="your_key_here"  # PowerShell
   export OPENAI_API_KEY=your_key_here  # Bash
   ```

### Debug Mode
```bash
# Enable debug output for any command
idt --debug workflow C:\Photos

# Check paths and environment
idt --debug-paths
```

---

## See Also

- [User Guide](USER_GUIDE.md) - Getting started tutorial
- [Prompt Writing Guide](PROMPT_WRITING_GUIDE.md) - How to create effective prompts
- [Build Reference](archive/BUILD_REFERENCE.md) - Building from source
- [API Documentation](archive/AI_AGENT_REFERENCE.md) - For developers