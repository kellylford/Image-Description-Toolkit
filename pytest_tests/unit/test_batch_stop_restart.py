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
    """Stands in for BatchProcessingWorker; records whether it was started,
    and what was queued for describing (#344: frames join an open queue)."""
    instances = []

    def __init__(self, *a, **k):
        self.started = False
        self.stopped = False
        paths = k.get("file_paths", a[1] if len(a) > 1 else [])
        self.file_paths = list(paths or [])
        self.queue_open = k.get("queue_open", False)
        self.closing_note = None
        _FakeWorker.instances.append(self)

    def add_files(self, paths):
        assert self.queue_open, "frames added after the queue was closed"
        self.file_paths.extend(paths)

    def close_queue(self, note=None):
        self.queue_open = False
        self.closing_note = note

    def queued_total(self):
        return len(self.file_paths)

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
    monkeypatch.setattr(f, "_window_closing", False)
    monkeypatch.setattr(f, "batch_worker", None)
    monkeypatch.setattr(f, "batch_progress_dialog", None)
    _FakeWorker.instances = []
    monkeypatch.setattr(imagedescriber_wx, "BatchProcessingWorker", _FakeWorker)
    f.infos = []
    for name in ("show_info", "show_warning", "show_error"):
        monkeypatch.setattr(imagedescriber_wx, name,
                            lambda _p, msg, *a, **k: f.infos.append(msg))
    # Questions are recorded and answered No unless a test says otherwise.
    f.questions = []
    f.answer = False
    monkeypatch.setattr(imagedescriber_wx, "ask_yes_no",
                        lambda _p, msg, *a, **k: (f.questions.append(msg), f.answer)[1])
    monkeypatch.setattr(f, "_load_video_extraction_config", lambda: {})
    f.src = src
    yield f
    if f._run_cancel is not None:          # never leave a thread waiting
        f._run_cancel.set()
        # After a (stubbed) Destroy the run's hand-back leaves the window
        # alone, so _run_cancel is never cleared: just let the thread finish.
        _pump_until(lambda: f._run_cancel is None, 0.5 if f._window_closing else 5)
    if f.batch_progress_dialog:
        f._close_progress_dialog()


def _extracting(f):
    """The run's extraction thread has started. Since #344 it starts once
    describing has, after the save stage, not as the run begins."""
    run = f._run_cancel
    return run is not None and getattr(run, "thread", None) is not None


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
    # Describing ran alongside extraction (#344); Stop stopped both.
    worker = _FakeWorker.instances[0]
    assert worker.started and worker.stopped
    assert worker.file_paths == [str(f.src / "a.jpg")], "frames queued after Stop"
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

    # After Stop and before the batch has wound down, still refused: the
    # describe worker finishes the image in flight first.
    worker = _FakeWorker.instances[0]
    worker.is_alive = lambda: True        # still on its last image
    f.on_stop_batch()
    f.infos.clear()
    f.on_process_all(None, skip_existing=True, preset_options=OPTIONS)
    assert len(calls) == 1
    assert any("still finishing" in m for m in f.infos)
    assert _pump_until(lambda: f._run_cancel is None)
    worker.is_alive = lambda: False


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
    on_disk = Workspace.open(Path(f.workspace_file)).batch_state
    assert on_disk is None
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


def test_frame_folders_claimed_off_the_main_thread(frame, monkeypatch):
    """Issue #342: claiming reads each source video (fingerprint). On a macOS
    network share that took ~60 ms a video, all on the main thread before the
    progress window appeared: 1,340 videos froze the app for ~2 minutes."""
    import imagedescriber_wx
    from data_models import ImageItem
    f = frame
    v2 = f.src / "clip2.mp4"
    v2.write_bytes(b"x")
    f.workspace.add_item(ImageItem(str(v2), "video"))
    claimed_on = []
    real_claim = imagedescriber_wx._claim_frames_dir_for

    def claim(*a):
        claimed_on.append(threading.current_thread())
        return real_claim(*a)
    monkeypatch.setattr(imagedescriber_wx, "_claim_frames_dir_for", claim)
    dirs = {}

    def extract(vp, cfg, cancel=None, frames_dir=None):
        dirs[vp] = frames_dir
        out = Path(frames_dir) / f"{Path(vp).stem}_0.00s.jpg"
        out.write_bytes(b"x")
        return [str(out)], {}
    monkeypatch.setattr(f, "_extract_video_frames_sync", extract)

    vids = [str(f.src / "clip.mp4"), str(v2)]
    f._extract_then_launch(vids, [], OPTIONS, True)
    assert _pump_until(lambda: f._run_cancel is None)
    assert len(claimed_on) == 2
    assert threading.main_thread() not in claimed_on
    # Same folders as the main-thread path chooses, and the frames recorded
    # under them.
    for vp in vids:
        assert dirs[vp] == f._frames_dir_for_video(vp)
        frame_path = f.workspace.items[vp].extracted_frames[0]
        assert f.workspace.items[frame_path].subfolder == f._frame_subfolder(dirs[vp])


def test_video_whose_folder_cannot_be_claimed_is_skipped(frame, monkeypatch):
    import imagedescriber_wx
    from data_models import ImageItem
    f = frame
    v2 = f.src / "clip2.mp4"
    v2.write_bytes(b"x")
    f.workspace.add_item(ImageItem(str(v2), "video"))
    real_claim = imagedescriber_wx._claim_frames_dir_for

    def claim(derived, vp, *a):
        if Path(vp).name == "clip.mp4":
            raise OSError("share went away")
        return real_claim(derived, vp, *a)
    monkeypatch.setattr(imagedescriber_wx, "_claim_frames_dir_for", claim)

    def extract(vp, cfg, cancel=None, frames_dir=None):
        out = Path(frames_dir) / "clip2_0.00s.jpg"
        out.write_bytes(b"x")
        return [str(out)], {}
    monkeypatch.setattr(f, "_extract_video_frames_sync", extract)

    f._extract_then_launch([str(f.src / "clip.mp4"), str(v2)], [], OPTIONS, True)
    assert _pump_until(lambda: f._run_cancel is None)
    assert not f.workspace.items[str(f.src / "clip.mp4")].extracted_frames
    assert len(f.workspace.items[str(v2)].extracted_frames) == 1
    # The other video's frame still reached describing.
    assert _FakeWorker.instances[0].file_paths == f.workspace.items[str(v2)].extracted_frames


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
        fi.subfolder = "frames/clip"
        f.workspace.add_item(fi)
    f.workspace.items[vid].extracted_frames = frames

    # The save a batch runs before describing ("Saving workspace" stage); it
    # replaced a separate main-thread frame save, so it must record frames
    # the same way: storage "reference", parent_video and subfolder kept.
    f._save_bundle()

    ws = Workspace.open(Path(f.workspace_file))
    # Recorded truthfully (they are not in images/), not rescued by the
    # image_path fallback that exists for bundles the old code wrote.
    assert {ws.get_item(Path(p).name).storage for p in frames} == {"reference"}
    subfolders = {ws.get_item(Path(p).name, "frames/clip").subfolder for p in frames}
    assert subfolders == {"frames/clip"}
    gui = bundle_to_gui_workspace_dict(ws)
    for p in frames:
        assert p in gui["items"], "frame no longer at its real path after reopen"
        assert gui["items"][p]["parent_video"] == vid
    assert gui["items"][vid]["extracted_frames"] == frames


# --------------------------------------------------------------------------- #
# Found by independent review of the first fix                                 #
# --------------------------------------------------------------------------- #

def test_stop_button_enabled_while_extracting(frame, monkeypatch):
    """Stop must be reachable from the progress window while frames are
    extracted. Since #344 describing runs alongside, so Pause (which pauses
    describing) applies too."""
    f = frame
    release, calls = _slow_extraction(monkeypatch, f, [])
    f._extract_then_launch([str(f.src / "clip.mp4")], [], OPTIONS, True)
    assert _pump_until(lambda: calls)
    dlg = f.batch_progress_dialog
    assert dlg is not None
    assert dlg.stop_button.IsEnabled()
    assert dlg.pause_button.IsEnabled()
    release.set()


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
    # The provider's own message is shown, with an offer to resume.
    assert any("claude auth login" in q and "resume" in q for q in f.questions)
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


# --------------------------------------------------------------------------- #
# Halt follow-ups from the second review                                       #
# --------------------------------------------------------------------------- #

def test_halting_image_requeued_and_yes_resumes(frame, monkeypatch):
    f = frame
    monkeypatch.setattr(f, "_save_bundle", lambda *a, **k: None)
    resumed = []
    monkeypatch.setattr(f, "resume_batch_processing", lambda: resumed.append(1))
    img = str(f.src / "a.jpg")
    f.workspace.items[img].processing_state = "failed"
    f.workspace.items[img].processing_error = "signed out"
    w = _FakeWorker()
    f.batch_worker = w
    f.workspace.batch_state = {"total_queued": 1}
    f.answer = True
    f.on_workflow_complete(SimpleNamespace(input_dir="1/1 images", output_dir="",
                                           worker=w, halted="signed out",
                                           halted_files=[img]))
    assert f.workspace.items[img].processing_state == "pending"
    assert f.workspace.items[img].processing_error is None
    assert resumed == [1]


def test_batch_failures_are_counted_not_boxed(frame):
    f = frame
    w = _FakeWorker()
    w.start()
    f.batch_worker = w
    img = str(f.src / "a.jpg")
    f._batch_failures, f._batch_first_failure = 0, None
    f.on_worker_failed(SimpleNamespace(file_path=img, error="signed out",
                                       kind="unavailable", run_fatal=True, batch=w))
    assert f.infos == []
    assert f._batch_failures == 0, "the halt explains a run-fatal failure"
    f.on_worker_failed(SimpleNamespace(file_path=img, error="bad image",
                                       kind=None, run_fatal=False, batch=w))
    assert f.infos == []
    assert f._batch_failures == 1 and "bad image" in f._batch_first_failure
    # Counted even when the batch thread has already exited (last image).
    w.stopped = True
    f.on_worker_failed(SimpleNamespace(file_path=img, error="bad image",
                                       kind=None, run_fatal=False, batch=w))
    assert f.infos == [] and f._batch_failures == 2
    # A single image, follow-up question or rename (no batch) still reports.
    f.on_worker_failed(SimpleNamespace(file_path=img, error="bad image",
                                       kind=None, run_fatal=False, batch=None))
    assert f.infos, "non-batch failures still report"
    f.batch_worker = None


def test_end_of_batch_reports_failures_once(frame):
    """The final save opens a progress window; that used to reset the count
    before the summary read it, so nothing was ever reported."""
    f = frame
    w = _FakeWorker()
    f.batch_worker = w
    f._batch_failures, f._batch_first_failure = 0, None
    img = str(f.src / "a.jpg")
    f.on_worker_failed(SimpleNamespace(file_path=img, error="bad image",
                                       kind=None, run_fatal=False, batch=w))
    f.on_workflow_complete(SimpleNamespace(input_dir="1/1 images", output_dir="",
                                           worker=w, halted=None, halted_files=[]))
    assert any("could not be described" in m and "bad image" in m for m in f.infos)


def test_failed_start_keeps_a_halted_batchs_resume_state(frame, monkeypatch):
    f = frame
    halted_state = {"total_queued": 9, "provider": "claude-code"}
    f.workspace.batch_state = halted_state
    other = str(f.src / "clip.mp4")
    f.workspace.items[other].processing_state = "pending"

    def boom(*a, **k):
        raise RuntimeError("refresh exploded")
    # Fails before the new run sets batch_state or marks anything pending.
    monkeypatch.setattr(f, "refresh_image_list", boom)
    f._launch_batch([str(f.src / "a.jpg")], OPTIONS, True)
    assert f.workspace.batch_state is halted_state
    assert f.workspace.items[other].processing_state == "pending"
    assert f._batch_busy_message() is None


def test_halted_dialog_says_stopped(_frame):
    from batch_progress_dialog import BatchProgressDialog
    dlg = BatchProgressDialog(_frame, 10)
    try:
        dlg.mark_complete("3/10 images: signed out", stopped=True)
        assert "Stopped" in dlg.GetTitle()
        assert "Complete" not in dlg.GetTitle()
    finally:
        dlg.Destroy()



def test_completion_during_a_progress_save_is_delivered(frame, monkeypatch):
    """A REAL posted event arriving while the real progress save pumps events
    (pause with the last image in flight). Re-dispatching the event itself
    failed (wx had deleted it) and the finished batch was left looking paused
    (fourth review); a timer-based retry never fired inside the save loop."""
    import workers_wx
    f = frame
    w = _FakeWorker()
    f.batch_worker = w
    f.workspace.batch_state = {"total_queued": 1}
    real_save = f._save_bundle
    posted = []

    def save_while_the_batch_finishes(*a, **k):
        if not posted:               # posted from the save thread, mid-save
            posted.append(1)
            wx.PostEvent(f, workers_wx.WorkflowCompleteEventData(
                input_dir="1/1 images", output_dir="", worker=w))
            time.sleep(0.3)
        return real_save(*a, **k)
    monkeypatch.setattr(f, "_save_bundle", save_while_the_batch_finishes)

    f._save_bundle_with_progress()     # the real one (as on_pause_batch calls it)
    assert posted
    assert _pump_until(lambda: f.batch_worker is None, 5), "deferred completion lost"
    assert f.workspace.batch_state is None

