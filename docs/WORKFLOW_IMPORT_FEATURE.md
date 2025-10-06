# Workflow Import Feature Documentation

## Overview
The workflow import feature allows you to import descriptions from completed workflows into the ImageDescriber GUI workspace. This bridges the gap between CLI batch processing and GUI-based refinement.

## Issues Fixed

### 1. Double Success Dialog ✅
**Problem:** Import success dialog appeared twice.  
**Solution:** Removed duplicate dialog from `finally` block, keeping only one in the `try` block after successful refresh.

### 2. Missing File Path Tracking ✅
**Problem:** Files from original sources (like `09\IMG_3137.PNG`) were missing because they were processed in `temp_combined_images` directory that gets deleted after workflow completion.  
**Solution:** 
- **For future workflows**: `workflow.py` now saves `file_path_mapping.json` that maps temp paths to original source paths
- **For existing workflows**: Import parses `workflow_*.log` to find original source directory and reconstructs paths

### 3. Improved Import Statistics ✅
**Problem:** "Skipped" count didn't distinguish between duplicates and missing files.  
**Solution:** Separated into two counters:
- `duplicate_count` - Descriptions already in workspace
- `missing_file_count` - Files that couldn't be located

### 4. Sort Order Enhancements ✅
**Problem:** 
- Only had "Date" sort which was newest-first
- Default was "Filename" 
- No way to sort oldest-first

**Solution:**
- Changed default sort to "Date (Oldest First)"
- Added three sort options:
  - Filename (A-Z)
  - Date (Oldest First) - **DEFAULT**
  - Date (Newest First)

## How It Works

### File Path Resolution Strategy

The import tries multiple strategies to locate files:

1. **Mapping File** (`.json` created by new workflows)
   - Maps `temp_combined_images` paths to original source locations
   - Most reliable for future workflows

2. **Workflow Subdirectories**
   - Checks `converted_images/` and `extracted_frames/`
   - Works for HEIC conversions and video frame extractions

3. **Original Source Directory** (fallback for old workflows)
   - Parses workflow log to find "Input directory"
   - Reconstructs path by combining source dir + filename
   - Handles files like `09\IMG_3137.PNG`

4. **Absolute Paths** (last resort)
   - Tries the path as-is if it exists

### Import Process

1. Select workflow directory via file dialog
2. Check for `descriptions/file_path_mapping.json`
3. If no mapping, parse `logs/workflow_*.log` for original source
4. Parse `descriptions/image_descriptions.txt`
5. For each entry:
   - Extract File, Provider, Model, Prompt Style, Description
   - Resolve file path using strategy above
   - Create `ImageItem` and `ImageDescription` objects
   - Skip if duplicate or file missing
6. Add all items to workspace
7. Refresh view with updated content
8. Show summary: Imported, Duplicates, Missing, Errors

## Usage

### Importing a Workflow

1. Open ImageDescriber GUI
2. Go to **File → Import Workflow...**
3. Select the workflow directory (e.g., `wf_claude_claude-3-haiku-20240307_narrative_20251005_172829`)
4. Review import summary

### For Existing Workflows (Without Mapping File)

**Requirements:**
- Original source files must still exist at original location
- Workflow log file must be present in `logs/workflow_*.log`

**Expected Behavior:**
- Converted images and extracted frames: ✅ Will import
- Original source files (PNG, JPEG not needing conversion): ✅ Will import IF original source directory still exists
- Files from deleted temp directory: ❌ Will be counted as "Missing"

### For New Workflows (With Mapping File)

After the workflow.py update, all new workflows will create `descriptions/file_path_mapping.json`. This ensures:
- ✅ All file paths are preserved
- ✅ No files will be missing
- ✅ Works even if original source is moved/deleted

## Files Modified

### 1. `scripts/workflow.py`
- Added code to save `file_path_mapping.json` before deleting temp directory
- Maps temp paths to original source paths
- Logged at INFO level

### 2. `imagedescriber/imagedescriber.py`
- Added "Import Workflow..." menu item under File menu
- Implemented `import_workflow()` method with:
  - Mapping file loader
  - Workflow log parser
  - Multi-strategy path resolution
  - Progress dialog for large imports
  - Detailed error handling
- Updated sort order system:
  - Changed default from `"filename"` to `"date_oldest"`
  - Added `sort_date_oldest_action` and `sort_date_newest_action`
  - Updated `set_sort_order()` to handle three modes
  - Updated `refresh_view()` sorting logic
- Separated skip counters: `duplicate_count` and `missing_file_count`

## Testing

### Test Case 1: Import with Mapping File (Future Workflows)
1. Run a new workflow after these changes
2. Import should find ALL files (0 missing)
3. Check that `file_path_mapping.json` exists in workflow

### Test Case 2: Import without Mapping File (Existing Workflows)
1. Import an existing workflow (like the Claude Haiku one)
2. Files in `converted_images/` and `extracted_frames/`: Should import ✅
3. Files from original source: Should import IF source still exists ✅
4. Missing file count should show files from deleted temp directory

### Test Case 3: Sort Order
1. Import workflow with many images
2. Check default is "Date (Oldest First)"
3. Switch to "Date (Newest First)" - order should reverse
4. Switch to "Filename" - alphabetical order

## Known Limitations

1. **Existing workflows without mapping file**: If original source directory is moved/deleted, those files will be marked as missing
2. **Network paths**: May be slower to resolve (like `\\ford\home\photos\...`)
3. **Large imports**: 1800+ files may take 10-30 seconds to import and refresh

## Recommendations

1. **Re-run important workflows** after this update to get mapping files
2. **Keep workflow directories** until you've successfully imported them
3. **Don't move original source files** until after import
4. **For workflows with many missing files**: Consider re-running the workflow if the original source is still available

## Future Enhancements

Potential improvements for future versions:
- Batch import multiple workflows at once
- Option to copy missing files from source during import
- Auto-detect and suggest original source location
- Import preview showing what will/won't be found
- Option to skip missing files without prompting
