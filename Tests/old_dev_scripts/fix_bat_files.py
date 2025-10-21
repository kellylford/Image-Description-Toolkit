#!/usr/bin/env python3
"""
Fix all internal bat files to support flexible argument handling like the external ones.
Changes rigid %1, %2 argument parsing to %* pass-through.
"""

import os
import re
from pathlib import Path


def fix_bat_file(bat_file_path):
    """Fix a single bat file to use flexible argument handling."""
    print(f"Fixing: {bat_file_path.name}")
    
    # Read the file
    content = bat_file_path.read_text()
    
    # Check if it's already using the new format
    if "%*" in content and "Supports all workflow options" in content:
        print(f"  ✅ Already fixed")
        return False
    
    # Check if it's using the old rigid format
    if "SET PROMPT_STYLE=%2" not in content:
        print(f"  ⏭️ Not a rigid argument bat file")
        return False
    
    # Extract the model name from the existing command
    model_match = re.search(r'--model\s+([^\s]+)', content)
    if not model_match:
        print(f"  ❌ Could not extract model name")
        return False
    
    model = model_match.group(1)
    
    # Create the new content
    new_content = f"""@echo off
SETLOCAL
REM Run workflow with Ollama {model}
REM Usage: {bat_file_path.name} [options] <image_directory>
REM Supports all workflow options in any order

REM Change to project root directory to ensure config files are found
cd /d "%~dp0\.."
python workflow.py --provider ollama --model {model} --output-dir Descriptions %*
ENDLOCAL
"""
    
    # Write the new content
    bat_file_path.write_text(new_content)
    print(f"  ✅ Fixed")
    return True


def main():
    """Fix all bat files in the bat/ directory."""
    print("Fixing internal bat files for flexible argument handling...")
    print("=" * 60)
    
    bat_dir = Path("bat")
    if not bat_dir.exists():
        print("❌ bat/ directory not found")
        return 1
    
    # Find all run_*.bat files
    bat_files = list(bat_dir.glob("run_*.bat"))
    
    if not bat_files:
        print("❌ No run_*.bat files found")
        return 1
    
    print(f"Found {len(bat_files)} bat files to check")
    print()
    
    fixed_count = 0
    for bat_file in sorted(bat_files):
        if fix_bat_file(bat_file):
            fixed_count += 1
    
    print()
    print("=" * 60)
    print(f"✅ Fixed {fixed_count} bat files")
    print("All internal bat files now support flexible argument handling!")
    print()
    print("Benefits:")
    print("  - Can use any workflow options (--steps, --verbose, --dry-run, etc.)")
    print("  - Arguments can be in any order")
    print("  - Matches external bat_exe/ behavior")
    print("  - Works correctly when run from bat/ directory")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())