#!/usr/bin/env python3
"""
Video Metadata Extractor for IDT
Extracts GPS, date, and camera metadata from video files using ffprobe
Designed to work alongside image metadata extraction for frame embedding
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


class VideoMetadataExtractor:
    """Extract metadata from video files using ffprobe"""
    
    def __init__(self):
        self.supported_formats = {'.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm', '.m4v'}
        self.ffprobe_available = self._check_ffprobe()
    
    def _check_ffprobe(self) -> bool:
        """Check if ffprobe is available"""
        try:
            result = subprocess.run(
                ['ffprobe', '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def is_supported_video(self, file_path: Path) -> bool:
        """Check if file is a supported video format"""
        return file_path.suffix.lower() in self.supported_formats
    
    def extract_metadata(self, video_path: Path) -> Optional[Dict[str, Any]]:
        """
        Extract metadata from video file using ffprobe.
        
        Returns dict with:
        - gps: {latitude, longitude, altitude} if available
        - datetime: datetime object if available
        - camera: {make, model} if available
        - format_info: basic video info
        
        Returns None if extraction fails or ffprobe unavailable.
        """
        if not self.ffprobe_available:
            return None
        
        if not video_path.exists() or not self.is_supported_video(video_path):
            return None
        
        try:
            # Run ffprobe to get JSON metadata
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                str(video_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return None
            
            ffprobe_data = json.loads(result.stdout)
            metadata = {}
            
            # Extract format tags (where GPS/date usually live)
            format_tags = {}
            if 'format' in ffprobe_data and 'tags' in ffprobe_data['format']:
                format_tags = ffprobe_data['format']['tags']
            
            # Extract stream tags (backup location)
            stream_tags = {}
            if 'streams' in ffprobe_data:
                for stream in ffprobe_data['streams']:
                    if 'tags' in stream:
                        stream_tags.update(stream['tags'])
            
            # Combine tags (format takes precedence)
            all_tags = {**stream_tags, **format_tags}
            
            # Convert tag keys to lowercase for easier matching
            tags_lower = {k.lower(): v for k, v in all_tags.items()}
            
            # Extract GPS coordinates
            gps_data = self._extract_gps(tags_lower)
            if gps_data:
                metadata['gps'] = gps_data
            
            # Extract datetime
            dt = self._extract_datetime(tags_lower)
            if dt:
                metadata['datetime'] = dt
            
            # Extract camera info
            camera = self._extract_camera_info(tags_lower)
            if camera:
                metadata['camera'] = camera
            
            # Add basic format info
            if 'format' in ffprobe_data:
                fmt = ffprobe_data['format']
                metadata['format_info'] = {
                    'duration': float(fmt.get('duration', 0)),
                    'size': int(fmt.get('size', 0)),
                    'format_name': fmt.get('format_name', 'unknown')
                }
            
            return metadata if metadata else None
            
        except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
            return None
    
    def _extract_gps(self, tags: Dict[str, str]) -> Optional[Dict[str, float]]:
        """
        Extract GPS coordinates from video tags.
        
        Common tag formats:
        - location: "+37.7749-122.4194/" (ISO 6709)
        - com.apple.quicktime.location.ISO6709: "+37.7749-122.4194+010.500/"
        - gps: various formats
        """
        gps_data = {}
        
        # Check for ISO 6709 format (most common in videos)
        for key in ['location', 'com.apple.quicktime.location.iso6709', 'gps']:
            if key in tags:
                coords = self._parse_iso6709(tags[key])
                if coords:
                    return coords
        
        # Check for separate latitude/longitude tags
        lat_keys = ['latitude', 'gps_latitude', 'gpslatitude']
        lon_keys = ['longitude', 'gps_longitude', 'gpslongitude']
        alt_keys = ['altitude', 'gps_altitude', 'gpsaltitude']
        
        for lat_key in lat_keys:
            if lat_key in tags:
                try:
                    gps_data['latitude'] = float(tags[lat_key])
                except (ValueError, TypeError):
                    pass
        
        for lon_key in lon_keys:
            if lon_key in tags:
                try:
                    gps_data['longitude'] = float(tags[lon_key])
                except (ValueError, TypeError):
                    pass
        
        for alt_key in alt_keys:
            if alt_key in tags:
                try:
                    gps_data['altitude'] = float(tags[alt_key])
                except (ValueError, TypeError):
                    pass
        
        # Need at least lat/lon
        if 'latitude' in gps_data and 'longitude' in gps_data:
            return gps_data
        
        return None
    
    def _parse_iso6709(self, location_string: str) -> Optional[Dict[str, float]]:
        """
        Parse ISO 6709 location string.
        Format: +37.7749-122.4194/ or +37.7749-122.4194+010.500/
        """
        try:
            # Remove trailing slash
            location_string = location_string.rstrip('/')
            
            # Parse latitude (starts with + or -)
            lat_end = 1
            while lat_end < len(location_string) and location_string[lat_end] not in ['+', '-']:
                lat_end += 1
            
            lat_str = location_string[:lat_end]
            rest = location_string[lat_end:]
            
            # Parse longitude (next + or -)
            lon_end = 1
            while lon_end < len(rest) and rest[lon_end] not in ['+', '-']:
                lon_end += 1
            
            lon_str = rest[:lon_end]
            alt_str = rest[lon_end:] if lon_end < len(rest) else None
            
            result = {
                'latitude': float(lat_str),
                'longitude': float(lon_str)
            }
            
            if alt_str:
                try:
                    result['altitude'] = float(alt_str)
                except (ValueError, TypeError):
                    pass
            
            return result
            
        except (ValueError, IndexError):
            return None
    
    def _extract_datetime(self, tags: Dict[str, str]) -> Optional[datetime]:
        """
        Extract recording datetime from video tags.
        
        Common tag keys:
        - creation_time
        - date
        - com.apple.quicktime.creationdate
        """
        date_keys = [
            'creation_time',
            'com.apple.quicktime.creationdate',
            'date',
            'datetime',
            'datetimeoriginal'
        ]
        
        for key in date_keys:
            if key in tags:
                dt = self._parse_datetime(tags[key])
                if dt:
                    return dt
        
        return None
    
    def _parse_datetime(self, date_string: str) -> Optional[datetime]:
        """Parse various datetime formats found in video metadata"""
        # Common formats in video files
        formats = [
            '%Y-%m-%dT%H:%M:%S.%fZ',      # ISO 8601 with microseconds
            '%Y-%m-%dT%H:%M:%SZ',          # ISO 8601
            '%Y-%m-%d %H:%M:%S',           # Standard format
            '%Y:%m:%d %H:%M:%S',           # EXIF-like format
            '%Y-%m-%d',                    # Date only
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_string, fmt)
            except (ValueError, TypeError):
                continue
        
        return None
    
    def _extract_camera_info(self, tags: Dict[str, str]) -> Optional[Dict[str, str]]:
        """Extract camera/device information from video tags"""
        camera = {}
        
        # Check for make/model
        make_keys = ['make', 'manufacturer', 'com.apple.quicktime.make']
        model_keys = ['model', 'device', 'com.apple.quicktime.model']
        
        for key in make_keys:
            if key in tags and tags[key]:
                camera['make'] = tags[key]
                break
        
        for key in model_keys:
            if key in tags and tags[key]:
                camera['model'] = tags[key]
                break
        
        return camera if camera else None


def main():
    """Test video metadata extraction"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python video_metadata_extractor.py <video_file>")
        sys.exit(1)
    
    video_path = Path(sys.argv[1])
    
    extractor = VideoMetadataExtractor()
    
    if not extractor.ffprobe_available:
        print("ERROR: ffprobe not available. Install ffmpeg to enable video metadata extraction.")
        sys.exit(1)
    
    print(f"Extracting metadata from: {video_path}")
    print()
    
    metadata = extractor.extract_metadata(video_path)
    
    if metadata:
        print("Metadata found:")
        print(json.dumps(metadata, indent=2, default=str))
    else:
        print("No metadata found or extraction failed.")


if __name__ == '__main__':
    main()
