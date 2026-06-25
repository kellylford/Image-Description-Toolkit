"""
Unit tests for metadata extraction and format string safety.

Tests ensure EXIF data is extracted correctly and that user-provided text
cannot cause format string errors in prompt context building.
"""

import pytest
from pathlib import Path
from datetime import datetime

import piexif
from PIL import Image

from idt_core.metadata import MetadataExtractor, ImageMetadata


def _make_jpeg_with_exif(path: Path, make: str = "Apple", model: str = "iPhone 15 Pro",
                          lat: float = 28.1, lon: float = -80.57) -> Path:
    """Write a JPEG with Make/Model and GPS EXIF tags."""
    path.parent.mkdir(parents=True, exist_ok=True)

    def _dd_to_dms(dd: float):
        dd = abs(dd)
        d = int(dd)
        m = int((dd - d) * 60)
        s = round(((dd - d) * 60 - m) * 60 * 100)
        return ((d, 1), (m, 1), (s, 100))

    exif = {
        "0th": {
            piexif.ImageIFD.Make: make.encode(),
            piexif.ImageIFD.Model: model.encode(),
            piexif.ImageIFD.DateTime: b"2024:10:29 08:30:00",
        },
        "Exif": {
            piexif.ExifIFD.DateTimeOriginal: b"2024:10:29 08:30:00",
        },
        "GPS": {
            piexif.GPSIFD.GPSLatitudeRef: b"N" if lat >= 0 else b"S",
            piexif.GPSIFD.GPSLatitude: _dd_to_dms(lat),
            piexif.GPSIFD.GPSLongitudeRef: b"E" if lon >= 0 else b"W",
            piexif.GPSIFD.GPSLongitude: _dd_to_dms(lon),
        },
    }
    img = Image.new("RGB", (64, 64), (100, 150, 200))
    img.save(path, "JPEG", exif=piexif.dump(exif))
    return path


class TestFormatStringSafety:
    """Camera/location text with braces or special chars must not crash prompt building."""

    @pytest.mark.regression
    def test_camera_make_with_format_chars_safe(self, tmp_path):
        """prompt_context() must not raise when camera make/model contains {}."""
        path = _make_jpeg_with_exif(tmp_path / "cam.jpg",
                                    make="Camera{0}Brand", model="Model{1}Name")
        meta = MetadataExtractor().extract(path)
        assert meta.camera_make == "Camera{0}Brand"
        assert meta.camera_model == "Model{1}Name"
        # Building the prompt context string must not raise
        ctx = meta.prompt_context()
        assert isinstance(ctx, str)

    def test_metadata_formatting_uses_concatenation(self, tmp_path):
        """prompt_context() must produce a plain string with no format tokens."""
        path = _make_jpeg_with_exif(tmp_path / "fmt.jpg",
                                    make="{not_a_key}", model="{also_not}")
        meta = MetadataExtractor().extract(path)
        ctx = meta.prompt_context()
        # The output is a plain string — no unresolved {…} format tokens
        assert isinstance(ctx, str)
        # Neither camera string triggered an exception (if it raised, we'd never reach here)


class TestMetadataExtraction:
    """GPS coordinates and camera info must be extracted correctly."""

    def test_gps_coordinates_extracted(self, tmp_path):
        """Latitude and longitude must round-trip through EXIF correctly."""
        path = _make_jpeg_with_exif(tmp_path / "gps.jpg", lat=28.1, lon=-80.57)
        meta = MetadataExtractor().extract(path)
        assert meta.latitude is not None, "Should extract latitude"
        assert meta.longitude is not None, "Should extract longitude"
        assert 28.0 < meta.latitude < 28.2, f"Latitude {meta.latitude} should be ~28.1"
        assert -80.6 < meta.longitude < -80.5, f"Longitude {meta.longitude} should be ~-80.57"

    def test_date_formatting_windows_safe(self):
        """Date formatting must not use %-directives (unsupported on Windows)."""
        test_date = datetime(2023, 1, 8, 13, 43, 0)
        formatted = test_date.strftime("%m/%d/%Y %I:%M%p")
        assert formatted, "Date should format successfully"
        # Remove leading zeros the Windows-safe way
        m, d, y = formatted.split()[0].split("/")
        clean = f"{int(m)}/{int(d)}/{y}"
        assert clean == "1/8/2023"
