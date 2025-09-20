#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive Metadata Extraction Test Script

This script extracts all available metadata from images and videos
to understand what information is available before processing.

Usage:
    python test_metadata_extraction.py <directory_path>
    
Example:
    python test_metadata_extraction.py /path/to/your/images
    python test_metadata_extraction.py C:\\Users\\username\\Pictures
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

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
    
    # ffprobe for detailed video metadata
    try:
        import subprocess
        result = subprocess.run(['ffprobe', '-version'], capture_output=True, text=True)
        if result.returncode == 0:
            imports['ffprobe'] = True
            print("✓ ffprobe available for detailed video metadata")
        else:
            imports['ffprobe'] = False
            print("✗ ffprobe not available")
    except:
        imports['ffprobe'] = False
        print("✗ ffprobe not available")
    
    return imports

def get_file_system_metadata(file_path: Path) -> Dict[str, Any]:
    """Extract file system metadata"""
    try:
        stat = file_path.stat()
        return {
            "file_size_bytes": stat.st_size,
            "file_size_mb": round(stat.st_size / (1024 * 1024), 2),
            "created_timestamp": stat.st_ctime,
            "created_datetime": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified_timestamp": stat.st_mtime,
            "modified_datetime": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "accessed_timestamp": stat.st_atime,
            "accessed_datetime": datetime.fromtimestamp(stat.st_atime).isoformat(),
            "permissions": oct(stat.st_mode)[-3:],
            "file_extension": file_path.suffix.lower(),
            "filename": file_path.name,
            "absolute_path": str(file_path.absolute())
        }
    except Exception as e:
        return {"error": f"Failed to get file system metadata: {str(e)}"}

def get_image_metadata(file_path: Path, imports: Dict) -> Dict[str, Any]:
    """Extract comprehensive image metadata"""
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
            
            # EXIF data
            exif_data = {}
            if hasattr(image, '_getexif') and image._getexif() is not None:
                exif = image._getexif()
                for tag_id, value in exif.items():
                    tag = TAGS.get(tag_id, tag_id)
                    
                    # Handle GPS info separately
                    if tag == "GPSInfo":
                        gps_data = {}
                        for gps_tag_id, gps_value in value.items():
                            gps_tag = GPSTAGS.get(gps_tag_id, gps_tag_id)
                            gps_data[gps_tag] = str(gps_value)
                        exif_data['GPSInfo'] = gps_data
                    else:
                        # Convert to string to handle non-serializable types
                        exif_data[tag] = str(value)
            
            metadata['exif'] = exif_data
            
            # PIL info dictionary
            pil_info = {}
            for key, value in image.info.items():
                try:
                    pil_info[key] = str(value)
                except:
                    pil_info[key] = f"<non-serializable: {type(value)}>"
            
            metadata['pil_info'] = pil_info
            
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

def get_video_metadata_opencv(file_path: Path) -> Dict[str, Any]:
    """Extract video metadata using OpenCV"""
    metadata = {}
    
    try:
        import cv2
        
        cap = cv2.VideoCapture(str(file_path))
        
        if not cap.isOpened():
            metadata['error'] = "Could not open video with OpenCV"
            return metadata
        
        # Basic video properties
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
            metadata['opencv_info']['duration_seconds'] = frame_count / fps
            metadata['opencv_info']['duration_formatted'] = str(datetime.fromtimestamp(frame_count / fps).strftime('%H:%M:%S'))
        
        cap.release()
        
    except Exception as e:
        metadata['error'] = f"OpenCV video metadata extraction failed: {str(e)}"
    
    return metadata

