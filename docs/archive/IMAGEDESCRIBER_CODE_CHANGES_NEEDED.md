# ImageDescriber wxPython - Specific Code Changes Needed

**Quick Reference**: Exact code locations and implementations needed  
**Based on**: Comprehensive Qt6 vs wxPython audit

---

## 🎯 TOP 3 QUICK WINS (5-7 Hours Total)

---

## #1 Add Custom Prompt Field to ProcessingOptionsDialog

**File**: `imagedescriber/dialogs_wx.py`  
**Function**: `ProcessingOptionsDialog.__init__()` or setup method  
**Impact**: CRITICAL - Users can't customize prompts without this

### Current Issue
```python
# Users can only select from pre-defined prompts in config
# No way to enter a custom prompt
```

### Required Change
Add this to the "AI Model" settings section of ProcessingOptionsDialog:

```python
# In the AI Model settings panel setup, add after prompt_style_choice:

custom_prompt_label = wx.StaticText(settings_panel, label="Custom Prompt (optional):")
settings_sizer.Add(custom_prompt_label, 0, wx.ALL, 5)

self.custom_prompt_input = wx.TextCtrl(
    settings_panel,
    value="",
    style=wx.TE_MULTILINE | wx.TE_WORDWRAP,
    name="Custom prompt override"
)
self.custom_prompt_input.SetMinSize((300, 60))
settings_sizer.Add(self.custom_prompt_input, 0, wx.EXPAND | wx.ALL, 5)

# Add help text
help_text = wx.StaticText(
    settings_panel,
    label="Leave blank to use selected prompt style, or enter a custom prompt here"
)
help_text.SetFont(help_text.GetFont().MakeItalic())
settings_sizer.Add(help_text, 0, wx.ALL, 5)
```

### Data Retrieval
```python
# In get_options() or similar method, return custom prompt:
def get_options(self):
    options = {
        'model': self.model_choice.GetStringSelection(),
        'temperature': float(self.temperature_spin.GetValue()),
        'max_tokens': int(self.tokens_spin.GetValue()),
        'custom_prompt': self.custom_prompt_input.GetValue(),  # ← ADD THIS
        # ... other options
    }
    return options
```

### Usage in Worker
```python
# In worker_threads.py or process handler:
custom_prompt = options.get('custom_prompt', '')
if custom_prompt:
    prompt = custom_prompt  # Use custom
else:
    prompt = default_prompt_from_config  # Use configured
```

---

## #2 Implement Edit Menu

**File**: `imagedescriber/imagedescriber_wx.py`  
**Function**: `create_menu_bar()`  
**Impact**: ESSENTIAL - Standard user expectation for any text editor

### Current Issue
```python
# Edit menu exists but is empty
# Users expect Cut, Copy, Paste, Select All
```

### Required Change

Find `create_menu_bar()` method and add this after creating File menu:

```python
# Create Edit Menu
edit_menu = wx.Menu()

cut_item = edit_menu.Append(wx.ID_CUT, "&Cut\tCtrl+X")
self.Bind(wx.EVT_MENU, self.on_cut, cut_item)

copy_item = edit_menu.Append(wx.ID_COPY, "&Copy\tCtrl+C")
self.Bind(wx.EVT_MENU, self.on_copy, copy_item)

paste_item = edit_menu.Append(wx.ID_PASTE, "&Paste\tCtrl+V")
self.Bind(wx.EVT_MENU, self.on_paste, paste_item)

edit_menu.AppendSeparator()

select_all_item = edit_menu.Append(wx.ID_SELECTALL, "Select &All\tCtrl+A")
self.Bind(wx.EVT_MENU, self.on_select_all, select_all_item)

menubar.Append(edit_menu, "&Edit")
```

### Event Handlers
Add these methods to ImageDescriberFrame class:

```python
def on_cut(self, event):
    """Handle cut from Edit menu"""
    control = self.FindFocus()
    if control and hasattr(control, 'Cut'):
        try:
            control.Cut()
        except Exception:
            pass

def on_copy(self, event):
    """Handle copy from Edit menu"""
    control = self.FindFocus()
    if control and hasattr(control, 'Copy'):
        try:
            control.Copy()
        except Exception:
            pass

def on_paste(self, event):
    """Handle paste from Edit menu"""
    control = self.FindFocus()
    if control and hasattr(control, 'Paste'):
        try:
            control.Paste()
        except Exception:
            pass

def on_select_all(self, event):
    """Handle select all from Edit menu"""
    control = self.FindFocus()
    if control and hasattr(control, 'SelectAll'):
        try:
            control.SelectAll()
        except Exception:
            pass
```

**Testing**: 
- [ ] Click in description editor
- [ ] Edit → Cut, Copy, Paste, Select All all work
- [ ] Ctrl+X, Ctrl+C, Ctrl+V, Ctrl+A keyboard shortcuts work
- [ ] Works in description_text field
- [ ] Works in dialog text fields

---

## #3 Add Image Preview Panel

**File**: `imagedescriber/imagedescriber_wx.py`  
**Function**: `create_description_panel()`  
**Impact**: HIGH - Users need to see what they're describing

### Current Issue
```python
# Right panel only shows descriptions and editor
# No way to see the actual image being described
```

### Required Change

Modify `create_description_panel()` to add preview before descriptions list:

```python
def create_description_panel(self, parent):
    """Create the right panel with image preview, descriptions, and editor"""
    panel = wx.Panel(parent)
    sizer = wx.BoxSizer(wx.VERTICAL)
    
    # Image info label
    self.image_info_label = wx.StaticText(panel, label="No image selected")
    sizer.Add(self.image_info_label, 0, wx.ALL, 5)
    
    # ===== NEW: IMAGE PREVIEW SECTION =====
    preview_label = wx.StaticText(panel, label="Image Preview:")
    sizer.Add(preview_label, 0, wx.ALL, 5)
    
    # Preview panel with fixed size
    self.image_preview_panel = wx.Panel(panel, size=(250, 250))
    self.image_preview_panel.SetBackgroundColour(wx.Colour(200, 200, 200))
    self.image_preview_panel.SetName("Image preview panel")
    
    # Bind paint event for displaying image
    self.image_preview_bitmap = None
    self.image_preview_panel.Bind(wx.EVT_PAINT, self.on_paint_preview)
    
    sizer.Add(self.image_preview_panel, 0, wx.ALL | wx.EXPAND, 5)
    
    # ===== DESCRIPTIONS LIST (EXISTING) =====
    desc_list_label = wx.StaticText(panel, label="Descriptions for this image:")
    sizer.Add(desc_list_label, 0, wx.ALL, 5)
    
    self.desc_list = DescriptionListBox(
        panel, 
        name="Description list for current image",
        style=wx.LB_SINGLE | wx.LB_NEEDED_SB
    )
    self.desc_list.Bind(wx.EVT_LISTBOX, self.on_description_selected)
    sizer.Add(self.desc_list, 1, wx.EXPAND | wx.ALL, 5)
    
    # ===== EDITOR (EXISTING) =====
    editor_label = wx.StaticText(panel, label="Edit selected description:")
    sizer.Add(editor_label, 0, wx.ALL, 5)
    
    self.description_text = wx.TextCtrl(
        panel,
        name="Image description editor",
        style=wx.TE_MULTILINE | wx.TE_WORDWRAP | wx.TE_RICH2
    )
    sizer.Add(self.description_text, 1, wx.EXPAND | wx.ALL, 5)
    
    # Buttons (existing)
    button_sizer = wx.BoxSizer(wx.HORIZONTAL)
    # ... rest of buttons unchanged
    
    panel.SetSizer(sizer)
    return panel
```

### Add Paint Handler and Preview Loading

