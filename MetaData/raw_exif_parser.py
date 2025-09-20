#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Raw Binary EXIF Parser for HEIC Files

This script manually parses the raw binary EXIF data to extract camera and GPS information
that standard libraries can't parse from HEIC files.

Usage:
    python raw_exif_parser.py <directory_path>
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

def extract_camera_info_from_binary(exif_bytes: bytes) -> Dict[str, str]:
    """Extract camera information from binary EXIF data using string pattern matching"""
    if not exif_bytes:
        return {}
    
    try:
        # Convert bytes to string, ignoring decode errors
        exif_str = exif_bytes.decode('latin-1', errors='ignore')
        
        camera_info = {}
        
        # Look for common camera manufacturers and models
        patterns = {
            'apple_iphone': r'(iPhone\s+[^\\x00]*?)[\x00]',
            'apple_make': r'Apple[\x00]',
            'meta_ai': r'Meta\s+AI[\x00]',
            'ray_ban': r'Ray-Ban\s+Meta\s+Smart\s+Glasses[\x00]',
            'canon': r'Canon[\x00]',
            'nikon': r'Nikon[\x00]',
            'sony': r'Sony[\x00]',
            'samsung': r'Samsung[\x00]',
            # Software versions
            'ios_version': r'(\d+\.\d+)[\x00]',
            'datetime': r'(\d{4}:\d{2}:\d{2}\s+\d{2}:\d{2}:\d{2})[\x00]'
        }
        
        # Extract information using patterns
        for key, pattern in patterns.items():
            matches = re.findall(pattern, exif_str, re.IGNORECASE)
            if matches:
                if key == 'apple_iphone':
                    camera_info['model'] = matches[0].strip()
                    camera_info['make'] = 'Apple'
                elif key == 'apple_make':
                    camera_info['make'] = 'Apple'
                elif key == 'meta_ai':
                    camera_info['make'] = 'Meta AI'
                elif key == 'ray_ban':
                    camera_info['model'] = 'Ray-Ban Meta Smart Glasses'
                    camera_info['make'] = 'Meta AI'
                elif key in ['canon', 'nikon', 'sony', 'samsung']:
                    camera_info['make'] = key.title()
                elif key == 'ios_version':
                    camera_info['software'] = matches[0]
                elif key == 'datetime':
                    camera_info['datetime_original'] = matches[0]
        
        # Look for specific iPhone models
        iphone_models = [
            'iPhone 15 Pro Max', 'iPhone 15 Pro', 'iPhone 15 Plus', 'iPhone 15',
            'iPhone 14 Pro Max', 'iPhone 14 Pro', 'iPhone 14 Plus', 'iPhone 14',
            'iPhone 13 Pro Max', 'iPhone 13 Pro', 'iPhone 13 mini', 'iPhone 13',
            'iPhone 12 Pro Max', 'iPhone 12 Pro', 'iPhone 12 mini', 'iPhone 12',
            'iPhone 11 Pro Max', 'iPhone 11 Pro', 'iPhone 11'
        ]
        
        for model in iphone_models:
            if model.encode('latin-1') in exif_bytes:
                camera_info['model'] = model
                camera_info['make'] = 'Apple'
                break
        
        # Look for lens information
        lens_patterns = [
            r'(iPhone\s+\d+[^\\x00]*?camera[^\\x00]*?)[\x00]',
            r'([^\\x00]*?mm\s+f/[^\\x00]*?)[\x00]'
        ]
        
        for pattern in lens_patterns:
            matches = re.findall(pattern, exif_str, re.IGNORECASE)
            if matches:
                camera_info['lens_model'] = matches[0].strip()
                break
        
        return camera_info
        
    except Exception as e:
        return {'parsing_error': str(e)}

def extract_gps_from_binary(exif_bytes: bytes) -> Dict[str, Any]:
    """Extract GPS information from binary EXIF data"""
    if not exif_bytes:
        return {}
    
    try:
        # Look for GPS coordinate patterns in binary data
        gps_info = {}
        
        # Convert to string for pattern matching
        exif_str = exif_bytes.decode('latin-1', errors='ignore')
        
        # Look for GPS patterns (this is simplified - real GPS data is more complex)
        # Most consumer photos don't have GPS unless specifically enabled
        
        # Check for GPS-related strings
        gps_indicators = ['GPS', 'coordinates', 'latitude', 'longitude']
        has_gps_indicators = any(indicator.lower() in exif_str.lower() for indicator in gps_indicators)
        
        if has_gps_indicators:
            gps_info['potential_gps_data'] = True
            gps_info['note'] = 'GPS indicators found but coordinates need specialized parsing'
        else:
            gps_info['gps_present'] = False
            gps_info['note'] = 'No GPS indicators found in EXIF data'
        
        return gps_info
        
    except Exception as e:
        return {'gps_parsing_error': str(e)}

