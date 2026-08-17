"""Repair what wx gets wrong natively on macOS: control names, and stolen keys.

Two unrelated defects, both fixed by reaching past wx to the native view, and
both no-ops off macOS.

Keys wx gives away
------------------
``wx.Button(panel, label="&Attach Files...")`` is an Alt mnemonic on Windows
and should be nothing at all on macOS. wxOSX instead turns the ``&`` into a
**Command key equivalent on the NSButton** — measured on a macOS runner, that
window's buttons claimed ``Cmd+s``, ``Cmd+t``, ``Cmd+a`` and ``Cmd+r``.

That is not a cosmetic problem. AppKit offers a key equivalent to the key
window's view hierarchy *before* the main menu, so those buttons outrank the
menu bar: Cmd+A opened the Attach Files dialog instead of selecting text, with
a completely correct Edit menu sitting behind it. ``clear_command_key_equivalents``
takes those chords back.

Why VoiceOver naming is here too
--------------------------------
wx has no working way to name a control for VoiceOver. Measured on wxPython
4.3.1 / wxWidgets 3.3.3 (Apple Silicon):

* ``wx.Window.SetAccessible()`` raises ``NotImplementedError`` — the whole
  ``wx.Accessible`` framework is Windows-only.
* ``SetName()`` and the ``name=`` constructor argument reach nothing native.
  Every ``wx.TextCtrl``, ``wx.ListBox`` and ``wx.Choice`` reports
  ``accessibilityLabel == nil`` however it was named, which is why tabbing to
  them announced the value but never the label. (``wx.Button`` and
  ``wx.CheckBox`` are fine without help: AppKit derives their accessible name
  from the button title.)

So the label has to be set on the native view, through the NSAccessibility
protocol. That is done here with ``ctypes`` rather than PyObjC, because
PyObjC is not a dependency of this project and adding one to the frozen macOS
bundles for three selector calls is a poor trade.

Everything in this module is a no-op off macOS, so Windows behaviour — where
``SetName`` plus a ``wx.Accessible`` already works — is untouched.

The documentView step
---------------------
``GetHandle()`` does not always return the view VoiceOver lands on. A
multi-line ``wx.TextCtrl`` is a ``wxNSTextScrollView`` wrapping a
``wxNSTextView``; a ``wx.ListBox`` is an ``NSScrollView`` wrapping a
``wxNSTableView``. VoiceOver focuses the inner view (AXTextArea, AXTable), so
labelling the scroll view alone leaves the focused element anonymous. When the
handle has a ``documentView``, that is what gets the label.
"""
from __future__ import annotations

import ctypes
import ctypes.util
import sys

IS_MACOS = sys.platform == "darwin"

_objc = None            # the loaded libobjc, or False once loading has failed


def _runtime():
    """The Objective-C runtime, or None where it is unavailable."""
    global _objc
    if _objc is None:
        _objc = False
        if IS_MACOS:
            try:
                path = ctypes.util.find_library("objc")
                lib = ctypes.cdll.LoadLibrary(path) if path else None
            except OSError:
                lib = None
            if lib is not None:
                lib.sel_registerName.restype = ctypes.c_void_p
                lib.sel_registerName.argtypes = [ctypes.c_char_p]
                lib.objc_getClass.restype = ctypes.c_void_p
                lib.objc_getClass.argtypes = [ctypes.c_char_p]
                _objc = lib
    return _objc or None


def _send(obj, selector, *args, restype=ctypes.c_void_p, argtypes=()):
    """``[obj selector:args]``.

    objc_msgSend has to be re-cast for every signature: it is a variadic stub
    whose real prototype is the one of the method being called, and calling it
    through the wrong prototype is undefined on arm64.
    """
    objc = _runtime()
    signature = ctypes.CFUNCTYPE(restype, ctypes.c_void_p, ctypes.c_void_p,
                                 *argtypes)
    call = signature(ctypes.cast(objc.objc_msgSend, ctypes.c_void_p).value)
    return call(obj, objc.sel_registerName(selector.encode()), *args)


def _responds(obj, selector) -> bool:
    objc = _runtime()
    return bool(_send(
        obj, "respondsToSelector:",
        ctypes.c_void_p(objc.sel_registerName(selector.encode())),
        restype=ctypes.c_bool, argtypes=(ctypes.c_void_p,),
    ))


def _nsstring(text: str):
    objc = _runtime()
    return _send(objc.objc_getClass(b"NSString"), "stringWithUTF8String:",
                 text.encode("utf-8"), argtypes=(ctypes.c_char_p,))


