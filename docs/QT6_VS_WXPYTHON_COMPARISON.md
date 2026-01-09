# Qt6 vs wxPython: Two-Panel Architecture Comparison

Quick reference showing how the same two-panel image list + description layout is implemented in **PyQt6** (original) vs **wxPython** (current migration).

---

## Panel Layout Structure

### PyQt6 (Original)
```python
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QTextEdit, QSplitter, QLabel
)
from PyQt6.QtCore import Qt

class ImageDescriberFrame(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Main widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        
        # Horizontal splitter for two panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # LEFT PANEL
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        label = QLabel("Images:")
        left_layout.addWidget(label)
        
        self.image_list = QListWidget()
        self.image_list.itemSelectionChanged.connect(self.on_image_selected)
        left_layout.addWidget(self.image_list)
        
        # RIGHT PANEL
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        self.image_info_label = QLabel("No image selected")
        right_layout.addWidget(self.image_info_label)
        
        desc_label = QLabel("Description:")
        right_layout.addWidget(desc_label)
        
        self.description_text = QTextEdit()
        right_layout.addWidget(self.description_text)
        
        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        splitter.setSizes([400, 600])  # Initial split point
        
        main_layout.addWidget(splitter)
```

### wxPython (Current)
```python
import wx

class ImageDescriberFrame(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(
            self,
            None,
            title="ImageDescriber - AI-Powered Image Description",
            size=(1400, 900)
        )
        
        # Main panel
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Splitter for resizable panels
        splitter = wx.SplitterWindow(panel, style=wx.SP_LIVE_UPDATE)
        
        # Create panels
        left_panel = self.create_image_list_panel(splitter)
        right_panel = self.create_description_panel(splitter)
        
        # Setup splitter
        splitter.SplitVertically(left_panel, right_panel, 400)
        splitter.SetMinimumPaneSize(200)
        
        main_sizer.Add(splitter, 1, wx.EXPAND | wx.ALL, 5)
        panel.SetSizer(main_sizer)
    
    def create_image_list_panel(self, parent):
        panel = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        label = wx.StaticText(panel, label="Images:")
        sizer.Add(label, 0, wx.ALL, 5)
        
        self.image_list = wx.ListBox(
            panel,
            name="Images in workspace",
            style=wx.LB_SINGLE | wx.LB_NEEDED_SB
        )
        self.image_list.Bind(wx.EVT_LISTBOX, self.on_image_selected)
        sizer.Add(self.image_list, 1, wx.EXPAND | wx.ALL, 5)
        
        panel.SetSizer(sizer)
        return panel
    
    def create_description_panel(self, parent):
        panel = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        self.image_info_label = wx.StaticText(
            panel,
            label="No image selected"
        )
        sizer.Add(self.image_info_label, 0, wx.ALL, 5)
        
        label = wx.StaticText(panel, label="Description:")
        sizer.Add(label, 0, wx.ALL, 5)
        
        self.description_text = wx.TextCtrl(
            panel,
            name="Image description editor",
            style=wx.TE_MULTILINE | wx.TE_WORDWRAP | wx.TE_RICH2
        )
        sizer.Add(self.description_text, 1, wx.EXPAND | wx.ALL, 5)
        
        panel.SetSizer(sizer)
        return panel
```

---

## Image List Population

### PyQt6
```python
def refresh_image_list(self):
    """Refresh the image list display"""
    self.image_list.clear()
    
    for file_path in sorted(self.workspace.items.keys()):
        item = self.workspace.items[file_path]
        
        # Create display name
        display_name = Path(file_path).name
        
        # Add item with client data (file path)
        list_item = QListWidgetItem(display_name)
        list_item.setData(Qt.ItemDataRole.UserRole, file_path)  # Store path
        
        self.image_list.addItem(list_item)
```

### wxPython
```python
def refresh_image_list(self):
    """Refresh the image list display"""
    self.image_list.Clear()
    
    for file_path in sorted(self.workspace.items.keys()):
        item = self.workspace.items[file_path]
        
        # Create display name
        display_name = Path(file_path).name
        
        # Add item with client data (file path)
        # In wxPython: Append(string, client_data)
        self.image_list.Append(display_name, file_path)
```

---

## Image Selection and Description Display

### PyQt6
```python
def on_image_selected(self):
    """Handle image selection change"""
    current_item = self.image_list.currentItem()
    
    if current_item:
        # Get file path from client data
        file_path = current_item.data(Qt.ItemDataRole.UserRole)
        image_item = self.workspace.get_item(file_path)
        
        # Update info label
        self.image_info_label.setText(Path(file_path).name)
        
        # Display description
        if image_item.descriptions:
            description = image_item.descriptions[0]  # Most recent
            self.description_text.setText(description.text)
            
            # Add metadata as prefix (optional)
            if description.model:
                info = f"Model: {description.model} | "
                info += f"Style: {description.prompt_style}"
                self.image_info_label.setText(
                    f"{Path(file_path).name} ({info})"
                )
        else:
            self.description_text.setText("")
    else:
        self.image_info_label.setText("No image selected")
        self.description_text.setText("")
```

