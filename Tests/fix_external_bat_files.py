#!/usr/bin/env python3
"""
Script to update external bat files to use correct dist\idt.exe path
"""

import os
import re
import glob

def fix_external_bat_files():
    """Update all external bat files to use dist\idt.exe instead of idt.exe"""
    
    # Get all .bat files in bat_exe directory
    bat_files = glob.glob("bat_exe/*.bat")
    
    updated_count = 0
    
    for bat_file in bat_files:
        print(f"Processing: {bat_file}")
        
        try:
            # Read current content
            with open(bat_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Replace idt.exe with dist\idt.exe
            if 'idt.exe workflow' in content and 'dist\\idt.exe workflow' not in content:
                new_content = content.replace('idt.exe workflow', 'dist\\idt.exe workflow')
                
                # Write updated content
                with open(bat_file, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                print(f"  ✅ Updated: {bat_file}")
                updated_count += 1
            else:
                print(f"  ⏭️  No changes needed: {bat_file}")
                
        except Exception as e:
            print(f"  ❌ Error processing {bat_file}: {e}")
    
    print(f"\n📊 Summary: Updated {updated_count} external bat files")

if __name__ == "__main__":
    fix_external_bat_files()