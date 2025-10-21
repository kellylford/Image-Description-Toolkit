# IDT Testing Checklist - October 21, 2025

## Major Fixes to Test

### 1. Enhanced Error Logging & Retry Logic ✅
**What was fixed:** 500 server errors now have detailed logging and automatic retry

**Test Steps:**
- [ ] Run a cloud workflow (Claude or OpenAI) with 20+ images
- [ ] Look for any API failures in the console output
- [ ] Verify detailed error logging shows:
  - [ ] Exact status codes (e.g., "status code: 500") 
  - [ ] Timestamps for each error
  - [ ] Image filename that failed
  - [ ] Retry attempts (e.g., "Attempt 2/4 failed, retrying in 3.2s...")
- [ ] Check if `api_errors.log` file is created with JSON error details
- [ ] Verify transient errors (5xx, timeouts) are automatically retried
- [ ] Confirm permanent errors (400, 401) are not retried wastefully

**Expected Results:**
- Detailed console error messages instead of just "(status code: 500)"
- Automatic retry attempts for server errors
- Comprehensive failure summary at end of processing

---

### 2. Date Sorting for combinedescriptions ✅  
**What was fixed:** Default sort changed from alphabetical to chronological by image date

**Test Steps:**
- [ ] Run `idt combinedescriptions` (no arguments)
- [ ] Open the generated CSV file in Excel
- [ ] Verify images are sorted by photo date (oldest to newest)
- [ ] Test legacy behavior: `idt combinedescriptions --sort name`
- [ ] Verify alphabetical sorting still works with --sort name
- [ ] Check that EXIF dates are used when available, file dates as fallback

**Expected Results:**
- Default CSV shows images in chronological order by when photos were taken
- --sort name option provides old alphabetical behavior
- Console shows "Sorting images by date (oldest to newest, extracting EXIF data)..."

---

### 3. Metadata Display & Extraction Fix 🚨 CRITICAL BUG FIXED
**What was fixed:** 
- ✅ Ollama provider now has retry logic for 500 server errors
- ✅ Metadata extraction improved with better error handling and logging
- ✅ Config updated to show EXIF metadata by default

**🔧 REBUILD REQUIRED:** You must rebuild the IDT executable for these fixes to take effect!

**Critical Bugs Fixed:**
1. **Missing Retry Logic**: Ollama provider was missing `@retry_on_api_error` decorator
2. **Silent Metadata Failures**: Better logging for metadata extraction issues
3. **iPhone Photos Should Always Have Metadata**: All iPhone/Meta glasses photos should show rich EXIF data

**Test Steps:**
- [ ] **REBUILD FIRST**: Run `builditall.bat` to rebuild IDT with the latest fixes
- [ ] **Test Run #1**: `idt workflow C:\iPhone_Photos --provider ollama --model [model]`
  - [ ] Watch console for metadata extraction logs: `"Extracted 3 metadata sections for IMG_1234.jpg"`
  - [ ] Verify NO 500 errors occur (should auto-retry now)
  - [ ] Check `descriptions\image_descriptions.txt` file
  - [ ] **ALL iPhone photos should have metadata sections** (Camera, Settings, Date Taken, etc.)
- [ ] **Test Run #2**: `idt workflow C:\Different_Photos --provider [different_provider] --model [model]`
  - [ ] Verify consistent metadata extraction across different providers
  - [ ] Check for retry attempts if any 500 errors occur (should see multiple attempts in logs)

**Expected Results for iPhone Photos:**
- **Camera:** Apple iPhone [model]
- **Settings:** f/1.8, 1/120s, ISO 64, 26mm
- **Date Taken:** 2025-10-21 14:30:22
- **GPS:** 37.7749, -122.4194 (if location enabled)
- **Image Size:** 4032x3024
- **Path:** Full file path
- **Timestamp:** When processing occurred

**Console Log Should Show:**
```
INFO - Extracted 4 metadata sections for IMG_1234.jpg
INFO - Getting AI description for IMG_1234.jpg (4 metadata sections)
```

