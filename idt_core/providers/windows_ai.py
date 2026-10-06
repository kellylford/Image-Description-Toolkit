"""
Windows AI provider: on-device image descriptions on Copilot+ PCs, through Windows' own model
(``Microsoft.Windows.AI.Imaging.ImageDescriptionGenerator``).

Nothing here talks to a network. The model runs on the PC's NPU, needs no API key and no
account, and costs nothing per image.

How it connects. Windows only lets a *packaged* app use the model; called from an ordinary
process the API refuses with "Access is denied" (0x80070005) at its first call. Python can't
be given a package identity, so IDT ships a small packaged helper (``windows_ai_helper/``, C#)
and runs it: one ``idt-windows-ai --serve`` per process, talking JSON lines over its stdin and
stdout, started on first use and stopped at exit. The helper's README documents the protocol;
its failure codes are mapped to IDT's batch handling here.

What differs from every other provider:

* **There is no prompt.** The model offers four fixed kinds of description instead
  (Accessible, Detailed, Brief, Diagram), so the kinds are this provider's *models* and the
  prompt passed to :meth:`WindowsAIProvider.describe` is ignored. Callers say so rather than
  pretend otherwise; see :data:`PROMPT_NAME`.
* **It describes; it can't chat.** The registry marks it ``chat=False`` and chat refuses it.
* **No token counts.** The API reports none.

Setup is installing the helper, which IDT's installer does on a Copilot+ PC. The model itself
may need preparing (downloading) the first time; :func:`prepare` does that.
"""
from __future__ import annotations

import atexit
import base64
import io
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
from typing import List, Optional

from .base import BaseProvider, DescriptionResult

__all__ = [
    "DEFAULT_MODEL",
    "PROMPT_NAME",
    "WINDOWS_AI_MODELS",
    "WINDOWS_AI_MODEL_METADATA",
    "WindowsAIError",
    "WindowsAIProvider",
    "check_ready",
    "find_helper",
    "is_available",
    "prepare",
    "readiness",
    "shutdown_helper",
]

#: The description kinds, which are this provider's models. The first is the default:
#: Accessible is the one Microsoft writes for people who are blind or have low vision.
WINDOWS_AI_MODELS: List[str] = ["accessible", "detailed", "brief", "diagram"]
DEFAULT_MODEL = WINDOWS_AI_MODELS[0]

#: Picker metadata, read by ``catalog`` like the other providers' tables. No context window or
#: output limit is published, and inventing one would break the catalog's rule that an unknown
#: stays None.
WINDOWS_AI_MODEL_METADATA: dict = {
    "accessible": {
        "name": "Accessible",
        "description": "A long description written for people who are blind or have low vision. "
                       "Runs on this PC's NPU: no key, no cost, works offline",
        "supports_vision": True,
        "cost": "free",
        "recommended": True,
    },
    "detailed": {
        "name": "Detailed",
        "description": "A long, detailed description. Runs on this PC's NPU",
        "supports_vision": True,
        "cost": "free",
    },
    "brief": {
        "name": "Brief",
        "description": "A short caption. Runs on this PC's NPU",
        "supports_vision": True,
        "cost": "free",
    },
    "diagram": {
        "name": "Diagram",
        "description": "Suited to charts and diagrams. Runs on this PC's NPU",
        "supports_vision": True,
        "cost": "free",
    },
}

#: What a description records as its prompt. The model takes none, so recording the user's
#: prompt would say something that didn't happen; an empty name shows as a blank "Prompt:" in
#: exports.
PROMPT_NAME = "none"

#: The command the helper's package adds. Started as this, Windows runs it with the package's
#: identity, which the model requires.
HELPER_ALIAS = "idt-windows-ai.exe"

#: Windows 11 24H2. The AI APIs don't exist before it.
MIN_WINDOWS_BUILD = 26100

#: The helper protocol this module speaks. The helper reports its own in ``--check``.
PROTOCOL_VERSION = 1

