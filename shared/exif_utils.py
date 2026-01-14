"""
Shared EXIF metadata extraction utilities for IDT applications.

This module consolidates EXIF data extraction logic used across multiple
applications to reduce code duplication and improve maintainability.

EXIF Field Priority:
    When extracting datetime information, fields are checked in this order:
    1. DateTimeOriginal - When the photo was actually taken (preferred)
    2. DateTimeDigitized - When the photo was scanned/digitized
    3. DateTime - Generic datetime field
    4. File modification time - Last resort fallback

Functions:
    - extract_exif_datetime() - Extract datetime object from EXIF
    - extract_exif_date_string() - Extract formatted date string (M/D/YYYY H:MMP)
    - extract_exif_data() - Extract complete EXIF dictionary
    - extract_gps_coordinates() - Extract GPS location from EXIF
"""

import os
from pathlib import Path
from typing import Dict, Optional, Any, Union, Tuple
from datetime import datetime


def extract_exif_datetime(image_path: Union[str, Path]) -> Optional[datetime]:
    """Extract datetime object from image EXIF data with fallback to file mtime.
    
    Searches EXIF fields in priority order:
    1. DateTimeOriginal - When photo was taken
    2. DateTimeDigitized - When photo was digitized
    3. DateTime - Generic datetime
    4. File modification time - Last resort
    
    Args:
        image_path: Path to image file
        
    Returns:
        datetime object if found, None if no date available
        
    Examples:
        >>> dt = extract_exif_datetime('/path/to/photo.jpg')
        >>> if dt:
        ...     print(f"Photo taken: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
        
    Notes:
        - Handles both PIL and fallback mechanisms
        - Returns file modification time if EXIF data missing
        - Returns None only if file doesn't exist
    """
    try:
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS
        except ImportError:
            # Fallback if PIL not available
            return datetime.fromtimestamp(Path(image_path).stat().st_mtime)
        
        image_path = Path(image_path)
        
        if not image_path.exists():
            return None
        
        with Image.open(image_path) as img:
            exif_data = img.getexif()
            
            if exif_data:
                # Convert raw EXIF to human-readable format
                exif_dict = {}
                for tag_id, value in exif_data.items():
                    tag = TAGS.get(tag_id, tag_id)
                    exif_dict[tag] = value
                
                # Try datetime fields in priority order
                datetime_fields = ['DateTimeOriginal', 'DateTimeDigitized', 'DateTime']
                
                for field in datetime_fields:
                    if field in exif_dict:
                        dt_str = exif_dict[field]
                        if not dt_str:
                            continue
                        
                        # Try multiple datetime formats
                        for fmt in ('%Y:%m:%d %H:%M:%S', '%Y-%m-%d %H:%M:%S'):
                            try:
                                return datetime.strptime(str(dt_str), fmt)
                            except (ValueError, TypeError):
                                continue
        
        # Fallback to file modification time
        file_mtime = image_path.stat().st_mtime
        return datetime.fromtimestamp(file_mtime)
        
    except Exception:
        # Return None only if file doesn't exist
        return None


def extract_exif_date_string(image_path: Union[str, Path]) -> str:
    """Extract formatted date string from image EXIF data (M/D/YYYY H:MMP format).
    
    Extracts datetime using same field priority as extract_exif_datetime(), then
    formats as M/D/YYYY H:MMP with:
    - No leading zeros on month, day, hour
    - 12-hour format with A/P suffix
    - 2-digit padded minutes
    
    Args:
        image_path: Path to image file
        
    Returns:
        Formatted date string (e.g., "3/25/2025 7:35P") or "Unknown date" if error
        
    Examples:
        >>> date_str = extract_exif_date_string('/path/to/photo.jpg')
        >>> print(date_str)  # "3/25/2025 7:35P"
        
    Notes:
        - Always returns a string (never None)
        - Returns "Unknown date" if file not found or EXIF extraction fails
        - Compatible with all platform line-endings and file systems
        - Used by: viewer, window titles, metadata displays
    """
    try:
        dt = extract_exif_datetime(image_path)
        
        if dt is None:
            return "Unknown date"
        
        # Format as M/D/YYYY H:MMP (no leading zeros)
        month = dt.month
        day = dt.day
        year = dt.year
        
        # Convert 24-hour to 12-hour format
        hour24 = dt.hour
        minute = dt.minute
        suffix = 'A' if hour24 < 12 else 'P'
        
        hour12 = hour24 % 12
        if hour12 == 0:
            hour12 = 12
        
        return f"{month}/{day}/{year} {hour12}:{minute:02d}{suffix}"
        
    except Exception:
        return "Unknown date"


