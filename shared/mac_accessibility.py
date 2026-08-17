"""Give wx controls a name VoiceOver will actually read.

Why this exists
---------------
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
