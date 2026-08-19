"""What an embedded description looks like from outside IDT.

The existing embedder tests in test_idt_core.py prove the copies get made, land
in the right directory and carry XMP. They stop there. But the promise the user
guide makes is a different one: turn on the Comments column in File Explorer and
the description is sitting there; press Cmd+I in Finder and it is sitting there.
That promise rests on *which specific tag* each format gets, and nothing pinned
those tags down.

So these tests read the files back the way the operating system does:

  Windows Explorer "Comments"  ← EXIF UserComment (JPEG, WebP) / XPComment (TIFF)
  Windows Explorer "Title"     ← XMP dc:description (JPEG, PNG) / ImageDescription (TIFF)
  macOS Get Info / Spotlight   ← XMP dc:description
  Apple Photos caption         ← XMP dc:description

Change a tag number here and a documented, screen-reader-accessible way of
getting at these descriptions quietly stops working, with no error anywhere.

The TIFF cases are a regression guard. Until this file existed, .tif and .tiff
were routed through the JPEG writer, which injected an APP1 segment over the
"II*\0" magic. The result was not a TIFF without a description; it was a file
Pillow, Explorer and Preview all refused to open.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

pytestmark = pytest.mark.unit

DESCRIPTION = "A tabby cat asleep on a sunlit windowsill."
UNICODE_DESCRIPTION = "Un café à Paris — 15° et « nuageux », 日本語も"


# ------------------------------------------------------------------ #
# Fixtures                                                             #
# ------------------------------------------------------------------ #

def _write_source(path: Path, fmt: str) -> Path:
    """Save a small real image so the format writers have something to chew on."""
    from PIL import Image

    Image.new("RGB", (32, 24), (120, 60, 30)).save(path, fmt)
    return path


def _embed(tmp_path: Path, suffix: str, fmt: str, text: str = DESCRIPTION) -> Path:
    from idt_core.embedder import embed_image_file

    src = _write_source(tmp_path / f"src{suffix}", fmt)
    dest = tmp_path / f"embedded{suffix}"
    embed_image_file(src, text, dest)
    return dest


# ------------------------------------------------------------------ #
# Readers that mimic what each platform actually looks at               #
# ------------------------------------------------------------------ #

def _read_exif_user_comment(path: Path) -> str:
    """EXIF UserComment — the tag behind Explorer's "Comments" column."""
    import piexif
    import piexif.helper

    exif = piexif.load(str(path))
    raw = exif["Exif"].get(piexif.ExifIFD.UserComment)
    assert raw is not None, f"{path.name} has no EXIF UserComment"
    return piexif.helper.UserComment.load(raw)


def _read_xmp_description(path: Path) -> str:
    """XMP dc:description — what macOS Spotlight, Preview and Photos read."""
    from idt_core.embedder import _extract_xmp_from_jpeg

    if path.suffix.lower() in (".jpg", ".jpeg"):
        payload = _extract_xmp_from_jpeg(path.read_bytes())
        assert payload is not None, f"{path.name} has no XMP APP1 segment"
        xmp = payload.decode("utf-8", errors="replace")
    else:
        from PIL import Image

        xmp = (getattr(Image.open(path), "text", {}) or {}).get("XML:com.adobe.xmp", "")
        assert xmp, f"{path.name} has no XMP chunk"

    match = re.search(r'<rdf:li[^>]*x-default"?[^>]*>(.*?)</rdf:li>', xmp, re.DOTALL)
    assert match, f"{path.name} XMP has no x-default rdf:li:\n{xmp}"
    return match.group(1).strip()


def _read_tiff_tag(path: Path, tag: int):
    from PIL import Image

    return Image.open(path).tag_v2.get(tag)


def _still_opens(path: Path) -> None:
    """A file with metadata nothing can read is a bug; a file nothing can open is worse."""
    from PIL import Image

    img = Image.open(path)
    img.load()


