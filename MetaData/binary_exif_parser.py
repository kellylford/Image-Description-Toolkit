#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Binary EXIF Parser for HEIC Files

This script properly parses binary EXIF data from HEIC files to extract:
- Camera make, model, and lens information
- GPS coordinates and location data  
- Technical camera settings (ISO, aperture, etc.)
- Device identification and categorization

Usage:
    python binary_exif_parser.py <directory_path>
"""

import os
import sys
import json
import io
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

def setup_imports():
    """Setup and verify required imports"""
    imports = {}
    
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS, GPSTAGS
        imports['PIL'] = True
        print("✓ PIL/Pillow available")
    except ImportError:
        imports['PIL'] = False
        print("✗ PIL/Pillow not available")
        return imports
    
    try:
        import pillow_heif
        pillow_heif.register_heif_opener()
        imports['pillow_heif'] = True
        print("✓ pillow-heif available")
    except ImportError:
        imports['pillow_heif'] = False
        print("✗ pillow-heif not available")
    
    try:
        import exifread
        imports['exifread'] = True
        print("✓ ExifRead available for binary EXIF parsing")
    except ImportError:
        imports['exifread'] = False
        print("✗ ExifRead not available")
    
    return imports

def parse_binary_exif(exif_bytes: bytes) -> Dict[str, Any]:
    """Parse binary EXIF data using ExifRead"""
    try:
        import exifread
        
        # Create a BytesIO object from the binary data
        exif_io = io.BytesIO(exif_bytes)
        
        # Parse EXIF data
        tags = exifread.process_file(exif_io, details=False)
        
        parsed_exif = {}
        camera_info = {}
        gps_info = {}
        technical_settings = {}
        
        for tag_name, tag_value in tags.items():
            try:
                value_str = str(tag_value)
                
                # Camera information
                if tag_name == 'Image Make':
                    camera_info['make'] = value_str
                elif tag_name == 'Image Model':
                    camera_info['model'] = value_str
                elif tag_name == 'Image Software':
                    camera_info['software'] = value_str
                elif tag_name == 'EXIF LensModel':
                    camera_info['lens_model'] = value_str
                elif tag_name == 'EXIF LensMake':
                    camera_info['lens_make'] = value_str
                
                # GPS information
                elif tag_name.startswith('GPS'):
                    gps_info[tag_name] = value_str
                
                # Technical camera settings
                elif tag_name in ['EXIF ISOSpeedRatings', 'EXIF ExposureTime', 'EXIF FNumber', 
                                'EXIF FocalLength', 'EXIF Flash', 'EXIF WhiteBalance',
                                'EXIF ExposureMode', 'EXIF MeteringMode', 'EXIF SceneCaptureType']:
                    technical_settings[tag_name.replace('EXIF ', '').lower()] = value_str
                
                # Timestamps and other EXIF data
                elif tag_name in ['Image DateTime', 'EXIF DateTimeOriginal', 'EXIF DateTimeDigitized',
                                'Image Orientation', 'EXIF ColorSpace', 'EXIF ExifImageWidth',
                                'EXIF ExifImageLength']:
                    parsed_exif[tag_name.lower().replace(' ', '_').replace('exif_', '').replace('image_', '')] = value_str
                
                # Store all tags for reference
                parsed_exif[f"raw_{tag_name.lower().replace(' ', '_')}"] = value_str
                
            except Exception as e:
                parsed_exif[f"error_{tag_name}"] = f"Parse error: {str(e)}"
        
        return {
            'parsed_exif': parsed_exif,
            'camera_info': camera_info,
            'gps_info': gps_info,
            'technical_settings': technical_settings
        }
        
    except Exception as e:
        return {'error': f"Binary EXIF parsing failed: {str(e)}"}

def convert_gps_to_decimal(gps_info: Dict[str, str]) -> Optional[Dict[str, float]]:
    """Convert GPS coordinates to decimal degrees"""
    try:
        result = {}
        
        # Parse latitude
        if 'GPS GPSLatitude' in gps_info and 'GPS GPSLatitudeRef' in gps_info:
            lat_str = gps_info['GPS GPSLatitude']
            lat_ref = gps_info['GPS GPSLatitudeRef']
            
            # Parse coordinate format: [DD, MM, SS]
            if '[' in lat_str and ']' in lat_str:
                coords = lat_str.strip('[]').split(', ')
                if len(coords) >= 3:
                    degrees = float(coords[0])
                    minutes = float(coords[1])
                    seconds = float(coords[2])
                    
                    decimal_lat = degrees + (minutes / 60.0) + (seconds / 3600.0)
                    if lat_ref in ['S', 'South']:
                        decimal_lat = -decimal_lat
                    
                    result['latitude'] = decimal_lat
                    result['latitude_ref'] = lat_ref
        
        # Parse longitude
        if 'GPS GPSLongitude' in gps_info and 'GPS GPSLongitudeRef' in gps_info:
            lon_str = gps_info['GPS GPSLongitude']
            lon_ref = gps_info['GPS GPSLongitudeRef']
            
            # Parse coordinate format: [DD, MM, SS]
            if '[' in lon_str and ']' in lon_str:
                coords = lon_str.strip('[]').split(', ')
                if len(coords) >= 3:
                    degrees = float(coords[0])
                    minutes = float(coords[1])
                    seconds = float(coords[2])
                    
                    decimal_lon = degrees + (minutes / 60.0) + (seconds / 3600.0)
                    if lon_ref in ['W', 'West']:
                        decimal_lon = -decimal_lon
                    
                    result['longitude'] = decimal_lon
                    result['longitude_ref'] = lon_ref
        
        # Parse altitude
        if 'GPS GPSAltitude' in gps_info:
            alt_str = gps_info['GPS GPSAltitude']
            try:
                # Handle fractional format like "123/10"
                if '/' in alt_str:
                    num, den = alt_str.split('/')
                    altitude = float(num) / float(den)
                else:
                    altitude = float(alt_str)
                
                result['altitude'] = altitude
                
                if 'GPS GPSAltitudeRef' in gps_info:
                    alt_ref = gps_info['GPS GPSAltitudeRef']
                    if alt_ref == '1':  # Below sea level
                        result['altitude'] = -result['altitude']
                    result['altitude_ref'] = alt_ref
                        
            except ValueError:
                pass
        
        return result if result else None
        
    except Exception as e:
        return {'error': f"GPS conversion failed: {str(e)}"}

def analyze_device_type(camera_info: Dict[str, str], file_extension: str) -> Dict[str, str]:
    """Analyze and categorize the device type"""
    device_info = {}
    
    make = camera_info.get('make', '').lower()
    model = camera_info.get('model', '').lower()
    
    if make and model:
        device_info['device_type'] = 'camera'
        device_info['full_name'] = f"{camera_info.get('make', '')} {camera_info.get('model', '')}"
        
        # Categorize device
        if 'iphone' in model:
            device_info['category'] = 'smartphone'
            device_info['brand'] = 'Apple'
            device_info['device_family'] = 'iPhone'
        elif 'meta' in make or 'ray-ban' in model or 'meta ai' in make:
            device_info['category'] = 'smart_glasses'
            device_info['brand'] = 'Meta/Ray-Ban'
            device_info['device_family'] = 'Ray-Ban Meta Smart Glasses'
        elif any(brand in make for brand in ['canon', 'nikon', 'sony', 'fuji', 'panasonic']):
            device_info['category'] = 'dslr_mirrorless'
            device_info['brand'] = camera_info.get('make', '')
        elif 'samsung' in make or 'galaxy' in model:
            device_info['category'] = 'smartphone'
            device_info['brand'] = 'Samsung'
        elif 'google' in make or 'pixel' in model:
            device_info['category'] = 'smartphone'
            device_info['brand'] = 'Google'
        else:
            device_info['category'] = 'unknown_camera'
            device_info['brand'] = camera_info.get('make', 'Unknown')
    
    elif file_extension.lower() == '.png':
        device_info['device_type'] = 'screenshot'
        device_info['category'] = 'screenshot'
        device_info['brand'] = 'Unknown'
    
    else:
        device_info['device_type'] = 'unknown'
        device_info['category'] = 'unknown'
        device_info['brand'] = 'Unknown'
    
    return device_info

def analyze_image_with_binary_exif(file_path: Path, imports: Dict) -> Dict[str, Any]:
    """Analyze image with proper binary EXIF parsing"""
    metadata = {
        "file_info": {
            "filename": file_path.name,
            "file_extension": file_path.suffix.lower(),
            "file_size_mb": round(file_path.stat().st_size / (1024 * 1024), 2),
        },
        "analysis_timestamp": datetime.now().isoformat()
    }
    
    if not imports['PIL']:
        metadata['error'] = "PIL not available"
        return metadata
    
    try:
        from PIL import Image
        
        with Image.open(file_path) as image:
            # Basic image info
            metadata['basic_info'] = {
                "format": image.format,
                "size_pixels": [image.width, image.height],
                "megapixels": round((image.width * image.height) / 1000000, 2),
            }
            
            # Extract binary EXIF data
            if 'exif' in image.info and imports['exifread']:
                binary_exif = image.info['exif']
                if isinstance(binary_exif, bytes) and len(binary_exif) > 0:
                    exif_data = parse_binary_exif(binary_exif)
                    
                    metadata['camera_info'] = exif_data.get('camera_info', {})
                    metadata['gps_info_raw'] = exif_data.get('gps_info', {})
                    metadata['technical_settings'] = exif_data.get('technical_settings', {})
                    metadata['exif_parsed'] = exif_data.get('parsed_exif', {})
                    
                    # Convert GPS to decimal coordinates
                    if metadata['gps_info_raw']:
                        gps_decimal = convert_gps_to_decimal(metadata['gps_info_raw'])
                        if gps_decimal:
                            metadata['gps_coordinates'] = gps_decimal
                    
                    # Analyze device type
                    metadata['device_info'] = analyze_device_type(metadata['camera_info'], file_path.suffix)
                    
                else:
                    metadata['note'] = "No binary EXIF data found"
                    metadata['camera_info'] = {}
                    metadata['gps_info_raw'] = {}
                    metadata['technical_settings'] = {}
                    metadata['device_info'] = analyze_device_type({}, file_path.suffix)
            else:
                metadata['note'] = "No EXIF data or ExifRead not available"
                metadata['camera_info'] = {}
                metadata['gps_info_raw'] = {}
                metadata['technical_settings'] = {}
                metadata['device_info'] = analyze_device_type({}, file_path.suffix)
            
            # Enhanced XMP parsing
            if 'xmp' in image.info:
                xmp_bytes = image.info['xmp']
                xmp_string = xmp_bytes.decode('utf-8') if isinstance(xmp_bytes, bytes) else str(xmp_bytes)
                
                import re
                xmp_data = {}
                
                # Extract key XMP fields
                create_date = re.search(r'xmp:CreateDate[^>]*>([^<]+)', xmp_string)
                if create_date:
                    xmp_data['create_date'] = create_date.group(1)
                
                creator_tool = re.search(r'xmp:CreatorTool[^>]*>([^<]+)', xmp_string)
                if creator_tool:
                    xmp_data['creator_tool'] = creator_tool.group(1)
                
                metadata['xmp_parsed'] = xmp_data
            
    except Exception as e:
        metadata['error'] = f"Image analysis failed: {str(e)}"
    
    return metadata

def main():
    """Main function to analyze files with proper binary EXIF parsing"""
    print("=" * 70)
    print("BINARY EXIF PARSER FOR CAMERA & GPS METADATA")
    print("=" * 70)
    
    # Get directory from command line
    if len(sys.argv) > 1:
        test_dir = Path(sys.argv[1])
    else:
        print("Usage: python binary_exif_parser.py <directory_path>")
        return
    
    if not test_dir.exists():
        print(f"❌ Directory not found: {test_dir}")
        return
    
    print(f"📁 Directory: {test_dir}")
    print()
    
    # Setup imports
    imports = setup_imports()
    if not imports['PIL'] or not imports['exifread']:
        print("❌ Required libraries not available")
        return
    
    print()
    
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
    
    # Analyze sample files (first 20 for speed)
    sample_files = image_files[:20]
    results = {}
    
    camera_devices = set()
    gps_found = 0
    device_categories = {}
    
    for i, file_path in enumerate(sample_files, 1):
        print(f"[{i}/{len(sample_files)}] Analyzing: {file_path.name}")
        
        try:
            metadata = analyze_image_with_binary_exif(file_path, imports)
            results[file_path.name] = metadata
            
            # Collect statistics
            if metadata.get('camera_info') and metadata['camera_info']:
                if 'make' in metadata['camera_info'] and 'model' in metadata['camera_info']:
                    device_name = f"{metadata['camera_info']['make']} {metadata['camera_info']['model']}"
                    camera_devices.add(device_name)
            
            if metadata.get('gps_coordinates') and len(metadata['gps_coordinates']) > 1:
                gps_found += 1
            
            if metadata.get('device_info') and 'category' in metadata['device_info']:
                category = metadata['device_info']['category']
                device_categories[category] = device_categories.get(category, 0) + 1
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            results[file_path.name] = {"error": str(e)}
    
    print()
    print("=" * 70)
    print("BINARY EXIF ANALYSIS COMPLETE")
    print("=" * 70)
    
    # Generate comprehensive summary
    summary = {
        "total_analyzed": len(sample_files),
        "camera_devices_found": list(camera_devices),
        "files_with_gps": gps_found,
        "device_categories": device_categories,
        "analysis_timestamp": datetime.now().isoformat()
    }
    
    # Save results
    output_data = {
        "summary": summary,
        "sample_results": results
    }
    
    output_file = Path(__file__).parent / f"binary_exif_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"📄 Results saved to: {output_file}")
    except Exception as e:
        print(f"❌ Failed to save: {str(e)}")
    
    # Print findings
    print()
    print("🔍 FINDINGS:")
    print(f"   Files analyzed: {len(sample_files)}")
    print(f"   Camera devices detected: {len(camera_devices)}")
    
    for device in sorted(camera_devices):
        print(f"     • {device}")
    
    print(f"   Files with GPS coordinates: {gps_found}")
    
    print(f"   Device categories:")
    for category, count in device_categories.items():
        print(f"     • {category.replace('_', ' ').title()}: {count}")
    
    if gps_found > 0:
        print(f"\n📍 GPS DATA FOUND! {gps_found} files contain location information")
    
    if camera_devices:
        print(f"\n📷 CAMERA INFO FOUND! Detected {len(camera_devices)} different devices")
    
    print(f"\n📂 Full results: {output_file}")

if __name__ == "__main__":
    main()