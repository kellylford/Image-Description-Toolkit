# Viewer Performance Optimization

## Overview

This document describes the performance optimizations implemented in the Image Description Viewer to ensure responsive navigation when browsing through large image sets.

## Problem

When navigating through a list of images using arrow keys, each selection change triggered:
1. Description text update (fast)
2. Image file loading from disk (potentially slow)
3. Image scaling/transformation (CPU intensive)

This could cause noticeable lag, especially when rapidly pressing arrow keys to browse through many images.

## Solution: Debounced Image Preview Loading

### Implementation Details

#### 1. Added Timer-Based Debouncing

In `viewer.py`, added a single-shot timer to debounce image preview loading:

```python
# In __init__:
self.image_preview_timer = QTimer()
self.image_preview_timer.setSingleShot(True)
self.image_preview_timer.timeout.connect(self._update_image_preview_delayed)
self.pending_preview_row = None
```

#### 2. Split Fast and Slow Operations

Modified `display_description()` method to:
- **Update description text immediately** (lines 920-969)
  - Fast operation with minimal overhead
  - Provides instant user feedback
  - Maintains accessibility features
  
- **Delay image preview loading** (lines 971-976)
  - Cancels any pending preview timer
  - Stores the row to preview
  - Starts a 150ms debounce timer

```python
def display_description(self, row):
    # ... Update text immediately ...
    
    # Delay image preview loading to avoid blocking UI during rapid navigation
    self.image_preview_timer.stop()
    self.pending_preview_row = row
    self.image_preview_timer.start(150)
```

#### 3. Delayed Image Loading

Created `_update_image_preview_delayed()` method (lines 978-1012):
- Called after 150ms debounce delay
- Loads and displays the image preview
- Only executes if user has stopped navigating

## Benefits

### Performance Improvements

1. **Instant Text Response**: Description text updates immediately on arrow key press
2. **Reduced I/O**: Image files only loaded after user stops navigating
3. **Lower CPU Usage**: Image scaling operations deferred until needed
4. **Smoother Navigation**: No blocking operations during rapid key presses

### User Experience

- **Responsive Feel**: Immediate visual feedback from text updates
- **Smooth Scrolling**: No lag when rapidly pressing arrow keys
- **Progressive Loading**: Images appear shortly after navigation stops
- **No Regression**: All existing functionality preserved

### Accessibility Maintained

- Accessible descriptions update immediately
- Screen readers announce changes without delay
- Focus management unchanged
- Keyboard navigation remains fluid

## Technical Details

### Debounce Delay: 150ms

The 150ms delay was chosen to balance:
- **Responsiveness**: Short enough to feel instant when user stops
- **Performance**: Long enough to skip loading during rapid navigation
- **User Experience**: Matches typical UI interaction patterns

### Timer Behavior

- **Single-shot**: Timer fires once per navigation stop
- **Cancellable**: Each new selection cancels pending preview
- **Memory Efficient**: Only stores row number, not image data

## Testing Recommendations

When testing this optimization:

1. Load a workspace with 100+ images
2. Rapidly press arrow keys up/down through image list
3. Verify:
   - Description text updates immediately
   - Navigation feels smooth and responsive
   - Images load within ~150ms after stopping
   - No crashes or visual glitches

## Code Changes Summary

**File**: `viewer/viewer.py`

**Added**:
- `self.image_preview_timer` (QTimer instance)
- `self.pending_preview_row` (current row tracker)
- `_update_image_preview_delayed()` method

**Modified**:
- `__init__()`: Added timer initialization
- `display_description()`: Split into immediate text update + delayed image loading

**Lines Changed**: ~35 lines (additions and modifications)

## Future Enhancements

Potential additional optimizations:

1. **Image Caching**: Cache recently loaded images in memory
2. **Thumbnail Generation**: Use smaller previews for faster loading
3. **Lazy Scaling**: Defer image scaling until window size stable
4. **Progressive Loading**: Load preview at lower quality first

## Related Issues

This optimization addresses the performance strategy outlined in:
- Issue: "Optimize ImageDescriber Navigation Performance - Slow Arrow Key Response"
- Strategy: Priority 2 - "Lazy image preview loading"
