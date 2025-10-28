#!/usr/bin/env python3
"""
Shared Metadata Extraction Module for IDT
Extracts EXIF metadata from images including GPS, dates, camera info
Supports optional reverse geocoding via OpenStreetMap Nominatim
"""

import sys
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Import PIL for EXIF extraction
try:
    from PIL import Image
    from PIL.ExifTags import TAGS, GPSTAGS
except ImportError:
    print("ERROR: PIL (Pillow) not installed")
    print("Install with: pip install Pillow")
    sys.exit(1)

# Try to enable HEIC support
HEIC_SUPPORT = False
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    HEIC_SUPPORT = True
except ImportError:
    pass


class MetadataExtractor:
    """Extract and format image metadata"""
    
    def __init__(self):
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp', '.heic'}
    
    def is_supported_image(self, file_path: Path) -> bool:
        """Check if file is a supported image format"""
        return file_path.suffix.lower() in self.supported_formats
    
    def _format_mdy_ampm(self, dt: datetime) -> str:
        """Format datetime as M/D/YYYY H:MMP (no leading zero on hour, A/P)."""
        month = dt.month
        day = dt.day
        year = dt.year
        hour24 = dt.hour
        minute = dt.minute
        suffix = 'A' if hour24 < 12 else 'P'
        hour12 = hour24 % 12
        if hour12 == 0:
            hour12 = 12
        return f"{month}/{day}/{year} {hour12}:{minute:02d}{suffix}"
    
    def _format_short_date(self, dt: datetime) -> str:
        """Format datetime as 'Mon Day, Year' (e.g., 'Sep 9, 2025'). Cross-platform (Windows-safe)."""
        # Use %d (with leading zero) and strip the zero for 01-09 days to avoid %-d incompatibility on Windows
        return dt.strftime("%b %d, %Y").replace(" 0", " ")
    
    def _extract_datetime(self, exif_data: dict) -> Optional[datetime]:
        """Extract date/time from EXIF as datetime object.
        Priority: DateTimeOriginal > DateTimeDigitized > DateTime.
        """
        try:
            datetime_fields = ['DateTimeOriginal', 'DateTimeDigitized', 'DateTime']
            for field in datetime_fields:
                if field in exif_data:
                    dt_str = exif_data[field]
                    if not dt_str:
                        continue
                    for fmt in ('%Y:%m:%d %H:%M:%S', '%Y-%m-%d %H:%M:%S'):
                        try:
                            return datetime.strptime(dt_str, fmt)
                        except ValueError:
                            continue
        except Exception:
            pass
        return None
    
    def _extract_location(self, exif_data: dict) -> Optional[Dict[str, Any]]:
        """Extract GPS/location info including optional human-readable fields."""
        try:
            gps_info = exif_data.get('GPSInfo')
            if not gps_info:
                # Fallback: collect any textual location hints from EXIF
                text_loc = {}
                for key in ('City', 'State', 'Province', 'Country', 'CountryName', 'CountryCode'):
                    if key in exif_data and exif_data[key]:
                        k = key.lower()
                        if k == 'province':
                            k = 'state'
                        text_loc[k] = exif_data[key]
                return text_loc or None
            
            # Convert GPS info to readable format
            gps_dict = {}
            for tag_id, value in gps_info.items():
                tag = GPSTAGS.get(tag_id, tag_id)
                gps_dict[tag] = value
            
            location = {}
            
            # Extract latitude
            if 'GPSLatitude' in gps_dict and 'GPSLatitudeRef' in gps_dict:
                lat = self._convert_gps_coordinate(gps_dict['GPSLatitude'])
                if gps_dict['GPSLatitudeRef'] == 'S':
                    lat = -lat
                location['latitude'] = lat
            
            # Extract longitude
            if 'GPSLongitude' in gps_dict and 'GPSLongitudeRef' in gps_dict:
                lon = self._convert_gps_coordinate(gps_dict['GPSLongitude'])
                if gps_dict['GPSLongitudeRef'] == 'W':
                    lon = -lon
                location['longitude'] = lon
            
            # Extract altitude
            if 'GPSAltitude' in gps_dict:
                altitude = float(gps_dict['GPSAltitude'])
                if 'GPSAltitudeRef' in gps_dict and gps_dict['GPSAltitudeRef'] == 1:
                    altitude = -altitude
                location['altitude'] = altitude
            
            # Attach any human-readable tags if present
            for key in ('City', 'State', 'Province', 'Country', 'CountryName', 'CountryCode'):
                if key in exif_data and exif_data[key]:
                    k = key.lower()
                    if k == 'province':
                        k = 'state'
                    location[k] = exif_data[key]
            
            return location if location else None
        except Exception:
            pass
        return None
    
    def _extract_camera_info(self, exif_data: dict) -> Optional[Dict[str, str]]:
        """Extract camera information from EXIF data"""
        try:
            camera_info = {}
            
            if 'Make' in exif_data:
                camera_info['make'] = exif_data['Make']
            if 'Model' in exif_data:
                camera_info['model'] = exif_data['Model']
            if 'LensModel' in exif_data:
                camera_info['lens'] = exif_data['LensModel']
            
            return camera_info if camera_info else None
        except Exception:
            pass
        return None
    
    def _convert_gps_coordinate(self, coord_tuple) -> float:
        """Convert GPS coordinate from tuple format to decimal degrees"""
        try:
            degrees = float(coord_tuple[0])
            minutes = float(coord_tuple[1])
            seconds = float(coord_tuple[2])
            return degrees + (minutes / 60.0) + (seconds / 3600.0)
        except:
            return 0.0
    
    def extract_metadata(self, image_path: Path) -> Dict[str, Any]:
        """Extract all metadata from an image file"""
        metadata = {}
        
        try:
            with Image.open(image_path) as img:
                exif_data = img.getexif()
                
                if not exif_data:
                    return metadata
                
                # Convert EXIF data to human-readable format
                exif_dict = {}
                for tag_id, value in exif_data.items():
                    tag = TAGS.get(tag_id, tag_id)
                    exif_dict[tag] = value
                
                # Extract GPS IFD separately (it's stored in a separate structure)
                try:
                    gps_ifd = exif_data.get_ifd(0x8825)  # 0x8825 = GPSInfo tag
                    if gps_ifd:
                        gps_dict = {}
                        for tag_id, value in gps_ifd.items():
                            tag = GPSTAGS.get(tag_id, tag_id)
                            gps_dict[tag] = value
                        exif_dict['GPSInfo'] = gps_dict
                except (KeyError, AttributeError):
                    # No GPS data or get_ifd not available
                    pass
                
                # Extract all available metadata
                dt = self._extract_datetime(exif_dict)
                if dt:
                    metadata['datetime'] = dt
                    metadata['datetime_str'] = self._format_mdy_ampm(dt)
                    metadata['date_short'] = self._format_short_date(dt)
                
                location_info = self._extract_location(exif_dict)
                if location_info:
                    metadata['location'] = location_info
                
                camera_info = self._extract_camera_info(exif_dict)
                if camera_info:
                    metadata['camera'] = camera_info
        except Exception as e:
            # Silently fail - metadata is optional
            pass
        
        # Always add file modification time as fallback
        try:
            mtime = datetime.fromtimestamp(image_path.stat().st_mtime)
            if 'datetime' not in metadata:
                metadata['datetime'] = mtime
                metadata['datetime_str'] = self._format_mdy_ampm(mtime)
                metadata['date_short'] = self._format_short_date(mtime)
        except Exception:
            pass
        
        return metadata
    
    def format_location_prefix(self, metadata: Dict[str, Any]) -> str:
        """
        Format location and date as a prefix for descriptions.
        Format: "City, State Mon Day, Year" or just "Mon Day, Year" if no location.
        Examples:
            "Madison, WI Sep 9, 2025"
            "Sep 9, 2025"
        Returns empty string if no date information available.
        """
        parts = []
        
        # Location (city, state or city, country)
        if 'location' in metadata:
            loc = metadata['location']
            city = loc.get('city') or loc.get('town')
            state = loc.get('state')
            country = loc.get('country') or loc.get('countryname')
            
            if city and state:
                parts.append(str(city) + ", " + str(state))
            elif city and country:
                parts.append(str(city) + ", " + str(country))
            elif state:
                parts.append(state)
        
        # Date
        if 'date_short' in metadata:
            parts.append(metadata['date_short'])
        elif 'datetime' in metadata:
            dt = metadata['datetime']
            if isinstance(dt, datetime):
                parts.append(self._format_short_date(dt))
        
        return " ".join(parts)
    
    def build_meta_suffix(self, image_path: Path, metadata: Dict[str, Any]) -> str:
        """Build the compact one-line Meta suffix that appears in description files"""
        parts = []
        
        # Date
        if metadata.get('datetime_str'):
            parts.append(metadata['datetime_str'])
        
        # Camera
        if 'camera' in metadata:
            camera = metadata['camera']
            if 'make' in camera and 'model' in camera:
                # Simplify camera name (e.g., "Apple iPhone 14")
                make = camera['make'].strip()
                model = camera['model'].strip()
                # Remove redundant make from model if present
                if model.lower().startswith(make.lower()):
                    parts.append(model)
                else:
                    parts.append(str(make) + " " + str(model))
            elif 'model' in camera:
                parts.append(camera['model'])
        
        # GPS coordinates
        if 'location' in metadata:
            loc = metadata['location']
            if 'latitude' in loc and 'longitude' in loc:
                lat = loc['latitude']
                lon = loc['longitude']
                lat_dir = 'N' if lat >= 0 else 'S'
                lon_dir = 'E' if lon >= 0 else 'W'
                parts.append(f"{abs(lat):.4f}°{lat_dir}, {abs(lon):.4f}°{lon_dir}")
                
                if 'altitude' in loc:
                    parts.append(f"{loc['altitude']:.0f}m")
        
        return f"[{', '.join(parts)}]" if parts else ""


