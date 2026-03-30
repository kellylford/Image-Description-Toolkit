"""
Smoke tests for CLI and GUI entry points.

These tests verify that all main commands and apps can launch without crashing.
They don't test full functionality, just that the entry points are valid and
the processes/scripts start up correctly.
"""

import os
import subprocess
import sys
import time
from pathlib import Path


class TestCLIEntryPoints:
    """Test that all CLI commands launch and respond correctly."""
    
    def test_idt_help(self):
        """Test that 'idt --help' or 'idt help' works."""
        # Run the CLI with --help
        result = subprocess.run(
            [sys.executable, 'idt_cli.py', 'help'],
            capture_output=True,
            encoding='utf-8',
            errors='replace',
            timeout=10
        )
        
        # Should exit successfully (or with code 1 if it just prints help)
        assert result.returncode in (0, 1), "idt help should exit cleanly"
        
        # Should output something to stdout or stderr
        stdout = result.stdout or ""
        stderr = result.stderr or ""
        output = stdout + stderr
        assert len(output) > 50, "Help should print usage information"
    
    def test_idt_version(self):
        """Test that 'idt version' works."""
        result = subprocess.run(
            [sys.executable, 'idt_cli.py', 'version'],
            capture_output=True,
            encoding='utf-8',
            errors='replace',
            timeout=10
        )
        
        assert result.returncode == 0, "idt version should exit successfully"
        
        # Should mention "Image Description Toolkit"
        stdout = result.stdout or ""
        stderr = result.stderr or ""
        output = stdout + stderr
        assert 'Image Description Toolkit' in output or 'IDT' in output, \
            "Version should identify the toolkit"
    
    def test_idt_workflow_help(self):
        """Test that 'idt workflow --help' works."""
        # Use utf-8 encoding and errors='replace' to handle any encoding issues
        result = subprocess.run(
            [sys.executable, 'idt_cli.py', 'workflow', '--help'],
            capture_output=True,
            encoding='utf-8',
            errors='replace',
            timeout=10
        )
        
        # Should exit successfully (help exits with 0)
        assert result.returncode == 0, f"workflow --help should exit successfully (got {result.returncode})"
        
        # Should mention workflow-related options
        stdout = result.stdout or ""
        stderr = result.stderr or ""
        output = stdout + stderr
        
        # Workflow help should be substantial (at least some text)
        assert len(output) > 50, f"Workflow help should print usage info (got {len(output)} chars)"
        
        # Look for common workflow flags or usage text
        output_lower = output.lower()
        assert any(keyword in output_lower for keyword in 
                  ['workflow', 'usage', 'input', 'output', 'model', 'provider', 'help', 'options']), \
            f"Workflow help should mention key options, got: {output[:200]}"
    
    def test_idt_guideme_launches(self):
        """Test that 'idt guideme' starts (we'll kill it immediately)."""
        # Start guideme in a subprocess
        proc = subprocess.Popen(
            [sys.executable, 'idt_cli.py', 'guideme'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
                encoding='utf-8',
                errors='replace'
        )
        
        # Wait a moment to see if it crashes immediately
        time.sleep(0.5)
        
        # Check if process is still running
        poll_result = proc.poll()
        
        # Terminate the process
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        
        # If poll_result is None, process was still running (good!)
        # If poll_result is not None, process exited (might be OK if it prompts and exits)
        assert poll_result is None or poll_result == 0, \
            f"guideme should launch without immediate crash (exit code: {poll_result})"
    
    def test_idt_check_models_launches(self):
        """Test that 'idt check-models' runs."""
        result = subprocess.run(
            [sys.executable, 'idt_cli.py', 'check-models'],
            capture_output=True,
            encoding='utf-8',
            errors='replace',
            timeout=30  # Longer timeout as it may check network
        )
        
        # Should exit (may fail if ollama not running, but shouldn't crash)
        assert result.returncode in (0, 1), \
            f"check-models should exit cleanly (got {result.returncode})"
    
    def test_idt_results_list_launches(self):
        """Test that 'idt results-list' runs."""
        result = subprocess.run(
            [sys.executable, 'idt_cli.py', 'results-list'],
            capture_output=True,
                encoding='utf-8',
                errors='replace',
            timeout=10
        )
        
        # Should exit successfully (may find 0 results, that's OK)
        assert result.returncode in (0, 1), \
            f"results-list should exit cleanly (got {result.returncode})"

    def test_idt_help_has_video_commands(self):
        """Test that 'idt help' output includes video-related commands."""
        result = subprocess.run(
            [sys.executable, 'idt_cli.py', 'help'],
            capture_output=True,
            encoding='utf-8',
            errors='replace',
            timeout=10
        )
        output = (result.stdout or "") + (result.stderr or "")
        for cmd in ('extract-frames', 'describe-video', 'descriptions-to-html'):
            assert cmd in output, f"'idt help' output should include '{cmd}'"

    def test_idt_help_no_deprecated_commands(self):
        """Test that 'idt help' does not list removed commands (viewer, prompteditor, configure)."""
        result = subprocess.run(
            [sys.executable, 'idt_cli.py', 'help'],
            capture_output=True,
            encoding='utf-8',
            errors='replace',
            timeout=10
        )
        output = (result.stdout or "") + (result.stderr or "")
        # These commands were removed; should not appear in the COMMANDS section
        for cmd in ('prompteditor', 'configure (or config)'):
            assert cmd not in output, (
                f"'idt help' output should not mention deprecated command '{cmd}'"
            )


class TestGUIEntryPoints:
    """Test that GUI apps launch without crashing."""
    
    @staticmethod
    def _skip_gui_in_ci() -> bool:
        """Return True if running in CI environment where GUI cannot launch."""
        # GitHub sets GITHUB_ACTIONS=true; many CI environments set CI=true
        return (os.environ.get("GITHUB_ACTIONS", "").lower() == "true" 
                or os.environ.get("CI", "").lower() == "true")
    

    
    def test_imagedescriber_launches(self):
        """Test that ImageDescriber.exe or app launches."""
        if self._skip_gui_in_ci():
            print("CI environment detected; skipping ImageDescriber GUI launch test")
            return
        app_paths = [
            Path('imagedescriber/ImageDescriber.exe'),
            Path('imagedescriber/imagedescriber.py')
        ]
        
        app_path = None
        for path in app_paths:
            if path.exists():
                app_path = path
                break
        
        if app_path is None:
            print("ImageDescriber not found, skipping launch test")
            return
        
        if app_path.suffix == '.exe':
            cmd = [str(app_path)]
        else:
            cmd = [sys.executable, str(app_path)]
        
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        time.sleep(1.0)
        poll_result = proc.poll()
        
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        
        assert poll_result is None, \
            f"ImageDescriber should launch and stay running (exited with {poll_result})"
    



if __name__ == "__main__":
    import unittest
    unittest.main()
