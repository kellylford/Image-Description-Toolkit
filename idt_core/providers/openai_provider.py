"""
OpenAI provider (GPT-4o, GPT-4o-mini, o1).
Reads OPENAI_API_KEY from the environment.
"""
from __future__ import annotations

import base64
import re
from typing import Iterable, List, Optional, Sequence

from .base import BaseProvider, DescriptionResult

# The list below is no longer the source of truth for *which* models exist --
# `catalog.py` asks the API that, and this list is the offline fallback plus the
# metadata layer (issue #267). It is still the source of truth for
# context_window / max_output / cost / recommended, and for display order.
#
# Updated July 2026.
DEFAULT_MODEL = "gpt-5.2"

OPENAI_MODELS = [
    # Current generation — GPT-5.x
    "gpt-5.2", "gpt-5.1", "gpt-5", "gpt-5-mini", "gpt-5-nano",
    # Reasoning models
    "o4-mini", "o3",
    # Legacy (still functional, users may have old descriptions referencing them)
    "gpt-4o", "gpt-4o-mini",
    "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano",
    "o1",
]

# context_window / max_output are the platform-documented figures. They feed
# the chat token budgeter and the context gauge; before they were recorded,
# registry.model_limits() returned (None, None) for every OpenAI model and
# budgeting fell back to a flat 128k guess regardless of model.
OPENAI_MODEL_METADATA: dict = {
    # --- GPT-5.x --- (400k context, 128k max output across the family)
    "gpt-5.2": {"name": "GPT-5.2", "description": "Best available model — highest quality vision and reasoning.", "cost": "$$$$", "supports_vision": True, "recommended": True,
                "context_window": 400_000, "max_output": 128_000},
    "gpt-5.1": {"name": "GPT-5.1", "description": "High-quality GPT-5 with strong reasoning.", "cost": "$$$", "supports_vision": True, "recommended": False,
                "context_window": 400_000, "max_output": 128_000},
    "gpt-5": {"name": "GPT-5", "description": "Flagship GPT-5 reasoning model.", "cost": "$$$", "supports_vision": True, "recommended": False,
              "context_window": 400_000, "max_output": 128_000},
    "gpt-5-mini": {"name": "GPT-5 Mini", "description": "Faster, efficient GPT-5.", "cost": "$$", "supports_vision": True, "recommended": False,
                   "context_window": 400_000, "max_output": 128_000},
    "gpt-5-nano": {"name": "GPT-5 Nano", "description": "Fastest and most affordable GPT-5.", "cost": "$", "supports_vision": True, "recommended": False,
                   "context_window": 400_000, "max_output": 128_000},
    # --- Reasoning models ---
    "o4-mini": {"name": "O4 Mini", "description": "Fast cost-efficient reasoning.", "cost": "$$", "supports_vision": True, "recommended": False,
                "context_window": 200_000, "max_output": 100_000},
    "o3": {"name": "O3", "description": "Powerful reasoning for complex tasks.", "cost": "$$$", "supports_vision": True, "recommended": False,
           "context_window": 200_000, "max_output": 100_000},
    # --- Legacy (still functional) ---
    "gpt-4o": {"name": "GPT-4o", "description": "Legacy — still works well for vision tasks.", "cost": "$$", "supports_vision": True, "recommended": False,
               "context_window": 128_000, "max_output": 16_384},
    "gpt-4o-mini": {"name": "GPT-4o Mini", "description": "Legacy — affordable and fast.", "cost": "$", "supports_vision": True, "recommended": False,
                    "context_window": 128_000, "max_output": 16_384},
    "gpt-4.1": {"name": "GPT-4.1", "description": "Legacy — last non-reasoning GPT-4 generation.", "cost": "$$", "supports_vision": True, "recommended": False,
                "context_window": 1_047_576, "max_output": 32_768},
    "gpt-4.1-mini": {"name": "GPT-4.1 Mini", "description": "Legacy — compact GPT-4.1.", "cost": "$", "supports_vision": True, "recommended": False,
                     "context_window": 1_047_576, "max_output": 32_768},
    "gpt-4.1-nano": {"name": "GPT-4.1 Nano", "description": "Legacy — ultra-budget GPT-4.1.", "cost": "$", "supports_vision": True, "recommended": False,
                     "context_window": 1_047_576, "max_output": 32_768},
    "o1": {"name": "O1", "description": "Legacy — original full reasoning model.", "cost": "$$$", "supports_vision": True, "recommended": False,
           "context_window": 200_000, "max_output": 100_000},
}


