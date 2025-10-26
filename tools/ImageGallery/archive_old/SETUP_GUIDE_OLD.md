# Image Gallery Setup Guide

Complete step-by-step instructions for creating and deploying the IDT Image Gallery.

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Step 1: Gather Image Descriptions](#step-1-gather-image-descriptions)
4. [Step 2: Generate Gallery Data Files](#step-2-generate-gallery-data-files)
5. [Step 3: Deploy the Gallery](#step-3-deploy-the-gallery)
6. [Step 4: Cleanup and Maintenance](#step-4-cleanup-and-maintenance)
7. [Troubleshooting](#troubleshooting)

---

## Overview

The Image Gallery is a web-based demonstration of IDT's capabilities, showing how different AI models and prompts generate descriptions for the same images. The gallery allows visitors to:
- Browse images with accessible alt text
- Compare AI descriptions side-by-side
- Explore different prompt styles (narrative, colorful, technical, detailed)
- See how different providers (Claude, OpenAI, Ollama) describe the same image

**Architecture:**
- Static HTML/CSS/JavaScript (no server required)
- JSON data files for descriptions and metadata
- Image files served locally or from CDN

---

## Prerequisites

### Required Software
1. **IDT installed** at `c:\idt\` (or adjust paths in scripts)
2. **Python 3.8+** (for data processing scripts)
3. **API Keys configured** (for cloud providers):
   - Claude API key (optional): Use `setup_claude_key.bat`
   - OpenAI API key (optional): Use `setup_openai_key.bat`
4. **Ollama installed** (optional, for local models):
   - Download from https://ollama.ai
   - Pull desired models (see below)

### Optional Ollama Models
If using Ollama, pull the models you want:
```bash
ollama pull qwen3-vl:235b-cloud
ollama pull llava:latest
ollama pull gemma3:latest
ollama pull moondream:latest
ollama pull granite3.2-vision:latest
```

---

## Step 1: Gather Image Descriptions

### 1.1 Prepare Your Images

**Location:** Place 25 images in a directory (e.g., `c:\idt\images\`)

**Image Requirements:**
- Supported formats: JPG, JPEG, PNG, GIF, WEBP, BMP
- Reasonable file sizes (< 10MB recommended)
- Diverse subjects for interesting comparisons

**Example:**
```
c:\idt\images\
  ├── image001.jpg
  ├── image002.jpg
  ├── ...
  └── image025.jpg
```

### 1.2 Run Comprehensive Data Collection

**Use the automated script** to generate descriptions for all provider/model/prompt combinations:

```batch
cd c:\Users\kelly\GitHub\Image-Description-Toolkit\tools\ImageGallery
generate_all_gallery_data.bat c:\idt\images
```

**Important:** The script uses a hardcoded workflow name: **`25imagetest`**. This name is required for the consolidation script to find and process your workflows correctly. Do not modify the workflow name in the batch file unless you also update the consolidation script.

**What this does:**
- Runs **40 workflows** total:
  - 3 Claude models × 4 prompts = 12 workflows
  - 2 OpenAI models × 4 prompts = 8 workflows
  - 5 Ollama models × 4 prompts = 20 workflows
- Each workflow processes all 25 images
- Total: **1,000 descriptions** (40 workflows × 25 images)
- Saves results in `Descriptions/` subdirectories
- All workflows use the name **`25imagetest`** for consistency

**Time estimate:** 30 minutes to several hours depending on:
- Which providers you use (Ollama is faster, Claude/OpenAI are slower due to rate limits)
- Your API plan limits
- Image complexity

**Output structure:**
```
Descriptions/
  ├── wf_25imagetest_claude_3-5-haiku-20241022_narrative_YYYYMMDD_HHMMSS/
  ├── wf_25imagetest_claude_3-5-haiku-20241022_colorful_YYYYMMDD_HHMMSS/
  ├── wf_25imagetest_ollama_llava_narrative_YYYYMMDD_HHMMSS/
  └── ... (40 total workflow directories)
```

Each workflow directory contains:
- `log_image_describer.txt` - Processing log
- `workflow_summary.json` - Workflow metadata
- `descriptions.json` - The actual descriptions

---

## Step 2: Generate Gallery Data Files

### 2.1 Consolidate Data into JSON Format

**Purpose:** Convert workflow data into a format the gallery web page can use.

**Run the consolidation script:**
```batch
cd c:\Users\kelly\GitHub\Image-Description-Toolkit\tools\ImageGallery
python consolidate_gallery_data.py
```

**What this does:**
- Scans all workflow directories in `Descriptions/`
- Extracts descriptions and metadata
- Creates JSON files organized by provider, model, and prompt
- Generates `index.json` with available configurations
- Saves everything to `jsondata/` directory

**Output structure:**
```
jsondata/
  ├── index.json                                      # Master configuration file
  ├── claude_3-5-haiku-20241022_narrative.json        # Descriptions for this config
  ├── claude_3-5-haiku-20241022_colorful.json
  ├── ollama_llava_narrative.json
  └── ... (40 JSON files, one per provider/model/prompt combination)
```

**Each JSON file contains:**
```json
{
  "provider": "claude",
  "model": "claude-3-5-haiku-20241022",
  "prompt_style": "narrative",
  "total_images": 25,
  "images": {
    "image001.jpg": {
      "description": "Full AI-generated description...",
      "alt_text": "Concise alt text...",
      "photo_date": "2024-10-20T15:30:00",
      "camera": "Canon EOS R5",
      "timestamp": "2024-10-24T09:15:23"
    },
    ...
  }
}
```

### 2.2 Verify the Data

**Check that files were created:**
```batch
dir jsondata
```

You should see:
- 1 `index.json` file
- 40 JSON files (one per provider/model/prompt combination)

**Verify index.json has all configurations:**
```batch
type jsondata\index.json
```

Should show all providers, models, and prompts available.

---

## Step 3: Deploy the Gallery

### 3.1 Required Files

**The gallery needs these files:**

```
ImageGallery/
  ├── index.html              # Main gallery page
  ├── images/                 # Your image files
  │   ├── image001.jpg
  │   ├── image002.jpg
  │   └── ...
  └── jsondata/               # Description data
      ├── index.json
      ├── claude_*.json
      ├── openai_*.json
      └── ollama_*.json
```

### 3.2 Copy Images to Gallery Directory

```batch
cd c:\Users\kelly\GitHub\Image-Description-Toolkit\tools\ImageGallery

REM Create images directory if it doesn't exist
mkdir images

REM Copy your images
copy c:\idt\images\*.jpg images\
copy c:\idt\images\*.png images\
```

### 3.3 Test Locally

**Open the gallery in a browser:**
```batch
REM Open directly in default browser
start index.html
```

**OR use Python's built-in web server:**
```batch
cd c:\Users\kelly\GitHub\Image-Description-Toolkit\tools\ImageGallery
python -m http.server 8000
```
Then open: http://localhost:8000

**What to test:**
- ✅ Images load in the image browser
- ✅ Alt text displays for each image
- ✅ Description Explorer loads
- ✅ Comparison modes work (All Prompts / Same Prompt)
- ✅ Provider/model selectors populate correctly
- ✅ Prompt text displays when "Show Prompt Text" is clicked

### 3.4 Deploy to Web Server (Optional)

**Option A: GitHub Pages**
1. Commit the ImageGallery folder to your repository
2. Enable GitHub Pages in repository settings
3. Set source to main branch, /tools/ImageGallery folder
4. Access at: https://yourusername.github.io/Image-Description-Toolkit/tools/ImageGallery/

**Option B: Static Hosting**
Upload these files to any static web host:
- index.html
- images/ directory
- jsondata/ directory

**Hosts that work well:**
- GitHub Pages (free)
- Netlify (free tier)
- Vercel (free tier)
- AWS S3 + CloudFront
- Any web server with static file hosting

---

## Step 4: Cleanup and Maintenance

### 4.1 What Can Be Deleted

After successfully running `consolidate_gallery_data.py`, you have two copies of your description data:

1. **Workflow directories** in `Descriptions/` (44+ directories)
2. **JSON files** in `jsondata/` (41 files)

**The gallery ONLY needs the `jsondata/` files.** The workflow directories are only needed for:
- Re-running consolidation if you change the script
- Exporting to CSV for analysis (using `export_analysis_data.py`)
- Debugging or auditing the original workflow runs

### 4.2 Safe Cleanup Process

**If you're confident everything works:**

```batch
REM 1. Test the gallery thoroughly first!
REM 2. Optional: Export to CSV for archival records
python export_analysis_data.py --descriptions-dir Descriptions --output-dir jsondata

REM 3. Archive workflow directories (optional)
mkdir archive
move Descriptions archive\Descriptions_backup_YYYYMMDD

REM 4. Or delete if you don't need them
REM rmdir /s /q Descriptions
```

**What to keep:**
- ✅ `jsondata/` directory (REQUIRED for gallery)
- ✅ `images/` directory (REQUIRED for gallery)
- ✅ `index.html` (REQUIRED for gallery)
- ✅ CSV export file (optional, for analysis)

**What can be deleted:**
- ❌ `Descriptions/wf_*` directories (44 workflow dirs)
- ❌ Individual workflow logs and summary files

### 4.3 Disk Space Savings

**Typical sizes:**
- Each workflow directory: 50-200 KB (mostly text)
- 44 workflows: ~4-8 MB total
- `jsondata/` directory: 2-4 MB total
- CSV export: 500 KB - 1 MB

**After cleanup:** You'll save 4-8 MB of disk space, which may not be significant, but reduces clutter.

### 4.4 Re-generating Gallery Data

**If you need to regenerate the gallery data files:**

```batch
REM If you still have Descriptions/ directory:
python consolidate_gallery_data.py

REM If you deleted Descriptions/ but have the CSV:
REM You'll need to re-run the workflows with generate_all_gallery_data.bat
```

---

## Troubleshooting

### Problem: Gallery shows "No data available"

**Causes:**
- `jsondata/` directory missing or empty
- `index.json` missing or malformed
- JSON files have incorrect provider/model/prompt names

**Fix:**
```batch
REM Re-run consolidation
python consolidate_gallery_data.py

REM Verify files exist
dir jsondata
type jsondata\index.json
```

### Problem: Images don't load

**Causes:**
- `images/` directory missing
- Image files in wrong location
- Path configuration mismatch

**Fix:**
1. Check `index.html` CONFIG section (around line 988):
   ```javascript
   const CONFIG = {
       imagesBaseUrl: './images/',  // Verify this path
       descriptionsBaseUrl: './jsondata/'
   };
   ```
2. Ensure images are in the correct directory
3. Check image file extensions match what's in JSON files

### Problem: Some providers/models missing

**Causes:**
- Workflows didn't complete successfully
- JSON files weren't created during consolidation
- API errors or rate limits during data collection

**Fix:**
```batch
REM Check which workflows completed
dir Descriptions

REM Re-run failed workflows individually
REM Example for Claude:
c:\idt\idt.exe workflow c:\idt\images --provider claude --model claude-3-5-haiku-20241022 --prompt-style narrative --name 25imagetest --output-dir Descriptions --batch

REM Then re-consolidate
python consolidate_gallery_data.py
```

### Problem: Descriptions are truncated or empty

**Causes:**
- API errors during generation
- Model timeouts
- Image format not supported by the model

**Fix:**
1. Check workflow logs in `Descriptions/wf_*/log_image_describer.txt`
2. Look for error messages
3. Re-run problematic workflows with increased timeout:
   ```batch
   c:\idt\idt.exe workflow c:\idt\images --timeout 300 ...
   ```

---

## Summary Checklist

- [ ] Install IDT and dependencies
- [ ] Configure API keys (if using cloud providers)
- [ ] Install Ollama and pull models (if using local models)
- [ ] Prepare 25 images in a directory
- [ ] Run `generate_all_gallery_data.bat` to collect descriptions
- [ ] Run `python consolidate_gallery_data.py` to create JSON files
- [ ] Copy images to `images/` directory
- [ ] Test gallery locally by opening `index.html`
- [ ] (Optional) Deploy to web hosting
- [ ] (Optional) Export CSV for analysis
- [ ] (Optional) Clean up workflow directories in `Descriptions/`

---

## Additional Resources

- **IDT Documentation:** See main repository README.md
- **Image Gallery README:** `tools/ImageGallery/README.md`
- **Alt Text Guide:** `tools/ImageGallery/README_ALT_TEXT.md`
- **Batch Scripts:** Located in `tools/ImageGallery/*.bat`
- **Python Scripts:** Located in `tools/ImageGallery/*.py`

---

*Last updated: October 25, 2025*
