# Build Testing Checklist — October 27, 2025

Use this checklist to validate the current build end-to-end. Mark items with [x] as you verify them and add short notes inline. This file lives in the repo so both of us can see status.

- Build ID: 
- Commit(s): 03fe6bd + latest on main
- Tester: 
- Date: 

## 0) Pre-flight
- [ ] Clean working tree (no uncommitted changes)
- [ ] Pull latest main
- [ ] Dependencies present (Ollama or cloud keys available as needed)
- [ ] Test images ready (include a few HEICs, JPGs, and a short MP4 if testing video)

## 1) Build and Packaging
- [ ] Run build scripts (builditall.bat or release flow) without errors
- [ ] idt.exe launches with `idt --help`
- [ ] imagedescriber.exe launches
- [ ] viewer.exe launches
- [ ] prompt_editor.exe launches
- [ ] Final artifact structure correct (executables + scripts + docs)

Notes:

## 2) Workflow (CLI) — Golden Path
- [ ] Run: `idt workflow <images_dir>` with default options completes
- [ ] Output directory created under Descriptions/ with workflow name
- [ ] image_descriptions.txt contains entries for each input image
- [ ] viewer prompt after completion works (y launches viewer)

Notes:

## 3) Conversion Step — Real-time Progress (NEW)
- [ ] CMD shows: "⟳ Image conversion in progress: X/Y HEIC → JPG (Z%)"
- [ ] On completion, shows: "✓ Image conversion complete (Y HEIC → JPG)"
- [ ] logs/convert_images_progress.txt created and appended per converted file
- [ ] logs/status.log mirrors convert in-progress and completion lines
- [ ] Edge case: If no HEIC files, workflow skips convert cleanly (no errors)

Notes:

## 4) Description Step — Real-time Progress
- [ ] CMD shows description progress updates X/Y (Z%)
- [ ] logs/image_describer_progress.txt created and grows over time
- [ ] logs/status.log mirrors describe in-progress and completion lines
- [ ] Resume/re-run with --preserve-descriptions skips existing entries

Notes:

## 5) Metadata Extraction & Geocoding (NEW)
- [ ] Descriptions prefixed with location/date when metadata enabled
- [ ] Geocoding opt-in via --geocode works
- [ ] geocode_cache.json created/persisted across runs
- [ ] OpenStreetMap attribution appears when geocoding used (console/description/HTML)
- [ ] Privacy mode: --no-metadata removes prefix

Notes:

## 6) Viewer — Live & Completed Modes
- [ ] Auto-launch from guideme shows live updates
- [ ] Title shows progress: "XX%, X of Y images described (Live)"
- [ ] Completed workflows display 100% with counts
- [ ] Prefix (location/date) rendered in bold blue above description
- [ ] Keyboard-only navigation works (WCAG single tab stop pattern)

Notes:

## 7) ImageDescriber GUI — Properties & Batch
- [ ] Properties dialog shows Location & Date, Camera Info, Photo Settings
- [ ] Batch processing updates progress visibly and accessibly
- [ ] Manual description edits saved correctly

Notes:

## 8) IDTConfigure — Metadata Settings
- [ ] "Metadata Settings" category present
- [ ] Toggle metadata enablement
- [ ] Toggle geocoding and set cache file path
- [ ] Settings persist to image_describer_config.json

Notes:

## 9) HTML Output — Prefix & Attribution
- [ ] HTML report highlights location/date prefix in bold blue
- [ ] OSM attribution footer shown only when geocoding was used

Notes:

## 10) Guided Wizard — Metadata Prompts
- [ ] guideme prompts to enable metadata
- [ ] guideme prompts to enable geocoding
- [ ] Pass-through options respected (e.g., --timeout, --preserve-descriptions)

Notes:

## 11) Logs & Diagnostics
- [ ] logs/status.log is human-readable and updates during convert/describe
- [ ] No noisy stack traces; clear actionable messages for errors
- [ ] Timeouts respect provided --timeout value and log clearly

Notes:

## 12) Edge Cases
- [ ] Read-only images directory (graceful error)
- [ ] Network offline while --geocode enabled (falls back, continues)
- [ ] No EXIF GPS available (uses file mtime/date fallback)
- [ ] Very large collections (spot-check progress/log behavior)

Notes:

## 13) Performance Quick Checks
- [ ] Small set (<50 images) completes without stalls
- [ ] Progress updates feel responsive (every ~2s)
- [ ] No excessive disk writes (progress files are append-only, lightweight)

Notes:

## 14) Sign-off
- [ ] Build artifacts validated
- [ ] Docs updated (User Guide, CLI Reference reflect progress features)
- [ ] Ready to tag release

Notes:
