"""
Embedder — writes AI descriptions into image metadata copies.

Source files are NEVER modified. Copies go to <project>.idt/embedded/,
mirroring the source directory structure.

For JPEG (the primary format):
  - EXIF UserComment   → Windows "Comments" column in Explorer
  - XMP dc:description → Apple Photos (caption), Lightroom Description,
                         macOS Spotlight (kMDItemDescription), modern tools

For PNG:
  - tEXt chunk "Description"  → basic description
  - iTXt chunk "XML:com.adobe.xmp" → XMP dc:description for modern apps

For WebP:
  - EXIF UserComment + XMP dc:description

HEIC originals in copy mode use the .idt/ JPEG conversion if available;
otherwise they are converted fresh and that copy is embedded into.
"""
from __future__ import annotations

import html as _html
import re
import shutil
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .image_item import ImageItem
from .project import Project
from .scanner import is_heic
from .converter import save_heic_copy, load_for_api

# ------------------------------------------------------------------ #
# Namespace constants                                                  #
# ------------------------------------------------------------------ #
_X   = "adobe:ns:meta/"
_RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
_DC  = "http://purl.org/dc/elements/1.1/"
_XML = "http://www.w3.org/XML/1998/namespace"

_XMP_JPEG_HEADER = b"http://ns.adobe.com/xap/1.0/\x00"
_EXIF_HEADER     = b"Exif\x00\x00"

# ------------------------------------------------------------------ #
# Result type                                                          #
# ------------------------------------------------------------------ #

@dataclass
class EmbedResult:
    embedded: list[Path] = field(default_factory=list)
    skipped: list[tuple[Path, str]] = field(default_factory=list)   # (path, reason)
    errors: list[tuple[Path, str]] = field(default_factory=list)    # (path, message)
    dry_run: bool = False

    @property
    def total(self) -> int:
        return len(self.embedded) + len(self.skipped) + len(self.errors)


# ------------------------------------------------------------------ #
# Public API                                                           #
# ------------------------------------------------------------------ #

def embed_image_file(
    source: Path,
    description: str,
    dest: Path,
    *,
    overwrite: bool = True,
) -> None:
    """
    Copy *source* to *dest* and embed *description* into the metadata of the copy.

    Works without a Project object — suitable for the GUI workspace model or
    any context where the caller already knows the source and destination paths.

    Supported formats: JPEG/TIFF (.jpg .jpeg .tif .tiff),
                       PNG (.png), WebP (.webp).
    Other formats: copy is made but no metadata is written.

    Raises RuntimeError if the copy or embed fails.
    """
    if dest == source:
        # In-place mode: embed directly, no copy step
        suffix = source.suffix.lower()
        if suffix in (".jpg", ".jpeg", ".tif", ".tiff"):
            _embed_jpeg(source, description)
        elif suffix == ".png":
            _embed_png(source, description)
        elif suffix == ".webp":
            _embed_webp(source, description)
        return

    if not overwrite and dest.exists():
        raise FileExistsError(f"Destination already exists: {dest}")

    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)

    suffix = dest.suffix.lower()
    if suffix in (".jpg", ".jpeg", ".tif", ".tiff"):
        _embed_jpeg(dest, description)
    elif suffix == ".png":
        _embed_png(dest, description)
    elif suffix == ".webp":
        _embed_webp(dest, description)


