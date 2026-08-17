"""The chat app's keyboard accelerators must not take over platform standards.

Source-level on purpose: no wx, no display, no App. These are the checks that
have to run on the Windows CI box and on the Mac alike, because the mistake
they guard against is exactly a shortcut that looks fine on the platform the
author happened to be using.

wx maps every ``Ctrl+`` accelerator to Command on macOS, so one string has to
clear two sets of conventions at once. That is how ``Ctrl+M`` for Change Model
came to shadow Cmd+M (Minimize), and how ``Ctrl+C`` for "copy the selected
message" came to make Cmd+C useless in every text box in the window.
"""

import ast
import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
APP_SOURCE = _ROOT / "chatapp" / "chat_app_wx.py"


@pytest.fixture(scope="module")
def source() -> str:
    return APP_SOURCE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def menu_source(source) -> str:
    """Just the body of _build_menu, so unrelated strings cannot register."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_build_menu":
            return ast.get_source_segment(source, node) or ""
    pytest.fail("_build_menu not found")


def _accelerators(text: str):
    """Every accelerator spelled out in menu labels: ``"&Copy\\tCtrl+C"``.

    Misses the two that are chosen at runtime (Redo, and the help key), which
    are asserted separately; those are per-platform by construction.
    """
    return re.findall(r"\\t([A-Za-z0-9+?.,]+)", text)


# ---------------------------------------------------------------------------
# Chords the operating systems have already claimed
# ---------------------------------------------------------------------------

#: accelerator -> what it already means, and where.
RESERVED = {
    "Ctrl+M": "Cmd+M minimises the window on macOS (wx puts it on the "
              "automatic Window menu)",
    "Ctrl+W": "Cmd+W closes the window on macOS; it may only be bound to "
              "Close Window",
    "Ctrl+Shift+W": "Cmd+Shift+W is the close-window family on macOS",
    "Ctrl+,": "Cmd+, is Settings, supplied by the macOS application menu",
    "Ctrl+Q": "Cmd+Q is Quit, supplied by the macOS application menu",
    "Ctrl+H": "Cmd+H hides the application on macOS",
    "Ctrl+Space": "reserved by the input-source switcher and Spotlight",
}

#: The ones that must reach the focused control instead of a bespoke command.
STANDARD_EDIT_IDS = (
    "wx.ID_UNDO", "wx.ID_REDO", "wx.ID_CUT", "wx.ID_COPY", "wx.ID_PASTE",
    "wx.ID_SELECTALL",
)


def test_no_accelerator_is_claimed_twice(menu_source):
    """Two commands on one chord means one of them silently never runs."""
    found = _accelerators(menu_source)
    duplicates = {a for a in found if found.count(a) > 1}
    assert not duplicates, f"accelerator bound more than once: {sorted(duplicates)}"


@pytest.mark.parametrize("chord", sorted(RESERVED))
def test_reserved_chords_are_left_alone(chord, menu_source):
    """A system chord taken by the app is a system behaviour the user loses."""
    if chord == "Ctrl+W":
        # Legitimate for Close Window and nothing else.
        for line in menu_source.splitlines():
            if "\\tCtrl+W" in line:
                assert "Close" in line, (
                    f"Ctrl+W is Close Window on macOS, not: {line.strip()}")
        return
    if chord in ("Ctrl+Q", "Ctrl+,"):
        # Spelled out for Windows through _accel(), which drops them on macOS
        # precisely because the application menu already supplies them.
        assert f'"{chord}"' not in menu_source or "_accel" in menu_source
        assert f"\\t{chord}" not in menu_source, (
            f"{chord} must go through _accel(): {RESERVED[chord]}")
        return
    assert chord not in _accelerators(menu_source), (
        f"{chord} is not available: {RESERVED[chord]}")


def test_the_standard_edit_menu_exists(menu_source):
    """Without it, macOS has no Cmd+A, Cmd+V, Cmd+Z in any text field.

    Cocoa dispatches cut:/copy:/paste:/selectAll:/undo: through menu items. An
    app with no Edit menu does not get them from anywhere else, which is why
    the API key box could not be pasted into.
    """
    missing = [i for i in STANDARD_EDIT_IDS if i not in menu_source]
    assert not missing, f"Edit menu is missing standard ids: {missing}"


def test_copy_is_the_standard_copy(menu_source):
    """Ctrl+C must be wx.ID_COPY, not a private "copy the message" command."""
    for line in menu_source.splitlines():
        if "\\tCtrl+C" in line and "Ctrl+Shift+C" not in line:
            break
    else:
        pytest.fail("no Ctrl+C accelerator found")
    # The id lands on the following line in the wrapped call.
    index = menu_source.splitlines().index(line)
    context = "\n".join(menu_source.splitlines()[index:index + 2])
    assert "wx.ID_COPY" in context, (
        f"Ctrl+C must be the standard Copy command: {context.strip()}")


def test_the_mac_application_menu_ids_are_used(source):
    """Settings, About and Quit reach these handlers only through these ids."""
    for wid in ("wx.ID_PREFERENCES", "wx.ID_ABOUT", "wx.ID_EXIT"):
        assert wid in source, (
            f"{wid} is what wires the macOS application menu to a handler")


def test_delete_chat_still_has_no_accelerator(menu_source):
    """A plain-Delete accelerator would break typing; it is contextual instead."""
    for line in menu_source.splitlines():
        if "Delete Chat" in line:
            assert "\\t" not in line, f"Delete Chat must stay unbound: {line}"


def test_the_shortcut_list_covers_every_accelerator(source, menu_source):
    """Help > Keyboard Shortcuts is the only place these are written down."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_shortcut_lines":
            listing = ast.get_source_segment(source, node) or ""
            break
    else:
        pytest.fail("_shortcut_lines not found")

    # The listing spells the modifier per platform ("Cmd+N" / "Ctrl+N"), so
    # compare on the key part alone.
    documented = set(re.findall(r"\{mod\}\+([A-Za-z0-9+?.]+)", listing))
    for accel in _accelerators(menu_source):
        key = accel[len("Ctrl+"):] if accel.startswith("Ctrl+") else accel
        if key in ("Return", "W"):
            continue        # Send is listed as Enter; Close Window is macOS glue
        assert key in documented, (
            f"{accel} is not in Help > Keyboard Shortcuts")
