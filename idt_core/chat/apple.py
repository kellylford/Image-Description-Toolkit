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

_SUPPORTED_IMAGE_MIMES = ("image/jpeg", "image/png")

#: Longest edge for an attached image, matching the OpenAI chat path.
#:
#: The describe path deliberately sends images untouched, because the server
#: downscales internally and one photo of any size goes through fine. Chat is
#: different: a turn can carry several attachments, and phone photos are 8-14 MB
#: each. Two of them closed the connection outright -- the server dropped the
#: request and the user saw an empty reply with "Broken pipe" behind it.
#: Measured 9/24/2026: two 8.5 MB + 14 MB photos failed; the same two at 1600px
#: (950 KB total) answered normally, as did three.
MAX_IMAGE_DIM = 1600
JPEG_QUALITY = 85


def encode_image(att: Attachment) -> dict:
    """An ``image_url`` content part for one attachment, downscaled to fit.

    Two things happen here, both for the same reason -- a turn that fails is
    worse than one that loses pixels nobody was going to see:

    * Anything larger than :data:`MAX_IMAGE_DIM` on its longest edge is resized.
      Full-size phone photos are megabytes each and several of them in one turn
      break the request (see the note on that constant).
    * GIF and WebP are re-encoded to JPEG, because only JPEG and PNG data URLs
      are verified against this endpoint.

    If Pillow is missing or the image will not decode, the original bytes go as
    they are: the server refusing is a clearer failure than this function
    raising one the user cannot act on.
    """
    raw = att.read_bytes()
    media_type = att.media_type or "image/jpeg"
    try:
        import io

        from PIL import Image

        img = Image.open(io.BytesIO(raw))
        oversized = max(img.size) > MAX_IMAGE_DIM
        if oversized or media_type not in _SUPPORTED_IMAGE_MIMES:
            if img.mode != "RGB":
                img = img.convert("RGB")
            if oversized:
                img.thumbnail((MAX_IMAGE_DIM, MAX_IMAGE_DIM), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=JPEG_QUALITY)
            raw, media_type = buf.getvalue(), "image/jpeg"
    except Exception:                                       # noqa: BLE001
        pass
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
