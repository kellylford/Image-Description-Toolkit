#!/usr/bin/env python3
"""Quick test to verify the format string fix"""

# Test the problematic scenario
location_prefix = "Madison, WI Jan 1, 2025"
description_with_braces = "This image shows a {beautiful} sunset over the lake"
description_safe = "This image shows a beautiful sunset over the lake"

print("Testing format string issue...")

# The old way that would fail
try:
    old_way = f"{location_prefix}: {description_with_braces}"
    print("OLD WAY (f-string): FAILED - should have raised an error!")
except Exception as e:
    print(f"OLD WAY (f-string): CORRECTLY FAILED - {e}")

# The new way that should work
try:
    new_way = location_prefix + ": " + description_with_braces
    print(f"NEW WAY (concatenation): SUCCESS - {new_way}")
except Exception as e:
    print(f"NEW WAY (concatenation): FAILED - {e}")

# Test with safe description
try:
    safe_way = f"{location_prefix}: {description_safe}"
    print(f"SAFE DESCRIPTION (f-string): SUCCESS - {safe_way}")
except Exception as e:
    print(f"SAFE DESCRIPTION (f-string): FAILED - {e}")