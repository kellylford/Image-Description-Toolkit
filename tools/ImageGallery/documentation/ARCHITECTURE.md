# Image Gallery Architecture

**Last Updated:** October 25, 2025

## Overview

The Image Gallery is a static web application that displays images alongside AI-generated descriptions from multiple providers, models, and prompts. It allows side-by-side comparison of how different AI configurations describe the same images.

## 🔴 IMPORTANT REFERENCES

**Before creating any new gallery**, read these documents:

1. **TEMPLATE_CHECKLIST.md** - Step-by-step guide for creating new galleries
2. **ARIA_EVALUATION_OCT24.md** - Critical accessibility requirements (why aria-labels were removed)
3. **Reference Commit**: `6de91fb` - Use this as the base template (October 24, 2025)

**Template Source of Truth**: `tools/ImageGallery/index.html` at commit **6de91fb**

---

## Directory Structure

```
ImageGallery/
├── index.html              # Gallery web interface (95KB)
├── images/                 # Source images (JPG files)
├── gallery-data/           # JSON data files (USED BY GALLERY) ~150KB
│   ├── index.json         # Lists all available configurations
│   └── *.json             # One file per provider_model_prompt combination
│
├── descriptions/           # Workflow outputs (NOT needed for deployment)
│   └── wf_*/              # Workflow directories (~130MB with logs)
│
├── jsondata/              # LEGACY: Old location, kept for compatibility
│   └── *.json             # Mirror of gallery-data/ directory
│
├── data/                  # Main gallery production data
│   ├── images/            # Production image files
│   └── jsondata/          # Production JSON files
│
├── contentprototype/      # Example: Secondary gallery
│   ├── images/            # Different image set
│   ├── gallery-data/      # JSON files for this gallery
│   ├── descriptions/      # Workflow outputs (can delete after deploy)
│   └── index.html         # Gallery interface (same as parent)
│
├── generate_descriptions.py   # Converts workflow outputs to JSON
├── generate_alt_text.py       # Adds accessibility alt text
└── *.md                      # Documentation files
```

**Critical Distinction:**
- `descriptions/wf_*/`: Workflow directories with logs, temp files (~130MB)
- `gallery-data/*.json`: Just the JSON files gallery needs (~150KB)
- **Deploy only the JSON files, not the workflow directories!**

---

## Key Concepts

### 1. Gallery Instance
Each gallery is a **self-contained directory** containing:
- `index.html` - The web interface
- `images/` - Image files to display
- `gallery-data/` (or `jsondata/`) - JSON data files **for deployment**
- `descriptions/` - Workflow outputs **for development only**

**Examples:**
- Main gallery: `tools/ImageGallery/` (uses `data/jsondata/`)
- Prototype gallery: `tools/ImageGallery/contentprototype/`

**Important:** Only `index.html`, `images/`, and `gallery-data/` (JSON files) need to be deployed to web server. The `descriptions/wf_*/` directories contain workflow logs and temp files (~130MB) that are NOT needed for the gallery.

### 2. Workflow Output
IDT workflows generate descriptions in this structure:
```
descriptions/
  wf_WORKFLOWNAME_PROVIDER_MODEL_PROMPTSTYLE_TIMESTAMP/
    descriptions/
      image_descriptions.txt    # Raw descriptions
    images_processed/           # Workflow tracking
    logs/                       # Execution logs
    workflow_metadata.json      # Configuration details
```

### 3. JSON Data Files
The gallery reads JSON files in this format:
```json
{
  "provider": "claude",
  "model": "claude-3-haiku-20240307",
  "prompt_style": "narrative",
  "images": {
    "photo.jpg": {
      "description": "Full AI description...",
      "alt_text": "Concise accessibility text",
      "provider": "claude",
      "model": "claude-3-haiku-20240307",
      "prompt_style": "narrative",
      "timestamp": "2025-10-25 12:34:56"
    }
  }
}
```

---

## Data Flow

### Complete Pipeline

