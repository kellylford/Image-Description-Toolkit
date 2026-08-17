"""The model catalog: merge rules, ordering, and the two hot-path invariants.

Issue #267 replaced two hardcoded model lists with a live listing merged against
curated metadata. Two properties of that merge are load-bearing, and neither is
visible from the outside until something has already gone wrong:

* **Curated always wins.** A live listing says which models exist. It must never
  decide what their limits are. If a fetched entry for ``gpt-4o`` could null out
  its recorded context window, the chat token budgeter would drop to a flat
  guess and nothing anywhere would report it.
* **The read path does no I/O.** ``registry.model_limits`` runs on every chat
  turn, so a ``stat()`` of the cache file per turn is already too much.

The exact-value assertions in ``test_chat_providers.py`` and
``test_chat_engine.py`` are what break when the first one is violated. These
tests exist so that the *reason* is visible when they do.
"""

import sys
import threading
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from idt_core.providers import catalog, model_cache  # noqa: E402
from idt_core.providers.claude import CLAUDE_MODELS  # noqa: E402
from idt_core.providers.openai_provider import OPENAI_MODELS  # noqa: E402
from idt_core.providers.registry import model_limits  # noqa: E402

pytestmark = pytest.mark.unit


#: Stand-in for the developer's real key. Pinning it matters: the cache is keyed
#: by an account fingerprint, so without this these tests would pass or fail
#: depending on whether whoever ran them happens to have ANTHROPIC_API_KEY set.
_TEST_KEY = "test-key-not-a-real-credential"


@pytest.fixture(autouse=True)
def clear_memo(monkeypatch):
    """Reset the process memo and pin key resolution.

    The memo is process-level by design, so tests must not inherit it. Key
    resolution is neutralised at ``catalog._api_key_for`` rather than by clearing
    environment variables, because ``keys.resolve_api_key`` also reads the OS
    credential store and a config file -- patching only the environment would
    leave the real machine leaking in through the other two.
    """
    monkeypatch.setattr(catalog, "_api_key_for", lambda _provider: _TEST_KEY)
    catalog.invalidate()
    yield
    catalog.invalidate()


@pytest.fixture
def cache_fingerprint():
    """The fingerprint the catalog will look for, given the pinned key."""
    return model_cache.account_fingerprint(_TEST_KEY)


def _live(*specs):
    """Build live listing records: ``_live(("gpt-4o", "GPT-4o", 100))``."""
    return [{"id": i, "name": n, "created": c} for i, n, c in specs]


# ---------------------------------------------------------------------------
# Curated-only behaviour: unchanged from before this module existed
# ---------------------------------------------------------------------------

def test_with_no_cache_the_list_is_exactly_the_curated_one():
    """First run, no key, no network -- the picker must look like it always did."""
    assert [e.id for e in catalog.cached_models("claude")] == list(CLAUDE_MODELS)
    assert [e.id for e in catalog.cached_models("openai")] == list(OPENAI_MODELS)


def test_curated_order_is_preserved():
    """Hand-tuned best-first, and several pickers select index 0."""
    entries = catalog.curated_models("claude")
    assert [e.id for e in entries] == list(CLAUDE_MODELS)
    assert entries[0].recommended is True


def test_aliases_resolve():
    assert catalog.cached_models("anthropic") == catalog.cached_models("claude")
    assert catalog.model_entry("Anthropic", "claude-opus-5").provider == "claude"


def test_unknown_provider_is_empty_not_an_exception():
    assert catalog.cached_models("no-such-provider") == []


def test_returned_lists_are_copies():
    """ImageDescriber sorts Claude models cheapest-first, deliberately differing
    from the curated order. It must not be sorting the memo."""
    first = catalog.cached_models("claude")
    first.sort(key=lambda e: e.id)
    assert [e.id for e in catalog.cached_models("claude")] == list(CLAUDE_MODELS)


# ---------------------------------------------------------------------------
# INVARIANT 1: curated always wins
# ---------------------------------------------------------------------------

def test_a_live_entry_cannot_overwrite_recorded_limits():
    """The single most important test in this file.

    A live listing reports no context window at all, so if it were allowed to
    build the entry for a model we have figures for, those figures would become
    None and budgeting would fall back to a flat guess -- silently.
    """
    merged = catalog.merge("openai", _live(("gpt-4o", "Whatever The API Says", 1)))
    entry = next(e for e in merged if e.id == "gpt-4o")

    assert entry.context_window == 128_000
    assert entry.max_output == 16_384
    assert entry.name == "GPT-4o"           # curated name, not the API's
    assert entry.source == "curated"


