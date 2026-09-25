"""Apple Intelligence provider — the divergences that bite, pinned down.

The endpoint is OpenAI-shaped but not OpenAI-compatible, and two of the three
differences fail *silently*: a request that omits ``stream`` gets an event
stream where it expected JSON, and ``max_tokens`` is accepted and ignored.
Neither produces an error, so neither would be caught by a test that only
asserts "a description came back". They are asserted directly here.

The license check has its own regression test for the same reason: ``fm models``
exits non-zero whenever any model is unavailable, and ``pcc`` always is from a
process that is not Terminal — so reading the exit status would report every
correctly licensed Mac as unlicensed.

Nothing here starts a server, runs ``fm`` or needs macOS: the transport is faked
at the seams, so these run on CI.
"""

import json
import os
import platform
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from idt_core.providers import apple  # noqa: E402
from idt_core.providers.apple import (  # noqa: E402
    APPLE_MODELS,
    APPLE_MODEL_METADATA,
    DEFAULT_MODEL,
    AppleFMError,
    AppleProvider,
    build_payload,
    describe_messages,
    image_part,
    response_text,
    usage_tokens,
)

pytestmark = pytest.mark.unit

JPEG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"


# ---------------------------------------------------------------------------
# The request body
# ---------------------------------------------------------------------------

def test_stream_is_always_stated_explicitly():
    """The server's default is stream=true, the opposite of the OpenAI API.

    Omitting the field hands a JSON caller ``text/event-stream``, whose body
    fails to parse as an empty document — the failure that cost three attempts
    when this provider was first measured.
    """
    for streaming in (True, False):
        payload = build_payload([{"role": "user", "content": "hi"}],
                                stream=streaming)
        assert "stream" in payload, "stream must never be left to the server default"
        assert payload["stream"] is streaming


def test_streaming_asks_for_usage():
    """Without stream_options a streamed turn reports no tokens at all."""
    payload = build_payload([{"role": "user", "content": "hi"}], stream=True)
    assert payload["stream_options"] == {"include_usage": True}


def test_non_streaming_does_not_ask_for_usage():
    payload = build_payload([{"role": "user", "content": "hi"}], stream=False)
    assert "stream_options" not in payload


def test_output_limit_uses_max_completion_tokens_not_max_tokens():
    """``max_tokens`` is accepted and ignored by this server.

    Measured 9/24/2026: ``max_tokens: 10`` returned 39 tokens and
    ``finish_reason: stop``, while ``max_completion_tokens: 40`` returned
    exactly 40. Sending the wrong field means no length control, with no error.
    """
    payload = build_payload([{"role": "user", "content": "hi"}],
                            stream=False, max_output_tokens=120)
    assert payload["max_completion_tokens"] == 120
    assert "max_tokens" not in payload


def test_temperature_is_passed_through_only_when_set():
    assert "temperature" not in build_payload([], stream=False)
    assert build_payload([], stream=False, temperature=0.2)["temperature"] == 0.2


def test_model_defaults_when_blank():
    assert build_payload([], "", stream=False)["model"] == DEFAULT_MODEL


# ---------------------------------------------------------------------------
# The license gate
# ---------------------------------------------------------------------------

class _Result:
    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout, self.stderr, self.returncode = stdout, stderr, returncode


@pytest.fixture(autouse=True)
def _forget_license_memo(monkeypatch):
    """Each test decides the license state for itself."""
    monkeypatch.setattr(apple, "_license_confirmed", False, raising=False)


def test_licensed_mac_is_recognised_despite_a_nonzero_exit(monkeypatch):
    """The regression: ``fm models`` exits 1 whenever any model is unavailable.

    ``pcc`` is unavailable to every process that is not Terminal, so a correct,
    licensed machine reports exit code 1 on every run. Gating on the status
    would hide the provider on exactly the machines that can use it.
    """
    listing = ("  Apple Foundation Models\n"
               "  ✓ system (AFM 3 Core)\n"
               "  ✗ pcc  (Private Cloud Compute is not available in this context.)\n")
    monkeypatch.setattr(apple, "find_fm", lambda: "/usr/bin/fm")
    monkeypatch.setattr(apple.subprocess, "run",
                        lambda *a, **k: _Result(stdout=listing, returncode=1))
    assert apple.license_accepted() is True