**If 500 Errors Occur, Should See:**
```
ERROR - API error (attempt 1/3): status code 500 - retrying in 2.0s...
ERROR - API error (attempt 2/3): status code 500 - retrying in 4.0s...
INFO - Successfully processed after retry
```

---

### 4. Dynamic Window Title Updates ✅
**What was fixed:** Window title now shows progress during image description

**Test Steps:**
- [ ] Start a workflow with 10+ images
- [ ] Watch the window title bar during processing
- [ ] Verify title updates show:
  - [ ] Progress percentage (e.g., "75%")
  - [ ] Current count vs total (e.g., "18 of 24")
  - [ ] Status indicators for skipped/failed images
- [ ] Check final completion title shows success/failure summary

**Expected Results:**
- Title: "IDT - Describing Images (75%, 18 of 24)" during processing
- Title: "IDT - Describing Images (75%, 18 of 24) - Skipped" for already-processed images
- Title: "IDT - Image Description Complete (20 success, 4 failed)" when done

---

### 8. Real-Time Status File Updates ✅ NEW!
**What was fixed:** Status file now shows live progress during image description step

**Test Steps:**
- [ ] Start a workflow with 10+ images: `idt workflow C:\Photos --provider [provider] --model [model]`
- [ ] During processing, monitor the status file: `logs\status\workflow_status.log`
- [ ] Verify the status file shows real-time progress like:
  ```
  ⟳ Image description in progress: 3/10 images described (30%)
     Estimated time remaining: 2.5m
  ```
- [ ] Check that updates happen every few seconds as images are processed
- [ ] Verify final status shows completion: `✓ Image description complete (10 descriptions)`

**Expected Status File Content During Processing:**
```
Workflow Progress: 1/4 steps completed
✓ Image conversion complete (25 HEIC → JPG)
⟳ Image description in progress: 8/25 images described (32%)
   Estimated time remaining: 3.2m

Elapsed time: 1.5 minutes
```

**Expected Real-Time Updates:**
- Progress count increases as each image completes
- Percentage updates dynamically  
- Time estimates become more accurate as more images process
- Status file refreshes every 2 seconds during description step

---

### 5. Comprehensive Failure Reporting ✅
**What was fixed:** Users now get detailed failure summaries instead of silent failures

**Test Steps:**
- [ ] Run workflow that encounters some failures (try large images or rate limits)
- [ ] At end of processing, verify you see:
  - [ ] "FAILURE SUMMARY:" section in console
  - [ ] Failures grouped by category (Server Error, Rate Limit, etc.)
  - [ ] "RECOMMENDATIONS:" with specific advice for each error type
  - [ ] Failure report file created: `failure_report_[timestamp].txt`
- [ ] Open the failure report file and verify it contains detailed error info

**Expected Results:**
- No more silent failures - you always know what failed and why
- Actionable recommendations for fixing different types of failures
- Clear distinction between 16 successful vs 25 expected images

---

### 6. Image Validation ✅
**What was fixed:** Images are validated before expensive API calls

**Test Steps:**
- [ ] Test with corrupted image files
- [ ] Test with oversized images (>20MB for OpenAI, >5MB for Claude)
- [ ] Test with unsupported formats
- [ ] Verify validation failures are:
  - [ ] Caught early (before API calls)
  - [ ] Clearly reported with specific reasons
  - [ ] Included in failure summary

**Expected Results:**
- Invalid images fail fast with clear error messages
- No wasted API calls on images that will definitely fail
- Validation errors appear in failure categories

---

## Quick Validation Commands

```bash
# Test error logging and retry (expect some failures)
idt workflow C:\TestImages --provider claude --model claude-sonnet-4

# Test date sorting  
idt combinedescriptions --sort date

# Test legacy name sorting
idt combinedescriptions --sort name

# Check if config metadata is working
# Look in: C:\idt\Descriptions\[latest_workflow]\descriptions\image_descriptions.txt
```

---

### 7. Help Text Correctness Fix ✅
**What was fixed:** Analysis commands now show correct `idt` syntax instead of Python script syntax

