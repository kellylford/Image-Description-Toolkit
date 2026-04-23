# Video Support Implementation Plan for wxPython ImageDescriber

**Status:** Planning  
**Created:** February 10, 2026  
**Target Version:** 4.2.0  
**Priority:** High - Feature parity with Qt6 version  

## Executive Summary

Restore video support to the wxPython ImageDescriber that was removed during migration from Qt6. This implementation uses a simplified approach: videos and extracted frames appear as regular items in the existing image list, with no special UI components needed.

**Key Goals:**
1. ✅ Load and display video files in workspace
2. ✅ Extract frames with user-configurable options
3. ✅ Auto-process frames after extraction (optional)
4. ✅ Support batch extraction and processing
5. ✅ Maintain simple flat-list design (no tree widgets)
6. ✅ Match CLI behavior and naming conventions

---

## Background

### What Qt6 Had
- **QTreeWidget** with expandable video nodes
- Extracted frames appeared as child items under parent video
- Status prefixes: `d2` (2 descriptions), `p` (processing), `E5` (5 frames extracted)
- Separate extraction workflow from processing

### Why This Approach is Different
- **No tree widget** - use existing flat ListBox
- **Frames = regular images** - no special treatment in UI
- **Videos stay visible** after extraction (can re-extract)
- **Simple status indicators** - E{count} for videos, d{count} for all items
- **Matches CLI behavior** - same folder structure and naming

### Current State
- ✅ Full data model support (`ImageItem` with `item_type`, `extracted_frames`, `parent_video`)
- ✅ `VideoProcessingWorker` exists and is functional  
- ✅ Menu item exists: Processing → Extract Video Frames
- ❌ **Videos NOT loaded when scanning directories**
- ❌ **Frames NOT displayed in UI**
- ❌ **No extraction dialog for options**
- ❌ **No batch processing integration**

---

## Design Decisions

### Decision 1: Frame Storage Location

**Use CLI convention:** `{video_dir}/imagedescriptiontoolkit/{video_name}_frames/`

**Rationale:**
1. Consistency with CLI workflow
2. Frames stored next to source video
3. Clear separation in `imagedescriptiontoolkit/` folder
4. No duplication (workspace references by path)

**Example:**
```
C:\Videos\
├── vacation.mp4
├── interview.mp4
└── imagedescriptiontoolkit\
    ├── vacation_frames\
    │   ├── vacation_frame_00001.jpg
    │   ├── vacation_frame_00002.jpg
    │   └── vacation_frame_00003.jpg
    └── interview_frames\
        ├── interview_frame_00001.jpg
        └── interview_frame_00002.jpg
```

### Decision 2: Frame File Naming

**Pattern:** `{video_name}_frame_{number}.jpg`

**Examples:**
- `vacation_frame_00001.jpg`
- `vacation_frame_00002.jpg`
- `interview_frame_00001.jpg`

**Rationale:**
- Video name provides context in flat list
- Numbering matches CLI pattern (5-digit zero-padded)
- `.jpg` extension for universal compatibility

### Decision 3: Display Pattern

**Videos and frames appear as regular list items:**

```
🖼 photo1.jpg (d5)           # Regular image with 5 descriptions
📹 vacation.mp4 (E3)         # Video with 3 extracted frames
🖼 vacation_frame_00001.jpg (d2)  # Frame with 2 descriptions
🖼 vacation_frame_00002.jpg (d1)  # Frame with 1 description
🖼 vacation_frame_00003.jpg       # Frame without descriptions (pending)
🖼 photo2.jpg (d3)           # Regular image
📹 interview.mp4             # Video not yet extracted
```

**Status Indicators:**
- `d{count}` = Number of descriptions (images and frames)
- `E{count}` = Number of extracted frames (videos only)
- `p` = Currently processing (existing feature)

**No Special Treatment:**
- Frames are NOT visually distinguished from regular images
- No "parent video" text in screen reader announcements
- No collapse/expand functionality
- No special icons for frames (use regular image icon)

### Decision 4: Processing Workflows

#### Individual Video Processing

1. User selects video in list
2. User clicks "Process Selected" (or Processing → Process Selected Image)
3. **Extraction Options Dialog** appears:
   ```
   Extract Frames from vacation.mp4
   
   Extraction Method:
   ○ Time Interval
   ● Scene Change
   
   [Time Interval: 5] seconds
   [Scene Threshold: 30] percent
   
   ☑ Process extracted frames automatically
   
   [Extract]  [Cancel]
   ```
4. If "Process automatically" checked:
   - Extract frames
   - Immediately process each frame with current provider/model/prompt
   - Show batch progress dialog
