# Plan: Add URL Image Download to ImageDescriber GUI

**TL;DR**: Port the existing CLI URL download functionality to ImageDescriber GUI by creating a new File menu item "Load Images From URL" (Ctrl+U) that downloads images from web pages using the same worker thread pattern as video extraction. Downloads will be stored in the workspace's `downloaded_images/` directory and automatically added to the workspace. This leverages ~80% existing code from `WebImageDownloader` with low risk by following the proven video extraction integration pattern.

**Estimated Effort**: 2-3 days for basic download + workspace integration  
**Risk Level**: Low-Medium (main risk: PyInstaller frozen mode testing)  
**Code Reuse**: High (~80% of logic exists in `scripts/web_image_downloader.py`)

---

## Implementation Phases

### Phase 1: Core Download Infrastructure (Day 1)

**Goal**: Basic download functionality working without batch processing integration.

#### 1.1 Add Menu Item
- **File**: `imagedescriber/imagedescriber_wx.py` (around line 1050-1100)
- **Action**: Add to File menu after "Load Directory":
  ```python
  load_url_item = file_menu.Append(wx.ID_ANY, "Load Images From &URL...\tCtrl+U")
  self.Bind(wx.EVT_MENU, self.on_load_from_url, load_url_item)
  ```
- **Shortcut**: `Ctrl+U`

#### 1.2 Create Download Settings Dialog
- **New File**: `imagedescriber/download_dialog.py`
- **Class**: `DownloadSettingsDialog` (based on `VideoExtractionDialog` pattern)
- **Fields**:
  - URL input (text field with validation)
  - Minimum image size (width × height spinners, default: 0 × 0)
  - Maximum images limit (spinner, default: unlimited/-1)
  - "Add to workspace automatically" checkbox (default: checked)
  - OK/Cancel buttons
- **Validation**: Check URL format before accepting
- **Returns**: `dict` with settings: `{'url': str, 'min_width': int, 'min_height': int, 'max_images': int, 'auto_add': bool}`

#### 1.3 Create Download Worker Thread
- **File**: `imagedescriber/workers_wx.py` (add to existing file)
- **Class**: `DownloadProcessingWorker(threading.Thread)`
- **Pattern**: Mirror `VideoProcessingWorker` architecture

#### 1.4 Import WebImageDownloader
- **File**: `imagedescriber/workers_wx.py` (top of file)
- **Add Import** with frozen mode fallback

#### 1.5 Add Menu Handler
- **File**: `imagedescriber/imagedescriber_wx.py`
- **Method**: `on_load_from_url(self, event=None)`

---

### Phase 2: Workspace Integration (Day 2)

**Goal**: Downloaded images automatically appear in workspace with proper metadata.

#### 2.1 Add Downloaded Images to Workspace
- **File**: `imagedescriber/imagedescriber_wx.py`
- **Method**: `on_workflow_complete(self, event)`
- **Modify**: Detect download completion and add images

#### 2.2 Track Download Settings
- **File**: `imagedescriber/imagedescriber_wx.py`
- **Action**: Store settings temporarily before starting worker

#### 2.3 Save Download Metadata in Workspace
- **File**: `imagedescriber/data_models.py`
- **Class**: `ImageItem`
- **Add Fields**: `download_url`, `download_timestamp`

#### 2.4 Visual Indicator for Downloaded Images
- **File**: `imagedescriber/imagedescriber_wx.py`
- **Method**: `refresh_image_list()`
- **Modify**: Add visual indicator (🌐) in list display

---

### Phase 3: PyInstaller Compatibility (Day 3)

**Goal**: Ensure frozen executable can download images.

#### 3.1 Update Hidden Imports
- **File**: `imagedescriber/imagedescriber_wx.spec`
- **Modify**: Add BeautifulSoup dependencies to `hiddenimports`

#### 3.2 Test Frozen Build
- **Command**: `cd imagedescriber && build_imagedescriber_wx.bat`
- **Verify**: Build completes, executable launches, download works

---

## Verification Steps

### Integration Testing

**Test Case 1: Basic Download**
1. Launch ImageDescriber
2. File → Load Images From URL (or Ctrl+U)
3. Enter URL, set max images
4. Click OK
5. Verify: Progress shown, images downloaded, completion message appears

**Test Case 2: Workspace Integration**
1. Create new workspace
2. File → Load Images From URL
3. Enter URL, enable "Add to workspace automatically"
4. Click OK
5. Verify: Downloaded images appear with 🌐 icon
6. Save and reload workspace
7. Verify: Downloaded images still present

**Test Case 3: Error Handling**
1. Enter invalid URL
2. Verify: Validation error shown
3. Enter unreachable URL
4. Verify: Error message shown, app stable

**Test Case 4: Frozen Executable**
1. Build: `build_imagedescriber_wx.bat`
2. Run: `dist\ImageDescriber.exe`
3. Repeat Test Case 1-3 in frozen mode
4. Verify: All functionality works

---

## Technical Decisions

### Decision 1: Item Type for Downloaded Images
**Chosen**: `item_type = "downloaded_image"`  
**Rationale**: 
- Allows filtering/grouping by source
- Can apply special handling if needed
- Mirrors `"extracted_frame"` pattern
- Metadata tracking (source URL, timestamp)

### Decision 2: Storage Location
**Chosen**: `{workspace}_workspace/downloaded_images/`  
**Rationale**:
- Mirrors `extracted_frames/` pattern (consistency)
- Workspace-relative paths (portable projects)
- Automatic cleanup when workspace deleted
- Handles untitled workspaces gracefully

### Decision 3: Worker Thread Pattern
**Chosen**: `DownloadProcessingWorker` as daemon thread (like `VideoProcessingWorker`)  
**Rationale**:
- Non-blocking UI (critical for network operations)
- Proven pattern with extensive testing
- Clean event-based communication
- Handles errors gracefully

### Decision 4: Menu Location
**Chosen**: File menu, after "Load Directory"  
**Rationale**:
- Semantically similar to loading local directory
- Natural keyboard navigation flow
- Ctrl+U shortcut available and mnemonic (&URL)

---

## Files to Create/Modify

### New Files
1. `imagedescriber/download_dialog.py` - Download settings UI (~150 lines)

### Modified Files
1. `imagedescriber/imagedescriber_wx.py`
   - Add menu item
   - Add `on_load_from_url()` handler
   - Modify `on_workflow_complete()` to handle downloads
   - Track `self.download_worker` and `self.current_download_settings`

2. `imagedescriber/workers_wx.py`
   - Import `WebImageDownloader`
   - Add `DownloadProcessingWorker` class

3. `imagedescriber/data_models.py`
   - Add `download_url` and `download_timestamp` fields to `ImageItem`

4. `imagedescriber/imagedescriber_wx.spec`
   - Add `bs4` and related to `hiddenimports`

### Unchanged (Reused)
- `scripts/web_image_downloader.py` - Import as-is ✅

---

## Success Criteria

✅ **Phase 1 Complete When**:
- Menu item "Load Images From URL" appears and opens dialog
- Dialog accepts valid URLs and rejects invalid ones
- Images download to workspace directory
- Completion message shows count

✅ **Phase 2 Complete When**:
- Downloaded images automatically appear in workspace
- Images have visual indicator (🌐 icon)
- Workspace save/load preserves downloads
- Downloaded images can be processed like regular images

✅ **Phase 3 Complete When**:
- Frozen executable builds successfully
- All Phase 1-2 functionality works in `ImageDescriber.exe`
- No import errors or crashes

---

**Created**: 2026-02-11  
**Status**: Implementation  
**Assigned**: AI Agent
