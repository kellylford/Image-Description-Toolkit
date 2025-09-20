#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Metadata Extraction with Proper EXIF Parsing

This script extracts and properly parses all metadata including:
- Camera information (make, model, lens)
- GPS coordinates and location data
- Technical camera settings (ISO, aperture, shutter speed)
- Device-specific information
- Timestamps and creation context

Usage:
    python enhanced_metadata_extraction.py <directory_path>
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import base64

def setup_imports():
    """Setup and verify required imports"""
    imports = {}
    
    # PIL/Pillow for image metadata
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS, GPSTAGS
        imports['PIL'] = True
        print("✓ PIL/Pillow available for image metadata")
    except ImportError:
        imports['PIL'] = False
        print("✗ PIL/Pillow not available")
    
    # pillow-heif for HEIC metadata
    try:
        import pillow_heif
        pillow_heif.register_heif_opener()
        imports['pillow_heif'] = True
        print("✓ pillow-heif available for HEIC metadata")
    except ImportError:
        imports['pillow_heif'] = False
        print("✗ pillow-heif not available for HEIC metadata")
    
    # OpenCV for video metadata
    try:
        import cv2
        imports['cv2'] = True
        print("✓ OpenCV available for video metadata")
    except ImportError:
        imports['cv2'] = False
        print("✗ OpenCV not available for video metadata")
    
    # exifread for enhanced EXIF parsing
    try:
        import exifread
        imports['exifread'] = True
        print("✓ exifread available for enhanced EXIF parsing")
    except ImportError:
        imports['exifread'] = False
        print("✗ exifread not available (install with: pip install ExifRead)")
    
    return imports

def parse_gps_coordinates(gps_info: Dict) -> Optional[Dict[str, Any]]:
    """Parse GPS coordinates from EXIF GPS info"""
    try:
        def convert_to_degrees(value):
            """Convert GPS coordinates to decimal degrees"""
            if hasattr(value, 'values'):
                # Handle PIL GPS format
                d, m, s = value.values
                return d + (m / 60.0) + (s / 3600.0)
            else:
                # Handle string format
                return float(value)
        
        gps_data = {}
        
        # Latitude
        if 'GPSLatitude' in gps_info and 'GPSLatitudeRef' in gps_info:
            lat = convert_to_degrees(gps_info['GPSLatitude'])
            if gps_info['GPSLatitudeRef'] in ['S', 'South']:
                lat = -lat
            gps_data['latitude'] = lat
            gps_data['latitude_ref'] = gps_info['GPSLatitudeRef']
        
        # Longitude
        if 'GPSLongitude' in gps_info and 'GPSLongitudeRef' in gps_info:
            lon = convert_to_degrees(gps_info['GPSLongitude'])
            if gps_info['GPSLongitudeRef'] in ['W', 'West']:
                lon = -lon
            gps_data['longitude'] = lon
            gps_data['longitude_ref'] = gps_info['GPSLongitudeRef']
        
        # Altitude
        if 'GPSAltitude' in gps_info:
            altitude = float(gps_info['GPSAltitude'])
            if 'GPSAltitudeRef' in gps_info and gps_info['GPSAltitudeRef'] == 1:
                altitude = -altitude  # Below sea level
            gps_data['altitude'] = altitude
            gps_data['altitude_ref'] = gps_info.get('GPSAltitudeRef', 0)
        
        # Timestamp
        if 'GPSTimeStamp' in gps_info and 'GPSDateStamp' in gps_info:
            try:
                time_vals = gps_info['GPSTimeStamp'].values if hasattr(gps_info['GPSTimeStamp'], 'values') else gps_info['GPSTimeStamp']
                date_str = str(gps_info['GPSDateStamp'])
                time_str = f"{int(time_vals[0]):02d}:{int(time_vals[1]):02d}:{int(time_vals[2]):02d}"
                gps_data['timestamp'] = f"{date_str} {time_str}"
            except:
                pass
        
        # Speed and direction
        if 'GPSSpeed' in gps_info:
            gps_data['speed'] = float(gps_info['GPSSpeed'])
            gps_data['speed_ref'] = gps_info.get('GPSSpeedRef', 'K')  # K=km/h, M=mph, N=knots
        
        if 'GPSImgDirection' in gps_info:
            gps_data['direction'] = float(gps_info['GPSImgDirection'])
            gps_data['direction_ref'] = gps_info.get('GPSImgDirectionRef', 'T')  # T=true north, M=magnetic north
        
        return gps_data if gps_data else None
        
    except Exception as e:
        return {"error": f"GPS parsing failed: {str(e)}"}

