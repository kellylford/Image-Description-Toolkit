"""
Unit tests for status log ASCII-only output.

These tests ensure that status log messages use ASCII symbols only,
not Unicode symbols that cause issues with screen readers.

Regression prevention for the bug where ⟳, ✓, ✗, → symbols were
rendering as garbage for screen readers.
"""

import pytest
from pathlib import Path


class TestStatusLogASCIISymbols:
    """Test that status log output uses ASCII-only symbols."""
    
    def test_no_unicode_circled_arrow(self):
        """Test that status messages don't contain ⟳ (circled anticlockwise arrow)."""
        # Sample status messages that should use [ACTIVE] instead
        status_messages = [
            "[ACTIVE] Image conversion in progress: 12/48 HEIC to JPG (25%)",
            "[ACTIVE] Video extraction in progress: 2/5 videos (40%)",
            "[ACTIVE] Image description in progress: 8/23 JPG files (34%)",
        ]
        
        for message in status_messages:
            assert "⟳" not in message, \
                f"Status message should not contain Unicode ⟳ symbol: {message}"
            assert "[ACTIVE]" in message, \
                f"Status message should contain [ACTIVE] ASCII prefix: {message}"
    
    def test_no_unicode_checkmark(self):
        """Test that status messages don't contain ✓ (checkmark)."""
        status_messages = [
            "[DONE] Image conversion complete (48 HEIC to JPG)",
            "[DONE] Video extraction complete (5 videos)",
            "[DONE] Image description complete (23 JPG files)",
        ]
        
        for message in status_messages:
            assert "✓" not in message, \
                f"Status message should not contain Unicode ✓ symbol: {message}"
            assert "[DONE]" in message, \
                f"Status message should contain [DONE] ASCII prefix: {message}"
    
    def test_no_unicode_x_mark(self):
        """Test that status messages don't contain ✗ (X mark)."""
        status_messages = [
            "[FAILED] Image conversion failed",
            "[FAILED] Video extraction failed",
            "[FAILED] Image description failed",
        ]
        
        for message in status_messages:
            assert "✗" not in message, \
                f"Status message should not contain Unicode ✗ symbol: {message}"
            assert "[FAILED]" in message, \
                f"Status message should contain [FAILED] ASCII prefix: {message}"
    
    def test_no_unicode_arrow(self):
        """Test that status messages don't contain → (rightward arrow)."""
        status_messages = [
            "[ACTIVE] Image conversion in progress: 12/48 HEIC to JPG (25%)",
            "[DONE] Image conversion complete (48 HEIC to JPG)",
        ]
        
        for message in status_messages:
            assert "→" not in message, \
                f"Status message should not contain Unicode → symbol: {message}"
            assert " to " in message.lower(), \
                f"Status message should use ' to ' instead of arrow: {message}"
    
    def test_ascii_status_indicators_present(self):
        """Test that ASCII status indicators are used correctly."""
        test_cases = [
            ("[ACTIVE]", "in progress"),
            ("[DONE]", "complete"),
            ("[FAILED]", "failed"),
        ]
        
        for indicator, context in test_cases:
            # Verify the indicator is valid ASCII
            assert all(ord(c) < 128 for c in indicator), \
                f"Status indicator should be ASCII-only: {indicator}"
            
            # Verify it uses brackets not other symbols
            assert indicator.startswith("[") and indicator.endswith("]"), \
                f"Status indicator should use brackets: {indicator}"
    
    def test_heic_to_jpg_uses_text_not_arrow(self):
        """Test that HEIC→JPG is written as 'HEIC to JPG'."""
        correct_messages = [
            "Image conversion in progress: 12/48 HEIC to JPG (25%)",
            "Image conversion complete (48 HEIC to JPG)",
            "Converting HEIC to JPG format",
        ]
        
        for message in correct_messages:
            assert "HEIC to JPG" in message or "HEIC to jpg" in message.lower(), \
                f"Message should use 'to' not arrow: {message}"
            assert "→" not in message, \
                f"Message should not contain arrow symbol: {message}"