**Test Steps:**
- [ ] Test `idt combinedescriptions --help` - should show `idt combinedescriptions` examples, not `python combine_workflow_descriptions.py`
- [ ] Test `idt stats --help` - should show `idt stats` examples, not `python analyze_workflow_stats.py`  
- [ ] Test `idt contentreview --help` - should show `idt contentreview` examples, not `python analyze_description_content.py`
- [ ] Verify main help `idt --help` correctly shows `idt` command format

**Expected Results:**
- All help text examples use the correct `idt` executable commands
- No confusion about Python script vs executable usage
- Consistent command format across all help documentation

---

## Files Modified in This Session

- `imagedescriber/ai_providers.py` - Enhanced error handling and retry logic + **CRITICAL: Added missing retry decorator to Ollama provider**
- `scripts/image_describer.py` - Added validation, failure tracking, window title updates, enhanced metadata logging
- `scripts/workflow.py` - **NEW: Real-time status file updates with progress monitoring and ETA calculation**
- `scripts/image_describer_config.json` - Enabled metadata display by default
- `analysis/combine_workflow_descriptions.py` - Changed default sort to date, fixed help text
- `analysis/content_analysis.py` - Fixed help text to show idt commands
- `analysis/stats_analysis.py` - Fixed help text to show idt commands
- `test_metadata_extraction.py` - **NEW**: Debug tool for testing metadata extraction
- `docs/USER_GUIDE.md` - Updated documentation
- `models/RunFailureNotes..md` - This analysis and implementation notes

---

## 🚨 CRITICAL: You Must Rebuild Before Testing!

**The fixes will NOT work until you rebuild the executable:**

```bash
# Rebuild IDT with latest fixes
builditall.bat
```

**Why rebuild is required:**
- Ollama provider was missing critical retry logic for 500 server errors
- Metadata extraction logging was insufficient
- Your current running workflow is using the old code without these fixes

---

## Success Criteria

- [ ] **No more mystery failures:** Every failure has a clear explanation
- [ ] **Intelligent retry:** Transient errors are automatically retried (especially Ollama 500 errors)
- [ ] **Rich metadata:** iPhone photos show full EXIF data (Camera, Settings, GPS, etc.)
- [ ] **Chronological sorting:** Photos appear in date order by default
- [ ] **Live progress:** Window title shows real-time processing status
- [ ] **Actionable feedback:** Users know exactly what to do when things fail
- [ ] **Correct documentation:** Help text shows proper idt commands, not Python scripts
- [ ] **Consistent metadata:** ALL iPhone/Meta glasses photos have metadata sections

**All major reliability and user experience issues should now be resolved!** 🎉

**NEXT STEPS:**
1. **Run `builditall.bat`** to rebuild with fixes
2. **Test with iPhone photos** - should see metadata for EVERY image
3. **Verify retry logic** - 500 errors should auto-retry instead of failing immediately
- `scripts/image_describer.py` - Added validation, failure tracking, window title updates  
- `scripts/image_describer_config.json` - Enabled metadata display by default
- `analysis/combine_workflow_descriptions.py` - Changed default sort to date, fixed help text
- `analysis/content_analysis.py` - Fixed help text to show idt commands
- `analysis/stats_analysis.py` - Fixed help text to show idt commands
- `docs/USER_GUIDE.md` - Updated documentation
- `models/RunFailureNotes..md` - This analysis and implementation notes

---

## Success Criteria

- [ ] **No more mystery failures:** Every failure has a clear explanation
- [ ] **Intelligent retry:** Transient errors are automatically retried
- [ ] **Rich metadata:** Users see camera info, GPS, dates in output
- [ ] **Chronological sorting:** Photos appear in date order by default
- [ ] **Live progress:** Window title shows real-time processing status
- [ ] **Actionable feedback:** Users know exactly what to do when things fail
- [ ] **Correct documentation:** Help text shows proper idt commands, not Python scripts

All major reliability and user experience issues from the original failure report should now be resolved! 🎉