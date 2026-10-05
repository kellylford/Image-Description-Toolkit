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
    assert _pump_until(lambda: _FakeWorker.instances)
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
    assert _pump_until(lambda: _FakeWorker.instances), "describing never started"
    assert not f.workspace.items[str(f.src / "clip.mp4")].extracted_frames
    assert len(f.workspace.items[str(v2)].extracted_frames) == 1


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
    assert _FakeWorker.instances == []


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
    # Extraction, then the real _launch_batch through its save stage.
    assert _pump_until(lambda: _FakeWorker.instances and _FakeWorker.instances[-1].started)
    assert f._batch_video_failures == [("clip.mp4", "not a video")]

    w = _FakeWorker.instances[-1]
    f.on_workflow_complete(SimpleNamespace(input_dir="1/1 images", output_dir="",
                                           worker=w, halted=None, halted_files=[]))
    assert any("could not be extracted from 1 video" in m and "not a video" in m
               for m in f.infos)


def test_stop_during_extraction_announces_after_the_save(frame, monkeypatch):
    """The "stopped" message used to appear at once; the save's progress window
    then took focus from it while a screen reader was reading it. The progress
    window now says it is stopping until the (real) save is done, and the save
    never reads as the batch's next step."""
    import imagedescriber_wx
    from data_models import ImageItem
    f = frame
    order = []
    done_frame = f.src / "clip_0.00s.jpg"
    done_frame.write_bytes(b"x")
    v2 = f.src / "clip2.mp4"
    v2.write_bytes(b"x")
    f.workspace.add_item(ImageItem(str(v2), "video"))
    second = []

    def extract(vp, cfg, cancel=None, frames_dir=None):
        if Path(vp).name == "clip.mp4":
            return [str(done_frame)], {}
        second.append(vp)
        while not cancel.is_set():
            time.sleep(0.01)
        raise imagedescriber_wx.ExtractionCancelled(Path(vp).name)
    monkeypatch.setattr(f, "_extract_video_frames_sync", extract)
    real_save = f._save_bundle
    monkeypatch.setattr(f, "_save_bundle",
                        lambda *a, **k: (order.append("save"), real_save(*a, **k))[1])
    monkeypatch.setattr(imagedescriber_wx, "show_info",
                        lambda _p, msg, *a, **k: order.append("message"))
    f._extract_then_launch([str(f.src / "clip.mp4"), str(v2)], [], OPTIONS, True)
    assert _pump_until(lambda: second)
    dlg = f.batch_progress_dialog
    titles, lists = [], []
    real_set_title = dlg.SetTitle

    def set_title(t):
        titles.append(t)
        real_set_title(t)
    monkeypatch.setattr(dlg, "SetTitle", set_title)
    real_update = dlg.update_progress

    def update(*a, **k):
        real_update(*a, **k)
        lists.append([dlg.stats_list.GetString(i) for i in range(dlg.stats_list.GetCount())])
    monkeypatch.setattr(dlg, "update_progress", update)

    f.on_stop_batch()
    assert order == [], "announced before the run had wound down"
    assert _pump_until(lambda: f._run_cancel is None)
    assert order[0] == "save" and order[-1] == "message"
    assert titles and all("Stopping" in t for t in titles), titles
    assert not any("step" in t for t in titles), titles
    assert lists and all(any("Stopping" in line for line in rows) for rows in lists)
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
    assert any("stopped before describing" in m for m in f.infos), \
        "the run the cancelled close stopped should still say so"

    # A later run and Stop still announce.
    f.infos.clear()
    calls.clear()
    f._extract_then_launch([str(f.src / "clip.mp4")], [], OPTIONS, True)
    assert _pump_until(lambda: calls)
    f.on_stop_batch()
    assert _pump_until(lambda: f._run_cancel is None)
    assert any("stopped before describing" in m for m in f.infos)


def test_scan_finishing_mid_run_keeps_the_runs_window_and_embed_choice(frame, monkeypatch):
    """A folder scan completing while a run extracted frames closed the run's
    progress window, and with it reset "embed after processing"."""
    f = frame
    release, calls = _slow_extraction(monkeypatch, f, [])
    opts = dict(OPTIONS, embed_after_process=True)
    f._batch_embed = True
    f._extract_then_launch([str(f.src / "clip.mp4")], [], opts, True)
    assert _pump_until(lambda: calls)
    dlg = f.batch_progress_dialog
    f.on_scan_failed(SimpleNamespace(error="share went away"))
    assert f.batch_progress_dialog is dlg
    assert f._batch_embed is True
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
    assert Workspace.open(Path(f.workspace_file)).batch_state is None
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
    assert Workspace.open(Path(f.workspace_file)).batch_state is None
    assert any("stopped before describing" in m for m in f.infos)
