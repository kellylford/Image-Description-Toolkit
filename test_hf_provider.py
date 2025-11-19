#!/usr/bin/env python3
"""
Test script for HuggingFace provider

Tests that the HuggingFace provider is properly implemented and registered.
Note: Requires transformers to be installed for full functionality.

Usage:
    python test_hf_provider.py
"""

import sys
from pathlib import Path

# Add imagedescriber to path
sys.path.insert(0, str(Path(__file__).parent / "imagedescriber"))

from ai_providers import get_all_providers, get_available_providers


def test_provider_exists():
    """Test that HuggingFace provider is defined"""
    print("=== Test 1: Provider Exists ===")
    
    all_providers = get_all_providers()
    print(f"All providers: {list(all_providers.keys())}")
    
    if 'huggingface' in all_providers:
        print("✓ HuggingFace provider is defined")
        hf_provider = all_providers['huggingface']
        print(f"  Provider name: {hf_provider.get_provider_name()}")
        return True
    else:
        print("✗ HuggingFace provider NOT defined")
        return False


def test_provider_availability():
    """Test provider availability (requires transformers)"""
    print("\n=== Test 2: Provider Availability ===")
    
    all_providers = get_all_providers()
    hf_provider = all_providers['huggingface']
    
    is_available = hf_provider.is_available()
    print(f"  Is available: {is_available}")
    
    if is_available:
        print("✓ HuggingFace provider is available (transformers installed)")
        
        # Test model list
        models = hf_provider.get_available_models()
        print(f"  Available models: {len(models)}")
        for model in models:
            print(f"    - {model}")
        
        # Test provider registration
        available_providers = get_available_providers()
        if 'huggingface' in available_providers:
            print("✓ Provider is registered in available_providers()")
        else:
            print("✗ Provider NOT in available_providers()")
            return False
    else:
        print("ℹ HuggingFace provider unavailable (transformers not installed)")
        print("  This is expected if transformers package is not installed")
        print("  To enable: pip install 'transformers>=4.45.0' torch torchvision pillow")
    
    return True


def test_model_registry():
    """Test that HuggingFace models are in the registry"""
    print("\n=== Test 3: Model Registry ===")
    
    from models.manage_models import MODEL_METADATA
    
    hf_models = {k: v for k, v in MODEL_METADATA.items() if v.get('provider') == 'huggingface'}
    
    print(f"  HuggingFace models in registry: {len(hf_models)}")
    for model_name, metadata in hf_models.items():
        print(f"    - {model_name}")
        print(f"      Description: {metadata.get('description', 'N/A')}")
        print(f"      Size: {metadata.get('size', 'N/A')}")
        print(f"      Recommended: {metadata.get('recommended', False)}")
    
    if len(hf_models) > 0:
        print(f"✓ Found {len(hf_models)} HuggingFace models in registry")
        return True
    else:
        print("✗ No HuggingFace models in registry")
        return False


def main():
    """Run all tests"""
    print("HuggingFace Provider Test Suite")
    print("=" * 60)
    
    test1 = test_provider_exists()
    test2 = test_provider_availability()
    test3 = test_model_registry()
    
    print("\n" + "=" * 60)
    print("Test Summary:")
    print(f"  Provider Exists: {'✓ PASS' if test1 else '✗ FAIL'}")
    print(f"  Provider Availability: {'✓ PASS' if test2 else '✗ FAIL'}")
    print(f"  Model Registry: {'✓ PASS' if test3 else '✗ FAIL'}")
    print("=" * 60)
    
    if test1 and test3:
        print("\n✓ All core tests passed")
        print("ℹ Provider is properly implemented and ready to use")
        return True
    else:
        print("\n✗ Some tests failed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
