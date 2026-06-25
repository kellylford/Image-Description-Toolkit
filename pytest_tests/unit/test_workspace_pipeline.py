"""
WorkspacePipeline — describe-to-bundle data flow, validated with a fake provider
(no network / no real model needed).
"""
from pathlib import Path

import pytest

from idt_core.workspace import Workspace
from idt_core.pipeline import WorkspacePipeline, RunOptions
from idt_core.providers.base import DescriptionResult


class FakeProvider:
    """Returns a deterministic description; records how many times it was called."""
    def __init__(self):
        self.calls = 0

    @property
    def provider_name(self) -> str:
        return "fake"

    @property
    def model_name(self) -> str:
        return "fake-1"

    def describe(self, image_bytes, mime_type, prompt):
        self.calls += 1
        return DescriptionResult(
            text=f"Description #{self.calls} (prompt len {len(prompt)})",
            provider="fake",
            model="fake-1",
            input_tokens=100,
            output_tokens=20,
        )


def _make_jpeg(path: Path):
    """Write a minimal valid-enough JPEG (Pillow can open it for EXIF extraction)."""
    from PIL import Image
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (16, 16), (123, 80, 200)).save(path, "JPEG")


@pytest.fixture
def src(tmp_path):
    root = tmp_path / "Pics"
    _make_jpeg(root / "a.jpg")
    _make_jpeg(root / "b.jpg")
    return root


def test_describe_writes_into_bundle_and_leaves_originals(tmp_path, src):
    a_before = (src / "a.jpg").read_bytes()

    ws = Workspace.create(tmp_path / "WS")
    ws.add_source_folder(src, recursive=True)

    provider = FakeProvider()
    pipeline = WorkspacePipeline(ws, provider)
    events = list(pipeline.run(RunOptions(prompt_name="detailed", prompt_text="Describe.")))

    assert len(events) == 2
    assert all(e.success for e in events)
    assert provider.calls == 2

    # descriptions persisted in the bundle
    described = [i for i in ws.items() if i.described]
    assert len(described) == 2
    assert described[0].active_description.text.startswith("Description #")
    assert described[0].active_description.provider == "fake"

    # originals untouched
    assert (src / "a.jpg").read_bytes() == a_before


def test_describe_skips_already_described(tmp_path, src):
    ws = Workspace.create(tmp_path / "WS")
    ws.add_source_folder(src, recursive=True)
    provider = FakeProvider()

    list(WorkspacePipeline(ws, provider).run(RunOptions(prompt_text="x")))
    assert provider.calls == 2

    # second run with redescribe=False should describe nothing new
    list(WorkspacePipeline(ws, provider).run(RunOptions(prompt_text="x")))
    assert provider.calls == 2  # unchanged


def test_redescribe_adds_second_description(tmp_path, src):
    ws = Workspace.create(tmp_path / "WS")
    ws.add_source_folder(src, recursive=True)
    provider = FakeProvider()

    list(WorkspacePipeline(ws, provider).run(RunOptions(prompt_text="x")))
    list(WorkspacePipeline(ws, provider).run(RunOptions(prompt_text="x", redescribe=True)))

    item = ws.items()[0]
    assert len(item.descriptions) == 2


def test_limit_caps_run(tmp_path, src):
    ws = Workspace.create(tmp_path / "WS")
    ws.add_source_folder(src, recursive=True)
    provider = FakeProvider()
    events = list(WorkspacePipeline(ws, provider).run(RunOptions(prompt_text="x", limit=1)))
    assert len(events) == 1
    assert provider.calls == 1


def test_metadata_context_stored_when_present(tmp_path, src):
    # EXIF extraction is on by default; our tiny JPEGs have no GPS/date so context
    # is empty, but the run must still succeed and store a description.
    ws = Workspace.create(tmp_path / "WS")
    ws.add_source_folder(src, recursive=True)
    events = list(WorkspacePipeline(ws, FakeProvider()).run(
        RunOptions(prompt_text="x", extract_metadata=True)))
    assert all(e.success for e in events)
