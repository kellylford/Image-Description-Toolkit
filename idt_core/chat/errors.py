"""Classifying chat failures into "worth retrying" and "not".

Note on duplication, stated plainly: ``imagedescriber/ai_providers.py`` already
has an ``ErrorKind`` / ``ProviderError`` / ``retry_on_api_error`` system (issue
#228), and only batch describe uses it — chat has never retried anything. The
right end state is one classifier. Moving that one would change ImageDescriber,
which is out of scope for this work, so this module classifies chat failures
for now and the two should be merged when the GUI adopts this engine.

It is not a copy. The older one matches on message text, which is what let
``"Error: HTTP 500"`` go unrecognised for nine months because it contains no
"status code". This one reads ``status_code`` off the SDK exception, and only
falls back to text when there is no structured status to read.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

__all__ = ["ErrorKind", "ChatError", "classify", "RETRYABLE_KINDS"]


class ErrorKind(Enum):
    RATE_LIMIT = "rate_limit"
    SERVER = "server"
    TIMEOUT = "timeout"
    CONNECTION = "connection"
    AUTH = "auth"
    BAD_REQUEST = "bad_request"
    NOT_FOUND = "not_found"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


#: Transient conditions. Everything else fails immediately: retrying a bad API
#: key or a malformed request just wastes the user's time.
RETRYABLE_KINDS = frozenset(
    {ErrorKind.RATE_LIMIT, ErrorKind.SERVER, ErrorKind.TIMEOUT, ErrorKind.CONNECTION}
)


@dataclass
class ChatError:
    kind: ErrorKind
    message: str
    status_code: Optional[int] = None

    @property
    def retryable(self) -> bool:
        return self.kind in RETRYABLE_KINDS

    def user_message(self) -> str:
        """Phrasing aimed at someone who has to decide what to do next."""
        if self.kind is ErrorKind.AUTH:
            return f"Authentication failed: {self.message}"
        if self.kind is ErrorKind.RATE_LIMIT:
            return f"Rate limited by the provider: {self.message}"
        if self.kind is ErrorKind.CONNECTION:
            return f"Could not reach the provider: {self.message}"
        if self.kind is ErrorKind.TIMEOUT:
            return f"The provider timed out: {self.message}"
        if self.kind is ErrorKind.SERVER:
            return f"The provider had a server error: {self.message}"
        if self.kind is ErrorKind.NOT_FOUND:
            return f"Model or endpoint not found: {self.message}"
        return self.message


def _status_from(exc: BaseException) -> Optional[int]:
    """Pull an HTTP status off an SDK exception, whatever it calls it."""
    for attr in ("status_code", "http_status", "code"):
        value = getattr(exc, attr, None)
        if isinstance(value, int) and 100 <= value < 600:
            return value
    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None)
    if isinstance(status, int):
        return status
    return None


def _kind_for_status(status: int) -> ErrorKind:
    if status == 429:
        return ErrorKind.RATE_LIMIT
    if status in (401, 403):
        return ErrorKind.AUTH
    if status == 404:
        return ErrorKind.NOT_FOUND
    if 500 <= status < 600:
        return ErrorKind.SERVER
    if 400 <= status < 500:
        return ErrorKind.BAD_REQUEST
    return ErrorKind.UNKNOWN


def _kind_from_text(text: str) -> ErrorKind:
    lowered = text.lower()
    # Ordered so the most specific wins: "connection timed out" is a timeout.
    if "timed out" in lowered or "timeout" in lowered:
        return ErrorKind.TIMEOUT
    if "rate limit" in lowered or "too many requests" in lowered:
        return ErrorKind.RATE_LIMIT
    if any(s in lowered for s in ("unauthorized", "api key", "authentication", "invalid_api_key")):
        return ErrorKind.AUTH
    if any(s in lowered for s in ("connection", "refused", "unreachable", "dns", "network")):
        return ErrorKind.CONNECTION
    if "not found" in lowered or "no such model" in lowered:
        return ErrorKind.NOT_FOUND
    for marker in ("http 500", "http 502", "http 503", "http 504",
                   "internal server error", "bad gateway", "service unavailable"):
        if marker in lowered:
            return ErrorKind.SERVER
    return ErrorKind.UNKNOWN


def classify(exc: BaseException) -> ChatError:
    """Turn any exception into a :class:`ChatError`.

    Structured status first, exception type second, message text last. Text is
    the weakest signal and is only consulted when nothing better exists.
    """
    message = str(exc) or exc.__class__.__name__

    if isinstance(exc, (KeyboardInterrupt, GeneratorExit)):
        return ChatError(ErrorKind.CANCELLED, "Cancelled")

    status = _status_from(exc)
    if status is not None:
        return ChatError(_kind_for_status(status), message, status)

    if isinstance(exc, TimeoutError):
        return ChatError(ErrorKind.TIMEOUT, message)
    if isinstance(exc, (ConnectionError, OSError)):
        # OSError covers socket errors; refine via text where possible.
        kind = _kind_from_text(message)
        return ChatError(
            kind if kind is not ErrorKind.UNKNOWN else ErrorKind.CONNECTION, message
        )
    if isinstance(exc, ValueError):
        kind = _kind_from_text(message)
        return ChatError(kind if kind is not ErrorKind.UNKNOWN else ErrorKind.BAD_REQUEST, message)

    return ChatError(_kind_from_text(message), message)
