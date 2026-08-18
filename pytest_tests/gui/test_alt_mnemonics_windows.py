"""Ask the built window which Alt letters it actually claims.

The Windows counterpart of ``test_key_equivalent_dispatch_macos.py``, and it
exists for the same reason: the source-level checks in
``unit/test_mnemonics.py`` read labels out of the AST, and a label the app
*writes at runtime* is invisible to them. That is not hypothetical -- the
attachments label is rewritten by ``_refresh_attachments`` on every change, so
the mnemonic a user actually meets came from there, not from the constructor.

What it measures: on Windows, wx runs a frame's child panel through
``IsDialogMessage`` before the frame handles ``WM_SYSCHAR``. A mnemonic on a
panel control therefore answers Alt+letter *before* the menu bar does. So a
control sharing a letter with a menu title does not merely duplicate it -- it
takes that menu away. ``Atta&chments`` took Alt+C from the ``&Chat`` menu that
way, and ``Conversation &history`` took Alt+H from ``&Help``.

This builds the real frames and reads ``GetLabel()`` off the live widgets, so
it sees whatever the app last set.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(_ROOT), str(_ROOT / "chatapp"), str(_ROOT / "imagedescriber")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

pytestmark = pytest.mark.skipif(
    sys.platform != "win32",
    reason="Alt mnemonics are a Windows system; macOS has no equivalent")

wx = pytest.importorskip("wx")

_MNEMONIC = re.compile(r"&([A-Za-z0-9])")


def _letter(label):
    """The Alt letter a live label claims, or None. "&&" is a literal "&"."""
    match = _MNEMONIC.search((label or "").replace("&&", ""))
    return match.group(1).upper() if match else None


@pytest.fixture(scope="module")
def app():
    existing = wx.App.Get()
    if existing is not None:
        yield existing
        return
    created = wx.App(False)
    yield created


def _menu_titles(frame):
    """{letter: title} for the menu bar."""
    bar = frame.GetMenuBar()
    assert bar is not None, "frame has no menu bar"
    titles = {}
    for index in range(bar.GetMenuCount()):
        title = bar.GetMenuLabel(index)
        letter = _letter(title)
        if letter:
            titles.setdefault(letter, []).append(title)
    return titles


def _control_labels(window):
    """(letter, label, class name) for every live descendant carrying a "&"."""
    found = []
    for child in window.GetChildren():
        try:
            label = child.GetLabel()
        except Exception:              # not every native control has one
            label = ""
        letter = _letter(label)
        if letter:
            found.append((letter, label, type(child).__name__))
        found.extend(_control_labels(child))
    return found


def _menu_duplicates(menu, path=""):
    """[(path, letter, first label, second label)] for repeats in one menu."""
    problems, seen = [], {}
    for item in menu.GetMenuItems():
        label = item.GetItemLabel()
        letter = _letter(label)
        if letter:
            name = label.split("\t")[0]
            if letter in seen and seen[letter] != name:
                problems.append((path, letter, seen[letter], name))
            seen[letter] = name
        submenu = item.GetSubMenu()
        if submenu is not None:
            problems.extend(_menu_duplicates(
                submenu, f"{path} > {label.split(chr(9))[0]}"))
    return problems


# ---------------------------------------------------------------------------
# IDT Chat -- where the bug was reported
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def chat_frame(app):
    from chat_app_wx import ChatFrame
    frame = ChatFrame()
    yield frame
    frame.Destroy()


def test_chat_controls_leave_the_menu_bar_its_letters(chat_frame):
    """Reported from Windows: Alt+C reached the attachments list, not Chat."""
    titles = _menu_titles(chat_frame)
    assert set(titles) == {"F", "E", "C", "V", "H"}, titles

    stolen = [f"{name} {label!r} takes Alt+{letter} from {titles[letter][0]!r}"
              for letter, label, name in _control_labels(chat_frame)
              if letter in titles]
    assert not stolen, "; ".join(stolen)


def test_chat_controls_do_not_share_a_letter(chat_frame):
    claims = {}
    for letter, label, _name in _control_labels(chat_frame):
        claims.setdefault(letter, set()).add(label)
    shared = {k: sorted(v) for k, v in claims.items() if len(v) > 1}
    assert not shared, f"controls sharing an Alt letter: {shared}"


def test_the_attachments_label_keeps_its_letter_through_a_refresh(chat_frame):
    """The label is rewritten per state; every state must claim the same key.

    This is the case the AST-based test cannot see, and the one that shipped:
    the mnemonic users met came from ``_refresh_attachments``.
    """
    before = chat_frame.attach_label.GetLabel()
    chat_frame._refresh_attachments()
    after = chat_frame.attach_label.GetLabel()
    assert _letter(after) == _letter(before) == "N", (before, after)
    assert _letter(after) not in _menu_titles(chat_frame)


def test_no_chat_menu_repeats_a_letter(chat_frame):
    bar = chat_frame.GetMenuBar()
    problems = []
    for index in range(bar.GetMenuCount()):
        problems.extend(_menu_duplicates(bar.GetMenu(index),
                                         bar.GetMenuLabel(index)))
    assert not problems, problems


# ---------------------------------------------------------------------------
# ImageDescriber
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def describer_frame(app):
    from imagedescriber_wx import ImageDescriberFrame
    frame = ImageDescriberFrame()
    yield frame
    frame.Destroy()


def test_describer_controls_leave_the_menu_bar_its_letters(describer_frame):
    titles = _menu_titles(describer_frame)
    assert set(titles) == {"F", "E", "P", "D", "V", "T", "H"}, titles

    stolen = [f"{name} {label!r} takes Alt+{letter} from {titles[letter][0]!r}"
              for letter, label, name in _control_labels(describer_frame)
              if letter in titles]
    assert not stolen, "; ".join(stolen)


def test_no_describer_menu_repeats_a_letter(describer_frame):
    """Nine letters were claimed twice, so nine keys needed Enter to commit."""
    bar = describer_frame.GetMenuBar()
    problems = []
    for index in range(bar.GetMenuCount()):
        problems.extend(_menu_duplicates(bar.GetMenu(index),
                                         bar.GetMenuLabel(index)))
    assert not problems, problems
