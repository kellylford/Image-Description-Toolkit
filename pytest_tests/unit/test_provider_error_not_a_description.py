"""A provider failure must never be stored as the image's description.

Issue #230. Providers report failure by RETURNING a string. The batch worker
tested only whether that string was non-empty:

    description = provider.describe_image(processing_path, prompt, self.model)
    if description and description.strip():
        break

"Rate limit exceeded (status code: 429) - (2026-07-28 ...)" is perfectly
non-empty. So it broke out of the loop, had a location byline and token counts
appended to it, and was posted as ProcessingCompleteEventData with
result_ok = True (workers_wx.py 513 -> 549 -> 279 -> 309).

The user's workspace then held an API error where a description belonged. It
counted toward "X of Y images described" and was exported to HTML. No failure
event fired, nothing was logged, and the run reported success.

This is the same root cause as the nine-month retry bug in #228: success and
failure share a type, so nothing can tell them apart. These tests pin the
behaviour at the two levels where it can be checked without a wx.App -- the
predicate, and the worker's guard.
"""

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "imagedescriber"))

from ai_providers import (  # noqa: E402
    ErrorKind,
    format_provider_error,
    is_provider_error,
)

wx = pytest.importorskip("wx", reason="workers_wx imports wx at module scope")

from workers_wx import (  # noqa: E402
    ProviderCallFailed,
    raise_if_provider_error,
)


REAL_DESCRIPTIONS = [
    "A weathered wooden dock with three boats moored alongside.",
    "A cluttered desk with a coffee cup and an open notebook.",
    "Two people walking a dog along a beach at sunset.",
    # Awkward but legitimate content that must not trip the predicate.
    "A server rack with a status display reading 500 units remaining.",
    "A screenshot of a terminal showing an error message.",
]


# ---------------------------------------------------------------------------
# The predicate
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("kind", ErrorKind.ALL)
@pytest.mark.parametrize("status_code", [None, 429, 500, 503, 401, 400])
def test_every_formatted_error_is_recognised_as_an_error(kind, status_code):
    """Exhaustive over the formatter, so no error kind can slip through.

    Checking the formatter's whole output space is what makes this reliable
    rather than a guess about wording -- the same approach used for
    _is_retryable_error in test_provider_contract.py.
    """
    text = format_provider_error(
        provider="Test", kind=kind, status_code=status_code,
        message="something went wrong", timestamp="2026-07-28 12:00:00,000")

    assert is_provider_error(text), (
        f"kind={kind} status={status_code} produced {text!r}, which would be "
        "stored as the image's description"
    )


@pytest.mark.parametrize("text", REAL_DESCRIPTIONS)
def test_real_descriptions_are_not_mistaken_for_errors(text):
    """A false positive would throw away work the user paid an API for."""
    assert not is_provider_error(text), (
        f"{text!r} was classified as a provider failure and would be discarded"
    )


def test_availability_messages_are_errors():
    """These are returned before a request is ever made."""
    for text in (
        "Error: OpenAI API key not configured or SDK not installed",
        "Error: Claude API key not configured or SDK not installed",
        "Error: MLX provider not available. Requires macOS with Apple Silicon",
        "Error: No content in response",
    ):
        assert is_provider_error(text), text


def test_non_strings_are_not_errors():
    for value in (None, 42, [], {"a": 1}):
        assert is_provider_error(value) is False


# ---------------------------------------------------------------------------
# The worker's guard
# ---------------------------------------------------------------------------

def test_a_real_description_passes_through_unchanged():
    text = REAL_DESCRIPTIONS[0]
    assert raise_if_provider_error(text, "Ollama", "gemma4") == text


@pytest.mark.parametrize("status,label", [
    (429, "rate limit"), (500, "server error"),
    (401, "auth failure"), (400, "bad request"),
])
def test_an_api_failure_raises_instead_of_becoming_a_description(status, label):
    """The exact defect: this used to return the error string as a description."""
    error = format_provider_error(
        provider="Ollama", kind=ErrorKind.UNKNOWN, status_code=status,
        message="upstream failed", timestamp="2026-07-28 12:00:00,000")

    with pytest.raises(ProviderCallFailed) as caught:
        raise_if_provider_error(error, "Ollama", "gemma4:31b-cloud")

    # The provider, model and original text all have to survive: this message
    # is what reaches ProcessingFailedEventData and therefore the user.
    message = str(caught.value)
    assert "Ollama" in message and "gemma4:31b-cloud" in message
    assert str(status) in message, f"{label} lost its status code"


def test_the_raised_error_reaches_the_failure_path_as_an_exception():
    """run() converts any exception into ProcessingFailedEventData.

    _process_with_ai wraps its body in `except Exception as e: raise`, and
    run() turns that into a failure event. So raising here is what makes a
    failed image show up as failed rather than as a described one.
    """
    error = format_provider_error(
        provider="OpenAI API", kind=ErrorKind.RATE_LIMIT, status_code=429,
        message="", timestamp="2026-07-28 12:00:00,000")

    with pytest.raises(Exception) as caught:
        raise_if_provider_error(error, "OpenAI", "gpt-4o")

    assert isinstance(caught.value, Exception)


def test_the_worker_actually_calls_the_guard():
    """The helper is only useful if the describe_image loop invokes it.

    Everything above tests raise_if_provider_error in isolation; deleting the
    single call in _process_with_ai would leave all of it green while the bug
    returned. This checks the wiring, since driving the real worker needs a
    wx.App, a parent window and an event loop.
    """
    source = (_ROOT / "imagedescriber" / "workers_wx.py").read_text(
        encoding="utf-8")

    call = source.index("provider.describe_image(")
    guard = source.index("raise_if_provider_error(", call)
    empty_check = source.index("if description and description.strip():", call)

    assert guard < empty_check, (
        "raise_if_provider_error must run BEFORE the emptiness check, "
        "otherwise an error string is accepted as the description."
    )
    between = source[call:guard]
    assert between.count("\n") < 12, (
        "the guard has drifted away from the describe_image call; make sure "
        "nothing consumes the result before it is validated"
    )


def test_empty_and_whitespace_are_left_to_the_empty_response_retry():
    """Empty results are a different failure mode with its own retry policy.

    The worker retries empty responses when finish_reason is 'length'. Turning
    them into exceptions here would bypass that and lose descriptions that a
    second attempt would have produced.
    """
    for value in ("", "   ", "\n"):
        assert raise_if_provider_error(value, "Ollama", "gemma4") == value
