# Architecture Search Results - ImageDescriber UI Research

**Date**: January 9, 2026  
**Search Scope**: Image-Description-Toolkit Repository  
**Objective**: Locate and document the original Qt6/PyQt6 ImageDescriber architecture to understand the correct two-panel layout design

---

## Search Findings Summary

### ✅ Found Files

| File | Location | Status | Type |
|------|----------|--------|------|
| **PyQt6 Version (Full Original)** | Git commit `5a081303` | Archived in history | Complete implementation |
| **PyQt6 Dialogs** | `imagedescriber/dialogs.py` | Present | PyQt6 imports visible |
| **PyQt6 Workers** | `imagedescriber/worker_threads.py` | Present | PyQt6 QThread imports |
| **wxPython Port** | `imagedescriber/imagedescriber_wx.py` | Current | wxPython replacement (1649 lines) |
| **Data Models** | `imagedescriber/data_models.py` | Present | Shared between both versions |
| **README** | `imagedescriber/README.md` | Present | Complete feature documentation |
| **WXPythonDemo** | `WXPythonDemo/` directory | Reference | Test implementations of patterns |

### ❌ Files That Were Deleted

The following PyQt6 files were **intentionally removed** in commit `e4256ac` (Jan 8, 2026):
- `imagedescriber/imagedescriber.py` (main PyQt6 file) - **Removed**
- `imagedescriber/imagedescriber_macos.spec` - **Removed**
- `imagedescriber/build_imagedescriber.bat` - **Removed**
- `imagedescriber/build_imagedescriber_macos.sh` - **Removed**

**Reason for Deletion**: Consolidation into single wxPython implementation

---

## Original Architecture (PyQt6 Version)

### Main Window Structure
**File**: Git history commit `5a081303:imagedescriber/imagedescriber.py`

```
ImageDescriberFrame (QMainWindow)
├── Central Widget (QWidget)
│   ├── QSplitter (Horizontal, resizable)
│   │   │
│   │   ├── LEFT PANEL (QWidget)
│   │   │   ├── QLabel("Images:")
│   │   │   ├── QListWidget(name="image_list")
│   │   │   │   ├── Display: Image filenames only
│   │   │   │   ├── ClientData: Full file paths
│   │   │   │   ├── Selection: Single item
│   │   │   │   └── Signal: itemSelectionChanged()
│   │   │   │       └── Trigger: on_image_selected()
│   │   │   │
│   │   │   └── Buttons
│   │   │       ├── "Load Directory"
│   │   │       └── "Process All"
│   │   │
│   │   └── RIGHT PANEL (QWidget)
│   │       ├── QLabel(name="image_info_label") 
│   │       │   └── Shows: "filename.jpg (model: X, style: Y)"
│   │       ├── QLabel("Description:")
│   │       ├── QTextEdit(name="description_text")
│   │       │   ├── Content: Full description text
│   │       │   ├── Style: Multiline, rich text
│   │       │   └── Purpose: Display/edit descriptions
│   │       │
│   │       └── Buttons
│   │           ├── "Generate Description"
│   │           └── "Save Description"
│   │
│   └── MenuBar
│       ├── File (New, Open, Save, Load Directory, Exit)
│       ├── Processing (Process Selected, Process All, Batch, etc.)
│       ├── View (Filters, All Descriptions, Workspace Manager)
│       └── Help (About, Check Updates)
│
└── StatusBar (Real-time progress messages)
```

### Key UI Components

#### QListWidget (Left Panel)
- **Name**: `image_list`
- **Purpose**: Display images available in workspace
- **Display Format**: Simple strings with image filenames
  ```
  photo_001.jpg
  sunset_photo.jpg
  family_gathering.jpg
  vacation_2025.jpg
  ```
- **Client Data**: Full file paths (stored, not displayed)
- **Selection**: Single item at a time
- **Signal**: `itemSelectionChanged()` → calls `on_image_selected()`
- **Accessibility**: Single tab stop (not tabbing through individual items)