# ------------------------------------------------------------------ #
# JPEG — both Windows columns and the macOS fields                      #
# ------------------------------------------------------------------ #

class TestJpegVisibility:
    def test_user_comment_carries_description(self, tmp_path):
        """Explorer's "Comments" column reads EXIF UserComment."""
        dest = _embed(tmp_path, ".jpg", "JPEG")
        assert _read_exif_user_comment(dest) == DESCRIPTION

    def test_xmp_description_carries_description(self, tmp_path):
        """Finder Get Info, Spotlight and Photos all read XMP dc:description."""
        dest = _embed(tmp_path, ".jpg", "JPEG")
        assert _read_xmp_description(dest) == DESCRIPTION

    def test_both_fields_agree(self, tmp_path):
        """Windows and macOS users must not be shown two different descriptions."""
        dest = _embed(tmp_path, ".jpg", "JPEG")
        assert _read_exif_user_comment(dest) == _read_xmp_description(dest)

    def test_file_still_opens(self, tmp_path):
        _still_opens(_embed(tmp_path, ".jpg", "JPEG"))

    def test_unicode_survives_both_fields(self, tmp_path):
        """UserComment is dumped as UCS-2 and XMP as UTF-8 — neither may mangle accents."""
        dest = _embed(tmp_path, ".jpg", "JPEG", UNICODE_DESCRIPTION)
        assert _read_exif_user_comment(dest) == UNICODE_DESCRIPTION
        assert _read_xmp_description(dest) == UNICODE_DESCRIPTION


# ------------------------------------------------------------------ #
# PNG — no EXIF, so XMP and tEXt are the whole story                    #
# ------------------------------------------------------------------ #

class TestPngVisibility:
    def test_text_chunk_carries_description(self, tmp_path):
        from PIL import Image

        dest = _embed(tmp_path, ".png", "PNG")
        assert Image.open(dest).text["Description"] == DESCRIPTION

    def test_xmp_chunk_carries_description(self, tmp_path):
        """PNG has no EXIF, so the guide tells PNG users to use the Title column."""
        dest = _embed(tmp_path, ".png", "PNG")
        assert _read_xmp_description(dest) == DESCRIPTION

    def test_file_still_opens(self, tmp_path):
        _still_opens(_embed(tmp_path, ".png", "PNG"))

    def test_unicode_survives(self, tmp_path):
        dest = _embed(tmp_path, ".png", "PNG", UNICODE_DESCRIPTION)
        assert _read_xmp_description(dest) == UNICODE_DESCRIPTION


# ------------------------------------------------------------------ #
# WebP — EXIF only                                                      #
# ------------------------------------------------------------------ #

class TestWebpVisibility:
    def test_user_comment_carries_description(self, tmp_path):
        dest = _embed(tmp_path, ".webp", "WEBP")
        assert _read_exif_user_comment(dest) == DESCRIPTION

    def test_file_still_opens(self, tmp_path):
        _still_opens(_embed(tmp_path, ".webp", "WEBP"))

    def test_unicode_survives(self, tmp_path):
        dest = _embed(tmp_path, ".webp", "WEBP", UNICODE_DESCRIPTION)
        assert _read_exif_user_comment(dest) == UNICODE_DESCRIPTION


# ------------------------------------------------------------------ #
# TIFF — the regression that started this file                          #
# ------------------------------------------------------------------ #

