#!/usr/bin/env python3
"""Fix external batch files to properly handle original working directory for relative paths"""

import os
import glob
import re

def fix_external_bat_file(file_path):
    """Fix a single external batch file to include original-cwd support"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Skip if already has ORIGINAL_CWD
        if 'ORIGINAL_CWD' in content:
            print(f"Skipping {file_path} - already has ORIGINAL_CWD support")
            return False
            
        # Pattern to find the cd command and the dist\idt.exe line
        cd_pattern = r'(REM Change to project root directory to ensure config files are found\r?\n)cd /d "%~dp0\.\."'
        exe_pattern = r'dist\\idt\.exe workflow ([^%]*?)%\*'
        
        # Add original CWD capture
        new_content = re.sub(
            cd_pattern,
            r'\1REM Capture the original working directory before changing directories\nSET ORIGINAL_CWD=%CD%\n\nREM Change to project root directory to ensure config files are found\ncd /d "%~dp0\.."',
            content
        )
        
        # Add --original-cwd parameter
        new_content = re.sub(
            exe_pattern,
            r'dist\\idt.exe workflow \1--original-cwd "%ORIGINAL_CWD%" %*',
            new_content
        )
        
        # Check if changes were made
        if new_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Fixed {file_path}")
            return True
        else:
            print(f"No changes needed for {file_path}")
            return False
            
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Fix all external batch files"""
    bat_exe_dir = "bat_exe"
    
    if not os.path.exists(bat_exe_dir):
        print(f"Directory {bat_exe_dir} not found")
        return
    
    # Find all .bat files in bat_exe directory
    bat_files = glob.glob(os.path.join(bat_exe_dir, "*.bat"))
    
    if not bat_files:
        print(f"No .bat files found in {bat_exe_dir}")
        return
    
    print(f"Found {len(bat_files)} batch files to process")
    
    fixed_count = 0
    for bat_file in sorted(bat_files):
        if fix_external_bat_file(bat_file):
            fixed_count += 1
    
    print(f"\nFixed {fixed_count} out of {len(bat_files)} batch files")

if __name__ == "__main__":
    main()