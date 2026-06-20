"""
Tests for the unified .idtw workspace bundle (idt_core.workspace).

Covers the invariants from docs/design/unified-workspace.md:
  - originals are copied in, never moved or modified
  - collision-safe image naming
  - description / chat round-trips
  - manifest + batch_state persistence across reopen
  - everything lands inside the bundle directory
"""
import hashlib
from pathlib import Path

import pytest

from idt_core.workspace import (
    Workspace,
    WorkspaceItem,
    WorkspaceDescription,
    BUNDLE_EXT,
)


def _make_png(path: Path, color: bytes = b"\x89PNG\r\n\x1a\n") -> None:
    """Write a tiny fake image file (content only needs to be stable bytes)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(color + path.name.encode("utf-8"))


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def src(tmp_path):
    """A source tree with images, including a name collision across subfolders."""
    root = tmp_path / "Pictures" / "Vacation"
    _make_png(root / "beach.jpg")
    _make_png(root / "sunset.jpg")
    _make_png(root / "Day2" / "beach.jpg")  # collides with root beach.jpg
    return root


def test_create_makes_bundle_layout(tmp_path):
    ws = Workspace.create(tmp_path / "MyTrip")
    assert ws.path.name == "MyTrip" + BUNDLE_EXT
    assert ws.manifest_path.is_file()
    assert ws.images_dir.is_dir()
    assert ws.descriptions_dir.is_dir()
    assert Workspace.is_bundle(ws.path)


def test_create_appends_extension_only_once(tmp_path):
    ws = Workspace.create(tmp_path / "Trip.idtw")
    assert ws.path.name == "Trip.idtw"
    assert not ws.path.name.endswith(".idtw.idtw")


def test_add_image_copies_in_and_leaves_original_untouched(tmp_path, src):
    original = src / "beach.jpg"
    before = _digest(original)
    before_mtime = original.stat().st_mtime

    ws = Workspace.create(tmp_path / "WS")
    item = ws.add_image(original)

    # original is byte-for-byte unchanged and not moved
    assert original.exists()
    assert _digest(original) == before
    assert original.stat().st_mtime == before_mtime

    # a copy now lives in the bundle with identical content
    copy = ws.image_path(item)
    assert copy.exists()
    assert _digest(copy) == before
    assert copy.parent == ws.images_dir
    # source path retained as provenance
    assert item.source_path == str(original.resolve())


def test_add_image_is_idempotent(tmp_path, src):
    ws = Workspace.create(tmp_path / "WS")
    a = ws.add_image(src / "beach.jpg")
    b = ws.add_image(src / "beach.jpg")
    assert a.image == b.image
    assert len(list(ws.images_dir.glob("*.jpg"))) == 1


def test_collision_safe_naming(tmp_path, src):
    ws = Workspace.create(tmp_path / "WS")
    a = ws.add_image(src / "beach.jpg", subfolder=None)
    b = ws.add_image(src / "Day2" / "beach.jpg", subfolder="Day2")
    assert a.image != b.image
    assert a.image == "beach.jpg"
    assert b.image == "Day2__beach.jpg"
    # both copies exist independently
    assert (ws.images_dir / a.image).exists()
    assert (ws.images_dir / b.image).exists()


def test_add_source_folder_records_provenance(tmp_path, src):
    ws = Workspace.create(tmp_path / "WS")
    added = ws.add_source_folder(src, recursive=True)
    assert len(added) == 3
    # manifest records the source folder
    assert any(s["path"] == str(src.resolve()) for s in ws.sources)
    # subfolder grouping preserved on the Day2 item
    day2 = next(i for i in ws.items() if i.subfolder == "Day2")
    assert day2.source_path.endswith("beach.jpg")


def test_description_round_trip(tmp_path, src):
    ws = Workspace.create(tmp_path / "WS")
    item = ws.add_image(src / "sunset.jpg")
    desc = WorkspaceDescription.create(
        "A glowing orange sunset over the water.",
        provider="anthropic", model="claude-opus-4-6",
        prompt_name="detailed", input_tokens=1800, output_tokens=300,
        metadata_context="Seattle, Washington  Sep 12, 2025",
    )
    item.add_description(desc)
    ws.save_item(item)

    reloaded = ws.get_item(item.image)
    assert reloaded.described
    assert len(reloaded.descriptions) == 1
    d = reloaded.descriptions[0]
    assert d.text.startswith("A glowing")
    assert d.input_tokens == 1800
    assert d.output_tokens == 300
    assert d.metadata_context == "Seattle, Washington  Sep 12, 2025"
    assert reloaded.active_description_id == desc.id


def test_new_description_clears_embedded_at(tmp_path, src):
    ws = Workspace.create(tmp_path / "WS")
    item = ws.add_image(src / "beach.jpg")
    item.embedded_at = "2026-06-20T00:00:00Z"
    item.add_description(WorkspaceDescription.create("desc"))
    assert item.embedded_at is None


def test_legacy_description_field_aliases(tmp_path):
    """from_dict accepts the GUI's prompt_style/custom_prompt/timestamp aliases."""
    d = WorkspaceDescription.from_dict({
        "id": "x", "text": "t",
        "prompt_style": "narrative", "custom_prompt": "custom",
        "timestamp": "2026-01-01T00:00:00Z",
    })
    assert d.prompt_name == "narrative"
    assert d.prompt_text == "custom"
    assert d.created == "2026-01-01T00:00:00Z"


def test_chat_round_trip(tmp_path):
    ws = Workspace.create(tmp_path / "WS")
    ws.save_chat({
        "id": "chat_1", "name": "Test chat", "image": None,
        "provider": "anthropic", "model": "claude-opus-4-6",
        "messages": [{"id": "m1", "text": "hello", "prompt_name": "user_question"}],
    })
    chats = ws.chats()
    assert len(chats) == 1
    assert chats[0]["name"] == "Test chat"
    ws.delete_chat("chat_1")
    assert ws.chats() == []


def test_manifest_and_batch_state_persist_across_reopen(tmp_path, src):
    ws = Workspace.create(tmp_path / "WS", name="My Trip")
    ws.add_image(src / "beach.jpg")
    ws.defaults.provider = "ollama"
    ws.defaults.model = "llava"
    ws.geocode_enabled = True
    ws.batch_state = {"provider": "ollama", "model": "llava", "paused_at_index": 3,
                      "geocode_enabled": True}
    ws.save_manifest()

    reopened = Workspace.open(ws.path)
    assert reopened.name == "My Trip"
    assert reopened.defaults.provider == "ollama"
    assert reopened.defaults.model == "llava"
    assert reopened.geocode_enabled is True
    assert reopened.batch_state["paused_at_index"] == 3
    # item survives reopen too
    assert reopened.status()["total"] == 1


def test_open_nonexistent_creates(tmp_path):
    p = tmp_path / "Fresh"
    ws = Workspace.open(p)
    assert Workspace.is_bundle(ws.path)


def test_everything_lands_inside_bundle(tmp_path, src):
    """No file is written outside the .idtw directory during normal use."""
    ws = Workspace.create(tmp_path / "WS")
    ws.add_source_folder(src, recursive=True)
    item = ws.items()[0]
    item.add_description(WorkspaceDescription.create("d"))
    ws.save_item(item)
    ws.save_chat({"id": "c1", "messages": []})

    # Only the source tree and the bundle exist under tmp_path; nothing stray.
    bundle = ws.path
    for f in bundle.rglob("*"):
        assert bundle in f.parents or f == bundle
    # original source files still present
    assert (src / "beach.jpg").exists()
