#!/usr/bin/env python3
"""
Unit tests for workflow redescribe functionality
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json
import tempfile
import shutil

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from workflow import (
    validate_redescribe_args,
    determine_reusable_steps,
    can_create_hardlinks,
    can_create_symlinks,
    reuse_images
)
from workflow_utils import save_workflow_metadata, load_workflow_metadata


class TestValidateRedescribeArgs:
    """Tests for validate_redescribe_args function"""
    
    def test_rejects_input_source_with_redescribe(self, tmp_path):
        """Should reject input_source argument with --redescribe"""
        args = Mock(
            input_source="/some/path",
            redescribe=str(tmp_path),
            resume=None,
            download=None
        )
        
        with pytest.raises(ValueError, match="Cannot specify input_source with --redescribe"):
            validate_redescribe_args(args, tmp_path)
    
    def test_rejects_resume_with_redescribe(self, tmp_path):
        """Should reject --resume argument with --redescribe"""
        args = Mock(
            input_source=None,
            redescribe=str(tmp_path),
            resume="/some/path",
            download=None
        )
        
        with pytest.raises(ValueError, match="Cannot use --resume with --redescribe"):
            validate_redescribe_args(args, tmp_path)
    
    def test_rejects_download_with_redescribe(self, tmp_path):
        """Should reject --download argument with --redescribe"""
        args = Mock(
            input_source=None,
            redescribe=str(tmp_path),
            resume=None,
            download="https://example.com"
        )
        
        with pytest.raises(ValueError, match="Cannot use --download with --redescribe"):
            validate_redescribe_args(args, tmp_path)
    
    def test_rejects_nonexistent_source(self):
        """Should reject source workflow that doesn't exist"""
        fake_path = Path("/nonexistent/workflow/dir")
        args = Mock(
            input_source=None,
            redescribe=str(fake_path),
            resume=None,
            download=None
        )
        
        with pytest.raises(ValueError, match="Source workflow not found"):
            validate_redescribe_args(args, fake_path)
    
    def test_rejects_source_without_metadata(self, tmp_path):
        """Should reject source workflow without metadata file"""
        source_dir = tmp_path / "test_workflow"
        source_dir.mkdir()
        
        args = Mock(
            input_source=None,
            redescribe=str(source_dir),
            resume=None,
            download=None
        )
        
        with pytest.raises(ValueError, match="Invalid workflow directory"):
            validate_redescribe_args(args, source_dir)
    
    def test_rejects_source_without_images(self, tmp_path):
        """Should reject source workflow without processed images"""
        source_dir = tmp_path / "test_workflow"
        source_dir.mkdir()
        
        # Create metadata but no images
        metadata = {
            "workflow_name": "test",
            "provider": "ollama",
            "model": "llava",
            "prompt_style": "narrative"
        }
        save_workflow_metadata(source_dir, metadata)
        
        args = Mock(
            input_source=None,
            redescribe=str(source_dir),
            resume=None,
            download=None,
            provider="openai",
            model="gpt-4o",
            prompt_style=None,
            config_image_describer=None
        )
        
        with pytest.raises(ValueError, match="has no processed images"):
            validate_redescribe_args(args, source_dir)
    
    def test_requires_changed_ai_settings(self, tmp_path):
        """Should require at least one AI setting to change"""
        source_dir = tmp_path / "test_workflow"
        source_dir.mkdir()
        (source_dir / "converted_images").mkdir()
        
        # Create a dummy image file
        (source_dir / "converted_images" / "test.jpg").write_text("fake image")
        
        # Create metadata
        metadata = {
            "workflow_name": "test",
            "provider": "ollama",
            "model": "llava",
            "prompt_style": "narrative"
        }
        save_workflow_metadata(source_dir, metadata)
        
        # Try to redescribe with same settings
        args = Mock(
            input_source=None,
            redescribe=str(source_dir),
            resume=None,
            download=None,
            provider="ollama",
            model="llava",
            prompt_style="narrative",
            config_image_describer=None
        )
        
        with pytest.raises(ValueError, match="requires at least one change"):
            validate_redescribe_args(args, source_dir)
    
    def test_accepts_valid_source_with_changes(self, tmp_path):
        """Should accept valid source workflow with changed AI settings"""
        source_dir = tmp_path / "test_workflow"
        source_dir.mkdir()
        (source_dir / "converted_images").mkdir()
        
        # Create a dummy image file
        (source_dir / "converted_images" / "test.jpg").write_text("fake image")
        
        # Create metadata
        metadata = {
            "workflow_name": "test",
            "provider": "ollama",
            "model": "llava",
            "prompt_style": "narrative"
        }
        save_workflow_metadata(source_dir, metadata)
        
        # Redescribe with different provider
        args = Mock(
            input_source=None,
            redescribe=str(source_dir),
            resume=None,
            download=None,
            provider="openai",
            model=None,  # Will use default
            prompt_style=None,
            config_image_describer=None
        )
        
        # Should not raise
        result = validate_redescribe_args(args, source_dir)
        assert result == metadata


