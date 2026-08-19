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
  macOS Get Info / Preview     ← ImageIO, which reports the description as IPTC
                                 Caption/Abstract and EXIF UserComment
  macOS Spotlight, mdls        ← kMDItemDescription, off the same importer

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


def _page_count(path: Path) -> int:
    """Number of frames in a multi-page image."""
    from PIL import Image

    img = Image.open(path)
    count = 0
    try:
        while True:
            img.seek(count)
            count += 1
    except EOFError:
        pass
    return count


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

    @pytest.mark.regression
    def test_multipage_tiff_keeps_every_page(self, tmp_path):
        """Scanned documents are multi-page, and a plain save() keeps only one.

        Pillow's save() writes the frame currently seeked unless save_all is
        passed, so a four-page scan came back as one page with no error raised.
        In-place mode overwrites the only copy, making it unrecoverable.
        """
        from PIL import Image

        from idt_core.embedder import embed_image_file

        colours = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]
        pages = [Image.new("RGB", (40, 30), c) for c in colours]
        src = tmp_path / "scan.tif"
        pages[0].save(src, "TIFF", save_all=True, append_images=pages[1:])

        dest = tmp_path / "scan_out.tif"
        embed_image_file(src, DESCRIPTION, dest)

        assert _page_count(dest) == 4, "pages were dropped"
        out = Image.open(dest)
        for index, colour in enumerate(colours):
            out.seek(index)
            assert out.convert("RGB").getpixel((5, 5)) == colour, f"page {index} wrong"

    @pytest.mark.regression
    def test_multipage_tiff_still_gets_the_description(self, tmp_path):
        """The page fix must not cost the description.

        `seek()` rewrites tag_v2 in place rather than returning a new object, so
        setting the tags before walking the frames left them wiped by the time
        of the save — pages preserved, description silently gone.
        """
        from PIL import Image

        from idt_core.embedder import embed_image_file, _TIFF_IMAGE_DESCRIPTION

        pages = [Image.new("RGB", (20, 20), c) for c in [(1, 2, 3), (4, 5, 6)]]
        src = tmp_path / "two.tif"
        pages[0].save(src, "TIFF", save_all=True, append_images=pages[1:])

        dest = tmp_path / "two_out.tif"
        embed_image_file(src, DESCRIPTION, dest)
        assert _read_tiff_tag(dest, _TIFF_IMAGE_DESCRIPTION) == DESCRIPTION

    @pytest.mark.regression
    def test_multipage_tiff_in_place_keeps_pages(self, tmp_path):
        """In-place mode is where page loss is unrecoverable — no copy to fall back on."""
        from PIL import Image

        from idt_core.embedder import embed_image_file

        pages = [Image.new("RGB", (20, 20), c) for c in [(1, 2, 3), (4, 5, 6), (7, 8, 9)]]
        path = tmp_path / "inplace_multi.tif"
        pages[0].save(path, "TIFF", save_all=True, append_images=pages[1:])

        embed_image_file(path, DESCRIPTION, path)
        assert _page_count(path) == 3

    def test_compression_is_not_silently_dropped(self, tmp_path):
        """Rewriting the file must not turn an LZW archive into an uncompressed one."""
        from PIL import Image

        from idt_core.embedder import embed_image_file

        src = tmp_path / "lzw.tif"
        Image.new("RGB", (400, 300), (10, 20, 30)).save(src, "TIFF", compression="tiff_lzw")
        dest = tmp_path / "lzw_out.tif"
        embed_image_file(src, DESCRIPTION, dest)
        assert Image.open(dest).info.get("compression") == "tiff_lzw"

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
        """WebP needs a codec Windows does not always ship.

        Explorer reads WebP properties through the Microsoft WebP Image
        Extension. Windows 11 desktop installs have it; Server images and CI
        runners do not, and without it the shell has no property handler for
        .webp at all — every image column comes back empty, not just Comments.

        Distinguish the two: no Dimensions means no handler, which is a fact
        about the machine. Dimensions but no Comments means the embed is broken.
        """
        columns = _explorer_columns(_embed(tmp_path, ".webp", "WEBP"))
        if not columns.get("Dimensions"):
            pytest.skip(
                "no WebP property handler on this machine (Microsoft WebP Image "
                "Extension not installed) — Explorer shows no WebP image "
                "columns at all, so Comments cannot be checked"
            )
        assert columns.get("Comments") == DESCRIPTION

    def test_tiff_appears_in_comments_column(self, tmp_path):
        columns = _explorer_columns(_embed(tmp_path, ".tif", "TIFF"))
        assert columns.get("Comments") == DESCRIPTION


