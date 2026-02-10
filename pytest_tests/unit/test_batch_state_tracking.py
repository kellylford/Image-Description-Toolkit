"""
Unit tests for batch processing state tracking in data models

Tests Phase 1: Data Model & State Tracking
- ImageItem processing state fields
- ImageWorkspace batch_state field
- Backward compatibility with old workspace files
"""

import pytest
import json
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'imagedescriber'))

from imagedescriber.data_models import ImageItem, ImageWorkspace, ImageDescription


def test_image_item_new_fields():
    """Test that ImageItem has new processing state fields"""
    item = ImageItem("/path/to/image.jpg")
    
    # Check new fields exist and default to None
    assert hasattr(item, 'processing_state')
    assert item.processing_state is None
    
    assert hasattr(item, 'processing_error')
    assert item.processing_error is None
    
    assert hasattr(item, 'batch_queue_position')
    assert item.batch_queue_position is None


def test_image_item_serialization():
    """Test that ImageItem serializes new fields"""
    item = ImageItem("/path/to/image.jpg")
    item.processing_state = "pending"
    item.processing_error = "Test error"
    item.batch_queue_position = 5
    
    # Serialize
    data = item.to_dict()
    
    # Check fields are in dict
    assert 'processing_state' in data
    assert data['processing_state'] == "pending"
    
    assert 'processing_error' in data
    assert data['processing_error'] == "Test error"
    
    assert 'batch_queue_position' in data
    assert data['batch_queue_position'] == 5


def test_image_item_deserialization():
    """Test that ImageItem deserializes new fields"""
    data = {
        "file_path": "/path/to/image.jpg",
        "item_type": "image",
        "descriptions": [],
        "batch_marked": False,
        "parent_video": None,
        "extracted_frames": [],
        "display_name": "",
        "processing_state": "paused",
        "processing_error": "Network timeout",
        "batch_queue_position": 3
    }
    
    # Deserialize
    item = ImageItem.from_dict(data)
    
    # Check fields are restored
    assert item.processing_state == "paused"
    assert item.processing_error == "Network timeout"
    assert item.batch_queue_position == 3


def test_image_item_backward_compatibility():
    """Test that old workspace files without new fields load correctly"""
    # Old workspace format (missing new fields)
    old_data = {
        "file_path": "/path/to/image.jpg",
        "item_type": "image",
        "descriptions": [],
        "batch_marked": False,
        "parent_video": None,
        "extracted_frames": [],
        "display_name": ""
        # NOTE: Missing processing_state, processing_error, batch_queue_position
    }
    
    # Should load without error
    item = ImageItem.from_dict(old_data)
    
    # New fields should default to None
    assert item.processing_state is None
    assert item.processing_error is None
    assert item.batch_queue_position is None


def test_workspace_batch_state_field():
    """Test that ImageWorkspace has batch_state field"""
    workspace = ImageWorkspace()
    
    # Check field exists and defaults to None
    assert hasattr(workspace, 'batch_state')
    assert workspace.batch_state is None


def test_workspace_batch_state_serialization():
    """Test that ImageWorkspace serializes batch_state"""
    workspace = ImageWorkspace()
    workspace.batch_state = {
        "provider": "claude",
        "model": "claude-opus-4",
        "prompt_style": "detailed",
        "total_queued": 20,
        "started": "2026-02-10T12:00:00"
    }
    
    # Serialize
    data = workspace.to_dict()
    
    # Check field is in dict
    assert 'batch_state' in data
    assert data['batch_state']['provider'] == "claude"
    assert data['batch_state']['total_queued'] == 20


def test_workspace_batch_state_deserialization():
    """Test that ImageWorkspace deserializes batch_state"""
    data = {
        "version": "3.0",
        "directory_path": "",
        "directory_paths": [],
        "items": {},
        "chat_sessions": {},
        "imported_workflow_dir": None,
        "cached_ollama_models": None,
        "batch_state": {
            "provider": "openai",
            "model": "gpt-4o",
            "prompt_style": "narrative",
            "total_queued": 15
        },
        "created": "2026-02-10T12:00:00",
        "modified": "2026-02-10T12:00:00"
    }
    
    # Deserialize
    workspace = ImageWorkspace.from_dict(data)
    
    # Check field is restored
    assert workspace.batch_state is not None
    assert workspace.batch_state['provider'] == "openai"
    assert workspace.batch_state['total_queued'] == 15


def test_workspace_backward_compatibility():
    """Test that old workspace files without batch_state load correctly"""
    # Old workspace format (missing batch_state)
    old_data = {
        "version": "3.0",
        "directory_path": "",
        "directory_paths": [],
        "items": {},
        "chat_sessions": {},
        "created": "2026-02-10T12:00:00",
        "modified": "2026-02-10T12:00:00"
        # NOTE: Missing batch_state
    }
    
    # Should load without error
    workspace = ImageWorkspace.from_dict(old_data)
    
    # batch_state should default to None
    assert workspace.batch_state is None


def test_full_workflow_roundtrip():
    """Test complete save/load cycle with batch processing state"""
    # Create workspace with items in various states
    workspace = ImageWorkspace()
    
    # Add items with different states
    item1 = ImageItem("/path/to/image1.jpg")
    item1.processing_state = "completed"
    item1.add_description(ImageDescription("A beautiful sunset", "gpt-4o", "narrative"))
    workspace.add_item(item1)
    
    item2 = ImageItem("/path/to/image2.jpg")
    item2.processing_state = "pending"
    item2.batch_queue_position = 0
    workspace.add_item(item2)
    
    item3 = ImageItem("/path/to/image3.jpg")
    item3.processing_state = "failed"
    item3.processing_error = "API rate limit exceeded"
    item3.batch_queue_position = 1
    workspace.add_item(item3)
    
    # Set batch state
    workspace.batch_state = {
        "provider": "claude",
        "model": "claude-opus-4",
        "total_queued": 3,
        "started": "2026-02-10T12:00:00"
    }
    
    # Serialize to JSON
    data = workspace.to_dict()
    json_str = json.dumps(data, indent=2)
    
    # Deserialize back
    loaded_data = json.loads(json_str)
    loaded_workspace = ImageWorkspace.from_dict(loaded_data)
    
    # Verify batch state
    assert loaded_workspace.batch_state is not None
    assert loaded_workspace.batch_state['provider'] == "claude"
    
    # Verify item states
    loaded_item1 = loaded_workspace.items["/path/to/image1.jpg"]
    assert loaded_item1.processing_state == "completed"
    assert len(loaded_item1.descriptions) == 1
    
    loaded_item2 = loaded_workspace.items["/path/to/image2.jpg"]
    assert loaded_item2.processing_state == "pending"
    assert loaded_item2.batch_queue_position == 0
    
    loaded_item3 = loaded_workspace.items["/path/to/image3.jpg"]
    assert loaded_item3.processing_state == "failed"
    assert loaded_item3.processing_error == "API rate limit exceeded"
    assert loaded_item3.batch_queue_position == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