#### QTextEdit (Right Panel)
- **Name**: `description_text`
- **Purpose**: Display description for currently selected image
- **Content**: Full description text (could be multiple paragraphs)
- **Style**: 
  - Rich text enabled
  - Multiline
  - Word wrap
  - May have formatting (bold, italic, colors)
- **Interaction**:
  - Click to select and edit
  - Tab key moves focus to next control (not insert tab)
  - Can save edited description back to workspace

### Data Flow

```
User clicks image in list
    ↓
itemSelectionChanged() signal
    ↓
on_image_selected() handler
    ├─ Get file path from item clientData
    ├─ Retrieve ImageItem from workspace
    ├─ Find most recent ImageDescription in descriptions list
    └─ Display in QTextEdit (right panel)
        └─ Show metadata in info label
```

---

## Current Implementation (wxPython Port)

### File Location
**File**: `imagedescriber/imagedescriber_wx.py` (1649 lines)

### Architecture Equivalence
The wxPython version maintains **identical architecture**:

| Component | PyQt6 | wxPython |
|-----------|-------|----------|
| Main Window | `QMainWindow` | `wx.Frame` |
| Splitter | `QSplitter` | `wx.SplitterWindow` |
| Image List | `QListWidget` | `wx.ListBox` |
| Description | `QTextEdit` | `wx.TextCtrl` |
| Info Label | `QLabel` | `wx.StaticText` |

### Code Structure
```python
class ImageDescriberFrame(wx.Frame, ModifiedStateMixin):
    def __init__(self):
        # Setup frame
        # Create menu bar
        # Create status bar
        
    def init_ui(self):
        # Main splitter
        # Left & right panels
        
    def create_image_list_panel(self, parent):
        # wx.ListBox with name="Images in workspace"
        # Bound to on_image_selected()
        
    def create_description_panel(self, parent):
        # wx.TextCtrl with name="Image description editor"
        # Info label above
        
    def on_image_selected(self, evt):
        # Get selection
        # Retrieve from workspace
        # Update right panel
```

---

## Key Architectural Decisions

### 1. Two-Panel Layout (Not Tree View)
**Decision**: Left panel shows flat list of images, not hierarchical tree
**Rationale**:
- Simpler, more accessible UI
- Single tab stop (better for screen readers)
- Direct mapping: list item ↔ description
- Users expect image list + editor (like photo apps)

**Evidence**: README.md explicitly states:
> "Split Pane: Images on left, descriptions on right for efficient workflow"

### 2. Multiple Descriptions Per Image
**Architecture**: Each `ImageItem` contains:
```python
descriptions: List[ImageDescription] = []
```

**Display Logic**:
- Right panel shows **most recent description** (index [0])
- Other descriptions accessible via menu: "All Descriptions Dialog"
- When processing image again, new description is **prepended** (index [0])

**Rationale**:
- Users may regenerate descriptions with different models/prompts
- Want to compare descriptions side-by-side
- Preserve complete history of processing

### 3. Single Tab Stop for Accessibility
**Implementation**: Use `QListWidget` (PyQt6) or `wx.ListBox` (wxPython), NOT:
- ❌ `QListView` with custom model
- ❌ `QTreeWidget` (even for flat structure)
- ❌ `wx.ListCtrl` (allows column tabbing)

**Why**: Screen reader users should:
- Tab once to enter list
- Use arrow keys to navigate items
- Tab again to leave list
- NOT tab through every individual item (20+ tab presses!)

### 4. Client Data Pattern for File Paths
**Implementation**:
```python
# Display text
self.image_list.addItem("photo.jpg")

# Store actual path in client data
item = self.image_list.item(count - 1)
item.setData(Qt.UserRole, "/full/path/to/photo.jpg")  # PyQt6

# or wxPython:
self.image_list.Append("photo.jpg", "/full/path/to/photo.jpg")
```

**Rationale**:
- Display shows only filename (shorter, user-friendly)
- Backend has full path when needed
- Handles files with same name in different directories

