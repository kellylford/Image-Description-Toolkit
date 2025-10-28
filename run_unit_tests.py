#!/usr/bin/env python3
"""
Simple test runner that bypasses pytest's buffer issues with Python 3.13.
Runs all unit tests and reports results in a GitHub Actions-friendly format.
"""

import sys
import importlib.util
from pathlib import Path
import traceback

# Add scripts directory to Python path for imports
scripts_dir = Path(__file__).parent / "scripts"
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))


def load_test_module(test_file):
    """Load a test module from a file path."""
    spec = importlib.util.spec_from_file_location("test_module", test_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_tests_in_module(module, module_name):
    """Run all test functions/classes in a module."""
    passed = 0
    failed = 0
    failures = []
    
    # Find all test classes
    for name in dir(module):
        obj = getattr(module, name)
        if isinstance(obj, type) and name.startswith('Test'):
            # Found a test class
            print(f"\n  Testing {module_name}::{name}")
            instance = obj()
            
            # Run all test methods
            for method_name in dir(instance):
                if method_name.startswith('test_'):
                    test_name = f"{module_name}::{name}::{method_name}"
                    try:
                        method = getattr(instance, method_name)
                        method()
                        print(f"    [PASS] {method_name}")
                        passed += 1
                    except Exception as e:
                        print(f"    [FAIL] {method_name}")
                        print(f"      {type(e).__name__}: {e}")
                        failed += 1
                        failures.append({
                            'test': test_name,
                            'error': str(e),
                            'traceback': traceback.format_exc()
                        })
    
    # Also check for standalone test functions
    for name in dir(module):
        obj = getattr(module, name)
        if callable(obj) and name.startswith('test_') and not isinstance(obj, type):
            test_name = f"{module_name}::{name}"
            try:
                obj()
                print(f"  [PASS] {name}")
                passed += 1
            except Exception as e:
                print(f"  [FAIL] {name}")
                print(f"    {type(e).__name__}: {e}")
                failed += 1
                failures.append({
                    'test': test_name,
                    'error': str(e),
                    'traceback': traceback.format_exc()
                })
    
    return passed, failed, failures


def main():
    """Run all unit tests."""
    print("=" * 70)
    print("Running Unit Tests (Python 3.13 compatible runner)")
    print("=" * 70)
    
    # Find all test files
    test_dir = Path(__file__).parent / "pytest_tests" / "unit"
    test_files = list(test_dir.glob("test_*.py"))
    
    if not test_files:
        print(f"\n[FAIL] No test files found in {test_dir}")
        return 1
    
    print(f"\nFound {len(test_files)} test file(s)")
    
    total_passed = 0
    total_failed = 0
    all_failures = []
    
    for test_file in sorted(test_files):
        print(f"\n{'=' * 70}")
        print(f"Running: {test_file.name}")
        print(f"{'=' * 70}")
        
        try:
            module = load_test_module(test_file)
            passed, failed, failures = run_tests_in_module(module, test_file.stem)
            total_passed += passed
            total_failed += failed
            all_failures.extend(failures)
        except Exception as e:
            print(f"\n[FAIL] Failed to load test module: {e}")
            traceback.print_exc()
            total_failed += 1
    
    # Summary
    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")
    print(f"[PASS] Passed: {total_passed}")
    print(f"[FAIL] Failed: {total_failed}")
    
    if all_failures:
        print(f"\n{'=' * 70}")
        print("FAILURES")
        print(f"{'=' * 70}")
        for failure in all_failures:
            print(f"\n{failure['test']}")
            print(f"  Error: {failure['error']}")
            if '--verbose' in sys.argv:
                print(f"\n{failure['traceback']}")
    
    # Exit with appropriate code
    return 0 if total_failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
