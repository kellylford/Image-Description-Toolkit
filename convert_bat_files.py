#!/usr/bin/env python3
"""
Convert batch files from Python calls to idt.exe calls
"""
import os
import glob

def convert_batch_files():
    bat_files = glob.glob('c:/Users/kelly/GitHub/idt/bat_exe/*.bat')
    
    for bat_file in bat_files:
        print(f"Converting {bat_file}...")
        
        with open(bat_file, 'r') as f:
            content = f.read()
        
        # Replace Python workflow calls with idt.exe workflow
        content = content.replace('..\\\\venv\\\\Scripts\\\\python.exe ..\\\\workflow.py', 'idt.exe workflow')
        content = content.replace('..\\venv\\Scripts\\python.exe ..\\workflow.py', 'idt.exe workflow')
        content = content.replace('python.exe ..\\workflow.py', 'idt.exe workflow')
        content = content.replace('python ..\\workflow.py', 'idt.exe workflow')
        content = content.replace('python workflow.py', 'idt.exe workflow')
        
        # Fix output directory paths
        content = content.replace('..\\Descriptions', 'Descriptions')
        content = content.replace('..\\analysis', 'analysis')
        
        # Fix model check calls (install_vision_models.bat)
        content = content.replace('python models/check_models.py', 'idt.exe check-models')
        
        with open(bat_file, 'w') as f:
            f.write(content)
    
    print(f"Converted {len(bat_files)} batch files")

if __name__ == '__main__':
    convert_batch_files()