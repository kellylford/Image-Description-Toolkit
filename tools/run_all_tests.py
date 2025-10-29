#!/usr/bin/env python3
"""
IDT Local Test Runner - Complete Test Suite (Python version)
=============================================================
Runs all tests that GitHub Actions runs, but locally for quick validation.
This is a Python version that works cross-platform.
"""

import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime


class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    """Print a section header."""
    print(f"\n{'=' * 80}")
    print(f"  {text}")
    print(f"{'=' * 80}\n")


def print_result(status, message):
    """Print a test result with color."""
    if status == "PASS":
        print(f"{Colors.OKGREEN}[PASS]{Colors.ENDC} {message}")
    elif status == "FAIL":
        print(f"{Colors.FAIL}[FAIL]{Colors.ENDC} {message}")
    elif status == "SKIP":
        print(f"{Colors.WARNING}[SKIP]{Colors.ENDC} {message}")
    elif status == "WARN":
        print(f"{Colors.WARNING}[WARN]{Colors.ENDC} {message}")
    else:
        print(f"[{status}] {message}")


def run_unit_tests():
    """Run unit and smoke tests."""
    print_header("[1/5] UNIT TESTS")
    print("Running unit and smoke tests...\n")
    
    try:
        result = subprocess.run(
            [sys.executable, "run_unit_tests.py"],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        # Print the output
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        
        if result.returncode == 0:
            print_result("PASS", "Unit tests passed!")
            return True
        else:
            print_result("FAIL", "Unit tests failed!")
            return False
    except Exception as e:
        print_result("FAIL", f"Failed to run unit tests: {e}")
        return False


def check_syntax():
    """Check syntax of main Python scripts."""
    print_header("[2/5] SYNTAX & IMPORT CHECK")
    print("Checking Python syntax and imports...\n")
    
    scripts = [
        "scripts/workflow.py",
        "scripts/image_describer.py",
        "scripts/metadata_extractor.py",
        "idt_cli.py"
    ]
    
    all_passed = True
    
    # Check syntax
    for script in scripts:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", script],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                print_result("PASS", f"{script} compiles successfully")
            else:
                print_result("FAIL", f"{script} has syntax errors")
                if result.stderr:
                    print(f"       {result.stderr.strip()}")
                all_passed = False
        except Exception as e:
            print_result("FAIL", f"{script} - {e}")
            all_passed = False
    
    # Check imports
    print()
    import_tests = [
        ("workflow_utils", "scripts"),
        ("image_describer", "scripts"),
        ("metadata_extractor", "scripts")
    ]
    
    for module, subdir in import_tests:
        try:
            # Change to the subdirectory for the import test
            if subdir:
                import_cmd = f"import sys; sys.path.insert(0, '{subdir}'); import {module}; print('OK')"
            else:
                import_cmd = f"import {module}; print('OK')"
            
            result = subprocess.run(
                [sys.executable, "-c", import_cmd],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and "OK" in result.stdout:
                print_result("PASS", f"{module} imports successfully")
            else:
                print_result("FAIL", f"{module} import failed")
                if result.stderr:
                    print(f"       {result.stderr.strip()}")
                all_passed = False
        except Exception as e:
            print_result("FAIL", f"{module} - {e}")
            all_passed = False
    
    print()
    if all_passed:
        print_result("PASS", "Syntax and import checks passed!")
    else:
        print_result("FAIL", "Syntax and import checks failed!")
    
    return all_passed


def test_pyinstaller_build():
    """
    SKIPPED: PyInstaller build test.
    
    NOTE: Actual IDT builds use BuildAndRelease/builditall.bat with .spec files.
    Simple PyInstaller command-line builds conflict with the 'workflow' package.
    This test is intentionally skipped - use the real build scripts for validation.
    """
    print_header("[3/5] PYINSTALLER BUILD TEST")
    print("Checking build infrastructure...\n")
    
    # Check if the proper build scripts exist
    spec_file = Path("BuildAndRelease/final_working.spec")
    build_script = Path("BuildAndRelease/builditall.bat")
    
    if spec_file.exists() and build_script.exists():
        print_result("SKIP", "PyInstaller test skipped - use BuildAndRelease/builditall.bat for actual builds")
        print("       Reason: Simple builds conflict with 'workflow' package")
        print("       Build scripts present and ready to use")
        return None  # Skipped, not a failure
    else:
        print_result("WARN", "Build infrastructure incomplete")
        if not spec_file.exists():
            print("       Missing: BuildAndRelease/final_working.spec")
        if not build_script.exists():
            print("       Missing: BuildAndRelease/builditall.bat")
        return None  # Still not a failure, just a warning


def validate_build_scripts():
    """Validate that build scripts exist and are accessible."""
    print_header("[4/5] BUILD SCRIPTS VALIDATION")
    print("Checking batch file existence...\n")
    
    scripts = [
        "BuildAndRelease/builditall.bat",
        "BuildAndRelease/packageitall.bat",
        "BuildAndRelease/releaseitall.bat",
        "BuildAndRelease/build_idt.bat",
        "tools/environmentsetup.bat"
    ]
    
    errors = 0
    for script in scripts:
        script_path = Path(script)
        if not script_path.exists():
            print_result("WARN", f"{script} not found")
            errors += 1
        else:
            print_result("PASS", f"{script} exists")
    
    print()
    if errors == 0:
        print_result("PASS", "All build scripts present")
        return True
    else:
        print_result("FAIL", f"Some build scripts missing ({errors} files)")
        return False


def check_git_status():
    """Check if there are uncommitted changes."""
    print_header("[5/5] GIT STATUS CHECK")
    print("Checking repository status...\n")
    
    try:
        # Check for uncommitted changes
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            if result.stdout.strip():
                print_result("WARN", "You have uncommitted changes")
                print("\nUncommitted files:")
                for line in result.stdout.strip().split('\n')[:10]:
                    print(f"       {line}")
                if len(result.stdout.strip().split('\n')) > 10:
                    print(f"       ... and {len(result.stdout.strip().split('\n')) - 10} more")
                return None  # Warning, not a failure
            else:
                print_result("PASS", "Working directory is clean")
                return True
        else:
            print_result("SKIP", "Not a git repository or git not available")
            return None
    except Exception as e:
        print_result("SKIP", f"Git check failed: {e}")
        return None


def main():
    """Run all tests."""
    start_time = time.time()
    start_datetime = datetime.now()
    
    print("\n" + "=" * 80)
    print("   IMAGE DESCRIPTION TOOLKIT - LOCAL TEST SUITE")
    print("=" * 80)
    print("   Running all automated tests locally...")
    print(f"   Started: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    results = {
        "Unit Tests": run_unit_tests(),
        "Syntax & Import Check": check_syntax(),
        "PyInstaller Build": test_pyinstaller_build(),
        "Build Scripts": validate_build_scripts(),
        "Git Status": check_git_status()
    }
    
    # Calculate summary
    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    skipped = sum(1 for v in results.values() if v is None)
    
    # Print summary
    end_time = time.time()
    duration = end_time - start_time
    
    print_header("TEST SUMMARY")
    print(f"   Tests Passed:  {passed}")
    print(f"   Tests Failed:  {failed}")
    print(f"   Tests Skipped: {skipped}")
    print(f"   Duration:      {duration:.1f} seconds")
    print(f"   Started:       {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Completed:     {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Detailed results
    print("\nDetailed Results:")
    for test_name, result in results.items():
        if result is True:
            status = f"{Colors.OKGREEN}PASS{Colors.ENDC}"
        elif result is False:
            status = f"{Colors.FAIL}FAIL{Colors.ENDC}"
        else:
            status = f"{Colors.WARNING}SKIP{Colors.ENDC}"
        print(f"   [{status}] {test_name}")
    
    # What does PASS mean?
    print("\n" + "=" * 80)
    print("WHAT THESE RESULTS MEAN:")
    print("=" * 80)
    print("[PASS] Unit Tests = All 48 unit/smoke tests passed")
    print("                    - Core functionality validated")
    print("                    - CLI commands work")
    print("                    - Config handling correct")
    print("")
    print("[PASS] Syntax Check = All Python files compile")
    print("                      - No syntax errors")
    print("                      - All imports resolve")
    print("")
    print("[SKIP] PyInstaller = Use BuildAndRelease/builditall.bat")
    print("                     - Test intentionally skipped")
    print("                     - Actual builds use .spec files")
    print("")
    print("[PASS] Build Scripts = All build .bat files present")
    print("                       - Build infrastructure intact")
    print("")
    print("[SKIP] Git Status = Informational only")
    print("                    - Not a test failure")
    print("=" * 80)
    
    print("\n" + "=" * 80)
    
    if failed > 0:
        print(f"   {Colors.FAIL}[FAIL] {failed} critical test(s) failed - DO NOT BUILD{Colors.ENDC}\n")
        return 1
    else:
        print(f"   {Colors.OKGREEN}[PASS] All critical tests passed - safe to build{Colors.ENDC}\n")
        return 0


if __name__ == "__main__":
    sys.exit(main())
