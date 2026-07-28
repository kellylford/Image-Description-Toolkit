"""The contract between provider error strings and the retry decorator.

Providers signal failure by RETURNING a string, not by raising. The retry
decorator therefore has to recognise a transient failure from its wording
alone. That is an implicit contract, and it broke silently twice:

  * Ollama returned "Error: HTTP 500 - (ts)", but the decorator only matched
    "status code: 5" / "status code: 429". Every Ollama 5xx was a hard failure
    for nine months. It only became visible when ollama.com's cloud vision
    backend started failing ~50% of the time.
  * The decorator additionally required result.startswith("Error:"), which most
    OpenAI and Claude error strings do not, so their 429/5xx never retried
    either.

Both defects lived under a fully green suite because nothing exercised
describe_image()'s error path or the decorator at all. These tests close that
gap: they assert the classification table, that the decorator actually retries,
and -- most importantly -- that every provider's real error strings are
classified the way the provider intends.
"""

import re
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "imagedescriber"))

from ai_providers import (  # noqa: E402
    OllamaProvider,
    _is_retryable_error,
    retry_on_api_error,
)


# --------------------------------------------------------------------------
# Classification table
# --------------------------------------------------------------------------

RETRYABLE = [
    "Rate limit exceeded (status code: 429) - (ts)",
    "Server error from OpenAI API (status code: 500) - (ts)",
    "Server error from Claude API (status code: 503) - (ts)",
    "Error: Server error from Ollama (status code: 502) - (ts)",
    "Request timeout - try again later (status code: timeout) - (ts)",
    "Error generating description: connection timeout - (ts)",
]

NOT_RETRYABLE = [
    "Authentication failed - check API key (status code: 401) - (ts)",
    "Invalid request - image too large (status code: 400) - (ts)",
    "Invalid request - bad model (status code: 404) - (ts)",
    "A photo of a cat sitting on a windowsill.",
    "",
]


@pytest.mark.parametrize("text", RETRYABLE)
def test_transient_failures_are_retryable(text):
    assert _is_retryable_error(text) is True, f"should retry: {text!r}"


@pytest.mark.parametrize("text", NOT_RETRYABLE)
def test_permanent_failures_are_not_retryable(text):
    assert _is_retryable_error(text) is False, f"should NOT retry: {text!r}"


def test_non_string_results_are_not_retryable():
    """describe_image can only return str, but the guard must not explode."""
    for value in (None, 42, [], {"a": 1}):
        assert _is_retryable_error(value) is False


# --------------------------------------------------------------------------
# The decorator actually retries
# --------------------------------------------------------------------------

def test_decorator_retries_then_succeeds(monkeypatch):
    monkeypatch.setattr("ai_providers.time.sleep", lambda _s: None)
    calls = []

    @retry_on_api_error(max_retries=3, base_delay=0)
    def flaky():
        calls.append(1)
        if len(calls) < 3:
            return "Error: Server error from Ollama (status code: 500) - (ts)"
        return "a description"

    assert flaky() == "a description"
    assert len(calls) == 3, "should have retried twice before succeeding"


def test_decorator_gives_up_and_returns_last_error(monkeypatch):
    monkeypatch.setattr("ai_providers.time.sleep", lambda _s: None)
    calls = []

    @retry_on_api_error(max_retries=2, base_delay=0)
    def always_500():
        calls.append(1)
        return "Error: Server error from Ollama (status code: 500) - (ts)"

    result = always_500()
    assert "status code: 500" in result
    assert len(calls) == 3, "initial attempt + 2 retries"


@pytest.mark.parametrize("error_text", [
    # Neither of these starts with "Error:" -- the old guard required that
    # prefix, so OpenAI and Claude 429/5xx responses skipped every retry.
    "Rate limit exceeded (status code: 429) - (ts)",
    "Server error from OpenAI API (status code: 500) - (ts)",
    "Server error from Claude API (status code: 503) - (ts)",
    "Request timeout - try again later (status code: timeout) - (ts)",
])
def test_decorator_retries_errors_without_the_error_prefix(monkeypatch, error_text):
    monkeypatch.setattr("ai_providers.time.sleep", lambda _s: None)
    calls = []

    @retry_on_api_error(max_retries=3, base_delay=0)
    def flaky():
        calls.append(1)
        if len(calls) < 2:
            return error_text
        return "a description"

    assert flaky() == "a description", (
        f"{error_text!r} was treated as permanent and never retried"
    )
    assert len(calls) == 2


def test_decorator_does_not_retry_permanent_failures(monkeypatch):
    monkeypatch.setattr("ai_providers.time.sleep", lambda _s: None)
    calls = []

    @retry_on_api_error(max_retries=3, base_delay=0)
    def auth_failure():
        calls.append(1)
        return "Authentication failed - check API key (status code: 401) - (ts)"

    auth_failure()
    assert len(calls) == 1, "a 401 must not be retried"