def test_unaccepted_terms_are_detected(monkeypatch):
    banner = ("YOU HAVE NOT AGREED TO THE FOUNDATION MODELS CLI LEGAL NOTICE & "
              "TERMS.\nAgreeing ... must be run as a privileged user "
              "(e.g. 'sudo fm license').")
    monkeypatch.setattr(apple, "find_fm", lambda: "/usr/bin/fm")
    monkeypatch.setattr(apple.subprocess, "run",
                        lambda *a, **k: _Result(stderr=banner, returncode=1))
    assert apple.license_accepted() is False


def test_unrecognised_output_is_not_treated_as_licensed(monkeypatch):
    """A future output format must fail closed, with a hint, not at the socket."""
    monkeypatch.setattr(apple, "find_fm", lambda: "/usr/bin/fm")
    monkeypatch.setattr(apple.subprocess, "run",
                        lambda *a, **k: _Result(stdout="something else entirely"))
    assert apple.license_accepted() is False


def test_check_ready_names_the_command_the_user_must_run(monkeypatch):
    monkeypatch.setattr(apple.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(apple.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(apple, "find_fm", lambda: "/usr/bin/fm")
    monkeypatch.setattr(apple, "license_accepted", lambda *a, **k: False)

    with pytest.raises(AppleFMError) as excinfo:
        apple.check_ready()
    assert "sudo fm license" in str(excinfo.value)


def test_check_ready_rejects_other_platforms(monkeypatch):
    monkeypatch.setattr(apple.platform, "system", lambda: "Windows")
    with pytest.raises(AppleFMError) as excinfo:
        apple.check_ready()
    assert "macOS 27" in str(excinfo.value)


def test_check_ready_rejects_intel_macs(monkeypatch):
    monkeypatch.setattr(apple.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(apple.platform, "machine", lambda: "x86_64")
    with pytest.raises(AppleFMError):
        apple.check_ready()


def test_is_available_is_false_off_apple_silicon(monkeypatch):
    monkeypatch.setattr(apple.platform, "system", lambda: "Linux")
    assert apple.is_available() is False


# ---------------------------------------------------------------------------
# Reading a response
# ---------------------------------------------------------------------------

def test_response_text_extracts_the_message():
    data = {"choices": [{"message": {"content": "  a desk  "}}]}
    assert response_text(data) == "a desk"


def test_a_refusal_is_raised_not_returned():
    """A refusal stored as the image's description would be indistinguishable
    from one — the defect issue #230 is about."""
    data = {"choices": [{"message": {"content": "", "refusal": "no"}}]}
    with pytest.raises(AppleFMError):
        response_text(data)


def test_an_empty_response_is_raised_with_its_finish_reason():
    data = {"choices": [{"message": {"content": ""}, "finish_reason": "length"}]}
    with pytest.raises(AppleFMError) as excinfo:
        response_text(data)
    assert "length" in str(excinfo.value)


def test_usage_tokens_survive_a_response_without_usage():
    assert usage_tokens({}) == (0, 0)
    assert usage_tokens({"usage": {"prompt_tokens": 3, "completion_tokens": 4}}) == (3, 4)


# ---------------------------------------------------------------------------
# Image parts
# ---------------------------------------------------------------------------

def test_jpeg_is_sent_untouched():
    """No downscaling: the server resizes internally, and resolution made no
    measurable difference to prompt tokens (640×480 and 9000×6750 both ~206)."""
    part = image_part(JPEG, "image/jpeg")
    assert part["type"] == "image_url"
    assert part["image_url"]["url"].startswith("data:image/jpeg;base64,")

    import base64
    encoded = part["image_url"]["url"].split(",", 1)[1]
    assert base64.standard_b64decode(encoded) == JPEG


def test_unverified_formats_are_re_encoded_to_jpeg():
    """Only JPEG and PNG data URLs are verified against this endpoint."""
    pytest.importorskip("PIL")
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (4, 4), "red").save(buf, format="GIF")
    part = image_part(buf.getvalue(), "image/gif")
    assert part["image_url"]["url"].startswith("data:image/jpeg;base64,")


def test_describe_messages_put_the_prompt_and_image_in_one_user_turn():
    messages = describe_messages(JPEG, "image/jpeg", "describe it")
    assert [m["role"] for m in messages] == ["system", "user"]
    parts = messages[1]["content"]
    assert parts[0] == {"type": "text", "text": "describe it"}
    assert parts[1]["type"] == "image_url"


# ---------------------------------------------------------------------------
# describe(), with the transport faked
# ---------------------------------------------------------------------------

def _provider(monkeypatch):
    monkeypatch.setattr(apple, "check_ready", lambda *a, **k: None)
    return AppleProvider()


def test_describe_returns_text_and_tokens(monkeypatch):
    captured = {}

    def post_chat(payload, **_kwargs):
        captured.update(payload)
        return {"choices": [{"message": {"content": "a desk"}}],
                "usage": {"prompt_tokens": 288, "completion_tokens": 97}}

    monkeypatch.setattr(apple, "post_chat", post_chat)
    result = _provider(monkeypatch).describe(JPEG, "image/jpeg", "describe it")

    assert result.text == "a desk"
    assert result.provider == "apple"
    assert (result.input_tokens, result.output_tokens) == (288, 97)
    assert captured["stream"] is False, "describe must not receive an event stream"


def test_describe_uses_the_only_model_there_is(monkeypatch):
    assert APPLE_MODELS == ["system"]
    monkeypatch.setattr(apple, "check_ready", lambda *a, **k: None)
    assert AppleProvider().model_name == DEFAULT_MODEL


# ---------------------------------------------------------------------------
# Streaming
# ---------------------------------------------------------------------------

class _FakeResponse:
    """Yields SSE lines the way http.client's response object does."""

    def __init__(self, lines):
        self._lines = [line.encode("utf-8") for line in lines]

    def __iter__(self):
        return iter(self._lines)


class _FakeServer:
    def __init__(self, lines):
        self._lines = lines
        self.closed = False

    def open_chat(self, _payload, _timeout):
        outer = self

        class _Conn:
            def close(self):
                outer.closed = True

        return _Conn(), _FakeResponse(self._lines)


def _sse(**event):
    return "data: " + json.dumps(event) + "\n"


def test_stream_yields_deltas_then_usage(monkeypatch):
    lines = [
        _sse(choices=[{"delta": {"role": "assistant"}}]),
        _sse(choices=[{"delta": {"content": "a "}}]),
        _sse(choices=[{"delta": {"content": "desk"}}]),
        _sse(choices=[{"delta": {}, "finish_reason": "stop"}]),
        _sse(choices=[], usage={"prompt_tokens": 5, "completion_tokens": 2}),
        "data: [DONE]\n",
    ]
    server = _FakeServer(lines)
    monkeypatch.setattr(apple, "_server", server)

    events = list(apple.stream_chat({}))
    assert [text for kind, text in events if kind == "delta"] == ["a ", "desk"]
    kind, final = events[-1]
    assert kind == "done"
    assert final["usage"]["completion_tokens"] == 2
    assert final["finish_reason"] == "stop"
    assert server.closed, "the socket must be closed when the stream ends"


def test_abandoning_the_stream_closes_the_socket(monkeypatch):
    """Cancellation contract: closing the generator releases the connection.

    This is what makes Stop work in chat — and a leaked socket here would hold
    the single-threaded server open against every later request.
    """
    lines = [_sse(choices=[{"delta": {"content": "a "}}]),
             _sse(choices=[{"delta": {"content": "desk"}}]),
             "data: [DONE]\n"]
    server = _FakeServer(lines)
    monkeypatch.setattr(apple, "_server", server)

    stream = apple.stream_chat({})
    next(stream)
    stream.close()
    assert server.closed


def test_unparseable_sse_lines_are_skipped(monkeypatch):
    """A keep-alive or a truncated line must not end the turn."""
    lines = ["\n", ": keep-alive\n", "data: not-json\n",
             _sse(choices=[{"delta": {"content": "ok"}}]), "data: [DONE]\n"]
    monkeypatch.setattr(apple, "_server", _FakeServer(lines))
    assert [t for k, t in apple.stream_chat({}) if k == "delta"] == ["ok"]


# ---------------------------------------------------------------------------
# Server lifecycle
# ---------------------------------------------------------------------------

def test_health_reports_an_unavailable_model_with_its_reason():
    """Apple Intelligence can be switched off on a Mac where `fm` runs fine."""
    health = {"models": [{"name": "system", "available": False,
                          "reason": "Apple Intelligence is not enabled."}]}
    with pytest.raises(AppleFMError) as excinfo:
        apple.FmServer._check_model_available(health)
    message = str(excinfo.value)
    assert "Apple Intelligence is not enabled." in message
    assert "System Settings" in message


def test_health_passes_when_the_model_is_available():
    apple.FmServer._check_model_available(
        {"models": [{"name": "system", "available": True},
                    {"name": "pcc", "available": False, "reason": "not here"}]}
    )


def test_stopping_a_server_that_never_started_is_harmless():
    apple.FmServer().stop()


@pytest.mark.skipif(platform.system() != "Darwin", reason="Unix socket paths")
def test_socket_path_stays_short_enough_to_bind(monkeypatch):
    """macOS caps a Unix socket path at ~104 bytes.

    The default temp directory is a long per-user path under /var/folders, which
    leaves too little room — hence /tmp. A regression here would fail only at
    runtime, on a real Mac, as an unexplained bind error.
    """
    started = {}

    class _Proc:
        pid = 4242

        def poll(self):
            return None

        def terminate(self):
            pass

        def wait(self, timeout=None):
            return 0

    def fake_popen(cmd, **_kwargs):
        started["cmd"] = cmd
        return _Proc()

    monkeypatch.setattr(apple, "check_ready", lambda *a, **k: None)
    monkeypatch.setattr(apple.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(apple.FmServer, "_await_health_locked", lambda self: None)

    server = apple.FmServer()
    try:
        path = server.ensure_running(fm="/usr/bin/fm")
        assert len(path.encode()) < 100, f"socket path too long to bind: {path}"
        assert started["cmd"][:3] == ["/usr/bin/fm", "serve", "--socket"]
    finally:
        server.stop()


# ---------------------------------------------------------------------------
# Review fixes: things that were wrong in the first cut of this provider
# ---------------------------------------------------------------------------

def test_the_context_window_is_the_measured_one():
    """It was 65,536 in the first cut, invented rather than measured.

    The server accepted a 4,060-token prompt and refused a 5,060-token one, so
    the real window is 4,096. The chat budgeter trims against this number: at
    65,536 it would happily build a conversation sixteen times too large, and
    every turn would fail with a context error no retry could fix.
    """
    from idt_core.chat.tokens import DEFAULT_CONTEXT_WINDOWS

    assert APPLE_MODEL_METADATA["system"]["context_window"] == 4096
    assert DEFAULT_CONTEXT_WINDOWS["apple"] == 4096, (
        "the budgeter's default must match the catalog entry"
    )


def test_a_too_long_conversation_reads_as_permanent_not_as_a_500():
    """The server reports it as HTTP 500, which classifies as retryable.

    Retrying sends the same oversized transcript, so it fails identically,
    forever. The message is rewritten to say what to do instead.
    """
    from idt_core.chat.errors import classify

    detail = ('{"error":{"type":"server_error","message":"The session\'s '
              'transcript exceeded the model\'s context size.","code":"500"}}')
    server = _FailingServer(500, detail)
    monkey = pytest.MonkeyPatch()
    try:
        monkey.setattr(apple, "_server", server)
        with pytest.raises(AppleFMError) as excinfo:
            apple.post_chat({})
    finally:
        monkey.undo()

    message = str(excinfo.value)
    assert "4,096" in message and "new chat" in message
    assert "500" not in message, "a 500 in the text is read as a transient error"
    assert not classify(excinfo.value).retryable


def test_a_real_server_error_still_says_so():
    """Only the context case is rewritten; other failures keep their status."""
    server = _FailingServer(503, "upstream exploded")
    monkey = pytest.MonkeyPatch()
    try:
        monkey.setattr(apple, "_server", server)
        with pytest.raises(AppleFMError) as excinfo:
            apple.post_chat({})
    finally:
        monkey.undo()
    assert "503" in str(excinfo.value)


def test_a_socket_timeout_mid_read_is_an_apple_error_not_a_bare_oserror(monkeypatch):
    """It used to escape past every ``except AppleFMError`` in the callers.

    describe_image would then raise an unclassified OSError instead of a
    ProviderError, which a batch worker cannot tell from a crash.
    """
    class _TimingOutResponse:
        def read(self):
            raise TimeoutError("timed out")

        def __iter__(self):
            raise TimeoutError("timed out")

    class _Server:
        def __init__(self):
            self.closed = False

        def open_chat(self, _payload, _timeout):
            outer = self

            class _Conn:
                def close(self):
                    outer.closed = True

            return _Conn(), _TimingOutResponse()

    server = _Server()
    monkeypatch.setattr(apple, "_server", server)

    with pytest.raises(AppleFMError) as excinfo:
        apple.post_chat({})
    assert "timed out" in str(excinfo.value).lower(), (
        "callers classify on this text; a timeout must still read as one"
    )
    assert server.closed, "the connection must be closed even when the read fails"


def test_a_stream_that_dies_mid_answer_is_an_apple_error(monkeypatch):
    server = _Server = None  # noqa: F841 - readability of the block below

    class _DyingResponse:
        def __iter__(self):
            yield b'data: {"choices":[{"delta":{"content":"a "}}]}\n'
            raise ConnectionResetError("connection reset by peer")

    class _S:
        def __init__(self):
            self.closed = False

        def open_chat(self, _payload, _timeout):
            outer = self

            class _Conn:
                def close(self):
                    outer.closed = True

            return _Conn(), _DyingResponse()

    s = _S()
    monkeypatch.setattr(apple, "_server", s)

    stream = apple.stream_chat({})
    assert next(stream) == ("delta", "a ")
    with pytest.raises(AppleFMError):
        next(stream)
    assert s.closed


def test_describe_caps_the_reply_length(monkeypatch):
    """Every other provider bounds its output; with a 4,096-token window an
    unbounded reply would eat the budget the image needs."""
    captured = {}

    def post_chat(payload, **_kwargs):
        captured.update(payload)
        return {"choices": [{"message": {"content": "a desk"}}]}

    monkeypatch.setattr(apple, "post_chat", post_chat)
    _provider(monkeypatch).describe(JPEG, "image/jpeg", "describe it")
    assert captured["max_completion_tokens"] == apple.DESCRIBE_MAX_OUTPUT_TOKENS


def test_an_unavailable_model_stops_the_server_it_started(monkeypatch):
    """Otherwise the next request reuses that server, skips the health check,
    and reports a raw HTTP error instead of "turn on Apple Intelligence"."""
    server = apple.FmServer()
    stopped = []

    monkeypatch.setattr(apple, "check_ready", lambda *a, **k: None)
    monkeypatch.setattr(apple.subprocess, "Popen",
                        lambda *a, **k: _LiveProc())
    monkeypatch.setattr(
        apple.FmServer, "_get_json",
        lambda self, path, timeout: {
            "models": [{"name": "system", "available": False,
                        "reason": "Apple Intelligence is not enabled."}]})
    original = apple.FmServer._cleanup_locked

    def cleanup(self):
        stopped.append(True)
        original(self)

    monkeypatch.setattr(apple.FmServer, "_cleanup_locked", cleanup)

    with pytest.raises(AppleFMError) as excinfo:
        server.ensure_running(fm="/usr/bin/fm")
    assert "Apple Intelligence is not enabled." in str(excinfo.value)
    assert stopped, "the server it just started must be stopped"
    assert not server.is_running()


# ---------------------------------------------------------------------------
# Reaping servers left behind by a run that was killed
# ---------------------------------------------------------------------------

def test_an_orphaned_server_is_killed_when_its_owner_is_gone(monkeypatch, tmp_path):
    """atexit does not run when an app is force-quit, and the child is in its
    own session, so it survives holding the model in memory."""
    stale = tmp_path / "idt-fm-stale"
    stale.mkdir()
    (stale / apple.OWNER_FILE).write_text(
        json.dumps({"owner_pid": 999001, "server_pid": 999002}), encoding="utf-8")

    killed = []
    monkeypatch.setattr(apple, "SOCKET_ROOT", str(tmp_path))
    monkeypatch.setattr(apple, "_pid_alive", lambda pid: pid == 999002)
    monkeypatch.setattr(apple.os, "kill", lambda pid, sig: killed.append((pid, sig)))

    apple._reap_orphans()

    assert killed == [(999002, apple.signal.SIGTERM)]
    assert not stale.exists()


def test_a_live_owners_server_is_left_alone(monkeypatch, tmp_path):
    """A second IDT running right now must keep its own server."""
    live = tmp_path / "idt-fm-live"
    live.mkdir()
    (live / apple.OWNER_FILE).write_text(
        json.dumps({"owner_pid": os.getpid(), "server_pid": 999002}),
        encoding="utf-8")

    signals = []
    monkeypatch.setattr(apple, "SOCKET_ROOT", str(tmp_path))
    # _pid_alive probes with os.kill(pid, 0), so record the signal, not the call.
    monkeypatch.setattr(apple.os, "kill",
                        lambda pid, sig: signals.append((pid, sig)))

    apple._reap_orphans()

    assert all(sig == 0 for _pid, sig in signals), (
        f"a live owner's server was signalled: {signals}"
    )
    assert live.exists()


def test_a_directory_without_an_owner_file_is_never_touched(monkeypatch, tmp_path):
    """An unowned socket costs nothing; a wrong kill costs someone's run."""
    unknown = tmp_path / "idt-fm-unknown"
    unknown.mkdir()
    monkeypatch.setattr(apple, "SOCKET_ROOT", str(tmp_path))
    apple._reap_orphans()
    assert unknown.exists()


def test_reaping_survives_an_unreadable_socket_root(monkeypatch):
    """Best effort: cleanup must never stop a new server from starting."""
    monkeypatch.setattr(apple, "SOCKET_ROOT", "/nonexistent-path-for-a-test")
    apple._reap_orphans()


class _LiveProc:
    pid = 4242

    def poll(self):
        return None

    def terminate(self):
        pass

    def kill(self):
        pass

    def wait(self, timeout=None):
        return 0


class _FailingServer:
    """A server whose endpoint answers with an HTTP error."""

    def __init__(self, status, detail):
        self._status, self._detail = status, detail

    def open_chat(self, _payload, _timeout):
        # open_chat itself raises for a non-200, which is what is under test,
        # so this reproduces that path rather than returning a response.
        from idt_core.providers.apple import CONTEXT_HINT, _CONTEXT_MARKER

        if _CONTEXT_MARKER in self._detail:
            raise AppleFMError(CONTEXT_HINT)
        raise AppleFMError(
            f"Apple Intelligence returned HTTP {self._status}: {self._detail}")


def test_a_directory_owned_by_another_user_is_never_reaped(monkeypatch, tmp_path):
    """/tmp is world-writable. Without an ownership check, another account
    could plant an owner file naming a dead owner and any pid it liked, and
    have IDT SIGTERM a process of this user's that it has no business killing.
    """
    planted = tmp_path / "idt-fm-planted"
    planted.mkdir()
    (planted / apple.OWNER_FILE).write_text(
        json.dumps({"owner_pid": 999001, "server_pid": 999002}), encoding="utf-8")

    signals = []
    monkeypatch.setattr(apple, "SOCKET_ROOT", str(tmp_path))
    # Captured first: apple.os IS os, so a lambda calling os.getuid() would
    # call the patched version and recurse.
    someone_else = os.getuid() + 1
    monkeypatch.setattr(apple.os, "getuid", lambda: someone_else)
    monkeypatch.setattr(apple.os, "kill",
                        lambda pid, sig: signals.append((pid, sig)))

    apple._reap_orphans()

    assert signals == [], "a directory this user does not own must be left alone"
    assert planted.exists()