# ------------------------------------------------------------------ #
# The macOS instructions in the user guide, checked against macOS        #
# ------------------------------------------------------------------ #
#
# Three different readers, because they fail in different ways:
#
#   xattr     — Finder comments are an extended attribute. No index, no
#               framework, works on any Mac including a bare CI runner.
#   ImageIO   — the framework Preview, Get Info and the Spotlight importer all
#               sit on. Needs pyobjc but no running daemon.
#   Spotlight — mdls, the command printed in the guide. Needs an indexed
#               volume, which GitHub's runners do not have.
#
# Only the last one is allowed to skip.

_FINDER_COMMENT_XATTR = "com.apple.metadata:kMDItemFinderComment"


def _imageio_descriptions(path: Path) -> dict:
    """Return the description-bearing fields macOS's own image framework reports.

    Get Info, Preview and the Spotlight importer all read through ImageIO, so
    these are the values a reader following the guide ends up looking at.

    The individual fields are pulled out rather than matching against str() of
    the whole dictionary: an NSDictionary renders non-ASCII escaped, so a
    stringified compare fails on accented text that is in fact stored correctly.
    """
    Quartz = pytest.importorskip(
        "Quartz", reason="pyobjc-framework-Quartz not installed",
    )
    from CoreFoundation import CFURLCreateFromFileSystemRepresentation

    encoded = str(path).encode("utf-8")
    url = CFURLCreateFromFileSystemRepresentation(None, encoded, len(encoded), False)
    source = Quartz.CGImageSourceCreateWithURL(url, None)
    assert source is not None, f"ImageIO could not open {path.name}"
    properties = Quartz.CGImageSourceCopyPropertiesAtIndex(source, 0, None)
    assert properties is not None, f"ImageIO returned no properties for {path.name}"

    wanted = {
        "iptc_caption": ("{IPTC}", "Caption/Abstract"),
        "exif_user_comment": ("{Exif}", "UserComment"),
        "tiff_image_description": ("{TIFF}", "ImageDescription"),
        "png_description": ("{PNG}", "Description"),
    }
    found = {}
    for name, (section, key) in wanted.items():
        value = (properties.get(section) or {}).get(key)
        if value:
            found[name] = str(value)
    return found