def test_fatal_halt_count_excludes_nothing(frame, monkeypatch):
    """Two ordinary failures then a sign-out halt: 2 failed, not 1."""
    f = frame
    monkeypatch.setattr(f, "_save_bundle", lambda *a, **k: None)
    w = _FakeWorker()
    f.batch_worker = w
    f._batch_failures, f._batch_first_failure = 0, None
    from batch_progress_dialog import BatchProgressDialog
    f.batch_progress_dialog = BatchProgressDialog(f, 9)
    dlg = f.batch_progress_dialog
    img = str(f.src / "a.jpg")
    for _ in range(2):
        f.on_worker_failed(SimpleNamespace(file_path=img, error="bad", kind=None,
                                           run_fatal=False, batch=w))
    seen = []
    monkeypatch.setattr(dlg, "mark_complete", lambda summary, stopped=False: seen.append(summary))
    f.on_workflow_complete(SimpleNamespace(input_dir="3/9 images", output_dir="", worker=w,
                                           halted="signed out", halted_files=[img],
                                           halted_streak=False))
    dlg.Destroy()
    assert seen and "(2 failed)" in seen[0]



def test_completion_during_a_plain_save_is_deferred_too(frame, monkeypatch):
    """Ctrl+S / Save As run their own progress save; a batch finishing during
    one used to complete nested, starting a second save alongside (fifth
    review). Now it waits for the save to end."""
    import workers_wx
    f = frame
    w = _FakeWorker()
    f.batch_worker = w
    f.workspace.batch_state = {"total_queued": 1}
    real_save = f._save_bundle
    depth = []
    active = [0]

    def save(*a, **k):
        active[0] += 1
        depth.append(active[0])
        try:
            if len(depth) == 1:
                wx.PostEvent(f, workers_wx.WorkflowCompleteEventData(
                    input_dir="1/1 images", output_dir="", worker=w))
                time.sleep(0.3)
            return real_save(*a, **k)
        finally:
            active[0] -= 1
    monkeypatch.setattr(f, "_save_bundle", save)
    f.on_save_workspace(None)          # File > Save, the real handler
    assert _pump_until(lambda: f.batch_worker is None, 5), "completion lost"
    assert max(depth) == 1, "a second save ran inside the first"



def test_pump_depth_recovers_when_closing_the_dialog_raises(frame, monkeypatch):
    """A depth left above 0 deferred every later batch completion forever."""
    f = frame
    assert f._progress_pump_depth == 0

    real_close = f._close_progress_dialog
    raised = []

    def boom():
        if not raised:            # once; the fixture's own cleanup calls it too
            raised.append(1)
            raise RuntimeError("dialog already gone")
        return real_close()
    monkeypatch.setattr(f, "_close_progress_dialog", boom)
    with pytest.raises(RuntimeError):
        f._run_with_progress("Saving workspace", 1, lambda cb: None)
    assert f._progress_pump_depth == 0


def test_all_videos_failing_says_so(frame, monkeypatch):
    """Every video's extraction failing used to end with "All images already
    have descriptions." (third reviewer of PR 343)."""
    from data_models import ImageDescription
    f = frame
    f.workspace.items[str(f.src / "a.jpg")].descriptions.append(
        ImageDescription(text="done"))

    def fail(vp, cfg, cancel=None, frames_dir=None):
        raise OSError("share went read-only")
    monkeypatch.setattr(f, "_extract_video_frames_sync", fail)
    f._extract_then_launch([str(f.src / "clip.mp4")], [], OPTIONS, True)
    assert _pump_until(lambda: f._run_cancel is None)
    assert any("No frames could be extracted" in m and "read-only" in m for m in f.infos)
    assert not any("All images already have descriptions" in m for m in f.infos)
    assert f.batch_progress_dialog is None
    assert f._batch_active is False
    # Describing started (idle, waiting for frames) and was let go quietly.
    worker = _FakeWorker.instances[0]
    assert not worker.queue_open and worker.file_paths == []
    assert f.batch_worker is None and f._stopping_worker is worker
    assert f.workspace.batch_state is None


def test_some_videos_failing_are_reported_at_the_end(frame, monkeypatch, tmp_path):
    """A failed video was counted in the progress window but missing from the
    end-of-batch summary (fourth reviewer of PR 343). Driven through the real
    _launch_batch, so the hand-over into the batch is covered too."""
    from data_models import ImageItem
    f = frame
    good = f.src / "good.mp4"
    good.write_bytes(b"x")
    f.workspace.add_item(ImageItem(str(good), "video"))
    frame_file = tmp_path / "good_0.00s.jpg"
    frame_file.write_bytes(b"x")

    def extract(vp, cfg, cancel=None, frames_dir=None):
        if Path(vp).name == "clip.mp4":
            raise OSError("not a video")
        return [str(frame_file)], {}
    monkeypatch.setattr(f, "_extract_video_frames_sync", extract)
    f._extract_then_launch([str(f.src / "clip.mp4"), str(good)], [], OPTIONS, True)
    # The real _launch_batch through its save stage, then extraction.
    assert _pump_until(lambda: f._run_cancel is None)
    assert f._batch_video_failures == [("clip.mp4", "not a video")]
    assert _FakeWorker.instances[-1].file_paths == [str(frame_file)]
    assert not _FakeWorker.instances[-1].queue_open

    w = _FakeWorker.instances[-1]
    f.on_workflow_complete(SimpleNamespace(input_dir="1/1 images", output_dir="",
                                           worker=w, halted=None, halted_files=[]))
    assert any("could not be extracted from 1 video" in m and "not a video" in m
               for m in f.infos)


def test_stop_during_the_save_stage_announces_after_the_save(frame, monkeypatch):
    """The "stopped" message used to appear at once; the save's progress window
    then took focus from it while a screen reader was reading it. The progress
    window says it is stopping until the (real) save is done, and the save
    never reads as the batch's next step. Since #344 the run saves first and
    extracts while describing, so this is Stop during that first save."""
    import imagedescriber_wx
    f = frame
    order = []
    gate = threading.Event()
    real_save = f._save_bundle

    def slow_save(*a, **k):
        order.append("save")
        if not gate.is_set():
            gate.wait(10)
        return real_save(*a, **k)
    monkeypatch.setattr(f, "_save_bundle", slow_save)
    monkeypatch.setattr(imagedescriber_wx, "show_info",
                        lambda _p, msg, *a, **k: order.append("message"))
    extracted = []
    monkeypatch.setattr(f, "_extract_video_frames_sync",
                        lambda vp, *a, **k: (extracted.append(vp), ([], {}))[1])
    f._extract_then_launch([str(f.src / "clip.mp4")], [str(f.src / "a.jpg")], OPTIONS, True)
    assert _pump_until(lambda: order == ["save"])
    dlg = f.batch_progress_dialog
    titles, lists = [], []
    real_set_title = dlg.SetTitle
    monkeypatch.setattr(dlg, "SetTitle", lambda t: (titles.append(t), real_set_title(t)))
    real_update = dlg.update_progress

    def update(*a, **k):
        real_update(*a, **k)
        lists.append([dlg.stats_list.GetString(i) for i in range(dlg.stats_list.GetCount())])
    monkeypatch.setattr(dlg, "update_progress", update)

    f.on_stop_batch()
    assert "message" not in order, "announced before the run had wound down"
    gate.set()
    assert _pump_until(lambda: f._run_cancel is None)
    assert order[-1] == "message"
    assert titles and all("Stopping" in t for t in titles), titles
    # Restored from before #344 (#352): the save never reads as a step of the
    # batch, and every repaint keeps saying it is stopping.
    assert not any("step" in t for t in titles), titles
    assert all(any("Stopping" in line for line in rows) for rows in lists), lists
    assert extracted == [], "extraction started after Stop"
    assert not _FakeWorker.instances[0].started
    assert f.batch_progress_dialog is None

def _veto_close(f, monkeypatch):
    """Run on_close with the user answering Cancel to "save changes?"."""
    monkeypatch.setattr(f, "confirm_unsaved_changes", lambda: False)
    vetoed = []
    f.on_close(SimpleNamespace(CanVeto=lambda: True, Veto=lambda: vetoed.append(1)))
    assert vetoed


def test_closing_during_extraction_saves_nothing_and_says_nothing(frame, monkeypatch):
    """Closing used to run a full save inside the "save changes?" question."""
    import imagedescriber_wx
    from data_models import ImageItem
    f = frame
    saves, extracted = [], []
    monkeypatch.setattr(f, "_save_bundle_with_progress", lambda: saves.append(1))
    done_frame = f.src / "clip_0.00s.jpg"
    done_frame.write_bytes(b"x")
    v2 = f.src / "clip2.mp4"
    v2.write_bytes(b"x")
    f.workspace.add_item(ImageItem(str(v2), "video"))

    def extract(vp, cfg, cancel=None, frames_dir=None):
        if Path(vp).name == "clip.mp4":
            return [str(done_frame)], {}
        extracted.append(vp)
        while not cancel.is_set():
            time.sleep(0.01)
        raise imagedescriber_wx.ExtractionCancelled(Path(vp).name)
    monkeypatch.setattr(f, "_extract_video_frames_sync", extract)
    f._extract_then_launch([str(f.src / "clip.mp4"), str(v2)], [], OPTIONS, True)
    assert _pump_until(lambda: extracted)
    cancel = f._run_cancel
    cancel.closing = True             # as on_close marks it
    cancel.set()
    assert _pump_until(lambda: f._run_cancel is None)
    assert saves == []
    assert f.infos == []


def test_quitting_during_extraction_keeps_finished_videos(frame, monkeypatch):
    """#345: quitting mid-extraction (answering Don't Save) lost every video
    already extracted, because they were only recorded when the whole
    extraction handed back, which never happens once the window is gone. The
    next run extracted all of them again: 20+ minutes for 1,000 videos on a
    network share."""
    import imagedescriber_wx
    from data_models import ImageItem
    f = frame
    done_frame = f.src / "clip_0.00s.jpg"
    done_frame.write_bytes(b"x")
    v2 = f.src / "clip2.mp4"
    v2.write_bytes(b"x")
    f.workspace.add_item(ImageItem(str(v2), "video"))
    f._save_bundle()                  # both videos are in the bundle beforehand
    second_started = threading.Event()

    def extract(vp, cfg, cancel=None, frames_dir=None):
        if Path(vp).name == "clip.mp4":
            return [str(done_frame)], {"fps": 30}
        second_started.set()
        while not cancel.is_set():
            time.sleep(0.01)
        raise imagedescriber_wx.ExtractionCancelled(Path(vp).name)
    monkeypatch.setattr(f, "_extract_video_frames_sync", extract)
    f._extract_then_launch([str(f.src / "clip.mp4"), str(v2)], [], OPTIONS, True)
    assert _pump_until(second_started.is_set)
    wx.SafeYield()                    # let the first video's record run

    monkeypatch.setattr(f, "confirm_unsaved_changes", lambda: True)  # Don't Save
    monkeypatch.setattr(f, "Destroy", lambda: None)
    f.on_close(SimpleNamespace(CanVeto=lambda: True, Veto=lambda: None))

    gui = bundle_to_gui_workspace_dict(Workspace.open(Path(f.workspace_file)))
    frame_item = gui["items"].get(str(done_frame))
    assert frame_item is not None, "finished video's frame was not saved"
    assert frame_item["parent_video"] == str(f.src / "clip.mp4")
    assert gui["items"][str(f.src / "clip.mp4")]["extracted_frames"] == [str(done_frame)]
    # The video being extracted when the app quit is extracted again.
    assert str(v2) in gui["items"]
    assert not gui["items"][str(v2)].get("extracted_frames")


def _slow_writer(f, monkeypatch, secs=0.3):
    """Each checkpoint write takes `secs`, so an unflushed one is still queued."""
    real = f._checkpointer._handle

    def slow(*a):
        time.sleep(secs)
        return real(*a)
    monkeypatch.setattr(f._checkpointer, "_handle", slow)


def _video_released_by(gate, done_frame):
    """Extraction of one video that finishes only when `gate` is set (not on
    cancel: a video already being written finishes)."""
    def extract(vp, cfg, cancel=None, frames_dir=None):
        assert gate.wait(10)
        return [str(done_frame)], {}
    return extract


def test_video_finishing_during_the_save_question_is_written(frame, monkeypatch):
    """#347 review: a video recorded while "save changes?" is open queues its
    writes after on_close's first flush; the second flush must wait for them."""
    f = frame
    done_frame = f.src / "clip_0.00s.jpg"
    done_frame.write_bytes(b"x")
    gate = threading.Event()
    monkeypatch.setattr(f, "_extract_video_frames_sync", _video_released_by(gate, done_frame))
    _slow_writer(f, monkeypatch)
    f._extract_then_launch([str(f.src / "clip.mp4")], [], OPTIONS, True)
    assert _pump_until(lambda: _extracting(f))

    def question():
        gate.set()                     # the video finishes during the question
        assert _pump_until(lambda: str(done_frame) in f.workspace.items)
        return True                    # Don't Save
    monkeypatch.setattr(f, "confirm_unsaved_changes", question)
    monkeypatch.setattr(f, "Destroy", lambda: None)
    f.on_close(SimpleNamespace(CanVeto=lambda: True, Veto=lambda: None))
    assert f._checkpointer._queue.unfinished_tasks == 0, "left unwritten at exit"


def test_video_finishing_after_destroy_is_written(frame, monkeypatch):
    """#347 review: Destroy only schedules deletion, and on msw neither
    IsBeingDeleted() nor bool(frame) changes before queued CallAfters run. A
    video recorded then must still be written: nothing flushes after it."""
    f = frame
    done_frame = f.src / "clip_0.00s.jpg"
    done_frame.write_bytes(b"x")
    gate = threading.Event()
    monkeypatch.setattr(f, "_extract_video_frames_sync", _video_released_by(gate, done_frame))
    _slow_writer(f, monkeypatch)
    f._extract_then_launch([str(f.src / "clip.mp4")], [], OPTIONS, True)
    assert _pump_until(lambda: _extracting(f))

    destroyed = []
    monkeypatch.setattr(f, "confirm_unsaved_changes", lambda: True)
    monkeypatch.setattr(f, "Destroy", lambda: destroyed.append(1))
    f.on_close(SimpleNamespace(CanVeto=lambda: True, Veto=lambda: None))
    assert destroyed == [1] and f._window_closing

    gate.set()                         # finishes after the window is gone
    assert _pump_until(lambda: str(done_frame) in f.workspace.items)
    assert f._checkpointer._queue.unfinished_tasks == 0, "recorded but never written"
    gui = bundle_to_gui_workspace_dict(Workspace.open(Path(f.workspace_file)))
    assert gui["items"][str(f.src / "clip.mp4")]["extracted_frames"] == [str(done_frame)]


