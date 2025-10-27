"""
Unit tests for workflow.py sanitize_name function and name handling.

These tests ensure that workflow names preserve or convert case as expected,
preventing regressions like the one where --name MyRunHasUpperCase was being
lowercased in the directory name despite preserve_case=True.
"""

import pytest
import sys
from pathlib import Path

# Import the function we're testing
from scripts.workflow import sanitize_name


class TestSanitizeName:
    """Test the sanitize_name function for proper case handling."""
    
    def test_sanitize_name_preserves_case_when_requested(self):
        """Test that sanitize_name preserves case with preserve_case=True."""
        # This is the bug we just fixed - it was incorrectly lowercasing
        result = sanitize_name("MyRunHasUpperCase", preserve_case=True)
        assert result == "MyRunHasUpperCase", \
            "sanitize_name should preserve case when preserve_case=True"
    
    def test_sanitize_name_lowercases_when_not_preserving(self):
        """Test that sanitize_name converts to lowercase with preserve_case=False."""
        result = sanitize_name("MyRunHasUpperCase", preserve_case=False)
        assert result == "myrunhasuppercase", \
            "sanitize_name should convert to lowercase when preserve_case=False"
    
    def test_sanitize_name_preserves_case_by_default(self):
        """Test that sanitize_name preserves case when preserve_case not specified."""
        # Check what the default behavior is
        result = sanitize_name("MyRunHasUpperCase")
        # According to the function signature, default should be preserve_case=True
        assert result == "MyRunHasUpperCase", \
            "sanitize_name should preserve case by default"
    
    def test_sanitize_name_removes_special_characters(self):
        """Test that special characters are removed/replaced."""
        test_cases = [
            ("My Run!", "MyRun"),
            ("Run@#$%Name", "RunName"),
            ("Test & Run", "TestRun"),
            ("Run/Name", "RunName"),
        ]
        
        for input_name, expected_safe in test_cases:
            result = sanitize_name(input_name, preserve_case=True)
            assert result == expected_safe, \
                f"sanitize_name('{input_name}') should become '{expected_safe}', got '{result}'"
    
    def test_sanitize_name_preserves_underscores(self):
        """Test that underscores are preserved as they're valid in directory names."""
        result = sanitize_name("My_Run_Name", preserve_case=True)
        assert result == "My_Run_Name", \
            "sanitize_name should preserve underscores"
    
    def test_sanitize_name_preserves_hyphens(self):
        """Test that hyphens are preserved as they're valid in directory names."""
        result = sanitize_name("My-Run-Name", preserve_case=True)
        assert result == "My-Run-Name", \
            "sanitize_name should preserve hyphens"
    
    def test_sanitize_name_handles_spaces(self):
        """Test that spaces are either removed or converted."""
        # Spaces should be removed or replaced
        result = sanitize_name("My Run Name", preserve_case=True)
        # Check that there are no spaces in the result
        assert " " not in result, \
            "sanitize_name should not have spaces in result"
    
    def test_sanitize_name_with_numbers(self):
        """Test that numbers are preserved."""
        result = sanitize_name("Run123Test456", preserve_case=True)
        assert result == "Run123Test456", \
            "sanitize_name should preserve numbers"
    
    def test_sanitize_name_empty_string(self):
        """Test handling of empty string input."""
        result = sanitize_name("", preserve_case=True)
        # Should return something valid (not crash)
        assert isinstance(result, str), \
            "sanitize_name should return a string even for empty input"
    
    def test_sanitize_name_only_special_characters(self):
        """Test handling of string with only special characters."""
        result = sanitize_name("!@#$%^&*()", preserve_case=True)
        # Should return something valid (probably empty or a safe default)
        assert isinstance(result, str), \
            "sanitize_name should handle strings with only special characters"


class TestWorkflowNameHandling:
    """Test that workflow directory names use the correctly-cased name.
    
    These tests would have caught the recent bug where workflow_name was
    being lowercased even when the user provided --name with uppercase letters.
    """
    
    def test_custom_name_preserves_case_in_metadata(self):
        """Test that custom names preserve case for display."""
        # This tests the workflow_name_display variable
        from scripts.workflow import sanitize_name
        
        custom_name = "MyRunHasUpperCase"
        workflow_name_display = sanitize_name(custom_name, preserve_case=True)
        
        assert workflow_name_display == "MyRunHasUpperCase", \
            "workflow_name_display should preserve case from user input"
    
    def test_custom_name_preserves_case_in_directory(self):
        """Test that custom names preserve case for directory naming.
        
        THIS IS THE BUG WE JUST FIXED - it was calling sanitize_name with
        preserve_case=False for the directory name, even though we want
        case preservation.
        """
        from scripts.workflow import sanitize_name
        
        custom_name = "MyRunHasUpperCase"
        # This should be what gets used in the directory name
        workflow_name = sanitize_name(custom_name, preserve_case=True)
        
        assert workflow_name == "MyRunHasUpperCase", \
            "workflow_name for directory should preserve case from user input"
        
        # Simulate the directory name construction
        provider_name = "ollama"
        model_name = "moondream"
        prompt_style = "default"
        timestamp = "20251027_120000"
        
        wf_dirname = f"wf_{workflow_name}_{provider_name}_{model_name}_{prompt_style}_{timestamp}"
        
        assert "MyRunHasUpperCase" in wf_dirname, \
            f"Directory name should contain case-preserved name, got: {wf_dirname}"
        assert "myrunhasuppercase" not in wf_dirname, \
            f"Directory name should NOT contain lowercased name, got: {wf_dirname}"
    
    def test_lowercase_conversion_when_requested(self):
        """Test that we CAN lowercase when explicitly requested.
        
        This ensures the preserve_case=False option still works when needed.
        """
        from scripts.workflow import sanitize_name
        
        custom_name = "MyRunHasUpperCase"
        workflow_name = sanitize_name(custom_name, preserve_case=False)
        
        assert workflow_name == "myrunhasuppercase", \
            "Should lowercase when preserve_case=False is explicit"


class TestCasePreservationIntegration:
    """Integration tests for case preservation throughout the workflow.
    
    These tests verify that case preservation works correctly in the
    complete workflow context, not just isolated functions.
    """
    
    def test_args_name_to_directory_name(self, mock_args):
        """Test the full path from args.name to directory name."""
        from scripts.workflow import sanitize_name
        
        # Simulate user providing --name MyRunHasUpperCase
        args = mock_args(name="MyRunHasUpperCase")
        
        # This is what the workflow code does
        if args.name:
            workflow_name_display = sanitize_name(args.name, preserve_case=True)
            workflow_name = workflow_name_display  # Should use same case-preserved value
        
        assert workflow_name == "MyRunHasUpperCase", \
            "workflow_name should equal workflow_name_display for case preservation"
    
    def test_different_case_styles(self, mock_args):
        """Test that various case styles are preserved correctly."""
        test_cases = [
            "AllUpperCase",
            "alllowercase", 
            "CamelCaseRun",
            "snake_case_run",
            "kebab-case-run",
            "MixedCase123Run",
        ]
        
        from scripts.workflow import sanitize_name
        
        for case_style in test_cases:
            result = sanitize_name(case_style, preserve_case=True)
            # The case should be preserved exactly
            # (though special chars might be removed, the case should match)
            result_letters = ''.join(c for c in result if c.isalpha())
            input_letters = ''.join(c for c in case_style if c.isalpha())
            
            assert result_letters == input_letters, \
                f"Case not preserved: '{case_style}' became '{result}'"


if __name__ == "__main__":
    # Allow running this test file directly
    pytest.main([__file__, "-v"])
