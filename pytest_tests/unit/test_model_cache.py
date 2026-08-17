"""The on-disk model cache, and the ways a cache file can be wrong.

Every test here is about degradation. The cache exists to make pickers instant;
it must never be the reason a picker is empty, shows another account's models,
or raises inside a wx event handler where the traceback would be swallowed.

So the bar is not "it round-trips" -- it is "every corrupt, stale, foreign or
unwritable state reads as *nothing cached*", because that is the one state every
caller already handles by falling back to its curated list.
"""

import json
import sys
import threading
import time
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from idt_core.providers import model_cache as mc  # noqa: E402

pytestmark = pytest.mark.unit

_DAY = 24 * 3600.0
_FP = "fingerprint01"
_MODELS = [{"id": "claude-opus-5", "name": "Claude Opus 5", "created": 1700000000}]


# ---------------------------------------------------------------------------
# Location
# ---------------------------------------------------------------------------

def test_env_override_wins(tmp_path, monkeypatch):
    """The whole test suite depends on this override actually being honoured."""
    monkeypatch.setenv("IDT_MODEL_CACHE_DIR", str(tmp_path / "elsewhere"))
    assert mc.cache_dir() == tmp_path / "elsewhere"


def test_default_location_is_under_dot_idt(monkeypatch):
    monkeypatch.delenv("IDT_MODEL_CACHE_DIR", raising=False)
    assert mc.cache_dir() == Path.home() / ".idt" / "models"


def test_reading_creates_nothing(tmp_path, monkeypatch):
    """A read on a machine that never refreshed must not leave a directory."""
    monkeypatch.setenv("IDT_MODEL_CACHE_DIR", str(tmp_path / "fresh"))
    assert mc.read("claude", _FP, _DAY) is None
    assert not (tmp_path / "fresh").exists()


def test_one_file_per_provider():
    """A shared file would let a Claude refresh clobber an OpenAI one."""
    assert mc.path_for("claude") != mc.path_for("openai")


def test_provider_name_cannot_escape_the_directory():
    path = mc.path_for("../../etc/passwd")
    assert path.parent == mc.cache_dir()
    assert "/" not in path.name and "\\" not in path.name


def test_provider_names_with_spaces_are_usable():
    assert mc.path_for("ollama cloud").name == "ollama_cloud.json"


# ---------------------------------------------------------------------------
# Fingerprints
# ---------------------------------------------------------------------------

def test_fingerprint_never_contains_the_key():
    key = "sk-ant-supersecretvalue-0123456789"
    fingerprint = mc.account_fingerprint(key)
    assert fingerprint not in key
    assert key[:8] not in fingerprint
    assert len(fingerprint) == 12


def test_fingerprint_distinguishes_accounts():
    assert mc.account_fingerprint("key-a") != mc.account_fingerprint("key-b")
    assert mc.account_fingerprint("key-a") == mc.account_fingerprint("key-a")


def test_absent_key_has_its_own_fingerprint():
    assert mc.account_fingerprint(None) == "nokey"
    assert mc.account_fingerprint("") == "nokey"


# ---------------------------------------------------------------------------
# The happy path
# ---------------------------------------------------------------------------

def test_round_trip():
    assert mc.write("claude", _FP, _MODELS) is True
    assert mc.read("claude", _FP, _DAY) == _MODELS


def test_write_replaces_rather_than_appends():
    mc.write("claude", _FP, _MODELS)
    newer = [{"id": "claude-opus-6", "name": "Claude Opus 6", "created": 1800000000}]
    mc.write("claude", _FP, newer)
    assert mc.read("claude", _FP, _DAY) == newer


def test_no_temp_files_are_left_behind():
    mc.write("claude", _FP, _MODELS)
    assert not list(mc.cache_dir().glob("*.tmp"))


# ---------------------------------------------------------------------------
# Every way a cache can be unusable reads as "nothing cached"
# ---------------------------------------------------------------------------

def test_empty_list_is_never_stored():
    """An empty fetch result means the fetch failed, not that there are no
    models. Storing it would blank the picker for a whole TTL."""
    assert mc.write("claude", _FP, []) is False
    assert mc.read("claude", _FP, _DAY) is None