5. If unchecked:
   - Extract frames only
   - Frames appear in list (pending descriptions)

#### Batch Processing

1. User clicks "Processing → Process All Undescribed"
2. Worker encounters video in queue:
   - **Auto-extract using config defaults** (no dialog)
   - Extract frames to standard location
   - Add frames to processing queue
   - Continue with frame processing
3. Newly extracted frames are processed in same batch run
4. Progress shows: "Processing vacation_frame_00005.jpg (12/47)"

### Decision 5: Video Item Behavior

**After Extraction:**
- Video item REMAINS in list
- Status changes from no indicator → `E{count}`
- Frames appear immediately after video in list
- User can select video and re-extract (will overwrite existing frames)

**Re-extraction:**
- Right-click video → "Re-extract Frames (Overwrite)"
- Shows same extraction dialog
- Overwrites existing frame files
- Updates workspace with new frame count

---

## Implementation Plan

### Phase 1: Core Infrastructure (2 days)

#### 1.1 Update File Loading
**File:** `imagedescriber_wx.py` → `load_directory()`

**Changes:**
- Add video extensions to scan list:
  ```python
  VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv', '.m4v'}
  
  def load_directory(self, directory: Path):
      for file_path in directory.rglob('*'):
          ext = file_path.suffix.lower()
          
          if ext in self.image_extensions:
              # Existing image loading code
              
          elif ext in VIDEO_EXTENSIONS:
              # Create video item
              item = ImageItem(str(file_path), item_type="video")
              
              # Check for existing extracted frames
              frame_dir = get_frame_directory(file_path)
              if frame_dir.exists():
                  frame_files = sorted(frame_dir.glob(f"{file_path.stem}_frame_*.jpg"))
                  for frame_path in frame_files:
                      # Create frame item
                      frame_item = ImageItem(str(frame_path), item_type="extracted_frame")
                      frame_item.parent_video = str(file_path)
                      self.workspace.add_item(frame_item)
                      item.extracted_frames.append(str(frame_path))
              
              self.workspace.add_item(item)
  ```

**Helper Function:**
```python
def get_frame_directory(video_path: Path) -> Path:
    """Get standardized frame extraction directory"""
    video_dir = video_path.parent
    video_name = video_path.stem
    return video_dir / "imagedescriptiontoolkit" / f"{video_name}_frames"
```

#### 1.2 Update List Display
**File:** `imagedescriber_wx.py` → `update_image_list()` and `format_item_for_display()`

**Changes:**
```python
def format_item_for_display(self, item: ImageItem) -> str:
    """Format item for list display with status indicators"""
    prefix_parts = []
    
    # Processing state indicator
    if item.processing_state == "processing":
        prefix_parts.append("p")
    
    # Description count (for images and frames)
    if item.item_type in ["image", "extracted_frame"]:
        desc_count = len(item.descriptions)
        if desc_count > 0:
            prefix_parts.append(f"d{desc_count}")
    
    # Extracted frame count (for videos)
    elif item.item_type == "video":
        if item.extracted_frames:
            frame_count = len(item.extracted_frames)
            prefix_parts.append(f"E{frame_count}")
    
    # Build display string
    prefix = " ".join(prefix_parts) if prefix_parts else ""
    filename = Path(item.file_path).name
    
    if prefix:
        return f"{prefix} {filename}"
    else:
        return filename
```

**Note:** No changes needed to actual ListBox widget - just the text formatting.

### Phase 2: Extraction Dialog & Worker (2 days)

#### 2.1 Create Extraction Options Dialog
**New File:** `imagedescriber/video_extraction_dialog.py`

**Dialog UI:**
```python
class VideoExtractionDialog(wx.Dialog):
    """Dialog for configuring video frame extraction options"""
    
    def __init__(self, parent, video_path: str, config: dict):
        super().__init__(parent, title=f"Extract Frames from {Path(video_path).name}")
        
        # Extraction method radio buttons
        self.time_interval_radio = wx.RadioButton(panel, label="Time Interval")
        self.scene_change_radio = wx.RadioButton(panel, label="Scene Change")
        
        # Time interval settings
        self.time_interval_spin = wx.SpinCtrlDouble(panel, value="5.0", min=0.1, max=60.0)
        
        # Scene change settings
        self.scene_threshold_spin = wx.SpinCtrl(panel, value="30", min=1, max=100)
        
        # Auto-process checkbox
        self.auto_process_check = wx.CheckBox(panel, label="Process extracted frames automatically")
        self.auto_process_check.SetValue(True)  # Default to checked
        
        # Buttons
        self.extract_btn = wx.Button(panel, wx.ID_OK, "Extract")
        self.cancel_btn = wx.Button(panel, wx.ID_CANCEL, "Cancel")
    
    def get_options(self) -> dict:
        """Get user-selected extraction options"""
        return {
            'method': 'time_interval' if self.time_interval_radio.GetValue() else 'scene_change',
            'time_interval': self.time_interval_spin.GetValue(),
            'scene_threshold': self.scene_threshold_spin.GetValue(),
            'auto_process': self.auto_process_check.GetValue()
        }
```

