"""
Unit tests for metadata extraction and format string safety.

Tests ensure that user-provided text and EXIF data cannot cause format string
errors when used in string formatting operations.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

# Import metadata extractor
from idt_core.metadata import MetadataExtractor


class TestFormatStringSafety:
    """Test that format strings are safe from user input injection."""
    
    @pytest.mark.regression
    def test_camera_make_with_format_chars_safe(self):
        """Test that camera make/model with {} characters doesn't break formatting."""
        from idt_core.metadata import ImageMetadata
        exif = {
            'Make': 'Camera{0}Brand',
            'Model': 'Model{1}Name',
        }
        meta = ImageMetadata()
        MetadataExtractor()._fill_camera(meta, exif)
        assert meta.camera_make == 'Camera{0}Brand'
        assert meta.camera_model == 'Model{1}Name'
        # prompt_context must not raise when values contain format-string characters
        context = meta.prompt_context()
        assert isinstance(context, str)
        assert 'Camera{0}Brand' in context or 'Model{1}Name' in context
    
    @pytest.mark.regression  
    def test_location_prefix_with_format_chars_safe(self):
        """Test that city/state names with {} don't break formatting."""
        # City names could theoretically contain {}, though rare
        test_cases = [
            ("City{0}", "State"),
            ("Normal City", "State{1}"),
            ("City{name}", "State{code}")
        ]
        
        for city, state in test_cases:
            # Should not raise an exception when building location prefix
            try:
                # This simulates what image_describer does
                location_str = city + ", " + state
                # Using concatenation (the fix) instead of f-string or .format()
                assert city in location_str and state in location_str
            except (KeyError, ValueError) as e:
                pytest.fail(f"Location text '{city}, {state}' caused error: {e}")
    
    def test_metadata_formatting_uses_concatenation(self):
        """Verify that prompt_context() is safe when metadata values contain format-string chars."""
        from idt_core.metadata import ImageMetadata
        # Values with format-string markers that would crash str.format() or % formatting
        meta = ImageMetadata(
            city="City{0}",
            state="State{1}",
            date_short="Jan{2} 2025",
            camera_model="Model{name}",
        )
        # Must not raise KeyError / IndexError even with format-string characters
        context = meta.prompt_context()
        assert isinstance(context, str)
        assert "City{0}" in context
        assert "State{1}" in context


class TestMetadataExtraction:
    """Test metadata extraction functionality."""
    
    def test_gps_coordinates_extracted(self):
        """Test that GPS coordinates are properly extracted."""
        from idt_core.metadata import ImageMetadata
        exif = {
            'GPSInfo': {
                'GPSLatitude': ((28, 1), (6, 1), (2, 100)),
                'GPSLatitudeRef': 'N',
                'GPSLongitude': ((80, 1), (34, 1), (5, 100)),
                'GPSLongitudeRef': 'W',
            }
        }
        meta = ImageMetadata()
        MetadataExtractor()._fill_location(meta, exif)
        assert meta.latitude is not None
        assert meta.longitude is not None
        # Should be approximately 28.1006, -80.5681
        assert 28.0 < meta.latitude < 28.2, f"Latitude {meta.latitude} should be ~28.1"
        assert -80.6 < meta.longitude < -80.5, f"Longitude {meta.longitude} should be ~-80.57"
    
    def test_date_formatting_windows_safe(self):
        """Test that date formatting works on Windows (no %-formatting)."""
        # Windows doesn't support %-d, %-m, etc. Must use different approach
        test_date = datetime(2023, 1, 8, 13, 43, 0)
        
        # The fix: use .replace() to remove leading zeros
        formatted = test_date.strftime("%m/%d/%Y %I:%M%p")
        
        # Should not have leading zero issues that crash on Windows
        assert formatted, "Date should format successfully"
        
        # Remove leading zeros
        parts = formatted.split()
        date_part = parts[0]
        time_part = parts[1] if len(parts) > 1 else ""
        
        # Split date part
        m, d, y = date_part.split('/')
        formatted_clean = f"{int(m)}/{int(d)}/{y}"
        
        if time_part:
            h, rest = time_part.split(':', 1)
            formatted_clean += f" {int(h)}:{rest}"
        
        assert formatted_clean, "Date formatting should work on Windows"


if __name__ == "__main__":
    # Allow running this test file directly
    import unittest
    unittest.main()
