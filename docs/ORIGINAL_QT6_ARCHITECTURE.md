# Original Qt6/PyQt6 ImageDescriber Architecture

**Status**: Reference Documentation - Qt6 Version Removed (Jan 8, 2026)  
**Original Version**: PyQt6-based GUI (now migrated to wxPython)  
**Location**: Git history `5a081303` (commit before PyQt6 removal at `e4256ac`)

## Overview

The original ImageDescriber was a **Qt6-based (PyQt6)** application with a **two-panel layout** architecture:
- **Left Panel**: QListWidget displaying image names (with image file as client data)
- **Right Panel**: QTextEdit showing descriptions for the selected image

Users could navigate both lists with arrow keys and manage multiple descriptions per image.

---

## Architecture: Two-Panel Layout

### Main Window Structure

```
ImageDescriberFrame (QMainWindow)
├── Central Widget
│   ├── QSplitter (Horizontal Split)
│   │   ├── LEFT PANEL (Image List)
│   │   │   ├── QLabel "Images in Workspace"
│   │   │   ├── QListWidget (image_list)
│   │   │   │   ├── Items = Image Display Names
│   │   │   │   └── ClientData = Full File Paths
│   │   │   └── Buttons: [Load Directory] [Process All]
│   │   │
│   │   └── RIGHT PANEL (Description Editor)
│   │       ├── QLabel (image_info_label) = Current image filename
│   │       ├── QLabel "Description:"
│   │       ├── QTextEdit (description_text) = Description content
│   │       └── Buttons: [Generate] [Save Description]
│   │
│   ├── Status Bar
│   └── Menu Bar (File, Processing, View, Help)
```

### Key Widget Characteristics

#### Left Panel - Image List
- **Widget Type**: `QListWidget` (single-column, single tab stop)
- **Name**: `image_list`
- **Item Display**: Image filename only (e.g., "photo_001.jpg")
- **Item Data**: Full file path stored as client data
- **Selection Mode**: Single selection (`QListWidget.SelectionMode.SingleSelection`)
- **Signals**:
  - `itemSelectionChanged()` → triggers display of descriptions in right panel
  - Arrow keys navigate list items
  - Space/Enter toggles batch marking (when batch feature active)

#### Right Panel - Description Editor
- **Primary Widget**: `QTextEdit` (multiline, rich text)
- **Name**: `description_text`
- **Purpose**: Display and edit descriptions for currently selected image
- **Content**: Full description text for the image
- **User Interaction**: 
  - Read-only initially
  - Editable when generated or manually entered
  - Tab key handled specially (moves focus to next control, not insert tab)

---

## Data Model Architecture

### ImageDescription Class
Represents a single description for an image:

```python
class ImageDescription:
    def __init__(self, 
                 text: str,                    # Description text
                 model: str = "",              # AI model used (e.g., "llava:7b")
                 prompt_style: str = "",       # Prompt category (e.g., "narrative")
                 created: str = "",            # ISO timestamp
                 custom_prompt: str = "",      # User-provided prompt (if any)
                 provider: str = "",           # Provider name (ollama, openai, claude)
                 total_tokens: int = None,     # Token usage tracking
                 prompt_tokens: int = None,
                 completion_tokens: int = None):
        self.id = f"{int(time.time() * 1000)}"  # Unique ID for this description
```

**Key Feature**: Multiple descriptions per image stored chronologically.

### ImageItem Class
Represents a single image or extracted video frame:

```python
class ImageItem:
    def __init__(self, file_path: str, item_type: str = "image"):
        self.file_path = file_path            # Full path to file
        self.item_type = item_type            # "image", "video", "extracted_frame"
        self.descriptions: List[ImageDescription] = []  # All descriptions
        self.batch_marked = False             # Batch processing flag
        self.parent_video = None              # For extracted frames
        self.extracted_frames: List[str] = [] # For videos
        self.display_name = ""                # Custom display name
    
    def add_description(self, description: ImageDescription)
    def remove_description(self, desc_id: str)
```

### ImageWorkspace Class
Document model for the entire workspace:

