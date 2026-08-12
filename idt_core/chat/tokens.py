"""Token estimation and context-budget truncation.

Ported from ``ChatProcessingWorker._estimate_tokens`` /
``_truncate_to_token_budget`` in ``imagedescriber/workers_wx.py``, with three
changes:

1. It operates on :class:`ChatMessage` rather than raw dicts.
2. It consults :func:`idt_core.providers.registry.model_limits` first, so a
   200k-context Claude model is not treated as though it had the flat
   per-provider default. The old ``_CONTEXT_WINDOWS`` dict ignored the model
   entirely, and ignored the per-model metadata the UI was already reading.
3. **It reports what it dropped instead of printing it.** The original wrote
   ``print(f"[chat] Token budget: dropped ...")`` to stdout, which in a windowed
   build goes nowhere at all — so a conversation could silently lose its
   beginning with no way for the user to know.

The estimate is deliberately rough and biased high (1 token ≈ 4 characters,
1 000 tokens per image). Being wrong in the direction of sending less is
recoverable; being wrong the other way is an API error mid-conversation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from .messages import ChatMessage

#: Fallbacks used only when the registry has no recorded figure for the model.
#: Conservative on purpose.
DEFAULT_CONTEXT_WINDOWS = {
    "openai": 128_000,
    "claude": 200_000,
    "ollama": 32_768,
    "mlx": 32_768,
}

FALLBACK_CONTEXT_WINDOW = 32_768

#: Fraction of the window a conversation may occupy before turns are dropped.
#: The remainder is headroom for the reply itself.
DEFAULT_BUDGET_FRACTION = 0.80

CHARS_PER_TOKEN = 4
TOKENS_PER_IMAGE = 1_000


def context_window_for(provider: str, model: str = "") -> int:
    """Best known context window for a provider/model pair."""
    if model:
        try:
            from ..providers.registry import model_limits

            recorded, _ = model_limits(provider, model)
            if recorded:
                return recorded
        except ImportError:  # pragma: no cover - registry always ships
            pass
    return DEFAULT_CONTEXT_WINDOWS.get((provider or "").lower(), FALLBACK_CONTEXT_WINDOW)


def estimate_tokens(messages: Sequence[ChatMessage]) -> int:
    """Rough, deliberately high, token estimate for a conversation."""
    total = 0
    for msg in messages:
        total += max(1, len(msg.content) // CHARS_PER_TOKEN)
        for att in msg.attachments:
            if att.is_image:
                total += TOKENS_PER_IMAGE
    return total


@dataclass
class BudgetResult:
    """Outcome of fitting a conversation into its context window."""

    messages: List[ChatMessage]
    dropped: int
    estimated_before: int
    estimated_after: int
    limit: int

    @property
    def was_truncated(self) -> bool:
        return self.dropped > 0

    def describe(self) -> str:
        """A sentence fit for showing to a user or a screen reader."""
        if not self.was_truncated:
            return ""
        turns = "turn" if self.dropped == 1 else "turns"
        return (
            f"Dropped the {self.dropped} oldest {turns} to stay within the "
            f"model's context window ({self.estimated_after:,} of "
            f"{self.limit:,} estimated tokens)."
        )


def _has_image(msg: ChatMessage) -> bool:
    return any(a.is_image for a in msg.attachments)


def fit_to_budget(
    messages: Sequence[ChatMessage],
    provider: str,
    model: str = "",
    *,
    budget_fraction: float = DEFAULT_BUDGET_FRACTION,
    context_window: Optional[int] = None,
) -> BudgetResult:
    """Trim oldest history until the conversation fits the budget.

    Drop order, oldest first: text-only pairs, then individual leading
    text-only turns, then image-bearing pairs, then anything. The most recent
    message is never dropped — without it there is no question to answer.
    """
    limit = context_window or context_window_for(provider, model)
    target = int(limit * budget_fraction)
    before = estimate_tokens(messages)

    msgs = list(messages)
    if before <= target:
        return BudgetResult(msgs, 0, before, before, limit)

    # Phase 1 — oldest text-only pairs (a user turn and its reply).
    while len(msgs) > 2 and estimate_tokens(msgs) > target:
        if not _has_image(msgs[0]) and not _has_image(msgs[1]):
            msgs = msgs[2:]
        else:
            break

    # Phase 2 — individual leading text-only turns.
    while len(msgs) > 1 and estimate_tokens(msgs) > target:
        if not _has_image(msgs[0]):
            msgs = msgs[1:]
        else:
            break

    # Phase 3 — image-bearing pairs.
    while len(msgs) > 2 and estimate_tokens(msgs) > target:
        msgs = msgs[2:]

    # Phase 4 — last resort, down to the most recent message alone.
    while len(msgs) > 1 and estimate_tokens(msgs) > target:
        msgs = msgs[1:]

    after = estimate_tokens(msgs)
    return BudgetResult(msgs, len(messages) - len(msgs), before, after, limit)


def dedupe_attachments(messages: Sequence[ChatMessage]) -> List[ChatMessage]:
    """Keep only the first occurrence of each attachment path.

    Every request re-sends the whole history, so an image attached in turn one
    would otherwise be re-encoded and re-uploaded on every subsequent turn.
    The model has already seen it; the text of later turns is preserved.

    Returns new :class:`ChatMessage` objects where attachments were removed and
    the originals everywhere else, so callers' history is never mutated.
    """
    seen: set = set()
    result: List[ChatMessage] = []

    for msg in messages:
        if not msg.attachments:
            result.append(msg)
            continue

        kept = []
        for att in msg.attachments:
            key = att.path or att.name
            if key and key in seen:
                continue
            if key:
                seen.add(key)
            kept.append(att)

        if len(kept) == len(msg.attachments):
            result.append(msg)
        else:
            trimmed = ChatMessage(
                role=msg.role,
                content=msg.content,
                attachments=kept,
                created=msg.created,
                provider=msg.provider,
                model=msg.model,
                input_tokens=msg.input_tokens,
                output_tokens=msg.output_tokens,
                stop_reason=msg.stop_reason,
                error=msg.error,
            )
            result.append(trimmed)

    return result


def prepare_history(
    messages: Sequence[ChatMessage],
    provider: str,
    model: str = "",
    *,
    budget_fraction: float = DEFAULT_BUDGET_FRACTION,
) -> Tuple[List[ChatMessage], BudgetResult]:
    """Dedupe attachments, then fit to the context budget.

    Dedupe first: removing repeated images lowers the estimate, which can avoid
    dropping turns that would otherwise have to go.
    """
    deduped = dedupe_attachments(messages)
    result = fit_to_budget(
        deduped, provider, model, budget_fraction=budget_fraction
    )
    return result.messages, result
