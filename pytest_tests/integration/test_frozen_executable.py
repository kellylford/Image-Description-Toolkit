"""
Test to verify frozen executable can import and use versioning module.

This test would have caught the missing versioning.py in the PyInstaller spec.
It's marked as slow since it requires building the executable first.
"""
import subprocess
import sys
from pathlib import Path
import pytest


@pytest.mark.slow
@pytest.mark.integration
def test_frozen_executable_has_versioning():
    """Verify frozen executable can import versioning and show version info"""
    exe_path = Path(__file__).parent.parent.parent / 'dist' / 'idt.exe'
    
    # Skip if executable doesn't exist (dev environment or build not run yet)
    if not exe_path.exists():
        pytest.skip(f"Frozen executable not found at {exe_path}")
    
    # Run version command
    result = subprocess.run(
        [str(exe_path), 'version'],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    # Should succeed
    assert result.returncode == 0, f"version command failed: {result.stderr}"
    
    # Should contain version banner components
    output = result.stdout
    assert 'Version:' in output, "Missing 'Version:' in output"
    assert 'Commit:' in output, "Missing 'Commit:' in output"
    assert 'Mode:' in output, "Missing 'Mode:' in output"
    
    # Mode should be "Frozen" for built executable
    assert 'Frozen' in output, "Executable should report Mode: Frozen"


@pytest.mark.slow
@pytest.mark.integration
def test_frozen_workflow_imports_versioning():
    """Verify workflow command can import versioning (would fail if not in spec)"""
    exe_path = Path(__file__).parent.parent.parent / 'dist' / 'idt.exe'
    
    if not exe_path.exists():
        pytest.skip(f"Frozen executable not found at {exe_path}")
    
    # Run workflow help - this imports workflow.py which imports versioning
    result = subprocess.run(
        [str(exe_path), 'workflow', '--help'],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    # Should succeed without import errors
    assert result.returncode == 0, (
        f"workflow command failed (likely versioning import error): {result.stderr}"
    )
    
    # Should show workflow help
    assert 'workflow' in result.stdout.lower(), "Missing workflow help output"


@pytest.mark.slow  
@pytest.mark.integration
def test_frozen_executable_basic_commands():
    """Verify basic commands work in frozen executable"""
    exe_path = Path(__file__).parent.parent.parent / 'dist' / 'idt.exe'
    
    if not exe_path.exists():
        pytest.skip(f"Frozen executable not found at {exe_path}")
    
    commands_to_test = [
        (['--help'], 'main help'),
        (['image_describer', '--help'], 'image_describer help'),
        (['convert-images', '--help'], 'convert-images help'),
    ]
    
    for cmd, description in commands_to_test:
        result = subprocess.run(
            [str(exe_path)] + cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        assert result.returncode == 0, (
            f"{description} failed: {result.stderr}"
        )