### wxPython
```python
def on_image_selected(self, evt):
    """Handle image selection change"""
    selection = self.image_list.GetSelection()
    
    if selection != wx.NOT_FOUND:
        # Get file path from client data
        file_path = self.image_list.GetClientData(selection)
        image_item = self.workspace.get_item(file_path)
        
        # Update info label
        self.image_info_label.SetLabel(Path(file_path).name)
        
        # Display description
        if image_item.descriptions:
            description = image_item.descriptions[0]  # Most recent
            self.description_text.SetValue(description.text)
            
            # Add metadata as prefix (optional)
            if description.model:
                info = f"Model: {description.model} | "
                info += f"Style: {description.prompt_style}"
                self.image_info_label.SetLabel(
                    f"{Path(file_path).name} ({info})"
                )
        else:
            self.description_text.SetValue("")
    else:
        self.image_info_label.SetLabel("No image selected")
        self.description_text.SetValue("")
```

---

## Keyboard Navigation

### PyQt6 (Automatic)
```python
# Arrow keys automatically handled by QListWidget
# No code needed - just bind to itemSelectionChanged signal
self.image_list.itemSelectionChanged.connect(self.on_image_selected)

# Tab key behavior is automatic
# - Tab enters list
# - Arrow up/down navigate items
# - Tab/Shift-Tab move to next/prev control
```

### wxPython (Automatic)
```python
# Arrow keys automatically handled by wx.ListBox
# No code needed - just bind to EVT_LISTBOX
self.image_list.Bind(wx.EVT_LISTBOX, self.on_image_selected)

# Tab key behavior is automatic
# - Tab enters list
# - Arrow up/down navigate items
# - Tab/Shift-Tab move to next/prev control
```

---

## Single-Key Shortcuts (P for Process)

### PyQt6
```python
def keyPressEvent(self, event):
    """Handle single-key shortcuts"""
    if event.key() == Qt.Key.Key_P:
        # Process selected image
        self.on_process_single()
        event.accept()
    elif event.key() == Qt.Key.Key_B:
        # Mark for batch
        self.on_batch_mark()
        event.accept()
    else:
        super().keyPressEvent(event)
```

### wxPython
```python
def on_key_press(self, evt):
    """Handle single-key shortcuts"""
    key_code = evt.GetKeyCode()
    
    if key_code == ord('P'):
        self.on_process_single()
        evt.Skip(False)  # Don't propagate
    elif key_code == ord('B'):
        self.on_batch_mark()
        evt.Skip(False)
    else:
        evt.Skip()  # Propagate to default handler
```

---

## Processing Workflow

### PyQt6
```python
def on_process_single(self):
    """Process selected image"""
    current_item = self.image_list.currentItem()
    if not current_item:
        QMessageBox.warning(self, "Error", "No image selected")
        return
    
    file_path = current_item.data(Qt.ItemDataRole.UserRole)
    
    # Open processing dialog
    dialog = ProcessingDialog(self)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        # Create worker thread
        worker = ProcessingWorker(
            file_path,
            dialog.provider_combo.currentText(),
            dialog.model_combo.currentText(),
            dialog.prompt_combo.currentText()
        )
        worker.processing_complete.connect(self.on_processing_complete)
        worker.start()
        
        # Show progress
        self.status_label.setText(f"Processing: {Path(file_path).name}...")
```

### wxPython
```python
def on_process_single(self, evt=None):
    """Process selected image"""
    selection = self.image_list.GetSelection()
    if selection == wx.NOT_FOUND:
        show_warning(self, "Error", "No image selected")
        return
    
    file_path = self.image_list.GetClientData(selection)
    
    # Open processing dialog
    dialog = ProcessingOptionsDialog(self)
    if dialog.ShowModal() == wx.ID_OK:
        # Create worker thread
        worker = ProcessingWorker(
            file_path,
            dialog.get_provider(),
            dialog.get_model(),
            dialog.get_prompt_style()
        )
        self.Bind(EVT_PROCESSING_COMPLETE, self.on_processing_complete)
        worker.start()
        
        # Show progress
        self.SetStatusText(f"Processing: {Path(file_path).name}...")
```

---

## Data Model Integration

Both versions use identical data models (no conversion needed):

### ImageDescription (Same in both)
```python
class ImageDescription:
    def __init__(self, text: str, model: str = "", 
                 prompt_style: str = "", created: str = "",
                 custom_prompt: str = "", provider: str = "",
                 total_tokens: int = None):
        self.text = text
        self.model = model
        self.prompt_style = prompt_style
        self.created = created or datetime.now().isoformat()
        self.custom_prompt = custom_prompt
        self.provider = provider
        self.total_tokens = total_tokens
        self.id = f"{int(time.time() * 1000)}"  # Unique ID
```

