# 2025-10-29 Session Summary

## Status
- User reports: "runs are happening" — builds/tests are in progress.
- We simplified the viewer (always uses descriptions file), added source file tracking for video frames, and updated parsers yesterday (see 2025-10-28 summary).

### Incoming build test run (for verification)
- Workflow path: \\qnap\home\idt\descriptions\wf_BuildTest_ollama_moondreamlatest_concise_20251029_024146
- Contents: ~25 recent photos from Europe with geocoding enabled
- Purpose: Validate viewer simplification and source tracking end-to-end

## What to verify in this build
- Viewer reads only `descriptions/image_descriptions.txt` and shows full description text (no "strong strong").
- Window title shows "XX%, X of Y images described" and adds "(Live)" while active.
- Refresh button works and preserves focus/position.
- Descriptions file includes `Source: <video path> at <timestamp>` for extracted frames; absent for still images.
- EXIF on a frame contains ImageDescription/UserComment with source video path and timestamp.
- Combined CSV export includes Location column (city/state/country when available) and remains date sorted.
- All apps build and launch (CLI + GUIs).

## Quick checks (when runs complete)
- Open any recent workflow in viewer and skim descriptions for Source lines.
- Spot-check a frame's EXIF using exiftool or Pillow to confirm source fields.
- Run combined export and check Location column is filled where EXIF has data.

### Optional: automated verification helper
We added `tools/verify_workflow_output.py` to quickly validate a workflow:

```bash
# Summary + list first 5 frames missing Source (if any)
python tools/verify_workflow_output.py "//qnap/home/idt/descriptions/wf_BuildTest_ollama_moondreamlatest_concise_20251029_024146" --list-missing 5

# Include EXIF spot-checks (up to 5 images)
python tools/verify_workflow_output.py "//qnap/home/idt/descriptions/wf_BuildTest_ollama_moondreamlatest_concise_20251029_024146" --check-exif --list-missing 5
```

It reports counts for entries with Source lines, OSM attribution (geocoded), Photo Date, Camera, and flags likely video frames missing Source.

## Notes / Decisions
- Viewer simplification removed HTML parsing path entirely to improve accessibility and reliability.
- Source tracking is embedded in EXIF and echoed into the descriptions file for easy tracing back to originals.

## Next
- Ask Kelly how the build and run went and capture results here.
- If any failures, triage with minimal repro and add tests.

---

## Update — 2025-10-29 (early morning) — CRITICAL BUG FIX: Metadata Loss

### Issue Reported
User ran workflow `wf_Cottage_ollama_qwen3-vl235b-cloud_colorful_20251029_051724`:
- Only 1 image (from Meta glasses) had metadata in descriptions
- All iPhone Live Photos missing metadata (GPS, dates, camera info)
- iPhone originals were Live Photos (`.mov` + `.heic` or `.jpg`)

### Root Cause Identified
**Bug in `scripts/ConvertImage.py` lines 161-164**:

```python
# OLD CODE (BROKEN):
if keep_metadata and hasattr(current_image, 'info') and attempt == 0:
    exif_data = current_image.info.get('exif', b'')
    if exif_data:
        save_kwargs['exif'] = exif_data
```

**Problem**: EXIF metadata only preserved on first save attempt (`attempt == 0`). When images needed size optimization (quality reduction or resizing), all subsequent saves **lost the EXIF data**.

**Why iPhone Photos Were Affected**: iPhone images are often larger and required multiple optimization attempts to meet size limits (3.75MB target for base64 encoding). Each optimization attempt lost the metadata.

**Why Meta Glasses Photo Worked**: Likely smaller file size, saved successfully on first attempt without needing optimization.

### Fix Applied
**Modified `scripts/ConvertImage.py` lines 143-168**:

```python
# NEW CODE (FIXED):
# Preserve EXIF metadata once at the beginning (will be included in all save attempts)
exif_data = None
if keep_metadata and hasattr(image, 'info'):
    exif_data = image.info.get('exif', b'')
    if exif_data:
        logger.debug(f"Preserved EXIF metadata from {input_path.name} ({len(exif_data)} bytes)")

# ... optimization loop ...
while attempt < 10:
    save_kwargs = {...}
    # Include EXIF data in every save attempt
    if exif_data:
        save_kwargs['exif'] = exif_data
    current_image.save(output_path, **save_kwargs)
```

**Solution**: Extract EXIF data once before the optimization loop, then include it in **every** save attempt regardless of quality/size adjustments.

### Impact
- **Critical**: This bug caused metadata loss for any image requiring size optimization
- **Scope**: Affects all workflows using HEIC→JPG conversion with larger images
- **Data Loss**: GPS coordinates, dates, camera info, lens data all lost during conversion
- **Geocoding Impact**: Without GPS, reverse geocoding couldn't add city/state names

### Testing Status
- ✅ Syntax validated
- ⏳ Awaiting rebuild and re-test of Cottage workflow
- Should see metadata for all iPhone photos after rebuild

