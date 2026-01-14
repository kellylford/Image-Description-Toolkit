"""
Unit Tests for shared/window_title_builder.py

Tests comprehensive window title building functionality including:
- Basic title formatting
- Progress percentage and counts
- Context parts ordering and filtering
- Empty/None value handling
- Optional suffix handling
- Both function variants (list-based and parameter-based)
"""

import pytest
from shared.window_title_builder import build_window_title, build_window_title_from_context


class TestBuildWindowTitle:
    """Tests for build_window_title() function"""

    def test_basic_title_no_context(self):
        """Test basic title without context or suffix"""
        title = build_window_title(50, 5, 10, "Describing Images")
        assert title == "IDT - Describing Images (50%, 5 of 10)"

    def test_zero_progress(self):
        """Test title with zero progress"""
        title = build_window_title(0, 0, 0, "Starting Process")
        assert title == "IDT - Starting Process (0%, 0 of 0)"

    def test_complete_progress(self):
        """Test title with 100% progress"""
        title = build_window_title(100, 50, 50, "Complete")
        assert title == "IDT - Complete (100%, 50 of 50)"

    def test_partial_progress(self):
        """Test title with various progress percentages"""
        assert "75%, 3 of 4" in build_window_title(75, 3, 4, "Processing")
        assert "33%, 1 of 3" in build_window_title(33, 1, 3, "Processing")

    def test_with_single_context(self):
        """Test title with single context part"""
        title = build_window_title(50, 5, 10, "Describing", context_parts=["my_workflow"])
        assert title == "IDT - Describing (50%, 5 of 10) - my_workflow"

    def test_with_multiple_context_parts(self):
        """Test title with multiple context parts"""
        title = build_window_title(
            50, 5, 10, "Describing",
            context_parts=["my_workflow", "detailed", "gpt-4o"]
        )
        assert title == "IDT - Describing (50%, 5 of 10) - my_workflow - detailed - gpt-4o"

    def test_context_parts_preserves_order(self):
        """Test that context parts are joined in provided order"""
        parts = ["first", "second", "third", "fourth"]
        title = build_window_title(0, 0, 0, "Test", context_parts=parts)
        assert " - first - second - third - fourth" in title

    def test_with_suffix_no_context(self):
        """Test title with suffix but no context"""
        title = build_window_title(50, 5, 10, "Describing", suffix=" - Live")
        assert title == "IDT - Describing (50%, 5 of 10) - Live"

    def test_with_suffix_and_context(self):
        """Test title with both suffix and context"""
        title = build_window_title(
            50, 5, 10, "Describing",
            context_parts=["wf", "detailed"],
            suffix=" - Live"
        )
        assert title == "IDT - Describing (50%, 5 of 10) - Live - wf - detailed"

    def test_suffix_appears_before_context(self):
        """Test that suffix appears before context parts in title"""
        title = build_window_title(
            50, 5, 10, "Process",
            context_parts=["ctx"],
            suffix=" - Status"
        )
        # Suffix should come after progress but before context
        assert title.index("- Status") < title.index("- ctx")

    def test_empty_context_parts_list(self):
        """Test with empty context parts list"""
        title = build_window_title(50, 5, 10, "Process", context_parts=[])
        assert title == "IDT - Process (50%, 5 of 10)"

    def test_none_context_parts(self):
        """Test with None context parts"""
        title = build_window_title(50, 5, 10, "Process", context_parts=None)
        assert title == "IDT - Process (50%, 5 of 10)"

    def test_context_parts_with_none_values(self):
        """Test context parts list containing None values"""
        title = build_window_title(
            50, 5, 10, "Process",
            context_parts=["first", None, "second", None]
        )
        assert title == "IDT - Process (50%, 5 of 10) - first - second"

    def test_context_parts_with_empty_strings(self):
        """Test context parts list containing empty strings"""
        title = build_window_title(
            50, 5, 10, "Process",
            context_parts=["first", "", "second", ""]
        )
        assert title == "IDT - Process (50%, 5 of 10) - first - second"

    def test_context_parts_with_whitespace(self):
        """Test context parts with whitespace"""
        title = build_window_title(
            50, 5, 10, "Process",
            context_parts=["  first  ", "  second  "]
        )
        assert title == "IDT - Process (50%, 5 of 10) - first - second"

    def test_context_parts_all_none_or_empty(self):
        """Test context parts that are all None or empty after filtering"""
        title = build_window_title(
            50, 5, 10, "Process",
            context_parts=[None, "", None, ""]
        )
        # Should not add context separator if no valid parts
        assert title == "IDT - Process (50%, 5 of 10)"

    def test_large_numbers(self):
        """Test with large progress numbers"""
        title = build_window_title(99, 1000000, 1000000, "Processing")
        assert "99%, 1000000 of 1000000" in title

    def test_operation_with_special_characters(self):
        """Test operation string with various characters"""
        title = build_window_title(50, 5, 10, "Extract & Convert (Advanced)")
        assert "Extract & Convert (Advanced)" in title

    def test_context_with_special_characters(self):
        """Test context parts containing special characters"""
        title = build_window_title(
            50, 5, 10, "Process",
            context_parts=["model-v2", "style/advanced", "wf_2025-01-14"]
        )
        assert "model-v2 - style/advanced - wf_2025-01-14" in title

    def test_suffix_with_multiple_dashes(self):
        """Test suffix with multiple dash segments"""
        title = build_window_title(50, 5, 10, "Process", suffix=" - Step 1 - Validating")
        assert title == "IDT - Process (50%, 5 of 10) - Step 1 - Validating"

    def test_context_integers_converted_to_strings(self):
        """Test that integer context parts are converted to strings"""
        # If someone passes integers, they should be converted
        title = build_window_title(
            50, 5, 10, "Process",
            context_parts=["batch", 1, "of", 5]  # type: ignore
        )
        assert "batch - 1 - of - 5" in title


