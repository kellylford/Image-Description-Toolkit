"""Provider pickers must not offer a provider that cannot run here.

Issue #271: starting a chat in ImageDescriber on Windows listed MLX, which is
Apple Silicon only — picking it could only fail. `MLXProvider.is_available()`
was correct all along; three dialogs simply never asked it and hardcoded the
list instead. IDT Chat filtered correctly, which is how the difference was
spotted.

The tests are written to fail on the machine that has the bug rather than to
assert one platform's answer: on Windows and Linux MLX must be absent, on
macOS the expectation follows `MLXProvider.is_available()` (platform *and*
whether `mlx_vlm` imports — a packaged Mac build can exclude the library).

The selection tests matter as much as the list ones. The old code chose the
configured provider through a fixed ``{'ollama': 0, ..., 'mlx': 3}`` index map,
so filtering the list without changing that map would have quietly pointed
every provider at the wrong entry — a worse bug than the one being fixed.
"""

import os
import platform
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_APP_DIR = _ROOT / "imagedescriber"
for _p in (str(_ROOT), str(_APP_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

REQUIRE_WX = os.environ.get("IDT_REQUIRE_WX") == "1"

try:
    import wx
except ImportError as _exc:  # pragma: no cover
    if REQUIRE_WX:
        raise
    wx = None
    _WX_ERROR = str(_exc)

pytestmark = pytest.mark.unit

import ai_providers  # noqa: E402


def _mlx_can_run() -> bool:
    """What the app itself believes about MLX on this machine."""
    return ai_providers.MLXProvider().is_available()


# ---------------------------------------------------------------------------
# The helper
# ---------------------------------------------------------------------------

def test_mlx_is_offered_only_where_it_can_run():
    """The bug, stated directly."""
    offered = any(key == "mlx" for key, _ in ai_providers.provider_picker_choices())
    assert offered == _mlx_can_run(), (
        f"MLX offered={offered} but is_available()={_mlx_can_run()} "
        f"on {platform.system()}"
    )


@pytest.mark.skipif(platform.system() == "Darwin", reason="MLX can run on macOS")
def test_mlx_is_never_offered_off_macos():
    """Explicit form of the reported bug: Windows and Linux, never."""
    assert "mlx" not in [key for key, _ in ai_providers.provider_picker_choices()]


def test_the_cloud_providers_are_always_offered():
    """Guards the opposite failure — an over-eager filter that hides providers
    the user could fix by adding a key. A missing API key is a setup step the
    dialogs already explain, not a reason to make the provider undiscoverable."""
    keys = [key for key, _ in ai_providers.provider_picker_choices()]
    assert keys[:3] == ["ollama", "openai", "claude"]


def test_ollama_is_offered_even_when_the_daemon_is_down(monkeypatch):
    """Unlike MLX, Ollama is installable here — hiding it would tell someone
    their setup is impossible when it is merely not running yet."""
    monkeypatch.setattr(ai_providers, "get_available_providers", lambda: {})
    assert "ollama" in [key for key, _ in ai_providers.provider_picker_choices()]


def test_a_broken_availability_check_shows_too_much_not_too_little(monkeypatch):
    """A picker with a stale list is a bad day; an empty one is a dead dialog."""
    def boom():
        raise RuntimeError("provider probing exploded")

    monkeypatch.setattr(ai_providers, "get_available_providers", boom)
    keys = [key for key, _ in ai_providers.provider_picker_choices()]
    assert keys == ["ollama", "openai", "claude", "mlx"]


def test_labels_lowercase_to_provider_keys():
    """ChatDialog derives the provider with `GetStringSelection().lower()`, so
    a label that doesn't lowercase to its key would route to the wrong
    provider."""
    for key, label in ai_providers.provider_picker_choices():
        assert label.lower() == key


# ---------------------------------------------------------------------------
# The dialogs
# ---------------------------------------------------------------------------

if wx is None:  # pragma: no cover
    pytest.skip(f"wxPython unavailable: {_WX_ERROR}", allow_module_level=True)


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


@pytest.fixture
def frame(wx_app):
    f = wx.Frame(None)
    yield f
    f.Destroy()


_CONFIG = {"default_model": "gpt-5.2", "provider": "openai",
           "default_provider": "claude"}


def _labels(choice):
    return [choice.GetString(i) for i in range(choice.GetCount())]


def test_chat_dialog_does_not_offer_mlx_off_macos(frame):
    """The dialog in the report: Process -> Chat inside ImageDescriber."""
    import chat_window_wx

    dlg = chat_window_wx.ChatDialog(frame, _CONFIG, cached_ollama_models=[])
    try:
        offered = "mlx" in [l.lower() for l in _labels(dlg.provider_choice)]
        assert offered == _mlx_can_run()
    finally:
        dlg.Destroy()


def test_processing_options_does_not_offer_mlx_off_macos(frame):
    import dialogs_wx

    dlg = dialogs_wx.ProcessingOptionsDialog(_CONFIG, cached_ollama_models=[],
                                             parent=frame)
    try:
        offered = "mlx" in [l.lower() for l in _labels(dlg.provider_choice)]
        assert offered == _mlx_can_run()
    finally:
        dlg.Destroy()


def test_processing_options_still_honours_the_configured_provider(frame):
    """The fixed index map is gone; selection is now looked up in the list that
    was actually built. If that regressed, every provider would select the
    wrong entry — worse than the bug being fixed."""
    import dialogs_wx

    dlg = dialogs_wx.ProcessingOptionsDialog(_CONFIG, cached_ollama_models=[],
                                             parent=frame)
    try:
        assert dlg.provider_choice.GetStringSelection() == "Claude"
    finally:
        dlg.Destroy()


def test_processing_options_falls_back_when_the_configured_provider_is_absent(frame):
    """An .idtw saved on a Mac with MLX, reopened on Windows: select something
    valid rather than leaving the picker on nothing."""
    import dialogs_wx

    config = dict(_CONFIG, default_provider="mlx")
    dlg = dialogs_wx.ProcessingOptionsDialog(config, cached_ollama_models=[],
                                             parent=frame)
    try:
        selection = dlg.provider_choice.GetStringSelection()
        if _mlx_can_run():
            assert selection == "MLX"
        else:
            assert selection == "Ollama"
    finally:
        dlg.Destroy()


def test_followup_fallback_default_does_not_reintroduce_mlx(frame):
    """This dialog's caller passes a filtered list, but wraps the lookup in
    try/except — the fallback used to be a hardcoded list including mlx, so any
    failure there put MLX back in front of Windows users."""
    import dialogs_wx

    dlg = dialogs_wx.FollowupQuestionDialog(
        frame, "claude", "claude-opus-5", "preview", _CONFIG,
        cached_ollama_models=[], available_providers=None,
    )
    try:
        offered = "mlx" in [l.lower() for l in _labels(dlg.provider_choice)]
        assert offered == _mlx_can_run()
    finally:
        dlg.Destroy()


def test_no_dialog_hardcodes_a_provider_list():
    """The regression guard. Each of these dialogs was fixed by routing through
    provider_picker_choices(); a new hardcoded list is how this bug returns."""
    import re

    offenders = []
    for name in ("dialogs_wx.py", "chat_window_wx.py"):
        source = (_APP_DIR / name).read_text(encoding="utf-8")
        for match in re.finditer(r"choices\s*=\s*\[[^\]]*\]", source):
            text = match.group(0)
            if re.search(r"['\"]mlx['\"]", text, re.IGNORECASE):
                line = source[:match.start()].count("\n") + 1
                offenders.append(f"{name}:{line}")
    assert not offenders, (
        "hardcoded provider list naming MLX — route through "
        f"ai_providers.provider_picker_choices() instead: {offenders}"
    )
