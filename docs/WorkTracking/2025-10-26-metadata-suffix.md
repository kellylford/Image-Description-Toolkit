# Work Tracking - Metadata Suffix and Date Format Update (Oct 26, 2025)

## Summary
- Implemented standardized date formatting (M/D/YYYY H:MMP) for EXIF-derived dates used by the image describer.
- Added a compact, parseable one-line "Meta:" suffix at the end of each description entry:
  - Example: `Meta: date=3/25/2025 7:35P; location=Austin, TX; coords=30.267200,-97.743100`
  - Includes only available fields; falls back to file mtime if EXIF date absent.
  - Uses human-readable location when available (City/State/Country), with GPS coords when present.
- Kept existing multi-line metadata block unchanged for backward compatibility.

## Files Changed
- `scripts/image_describer.py`
  - Added `_format_mdy_ampm(dt)`; updated `_extract_datetime(...)` priority and output format
  - Enhanced `_extract_location(...)` to include city/state/country when available
  - Added `_build_meta_suffix(image_path, metadata)` and appended its output in `write_description_to_file(...)`

## Documentation Updated
- `docs/USER_GUIDE.md`
  - New section: "Results and output files" documenting the Meta suffix, date format, and example entry

## Notes
- Lint note: optional dependency `ollama` may not be present in all environments; code already guards provider usage.
- No breaking changes; suffix is additive.

## Next Steps (Optional)
- Teach results/analysis tools to parse the new Meta line when beneficial
- Add a brief note in CLI reference about output entry structure
