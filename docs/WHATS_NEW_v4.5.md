# What's New in v4.5

**Release Date:** 2026-06-18  
**Previous Version:** v4.0.0  
**Branch:** v4.5  
**Status:** In Development

---

## Major Features

### 1. Embed AI Descriptions into Image Metadata

AI-generated descriptions can now be **permanently embedded into image files** so the description travels with the image when it is copied, shared, attached to an email, or posted online. Any application that reads standard image metadata can see the description — no IDT workspace or sidecar file required.

Previously, descriptions were stored in IDT's own sidecar files and workspace files. This is still how IDT manages and organizes descriptions internally. Embedding is the step that makes descriptions durable and portable: once embedded, the description is part of the image file itself.

#### What Gets Written

| Format | Metadata Field |
|--------|---------------|
| JPEG, TIFF | EXIF `Image Description` (standard caption field) + attribution in `User Comment` |
| PNG | `tEXt` chunk, key `Description` |
| WebP | EXIF `Image Description` |
| HEIC | Copy mode: produces a JPEG copy with description embedded |

JPEG and TIFF embedding is **lossless** — the image pixel data is not re-encoded or recompressed.

When an image has more than one AI description, the most recent description is embedded.

---

### How to Use It: ImageDescriber (GUI)

1. Open a workspace with described images.
2. Choose **File → Embed Descriptions into Images…**
3. In the dialog, choose a write mode:

   **Create copies with descriptions embedded** *(recommended — default)*
   Copies of your images are written to a folder you choose. Your originals are not modified.
   Default output folder: `~/Pictures/IDT_Embedded`

   **Embed into original files**
   Writes the description directly into each original. Requires checking the confirmation box before the Embed button becomes active.

4. Click **Embed**. A summary shows how many were embedded, any skipped files (unsupported format or file not found), and any errors. In copy mode, you are offered the option to open the output folder when done.

---

### How to Use It: CLI (`idt embed`)

```bash
# Create copies with descriptions embedded (safe default)
idt embed wf_2026-06-18_143022_claude_Detailed/

# Specify your own output folder
idt embed wf_2026-06-18_143022_claude_Detailed/ --output-dir ~/Pictures/WithDescriptions/

# Preview what would happen without writing anything
idt embed wf_2026-06-18_143022_claude_Detailed/ --dry-run

# Embed directly into the original files
idt embed wf_2026-06-18_143022_claude_Detailed/ --in-place
```

The CLI reads descriptions and original file paths from the workflow's `descriptions/` folder. The originals are the files you ran the workflow on — not any copies IDT made during processing.

---

### Verifying the Embedded Description

**macOS Finder:** Select the image, press `Cmd+I` (Get Info). The description appears under **Comments**.

**macOS Preview:** Open the image, choose **Tools → Show Inspector**, then the **EXIF** tab. Look for `Image Description`.

**Windows File Explorer:** Right-click the image → Properties → Details tab. Look for **Description** under the Image section.

**Lightroom Classic / Adobe Bridge:** The description appears in the metadata panel under `Caption` or `Description` (IPTC/EXIF overlay).

---

### Design Notes

**Copy mode is the default.** Modifying original photo files is a destructive operation. IDT requires you to opt in explicitly — either by checking a box in the GUI or passing `--in-place` on the CLI.

**JPEG embedding is lossless.** IDT uses `piexif.insert()` to update the EXIF section of a JPEG file without touching the image data. The compressed pixel stream is not re-encoded and there is no quality loss.

**True originals, not IDT copies.** The CLI resolves which file to embed into using `file_path_mapping.json` — a map IDT writes during every workflow run that links each processed copy back to the original source file. The GUI uses each workspace item's stored file path, which is always the original on-disk location.

**HEIC support in copy mode.** HEIC files cannot be reliably written to directly. In copy mode, IDT converts the HEIC to a JPEG copy (the same conversion the existing "Convert HEIC Files" menu action uses) and embeds the description into that copy.

---

## Other Changes in v4.5

### New Models
- Added Qwen3-VL MLX models for Apple Silicon Macs
- Qwen3-VL-4B is now the default model on Mac

### Dependency Updates
- Minimum versions bumped: `ollama`, `pillow-heif`, `anthropic`, `timm`, `opencv-python`

---

## Coming in a Future Release

- **XMP `dc:description`** — embeds descriptions in the XMP sidecar / packet that Lightroom, Apple Photos, and other professional photo apps read as the primary description field. Requires `exiftool` or `pyexiv2`.
- **Per-image embed button** in the ImageDescriber viewer panel
- **Automatic embedding during workflow run** via an `--embed-metadata` flag
