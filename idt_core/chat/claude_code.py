"""Chat through the ``claude`` CLI, billed to the user's Claude subscription.

Each turn is one ``claude -p`` run with no saved session, so the engine stays
the owner of the conversation — edits, retries and compaction behave exactly
as they do for the API providers.

The CLI cannot be handed prior assistant turns: in ``--input-format
stream-json`` every user line is answered as a new turn and assistant lines
are ignored (verified against Claude Code 2.1). So earlier turns travel as a
labelled transcript inside one user message, with a system-prompt note saying
so. The API providers resend the whole history every turn too; this sends the
same content in a different wrapper, not more of it.

Chat tools (web search) are not offered: they are executed by the engine
through provider-native tool calls, and the CLI's own tool loop has no way to
call back into this process.
"""
from __future__ import annotations

from typing import Iterator, List, Optional, Sequence

from ..providers.base import ChatDelta, ChatProvider, ChatRequest, ChatUsage, ChatYield
from ..providers.claude_code import (
    CHAT_SYSTEM_PROMPT,
    ClaudeCodeError,
    DEFAULT_MODEL,
    check_subscription,
    find_claude,
    result_error,
    run_claude,
    usage_tokens,
)
from .messages import ChatMessage, conversation_turns

#: Appended to the system prompt whenever earlier turns are sent as a transcript.
TRANSCRIPT_NOTE = (
    "Earlier turns of this conversation are included in the user's message as "
    "a transcript, each turn labelled 'User:' or 'Assistant:'. Continue the "
    "conversation as the assistant: reply only to the final User turn, and do "
    "not start your reply with a label."
)


def _turn_blocks(msg: ChatMessage, label: Optional[str]) -> List[dict]:
    """Content blocks for one turn: uploads first, then its text."""
    # Imported here: providers.py lazily imports this module, so importing it
    # at module scope would be a cycle.
    from .providers import encode_attachment_claude, merge_text_attachments

    blocks = [encode_attachment_claude(a) for a in msg.attachments if not a.is_text]
    text = merge_text_attachments(msg)
    if label:
        text = f"{label}:\n{text}" if text else f"{label}: (attachment only)"
    if text:
        blocks.append({"type": "text", "text": text})
    return blocks


def format_for_claude_code(
    messages: Sequence[ChatMessage], system_prompt: str = ""
) -> tuple:
    """Return ``(system_prompt, content_blocks)`` for one CLI run.

    A conversation of a single user turn is sent as-is. Anything longer
    becomes a transcript: every turn labelled, attachments kept with the turn
    they belong to, and the note explaining the format added to the system
    prompt.
    """
    turns = conversation_turns(messages)
    system = system_prompt or CHAT_SYSTEM_PROMPT
    if len(turns) <= 1:
        blocks: List[dict] = []
        for msg in turns:
            blocks.extend(_turn_blocks(msg, None))
        return system, blocks

    blocks = []
    for msg in turns:
        blocks.extend(_turn_blocks(msg, "User" if msg.role == "user" else "Assistant"))
    return f"{system}\n\n{TRANSCRIPT_NOTE}", blocks


class ClaudeCodeChatProvider(ChatProvider):
    """Streaming chat via Claude Code. Needs no API key; ``api_key`` is ignored."""

    def __init__(self, model: str = DEFAULT_MODEL, api_key: Optional[str] = None):
        self._model = model or DEFAULT_MODEL

    @property
    def provider_name(self) -> str:
        return "claude-code"

    @property
    def model_name(self) -> str:
        return self._model

    def chat(self, request: ChatRequest) -> Iterator[ChatYield]:
        claude = find_claude()
        check_subscription(claude)
        system, blocks = format_for_claude_code(request.messages, request.system_prompt)
        if not blocks:
            raise ClaudeCodeError("Nothing to send: the conversation is empty.")

        result = None
        runner = run_claude(
            blocks, request.model or self._model, system,
            partial=True, max_output_tokens=request.max_output_tokens, claude=claude,
        )
        try:
            for kind, value in runner:
                if kind == "delta":
                    yield ChatDelta(value)
                elif kind == "result":
                    result = value
        finally:
            # Closing the runner kills the CLI process when the consumer
            # abandons this generator (the user pressed Stop).
            runner.close()

        error = result_error(result)
        if error:
            raise ClaudeCodeError(error)
        input_tokens, output_tokens = usage_tokens(result)
        yield ChatUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            stop_reason=result.get("stop_reason") or "",
        )
