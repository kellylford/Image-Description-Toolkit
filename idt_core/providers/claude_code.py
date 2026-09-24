"""
Claude Code provider — image descriptions and chat through the ``claude`` CLI,
billed to the user's Claude subscription (Pro/Max) instead of an API key.

Every request is one ``claude -p`` run: a fresh, unsaved session, so images
never pile up in a context window between requests.

Overhead. A default ``claude -p`` carries Claude Code's full system prompt and
tool definitions, and opening an image with the Read tool costs extra turns —
about 17,700 input tokens and 3 turns per image when measured. Instead the
content goes in as Messages-API content blocks on stdin (``--input-format
stream-json``), with a short ``--system-prompt`` and no tools: one turn, and an
image costs about what it costs through the API (1,876 input tokens for a
12-megapixel photo, measured).

Billing guard. The point is "never touch API credits", so nothing runs unless
``claude auth status`` reports a claude.ai login, and every variable that would
reroute the child onto an API key or another endpoint is stripped from its
environment (``ANTHROPIC_API_KEY``, ``ANTHROPIC_AUTH_TOKEN``,
``ANTHROPIC_BASE_URL``). ``--bare`` is deliberately not used: bare mode accepts
*only* API-key auth.

This runs as whoever is signed in to Claude Code on the machine. It is for a
person using their own subscription, not for serving other users.
"""
from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Iterator, List, Optional, Sequence, Tuple

from .base import BaseProvider, DescriptionResult

__all__ = [
    "CLAUDE_CODE_MODELS",
    "DEFAULT_MODEL",
    "ClaudeCodeError",
    "ClaudeCodeProvider",
    "auth_status",
    "check_subscription",
    "find_claude",
    "is_available",
    "run_claude",
    "usage_tokens",
]

#: Aliases the CLI resolves to the current model of each tier, so the list
#: never goes stale when a new Haiku/Sonnet/Opus ships.
CLAUDE_CODE_MODELS = ["haiku", "sonnet", "opus"]
DEFAULT_MODEL = "haiku"

#: Picker metadata, read by ``catalog`` like the other providers' tables.
#: Limits are deliberately the conservative ones Claude Code applies by
#: default (200K context, 32K output), not the larger figures some of these
#: models reach through the API.
CLAUDE_CODE_MODEL_METADATA: dict = {
    "haiku": {
        "name": "Haiku (subscription)",
        "description": "Fastest; uses the least of your plan's usage",
        "context_window": 200000, "max_output": 32000,
        "supports_vision": True, "cost": "$", "recommended": True,
    },
    "sonnet": {
        "name": "Sonnet (subscription)",
        "description": "More detail and better at reading text in images",
        "context_window": 200000, "max_output": 32000,
        "supports_vision": True, "cost": "$$", "recommended": True,
    },
    "opus": {
        "name": "Opus (subscription)",
        "description": "Most capable; uses your plan's usage fastest",
        "context_window": 200000, "max_output": 32000,
        "supports_vision": True, "cost": "$$$", "recommended": False,
    },
}

#: Removed from the child's environment so it can only use the subscription
#: login. CLAUDECODE is set inside a Claude Code session and would mark the
#: child as nested.
_STRIPPED_ENV = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_BASE_URL",
    "CLAUDECODE",
)

#: Replaces Claude Code's default system prompt, which is written for coding
#: work and is most of the per-request overhead.
DESCRIBE_SYSTEM_PROMPT = (
    "You describe images. Follow the user's instructions about the image and "
    "reply with only the description itself, no preamble."
)
CHAT_SYSTEM_PROMPT = "You are a helpful assistant."

DESCRIBE_TIMEOUT_SECONDS = 300

#: Diagnostic hook: when set, each run's result record (tokens, turns,
#: API-equivalent cost) is appended to this JSONL file. Used to measure how
#: much of a subscription allowance a batch takes.
STATS_ENV = "IDT_CLAUDE_CODE_STATS"

