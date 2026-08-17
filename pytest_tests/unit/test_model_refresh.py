"""Fetching live model lists, and every way that can go wrong.

The refresh path runs on a worker thread behind a picker. That shapes what these
tests are about: not "does it fetch", but "when it cannot fetch, is the user
left exactly where they were". A refresh that raises, blanks a picker, or caches
an empty answer for a day is worse than never having refreshed.

No network anywhere. The fetchers take an injectable client, and the SDKs are
faked at ``sys.modules`` when the construction path itself is under test --
the same two techniques ``test_ollama_vision_filter.py`` uses.
"""

import sys
import threading
import time
import types
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from idt_core.providers import catalog, model_cache  # noqa: E402
from idt_core.providers.claude import CLAUDE_MODELS, list_models_live  # noqa: E402
from idt_core.providers.openai_provider import (  # noqa: E402
    OPENAI_MODELS,
    list_models_live as openai_list_models_live,
)

pytestmark = pytest.mark.unit

_TEST_KEY = "test-key-not-a-real-credential"


@pytest.fixture(autouse=True)
def clean_catalog(monkeypatch):
    monkeypatch.setattr(catalog, "_api_key_for", lambda _p: _TEST_KEY)
    catalog.invalidate()
    yield
    catalog.invalidate()


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class _Model:
    def __init__(self, model_id, display_name="", created_at=None, type_="model"):
        self.id = model_id
        self.display_name = display_name
        self.created_at = created_at
        self.type = type_


class _Page:
    """One page of an SDK listing, optionally chained to another."""

    def __init__(self, data, nxt=None):
        self.data = data
        self._next = nxt

    def has_next_page(self):
        return self._next is not None

    def get_next_page(self):
        return self._next


class _Models:
    def __init__(self, page):
        self._page = page
        self.calls = 0

    def list(self, **kwargs):
        self.calls += 1
        return self._page


class _Client:
    def __init__(self, page):
        self.models = _Models(page)


def _claude_client(*ids):
    return _Client(_Page([_Model(i, f"Name {i}") for i in ids]))


def _openai_client(*ids):
    data = [types.SimpleNamespace(id=i, created=100) for i in ids]
    return _Client(_Page(data))


# ---------------------------------------------------------------------------
# Claude fetcher
# ---------------------------------------------------------------------------

def test_claude_returns_records_not_entries():
    """Building ModelEntry objects is the catalog's job. Keeping it there is
    what stops a live response from ever shadowing curated limits."""
    records = list_models_live(client=_claude_client("claude-opus-5"))
    assert records == [{"id": "claude-opus-5", "name": "Name claude-opus-5",
                        "created": 0.0}]


def test_claude_walks_pages():
    page2 = _Page([_Model("claude-b")])
    client = _Client(_Page([_Model("claude-a")], nxt=page2))
    assert [r["id"] for r in list_models_live(client=client)] == ["claude-a", "claude-b"]


def test_claude_stops_if_pagination_misbehaves():
    """A page that always claims another would spin forever on a worker thread,
    where nothing would ever surface it."""
    class _Endless:
        data = [_Model("claude-a")]

        def has_next_page(self):
            return True

        def get_next_page(self):
            return self

    records = list_models_live(client=_Client(_Endless()))
    assert [r["id"] for r in records] == ["claude-a"]


def test_claude_skips_non_model_entries():
    client = _Client(_Page([_Model("claude-a"), _Model("weird", type_="something")]))
    assert [r["id"] for r in list_models_live(client=client)] == ["claude-a"]


def test_claude_converts_a_datetime_created_at():
    from datetime import datetime, timezone

    when = datetime(2026, 8, 1, tzinfo=timezone.utc)
    client = _Client(_Page([_Model("claude-a", created_at=when)]))
    assert list_models_live(client=client)[0]["created"] == when.timestamp()


def test_claude_survives_an_unparseable_created_at():
    """Only an ordering signal, so a bad value costs a position, not the fetch."""
    client = _Client(_Page([_Model("claude-a", created_at="not a date")]))
    assert list_models_live(client=client)[0]["created"] == 0.0


def test_claude_propagates_failures():
    """The caller needs to tell a failure from an empty account."""
    class _Boom:
        def list(self, **kwargs):
            raise RuntimeError("401 unauthorized")

    client = types.SimpleNamespace(models=_Boom())
    with pytest.raises(RuntimeError):
        list_models_live(client=client)


