# Retroactive Workflow Geotagging Tool

Add metadata and geocoding to workflows that were processed before these features were enabled.

## What It Does

This tool:
- **Extracts metadata** (GPS, dates, camera info) from original images
- **Adds location/date prefixes** to existing descriptions
- **Geocodes GPS coordinates** to readable locations (city, state, country)
- **Updates both CSV and individual TXT files**
- **Preserves original descriptions** while enriching with metadata
- **Backs up original files** before making changes

## Perfect For

- Workflows processed before metadata extraction was available
- Re-running geocoding after cache improvements
- Adding location context to old workflow results
- Migrating legacy workflows to the new metadata format

## Quick Start

```bash
# Preview changes (dry run)
python tools/geotag_workflow.py C:\idt\Descriptions\wf_VacationPhotos_... --dry-run

# Apply geotagging with geocoding
python tools/geotag_workflow.py C:\idt\Descriptions\wf_VacationPhotos_...

# Geotag without geocoding (coordinates only)
python tools/geotag_workflow.py C:\idt\Descriptions\wf_VacationPhotos_... --no-geocode
```

## Usage Examples

### Basic Geotagging
```bash
python tools/geotag_workflow.py C:\idt\Descriptions\wf_MyWorkflow_ollama_llava_narrative_20251027_120000
```

This will:
1. Find original images for each description
2. Extract metadata (GPS, dates, camera info)
3. Convert GPS to city/state via OpenStreetMap Nominatim
4. Add location/date prefix: `"Austin, TX Mar 25, 2025: ..."`
5. Update both CSV and TXT files
6. Create `.bak` backups of originals

### Preview Mode (Dry Run)
```bash
python tools/geotag_workflow.py C:\idt\Descriptions\wf_MyWorkflow_... --dry-run
```

Shows what would be changed without modifying files. Perfect for testing.

### Update Specific File Types
```bash
# Update only CSV file
python tools/geotag_workflow.py C:\idt\Descriptions\wf_MyWorkflow_... --only-csv

# Update only individual TXT files
python tools/geotag_workflow.py C:\idt\Descriptions\wf_MyWorkflow_... --only-txt
```

### Custom Geocoding Cache
```bash
python tools/geotag_workflow.py C:\idt\Descriptions\wf_MyWorkflow_... --geocode-cache my_cache.json
```

Useful for sharing geocoding cache across multiple workflow updates.

## Before & After Example

**Before (no metadata):**
```
A beautiful sunset over the lake with vibrant orange and pink hues reflecting on the calm water.
```

**After (with metadata & geocoding):**
```
Austin, TX Mar 25, 2025: A beautiful sunset over the lake with vibrant orange and pink hues reflecting on the calm water.

[3/25/2025 7:35P, iPhone 14, 30.2672°N, 97.7431°W]
```

## How It Works

### Image Location Discovery

The tool searches for original images in:
1. Parent directory of workflow output (typical input location)
2. `converted_images/` subdirectory (HEIC conversions)
3. `frames/` subdirectory (video frames)
4. `source_images.txt` manifest (if present)

### Smart Skipping

- **Already tagged** - Skips descriptions that already have location/date prefix
- **No metadata** - Skips images without EXIF data
- **Missing images** - Reports when original images can't be found

### Backup Strategy

Before modifying files:
- Creates `.bak` backup: `descriptions.csv.bak`
- Creates `.bak` for each TXT: `IMG_1234.txt.bak`
- Originals are preserved for safety

## Options Reference

```
python tools/geotag_workflow.py <workflow_dir> [OPTIONS]

Required:
  workflow_dir          Path to workflow directory to geotag

Options:
  --dry-run             Preview changes without modifying files
  --no-geocode          Skip geocoding (GPS coordinates only)
  --geocode-cache FILE  Custom geocoding cache file (default: geocode_cache.json)
  --only-csv            Update only CSV file (skip .txt files)
  --only-txt            Update only .txt files (skip CSV)
  -h, --help            Show help message
```

## Requirements

- Original image files must be accessible (not deleted after workflow)
- Images must have EXIF metadata (GPS, dates, camera info)
- Internet connection required for geocoding (unless using cached data)

## Limitations

### Won't Work If:
- Original images have been deleted or moved
- Images never had EXIF metadata (e.g., screenshots, downloaded images)
- Workflow output directory structure has been modified

### Geocoding Notes:
- Uses OpenStreetMap Nominatim API (free, open-source)
- Respects 1-second delay between API requests
- Results are cached for future runs
- Works offline after locations are cached

## Output & Statistics

The tool reports:
- **Total images processed**
- **Metadata extracted successfully**
- **Locations geocoded**
- **CSV descriptions updated**
- **TXT files updated**
- **Skipped** (already tagged or no metadata)
- **Errors** (if any)

Example output:
```
====================================================================
📊 SUMMARY
====================================================================
Total images processed: 45
Metadata extracted: 38
Geocoded locations: 32
CSV descriptions updated: 38
TXT files updated: 38
Skipped (already tagged/no metadata): 7
Errors: 0

✅ Geotagging complete!
   Original files backed up with .bak extension
====================================================================
```

## Integration with IDT Workflow

This tool complements the built-in metadata extraction:

**During workflow creation:**
```bash
# New workflows with metadata enabled
idt workflow C:\Photos --metadata --geocode
```

**After workflow completion:**
```bash
# Retroactively add metadata to old workflows
python tools/geotag_workflow.py C:\idt\Descriptions\wf_OldWorkflow_...
```

## Troubleshooting

### "Could not locate original image"
- Original images were deleted or moved after workflow
- Check that input directory still exists
- Verify workflow directory structure is intact

### "No metadata for [image]"
- Image has no EXIF data (screenshots, downloaded images)
- HEIC support not installed (`pip install pillow-heif`)
- Image file is corrupted

### Geocoding Slow
- First run must contact OpenStreetMap API (1 sec delay per unique location)
- Subsequent runs use cache (instant)
- Use `--no-geocode` for GPS coordinates only (no API calls)

### Changes Not Applied
- Forgot to remove `--dry-run` flag
- Permission issues (check write access to workflow directory)
- Files locked by another program

## Best Practices

1. **Always dry-run first**: Use `--dry-run` to preview changes
2. **Keep originals**: Tool creates `.bak` files automatically
3. **Share cache**: Use same `--geocode-cache` file for multiple workflows
4. **Batch processing**: Process multiple workflows with same geocoding cache
5. **Verify results**: Check a few updated descriptions before bulk processing

## Future Enhancements

Potential additions:
- Batch mode for multiple workflows at once
- Config file for default settings
- Progress bars for large workflows
- CSV export of metadata statistics
- Integration with viewer for visual verification

## See Also

- **User Guide**: Full metadata documentation
- **CLI Reference**: Built-in metadata workflow options
- **show_metadata tool**: View metadata without updating files