```
1. Source Images
   └─> images/*.jpg

2. Run IDT Workflows
   └─> c:/idt/idt.exe workflow images/ --provider X --model Y --prompt-style Z
       └─> descriptions/wf_*_*_*_*/descriptions/image_descriptions.txt
       └─> descriptions/wf_*_*_*_*/logs/*.log (~130MB total)

3. Convert to JSON (separate output!)
   └─> python generate_descriptions.py --descriptions-dir descriptions/ --output-dir gallery-data/ --pattern WORKFLOWNAME
       └─> gallery-data/*.json (one per config, ~150KB total)
       └─> gallery-data/index.json (lists all configs)

4. Add Alt Text (optional but recommended)
   └─> python generate_alt_text.py --jsondata-dir gallery-data/
       └─> Adds "alt_text" field to each image in all JSON files

5. Deploy Gallery (only these files!)
   └─> Copy index.html, images/, gallery-data/ to web server
   └─> Total size: ~50-100MB (images) + ~150KB (JSON)
   └─> DO NOT copy descriptions/wf_*/ directories (saves ~130MB)
```

**Key Point:** Workflow directories (`descriptions/wf_*/`) contain logs and temp files that are useful for debugging but NOT needed for the gallery. Always use separate output directory for JSON files.

### Why Two Directories? (descriptions vs gallery-data)

**The Problem:**
- `descriptions/` contains workflow directories (`wf_*`) with logs, temp files (~130MB)
- Gallery only needs JSON files (~150KB)
- Deploying entire `descriptions/` wastes bandwidth and disk space

**The Solution:**
- Use `--output-dir gallery-data/` when generating JSON
- This creates clean directory with only JSON files
- Deploy `gallery-data/` to web server (not `descriptions/`)

**Current Practice:**
- **Development:** `descriptions/` has workflow outputs (keep locally)
- **Deployment:** `gallery-data/` has only JSON files (deploy this)
- **Legacy:** Some galleries use `jsondata/` (backward compatible)

**Size Comparison (25 images, 4 prompts):**
| Directory | Contents | Size |
|-----------|----------|------|
| `descriptions/` | Workflows + JSON | ~130MB |
| `gallery-data/` | JSON only | ~150KB |
| **Savings** | | **99.9%** |

---

## Configuration

### Gallery HTML (index.html)

Line ~1010 contains the configuration:

```javascript
const CONFIG = {
    imagesBaseUrl: './images/',           // Where to find image files
    descriptionsBaseUrl: './descriptions/', // Where to find JSON files
    workflowPattern: 'your_workflow_name'  // Used for filtering (optional)
};
```

**Key Points:**
- `imagesBaseUrl`: Relative path from index.html to images
- `descriptionsBaseUrl`: Relative path from index.html to JSON files
- `workflowPattern`: Typically matches workflow name used in IDT commands
- All paths are **relative to index.html location**

### Script Configuration

**generate_descriptions.py:**
```bash
python generate_descriptions.py \
  --descriptions-dir <workflow_output_dir> \    # Where wf_* directories are
  --output-dir <json_output_dir> \              # Where to write JSON files
  --pattern <workflow_name>                     # Filter workflows by name
```

**generate_alt_text.py:**
```bash
python generate_alt_text.py \
  --jsondata-dir <json_files_dir>    # Directory containing *.json files
```

---

## Gallery Deployment Models

### Model 1: Single Gallery (Main Production)
```
ImageGallery/
├── index.html          # Gallery interface
├── images/            # All images (~20-50 files)
├── descriptions/      # All JSON data
└── data/             # Historical: original location
    └── jsondata/     # (still used by main gallery)
```

**Use when:**
- Single set of images
- Main production gallery
- Maintaining backward compatibility

### Model 2: Multiple Sub-Galleries
```
ImageGallery/
├── index.html          # Template gallery
├── contentprototype/   # Europe vacation photos
│   ├── index.html
│   ├── images/
│   └── descriptions/
├── beach2024/         # Beach photos
│   ├── index.html
│   ├── images/
│   └── descriptions/
└── architecture/      # Building photos
    ├── index.html
    ├── images/
    └── descriptions/
```

**Use when:**
- Multiple distinct image sets
- Want independent galleries
- Easy to manage/deploy separately

### Model 3: Shared Images, Multiple Configs
```
ImageGallery/
├── index.html
├── images/            # Shared image set
└── descriptions/      # Many JSON files (different models/prompts)
    ├── claude_haiku_narrative.json
    ├── claude_opus_narrative.json
    ├── openai_gpt4o_narrative.json
    └── ... (dozens of configs)
```

**Use when:**
- Testing many AI configurations
- Comparing providers/models/prompts
- Demo/research gallery

---

## File Naming Conventions