```python
def on_paint_preview(self, event):
    """Paint the preview image"""
    dc = wx.PaintDC(self.image_preview_panel)
    if self.image_preview_bitmap:
        dc.DrawBitmap(self.image_preview_bitmap, 0, 0)

def load_preview_image(self, file_path):
    """Load and display image preview"""
    try:
        from PIL import Image
        
        # Load and resize image
        img = Image.open(file_path)
        img.thumbnail((250, 250), Image.Resampling.LANCZOS)
        
        # Convert PIL image to wx.Bitmap
        width, height = img.size
        wx_image = wx.Image(width, height)
        
        # Convert to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        rgb_data = img.tobytes()
        wx_image.SetData(rgb_data)
        
        self.image_preview_bitmap = wx.Bitmap(wx_image)
        
        # Refresh panel
        self.image_preview_panel.SetBackgroundColour(wx.Colour(255, 255, 255))
        self.image_preview_panel.Refresh()
        
    except Exception as e:
        # If image can't be loaded, show placeholder
        self.image_preview_bitmap = None
        self.image_preview_panel.SetBackgroundColour(wx.Colour(200, 200, 200))
        self.image_preview_panel.Refresh()
        print(f"Could not load preview: {e}")

def on_image_selected(self, event):
    """Handle image selection - update preview and descriptions"""
    selection = self.image_list.GetSelection()
    if selection != wx.NOT_FOUND:
        file_path = self.image_list.GetClientData(selection)
        if file_path and file_path in self.workspace.items:
            self.current_image_item = self.workspace.items[file_path]
            
            # Load preview image ← ADD THIS
            self.load_preview_image(file_path)
            
            self.display_image_info(self.current_image_item)
            self.process_btn.Enable(True)
            self.save_desc_btn.Enable(True)
    else:
        self.current_image_item = None
        self.image_preview_bitmap = None
        self.image_preview_panel.SetBackgroundColour(wx.Colour(200, 200, 200))
        self.image_preview_panel.Refresh()
        self.process_btn.Enable(False)
        self.save_desc_btn.Enable(False)
```

### Dependency
Add to requirements or imports:
```python
from PIL import Image  # For image thumbnail generation
```

**Testing**:
- [ ] Load directory with images
- [ ] Click on image in list
- [ ] Preview displays thumbnail of selected image
- [ ] Preview updates when different image selected
- [ ] Preview is readable/clear
- [ ] Works with JPEG, PNG, and other formats
- [ ] Graceful error handling for corrupted images

---

## Verification After Changes

### Syntax Check
```bash
cd imagedescriber
python -m py_compile imagedescriber_wx.py dialogs_wx.py
```

### Basic Functional Test
1. Load directory with images
2. Click image → preview should display, descriptions should populate
3. Type in custom prompt field → save dialog, verify it's saved
4. Edit → Cut, Copy, Paste, Select All → all should work
5. Edit description and use Ctrl+X, Ctrl+C, Ctrl+V → should work

### Full Test Coverage
See [2026-01-09-imagedescriber-comprehensive-audit.md](2026-01-09-imagedescriber-comprehensive-audit.md) for complete 50+ item test checklist.

---

## After Tier 1: Next Steps

Once these three are working:

### Tier 2 (High Priority)
1. **Auto-Rename**: Fix the Z key handler to actually rename files
2. **Chat**: Add conversation history and multi-turn support  
3. **Video Config**: Create VideoExtractionDialog with options

### Tier 3 (Medium Priority)
4. **Toolbar**: Add wx.ToolBar with common actions
5. **Search**: Implement description search feature
6. **Export**: Add CSV/JSON export capability

---

## Quick Reference: File Locations

| Feature | File | Location |
|---------|------|----------|
| Custom Prompt | `imagedescriber/dialogs_wx.py` | ProcessingOptionsDialog class |
| Edit Menu | `imagedescriber/imagedescriber_wx.py` | create_menu_bar() method |
| Image Preview | `imagedescriber/imagedescriber_wx.py` | create_description_panel() method |
| Auto-Rename Fix | `imagedescriber/imagedescriber_wx.py` | on_auto_rename() method |
| Chat Multi-turn | `imagedescriber/dialogs_wx.py` | ChatDialog class |
| Video Config | `imagedescriber/dialogs_wx.py` | New VideoExtractionDialog class |

---

**Note**: All code changes preserve accessibility, maintain keyboard navigation, and follow wxPython best practices from the rest of the codebase.

