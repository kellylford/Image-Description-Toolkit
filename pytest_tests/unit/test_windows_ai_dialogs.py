"""Windows AI in ImageDescriber, driven through the real dialogs and workers.

Windows AI is the first provider that takes no prompt. Its models are the kinds of description,
and the prompt controls stay where they are (disabled controls drop out of the tab order) but
say they aren't used. Anything that is only a prompt -- chat, a follow-up question, testing a
prompt -- doesn't offer it, and its descriptions record the prompt as "none".

The provider is reported as available so these run on any machine; nothing starts the helper.
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
from idt_core.providers import catalog, windows_ai  # noqa: E402

KINDS = ["accessible", "detailed", "brief", "diagram"]


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


@pytest.fixture(autouse=True)
def copilot_pc(monkeypatch):
    for key, instance in ai_providers.get_all_providers().items():
        monkeypatch.setattr(instance, "is_available",
                            lambda k=key: k == "windows-ai" or k not in ai_providers._GATED_PROVIDERS)
    monkeypatch.setattr(windows_ai, "is_available", lambda: True)
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


def _strings(choice):
    return [choice.GetString(i) for i in range(choice.GetCount())]


def test_processing_options_offers_the_kinds_and_says_the_prompt_isnt_used(frame):
    import dialogs_wx

    dlg = dialogs_wx.ProcessingOptionsDialog(_CONFIG, cached_ollama_models=[], parent=frame)
    try:
        assert dlg.provider_choice.SetStringSelection("Windows AI")
        dlg.populate_models_for_provider()
        assert _ids(dlg.model_combo) == KINDS
        config = dlg.get_config()
        assert (config["provider"], config["model"]) == ("windows-ai", "accessible")
        assert "Takes no prompt" in dlg.model_desc_text.GetValue()
        assert dlg.prompt_choice.GetName() == "Prompt style, not used by Windows AI"
        assert dlg.custom_prompt_input.GetName() == "Custom prompt override, not used by Windows AI"
        assert dlg.prompt_box.GetLabel() == "Prompt Style, not used by Windows AI"
        # Still there and still reachable from the keyboard.
        assert dlg.prompt_choice.IsEnabled() and dlg.custom_prompt_input.IsEnabled()

        # And back: the note goes as soon as the provider takes a prompt.
        dlg.provider_choice.SetStringSelection("Claude")
        dlg.populate_models_for_provider()
        assert dlg.prompt_choice.GetName() == "Prompt style"
        assert dlg.prompt_box.GetLabel() == "Prompt Style"
        assert not set(_ids(dlg.model_combo)) & set(KINDS)
    finally:
        dlg.Destroy()


def test_processing_options_opens_on_a_configured_windows_ai_default(frame):
    import dialogs_wx

    config = {"default_provider": "windows-ai", "provider": "windows-ai", "default_model": "brief"}
    dlg = dialogs_wx.ProcessingOptionsDialog(config, cached_ollama_models=[], parent=frame)
    try:
        assert dlg.provider_choice.GetStringSelection() == "Windows AI"
        assert dlg.get_config()["model"] == "brief"
        assert dlg.prompt_choice.GetName() == "Prompt style, not used by Windows AI"
    finally:
        dlg.Destroy()


def test_a_followup_to_a_windows_ai_description_uses_another_provider(frame):
    import dialogs_wx

    dlg = dialogs_wx.FollowupQuestionDialog(
        frame, "windows-ai", "accessible", "preview", _CONFIG, cached_ollama_models=[],
        available_providers=["ollama", "openai", "windows-ai"])
    try:
        assert "windows-ai" not in _strings(dlg.provider_choice)
        values = dlg.get_values()
        assert values["provider"] == "ollama"
        assert values["model"] != "accessible"
    finally:
        dlg.Destroy()


def test_the_followup_fallback_list_leaves_it_out(frame):
    import dialogs_wx

    dlg = dialogs_wx.FollowupQuestionDialog(
        frame, "openai", "gpt-5.2", "preview", _CONFIG, cached_ollama_models=[])
    try:
        assert "windows-ai" not in _strings(dlg.provider_choice)
        assert dlg.get_values()["provider"] == "openai"
    finally:
        dlg.Destroy()


def test_chat_doesnt_offer_it(frame):
    import chat_window_wx

    dlg = chat_window_wx.ChatDialog(frame, _CONFIG, cached_ollama_models=[])
    try:
        assert "Windows AI" not in _strings(dlg.provider_choice)
    finally:
        dlg.Destroy()


def test_idt_chat_doesnt_offer_it(frame):
    import chat_app_wx

    assert "windows-ai" not in chat_app_wx.ProviderDialog._provider_names()


def test_the_prompt_editor_doesnt_offer_it(frame):
    import prompt_editor_dialog

    dlg = prompt_editor_dialog.PromptEditorDialog(frame)
    try:
        assert "windows-ai" not in _strings(dlg.provider_combo)
    finally:
        dlg.Destroy()


def test_settings_offer_it_as_the_default_provider():
    from types import SimpleNamespace

    import configure_dialog

    meta = configure_dialog.ConfigureDialog.build_settings_metadata(
        SimpleNamespace(_get_ollama_models=lambda: []))
    setting = meta["AI Model Settings"]["default_provider"]
    assert "windows-ai" in setting["choices"]
    assert "takes no prompt" in setting["description"]


# ---------------------------------------------------------------------------
# What a run records
# ---------------------------------------------------------------------------


def test_one_picture_records_no_prompt(frame):
    import workers_wx

    worker = workers_wx.ProcessingWorker(frame, "x.jpg", "windows-ai", "brief", "narrative", "Be poetic")
    assert (worker.prompt_style, worker.custom_prompt) == ("none", "")
    other = workers_wx.ProcessingWorker(frame, "x.jpg", "ollama", "moondream", "narrative", "Be poetic")
    assert (other.prompt_style, other.custom_prompt) == ("narrative", "Be poetic")


def test_a_batch_records_no_prompt(frame):
    import workers_wx

    batch = workers_wx.BatchProcessingWorker(frame, ["a.jpg"], "windows-ai", "brief", "narrative", "x")
    assert (batch.prompt_style, batch.custom_prompt) == ("none", "")


def test_a_refused_picture_counts_as_a_refusal_not_a_failure_streak():
    import workers_wx
    from idt_core.providers.windows_ai import error_for_code

    try:
        try:
            raise error_for_code("content_filtered", "declined")
        except Exception:
            ai_providers.raise_provider_error(provider="Windows AI", kind=ai_providers.ErrorKind.UNKNOWN,
                                              message="declined")
    except ai_providers.ProviderError as err:
        assert workers_wx._is_per_image_failure(err)
        assert workers_wx._provider_error_kind(err) not in workers_wx.RUN_FATAL_KINDS
