"""
Unit tests for chat-as-first-class-item data model changes.

Phase 1 verification:
- ImageDescription.token_usage field serialization
- ImageItem.ITEM_TYPE_CHAT constant
- ImageWorkspace.migrate_chat_sessions() correctness and idempotency
"""
import sys
import os
from datetime import datetime

# Ensure imagedescriber package is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'imagedescriber'))

from data_models import ImageDescription, ImageItem, ImageWorkspace


class TestImageDescriptionTokenUsage:
    """Test that token_usage field is correctly stored and serialized."""

    def test_default_token_usage_is_empty_dict(self):
        desc = ImageDescription(text="hello")
        assert desc.token_usage == {}

    def test_token_usage_stored(self):
        usage = {'prompt_tokens': 100, 'completion_tokens': 50, 'total_tokens': 150}
        desc = ImageDescription(text="hello", token_usage=usage)
        assert desc.token_usage == usage

    def test_token_usage_in_to_dict_when_non_empty(self):
        usage = {'prompt_tokens': 10, 'completion_tokens': 5, 'total_tokens': 15}
        desc = ImageDescription(text="hello", token_usage=usage)
        d = desc.to_dict()
        assert 'token_usage' in d
        assert d['token_usage'] == usage

    def test_token_usage_not_in_to_dict_when_empty(self):
        desc = ImageDescription(text="hello", token_usage={})
        d = desc.to_dict()
        # Empty token_usage is falsy, so it's not included
        assert 'token_usage' not in d

    def test_token_usage_roundtrip(self):
        usage = {'prompt_tokens': 200, 'completion_tokens': 75, 'total_tokens': 275}
        desc = ImageDescription(text="test text", token_usage=usage)
        d = desc.to_dict()
        restored = ImageDescription.from_dict(d)
        assert restored.token_usage == usage

    def test_from_dict_missing_token_usage_defaults_to_empty(self):
        d = {"text": "hello", "model": "gpt-4"}
        desc = ImageDescription.from_dict(d)
        assert desc.token_usage == {}

    def test_none_token_usage_treated_as_empty(self):
        desc = ImageDescription(text="hello", token_usage=None)
        assert desc.token_usage == {}


class TestImageItemChatConstant:
    """Test ImageItem.ITEM_TYPE_CHAT class constant."""

    def test_constant_value(self):
        assert ImageItem.ITEM_TYPE_CHAT == "chat"

    def test_chat_item_type(self):
        item = ImageItem(file_path="chat:abc123", item_type=ImageItem.ITEM_TYPE_CHAT)
        assert item.item_type == "chat"

    def test_constant_accessible_on_instance(self):
        item = ImageItem(file_path="chat:abc123", item_type="chat")
        assert item.ITEM_TYPE_CHAT == "chat"


