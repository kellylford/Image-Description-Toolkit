"""Ask Cocoa which command a chord actually runs — the layer that was missing.

The bug this exists for: with focus in the message box, Cmd+A opened the
Attach Files dialog instead of selecting the text. Twenty-two tests were green
at the time. They asserted the menu *table* (``Ctrl+A`` is bound to
``wx.ID_SELECTALL``) and the *routing* (given a focused text control,
``_text_command`` calls ``SelectAll``). Nothing in between: no test ever asked
what a key press does, which is the only thing the user experiences.

Why NSEvent and not wx.UIActionSimulator
----------------------------------------
``UIActionSimulator`` posts CGEvents, and macOS drops those on the floor
unless the posting process is trusted for Accessibility. On a CI runner it is
not, so a simulator-based test presses nothing and passes — a vacuous test in
exactly the place we most need a real one.

Building an NSEvent and handing it to ``[NSApp.mainMenu performKeyEquivalent:]``
runs Cocoa's own matching code, in-process, with no permissions at all. That
matching is the thing that was wrong, so it is the thing to measure.
"""
from __future__ import annotations

import ctypes
import ctypes.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(_ROOT), str(_ROOT / "chatapp")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

pytestmark = pytest.mark.skipif(sys.platform != "darwin",
                                reason="Cocoa key equivalents are macOS only")

wx = pytest.importorskip("wx")


# --- the small slice of the Objective-C runtime this needs -----------------

_objc = ctypes.cdll.LoadLibrary(ctypes.util.find_library("objc"))
_objc.sel_registerName.restype = ctypes.c_void_p
_objc.sel_registerName.argtypes = [ctypes.c_char_p]
_objc.objc_getClass.restype = ctypes.c_void_p
_objc.objc_getClass.argtypes = [ctypes.c_char_p]


def _send(obj, selector, *args, restype=ctypes.c_void_p, argtypes=()):
    """``[obj selector:args]``, re-cast per signature as arm64 requires."""
    signature = ctypes.CFUNCTYPE(restype, ctypes.c_void_p, ctypes.c_void_p,
                                 *argtypes)
    call = signature(ctypes.cast(_objc.objc_msgSend, ctypes.c_void_p).value)
    return call(obj, _objc.sel_registerName(selector.encode()), *args)


def _nsstring(text: str):
    return _send(_objc.objc_getClass(b"NSString"), "stringWithUTF8String:",
                 text.encode("utf-8"), argtypes=(ctypes.c_char_p,))


def _to_str(nsstring) -> str:
    if not nsstring:
        return ""
    pointer = _send(nsstring, "UTF8String", restype=ctypes.c_char_p)
    return pointer.decode("utf-8") if pointer else ""


NSKeyDown = 10
MOD_SHIFT = 1 << 17
MOD_CTRL = 1 << 18
MOD_ALT = 1 << 19
MOD_CMD = 1 << 20

#: NSEvent needs a location and a window number; neither affects matching.
_EVENT_SELECTOR = (
    "keyEventWithType:location:modifierFlags:timestamp:windowNumber:"
    "context:characters:charactersIgnoringModifiers:isARepeat:keyCode:"
)


class _NSPoint(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]


def _key_event(characters: str, modifiers: int, key_code: int = 0):
    """An NSEvent for a chord, as AppKit would deliver it.

    ``charactersIgnoringModifiers`` is what Cocoa matches against, and Shift is
    *not* ignored: Cmd+A gives "a", Cmd+Shift+A gives "A". Getting that
    backwards is how a test can press a chord nobody ever bound and still pass.
    """
    shifted = characters.upper() if modifiers & MOD_SHIFT else characters
    return _send(
        _objc.objc_getClass(b"NSEvent"), _EVENT_SELECTOR,
        ctypes.c_ulong(NSKeyDown),
        _NSPoint(0.0, 0.0),
        ctypes.c_ulong(modifiers),
        ctypes.c_double(0.0),
        ctypes.c_long(0),
        None,
        ctypes.c_void_p(_nsstring(shifted)),
        ctypes.c_void_p(_nsstring(shifted)),
        ctypes.c_bool(False),
        ctypes.c_ushort(key_code),
        restype=ctypes.c_void_p,
        argtypes=(ctypes.c_ulong, _NSPoint, ctypes.c_ulong, ctypes.c_double,
                  ctypes.c_long, ctypes.c_void_p, ctypes.c_void_p,
                  ctypes.c_void_p, ctypes.c_bool, ctypes.c_ushort),
    )


