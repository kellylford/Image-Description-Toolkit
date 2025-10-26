# Gallery Content Identification Tool

**Configurable image gallery creation from IDT workflow outputs**

## Overview

This tool helps you automatically identify and select images for themed galleries from your IDT workflow results. Instead of manually editing scripts, you can use JSON configuration files or command-line parameters to specify selection criteria.

## Quick Start

### Option 1: Interactive Wizard (Recommended! 🧙‍♂️)
```bash
# Launch the friendly guided wizard
python gallery_wizard.py

# Or double-click wizard.bat on Windows
```
**Perfect for beginners!** The wizard walks you through every step with helpful prompts and examples.

### Option 2: Use a Pre-built Configuration
```bash
# Use one of the ready-made configurations
python identify_gallery_content.py --config example_configs/sunset_water.json
```

### Option 3: Command-Line Interface
```bash
# Create a custom gallery with CLI parameters
python identify_gallery_content.py \
  --name "My Water Gallery" \
  --required water,sun \
  --keywords sunset,reflection,ocean \
  --exclude indoor,night \
  --max-images 30 \
  --output my_gallery.json
```

## Files in This Directory

### Core Tool
- **`gallery_wizard.py`** - 🧙‍♂️ **Interactive wizard (RECOMMENDED!)**
  - Friendly step-by-step guidance
  - No command-line knowledge needed
  - Saves configurations for reuse
  - Handles all the complex options for you
  - **NEW:** Offers IDW workspace creation after identification
- **`identify_gallery_content.py`** - Main script (689 lines)
  - JSON configuration support
  - Full CLI interface
  - Keyword matching and scoring
  - Integration with IDT workflows
- **`create_gallery_idw.py`** - **NEW:** IDW workspace creator
  - Creates ImageDescriber-compatible workspace files
  - Includes all identified images with descriptions
  - Enables visual review in existing IDT tools
- **`wizard.bat`** - Windows launcher for the wizard

### Configuration & Examples
- **`gallery_config_schema.json`** - JSON schema for validation
- **`example_configs/`** - Ready-to-use configurations:
  - `sunset_water.json` - "Sunshine On The Water Makes Me Happy"
  - `mountains.json` - Mountain adventures and hiking
  - `architecture.json` - Urban architecture and buildings
  - `wildlife.json` - Wildlife and nature photography
  - `food.json` - Food photography
  - `README.md` - Configuration guide and examples

### Testing & Documentation
- **`test_identify_gallery_content.py`** - Comprehensive test suite (471 lines, 19 tests)
- **`GALLERY_CONTENT_IDENTIFICATION.md`** - Complete usage guide (564 lines)

## How It Works

1. **Scan IDT Workflows** - Finds all description files from your workflows
2. **Apply Filters** - Uses date ranges, workflow patterns, model preferences
3. **Match Keywords** - Required (must have), preferred (bonus), excluded (filter out)
4. **Score Results** - Ranks images by relevance and quality
5. **Generate Output** - Creates JSON file with ranked candidates for review
6. **🆕 Create IDW Workspace** - Optionally generate `.idw` files for visual review in ImageDescriber/Viewer

## NEW: Visual Review Integration ✨

After identifying gallery candidates, you can now automatically create **IDW workspace files** for seamless visual review:

- **What:** `.idw` files that open directly in ImageDescriber or Viewer
- **Contains:** All identified images with their complete descriptions
- **Benefits:** Visual browsing instead of text file review
- **Access:** Available through the wizard after identification completes

### IDW Integration Workflow
```
1. Run gallery identification (wizard or CLI)
2. Choose "Create IDW workspace" when prompted
3. Open the generated .idw file in ImageDescriber/Viewer
4. Visually browse all candidates with descriptions
5. Select favorites for your gallery
```

## Workflow Integration

```
1. Run IDT workflows on your images (existing)
2. → Use this tool to identify gallery candidates (NEW!)
3. → Optionally create IDW workspace for visual review (NEW!)
4. Review results (JSON file or visual in ImageDescriber/Viewer)
5. Select and copy images to gallery directory
6. Build gallery with existing tools (build_gallery.py)
```

## Example Configurations

### Sunset/Water Gallery
```json
{
  "gallery_name": "Sunshine On The Water Makes Me Happy",
  "content_rules": {
    "required_keywords": ["water", "sun"],
    "preferred_keywords": ["sunset", "sunrise", "reflection", "clouds"],
    "excluded_keywords": ["indoor", "night", "dark"]
  }
}
```

### Mountain Adventure Gallery
```json
{
  "gallery_name": "Mountain Adventures", 
  "content_rules": {
    "required_keywords": ["mountain"],
    "preferred_keywords": ["hiking", "peak", "summit", "trail", "alpine"],
    "excluded_keywords": ["indoor", "urban", "city"]
  }
}
```

## Command Line Examples

```bash
# Simple keyword search
python identify_gallery_content.py --required nature --keywords trees,forest

# Date-filtered search
python identify_gallery_content.py \
  --date-start 2025-10-01 \
  --date-end 2025-10-31 \
  --keywords vacation,travel

# Model-specific search
python identify_gallery_content.py \
  --models claude-opus-4,claude-sonnet-4 \
  --prompts narrative,colorful \
  --keywords artistic,creative

# Multiple directories
python identify_gallery_content.py \
  --scan ./descriptions //qnap/home/idt/descriptions \
  --required water \
  --output combined_results.json
```

## Scoring System

- **Required keywords:** +10 points each (must have ALL)
- **Preferred keywords:** +5 points each (bonus points)
- **Preferred models:** +2-3 bonus points
- **Preferred prompts:** +2-3 bonus points
- **Excluded keywords:** Immediate disqualification

## Output Format

The tool generates:

### JSON Results File
- Ranked list of matching images
- Relevance scores and keyword matches
- Source metadata (workflow, model, prompt)
- File paths for copying to gallery

### IDW Workspace Files (Optional)
- **NEW:** ImageDescriber-compatible workspace files
- Contains all identified images with complete descriptions
- Opens directly in ImageDescriber or Viewer
- Enables visual browsing and selection

## Getting Help

```bash
# Use the interactive wizard (easiest!)
python gallery_wizard.py

# Show all CLI options
python identify_gallery_content.py --help

# See configuration examples
cat example_configs/README.md

# Read complete guide
cat GALLERY_CONTENT_IDENTIFICATION.md
```

## Testing

```bash
# Run the test suite
python test_identify_gallery_content.py

# Test with verbose output
python -m pytest test_identify_gallery_content.py -v
```

---

**Part of:** [Image Description Toolkit](../../../README.md)  
**Parent Tool:** [ImageGallery](../../README.md)  
**Complete Guide:** [GALLERY_CONTENT_IDENTIFICATION.md](GALLERY_CONTENT_IDENTIFICATION.md)