### ImageItem (Same in both)
```python
class ImageItem:
    def __init__(self, file_path: str, item_type: str = "image"):
        self.file_path = file_path
        self.item_type = item_type  # "image", "video", "extracted_frame"
        self.descriptions: List[ImageDescription] = []
        self.batch_marked = False
```

### ImageWorkspace (Same in both)
```python
class ImageWorkspace:
    def __init__(self, new_workspace=False):
        self.version = WORKSPACE_VERSION
        self.directory_paths: List[str] = []
        self.items: Dict[str, ImageItem] = {}  # file_path → ImageItem
        self.created = datetime.now().isoformat()
```

---

## Threading and Event Handling

### PyQt6
```python
from PyQt6.QtCore import QThread, pyqtSignal

class ProcessingWorker(QThread):
    progress_updated = pyqtSignal(str, str)  # file_path, message
    processing_complete = pyqtSignal(str, str)  # file_path, description
    
    def run(self):
        try:
            description, tokens = self.process_with_ai()
            self.processing_complete.emit(self.file_path, description)
        except Exception as e:
            self.processing_failed.emit(self.file_path, str(e))
```

### wxPython
```python
import threading
import wx.lib.newevent

ProcessingCompleteEvent, EVT_PROCESSING_COMPLETE = wx.lib.newevent.NewEvent()

class ProcessingWorker(threading.Thread):
    def __init__(self, parent, file_path: str):
        super().__init__()
        self.parent = parent
        self.file_path = file_path
        self.daemon = True
    
    def run(self):
        try:
            description, tokens = self.process_with_ai()
            
            # Post event to main thread
            event = ProcessingCompleteEvent(
                file_path=self.file_path,
                description=description
            )
            wx.PostEvent(self.parent, event)
        except Exception as e:
            # Handle error
            pass
```

---

## Accessibility Features

### PyQt6 - Single Tab Stop
```python
# QListWidget automatically provides single tab stop
self.image_list = QListWidget()
# Tab key enters list, arrows navigate, Tab exits

# Custom accessible components
class AccessibleTreeWidget(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAccessibilityMode(True)
```

### wxPython - Single Tab Stop
```python
# wx.ListBox automatically provides single tab stop
self.image_list = wx.ListBox(
    panel,
    name="Images in workspace",  # Screen reader label
    style=wx.LB_SINGLE | wx.LB_NEEDED_SB
)
# Tab key enters list, arrows navigate, Tab exits
```

---

## Key Differences Summary

| Feature | PyQt6 | wxPython |
|---------|-------|----------|
| **Main Window Class** | `QMainWindow` | `wx.Frame` |
| **Image List Widget** | `QListWidget` | `wx.ListBox` |
| **Description Editor** | `QTextEdit` | `wx.TextCtrl` |
| **Splitter** | `QSplitter` | `wx.SplitterWindow` |
| **Threading** | `QThread` with `pyqtSignal` | `threading.Thread` with `wx.lib.newevent` |
| **Dialog** | `QDialog.exec()` | `ShowModal()` / `ShowModalAsync()` |
| **String Append with Data** | `QListWidgetItem` + `setData()` | `Append(string, client_data)` |
| **Get Selected Item** | `currentItem()` | `GetSelection()` |
| **Get Item Data** | `itemData(role)` | `GetClientData(index)` |
| **Set Label Text** | `setText()` | `SetLabel()` |
| **Set TextCtrl Text** | `setText()` | `SetValue()` |
| **Tab Key Handling** | Automatic | Automatic (special case: EVT_CHAR_HOOK for Ctrl+Tab) |

---

## Migration Checklist

When migrating from PyQt6 to wxPython:

- [ ] Replace `QMainWindow` with `wx.Frame`
- [ ] Replace `QListWidget` with `wx.ListBox`
- [ ] Replace `QTextEdit` with `wx.TextCtrl`
- [ ] Replace `QSplitter` with `wx.SplitterWindow`
- [ ] Update threading model (QThread → threading.Thread)
- [ ] Update signals (pyqtSignal → wx.lib.newevent.NewEvent)
- [ ] Update widget method names (setText → SetValue)
- [ ] Update dialog handling (exec → ShowModal)
- [ ] Verify tab order and focus behavior
- [ ] Test screen reader support (Narrator/VoiceOver)
- [ ] Test keyboard shortcuts (P, B, Ctrl+S, etc.)

---

## See Also

- [Original Qt6 Architecture Documentation](../docs/ORIGINAL_QT6_ARCHITECTURE.md)
- [ImageDescriber wxPython Implementation](../imagedescriber/imagedescriber_wx.py)
- [WXPythonDemo Integration Guide](../WXPythonDemo/INTEGRATION_GUIDE.md)
- [PyQt6 Documentation](https://www.riverbankcomputing.com/static/Docs/PyQt6/)
- [wxPython Documentation](https://docs.wxpython.org/)
