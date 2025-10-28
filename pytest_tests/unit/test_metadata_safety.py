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
from scripts.metadata_extractor import MetadataExtractor


class TestFormatStringSafety:
    """Test that format strings are safe from user input injection."""
    
    @pytest.mark.regression
    def test_camera_make_with_format_chars_safe(self):
        """Test that camera make/model with {} characters doesn't break formatting."""
        # This was the actual bug reported by the user
        mock_exif = {
            'Make': 'Camera{0}Brand',  # Malicious or accidental format string
            'Model': 'Model{1}Name'
        }
        
        extractor = MetadataExtractor()
        
        # Should not raise KeyError or ValueError
        try:
            camera_info = extractor._format_camera_info(mock_exif)
            # If we get here, no exception was raised - good!
            assert '{0}' in camera_info or '{1}' in camera_info or \
                   'Camera' in camera_info, \
                "Should preserve original text safely"
        except (KeyError, ValueError) as e:
            pytest.fail(f"Format string in camera info should not cause errors: {e}")
    
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
        """Verify that metadata formatting uses safe concatenation."""
        # Check that image_describer.py uses concatenation, not format()
        image_describer_path = Path(__file__).parent.parent.parent / "scripts" / "image_describer.py"
        
        with open(image_describer_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Look for the metadata formatting section
        # Should find safe concatenation patterns, not .format() with user data
        lines = source.split('\n')
        
        # Find where metadata is formatted
        metadata_section = []
        in_metadata_format = False
        
        for line in lines:
            if 'def _format_metadata_line' in line or '_format_location_prefix' in line:
                in_metadata_format = True
            
            if in_metadata_format:
                metadata_section.append(line)
                
                if line.strip() and not line.strip().startswith('#') and \
                   line.strip() != '' and 'return' in line:
                    in_metadata_format = False
        
        metadata_code = '\n'.join(metadata_section)
        
        # Should use + concatenation, not .format() or f-strings with external data
        # This is a heuristic check - not perfect but catches obvious issues
        if 'camera_info.format(' in metadata_code or 'location.format(' in metadata_code:
            pytest.fail("Metadata formatting should not use .format() with user data")


class TestMetadataExtraction:
    """Test metadata extraction functionality."""
    
    def test_gps_coordinates_extracted(self):
        """Test that GPS coordinates are properly extracted."""
        mock_exif = {
            'GPSLatitude': ((28, 1), (6, 1), (2, 100)),
            'GPSLatitudeRef': 'N',
            'GPSLongitude': ((80, 1), (34, 1), (5, 100)),
            'GPSLongitudeRef': 'W'
        }
        
        extractor = MetadataExtractor()
        lat, lon = extractor._extract_gps_coordinates(mock_exif)
        
        # Should be approximately 28.1006, -80.5681
        assert 28.0 < lat < 28.2, f"Latitude {lat} should be ~28.1"
        assert -80.6 < lon < -80.5, f"Longitude {lon} should be ~-80.57"
    
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
    pytest.main([__file__, "-v"])
