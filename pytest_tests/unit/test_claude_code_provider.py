"""The Claude Code provider: Claude on the user's subscription via the `claude` CLI.

Nothing here runs the real CLI or spends any of a subscription. The subprocess
tests swap the command for a small Python script that speaks the CLI's
stream-json protocol, so the real Popen / pipe / kill code is exercised.
"""
import json
import os
import sys
import textwrap
import time
from types import SimpleNamespace

import pytest

from idt_core.providers import claude_code
from idt_core.providers.claude_code import (
    ClaudeCodeError,
    ClaudeCodeProvider,
    build_command,
    result_error,
    run_claude,
    usage_tokens,
)


@pytest.fixture(autouse=True)
def _fresh_subscription_cache(monkeypatch):
    monkeypatch.setattr(claude_code, "_subscription_confirmed", False)


# ---------------------------------------------------------------------------
# Billing guard
# ---------------------------------------------------------------------------

def test_child_environment_cannot_reach_an_api_account(monkeypatch):
    """Any of these would move billing off the subscription."""
    for name in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL", "CLAUDECODE"):
        monkeypatch.setenv(name, "set-by-test")
    env = claude_code._child_env()
    for name in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL", "CLAUDECODE"):
        assert name not in env
    assert "PATH" in env or "Path" in env


def test_command_never_uses_bare_mode():
    """--bare accepts only API-key auth, which is the one thing to avoid."""
    cmd = build_command("claude", "haiku", "prompt.txt")
    assert "--bare" not in cmd
    # Overhead controls: no tools, own system prompt, no saved session.
    assert cmd[cmd.index("--tools") + 1] == ""
    # From a file, never argv: claude.cmd would hand argv to cmd.exe.
    assert cmd[cmd.index("--system-prompt-file") + 1] == "prompt.txt"
    assert "--system-prompt" not in cmd
    # The user's own hooks (read-aloud, notifications) must not fire per image.
    assert json.loads(cmd[cmd.index("--settings") + 1]) == {"disableAllHooks": True}
    assert cmd[cmd.index("--setting-sources") + 1] == "project,local"
    assert "--no-session-persistence" in cmd
    assert "--include-partial-messages" not in cmd
    assert "--include-partial-messages" in build_command("claude", "haiku", "s", partial=True)


@pytest.mark.parametrize("status, expected", [
    ({"loggedIn": False, "authMethod": "none"}, "not signed in"),
    ({"loggedIn": True, "authMethod": "api_key"}, "would bill an API account"),
    ({"loggedIn": True, "authMethod": "console"}, "would bill an API account"),
])
def test_anything_but_a_subscription_login_is_refused(monkeypatch, status, expected):
    monkeypatch.setattr(claude_code, "auth_status", lambda claude=None: status)
    with pytest.raises(ClaudeCodeError, match=expected):
        claude_code.check_subscription("claude")


def test_subscription_check_runs_once_per_process(monkeypatch):
    calls = []

    def status(claude=None):
        calls.append(1)
        return {"loggedIn": True, "authMethod": "claude.ai"}

    monkeypatch.setattr(claude_code, "auth_status", status)
    claude_code.check_subscription("claude")
    claude_code.check_subscription("claude")
    assert len(calls) == 1
    claude_code.check_subscription("claude", force=True)
    assert len(calls) == 2


def test_missing_cli_names_the_fix(monkeypatch):
    monkeypatch.setattr(claude_code, "find_claude", lambda: None)
    with pytest.raises(ClaudeCodeError, match="claude.com/claude-code"):
        ClaudeCodeProvider()


# ---------------------------------------------------------------------------
# Result records
# ---------------------------------------------------------------------------

def test_result_error_and_usage():
    ok = {"result": "A desk.", "is_error": False,
          "usage": {"input_tokens": 18, "cache_read_input_tokens": 1000,
                    "cache_creation_input_tokens": 858, "output_tokens": 300}}
    assert result_error(ok) is None
    assert usage_tokens(ok) == (1876, 300)

    auth = {"result": "Failed to authenticate: OAuth session expired", "is_error": True}
    assert "claude auth login" in result_error(auth)
    assert result_error({"result": "", "is_error": False, "subtype": "success"})