def get_openai_model_info(model_id: str) -> dict:
    return OPENAI_MODEL_METADATA.get(model_id, {"name": model_id, "supports_vision": True})


# ---------------------------------------------------------------------------
# Live listing
# ---------------------------------------------------------------------------
#
# `GET /v1/models` returns everything the account can reach -- around eighty
# entries, most of which are not chat models at all, plus a dated snapshot
# alongside nearly every base id. Dropping a picker of that size in front of
# someone arrowing through it with a screen reader would be worse than the stale
# list this replaces, so the response is filtered before it is offered.

#: Whole tokens that mean "not a chat model". Matched against the id split on
#: `-` and `.`, never as substrings: a substring test for "audio" or "image"
#: would drop a future `gpt-6-audio-native` flagship, which is precisely the
#: kind of silent omission issue #267 exists to fix. `idt models --all` shows
#: everything when this filter is wrong.
#
# "vision" is deliberately absent from this set: `gpt-4-vision-preview` is a
# chat model, and for an image-description app it is one of the last ones we
# would want to hide.
_NON_CHAT_TOKENS = frozenset({
    "embedding", "embeddings", "similarity",
    "tts", "whisper", "transcribe", "audio", "realtime", "voice",
    "dall", "image", "sora", "moderation",
    "davinci", "babbage", "curie", "ada", "instruct",
})
# "search", "codex", "pro", "chat" and "deep" are all deliberately absent:
# `gpt-4o-search-preview`, `gpt-5.3-codex`, `gpt-5-pro`, `gpt-5-chat-latest` and
# `o4-mini-deep-research` all answer chat completions perfectly well. Verified
# against a real account listing (126 ids in, 47 out) rather than guessed --
# every one of those would have been a model the user could call and IDT would
# not have offered.

#: A trailing release date: `-2024-08-06` or `-20240806`.
_DATED = re.compile(r"^(?P<base>.+?)-(?P<date>\d{4}-\d{2}-\d{2}|\d{8})$")

#: A trailing four-digit MMDD snapshot: `gpt-4-0613`, `gpt-3.5-turbo-0125`.
#: Handled more cautiously than a full date -- four digits are ambiguous enough
#: that a future `gpt-5-1000` could match -- so this form only ever *collapses*
#: into an existing base id and never drives the "keep the newest" branch.
_SHORT_DATED = re.compile(r"^(?P<base>.+?)-(?P<date>\d{4})$")


def _normalise_date(value: str) -> str:
    """`20240806` -> `2024-08-06`, so both spellings sort and group together.

    Without this, one family spelled both ways becomes two groups and the
    collapse silently does nothing for it.
    """
    if len(value) == 8 and value.isdigit():
        return f"{value[:4]}-{value[4:6]}-{value[6:]}"
    return value


def _is_non_chat(model_id: str) -> bool:
    tokens = {t for t in re.split(r"[-.]", model_id.lower()) if t}
    return bool(tokens & _NON_CHAT_TOKENS)