class Embedder:
    """Copies images to .idt/embedded/ and writes description metadata into the copies."""

    def __init__(self, project: Project):
        self.project = project
        self._embedded_dir = project.idt_dir / "embedded"

    def embed_all(self, force: bool = False, dry_run: bool = False) -> EmbedResult:
        """
        Embed descriptions for all described images in the project.
        force=True: re-embed even if embedded_at is already set.
        dry_run=True: report what would happen without writing anything.
        """
        result = EmbedResult(dry_run=dry_run)
        for item in self.project.described():
            if not force and item.embedded_at:
                result.skipped.append((item.source_path, "already embedded"))
                continue
            desc = item.active_description
            if not desc:
                result.skipped.append((item.source_path, "no active description"))
                continue
            try:
                dest = self._embed_one(item, desc.text, dry_run)
                result.embedded.append(dest)
                if not dry_run:
                    item.embedded_at = datetime.now(timezone.utc).isoformat()
                    item.embedded_path = dest
                    item.save()
            except Exception as exc:
                result.errors.append((item.source_path, str(exc)))
        return result

    def _embed_one(self, item: ImageItem, description: str, dry_run: bool) -> Path:
        """Copy the image and embed the description. Returns destination path."""
        source = item.source_path
        suffix = source.suffix.lower()

        # For HEIC originals, use the .idt/ JPEG copy; create it if missing
        if is_heic(source):
            if item.converted_path and item.converted_path.exists():
                work_src = item.converted_path
            else:
                if not dry_run:
                    item.converted_path = save_heic_copy(source, item.sidecar_path.parent)
                    item.save()
                    work_src = item.converted_path
                else:
                    work_src = source.with_suffix(".jpg")   # hypothetical path
            dest = self._dest_path(source).with_suffix(".jpg")
        else:
            work_src = source
            dest = self._dest_path(source)

        if dry_run:
            return dest

        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(work_src, dest)

        embed_suffix = dest.suffix.lower()
        if embed_suffix in (".jpg", ".jpeg"):
            _embed_jpeg(dest, description)
        elif embed_suffix == ".png":
            _embed_png(dest, description)
        elif embed_suffix == ".webp":
            _embed_webp(dest, description)
        # Other formats: copy is made but no metadata written (rare)

        return dest

    def _dest_path(self, source: Path) -> Path:
        """Mirror source path under .idt/embedded/."""
        rel = source.relative_to(self.project.source_dir)
        return self._embedded_dir / rel


# ------------------------------------------------------------------ #
# JPEG embedding                                                       #
# ------------------------------------------------------------------ #

def _embed_jpeg(path: Path, description: str) -> None:
    """Write EXIF ImageDescription + XMP dc:description into a JPEG in place."""
    data = path.read_bytes()

    # --- EXIF (lossless via piexif) ---
    try:
        import piexif
        import piexif.helper
        try:
            exif_dict = piexif.load(str(path))
        except Exception:
            exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}}
        exif_dict["Exif"][piexif.ExifIFD.UserComment] = piexif.helper.UserComment.dump(
            description, encoding="unicode"
        )
        exif_bytes = piexif.dump(exif_dict)
        piexif.insert(exif_bytes, str(path))
        # Reload after piexif writes it back
        data = path.read_bytes()
    except Exception:
        pass   # EXIF failure is non-fatal; XMP will still be written

    # --- XMP ---
    existing_xmp = _extract_xmp_from_jpeg(data)
    if existing_xmp is not None:
        xmp_str = _update_xmp_description(existing_xmp, description)
    else:
        xmp_str = _build_minimal_xmp(description)

    modified = _inject_xmp_into_jpeg(data, xmp_str)
    path.write_bytes(modified)


def _extract_xmp_from_jpeg(data: bytes) -> Optional[bytes]:
    """Return the XMP payload bytes (after the namespace header) or None."""
    i = 2  # skip SOI
    while i + 3 < len(data):
        if data[i] != 0xFF:
            break
        marker = data[i + 1]
        if marker == 0xDA:   # SOS
            break
        if marker in (0xD8, 0xD9, 0x01) or (0xD0 <= marker <= 0xD7):
            i += 2
            continue
        if i + 3 >= len(data):
            break
        length = int.from_bytes(data[i + 2: i + 4], "big")
        seg_data = data[i + 4: i + 2 + length]
        if marker == 0xE1 and seg_data.startswith(_XMP_JPEG_HEADER):
            return seg_data[len(_XMP_JPEG_HEADER):]
        i += 2 + length
    return None