```python
class ImageWorkspace:
    def __init__(self):
        self.version = WORKSPACE_VERSION       # Version tracking
        self.directory_path = ""               # Single directory (legacy)
        self.directory_paths: List[str] = []   # Multiple directories support
        self.items: Dict[str, ImageItem] = {}  # All images/videos
        self.chat_sessions: Dict[str, dict] = {}  # Chat history
        self.created = datetime.now().isoformat()
        self.file_path = None                  # Path to .idw workspace file
```

---

## User Interaction Flow

### Image Selection and Description Display

1. **User clicks image in left panel**:
   ```python
   def on_image_selected(self, item):
       # Get file path from item client data
       file_path = self.image_list.itemFromIndex(index).data(Qt.UserRole)
       image_item = self.workspace.get_item(file_path)
       
       # Display image info
       self.image_info_label.setText(Path(file_path).name)
       
       # Display first (most recent) description
       if image_item.descriptions:
           first_desc = image_item.descriptions[0]
           self.description_text.setText(first_desc.text)
       else:
           self.description_text.setText("")
   ```

2. **Arrow Key Navigation**:
   - ↑/↓ keys navigate image list (automatic QListWidget behavior)
   - Each navigation triggers image selection event
   - Right panel automatically updates to show selected image's description

3. **Processing Single Image**:
   - Select image in left panel
   - Press **P** key or click "Generate Description"
   - Processing dialog opens with AI provider options
   - New description added to `image_item.descriptions[]`
   - Right panel updates automatically

### Multiple Descriptions Per Image

The right panel can display:
- **All descriptions** (accessible via list selector or tabs)
- **Most recent first** (default display)
- **With metadata**: model, prompt style, creation date, token usage

---

## Key Architecture Decisions

### 1. Single Tab Stop Accessibility
- **Why QListWidget instead of QListView**: Single tab stop means users don't tab-through every item
- **Screen readers**: Announce item count, current selection, can arrow through
- **Consistent with WCAG AA**: Proper focus management

### 2. Client Data Pattern for File Paths
```python
# Display text (shown to user)
self.image_list.addItem("photo_001.jpg")

# Store actual file path as client data
item = self.image_list.item(self.image_list.count() - 1)
item.setData(Qt.UserRole, "/full/path/to/photo_001.jpg")

# Retrieve on selection
index = self.image_list.currentRow()
item = self.image_list.item(index)
file_path = item.data(Qt.UserRole)
```

### 3. QTextEdit for Description Display
- Supports rich text formatting (future enhancement)
- Multiline for full descriptions
- Tab handling customized to allow focus navigation

### 4. Splitter for Resizable Panels
```python
splitter = QSplitter(Qt.Orientation.Horizontal)
splitter.addWidget(left_panel)    # Image list
splitter.addWidget(right_panel)   # Description editor
splitter.setCollapsible(0, False) # Don't allow collapse
splitter.setCollapsible(1, False)
splitter.setSizes([400, 600])     # Initial split point
```

---

## AI Provider Integration

### Processing Dialog
Opened when user initiates image processing:

```python
class ProcessingDialog(QDialog):
    """Dynamic dialog based on provider capabilities"""
    
    def __init__(self, parent=None):
        # Provider selection dropdown
        self.provider_combo = QComboBox()
        # Dynamically populated from get_all_providers()
        
        # Model selection (updates when provider changes)
        self.model_combo = QComboBox()
        
        # Prompt style (if provider supports custom prompts)
        self.prompt_combo = QComboBox()
        
        # Custom prompt option
        self.custom_checkbox = QCheckBox("Use custom prompt")
        self.custom_prompt = AccessibleTextEdit()
        
        # Provider-specific settings:
        # - YOLO: confidence threshold, max objects
        # - GroundingDINO: detection mode (auto/custom), presets
```

### Processing Workflow

```
User selects image → Press P or "Generate Description"
    ↓
ProcessingDialog opens with AI options
    ↓
User selects: Provider → Model → Prompt → OK
    ↓
ProcessingWorker thread spawns
    ↓
AI provider generates description
    ↓
ImageDescription object created with metadata
    ↓
Added to ImageItem.descriptions[] list
    ↓
Right panel updates with new description
    ↓
Window title shows modification indicator
```

---

## File Format: ImageDescriber Workspace (.idw)

