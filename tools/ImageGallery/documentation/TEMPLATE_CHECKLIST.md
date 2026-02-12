# Image Gallery Template Creation Checklist

## Source of Truth

**Reference Commit**: `6de91fb` (October 24, 2025, 9:09 PM)  
**Commit Message**: "Fix prompt text display and cleanup unnecessary ARIA attributes"  
**Working Example**: https://www.kellford.com/idtdemo/

## Critical Requirements

### 1. Base Template File

✅ **USE**: `tools/ImageGallery/index.html` at commit **6de91fb**  
❌ **DON'T USE**: Later commits that re-introduced verbose aria-labels

**Verification Command**:
```bash
git show 6de91fb:tools/ImageGallery/index.html > template.html
```

### 2. ARIA Label Check (CRITICAL)

The `loadAltTextForItem` function **MUST NOT** set aria-labels:

✅ **CORRECT** (Natural accessibility):
```javascript
async function loadAltTextForItem(index, imageName, imgElement, altTextDiv, itemElement) {
    try {
        const altText = await getAltTextForBrowser(imageName);
        
        if (altText && altText !== imageName) {
            altTextDiv.textContent = altText;
            imgElement.alt = altText;
            // NO aria-label here
        } else {
            altTextDiv.textContent = imageName;
            imgElement.alt = imageName;
            // NO aria-label here
        }
    } catch (error) {
        console.warn('Could not get alt text for', imageName, error);
        altTextDiv.textContent = imageName;
        imgElement.alt = imageName;
        // NO aria-label here
    }
}
```

❌ **WRONG** (Verbose, causes triple announcement):
```javascript
itemElement.setAttribute('aria-label', `Image ${index + 1}: ${imageName} - ${altText}`);
```

**Screen Reader Test**:
- ✅ GOOD: "Sunny urban plaza with outdoor seating... Button"
- ❌ BAD: "Image 25: photo-19500.jpg - Sunny urban plaza with outdoor seating... Button"

### 3. Directory Structure

```
[gallery-name]/
├── index.html              ← From 6de91fb template
├── images/                 ← Your images
└── jsondata/               ← JSON configs with alt_text
```

### 4. Automatic Build Process (Recommended)

**Use the build script** to automatically update index.html:

```bash
# 1. Copy template
cp -r template/ my-gallery/

# 2. Add images to my-gallery/images/

# 3. Build (automatically updates index.html)
python build_gallery.py my-gallery/
```

The script will:
- ✅ Scan images/ directory for all images
- ✅ Update the hardcoded image array in index.html
- ✅ Verify paths are relative
- ✅ Check for JSON files
- ✅ Show deployment checklist

**No more manual image list editing!**

### 5. Manual Customizations (Optional)

#### A. Gallery Title and Header

**Line ~12** - Update page title:
```html
<title>Your Gallery Name - Image Gallery</title>
```

**Line ~964** - Update gallery header:
```html
<h1>Your Gallery Name - XX Images from [Date/Context]</h1>
```

#### B. Image List (Handled by build_gallery.py)

The image list is **automatically updated** by `build_gallery.py`. 

If you need to manually update (not recommended):
- **Line ~1991** - Update image array:
```javascript
const images = [
    'IMG_XXXX.jpg',
    'IMG_YYYY.jpg',
    // ... all your images
];
```

#### C. JSON Path Verification (Handled by build_gallery.py)

**Line ~1510** - Ensure correct path:
```javascript
const response = await fetch(`./jsondata/${jsonFilename}`);
```

**Should be**: `./jsondata/` (relative to index.html)

The `build_gallery.py` script verifies this automatically.

### 6. JSON Requirements

Each JSON file **MUST** include:
```json
{
  "workflow_name": "wf_name_provider_model_prompt_timestamp",
  "provider": "claude",
  "model": "claude-sonnet-4",
  "prompt_style": "narrative",
  "images": {
    "IMG_1234.jpg": {
      "description": "Full description text",
      "alt_text": "Short alt text for accessibility"
    }
  }
}
```

**Critical**: `alt_text` field is required for proper accessibility.

### 7. Image Requirements