def get_enhanced_image_metadata(file_path: Path, imports: Dict) -> Dict[str, Any]:
    """Extract comprehensive and properly parsed image metadata"""
    metadata = {}
    
    if not imports['PIL']:
        metadata['error'] = "PIL not available for image metadata"
        return metadata
    
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS, GPSTAGS
        
        with Image.open(file_path) as image:
            # Basic image info
            metadata['basic_info'] = {
                "format": image.format,
                "mode": image.mode,
                "size_pixels": image.size,
                "width": image.width,
                "height": image.height,
                "megapixels": round((image.width * image.height) / 1000000, 2),
                "has_transparency": image.mode in ('RGBA', 'LA') or 'transparency' in image.info
            }
            
            # Extract and parse EXIF data properly
            exif_data = {}
            camera_info = {}
            gps_info = {}
            technical_settings = {}
            
            if hasattr(image, '_getexif') and image._getexif() is not None:
                exif = image._getexif()
                
                for tag_id, value in exif.items():
                    tag = TAGS.get(tag_id, f"Unknown_{tag_id}")
                    
                    # Handle GPS info separately and parse it
                    if tag == "GPSInfo":
                        raw_gps = {}
                        for gps_tag_id, gps_value in value.items():
                            gps_tag = GPSTAGS.get(gps_tag_id, f"GPS_Unknown_{gps_tag_id}")
                            raw_gps[gps_tag] = gps_value
                        
                        # Parse GPS coordinates
                        parsed_gps = parse_gps_coordinates(raw_gps)
                        if parsed_gps:
                            gps_info = parsed_gps
                        gps_info['raw_gps_tags'] = {k: str(v) for k, v in raw_gps.items()}
                    
                    # Camera information
                    elif tag in ['Make', 'Model', 'Software', 'LensModel', 'LensMake']:
                        camera_info[tag.lower()] = str(value)
                    
                    # Technical camera settings
                    elif tag in ['ISO', 'ISOSpeedRatings', 'ExposureTime', 'FNumber', 'FocalLength', 
                               'Flash', 'WhiteBalance', 'ExposureMode', 'MeteringMode', 'SceneCaptureType']:
                        technical_settings[tag.lower()] = str(value)
                    
                    # Timestamps
                    elif tag in ['DateTime', 'DateTimeOriginal', 'DateTimeDigitized']:
                        exif_data[tag.lower()] = str(value)
                    
                    # Image orientation
                    elif tag == 'Orientation':
                        orientation_map = {
                            1: "Normal", 2: "Flipped horizontally", 3: "Rotated 180°",
                            4: "Flipped vertically", 5: "Rotated 90° CCW and flipped vertically",
                            6: "Rotated 90° CCW", 7: "Rotated 90° CW and flipped vertically",
                            8: "Rotated 90° CW"
                        }
                        exif_data['orientation'] = orientation_map.get(value, f"Unknown ({value})")
                        exif_data['orientation_value'] = value
                    
                    # Other important metadata
                    else:
                        try:
                            exif_data[tag] = str(value)
                        except:
                            exif_data[tag] = f"<non-serializable: {type(value)}>"
            
            metadata['exif'] = exif_data
            metadata['camera_info'] = camera_info
            metadata['gps_info'] = gps_info
            metadata['technical_settings'] = technical_settings
            
            # Enhanced XMP parsing
            xmp_data = {}
            if 'xmp' in image.info:
                try:
                    xmp_bytes = image.info['xmp']
                    xmp_string = xmp_bytes.decode('utf-8') if isinstance(xmp_bytes, bytes) else str(xmp_bytes)
                    
                    # Extract key XMP fields
                    import re
                    
                    # Creation dates
                    create_date = re.search(r'xmp:CreateDate[^>]*>([^<]+)', xmp_string)
                    if create_date:
                        xmp_data['create_date'] = create_date.group(1)
                    
                    modify_date = re.search(r'xmp:ModifyDate[^>]*>([^<]+)', xmp_string)
                    if modify_date:
                        xmp_data['modify_date'] = modify_date.group(1)
                    
                    # Creator tool
                    creator_tool = re.search(r'xmp:CreatorTool[^>]*>([^<]+)', xmp_string)
                    if creator_tool:
                        xmp_data['creator_tool'] = creator_tool.group(1)
                    
                    # Photoshop date created
                    ps_date = re.search(r'photoshop:DateCreated[^>]*>([^<]+)', xmp_string)
                    if ps_date:
                        xmp_data['photoshop_date_created'] = ps_date.group(1)
                    
                    # Store full XMP for reference (truncated)
                    xmp_data['full_xmp_preview'] = xmp_string[:500] + "..." if len(xmp_string) > 500 else xmp_string
                    
                except Exception as e:
                    xmp_data['parsing_error'] = str(e)
            
            metadata['xmp_parsed'] = xmp_data
            
            # Device identification
            device_info = {}
            if camera_info.get('make') and camera_info.get('model'):
                device_info['device_type'] = 'camera'
                device_info['full_name'] = f"{camera_info['make']} {camera_info['model']}"
                
                # Identify device categories
                make_lower = camera_info.get('make', '').lower()
                model_lower = camera_info.get('model', '').lower()
                
                if 'iphone' in model_lower:
                    device_info['category'] = 'smartphone'
                    device_info['brand'] = 'Apple'
                elif 'meta' in make_lower or 'ray-ban' in model_lower:
                    device_info['category'] = 'smart_glasses'
                    device_info['brand'] = 'Meta/Ray-Ban'
                elif any(brand in make_lower for brand in ['canon', 'nikon', 'sony', 'fuji']):
                    device_info['category'] = 'dslr_mirrorless'
                    device_info['brand'] = camera_info['make']
                else:
                    device_info['category'] = 'unknown'
                    device_info['brand'] = camera_info.get('make', 'Unknown')
            
            # Detect screenshots (typically have no camera info but specific dimensions)
            elif not camera_info and file_path.suffix.upper() == '.PNG':
                device_info['device_type'] = 'screenshot'
                device_info['category'] = 'screenshot'
                
                # Common screenshot dimensions
                width, height = image.size
                if width in [375, 414, 428, 390, 393] or height in [667, 736, 926, 844, 852]:
                    device_info['likely_source'] = 'iPhone screenshot'
                elif width in [360, 412, 393] or height in [640, 732, 851]:
                    device_info['likely_source'] = 'Android screenshot'
                else:
                    device_info['likely_source'] = 'Desktop/other screenshot'
            
            metadata['device_info'] = device_info
            
            # Color profile info
            try:
                if hasattr(image, 'icc_profile') and image.icc_profile:
                    metadata['color_profile'] = {
                        "has_icc_profile": True,
                        "icc_profile_size": len(image.icc_profile)
                    }
                else:
                    metadata['color_profile'] = {"has_icc_profile": False}
            except:
                metadata['color_profile'] = {"error": "Could not read color profile"}
                
    except Exception as e:
        metadata['error'] = f"Failed to extract image metadata: {str(e)}"
    
    return metadata