class TestBuildWindowTitleFromContext:
    """Tests for build_window_title_from_context() function"""

    def test_basic_title_no_context(self):
        """Test basic title with minimal parameters"""
        title = build_window_title_from_context(50, 5, 10, "Describing")
        assert title == "IDT - Describing (50%, 5 of 10)"

    def test_all_context_parameters(self):
        """Test with all context parameters provided"""
        title = build_window_title_from_context(
            50, 5, 10, "Describing",
            workflow_name="my_workflow",
            prompt_style="detailed",
            model_name="gpt-4o"
        )
        assert title == "IDT - Describing (50%, 5 of 10) - my_workflow - detailed - gpt-4o"

    def test_workflow_name_only(self):
        """Test with only workflow name"""
        title = build_window_title_from_context(
            50, 5, 10, "Describing",
            workflow_name="my_workflow"
        )
        assert title == "IDT - Describing (50%, 5 of 10) - my_workflow"

    def test_prompt_style_only(self):
        """Test with only prompt style"""
        title = build_window_title_from_context(
            50, 5, 10, "Describing",
            prompt_style="detailed"
        )
        assert title == "IDT - Describing (50%, 5 of 10) - detailed"

    def test_model_name_only(self):
        """Test with only model name"""
        title = build_window_title_from_context(
            50, 5, 10, "Describing",
            model_name="gpt-4o"
        )
        assert title == "IDT - Describing (50%, 5 of 10) - gpt-4o"

    def test_workflow_and_model(self):
        """Test with workflow name and model only"""
        title = build_window_title_from_context(
            50, 5, 10, "Describing",
            workflow_name="wf_test",
            model_name="claude-3"
        )
        assert title == "IDT - Describing (50%, 5 of 10) - wf_test - claude-3"

    def test_with_suffix_and_all_context(self):
        """Test with suffix and all context parameters"""
        title = build_window_title_from_context(
            100, 20, 20, "Describing",
            workflow_name="project_a",
            prompt_style="concise",
            model_name="gpt-4o",
            suffix=" - Complete"
        )
        assert title == "IDT - Describing (100%, 20 of 20) - Complete - project_a - concise - gpt-4o"

    def test_none_context_parameters(self):
        """Test with None context parameters"""
        title = build_window_title_from_context(
            50, 5, 10, "Processing",
            workflow_name=None,
            prompt_style=None,
            model_name=None
        )
        assert title == "IDT - Processing (50%, 5 of 10)"

    def test_empty_string_context_parameters(self):
        """Test with empty string context parameters"""
        title = build_window_title_from_context(
            50, 5, 10, "Processing",
            workflow_name="",
            prompt_style="",
            model_name=""
        )
        assert title == "IDT - Processing (50%, 5 of 10)"

    def test_mixed_none_and_values(self):
        """Test with mix of None and actual context values"""
        title = build_window_title_from_context(
            50, 5, 10, "Processing",
            workflow_name="wf_test",
            prompt_style=None,
            model_name="claude-3"
        )
        assert title == "IDT - Processing (50%, 5 of 10) - wf_test - claude-3"

    def test_order_preservation(self):
        """Test that context parameters appear in correct order"""
        title = build_window_title_from_context(
            50, 5, 10, "Process",
            workflow_name="first",
            prompt_style="second",
            model_name="third"
        )
        # Check order: workflow, prompt_style, model_name
        first_idx = title.index("first")
        second_idx = title.index("second")
        third_idx = title.index("third")
        assert first_idx < second_idx < third_idx

    def test_large_numbers_with_context(self):
        """Test with large numbers and full context"""
        title = build_window_title_from_context(
            100, 10000, 10000, "Processing",
            workflow_name="large_batch",
            prompt_style="comprehensive",
            model_name="gpt-4-turbo"
        )
        assert "100%, 10000 of 10000" in title
        assert "large_batch" in title
        assert "comprehensive" in title
        assert "gpt-4-turbo" in title

    def test_special_characters_in_context(self):
        """Test special characters in context parameters"""
        title = build_window_title_from_context(
            50, 5, 10, "Process",
            workflow_name="wf_2025-01-14_test",
            prompt_style="style/advanced",
            model_name="claude-3-opus"
        )
        assert "wf_2025-01-14_test" in title
        assert "style/advanced" in title
        assert "claude-3-opus" in title

    def test_whitespace_in_context(self):
        """Test context parameters with leading/trailing whitespace"""
        title = build_window_title_from_context(
            50, 5, 10, "Process",
            workflow_name="  wf_test  ",
            prompt_style="  detailed  ",
            model_name="  gpt-4o  "
        )
        # Whitespace should be stripped
        assert "wf_test - detailed - gpt-4o" in title

    def test_suffix_placement(self):
        """Test that suffix appears in correct position"""
        title = build_window_title_from_context(
            75, 15, 20, "Processing",
            workflow_name="test",
            model_name="gpt-4",
            suffix=" - In Progress"
        )
        # Verify order: progress, suffix, then context
        progress_idx = title.index("75%")
        suffix_idx = title.index("In Progress")
        context_idx = title.index("test")
        assert progress_idx < suffix_idx < context_idx


