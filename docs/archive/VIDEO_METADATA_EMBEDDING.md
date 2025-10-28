# Video Metadata Embedding in Extracted Frames

## Overview

As of October 2025, the IDT Video Frame Extractor now automatically extracts GPS location, recording date/time, and camera information from source video files and embeds this metadata into each extracted frame as standard EXIF data.

## Why This Matters

**Problem:** When extracting frames from videos (especially from phones), the frames were previously saved as plain JPEGs with no metadata. This meant:
- No GPS location data
- No recording date/time  
- No camera/device information
- Frames couldn't be processed by IDT's metadata extraction features

**Solution:** Frames now have full EXIF metadata embedded, making them "first-class citizens" alongside regular photos.

## Benefits

1. **Automatic Metadata Preservation**
   - GPS coordinates from phone videos are preserved in frames
   - Recording dates are embedded properly
   - Camera/device info travels with the frames

2. **Seamless Integration**
   - Works with existing IDT metadata extraction (`--metadata` flag)
   - Geocoding works automatically on frames
   - No changes needed to workflows or processing scripts

3. **Portable Metadata**
   - EXIF data travels with the files if copied elsewhere
   - Any tool that reads EXIF can access the metadata
   - Future-proof design following standards

4. **Per-Frame Timestamps**
   - Each frame gets the source video's recording time
   - Plus an offset for the frame's position in the video
   - Maintains chronological accuracy

## Technical Details

### Requirements

**Required:**
- `piexif>=1.1.3` - For writing EXIF data to JPEGs
- Installed automatically with `pip install -r requirements.txt`

**Optional (but recommended):**
- `ffmpeg` with `ffprobe` - For extracting video metadata
- Without ffprobe: Frame extraction still works, but no metadata embedding

### How It Works

1. **Video Analysis** (once per video)
   - Uses `ffprobe` to extract metadata from video file headers
   - Looks for GPS coordinates (ISO 6709 format, common in phone videos)
   - Extracts recording date/time from creation_time tags
   - Gets camera/device make and model

2. **Frame Saving** (per frame)
   - Saves frame as JPEG using OpenCV
   - Converts video metadata to standard EXIF format
   - Embeds EXIF data into the JPEG file
   - Adds frame time offset to recording datetime

3. **Graceful Degradation**
   - If ffprobe not available: Frames saved without metadata (old behavior)
   - If video has no metadata: Frames saved normally without errors
   - Errors logged at debug level, processing continues

### Metadata Mapping

| Video Tag | EXIF Field | Notes |
|-----------|------------|-------|
| ISO 6709 location | GPS IFD | Latitude, longitude, altitude |
| creation_time | DateTimeOriginal | Plus frame offset |
| make | Make | Camera manufacturer |
| model | Model | Camera/device model |

### Video Formats Supported

All standard video formats are supported:
- `.mp4` - Most common, excellent metadata support
- `.mov` - Apple QuickTime, excellent metadata support  
- `.avi`, `.mkv`, `.wmv`, `.flv`, `.webm`, `.m4v` - Various levels of metadata support

**Best metadata support:** MP4 and MOV files from phones/cameras

## Usage

### No Configuration Required

The feature is **automatically enabled** when:
1. `piexif` is installed
2. `ffprobe` is available on the system

```bash
# Standard frame extraction - metadata embedding happens automatically
python scripts/video_frame_extractor.py
```

### Checking If It's Working

Look for this log message at startup:
```
Video metadata extraction enabled (ffprobe available)
```

Per-video you'll see:
```
Extracted metadata from video: GPS=True, Date=True, Camera=True
```

### Using With IDT Workflows

```bash
# Run workflow with metadata extraction
idt workflow --input-dir ./videos --metadata --geocode
```

Frames will:
1. Be extracted with embedded EXIF metadata
2. Have location/date prefixes added to descriptions automatically
3. Geocode properly if GPS data exists

### Verifying Embedded Metadata

#### Using IDT's Test Script

```bash
python scripts/metadata_extractor.py path/to/extracted_frame.jpg
```

#### Using ExifTool (if installed)

```bash
exiftool extracted_frame.jpg
```

Should show:
- GPS Latitude / Longitude
- Date/Time Original
- Make / Model
- User Comment: "Frame extracted with metadata from source video"

## Installation

### Standard Installation

```bash
# Install all requirements including piexif
pip install -r requirements.txt
```

### Installing ffprobe

**Windows:**
1. Download ffmpeg from https://ffmpeg.org/download.html
2. Extract and add to PATH
3. Verify: `ffprobe -version`

