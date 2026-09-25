"""Chat with Apple Intelligence, on-device, through the local ``fm serve`` endpoint.

The wire format is OpenAI's, but the formatting is written here rather than
borrowed from ``providers.py``: that module lazily imports this one, and a
top-level import back would close the cycle CodeQL flagged when the Claude Code
provider did it (fixed in commit 5e813d3 by splitting out ``encoding.py``).

Streaming and cancellation work exactly as they do for the SDK-backed providers:
closing the generator closes the socket, and the partial reply is kept.
"""
from __future__ import annotations

import base64
from typing import Iterator, List, Optional, Sequence

from ..providers.apple import (
    CHAT_SYSTEM_PROMPT,
    DEFAULT_MODEL,
    AppleFMError,
    build_payload,
    check_ready,
    stream_chat,
)
from ..providers.base import ChatDelta, ChatProvider, ChatRequest, ChatUsage, ChatYield
from .encoding import merge_text_attachments
from .messages import Attachment, ChatMessage, conversation_turns

#: Images are sent as they are. Unlike the cloud providers there is no upload
#: limit to defend against — the server downscales before the model sees the
#: image, and resolution made no measurable difference to prompt tokens.
_SUPPORTED_IMAGE_MIMES = ("image/jpeg", "image/png")


def encode_image(att: Attachment) -> dict:
    """An ``image_url`` content part for one attachment.

    GIF and WebP are re-encoded to JPEG: only JPEG and PNG data URLs are
    verified against this endpoint, and a silent refusal mid-conversation is
    worse than a re-encode nobody sees.
    """
    raw = att.read_bytes()
    media_type = att.media_type
    if media_type not in _SUPPORTED_IMAGE_MIMES:
        try:
            import io

            from PIL import Image

            img = Image.open(io.BytesIO(raw))
            if img.mode != "RGB":
                img = img.convert("RGB")
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            raw, media_type = buf.getvalue(), "image/jpeg"
        except Exception:                                   # noqa: BLE001
            # Pillow missing or the image undecodable: send it as-is and let
            # the server have the final say, rather than failing the turn here.
            media_type = media_type or "image/jpeg"
    payload = base64.b64encode(raw).decode("utf-8")
    return {"type": "image_url",
            "image_url": {"url": f"data:{media_type};base64,{payload}"}}


def format_for_apple(
    messages: Sequence[ChatMessage], system_prompt: str = ""
) -> List[dict]:
    """The message list for one turn.

    A leading system message, then every turn. Turns carrying images become a
    content array; plain turns stay strings, matching what the OpenAI formatter
    does and keeping payloads small. Documents are dropped rather than sent:
    the on-device model takes images and text only, and a PDF encoded as an
    image part would fail the turn.
    """
    out: List[dict] = [{"role": "system", "content": system_prompt or CHAT_SYSTEM_PROMPT}]
    for msg in conversation_turns(messages):
        text = merge_text_attachments(msg)
        images = [a for a in msg.attachments if a.is_image]
        if images:
            content: List[dict] = [{"type": "text", "text": text}]
            content.extend(encode_image(a) for a in images)
            out.append({"role": msg.role, "content": content})
        else:
            out.append({"role": msg.role, "content": text})
    return out


class AppleChatProvider(ChatProvider):
    """Streaming chat on the local machine. Needs no API key; ``api_key`` is ignored."""

    def __init__(self, model: str = DEFAULT_MODEL, api_key: Optional[str] = None):
        self._model = model or DEFAULT_MODEL

    @property
    def provider_name(self) -> str:
        return "apple"

    @property
    def model_name(self) -> str:
        return self._model

    def chat(self, request: ChatRequest) -> Iterator[ChatYield]:
        check_ready()
        messages = format_for_apple(request.messages, request.system_prompt)
        if len(messages) <= 1:
            raise AppleFMError("Nothing to send: the conversation is empty.")

        payload = build_payload(
            messages, request.model or self._model, stream=True,
            max_output_tokens=request.max_output_tokens,
            temperature=request.temperature,
        )
        final: dict = {}
        stream = stream_chat(payload)
        try:
            for kind, value in stream:
                if kind == "delta":
                    yield ChatDelta(value)
                elif kind == "done":
                    final = value or {}
        finally:
            # Closing the generator closes the socket when the consumer
            # abandons this one (the user pressed Stop).
            stream.close()

        usage = final.get("usage") or {}
        yield ChatUsage(
            input_tokens=usage.get("prompt_tokens") or 0,
            output_tokens=usage.get("completion_tokens") or 0,
            stop_reason=final.get("finish_reason") or "",
        )
