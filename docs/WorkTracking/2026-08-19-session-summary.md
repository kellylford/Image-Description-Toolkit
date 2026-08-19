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

## What was NOT tested

- **macOS instructions were not verified on a Mac.** No macOS machine in this
  session. The Get Info / Preview Inspector / Spotlight / `mdls` / Photos routes
  rest on the XMP `dc:description` field, which *is* verified present by the new
  tests, and on the user's own report that Get Info shows it. But nobody ran
  `mdls` against an embedded file here, and the "More Info section" placement in
  Get Info is from the user's description, not observation. Worth a confirming
  pass on a Mac before anyone relies on the exact wording.
- **HEIC** was not exercised. It converts to JPEG first, so it inherits the JPEG
  path the tests do cover, but no HEIC file went through end to end.
- **The published HTML** was not rendered. Pandoc is not installed locally, so the
  new tables and the nested fenced code block in the macOS bullet list have not
  been seen through the real publish pipeline — only checked for correct
  indentation. The GitHub Pages workflow rebuilds on merge to `main`.
- **Explorer's own UI** was not driven. The column values were read from the shell
  property system rather than by tabbing to a header and pressing Shift+F10, so
  the keystroke sequence in the guide is unverified as a sequence, even though
  every column it names is confirmed populated.
