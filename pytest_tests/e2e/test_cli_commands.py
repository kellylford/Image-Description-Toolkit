"""
End-to-end tests for all CLI commands with frozen executable.

Tests that all command-line interfaces work correctly when running
from the frozen PyInstaller executable.
"""

import pytest
import subprocess
from pathlib import Path


@pytest.mark.e2e
def test_cli_main_help(built_executable):
    """Test main help command"""
    result = subprocess.run(
        [str(built_executable), "--help"],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower() or "Usage:" in result.stdout


@pytest.mark.e2e
def test_cli_version(built_executable):
    """Test version command"""
    result = subprocess.run(
        [str(built_executable), "version"],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    assert result.returncode == 0
    assert len(result.stdout) > 20, "Version output too short"


@pytest.mark.e2e
def test_cli_list_results(built_executable, tmp_path):
    """Test list-results command"""
    # Create empty output directory for testing
    output_dir = tmp_path / "results"
    output_dir.mkdir()
    
    result = subprocess.run(
        [str(built_executable), "list-results", str(output_dir)],
        capture_output=True,
        text=True,
        timeout=30
    )
    
    # Should succeed even with empty directory
    assert result.returncode == 0


@pytest.mark.e2e  
def test_cli_list_prompts(built_executable):
    """Test list-prompts command"""
    result = subprocess.run(
        [str(built_executable), "list-prompts"],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    assert result.returncode == 0
    # Should show available prompt styles
    assert "narrative" in result.stdout.lower() or "prompts:" in result.stdout.lower()


@pytest.mark.e2e
def test_cli_guideme(built_executable, tmp_path, monkeypatch):
    """Test guideme command (non-interactive mode)"""
    # Create test directory
    test_dir = tmp_path / "images"
    test_dir.mkdir()
    
    # guideme should fail gracefully if no input provided
    # We can't test interactive mode in CI, but we can test it launches
    result = subprocess.run(
        [str(built_executable), "guideme", "--help"],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    assert result.returncode == 0
    assert "guideme" in result.stdout.lower() or "guide" in result.stdout.lower()


@pytest.mark.e2e
def test_cli_image_describer_help(built_executable):
    """Test image_describer command help"""
    result = subprocess.run(
        [str(built_executable), "image_describer", "--help"],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    assert result.returncode == 0
    assert "image" in result.stdout.lower()


@pytest.mark.e2e
def test_cli_convert_images_help(built_executable):
    """Test convert-images command help"""
    result = subprocess.run(
        [str(built_executable), "convert-images", "--help"],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    assert result.returncode == 0
    assert "convert" in result.stdout.lower()


@pytest.mark.e2e
def test_cli_workflow_help(built_executable):
    """Test workflow command help"""
    result = subprocess.run(
        [str(built_executable), "workflow", "--help"],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    assert result.returncode == 0
    assert "workflow" in result.stdout.lower()


@pytest.mark.e2e
def test_cli_combinedescriptions_help(built_executable):
    """Test combinedescriptions command help"""
    result = subprocess.run(
        [str(built_executable), "combinedescriptions", "--help"],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    assert result.returncode == 0
    # Command might have variations in naming
    assert "combine" in result.stdout.lower() or "description" in result.stdout.lower()


@pytest.mark.e2e
def test_cli_stats_help(built_executable):
    """Test stats command help"""
    result = subprocess.run(
        [str(built_executable), "stats", "--help"],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    assert result.returncode == 0
    assert "stats" in result.stdout.lower() or "statistic" in result.stdout.lower()


@pytest.mark.e2e
@pytest.mark.slow
def test_cli_convert_images_with_sample(built_executable, test_data_dir, tmp_path):
    """Test convert-images command with actual file"""
    # Find a test image
    test_images = list(test_data_dir.glob("*.jpg")) + list(test_data_dir.glob("*.jpeg"))
    
    if not test_images:
        pytest.skip("No test images available")
    
    output_dir = tmp_path / "converted"
    output_dir.mkdir()
    
    result = subprocess.run(
        [
            str(built_executable),
            "convert-images",
            str(test_data_dir),
            "--output", str(output_dir)
        ],
        capture_output=True,
        text=True,
        timeout=60
    )
    
    # Should succeed or report no convertible images
    assert result.returncode == 0 or "no" in result.stdout.lower()


@pytest.mark.e2e
@pytest.mark.slow
def test_cli_list_results_with_workflow(built_executable, sample_workflow_directory):
    """Test list-results with actual workflow directory"""
    # Use the parent directory that contains the workflow
    results_dir = sample_workflow_directory.parent
    
    result = subprocess.run(
        [str(built_executable), "list-results", str(results_dir)],
        capture_output=True,
        text=True,
        timeout=30
    )
    
    assert result.returncode == 0
    # Should find and list the workflow
    output = result.stdout.lower()
    assert "workflow" in output or "wf_" in output or "found" in output


@pytest.mark.e2e
def test_cli_invalid_command(built_executable):
    """Test that invalid command shows helpful error"""
    result = subprocess.run(
        [str(built_executable), "nonexistent-command"],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    # Should exit with error
    assert result.returncode != 0
    # Should show error message
    combined_output = result.stdout + result.stderr
    assert "invalid" in combined_output.lower() or "unknown" in combined_output.lower() \
           or "error" in combined_output.lower()


@pytest.mark.e2e
def test_cli_missing_required_argument(built_executable):
    """Test that missing required arguments show helpful error"""
    # workflow requires input directory
    result = subprocess.run(
        [str(built_executable), "workflow"],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    # Should exit with error
    assert result.returncode != 0
    # Should show error about missing argument
    combined_output = result.stdout + result.stderr
    assert any(word in combined_output.lower() for word in ["required", "argument", "missing", "error"])


# Fixture to ensure built_executable is available
@pytest.fixture(scope="module")
def built_executable(project_root):
    """Get path to built executable, skip if not found"""
    exe_path = project_root / "dist" / "idt.exe"
    
    if not exe_path.exists():
        pytest.skip("Frozen executable not found. Run build first.")
    
    return exe_path
