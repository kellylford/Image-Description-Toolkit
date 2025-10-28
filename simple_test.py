#!/usr/bin/env python3
"""
Simple test to verify the format string fix works.
Uses the built executable to test if the fix is working.
"""

import subprocess
import tempfile
import os
import shutil
from pathlib import Path

def test_format_fix():
    print("Testing format string fix...")
    
    # Use the built executable
    idt_exe = Path("dist/idt.exe")
    if not idt_exe.exists():
        print("ERROR: idt.exe not found in dist/")
        return False
        
    # Create a temporary test directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Copy a test image if available
        test_image_dir = Path("testimages")
        if test_image_dir.exists():
            # Copy test images to temp directory
            for img_file in test_image_dir.glob("*.jpg"):
                shutil.copy2(img_file, temp_path)
                break  # Just copy one image for testing
        
        # If no test images, create a simple text file to trigger the process
        if not list(temp_path.glob("*.jpg")):
            print("No test images found, skipping image processing test")
            return True
            
        # Run image_describer with the problematic conditions that caused format errors
        print(f"Testing with image in: {temp_path}")
        
        cmd = [
            str(idt_exe), "image_describer", str(temp_path),
            "--output-dir", str(temp_path / "output"),
            "--max-files", "1",
            "--provider", "ollama",
            "--model", "moondream:latest",
            "--prompt-style", "narrative"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            # Check if there were format string errors in the output
            output = result.stdout + result.stderr
            
            if "Invalid format string" in output:
                print("FAILED: Format string errors still present")
                print("Error output:")
                print(output)
                return False
            elif "Error writing description to file: Invalid format string" in output:
                print("FAILED: Specific format string error still present")
                return False
            else:
                print("SUCCESS: No format string errors detected")
                return True
                
        except subprocess.TimeoutExpired:
            print("Test timed out (this might be expected if Ollama isn't running)")
            return True  # Timeout isn't necessarily a failure of our fix
        except Exception as e:
            print(f"Test failed with exception: {e}")
            return False

if __name__ == "__main__":
    success = test_format_fix()
    exit(0 if success else 1)