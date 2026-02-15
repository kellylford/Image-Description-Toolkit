#!/usr/bin/env python3
import json
from collections import defaultdict, Counter
import os

workspaces = [
    ('EuropeNano509_20260214.idw', 'First batch (Feb 14)'),
    ('EuropeNano5.idw', 'Second batch (Feb 15)')
]

# Track which images failed in both batches
failed_images = defaultdict(int)  # filename -> times it failed
succeeded_images = set()
failed_by_type = Counter()
succeeded_by_type = Counter()
failed_by_size = []
succeeded_by_size = []

print("ANALYZING EMPTY RESPONSE PATTERNS")
print("=" * 70)

for ws_file, label in workspaces:
    try:
        path = f'/Users/kellyford/Documents/ImageDescriptionToolkit/workspaces/{ws_file}'
        with open(path) as f:
            data = json.load(f)
        
        print(f"\n{label}:")
        
        for filename, item in data.get('items', {}).items():
            file_ext = os.path.splitext(filename)[1].lower()
            file_size = item.get('file_size', 0)
            
            for desc in item.get('descriptions', []):
                if desc.get('model') == 'gpt-5-nano':
                    is_empty = not desc.get('text', '').strip()
                    
                    if is_empty:
                        failed_images[filename] += 1
                        failed_by_type[file_ext] += 1
                        if file_size:
                            failed_by_size.append(file_size)
                    else:
                        succeeded_images.add(filename)
                        succeeded_by_type[file_ext] += 1
                        if file_size:
                            succeeded_by_size.append(file_size)
        
    except Exception as e:
        print(f"  Error: {e}")

print(f"\n{'='*70}")
print("PATTERN ANALYSIS:")
print(f"{'='*70}")

# Check if same images fail multiple times
repeated_failures = {k: v for k, v in failed_images.items() if v > 1}
if repeated_failures:
    print(f"\n❌ Images that failed in BOTH batches: {len(repeated_failures)}")
    for img, count in sorted(repeated_failures.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {img}: failed {count} times")
else:
    print(f"\n✅ No images failed in both batches")

# Check if failed images ever succeeded
failed_then_succeeded = set(failed_images.keys()) & succeeded_images
if failed_then_succeeded:
    print(f"\n⚠️  Images that failed once but succeeded another time: {len(failed_then_succeeded)}")
    for img in list(failed_then_succeeded)[:5]:
        print(f"  {img}")
else:
    print(f"\n❌ No images both failed and succeeded (different attempts)")

# File type distribution
print(f"\n{'='*70}")
print("BY FILE TYPE:")
print(f"{'='*70}")
for ext in sorted(set(failed_by_type.keys()) | set(succeeded_by_type.keys())):
    failed = failed_by_type[ext]
    succeeded = succeeded_by_type[ext]
    total = failed + succeeded
    fail_rate = failed / total * 100 if total > 0 else 0
    print(f"  {ext:6s}: {failed:4d} failed / {total:4d} total = {fail_rate:5.1f}% failure rate")

# File size analysis
if failed_by_size and succeeded_by_size:
    avg_failed = sum(failed_by_size) / len(failed_by_size)
    avg_succeeded = sum(succeeded_by_size) / len(succeeded_by_size)
    print(f"\n{'='*70}")
    print("BY FILE SIZE:")
    print(f"{'='*70}")
    print(f"  Average size of failed images:     {avg_failed/1024/1024:.2f} MB")
    print(f"  Average size of succeeded images:  {avg_succeeded/1024/1024:.2f} MB")
    print(f"  Difference: {abs(avg_failed - avg_succeeded)/1024/1024:.2f} MB")

print(f"\n{'='*70}")
print("CONCLUSION:")
print(f"{'='*70}")
if repeated_failures:
    print("❌ SAME images fail repeatedly (content-specific)")
elif failed_then_succeeded:
    print("⚠️  Random/intermittent failures (not content-specific)")
else:
    print("? Unclear pattern - need more data")
