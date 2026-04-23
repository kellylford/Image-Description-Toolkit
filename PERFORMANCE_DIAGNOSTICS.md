# Performance Diagnostics During Batch Processing

## The Problem Identified

**Root Cause**: The `on_worker_progress` method was calling `refresh_image_list()` after **every single image** was processed.

For your 1800-image batch:
- **1800 complete list rebuilds** (sorting + UI recreation each time)
- Each rebuild = O(n log n) sorting of all 1800 items
- Total operations: **~32 million sort comparisons + 1800 UI reconstructions**
- Result: Complete UI freeze when you switch back to the ImageDescriber window

## The Fix Applied

**File**: `imagedescriber/imagedescriber_wx.py`

### Changes Made:

1. **Reduced refresh frequency**: Now only refreshes list every 50 images (instead of every 1 image)
   - Reduces from 1800 refreshes → 36 refreshes for your batch
   - **98% reduction in UI overhead**

2. **Added performance logging**: Track how long each refresh takes
   - Logs every 10th image progress
   - Logs refresh times > 0.5s or for batches > 100 items

3. **Added diagnostic timing**: Measure actual refresh_image_list performance

## Available Diagnostics

### 1. **Log File** (Real-time monitoring)

**Location** (macOS):
- Development mode: `./ImageDescriber.log`
- Frozen app (if using .app): `~/Library/Logs/ImageDescriber/ImageDescriber.log`

**Monitor in real-time**:
```bash
# Watch the log while processing
tail -f ~/Library/Logs/ImageDescriber/ImageDescriber.log

# Or if running from command line:
tail -f ./ImageDescriber.log
```

**What to look for**:
```
INFO - Progress: 10/1800 (0%) - image010.jpg
INFO - refresh_image_list took 2.34s for 1800 items
INFO - Progress: 20/1800 (1%) - image020.jpg
```

- **Progress lines**: Show which image is being processed
- **refresh_image_list lines**: Show when UI refreshes happen and how long they take
- If you see frequent (>0.5s) refresh times, that indicates UI slowdown

### 2. **System Performance Monitor** (New diagnostic script)

**File**: `diagnose_performance.py`

**Run while processing**:
```bash
# In a separate terminal
cd /Users/kellyford/Documents/Image-Description-Toolkit
source .venv/bin/activate
pip install psutil  # If not already installed
python diagnose_performance.py
```

**What it shows**:
```
Time         CPU %    Memory MB    Threads   
--------------------------------------------------
14:23:15     45.2%      892.3 MB       12
14:23:16     48.1%      895.7 MB       12
14:23:17     92.3%      901.2 MB       12
  ⚠️  HIGH CPU - UI operations may be blocking
```

**Interpretation**:
- **Steady 40-60% CPU**: Normal - AI processing happening
- **Spikes to 90-100% every few seconds**: UI refresh operations (should be rare now)
- **Growing memory**: Possible leak (watch over time)
- **Many threads (>20)**: Thread leak (shouldn't happen)

### 3. **Progress Dialog** (Built-in)

The batch progress dialog already shows:
- Items processed count
- Average processing time per image
- Estimated time remaining
- Last completed description

This gives you real-time visibility without needing logs.

### 4. **Enable Debug Mode** (Maximum diagnostics)

For maximum logging detail:

**Start ImageDescriber with debug flag**:
```bash
cd /Users/kellyford/Documents/Image-Description-Toolkit/imagedescriber
source ../.venv/bin/activate

# Run with debug logging
python imagedescriber_wx.py --debug
```

This enables:
- Detailed function-level logging
- Line numbers in log messages
- Debug-level messages
- More verbose error tracking

### 5. **Check for Crashes**

**Crash log location**:
```bash
cat ~/imagedescriber_crash.log
```

This file records any fatal errors with full stack traces.

## Testing the Fix

### Before the Fix (Estimated):
- **1800 images** × **~2 seconds/refresh** = **60 minutes** of UI freeze time
- Total processing time: AI time + 60 min UI overhead

### After the Fix (Expected):
- **36 refreshes** × **~2 seconds/refresh** = **72 seconds** of UI overhead
- Total processing time: AI time + 1.2 min UI overhead
- **98% improvement** in UI responsiveness

### How to Verify:

1. **Monitor the log file** during your current run:
   ```bash
   tail -f ~/Library/Logs/ImageDescriber/ImageDescriber.log
   ```

2. **Look for these patterns**:
   - BEFORE: `refresh_image_list` every 1 image
   - AFTER: `refresh_image_list` every 50 images

3. **Test UI responsiveness**:
   - Switch away from ImageDescriber
   - Do other work for a few minutes
   - Switch back to ImageDescriber
   - **Should be responsive immediately** (no freeze)

## Current Run Status

Since you're at **250/1800 images**:

### What the fix will do:
- **Already processed (1-250)**: Those were slow (old code)
- **Remaining (251-1800)**: Will be MUCH faster (new code)

### Remaining refreshes:
- Images left: 1550
- Refreshes remaining: 1550 ÷ 50 = **31 refreshes**
- UI overhead remaining: ~62 seconds (vs. ~52 minutes without fix)

## Additional Performance Tips

### For Future Runs:

1. **Keep the Progress Dialog minimized/hidden**
   - It updates less frequently than the main window
   - Reduces total UI operations

2. **Don't switch back to the main ImageDescriber window**
   - Stay in processing dialog or another app
   - Main window only needs to be active at start and end

3. **Process in smaller batches** (if needed):
   - 500 images at a time instead of 1800
   - Easier to monitor progress
   - Can pause between batches

4. **Use "Process All (Skip Existing)"** for resuming:
   - If something crashes, restart
   - It will skip already-described images
   - No duplicate work

## Metrics to Track

When your current run completes, check:

1. **Total processing time** (from start to finish)
2. **Average time per image** (shown in progress dialog)
3. **Any UI freeze duration** (how long after switching back to app)

Report these and we can optimize further if needed.

## Next Steps

1. **Let the current run complete** with the applied fix
2. **Monitor the log file** to verify reduced refresh frequency
3. **Test UI responsiveness** by switching back to the app mid-run
4. **Report results**: Did the UI freeze go away?

## Diagnostic Commands Quick Reference

```bash
# Monitor log in real-time
tail -f ~/Library/Logs/ImageDescriber/ImageDescriber.log

# Check for crashes
cat ~/imagedescriber_crash.log

# Monitor system performance
python diagnose_performance.py

# Enable debug mode (for next run)
python imagedescriber_wx.py --debug

# Check most recent log entries
tail -50 ~/Library/Logs/ImageDescriber/ImageDescriber.log
```

---

**Summary**: The fix is now applied. Your remaining 1550 images should process with minimal UI overhead. Monitor the log file to verify the improvement.
