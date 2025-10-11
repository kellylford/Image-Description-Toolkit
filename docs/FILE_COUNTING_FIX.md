# File Counting Fix - Consistent Statistics Across Providers

## Problem Description

Previously, file counting statistics were inconsistent across different AI providers:
- **Cloud providers (Claude, OpenAI)**: Reported **2 files** processed
- **Local Ollama models**: Reported **1 file** processed

This created confusion about how many images were actually being described.

## Root Cause

The discrepancy occurred because:

1. When HEIC images were converted to JPG, the workflow searched multiple directories:
   - `input_dir` (containing original HEIC files)
   - `converted_dir` (containing converted JPG files)

2. The old code counted ALL images found across all directories:
   ```python
   # OLD CODE - Double counting
   search_dirs = [input_dir]
   if converted_dir.exists():
       search_dirs.append(converted_dir)  # Both dirs searched
   
   for search_dir in search_dirs:
       image_files = discovery.find_files_by_type(search_dir, "images")
       all_image_files.extend(image_files)  # HEIC + JPG both counted!
   ```

3. This resulted in counting the same logical image twice:
   - Once as `image.heic` from `input_dir`
   - Again as `image.jpg` from `converted_dir`

## Solution

The fix implements smart counting logic that:

1. **Identifies HEIC files** in the input directory
2. **Separates regular images** (JPG, PNG, etc.) from HEIC files
3. **Counts converted images OR HEIC files, but NOT both**
4. **Tracks conversions separately** from the unique image count

### New Counting Logic

```python
# NEW CODE - Smart counting
heic_files_in_input = discovery.find_files_by_type(input_dir, "heic")
all_input_images = discovery.find_files_by_type(input_dir, "images")
regular_input_images = [img for img in all_input_images if img not in heic_files_in_input]

unique_source_count = 0
conversion_count = 0

# Add regular (non-HEIC) images
unique_source_count += len(regular_input_images)

# Add converted images OR HEIC files (NOT both)
if has_conversions:
    converted_images = discovery.find_files_by_type(converted_dir, "images")
    unique_source_count += len(converted_images)
    conversion_count = len(converted_images)  # Track separately!
elif heic_files_in_input:
    unique_source_count += len(heic_files_in_input)

# Add video frames
if frames_exist:
    unique_source_count += len(frame_images)
```

## Results

### Before (Inconsistent)
```
Claude Haiku 3.5          claude    claude-3-5-haiku-20241022   narrative  2
Claude Sonnet 3.7         claude    claude-3-7-sonnet-20250219  narrative  2
Ollama LLaVA              ollama    bakllava                    narrative  1
Ollama Gemma3             ollama    gemma3                      narrative  1
OpenAI GPT-4o-mini        openai    gpt-4o-mini                 narrative  2
OpenAI GPT-4o             openai    gpt-4o                      narrative  2
```

### After (Consistent)
```
All providers will now report:
- Unique images to describe: 1
- Format conversions (HEIC → JPG): 1
- Descriptions generated: 1
```

## Statistics Changes

### Return Values
The `describe_images()` method now returns:
- `unique_images`: Count of unique source images (what user expects to see described)
- `conversions`: Count of HEIC → JPG conversions performed
- `processed`: Count of descriptions actually generated

### Log Output
New log messages provide clear information:
```
Found 0 regular image(s) in input directory
Including 1 converted image(s) from: .../image_conversion
Total unique images to describe: 1
Format conversions included: 1 (HEIC → JPG)
```

### Final Statistics
Statistics now clearly separate conversions from unique images:
```
FINAL WORKFLOW STATISTICS
==========================================================
Total files processed: 1
Videos processed: 0
Unique images processed: 1
Format conversions (HEIC → JPG): 1
Descriptions generated: 1
```

## Test Scenarios Verified

1. ✓ **Single JPG image**: unique_images=1, conversions=0
2. ✓ **Multiple JPG images**: unique_images=2, conversions=0
3. ✓ **HEIC with conversion**: unique_images=1, conversions=1
4. ✓ **Mixed JPG + HEIC with conversion**: unique_images=2, conversions=1
5. ✓ **Empty directory**: unique_images=0, conversions=0

## Validation

The code now validates that description count matches expected count:
```python
if total_processed != unique_source_count:
    logger.warning(f"Description count mismatch: processed {total_processed} but expected {unique_source_count}")
else:
    logger.info(f"✓ Validation: All {unique_source_count} unique images were described")
```

## Backward Compatibility

- The `processed` field is still returned for backward compatibility
- Statistics tracking continues to work with existing code
- Error handling includes `unique_images` and `conversions` fields even on failure

## Benefits

1. **Consistent counts across all providers** (Claude, OpenAI, Ollama)
2. **Clear separation** between source images and format conversions
3. **User-friendly** statistics that match user expectations
4. **Better troubleshooting** with validation messages
5. **No more confusion** about how many descriptions to expect

## Files Modified

- `scripts/workflow.py`:
  - `describe_images()` method - Smart counting logic
  - `_update_statistics()` method - Separate conversion tracking
  - `_log_final_statistics()` method - Clear labeling
  - Status reporting - Updated terminology