### Workflow Directories
Format: `wf_WORKFLOWNAME_PROVIDER_MODEL_PROMPTSTYLE_TIMESTAMP`

Example: `wf_europeprototype_claude_claude-3-haiku-20240307_narrative_20251025_091557`

### JSON Files
Format: `PROVIDER_MODEL_PROMPTSTYLE.json`

Example: `claude_claude-3-haiku-20240307_narrative.json`

**Why different formats?**
- Workflow dirs include timestamp (unique, sortable)
- JSON files are canonical (latest version, no timestamp needed)

---

## Common Gotchas

### 1. Wrong Directory in generate_alt_text.py
**Problem:** Script looks for `jsondata/` but files are in `gallery-data/`

**Solution:** Use `--jsondata-dir` parameter:
```bash
python generate_alt_text.py --jsondata-dir gallery-data/
```

### 2. Deployed workflow directories to web server
**Problem:** Copied entire `descriptions/` directory including `wf_*` subdirectories

**Symptoms:**
- Gallery works but deployment is 100MB+ instead of ~1MB
- Unnecessary files on web server
- Wasted bandwidth

**Solution:**
```bash
# Instead of copying descriptions/, copy only JSON files
cp descriptions/*.json gallery-data/
# Then deploy gallery-data/ to web server

# Or use correct output-dir from start
python generate_descriptions.py \
  --descriptions-dir descriptions \
  --output-dir gallery-data \
  --pattern yourproject
```

**Prevention:** Always use separate `--output-dir` for JSON files

### 2. Gallery Shows "No configurations found"
**Problem:** `CONFIG.descriptionsBaseUrl` doesn't match actual directory

**Fix:**
```javascript
// In index.html, verify:
descriptionsBaseUrl: './descriptions/'  // Must match actual location
```

### 3. Images Don't Display
**Problem:** `CONFIG.imagesBaseUrl` is wrong or images not copied

**Fix:**
1. Check `imagesBaseUrl: './images/'` in index.html
2. Verify `ls images/*.jpg` shows files
3. Use browser console to see 404 errors

### 4. Workflow Pattern Mismatch
**Problem:** JSON files exist but gallery doesn't load them

**Cause:** `workflowPattern` in CONFIG doesn't match JSON filenames

**Fix:** Either:
- Set `workflowPattern: ''` (loads all JSON files)
- Or match workflow name used in commands

### 5. CORS Errors (file:// Protocol)
**Problem:** Gallery opened via `file://` instead of HTTP server

**Fix:** Always use HTTP server:
```bash
python -m http.server 8082
# Open http://localhost:8082
```

---

## Image Requirements

### Supported Formats
- **Primary:** JPG/JPEG
- Also works: PNG, GIF, WebP (with browser support)

### Recommended Specs
- **Resolution:** 1920x1080 or higher (for quality)
- **File size:** 1-5 MB per image (balance quality vs load time)
- **Total images:** 20-50 per gallery (sweet spot for comparison)
- **Aspect ratio:** Mixed OK, gallery handles automatically

### File Naming
- **Avoid:** Spaces, special characters, unicode
- **Good:** `IMG_1234.jpg`, `photo-5678.jpg`, `building_front.jpg`
- **Why:** URL encoding issues, server compatibility

---

## Alt Text Strategy

### Why Alt Text?
1. **Accessibility:** Screen readers for visually impaired users
2. **SEO:** Search engines use alt text for image context
3. **Fallback:** Displays if image fails to load
4. **Best practice:** WCAG 2.2 AA compliance

### Alt Text vs Description
| | Alt Text | Description |
|---|---|---|
| **Length** | 25-50 words | 100-500 words |
| **Purpose** | Quick identification | Detailed analysis |
| **Audience** | Screen readers, SEO | All users, comparison |
| **Tone** | Concise, factual | Varies by prompt style |

### Generation Strategy
1. **Source:** Use narrative prompt descriptions (most neutral)
2. **Model:** Claude Haiku (fast, accurate, cost-effective)
3. **Consistency:** Same image = same alt text across all configs
4. **Review:** Spot-check first 5-10 before processing all

---

## Performance Considerations

### Gallery Size Recommendations

| Gallery Size | Image Count | JSON Configs | Total Size | Load Time |
|--------------|-------------|--------------|------------|-----------|
| **Small** | 10-20 | 3-6 | 30-80 MB | <2 sec |
| **Medium** | 20-50 | 6-12 | 80-200 MB | 2-5 sec |
| **Large** | 50-100 | 12-27 | 200-500 MB | 5-10 sec |
| **Extra Large** | 100+ | 27+ | 500+ MB | 10+ sec |

