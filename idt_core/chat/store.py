"""Where conversations are saved.

Two backends, one schema:

* :class:`DirectoryChatStore` — ``~/.idt/chats/<id>.json``. What the standalone
  chat app uses.
* :class:`WorkspaceChatStore` — the ``chats/`` directory inside a ``.idtw``
  bundle, via the ``save_chat``/``chats``/``delete_chat`` methods that
  ``idt_core/workspace.py`` has had all along.

The schema being identical is the point: a conversation started in the
standalone app can be dropped into a bundle's ``chats/`` directory and opened
in ImageDescriber, and vice versa. Nothing needs converting.

Writes go through a temp file and ``os.replace``, so a crash mid-write leaves
the previous conversation intact rather than a truncated one.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Optional, Protocol, runtime_checkable

from .messages import ChatSession

__all__ = [
    "ChatStore",
    "DirectoryChatStore",
    "WorkspaceChatStore",
    "default_chat_dir",
]


@runtime_checkable
class ChatStore(Protocol):
    """Persistence for chat sessions."""

    def save(self, session: ChatSession) -> None: ...

    def load(self, session_id: str) -> Optional[ChatSession]: ...

    def list_sessions(self) -> List[ChatSession]: ...

    def delete(self, session_id: str) -> bool: ...


def default_chat_dir() -> Path:
    """``~/.idt/chats``, alongside the existing ``~/.idt/config.json``."""
    return Path.home() / ".idt" / "chats"


def _atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    os.replace(tmp, path)


class DirectoryChatStore:
    """One JSON file per conversation in a directory."""

    def __init__(self, directory: Optional[Path] = None):
        self.directory = Path(directory) if directory else default_chat_dir()

    def _path(self, session_id: str) -> Path:
        """Map a session id to its file, rejecting anything unexpected.

        Validate rather than sanitise. Stripping the offending characters would
        quietly turn ``../../etc/passwd`` into ``etcpasswd.json`` -- safe, but
        it would read or overwrite a *different* conversation than the caller
        named, which is its own kind of bug. Generated ids are ``chat_<hex>``,
        so anything outside this set means the caller has a problem worth
        hearing about.
        """
        if not session_id or not all(
            c.isalnum() or c in "-_" for c in session_id
        ):
            raise ValueError(
                f"invalid session id {session_id!r}: expected letters, digits, "
                "hyphen or underscore only"
            )
        return self.directory / f"{session_id}.json"

    def save(self, session: ChatSession) -> None:
        session.touch()
        _atomic_write_json(self._path(session.id), session.to_dict())

    def load(self, session_id: str) -> Optional[ChatSession]:
        path = self._path(session_id)
        if not path.is_file():
            return None
        return self._read(path)

    @staticmethod
    def _read(path: Path) -> Optional[ChatSession]:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(raw, dict):
            return None
        return ChatSession.from_dict(raw)

    def list_sessions(self) -> List[ChatSession]:
        """Every readable session, most recently modified first.

        Unreadable files are skipped rather than raised: one corrupt file
        should not make the conversation list unopenable.
        """
        if not self.directory.is_dir():
            return []
        sessions = []
        for path in self.directory.glob("*.json"):
            session = self._read(path)
            if session is not None:
                sessions.append(session)
        sessions.sort(key=lambda s: s.modified or "", reverse=True)
        return sessions

    def delete(self, session_id: str) -> bool:
        path = self._path(session_id)
        try:
            path.unlink()
            return True
        except FileNotFoundError:
            return False


class WorkspaceChatStore:
    """Chats inside a ``.idtw`` bundle.

    Wraps the workspace API rather than writing into ``chats/`` directly, so
    the bundle keeps control of its own layout and atomic-write behaviour.
    """

    def __init__(self, workspace):
        self.workspace = workspace

    def save(self, session: ChatSession) -> None:
        session.touch()
        self.workspace.save_chat(session.to_dict())

    def load(self, session_id: str) -> Optional[ChatSession]:
        for raw in self.workspace.chats():
            if raw.get("id") == session_id or raw.get("chat_id") == session_id:
                return ChatSession.from_dict(raw)
        return None

    def list_sessions(self) -> List[ChatSession]:
        sessions = [ChatSession.from_dict(raw) for raw in self.workspace.chats()]
        sessions.sort(key=lambda s: s.modified or "", reverse=True)
        return sessions

    def delete(self, session_id: str) -> bool:
        result = self.workspace.delete_chat(session_id)
        # delete_chat predates this store and may return None on success.
        return True if result is None else bool(result)
