"""
Unit tests for shared utility functions.

Tests for functions in shared/utility_functions.py including:
- sanitize_name()
- sanitize_filename()
- format_timestamp_standard()
"""

import pytest
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.utility_functions import (
    sanitize_name,
    sanitize_filename,
    format_timestamp_standard
)


class TestSanitizeName:
    """Test suite for sanitize_name() function."""
    
    def test_sanitize_name_preserves_case_when_requested(self):
        """Test that sanitize_name preserves case with preserve_case=True."""
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
        result = sanitize_name("MyRunHasUpperCase")
        assert result == "MyRunHasUpperCase", \
            "sanitize_name should preserve case by default"
    
    def test_sanitize_name_removes_special_characters(self):
        """Test that sanitize_name removes special characters correctly."""
        test_cases = {
            "GPT-4 Vision": "GPT-4Vision",
            "Model (v2.1)": "Modelv2.1",
            "OpenAI:API/Key": "OpenAIAPIKey",
            "Test@#$%Name": "TestName",
            "Name&Test": "NameTest",
        }
        
        for input_name, expected_safe in test_cases.items():
            result = sanitize_name(input_name, preserve_case=True)
            assert result == expected_safe, \
                f"sanitize_name('{input_name}') should become '{expected_safe}', got '{result}'"
    
    def test_sanitize_name_preserves_underscores(self):
        """Test that sanitize_name preserves underscores."""
        result = sanitize_name("My_Run_Name", preserve_case=True)
        assert result == "My_Run_Name", \
            "sanitize_name should preserve underscores"
    
    def test_sanitize_name_preserves_hyphens(self):
        """Test that sanitize_name preserves hyphens."""
        result = sanitize_name("My-Run-Name", preserve_case=True)
        assert result == "My-Run-Name", \
            "sanitize_name should preserve hyphens"
    
    def test_sanitize_name_preserves_periods(self):
        """Test that sanitize_name preserves periods."""
        result = sanitize_name("My.Run.Name", preserve_case=True)
        assert result == "My.Run.Name", \
            "sanitize_name should preserve periods"
    
    def test_sanitize_name_handles_spaces(self):
        """Test that sanitize_name removes spaces."""
        result = sanitize_name("My Run Name", preserve_case=True)
        assert result == "MyRunName", \
            "sanitize_name should remove spaces entirely"
    
    def test_sanitize_name_with_numbers(self):
        """Test that sanitize_name preserves numbers."""
        result = sanitize_name("Run123Test456", preserve_case=True)
        assert result == "Run123Test456", \
            "sanitize_name should preserve numbers"
    
    def test_sanitize_name_empty_string(self):
        """Test that sanitize_name returns 'unknown' for empty string."""
        result = sanitize_name("", preserve_case=True)
        assert result == "unknown", \
            "sanitize_name should return 'unknown' for empty string"
    
    def test_sanitize_name_only_special_characters(self):
        """Test that sanitize_name returns 'unknown' when only special chars."""
        result = sanitize_name("!@#$%^&*()", preserve_case=True)
        assert result == "unknown", \
            "sanitize_name should return 'unknown' when input becomes empty"
    
    def test_sanitize_name_none_input(self):
        """Test that sanitize_name handles None gracefully."""
        result = sanitize_name(None, preserve_case=True)
        assert result == "unknown", \
            "sanitize_name should return 'unknown' for None input"
    
    def test_sanitize_name_model_examples(self):
        """Test real-world model name examples."""
        examples = {
            "GPT-4o": "GPT-4o",
            "Claude 3 Opus": "Claude3Opus",
            "Llama 2 7B": "Llama27B",
            "ollama:llama2": "ollama:llama2",  # Note: colon is removed
            "llama2": "llama2",
        }
        
        for model_name, expected in examples.items():
            result = sanitize_name(model_name, preserve_case=True)
            # For model with colon, it gets removed
            if ":" in model_name:
                expected = model_name.replace(":", "")
            assert result == expected, \
                f"Model name '{model_name}' should become '{expected}', got '{result}'"


