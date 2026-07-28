"""Every AIProvider subclass, driven through real failures.

Issue #228. The previous guard here scanned ai_providers.py for string literals
that already contained the words "status code" and checked those classified
correctly. A provider that invented its own wording was invisible to it -- the
exact defect that shipped: OllamaProvider returned "Error: HTTP 500", which
contains no "status code", so the scanner had nothing to look at and
retry_on_api_error treated every Ollama 5xx as permanent for nine months.

This file inverts the check. Instead of asking "does the wording that exists
look right", it enumerates AIProvider's subclasses at runtime and demands that
each one be driven through an injected 200 / 429 / 500 / 401 / timeout and
classify the way it claims to. A provider added later cannot opt out: with no
driver registered, test_every_provider_subclass_has_a_fault_injection_driver
fails and names it.

The strongest test in here is _500_then_200: it asserts a description comes
back after a transient failure. That fails if the wording is wrong, if the
retry decorator is missing, or if a delegating provider forgets to delegate --
three separate ways the bug could recur, caught by one assertion.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "imagedescriber"))

import ai_providers  # noqa: E402
from ai_providers import (  # noqa: E402
    AIProvider,
    ClaudeProvider,
    ErrorKind,
    MLXProvider,
    OllamaCloudProvider,
    OllamaProvider,
    OpenAIProvider,
    RETRYABLE_KINDS,
    _is_retryable_error,
    format_provider_error,
    kind_for_status,
)


# ===========================================================================
# Fault injection
#
# An "outcome script" is a list consumed one entry per API call:
#   ("ok", text)      -- a successful description
#   ("http", status)  -- an HTTP failure with that status
#   ("timeout", None) -- a transport timeout
#   ("garbage", None) -- a response the provider cannot parse
# Each driver knows how to make its provider's transport produce them.
# ===========================================================================

OK = "a cluttered desk with a coffee cup"


class _ScriptExhausted(AssertionError):
    pass


class _Script:
    """Pops outcomes in order; the last one repeats forever."""

    def __init__(self, outcomes):
        if not outcomes:
            raise _ScriptExhausted("an outcome script needs at least one entry")
        self._outcomes = list(outcomes)
        self.calls = 0

    def next(self):
        self.calls += 1
        if len(self._outcomes) > 1:
            return self._outcomes.pop(0)
        return self._outcomes[0]


# -- fake SDK exceptions ----------------------------------------------------
# Named to match what classify_provider_exception keys off, so the drivers
# exercise the same branches the real SDKs trigger.

class RateLimitError(Exception):
    status_code = 429


class AuthenticationError(Exception):
    status_code = 401


class APIStatusError(Exception):
    def __init__(self, message, status_code):
        super().__init__(message)
        self.status_code = status_code


class APITimeoutError(Exception):
    pass


def _sdk_exception(status):
    if status == 429:
        return RateLimitError(f"rate limited (status {status})")
    if status == 401:
        return AuthenticationError(f"invalid api key (status {status})")
    return APIStatusError(f"upstream said {status}", status)


# -- HTTP fake for the requests-based providers -----------------------------

class _FakeResponse:
    def __init__(self, status_code, text, parseable=True):
        self.status_code = status_code
        self.text = text
        self._parseable = parseable

    def json(self):
        if not self._parseable:
            raise ValueError("Expecting value: line 1 column 1 (char 0)")
        return {"response": self.text}


# ===========================================================================
# Drivers -- one per AIProvider subclass
# ===========================================================================

class ProviderDriver:
    """Knows how to build a provider whose transport does what we say.

    Every AIProvider subclass needs one of these. That requirement is the
    mechanism: a new provider with no driver fails the suite by name, so its
    author cannot skip declaring how it fails.
    """

    provider_class = None

    #: False for on-device providers, which have no remote to return a status.
    #: Must carry a reason -- "it doesn't apply" has to be argued, not assumed.
    speaks_http = True
    no_http_reason = ""

    def build(self, monkeypatch, tmp_path, outcomes):
        """Return (provider, script). script.calls counts transport calls."""
        raise NotImplementedError


class _OllamaDriver(ProviderDriver):
    provider_class = OllamaProvider

    def _make(self, monkeypatch, outcomes):
        script = _Script(outcomes)

        def fake_post(*_args, **_kwargs):
            kind, value = script.next()
            if kind == "ok":
                return _FakeResponse(200, value)
            if kind == "http":
                return _FakeResponse(value, f'{{"error":"status {value}"}}')
            if kind == "timeout":
                raise APITimeoutError("Read timeout after 300s")
            if kind == "garbage":
                return _FakeResponse(200, "<html>not json</html>", parseable=False)
            raise _ScriptExhausted(kind)

        monkeypatch.setattr(ai_providers.requests, "post", fake_post)
        return script

    def build(self, monkeypatch, tmp_path, outcomes):
        script = self._make(monkeypatch, outcomes)
        return OllamaProvider(), script


class _OllamaCloudDriver(_OllamaDriver):
    """Cloud models are served through the same local endpoint.

    OllamaCloudProvider.describe_image carries no @retry_on_api_error of its
    own -- it delegates to OllamaProvider, which has one. That is fine, and the
    500-then-200 case is what proves the delegation is still in place.
    """

    provider_class = OllamaCloudProvider

    def build(self, monkeypatch, tmp_path, outcomes):
        script = self._make(monkeypatch, outcomes)
        return OllamaCloudProvider(), script


class _OpenAIDriver(ProviderDriver):
    provider_class = OpenAIProvider

    def build(self, monkeypatch, tmp_path, outcomes):
        script = _Script(outcomes)

        def create(**_kwargs):
            kind, value = script.next()
            if kind == "ok":
                return SimpleNamespace(
                    id="resp_1",
                    model="gpt-4o",
                    choices=[SimpleNamespace(
                        message=SimpleNamespace(content=value, role="assistant"),
                        finish_reason="stop",
                    )],
                    usage=SimpleNamespace(
                        prompt_tokens=10, completion_tokens=5, total_tokens=15),
                )
            if kind == "http":
                raise _sdk_exception(value)
            if kind == "timeout":
                raise APITimeoutError("Request timed out.")
            if kind == "garbage":
                # A response shaped nothing like the SDK's -- attribute access
                # inside describe_image blows up and must not escape.
                return SimpleNamespace(choices=[])
            raise _ScriptExhausted(kind)

        provider = OpenAIProvider(api_key="sk-test-not-a-real-key")
        provider.client = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        return provider, script


class _ClaudeDriver(ProviderDriver):
    provider_class = ClaudeProvider

    def build(self, monkeypatch, tmp_path, outcomes):
        script = _Script(outcomes)

        def create(**_kwargs):
            kind, value = script.next()
            if kind == "ok":
                return SimpleNamespace(
                    content=[SimpleNamespace(text=value)],
                    usage=SimpleNamespace(input_tokens=10, output_tokens=5),
                )
            if kind == "http":
                raise _sdk_exception(value)
            if kind == "timeout":
                raise APITimeoutError("Request timed out.")
            if kind == "garbage":
                return SimpleNamespace(content=[SimpleNamespace()])
            raise _ScriptExhausted(kind)

        provider = ClaudeProvider(api_key="sk-ant-test-not-a-real-key")
        provider.client = SimpleNamespace(
            messages=SimpleNamespace(create=create))
        return provider, script


class _MLXDriver(ProviderDriver):
    provider_class = MLXProvider
    speaks_http = False
    no_http_reason = (
        "MLX runs mlx-vlm on the local Metal GPU. There is no remote, so no "
        "HTTP status exists to classify. Its failures are exceptions, which "
        "are covered by the success/timeout/garbage cases below."
    )

    def build(self, monkeypatch, tmp_path, outcomes):
        script = _Script(outcomes)

        def generate(*_args, **_kwargs):
            kind, value = script.next()
            if kind == "ok":
                return SimpleNamespace(
                    text=value, prompt_tokens=10,
                    generation_tokens=5, generation_tps=1.0, prompt_tps=1.0)
            if kind == "timeout":
                raise APITimeoutError("Metal command buffer timeout")
            if kind == "http":
                raise APIStatusError(f"upstream said {value}", value)
            if kind == "garbage":
                raise RuntimeError("Unrecognized video processor")
            raise _ScriptExhausted(kind)

        # These names only exist when mlx_vlm imported, i.e. never on CI.
        for name, value in (
            ("HAS_MLX_VLM", True),
            ("_mlx_generate", generate),
            ("_mlx_load", lambda _m: (object(), object())),
            ("_mlx_load_config", lambda _m: {}),
            ("_mlx_apply_chat_template", lambda *a, **k: "prompt"),
        ):
            monkeypatch.setattr(ai_providers, name, value, raising=False)
        monkeypatch.setattr(ai_providers.platform, "system", lambda: "Darwin")

        provider = MLXProvider()
        monkeypatch.setattr(
            provider, "_to_jpeg_tempfile",
            lambda p: str(tmp_path / "converted.jpg"))
        monkeypatch.setattr(provider, "_patch_transformers_video_bug",
                            lambda: None)
        return provider, script


DRIVERS = [
    _OllamaDriver(),
    _OllamaCloudDriver(),
    _OpenAIDriver(),
    _ClaudeDriver(),
    _MLXDriver(),
]

HTTP_DRIVERS = [d for d in DRIVERS if d.speaks_http]


def _driver_id(driver):
    return driver.provider_class.__name__


def _all_subclasses(cls):
    for sub in cls.__subclasses__():
        yield sub
        yield from _all_subclasses(sub)


@pytest.fixture
def image(tmp_path, monkeypatch):
    """A file on disk, with retries instant and api_errors.log out of the repo."""
    monkeypatch.setattr(ai_providers.time, "sleep", lambda _s: None)
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "img.jpg"
    path.write_bytes(b"\xff\xd8\xff\xe0not-a-real-jpeg")
    (tmp_path / "converted.jpg").write_bytes(path.read_bytes())
    return str(path)


def _describe(driver, monkeypatch, tmp_path, image_path, outcomes):
    provider, script = driver.build(monkeypatch, tmp_path, outcomes)
    result = provider.describe_image(image_path, "describe this", "test-model")
    return result, script


# ===========================================================================
# The gate: no provider may exist without a driver
# ===========================================================================

def test_every_provider_subclass_has_a_fault_injection_driver():
    """A new provider must declare how it fails, or the suite fails.

    This is the check the old literal-scanning test could not make. Adding a
    GeminiProvider that returns "Error: upstream returned HTTP 503 - retry
    later" -- byte-for-byte the same class of defect as the original bug --
    left the previous suite fully green.
    """
    registered = {d.provider_class for d in DRIVERS}
    missing = sorted(
        cls.__name__ for cls in _all_subclasses(AIProvider)
        if cls not in registered and not getattr(cls, "__abstractmethods__", None)
    )
    assert not missing, (
        "These AIProvider subclasses have no fault-injection driver, so nothing "
        "verifies that their failures are classified correctly:\n  "
        + "\n  ".join(missing)
        + "\n\nAdd a ProviderDriver subclass for each in "
        "pytest_tests/unit/test_provider_contract.py and append it to DRIVERS. "
        "The driver only has to make the provider's transport return a given "
        "HTTP status; the assertions below are shared."
    )


def test_drivers_that_skip_http_give_a_reason():
    """"HTTP doesn't apply to me" has to be argued, not assumed."""
    for driver in DRIVERS:
        if not driver.speaks_http:
            assert driver.no_http_reason.strip(), (
                f"{_driver_id(driver)} opts out of the HTTP status matrix "
                "without saying why. State the reason in no_http_reason."
            )


# ===========================================================================
# The classification matrix, per provider
# ===========================================================================

@pytest.mark.parametrize("driver", HTTP_DRIVERS, ids=_driver_id)
@pytest.mark.parametrize("status,should_retry", [
    (500, True),    # the original bug
    (502, True),    # ollama.com's cloud vision backend, ~50% of the time
    (503, True),
    (429, True),    # rate limit
    (401, False),   # bad key -- retrying burns time and never succeeds
    (400, False),   # malformed request
])
def test_http_status_classifies_correctly(driver, status, should_retry,
                                          monkeypatch, tmp_path, image):
    """The returned string must be classified the way the status implies."""
    result, _ = _describe(driver, monkeypatch, tmp_path, image,
                          [("http", status)])

    assert isinstance(result, str) and result, "a provider must return a string"
    assert _is_retryable_error(result) is should_retry, (
        f"{_driver_id(driver)} returned {result!r} for HTTP {status}. "
        f"_is_retryable_error says {not should_retry}, but a {status} is "
        f"{'transient' if should_retry else 'permanent'}. "
        "Build the string with format_provider_error() instead of by hand."
    )


@pytest.mark.parametrize("driver", HTTP_DRIVERS, ids=_driver_id)
def test_five_hundred_then_two_hundred_returns_a_description(
        driver, monkeypatch, tmp_path, image):
    """The single most important assertion in this file.

    This is what a user experiences: one flaky call, then a good one. It fails
    if the error wording drifts, if @retry_on_api_error is missing from a new
    provider, or if a delegating provider stops delegating.
    """
    result, script = _describe(driver, monkeypatch, tmp_path, image,
                               [("http", 500), ("ok", OK)])

    assert result == OK, (
        f"{_driver_id(driver)} gave up after one 500 and returned {result!r}. "
        "A transient server error must be retried."
    )
    assert script.calls == 2, f"expected exactly one retry, saw {script.calls} calls"


@pytest.mark.parametrize("driver", HTTP_DRIVERS, ids=_driver_id)
def test_a_401_is_not_retried(driver, monkeypatch, tmp_path, image):
    """Retrying a bad API key wastes the user's time on every image."""
    _, script = _describe(driver, monkeypatch, tmp_path, image,
                          [("http", 401)])
    assert script.calls == 1, (
        f"{_driver_id(driver)} retried a 401 {script.calls} times"
    )


