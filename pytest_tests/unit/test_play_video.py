"""Enter on a video in the image list plays it in the OS default player.

Drives the real ImageDescriberFrame handlers, because wx swallows exceptions
raised inside event handlers: a broken handler here would look like a key
that silently does nothing.
"""

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(_ROOT), str(_ROOT / "imagedescriber")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

wx = pytest.importorskip("wx", reason="wxPython not installed in this environment")

import imagedescriber_wx  # noqa: E402
from data_models import ImageItem  # noqa: E402


class _Node:
    def __init__(self, data):
        self.data = data

    def IsOk(self):
        return True


class _Tree:
    """Stands in for the image list: only the node data is read."""

    def GetItemData(self, node):
        return node.data


class _Event:
    """An activation event on a tree node carrying `data` (None = folder)."""

    def __init__(self, data):
        self.node = _Node(data)
        self.skipped = False

    def GetItem(self):
        return self.node

    def Skip(self):
        self.skipped = True


@pytest.fixture(scope="module")
def _frame():
    app = wx.App.Get() or wx.App(False)
    f = imagedescriber_wx.ImageDescriberFrame()
    yield f
    f.Destroy()
    wx.SafeYield()
    del app


@pytest.fixture
def frame(_frame, monkeypatch):
    """The frame, with dialogs and the OS hand-off recorded instead of run."""
    monkeypatch.setattr(_frame, "image_list", _Tree())
    _frame.opened = []
    _frame.dialogs = []
    monkeypatch.setattr(imagedescriber_wx, "open_with_default_app",
                        _frame.opened.append)
    for name in ("show_error", "show_warning", "show_info"):
        monkeypatch.setattr(
            imagedescriber_wx, name,
            lambda _parent, message, *_a, _n=name, **_k:
                _frame.dialogs.append((_n, message)))
    yield _frame
    _frame.current_image_item = None


def test_enter_on_a_video_plays_it(frame, tmp_path):
    video = tmp_path / "clip.mov"
    video.write_bytes(b"not really a video")
    frame.current_image_item = ImageItem(str(video), "video")

    event = _Event(str(video))
    frame.on_item_activated(event)

    assert frame.opened == [video]
    assert not frame.dialogs
    assert not event.skipped


def test_enter_on_an_image_does_not_play_anything(frame, tmp_path):
    image = tmp_path / "photo.jpg"
    image.write_bytes(b"jpeg")
    frame.current_image_item = ImageItem(str(image), "image")

    event = _Event(str(image))
    frame.on_item_activated(event)

    assert frame.opened == []
    assert event.skipped


def test_enter_on_a_folder_does_not_replay_the_last_video(frame, tmp_path):
    """Selecting a folder node leaves current_image_item on the last file."""
    video = tmp_path / "clip.mov"
    video.write_bytes(b"not really a video")
    frame.current_image_item = ImageItem(str(video), "video")

    event = _Event(None)
    frame.on_item_activated(event)

    assert frame.opened == []
    assert event.skipped


def test_a_missing_video_file_is_reported(frame, tmp_path):
    frame.current_image_item = ImageItem(str(tmp_path / "gone.mov"), "video")

    frame.on_play_video(None)

    assert frame.opened == []
    assert frame.dialogs and frame.dialogs[0][0] == "show_error"
    assert "could not be found" in frame.dialogs[0][1]


def test_play_video_menu_with_no_video_selected_warns(frame):
    frame.current_image_item = None

    frame.on_play_video(None)

    assert frame.opened == []
    assert frame.dialogs and frame.dialogs[0][0] == "show_warning"


def test_play_video_is_in_the_process_menu(frame):
    menubar = frame.GetMenuBar()
    process = menubar.GetMenu(menubar.FindMenu("Process"))
    labels = [i.GetItemLabelText() for i in process.GetMenuItems()]
    assert "Play Video" in labels
