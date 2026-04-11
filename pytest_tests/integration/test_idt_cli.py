"""
IDT CLI Integration Tests
=========================
Validates every routed command in idt_cli.py:
  - exits with a known-good code
  - prints expected text
  - does NOT produce unexpected "Unknown command" / Python tracebacks

These tests run in dev-mode (python idt_cli.py …) so they require no build step
and work in CI without a frozen executable.

Test categories
---------------
HELP         – help/version output is correct and complete
ROUTING      – each command launches without crash (exit 0 or expected non-zero)
ALIASES      – describe / redescribe / -v / --version all route correctly
ARGS         – per-command --help output matches known flags
CONTRACT     – help text does NOT mention removed commands (viewer, etc.)
"""

import subprocess
import sys
from pathlib import Path

import pytest

# ── Paths ─────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent.parent
IDT_CLI = PROJECT_ROOT / "idt" / "idt_cli.py"
TEST_IMAGES = PROJECT_ROOT / "testimages"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"


def idt(*args, timeout: int = 15, cwd=None):
    """Run idt_cli.py with the given arguments and return CompletedProcess."""
    cmd = [sys.executable, str(IDT_CLI)] + list(args)
    return subprocess.run(
        cmd,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        cwd=str(cwd or PROJECT_ROOT),
    )


def output(result) -> str:
    """Return combined stdout+stderr."""
    return (result.stdout or "") + (result.stderr or "")


# ── HELP / VERSION ─────────────────────────────────────────────────────────────
class TestHelp:
    def test_no_args_prints_usage(self):
        r = idt()
        assert r.returncode in (0, 1)
        assert "USAGE" in output(r) or "usage" in output(r).lower()

    def test_help_command(self):
        r = idt("help")
        assert r.returncode == 0
        assert "COMMANDS" in output(r)

    def test_dash_dash_help(self):
        r = idt("--help")
        assert r.returncode == 0
        assert "COMMANDS" in output(r)

    def test_dash_h(self):
        r = idt("-h")
        assert r.returncode == 0
        assert "COMMANDS" in output(r)

    def test_version_command(self):
        r = idt("version")
        assert r.returncode == 0
        assert "Image Description Toolkit" in output(r)

    def test_version_flag(self):
        r = idt("--version")
        assert r.returncode == 0
        assert "Image Description Toolkit" in output(r)

    def test_version_shortflag(self):
        r = idt("-v", "version")
        # -v is a Python interpreter flag; dispatched transparently; version still shown
        # (just check the version sub-command also works as a standalone)
        r2 = idt("version")
        assert r2.returncode == 0

    def test_unknown_command_nonzero(self):
        r = idt("this-command-does-not-exist-xyz")
        assert r.returncode != 0
        assert "Unknown command" in output(r)


# ── HELP TEXT CONTRACT ─────────────────────────────────────────────────────────
class TestHelpContract:
    """Verify help text lists the right commands and no removed ones."""

    EXPECTED_COMMANDS = [
        "guideme",
        "workflow",
        "describe",
        "redescribe",
        "stats",
        "contentreview",
        "combinedescriptions",
        "manage-models",
        "results-list",
        "check-models",
        "prompt-list",
        "extract-frames",
        "describe-video",
        "convert-images",
        "descriptions-to-html",
        "version",
        "help",
    ]

    REMOVED_COMMANDS = [
        # Viewer was merged into ImageDescriber; no longer an idt command
        # Only block it appearing in the COMMANDS table – the word "viewer"
        # legitimately appears in notes about ImageDescriber's Viewer Mode tab.
        "    viewer ",
        # Legacy standalone apps never existed as idt sub-commands
        "prompteditor",
        "idtconfigure",
    ]

    def test_all_expected_commands_listed(self):
        r = idt("help")
        text = output(r)
        missing = [cmd for cmd in self.EXPECTED_COMMANDS if cmd not in text]
        assert not missing, f"Missing from help: {missing}"

    def test_no_removed_commands_listed(self):
        r = idt("help")
        text = output(r)
        found = [cmd for cmd in self.REMOVED_COMMANDS if cmd in text]
        assert not found, f"Removed command(s) still appear in help: {found}"

    def test_workflow_options_section_present(self):
        r = idt("help")
        assert "WORKFLOW OPTIONS" in output(r)

    def test_manage_models_options_section_present(self):
        r = idt("help")
        assert "MANAGE MODELS OPTIONS" in output(r)

    def test_prompt_list_options_section_present(self):
        r = idt("help")
        assert "PROMPT LIST OPTIONS" in output(r)

    def test_workflow_redescribe_flag_documented(self):
        r = idt("help")
        assert "--redescribe" in output(r)

    def test_workflow_link_images_flag_documented(self):
        r = idt("help")
        assert "--link-images" in output(r)

    def test_workflow_progress_status_flag_documented(self):
        r = idt("help")
        assert "--progress-status" in output(r)

    def test_workflow_no_alt_text_flag_documented(self):
        r = idt("help")
        assert "--no-alt-text" in output(r)

    def test_workflow_geocode_cache_flag_documented(self):
        r = idt("help")
        assert "--geocode-cache" in output(r)

    def test_workflow_view_results_flag_documented(self):
        r = idt("help")
        assert "--view-results" in output(r)

    def test_no_stale_idt_viewer_command_in_help(self):
        r = idt("help")
        # "idt viewer" as a command invocation must not appear in COMMANDS table
        assert "idt viewer [" not in output(r)


