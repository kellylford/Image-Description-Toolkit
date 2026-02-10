# Standardize and Enhance Metadata System

**Date:** 2026-02-09  
**Status:** In Progress  
**Priority:** P1 - Core Functionality  

## Overview

Metadata handling is currently inconsistent between IDT CLI and ImageDescriber GUI. This document tracks the work to standardize metadata across all components, add processing time to output, and ensure config settings work consistently.

## Problems Identified

1. **Processing Time** - Tracked but not saved to output
   - IDT CLI: Calculated at [scripts/image_describer.py:1350](../../scripts/image_describer.py#L1350) but only logged
   - GUI: Not tracked at all

2. **Token Usage** - Inconsistent handling
   - IDT CLI: Logged but not written to description files
   - GUI: Appended inline to description text
   - Result: Can't compare token usage across CLI/GUI workflows

3. **Metadata Output Format** - Different approaches
   - IDT CLI: Structured text sections + compact suffix
   - GUI: Stored in workspace (.idw), not exported to .txt
   - Result: GUI users can't get .txt files with metadata like CLI

4. **OpenStreetMap Attribution** - Missing in GUI
   - IDT CLI: Includes attribution when geocoding used
   - GUI: Missing attribution (potential policy violation)

5. **Config Settings** - Some only work in CLI
   - `include_timestamp`, `include_model_info`, `include_file_path`, `include_metadata`
   - Checkboxes exist in GUI but may not be fully implemented

## Current Metadata Fields

| Field | IDT CLI | GUI | Notes |
|-------|---------|-----|-------|
| Photo Date | ✅ Written | ✅ Stored | M/D/YYYY H:MMP format |
| Location (geocoded) | ✅ Written | ✅ Stored | City, State, Country |
| GPS Coordinates | ✅ Written | ✅ Stored | Lat/Lon/Altitude |
| Camera Info | ✅ Written | ✅ Stored | Make/Model/Lens |
| Source File | ✅ Written | ✅ Stored | For video frames |
| Processing Time | ❌ Logged only | ❌ Not tracked | **TO ADD** |
| Token Usage | ❌ Logged only | ✅ In description | **TO STANDARDIZE** |
| Compact Meta Suffix | ✅ Written | ❌ Not used | CLI-specific |
| Location Prefix | ✅ Written | ✅ In description | Different formats |
| OSM Attribution | ✅ Written | ❌ Missing | **TO ADD** |

## Implementation Plan

### 1. Add Processing Time to Metadata Output ✅ COMPLETE

**IDT CLI:**
- [x] Modify `write_description_to_file()` to accept `processing_duration` parameter
- [x] Update `format_metadata()` to include processing time
- [x] Pass calculated duration from line 1350 to write function

**ImageDescriber GUI:**
- [x] Add timing to `workers_wx.py:_process_with_ai()`
- [x] Store in `ImageDescription.metadata['processing_time_seconds']`
- [x] Include in token usage display: `[... | Time: X.Xs]`

### 2. Standardize Token Usage ✅ COMPLETE

**IDT CLI:**
- [x] Add token usage to metadata section (not just logs)
- [x] Format: `Tokens: X,XXX total (X,XXX input + X,XXX output)`

**Both:**
- [x] Ensure consistent format
- [x] Include in combined info line: `[Token Usage: ... | Time: X.Xs]`

### 3. Add OSM Attribution to GUI ✅ COMPLETE

- [x] Add attribution flag to `workers_wx.py:_extract_metadata()`
- [x] Set `metadata['osm_attribution_required'] = True` when geocoding used
- [x] Display in exported text files

### 4. Audit Config Settings ⏳ DEFERRED

**Verify these work in both CLI and GUI:**
- [ ] `include_timestamp`
- [ ] `include_model_info`
- [ ] `include_file_path`
- [ ] `include_metadata`

**Note:** Config audit deferred to post-wxPython migration release.

### 5. Update Configure Dialog ⏳ DEFERRED

**Add new options:**
- [ ] Processing time toggle
- [ ] Token usage toggle
- [ ] Compact metadata suffix toggle

**Note:** Config dialog updates deferred to Issue #72 (surface model metadata).

### 6. Enable Metadata Export from GUI ✅ COMPLETE

**Critical: Handle Multiple Descriptions Per Image**
- [x] GUI allows multiple descriptions per image (different models/prompts)
- [x] Export handles this gracefully
- [x] Separate sections per description
- [x] Note which description (1 of 3, etc.)

**Implementation:**
- [x] Add "Export Descriptions to Text" command in File menu
- [x] Generate same format as CLI `write_description_to_file()`
- [x] Include all metadata sections
- [x] Handle multiple descriptions per image
- [x] Include OSM attribution when needed

## Code References

### Metadata Extraction (Shared)
- [scripts/metadata_extractor.py:40-492](../../scripts/metadata_extractor.py#L40-L492) - MetadataExtractor class

### IDT CLI
- [scripts/image_describer.py:1536-1582](../../scripts/image_describer.py#L1536-L1582) - extract_metadata()
- [scripts/image_describer.py:1755-1833](../../scripts/image_describer.py#L1755-L1833) - format_metadata()
- [scripts/image_describer.py:1044-1153](../../scripts/image_describer.py#L1044-L1153) - write_description_to_file()
- [scripts/image_describer.py:1312-1352](../../scripts/image_describer.py#L1312-L1352) - Processing time tracking

### GUI Metadata
- [imagedescriber/workers_wx.py:439-491](../../imagedescriber/workers_wx.py#L439-L491) - _extract_metadata()
- [imagedescriber/workers_wx.py:495-528](../../imagedescriber/workers_wx.py#L495-L528) - _add_location_byline()
- [imagedescriber/workers_wx.py:533-561](../../imagedescriber/workers_wx.py#L533-L561) - _add_token_usage_info()

### Config
- [scripts/image_describer_config.json:22-77](../../scripts/image_describer_config.json#L22-L77) - All metadata settings
- [imagedescriber/configure_dialog.py:400-558](../../imagedescriber/configure_dialog.py#L400-L558) - GUI checkboxes

## Testing Checklist

- [ ] Test processing time in CLI output
- [ ] Test processing time in GUI output
- [ ] Test token usage in CLI metadata section
- [ ] Test token usage format matches GUI
- [ ] Test OSM attribution appears in GUI
- [ ] Test all config checkboxes work in CLI
- [ ] Test all config checkboxes work in GUI
- [ ] Test export from GUI workspace
- [ ] Test export handles multiple descriptions per image
- [ ] Compare CLI and GUI metadata - should be consistent

## Export Format for Multiple Descriptions

When exporting from GUI with multiple descriptions per image:

```
================================================================================
File: IMG_1234.jpg
Path: C:\Images\IMG_1234.jpg
Photo Date: 2/9/2026 3:45P
Camera: iPhone 14 Pro
Location: Austin, TX
GPS: 30.2672°N, 97.7431°W, 150m
================================================================================

Description #1
Provider: claude
Model: claude-opus-4-6
Prompt Style: narrative
Processing Time: 2.34 seconds
Tokens: 1,723 total (1,580 input + 143 completion)
Created: 2/9/2026 3:45:12P

[Description text here]

--------------------------------------------------------------------------------

Description #2
Provider: openai
Model: gpt-4o
Prompt Style: detailed
Processing Time: 1.89 seconds
Tokens: 1,456 total (1,200 input + 256 completion)
Created: 2/9/2026 3:47:28P

[Description text here]

================================================================================
```

## Dependencies

- No external dependencies required
- Uses existing metadata extraction code
- Leverages current config system

## Timeline

- **Session 1 (2026-02-09):** Planning and implementation
- **Session 2:** Testing and refinement
- **Release:** Include in next wxPython migration release

## Notes

- Keep metadata format human-readable (no JSON dumps)
- Maintain backwards compatibility with existing workflows
- Export should work with both single and multiple descriptions
- Consider adding "Export Selected Descriptions" option later