**Recommendations:**
- **Optimal:** 25-30 images, 6-9 configs (~120 MB)
- **Maximum:** 50 images, 12 configs (~250 MB) before considering split
- **Split galleries:** If exceeding 300 MB or 60 images

### Optimization Tips
1. **Image compression:** Use 85% JPG quality, resize to 1920px max width
2. **Lazy loading:** Gallery loads images on-demand (already implemented)
3. **CDN:** Use for large deployments
4. **Caching:** Enable browser caching with proper headers
5. **Progressive:** Start with small gallery, expand based on user interest

---

## Accessibility Features

### WCAG 2.2 AA Compliance
- ✅ Alt text on all images
- ✅ Keyboard navigation (Tab, Arrow keys, Enter)
- ✅ Screen reader announcements
- ✅ Color contrast (4.5:1 minimum)
- ✅ Focus indicators
- ✅ Semantic HTML

### Keyboard Controls
- **Tab/Shift+Tab:** Navigate between images
- **Arrow keys:** Move between images in browser/explorer modes
- **Enter:** Select image/toggle description
- **Alt+P:** Toggle prompt text
- **Alt+N:** Next prompt style (future)

### Screen Reader Support
- Image alt text announced on focus
- Description text readable
- Button/control labels clear
- Status announcements (mode changes, etc.)

---

## Version History

### Current Version
- **Date:** October 25, 2025
- **Features:**
  - Dual view modes (Image Browser, Description Explorer)
  - Alt text support
  - Multiple provider/model/prompt support
  - Keyboard accessible
  - Responsive design

