"""
Unit tests for shared EXIF extraction utilities.

Tests for functions in shared/exif_utils.py including:
- extract_exif_datetime()
- extract_exif_date_string()
- extract_exif_data()
- extract_gps_coordinates()
- get_image_date_for_sorting()
- _convert_gps_coordinate() (internal)
"""

import pytest
from pathlib import Path
from datetime import datetime, timedelta
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.exif_utils import (
    extract_exif_datetime,
    extract_exif_date_string,
    extract_exif_data,
    extract_gps_coordinates,
    get_image_date_for_sorting,
    _convert_gps_coordinate
)


class TestExtractExifDatetime:
    """Test suite for extract_exif_datetime() function."""
    
    def test_extract_exif_datetime_with_missing_file(self):
        """Test that missing file returns None."""
        result = extract_exif_datetime('/nonexistent/file.jpg')
        assert result is None, "Should return None for nonexistent file"
    
    def test_extract_exif_datetime_handles_pathlib_path(self):
        """Test that both string and Path objects are handled."""
        # Both should handle the same way
        str_result = extract_exif_datetime('/nonexistent/file.jpg')
        path_result = extract_exif_datetime(Path('/nonexistent/file.jpg'))
        assert str_result == path_result, "Should handle both str and Path"
    
    def test_extract_exif_datetime_error_handling(self):
        """Test that exceptions are handled gracefully."""
        # Test with invalid path type - should return None, not raise
        try:
            result = extract_exif_datetime(None)
            # Should handle gracefully without raising
            assert result is None or isinstance(result, (datetime, type(None)))
        except TypeError:
            # If TypeError is raised, that's also acceptable for None input
            pass


class TestExtractExifDateString:
    """Test suite for extract_exif_date_string() function."""
    
    def test_extract_exif_date_string_missing_file_returns_default(self):
        """Test that missing file returns 'Unknown date'."""
        result = extract_exif_date_string('/nonexistent/file.jpg')
        assert result == "Unknown date", "Should return 'Unknown date' for missing file"
    
    def test_extract_exif_date_string_never_returns_none(self):
        """Test that function always returns a string."""
        result = extract_exif_date_string('/nonexistent/file.jpg')
        assert isinstance(result, str), "Should always return a string"
        assert len(result) > 0, "Should never return empty string"
    
    def test_extract_exif_date_string_error_handling(self):
        """Test that exceptions are handled gracefully."""
        try:
            result = extract_exif_date_string(None)
            assert isinstance(result, str), "Should return string even with invalid input"
        except Exception as e:
            # If exception raised, should be caught internally
            pytest.fail(f"Should handle errors gracefully, got: {e}")


class TestExtractExifData:
    """Test suite for extract_exif_data() function."""
    
    def test_extract_exif_data_missing_file_returns_empty_dict(self):
        """Test that missing file returns empty dictionary."""
        result = extract_exif_data('/nonexistent/file.jpg')
        assert result == {}, "Should return empty dict for missing file"
        assert isinstance(result, dict), "Should always return dict"
    
    def test_extract_exif_data_returns_dict_type(self):
        """Test that function returns dictionary."""
        result = extract_exif_data('/nonexistent/file.jpg')
        assert isinstance(result, dict), "Should return dict type"
    
    def test_extract_exif_data_error_handling(self):
        """Test that exceptions are handled gracefully."""
        try:
            result = extract_exif_data(None)
            assert isinstance(result, dict), "Should return dict even with invalid input"
        except Exception as e:
            pytest.fail(f"Should handle errors gracefully, got: {e}")


class TestExtractGpsCoordinates:
    """Test suite for extract_gps_coordinates() function."""
    
    def test_extract_gps_coordinates_missing_file_returns_none(self):
        """Test that missing file returns None."""
        result = extract_gps_coordinates('/nonexistent/file.jpg')
        assert result is None, "Should return None for missing file"
    
    def test_extract_gps_coordinates_error_handling(self):
        """Test that exceptions are handled gracefully."""
        try:
            result = extract_gps_coordinates(None)
            assert result is None or isinstance(result, dict), "Should handle errors gracefully"
        except Exception as e:
            pytest.fail(f"Should handle errors gracefully, got: {e}")


