#!/usr/bin/env python3
"""
Gallery Builder Script

Automatically prepares a gallery for deployment by:
1. Scanning the images/ directory for image files
2. Updating the hardcoded image list in index.html
3. Verifying JSON files have corresponding images
4. Creating a ready-to-deploy gallery

Usage:
    python build_gallery.py [gallery_directory]
    
Example:
    python build_gallery.py my-gallery/
    python build_gallery.py .  # Current directory
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import List, Set, Tuple

def find_image_files(images_dir: Path) -> List[str]:
    """
    Find all image files in the images directory.
    
    Args:
        images_dir: Path to the images directory
        
    Returns:
        Sorted list of image filenames
    """
    if not images_dir.exists():
        print(f"❌ Error: Images directory not found: {images_dir}")
        return []
    
    # Supported image extensions
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    
    image_files = []
    for file in images_dir.iterdir():
        if file.is_file() and file.suffix.lower() in image_extensions:
            image_files.append(file.name)
    
    # Sort for consistent ordering
    image_files.sort()
    
    return image_files

def update_index_html(index_path: Path, image_files: List[str]) -> bool:
    """
    Update the hardcoded image list in index.html.
    
    Args:
        index_path: Path to index.html
        image_files: List of image filenames
        
    Returns:
        True if successful, False otherwise
    """
    if not index_path.exists():
        print(f"❌ Error: index.html not found: {index_path}")
        return False
    
    # Read the current content
    try:
        with open(index_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ Error reading index.html: {e}")
        return False
    
    # Find the images array in the JavaScript
    # Look for: const images = [...]; or let images = [...]; or images = [...];
    pattern = r'((?:const|let|var)?\s*images\s*=\s*\[)[^\]]*(\];)'
    
    if not re.search(pattern, content):
        print(f"❌ Error: Could not find 'images = [...]' in index.html")
        print(f"   Make sure index.html has the hardcoded image array")
        return False
    
    # Build the new image array
    indent = ' ' * 16  # Indentation for array items
    image_list = ',\n'.join(f"{indent}'{img}'" for img in image_files)
    new_array = f"\\1\n{image_list}\n            \\2"
    
    # Replace the old array with the new one
    new_content = re.sub(pattern, new_array, content)
    
    # Write back
    try:
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    except Exception as e:
        print(f"❌ Error writing index.html: {e}")
        return False

def verify_json_files(jsondata_dir: Path, image_files: List[str]) -> Tuple[Set[str], Set[str]]:
    """
    Verify that JSON files reference the correct images.
    
    Args:
        jsondata_dir: Path to jsondata directory
        image_files: List of image filenames
        
    Returns:
        Tuple of (images_in_json, images_missing_from_json)
    """
    if not jsondata_dir.exists():
        return set(), set(image_files)
    
    images_in_json = set()
    
    for json_file in jsondata_dir.glob('*.json'):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Get image keys from the JSON
            if 'images' in data and isinstance(data['images'], dict):
                images_in_json.update(data['images'].keys())
        except Exception as e:
            print(f"⚠️  Warning: Could not read {json_file.name}: {e}")
    
    image_set = set(image_files)
    missing = image_set - images_in_json
    
    return images_in_json, missing

def verify_paths(gallery_dir: Path) -> bool:
    """
    Verify that index.html uses relative paths for images and JSON.
    
    Args:
        gallery_dir: Path to gallery directory
        
    Returns:
        True if paths are relative, False if issues found
    """
    index_path = gallery_dir / 'index.html'
    
    if not index_path.exists():
        return False
    
    try:
        with open(index_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ Error reading index.html: {e}")
        return False
    
    issues = []
    
    # Check for absolute paths (common mistakes)
    if re.search(r'["\'](?:/|[A-Z]:\\)[^"\']*(?:images|jsondata)', content):
        issues.append("Found absolute paths (should be relative: ./images/, ./jsondata/)")
    
    # Check for correct relative paths
    if './jsondata/' not in content and './gallery-data/' not in content:
        issues.append("Could not find './jsondata/' or './gallery-data/' path")
    
    if issues:
        print("⚠️  Path verification issues:")
        for issue in issues:
            print(f"   - {issue}")
        return False
    
    return True

def build_gallery(gallery_dir: str) -> bool:
    """
    Build and prepare a gallery for deployment.
    
    Args:
        gallery_dir: Path to gallery directory
        
    Returns:
        True if successful, False otherwise
    """
    gallery_path = Path(gallery_dir).resolve()
    
    print(f"🔨 Building gallery: {gallery_path.name}")
    print(f"   Location: {gallery_path}")
    print()
    
    # Check directory structure
    images_dir = gallery_path / 'images'
    jsondata_dir = gallery_path / 'jsondata'
    index_path = gallery_path / 'index.html'
    
    if not index_path.exists():
        print(f"❌ Error: index.html not found in {gallery_path}")
        print(f"   Make sure you're in a gallery directory (copied from template/)")
        return False
    
    # Step 1: Find images
    print("📁 Step 1: Scanning images directory...")
    image_files = find_image_files(images_dir)
    
    if not image_files:
        print(f"   ⚠️  No images found in {images_dir}")
        print(f"   Add your images to the images/ directory first")
        return False
    
    print(f"   ✅ Found {len(image_files)} images")
    for img in image_files[:5]:  # Show first 5
        print(f"      - {img}")
    if len(image_files) > 5:
        print(f"      ... and {len(image_files) - 5} more")
    print()
    
    # Step 2: Update index.html
    print("📝 Step 2: Updating index.html with image list...")
    if update_index_html(index_path, image_files):
        print(f"   ✅ Updated image array in index.html")
    else:
        print(f"   ❌ Failed to update index.html")
        return False
    print()
    
    # Step 3: Verify JSON files (if they exist)
    print("🔍 Step 3: Verifying JSON files...")
    if jsondata_dir.exists():
        images_in_json, missing = verify_json_files(jsondata_dir, image_files)
        
        json_count = len(list(jsondata_dir.glob('*.json')))
        print(f"   📊 Found {json_count} JSON config files")
        print(f"   📸 JSON files reference {len(images_in_json)} images")
        
        if missing:
            print(f"   ⚠️  Warning: {len(missing)} images not in JSON files:")
            for img in list(missing)[:5]:
                print(f"      - {img}")
            if len(missing) > 5:
                print(f"      ... and {len(missing) - 5} more")
            print(f"   💡 Run generate_descriptions.py to create descriptions")
        else:
            print(f"   ✅ All images have JSON entries")
    else:
        print(f"   ⚠️  No jsondata/ directory found")
        print(f"   💡 Run generate_descriptions.py to create JSON files")
    print()
    
    # Step 4: Verify paths
    print("🔗 Step 4: Verifying paths in index.html...")
    if verify_paths(gallery_path):
        print(f"   ✅ Paths are relative (good for deployment)")
    else:
        print(f"   ⚠️  Check paths in index.html")
    print()
    
    # Summary
    print("=" * 60)
    print("✅ Gallery build complete!")
    print()
    print(f"📦 Ready for deployment:")
    print(f"   - {len(image_files)} images in images/")
    print(f"   - Image list updated in index.html")
    if jsondata_dir.exists():
        json_count = len(list(jsondata_dir.glob('*.json')))
        print(f"   - {json_count} JSON config files")
    print()
    print(f"🧪 Test locally:")
    print(f"   cd {gallery_path}")
    print(f"   python -m http.server 8000")
    print(f"   Open: http://localhost:8000")
    print()
    print(f"🚀 Deploy:")
    print(f"   Upload index.html, images/, and jsondata/ to your server")
    print("=" * 60)
    
    return True

def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        gallery_dir = sys.argv[1]
    else:
        gallery_dir = '.'
    
    success = build_gallery(gallery_dir)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