def detect_device_category(camera_info: Dict[str, str], filename: str) -> Dict[str, str]:
    """Detect device category based on camera info and filename patterns"""
    device_info = {}
    
    make = camera_info.get('make', '').lower()
    model = camera_info.get('model', '').lower()
    
    # Device categorization
    if 'iphone' in model:
        device_info.update({
            'category': 'smartphone',
            'brand': 'Apple',
            'device_family': 'iPhone',
            'device_type': 'camera'
        })
    elif 'meta ai' in make or 'ray-ban' in model:
        device_info.update({
            'category': 'smart_glasses',
            'brand': 'Meta/Ray-Ban',
            'device_family': 'Ray-Ban Meta Smart Glasses',
            'device_type': 'camera'
        })
    elif any(brand in make for brand in ['canon', 'nikon', 'sony', 'fuji']):
        device_info.update({
            'category': 'dslr_mirrorless',
            'brand': camera_info.get('make', ''),
            'device_type': 'camera'
        })
    elif filename.startswith('IMG_') and filename.endswith('.PNG'):
        device_info.update({
            'category': 'screenshot',
            'device_type': 'screenshot',
            'likely_source': 'iPhone screenshot' if len(camera_info) == 0 else 'Unknown screenshot'
        })
    elif not camera_info or (not make and not model):
        device_info.update({
            'category': 'unknown',
            'device_type': 'unknown',
            'note': 'No camera information found'
        })
    else:
        device_info.update({
            'category': 'unknown_camera',
            'device_type': 'camera',
            'brand': camera_info.get('make', 'Unknown')
        })
    
    return device_info

def analyze_image_raw_exif(file_path: Path) -> Dict[str, Any]:
    """Analyze image using raw binary EXIF parsing"""
    try:
        from PIL import Image
        import pillow_heif
        
        # Register HEIF opener
        pillow_heif.register_heif_opener()
        
        metadata = {
            "filename": file_path.name,
            "file_extension": file_path.suffix.lower(),
            "file_size_mb": round(file_path.stat().st_size / (1024 * 1024), 2),
            "analysis_timestamp": datetime.now().isoformat()
        }
        
        with Image.open(file_path) as image:
            # Basic image info
            metadata['basic_info'] = {
                "format": image.format,
                "size_pixels": [image.width, image.height],
                "megapixels": round((image.width * image.height) / 1000000, 2),
            }
            
            # Extract raw binary EXIF data
            if 'exif' in image.info:
                exif_bytes = image.info['exif']
                if isinstance(exif_bytes, bytes) and len(exif_bytes) > 0:
                    # Parse camera information
                    camera_info = extract_camera_info_from_binary(exif_bytes)
                    metadata['camera_info'] = camera_info
                    
                    # Parse GPS information
                    gps_info = extract_gps_from_binary(exif_bytes)
                    metadata['gps_info'] = gps_info
                    
                    # Detect device category
                    device_info = detect_device_category(camera_info, file_path.name)
                    metadata['device_info'] = device_info
                    
                    # Store binary EXIF length for reference
                    metadata['exif_binary_length'] = len(exif_bytes)
                    
                    # Store first 200 characters of EXIF as preview (for debugging)
                    try:
                        exif_preview = exif_bytes.decode('latin-1', errors='ignore')[:200]
                        metadata['exif_preview'] = repr(exif_preview)
                    except:
                        metadata['exif_preview'] = "Could not decode for preview"
                        
                else:
                    metadata['note'] = "No binary EXIF data found"
                    metadata['camera_info'] = {}
                    metadata['gps_info'] = {}
                    metadata['device_info'] = detect_device_category({}, file_path.name)
            else:
                metadata['note'] = "No EXIF data in image.info"
                metadata['camera_info'] = {}
                metadata['gps_info'] = {}
                metadata['device_info'] = detect_device_category({}, file_path.name)
            
            # Parse XMP data if available
            if 'xmp' in image.info:
                xmp_bytes = image.info['xmp']
                try:
                    xmp_string = xmp_bytes.decode('utf-8') if isinstance(xmp_bytes, bytes) else str(xmp_bytes)
                    
                    # Extract creation date from XMP
                    import re
                    create_date = re.search(r'xmp:CreateDate[^>]*>([^<]+)', xmp_string)
                    if create_date:
                        metadata['xmp_create_date'] = create_date.group(1)
                except:
                    metadata['xmp_parsing_error'] = "Could not parse XMP data"
        
        return metadata
        
    except Exception as e:
        return {
            "filename": file_path.name,
            "error": f"Analysis failed: {str(e)}",
            "analysis_timestamp": datetime.now().isoformat()
        }