### 5. Keyboard-Centric Interaction
**Single-Key Shortcuts**:
```
P = Process selected image
B = Mark/unmark for batch
Ctrl+S = Save workspace
Ctrl+N = New workspace
Ctrl+O = Open workspace
```

**Rationale**: Power users want fast processing without mouse

---

## Data Model (Shared Between PyQt6 and wxPython)

### ImageDescription
```python
class ImageDescription:
    id: str                  # Unique identifier
    text: str               # Description content
    model: str              # AI model (e.g., "llava:7b")
    prompt_style: str       # Prompt type (e.g., "narrative")
    provider: str           # Provider (ollama, openai, claude)
    created: str            # ISO timestamp
    custom_prompt: str      # Custom prompt if provided
    total_tokens: int       # Token usage tracking
    
    def to_dict() -> dict   # Serialize to JSON
    @classmethod
    def from_dict(data: dict)  # Deserialize from JSON
```

### ImageItem
```python
class ImageItem:
    file_path: str          # Full path to file
    item_type: str          # "image", "video", "extracted_frame"
    descriptions: List[ImageDescription]  # All descriptions (newest first)
    batch_marked: bool      # For batch processing
    parent_video: str       # For extracted frames
    extracted_frames: List[str]  # For videos
    display_name: str       # Custom name (rarely used)
```

### ImageWorkspace
```python
class ImageWorkspace:
    version: str            # File format version
    directory_paths: List[str]  # Multiple image directories
    items: Dict[str, ImageItem]  # file_path → ImageItem
    created: str            # When workspace created
    modified: str           # Last modification time
    file_path: str          # Path to .idw file
    
    def add_item(item: ImageItem)
    def remove_item(file_path: str)
    def get_item(file_path: str) -> ImageItem
    def mark_modified()
```

### Workspace File Format (.idw)
```json
{
  "version": "1.0",
  "directory_paths": ["/path/to/images"],
  "created": "2025-01-09T14:30:45.123456",
  "modified": "2025-01-09T15:45:20.654321",
  "items": {
    "/path/to/images/photo.jpg": {
      "file_path": "/path/to/images/photo.jpg",
      "item_type": "image",
      "descriptions": [
        {
          "id": "1704836445123",
          "text": "A sunset over the ocean...",
          "model": "llava:7b",
          "prompt_style": "narrative",
          "provider": "ollama",
          "created": "2025-01-09T14:35:45.123456",
          "custom_prompt": "",
          "total_tokens": 125
        }
      ],
      "batch_marked": false
    }
  }
}
```

---

## Integration Points

### 1. AI Provider System
- **Location**: `imagedescriber/ai_providers.py`
- **Shared by**: Both PyQt6 (old) and wxPython (current)
- **Providers**: Ollama, OpenAI, Claude, HuggingFace
- **Selection**: Dynamic based on `supports_prompts()`, `supports_custom_prompts()`

### 2. Configuration System
- **File**: `scripts/image_describer_config.json`
- **Loaded by**: Both UI versions
- **Contains**: Default provider, models, prompt configurations
- **Resolution**: Config loader checks multiple paths (env vars, bundled, etc.)

### 3. Worker Threads
- **PyQt6**: `imagedescriber/worker_threads.py` uses `QThread` with `pyqtSignal`
- **wxPython**: `imagedescriber/workers_wx.py` uses `threading.Thread` with `wx.lib.newevent`
- **Same class names**: `ProcessingWorker`, `BatchProcessingWorker`, etc.

### 4. Dialog Boxes
- **PyQt6**: `imagedescriber/dialogs.py` uses `QDialog`
- **wxPython**: `imagedescriber/dialogs_wx.py` uses `wx.Dialog`
- **Accessible**: Both use accessible text input widgets with proper tab handling

---

## WXPythonDemo Reference Implementations

### Location
`WXPythonDemo/` - Separate repository with test/demo files