def test_decorator_does_not_retry_a_successful_description(monkeypatch):
    monkeypatch.setattr("ai_providers.time.sleep", lambda _s: None)
    calls = []

    @retry_on_api_error(max_retries=3, base_delay=0)
    def ok():
        calls.append(1)
        return "A photo of a desk with a coffee cup."

    assert ok() == "A photo of a desk with a coffee cup."
    assert len(calls) == 1


# --------------------------------------------------------------------------
# The real Ollama path -- the exact regression
# --------------------------------------------------------------------------

class _FakeResponse:
    def __init__(self, status_code, payload=""):
        self.status_code = status_code
        self.text = payload

    def json(self):
        return {"response": self.text}


def test_ollama_http_500_produces_a_retryable_string(tmp_path, monkeypatch):
    """ollama.com's cloud vision backend returns 500/502 intermittently.

    The string OllamaProvider returns for that MUST be one the decorator
    retries -- this is the bug that shipped for nine months.
    """
    monkeypatch.setattr("ai_providers.time.sleep", lambda _s: None)
    monkeypatch.chdir(tmp_path)  # keep api_errors.log out of the repo
    image = tmp_path / "img.jpg"
    image.write_bytes(b"\xff\xd8\xff\xe0not-a-real-jpeg")

    monkeypatch.setattr(
        "ai_providers.requests.post",
        lambda *a, **k: _FakeResponse(500, '{"error":"Internal Server Error"}'),
    )

    provider = OllamaProvider()
    # describe_image is wrapped by the decorator, so this exhausts the retries
    # and hands back the final error string.
    result = provider.describe_image(str(image), "describe", "gemma4:31b-cloud")

    assert _is_retryable_error(result), (
        f"Ollama's HTTP-error string is not recognised as retryable: {result!r}. "
        "Every 5xx would become a hard per-image failure."
    )


def test_ollama_retries_and_recovers(tmp_path, monkeypatch):
    """A 500 followed by a 200 must yield the description, not an error."""
    monkeypatch.setattr("ai_providers.time.sleep", lambda _s: None)
    monkeypatch.chdir(tmp_path)
    image = tmp_path / "img.jpg"
    image.write_bytes(b"\xff\xd8\xff\xe0not-a-real-jpeg")

    calls = []

    def fake_post(*a, **k):
        calls.append(1)
        if len(calls) == 1:
            return _FakeResponse(500, '{"error":"Internal Server Error"}')
        return _FakeResponse(200, "a cluttered desk")

    monkeypatch.setattr("ai_providers.requests.post", fake_post)

    provider = OllamaProvider()
    result = provider.describe_image(str(image), "describe", "gemma4:31b-cloud")

    assert result == "a cluttered desk"
    assert len(calls) == 2, "should have retried exactly once"


# --------------------------------------------------------------------------
# Format drift across ALL providers
# --------------------------------------------------------------------------

def test_every_provider_error_string_uses_the_status_code_convention():
    """Statically scan for error returns that name an HTTP status.

    A provider that invents its own wording (Ollama's old "Error: HTTP 500")
    silently opts out of retrying. Any literal in ai_providers.py that mentions
    a 5xx/429 status must be classified retryable.
    """
    src = (_ROOT / "imagedescriber" / "ai_providers.py").read_text(encoding="utf-8")

    # Literals that look like an error message mentioning a concrete status code
    literals = re.findall(r'f?"([^"\n]*status code[^"\n]*)"', src, re.IGNORECASE)
    assert literals, "expected to find provider error-string literals"

    offenders = []
    for lit in literals:
        # Only check templates with a literal status number; {placeholder} ones
        # are resolved at runtime and covered by the behavioural tests above.
        m = re.search(r"status code:\s*(\d{3})", lit, re.IGNORECASE)
        if not m:
            continue
        status = int(m.group(1))
        should_retry = status >= 500 or status == 429
        if _is_retryable_error(lit) != should_retry:
            offenders.append((lit, status, should_retry))

    assert not offenders, (
        "provider error strings disagree with the retry classifier: " + repr(offenders)
    )


def test_no_provider_uses_the_old_bare_http_wording():
    """Guard the specific regression: "Error: HTTP 500" style strings."""
    src = (_ROOT / "imagedescriber" / "ai_providers.py").read_text(encoding="utf-8")
    assert 'Error: HTTP {response.status_code}' not in src, (
        "This wording does not contain 'status code: NNN', so retry_on_api_error "
        "will never retry it. Use the '(status code: NNN)' convention instead."
    )


def test_retry_decorator_is_defined_exactly_once():
    """It was defined twice; the second silently shadowed the first."""
    src = (_ROOT / "imagedescriber" / "ai_providers.py").read_text(encoding="utf-8")
    count = len(re.findall(r"^def retry_on_api_error\b", src, re.MULTILINE))
    assert count == 1, f"expected exactly one definition, found {count}"
