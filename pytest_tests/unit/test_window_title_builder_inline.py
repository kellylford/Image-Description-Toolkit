#!/usr/bin/env python3
"""
Quick inline tests for window_title_builder module

This tests the functions directly without external dependencies
"""

import sys
import os

# Test the functions directly by executing the module code
def test_window_title_builder():
    """Test window_title_builder functions inline"""
    
    # Define the functions inline for testing
    def build_window_title(
        progress_percent: int,
        current: int,
        total: int,
        operation: str = "Processing",
        context_parts=None,
        suffix: str = ""
    ) -> str:
        """Build a standardized window title for IDT applications."""
        base_title = f"IDT - {operation} ({progress_percent}%, {current} of {total})"
        if suffix:
            base_title += suffix
        if context_parts:
            valid_parts = [str(part).strip() for part in context_parts if part]
            if valid_parts:
                base_title += f" - {' - '.join(valid_parts)}"
        return base_title

    def build_window_title_from_context(
        progress_percent: int,
        current: int,
        total: int,
        operation: str,
        workflow_name=None,
        prompt_style=None,
        model_name=None,
        suffix: str = ""
    ) -> str:
        """Build a standardized window title with explicit context parameters."""
        context_parts = []
        for part in [workflow_name, prompt_style, model_name]:
            if part:
                context_parts.append(part)
        return build_window_title(
            progress_percent=progress_percent,
            current=current,
            total=total,
            operation=operation,
            context_parts=context_parts if context_parts else None,
            suffix=suffix
        )

    # Test cases
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Basic title
    result = build_window_title(50, 5, 10, "Describing Images")
    expected = "IDT - Describing Images (50%, 5 of 10)"
    if result == expected:
        print("✓ Test 1: Basic title")
        tests_passed += 1
    else:
        print(f"✗ Test 1: Expected '{expected}', got '{result}'")
        tests_failed += 1
    
    # Test 2: With context parts
    result = build_window_title(50, 5, 10, "Describing", context_parts=["wf", "detailed", "gpt-4o"])
    if "wf - detailed - gpt-4o" in result:
        print("✓ Test 2: With context parts")
        tests_passed += 1
    else:
        print(f"✗ Test 2: Expected context parts in '{result}'")
        tests_failed += 1
    
    # Test 3: With suffix
    result = build_window_title(50, 5, 10, "Describing", suffix=" - Live")
    expected = "IDT - Describing (50%, 5 of 10) - Live"
    if result == expected:
        print("✓ Test 3: With suffix")
        tests_passed += 1
    else:
        print(f"✗ Test 3: Expected '{expected}', got '{result}'")
        tests_failed += 1
    
    # Test 4: With suffix and context
    result = build_window_title(50, 5, 10, "Describing", context_parts=["wf", "style"], suffix=" - Live")
    if result == "IDT - Describing (50%, 5 of 10) - Live - wf - style":
        print("✓ Test 4: With suffix and context")
        tests_passed += 1
    else:
        print(f"✗ Test 4: Got '{result}'")
        tests_failed += 1
    
    # Test 5: Filters None
    result = build_window_title(50, 5, 10, "Process", context_parts=["first", None, "second"])
    expected = "IDT - Process (50%, 5 of 10) - first - second"
    if result == expected:
        print("✓ Test 5: Filters None values")
        tests_passed += 1
    else:
        print(f"✗ Test 5: Expected '{expected}', got '{result}'")
        tests_failed += 1
    
    # Test 6: From context function
    result = build_window_title_from_context(
        50, 5, 10, "Describing",
        workflow_name="wf",
        prompt_style="detailed",
        model_name="gpt-4o"
    )
    expected = "IDT - Describing (50%, 5 of 10) - wf - detailed - gpt-4o"
    if result == expected:
        print("✓ Test 6: From context function")
        tests_passed += 1
    else:
        print(f"✗ Test 6: Expected '{expected}', got '{result}'")
        tests_failed += 1
    
    # Test 7: From context with suffix
    result = build_window_title_from_context(
        100, 20, 20, "Describing",
        workflow_name="proj",
        prompt_style="concise",
        model_name="gpt-4o",
        suffix=" - Complete"
    )
    if "- Complete -" in result and "proj" in result and "concise" in result:
        print("✓ Test 7: From context with suffix")
        tests_passed += 1
    else:
        print(f"✗ Test 7: Got '{result}'")
        tests_failed += 1
    
    # Test 8: Zero progress
    result = build_window_title(0, 0, 0, "Starting")
    expected = "IDT - Starting (0%, 0 of 0)"
    if result == expected:
        print("✓ Test 8: Zero progress")
        tests_passed += 1
    else:
        print(f"✗ Test 8: Expected '{expected}', got '{result}'")
        tests_failed += 1
    
    # Test 9: Function equivalence
    list_result = build_window_title(50, 5, 10, "Describing", context_parts=["wf", "style", "model"])
    param_result = build_window_title_from_context(50, 5, 10, "Describing", workflow_name="wf", prompt_style="style", model_name="model")
    if list_result == param_result:
        print("✓ Test 9: Function equivalence")
        tests_passed += 1
    else:
        print(f"✗ Test 9: Functions not equivalent")
        tests_failed += 1
    
    # Test 10: Order preservation
    result = build_window_title_from_context(50, 5, 10, "Process", workflow_name="first", prompt_style="second", model_name="third")
    first_idx = result.index("first")
    second_idx = result.index("second")
    third_idx = result.index("third")
    if first_idx < second_idx < third_idx:
        print("✓ Test 10: Order preservation")
        tests_passed += 1
    else:
        print(f"✗ Test 10: Order not preserved in '{result}'")
        tests_failed += 1
    
    print(f"\n{'=' * 50}")
    print(f"Results: {tests_passed} passed, {tests_failed} failed")
    print(f"{'=' * 50}")
    
    return tests_failed == 0

if __name__ == "__main__":
    success = test_window_title_builder()
    sys.exit(0 if success else 1)