def _main_menu():
    nsapp = _send(_objc.objc_getClass(b"NSApplication"), "sharedApplication")
    return _send(nsapp, "mainMenu")


def _menu_table():
    """Every native menu item: path -> (keyEquivalent, modifierMask)."""
    table = {}

    def walk(menu, prefix=""):
        count = _send(menu, "numberOfItems", restype=ctypes.c_long)
        for index in range(count):
            item = _send(menu, "itemAtIndex:", ctypes.c_long(index),
                         argtypes=(ctypes.c_long,))
            title = _to_str(_send(item, "title"))
            key = _to_str(_send(item, "keyEquivalent"))
            mask = _send(item, "keyEquivalentModifierMask", restype=ctypes.c_ulong)
            if key:
                table[f"{prefix}{title}"] = (key, int(mask))
            submenu = _send(item, "submenu")
            if submenu and not prefix:
                walk(submenu, f"{title} > ")

    walk(_main_menu())
    return table


def _describe(mask: int) -> str:
    names = [(MOD_CMD, "Cmd"), (MOD_SHIFT, "Shift"), (MOD_ALT, "Alt"),
             (MOD_CTRL, "Ctrl")]
    return "+".join(name for bit, name in names if mask & bit)


# --- fixtures --------------------------------------------------------------

@pytest.fixture(scope="module")
def app():
    try:
        return wx.App.Get() or wx.App(False)
    except Exception as exc:                                # noqa: BLE001
        pytest.skip(f"no usable display for wxPython: {exc}")


#: Commands that would put a modal on screen. On a runner a real modal blocks
#: until the job times out, so each is replaced by a recorder — which is also
#: how the test learns *which* command a chord ran.
_MODAL_COMMANDS = (
    "on_attach_files", "on_paste_image", "on_export", "on_settings",
    "on_api_keys", "on_change_model", "on_system_prompt", "on_token_usage",
    "on_shortcuts", "on_about", "on_delete_chat", "on_send",
    "on_toggle_web_search", "on_open_session",
)


@pytest.fixture
def frame(app, tmp_path, monkeypatch):
    """A real ChatFrame that cannot open a modal.

    Everything that matters here -- the menu bar, the accelerators, Cocoa's
    matching -- is the genuine article. Only the ends of the command paths are
    stubbed, and three belt-and-braces guards make it impossible for an
    unforeseen chord to hang the runner: MessageBox, ShowModal and FileDialog
    all become no-ops.
    """
    import chat_app_wx
    from chat_app_wx import ChatFrame
    from idt_core.chat import DirectoryChatStore

    fired = []
    for name in _MODAL_COMMANDS:
        monkeypatch.setattr(
            ChatFrame, name,
            (lambda n: lambda self, event=None: fired.append(n))(name))

    monkeypatch.setattr(chat_app_wx.wx, "MessageBox",
                        lambda *a, **k: fired.append("MessageBox") or wx.OK)
    monkeypatch.setattr(wx.Dialog, "ShowModal",
                        lambda self: fired.append("ShowModal") or wx.ID_CANCEL)
    monkeypatch.setattr(chat_app_wx.wx, "FileDialog",
                        lambda *a, **k: pytest.fail("a real FileDialog opened"))

    window = ChatFrame()
    window.store = DirectoryChatStore(tmp_path)
    window.fired = fired
    window.Show()
    window.Raise()
    wx.Yield()
    yield window
    window.Destroy()
    wx.Yield()


