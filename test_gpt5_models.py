#!/usr/bin/env python3
"""
Test script to verify GPT-5 models are available via OpenAI API
"""
import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from openai import OpenAI
except ImportError:
    print("ERROR: openai package not installed")
    print("Run: pip install openai")
    sys.exit(1)

# Try to get API key from config
try:
    config_path = project_root / 'scripts' / 'image_describer_config.json'
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    api_keys = config.get('api_keys', {})
    api_key = None
    for key in ['OpenAI', 'openai', 'OPENAI']:
        if key in api_keys and api_keys[key]:
            api_key = api_keys[key].strip()
            break
    
    if not api_key:
        print("ERROR: No OpenAI API key found in config file")
        print(f"Config path: {config_path}")
        print(f"API keys section: {api_keys}")
        sys.exit(1)
    
    print(f"✓ Found API key in config")
    
except Exception as e:
    print(f"ERROR loading config: {e}")
    sys.exit(1)

# Initialize OpenAI client
try:
    client = OpenAI(api_key=api_key)
    print("✓ OpenAI client initialized")
except Exception as e:
    print(f"ERROR initializing OpenAI client: {e}")
    sys.exit(1)

# List available models
print("\n" + "="*60)
print("Checking available models from your OpenAI account:")
print("="*60)

try:
    models = client.models.list()
    model_ids = sorted([m.id for m in models.data])
    
    # Check for GPT-5 models
    gpt5_models = [m for m in model_ids if 'gpt-5' in m.lower()]
    
    print(f"\nTotal models available: {len(model_ids)}")
    
    if gpt5_models:
        print(f"\n✓ GPT-5 models found ({len(gpt5_models)}):")
        for model in gpt5_models:
            print(f"  - {model}")
    else:
        print("\n✗ No GPT-5 models found in your account")
        print("\nNote: GPT-5 models may require specific API access or tier")
    
    # Check for specific models we want to add
    target_models = ['gpt-5.2', 'gpt-5', 'gpt-5-mini']
    print(f"\n" + "="*60)
    print("Checking specific models we want to add:")
    print("="*60)
    
    for model in target_models:
        if model in model_ids:
            print(f"✓ {model} - AVAILABLE")
        else:
            print(f"✗ {model} - NOT FOUND")
    
    # Show all GPT models for context
    gpt_models = [m for m in model_ids if m.startswith('gpt-')]
    if gpt_models:
        print(f"\nAll GPT models in your account ({len(gpt_models)}):")
        for model in gpt_models:
            print(f"  - {model}")
    
except Exception as e:
    print(f"ERROR listing models: {e}")
    sys.exit(1)

# Try a simple test with an available GPT model
print(f"\n" + "="*60)
print("Testing vision capability:")
print("="*60)

# Find best available model to test with
test_model = None
for model in ['gpt-5.2', 'gpt-5', 'gpt-5-mini', 'gpt-4o', 'gpt-4o-mini']:
    if model in model_ids:
        test_model = model
        break

if test_model:
    print(f"\nTesting with model: {test_model}")
    try:
        # Simple test - no actual image needed, just check if model accepts the format
        response = client.chat.completions.create(
            model=test_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Say 'OK' if you can see this message"}
                    ]
                }
            ],
            max_tokens=10
        )
        print(f"✓ Model responded: {response.choices[0].message.content}")
        print(f"  Tokens used: {response.usage.total_tokens}")
    except Exception as e:
        print(f"✗ Test failed: {e}")
else:
    print("\n✗ No suitable model found for testing")

print("\n" + "="*60)
print("RECOMMENDATION:")
print("="*60)

if gpt5_models:
    print("✓ You have access to GPT-5 models - safe to add them")
else:
    print("✗ GPT-5 models not available in your account")
    print("  We should NOT add them to the default list yet")
    print("  Stick with gpt-4o series for now")