# ---------------------------------------------------------------------------
# The subprocess, through a fake CLI
# ---------------------------------------------------------------------------

FAKE_CLI = textwrap.dedent('''
    import json, sys, time
    msg = json.loads(sys.stdin.readline())
    content = msg["message"]["content"]
    mode = content[-1]["text"]
    # Echo what arrived so tests can see the payload survived the pipe.
    kinds = ",".join(b["type"] for b in content)
    if mode == "hang":
        time.sleep(60)
    if mode == "crash":
        sys.stderr.write("boom from fake cli\\n")
        sys.exit(3)
    def out(obj):
        sys.stdout.write(json.dumps(obj) + "\\n"); sys.stdout.flush()
    out({"type": "system", "subtype": "init"})
    for piece in ["Hello", " there"]:
        out({"type": "stream_event", "event": {"type": "content_block_delta",
             "delta": {"type": "text_delta", "text": piece}}})
        if mode == "slow":
            time.sleep(30)
    out({"type": "result", "subtype": "success", "is_error": False,
         "result": "Hello there [" + kinds + "]",
         "usage": {"input_tokens": 7, "output_tokens": 2}})
''')


@pytest.fixture
def fake_cli(tmp_path, monkeypatch):
    script = tmp_path / "fake_claude.py"
    script.write_text(FAKE_CLI, encoding="utf-8")
    monkeypatch.setattr(
        claude_code, "build_command",
        lambda claude, model, system_prompt, partial=False: [sys.executable, str(script)],
    )
    return script


def _text(mode):
    return [{"type": "text", "text": mode}]


def test_system_prompt_reaches_the_cli_through_a_file(tmp_path, monkeypatch):
    """Characters cmd.exe would mangle arrive intact, because they never touch argv."""
    script = tmp_path / "echo_cli.py"
    script.write_text(textwrap.dedent('''
        import json, sys
        sys.stdin.readline()
        prompt = open(sys.argv[1], encoding="utf-8").read()
        print(json.dumps({"type": "result", "is_error": False, "result": prompt}))
    '''), encoding="utf-8")
    monkeypatch.setattr(
        claude_code, "build_command",
        lambda claude, model, prompt_file, partial=False: [sys.executable, str(script), prompt_file],
    )
    tricky = 'Say "hi" & echo %PATH% | more'
    events = list(run_claude(_text("ok"), "haiku", tricky, claude="x"))
    assert events[-1][1]["result"] == tricky


def test_oversized_images_are_shrunk_below_the_api_limit():
    import io

    from PIL import Image

    noisy = Image.frombytes("RGB", (3000, 2400), os.urandom(3000 * 2400 * 3))
    buf = io.BytesIO()
    noisy.save(buf, format="PNG")
    assert len(buf.getvalue()) > claude_code.MAX_IMAGE_BYTES
    data, mime = claude_code.fit_image(buf.getvalue(), "image/png")
    assert mime == "image/jpeg" and len(data) <= claude_code.MAX_IMAGE_BYTES
    assert max(Image.open(io.BytesIO(data)).size) == claude_code.FIT_LONG_EDGE
    small = b"\xff\xd8small"
    assert claude_code.fit_image(small, "image/jpeg") == (small, "image/jpeg")


def test_run_streams_deltas_then_one_result(fake_cli):
    events = list(run_claude(_text("ok"), "haiku", "sys", partial=True, claude="x"))
    deltas = [v for k, v in events if k == "delta"]
    results = [v for k, v in events if k == "result"]
    assert deltas == ["Hello", " there"]
    assert len(results) == 1 and results[0]["result"].startswith("Hello there")


def test_a_large_image_payload_crosses_the_pipe(fake_cli):
    """Several MB on stdin must not deadlock against the child's stdout."""
    big = claude_code.image_block(os.urandom(3 * 1024 * 1024), "image/jpeg")
    events = list(run_claude([big] + _text("ok"), "haiku", "sys", claude="x"))
    assert events[-1][1]["result"].endswith("[image,text]")


def test_no_result_reports_stderr(fake_cli):
    with pytest.raises(ClaudeCodeError, match="boom from fake cli"):
        list(run_claude(_text("crash"), "haiku", "sys", claude="x"))


