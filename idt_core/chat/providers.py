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

from ..providers.base import (
    ChatDelta,
    ChatProvider,
    ChatRequest,
    ChatThinking,
    ChatToolCall,
    ChatToolResult,
    ChatUsage,
    ChatYield,
)
from .messages import Attachment, ChatMessage, conversation_turns

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


def encode_pdf_openai(att: Attachment) -> dict:
    """PDF as a ``file`` content part for the OpenAI chat completions API."""
    payload = base64.b64encode(att.read_bytes()).decode("utf-8")
    return {
        "type": "file",
        "file": {
            "filename": att.name or "document.pdf",
            "file_data": f"data:application/pdf;base64,{payload}",
        },
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


def format_for_ollama(
    messages: Sequence[ChatMessage], system_prompt: str = ""
) -> List[dict]:
    """Ollama takes the system prompt as a leading message with role=system."""
    out: List[dict] = []
    if system_prompt:
        out.append({"role": "system", "content": system_prompt})
    for msg in conversation_turns(messages):
        entry = {"role": msg.role, "content": merge_text_attachments(msg)}
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
    for msg in conversation_turns(messages):
        text = merge_text_attachments(msg)
        images = [a for a in msg.attachments if a.is_image]
        pdfs = [a for a in msg.attachments
                if a.media_type == "application/pdf"]
        if images or pdfs:
            content: List[dict] = [{"type": "text", "text": text}]
            content.extend(encode_image_openai(a) for a in images)
            content.extend(encode_pdf_openai(a) for a in pdfs)
            out.append({"role": msg.role, "content": content})
        else:
            out.append({"role": msg.role, "content": text})
    return out


def format_for_claude(
    messages: Sequence[ChatMessage], system_prompt: str = ""
) -> Tuple[str, List[dict]]:
    """Anthropic takes the system prompt as a **top-level parameter**.

    Returns ``(system, messages)``. This is the one provider where a system
    message must not be prepended to the list — doing so is an API error.
    Attachments come before the text in a content array, matching the previous
    implementation. Text attachments are inlined into the text block, never
    handed to :func:`encode_attachment_claude` — encoding a ``.txt`` as an
    image block would be an API error.
    """
    out: List[dict] = []
    for msg in conversation_turns(messages):
        text = merge_text_attachments(msg)
        uploads = [a for a in msg.attachments if not a.is_text]
        if uploads:
            content: List[dict] = [encode_attachment_claude(a) for a in uploads]
            content.append({"type": "text", "text": text})
            out.append({"role": msg.role, "content": content})
        else:
            out.append({"role": msg.role, "content": text})
    return system_prompt, out


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------


class OllamaChatProvider(ChatProvider):
    """Local or cloud Ollama. No API key."""

    #: Never request less than Ollama's own server-side default; asking for a
    #: smaller cache than the server would allocate anyway buys nothing.
    MIN_NUM_CTX = 4096
    #: Cap when the model's trained context length cannot be discovered.
    #: Matches the budgeter's flat Ollama default in tokens.py.
    FALLBACK_MAX_NUM_CTX = 32_768
    #: num_ctx is rounded up to a multiple of this so the KV cache is not
    #: reallocated on every turn as the conversation grows a few tokens.
    NUM_CTX_STEP = 2048
    #: Reply headroom when the caller did not set max_output_tokens.
    DEFAULT_REPLY_HEADROOM = 2048

    def __init__(self, model: str, host: Optional[str] = None):
        self._model = model
        self._host = host

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return self._model

    def _num_ctx(self, request: ChatRequest) -> int:
        """Context size to request for this turn.

        Without an explicit ``num_ctx`` the server applies its own default
        (4,096 on current builds) regardless of what the model supports, so
        long conversations were silently truncated server-side while the
        client-side budgeter believed 32k were available. Request what the
        conversation actually needs — estimated prompt plus reply headroom,
        rounded up — capped at the model's trained length. Asking for the full
        window on every turn would balloon KV-cache memory for no benefit on
        short chats.
        """
        from . import tokens as token_tools

        needed = token_tools.estimate_tokens(request.messages)
        needed += request.max_output_tokens or self.DEFAULT_REPLY_HEADROOM
        if request.tools:
            # Tool rounds append search results the estimate cannot see yet;
            # Ollama's own web-search guide recommends ~32k for search agents.
            needed = max(needed, self.FALLBACK_MAX_NUM_CTX)
        needed = -(-needed // self.NUM_CTX_STEP) * self.NUM_CTX_STEP

        try:
            from ..providers.ollama import model_context_length

            cap = model_context_length(
                request.model or self._model,
                **({"host": self._host} if self._host else {}),
            )
        except Exception:
            cap = None
        return min(cap or self.FALLBACK_MAX_NUM_CTX, max(self.MIN_NUM_CTX, needed))

    def _request_options(self, request: ChatRequest) -> dict:
        """The ``options`` dict for /api/chat.

        Before this existed, ``temperature`` and ``max_output_tokens`` were
        honoured by OpenAI and Claude but silently dropped for Ollama.
        """
        options = {"num_ctx": self._num_ctx(request)}
        if request.temperature is not None:
            options["temperature"] = request.temperature
        if request.max_output_tokens:
            options["num_predict"] = request.max_output_tokens
        return options

    #: Rounds of tool use before the model is made to answer with what it has.
    #: A search agent normally needs one or two; the bound exists so a model
    #: stuck re-searching cannot loop forever on the user's API quota.
    MAX_TOOL_ROUNDS = 5

    @staticmethod
    def _tool_call_fields(call) -> Tuple[str, dict]:
        """(name, arguments) from a tool call, tolerating both the SDK's
        object shape and plain dicts. Arguments may arrive as a JSON string."""
        if hasattr(call, "get"):
            function = call.get("function") or {}
        else:
            function = getattr(call, "function", None) or {}
        if hasattr(function, "get"):
            name = function.get("name") or ""
            arguments = function.get("arguments")
        else:
            name = getattr(function, "name", "") or ""
            arguments = getattr(function, "arguments", None)
        if isinstance(arguments, str):
            import json

            try:
                arguments = json.loads(arguments)
            except ValueError:
                arguments = {"raw": arguments}
        if not isinstance(arguments, dict):
            arguments = {}
        return name, arguments

    def _effective_think(self, request: ChatRequest):
        """The ``think`` parameter to send, or None to omit it.

        Auto mode (``request.think is None``) turns thinking separation on for
        models whose /api/show reports the capability, so their scratch work
        streams as :class:`ChatThinking` instead of landing inside the saved
        answer wrapped in ``<think>`` tags. Sending ``think`` to a model
        without the capability is an API error, hence omit — and unlike the
        picker probes this one fails CLOSED, because a wrong True breaks the
        turn while a wrong None merely leaves tags in the text.
        """
        if request.think is not None:
            return request.think
        try:
            from ..providers.ollama import model_capabilities

            caps = model_capabilities(
                request.model or self._model,
                **({"host": self._host} if self._host else {}),
            )
        except Exception:
            caps = None
        return True if caps and "thinking" in caps else None

    def chat(self, request: ChatRequest) -> Iterator[ChatYield]:
        import ollama

        client = ollama.Client(host=self._host) if self._host else ollama
        messages = format_for_ollama(request.messages, request.system_prompt)
        options = self._request_options(request)
        tools = list(request.tools) if request.tools and request.execute_tool else None
        think = self._effective_think(request)
        input_tokens = output_tokens = 0

        # Round 0 is the ordinary turn. When the model calls tools, their
        # results are appended as role=tool messages and the loop goes again;
        # the final iteration withholds the tools so the model must answer.
        for round_index in range(self.MAX_TOOL_ROUNDS + 1):
            offer_tools = tools if round_index < self.MAX_TOOL_ROUNDS else None
            kwargs = {
                "model": request.model or self._model,
                "messages": messages,
                "stream": True,
                "options": options,
            }
            if offer_tools:
                kwargs["tools"] = offer_tools
            if think is not None:
                kwargs["think"] = think

            stream = client.chat(**kwargs)
            text_parts: List[str] = []
            tool_calls: List = []
            try:
                for chunk in stream:
                    message = chunk.get("message") or {}
                    thinking = message.get("thinking")
                    if thinking:
                        yield ChatThinking(thinking)
                    text = message.get("content")
                    if text:
                        text_parts.append(text)
                        yield ChatDelta(text)
                    calls = message.get("tool_calls")
                    if calls:
                        tool_calls.extend(calls)
                    if chunk.get("done"):
                        # Sum across rounds: each is a separate model call.
                        input_tokens += chunk.get("prompt_eval_count") or 0
                        output_tokens += chunk.get("eval_count") or 0
            finally:
                close = getattr(stream, "close", None)
                if close:
                    close()

            if not tool_calls:
                break

            messages.append(
                {
                    "role": "assistant",
                    "content": "".join(text_parts),
                    "tool_calls": tool_calls,
                }
            )
            for call in tool_calls:
                name, arguments = self._tool_call_fields(call)
                yield ChatToolCall(name=name, arguments=arguments)
                try:
                    result = request.execute_tool(name, arguments)
                except Exception as exc:  # noqa: BLE001 - a tool must not fail the turn
                    result = f"Tool {name} failed: {exc}"
                from .tools import tool_result_summary

                yield ChatToolResult(name=name, summary=tool_result_summary(name, result))
                messages.append(
                    {"role": "tool", "content": result, "tool_name": name}
                )

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
