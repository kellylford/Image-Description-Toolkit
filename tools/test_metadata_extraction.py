#!/usr/bin/env python3
"""
Test script to demonstrate metadata extraction behavior
Shows why some images have metadata while others don't
"""

import sys
from pathlib import Path
from PIL import Image
from PIL.ExifTags import TAGS
import json

def test_image_metadata(image_path):
    """Test metadata extraction for a single image"""
    print(f"\n=== Testing: {image_path.name} ===")
    
    try:
        with Image.open(image_path) as img:
            print(f"Format: {img.format}")
            print(f"Size: {img.size}")
            print(f"Mode: {img.mode}")
            
            # Check for EXIF data
            exif_data = img.getexif()
            
            if not exif_data:
                print("❌ No EXIF data found")
                print("   This is normal for:")
                print("   - Screenshots")
                print("   - Web images")
                print("   - Processed/edited images")
                print("   - Some PNG files")
                return
            
            print(f"✅ Found {len(exif_data)} EXIF entries")
            
            # Convert to readable format
            exif_dict = {}
            for tag_id, value in exif_data.items():
                tag = TAGS.get(tag_id, tag_id)
                exif_dict[tag] = value
            
            # Show key metadata fields
            key_fields = ['DateTime', 'DateTimeOriginal', 'Make', 'Model', 'Software', 'GPSInfo']
            found_fields = []
            
            for field in key_fields:
                if field in exif_dict:
                    found_fields.append(field)
                    print(f"   {field}: {exif_dict[field]}")
            
            if not found_fields:
                print("   No standard metadata fields found (unusual)")
            else:
                print(f"   Found {len(found_fields)} standard metadata fields")
                
    except Exception as e:
        print(f"❌ Error reading image: {e}")

def main():
    """Test metadata extraction on images"""
    if len(sys.argv) < 2:
        print("Usage: python test_metadata_extraction.py <image_path_or_directory>")
        print("\nThis script shows why some images have metadata while others don't.")
        print("Common reasons for missing metadata:")
        print("- Screenshots have no EXIF data")
        print("- Web images often have EXIF stripped")
        print("- Edited images may lose metadata")
        print("- Some formats (PNG) rarely have EXIF")
        return
    
    target_path = Path(sys.argv[1])
    
    if not target_path.exists():
        print(f"Error: Path does not exist: {target_path}")
        return
    
    if target_path.is_file():
        # Test single image
        test_image_metadata(target_path)
    else:
        # Test directory
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
        image_files = [f for f in target_path.iterdir() 
                      if f.suffix.lower() in image_extensions]
        
        if not image_files:
            print(f"No image files found in {target_path}")
            return
        
        print(f"Testing {len(image_files)} images in {target_path}")
        
        with_metadata = 0
        without_metadata = 0
        
        for image_file in sorted(image_files):
            test_image_metadata(image_file)
            
            # Quick check for summary
            try:
                with Image.open(image_file) as img:
                    if img.getexif():
                        with_metadata += 1
                    else:
                        without_metadata += 1
            except:
                without_metadata += 1
        
        print(f"\n=== SUMMARY ===")
        print(f"Images with metadata: {with_metadata}")
        print(f"Images without metadata: {without_metadata}")
        print(f"Total images: {len(image_files)}")
        
        if without_metadata > 0:
            print(f"\n{without_metadata} images have no metadata - this is normal!")
            print("Common sources of images without metadata:")
            print("- Screenshots from any device")
            print("- Images downloaded from websites")
            print("- Images processed by photo editing software")
            print("- Images shared through messaging apps")

if __name__ == "__main__":
    main()