#### 2.2 Update VideoProcessingWorker
**File:** `workers_wx.py` → `VideoProcessingWorker`

**Verify/Update:**
- Uses `get_frame_directory()` for consistent path
- Uses frame naming pattern: `{video_name}_frame_{number:05d}.jpg`
- Follows extraction config from dialog or defaults
- Emits progress events for UI updates
- Returns list of extracted frame paths

**Integration with CLI:**
```python
def run(self):
    """Extract frames from video"""
    try:
        # Use scripts/video_frame_extractor.py logic
        from scripts.video_frame_extractor import extract_frames_from_video
        
        frame_paths = extract_frames_from_video(
            video_path=self.video_path,
            output_dir=get_frame_directory(Path(self.video_path)),
            method=self.options['method'],
            time_interval=self.options.get('time_interval', 5.0),
            scene_threshold=self.options.get('scene_threshold', 30)
        )
        
        wx.CallAfter(self.callback, True, frame_paths)
    except Exception as e:
        wx.CallAfter(self.callback, False, str(e))
```

#### 2.3 Update Processing Handler
**File:** `imagedescriber_wx.py` → `on_process_selected_image()`

**Changes:**
```python
def on_process_selected_image(self, event=None):
    """Process selected image or video"""
    if not self.current_image_item:
        return
    
    # If video, show extraction dialog first
    if self.current_image_item.item_type == "video":
        self.extract_and_process_video(self.current_image_item)
    else:
        # Existing image processing code
        self.process_single_image(self.current_image_item)

def extract_and_process_video(self, video_item: ImageItem):
    """Extract frames from video with optional auto-processing"""
    from video_extraction_dialog import VideoExtractionDialog
    
    # Load config defaults
    config = load_video_extraction_config()
    
    # Show extraction dialog
    dialog = VideoExtractionDialog(self, video_item.file_path, config)
    if dialog.ShowModal() != wx.ID_OK:
        return
    
    options = dialog.get_options()
    auto_process = options.pop('auto_process')
    
    # Start extraction worker
    worker = VideoProcessingWorker(
        video_path=video_item.file_path,
        options=options,
        callback=lambda success, result: self.on_extraction_complete(
            success, result, video_item, auto_process
        )
    )
    worker.start()
    
    # Show progress dialog
    self.show_extraction_progress_dialog(video_item)

def on_extraction_complete(self, success: bool, frame_paths: list, 
                          video_item: ImageItem, auto_process: bool):
    """Handle extraction completion"""
    if not success:
        show_error(self, f"Extraction failed: {frame_paths}")
        return
    
    # Create frame items
    for frame_path in frame_paths:
        frame_item = ImageItem(frame_path, item_type="extracted_frame")
        frame_item.parent_video = video_item.file_path
        self.workspace.add_item(frame_item)
        video_item.extracted_frames.append(frame_path)
    
    # Refresh display
    self.update_image_list()
    
    # Auto-process if requested
    if auto_process:
        self.process_extracted_frames(frame_paths)
```

### Phase 3: Batch Processing Integration (1 day)

#### 3.1 Update Batch Worker
**File:** `workers_wx.py` → `BatchProcessingWorker.run()`

**Changes:**
```python
def run(self):
    """Process all undescribed items including videos"""
    # Collect items to process
    pending_items = []
    
    for item_path, item in self.workspace.items.items():
        if item.item_type == "video":
            # Check if video needs extraction
            if not item.extracted_frames:
                pending_items.append(('extract_video', item))
        
        elif item.item_type in ["image", "extracted_frame"]:
            if not item.descriptions:
                pending_items.append(('process_image', item))
    
    # Process queue
    for i, (action, item) in enumerate(pending_items):
        if self.should_stop:
            break
        
        if action == 'extract_video':
            # Extract using config defaults
            frame_paths = self.extract_video_default(item)
            
            # Add frames to workspace and queue
            for frame_path in frame_paths:
                frame_item = ImageItem(frame_path, item_type="extracted_frame")
                frame_item.parent_video = item.file_path
                self.workspace.add_item(frame_item)
                item.extracted_frames.append(frame_path)
                
                # Add to queue for processing
                pending_items.append(('process_image', frame_item))
        
        elif action == 'process_image':
            # Existing image processing code
            self.process_single_item(item)
        
        # Update progress
        self.update_progress(i + 1, len(pending_items))
```

