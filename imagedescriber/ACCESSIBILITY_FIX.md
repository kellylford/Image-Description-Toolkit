# Screen Reader Accessibility Fix

## Issue
Processing status messages in the image list were being truncated for screen readers, making it impossible for users with visual impairments to access the full status information.

## Root Cause
In the `get_display_name()` method, processing status messages longer than 50 characters were truncated to 47 characters + "..." for visual display:

```python
# Old code (line ~7232-7234)
if len(status_msg) > 50:
    status_msg = status_msg[:47] + "..."
```

This truncated text was the only version available to screen readers through the QListWidgetItem.

## Solution
Implemented a comprehensive accessibility solution that:

1. **Preserves visual truncation** for UI cleanliness while providing full content to screen readers
2. **Adds accessibility properties** using PyQt6's built-in accessibility features
3. **Sets tooltips** with full status messages
4. **Uses AccessibleDescriptionRole** to provide complete information to assistive technologies

### Key Changes

1. **New helper method** `set_item_accessibility()`:
   - Sets `AccessibleTextRole` with full display name
   - Provides complete status messages via `AccessibleDescriptionRole`
   - Sets tooltips with full processing status
   - Handles both processing and non-processing items

2. **Updated `update_specific_item_display()`**:
   - Now calls `set_item_accessibility()` to ensure full status is available to screen readers
   - Maintains visual truncation while providing accessibility

3. **Enhanced initial list population**:
   - Added accessibility setup when items are first created
   - Ensures consistent accessibility across all list items

## Technical Implementation

The fix uses PyQt6's accessibility framework:

```python
# Visual display (truncated)
item.setText(display_name)  # May contain "p [Processing image...]"

# Full content for screen readers
item.setData(Qt.ItemDataRole.AccessibleTextRole, display_name)
item.setData(Qt.ItemDataRole.AccessibleDescriptionRole, accessible_name)
item.setToolTip(f"Status: {full_status}")
```

## Testing
- Application starts without errors
- Visual display remains clean with truncated messages
- Screen readers can access full status information through accessibility properties
- Tooltip provides additional context on hover

## Accessibility Standards
This fix aligns with:
- WCAG 2.1 Guidelines for programmatically determinable information
- Qt Accessibility Guidelines for assistive technology support
- Screen reader best practices for dynamic content updates