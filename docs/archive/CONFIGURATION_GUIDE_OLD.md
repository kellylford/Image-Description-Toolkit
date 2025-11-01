# Configuration Guide

## Overview

IDT uses three main configuration files to control different aspects of the workflow. Understanding these files allows you to customize IDT's behavior, create specialized workflows, and maintain different configuration profiles for different use cases.

**Configuration Files:**
1. **`workflow_config.json`** - Orchestrates the entire workflow pipeline
2. **`image_describer_config.json`** - Controls AI models, prompts, and description settings
3. **`video_frame_extractor_config.json`** - Manages video frame extraction settings

**Default Location:** `scripts/` directory (relative to IDT installation)

---

## Table of Contents

1. [Using Custom Configuration Files](#using-custom-configuration-files)
2. [workflow_config.json](#workflow_configjson)
3. [image_describer_config.json](#image_describer_configjson)
4. [video_frame_extractor_config.json](#video_frame_extractor_configjson)
5. [Common Use Cases](#common-use-cases)
6. [Creating Custom Prompts](#creating-custom-prompts)
7. [Configuration Search Order](#configuration-search-order)
8. [Best Practices](#best-practices)

---

## Using Custom Configuration Files

### Command-Line Option

All IDT commands support the `--config` (or `-c`) option to specify a custom configuration file:

```bash
# Use custom workflow config
idt workflow photos --config my_workflow_config.json

# Use custom image describer config (workflow will use it)
idt workflow photos --config my_prompts_config.json

# Use custom video extractor config (via workflow)
idt workflow videos --config my_extraction_config.json
```

### Environment Variables

You can also set configuration paths via environment variables:

```bash
# Windows (PowerShell)
$env:IDT_WORKFLOW_CONFIG = "C:\MyConfigs\custom_workflow.json"
$env:IDT_IMAGE_DESCRIBER_CONFIG = "C:\MyConfigs\custom_prompts.json"
$env:IDT_VIDEO_FRAME_EXTRACTOR_CONFIG = "C:\MyConfigs\custom_extraction.json"

# Windows (CMD)
set IDT_WORKFLOW_CONFIG=C:\MyConfigs\custom_workflow.json
set IDT_IMAGE_DESCRIBER_CONFIG=C:\MyConfigs\custom_prompts.json
set IDT_VIDEO_FRAME_EXTRACTOR_CONFIG=C:\MyConfigs\custom_extraction.json

# Linux/Mac
export IDT_WORKFLOW_CONFIG="/path/to/custom_workflow.json"
export IDT_IMAGE_DESCRIBER_CONFIG="/path/to/custom_prompts.json"
export IDT_VIDEO_FRAME_EXTRACTOR_CONFIG="/path/to/custom_extraction.json"
```

---

## workflow_config.json

**Purpose:** Controls the overall workflow orchestration, including which steps run, output directories, and step-specific settings.

### Key Sections

#### 1. Workflow Steps
```json
{
  "workflow": {
    "base_output_dir": "workflow_output",
    "preserve_structure": true,
    "cleanup_intermediate": false,
    "steps": {
      "video_extraction": {
        "enabled": true,
        "output_subdir": "extracted_frames",
        "config_file": "video_frame_extractor_config.json"
      },
      "image_conversion": {
        "enabled": true,
        "output_subdir": "converted_images",
        "quality": 95,
        "keep_metadata": true
      },
      "image_description": {
        "enabled": true,
        "output_subdir": "descriptions",
        "config_file": "image_describer_config.json",
        "model": null,
        "prompt_style": null
      },
      "html_generation": {
        "enabled": true,
        "output_subdir": "html_reports",
        "include_details": false,
        "title": "Image Analysis Report"
      }
    }
  }
}
```

#### 2. File Patterns
```json
{
  "file_patterns": {
    "videos": [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v"],
    "images": [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"],
    "heic": [".heic", ".heif"],
    "descriptions": ["image_descriptions.txt"]
  }
}
```

#### 3. Logging
```json
{
  "logging": {
    "level": "INFO",
    "log_to_file": true,
    "log_filename": "workflow_{timestamp}.log"
  }
}
```

### Common Customizations

**Example: Quick Preview Config** (`workflow_quick.json`)
```json
{
  "workflow": {
    "base_output_dir": "quick_preview",
    "steps": {
      "video_extraction": {
        "enabled": true,
        "config_file": "video_quick_extract.json"
      },
      "image_conversion": {
        "enabled": true,
        "quality": 85
      },
      "image_description": {
        "enabled": true,
        "config_file": "image_describer_concise.json"
      },
      "html_generation": {
        "enabled": false
      }
    }
  }
}
```

**Usage:**
```bash
idt workflow videos --config workflow_quick.json
```

---

## image_describer_config.json

**Purpose:** Controls AI model selection, prompt styles, metadata extraction, and description generation settings.

### Key Sections

#### 1. Model Settings
```json
{
  "default_model": "moondream:latest",
  "model_settings": {
    "model": "moondream",
    "temperature": 0.1,
    "num_predict": 600,
    "top_k": 40,
    "top_p": 0.9,
    "repeat_penalty": 1.3
  }
}
```

**Settings Explained:**
- **`temperature`**: Controls randomness (0.0-1.0). Lower = more consistent, higher = more creative. Recommended: 0.1-0.3
- **`num_predict`**: Maximum tokens to generate. Higher = longer descriptions. Recommended: 400-800
- **`top_k`**: Number of top tokens to consider. Lower = more focused. Recommended: 40
- **`top_p`**: Cumulative probability cutoff. Lower = more focused. Recommended: 0.9
- **`repeat_penalty`**: Penalty for repeating tokens. Higher = less repetition. Recommended: 1.1-1.3

#### 2. Prompt Styles
```json
{
  "default_prompt_style": "narrative",
  "prompt_variations": {
    "narrative": "Provide a narrative description including objects, colors and detail. Avoid interpretation, just describe.",
    "detailed": "Describe this image in detail, including:\n- Main subjects/objects\n- Setting/environment\n- Key colors and lighting\n- Notable activities or composition",
    "concise": "Describe this image concisely...",
    "artistic": "Analyze this image from an artistic perspective...",
    "technical": "Provide a technical analysis...",
    "colorful": "Give me a rich, vivid description emphasizing colors..."
  }
}
```

#### 3. Metadata Settings
```json
{
  "metadata": {
    "enabled": true,
    "include_location_prefix": true,
    "geocoding": {
      "enabled": true,
      "user_agent": "IDT/3.5 (+https://github.com/kellylford/Image-Description-Toolkit)",
      "delay_seconds": 1.0,
      "cache_file": "geocode_cache.json"
    }
  }
}
```

#### 4. Processing Options
```json
{
  "processing_options": {
    "default_max_image_size": 1024,
    "default_batch_delay": 2.0,
    "default_compression": true,
    "extract_metadata": true,
    "chronological_sorting": {
      "enabled_by_default": true
    }
  }
}
```

---

## video_frame_extractor_config.json

**Purpose:** Controls how frames are extracted from videos, including timing, quality, and naming.

### Key Settings

#### 1. Extraction Mode
```json
{
  "extraction_mode": "time_interval",
  "time_interval_seconds": 5.0,
  "scene_change_threshold": 30.0,
  "min_scene_duration_seconds": 1.0
}
```

**Modes:**
- **`time_interval`**: Extract frames at regular intervals (e.g., every 5 seconds)
- **`scene_change`**: Extract frames only when scene changes significantly

#### 2. Output Settings
```json
{
  "output_directory": "extracted_frames",
  "preserve_directory_structure": false,
  "image_quality": 95,
  "resize_width": null,
  "resize_height": null
}
```

#### 3. Frame Naming
```json
{
  "frame_naming": {
    "format": "{video_name}_{timestamp:.2f}s.jpg",
    "description": "Frames are automatically named using the source video filename and timestamp"
  },
  "frame_prefix": "frame"
}
```

#### 4. Advanced Options
```json
{
  "start_time_seconds": 0,
  "end_time_seconds": null,
  "max_frames_per_video": null,
  "skip_existing": false,
  "timestamp_preservation": {
    "enabled": true,
    "description": "Extracted frames inherit modification time from source video"
  }
}
```

---

## Common Use Cases

### 1. Multiple Prompt Style Configurations

**Scenario:** You want different prompt configs for different types of photos.

**Setup:**

**`image_describer_vacation.json`** - For vacation photos
```json
{
  "default_model": "llava:latest",
  "default_prompt_style": "narrative",
  "prompt_variations": {
    "narrative": "Describe this vacation photo including location details, activities, people (without identifying them), atmosphere, and memorable visual elements.",
    "artistic": "Capture the artistic and emotional qualities of this travel moment..."
  },
  "model_settings": {
    "temperature": 0.2,
    "num_predict": 800
  }
}
```

**`image_describer_technical.json`** - For technical documentation
```json
{
  "default_model": "llama3.2-vision:latest",
  "default_prompt_style": "technical",
  "prompt_variations": {
    "technical": "Provide a precise technical description focusing on equipment, settings, composition, and technical quality.",
    "detailed": "Document every technical aspect visible in this image..."
  },
  "model_settings": {
    "temperature": 0.1,
    "num_predict": 600
  }
}
```

**Usage:**
```bash
# Vacation photos
idt workflow vacation_2024 --config image_describer_vacation.json

# Technical documentation
idt workflow equipment_photos --config image_describer_technical.json
```

### 2. High-Quality vs. Quick Preview

**High-Quality Config** (`workflow_hq.json`)
```json
{
  "workflow": {
    "steps": {
      "video_extraction": {
        "enabled": true,
        "config_file": "video_hq_extract.json"
      },
      "image_description": {
        "enabled": true,
        "config_file": "image_describer_detailed.json",
        "model": "llava:34b"
      }
    }
  }
}
```

**Quick Preview Config** (`workflow_quick.json`)
```json
{
  "workflow": {
    "steps": {
      "video_extraction": {
        "enabled": true,
        "config_file": "video_quick_extract.json"
      },
      "image_description": {
        "enabled": true,
        "config_file": "image_describer_concise.json",
        "model": "moondream"
      }
    }
  }
}
```

**Video Extraction Configs:**

**`video_hq_extract.json`** - High quality, more frames
```json
{
  "extraction_mode": "time_interval",
  "time_interval_seconds": 2.0,
  "image_quality": 95,
  "resize_width": null
}
```

**`video_quick_extract.json`** - Quick preview, fewer frames
```json
{
  "extraction_mode": "time_interval",
  "time_interval_seconds": 10.0,
  "image_quality": 85,
  "resize_width": 1024
}
```

**Usage:**
```bash
# High quality (slower, detailed)
idt workflow important_project --config workflow_hq.json

# Quick preview (faster, overview)
idt workflow quick_check --config workflow_quick.json
```

### 3. Cloud AI vs. Local AI

**`workflow_cloud.json`** - Using GPT-4 Vision
```json
{
  "workflow": {
    "steps": {
      "image_description": {
        "enabled": true,
        "config_file": "image_describer_gpt4.json"
      }
    }
  }
}
```

**`image_describer_gpt4.json`**
```json
{
  "default_model": "gpt-4o",
  "default_prompt_style": "detailed",
  "prompt_variations": {
    "detailed": "Provide a comprehensive, highly detailed description of this image...",
    "narrative": "Create a rich narrative description..."
  },
  "model_settings": {
    "temperature": 0.3,
    "num_predict": 1000
  }
}
```

**Usage:**
```bash
# Local Ollama (default)
idt workflow photos

# Cloud GPT-4 Vision
idt workflow photos --config workflow_cloud.json --provider openai --api-key-file openai_key.txt
```

---

## Creating Custom Prompts

### Scenario: Custom Prompts for Your Workflow

**Goal:** Create your own custom prompts and have IDT and all tools use them throughout the system.

### Step-by-Step Instructions

#### Step 1: Copy the Default Config

```bash
# Windows
copy scripts\image_describer_config.json scripts\my_custom_prompts.json

# Linux/Mac
cp scripts/image_describer_config.json scripts/my_custom_prompts.json
```

#### Step 2: Edit Your Custom Config

Open `scripts/my_custom_prompts.json` and modify the `prompt_variations` section:

```json
{
  "default_model": "llava:latest",
  "default_prompt_style": "my_style",
  "prompt_variations": {
    "my_style": "Describe this image with focus on [YOUR CUSTOM INSTRUCTIONS]",
    "product_photo": "Analyze this product photo: describe the item, its features, condition, colors, and any text or branding visible. Be specific and objective.",
    "nature_photo": "Describe this nature photograph: identify flora and fauna if possible, describe the landscape, lighting conditions, season indicators, and overall atmosphere.",
    "family_photo": "Describe this family photo: note the setting, activities, expressions (without identifying individuals), clothing era if relevant, and overall mood. Preserve privacy.",
    "architecture": "Analyze this architectural image: describe the building style, materials, structural elements, historical period if evident, surrounding context, and notable design features.",
    "food_photo": "Describe this food image: identify dishes, presentation style, ingredients visible, plating, colors, setting, and overall appeal."
  },
  "model_settings": {
    "temperature": 0.2,
    "num_predict": 800,
    "top_k": 40,
    "top_p": 0.9,
    "repeat_penalty": 1.2
  }
}
```

#### Step 3: Use Your Custom Prompts System-Wide

**Option A: Use with Workflow Command**
```bash
# Specify custom config and prompt style
idt workflow photos --config my_custom_prompts.json --prompt-style my_style

# The workflow will use your custom prompts for all images
```

**Option B: Update Workflow Config to Reference It**

Edit `workflow_config.json` (or create `my_workflow.json`):
```json
{
  "workflow": {
    "steps": {
      "image_description": {
        "enabled": true,
        "config_file": "my_custom_prompts.json",
        "model": "llava:latest",
        "prompt_style": "my_style"
      }
    }
  }
}
```

Then use:
```bash
idt workflow photos --config my_workflow.json
```

**Option C: Set Environment Variable (System-Wide Default)**
```bash
# Windows (PowerShell) - Persists for session
$env:IDT_IMAGE_DESCRIBER_CONFIG = "C:\path\to\scripts\my_custom_prompts.json"

# Windows (Set permanently)
setx IDT_IMAGE_DESCRIBER_CONFIG "C:\path\to\scripts\my_custom_prompts.json"

# Linux/Mac (Add to ~/.bashrc or ~/.zshrc)
export IDT_IMAGE_DESCRIBER_CONFIG="/path/to/scripts/my_custom_prompts.json"
```

Now ALL IDT commands will use your custom prompts by default:
```bash
# Uses your custom config automatically
idt workflow photos

# Uses your custom config with specific style
idt workflow photos --prompt-style product_photo

# Image describer GUI will also use your custom prompts
idt imagedescriber

# Viewer will show descriptions generated with your prompts
idt viewer
```

#### Step 4: Test Your Custom Prompts

```bash
# Run a small test batch first
idt workflow test_photos --config my_custom_prompts.json --prompt-style my_style --max-files 5

# View results
idt viewer

# If satisfied, run full batch
idt workflow all_photos --config my_custom_prompts.json
```

#### Step 5: Maintain Multiple Prompt Profiles

Create multiple specialized configs:

```
scripts/
├── image_describer_config.json          # Default/original
├── prompts_product_photos.json          # E-commerce listings
├── prompts_nature_photos.json           # Wildlife/landscapes
├── prompts_family_archive.json          # Personal photo collections
├── prompts_technical_docs.json          # Documentation/screenshots
└── prompts_artistic_analysis.json       # Art critique/analysis
```

**Usage:**
```bash
# Product photos
idt workflow products --config prompts_product_photos.json

# Nature photos
idt workflow wildlife --config prompts_nature_photos.json

# Family archive
idt workflow family_1990s --config prompts_family_archive.json
```

### Advanced: Custom Prompts with Model-Specific Tuning

Different models may respond better to different prompt styles. Create model-specific configs:

**`prompts_moondream_optimized.json`**
```json
{
  "default_model": "moondream:latest",
  "default_prompt_style": "optimized",
  "prompt_variations": {
    "optimized": "Describe the image. Be specific and detailed."
  },
  "model_settings": {
    "temperature": 0.1,
    "num_predict": 400,
    "repeat_penalty": 1.3
  }
}
```

**`prompts_llava_optimized.json`**
```json
{
  "default_model": "llava:latest",
  "default_prompt_style": "optimized",
  "prompt_variations": {
    "optimized": "Provide a comprehensive description of this image, including all notable objects, colors, composition, and context."
  },
  "model_settings": {
    "temperature": 0.2,
    "num_predict": 800,
    "repeat_penalty": 1.1
  }
}
```

---

## Configuration Search Order

When IDT looks for configuration files, it searches in this order:

1. **Explicit `--config` path** - Highest priority
   ```bash
   idt workflow photos --config /path/to/custom.json
   ```

2. **Environment variable** (file-specific)
   ```bash
   $env:IDT_IMAGE_DESCRIBER_CONFIG
   $env:IDT_WORKFLOW_CONFIG
   $env:IDT_VIDEO_FRAME_EXTRACTOR_CONFIG
   ```

3. **Environment variable** (directory + filename)
   ```bash
   $env:IDT_CONFIG_DIR = "C:\MyConfigs"
   # Looks for: C:\MyConfigs\workflow_config.json
   ```

4. **Frozen executable directory** (if running as .exe)
   - `<exe_dir>/scripts/<config_file>`
   - `<exe_dir>/<config_file>`

5. **Current working directory**
   - `./workflow_config.json`

6. **Bundled script directory** - Fallback
   - `scripts/workflow_config.json`

**Example Resolution:**
```bash
# If you run:
cd C:\Projects
idt workflow photos --config my_config.json

# IDT searches:
1. C:\Projects\my_config.json (explicit path, found!)
2. (stops searching)

# If you run:
$env:IDT_WORKFLOW_CONFIG = "D:\Configs\special.json"
idt workflow photos

# IDT searches:
1. (no --config specified)
2. D:\Configs\special.json (env var, found!)
3. (stops searching)
```

---

## Best Practices

### 1. Version Control Your Configs

```bash
# Create a configs directory
mkdir custom_configs
cd custom_configs

# Initialize git
git init

# Add your configs
cp ../scripts/image_describer_config.json ./describer_baseline.json
# Edit describer_baseline.json...
git add describer_baseline.json
git commit -m "Initial baseline config"
```

### 2. Naming Conventions

Use descriptive names that indicate purpose:

```
config_ollama_moondream.json          # Model-specific
config_product_photos.json            # Use-case specific
config_high_quality.json              # Quality level
config_test_environment.json          # Environment specific
config_batch_processing.json          # Workflow type
```

### 3. Document Your Custom Configs

Add a `documentation` section to your custom configs:

```json
{
  "documentation": {
    "purpose": "Optimized for product photography with detailed descriptions",
    "created": "2025-10-30",
    "author": "Your Name",
    "model_requirements": "Requires llava:13b or larger",
    "usage": "idt workflow products --config config_product_photos.json"
  },
  "default_model": "llava:13b",
  "prompt_variations": {
    ...
  }
}
```

### 4. Test Before Production

Always test new configs on a small batch:

```bash
# Test with just 5 images
idt workflow test_batch --config new_config.json --max-files 5

# Review results
idt viewer

# If good, run full batch
idt workflow full_batch --config new_config.json
```

### 5. Keep Backups

Before modifying production configs:

```bash
# Backup before changes
copy scripts\workflow_config.json scripts\workflow_config.json.backup

# Or use timestamped backups
copy scripts\workflow_config.json scripts\workflow_config_20251030.json
```

### 6. Use Config Validation

IDT will report config errors. Test your config:

```bash
# Dry run to validate config without processing
idt workflow test --config my_config.json --dry-run
```

### 7. Prompt Engineering Tips

When creating custom prompts:

- **Be specific** about what you want described
- **Use consistent structure** across prompt variations
- **Test with different models** - prompts perform differently
- **Iterate based on results** - refine prompts based on output quality
- **Keep temperature low** (0.1-0.3) for consistent, factual descriptions
- **Increase num_predict** if descriptions are getting cut off
- **Use examples** in prompts for complex requirements

**Example: Structured Prompt**
```json
{
  "structured_description": "Analyze this image using the following structure:\n\n1. SUBJECT: Identify the main subject(s)\n2. SETTING: Describe the environment/location\n3. COLORS: Note dominant colors and color relationships\n4. LIGHTING: Describe lighting conditions and quality\n5. COMPOSITION: Comment on framing and arrangement\n6. DETAILS: Note any significant details or text\n7. MOOD: Describe the overall atmosphere\n\nBe specific and objective."
}
```

---

## Troubleshooting

### Config File Not Found

**Error:** `Config file not found: my_config.json`

**Solution:**
- Use absolute paths: `--config C:\full\path\to\config.json`
- Or place config in current directory
- Check environment variables: `echo $env:IDT_IMAGE_DESCRIBER_CONFIG`

### Prompt Style Not Found

**Error:** `Prompt style 'my_style' not found`

**Solution:**
- Check spelling in `prompt_variations` section
- Ensure prompt style key exists in config file
- Verify correct config file is being loaded (use `--verbose` to see paths)

### Model Not Available

**Error:** `Model 'llava:13b' not found`

**Solution:**
```bash
# Install the model first
ollama pull llava:13b

# Verify installation
ollama list

# Then run workflow
idt workflow photos --config my_config.json
```

### Config Syntax Errors

**Error:** `JSON decode error`

**Solution:**
- Validate JSON syntax: https://jsonlint.com/
- Check for missing commas, quotes, brackets
- Ensure no trailing commas in last array/object elements
- Use proper escape sequences for special characters

---

## Quick Reference

### Essential Commands

```bash
# Use custom workflow config
idt workflow photos --config my_workflow.json

# Use custom prompts
idt workflow photos --config my_prompts.json --prompt-style my_style

# Set default config via environment
$env:IDT_IMAGE_DESCRIBER_CONFIG = "C:\path\to\my_prompts.json"

# View current configuration being used (verbose mode)
idt workflow photos --verbose --dry-run

# Test config without processing
idt workflow test --config new_config.json --dry-run

# List available prompt styles
idt prompt-list

# List available models
idt check-models
```

### File Locations

```
Image-Description-Toolkit/
├── scripts/
│   ├── workflow_config.json                    # Default workflow config
│   ├── image_describer_config.json             # Default prompts/model config
│   ├── video_frame_extractor_config.json       # Default video extraction config
│   └── (your custom configs here)
└── docs/
    └── CONFIGURATION_GUIDE.md                   # This file
```

---

## Further Reading

- **[USER_GUIDE.md](USER_GUIDE.md)** - Complete user guide with workflow examples
- **[CLI_REFERENCE.md](CLI_REFERENCE.md)** - Full command-line reference
- **[VIDEO_METADATA_EMBEDDING.md](VIDEO_METADATA_EMBEDDING.md)** - Video metadata configuration
- **[TESTING.md](TESTING.md)** - Testing procedures and validation

---

## Support

For issues or questions:
- Check existing documentation in `docs/`
- Review default config files in `scripts/`
- Open an issue on GitHub: https://github.com/kellylford/Image-Description-Toolkit

---

**Last Updated:** October 30, 2025  
**Version:** 3.5.0-beta