#: One picture usually takes 2 to 4 s, occasionally 12 when Windows is using the NPU for
#: something else. The first request of a run also waits for the model to load.
DESCRIBE_TIMEOUT_SECONDS = 180.0
CHECK_TIMEOUT_SECONDS = 30.0
#: Preparing may download the model the first time.
PREPARE_TIMEOUT_SECONDS = 900.0

#: What the helper accepts; anything else is converted to JPEG here first.
SUPPORTED_IMAGE_MIMES = ("image/jpeg", "image/png", "image/bmp", "image/gif", "image/tiff")

_NOT_WINDOWS_HINT = "Windows AI runs only on Windows, on a Copilot+ PC."
_OLD_WINDOWS_HINT = (
    "Windows AI needs Windows 11 version 24H2 or later on a Copilot+ PC "
    "(this PC is on build {build})."
)
_NO_HELPER_HINT = (
    "The Windows AI helper isn't installed. IDT's installer adds it on a Copilot+ PC; "
    "reinstall IDT, or install the helper package that came with it."
)
_NO_IDENTITY_HINT = (
    "The Windows AI helper is present but isn't installed as a package, and Windows only lets "
    "a package use its model. Reinstall IDT to install it properly."
)

#: Failure codes from the helper, by what a batch should do with them.
_PER_IMAGE_CODES = {"content_filtered", "too_much_text", "unsupported_format", "decode_failed", "too_large"}
_SETUP_CODES = {"not_supported", "disabled_by_user", "blocked_by_policy"}
#: Worth one retry: the model may still be loading, or Windows hit something transient.
#: (internal_error is first retried at smaller sizes by WindowsAIProvider.describe, which
#: decides what a picture that fails at every size means; this covers the rest.)
_RETRYABLE_CODES = {"not_ready", "internal_error"}

#: No console window flashing up for the helper. Windows only: elsewhere a non-zero
#: ``creationflags`` is an error, and the test suite runs on macOS too.
_CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


class WindowsAIError(RuntimeError):
    """A Windows AI failure, carrying what a batch needs to decide what to do next.

    * ``setup``: nothing will work until the user changes something (install the helper, use a
      Copilot+ PC, turn the feature on). A batch should stop and say so.
    * ``per_image``: this picture only (a content-filter refusal, an unreadable file). Says
      nothing about the next picture, so a batch carries on (#337, #352).
    * ``status_code``: 503 for a failure worth retrying, as the GUI's classifier reads it.
    * ``timeout``: the helper didn't answer in time.
    * ``code``: the helper's failure code, when there was one.
    """

    def __init__(self, message: str, *, code: str = "", status_code: Optional[int] = None,
                 setup: bool = False, per_image: bool = False, timeout: bool = False):
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.setup = setup
        self.per_image = per_image
        self.timeout = timeout


def error_for_code(code: str, message: str) -> WindowsAIError:
    """The error for a failure code the helper reported."""
    if code in _PER_IMAGE_CODES:
        return WindowsAIError(message, code=code, per_image=True)
    if code in _SETUP_CODES:
        return WindowsAIError(message, code=code, setup=True)
    if code in _RETRYABLE_CODES:
        return WindowsAIError(message, code=code, status_code=503)
    return WindowsAIError(message, code=code)


# ---------------------------------------------------------------------------
# Finding and checking the helper
# ---------------------------------------------------------------------------


def _on_windows() -> bool:
    return sys.platform == "win32"


def _windows_build() -> int:
    try:
        return sys.getwindowsversion().build  # type: ignore[attr-defined]
    except AttributeError:
        return 0


def find_helper() -> Optional[str]:
    """Path to the helper's command, or None.

    The command is an app execution alias in ``%LOCALAPPDATA%\\Microsoft\\WindowsApps``, which
    is on PATH for most users but not for every process (a service, a stripped environment), so
    that folder is checked directly too.
    """
    found = shutil.which(HELPER_ALIAS)
    if found:
        return found
    local = os.environ.get("LOCALAPPDATA")
    if local:
        candidate = os.path.join(local, "Microsoft", "WindowsApps", HELPER_ALIAS)
        if os.path.isfile(candidate):
            return candidate
    return None


