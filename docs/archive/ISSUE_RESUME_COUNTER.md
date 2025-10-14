# Issue: Resume Workflow Progress Counter May Not Reflect Already-Described Images

## Summary

When resuming a workflow that has partial progress (e.g., 338 descriptions already completed), the progress counter in `image_describer.py` appears to start at "1" instead of continuing from where it left off (e.g., "339"). This creates confusion about actual progress.

## Expected Behavior

When resuming a workflow with 338 existing descriptions out of 500 total images:

```
INFO - Skipping already-described image 1 of 500: image001.jpg - (timestamp)
INFO - Skipping already-described image 2 of 500: image002.jpg - (timestamp)
...
INFO - Skipping already-described image 338 of 500: image338.jpg - (timestamp)
INFO - Describing image 339 of 500: image339.jpg - (timestamp)  ← First new image
```

## Actual Behavior

When resuming the same workflow:

```
INFO - Found 338 already-described images in progress file, will skip them - (timestamp)
INFO - Describing image 1 of [total]: image339.jpg - (timestamp)  ← Appears to start at 1
```

## Impact

- User confusion about actual progress
- Unclear whether resume is working correctly
- Statistics may be misleading (though likely still accurate in log files)

## Root Cause Analysis

### Code Path Investigation

**In `image_describer.py` (lines 702-712):**

```python
for i, image_path in enumerate(image_files, 1):
    # Check if this image was already described (resume support)
    if str(image_path) in already_described:
        skip_count += 1
        logger.info(f"Skipping already-described image {i} of {len(image_files)}: {image_path.name}")
        success_count += 1  # Count as success since it's already done
        continue
    
    # Log progress and start time for this image
    logger.info(f"Describing image {i} of {len(image_files)}: {image_path.name}")
```

**The counter logic:**
- `enumerate(image_files, 1)` starts counter `i` at 1 for ALL images
- `len(image_files)` is the TOTAL number of images (including already-described)
- When skipping, `i` increments but logs show it's being skipped
- When describing, `i` should be at the correct position (e.g., 339)

### Potential Issues

#### Issue 1: Progress File Path Mismatch

**When saving progress (`image_describer.py` line 738):**
```python
pf.write(f"{image_path}\n")  # Writes FULL path
# Example: C:\Users\...\wf_ollama_xxx\temp_combined_images\photos\img001.jpg
```

**When checking (`image_describer.py` line 704):**
```python
if str(image_path) in already_described:  # Checks against stored paths
```

**Workflow behavior (`workflow.py` lines 521-522, 722):**
```python
temp_combined_dir = self.config.base_output_dir / "temp_combined_images"
temp_combined_dir.mkdir(parents=True, exist_ok=True)
# ... processing ...
shutil.rmtree(temp_combined_dir)  # Cleaned up after processing
```

**On Resume:**
1. `temp_combined_images` is recreated with same structure
2. Files get same paths as before
3. Progress file should match these paths
4. BUT: If progress file was deleted or paths differ slightly, matching fails

#### Issue 2: Already-Described Set Population

**Progress file loading (`image_describer.py` lines 616-634):**
```python
already_described = set()
file_mode = 'w'  # Default to overwrite

# Use a progress file to track completed images
if self.log_dir:
    progress_file = Path(self.log_dir) / "image_describer_progress.txt"
else:
    progress_file = output_file.parent / "image_describer_progress.txt"

if progress_file.exists():
    logger.info(f"Found progress file: {progress_file}")
    try:
        with open(progress_file, 'r', encoding='utf-8') as f:
            for line in f:
                image_path_str = line.strip()
                if image_path_str:
                    already_described.add(image_path_str)
        logger.info(f"Found {len(already_described)} already-described images in progress file, will skip them")
```

**If this shows "Found 338 already-described images", the set IS populated correctly.**

#### Issue 3: Counter Display vs. Reality

The counter might be working correctly, but the display could be confusing:

**Hypothesis A:** Counter shows "1 of 162" (only remaining images)
- Total is adjusted to exclude already-described images
- But user expects "339 of 500" (continuing from where left off)