@pytest.mark.parametrize("driver", HTTP_DRIVERS, ids=_driver_id)
def test_a_persistent_500_gives_up_and_reports_it(
        driver, monkeypatch, tmp_path, image):
    """Retries are bounded, and the final answer still reads as an error."""
    result, script = _describe(driver, monkeypatch, tmp_path, image,
                               [("http", 500)])
    assert script.calls == 4, (
        f"expected initial attempt + 3 retries, saw {script.calls}"
    )
    assert _is_retryable_error(result), (
        f"{_driver_id(driver)} lost the transient marker on the final "
        f"attempt: {result!r}"
    )


@pytest.mark.parametrize("driver", DRIVERS, ids=_driver_id)
def test_success_returns_the_description_unchanged(
        driver, monkeypatch, tmp_path, image):
    result, script = _describe(driver, monkeypatch, tmp_path, image,
                               [("ok", OK)])
    assert result == OK
    assert script.calls == 1, "a successful call must not be repeated"
    assert not _is_retryable_error(result), (
        "a real description was mistaken for a transient error -- it would be "
        "thrown away and re-requested"
    )


@pytest.mark.parametrize("driver", DRIVERS, ids=_driver_id)
def test_timeout_is_treated_as_transient(driver, monkeypatch, tmp_path, image):
    result, _ = _describe(driver, monkeypatch, tmp_path, image,
                          [("timeout", None)])
    assert _is_retryable_error(result), (
        f"{_driver_id(driver)} reported a timeout as permanent: {result!r}"
    )


