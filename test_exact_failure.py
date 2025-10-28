#!/usr/bin/env python3
"""Test the exact scenario that was failing"""

# Test the problematic f-string that was causing the issue
description_with_problematic_content = "This shows {something} with formatting {:.2f} and {} empty braces"

print("Testing the exact failing scenario...")

# The old way that would fail (what was in the code)
try:
    old_way = f"Description: {description_with_problematic_content}\n"
    print("OLD WAY: This shouldn't work but somehow did...")
    print(f"Result: {old_way}")
except Exception as e:
    print(f"OLD WAY: CORRECTLY FAILED - {e}")

# The new way that should work
try:
    new_way = "Description: " + description_with_problematic_content + "\n"
    print(f"NEW WAY: SUCCESS - {new_way}")
except Exception as e:
    print(f"NEW WAY: FAILED - {e}")

# Let's test something that would definitely fail
problematic_text = "Temperature is {temperature:.2f}°C"
print(f"\nTesting definitely problematic content: '{problematic_text}'")

# This should fail because {temperature:.2f} is a format specifier without the value
try:
    # Simulating the actual error - trying to format a string that contains unresolved format specifiers
    formatted = problematic_text.format()
    print(f"Format method: {formatted}")
except Exception as e:
    print(f"Format method: FAILED as expected - {e}")

# But in an f-string it might try to interpret it
try:
    f_string = f"Description: {problematic_text}\n"
    print(f"F-string: {f_string}")
except Exception as e:
    print(f"F-string: FAILED - {e}")

# Concatenation should always work
try:
    concat = "Description: " + problematic_text + "\n"
    print(f"Concatenation: {concat}")
except Exception as e:
    print(f"Concatenation: FAILED - {e}")