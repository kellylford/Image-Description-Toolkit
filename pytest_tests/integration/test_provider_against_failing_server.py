"""Drive a provider against a real HTTP server that really fails.

Issue #228, item 6. `Integration Test: Windows` pulls minicpm-v4.6 and runs it
locally. A local model never returns 5xx, so the code path where the nine-month
retry bug lived is not reachable anywhere in CI -- the defect only surfaced
because ollama.com's cloud vision backend started failing about half the time
in production.

The tests here stand up a socket-level HTTP server that returns 500 then 200
and assert a description comes back. Everything between requests.post and the
retry decorator is real: the socket, the status line, the JSON body, the
backoff loop. The only thing stubbed is the sleep.
"""

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "imagedescriber"))

from ai_providers import OllamaProvider, _is_retryable_error  # noqa: E402

pytestmark = pytest.mark.integration

DESCRIPTION = "A weathered wooden dock with three boats moored alongside."


class _ScriptedHandler(BaseHTTPRequestHandler):
    """Serves the statuses listed in server.script, one per request."""

    protocol_version = "HTTP/1.1"

    def do_POST(self):  # noqa: N802 - BaseHTTPRequestHandler's naming
        length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(length)

        with self.server.lock:
            self.server.requests += 1
            index = min(self.server.requests - 1, len(self.server.script) - 1)
            status = self.server.script[index]

        if status == 200:
            body = json.dumps({
                "response": DESCRIPTION,
                "prompt_eval_count": 12,
                "eval_count": 9,
            }).encode("utf-8")
        else:
            body = json.dumps({"error": f"synthetic {status}"}).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        pass  # keep pytest output readable


@pytest.fixture
def failing_server():
    """Start a throwaway server on a free port; yield a factory for scripts."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), _ScriptedHandler)
    server.script = [200]
    server.requests = 0
    server.lock = threading.Lock()

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.fixture
def image(tmp_path, monkeypatch):
    monkeypatch.setattr("ai_providers.time.sleep", lambda _s: None)
    monkeypatch.chdir(tmp_path)   # keep api_errors.log out of the repo
    path = tmp_path / "dock.jpg"
    path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 64)
    return str(path)


def _describe(server, image_path):
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    provider = OllamaProvider(base_url=base_url)
    provider.timeout = 10
    return provider.describe_image(image_path, "Describe this image.",
                                   "gemma4:31b-cloud")


def test_five_hundred_then_two_hundred_yields_a_description(failing_server, image):
    """The production symptom, reproduced end to end over a real socket."""
    failing_server.script = [500, 200]

    result = _describe(failing_server, image)

    assert result == DESCRIPTION, (
        f"a single transient 500 became a hard failure: {result!r}"
    )
    assert failing_server.requests == 2, "expected exactly one retry"


@pytest.mark.parametrize("status", [500, 502, 503, 429])
def test_transient_statuses_are_retried_then_succeed(failing_server, image, status):
    """502 is what ollama.com's cloud vision backend actually returned."""
    failing_server.script = [status, status, 200]

    result = _describe(failing_server, image)

    assert result == DESCRIPTION
    assert failing_server.requests == 3


def test_a_permanent_500_run_reports_a_retryable_error(failing_server, image):
    """When the server never recovers, the last word must still read transient.

    Callers use that to tell "the model refused" from "the service was down",
    which is the difference between re-running the batch and not bothering.
    """
    failing_server.script = [500]

    result = _describe(failing_server, image)

    assert failing_server.requests == 4, "initial attempt + 3 retries"
    assert _is_retryable_error(result), result
    assert "500" in result


def test_a_401_is_not_retried(failing_server, image):
    """Retrying a rejected key costs the user four round trips per image."""
    failing_server.script = [401]

    result = _describe(failing_server, image)

    assert failing_server.requests == 1, (
        f"a 401 was retried {failing_server.requests} times"
    )
    assert not _is_retryable_error(result), result


def test_token_usage_survives_a_retry(failing_server, image):
    """The recovered response must be parsed like any other, not half-handled."""
    failing_server.script = [503, 200]
    base_url = f"http://127.0.0.1:{failing_server.server_address[1]}"
    provider = OllamaProvider(base_url=base_url)
    provider.timeout = 10

    provider.describe_image(image, "Describe this image.", "gemma4:31b-cloud")

    usage = provider.get_last_token_usage()
    assert usage is not None, "token usage was dropped on the retried attempt"
    assert usage["total_tokens"] == 21