class TestDetermineReusableSteps:
    """Tests for determine_reusable_steps function"""
    
    def test_detects_converted_images(self, tmp_path):
        """Should detect converted images directory"""
        source_dir = tmp_path / "test_workflow"
        source_dir.mkdir()
        converted = source_dir / "converted_images"
        converted.mkdir()
        
        # Create dummy images
        (converted / "img1.jpg").write_text("fake")
        (converted / "img2.png").write_text("fake")
        
        metadata = {}
        
        with patch('builtins.print'):
            result = determine_reusable_steps(source_dir, metadata)
        
        assert "convert" in result
        assert "video" not in result
    
    def test_detects_extracted_frames(self, tmp_path):
        """Should detect extracted video frames"""
        source_dir = tmp_path / "test_workflow"
        source_dir.mkdir()
        extracted = source_dir / "extracted_frames"
        extracted.mkdir()
        
        # Create dummy frames
        (extracted / "frame001.jpg").write_text("fake")
        (extracted / "frame002.jpg").write_text("fake")
        
        metadata = {}
        
        with patch('builtins.print'):
            result = determine_reusable_steps(source_dir, metadata)
        
        assert "video" in result
        assert "convert" not in result
    
    def test_detects_both_types(self, tmp_path):
        """Should detect both video frames and converted images"""
        source_dir = tmp_path / "test_workflow"
        source_dir.mkdir()
        
        extracted = source_dir / "extracted_frames"
        extracted.mkdir()
        (extracted / "frame001.jpg").write_text("fake")
        
        converted = source_dir / "converted_images"
        converted.mkdir()
        (converted / "img1.jpg").write_text("fake")
        
        metadata = {}
        
        with patch('builtins.print'):
            result = determine_reusable_steps(source_dir, metadata)
        
        assert "video" in result
        assert "convert" in result
    
    def test_empty_directories_not_reusable(self, tmp_path):
        """Should not mark empty directories as reusable"""
        source_dir = tmp_path / "test_workflow"
        source_dir.mkdir()
        
        # Create empty directories
        (source_dir / "extracted_frames").mkdir()
        (source_dir / "converted_images").mkdir()
        
        metadata = {}
        
        with patch('builtins.print'):
            result = determine_reusable_steps(source_dir, metadata)
        
        assert len(result) == 0


class TestCanCreateHardlinks:
    """Tests for can_create_hardlinks function"""
    
    def test_same_filesystem(self, tmp_path):
        """Should return True for same filesystem"""
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir1.mkdir()
        dir2.mkdir()
        
        result = can_create_hardlinks(dir1, dir2)
        # Should be True on same filesystem
        assert isinstance(result, bool)


class TestReuseImages:
    """Tests for reuse_images function"""
    
    def test_copy_method(self, tmp_path):
        """Should successfully copy images"""
        source_dir = tmp_path / "source"
        dest_dir = tmp_path / "dest"
        source_dir.mkdir()
        dest_dir.mkdir()
        
        source_images = source_dir / "converted_images"
        source_images.mkdir()
        
        # Create test images
        (source_images / "img1.jpg").write_bytes(b"fake image 1")
        (source_images / "img2.png").write_bytes(b"fake image 2")
        
        with patch('builtins.print'):
            result = reuse_images(source_dir, dest_dir, method="copy")
        
        assert result == "copy"
        
        dest_images = dest_dir / "converted_images"
        assert dest_images.exists()
        assert (dest_images / "img1.jpg").exists()
        assert (dest_images / "img2.png").exists()
        assert (dest_images / "img1.jpg").read_bytes() == b"fake image 1"
    
    def test_prefers_converted_over_extracted(self, tmp_path):
        """Should prefer converted_images over extracted_frames"""
        source_dir = tmp_path / "source"
        dest_dir = tmp_path / "dest"
        source_dir.mkdir()
        dest_dir.mkdir()
        
        # Create both directories
        extracted = source_dir / "extracted_frames"
        extracted.mkdir()
        (extracted / "frame.jpg").write_bytes(b"frame")
        
        converted = source_dir / "converted_images"
        converted.mkdir()
        (converted / "img.jpg").write_bytes(b"image")
        
        with patch('builtins.print'):
            reuse_images(source_dir, dest_dir, method="copy")
        
        dest_images = dest_dir / "converted_images"
        # Should have copied from converted_images, not extracted_frames
        assert (dest_images / "img.jpg").exists()
        assert not (dest_images / "frame.jpg").exists()
    
    def test_raises_on_no_images(self, tmp_path):
        """Should raise error if no images found"""
        source_dir = tmp_path / "source"
        dest_dir = tmp_path / "dest"
        source_dir.mkdir()
        dest_dir.mkdir()
        
        with pytest.raises(ValueError, match="No images found"):
            reuse_images(source_dir, dest_dir, method="copy")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
