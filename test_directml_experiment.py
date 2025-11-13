#!/usr/bin/env python3
"""
Experimental script to test Florence-2 with ONNX Runtime DirectML acceleration
This is for testing NPU performance without modifying the main codebase

Requirements:
  pip install optimum[onnxruntime-directml] onnxruntime-directml

Usage:
  python test_directml_experiment.py testimages/blue_circle.jpg
"""

import sys
import time
from pathlib import Path

def test_directml_florence():
    """Test Florence-2 with DirectML acceleration"""
    print("=" * 70)
    print("Florence-2 DirectML NPU Acceleration Test")
    print("=" * 70)
    
    # Check for required packages
    try:
        import onnxruntime
        print(f"✓ onnxruntime version: {onnxruntime.__version__}")
    except ImportError:
        print("✗ onnxruntime-directml not installed")
        print("  Install with: pip install onnxruntime-directml")
        return False
    
    try:
        from optimum.onnxruntime import ORTModelForVision2Seq
        from transformers import AutoProcessor
        from PIL import Image
        print("✓ optimum and transformers installed")
    except ImportError as e:
        print(f"✗ Missing package: {e}")
        print("  Install with: pip install optimum transformers pillow")
        return False
    
    # Get image path
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        image_path = "testimages/blue_circle.jpg"
    
    if not Path(image_path).exists():
        print(f"✗ Image not found: {image_path}")
        return False
    
    print(f"\nImage: {image_path}")
    print("-" * 70)
    
    # Check available providers
    providers = onnxruntime.get_available_providers()
    print(f"\nAvailable ONNX Runtime providers: {providers}")
    
    if 'DmlExecutionProvider' in providers:
        print("✓ DirectML provider available - NPU/GPU acceleration ready!")
        provider = 'DmlExecutionProvider'
    else:
        print("⚠ DirectML provider not available - falling back to CPU")
        provider = 'CPUExecutionProvider'
    
    print(f"\nUsing provider: {provider}")
    print("-" * 70)
    
    # Load model with ONNX Runtime
    print("\n1. Loading Florence-2 model...")
    print("   (First run will export to ONNX - takes 1-2 minutes)")
    print("   (Subsequent runs will be instant)")
    
    load_start = time.time()
    try:
        # This will automatically:
        # 1. Export Florence-2 to ONNX format (cached after first run)
        # 2. Use DirectML provider for acceleration
        model = ORTModelForVision2Seq.from_pretrained(
            "microsoft/Florence-2-base",
            export=True,  # Export to ONNX if not already done
            provider=provider,
            use_io_binding=True if provider == 'DmlExecutionProvider' else False
        )
        processor = AutoProcessor.from_pretrained("microsoft/Florence-2-base", trust_remote_code=True)
        load_time = time.time() - load_start
        print(f"   ✓ Model loaded in {load_time:.2f} seconds")
    except Exception as e:
        print(f"   ✗ Failed to load model: {e}")
        print("\n   This might be because Florence-2 doesn't support ONNX export via optimum.")
        print("   Florence-2 uses custom model code that may not be compatible.")
        return False
    
    # Load image
    print("\n2. Loading image...")
    image = Image.open(image_path).convert("RGB")
    print(f"   ✓ Image loaded: {image.size}")
    
    # Test different detail levels
    tasks = [
        ("<CAPTION>", "Simple"),
        ("<DETAILED_CAPTION>", "Detailed"),
        ("<MORE_DETAILED_CAPTION>", "Narrative")
    ]
    
    print("\n3. Generating descriptions...")
    print("=" * 70)
    
    for task, label in tasks:
        print(f"\n{label} Description ({task}):")
        print("-" * 70)
        
        # Prepare inputs
        inputs = processor(text=task, images=image, return_tensors="pt")
        
        # Generate with timing
        gen_start = time.time()
        generated_ids = model.generate(
            **inputs,
            max_new_tokens=512,
            use_cache=False  # Same workaround as main implementation
        )
        gen_time = time.time() - gen_start
        
        # Decode output
        generated_text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        description = generated_text.replace(task, "").strip()
        
        print(f"Time: {gen_time:.2f} seconds")
        print(f"Description: {description[:200]}{'...' if len(description) > 200 else ''}")
    
    print("\n" + "=" * 70)
    print("Test Complete!")
    print("=" * 70)
    
    if provider == 'DmlExecutionProvider':
        print("\n✓ This used DirectML (NPU/GPU) acceleration")
    else:
        print("\n⚠ This used CPU only (DirectML not available)")
    
    return True

if __name__ == "__main__":
    try:
        success = test_directml_florence()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
