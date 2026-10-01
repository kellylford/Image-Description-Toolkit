"""A collected wx.App must not rebind sys.stdout in whatever test is running.

wx.App.__del__ restores the stdout it saw at construction. Under pytest that
is a previous test's capture stream, so a collection at the wrong moment sent
a later test's prints there and left its capsys empty -- an intermittent CI
failure in test_cli_models_command.py. pytest_tests/conftest.py disables the
restore; this pins that it stays disabled.
"""

import gc
import io
import sys

import pytest

wx = pytest.importorskip("wx", reason="wxPython not installed in this environment")


def test_collecting_an_app_leaves_sys_stdout_alone(monkeypatch):
    stale = io.StringIO()
    monkeypatch.setattr(sys, "stdout", stale)
    app = wx.App.Get() or wx.App(False)
    # Whether or not this call made the App, its saved stream must not come back.
    app.saveStdio = (stale, sys.stderr)

    current = io.StringIO()
    monkeypatch.setattr(sys, "stdout", current)
    app.RestoreStdio()
    del app
    gc.collect()

    assert sys.stdout is current
