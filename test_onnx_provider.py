"""
Test script for ONNX Provider with Florence-2

Usage:
    python test_onnx_provider.py

This script tests the newly implemented ONNX provider with Florence-2 models.
Requires: pip install 'transformers>=4.45.0' torch torchvision pillow
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_onnx_provider():
    """Test ONNX provider with Florence-2"""
    print("=" * 80)
    print("ONNX Provider Test")
    print("=" * 80)
    
    # Import the provider
    try:
        from imagedescriber.ai_providers import ONNXProvider, get_all_providers, get_available_providers
        print("✅ Successfully imported ONNXProvider")
    except ImportError as e:
        print(f"❌ Failed to import ONNXProvider: {e}")
        return False
    
    # Check if provider is available
    provider = ONNXProvider()
    print(f"\nProvider Name: {provider.get_provider_name()}")
    print(f"Is Available: {provider.is_available()}")
    
    if not provider.is_available():
        print("\n⚠️  Florence-2 dependencies not installed.")
        print("Install with: pip install 'transformers>=4.45.0' torch torchvision pillow")
        return False
    
    # Check available models
    models = provider.get_available_models()
    print(f"\nAvailable Models: {len(models)}")
    for model in models:
        print(f"  • {model}")
    
    # Check if provider is in registry
    all_providers = get_all_providers()
    available_providers = get_available_providers()
    
    print(f"\nProvider Registry:")
    print(f"  • In all_providers: {'onnx' in all_providers}")
    print(f"  • In available_providers: {'onnx' in available_providers}")
    
    # Test image description (if dependencies are installed)
    test_image = project_root / "testimages" / "red_square.jpg"
    if test_image.exists():
        print(f"\n" + "=" * 80)
        print(f"Testing with image: {test_image}")
        print("=" * 80)
        
        # Test with base model
        model = "microsoft/Florence-2-base"
        prompt = "Describe this image in detail"
        
        print(f"\nModel: {model}")
        print(f"Prompt: {prompt}")
        print(f"\nGenerating description (this may take a minute on first run)...")
        
        try:
            description = provider.describe_image(str(test_image), prompt, model)
            print(f"\n{'-' * 80}")
            print("Description:")
            print(f"{'-' * 80}")
            print(description)
            print(f"{'-' * 80}")
            
            # Test different prompt styles
            print(f"\n" + "=" * 80)
            print("Testing prompt style variations:")
            print("=" * 80)
            
            styles = [
                ("simple", "Give a simple brief description"),
                ("technical", "Provide a technical detailed description"),
                ("narrative", "Create a narrative comprehensive description")
            ]
            
            for style_name, style_prompt in styles:
                print(f"\n{style_name.upper()} style:")
                desc = provider.describe_image(str(test_image), style_prompt, model)
                print(f"  {desc[:100]}...")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Error generating description: {e}")
            import traceback
            traceback.print_exc()
            return False
    else:
        print(f"\n⚠️  Test image not found: {test_image}")
        return False

if __name__ == "__main__":
    success = test_onnx_provider()
    sys.exit(0 if success else 1)
