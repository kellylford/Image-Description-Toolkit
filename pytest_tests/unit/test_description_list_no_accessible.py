"""The description list loads where wx.Accessible is unavailable (macOS).

wx.Accessible is Windows-only; on macOS constructing one raises
NotImplementedError. LoadDescriptions built one unconditionally, and because
wx swallows exceptions in event handlers, selecting a described image on a Mac
silently skipped the rest of display_image_info. Found when the macOS release
job ran a test that selects an image.
"""

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

wx = pytest.importorskip("wx", reason="wxPython not installed in this environment")

from shared import wx_common  # noqa: E402


def test_load_descriptions_survives_missing_accessible(monkeypatch):
    app = wx.App.Get() or wx.App(False)
    frame = wx.Frame(None)
    try:
        lst = wx_common.DescriptionListBox(frame)

        def _unsupported(*_a, **_k):
            raise NotImplementedError

        monkeypatch.setattr(wx_common, "AccessibleDescriptionListBox", _unsupported)
        lst.LoadDescriptions([{"description": "a red barn", "model": "m",
                               "prompt_style": "detailed", "created": "",
                               "provider": "ollama"}])
        assert lst.GetCount() == 1
        assert lst.custom_accessible is None
    finally:
        frame.Destroy()
    del app