def _inject_xmp_into_jpeg(jpeg_data: bytes, xmp_string: str) -> bytes:
    """Replace or insert the XMP APP1 segment in a JPEG."""
    xmp_payload = _XMP_JPEG_HEADER + xmp_string.encode("utf-8")
    seg_length = len(xmp_payload) + 2   # +2 for the length field itself
    if seg_length > 65535:
        raise ValueError(f"XMP packet too large ({seg_length} bytes; JPEG APP1 max is 65535)")
    xmp_segment = b"\xFF\xE1" + seg_length.to_bytes(2, "big") + xmp_payload

    # Scan for existing XMP APP1
    i = 2
    while i + 3 < len(jpeg_data):
        if jpeg_data[i] != 0xFF:
            break
        marker = jpeg_data[i + 1]
        if marker == 0xDA:
            break
        if marker in (0xD8, 0xD9, 0x01) or (0xD0 <= marker <= 0xD7):
            i += 2
            continue
        if i + 3 >= len(jpeg_data):
            break
        length = int.from_bytes(jpeg_data[i + 2: i + 4], "big")
        seg_end = i + 2 + length
        seg_data = jpeg_data[i + 4: seg_end]
        if marker == 0xE1 and seg_data.startswith(_XMP_JPEG_HEADER):
            # Replace existing XMP segment
            return jpeg_data[:i] + xmp_segment + jpeg_data[seg_end:]
        i = seg_end

    # No existing XMP — insert after SOI and after EXIF APP1 (if present)
    insert_at = 2
    if (len(jpeg_data) > 6
            and jpeg_data[2] == 0xFF and jpeg_data[3] == 0xE1):
        length = int.from_bytes(jpeg_data[4:6], "big")
        if jpeg_data[6:12] == _EXIF_HEADER:
            insert_at = 2 + 2 + length

    return jpeg_data[:insert_at] + xmp_segment + jpeg_data[insert_at:]


# ------------------------------------------------------------------ #
# XMP building / updating                                              #
# ------------------------------------------------------------------ #

def _build_minimal_xmp(description: str) -> str:
    """Build a minimal XMP packet with dc:description set."""
    escaped = _html.escape(description, quote=False)
    return (
        '<?xpacket begin="\xef\xbb\xbf" id="W5M0MpCehiHzreSzNTczkc9d"?>\n'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">\n'
        '  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">\n'
        '    <rdf:Description rdf:about=""\n'
        '        xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
        '      <dc:description>\n'
        '        <rdf:Alt>\n'
        f'          <rdf:li xml:lang="x-default">{escaped}</rdf:li>\n'
        '        </rdf:Alt>\n'
        '      </dc:description>\n'
        '    </rdf:Description>\n'
        '  </rdf:RDF>\n'
        '</x:xmpmeta>\n'
        '<?xpacket end="w"?>'
    )


def _wrap_xpacket(xml_content: str) -> str:
    return (
        '<?xpacket begin="\xef\xbb\xbf" id="W5M0MpCehiHzreSzNTczkc9d"?>\n'
        + xml_content
        + "\n<?xpacket end=\"w\"?>"
    )


