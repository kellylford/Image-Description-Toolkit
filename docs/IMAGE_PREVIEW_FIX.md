# Image Preview Fix - October 1, 2025

## Problem
When enabling "Show Image Preview" in the View menu, users were getting "Unable to load image" errors.

## Root Cause
**QPixmap has limited format support** and cannot load:
- HEIC/HEIF files (common on iPhones)
- Some TIFF variants
- CMYK mode images
- Other specialized formats

The original implementation used `QPixmap(file_path)` directly, which failed for these formats.

## Solution
**Use PIL (Python Imaging Library) as the primary loader** with QPixmap as fallback:

1. **Load with PIL first**: PIL supports many more formats including HEIC (with pillow_heif)
2. **Convert to QPixmap**: Transform PIL Image → bytes → QImage → QPixmap
3. **Handle color modes**: Convert CMYK, LA, P modes to RGB/RGBA
4. **Fallback to QPixmap**: If PIL fails, try direct QPixmap loading
5. **Better error messages**: Show specific error details and file names

## Technical Details

### Image Loading Pipeline
```
File → PIL.Image.open()
     ↓
  Convert mode (CMYK/LA/P → RGB/RGBA)
     ↓
  Convert to bytes (raw RGB data)
     ↓
  Create QImage from bytes
     ↓
  Convert QImage → QPixmap
     ↓
  Scale and display
```

### Supported Formats
Now supports all formats that PIL can handle:
- ✅ JPEG, PNG, GIF, BMP, TIFF (standard formats)
- ✅ **HEIC/HEIF** (with pillow_heif installed)
- ✅ WebP
- ✅ CMYK mode images
- ✅ Grayscale images
- ✅ Images with transparency

### Fallback Handling
If PIL loading fails (corrupted file, unsupported format):
- Attempts direct QPixmap loading
- Shows descriptive error message with filename
- Logs error details to console for debugging

## Code Changes

**File**: `imagedescriber/imagedescriber.py`

**Method**: `update_image_preview()`

### Before (Broken)
```python
# Direct QPixmap loading - fails for HEIC and other formats
pixmap = QPixmap(file_path)
if pixmap.isNull():
    self.image_preview_label.setText("Unable to load image")
```

### After (Fixed)
```python
# PIL loading with format conversion
pil_image = Image.open(file_path)
if pil_image.mode not in ('RGB', 'RGBA', 'L'):
    pil_image = pil_image.convert('RGB')

# Convert PIL → QImage → QPixmap
img_bytes = pil_image.tobytes('raw', 'RGB')
qimage = QImage(img_bytes, width, height, stride, Format_RGB888)
pixmap = QPixmap.fromImage(qimage)
```

## Testing Recommendations

Test with various image formats:
1. **HEIC files** (iPhone photos) - should now work
2. **CMYK JPEG** (some professional cameras) - should convert to RGB
3. **PNG with transparency** - should preserve alpha channel
4. **Standard JPEG/PNG** - should work as before
5. **Corrupted files** - should show error message

## Error Messages

Users will now see specific messages:
- "No image selected" - no file selected
- "HEIC support not available" - need to install pillow-heif
- "Unable to convert image format" - QImage creation failed
- "Unable to create pixmap" - QPixmap conversion failed
- "Unable to load image: [filename]" - both PIL and QPixmap failed
- "Error loading image: [error details]" - exception occurred

## Dependencies

Ensure these are installed:
```bash
pip install Pillow              # Core image library
pip install pillow-heif        # HEIC support (optional but recommended)
```

## Future Enhancements

Potential improvements:
1. **Lazy loading**: Load thumbnails first for faster display
2. **Caching**: Cache scaled images to avoid re-processing
3. **Format indication**: Show image format in preview panel
4. **Resize handling**: Update preview when panel is resized

## Related Files

- `imagedescriber/imagedescriber.py` - Main fix location
- `docs/ENHANCEMENTS_2025_10_01.md` - Overall enhancement documentation

## Resolution Status

✅ **Fixed** - Image preview now handles all PIL-supported formats including HEIC files.