_INSTALL_HINT = (
    "Claude Code is not installed or not on PATH. "
    "Install it from https://claude.com/claude-code, then run: claude auth login"
)


class ClaudeCodeError(RuntimeError):
    """Claude Code is missing, signed out, on the wrong account type, or a run failed."""


# ---------------------------------------------------------------------------
# Locating and checking the CLI
# ---------------------------------------------------------------------------


def find_claude() -> Optional[str]:
    """Path to the ``claude`` executable, or None."""
    found = shutil.which("claude")
    if found:
        return found
    for candidate in (
        Path.home() / ".local" / "bin" / "claude.exe",
        Path.home() / ".local" / "bin" / "claude",
    ):
        if candidate.is_file():
            return str(candidate)
    return None


def is_available() -> bool:
    """True if the CLI is installed. Says nothing about sign-in; cheap."""
    return find_claude() is not None


def _child_env(extra: Optional[dict] = None) -> dict:
    env = dict(os.environ)
    for name in _STRIPPED_ENV:
        env.pop(name, None)
    if extra:
        env.update(extra)
    return env


def _no_window() -> int:
    """Keep a console window from flashing up when a GUI app runs the CLI."""
    return getattr(subprocess, "CREATE_NO_WINDOW", 0)


def auth_status(claude: Optional[str] = None) -> dict:
    """``claude auth status`` as a dict. Raises ClaudeCodeError if unreadable."""
    claude = claude or find_claude()
    if not claude:
        raise ClaudeCodeError(_INSTALL_HINT)
    try:
        result = subprocess.run(
            [claude, "auth", "status"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env=_child_env(), timeout=60, creationflags=_no_window(),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ClaudeCodeError(f"Could not run 'claude auth status': {exc}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        raise ClaudeCodeError(
            f"Could not read 'claude auth status': {(result.stdout or result.stderr).strip()}"
        )


#: Set once a subscription login has been confirmed in this process, so chat
#: does not spend a second on ``claude auth status`` before every turn. A login
#: that lapses later still fails loudly: the run itself reports the error.
_subscription_confirmed = False


def check_subscription(claude: Optional[str] = None, force: bool = False) -> None:
    """Raise ClaudeCodeError unless Claude Code is signed in to claude.ai.

    Any other auth method (an API key, a cloud provider) would bill something
    other than the subscription, which is exactly what this provider exists
    to avoid, so it is refused rather than warned about.
    """
    global _subscription_confirmed
    if _subscription_confirmed and not force:
        return
    status = auth_status(claude)
    if not status.get("loggedIn"):
        raise ClaudeCodeError("Claude Code is not signed in. Run: claude auth login")
    method = status.get("authMethod")
    if method != "claude.ai":
        raise ClaudeCodeError(
            f"Claude Code is signed in with '{method}', not a claude.ai "
            "subscription, so it would bill an API account. Run: claude auth login"
        )
    _subscription_confirmed = True


# ---------------------------------------------------------------------------
# Running one request
# ---------------------------------------------------------------------------


def build_command(claude: str, model: str, system_prompt_file: str,
                  partial: bool = False) -> List[str]:
    """The ``claude -p`` command line.

    The system prompt travels in a file, never as an argument: an npm install
    on Windows is ``claude.cmd``, whose arguments pass through cmd.exe, where
    a chat system prompt containing ``&``, ``%`` or a quote would be split or
    expanded -- and a long one would hit the 32K command-line limit.

    ``disableAllHooks`` and ``--setting-sources project,local`` keep the
    user's own Claude Code setup out of every request: a Stop hook in
    ~/.claude/settings.json (read-aloud, notifications) would otherwise fire
    once per image. The working directory is an empty scratch folder, so the
    project and local sources are empty too.
    """
    cmd = [
        claude, "-p",
        "--model", model,
        "--system-prompt-file", system_prompt_file,
        "--settings", '{"disableAllHooks": true}',
        "--setting-sources", "project,local",
        "--tools", "",
        "--strict-mcp-config",
        "--disable-slash-commands",
        "--no-session-persistence",
        "--input-format", "stream-json",
        "--output-format", "stream-json",
        "--verbose",  # the CLI requires it for stream-json output
    ]
    if partial:
        cmd.append("--include-partial-messages")
    return cmd


def _record_stats(data: dict) -> None:
    path = os.environ.get(STATS_ENV)
    if not path:
        return
    keep = {k: data.get(k) for k in (
        "num_turns", "duration_ms", "duration_api_ms", "total_cost_usd", "usage", "is_error",
    )}
    try:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(keep) + "\n")
    except OSError:
        pass


def result_error(data: dict) -> Optional[str]:
    """The failure message from a ``result`` record, or None on success."""
    text = (data.get("result") or "").strip()
    if not data.get("is_error") and text:
        return None
    message = text or data.get("subtype") or "no response"
    lowered = message.lower()
    if "authenticate" in lowered or "oauth" in lowered or "log in" in lowered:
        message += " — run: claude auth login"
    return f"Claude Code: {message}"


def usage_tokens(data: dict) -> Tuple[int, int]:
    """(input, output) tokens from a ``result`` record; cached input counts."""
    usage = data.get("usage") or {}
    input_tokens = (
        (usage.get("input_tokens") or 0)
        + (usage.get("cache_read_input_tokens") or 0)
        + (usage.get("cache_creation_input_tokens") or 0)
    )
    return input_tokens, usage.get("output_tokens") or 0


def run_claude(
    content: Sequence[dict],
    model: str,
    system_prompt: str,
    *,
    partial: bool = False,
    timeout: Optional[float] = None,
    max_output_tokens: Optional[int] = None,
    claude: Optional[str] = None,
) -> Iterator[Tuple[str, object]]:
    """Run one ``claude -p`` request and yield what comes back.

    ``content`` is a list of Messages-API content blocks (text, image,
    document) forming one user turn. Yields ``("delta", str)`` for each piece
    of answer text when ``partial`` is set, then exactly one
    ``("result", dict)``; raises ClaudeCodeError when no result arrives.

    A generator so chat can stream and cancel: closing it kills the process in
    the ``finally``, the same contract as the SDK-backed chat providers.
    """
    claude = claude or find_claude()
    if not claude:
        raise ClaudeCodeError(_INSTALL_HINT)

    message = {"type": "user", "message": {"role": "user", "content": list(content)}}
    payload = json.dumps(message) + "\n"
    extra_env = {}
    if max_output_tokens:
        extra_env["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] = str(int(max_output_tokens))

    # An empty scratch directory as the working directory, so Claude Code does
    # not pick up whatever project (and CLAUDE.md) the app happens to run in.
    scratch = tempfile.mkdtemp(prefix="idt-cc-")
    prompt_file = Path(scratch) / "system_prompt.txt"
    try:
        prompt_file.write_text(system_prompt, encoding="utf-8")
        proc = subprocess.Popen(
            build_command(claude, model, str(prompt_file), partial),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace",
            cwd=scratch, env=_child_env(extra_env), creationflags=_no_window(),
        )
    except OSError as exc:
        shutil.rmtree(scratch, ignore_errors=True)
        raise ClaudeCodeError(f"Could not start Claude Code: {exc}")

    stderr_lines: List[str] = []
    timed_out = threading.Event()

    def feed_stdin():
        # Separate thread: a large image payload must not deadlock against
        # the child filling its stdout pipe before it has read all of stdin.
        try:
            proc.stdin.write(payload)
            proc.stdin.close()
        except (OSError, ValueError):
            pass

    def drain_stderr():
        for line in proc.stderr:
            stderr_lines.append(line)

    def on_timeout():
        timed_out.set()
        proc.kill()

    threads = [threading.Thread(target=feed_stdin, daemon=True),
               threading.Thread(target=drain_stderr, daemon=True)]
    for t in threads:
        t.start()
    timer = threading.Timer(timeout, on_timeout) if timeout else None
    if timer:
        timer.daemon = True
        timer.start()

    result = None
    try:
        for line in proc.stdout:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            kind = event.get("type")
            if kind == "stream_event" and partial:
                inner = event.get("event") or {}
                if inner.get("type") == "content_block_delta":
                    delta = inner.get("delta") or {}
                    if delta.get("type") == "text_delta" and delta.get("text"):
                        yield ("delta", delta["text"])
            elif kind == "result":
                result = event
        proc.wait()
    finally:
        if timer:
            timer.cancel()
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        shutil.rmtree(scratch, ignore_errors=True)

    if timed_out.is_set():
        raise ClaudeCodeError(f"Claude Code did not finish within {int(timeout)}s")
    if result is None:
        detail = "".join(stderr_lines).strip()[:500] or f"exit code {proc.returncode}"
        raise ClaudeCodeError(f"Claude Code returned no result: {detail}")
    _record_stats(result)
    yield ("result", result)


# ---------------------------------------------------------------------------
# Image description
# ---------------------------------------------------------------------------


#: The API refuses images over 5 MB once base64-encoded, and base64 grows the
#: payload by a third. The first prototype never hit this because Claude
#: Code's Read tool resized for it; sending the bytes inline means doing it here.
MAX_IMAGE_BYTES = 3_700_000

#: Long edge for a downscaled image. The API resizes anything larger to about
#: this before the model sees it, so nothing visible is lost.
FIT_LONG_EDGE = 1568


def fit_image(image_bytes: bytes, mime_type: str) -> Tuple[bytes, str]:
    """``(bytes, mime)`` small enough to send; unchanged when it already is.

    A 24 or 48 MP phone JPEG, or a large PNG scan, is over the limit and
    would otherwise fail on every attempt.
    """
    if len(image_bytes) <= MAX_IMAGE_BYTES:
        return image_bytes, mime_type
    import io

    from PIL import Image

    img = Image.open(io.BytesIO(image_bytes))
    if img.mode != "RGB":
        img = img.convert("RGB")
    img.thumbnail((FIT_LONG_EDGE, FIT_LONG_EDGE), Image.Resampling.LANCZOS)
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=85)
    return out.getvalue(), "image/jpeg"


def image_block(image_bytes: bytes, mime_type: str) -> dict:
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": mime_type,
            "data": base64.standard_b64encode(image_bytes).decode("ascii"),
        },
    }


