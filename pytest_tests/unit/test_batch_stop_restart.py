"""Stop and restart of a batch that extracts video frames.

Reported: start a batch with videos, Stop it, then Process > Describe All
Undescribed. Frames were extracted a second time and describing failed with
"file not found". Reproduced in dev mode; the causes, each pinned here:

- Stop did nothing while frames were being extracted (no describe worker
  existed yet), so the run carried on into describing.
- Nothing stopped a second run starting meanwhile. Its extraction cleared the
  video's frame folder, deleting frames the first run was about to describe.
- Stop during the pre-describe save left describing to call .start() on None.
- Frames were persisted as storage="copy" without being copied, so after the
  workspace was reopened every frame resolved to a file that does not exist.
- A stopped worker's completion event re-ran the whole completion path.
"""

import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(_ROOT), str(_ROOT / "imagedescriber")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from idt_core.gui_bridge import (  # noqa: E402
    BundleCheckpointWriter, bundle_to_gui_workspace_dict, gui_item_to_ws_item,
)
from idt_core.workspace import Workspace, WorkspaceItem  # noqa: E402


# --------------------------------------------------------------------------- #
# Bundle layer (no wx)                                                         #
# --------------------------------------------------------------------------- #

def test_frame_recorded_as_copy_but_never_copied_still_resolves(tmp_path):
    """Bundles written by the old code must keep working after the fix."""
    ws = Workspace.create(tmp_path / "w.idtw")
    frame = ws.derived_dir("frames/clip")
    frame.mkdir(parents=True)
    f = frame / "clip_5.00s.jpg"
    f.write_bytes(b"x")
    item = WorkspaceItem(image=f.name, source_path=str(f), storage="copy",
                         item_type="extracted_frame")
    ws.save_item(item)
    assert ws.image_path(ws.get_item(f.name)) == f


def test_real_copy_still_preferred(tmp_path):
    src = tmp_path / "a.jpg"
    src.write_bytes(b"x")
    ws = Workspace.create(tmp_path / "w.idtw", copy_originals=True)
    wi = ws.add_image(src)
    assert ws.image_path(wi) == ws.images_dir / "a.jpg"


def test_new_item_keeps_parent_video_and_video_metadata(tmp_path):
    ws = Workspace.create(tmp_path / "w.idtw")
    frame = tmp_path / "clip_5.00s.jpg"
    frame.write_bytes(b"x")
    wi = gui_item_to_ws_item(ws, str(frame), {
        "item_type": "extracted_frame", "parent_video": "C:/v/clip.mp4",
        "descriptions": [], "video_metadata": None})
    assert wi.storage == "reference" and wi.parent_video == "C:/v/clip.mp4"
    vid = tmp_path / "clip.mp4"
    vid.write_bytes(b"x")
    wv = gui_item_to_ws_item(ws, str(vid), {
        "item_type": "video", "descriptions": [], "video_metadata": {"fps": 30}})
    ws.save_item(wv)
    again = gui_item_to_ws_item(ws, str(vid), {
        "item_type": "video", "descriptions": [], "video_metadata": {"fps": 25}})
    assert again.video_metadata == {"fps": 25}


# --------------------------------------------------------------------------- #
# The frame                                                                   #
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


