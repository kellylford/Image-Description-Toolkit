"""
gui_bridge — GUI workspace dict <-> .idtw bundle round-trips.

Where possible these use the REAL GUI data model (imagedescriber.data_models) so
a shape drift between the two is caught. The GUI package imports cleanly without
wx for the pure data classes.
"""
import sys
from pathlib import Path

import pytest

from idt_core.workspace import Workspace
from idt_core.gui_bridge import (
    gui_workspace_to_bundle,
    bundle_to_gui_workspace_dict,
    _gui_desc_to_ws,
    _ws_desc_to_gui,
)

# Make the GUI data model importable (it lives in imagedescriber/)
_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "imagedescriber"))


def _make_jpeg(path: Path, color=(120, 60, 200)):
    from PIL import Image
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (16, 16), color).save(path, "JPEG")


@pytest.fixture
def gui_workspace(tmp_path):
    """Build a real GUI ImageWorkspace with an image, descriptions, and a chat."""
    from data_models import ImageWorkspace, ImageItem, ImageDescription

    src_dir = tmp_path / "Photos"
    _make_jpeg(src_dir / "a.jpg")
    _make_jpeg(src_dir / "b.jpg", (10, 200, 30))

    ws = ImageWorkspace(new_workspace=True)
    ws.add_directory(str(src_dir))

    a = ImageItem(str(src_dir / "a.jpg"))
    a.subfolder = None
    a.exif_datetime = "2025-09-12T08:03:00"
    a.add_description(ImageDescription(
        text="A purple square.", model="gpt-4o", prompt_style="detailed",
        provider="openai", metadata={"prompt_context": "Seattle  Sep 12, 2025"},
        token_usage={"prompt_tokens": 1000, "completion_tokens": 200, "total_tokens": 1200},
    ))
    ws.add_item(a)

    b = ImageItem(str(src_dir / "b.jpg"))
    b.batch_marked = True
    b.processing_state = "completed"
    ws.add_item(b)

    # A chat session (migrated into an item by from_dict in the GUI; here we add
    # it as a chat item directly)
    chat = ImageItem("chat:chat_123", item_type=ImageItem.ITEM_TYPE_CHAT)
    chat.display_name = "Chat about a.jpg"
    chat.add_description(ImageDescription(text="What is this?", prompt_style="user_question",
                                          provider="openai", model="gpt-4o"))
    chat.add_description(ImageDescription(text="A purple square.", prompt_style="ai_response",
                                          provider="openai", model="gpt-4o"))
    ws.add_item(chat)

    ws.batch_state = {"provider": "openai", "model": "gpt-4o", "paused_at_index": 1}
    ws.cached_ollama_models = ["llava", "moondream"]
    return ws, src_dir


def test_gui_to_bundle_copies_images_and_leaves_originals(tmp_path, gui_workspace):
    ws, src_dir = gui_workspace
    a_before = (src_dir / "a.jpg").read_bytes()

    bundle = gui_workspace_to_bundle(ws.to_dict(), tmp_path / "Trip")

    # images copied in, originals untouched
    assert (bundle.images_dir / "a.jpg").exists()
    assert (bundle.images_dir / "b.jpg").exists()
    assert (src_dir / "a.jpg").read_bytes() == a_before

    # descriptions persisted
    described = [i for i in bundle.items() if i.described]
    assert len(described) == 1  # only a.jpg has a description
    d = described[0].active_description
    assert d.text == "A purple square."
    assert d.prompt_name == "detailed"
    assert d.input_tokens == 1000
    assert d.output_tokens == 200
    assert d.metadata_context == "Seattle  Sep 12, 2025"

    # chat written to chats/
    chats = bundle.chats()
    assert len(chats) == 1
    assert chats[0]["name"] == "Chat about a.jpg"
    assert len(chats[0]["messages"]) == 2

    # manifest carried batch_state + cached models
    assert bundle.batch_state["paused_at_index"] == 1
    assert bundle.cached_ollama_models == ["llava", "moondream"]


def test_bundle_to_gui_dict_loads_in_real_workspace(tmp_path, gui_workspace):
    from data_models import ImageWorkspace

    ws, src_dir = gui_workspace
    bundle = gui_workspace_to_bundle(ws.to_dict(), tmp_path / "Trip")

    gui_dict = bundle_to_gui_workspace_dict(bundle)
    # The real GUI loader must accept it without raising
    reloaded = ImageWorkspace.from_dict(gui_dict)

    # image items point at the bundle copies and the description survived
    image_items = [i for i in reloaded.items.values() if i.item_type != "chat"]
    assert len(image_items) == 2
    described = [i for i in image_items if i.descriptions]
    assert len(described) == 1
    assert described[0].descriptions[0].text == "A purple square."
    assert described[0].descriptions[0].prompt_style == "detailed"

    # batch state preserved
    assert reloaded.batch_state["paused_at_index"] == 1


def test_gui_only_item_fields_round_trip(tmp_path, gui_workspace):
    ws, src_dir = gui_workspace
    bundle = gui_workspace_to_bundle(ws.to_dict(), tmp_path / "Trip")

    # b.jpg had batch_marked + processing_state — preserved in item.extra
    b = next(i for i in bundle.items() if i.image == "b.jpg")
    assert b.extra.get("batch_marked") is True
    assert b.extra.get("processing_state") == "completed"

    # and they come back in the GUI dict
    gui_dict = bundle_to_gui_workspace_dict(bundle)
    b_path = str(bundle.images_dir / "b.jpg")
    assert gui_dict["items"][b_path]["batch_marked"] is True
    assert gui_dict["items"][b_path]["processing_state"] == "completed"


def test_description_field_mapping_is_lossless():
    gui_desc = {
        "id": "111", "text": "hi", "model": "gpt-4o", "prompt_style": "brief",
        "created": "2026-01-01T00:00:00", "custom_prompt": "be brief",
        "provider": "openai", "detection_data": [],
        "metadata": {"prompt_context": "ctx", "camera": "iPhone"},
        "finish_reason": "stop", "response_id": "resp_1",
        "token_usage": {"prompt_tokens": 5, "completion_tokens": 7, "total_tokens": 12},
        "completion_tokens": 7,
    }
    w = _gui_desc_to_ws(gui_desc)
    assert w.prompt_name == "brief"
    assert w.prompt_text == "be brief"
    assert w.input_tokens == 5
    assert w.output_tokens == 7
    assert w.metadata_context == "ctx"

    back = _ws_desc_to_gui(w)
    assert back["prompt_style"] == "brief"
    assert back["custom_prompt"] == "be brief"
    assert back["metadata"]["camera"] == "iPhone"
    assert back["token_usage"]["completion_tokens"] == 7
    assert back["finish_reason"] == "stop"
    assert back["response_id"] == "resp_1"


def test_missing_file_does_not_crash(tmp_path):
    """An item whose file no longer exists is registered without a copy."""
    gui_dict = {
        "version": "3.0",
        "directory_paths": [str(tmp_path / "gone")],
        "items": {
            str(tmp_path / "gone" / "x.jpg"): {
                "file_path": str(tmp_path / "gone" / "x.jpg"),
                "item_type": "image",
                "descriptions": [],
                "is_missing": True,
            }
        },
    }
    bundle = gui_workspace_to_bundle(gui_dict, tmp_path / "WS")
    items = bundle.items()
    assert len(items) == 1
    assert items[0].is_missing is True
