#!/usr/bin/env python3
"""
Emergency patch script to fix the format string error in deployed idt.exe
This replaces the buggy executable with a working one using Python source.
"""

import shutil
import os
from pathlib import Path

def create_emergency_wrapper():
    """Create a Python wrapper that can replace idt.exe temporarily"""
    
    source_dir = Path(r"C:\Users\kelly\GitHub\Image-Description-Toolkit")
    target_dir = Path(r"C:\idt")
    
    # Create the wrapper script
    wrapper_content = f'''@echo off
REM Emergency wrapper for idt.exe with format string fixes
cd /d "{source_dir}"
python idt_cli.py %*
'''
    
    # Backup the original exe
    if (target_dir / "idt.exe").exists():
        shutil.copy2(target_dir / "idt.exe", target_dir / "idt_original.exe")
        print("✓ Backed up original idt.exe to idt_original.exe")
    
    # Create the wrapper batch file
    wrapper_path = target_dir / "idt_fixed.bat"
    with open(wrapper_path, 'w') as f:
        f.write(wrapper_content)
    
    print(f"✓ Created emergency wrapper: {wrapper_path}")
    print(f"✓ To use the fix, run: C:\\idt\\idt_fixed.bat instead of idt.exe")
    print(f"✓ Example: C:\\idt\\idt_fixed.bat workflow --name TestFixed C:\\path\\to\\images")

if __name__ == "__main__":
    create_emergency_wrapper()
    print("\\n🚨 EMERGENCY FIX DEPLOYED")
    print("Use 'idt_fixed.bat' instead of 'idt.exe' until rebuild is complete")