class ClaudeCodeProvider(BaseProvider):
    """One image, one prompt, one description, through the subscription."""

    def __init__(self, model: str = DEFAULT_MODEL, check_auth: bool = True):
        self._model = model or DEFAULT_MODEL
        self._claude = find_claude()
        if not self._claude:
            raise ClaudeCodeError(_INSTALL_HINT)
        if check_auth:
            check_subscription(self._claude)

    @property
    def provider_name(self) -> str:
        return "claude-code"

    @property
    def model_name(self) -> str:
        return self._model

    def describe(self, image_bytes: bytes, mime_type: str, prompt: str) -> DescriptionResult:
        image_bytes, mime_type = fit_image(image_bytes, mime_type)
        content = [image_block(image_bytes, mime_type), {"type": "text", "text": prompt}]
        data = None
        for kind, value in run_claude(
            content, self._model, DESCRIBE_SYSTEM_PROMPT,
            timeout=DESCRIBE_TIMEOUT_SECONDS, claude=self._claude,
        ):
            if kind == "result":
                data = value
        error = result_error(data)
        if error:
            raise ClaudeCodeError(error)
        input_tokens, output_tokens = usage_tokens(data)
        return DescriptionResult(
            text=data["result"].strip(),
            model=self._model,
            provider="claude-code",
            input_tokens=input_tokens or None,
            output_tokens=output_tokens or None,
        )
