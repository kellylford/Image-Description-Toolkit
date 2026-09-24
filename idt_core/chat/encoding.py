"""Attachment encoding shared by several chat providers.

Split out of ``providers.py`` so that provider modules which ``providers.py``
itself imports lazily (``claude_code``, ``mlx``) can use these without an
import cycle -- the same reason ``conversation_turns`` lives in ``messages``.
``providers.py`` re-exports both names, so existing imports keep working.
"""
from __future__ import annotations

import base64

from .messages import Attachment, ChatMessage


def encode_attachment_claude(att: Attachment) -> dict:
    """Image or document content block for the Anthropic messages API."""
    payload = base64.b64encode(att.read_bytes()).decode("utf-8")
    if att.media_type == "application/pdf":
        return {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": payload,
            },
        }
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": att.media_type, "data": payload},
    }


def merge_text_attachments(msg: ChatMessage) -> str:
    """The turn's text with any text attachments inlined after it.

    This is how a ``.txt``/``.md``/code attachment reaches the model on every
    provider — as a longer prompt, never as an upload. It therefore works with
    text-only models too. A file that has gone missing since it was attached
    becomes a note rather than a failed turn: the conversation history may be
    replayed long after the file was deleted.
    """
    texts = [a for a in msg.attachments if a.is_text]
    if not texts:
        return msg.content

    parts = [msg.content] if msg.content else []
    for att in texts:
        try:
            body = att.read_bytes().decode("utf-8", errors="replace")
        except (OSError, ValueError):
            parts.append(f"[Attached file {att.name} is no longer available.]")
            continue
        parts.append(f"[Attached file: {att.name}]\n{body}")
    return "\n\n".join(parts)
