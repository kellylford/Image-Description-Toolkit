#!/usr/bin/env python3
"""
Manual Test for Viewer Performance Optimization

This script provides a manual testing procedure to verify the debounced
image preview loading optimization in the viewer application.

Prerequisites:
1. PyQt6 installed (pip install PyQt6)
2. Test images available
3. A workflow output directory with descriptions

Test Procedure:
"""

import sys
from pathlib import Path

def print_test_procedure():
    """Print the manual test procedure"""
    print("=" * 80)
    print("VIEWER PERFORMANCE OPTIMIZATION - MANUAL TEST PROCEDURE")
    print("=" * 80)
    print()
    
    print("SETUP:")
    print("-" * 80)
    print("1. Ensure PyQt6 is installed: pip install PyQt6")
    print("2. Have a workflow output directory with:")
    print("   - html_reports/image_descriptions.html OR")
    print("   - descriptions/image_descriptions.txt (for live mode)")
    print("3. Directory should have 20+ images for effective testing")
    print()
    
    print("TEST 1: Rapid Arrow Key Navigation")
    print("-" * 80)
    print("OBJECTIVE: Verify no lag during rapid navigation")
    print()
    print("Steps:")
    print("  1. Run viewer: python3 viewer/viewer.py")
    print("  2. Load a directory with 20+ images")
    print("  3. Click on the description list to focus it")
    print("  4. RAPIDLY press arrow down key 10-15 times")
    print()
    print("Expected Behavior:")
    print("  ✓ List selection moves instantly (no lag)")
    print("  ✓ Description text updates immediately")
    print("  ✓ Image preview appears ~150ms after you STOP pressing keys")
    print("  ✓ No visible stuttering or freezing")
    print()
    print("Before Optimization (what to NOT see):")
    print("  ✗ Noticeable delay between key press and selection change")
    print("  ✗ UI freezes briefly on each key press")
    print("  ✗ Images flash rapidly during navigation")
    print()
    
    print("TEST 2: Single Selection Change")
    print("-" * 80)
    print("OBJECTIVE: Verify normal behavior still works")
    print()
    print("Steps:")
    print("  1. With viewer open and directory loaded")
    print("  2. Click on a description in the list")
    print("  3. Wait and observe")
    print()
    print("Expected Behavior:")
    print("  ✓ Description text appears immediately")
    print("  ✓ Image preview loads within 150ms")
    print("  ✓ All accessibility features work normally")
    print()
    
    print("TEST 3: Live Mode Refresh")
    print("-" * 80)
    print("OBJECTIVE: Verify live updates don't trigger unnecessary previews")
    print()
    print("Steps:")
    print("  1. Load a directory with live descriptions file")
    print("  2. Enable 'Live Mode' checkbox")
    print("  3. Select an image")
    print("  4. Add a new description to the file (simulate workflow)")
    print()
    print("Expected Behavior:")
    print("  ✓ New descriptions appear in list")
    print("  ✓ Current selection preserved")
    print("  ✓ No unexpected image reloads")
    print()
    
    print("TEST 4: Redescribe Feature")
    print("-" * 80)
    print("OBJECTIVE: Verify redescribe still updates preview")
    print()
    print("Steps:")
    print("  1. Select an image")
    print("  2. Click 'Redescribe' button")
    print("  3. Choose model and prompt")
    print("  4. Wait for completion")
    print()
    print("Expected Behavior:")
    print("  ✓ Description updates in list")
    print("  ✓ Description text area updates")
    print("  ✓ Image preview remains visible")
    print()
    
    print("PERFORMANCE METRICS TO OBSERVE:")
    print("-" * 80)
    print("• Selection change latency: < 10ms (instant feel)")
    print("• Text update latency: < 50ms (instant feel)")
    print("• Image preview latency: ~150ms after navigation stops")
    print("• CPU usage during rapid navigation: Low (no image loading)")
    print("• Memory usage: Stable (no image caching yet)")
    print()
    
    print("CODE INSPECTION:")
    print("-" * 80)
    print("Review the following in viewer.py:")
    print()
    print("1. Timer initialization (__init__ method):")
    print("   self.image_preview_timer = QTimer()")
    print("   self.image_preview_timer.setSingleShot(True)")
    print("   self.image_preview_timer.timeout.connect(self._update_image_preview_delayed)")
    print("   self.pending_preview_row = None")
    print()
    print("2. Display description method splits operations:")
    print("   - Text update: Immediate (lines 920-969)")
    print("   - Image preview: Delayed via timer (lines 971-976)")
    print()
    print("3. New method _update_image_preview_delayed:")
    print("   - Loads image after debounce delay")
    print("   - Only runs if row is valid")
    print()
    print("4. Timer cleanup in stop_live_monitoring:")
    print("   - Stops image_preview_timer on close")
    print()
    
    print("DEBUGGING:")
    print("-" * 80)
    print("If issues occur, add debug prints:")
    print()
    print("In display_description:")
    print("  print(f'display_description called for row {row}')")
    print()
    print("In _update_image_preview_delayed:")
    print("  print(f'Loading image preview for row {self.pending_preview_row}')")
    print()
    print("This will show:")
    print("  - display_description called many times during rapid navigation")
    print("  - _update_image_preview_delayed called once after navigation stops")
    print()
    
    print("SUCCESS CRITERIA:")
    print("-" * 80)
    print("✓ Arrow key navigation feels as responsive as a simple text list")
    print("✓ No noticeable lag when rapidly pressing arrow keys")
    print("✓ Image previews load smoothly after navigation stops")
    print("✓ All existing features (redescribe, copy, live mode) work correctly")
    print("✓ Accessibility features remain intact")
    print()
    
    print("=" * 80)
    print("For automated testing, consider using pytest-qt with QTest.keyClick")
    print("=" * 80)
    print()

if __name__ == "__main__":
    print_test_procedure()
    
    # Optional: Check if viewer can be imported
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent / "viewer"))
        print("Attempting to verify viewer.py syntax...")
        import py_compile
        viewer_path = Path(__file__).parent.parent / "viewer" / "viewer.py"
        py_compile.compile(str(viewer_path), doraise=True)
        print("✓ viewer.py syntax is valid")
        print()
    except Exception as e:
        print(f"✗ Syntax check failed: {e}")
        print()
    
    print("To run the viewer:")
    print("  cd viewer && python3 viewer.py")
    print()
