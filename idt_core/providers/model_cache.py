"""On-disk cache of the model lists returned by the provider APIs.

Pure storage. Nothing here knows what a model *is* -- it stores whatever list of
records ``catalog.py`` hands over and gives it back, or reports that it has
nothing. Keeping the disk layer separate is what lets the merge logic in
``catalog.py`` be tested with no filesystem at all, which matters because that
merge is what protects the recorded ``context_window`` figures the token
budgeter depends on.

One file per provider, under ``~/.idt/models/``. That directory is chosen to
match where the rest of IDT's mutable state already lives (``~/.idt/config.json``,
``~/.idt/chats/``, ``~/.idt/geocode_cache.json``); ``%APPDATA%/IDT`` is for config
*overrides* the user edits, which this is not.

Two properties this module exists to guarantee:

* **A bad cache is never worse than no cache.** Truncated JSON, an unknown
  schema version, a future-dated timestamp, an unreadable directory -- every one
  of them reads as "nothing cached", so the caller falls back to its curated
  list. Nothing here raises at a caller.
* **Concurrent writers cannot publish half a file.** All three IDT apps can run
  at once and refresh the same provider.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import List, Optional

__all__ = [
    "CACHE_VERSION",
    "cache_dir",
    "path_for",
    "read",
    "write",
    "account_fingerprint",
]

#: Bumped when the stored shape changes. A file carrying any other version is
#: ignored rather than migrated -- this is a cache, so the cheapest correct
#: answer is to refetch.
CACHE_VERSION = 1

#: Overrides the location entirely. The test suite points this at a tmp_path in
#: an autouse fixture; without it, whether a test passes would depend on whether
#: the developer had ever run `idt models --refresh`.
_DIR_ENV_VAR = "IDT_MODEL_CACHE_DIR"

#: Clocks move backwards (NTP corrections, VM snapshots, dual-boot). A cache
#: stamped in the future would otherwise read as fresh forever and never
#: refresh again, which is the one failure mode a TTL cache must not have.
_FUTURE_TOLERANCE_SECONDS = 60.0


def cache_dir() -> Path:
    """Directory holding the per-provider cache files.

    Not created here -- :func:`write` creates it, so a read on a machine that
    has never refreshed does not leave an empty directory behind.
    """
    override = os.environ.get(_DIR_ENV_VAR)
    if override:
        return Path(override)
    return Path.home() / ".idt" / "models"


def account_fingerprint(api_key: Optional[str]) -> str:
    """A short, non-reversible tag for the account a cached list belongs to.

    Both APIs return models by entitlement: Anthropic by organisation, OpenAI by
    project (including that project's fine-tunes). Serving one account's list to
    another shows models the user cannot call and hides ones they can. This is
    the same reasoning that makes ``ollama._SHOW_CACHE`` key on host as well as
    model name.

    Never the key itself, and never a prefix of one -- a cache file is not a
    place to leave credential material, even partially.
    """
    if not api_key:
        return "nokey"
    import hashlib

    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:12]


def _safe_name(provider: str) -> str:
    """Provider name reduced to something that is certainly a filename.

    Validate-by-construction rather than sanitise: only characters known to be
    safe survive, so a provider name like ``"ollama cloud"`` becomes
    ``ollama_cloud`` and nothing can escape the directory.
    """
    cleaned = "".join(
        ch if ch.isalnum() else "_" for ch in (provider or "").strip().lower()
    )
    return cleaned or "unknown"


def path_for(provider: str) -> Path:
    """Cache file for one provider.

    One file per provider, not one shared file: a Claude refresh in ImageDescriber
    and an OpenAI refresh in IDT Chat can be in flight at the same moment, and a
    shared file would make one clobber the other's result.
    """
    return cache_dir() / f"{_safe_name(provider)}.json"


def read(provider: str, fingerprint: str, max_age_seconds: float) -> Optional[List[dict]]:
    """Cached records for ``provider``, or ``None`` when there is nothing usable.

    ``None`` covers every failure equally -- absent, unreadable, corrupt, wrong
    schema version, wrong account, or too old. The caller's response is the same
    in all of those cases (use the curated list, refresh in the background), so
    distinguishing them here would only invite a caller to get one wrong.
    """
    try:
        raw = path_for(provider).read_text(encoding="utf-8")
    except OSError:
        return None

    try:
        payload = json.loads(raw)
    except (ValueError, TypeError):
        # Truncated or garbage -- most likely a writer that died mid-rename on a
        # machine where the atomic path below did not hold.
        return None

    if not isinstance(payload, dict):
        return None
    if payload.get("version") != CACHE_VERSION:
        return None
    if payload.get("account") != fingerprint:
        return None

    models = payload.get("models")
    if not isinstance(models, list) or not models:
        # An empty list is not a legitimate cached answer: `refresh` refuses to
        # store one, so seeing it means the file was written by something else.
        return None

    fetched_at = payload.get("fetched_at")
    if not isinstance(fetched_at, (int, float)):
        return None

    now = time.time()
    if fetched_at > now + _FUTURE_TOLERANCE_SECONDS:
        return None                       # future-dated; treat as stale
    if now - fetched_at > max_age_seconds:
        return None

    return [m for m in models if isinstance(m, dict)] or None


def write(provider: str, fingerprint: str, models: List[dict]) -> bool:
    """Store ``models`` for ``provider``. True if it landed.

    Refuses to store an empty list. An empty result almost always means the
    fetch failed in a way the SDK did not raise on, and caching it would replace
    a good list with nothing for the next 24 hours.

    The write is atomic *and* multi-process safe. The existing atomic writers in
    this repo (``chat/store.py``, ``workspace.py``) use a fixed ``.tmp`` name,
    which is fine for their one-writer access patterns but not for this one: with
    three apps refreshing the same provider, one truncates the other's temp file
    mid-write and the surviving ``os.replace`` publishes partial bytes -- or, on
    Windows, fails outright while the other process holds the handle. Hence a
    temp name unique per process and per call.

    Losing a race is harmless and is not reported as failure to the caller's
    logic: whoever lost simply refreshes again within the TTL. Publishing a
    truncated file would not be harmless, which is what the rename buys.
    """
    if not models:
        return False

    payload = {
        "version": CACHE_VERSION,
        "account": fingerprint,
        "fetched_at": time.time(),
        "models": models,
    }

    target = path_for(provider)
    tmp = target.with_name(f"{target.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        os.replace(tmp, target)
        return True
    except OSError:
        # A read-only home directory, a full disk, or a lost rename race. The
        # cache is disposable, so none of those is worth surfacing.
        try:
            tmp.unlink()
        except OSError:
            pass
        return False