def _to_str(nsstring) -> str | None:
    if not nsstring:
        return None
    pointer = _send(nsstring, "UTF8String", restype=ctypes.c_char_p)
    return pointer.decode("utf-8") if pointer else None


def _target_view(window):
    """The native view that carries the accessible name, or None.

    Steps inward to the ``documentView`` for scroll-backed controls; see the
    module docstring.
    """
    if _runtime() is None:
        return None
    try:
        handle = window.GetHandle()
    except (AttributeError, RuntimeError):
        return None
    if not handle:
        return None
    view = ctypes.c_void_p(handle)
    if _responds(view, "documentView"):
        inner = _send(view, "documentView")
        if inner:
            return ctypes.c_void_p(inner)
    return view


def set_accessible_name(window, label: str) -> bool:
    """Name `window` for VoiceOver. True if the name was applied.

    False — never an exception — off macOS, on a control with no native view,
    or on any wx or runtime version where the selector is missing. Naming a
    control is an enhancement; failing to name one must not take the window
    down with it.
    """
    if not IS_MACOS or not label:
        return False
    try:
        view = _target_view(window)
        if view is None or not _responds(view, "setAccessibilityLabel:"):
            return False
        _send(view, "setAccessibilityLabel:", ctypes.c_void_p(_nsstring(label)),
              argtypes=(ctypes.c_void_p,))
        return True
    except Exception:                                       # noqa: BLE001
        return False


#: wx's own default names, handed out when a control was constructed without
#: ``name=``. They are class names, not labels ("text", "listBox"), and pushing
#: them to VoiceOver would be worse than silence.
_WX_DEFAULT_NAMES = frozenset((
    "text", "listBox", "choice", "comboBox", "checkBox", "radioBox",
    "radioButton", "button", "staticText", "staticBox", "staticBitmap",
    "treeCtrl", "listCtrl", "dataView", "notebook", "panel", "dialog",
    "frame", "scrolledWindow", "spinCtrl", "spinButton", "slider", "gauge",
    "searchCtrl", "toolBar", "statusBar", "splitter", "collapsiblePane",
    "checkListBox", "genericDirCtrl", "filePickerCtrl", "dirPickerCtrl",
    "colourPickerCtrl", "fontPickerCtrl", "htmlWindow", "grid", "message",
    "sliderCtrl", "bmpButton", "toggleButton",
))


#: Classes the walk leaves alone. These are not tab stops, and their own text
#: *is* what a screen reader should read; giving them a separate name risks
#: changing that announcement for no gain. Matched by class name so this module
#: stays importable without wx.
_NOT_NAMED = frozenset(("StaticText", "StaticBox", "StaticBitmap", "StaticLine"))


def apply_accessible_names(root) -> int:
    """Publish every wx control name under `root` to VoiceOver.

    ``name=`` in a control's constructor is already the convention in this
    codebase, and it is what Windows screen readers read. This walks the window
    tree and gives each of those names to NSAccessibility as well, so one call
    at the end of a window's construction covers the whole window instead of a
    line per control.

    Controls still carrying wx's default name are skipped: those were built
    without a label, and announcing "listBox" is worse than announcing nothing.
    Add ``name=`` to the control instead.

    Returns how many controls were named, which is worth asserting in a test --
    a window that silently names nothing looks exactly like one that needs no
    naming.
    """
    if not IS_MACOS:
        return 0
    named = 0
    try:
        children = list(root.GetChildren())
    except (AttributeError, RuntimeError):
        return 0
    for child in children:
        try:
            label = child.GetName()
        except (AttributeError, RuntimeError):
            label = ""
        if (label and label not in _WX_DEFAULT_NAMES
                and type(child).__name__ not in _NOT_NAMED):
            if set_accessible_name(child, label):
                named += 1
        named += apply_accessible_names(child)
    return named


def set_accessible_help(window, text: str) -> bool:
    """Attach a longer explanation to `window` for VoiceOver.

    Read after the name, so it suits the "what will this button do" text the
    dialogs already carry. Windows has no wx-level equivalent, which is why
    this is macOS-only rather than part of ``set_accessible_name``.
    """
    if not IS_MACOS or not text:
        return False
    try:
        view = _target_view(window)
        if view is None or not _responds(view, "setAccessibilityHelp:"):
            return False
        _send(view, "setAccessibilityHelp:", ctypes.c_void_p(_nsstring(text)),
              argtypes=(ctypes.c_void_p,))
        return True
    except Exception:                                       # noqa: BLE001
        return False


