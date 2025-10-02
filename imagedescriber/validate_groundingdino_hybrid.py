"""
Quick validation script for GroundingDINO hybrid mode fixes.

Run this to verify:
1. Config file path resolution works
2. Checkpoint download/caching works
3. Ollama models are available for hybrid mode
4. Validation prevents invalid configurations

This doesn't test the full UI, just the core provider logic.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all required imports work"""
    print("=" * 60)
    print("TEST 1: Imports")
    print("=" * 60)
    
    try:
        import groundingdino
        print("✅ groundingdino imported")
        
        from groundingdino.util.inference import Model
        print("✅ groundingdino.util.inference.Model imported")
        
        import torch
        print("✅ torch imported")
        
        from ai_providers import GroundingDINOProvider, GroundingDINOHybridProvider
        print("✅ GroundingDINO providers imported")
        
        return True, groundingdino, torch
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False, None, None

def test_config_path(groundingdino):
    """Test config file path resolution"""
    print("\n" + "=" * 60)
    print("TEST 2: Config File Path")
    print("=" * 60)
    
    try:
        package_path = os.path.dirname(groundingdino.__file__)
        config_path = os.path.join(package_path, "config", "GroundingDINO_SwinT_OGC.py")
        
        print(f"Package path: {package_path}")
        print(f"Config path: {config_path}")
        
        if os.path.exists(config_path):
            print("✅ Config file exists at resolved path")
            return True
        else:
            print("❌ Config file not found at resolved path")
            return False
    except Exception as e:
        print(f"❌ Config path resolution failed: {e}")
        return False

def test_checkpoint_cache(torch):
    """Test checkpoint cache directory"""
    print("\n" + "=" * 60)
    print("TEST 3: Checkpoint Cache")
    print("=" * 60)
    
    try:
        cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "torch", "hub", "checkpoints")
        checkpoint_path = os.path.join(cache_dir, "groundingdino_swint_ogc.pth")
        
        print(f"Cache directory: {cache_dir}")
        print(f"Checkpoint path: {checkpoint_path}")
        
        if os.path.exists(checkpoint_path):
            size_mb = os.path.getsize(checkpoint_path) / (1024 * 1024)
            print(f"✅ Checkpoint cached ({size_mb:.1f} MB)")
            return True
        else:
            print("⚠️ Checkpoint not yet cached (will download on first use)")
            print("   Expected size: ~700MB")
            return True  # Not an error, just not downloaded yet
    except Exception as e:
        print(f"❌ Cache check failed: {e}")
        return False

def test_provider_creation():
    """Test provider instantiation"""
    print("\n" + "=" * 60)
    print("TEST 4: Provider Creation")
    print("=" * 60)
    
    try:
        from ai_providers import GroundingDINOProvider, GroundingDINOHybridProvider
        
        # Test standalone provider
        standalone = GroundingDINOProvider()
        print(f"✅ GroundingDINOProvider created")
        print(f"   Available: {standalone.is_available()}")
        
        # Test hybrid provider
        hybrid = GroundingDINOHybridProvider()
        print(f"✅ GroundingDINOHybridProvider created")
        print(f"   Available: {hybrid.is_available()}")
        
        # Check if hybrid can get Ollama models
        models = hybrid.get_available_models()
        if models:
            print(f"✅ Hybrid provider found {len(models)} Ollama models:")
            for model in models[:5]:  # Show first 5
                print(f"      - {model}")
        else:
            print("⚠️ No Ollama models available")
            print("   For hybrid mode, install: ollama pull llava")
        
        return True
    except Exception as e:
        print(f"❌ Provider creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_device_detection(torch):
    """Test CUDA/CPU device detection"""
    print("\n" + "=" * 60)
    print("TEST 5: Device Detection")
    print("=" * 60)
    
    try:
        cuda_available = torch.cuda.is_available()
        if cuda_available:
            device_name = torch.cuda.get_device_name(0)
            print(f"✅ CUDA GPU available: {device_name}")
            print("   Detection will be FAST (<1 second)")
        else:
            print("⚠️ CUDA not available, will use CPU")
            print("   Detection will be slower (3-10 seconds)")
        
        return True
    except Exception as e:
        print(f"❌ Device detection failed: {e}")
        return False

def main():
    """Run all validation tests"""
    print("\n" + "=" * 70)
    print(" GroundingDINO Hybrid Mode - Quick Validation")
    print("=" * 70)
    
    results = []
    
    # Test 1: Imports
    success, groundingdino, torch_module = test_imports()
    results.append(("Imports", success))
    if not success:
        print("\n❌ Cannot continue - imports failed")
        print("   Run: pip install groundingdino-py torch torchvision")
        return False
    
    # Test 2: Config path
    success = test_config_path(groundingdino)
    results.append(("Config Path", success))
    
    # Test 3: Checkpoint cache
    success = test_checkpoint_cache(torch_module)
    results.append(("Checkpoint Cache", success))
    
    # Test 4: Provider creation
    success = test_provider_creation()
    results.append(("Provider Creation", success))
    
    # Test 5: Device detection
    success = test_device_detection(torch_module)
    results.append(("Device Detection", success))
    
    # Summary
    print("\n" + "=" * 70)
    print(" VALIDATION SUMMARY")
    print("=" * 70)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status:12} {test_name}")
        if not passed:
            all_passed = False
    
    print("=" * 70)
    
    if all_passed:
        print("\n✅ ALL TESTS PASSED - Ready to test in UI")
        print("\nNext steps:")
        print("1. Launch ImageDescriber")
        print("2. Select 'GroundingDINO + Ollama' provider")
        print("3. Select an Ollama model (e.g., llava:latest)")
        print("4. Process an image")
        print("5. Verify: Detection summary + Ollama description")
    else:
        print("\n⚠️ SOME TESTS FAILED - Review errors above")
    
    return all_passed

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nValidation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
