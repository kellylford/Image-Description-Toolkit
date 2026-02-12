"""
Unit tests for cached sort date functionality in ImageItem.

Tests the EXIF date caching mechanism that prevents re-reading files
on every refresh_image_list() call (Issue #81 performance fix).
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "imagedescriber"))

from imagedescriber.data_models import ImageItem, ImageWorkspace


class TestCachedSortDateField:
    """Test cached_sort_date field on ImageItem."""
    
    def test_default_is_none(self):
        """New items should have no cached sort date."""
        item = ImageItem("/test/image.jpg")
        assert item.cached_sort_date is None
    
    def test_can_set_iso_date(self):
        """Should accept ISO format date strings."""
        item = ImageItem("/test/image.jpg")
        item.cached_sort_date = "2025-03-15T14:30:00"
        assert item.cached_sort_date == "2025-03-15T14:30:00"
    
    def test_roundtrip_serialization(self):
        """cached_sort_date should survive to_dict/from_dict roundtrip."""
        item = ImageItem("/test/image.jpg", "image")
        item.cached_sort_date = "2025-06-01T10:00:00"
        
        data = item.to_dict()
        assert data["cached_sort_date"] == "2025-06-01T10:00:00"
        
        restored = ImageItem.from_dict(data)
        assert restored.cached_sort_date == "2025-06-01T10:00:00"
    
    def test_backward_compatible_deserialization(self):
        """Items saved without cached_sort_date should load with None."""
        old_data = {
            "file_path": "/test/old_image.jpg",
            "item_type": "image",
            "descriptions": [],
            "batch_marked": False,
            "parent_video": None,
            "extracted_frames": [],
            "display_name": "",
            "video_metadata": None,
        }
        item = ImageItem.from_dict(old_data)
        assert item.cached_sort_date is None
    
    def test_iso_date_can_be_parsed(self):
        """Cached ISO dates should be parseable back to datetime."""
        item = ImageItem("/test/image.jpg")
        test_dt = datetime(2025, 3, 15, 14, 30, 0)
        item.cached_sort_date = test_dt.isoformat()
        
        parsed = datetime.fromisoformat(item.cached_sort_date)
        assert parsed == test_dt
    
    def test_video_item_cached_sort_date(self):
        """Video items should also support cached sort dates."""
        item = ImageItem("/test/video.mp4", "video")
        item.cached_sort_date = "2025-01-01T00:00:00"
        
        data = item.to_dict()
        restored = ImageItem.from_dict(data)
        assert restored.cached_sort_date == "2025-01-01T00:00:00"
        assert restored.item_type == "video"


class TestWorkspaceAddItems:
    """Test bulk add_items() method on ImageWorkspace."""
    
    def test_add_items_basic(self):
        """Should add multiple items at once."""
        ws = ImageWorkspace(new_workspace=True)
        items = [ImageItem(f"/test/{i}.jpg") for i in range(10)]
        ws.add_items(items)
        assert len(ws.items) == 10
    
    def test_add_items_deduplication(self):
        """Should skip items that already exist in workspace."""
        ws = ImageWorkspace(new_workspace=True)
        ws.add_item(ImageItem("/test/existing.jpg"))
        
        new_items = [
            ImageItem("/test/existing.jpg"),  # duplicate
            ImageItem("/test/new1.jpg"),
            ImageItem("/test/new2.jpg"),
        ]
        ws.add_items(new_items)
        assert len(ws.items) == 3  # existing + 2 new
    
    def test_add_items_empty_list(self):
        """Should handle empty list without error."""
        ws = ImageWorkspace(new_workspace=True)
        ws.add_items([])
        assert len(ws.items) == 0
    
    def test_add_items_marks_modified_once(self):
        """Should only mark modified once for bulk add."""
        ws = ImageWorkspace(new_workspace=True)
        ws.saved = True
        
        items = [ImageItem(f"/test/{i}.jpg") for i in range(5)]
        ws.add_items(items)
        
        # Should be marked as not saved
        assert ws.saved is False
    
    def test_add_items_preserves_cached_sort_date(self):
        """Bulk-added items should retain their cached sort dates."""
        ws = ImageWorkspace(new_workspace=True)
        items = []
        for i in range(3):
            item = ImageItem(f"/test/{i}.jpg")
            item.cached_sort_date = f"2025-01-0{i+1}T00:00:00"
            items.append(item)
        
        ws.add_items(items)
        
        for i in range(3):
            assert ws.items[f"/test/{i}.jpg"].cached_sort_date == f"2025-01-0{i+1}T00:00:00"


class TestWorkspaceSortDateRoundtrip:
    """Test that sort dates survive workspace save/load cycle."""
    
    def test_full_workspace_roundtrip(self):
        """Workspace with cached sort dates should serialize/deserialize correctly."""
        ws = ImageWorkspace(new_workspace=True)
        ws.add_directory("/test/photos")
        
        items = []
        for i, date_str in enumerate([
            "2025-01-15T10:30:00",
            "2025-06-20T14:45:00",
            "2024-12-25T08:00:00",
        ]):
            item = ImageItem(f"/test/photos/img_{i}.jpg")
            item.cached_sort_date = date_str
            items.append(item)
        
        ws.add_items(items)
        
        # Serialize
        data = ws.to_dict()
        
        # Deserialize
        ws2 = ImageWorkspace.from_dict(data)
        
        assert len(ws2.items) == 3
        for key in ws.items:
            assert ws2.items[key].cached_sort_date == ws.items[key].cached_sort_date
    
    def test_sort_with_cached_dates(self):
        """Items with cached dates should sort correctly by date."""
        items_data = [
            ("/test/c.jpg", "2025-06-01T00:00:00"),
            ("/test/a.jpg", "2024-01-01T00:00:00"),
            ("/test/b.jpg", "2025-03-15T00:00:00"),
        ]
        
        items = []
        for path, date_str in items_data:
            item = ImageItem(path)
            item.cached_sort_date = date_str
            items.append((path, item))
        
        # Sort using cached dates (same logic as refresh_image_list)
        items.sort(key=lambda x: datetime.fromisoformat(x[1].cached_sort_date))
        
        assert items[0][0] == "/test/a.jpg"  # oldest
        assert items[1][0] == "/test/b.jpg"  # middle
        assert items[2][0] == "/test/c.jpg"  # newest


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
