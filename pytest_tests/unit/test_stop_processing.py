""""Stop All Processing" — halting background work from the menu.

The Qt6 build had a "Stop Processing" item in the Process menu (added in
7054a61 as a QAction). It did not survive the wxPython migration, leaving the
batch progress dialog's Stop button as the only way to halt a run — so if that
dialog was closed, or the work was something other than a batch, there was no
way to stop anything short of killing the process.

on_close also carried its own partial copy of the "stop every worker" logic
which omitted the directory scan worker, so quitting mid-scan left the thread
running. Both paths now share one inventory.

imagedescriber_wx.py is a ~8600-line wx module at 0% coverage that cannot be
imported headlessly, so these tests extract the worker-control methods from the
shipped source and run them against fake workers.
"""

import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_SRC = (_ROOT / "imagedescriber" / "imagedescriber_wx.py").read_text(
    encoding="utf-8", errors="replace"
)

_METHODS = ("_running_workers", "_stop_worker", "_stop_all_workers")


class _App:
    """Host object carrying the real methods under test."""


def _bind_real_methods():
    ns = {
        "logger": type("L", (), {
            "info": staticmethod(lambda *a, **k: None),
            "warning": staticmethod(lambda *a, **k: None),
            "error": staticmethod(lambda *a, **k: None),
        })(),
    }
    for name in _METHODS:
        m = re.search(
            rf"^    def {name}\(self.*?(?=^    def )", _SRC, re.MULTILINE | re.DOTALL
        )
        assert m, f"could not locate {name} in imagedescriber_wx.py"
        body = "\n".join(line[4:] if line.startswith("    ") else line
                         for line in m.group(0).splitlines())
        exec(compile(body, "imagedescriber_wx.py", "exec"), ns)
        setattr(_App, name, ns[name])

    # The worker inventory is a class attribute, not a method.
    m = re.search(r"^    _WORKER_ATTRS = \((.*?)^    \)", _SRC, re.MULTILINE | re.DOTALL)
    assert m, "could not locate _WORKER_ATTRS"
    _App._WORKER_ATTRS = eval("(" + m.group(1) + ")")


_bind_real_methods()


class _Worker:
    """Worker exposing stop()."""

    def __init__(self, alive=True):
        self._alive = alive
        self.stopped = False

    def is_alive(self):
        return self._alive

    def stop(self):
        self.stopped = True
        self._alive = False


class _CancelOnlyWorker(_Worker):
    """Worker exposing cancel() but not stop()."""

    stop = None  # shadow so getattr(...,'stop') is not callable

    def cancel(self):
        self.stopped = True
        self._alive = False


class _EventWorker:
    """VideoProcessingWorker-style: signals through _stop_event."""

    class _Event:
        def __init__(self):
            self.is_set = False

        def set(self):
            self.is_set = True

    def __init__(self, alive=True):
        self._alive = alive
        self._stop_event = self._Event()

    def is_alive(self):
        return self._alive


class _BrokenWorker:
    """is_alive() raises — must not take the whole stop path down."""

    def is_alive(self):
        raise RuntimeError("worker in a bad state")


def _app(**workers):
    app = _App()
    for attr, _label in _App._WORKER_ATTRS:
        setattr(app, attr, workers.get(attr))
    return app


# --------------------------------------------------------------------------- #
# Which workers count as running                                              #
# --------------------------------------------------------------------------- #

def test_no_workers_means_nothing_running():
    assert _app()._running_workers() == []


def test_finished_workers_are_not_running():
    assert _app(batch_worker=_Worker(alive=False))._running_workers() == []


def test_running_workers_are_reported_with_labels():
    app = _app(batch_worker=_Worker(), scan_worker=_Worker())
    running = app._running_workers()
    assert "batch processing" in running
    assert "directory scan" in running


def test_a_worker_that_cannot_report_liveness_is_skipped():
    """Otherwise one broken worker pins the menu item enabled forever."""
    app = _app(batch_worker=_BrokenWorker(), scan_worker=_Worker())
    assert app._running_workers() == ["directory scan"]


