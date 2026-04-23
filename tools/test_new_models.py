#!/usr/bin/env python3
"""
Test which newly added models actually support vision/image input.
Tests with a real image to verify end-to-end functionality.
"""

import sys
from pathlib import Path

# Add project root and scripts to path
project_root = Path(__file__).parent
scripts_dir = project_root / "scripts"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(scripts_dir))

from imagedescriber.ai_providers import OpenAIProvider
from config_loader import load_json_config

# Models we just added
NEW_MODELS = [
    "gpt-5.2-pro",
    "gpt-5.1", 
    "gpt-5-pro",
    "gpt-5-mini",
    "gpt-5-nano",
    "gpt-4.1",
    "gpt-4.1-mini",
    "gpt-4.1-nano"
]

# Load API key from config
config, _, _ = load_json_config('image_describer_config.json')
api_key = config.get('api_keys', {}).get('OpenAI') or config.get('api_keys', {}).get('openai')

if not api_key:
    print("❌ No OpenAI API key found in config")
    sys.exit(1)

# Find a test image
testimages = Path("testimages")
test_image = None
for ext in ['.jpg', '.jpeg', '.png']:
    candidates = list(testimages.glob(f"*{ext}"))
    if candidates:
        test_image = candidates[0]
        break

if not test_image:
    print("❌ No test image found in testimages/")
    sys.exit(1)

print(f"Testing with image: {test_image}")
print(f"Testing {len(NEW_MODELS)} new models...\n")

results = {
    "working": [],
    "failed": [],
    "no_vision": []
}

for model in NEW_MODELS:
    print(f"Testing {model}...", end=" ", flush=True)
    
    try:
        provider = OpenAIProvider(api_key=api_key)
        
        # Try to describe the image
        description = provider.describe_image(
            str(test_image),
            prompt="Briefly describe this image in one sentence.",
            model=model
        )
        
        if description and len(description.strip()) > 10:
            print(f"✅ WORKS ({len(description)} chars)")
            results["working"].append(model)
        else:
            print(f"⚠️  NO OUTPUT (vision not supported)")
            results["no_vision"].append(model)
            
    except Exception as e:
        error_msg = str(e).lower()
        if "does not support" in error_msg or "vision" in error_msg:
            print(f"⚠️  NO VISION SUPPORT")
            results["no_vision"].append(model)
        else:
            print(f"❌ ERROR: {str(e)[:100]}")
            results["failed"].append(model)

print("\n" + "="*70)
print("SUMMARY")
print("="*70)

print(f"\n✅ Working vision models ({len(results['working'])}):")
for m in results['working']:
    print(f"   - {m}")

print(f"\n⚠️  No vision support ({len(results['no_vision'])}):")
for m in results['no_vision']:
    print(f"   - {m}")

print(f"\n❌ Failed with errors ({len(results['failed'])}):")
for m in results['failed']:
    print(f"   - {m}")

print("\n" + "="*70)
print("RECOMMENDATION")
print("="*70)
if results['no_vision'] or results['failed']:
    print("\nRemove these models from model lists:")
    for m in results['no_vision'] + results['failed']:
        print(f'  "{m}",')
else:
    print("\nAll new models support vision! ✅")
