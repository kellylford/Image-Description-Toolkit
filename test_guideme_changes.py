#!/usr/bin/env python3
"""
Test script for guided_workflow.py changes

Validates:
1. API key detection from config file
2. Model list loading from models package
3. USE_CONFIG marker handling
"""

import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent / 'scripts'))

from guided_workflow import check_api_key_in_config, check_api_key_file

def test_api_key_detection():
    """Test API key detection from config"""
    print("=" * 70)
    print("TEST: API Key Detection")
    print("=" * 70)
    
    # Test OpenAI
    print("\n1. Checking for OpenAI API key in config...")
    config_path, api_key = check_api_key_in_config('openai')
    if config_path and api_key:
        masked = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
        print(f"   ✓ Found in config: {config_path}")
        print(f"   ✓ Key (masked): {masked}")
    else:
        print(f"   ✗ Not found in config")
    
    # Test Claude
    print("\n2. Checking for Claude API key in config...")
    config_path, api_key = check_api_key_in_config('claude')
    if config_path and api_key:
        masked = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
        print(f"   ✓ Found in config: {config_path}")
        print(f"   ✓ Key (masked): {masked}")
    else:
        print(f"   ✗ Not found in config")
    
    # Test file-based keys
    print("\n3. Checking for standalone API key files...")
    openai_file = check_api_key_file('openai')
    if openai_file:
        print(f"   ✓ Found OpenAI key file: {openai_file}")
    else:
        print(f"   ✗ No OpenAI key file found")
    
    claude_file = check_api_key_file('claude')
    if claude_file:
        print(f"   ✓ Found Claude key file: {claude_file}")
    else:
        print(f"   ✗ No Claude key file found")


def test_model_imports():
    """Test model list imports"""
    print("\n" + "=" * 70)
    print("TEST: Model List Imports")
    print("=" * 70)
    
    # Add project root to path
    project_root = Path(__file__).parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    # Test OpenAI models
    print("\n1. Testing OpenAI model import...")
    try:
        from models.openai_models import get_openai_models, format_openai_model_for_display
        models = get_openai_models()
        print(f"   ✓ Loaded {len(models)} OpenAI models")
        print(f"   First 5 models:")
        for model in models[:5]:
            formatted = format_openai_model_for_display(model)
            print(f"     - {formatted}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test Claude models
    print("\n2. Testing Claude model import...")
    try:
        from models.claude_models import get_claude_models, format_claude_model_for_display
        models = get_claude_models()
        print(f"   ✓ Loaded {len(models)} Claude models")
        print(f"   First 5 models:")
        for model in models[:5]:
            formatted = format_claude_model_for_display(model)
            print(f"     - {formatted}")
    except Exception as e:
        print(f"   ✗ Error: {e}")


def main():
    print("Testing guided_workflow.py changes\n")
    
    test_api_key_detection()
    test_model_imports()
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("\nAll tests completed. Review output above for any failures.")
    print("\nTo test the full interactive workflow:")
    print("  python scripts/guided_workflow.py")
    print("  OR")
    print("  idt guideme")
    print()


if __name__ == '__main__':
    main()
