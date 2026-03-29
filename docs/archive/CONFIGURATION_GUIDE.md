# Configuring and Controlling IDT Through Config Files

**Version:** 3.5.0  
**Last Updated:** November 1, 2025

This guide explains how to configure and customize the Image Description Toolkit (IDT) using configuration files with the frozen/built version (`idt.exe`). It covers all three configuration file types, their settings, and how to use custom configurations across all IDT tools.

---

## Table of Contents

1. [Overview](#overview)
2. [The Three Configuration Files](#the-three-configuration-files)
3. [Configuration File Locations](#configuration-file-locations)
4. [Configuration Priority Order](#configuration-priority-order)
5. [workflow_config.json](#workflow_configjson)
6. [image_describer_config.json](#image_describer_configjson)
7. [video_frame_extractor_config.json](#video_frame_extractor_configjson)
8. [Using Custom Config Files](#using-custom-config-files)
9. [Common Configuration Scenarios](#common-configuration-scenarios)
10. [Troubleshooting](#troubleshooting)

---

## Overview

IDT uses three JSON configuration files to control its behavior:

1. **`workflow_config.json`** - Controls workflow-level settings (steps, output, metadata)
2. **`image_describer_config.json`** - Controls AI model settings, prompts, and image description behavior
3. **`video_frame_extractor_config.json`** - Controls video frame extraction settings

These files allow you to:
- Set default AI models and providers
- Customize prompts and description styles
- Configure video frame extraction parameters
- Control metadata extraction and geocoding
- Define output formats and locations
- Create reusable configuration profiles for different projects

---

## The Three Configuration Files

### Quick Reference

| Config File | Purpose | Used By |
|-------------|---------|---------|
| `workflow_config.json` | Workflow orchestration, output settings | `idt workflow` command |
| `image_describer_config.json` | AI models, prompts, image processing | `idt describe`, ImageDescriber GUI, workflow describe step |
| `video_frame_extractor_config.json` | Video frame extraction settings | `idt extract-frames`, workflow extract step |

---

## Configuration File Locations

### System Default Configs

When you run the frozen IDT executable (`c:\idt\idt.exe`), it looks for config files in:

```
c:\idt\scripts\
├── workflow_config.json
├── image_describer_config.json
└── video_frame_extractor_config.json
```

These are the **system defaults** that ship with IDT. You can modify these directly, but it's better to create custom config files (see below).

### Custom Config File Locations

You can create custom config files anywhere and reference them with command-line arguments:

```bash
# Custom configs in your user directory
c:\users\yourusername\myconfigs\
├── custom_workflow.json
├── my_description_config.json
└── my_video_config.json

# Custom configs in project directories
d:\projects\vacation2024\
└── vacation_config.json
```

---

## Configuration Priority Order

IDT uses a **4-level priority system** when determining which settings to use:

```
1. Command-Line Arguments (--model, --prompt-style, etc.)
   ↓ (if not provided)
2. Custom Config File Defaults (--config-image-describer, etc.)
   ↓ (if not provided)
3. Workflow Config File (workflow_config.json)
   ↓ (if not provided)
4. System Defaults (built-in fallbacks)
```

### Example

```bash
# Custom config has default_model: "gemma3latest"
# Command line specifies --model moondream
idt workflow photos/ --config-image-describer c:\myconfigs\custom.json --model moondream

# Result: Uses moondream (CLI args win)
```

```bash
# Custom config has default_model: "gemma3latest"
# No --model specified on command line
idt workflow photos/ --config-image-describer c:\myconfigs\custom.json

# Result: Uses gemma3latest (custom config default wins)
```

This priority system gives you maximum flexibility:
- **CLI arguments** for one-off overrides
- **Custom configs** for project-specific defaults
- **Workflow config** for general defaults
- **System defaults** as ultimate fallbacks

---

## workflow_config.json

Controls overall workflow behavior, default steps, and output settings.

### Location
- System default: `c:\idt\scripts\workflow_config.json`
- Custom: Anywhere (use `--config-workflow` to specify)

### Complete Settings Reference

```json
{
  "workflow_settings": {
    "default_steps": ["extract", "convert", "describe", "html"],
    "frame_extraction_per_second": 1.0,
    "image_conversion": true,
    "max_workers": 4,
    "enable_html_output": true,
    "output_base_dir": "c:\\idt\\workflows",
    "enable_metadata_extraction": true,
    "enable_geocoding": true
  },
  
  "metadata_settings": {
    "extract_gps": true,
    "extract_datetime": true,
    "extract_camera_info": true,
    "geocoding_service": "nominatim",
    "geocode_cache_file": "geocode_cache.json",
    "geocode_rate_limit": 1.0
  },
  
  "ai_provider_settings": {
    "default_provider": "ollama",
    "default_model": "moondream:latest",
    "openai_api_key": "",
    "anthropic_api_key": ""
  },
  
  "video_extraction_settings": {
    "default_fps": 1.0,
    "extract_metadata": true,
    "max_dimensions": null
  }
}
```

### Key Settings Explained

#### `default_steps`
Defines which workflow steps run by default if not specified with `--steps`:
- `"extract"` - Extract frames from videos
- `"convert"` - Convert images to JPEG format
- `"describe"` - Generate AI descriptions
- `"html"` - Create HTML gallery

**Example:**
```json
"default_steps": ["describe", "html"]  // Skip extraction, only describe and create HTML
```

#### `output_base_dir`
Where workflow output directories are created. Each workflow gets a timestamped subdirectory.

**Example:**
```json
"output_base_dir": "d:\\projects\\descriptions"
```

Result: Workflows created in `d:\projects\descriptions\wf_<name>_<timestamp>\`

#### `enable_metadata_extraction` and `enable_geocoding`
Control whether EXIF metadata and GPS geocoding are enabled by default.

**Note:** As of v3.5.0, both default to `true`. Use `--no-metadata` and `--no-geocode` CLI flags to disable.

#### `max_workers`
Number of parallel processes for image description. Higher = faster but more CPU/memory.

**Recommendations:**
- 4 workers: Good for most systems
- 8 workers: High-end desktops
- 2 workers: Laptops or systems with limited RAM

### Using Custom workflow_config.json

```bash
# Specify custom workflow config
idt workflow photos/ --config-workflow c:\myconfigs\my_workflow.json

# Custom config with other options
idt workflow videos/ --config-workflow d:\projects\project_settings.json --steps extract,describe
```

---

## image_describer_config.json

Controls AI model selection, prompts, description styles, and image processing behavior.

### Location
- System default: `c:\idt\scripts\image_describer_config.json`
- Custom: Anywhere (use `--config-image-describer` to specify)

### Complete Settings Reference

```json
{
  "default_model": "moondream:latest",
  "default_provider": "ollama",
  "default_prompt_style": "narrative",
  
  "model_settings": {
    "provider": "ollama",
    "model": "moondream:latest",
    "temperature": 0.7,
    "max_tokens": 500,
    "timeout": 60
  },
  
  "prompts": {
    "narrative": "Describe this image in detail...",
    "technical": "Provide a technical analysis...",
    "brief": "Briefly describe this image...",
    "custom": "Your custom prompt here..."
  },
  
  "image_processing": {
    "max_image_size": 2048,
    "resize_mode": "contain",
    "quality": 95,
    "format": "JPEG"
  },
  
  "output_settings": {
    "include_metadata": true,
    "include_location": true,
    "location_prefix_format": "Location: {location}\n\n",
    "date_prefix_format": "Date: {date}\n\n"
  },
  
  "batch_processing": {
    "max_workers": 4,
    "continue_on_error": true,
    "save_failed_list": true
  }
}
```

### Key Settings Explained

#### `default_model`, `default_provider`, `default_prompt_style`
**NEW in v3.5.0:** These defaults are now properly respected!

These set the default values that will be used unless overridden by CLI arguments.

**Example:**
```json
{
  "default_model": "gemma3:latest",
  "default_provider": "ollama", 
  "default_prompt_style": "Orientation"
}
```

When you run:
```bash
idt workflow photos/ --config-image-describer c:\myconfigs\custom.json
```

The workflow will use `gemma3:latest` with the `Orientation` prompt style, and the output directory will be named accordingly:
```
wf_photos_20251101_120000_ollama_gemma3latest_Orientation
```

#### `prompts`
Define custom prompt templates for different description styles.

**Example:**
```json
{
  "prompts": {
    "detailed": "Provide a comprehensive description of this image including...",
    "accessibility": "Describe this image for someone who cannot see it...",
    "scientific": "Analyze this image from a scientific perspective..."
  }
}
```

Use with:
```bash
idt describe image.jpg --prompt-style detailed
```

#### `model_settings.temperature`
Controls AI randomness/creativity:
- `0.0` - Deterministic, consistent descriptions
- `0.7` - Balanced (default)
- `1.0` - More creative and varied

#### `image_processing.max_image_size`
Maximum dimension (width or height) before resizing. Larger images = slower processing.

**Recommendations:**
- `1024` - Fast, good for batch processing
- `2048` - Standard (default), good quality
- `4096` - High quality, slower

### Using Custom image_describer_config.json

```bash
# With idt workflow command
idt workflow photos/ --config-image-describer c:\myconfigs\detailed_descriptions.json

# With idt describe command
idt describe image.jpg --config-image-describer c:\myconfigs\scientific.json

# With ImageDescriber GUI
# 1. Launch ImageDescriber (c:\idt\idtimagedescriber.exe)
# 2. Click "Load Prompt Config" button
# 3. Browse to your custom config file
# 4. Config defaults (model, provider, prompt style) will be applied to dropdowns
```

**Important:** The ImageDescriber GUI now properly respects `default_model`, `default_provider`, and `default_prompt_style` when you load a config file!

---

## video_frame_extractor_config.json

Controls video frame extraction parameters.

### Location
- System default: `c:\idt\scripts\video_frame_extractor_config.json`
- Custom: Anywhere (use `--config-video` to specify)

### Complete Settings Reference

```json
{
  "extraction_settings": {
    "default_fps": 1.0,
    "output_format": "jpg",
    "output_quality": 95,
    "naming_pattern": "frame_{sequence:06d}.jpg"
  },
  
  "video_processing": {
    "extract_metadata": true,
    "preserve_aspect_ratio": true,
    "max_width": null,
    "max_height": null,
    "skip_first_seconds": 0,
    "skip_last_seconds": 0
  },
  
  "metadata_embedding": {
    "embed_gps": true,
    "embed_datetime": true,
    "embed_camera_info": true,
    "frame_timestamp_mode": "relative"
  },
  
  "output_settings": {
    "create_subdirectory": true,
    "subdirectory_pattern": "{video_name}_frames",
    "overwrite_existing": false
  }
}
```

### Key Settings Explained

#### `default_fps`
Frames per second to extract. Controls density of frame extraction.

**Examples:**
- `1.0` - One frame per second (default, good balance)
- `0.5` - One frame every 2 seconds (less dense)
- `2.0` - Two frames per second (more dense)
- `0.1` - One frame every 10 seconds (sparse sampling)

#### `extract_metadata` and `embed_gps`
**NEW in v3.5.0:** Video metadata embedding!

When `true`, IDT extracts GPS coordinates, recording date/time, and camera info from video files and embeds them into extracted frame EXIF data.

**Result:** Video frames have proper metadata just like photos, enabling location/date prefixes in descriptions.

#### `skip_first_seconds` / `skip_last_seconds`
Skip frames at the beginning or end of videos.

**Example:**
```json
{
  "skip_first_seconds": 5,
  "skip_last_seconds": 3
}
```

Useful for skipping:
- Camera shake at start/end
- Black frames
- Unwanted intro/outro

#### `naming_pattern`
How extracted frames are named.

**Pattern Variables:**
- `{sequence}` - Frame number (1, 2, 3...)
- `{sequence:06d}` - Zero-padded frame number (000001, 000002...)
- `{timestamp}` - Frame timestamp in seconds
- `{video_name}` - Original video filename

**Example:**
```json
"naming_pattern": "{video_name}_frame_{sequence:04d}.jpg"
```

Result: `vacation_frame_0001.jpg`, `vacation_frame_0002.jpg`...

### Using Custom video_frame_extractor_config.json

```bash
# With idt workflow command
idt workflow videos/ --config-video c:\myconfigs\sparse_extraction.json

# With idt extract-frames command
idt extract-frames video.mp4 --config-video c:\myconfigs\dense_extraction.json
```

---

## Using Custom Config Files

### Command-Line Usage

All IDT commands support custom config files through `--config-*` flags:

```bash
# idt workflow command (supports all three config types)
idt workflow photos/ \
  --config-workflow c:\myconfigs\workflow.json \
  --config-image-describer c:\myconfigs\descriptions.json \
  --config-video c:\myconfigs\video.json

# idt describe command (uses image_describer config)
idt describe photos/ --config-image-describer c:\myconfigs\detailed.json

# idt extract-frames command (uses video config)
idt extract-frames video.mp4 --config-video c:\myconfigs\extraction.json
```

### ImageDescriber GUI Usage

The ImageDescriber GUI application (`c:\idt\idtimagedescriber.exe`) supports loading custom config files:

1. Launch ImageDescriber
2. Click the **"Load Prompt Config"** button in the toolbar
3. Browse to your custom `image_describer_config.json` file
4. Click **"Open"**

**What Happens:**
- All prompts from the config are loaded into the prompt editor
- `default_model` is selected in the Model dropdown
- `default_provider` is selected in the Provider dropdown
- `default_prompt_style` is selected in the Prompt Style dropdown

**Note:** GUI changes made after loading are not saved back to the config file. The config file is read-only to the GUI.

### Creating Custom Config Files

#### Method 1: Copy and Modify System Defaults

```bash
# Copy system defaults to your custom location
copy c:\idt\scripts\image_describer_config.json c:\myconfigs\my_descriptions.json

# Edit the copy with your preferred text editor
notepad c:\myconfigs\my_descriptions.json
```

#### Method 2: Start from Minimal Template

Create a minimal config with just the settings you want to override:

**Minimal workflow_config.json:**
```json
{
  "workflow_settings": {
    "output_base_dir": "d:\\my_projects\\descriptions"
  }
}
```

**Minimal image_describer_config.json:**
```json
{
  "default_model": "gemma3:latest",
  "default_provider": "ollama",
  "default_prompt_style": "detailed",
  "prompts": {
    "detailed": "Describe this image in comprehensive detail..."
  }
}
```

IDT will use your settings and fall back to system defaults for anything not specified.

---

## Common Configuration Scenarios

### Scenario 1: Project-Specific Descriptions

**Goal:** Different projects need different AI models and description styles.

**Solution:** Create project-specific image_describer configs.

```bash
# Create configs
c:\projects\
├── nature\
│   └── nature_config.json      # Model: gemma3, Style: scientific
├── family\
│   └── family_config.json      # Model: moondream, Style: narrative
└── work\
    └── work_config.json        # Model: gpt-4o-mini, Style: technical

# Use them
cd c:\projects\nature
idt workflow photos\ --config-image-describer nature_config.json

cd c:\projects\family
idt workflow photos\ --config-image-describer family_config.json
```

### Scenario 2: Sparse Video Frame Extraction

**Goal:** Extract fewer frames from long videos to save time and disk space.

**Solution:** Create custom video config with lower FPS.

**sparse_video.json:**
```json
{
  "extraction_settings": {
    "default_fps": 0.2
  },
  "video_processing": {
    "skip_first_seconds": 5,
    "skip_last_seconds": 5
  }
}
```

**Usage:**
```bash
idt extract-frames longvideo.mp4 --config-video sparse_video.json
# Extracts 1 frame every 5 seconds, skips first/last 5 seconds
```

### Scenario 3: High-Quality Batch Processing

**Goal:** Process images with highest quality settings, multiple workers.

**Solution:** Custom image_describer config optimized for quality.

**highquality.json:**
```json
{
  "default_model": "gpt-4o-mini",
  "default_provider": "openai",
  "default_prompt_style": "detailed",
  "image_processing": {
    "max_image_size": 4096,
    "quality": 98
  },
  "batch_processing": {
    "max_workers": 8
  },
  "prompts": {
    "detailed": "Provide an extremely detailed and comprehensive description..."
  }
}
```

**Usage:**
```bash
idt workflow photos\ --config-image-describer highquality.json
```

### Scenario 4: Multiple AI Models for Comparison

**Goal:** Process same images with different AI models to compare outputs.

**Solution:** Create multiple configs, run workflows separately.

**moondream_config.json:**
```json
{
  "default_model": "moondream:latest",
  "default_provider": "ollama",
  "default_prompt_style": "narrative"
}
```

**gemma_config.json:**
```json
{
  "default_model": "gemma3:latest",
  "default_provider": "ollama",
  "default_prompt_style": "narrative"
}
```

**Usage:**
```bash
# Process with moondream
idt workflow photos\ --config-image-describer moondream_config.json --name moondream_test

# Process with gemma
idt workflow photos\ --config-image-describer gemma_config.json --name gemma_test

# Compare results in separate workflow directories
```

### Scenario 5: Accessible Descriptions with Geocoding

**Goal:** Generate descriptions optimized for screen readers with location context.

**Solution:** Custom config with accessibility-focused prompts and metadata enabled.

**accessible.json:**
```json
{
  "default_model": "gpt-4o-mini",
  "default_provider": "openai",
  "default_prompt_style": "accessible",
  "output_settings": {
    "include_metadata": true,
    "include_location": true,
    "location_prefix_format": "Location: {location}. ",
    "date_prefix_format": "Taken on {date}. "
  },
  "prompts": {
    "accessible": "Describe this image as if explaining it to someone who cannot see it. Be specific about spatial relationships, colors, and important details that convey the full context..."
  }
}
```

**Usage:**
```bash
idt workflow photos\ --config-image-describer accessible.json
# Results include location/date prefixes plus accessibility-focused descriptions
```

---

## Troubleshooting

### Config File Not Found

**Problem:** Error message about config file not being found.

**Solutions:**
1. Check the file path - use absolute paths with `--config-*` flags
2. Use forward slashes `/` or escaped backslashes `\\` in JSON
3. Verify the file exists: `dir c:\myconfigs\custom.json`

**Example - Correct paths:**
```bash
# Windows - use forward slashes or escaped backslashes
idt workflow photos/ --config-image-describer c:/myconfigs/custom.json
idt workflow photos/ --config-image-describer c:\\myconfigs\\custom.json
```

### Custom Config Settings Not Applied

**Problem:** Changed settings in custom config but they're not being used.

**Solutions:**
1. Check configuration priority - CLI args override config files
2. Verify JSON syntax - use a JSON validator
3. Check setting names - they must match exactly
4. Look for typos in field names

**Example - Priority issue:**
```bash
# This won't use config's default_model because CLI arg overrides
idt workflow photos/ --config-image-describer custom.json --model moondream
# Solution: Remove --model flag to use config default
idt workflow photos/ --config-image-describer custom.json
```

### IDT_CONFIG_DIR Environment Variable Conflicts

**Problem:** Error about "Invalid prompt style" or configs being loaded from unexpected locations (e.g., `C:\idt\scripts\`).

**Symptoms:**
- Log shows: `Using image_describer_config from C:\idt\scripts\image_describer_config.json (source=idt_config_dir)`
- Prompt styles or settings don't match your current config files
- Config from a different IDT installation is being used

**Root Cause:** The `IDT_CONFIG_DIR` environment variable is set and pointing to an old or different config directory. This takes **higher priority** than the executable's local configs.

**How to check:**
```bash
# Windows Command Prompt
echo %IDT_CONFIG_DIR%

# Windows PowerShell
$env:IDT_CONFIG_DIR

# macOS/Linux
echo $IDT_CONFIG_DIR
```

**How to fix:**

**Windows:**
```batch
# Option 1: Remove the environment variable (recommended)
setx IDT_CONFIG_DIR ""

# Option 2: Update it to point to the correct directory
setx IDT_CONFIG_DIR "C:\path\to\your\idt\installation"

# Option 3: Remove via System Properties
# Control Panel → System → Advanced → Environment Variables
# Find IDT_CONFIG_DIR and delete it
```

**macOS/Linux:**
```bash
# Remove from your shell profile (~/.zshrc, ~/.bash_profile, or ~/.bashrc)
# Delete or comment out line like: export IDT_CONFIG_DIR=/path/to/configs

# Then reload:
source ~/.zshrc  # or ~/.bash_profile
```

**After removing, restart your terminal/command prompt for changes to take effect.**

**When IDT_CONFIG_DIR is useful:** This variable is intended for shared config setups (e.g., team configs on a network drive). Most users should **not** set this variable.

---

### Invalid JSON Syntax

**Problem:** Error parsing config file.

**Common issues:**
- Missing commas between fields
- Trailing commas at end of objects/arrays
- Missing quotes around strings
- Unescaped backslashes in paths

**Example - Invalid:**
```json
{
  "default_model": "gemma3:latest"
  "default_provider": "ollama",    // Missing comma above
  "prompts": {
    "test": "description",         // Trailing comma below
  },
}
```

**Example - Valid:**
```json
{
  "default_model": "gemma3:latest",
  "default_provider": "ollama",
  "prompts": {
    "test": "description"
  }
}
```

**Solution:** Use a JSON validator like [jsonlint.com](https://jsonlint.com/) to check syntax.

### Config Changes Not Reflected in GUI

**Problem:** Modified config file but ImageDescriber GUI still shows old values.

**Solution:** The GUI caches config on startup. Restart ImageDescriber to reload:
1. Close ImageDescriber completely
2. Modify your config file
3. Relaunch ImageDescriber
4. Click "Load Prompt Config" and select your config

### Model Not Found

**Problem:** Error about model not being found after loading config.

**Solutions:**
1. Verify the model name is correct (check with `ollama list` for Ollama models)
2. Ensure the AI provider is running (e.g., Ollama service)
3. Check API keys for cloud providers (OpenAI, Anthropic)
4. Verify `default_provider` matches the model's provider

**Example:**
```json
{
  "default_model": "gemma3:latest",    // Model name
  "default_provider": "ollama"         // Must match model's provider
}
```

### Workflow Directory Named Incorrectly

**Problem:** Workflow directory name doesn't reflect custom config model.

**Cause:** This was a bug in versions before v3.5.0.

**Solution:** Update to v3.5.0 or later. The workflow directory naming now properly uses custom config defaults.

**Before (broken):**
```
wf_photos_20251101_120000_ollama_moondreamlatest_narrative
```

**After (fixed):**
```
wf_photos_20251101_120000_ollama_gemma3latest_Orientation
```

---

## Best Practices

### 1. Use Version Control for Config Files

Store your custom configs in git or another version control system:

```bash
c:\myconfigs\
├── .git\
├── README.md              # Document what each config is for
├── default.json
├── high_quality.json
└── quick_test.json
```

### 2. Document Your Custom Configs

Add comments using a separate README file (JSON doesn't support comments):

```markdown
# My IDT Configs

- `default.json` - General purpose, moondream model
- `high_quality.json` - GPT-4 with detailed prompts, for final outputs
- `quick_test.json` - Fast processing for testing
```

### 3. Use Descriptive Config Names

```bash
# Good
scientific_analysis_config.json
family_photos_narrative.json
web_download_settings.json

# Bad
config1.json
test.json
new.json
```

### 4. Start Minimal, Add as Needed

Begin with a minimal config that only overrides what you need:

```json
{
  "default_model": "gemma3:latest"
}
```

Add more settings as your requirements grow.

### 5. Test Config Changes

After modifying a config, test it with a small sample:

```bash
# Test with just a few images first
idt describe test_image.jpg --config-image-describer newconfig.json

# If successful, run on full batch
idt workflow photos\ --config-image-describer newconfig.json
```

### 6. Keep Backups of Working Configs

When you have a config that works well, save a backup:

```bash
copy working_config.json working_config_backup_20251101.json
```

### 7. Use Absolute Paths in Configs

For `output_base_dir` and file paths within configs, use absolute paths:

```json
{
  "workflow_settings": {
    "output_base_dir": "d:\\projects\\idt_outputs"
  }
}
```

This prevents confusion about relative path context.

---

## Additional Resources

- **[CLI_REFERENCE.md](CLI_REFERENCE.md)** - Complete command-line reference with all `--config-*` options
- **[USER_GUIDE.md](USER_GUIDE.md)** - General IDT usage guide
- **[PROMPT_WRITING_GUIDE.md](PROMPT_WRITING_GUIDE.md)** - How to write effective prompts for the `prompts` section
- **[WHATS_NEW_v3.5.0.md](WHATS_NEW_v3.5.0.md)** - Latest features including config priority fixes

---

## Summary

- IDT uses **three config files**: workflow, image_describer, and video_frame_extractor
- **Priority order**: CLI args > Custom config > Workflow config > System defaults
- Use `--config-workflow`, `--config-image-describer`, and `--config-video` flags to specify custom configs
- ImageDescriber GUI supports loading custom configs via "Load Prompt Config" button
- Custom configs can be minimal - only override what you need to change
- Store configs in version control and document their purposes
- Test config changes with small samples before full batch processing

---

**Need Help?**
- Check the [CLI_REFERENCE.md](CLI_REFERENCE.md) for command-line syntax
- See [USER_GUIDE.md](USER_GUIDE.md) for general usage
- Review [WHATS_NEW_v3.5.0.md](WHATS_NEW_v3.5.0.md) for latest features

*Last updated: November 11, 2025 for IDT v3.5.0*