def _update_xmp_description(xmp_payload: bytes, description: str) -> str:
    """
    Parse existing XMP bytes and set dc:description to the given text.
    Falls back to a minimal XMP packet if parsing fails.
    """
    # Register friendly prefixes before any parsing so ET uses them on output
    ET.register_namespace("x",      _X)
    ET.register_namespace("rdf",    _RDF)
    ET.register_namespace("dc",     _DC)
    ET.register_namespace("xmp",    "http://ns.adobe.com/xap/1.0/")
    ET.register_namespace("tiff",   "http://ns.adobe.com/tiff/1.0/")
    ET.register_namespace("exif",   "http://ns.adobe.com/exif/1.0/")
    ET.register_namespace("xmpMM",  "http://ns.adobe.com/xap/1.0/mm/")
    ET.register_namespace("photoshop", "http://ns.adobe.com/photoshop/1.0/")

    try:
        xmp_str = xmp_payload.decode("utf-8", errors="replace")
        # Strip xpacket processing instructions — ET can't parse them
        xmp_str = re.sub(r"<\?xpacket[^?]*\?>", "", xmp_str).strip()
        root = ET.fromstring(xmp_str)

        rdf_rdf = root.find(f"{{{_RDF}}}RDF")
        if rdf_rdf is None:
            return _build_minimal_xmp(description)

        # Try to find an existing dc:description element
        for rdf_desc in rdf_rdf.findall(f"{{{_RDF}}}Description"):
            dc_elem = rdf_desc.find(f"{{{_DC}}}description")
            if dc_elem is not None:
                _set_rdf_alt_text(dc_elem, description)
                return _wrap_xpacket(ET.tostring(root, encoding="unicode"))

        # No dc:description found — add it to the first rdf:Description
        first = rdf_rdf.find(f"{{{_RDF}}}Description")
        if first is None:
            return _build_minimal_xmp(description)

        dc_elem = ET.SubElement(first, f"{{{_DC}}}description")
        _set_rdf_alt_text(dc_elem, description)
        return _wrap_xpacket(ET.tostring(root, encoding="unicode"))

    except ET.ParseError:
        return _build_minimal_xmp(description)


def _set_rdf_alt_text(dc_elem: ET.Element, text: str) -> None:
    """Set the x-default rdf:li inside an existing or new rdf:Alt under dc_elem."""
    alt = dc_elem.find(f"{{{_RDF}}}Alt")
    if alt is None:
        dc_elem.clear()
        alt = ET.SubElement(dc_elem, f"{{{_RDF}}}Alt")

    for li in alt.findall(f"{{{_RDF}}}li"):
        if li.get(f"{{{_XML}}}lang") == "x-default":
            li.text = text
            return

    li = ET.SubElement(alt, f"{{{_RDF}}}li")
    li.set(f"{{{_XML}}}lang", "x-default")
    li.text = text


# ------------------------------------------------------------------ #
# PNG embedding                                                        #
# ------------------------------------------------------------------ #

def _embed_png(path: Path, description: str) -> None:
    """Write tEXt Description + XMP iTXt chunk into a PNG in place."""
    try:
        from PIL import Image, PngImagePlugin

        img = Image.open(path)
        meta = PngImagePlugin.PngInfo()

        # Preserve existing text chunks (except ones we're overwriting)
        for key, val in (getattr(img, "text", {}) or {}).items():
            if key not in ("Description", "XML:com.adobe.xmp"):
                try:
                    meta.add_text(key, val)
                except Exception:
                    pass

        meta.add_text("Description", description)

        # XMP as iTXt chunk — what Apple Photos and modern apps read
        xmp_str = _build_minimal_xmp(description)
        meta.add_itxt("XML:com.adobe.xmp", xmp_str, lang="", tkey="")

        img.save(path, "PNG", pnginfo=meta)
    except Exception as exc:
        raise RuntimeError(f"PNG embed failed for {path.name}: {exc}") from exc


# ------------------------------------------------------------------ #
# WebP embedding                                                       #
# ------------------------------------------------------------------ #

def _embed_webp(path: Path, description: str) -> None:
    """Write EXIF UserComment into a WebP (requires re-save)."""
    try:
        import piexif
        import piexif.helper
        from PIL import Image

        try:
            exif_dict = piexif.load(str(path))
        except Exception:
            exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}}

        exif_dict["Exif"][piexif.ExifIFD.UserComment] = piexif.helper.UserComment.dump(
            description, encoding="unicode"
        )
        exif_bytes = piexif.dump(exif_dict)

        img = Image.open(path)
        lossless = img.info.get("lossless", False)
        save_kwargs = {"exif": exif_bytes}
        if lossless:
            save_kwargs["lossless"] = True
        else:
            save_kwargs["quality"] = 95
        img.save(path, "WEBP", **save_kwargs)
    except Exception as exc:
        raise RuntimeError(f"WebP embed failed for {path.name}: {exc}") from exc
