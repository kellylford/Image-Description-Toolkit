"""
Standalone tests for shared/window_title_builder.py

Run with: python test_window_title_builder_standalone.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.window_title_builder import build_window_title, build_window_title_from_context


def test_basic_title():
    """Test basic title without context"""
    result = build_window_title(50, 5, 10, "Describing Images")
    expected = "IDT - Describing Images (50%, 5 of 10)"
    assert result == expected, f"Expected '{expected}', got '{result}'"
    print("✓ test_basic_title")


def test_with_context_parts():
    """Test with multiple context parts"""
    result = build_window_title(
        50, 5, 10, "Describing",
        context_parts=["my_workflow", "detailed", "gpt-4o"]
    )
    expected = "IDT - Describing (50%, 5 of 10) - my_workflow - detailed - gpt-4o"
    assert result == expected, f"Expected '{expected}', got '{result}'"
    print("✓ test_with_context_parts")


def test_with_suffix():
    """Test with suffix"""
    result = build_window_title(50, 5, 10, "Describing", suffix=" - Live")
    expected = "IDT - Describing (50%, 5 of 10) - Live"
    assert result == expected, f"Expected '{expected}', got '{result}'"
    print("✓ test_with_suffix")


def test_with_suffix_and_context():
    """Test with both suffix and context"""
    result = build_window_title(
        50, 5, 10, "Describing",
        context_parts=["wf", "detailed"],
        suffix=" - Live"
    )
    expected = "IDT - Describing (50%, 5 of 10) - Live - wf - detailed"
    assert result == expected, f"Expected '{expected}', got '{result}'"
    print("✓ test_with_suffix_and_context")


def test_filters_none_values():
    """Test that None values in context are filtered"""
    result = build_window_title(
        50, 5, 10, "Process",
        context_parts=["first", None, "second"]
    )
    expected = "IDT - Process (50%, 5 of 10) - first - second"
    assert result == expected, f"Expected '{expected}', got '{result}'"
    print("✓ test_filters_none_values")


def test_filters_empty_strings():
    """Test that empty strings in context are filtered"""
    result = build_window_title(
        50, 5, 10, "Process",
        context_parts=["first", "", "second"]
    )
    expected = "IDT - Process (50%, 5 of 10) - first - second"
    assert result == expected, f"Expected '{expected}', got '{result}'"
    print("✓ test_filters_empty_strings")


def test_from_context_all_params():
    """Test build_window_title_from_context with all parameters"""
    result = build_window_title_from_context(
        50, 5, 10, "Describing",
        workflow_name="my_workflow",
        prompt_style="detailed",
        model_name="gpt-4o"
    )
    expected = "IDT - Describing (50%, 5 of 10) - my_workflow - detailed - gpt-4o"
    assert result == expected, f"Expected '{expected}', got '{result}'"
    print("✓ test_from_context_all_params")


def test_from_context_with_suffix():
    """Test build_window_title_from_context with suffix"""
    result = build_window_title_from_context(
        100, 20, 20, "Describing",
        workflow_name="project_a",
        prompt_style="concise",
        model_name="gpt-4o",
        suffix=" - Complete"
    )
    expected = "IDT - Describing (100%, 20 of 20) - Complete - project_a - concise - gpt-4o"
    assert result == expected, f"Expected '{expected}', got '{result}'"
    print("✓ test_from_context_with_suffix")


def test_from_context_filters_none():
    """Test that build_window_title_from_context filters None values"""
    result = build_window_title_from_context(
        50, 5, 10, "Processing",
        workflow_name="wf_test",
        prompt_style=None,
        model_name="claude-3"
    )
    expected = "IDT - Processing (50%, 5 of 10) - wf_test - claude-3"
    assert result == expected, f"Expected '{expected}', got '{result}'"
    print("✓ test_from_context_filters_none")


def test_context_order_preserved():
    """Test that context parts appear in correct order"""
    result = build_window_title_from_context(
        50, 5, 10, "Process",
        workflow_name="first",
        prompt_style="second",
        model_name="third"
    )
    first_idx = result.index("first")
    second_idx = result.index("second")
    third_idx = result.index("third")
    assert first_idx < second_idx < third_idx, f"Order not preserved in: {result}"
    print("✓ test_context_order_preserved")


def test_large_numbers():
    """Test with large numbers"""
    result = build_window_title(99, 1000000, 1000000, "Processing")
    assert "99%, 1000000 of 1000000" in result
    print("✓ test_large_numbers")


def test_zero_progress():
    """Test with zero progress"""
    result = build_window_title(0, 0, 0, "Starting")
    expected = "IDT - Starting (0%, 0 of 0)"
    assert result == expected, f"Expected '{expected}', got '{result}'"
    print("✓ test_zero_progress")


def test_equivalence_of_functions():
    """Test that both functions produce equivalent results"""
    list_result = build_window_title(
        50, 5, 10, "Describing",
        context_parts=["wf", "style", "model"]
    )
    
    param_result = build_window_title_from_context(
        50, 5, 10, "Describing",
        workflow_name="wf",
        prompt_style="style",
        model_name="model"
    )
    
    assert list_result == param_result, f"Functions not equivalent:\n  list: {list_result}\n  param: {param_result}"
    print("✓ test_equivalence_of_functions")


def test_whitespace_stripping():
    """Test that whitespace in context is stripped"""
    result = build_window_title_from_context(
        50, 5, 10, "Process",
        workflow_name="  wf_test  ",
        prompt_style="  detailed  ",
        model_name="  gpt-4o  "
    )
    assert "wf_test - detailed - gpt-4o" in result
    assert "  " not in result.split("(100%,")[1] if "100%," in result else True
    print("✓ test_whitespace_stripping")


def run_all_tests():
    """Run all standalone tests"""
    tests = [
        test_basic_title,
        test_with_context_parts,
        test_with_suffix,
        test_with_suffix_and_context,
        test_filters_none_values,
        test_filters_empty_strings,
        test_from_context_all_params,
        test_from_context_with_suffix,
        test_from_context_filters_none,
        test_context_order_preserved,
        test_large_numbers,
        test_zero_progress,
        test_equivalence_of_functions,
        test_whitespace_stripping,
    ]
    
    print("Running Window Title Builder Tests")
    print("=" * 50)
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test_func.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test_func.__name__}: {type(e).__name__}: {e}")
            failed += 1
    
    print("=" * 50)
    print(f"Results: {passed} passed, {failed} failed")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