**Helper Method:**
```python
def extract_video_default(self, video_item: ImageItem) -> list:
    """Extract video frames using config defaults (no dialog)"""
    from scripts.video_frame_extractor import extract_frames_from_video
    
    config = load_video_extraction_config()
    
    frame_paths = extract_frames_from_video(
        video_path=video_item.file_path,
        output_dir=get_frame_directory(Path(video_item.file_path)),
        method=config.get('extraction_mode', 'time_interval'),
        time_interval=config.get('time_interval_seconds', 5.0),
        scene_threshold=config.get('scene_change_threshold', 30)
    )
    
    return frame_paths
```

### Phase 4: Workspace Persistence (1 day)

#### 4.1 Update Workspace Save/Load
**File:** `data_models.py`

**Verify Existing Serialization:**
```python
class ImageItem:
    def to_dict(self) -> dict:
        return {
            'file_path': self.file_path,
            'item_type': self.item_type,  # "image", "video", "extracted_frame"
            'parent_video': self.parent_video,  # For frames
            'extracted_frames': self.extracted_frames,  # For videos
            'descriptions': [d.to_dict() for d in self.descriptions],
            # ... other fields
        }
```

**File:** `imagedescriber_wx.py` → `load_workspace()`

**Add Validation:**
```python
def load_workspace(self, workspace_path: Path):
    """Load workspace with frame validation"""
    workspace = ImageWorkspace.load(workspace_path)
    
    # Validate that referenced files still exist
    missing_items = []
    for item_path, item in workspace.items.items():
        if not Path(item_path).exists():
            missing_items.append(item_path)
        
        # Validate extracted frames for videos
        if item.item_type == "video" and item.extracted_frames:
            valid_frames = [f for f in item.extracted_frames if Path(f).exists()]
            if len(valid_frames) != len(item.extracted_frames):
                missing_count = len(item.extracted_frames) - len(valid_frames)
                logging.warning(f"{missing_count} frames missing from {item.file_path}")
            item.extracted_frames = valid_frames
    
    # Warn user about missing files
    if missing_items:
        show_warning(self, f"{len(missing_items)} files are missing from workspace.\n"
                          f"They will be removed from the workspace.")
    
    self.workspace = workspace
    self.update_image_list()
```

### Phase 5: Context Menu & Polish (1 day)

#### 5.1 Enhanced Context Menu
**File:** `imagedescriber_wx.py` → `on_image_list_right_click()`

**Add video-specific options:**
```python
def show_context_menu(self, item: ImageItem, position):
    """Show context menu for selected item"""
    menu = wx.Menu()
    
    if item.item_type == "video":
        # Video-specific options
        if item.extracted_frames:
            menu.Append(MENU_ID_RE_EXTRACT, "Re-extract Frames (Overwrite)")
        else:
            menu.Append(MENU_ID_EXTRACT, "Extract Frames from This Video")
        
        menu.AppendSeparator()
    
    elif item.item_type == "extracted_frame":
        # Frame-specific options
        menu.Append(MENU_ID_GOTO_VIDEO, f"Go to Parent Video")
        menu.AppendSeparator()
    
    # Common options for all items
    if item.item_type in ["image", "extracted_frame"]:
        menu.Append(MENU_ID_PROCESS, "Process This Item")
        menu.Append(MENU_ID_DELETE_DESCRIPTIONS, "Delete All Descriptions")
    
    menu.Append(MENU_ID_SHOW_IN_EXPLORER, "Show in File Explorer")
    
    self.PopupMenu(menu, position)
```

#### 5.2 Statistics Display
**File:** `imagedescriber_wx.py` → `update_title()` / status bar

**Show video/frame counts:**
```python
def update_statistics(self):
    """Update status bar with workspace statistics"""
    total = len(self.workspace.items)
    videos = len([i for i in self.workspace.items.values() if i.item_type == "video"])
    frames = len([i for i in self.workspace.items.values() if i.item_type == "extracted_frame"])
    images = total - videos - frames
    
    described = len([i for i in self.workspace.items.values() 
                    if i.item_type in ["image", "extracted_frame"] and i.descriptions])
    
    processable = images + frames  # Images + frames (videos don't get descriptions)
    percentage = int((described / processable) * 100) if processable > 0 else 0
    
    status_text = f"{images} images, {videos} videos, {frames} frames | {described}/{processable} described ({percentage}%)"
    self.SetStatusText(status_text, 0)
```