@pytest.mark.parametrize("driver", DRIVERS, ids=_driver_id)
def test_malformed_response_does_not_escape_as_an_exception(
        driver, monkeypatch, tmp_path, image):
    """A garbage response must become an error string, not crash the batch.

    wxPython swallows exceptions in event handlers, so one escaping here shows
    up to the user as a button that does nothing.
    """
    result, _ = _describe(driver, monkeypatch, tmp_path, image,
                          [("garbage", None)])
    assert isinstance(result, str) and result, (
        f"{_driver_id(driver)} returned {result!r} for an unparseable response"
    )


# ===========================================================================
# The formatter is the contract
# ===========================================================================

@pytest.mark.parametrize("kind", ErrorKind.ALL)
@pytest.mark.parametrize("status_code", [None, 429, 500, 503, 401, 400])
def test_formatter_output_always_classifies_as_its_kind(kind, status_code):
    """format_provider_error and _is_retryable_error must never disagree.

    The whole point of routing every provider through one formatter is that
    this can be checked exhaustively instead of hoping each author remembered
    the convention. When a numeric status is supplied it decides; without one,
    the kind does.
    """
    text = format_provider_error(
        provider="Test", kind=kind, status_code=status_code,
        message="something went wrong", timestamp="2026-07-28 12:00:00,000")

    if status_code is not None:
        expected = kind_for_status(status_code) in RETRYABLE_KINDS
    else:
        expected = kind in RETRYABLE_KINDS

    assert _is_retryable_error(text) is expected, (
        f"kind={kind} status={status_code} produced {text!r}, which "
        f"_is_retryable_error reads as {not expected}"
    )


