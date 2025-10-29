# Issue: Video Frame GPS Extraction Not Working (ffprobe Missing)

**Created:** 2025-10-29  
**Priority:** Medium  
**Status:** Identified - Not Blocking  

## Problem Statement

Video frames extracted from MOV/MP4 files are missing GPS location data in their descriptions, while still images from the same workflow have complete geodata. This results in incomplete geocoding coverage for video-based content.

## Current Behavior

**What Works:**
- Still images (JPG, HEIC converted to JPG) have GPS data ✅
- Geocoding works correctly for images with GPS ✅
- Video frame extraction works ✅
- Video frame source tracking (Source: video.mov at timestamp) works ✅

**What Doesn't Work:**
- Video frames have no GPS coordinates ❌
- Video frames show "(no metadata)" in descriptions ❌
- Video frames cannot be geocoded (no city/state/country) ❌

## Root Cause

**ffprobe is not installed/available** on the system, which prevents video metadata extraction.

From workflow logs (`wf_testing_ollama_moondreamlatest_colorful_20251029_063117`):
```
frame_extractor_20251029_063119.log:INFO - Video metadata extraction disabled (ffprobe not found)
image_describer_20251029_063132.log:INFO - Getting AI description for IMG_5692_0.00s.jpg (no metadata)
image_describer_20251029_063132.log:INFO - Getting AI description for IMG_5694_0.00s.jpg (no metadata)
```

## Expected Behavior

When ffprobe is available, the system should:
1. Extract GPS coordinates from video files (stored in metadata by iPhone, Android, etc.)
2. Embed GPS into extracted frame EXIF via `exif_embedder.py`
3. Allow geocoding to add city/state/country to video frame descriptions
4. Log: `"Extracted metadata from video: GPS=True, Date=True, Camera=True"`

## Code Path

The infrastructure exists but is disabled:
- `scripts/video_metadata_extractor.py` - Extracts GPS/date/camera from videos via ffprobe
- `scripts/exif_embedder.py` - Embeds video metadata into frame EXIF
- `scripts/video_frame_extractor.py` (lines 259-269) - Calls both when ffprobe available
- Graceful degradation: Falls back to "no metadata" mode when ffprobe missing

## Impact

**Severity:** Medium (not blocking, data just incomplete)

**Current workaround:** Living without GPS data for video frames
- Still images provide most location coverage
- Video frames get descriptions, just no geocoding
- Source tracking still works (can trace back to original video)

**Users Affected:**
- Anyone processing videos with iPhone Live Photos or Android video clips
- Workflows mixing still images and video content
- Travel/event documentation with moving video

## Example

**Workflow:** `C:\idt35beta\Descriptions\wf_testing_ollama_moondreamlatest_colorful_20251029_063117`

**Still image (has GPS):**
```
File: converted_images\IMG_5692.jpg
Location: Florida, United States of America, GPS: 28.100728, -80.568056, Altitude: 3.1m
```

**Video frame (no GPS):**
```
File: extracted_frames\IMG_5692\IMG_5692_0.00s.jpg
[No Location line present]
```

## Solution Options

### Option 1: Install FFmpeg (Recommended)
**Pros:**
- Unlocks GPS extraction for video frames
- Enables complete metadata preservation (date, camera, GPS)
- Better geocoding coverage
- Professional feature completeness

**Cons:**
- External dependency (FFmpeg ~100MB download)
- Requires PATH configuration
- May raise privacy concerns (videos record GPS along entire path)

**Steps:**
1. Download FFmpeg from https://ffmpeg.org/download.html
2. Extract to `C:\Program Files\FFmpeg\` (or similar)
3. Add `C:\Program Files\FFmpeg\bin\` to system PATH
4. Verify: `ffprobe -version` in terminal
5. Rebuild IDT (no code changes needed)
6. Re-run workflow with videos

### Option 2: Bundle ffprobe with IDT (Future)
**Pros:**
- No user installation required
- Guaranteed availability
- Better UX

**Cons:**
- Increases IDT distribution size (~30MB for ffprobe.exe alone)
- Licensing considerations (FFmpeg is LGPL/GPL)
- Windows-only solution (need platform-specific binaries)

**Implementation:**
- Add `ffprobe.exe` to `BuildAndRelease/resources/`
- Update PyInstaller spec to include it
- Update `video_metadata_extractor.py` to check bundled location first
- Test frozen executable with bundled ffprobe

### Option 3: Document as Optional Feature (Current)
**Pros:**
- No code changes needed
- System works fine without it
- Users decide if they need it

**Cons:**
- Silent feature degradation (no warning in UI)
- Users may not realize they're missing data
- Inconsistent behavior (some frames have GPS, others don't)

## Privacy Considerations

Videos record GPS continuously while recording, not just at frame extraction point. This means:
- Video GPS shows location at recording time (might be different from viewing location)
- Privacy-sensitive if video recorded while moving through private areas
- Users should be aware GPS is being copied from videos to frames

**Recommendation:** Add configuration option to disable video GPS extraction even when ffprobe available.

## Testing

Once ffprobe is installed, verify with:
```bash
# Extract frames from a video with GPS
idt workflow --video-dir /path/to/videos/with/gps

# Check logs for:
grep "Extracted metadata from video" logs/frame_extractor_*.log

# Verify frame has GPS
python -c "import piexif; print(piexif.load('extracted_frames/video_0.00s.jpg')['GPS'])"

# Check descriptions file includes Location for frames
grep -A2 "extracted_frames" descriptions/image_descriptions.txt | grep "Location:"
```

## Related Code

**Files:**
- `scripts/video_metadata_extractor.py` (lines 1-200) - ffprobe wrapper
- `scripts/exif_embedder.py` (lines 1-221) - EXIF embedding
- `scripts/video_frame_extractor.py` (lines 259-269, 321-330) - Integration point

**Configuration:**
- No config needed - auto-detects ffprobe availability
- Consider adding `enable_video_gps: true/false` to workflow_config.json

## Decision Needed

1. **Should we bundle ffprobe with IDT?** (increases size, better UX)
2. **Should we add UI warning when ffprobe missing?** (user awareness)
3. **Should we add config option to disable video GPS?** (privacy control)
4. **Priority for fixing?** (currently Medium, user living without it)

## Next Steps

- [ ] Decide on solution approach (install vs bundle vs document)
- [ ] Test ffprobe installation on clean Windows system
- [ ] Update documentation with ffprobe setup instructions
- [ ] Consider adding UI indicator when video metadata disabled
- [ ] Add to FAQ: "Why don't my video frames have location data?"

---

**User Decision (2025-10-29):** Living without the data for now. Current build is acceptable without video GPS extraction. Priority remains Medium - revisit when time allows.