def test_quit_waits_for_a_video_finishing_as_the_app_closes(frame, monkeypatch):
    """#347 Windows probe: MainLoop exits ~0.4 s after Close, and a video's
    hand-back queued later never runs, so the video was lost. on_close now
    waits for the cancelled extraction thread and runs its hand-back before
    the last flush. Checked with no event pumping after on_close returns,
    as at a real exit."""
    f = frame
    done_frame = f.src / "clip_0.00s.jpg"
    done_frame.write_bytes(b"x")
    gate = threading.Event()
    monkeypatch.setattr(f, "_extract_video_frames_sync", _video_released_by(gate, done_frame))
    f._extract_then_launch([str(f.src / "clip.mp4")], [], OPTIONS, True)
    assert _pump_until(lambda: _extracting(f))

    monkeypatch.setattr(f, "confirm_unsaved_changes",
                        lambda: (threading.Timer(0.3, gate.set).start(), True)[1])
    monkeypatch.setattr(f, "Destroy", lambda: None)
    f.on_close(SimpleNamespace(CanVeto=lambda: True, Veto=lambda: None))
    assert str(done_frame) in f.workspace.items, "finished video never recorded"
    assert f._checkpointer._queue.unfinished_tasks == 0
    gui = bundle_to_gui_workspace_dict(Workspace.open(Path(f.workspace_file)))
    assert gui["items"][str(f.src / "clip.mp4")]["extracted_frames"] == [str(done_frame)]


def test_reapplying_a_recorded_video_adds_nothing_twice(frame, monkeypatch):
    """_record_video and then _finish_extraction both apply each video; its
    frames are added, and queued for describing, once."""
    f = frame
    frames = [f.src / "clip_0.00s.jpg", f.src / "clip_5.00s.jpg"]
    for fr in frames:
        fr.write_bytes(b"x")
    monkeypatch.setattr(f, "_extract_video_frames_sync",
                        lambda vp, cfg, cancel=None, frames_dir=None:
                        ([str(fr) for fr in frames], {}))
    before = len(f.workspace.items)
    f._extract_then_launch([str(f.src / "clip.mp4")], [], OPTIONS, True)
    assert _pump_until(lambda: f._run_cancel is None)
    worker = _FakeWorker.instances[0]
    assert worker.file_paths == [str(fr) for fr in frames]
    assert len(f.workspace.items) == before + 2
    assert f.workspace.items[str(f.src / "clip.mp4")].extracted_frames == \
        [str(fr) for fr in frames]
    assert f.workspace.batch_state["total_queued"] == 2

def _extraction_waiting_for_cancel(f, monkeypatch):
    """Start a run whose only video extracts until the run is cancelled."""
    _, calls = _slow_extraction(monkeypatch, f, [])
    f._extract_then_launch([str(f.src / "clip.mp4")], [], OPTIONS, True)
    assert _pump_until(lambda: calls)
    return calls


def test_cancelled_close_shows_the_batchs_own_window(frame, monkeypatch):
    """#346: the cancelled close built a new progress window with no Stage
    row; the batch's window was only hidden and still has it. Since #344 a
    run is "preparing" only in its save stage (extraction runs alongside
    describing, where a cancelled close is a plain Stop), so closed there."""
    f = frame
    gate = threading.Event()
    real_save = f._save_bundle

    def slow_save(*a, **k):
        if k.get("progress") is not None and not gate.is_set():
            gate.wait(10)
        return real_save(*a, **k)
    monkeypatch.setattr(f, "_save_bundle", slow_save)
    f._extract_then_launch([str(f.src / "clip.mp4")], [str(f.src / "a.jpg")], OPTIONS, True)
    assert _pump_until(lambda: f.batch_progress_dialog is not None
                       and "Saving" in f.batch_progress_dialog.GetTitle())
    threading.Timer(0.5, gate.set).start()
    original = f.batch_progress_dialog
    assert original is not None
    _veto_close(f, monkeypatch)
    assert f.batch_progress_dialog is original
    assert original.IsShown()
    rows = [original.stats_list.GetString(i)
            for i in range(original.stats_list.GetCount())]
    assert any(r.startswith("Stage:") for r in rows), rows
    assert any("Stopping" in r for r in rows), rows
    assert _pump_until(lambda: f._run_cancel is None)


def test_close_that_cannot_be_vetoed_does_not_become_a_stop(frame, monkeypatch):
    """#346: at shutdown Cancel can't keep the app open. Converting the run
    into a Stop opened a window and a save, then destroyed the frame under
    them."""
    f = frame
    _extraction_waiting_for_cancel(f, monkeypatch)
    calls, saves, stops = [], [], []
    monkeypatch.setattr(f, "confirm_unsaved_changes", lambda: False)
    monkeypatch.setattr(f, "Destroy", lambda: calls.append("destroy"))
    real_flush = f._flush_checkpoints
    monkeypatch.setattr(f, "_flush_checkpoints",
                        lambda *a, **k: (calls.append("flush"), real_flush(*a, **k))[1])
    monkeypatch.setattr(f, "_save_bundle_with_progress", lambda: saves.append(1))
    monkeypatch.setattr(f, "_stop_preparing_run", lambda: stops.append(1))
    f.on_close(SimpleNamespace(CanVeto=lambda: False, Veto=lambda: None))
    assert calls[-2:] == ["flush", "destroy"], calls
    assert f._window_closing
    assert stops == [] and saves == []
    assert f.batch_progress_dialog is None
    # The thread's hand-back after Destroy leaves the window alone.
    for _ in range(20):
        wx.SafeYield()
        time.sleep(0.02)
    assert f.infos == []


def test_cancelling_the_close_leaves_later_stops_working(frame, monkeypatch):
    """A closing flag that outlived the cancelled close silenced every later
    Stop for the rest of the session (fifth reviewer of PR 343)."""
    import imagedescriber_wx
    f = frame
    release, calls = _slow_extraction(monkeypatch, f, [])
    monkeypatch.setattr(f, "_save_bundle_with_progress", lambda: None)
    f._extract_then_launch([str(f.src / "clip.mp4")], [], OPTIONS, True)
    assert _pump_until(lambda: calls)
    _veto_close(f, monkeypatch)            # user chooses Cancel: stays
    assert _pump_until(lambda: f._run_cancel is None)
    assert any("Batch processing stopped" in m for m in f.infos), \
        "the run the cancelled close stopped should still say so"

    # A later run and Stop still announce.
    f.infos.clear()
    calls.clear()
    f._extract_then_launch([str(f.src / "clip.mp4")], [], OPTIONS, True)
    assert _pump_until(lambda: calls)
    f.on_stop_batch()
    assert _pump_until(lambda: f._run_cancel is None)
    assert any("Batch processing stopped" in m for m in f.infos)


def test_scan_finishing_mid_run_keeps_the_runs_window(frame, monkeypatch):
    """A folder scan completing while a run extracted frames closed the run's
    progress window. (It also reset "embed after processing"; that choice now
    lives on the batch worker, which a scan can't touch.)"""
    f = frame
    release, calls = _slow_extraction(monkeypatch, f, [])
    opts = dict(OPTIONS, embed_after_process=True)
    f._extract_then_launch([str(f.src / "clip.mp4")], [], opts, True)
    assert _pump_until(lambda: calls)
    dlg = f.batch_progress_dialog
    f.on_scan_failed(SimpleNamespace(error="share went away"))
    assert f.batch_progress_dialog is dlg
    f._run_cancel.set()
    assert _pump_until(lambda: f._run_cancel is None)


def test_cancelled_close_during_the_save_stage_is_a_full_stop(frame, monkeypatch):
    """Closing then choosing Cancel during "Saving workspace" left batch_state
    and pending flags set, so reopening offered to resume a batch the user was
    told had stopped (sixth reviewer of PR 343)."""
    f = frame
    gate = threading.Event()
    real_save = f._save_bundle

    def slow_save(*a, **k):
        if k.get("progress") is not None and not gate.is_set():
            gate.wait(10)
        return real_save(*a, **k)
    monkeypatch.setattr(f, "_save_bundle", slow_save)
    f._launch_batch([str(f.src / "a.jpg")], OPTIONS, True)
    assert f._run_cancel is not None
    _veto_close(f, monkeypatch)
    gate.set()
    assert _pump_until(lambda: f._run_cancel is None)
    assert f.workspace.batch_state is None
    assert f.workspace.items[str(f.src / "a.jpg")].processing_state is None
    on_disk = Workspace.open(Path(f.workspace_file)).batch_state
    assert on_disk is None
    assert any("stopped before describing" in m for m in f.infos)
    assert not _FakeWorker.instances[-1].started


def test_scan_progress_does_not_paint_into_a_runs_window(frame, monkeypatch):
    f = frame
    release, calls = _slow_extraction(monkeypatch, f, [])
    f._extract_then_launch([str(f.src / "clip.mp4")], [], OPTIONS, True)
    assert _pump_until(lambda: calls)
    dlg = f.batch_progress_dialog
    painted = []
    monkeypatch.setattr(dlg, "update_progress", lambda *a, **k: painted.append(a))
    f.on_scan_progress(SimpleNamespace(files_found=812, message="scanning"))
    f.on_scan_complete(SimpleNamespace(total_files=812, elapsed_time=3.1))
    wx.SafeYield()
    assert painted == []
    f._run_cancel.set()
    assert _pump_until(lambda: f._run_cancel is None)


def test_halted_question_mentions_failed_videos(frame, monkeypatch):
    f = frame
    monkeypatch.setattr(f, "_save_bundle", lambda *a, **k: None)
    w = _FakeWorker()
    f.batch_worker = w
    f._reset_batch_failures()
    f._batch_video_failures = [("clip.mp4", "not a video")]
    f.on_workflow_complete(SimpleNamespace(input_dir="1/2 images", output_dir="",
                                           worker=w, halted="signed out",
                                           halted_files=[], halted_streak=False))
    assert any("could not be extracted from 1 video" in q for q in f.questions)


def test_frames_all_already_described_is_not_called_a_failure(frame, monkeypatch, tmp_path):
    """One video fails, another gives frames that are all already described:
    nothing to do, but frames *were* extracted, so the message must not say
    none could be."""
    from data_models import ImageItem, ImageDescription
    f = frame
    f.workspace.items[str(f.src / "a.jpg")].descriptions.append(ImageDescription(text="d"))
    good = f.src / "good.mp4"
    good.write_bytes(b"x")
    f.workspace.add_item(ImageItem(str(good), "video"))
    fr = tmp_path / "good_0.00s.jpg"
    fr.write_bytes(b"x")
    done = ImageItem(str(fr), "extracted_frame")
    done.descriptions.append(ImageDescription(text="already"))
    f.workspace.add_item(done)

    def extract(vp, cfg, cancel=None, frames_dir=None):
        if Path(vp).name == "clip.mp4":
            raise OSError("not a video")
        return [str(fr)], {}
    monkeypatch.setattr(f, "_extract_video_frames_sync", extract)
    f._extract_then_launch([str(f.src / "clip.mp4"), str(good)], [], OPTIONS, True)
    assert _pump_until(lambda: f._run_cancel is None)
    assert not any("No frames could be extracted" in m for m in f.infos)
    assert any("All images already have descriptions" in m for m in f.infos)


def test_stopping_line_stays_selected_through_rebuilds(_frame):
    """mark_stopping appends the line at the end and selects it; the next
    rebuild moves it to the top. Restoring the selection by row number landed
    a screen reader on "Prompt Style" instead of "Stopping". (From the Mac
    session, which found it independently.)"""
    from batch_progress_dialog import BatchProgressDialog
    dlg = BatchProgressDialog(_frame, 10, batch_provider="ollama",
                              batch_model="m", batch_prompt="detailed")
    try:
        dlg.begin_stage("Extracting frames", 10, stage_index=1, stage_count=3)
        dlg.update_progress(3, 10, image_name="clip.mp4")
        dlg.mark_stopping()
        dlg.begin_stage("Saving workspace", 10, stage_index=2, stage_count=3)
        for _ in range(2):
            dlg.update_progress(4, 10, image_name="clip2.mp4")
            sel = dlg.stats_list.GetSelection()
            assert sel != wx.NOT_FOUND
            assert "Stopping:" in dlg.stats_list.GetString(sel)
            rows = [dlg.stats_list.GetString(i) for i in range(dlg.stats_list.GetCount())]
            assert not any("step" in r for r in rows), rows
    finally:
        dlg.Destroy()


def test_mark_stopping_shows_a_hidden_window_before_focusing_it(_frame):
    """Focus moved into a hidden progress window went nowhere for the save."""
    from batch_progress_dialog import BatchProgressDialog
    dlg = BatchProgressDialog(_frame, 10)
    try:
        dlg.Show()
        dlg.Hide()                     # what its Close button does
        dlg.mark_stopping()
        assert dlg.IsShown()
    finally:
        dlg.Destroy()