def get_video_metadata_ffprobe(file_path: Path) -> Dict[str, Any]:
    """Extract detailed video metadata using ffprobe"""
    metadata = {}
    
    try:
        import subprocess
        
        # Run ffprobe to get JSON metadata
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            str(file_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            ffprobe_data = json.loads(result.stdout)
            
            # Extract format info
            if 'format' in ffprobe_data:
                format_info = ffprobe_data['format']
                metadata['format'] = {
                    "filename": format_info.get('filename'),
                    "format_name": format_info.get('format_name'),
                    "format_long_name": format_info.get('format_long_name'),
                    "duration": format_info.get('duration'),
                    "size": format_info.get('size'),
                    "bit_rate": format_info.get('bit_rate'),
                    "tags": format_info.get('tags', {})
                }
            
            # Extract stream info
            if 'streams' in ffprobe_data:
                metadata['streams'] = []
                for stream in ffprobe_data['streams']:
                    stream_info = {
                        "index": stream.get('index'),
                        "codec_name": stream.get('codec_name'),
                        "codec_long_name": stream.get('codec_long_name'),
                        "codec_type": stream.get('codec_type'),
                        "width": stream.get('width'),
                        "height": stream.get('height'),
                        "duration": stream.get('duration'),
                        "bit_rate": stream.get('bit_rate'),
                        "frame_rate": stream.get('r_frame_rate'),
                        "tags": stream.get('tags', {})
                    }
                    
                    # Add audio-specific info
                    if stream.get('codec_type') == 'audio':
                        stream_info.update({
                            "sample_rate": stream.get('sample_rate'),
                            "channels": stream.get('channels'),
                            "channel_layout": stream.get('channel_layout')
                        })
                    
                    metadata['streams'].append(stream_info)
        else:
            metadata['error'] = f"ffprobe failed: {result.stderr}"
            
    except subprocess.TimeoutExpired:
        metadata['error'] = "ffprobe timed out"
    except Exception as e:
        metadata['error'] = f"ffprobe metadata extraction failed: {str(e)}"
    
    return metadata

def analyze_file(file_path: Path, imports: Dict) -> Dict[str, Any]:
    """Analyze a single file and extract all possible metadata"""
    print(f"Analyzing: {file_path.name}")
    
    metadata = {
        "file_info": get_file_system_metadata(file_path),
        "analysis_timestamp": datetime.now().isoformat()
    }
    
    # Determine file type
    extension = file_path.suffix.lower()
    
    # Image formats
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif', '.webp', '.heic', '.heif'}
    video_extensions = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
    
    if extension in image_extensions:
        metadata['file_type'] = 'image'
        metadata['image_metadata'] = get_image_metadata(file_path, imports)
    elif extension in video_extensions:
        metadata['file_type'] = 'video'
        if imports['cv2']:
            metadata['video_metadata_opencv'] = get_video_metadata_opencv(file_path)
        if imports['ffprobe']:
            metadata['video_metadata_ffprobe'] = get_video_metadata_ffprobe(file_path)
    else:
        metadata['file_type'] = 'unknown'
        metadata['note'] = f"Unknown file type: {extension}"
    
    return metadata

def main():
    """Main function to analyze all files in the specified directory"""
    print("=" * 60)
    print("COMPREHENSIVE METADATA EXTRACTION TEST")
    print("=" * 60)
    
    # Get directory from command line argument or use default
    if len(sys.argv) > 1:
        test_dir = Path(sys.argv[1])
    else:
        print("Usage: python test_metadata_extraction.py <directory_path>")
        print("Example: python test_metadata_extraction.py /path/to/your/images")
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
            metadata = analyze_file(file_path, imports)
            results[str(file_path.relative_to(test_dir))] = metadata
        except Exception as e:
            print(f"❌ Error analyzing {file_path.name}: {str(e)}")
            results[str(file_path.relative_to(test_dir))] = {
                "error": str(e),
                "analysis_timestamp": datetime.now().isoformat()
            }
    
    print()
    print("=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)
    
    # Save results to JSON file
    output_file = Path(__file__).parent / f"metadata_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"📄 Results saved to: {output_file}")
    except Exception as e:
        print(f"❌ Failed to save results: {str(e)}")
    
    # Print summary
    print()
    print("📊 SUMMARY:")
    print(f"   Total files analyzed: {len(results)}")
    
    file_types = {}
    errors = 0
    
    for file_data in results.values():
        if 'error' in file_data:
            errors += 1
        else:
            file_type = file_data.get('file_type', 'unknown')
            file_types[file_type] = file_types.get(file_type, 0) + 1
    
    for file_type, count in file_types.items():
        print(f"   {file_type.title()} files: {count}")
    
    if errors > 0:
        print(f"   Files with errors: {errors}")
    
    print()
    print("🔍 Check the JSON file for detailed metadata extraction results!")
    print(f"📂 Output location: {output_file}")

if __name__ == "__main__":
    main()