```json
{
  "version": "1.0",
  "directory_path": "/path/to/images",
  "directory_paths": [
    "/path/to/images",
    "/another/path"
  ],
  "created": "2025-01-09T14:30:45.123456",
  "modified": "2025-01-09T15:45:20.654321",
  "items": {
    "/path/to/images/photo_001.jpg": {
      "file_path": "/path/to/images/photo_001.jpg",
      "item_type": "image",
      "descriptions": [
        {
          "id": "1704836445123",
          "text": "A sunset over the ocean with vibrant orange and pink hues...",
          "model": "llava:7b",
          "prompt_style": "narrative",
          "provider": "ollama",
          "created": "2025-01-09T14:35:45.123456",
          "custom_prompt": "",
          "total_tokens": 125,
          "prompt_tokens": 20,
          "completion_tokens": 105
        },
        {
          "id": "1704837120456",
          "text": "Sunset, ocean, orange, pink, clouds...",
          "model": "moondream",
          "prompt_style": "simple",
          "provider": "ollama",
          "created": "2025-01-09T14:52:00.456789",
          "custom_prompt": "",
          "total_tokens": 42,
          "prompt_tokens": 12,
          "completion_tokens": 30
        }
      ],
      "batch_marked": false,
      "extracted_frames": [],
      "display_name": ""
    }
  }
}
```

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| **P** | Process selected image |
| **B** | Mark/unmark for batch processing |
| **Ctrl+N** | New workspace |
| **Ctrl+O** | Open workspace |
| **Ctrl+S** | Save workspace |
| **↑/↓** | Navigate image list |
| **Tab** | Move focus to next control |
| **Shift+Tab** | Move focus to previous control |
| **Del** | Delete selected description |
| **F1** | Help/About |

---

## Menu Structure

### File Menu
- New Workspace (Ctrl+N)
- Open Workspace (Ctrl+O)
- Save Workspace (Ctrl+S)
- Save As...
- Load Image Directory...
- Recent Workspaces
- ---
- Exit (Ctrl+Q)

### Processing Menu
- Process Selected (P)
- Process All
- Process Batch
- Mark for Batch (B)
- Clear Batch Marks
- Skip Model Verification
- ---
- Stop Processing

### View Menu
- Descriptions Only
- Images First (default)
- All Descriptions Dialog
- Workspace Directory Manager
- Filter: All / Described Only / Batch-Marked Only
- Refresh (F5)

### Help Menu
- About ImageDescriber
- Check for Updates
- Report Issue

---

## Migration Notes (wxPython Port)

The wxPython version (`imagedescriber_wx.py`) maintains the same **two-panel architecture**:

- **Left Panel**: `wx.ListBox` (replaces QListWidget)
- **Right Panel**: `wx.TextCtrl` (replaces QTextEdit)
- **Splitter**: `wx.SplitterWindow` (replaces QSplitter)
- **Data Model**: Identical (ImageDescription, ImageItem, ImageWorkspace)
- **Workflow**: Identical single-key shortcuts and navigation

Key improvements in wxPython version:
- ✅ Better macOS VoiceOver accessibility
- ✅ Native Windows/macOS look and feel
- ✅ Reduced bundle size
- ✅ Better wxPython threading support

---

## References

- **PyQt6 Original Commit**: `5a081303` (full implementation)
- **Deletion Commit**: `e4256ac` (removed PyQt6 files)
- **Current wxPython Version**: [imagedescriber_wx.py](../../imagedescriber/imagedescriber_wx.py)
- **Data Models**: [data_models.py](../../imagedescriber/data_models.py)
- **AI Providers**: [ai_providers.py](../../imagedescriber/ai_providers.py)
- **Worker Threads**: [workers_wx.py](../../imagedescriber/workers_wx.py)

---

## Summary

The original ImageDescriber Qt6 architecture was built around:

1. **Two-panel layout** with left image list and right description editor
2. **Multiple descriptions per image** with full metadata tracking
3. **Document-based workspace** model (save/load .idw files)
4. **Dynamic AI provider integration** with runtime capabilities detection
5. **Accessibility-first design** with single tab stops and screen reader support
6. **Keyboard-centric interaction** with single-key shortcuts for power users

All of these architectural principles **remain intact in the wxPython migration**, ensuring consistency and compatibility while providing better cross-platform support.