def test_cancelled_close_after_the_run_ended_is_still_a_full_stop(frame, monkeypatch):
    """The save stage ended while "save changes?" was open, then Cancel: the
    user was told "stopped" but the batch was saved as resumable (seventh
    reviewer of PR 343)."""
    f = frame
    gate = threading.Event()
    real_save = f._save_bundle

    def slow_save(*a, **k):
        if k.get("progress") is not None and not gate.is_set():
            gate.wait(10)
        return real_save(*a, **k)
    monkeypatch.setattr(f, "_save_bundle", slow_save)
    f._launch_batch([str(f.src / "a.jpg")], OPTIONS, True)

    def question():
        gate.set()                     # the save finishes during the question
        assert _pump_until(lambda: f._run_cancel is None)
        return False                   # Cancel
    monkeypatch.setattr(f, "confirm_unsaved_changes", question)
    vetoed = []
    f.on_close(SimpleNamespace(CanVeto=lambda: True, Veto=lambda: vetoed.append(1)))
    assert vetoed
    assert f.workspace.batch_state is None
    assert f.workspace.items[str(f.src / "a.jpg")].processing_state is None
    on_disk = Workspace.open(Path(f.workspace_file)).batch_state
    assert on_disk is None
    assert any("stopped before describing" in m for m in f.infos)


# --------------------------------------------------------------------------- #
# Issue 346 item 1: "embed after processing" belongs to the batch              #
# --------------------------------------------------------------------------- #

def _completion(path, batch):
    return SimpleNamespace(file_path=path, description="a cat", provider="ollama",
                           model="m", prompt_style="detailed", custom_prompt="",
                           metadata={}, batch=batch)


def _record_embeds(f, monkeypatch):
    embedded = []
    monkeypatch.setattr(f, "_embed_single_description",
                        lambda item, desc: embedded.append(item.file_path))
    return embedded


def _record_worker_kwargs(monkeypatch):
    import imagedescriber_wx
    seen = []

    class _Recording(_FakeWorker):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            self.embed_after_process = k.get("embed_after_process", False)
            seen.append(k)
    monkeypatch.setattr(imagedescriber_wx, "BatchProcessingWorker", _Recording)
    return seen


@pytest.mark.parametrize("choice", [True, False])
def test_batch_completion_embeds_by_the_batchs_own_choice(frame, monkeypatch, choice):
    """The choice was a window-wide flag, cleared on Stop, so the image still
    in flight when Stop was pressed lost it. Now it rides on the worker."""
    f = frame
    embedded = _record_embeds(f, monkeypatch)
    batch = _FakeWorker()
    batch.embed_after_process = choice
    batch.start()
    monkeypatch.setattr(f, "batch_worker", batch)
    path = str(f.src / "a.jpg")
    f.on_stop_batch()                 # in flight at Stop: still its batch's choice
    f.on_worker_complete(_completion(path, batch))
    assert embedded == ([path] if choice else [])


def test_single_image_during_an_embedding_batch_does_not_embed(frame, monkeypatch):
    """With a batch that embeds still running, a single image, follow-up or
    rename (no batch on its event, embed off in its own options) must not."""
    f = frame
    embedded = _record_embeds(f, monkeypatch)
    seen = _record_worker_kwargs(monkeypatch)
    f._launch_batch([str(f.src / "a.jpg")], dict(OPTIONS, embed_after_process=True), True)
    assert _pump_until(lambda: seen)
    assert f.batch_worker is not None and f.batch_worker.embed_after_process
    single = str(f.src / "a.jpg")
    f.processing_items[single] = {"embed_after_process": False}
    f.on_worker_complete(_completion(single, None))
    assert embedded == []
    f.processing_items[single] = {"embed_after_process": True}
    f.on_worker_complete(_completion(single, None))
    assert embedded == [single]


def test_launched_batch_carries_and_saves_the_embed_choice(frame, monkeypatch):
    f = frame
    seen = _record_worker_kwargs(monkeypatch)
    f._launch_batch([str(f.src / "a.jpg")], dict(OPTIONS, embed_after_process=True), True)
    assert _pump_until(lambda: seen)
    assert seen[0]["embed_after_process"] is True
    assert f.workspace.batch_state["embed_after_process"] is True


@pytest.mark.parametrize("choice", [True, False])
def test_resumed_batch_embeds_as_the_original_did(frame, monkeypatch, choice):
    """Resume (after a halt, or on reopening) rebuilt the worker without the
    choice, so a resumed batch never embedded."""
    f = frame
    seen = _record_worker_kwargs(monkeypatch)
    item = f.workspace.items[str(f.src / "a.jpg")]
    item.processing_state = "paused"
    f.workspace.batch_state = dict(OPTIONS, total_queued=1, embed_after_process=choice)
    f.resume_batch_processing()
    assert seen and seen[0]["embed_after_process"] is choice


def test_resuming_an_older_batch_without_the_key_does_not_embed(frame, monkeypatch):
    f = frame
    seen = _record_worker_kwargs(monkeypatch)
    f.workspace.items[str(f.src / "a.jpg")].processing_state = "paused"
    f.workspace.batch_state = dict(OPTIONS, total_queued=1)
    f.resume_batch_processing()
    assert seen and seen[0]["embed_after_process"] is False


def test_downloaded_images_batch_carries_the_embed_choice(frame, monkeypatch):
    """New behaviour: downloads processed afterwards follow the dialog's
    embed checkbox (they never embedded before)."""
    f = frame
    seen = _record_worker_kwargs(monkeypatch)
    f.auto_process_downloaded_images([str(f.src / "a.jpg")],
                                     dict(OPTIONS, embed_after_process=True))
    assert seen and seen[0]["embed_after_process"] is True
    assert f.workspace.batch_state["embed_after_process"] is True


def test_extracted_frames_batch_carries_the_embed_choice(frame, monkeypatch):
    """New behaviour: auto-processed video frames follow the dialog's embed
    checkbox (they never embedded before)."""
    import imagedescriber_wx
    f = frame
    seen = _record_worker_kwargs(monkeypatch)

    class _Dialog:
        def __init__(self, *a, **k):
            pass

        def ShowModal(self):
            return wx.ID_OK

        def get_config(self):
            return dict(OPTIONS, embed_after_process=True)

        def Destroy(self):
            pass
    monkeypatch.setattr(imagedescriber_wx, "ProcessingOptionsDialog", _Dialog)
    monkeypatch.setattr(f, "_persist_processing_options", lambda o: None)
    f.auto_process_extracted_frames([str(f.src / "a.jpg")])
    assert seen and seen[0]["embed_after_process"] is True
    assert f.workspace.batch_state["embed_after_process"] is True


def test_completion_event_carries_its_batch():
    """The event the window reads the choice from must carry the batch."""
    import workers_wx
    marker = object()
    evt = workers_wx.ProcessingCompleteEventData("p", "d", "ollama", "m", "s", "", batch=marker)
    assert evt.batch is marker
    assert workers_wx.ProcessingCompleteEventData("p", "d", "ollama", "m", "s", "").batch is None


# --------------------------------------------------------------------------- #
# Issue 346 item 4: the Stopping line                                          #
# --------------------------------------------------------------------------- #

def test_stopping_line_stays_selected_beside_a_callers_status(_frame):
    """While stopping, a caller's own status message used to replace the
    Stopping line, and the selection fell back to a row number."""
    from batch_progress_dialog import BatchProgressDialog, STOPPING_PREFIX, STOPPING_LINE
    dlg = BatchProgressDialog(_frame, 10, batch_provider="ollama",
                              batch_model="m", batch_prompt="detailed")
    try:
        dlg.begin_stage("Saving workspace", 10, stage_index=2, stage_count=3)
        dlg.mark_stopping()
        for msg in ("Writing manifest", None):
            dlg.update_progress(4, 10, image_name="clip.mp4", status_message=msg)
            rows = [dlg.stats_list.GetString(i) for i in range(dlg.stats_list.GetCount())]
            sel = dlg.stats_list.GetSelection()
            assert sel != wx.NOT_FOUND
            assert rows[sel].endswith(STOPPING_LINE)
            assert (msg is None) or any(r.endswith(msg) for r in rows), rows
        assert dlg.GetTitle() == f"{STOPPING_PREFIX} saving workspace — Batch Processing"
        # A stage begun after Stop is titled the same way.
        dlg.begin_stage("Describing images", 10, stage_index=3, stage_count=3)
        assert dlg.GetTitle().startswith(STOPPING_PREFIX)
    finally:
        dlg.Destroy()


def test_selection_on_a_row_mentioning_stopping_is_not_moved(_frame):
    """Only the Stopping line itself is followed: a row that merely contains
    "Stopping:" (a file name, a description) keeps its place."""
    from batch_progress_dialog import BatchProgressDialog, _is_stopping_row, STOPPING_LINE
    assert _is_stopping_row(STOPPING_LINE)
    assert _is_stopping_row(f"⏳ Status:                   {STOPPING_LINE}")
    assert not _is_stopping_row("Current:                    Stopping: notes.jpg")
    dlg = BatchProgressDialog(_frame, 10)
    try:
        dlg.begin_stage("Saving workspace", 10, stage_index=2, stage_count=3)
        dlg.mark_stopping()
        dlg.update_progress(4, 10, image_name="Stopping: notes.jpg")
        rows = [dlg.stats_list.GetString(i) for i in range(dlg.stats_list.GetCount())]
        current = next(i for i, r in enumerate(rows) if r.startswith("Current:"))
        dlg.stats_list.SetSelection(current)
        dlg.update_progress(5, 10, image_name="Stopping: notes.jpg")
        assert dlg.stats_list.GetString(dlg.stats_list.GetSelection()).startswith("Current:")
    finally:
        dlg.Destroy()


@pytest.mark.parametrize("tick_between", [False, True])
def test_marking_stopping_twice_shows_one_stopping_line(_frame, tick_between):
    """Stop, then a cancelled close, marks the same window stopping twice;
    it added a second Stopping line (reviewer of PR 347)."""
    from batch_progress_dialog import BatchProgressDialog, _is_stopping_row
    dlg = BatchProgressDialog(_frame, 10)
    try:
        dlg.begin_stage("Extracting frames", 10, stage_index=1, stage_count=3)
        dlg.mark_stopping()
        if tick_between:
            dlg.update_progress(3, 10, image_name="clip.mp4")
        dlg.mark_stopping()
        rows = [dlg.stats_list.GetString(i) for i in range(dlg.stats_list.GetCount())]
        assert sum(_is_stopping_row(r) for r in rows) == 1, rows
        assert _is_stopping_row(rows[dlg.stats_list.GetSelection()])
    finally:
        dlg.Destroy()


# --------------------------------------------------------------------------- #
# Issue 344: describe while frames are extracted                               #
# --------------------------------------------------------------------------- #

class _InstantImage(threading.Thread):
    """Stands in for ProcessingWorker inside the real BatchProcessingWorker."""
    seen = []

    def __init__(self, parent, file_path, *a, **k):
        super().__init__(daemon=True)
        self.file_path = file_path
        self.result_ok = True
        self.result_error = None
        self.result_kind = None
        self.result_signature = None
        self.result_input_tokens = self.result_output_tokens = 0

    def run(self):
        _InstantImage.seen.append(self.file_path)


def _real_batch(monkeypatch, paths, queue_open):
    import workers_wx
    _InstantImage.seen = []
    monkeypatch.setattr(workers_wx, "ProcessingWorker", _InstantImage)
    events = []

    def post(_target, evt):
        if isinstance(evt, workers_wx.WorkflowCompleteEventData):
            events.append(evt.input_dir)
    monkeypatch.setattr(workers_wx.wx, "PostEvent", post)
    w = workers_wx.BatchProcessingWorker(object(), paths, "ollama", "m", "s",
                                         queue_open=queue_open)
    return w, events


def test_open_queue_waits_for_more_and_ends_after_close(monkeypatch):
    w, events = _real_batch(monkeypatch, ["a.jpg"], queue_open=True)
    w.start()
    assert _pump_until(lambda: _InstantImage.seen == ["a.jpg"])
    time.sleep(0.2)
    assert w.is_alive(), "ended while the queue was still open"
    w.add_files(["f1.jpg", "f2.jpg"])
    assert _pump_until(lambda: _InstantImage.seen == ["a.jpg", "f1.jpg", "f2.jpg"])
    assert w.is_alive()
    w.close_queue(note="Video extraction: 1 video(s) → 2 frame(s)")
    w.join(5)
    assert not w.is_alive()
    assert events == ["3/3 images"]


def test_open_queue_with_nothing_yet_waits_and_stop_wakes_it(monkeypatch):
    w, events = _real_batch(monkeypatch, [], queue_open=True)
    w.start()
    time.sleep(0.2)
    assert w.is_alive()
    w.stop()
    w.join(5)
    assert not w.is_alive(), "Stop did not wake a worker waiting for frames"
    assert _InstantImage.seen == []


def test_closed_queue_behaves_as_before(monkeypatch):
    w, events = _real_batch(monkeypatch, ["a.jpg", "b.jpg"], queue_open=False)
    w.start()
    w.join(5)
    assert not w.is_alive()
    assert _InstantImage.seen == ["a.jpg", "b.jpg"]


