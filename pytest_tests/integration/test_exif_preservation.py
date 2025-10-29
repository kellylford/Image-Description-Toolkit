#!/usr/bin/env python3
"""
Integration tests for EXIF metadata preservation through the conversion pipeline.

This test suite specifically addresses the bug where EXIF data was lost during
size optimization (multiple save attempts) in ConvertImage.py.

Tests cover:
1. EXIF preservation on first attempt (small files)
2. EXIF preservation through quality reduction (medium files)
3. EXIF preservation through resizing (large files)
4. GPS coordinates preservation
5. Date/time preservation
6. Camera info preservation
"""

import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import pytest

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from PIL import Image
import piexif

# Import the module under test
from ConvertImage import convert_heic_to_jpg


class TestEXIFPreservation:
    """Test EXIF metadata preservation through image conversion"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files"""
        tmp = tempfile.mkdtemp()
        yield Path(tmp)
        shutil.rmtree(tmp)
    
    @pytest.fixture
    def sample_exif_data(self):
        """Create sample EXIF data with GPS, date, camera info"""
        exif_dict = {
            "0th": {
                piexif.ImageIFD.Make: b"Apple",
                piexif.ImageIFD.Model: b"iPhone 15 Pro",
                piexif.ImageIFD.DateTime: b"2024:10:29 08:30:00",
                piexif.ImageIFD.Software: b"iOS 17.1",
            },
            "Exif": {
                piexif.ExifIFD.DateTimeOriginal: b"2024:10:29 08:30:00",
                piexif.ExifIFD.DateTimeDigitized: b"2024:10:29 08:30:00",
                piexif.ExifIFD.LensModel: b"iPhone 15 Pro back camera",
            },
            "GPS": {
                piexif.GPSIFD.GPSLatitudeRef: b"N",
                piexif.GPSIFD.GPSLatitude: ((43, 1), (4, 1), (3456, 100)),  # 43.073333
                piexif.GPSIFD.GPSLongitudeRef: b"W",
                piexif.GPSIFD.GPSLongitude: ((89, 1), (23, 1), (4567, 100)),  # 89.395
                piexif.GPSIFD.GPSAltitudeRef: 0,
                piexif.GPSIFD.GPSAltitude: (180, 1),  # 180m
            },
        }
        return piexif.dump(exif_dict)
    
    def create_test_image(self, path: Path, size: tuple, exif_bytes: bytes):
        """Create a test JPEG with specified size and EXIF data"""
        # Create a solid color image
        img = Image.new('RGB', size, color=(73, 109, 137))
        img.save(path, 'JPEG', quality=95, exif=exif_bytes)
        return path
    
    def extract_exif_dict(self, image_path: Path):
        """Extract EXIF data from an image as a dict"""
        try:
            exif_dict = piexif.load(str(image_path))
            return exif_dict
        except Exception as e:
            return None
    
    @pytest.mark.integration
    def test_exif_preserved_small_image(self, temp_dir, sample_exif_data):
        """Test EXIF preservation for small images (no optimization needed)"""
        # Create a small image (500x500) that won't need optimization
        input_path = temp_dir / "small_test.jpg"
        output_path = temp_dir / "small_output.jpg"
        
        self.create_test_image(input_path, (500, 500), sample_exif_data)
        
        # Convert
        success = convert_heic_to_jpg(
            input_path, 
            output_path, 
            quality=95, 
            keep_metadata=True
        )
        
        assert success, "Conversion should succeed"
        assert output_path.exists(), "Output file should exist"
        
        # Verify EXIF preserved
        output_exif = self.extract_exif_dict(output_path)
        assert output_exif is not None, "Output should have EXIF data"
        assert output_exif["0th"][piexif.ImageIFD.Make] == b"Apple"
        assert output_exif["0th"][piexif.ImageIFD.Model] == b"iPhone 15 Pro"
        assert "GPS" in output_exif and output_exif["GPS"], "GPS data should be preserved"
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_exif_preserved_through_quality_reduction(self, temp_dir, sample_exif_data):
        """Test EXIF preservation when quality reduction is needed (medium size)"""
        # Create a medium image that will trigger quality reduction
        # but not resizing (around 2000x2000)
        input_path = temp_dir / "medium_test.jpg"
        output_path = temp_dir / "medium_output.jpg"
        
        self.create_test_image(input_path, (2000, 2000), sample_exif_data)
        
        # Make the file large by saving at high quality
        img = Image.open(input_path)
        img.save(input_path, 'JPEG', quality=100, exif=sample_exif_data)
        
        # Convert with a size limit that will trigger optimization
        success = convert_heic_to_jpg(
            input_path,
            output_path,
            quality=95,
            keep_metadata=True,
            max_file_size=2 * 1024 * 1024  # 2MB limit to force optimization
        )
        
        assert success, "Conversion should succeed"
        
        # Verify EXIF preserved AFTER quality reduction
        output_exif = self.extract_exif_dict(output_path)
        assert output_exif is not None, "Output should have EXIF data after quality reduction"
        assert output_exif["0th"][piexif.ImageIFD.Make] == b"Apple"
        assert output_exif["Exif"][piexif.ExifIFD.DateTimeOriginal] == b"2024:10:29 08:30:00"
        assert "GPS" in output_exif and output_exif["GPS"], "GPS data should survive quality reduction"
    
    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.regression
    def test_exif_preserved_through_resize(self, temp_dir, sample_exif_data):
        """
        Test EXIF preservation when resizing is needed (large size).
        
        This is a regression test for the bug where EXIF data was lost
        during size optimization (multiple save attempts) in ConvertImage.py.
        """
        # Create a very large image that will trigger both quality reduction AND resizing
        input_path = temp_dir / "large_test.jpg"
        output_path = temp_dir / "large_output.jpg"
        
        self.create_test_image(input_path, (4000, 3000), sample_exif_data)
        
        # Make it extremely large
        img = Image.open(input_path)
        img.save(input_path, 'JPEG', quality=100, exif=sample_exif_data)
        
        # Convert with a tight size limit to force resizing
        success = convert_heic_to_jpg(
            input_path,
            output_path,
            quality=95,
            keep_metadata=True,
            max_file_size=1 * 1024 * 1024  # 1MB limit to force aggressive optimization
        )
        
        assert success, "Conversion should succeed"
        
        # THIS IS THE CRITICAL TEST: EXIF must survive resizing
        output_exif = self.extract_exif_dict(output_path)
        assert output_exif is not None, "Output should have EXIF data after resize"
        assert output_exif["0th"][piexif.ImageIFD.Make] == b"Apple"
        assert output_exif["0th"][piexif.ImageIFD.Model] == b"iPhone 15 Pro"
        assert "GPS" in output_exif and output_exif["GPS"], "GPS data should survive resize"
    
    @pytest.mark.integration
    def test_gps_coordinates_accuracy(self, temp_dir, sample_exif_data):
        """Test that GPS coordinates remain accurate through conversion"""
        input_path = temp_dir / "gps_test.jpg"
        output_path = temp_dir / "gps_output.jpg"
        
        self.create_test_image(input_path, (2000, 1500), sample_exif_data)
        
        # Force optimization
        img = Image.open(input_path)
        img.save(input_path, 'JPEG', quality=100, exif=sample_exif_data)
        
        convert_heic_to_jpg(
            input_path,
            output_path,
            keep_metadata=True,
            max_file_size=1.5 * 1024 * 1024
        )
        
        output_exif = self.extract_exif_dict(output_path)
        
        # Verify GPS coordinates match exactly
        assert output_exif["GPS"][piexif.GPSIFD.GPSLatitude] == ((43, 1), (4, 1), (3456, 100))
        assert output_exif["GPS"][piexif.GPSIFD.GPSLongitude] == ((89, 1), (23, 1), (4567, 100))
        assert output_exif["GPS"][piexif.GPSIFD.GPSAltitude] == (180, 1)
    
    @pytest.mark.integration
    def test_metadata_disabled(self, temp_dir, sample_exif_data):
        """Test that metadata can be intentionally stripped when keep_metadata=False"""
        input_path = temp_dir / "strip_test.jpg"
        output_path = temp_dir / "strip_output.jpg"
        
        self.create_test_image(input_path, (800, 600), sample_exif_data)
        
        convert_heic_to_jpg(
            input_path,
            output_path,
            keep_metadata=False  # Explicitly disable metadata
        )
        
        # Verify EXIF was stripped
        output_exif = self.extract_exif_dict(output_path)
        # Some basic EXIF might still exist (orientation, etc) but our custom data should be gone
        if output_exif:
            assert piexif.ImageIFD.Make not in output_exif.get("0th", {})
            assert "GPS" not in output_exif or not output_exif["GPS"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