def test_curated_wins_for_every_metadata_field():
    merged = catalog.merge("claude", _live(("claude-opus-5", "Bogus", 1)))
    entry = next(e for e in merged if e.id == "claude-opus-5")

    assert entry.name == "Claude Opus 5"
    assert entry.cost == "$$$$"
    assert entry.recommended is True
    assert entry.description and entry.description != catalog.NEW_MODEL_NOTE


def test_model_limits_still_matches_the_recorded_figures():
    """Guards the same numbers test_chat_providers.py asserts, from this side."""
    assert model_limits("openai", "gpt-4o") == (128_000, 16_384)
    assert model_limits("openai", "gpt-5.2")[0] == 400_000
    assert model_limits("claude", "claude-opus-5") == (200_000, 128_000)


# ---------------------------------------------------------------------------
# INVARIANT 2: the hot path does no I/O
# ---------------------------------------------------------------------------

def test_model_limits_never_touches_the_disk(monkeypatch):
    """Called on every chat turn. Even a stat() per turn is wrong."""
    def explode(*_args, **_kwargs):
        raise AssertionError("model_limits reached the disk cache")

    monkeypatch.setattr(model_cache, "read", explode)
    monkeypatch.setattr(model_cache, "path_for", explode)

    for _ in range(100):
        assert model_limits("claude", "claude-opus-5") == (200_000, 128_000)
        assert model_limits("openai", "no-such-model") == (None, None)


def test_cached_models_makes_no_network_call(monkeypatch):
    """Called from wx event handlers, where a hang freezes the window."""
    import socket

    def explode(*_args, **_kwargs):
        raise AssertionError("cached_models opened a socket")

    monkeypatch.setattr(socket, "create_connection", explode)
    assert catalog.cached_models("claude")


def test_the_disk_is_read_once_per_process(monkeypatch):
    calls = []
    real_read = model_cache.read

    def counting_read(*args, **kwargs):
        calls.append(args[0])
        return real_read(*args, **kwargs)

    monkeypatch.setattr(model_cache, "read", counting_read)
    for _ in range(10):
        catalog.cached_models("claude")
    assert calls.count("claude") == 1


# ---------------------------------------------------------------------------
# Unknown models
# ---------------------------------------------------------------------------

def test_an_unrecognised_live_model_appears_with_no_invented_numbers():
    """The whole point of the issue: visible the day it ships."""
    merged = catalog.merge("claude", _live(("claude-opus-6", "Claude Opus 6", 9)))
    entry = next(e for e in merged if e.id == "claude-opus-6")

    assert entry.source == "live"
    assert entry.is_known is False
    assert entry.context_window is None
    assert entry.max_output is None
    assert entry.supports_vision is None


def test_an_unknown_model_flows_through_the_documented_fallback():
    """End-to-end proof of the None contract, through the real caller."""
    from idt_core.chat.tokens import DEFAULT_CONTEXT_WINDOWS, context_window_for

    assert model_limits("claude", "claude-opus-6") == (None, None)
    assert context_window_for("claude", "claude-opus-6") == DEFAULT_CONTEXT_WINDOWS["claude"]


def test_a_new_model_is_labelled_in_prose():
    """A screen reader reads this, so it is words rather than a symbol."""
    entry = catalog.merge("claude", _live(("claude-opus-6", "Claude Opus 6", 9)))[-1]
    assert entry.display() == f"Claude Opus 6 ({catalog.NEW_MODEL_NOTE})"


def test_a_live_model_without_a_name_falls_back_to_its_id():
    """OpenAI's listing supplies no display name at all."""
    merged = catalog.merge("openai", _live(("gpt-6-turbo", "", 9)))
    assert merged[-1].name == "gpt-6-turbo"


# ---------------------------------------------------------------------------
# Ordering and retirement
# ---------------------------------------------------------------------------

def test_curated_first_then_live_only_newest_first():
    merged = catalog.merge(
        "claude",
        _live(
            ("claude-opus-6", "Claude Opus 6", 100),
            ("claude-opus-5", "Claude Opus 5", 50),
            ("claude-zeta", "Claude Zeta", 200),
        ),
    )
    assert [e.id for e in merged] == ["claude-opus-5", "claude-zeta", "claude-opus-6"]


def test_a_retired_model_drops_out_of_the_list():
    """Second half of the issue: a model the API no longer offers must stop
    being offered, rather than failing at request time."""
    merged = catalog.merge("claude", _live(("claude-opus-5", "Claude Opus 5", 1)))
    ids = [e.id for e in merged]
    assert "claude-opus-4-1-20250805" in CLAUDE_MODELS
    assert "claude-opus-4-1-20250805" not in ids


