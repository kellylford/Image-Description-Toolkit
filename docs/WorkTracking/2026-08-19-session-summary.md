# 2026-08-19 — Reading embedded descriptions back, on Windows and macOS

## What prompted this

The user guide explained how to embed descriptions into images and then stopped.
It never said where the description ends up or how to look at it, which makes the
feature hard to trust: you run `idt embed`, you get a folder of copies, and you
have no way to confirm anything happened.

## Files changed

| File | Change |
|------|--------|
| `docs/USER_GUIDE.md` | Expanded *Embedding Descriptions into Images* with a field-by-format table and two new subsections: Windows and macOS access steps |
| `docs/IMAGE_FORMAT_SUPPORT.md` | Corrected three claims that measurement contradicted |
| `idt_core/embedder.py` | New `_embed_by_format()` dispatcher; new `_embed_tiff()`; TIFF no longer routed to the JPEG writer |
| `pytest_tests/unit/test_embedded_metadata_visibility.py` | New — 35 tests |
| `CHANGELOG.md` | Documentation and Bug Fixes entries under Unreleased |

## What was measured, not assumed

The whole point of the new guide section is telling someone which column to switch
on, so guessing was not an option. Every claim was checked on this Windows 11
machine by querying the shell property system (`Shell.Application.GetDetailsOf`),
which is the same source Explorer draws its columns from.

| Format | Comments column | Title column |
|--------|-----------------|--------------|
| JPEG | ✓ EXIF UserComment | ✓ XMP `dc:description` |
| PNG | ✗ (no EXIF) | ✓ XMP iTXt chunk |
| WebP | ✓ EXIF UserComment | ✗ (no XMP written) |
| TIFF | ✓ XPComment | ✓ ImageDescription |

The user's instinct — Details view, tab to headers, Shift+F10, turn on Comments or
Title — is correct, with the PNG exception worth calling out.

## The TIFF bug this turned up

Writing the format table meant embedding into one of each format and looking at
the result. The TIFF would not open afterwards.

`embed_image_file()` routed `.tif` and `.tiff` to `_embed_jpeg()`, which walks
JPEG marker segments and injects an APP1. Run against a TIFF that overwrites the
`II*\0` byte-order magic — the file began `II\xff\xe1` — and Pillow, Explorer and
Preview all refused it. Nothing raised. The embed reported success and the user
got a folder of dead files.

Fixed by giving TIFF its own writer (`ImageDescription` 270 + `XPComment` 40092
via Pillow) and putting format dispatch in one place, where an unknown extension
is copied and left alone instead of handed to whichever writer looked closest.

`_embed_one()` in the `Embedder` class never had the TIFF branch, so project-mode
embeds silently skipped metadata for TIFF rather than corrupting it. It now goes
through the same dispatcher and gets the tags.

## Test coverage

Before: `TestEmbedder` and `TestXmpInjection` in `test_idt_core.py` proved copies
land in the right place and carry XMP. Nothing asserted *which* tag any format
got, so nothing would have caught a change that left an Explorer column blank —
or the TIFF corruption.

New file reads the files back the way each OS does:

- EXIF UserComment via piexif (JPEG, WebP)
- XMP `dc:description` extracted and parsed (JPEG, PNG)
- PNG tEXt and iTXt chunks
- TIFF tags 270 and 40092
- Unicode round-trip per format — UserComment is UCS-2, XMP is UTF-8
- Every embedded file still opens
- Sources never modified; unknown formats byte-identical after copy
- **Windows only:** actual Explorer column values via the shell property system,
  asserting the exact instruction the guide gives
- The guide itself still contains the Windows steps, the macOS steps and the
  Spotlight Comments caveat

Result: 35 passed. Against the pre-fix embedder, 7 fail.

Full suite: 1715 passed, 34 skipped.

## Reviewed, then fixed

An independent review pass over the first commit found three things worth having.

**Multi-page TIFF was being flattened.** Pillow's `save()` writes only the frame
currently seeked unless `save_all` is passed, so a four-page scan came back as
one page with nothing raised. In-place mode dropped the other three off the only
copy. TIFF is the format `IMAGE_FORMAT_SUPPORT.md` calls archival, which is
precisely the multi-page case.

