"""
Anthropic Claude provider.
Reads ANTHROPIC_API_KEY from the environment (standard SDK behavior).
"""
from __future__ import annotations

import base64
from typing import Optional

from .base import BaseProvider, DescriptionResult

# The list below is no longer the source of truth for *which* models exist --
# `catalog.py` asks `GET /v1/models` that, and this list is the offline fallback
# plus the metadata layer (issue #267). It is still the source of truth for
# context_window / max_output / cost / recommended, and for display order, none
# of which the API reports.
#
# All Claude models support vision natively. Updated July 2026.
CLAUDE_MODELS = [
    # Current generation — 5.x
    "claude-opus-5",
    "claude-sonnet-5",
    "claude-fable-5",
    "claude-mythos-5",
    "claude-mythos-preview",
    # Current generation — 4.x (still supported)
    "claude-opus-4-8",
    "claude-opus-4-7",
    "claude-opus-4-6",
    "claude-sonnet-4-6",
    "claude-haiku-4-5-20251001",
    # Legacy (still in SDK, users may have old descriptions referencing them)
    "claude-opus-4-5-20251101",
    "claude-sonnet-4-5-20250929",
    "claude-opus-4-1-20250805",
]

DEFAULT_MODEL = "claude-opus-4-8"

CLAUDE_MODEL_METADATA: dict = {
    # --- Generation 5 ---
    "claude-opus-5": {
        "name": "Claude Opus 5",
        "description": "Flagship — highest intelligence and description depth",
        "generation": "5.0", "context_window": 200000, "max_output": 128000,
        "supports_vision": True, "cost": "$$$$", "recommended": True,
    },
    "claude-sonnet-5": {
        "name": "Claude Sonnet 5",
        "description": "Best balance of speed and intelligence",
        "generation": "5.0", "context_window": 200000, "max_output": 64000,
        "supports_vision": True, "cost": "$$$", "recommended": True,
    },
    "claude-fable-5": {
        "name": "Claude Fable 5",
        "description": "Creative model with strong visual storytelling",
        "generation": "5.0", "context_window": 200000, "max_output": 64000,
        "supports_vision": True, "cost": "$$", "recommended": False,
    },
    "claude-mythos-5": {
        "name": "Claude Mythos 5",
        "description": "Specialized model for complex visual analysis",
        "generation": "5.0", "context_window": 200000, "max_output": 128000,
        "supports_vision": True, "cost": "$$$", "recommended": False,
    },
    "claude-mythos-preview": {
        "name": "Claude Mythos (Preview)",
        "description": "Preview model — experimental, may change",
        "generation": "5.0", "context_window": 200000, "max_output": 128000,
        "supports_vision": True, "cost": "$$$", "recommended": False,
    },
    # --- Generation 4.x (current, still supported) ---
    "claude-opus-4-8": {
        "name": "Claude Opus 4.8",
        "description": "Most intelligent 4.x model for complex coding and analysis",
        "generation": "4.8", "context_window": 200000, "max_output": 128000,
        "supports_vision": True, "cost": "$$$", "recommended": True,
    },
    "claude-opus-4-7": {
        "name": "Claude Opus 4.7",
        "description": "High intelligence, strong value",
        "generation": "4.7", "context_window": 200000, "max_output": 128000,
        "supports_vision": True, "cost": "$$$", "recommended": False,
    },
    "claude-opus-4-6": {
        "name": "Claude Opus 4.6",
        "description": "Intelligent model for agents and complex coding",
        "generation": "4.6", "context_window": 200000, "max_output": 128000,
        "supports_vision": True, "cost": "$$$", "recommended": False,
    },
    "claude-sonnet-4-6": {
        "name": "Claude Sonnet 4.6",
        "description": "Best combination of speed and intelligence (4.x)",
        "generation": "4.6", "context_window": 200000, "max_output": 64000,
        "supports_vision": True, "cost": "$$", "recommended": False,
    },
    "claude-haiku-4-5-20251001": {
        "name": "Claude Haiku 4.5",
        "description": "Fastest model with near-frontier intelligence",
        "generation": "4.5", "context_window": 200000, "max_output": 64000,
        "supports_vision": True, "cost": "$", "recommended": True,
    },
    # --- Legacy (still in SDK, not recommended for new work) ---
    "claude-opus-4-5-20251101": {
        "name": "Claude Opus 4.5",
        "description": "Legacy — prefer claude-opus-4-8 or claude-opus-5",
        "generation": "4.5", "context_window": 200000, "max_output": 32000,
        "supports_vision": True, "cost": "$$$", "recommended": False,
    },
    "claude-sonnet-4-5-20250929": {
        "name": "Claude Sonnet 4.5",
        "description": "Legacy — prefer claude-sonnet-5 or claude-sonnet-4-6",
        "generation": "4.5", "context_window": 200000, "max_output": 64000,
        "supports_vision": True, "cost": "$$", "recommended": False,
    },
    "claude-opus-4-1-20250805": {
        "name": "Claude Opus 4.1",
        "description": "Legacy — prefer claude-opus-4-8 or claude-opus-5",
        "generation": "4.1", "context_window": 200000, "max_output": 32000,
        "supports_vision": True, "cost": "$$$", "recommended": False,
    },
}