def test_describing_starts_before_extraction_ends(frame, monkeypatch, tmp_path):
    """#344: nothing was described until the last video was extracted (half
    an hour on a large library). The images start at once, and each video's
    frames are queued as it finishes, while the next one extracts."""
    import imagedescriber_wx
    from data_models import ImageItem
    f = frame
    v2 = f.src / "clip2.mp4"
    v2.write_bytes(b"x")
    f.workspace.add_item(ImageItem(str(v2), "video"))
    first_frame = tmp_path / "clip_0.00s.jpg"
    first_frame.write_bytes(b"x")
    second_frame = tmp_path / "clip2_0.00s.jpg"
    second_frame.write_bytes(b"x")
    release = threading.Event()

    def extract(vp, cfg, cancel=None, frames_dir=None):
        if Path(vp).name == "clip.mp4":
            return [str(first_frame)], {}
        while not release.is_set():
            if cancel.is_set():
                raise imagedescriber_wx.ExtractionCancelled(Path(vp).name)
            time.sleep(0.01)
        return [str(second_frame)], {}
    monkeypatch.setattr(f, "_extract_video_frames_sync", extract)
    f._extract_then_launch([str(f.src / "clip.mp4"), str(v2)],
                           [str(f.src / "a.jpg")], OPTIONS, True)
    assert _pump_until(lambda: _FakeWorker.instances and _FakeWorker.instances[0].started)
    worker = _FakeWorker.instances[0]
    assert worker.queue_open
    # The first video's frame is queued while the second is still extracting.
    assert _pump_until(lambda: str(first_frame) in worker.file_paths)
    assert f._run_cancel is not None and worker.queue_open
    assert f.workspace.items[str(first_frame)].processing_state == "pending"
    assert f.workspace.batch_state["total_queued"] == 2
    rows = [f.batch_progress_dialog.stats_list.GetString(i)
            for i in range(f.batch_progress_dialog.stats_list.GetCount())]
    assert any(r.startswith("Extracting Frames:") for r in rows), rows
    assert "extracting frames" in f.batch_progress_dialog.GetTitle().lower()

    release.set()
    assert _pump_until(lambda: f._run_cancel is None)
    assert worker.file_paths == [str(f.src / "a.jpg"), str(first_frame), str(second_frame)]
    assert not worker.queue_open
    assert "2 video(s) → 2 frame(s)" in worker.closing_note
    assert f.workspace.batch_state["total_queued"] == 3
    assert f.workspace.batch_state["videos"] == [str(f.src / "clip.mp4"), str(v2)]
    title = f.batch_progress_dialog.GetTitle()
    assert title.startswith("Describing (step 2 of 2)"), title


def test_stop_while_describing_and_extracting_queues_nothing_more(frame, monkeypatch, tmp_path):
    """A video finishing just after Stop keeps its frames (no re-extraction)
    but they are not queued, marked pending, or offered for resume."""
    import imagedescriber_wx
    f = frame
    late_frame = tmp_path / "clip_0.00s.jpg"
    late_frame.write_bytes(b"x")
    stopped = threading.Event()
    started = threading.Event()

    def extract(vp, cfg, cancel=None, frames_dir=None):
        started.set()
        assert stopped.wait(10)
        return [str(late_frame)], {}      # was on its last frame
    monkeypatch.setattr(f, "_extract_video_frames_sync", extract)
    f._extract_then_launch([str(f.src / "clip.mp4")], [str(f.src / "a.jpg")], OPTIONS, True)
    assert _pump_until(started.is_set)
    worker = _FakeWorker.instances[0]
    f.on_stop_batch()
    stopped.set()
    assert _pump_until(lambda: f._run_cancel is None)
    assert worker.stopped
    assert str(late_frame) not in worker.file_paths
    assert f.workspace.items[str(f.src / "clip.mp4")].extracted_frames == [str(late_frame)]
    assert f.workspace.items[str(late_frame)].processing_state is None
    assert f.workspace.batch_state is None
    stop_messages = [m for m in f.infos if "Batch processing stopped" in m]
    assert len(stop_messages) == 1, f.infos
    assert "extracted again next time" in stop_messages[0]


def test_halt_while_extracting_keeps_the_rest_for_resume(frame, monkeypatch, tmp_path):
    """Signed out while videos were still being extracted: extraction stops
    too, the batch keeps its batch_state, and resuming extracts the videos
    it never reached and describes everything left."""
    import imagedescriber_wx
    from data_models import ImageItem
    f = frame
    v2 = f.src / "clip2.mp4"
    v2.write_bytes(b"x")
    f.workspace.add_item(ImageItem(str(v2), "video"))
    first_frame = tmp_path / "clip_0.00s.jpg"
    first_frame.write_bytes(b"x")
    second_started = threading.Event()

    def extract(vp, cfg, cancel=None, frames_dir=None):
        if Path(vp).name == "clip.mp4":
            return [str(first_frame)], {}
        second_started.set()
        while not cancel.is_set():
            time.sleep(0.01)
        raise imagedescriber_wx.ExtractionCancelled(Path(vp).name)
    monkeypatch.setattr(f, "_extract_video_frames_sync", extract)
    f._extract_then_launch([str(f.src / "clip.mp4"), str(v2)],
                           [str(f.src / "a.jpg")], OPTIONS, True)
    assert _pump_until(second_started.is_set)
    assert _pump_until(lambda: str(first_frame) in _FakeWorker.instances[0].file_paths)
    worker = _FakeWorker.instances[0]

    f.answer = False                         # "resume now?" No: later
    f.on_workflow_complete(SimpleNamespace(
        input_dir="0/2 images", output_dir="", worker=worker,
        halted="Claude Code is signed out.", halted_files=[str(f.src / "a.jpg")],
        halted_streak=False))
    assert f._run_cancel is None, "extraction still running after the halt"
    state = f.workspace.batch_state
    assert state is not None and state["videos"] == [str(f.src / "clip.mp4"), str(v2)]
    assert f.workspace.items[str(first_frame)].processing_state == "pending"
    assert f._unextracted_batch_videos(state) == [str(v2)]
    assert any("signed out" in q for q in f.questions)

    # Resume: the unreached video is extracted, everything left is described.
    launched = []
    monkeypatch.setattr(f, "_extract_then_launch",
                        lambda videos, images, options, skip_existing: launched.append(
                            (videos, sorted(images), options['embed_after_process'])))
    f.resume_batch_processing()
    assert launched == [([str(v2)], sorted([str(f.src / "a.jpg"), str(first_frame)]), False)]


def test_resume_prompt_counts_videos_left_to_extract(frame, monkeypatch):
    f = frame
    f.workspace.batch_state = dict(OPTIONS, total_queued=0,
                                   videos=[str(f.src / "clip.mp4")])
    f.prompt_resume_batch()
    assert f.questions and "1 video to extract frames from" in f.questions[-1]
    assert "Progress: 0 of 0" not in f.questions[-1]
    # Answered No: the batch is forgotten.
    assert f.workspace.batch_state is None


def test_extraction_row_and_title(_frame):
    from batch_progress_dialog import BatchProgressDialog
    dlg = BatchProgressDialog(_frame, 0)
    try:
        dlg.begin_stage("Describing and extracting frames", 1, stage_index=2, stage_count=2)
        dlg.begin_extraction(3)
        dlg.update_progress(1, 4, image_name="a.jpg")
        dlg.set_extraction(2, 3, "clip.mp4")
        rows = [dlg.stats_list.GetString(i) for i in range(dlg.stats_list.GetCount())]
        assert any(r.startswith("Items Processed:") and "1 / 4" in r
                   and "more as videos finish" in r for r in rows), rows
        assert any(r.startswith("Extracting Frames:") and "2 of 3 videos" in r for r in rows)
        assert any(r.startswith("Last Video Extracted:") and "clip.mp4" in r for r in rows)
        assert any(r.startswith("Current:") and "a.jpg" in r for r in rows), \
            "an extraction tick lost the describe progress"
        dlg.end_extraction("Describing")
        rows = [dlg.stats_list.GetString(i) for i in range(dlg.stats_list.GetCount())]
        assert not any("Extracting Frames" in r or "more as videos" in r for r in rows)
        assert dlg.GetTitle() == "Describing (step 2 of 2) — Batch Processing"
        dlg.set_extraction(3, 3, "late.mp4")     # a late tick is ignored
        rows = [dlg.stats_list.GetString(i) for i in range(dlg.stats_list.GetCount())]
        assert not any("Extracting Frames" in r for r in rows)
    finally:
        dlg.Destroy()


# ----- #344 review findings ----- #

class _LingeringWorker(_FakeWorker):
    """Like a real batch worker: after stop() it is still alive until the
    image in flight is done (finish())."""
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.finished = False

    def is_alive(self):
        return self.started and not self.finished

    def finish(self):
        self.finished = True


def _pipeline_running(f, monkeypatch, worker_cls=_FakeWorker):
    """A run describing a.jpg while clip.mp4 extracts until cancelled."""
    import imagedescriber_wx
    monkeypatch.setattr(imagedescriber_wx, "BatchProcessingWorker", worker_cls)
    release, calls = _slow_extraction(monkeypatch, f, [])
    f._extract_then_launch([str(f.src / "clip.mp4")], [str(f.src / "a.jpg")], OPTIONS, True)
    assert _pump_until(lambda: calls)
    return _FakeWorker.instances[-1]


def test_cancelled_close_while_describing_is_a_stop_of_a_describing_batch(frame, monkeypatch):
    """Review finding 1: the cancelled close took the "before describing"
    branches, said so, and dropped the still-running worker, so a new run
    could start and describe its in-flight image again."""
    f = frame
    worker = _pipeline_running(f, monkeypatch, _LingeringWorker)
    _veto_close(f, monkeypatch)
    assert _pump_until(lambda: f._run_cancel is None)
    assert worker.stopped and worker.is_alive()        # still on its last image
    assert f._stopping_worker is worker
    assert f._batch_busy_message() is not None, "a new run could start"
    stops = [m for m in f.infos if "Batch processing stopped" in m]
    assert len(stops) == 1, f.infos
    assert "before describing" not in stops[0]
    assert f.workspace.batch_state is None
    worker.finish()


def test_nothing_to_describe_leaves_no_batch_to_resume_on_disk(frame, monkeypatch):
    """Review finding 2: the save stage and checkpoints wrote batch_state
    (with its videos); clearing it only in memory left reopening offering to
    resume a batch that had nothing to describe."""
    f = frame
    f._save_bundle()

    def fail(vp, cfg, cancel=None, frames_dir=None):
        raise OSError("not a video")
    monkeypatch.setattr(f, "_extract_video_frames_sync", fail)
    f._extract_then_launch([str(f.src / "clip.mp4")], [], OPTIONS, True)
    assert _pump_until(lambda: f._run_cancel is None)
    assert any("No frames could be extracted" in m for m in f.infos)
    on_disk = Workspace.open(Path(f.workspace_file)).batch_state
    assert on_disk is None


def test_error_in_the_extraction_hand_back_keeps_the_batch_window(frame, monkeypatch):
    """Review finding 3, driven directly: the hand-back raises after
    describing started."""
    f = frame
    released = threading.Event()

    def extract(vp, cfg, cancel=None, frames_dir=None):
        released.wait(10)
        return [], {}
    monkeypatch.setattr(f, "_extract_video_frames_sync", extract)
    f._extract_then_launch([str(f.src / "clip.mp4")], [str(f.src / "a.jpg")], OPTIONS, True)
    assert _pump_until(lambda: _extracting(f))
    worker = _FakeWorker.instances[-1]
    dlg = f.batch_progress_dialog
    monkeypatch.setattr(f, "mark_modified", lambda: (_ for _ in ()).throw(RuntimeError("disk gone")))
    released.set()
    assert _pump_until(lambda: f._run_cancel is None)
    assert not worker.queue_open, "describing never told the queue was closed"
    assert not worker.stopped
    assert f.batch_progress_dialog is dlg, "the running batch's window was closed"
    assert any("describing continues" in m and "disk gone" in m for m in f.infos)
    assert not any("could not start" in m for m in f.infos)


def test_failure_after_the_worker_started_does_not_leave_it_waiting(frame, monkeypatch):
    """Review finding 4: starting extraction failing after the worker had
    started left an open queue waiting forever, and every later run refused."""
    f = frame

    def cannot_start():
        raise RuntimeError("can't start new thread")
    f._launch_batch([str(f.src / "a.jpg")], OPTIONS, True,
                    extraction=cannot_start,
                    extraction_videos=[str(f.src / "clip.mp4")])
    assert _pump_until(lambda: f._run_cancel is None)
    worker = _FakeWorker.instances[-1]
    assert worker.started and worker.stopped
    assert f._batch_busy_message() is None
    assert any("could not start" in m and "new thread" in m for m in f.infos)
    # #352: and no batch is left to resume, nor flags pending.
    assert f.workspace.batch_state is None
    assert f.workspace.items[str(f.src / "a.jpg")].processing_state is None


def test_halted_batch_final_stats_do_not_say_extracting(frame, monkeypatch):
    """Review finding 5: after a halt the kept window still read
    "Extracting Frames: 0 of 1 videos" and "(more as videos finish)"."""
    f = frame
    worker = _pipeline_running(f, monkeypatch)
    dlg = f.batch_progress_dialog
    f.on_workflow_complete(SimpleNamespace(
        input_dir="0/1 images", output_dir="", worker=worker,
        halted="Signed out.", halted_files=[str(f.src / "a.jpg")], halted_streak=False))
    rows = [dlg.stats_list.GetString(i) for i in range(dlg.stats_list.GetCount())]
    assert not any("Extracting Frames" in r or "more as videos" in r for r in rows), rows
    # A late extraction tick doesn't rebuild over the summary.
    dlg.set_extraction(1, 1, "late.mp4")
    assert [dlg.stats_list.GetString(i) for i in range(dlg.stats_list.GetCount())] == rows
    dlg.Destroy()