class TestTiffVisibility:
    @pytest.mark.regression
    def test_embedded_tiff_is_still_a_readable_tiff(self, tmp_path):
        """.tif used to be handed to the JPEG writer, which destroyed the file."""
        dest = _embed(tmp_path, ".tif", "TIFF")
        assert dest.read_bytes()[:2] in (b"II", b"MM"), "TIFF byte-order magic overwritten"
        _still_opens(dest)

    @pytest.mark.regression
    def test_tiff_extension_also_handled(self, tmp_path):
        """Both spellings route to the TIFF writer, not just .tif."""
        dest = _embed(tmp_path, ".tiff", "TIFF")
        _still_opens(dest)
        from idt_core.embedder import _TIFF_IMAGE_DESCRIPTION

        assert _read_tiff_tag(dest, _TIFF_IMAGE_DESCRIPTION) == DESCRIPTION

    def test_image_description_tag_carries_description(self, tmp_path):
        """Tag 270 feeds Explorer's Title and Subject columns."""
        from idt_core.embedder import _TIFF_IMAGE_DESCRIPTION

        dest = _embed(tmp_path, ".tif", "TIFF")
        assert _read_tiff_tag(dest, _TIFF_IMAGE_DESCRIPTION) == DESCRIPTION

    def test_xp_comment_tag_carries_description(self, tmp_path):
        """Tag 40092 is UCS-2 with a trailing NUL, and feeds the Comments column."""
        from idt_core.embedder import _TIFF_XP_COMMENT

        dest = _embed(tmp_path, ".tif", "TIFF")
        raw = _read_tiff_tag(dest, _TIFF_XP_COMMENT)
        assert raw is not None, "no XPComment tag — Explorer's Comments column stays empty"
        if isinstance(raw, (tuple, list)):
            raw = bytes(raw)
        assert raw.decode("utf-16-le").rstrip("\x00") == DESCRIPTION

    def test_pixels_are_preserved(self, tmp_path):
        """Pillow rewrites the whole file for TIFF, so check it rewrites it faithfully."""
        from PIL import Image

        from idt_core.embedder import embed_image_file

        src = _write_source(tmp_path / "src.tif", "TIFF")
        before = Image.open(src).tobytes()
        dest = tmp_path / "out.tif"
        embed_image_file(src, DESCRIPTION, dest)
        assert Image.open(dest).tobytes() == before


# ------------------------------------------------------------------ #
# Format dispatch                                                       #
# ------------------------------------------------------------------ #

class TestFormatDispatch:
    def test_unknown_format_is_copied_not_corrupted(self, tmp_path):
        """An unsupported extension gets a plain copy — never a speculative write."""
        from idt_core.embedder import embed_image_file

        src = tmp_path / "notes.bmp"
        _write_source(src, "BMP")
        original = src.read_bytes()
        dest = tmp_path / "out.bmp"
        embed_image_file(src, DESCRIPTION, dest)
        assert dest.read_bytes() == original

    @pytest.mark.parametrize("suffix,fmt", [
        (".jpg", "JPEG"), (".png", "PNG"), (".webp", "WEBP"), (".tif", "TIFF"),
    ])
    def test_source_is_never_touched(self, tmp_path, suffix, fmt):
        from idt_core.embedder import embed_image_file

        src = _write_source(tmp_path / f"src{suffix}", fmt)
        before = src.read_bytes()
        embed_image_file(src, DESCRIPTION, tmp_path / f"out{suffix}")
        assert src.read_bytes() == before

    @pytest.mark.parametrize("suffix,fmt", [
        (".jpg", "JPEG"), (".png", "PNG"), (".webp", "WEBP"), (".tif", "TIFF"),
    ])
    def test_in_place_mode_keeps_the_file_openable(self, tmp_path, suffix, fmt):
        from idt_core.embedder import embed_image_file

        path = _write_source(tmp_path / f"inplace{suffix}", fmt)
        embed_image_file(path, DESCRIPTION, path)
        _still_opens(path)


# ------------------------------------------------------------------ #
# The Windows instructions in the user guide, checked against Windows    #
# ------------------------------------------------------------------ #

