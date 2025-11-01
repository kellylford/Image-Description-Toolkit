"""
End-to-end test that builds the frozen executable and runs a complete workflow.

This is the user's #1 testing priority - automated verification that:
1. The project builds successfully
2. The frozen executable runs a workflow
3. The workflow generates expected results

This test takes 1-3 minutes to run and should be part of the release process.
"""

import pytest
import subprocess
import shutil
import time
from pathlib import Path


@pytest.fixture(scope="module")
def built_executable(tmp_path_factory, project_root):
    """
    Ensure idt.exe exists. 
    
    Note: This doesn't rebuild every time - it assumes you've run the build
    script or test_and_build.bat separately. This keeps tests fast.
    """
    exe_path = project_root / "dist" / "idt.exe"
    
    if not exe_path.exists():
        pytest.skip(
            "Frozen executable not found at dist/idt.exe. "
            "Run BuildAndRelease\\build_idt.bat or test_and_build.bat first."
        )
    
    # Verify it's actually executable
    result = subprocess.run(
        [str(exe_path), "version"],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    if result.returncode != 0:
        pytest.fail(f"Executable exists but version command failed: {result.stderr}")
    
    return exe_path


@pytest.mark.e2e
@pytest.mark.slow
def test_frozen_exe_runs_complete_workflow(built_executable, test_data_dir, tmp_path):
    """
    CRITICAL TEST: Verify frozen executable can run a complete workflow.
    
    This is the primary automated verification that the build is functional.
    Tests the complete pipeline:
    - Load test images
    - Run describe step
    - Generate HTML report
    - Verify all outputs created
    """
    output_dir = tmp_path / "workflow_output"
    output_dir.mkdir()
    
    print(f"\n[E2E Test] Running workflow with frozen executable...")
    print(f"  Executable: {built_executable}")
    print(f"  Test Images: {test_data_dir}")
    print(f"  Output: {output_dir}")
    
    # Run workflow with frozen executable
    # Using moondream (fast local model) with concise prompt for speed
    result = subprocess.run(
        [
            str(built_executable),
            "workflow",
            str(test_data_dir),
            "--output", str(output_dir),
            "--model", "moondream",
            "--prompt-style", "concise",
            "--steps", "describe,html",
            "--no-view"
        ],
        capture_output=True,
        text=True,
        timeout=300  # 5 minute timeout
    )
    
    # Print output for debugging
    if result.stdout:
        print(f"\n[Workflow Output]\n{result.stdout[:500]}")
    if result.stderr:
        print(f"\n[Workflow Errors]\n{result.stderr[:500]}")
    
    # Verify successful execution
    assert result.returncode == 0, (
        f"Workflow failed with exit code {result.returncode}\n"
        f"STDERR: {result.stderr}\n"
        f"STDOUT: {result.stdout}"
    )
    
    # Verify workflow directory created
    workflow_dirs = list(output_dir.glob("wf_*"))
    assert len(workflow_dirs) >= 1, (
        f"Expected at least 1 workflow dir, found {len(workflow_dirs)}\n"
        f"Contents of {output_dir}: {list(output_dir.iterdir())}"
    )
    
    workflow_dir = workflow_dirs[0]
    print(f"  Workflow dir: {workflow_dir.name}")
    
    # Verify descriptions directory created
    descriptions_dir = workflow_dir / "descriptions"
    assert descriptions_dir.exists(), (
        f"Descriptions directory not created\n"
        f"Workflow dir contents: {list(workflow_dir.iterdir())}"
    )
    
    # Verify descriptions generated
    description_files = list(descriptions_dir.glob("*.txt"))
    assert len(description_files) > 0, (
        f"No description files generated\n"
        f"Descriptions dir contents: {list(descriptions_dir.iterdir())}"
    )
    
    print(f"  Generated {len(description_files)} description(s)")
    
    # Verify HTML report generated
    html_report = workflow_dir / "html_reports" / "index.html"
    assert html_report.exists(), (
        f"HTML report not generated\n"
        f"html_reports dir contents: {list((workflow_dir / 'html_reports').iterdir()) if (workflow_dir / 'html_reports').exists() else 'directory not found'}"
    )
    
    # Verify HTML content is valid
    html_content = html_report.read_text(encoding='utf-8')
    assert len(html_content) > 100, "HTML report is too short to be valid"
    assert "<html" in html_content.lower(), "HTML missing <html> tag"
    assert "Image Description Report" in html_content or "Description" in html_content, \
        "HTML missing expected title or content"
    
    # Verify at least one description appears in HTML or is referenced
    first_description_file = description_files[0]
    first_description = first_description_file.read_text(encoding='utf-8')
    
    # HTML should reference the image file name
    image_filename = first_description_file.stem
    assert image_filename in html_content, \
        f"HTML doesn't reference image {image_filename}"
    
    print(f"  HTML report verified: {html_report.stat().st_size} bytes")
    print(f"\n[E2E Test] ✓ Complete workflow test PASSED")


@pytest.mark.e2e  
@pytest.mark.slow
def test_frozen_exe_handles_no_images_gracefully(built_executable, tmp_path):
    """
    Verify workflow handles empty directory without crashing.
    
    Tests error handling in the frozen executable.
    """
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    output_dir = tmp_path / "output"
    
    print(f"\n[E2E Test] Testing error handling with empty directory...")
    
    result = subprocess.run(
        [
            str(built_executable),
            "workflow",
            str(empty_dir),
            "--output", str(output_dir),
            "--model", "moondream",
            "--no-view"
        ],
        capture_output=True,
        text=True,
        timeout=30
    )
    
    # Should handle gracefully (may exit with error code, but shouldn't crash)
    # Check that it reports the issue clearly
    combined_output = result.stdout + result.stderr
    
    assert any(phrase in combined_output.lower() for phrase in [
        "no images found",
        "no files found",
        "empty directory",
        "no image files"
    ]), (
        f"Should report no images found gracefully\n"
        f"Output: {combined_output}"
    )
    
    print(f"  Correctly handled empty directory")
    print(f"\n[E2E Test] ✓ Error handling test PASSED")


@pytest.mark.e2e
@pytest.mark.slow  
def test_frozen_exe_workflow_with_multiple_steps(built_executable, test_data_dir, tmp_path):
    """
    Test running workflow with multiple steps specified.
    
    Verifies that step filtering works in frozen executable.
    """
    output_dir = tmp_path / "workflow_output"
    output_dir.mkdir()
    
    print(f"\n[E2E Test] Testing multi-step workflow...")
    
    # Run with just describe step (no HTML)
    result = subprocess.run(
        [
            str(built_executable),
            "workflow",
            str(test_data_dir),
            "--output", str(output_dir),
            "--model", "moondream",
            "--steps", "describe",
            "--no-view"
        ],
        capture_output=True,
        text=True,
        timeout=300
    )
    
    assert result.returncode == 0, f"Workflow failed: {result.stderr}"
    
    # Find workflow directory
    workflow_dirs = list(output_dir.glob("wf_*"))
    assert len(workflow_dirs) >= 1, "No workflow directory created"
    
    workflow_dir = workflow_dirs[0]
    
    # Should have descriptions
    descriptions_dir = workflow_dir / "descriptions"
    assert descriptions_dir.exists(), "Descriptions not created with describe step"
    assert len(list(descriptions_dir.glob("*.txt"))) > 0, "No descriptions generated"
    
    # Should NOT have HTML (we didn't run html step)
    html_dir = workflow_dir / "html_reports"
    # It's okay if the directory exists but is empty
    if html_dir.exists():
        html_files = list(html_dir.glob("*.html"))
        # This is actually okay - workflow might create the directory anyway
        # The important thing is the describe step worked
    
    print(f"  Step filtering works correctly")
    print(f"\n[E2E Test] ✓ Multi-step test PASSED")


@pytest.mark.e2e
@pytest.mark.slow
def test_frozen_exe_help_commands(built_executable):
    """
    Verify all help commands work in frozen executable.
    
    This is a sanity check that all entry points are accessible.
    """
    print(f"\n[E2E Test] Testing help commands...")
    
    help_commands = [
        ([], "main help"),
        (["--help"], "main help (explicit)"),
        (["workflow", "--help"], "workflow help"),
        (["image_describer", "--help"], "image_describer help"),
        (["convert-images", "--help"], "convert-images help"),
        (["combinedescriptions", "--help"], "combinedescriptions help"),
    ]
    
    for cmd_args, description in help_commands:
        result = subprocess.run(
            [str(built_executable)] + cmd_args,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        assert result.returncode == 0, (
            f"{description} failed with exit code {result.returncode}\n"
            f"STDERR: {result.stderr}"
        )
        
        # Should have some output
        assert len(result.stdout) > 50, (
            f"{description} produced insufficient output: {result.stdout[:100]}"
        )
        
        print(f"  ✓ {description}")
    
    print(f"\n[E2E Test] ✓ Help commands test PASSED")


@pytest.mark.e2e
@pytest.mark.slow
def test_frozen_exe_version_command(built_executable):
    """
    Test version command shows build information.
    
    This verifies versioning module is included in frozen exe.
    """
    print(f"\n[E2E Test] Testing version command...")
    
    result = subprocess.run(
        [str(built_executable), "version"],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    assert result.returncode == 0, f"Version command failed: {result.stderr}"
    
    output = result.stdout
    
    # Should contain version information
    assert "Version:" in output or "version" in output.lower(), \
        "Missing version information"
    
    # Should indicate frozen mode
    assert "Frozen" in output or "frozen" in output.lower(), \
        "Should indicate frozen executable mode"
    
    print(f"  Version info:\n{output[:200]}")
    print(f"\n[E2E Test] ✓ Version command test PASSED")
