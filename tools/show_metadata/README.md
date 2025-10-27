# Show Metadata Tool

Extract and display EXIF metadata from images without running AI descriptions.

## Features

- **HEIC Support**: Reads iPhone HEIC photos (requires pillow-heif)
- **GPS Extraction**: Extracts GPS coordinates and altitude from EXIF
- **Reverse Geocoding**: Optional city/state/country lookup via OpenStreetMap Nominatim
- **CSV Export**: Export metadata to spreadsheet for analysis
- **Meta Suffix**: Shows the compact one-line metadata format used in workflows

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
# Single directory
python show_metadata.py /path/to/images

# Recursive scan
python show_metadata.py /path/to/images --recursive
```

### With Geocoding

```bash
python show_metadata.py /path/to/images \
  --geocode \
  --geocode-user-agent "YourApp/1.0 (+https://yoursite.com)" \
  --geocode-cache geocode_cache.json
```

### Export to CSV

```bash
python show_metadata.py /path/to/images \
  --csv-out metadata_report.csv
```

### Combined (Geocoding + CSV)

```bash
python show_metadata.py /path/to/images \
  --recursive \
  --geocode \
  --geocode-user-agent "IDT-ShowMetadata/3.0 (+https://github.com/kellylford/Image-Description-Toolkit)" \
  --geocode-cache geocode_cache.json \
  --csv-out metadata_full_report.csv
```

## Output Files

When run from the `tools/show_metadata/` directory, output files are saved here:
- `<name>.csv` - Metadata export
- `geocode_cache.json` - Cached geocoding results (if --geocode-cache specified)

## Options

- `--recursive`, `-r` - Process subdirectories recursively
- `--no-meta-suffix` - Hide the compact Meta suffix line
- `--geocode` - Enable reverse geocoding (requires requests library)
- `--geocode-user-agent` - User-Agent for Nominatim API (required by usage policy)
- `--geocode-delay` - Delay between geocoding requests in seconds (default: 1.0)
- `--geocode-cache` - Path to JSON cache file for geocoding results
- `--csv-out` - Path to write CSV summary of all image metadata

## CSV Columns

The CSV export includes:
- `file` - Relative path to image file
- `modified` - File modification timestamp
- `date` - Photo date from EXIF
- `latitude`, `longitude`, `altitude_m` - GPS coordinates
- `city`, `state`, `country`, `country_code` - Geocoded location (if enabled)
- `camera_make`, `camera_model`, `lens` - Camera information
- `meta_suffix` - The compact Meta line that would appear in workflow outputs

## Geocoding Notes

- Uses OpenStreetMap Nominatim API (free, public)
- Respects 1 request/second rate limit by default
- Caches results to minimize API calls
- Requires unique User-Agent per Nominatim usage policy
- Optional—runs offline if `--geocode` not specified

## Examples

### Quick inspection of a folder
```bash
python show_metadata.py ~/Pictures/2023/
```

### Scan entire iPhone backup with full metadata export
```bash
python show_metadata.py /mnt/backup/iphone \
  --recursive \
  --geocode \
  --geocode-cache geocode_cache.json \
  --csv-out iphone_full_metadata.csv
```

### Compare EXIF vs file mtime
```bash
# See which images have EXIF dates vs fallback to file modification time
python show_metadata.py ~/Downloads/ | grep -E "(Photo Date|File modified)"
```

## Dependencies

- **Pillow** (>=10) - Core EXIF reading
- **pillow-heif** (>=0.16) - HEIC file support (optional but recommended for iPhone photos)
- **requests** (>=2.31) - Geocoding support (optional, only needed with `--geocode`)

## Notes

- PNGs and screenshots typically have no EXIF metadata (will use file mtime)
- HEIC files from iPhones usually contain rich EXIF including GPS
- Geocoding is opt-in to respect privacy and network usage
- Cache file prevents repeated API calls for the same locations
- All output files save to current working directory (run from `tools/show_metadata/` for organized outputs)
