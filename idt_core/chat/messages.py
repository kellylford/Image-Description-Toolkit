"""Chat data model — conversations, turns, and attachments.

Deliberately free of any UI, provider SDK, or wx dependency: these types are
what the GUI, the CLI, and the standalone chat app all agree on.

The one subtle thing in here is that :class:`ChatSession` exposes **two**
different token totals. They are genuinely different numbers and conflating
them is a live defect in the existing chat window, which does::

    self._total_input_tokens += usage['input_tokens']

Every request re-sends the whole conversation, so each call's ``input_tokens``
already counts all prior turns. Summing them across turns therefore grows
roughly quadratically, and the context gauge reads "over budget" long before
the model actually is.

* :attr:`ChatSession.context_tokens` — what currently occupies the model's
  context window. That is the *last* exchange's input + output, not a sum.
* :attr:`ChatSession.billed_tokens` — what you have paid for across the whole
  session. That one *is* a sum.

A gauge wants the first. A cost display wants the second.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Literal, Optional, Sequence

Role = Literal["system", "user", "assistant"]

SCHEMA_VERSION = 2


def _now() -> str:
    return datetime.now().astimezone().isoformat()


def new_id(prefix: str = "chat") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


@dataclass
class Attachment:
    """A file sent along with a turn.

    ``data`` is optional: when it is None the bytes are read from ``path`` at
    send time. Keeping the path rather than the bytes means a long session does
    not hold every image it ever sent in memory.
    """

    media_type: str
    path: Optional[str] = None
    data: Optional[bytes] = None
    name: str = ""

    def __post_init__(self) -> None:
        if not self.name and self.path:
            self.name = Path(self.path).name

    @property
    def is_image(self) -> bool:
        return self.media_type.startswith("image/")

    @property
    def is_text(self) -> bool:
        """True when the content is inlined into the message text at send time
        rather than uploaded as a file. The registry owns the definition."""
        from ..providers.registry import is_text_media_type

        return is_text_media_type(self.media_type)

    def size_bytes(self) -> Optional[int]:
        """Size without reading the content — token estimation runs in loops,
        so it must cost a stat, not a read."""
        if self.data is not None:
            return len(self.data)
        if self.path:
            try:
                return Path(self.path).stat().st_size
            except OSError:
                return None
        return None

    def read_bytes(self) -> bytes:
        """Return the attachment's bytes, reading from disk once.

        The wire formatters replay the whole history every turn, so without
        this cache a 1 MB attached log would be re-read from disk on every
        subsequent send for the rest of the conversation. ``to_dict`` still
        serialises only the path, never the cached bytes.
        """
        if self.data is not None:
            return self.data
        if not self.path:
            raise ValueError(f"attachment {self.name!r} has neither data nor path")
        self.data = Path(self.path).read_bytes()
        return self.data

    def exists(self) -> bool:
        if self.data is not None:
            return True
        return bool(self.path) and Path(self.path).exists()

    def to_dict(self) -> dict:
        # Bytes are never serialised — only the reference.
        return {"media_type": self.media_type, "path": self.path, "name": self.name}

    @classmethod
    def from_dict(cls, raw: dict) -> "Attachment":
        return cls(
            media_type=raw.get("media_type", "application/octet-stream"),
            path=raw.get("path"),
            name=raw.get("name", ""),
        )


@dataclass
class ChatMessage:
    """One turn in a conversation."""

    role: Role
    content: str
    attachments: List[Attachment] = field(default_factory=list)
    created: str = field(default_factory=_now)
    provider: str = ""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    stop_reason: str = ""
    #: Non-empty when the turn failed or was cancelled. A failed turn is kept
    #: in history rather than dropped, so the transcript shows what happened
    #: instead of silently missing a reply.
    error: str = ""

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def is_partial(self) -> bool:
        """True for a turn that was cut short but still has usable text."""
        return bool(self.error) and bool(self.content)

    def to_dict(self) -> dict:
        out = {
            "role": self.role,
            "content": self.content,
            "created": self.created,
        }
        if self.attachments:
            out["attachments"] = [a.to_dict() for a in self.attachments]
        for key in ("provider", "model", "stop_reason", "error"):
            value = getattr(self, key)
            if value:
                out[key] = value
        if self.input_tokens or self.output_tokens:
            out["input_tokens"] = self.input_tokens
            out["output_tokens"] = self.output_tokens
        return out

    @classmethod
    def from_dict(cls, raw: dict) -> "ChatMessage":
        return cls(
            role=raw.get("role", "user"),
            content=raw.get("content", ""),
            attachments=[Attachment.from_dict(a) for a in raw.get("attachments", [])],
            created=raw.get("created", ""),
            provider=raw.get("provider", ""),
            model=raw.get("model", ""),
            input_tokens=int(raw.get("input_tokens", 0) or 0),
            output_tokens=int(raw.get("output_tokens", 0) or 0),
            stop_reason=raw.get("stop_reason", ""),
            error=raw.get("error", ""),
        )


@dataclass
class ChatSession:
    """A whole conversation, plus the settings it runs under."""

    id: str = field(default_factory=new_id)
    title: str = ""
    system_prompt: str = ""
    provider: str = ""
    model: str = ""
    messages: List[ChatMessage] = field(default_factory=list)
    created: str = field(default_factory=_now)
    modified: str = field(default_factory=_now)

    # ---- token accounting ------------------------------------------------

    @property
    def context_tokens(self) -> int:
        """Tokens currently occupying the model's context window.

        The most recent assistant turn's input + output. Because the full
        history is re-sent on every request, that single turn's input count
        already accounts for everything before it — so this is a lookup, not
        a sum. Summing would over-count roughly quadratically.
        """
        for msg in reversed(self.messages):
            if msg.role == "assistant" and msg.total_tokens:
                return msg.total_tokens
        return 0

    @property
    def billed_tokens(self) -> int:
        """Total tokens paid for across the session — this one *is* a sum."""
        return sum(m.total_tokens for m in self.messages)

    # ---- history ---------------------------------------------------------

    def add(self, message: ChatMessage) -> ChatMessage:
        self.messages.append(message)
        self.touch()
        return message

    def touch(self) -> None:
        self.modified = _now()

    @property
    def last_user_message(self) -> Optional[ChatMessage]:
        for msg in reversed(self.messages):
            if msg.role == "user":
                return msg
        return None

    def display_title(self) -> str:
        """A title for lists: the explicit one, else the opening question."""
        if self.title:
            return self.title
        first = next((m for m in self.messages if m.role == "user"), None)
        if first and first.content:
            text = " ".join(first.content.split())
            return text[:60] + ("…" if len(text) > 60 else "")
        return "New chat"

    # ---- serialisation ---------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "schema": SCHEMA_VERSION,
            "id": self.id,
            "title": self.title,
            "system_prompt": self.system_prompt,
            "provider": self.provider,
            "model": self.model,
            "created": self.created,
            "modified": self.modified,
            "messages": [m.to_dict() for m in self.messages],
        }

    @classmethod
    def from_dict(cls, raw: dict) -> "ChatSession":
        """Load a session, accepting both schema 2 and the original format.

        Schema 1 had no ``schema`` key and stored turns as description records
        with a ``prompt_style`` of ``user_question``/``ai_response``, plus
        ``compact_summary`` markers left by the Summarize & Compact command.
        Users have live saved chats in that shape, so dropping any of those
        three would silently lose history.
        """
        if raw.get("schema") == SCHEMA_VERSION or "messages" in raw:
            return cls(
                id=raw.get("id") or new_id(),
                title=raw.get("title", ""),
                system_prompt=raw.get("system_prompt", ""),
                provider=raw.get("provider", ""),
                model=raw.get("model", ""),
                created=raw.get("created", "") or _now(),
                modified=raw.get("modified", "") or _now(),
                messages=[ChatMessage.from_dict(m) for m in raw.get("messages", [])],
            )
        return cls._from_v1(raw)

    _V1_ROLES = {
        "user_question": "user",
        "ai_response": "assistant",
        "compact_summary": "system",
    }

    @classmethod
    def _from_v1(cls, raw: dict) -> "ChatSession":
        messages: List[ChatMessage] = []
        for entry in raw.get("descriptions", []):
            style = entry.get("prompt_style", "")
            role = cls._V1_ROLES.get(style)
            if role is None:
                continue
            usage = entry.get("token_usage") or {}
            messages.append(
                ChatMessage(
                    role=role,
                    content=entry.get("text", "") or entry.get("description", ""),
                    created=entry.get("created", "") or entry.get("timestamp", ""),
                    provider=entry.get("provider", ""),
                    model=entry.get("model", ""),
                    input_tokens=int(usage.get("input_tokens", 0) or 0),
                    output_tokens=int(usage.get("output_tokens", 0) or 0),
                )
            )
        return cls(
            id=raw.get("id") or raw.get("chat_id") or new_id(),
            title=raw.get("name", "") or raw.get("title", ""),
            provider=raw.get("provider", ""),
            model=raw.get("model", ""),
            created=raw.get("created", "") or _now(),
            modified=raw.get("modified", "") or _now(),
            messages=messages,
        )


def conversation_turns(messages: Sequence["ChatMessage"]) -> List["ChatMessage"]:
    """Only user/assistant turns, and only ones with something to say.

    Lives here rather than beside the providers that use it so that the MLX
    provider can reach it without importing the module that lazily imports
    *it* -- that pairing was a genuine import cycle, flagged by CodeQL.

    System turns are handled per-provider. A failed turn that produced no text
    is skipped: sending an empty assistant message makes some providers reject
    the whole request.
    """
    return [
        m
        for m in messages
        if m.role in ("user", "assistant") and (m.content or m.attachments)
    ]
