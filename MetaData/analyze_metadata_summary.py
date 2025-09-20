#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Metadata Analysis Summary Script

This script creates a comprehensive summary of the metadata extraction results
to understand what information we can preserve during processing.
"""

import json
from pathlib import Path
from datetime import datetime
import re

def analyze_metadata_results(json_file):
    """Analyze the metadata extraction results and create a summary"""
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("=" * 80)
    print("COMPREHENSIVE METADATA ANALYSIS SUMMARY")
    print("=" * 80)
    
    total_files = len(data)
    image_files = 0
    video_files = 0
    error_files = 0
    
    # File type analysis
    heic_files = 0
    png_files = 0
    jpeg_files = 0
    mov_files = 0
    
    # Metadata availability analysis
    files_with_exif = 0
    files_with_gps = 0
    files_with_xmp = 0
    files_with_camera_info = 0
    
    # Date/time analysis
    creation_dates = []
    file_system_dates = []
    
    # Camera/device analysis
    cameras = set()
    
    # Video metadata analysis
    video_durations = []
    video_formats = []
    
    print(f"\n📊 PROCESSING {total_files} FILES...")
    
    for filename, metadata in data.items():
        # Basic file classification
        if 'error' in metadata:
            error_files += 1
            continue
            
        file_type = metadata.get('file_type', 'unknown')
        if file_type == 'image':
            image_files += 1
        elif file_type == 'video':
            video_files += 1
        
        # File extension analysis
        ext = Path(filename).suffix.lower()
        if ext == '.heic':
            heic_files += 1
        elif ext == '.png':
            png_files += 1
        elif ext in ['.jpg', '.jpeg']:
            jpeg_files += 1
        elif ext == '.mov':
            mov_files += 1
        
        # File system timestamps
        if 'file_info' in metadata:
            fs_info = metadata['file_info']
            if 'created_datetime' in fs_info:
                file_system_dates.append(fs_info['created_datetime'])
        
        # Image metadata analysis
        if 'image_metadata' in metadata:
            img_meta = metadata['image_metadata']
            
            # Check for EXIF data
            if 'exif' in img_meta and img_meta['exif']:
                files_with_exif += 1
                
                # Check for GPS
                if 'GPSInfo' in img_meta['exif']:
                    files_with_gps += 1
                
                # Check for camera info
                exif = img_meta['exif']
                if 'Make' in exif or 'Model' in exif:
                    files_with_camera_info += 1
                    make = exif.get('Make', 'Unknown')
                    model = exif.get('Model', '')
                    cameras.add(f"{make} {model}".strip())
                
                # Extract creation dates from EXIF
                if 'DateTime' in exif:
                    creation_dates.append(exif['DateTime'])
                elif 'DateTimeOriginal' in exif:
                    creation_dates.append(exif['DateTimeOriginal'])
            
            # Check for XMP data
            if 'pil_info' in img_meta and 'xmp' in img_meta['pil_info']:
                xmp_data = img_meta['pil_info']['xmp']
                if xmp_data and xmp_data != "b''":
                    files_with_xmp += 1
        
        # Video metadata analysis
        if 'video_metadata_opencv' in metadata:
            vid_meta = metadata['video_metadata_opencv']
            if 'opencv_info' in vid_meta:
                ov_info = vid_meta['opencv_info']
                if 'duration_seconds' in ov_info:
                    video_durations.append(ov_info['duration_seconds'])
                if 'fourcc_string' in ov_info:
                    video_formats.append(ov_info['fourcc_string'])
    
    # Print comprehensive summary
    print(f"\n🗂️  FILE TYPE BREAKDOWN:")
    print(f"   📷 Image files: {image_files}")
    print(f"     • HEIC files: {heic_files}")
    print(f"     • PNG files: {png_files}")
    print(f"     • JPEG files: {jpeg_files}")
    print(f"   🎬 Video files: {video_files}")
    print(f"     • MOV files: {mov_files}")
    print(f"   ❌ Files with errors: {error_files}")
    
    print(f"\n📋 METADATA AVAILABILITY:")
    print(f"   📸 Files with EXIF data: {files_with_exif}/{image_files} ({files_with_exif/image_files*100:.1f}%)")
    print(f"   🌍 Files with GPS data: {files_with_gps}/{image_files} ({files_with_gps/image_files*100:.1f}%)")
    print(f"   📝 Files with XMP data: {files_with_xmp}/{image_files} ({files_with_xmp/image_files*100:.1f}%)")
    print(f"   📱 Files with camera info: {files_with_camera_info}/{image_files} ({files_with_camera_info/image_files*100:.1f}%)")
    
    if cameras:
        print(f"\n📱 DETECTED CAMERAS/DEVICES:")
        for camera in sorted(cameras):
            print(f"   • {camera}")
    
    if creation_dates:
        print(f"\n📅 DATE RANGE ANALYSIS:")
        dates = sorted(creation_dates)
        print(f"   • Earliest photo: {dates[0]}")
        print(f"   • Latest photo: {dates[-1]}")
        print(f"   • Total photos with dates: {len(dates)}")
    
    if video_durations:
        print(f"\n🎬 VIDEO ANALYSIS:")
        avg_duration = sum(video_durations) / len(video_durations)
        total_duration = sum(video_durations)
        print(f"   • Total videos: {len(video_durations)}")
        print(f"   • Average duration: {avg_duration:.1f} seconds")
        print(f"   • Total video length: {total_duration:.1f} seconds ({total_duration/60:.1f} minutes)")
        print(f"   • Shortest video: {min(video_durations):.1f} seconds")
        print(f"   • Longest video: {max(video_durations):.1f} seconds")
    
    # What we would lose during conversion
    print(f"\n⚠️  METADATA THAT WOULD BE LOST:")
    print(f"   🗓️  Original file creation/modification dates (filesystem timestamps)")
    print(f"   📍 GPS coordinates from {files_with_gps} images")
    print(f"   📷 Camera settings and technical data from {files_with_exif} images")
    print(f"   🎬 Original video creation timestamps")
    print(f"   📝 XMP metadata from {files_with_xmp} images")
    print(f"   🔗 Relationship between paired HEIC/MOV files")
    
    # What we can preserve
    print(f"\n✅ METADATA WE CAN PRESERVE:")
    print(f"   📄 In detailed logs:")
    print(f"     • Original filenames and paths")
    print(f"     • File creation/modification timestamps")
    print(f"     • Complete EXIF data snapshots")
    print(f"     • XMP metadata")
    print(f"     • Video metadata (duration, format, dimensions)")
    print(f"     • Processing timestamps and settings")
    print(f"   🏷️  In converted files:")
    print(f"     • EXIF data (for HEIC→JPG conversion)")
    print(f"     • Image dimensions and basic properties")
    print(f"   📂 In organized file structure:")
    print(f"     • Grouped by original capture date")
    print(f"     • Preserved directory relationships")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    print(f"   1. 📋 Implement comprehensive metadata logging")
    print(f"   2. 🗓️  Preserve original file timestamps using os.utime()")
    print(f"   3. 🏷️  Include original timestamps in converted filenames")
    print(f"   4. 📦 Create sidecar metadata files for complex data")
    print(f"   5. 🔗 Maintain HEIC/MOV pairing information")
    print(f"   6. 📍 Extract and log GPS coordinates before conversion")
    
    print(f"\n" + "=" * 80)

def main():
    # Find the most recent metadata analysis file
    json_files = list(Path('.').glob('metadata_analysis_*.json'))
    if not json_files:
        print("No metadata analysis files found!")
        return
    
    latest_file = max(json_files, key=lambda f: f.stat().st_mtime)
    print(f"Analyzing: {latest_file}")
    
    analyze_metadata_results(latest_file)

if __name__ == "__main__":
    main()