# --------------------------------------------------------------------------- #
# Stopping                                                                     #
# --------------------------------------------------------------------------- #

def test_stop_all_stops_every_running_worker():
    batch, scan, download = _Worker(), _Worker(), _Worker()
    app = _app(batch_worker=batch, scan_worker=scan, download_worker=download)

    stopped = app._stop_all_workers()

    assert batch.stopped and scan.stopped and download.stopped
    assert set(stopped) == {"batch processing", "directory scan", "download"}
    assert app._running_workers() == []


def test_scan_worker_is_included():
    """on_close's old inline copy omitted it, leaking the thread on quit."""
    assert any(attr == "scan_worker" for attr, _ in _App._WORKER_ATTRS)
    scan = _Worker()
    app = _app(scan_worker=scan)
    assert app._stop_all_workers() == ["directory scan"]
    assert scan.stopped


def test_cancel_only_worker_is_stopped_via_cancel():
    w = _CancelOnlyWorker()
    app = _app(batch_worker=w)
    assert app._stop_all_workers() == ["batch processing"]
    assert w.stopped


def test_event_driven_worker_is_stopped_via_stop_event():
    w = _EventWorker()
    app = _app(video_worker=w)
    assert app._stop_all_workers() == ["video extraction"]
    assert w._stop_event.is_set


def test_include_batch_false_leaves_the_batch_alone():
    """The batch needs on_stop_batch's extra cleanup, not just a thread stop."""
    batch, scan = _Worker(), _Worker()
    app = _app(batch_worker=batch, scan_worker=scan)

    stopped = app._stop_all_workers(include_batch=False)

    assert stopped == ["directory scan"]
    assert scan.stopped
    assert not batch.stopped


def test_one_failing_worker_does_not_prevent_stopping_the_others():
    class _Explodes(_Worker):
        def stop(self):
            raise RuntimeError("nope")

    scan = _Worker()
    app = _app(batch_worker=_Explodes(), scan_worker=scan)

    stopped = app._stop_all_workers()

    assert scan.stopped, "a failure on one worker must not abort the sweep"
    assert "directory scan" in stopped


def test_already_finished_workers_are_not_reported_as_stopped():
    app = _app(batch_worker=_Worker(alive=False))
    assert app._stop_all_workers() == []


# --------------------------------------------------------------------------- #
# Wiring                                                                       #
# --------------------------------------------------------------------------- #

def test_menu_item_exists_and_is_disabled_by_default():
    assert 'S&top All Processing' in _SRC, "Process menu needs a Stop All item"
    m = re.search(r"self\.stop_processing_item = process_menu\.Append\(.*?\)\s*\n\s*"
                  r"self\.stop_processing_item\.Enable\(False\)", _SRC, re.DOTALL)
    assert m, "Stop All Processing should start disabled"


def test_menu_item_enabled_state_is_driven_by_update_ui():
    """Hooking each worker's start/finish would eventually miss a transition."""
    assert "wx.EVT_UPDATE_UI, self.on_update_stop_processing_ui" in _SRC
    m = re.search(r"def on_update_stop_processing_ui\(self.*?(?=\n    def )",
                  _SRC, re.DOTALL)
    assert m and "_running_workers()" in m.group(0)


def test_stop_all_delegates_the_batch_to_on_stop_batch():
    """Batch state, item flags, dialog and save live there — don't duplicate."""
    m = re.search(r"def on_stop_all_processing\(self.*?(?=\n    def )", _SRC, re.DOTALL)
    assert m, "expected an on_stop_all_processing handler"
    body = m.group(0)
    assert "self.on_stop_batch()" in body
    assert "ask_yes_no" in body, "stopping a long run should be confirmed"


def test_on_close_uses_the_shared_inventory():
    """It used to carry a partial copy that omitted the scan worker."""
    m = re.search(r"# Stop all background workers.*?workers_stopped\s*=\s*[^\n]+",
                  _SRC, re.DOTALL)
    assert m, "could not find the on_close worker shutdown block"
    assert "self._stop_all_workers()" in m.group(0), (
        "on_close should reuse the shared worker inventory rather than "
        "re-listing workers inline"
    )