def _ns_window(frame):
    """The NSWindow behind a wx frame."""
    return _send(ctypes.c_void_p(frame.GetHandle()), "window")


def _button_key_equivalents(frame):
    """Every view in the window that claims a key equivalent.

    This is the half of dispatch a menu dump cannot see. AppKit offers a key
    equivalent to the key window's view hierarchy *before* the main menu, so a
    control that claims a chord beats a perfectly correct menu bar. Buttons are
    the usual culprit, because a "&" mnemonic in a wx label -- Alt+A on Windows,
    where it is harmless -- can arrive here as a Command key equivalent.
    """
    found = {}

    def walk(view):
        if _responds(view, "keyEquivalent"):
            key = _to_str(_send(view, "keyEquivalent"))
            if key:
                mask = _send(view, "keyEquivalentModifierMask",
                             restype=ctypes.c_ulong)
                title = _to_str(_send(view, "title")) if _responds(view, "title") else ""
                found[title or "<untitled>"] = (key, int(mask))
        subviews = _send(view, "subviews")
        if subviews:
            count = _send(subviews, "count", restype=ctypes.c_ulong)
            for index in range(count):
                walk(ctypes.c_void_p(_send(
                    subviews, "objectAtIndex:", ctypes.c_ulong(index),
                    argtypes=(ctypes.c_ulong,))))

    content = _send(_ns_window(frame), "contentView")
    if content:
        walk(ctypes.c_void_p(content))
    return found


def _responds(obj, selector) -> bool:
    return bool(_send(
        obj, "respondsToSelector:",
        ctypes.c_void_p(_objc.sel_registerName(selector.encode())),
        restype=ctypes.c_bool, argtypes=(ctypes.c_void_p,)))


def _press(frame, characters, modifiers):
    """Send a chord the way AppKit does: the window first, then the menu.

    Order matters and getting it wrong hides the bug. NSApplication offers a
    key equivalent to the key window's view hierarchy before consulting the
    main menu, so a test that asks the menu directly will report a correct menu
    table while the user watches the wrong command run.
    """
    del frame.fired[:]
    event = ctypes.c_void_p(_key_event(characters, modifiers))

    handled = _send(_ns_window(frame), "performKeyEquivalent:", event,
                    restype=ctypes.c_bool, argtypes=(ctypes.c_void_p,))
    where = "window"
    if not handled:
        handled = _send(_main_menu(), "performKeyEquivalent:", event,
                        restype=ctypes.c_bool, argtypes=(ctypes.c_void_p,))
        where = "menu" if handled else "nothing"
    wx.Yield()
    return bool(handled), where


# --- the tests -------------------------------------------------------------

def test_cmd_a_selects_text_and_does_not_attach_files(frame):
    """The reported bug, stated as a test.

    Focus the message box, type into it, press Cmd+A. The text must end up
    selected and the Attach Files command must not have run.
    """
    frame.input_text.SetValue("hello world")
    frame.input_text.SetFocus()
    frame.input_text.SetSelection(0, 0)
    wx.Yield()

    claimed, where = _press(frame, "a", MOD_CMD)

    buttons = {k: f"{_describe(v[1])}+{v[0]}"
               for k, v in _button_key_equivalents(frame).items()}
    assert where != "window", (
        f"Cmd+A was swallowed by a control in the window before the menu saw "
        f"it. Views claiming a key equivalent: {buttons}")
    assert "on_attach_files" not in frame.fired, (
        f"Cmd+A ran the wrong command: {frame.fired}")

    if not claimed:
        table = {k: f"{_describe(v[1])}+{v[0]}" for k, v in _menu_table().items()}
        pytest.skip(
            "nothing claimed Cmd+A, so this run proves nothing about dispatch "
            f"— the window is probably not key on this runner. Menu: {table}")

    assert frame.input_text.GetStringSelection() == "hello world", (
        f"Cmd+A was claimed by the {where} but selected nothing. "
        f"Commands that ran: {frame.fired}")