# ---------------------------------------------------------------------------
# OpenAI fetcher
# ---------------------------------------------------------------------------

def test_openai_applies_the_chat_filter():
    client = _openai_client("gpt-5.2", "text-embedding-3-large", "whisper-1")
    assert [r["id"] for r in openai_list_models_live(client=client)] == ["gpt-5.2"]


def test_openai_include_all_bypasses_the_filter():
    """Backs `idt models --all`, for when the filter hides something it should not."""
    client = _openai_client("gpt-5.2", "whisper-1")
    records = openai_list_models_live(client=client, include_all=True)
    assert {r["id"] for r in records} == {"gpt-5.2", "whisper-1"}


def test_openai_keep_survives_the_filter():
    client = _openai_client("gpt-5.2", "tts-1")
    records = openai_list_models_live(client=client, keep=["tts-1"])
    assert "tts-1" in [r["id"] for r in records]


def test_openai_supplies_no_display_name():
    """The endpoint reports none, and every OpenAI picker has always shown ids."""
    records = openai_list_models_live(client=_openai_client("gpt-5.2"))
    assert records[0]["name"] == ""


# ---------------------------------------------------------------------------
# refresh_models
# ---------------------------------------------------------------------------

def _fake_fetch(records):
    return lambda *a, **k: list(records)


def _records(*ids):
    return [{"id": i, "name": "", "created": n} for n, i in enumerate(ids)]


def test_a_successful_refresh_merges_caches_and_memoises(monkeypatch):
    monkeypatch.setattr(catalog, "_fetch",
                        _fake_fetch(_records("claude-opus-5", "claude-opus-6",
                                             "claude-sonnet-5")))
    entries = catalog.refresh_models("claude")

    assert [e.id for e in entries] == ["claude-opus-5", "claude-sonnet-5",
                                       "claude-opus-6"]
    # The merged result is what pickers now see, without re-reading disk.
    assert [e.id for e in catalog.cached_models("claude")] == [e.id for e in entries]
    # And it survives into the next process.
    fingerprint = model_cache.account_fingerprint(_TEST_KEY)
    assert model_cache.read("claude", fingerprint, catalog.CACHE_TTL_SECONDS)


def test_curated_limits_survive_a_refresh(monkeypatch):
    """The invariant, checked through the real refresh path rather than merge()."""
    monkeypatch.setattr(catalog, "_fetch",
                        _fake_fetch(_records("gpt-4o", "gpt-5.2", "gpt-5-mini")))
    catalog.refresh_models("openai")

    from idt_core.providers.registry import model_limits
    assert model_limits("openai", "gpt-4o") == (128_000, 16_384)


