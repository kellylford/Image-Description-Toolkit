"""Remove Unicode emojis from geotag_workflow.py"""
import re

with open('geotag_workflow.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace emojis with plain text
replacements = [
    ('\U0001f4cb', ''),  # clipboard emoji
    ('\u26a0\ufe0f', 'WARNING:'),  # warning emoji
    ('\u2705', '[OK]'),  # checkmark emoji
    ('\u274c', 'ERROR:'),  # X emoji
    ('\U0001f4f7', ''),  # camera emoji
    ('\U0001f50d', ''),  # magnifying glass emoji
]

for old, new in replacements:
    content = content.replace(old, new)

with open('geotag_workflow.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed all Unicode emojis')