def get_enhanced_video_metadata(file_path: Path, imports: Dict) -> Dict[str, Any]:
    """Extract enhanced video metadata"""
    metadata = {}
    
    if imports['cv2']:
        try:
            import cv2
            
            cap = cv2.VideoCapture(str(file_path))
            
            if cap.isOpened():
                metadata['opencv_info'] = {
                    "frame_count": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
                    "fps": cap.get(cv2.CAP_PROP_FPS),
                    "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                    "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                    "fourcc": int(cap.get(cv2.CAP_PROP_FOURCC)),
                    "fourcc_string": "".join([chr((int(cap.get(cv2.CAP_PROP_FOURCC)) >> 8 * i) & 0xFF) for i in range(4)]),
                    "backend": cap.getBackendName() if hasattr(cap, 'getBackendName') else "unknown"
                }
                
                # Calculate duration
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                if fps > 0:
                    duration = frame_count / fps
                    metadata['opencv_info']['duration_seconds'] = duration
                    metadata['opencv_info']['duration_formatted'] = f"{int(duration//3600):02d}:{int((duration%3600)//60):02d}:{int(duration%60):02d}"
                
                cap.release()
        except Exception as e:
            metadata['opencv_error'] = str(e)
    
    return metadata

def analyze_file_enhanced(file_path: Path, imports: Dict) -> Dict[str, Any]:
    """Enhanced file analysis with proper metadata parsing"""
    print(f"Analyzing: {file_path.name}")
    
    metadata = {
        "file_info": {
            "file_size_bytes": file_path.stat().st_size,
            "file_size_mb": round(file_path.stat().st_size / (1024 * 1024), 2),
            "created_timestamp": file_path.stat().st_ctime,
            "created_datetime": datetime.fromtimestamp(file_path.stat().st_ctime).isoformat(),
            "modified_timestamp": file_path.stat().st_mtime,
            "modified_datetime": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
            "file_extension": file_path.suffix.lower(),
            "filename": file_path.name,
        },
        "analysis_timestamp": datetime.now().isoformat()
    }
    
    # Determine file type
    extension = file_path.suffix.lower()
    
    # Image formats
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif', '.webp', '.heic', '.heif'}
    video_extensions = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
    
    if extension in image_extensions:
        metadata['file_type'] = 'image'
        metadata['image_metadata'] = get_enhanced_image_metadata(file_path, imports)
    elif extension in video_extensions:
        metadata['file_type'] = 'video'
        metadata['video_metadata'] = get_enhanced_video_metadata(file_path, imports)
    else:
        metadata['file_type'] = 'unknown'
        metadata['note'] = f"Unknown file type: {extension}"
    
    return metadata

