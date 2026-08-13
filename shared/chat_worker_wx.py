"""Bridge between :class:`idt_core.chat.ChatEngine` and the wx event loop.

Shared by ImageDescriber's chat window and the standalone IDT Chat app, so
there is exactly one place where chat events cross onto the UI thread.

One worker for every provider. The old design had four provider-specific code
paths inside a wx thread; here the engine yields events and this class does
nothing but move them to the UI thread.

Two hazards it exists to close:

* **Posting to a destroyed window.** The previous chat worker was a bare daemon
  thread holding a strong reference to its window, and ``on_close`` simply
  abandoned it — the thread went on posting events to a deleted C++ object. A
  ``weakref`` plus wx's falsiness check for destroyed windows makes a late
  event a no-op.
* **No way to stop.** There was no cancellation at all. Closing the generator
  raises ``GeneratorExit`` inside the engine, which closes the provider's HTTP
  stream and persists whatever text had arrived.
"""
from __future__ import annotations

import threading
import weakref
from typing import Callable, Iterator

import wx

from idt_core.chat import ChatEngine, ChatFailed


class ChatWorker(threading.Thread):
    """Runs one turn on a background thread, marshalling events to the UI.

    The window must expose ``on_chat_event(event)``; it is always called on the
    UI thread.
    """

    def __init__(
        self,
        window: wx.Window,
        engine: ChatEngine,
        start: Callable[[], Iterator],
    ):
        """
        Args:
            window: must expose ``on_chat_event(event)``
            engine: the engine being driven, so ``cancel()`` can reach it
            start: zero-argument callable returning the event generator, e.g.
                ``lambda: engine.send(text, attachments)`` or
                ``lambda: engine.continue_turn()``. A factory rather than a
                mode flag, so a caller can choose send / continue_turn /
                regenerate without this class growing a branch per case.
        """
        super().__init__(daemon=True)
        self._window_ref = weakref.ref(window)
        self._engine = engine
        self._start = start
        self._generator = None
        self._stop = threading.Event()

    # ---- lifecycle -------------------------------------------------------

    def run(self) -> None:
        try:
            self._generator = self._start()
            for event in self._generator:
                if self._stop.is_set():
                    break
                self._deliver(event)
        except Exception as exc:  # noqa: BLE001 - surfaced to the user
            self._deliver(ChatFailed(error=str(exc)))
        finally:
            self._close_generator()

    def cancel(self) -> None:
        """Stop the turn. Safe to call from the UI thread, or twice."""
        self._stop.set()
        self._engine.request_stop()

    def _close_generator(self) -> None:
        generator = self._generator
        self._generator = None
        if generator is not None:
            try:
                generator.close()
            except Exception:
                # Best effort teardown on a thread that is already finishing.
                # The generator may have raised on its way out, or been closed
                # already by a concurrent cancel(); either way there is nothing
                # left to salvage and nobody to report it to.
                pass

    # ---- delivery --------------------------------------------------------

    def _deliver(self, event) -> None:
        wx.CallAfter(self._dispatch, event)

    def _dispatch(self, event) -> None:
        """Runs on the UI thread."""
        window = self._window_ref()
        # wx windows are falsy once the underlying C++ object is destroyed, so
        # this covers both "garbage collected" and "closed while we were mid
        # response" without touching a dangling pointer.
        if window is None or not window:
            return
        window.on_chat_event(event)
