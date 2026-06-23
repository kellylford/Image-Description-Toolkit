#!/usr/bin/env python3
"""
Post-Build Validation for IDT Executable (v4.5 CLI)

Smoke-tests the built executable to catch frozen-executable import failures
before deployment. Tests the new cli/main.py command surface.

Run from the project root after builditall:
    python3 BuildAndRelease/validate_build.py
"""
import subprocess
import sys
import platform
from pathlib import Path


def run_command(cmd, description):
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=60,
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)


def get_executable_path():
    project_root = Path(__file__).parent.parent
    if platform.system() == 'Windows':
        return project_root / 'idt' / 'dist' / 'idt.exe'
    else:
        return project_root / 'idt' / 'dist' / 'idt'


def test_executable_exists():
    exe_path = get_executable_path()
    if not exe_path.exists():
        print(f"[FAIL] {exe_path.name} not found at: {exe_path}")
        return False
    size_mb = exe_path.stat().st_size / 1_048_576
    print(f"[PASS] Executable exists: {exe_path}  ({size_mb:.1f} MB)")
    return True


def test_help_command():
    exe = str(get_executable_path())
    success, stdout, stderr = run_command([exe, '--help'], "help")
    if not success:
        print(f"[FAIL] --help failed\n   stderr: {stderr[:300]}")
        return False
    if 'describe' not in stdout.lower():
        print("[FAIL] --help output doesn't mention 'describe' — wrong exe or broken import")
        print(f"   Output: {stdout[:300]}")
        return False
    print("[PASS] --help works and mentions 'describe'")
    return True


def test_describe_help():
    exe = str(get_executable_path())
    success, stdout, stderr = run_command([exe, 'describe', '--help'], "describe --help")
    if not success:
        print(f"[FAIL] describe --help failed — likely a broken import in idt_core\n   stderr: {stderr[:500]}")
        return False
    if '--provider' not in stdout:
        print("[FAIL] describe --help missing expected flags")
        return False
    print("[PASS] describe command works (idt_core imports OK)")
    return True


def test_key_commands():
    exe = str(get_executable_path())
    commands = [
        ('export',   '--help', 'export'),
        ('status',   '--help', 'status'),
        ('video',    '--help', 'video'),
        ('embed',    '--help', 'embed'),
        ('guideme',  '--help', 'guideme'),
    ]
    all_passed = True
    for cmd, flag, name in commands:
        success, stdout, stderr = run_command([exe, cmd, flag], f"{cmd} {flag}")
        if not success:
            print(f"[WARN] {name} command failed")
            all_passed = False
        else:
            print(f"[PASS] {name} command works")
    return all_passed


def main():
    print("=" * 70)
    print("IDT BUILD VALIDATION (v4.5)")
    print("=" * 70)
    print()

    tests = [
        ("Executable exists", test_executable_exists),
        ("Help command",      test_help_command),
        ("Describe command",  test_describe_help),
        ("Other commands",    test_key_commands),
    ]

    results = []
    for name, fn in tests:
        print(f"\nTesting: {name}")
        print("-" * 70)
        try:
            results.append((name, fn()))
        except Exception as e:
            print(f"[FAIL] EXCEPTION: {e}")
            results.append((name, False))

    print()
    print("=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)
    passed = sum(1 for _, p in results if p)
    for name, result in results:
        print(f"{'[PASS]' if result else '[FAIL]'} {name}")
    print()
    print(f"Result: {passed}/{len(results)} tests passed")
    print()

    if passed == len(results):
        print("[SUCCESS] BUILD VALIDATION PASSED")
        return 0
    else:
        print("[FAIL] BUILD VALIDATION FAILED")
        print()
        print("Common fixes:")
        print("  - Import error: check idt.spec hiddenimports for missing idt_core.* modules")
        print("  - Wrong exe:    confirm idt/dist/idt.exe was rebuilt with --clean")
        return 1


if __name__ == '__main__':
    sys.exit(main())