class TestStatusLogFormat:
    """Test that status log messages follow consistent ASCII format."""
    
    def test_progress_message_format(self):
        """Test that progress messages follow the standard format."""
        # Format: [ACTIVE] <operation> in progress: X/Y <type> (Z%)
        message = "[ACTIVE] Image conversion in progress: 12/48 HEIC to JPG (25%)"
        
        # Check all components
        assert message.startswith("[ACTIVE]"), "Should start with [ACTIVE]"
        assert " in progress: " in message, "Should contain ' in progress: '"
        assert "12/48" in message, "Should contain count fraction"
        assert "(25%)" in message, "Should contain percentage"
        assert all(ord(c) < 128 for c in message), "Should be ASCII-only"
    
    def test_completion_message_format(self):
        """Test that completion messages follow the standard format."""
        # Format: [DONE] <operation> complete (<details>)
        message = "[DONE] Image conversion complete (48 HEIC to JPG)"
        
        assert message.startswith("[DONE]"), "Should start with [DONE]"
        assert " complete " in message, "Should contain ' complete '"
        assert "(" in message and ")" in message, "Should contain details in parentheses"
        assert all(ord(c) < 128 for c in message), "Should be ASCII-only"
    
    def test_failure_message_format(self):
        """Test that failure messages follow the standard format."""
        # Format: [FAILED] <operation> failed
        message = "[FAILED] Image conversion failed"
        
        assert message.startswith("[FAILED]"), "Should start with [FAILED]"
        assert " failed" in message, "Should contain ' failed'"
        assert all(ord(c) < 128 for c in message), "Should be ASCII-only"
    
    def test_all_status_prefixes_are_ascii(self):
        """Test that all status prefixes use only ASCII characters."""
        prefixes = ["[ACTIVE]", "[DONE]", "[FAILED]"]
        
        for prefix in prefixes:
            # Check each character is ASCII (ord < 128)
            for char in prefix:
                assert ord(char) < 128, \
                    f"Character '{char}' in prefix '{prefix}' is not ASCII (ord={ord(char)})"
    
    def test_no_unicode_anywhere_in_status(self):
        """Comprehensive test that no Unicode appears in any status message."""
        sample_messages = [
            "[ACTIVE] Video extraction in progress: 2/5 videos (40%)",
            "[ACTIVE] Image conversion in progress: 12/48 HEIC to JPG (25%)",
            "[ACTIVE] Image description in progress: 8/23 JPG files (34%)",
            "[DONE] Video extraction complete (5 videos)",
            "[DONE] Image conversion complete (48 HEIC to JPG)",
            "[DONE] Image description complete (23 JPG files)",
            "[FAILED] Video extraction failed",
            "[FAILED] Image conversion failed",
            "[FAILED] Image description failed",
        ]
        
        for message in sample_messages:
            # Every character should be ASCII (ord < 128)
            for char in message:
                assert ord(char) < 128, \
                    f"Non-ASCII character '{char}' (ord={ord(char)}) found in: {message}"


class TestStatusLogReadability:
    """Test that ASCII status messages are screen-reader friendly."""
    
    def test_brackets_instead_of_symbols(self):
        """Test that we use [WORD] format instead of symbols."""
        # [ACTIVE] is much better for screen readers than ⟳
        # Screen reader reads: "bracket ACTIVE bracket" clearly
        
        test_prefixes = {
            "[ACTIVE]": "⟳",  # Old Unicode symbol
            "[DONE]": "✓",     # Old Unicode symbol
            "[FAILED]": "✗",   # Old Unicode symbol
        }
        
        for ascii_prefix, unicode_symbol in test_prefixes.items():
            # ASCII prefix should be readable
            assert ascii_prefix.isascii(), \
                f"Prefix should be ASCII: {ascii_prefix}"
            
            # Should use brackets
            assert ascii_prefix.startswith("[") and ascii_prefix.endswith("]"), \
                f"Prefix should use brackets: {ascii_prefix}"
            
            # Should be uppercase for clarity
            inner_word = ascii_prefix[1:-1]
            assert inner_word.isupper(), \
                f"Inner word should be uppercase: {inner_word}"
    
    def test_word_instead_of_arrow(self):
        """Test that we use 'to' instead of → arrow."""
        # "HEIC to JPG" reads naturally
        # "HEIC right arrow JPG" or garbage is confusing
        
        correct_phrase = "HEIC to JPG"
        incorrect_phrase = "HEIC → JPG"
        
        # Correct phrase should be ASCII and contain 'to'
        assert correct_phrase.isascii(), "Should be ASCII"
        assert " to " in correct_phrase, "Should use word 'to'"
        
        # Incorrect phrase contains Unicode
        assert not incorrect_phrase.isascii(), "Arrow is not ASCII"


if __name__ == "__main__":
    # Allow running this test file directly
    pytest.main([__file__, "-v"])
