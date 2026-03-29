# Accessible ListBox Pattern - Integration Guide

**Location**: `shared/wx_common.py` (lines ~760+)  
**Classes**: `AccessibleDescriptionListBox`, `DescriptionListBox`  
**Status**: Production-ready, used in Viewer and ImageDescriber

## Purpose

The `DescriptionListBox` class solves a critical accessibility problem:

**Problem**: wxPython's `wx.ListBox` doesn't support different text for screen readers vs. visual display. When displaying long descriptions (100-500+ characters), the list becomes cluttered and truncation loses accessibility.

**Solution**: Custom `wx.Accessible` subclass that overrides screen reader queries to return full text while the visual ListBox shows truncated versions.

## Quick Start

### 1. Create the ListBox
```python
from shared.wx_common import DescriptionListBox

# Create accessible description listbox
desc_list = DescriptionListBox(
    parent_panel,
    name="Descriptions",
    style=wx.LB_SINGLE | wx.LB_NEEDED_SB
)
```

### 2. Load Descriptions
```python
# Prepare data: list of dicts with 'description' key
descriptions = [
    {
        'description': 'Full 200+ character description text...',
        'model': 'gpt-4',
        'prompt_style': 'detailed',
        'created': '2025-01-09T10:30:00'
    },
    {
        'description': 'Another full description...',
        'model': 'claude',
        'prompt_style': 'concise',
        'created': '2025-01-09T10:35:00'
    }
]

# Load into listbox (applies accessibility + truncation)
desc_list.LoadDescriptions(descriptions, truncate_at=100)
```

### 3. Handle Selection
```python
# Bind selection event
desc_list.Bind(wx.EVT_LISTBOX, self.on_description_selected)

def on_description_selected(self, event):
    idx = desc_list.GetSelection()
    if idx != wx.NOT_FOUND:
        # Get full description dict
        full_entry = desc_list.GetFullDescription(idx)
        description_text = full_entry.get('description', '')
        # Do something with the full description
```

## How It Works

### Visual Display (User Sees)
```
Description List:
  • Long description that gets truncated at 100 characters to sav...
  • Another description that's also truncated for cleaner UI disp...
```

### Accessibility (Screen Reader Announces)
- **Item 1**: "Long description that gets truncated at 100 characters to save space while users can still see the beginning" (full text)
- **Item 2**: "Another description that's also truncated for cleaner UI display but screen readers announce the complete text" (full text)

### Technical Details

#### `LoadDescriptions(descriptions_list, truncate_at=100)`
- Takes list of dicts with 'description' key
- Creates truncated text for visual display
- Stores full text in memory
- Creates and assigns custom `wx.Accessible` instance

#### `GetFullDescription(index)`
- Returns complete dict for selected item
- Useful for getting metadata (model, timestamp, etc.)
- Returns empty dict if index is invalid

## Real-World Examples

### Viewer App (Image Descriptions)
```python
# In viewer_wx.py
self.desc_list = DescriptionListBox(left_panel)

# When loading workflow
entries = load_workflow_descriptions()  # Returns dicts with 'description' key
self.desc_list.LoadDescriptions(entries)

# When user selects
def on_description_selected(self, event):
    idx = self.desc_list.GetSelection()
    full_desc = self.desc_list.GetFullDescription(idx)
    self.display_image_preview(full_desc)
```

### ImageDescriber App (Generated Descriptions)
```python
# In imagedescriber_wx.py
self.desc_list = DescriptionListBox(right_panel)

# When image is selected
def display_image_info(self, image_item):
    # Build description data from ImageDescription objects
    desc_data = []
    for desc in image_item.descriptions:
        entry = {
            'description': desc.text,  # Full text (100-500+ chars)
            'model': desc.model,
            'prompt_style': desc.prompt_style,
            'created': desc.created
        }
        desc_data.append(entry)
    
    # Load with accessibility
    self.desc_list.LoadDescriptions(desc_data)
```

## When to Use

✅ **Use `DescriptionListBox` when:**
- Displaying text 100+ characters in length
- Need to truncate visually for UI clarity
- Must preserve full text for screen readers
- Users navigate with arrow keys (accessibility critical)

❌ **Don't use when:**
- Text is naturally short (< 50 chars) - use regular `wx.ListBox`
- Visual truncation isn't needed
- Single-column display isn't sufficient

## Customization

### Change Truncation Length
```python
# Truncate at 150 chars instead of default 100
desc_list.LoadDescriptions(descriptions, truncate_at=150)
```

### Different Text for Screen Readers
The current implementation uses the full 'description' value. To customize:
- Modify `AccessibleDescriptionListBox.GetName()` to build different text
- Example: Include model name in screen reader text: `f"{entry['model']}: {entry['description']}"`

### Add More Metadata
The 'description' key is required, but you can include any other fields:
```python
entry = {
    'description': 'The full text shown to screen readers',
    'model': 'gpt-4',
    'timestamp': '2025-01-09T10:30:00',
    'confidence': 0.95,
    'tags': ['sunset', 'landscape'],
    # ... any custom fields
}

# Access later with GetFullDescription()
entry = desc_list.GetFullDescription(selected_idx)
confidence = entry.get('confidence', 0)
```

## Troubleshooting

### Screen Readers Still Announce Truncated Text
**Cause**: wx.Accessible API behavior varies by platform  
**Workaround**: Use more verbose accessible text in `GetName()`:
```python
# In AccessibleDescriptionListBox.GetName():
return wx.ACC_OK, f"{full_text} (from {entry.get('model', 'unknown')})"
```

### ListBox Not Showing Items
**Cause**: Usually a layout issue  
**Debug**: Check parent sizer:
```python
# Make sure parent sizer uses EXPAND flag
sizer.Add(desc_list, 1, wx.EXPAND | wx.ALL, 5)  # ← Important: proportion=1, EXPAND
```

### Import Error: DescriptionListBox Not Found
**Cause**: Old import statement  
**Fix**: Use new import path:
```python
# OLD (if still using local copy):
# from custom_accessible_listbox_viewer import DescriptionListBox

# NEW (shared module):
from shared.wx_common import DescriptionListBox
```

## Performance Considerations

- **Memory**: Stores full text in memory (not displayed). For typical 1000 descriptions @ 300 chars = ~300KB (negligible)
- **Rendering**: Only truncated text rendered (fast), accessibility queries are on-demand
- **No Performance Issues**: Suitable for any realistic description count

## Future Improvements

1. **Customizable truncation indicator**: Allow "..." → "▸" or other characters
2. **Hover tooltips**: Show full text in tooltip (separate from accessibility)
3. **Search**: Integrate Find-in-ListBox functionality
4. **Sorting**: Add sort-by-metadata options
5. **Filtering**: Add filter capabilities with persistent accessibility

## See Also

- [accessible_listbox_impact_analysis.md](accessible_listbox_impact_analysis.md) - Why this pattern is needed
- [viewer/ACCESSIBLE_LISTBOX_PATTERN.txt](../../viewer/ACCESSIBLE_LISTBOX_PATTERN.txt) - Original pattern documentation
- [imagedescriber/imagedescriber_wx.py](../../imagedescriber/imagedescriber_wx.py#L592) - Real-world usage example

