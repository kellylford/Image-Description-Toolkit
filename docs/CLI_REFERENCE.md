# IDT Complete Application Reference

Comprehensive reference for all Image Description Toolkit applications and commands

> **📌 Note:** This document covers ALL applications and commands in IDT v2.0. For getting started, see the [User Guide](USER_GUIDE.md).

## Table of Contents

1. [Application Overview](#application-overview)
2. [IDT Unified CLI (`idt.exe`)](#idt-unified-cli-idtexe)
3. [Standalone GUI Applications](#standalone-gui-applications)
4. [IDT Command Reference](#idt-command-reference)
5. [Global Options & Environment Variables](#global-options--environment-variables)
6. [Examples by Use Case](#examples-by-use-case)
7. [Troubleshooting](#troubleshooting)

---

## Application Overview

IDT v2.0 includes **multiple applications** that can be used independently or together:

### **Primary Applications**

| Application | File | Purpose | Interface |
|-------------|------|---------|-----------|
| **IDT Unified CLI** | `idt.exe` | Command dispatcher & workflow runner | Command Line |
| **Results Viewer** | `viewer.exe` | Browse and monitor workflow results | GUI |
| **ImageDescriber** | `imagedescriber.exe` | Interactive batch processing | GUI |
| **Prompt Editor** | `prompteditor.exe` | Visual prompt template editor | GUI |

### **Usage Patterns**

```bash
# Unified CLI - routes to all functionality
idt <command> [options]

# Standalone GUI applications
viewer.exe [directory]
imagedescriber.exe
prompteditor.exe [config_file]
```

---

## IDT Unified CLI (`idt.exe`)

The unified CLI is the **main entry point** that routes to all toolkit functionality.

### Basic Usage

```bash
idt <command> [options]
```

- **Windows:** Use `idt.exe` (standalone executable)
- **Development:** Use `python idt_cli.py` or just `idt` if in PATH
- **Help:** `idt help` or `idt <command> --help` for command-specific help

### Complete Command List

```bash
# Interactive & Workflow Commands
idt guideme               # Interactive workflow wizard ⭐ RECOMMENDED
idt workflow              # Direct workflow execution
idt viewer                # Launch results viewer GUI
idt imagedescriber        # Launch batch processing GUI  
idt prompteditor          # Launch prompt editor GUI

# Analysis Tools
idt combinedescriptions   # Export workflows to CSV/Excel (date-sorted by default)
idt stats                 # Workflow performance analysis
idt contentreview         # Description quality analysis

# Information & Discovery
idt results-list          # List available workflow results
idt check-models          # List available AI models
idt prompt-list           # List available prompt styles
idt version               # Show version information

# Utility Commands
idt extract-frames        # Extract frames from videos
idt convert-images        # Convert HEIC images to JPG
idt descriptions-to-html  # Generate HTML reports

# Help & Legacy
idt help                  # Show help information
idt image_describer       # Legacy: same as 'imagedescriber'
```

---

## Standalone GUI Applications

These applications run independently and have their own interfaces:

### `viewer.exe` - Results Viewer

**Purpose:** Browse workflow results with real-time monitoring capabilities

```bash
# Launch methods
viewer.exe                           # Directory browser mode
viewer.exe C:\path\to\workflow       # Direct directory mode
viewer.exe --open                    # Directory picker dialog

# Via IDT CLI
idt viewer                           # Same as viewer.exe
idt viewer C:\path\to\workflow       # Direct directory
idt viewer --open                    # Directory picker
```

**Features:**
- ✅ **Real-time monitoring** - Watch workflows as they process
- ✅ **Keyboard navigation** - Full accessibility support
- ✅ **Live updates** - Automatically refreshes during processing
- ✅ **Search and filter** - Find specific images or descriptions
- ✅ **WCAG 2.2 AA compliant** - Screen reader optimized

**Interface Elements:**
- **Browse Results button** - Shows directory picker for all available workflows
- **Image list** - Keyboard navigable with arrow keys and Enter
- **Description panel** - Shows full description with metadata
- **Status bar** - Real-time progress and statistics
- **Title bar** - Shows completion percentage and workflow name

### `imagedescriber.exe` - Batch Processing GUI

**Purpose:** Interactive batch processing with full accessibility features

```bash
# Launch methods
imagedescriber.exe                   # Main GUI interface

# Via IDT CLI  
idt imagedescriber                   # Same as imagedescriber.exe
```

**Features:**
- ✅ **Interactive processing** - Visual workflow setup and execution
- ✅ **Progress monitoring** - Real-time processing status with accessibility
- ✅ **Manual editing** - Edit descriptions after AI generation
- ✅ **Filter and sort** - Organize images by processing status
- ✅ **Process All** - Batch process multiple images with live updates
- ✅ **Stop processing** - Graceful workflow cancellation
- ✅ **WCAG 2.2 AA compliant** - Full screen reader support

**Main Interface:**
- **Image list** - Shows all images with processing status
- **Description panel** - Edit and review descriptions
- **Progress indicators** - Visual and accessible progress updates
- **Model selection** - Choose AI provider and model
- **Process controls** - Start, stop, and monitor processing

### `prompteditor.exe` - Prompt Template Editor

**Purpose:** Visual editor for creating and managing prompt templates

```bash
# Launch methods
prompteditor.exe                     # Default config
prompteditor.exe config.json         # Specific config file

# Via IDT CLI
idt prompteditor                     # Default config
idt prompteditor config.json         # Specific config
```

**Features:**
- ✅ **Live preview** - See how prompts will appear to AI models
- ✅ **Template management** - Create, edit, save, and load prompt templates
- ✅ **Model integration** - Live discovery of available Ollama models
- ✅ **Export/import** - Share prompt configurations
- ✅ **Syntax highlighting** - Visual editing with proper formatting
- ✅ **Auto-save** - Prevents loss of work

**Interface Elements:**
- **Prompt editor** - Main text editing area with syntax highlighting
- **Model selector** - Choose AI model for testing
- **Preview panel** - See processed prompt template
- **Template library** - Load and save prompt configurations
- **Export tools** - Share prompts with others

---

## IDT Command Reference

Detailed reference for all `idt` commands with options and examples.

### Interactive & Workflow Commands

#### `guideme` - Interactive Workflow Wizard ⭐
**The recommended way to get started!**

```bash
idt guideme [workflow_options]
```

**What it does:**
- Interactive step-by-step workflow setup with accessible prompts
- Guides through model selection, image directory, output location  
- Handles API key setup if needed
- Launches viewer automatically for real-time monitoring
- Perfect for screen reader users and beginners
- **NEW:** Accepts workflow options (like `--timeout`) for advanced control

**Workflow Options Pass-Through:**
You can pass any workflow option to `guideme` and it will be included in the generated command:

```bash
# Increase timeout for large vision models (use any value in seconds)
idt guideme --timeout 300
idt guideme --timeout 180
idt guideme --timeout 600

# Preserve existing descriptions when re-running
idt guideme --preserve-descriptions

# Combine multiple options
idt guideme --timeout 180 --preserve-descriptions
```

Common workflow options that work with guideme:
- `--timeout SECONDS` - API request timeout (default: 90). Recommended: 180-300 for large models like Qwen
- `--preserve-descriptions` - Skip images that already have descriptions

**Interactive Steps:**
1. **Model Selection** - Choose from available Ollama, OpenAI, or Claude models
2. **Image Directory** - Select folder containing images/videos to process
3. **Output Location** - Choose where to save results (default: Descriptions/)
4. **Workflow Naming** - Optional custom name for organization
5. **Launch Options** - Option to launch viewer for real-time monitoring

**Example Sessions:**
```bash
# Basic interactive workflow
idt guideme
# Follow the interactive prompts:
# > Select AI provider: [ollama] openai claude
# > Choose model: llava llava:13b minicpm-v ...
# > Image directory: C:\Photos
# > Workflow name (optional): vacation_photos
# > Launch viewer? [Y/n]: y

# With extended timeout for slow models
idt guideme --timeout 300
# Then proceed through the interactive prompts as usual
# The generated command will include --timeout 300
```

#### `workflow` - Direct Workflow Execution

```bash
idt workflow <image_directory> [options]
```

**Required:**
- `<image_directory>` - Path to folder containing images/videos

**Core Options:**
```bash
--provider {ollama,openai,claude}     # AI provider (default: ollama)
--model MODEL_NAME                    # Specific model to use
--prompt-style STYLE                  # See prompt styles below
--output-dir OUTPUT_PATH              # Where to save results (default: Descriptions/)
--name WORKFLOW_NAME                  # Custom name for this workflow run
```

**Advanced Options:**
```bash
--config CONFIG_FILE                  # Use custom config file
--view-results                        # Launch viewer after completion
--skip-existing                       # Skip images that already have descriptions
--dry-run                            # Show what would be processed without doing it
--original-cwd PATH                   # Set working directory context
--steps STEPS                         # Workflow steps: video,convert,describe,html
--timeout SECONDS                     # Ollama request timeout (default: 90, increase for slow hardware)
```

**Prompt Styles:**
- `narrative` - Story-like descriptions with context
- `detailed` - Comprehensive technical descriptions  
- `concise` - Brief, essential details only
- `technical` - Photography and technical analysis
- `creative` - Artistic and emotional interpretations
- `colorful` - Focus on colors and visual elements
- `artistic` - Art analysis and composition
- `simple` - Basic, accessible descriptions

**Examples:**
```bash
# Basic Ollama workflow
idt workflow C:\Photos --model llava --prompt-style narrative

# OpenAI with custom name and viewer launch
idt workflow C:\Photos --provider openai --model gpt-4o --name "vacation_photos" --view-results

# Claude with custom output directory
idt workflow C:\Photos --provider claude --model claude-opus-4 --output-dir C:\Results

# Increase timeout for slower hardware or large models
idt workflow C:\Photos --timeout 120

# Dry run to preview what will be processed
idt workflow C:\Photos --dry-run

# Skip existing descriptions, launch viewer
idt workflow C:\Photos --skip-existing --view-results

# Custom workflow with specific steps
idt workflow C:\Videos --steps video,describe --name "video_analysis"
```

### GUI Application Launchers

#### `viewer` / `view` - Results Viewer

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

# Alternative command alias
idt view C:\Results\workflow_photos
```

#### `prompteditor` - Prompt Template Editor

```bash
idt prompteditor [config_file]
```

**Options:**
```bash
config_file               # Open specific config file (optional)
```

**Examples:**
```bash
# Launch prompt editor with default config
idt prompteditor

# Edit specific config file
idt prompteditor scripts/custom_config.json

# Edit ImageDescriber config
idt prompteditor scripts/image_describer_config.json
```

#### `imagedescriber` - Batch Processing GUI

```bash
idt imagedescriber
```

**What it does:**
- Launches the interactive batch processing GUI
- Full-featured interface for processing multiple images
- Real-time progress monitoring with accessibility features
- Manual description editing capabilities

**Example:**
```bash
# Launch ImageDescriber GUI
idt imagedescriber
```

### Analysis Tools

#### `combinedescriptions` - Export to CSV/Excel ⭐

```bash
idt combinedescriptions [options]
```

**What it does:**
- Combines descriptions from multiple workflow runs into a single file
- **NEW in v2.0:** Sorts images chronologically by photo date (EXIF data) by default
- Creates Excel-ready files with proper formatting
- Works across all workflow directories automatically

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
- `csv` - Standard comma-delimited, opens directly in Excel ⭐
- `tsv` - Tab-delimited, excellent Excel compatibility
- `atsv` - @-delimited legacy format (requires Excel import wizard)

**Examples:**
```bash
# Default: CSV export sorted by photo date (RECOMMENDED)
idt combinedescriptions

# Sort alphabetically instead of by date (legacy behavior)
idt combinedescriptions --sort name

# TSV format with date sorting
idt combinedescriptions --format tsv --sort date --output vacation_results.tsv

# Process specific workflow directory
idt combinedescriptions --input-dir C:\Results\workflow_summer --sort date

# Legacy @-separated format with filename sorting
idt combinedescriptions --format atsv --sort name --output legacy_results.txt
```

#### `stats` - Workflow Performance Analysis

```bash
idt stats [workflow_directory]
```

**What it does:**
- Analyzes workflow performance metrics
- Generates detailed timing and throughput statistics
- Identifies bottlenecks and optimization opportunities

**Examples:**
```bash
# Analyze most recent workflow
idt stats

# Analyze specific workflow
idt stats Descriptions/workflow_vacation_photos

# Analyze by directory path
idt stats C:\Results\workflow_summer_photos
```

**Output:** `analysis/results/workflow_stats_[timestamp].json`

**Metrics Provided:**
- Total processing time and average time per image
- Images processed vs skipped counts
- Model performance and throughput rates
- Success/failure rates and error analysis
- HEIC conversion timing (if applicable)
- Video frame extraction timing (if applicable)

#### `contentreview` - Description Quality Analysis

```bash
idt contentreview [workflow_directory]
```

**What it does:**
- Analyzes description content quality and patterns
- Evaluates vocabulary richness and readability
- Identifies common themes and word usage patterns

**Examples:**
```bash
# Review most recent workflow
idt contentreview

# Review specific workflow
idt contentreview Descriptions/workflow_summer_photos

# Review by directory path
idt contentreview C:\Results\workflow_technical_photos
```

**Output:** `analysis/results/content_analysis_[timestamp].txt`

**Analysis Includes:**
- Description length statistics (min, max, average, median)
- Word frequency analysis and vocabulary diversity
- Readability metrics and complexity scores
- Content categorization (colors, emotions, technical terms)
- Quality indicators and consistency measures

---

## Utility Commands

#### `extract-frames` - Video Frame Extraction

```bash
idt extract-frames <video_file> [options]
```

**What it does:**
- Extracts individual frames from video files
- Supports multiple video formats (MP4, AVI, MOV, etc.)
- Configurable frame rate and output quality
- Perfect for creating image datasets from videos

**Options:**
```bash
--output-dir OUTPUT_PATH  # Where to save frames (default: extracted_frames/)
--fps RATE               # Frames per second to extract (default: 1)
--format {jpg,png}       # Output image format (default: jpg)
--quality QUALITY        # Output quality 1-100 (default: 95)
```

**Examples:**
```bash
# Basic frame extraction (1 fps)
idt extract-frames vacation_video.mp4

# High frequency extraction
idt extract-frames movie.avi --fps 2 --output-dir movie_frames/

# High quality PNG extraction for analysis
idt extract-frames presentation.mp4 --fps 0.5 --format png --quality 100

# Extract every 10 seconds from a long video
idt extract-frames lecture.mp4 --fps 0.1 --output-dir lecture_slides/
```

#### `convert-images` - HEIC to JPG Conversion

```bash
idt convert-images <input_directory> [options]
```

**What it does:**
- Converts Apple HEIC images to standard JPG format
- Preserves image quality and metadata when possible
- Batch processes entire directories
- Essential for processing iPhone/iPad photos

**Options:**
```bash
--output-dir OUTPUT_PATH  # Where to save converted images
--quality QUALITY        # JPEG quality 1-100 (default: 95)
--preserve-timestamps     # Keep original file timestamps
--recursive              # Process subdirectories
```

**Examples:**
```bash
# Convert iPhone photos to JPG
idt convert-images C:\Photos\iPhone --output-dir C:\Photos\JPG

# High quality conversion with timestamp preservation
idt convert-images C:\Photos --quality 98 --preserve-timestamps

# Recursive conversion of directory tree
idt convert-images C:\Photos\RAW --recursive --output-dir C:\Photos\Converted
```

#### `descriptions-to-html` - HTML Report Generation

```bash
idt descriptions-to-html <workflow_directory> [options]
```

**What it does:**
- Generates comprehensive HTML reports from workflow results
- Creates web-friendly galleries with descriptions
- Includes metadata and processing information
- Perfect for sharing results or archival purposes

**Options:**
```bash
--output OUTPUT_FILE      # HTML output file (default: auto-generated)
--template TEMPLATE       # Custom HTML template file
--include-metadata        # Include EXIF and processing metadata
--title TITLE            # Custom report title
```

**Examples:**
```bash
# Generate basic HTML report
idt descriptions-to-html Descriptions/workflow_vacation_photos

# Custom output with metadata
idt descriptions-to-html Descriptions/workflow_photos --output vacation_report.html --include-metadata

# Custom title and template
idt descriptions-to-html Descriptions/workflow_art --title "Art Collection Analysis" --template custom.html
```

---

## Information & Discovery Commands

#### `results-list` - List Available Workflows

```bash
idt results-list [options]
```

**What it does:**
- Scans for available workflow results
- Shows metadata and completion status
- Provides viewer launch commands for each workflow
- Essential for discovering what results are available

**Options:**
```bash
--input-dir DIRECTORY     # Directory to scan (default: Descriptions/)
--verbose                 # Show detailed information
--format {table,json}     # Output format (default: table)
```

**Examples:**
```bash
# List all workflows in default directory
idt results-list

# Detailed listing with metadata and stats
idt results-list --verbose

# JSON output for scripting
idt results-list --format json

# Scan custom directory for workflows
idt results-list --input-dir C:\MyResults
```

#### `check-models` - List Available AI Models

```bash
idt check-models [options]
```

**What it does:**
- Discovers available models from all providers
- Shows model status and readiness
- Validates API connectivity for cloud providers
- Helps troubleshoot model configuration issues

**Options:**
```bash
--provider {ollama,openai,claude}  # Check specific provider only
--verbose                          # Show detailed model information
```

**Examples:**
```bash
# Check all available models across all providers
idt check-models

# Check only Ollama models
idt check-models --provider ollama

# Check OpenAI models with details
idt check-models --provider openai --verbose

# Check Claude models and connectivity
idt check-models --provider claude
```

#### `prompt-list` - List Available Prompt Styles

```bash
idt prompt-list [options]
```

**What it does:**
- Lists all configured prompt styles
- Shows prompt descriptions and use cases
- Can display full prompt text for review
- Useful for selecting appropriate prompts for different image types

**Options:**
```bash
--verbose                 # Show full prompt text
--config CONFIG_FILE      # Use specific config file
```

**Examples:**
```bash
# List available prompt styles
idt prompt-list

# Show full prompt text for all styles
idt prompt-list --verbose

# List prompts from custom config
idt prompt-list --config scripts/custom_config.json
```

### System & Help Commands

#### `version` - Show Version Information

```bash
idt version
idt --version
idt -v
```

**What it shows:**
- IDT version number and build date
- Python version and platform information
- Component versions (viewer, imagedescriber, etc.)
- Git commit hash (if available)

#### `help` - Show Help Information

```bash
idt help
idt --help
idt -h
```

**What it shows:**
- Complete command overview
- Usage examples for common tasks
- Quick reference for all commands
- Links to documentation

### Legacy & Compatibility Commands

#### `image_describer` - Legacy ImageDescriber Launcher

```bash
idt image_describer
```

**Note:** Identical to `idt imagedescriber` - kept for backward compatibility with old scripts and documentation.

---

## Standalone GUI Applications

### `viewer.exe` - Results Viewer

**Windows Command:**
```cmd
viewer.exe [workflow_directory]
```

**What it does:**
- Interactive results browser with live monitoring
- WCAG 2.2 AA accessible interface with screen reader support
- View images and descriptions side-by-side
- Monitor workflows in real-time with progress updates
- Export functionality and workflow statistics

**Features:**
- **Live Mode:** Real-time monitoring of active workflows
- **Accessibility:** Full keyboard navigation and screen reader support
- **Date Sorting:** Images displayed chronologically by EXIF date
- **Statistics:** Always-visible progress indicators in window title
- **Export Options:** Built-in export to CSV/Excel functionality

**Examples:**
```cmd
# Launch viewer for most recent workflow
viewer.exe

# View specific workflow directory
viewer.exe Descriptions\workflow_vacation_photos

# View results from custom location
viewer.exe C:\Results\my_workflow
```

### `imagedescriber.exe` - Batch Processing GUI

**Windows Command:**
```cmd
imagedescriber.exe
```

**What it does:**
- Full-featured batch processing interface
- Interactive model and prompt selection
- Real-time progress monitoring with accessibility features
- Manual description editing capabilities
- Advanced configuration options

**Features:**
- **Model Selection:** Choose from available Ollama, OpenAI, or Claude models
- **Prompt Customization:** Select from predefined prompts or create custom ones
- **Progress Monitoring:** Real-time updates with accessible progress indicators
- **Manual Editing:** Edit generated descriptions before saving
- **Accessibility:** Full WCAG 2.2 AA compliance with screen reader support

**Key Usage:**
1. Launch the application
2. Select source directory containing images
3. Choose AI model and prompt style
4. Monitor progress in real-time
5. Review and edit descriptions as needed
6. Save results to workflow directory

### `prompteditor.exe` - Prompt Configuration Editor

**Windows Command:**
```cmd
prompteditor.exe [config_file]
```

**What it does:**
- Visual editor for creating and modifying prompt configurations
- Syntax highlighting and validation
- Preview functionality for prompt templates
- Integration with both CLI and GUI tools

**Features:**
- **Visual Editing:** User-friendly interface for prompt creation
- **Syntax Validation:** Real-time validation of JSON configuration
- **Template Preview:** See how prompts will appear to AI models
- **Integration:** Works with both CLI workflows and ImageDescriber GUI

**Examples:**
```cmd
# Launch with default configuration
prompteditor.exe

# Edit specific configuration file
prompteditor.exe scripts\image_describer_config.json

# Edit custom prompt configuration
prompteditor.exe C:\MyConfigs\custom_prompts.json
```

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

# Run workflow with date-based naming
idt workflow C:\Photos --provider ollama --model llava --name "batch_20241215"
idt combinedescriptions --sort date --output "results_20241215.csv"

# Generate comprehensive reports
idt stats > analysis/workflow_stats.json
idt contentreview > analysis/content_review.txt
idt descriptions-to-html Descriptions/workflow_batch_* --output reports/full_report.html
```

### GUI Application Workflows
```cmd
REM Windows batch file example
REM Process images with GUI tools

REM Launch batch processing
imagedescriber.exe

REM View results (can run simultaneously)
viewer.exe

REM Edit prompts for next run
prompteditor.exe scripts\image_describer_config.json
```

---

## Troubleshooting

### Common Issues

#### 1. Command not found
```bash
# Make sure you're using the right executable name
idt.exe help                 # Windows executable
python idt_cli.py help       # Development mode

# Check if IDT is in your PATH
where idt.exe               # Windows
which idt                   # Linux/Mac
```

#### 2. Permission errors
```bash
# Run as administrator if needed (Windows)
# Check that output directories are writable
# Verify user has read access to input directories
```

#### 3. Model not found or unavailable
```bash
# Check available models first
idt check-models --provider ollama

# Install missing Ollama models
ollama pull llava
ollama pull llava:13b

# Verify cloud API connectivity
idt check-models --provider openai --verbose
```

#### 4. API key issues
```bash
# Set environment variables properly
set OPENAI_API_KEY=your_key_here        # Windows CMD
$env:OPENAI_API_KEY="your_key_here"     # PowerShell
export OPENAI_API_KEY=your_key_here     # Bash

# Use helper scripts (Windows)
bat\setup_openai_key.bat
bat\setup_claude_key.bat
```

#### 5. Image format issues
```bash
# Convert HEIC images first
idt convert-images C:\Photos\iPhone --output-dir C:\Photos\JPG

# Check supported formats
idt help workflow
```

#### 6. Workflow directory issues
```bash
# List available workflows
idt results-list --verbose

# Check directory permissions
# Ensure workflow completed successfully
idt stats [workflow_directory]
```

#### 7. Timeout errors with Ollama
```bash
# Increase timeout for slower hardware or large models
idt workflow C:\Photos --timeout 120

# Default is 90 seconds - adjust based on your hardware:
# - Fast cloud Ollama: 60-90 seconds
# - Local powerful GPU: 90-120 seconds  
# - Slower hardware or large models (34B+): 180-300 seconds
```

#### 8. GUI applications not launching
```cmd
REM Check if dependencies are installed
REM Try running from command line to see error messages
imagedescriber.exe
viewer.exe
prompteditor.exe

REM Check if Python environment is properly configured
python --version
```

### Getting Help

- **Documentation:** Check `docs/` directory for comprehensive guides
- **Command Help:** Use `idt help` or `idt [command] --help` for specific commands
- **Verbose Output:** Add `--debug` flag to any command for detailed logging
- **GitHub Issues:** Report bugs or feature requests on the project repository

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