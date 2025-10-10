# Status Log Feature

**Date:** October 8, 2025  
**Status:** ✅ Implemented and Tested

---

## Overview

The workflow system now includes a simple, easy-to-read **`status.log`** file that provides real-time progress information for long-running workflows. This file is automatically created in the `logs/` directory and is continuously updated as the workflow progresses.

---

## Problem Solved

**Before:** Users had to dig through verbose log files to determine workflow progress. Questions like "How many images have been processed?" or "Is the workflow still running?" required manually parsing large log files.

**After:** Users can simply open `status.log` to see a clean, concise summary of current progress.

---

## Location

The status log is created at:
```
<workflow_output_dir>/logs/status.log
```

For example:
```
workflow_output/logs/status.log
```

---

## File Format

The status log is a simple text file with human-readable status information:

```
Workflow Status - Last Updated: 2025-10-08 14:30:45
======================================================================

Workflow Progress: 3/4 steps completed

✓ Video extraction complete (5 videos)
✓ Image conversion complete (12 images)
⟳ Image description in progress: 33/94 images described
○ HTML generation pending

Elapsed time: 15.3 minutes
```

---

## Status Indicators

| Symbol | Meaning |
|--------|---------|
| ✓ | Step completed successfully |
| ⟳ | Step currently in progress |
| ✗ | Step failed |
| ○ | Step pending/not started |
| ⚠ | Warning or errors encountered |

---

## What's Included

The status log shows:

1. **Last update timestamp** - When the file was last updated
2. **Overall progress** - X/Y steps completed
3. **Step-by-step status** - Which steps are done, in progress, or failed
4. **Item counts** - Number of videos, images, descriptions processed
5. **Progress during long steps** - For image description: "33/94 images described"
6. **Elapsed time** - How long the workflow has been running
7. **Error count** - If any errors were encountered

---

## Usage Examples

### Monitor Progress During Workflow

```bash
# Start a workflow in the background
python workflow.py /path/to/images --steps all &

# Watch the status in real-time
watch -n 1 cat workflow_output/logs/status.log

# Or on Windows
while ($true) { clear; cat workflow_output/logs/status.log; sleep 1 }
```

### Check If Workflow Is Still Running

```bash
# Quick check of current status
cat workflow_output/logs/status.log
```

If you see "⟳ in progress", the workflow is still running.
If all steps show "✓", the workflow is complete.

### Estimate Time Remaining

The elapsed time combined with progress gives you a rough estimate:
- If 33/94 images described in 15 minutes
- Remaining: 61 images
- Rate: ~2.2 images/minute
- Estimated remaining: ~28 minutes

---

## Implementation Details

### When Status Is Updated

The status log is updated at these key points:

1. **Workflow start** - Initial status created
2. **After each step completes** - Updated with step results
3. **After each step fails** - Updated with failure status
4. **When errors occur** - Error count updated
5. **Workflow end** - Final status written

### For Image Description Step

The image description step is the longest-running part of most workflows. The status log shows:
- Total number of images to process
- Current progress (updated after the subprocess completes)
- In future updates, could show real-time progress by monitoring output file

---

## Code Integration

### Adding Status Updates

The status log is managed by the `WorkflowLogger` class in `workflow_utils.py`:

```python
# Update status with custom messages
logger.update_status([
    "Workflow Progress: 2/4 steps",
    "",
    "✓ Video extraction complete",
    "⟳ Image conversion in progress: 5/12 images",
    ""
])
```

### In Workflow Scripts

The `WorkflowOrchestrator` automatically calls `_update_status_log()`:
- After each step completes
- After errors
- At workflow start and end

No manual intervention needed for standard workflows!

---

## Testing

A test script is provided to demonstrate the status log:

```bash
cd scripts
python test_status_log.py
```

This simulates a workflow with multiple steps and shows how the status log is updated in real-time.

---

## Future Enhancements

Possible improvements for future versions:

1. **Real-time progress during image description**
   - Monitor the output file as it's being written
   - Update status every N images (e.g., every 10 images)

2. **Estimated time remaining**
   - Calculate based on processing rate
   - Show in status log

3. **Performance metrics**
   - Images per second
   - Time per step

4. **JSON output option**
   - Machine-readable status for monitoring tools
   - Example: `status.json` alongside `status.log`

5. **Status API endpoint**
   - For web-based monitoring dashboards
   - WebSocket for real-time updates

---

## Files Modified

1. **`scripts/workflow_utils.py`**
   - Added `update_status()` method to `WorkflowLogger` class
   - Tracks `status_log_path` and `logs_dir`

2. **`scripts/workflow.py`**
   - Added `_update_status_log()` method to `WorkflowOrchestrator`
   - Calls status update after each workflow step
   - Updates status on errors and completion

3. **`scripts/test_status_log.py`** (new file)
   - Test script to demonstrate functionality
   - Simulates workflow with progress updates

---

## Benefits

✅ **Instant visibility** - Open one file to see current progress  
✅ **No log parsing** - Clean, human-readable format  
✅ **Real-time updates** - File is continuously updated  
✅ **Remote monitoring** - Can check progress via SSH/remote desktop  
✅ **Integration friendly** - Simple text format works with any monitoring tool  
✅ **Minimal overhead** - Lightweight file writes don't impact performance  

---

## Example Use Cases

### 1. Long-Running Batch Job

```bash
# Start processing 500 images overnight
python workflow.py /large/image/collection --steps all

# Next morning, quickly check progress
cat workflow_output/logs/status.log

# See: "✓ Image description complete (500 descriptions)"
```

### 2. Monitoring Remote Workflow

```bash
# SSH into remote server
ssh user@server

# Check workflow progress without digging through logs
cat /path/to/workflow_output/logs/status.log
```

### 3. Debugging Stuck Workflows

```bash
# Is the workflow frozen or still processing?
cat workflow_output/logs/status.log

# Last Updated: 2025-10-08 14:45:12  <- If this timestamp is old, it might be stuck
# ⟳ Image description in progress: 94/94 images
```

---

## Conclusion

The status log provides a simple, effective way to monitor workflow progress without the complexity of parsing verbose log files. It's automatically updated by the workflow system and requires no additional configuration.

**Location:** Always at `<output_dir>/logs/status.log`  
**Updates:** Automatic throughout workflow execution  
**Format:** Simple, human-readable text  
**Overhead:** Minimal (small text file writes)  

Just open the file anytime during or after workflow execution to see current status!
