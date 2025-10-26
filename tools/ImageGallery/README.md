# Image Gallery - Organized Structure# IDT Interactive Demo Gallery



**Last Updated:** October 25, 2025An interactive web-based gallery that showcases the Image Description Toolkit's capabilities by allowing users to compare AI-generated image descriptions across different providers, models, and prompt styles.



This directory contains everything needed to create and deploy image galleries that showcase AI-generated descriptions from multiple providers, models, and prompts.---



## 📁 Directory Structure## Quick Start



```### View Existing Gallery

ImageGallery/

├── galleries/           Individual galleries (template + deployed)```bash

├── documentation/       All guides and reference docscd tools/ImageGallery

├── content-creation/    Scripts and tools for creating galleriespython -m http.server 8082

├── archive_old/         Historical files (not needed for regular use)# Open browser to: http://localhost:8082

├── index.html           Root template file (reference version)```

└── requirements.txt     Python dependencies

```### Create Your Own Gallery



## 🚀 Quick Start**See [REPLICATION_GUIDE.md](REPLICATION_GUIDE.md) for detailed instructions.**



### For Creating a New GalleryQuick summary (30-45 minutes for 25 images):

1. Create project directory and add 15-30 images

1. **Read the documentation**:2. Run 4 IDT workflows (narrative, colorful, technical, detailed)

   ```bash3. Generate JSON files from workflows

   cd documentation/4. Add accessibility alt text

   cat TEMPLATE_CHECKLIST.md5. Configure and deploy

   ```

---

2. **Copy the template**:

   ```bash## Documentation Map

   cd galleries/

   cp -r template/ my-new-gallery/| Document | Purpose | Who Should Read |

   ```|----------|---------|-----------------|

| **README.md** | Quick start, overview | Everyone (start here) |

3. **Add images** to `my-new-gallery/images/`| **[REPLICATION_GUIDE.md](REPLICATION_GUIDE.md)** | Step-by-step gallery creation | Gallery creators |

| **[ARCHITECTURE.md](ARCHITECTURE.md)** | Technical details, troubleshooting | Developers, advanced users |

4. **Build the gallery**:| **[SETUP_GUIDE.md](SETUP_GUIDE.md)** | Deployment instructions | System administrators |

   ```bash

   cd ../content-creation/**Archived Documentation:**

   python build_gallery.py ../galleries/my-new-gallery/- [archive/GALLERY_DATA_CHECKLIST.md](archive/GALLERY_DATA_CHECKLIST.md) - Workflow tracking checklist

   ```- [archive/README_ALT_TEXT.md](archive/README_ALT_TEXT.md) - Alt text implementation details



5. **Deploy** - Upload `my-new-gallery/` to your server---



### For Generating Descriptions## Gallery Features



1. **Run IDT workflows** on your images### User Features

2. **Convert to gallery format**:- **Two View Modes:**

   ```bash  - **Image Browser:** Browse images with descriptions

   cd content-creation/  - **Description Explorer:** Search/filter by description text

   python generate_descriptions.py ../galleries/my-gallery/images/  

   python generate_alt_text.py ../galleries/my-gallery/- **Multi-Provider Comparison:**

   ```  - Claude (Haiku, Opus, Sonnet)

  - OpenAI (GPT-4o, GPT-4o-mini)

## 📚 Key Documentation  - Ollama (Llava, Qwen, Gemma, etc.)

  

All documentation is in the `documentation/` directory:- **Multiple Prompt Styles:**

  - Narrative (balanced, story-like)

- **TEMPLATE_CHECKLIST.md** - Step-by-step gallery creation guide  - Colorful (artistic, vibrant)

- **BUILD_GALLERY_README.md** - How to use build_gallery.py  - Technical (analytical, detailed)

- **ARCHITECTURE.md** - Overall system design  - Detailed (comprehensive, thorough)

- **ARIA_EVALUATION_OCT24.md** - Accessibility requirements  

- **README.md** - Complete overview (start here!)- **Accessibility:**

- **SETUP_GUIDE.md** - Initial setup instructions  - WCAG 2.2 AA compliant

- **SOURCE_CONTROL.md** - What to commit to git  - Keyboard navigation (arrows, Tab, Enter)

  - Screen reader support

## 🛠️ Content Creation Tools  - Alt text on all images



All tools are in the `content-creation/` directory:### Gallery Capabilities

- Side-by-side comparison of different AI descriptions

### Python Scripts- Filter by provider, model, or prompt style

- **build_gallery.py** - Automatically updates image list in index.html- Responsive design (desktop and mobile)

- **generate_descriptions.py** - Converts workflow outputs to JSON- Works offline (static files)

- **generate_alt_text.py** - Adds accessibility alt text- No backend required

- **check_data_status.py** - Verifies gallery data

- **evaluate_alt_text_generation.py** - Tests alt text quality---

- **export_analysis_data.py** - Exports analysis data

## Architecture Overview

