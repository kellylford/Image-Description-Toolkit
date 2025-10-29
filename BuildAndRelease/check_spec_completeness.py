#!/usr/bin/env python3
"""
PyInstaller Spec File Completeness Check

Verifies that all Python modules in scripts/ are properly included in the
PyInstaller spec file (final_working.spec). This catches the common mistake
of adding a new module but forgetting to update the spec file.

Run this before building to ensure frozen executable won't have missing imports.
"""
import sys
from pathlib import Path


def find_python_modules(directory):
    """Find all .py files in a directory"""
    py_files = list(directory.glob('*.py'))
    # Return stems (filename without .py)
    return {f.stem for f in py_files if f.stem != '__init__'}


def check_spec_file(spec_path, modules_to_check, directory_name):
    """Check if all modules are referenced in spec file"""
    spec_text = spec_path.read_text(encoding='utf-8')
    
    missing_from_datas = []
    missing_from_hiddenimports = []
    
    for module in sorted(modules_to_check):
        # Check datas section (looks for pattern like: ('../scripts/module.py', 'scripts'))
        if f"/{module}.py" not in spec_text:
            missing_from_datas.append(module)
        
        # Check hiddenimports section (looks for pattern like: 'scripts.module')
        if f"{directory_name}.{module}" not in spec_text:
            missing_from_hiddenimports.append(module)
    
    return missing_from_datas, missing_from_hiddenimports


def main():
    """Run completeness check"""
    print("=" * 70)
    print("PYINSTALLER SPEC FILE COMPLETENESS CHECK")
    print("=" * 70)
    print()
    
    # Find spec file and scripts directory
    build_dir = Path(__file__).parent
    spec_file = build_dir / 'final_working.spec'
    scripts_dir = build_dir.parent / 'scripts'
    
    if not spec_file.exists():
        print(f"[FAIL] ERROR: Spec file not found at {spec_file}")
        return 1
    
    if not scripts_dir.exists():
        print(f"[FAIL] ERROR: Scripts directory not found at {scripts_dir}")
        return 1
    
    print(f"Spec file: {spec_file.name}")
    print(f"Checking: {scripts_dir}")
    print()
    
    # Find all Python modules
    modules = find_python_modules(scripts_dir)
    print(f"Found {len(modules)} Python modules in scripts/")
    
    # Check spec file
    missing_datas, missing_imports = check_spec_file(spec_file, modules, 'scripts')
    
    # Report results
    if not missing_datas and not missing_imports:
        print()
        print("[SUCCESS] ALL MODULES ARE PROPERLY INCLUDED IN SPEC FILE")
        print()
        return 0
    
    # Show what's missing
    print()
    print("[FAIL] MISSING MODULES DETECTED")
    print()
    
    if missing_datas:
        print("Missing from 'datas' section:")
        print("-" * 70)
        print("Add these lines to the datas list in final_working.spec:")
        print()
        for module in sorted(missing_datas):
            print(f"        ('../scripts/{module}.py', 'scripts'),")
        print()
    
    if missing_imports:
        print("Missing from 'hiddenimports' section:")
        print("-" * 70)
        print("Add these lines to the hiddenimports list in final_working.spec:")
        print()
        for module in sorted(missing_imports):
            print(f"        'scripts.{module}',")
        print()
    
    print("=" * 70)
    print("WHY THIS MATTERS:")
    print("-" * 70)
    print("Missing modules will cause import errors in the frozen executable.")
    print("The executable will build successfully but fail at runtime with:")
    print("  ModuleNotFoundError or ImportError")
    print()
    print("Fix the spec file before building to avoid deployment issues.")
    print("=" * 70)
    print()
    
    return 1


if __name__ == '__main__':
    sys.exit(main())
