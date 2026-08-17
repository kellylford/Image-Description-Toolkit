"""What models a provider offers, and what we know about each one.

Ollama has always been dynamic: if a model is on the machine, IDT offers it.
Claude and OpenAI were the opposite -- two hand-maintained lists that went stale
between releases, so a model released today stayed invisible until someone
edited a file and cut a build, and a retired one stayed in every picker until it
failed at request time (issue #267).

Both APIs do list their models. Neither reports context window, max output,
pricing, or capability flags. So neither "hardcode everything" nor "trust the
API for everything" works, and this module is the hybrid:

    the live list decides what EXISTS
    the curated tables decide what we KNOW about each entry
    anything we do not recognise still appears, marked, with no invented numbers

**The load-bearing invariant is that curated always wins.** A live listing
contributes existence, a display name, and a creation timestamp for ordering --
nothing else. It may never overwrite a recorded ``context_window`` or
``max_output``, because those feed the chat token budgeter and the context
gauge; letting a live entry blank them would silently drop every Claude model
back to a flat guess, with no error anywhere to notice.

Reading, in three layers, cheapest first:

* ``model_entry`` answers from the curated tables with no I/O at all. This is the
  hot path -- ``registry.model_limits`` calls it on every chat turn -- so it must
  stay free of even a ``stat()``.
* ``cached_models`` adds the on-disk cache (``model_cache.py``), read once per
  process and memoised. Safe to call from a wx event handler: no network, and at
  most one file read for the life of the process.
* Refreshing the cache from the API is a separate, explicitly blocking call for
  worker threads and the CLI.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, replace
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from . import model_cache

__all__ = [
    "ModelEntry",
    "CACHE_TTL_SECONDS",
    "cached_models",
    "model_entry",
    "curated_models",
    "refresh_models",
    "refresh_if_stale",
    "is_stale",
    "invalidate",
]

#: How long a cached listing is served before a refresh is wanted. A day is
#: chosen against how often these providers actually ship models, not against
#: how cheap the call is: refreshing more often would add API round trips
#: without ever showing the user something new.
CACHE_TTL_SECONDS = 24 * 3600.0

#: Shown in place of a curated description for a model the API returned but we
#: have no recorded metadata for. Deliberately plain text rather than a symbol
#: or colour -- this is read aloud.
NEW_MODEL_NOTE = "new — details unknown"


@dataclass(frozen=True)
class ModelEntry:
    """One model, and everything the app knows about it.

    ``context_window`` and ``max_output`` are ``Optional`` and stay ``None`` for
    anything not in the curated tables. That is not laziness -- it is the
    contract ``registry.model_limits`` documents, and the reason unknown models
    flow through each caller's own documented fallback instead of a number this
    module made up.

    ``supports_vision`` is tri-state for the same reason. A live-only OpenAI
    model might be text-only, and claiming ``True`` would put it in
    ImageDescriber's *describe* picker, where handing it an image fails at
    request time. ``None`` means "we do not know", which a picker can present
    honestly.
    """

    id: str
    provider: str
    name: str
    description: str = ""
    context_window: Optional[int] = None
    max_output: Optional[int] = None
    cost: str = ""
    recommended: bool = False
    supports_vision: Optional[bool] = None
    #: "curated" -- in our tables. "live" -- returned by the API, unrecognised.
    #: "retired" -- in our tables, absent from the live list, resolved anyway for
    #: an old workspace or chat session that still references it.
    source: str = "curated"

    @property
    def is_known(self) -> bool:
        return self.source != "live"

    def display(self, *, mark_new: bool = True) -> str:
        """Label for a picker. Screen readers read this, so it stays prose."""
        if mark_new and self.source == "live":
            return f"{self.name} ({NEW_MODEL_NOTE})"
        return self.name


# ---------------------------------------------------------------------------
# The curated tables
# ---------------------------------------------------------------------------

def _curated_tables(provider: str) -> Tuple[Sequence[str], Dict[str, dict]]:
    """``(ordered ids, metadata)`` for a provider, or empty for anything else.

    Imported inside the function, not at module scope: ``claude.py`` and
    ``openai_provider.py`` each define a provider class that imports a vendor
    SDK at construction time, and this module is reached from
    ``registry.model_limits`` on every chat turn. A module-scope import would
    make an absent ``openai`` package break Claude chat.
    """
    if provider == "claude":
        from .claude import CLAUDE_MODEL_METADATA, CLAUDE_MODELS

        return CLAUDE_MODELS, CLAUDE_MODEL_METADATA
    if provider == "openai":
        from .openai_provider import OPENAI_MODEL_METADATA, OPENAI_MODELS

        return OPENAI_MODELS, OPENAI_MODEL_METADATA
    return (), {}


def _canonical(provider: str) -> str:
    """Resolve aliases (``anthropic`` -> ``claude``) through the registry."""
    try:
        from .registry import capabilities_for

        name = capabilities_for(provider).provider
        if name != "unknown":
            return name
    except ImportError:  # pragma: no cover - registry always ships
        pass
    return (provider or "").strip().lower()


def _entry_from_metadata(model_id: str, provider: str, meta: dict,
                         source: str = "curated") -> ModelEntry:
    context = meta.get("context_window")
    max_output = meta.get("max_output")
    return ModelEntry(
        id=model_id,
        provider=provider,
        name=meta.get("name") or model_id,
        description=meta.get("description", ""),
        context_window=int(context) if context else None,
        max_output=int(max_output) if max_output else None,
        cost=meta.get("cost", ""),
        recommended=bool(meta.get("recommended", False)),
        supports_vision=meta.get("supports_vision"),
        source=source,
    )


def curated_models(provider: str) -> List[ModelEntry]:
    """Every model in the curated tables, in their hand-tuned order.

    That order is load-bearing, not cosmetic: it is roughly best-first, and
    several pickers fall back to selecting index 0.
    """
    canonical = _canonical(provider)
    ids, metadata = _curated_tables(canonical)
    return [
        _entry_from_metadata(model_id, canonical, metadata.get(model_id, {}))
        for model_id in ids
    ]


# ---------------------------------------------------------------------------
# Merge
# ---------------------------------------------------------------------------

def merge(provider: str, live: Sequence[dict], *,
          keep: Iterable[str] = ()) -> List[ModelEntry]:
    """Combine a live listing with the curated tables.

    ``live`` is a list of ``{"id", "name", "created"}`` records -- whatever the
    provider's fetcher and the disk cache exchange. Ordering is:

    1. curated ids, in their curated order, that the live list still has;
    2. ids named in ``keep`` that survived nothing else;
    3. live-only ids, newest first.

    ``keep`` exists because every filter here can remove the model the user has
    already selected and saved. Without it a picker would silently fall back to
    index 0, changing the user's model with no message anywhere -- the kind of
    change that is invisible until a bill or an output style shifts.
    """
    canonical = _canonical(provider)
    ids, metadata = _curated_tables(canonical)

    live_ids = [str(record.get("id")) for record in live if record.get("id")]
    live_by_id = {str(r.get("id")): r for r in live if r.get("id")}
    live_set = set(live_ids)
    # Ordered and de-duplicated, not a set: sets iterate in an order that varies
    # between runs, and step 2 below appends straight into a picker. Two kept
    # models would otherwise swap places between one dialog opening and the next.
    keep_ids = list(dict.fromkeys(k for k in keep if k))
    keep_set = set(keep_ids)

    out: List[ModelEntry] = []
    seen: set = set()

    # 1. Curated, in curated order. Retired ids -- ours but no longer offered --
    #    drop out here, which is the other half of what issue #267 asks for.
    for model_id in ids:
        if model_id in live_set or model_id in keep_set:
            out.append(
                _entry_from_metadata(model_id, canonical, metadata.get(model_id, {}))
            )
            seen.add(model_id)

    # 2. Anything still in use that neither table nor listing produced. It is
    #    real enough that the user selected it, so it must remain selectable.
    for model_id in keep_ids:
        if model_id not in seen:
            out.append(_unknown_entry(canonical, model_id, live_by_id.get(model_id)))
            seen.add(model_id)

    # 3. Live-only, newest first. Newest first because the entire point is that
    #    a model released today is visible today.
    fresh = [m for m in live_ids if m not in seen]
    fresh.sort(key=lambda m: live_by_id[m].get("created") or 0, reverse=True)
    for model_id in fresh:
        out.append(_unknown_entry(canonical, model_id, live_by_id[model_id]))

    return out


def _unknown_entry(provider: str, model_id: str,
                   record: Optional[dict] = None) -> ModelEntry:
    """An entry for a model with no curated metadata.

    Limits stay ``None`` -- the whole reason the ``model_limits`` contract says
    ``None`` rather than a guess. ``supports_vision`` likewise.
    """
    name = ""
    if record:
        name = str(record.get("name") or "").strip()
    return ModelEntry(
        id=model_id,
        provider=provider,
        name=name or model_id,
        description=NEW_MODEL_NOTE,
        source="live",
    )


# ---------------------------------------------------------------------------
# Process memo
# ---------------------------------------------------------------------------

#: provider -> merged entries. Populated on first `cached_models` call and then
#: reused, so repeatedly opening a picker costs nothing.
_memo: Dict[str, List[ModelEntry]] = {}
#: Guards `_memo`. `check -> read -> store` is not atomic under the GIL, and
#: several wx dialogs can open at once.
_lock = threading.RLock()


def invalidate(provider: Optional[str] = None) -> None:
    """Drop the process memo, so the next read consults disk again.

    Also clears the failure bookkeeping: an explicit invalidate is the user
    asking for a fresh look (the Refresh AI Models menu item, `--refresh`), and
    making them wait out a negative TTL they cannot see would read as the button
    doing nothing.
    """
    with _lock:
        if provider is None:
            _memo.clear()
            _failed_at.clear()
        else:
            canonical = _canonical(provider)
            _memo.pop(canonical, None)
            _failed_at.pop(canonical, None)


def _api_key_for(provider: str) -> Optional[str]:
    try:
        from ..keys import resolve_api_key

        return resolve_api_key(provider)
    except Exception:  # pragma: no cover - key resolution never raises today
        return None


def _load(provider: str) -> List[ModelEntry]:
    """Merged entries for a provider, consulting disk at most once per process."""
    with _lock:
        cached = _memo.get(provider)
        if cached is not None:
            return cached

        fingerprint = model_cache.account_fingerprint(_api_key_for(provider))
        records = model_cache.read(provider, fingerprint, CACHE_TTL_SECONDS)
        entries = merge(provider, records) if records else curated_models(provider)
        _memo[provider] = entries
        return entries


def cached_models(provider: str, *, keep: Iterable[str] = ()) -> List[ModelEntry]:
    """Best known model list for ``provider``, without touching the network.

    Never blocks on I/O beyond one file read per process, so this is what every
    picker calls on the UI thread. It never returns empty for Claude or OpenAI:
    with no cache, no key and no network it is exactly the curated list, which
    is how these pickers behaved before this module existed.

    The returned list is a fresh one -- callers sort it (ImageDescriber orders
    Claude models cheapest-first, which deliberately differs from the curated
    order) and must not be sorting the memo.
    """
    canonical = _canonical(provider)
    entries = list(_load(canonical))

    present = {entry.id for entry in entries}
    for model_id in keep:
        if model_id and model_id not in present:
            entries.append(_in_use_entry(canonical, model_id))
    return entries


def _in_use_entry(provider: str, model_id: str) -> ModelEntry:
    """The user's current model, when nothing else in the list produced it.

    Marked rather than silently normal: a model that the API no longer lists is
    worth flagging before the request fails, but removing it from the picker
    outright would change the user's selection without telling them.
    """
    curated = model_entry(provider, model_id)
    if curated.source == "curated":
        return replace(curated, source="retired")
    return replace(curated, source="retired", description="in use — no longer listed")


def model_entry(provider: str, model_id: str) -> ModelEntry:
    """Everything known about one model. Never raises, never does I/O.

    Curated tables first, and that ordering is the contract: this is what
    ``registry.model_limits`` calls on every chat turn, and a cache consulted
    ahead of the tables could let a live listing blank a recorded context
    window. The process memo is read only when something has already populated
    it, so this stays free of even a ``stat()`` on the hot path.
    """
    canonical = _canonical(provider)
    _, metadata = _curated_tables(canonical)
    meta = metadata.get(model_id)
    if meta:
        return _entry_from_metadata(model_id, canonical, meta)

    with _lock:
        for entry in _memo.get(canonical, ()):        # already loaded only
            if entry.id == model_id:
                return entry

    return _unknown_entry(canonical, model_id)


# ---------------------------------------------------------------------------
# Refreshing from the API
# ---------------------------------------------------------------------------

#: How long a failed fetch is remembered, so an offline machine does not spawn a
#: worker and wait out a timeout every time any picker opens. Short, because the
#: usual cause is a key that was just added or a network that just came back --
#: `ollama.py` makes the same trade for the same reason.
NEGATIVE_TTL_SECONDS = 60.0

_failed_at: Dict[str, float] = {}
#: Providers with a fetch in flight. Two dialogs opening together must produce
#: one API call, not two racing to write the same cache file.
_in_flight: set = set()


def _fetch(provider: str, api_key: Optional[str], timeout: float,
           keep: Iterable[str], include_all: bool) -> List[dict]:
    """Dispatch to the provider's own fetcher. Raises on failure."""
    if provider == "claude":
        from .claude import list_models_live

        return list_models_live(api_key=api_key, timeout=timeout)
    if provider == "openai":
        from .openai_provider import list_models_live

        return list_models_live(api_key=api_key, timeout=timeout,
                                keep=keep, include_all=include_all)
    raise ValueError(f"no live listing for provider {provider!r}")