def _helper_command() -> Optional[List[str]]:
    """The command that runs the helper. A function, so tests can put a stand-in here."""
    helper = find_helper()
    return [helper] if helper else None


def is_available() -> bool:
    """True when this PC could run the provider. Cheap: no subprocess.

    Says nothing about whether this is a Copilot+ PC or the model is ready: asking needs the
    helper, so that is checked at first use (:func:`check_ready`), where the error can say why.
    """
    if not _on_windows() or _windows_build() < MIN_WINDOWS_BUILD:
        return False
    return _helper_command() is not None


def _run_helper(option: str, timeout: float) -> dict:
    """Run the helper once with ``--check`` or ``--prepare`` and return its JSON report."""
    command = _helper_command()
    if not command:
        raise WindowsAIError(_NO_HELPER_HINT, setup=True)
    try:
        result = subprocess.run(
            command + [option], capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout, stdin=subprocess.DEVNULL, creationflags=_CREATE_NO_WINDOW,
        )
    except subprocess.TimeoutExpired:
        raise WindowsAIError(f"The Windows AI helper didn't answer {option} within {timeout:.0f} seconds.",
                             timeout=True)
    except OSError as exc:
        raise WindowsAIError(f"Couldn't run the Windows AI helper: {exc}", setup=True)
    for line in (result.stdout or "").splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                break
    detail = ((result.stderr or "") + (result.stdout or "")).strip()[:300]
    raise WindowsAIError(f"The Windows AI helper gave no report for {option}"
                         + (f": {detail}" if detail else "."))


#: The last readiness report that said the model could be used, so pickers and repeated
#: constructions don't start a process each time. A PC whose state changes later still fails
#: loudly: the request itself reports it.
_ready_report: Optional[dict] = None
_ready_lock = threading.RLock()


def readiness(force: bool = False) -> dict:
    """The helper's ``--check`` report: ``{"protocol", "identity", "state", "kinds", ...}``."""
    global _ready_report
    with _ready_lock:
        if _ready_report is not None and not force:
            return _ready_report
    report = _run_helper("--check", CHECK_TIMEOUT_SECONDS)
    if report.get("identity") and report.get("state") == "Ready":
        with _ready_lock:
            _ready_report = report
    return report


def _raise_unless_usable(report: dict) -> None:
    """Raise the setup error a report implies, if any. NotReady is usable: it can be prepared."""
    if not report.get("identity"):
        raise WindowsAIError(report.get("message") or _NO_IDENTITY_HINT, code="no_identity", setup=True)
    protocol = report.get("protocol")
    if protocol != PROTOCOL_VERSION:
        raise WindowsAIError(
            f"The Windows AI helper speaks protocol {protocol}; this IDT speaks {PROTOCOL_VERSION}. "
            "Reinstall IDT so the two match.", code="protocol", setup=True)
    state = report.get("state")
    if state == "NotSupportedOnCurrentSystem":
        raise WindowsAIError(
            "Windows' image description needs a Copilot+ PC, with an NPU, and a recent version of "
            "Windows 11. This PC doesn't support it.", code="not_supported", setup=True)
    if state == "DisabledByUser":
        raise WindowsAIError(
            "Windows' AI features are turned off on this PC. They can be turned on in Settings, "
            "Privacy & security.", code="disabled_by_user", setup=True)
    if state not in ("Ready", "NotReady"):
        raise WindowsAIError(f"Windows' image description isn't available on this PC ({state}).",
                             code="not_supported", setup=True)


def check_ready(force: bool = False) -> dict:
    """Raise :class:`WindowsAIError` unless a request could succeed; return the report.

    A model that isn't downloaded yet passes: it can be prepared (:func:`prepare`), and the
    helper prepares it on first use anyway.
    """
    if not _on_windows():
        raise WindowsAIError(_NOT_WINDOWS_HINT, setup=True)
    build = _windows_build()
    if build < MIN_WINDOWS_BUILD:
        raise WindowsAIError(_OLD_WINDOWS_HINT.format(build=build), setup=True)
    if _helper_command() is None:
        raise WindowsAIError(_NO_HELPER_HINT, setup=True)
    report = readiness(force=force)
    _raise_unless_usable(report)
    return report