def main():
    """Main function to analyze files with raw binary EXIF parsing"""
    print("=" * 70)
    print("RAW BINARY EXIF PARSER FOR HEIC FILES")
    print("=" * 70)
    
    # Get directory from command line
    if len(sys.argv) > 1:
        test_dir = Path(sys.argv[1])
    else:
        print("Usage: python raw_exif_parser.py <directory_path>")
        return
    
    if not test_dir.exists():
        print(f"❌ Directory not found: {test_dir}")
        return
    
    print(f"📁 Directory: {test_dir}")
    print()
    
    # Check dependencies
    try:
        from PIL import Image
        import pillow_heif
        print("✓ PIL and pillow-heif available")
    except ImportError as e:
        print(f"❌ Required libraries not available: {e}")
        return
    
    # Find image files
    image_extensions = {'.jpg', '.jpeg', '.png', '.heic', '.heif'}
    image_files = []
    
    for file_path in test_dir.rglob('*'):
        if file_path.is_file() and file_path.suffix.lower() in image_extensions:
            image_files.append(file_path)
    
    if not image_files:
        print("❌ No image files found")
        return
    
    print(f"📊 Found {len(image_files)} image files")
    print()
    
    # Analyze sample files (first 50 for comprehensive analysis)
    sample_files = image_files[:50]
    results = {}
    
    # Statistics
    camera_devices = {}
    device_categories = {}
    files_with_gps = 0
    exif_data_found = 0
    
    for i, file_path in enumerate(sample_files, 1):
        print(f"[{i}/{len(sample_files)}] Analyzing: {file_path.name}")
        
        try:
            metadata = analyze_image_raw_exif(file_path)
            results[file_path.name] = metadata
            
            # Collect statistics
            if 'camera_info' in metadata and metadata['camera_info']:
                camera_info = metadata['camera_info']
                if 'make' in camera_info and 'model' in camera_info:
                    device_key = f"{camera_info['make']} {camera_info['model']}"
                    camera_devices[device_key] = camera_devices.get(device_key, 0) + 1
                elif 'make' in camera_info:
                    device_key = camera_info['make']
                    camera_devices[device_key] = camera_devices.get(device_key, 0) + 1
            
            if 'device_info' in metadata and 'category' in metadata['device_info']:
                category = metadata['device_info']['category']
                device_categories[category] = device_categories.get(category, 0) + 1
            
            if 'gps_info' in metadata and metadata['gps_info'].get('potential_gps_data'):
                files_with_gps += 1
            
            if 'exif_binary_length' in metadata and metadata['exif_binary_length'] > 0:
                exif_data_found += 1
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            results[file_path.name] = {"error": str(e)}
    
    print()
    print("=" * 70)
    print("RAW BINARY EXIF ANALYSIS COMPLETE")
    print("=" * 70)
    
    # Generate summary
    summary = {
        "total_analyzed": len(sample_files),
        "files_with_exif_data": exif_data_found,
        "camera_devices_detected": camera_devices,
        "device_categories": device_categories,
        "files_with_potential_gps": files_with_gps,
        "analysis_timestamp": datetime.now().isoformat()
    }
    
    # Save results
    output_data = {
        "summary": summary,
        "detailed_results": results
    }
    
    output_file = Path(__file__).parent / f"raw_exif_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"📄 Results saved to: {output_file}")
    except Exception as e:
        print(f"❌ Failed to save: {str(e)}")
    
    # Print comprehensive findings
    print()
    print("🔍 COMPREHENSIVE FINDINGS:")
    print(f"   Files analyzed: {len(sample_files)}")
    print(f"   Files with EXIF data: {exif_data_found}")
    print()
    
    print("📷 CAMERA DEVICES DETECTED:")
    if camera_devices:
        for device, count in sorted(camera_devices.items()):
            print(f"     • {device}: {count} files")
    else:
        print("     No camera devices detected")
    
    print()
    print("📱 DEVICE CATEGORIES:")
    for category, count in sorted(device_categories.items()):
        print(f"     • {category.replace('_', ' ').title()}: {count} files")
    
    print()
    if files_with_gps > 0:
        print(f"📍 GPS: Potential GPS data found in {files_with_gps} files")
    else:
        print("📍 GPS: No GPS data detected")
    
    print()
    print("🎯 KEY INSIGHTS:")
    if camera_devices:
        total_devices = len(camera_devices)
        print(f"   • Successfully identified {total_devices} different camera devices")
        
        # Identify most common devices
        most_common = sorted(camera_devices.items(), key=lambda x: x[1], reverse=True)
        if most_common:
            print(f"   • Most common device: {most_common[0][0]} ({most_common[0][1]} files)")
    
    smartphone_count = device_categories.get('smartphone', 0)
    smart_glasses_count = device_categories.get('smart_glasses', 0)
    screenshot_count = device_categories.get('screenshot', 0)
    
    if smartphone_count > 0:
        print(f"   • iPhone photos detected: {smartphone_count} files")
    if smart_glasses_count > 0:
        print(f"   • Ray-Ban Meta Smart Glasses photos: {smart_glasses_count} files")
    if screenshot_count > 0:
        print(f"   • Screenshots detected: {screenshot_count} files")
    
    print(f"\n📂 Full analysis: {output_file}")

if __name__ == "__main__":
    main()