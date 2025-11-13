#!/usr/bin/env python3
"""
Quick test script for ONNX provider
Tests that the provider is properly integrated and can generate descriptions
"""

import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

def test_provider_availability():
    """Test that ONNX provider is available"""
    print("=" * 60)
    print("Testing ONNX Provider Availability")
    print("=" * 60)
    
    try:
        from imagedescriber.ai_providers import ONNXProvider
        provider = ONNXProvider()
        
        print(f"✓ ONNXProvider imported successfully")
        print(f"  Available: {provider.is_available()}")
        
        if provider.is_available():
            print(f"  Supported models: {provider.get_available_models()}")
            return True
        else:
            print("\n⚠ Provider not available. Install dependencies:")
            print("  pip install transformers torch torchvision einops timm")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_description_generation():
    """Test generating a description with ONNX provider"""
    print("\n" + "=" * 60)
    print("Testing Description Generation")
    print("=" * 60)
    
    try:
        from imagedescriber.ai_providers import ONNXProvider
        
        provider = ONNXProvider()
        if not provider.is_available():
            print("⚠ Skipping (dependencies not installed)")
            return False
        
        # Use test image
        test_image = Path(__file__).parent / "testimages" / "red_square.jpg"
        if not test_image.exists():
            print(f"✗ Test image not found: {test_image}")
            return False
        
        print(f"\nGenerating description for: {test_image.name}")
        print("Model: microsoft/Florence-2-base")
        print("Detail level: Narrative (<MORE_DETAILED_CAPTION>)")
        print("\nThis will take 5-10 seconds on first run (model download)...")
        
        description = provider.describe_image(
            str(test_image),
            "Describe this image in detail",
            "microsoft/Florence-2-base"
        )
        
        print(f"\n✓ Description generated successfully!")
        print(f"\nResult: {description[:200]}..." if len(description) > 200 else f"\nResult: {description}")
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_cli_integration():
    """Test that ONNX is available in CLI"""
    print("\n" + "=" * 60)
    print("Testing CLI Integration")
    print("=" * 60)
    
    try:
        from scripts.workflow import create_parser
        parser = create_parser()
        
        # Check if onnx is in choices
        for action in parser._actions:
            if action.dest == 'provider':
                if 'onnx' in action.choices:
                    print("✓ ONNX provider is in CLI choices")
                    print(f"  Available providers: {list(action.choices)}")
                    return True
                else:
                    print("✗ ONNX provider NOT in CLI choices")
                    print(f"  Available providers: {list(action.choices)}")
                    return False
        
        print("✗ Provider argument not found in parser")
        return False
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("\n🔍 ONNX Provider Integration Test")
    print("=" * 60)
    
    results = []
    
    # Test 1: Provider availability
    results.append(("Provider Availability", test_provider_availability()))
    
    # Test 2: CLI integration
    results.append(("CLI Integration", test_cli_integration()))
    
    # Test 3: Description generation (only if dependencies available)
    if results[0][1]:  # If provider is available
        results.append(("Description Generation", test_description_generation()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} - {test_name}")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    print(f"\n{passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n✅ All tests passed! ONNX provider is ready to use.")
        print("\nTry it with:")
        print("  idt workflow --provider onnx --model microsoft/Florence-2-base testimages/")
    else:
        print("\n⚠ Some tests failed. Check output above for details.")
    
    return 0 if passed_count == total_count else 1

if __name__ == "__main__":
    sys.exit(main())
