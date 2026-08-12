"""
Base provider interfaces.

Two ABCs live here, for two different shapes of work:

* :class:`BaseProvider` — one image, one prompt, one description. What the
  describe pipeline needs.
* :class:`ChatProvider` — a multi-turn conversation streamed back as it
  arrives. What chat needs.

They are deliberately parallel rather than one extending the other. Making
``BaseProvider`` abstract over chat would break all three concrete providers at
import time, and MLX has no clean ``describe(bytes, mime, prompt)`` form today
so it can implement chat only.

The intended endgame is that ``describe()`` becomes a one-turn ``chat()`` with
an image attachment and ``BaseProvider`` retires. Stating that here on purpose:
without a named endgame, "add a parallel interface" is how a codebase ends up
with several permanent ones.

Nothing here imports a vendor SDK — concrete implementations do that lazily.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterator, Optional, Sequence, Union


@dataclass
class DescriptionResult:
    text: str
    model: str
    provider: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None


class BaseProvider(ABC):
    @abstractmethod
    def describe(self, image_bytes: bytes, mime_type: str, prompt: str) -> DescriptionResult:
        """
        Send image_bytes to the AI and return a description.
        mime_type: e.g. "image/jpeg", "image/png"
        prompt: the user's instruction text
        """
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @property
    @abstractmethod
    def model_name(self) -> str: ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.model_name!r})"


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------


@dataclass
class ChatRequest:
    """Everything a provider needs to produce one assistant turn.

    ``messages`` is a list of ``idt_core.chat.messages.ChatMessage``. It is not
    imported here to keep this module free of a cycle — ``idt_core.chat``
    imports from ``idt_core.providers``, not the other way round.
    """

    messages: Sequence  # Sequence[ChatMessage]
    model: str
    system_prompt: str = ""
    max_output_tokens: Optional[int] = None
    temperature: Optional[float] = None


@dataclass
class ChatDelta:
    """A chunk of assistant text as it arrives."""

    text: str


@dataclass
class ChatUsage:
    """Token counts for the completed turn."""

    input_tokens: int = 0
    output_tokens: int = 0
    stop_reason: str = ""


#: What a provider's ``chat()`` generator yields.
ChatYield = Union[ChatDelta, ChatUsage]


class ChatProvider(ABC):
    """A conversational backend.

    ``chat()`` is a **synchronous generator**, and that is the load-bearing
    decision in this design:

    * A CLI consumes it directly::

          for item in provider.chat(request):
              ...

    * A wx GUI runs the same loop on a worker thread and marshals each item
      with ``wx.CallAfter``.
    * **Cancellation is free and correct.** The consumer breaks out of the loop
      or calls ``gen.close()``; a ``GeneratorExit`` is raised at the yield point
      and the provider's ``finally`` closes the HTTP stream. No cancellation
      flag to poll, no half-torn SDK state.

    Not asyncio: all three vendor SDKs offer synchronous streaming, wx has no
    safe event-loop integration on Windows worth the risk, and a second loop is
    another way for a frozen build to fail.

    Providers that cannot stream yield a single :class:`ChatDelta` containing
    the whole response, so consumers never branch on whether streaming is
    supported.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @property
    @abstractmethod
    def model_name(self) -> str: ...

    @abstractmethod
    def chat(self, request: ChatRequest) -> Iterator[ChatYield]:
        """Yield ChatDelta chunks, then at most one ChatUsage.

        Implementations must not swallow exceptions: the engine classifies and
        retries them. They must release network resources in a ``finally`` so
        that a consumer abandoning the generator does not leak a connection.
        """
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.model_name!r})"
