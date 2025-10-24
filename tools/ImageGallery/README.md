# IDT Interactive Demo Gallery

An interactive web-based gallery that showcases the Image Description Toolkit's capabilities by allowing users to compare AI-generated image descriptions across different providers, models, and prompt styles.

## Purpose

This is a "one-time demo project to show the power of the IDT without having to install anything." Users can:

- View a collection of 25 test images
- Select different AI providers (Ollama, OpenAI, Claude)
- Choose from various models (llava, granite, gpt-4o, claude, etc.)
- Pick prompt styles (narrative, detailed, colorful, etc.)
- See how different configurations describe the same images

## Quick Start

### 1. Collect Gallery Data

Run workflows for all provider/model/prompt combinations:

```bash
# Full data collection (27 workflows)
generate_all_gallery_data.bat c:\idt\images

# Or test first (6 workflows)
generate_test_gallery_data.bat c:\idt\images
```

See `GALLERY_DATA_CHECKLIST.md` for detailed progress tracking.

### 2. Generate JSON Files

```bash
cd tools\ImageGallery
python generate_descriptions.py --name 25imagetest
```

### 3. Test Locally

```bash
test_gallery.bat
```

### 4. Deploy to Web Server

Copy these files to your web server:
- `index.html`
- `descriptions/` folder (with all JSON files)
- `*.jpg` files (25 images)

## Architecture

### Files

1. **index.html** - Single-page interactive gallery
   - Responsive design (mobile and desktop)
   - Three view modes: Single, Provider Comparison, Prompt Matrix
   - Provider/Model/Prompt dropdowns with smart validation
   - Image viewer with prev/next navigation (Alt+P/Alt+N)
   - Model navigation buttons in Provider Comparison mode
   - Description display panel with accessibility features
   - Collapsible prompt text viewer
   - WCAG 2.2 AA compliant interface

2. **generate_descriptions.py** - Data extraction script
   - Scans IDT workflow directories
   - Parses description files
   - Generates JSON files for web consumption
   - Normalizes Ollama model names (treats "model" and "model:latest" as same)

3. **generate_all_gallery_data.bat** - Comprehensive data collection
   - Runs 27 workflows (3 providers × 3-4 models × 3 prompts)
   - Claude: Haiku 3.5, Opus 4, Sonnet 4.5
   - OpenAI: GPT-4o-mini, GPT-4o
   - Ollama: Qwen3-VL Cloud, Llava, Gemma3, Moondream

4. **generate_test_gallery_data.bat** - Quick test (6 workflows)
   - One model per provider, 2 prompts each
   - Good for testing before full run

5. **GALLERY_DATA_CHECKLIST.md** - Progress tracking
   - Checklist for all 27 workflows
   - Prerequisites and setup instructions
   - Ollama model installation commands

