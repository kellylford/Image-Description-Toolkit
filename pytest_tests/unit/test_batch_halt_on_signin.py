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
        self.result_signature = (None if self.result_ok
                                 else (self.result_kind, None, self.result_error))
        self.result_per_image = outcome == "declined"

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


def test_refusals_below_the_cap_do_not_halt(monkeypatch):
    """#352: Apple's guardrails refuse some photos (taxidermy, #337) with an
    identical message. Ten in a row, as a trip's photos can be, halted the
    whole batch as though Apple Intelligence were down."""
    names = [f"{i}.jpg" for i in range(15)]
    done, _ = _run_batch(monkeypatch, names, {n: "declined" for n in names})
    assert _FakeImageWorker.seen == names
    assert done.halted is None


def test_a_prompt_refused_on_every_image_halts(monkeypatch):
    """PR 353 review: exempt from the identical-failure rule, a prompt the
    guardrails refuse on every image ground through the whole library."""
    names = [f"{i}.jpg" for i in range(40)]
    done, _ = _run_batch(monkeypatch, names, {n: "declined" for n in names})
    assert len(_FakeImageWorker.seen) == workers_wx.REFUSAL_STREAK
    assert done.halted == "failed: declined"
    # Declined, not untried: they stay failed rather than go back in the
    # queue, or resuming hits the same refusals first and halts every time
    # (PR 353 Windows review).
    assert done.halted_refusals
    assert not done.halted_streak
    assert done.halted_files == []


def test_resuming_after_a_refusal_halt_carries_on_past_them(monkeypatch):
    """The resumed batch is the images not yet tried: it gets past the 25."""
    names = [f"{i}.jpg" for i in range(40)]
    script = {n: "declined" for n in names[:workers_wx.REFUSAL_STREAK]}
    done, _ = _run_batch(monkeypatch, names, script)
    assert done.halted_refusals and done.halted_files == []
    left = [n for n in names if n not in _FakeImageWorker.seen]
    done, _ = _run_batch(monkeypatch, left, script)
    assert done.halted is None
    assert _FakeImageWorker.seen == left


def test_a_described_image_resets_the_refusal_count(monkeypatch):
    names = [f"{i}.jpg" for i in range(40)]
    script = {n: "declined" for n in names}
    script["20.jpg"] = "ok"
    done, _ = _run_batch(monkeypatch, names, script)
    assert _FakeImageWorker.seen == names
    assert done.halted is None


def test_a_refusal_does_not_hide_a_real_streak(monkeypatch):
    names = [f"{i}.jpg" for i in range(15)]
    script = {n: "plain" for n in names}
    script["5.jpg"] = "declined"           # 5 failures, a refusal, 5 more
    done, _ = _run_batch(monkeypatch, names, script)
    assert len(_FakeImageWorker.seen) == workers_wx.SAME_FAILURE_STREAK + 1
    assert done.halted == "failed: plain"


def test_one_videos_frames_failing_do_not_stop_the_batch(monkeypatch):
    """Windows AI failed on every frame of one screen recording while describing the
    frames around it (10/8/2026); counted as ten failures, it stopped every run there."""
    bad = [f"ws/derived/frames/iPhone/RPReplay/RPReplay_{t}.00s.jpg" for t in range(0, 75, 5)]
    names = ["ws/images/a.jpg"] + bad + ["ws/images/b.jpg"]
    script = {Path(n).name: "plain" for n in bad}
    done, _ = _run_batch(monkeypatch, names, script)
    assert _FakeImageWorker.seen == [Path(n).name for n in names]
    assert done.halted is None


def test_ten_videos_failing_in_a_row_still_stop_the_batch(monkeypatch):
    names = [f"ws/derived/frames/v{n}/v{n}_0.00s.jpg" for n in range(12)]
    script = {Path(n).name: "plain" for n in names}
    done, _ = _run_batch(monkeypatch, names, script)
    assert len(_FakeImageWorker.seen) == workers_wx.SAME_FAILURE_STREAK
    assert done.halted == "failed: plain"


def test_guardrail_refusal_is_per_image_through_the_adapter():
    """The flag must survive the adapter's re-raise and the worker's wrap,
    which is what the batch actually sees."""
    from ai_providers import raise_provider_error
    from idt_core.providers.apple import AppleFMError, GUARDRAIL_HINT
    try:
        try:
            try:
                raise AppleFMError(GUARDRAIL_HINT, per_image=True)
            except AppleFMError as exc:   # as AppleProvider.describe_image does
                raise_provider_error(provider="Apple Intelligence", kind=ErrorKind.UNKNOWN,
                                     message=str(exc))
        except ProviderError as e:        # as ProcessingWorker does
            raise Exception(f"AI processing failed: {e}") from e
    except Exception as wrapped:
        assert workers_wx._is_per_image_failure(wrapped)
    assert not workers_wx._is_per_image_failure(AppleFMError("fm crashed"))
    assert not workers_wx._is_per_image_failure(RuntimeError("x"))


