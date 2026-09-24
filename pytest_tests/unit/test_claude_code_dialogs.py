"""Claude Code in every GUI picker, driven through the real dialogs.

Its picker label, "Claude Code", is the first that is not simply its key in
title case: the key is "claude-code". The dialogs used to read the provider
back with ``GetStringSelection().lower()``, which would have produced "claude
code" -- no provider at all. wx swallows exceptions in handlers, so that bug
shows up as an empty picker or a batch that silently fails, not a traceback.
These tests open each dialog, choose Claude Code, and check what comes back.

The `claude` CLI is reported as installed so the provider is offered even on a
machine (or CI runner) without it. Nothing here runs the CLI.
"""

import os
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(_ROOT), str(_ROOT / "imagedescriber"), str(_ROOT / "chatapp")):
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

if wx is None:  # pragma: no cover
    pytest.skip(f"wxPython unavailable: {_WX_ERROR}", allow_module_level=True)

import ai_providers  # noqa: E402
from idt_core.providers import catalog, claude_code  # noqa: E402

ALIASES = ["haiku", "sonnet", "opus"]


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


@pytest.fixture(autouse=True)
def cli_installed(monkeypatch):
    monkeypatch.setattr(ai_providers._claude_code_provider, "is_available", lambda: True)
    monkeypatch.setattr(claude_code, "is_available", lambda: True)
    monkeypatch.setattr(catalog, "_api_key_for", lambda _p: "test-key")
    monkeypatch.setattr(
        catalog, "_fetch",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no network in tests")),
    )
    catalog.invalidate()
    yield
    catalog.invalidate()


@pytest.fixture
def frame(wx_app):
    f = wx.Frame(None)
    yield f
    f.Destroy()


_CONFIG = {"default_model": "gpt-5.2", "provider": "openai", "default_provider": "openai"}


def _ids(combo):
    return [combo.GetClientData(i) for i in range(combo.GetCount())]


def test_processing_options_returns_the_claude_code_key(frame):
    import dialogs_wx

    dlg = dialogs_wx.ProcessingOptionsDialog(_CONFIG, cached_ollama_models=[], parent=frame)
    try:
        assert dlg.provider_choice.SetStringSelection("Claude Code")
        dlg.populate_models_for_provider()
        assert _ids(dlg.model_combo) == ALIASES
        config = dlg.get_config()
        assert config["provider"] == "claude-code"
        assert config["model"] == "haiku"
        assert "subscription" in dlg.model_desc_text.GetValue()

        # And back: no Claude Code alias may leak into the API provider's list.
        dlg.provider_choice.SetStringSelection("Claude")
        dlg.populate_models_for_provider()
        assert not set(_ids(dlg.model_combo)) & set(ALIASES)
    finally:
        dlg.Destroy()


def test_processing_options_opens_on_a_configured_claude_code_default(frame):
    import dialogs_wx

    config = {"default_provider": "claude-code", "provider": "claude-code",
              "default_model": "sonnet"}
    dlg = dialogs_wx.ProcessingOptionsDialog(config, cached_ollama_models=[], parent=frame)
    try:
        assert dlg.provider_choice.GetStringSelection() == "Claude Code"
        assert dlg.get_config()["provider"] == "claude-code"
        assert dlg.get_config()["model"] == "sonnet"
    finally:
        dlg.Destroy()


def test_followup_dialog_keeps_the_original_claude_code_model(frame):
    import dialogs_wx

    dlg = dialogs_wx.FollowupQuestionDialog(
        frame, "claude-code", "sonnet", "preview", _CONFIG, cached_ollama_models=[])
    try:
        values = dlg.get_values()
        assert values["model"] == "sonnet"
        assert _ids(dlg.model_combo) == ALIASES
    finally:
        dlg.Destroy()


def test_chat_dialog_returns_the_claude_code_key(frame):
    import chat_window_wx

    dlg = chat_window_wx.ChatDialog(frame, _CONFIG, cached_ollama_models=[])
    try:
        assert dlg.provider_choice.SetStringSelection("Claude Code")
        dlg.on_provider_changed(None)
        assert dlg.get_selections() == {"provider": "claude-code", "model": "haiku"}
    finally:
        dlg.Destroy()


def test_prompt_editor_lists_claude_code_models(frame):
    import prompt_editor_dialog

    dlg = prompt_editor_dialog.PromptEditorDialog(frame)
    try:
        assert dlg.provider_combo.SetStringSelection("claude-code")
        dlg.populate_model_combo()
        assert dlg.default_model_combo.IsEnabled()
        labels = [dlg.default_model_combo.GetString(i)
                  for i in range(dlg.default_model_combo.GetCount())]
        assert labels[0] == "Haiku (subscription) (Recommended)"
    finally:
        dlg.Destroy()


def test_chat_app_provider_dialog_offers_claude_code(frame):
    import chat_app_wx

    dlg = chat_app_wx.ProviderDialog(frame, "claude-code", "sonnet")
    try:
        names = [dlg.provider_choice.GetString(i) for i in range(dlg.provider_choice.GetCount())]
        assert "claude-code" in names
        assert dlg.get_selection() == ("claude-code", "sonnet")
        assert "claude auth login" in dlg.status.GetLabel()
    finally:
        dlg.Destroy()


def test_chat_app_hides_claude_code_without_the_cli(frame, monkeypatch):
    import chat_app_wx

    monkeypatch.setattr(claude_code, "is_available", lambda: False)
    assert "claude-code" not in chat_app_wx.ProviderDialog._provider_names()


def test_display_names_in_titles():
    """Window and session titles used provider.title() -> "Claude-Code"."""
    import data_models
    import imagedescriber_wx

    assert data_models._display_provider("claude-code") == "Claude Code"
    assert imagedescriber_wx._display_provider("openai") == "OpenAI"