def filter_chat_model_ids(
    ids: Iterable[str],
    *,
    curated: Sequence[str] = (),
    keep: Iterable[str] = (),
) -> List[str]:
    """Reduce a raw `/v1/models` listing to what belongs in a picker.

    Order of operations matters, and the first rule is the safety net for the
    other two:

    1. **Curated ids and ``keep`` ids always survive.** Whatever the patterns
       below decide, a model we ship metadata for -- or one the user has already
       selected -- is never removed. A filter that can drop the user's saved
       model would change their selection with no message anywhere.
    2. **Non-chat ids go**, by whole-token match (see ``_NON_CHAT_TOKENS``).
    3. **Dated snapshots collapse.** When `gpt-4o` is present, every
       `gpt-4o-YYYY-MM-DD` is hidden behind it. When the base is *absent*, the
       newest snapshot is kept rather than the family vanishing entirely --
       otherwise a model offered only as a pinned snapshot would disappear from
       the picker, which is the failure mode most likely to bite in practice.

    ``ft:`` fine-tunes are kept: a fine-tune of a vision model is a perfectly
    good chat model. They sort last, after everything else.

    Returns ``[]`` for an empty input; the caller treats that as a failed fetch
    rather than as "this account has no models".
    """
    ordered = [str(i) for i in ids if i]
    protected = set(curated) | {k for k in keep if k}
    present = set(ordered)

    survivors = [
        model_id for model_id in ordered
        if model_id in protected or not _is_non_chat(model_id)
    ]

    # Group the dated variants so we can tell "collapse behind the base" from
    # "this family only exists as snapshots".
    newest_of: dict = {}
    for model_id in survivors:
        match = _DATED.match(model_id)
        if not match:
            continue
        base = match.group("base")
        date = _normalise_date(match.group("date"))
        if base not in present:
            current = newest_of.get(base)
            if current is None or date > current[0]:
                newest_of[base] = (date, model_id)

    out: List[str] = []
    fine_tunes: List[str] = []
    for model_id in survivors:
        if model_id.startswith("ft:"):
            fine_tunes.append(model_id)
            continue
        if model_id in protected:
            out.append(model_id)
            continue

        match = _DATED.match(model_id)
        if match:
            base = match.group("base")
            if base in present:
                continue                          # collapsed behind the base id
            if newest_of.get(base, (None, None))[1] != model_id:
                continue                          # an older snapshot of a base-less family
            out.append(model_id)
            continue

        short = _SHORT_DATED.match(model_id)
        if short and short.group("base") in present:
            continue                              # legacy MMDD snapshot, base present

        out.append(model_id)

    return out + fine_tunes


# Alias kept for import compatibility
DEV_OPENAI_MODELS = OPENAI_MODELS


def list_models_live(client=None, api_key: Optional[str] = None,
                     timeout: float = 8.0, *, keep: Iterable[str] = (),
                     include_all: bool = False) -> List[dict]:
    """Ask the API which OpenAI models this account can use.

    Returns ``{"id", "name", "created"}`` records for ``catalog`` to merge. The
    endpoint reports no display name, so ``name`` is empty and the catalog falls
    back to the id -- which is what every OpenAI picker in this app has always
    shown anyway.

    ``include_all`` bypasses :func:`filter_chat_model_ids`, backing
    ``idt models --all`` for when the filter is hiding something it should not.

    Raises rather than swallowing, for the same reason as the Claude fetcher:
    the caller cannot tell a failure from an empty account otherwise.
    """
    if client is None:
        from openai import OpenAI

        client = OpenAI(api_key=api_key, timeout=timeout)

    response = client.models.list()
    records = {}
    for model in getattr(response, "data", None) or []:
        model_id = str(getattr(model, "id", "") or "")
        if not model_id:
            continue
        created = getattr(model, "created", None)
        try:
            created = float(created) if created is not None else 0.0
        except (TypeError, ValueError):
            created = 0.0
        records[model_id] = {"id": model_id, "name": "", "created": created}

    if include_all:
        wanted = list(records)
    else:
        wanted = filter_chat_model_ids(
            records, curated=OPENAI_MODELS, keep=keep
        )
    return [records[model_id] for model_id in wanted]


class OpenAIProvider(BaseProvider):
    def __init__(self, model: str = DEFAULT_MODEL, api_key: Optional[str] = None):
        try:
            from openai import OpenAI  # noqa: F401
        except ImportError:
            raise ImportError(
                "openai package is required: pip install openai"
            )
        from openai import OpenAI
        self._model = model
        # api_key=None → SDK reads OPENAI_API_KEY from environment
        self._client = OpenAI(api_key=api_key)

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model

    def describe(self, image_bytes: bytes, mime_type: str, prompt: str) -> DescriptionResult:
        b64 = base64.standard_b64encode(image_bytes).decode("ascii")
        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{b64}"},
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )
        usage = response.usage
        return DescriptionResult(
            text=response.choices[0].message.content,
            model=self._model,
            provider="openai",
            input_tokens=usage.prompt_tokens if usage else None,
            output_tokens=usage.completion_tokens if usage else None,
        )
