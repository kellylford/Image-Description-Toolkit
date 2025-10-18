#!/usr/bin/env python3
"""
Test script to verify that new prompts are correctly detected in analysis scripts.

This script:
1. Creates test workflow directories with different prompts
2. Runs combine_workflow_descriptions.py to verify prompts are detected
3. Validates that no prompts show as "unknown"
"""

import sys
import json
import shutil
from pathlib import Path
import tempfile
import subprocess

# Add parent directory to path
script_dir = Path(__file__).parent
parent_dir = script_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from analysis.analysis_utils import load_prompt_styles_from_config


def create_test_workflow(base_dir: Path, prompt_style: str, workflow_num: int):
    """Create a test workflow directory with sample descriptions."""
    workflow_name = f"wf_ollama_moondream_{prompt_style}_20241018_{workflow_num:04d}"
    workflow_dir = base_dir / workflow_name
    desc_dir = workflow_dir / "descriptions"
    desc_dir.mkdir(parents=True, exist_ok=True)
    
    desc_file = desc_dir / "image_descriptions.txt"
    content = f"""File: test_image_{workflow_num}.jpg
Description: Test description for {prompt_style} prompt style.
Provider: ollama
Model: moondream
Prompt Style: {prompt_style}
---
"""
    desc_file.write_text(content)
    return workflow_dir


def run_combine_script(input_dir: Path, output_file: Path):
    """Run the combine_workflow_descriptions.py script."""
    cmd = [
        sys.executable,
        str(parent_dir / "analysis" / "combine_workflow_descriptions.py"),
        "--input-dir", str(input_dir),
        "--output", str(output_file)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout, result.stderr, result.returncode


def verify_output(output_text: str, expected_prompts: list) -> bool:
    """Verify that all expected prompts are detected and none show as unknown."""
    success = True
    
    print("\n=== Verification Results ===")
    
    # Check for unknown prompts
    if "unknown:" in output_text.lower():
        print("❌ FAIL: Found 'unknown' prompts in output")
        success = False
    else:
        print("✅ PASS: No 'unknown' prompts found")
    
    # Check that all expected prompts are found
    for prompt in expected_prompts:
        if f"{prompt}:" in output_text:
            print(f"✅ PASS: Found prompt '{prompt}'")
        else:
            print(f"❌ FAIL: Prompt '{prompt}' not found in output")
            success = False
    
    return success


def main():
    """Run the test."""
    print("=== Testing Prompt Detection in Analysis Scripts ===\n")
    
    # Load current prompt styles from config
    print("Loading prompt styles from config...")
    prompt_styles = load_prompt_styles_from_config()
    print(f"Found {len(prompt_styles)} prompt styles: {', '.join(prompt_styles)}\n")
    
    # Create temporary test directory
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "test_workflows"
        test_dir.mkdir()
        
        print(f"Creating test workflows in: {test_dir}")
        
        # Create test workflows for several prompts
        test_prompts = []
        for i, prompt in enumerate(prompt_styles[:5], 1):  # Test first 5 prompts
            create_test_workflow(test_dir, prompt, i)
            test_prompts.append(prompt)
            print(f"  Created workflow with prompt: {prompt}")
        
        print(f"\nCreated {len(test_prompts)} test workflows\n")
        
        # Run combine script
        print("Running combine_workflow_descriptions.py...")
        output_file = Path(temp_dir) / "combined_test.csv"
        stdout, stderr, returncode = run_combine_script(test_dir, output_file)
        
        if returncode != 0:
            print(f"❌ FAIL: Script returned error code {returncode}")
            print(f"STDERR: {stderr}")
            return 1
        
        print("Script completed successfully\n")
        
        # Verify results
        success = verify_output(stdout, test_prompts)
        
        # Show relevant output
        print("\n=== Script Output (Prompts Section) ===")
        lines = stdout.split('\n')
        capture = False
        for line in lines:
            if "Prompts found:" in line:
                capture = True
            if capture:
                print(line)
            if capture and line.strip() == "":
                break
        
        # Check CSV file
        if output_file.exists():
            print(f"\n✅ Output CSV created: {output_file}")
            with open(output_file, 'r') as f:
                lines = f.readlines()
                print(f"   CSV has {len(lines)} rows (including header)")
                if len(lines) > 1:
                    # Show header and first data row
                    print(f"   Header: {lines[0].strip()}")
                    print(f"   First row: {lines[1].strip()[:100]}...")
        else:
            print(f"❌ Output CSV not created")
            success = False
        
        print("\n" + "="*50)
        if success:
            print("✅ ALL TESTS PASSED")
            return 0
        else:
            print("❌ SOME TESTS FAILED")
            return 1


if __name__ == "__main__":
    sys.exit(main())
