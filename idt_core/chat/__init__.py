"""Provider-agnostic chat engine.

Contains no UI code and imports no GUI toolkit, so the same engine backs the
``idt chat`` CLI command, the standalone chat application, and (eventually)
ImageDescriber's chat window.

Typical use::

    from idt_core.chat import ChatEngine, ChatSession, DirectoryChatStore
    from idt_core.chat.providers import create_chat_provider
    from idt_core.keys import resolve_api_key

    session = ChatSession(system_prompt="You are concise.")
    provider = create_chat_provider("claude", "claude-opus-5",
                                    resolve_api_key("claude"))
    engine = ChatEngine(session, provider, DirectoryChatStore())

    for event in engine.send("Hello"):
        ...

``providers`` is not imported here: it pulls in vendor SDKs lazily inside each
``chat()`` call, and importing it eagerly would make this package fail whenever
one SDK is missing.
"""
from .attachments import (
    AttachmentError,
    infer_media_type,
    prepare_attachment,
    prepare_attachments,
)
from .engine import ChatBusyError, ChatEngine, ChatOptions
from .errors import ChatError, ErrorKind, classify
from .events import (
    ChatCancelled,
    ChatDelta,
    ChatEvent,
    ChatFailed,
    ChatFinished,
    ChatRetrying,
    ChatStarted,
    ChatUsage,
    TERMINAL_EVENTS,
)
from .messages import SCHEMA_VERSION, Attachment, ChatMessage, ChatSession, Role, new_id
from .store import ChatStore, DirectoryChatStore, WorkspaceChatStore, default_chat_dir
from .tokens import BudgetResult, context_window_for, estimate_tokens, prepare_history

__all__ = [
    "Attachment",
    "AttachmentError",
    "BudgetResult",
    "ChatBusyError",
    "ChatCancelled",
    "ChatDelta",
    "ChatEngine",
    "ChatError",
    "ChatEvent",
    "ChatFailed",
    "ChatFinished",
    "ChatMessage",
    "ChatOptions",
    "ChatRetrying",
    "ChatSession",
    "ChatStarted",
    "ChatStore",
    "ChatUsage",
    "DirectoryChatStore",
    "ErrorKind",
    "Role",
    "SCHEMA_VERSION",
    "TERMINAL_EVENTS",
    "WorkspaceChatStore",
    "classify",
    "context_window_for",
    "default_chat_dir",
    "estimate_tokens",
    "infer_media_type",
    "new_id",
    "prepare_attachment",
    "prepare_attachments",
    "prepare_history",
]