def test_selection_follows_its_row_when_rows_are_added_above(_frame):
    """Review finding 6: restoring the selection by index moved a reader from
    "Last Description" to another row when a video finished above it."""
    from batch_progress_dialog import BatchProgressDialog
    dlg = BatchProgressDialog(_frame, 0)
    try:
        dlg.begin_stage("Describing and extracting frames", 4, stage_index=2, stage_count=2)
        dlg.begin_extraction(3)
        dlg.update_progress(1, 4, image_name="a.jpg", last_image="a.jpg",
                            last_description="A cat on a desk.")
        rows = [dlg.stats_list.GetString(i) for i in range(dlg.stats_list.GetCount())]
        target = next(i for i, r in enumerate(rows) if r.startswith("Last Description:"))
        dlg.stats_list.SetSelection(target)
        dlg.set_extraction(1, 3, "clip.mp4")          # adds a row above it
        sel = dlg.stats_list.GetString(dlg.stats_list.GetSelection())
        assert sel.startswith("Last Description:"), sel
        dlg.end_extraction()                          # removes two rows above
        sel = dlg.stats_list.GetString(dlg.stats_list.GetSelection())
        assert sel.startswith("Last Description:"), sel
    finally:
        dlg.Destroy()


def test_waiting_for_frames_is_not_counted_as_describing_time(frame, monkeypatch):
    """Review finding 7: a five-minute wait for a long video counted as one
    image taking five minutes, and the title read 100% with videos to come."""
    f = frame
    monkeypatch.setattr(f, "batch_start_time", time.time() - 10.0)
    monkeypatch.setattr(f, "batch_processing_times", [])
    evt = SimpleNamespace(message="Processing 6/6", current=6, total=6,
                          file_path=str(f.src / "a.jpg"), waited=9.5, more_coming=True)
    f.on_worker_progress(evt)
    assert f.batch_processing_times[-1] < 1.0
    assert "100%" not in f.GetTitle() and "extracting videos" in f.GetTitle()
    evt.more_coming = False
    f.on_worker_progress(evt)
    assert f.GetTitle().startswith("100%, 6 of 6")


def test_pause_while_waiting_for_frames_holds_the_next_one(monkeypatch):
    """Review finding 9: Pause pressed while the worker waited for frames
    still described the next frame to arrive."""
    w, events = _real_batch(monkeypatch, [], queue_open=True)
    w.start()
    time.sleep(0.2)
    w.pause()
    w.add_files(["f1.jpg"])
    time.sleep(0.4)
    assert _InstantImage.seen == [], "described while paused"
    w.resume()
    assert _pump_until(lambda: _InstantImage.seen == ["f1.jpg"])
    w.close_queue()
    w.join(5)
    assert not w.is_alive()


def test_stale_frames_of_a_reextracted_video_are_not_described_alongside(frame, monkeypatch):
    """Review finding 10: frames left by an interrupted extraction were both
    in the image list and re-queued, and described while extraction cleared
    their folder."""
    from data_models import ImageItem
    f = frame
    stale = f.src / "clip_0.00s.jpg"
    stale.write_bytes(b"x")
    it = ImageItem(str(stale), "extracted_frame")
    it.parent_video = str(f.src / "clip.mp4")
    f.workspace.add_item(it)
    release, calls = _slow_extraction(monkeypatch, f, [])
    f._extract_then_launch([str(f.src / "clip.mp4")],
                           [str(f.src / "a.jpg"), str(stale)], OPTIONS, True)
    assert _pump_until(lambda: calls)
    assert _FakeWorker.instances[-1].file_paths == [str(f.src / "a.jpg")]
    release.set()


def test_last_image_finishing_during_a_cancelled_close_still_says_stopped(frame, monkeypatch):
    """Re-review of #350: the stopped worker's completion arriving while
    "save changes?" was open took the normal path ("Batch complete", a save
    inside the question), and the cancelled close then said nothing."""
    f = frame
    worker = _pipeline_running(f, monkeypatch, _LingeringWorker)
    saves = []
    real_save = f._save_bundle_with_progress

    def question():
        worker.finish()                  # its last image is done...
        f.on_workflow_complete(SimpleNamespace(   # ...while the question is open
            input_dir="1/1 images", output_dir="", worker=worker,
            halted=None, halted_files=[], halted_streak=False))
        assert saves == [], "saved inside the save-changes question"
        return False                     # Cancel: stay
    monkeypatch.setattr(f, "_save_bundle_with_progress",
                        lambda: (saves.append(1), real_save())[1])
    monkeypatch.setattr(f, "confirm_unsaved_changes", question)
    f.on_close(SimpleNamespace(CanVeto=lambda: True, Veto=lambda: None))
    assert _pump_until(lambda: f._run_cancel is None)
    stops = [m for m in f.infos if "Batch processing stopped" in m]
    assert len(stops) == 1 and "before describing" not in stops[0], f.infos
    assert "Batch complete" not in f.GetStatusBar().GetStatusText(0)
    assert f.workspace.batch_state is None


# ----- #352: post-merge review of #350 ----- #

def _batch_done(worker):
    return SimpleNamespace(input_dir="1/1 images", output_dir="", worker=worker,
                           halted=None, halted_files=[], halted_streak=False)


def _close_with_late_completion(f, monkeypatch, answer):
    """on_close with the usual real ordering: extraction hands back (ending
    the run) while "save changes?" is open, and only then does the stopped
    worker's last image finish. Returns what happened inside the question."""
    worker = _pipeline_running(f, monkeypatch, _LingeringWorker)
    saves, seen = [], {}
    real_save = f._save_bundle_with_progress
    monkeypatch.setattr(f, "_save_bundle_with_progress",
                        lambda: (saves.append(1), real_save())[1])

    def question():
        assert _pump_until(lambda: f._run_cancel is None)   # extraction ended first
        worker.finish()
        f.on_workflow_complete(_batch_done(worker))
        seen["saves"] = len(saves)
        seen["status"] = f.GetStatusBar().GetStatusText(0)
        seen["batch_state"] = f.workspace.batch_state
        return answer
    monkeypatch.setattr(f, "confirm_unsaved_changes", question)
    monkeypatch.setattr(f, "Destroy", lambda: None)
    f.on_close(SimpleNamespace(CanVeto=lambda: True, Veto=lambda: None))
    return seen


def test_late_completion_during_a_cancelled_close_is_still_a_stop(frame, monkeypatch):
    """#352 item 1: the closing branch read the close off the run, which
    extraction usually ends first; the completion then saved inside the
    question and said "Batch complete"."""
    f = frame
    seen = _close_with_late_completion(f, monkeypatch, answer=False)   # Cancel
    assert seen["saves"] == 0, "saved inside the save-changes question"
    assert "Batch complete" not in seen["status"]
    stops = [m for m in f.infos if "Batch processing stopped" in m]
    assert len(stops) == 1, f.infos
    assert f.workspace.batch_state is None


def test_late_completion_during_a_quit_keeps_the_batch_to_resume(frame, monkeypatch):
    """Quitting (Don't Save) must leave the batch on disk for the next open to
    offer to resume; the normal completion path cleared it."""
    f = frame
    seen = _close_with_late_completion(f, monkeypatch, answer=True)    # quit
    assert seen["saves"] == 0
    assert "Batch complete" not in seen["status"]
    assert seen["batch_state"] is not None
    on_disk = Workspace.open(Path(f.workspace_file)).batch_state
    assert on_disk is not None
    assert f.infos == []


def test_cancelled_close_of_a_batch_without_videos_is_a_stop(frame, monkeypatch):
    """A plain describe batch stopped by a close that was then cancelled: its
    completion announced "Batch complete" for a batch that had been stopped."""
    import imagedescriber_wx
    f = frame
    monkeypatch.setattr(imagedescriber_wx, "BatchProcessingWorker", _LingeringWorker)
    f._launch_batch([str(f.src / "a.jpg")], OPTIONS, True)
    assert _pump_until(lambda: _FakeWorker.instances and _FakeWorker.instances[-1].started)
    worker = _FakeWorker.instances[-1]
    _veto_close(f, monkeypatch)
    assert f._stopping_worker is worker
    worker.finish()
    f.on_workflow_complete(_batch_done(worker))
    stops = [m for m in f.infos if "Batch processing stopped" in m]
    assert len(stops) == 1, f.infos
    assert "Batch complete" not in f.GetStatusBar().GetStatusText(0)
    assert not getattr(worker, "stopped_by_close", False)


def test_describe_worker_crash_stops_extraction_and_frees_the_batch(frame, monkeypatch):
    """#352 item 6: a crashed describe worker left extraction running for a
    batch that was gone, and new runs refused as "already running"."""
    f = frame
    worker = _pipeline_running(f, monkeypatch)
    run = f._run_cancel
    f.on_workflow_failed(SimpleNamespace(error="Batch processing failed: boom", worker=worker))
    assert run.is_set()
    assert _pump_until(lambda: f._run_cancel is None)
    assert f.batch_worker is None
    assert f._batch_busy_message() is None
    assert f.batch_progress_dialog is None
    assert f.workspace.batch_state is not None, "reopening should offer to resume"
    assert any("boom" in m for m in f.infos)
    # The extraction it cancelled ends quietly: this handler said what happened.
    assert not any("Batch processing stopped" in m for m in f.infos), f.infos


def test_videos_giving_no_frames_without_an_error_say_so(frame, monkeypatch):
    """#352 item 4: an empty result with no exception said "All images
    already have descriptions"."""
    f = frame
    monkeypatch.setattr(f, "_extract_video_frames_sync", lambda vp, *a, **k: ([], {}))
    f._extract_then_launch([str(f.src / "clip.mp4")], [], OPTIONS, True)
    assert _pump_until(lambda: f._run_cancel is None)
    assert any("No frames could be extracted" in m for m in f.infos), f.infos
    assert not any("already have descriptions" in m for m in f.infos)


def _stats_rows(dlg):
    return [dlg.stats_list.GetString(i) for i in range(dlg.stats_list.GetCount())]


@pytest.mark.parametrize("target", ["Provider", "Model", "Prompt Style",
                                    "Last Image Described", "Average Processing Time"])
def test_selected_row_is_kept_when_extraction_ends(_frame, target):
    """#352 item 2: the restore checked the old row number against the NEW
    list's separators, so a reader on "Model" landed on "Last Image
    Described" when the extraction rows above went away."""
    from batch_progress_dialog import BatchProgressDialog
    dlg = BatchProgressDialog(_frame, 0, batch_provider="ollama",
                              batch_model="m", batch_prompt="d")
    try:
        dlg.begin_stage("Describing and extracting frames", 10, stage_index=2, stage_count=2)
        dlg.begin_extraction(3)
        dlg.update_progress(2, 10, file_path="/x/a.jpg", avg_time=3.0,
                            last_image="a.jpg", last_description="A cat.")
        dlg.set_extraction(1, 3, "clip.mp4")
        row = next(i for i, r in enumerate(_stats_rows(dlg)) if r.startswith(target + ":"))
        dlg.stats_list.SetSelection(row)
        dlg.end_extraction()
        assert dlg.stats_list.GetString(dlg.stats_list.GetSelection()).startswith(target + ":")
    finally:
        dlg.Destroy()


def test_gauge_and_estimate_wait_for_the_total_while_extracting(_frame, monkeypatch):
    """#352 item 3: the gauge was a percentage of a growing total (100%, then
    50%), and the estimate counted only frames queued so far."""
    from batch_progress_dialog import BatchProgressDialog
    dlg = BatchProgressDialog(_frame, 0)
    try:
        values = []
        real = dlg.progress_bar.SetValue
        monkeypatch.setattr(dlg.progress_bar, "SetValue", lambda v: (values.append(v), real(v)))
        dlg.begin_extraction(3)
        dlg.update_progress(5, 5, avg_time=2.0)
        dlg.update_progress(6, 12, avg_time=2.0)
        assert values == [], "a percentage of a total still growing"
        assert not any(r.startswith("Estimated Time Remaining") for r in _stats_rows(dlg))
        dlg.end_extraction()
        dlg.update_progress(6, 12, avg_time=2.0)
        assert values and values[-1] == 50
        assert any(r.startswith("Estimated Time Remaining") for r in _stats_rows(dlg))
    finally:
        dlg.Destroy()


def _pending(f, name, position):
    from data_models import ImageItem
    path = f.src / name
    path.write_bytes(b"x")
    item = ImageItem(str(path))
    item.processing_state = "pending"
    item.batch_queue_position = position
    f.workspace.add_item(item)


def test_resume_prompt_counts_from_the_items_not_a_stale_total(frame, monkeypatch):
    """#352 item 5: after a crash the manifest's total lagged the frames
    queued since, and the prompt read "0 of 1 completed / Remaining: 3"."""
    f = frame
    for i, pos in enumerate((3, 4, 5)):
        _pending(f, f"f{i}.jpg", pos)
    f.workspace.batch_state = {"total_queued": 1, "provider": "ollama",
                               "model": "m", "prompt_style": "d"}
    f.answer = False
    f.prompt_resume_batch()
    assert "Progress: 3 of 6 images completed" in f.questions[-1], f.questions[-1]
    assert "Remaining: 3 images" in f.questions[-1]


def test_resume_prompt_with_only_videos_left(frame, monkeypatch):
    f = frame
    f.workspace.batch_state = {"total_queued": 2, "provider": "ollama", "model": "m",
                               "prompt_style": "d", "videos": [str(f.src / "clip.mp4")]}
    f.answer = False
    f.prompt_resume_batch()
    assert "Remaining: 1 video to extract frames from" in f.questions[-1], f.questions[-1]
    assert "0 images" not in f.questions[-1]


def test_resuming_while_extracting_shows_no_percentage(frame, monkeypatch):
    """#352: Resume after Pause showed "100%, 3 of 3" while videos were still
    adding frames."""
    f = frame
    worker = _FakeWorker(None, [], queue_open=True)
    worker.started = True
    worker.queue_open = True
    worker.pause = worker.resume = lambda: None
    monkeypatch.setattr(f, "batch_worker", worker)
    monkeypatch.setattr(f, "batch_progress",
                        {"current": 3, "total": 3, "file_path": str(f.src / "a.jpg")},
                        raising=False)
    monkeypatch.setattr(f, "_save_bundle_with_progress", lambda: None)
    f.on_pause_batch()
    f.on_resume_batch()
    assert "%" not in f.GetTitle(), f.GetTitle()
    assert "extracting videos" in f.GetTitle()


