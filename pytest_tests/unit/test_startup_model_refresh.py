"""The startup model refresh stays off in the test suite.

Every test that built an ImageDescriber window started a background thread
that queried Ollama and the Claude and OpenAI APIs and then changed the shared
model catalog while later tests on the same xdist worker ran. That was an
intermittent test_model_refresh failure, and real API calls on a machine with
keys. conftest sets IDT_SKIP_STARTUP_MODEL_REFRESH for the whole session.
"""

import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(_ROOT), str(_ROOT / "imagedescriber")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

wx = pytest.importorskip("wx")


def _threads_started(monkeypatch):
    import threading
    started = []

    class _Thread:
        def __init__(self, *a, **k):
            started.append(k.get("target"))

        def start(self):
            pass
    monkeypatch.setattr(threading, "Thread", _Thread)
    return started


def test_the_suite_sets_the_switch():
    assert os.environ.get("IDT_SKIP_STARTUP_MODEL_REFRESH")


def test_no_refresh_thread_while_the_switch_is_set(monkeypatch):
    import imagedescriber_wx
    started = _threads_started(monkeypatch)
    window = SimpleNamespace()
    imagedescriber_wx.ImageDescriberFrame.refresh_ai_models_silent(window)
    assert started == []
    assert not getattr(window, "_model_refresh_running", False)


def test_the_app_still_refreshes_without_it(monkeypatch):
    import imagedescriber_wx
    monkeypatch.delenv("IDT_SKIP_STARTUP_MODEL_REFRESH")
    started = _threads_started(monkeypatch)
    window = SimpleNamespace()
    imagedescriber_wx.ImageDescriberFrame.refresh_ai_models_silent(window)
    assert len(started) == 1
    assert window._model_refresh_running
