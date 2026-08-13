"""Events yielded by :meth:`ChatEngine.send`.

One event stream serves every consumer. A CLI prints deltas as they arrive; a
wx GUI forwards each event to the UI thread with ``wx.CallAfter``; a test
collects them into a list. Nothing here knows which.

Mirrors the shape ``WorkspacePipeline.run()`` already uses in
``idt_core/pipeline.py`` — yield events, let the caller decide on output.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Union

from .messages import ChatMessage


@dataclass
class ChatStarted:
    """Emitted once, after the user turn is committed to history."""

    provider: str
    model: str
    #: Turns actually sent, after token-budget truncation.
    sent_messages: int = 0
    #: Turns dropped to fit the budget. Non-zero means the model can no longer
    #: see the start of the conversation, which the UI must surface — the old
    #: implementation only wrote this to stdout via print().
    dropped_messages: int = 0


@dataclass
class ChatDelta:
    """A chunk of assistant text.

    Non-streaming providers emit exactly one of these with the whole response,
    so consumers never need to know which providers stream.
    """

    text: str


@dataclass
class ChatUsage:
    """Token counts, normally available only at the end of a turn."""

    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class ChatFinished:
    """The turn completed normally."""

    message: ChatMessage


@dataclass
class ChatCancelled:
    """The consumer stopped the turn.

    ``message`` holds whatever text had arrived, already saved to history —
    a stopped response is kept, not thrown away.
    """

    message: ChatMessage


@dataclass
class ChatFailed:
    """The turn failed. ``message`` carries any partial text plus the error."""

    error: str
    message: Optional[ChatMessage] = None
    attempts: int = 1
    retryable: bool = False


@dataclass
class ChatRetrying:
    """A transient failure is about to be retried."""

    error: str
    attempt: int
    delay_seconds: float = 0.0


ChatEvent = Union[
    ChatStarted,
    ChatDelta,
    ChatUsage,
    ChatRetrying,
    ChatFinished,
    ChatCancelled,
    ChatFailed,
]

#: Events after which no further event arrives for that turn.
TERMINAL_EVENTS = (ChatFinished, ChatCancelled, ChatFailed)