def prepare() -> dict:
    """Make the model ready, downloading it if Windows needs to. Can take minutes the first time.

    Raises :class:`WindowsAIError` when it can't be made ready.
    """
    report = check_ready()
    if report.get("state") == "Ready":
        return report
    report = _run_helper("--prepare", PREPARE_TIMEOUT_SECONDS)
    _raise_unless_usable(report)
    if report.get("state") != "Ready":
        raise WindowsAIError(
            report.get("message") or "Windows couldn't get its image description model ready. "
            "It may still be downloading; try again in a few minutes.",
            code="not_ready", status_code=503)
    readiness(force=True)
    return report


# ---------------------------------------------------------------------------
# The helper process
# ---------------------------------------------------------------------------


class HelperProcess:
    """One ``idt-windows-ai --serve``, started on demand and shared by every request.

    Started lazily, so a PC that never selects this provider starts nothing, and the cost stays
    off a GUI's UI thread at startup. A helper that died is started again for the next request,
    so a crash mid-batch costs one picture, not the rest of the run.

    Two locks. ``_request_lock`` takes requests one at a time (the model handles one at a time
    anyway) and is held while a request waits for its answer. ``_state_lock`` guards which
    process is running and is only ever held briefly, so :meth:`stop` and :meth:`is_running`
    never wait behind a picture: stopping closes the helper, and the request waiting on it
    returns at once, saying it was stopped. A GUI's Stop, and exit, can't hang on a describe.

    Answers are read by a thread into a queue, so a request can time out; a helper that times
    out is stopped, so a late answer can never be taken for the next request's.

    Nothing can be orphaned: the helper exits when its stdin closes, which happens when this
    process stops it or ends, however it ends.
    """

    def __init__(self) -> None:
        self._request_lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._proc: Optional[subprocess.Popen] = None
        self._answers: "queue.Queue[Optional[str]]" = queue.Queue()
        self._next_id = 0
        self._stopped = False   # set by stop(), so a request it cut short can say so

    def is_running(self) -> bool:
        with self._state_lock:
            return self._proc is not None and self._proc.poll() is None

    def _start_locked(self) -> subprocess.Popen:
        """The running helper, started if need be. Call with ``_state_lock`` held."""
        if self._proc is not None and self._proc.poll() is None:
            return self._proc
        self._close_locked()
        command = _helper_command()
        if not command:
            raise WindowsAIError(_NO_HELPER_HINT, setup=True)
        try:
            # stderr goes nowhere: the helper reports everything on stdout, and an unread
            # stderr pipe that filled up would wedge it mid-batch.
            proc = subprocess.Popen(
                command + ["--serve"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace",
                bufsize=1, creationflags=_CREATE_NO_WINDOW,
            )
        except OSError as exc:
            raise WindowsAIError(f"Couldn't start the Windows AI helper: {exc}", setup=True)
        self._proc = proc
        self._answers = queue.Queue()
        threading.Thread(target=self._read_answers, args=(proc, self._answers),
                         name="windows-ai-helper-reader", daemon=True).start()
        return proc

    def ensure_running(self) -> None:
        with self._state_lock:
            self._start_locked()

    @staticmethod
    def _read_answers(proc: subprocess.Popen, answers: "queue.Queue[Optional[str]]") -> None:
        try:
            for line in proc.stdout:  # type: ignore[union-attr]
                answers.put(line)
        except (OSError, ValueError):
            pass  # the pipe closed under us (a stop); the None below says the helper has gone
        finally:
            answers.put(None)  # the helper has gone

    def request(self, kind: str, mime_type: str, image_bytes: bytes,
                timeout: float = DESCRIBE_TIMEOUT_SECONDS) -> str:
        """Describe one picture; return the description or raise :class:`WindowsAIError`."""
        with self._request_lock:
            with self._state_lock:
                self._stopped = False
                proc = self._start_locked()
                answers = self._answers
                self._next_id += 1
                request_id = self._next_id
            line = json.dumps({
                "id": request_id, "kind": kind, "mime": mime_type,
                "image": base64.b64encode(image_bytes).decode("ascii"),
            })
            try:
                proc.stdin.write(line + "\n")  # type: ignore[union-attr]
                proc.stdin.flush()  # type: ignore[union-attr]
            except (OSError, ValueError) as exc:
                raise self._gone(proc, f"The Windows AI helper stopped unexpectedly: {exc}")
            try:
                answer = answers.get(timeout=timeout)
            except queue.Empty:
                self.stop()
                raise WindowsAIError(
                    f"Windows AI timed out: no description after {timeout:.0f} seconds.", timeout=True)
            if answer is None:
                raise self._gone(proc, "The Windows AI helper stopped unexpectedly.")
            return self._read_answer(answer, request_id)

    def _gone(self, proc: subprocess.Popen, message: str) -> WindowsAIError:
        """The error for a helper that went away mid-request: retryable if it died, not if it
        was stopped on purpose (a GUI's Stop, or exit), which a retry would only undo."""
        with self._state_lock:
            if self._proc is proc:
                # Its output has ended, though it may not have quite exited yet: done with it,
                # so the next request starts another rather than write to this one.
                self._close_locked()
            elif self._stopped:
                return WindowsAIError("Windows AI was stopped before it finished the picture.")
        return WindowsAIError(message, status_code=503)

    def _read_answer(self, answer: str, request_id: int) -> str:
        try:
            response = json.loads(answer)
        except json.JSONDecodeError:
            response = None
        if not isinstance(response, dict):
            self.stop()
            raise WindowsAIError(f"The Windows AI helper gave an answer IDT can't read: {answer.strip()[:200]}",
                                 status_code=503)
        if response.get("id") not in (request_id, 0):
            # Can't happen with one request at a time and a helper stopped on timeout; if it
            # ever does, the stream is out of step, so start again.
            self.stop()
            raise WindowsAIError("The Windows AI helper answered a different request.", status_code=503)
        if response.get("ok"):
            text = str(response.get("text") or "").strip()
            if not text:
                # Never stored as a description; another attempt usually gives one.
                raise WindowsAIError("Windows AI returned an empty description.", status_code=503)
            return text
        raise error_for_code(str(response.get("code") or ""),
                             str(response.get("message") or "Windows AI couldn't describe the picture."))

    def _close_locked(self) -> None:
        proc, self._proc = self._proc, None
        if proc is None:
            return
        try:
            if proc.stdin:
                proc.stdin.close()  # the helper exits when its input ends
        except OSError:
            pass  # already closed or broken: the wait and kill below end it either way
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

    def stop(self) -> None:
        """Stop the helper, at once, even while a request waits on it: that request then
        raises, saying it was stopped. Safe to call repeatedly and from any thread."""
        with self._state_lock:
            if self._proc is not None:
                self._stopped = True
            self._close_locked()


#: The process-wide helper. One is right: requests are handled one at a time anyway, so a
#: second would add memory without adding throughput.
_helper = HelperProcess()


def helper() -> HelperProcess:
    return _helper


def shutdown_helper() -> None:
    """Stop the shared helper. Registered at exit; also useful in tests."""
    _helper.stop()


atexit.register(shutdown_helper)


# ---------------------------------------------------------------------------
# Image description
# ---------------------------------------------------------------------------


def normalise_kind(model: Optional[str]) -> str:
    """The description kind a model name means, or ValueError naming the kinds."""
    kind = (model or DEFAULT_MODEL).strip().lower()
    if kind not in WINDOWS_AI_MODELS:
        raise ValueError(f"Windows AI has no model {model!r}. Its models are the description kinds: "
                         + ", ".join(WINDOWS_AI_MODELS) + ".")
    return kind


#: The most IDT sends the helper, which takes up to 20 MB; base64 adds a third on the way.
#: Larger pictures are scaled down first: the model sees at most 4096 pixels on a side anyway.
MAX_IMAGE_BYTES = 4_000_000
FIT_LONG_EDGE = 4096

#: Sizes, as the longer side in pixels, to try a picture again at when Windows' model fails on
#: it with InternalError. The failure belongs to a picture at one size, not to the picture: on a
#: Copilot+ PC (10/6/2026), photos that failed at full size every time were described at 2048,
#: 1024 or 512, a different one for each photo, and one that failed at 1024 was described at
#: 2048. Retrying at the same size only failed again.
RETRY_LONG_EDGES = (2048, 1024, 512)


def _as_supported_image(image_bytes: bytes, mime_type: str):
    """The picture in a type and size the helper accepts: as it is, or converted to JPEG,
    scaled down if it is over :data:`MAX_IMAGE_BYTES`."""
    from idt_core.converter import fit_image

    image_bytes, mime_type = fit_image(image_bytes, mime_type, MAX_IMAGE_BYTES, FIT_LONG_EDGE)
    if mime_type in SUPPORTED_IMAGE_MIMES:
        return image_bytes, mime_type
    from PIL import Image

    img = Image.open(io.BytesIO(image_bytes))
    if img.mode != "RGB":
        img = img.convert("RGB")
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=90)
    return out.getvalue(), "image/jpeg"


