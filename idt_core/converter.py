"""
Image loading and format conversion.
All HEIC conversion is done in memory — nothing is written to the source directory.
When a persistent JPEG copy is needed (for .idt/ storage), callers use save_heic_copy().
"""
from __future__ import annotations

import io
from pathlib import Path

MIME_TYPES: dict[str, str] = {
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png":  "image/png",
    ".webp": "image/webp",
    ".gif":  "image/gif",
    ".tiff": "image/tiff",
    ".tif":  "image/tiff",
    ".bmp":  "image/jpeg",   # converted on the fly
    ".heic": "image/jpeg",   # converted on the fly
    ".heif": "image/jpeg",   # converted on the fly
}

# Formats that need to be converted before sending to an API
_NEEDS_CONVERSION = frozenset({".heic", ".heif", ".bmp", ".tiff", ".tif"})


def load_for_api(path: Path) -> tuple[bytes, str]:
    """
    Load an image as bytes ready for an AI provider API call.
    HEIC/HEIF and BMP are converted to JPEG in memory.
    TIFF is also converted because several cloud providers reject it.
    Returns (image_bytes, mime_type).
    """
    suffix = path.suffix.lower()
    if suffix in (".heic", ".heif"):
        return _heic_to_jpeg_bytes(path)
    if suffix in (".bmp", ".tiff", ".tif"):
        return _pil_to_jpeg_bytes(path)
    with open(path, "rb") as f:
        data = f.read()
    return data, MIME_TYPES.get(suffix, "image/jpeg")


def save_heic_copy(source: Path, dest_dir: Path) -> Path:
    """
    Convert a HEIC/HEIF file to JPEG and save it in dest_dir.
    dest_dir should be a path inside the .idt/ mirror — never the source directory.
    Returns the path to the saved JPEG.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    jpeg_path = dest_dir / source.with_suffix(".jpg").name
    img_bytes, _ = _heic_to_jpeg_bytes(source)
    jpeg_path.write_bytes(img_bytes)
    return jpeg_path


def _heic_to_jpeg_bytes(path: Path) -> tuple[bytes, str]:
    try:
        import pillow_heif
        from PIL import Image
    except ImportError:
        raise ImportError(
            "pillow-heif is required for HEIC/HEIF support: pip install pillow-heif"
        )
    pillow_heif.register_heif_opener()
    img = Image.open(path).convert("RGB")
    return _pil_image_to_jpeg_bytes(img)


def _pil_to_jpeg_bytes(path: Path) -> tuple[bytes, str]:
    from PIL import Image
    img = Image.open(path).convert("RGB")
    return _pil_image_to_jpeg_bytes(img)


def _pil_image_to_jpeg_bytes(img) -> tuple[bytes, str]:
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=92, optimize=True)
    return buf.getvalue(), "image/jpeg"
