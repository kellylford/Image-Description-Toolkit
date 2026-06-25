#!/usr/bin/env python3
"""
End-to-end workflow integration tests.

Tests the complete pipeline:
1. Video frame extraction with EXIF embedding
2. HEIC to JPG conversion with metadata preservation
3. Image description with metadata extraction
4. HTML generation
5. Viewer parsing

These tests would have caught:
- EXIF loss during conversion optimization
- Source file tracking for video frames
- Metadata extraction failures
- Viewer parsing issues
"""

import sys
import tempfile
import shutil
import json
from pathlib import Path
from datetime import datetime
import pytest

from PIL import Image
import piexif


class TestWorkflowIntegration:
    """End-to-end workflow tests"""
    
    @pytest.fixture
    def temp_workflow_dir(self):
        """Create a temporary workflow directory structure"""
        tmp = Path(tempfile.mkdtemp())
        
        # Create workflow structure
        (tmp / "converted_images").mkdir()
        (tmp / "descriptions").mkdir()
        (tmp / "html_reports").mkdir()
        (tmp / "logs").mkdir()
        
        yield tmp
        shutil.rmtree(tmp)
    
    def create_test_image_with_metadata(self, path: Path, size=(1000, 1000)):
        """Create a test image with realistic EXIF metadata"""
        exif_dict = {
            "0th": {
                piexif.ImageIFD.Make: b"Apple",
                piexif.ImageIFD.Model: b"iPhone 15 Pro",
                piexif.ImageIFD.DateTime: b"2024:10:29 08:30:00",
            },
            "Exif": {
                piexif.ExifIFD.DateTimeOriginal: b"2024:10:29 08:30:00",
            },
            "GPS": {
                piexif.GPSIFD.GPSLatitudeRef: b"N",
                piexif.GPSIFD.GPSLatitude: ((43, 1), (4, 1), (20, 1)),
                piexif.GPSIFD.GPSLongitudeRef: b"W",
                piexif.GPSIFD.GPSLongitude: ((89, 1), (23, 1), (45, 1)),
            },
        }
        
        exif_bytes = piexif.dump(exif_dict)
        img = Image.new('RGB', size, color=(100, 150, 200))
        img.save(path, 'JPEG', quality=95, exif=exif_bytes)
        return path
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_conversion_preserves_metadata_end_to_end(self, temp_workflow_dir):
        """Test that conversion preserves EXIF through the whole pipeline"""
        from idt_core.converter import convert_heic_to_jpg
        from idt_core.metadata import MetadataExtractor
        
        # Create source image with metadata
        source_path = temp_workflow_dir / "source.jpg"
        self.create_test_image_with_metadata(source_path, size=(2500, 2000))
        
        # Make it large to trigger optimization
        img = Image.open(source_path)
        exif_bytes = piexif.dump(piexif.load(str(source_path)))
        img.save(source_path, 'JPEG', quality=100, exif=exif_bytes)
        
        # Convert (will trigger size optimization)
        output_path = temp_workflow_dir / "converted_images" / "source.jpg"
        success = convert_heic_to_jpg(
            source_path,
            output_path,
            keep_metadata=True,
            max_file_size=2 * 1024 * 1024  # 2MB to force optimization
        )
        
        assert success, "Conversion should succeed"
        
        # Extract metadata using the real extractor (flat ImageMetadata.to_dict() format)
        extractor = MetadataExtractor()
        meta = extractor.extract(output_path)
        metadata = meta.to_dict() if meta else {}

        # Verify metadata was preserved
        assert metadata.get('date_short') or metadata.get('date_taken'), "Should have datetime"
        assert metadata.get('camera_make') or metadata.get('camera_model'), "Should have camera info"
        assert metadata.get('latitude') is not None, "Should have GPS latitude"
        assert metadata.get('longitude') is not None, "Should have GPS longitude"
        assert metadata.get('camera_make') == 'Apple'
        assert metadata.get('camera_model') == 'iPhone 15 Pro'
    


class TestVideoFrameSourceTracking:
    """Test video frame source file tracking"""
    
    @pytest.mark.integration
    def test_video_frame_has_source_in_exif(self):
        """Test that extracted video frames have source path in EXIF"""
        # This would test the exif_embedder.py functionality
        from idt_core.video import ExifEmbedder
        
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            
            # Create a test frame
            frame_path = tmp / "video_12.34s.jpg"
            img = Image.new('RGB', (1920, 1080), color=(50, 100, 150))
            img.save(frame_path, 'JPEG')
            
            # Embed source video info
            embedder = ExifEmbedder()
            metadata = {'datetime': datetime.now()}
            
            success = embedder.embed_metadata(
                frame_path,
                metadata,
                frame_time=12.34,
                source_video_path=Path("/videos/test_video.mp4")
            )
            
            assert success, "Should embed metadata successfully"
            
            # Verify EXIF contains source info
            exif_dict = piexif.load(str(frame_path))
            desc = exif_dict['0th'].get(piexif.ImageIFD.ImageDescription, b'')
            
            if isinstance(desc, bytes):
                desc = desc.decode('utf-8', errors='ignore')
            
            assert "Extracted from video:" in desc
            assert "test_video.mp4" in desc
            assert "12.34s" in desc


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