class WindowsAIProvider(BaseProvider):
    """One image, one description, on this PC's NPU. The prompt is not used: see module docs."""

    def __init__(self, model: str = DEFAULT_MODEL, check: bool = True):
        self._model = normalise_kind(model)
        if check:
            check_ready()

    @property
    def provider_name(self) -> str:
        return "windows-ai"

    @property
    def model_name(self) -> str:
        return self._model

    def describe(self, image_bytes: bytes, mime_type: str, prompt: str) -> DescriptionResult:
        image_bytes, mime_type = _as_supported_image(image_bytes, mime_type)
        try:
            text = _helper.request(self._model, mime_type, image_bytes)
        except WindowsAIError as exc:
            if exc.code != "internal_error":
                raise
            text = self._describe_at_other_sizes(image_bytes, exc)
        return DescriptionResult(text=text, model=self._model, provider="windows-ai")

    def _describe_at_other_sizes(self, image_bytes: bytes, first: WindowsAIError) -> str:
        """Try a picture Windows failed on again at each of :data:`RETRY_LONG_EDGES` smaller
        than it. If none works, it is reported as a failure that isn't retried and isn't a
        refusal: rare for one picture (none of 8 measured), but every picture failing so is a
        broken helper, which a batch should stop for after ten in a row, not take for Windows
        declining pictures. A picture with no smaller size to try keeps its first error, which
        a caller may retry as it is."""
        from PIL import Image

        try:
            img = Image.open(io.BytesIO(image_bytes))
            img.load()
        except Exception:                                   # noqa: BLE001
            raise first   # not a picture PIL reads: nothing to resize
        # The copy is saved without EXIF, so turn a phone photo upright first, or the copy
        # would reach Windows on its side.
        from PIL import ImageOps

        img = ImageOps.exif_transpose(img)
        if img.mode != "RGB":
            img = img.convert("RGB")
        edges = [edge for edge in RETRY_LONG_EDGES if edge < max(img.size)]
        if not edges:
            raise first
        for edge in edges:   # largest first, so each resize shrinks the last one in place
            img.thumbnail((edge, edge), Image.Resampling.LANCZOS)
            out = io.BytesIO()
            img.save(out, format="JPEG", quality=90)
            try:
                return _helper.request(self._model, "image/jpeg", out.getvalue())
            except WindowsAIError as exc:
                if exc.code != "internal_error":
                    raise
        raise WindowsAIError(f"{str(first).rstrip('.')}. Windows couldn't describe it at a smaller "
                             "size either.", code="internal_error")
