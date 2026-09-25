"""
Apple Intelligence provider — on-device image descriptions and chat through the
Foundation Models framework on macOS 27.

Nothing here talks to a network. The model runs on the machine's Neural Engine,
needs no API key and no account, and costs nothing per image.

How it connects. macOS 27 ships ``/usr/bin/fm``, whose ``fm serve`` mode exposes
a local OpenAI-compatible Chat Completions endpoint that accepts base64
``image_url`` parts — the same wire format IDT's OpenAI provider already emits.
So IDT starts one ``fm serve`` per process, talks to it over a Unix domain
socket, and kills it at exit. The alternative, one ``fm respond`` subprocess per
image, cold-starts the model every time and reports no token counts.

**It is not a drop-in for the OpenAI SDK**, which is why this module exists
rather than a ``base_url`` override. Measured against the shipping CLI on macOS
27.2 (9/24/2026), three behaviours differ, two of them silently:

* ``stream`` defaults to **true**, the opposite of the OpenAI API. A request
  that omits it gets ``text/event-stream`` back, and a JSON parse of that fails
  on an empty body. Every request here sets ``stream`` explicitly.
* ``max_tokens`` is **ignored**; ``max_completion_tokens`` is honoured exactly.
  Sending the wrong one produces a reply of whatever length the model felt like,
  with no error.
* Requests **serialize** server-side. Two concurrent describes took 11.2s
  against ~4–6s each alone, so batch callers gain nothing from a worker pool.

Two things the cloud providers need are unnecessary here: the server downscales
internally (a 9000×6750 JPEG and a 640×480 one both reported ~206 prompt tokens),
and PNG is accepted alongside JPEG.

Setup is one command the user must run themselves, once per machine:
``sudo fm license``. It is machine-wide and needs an administrator, so IDT
detects it and says so rather than failing opaquely.
"""
from __future__ import annotations

import atexit
import base64
import http.client
import json
import os
import platform
import shutil
import socket
import subprocess
import tempfile
import threading
import time
from typing import Iterator, List, Optional, Sequence, Tuple

from .base import BaseProvider, DescriptionResult

__all__ = [
    "APPLE_MODELS",
    "APPLE_MODEL_METADATA",
    "DEFAULT_MODEL",
    "AppleFMError",
    "AppleProvider",
    "check_ready",
    "find_fm",
    "is_available",
    "license_accepted",
    "post_chat",
    "server",
    "shutdown_server",
    "usage_tokens",
]

#: The only model IDT offers. ``fm`` also lists ``pcc`` (Private Cloud Compute),
#: but it reports "not available in this context. Please use the Terminal app."
#: when ``fm`` is launched from another process — which is always, here. Offering
#: a model that fails for structural reasons would be a picker entry that never
#: works.
APPLE_MODELS = ["system"]
DEFAULT_MODEL = "system"

#: Picker metadata, read by ``catalog`` like the other providers' tables.
#: ``context_window`` is Apple's published on-device figure. ``max_output`` is
#: left unset: the server honours whatever ``max_completion_tokens`` we ask for
#: and documents no ceiling, and the catalog contract is that an unknown number
#: stays None rather than becoming a guess.
APPLE_MODEL_METADATA: dict = {
    "system": {
        "name": "On-device (Apple Intelligence)",
        "description": "Runs on this Mac. No API key, no account, no cost, works offline",
        "context_window": 65536,
        "supports_vision": True,
        "cost": "free",
        "recommended": True,
    },
}

#: Where the binary lives on a stock install. ``shutil.which`` is tried first so
#: a PATH override still wins.
FM_PATH = "/usr/bin/fm"

DESCRIBE_TIMEOUT_SECONDS = 300

#: How long to wait for a freshly spawned ``fm serve`` to answer /health.
#: Measured at ~1s on an M-series Mac; the margin covers a first run that has to
#: page the model in.
SERVER_START_TIMEOUT = 45.0

DESCRIBE_SYSTEM_PROMPT = (
    "You describe images. Follow the user's instructions about the image and "
    "reply with only the description itself, no preamble."
)
CHAT_SYSTEM_PROMPT = "You are a helpful assistant."

