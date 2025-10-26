# IDT Interactive Demo Gallery

An interactive web-based gallery that showcases the Image Description Toolkit's capabilities by allowing users to compare AI-generated image descriptions across different providers, models, and prompt styles.

---

## Quick Start

### View Existing Gallery

```bash
cd tools/ImageGallery
python -m http.server 8082
# Open browser to: http://localhost:8082
```

### Create Your Own Gallery

**See [REPLICATION_GUIDE.md](REPLICATION_GUIDE.md) for detailed instructions.**

Quick summary (30-45 minutes for 25 images):
1. Create project directory and add 15-30 images
2. Run 4 IDT workflows (narrative, colorful, technical, detailed)
3. Generate JSON files from workflows
4. Add accessibility alt text
5. Configure and deploy

---

## Documentation Map

| Document | Purpose | Who Should Read |
|----------|---------|-----------------|
| **README.md** | Quick start, overview | Everyone (start here) |
| **[REPLICATION_GUIDE.md](REPLICATION_GUIDE.md)** | Step-by-step gallery creation | Gallery creators |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | Technical details, troubleshooting | Developers, advanced users |
| **[SETUP_GUIDE.md](SETUP_GUIDE.md)** | Deployment instructions | System administrators |

**Archived Documentation:**
- [archive/GALLERY_DATA_CHECKLIST.md](archive/GALLERY_DATA_CHECKLIST.md) - Workflow tracking checklist
- [archive/README_ALT_TEXT.md](archive/README_ALT_TEXT.md) - Alt text implementation details

---

## Gallery Features

### User Features
- **Two View Modes:**
  - **Image Browser:** Browse images with descriptions
  - **Description Explorer:** Search/filter by description text
  
- **Multi-Provider Comparison:**
  - Claude (Haiku, Opus, Sonnet)
  - OpenAI (GPT-4o, GPT-4o-mini)
  - Ollama (Llava, Qwen, Gemma, etc.)
  
- **Multiple Prompt Styles:**
  - Narrative (balanced, story-like)
  - Colorful (artistic, vibrant)
  - Technical (analytical, detailed)
  - Detailed (comprehensive, thorough)
  
- **Accessibility:**
  - WCAG 2.2 AA compliant
  - Keyboard navigation (arrows, Tab, Enter)
  - Screen reader support
  - Alt text on all images

### Gallery Capabilities
- Side-by-side comparison of different AI descriptions
- Filter by provider, model, or prompt style
- Responsive design (desktop and mobile)
- Works offline (static files)
- No backend required

---

## Architecture Overview

```
Gallery Directory Structure:
├── index.html              # Web interface
├── images/                 # Image files (JPG)
├── gallery-data/           # JSON files for gallery (DEPLOY THIS)
│   ├── index.json         # Configuration list
│   └── *.json             # One per provider+model+prompt
├── descriptions/           # Workflow outputs (KEEP LOCAL)
│   └── wf_*/              # Logs, temp files (~130MB)
└── generate_*.py          # Data generation scripts
```

**Data Flow:**
```
Images → IDT Workflows → descriptions/wf_*/ → JSON Files → Gallery
                         (~130MB, keep local)  (~150KB, deploy)
```

**Critical:** Only deploy `index.html`, `images/`, and `gallery-data/` to web server. The `descriptions/wf_*/` directories are development artifacts (logs, temp files) not needed by the gallery.

**See [ARCHITECTURE.md](ARCHITECTURE.md) for complete technical details.**

---

## Requirements

### To View Gallery
- Modern web browser (Chrome, Firefox, Safari, Edge)
- HTTP server (Python's `http.server` works great)
- **Note:** Won't work with `file://` protocol due to CORS

### To Create Gallery
- **IDT:** Image Description Toolkit (`idt.exe`)
- **Python 3.x** with `requests` package
- **API Keys:** Claude and/or OpenAI (depending on providers)
- **Images:** 15-30 JPG files recommended
- **Time:** 30-45 minutes for complete gallery

---

## Common Tasks

### Add New Images
```bash
# 1. Copy images to images/ directory
cp /path/to/new/*.jpg images/

# 2. Re-run workflows
c:/idt/idt.exe workflow images/ --provider claude --model MODEL --prompt-style STYLE ...

# 3. Regenerate JSON
python generate_descriptions.py --descriptions-dir descriptions/ --output-dir gallery-data/

# 4. Regenerate alt text
python generate_alt_text.py --jsondata-dir gallery-data/
```

### Add New Model Configuration
```bash
# 1. Run workflow with new model
c:/idt/idt.exe workflow images/ --provider PROVIDER --model NEW_MODEL --prompt-style STYLE ...

# 2. Regenerate JSON (will include new config)
python generate_descriptions.py --descriptions-dir descriptions/ --output-dir gallery-data/

# Gallery automatically shows new configuration
```

### Export Analysis Data
```bash
# Extract workflow metrics (timing, tokens, costs)
python export_analysis_data.py \
  --descriptions-dir descriptions \
  --output-dir analysis \
  --pattern WORKFLOW_NAME

# Creates CSV with per-image data
# Use for cost analysis, performance benchmarking
```

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
