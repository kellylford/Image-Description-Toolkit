"""A batch stops on the first failure every remaining image would hit.

Seen in a real run: Claude Code's sign-in expired, and an 11,545-image batch
failed 533 images in 17 minutes, one by one, each with the same "OAuth session
expired" message. A signed-out provider, refused credentials or a provider that
is not set up fails every image identically, so the batch now stops at the
first one, keeps its resume state and says why.

The decision rides on a ProviderError kind. Claude Code confirms an expired
sign-in with `claude auth status`; its own sign-in wording is a fallback for
when the status still says signed in. Apple Intelligence flags setup problems
where it detects them.
"""

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(_ROOT), str(_ROOT / "imagedescriber")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from idt_core.providers import claude_code as cc  # noqa: E402


# --------------------------------------------------------------------------- #
# Claude Code: sign-in decided by `claude auth status`                         #
# --------------------------------------------------------------------------- #

@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setattr(cc, "find_claude", lambda: "claude")
    monkeypatch.setattr(cc, "_subscription_confirmed", True)
    monkeypatch.setattr(cc, "run_claude", lambda *a, **k: iter([
        ("result", {"is_error": True, "result": "Something went wrong"})]))
    return cc.ClaudeCodeProvider(model="haiku", check_auth=False)


def test_failure_while_signed_out_is_a_sign_in_error(provider, monkeypatch):
    monkeypatch.setattr(cc, "auth_status", lambda claude=None: {"loggedIn": False})
    with pytest.raises(cc.ClaudeCodeSignInError):
        provider.describe(b"x" * 10, "image/jpeg", "describe")
    assert cc._subscription_confirmed is False


def test_failure_while_signed_in_is_an_ordinary_error(provider, monkeypatch):
    monkeypatch.setattr(cc, "auth_status",
                        lambda claude=None: {"loggedIn": True, "authMethod": "claude.ai"})
    with pytest.raises(cc.ClaudeCodeError) as info:
        provider.describe(b"x" * 10, "image/jpeg", "describe")
    assert not isinstance(info.value, cc.ClaudeCodeSignInError)


def test_unreadable_status_reports_the_original_failure(provider, monkeypatch):
    def unreadable(claude=None):
        raise cc.ClaudeCodeError("Could not read 'claude auth status'")
    monkeypatch.setattr(cc, "auth_status", unreadable)
    with pytest.raises(cc.ClaudeCodeError, match="Something went wrong") as info:
        provider.describe(b"x" * 10, "image/jpeg", "describe")
    assert not isinstance(info.value, cc.ClaudeCodeSignInError)


def test_sign_in_error_is_still_a_claude_code_error():
    """Every existing `except ClaudeCodeError` keeps catching it."""
    assert issubclass(cc.ClaudeCodeSignInError, cc.ClaudeCodeError)


# --------------------------------------------------------------------------- #
# The kind survives the GUI's wrapping                                         #
# --------------------------------------------------------------------------- #

wx = pytest.importorskip("wx", reason="wxPython not installed in this environment")

import workers_wx  # noqa: E402
from ai_providers import ErrorKind, ProviderError  # noqa: E402


def test_kind_found_through_wrapping():
    try:
        try:
            raise ProviderError("Claude Code: not signed in", kind=ErrorKind.AUTH)
        except Exception as e:
            raise Exception(f"AI processing failed: {e}") from e
    except Exception as wrapped:
        assert workers_wx._provider_error_kind(wrapped) == ErrorKind.AUTH


def test_plain_failure_has_no_kind():
    assert workers_wx._provider_error_kind(ValueError("bad image")) is None


def test_only_sign_in_and_setup_failures_halt_a_run():
    assert workers_wx.RUN_FATAL_KINDS == {ErrorKind.AUTH, ErrorKind.UNAVAILABLE}
    for kind in (ErrorKind.RATE_LIMIT, ErrorKind.SERVER_ERROR, ErrorKind.TIMEOUT,
                 ErrorKind.INVALID_REQUEST, ErrorKind.UNKNOWN):
        assert kind not in workers_wx.RUN_FATAL_KINDS


