#!/usr/bin/env python3
"""
Generate Consistent Alt Text for Image Gallery

This script generates alt text once per unique image and applies it consistently 
across all AI configurations. Uses Claude Haiku + narrative descriptions as the 
source for generating consistent, accessible alt text.

The same image gets the same alt text regardless of AI model/prompt combination.
"""

import os
import sys
import json
import requests
import time
from pathlib import Path
from typing import Dict, Optional, Set

def get_claude_api_key() -> Optional[str]:
    """Get Claude API key from environment."""
    return os.getenv('ANTHROPIC_API_KEY')

def call_claude_for_alt_text(api_key: str, description: str) -> Optional[str]:
    """Generate alt text using Claude Haiku."""
    url = "https://api.anthropic.com/v1/messages"
    
    prompt = f"""Create concise, descriptive alt text for an image based on this description. The alt text should be accessible, informative, and 25-50 words maximum.

Description: {description}

Provide only the alt text, no explanatory text."""

    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01"
    }
    
    data = {
        "model": "claude-3-5-haiku-20241022",
        "max_tokens": 100,
        "temperature": 0.1,
        "messages": [{"role": "user", "content": prompt}]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        return result['content'][0]['text'].strip()
    except Exception as e:
        print(f"Error generating alt text: {e}")
        return None

def collect_all_images(jsondata_dir: Path) -> Set[str]:
    """Collect all unique image filenames across all configurations."""
    all_images = set()
    
    json_files = list(jsondata_dir.glob("*.json"))
    json_files = [f for f in json_files if f.name != "index.json"]
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for image_name in data.get('images', {}).keys():
                all_images.add(image_name)
        except Exception as e:
            print(f"Warning: Could not read {json_file.name}: {e}")
    
    return all_images

def get_best_description_for_image(jsondata_dir: Path, image_name: str) -> str:
    """Get the best description for generating alt text - prefer Claude Haiku narrative."""
    
    # Priority order for source descriptions (best quality for alt text generation)
    preferred_sources = [
        "claude_claude-3-5-haiku-20241022_narrative.json",
        "claude_claude-3-haiku-20240307_narrative.json", 
        "openai_gpt-4o-mini_narrative.json",
        "openai_gpt-4o_narrative.json"
    ]
    
    # Try preferred sources first
    for source_file in preferred_sources:
        json_path = jsondata_dir / source_file
        if json_path.exists():
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if image_name in data.get('images', {}):
                    description = data['images'][image_name].get('description', '')
                    if description and len(description) > 50:  # Good quality description
                        print(f"  Using description from {source_file}")
                        return description
            except Exception:
                continue
    
    # Fallback: find any description for this image
    json_files = list(jsondata_dir.glob("*.json"))
    json_files = [f for f in json_files if f.name != "index.json"]
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if image_name in data.get('images', {}):
                description = data['images'][image_name].get('description', '')
                if description and len(description) > 20:
                    print(f"  Using fallback description from {json_file.name}")
                    return description
        except Exception:
            continue
    
    return ""

def generate_consistent_alt_text(jsondata_dir: Path, api_key: str):
    """Generate consistent alt text for all images, then apply to all configurations."""
    
    print("Phase 1: Collecting all unique images...")
    all_images = collect_all_images(jsondata_dir)
    print(f"Found {len(all_images)} unique images")
    
    print("\nPhase 2: Generating alt text for each unique image...")
    image_alt_text = {}  # image_name -> alt_text mapping
    
    for i, image_name in enumerate(sorted(all_images), 1):
        print(f"\n[{i}/{len(all_images)}] Processing: {image_name}")
        
        # Get best description for this image
        description = get_best_description_for_image(jsondata_dir, image_name)
        
        if description:
            print(f"  Generating alt text...")
            alt_text = call_claude_for_alt_text(api_key, description)
            if alt_text:
                image_alt_text[image_name] = alt_text
                print(f"  ✓ Generated: {alt_text[:60]}...")
                time.sleep(1)  # Rate limiting
            else:
                # Fallback to first sentence
                first_sentence = description.split('.')[0][:80] + "..."
                image_alt_text[image_name] = first_sentence
                print(f"  ⚠ Fallback: {first_sentence}")
        else:
            # Use filename as last resort
            image_alt_text[image_name] = f"Image: {image_name.replace('_', ' ').replace('.jpg', '').replace('.jpeg', '').replace('.png', '')}"
            print(f"  ⚠ No description found, using filename")
    
    print(f"\nPhase 3: Applying consistent alt text to all {len(list(jsondata_dir.glob('*.json')))-1} configuration files...")
    
    # Apply the same alt text to all configurations
    json_files = list(jsondata_dir.glob("*.json"))
    json_files = [f for f in json_files if f.name != "index.json"]
    
    for json_file in json_files:
        print(f"\nUpdating: {json_file.name}")
        
        try:
            # Create backup
            backup_file = json_file.with_suffix('.json.bak')
            if not backup_file.exists():
                with open(json_file, 'r', encoding='utf-8') as original:
                    with open(backup_file, 'w', encoding='utf-8') as backup:
                        backup.write(original.read())
            
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            modified = False
            updated_count = 0
            
            for image_name, image_data in data.get('images', {}).items():
                if image_name in image_alt_text:
                    image_data['alt_text'] = image_alt_text[image_name]
                    modified = True
                    updated_count += 1
            
            if modified:
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"  ✓ Updated {updated_count} images")
            else:
                print(f"  - No images to update")
                
        except Exception as e:
            print(f"  ✗ Error updating {json_file.name}: {e}")

def main():
    """Main function."""
    jsondata_dir = Path("jsondata")
    
    if not jsondata_dir.exists():
        print("Error: jsondata directory not found")
        return 1
    
    api_key = get_claude_api_key()
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not found")
        print("Please set your Claude API key:")
        print("set ANTHROPIC_API_KEY=your_key_here")
        return 1
    
    print("="*70)
    print("Image Gallery Consistent Alt Text Generator")
    print("="*70)
    print("Generating the same alt text for each image across all configurations")
    print()
    
    generate_consistent_alt_text(jsondata_dir, api_key)
    
    print("\n" + "="*70)
    print("Consistent alt text generation complete!")
    print("="*70)
    print("\nAll JSON files now have consistent alt_text for each image.")
    print("The same image will have identical alt text regardless of AI configuration.")
    print("The website will provide a consistent accessibility experience.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())