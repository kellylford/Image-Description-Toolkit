#!/usr/bin/env python3
import json
import sys

workspace_file = sys.argv[1] if len(sys.argv) > 1 else 'EuropeNano509_20260214.idw'

with open(workspace_file, 'r') as f:
    workspace = json.load(f)

# Find IMG_3137.PNG
for path, item in workspace['items'].items():
    if 'IMG_3137.PNG' in path:
        print(f"Found: {path}\n")
        descriptions = item.get('descriptions', [])
        print(f"Total descriptions: {len(descriptions)}\n")
        
        for i, desc in enumerate(descriptions, 1):
            text = desc.get('text', '').strip()
            model = desc.get('model', 'unknown')
            provider = desc.get('provider', 'unknown')
            created = desc.get('created', 'unknown')
            
            if text:
                preview = text[:150] + "..." if len(text) > 150 else text
            else:
                preview = "(EMPTY)"
            
            print(f"Description #{i}:")
            print(f"  Provider: {provider}")
            print(f"  Model: {model}")
            print(f"  Created: {created}")
            print(f"  Text: {preview}")
            print()
        break