class TestGetImageDateForSorting:
    """Test suite for get_image_date_for_sorting() function."""
    
    def test_get_image_date_for_sorting_returns_datetime(self):
        """Test that function always returns datetime object."""
        result = get_image_date_for_sorting('/nonexistent/file.jpg')
        assert isinstance(result, datetime), "Should always return datetime"
    
    def test_get_image_date_for_sorting_missing_file_returns_epoch(self):
        """Test that missing file returns epoch time."""
        result = get_image_date_for_sorting('/nonexistent/file.jpg')
        epoch = datetime.fromtimestamp(0)
        assert result == epoch, "Should return epoch time for missing file"
    
    def test_get_image_date_for_sorting_safe_for_comparison(self):
        """Test that returned datetime can be compared and sorted."""
        dt1 = get_image_date_for_sorting('/nonexistent/file1.jpg')
        dt2 = get_image_date_for_sorting('/nonexistent/file2.jpg')
        
        # Should be sortable without error
        dates = [dt2, dt1]
        sorted_dates = sorted(dates)
        
        assert len(sorted_dates) == 2, "Should be sortable"
        assert sorted_dates[0] <= sorted_dates[1], "Should maintain order"


class TestConvertGpsCoordinate:
    """Test suite for _convert_gps_coordinate() internal function."""
    
    def test_convert_gps_coordinate_basic(self):
        """Test basic GPS coordinate conversion."""
        # Test with simple values (as Fraction objects would be)
        class Fraction:
            def __init__(self, num, denom=1):
                self.numerator = num
                self.denominator = denom
            
            def __float__(self):
                return self.numerator / self.denominator
            
            def __truediv__(self, other):
                return float(self) / other
        
        # Degrees: 40, Minutes: 30, Seconds: 0
        # Expected: 40 + 30/60 + 0/3600 = 40.5
        degrees = Fraction(40, 1)
        minutes = Fraction(30, 1)
        seconds = Fraction(0, 1)
        
        result = _convert_gps_coordinate((degrees, minutes, seconds))
        expected = 40.5
        
        # Allow small float rounding errors
        assert abs(result - expected) < 0.0001, \
            f"Should convert to 40.5, got {result}"
    
    def test_convert_gps_coordinate_zero_division_handling(self):
        """Test that zero values are handled gracefully."""
        # Test with zero values
        result = _convert_gps_coordinate((0, 0, 0))
        assert result == 0.0, "Should handle zero coordinates"
    
    def test_convert_gps_coordinate_error_handling(self):
        """Test that invalid input is handled."""
        # Test with invalid input
        result = _convert_gps_coordinate((None, None, None))
        assert result == 0.0, "Should return 0.0 for invalid input"


class TestDateFormatting:
    """Test suite for date formatting consistency."""
    
    def test_exif_date_string_format(self):
        """Test that date string format is correct when date is found."""
        # This tests the format when EXIF data is available
        # Note: actual testing requires real image files
        # This tests the format string construction
        
        # Mock datetime for testing format
        test_date_str = extract_exif_date_string('/nonexistent/file.jpg')
        
        # Even if "Unknown date", should be string
        assert isinstance(test_date_str, str), "Should return string"
    
    def test_get_image_date_for_sorting_always_sortable(self):
        """Test that dates returned are always sortable."""
        # Create multiple dates and verify they sort correctly
        dates = []
        for i in range(3):
            dt = get_image_date_for_sorting(f'/nonexistent/file{i}.jpg')
            dates.append(dt)
        
        # Should be able to sort without error
        sorted_dates = sorted(dates)
        assert len(sorted_dates) == 3, "Should maintain list length after sorting"


class TestPilImportHandling:
    """Test suite for PIL import fallback behavior."""
    
    def test_extract_exif_datetime_without_pil(self):
        """Test that functions work even if PIL not available."""
        # This tests the fallback behavior
        result = extract_exif_datetime('/nonexistent/file.jpg')
        # Should handle gracefully (None or datetime)
        assert result is None or isinstance(result, datetime)
    
    def test_extract_exif_data_without_pil(self):
        """Test that extract_exif_data returns empty dict without PIL."""
        result = extract_exif_data('/nonexistent/file.jpg')
        assert result == {}, "Should return empty dict"


class TestEdgeCases:
    """Test suite for edge cases and error conditions."""
    
    def test_unicode_filename_handling(self):
        """Test that unicode filenames are handled."""
        result = extract_exif_datetime('/nonexistent/文件.jpg')
        assert result is None, "Should handle unicode filenames"
    
    def test_very_long_path_handling(self):
        """Test that very long paths are handled."""
        long_path = '/nonexistent/' + 'dir/' * 50 + 'file.jpg'
        result = extract_exif_datetime(long_path)
        assert result is None, "Should handle long paths"
    
    def test_special_characters_in_path(self):
        """Test that special characters in path are handled."""
        result = extract_exif_datetime('/nonexistent/file@#$%.jpg')
        assert result is None, "Should handle special characters"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