def _pump_until(cond, timeout=10.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        wx.SafeYield()
        if cond():
            return True
        time.sleep(0.02)
    return cond()


class _FakeWorker:
    """Stands in for BatchProcessingWorker; records whether it was started."""
    instances = []

    def __init__(self, *a, **k):
        self.started = False
        self.stopped = False
        _FakeWorker.instances.append(self)

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def is_alive(self):
        return self.started and not self.stopped

    def is_paused(self):
        return False


OPTIONS = {"provider": "ollama", "model": "m", "prompt_style": "detailed",
           "custom_prompt": ""}


@pytest.fixture
def frame(_frame, tmp_path, monkeypatch):
    import imagedescriber_wx
    from data_models import ImageItem, ImageWorkspace
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.jpg").write_bytes(b"x")
    (src / "clip.mp4").write_bytes(b"x")
    bundle = Workspace.create(tmp_path / "run.idtw")
    ws = ImageWorkspace(new_workspace=True)
    ws.directory_paths = [str(src)]
    ws.add_item(ImageItem(str(src / "a.jpg")))
    ws.add_item(ImageItem(str(src / "clip.mp4"), "video"))
    f = _frame
    monkeypatch.setattr(f, "workspace", ws)
    monkeypatch.setattr(f, "workspace_file", bundle.path)
    monkeypatch.setattr(f, "_checkpointer", BundleCheckpointWriter())
    monkeypatch.setattr(f, "_changed_seq", {})
    monkeypatch.setattr(f, "_run_cancel", None)
    monkeypatch.setattr(f, "_stopping_worker", None)
    monkeypatch.setattr(f, "batch_worker", None)
    monkeypatch.setattr(f, "batch_progress_dialog", None)
    _FakeWorker.instances = []
    monkeypatch.setattr(imagedescriber_wx, "BatchProcessingWorker", _FakeWorker)
    f.infos = []
    for name in ("show_info", "show_warning", "show_error"):
        monkeypatch.setattr(imagedescriber_wx, name,
                            lambda _p, msg, *a, **k: f.infos.append(msg))
    monkeypatch.setattr(f, "_load_video_extraction_config", lambda: {})
    f.src = src
    yield f
    if f._run_cancel is not None:          # never leave a thread waiting
        f._run_cancel.set()
        _pump_until(lambda: f._run_cancel is None, 5)
    if f.batch_progress_dialog:
        f._close_progress_dialog()


def _slow_extraction(monkeypatch, f, frames_when_done):
    """Extraction that runs until cancelled (a long video), or until released."""
    release = threading.Event()
    calls = []

    def extract(vp, cfg, cancel=None, frames_dir=None):
        import imagedescriber_wx
        calls.append(vp)
        while not release.is_set():
            if cancel is not None and cancel.is_set():
                raise imagedescriber_wx.ExtractionCancelled(Path(vp).name)
            time.sleep(0.01)
        return frames_when_done, {"fps": 30}
    monkeypatch.setattr(f, "_extract_video_frames_sync", extract)
    return release, calls


def test_stop_during_extraction_stops_the_run(frame, monkeypatch):
    f = frame
    release, calls = _slow_extraction(monkeypatch, f, [])
    vid = str(f.src / "clip.mp4")
    f._extract_then_launch([vid], [str(f.src / "a.jpg")], OPTIONS, True)
    assert _pump_until(lambda: calls)
    assert f._batch_busy_message() is not None

    f.on_stop_batch()
    assert _pump_until(lambda: f._run_cancel is None), "extraction thread never ended"
    assert _FakeWorker.instances == [], "describing was set up after Stop"
    # The half-extracted video is not recorded as done: next run re-extracts it.
    assert not f.workspace.items[vid].extracted_frames
    assert f.workspace.batch_state is None
    assert f._batch_busy_message() is None


def test_second_run_refused_while_extracting(frame, monkeypatch):
    f = frame
    release, calls = _slow_extraction(monkeypatch, f, [])
    f._extract_then_launch([str(f.src / "clip.mp4")], [], OPTIONS, True)
    assert _pump_until(lambda: calls)

    f.on_process_all(None, skip_existing=True, preset_options=OPTIONS)
    assert len(calls) == 1, "a second extraction of the same video started"
    assert any("already running" in m for m in f.infos)

    # After Stop and before the run has ended, still refused. The run can only
    # end in a CallAfter, so with no event pumping in between it is still on.
    f.on_stop_batch()
    assert f._run_cancel is not None
    f.infos.clear()
    f.on_process_all(None, skip_existing=True, preset_options=OPTIONS)
    assert len(calls) == 1
    assert any("still finishing" in m for m in f.infos)
    assert _pump_until(lambda: f._run_cancel is None)


def test_finished_videos_keep_frames_when_stopped_later(frame, monkeypatch, tmp_path):
    """Stop after video 1 finished and during video 2: keep video 1's frames."""
    import imagedescriber_wx
    from data_models import ImageItem
    f = frame
    v2 = f.src / "clip2.mp4"
    v2.write_bytes(b"x")
    f.workspace.add_item(ImageItem(str(v2), "video"))
    done_frame = tmp_path / "clip_0.00s.jpg"
    done_frame.write_bytes(b"x")
    second_started = threading.Event()

    def extract(vp, cfg, cancel=None, frames_dir=None):
        if Path(vp).name == "clip.mp4":
            return [str(done_frame)], {}
        second_started.set()
        while not cancel.is_set():
            time.sleep(0.01)
        raise imagedescriber_wx.ExtractionCancelled(Path(vp).name)
    monkeypatch.setattr(f, "_extract_video_frames_sync", extract)

    f._extract_then_launch([str(f.src / "clip.mp4"), str(v2)], [], OPTIONS, True)
    assert _pump_until(second_started.is_set)
    f.on_stop_batch()
    assert _pump_until(lambda: f._run_cancel is None)
    assert f.workspace.items[str(f.src / "clip.mp4")].extracted_frames == [str(done_frame)]
    assert str(done_frame) in f.workspace.items
    assert not f.workspace.items[str(v2)].extracted_frames
    # ...and they reach the bundle as reference items that resolve on reopen.
    ws = Workspace.open(Path(f.workspace_file))
    gui = bundle_to_gui_workspace_dict(ws)
    assert str(done_frame) in gui["items"]


def test_stop_during_save_stage_never_starts_describing(frame, monkeypatch):
    f = frame
    gate = threading.Event()
    real_save = f._save_bundle

    def slow_save(*a, **k):
        if k.get("progress") is not None:     # the pre-describe save
            gate.wait(10)
        return real_save(*a, **k)
    monkeypatch.setattr(f, "_save_bundle", slow_save)

    f._launch_batch([str(f.src / "a.jpg")], OPTIONS, True)
    assert len(_FakeWorker.instances) == 1
    f.on_stop_batch()
    assert f.batch_worker is None
    gate.set()
    assert _pump_until(lambda: f._run_cancel is None)
    assert not _FakeWorker.instances[0].started
    assert f.workspace.batch_state is None
    assert Workspace.open(Path(f.workspace_file)).batch_state is None
    item = Workspace.open(Path(f.workspace_file)).get_item("a.jpg")
    assert item.extra.get("processing_state") is None


def test_stopped_workers_completion_does_not_rerun_completion(frame, monkeypatch):
    f = frame
    saves = []
    monkeypatch.setattr(f, "_save_bundle", lambda *a, **k: saves.append(1))
    stopped = SimpleNamespace(is_alive=lambda: False)
    f._stopping_worker = stopped
    f.on_workflow_complete(SimpleNamespace(input_dir="3/26 images", output_dir="",
                                           worker=stopped, halted=None))
    assert f._stopping_worker is None
    assert saves == []


def test_same_named_videos_get_separate_frame_folders(frame):
    """IMG_0001.mp4 in two folders shared derived/frames/IMG_0001: extracting
    the second cleared or overwrote the first's frames."""
    from data_models import ImageItem
    f = frame
    a = ImageItem(str(f.src / "jan" / "IMG_0001.mp4"), "video")
    a.subfolder = "src/jan"
    b = ImageItem(str(f.src / "feb" / "IMG_0001.mp4"), "video")
    b.subfolder = "src/feb"
    f.workspace.add_item(a)
    f.workspace.add_item(b)
    da, db = f._frames_dir_for_video(a.file_path), f._frames_dir_for_video(b.file_path)
    assert da != db
    assert f._frame_subfolder(da) == "frames/src/jan/IMG_0001"


def test_same_named_videos_without_subfolder_still_separate(frame):
    """Videos added by file dialog have no subfolder; fall back to a hash."""
    from data_models import ImageItem
    f = frame
    a = ImageItem("C:/one/clip.mp4", "video")
    b = ImageItem("C:/two/clip.mp4", "video")
    f.workspace.add_item(a)
    f.workspace.add_item(b)
    da, db = f._frames_dir_for_video(a.file_path), f._frames_dir_for_video(b.file_path)
    assert da != db
    assert da == f._frames_dir_for_video(a.file_path), "must be stable across calls"


def test_unique_video_keeps_plain_folder_name(frame):
    f = frame
    d = f._frames_dir_for_video(str(f.src / "clip.mp4"))
    assert d.name == "clip"


def test_persisted_frames_resolve_after_reopen(frame, tmp_path):
    from data_models import ImageItem
    f = frame
    vid = str(f.src / "clip.mp4")
    fdir = Path(f.workspace_file) / "derived" / "frames" / "clip"
    fdir.mkdir(parents=True)
    frames = []
    for t in (0, 5):
        p = fdir / f"clip_{t}.00s.jpg"
        p.write_bytes(b"x")
        frames.append(str(p))
        fi = ImageItem(str(p), "extracted_frame")
        fi.parent_video = vid
        f.workspace.add_item(fi)
    f.workspace.items[vid].extracted_frames = frames

    f._persist_extracted_frames_to_bundle()

    ws = Workspace.open(Path(f.workspace_file))
    # Recorded truthfully (they are not in images/), not rescued by the
    # image_path fallback that exists for bundles the old code wrote.
    assert {ws.get_item(Path(p).name).storage for p in frames} == {"reference"}
    gui = bundle_to_gui_workspace_dict(ws)
    for p in frames:
        assert p in gui["items"], "frame no longer at its real path after reopen"
        assert gui["items"][p]["parent_video"] == vid
    assert gui["items"][vid]["extracted_frames"] == frames


# --------------------------------------------------------------------------- #
# Found by independent review of the first fix                                 #
# --------------------------------------------------------------------------- #

def test_stop_button_enabled_while_extracting(frame, monkeypatch):
    """Stop must be reachable from the progress window in the extract stage
    (it was disabled there, so the new stop path could only be reached from
    the menu)."""
    f = frame
    release, calls = _slow_extraction(monkeypatch, f, [])
    f._extract_then_launch([str(f.src / "clip.mp4")], [], OPTIONS, True)
    assert _pump_until(lambda: calls)
    dlg = f.batch_progress_dialog
    assert dlg is not None
    assert dlg.stop_button.IsEnabled()
    assert not dlg.pause_button.IsEnabled()


def test_failure_before_describing_does_not_leave_app_busy(frame, monkeypatch):
    f = frame

    def boom(*a, **k):
        raise RuntimeError("dialog exploded")
    monkeypatch.setattr(f, "_ensure_progress_dialog", boom)
    f._launch_batch([str(f.src / "a.jpg")], OPTIONS, True)
    assert f._run_cancel is None
    assert f._batch_busy_message() is None
    assert any("could not start" in m for m in f.infos)
    assert f.workspace.batch_state is None


def test_failure_after_extraction_does_not_leave_app_busy(frame, monkeypatch):
    f = frame
    monkeypatch.setattr(f, "_extract_video_frames_sync",
                        lambda vp, cfg, cancel=None, frames_dir=None: ([], {}))

    def boom(*a, **k):
        raise RuntimeError("persist exploded")
    monkeypatch.setattr(f, "_launch_batch_impl", boom)
    f._extract_then_launch([str(f.src / "clip.mp4")], [str(f.src / "a.jpg")], OPTIONS, True)
    assert _pump_until(lambda: f._run_cancel is None)
    assert f._batch_busy_message() is None


def test_manual_video_extraction_counts_as_busy(frame):
    f = frame
    f.video_worker = SimpleNamespace(is_alive=lambda: True)
    try:
        assert "being extracted" in f._batch_busy_message()
    finally:
        f.video_worker = None


def test_stale_completion_does_not_clear_a_new_run(frame):
    """A finished worker's queued completion must not end the batch after it."""
    f = frame
    old = SimpleNamespace(is_alive=lambda: False)
    new = _FakeWorker()
    new.start()
    f.batch_worker = new
    f.workspace.batch_state = {"total_queued": 1}
    f.on_workflow_complete(SimpleNamespace(input_dir="1/1 images", output_dir="",
                                           worker=old, halted=None))
    assert f.batch_worker is new
    assert f.workspace.batch_state == {"total_queued": 1}
    f.batch_worker = None


def test_halted_batch_keeps_resume_state_and_says_why(frame, monkeypatch):
    f = frame
    monkeypatch.setattr(f, "_save_bundle", lambda *a, **k: None)
    w = _FakeWorker()
    f.batch_worker = w
    f.workspace.batch_state = {"total_queued": 2}
    f.workspace.items[str(f.src / "a.jpg")].processing_state = "pending"
    f.on_workflow_complete(SimpleNamespace(
        input_dir="1/2 images", output_dir="", worker=w,
        halted="Claude Code is not signed in. Run: claude auth login"))
    assert f.workspace.batch_state == {"total_queued": 2}
    assert f.workspace.items[str(f.src / "a.jpg")].processing_state == "pending"
    assert any("claude auth login" in m for m in f.infos)
    assert f.batch_worker is None


def test_frame_folders_ignore_case_on_case_insensitive_systems(frame):
    from data_models import ImageItem
    if sys.platform not in ("win32", "darwin"):
        pytest.skip("case-sensitive file system")
    f = frame
    a = ImageItem("C:/x/IMG_0001.MOV", "video")
    b = ImageItem("C:/y/img_0001.mov", "video")
    f.workspace.add_item(a)
    f.workspace.add_item(b)
    assert (f._frames_dir_for_video(a.file_path).name.lower()
            != f._frames_dir_for_video(b.file_path).name.lower())


def test_real_extraction_stops_on_cancel_and_writes_to_frames_dir(frame, tmp_path):
    cv2 = pytest.importorskip("cv2")
    import numpy as np
    import imagedescriber_wx
    f = frame
    video = tmp_path / "real.mp4"
    w = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"mp4v"), 10, (64, 48))
    for i in range(200):
        w.write(np.full((48, 64, 3), i % 255, np.uint8))
    w.release()
    out = tmp_path / "frames_here"
    frames, meta = f._extract_video_frames_sync(
        str(video), {"time_interval_seconds": 5}, frames_dir=out)
    assert frames and all(Path(p).parent == out for p in frames)

    cancel = threading.Event()
    cancel.set()
    with pytest.raises(imagedescriber_wx.ExtractionCancelled):
        f._extract_video_frames_sync(str(video), {"time_interval_seconds": 5},
                                     cancel=cancel, frames_dir=out)


