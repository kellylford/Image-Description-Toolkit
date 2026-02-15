#!/usr/bin/env python3
import json

for ws_file, label in [('EuropeNano509_20260214.idw', 'Batch 1'), ('EuropeNano5.idw', 'Batch 2')]:
    path = f'/Users/kellyford/Documents/ImageDescriptionToolkit/workspaces/{ws_file}'
    with open(path) as f:
        data = json.load(f)
    
    # Collect all descriptions with timestamps
    all_descs = []
    for item in data.get('items', {}).values():
        for desc in item.get('descriptions', []):
            if desc.get('model') == 'gpt-5-nano':
                all_descs.append({
                    'created': desc.get('created', ''),
                    'is_empty': not desc.get('text', '').strip()
                })
    
    # Sort by timestamp
    all_descs.sort(key=lambda x: x['created'])
    
    print(f"\n{label}:")
    print(f"  Total: {len(all_descs)} descriptions")
    
    # Find first empty
    first_empty_idx = next((i for i, d in enumerate(all_descs) if d['is_empty']), None)
    if first_empty_idx is not None:
        print(f"  First empty at position: {first_empty_idx + 1}/{len(all_descs)} ({(first_empty_idx+1)/len(all_descs)*100:.1f}%)")
        print(f"  First empty timestamp: {all_descs[first_empty_idx]['created']}")
    
    # Check first 100
    empty_in_first_100 = sum(1 for d in all_descs[:min(100, len(all_descs))] if d['is_empty'])
    print(f"  Empty in first 100: {empty_in_first_100}/100 ({empty_in_first_100}%)")
    
    # Check first 200
    if len(all_descs) >= 200:
        empty_in_first_200 = sum(1 for d in all_descs[:200] if d['is_empty'])
        print(f"  Empty in first 200: {empty_in_first_200}/200 ({empty_in_first_200/200*100:.1f}%)")
    
    # Check first 300
    if len(all_descs) >= 300:
        empty_in_first_300 = sum(1 for d in all_descs[:300] if d['is_empty'])
        print(f"  Empty in first 300: {empty_in_first_300}/300 ({empty_in_first_300/300*100:.1f}%)")
