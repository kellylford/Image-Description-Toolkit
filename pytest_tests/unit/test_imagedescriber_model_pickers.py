"""ImageDescriber's four model pickers, driven the way a user drives them.

These exist because of a bug that only appeared when the dialogs were actually
opened and switched between providers. ``keep=`` was added so a model the API
has retired cannot silently vanish from under the user's selection -- but the
value passed to it was the *configured* model, which belongs to whichever
provider is configured. Switching the dialog to Claude therefore listed
"gpt-5.2" among the Claude models and selected it, and the prompt editor put the
Ollama default ("minicpm-v4.6") into both cloud providers' lists.

A model id means nothing outside its own provider, so every one of these pickers
is checked by round-tripping the provider selection and asserting that what
comes back belongs to the provider that is showing.

wx swallows exceptions inside event handlers, so a mistake in these paths is not
a traceback -- it is a picker that is empty or quietly holds the wrong thing.
That is why these drive the real dialogs rather than the helpers underneath.
"""

import os
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

if wx is None:  # pragma: no cover
    pytest.skip(f"wxPython unavailable: {_WX_ERROR}", allow_module_level=True)

from idt_core.providers import catalog  # noqa: E402


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


@pytest.fixture(autouse=True)
def offline(monkeypatch):
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


_CONFIG = {"default_model": "gpt-5.2", "provider": "openai",
           "default_provider": "openai"}


def _canonical(provider):
    return "openai" if provider.lower() == "openai" else "claude"


def _belongs_to(model_id, provider):
    """True if ``model_id`` is one of ``provider``'s models.

    Membership, not a name prefix: OpenAI's list legitimately includes `o3`,
    `o1` and `o4-mini`, so a "starts with gpt" test would flag real models as
    foreign and hide the contamination it was meant to catch.
    """
    return model_id in {e.id for e in catalog.cached_models(_canonical(provider))}


def _foreign_ids(ids, provider):
    """Ids in ``ids`` that belong to the *other* cloud provider."""
    other = "claude" if _canonical(provider) == "openai" else "openai"
    return sorted(set(ids) & {e.id for e in catalog.cached_models(other)})


def _ids(combo):
    return [combo.GetClientData(i) for i in range(combo.GetCount())]


# ---------------------------------------------------------------------------
# ProcessingOptionsDialog — the batch picker
# ---------------------------------------------------------------------------

def test_processing_options_picker_round_trips_providers(frame):
    import dialogs_wx

    dlg = dialogs_wx.ProcessingOptionsDialog(_CONFIG, cached_ollama_models=[],
                                             parent=frame)
    try:
        for provider in ("OpenAI", "Claude", "OpenAI"):
            dlg.provider_choice.SetStringSelection(provider)
            dlg.populate_models_for_provider()

            ids = _ids(dlg.model_combo)
            assert ids, f"{provider} picker is empty"
            selection = dlg.model_combo.GetSelection()
            chosen = dlg.model_combo.GetClientData(selection)
            assert chosen, "selection carries no API id"
            assert _belongs_to(chosen, provider), (
                f"{provider} selected {chosen}, which is not one of its models"
            )
            assert not _foreign_ids(ids, provider), (
                f"{provider} list contains {_foreign_ids(ids, provider)}"
            )
    finally:
        dlg.Destroy()


def test_processing_options_does_not_default_to_a_legacy_openai_model(frame):
    """It used to hardcode SetStringSelection("gpt-4o"), quietly starting every
    batch on a legacy model regardless of what was configured."""
    import dialogs_wx

    config = dict(_CONFIG, default_model="", provider="")
    dlg = dialogs_wx.ProcessingOptionsDialog(config, cached_ollama_models=[],
                                             parent=frame)
    try:
        dlg.provider_choice.SetStringSelection("OpenAI")
        dlg.populate_models_for_provider()
        chosen = dlg.model_combo.GetClientData(dlg.model_combo.GetSelection())
        assert chosen != "gpt-4o"
    finally:
        dlg.Destroy()


# ---------------------------------------------------------------------------
# FollowupQuestionDialog
# ---------------------------------------------------------------------------

def test_followup_picker_round_trips_providers(frame):
    import dialogs_wx

    dlg = dialogs_wx.FollowupQuestionDialog(
        frame, "claude", "claude-opus-5", "preview", _CONFIG,
        cached_ollama_models=[],
    )
    try:
        for provider in ("claude", "openai", "claude"):
            dlg.provider_choice.SetStringSelection(provider)
            dlg.populate_models()

            model = dlg.get_values()["model"]
            assert _belongs_to(model, provider), (
                f"{provider} returned {model}, which is not one of its models"
            )
    finally:
        dlg.Destroy()


def test_followup_preselects_the_original_model(frame):
    """The point of the dialog: ask again about an existing description, so it
    should open on the model that produced it."""
    import dialogs_wx

    dlg = dialogs_wx.FollowupQuestionDialog(
        frame, "claude", "claude-sonnet-5", "preview", _CONFIG,
        cached_ollama_models=[],
    )
    try:
        assert dlg.get_values()["model"] == "claude-sonnet-5"
    finally:
        dlg.Destroy()


# ---------------------------------------------------------------------------
# ChatDialog
# ---------------------------------------------------------------------------

def test_chat_dialog_picker_round_trips_providers(frame):
    import chat_window_wx

    dlg = chat_window_wx.ChatDialog(frame, _CONFIG, cached_ollama_models=[])
    try:
        for provider in ("openai", "claude", "openai"):
            dlg.provider_choice.SetStringSelection(provider)
            dlg.on_provider_changed(None)

            model = dlg.get_selections()["model"]
            assert _belongs_to(model, provider), (
                f"{provider} returned {model}, which is not one of its models"
            )
    finally:
        dlg.Destroy()


# ---------------------------------------------------------------------------
# PromptEditorDialog
# ---------------------------------------------------------------------------

def test_prompt_editor_does_not_offer_an_ollama_model_under_a_cloud_provider(frame):
    """`default_model` in image_describer_config.json is an Ollama model, so
    passing it through as `keep` put "minicpm-v4.6" in both cloud lists."""
    import prompt_editor_dialog

    dlg = prompt_editor_dialog.PromptEditorDialog(frame)
    try:
        for provider in ("openai", "claude"):
            dlg.provider_combo.SetStringSelection(provider)
            dlg.populate_model_combo()

            ids = _ids(dlg.default_model_combo)
            assert ids, f"{provider} picker is empty"
            assert "minicpm-v4.6" not in ids, "the Ollama default leaked in"
            assert not _foreign_ids(ids, provider), (
                f"{provider} list contains {_foreign_ids(ids, provider)}"
            )
    finally:
        dlg.Destroy()


def test_prompt_editor_labels_openai_models_too(frame):
    """OpenAI models used to render as bare ids with no description: the only
    friendly-name lookup was CLAUDE_MODEL_METADATA, and the fallback read an
    Ollama-only section of the config."""
    import prompt_editor_dialog

    dlg = prompt_editor_dialog.PromptEditorDialog(frame)
    try:
        dlg.provider_combo.SetStringSelection("openai")
        dlg.populate_model_combo()
        assert dlg.default_model_combo.GetString(0) == "GPT-5.2 (Recommended)"
    finally:
        dlg.Destroy()
