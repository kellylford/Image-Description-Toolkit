#!/usr/bin/env python3
"""
Test runner for Image Description Toolkit.

Usage:
    python run_tests.py              # Run all tests
    python run_tests.py --coverage   # Run with coverage report
    python run_tests.py --quick      # Run unit tests only
    python run_tests.py --verbose    # Verbose output
"""

import sys
import subprocess
from pathlib import Path

def main():
    """Run pytest with appropriate options."""
    args = sys.argv[1:]
    
    # Default pytest args
    pytest_args = ["pytest", "pytest_tests"]
    
    # Parse options
    if "--coverage" in args:
        pytest_args.extend(["--cov=scripts", "--cov-report=html", "--cov-report=term"])
        args.remove("--coverage")
    
    if "--quick" in args:
        pytest_args.extend(["-m", "not slow", "pytest_tests/unit"])
        args.remove("--quick")
    
    if "--verbose" in args or "-v" in args:
        pytest_args.append("-v")
        if "--verbose" in args:
            args.remove("--verbose")
        if "-v" in args:
            args.remove("-v")
    
    # Add any remaining args
    pytest_args.extend(args)
    
    # Run pytest
    print(f"Running: {' '.join(pytest_args)}")
    result = subprocess.run(pytest_args)
    
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
