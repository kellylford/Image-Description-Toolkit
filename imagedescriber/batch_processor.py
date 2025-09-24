#!/usr/bin/env python3
"""
Batch Image Description Tool for Kelly's Image Collection

This script processes hundreds of images from C:/Users/kelly/GitHub/testingimages
with automatic HEIC conversion and smart model selection.
"""

import os
import sys
import json
from pathlib import Path
from enhanced_processor import EnhancedImageProcessor

def main():
    # Configuration
    images_dir = Path("C:/Users/kelly/GitHub/testingimages")
    output_file = Path("C:/Users/kelly/GitHub/Image-Description-Toolkit/batch_results.json")
    
    # Prompt for image descriptions
    prompt = """Provide a detailed description of this image including:
- Main subjects and objects
- Colors and lighting
- Setting or location if identifiable
- Actions or activities
- Overall composition and mood
Keep the description factual and descriptive."""
    
    print("🖼️  Batch Image Description Tool")
    print("=" * 50)
    print(f"📁 Source directory: {images_dir}")
    print(f"💾 Output file: {output_file}")
    print(f"📝 Prompt: {prompt[:100]}...")
    print()
    
    if not images_dir.exists():
        print(f"❌ Directory not found: {images_dir}")
        return
    
    # Initialize processor
    processor = EnhancedImageProcessor()
    
    # Test available vision models
    print("🔍 Testing available vision models...")
    local_models = ['llava:latest', 'llava-llama3:latest', 'bakllava:latest', 'moondream:latest']
    
    available_models = []
    for model in local_models:
        if processor.test_vision_capability(model):
            available_models.append(model)
            print(f"✅ {model} - Vision capable")
        else:
            print(f"❌ {model} - Not available")
    
    if not available_models:
        print("⚠️  No vision-capable models found. Please install a vision model:")
        print("   ollama pull llava:latest")
        return
    
    # Select best model (prefer llava-llama3 > llava > bakllava > moondream)
    model_priority = ['llava-llama3:latest', 'llava:latest', 'bakllava:latest', 'moondream:latest']
    selected_model = None
    for preferred in model_priority:
        if preferred in available_models:
            selected_model = preferred
            break
    
    print(f"🤖 Selected model: {selected_model}")
    print()
    
    # Get user confirmation
    response = input("🚀 Start batch processing? (y/N): ").strip().lower()
    if response != 'y':
        print("Cancelled.")
        return
    
    # Start processing
    print("🔄 Starting batch processing...")
    results = processor.batch_process(
        images_dir=images_dir,
        output_file=output_file,
        prompt=prompt,
        preferred_model=selected_model
    )
    
    # Generate summary report
    print("\n📊 Processing Summary")
    print("=" * 50)
    
    successful = [r for r in results if r.get('success')]
    failed = [r for r in results if not r.get('success')]
    converted = [r for r in results if r.get('converted_path')]
    
    print(f"Total images: {len(results)}")
    print(f"Successfully processed: {len(successful)}")
    print(f"Failed: {len(failed)}")
    print(f"HEIC conversions: {len(converted)}")
    
    if failed:
        print("\n❌ Failed images:")
        for failure in failed[:5]:  # Show first 5 failures
            print(f"   • {Path(failure['image_path']).name}: {failure.get('error', 'Unknown error')}")
        if len(failed) > 5:
            print(f"   ... and {len(failed) - 5} more")
    
    print(f"\n💾 Full results saved to: {output_file}")
    print("\n🎉 Batch processing complete!")

if __name__ == "__main__":
    main()