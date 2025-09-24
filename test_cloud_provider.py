#!/usr/bin/env python3
"""
Test script to verify Ollama Cloud model detection works
"""

import sys
import os

# Add imagedescriber directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'imagedescriber'))

from ai_providers import get_available_providers

def test_provider_and_models():
    """Test provider and model detection"""
    print("🔍 Testing Provider Detection")
    print("=" * 40)
    
    providers = get_available_providers()
    print(f"Available providers: {list(providers.keys())}")
    
    for provider_key, provider in providers.items():
        print(f"\n📊 {provider_key}: {provider.get_provider_name()}")
        print(f"   Available: {provider.is_available()}")
        
        if provider.is_available():
            models = provider.get_available_models()
            print(f"   Models ({len(models)}): {models}")
        else:
            print("   Models: Not available")
    
    print("\n✅ Provider detection test complete!")
    
    # Test specific ollama_cloud functionality
    if 'ollama_cloud' in providers:
        print("\n🔥 Ollama Cloud Specific Test")
        print("-" * 30)
        cloud_provider = providers['ollama_cloud']
        
        print(f"Name: {cloud_provider.get_provider_name()}")
        print(f"Available: {cloud_provider.is_available()}")
        models = cloud_provider.get_available_models()
        print(f"Cloud Models: {models}")
        
        if models:
            print("✅ Ollama Cloud models detected successfully!")
            print(f"   You should see '{cloud_provider.get_provider_name()}' in ImageDescriber")
            print(f"   With model: {models[0]}")
        else:
            print("❌ No cloud models found")
    else:
        print("\n❌ ollama_cloud provider not in registry")

if __name__ == "__main__":
    test_provider_and_models()