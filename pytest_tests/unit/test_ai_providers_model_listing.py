"""ImageDescriber's model-listing wrappers.

Everything under ``imagedescriber/`` reaches model information through
``ai_providers``, never through ``idt_core`` directly, because these modules are
imported flat in a frozen build and as a package in development -- so a direct
``idt_core`` import inside a dialog is a hidden import that works locally and
fails only in the packaged app. That makes these three functions the seam every
picker depends on, and worth testing on their own rather than only through the
dialogs.

The behaviour that matters: they never raise. Their callers are wx event
handlers, where an exception is swallowed and the visible symptom is a model
picker that is simply empty, with no error anywhere.
"""

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_APP_DIR = _ROOT / "imagedescriber"
for _p in (str(_ROOT), str(_APP_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from idt_core.providers import catalog  # noqa: E402
from idt_core.providers.claude import CLAUDE_MODELS  # noqa: E402

import ai_providers  # noqa: E402

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(catalog, "_api_key_for", lambda _p: "test-key")
    monkeypatch.setattr(
        catalog, "_fetch",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no network in tests")),
    )
    catalog.invalidate()
    yield
    catalog.invalidate()


# ---------------------------------------------------------------------------
# list_models
# ---------------------------------------------------------------------------

def test_list_models_returns_the_curated_list_offline():
    entries = ai_providers.list_models("claude")
    assert [e.id for e in entries] == list(CLAUDE_MODELS)


def test_list_models_keeps_a_model_that_is_no_longer_listed():
    """The user's saved model must remain selectable rather than silently
    dropping them onto whatever is first."""
    entries = ai_providers.list_models("claude", keep=["claude-retired-9"])
    assert "claude-retired-9" in [e.id for e in entries]


def test_list_models_ignores_blank_keep_entries():
    """Callers pass the current selection straight through, and it is often ''."""
    entries = ai_providers.list_models("claude", keep=["", None])
    assert [e.id for e in entries] == list(CLAUDE_MODELS)


def test_list_models_returns_empty_rather_than_raising(monkeypatch):
    """A wx handler cannot report an exception, so this must not throw one."""
    monkeypatch.setattr(
        catalog, "cached_models",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("catalog is unhappy")),
    )
    assert ai_providers.list_models("claude") == []


def test_list_models_does_not_reach_the_network(monkeypatch):
    """It is called on the UI thread; a blocking call here freezes the window."""
    import socket

    monkeypatch.setattr(
        socket, "create_connection",
        lambda *a, **k: pytest.fail("list_models opened a socket"),
    )
    assert ai_providers.list_models("openai")


# ---------------------------------------------------------------------------
# model_info
# ---------------------------------------------------------------------------

def test_model_info_carries_the_curated_metadata():
    entry = ai_providers.model_info("claude", "claude-opus-5")
    assert entry.name == "Claude Opus 5"
    assert entry.context_window == 200_000


def test_model_info_for_an_unknown_model_invents_nothing():
    entry = ai_providers.model_info("claude", "claude-not-a-real-model")
    assert entry.context_window is None
    assert entry.max_output is None


# ---------------------------------------------------------------------------
# get_available_models, the two that used to be wrong
# ---------------------------------------------------------------------------

def test_claude_get_available_models_is_sorted_cheapest_first():
    """This GUI orders haiku -> sonnet -> opus, deliberately differing from the
    catalog's curated best-first order. Both orderings are wanted, each in its
    own place, so the sort must survive the switch to the catalog.

    Needs the SDK: without it the provider returns [] by design, and the
    assertion below reads as a sorting regression when it is really a missing
    dependency. Skipping is the honest result -- CI installs the SDK and runs
    the check for real.
    """
    pytest.importorskip("anthropic")
    provider = ai_providers.ClaudeProvider(api_key="test-key")
    models = provider.get_available_models()
    assert models, "no models returned"
    tiers = [m for m in models if "haiku" in m or "opus" in m]
    if tiers:
        assert "haiku" in tiers[0], f"expected cheapest first, got {tiers[0]}"


def test_openai_get_available_models_is_no_longer_capped_by_the_static_list(monkeypatch):
    """The bug this replaced: the live response was intersected with the
    hardcoded list, so a listing could only ever subtract from it and a newly
    released model could never appear.

    Needs the SDK for the same reason as the Claude test above.
    """
    pytest.importorskip("openai")
    monkeypatch.setattr(
        catalog, "_fetch",
        lambda *a, **k: [{"id": i, "name": "", "created": n} for n, i in enumerate(
            ["gpt-5.2", "gpt-4o", "gpt-9-brand-new"])],
    )
    catalog.invalidate()
    catalog.refresh_models("openai", force=True)

    provider = ai_providers.OpenAIProvider(api_key="test-key")
    assert "gpt-9-brand-new" in provider.get_available_models()


# ---------------------------------------------------------------------------
# refresh_models_from_apis
# ---------------------------------------------------------------------------

def test_refresh_reports_what_actually_refreshed(monkeypatch):
    monkeypatch.setattr(
        catalog, "_fetch",
        lambda *a, **k: [{"id": i, "name": "", "created": n} for n, i in enumerate(
            ["claude-opus-5", "claude-a", "claude-b"])],
    )
    assert ai_providers.refresh_models_from_apis(("claude",)) == {"claude": 3}


def test_refresh_is_silent_when_nothing_can_be_refreshed():
    """No key, a fresh cache, or an unreachable endpoint are all ordinary --
    none of them is an error worth interrupting anyone about."""
    assert ai_providers.refresh_models_from_apis(("claude", "openai")) == {}


def test_refresh_swallows_an_unexpected_failure(monkeypatch):
    """This runs on the startup worker thread, where an escaping exception
    would be a thread dying silently during app launch -- and the app would
    then be missing its cached model lists with nothing to say why."""
    monkeypatch.setattr(
        catalog, "refresh_if_stale",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("catalog exploded")),
    )
    assert ai_providers.refresh_models_from_apis(("claude",)) == {}


def test_refresh_continues_past_a_failing_provider(monkeypatch):
    """One provider failing must not stop the other from refreshing."""
    def selective(provider, **kwargs):
        if provider == "claude":
            raise RuntimeError("claude is unhappy")
        return [object(), object()]

    monkeypatch.setattr(catalog, "refresh_if_stale", selective)
    assert ai_providers.refresh_models_from_apis(("claude", "openai")) == {"openai": 2}