def test_identical_failures_match_despite_timestamps():
    """Real formatted provider errors end in a timestamp; the streak rule
    compared those strings and so never fired (found by the third review)."""
    import time
    from ai_providers import format_provider_error

    def failure():
        try:
            try:
                raise ProviderError(
                    format_provider_error(provider="Claude Code", kind=ErrorKind.UNKNOWN,
                                          message="You have hit your limit"),
                    kind=ErrorKind.UNKNOWN, raw_message="You have hit your limit")
            except Exception as e:
                raise Exception(f"AI processing failed: {e}") from e
        except Exception as wrapped:
            return wrapped
    a = failure()
    time.sleep(0.01)
    b = failure()
    assert str(a) != str(b)
    assert workers_wx._failure_signature(a) == workers_wx._failure_signature(b)


def test_signature_strips_timestamp_without_raw_message():
    a = Exception("Error generating description: boom  - (2026-10-04 15:44:45,422)")
    b = Exception("Error generating description: boom  - (2026-10-04 15:44:46,456)")
    assert workers_wx._failure_signature(a) == workers_wx._failure_signature(b)


def test_batch_images_carry_their_batch(monkeypatch):
    posted = []
    monkeypatch.setattr(workers_wx.wx, "PostEvent", lambda win, evt: posted.append(evt))
    marker = object()
    w = workers_wx.ProcessingWorker(None, "C:/p/a.jpg", "ollama", "m", "narrative",
                                    "", None, batch=marker)

    def bad(*a, **k):
        raise ValueError("bad")
    monkeypatch.setattr(w, "_process_with_ai", bad)
    monkeypatch.setattr(w, "_inject_exif_context", lambda p: (p, ""), raising=False)
    w.run()
    failed = [e for e in posted if isinstance(e, workers_wx.ProcessingFailedEventData)]
    assert failed[0].batch is marker


def test_request_ids_do_not_make_identical_failures_differ():
    """Anthropic error text embeds a per-request id (fourth review)."""
    body = ("Error code: 400 - {'type': 'error', 'error': {'type': "
            "'invalid_request_error', 'message': 'Your credit balance is too low'}, "
            "'request_id': 'REQ'}")
    a = ProviderError("x", kind=ErrorKind.INVALID_REQUEST,
                      raw_message=body.replace("REQ", "req_011CAbc123"))
    b = ProviderError("y", kind=ErrorKind.INVALID_REQUEST,
                      raw_message=body.replace("REQ", "req_011CXyz789"))
    assert workers_wx._failure_signature(a) == workers_wx._failure_signature(b)


def test_streak_halt_is_flagged_and_fatal_halt_is_not(monkeypatch):
    names = [f"{i}.jpg" for i in range(12)]
    done, _ = _run_batch(monkeypatch, names, {n: "plain" for n in names})
    assert done.halted_streak is True
    done, _ = _run_batch(monkeypatch, ["a.jpg", "b.jpg"], {"a.jpg": ErrorKind.AUTH})
    assert done.halted_streak is False and done.halted_files == ["C:/p/a.jpg"]


def test_empty_description_after_retries_is_a_failure(monkeypatch, tmp_path):
    """Returned, it was stored as a blank description and counted as described."""
    import ai_providers
    posted = []
    monkeypatch.setattr(workers_wx.wx, "PostEvent", lambda win, evt: posted.append(evt))
    monkeypatch.setattr(workers_wx.time, "sleep", lambda s: None)

    class _Empty:
        last_usage = {"finish_reason": "stop"}

        def describe_image(self, *a, **k):
            return ""
    monkeypatch.setattr(ai_providers, "get_all_providers",
                        lambda: {"ollama": _Empty()}, raising=False)
    monkeypatch.setattr(workers_wx, "get_all_providers",
                        lambda: {"ollama": _Empty()}, raising=False)
    workers_wx.ProcessingWorker._provider_cache = {}
    img = tmp_path / "a.jpg"
    from PIL import Image
    Image.new("RGB", (8, 8)).save(img)
    w = workers_wx.ProcessingWorker(None, str(img), "ollama", "m", "narrative", "", None)
    monkeypatch.setattr(w, "_inject_exif_context", lambda p: (p, ""), raising=False)
    w.run()
    assert w.result_ok is False
    assert "empty description" in (w.result_error or "")
    assert not [e for e in posted if isinstance(e, workers_wx.ProcessingCompleteEventData)]