class TestMigrateChatSessions:
    """Test ImageWorkspace.migrate_chat_sessions()."""

    def _make_workspace_with_legacy_sessions(self):
        """Return a workspace dict with legacy chat_sessions entries."""
        return {
            "version": "3.0",
            "directory_paths": [],
            "directory_path": "",
            "items": {},
            "chat_sessions": {
                "chat_1234": {
                    "id": "chat_1234",
                    "name": "Test Chat",
                    "provider": "claude",
                    "model": "claude-opus-4-6",
                    "created": "2026-05-09T10:00:00",
                    "modified": "2026-05-09T10:05:00",
                    "messages": [
                        {
                            "role": "user",
                            "content": "What is in this photo?",
                            "timestamp": "2026-05-09T10:01:00"
                        },
                        {
                            "role": "assistant",
                            "content": "The photo shows a coastal town.",
                            "timestamp": "2026-05-09T10:01:05",
                            "metadata": {},
                            "token_usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
                        }
                    ]
                }
            },
            "created": "2026-05-09T10:00:00",
            "modified": "2026-05-09T10:05:00"
        }

    def test_migration_creates_chat_item(self):
        data = self._make_workspace_with_legacy_sessions()
        ws = ImageWorkspace.from_dict(data)
        assert "chat:chat_1234" in ws.items

    def test_migration_clears_chat_sessions(self):
        data = self._make_workspace_with_legacy_sessions()
        ws = ImageWorkspace.from_dict(data)
        assert ws.chat_sessions == {}

    def test_migrated_item_has_correct_type(self):
        data = self._make_workspace_with_legacy_sessions()
        ws = ImageWorkspace.from_dict(data)
        item = ws.items["chat:chat_1234"]
        assert item.item_type == "chat"

    def test_migrated_item_display_name(self):
        data = self._make_workspace_with_legacy_sessions()
        ws = ImageWorkspace.from_dict(data)
        item = ws.items["chat:chat_1234"]
        assert item.display_name == "Test Chat"

    def test_migrated_item_has_descriptions(self):
        data = self._make_workspace_with_legacy_sessions()
        ws = ImageWorkspace.from_dict(data)
        item = ws.items["chat:chat_1234"]
        assert len(item.descriptions) == 2

    def test_migrated_user_message_prompt_style(self):
        data = self._make_workspace_with_legacy_sessions()
        ws = ImageWorkspace.from_dict(data)
        item = ws.items["chat:chat_1234"]
        user_desc = item.descriptions[0]
        assert user_desc.prompt_style == "user_question"
        assert user_desc.text == "What is in this photo?"

    def test_migrated_ai_message_prompt_style(self):
        data = self._make_workspace_with_legacy_sessions()
        ws = ImageWorkspace.from_dict(data)
        item = ws.items["chat:chat_1234"]
        ai_desc = item.descriptions[1]
        assert ai_desc.prompt_style == "ai_response"
        assert ai_desc.text == "The photo shows a coastal town."

    def test_migrated_ai_message_token_usage(self):
        data = self._make_workspace_with_legacy_sessions()
        ws = ImageWorkspace.from_dict(data)
        item = ws.items["chat:chat_1234"]
        ai_desc = item.descriptions[1]
        assert ai_desc.token_usage == {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}

    def test_migration_is_idempotent(self):
        """Running migrate_chat_sessions() twice must not create duplicates."""
        data = self._make_workspace_with_legacy_sessions()
        ws = ImageWorkspace.from_dict(data)
        # Manually re-add a legacy session to simulate calling migration again
        ws.chat_sessions = {
            "chat_1234": {
                "id": "chat_1234",
                "name": "Test Chat (duplicate)",
                "provider": "claude",
                "model": "claude-opus-4-6",
                "created": "2026-05-09T10:00:00",
                "modified": "2026-05-09T10:05:00",
                "messages": []
            }
        }
        ws.migrate_chat_sessions()
        # Should still have exactly one chat item (the original, not the duplicate)
        chat_items = [k for k in ws.items if k.startswith("chat:")]
        assert len(chat_items) == 1
        # Display name should be the original, not the duplicate
        assert ws.items["chat:chat_1234"].display_name == "Test Chat"

    def test_workspace_with_no_legacy_sessions(self):
        """Workspace with no chat_sessions should remain unchanged."""
        ws = ImageWorkspace()
        ws.chat_sessions = {}
        ws.migrate_chat_sessions()
        assert ws.chat_sessions == {}
        chat_items = [k for k in ws.items if k.startswith("chat:")]
        assert len(chat_items) == 0

    def test_migration_preserves_existing_image_items(self):
        """Image items in workspace.items must not be affected by migration."""
        data = self._make_workspace_with_legacy_sessions()
        data["items"] = {
            "/path/to/photo.jpg": {
                "file_path": "/path/to/photo.jpg",
                "item_type": "image",
                "descriptions": [],
                "batch_marked": False,
                "parent_video": None,
                "extracted_frames": [],
                "display_name": "",
                "video_metadata": None,
                "is_missing": False
            }
        }
        ws = ImageWorkspace.from_dict(data)
        assert "/path/to/photo.jpg" in ws.items
        assert ws.items["/path/to/photo.jpg"].item_type == "image"
        assert "chat:chat_1234" in ws.items

    def test_migration_provider_and_model_on_descriptions(self):
        data = self._make_workspace_with_legacy_sessions()
        ws = ImageWorkspace.from_dict(data)
        item = ws.items["chat:chat_1234"]
        for desc in item.descriptions:
            assert desc.provider == "claude"
            assert desc.model == "claude-opus-4-6"