Fixing that exposed a second layer underneath: `seek()` rewrites `tag_v2` in
place rather than returning a new object, so the tags set before walking the
frames were wiped by the walk. Pages came back and the description did not. The
IFD is now read after iteration. Both halves have their own test, because each
failed silently on its own.

**The macOS job could not pass on GitHub hardware** — see below.

**The CI guard hid failures.** `pytest | tee` returns tee's exit status, and the
step's default shell is `bash -e`, which does not set pipefail. Fixed with an
explicit `set -o pipefail`, and a skip in the must-run classes is now an error.

## What macOS CI can and cannot verify

Established by running it, not by reasoning about it:

| Reader | On a GitHub runner | Why |
|--------|--------------------|-----|
| `xattr` | ✓ works | Finder comments are an extended attribute; no daemon |
| ImageIO | ✓ works | Needs pyobjc, no index |
| `mdls` | ✗ returns `(null)` | Reads the Spotlight index; runners index nothing |
| `mdimport` | ✗ crashes | `NSInvalidArgumentException ... -[NSNull length]` |

The first attempt set `IDT_REQUIRE_SPOTLIGHT=1` and got 5 failed, 30 passed. So
the macOS cases were rebuilt on readers a runner can actually run. ImageIO is the
framework Get Info, Preview and the Spotlight importer all sit on, so it is one
layer below the same answer rather than a weaker substitute.

**What the macOS run settled:** ImageIO reports the description for JPEG, PNG,
WebP and TIFF alike, as IPTC `Caption/Abstract` and EXIF `UserComment`. The open
question about whether TIFF reaches macOS is answered — it does — so the guide's
macOS section needs no per-format carve-out, unlike the Windows column table.

Seven macOS cases pass on Apple hardware. The two `mdls` cases skip on CI and run
for real on a Mac with `IDT_REQUIRE_SPOTLIGHT=1`.

## What the Windows runner settled

`test_webp_appears_in_comments_column` passes on Kelly's Windows 11 desktop and
failed on the runner. Explorer reads WebP properties through the Microsoft WebP
Image Extension; desktop installs have it, CI images do not, and without it the
shell has no property handler for `.webp` at all — Dimensions, Bit depth and
Width come back empty alongside Comments.

The test separates the two cases rather than being loosened: no Dimensions means
no handler and skips with that reason; Dimensions present but Comments empty
still fails. Readers get told too, because a missing codec looks exactly like a
failed embed.

## Test coverage

Before: `TestEmbedder` and `TestXmpInjection` in `test_idt_core.py` proved copies
land in the right place and carry XMP. Nothing asserted *which* tag any format
got, so nothing would have caught a change that left an Explorer column blank —
or the TIFF corruption.

The new file reads the files back the way each OS does: EXIF UserComment via
piexif, XMP `dc:description` parsed out, PNG tEXt and iTXt chunks, TIFF tags 270
and 40092, unicode round-trip per format, every embedded file still opens,
sources never modified, unknown formats byte-identical after copy. Then the
platform layer — real Explorer column values on Windows, `xattr` and ImageIO on
macOS — and assertions that the guide still contains the instructions.

48 cases. On Windows: 39 passed, 9 skipped (macOS-only). Full suite 1720 passed.
All six CI checks green, including the new macOS job.

## What was NOT tested

- **`mdls` itself has never been run against an embedded file.** It is the
  command printed in the guide, and CI cannot exercise it. The ImageIO tests
  cover the layer beneath it on real macOS, which is strong evidence but not the
  same thing. Running the suite on a Mac with `IDT_REQUIRE_SPOTLIGHT=1` closes
  this, and is worth doing once.
- **No GUI was driven on either platform.** Explorer columns were read from the
  shell property system rather than by tabbing to a header and pressing
  Shift+F10, and Get Info was never opened. Every field the instructions name is
  confirmed populated; the keystroke sequences are unverified as sequences.
- **HEIC** was not exercised end to end. It converts to JPEG first, so it
  inherits a covered path.
- **The published HTML** was not rendered. Pandoc is not installed locally, so
  the new tables and the nested code block were checked for indentation only.
  The Pages workflow rebuilds on merge to `main`.
