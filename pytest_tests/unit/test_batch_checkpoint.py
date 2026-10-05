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
        not_due = Workspace.open(path).batch_state
        assert not_due is None   # not due yet
        w.enqueue_item(path, str(src / "b.jpg"), _gui_item(src / "b.jpg", "b"),
                       state, w.snapshot_seq())
        assert w.flush(5)
        reopened = Workspace.open(path)
        assert reopened.batch_state == state
        assert reopened.has_any_descriptions

    def test_manifest_refresh_keeps_defaults_a_full_save_wrote(self, bundle):
        path, src = bundle
        ws = Workspace.open(path)
        ws.defaults.model = "chosen-model"
        ws.save_manifest()
        w = BundleCheckpointWriter(manifest_every=1)
        w.enqueue_item(path, str(src / "a.jpg"), _gui_item(src / "a.jpg", "a"),
                       {"total_queued": 3}, w.snapshot_seq())
        assert w.flush(5)
        reopened = Workspace.open(path)
        assert reopened.defaults.model == "chosen-model"
        assert reopened.batch_state == {"total_queued": 3}

    def test_same_name_in_another_folder_is_not_overwritten(self, tmp_path):
        """Review finding: a new image whose name matches one already described
        in another folder must get its own sidecar, not take over that one."""
        src = tmp_path / "photos"
        (src / "A").mkdir(parents=True)
        (src / "A" / "x.jpg").write_bytes(b"x")
        ws = Workspace.create(tmp_path / "run.idtw")
        ws.add_source_folder(src)
        a_sub = ws.items()[0].subfolder
        w = BundleCheckpointWriter()
        a = src / "A" / "x.jpg"
        w.enqueue_item(ws.path, str(a), _gui_item(a, "A's desc", subfolder=a_sub),
                       None, w.snapshot_seq())
        # B arrives later (rescan) and has no sidecar yet.
        (src / "B").mkdir()
        b = src / "B" / "x.jpg"
        b.write_bytes(b"x")
        b_sub = str(Path("photos") / "B")
        w.enqueue_item(ws.path, str(b), _gui_item(b, "B's desc", subfolder=b_sub),
                       None, w.snapshot_seq())
        # And once more with no subfolder at all (older GUI items).
        c = src / "C" / "x.jpg"
        c.parent.mkdir()
        c.write_bytes(b"x")
        w.enqueue_item(ws.path, str(c), _gui_item(c, "C's desc"),
                       None, w.snapshot_seq())
        assert w.flush(5)
        by_source = {Path(i.source_path).parent.name: [d.text for d in i.descriptions]
                     for i in ws.items()}
        assert by_source == {"A": ["A's desc"], "B": ["B's desc"], "C": ["C's desc"]}

    def test_stale_job_does_not_put_back_older_batch_state(self, bundle):
        """#345 review: per-video frame checkpoints queue jobs during
        extraction carrying the old batch_state. One still queued when the
        pre-describe full save writes the new batch_state must not restore
        the old one, or a crash then loses (or misdirects) resume."""
        path, src = bundle
        w = BundleCheckpointWriter(manifest_every=1)
        stale_seq = w.snapshot_seq()               # taken before the save
        with w.lock:                                # as _save_bundle does
            ws = Workspace.open(path)
            ws.batch_state = {"total_queued": 9, "provider": "new"}
            ws.save_manifest()
            w.note_manifest(path)
        w.enqueue_item(path, str(src / "a.jpg"), _gui_item(src / "a.jpg", "a"),
                       {"total_queued": 1, "provider": "old"}, stale_seq)
        flushed = w.flush(5)
        assert flushed
        on_disk = Workspace.open(path).batch_state
        assert on_disk["provider"] == "new"
        # A job snapshotted after the save still refreshes it.
        w.enqueue_item(path, str(src / "b.jpg"), _gui_item(src / "b.jpg", "b"),
                       {"total_queued": 9, "provider": "newer"}, w.snapshot_seq())
        flushed = w.flush(5)
        assert flushed
        on_disk = Workspace.open(path).batch_state
        assert on_disk["provider"] == "newer"

    def test_name_index_built_once_and_kept_current(self, bundle, monkeypatch):
        """#345 review: each new item (every extracted frame) used to walk
        all of descriptions/; ~50 ms an item at 30,000 sidecars. The index is
        built once per bundle and updated as the writer saves, so an item it
        wrote under one subfolder is still found by name afterwards."""
        gb = sys.modules[BundleCheckpointWriter.__module__]
        path, src = bundle
        builds = []
        real = gb.sidecar_name_index
        monkeypatch.setattr(gb, "sidecar_name_index",
                            lambda ws: (builds.append(1), real(ws))[1])
        frame = src / "clip_0.00s.jpg"
        frame.write_bytes(b"x")
        w = BundleCheckpointWriter()
        w.enqueue_item(path, str(frame), _gui_item(frame, "first", subfolder="frames/clip"),
                       None, w.snapshot_seq())
        # Same image, no subfolder (an older GUI item): found through the index.
        w.enqueue_item(path, str(frame), _gui_item(frame, "second"),
                       None, w.snapshot_seq())
        flushed = w.flush(5)
        assert flushed
        assert builds == [1]
        mine = [i for i in Workspace(path).items() if i.image == frame.name]
        assert len(mine) == 1 and [d.text for d in mine[0].descriptions] == ["second"]
        # A full save may add sidecars the index lacks: it is rebuilt after one.
        with w.lock:
            w.note_manifest(path)
        w.enqueue_item(path, str(src / "a.jpg"), _gui_item(src / "a.jpg", "a"),
                       None, w.snapshot_seq())
        flushed = w.flush(5)
        assert flushed
        assert builds == [1, 1]

    def test_name_only_lookup_still_finds_the_same_image(self, bundle):
        """A GUI item with no subfolder still updates its own sidecar in a subfolder."""
        path, src = bundle
        w = BundleCheckpointWriter()
        w.enqueue_item(path, str(src / "a.jpg"), _gui_item(src / "a.jpg", "a"),
                       None, w.snapshot_seq())
        assert w.flush(5)
        assert len(Workspace(path).items()) == 3

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


