#!/usr/bin/env python3
import json

workspaces = [
    ('EuropeNano509_20260214.idw', 'First batch (Feb 14)'),
    ('EuropeNano5.idw', 'Second batch (Feb 15)')
]

total_all = 0
empty_all = 0

for ws_file, label in workspaces:
    try:
        path = f'/Users/kellyford/Documents/ImageDescriptionToolkit/workspaces/{ws_file}'
        with open(path) as f:
            data = json.load(f)
        
        total = 0
        empty = 0
        for item in data.get('items', {}).values():
            for desc in item.get('descriptions', []):
                if desc.get('model') == 'gpt-5-nano':
                    total += 1
                    if not desc.get('text', '').strip():
                        empty += 1
        
        total_all += total
        empty_all += empty
        success_pct = (total - empty) / total * 100 if total > 0 else 0
        print(f"{label}:")
        print(f"  Total: {total}")
        print(f"  Empty: {empty}")
        print(f"  Success: {total - empty} ({success_pct:.1f}%)")
    except Exception as e:
        print(f"{label}: Error - {e}")

print(f"\n{'='*50}")
print(f"COMBINED TOTALS:")
print(f"  Total requests: {total_all}")
print(f"  Empty responses: {empty_all}")
print(f"  Successful: {total_all - empty_all}")
print(f"  Empty rate: {empty_all/total_all*100:.1f}%")

print(f"\n{'='*50}")
print(f"OPENAI BILLING DATA:")
print(f"  Feb 14: 2 requests")
print(f"  Feb 15: 3,169 requests")
print(f"  Total logged: 3,171 requests")
print(f"\nDifference: {total_all - 3171} requests ({abs(total_all - 3171) / 3171 * 100:.1f}% {'over' if total_all > 3171 else 'under'})")
