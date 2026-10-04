"""Descriptions reach the .idtw bundle as a batch produces them.

ImageDescriber used to hold every description in memory until a batch ended,
so a crash partway through a 10,000-image run lost all of it. The checkpoint
writer saves each finished image's sidecar on a background thread; these tests
cover the writer on its own and the frame's completion handler driving it.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(_ROOT), str(_ROOT / "imagedescriber")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from idt_core.gui_bridge import BundleCheckpointWriter  # noqa: E402
from idt_core.workspace import Workspace  # noqa: E402


def _gui_item(path, text=None, subfolder=None):
    descs = []
    if text is not None:
        descs.append({"id": f"d-{text}", "text": text, "model": "m",
                      "prompt_style": "detailed", "provider": "ollama",
                      "created": "2026-10-04T10:00:00"})
    return {"file_path": str(path), "item_type": "image", "descriptions": descs,
            "subfolder": subfolder, "processing_state": "completed"}


def _sidecar(bundle, name, subfolder=None):
    item = Workspace(bundle).get_item(name, subfolder)
    return item


@pytest.fixture
def bundle(tmp_path):
    src = tmp_path / "photos"
    src.mkdir()
    for n in ("a.jpg", "b.jpg", "c.jpg"):
        (src / n).write_bytes(b"x")
    ws = Workspace.create(tmp_path / "run.idtw")
    ws.add_source_folder(src)
    return ws.path, src


class TestWriter:
    def test_item_written_before_batch_ends(self, bundle):
        path, src = bundle
        w = BundleCheckpointWriter()
        w.enqueue_item(path, str(src / "a.jpg"), _gui_item(src / "a.jpg", "a cat"),
                       {"total_queued": 3}, w.snapshot_seq())
        assert w.flush(5)
        item = _sidecar(path, "a.jpg")
        assert [d.text for d in item.descriptions] == ["a cat"]
        assert item.extra["processing_state"] == "completed"

    def test_manifest_batch_state_refreshed_periodically(self, bundle):
        path, src = bundle
        w = BundleCheckpointWriter(manifest_every=2, manifest_secs=3600)
        state = {"total_queued": 3, "provider": "ollama"}
        w.enqueue_item(path, str(src / "a.jpg"), _gui_item(src / "a.jpg", "a"),
                       state, w.snapshot_seq())
        assert w.flush(5)
        assert Workspace.open(path).batch_state is None   # not due yet
        w.enqueue_item(path, str(src / "b.jpg"), _gui_item(src / "b.jpg", "b"),
                       state, w.snapshot_seq())
        assert w.flush(5)
        reopened = Workspace.open(path)
        assert reopened.batch_state == state
        assert reopened.has_any_descriptions

    def test_manifest_job_writes_now(self, bundle):
        path, _ = bundle
        w = BundleCheckpointWriter(manifest_every=1000, manifest_secs=3600)
        w.enqueue_manifest(path, {"total_queued": 3})
        assert w.flush(5)
        assert Workspace.open(path).batch_state == {"total_queued": 3}

    def test_older_snapshot_never_overwrites_newer(self, bundle):
        path, src = bundle
        w = BundleCheckpointWriter()
        old = w.snapshot_seq()
        new = w.snapshot_seq()
        w.enqueue_item(path, str(src / "a.jpg"), _gui_item(src / "a.jpg", "new"),
                       None, new)
        w.enqueue_item(path, str(src / "a.jpg"), _gui_item(src / "a.jpg", "old"),
                       None, old)
        assert w.flush(5)
        assert [d.text for d in _sidecar(path, "a.jpg").descriptions] == ["new"]

    def test_full_save_claim_respects_checkpoint(self, bundle):
        """A full save that snapshotted before a checkpoint must skip that item."""
        path, src = bundle
        w = BundleCheckpointWriter()
        save_seq = w.snapshot_seq()            # full save snapshots first
        w.enqueue_item(path, str(src / "a.jpg"), _gui_item(src / "a.jpg", "done"),
                       None, w.snapshot_seq())
        assert w.flush(5)
        with w.lock:
            assert not w.claim(path, str(src / "a.jpg"), save_seq)
            assert w.claim(path, str(src / "b.jpg"), save_seq)

    def test_subfolder_item_updates_its_own_sidecar(self, tmp_path):
        src = tmp_path / "photos"
        for sub in ("2024", "2025"):
            (src / sub).mkdir(parents=True)
            (src / sub / "same.jpg").write_bytes(b"x")
        ws = Workspace.create(tmp_path / "run.idtw")
        ws.add_source_folder(src)
        subs = {Path(i.source_path).parent.name: i.subfolder for i in ws.items()}
        w = BundleCheckpointWriter()
        target = src / "2025" / "same.jpg"
        w.enqueue_item(ws.path, str(target),
                       _gui_item(target, "the 2025 one", subfolder=subs["2025"]),
                       None, w.snapshot_seq())
        assert w.flush(5)
        assert [d.text for d in _sidecar(ws.path, "same.jpg", subs["2025"]).descriptions] \
            == ["the 2025 one"]
        assert _sidecar(ws.path, "same.jpg", subs["2024"]).descriptions == []

    def test_missing_bundle_is_not_recreated(self, tmp_path):
        w = BundleCheckpointWriter()
        gone = tmp_path / "gone.idtw"
        w.enqueue_item(gone, str(tmp_path / "a.jpg"), _gui_item(tmp_path / "a.jpg", "x"),
                       None, w.snapshot_seq())
        assert w.flush(5)
        assert not gone.exists()

    def test_bad_job_does_not_stop_writer(self, bundle):
        path, src = bundle
        w = BundleCheckpointWriter()
        w.enqueue_item(path, str(src / "a.jpg"), {"descriptions": [None]},
                       None, w.snapshot_seq())
        w.enqueue_item(path, str(src / "b.jpg"), _gui_item(src / "b.jpg", "b"),
                       None, w.snapshot_seq())
        assert w.flush(5)
        assert w.last_error
        assert [d.text for d in _sidecar(path, "b.jpg").descriptions] == ["b"]


# --------------------------------------------------------------------------- #
# The frame: a finished image is on disk without pressing Save                  #
# --------------------------------------------------------------------------- #

wx = pytest.importorskip("wx", reason="wxPython not installed in this environment")


@pytest.fixture(scope="module")
def _frame():
    import imagedescriber_wx
    app = wx.App.Get() or wx.App(False)
    f = imagedescriber_wx.ImageDescriberFrame()
    yield f
    f.Destroy()
    wx.SafeYield()
    del app


def _completion(path, text):
    return SimpleNamespace(file_path=str(path), description=text, model="m",
                           prompt_style="detailed", custom_prompt=None,
                           provider="ollama", metadata={})


def test_worker_complete_saves_description_to_bundle(_frame, bundle, monkeypatch):
    from data_models import ImageItem, ImageWorkspace
    path, src = bundle
    f = _frame
    ws = ImageWorkspace(new_workspace=True)
    ws.directory_paths = [str(src)]
    for n in ("a.jpg", "b.jpg", "c.jpg"):
        ws.add_item(ImageItem(str(src / n)))
    ws.batch_state = {"total_queued": 3, "provider": "ollama"}
    monkeypatch.setattr(f, "workspace", ws)
    monkeypatch.setattr(f, "workspace_file", path)
    monkeypatch.setattr(f, "_batch_active", True)
    monkeypatch.setattr(f, "_batch_embed", False)

    f.on_worker_complete(_completion(src / "a.jpg", "a red barn"))
    f.on_worker_complete(_completion(src / "b.jpg", "a blue boat"))
    f._flush_checkpoints(5)

    # Read straight from disk — no Save was pressed.
    assert [d.text for d in _sidecar(path, "a.jpg").descriptions] == ["a red barn"]
    assert [d.text for d in _sidecar(path, "b.jpg").descriptions] == ["a blue boat"]
    assert _sidecar(path, "c.jpg").descriptions == []
    # processing_state rides along, so resume after a crash skips this image.
    assert _sidecar(path, "a.jpg").extra["processing_state"] == "completed"

    # A full save afterwards keeps them (the shared conversion path).
    f._save_bundle()
    assert [d.text for d in _sidecar(path, "a.jpg").descriptions] == ["a red barn"]
