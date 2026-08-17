"""Menu accelerators must not take over platform standards, in either app.

Source-level on purpose: no wx, no display, no App. These are the checks that
have to run on the Windows CI box and on the Mac alike, because the mistake
they guard against is exactly a shortcut that looks fine on the platform the
author happened to be using.

wx maps every ``Ctrl+`` accelerator to Command on macOS, so one string has to
clear two sets of conventions at once. That is how ``Ctrl+M`` for Change Model
came to shadow Cmd+M (Minimize) in IDT Chat, how ``Ctrl+C`` for "copy the
selected message" made Cmd+C useless in every text box, and how ``Ctrl+P``
for Edit Prompts sat on Print in ImageDescriber -- a Windows standard as much
as a Mac one.
"""

import ast
import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]

#: app key -> (source file, the function that builds the menu bar)
APPS = {
    "chat": (_ROOT / "chatapp" / "chat_app_wx.py", "_build_menu"),
    "imagedescriber": (_ROOT / "imagedescriber" / "imagedescriber_wx.py",
                       "create_menu_bar"),
}


def _source(app: str) -> str:
    return APPS[app][0].read_text(encoding="utf-8")


def _menu_source(app: str) -> str:
    """Just the body of the menu builder, so unrelated strings cannot register."""
    path, function = APPS[app]
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function:
            return ast.get_source_segment(source, node) or ""
    pytest.fail(f"{function} not found in {path.name}")


def _accelerators(text: str):
    """Every accelerator spelled out in a menu label: ``"&Copy\\tCtrl+C"``.

    Misses the handful chosen at runtime (Redo, refresh, the help key), which
    are per-platform by construction and asserted separately.
    """
    return re.findall(r"\\t([A-Za-z0-9+?.,]+)", text)


# ---------------------------------------------------------------------------
# Chords the operating systems have already claimed
# ---------------------------------------------------------------------------

#: accelerator -> what it already means, and where.
RESERVED = {
    "Ctrl+M": "Cmd+M minimises the window on macOS (wx puts it on the "
              "automatic Window menu)",
    "Ctrl+Shift+W": "Cmd+Shift+W is the close-window family on macOS",
    "Ctrl+H": "Cmd+H hides the application on macOS",
    "Ctrl+Space": "reserved by the input-source switcher and Spotlight",
    "Ctrl+P": "Ctrl+P / Cmd+P is Print on both platforms, and it is pressed "
              "reflexively",
}

#: The ids that make the standard editing keys reach the focused control.
#: On macOS these are not a convenience: Cocoa dispatches cut:/copy:/paste:/
#: selectAll:/undo: *through* menu items, so a missing item is a key that does
#: nothing in every text field in the application.
STANDARD_EDIT_IDS = (
    "wx.ID_UNDO", "wx.ID_REDO", "wx.ID_CUT", "wx.ID_COPY", "wx.ID_PASTE",
    "wx.ID_SELECTALL",
)

every_app = pytest.mark.parametrize("app", sorted(APPS))


@every_app
def test_no_accelerator_is_claimed_twice(app):
    """Two commands on one chord means one of them silently never runs."""
    found = _accelerators(_menu_source(app))
    duplicates = {a for a in found if found.count(a) > 1}
    assert not duplicates, f"accelerator bound more than once: {sorted(duplicates)}"


@every_app
@pytest.mark.parametrize("chord", sorted(RESERVED))
def test_reserved_chords_are_left_alone(chord, app):
    """A system chord taken by the app is a system behaviour the user loses."""
    assert chord not in _accelerators(_menu_source(app)), (
        f"{chord} is not available: {RESERVED[chord]}")


@every_app
def test_close_window_is_the_only_use_of_ctrl_w(app):
    """Cmd+W closes the window on macOS whether an app implements it or not."""
    for line in _menu_source(app).splitlines():
        if "\\tCtrl+W" in line:
            assert "Close" in line, (
                f"Ctrl+W is Close Window on macOS, not: {line.strip()}")


@every_app
def test_quit_does_not_repeat_the_macos_accelerator(app):
    """The application menu already supplies Cmd+Q for the wx.ID_EXIT item.

    Spelling it out again puts two menu items on one chord -- which is what
    both apps did.
    """
    for line in _menu_source(app).splitlines():
        if "\\tCtrl+Q" in line:
            assert "darwin" in line or "_MAC" in line, (
                f"Ctrl+Q must be Windows-only: {line.strip()}")


@every_app
def test_the_standard_edit_menu_exists(app):
    """Missing ids are missing keys, not missing menu entries."""
    missing = [i for i in STANDARD_EDIT_IDS if i not in _menu_source(app)]
    assert not missing, f"Edit menu is missing standard ids: {missing}"


@every_app
def test_the_mac_application_menu_ids_are_used(app):
    """Settings, About and Quit reach their handlers only through these ids."""
    source = _source(app)
    for wid in ("wx.ID_PREFERENCES", "wx.ID_ABOUT", "wx.ID_EXIT"):
        assert wid in source, (
            f"{wid} is what wires the macOS application menu to a handler")