def test_timeout_kills_the_process(fake_cli):
    start = time.monotonic()
    with pytest.raises(ClaudeCodeError, match="did not finish within"):
        list(run_claude(_text("hang"), "haiku", "sys", timeout=2, claude="x"))
    assert time.monotonic() - start < 20


def test_closing_the_generator_stops_the_process(fake_cli):
    """Stop in a chat window is gen.close(); it must not wait out the reply."""
    gen = run_claude(_text("slow"), "haiku", "sys", partial=True, claude="x")
    start = time.monotonic()
    assert next(gen) == ("delta", "Hello")
    gen.close()
    assert time.monotonic() - start < 20


# ---------------------------------------------------------------------------
# describe()
# ---------------------------------------------------------------------------

def _stub_run(monkeypatch, result, seen=None):
    def fake(content, model, system_prompt, **kwargs):
        if seen is not None:
            seen.update(content=content, model=model, system=system_prompt, **kwargs)
        yield ("result", result)

    monkeypatch.setattr(claude_code, "find_claude", lambda: "claude")
    monkeypatch.setattr(claude_code, "check_subscription", lambda *a, **k: None)
    monkeypatch.setattr(claude_code, "run_claude", fake)


def test_describe_sends_the_image_inline_and_returns_tokens(monkeypatch):
    seen = {}
    _stub_run(monkeypatch, {"result": " A red bike. ", "is_error": False,
                            "usage": {"input_tokens": 1876, "output_tokens": 250}}, seen)
    result = ClaudeCodeProvider(model="sonnet").describe(b"\xff\xd8jpeg", "image/png", "Describe")
    assert result.text == "A red bike."
    assert (result.input_tokens, result.output_tokens) == (1876, 250)
    assert result.provider == "claude-code" and seen["model"] == "sonnet"
    image, text = seen["content"]
    assert image["type"] == "image" and image["source"]["media_type"] == "image/png"
    assert text == {"type": "text", "text": "Describe"}
    assert seen["timeout"] == claude_code.DESCRIBE_TIMEOUT_SECONDS


def test_describe_raises_on_an_error_result(monkeypatch):
    _stub_run(monkeypatch, {"result": "You've hit your limit", "is_error": True})
    with pytest.raises(ClaudeCodeError, match="hit your limit"):
        ClaudeCodeProvider().describe(b"x", "image/jpeg", "Describe")


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

from idt_core.chat.claude_code import (  # noqa: E402
    TRANSCRIPT_NOTE, ClaudeCodeChatProvider, format_for_claude_code,
)
from idt_core.chat.messages import Attachment, ChatMessage  # noqa: E402
from idt_core.providers.base import ChatDelta, ChatRequest, ChatUsage  # noqa: E402


def test_a_single_turn_is_sent_as_is():
    system, blocks = format_for_claude_code([ChatMessage(role="user", content="Hi")], "Be terse.")
    assert system == "Be terse."
    assert blocks == [{"type": "text", "text": "Hi"}]


def test_history_travels_as_a_labelled_transcript(tmp_path):
    photo = tmp_path / "p.png"
    photo.write_bytes(b"\x89PNG fake")
    messages = [
        ChatMessage(role="system", content="ignored here"),
        ChatMessage(role="user", content="What is this?",
                    attachments=[Attachment(path=str(photo), media_type="image/png")]),
        ChatMessage(role="assistant", content="A cat."),
        ChatMessage(role="user", content="What colour?"),
    ]
    system, blocks = format_for_claude_code(messages)
    assert TRANSCRIPT_NOTE in system
    kinds = [b["type"] for b in blocks]
    assert kinds == ["image", "text", "text", "text"]
    assert blocks[1]["text"] == "User:\nWhat is this?"
    assert blocks[2]["text"] == "Assistant:\nA cat."
    assert blocks[3]["text"] == "User:\nWhat colour?"


