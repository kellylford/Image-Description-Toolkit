# Async File Loading - Testing Plan
**Date**: February 12, 2026  
**Branch**: `feature/fast-file-loading`  
**Issue**: Performance problems loading directories and workspace files over network shares

## Changes Implemented

### Phase 1: Async Directory Scanning
- **DirectoryScanWorker** in `workers_wx.py` - scans directory in background thread
- Emits batches of 50 files progressively as discovered  
- UI remains responsive during scan (no freeze)
- Events: `EVT_FILES_DISCOVERED`, `EVT_SCAN_PROGRESS`, `EVT_SCAN_COMPLETE`, `EVT_SCAN_FAILED`

### Phase 2: EXIF Date Caching
- Added `exif_datetime` and `file_mtime` fields to `ImageItem` data model
- Cache persisted in workspace `.idw` files  
- `refresh_image_list()` uses cached dates instead of re-extracting
- **Expected result**: Workspace loading is instant (no network I/O for EXIF extraction)

## Test Scenarios

### Test 1: Network Share Directory Loading (NEW BEHAVIOR)
**Path**: `\\ford\home\photos\mobilebackup\iphone\2025\09`

**Steps**:
1. Launch `imagedescriber\dist\ImageDescriber.exe`
2. File → Load Directory
3. Navigate to network share path
4. Click "Load Directory"

**Expected Behavior**:
- ✅ UI remains responsive immediately (no freeze)
- ✅ Status bar shows "Scanning..." with progressive file count
- ✅ Images appear in list progressively (batches of 50)
- ✅ Status bar updates: "Found 100 files...", "Found 200 files...", etc.
- ✅ Final status: "Loaded X files in Y.Ys"  
- ✅ Progress feedback visible throughout scan

**Old Behavior** (for comparison):
- ❌ UI froze for 2-5 minutes with no feedback
- ❌ Status bar stuck on "Loading..."
- ❌ All images appeared at once after long delay

### Test 2: Workspace File Loading (CRITICAL FIX)
**Path**: `C:\Users\kelly\Documents\ImageDescriptionToolkit\workspaces\09_20260212.idw`

**Steps**:
1. Launch `ImageDescriber.exe`
2. File → Open Workspace
3. Select `09_20260212.idw` (the workspace that was hanging)
4. Click "Open"

**Expected Behavior**:
- ✅ Workspace loads in < 2 seconds (instant)
- ✅ All images appear immediately in sorted order
- ✅ No network I/O (uses cached EXIF dates from .idw file)
- ✅ Status bar shows image count immediately

**Old Behavior** (for comparison):
- ❌ Hung for 2-5 minutes
- ❌ Re-extracted EXIF from ALL images over network
- ❌ Identical slow performance to directory loading

### Test 3: Workspace Save/Reload Cycle
**Purpose**: Verify EXIF cache persistence

**Steps**:
1. Load directory from network share (Test 1)
2. Wait for scan to complete
3. File → Save Workspace As → `test_cache.idw`
4. Close ImageDescriber
5. Relaunch and open `test_cache.idw`
6. Measure load time

**Expected Behavior**:
- ✅ First load: Progressive scan (as in Test 1)
- ✅ Save: Creates `.idw` with cached `exif_datetime` and `file_mtime` fields
- ✅ Reload: Instant load (< 2 seconds, no EXIF re-extraction)
- ✅ Verify `.idw` file contains cache: Open in text editor, search for `"exif_datetime"`

### Test 4: UI Responsiveness During Scan
**Purpose**: Ensure UI doesn't freeze

**Steps**:
1. Start loading large directory from network share
2. While "Scanning..." appears in status bar:
   - Try clicking menu items
   - Try resizing window
   - Try clicking Cancel (if available - future enhancement)

**Expected Behavior**:
- ✅ All UI interactions remain responsive
- ✅ Can use menus/dialogs during scan
- ✅ Window resizes smoothly
- ✅ No "Not Responding" in title bar

### Test 5: Mixed Local/Network Performance
**Purpose**: Verify async benefits for local directories too

**Steps**:
1. Load local directory with 500+ images: `C:\Users\kelly\Pictures`
2. Observe behavior

**Expected Behavior**:
- ✅ Still uses async scanning (consistent behavior)
- ✅ Completes faster than old synchronous method
- ✅ Progressive feedback still shown

## Performance Metrics

### Before (Synchronous, No Cache)
- **Directory load** (1000 images over network): 2-5 minutes, UI frozen
- **Workspace load** (same 1000 images): 2-5 minutes, UI frozen (full re-scan)
- **User experience**: Appears crashed, no feedback

### After (Async + Cached)
- **Directory load** (first time): 30-60 seconds, progressive feedback, UI responsive
- **Workspace load** (cached): < 2 seconds, instant
- **User experience**: Responsive, informative, professional

## Expected File Changes in Workspace

Old `.idw` format (no cache):
```json
{
  "items": {
    "\\\\ford\\home\\...\\IMG_1234.jpg": {
      "file_path": "\\\\ford\\home\\...\\IMG_1234.jpg",
      "item_type": "image",
      "descriptions": []
    }
  }
}
```

New `.idw` format (with cache):
```json
{
  "items": {
    "\\\\ford\\home\\...\\IMG_1234.jpg": {
      "file_path": "\\\\ford\\home\\...\\IMG_1234.jpg",
      "item_type": "image",
      "descriptions": [],
      "exif_datetime": "2025-09-15T14:32:18",
      "file_mtime": 1726419138.5
    }
  }
}
```

## Regression Testing

Ensure existing functionality still works:
- ✅ Image descriptions still work
- ✅ Batch processing still works  
- ✅ Video extraction still works
- ✅ Workspace save/load preserves all data
- ✅ EXIF sorting order unchanged (DateTimeOriginal → DateTimeDigitized → DateTime → mtime)

## Rollback Plan

If issues found:
1. Switch back to `WXMigration` branch: `git checkout WXMigration`
2. Rebuild: `cd imagedescriber && build_imagedescriber_wx.bat`
3. Report issues in session summary

## Success Criteria

- ✅ Network directory load completes with responsive UI
- ✅ Workspace file loads in < 2 seconds (not 2-5 minutes)
- ✅ Progressive feedback during directory scan
- ✅ No regressions in existing functionality
- ✅ User can work with network share directories productively

## Notes

- Changes are **backward compatible** - old `.idw` files work (just slower until re-saved)
- Workspace version unchanged (additive only)
- `exif_datetime` and `file_mtime` default to `None` if missing
- Fallback to extraction preserves existing behavior for edge cases