6. **descriptions/** - Generated JSON data
   - index.json - Configuration index
   - {provider}_{model}_{prompt}.json - Individual description sets

### Data Flow

```
Workflow Directories (c:\idt\Descriptions)
    ↓
generate_descriptions.py (scans & parses)
    ↓
JSON Files (descriptions/*.json)
    ↓
index.html (loads & displays)
    ↓
User's Browser
```

## Data Collection

## Data Collection

### Automated Data Collection (Recommended)

Use the batch files to automatically run all needed workflows:

**Full Collection (27 workflows):**
```bash
generate_all_gallery_data.bat c:\idt\images
```

This runs:
- Claude: 3 models × 3 prompts = 9 workflows
- OpenAI: 2 models × 3 prompts = 6 workflows
- Ollama: 4 models × 3 prompts = 12 workflows

**Test Collection (6 workflows):**
```bash
generate_test_gallery_data.bat c:\idt\images
```

Good for testing before committing to the full 27-workflow run.

### Prerequisites

Before running data collection:

1. **Set up API keys:**
   ```bash
   # In bat/ directory
   setup_claude_key.bat
   setup_openai_key.bat
   ```

2. **Install Ollama models:**
   ```bash
   ollama pull qwen3-vl:235b-cloud
   ollama pull llava:latest
   ollama pull gemma3:latest
   ollama pull moondream:latest
   ```

3. **Ensure Ollama is running**

See `GALLERY_DATA_CHECKLIST.md` for detailed tracking of workflow completion.

## Interface Features

### View Modes

1. **Single View**: Traditional image gallery with individual model/prompt selection
2. **Provider Comparison**: Compare how different providers handle the same prompt style
3. **Prompt Matrix**: See all prompt styles for a selected model across multiple images

### Model Navigation (Provider Comparison)

The Provider Comparison view includes model navigation buttons (‹ and ›) for each provider that has multiple models available:

- **Navigation**: Click ‹ or › to cycle through available models for each provider
- **State Persistence**: Model selections are remembered throughout the session
- **Model Count Display**: Shows current model and total count (e.g., "2/4")
- **Accessibility**: Buttons include proper ARIA labels for screen readers
- **Smart Disable**: Navigation buttons are disabled when only one model is available

Example: When comparing the "narrative" prompt across providers, you might see:
- Claude: Sonnet 4.5 (1/3) with navigation to Haiku 3.5 and Opus 4
- OpenAI: GPT-4o (1/2) with navigation to GPT-4o-mini  
- Ollama: Llava (1/4) with navigation to Qwen3-VL, Gemma3, and Moondream

### Keyboard Shortcuts

- **Alt+P**: Previous image
- **Alt+N**: Next image
- **Arrow Keys**: Navigate through dropdowns and buttons
- **Enter/Space**: Activate buttons and selections

### Manual Data Collection

If you prefer to run workflows individually:

```bash
idt workflow c:\idt\images --provider claude --model claude-3-5-haiku-20241022 --prompt-style narrative --name 25imagetest
idt workflow c:\idt\images --provider openai --model gpt-4o-mini --prompt-style colorful --name 25imagetest
# ... etc
```

## Data Generation

### 1. Generate Description Data

Run the Python script to extract descriptions from your workflow directories:

```bash
cd tools/ImageGallery
python generate_descriptions.py
```

**Options:**
- `--input-dir PATH` or `--descriptions-dir PATH` - Path to Descriptions directory containing workflows (default: c:/idt/Descriptions)
- `--output-dir PATH` - Output directory for JSON files (default: descriptions)
- `--name PATTERN` or `--pattern PATTERN` - Workflow name pattern to match in directory names (default: 25imagetest)

**Example with custom input directory:**
```bash
# If your workflow data is in a different location
python generate_descriptions.py \
    --input-dir /path/to/your/Descriptions \
    --output-dir web_data \
    --name multipletest
```

**Example for generating from a specific Descriptions folder:**
```bash
# Generate from c:/mydata/Descriptions with default 25imagetest pattern
python generate_descriptions.py --input-dir c:/mydata/Descriptions

# Or use a different workflow name pattern
python generate_descriptions.py --input-dir c:/idt/Descriptions --name 10multipletest
```

### 2. Prepare Images

Copy your converted JPG images to the deployment directory:

```bash
# From your workflow's converted_images directory
cp c:/idt/Descriptions/wf_25imagetest_*/converted_images/*.jpg ./
```

Or use the source images directory:
```bash
cp c:/idt/images/*.jpg ./
```

### 3. Update Image List (if needed)

If you add more images, update the `images` array in index.html:

```javascript
images = [
    'IMG_4276.jpg',
    'IMG_4277.jpg',
    // ... add more images here
];
```

### 4. Deploy to Web Server

Copy these files to your web server:
- index.html
- descriptions/ (entire directory)
- *.jpg (all image files)

**Example using FTP:**
```bash
# In FTP client
cd /public_html/testimages
put index.html
mkdir descriptions
cd descriptions
mput descriptions/*.json
cd ..
mput *.jpg
```

**Example using network drive:**
```powershell
# In PowerShell
Copy-Item -Path "index.html" -Destination "Z:\testimages\"
Copy-Item -Path "descriptions" -Destination "Z:\testimages\" -Recurse
Copy-Item -Path "*.jpg" -Destination "Z:\testimages\"
```

## Adding More Data

The system is designed to scale easily:

1. **Run more workflows** - Use IDT with different configurations
   - Make sure workflow names include your pattern (e.g., "25imagetest")
   - Use consistent image sets across workflows for comparison

2. **Re-generate JSON** - Run the script again to pick up new workflows
   ```bash
   python generate_descriptions.py
   ```

3. **Upload updates** - Copy new JSON files to your server
   ```bash
   # Only updated files need to be re-uploaded
   ftp> cd descriptions
   ftp> mput *.json
   ```

The gallery will automatically detect and display new configurations!

## Data Structure

### Workflow Directory Naming
```
wf_WORKFLOWNAME_PROVIDER_MODEL_[VARIANT_]PROMPTSTYLE_TIMESTAMP/
    descriptions/
        image_descriptions.txt
```

Example:
```
wf_25imagetest_ollama_llava_7b_narrative_20251021_200409/
wf_25imagetest_claude_claude-3-haiku-20240307_narrative_20251022_141523/
wf_25imagetest_ollama_granite3.2-vision_latest_colorful_20251022_160315/
```

### Description File Format
```
File: converted_images\image.jpg
Provider: ollama
Model: llava:7b
Prompt Style: narrative
Description: [Multi-paragraph description text]
Timestamp: 2025-10-21 20:05:26
--------------------------------------------------------------------------------
```

### Generated JSON Structure

**index.json:**
```json
{
  "configs": {
    "providers": ["ollama", "claude", "openai"],
    "models": {
      "ollama": ["llava:7b", "granite3.2-vision"],
      "claude": ["claude-3-haiku"]
    },
    "prompts": {
      "ollama": {
        "llava:7b": ["narrative", "detailed"],
        "granite3.2-vision": ["colorful"]
      }
    }
  }
}
```

**ollama_llava_7b_narrative.json:**
```json
{
  "provider": "ollama",
  "model": "llava:7b",
  "prompt_style": "narrative",
  "images": {
    "IMG_4276.jpg": {
      "description": "The image shows...",
      "provider": "ollama",
      "model": "llava:7b",
      "prompt_style": "narrative",
      "timestamp": "2025-10-21 20:05:26"
    }
  }
}
```

## Customization

### Styling
Edit the `<style>` section in index.html to customize:
- Colors and gradients
- Layout (single column vs. side-by-side)
- Font sizes and spacing
- Mobile breakpoints

### Configuration
Update the `CONFIG` object in index.html:
```javascript
const CONFIG = {
    imagesBaseUrl: './',              // Image location
    descriptionsBaseUrl: './descriptions/',  // JSON location
    workflowPattern: '25imagetest'    // Workflow pattern
};
```

### Workflow Pattern
To include different workflows, change the pattern:
```bash
# Generate from all workflows
python generate_descriptions.py --name ""

# Generate from specific test set
python generate_descriptions.py --name "multipletest"

# Generate from model-specific runs
python generate_descriptions.py --name "granite"
```

## Troubleshooting

### No descriptions showing
1. Check browser console for errors (F12)
2. Verify descriptions/index.json exists and loads
3. Check that JSON filenames match the pattern: `{provider}_{model}_{prompt}.json`
4. Ensure descriptions directory is in the same location as index.html

### Images not loading
1. Verify image files are in correct location
2. Check image filenames match exactly (case-sensitive on some servers)
3. Ensure images are JPG format (not HEIC)

### Missing configurations
1. Re-run generate_descriptions.py to scan for new workflows
2. Verify workflow directories match the naming pattern
3. Check that description files exist in workflow directories

### Parsing errors
1. Check workflow directory naming follows the expected format
2. Verify description files have the expected structure
3. Look for encoding issues in description files (should be UTF-8)

## Performance Notes

- **Initial Load**: Loads only index.json (~few KB)
- **Per Configuration**: Loads one JSON file when selection changes (~50-200KB depending on image count)
- **Images**: Lazy loaded, one at a time as user navigates
- **Caching**: Browser will cache JSON and images after first load

For best performance:
- Keep JSON files under 500KB each
- Optimize images (1200px width recommended)
- Use a CDN for large deployments

## Future Enhancements

Possible additions:
- [ ] Side-by-side comparison mode (view 2+ configs at once)
- [ ] Search/filter functionality
- [ ] Export descriptions to text file
- [ ] Direct links to specific image/config combinations
- [ ] Image zoom/lightbox feature
- [ ] Statistics display (word count, processing time)
- [ ] Model performance comparison charts

## License

Part of the Image Description Toolkit project.
