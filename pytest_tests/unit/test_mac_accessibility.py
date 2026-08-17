"""The macOS naming layer, tested without wx and without a display.

The module is deliberately wx-free -- it talks to NSAccessibility through
ctypes and takes the wx module as an argument where it needs one -- which is
what lets these run anywhere, including the Windows CI box. ``IS_MACOS`` is
patched on rather than skipped around, so the selection logic is exercised on
every platform; only the three ctypes calls at the bottom are Mac-only, and
those are covered by the wx-level tests in test_chat_app_smoke.py.

What this is guarding: wx has no working way to name a control for VoiceOver.
``SetAccessible()`` raises NotImplementedError on macOS and ``SetName()``
reaches no NSAccessibility attribute, so every text box, list and picker
announced its contents and never its label.
"""

import sys
import types

import pytest

_ROOT = __import__("pathlib").Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from shared import mac_accessibility as M  # noqa: E402


class _Window:
    """A stand-in for a wx.Window: a name and some children."""

    def __init__(self, name, children=()):
        self._name = name
        self._children = list(children)

    def GetName(self):
        return self._name

    def GetChildren(self):
        return self._children


def _StaticText(name):
    """A _Window whose class is literally named StaticText, as wx's is."""
    return type("StaticText", (_Window,), {})(name)


@pytest.fixture
def named(monkeypatch):
    """Run the walk as if on macOS, recording what it would name."""
    recorded = []
    monkeypatch.setattr(M, "IS_MACOS", True)
    monkeypatch.setattr(M, "set_accessible_name",
                        lambda window, label: recorded.append(label) or True)
    return recorded


def test_the_walk_names_controls_that_carry_a_label(named):
    root = _Window("panel", [_Window("Your message"), _Window("Conversation history")])

    assert M.apply_accessible_names(root) == 2
    assert named == ["Your message", "Conversation history"]


def test_the_walk_reaches_nested_controls(named):
    """Controls live inside panels inside sizers inside splitters."""
    root = _Window("frame", [
        _Window("panel", [_Window("splitter", [_Window("Saved conversations")])]),
    ])

    M.apply_accessible_names(root)

    assert named == ["Saved conversations"]


def test_wx_default_names_are_not_announced(named):
    """"listBox" is wx's class name, not a label. Announcing it is worse than
    silence -- the control needs a real ``name=`` instead."""
    root = _Window("panel", [
        _Window("listBox"), _Window("text"), _Window("choice"),
        _Window("Pending attachments"),
    ])

    M.apply_accessible_names(root)

    assert named == ["Pending attachments"]


def test_static_text_is_left_alone(named):
    """Its own text is what a reader should read; a name could displace it."""
    root = _Window("panel", [_StaticText("Token usage"), _Window("Your message")])

    M.apply_accessible_names(root)

    assert named == ["Your message"]


def test_the_walk_does_nothing_off_macos(monkeypatch):
    """Windows already reads SetName; this must not touch anything there."""
    monkeypatch.setattr(M, "IS_MACOS", False)
    monkeypatch.setattr(M, "set_accessible_name",
                        lambda *a: pytest.fail("named a control off macOS"))

    assert M.apply_accessible_names(_Window("panel", [_Window("Your message")])) == 0


def test_a_window_without_children_is_not_an_error(named):
    """Called on every dialog, including ones built from a bare panel."""
    assert M.apply_accessible_names(object()) == 0


def test_naming_a_bogus_window_returns_false_rather_than_raising():
    """Naming is an enhancement; failing to name must not take the window down."""
    assert M.set_accessible_name(object(), "Something") is False
    assert M.get_accessible_name(object()) is None
    assert M.set_accessible_help(object(), "Some help") is False


# ---------------------------------------------------------------------------
# The dialog hook
# ---------------------------------------------------------------------------

class _FakeDialog:
    def __init__(self, children=()):
        self._children = list(children)
        self.shown = []

    def GetName(self):
        return "dialog"

    def GetChildren(self):
        return self._children

    def Show(self, show=True):
        self.shown.append(("Show", show))
        return "show-result"

    def ShowModal(self):
        self.shown.append(("ShowModal",))
        return 5100


@pytest.fixture
def fake_wx(monkeypatch):
    """A wx stand-in with a *fresh* Dialog class per test.

    The hook marks the class it patched so it cannot be installed twice, and
    that mark would otherwise leak from one test to the next.
    """
    monkeypatch.setattr(M, "IS_MACOS", True)
    return types.SimpleNamespace(Dialog=type("Dialog", (_FakeDialog,), {}))


def test_the_hook_names_a_dialog_when_it_is_shown(fake_wx, named):
    assert M.install_dialog_naming(fake_wx) is True
    dialog = fake_wx.Dialog([_Window("API key")])

    assert dialog.ShowModal() == 5100, "the hook must pass the result through"
    assert named == ["API key"]
    assert dialog.shown == [("ShowModal",)]


def test_the_hook_covers_modeless_dialogs_too(fake_wx, named):
    M.install_dialog_naming(fake_wx)
    dialog = fake_wx.Dialog([_Window("Your message")])

    assert dialog.Show() == "show-result"
    assert named == ["Your message"]


def test_hiding_a_dialog_does_not_re_name_it(fake_wx, named):
    M.install_dialog_naming(fake_wx)
    dialog = fake_wx.Dialog([_Window("Your message")])

    dialog.Show(False)

    assert named == []
    assert dialog.shown == [("Show", False)]


def test_installing_twice_does_not_stack_wrappers(fake_wx, named):
    assert M.install_dialog_naming(fake_wx) is True
    assert M.install_dialog_naming(fake_wx) is False

    fake_wx.Dialog([_Window("API key")]).ShowModal()

    assert named == ["API key"], "one name per control, not one per install"


def test_the_hook_is_not_installed_off_macos(monkeypatch):
    monkeypatch.setattr(M, "IS_MACOS", False)

    assert M.install_dialog_naming(types.SimpleNamespace(Dialog=_FakeDialog)) is False