### Batch Files (Windows)

- **generate_all_gallery_data.bat** - Full workflow automation```

- **generate_alt_text.bat** - Alt text generationGallery Directory Structure:

- **test_gallery.bat** - Local testing├── index.html              # Web interface

├── images/                 # Image files (JPG)

## 🎨 Galleries├── gallery-data/           # JSON files for gallery (DEPLOY THIS)

│   ├── index.json         # Configuration list

The `galleries/` directory contains:│   └── *.json             # One per provider+model+prompt

├── descriptions/           # Workflow outputs (KEEP LOCAL)

- **template/** - Clean starting point for new galleries│   └── wf_*/              # Logs, temp files (~130MB)

- **europe/** - Example deployed gallery (Europe travel photos)└── generate_*.py          # Data generation scripts

- *(Your new galleries go here)*```



## 🗄️ Archive**Data Flow:**

```

The `archive_old/` directory contains historical documentation and cleanup records. Not needed for regular use.Images → IDT Workflows → descriptions/wf_*/ → JSON Files → Gallery

                         (~130MB, keep local)  (~150KB, deploy)

## 🎯 Typical Workflow```



```bash**Critical:** Only deploy `index.html`, `images/`, and `gallery-data/` to web server. The `descriptions/wf_*/` directories are development artifacts (logs, temp files) not needed by the gallery.

# 1. Create from template

cd galleries/**See [ARCHITECTURE.md](ARCHITECTURE.md) for complete technical details.**

cp -r template/ my-gallery/

---

# 2. Add images

cp /path/to/photos/* my-gallery/images/## Requirements



# 3. Build gallery (automatic image list)### To View Gallery

cd ../content-creation/- Modern web browser (Chrome, Firefox, Safari, Edge)

python build_gallery.py ../galleries/my-gallery/- HTTP server (Python's `http.server` works great)

- **Note:** Won't work with `file://` protocol due to CORS

# 4. Optional: Generate descriptions

python generate_descriptions.py ../galleries/my-gallery/images/### To Create Gallery

python generate_alt_text.py ../galleries/my-gallery/- **IDT:** Image Description Toolkit (`idt.exe`)

- **Python 3.x** with `requests` package

# 5. Test locally- **API Keys:** Claude and/or OpenAI (depending on providers)

cd ../galleries/my-gallery/- **Images:** 15-30 JPG files recommended

python -m http.server 8000- **Time:** 30-45 minutes for complete gallery



# 6. Deploy: Upload to server---

```

## Common Tasks

## 📦 Dependencies

### Add New Images

Install Python dependencies:```bash

```bash# 1. Copy images to images/ directory

pip install -r requirements.txtcp /path/to/new/*.jpg images/

```

# 2. Re-run workflows

## 🌐 Live Examplesc:/idt/idt.exe workflow images/ --provider claude --model MODEL --prompt-style STYLE ...



- **Europe Gallery**: https://www.kellford.com/europegallery/# 3. Regenerate JSON

- **Cottage Gallery**: https://www.kellford.com/idtdemo/python generate_descriptions.py --descriptions-dir descriptions/ --output-dir gallery-data/



## 📖 Getting Started# 4. Regenerate alt text

python generate_alt_text.py --jsondata-dir gallery-data/

1. **New to this?** Start with `documentation/SETUP_GUIDE.md````

2. **Creating a gallery?** Follow `documentation/TEMPLATE_CHECKLIST.md`

3. **Need help?** Check `documentation/README.md` for complete overview### Add New Model Configuration

```bash

## ⚡ Key Features# 1. Run workflow with new model

c:/idt/idt.exe workflow images/ --provider PROVIDER --model NEW_MODEL --prompt-style STYLE ...

- ✅ **Automatic image list generation** - No manual editing

- ✅ **WCAG 2.2 AA accessible** - Screen reader optimized# 2. Regenerate JSON (will include new config)

- ✅ **Multiple AI providers** - Compare descriptions side-by-sidepython generate_descriptions.py --descriptions-dir descriptions/ --output-dir gallery-data/

- ✅ **Easy deployment** - Static HTML, works anywhere

- ✅ **Clean template system** - Start new galleries in minutes# Gallery automatically shows new configuration

```

## 🔗 Related

### Export Analysis Data

This is part of the **Image Description Toolkit (IDT)** project.```bash

# Extract workflow metrics (timing, tokens, costs)

- Main project: `../../` (two levels up)python export_analysis_data.py \

- IDT CLI tool: Use for generating descriptions  --descriptions-dir descriptions \

- Viewer tool: For browsing workflow outputs  --output-dir analysis \

  --pattern WORKFLOW_NAME

---

# Creates CSV with per-image data

**Repository Size**: ~81MB (after cleanup from 4.3GB)  # Use for cost analysis, performance benchmarking

**Last Major Cleanup**: October 25, 2025```


### Remove Configuration
```bash
# 1. Delete JSON file
rm descriptions/PROVIDER_MODEL_PROMPT.json