def _spotlight_description(path: Path):
    """Return what `mdls` reports, or None if Spotlight has nothing to say.

    mdls reads the Spotlight *index*. A CI runner never indexes its temp
    directories, so a null answer there is a fact about the machine and not
    about the file — hence None rather than a failure.
    """
    out = subprocess.run(
        ["mdls", "-name", "kMDItemDescription", str(path)],
        capture_output=True, text=True, timeout=60,
    )
    if out.returncode != 0 or "(null)" in out.stdout:
        return None
    _, sep, value = out.stdout.partition("=")
    return value.strip().strip('"') if sep else None


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS metadata")
class TestMacosFinderCommentCaveat:
    """The guide warns that Finder's Comments column is not the description.

    Finder comments live in an extended attribute, so this needs no Spotlight
    index and no framework — it runs anywhere, including a bare CI runner.
    """

    def test_embedding_writes_no_finder_comment(self, tmp_path):
        """If embedding ever populated this, the guide's warning would be wrong.

        Readers would then be told to ignore a column that actually works.
        """
        path = _embed(tmp_path, ".jpg", "JPEG")
        out = subprocess.run(
            ["xattr", "-p", _FINDER_COMMENT_XATTR, str(path)],
            capture_output=True, text=True, timeout=30,
        )
        assert out.returncode != 0, (
            f"embedding set a Finder comment ({out.stdout.strip()}); the user "
            "guide says Finder's Comments column stays empty"
        )

    def test_the_xattr_probe_can_actually_detect_one(self, tmp_path):
        """Guard against the assertion above passing because the probe is broken.

        A test that checks for absence proves nothing unless presence is
        detectable — so set a comment by hand and confirm it is seen.
        """
        path = _embed(tmp_path, ".jpg", "JPEG")
        written = subprocess.run(
            ["xattr", "-w", _FINDER_COMMENT_XATTR, "a hand-written note", str(path)],
            capture_output=True, text=True, timeout=30,
        )
        assert written.returncode == 0, f"could not set xattr: {written.stderr}"
        out = subprocess.run(
            ["xattr", "-p", _FINDER_COMMENT_XATTR, str(path)],
            capture_output=True, text=True, timeout=30,
        )
        assert out.returncode == 0 and "hand-written" in out.stdout


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS ImageIO")
class TestMacosImageIoMetadata:
    """Get Info, Preview and the Spotlight importer all read through ImageIO.

    Querying it directly is the closest thing to opening Get Info that a
    headless runner can do, and unlike mdls it needs no indexed volume.

    Measured on macos-latest: JPEG comes back as both IPTC Caption/Abstract and
    EXIF UserComment, and PNG and TIFF are visible too. Asserting that at least
    one recognised field holds the exact text keeps the check honest across
    formats without pinning macOS's internal choice of field.
    """

    def _assert_visible(self, path: Path, expected: str) -> None:
        found = _imageio_descriptions(path)
        assert found, (
            f"macOS's image framework reports no description at all for "
            f"{path.name} — Get Info would be empty"
        )
        assert expected in found.values(), (
            f"no ImageIO field holds the description for {path.name}: {found}"
        )

    def test_jpeg_description_is_visible_to_imageio(self, tmp_path):
        self._assert_visible(_embed(tmp_path, ".jpg", "JPEG"), DESCRIPTION)

    def test_tiff_description_is_visible_to_imageio(self, tmp_path):
        """TIFF gets IFD tags and no XMP, so it needs checking separately."""
        self._assert_visible(_embed(tmp_path, ".tif", "TIFF"), DESCRIPTION)

    def test_png_description_is_visible_to_imageio(self, tmp_path):
        self._assert_visible(_embed(tmp_path, ".png", "PNG"), DESCRIPTION)

    def test_webp_description_is_visible_to_imageio(self, tmp_path):
        self._assert_visible(_embed(tmp_path, ".webp", "WEBP"), DESCRIPTION)

    def test_unicode_survives_to_imageio(self, tmp_path):
        """Accents and CJK must arrive intact, not mojibake in Get Info."""
        self._assert_visible(
            _embed(tmp_path, ".jpg", "JPEG", UNICODE_DESCRIPTION), UNICODE_DESCRIPTION
        )


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS Spotlight")
class TestMacosSpotlight:
    """The `mdls` command the guide prints, run verbatim.

    This is the one reader allowed to skip: it depends on an indexed volume,
    and GitHub's macOS runners index nothing. Set IDT_REQUIRE_SPOTLIGHT=1 on a
    real Mac to turn the skip into a failure.
    """

    def _require_or_skip(self, value, path: Path):
        if value is not None:
            return value
        if os.environ.get("IDT_REQUIRE_SPOTLIGHT") == "1":
            pytest.fail(
                f"mdls reported nothing for {path.name}. The user guide tells "
                "macOS readers to use exactly this command."
            )
        pytest.skip(
            "Spotlight has not indexed this path (normal on CI). "
            "Set IDT_REQUIRE_SPOTLIGHT=1 on an indexed Mac to require it."
        )

    def test_documented_mdls_command_returns_the_description(self, tmp_path):
        path = _embed(tmp_path, ".jpg", "JPEG")
        value = self._require_or_skip(_spotlight_description(path), path)
        assert value == DESCRIPTION

    def test_png_description_reaches_spotlight(self, tmp_path):
        path = _embed(tmp_path, ".png", "PNG")
        value = self._require_or_skip(_spotlight_description(path), path)
        assert value == DESCRIPTION


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