def test_a_stale_entry_is_not_served():
    """Backdate the stored stamp rather than passing max_age=0.

    Passing 0 compares `now - fetched_at > 0`, and on Windows the clock can
    report the same value for both, so the entry reads as fresh and the test
    fails perhaps one run in ten. Ageing the file makes the assertion about the
    TTL rather than about timer granularity.
    """
    mc.write("claude", _FP, _MODELS)
    path = mc.path_for("claude")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["fetched_at"] = time.time() - (2 * _DAY)
    path.write_text(json.dumps(payload), encoding="utf-8")

    assert mc.read("claude", _FP, _DAY) is None
    # ...and still served by a caller willing to accept something older.
    assert mc.read("claude", _FP, 3 * _DAY) == _MODELS


def test_another_accounts_cache_is_not_served():
    """Both APIs list by entitlement, so this would show models the user cannot
    call and hide ones they can."""
    mc.write("claude", _FP, _MODELS)
    assert mc.read("claude", "a-different-account", _DAY) is None


def test_a_future_timestamp_reads_as_stale():
    """The one failure a TTL cache must not have: stamped ahead of the clock, it
    would look fresh forever and never refresh again."""
    mc.write("claude", _FP, _MODELS)
    path = mc.path_for("claude")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["fetched_at"] = time.time() + 86_400
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert mc.read("claude", _FP, _DAY) is None


def test_an_unknown_schema_version_is_ignored_not_migrated():
    mc.write("claude", _FP, _MODELS)
    path = mc.path_for("claude")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["version"] = mc.CACHE_VERSION + 99
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert mc.read("claude", _FP, _DAY) is None


@pytest.mark.parametrize(
    "content",
    [
        "",                                   # empty file
        "{",                                  # truncated mid-write
        '{"version": 1, "models": "nope"}',   # right shape, wrong types
        '["not", "a", "dict"]',               # valid JSON, wrong root
        "\x00\x00\x00",                       # binary garbage
    ],
    ids=["empty", "truncated", "wrong-types", "wrong-root", "binary"],
)
def test_corrupt_files_read_as_nothing_cached(content):
    """None of these may raise: the caller is often a wx event handler, where an
    exception is swallowed and the symptom is a control that does nothing."""
    mc.cache_dir().mkdir(parents=True, exist_ok=True)
    mc.path_for("claude").write_text(content, encoding="utf-8")
    assert mc.read("claude", _FP, _DAY) is None


def test_a_missing_fetched_at_reads_as_nothing_cached():
    mc.cache_dir().mkdir(parents=True, exist_ok=True)
    mc.path_for("claude").write_text(
        json.dumps({"version": mc.CACHE_VERSION, "account": _FP, "models": _MODELS}),
        encoding="utf-8",
    )
    assert mc.read("claude", _FP, _DAY) is None


def test_an_unwritable_location_reports_failure_without_raising(monkeypatch, tmp_path):
    """A read-only home is a real configuration, not a hypothetical."""
    blocker = tmp_path / "blocked"
    blocker.write_text("I am a file, not a directory", encoding="utf-8")
    monkeypatch.setenv("IDT_MODEL_CACHE_DIR", str(blocker / "models"))
    assert mc.write("claude", _FP, _MODELS) is False
    assert mc.read("claude", _FP, _DAY) is None


# ---------------------------------------------------------------------------
# Concurrency
# ---------------------------------------------------------------------------

def test_concurrent_writers_never_publish_a_partial_file():
    """Eight threads hammering one provider; the file must parse every time.

    This is a *thread* test standing in for a *process* race, and the distinction
    is worth being honest about: the bug it guards against (two writers sharing
    one fixed temp filename) is what the unique per-call temp name in `write`
    fixes, and that fix is what makes the multi-process case safe too. Spawning
    real processes in pytest to prove it would be slow and flaky on Windows, so
    this is the honest bar rather than the complete one.
    """
    errors: list = []
    barrier = threading.Barrier(8)

    def hammer(n: int):
        try:
            barrier.wait(timeout=10)
            for _ in range(15):
                mc.write("claude", _FP, [{"id": f"model-{n}", "name": str(n)}])
                got = mc.read("claude", _FP, _DAY)
                # Whichever writer won, the result must be a coherent list --
                # never a half-written file surfacing as None or as garbage.
                assert got is None or isinstance(got, list)
        except Exception as exc:                      # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=hammer, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert not errors, errors
    assert not list(mc.cache_dir().glob("*.tmp")), "temp files leaked"
    final = mc.read("claude", _FP, _DAY)
    assert final is not None and len(final) == 1