# --------------------------------------------------------------------------- #
# The batch worker stops at the first run-fatal failure                        #
# --------------------------------------------------------------------------- #

class _FakeImageWorker:
    """Stands in for ProcessingWorker. `script` maps file name -> outcome."""
    script = {}
    seen = []

    def __init__(self, parent, file_path, *a, **k):
        self.file_path = file_path
        self.result_input_tokens = self.result_output_tokens = 0
        outcome = self.script.get(Path(file_path).name, "ok")
        self.result_ok = outcome == "ok"
        self.result_error = None if self.result_ok else f"failed: {outcome}"
        self.result_kind = None if outcome in ("ok", "plain") else outcome

    def start(self):
        _FakeImageWorker.seen.append(Path(self.file_path).name)

    def join(self):
        pass


def _run_batch(monkeypatch, names, script):
    posted = []
    monkeypatch.setattr(workers_wx, "ProcessingWorker", _FakeImageWorker)
    monkeypatch.setattr(workers_wx.wx, "PostEvent", lambda win, evt: posted.append(evt))
    _FakeImageWorker.script = script
    _FakeImageWorker.seen = []
    worker = workers_wx.BatchProcessingWorker(
        None, [f"C:/p/{n}" for n in names], "claude-code", "haiku", "narrative",
        "", None, False)
    worker.run()
    done = [e for e in posted if isinstance(e, workers_wx.WorkflowCompleteEventData)]
    assert len(done) == 1
    return done[0], worker


def test_batch_halts_on_first_sign_in_failure(monkeypatch):
    names = [f"{i}.jpg" for i in range(6)]
    done, worker = _run_batch(monkeypatch, names, {"1.jpg": "ok", "2.jpg": ErrorKind.AUTH})
    assert _FakeImageWorker.seen == ["0.jpg", "1.jpg", "2.jpg"]
    assert done.halted == "failed: auth"
    assert done.worker is worker


def test_batch_halts_when_provider_unavailable(monkeypatch):
    done, _ = _run_batch(monkeypatch, ["a.jpg", "b.jpg"], {"a.jpg": ErrorKind.UNAVAILABLE})
    assert _FakeImageWorker.seen == ["a.jpg"]
    assert done.halted


def test_ordinary_failures_do_not_halt(monkeypatch):
    names = ["a.jpg", "b.jpg", "c.jpg"]
    done, _ = _run_batch(monkeypatch, names,
                         {"a.jpg": "plain", "b.jpg": ErrorKind.RATE_LIMIT})
    assert _FakeImageWorker.seen == names
    assert done.halted is None


# --------------------------------------------------------------------------- #
# Found by the second independent review                                       #
# --------------------------------------------------------------------------- #

def test_sign_in_wording_is_whole_words_only():
    for text in ("Failed to authenticate", "OAuth session expired", "Please log in",
                 "Please login"):
        assert cc._SIGN_IN_WORDING.search(text), text
    for text in ("backlog in queue", "catalog index", "dialog in progress"):
        assert not cc._SIGN_IN_WORDING.search(text), text


def test_adapter_keeps_claude_codes_message_and_halts(monkeypatch, tmp_path):
    """Signed out must read as Claude Code's own message, not "check API key",
    and still carry a kind that stops a batch."""
    import ai_providers
    import idt_core.converter as conv

    class _SignedOut:
        def __init__(self, *a, **k):
            pass

        def describe(self, *a, **k):
            raise cc.ClaudeCodeSignInError(
                "Claude Code: OAuth session expired — run: claude auth login")
    monkeypatch.setattr(cc, "ClaudeCodeProvider", _SignedOut)
    monkeypatch.setattr(conv, "load_for_api", lambda p: (b"x", "image/jpeg"))
    img = tmp_path / "a.jpg"
    img.write_bytes(b"x")
    with pytest.raises(ProviderError) as info:
        ai_providers.ClaudeCodeProvider().describe_image(str(img), "describe", "haiku")
    assert info.value.kind in workers_wx.RUN_FATAL_KINDS
    assert "OAuth session expired" in str(info.value)
    assert "API key" not in str(info.value)


