"""Concrete :class:`ChatProvider` implementations.

Ported from the four ``_chat_with_*`` methods of ``ChatProcessingWorker`` in
``imagedescriber/workers_wx.py``, which spoke to the vendor SDKs inline from a
wx worker thread. The wire formats here match that code so existing
conversations keep behaving the same way.

The structure differs in one deliberate respect: **message formatting is
separated from the network call.** ``format_for_openai`` and friends are pure
functions over :class:`ChatMessage`, so the part that is easy to get subtly
wrong — role mapping, attachment blocks, where the system prompt goes — is
directly testable without an API key or a network. The provider classes are
then thin wrappers that format, call, and yield.

Every ``chat()`` closes its stream in a ``finally``, so a consumer that
abandons the generator (the user pressing Stop) does not leak a connection.
"""
from __future__ import annotations

import base64
import io
from typing import Iterator, List, Optional, Sequence, Tuple

from ..providers.base import ChatDelta, ChatProvider, ChatRequest, ChatUsage, ChatYield
from .messages import Attachment, ChatMessage

#: OpenAI images are resized to this longest edge before upload, matching the
#: batch describe path in imagedescriber/ai_providers.py.
OPENAI_MAX_IMAGE_DIM = 1600
OPENAI_JPEG_QUALITY = 85


# ---------------------------------------------------------------------------
# Attachment encoding
# ---------------------------------------------------------------------------


def encode_image_ollama(att: Attachment) -> str:
    """Base64 for Ollama's ``images`` list."""
    return base64.b64encode(att.read_bytes()).decode("utf-8")


def encode_image_openai(att: Attachment) -> dict:
    """Resized base64 JPEG data-URL block for the OpenAI chat completions API.

    Falls back to the raw bytes if Pillow is unavailable or the image cannot be
    decoded — sending something oversized beats failing the turn.
    """
    raw = att.read_bytes()
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(raw))
        if img.mode != "RGB":
            img = img.convert("RGB")
        if max(img.size) > OPENAI_MAX_IMAGE_DIM:
            ratio = OPENAI_MAX_IMAGE_DIM / max(img.size)
            img = img.resize(
                (int(img.width * ratio), int(img.height * ratio)),
                Image.Resampling.LANCZOS,
            )
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=OPENAI_JPEG_QUALITY)
        payload = base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception:
        payload = base64.b64encode(raw).decode("utf-8")
    return {
        "type": "image_url",
        "image_url": {"url": f"data:image/jpeg;base64,{payload}"},
    }


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


# ---------------------------------------------------------------------------
# Message formatting — pure, and therefore testable
# ---------------------------------------------------------------------------


def _conversation_turns(messages: Sequence[ChatMessage]) -> List[ChatMessage]:
    """Only user/assistant turns, and only ones with something to say.

    System turns are handled per-provider. A failed turn that produced no text
    is skipped: sending an empty assistant message makes some providers reject
    the whole request.
    """
    return [
        m
        for m in messages
        if m.role in ("user", "assistant") and (m.content or m.attachments)
    ]


def format_for_ollama(
    messages: Sequence[ChatMessage], system_prompt: str = ""
) -> List[dict]:
    """Ollama takes the system prompt as a leading message with role=system."""
    out: List[dict] = []
    if system_prompt:
        out.append({"role": "system", "content": system_prompt})
    for msg in _conversation_turns(messages):
        entry = {"role": msg.role, "content": msg.content}
        images = [a for a in msg.attachments if a.is_image]
        if images:
            entry["images"] = [encode_image_ollama(a) for a in images]
        out.append(entry)
    return out


def format_for_openai(
    messages: Sequence[ChatMessage], system_prompt: str = ""
) -> List[dict]:
    """OpenAI also takes a leading system message.

    Turns carrying images become a content array; plain turns stay strings,
    which is what the API expects and what keeps payloads small.
    """
    out: List[dict] = []
    if system_prompt:
        out.append({"role": "system", "content": system_prompt})
    for msg in _conversation_turns(messages):
        images = [a for a in msg.attachments if a.is_image]
        if images:
            content: List[dict] = [{"type": "text", "text": msg.content}]
            content.extend(encode_image_openai(a) for a in images)
            out.append({"role": msg.role, "content": content})
        else:
            out.append({"role": msg.role, "content": msg.content})
    return out


def format_for_claude(
    messages: Sequence[ChatMessage], system_prompt: str = ""
) -> Tuple[str, List[dict]]:
    """Anthropic takes the system prompt as a **top-level parameter**.

    Returns ``(system, messages)``. This is the one provider where a system
    message must not be prepended to the list — doing so is an API error.
    Attachments come before the text in a content array, matching the previous
    implementation.
    """
    out: List[dict] = []
    for msg in _conversation_turns(messages):
        if msg.attachments:
            content: List[dict] = [encode_attachment_claude(a) for a in msg.attachments]
            content.append({"type": "text", "text": msg.content})
            out.append({"role": msg.role, "content": content})
        else:
            out.append({"role": msg.role, "content": msg.content})
    return system_prompt, out


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------


