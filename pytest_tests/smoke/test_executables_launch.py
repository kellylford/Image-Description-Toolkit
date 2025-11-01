"""
Smoke tests for executable launch verification.

These are quick tests to verify that all built executables can launch
without crashing. Useful for post-build validation.
"""

import pytest
import subprocess
from pathlib import Path


@pytest.fixture(scope="module")
def executables_dir(project_root):
    """Get paths to all executables"""
    return {
        'idt': project_root / "dist" / "idt.exe",
        'viewer': project_root / "viewer" / "dist" / "viewer_x64.exe",
        'imagedescriber': project_root / "imagedescriber" / "dist" / "ImageDescriber_x64.exe",
        'prompteditor': project_root / "prompt_editor" / "dist" / "prompt_editor_x64.exe",
        'idtconfigure': project_root / "idtconfigure" / "dist" / "idtconfigure_x64.exe",
    }


@pytest.mark.smoke
def test_idt_exe_launches(executables_dir):
    """Test that idt.exe launches and shows version"""
    exe_path = executables_dir['idt']
    
    if not exe_path.exists():
        pytest.skip(f"idt.exe not found at {exe_path}")
    
    result = subprocess.run(
        [str(exe_path), "version"],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    assert result.returncode == 0, f"idt.exe version failed: {result.stderr}"
    assert len(result.stdout) > 10, "Version output too short"


@pytest.mark.smoke
def test_viewer_exe_exists(executables_dir):
    """Test that viewer.exe exists (can't fully test GUI without display)"""
    exe_path = executables_dir['viewer']
    
    # Just check it exists - full GUI testing requires display
    if exe_path.exists():
        assert exe_path.stat().st_size > 1000, "Viewer executable seems too small"
    else:
        pytest.skip("Viewer not built yet")


@pytest.mark.smoke
def test_imagedescriber_exe_exists(executables_dir):
    """Test that ImageDescriber.exe exists"""
    exe_path = executables_dir['imagedescriber']
    
    if exe_path.exists():
        assert exe_path.stat().st_size > 1000, "ImageDescriber executable seems too small"
    else:
        pytest.skip("ImageDescriber not built yet")


@pytest.mark.smoke
def test_prompteditor_exe_exists(executables_dir):
    """Test that prompt_editor.exe exists"""
    exe_path = executables_dir['prompteditor']
    
    if exe_path.exists():
        assert exe_path.stat().st_size > 1000, "PromptEditor executable seems too small"
    else:
        pytest.skip("PromptEditor not built yet")


@pytest.mark.smoke
def test_idtconfigure_exe_exists(executables_dir):
    """Test that idtconfigure.exe exists"""
    exe_path = executables_dir['idtconfigure']
    
    if exe_path.exists():
        assert exe_path.stat().st_size > 1000, "IDTConfigure executable seems too small"
    else:
        pytest.skip("IDTConfigure not built yet")


@pytest.mark.smoke
def test_all_idt_commands_have_help(executables_dir):
    """Test that all idt commands have help text"""
    exe_path = executables_dir['idt']
    
    if not exe_path.exists():
        pytest.skip("idt.exe not found")
    
    commands = [
        "workflow",
        "image_describer",
        "convert-images",
        "list-results",
        "list-prompts",
        "guideme",
        "combinedescriptions",
        "stats",
    ]
    
    failed_commands = []
    
    for cmd in commands:
        result = subprocess.run(
            [str(exe_path), cmd, "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            failed_commands.append(cmd)
    
    assert len(failed_commands) == 0, f"Commands without help: {failed_commands}"
