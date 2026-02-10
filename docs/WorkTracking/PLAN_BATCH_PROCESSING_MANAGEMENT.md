# Batch Processing Management - Implementation Plan

**Created**: February 9, 2026  
**Status**: Planned  
**Priority**: High  
**Estimated Effort**: 16-20 hours

## Executive Summary

ImageDescriber has evolved from a small-batch tool to a stable, wxPython-based application capable of processing large batches of images. This plan implements essential batch management features: pause/resume/stop controls, crash recovery via workspace persistence, and a real-time stats dialog. These features bring ImageDescriber's batch capabilities in line with its new role as a robust processing tool while maintaining IDT CLI as the primary choice for massive batches.

## Background

**Original Intent**: ImageDescriber for small batches, IDT CLI for large batches  
**Current Reality**: wxPython migration + stability improvements = ImageDescriber now handles large batches excellently  
**Gap**: Missing pause/resume controls, crash recovery, processing stats  

### User Scenarios Addressed

1. **Long-Running Batches**: User processes 500 images, needs to pause for meeting, resume later
2. **Crash Recovery**: Computer crashes mid-batch, user reopens workspace and resumes from interruption
3. **Progress Monitoring**: User wants to see average processing time and estimated completion
4. **Selective Processing**: User processes a few images, likes results, wants to "process all remaining undescribed images"
5. **Concurrent Batch Prevention**: User clicks "Process All" while a batch is running - should prevent starting a second batch (could cause conflicts or wasteful reprocessing with different settings)

## Technical Foundation (Research Summary)

### Existing Capabilities ✅

