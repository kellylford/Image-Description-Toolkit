# Image Format Support for Description Embedding

This document lists which image formats support embedding AI-generated descriptions via metadata, and identifies formats that could be supported but currently aren't.

## Currently Supported Formats

| Format | File Extensions | Embedding Method | Notes |
|--------|-----------------|------------------|-------|
| **JPEG** | .jpg, .jpeg | EXIF via piexif + XMP packet | Lossless insertion—no image re-encoding |
| **TIFF** | .tif, .tiff | IFD tags via Pillow | File is rewritten; pixel data is unchanged |
| **PNG** | .png | tEXt metadata chunk + XMP iTXt chunk | Preserves existing text chunks; standardized metadata structure |
| **WebP** | .webp | EXIF blob | Requires re-save at quality 95 or lossless setting |
| **HEIC/HEIF** | .heic, .heif | Convert → JPEG | Original is left unmodified; conversion happens in copy workflow |

### Embedding Locations

- **JPEG**: `EXIF UserComment` and XMP `dc:description`
- **TIFF**: `ImageDescription` tag (270) and `XPComment` tag (40092)
- **PNG**: `tEXt` chunk key `Description`, plus XMP `dc:description` in an `XML:com.adobe.xmp` iTXt chunk
- **WebP**: `EXIF UserComment`
- **HEIC/HEIF**: Converted to JPEG, then embedded using JPEG method

TIFF cannot reuse the JPEG writer: TIFF keeps its metadata in the IFD, and injecting a
JPEG APP1 segment overwrites the byte-order magic and leaves an unopenable file. This was
a live bug until the format dispatcher in `idt_core/embedder.py` gained a TIFF branch.

### Which Windows Explorer Column Shows the Description

Windows maps the underlying tags onto its own property names, and the mapping differs by
format. Measured on Windows 11 via the shell property system, and pinned by
`pytest_tests/unit/test_embedded_metadata_visibility.py`:

| Format | "Comments" column | "Title" column |
|--------|-------------------|----------------|
| **JPEG** | ✓ (from EXIF UserComment) | ✓ (from XMP `dc:description`) |
| **PNG** | ✗ — PNG has no EXIF | ✓ (from the XMP iTXt chunk) |
| **WebP** | ✓ (from EXIF UserComment) | ✗ — no XMP is written |
| **TIFF** | ✓ (from XPComment) | ✓ (from ImageDescription) |

So **Comments** is the right column for JPEG and WebP, and PNG users need **Title** instead.
The earlier claim that Windows shows nothing at all for PNG was wrong: Windows does read the
XMP packet, it just does not surface it under "Comments".

See [USER_GUIDE.md](USER_GUIDE.md) → *Embedding Descriptions into Images* for the keyboard
steps to switch a column on, and for the macOS equivalents.

---

## Formats That DON'T Support Embedding

| Format | Why Not | Likelihood of Support |
|--------|---------|----------------------|
| **BMP** | No standardized metadata structure; pixel-data-only format | Low |
| **GIF** | No metadata standard (predates EXIF); animated variant adds complexity | Low |
| **TARGA** (.tga) | No standard metadata support | Very Low |
| **ICO** | Icon format; no metadata structure | Very Low |
| **CUR** | Cursor format; no metadata structure | Very Low |

### Why These Formats Lack Support

Older/Legacy Formats (BMP, GIF, TARGA, ICO, CUR):
- Designed before standardized metadata (EXIF, XMP) existed
- No defined metadata containers in their specs
- Minimal modern adoption for new workflows

---

## Formats Worth Considering for Future Support

### **AVIF** (.avif)

**Status**: Modern codec gaining adoption (Chrome, Firefox, Edge; Apple added in iOS 17)

**Pros**:
- Better compression than JPEG/PNG
- Increasingly used in web workflows
- Supports EXIF metadata in theory

**Cons**:
- Library support immature (Pillow gained basic support only in 2022)
- Limited EXIF library support for writing; piexif doesn't handle AVIF natively
- Would require adding a new dependency or custom implementation
- User adoption still ramping

**Recommendation**: Monitor adoption over next 12–18 months. Revisit if AVIF becomes dominant in user workflows. For now, users can export AVIF → PNG if they need metadata.

---

### **JPEG XL** (.jxl)

**Status**: Newer codec (2021); limited adoption outside specialized use cases

**Pros**:
- Excellent compression
- Native support for XMP, EXIF
- Lossless/lossy options

**Cons**:
- Very limited browser/OS support
- No native Pillow support
- Virtually no user demand yet
- Niche use case

**Recommendation**: Not worth implementing. Revisit only if it becomes mainstream (which is unlikely in the near term).

---

### **HEIC/HEIF (Direct Writing)**

**Status**: Currently supported via conversion to JPEG

**Pros**:
- Would preserve original codec
- Some libraries (Pillow, piexif) have read support
- Native on macOS/iOS

**Cons**:
- Direct write support is limited and unreliable
- Current workaround (convert to JPEG) is simple, safe, and predictable
- Would add complexity for marginal benefit
- Users on macOS typically re-download photos as JPEG anyway

**Recommendation**: Keep conversion-to-JPEG approach. Direct write adds risk for minimal user benefit.

---

## Verifying Embedded Metadata

If you need to confirm that descriptions were successfully embedded:

| Format | Method | Command |
|--------|--------|---------|
| **JPEG** | Windows Properties → Details → Comments or Title | ✓ Works natively |
| **PNG** | Windows Properties → Details → Title | ✓ Works natively (not under Comments) |
| **TIFF** | Windows Properties → Details → Comments or Title | ✓ Works natively |
| **WebP** | Windows Properties → Details → Comments | ✓ Works natively |
| **All formats** | macOS | `mdls -name kMDItemDescription file` |
| **All formats** | Python | `from PIL import Image; img = Image.open(path); print(img.text.get('Description'))` |

---

## Summary

**No new formats are critical additions today.** The current support (JPEG, PNG, WebP, TIFF) covers:
- ✅ Universal use cases (JPEG, PNG)
- ✅ Modern workflows (WebP)
- ✅ Professional/archival (TIFF)
- ✅ Apple ecosystem (HEIC → JPEG)

**Only revisit if:**
1. User requests come in for a specific format
2. That format's tooling/adoption reaches critical mass (unlikely for AVIF in the next 1–2 years)
3. A high-value use case emerges (e.g., professional archival switching to JPEG XL)

For now, the existing format coverage is sufficient and well-maintained.

**Note on PNG verification:** PNG descriptions do not appear under Windows' "Comments" property, only under "Title". If Comments looks empty for a PNG, that is the expected mapping, not a failed embed.
