# Viewer Application Code Path Analysis

**Purpose**: Understanding how the Viewer application processes and displays workflow results  
**Last Updated**: October 28, 2025  
**File**: `viewer/viewer.py` (1700+ lines)

---

## Overview

The Viewer application has **two distinct operating modes** with completely different code paths for loading and displaying workflow results. Understanding these paths is critical for debugging display issues and understanding the application's behavior.

---

## Mode Detection & Auto-Switching

### Auto-Mode Selection (Lines 1235-1250)

```python
def load_workflow_descriptions(self, dir_path):
    # Check if live mode should be auto-enabled
    descriptions_file = Path(dir_path) / "descriptions" / "image_descriptions.txt"
    html_file = Path(dir_path) / "html_reports" / "image_descriptions.html"
    
    # Auto-enable live mode if descriptions file exists but HTML doesn't
    if descriptions_file.exists() and not html_file.exists():
        self.live_mode_checkbox.setChecked(True)
        self.live_mode = True
    
    if self.live_mode:
        self.start_live_monitoring()
    else:
        self.load_html_descriptions(dir_path)
```

**Decision Logic**:
- If `image_descriptions.txt` exists **AND** `image_descriptions.html` does NOT exist → **Live Mode**
- If `image_descriptions.html` exists → **HTML Mode** (regardless of txt file)
- User can manually toggle via checkbox

**Why This Matters**:
- During workflow execution: Automatically uses Live Mode for real-time monitoring
- After workflow completion: Automatically switches to HTML Mode for final results
- This auto-switching can cause confusion if you're not aware of the mode change

---

## Code Path 1: HTML Mode

### Entry Point: `load_html_descriptions()` (Lines 1252-1306)

**Data Source**: `html_reports/image_descriptions.html`

**Parsing Method**: Regex extraction from HTML

```python
def load_html_descriptions(self, dir_path):
    html_path = os.path.join(dir_path, "html_reports", "image_descriptions.html")
    
    # Read entire HTML file
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()
    
    # Extract entries using regex pattern
    entry_pattern = re.compile(
        r'<div class="entry" id="entry-\d+">.*?<h2>(.*?)</h2>.*?'
        r'<h4>Description</h4>.*?<p>(.*?)</p>', 
        re.DOTALL
    )
    entries = entry_pattern.findall(html)
```

**What Gets Extracted**:
1. **Image Path**: From `<h2>` tag (e.g., `hawaii\boat\P1012338.JPG`)
2. **Description**: From `<p>` tag after "Description" heading

**Post-Processing**:
```python
for img_path, desc in entries:
    # Convert path separators to OS-specific format
    img_path = img_path.replace('\\', os.sep).replace('/', os.sep)
    
    # Convert HTML line breaks to newlines
    desc = re.sub(r'<br\s*/?>', '\n', desc)
    
    # Decode HTML entities (&quot;, &#x27;, &amp;, etc.)
    desc = re.sub(r'&[a-zA-Z0-9#]+;', lambda m: {
        '&quot;': '"', '&#x27;': "'", '&amp;': '&', 
        '&lt;': '<', '&gt;': '>'
    }.get(m.group(0), m.group(0)), desc)
```

**List Display**:
```python
# Truncate description for list item
truncated = desc[:100] + ("..." if len(desc) > 100 else "")
item = QListWidgetItem(truncated)

# Store full description for screen readers
item.setData(Qt.ItemDataRole.AccessibleTextRole, desc.strip())
self.list_widget.addItem(item)
```

**Behavior Characteristics**:
- ✅ **Static**: Loads once, no automatic updates
- ✅ **Complete**: All entries loaded at once
- ❌ **Destructive Refresh**: Clears entire list and rebuilds on manual refresh
- ❌ **Focus Disruption**: Jumps to top on reload
- ❌ **No Progress Tracking**: Shows final count only

---

## Code Path 2: Live Mode

### Entry Point: `start_live_monitoring()` → `refresh_live_content()` (Lines 1090-1196)

**Data Source**: `descriptions/image_descriptions.txt`

**Parsing Method**: Structured field parsing via `DescriptionFileParser`

### Phase 1: File Parsing (`DescriptionFileParser._parse_entry()`, Lines 123-177)

```python
def _parse_entry(self, section: str) -> dict:
    """Parse a single entry section from text file"""
    entry = {
        'file_path': '',
        'relative_path': '',
        'description': '',
        'model': '',
        'prompt_style': '',
        'metadata': {}
    }
    
    for line in lines:
        if line.startswith('File: '):
            entry['relative_path'] = line[6:].strip()
        elif line.startswith('Photo Date: '):
            entry['metadata']['photo_date'] = line[12:].strip()
        elif line.startswith('Camera: '):
            entry['metadata']['camera'] = line[8:].strip()
        elif line.startswith('Provider: '):
            entry['metadata']['provider'] = line[10:].strip()
        elif line.startswith('Model: '):
            entry['model'] = line[7:].strip()
        elif line.startswith('Prompt Style: '):
            entry['prompt_style'] = line[14:].strip()
        elif line.startswith('Description: '):
            description_started = True
            description_lines.append(line[13:].strip())
        # ... continues collecting description lines
    
    return entry if entry['description'] else None
```