---

## Testing Plan

### Unit Tests
- [ ] `get_frame_directory()` returns correct path
- [ ] Frame naming pattern: `{video_name}_frame_{number:05d}.jpg`
- [ ] Video item serialization/deserialization
- [ ] Frame validation on workspace load

### Integration Tests
- [ ] Load directory with videos and images
- [ ] Extract frames from video (individual)
- [ ] Process extracted frame (AI description)
- [ ] Batch process with videos (auto-extract + process)
- [ ] Save/load workspace with videos and frames
- [ ] Re-extract frames (overwrite existing)

### Manual Testing Scenarios

**Scenario 1: Individual Video Processing**
1. Load directory with 2 videos, 5 images
2. Select first video → "Process Selected"
3. Extraction dialog appears with config defaults
4. Change to scene detection, check "Process automatically"
5. Extract → verify frames appear below video
6. Verify frames are processed automatically
7. Verify video shows "E5" (or frame count)

**Scenario 2: Batch Processing**
1. Load directory with 3 videos, 10 images (all undescribed)
2. Click "Process All Undescribed"
3. Verify videos auto-extract using config defaults (no dialog)
4. Verify extracted frames are processed in same batch run
5. Verify progress shows frame context
6. Verify final count: videos show E{count}, frames show d{count}

**Scenario 3: Workspace Persistence**
1. Load directory, extract frames from 2 videos
2. Process some frames (not all)
3. Save workspace
4. Close ImageDescriber
5. Reopen workspace
6. Verify videos show E{count}
7. Verify frames appear below videos
8. Verify description counts preserved

**Scenario 4: Re-extraction**
1. Load workspace with already-extracted video
2. Right-click video → "Re-extract Frames (Overwrite)"
3. Change extraction settings (e.g., 10 second interval instead of 5)
4. Extract → verify fewer frames created
5. Verify old frame files are overwritten/removed
6. Verify workspace updates with new frame count

**Scenario 5: Missing Files**
1. Load workspace with videos and frames
2. Manually delete some frame files outside ImageDescriber
3. Reload workspace
4. Verify warning about missing frames
5. Verify video shows reduced frame count
6. Verify workspace still functional

---

## Configuration

### Video Extraction Config
**File:** `scripts/video_frame_extractor_config.json`

```json
{
  "extraction_mode": "time_interval",
  "time_interval_seconds": 5.0,
  "scene_change_threshold": 30,
  "output_quality": 95,
  "max_dimension": null,
  "skip_existing": false
}
```

**Used by:**
- Batch processing (auto-extract with defaults)
- Extraction dialog (pre-populate fields)
- CLI `idt workflow` command

---

## Success Criteria

### Must Have
- ✅ Videos load when scanning directories
- ✅ Individual video extraction with options dialog
- ✅ Frames appear in list as regular images
- ✅ Batch processing auto-extracts and processes frames
- ✅ Workspace saves/loads video and frame state
- ✅ Status indicators: E{count} for videos, d{count} for images/frames

### Should Have
- ✅ Re-extraction with overwrite option
- ✅ Context menu for video operations
- ✅ Statistics show video/frame counts
- ✅ Frame validation on workspace load

---

## Timeline Estimate

| Phase | Estimated Time | Dependencies |
|-------|----------------|--------------|
| Phase 1: Core Infrastructure | 2 days | None |
| Phase 2: Extraction Dialog & Worker | 2 days | Phase 1 |
| Phase 3: Batch Processing | 1 day | Phase 1, 2 |
| Phase 4: Workspace Persistence | 1 day | Phase 1 |
| Phase 5: Context Menu & Polish | 1 day | All above |
| **Testing & Documentation** | 2 days | All above |
| **Total** | **9 days** | - |

---

## Future Enhancements (v.next)

See separate GitHub issues:
- Delete individual images/frames from workspace (#TBD)
- Standardize CLI/GUI file naming and folder structure (#TBD)

---

## References

- CLI extraction: [video_frame_extractor.py](../../scripts/video_frame_extractor.py)
- Data models: [data_models.py](../../imagedescriber/data_models.py)
- Workers: [workers_wx.py](../../imagedescriber/workers_wx.py)
- Navigation analysis: [NAVIGATION_ANALYSIS.md](../archive/NAVIGATION_ANALYSIS.md)
