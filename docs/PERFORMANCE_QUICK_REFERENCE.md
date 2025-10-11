# Quick Reference: GUI Performance Optimization

## The Golden Rules

### 1. Fast First, Slow Later
```python
# ✓ GOOD: Immediate feedback, defer expensive work
def on_selection(row):
    self.update_text(row)           # FAST: ~5ms
    QTimer.singleShot(100, lambda: self.load_image(row))  # SLOW: deferred

# ✗ BAD: Everything synchronous
def on_selection(row):
    self.update_text(row)           # FAST: ~5ms
    self.load_image(row)            # SLOW: ~50ms - blocks UI!
```

### 2. Check Before Update
```python
# ✓ GOOD: Avoid redundant updates
if self.text_widget.toPlainText() != new_text:
    self.text_widget.setPlainText(new_text)

# ✗ BAD: Always updates
self.text_widget.setPlainText(new_text)  # May cause cursor jump
```

### 3. Early Returns
```python
# ✓ GOOD: Exit fast for invalid cases
def on_selection(row):
    if self.updating_content:
        return  # Skip during batch updates
    # ... normal processing ...

# ✗ BAD: Deep nesting
def on_selection(row):
    if not self.updating_content:
        # ... all processing nested ...
```

### 4. Direct Data Access
```python
# ✓ GOOD: O(1) array access
description = self.descriptions[row]

# ✗ BAD: Database/workspace query
description = self.workspace.get_item(file_path).get_description()
```

### 5. Simple Signals
```python
# ✓ GOOD: Direct connection
self.list_widget.currentRowChanged.connect(self.display_item)

# ✗ BAD: Chain of signals
self.list_widget.currentRowChanged.connect(self.on_selection)
self.on_selection → self.process_selection → self.display_item
```

## Performance Checklist

When implementing list navigation:

- [ ] Text updates happen immediately (<10ms)
- [ ] Image/preview loading is deferred (100-200ms)
- [ ] Early return for invalid selections
- [ ] Early return during batch updates
- [ ] Check if content changed before updating widget
- [ ] Use direct array access, not database queries
- [ ] Single signal connection to handler
- [ ] No nested signal chains
- [ ] Accessibility descriptions maintained
- [ ] Focus management preserved

## Timing Targets

| Operation | Target | Max Acceptable |
|-----------|--------|----------------|
| Text update | <5ms | <10ms |
| List navigation response | <10ms | <20ms |
| Image preview (deferred) | +100-200ms | +500ms |
| Data lookup | <1ms | <5ms |

## Common Anti-Patterns

### ❌ Synchronous Image Loading
```python
def on_selection(row):
    self.text.setPlainText(self.descriptions[row])
    pixmap = QPixmap(self.images[row])  # BLOCKS!
    self.image_label.setPixmap(pixmap)
```

### ❌ Repeated Data Role Lookups
```python
def on_selection():
    item = self.list.currentItem()
    path = item.data(Qt.UserRole)           # Query 1
    name = item.data(Qt.UserRole)           # Query 2 (same!)
    type = item.data(Qt.UserRole + 1)       # Query 3
```

### ❌ Workspace Queries in Selection Handler
```python
def on_selection():
    path = self.current_file_path
    item = self.workspace.get_item(path)     # Database query!
    descs = item.get_descriptions()          # More queries!
```

### ❌ Complex Formatting Every Time
```python
def on_selection():
    desc = self.descriptions[row]
    formatted = self.format_for_accessibility(desc)  # Expensive!
    self.text.setPlainText(formatted)
```

## Quick Fixes

### Fix #1: Defer Images
```python
# Before
def on_selection(row):
    self.update_text(row)
    self.load_image(row)  # Blocks

# After
def on_selection(row):
    self.update_text(row)
    self.pending_row = row
    self.image_timer.start(100)  # Deferred
```

### Fix #2: Cache Formatting
```python
# Before
def on_selection(row):
    text = self.format_description(self.descriptions[row])  # Every time!

# After
def on_selection(row):
    if row not in self.formatted_cache:
        self.formatted_cache[row] = self.format_description(self.descriptions[row])
    text = self.formatted_cache[row]
```

### Fix #3: Store Data References
```python
# Before
item.setData(Qt.UserRole, file_path)
# Later: workspace.get_item(file_path)  # Query!

# After
item.setData(Qt.UserRole, workspace_item_ref)
# Later: workspace_item_ref  # Direct access!
```

## Implementation Template

```python
class OptimizedListView:
    def __init__(self):
        # Deferred loading timer
        self.preview_timer = QTimer()
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self._load_preview)
        self.pending_item = None
        
        # Cache
        self.formatted_cache = {}
        
        # Guard flag
        self.updating_content = False
        
        # Connect signals
        self.list.currentRowChanged.connect(self.on_selection)
    
    def on_selection(self, row):
        # Guard clause
        if self.updating_content:
            return
        
        # FAST: Update text immediately
        if 0 <= row < len(self.items):
            # Use cache if available
            if row not in self.formatted_cache:
                self.formatted_cache[row] = self.format_text(self.items[row])
            
            # Only update if changed
            text = self.formatted_cache[row]
            if self.text_widget.toPlainText() != text:
                self.text_widget.setPlainText(text)
        
        # SLOW: Defer preview loading
        self.pending_item = row
        self.preview_timer.start(100)
    
    def _load_preview(self):
        row = self.pending_item
        if row is not None and 0 <= row < len(self.items):
            # Load and display preview
            self.load_and_display_preview(row)
```

## Measurement

### Add Timing
```python
import time

def on_selection(self, row):
    start = time.perf_counter()
    
    # ... your code ...
    
    elapsed = (time.perf_counter() - start) * 1000
    if elapsed > 10:
        print(f"WARNING: on_selection took {elapsed:.1f}ms")
```

### Profile with cProfile
```python
import cProfile
profiler = cProfile.Profile()
profiler.enable()

# Navigate through list
for i in range(100):
    self.list.setCurrentRow(i)
    QApplication.processEvents()

profiler.disable()
profiler.print_stats(sort='cumulative')
```

## See Also

- Full guide: `docs/GUI_PERFORMANCE_OPTIMIZATION.md`
- Implementation example: `viewer/viewer.py` lines 920-1001
- Viewer optimization notes: `docs/VIEWER_PERFORMANCE_OPTIMIZATION.md`
