# Feature Spec: Embed AI Descriptions into Image Metadata

**Date:** 2026-06-18  
**Branch:** v4.5  
**Status:** Implemented

---

## Background

IDT generates AI descriptions stored as sidecar text files (`descriptions/image_descriptions.txt` for CLI workflows) and in `.idw` workspace files (GUI). The user wanted descriptions permanently embedded in image file metadata so they travel with the image when copied, shared, or posted — without requiring the recipient to have IDT or know about the sidecar file.

---

## Goal

Attach AI-generated descriptions to the **true original image files** as standard metadata fields (EXIF, PNG tEXt chunk) so any application that can read image metadata can see the description. Whether a given platform surfaces those fields to the user is secondary; the primary goal is the association.

Support Windows and macOS.

---

## How Each Surface Tracks Originals

**GUI (ImageDescriber):** `ImageItem.file_path` in the `.idw` workspace is the user's true original on-disk path. Images are never copied to a processing directory — only transient files for AI API calls are created in `tempfile.gettempdir()` and immediately deleted. The stored `file_path` is the real source.

**CLI (idt workflow):** Images are copied to `temp_combined_images/` for processing. `descriptions/file_path_mapping.json` (written by `workflow.py` lines 2135–2152) maps every workflow copy → original absolute path. This is the key for resolving true originals.

**HEIC exception (GUI):** If the user ran "Convert HEIC Files…", the workspace has a derived JPEG sibling as a separate `ImageItem` with no link back to the HEIC. If that JPEG is the described item, its `file_path` IS the embedable file. If the HEIC item itself was described, we cannot write back to HEIC directly.

---

## Default Behavior: Make Copies (Originals Untouched)

**Copy mode (default):** For each image with a description, copy the original file to an output directory and embed the description into the copy. User's originals are never modified.

**In-place mode (explicit opt-in):** Embed directly into the original files. GUI requires a confirmation dialog with a checkbox; CLI requires `--in-place` flag. This is available but not the default.

---

## Metadata Fields by Format

| Format | Field Written | Library | Notes |
|--------|--------------|---------|-------|
| JPEG, TIFF | EXIF `ImageDescription` (tag 0x010e) + `UserComment` | piexif (already installed) | Lossless — uses `piexif.insert()`, no image re-encoding |
| PNG | `tEXt` chunk key `"Description"` | Pillow PngInfo (already installed) | Existing tEXt chunks preserved |
| WebP | EXIF blob via `save(..., exif=)` | Pillow (already installed) | Re-encodes at quality=95 or lossless |
| HEIC | Copy mode → produce JPEG copy | Pillow + pillow-heif | In-place skipped |

XMP (`dc:description`) deferred — requires `exiftool` subprocess or `pyexiv2`, neither currently installed. EXIF `ImageDescription` is the standard field and is already read by `scripts/metadata_extractor.py` (line 166).

When multiple descriptions exist for one image, the most recent is embedded.

---

## Files Created / Modified

### `scripts/exif_embedder.py` (modified)
- Added `UnsupportedFormatError` exception class
- Added `embed_ai_description(image_path, description, model, timestamp)` public method
- Added `_embed_jpeg_tiff()` — lossless via `piexif.insert()`
- Added `_embed_png()` — Pillow PngInfo tEXt chunk
- Added `_embed_webp()` — Pillow re-save with EXIF blob
- Added `piexif.helper` import

### `scripts/embed_descriptions.py` (new)
- `EmbedDescriptions` class with two entry points:
  - `embed_from_workflow_dir(workflow_dir, output_dir, in_place, dry_run)` — reads `image_descriptions.txt` + `file_path_mapping.json`
  - `embed_from_workspace(workspace_data, output_dir, in_place, dry_run)` — reads deserialized `.idw` dict
- `EmbedResult` dataclass: `embedded`, `skipped_format`, `skipped_no_original`, `errors`
- `_resolve_original()` matching strategy: exact key → basename → filepath fallback
- `_convert_heic_and_embed()` for HEIC copy-mode path
- Standalone `main()` for direct CLI use
- Frozen/dev dual import pattern throughout

### `idt/idt_cli.py` (modified)
- Added `elif command == 'embed':` routing block (after `descriptions-to-html`, before `convert-images`)
- Added `embed` to the COMMANDS list in help text
- Added `EMBED OPTIONS` section in help text
- Added embed examples in EXAMPLES section

### `imagedescriber/dialogs_wx.py` (modified)
- Appended `EmbedDescriptionsDialog(wx.Dialog)` class at end of file
- Dialog has: intro text, mode radio buttons (copy/in-place), confirmation checkbox for in-place, output folder picker with Browse button, Embed/Cancel buttons

### `imagedescriber/imagedescriber_wx.py` (modified)
- Added `"Embed Descriptions into Images..."` to File menu (after Export Descriptions)
- Added `on_embed_descriptions()` handler
- Added `EmbedDescriptionsDialog` to all three import blocks (frozen, relative dev, absolute dev)

---

## Key Design Decisions

1. **Copy mode as default** — protects user's original photos from unexpected modification
2. **`piexif.insert()` for JPEG** — lossless metadata update, no image quality loss
3. **GUI `ImageItem.file_path` is the true original** — no new tracking field needed; the GUI never copies user images
4. **CLI uses `file_path_mapping.json`** — already produced by every workflow run
5. **`embed_from_workspace` accepts a dict** — decouples `embed_descriptions.py` from `data_models.py`, works in frozen exe mode

---

## Verification Steps

```bash
# Syntax check
python -m py_compile scripts/exif_embedder.py
python -m py_compile scripts/embed_descriptions.py
python -m py_compile idt/idt_cli.py
python -m py_compile imagedescriber/dialogs_wx.py
python -m py_compile imagedescriber/imagedescriber_wx.py

# Unit tests
pytest pytest_tests/ -k embed

# CLI smoke test
idt embed wf_*/  --dry-run
idt embed wf_*/  --output-dir ~/Desktop/test_embedded

# GUI: File > Embed Descriptions into Images...
# Test both copy mode and in-place mode
```

---

## Out of Scope (Future Work)

- XMP `dc:description` for Lightroom/Apple Photos compatibility (requires exiftool or pyexiv2)
- Per-image "Embed" button in the viewer panel
- Automatic embedding during workflow run (`--embed-metadata` flag)
- PyInstaller `.spec` changes (new module in `scripts/` is covered by existing hidden imports)