_NOT_MACOS_HINT = (
    "Apple Intelligence needs macOS 27 or later on an Apple Silicon Mac."
)
_NO_FM_HINT = (
    "Apple Intelligence is not available: this Mac has no /usr/bin/fm, which "
    "ships with macOS 27. Check that macOS is up to date and that Apple "
    "Intelligence is turned on in System Settings."
)
#: The license is accepted once per machine by an administrator, so this is an
#: instruction to the user rather than something IDT can do for them.
LICENSE_HINT = (
    "Apple's Foundation Models terms have not been accepted on this Mac. "
    "Open Terminal and run:  sudo fm license"
)

#: Substring of the CLI's refusal when the terms have not been accepted.
_LICENSE_MARKER = "NOT AGREED"


class AppleFMError(RuntimeError):
    """Apple Intelligence is unavailable, unlicensed, or a request failed."""


# ---------------------------------------------------------------------------
# Locating and checking the CLI
# ---------------------------------------------------------------------------


def find_fm() -> Optional[str]:
    """Path to the ``fm`` executable, or None."""
    found = shutil.which("fm")
    if found:
        return found
    return FM_PATH if os.path.isfile(FM_PATH) else None


def is_available() -> bool:
    """True when this machine could run the provider. Cheap: no subprocess.

    Says nothing about the license or whether Apple Intelligence is switched
    on — both are checked at first use, where the error can explain the fix.
    """
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        return False
    return find_fm() is not None


#: Set once the terms have been confirmed accepted, so a picker refresh does not
#: spawn a subprocess every time. A machine whose state changes later still
#: fails loudly: the request itself reports it.
_license_confirmed = False
_license_lock = threading.RLock()