def _halted_done(worker, path):
    return SimpleNamespace(input_dir="1/1 images", output_dir="", worker=worker,
                           halted="Claude Code is not signed in. Run: claude auth login",
                           halted_files=[path], halted_streak=False)


def _close_with_halt(f, monkeypatch, answer, inside=None, extracting=False):
    """The batch's last image, in flight as the app closes, halts it.
    `inside` records what happened while "save changes?" was open: a save or
    a question there is the bug (main asked "resume?" inside the question).
    With `extracting`, a video is still being extracted alongside."""
    import imagedescriber_wx
    a = str(f.src / "a.jpg")
    if extracting:
        worker = _pipeline_running(f, monkeypatch, _LingeringWorker)
    else:
        monkeypatch.setattr(imagedescriber_wx, "BatchProcessingWorker", _LingeringWorker)
        f._launch_batch([a], OPTIONS, True)
        assert _pump_until(lambda: _FakeWorker.instances and _FakeWorker.instances[-1].started)
        worker = _FakeWorker.instances[-1]
    saves = []
    real_save = f._save_bundle_with_progress
    monkeypatch.setattr(f, "_save_bundle_with_progress",
                        lambda: (saves.append(1), real_save())[1])

    def question():
        f.workspace.items[a].processing_state = "failed"   # as its failure set it
        f._checkpoint_item(a)                              # ...and saved it
        worker.finish()
        asked_before = len(f.questions)
        f.on_workflow_complete(_halted_done(worker, a))
        if inside is not None:
            inside["saves"] = len(saves)
            inside["questions"] = len(f.questions) - asked_before
        return answer
    monkeypatch.setattr(f, "confirm_unsaved_changes", question)
    monkeypatch.setattr(f, "Destroy", lambda: None)
    f.on_close(SimpleNamespace(CanVeto=lambda: True, Veto=lambda: None))
    return a


def test_a_halt_during_a_quit_is_requeued_for_resume(frame, monkeypatch):
    """PR 353 review: the close's early return skipped the halt's requeue, so
    the image a sign-out halted on stayed "failed" and resume skipped it."""
    f = frame
    inside = {}
    a = _close_with_halt(f, monkeypatch, answer=True, inside=inside)   # quit
    assert inside == {"saves": 0, "questions": 0}, \
        "saved or asked inside the save-changes question"
    gui = bundle_to_gui_workspace_dict(Workspace.open(Path(f.workspace_file)))
    assert gui["items"][a]["processing_state"] == "pending"
    assert gui["batch_state"] is not None


def test_a_halt_during_a_cancelled_close_is_delivered(frame, monkeypatch):
    """...and on a cancelled close the batch was called "stopped" and its
    resume wiped, so the user never heard the halt's reason."""
    f = frame
    f.answer = False                    # "resume now?" -> No, keep it for later
    inside = {}
    a = _close_with_halt(f, monkeypatch, answer=False, inside=inside)  # Cancel
    assert inside == {"saves": 0, "questions": 0}, \
        "saved or asked inside the save-changes question"
    assert not any("Batch processing stopped" in m for m in f.infos), f.infos
    assert any("claude auth login" in q for q in f.questions + f.infos)
    assert f.workspace.items[a].processing_state == "pending"
    assert f.workspace.batch_state is not None


def test_a_worker_that_already_finished_is_not_marked_stopped_by_close(frame, monkeypatch):
    """PR 353 review: a batch that finished on its own, its completion not yet
    handled when Quit was pressed, was treated as stopped by the close."""
    import imagedescriber_wx
    f = frame
    monkeypatch.setattr(imagedescriber_wx, "BatchProcessingWorker", _LingeringWorker)
    f._launch_batch([str(f.src / "a.jpg")], OPTIONS, True)
    assert _pump_until(lambda: _FakeWorker.instances and _FakeWorker.instances[-1].started)
    worker = _FakeWorker.instances[-1]
    worker.finish()                     # done; its completion is still queued
    monkeypatch.setattr(f, "confirm_unsaved_changes", lambda: True)
    monkeypatch.setattr(f, "Destroy", lambda: None)
    f.on_close(SimpleNamespace(CanVeto=lambda: True, Veto=lambda: None))
    assert not getattr(worker, "stopped_by_close", False)


def test_a_halt_during_a_cancelled_close_while_extracting_is_delivered(frame, monkeypatch):
    """PR 353 Windows review: the same, with a video still extracting when the
    halt arrives during the question. The halt's reason is delivered once the
    close is cancelled, extraction stops, and the batch can still be resumed."""
    f = frame
    f.answer = False
    inside = {}
    a = _close_with_halt(f, monkeypatch, answer=False, inside=inside, extracting=True)
    assert _pump_until(lambda: f._run_cancel is None), "extraction never stopped"
    assert inside == {"saves": 0, "questions": 0}
    assert not any("Batch processing stopped" in m for m in f.infos), f.infos
    assert any("claude auth login" in q for q in f.questions + f.infos)
    assert f.workspace.items[a].processing_state == "pending"
    assert f.workspace.batch_state is not None
    assert f.workspace.batch_state.get("videos") == [str(f.src / "clip.mp4")]


def test_a_video_giving_no_frames_is_reported_at_the_end(frame, monkeypatch):
    """PR 353 Windows review: only a video whose extraction raised was
    reported; one that quietly gave no frames was left out of the batch's
    failure summary and silently retried next time."""
    f = frame
    monkeypatch.setattr(f, "_extract_video_frames_sync",
                        lambda vp, cfg, cancel=None, frames_dir=None: ([], {}))
    f._extract_then_launch([str(f.src / "clip.mp4")], [str(f.src / "a.jpg")], OPTIONS, True)
    assert _pump_until(lambda: f._run_cancel is None)
    assert [n for n, _ in f._batch_video_failures] == ["clip.mp4"]
    w = _FakeWorker.instances[-1]
    f.on_workflow_complete(_batch_done(w))
    assert any("could not be extracted from 1 video" in m for m in f.infos), f.infos


def test_a_refusal_halt_offers_to_carry_on_and_leaves_them_failed(frame, monkeypatch):
    """PR 353 Windows review: a refusal halt said "every remaining image would
    fail the same way" and requeued the declined images, so Yes halted again
    on them. They stay failed and the question says what would help."""
    import imagedescriber_wx
    f = frame
    monkeypatch.setattr(imagedescriber_wx, "BatchProcessingWorker", _LingeringWorker)
    a = str(f.src / "a.jpg")
    f._launch_batch([a], OPTIONS, True)
    assert _pump_until(lambda: _FakeWorker.instances and _FakeWorker.instances[-1].started)
    worker = _FakeWorker.instances[-1]
    f.workspace.items[a].processing_state = "failed"
    from data_models import ImageItem
    b = str(f.src / "b.jpg")
    f.workspace.add_item(ImageItem(b))
    f.workspace.items[b].processing_state = "pending"     # not yet tried
    f._batch_video_failures = [("clip.mp4", "no frames could be extracted")]
    worker.finish()
    f.answer = False
    f.on_workflow_complete(_refusal_halt(worker))
    assert f.workspace.items[a].processing_state == "failed"
    assert f.workspace.batch_state is not None
    q = f.questions[-1]
    assert "different prompt style" in q and "carry on with the rest" in q
    assert "every remaining image would fail" not in q
    assert "could not be extracted from 1 video" in q, "video failures went unreported"
    assert "declined" in f.GetStatusBar().GetStatusText(0)


def _refusal_halt(worker):
    return SimpleNamespace(
        input_dir="25/25 images", output_dir="", worker=worker,
        halted="Apple Intelligence declined to describe this image.",
        halted_files=[], halted_streak=False, halted_refusals=True)


def test_a_refusal_halt_with_nothing_left_does_not_offer_to_carry_on(frame, monkeypatch):
    """Re-review: when the declined images were the last of the batch, Yes
    led to "No images to resume processing." Say what happened instead."""
    import imagedescriber_wx
    f = frame
    monkeypatch.setattr(imagedescriber_wx, "BatchProcessingWorker", _LingeringWorker)
    a = str(f.src / "a.jpg")
    f._launch_batch([a], OPTIONS, True)
    assert _pump_until(lambda: _FakeWorker.instances and _FakeWorker.instances[-1].started)
    worker = _FakeWorker.instances[-1]
    f.workspace.items[a].processing_state = "failed"
    worker.finish()
    asked = len(f.questions)
    f.on_workflow_complete(_refusal_halt(worker))
    assert len(f.questions) == asked
    assert any("different prompt style" in m for m in f.infos)
    assert f.workspace.batch_state is None


# ----- #352, the items #353 left ----- #

def test_worker_says_when_it_waits_for_frames(monkeypatch):
    import workers_wx
    w, _ = _real_batch(monkeypatch, ["a.jpg"], queue_open=True)
    posted = []
    monkeypatch.setattr(workers_wx.wx, "PostEvent", lambda _t, e: posted.append(e))
    w.start()
    assert _pump_until(lambda: any(getattr(e, "waiting_for_frames", False) for e in posted))
    w.close_queue()
    w.join(5)
    waits = [e for e in posted if getattr(e, "waiting_for_frames", False)]
    assert len(waits) == 1, "posted more than once for one wait"


def test_waiting_for_frames_replaces_the_stale_current_image(frame, monkeypatch):
    """#352: while the worker waited for frames, the window kept showing the
    last image as the one being described."""
    f = frame
    _pipeline_running(f, monkeypatch)
    dlg = f.batch_progress_dialog
    dlg.update_progress(1, 1, file_path=str(f.src / "a.jpg"))
    progress_before = f.batch_progress
    times_before = list(f.batch_processing_times)
    f.on_worker_progress(SimpleNamespace(message="Waiting for the next video's frames…",
                                         current=0, total=1, file_path="",
                                         waiting_for_frames=True))
    rows = [dlg.stats_list.GetString(i) for i in range(dlg.stats_list.GetCount())]
    assert any(r.startswith("Current Image:") and "waiting for the next video" in r
               for r in rows), rows
    assert not any("a.jpg" in r for r in rows if r.startswith("Current"))
    assert f.batch_processing_times == times_before
    assert f.batch_progress is progress_before, "a wait is not an image"
    f._run_cancel.set()


def test_untitled_workspace_has_no_missing_step(frame, monkeypatch):
    """#352: with no bundle there is no save stage, but the window said
    "step 1 of 2" and never reached step 2."""
    f = frame
    monkeypatch.setattr(f, "workspace_file", None)
    release, calls = _slow_extraction(monkeypatch, f, [])
    f._extract_then_launch([str(f.src / "clip.mp4")], [str(f.src / "a.jpg")], OPTIONS, True)
    assert _pump_until(lambda: calls)
    title = f.batch_progress_dialog.GetTitle()
    assert "step" not in title, title
    release.set()


def test_paused_title_stops_saying_extracting_when_extraction_ends(frame, monkeypatch):
    f = frame
    release, calls = _slow_extraction(monkeypatch, f, [])
    f._extract_then_launch([str(f.src / "clip.mp4")], [str(f.src / "a.jpg")], OPTIONS, True)
    assert _pump_until(lambda: calls)
    worker = _FakeWorker.instances[-1]
    worker.is_paused = lambda: True
    f.batch_progress = {"current": 1, "total": 1, "file_path": str(f.src / "a.jpg")}
    f._set_batch_title(paused=True)
    assert "extracting videos" in f.GetTitle()
    release.set()
    assert _pump_until(lambda: f._run_cancel is None)
    assert "extracting videos" not in f.GetTitle()
    assert f.GetTitle().startswith("(Paused) 100%")


def test_a_new_batch_lets_go_of_an_older_batchs_pending_flags(frame, monkeypatch):
    """#352: an older halted batch's pending flags overstated the new batch's
    resume total ("990 of 1000" for a 10-image batch)."""
    from data_models import ImageItem
    f = frame
    old = str(f.src / "old.jpg")
    f.workspace.add_item(ImageItem(old))
    f.workspace.items[old].processing_state = "pending"
    f.workspace.items[old].batch_queue_position = 989
    f._launch_batch([str(f.src / "a.jpg")], OPTIONS, True)
    assert _pump_until(lambda: _FakeWorker.instances and _FakeWorker.instances[-1].started)
    assert f.workspace.items[old].processing_state is None
    assert f.workspace.items[old].batch_queue_position is None
    assert f.workspace.items[str(f.src / "a.jpg")].processing_state == "pending"


def test_cancelled_close_keeps_the_window_while_extraction_stops(frame, monkeypatch):
    """#352: when the last image had finished during the question, a cancelled
    close left only the status bar's "Stopping…" until extraction let go."""
    f = frame
    worker = _pipeline_running(f, monkeypatch, _LingeringWorker)
    dlg = f.batch_progress_dialog
    seen = {}

    def question():
        worker.finish()                   # its last image is done; completion pending
        return False                      # Cancel
    monkeypatch.setattr(f, "confirm_unsaved_changes", question)
    f.on_close(SimpleNamespace(CanVeto=lambda: True, Veto=lambda: None))
    seen["dialog"] = f.batch_progress_dialog
    seen["title"] = dlg.GetTitle() if dlg else ""
    assert seen["dialog"] is dlg, "the batch's window wasn't kept while stopping"
    assert dlg.IsShown() and "Stopping" in seen["title"]
    assert _pump_until(lambda: f._run_cancel is None)
    stops = [m for m in f.infos if "Batch processing stopped" in m]
    assert len(stops) == 1, f.infos


