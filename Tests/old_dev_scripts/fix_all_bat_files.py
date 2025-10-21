#!/usr/bin/env python3
"""Fix all external batch files to properly handle original working directory for relative paths"""

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
            print(f"✓ {os.path.basename(file_path)} - already fixed")
            return False
            
        # Pattern to find dist\idt.exe workflow commands
        pattern = r'(dist\\idt\.exe workflow [^%]*?)%\*'
        
        # Check if this is a workflow batch file
        if 'dist\\idt.exe workflow' not in content:
            print(f"⊘ {os.path.basename(file_path)} - not a workflow batch file")
            return False
            
        # Add original CWD capture after SETLOCAL
        new_content = content.replace(
            'SETLOCAL\n',
            'SETLOCAL\n\nREM Capture the original working directory before changing directories\nSET ORIGINAL_CWD=%CD%\n'
        )
        
        # Add --original-cwd parameter
        new_content = re.sub(
            pattern,
            r'\1--original-cwd "%ORIGINAL_CWD%" %*',
            new_content
        )
        
        # Check if changes were made
        if new_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"✓ {os.path.basename(file_path)} - FIXED")
            return True
        else:
            print(f"⊘ {os.path.basename(file_path)} - no changes needed")
            return False
            
    except Exception as e:
        print(f"✗ {os.path.basename(file_path)} - ERROR: {e}")
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
    print("=" * 50)
    
    fixed_count = 0
    for bat_file in sorted(bat_files):
        if fix_external_bat_file(bat_file):
            fixed_count += 1
    
    print("=" * 50)
    print(f"Fixed {fixed_count} out of {len(bat_files)} batch files")
    
    if fixed_count > 0:
        print(f"\n✓ Ready to rebuild distribution with {fixed_count + 3} working batch files!")
    else:
        print(f"\n✓ All workflow batch files are already fixed!")

if __name__ == "__main__":
    main()