- **Batch processing worker**: [workers_wx.py#L1046-L1136](../../imagedescriber/workers_wx.py) - `BatchProcessingWorker` class
- **Cancel mechanism**: `worker._cancel` flag exists but **is never called** (reference lost after `worker.start()`)
- **Progress tracking**: Title bar shows "25%, 5 of 20 images", status bar updates
- **Safe interruption**: Worker checks cancel flag BETWEEN images (not mid-image)
- **Workspace persistence**: `.idw` files save/load via JSON in [imagedescriber_wx.py#L1717-L1726](../../imagedescriber/imagedescriber_wx.py)

### Missing Capabilities ❌

- **No worker reference stored**: Can't call `cancel()` because reference is lost
- **No pause mechanism**: Only cancel flag, no pause/resume
- **No processing state field**: ImageItem lacks `processing_state` (pending/completed/failed/paused)
- **No batch state persistence**: Can't resume after close/crash
- **No UI controls**: No pause/stop buttons anywhere
- **No failed item tracking**: Errors shown in dialog but not stored
- **No progress dialog**: Only title bar updates, no dedicated stats window

### Code Patterns to Follow

| Pattern | Location | Use For |
|---------|----------|---------|
| `threading.Event` for pause/stop | [workers_wx.py#L1358-L1420](../../imagedescriber/workers_wx.py) (HEICConversionWorker) | Pause mechanism |
| Resume detection from files | [workflow.py#L2444-L2580](../../scripts/workflow.py) | Resume logic |
| Progress events | [workers_wx.py#L1087-L1090](../../imagedescriber/workers_wx.py) | Stats calculation |

## Implementation Plan

### Phase 1: Data Model & State Tracking

**Files Modified**:
- [imagedescriber/data_models.py](../../imagedescriber/data_models.py)

#### Task 1.1: Add Processing State to ImageItem

**Current Structure** (Line 60-100):
```python
class ImageItem:
    def __init__(self, file_path: str, item_type: str = "image"):
        self.file_path = file_path
        self.item_type = item_type
        self.descriptions: List[ImageDescription] = []
        self.batch_marked = False  # Unused legacy field
        # ... other fields
```

**Changes**:
```python
class ImageItem:
    def __init__(self, file_path: str, item_type: str = "image"):
        # ... existing fields ...
        self.processing_state: Optional[str] = None  # None, "pending", "processing", "completed", "failed", "paused"
        self.processing_error: Optional[str] = None  # Error message if failed
        self.batch_queue_position: Optional[int] = None  # Order in queue for resume
```

**Update Required Methods**:
- `to_dict()`: Serialize new fields
- `from_dict()`: Deserialize new fields

**Testing**:
- Save workspace with items in various states → reload → verify states persist
- Test JSON schema compatibility with old workspaces (new fields default to None)

#### Task 1.2: Add Batch State to ImageWorkspace

**Current Structure** (Line 106-278):
```python
class ImageWorkspace:
    def __init__(self):
        self.version = WORKSPACE_VERSION
        self.items: Dict[str, ImageItem] = {}
        self.cached_ollama_models: Optional[List[str]] = None
        # ... other fields
```

**Changes**:
```python
class ImageWorkspace:
    def __init__(self):
        # ... existing fields ...
        self.batch_state: Optional[dict] = None
        # Structure: {
        #     "provider": "claude",
        #     "model": "claude-opus-4-6",
        #     "prompt_style": "detailed",
        #     "custom_prompt": "...",
        #     "detection_settings": {...},
        #     "paused_at_index": 5,
        #     "total_queued": 20,
        #     "started": "2026-02-09T14:30:00"
        # }
```

**Update Required Methods**:
- `to_dict()`: Serialize batch_state
- `from_dict()`: Deserialize batch_state

**Behavior**:
- Set when batch starts (stores all parameters)
- Cleared when batch completes or user clicks Stop
- Persists through save/load for crash recovery

---

### Phase 2: Worker Pause/Resume Mechanism

**Files Modified**:
- [imagedescriber/workers_wx.py](../../imagedescriber/workers_wx.py)

#### Task 2.1: Upgrade BatchProcessingWorker with Pause/Resume

**Current Implementation** (Line 1046-1136):
```python
class BatchProcessingWorker(threading.Thread):
    def __init__(self, ...):
        self._cancel = False  # Simple boolean
    
    def run(self):
        for i, file_path in enumerate(self.file_paths, 1):
            if self._cancel:  # Check before each image
                break
            # ... process image ...
    
    def cancel(self):
        self._cancel = True
```

**Changes**:
```python
class BatchProcessingWorker(threading.Thread):
    def __init__(self, ...):
        self._stop_event = threading.Event()  # Set = stopped
        self._pause_event = threading.Event()  # Set = running, cleared = paused
        self._pause_event.set()  # Start in running state
    
    def run(self):
        for i, file_path in enumerate(self.file_paths, 1):
            # Check if stopped
            if self._stop_event.is_set():
                break
            
            # Wait if paused (blocks here until resume)
            self._pause_event.wait()
            
            # Double-check stop after unpause
            if self._stop_event.is_set():
                break
            
            # ... process image ...
    
    def pause(self):
        """Pause batch processing after current image completes"""
        self._pause_event.clear()
    
    def resume(self):
        """Resume paused batch processing"""
        self._pause_event.set()
    
    def stop(self):
        """Stop batch processing (cannot resume)"""
        self._stop_event.set()
        self._pause_event.set()  # Unblock if paused
    
    def is_paused(self) -> bool:
        """Check if currently paused"""
        return not self._pause_event.is_set()
```

**Pattern Source**: [HEICConversionWorker](../../imagedescriber/workers_wx.py#L1358-L1420) uses `threading.Event` for stop signal

**Testing**:
- Start batch → pause after 3 images → verify processing stops → resume → verify continues
- Pause → stop → verify worker exits cleanly
- Pause → close app → reopen → resume → verify picks up from next image

#### Task 2.2: Update Completion Handlers

**Files Modified**:
- [imagedescriber/imagedescriber_wx.py](../../imagedescriber/imagedescriber_wx.py)

**Locations**:
- [on_worker_complete()](../../imagedescriber/imagedescriber_wx.py#L1989-L2013): Set `item.processing_state = "completed"`
- [on_worker_failed()](../../imagedescriber/imagedescriber_wx.py#L2018-L2025): Set `item.processing_state = "failed"`, store `item.processing_error`

**New Handler**:
```python
def on_batch_complete(self, event):
    """Called when entire batch finishes (success or stopped)"""
    # Clear batch state if stopped or completed
    if event.stopped:
        # User clicked Stop - don't clear batch_state (allows resume)
        pass
    else:
        # Batch completed successfully
        self.workspace.batch_state = None
    
    # Track failed items
    failed_items = [item for item in self.workspace.items.values() 
                   if item.processing_state == "failed"]
    if failed_items:
        # Show summary: "Batch complete. 3 items failed."
        pass
    
    # Close progress dialog
    if self.batch_progress_dialog:
        self.batch_progress_dialog.Close()
        self.batch_progress_dialog = None
    
    # Cleanup worker reference
    self.batch_worker = None
    
    # Save workspace (preserves states and errors)
    self.save_workspace(self.workspace_file)
```

---

### Phase 3: Progress Dialog UI

**New File**: [imagedescriber/batch_progress_dialog.py](../../imagedescriber/batch_progress_dialog.py)

#### Task 3.1: Create BatchProgressDialog Class

**Dialog Structure**:

```
┌─ Batch Processing Progress ──────────────────┐
│                                               │
│  Processing Statistics:                      │
│  ┌──────────────────────────────────────┐    │
│  │ Images Processed: 15 / 50            │    │
│  │ Average Processing Time: 3.2 seconds │    │
│  └──────────────────────────────────────┘    │
│                                               │
│  Current Image: IMG_1234.jpg                 │
│                                               │
│  Progress: ██████░░░░░░░░░░░░░░ 30%         │
│                                               │
│  [ Pause ]  [ Stop ]  [ Close ]              │
└───────────────────────────────────────────────┘
```

**Implementation**:
```python
class BatchProgressDialog(wx.Dialog):
    def __init__(self, parent, total_images: int):
        wx.Dialog.__init__(
            self,
            parent,
            title="Batch Processing Progress",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER  # Modeless
        )
        
        # Stats list box (read-only, single-selection for accessibility)
        self.stats_list = wx.ListBox(
            self,
            style=wx.LB_SINGLE,
            name="Processing statistics"
        )
        
        # Current image label
        self.current_image_label = wx.StaticText(
            self,
            label="Current Image: (none)",
            name="Current image being processed"
        )
        
        # Progress bar
        self.progress_bar = wx.Gauge(
            self,
            range=100,
            name="Batch progress percentage"
        )
        
        # Buttons
        self.pause_button = wx.Button(self, label="Pause")
        self.stop_button = wx.Button(self, label="Stop")
        self.close_button = wx.Button(self, label="Close")
        
        # Bindings (call parent methods)
        self.pause_button.Bind(wx.EVT_BUTTON, self.on_pause_clicked)
        self.stop_button.Bind(wx.EVT_BUTTON, self.on_stop_clicked)
        self.close_button.Bind(wx.EVT_BUTTON, lambda e: self.Hide())
        
        # Layout
        self._create_layout()
        
        # State
        self.total_images = total_images
        self.parent_window = parent
    
    def update_progress(self, current: int, total: int, 
                       file_path: str, avg_time: float):
        """Update progress display (called from parent)"""
        # Update stats list
        self.stats_list.Clear()
        self.stats_list.Append(f"Images Processed: {current} / {total}")
        self.stats_list.Append(f"Average Processing Time: {avg_time:.1f} seconds")
        
        # Update current image
        filename = Path(file_path).name
        self.current_image_label.SetLabel(f"Current Image: {filename}")
        
        # Update progress bar
        percentage = int((current / total) * 100) if total > 0 else 0
        self.progress_bar.SetValue(percentage)
        
        # Force refresh
        self.Layout()
    
    def on_pause_clicked(self, event):
        """Toggle pause/resume"""
        if self.pause_button.GetLabel() == "Pause":
            self.parent_window.on_pause_batch()
            self.pause_button.SetLabel("Resume")
        else:
            self.parent_window.on_resume_batch()
            self.pause_button.SetLabel("Pause")
    
    def on_stop_clicked(self, event):
        """Stop processing"""
        # Confirm before stopping
        result = ask_yes_no(
            self,
            "Stop batch processing?\n\nProgress will be saved. "
            "You can resume later by reopening this workspace."
        )
        if result:
            self.parent_window.on_stop_batch()
```

**Accessibility**:
- ListBox for stats (single tab stop, arrow keys navigate, full text to screen readers)
- Named controls for screen reader context
- Large click targets for buttons

**Testing**:
- Open dialog → verify stats list readable with screen reader
- Update progress rapidly (100 updates/sec) → verify no lag
- Minimize dialog → verify batch continues → restore → verify stats updated

#### Task 3.2: Integrate Dialog into Main Window

**File Modified**: [imagedescriber/imagedescriber_wx.py](../../imagedescriber/imagedescriber_wx.py)

**Changes to `__init__()`** (Line 334):
```python
def __init__(self):
    # ... existing initialization ...
    self.batch_worker: Optional[BatchProcessingWorker] = None  # NEW: Store worker reference
    self.batch_progress_dialog: Optional[BatchProgressDialog] = None  # NEW: Progress dialog
    self.batch_start_time: Optional[float] = None  # NEW: For avg time calculation
    self.batch_processing_times: List[float] = []  # NEW: Track times per image
```

**Changes to `on_process_all()`** (Line 1533-1587):

**Current Code**:
```python
def on_process_all(self, event):
    # ... collect images to process ...
    
    worker = BatchProcessingWorker(...)  # Line 1574
    worker.start()  # ← REFERENCE LOST HERE
    
    self.SetStatusText(f"Processing {len(to_process)} images...", 0)
```

**Updated Code**:
```python
def on_process_all(self, event):
    # ... existing dialog and collection code ...
    
    # Mark items as pending BEFORE starting batch
    queue_position = 0
    for file_path in to_process:
        item = self.workspace.items[file_path]
        item.processing_state = "pending"
        item.batch_queue_position = queue_position
        queue_position += 1
    
    # Store batch parameters for resume
    self.workspace.batch_state = {
        "provider": options['provider'],
        "model": options['model'],
        "prompt_style": options.get('prompt_style', 'default'),
        "custom_prompt": options.get('custom_prompt'),
        "detection_settings": options.get('detection_settings'),
        "total_queued": len(to_process),
        "started": datetime.now().isoformat()
    }
    
    # Store worker reference (KEY FIX)
    self.batch_worker = BatchProcessingWorker(...)
    self.batch_worker.start()
    
    # Show progress dialog
    self.batch_progress_dialog = BatchProgressDialog(self, len(to_process))
    self.batch_progress_dialog.Show()
    
    # Initialize timing
    self.batch_start_time = time.time()
    self.batch_processing_times = []
    
    # Save workspace (preserves batch_state)
    self.save_workspace(self.workspace_file)
```

**Changes to `on_worker_progress()`** (Line 1967-1984):

**Current Code**:
```python
def on_worker_progress(self, event):
    # Update title bar with percentage
    if self.batch_progress:
        current = self.batch_progress['current']
        total = self.batch_progress['total']
        percentage = int((current / total) * 100)
        # ... update title ...
```

**Updated Code**:
```python
def on_worker_progress(self, event):
    # ... existing title bar update ...
    
    # Track processing time for this image
    if self.batch_start_time:
        elapsed = time.time() - self.batch_start_time
        self.batch_processing_times.append(elapsed)
        self.batch_start_time = time.time()  # Reset for next image
    
    # Calculate average time
    avg_time = (sum(self.batch_processing_times) / len(self.batch_processing_times)
                if self.batch_processing_times else 0.0)
    
    # Update progress dialog
    if self.batch_progress_dialog and self.batch_progress:
        self.batch_progress_dialog.update_progress(
            current=self.batch_progress['current'],
            total=self.batch_progress['total'],
            file_path=self.batch_progress['file_path'],
            avg_time=avg_time
        )
```

#### Task 3.3: Add Pause/Resume/Stop Handlers

**New Methods** in [imagedescriber_wx.py](../../imagedescriber/imagedescriber_wx.py):

```python
def on_pause_batch(self):
    """Pause batch processing"""
    if not self.batch_worker:
        return
    
    self.batch_worker.pause()
    
    # Update title bar
    if self.batch_progress:
        current = self.batch_progress['current']
        total = self.batch_progress['total']
        percentage = int((current / total) * 100)
        self.update_window_title(f"(Paused) {percentage}%, {current} of {total}")
    
    # Mark current item as paused
    if self.batch_progress and self.batch_progress.get('file_path'):
        file_path = self.batch_progress['file_path']
        if file_path in self.workspace.items:
            item = self.workspace.items[file_path]
            if item.processing_state == "pending":
                item.processing_state = "paused"
    
    # Save workspace (preserves paused state)
    if self.workspace_file:
        self.save_workspace(self.workspace_file)
    
    self.SetStatusText("Batch processing paused", 0)

def on_resume_batch(self):
    """Resume paused batch processing"""
    if not self.batch_worker:
        return
    
    self.batch_worker.resume()
    
    # Update title bar (remove "Paused")
    if self.batch_progress:
        current = self.batch_progress['current']
        total = self.batch_progress['total']
        percentage = int((current / total) * 100)
        self.update_window_title(f"{percentage}%, {current} of {total}")
    
    # Unpause items
    for item in self.workspace.items.values():
        if item.processing_state == "paused":
            item.processing_state = "pending"
    
    self.SetStatusText("Batch processing resumed", 0)

def on_stop_batch(self):
    """Stop batch processing permanently"""
    if not self.batch_worker:
        return
    
    # Call worker stop
    self.batch_worker.stop()
    
    # Clear batch state (won't resume automatically)
    self.workspace.batch_state = None
    
    # Reset item states (leave completed/failed as-is)
    for item in self.workspace.items.values():
        if item.processing_state in ["pending", "paused"]:
            item.processing_state = None
            item.batch_queue_position = None
    
    # Close progress dialog
    if self.batch_progress_dialog:
        self.batch_progress_dialog.Close()
        self.batch_progress_dialog = None
    
    # Save workspace
    if self.workspace_file:
        self.save_workspace(self.workspace_file)
    
    # Clear worker reference
    self.batch_worker = None
    
    self.SetStatusText("Batch processing stopped", 0)
    show_info(self, "Batch processing stopped.\n\nCompleted descriptions have been saved.")
```

---

### Phase 4: Resume Functionality

**File Modified**: [imagedescriber/imagedescriber_wx.py](../../imagedescriber/imagedescriber_wx.py)

#### Task 4.1: Detect Resumable Batch on Load

**Location**: After workspace load in `on_load_workspace()` or `on_open_workspace()`

**Implementation**:
```python
def on_load_workspace(self, file_path):
    """Load workspace from .idw file"""
    # ... existing load logic ...
    
    # Check for resumable batch
    if self.workspace.batch_state:
        self.prompt_resume_batch()

def prompt_resume_batch(self):
    """Show dialog to resume interrupted batch"""
    batch_state = self.workspace.batch_state
    
    # Count remaining items
    pending_items = [
        item for item in self.workspace.items.values()
        if item.processing_state in ["pending", "paused"]
    ]
    
    if not pending_items:
        # No items to resume - clear stale batch state
        self.workspace.batch_state = None
        return
    
    total = batch_state.get('total_queued', len(pending_items))
    completed = total - len(pending_items)
    
    message = (
        f"Resume batch processing?\n\n"
        f"Progress: {completed} of {total} images completed\n"
        f"Remaining: {len(pending_items)} images\n\n"
        f"Provider: {batch_state.get('provider', 'Unknown')}\n"
        f"Model: {batch_state.get('model', 'Unknown')}\n"
        f"Prompt: {batch_state.get('prompt_style', 'Unknown')}"
    )
    
    result = ask_yes_no(self, message)
    
    if result:
        self.resume_batch_processing()
    else:
        # User declined - clear batch state
        self.workspace.batch_state = None
        for item in self.workspace.items.values():
            if item.processing_state in ["pending", "paused"]:
                item.processing_state = None
                item.batch_queue_position = None
        self.save_workspace(self.workspace_file)
```

#### Task 4.2: Implement Resume Logic

**New Method**:
```python
def resume_batch_processing(self):
    """Resume batch processing from saved state"""
    if not self.workspace.batch_state:
        return
    
    batch_state = self.workspace.batch_state
    
    # Collect items to process (pending or paused only)
    to_process = [
        item for item in self.workspace.items.values()
        if item.processing_state in ["pending", "paused"]
    ]
    
    # Sort by queue position to maintain original order
    to_process.sort(key=lambda item: item.batch_queue_position or 0)
    
    # Extract file paths
    file_paths = [item.file_path for item in to_process]
    
    if not file_paths:
        show_info(self, "No images to resume processing.")
        self.workspace.batch_state = None
        return
    
    # Recreate processing options from batch state
    options = {
        'provider': batch_state['provider'],
        'model': batch_state['model'],
        'prompt_style': batch_state.get('prompt_style', 'default'),
        'custom_prompt': batch_state.get('custom_prompt'),
        'detection_settings': batch_state.get('detection_settings'),
        'skip_existing': True  # Always skip completed
    }
    
    # Get prompt config path
    from shared.wx_common import find_config_file
    prompt_config_path = find_config_file('image_describer_config.json')
    
    # Reset items to pending (from paused)
    for item in to_process:
        item.processing_state = "pending"
    
    # Start worker
    self.batch_worker = BatchProcessingWorker(
        parent_window=self,
        file_paths=file_paths,
        provider=options['provider'],
        model=options['model'],
        prompt_style=options['prompt_style'],
        custom_prompt=options.get('custom_prompt'),
        detection_settings=options.get('detection_settings'),
        prompt_config_path=str(prompt_config_path) if prompt_config_path else None,
        skip_existing=True
    )
    self.batch_worker.start()
    
    # Show progress dialog (starting from resumed position)
    total = batch_state.get('total_queued', len(file_paths))
    self.batch_progress_dialog = BatchProgressDialog(self, total)
    self.batch_progress_dialog.Show()
    
    # Initialize timing
    self.batch_start_time = time.time()
    self.batch_processing_times = []
    
    self.SetStatusText(f"Resuming batch: {len(file_paths)} images remaining...", 0)
```

---

### Phase 5: Process All Behavior

**File Modified**: [imagedescriber/imagedescriber_wx.py](../../imagedescriber/imagedescriber_wx.py)

#### Task 5.1: Update Menu Structure

**Current Menu** (Line 700-732):
```
Process &Current Image
Process &All Images        ← CHANGES HERE
```

**New Menu Structure**:
```
Process &Current Image
─────────────────────────
Process &Undescribed Images    ← NEW: skip_existing=True (SAFE DEFAULT)
&Redescribe All Images          ← NEW: skip_existing=False (with warning)
```

**Implementation**:
```python
# In create_menu_bar()
process_menu = wx.Menu()

# ... existing Process Current Image ...

process_menu.AppendSeparator()

# Process undescribed (SAFE - won't overwrite work)
process_undesc_item = process_menu.Append(
    wx.ID_ANY,
    "Process &Undescribed Images",
    "Process only images without descriptions"
)
self.Bind(wx.EVT_MENU, lambda e: self.on_process_all(e, skip_existing=True), process_undesc_item)

# Redescribe all (DESTRUCTIVE - show warning)
redescribe_all_item = process_menu.Append(
    wx.ID_ANY,
    "&Redescribe All Images",
    "Reprocess ALL images (replaces existing descriptions)"
)
self.Bind(wx.EVT_MENU, lambda e: self.on_process_all(e, skip_existing=False), redescribe_all_item)
```

#### Task 5.2: Update on_process_all() Signature

**Current**:
```python
def on_process_all(self, event):
    # ... shows dialog with checkbox for skip_existing ...
```

**Updated**:
```python
def on_process_all(self, event, skip_existing: bool = True):
    """Process images in batch
    
    Args:
        event: Menu event
        skip_existing: If True, only process images without descriptions (default)
                      If False, reprocess all images (show warning first)
    """
    # Check if batch already running - prevent concurrent batches
    if self.batch_worker and self.batch_worker.is_alive():
        show_warning(
            self,
            "Batch processing already in progress.\n\n"
            "Please pause or stop the current batch before starting a new one."
        )
        return
    
    if not skip_existing:
        # Warn about redescribing
        result = ask_yes_no(
            self,
            "Redescribe ALL images?\n\n"
            "This will REPLACE existing descriptions with new ones.\n"
            "This action cannot be undone.\n\n"
            "Continue?"
        )
        if not result:
            return
    
    # ... rest of method, use skip_existing parameter ...
    
    # Collection logic:
    if skip_existing:
        to_process = [
            item.file_path for item in self.workspace.items.values()
            if not item.descriptions  # Skip images with descriptions
        ]
    else:
        to_process = [
            item.file_path for item in self.workspace.items.values()
            # Process everything
        ]
```

---

### Phase 6: Visual Indicators

**File Modified**: [imagedescriber/imagedescriber_wx.py](../../imagedescriber/imagedescriber_wx.py)

#### Task 6.1: Update Image List Display

**Location**: [refresh_image_list()](../../imagedescriber/imagedescriber_wx.py#L1393-L1450)

**Current Prefix Logic** (Line 1418-1432):
```python
# 1. Description count
desc_count = len(item.descriptions)
if desc_count > 0:
    prefix_parts.append(f"d{desc_count}")

# 2. Processing indicator (P)
if file_path in self.processing_items:
    prefix_parts.append("P")
```

**Updated Logic**:
```python
# 1. Description count
desc_count = len(item.descriptions)
if desc_count > 0:
    prefix_parts.append(f"d{desc_count}")

# 2. Processing state indicators
if file_path in self.processing_items:
    prefix_parts.append("P")  # Currently processing
elif item.processing_state == "paused":
    prefix_parts.append("⏸")  # Paused (or "!" if Unicode issues)
elif item.processing_state == "failed":
    prefix_parts.append("✗")  # Failed (or "X")
elif item.processing_state == "pending":
    prefix_parts.append("⋯")  # Pending (or "...")
```

**Alternative (ASCII-safe)**:
```python
STATE_INDICATORS = {
    "processing": "P",
    "paused": "!",
    "failed": "X",
    "pending": "."
}
```

**Testing**:
- Pause batch → verify paused items show indicator
- Resume → verify indicator disappears
- Fail an item (disconnect network mid-API call) → verify X indicator
- Select failed item → verify error message shown in description area

#### Task 6.2: Update Title Bar for Paused State

**Location**: [on_worker_progress()](../../imagedescriber/imagedescriber_wx.py#L1977)

**Current Code**:
```python
self.update_window_title(f"{percentage}%, {current} of {total}")
```

**Updated Code**:
```python
# Check if paused
paused_prefix = ""
if self.batch_worker and self.batch_worker.is_paused():
    paused_prefix = "(Paused) "

self.update_window_title(f"{paused_prefix}{percentage}%, {current} of {total}")
```

---

## Build System Updates

**File Modified**: [imagedescriber/imagedescriber_wx.spec](../../imagedescriber/imagedescriber_wx.spec)

**Add to hiddenimports** (Line 49):
```python
hiddenimports=[
    # ... existing imports ...
    'imagedescriber.batch_progress_dialog',  # NEW: Progress dialog
    # ... rest of imports ...
]
```

---

## Testing Plan

### Unit Tests

**New File**: `pytest_tests/test_batch_processing.py`

```python
def test_image_item_processing_state_persistence():
    """Test that processing states save/load correctly"""
    item = ImageItem("/path/to/image.jpg")
    item.processing_state = "failed"
    item.processing_error = "Network timeout"
    item.batch_queue_position = 5
    
    # Serialize
    data = item.to_dict()
    
    # Deserialize
    restored = ImageItem.from_dict(data)
    
    assert restored.processing_state == "failed"
    assert restored.processing_error == "Network timeout"
    assert restored.batch_queue_position == 5

def test_workspace_batch_state_persistence():
    """Test that batch state saves/loads correctly"""
    ws = ImageWorkspace()
    ws.batch_state = {
        "provider": "claude",
        "model": "claude-opus-4-6",
        "paused_at_index": 10,
        "total_queued": 50
    }
    
    # Serialize
    data = ws.to_dict()
    
    # Deserialize
    restored = ImageWorkspace.from_dict(data)
    
    assert restored.batch_state["provider"] == "claude"
    assert restored.batch_state["paused_at_index"] == 10

def test_batch_worker_pause_resume():
    """Test pause/resume mechanism"""
    # Mock worker with pause/resume
    # Verify _pause_event.wait() blocks when paused
    # Verify _pause_event.set() unblocks
    pass

def test_resume_queue_ordering():
    """Test that resume processes items in correct order"""
    # Create workspace with 5 pending items with different queue positions
    # Call resume logic
    # Verify file_paths list sorted by batch_queue_position
    pass
```

### Manual Testing Scenarios

#### Scenario 1: Basic Pause/Resume
1. Load directory with 10 images
2. Process → Process Undescribed Images
3. Verify progress dialog shows
4. After 3 images processed, click Pause
5. Verify title shows "(Paused)"
6. Verify stats frozen in dialog
7. Click Resume
8. Verify processing continues from image 4
9. Verify batch completes successfully

#### Scenario 2: Pause + Save + Reopen
1. Start batch of 20 images
2. Pause after 5 processed
3. Save workspace (Ctrl+S)
4. Close ImageDescriber
5. Reopen workspace
6. Verify resume prompt appears with correct counts (5 of 20 completed)
7. Click Resume
8. Verify processing picks up from image 6
9. Verify all 20 images eventually completed

#### Scenario 3: Stop Mid-Batch
1. Start batch of 30 images
2. Stop after 10 processed
3. Verify 10 have descriptions
4. Verify 20 remain undescribed (no "pending" state)
5. Re-run "Process Undescribed Images"
6. Verify only 20 queued (skips first 10)

#### Scenario 4: Crash Recovery
1. Start batch of 15 images
2. After 7 processed, forcibly terminate app (Task Manager → End Task)
3. Reopen workspace
4. Verify resume prompt shows "7 of 15 completed"
5. Resume
6. Verify processing continues from image 8
7. Verify state transitions:
   - Items 1-7: processing_state="completed"
   - Items 8-15: processing_state="pending" → "processing" → "completed"

#### Scenario 5: Failed Items
1. Disconnect network
2. Start batch with cloud provider (OpenAI/Claude)
3. Verify first image fails
4. Verify error stored in item.processing_error
5. Verify processing continues to next image
6. Reconnect network
7. Verify subsequent images succeed
8. Check failed item shows "X" indicator in list

#### Scenario 6: Redescribe All Warning
1. Load directory with 5 described images
2. Process → Redescribe All Images
3. Verify warning dialog appears
4. Click Yes
5. Verify all 5 images reprocessed
6. Verify descriptions replaced

#### Scenario 7: Prevent Concurrent Batches
1. Start batch of 20 images
2. While batch is running (after 5 processed), click Process → Process Undescribed Images again
3. Verify warning dialog appears: "Batch processing already in progress"
4. Verify original batch continues uninterrupted
5. Pause the batch
6. Try to start new batch again → verify still blocked
7. Stop the batch
8. Try to start new batch → verify it works now

#### Scenario 8: Progress Dialog Modeless
1. Start batch of 50 images
2. Minimize progress dialog
3. Navigate workspace (select different images, edit descriptions)
4. Verify progress continues in background
5. Restore dialog
6. Verify stats accurate and up-to-date

#### Scenario 8: Large Batch Stats
1. Process 100+ images
2. Verify "Average Processing Time" updates correctly
3. Verify progress bar smooth (no stuttering)
4. Verify title bar updates don't impact performance

### Build Verification

1. **Windows Build**:
   ```batch
   cd imagedescriber
   build_imagedescriber_wx.bat
   ```

2. **Test Frozen Executable**:
   - Run batch with 50 images
   - Pause → verify works in frozen mode
   - Close app → reopen → resume → verify works
   - Check that batch_progress_dialog module included

3. **Check Spec File**:
   - Verify `'imagedescriber.batch_progress_dialog'` in hiddenimports
   - Build log should show module packaged

---

## User Documentation Updates

**Files to Update**:
1. [docs/USER_GUIDE.md](../../docs/USER_GUIDE.md) - Add "Batch Processing" section
2. [docs/WHATS_NEW_v4.2.0.md](../../docs/WHATS_NEW_v4.2.0.md) - New file for release notes

**Key Points to Document**:
- How to use Process Undescribed Images vs Redescribe All
- How to pause/resume batch processing
- What happens if app crashes during batch
- How to interpret processing state indicators (P, !, X, .)
- Progress dialog can be minimized while batch runs

---

## Success Criteria

✅ **Required Features**:
- [ ] Pause button → batch processing freezes after current image
- [ ] Resume button → batch processing continues from next image
- [ ] Stop button → batch ends, progress saved, no auto-resume
- [ ] Progress dialog shows "X of Y" and average time
- [ ] Dialog is modeless (can minimize, workspace usable)
- [ ] Crash recovery: reopen workspace → resume prompt appears
- [ ] Resume processes remaining items in correct order
- [ ] Processing states persist in .idw file
- [ ] "Process Undescribed Images" skips images with descriptions (default)
- [ ] "Redescribe All Images" shows warning before overwriting
- [ ] Title bar shows "(Paused)" when paused

✅ **Quality Checks**:
- [ ] No memory leaks from worker references
- [ ] No race conditions in pause/resume
- [ ] Progress dialog updates don't slow processing
- [ ] Frozen executable includes batch_progress_dialog module
- [ ] All states serialize/deserialize correctly
- [ ] Failed items tracked and indicated visually

---

## Timeline Estimate

| Phase | Tasks | Estimated Time | Dependencies |
|-------|-------|----------------|--------------|
| Phase 1 | Data model updates | 2-3 hours | None |
| Phase 2 | Worker pause/resume | 3-4 hours | Phase 1 |
| Phase 3 | Progress dialog UI | 4-5 hours | Phase 2 |
| Phase 4 | Resume functionality | 3-4 hours | Phase 1-3 |
| Phase 5 | Process All behavior | 1-2 hours | None (parallel) |
| Phase 6 | Visual indicators | 1-2 hours | Phase 1 |
| Testing | Manual + unit tests | 3-4 hours | All phases |
| **Total** | | **17-24 hours** | |

**Recommended Approach**: Implement phases 1-2 first (foundation), then 3-4 (user-facing), then 5-6 (polish).

---

## Future Enhancements (Out of Scope)

These ideas came up during planning but are deferred for future consideration:

1. **Retry Failed Items**: Button to reprocess only failed items
2. **Estimated Time Remaining**: Based on average time × remaining items
3. **More Stats**: Total tokens used, average words per description
4. **Batch Presets**: Save common provider/model/prompt combos
5. **Scheduling**: "Process new images every N hours"
6. **Notification**: Desktop notification when batch completes
7. **Parallel Processing**: Process N images simultaneously (requires major refactor)

---

## References

- **Worker Pattern**: [workers_wx.py#L1046-L1136](../../imagedescriber/workers_wx.py) - BatchProcessingWorker
- **threading.Event**: [workers_wx.py#L1358-L1420](../../imagedescriber/workers_wx.py) - HEICConversionWorker
- **Resume Logic**: [workflow.py#L2444-L2580](../../scripts/workflow.py) - parse_workflow_state()
- **Dialog Pattern**: [dialogs_wx.py](../../imagedescriber/dialogs_wx.py) - ProcessingOptionsDialog
- **Workspace Persistence**: [imagedescriber_wx.py#L1717-L1726](../../imagedescriber/imagedescriber_wx.py)
- **Data Models**: [data_models.py](../../imagedescriber/data_models.py)

---

**Last Updated**: February 9, 2026  
**Tracking Issue**: [GitHub Issue #73](https://github.com/kellylford/Image-Description-Toolkit/issues/73)