def test_already_described_frames_and_a_failed_video_report_both(frame, monkeypatch, tmp_path):
    """#352: one video's frames all already described and another giving none
    said only "All images already have descriptions."."""
    from data_models import ImageItem, ImageDescription
    f = frame
    v2 = f.src / "clip2.mp4"
    v2.write_bytes(b"x")
    f.workspace.add_item(ImageItem(str(v2), "video"))
    done = tmp_path / "clip_0.00s.jpg"
    done.write_bytes(b"x")
    it = ImageItem(str(done), "extracted_frame")
    it.descriptions.append(ImageDescription(text="already"))
    f.workspace.add_item(it)

    def extract(vp, cfg, cancel=None, frames_dir=None):
        if Path(vp).name == "clip.mp4":
            return [str(done)], {}
        raise OSError("not a video")
    monkeypatch.setattr(f, "_extract_video_frames_sync", extract)
    f._extract_then_launch([str(f.src / "clip.mp4"), str(v2)], [], OPTIONS, True)
    assert _pump_until(lambda: f._run_cancel is None)
    msgs = [m for m in f.infos if "already have descriptions" in m]
    assert msgs and "could not be extracted from 1 video" in msgs[0] and "not a video" in msgs[0]


def test_final_stats_count_the_last_failure(_frame):
    """vmtest run: the stats read "Failed: 3" over a "4 failed" summary; the
    last image's failure was counted but never redrawn."""
    from batch_progress_dialog import BatchProgressDialog
    dlg = BatchProgressDialog(_frame, 4)
    try:
        dlg.begin_stage("Describing", 4)
        for n in range(1, 5):
            dlg.update_progress(n, 4, image_name=f"{n}.jpg")
            dlg.note_failure(f"{n}.jpg", "refused")   # after its progress update
        dlg.mark_complete("4/4 images (4 failed)")
        rows = [dlg.stats_list.GetString(i) for i in range(dlg.stats_list.GetCount())]
        failed = [r for r in rows if r.startswith("Failed:")]
        assert failed and failed[0].split()[-1] == "4", rows
    finally:
        dlg.Destroy()


# ----- #355 review ----- #

def test_yes_to_resume_resumes_once_extraction_lets_go(frame, monkeypatch):
    """#352: after a halt whose extraction thread outlived the 30 s wait, Yes
    was refused as busy. Now it resumes when the thread lets go, with the
    progress window saying so meanwhile and the app not blocked."""
    import imagedescriber_wx
    f = frame
    let_go = threading.Event()

    def extract(vp, cfg, cancel=None, frames_dir=None):
        while not cancel.is_set():
            time.sleep(0.01)
        assert let_go.wait(10)            # a share slow to release the video
        raise imagedescriber_wx.ExtractionCancelled(Path(vp).name)
    monkeypatch.setattr(f, "_extract_video_frames_sync", extract)
    f._extract_then_launch([str(f.src / "clip.mp4")], [str(f.src / "a.jpg")], OPTIONS, True)
    assert _pump_until(lambda: _extracting(f))
    worker = _FakeWorker.instances[-1]
    monkeypatch.setattr(f, "_wait_for_extraction", lambda run, timeout=5.0: None)  # timed out
    resumed = []
    monkeypatch.setattr(f, "resume_batch_processing",
                        lambda: resumed.append(f._batch_busy_message()))
    f.answer = True                                    # "resume now?" Yes
    f.on_workflow_complete(SimpleNamespace(
        input_dir="0/1 images", output_dir="", worker=worker,
        halted="Claude Code is not signed in.", halted_files=[str(f.src / "a.jpg")],
        halted_streak=False, halted_refusals=False))
    assert resumed == [], "resumed while extraction still held the video"
    dlg = f.batch_progress_dialog
    assert dlg is not None and "Resuming once frame extraction stops" in dlg.GetTitle()
    let_go.set()
    assert _pump_until(lambda: resumed)
    assert resumed == [None], "refused as busy"
    assert f.batch_progress_dialog is None or f.batch_progress_dialog is not dlg


def test_paused_title_counts_frames_queued_as_extraction_ends(frame, monkeypatch, tmp_path):
    """#355 review: paused at 1 of 1, a video then adds frames; the title read
    "(Paused) 100%, 1 of 1" with them still to describe."""
    f = frame
    frames = []
    for n in range(3):
        fr = tmp_path / f"clip_{n}.00s.jpg"
        fr.write_bytes(b"x")
        frames.append(str(fr))
    gate = threading.Event()

    def extract(vp, cfg, cancel=None, frames_dir=None):
        assert gate.wait(10)
        return frames, {}
    monkeypatch.setattr(f, "_extract_video_frames_sync", extract)
    f._extract_then_launch([str(f.src / "clip.mp4")], [str(f.src / "a.jpg")], OPTIONS, True)
    assert _pump_until(lambda: _extracting(f))
    worker = _FakeWorker.instances[-1]
    worker.is_paused = lambda: True
    worker.progress_offset = 0
    f.batch_progress = {"current": 1, "total": 1, "file_path": str(f.src / "a.jpg")}
    gate.set()
    assert _pump_until(lambda: f._run_cancel is None)
    assert f.GetTitle().startswith("(Paused) 25%, 1 of 4"), f.GetTitle()


def test_title_drops_extracting_when_extraction_ends_unpaused(frame, monkeypatch):
    f = frame
    release, calls = _slow_extraction(monkeypatch, f, [])
    f._extract_then_launch([str(f.src / "clip.mp4")], [str(f.src / "a.jpg")], OPTIONS, True)
    assert _pump_until(lambda: calls)
    worker = _FakeWorker.instances[-1]
    worker.is_paused = lambda: False
    worker.progress_offset = 0
    f.batch_progress = {"current": 1, "total": 1, "file_path": str(f.src / "a.jpg")}
    f._set_batch_title()
    assert "extracting videos" in f.GetTitle()
    release.set()
    assert _pump_until(lambda: f._run_cancel is None)
    assert f.GetTitle().startswith("100%, 1 of 1"), f.GetTitle()


def test_waiting_line_is_not_left_in_the_final_summary(_frame):
    """#355 review: describing waited, the last video gave nothing new, and
    the completed window still said it was waiting, above "Batch Complete"."""
    from batch_progress_dialog import BatchProgressDialog
    dlg = BatchProgressDialog(_frame, 3)
    try:
        dlg.begin_stage("Describing and extracting frames", 3, stage_index=2, stage_count=2)
        dlg.begin_extraction(2)
        dlg.update_progress(3, 3, file_path="3.jpg")
        dlg.show_waiting_for_frames()
        dlg.end_extraction()
        dlg.mark_complete("3/3 images")
        rows = [dlg.stats_list.GetString(i) for i in range(dlg.stats_list.GetCount())]
        assert not any("waiting" in r for r in rows), rows
        assert not any(r.startswith("Current") for r in rows), rows
    finally:
        dlg.Destroy()


def test_a_failed_start_puts_back_the_older_halted_batch(frame, monkeypatch):
    """#355 review: a batch halted (resume declined), a new batch then failed
    to start, and the older batch's resume state was gone."""
    from data_models import ImageItem
    f = frame
    old = str(f.src / "old.jpg")
    shared = str(f.src / "a.jpg")
    f.workspace.add_item(ImageItem(old))
    older = {"provider": "ollama", "model": "m", "total_queued": 2}
    f.workspace.batch_state = older
    for fp, pos in ((old, 0), (shared, 1)):
        f.workspace.items[fp].processing_state = "pending"
        f.workspace.items[fp].batch_queue_position = pos

    def cannot_start():
        raise RuntimeError("can't start new thread")
    f._launch_batch([shared], OPTIONS, True, extraction=cannot_start,
                    extraction_videos=[str(f.src / "clip.mp4")])
    assert _pump_until(lambda: f._run_cancel is None)
    assert any("could not start" in m for m in f.infos)
    assert f.workspace.batch_state is older
    assert (f.workspace.items[old].processing_state, f.workspace.items[old].batch_queue_position) == ("pending", 0)
    assert (f.workspace.items[shared].processing_state, f.workspace.items[shared].batch_queue_position) == ("pending", 1)


@pytest.mark.parametrize("entry", ["downloads", "frames"])
def test_every_batch_start_lets_go_of_an_older_batchs_flags(frame, monkeypatch, entry):
    """#355 review: only one of the ways a batch starts cleared them."""
    import imagedescriber_wx
    from data_models import ImageItem
    f = frame
    old = str(f.src / "old.jpg")
    f.workspace.add_item(ImageItem(old))
    f.workspace.items[old].processing_state = "pending"
    f.workspace.items[old].batch_queue_position = 989
    a = str(f.src / "a.jpg")
    if entry == "downloads":
        f.auto_process_downloaded_images([a], dict(OPTIONS))
    else:
        class _Dialog:
            def __init__(self, *a, **k):
                pass

            def ShowModal(self):
                return wx.ID_OK

            def get_config(self):
                return dict(OPTIONS)

            def Destroy(self):
                pass
        monkeypatch.setattr(imagedescriber_wx, "ProcessingOptionsDialog", _Dialog)
        monkeypatch.setattr(f, "_persist_processing_options", lambda o: None)
        f.auto_process_extracted_frames([a])
    assert f.workspace.items[old].processing_state is None
    assert f.workspace.items[a].processing_state == "pending"


def test_stats_and_summary_agree_after_a_streak_halt(frame, monkeypatch):
    """#355 review: ten identical failures halt and are requeued; the summary
    left them out of "failed" but the stats still read "Failed: 10"."""
    import imagedescriber_wx
    f = frame
    monkeypatch.setattr(imagedescriber_wx, "BatchProcessingWorker", _LingeringWorker)
    f._launch_batch([str(f.src / "a.jpg")], OPTIONS, True)
    assert _pump_until(lambda: _FakeWorker.instances and _FakeWorker.instances[-1].started)
    worker = _FakeWorker.instances[-1]
    dlg = f.batch_progress_dialog
    streak = [str(f.src / f"s{n}.jpg") for n in range(10)]
    dlg.update_progress(10, 10, file_path=streak[-1])
    for fp in streak:
        f._batch_failures += 1
        dlg.note_failure(Path(fp).name, "same error")
    worker.finish()
    f.answer = False
    f.on_workflow_complete(SimpleNamespace(
        input_dir="10/10 images", output_dir="", worker=worker,
        halted="Same error ten times.", halted_files=streak,
        halted_streak=True, halted_refusals=False))
    rows = [dlg.stats_list.GetString(i) for i in range(dlg.stats_list.GetCount())]
    assert not any(r.startswith("Failed:") for r in rows), rows
    assert not any("failed)" in r for r in rows), rows
    dlg.Destroy()


def _halt_while_extraction_holds_a_video(f, monkeypatch):
    """A batch halts (answer Yes to resume) while its extraction thread is
    still letting go of a video. Returns (let_go event, resumed calls)."""
    import imagedescriber_wx
    let_go = threading.Event()

    def extract(vp, cfg, cancel=None, frames_dir=None):
        while not cancel.is_set():
            time.sleep(0.01)
        assert let_go.wait(10)
        raise imagedescriber_wx.ExtractionCancelled(Path(vp).name)
    monkeypatch.setattr(f, "_extract_video_frames_sync", extract)
    f._extract_then_launch([str(f.src / "clip.mp4")], [str(f.src / "a.jpg")], OPTIONS, True)
    assert _pump_until(lambda: _extracting(f))
    worker = _FakeWorker.instances[-1]
    monkeypatch.setattr(f, "_wait_for_extraction", lambda run, timeout=5.0: None)
    resumed = []
    monkeypatch.setattr(f, "resume_batch_processing",
                        lambda: resumed.append(f._batch_busy_message()))
    f.answer = True
    f.on_workflow_complete(SimpleNamespace(
        input_dir="0/1 images", output_dir="", worker=worker,
        halted="Claude Code is not signed in.", halted_files=[str(f.src / "a.jpg")],
        halted_streak=False, halted_refusals=False))
    assert resumed == []
    return let_go, resumed


def test_stop_on_the_resuming_window_is_a_real_stop(frame, monkeypatch):
    """#355 re-review A: the waiting window offered Pause and Stop with no
    worker behind them; Stop then ended silently and resumed nothing."""
    f = frame
    let_go, resumed = _halt_while_extraction_holds_a_video(f, monkeypatch)
    dlg = f.batch_progress_dialog
    assert dlg.stop_button.IsEnabled() and not dlg.pause_button.IsEnabled()
    f.infos.clear()
    f.on_stop_batch()
    let_go.set()
    assert _pump_until(lambda: f._run_cancel is None)
    assert resumed == [], "resumed a batch the user stopped"
    assert any("Batch processing stopped" in m for m in f.infos), f.infos
    assert f.workspace.batch_state is None
    on_disk = Workspace.open(Path(f.workspace_file)).batch_state
    assert on_disk is None
    assert f._batch_active is False


@pytest.mark.parametrize("lets_go_during_question", [True, False])
def test_a_cancelled_quit_while_waiting_to_resume_still_resumes(frame, monkeypatch,
                                                               lets_go_during_question):
    """#355 re-review B: the resume was dropped without a word and the app
    was left half in a batch (_batch_active stuck True)."""
    f = frame
    let_go, resumed = _halt_while_extraction_holds_a_video(f, monkeypatch)

    def question():
        if lets_go_during_question:
            let_go.set()
            assert _pump_until(lambda: f._run_cancel is None)
        return False                                   # Cancel: stay
    monkeypatch.setattr(f, "confirm_unsaved_changes", question)
    f.on_close(SimpleNamespace(CanVeto=lambda: True, Veto=lambda: None))
    if not lets_go_during_question:
        dlg = f.batch_progress_dialog
        assert dlg is not None and dlg.IsShown(), "the waiting window went away"
        let_go.set()
    assert _pump_until(lambda: resumed)
    assert resumed == [None]
    assert f._batch_active is False