**macOS:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt-get install ffmpeg  # Ubuntu/Debian
sudo yum install ffmpeg      # CentOS/RHEL
```

## Troubleshooting

### "ffprobe not available" Message

**Symptom:** Log shows `Video metadata extraction disabled (ffprobe not found)`

**Solution:**
1. Install ffmpeg (includes ffprobe)
2. Ensure ffprobe is in your PATH
3. Test: `ffprobe -version`
4. Restart frame extraction

**Impact:** Frame extraction works, but no metadata embedding

### "Could not extract video metadata" Message

**Symptom:** Debug log shows extraction failure for specific video

**Possible Causes:**
- Video has no metadata (common for screen recordings, generated videos)
- Unsupported metadata format
- Corrupted video file

**Impact:** Frame extracted without metadata, processing continues

### Import Error: "No module named 'piexif'"

**Symptom:** Error when running video_frame_extractor.py

**Solution:**
```bash
pip install piexif
```

### Metadata Not Appearing in Descriptions

**Checklist:**
1. ✓ ffprobe installed and working?
2. ✓ piexif installed?
3. ✓ Source video has metadata? (Test with `ffprobe -show_format video.mp4`)
4. ✓ Using `--metadata` flag in workflow?
5. ✓ Check frame EXIF with exiftool or metadata_extractor.py

## Examples

### Example 1: Phone Video with GPS

**Input:** `vacation.mp4` recorded on iPhone
- GPS: 37.7749°N, 122.4194°W
- Date: October 15, 2025, 2:30 PM
- Device: iPhone 14 Pro

**Extracted Frame:** `vacation_0.00s.jpg`
- Contains same GPS coordinates in EXIF
- DateTimeOriginal: 2025:10:15 14:30:00
- Make: Apple
- Model: iPhone 14 Pro

**IDT Description with --metadata:**
```
San Francisco, California, USA - October 15, 2025

[AI-generated description of the scene]
```

### Example 2: Multiple Frames with Time Offsets

**Input:** 30-second video starting at 2:00 PM

**Frame at 0.00s:**
- DateTime: 2025:10:15 14:00:00

**Frame at 15.00s:**
- DateTime: 2025:10:15 14:00:15

**Frame at 30.00s:**
- DateTime: 2025:10:15 14:00:30

Each frame has the correct timestamp based on position in video.

### Example 3: Workflow Integration

```bash
# Extract frames from video directory
python scripts/video_frame_extractor.py

# Process frames with metadata
idt workflow --input-dir extracted_frames --metadata --geocode --provider ollama --model llava
```

**Result:** Descriptions include location and date information extracted from original videos

## API Reference

### VideoMetadataExtractor

```python
from video_metadata_extractor import VideoMetadataExtractor

extractor = VideoMetadataExtractor()
metadata = extractor.extract_metadata(Path('video.mp4'))

# Returns dict with:
# {
#   'gps': {'latitude': 37.7749, 'longitude': -122.4194, 'altitude': 10.5},
#   'datetime': datetime(2025, 10, 15, 14, 30, 0),
#   'camera': {'make': 'Apple', 'model': 'iPhone 14 Pro'},
#   'format_info': {'duration': 30.5, 'size': 15728640, 'format_name': 'mov,mp4,m4a,3gp,3g2,mj2'}
# }
```

### ExifEmbedder

```python
from exif_embedder import ExifEmbedder

embedder = ExifEmbedder()
success = embedder.embed_metadata(
    image_path=Path('frame.jpg'),
    metadata=video_metadata,
    frame_time=15.5  # seconds from video start
)
```

## Developer Notes

### Design Decisions

1. **Optional Dependency:** ffprobe is optional, system degrades gracefully
2. **Per-Frame Timestamps:** Adds offset to base datetime for accuracy
3. **No Performance Impact:** Metadata extracted once per video, not per frame
4. **Standard EXIF:** Uses standard GPS/DateTime tags for maximum compatibility

### Future Enhancements

Potential improvements:
- Extract additional metadata (codec info, resolution, etc.)
- Support for more metadata formats
- Batch metadata verification tool
- GUI indication of metadata status

### Testing

```bash
# Test metadata extraction from video
python scripts/video_metadata_extractor.py test_video.mp4

# Test EXIF embedding
python scripts/exif_embedder.py test_frame.jpg

# Extract frames and verify
python scripts/video_frame_extractor.py
python scripts/metadata_extractor.py extracted_frames/frame_0.00s.jpg
```

## Related Documentation

- [User Guide - Metadata Extraction](../docs/USER_GUIDE.md#metadata-extraction--geocoding)
- [CLI Reference - Metadata Flags](../docs/CLI_REFERENCE.md#metadata-options)
- [Video Frame Extractor Config](../scripts/video_frame_extractor_config.json)

## Changelog

**October 28, 2025** - Initial Implementation
- Added video metadata extraction using ffprobe
- Added EXIF embedding for extracted frames
- Integrated into video_frame_extractor.py
- Added piexif to requirements.txt
- Created documentation

---

**Questions?** Check the troubleshooting section or open an issue on GitHub.
