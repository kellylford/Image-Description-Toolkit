"""
Smoke tests for CLI and GUI entry points.

These tests verify that all main commands can launch without crashing.
They don't test full functionality, just that the entry points are valid and
respond correctly.

CLI entry point: cli/main.py  (the active v4.5 CLI)
"""

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

_CLI = [sys.executable, str(Path(__file__).parent.parent.parent / "cli" / "main.py")]


class TestCLIEntryPoints:
    """Test that all active CLI commands (cli/main.py) launch and respond correctly."""

    def test_idt_help(self):
        """idt --help should print usage and exit 0."""
        result = subprocess.run(
            _CLI + ["--help"],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        assert result.returncode == 0, f"--help should exit 0, got {result.returncode}"
        output = (result.stdout or "") + (result.stderr or "")
        assert len(output) > 50, "Help should print usage information"
        assert "describe" in output.lower(), "--help should mention the describe command"

    def test_idt_version(self):
        """idt version should print the version and exit 0."""
        result = subprocess.run(
            _CLI + ["version"],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        assert result.returncode == 0, f"version should exit 0, got {result.returncode}"
        output = (result.stdout or "") + (result.stderr or "")
        assert "idt" in output.lower() or "4." in output, \
            f"version output should identify the toolkit, got: {output!r}"

    def test_idt_describe_help(self):
        """idt describe --help should print describe-specific options."""
        result = subprocess.run(
            _CLI + ["describe", "--help"],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        assert result.returncode == 0, f"describe --help should exit 0, got {result.returncode}"
        output = (result.stdout or "") + (result.stderr or "")
        assert len(output) > 50, "describe --help should print usage info"
        assert any(kw in output.lower() for kw in ["provider", "model", "prompt", "source"]), \
            "describe --help should mention key options"

    def test_idt_guideme_launches(self):
        """idt guideme should start (or exit cleanly when there is no terminal)."""
        proc = subprocess.Popen(
            _CLI + ["guideme"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace",
        )
        time.sleep(0.5)
        poll_result = proc.poll()
        stdout = proc.stdout.read() if poll_result is not None else ""
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        # Either still running (interactive terminal) or exited cleanly without
        # a Python traceback (expected when stdin is not a tty).
        if poll_result not in (None, 0, 1):
            pytest.fail(f"guideme crashed with unexpected exit code: {poll_result}")
        if poll_result not in (None, 0):
            assert "Traceback" not in stdout, "guideme should not crash with a traceback"

    def test_idt_models_launches(self):
        """idt models should exit cleanly (may have no models if Ollama isn't running)."""
        result = subprocess.run(
            _CLI + ["models"],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
        assert result.returncode in (0, 1), \
            f"models should exit cleanly (got {result.returncode})"

    def test_idt_help_has_core_commands(self):
        """idt --help should list the core commands present in v4.5."""
        result = subprocess.run(
            _CLI + ["--help"],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        output = (result.stdout or "") + (result.stderr or "")
        for cmd in ("describe", "status", "show", "embed", "export", "combine", "stats"):
            assert cmd in output, f"--help output should include '{cmd}'"

    def test_idt_no_info_noise_on_simple_command(self):
        """Running a simple command should not emit INFO: lines to stderr."""
        result = subprocess.run(
            _CLI + ["version"],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        stderr = result.stderr or ""
        assert "INFO:" not in stderr, \
            f"No INFO: lines should appear in stderr for 'version', got: {stderr!r}"


class TestGUIEntryPoints:
    """Test that GUI apps launch without crashing."""

    @staticmethod
    def _skip_gui_in_ci() -> bool:
        return (os.environ.get("GITHUB_ACTIONS", "").lower() == "true"
                or os.environ.get("CI", "").lower() == "true")

    def test_imagedescriber_launches(self):
        """ImageDescriber should launch and stay running."""
        if self._skip_gui_in_ci():
            pytest.skip("Skipping GUI launch test in CI environment")

        app_path = None
        for candidate in [
            Path("imagedescriber/ImageDescriber.exe"),
            Path("imagedescriber/imagedescriber.py"),
            Path("imagedescriber/imagedescriber_wx.py"),
        ]:
            if candidate.exists():
                app_path = candidate
                break

        if app_path is None:
            pytest.skip("ImageDescriber entry point not found")

        cmd = ([str(app_path)] if app_path.suffix == ".exe"
               else [sys.executable, str(app_path)])
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(1.0)
        poll_result = proc.poll()
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        assert poll_result is None, \
            f"ImageDescriber should stay running (exited with {poll_result})"


if __name__ == "__main__":
    import unittest
    unittest.main()
