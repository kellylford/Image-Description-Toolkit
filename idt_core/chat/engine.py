"""The chat turn loop.

:meth:`ChatEngine.send` is a generator of :mod:`~idt_core.chat.events`. It owns
everything a provider should not have to: history assembly, the system prompt,
the token budget, retry on transient failures, persistence, and cancellation.
Providers stay thin — format, call, yield.

Threading contract, stated because getting it wrong is silent
------------------------------------------------------------
A :class:`ChatEngine` is **not thread-safe** and belongs to one thread at a
time. In a GUI the object can live on the UI thread while ``send()`` is
*iterated* on a worker; what must not happen is two turns in flight at once.
``send()`` raises :class:`ChatBusyError` rather than interleaving, because the
existing chat window has exactly that hole — ``on_send_message`` and
``on_summarize_compact`` both append to the same history with nothing stopping
them overlapping.

Cancellation
------------
Break out of the loop, or call ``gen.close()``. ``GeneratorExit`` is raised at
the yield point, the provider's ``finally`` closes the HTTP stream, and the
partial reply is saved to history. **A stopped response is kept, not
discarded** — the user watched it arrive, so throwing it away would be a
surprise. Note that a generator cannot yield during ``GeneratorExit``, so the
:class:`ChatCancelled` event is only delivered on the cooperative path
(:meth:`request_stop`); on ``close()`` the partial is still persisted.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Iterator, List, Optional, Sequence

from ..providers.base import ChatDelta as ProviderDelta
from ..providers.base import ChatProvider, ChatRequest
from ..providers.base import ChatUsage as ProviderUsage
from . import tokens as token_tools
from .errors import ChatError, classify
from .events import (
    ChatCancelled,
    ChatDelta,
    ChatEvent,
    ChatFailed,
    ChatFinished,
    ChatRetrying,
    ChatStarted,
    ChatUsage,
)
from .messages import Attachment, ChatMessage, ChatSession

__all__ = ["ChatEngine", "ChatOptions", "ChatBusyError"]


class ChatBusyError(RuntimeError):
    """Raised when a turn is started while one is already in flight."""


@dataclass
class ChatOptions:
    """Per-turn generation settings."""

    #: None means "ask the provider/registry", not "use 2048".
    max_output_tokens: Optional[int] = None
    temperature: Optional[float] = None
    #: Retries apply only to transient failures; see errors.RETRYABLE_KINDS.
    max_retries: int = 2
    retry_base_delay: float = 1.0
    budget_fraction: float = token_tools.DEFAULT_BUDGET_FRACTION
    #: Overrides the session's system prompt for this turn only.
    system_prompt: Optional[str] = None


@dataclass
class ChatEngine:
    """Drives one :class:`ChatSession` against one :class:`ChatProvider`."""

    session: ChatSession
    provider: ChatProvider
    store: object = None  # Optional[ChatStore]

    _busy: bool = field(default=False, init=False, repr=False)
    _stop_requested: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.session.provider:
            self.session.provider = self.provider.provider_name
        if not self.session.model:
            self.session.model = self.provider.model_name

    # ---- state -----------------------------------------------------------

    @property
    def is_busy(self) -> bool:
        return self._busy

    def request_stop(self) -> None:
        """Ask the in-flight turn to stop at the next chunk boundary.

        The cooperative counterpart to ``gen.close()``: this one can still emit
        a :class:`ChatCancelled` event, which ``close()`` cannot.
        """
        self._stop_requested = True

    def switch_provider(self, provider: ChatProvider) -> None:
        """Change provider/model mid-conversation, keeping history."""
        if self._busy:
            raise ChatBusyError("cannot switch provider while a turn is in flight")
        self.provider = provider
        self.session.provider = provider.provider_name
        self.session.model = provider.model_name
        self.session.touch()
        self._save()

    # ---- persistence -----------------------------------------------------

    def _save(self) -> None:
        if self.store is not None:
            self.store.save(self.session)

    # ---- the turn --------------------------------------------------------

    def send(
        self,
        text: str,
        attachments: Sequence[Attachment] = (),
        options: Optional[ChatOptions] = None,
    ) -> Iterator[ChatEvent]:
        """Send a user turn and stream the reply.

        The user turn is committed to history and persisted *before* the
        request goes out, so a crash or a failed call still leaves a record of
        what was asked.
        """
        if self._busy:
            raise ChatBusyError("a turn is already in flight")

        options = options or ChatOptions()
        self._busy = True
        self._stop_requested = False

        try:
            user_message = ChatMessage(
                role="user",
                content=text,
                attachments=list(attachments),
                provider=self.provider.provider_name,
                model=self.provider.model_name,
            )
            self.session.add(user_message)
            self._save()

            yield from self._run_turn(options)
        finally:
            self._busy = False
            self._stop_requested = False

    def continue_turn(self, options: Optional[ChatOptions] = None) -> Iterator[ChatEvent]:
        """Answer the history as it already stands, appending no user turn.

        For callers that maintain their own history and have already recorded
        the user's message — ImageDescriber's chat window persists the user turn
        to its workspace before sending, so :meth:`send` would duplicate it.
        """
        if self._busy:
            raise ChatBusyError("a turn is already in flight")
        if not self.session.messages:
            raise ValueError("nothing to answer: the conversation is empty")

        self._busy = True
        self._stop_requested = False
        try:
            yield from self._run_turn(options or ChatOptions())
        finally:
            self._busy = False
            self._stop_requested = False

    def regenerate(self, options: Optional[ChatOptions] = None) -> Iterator[ChatEvent]:
        """Drop the last assistant turn and answer the same question again."""
        if self._busy:
            raise ChatBusyError("a turn is already in flight")
        while self.session.messages and self.session.messages[-1].role == "assistant":
            self.session.messages.pop()
        if not self.session.messages:
            raise ValueError("nothing to regenerate: no user turn in this session")
        self._save()
        yield from self.continue_turn(options)

    # ---- internals -------------------------------------------------------

    def _system_prompt(self, options: ChatOptions) -> str:
        if options.system_prompt is not None:
            return options.system_prompt
        return self.session.system_prompt

    def _run_turn(self, options: ChatOptions) -> Iterator[ChatEvent]:
        history, budget = token_tools.prepare_history(
            self.session.messages,
            self.provider.provider_name,
            self.provider.model_name,
            budget_fraction=options.budget_fraction,
        )

        yield ChatStarted(
            provider=self.provider.provider_name,
            model=self.provider.model_name,
            sent_messages=len(history),
            dropped_messages=budget.dropped,
        )

        request = ChatRequest(
            messages=history,
            model=self.provider.model_name,
            system_prompt=self._system_prompt(options),
            max_output_tokens=options.max_output_tokens,
            temperature=options.temperature,
        )

        attempt = 0
        while True:
            attempt += 1
            chunks: List[str] = []
            usage: Optional[ProviderUsage] = None
            cancelled = False
            error: Optional[ChatError] = None

            stream = self.provider.chat(request)
            try:
                for item in stream:
                    if self._stop_requested:
                        cancelled = True
                        break
                    if isinstance(item, ProviderDelta):
                        if item.text:
                            chunks.append(item.text)
                            yield ChatDelta(item.text)
                    elif isinstance(item, ProviderUsage):
                        usage = item
            except GeneratorExit:
                # The consumer abandoned us. Persist what arrived, then let the
                # exception propagate -- yielding here is illegal.
                self._commit_assistant(
                    chunks, usage, error="Cancelled", stop_reason="cancelled"
                )
                stream.close()
                raise
            except BaseException as exc:  # noqa: BLE001 - classified below
                error = classify(exc)
            finally:
                close = getattr(stream, "close", None)
                if close:
                    close()

            if cancelled:
                message = self._commit_assistant(
                    chunks, usage, error="Cancelled", stop_reason="cancelled"
                )
                yield ChatCancelled(message)
                return

            if error is None:
                message = self._commit_assistant(chunks, usage)
                if usage is not None:
                    yield ChatUsage(
                        input_tokens=usage.input_tokens,
                        output_tokens=usage.output_tokens,
                    )
                yield ChatFinished(message)
                return

            # Failure. Retry only transient kinds, and only if nothing has been
            # emitted yet -- replaying a half-delivered answer would duplicate
            # text the user has already seen.
            can_retry = (
                error.retryable and attempt <= options.max_retries and not chunks
            )
            if can_retry:
                delay = options.retry_base_delay * (2 ** (attempt - 1))
                yield ChatRetrying(
                    error=error.user_message(), attempt=attempt, delay_seconds=delay
                )
                if delay:
                    time.sleep(delay)
                continue

            message = self._commit_assistant(
                chunks, usage, error=error.user_message(), stop_reason="error"
            )
            yield ChatFailed(
                error=error.user_message(),
                message=message,
                attempts=attempt,
                retryable=error.retryable,
            )
            return

    def _commit_assistant(
        self,
        chunks: Sequence[str],
        usage: Optional[ProviderUsage],
        error: str = "",
        stop_reason: str = "",
    ) -> ChatMessage:
        """Record the assistant turn and persist, even when it failed.

        A failed or stopped turn is kept in history with its error set, so the
        transcript shows what happened instead of a question with no answer.
        """
        message = ChatMessage(
            role="assistant",
            content="".join(chunks),
            provider=self.provider.provider_name,
            model=self.provider.model_name,
            input_tokens=usage.input_tokens if usage else 0,
            output_tokens=usage.output_tokens if usage else 0,
            stop_reason=(usage.stop_reason if usage and usage.stop_reason else stop_reason),
            error=error,
        )
        self.session.add(message)
        self._save()
        return message
