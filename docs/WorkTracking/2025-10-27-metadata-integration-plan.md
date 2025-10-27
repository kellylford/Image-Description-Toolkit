# Metadata Integration Implementation Plan
## Date: October 27, 2025

## Overview
Integrate comprehensive metadata (GPS coordinates, city/state/country via geocoding, dates, camera info) throughout the entire IDT ecosystem end-to-end.

## User Requirements
1. **Configuration**: Guideme and command-line flags for metadata and geocoding
2. **Data Flow**: Metadata extracted during workflow, included in logs and descriptions
3. **Viewer**: Display "City, State Mon Day, Year: Description" format
4. **ImageDescriber**: Show metadata as properties
5. **IDTConfigure**: Configure metadata settings
6. **HTML Output**: Include metadata in galleries/reports
7. **Documentation**: User guides updated with metadata features

## Technical Architecture

### Phase 1: Core Infrastructure ✅ COMPLETE
- **File**: `scripts/metadata_extractor.py` (NEW)
- **Classes**: `MetadataExtractor`, `NominatimGeocoder`
- **Functions**: 
  - `extract_metadata()` - Extract EXIF, GPS, camera, dates
  - `format_location_prefix()` - Format "City, State Mon Day, Year"
  - `build_meta_suffix()` - Compact metadata line
  - `enrich_metadata()` - Add geocoded city/state/country

### Phase 2: Integration into image_describer.py ⏳ IN PROGRESS
**Changes Needed:**
1. Import shared `metadata_extractor` module
2. Replace local `extract_metadata()` with shared version
3. Add geocoder initialization if enabled
4. Update `write_description_to_file()` to add location/date prefix to description text
5. Add configuration options for metadata and geocoding

**Description Format:**
```
File: photo.jpg
Path: /full/path/photo.jpg
Photo Date: 3/25/2025 7:35P
Location: GPS: 30.267200, -97.743100, City: Austin, State: Texas
Camera: Apple iPhone 14
Provider: openai
Model: gpt-4o
Prompt Style: detailed
Description: Madison, WI Sep 9, 2025: A beautiful sunset over the lake with vibrant orange and pink hues.
Timestamp: 2025-10-27 14:30:00
Meta: date=3/25/2025 7:35P; location=Austin, TX; coords=30.267200,-97.743100
--------------------------------------------------------------------------------
```

**Key Decision**: Location/date prefix goes in the Description line itself, not as separate metadata.

### Phase 3: Configuration System
**Files to Update:**
1. `scripts/image_describer_config.json` - Add metadata settings
2. `workflow.py` - Add CLI flags `--metadata`, `--geocode`, `--geocode-cache`
3. `scripts/guided_workflow.py` - Add metadata configuration steps
4. `idtconfigure/idtconfigure.py` - Add Metadata category

**Configuration Schema:**
```json
{
  "metadata": {
    "enabled": true,
    "include_location_prefix": true,
    "geocoding": {
      "enabled": false,
      "user_agent": "IDT/3.0 (+https://github.com/kellylford/Image-Description-Toolkit)",
      "delay_seconds": 1.0,
      "cache_file": "geocode_cache.json"
    }
  }
}
```

### Phase 4: Viewer Updates
**File**: `viewer/viewer.py`
**Changes**:
1. Parse location/date prefix from description text
2. Display prominently in description panel
3. Optional: Highlight prefix with different formatting

**Current Format**: 
```
Description: A beautiful sunset...
```

**New Format**:
```
Description: Madison, WI Sep 9, 2025: A beautiful sunset...
```

### Phase 5: ImageDescriber GUI
**File**: `imagedescriber/image_describer.py`
**Changes**:
1. Parse and display metadata fields:
   - Location (city, state, GPS coordinates)
   - Date taken
   - Camera make/model
2. Add to properties panel or create metadata section
3. Update accessible names for screen readers

### Phase 6: HTML Output
**Files**: 
- `analysis/combine_workflow_descriptions.py`
- HTML template generation code

**Changes**:
1. Include location/date prefix in HTML galleries
2. Add metadata as hover tooltips or expandable sections
3. Optional: Group by location or date

### Phase 7: Documentation
**Files to Update:**
1. `docs/USER_GUIDE.md` - Add metadata section
2. `docs/CLI_REFERENCE.md` - Document flags
3. `README.md` - Mention metadata features
4. `tools/show_metadata/README.md` - Cross-reference integration

## Implementation Order

### Priority 1: Core Workflow (Required for basic functionality)
1. ✅ Create shared metadata module
2. ⏳ Integrate into image_describer.py
3. ⏳ Add configuration system
4. ⏳ Update workflow.py CLI flags
5. ⏳ Update guided_workflow.py wizard

### Priority 2: UI/Display (Required for user visibility)
6. ⏳ Update viewer to show prefix
7. ⏳ Update ImageDescriber GUI
8. ⏳ Add IDTConfigure settings

### Priority 3: Output/Documentation (Enhancement)
9. ⏳ Update HTML output
10. ⏳ Update documentation

## Testing Plan

### Unit Tests
- [ ] Metadata extraction from various image formats
- [ ] Geocoding with mock API responses
- [ ] Cache persistence and retrieval
- [ ] Location prefix formatting

### Integration Tests
- [ ] Workflow with metadata enabled
- [ ] Workflow with geocoding enabled
- [ ] Resume workflow with metadata
- [ ] Viewer displays metadata correctly

### End-to-End Tests
- [ ] guideme → workflow → viewer → descriptions with metadata
- [ ] Configuration save/load
- [ ] HTML export with metadata
- [ ] Screen reader accessibility

## Rollout Strategy

### Stage 1: Opt-In (Safe)
- Metadata disabled by default
- Geocoding disabled by default
- Users must explicitly enable via config or CLI flags

### Stage 2: Soft Enable (After testing)
- Metadata enabled by default
- Geocoding still opt-in (requires API calls)

### Stage 3: Full Integration (After user feedback)
- Update default configuration
- Prominent in UI
- Featured in documentation

## Risk Mitigation

### Performance
- **Risk**: EXIF extraction adds overhead
- **Mitigation**: Only extract when enabled, cache results

### API Rate Limiting
- **Risk**: Nominatim blocks excessive requests
- **Mitigation**: 1-second delay enforced, caching, opt-in only

### Privacy
- **Risk**: GPS coordinates expose location
- **Mitigation**: User must explicitly enable, clear documentation

### Compatibility
- **Risk**: Existing workflows break
- **Mitigation**: Backward compatible, metadata optional, preserves existing format

## Success Criteria

### Functionality
- ✅ Metadata extracted from all supported image formats
- ✅ Geocoding works with caching and rate limiting
- ⏳ Location/date prefix appears in descriptions
- ⏳ Viewer displays metadata prominently
- ⏳ Configuration options accessible via CLI and GUI

### Quality
- ⏳ No performance degradation with metadata disabled
- ⏳ Screen reader accessible
- ⏳ Comprehensive error handling
- ⏳ Clear user documentation

### User Experience
- ⏳ Easy to enable/disable
- ⏳ Intuitive prefix format
- ⏳ Helpful in guideme wizard
- ⏳ Visible in all output formats

## Current Status
**Phase 1**: ✅ Complete - Shared module created
**Phase 2**: ⏳ In Progress - Ready to integrate into image_describer.py
**Phases 3-7**: ⏳ Not started

## Next Steps
1. Update image_describer.py to use shared metadata module
2. Add configuration schema to image_describer_config.json
3. Test metadata extraction and prefix formatting
4. Add workflow.py CLI flags
5. Update guided_workflow.py