**Hypothesis B:** Counter shows "1 of 500" but skips aren't being logged
- Progress file paths don't match
- No images are actually skipped
- All 500 images are re-processed

**Hypothesis C:** Counter shows correctly "339 of 500" but appears as "1" due to log viewing
- Logs are being viewed incorrectly
- Or different log source (workflow.py vs image_describer.py)

## Investigation Needed

### 1. Verify Progress File

Check if `image_describer_progress.txt` exists in the logs directory after resume:

```bash
# Look for progress file
ls -la workflow_output/logs/image_describer_progress.txt

# Check content (sample first 5 and last 5 lines)
head -5 workflow_output/logs/image_describer_progress.txt
tail -5 workflow_output/logs/image_describer_progress.txt
```

### 2. Compare Paths

Verify if paths in progress file match paths being checked:

```bash
# Extract a sample path from progress file
head -1 workflow_output/logs/image_describer_progress.txt

# Check if temp_combined_images still exists (should be cleaned up)
ls -la workflow_output/temp_combined_images
```

### 3. Check Log Output

Search the actual log file for skip messages:

```bash
# Look for skip messages in the log
grep "Skipping already-described" workflow_output/logs/image_describer_*.log | wc -l
# Should show 338 if working correctly

# Look for describe messages
grep "Describing image" workflow_output/logs/image_describer_*.log | head -5
# Check if numbers start at 1 or 339
```

### 4. Verify Workflow Behavior

Check what workflow.py reports:

```bash
# Look for preserve messages in workflow log
grep "existing descriptions" workflow_output/logs/workflow_*.log
grep "Prepared.*images for single processing" workflow_output/logs/workflow_*.log
```

## Possible Solutions (No Code Changes Yet)

Based on investigation results:

### Solution 1: If Progress File Paths Don't Match

**Problem:** Path format differences (Windows backslashes, relative vs absolute)

**Fix:** Normalize paths when storing and checking:
```python
# Store normalized path
pf.write(f"{Path(image_path).as_posix()}\n")

# Check normalized path
if Path(image_path).as_posix() in already_described:
```

### Solution 2: If Total Count Confusing

**Problem:** "1 of 162" is correct but confusing

**Enhancement:** Show both numbers:
```python
logger.info(f"Describing image {i} of {len(image_files)} (new image {i - skip_count} of {len(image_files) - len(already_described)}): {image_path.name}")
# Output: "Describing image 339 of 500 (new image 1 of 162): image339.jpg"
```

### Solution 3: If Already-Described Not Working

**Problem:** Progress file not persisting or being read

**Fix:** Ensure progress file survives cleanup:
```python
# In workflow.py, preserve progress file when cleaning temp_combined_dir
# Move it to a permanent location before cleanup
```

## Testing Plan

1. **Start a fresh workflow** with 500 images
2. **Interrupt after 338 completions** (Ctrl+C)
3. **Verify progress file exists** and contains 338 entries
4. **Resume the workflow** with `--resume`
5. **Capture console output** showing counter behavior
6. **Check log files** for skip messages
7. **Verify final statistics** match expectations

## Related Code Files

- `scripts/image_describer.py` - Lines 600-750 (progress tracking and counter display)
- `scripts/workflow.py` - Lines 445-730 (describe_images method and temp directory handling)
- Progress file location: `workflow_output/logs/image_describer_progress.txt`

## Priority

**Medium** - Functionality appears correct (resume works, files aren't re-processed), but user experience is confusing and could lead to unnecessary interruptions or debugging sessions.

## Labels

- `bug` (or `enhancement` if behavior is correct but display needs improvement)
- `resume-functionality`
- `user-experience`
- `logging`

## Additional Context

- Resume functionality was recently updated to support `--preserve-descriptions` flag
- Screen-reader friendly logging format was recently implemented
- Subprocess output streaming was recently enabled
- This investigation was triggered by user observation during manual testing of resume feature

---

**Investigation Date:** October 13, 2025
**Reporter:** User observation during resume testing
**Analyst:** GitHub Copilot