class TestEdgeCases:
    """Tests for edge cases and special scenarios"""

    def test_very_long_operation_name(self):
        """Test with very long operation name"""
        long_op = "Very Long Operation Name With Many Words And Descriptions"
        title = build_window_title(50, 5, 10, long_op)
        assert long_op in title

    def test_very_long_context_parts(self):
        """Test with very long context part strings"""
        long_parts = ["this_is_a_very_long_workflow_name_with_many_segments", "another_very_long_part"]
        title = build_window_title(50, 5, 10, "Process", context_parts=long_parts)
        assert "this_is_a_very_long_workflow_name_with_many_segments" in title
        assert "another_very_long_part" in title

    def test_many_context_parts(self):
        """Test with many context parts"""
        many_parts = [f"part_{i}" for i in range(10)]
        title = build_window_title(50, 5, 10, "Process", context_parts=many_parts)
        for part in many_parts:
            assert part in title

    def test_unicode_in_context(self):
        """Test unicode characters in context"""
        title = build_window_title(
            50, 5, 10, "Process",
            context_parts=["workflow_🎯", "model_📊"]
        )
        assert "workflow_🎯" in title
        assert "model_📊" in title

    def test_both_functions_equivalent_results(self):
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
        
        assert list_result == param_result

    def test_consistency_across_calls(self):
        """Test that same parameters produce same results"""
        params = (50, 5, 10, "Process", ["ctx1", "ctx2"], " - Suffix")
        title1 = build_window_title(*params)
        title2 = build_window_title(*params)
        assert title1 == title2