def is_stale(provider: str) -> bool:
    """True when a refresh would do something.

    False when the cache is fresh, when a recent attempt failed, when the
    provider needs a key we do not have, or when it has no live listing at all.
    """
    canonical = _canonical(provider)
    if canonical not in ("claude", "openai"):
        return False

    api_key = _api_key_for(canonical)
    if not api_key:
        return False                       # nothing to authenticate with

    with _lock:
        if canonical in _in_flight:
            return False
        failed = _failed_at.get(canonical)
        if failed is not None and time.monotonic() - failed < NEGATIVE_TTL_SECONDS:
            return False

    fingerprint = model_cache.account_fingerprint(api_key)
    return model_cache.read(canonical, fingerprint, CACHE_TTL_SECONDS) is None


def refresh_models(provider: str, *, timeout: float = 8.0,
                   keep: Iterable[str] = (), include_all: bool = False,
                   force: bool = False) -> Optional[List[ModelEntry]]:
    """Fetch the live list, merge it, cache it, and return the result.

    **Blocking.** Call it from a worker thread or the CLI, never from a wx event
    handler -- ``cached_models`` is what pickers use.

    Returns ``None`` when nothing was refreshed: no key, no live listing for this
    provider, a recent failure still inside the negative TTL, another thread
    already fetching, or the fetch failed now. ``None`` means "carry on with what
    ``cached_models`` gives you", never "there are no models".

    An empty or implausibly short response is treated as a failed fetch rather
    than as retirement. Publishing it would empty the picker and, worse, cache
    that emptiness for a day.
    """
    canonical = _canonical(provider)
    if canonical not in ("claude", "openai"):
        return None

    api_key = _api_key_for(canonical)
    if not api_key:
        return None

    with _lock:
        if canonical in _in_flight:
            return None                    # someone else is already doing it
        if not force:
            failed = _failed_at.get(canonical)
            if failed is not None and time.monotonic() - failed < NEGATIVE_TTL_SECONDS:
                return None
        _in_flight.add(canonical)

    # One try/finally around everything, so `_in_flight` is released no matter
    # how we leave. An earlier version cleared it in an `except Exception` and
    # in a `finally` on a second, inner block -- which meant a BaseException
    # (KeyboardInterrupt from Ctrl+C at the CLI, SystemExit at shutdown) skipped
    # both and left the provider marked as permanently mid-fetch. Every later
    # refresh in that process then returned None, silently, forever.
    try:
        try:
            records = _fetch(canonical, api_key, timeout, keep, include_all)
        except Exception:
            # Offline, bad key, rate limited, SDK shape changed -- all the same
            # answer to the caller, and all worth not retrying for a minute.
            with _lock:
                _failed_at[canonical] = time.monotonic()
            return None

        # A listing this short is not a plausible account; treat it as a failed
        # fetch so it can neither empty the picker nor retire real models.
        if len(records) < 3:
            with _lock:
                _failed_at[canonical] = time.monotonic()
            return None

        entries = merge(canonical, records, keep=keep)
        fingerprint = model_cache.account_fingerprint(api_key)
        model_cache.write(canonical, fingerprint, records)

        with _lock:
            _memo[canonical] = entries
            _failed_at.pop(canonical, None)
        return list(entries)
    finally:
        with _lock:
            _in_flight.discard(canonical)


def refresh_if_stale(provider: str, **kwargs) -> Optional[List[ModelEntry]]:
    """:func:`refresh_models`, but only when the cache has actually expired."""
    if not is_stale(provider):
        return None
    return refresh_models(provider, **kwargs)