#: NSEventModifierFlagCommand. Only Command equivalents are taken back: the
#: default button legitimately holds Return with no modifier, and clearing that
#: would stop Enter activating it.
_MOD_COMMAND = 1 << 20


def clear_command_key_equivalents(root) -> list[str]:
    """Take back Command chords wx handed to controls in `root`.

    Returns the titles it cleared, which is what a test asserts on and what a
    log line should say — silently fixing this would hide a wx regression the
    next time the mnemonic handling changes.

    Only Command chords are touched. A default button holds Return with an
    empty modifier mask and must keep it, or Enter stops working.
    """
    if not IS_MACOS or _runtime() is None:
        return []
    cleared = []
    try:
        handle = root.GetHandle()
    except (AttributeError, RuntimeError):
        return []
    if not handle:
        return []

    window = _send(ctypes.c_void_p(handle), "window")
    start = _send(window, "contentView") if window else handle
    if not start:
        return []

    def walk(view):
        if _responds(view, "keyEquivalentModifierMask"):
            mask = _send(view, "keyEquivalentModifierMask", restype=ctypes.c_ulong)
            key = _to_str(_send(view, "keyEquivalent")) if _responds(
                view, "keyEquivalent") else ""
            if key and int(mask) & _MOD_COMMAND:
                title = (_to_str(_send(view, "title"))
                         if _responds(view, "title") else "") or "<untitled>"
                _send(view, "setKeyEquivalent:", ctypes.c_void_p(_nsstring("")),
                      argtypes=(ctypes.c_void_p,))
                _send(view, "setKeyEquivalentModifierMask:", ctypes.c_ulong(0),
                      argtypes=(ctypes.c_ulong,))
                cleared.append(f"{title} ({_describe_mask(int(mask))}+{key})")
        subviews = _send(view, "subviews")
        if subviews:
            count = _send(subviews, "count", restype=ctypes.c_ulong)
            for index in range(count):
                walk(ctypes.c_void_p(_send(
                    subviews, "objectAtIndex:", ctypes.c_ulong(index),
                    argtypes=(ctypes.c_ulong,))))

    try:
        walk(ctypes.c_void_p(start))
    except Exception:                                       # noqa: BLE001
        return cleared
    return cleared


def _describe_mask(mask: int) -> str:
    names = [(_MOD_COMMAND, "Cmd"), (1 << 17, "Shift"), (1 << 19, "Alt"),
             (1 << 18, "Ctrl")]
    return "+".join(name for bit, name in names if mask & bit)


def install_dialog_naming(wx_module) -> bool:
    """Apply both macOS fix-ups to every dialog as it is shown: names, and the
    Command chords wx hands to buttons.

    (The name predates the second job. It is kept because two apps and the
    tests import it, and renaming it while fixing a live bug is churn for its
    own sake.)

    The alternative was a call at the end of each dialog's ``__init__`` -- 19
    of them across ImageDescriber, each needing to sit after the controls exist
    and before the dialog appears, and every one of them silently absent from
    the twentieth dialog somebody adds. Hooking ``Show``/``ShowModal`` gets the
    timing right by construction and cannot be forgotten.

    Takes the wx module as an argument so this file stays importable without
    wx, which is what lets the naming logic be tested on its own.

    Returns True if the hook was installed: False off macOS, or if it is
    already in place.
    """
    if not IS_MACOS:
        return False
    dialog = wx_module.Dialog
    if getattr(dialog, "_idt_accessible_naming", False):
        return False

    original_show_modal = dialog.ShowModal
    original_show = dialog.Show

    def show_modal(self, *args, **kwargs):
        apply_accessible_names(self)
        clear_command_key_equivalents(self)
        return original_show_modal(self, *args, **kwargs)

    def show(self, show=True, *args, **kwargs):
        if show:
            apply_accessible_names(self)
            clear_command_key_equivalents(self)
        return original_show(self, show, *args, **kwargs)

    dialog.ShowModal = show_modal
    dialog.Show = show
    dialog._idt_accessible_naming = True
    return True


def get_accessible_name(window) -> str | None:
    """The name VoiceOver would read for `window`, or None.

    Exists so the naming can be asserted in tests and inspected when a control
    is reported as unlabelled, rather than taken on trust.
    """
    if not IS_MACOS:
        return None
    try:
        view = _target_view(window)
        if view is None or not _responds(view, "accessibilityLabel"):
            return None
        return _to_str(_send(view, "accessibilityLabel"))
    except Exception:                                       # noqa: BLE001
        return None