class OllamaChatProvider(ChatProvider):
    """Local or cloud Ollama. No API key."""

    def __init__(self, model: str, host: Optional[str] = None):
        self._model = model
        self._host = host

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return self._model

    def chat(self, request: ChatRequest) -> Iterator[ChatYield]:
        import ollama

        client = ollama.Client(host=self._host) if self._host else ollama
        stream = client.chat(
            model=request.model or self._model,
            messages=format_for_ollama(request.messages, request.system_prompt),
            stream=True,
        )
        input_tokens = output_tokens = 0
        try:
            for chunk in stream:
                message = chunk.get("message") or {}
                text = message.get("content")
                if text:
                    yield ChatDelta(text)
                if chunk.get("done"):
                    input_tokens = chunk.get("prompt_eval_count") or 0
                    output_tokens = chunk.get("eval_count") or 0
        finally:
            close = getattr(stream, "close", None)
            if close:
                close()
        if input_tokens or output_tokens:
            yield ChatUsage(input_tokens=input_tokens, output_tokens=output_tokens)


class OpenAIChatProvider(ChatProvider):
    def __init__(self, model: str, api_key: Optional[str] = None):
        self._model = model
        self._api_key = api_key

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model

    def chat(self, request: ChatRequest) -> Iterator[ChatYield]:
        import openai

        client = (
            openai.OpenAI(api_key=self._api_key) if self._api_key else openai.OpenAI()
        )
        kwargs = {
            "model": request.model or self._model,
            "messages": format_for_openai(request.messages, request.system_prompt),
            "stream": True,
            # Without this the final chunk carries no usage and token counts
            # are simply unavailable.
            "stream_options": {"include_usage": True},
        }
        if request.max_output_tokens:
            kwargs["max_completion_tokens"] = request.max_output_tokens
        if request.temperature is not None:
            kwargs["temperature"] = request.temperature

        stream = client.chat.completions.create(**kwargs)
        usage = None
        try:
            for chunk in stream:
                if chunk.choices:
                    text = chunk.choices[0].delta.content
                    if text:
                        yield ChatDelta(text)
                if getattr(chunk, "usage", None) is not None:
                    usage = chunk.usage
        finally:
            close = getattr(stream, "close", None)
            if close:
                close()
        if usage is not None:
            yield ChatUsage(
                input_tokens=usage.prompt_tokens or 0,
                output_tokens=usage.completion_tokens or 0,
            )


class ClaudeChatProvider(ChatProvider):
    #: Used only when neither the caller nor the model metadata supplies one.
    #: The previous implementation hard-coded 2048 for every Claude model,
    #: silently truncating replies on models that support far more.
    FALLBACK_MAX_OUTPUT = 4096

    def __init__(self, model: str, api_key: Optional[str] = None):
        self._model = model
        self._api_key = api_key

    @property
    def provider_name(self) -> str:
        return "claude"

    @property
    def model_name(self) -> str:
        return self._model

    def _max_output(self, request: ChatRequest) -> int:
        if request.max_output_tokens:
            return request.max_output_tokens
        try:
            from ..providers.registry import model_limits

            _, recorded = model_limits("claude", request.model or self._model)
            if recorded:
                return recorded
        except ImportError:  # pragma: no cover
            pass
        return self.FALLBACK_MAX_OUTPUT

    def chat(self, request: ChatRequest) -> Iterator[ChatYield]:
        import anthropic

        client = (
            anthropic.Anthropic(api_key=self._api_key)
            if self._api_key
            else anthropic.Anthropic()
        )
        system, messages = format_for_claude(request.messages, request.system_prompt)

        kwargs = {
            "model": request.model or self._model,
            "max_tokens": self._max_output(request),
            "messages": messages,
        }
        if system:
            kwargs["system"] = system
        if request.temperature is not None:
            kwargs["temperature"] = request.temperature

        final = None
        with client.messages.stream(**kwargs) as stream:
            for text in stream.text_stream:
                if text:
                    yield ChatDelta(text)
            final = stream.get_final_message()

        if final is not None:
            yield ChatUsage(
                input_tokens=final.usage.input_tokens or 0,
                output_tokens=final.usage.output_tokens or 0,
                stop_reason=getattr(final, "stop_reason", "") or "",
            )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_PROVIDERS = {
    "ollama": OllamaChatProvider,
    "openai": OpenAIChatProvider,
    "claude": ClaudeChatProvider,
    # MLX is resolved lazily in create_chat_provider: importing it here
    # would be harmless but pointless on the platforms it cannot run on.
}


def create_chat_provider(
    provider: str, model: str, api_key: Optional[str] = None
) -> ChatProvider:
    """Build a chat provider by name.

    Resolves aliases through the capability registry, so ``anthropic`` and
    ``Claude`` both work.
    """
    from ..providers.registry import capabilities_for

    canonical = capabilities_for(provider).provider
    if canonical == "unknown":
        canonical = (provider or "").strip().lower()

    if canonical == "mlx":
        # Imported here rather than at module scope so that the macOS-only
        # code never loads on a platform that cannot run it.
        from .mlx import MLXChatProvider

        return MLXChatProvider(model)

    factory = _PROVIDERS.get(canonical)
    if factory is None:
        known = ", ".join(sorted(list(_PROVIDERS) + ["mlx"]))
        raise ValueError(f"unknown chat provider {provider!r}; known: {known}")

    if canonical == "ollama":
        return factory(model)
    return factory(model, api_key)