def test_real_processing_worker_records_kind_and_flags_event(monkeypatch):
    posted = []
    monkeypatch.setattr(workers_wx.wx, "PostEvent", lambda win, evt: posted.append(evt))
    w = workers_wx.ProcessingWorker(None, "C:/p/a.jpg", "claude-code", "haiku",
                                    "narrative", "", None)

    def fail(*a, **k):
        try:
            raise ProviderError("signed out", kind=ErrorKind.UNAVAILABLE)
        except Exception as e:
            raise Exception(f"AI processing failed: {e}") from e
    monkeypatch.setattr(w, "_process_with_ai", fail)
    monkeypatch.setattr(w, "_inject_exif_context", lambda p: (p, ""), raising=False)
    w.run()
    assert w.result_ok is False
    assert w.result_kind == ErrorKind.UNAVAILABLE
    failed = [e for e in posted if isinstance(e, workers_wx.ProcessingFailedEventData)]
    assert failed and failed[0].run_fatal


def test_apple_setup_flag_halts_but_server_crash_does_not(monkeypatch, tmp_path):
    import ai_providers
    from idt_core.providers import apple
    import idt_core.converter as conv
    monkeypatch.setattr(conv, "load_for_api", lambda p: (b"x", "image/jpeg"))
    img = tmp_path / "a.jpg"
    img.write_bytes(b"x")

    def run_with(exc):
        class _P:
            def __init__(self, *a, **k):
                pass

            def describe(self, *a, **k):
                raise exc
        monkeypatch.setattr(apple, "AppleProvider", _P)
        prov = ai_providers.AppleProvider()
        try:
            prov.describe_image(str(img), "describe", "")
        except ProviderError as e:
            return e.kind
        return None

    crash = apple.AppleFMError("Apple Intelligence server stopped: /usr/bin/fm exited")
    setup = apple.AppleFMError("Run sudo fm license", setup=True)
    assert run_with(setup) == ErrorKind.UNAVAILABLE
    assert run_with(crash) not in workers_wx.RUN_FATAL_KINDS


# --------------------------------------------------------------------------- #
# Identical failures in a row (no run-fatal kind: used-up plan, Ollama down)   #
# --------------------------------------------------------------------------- #

def test_ten_identical_failures_in_a_row_halt(monkeypatch):
    names = [f"{i}.jpg" for i in range(15)]
    script = {n: "plain" for n in names}   # same error text every time
    done, _ = _run_batch(monkeypatch, names, script)
    assert len(_FakeImageWorker.seen) == workers_wx.SAME_FAILURE_STREAK
    assert done.halted == "failed: plain"
    # The whole streak goes back in the queue, not just the last image.
    assert len(done.halted_files) == workers_wx.SAME_FAILURE_STREAK


def test_different_failures_do_not_halt(monkeypatch):
    names = [f"{i}.jpg" for i in range(15)]
    script = {n: f"plain-{i}" for i, n in enumerate(names)}   # all differ
    done, _ = _run_batch(monkeypatch, names, script)
    assert _FakeImageWorker.seen == names
    assert done.halted is None


def test_a_success_resets_the_streak(monkeypatch):
    names = [f"{i}.jpg" for i in range(19)]
    script = {n: "plain" for n in names}
    script["9.jpg"] = "ok"                 # 9 failures, a success, 9 failures
    done, _ = _run_batch(monkeypatch, names, script)
    assert _FakeImageWorker.seen == names
    assert done.halted is None
