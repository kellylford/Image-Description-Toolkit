"""IDT Chat's model picker: painting from cache, and refreshing politely.

Issue #267 made this picker's contents come from a live API listing. Two risks
came with that, and they are what this file is about.

**Blocking.** The list is painted from the catalog cache, which never touches
the network, so the dialog opens instantly and is never empty -- with no key and
no cache it shows exactly the curated list it always showed. The live fetch
happens on a worker thread behind it.

**Rebuilding the control underneath the user.** This is a keyboard- and
screen-reader-first app. Repopulating a ``wx.Choice`` moves the selection and
makes the reader re-announce the whole control, so a refresh landing while
someone is arrowing through the list would be actively hostile. The rules
tested here: identical list means touch nothing; a user who has started
choosing gets a status line, not a rebuild; and a rebuild restores the
selection by model id rather than by index.
"""

import os
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_APP_DIR = _ROOT / "chatapp"
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
from idt_core.providers.claude import CLAUDE_MODELS  # noqa: E402


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


@pytest.fixture(autouse=True)
def offline_catalog(monkeypatch):
    """No network, and a deterministic key regardless of the machine."""
    monkeypatch.setattr(catalog, "_api_key_for", lambda _p: "test-key")
    monkeypatch.setattr(
        catalog, "_fetch",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no network in tests")),
    )
    catalog.invalidate()
    yield
    catalog.invalidate()


def _dialog(model=""):
    from chat_app_wx import ProviderDialog

    return ProviderDialog(None, provider="claude", model=model)


def _ids(dlg):
    return [dlg.model_choice.GetClientData(i)
            for i in range(dlg.model_choice.GetCount())]


# ---------------------------------------------------------------------------
# Painting
# ---------------------------------------------------------------------------

def test_the_picker_is_filled_on_open_without_a_network(wx_app):
    """With no cache and no reachable API, this must look like it always did."""
    dlg = _dialog()
    try:
        assert _ids(dlg) == list(CLAUDE_MODELS)
    finally:
        dlg.Destroy()


def test_labels_are_display_names_and_client_data_is_the_api_id(wx_app):
    """The id is what gets sent; the name is what gets read aloud."""
    dlg = _dialog()
    try:
        assert dlg.model_choice.GetString(0) == "Claude Opus 5"
        assert dlg.model_choice.GetClientData(0) == "claude-opus-5"
    finally:
        dlg.Destroy()


def test_the_initial_model_is_preselected(wx_app):
    dlg = _dialog(model="claude-sonnet-5")
    try:
        assert dlg.get_selection() == ("claude", "claude-sonnet-5")
    finally:
        dlg.Destroy()


def test_a_model_the_listing_does_not_have_is_still_selectable(wx_app, monkeypatch):
    """Someone whose saved model has been retired keeps it, rather than being
    moved to whatever happens to be first without being told."""
    monkeypatch.setattr(
        catalog, "cached_models",
        lambda provider, keep=(): catalog.curated_models(provider) + [
            catalog.ModelEntry(id=k, provider="claude", name=k, source="retired")
            for k in keep
        ],
    )
    dlg = _dialog(model="claude-something-withdrawn")
    try:
        assert "claude-something-withdrawn" in _ids(dlg)
        assert dlg.get_selection()[1] == "claude-something-withdrawn"
    finally:
        dlg.Destroy()


# ---------------------------------------------------------------------------
# Refresh landing
# ---------------------------------------------------------------------------

def _entries(*ids):
    return [catalog.ModelEntry(id=i, provider="claude", name=i.title()) for i in ids]


def test_an_identical_list_does_not_touch_the_control(wx_app):
    """The cheapest and most important rule: no rebuild, no re-announcement,
    and no status message for a refresh that changed nothing."""
    dlg = _dialog(model="claude-sonnet-5")
    try:
        found = [(dlg.model_choice.GetString(i), dlg.model_choice.GetClientData(i))
                 for i in range(dlg.model_choice.GetCount())]
        before = dlg.model_choice.GetSelection()

        dlg._finish_catalog_refresh(dlg._load_token, "claude",
                                    dlg._selected_id(), found)

        assert dlg.model_choice.GetSelection() == before
        assert dlg.status.GetLabel() == ""
    finally:
        dlg.Destroy()


def test_a_changed_list_rebuilds_and_keeps_the_selection_by_id(wx_app):
    dlg = _dialog(model="claude-sonnet-5")
    try:
        found = [(e.name, e.id) for e in
                 _entries("claude-brand-new", "claude-sonnet-5", "claude-opus-5")]
        dlg._finish_catalog_refresh(dlg._load_token, "claude",
                                    dlg._selected_id(), found)

        assert _ids(dlg) == ["claude-brand-new", "claude-sonnet-5", "claude-opus-5"]
        # Restored by id, not by index -- the index moved.
        assert dlg.get_selection()[1] == "claude-sonnet-5"
        assert "1 new model" in dlg.status.GetLabel()
    finally:
        dlg.Destroy()


def test_a_user_mid_selection_is_told_rather_than_interrupted(wx_app):
    """They have started arrowing through the list. Rebuilding it now would
    move their selection and re-announce the control."""
    dlg = _dialog(model="claude-opus-5")
    try:
        painted = dlg._selected_id()
        dlg.model_choice.SetSelection(3)          # the user arrows down
        before = _ids(dlg)

        found = [(e.name, e.id) for e in _entries("claude-brand-new", "claude-opus-5")]
        dlg._finish_catalog_refresh(dlg._load_token, "claude", painted, found)

        assert _ids(dlg) == before, "the list was rebuilt under the user"
        assert dlg.get_selection()[1] == before[3], "the selection moved"
        assert "reopen" in dlg.status.GetLabel().lower()
    finally:
        dlg.Destroy()


def test_a_stale_result_for_another_provider_is_ignored(wx_app):
    """The generation token: a late Claude result must not repopulate a picker
    that is now showing something else."""
    dlg = _dialog()
    try:
        before = _ids(dlg)
        dlg._finish_catalog_refresh(dlg._load_token, "openai",
                                    dlg._selected_id(),
                                    [("GPT", "gpt-5.2")])
        assert _ids(dlg) == before
    finally:
        dlg.Destroy()


def test_a_superseded_token_is_ignored(wx_app):
    dlg = _dialog()
    try:
        before = _ids(dlg)
        dlg._finish_catalog_refresh(dlg._load_token - 1, "claude",
                                    dlg._selected_id(),
                                    [("New", "claude-brand-new")])
        assert _ids(dlg) == before
    finally:
        dlg.Destroy()


def test_the_status_line_is_plain_prose(wx_app):
    """Screen readers read this. No symbols, no counts-only shorthand."""
    dlg = _dialog(model="claude-opus-5")
    try:
        found = [(e.name, e.id) for e in
                 _entries("claude-a", "claude-b", "claude-opus-5")]
        dlg._finish_catalog_refresh(dlg._load_token, "claude",
                                    dlg._selected_id(), found)
        label = dlg.status.GetLabel()
        assert label.startswith("Model list updated")
        assert "2 new models" in label
    finally:
        dlg.Destroy()
