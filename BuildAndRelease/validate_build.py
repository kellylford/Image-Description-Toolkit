#!/usr/bin/env python3
"""
Post-Build Validation for IDT Executable

Runs quick smoke tests against the built executable to catch common issues:
- Version command works and shows build info
- Workflow command can import versioning module
- Help commands work
- Basic CLI structure is intact

Run this after builditall.bat/builditall_macos.sh to catch frozen-executable issues before deployment.
"""
import subprocess
import sys
import platform
from pathlib import Path


def run_command(cmd, description):
    """Run command and return success/failure"""
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True,
            encoding='utf-8',
            errors='replace',  # Replace invalid characters instead of crashing
            timeout=60  # Increased for torch/transformers import (can take 30-40s first time)
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)


def get_executable_path():
    """Get the path to the IDT executable based on platform"""
    base_dir = Path(__file__).parent.parent
    
    if platform.system() == 'Windows':
        return base_dir / 'dist' / 'idt.exe'
    else:  # macOS/Linux
        return base_dir / 'dist' / 'idt'


def test_executable_exists():
    """Verify the executable was actually built"""
    exe_path = get_executable_path()
    if not exe_path.exists():
        print(f"[FAIL] {exe_path.name} not found")
        print(f"   Expected at: {exe_path}")
        return False
    print(f"[PASS] Executable exists: {exe_path}")
    return True


def test_version_command():
    """Verify version command works and shows build info"""
    exe = str(get_executable_path())
    success, stdout, stderr = run_command([exe, 'version'], "version command")
    
    if not success:
        print(f"[FAIL] FAIL: {Path(exe).name} version command failed")
        print(f"   stderr: {stderr}")
        return False
    
    # Check for expected version components
    # Output format: "Image Description Toolkit X.Y.Z\nCommit: ...\nMode: ..."
    required = ['Image Description Toolkit', 'Commit:', 'Mode:']
    missing = [r for r in required if r not in stdout]
    
    if missing:
        print("[FAIL] FAIL: Version output missing required fields")
        print(f"   Missing: {', '.join(missing)}")
        print(f"   Output: {stdout[:200]}")
        return False
    
    print("[PASS] Version command works with build info")
    return True


def test_help_command():
    """Verify help command works"""
    exe = str(get_executable_path())
    success, stdout, stderr = run_command([exe, '--help'], "help command")
    
    if not success:
        print(f"[FAIL] FAIL: {Path(exe).name} --help failed")
        return False
    
    if 'workflow' not in stdout.lower():
        print("[FAIL] FAIL: Help output doesn't mention workflow")
        return False
    
    print("[PASS] Help command works")
    return True


def test_workflow_help():
    """Verify workflow command exists and imports work"""
    exe = str(get_executable_path())
    success, stdout, stderr = run_command([exe, 'workflow', '--help'], "workflow help")
    
    if not success:
        print(f"[FAIL] FAIL: {Path(exe).name} workflow --help failed")
        print(f"   This often means versioning import failed in frozen build")
        print(f"   stderr: {stderr[:500]}")
        return False
    
    print("[PASS] Workflow command works (versioning import OK)")
    return True


def test_list_commands():
    """Verify other key commands are present"""
    exe = str(get_executable_path())
    
    commands_to_test = [
        ('image_describer', 'Image describer'),
        ('convert-images', 'Image converter'),
        ('extract-frames', 'Frame extractor'),
    ]
    
    all_passed = True
    for cmd, name in commands_to_test:
        success, stdout, stderr = run_command([exe, cmd, '--help'], f"{cmd} help")
        if not success:
            print(f"[WARN] WARNING: {name} command failed")
            all_passed = False
        else:
            print(f"[PASS] {name} command works")
    
    return all_passed


def main():
    """Run all validation tests"""
    print("=" * 70)
    print("IDT BUILD VALIDATION")
    print("=" * 70)
    print()
    
    tests = [
        ("Executable exists", test_executable_exists),
        ("Version command", test_version_command),
        ("Help command", test_help_command),
        ("Workflow command", test_workflow_help),
        ("Other commands", test_list_commands),
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\nTesting: {name}")
        print("-" * 70)
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"[FAIL] EXCEPTION in {name}: {e}")
            results.append((name, False))
    
    # Summary
    print()
    print("=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, p in results if p)
    total = len(results)
    
    for name, result in results:
        status = "[PASS] PASS" if result else "[FAIL] FAIL"
        print(f"{status}: {name}")
    
    print()
    print(f"Result: {passed}/{total} tests passed")
    
    if passed == total:
        print()
        print("[SUCCESS] BUILD VALIDATION PASSED")
        print()
        return 0
    else:
        print()
        print("[FAIL] BUILD VALIDATION FAILED")
        print()
        print("Common fixes:")
        print("  - If 'versioning import' failed: Check BuildAndRelease/final_working.spec")
        print("  - If commands missing: Verify idt_cli.py includes all commands")
        print("  - If version info missing: Rebuild after fixing scripts/versioning.py")
        print()
        return 1


if __name__ == '__main__':
    sys.exit(main())