### Known Limitations
- No video support (images only)
- Requires HTTP server (not file://)
- Alt text per-config (not truly consistent yet)
- No batch image upload UI

---

## Future Enhancements

### Planned
1. **Truly consistent alt text:** Same for all configs
2. **Batch upload interface:** Upload images via web UI
3. **Online workflow execution:** Run IDT from browser
4. **Comparison view:** Side-by-side 2-3 configs
5. **Export functionality:** Download descriptions as CSV/JSON
6. **Search/filter:** Find images by description keywords

### Under Consideration
- **Video support:** Extend to video descriptions
- **Audio descriptions:** TTS for descriptions
- **Collaborative:** Multi-user rating/feedback
- **API:** RESTful API for programmatic access
- **Mobile app:** Native iOS/Android version

---

## Maintenance

### Adding New Images
```bash
# 1. Add images to images/ directory
cp /path/to/new/*.jpg images/

# 2. Run workflows for all configs
c:/idt/idt.exe workflow images/ --provider X --model Y --prompt-style Z ...

# 3. Regenerate JSON
python generate_descriptions.py --descriptions-dir descriptions/ --output-dir descriptions/

# 4. Regenerate alt text
python generate_alt_text.py --jsondata-dir descriptions/

# 5. Test
python -m http.server 8082
```

### Updating to New Model
```bash
# 1. Run workflow with new model
c:/idt/idt.exe workflow images/ --provider claude --model NEW_MODEL --prompt-style narrative ...

# 2. Add to JSON (will create new config file)
python generate_descriptions.py --descriptions-dir descriptions/ --output-dir descriptions/

# 3. Gallery automatically picks up new config
```

### Removing Old Configs
```bash
# 1. Delete JSON file
rm descriptions/OLD_PROVIDER_MODEL_PROMPT.json

# 2. Regenerate index
python generate_descriptions.py --descriptions-dir descriptions/ --output-dir descriptions/

# Gallery will no longer show that config
```

---

## Troubleshooting

### No descriptions appear
1. Check browser console for errors
2. Verify `descriptions/*.json` files exist
3. Check CONFIG.descriptionsBaseUrl in index.html
4. Ensure HTTP server running (not file://)

### Wrong alt text for images
1. Check if alt text generated: `grep "alt_text" descriptions/*.json`
2. Verify model used for alt text generation
3. Re-run with correct source: `python generate_alt_text.py --jsondata-dir descriptions/`

### Gallery loads but images missing
1. Verify images exist: `ls images/*.jpg`
2. Check CONFIG.imagesBaseUrl in index.html
3. Look for 404 errors in browser console
4. Check file permissions

### Performance issues
1. Check total file size: `du -sh .`
2. Count images: `ls images/*.jpg | wc -l`
3. Consider splitting into multiple galleries
4. Compress images: `mogrify -quality 85 -resize 1920x images/*.jpg`

---

## Support Files

### Documentation
- `README.md` - Main documentation, quick start
- `ARCHITECTURE.md` - This file, technical details
- `REPLICATION_GUIDE.md` - Step-by-step guide for creating new galleries
- `SETUP_GUIDE.md` - Initial setup instructions
- `GALLERY_DATA_CHECKLIST.md` - Workflow tracking checklist

### Scripts
- **`generate_descriptions.py`** - Workflow → JSON conversion
  - Extracts descriptions from workflow directories
  - Creates JSON files for gallery consumption
  - Usage: `--descriptions-dir <workflows> --output-dir <json> --pattern <name>`
  
- **`generate_alt_text.py`** - Alt text generation
  - Adds accessibility alt text to JSON files
  - Uses Claude API to generate concise descriptions
  - Usage: `--jsondata-dir <json-directory>`
  
- **`export_analysis_data.py`** - Export workflow data for analysis
  - Extracts timing, token usage, costs from workflow logs
  - Creates CSV with one row per image processed
  - Usage: `--descriptions-dir <workflows> --output-dir <analysis> --pattern <name>`
  - **Should be copied to each gallery project for analysis**
  
- **`check_data_status.py`** - Verify gallery data integrity
  - Checks for missing files, corrupt JSON
  - Validates data completeness

### Batch Files (Windows)
- `generate_all_gallery_data.bat` - Run all 27 workflows
- `generate_test_gallery_data.bat` - Run 6 test workflows
- `test_gallery.bat` - Start local HTTP server
- `generate_alt_text.bat` - Alt text generation wrapper

---

## Analysis and Reporting

### Export Workflow Data

The `export_analysis_data.py` script extracts comprehensive metrics from workflow logs:

**Usage:**
```bash
cd yourproject
cp ../export_analysis_data.py .

python export_analysis_data.py \
  --descriptions-dir descriptions \
  --output-dir analysis \
  --pattern yourproject
```

**Output:** CSV file with columns:
- `workflow_name`, `provider`, `model`, `prompt_style`
- `image_filename`, `file_size_bytes`
- `processing_time_seconds`
- `input_tokens`, `output_tokens`, `total_tokens`
- `estimated_cost_usd`
- `timestamp`, `success`

**Use Cases:**
1. **Cost Analysis:** Compare total costs across providers/models
2. **Performance:** Identify slow models or large images
3. **Token Usage:** Understand token consumption patterns
4. **Quality vs Cost:** Balance description quality with budget
5. **Model Selection:** Data-driven choice for production

**Example Analysis:**
```bash
# Total cost per model
csvcut -c model,estimated_cost_usd analysis/image_analysis_*.csv | \
  csvstat --sum

# Average processing time
csvcut -c model,processing_time_seconds analysis/image_analysis_*.csv | \
  csvstat --mean

# Token usage patterns
csvcut -c prompt_style,total_tokens analysis/image_analysis_*.csv | \
  csvstat
```

---

## Best Practices

### For Gallery Creators
1. **Start small:** 10-15 images, 3-4 configs for testing
2. **Test workflows:** Run one workflow completely before batch processing
3. **Review quality:** Check first few descriptions before continuing
4. **Alt text early:** Generate after first config, not at the end
5. **Document:** Note which models/prompts work best

### For Gallery Users
1. **Use HTTP server:** Always, never open via file://
2. **Update regularly:** Re-generate JSON when adding images
3. **Backup:** Keep copy of source images and workflow outputs
4. **Monitor size:** Watch total gallery size, split if needed
5. **Test accessibility:** Use keyboard and screen reader

### For Developers
1. **Validate JSON:** Check format after generation
2. **Handle errors:** Graceful degradation if files missing
3. **Log issues:** Browser console for debugging
4. **Version control:** Track changes to index.html, scripts
5. **Document changes:** Update this file when modifying architecture

---

**For more information, see:**
- [README.md](README.md) - Quick start and usage
- [REPLICATION_GUIDE.md](REPLICATION_GUIDE.md) - Create new galleries
- [Image Description Toolkit Documentation](../../docs/) - Main IDT docs
