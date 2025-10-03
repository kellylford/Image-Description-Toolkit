# Workflow Resume Functionality - Fix Summary

## Problem
The workflow resume functionality was broken due to two main issues:

### Issue #1: Step Completion Detection
**Problem**: The `parse_workflow_state()` function was looking for the string `"' completed successfully"` in log files, but the actual log format was `"' completed"` (without "successfully").

**Impact**: Completed steps (video, convert) were not being recognized, causing the resume logic to think no work had been done.

**Fix** (workflow.py line 964-970):
```python
# Now checks for both formats:
elif "Step '" in line and ("' completed successfully" in line or "' completed" in line):
    if "' completed successfully" in line:
        step_name = line.split("Step '")[1].split("' completed successfully")[0]
    else:
        step_name = line.split("Step '")[1].split("' completed")[0]
```

### Issue #2: Provider Detection Missing
**Problem**: The ONNX workflow was using `--provider onnx` but the resume logic wasn't parsing the `--provider` argument from logs.

**Impact**: ONNX workflows couldn't resume with the correct provider setting.

**Fix** (workflow.py lines 1000-1004, 1027-1030, 1210-1213):
- Added `provider` to the workflow state dictionary
- Added `--provider` parsing in command line argument extraction
- Added provider restoration when resuming: `args.provider = workflow_state["provider"]`

### Issue #3: Partial Resume Logic
**Problem**: When resuming a partially-completed describe step, the workflow would ask "Preserve existing descriptions?" If you answered "yes", it would skip the describe step entirely instead of continuing from where it left off.

**Impact**: Users couldn't continue describing remaining images - it was all-or-nothing.

**Fix** (workflow.py lines 1216-1226):
```python
# Old: Asked whether to skip describe step
# New: Always continues describe step with message:
if desc_count > 0:
    print(f"INFO: Describe step was partially completed ({desc_count} descriptions exist)")
    print(f"Will continue describing remaining images (existing descriptions will be preserved)")
```

### Issue #4: Progress Tracking Reliability
**Problem**: Tried to parse already-described images from the descriptions file, but:
- Format varies based on config settings (`include_file_path` can be true/false)
- Uses relative paths that don't match absolute paths in processing loop
- Parsing descriptions file is slow and error-prone

**Impact**: Resume would re-describe images that were already completed.

**Fix** (image_describer.py):
Created a dedicated progress tracking file:

```python
# Location: <workflow_dir>/logs/image_describer_progress.txt
# Format: One absolute path per line for each successfully described image

# On startup:
if progress_file.exists():
    # Read list of completed images
    for line in f:
        already_described.add(line.strip())

# After each successful description:
with open(progress_file, 'a') as pf:
    pf.write(f"{image_path}\n")

# During processing:
if str(image_path) in already_described:
    skip_count += 1
    logger.info(f"Skipping already-described image...")
    continue
```

## Benefits of New Progress Tracking

1. **Reliable**: Simple format (one path per line), easy to parse
2. **Fast**: Just read a list of paths, no regex or complex parsing
3. **Robust**: Works regardless of output format configuration settings
4. **Real-time**: Updated immediately after each successful description
5. **Transparent**: Human-readable file in logs directory
6. **Clean**: Separation of concerns - progress tracking separate from descriptions

## File Locations

- Progress file: `<workflow_dir>/logs/image_describer_progress.txt`
- Descriptions: `<workflow_dir>/descriptions/image_descriptions.txt`
- Workflow logs: `<workflow_dir>/logs/workflow_*.log`
- Image describer logs: `<workflow_dir>/logs/image_describer_*.log`

## Resume Workflow

When resuming a workflow:

1. **Parse workflow logs** to determine:
   - Which steps are completed (video, convert, describe, html)
   - Which images have been described (from progress file)
   - Original model, prompt_style, provider, config settings

2. **Filter remaining steps**:
   - Skip completed steps (video, convert if done)
   - Include partial steps (describe if not all images done)
   - Include pending steps (html if not done)

3. **Resume execution**:
   - Use original settings (model, prompt_style, provider)
   - Skip already-processed images (using progress file)
   - Continue from where it left off
   - Update progress file as new images are completed

## Usage

```bash
# Resume a workflow that was interrupted
python workflow.py --resume <workflow_directory>

# Example:
python workflow.py --resume wf_ollama_llava_latest_narrative_20251003_003644

# Dry-run to see what would be executed
python workflow.py --resume <workflow_directory> --dry-run
```

## Technical Notes

### Progress File Format
```
C:\path\to\workflow\temp_combined_images\09\image1.jpg
C:\path\to\workflow\temp_combined_images\converted_images\image2.jpg
C:\path\to\workflow\temp_combined_images\09\image3.png
```

### What Gets Logged
Every successful image description logs:
1. To progress file: Absolute path of image
2. To log file: "Successfully processed: <relative_path>"
3. To descriptions file: Full description entry with metadata

### Restart vs Resume
- **Restart**: Delete old workflow directory, start fresh (creates new directory)
- **Resume**: Use existing workflow directory, continue from last checkpoint

## Testing

To verify resume functionality:
1. Start a workflow with many images
2. Interrupt it (Ctrl+C) after a few images
3. Check `logs/image_describer_progress.txt` has the completed images
4. Resume with `--resume <workflow_dir>`
5. Verify it skips already-described images and continues with new ones
6. Check final descriptions file has no duplicates

## Files Modified

- `scripts/workflow.py`: Step completion detection, provider parsing, partial resume logic
- `scripts/image_describer.py`: Progress file tracking, skip logic, log_dir parameter
