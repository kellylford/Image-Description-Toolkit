# Phase 1 Implementation Quick Reference

**Status:** 🚧 Ready to Implement  
**Estimated Time:** 2-3 hours  
**Risk:** Very Low  
**Full Details:** See `CHRONOLOGICAL_ORDERING_PROPOSAL.md` (1117 lines)

---

## Three Changes to Make

### 1. Frame Naming (30 min)

**File:** `scripts/video_frame_extractor.py`  
**Line:** ~242 (in both `extract_frames_time_interval` and `extract_frames_scene_change`)

**Change:**
```python
# FROM:
filename = f"{self.config['frame_prefix']}_{timestamp:.2f}s.jpg"

# TO:
filename = f"{video_name}_{timestamp:.2f}s.jpg"
```

**Result:** `frame_12.45s.jpg` → `IMG_1235_12.45s.jpg`

---

### 2. Timestamp Preservation (30 min)

**File:** `scripts/video_frame_extractor.py`  
**Line:** ~248 (after frame save in both extraction methods)

**Add after `if success:` block:**
```python
if success:
    extracted_files.append(output_path)
    frame_count += 1
    
    # NEW: Preserve video timestamp on frame file
    video_stat = os.stat(video_path)
    os.utime(output_path, (video_stat.st_atime, video_stat.st_mtime))
```

**Result:** Frames inherit video's modification time for chronological sorting

**Note:** Also needs same change in `extract_frames_scene_change()` method (~line 315)

---

### 3. Chronological Sorting (1-2 hours)

**File:** `scripts/image_describer.py`  
**Line:** ~630-650 (in `process_directory` method)

**Replace file collection code:**
```python
# REPLACE THIS:
pattern = "**/*" if recursive else "*"
image_files = []

for file_path in directory_path.glob(pattern):
    if file_path.is_file() and self.is_supported_image(file_path):
        image_files.append(file_path)

# WITH THIS:
pattern = "**/*" if recursive else "*"
image_files_with_time = []

for file_path in directory_path.glob(pattern):
    if file_path.is_file() and self.is_supported_image(file_path):
        try:
            # Use file modification time for chronological sorting
            mtime = file_path.stat().st_mtime
            image_files_with_time.append((mtime, file_path))
        except OSError:
            # If stat fails, use current time as fallback
            import time
            image_files_with_time.append((time.time(), file_path))

# Sort chronologically (oldest first)
image_files_with_time.sort(key=lambda x: x[0])
image_files = [f[1] for f in image_files_with_time]

logger.info(f"Sorted {len(image_files)} files chronologically by modification time")
```

**Result:** Images processed in chronological order (oldest → newest)

---

## Configuration Updates (Optional)

### scripts/image_describer_config.json

Add documentation (optional):
```json
{
  "processing_options": {
    "chronological_sorting": true,
    "sort_direction": "ascending",
    "_note_sorting": "Images sorted by st_mtime (file modification time) for chronological order"
  }
}
```

### scripts/video_frame_extractor_config.json

Add documentation (optional):
```json
{
  "frame_prefix": "frame",
  "_note_frame_naming": "Frames named as {video_name}_{timestamp:.2f}s.jpg (frame_prefix not used)",
  "_note_timestamps": "Frame files inherit st_mtime from source video for chronological sorting"
}
```

---

## Testing Checklist

### Quick Tests

- [ ] **Frame Naming Test**
  ```bash
  python scripts/video_frame_extractor.py path/to/test_video.mov
  # Check: Frames named like video_12.45s.jpg
  ```

- [ ] **Timestamp Test**
  ```bash
  stat source_video.mov
  stat extracted_frames/video/video_01.00s.jpg
  # Check: Modification times match
  ```

- [ ] **Sorting Test**
  ```bash
  python scripts/image_describer.py path/to/mixed_photos/
  # Check: Descriptions in chronological order
  ```

### Full Validation

- [ ] **Europe Trip Test**
  ```bash
  python workflow.py \\ford\home\photos\MobileBackup\iPhone\2025\09
  # Check: 
  # - Frames named IMG_1235_12.45s.jpg
  # - Descriptions in chronological order
  # - Frames appear at video timestamps
  # - Can identify all frames from each video
  ```

---

## Expected Results

### Before
```
Output (random order):
- frame_01.00s.jpg (unknown source)
- frame_05.00s.jpg (unknown source)  
- IMG_1234.jpg
- IMG_1235.mov
```

### After
```
Output (chronological order):
- [2025-09-10 08:15] IMG_1234.jpg
- [2025-09-10 08:17] IMG_1235.mov
- [2025-09-10 08:17] IMG_1235_01.00s.jpg (from IMG_1235.mov)
- [2025-09-10 08:17] IMG_1235_05.00s.jpg (from IMG_1235.mov)
```

---

## Rollback Plan

If needed, revert is simple:

1. **Frame naming:** Change back to `f"{self.config['frame_prefix']}_{timestamp:.2f}s.jpg"`
2. **Timestamps:** Remove `os.utime()` calls
3. **Sorting:** Comment out sorting code

All changes are isolated and non-destructive.

---

## Key Decisions Made

- ✅ Use `st_mtime` (file modification time) for timestamps
- ✅ User-validated as accurate on Windows iPhone backups
- ✅ Frame format: `{videoname}_{timestamp:.2f}s.jpg`
- ✅ Sort direction: Oldest → Newest (ascending)
- ✅ No external dependencies (pure Python)
- ✅ Phase 1 only - enhanced formatting deferred

---

## Why This Works

**Timezone Offset Not a Problem:**
- Constant offset preserves relative ordering
- `[Europe 08:15]` → `[Local 02:15]` (6hr offset)
- `[Europe 14:30]` → `[Local 08:30]` (6hr offset)
- **08:15 still sorts before 14:30!** ✅

**st_mtime is Reliable:**
- User-tested on actual iPhone backup directory
- Accurate for photos and videos
- Fast to access (OS cached)
- Works for all file types

---

**Ready to implement when you are!** 🚀

Next: Make the three code changes above, test, then process your Europe trip!