def _explorer_columns(path: Path) -> dict:
    """Ask the Windows shell for the same column values Explorer would display."""
    script = f"""
$sh = New-Object -ComObject Shell.Application
$f = $sh.NameSpace('{path.parent}')
$item = $f.ParseName('{path.name}')
foreach ($i in 0..40) {{
  $col = $f.GetDetailsOf($f.Items, $i)
  $val = $f.GetDetailsOf($item, $i)
  if ($col -and $val) {{ Write-Output ($col + '=' + $val) }}
}}
"""
    out = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True, text=True, timeout=90,
    )
    if out.returncode != 0:
        pytest.skip(f"Windows shell query unavailable: {out.stderr.strip()[:200]}")
    columns = {}
    for line in out.stdout.splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            columns[key.strip()] = value.strip()
    return columns


@pytest.mark.skipif(sys.platform != "win32", reason="Windows Explorer columns")
class TestWindowsExplorerColumns:
    """The user guide tells Windows users to switch on a specific column.

    These tests query the shell property system directly, so if a future change
    to the tags leaves that column blank, the guide is wrong and CI says so
    rather than a reader discovering it in Explorer.
    """

    def test_jpeg_appears_in_comments_column(self, tmp_path):
        columns = _explorer_columns(_embed(tmp_path, ".jpg", "JPEG"))
        assert columns.get("Comments") == DESCRIPTION

    def test_jpeg_appears_in_title_column(self, tmp_path):
        columns = _explorer_columns(_embed(tmp_path, ".jpg", "JPEG"))
        assert columns.get("Title") == DESCRIPTION

    def test_png_appears_in_title_column(self, tmp_path):
        """PNG has no EXIF, so Title is the only column that works — as documented."""
        columns = _explorer_columns(_embed(tmp_path, ".png", "PNG"))
        assert columns.get("Title") == DESCRIPTION

    def test_webp_appears_in_comments_column(self, tmp_path):
        columns = _explorer_columns(_embed(tmp_path, ".webp", "WEBP"))
        assert columns.get("Comments") == DESCRIPTION

    def test_tiff_appears_in_comments_column(self, tmp_path):
        columns = _explorer_columns(_embed(tmp_path, ".tif", "TIFF"))
        assert columns.get("Comments") == DESCRIPTION


# ------------------------------------------------------------------ #
# The macOS instructions in the user guide, checked against macOS        #
# ------------------------------------------------------------------ #