**Field Recognition** (as of Oct 28, 2025 fix):
- ✅ `File:` - Relative path to image
- ✅ `Path:` - Full path to image
- ✅ `Photo Date:` - EXIF date from image
- ✅ `Camera:` - Camera model from EXIF
- ✅ `Provider:` - AI provider (ollama, openai, claude)
- ✅ `Model:` - AI model name
- ✅ `Prompt Style:` - Prompt variation used
- ✅ `Description:` - AI-generated description (multi-line)
- ✅ `Timestamp:` - When description was generated
- ✅ Skip summary lines: `[12/31/2001 8:00A, CAMERA]`

### Phase 2: Content Refresh (`refresh_live_content()`, Lines 1090-1196)

**Smart Update Logic**:

```python
def refresh_live_content(self):
    # 1. Check if user is actively interacting - if so, defer update
    focused_widget = QApplication.focusWidget()
    if focused_widget in [self.list_widget, self.description_text]:
        return  # Don't disrupt user
    
    # 2. Save current state
    current_row = self.list_widget.currentRow()
    current_item_count = self.list_widget.count()
    
    # 3. Parse file (cached if unchanged)
    entries = self.description_parser.parse_file(descriptions_file)
    
    # 4. Early exit if no new entries
    if len(entries) == current_item_count:
        return  # Just update progress info
    
    # 5. Add ONLY new entries (incremental)
    new_entries = entries[current_item_count:]
    for entry in new_entries:
        # Resolve image path (tries multiple locations)
        # Add to lists and UI
    
    # 6. Preserve selection - don't steal focus
    if current_row >= 0:
        self.list_widget.setCurrentRow(current_row)
```

**Image Path Resolution** (Lines 1150-1167):
```python
# Try multiple possible locations in order
possible_paths = [
    base_dir / "temp_combined_images" / rel_path,  # Workflow staging
    base_dir / "converted_images" / rel_path,      # After HEIC conversion
    base_dir / "extracted_frames" / rel_path,       # From videos
    base_dir / rel_path                             # Direct path
]

# Use first existing path
for possible_path in possible_paths:
    if possible_path.exists():
        image_path = str(possible_path)
        break
```

**List Display** (Lines 1171-1176):
```python
# Same truncation as HTML mode
truncated = entry['description'][:100] + ("..." if len(entry['description']) > 100 else "")
item = QListWidgetItem(truncated)

# Store full description for screen readers
item.setData(Qt.ItemDataRole.AccessibleTextRole, entry['description'].strip())
self.list_widget.addItem(item)
```

**Behavior Characteristics**:
- ✅ **Dynamic**: Auto-refreshes via QFileSystemWatcher
- ✅ **Incremental**: Adds only new entries, preserves existing
- ✅ **Non-Disruptive**: Preserves scroll position and selection
- ✅ **Focus-Aware**: Defers updates when user is actively interacting
- ✅ **Progress Tracking**: Shows current/total and updates in real-time
- ✅ **Graceful**: Handles file changes without crashing

---

## Visual Differences Between Modes

### List Display Format

**Both modes show identical format**:
```
Description text truncated to 100 characters...
```

**Why?** Both use the same truncation logic:
```python
truncated = description[:100] + ("..." if len(description) > 100 else "")
```

### Window Title

**HTML Mode**:
```
Viewer - workflow_name (XX%, X of Y images described)
```

**Live Mode**:
```
Viewer - workflow_name (XX%, X of Y images described) (Live)
```

### Status Bar

**HTML Mode**:
```
"Loaded X descriptions from HTML report"
```

**Live Mode**:
```
"Live mode: X descriptions loaded (Active)"  [during workflow]
"Live mode: X descriptions loaded"           [workflow paused]
```

### Update Behavior

| Aspect | HTML Mode | Live Mode |
|--------|-----------|-----------|
| Refresh Trigger | Manual button only | Auto (file watcher) + Manual |
| Update Style | Clear all → Rebuild | Append new entries |
| Position Preservation | ❌ Jumps to top | ✅ Stays in place |
| Focus Handling | Takes focus | Preserves focus |
| User Interaction | Disrupts on refresh | Non-disruptive |

---

## Common Issues & Debugging

### Issue: "Viewer only shows dates, not descriptions"

**Root Cause**: Parser not handling all metadata fields

**Affected Path**: Live Mode (`DescriptionFileParser._parse_entry()`)

**Fix Applied** (Oct 28, 2025):
- Added parsing for: `Photo Date:`, `Camera:`, `Provider:`
- Added skip logic for summary lines: `[date, camera]`
- Updated exclusion list to prevent metadata from being included in description