# --------------------------------------------------------------------------- #
# Bundle layer follow-ups                                                      #
# --------------------------------------------------------------------------- #

def test_fallback_only_for_frames_under_derived(tmp_path):
    """A copy-mode image whose copy is gone is still reported missing."""
    src = tmp_path / "a.jpg"
    src.write_bytes(b"x")
    ws = Workspace.create(tmp_path / "w.idtw", copy_originals=True)
    wi = ws.add_image(src)
    (ws.images_dir / "a.jpg").unlink()
    assert ws.image_path(wi) == ws.images_dir / "a.jpg"


def test_old_copy_record_corrected_when_rewritten(tmp_path):
    ws = Workspace.create(tmp_path / "w.idtw")
    d = ws.derived_dir("frames/clip")
    d.mkdir(parents=True)
    fr = d / "clip_5.00s.jpg"
    fr.write_bytes(b"x")
    ws.save_item(WorkspaceItem(image=fr.name, source_path=str(fr), storage="copy",
                               item_type="extracted_frame"))
    wi = gui_item_to_ws_item(ws, str(fr), {"item_type": "extracted_frame",
                                           "descriptions": []})
    assert wi.storage == "reference"


def test_name_index_matches_unindexed_lookup(tmp_path):
    from idt_core.gui_bridge import sidecar_name_index
    src = tmp_path / "p"
    (src / "A").mkdir(parents=True)
    (src / "A" / "x.jpg").write_bytes(b"x")
    ws = Workspace.create(tmp_path / "w.idtw")
    ws.add_source_folder(src)
    target = src / "A" / "x.jpg"
    idx = sidecar_name_index(ws)
    with_idx = gui_item_to_ws_item(ws, str(target), {"descriptions": []}, idx)
    without = gui_item_to_ws_item(ws, str(target), {"descriptions": []})
    assert with_idx.subfolder == without.subfolder and with_idx.image == without.image
