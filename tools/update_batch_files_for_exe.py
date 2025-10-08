#!/usr/bin/env python3
"""
Update batch files to use executable instead of Python
Run this ONCE after building the executable to update all batch files.

This script:
1. Updates all run_* batch files in bat/ directory
2. Changes: python workflow.py → ImageDescriptionToolkit.exe workflow
3. Creates backups in bat/backup_python/ for safety
"""

import re
import shutil
from pathlib import Path
from datetime import datetime


def main():
    """Update all batch files for executable distribution."""
    
    print("\n" + "=" * 80)
    print("Batch File Updater for Executable Distribution")
    print("=" * 80 + "\n")
    
    # Get directories
    root_dir = Path(__file__).parent.parent
    bat_dir = root_dir / 'bat'
    backup_dir = bat_dir / 'backup_python'
    
    # Check bat directory exists
    if not bat_dir.exists():
        print(f"ERROR: bat directory not found: {bat_dir}")
        return 1
    
    # Create backup directory
    backup_dir.mkdir(exist_ok=True)
    print(f"Backup directory: {backup_dir}")
    print()
    
    # Find all .bat files
    bat_files = list(bat_dir.glob('run_*.bat'))
    
    if not bat_files:
        print("WARNING: No run_*.bat files found!")
        return 1
    
    print(f"Found {len(bat_files)} batch files to update\n")
    
    # Process each file
    updated = []
    skipped = []
    errors = []
    
    for bat_file in sorted(bat_files):
        try:
            # Read original content
            original = bat_file.read_text(encoding='utf-8')
            
            # Check if already updated
            if 'ImageDescriptionToolkit.exe workflow' in original:
                print(f"⏭️  SKIP: {bat_file.name} (already updated)")
                skipped.append(bat_file.name)
                continue
            
            # Check if contains python workflow.py
            if 'python workflow.py' not in original and 'python ..\\workflow.py' not in original:
                print(f"⏭️  SKIP: {bat_file.name} (doesn't call workflow.py)")
                skipped.append(bat_file.name)
                continue
            
            # Create backup
            backup_file = backup_dir / bat_file.name
            shutil.copy2(bat_file, backup_file)
            
            # Update content
            updated_content = original
            
            # Replace: python workflow.py
            updated_content = re.sub(
                r'python\s+workflow\.py',
                r'ImageDescriptionToolkit.exe workflow',
                updated_content
            )
            
            # Replace: python ..\workflow.py (if called from subdirectory)
            updated_content = re.sub(
                r'python\s+\.\.\\workflow\.py',
                r'..\ImageDescriptionToolkit.exe workflow',
                updated_content
            )
            
            # Write updated content
            if updated_content != original:
                bat_file.write_text(updated_content, encoding='utf-8')
                print(f"✅ UPDATE: {bat_file.name}")
                updated.append(bat_file.name)
            else:
                print(f"⏭️  SKIP: {bat_file.name} (no changes needed)")
                skipped.append(bat_file.name)
        
        except Exception as e:
            print(f"❌ ERROR: {bat_file.name} - {e}")
            errors.append((bat_file.name, str(e)))
    
    # Print summary
    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80 + "\n")
    
    print(f"✅ Updated: {len(updated)} files")
    if updated:
        for name in updated:
            print(f"   - {name}")
    print()
    
    print(f"⏭️  Skipped: {len(skipped)} files")
    if skipped and len(skipped) <= 10:
        for name in skipped:
            print(f"   - {name}")
    print()
    
    if errors:
        print(f"❌ Errors: {len(errors)} files")
        for name, error in errors:
            print(f"   - {name}: {error}")
        print()
    
    print(f"📁 Backups saved to: {backup_dir}")
    print()
    
    # Create restore script
    create_restore_script(backup_dir)
    
    if updated:
        print("✅ Batch files successfully updated for executable distribution!")
        print()
        print("Next steps:")
        print("  1. Test a few batch files with the executable")
        print("  2. If issues occur, run: bat\\backup_python\\restore_python.bat")
        print("  3. Create distribution package with create_distribution.bat")
    else:
        print("⚠️  No files were updated. They may already be configured for exe.")
    
    print()
    return 0 if not errors else 1


def create_restore_script(backup_dir):
    """Create a script to restore original Python-based batch files."""
    
    restore_script = backup_dir / 'restore_python.bat'
    
    script_content = f'''@echo off
REM Restore Python-based batch files from backup
REM Created: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

echo.
echo Restoring Python-based batch files from backup...
echo.

set "backup_dir=%~dp0"
set "bat_dir=%~dp0.."

REM Count files
set count=0
for %%f in ("%backup_dir%\\*.bat") do (
    copy /y "%%f" "%bat_dir%\\%%~nxf" >nul
    set /a count+=1
    echo Restored: %%~nxf
)

echo.
echo Restored %count% batch files
echo.
echo Batch files now use Python instead of executable.
echo.
pause
'''
    
    restore_script.write_text(script_content, encoding='utf-8')
    print(f"📝 Created restore script: {restore_script}")


if __name__ == '__main__':
    import sys
    sys.exit(main())
