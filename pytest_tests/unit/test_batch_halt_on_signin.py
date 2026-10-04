"""A batch stops on the first failure every remaining image would hit.

Seen in a real run: Claude Code's sign-in expired, and an 11,545-image batch
failed 533 images in 17 minutes, one by one, each with the same "OAuth session
expired" message. A signed-out provider, refused credentials or a provider that
is not set up fails every image identically, so the batch now stops at the
first one, keeps its resume state and says why.

Classification is structural (a ProviderError kind; `claude auth status` for
Claude Code), never by matching error wording.
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
