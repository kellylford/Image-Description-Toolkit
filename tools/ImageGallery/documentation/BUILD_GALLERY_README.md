# Build Gallery Script

Automatically builds and prepares image galleries for deployment.

## Purpose

Eliminates the need to manually update the hardcoded image list in `index.html`. The script:

- ✅ Scans `images/` directory for image files
- ✅ Automatically updates the image array in `index.html`
- ✅ Verifies paths are relative (not absolute)
- ✅ Checks for JSON configuration files
- ✅ Validates that images match JSON entries
- ✅ Provides deployment checklist

## Usage

### Basic Usage

```bash
# Build a gallery (from ImageGallery root directory)
python build_gallery.py path/to/gallery/

# Examples
python build_gallery.py europe/webdeploy/
python build_gallery.py my-new-gallery/
python build_gallery.py .  # Current directory
```

### Complete Workflow

```bash
# 1. Create a new gallery from template
cp -r template/ my-gallery/

# 2. Add your images
cp /path/to/photos/*.jpg my-gallery/images/

# 3. Build the gallery
python build_gallery.py my-gallery/

# 4. (Optional) Customize title/header in my-gallery/index.html

# 5. (Optional) Generate descriptions
python generate_descriptions.py my-gallery/images/
python generate_alt_text.py my-gallery/

# 6. Rebuild to verify JSON
python build_gallery.py my-gallery/

# 7. Test locally
cd my-gallery/
python -m http.server 8000
```

## What It Does

### Step 1: Scan Images
Finds all image files in the `images/` directory:
- Supported formats: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`
- Sorts alphabetically for consistent ordering
- Reports count and first 5 filenames

### Step 2: Update index.html
Updates the hardcoded `images = [...]` array in `index.html`:
- Handles `const images`, `let images`, or `images` declarations
- Maintains proper indentation
- Replaces entire array with discovered files

**Before (manual)**:
```javascript
images = [
    'IMG_4276.jpg',
    'IMG_4277.jpg',
    // ... had to type all 25 manually!
];
```

**After (automatic)**:
```javascript
images = [
    'IMG_4010.jpg',
    'IMG_4011.jpg',
    // ... automatically detected!
];
```

### Step 3: Verify JSON Files
If `jsondata/` directory exists:
- Counts JSON configuration files
- Checks which images have descriptions
- Warns if images are missing from JSON
- Suggests running `generate_descriptions.py` if needed

### Step 4: Verify Paths
Checks that `index.html` uses relative paths:
- ✅ Good: `./jsondata/`, `./images/`
- ❌ Bad: `/absolute/path/jsondata/`, `C:\Windows\paths`
- Warns if absolute paths detected

## Output Example

```
🔨 Building gallery: europe
   Location: C:\...\ImageGallery\europe\webdeploy

📁 Step 1: Scanning images directory...
   ✅ Found 25 images
      - IMG_4010.jpg
      - IMG_4011.jpg
      ... and 23 more

📝 Step 2: Updating index.html with image list...
   ✅ Updated image array in index.html

🔍 Step 3: Verifying JSON files...
   📊 Found 5 JSON config files
   📸 JSON files reference 25 images
   ✅ All images have JSON entries

🔗 Step 4: Verifying paths in index.html...
   ✅ Paths are relative (good for deployment)

============================================================
✅ Gallery build complete!

📦 Ready for deployment:
   - 25 images in images/
   - Image list updated in index.html
   - 5 JSON config files

🧪 Test locally:
   cd C:\...\europe\webdeploy
   python -m http.server 8000
   Open: http://localhost:8000

🚀 Deploy:
   Upload index.html, images/, and jsondata/ to your server
============================================================
```

## Error Handling

### No Images Found
```
⚠️  No images found in images/
   Add your images to the images/ directory first
```
**Fix**: Add image files to `images/` directory

### No index.html Found
```
❌ Error: index.html not found
   Make sure you're in a gallery directory (copied from template/)
```
**Fix**: Copy from template or check directory path

### Can't Find Image Array
```
❌ Error: Could not find 'images = [...]' in index.html
   Make sure index.html has the hardcoded image array
```
**Fix**: Use the template index.html (from 6de91fb commit)

### Images Missing from JSON
```
⚠️  Warning: 5 images not in JSON files:
      - IMG_4010.jpg
      - IMG_4011.jpg
      ...
   💡 Run generate_descriptions.py to create descriptions
```
**Fix**: Run `python generate_descriptions.py path/to/images/`

## Benefits

### Before (Manual Process)
1. Copy template
2. Add images
3. **Open index.html in editor**
4. **Find line ~1991**
5. **Manually type all 25 image filenames**
6. **Check for typos**
7. **Ensure proper formatting**
8. Test and deploy

**Pain points**:
- ❌ Manual typing = errors
- ❌ Easy to miss images
- ❌ Have to count/verify
- ❌ Formatting issues
- ❌ Time consuming

### After (Automated Process)
1. Copy template
2. Add images
3. **Run `python build_gallery.py my-gallery/`**
4. Test and deploy

**Benefits**:
- ✅ Zero typos
- ✅ Never miss images
- ✅ Automatic verification
- ✅ Perfect formatting
- ✅ Fast and reliable

## Integration with Other Scripts

### With generate_descriptions.py
```bash
# 1. Build gallery to get image list
python build_gallery.py my-gallery/

# 2. Generate descriptions (uses workflow outputs)
python generate_descriptions.py my-gallery/images/

# 3. Add alt text
python generate_alt_text.py my-gallery/

# 4. Rebuild to verify
python build_gallery.py my-gallery/
```

### With Workflow Automation
```bash
# Run IDT workflows
idt workflow my-gallery/images/ --provider claude --model claude-sonnet-4

# Build gallery automatically
python build_gallery.py my-gallery/
```

## Technical Details

- **Language**: Python 3
- **Dependencies**: Standard library only (os, sys, json, re, pathlib)
- **Modifies**: Only `index.html` (updates image array)
- **Safe**: Reads-only for images/ and jsondata/

## See Also

- **TEMPLATE_CHECKLIST.md** - Complete gallery creation guide
- **template/README.md** - Template usage instructions
- **generate_descriptions.py** - Create JSON from workflows
- **generate_alt_text.py** - Add accessibility alt text

## Version History

- **v1.0** (Oct 25, 2025): Initial release
  - Automatic image list generation
  - Path verification
  - JSON validation
  - Deployment checklist