def license_accepted(fm: Optional[str] = None, force: bool = False) -> bool:
    """True when Apple's Foundation Models terms have been accepted here.

    Runs ``fm models``, which refuses with a recognisable banner until an
    administrator has run ``sudo fm license``.

    The decision is made on the output, not the exit code: ``fm models`` exits
    non-zero whenever any listed model is unavailable, and ``pcc`` always is
    from a process that is not Terminal. Reading the status as a failure would
    report every licensed Mac as unlicensed.
    """
    global _license_confirmed
    with _license_lock:
        if _license_confirmed and not force:
            return True
    fm = fm or find_fm()
    if not fm:
        return False
    try:
        result = subprocess.run(
            [fm, "models"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    combined = (result.stdout or "") + (result.stderr or "")
    if _LICENSE_MARKER in combined.upper():
        return False
    # Licensed machines list the on-device model here. Anything else -- an
    # unrecognised refusal, a future output format -- is treated as not ready,
    # so the failure arrives with a hint rather than as a socket error later.
    if DEFAULT_MODEL not in combined:
        return False
    with _license_lock:
        _license_confirmed = True
    return True


def check_ready(fm: Optional[str] = None) -> None:
    """Raise :class:`AppleFMError` unless a request could actually succeed."""
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise AppleFMError(_NOT_MACOS_HINT)
    fm = fm or find_fm()
    if not fm:
        raise AppleFMError(_NO_FM_HINT)
    if not license_accepted(fm):
        raise AppleFMError(LICENSE_HINT)


# ---------------------------------------------------------------------------
# HTTP over a Unix domain socket
# ---------------------------------------------------------------------------


class _UnixHTTPConnection(http.client.HTTPConnection):
    """``http.client`` speaking to a Unix socket instead of a TCP port.

    A socket rather than a port because the CLI's own help recommends it for
    local bindings, and because a port would need allocation, collision handling
    and a firewall prompt for something that never leaves the machine.
    """

    def __init__(self, socket_path: str, timeout: Optional[float] = None):
        super().__init__("localhost", timeout=timeout or socket._GLOBAL_DEFAULT_TIMEOUT)
        self._socket_path = socket_path

    def connect(self) -> None:  # noqa: D102 - http.client interface
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        if self.timeout is not None and self.timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
            sock.settimeout(self.timeout)
        sock.connect(self._socket_path)
        self.sock = sock


# ---------------------------------------------------------------------------
# Server lifecycle
# ---------------------------------------------------------------------------


class FmServer:
    """One ``fm serve`` process, started on demand and shared by every request.

    Starting it lazily rather than at import keeps a Mac that never selects this
    provider from spawning anything, and keeps the cost off the wx UI thread at
    startup. ``ensure_running`` is idempotent and re-spawns a server that died,
    so a crash mid-batch costs one image rather than the rest of the run.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._proc: Optional[subprocess.Popen] = None
        self._dir: Optional[str] = None
        self._socket_path: Optional[str] = None
        self._log_path: Optional[str] = None

    # -- state ----------------------------------------------------------

    @property
    def socket_path(self) -> Optional[str]:
        return self._socket_path

    def is_running(self) -> bool:
        with self._lock:
            return self._proc is not None and self._proc.poll() is None

    # -- lifecycle ------------------------------------------------------

    def ensure_running(self, fm: Optional[str] = None) -> str:
        """Start the server if needed and return its socket path."""
        with self._lock:
            if self.is_running() and self._socket_path:
                return self._socket_path
            self._cleanup_locked()
            return self._start_locked(fm)

    def _start_locked(self, fm: Optional[str]) -> str:
        fm = fm or find_fm()
        check_ready(fm)

        # Under /tmp, not the default temp dir: a Unix socket path is capped at
        # ~104 bytes on macOS and the per-user /var/folders path eats most of
        # that before the filename. mkdtemp still gives the directory 0700.
        self._dir = tempfile.mkdtemp(prefix="idt-fm-", dir="/tmp")
        self._socket_path = os.path.join(self._dir, "fm.sock")
        self._log_path = os.path.join(self._dir, "fm.log")

        try:
            log = open(self._log_path, "wb")
        except OSError as exc:
            self._cleanup_locked()
            raise AppleFMError(f"Could not start Apple Intelligence: {exc}")
        try:
            # stdout and stderr go to a file, never a pipe: nothing in this
            # process reads them during a run, and a full pipe buffer would
            # wedge the server mid-batch.
            self._proc = subprocess.Popen(
                [fm, "serve", "--socket", self._socket_path],
                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        except OSError as exc:
            log.close()
            self._cleanup_locked()
            raise AppleFMError(f"Could not start Apple Intelligence: {exc}")
        finally:
            log.close()

        self._await_health_locked()
        return self._socket_path

    def _await_health_locked(self) -> None:
        deadline = time.monotonic() + SERVER_START_TIMEOUT
        last_error = ""
        while time.monotonic() < deadline:
            if self._proc.poll() is not None:
                detail = self._log_tail() or f"exit code {self._proc.returncode}"
                self._cleanup_locked()
                raise AppleFMError(f"Apple Intelligence server stopped: {detail}")
            try:
                health = self._get_json("/health", timeout=5.0)
            except Exception as exc:                        # noqa: BLE001
                last_error = str(exc)
                time.sleep(0.1)
                continue
            self._check_model_available(health)
            return
        detail = self._log_tail() or last_error or "no response"
        self._cleanup_locked()
        raise AppleFMError(
            f"Apple Intelligence server did not start within "
            f"{int(SERVER_START_TIMEOUT)}s: {detail}"
        )

    @staticmethod
    def _check_model_available(health: dict) -> None:
        """Raise when the on-device model itself is unavailable.

        Apple Intelligence can be switched off, or its model still downloading,
        on a machine where ``fm`` runs perfectly well. The server reports that
        per model, and its ``reason`` is written for a person, so it is passed
        through rather than replaced.
        """
        for entry in health.get("models") or ():
            if entry.get("name") == DEFAULT_MODEL and not entry.get("available"):
                reason = entry.get("reason") or "the on-device model is unavailable"
                raise AppleFMError(
                    f"Apple Intelligence is not ready: {reason} "
                    "Check System Settings > Apple Intelligence & Siri."
                )

    def _log_tail(self, limit: int = 400) -> str:
        if not self._log_path:
            return ""
        try:
            with open(self._log_path, "r", encoding="utf-8", errors="replace") as fh:
                return fh.read().strip()[-limit:]
        except OSError:
            return ""

    def _cleanup_locked(self) -> None:
        proc, self._proc = self._proc, None
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        if self._dir:
            shutil.rmtree(self._dir, ignore_errors=True)
        self._dir = self._socket_path = self._log_path = None

    def stop(self) -> None:
        """Stop the server and remove its socket. Safe to call repeatedly."""
        with self._lock:
            self._cleanup_locked()

    # -- requests -------------------------------------------------------

    def _get_json(self, path: str, timeout: float) -> dict:
        conn = _UnixHTTPConnection(self._socket_path, timeout=timeout)
        try:
            conn.request("GET", path)
            response = conn.getresponse()
            return json.loads(response.read().decode("utf-8"))
        finally:
            conn.close()

    def open_chat(self, payload: dict, timeout: float) -> Tuple[http.client.HTTPConnection,
                                                                http.client.HTTPResponse]:
        """POST to /v1/chat/completions and return ``(connection, response)``.

        The caller owns both and must close the connection — streaming reads the
        response incrementally, so this cannot close it here.
        """
        socket_path = self.ensure_running()
        body = json.dumps(payload).encode("utf-8")
        conn = _UnixHTTPConnection(socket_path, timeout=timeout)
        try:
            conn.request(
                "POST", "/v1/chat/completions", body=body,
                headers={"Content-Type": "application/json",
                         "Content-Length": str(len(body))},
            )
            response = conn.getresponse()
        except OSError as exc:
            conn.close()
            raise AppleFMError(f"Apple Intelligence request failed: {exc}")
        if response.status != 200:
            detail = response.read().decode("utf-8", "replace").strip()[:300]
            conn.close()
            raise AppleFMError(
                f"Apple Intelligence returned HTTP {response.status}: {detail or 'no detail'}"
            )
        return conn, response


#: The process-wide server. One per process is right: requests serialize inside
#: the server anyway, so a second would add startup cost and memory without
#: adding throughput.
_server = FmServer()


def server() -> FmServer:
    return _server


def shutdown_server() -> None:
    """Stop the shared server. Registered at exit; also useful in tests."""
    _server.stop()


atexit.register(shutdown_server)


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


def build_payload(
    messages: Sequence[dict],
    model: str = DEFAULT_MODEL,
    *,
    stream: bool,
    max_output_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
) -> dict:
    """The request body.

    ``stream`` is always set, never left to the server's default — its default
    is ``true``, so omitting it hands a JSON caller an event stream.
    ``max_completion_tokens`` is the only length control the server honours;
    ``max_tokens`` is accepted and ignored.
    """
    payload = {
        "model": model or DEFAULT_MODEL,
        "messages": list(messages),
        "stream": bool(stream),
    }
    if stream:
        # Without this a streamed turn carries no usage at all, and chat's
        # context gauge and billed-token total would silently read zero.
        payload["stream_options"] = {"include_usage": True}
    if max_output_tokens:
        payload["max_completion_tokens"] = int(max_output_tokens)
    if temperature is not None:
        payload["temperature"] = temperature
    return payload


def post_chat(payload: dict, timeout: float = DESCRIBE_TIMEOUT_SECONDS) -> dict:
    """Send a non-streaming request and return the decoded response."""
    conn, response = _server.open_chat(payload, timeout)
    try:
        raw = response.read().decode("utf-8", "replace")
    finally:
        conn.close()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise AppleFMError(
            f"Apple Intelligence returned an unreadable response: {raw[:200]!r}"
        )


def stream_chat(payload: dict,
                timeout: float = DESCRIBE_TIMEOUT_SECONDS) -> Iterator[Tuple[str, object]]:
    """Send a streaming request, yielding ``("delta", text)`` then ``("done", dict)``.

    A generator so a consumer can abandon it: the ``finally`` closes the socket,
    which is what makes Stop work in chat.
    """
    conn, response = _server.open_chat(payload, timeout)
    final: dict = {}
    try:
        for raw_line in response:
            line = raw_line.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                event = json.loads(data)
            except json.JSONDecodeError:
                continue
            if event.get("usage"):
                final["usage"] = event["usage"]
            for choice in event.get("choices") or ():
                text = (choice.get("delta") or {}).get("content")
                if text:
                    yield ("delta", text)
                if choice.get("finish_reason"):
                    final["finish_reason"] = choice["finish_reason"]
    finally:
        conn.close()
    yield ("done", final)


def response_text(data: dict) -> str:
    """The assistant text from a non-streaming response."""
    choices = data.get("choices") or []
    if not choices:
        raise AppleFMError("Apple Intelligence returned no response.")
    message = choices[0].get("message") or {}
    refusal = message.get("refusal")
    if refusal:
        raise AppleFMError(f"Apple Intelligence declined: {refusal}")
    text = (message.get("content") or "").strip()
    if not text:
        reason = choices[0].get("finish_reason") or "no content"
        raise AppleFMError(f"Apple Intelligence returned an empty response ({reason}).")
    return text


def usage_tokens(data: dict) -> Tuple[int, int]:
    """``(input, output)`` tokens from a response, zero when absent."""
    usage = data.get("usage") or {}
    return usage.get("prompt_tokens") or 0, usage.get("completion_tokens") or 0


# ---------------------------------------------------------------------------
# Image content
# ---------------------------------------------------------------------------

#: Verified accepted as data URLs. Anything else is re-encoded rather than
#: gambled on — the caller has already converted HEIC, BMP and TIFF, so this
#: catches GIF and WebP.
SUPPORTED_IMAGE_MIMES = ("image/jpeg", "image/png")


def _as_supported_image(image_bytes: bytes, mime_type: str) -> Tuple[bytes, str]:
    if mime_type in SUPPORTED_IMAGE_MIMES:
        return image_bytes, mime_type
    import io

    from PIL import Image

    img = Image.open(io.BytesIO(image_bytes))
    if img.mode != "RGB":
        img = img.convert("RGB")
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=85)
    return out.getvalue(), "image/jpeg"


def image_part(image_bytes: bytes, mime_type: str) -> dict:
    """An ``image_url`` content part.

    No downscaling: the server resizes internally, and a 9000×6750 JPEG reported
    the same prompt-token count as a 640×480 one. This is the one place the
    Apple path is simpler than the cloud providers, which all need a size guard.
    """
    image_bytes, mime_type = _as_supported_image(image_bytes, mime_type)
    payload = base64.standard_b64encode(image_bytes).decode("ascii")
    return {"type": "image_url",
            "image_url": {"url": f"data:{mime_type};base64,{payload}"}}


def describe_messages(image_bytes: bytes, mime_type: str, prompt: str,
                      system_prompt: str = DESCRIBE_SYSTEM_PROMPT) -> List[dict]:
    """The message list for one image description."""
    messages: List[dict] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": [
        {"type": "text", "text": prompt},
        image_part(image_bytes, mime_type),
    ]})
    return messages


# ---------------------------------------------------------------------------
# Image description
# ---------------------------------------------------------------------------


class AppleProvider(BaseProvider):
    """One image, one prompt, one description, entirely on this Mac."""

    def __init__(self, model: str = DEFAULT_MODEL, check: bool = True):
        self._model = model or DEFAULT_MODEL
        if check:
            check_ready()

    @property
    def provider_name(self) -> str:
        return "apple"

    @property
    def model_name(self) -> str:
        return self._model

    def describe(self, image_bytes: bytes, mime_type: str, prompt: str) -> DescriptionResult:
        payload = build_payload(
            describe_messages(image_bytes, mime_type, prompt),
            self._model, stream=False,
        )
        data = post_chat(payload)
        input_tokens, output_tokens = usage_tokens(data)
        return DescriptionResult(
            text=response_text(data),
            model=self._model,
            provider="apple",
            input_tokens=input_tokens or None,
            output_tokens=output_tokens or None,
        )
