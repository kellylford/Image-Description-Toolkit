#!/usr/bin/env python3
"""Fix output directory paths in all workflow batch files"""

import os
import glob
import re

def fix_output_dir(file_path):
    """Fix output directory path in a batch file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Skip if not a workflow batch file
        if 'idt.exe workflow' not in content:
            return False
            
        # Replace --output-dir Descriptions with --output-dir ../Descriptions
        new_content = content.replace(
            '--output-dir Descriptions',
            '--output-dir ../Descriptions'
        )
        
        # Check if changes were made
        if new_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"✓ {os.path.basename(file_path)} - Fixed output directory")
            return True
        else:
            print(f"⊘ {os.path.basename(file_path)} - No changes needed")
            return False
            
    except Exception as e:
        print(f"✗ {os.path.basename(file_path)} - ERROR: {e}")
        return False

def main():
    """Fix output directory paths in all workflow batch files"""
    bat_exe_dir = "bat_exe"
    
    if not os.path.exists(bat_exe_dir):
        print(f"Directory {bat_exe_dir} not found")
        return
    
    # Find all .bat files in bat_exe directory
    bat_files = glob.glob(os.path.join(bat_exe_dir, "*.bat"))
    
    if not bat_files:
        print(f"No .bat files found in {bat_exe_dir}")
        return
    
    print(f"Fixing output directory paths in {len(bat_files)} batch files...")
    print("=" * 60)
    
    fixed_count = 0
    for bat_file in sorted(bat_files):
        if fix_output_dir(bat_file):
            fixed_count += 1
    
    print("=" * 60)
    print(f"Fixed output directory in {fixed_count} workflow batch files")
    
    if fixed_count > 0:
        print(f"\n✓ Ready to rebuild distribution with corrected output paths!")
    else:
        print(f"\n✓ All batch files already have correct output paths!")

if __name__ == "__main__":
    main()