# Content Creation Tools

Scripts and utilities for creating, building, and managing image galleries.

## 🔨 Core Tools

### build_gallery.py ⭐
**Primary automation tool** - Automatically updates image lists in index.html.

**Usage**:
```bash
python build_gallery.py ../galleries/my-gallery/
```

**What it does**:
- Scans `images/` directory for all image files
- Updates the hardcoded `images = [...]` array in `index.html`
- Verifies paths are relative
- Checks for JSON configuration files
- Shows deployment readiness

**Documentation**: See `../documentation/BUILD_GALLERY_README.md`

### generate_descriptions.py
Converts IDT workflow outputs into gallery-compatible JSON format.

**Usage**:
```bash
python generate_descriptions.py ../galleries/my-gallery/images/
```

**Requirements**: Workflow outputs in `descriptions/` directory

### generate_alt_text.py
Adds accessibility alt text to JSON configuration files.

**Usage**:
```bash
python generate_alt_text.py ../galleries/my-gallery/
```

**Note**: Run after `generate_descriptions.py`

## 🧪 Analysis Tools

### check_data_status.py
Verifies gallery data completeness and integrity.

**Usage**:
```bash
python check_data_status.py ../galleries/my-gallery/
```

### evaluate_alt_text_generation.py
Tests alt text generation quality.

**Usage**:
```bash
python evaluate_alt_text_generation.py
```

### export_analysis_data.py
Exports gallery analysis data to CSV format.

**Usage**:
```bash
python export_analysis_data.py
```

## 🪟 Windows Batch Files

### generate_all_gallery_data.bat
Full workflow automation for Windows.

### generate_alt_text.bat
Alt text generation wrapper.

### generate_test_gallery_data.bat
Test data generation.

### test_gallery.bat
Local testing helper.

## 📋 Complete Workflow

```bash
# 1. Create gallery from template
cd ../galleries/
cp -r template/ my-gallery/

# 2. Add images
cp /path/to/photos/* my-gallery/images/

# 3. Build gallery (automatic image list)
cd ../content-creation/
python build_gallery.py ../galleries/my-gallery/

# 4. Generate descriptions (if you have workflow outputs)
python generate_descriptions.py ../galleries/my-gallery/images/

# 5. Add alt text
python generate_alt_text.py ../galleries/my-gallery/

# 6. Rebuild to verify
python build_gallery.py ../galleries/my-gallery/

# 7. Test locally
cd ../galleries/my-gallery/
python -m http.server 8000
```

## 🐍 Python Dependencies

All tools require Python 3.7+. Install dependencies:

```bash
pip install -r ../requirements.txt
```

## 📖 Documentation

Detailed documentation in `../documentation/`:

- **BUILD_GALLERY_README.md** - Full build_gallery.py guide
- **TEMPLATE_CHECKLIST.md** - Complete workflow walkthrough
- **ARCHITECTURE.md** - Understanding the system

## 💡 Tips

### Before/After build_gallery.py

**Before** (manual editing):
1. Open index.html in editor
2. Find line ~1991
3. Type all image filenames by hand
4. Watch for typos
5. Time consuming and error-prone

**After** (automated):
1. Run `python build_gallery.py my-gallery/`
2. Done! ✅

### Path Issues

All tools use relative paths. Always run from the `content-creation/` directory:

```bash
# ✅ Good
cd content-creation/
python build_gallery.py ../galleries/my-gallery/

# ❌ Bad
cd galleries/my-gallery/
python ../../content-creation/build_gallery.py .
```

### Testing

Always test locally before deploying:
```bash
cd galleries/my-gallery/
python -m http.server 8000
# Open http://localhost:8000 in browser
```

## 🚀 Quick Reference

| Task | Tool | Command |
|------|------|---------|
| Update image list | build_gallery.py | `python build_gallery.py ../galleries/NAME/` |
| Create JSON from workflows | generate_descriptions.py | `python generate_descriptions.py ../galleries/NAME/images/` |
| Add alt text | generate_alt_text.py | `python generate_alt_text.py ../galleries/NAME/` |
| Verify gallery | check_data_status.py | `python check_data_status.py ../galleries/NAME/` |
| Test locally | Python web server | `python -m http.server 8000` |

## ⚡ Key Features

- ✅ **No manual editing** - build_gallery.py handles image lists
- ✅ **Automatic verification** - Checks paths, JSON, images
- ✅ **Batch processing** - Windows batch files for automation
- ✅ **Error handling** - Clear error messages and validation
- ✅ **Cross-platform** - Works on Windows, macOS, Linux