def _spotlight_attributes(path: Path) -> tuple[dict, str]:
    """Read a file's Spotlight attributes, returning (attributes, source_tool).

    `mdls` is the command the user guide gives, so it is tried first. It reads
    the Spotlight *index*, which on a CI runner may never have seen the temp
    directory -- a null answer there says nothing about the file.

    `mdimport -t` runs the same importer directly against the file, no index
    involved. If mdimport produces the description and mdls does not, the
    metadata is correct and only the index is missing, so the test still passes
    and records which tool answered.
    """
    attributes: dict[str, str] = {}

    probe = subprocess.run(
        ["mdls", str(path)], capture_output=True, text=True, timeout=60,
    )
    if probe.returncode == 0:
        for line in probe.stdout.splitlines():
            key, sep, value = line.partition("=")
            if sep and value.strip() not in ("(null)", ""):
                attributes[key.strip()] = value.strip().strip('"')
    if attributes.get("kMDItemDescription"):
        return attributes, "mdls"

    forced = subprocess.run(
        ["mdimport", "-t", "-d2", str(path)], capture_output=True, text=True, timeout=60,
    )
    combined = forced.stdout + forced.stderr
    match = re.search(r'kMDItemDescription\s*=\s*"?(.*?)"?[;\n]', combined)
    if match:
        attributes["kMDItemDescription"] = match.group(1).strip()
        return attributes, "mdimport"

    if os.environ.get("IDT_REQUIRE_SPOTLIGHT") == "1":
        pytest.fail(
            "Neither mdls nor mdimport reported kMDItemDescription. The user "
            "guide tells macOS readers to use exactly these tools.\n"
            f"mdls rc={probe.returncode}\nmdimport output:\n{combined[:1000]}"
        )
    pytest.skip("Spotlight metadata unavailable (set IDT_REQUIRE_SPOTLIGHT=1 to fail instead)")


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS Spotlight metadata")
class TestMacosSpotlightMetadata:
    """The guide tells macOS readers to use Get Info, Spotlight and mdls.

    All three read the same place: kMDItemDescription, which macOS populates
    from the XMP dc:description packet the embedder writes. Asserting on that
    key is asserting on what Get Info displays, without needing a GUI.
    """

    def test_jpeg_description_reaches_spotlight(self, tmp_path):
        attributes, _ = _spotlight_attributes(_embed(tmp_path, ".jpg", "JPEG"))
        assert attributes["kMDItemDescription"] == DESCRIPTION

    def test_png_description_reaches_spotlight(self, tmp_path):
        attributes, _ = _spotlight_attributes(_embed(tmp_path, ".png", "PNG"))
        assert attributes["kMDItemDescription"] == DESCRIPTION

    def test_unicode_survives_to_spotlight(self, tmp_path):
        attributes, _ = _spotlight_attributes(
            _embed(tmp_path, ".jpg", "JPEG", UNICODE_DESCRIPTION)
        )
        assert attributes["kMDItemDescription"] == UNICODE_DESCRIPTION

    def test_finder_comment_is_not_where_the_description_lands(self, tmp_path):
        """The caveat in the guide, made checkable.

        Finder's "Comments" column shows kMDItemFinderComment, an xattr Finder
        keeps on the side. Embedding must not populate it -- if it ever did, the
        guide's warning would be wrong and readers would be told to ignore a
        column that works.
        """
        attributes, _ = _spotlight_attributes(_embed(tmp_path, ".jpg", "JPEG"))
        assert not attributes.get("kMDItemFinderComment"), (
            "embedding wrote a Finder comment; the user guide says it does not"
        )

    def test_mdls_command_from_the_guide_runs_verbatim(self, tmp_path):
        """The guide prints `mdls -name kMDItemDescription photo.jpg`.

        Run that exact form, so a typo in the documented command is caught here
        rather than by a reader pasting it into Terminal.
        """
        path = _embed(tmp_path, ".jpg", "JPEG")
        out = subprocess.run(
            ["mdls", "-name", "kMDItemDescription", str(path)],
            capture_output=True, text=True, timeout=60,
        )
        assert out.returncode == 0, out.stderr
        assert "kMDItemDescription" in out.stdout
        if "(null)" in out.stdout:
            _spotlight_attributes(path)   # skips or fails with the fuller diagnosis
        else:
            assert DESCRIPTION in out.stdout


# ------------------------------------------------------------------ #
# The guide itself                                                      #
# ------------------------------------------------------------------ #

class TestUserGuideDocumentsAccess:
    """The feature is only useful if people can find the descriptions again.

    Embedding shipped before the guide said how to read the result back, which
    is how this whole exercise started. These assertions keep the instructions
    in place, so a future edit cannot quietly drop them.
    """

    @property
    def _guide(self) -> str:
        return (_ROOT / "docs" / "USER_GUIDE.md").read_text(encoding="utf-8")

    def test_guide_exists(self):
        assert (_ROOT / "docs" / "USER_GUIDE.md").is_file()

    def test_windows_steps_are_documented(self):
        guide = self._guide
        for needle in ("Details view", "Shift+F10", "Comments"):
            assert needle in guide, f"Windows access instructions lost {needle!r}"

    def test_macos_steps_are_documented(self):
        guide = self._guide
        assert "Get Info" in guide, "macOS access instructions lost Get Info"
        assert "mdls" in guide, "macOS access instructions lost the mdls fallback"

    def test_finder_comments_caveat_is_documented(self):
        """Finder's Comments column is a Spotlight xattr, not embedded metadata.

        Readers who switch it on and see nothing need to know why, or they will
        conclude the embed failed.
        """
        assert "Spotlight Comments" in self._guide