# 2. Regenerate index
python generate_descriptions.py --descriptions-dir descriptions/ --output-dir descriptions/
```

---

## Gallery Examples

### Main Gallery (Production)
- **Location:** `tools/ImageGallery/`
- **Images:** Test/demo images (24 images)
- **Configurations:** Multiple providers and models
- **Data:** `data/jsondata/` directory

### Content Prototype (Europe Trip)
- **Location:** `tools/ImageGallery/contentprototype/`
- **Images:** Europe vacation photos (25 images)
- **Configurations:** Claude Haiku (4 prompt styles)
- **Data:** `descriptions/` directory
- **Purpose:** Proof of concept for Phase 2

---

## Troubleshooting

### Gallery won't load
- ✓ Check you're using HTTP server, not `file://`
- ✓ Verify `descriptions/*.json` files exist
- ✓ Check browser console for errors
- ✓ Confirm `CONFIG.descriptionsBaseUrl` matches actual directory

### Images don't display
- ✓ Verify `images/*.jpg` files exist
- ✓ Check `CONFIG.imagesBaseUrl` in `index.html`
- ✓ Look for 404 errors in browser console

### No descriptions appear
- ✓ Check JSON files are not empty: `ls -lh descriptions/*.json`
- ✓ Verify workflow completed successfully
- ✓ Re-run: `python generate_descriptions.py`

### Alt text missing
- ✓ Run: `python generate_alt_text.py --jsondata-dir descriptions/`
- ✓ Check API key is set: `echo $ANTHROPIC_API_KEY`
- ✓ Verify `grep "alt_text" descriptions/*.json` shows results

**For detailed troubleshooting, see [ARCHITECTURE.md](ARCHITECTURE.md).**

---

## Scripts Reference

### Data Generation
- **`generate_descriptions.py`** - Convert IDT workflow outputs to JSON
  ```bash
  python generate_descriptions.py \
    --descriptions-dir descriptions \
    --output-dir descriptions \
    --pattern WORKFLOW_NAME
  ```

- **`generate_alt_text.py`** - Add accessibility alt text
  ```bash
  python generate_alt_text.py --jsondata-dir descriptions/
  ```

- **`check_data_status.py`** - Verify gallery data integrity

### Batch Workflows (Windows)
- **`generate_all_gallery_data.bat`** - Run all 27 workflows
- **`generate_test_gallery_data.bat`** - Run 6 test workflows
- **`test_gallery.bat`** - Start local HTTP server
- **`generate_alt_text.bat`** - Alt text generation wrapper

---

## Best Practices

### For Gallery Creators
1. **Start small:** Test with 10 images and 2 prompts first
2. **Review quality:** Check first few descriptions before batch processing
3. **Add alt text:** Generate after workflows complete
4. **Test locally:** Use `python -m http.server` before deployment
5. **Document:** Note which models/prompts work best for your use case

### For Gallery Users
1. **Use HTTP server:** Never open via `file://` protocol
2. **Keyboard shortcuts:** Learn Alt+P/Alt+N for navigation
3. **Compare prompts:** Try same image with different prompt styles
4. **Accessibility:** Test with keyboard-only navigation

### For Developers
1. **Validate JSON:** Check format after generation
2. **Handle errors:** Gallery degrades gracefully if files missing
3. **Version control:** Track changes to `index.html` and scripts
4. **Document changes:** Update ARCHITECTURE.md when modifying structure

---

## Performance Notes

### Recommended Gallery Sizes

| Size | Images | Configs | Total Size | Load Time |
|------|--------|---------|------------|-----------|
| **Small** | 10-20 | 3-6 | 30-80 MB | <2 sec |
| **Medium** | 20-50 | 6-12 | 80-200 MB | 2-5 sec |
| **Large** | 50-100 | 12-27 | 200-500 MB | 5-10 sec |

**Optimal:** 25-30 images with 6-9 configurations (~120 MB)

### If Gallery is Too Large
1. Split into multiple galleries by theme/date
2. Compress images (85% JPG quality, max 1920px width)
3. Reduce number of configurations
4. Use CDN for deployment

---

## Contributing

This is part of the Image Description Toolkit project. Improvements welcome:

1. **Gallery features:** Better UI, search, filters
2. **Documentation:** Clarifications, examples, tutorials
3. **Scripts:** Automation, error handling, validation
4. **Accessibility:** Additional WCAG compliance improvements

---

## License

Same as Image Description Toolkit - see [LICENSE](../../LICENSE)

---

## Support

- **Main IDT Documentation:** [docs/](../../docs/)
- **Issues:** GitHub Issues for bug reports
- **Architecture Questions:** See [ARCHITECTURE.md](ARCHITECTURE.md)
- **Process Questions:** See [REPLICATION_GUIDE.md](REPLICATION_GUIDE.md)

---

**Last Updated:** October 25, 2025
