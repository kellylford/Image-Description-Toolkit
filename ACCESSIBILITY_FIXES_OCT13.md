# ImageDescriber Accessibility Fixes - October 13, 2025

## Overview
Fixed accessibility issues in ImageDescriber's view modes to improve screen reader experience and keyboard navigation.

## Issues Fixed

### 1. Accessible Name Changes Based on View Mode

**Problem:** When in flat view mode (Descriptions First), the `image_list` control was showing descriptions but still had the accessible name "Image List", which was confusing for screen reader users.

**Solution:** The accessible name now dynamically changes based on the view mode:
- **AI Generation mode** (tree view): "Image List" 
  - Description: "List of images and video frames in the workspace. Use arrow keys to navigate, P to process selected image, B to mark for batch."
- **Descriptions First mode** (flat view): "Descriptions List"
  - Description: "List of all descriptions for images and video frames. Use arrow keys to navigate. Each entry shows the full description, image name, model, and prompt."

**Code Location:** `set_view_mode()` method in `imagedescriber.py` (line ~8337)

### 2. Hide Unused Controls in Descriptions First Mode

**Problem:** In Descriptions First mode (flat view), the `description_list` and `description_text` controls were still visible and reachable via Tab key, even though they would never have content in this mode.

**Solution:** 
- In **Descriptions First mode**: `description_list` and `description_text` are now hidden
- In **AI Generation mode**: Both controls are shown normally

**Code Location:** `set_view_mode()` method in `imagedescriber.py` (line ~8337)

### 3. Dynamic Tab Order Based on View Mode

**Problem:** Tab order was static and included controls that weren't visible/useful in certain modes.

**Solution:** Tab order now updates dynamically based on view mode:

**AI Generation mode (tree view):**
- image_list → description_list → description_text → image_preview (if visible)

**Descriptions First mode (flat view):**
- image_list (showing descriptions) → image_preview (if visible)
- Skips the hidden description_list and description_text controls

**Code Location:** `set_view_mode()` method in `imagedescriber.py` (line ~8337)

### 4. Renamed View Modes for Clarity

**Problem:** View mode names "Image Tree" and "Flat Image List" didn't clearly convey the purpose of each mode.

**Solution:** Renamed view modes to better reflect their purpose:
- "Image Tree" → **"AI Generation"** (mode for selecting images and generating descriptions)
- "Flat Image List" → **"Descriptions First"** (mode for browsing existing descriptions)

**Code Location:** 
- Menu items: Line ~4901-4910 in `imagedescriber.py`
- Status messages: `set_view_mode()` method (line ~8337)

## Testing Checklist

### AI Generation Mode (Tree View)
- [ ] Launch ImageDescriber
- [ ] Verify View → View Mode shows "AI Generation" as checked
- [ ] Load images/videos
- [ ] Tab through controls: Should go image_list → description_list → description_text → preview
- [ ] With screen reader: Verify "Image List" is announced for image_list
- [ ] Verify description_list and description_text are visible and functional

### Descriptions First Mode (Flat View)
- [ ] Switch to View → View Mode → Descriptions First
- [ ] Tab through controls: Should skip description_list and description_text
- [ ] With screen reader: Verify "Descriptions List" is announced for image_list
- [ ] Verify description_list and description_text are hidden
- [ ] Verify each description entry shows full description + metadata
- [ ] Switch back to AI Generation mode
- [ ] Verify controls reappear and tab order is restored

### Mode Switching
- [ ] Switch between modes multiple times
- [ ] Verify accessible names update correctly each time
- [ ] Verify tab order updates correctly each time
- [ ] Verify status bar shows correct mode name

## Implementation Details

### Files Modified
- `imagedescriber/imagedescriber.py`

### Functions Modified
- `set_view_mode()` - Added dynamic accessible name changes, control visibility, and tab order management

### Menu Items Changed
- View → View Mode → "Image Tree" → "AI Generation"
- View → View Mode → "Flat Image List" → "Descriptions First"

## Related Issues
- GitHub Issue #48: "Resolve flat view in image describer on image import without descriptions"
  - Note: This fix addresses accessibility concerns. The design question about what to show in flat view (all items vs. only described items) is still open.

## Backward Compatibility
- Internal `view_mode` value remains "tree" and "flat" (unchanged)
- Only user-facing names changed
- All existing functionality preserved

## Benefits
1. **Screen Reader Users:** Clear indication of what list content is being shown
2. **Keyboard Users:** Efficient tab navigation without hitting empty controls
3. **All Users:** Clear mode names that convey purpose
4. **Accessibility:** Meets WCAG guidelines for proper labeling and keyboard navigation
