"""
Debug script to test CI environment detection.
Run this to verify that the _skip_gui_in_ci logic works correctly.
"""

import os
import sys

print("=" * 80)
print("CI ENVIRONMENT DETECTION TEST")
print("=" * 80)
print()

# Check environment variables
github_actions = os.environ.get("GITHUB_ACTIONS", "")
ci = os.environ.get("CI", "")
runner_os = os.environ.get("RUNNER_OS", "")

print("Environment Variables:")
print(f"  GITHUB_ACTIONS = '{github_actions}'")
print(f"  CI = '{ci}'")
print(f"  RUNNER_OS = '{runner_os}'")
print()

# Test the detection logic from test_entry_points.py
def _skip_gui_in_ci() -> bool:
    """Return True if running in CI environment where GUI cannot launch."""
    # GitHub sets GITHUB_ACTIONS=true; many CI environments set CI=true
    return (os.environ.get("GITHUB_ACTIONS", "").lower() == "true" 
            or os.environ.get("CI", "").lower() == "true")

skip_result = _skip_gui_in_ci()

print("Detection Logic:")
print(f"  GITHUB_ACTIONS.lower() == 'true': {github_actions.lower() == 'true'}")
print(f"  CI.lower() == 'true': {ci.lower() == 'true'}")
print(f"  _skip_gui_in_ci() returns: {skip_result}")
print()

print("=" * 80)
if skip_result:
    print("RESULT: GUI tests WOULD BE SKIPPED in this environment")
else:
    print("RESULT: GUI tests WOULD RUN in this environment")
print("=" * 80)
print()

# Also test what would happen if we set the variables
print("Testing with GITHUB_ACTIONS=true:")
os.environ["GITHUB_ACTIONS"] = "true"
print(f"  _skip_gui_in_ci() returns: {_skip_gui_in_ci()}")
print()

sys.exit(0 if skip_result else 1)