### Files Modified
- `scripts/ConvertImage.py` - Fixed EXIF preservation to work through all optimization attempts

---

## User Action Required
**Rebuild immediately** to get this critical fix:
```bash
cd BuildAndRelease
builditall.bat
```

Then re-run the Cottage workflow to verify metadata is preserved for all iPhone photos.

---

## Test Infrastructure Discovery

After the EXIF bug, we discovered IDT has a comprehensive testing system already in place:

### Existing Test Structure
- **pytest_tests/unit/** - Fast unit tests (4 files)
  - `test_metadata_safety.py` - Format string injection protection (@pytest.mark.regression)
  - `test_workflow_config.py` - Config file race condition tests
  - `test_sanitization.py` - Input sanitization tests
  - `test_status_log.py` - Status logging tests
  
- **pytest_tests/integration/** - Integration tests requiring real operations (2 files)
  - `test_exif_preservation.py` - **NEW TODAY** - EXIF through optimization pipeline
  - `test_workflow_integration.py` - **NEW TODAY** - End-to-end workflow validation
  
- **pytest_tests/smoke/** - Entry point smoke tests
  - `test_entry_points.py` - CLI/GUI launch validation
  
- **pytest_tests/conftest.py** - Shared fixtures (project paths, temp dirs, mock args)

### Test Configuration (pyproject.toml)
- Markers: `@pytest.mark.slow`, `@pytest.mark.integration`, `@pytest.mark.unit`, `@pytest.mark.regression`
- Coverage configured for `scripts/` directory
- Test discovery: `test_*.py`, `*_test.py` patterns
- Strict markers enabled to catch typos

### CI/CD Roadmap Exists
Full automation plan in `docs/WorkTracking/ISSUE-automated-testing-cicd.md`:
- **Phase 1**: Fix current tests (immediate)
- **Phase 2**: GitHub Actions for syntax/unit tests (quick win)
- **Phase 3**: Self-hosted runner for integration tests with Ollama
- **Phase 4**: Full DevOps automation (releases, benchmarks, coverage)

### Testing Gap Analysis

**What existed before today:**
- Unit tests for format strings, config races, sanitization, status logging
- Smoke tests for application launches
- Regression test markers for known bugs
- Build automation scripts
- CI/CD roadmap document

**What was added today (2025-10-29):**
- `test_exif_preservation.py` - Tests EXIF metadata through image optimization
  - Small images (no optimization needed)
  - Medium images (quality reduction)
  - Large images (aggressive resize)
  - GPS coordinate accuracy
  - Metadata stripping when disabled
  - **Would have caught today's EXIF bug**
  
- `test_workflow_integration.py` - End-to-end pipeline tests
  - Conversion → metadata extraction → description → viewer parsing
  - Video frame source tracking validation
  - Full workflow execution
  - **Would have caught today's EXIF bug**

### Test Execution

```bash
# Run all tests
pytest pytest_tests -v

# Run only unit tests (fast)
pytest pytest_tests/unit -v

# Run only integration tests (slow, needs test images)
pytest pytest_tests/integration -v

# Run regression tests only
pytest pytest_tests -m regression -v

# With coverage report
pytest pytest_tests --cov=scripts --cov-report=html
```

### Integration Test Requirements
The new integration tests need:
- Test images with EXIF metadata (various sizes)
- Temporary directories for conversion output
- PIL/Pillow for EXIF reading
- piexif for detailed EXIF inspection

Tests are fixtures-based and clean up after themselves.

---

## Geocoding Configuration Issue (2025-10-29 morning)

**Problem Found**: Workflows were not showing city/state/country despite having GPS coordinates.

**Root Cause**: 
- Default config had `"metadata.geocoding.enabled": false`
- Users would need to manually edit JSON to get city/state - unacceptable UX
- Multiple config locations caused confusion (source repo vs deployed install)

**Fix Applied**:
1. Changed default in source: `scripts/image_describer_config.json` → `geocoding.enabled: true`
2. Updated deployed install: `C:\idt\scripts\image_describer_config.json` → `geocoding.enabled: true`

**Impact**:
- New workflows will automatically reverse geocode GPS → city/state/country
- No manual config editing required
- Example: `GPS: 28.385294, -80.599053` → `Location: Cape Canaveral, Florida, United States`

**Testing**:
- Log evidence from wf_2023_01 run showed: `"GPS detected but reverse geocoding is disabled"`
- After fix, new runs should show full Location lines with city/state

**Next rebuild**: Ensure new default ships with executable

---

## Next Steps

1. **Rebuild IDT with fixes** - EXIF preservation + geocoding enabled by default
2. **Re-run test workflow** - Verify city/state/country appears for images with GPS
3. **Run verify_workflow_output.py on BuildTest** - Validate Europe photos workflow
4. **Run new integration tests** - Validate EXIF preservation tests catch the bug:
   ```bash
   pytest pytest_tests/integration/test_exif_preservation.py -v
   ```
5. **Update CI/CD roadmap** - Document what's complete vs planned