def test_no_control_in_the_window_steals_a_command_chord(frame):
    """The half of dispatch a menu dump cannot see.

    A "&" in a wx button label is an Alt mnemonic on Windows and nothing on
    macOS — unless wx turns it into a Command key equivalent on the NSButton,
    in which case that button quietly outranks the entire menu bar, because
    AppKit asks the key window before it asks the menu.
    """
    stolen = {title: f"{_describe(mask)}+{key}"
              for title, (key, mask) in _button_key_equivalents(frame).items()
              if mask & MOD_CMD}
    assert not stolen, (
        f"controls in the window claim Command chords, which beat the menu "
        f"bar: {stolen}")


def test_cmd_shift_a_is_the_one_that_attaches(frame):
    """The other half: the chord that *should* attach still does."""
    frame.input_text.SetFocus()
    wx.Yield()

    _press(frame, "a", MOD_CMD | MOD_SHIFT)

    assert frame.fired == ["on_attach_files"], (
        f"Cmd+Shift+A should attach files, but ran {frame.fired}")


@pytest.mark.parametrize("chord,characters,modifiers,forbidden", [
    ("Cmd+C", "c", MOD_CMD, "on_copy_all"),
    ("Cmd+V", "v", MOD_CMD, "on_paste_image"),
    ("Cmd+R", "r", MOD_CMD, "on_read_last"),
    ("Cmd+E", "e", MOD_CMD, "on_export"),
    ("Cmd+P", "p", MOD_CMD, "on_system_prompt"),
    ("Cmd+M", "m", MOD_CMD, "on_change_model"),
])
def test_an_unshifted_chord_never_runs_its_shifted_neighbour(
        frame, chord, characters, modifiers, forbidden):
    """The whole family the Cmd+A bug belongs to.

    Every X / Shift+X pair in this app is a chance for the shifted command to
    answer the unshifted chord. One of them did.
    """
    frame.input_text.SetFocus()
    wx.Yield()

    _press(frame, characters, modifiers)

    assert forbidden not in frame.fired, (
        f"{chord} ran {forbidden}, which belongs to Shift+{chord}")


def test_no_chord_answers_two_different_commands(frame):
    """Covers wx's own application and Window menus, which no wx-level walk
    can see -- Quit and Minimize live there.

    Two menu items on one chord is only a bug when they are different
    commands. wx puts Quit in the application menu *and* in File, and gives
    both Cmd+Q however the source leaves the accelerator off; since both quit,
    that costs the user nothing. The invariant worth enforcing is that a chord
    never means two different things.
    """
    seen = {}
    for path, combo in _menu_table().items():
        seen.setdefault(combo, []).append(path)

    clashes = {}
    for (key, mask), paths in seen.items():
        if len(paths) < 2:
            continue
        # "Quit IDT Chat" and "File > Quit" are the same command; compare on
        # the leading word of the item title, not the whole path.
        commands = {path.rsplit(" > ", 1)[-1].split(" ")[0] for path in paths}
        if len(commands) > 1:
            clashes[f"{_describe(mask)}+{key}"] = paths
    assert not clashes, f"one chord, two different commands: {clashes}"


def test_the_system_chords_mean_what_macos_means_by_them(frame):
    """Cmd+A is Select All, Cmd+M is Minimize, Cmd+Q is Quit -- no exceptions."""
    table = _menu_table()
    by_combo = {combo: path for path, combo in table.items()}

    expectations = {
        ("a", MOD_CMD): "Select All",
        ("m", MOD_CMD): "Minimize",
        ("q", MOD_CMD): "Quit",
        ("x", MOD_CMD): "Cut",
        ("c", MOD_CMD): "Copy",
        ("v", MOD_CMD): "Paste",
        ("z", MOD_CMD): "Undo",
    }
    wrong = {}
    for combo, expected in expectations.items():
        path = by_combo.get(combo)
        if path is not None and expected.lower() not in path.lower():
            wrong[f"{_describe(combo[1])}+{combo[0]}"] = f"{path!r}, expected {expected}"
    assert not wrong, f"system chords bound to the wrong commands: {wrong}"