def extract_exif_data(image_path: Union[str, Path]) -> Dict[str, Any]:
    """Extract complete EXIF dictionary from image with human-readable tags.
    
    Converts raw EXIF data to dictionary with human-readable tag names.
    
    Args:
        image_path: Path to image file
        
    Returns:
        Dictionary mapping EXIF tag names to values, or empty dict if no EXIF data
        
    Examples:
        >>> exif = extract_exif_data('/path/to/photo.jpg')
        >>> if 'DateTimeOriginal' in exif:
        ...     print(f"Photo taken: {exif['DateTimeOriginal']}")
        >>> if 'GPSInfo' in exif:
        ...     print(f"Has GPS data: {exif['GPSInfo']}")
        
    Notes:
        - Returns empty dict if file doesn't exist or can't be read
        - EXIF tags are human-readable (e.g., 'DateTimeOriginal' not 306)
        - Returns raw EXIF values (no conversion or formatting)
    """
    try:
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS
        except ImportError:
            return {}
        
        image_path = Path(image_path)
        
        if not image_path.exists():
            return {}
        
        with Image.open(image_path) as img:
            exif_data = img.getexif()
            
            if not exif_data:
                return {}
            
            # Convert to human-readable format
            exif_dict = {}
            for tag_id, value in exif_data.items():
                tag = TAGS.get(tag_id, tag_id)
                exif_dict[tag] = value
            
            return exif_dict
        
    except Exception:
        return {}


def extract_gps_coordinates(image_path: Union[str, Path]) -> Optional[Dict[str, float]]:
    """Extract GPS coordinates from image EXIF data.
    
    Extracts latitude, longitude, and optional altitude from GPSInfo EXIF tag.
    
    Args:
        image_path: Path to image file
        
    Returns:
        Dictionary with keys:
            - 'latitude': float, range -90 to 90 (S is negative)
            - 'longitude': float, range -180 to 180 (W is negative)
            - 'altitude': float, optional, in meters
        Or None if no GPS data found
        
    Examples:
        >>> coords = extract_gps_coordinates('/path/to/photo.jpg')
        >>> if coords:
        ...     print(f"Location: {coords['latitude']}, {coords['longitude']}")
        ...     if 'altitude' in coords:
        ...         print(f"Altitude: {coords['altitude']}m")
        
    Notes:
        - Coordinates returned in signed decimal format
        - South latitudes are negative, West longitudes are negative
        - Returns None if no GPSInfo in EXIF
        - Handles malformed GPS data gracefully
    """
    try:
        try:
            from PIL import Image
            from PIL.ExifTags import GPSTAGS
        except ImportError:
            return None
        
        image_path = Path(image_path)
        
        if not image_path.exists():
            return None
        
        with Image.open(image_path) as img:
            exif_data = img.getexif()
            
            if not exif_data:
                return None
            
            # Look for GPS info
            gps_info = exif_data.get(34853)  # Tag 34853 is GPSInfo
            
            if not gps_info:
                return None
            
            # Convert GPS tags to human-readable format
            gps_dict = {}
            for tag_id, value in gps_info.items():
                tag = GPSTAGS.get(tag_id, tag_id)
                gps_dict[tag] = value
            
            coordinates = {}
            
            # Extract latitude
            if 'GPSLatitude' in gps_dict and 'GPSLatitudeRef' in gps_dict:
                lat = _convert_gps_coordinate(gps_dict['GPSLatitude'])
                if gps_dict['GPSLatitudeRef'] == 'S':
                    lat = -lat
                coordinates['latitude'] = lat
            
            # Extract longitude
            if 'GPSLongitude' in gps_dict and 'GPSLongitudeRef' in gps_dict:
                lon = _convert_gps_coordinate(gps_dict['GPSLongitude'])
                if gps_dict['GPSLongitudeRef'] == 'W':
                    lon = -lon
                coordinates['longitude'] = lon
            
            # Extract altitude (optional)
            if 'GPSAltitude' in gps_dict:
                try:
                    altitude = float(gps_dict['GPSAltitude'])
                    if 'GPSAltitudeRef' in gps_dict and gps_dict['GPSAltitudeRef'] == 1:
                        altitude = -altitude
                    coordinates['altitude'] = altitude
                except (ValueError, TypeError):
                    pass
            
            return coordinates if coordinates else None
        
    except Exception:
        return None


def _convert_gps_coordinate(coordinate_tuple: Tuple) -> float:
    """Convert GPS coordinate tuple (degrees, minutes, seconds) to decimal degrees.
    
    Args:
        coordinate_tuple: Tuple of (degrees, minutes, seconds) as fractions
        
    Returns:
        Decimal degrees (float)
        
    Notes:
        - Internal function used by extract_gps_coordinates()
        - Handles fraction objects from PIL.ExifTags
    """
    try:
        # Handle both tuples and individual fraction objects
        d, m, s = coordinate_tuple
        
        # Convert fraction objects to float
        degrees = float(d)
        minutes = float(m) / 60
        seconds = float(s) / 3600
        
        return degrees + minutes + seconds
        
    except (TypeError, ValueError, ZeroDivisionError):
        return 0.0


def get_image_date_for_sorting(image_path: Union[str, Path]) -> datetime:
    """Extract datetime for sorting purposes (used by analysis tools).
    
    Convenience wrapper around extract_exif_datetime() that always returns
    a datetime object suitable for sorting.
    
    Args:
        image_path: Path to image file
        
    Returns:
        datetime object (epoch time if file not found)
        
    Notes:
        - Always returns datetime (never None)
        - Returns epoch time (1970-01-01) if file doesn't exist
        - Used by: combine_workflow_descriptions, analysis tools
        - Safe for sorting without None checks
    """
    dt = extract_exif_datetime(image_path)
    
    if dt is None:
        # Return epoch time for sorting (will sort to beginning)
        return datetime.fromtimestamp(0)
    
    return dt
