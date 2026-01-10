#!/usr/bin/env python3
"""
Test script to debug image processing issues in ImageDescriber
"""

import sys
from pathlib import Path

# Add to path
sys.path.insert(0, str(Path.cwd()))
sys.path.insert(0, str(Path.cwd() / "imagedescriber"))

# Test 1: Can we import the worker?
print("=" * 60)
print("TEST 1: Import ProcessingWorker")
print("=" * 60)

try:
    from imagedescriber.workers_wx import ProcessingWorker
    print("✓ ProcessingWorker imported")
except Exception as e:
    print(f"✗ Failed to import ProcessingWorker: {e}")
    sys.exit(1)

# Test 2: Can we import ai_providers?
print("\n" + "=" * 60)
print("TEST 2: Import AI providers")
print("=" * 60)

try:
    from imagedescriber.ai_providers import get_available_providers
    print("✓ get_available_providers imported")
    providers = get_available_providers()
    print(f"✓ Available providers: {list(providers.keys())}")
except Exception as e:
    print(f"✗ Failed to get providers: {e}")
    sys.exit(1)

# Test 3: Find test image
print("\n" + "=" * 60)
print("TEST 3: Find test image")
print("=" * 60)

test_images_dir = Path("testimages")
test_images = list(test_images_dir.glob("*.jpg")) + list(test_images_dir.glob("*.png"))

if not test_images:
    print(f"✗ No test images found in {test_images_dir}")
    sys.exit(1)

test_image = test_images[0]
print(f"✓ Found test image: {test_image}")
print(f"  Size: {test_image.stat().st_size / 1024:.1f} KB")

# Test 4: Create a mock parent window
print("\n" + "=" * 60)
print("TEST 4: Create mock parent for worker")
print("=" * 60)

class MockWindow:
    """Mock wxPython window for event posting"""
    def GetId(self):
        return 0
    
    def __repr__(self):
        return "<MockWindow>"

mock_window = MockWindow()
print(f"✓ Created mock window: {mock_window}")

# Test 5: Create the worker
print("\n" + "=" * 60)
print("TEST 5: Create ProcessingWorker")
print("=" * 60)

try:
    worker = ProcessingWorker(
        parent_window=mock_window,
        file_path=str(test_image),
        provider="ollama",
        model="moondream",
        prompt_style="detailed",
        custom_prompt="",
        detection_settings=None,
        prompt_config_path=None
    )
    print(f"✓ Worker created: {worker}")
except Exception as e:
    print(f"✗ Failed to create worker: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 6: Test the _load_prompt_config method directly
print("\n" + "=" * 60)
print("TEST 6: Test _load_prompt_config")
print("=" * 60)

try:
    config = worker._load_prompt_config()
    print(f"✓ Config loaded")
    print(f"  Keys: {list(config.keys())}")
    if "prompts" in config or "prompt_variations" in config:
        print(f"  ✓ Has prompt data")
except Exception as e:
    print(f"✗ Failed to load config: {e}")
    import traceback
    traceback.print_exc()

# Test 7: Try to call _process_with_ai directly (without threading)
print("\n" + "=" * 60)
print("TEST 7: Test _process_with_ai (may take time/fail if no provider)")
print("=" * 60)

try:
    print(f"Attempting to process image with ollama/moondream...")
    print("(This will fail if ollama is not running or moondream model not loaded)")
    
    config = worker._load_prompt_config()
    prompt = "Describe this image"
    
    # This will likely fail if ollama is not running, but we want to see the error
    description = worker._process_with_ai(str(test_image), prompt)
    print(f"✓ Got description: {description[:100]}...")
    
except Exception as e:
    print(f"✗ Processing failed: {e}")
    print("\nNote: This is expected if ollama is not running.")
    print("The important thing is that the error is caught and reported.")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