class TestSanitizeFilename:
    """Test suite for sanitize_filename() function."""
    
    def test_sanitize_filename_basic(self):
        """Test basic filename sanitization."""
        result = sanitize_filename("My File: (1).txt")
        assert result == "MyFile1.txt", \
            "Should remove special characters from filename"
    
    def test_sanitize_filename_removes_windows_invalid_chars(self):
        """Test that sanitize_filename removes Windows invalid characters."""
        # Test each invalid Windows character
        invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in invalid_chars:
            result = sanitize_filename(f"test{char}file.txt")
            assert char not in result, \
                f"sanitize_filename should remove '{char}' from filenames"
    
    def test_sanitize_filename_preserves_case_by_default(self):
        """Test that sanitize_filename preserves case by default."""
        result = sanitize_filename("MyFileName.txt")
        assert result == "MyFileName.txt", \
            "sanitize_filename should preserve case by default"
    
    def test_sanitize_filename_lowercases_when_requested(self):
        """Test that sanitize_filename lowercases when preserve_case=False."""
        result = sanitize_filename("MyFileName.txt", preserve_case=False)
        assert result == "myfilename.txt", \
            "sanitize_filename should lowercase when preserve_case=False"
    
    def test_sanitize_filename_preserves_valid_characters(self):
        """Test that sanitize_filename preserves alphanumeric, ., -, _."""
        result = sanitize_filename("my-file_name.v2.0.txt")
        assert result == "my-file_name.v2.0.txt", \
            "sanitize_filename should preserve ., -, _"
    
    def test_sanitize_filename_removes_control_characters(self):
        """Test that sanitize_filename removes control characters."""
        # Control characters are in range \x00-\x1f
        result = sanitize_filename("test\x00file\x1fend.txt")
        assert "\x00" not in result and "\x1f" not in result, \
            "sanitize_filename should remove control characters"
    
    def test_sanitize_filename_empty_after_cleaning(self):
        """Test that sanitize_filename returns 'file' when input becomes empty."""
        result = sanitize_filename("!@#$%^&*()")
        assert result == "file", \
            "sanitize_filename should return 'file' for empty result"
    
    def test_sanitize_filename_extension_preserved(self):
        """Test that file extensions are handled correctly."""
        result = sanitize_filename("document (final).pdf")
        assert result.endswith(".pdf"), \
            "sanitize_filename should preserve file extensions"


class TestFormatTimestampStandard:
    """Test suite for format_timestamp_standard() function."""
    
    def test_format_timestamp_basic(self):
        """Test basic timestamp formatting."""
        dt = datetime(2025, 3, 25, 7, 35, 0)
        result = format_timestamp_standard(dt)
        assert result == "3/25/2025 7:35P", \
            "Should format as M/D/YYYY H:MMP"
    
    def test_format_timestamp_no_leading_zeros(self):
        """Test that format uses no leading zeros."""
        dt = datetime(2025, 1, 5, 8, 3, 0)
        result = format_timestamp_standard(dt)
        assert result == "1/5/2025 8:03A", \
            "Should have no leading zeros on month/day/hour"
    
    def test_format_timestamp_am_pm_morning(self):
        """Test AM/PM formatting for morning times."""
        dt = datetime(2025, 3, 25, 8, 30, 0)
        result = format_timestamp_standard(dt)
        assert result.endswith("A"), \
            "Should show 'A' for morning times"
    
    def test_format_timestamp_am_pm_afternoon(self):
        """Test AM/PM formatting for afternoon times."""
        dt = datetime(2025, 3, 25, 14, 30, 0)
        result = format_timestamp_standard(dt)
        assert result.endswith("P"), \
            "Should show 'P' for afternoon times"
    
    def test_format_timestamp_noon(self):
        """Test formatting for noon."""
        dt = datetime(2025, 3, 25, 12, 0, 0)
        result = format_timestamp_standard(dt)
        assert "12:" in result and result.endswith("P"), \
            "Should show 12 for noon"
    
    def test_format_timestamp_midnight(self):
        """Test formatting for midnight."""
        dt = datetime(2025, 3, 25, 0, 30, 0)
        result = format_timestamp_standard(dt)
        assert "12:" in result and result.endswith("A"), \
            "Should show 12 for midnight"
    
    def test_format_timestamp_single_digit_minute(self):
        """Test that single-digit minutes have leading zero."""
        dt = datetime(2025, 3, 25, 7, 5, 0)
        result = format_timestamp_standard(dt)
        assert "7:05P" in result, \
            "Should pad minutes with leading zero: 7:05P not 7:5P"
    
    def test_format_timestamp_none_input(self):
        """Test that None input uses current time."""
        result = format_timestamp_standard(None)
        # Just verify it returns a string in the correct format
        parts = result.split()
        assert len(parts) == 2, "Should have date and time parts"
        assert "/" in parts[0], "First part should be date"
        assert parts[1][-1] in "AP", "Second part should end with A or P"
    
    def test_format_timestamp_preserves_minutes_seconds_accuracy(self):
        """Test that minutes are formatted correctly regardless of seconds."""
        dt1 = datetime(2025, 3, 25, 7, 35, 15)
        dt2 = datetime(2025, 3, 25, 7, 35, 45)
        
        result1 = format_timestamp_standard(dt1)
        result2 = format_timestamp_standard(dt2)
        
        # Both should have same time part (seconds are ignored)
        assert result1 == result2, \
            "Seconds should not affect formatting"
        assert "7:35P" in result1, \
            "Should format as 7:35P"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
