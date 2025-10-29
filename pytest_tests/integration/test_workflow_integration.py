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

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

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
        from ConvertImage import convert_heic_to_jpg
        from metadata_extractor import MetadataExtractor
        
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
        
        # Extract metadata using the real extractor
        extractor = MetadataExtractor()
        metadata = extractor.extract_metadata(output_path)
        
        # Verify metadata was preserved
        assert 'datetime' in metadata, "Should have datetime"
        assert 'camera' in metadata, "Should have camera info"
        assert 'location' in metadata, "Should have GPS location"
        assert metadata['camera']['make'] == 'Apple'
        assert metadata['camera']['model'] == 'iPhone 15 Pro'
        assert 'latitude' in metadata['location']
        assert 'longitude' in metadata['location']
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_description_file_includes_metadata(self, temp_workflow_dir):
        """Test that description file includes all metadata fields"""
        from ConvertImage import convert_heic_to_jpg
        from image_describer import ImageDescriber
        
        # Create and convert image
        source_path = temp_workflow_dir / "test.jpg"
        converted_path = temp_workflow_dir / "converted_images" / "test.jpg"
        self.create_test_image_with_metadata(source_path, size=(2000, 1500))
        
        # Make it large
        img = Image.open(source_path)
        exif_bytes = piexif.dump(piexif.load(str(source_path)))
        img.save(source_path, 'JPEG', quality=100, exif=exif_bytes)
        
        convert_heic_to_jpg(source_path, converted_path, keep_metadata=True, max_file_size=1.5 * 1024 * 1024)
        
        # Create minimal config for testing
        config = {
            'output_format': {
                'include_metadata': True,
                'include_model_info': True,
                'include_file_path': True,
            },
            'metadata': {
                'include_location_prefix': False,  # Disable for simpler test
            }
        }
        
        # Mock describe - we're testing metadata extraction, not AI
        describer = ImageDescriber(provider="mock", model="test", config_dict=config)
        output_file = temp_workflow_dir / "descriptions" / "test.txt"
        
        # Manually write a description with metadata
        from metadata_extractor import MetadataExtractor
        extractor = MetadataExtractor()
        metadata = extractor.extract_metadata(converted_path)
        
        # Verify metadata was extracted
        assert metadata, "Should extract metadata"
        assert 'datetime' in metadata
        assert 'camera' in metadata
        assert 'location' in metadata
        
        # Write using the real method
        describer.write_description_to_file(
            converted_path,
            "Test description",
            output_file,
            metadata=metadata,
            base_directory=temp_workflow_dir
        )
        
        # Read and verify description file
        content = output_file.read_text(encoding='utf-8')
        assert "Photo Date:" in content, "Should include photo date"
        assert "GPS:" in content, "Should include GPS coordinates"
        assert "Camera:" in content, "Should include camera info"
        assert "Apple" in content or "iPhone" in content, "Should include camera make/model"
    
    @pytest.mark.integration
    def test_viewer_parses_all_fields(self, temp_workflow_dir):
        """Test that viewer can parse all metadata fields from description file"""
        # Create a sample description file
        desc_file = temp_workflow_dir / "descriptions" / "image_descriptions.txt"
        
        content = """File: test.jpg
Path: /path/to/test.jpg
Photo Date: 10/29/2024 8:30A
Camera: Apple iPhone 15 Pro
GPS: 43.073333, -89.395000, Altitude: 180.0m
Provider: ollama
Model: llava
Prompt Style: narrative
Description: A beautiful landscape photo
Timestamp: 2024-10-29 08:30:00
""" + ("-" * 80) + "\n"
        
        desc_file.write_text(content, encoding='utf-8')
        
        # Import and test viewer parser
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "viewer"))
        from viewer import DescriptionFileParser
        
        parser = DescriptionFileParser()
        entries = parser.parse_file(desc_file)
        
        assert len(entries) == 1, "Should parse one entry"
        entry = entries[0]
        
        assert entry['relative_path'] == "test.jpg"
        assert entry['file_path'] == "/path/to/test.jpg"
        assert entry['description'] == "A beautiful landscape photo"
        assert 'photo_date' in entry['metadata']
        assert 'camera' in entry['metadata']
        assert entry['model'] == "llava"


class TestVideoFrameSourceTracking:
    """Test video frame source file tracking"""
    
    @pytest.mark.integration
    def test_video_frame_has_source_in_exif(self):
        """Test that extracted video frames have source path in EXIF"""
        # This would test the exif_embedder.py functionality
        from exif_embedder import ExifEmbedder
        
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