@every_app
def test_the_help_key_is_platform_correct(app):
    """F1 on Windows; Cmd+? on macOS, where F1 is a hardware key."""
    menu = _menu_source(app)
    assert "Ctrl+?" in menu, "no macOS help key (Cmd+?) in the Help menu"
    assert "F1" in menu, "no Windows help key (F1) in the Help menu"


# ---------------------------------------------------------------------------
# IDT Chat specifics
# ---------------------------------------------------------------------------

def test_copy_is_the_standard_copy():
    """Ctrl+C must be wx.ID_COPY, not a private "copy the message" command."""
    menu = _menu_source("chat")
    lines = menu.splitlines()
    for index, line in enumerate(lines):
        if "\\tCtrl+C" in line and "Ctrl+Shift+C" not in line:
            context = "\n".join(lines[index:index + 2])
            assert "wx.ID_COPY" in context, (
                f"Ctrl+C must be the standard Copy command: {context.strip()}")
            return
    pytest.fail("no Ctrl+C accelerator found")


def test_delete_chat_still_has_no_accelerator():
    """A plain-Delete accelerator would break typing; it is contextual instead."""
    for line in _menu_source("chat").splitlines():
        if "Delete Chat" in line:
            assert "\\t" not in line, f"Delete Chat must stay unbound: {line}"


def test_the_shortcut_list_covers_every_accelerator():
    """Help > Keyboard Shortcuts is the only place these are written down."""
    source = _source("chat")
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
    for accel in _accelerators(_menu_source("chat")):
        key = accel[len("Ctrl+"):] if accel.startswith("Ctrl+") else accel
        if key in ("Return", "W"):
            continue        # Send is listed as Enter; Close Window is macOS glue
        assert key in documented, (
            f"{accel} is not in Help > Keyboard Shortcuts")


# ---------------------------------------------------------------------------
# ImageDescriber specifics
# ---------------------------------------------------------------------------

def test_imagedescriber_keeps_the_windows_standards_it_uses():
    """Where it takes a Windows standard chord, it must mean the standard thing."""
    menu = _menu_source("imagedescriber")
    expected = {
        "Ctrl+N": "New", "Ctrl+O": "Open", "Ctrl+S": "Save",
        "Ctrl+Shift+S": "Save", "Ctrl+F": "Find", "Ctrl+Z": "Undo",
        "Ctrl+X": "Cut", "Ctrl+C": "Copy", "Ctrl+V": "Paste",
        "Ctrl+A": "All",
    }
    for chord, word in expected.items():
        for line in menu.splitlines():
            if f"\\t{chord}" in line:
                assert word.lower() in line.lower(), (
                    f"{chord} means {word} on Windows, not: {line.strip()}")
                break
        else:
            pytest.fail(f"{chord} is missing; it should be {word}")


def test_imagedescriber_refresh_and_rename_are_platform_correct():
    """F5 and F2 are Windows keys; on a Mac they are hardware keys."""
    menu = _menu_source("imagedescriber")
    for line in menu.splitlines():
        if line.strip().startswith("#"):
            continue        # the comment explaining the choice, not the choice
        if '"F5"' in line or "\\tF5" in line or "\\tF2" in line:
            assert "darwin" in line, (
                f"F-keys must be chosen per platform: {line.strip()}")


# ---------------------------------------------------------------------------
# Button mnemonics — the second, hidden accelerator table on macOS
# ---------------------------------------------------------------------------

def _mnemonic_controls(source: str):
    """Every button/checkbox label carrying a "&" mnemonic, with its chord.

    wxOSX's ``wxButtonCocoaImpl::SetAcceleratorFromLabel`` turns "&X" into a
    **Command** key equivalent on the NSButton, and AppKit offers key
    equivalents to the key window's views before the menu bar. So every one of
    these is a chord that outranks the entire menu — which is how
    ``&Attach Files...`` came to own Cmd+A and open the file picker instead of
    selecting text.
    """
    found = {}
    pattern = re.compile(
        r"wx\.(?:Button|CheckBox|RadioButton|ToggleButton)\([^)]*?"
        r'label="([^"]*&[A-Za-z][^"]*)"', re.S)
    for label in pattern.findall(source):
        index = label.index("&")
        found[label] = f"Cmd+{label[index + 1].lower()}"
    return found


@every_app
def test_mnemonic_labels_are_declared_not_forgotten(app):
    """Mnemonics are fine — as long as the app takes the chords back.

    This does not forbid "&" in a label: Alt mnemonics are worth having on
    Windows. It requires that an app carrying them also calls
    ``clear_command_key_equivalents``, which is what stops macOS turning them
    into Command chords that beat the menu bar.
    """
    source = _source(app)
    mnemonics = _mnemonic_controls(source)
    if not mnemonics:
        return                      # nothing to take back
    assert "clear_command_key_equivalents" in source, (
        f"{app} labels controls with mnemonics that become Command chords on "
        f"macOS, but never reclaims them: {mnemonics}")
