#!/usr/bin/env python3
"""Test to reproduce the exact format string error from the logs"""

# Simulate problematic content that could cause format string errors
test_cases = [
    ("Simple case", "Madison, WI", "A beautiful sunset"),
    ("Braces in description", "Madison, WI", "This shows {something} nice"),
    ("Braces in location", "Madison{test}, WI", "A beautiful sunset"),
    ("Percentage in description", "Madison, WI", "This shows 50% coverage"),
    ("Percentage in location", "Madison, WI 50%", "A beautiful sunset"),
    ("Format specifiers", "Madison, WI", "Value is {:.2f} something"),
    ("Empty braces", "Madison, WI", "This has {} empty braces"),
    ("Nested braces", "Madison, WI", "This has {{nested}} braces"),
]

for name, location_prefix, description in test_cases:
    print(f"\nTesting: {name}")
    print(f"Location: '{location_prefix}'")
    print(f"Description: '{description}'")
    
    # Test old way (f-string)
    try:
        old_result = f"{location_prefix}: {description}"
        print(f"  OLD (f-string): SUCCESS - {old_result}")
    except Exception as e:
        print(f"  OLD (f-string): FAILED - {e}")
    
    # Test new way (concatenation)
    try:
        new_result = location_prefix + ": " + description
        print(f"  NEW (concat): SUCCESS - {new_result}")
    except Exception as e:
        print(f"  NEW (concat): FAILED - {e}")