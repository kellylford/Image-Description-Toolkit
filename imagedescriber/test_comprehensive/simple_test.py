#!/usr/bin/env python3
"""
Simple Test - Uses ImageDescriber's existing code directly
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to import ImageDescriber classes
sys.path.insert(0, str(Path(__file__).parent.parent))

from imagedescriber import ImageWorkspace, ImageItem, ProcessingWorker
import ollama
import time

def main():
    print("=== Simple ImageDescriber Test ===")
    
    # Create workspace using ImageDescriber's own code
    workspace = ImageWorkspace()
    
    # Use the actual test images
    test_images_dir = Path(__file__).parent.parent.parent / "tests" / "test_files" / "images"
    test_images = list(test_images_dir.glob("*.jpg"))[:1]  # Just one image to start
    
    print(f"Testing with: {[img.name for img in test_images]}")
    
    # Get models
    models_response = ollama.list()
    vision_models = []
    for model_obj in models_response.models:
        model_name = getattr(model_obj, 'model', '')
        if model_name:
            clean_name = model_name.split(':')[0]
            if clean_name in {'llava', 'moondream'}:
                vision_models.append(clean_name)
    
    print(f"Vision models: {vision_models}")
    
    # Test each image with each model
    for image_path in test_images:
        print(f"\nProcessing: {image_path.name}")
        
        # Add image to workspace using ImageDescriber's method
        workspace_item = ImageItem(str(image_path))
        workspace.add_item(workspace_item)
        
        for model in vision_models:
            print(f"  Model: {model}")
            
            # Use ImageDescriber's actual ProcessingWorker
            worker = ProcessingWorker(str(image_path), model, "detailed", "")
            
            # Run synchronously for testing
            worker.run()
            
            if hasattr(worker, 'result') and worker.result:
                from imagedescriber import ImageDescription
                desc = ImageDescription(worker.result, model, "detailed")
                workspace_item.add_description(desc)
                print(f"    ✓ Added description ({len(worker.result)} chars)")
            else:
                print(f"    ✗ Failed to get description")
            
            time.sleep(1)  # Brief delay
    
    # Save using ImageDescriber's format
    output_file = Path(__file__).parent / f"simple_test_{int(time.time())}.idw"
    
    # Save exactly like ImageDescriber does
    import json
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(workspace.to_dict(), f, indent=2)
    
    print(f"\nWorkspace saved to: {output_file}")
    print("You can now open this file in ImageDescriber GUI")

if __name__ == "__main__":
    main()