class NominatimGeocoder:
    """Reverse geocode GPS coordinates using OpenStreetMap Nominatim"""
    
    def __init__(self, user_agent: str, delay_seconds: float = 1.0, cache_path: Optional[Path] = None):
        """
        Initialize geocoder with rate limiting and optional caching.
        
        Args:
            user_agent: Custom User-Agent string (required by Nominatim policy)
            delay_seconds: Minimum delay between API requests (default 1.0)
            cache_path: Optional path to JSON file for persistent cache
        """
        self.user_agent = user_agent
        self.delay_seconds = max(delay_seconds, 0.5)  # Minimum 0.5 seconds
        self.last_request_time = 0
        self.cache = {}
        self.cache_path = cache_path
        
        # Try to import requests
        self._requests_available = False
        try:
            import requests
            self.requests = requests
            self._requests_available = True
        except ImportError:
            pass
        
        # Load cache if available
        if self.cache_path and self.cache_path.exists():
            try:
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
            except Exception:
                self.cache = {}
        
        # Log attribution notice when geocoder is initialized
        if self._requests_available:
            print("Geocoding service: OpenStreetMap Nominatim")
            print("Location data © OpenStreetMap contributors (https://www.openstreetmap.org/copyright)")
    
    def _save_cache(self):
        """Save cache to file if cache_path is set"""
        if self.cache_path:
            try:
                with open(self.cache_path, 'w', encoding='utf-8') as f:
                    json.dump(self.cache, f, indent=2, ensure_ascii=False)
            except Exception:
                pass
    
    def _rate_limit(self):
        """Enforce rate limiting between API requests"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.delay_seconds:
            time.sleep(self.delay_seconds - time_since_last)
        self.last_request_time = time.time()
    
    def geocode(self, latitude: float, longitude: float) -> Optional[Dict[str, str]]:
        """
        Reverse geocode coordinates to city/state/country.
        
        Returns dict with keys: city, state, country, country_code
        Returns None if geocoding fails or requests not available.
        """
        if not self._requests_available:
            return None
        
        # Check cache first
        cache_key = f"{latitude:.6f},{longitude:.6f}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Rate limit
        self._rate_limit()
        
        # Make API request
        try:
            url = "https://nominatim.openstreetmap.org/reverse"
            params = {
                'lat': latitude,
                'lon': longitude,
                'format': 'json',
                'addressdetails': 1,
            }
            headers = {
                'User-Agent': self.user_agent
            }
            
            response = self.requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            address = data.get('address', {})
            
            result = {
                'city': address.get('city') or address.get('town') or address.get('village'),
                'state': address.get('state'),
                'country': address.get('country'),
                'country_code': address.get('country_code', '').upper(),
            }
            
            # Remove None values
            result = {k: v for k, v in result.items() if v}
            
            # Cache result
            self.cache[cache_key] = result
            self._save_cache()
            
            return result
        except Exception:
            return None
    
    def enrich_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add geocoded city/state/country to metadata if GPS coordinates present.
        Modifies metadata dict in place and returns it.
        """
        if 'location' in metadata:
            loc = metadata['location']
            if 'latitude' in loc and 'longitude' in loc:
                geocoded = self.geocode(loc['latitude'], loc['longitude'])
                if geocoded:
                    loc.update(geocoded)
        
        return metadata