def test_a_failed_fetch_leaves_the_picker_alone(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("offline")

    monkeypatch.setattr(catalog, "_fetch", boom)
    assert catalog.refresh_models("claude") is None
    assert [e.id for e in catalog.cached_models("claude")] == list(CLAUDE_MODELS)


def test_an_implausibly_short_response_is_treated_as_failure(monkeypatch):
    """Publishing it would empty the picker AND cache that emptiness for a day."""
    monkeypatch.setattr(catalog, "_fetch", _fake_fetch(_records("claude-opus-5")))
    assert catalog.refresh_models("claude") is None
    assert [e.id for e in catalog.cached_models("claude")] == list(CLAUDE_MODELS)


def test_an_empty_response_is_treated_as_failure(monkeypatch):
    monkeypatch.setattr(catalog, "_fetch", _fake_fetch([]))
    assert catalog.refresh_models("claude") is None
    fingerprint = model_cache.account_fingerprint(_TEST_KEY)
    assert model_cache.read("claude", fingerprint, catalog.CACHE_TTL_SECONDS) is None


def test_no_key_means_no_fetch_attempt(monkeypatch):
    monkeypatch.setattr(catalog, "_api_key_for", lambda _p: None)
    monkeypatch.setattr(catalog, "_fetch",
                        lambda *a, **k: pytest.fail("fetched without a key"))
    assert catalog.refresh_models("claude") is None
    assert catalog.is_stale("claude") is False


def test_a_provider_with_no_live_listing_is_a_no_op(monkeypatch):
    monkeypatch.setattr(catalog, "_fetch",
                        lambda *a, **k: pytest.fail("fetched for ollama"))
    assert catalog.refresh_models("ollama") is None
    assert catalog.is_stale("ollama") is False


# ---------------------------------------------------------------------------
# Negative TTL and the in-flight guard
# ---------------------------------------------------------------------------

def test_a_recent_failure_is_not_retried(monkeypatch):
    """Otherwise an offline machine spawns a worker and waits out a timeout
    every single time any picker opens."""
    calls = []

    def boom(*a, **k):
        calls.append(1)
        raise RuntimeError("offline")

    monkeypatch.setattr(catalog, "_fetch", boom)
    catalog.refresh_models("claude")
    catalog.refresh_models("claude")
    catalog.refresh_models("claude")
    assert len(calls) == 1
    assert catalog.is_stale("claude") is False


def test_force_overrides_a_recent_failure(monkeypatch):
    calls = []

    def boom(*a, **k):
        calls.append(1)
        raise RuntimeError("offline")

    monkeypatch.setattr(catalog, "_fetch", boom)
    catalog.refresh_models("claude")
    catalog.refresh_models("claude", force=True)
    assert len(calls) == 2


def test_invalidate_clears_the_failure_marker(monkeypatch):
    """An explicit refresh is the user asking; making them wait out a TTL they
    cannot see would read as the button doing nothing."""
    monkeypatch.setattr(catalog, "_fetch",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")))
    catalog.refresh_models("claude")
    catalog.invalidate("claude")

    monkeypatch.setattr(catalog, "_fetch",
                        _fake_fetch(_records("claude-opus-5", "claude-a", "claude-b")))
    assert catalog.refresh_models("claude") is not None


def test_the_failure_marker_expires(monkeypatch):
    calls = []

    def boom(*a, **k):
        calls.append(1)
        raise RuntimeError("offline")

    monkeypatch.setattr(catalog, "_fetch", boom)
    catalog.refresh_models("claude")

    # A key added mid-session, or a network that came back, must be noticed
    # rather than written off for the rest of the process.
    #
    # `catalog.time` IS the stdlib time module, so the replacement must close
    # over the original function rather than call `time.monotonic()` again --
    # doing that patches itself and recurses.
    real_monotonic = time.monotonic
    monkeypatch.setattr(
        catalog.time, "monotonic",
        lambda: real_monotonic() + catalog.NEGATIVE_TTL_SECONDS + 1,
    )
    catalog.refresh_models("claude")
    assert len(calls) == 2


def test_concurrent_refreshes_fetch_once(monkeypatch):
    """Several dialogs opening together must not each hit the API and then race
    to write the same cache file."""
    calls = []
    started = threading.Event()

    def slow_fetch(*a, **k):
        calls.append(1)
        started.set()
        time.sleep(0.3)
        return _records("claude-opus-5", "claude-a", "claude-b")

    monkeypatch.setattr(catalog, "_fetch", slow_fetch)

    threads = [threading.Thread(target=catalog.refresh_models, args=("claude",))
               for _ in range(6)]
    for t in threads:
        t.start()
        started.wait(timeout=2)
    for t in threads:
        t.join(timeout=10)

    assert len(calls) == 1


def test_a_baseexception_does_not_wedge_the_provider(monkeypatch):
    """Ctrl+C during a fetch must not disable refreshing for the process.

    `KeyboardInterrupt` and `SystemExit` derive from BaseException, not
    Exception. An earlier version released the in-flight marker only in an
    `except Exception` and in a `finally` on an inner block, so both were
    skipped and the provider stayed marked as mid-fetch forever -- every later
    refresh returning None with nothing to indicate why. This suite found it by
    accident, via pytest.fail (also a BaseException); it is worth an
    intentional test.
    """
    def interrupted(*a, **k):
        raise KeyboardInterrupt

    monkeypatch.setattr(catalog, "_fetch", interrupted)
    with pytest.raises(KeyboardInterrupt):
        catalog.refresh_models("claude")

    monkeypatch.setattr(catalog, "_fetch",
                        _fake_fetch(_records("claude-opus-5", "claude-a", "claude-b")))
    assert catalog.refresh_models("claude", force=True) is not None


def test_refresh_if_stale_skips_a_fresh_cache(monkeypatch):
    monkeypatch.setattr(catalog, "_fetch",
                        _fake_fetch(_records("claude-opus-5", "claude-a", "claude-b")))
    assert catalog.refresh_if_stale("claude") is not None

    catalog.invalidate()
    monkeypatch.setattr(catalog, "_fetch",
                        lambda *a, **k: pytest.fail("refetched a fresh cache"))
    assert catalog.refresh_if_stale("claude") is None