@pytest.fixture
def frame(_frame, bundle, monkeypatch):
    """The frame mid-batch on `bundle`, with a fresh writer and no dialogs."""
    import imagedescriber_wx
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
    monkeypatch.setattr(f, "_checkpointer", BundleCheckpointWriter())
    monkeypatch.setattr(f, "_changed_seq", {})
    for name in ("show_error", "show_warning", "show_info"):
        monkeypatch.setattr(imagedescriber_wx, name, lambda *a, **k: None)
    return f


def test_worker_complete_saves_description_to_bundle(frame, bundle):
    path, src = bundle
    f = frame

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


def test_older_full_save_keeps_a_newer_checkpoint(frame, bundle):
    """A Save that snapshotted before an image finished must not erase it."""
    path, src = bundle
    f = frame
    old_seq = f._checkpointer.snapshot_seq()
    old_dict = f.workspace.to_dict()           # snapshot without the description
    f.on_worker_complete(_completion(src / "a.jpg", "finished during the save"))
    f._flush_checkpoints(5)
    f._save_bundle(ws_dict=old_dict, snap_seq=old_seq)
    assert [d.text for d in _sidecar(path, "a.jpg").descriptions]         == ["finished during the save"]


def test_stop_does_not_leave_batch_state_behind(frame, bundle, monkeypatch):
    """A checkpoint queued just before Stop must not put batch_state back."""
    path, src = bundle
    f = frame
    f._checkpointer.manifest_every = 1          # every checkpoint writes the manifest
    monkeypatch.setattr(f, "batch_worker", SimpleNamespace(stop=lambda: None, is_alive=lambda: False))
    monkeypatch.setattr(f, "batch_progress_dialog", None)
    f.on_worker_complete(_completion(src / "a.jpg", "a"))
    f.on_stop_batch()
    f._flush_checkpoints(5)
    on_disk = Workspace.open(path).batch_state
    assert on_disk is None
    assert [d.text for d in _sidecar(path, "a.jpg").descriptions] == ["a"]


def test_images_finished_during_save_as_reach_the_new_bundle(frame, bundle, monkeypatch):
    """Review finding: Save As builds the new bundle from a snapshot while
    images keep finishing; those must be checkpointed into the new bundle."""
    path, src = bundle
    f = frame
    monkeypatch.setattr(f, "workspace_file", None)   # unsaved when Save As starts
    snap = f._checkpointer.snapshot_seq()
    f.on_worker_complete(_completion(src / "b.jpg", "finished mid Save As"))
    f.workspace_file = path                           # Save As done
    f._recheckpoint_since(snap)
    f._flush_checkpoints(5)
    assert [d.text for d in _sidecar(path, "b.jpg").descriptions] == ["finished mid Save As"]