def test_kind_for_status_covers_the_boundaries():
    assert kind_for_status(429) == ErrorKind.RATE_LIMIT
    assert kind_for_status(401) == ErrorKind.AUTH
    assert kind_for_status(403) == ErrorKind.AUTH
    assert kind_for_status(400) == ErrorKind.INVALID_REQUEST
    assert kind_for_status(499) == ErrorKind.INVALID_REQUEST
    assert kind_for_status(500) == ErrorKind.SERVER_ERROR
    assert kind_for_status(599) == ErrorKind.SERVER_ERROR
    assert kind_for_status(None) == ErrorKind.UNKNOWN
    assert kind_for_status("nonsense") == ErrorKind.UNKNOWN


def test_provider_error_carries_the_status_as_a_field():
    """The decorator's exception branch reads e.status_code -- no parsing."""
    err = ai_providers.ProviderError("boom", status_code=503, provider="Ollama")
    assert err.status_code == 503
    assert err.kind == ErrorKind.SERVER_ERROR
    assert err.is_retryable is True
    assert _is_retryable_error(err.as_description()) is True

    denied = ai_providers.ProviderError("nope", status_code=401, provider="X")
    assert denied.is_retryable is False


def test_no_provider_writes_a_status_code_string_by_hand():
    """Wording lives in format_provider_error, and only there.

    Two commits two weeks apart disagreed about this wording while both looked
    correct in review. Keeping every "(status code: ...)" literal inside one
    function is what makes that impossible rather than unlikely.
    """
    src = (_ROOT / "imagedescriber" / "ai_providers.py").read_text(
        encoding="utf-8")

    formatter_start = src.index("def _status_token(")
    formatter_end = src.index("def provider_error_from_exception(")
    allowed = src[formatter_start:formatter_end]

    offenders = []
    for lineno, line in enumerate(src.splitlines(), start=1):
        if "status code:" not in line:
            continue
        stripped = line.strip()
        if stripped.startswith("#") or line in allowed:
            continue
        # Docstrings and the classifier's own regexes describe the format
        # rather than emitting it.
        if 'r"status code' in line or '"(status code' in line:
            continue
        offenders.append(f"  line {lineno}: {stripped}")

    assert not offenders, (
        "these lines build a status-code string outside format_provider_error:\n"
        + "\n".join(offenders)
        + "\n\nCall format_provider_error(provider=..., kind=..., "
          "status_code=...) instead."
    )