- **Count**: Any number (not limited to 25 anymore!)
- **Format**: JPG, PNG, GIF, WebP (tested)
- **Names**: Automatically detected by `build_gallery.py`
  - Must be in `images/` folder
  - Should match JSON `images` keys
  - Should match alt text references

### 8. Complete Workflow

```bash
# 1. Copy template
cp -r template/ my-gallery/

# 2. Add your images
cp /path/to/images/* my-gallery/images/

# 3. Build gallery (auto-updates index.html)
python build_gallery.py my-gallery/

# 4. Optional: Customize title/header in my-gallery/index.html
# (Line ~12 for <title>, line ~964 for <h1>)

# 5. Optional: Generate descriptions if you have workflows
python generate_descriptions.py my-gallery/images/
python generate_alt_text.py my-gallery/

# 6. Rebuild to verify
python build_gallery.py my-gallery/

# 7. Test locally
cd my-gallery/
python -m http.server 8000

# 8. Deploy: Upload index.html, images/, jsondata/ to server
```

### 9. Deployment Checklist

- [ ] Ran `python build_gallery.py my-gallery/` successfully
- [ ] Build script showed "✅ Gallery build complete!"
- [ ] Updated gallery title and header (optional)
- [ ] Verified `loadAltTextForItem` has NO `aria-label` setAttribute calls
- [ ] All images in `images/` folder
- [ ] All JSON files in `jsondata/` folder (if using descriptions)
- [ ] Each JSON has `alt_text` for every image
- [ ] Tested locally in browser
- [ ] Tested with screen reader (optional but recommended)

### 10. Local Testing

```bash
# From ImageGallery directory
cd [gallery-name]/webdeploy

# Python 3
python -m http.server 8000

# Or Python 2
python -m SimpleHTTPServer 8000

# Open: http://localhost:8000
```

**Test**:
1. Gallery loads without errors
2. All 25 images display
3. Alt text appears under images
4. Description cards load
5. Model navigation works
6. No console errors

### 9. Upload Checklist

Upload entire `webdeploy/` folder contents:
- [ ] `index.html`
- [ ] `images/` folder (25 images, ~65MB)
- [ ] `jsondata/` folder (JSON files, ~165KB)

**Don't upload**:
- ❌ `production/` folder
- ❌ `descriptions/` folder with workflows
- ❌ `.md` files (README, STATUS, etc.)

### 10. Post-Upload Verification

- [ ] Gallery loads at URL
- [ ] All images display correctly
- [ ] Alt text shows under images
- [ ] Description cards populate
- [ ] Provider/model navigation works
- [ ] No console errors (F12 developer tools)
- [ ] Screen reader test: announces ONLY alt text + "Button" (no "Image #:" prefix)

## Common Issues

### Issue: Verbose aria-labels

**Symptom**: Screen reader says "Image 25: filename.jpg - alt text... Button"  
**Cause**: Using wrong template version with aria-label setAttribute  
**Fix**: Revert to 6de91fb template version

### Issue: Wrong images display

**Symptom**: Gallery shows different images than expected  
**Cause**: Hardcoded image array not updated  
**Fix**: Update image array around line 1991

### Issue: No alt text

**Symptom**: Only filenames show, no descriptions  
**Cause**: JSON missing `alt_text` field  
**Fix**: Regenerate JSON with alt text included

### Issue: JSON not loading

**Symptom**: Cards show "No description available"  
**Cause**: Wrong JSON path  
**Fix**: Verify `./jsondata/` path (relative, not absolute)

## Template Extraction Command

```bash
# Extract clean template from git
cd /path/to/Image-Description-Toolkit/tools/ImageGallery
git show 6de91fb:tools/ImageGallery/index.html > CLEAN_TEMPLATE.html

# Or use current root file (if kept in sync with 6de91fb)
cp index.html CLEAN_TEMPLATE.html
```

## Documentation References

- **ARIA Evaluation**: `ARIA_EVALUATION_OCT24.md` - Why aria-labels were removed
- **Architecture**: `ARCHITECTURE.md` - Overall gallery structure
- **Original README**: `archive/README_OLD.md` - Historical context

## Version History

- **v1** (Oct 24, 2025): Initial checklist based on cottage/europe gallery creation
- **Base Commit**: 6de91fb - ARIA cleanup and prompt text fixes
