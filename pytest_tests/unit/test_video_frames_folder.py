"""Each video's frames get their own folder, in the CLI and ImageDescriber alike.

Frames went to derived/frames/<video name>, so two videos with the same name in
different folders (IMG_0001.MOV from two months) shared one folder and one set
of frame sidecars. The second extraction cleared or overwrote the first's
frames: "file not found", or the first video's frames described with the
second video's pictures.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from idt_core.workspace import (  # noqa: E402
    Workspace, claim_frames_dir, frames_dir_taken, frames_relpath,
)


def test_relpath_mirrors_subfolder():
    assert frames_relpath(Path("C:/s/jan/IMG_0001.mov"), "s/jan") == "frames/s/jan/IMG_0001"
    assert frames_relpath(Path("C:/s/IMG_0001.mov"), None) == "frames/IMG_0001"
    assert frames_relpath(Path("C:/s/IMG_0001.mov"), ".") == "frames/IMG_0001"


def test_relpath_hash_is_stable_and_distinct():
    a = frames_relpath(Path("C:/x/clip.mp4"), None, disambiguate=True)
    b = frames_relpath(Path("C:/y/clip.mp4"), None, disambiguate=True)
    assert a != b
    assert a == frames_relpath(Path("C:/x/clip.mp4"), None, disambiguate=True)


def test_folder_ownership(tmp_path):
    a, b = tmp_path / "a.mp4", tmp_path / "b.mp4"
    a.write_bytes(b"x")
    b.write_bytes(b"x")
    d = tmp_path / "frames" / "clip"
    assert not frames_dir_taken(d, a)
    claim_frames_dir(d, a)
    assert not frames_dir_taken(d, a)
    assert frames_dir_taken(d, b)


def test_moved_owner_does_not_hold_the_folder(tmp_path):
    """A library moved to a new drive must not re-extract into hashed folders."""
    old, new = tmp_path / "old" / "a.mp4", tmp_path / "new" / "a.mp4"
    new.parent.mkdir()
    new.write_bytes(b"x")
    d = tmp_path / "frames" / "a"
    claim_frames_dir(d, old)          # recorded owner no longer exists
    assert not frames_dir_taken(d, new)


def test_owner_compared_case_insensitively_where_the_fs_is(tmp_path):
    if sys.platform not in ("win32", "darwin"):
        pytest.skip("case-sensitive file system")
    a = tmp_path / "Clip.mp4"
    a.write_bytes(b"x")
    d = tmp_path / "frames" / "Clip"
    claim_frames_dir(d, a)
    assert not frames_dir_taken(d, tmp_path / "clip.MP4")


def test_cli_rerun_does_not_duplicate_frames(tmp_path):
    pytest.importorskip("cv2")
    from cli.main import _extract_one_video_into_workspace
    from idt_core.video import VideoExtractionOptions
    src = tmp_path / "phone"
    clip = src / "jan" / "IMG_0001.mp4"
    _video(clip, 20, 90)
    ws = Workspace.create(tmp_path / "w.idtw")
    opts = VideoExtractionOptions(mode="interval", interval_seconds=5.0)
    first = _extract_one_video_into_workspace(ws, clip, opts, src)
    second = _extract_one_video_into_workspace(ws, clip, opts, src)
    assert len(first) == len(second)
    frames = [i for i in ws.items() if i.item_type == "extracted_frame"]
    assert len(frames) == len(first)


def test_cli_keeps_a_legacy_frames_folder(tmp_path):
    """Bundles from older versions put frames in frames/<stem>; keep using it."""
    from cli.main import _previous_frames_rel
    from idt_core.workspace import WorkspaceItem
    ws = Workspace.create(tmp_path / "w.idtw")
    legacy = ws.derived_dir("frames") / "IMG_0001"
    legacy.mkdir(parents=True)
    (legacy / "IMG_0001_0.00s.jpg").write_bytes(b"x")
    video = tmp_path / "phone" / "jan" / "IMG_0001.mp4"
    vwi = WorkspaceItem(image=video.name, source_path=str(video), storage="reference",
                        item_type="video", subfolder="phone/jan")
    vwi.extra["extracted_frames"] = [str(legacy / "IMG_0001_0.00s.jpg")]
    assert _previous_frames_rel(ws, vwi, video) == "frames/IMG_0001"


def _video(path: Path, seconds: int, shade: int):
    cv2 = pytest.importorskip("cv2")
    import numpy as np
    path.parent.mkdir(parents=True, exist_ok=True)
    w = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 10, (64, 48))
    for _ in range(seconds * 10):
        w.write(np.full((48, 64, 3), shade, np.uint8))
    w.release()


def test_cli_same_named_videos_keep_separate_frames(tmp_path):
    """The real CLI extraction path, two IMG_0001.mp4 in different folders."""
    pytest.importorskip("cv2")
    from cli.main import _extract_one_video_into_workspace
    from idt_core.video import VideoExtractionOptions

    src = tmp_path / "phone"
    jan, feb = src / "jan" / "IMG_0001.mp4", src / "feb" / "IMG_0001.mp4"
    _video(jan, 30, 40)
    _video(feb, 10, 200)
    ws = Workspace.create(tmp_path / "w.idtw")
    opts = VideoExtractionOptions(mode="interval", interval_seconds=5.0)

    jan_frames = _extract_one_video_into_workspace(ws, jan, opts, src)
    feb_frames = _extract_one_video_into_workspace(ws, feb, opts, src)

    jan_dirs = {Path(f.source_path).parent for f in jan_frames}
    feb_dirs = {Path(f.source_path).parent for f in feb_frames}
    assert len(jan_dirs) == 1 and len(feb_dirs) == 1 and jan_dirs != feb_dirs
    # Nothing of jan's was deleted or replaced by feb's extraction.
    assert all(Path(f.source_path).exists() for f in jan_frames)
    assert len(jan_frames) > len(feb_frames)
    # Separate sidecars: every frame of both videos is in the bundle.
    frames = [i for i in ws.items() if i.item_type == "extracted_frame"]
    assert len(frames) == len(jan_frames) + len(feb_frames)
    parents = {i.parent_video for i in frames}
    assert len(parents) == 2


def test_cli_and_gui_agree_on_the_layout(tmp_path):
    """A bundle made by one tool reads the same in the other."""
    from idt_core.workspace import source_relative_subfolder
    src = tmp_path / "phone"
    video = src / "jan" / "IMG_0001.mp4"
    sub = source_relative_subfolder(video, src)
    assert frames_relpath(video, sub) == f"frames/{Path(sub).as_posix()}/IMG_0001"