def test_a_retired_model_is_still_resolvable():
    """Old .idtw workspaces and chat sessions reference these by id and must
    still render a real name rather than a raw string."""
    entry = catalog.model_entry("claude", "claude-opus-4-1-20250805")
    assert entry.name == "Claude Opus 4.1"
    assert entry.context_window == 200_000


def test_an_empty_live_list_is_not_treated_as_retirement():
    """Serving the offline fallback must never look like 'everything retired'."""
    assert [e.id for e in catalog.merge("claude", [])] == []
    assert [e.id for e in catalog.cached_models("claude")] == list(CLAUDE_MODELS)


# ---------------------------------------------------------------------------
# keep=: the user's own selection survives every filter
# ---------------------------------------------------------------------------

def test_keep_rescues_a_model_the_listing_dropped():
    """Otherwise a picker silently falls back to index 0 and the user's model
    changes with no message anywhere."""
    merged = catalog.merge(
        "claude",
        _live(("claude-opus-5", "Claude Opus 5", 1)),
        keep=["claude-opus-4-1-20250805"],
    )
    ids = [e.id for e in merged]
    assert "claude-opus-4-1-20250805" in ids


def test_keep_rescues_a_model_nothing_at_all_knows_about():
    merged = catalog.merge("openai", _live(("gpt-5.2", "GPT-5.2", 1)),
                           keep=["ft:gpt-4o:acme::abc123"])
    assert "ft:gpt-4o:acme::abc123" in [e.id for e in merged]


def test_cached_models_keep_marks_the_entry_rather_than_hiding_it():
    entries = catalog.cached_models("claude", keep=["claude-legacy-9"])
    entry = next(e for e in entries if e.id == "claude-legacy-9")
    assert entry.source == "retired"


def test_keep_does_not_duplicate_an_entry_already_present():
    entries = catalog.cached_models("claude", keep=["claude-opus-5"])
    assert [e.id for e in entries].count("claude-opus-5") == 1


def test_multiple_kept_models_keep_a_stable_order():
    """These append straight into a picker, so their order must not vary between
    one dialog opening and the next -- which iterating a set would do."""
    live = _live(("claude-opus-5", "Claude Opus 5", 1))
    kept = ["claude-zzz", "claude-aaa", "claude-mmm"]
    first = [e.id for e in catalog.merge("claude", live, keep=kept)]
    for _ in range(5):
        assert [e.id for e in catalog.merge("claude", live, keep=kept)] == first
    assert first[-3:] == kept, "kept models should follow the order given"


def test_keep_is_deduplicated():
    entries = catalog.merge("claude", _live(("claude-opus-5", "Opus", 1)),
                            keep=["claude-dup", "claude-dup"])
    assert [e.id for e in entries].count("claude-dup") == 1


# ---------------------------------------------------------------------------
# Cache integration and concurrency
# ---------------------------------------------------------------------------

def test_a_cached_listing_is_used_when_present(cache_fingerprint):
    model_cache.write("claude", cache_fingerprint,
                      [{"id": "claude-opus-5", "name": "Claude Opus 5", "created": 1},
                       {"id": "claude-opus-6", "name": "Claude Opus 6", "created": 2}])
    catalog.invalidate()

    ids = [e.id for e in catalog.cached_models("claude")]
    assert ids == ["claude-opus-5", "claude-opus-6"]


def test_another_accounts_cache_is_ignored(cache_fingerprint):
    """Switching keys must not serve the previous account's entitlements."""
    model_cache.write("claude", "someone-elses-account",
                      [{"id": "claude-only-they-have", "name": "Theirs", "created": 1}])
    catalog.invalidate()

    ids = [e.id for e in catalog.cached_models("claude")]
    assert "claude-only-they-have" not in ids
    assert ids == list(CLAUDE_MODELS)


def test_a_corrupt_cache_degrades_to_curated():
    model_cache.cache_dir().mkdir(parents=True, exist_ok=True)
    model_cache.path_for("claude").write_text("{ truncated", encoding="utf-8")
    catalog.invalidate()
    assert [e.id for e in catalog.cached_models("claude")] == list(CLAUDE_MODELS)


def test_concurrent_readers_agree(monkeypatch):
    """Several dialogs can open at once; check -> read -> store is not atomic."""
    results: list = []
    errors: list = []
    barrier = threading.Barrier(8)

    def read_it():
        try:
            barrier.wait(timeout=10)
            results.append(tuple(e.id for e in catalog.cached_models("claude")))
        except Exception as exc:                      # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=read_it) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert not errors, errors
    assert len(set(results)) == 1, "readers disagreed about the model list"
