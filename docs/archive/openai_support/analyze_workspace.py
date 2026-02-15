#!/usr/bin/env python3
"""Analyze workspace file for failed/empty descriptions"""
import json
import sys
from collections import Counter
from pathlib import Path

if len(sys.argv) < 2:
    print("Usage: python analyze_workspace.py <workspace_file.idw>")
    sys.exit(1)

workspace_file = sys.argv[1]

with open(workspace_file, 'r') as f:
    workspace = json.load(f)

total_items = len(workspace['items'])
items_with_descriptions = 0
items_with_empty_descriptions = 0
items_without_descriptions = 0

empty_desc_items = []
no_desc_items = []

for file_path, item in workspace['items'].items():
    descriptions = item.get('descriptions', [])
    
    if not descriptions:
        items_without_descriptions += 1
        no_desc_items.append(file_path)
    elif descriptions[0].get('text', '').strip() == '':
        items_with_empty_descriptions += 1
        empty_desc_items.append(file_path)
    else:
        items_with_descriptions += 1

# Analyze file types for empty descriptions
empty_file_types = Counter()
for path in empty_desc_items:
    ext = Path(path).suffix.lower()
    empty_file_types[ext] += 1

# Analyze file types for no descriptions
no_desc_file_types = Counter()
for path in no_desc_items:
    ext = Path(path).suffix.lower()
    no_desc_file_types[ext] += 1

print(f"=== WORKSPACE ANALYSIS ===")
print(f"\nTotal items: {total_items}")
print(f"Successfully described: {items_with_descriptions} ({items_with_descriptions*100//total_items}%)")
print(f"Empty descriptions: {items_with_empty_descriptions} ({items_with_empty_descriptions*100//total_items}%)")
print(f"No descriptions: {items_without_descriptions} ({items_without_descriptions*100//total_items}%)")
print(f"\nTotal failed: {items_with_empty_descriptions + items_without_descriptions} ({(items_with_empty_descriptions + items_without_descriptions)*100//total_items}%)")

print(f"\n=== EMPTY DESCRIPTION FILE TYPES ===")
for ext, count in empty_file_types.most_common():
    print(f"  {ext or 'no extension'}: {count}")

print(f"\n=== NO DESCRIPTION FILE TYPES ===")
for ext, count in no_desc_file_types.most_common():
    print(f"  {ext or 'no extension'}: {count}")

# Show sample filenames
print(f"\n=== SAMPLE EMPTY DESCRIPTION FILES (first 15) ===")
for path in empty_desc_items[:15]:
    filename = Path(path).name
    print(f"  {filename}")

print(f"\n=== SAMPLE NO DESCRIPTION FILES (first 15) ===")
for path in no_desc_items[:15]:
    filename = Path(path).name
    print(f"  {filename}")