def generate_summary_report(results: Dict) -> Dict[str, Any]:
    """Generate enhanced summary report"""
    summary = {
        "total_files": len(results),
        "analysis_timestamp": datetime.now().isoformat(),
        "file_types": {},
        "device_categories": {},
        "gps_data_found": 0,
        "camera_info_found": 0,
        "screenshots_found": 0,
        "errors": 0
    }
    
    # Analyze results
    for file_data in results.values():
        if 'error' in file_data:
            summary['errors'] += 1
            continue
            
        file_type = file_data.get('file_type', 'unknown')
        summary['file_types'][file_type] = summary['file_types'].get(file_type, 0) + 1
        
        if file_type == 'image' and 'image_metadata' in file_data:
            img_meta = file_data['image_metadata']
            
            # Check for GPS data
            if img_meta.get('gps_info') and len(img_meta['gps_info']) > 1:  # More than just error
                summary['gps_data_found'] += 1
            
            # Check for camera info
            if img_meta.get('camera_info') and img_meta['camera_info']:
                summary['camera_info_found'] += 1
            
            # Check device categories
            if 'device_info' in img_meta and 'category' in img_meta['device_info']:
                category = img_meta['device_info']['category']
                summary['device_categories'][category] = summary['device_categories'].get(category, 0) + 1
                
                if category == 'screenshot':
                    summary['screenshots_found'] += 1
    
    return summary

def main():
    """Main function to analyze all files with enhanced metadata extraction"""
    print("=" * 70)
    print("ENHANCED METADATA EXTRACTION WITH PROPER EXIF PARSING")
    print("=" * 70)
    
    # Get directory from command line argument
    if len(sys.argv) > 1:
        test_dir = Path(sys.argv[1])
    else:
        print("Usage: python enhanced_metadata_extraction.py <directory_path>")
        print("Example: python enhanced_metadata_extraction.py /path/to/your/images")
        return
    
    if not test_dir.exists():
        print(f"❌ Directory not found: {test_dir}")
        return
    
    if not test_dir.is_dir():
        print(f"❌ Path is not a directory: {test_dir}")
        return
    
    print(f"📁 Analyzing directory: {test_dir}")
    print()
    
    # Setup imports
    print("🔧 Checking available libraries:")
    imports = setup_imports()
    print()
    
    # Find all files
    all_files = []
    for file_path in test_dir.rglob('*'):
        if file_path.is_file():
            all_files.append(file_path)
    
    if not all_files:
        print("❌ No files found in directory")
        return
    
    print(f"📊 Found {len(all_files)} files to analyze")
    print()
    
    # Analyze each file
    results = {}
    for i, file_path in enumerate(all_files, 1):
        print(f"[{i}/{len(all_files)}] ", end="")
        try:
            metadata = analyze_file_enhanced(file_path, imports)
            results[str(file_path.relative_to(test_dir))] = metadata
        except Exception as e:
            print(f"❌ Error analyzing {file_path.name}: {str(e)}")
            results[str(file_path.relative_to(test_dir))] = {
                "error": str(e),
                "analysis_timestamp": datetime.now().isoformat()
            }
    
    print()
    print("=" * 70)
    print("ENHANCED ANALYSIS COMPLETE")
    print("=" * 70)
    
    # Generate summary
    summary = generate_summary_report(results)
    
    # Save results
    output_file = Path(__file__).parent / f"enhanced_metadata_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({"summary": summary, "detailed_results": results}, f, indent=2, ensure_ascii=False)
        
        print(f"📄 Results saved to: {output_file}")
    except Exception as e:
        print(f"❌ Failed to save results: {str(e)}")
    
    # Print enhanced summary
    print()
    print("📊 ENHANCED SUMMARY:")
    print(f"   Total files analyzed: {summary['total_files']}")
    print(f"   Files with errors: {summary['errors']}")
    print()
    
    print("📁 File Types:")
    for file_type, count in summary['file_types'].items():
        print(f"   {file_type.title()}: {count}")
    print()
    
    print("📱 Device Categories:")
    for category, count in summary['device_categories'].items():
        print(f"   {category.replace('_', ' ').title()}: {count}")
    print()
    
    print("🔍 Metadata Findings:")
    print(f"   Files with GPS data: {summary['gps_data_found']}")
    print(f"   Files with camera info: {summary['camera_info_found']}")
    print(f"   Screenshots detected: {summary['screenshots_found']}")
    
    if summary['gps_data_found'] > 0:
        print(f"   📍 GPS coordinates found in {summary['gps_data_found']} files!")
    if summary['camera_info_found'] > 0:
        print(f"   📷 Camera information found in {summary['camera_info_found']} files!")
    
    print()
    print("🔍 Check the JSON file for detailed metadata with proper EXIF parsing!")
    print(f"📂 Output location: {output_file}")

if __name__ == "__main__":
    main()