def get_claude_model_info(model_id: str) -> dict:
    return CLAUDE_MODEL_METADATA.get(model_id, {"name": model_id, "supports_vision": True})


def format_claude_model_for_display(model_id: str, include_description: bool = False) -> str:
    info = get_claude_model_info(model_id)
    name = info.get("name", model_id)
    if include_description and "description" in info:
        return f"{name} ({info['description']})"
    return name


# `get_claude_api_id_from_display` was removed here. It mapped a display name
# back to an API id by scanning CLAUDE_MODEL_METADATA, falling through to
# returning its argument unchanged. Harmless while every model was in that dict;
# actively wrong once the catalog can list models that are not, because the
# fallback would hand a *display string* to the API as a model id. It had no
# callers -- every picker stores the api id as wx client data, which is the
# right way to do this -- so it went rather than being fixed into a trap that
# works until it doesn't.


# Alias kept for import compatibility
DEV_CLAUDE_MODELS = CLAUDE_MODELS


# ---------------------------------------------------------------------------
# Live listing
# ---------------------------------------------------------------------------

#: Pages of the models endpoint. The account's list is short enough that this is
#: really a "fetch it all in one request" number with headroom.
_PAGE_SIZE = 100

#: Bound on how many pages we will walk. A malformed pagination response that
#: kept reporting another page would otherwise spin forever on a worker thread,
#: where nothing would ever surface it.
_MAX_PAGES = 20


def list_models_live(client=None, api_key: Optional[str] = None,
                     timeout: float = 8.0) -> list:
    """Ask the API which Claude models this account can use.

    Returns ``{"id", "name", "created"}`` records -- the shape ``catalog`` merges
    and ``model_cache`` stores. Deliberately *not* ``ModelEntry``: building those
    is the catalog's job, and keeping it there is what stops a live response from
    ever constructing an entry that could shadow curated limits.

    ``client`` is injectable so tests never reach the network, matching
    ``ollama._show(client=...)``.

    Raises rather than swallowing. The caller (``catalog.refresh_models``) has
    the cache to fall back on and the negative-TTL bookkeeping to do, and it
    cannot do either if a failure arrives disguised as an empty list.
    """
    if client is None:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key, timeout=timeout)

    out: list = []
    seen: set = set()
    page = client.models.list(limit=_PAGE_SIZE)

    for _ in range(_MAX_PAGES):
        for model in getattr(page, "data", None) or []:
            model_id = str(getattr(model, "id", "") or "")
            # `type` is "model" for real entries; anything else is a shape we
            # do not recognise and should not be putting in a picker.
            if not model_id or getattr(model, "type", "model") != "model":
                continue
            if model_id in seen:
                continue
            seen.add(model_id)
            out.append({
                "id": model_id,
                "name": str(getattr(model, "display_name", "") or "").strip(),
                "created": _created_timestamp(model),
            })

        has_next = getattr(page, "has_next_page", None)
        try:
            if not (callable(has_next) and has_next()):
                break
            page = page.get_next_page()
        except Exception:
            # Pagination is a convenience here, not a requirement -- the first
            # page already holds every model any real account has. Losing the
            # rest is better than losing the whole refresh.
            break

    return out


def _created_timestamp(model) -> float:
    """`created_at` as a sortable number, or 0 when it is missing or odd.

    The SDK hands back a ``datetime``; older or stubbed shapes may give a string
    or a number. This is only ever an ordering signal for models we have no
    metadata for, so an unparseable value costs a position in the list, nothing
    more.
    """
    raw = getattr(model, "created_at", None)
    if raw is None:
        return 0.0
    timestamp = getattr(raw, "timestamp", None)
    if callable(timestamp):
        try:
            return float(timestamp())
        except (ValueError, OSError, OverflowError):
            return 0.0
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


class ClaudeProvider(BaseProvider):
    def __init__(self, model: str = DEFAULT_MODEL, api_key: Optional[str] = None):
        try:
            import anthropic
        except ImportError:
            raise ImportError(
                "anthropic package is required for Claude: pip install anthropic"
            )
        self._model = model
        # api_key=None → SDK reads ANTHROPIC_API_KEY from environment
        self._client = __import__("anthropic").Anthropic(api_key=api_key)

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def model_name(self) -> str:
        return self._model

    def describe(self, image_bytes: bytes, mime_type: str, prompt: str) -> DescriptionResult:
        b64 = base64.standard_b64encode(image_bytes).decode("ascii")
        message = self._client.messages.create(
            model=self._model,
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime_type,
                                "data": b64,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )
        return DescriptionResult(
            text=message.content[0].text,
            model=self._model,
            provider="anthropic",
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
        )