def test_chat_yields_deltas_then_usage(monkeypatch):
    def fake(content, model, system_prompt, **kwargs):
        assert kwargs["partial"] is True
        yield ("delta", "Tea")
        yield ("delta", "l.")
        yield ("result", {"result": "Teal.", "is_error": False, "stop_reason": "end_turn",
                          "usage": {"input_tokens": 272, "output_tokens": 52}})

    monkeypatch.setattr("idt_core.chat.claude_code.find_claude", lambda: "claude")
    monkeypatch.setattr("idt_core.chat.claude_code.check_subscription", lambda *a, **k: None)
    monkeypatch.setattr("idt_core.chat.claude_code.run_claude", fake)
    items = list(ClaudeCodeChatProvider("haiku").chat(
        ChatRequest(messages=[ChatMessage(role="user", content="Colour?")], model="haiku")))
    assert [i.text for i in items if isinstance(i, ChatDelta)] == ["Tea", "l."]
    assert items[-1] == ChatUsage(input_tokens=272, output_tokens=52, stop_reason="end_turn")


def test_chat_error_result_raises(monkeypatch):
    def fake(*a, **k):
        yield ("result", {"result": "Failed to authenticate", "is_error": True})

    monkeypatch.setattr("idt_core.chat.claude_code.find_claude", lambda: "claude")
    monkeypatch.setattr("idt_core.chat.claude_code.check_subscription", lambda *a, **k: None)
    monkeypatch.setattr("idt_core.chat.claude_code.run_claude", fake)
    with pytest.raises(ClaudeCodeError, match="claude auth login"):
        list(ClaudeCodeChatProvider().chat(
            ChatRequest(messages=[ChatMessage(role="user", content="x")], model="haiku")))


@pytest.mark.parametrize("name", ["claude-code", "Claude Code", "claude_code", "CLAUDECODE"])
def test_chat_factory_resolves_claude_code(name):
    from idt_core.chat.providers import create_chat_provider

    provider = create_chat_provider(name, "haiku", api_key="ignored")
    assert isinstance(provider, ClaudeCodeChatProvider)
    assert provider.provider_name == "claude-code"


# ---------------------------------------------------------------------------
# Registry, catalog, keys, token budget
# ---------------------------------------------------------------------------

def test_registered_as_a_keyless_streaming_provider():
    from idt_core.keys import requires_api_key, resolve_api_key
    from idt_core.providers.registry import capabilities_for, display_name

    caps = capabilities_for("claude-code")
    assert caps.provider == "claude-code"
    assert caps.streaming and caps.system_prompt and caps.supports_images
    assert not caps.requires_api_key
    assert not requires_api_key("claude-code")
    assert resolve_api_key("claude-code") is None
    assert display_name("claude-code") == "Claude Code"


def test_catalog_lists_the_tier_aliases_with_limits():
    from idt_core.chat.tokens import context_window_for
    from idt_core.providers import catalog

    ids = [e.id for e in catalog.cached_models("claude-code")]
    assert ids == ["haiku", "sonnet", "opus"]
    entry = catalog.model_entry("claude-code", "haiku")
    assert entry.context_window == 200000 and entry.supports_vision
    assert context_window_for("claude-code", "sonnet") == 200000


# ---------------------------------------------------------------------------
# CLI wiring
# ---------------------------------------------------------------------------

def test_cli_chat_default_model_is_not_an_ollama_model():
    from cli.main import _chat_default_model

    assert _chat_default_model("claude-code") == "haiku"


def test_cli_make_provider_exits_cleanly_when_signed_out(monkeypatch, capsys):
    from cli.main import _make_provider

    monkeypatch.setattr(claude_code, "find_claude", lambda: "claude")
    monkeypatch.setattr(claude_code, "auth_status",
                        lambda claude=None: {"loggedIn": False, "authMethod": "none"})
    with pytest.raises(SystemExit):
        _make_provider("claude-code", "haiku", "http://localhost:11434")
    assert "claude auth login" in capsys.readouterr().err


def test_idt_models_reports_claude_code_status(monkeypatch, capsys):
    from cli.main import cmd_models

    monkeypatch.setattr(claude_code, "find_claude", lambda: "claude")
    monkeypatch.setattr(claude_code, "auth_status",
                        lambda claude=None: {"loggedIn": True, "authMethod": "claude.ai"})
    args = SimpleNamespace(provider="claude-code", json_out=True, refresh=False,
                           all=False, ollama_host="http://localhost:11434")
    cmd_models(args)
    out = json.loads(capsys.readouterr().out)
    assert out == {"claude-code": {"status": "ok", "models": ["haiku", "sonnet", "opus"]}}