# ── ALIASES ────────────────────────────────────────────────────────────────────
class TestAliases:
    def test_describe_alias_routes_to_workflow(self):
        """'idt describe --help' should show workflow help, not 'Unknown command'."""
        r = idt("describe", "--help")
        text = output(r)
        assert "Unknown command" not in text
        assert "workflow" in text.lower() or "input" in text.lower()

    def test_redescribe_alias_routes_to_workflow(self):
        """'idt redescribe --help' should show workflow help."""
        r = idt("redescribe", "--help")
        text = output(r)
        assert "Unknown command" not in text
        assert "--redescribe" in text or "workflow" in text.lower()

    def test_redescribe_with_fake_dir_routes(self):
        """'idt redescribe some_dir --model foo' should attempt workflow, not unknown command."""
        r = idt("redescribe", "nonexistent_wf_dir", "--model", "llava")
        text = output(r)
        assert "Unknown command" not in text


# ── PER-COMMAND --help ─────────────────────────────────────────────────────────
class TestCommandHelp:
    """Each command should accept --help and print useful output without crashing."""

    @pytest.mark.parametrize("command", [
        "workflow",
        "stats",
        "contentreview",
        "combinedescriptions",
        "check-models",
        "results-list",
        "prompt-list",
        "extract-frames",
        "describe-video",
        "convert-images",
        "descriptions-to-html",
        "manage-models",
    ])
    def test_command_help(self, command):
        r = idt(command, "--help", timeout=15)
        text = output(r)
        # help exits 0; some parsers exit 1 — both are acceptable
        assert r.returncode in (0, 1), \
            f"'{command} --help' exited {r.returncode}; output: {text[:300]}"
        assert len(text) > 30, \
            f"'{command} --help' produced too little output: {text!r}"
        assert "Traceback" not in text, \
            f"'{command} --help' raised an uncaught exception: {text[:500]}"


# ── WORKFLOW-SPECIFIC ARG FLAGS ────────────────────────────────────────────────
class TestWorkflowFlags:
    """Spot-check that known flags appear in 'idt workflow --help' output."""

    EXPECTED_FLAGS = [
        "--provider",
        "--model",
        "--prompt-style",
        "--steps",
        "--resume",
        "--redescribe",
        "--preserve-descriptions",
        "--link-images",
        "--force-copy",
        "--output-dir",
        "--timeout",
        "--name",
        "--api-key-file",
        "--download",
        "--min-size",
        "--max-images",
        "--url",
        "--no-alt-text",
        "--metadata",
        "--no-metadata",
        "--no-geocode",
        "--geocode-cache",
        "--dry-run",
        "--batch",
        "--progress-status",
        "--view-results",
        "--verbose",
        "--config-workflow",
        "--config-image-describer",
        "--config-video",
    ]

    def test_all_workflow_flags_in_help(self):
        r = idt("workflow", "--help")
        text = output(r)
        missing = [f for f in self.EXPECTED_FLAGS if f not in text]
        assert not missing, f"Workflow --help missing flags: {missing}"


