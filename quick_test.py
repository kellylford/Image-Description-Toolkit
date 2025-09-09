#!/usr/bin/env python3
"""
Quick test to see if we can get any AI model to work at all
This is the simplest possible test - just call Ollama directly
"""

import base64
import json
import sys
from pathlib import Path

# Add the scripts directory to path so we can import ollama
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

try:
    import ollama
    print("✓ Ollama imported successfully")
except ImportError as e:
    print(f"✗ Failed to import ollama: {e}")
    sys.exit(1)

def test_basic_ollama():
    """Test if ollama works with a simple text prompt first"""
    try:
        print("\n=== Testing Ollama with text-only prompt ===")
        response = ollama.chat(
            model='moondream',
            messages=[{
                'role': 'user',
                'content': 'Say hello world'
            }]
        )
        print(f"Text response: {response}")
        return True
    except Exception as e:
        print(f"Text test failed: {e}")
        return False

def test_image_processing():
    """Test if we can process one simple image"""
    test_image = Path("tests/test_files/images/blue_landscape.jpg")
    
    if not test_image.exists():
        print(f"✗ Test image not found: {test_image}")
        return False
    
    try:
        print(f"\n=== Testing image processing with {test_image.name} ===")
        
        # Read and encode image
        with open(test_image, 'rb') as f:
            image_data = f.read()
        
        print(f"Image size: {len(image_data)} bytes")
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        print(f"Base64 encoded length: {len(image_base64)}")
        
        # Try with moondream first
        print("\nTrying moondream...")
        response = ollama.chat(
            model='moondream',
            messages=[{
                'role': 'user',
                'content': 'What do you see in this image?',
                'images': [image_base64]
            }],
            options={
                'temperature': 0.1,
                'num_predict': 100
            }
        )
        
        print(f"Raw response: {response}")
        
        if 'message' in response and 'content' in response['message']:
            content = response['message']['content']
            if content and content.strip():
                print(f"✓ SUCCESS: {content.strip()}")
                return True
            else:
                print("✗ Empty content in response")
        else:
            print("✗ Unexpected response format")
        
        return False
        
    except Exception as e:
        print(f"✗ Image processing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Quick Ollama Test")
    print("=" * 50)
    
    # Test 1: Basic text
    text_works = test_basic_ollama()
    
    # Test 2: Image processing
    if text_works:
        image_works = test_image_processing()
    else:
        print("Skipping image test since text test failed")
        image_works = False
    
    print("\n" + "=" * 50)
    print("SUMMARY:")
    print(f"Text processing: {'✓ WORKS' if text_works else '✗ FAILED'}")
    print(f"Image processing: {'✓ WORKS' if image_works else '✗ FAILED'}")
    
    if not text_works:
        print("\nOllama appears to have fundamental issues.")
        print("Try: ollama list, ollama pull moondream, ollama serve")
    elif not image_works:
        print("\nText works but image processing fails.")
        print("This might be a vision model or image encoding issue.")