**Why it only appeared "when done"**:
- During workflow: Live Mode was active (parser bug dormant but tolerated)
- After completion: Auto-switched to HTML Mode, which has different regex-based parsing
- HTML Mode may have had its own issues extracting the full description

### Issue: "Descriptions cut off or missing"

**HTML Mode Diagnosis**:
```python
# Check if regex pattern matches your HTML structure
entry_pattern = re.compile(
    r'<div class="entry" id="entry-\d+">.*?<h2>(.*?)</h2>.*?'
    r'<h4>Description</h4>.*?<p>(.*?)</p>', 
    re.DOTALL
)
```

**Potential Problems**:
- HTML structure changed but regex not updated
- Description spans multiple `<p>` tags (regex only captures first)
- Special characters breaking regex

**Live Mode Diagnosis**:
```python
# Check if all fields before "Description:" are recognized
# Unrecognized fields may prevent description_started flag from working
```

### Issue: "Image paths not resolving"

**Live Mode has fallback logic** (tries 4 locations)  
**HTML Mode uses path from HTML directly** (no fallback)

**Debug**:
```python
# Live Mode: Check all possible_paths in order
print(f"Tried: {possible_paths}")

# HTML Mode: Path comes from <h2> tag in HTML
```

---

## File Format Requirements

### Live Mode Expects (`image_descriptions.txt`):

```
File: relative/path/to/image.jpg
Path: /full/path/to/image.jpg
Photo Date: 12/31/2001 8:00A
Camera: CAMERA MODEL
Provider: ollama
Model: moondream
Prompt Style: narrative
Description: The actual description text here...
Timestamp: 2025-10-28 22:18:06
[12/31/2001 8:00A, CAMERA MODEL]
--------------------------------------------------------------------------------
```

**Critical**: Field names must match exactly (case-sensitive)

### HTML Mode Expects (`image_descriptions.html`):

```html
<div class="entry" id="entry-1">
    <h2>relative/path/to/image.jpg</h2>
    <h4>Description</h4>
    <p>The actual description text here...</p>
</div>
```

**Critical**: Structure must match regex pattern exactly

---

## Performance Considerations

### HTML Mode
- **Load Time**: O(n) - reads entire file once, parses all entries
- **Memory**: Stores all descriptions in memory at once
- **Refresh Cost**: O(n) - rebuilds entire list every time

### Live Mode
- **Load Time**: O(n) - initial parse
- **Memory**: Same as HTML mode (all in memory)
- **Refresh Cost**: O(k) where k = new entries only (typically k << n)
- **File Monitoring**: Minimal overhead (OS-level file watcher)

**Recommendation**: 
- For active workflows (< 1000 images): Live Mode is superior
- For massive completed workflows (10k+ images): Consider HTML Mode for simplicity

---

## Extension Points

### Adding New Metadata Fields

**Live Mode** (Easy):
1. Add field parsing in `_parse_entry()`:
   ```python
   elif line.startswith('YourField: '):
       entry['metadata']['your_field'] = line[11:].strip()
   ```
2. Add to exclusion list in `description_started` check

**HTML Mode** (Medium):
1. Ensure field is in HTML output
2. Extend regex pattern if needed
3. Add post-processing if required

### Supporting Alternative HTML Structures

Modify regex in `load_html_descriptions()`:
```python
# Example: Support multiple <p> tags for description
entry_pattern = re.compile(
    r'<div class="entry".*?<h2>(.*?)</h2>.*?'
    r'<h4>Description</h4>(.*?)<h4>',  # Capture until next heading
    re.DOTALL
)
```

---

## Testing Checklist

When modifying parser or display logic:

- [ ] Test with **in-progress workflow** (Live Mode)
- [ ] Test with **completed workflow** (HTML Mode)
- [ ] Test **manual mode toggle** during active workflow
- [ ] Test with **various image path structures** (subdirectories, spaces, special chars)
- [ ] Test **screen reader accessibility** (AccessibleTextRole data)
- [ ] Test **focus preservation** during live updates
- [ ] Test with **empty descriptions**
- [ ] Test with **very long descriptions** (1000+ chars)
- [ ] Test **HTML entities** in descriptions (&, <, >, quotes)
- [ ] Test **description prefixes** (dates, locations) parsing

---

## Related Files

- `viewer/viewer.py` - Main application (1700+ lines)
- `scripts/descriptions_to_html.py` - Generates HTML reports
- `scripts/image_describer.py` - Writes `image_descriptions.txt`
- `scripts/list_results.py` - Shared workflow scanning utilities
- `docs/archive/VIEWER_CODE_PATHS.md` - This document

---

## Version History

- **Oct 28, 2025**: Initial documentation
  - Identified dual code path architecture
  - Documented parser bug fix (Photo Date, Camera, Provider fields)
  - Explained mode auto-switching behavior