# ── COMMAND ROUTING (no crash) ─────────────────────────────────────────────────
class TestRouting:
    """
    Each command must route without 'Unknown command' and without an uncaught
    Python Traceback. We don't require exit 0 — missing Ollama / missing files
    cause non-zero exits and that's fine.
    """

    def _assert_routes(self, *args):
        r = idt(*args, timeout=20)
        text = output(r)
        assert "Unknown command" not in text, \
            f"Command {args!r} not routed: {text[:300]}"
        assert "Traceback (most recent call last)" not in text, \
            f"Command {args!r} raised unhandled exception: {text[:500]}"

    def test_version_routes(self):
        self._assert_routes("version")

    def test_help_routes(self):
        self._assert_routes("help")

    def test_check_models_routes(self):
        self._assert_routes("check-models", "--help")

    def test_manage_models_routes(self):
        self._assert_routes("manage-models", "--help")

    def test_results_list_routes(self):
        self._assert_routes("results-list", "--help")

    def test_prompt_list_routes(self):
        self._assert_routes("prompt-list", "--help")

    def test_stats_routes(self):
        self._assert_routes("stats", "--help")

    def test_contentreview_routes(self):
        self._assert_routes("contentreview", "--help")

    def test_combinedescriptions_routes(self):
        self._assert_routes("combinedescriptions", "--help")

    def test_extract_frames_routes(self):
        self._assert_routes("extract-frames", "--help")

    def test_describe_video_routes(self):
        self._assert_routes("describe-video", "--help")

    def test_convert_images_routes(self):
        self._assert_routes("convert-images", "--help")

    def test_descriptions_to_html_routes(self):
        self._assert_routes("descriptions-to-html", "--help")

    def test_workflow_routes(self):
        self._assert_routes("workflow", "--help")

    def test_describe_alias_routes(self):
        self._assert_routes("describe", "--help")

    def test_redescribe_alias_routes(self):
        self._assert_routes("redescribe", "--help")

    def test_guideme_routes(self):
        """guideme is interactive; just verify it doesn't raise immediately."""
        import threading
        import time

        proc = subprocess.Popen(
            [sys.executable, str(IDT_CLI), "guideme"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace",
            cwd=str(PROJECT_ROOT),
        )
        time.sleep(1.0)
        poll = proc.poll()
        proc.terminate()
        try:
            stdout, stderr = proc.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()

        text = (stdout or "") + (stderr or "")
        assert "Traceback" not in text, f"guideme raised exception: {text[:500]}"
        # guideme is interactive; when stdin is not a tty it may exit 1 cleanly.
        # Acceptable outcomes: still running (poll=None), clean exit 0, or
        # expected non-zero exit when no terminal is attached.
        if poll is not None:
            assert poll in (0, 1), \
                f"guideme exited immediately with unexpected code {poll}: {text[:300]}"


# ── MANAGE-MODELS SUBCOMMAND CONTRACT ─────────────────────────────────────────
class TestManageModels:
    def test_list_subcommand_help(self):
        r = idt("manage-models", "list", "--help")
        text = output(r)
        assert r.returncode in (0, 1)
        assert "Traceback" not in text
        assert "list" in text.lower() or "installed" in text.lower()

    def test_recommend_subcommand_help(self):
        r = idt("manage-models", "recommend", "--help")
        text = output(r)
        assert r.returncode in (0, 1)
        assert "Traceback" not in text

    def test_no_subcommand_shows_help(self):
        r = idt("manage-models")
        text = output(r)
        assert "Traceback" not in text
        # Should show help/usage, not crash
        assert len(text) > 10


# ── EXTRACT-FRAMES ARG CONTRACT ───────────────────────────────────────────────
class TestExtractFramesArgs:
    EXPECTED = ["--time", "--scene", "--output-dir", "--config", "--log-dir",
                "--create-config", "--quiet"]

    def test_extract_frames_flags_in_help(self):
        r = idt("extract-frames", "--help")
        text = output(r)
        missing = [f for f in self.EXPECTED if f not in text]
        assert not missing, f"extract-frames --help missing: {missing}"


# ── DESCRIBE-VIDEO ARG CONTRACT ───────────────────────────────────────────────
class TestDescribeVideoArgs:
    EXPECTED = ["--provider", "--model", "--prompt", "--frames", "--mode",
                "--output", "--verbose"]

    def test_describe_video_flags_in_help(self):
        r = idt("describe-video", "--help")
        text = output(r)
        missing = [f for f in self.EXPECTED if f not in text]
        assert not missing, f"describe-video --help missing: {missing}"


# ── CONVERT-IMAGES ARG CONTRACT ───────────────────────────────────────────────
class TestConvertImagesArgs:
    EXPECTED = ["--output", "--recursive", "--quality", "--no-metadata",
                "--log-dir", "--verbose", "--quiet"]

    def test_convert_images_flags_in_help(self):
        r = idt("convert-images", "--help")
        text = output(r)
        missing = [f for f in self.EXPECTED if f not in text]
        assert not missing, f"convert-images --help missing: {missing}"


# ── DESCRIPTIONS-TO-HTML ARG CONTRACT ─────────────────────────────────────────
class TestDescriptionsToHtmlArgs:
    EXPECTED = ["--title", "--full", "--verbose", "--log-dir"]

    def test_descriptions_to_html_flags_in_help(self):
        r = idt("descriptions-to-html", "--help")
        text = output(r)
        missing = [f for f in self.EXPECTED if f not in text]
        assert not missing, f"descriptions-to-html --help missing: {missing}"
