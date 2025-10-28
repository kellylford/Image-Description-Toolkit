# Geocoding Feature Documentation

## Overview

The Image Description Toolkit now supports **automatic reverse geocoding** of GPS coordinates found in image EXIF data. When enabled, GPS coordinates (latitude/longitude) are converted to human-readable city and state names, which are then included as prefixes in image descriptions.

## Example Output

**Before** (GPS coordinates only):
```
Jan 8, 2023: A person stands on a beach with the ocean in the background...
[1/8/2023 12:43P, Apple iPhone XS, 28.1007°N, 80.5681°W, 3m]
```

**After** (with geocoding):
```
Melbourne, FL Jan 8, 2023: A person stands on a beach with the ocean in the background...
[1/8/2023 12:43P, Apple iPhone XS, 28.1007°N, 80.5681°W, 3m]
```

## How to Enable

### Option 1: Guided Workflow Wizard (Easiest)
1. Run the guided workflow wizard:
   ```bash
   idt.exe
   ```
2. When prompted "Would you like to add city and state names to descriptions?", answer **Yes**
3. The wizard automatically adds `--geocode` flag to your workflow

### Option 2: Command Line Flag
Add the `--geocode` flag to any workflow command:
```bash
idt.exe workflow "path/to/images" --geocode --steps describe,html
```

### Option 3: Direct ImageDescriber Usage
```bash
python scripts/image_describer.py "path/to/images" --geocode
```

## How It Works

1. **EXIF Extraction**: GPS coordinates are extracted from image metadata
2. **Reverse Geocoding**: Coordinates are sent to OpenStreetMap Nominatim API
3. **Location Formatting**: City, state, and country are formatted as "City, State"
4. **Caching**: Results are cached locally to minimize API calls
5. **Description Prefix**: Location and date are added as prefix to description

## API Details

### Service: OpenStreetMap Nominatim
- **Free and Open**: No API key required
- **Rate Limit**: 1 request per second (enforced automatically)
- **Attribution**: "Geocoding data © OpenStreetMap contributors" (added to HTML reports)
- **Privacy**: Only GPS coordinates are sent, no image data
- **URL**: `https://nominatim.openstreetmap.org/reverse`

### Caching System
- **Cache File**: `geocode_cache.json` (configurable)
- **Format**: JSON with coordinates as keys
- **Benefits**: 
  - Respects rate limits
  - Speeds up re-runs
  - Works offline for cached locations
- **Custom Location**:
  ```bash
  idt.exe workflow images --geocode --geocode-cache "C:\path\to\cache.json"
  ```

## Configuration

### In Config File (`scripts/image_describer_config.json`)
```json
{
  "metadata": {
    "enabled": true,
    "include_location_prefix": true,
    "geocoding": {
      "enabled": true,
      "user_agent": "IDT/3.0 (+https://github.com/kellylford/Image-Description-Toolkit)",
      "delay_seconds": 1.0,
      "cache_file": "geocode_cache.json"
    }
  }
}
```

### Command Line Options
- `--geocode` - Enable reverse geocoding
- `--geocode-cache <path>` - Specify custom cache file location
- `--metadata` - Enable metadata extraction (required for geocoding)

## Requirements

- **Internet connection** for initial lookups (cached results work offline)
- **GPS data** in image EXIF (photos from smartphones typically have this)
- **Metadata enabled** (`--metadata` flag or config setting)

## Privacy & Usage Policy

### What Data is Sent
- Only GPS coordinates (latitude and longitude)
- User-Agent string identifying the toolkit
- NO image data, filenames, or personal information

### OpenStreetMap Usage Policy
We comply with Nominatim's usage policy:
- ✅ 1-second delay between requests (automatic)
- ✅ Valid User-Agent header (included)
- ✅ Appropriate use (non-commercial batch processing)
- ✅ Attribution in HTML reports
- ✅ Caching to minimize requests

**Reference**: https://operations.osmfoundation.org/policies/nominatim/

## Troubleshooting

### "GPS detected but reverse geocoding is disabled"
This log message appears when:
- Images have GPS data
- But `--geocode` flag is not enabled

**Solution**: Add `--geocode` flag to your command or re-run the guided wizard.

### No City Names Appearing
**Check these:**
1. Did you use `--geocode` flag? (Check command or wizard)
2. Is `geocode_cache.json` being created? (Check workflow directory)
3. Are your images from before the fix? (May need to re-run)
4. Check logs for "geocoding" messages (should see "Geocoding enabled" or API errors)

### Cache File Location
**Default**: Created in current working directory where executable runs

**For frozen builds (idt.exe)**: Recommended to specify absolute path:
```bash
idt.exe workflow images --geocode --geocode-cache "C:\idt\geocode_cache.json"
```

**For workflows**: Cache typically appears in the workflow output directory automatically.

### Rate Limiting
If you see "rate limit" errors:
- The toolkit automatically enforces 1-second delays
- Cache prevents redundant lookups
- Large batches may take time but will complete
- Consider running overnight for thousands of images

## Technical Details

### Race Condition Fix (Oct 2025)
Early versions had a race condition where config updates weren't visible to ImageDescriber. This was fixed by:
- Adding `f.flush()` to flush Python buffers
- Adding `os.fsync()` to force OS disk write
- Adding 100ms delay to ensure filesystem commit
- Proper frozen-mode path resolution

### Frozen Mode Path Resolution
In frozen builds (idt.exe), config paths are resolved relative to:
- `Path(sys.executable).parent / "scripts"` 

Not relative to:
- `Path(__file__).parent` (points to temp _MEIPASS directory)

## Future Enhancements

Potential features for future releases:
- [ ] Offline geocoding database option
- [ ] Configurable location format (city only, full address, etc.)
- [ ] Alternative geocoding services (Google, Bing, etc.)
- [ ] Bulk pre-caching for known locations
- [ ] Location-based grouping in reports

## Related Files

- `scripts/metadata_extractor.py` - GPS extraction and geocoding logic
- `scripts/image_describer.py` - Location prefix formatting
- `scripts/workflow.py` - Config management and geocoding flag handling
- `scripts/guided_workflow.py` - Interactive wizard prompts

## Credits

- Geocoding powered by **OpenStreetMap Nominatim**
- Map data © OpenStreetMap contributors
- Feature implemented October 2025

---

**Questions or issues?** Check the logs in your workflow's `logs/` directory for detailed error messages.