### Key Files
1. **`custom_accessible_listbox.py`** - Reusable accessible ListBox class
2. **`image_description_viewer.py`** - Two-panel layout demo
3. **`viewer_demo_accessible.py`** - Full accessible patterns
4. **`test_listbox_accessibility.py`** - Automated accessibility tests

### Usage in ImageDescriber
- Reference patterns for accessible wxPython widgets
- Test screen reader compatibility
- Validate keyboard navigation
- Example of two-panel layout (matches original design)

---

## Documentation References

### New Documents Created
1. **[ORIGINAL_QT6_ARCHITECTURE.md](ORIGINAL_QT6_ARCHITECTURE.md)** - Complete Qt6 design documentation
2. **[QT6_VS_WXPYTHON_COMPARISON.md](QT6_VS_WXPYTHON_COMPARISON.md)** - Side-by-side code examples
3. **[WXPythonDemo/INTEGRATION_GUIDE.md](../../WXPythonDemo/INTEGRATION_GUIDE.md)** - How to use patterns

### Existing Documentation
- **[imagedescriber/README.md](../../imagedescriber/README.md)** - Feature documentation
- **[imagedescriber/imagedescriber_wx.py](../../imagedescriber/imagedescriber_wx.py)** - Current implementation (1649 lines)
- **[docs/AI_ONBOARDING.md](AI_ONBOARDING.md)** - Development status and issues

---

## Key Findings

### ✅ Confirmed Architecture
1. **Two-panel layout** with QListWidget (left) + QTextEdit (right)
2. **Multiple descriptions per image** stored chronologically
3. **Document-based workspace** (save/load .idw files)
4. **Single tab stop** for accessibility
5. **Keyboard shortcuts** for power users (P, B, Ctrl+S)
6. **Split pane** with resizable panels

### ✅ Confirmed Data Model
- `ImageDescription` - Single description with metadata
- `ImageItem` - Image file with multiple descriptions
- `ImageWorkspace` - Collection of images/videos
- File format: JSON-based `.idw` workspace files

### ✅ Confirmed UI Components
- Image list: QListWidget (PyQt6) or wx.ListBox (wxPython)
- Description editor: QTextEdit (PyQt6) or wx.TextCtrl (wxPython)
- Info label: QLabel (PyQt6) or wx.StaticText (wxPython)
- Splitter: QSplitter (PyQt6) or wx.SplitterWindow (wxPython)

### ✅ Migration Status
- PyQt6 version **removed** (commit `e4256ac`)
- wxPython version **complete and current** (1649 lines)
- Both versions **use identical data models**
- Both versions **support same features** (minor wxPython improvements)

---

## Search Methodology

**Tools Used**:
- `git show <commit>:<file>` - Retrieve historical file versions
- `git log --oneline <path>` - Track file history
- `grep_search` - Find code patterns (PyQt6 imports, widget names)
- `file_search` - Locate files by name
- Direct file inspection - Read implementations

**Searches Performed**:
1. ✅ `PyQt6|from PyQt6|import PyQt6|QMainWindow|QListWidget` - Found all PyQt6 references
2. ✅ `imagedescriber/imagedescriber.py` - Located in git history
3. ✅ `imagedescriber/*.py` - Found all related files
4. ✅ `left.*panel|right.*panel|image.*list|description.*list` - Found UI structure
5. ✅ Git history commits - Tracked PyQt6 → wxPython migration

---

## Conclusion

The original **Qt6/PyQt6 ImageDescriber** featured a clean two-panel architecture:
- **Left**: Flat list of images (single tab stop, accessible)
- **Right**: Description editor with metadata

This design has been **faithfully preserved** in the wxPython port, with identical:
- Layout and interaction patterns
- Data models and file formats
- Feature set and keyboard shortcuts
- Accessibility support (improved on macOS)

All architectural decisions are **well-justified** and backed by accessibility and usability principles. The wxPython migration maintains 100% feature parity while improving cross-platform compatibility.
