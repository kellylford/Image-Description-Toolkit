#!/usr/bin/env python3
"""
Show Image Metadata Tool
Extracts and displays EXIF metadata from images without running AI descriptions.
Useful for testing what metadata will be included in workflow outputs.

Note: HEIC file support requires pillow-heif:
    pip install pillow-heif
"""

import sys
import argparse
import time
import json
import csv
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
    pass  # HEIC support not available, will warn user later


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
    
    def _extract_datetime(self, exif_data: dict) -> Optional[str]:
        """Extract date/time from EXIF using standard format.
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
                            dt = datetime.strptime(dt_str, fmt)
                            return self._format_mdy_ampm(dt)
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
    
    def _extract_technical_info(self, exif_data: dict) -> Optional[Dict[str, Any]]:
        """Extract technical camera settings from EXIF data"""
        try:
            technical_info = {}
            
            # ISO
            if 'ISOSpeedRatings' in exif_data:
                technical_info['iso'] = exif_data['ISOSpeedRatings']
            elif 'ISO' in exif_data:
                technical_info['iso'] = exif_data['ISO']
            
            # Aperture
            if 'FNumber' in exif_data:
                f_number = exif_data['FNumber']
                if isinstance(f_number, tuple) and len(f_number) == 2:
                    f_value = f_number[0] / f_number[1]
                    technical_info['aperture'] = f"f/{f_value:.1f}"
                else:
                    technical_info['aperture'] = f"f/{f_number}"
            
            # Shutter speed
            if 'ExposureTime' in exif_data:
                exposure_time = exif_data['ExposureTime']
                if isinstance(exposure_time, tuple) and len(exposure_time) == 2:
                    if exposure_time[0] == 1:
                        technical_info['shutter_speed'] = f"1/{exposure_time[1]}s"
                    else:
                        technical_info['shutter_speed'] = f"{exposure_time[0]/exposure_time[1]}s"
                else:
                    technical_info['shutter_speed'] = f"{exposure_time}s"
            
            # Focal length
            if 'FocalLength' in exif_data:
                focal_length = exif_data['FocalLength']
                if isinstance(focal_length, tuple) and len(focal_length) == 2:
                    fl_value = focal_length[0] / focal_length[1]
                    technical_info['focal_length'] = f"{fl_value:.0f}mm"
                else:
                    technical_info['focal_length'] = f"{focal_length}mm"
            
            return technical_info if technical_info else None
        except Exception:
            pass
        return None
    
    def _convert_gps_coordinate(self, coord_tuple) -> float:
        """Convert GPS coordinate from tuple format to decimal degrees"""
        try:
            # Elements may be rational numbers; float() should work for IFDRational
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
                datetime_info = self._extract_datetime(exif_dict)
                if datetime_info:
                    metadata['datetime'] = datetime_info
                
                location_info = self._extract_location(exif_dict)
                if location_info:
                    metadata['location'] = location_info
                
                camera_info = self._extract_camera_info(exif_dict)
                if camera_info:
                    metadata['camera'] = camera_info
                
                technical_info = self._extract_technical_info(exif_dict)
                if technical_info:
                    metadata['technical'] = technical_info
        except Exception as e:
            print(f"    Error extracting metadata: {e}")
        
        return metadata
    
    def build_meta_suffix(self, image_path: Path, metadata: Dict[str, Any]) -> str:
        """Build the compact one-line Meta suffix that would appear in descriptions"""
        parts = []
        
        # Date from metadata or fallback to file mtime
        date_str = None
        try:
            if metadata and metadata.get('datetime'):
                date_str = metadata['datetime']
            else:
                mtime = datetime.fromtimestamp(image_path.stat().st_mtime)
                date_str = self._format_mdy_ampm(mtime)
        except Exception:
            date_str = None
        if date_str:
            parts.append(f"date={date_str}")
        
        # Human-readable location if present
        loc_human = None
        coords = None
        loc = metadata.get('location') if metadata else None
        if isinstance(loc, dict):
            city = loc.get('city') or loc.get('town')
            state = loc.get('state')
            country = loc.get('country') or loc.get('countryname')
            if city and state:
                loc_human = f"{city}, {state}"
            elif city and country:
                loc_human = f"{city}, {country}"
            elif state and country:
                loc_human = f"{state}, {country}"
            
            if 'latitude' in loc and 'longitude' in loc:
                try:
                    coords = f"{float(loc['latitude']):.6f},{float(loc['longitude']):.6f}"
                except Exception:
                    coords = None
        
        if loc_human:
            parts.append(f"location={loc_human}")
        if coords:
            parts.append(f"coords={coords}")
        
        return ("Meta: " + "; ".join(parts)) if parts else ""
    
    def format_metadata_display(self, metadata: Dict[str, Any]) -> str:
        """Format metadata for human-readable display"""
        if not metadata:
            return "  [No EXIF metadata found]"
        
        lines = []
        
        # Format datetime
        if 'datetime' in metadata:
            lines.append(f"  Photo Date: {metadata['datetime']}")
        
        # Format location
        if 'location' in metadata:
            location = metadata['location']
            location_parts = []
            
            if 'latitude' in location and 'longitude' in location:
                location_parts.append(f"GPS: {location['latitude']:.6f}, {location['longitude']:.6f}")
            
            if 'altitude' in location:
                location_parts.append(f"Altitude: {location['altitude']:.1f}m")
            
            # Add human-readable location if available
            city = location.get('city') or location.get('town')
            state = location.get('state')
            country = location.get('country') or location.get('countryname')
            
            if city or state or country:
                readable = []
                if city:
                    readable.append(city)
                if state:
                    readable.append(state)
                if country:
                    readable.append(country)
                location_parts.append("Location: " + ", ".join(readable))
            
            if location_parts:
                lines.append("  Location: " + ", ".join(location_parts))
        
        # Format camera info
        if 'camera' in metadata:
            camera = metadata['camera']
            camera_parts = []
            
            if 'make' in camera and 'model' in camera:
                camera_parts.append(f"{camera['make']} {camera['model']}")
            
            if 'lens' in camera:
                camera_parts.append(f"Lens: {camera['lens']}")
            
            if camera_parts:
                lines.append("  Camera: " + ", ".join(camera_parts))
        
        # Format technical info
        if 'technical' in metadata:
            technical = metadata['technical']
            technical_parts = []
            
            for key, value in technical.items():
                technical_parts.append(f"{key.replace('_', ' ').title()}: {value}")
            
            if technical_parts:
                lines.append("  Settings: " + ", ".join(technical_parts))
        
        return "\n".join(lines) if lines else "  [No EXIF metadata found]"
    
    def process_directory(self, directory: Path, recursive: bool = False, show_meta_suffix: bool = True,
                          geocoder: Optional["NominatimGeocoder"] = None,
                          csv_out: Optional[Path] = None):
        """Process all images in a directory and display their metadata"""
        
        if not directory.exists():
            print(f"ERROR: Directory does not exist: {directory}")
            return
        
        if not directory.is_dir():
            print(f"ERROR: Not a directory: {directory}")
            return
        
        # Find all image files
        pattern = "**/*" if recursive else "*"
        image_files = []
        
        for file_path in directory.glob(pattern):
            if file_path.is_file() and self.is_supported_image(file_path):
                image_files.append(file_path)
        
        if not image_files:
            print("No supported image files found in directory")
            return
        
        # Sort files for consistent output
        image_files.sort()
        
        # Check for HEIC files and warn if no support
        heic_files = [f for f in image_files if f.suffix.lower() in {'.heic', '.heif'}]
        if heic_files and not HEIC_SUPPORT:
            print(f"\n{'='*80}")
            print(f"WARNING: HEIC Support Not Available")
            print(f"{'='*80}")
            print(f"Found {len(heic_files)} HEIC/HEIF files, but pillow-heif is not installed.")
            print(f"HEIC files contain GPS location and camera metadata that cannot be extracted.")
            print(f"")
            print(f"To enable HEIC support:")
            print(f"  pip install pillow-heif")
            print(f"")
            print(f"Without HEIC support, only file modification time will be available.")
            print(f"{'='*80}\n")
        elif HEIC_SUPPORT:
            print(f"HEIC support: Enabled (pillow-heif installed)")
        
        print(f"\n{'='*80}")
        print(f"Image Metadata Extraction Report")
        print(f"{'='*80}")
        print(f"Directory: {directory}")
        print(f"Images found: {len(image_files)}")
        print(f"Recursive: {'Yes' if recursive else 'No'}")
        print(f"{'='*80}\n")
        
        # Prepare CSV output if requested
        csv_rows = []
        csv_headers = [
            'file', 'modified', 'date', 'latitude', 'longitude', 'altitude_m',
            'city', 'state', 'country', 'country_code', 'camera_make', 'camera_model', 'lens', 'meta_suffix'
        ]

        # Process each image
        images_with_metadata = 0
        images_without_metadata = 0
        
        for i, image_path in enumerate(image_files, 1):
            try:
                relative_path = image_path.relative_to(directory)
            except ValueError:
                relative_path = image_path.name
            
            print(f"[{i}/{len(image_files)}] {relative_path}")
            
            # Get file info
            try:
                file_size = image_path.stat().st_size / 1024  # KB
                file_mtime = datetime.fromtimestamp(image_path.stat().st_mtime)
                print(f"  File size: {file_size:.1f} KB")
                print(f"  File modified: {self._format_mdy_ampm(file_mtime)}")
            except Exception as e:
                print(f"  Could not read file info: {e}")
            
            # Extract metadata
            metadata = self.extract_metadata(image_path)
            
            if metadata:
                images_with_metadata += 1
                print("\n  EXIF Metadata:")
                print(self.format_metadata_display(metadata))
                
                # Optional reverse geocoding when GPS present
                loc = metadata.get('location') if isinstance(metadata, dict) else None
                if geocoder and isinstance(loc, dict) and 'latitude' in loc and 'longitude' in loc:
                    geo = geocoder.reverse(loc['latitude'], loc['longitude'])
                    if geo:
                        # Merge geocode results into location dict without overwriting existing human tags
                        for k in ('city', 'state', 'country', 'country_code', 'display_name'):
                            if geo.get(k) and not loc.get(k):
                                loc[k] = geo[k]
                        # Show a concise line for geocode
                        readable = [v for v in [loc.get('city') or loc.get('town'), loc.get('state'), loc.get('country')] if v]
                        if readable:
                            print("  Geocoded: " + ", ".join(readable))

                if show_meta_suffix:
                    meta_suffix = self.build_meta_suffix(image_path, metadata)
                    if meta_suffix:
                        print(f"\n  {meta_suffix}")
            else:
                images_without_metadata += 1
                print("  [No EXIF metadata found - will use file mtime as fallback]")
                
                if show_meta_suffix:
                    meta_suffix = self.build_meta_suffix(image_path, {})
                    if meta_suffix:
                        print(f"  {meta_suffix}")
            
            # Collect CSV row if requested
            if csv_out is not None:
                row = {
                    'file': str(relative_path),
                    'modified': self._format_mdy_ampm(file_mtime) if 'file_mtime' in locals() else '',
                    'date': metadata.get('datetime') if metadata else '',
                    'latitude': '',
                    'longitude': '',
                    'altitude_m': '',
                    'city': '',
                    'state': '',
                    'country': '',
                    'country_code': '',
                    'camera_make': '',
                    'camera_model': '',
                    'lens': '',
                    'meta_suffix': self.build_meta_suffix(image_path, metadata if metadata else {}),
                }
                if metadata:
                    loc = metadata.get('location') or {}
                    try:
                        if 'latitude' in loc:
                            row['latitude'] = f"{float(loc['latitude']):.6f}"
                        if 'longitude' in loc:
                            row['longitude'] = f"{float(loc['longitude']):.6f}"
                    except Exception:
                        pass
                    if isinstance(loc, dict):
                        row['altitude_m'] = f"{loc.get('altitude'):.1f}" if isinstance(loc.get('altitude'), (int, float)) else ''
                        row['city'] = loc.get('city') or loc.get('town') or ''
                        row['state'] = loc.get('state') or ''
                        row['country'] = loc.get('country') or loc.get('countryname') or ''
                        row['country_code'] = loc.get('country_code') or ''
                    cam = metadata.get('camera') or {}
                    if isinstance(cam, dict):
                        row['camera_make'] = cam.get('make') or ''
                        row['camera_model'] = cam.get('model') or ''
                        row['lens'] = cam.get('lens') or ''
                csv_rows.append(row)

            print()
        
        # Summary
        print(f"{'='*80}")
        print(f"Summary:")
        print(f"  Total images: {len(image_files)}")
        print(f"  With EXIF metadata: {images_with_metadata}")
        print(f"  Without EXIF metadata: {images_without_metadata}")
        print(f"{'='*80}\n")

        # Write CSV if requested
        if csv_out is not None:
            try:
                csv_out.parent.mkdir(parents=True, exist_ok=True)
                with open(csv_out, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.DictWriter(f, fieldnames=csv_headers)
                    writer.writeheader()
                    for r in csv_rows:
                        writer.writerow(r)
                print(f"CSV written: {csv_out} ({len(csv_rows)} rows)")
            except Exception as e:
                print(f"ERROR writing CSV ({csv_out}): {e}")


class NominatimGeocoder:
    """Reverse geocoder using OpenStreetMap Nominatim with simple caching and rate limiting.

    Notes:
    - Requires 'requests' only when geocoding is enabled.
    - Respects Nominatim usage policy: unique User-Agent and ~1 request/second.
    """

    def __init__(self, user_agent: str, delay_seconds: float = 1.0, cache_path: Optional[Path] = None):
        self.user_agent = user_agent
        self.delay_seconds = max(0.0, float(delay_seconds))
        self.cache_path = cache_path
        self.cache: Dict[str, Any] = {}
        self._last_request_ts = 0.0

        # Lazy import so script works without requests unless --geocode is used
        try:
            import requests  # noqa: F401
            self._requests_available = True
        except Exception:
            self._requests_available = False

        # Load existing cache if provided
        if self.cache_path and self.cache_path.exists():
            try:
                with self.cache_path.open('r', encoding='utf-8') as f:
                    self.cache = json.load(f)
            except Exception:
                self.cache = {}

    def _persist_cache(self):
        if not self.cache_path:
            return
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with self.cache_path.open('w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def reverse(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        if not self._requests_available:
            print("  [Geocode] Skipping: 'requests' not installed. Install with: pip install requests")
            return None

        # Normalize key to reduce cache misses for very close coordinates
        key = f"{round(lat, 4)},{round(lon, 4)}"
        if key in self.cache:
            return self.cache[key]

        # Rate limit
        now = time.time()
        wait = self.delay_seconds - (now - self._last_request_ts)
        if wait > 0:
            time.sleep(wait)

        try:
            import requests
            url = "https://nominatim.openstreetmap.org/reverse"
            params = {
                'format': 'jsonv2',
                'lat': lat,
                'lon': lon,
                'zoom': 10,  # city/region level
                'addressdetails': 1,
            }
            headers = {"User-Agent": self.user_agent}
            resp = requests.get(url, params=params, headers=headers, timeout=15)
            self._last_request_ts = time.time()
            if resp.status_code != 200:
                print(f"  [Geocode] HTTP {resp.status_code}: {resp.text[:120]}")
                return None
            data = resp.json()
            address = data.get('address', {}) if isinstance(data, dict) else {}

            # Choose the best locality name available
            city_like = address.get('city') or address.get('town') or address.get('village') or address.get('hamlet') or address.get('suburb')
            result = {
                'city': city_like,
                'state': address.get('state') or address.get('region') or address.get('province'),
                'country': address.get('country'),
                'country_code': address.get('country_code'),
                'display_name': data.get('display_name'),
            }
            # Save and persist
            self.cache[key] = result
            self._persist_cache()
            return result
        except Exception as e:
            print(f"  [Geocode] Error: {e}")
            return None


def main():
    parser = argparse.ArgumentParser(
        description="Extract and display image metadata without running AI descriptions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python show_metadata.py images/
    python show_metadata.py images/ --recursive
    python show_metadata.py images/ --no-meta-suffix
    python show_metadata.py images/ --geocode --csv-out report.csv

This tool shows what metadata will be extracted and included in workflow outputs.
        """
    )
    
    parser.add_argument(
        'directory',
        type=str,
        help='Directory containing images to analyze'
    )
    
    parser.add_argument(
        '--recursive', '-r',
        action='store_true',
        help='Process subdirectories recursively'
    )
    
    parser.add_argument(
        '--no-meta-suffix',
        action='store_true',
        help='Hide the compact Meta suffix line'
    )

    parser.add_argument(
        '--geocode',
        action='store_true',
        help='Reverse geocode GPS coordinates to city/state/country using OpenStreetMap Nominatim (opt-in)'
    )

    parser.add_argument(
        '--geocode-user-agent',
        type=str,
        default='Image-Description-Toolkit/ShowMetadata (https://github.com/kelly/Image-Description-Toolkit)',
        help='Custom User-Agent string for geocoding requests (required by Nominatim usage policy)'
    )

    parser.add_argument(
        '--geocode-delay',
        type=float,
        default=1.0,
        help='Delay in seconds between geocoding requests (min 1.0 recommended)'
    )

    parser.add_argument(
        '--geocode-cache',
        type=str,
        default=None,
        help='Optional path to a JSON cache file to store geocoding results'
    )

    parser.add_argument(
        '--csv-out',
        type=str,
        default=None,
        help='Optional path to write a CSV summary of metadata for all images'
    )
    
    args = parser.parse_args()
    
    directory = Path(args.directory)
    extractor = MetadataExtractor()

    geocoder = None
    csv_out = Path(args.csv_out) if args.csv_out else None
    if args.geocode:
        cache_path = Path(args.geocode_cache) if args.geocode_cache else None
        geocoder = NominatimGeocoder(user_agent=args.geocode_user_agent, delay_seconds=args.geocode_delay, cache_path=cache_path)
        if not geocoder._requests_available:
            print("WARNING: requests not installed; install with 'pip install requests' to enable geocoding.")

    extractor.process_directory(
        directory,
        recursive=args.recursive,
        show_meta_suffix=not args.no_meta_suffix,
        geocoder=geocoder,
        csv_out=csv_out,
    )


def print_header(text):
    """Print a section header"""
    print(f"\n{'=' * 70}")
    print(f"  {text}")
    print(f"{'=' * 70}\n")


def print_numbered_list(items, start=1):
    """Print a numbered list of items (accessible for screen readers)"""
    for idx, item in enumerate(items, start=start):
        print(f"  {idx}. {item}")
    print()


def get_choice(prompt, options, default=None, allow_back=False, allow_exit=True):
    """
    Get user choice from numbered list (accessible for screen readers)
    
    Args:
        prompt: Question to ask
        options: List of option strings
        default: Default option number (1-based) if user just presses Enter
        allow_back: If True, allow 'b' to go back
        allow_exit: If True, allow 'e' to exit
    
    Returns:
        Selected option string, or 'BACK' if user pressed 'b', or 'EXIT' if user pressed 'e'
    """
    print(prompt)
    print_numbered_list(options)
    
    # Build help text
    help_parts = []
    if allow_back:
        help_parts.append("b=back")
    if allow_exit:
        help_parts.append("e=exit")
    help_text = ", ".join(help_parts)
    
    while True:
        if default:
            if help_text:
                user_input = input(f"Enter choice (1-{len(options)}, {help_text}, default={default}): ").strip().lower()
            else:
                user_input = input(f"Enter choice (1-{len(options)}, default={default}): ").strip().lower()
            if not user_input:
                return options[default - 1]
        else:
            if help_text:
                user_input = input(f"Enter choice (1-{len(options)}, {help_text}): ").strip().lower()
            else:
                user_input = input(f"Enter choice (1-{len(options)}): ").strip().lower()
        
        # Check for special commands
        if user_input == 'b' and allow_back:
            return 'BACK'
        if user_input == 'e' and allow_exit:
            return 'EXIT'
        
        try:
            choice = int(user_input)
            if 1 <= choice <= len(options):
                return options[choice - 1]
            else:
                print(f"Please enter a number between 1 and {len(options)}")
        except ValueError:
            valid_options = f"a number between 1 and {len(options)}"
            if allow_back or allow_exit:
                extras = []
                if allow_back:
                    extras.append("'b' for back")
                if allow_exit:
                    extras.append("'e' for exit")
                valid_options += ", " + ", or ".join(extras)
            print(f"Please enter {valid_options}")


def get_input(prompt, default=None, allow_empty=False):
    """Get user input with optional default"""
    if default:
        result = input(f"{prompt} (default: {default}): ").strip()
        return result if result else default
    else:
        while True:
            result = input(f"{prompt}: ").strip()
            if result or allow_empty:
                return result
            print("This field is required. Please enter a value.")


def get_yes_no(prompt, default_yes=True):
    """Get yes/no answer from user"""
    default_text = "Y/n" if default_yes else "y/N"
    while True:
        response = input(f"{prompt} [{default_text}]: ").strip().lower()
        if not response:
            return default_yes
        if response in ['y', 'yes']:
            return True
        if response in ['n', 'no']:
            return False
        print("Please enter 'y' or 'n'")


def guideme():
    """Interactive guided workflow for show_metadata"""
    print_header("Show Metadata - Interactive Wizard")
    
    print("Welcome! This wizard will help you set up metadata extraction.")
    print("You can press Ctrl+C at any time to exit.")
    print()
    
    # Step 1: Image Directory
    print_header("Step 1: Image Directory")
    print("Enter the path to the directory containing images to analyze.")
    print("Examples:")
    print("  - C:\\Photos\\Vacation")
    print("  - //server/share/photos")
    print("  - /mnt/photos")
    print()
    
    img_dir = get_input("Image directory path")
    if not Path(img_dir).exists():
        print(f"\nWARNING: Directory does not exist: {img_dir}")
        continue_anyway = get_yes_no("Continue anyway?", default_yes=False)
        if not continue_anyway:
            print("Exiting...")
            return
    
    # Step 2: Recursive Scan
    print_header("Step 2: Recursive Scanning")
    print("Should subdirectories be included in the scan?")
    print()
    
    recursive = get_yes_no("Scan subdirectories recursively?", default_yes=True)
    
    # Step 3: Meta Suffix Display
    print_header("Step 3: Meta Suffix Display")
    print("The meta suffix shows key metadata in a compact format.")
    print("Example: [6/7/2023 2:35P, iPhone 14, 39.9047°N, 116.4074°E, 51m]")
    print()
    
    show_meta_suffix = get_yes_no("Display meta suffix?", default_yes=True)
    
    # Step 4: Geocoding
    print_header("Step 4: Reverse Geocoding")
    print("Reverse geocoding converts GPS coordinates to city/state/country names.")
    print("This requires an internet connection and may take time for large batches.")
    print()
    
    use_geocoding = get_yes_no("Enable reverse geocoding?", default_yes=False)
    
    geocode_user_agent = None
    geocode_delay = None
    geocode_cache = None
    
    if use_geocoding:
        # Step 4a: User Agent
        print("\nOpenStreetMap Nominatim requires a custom User-Agent string.")
        print("This identifies your application to their service.")
        default_user_agent = 'Image-Description-Toolkit/ShowMetadata (https://github.com/kelly/Image-Description-Toolkit)'
        print(f"\nDefault: {default_user_agent}")
        print()
        
        custom_agent = get_yes_no("Use default User-Agent?", default_yes=True)
        if custom_agent:
            geocode_user_agent = default_user_agent
        else:
            geocode_user_agent = get_input("Enter custom User-Agent string")
        
        # Step 4b: Delay
        print("\nNominatim recommends 1 second delay between requests.")
        print("Lower delays may result in rate limiting or blocking.")
        print()
        
        use_default_delay = get_yes_no("Use recommended 1 second delay?", default_yes=True)
        if use_default_delay:
            geocode_delay = 1.0
        else:
            while True:
                delay_input = get_input("Enter delay in seconds (minimum 0.5)", "1.0")
                try:
                    geocode_delay = float(delay_input)
                    if geocode_delay < 0.5:
                        print("Delay must be at least 0.5 seconds")
                        continue
                    break
                except ValueError:
                    print("Please enter a valid number")
        
        # Step 4c: Cache
        print("\nGeocoding results can be cached to avoid repeated API calls.")
        print("This is especially useful when re-scanning the same locations.")
        print()
        
        use_cache = get_yes_no("Enable geocoding cache?", default_yes=True)
        if use_cache:
            default_cache = str(Path(__file__).parent / "geocode_cache.json")
            print(f"\nDefault cache location: {default_cache}")
            print()
            
            use_default_cache = get_yes_no("Use default cache location?", default_yes=True)
            if use_default_cache:
                geocode_cache = default_cache
            else:
                geocode_cache = get_input("Enter cache file path")
    
    # Step 5: CSV Export
    print_header("Step 5: CSV Export")
    print("Export metadata to a CSV file for analysis in Excel or other tools.")
    print()
    
    export_csv = get_yes_no("Export to CSV?", default_yes=False)
    
    csv_out = None
    if export_csv:
        # Generate default CSV name based on input directory
        dir_name = Path(img_dir).name or "metadata"
        default_csv = str(Path(__file__).parent / f"metadata_{dir_name}.csv")
        print(f"\nDefault CSV location: {default_csv}")
        print()
        
        use_default_csv = get_yes_no("Use default CSV location?", default_yes=True)
        if use_default_csv:
            csv_out = default_csv
        else:
            csv_out = get_input("Enter CSV file path")
    
    # Build command
    print_header("Command Summary")
    
    cmd_parts = ["python", "show_metadata.py", img_dir]
    
    if recursive:
        cmd_parts.append("--recursive")
    
    if not show_meta_suffix:
        cmd_parts.append("--no-meta-suffix")
    
    if use_geocoding:
        cmd_parts.append("--geocode")
        if geocode_user_agent:
            cmd_parts.extend(["--geocode-user-agent", geocode_user_agent])
        if geocode_delay:
            cmd_parts.extend(["--geocode-delay", str(geocode_delay)])
        if geocode_cache:
            cmd_parts.extend(["--geocode-cache", geocode_cache])
    
    if csv_out:
        cmd_parts.extend(["--csv-out", csv_out])
    
    # Display the command
    command_str = " ".join(f'"{part}"' if ' ' in part else part for part in cmd_parts)
    print("The following command will be executed:\n")
    print(f"  {command_str}\n")
    
    # Save command to file
    command_file = Path(__file__).parent / ".show_metadata_last_command"
    try:
        with open(command_file, 'w', encoding='utf-8') as f:
            f.write(f"# Show Metadata - Last Command\n")
            f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(command_str + "\n")
        print(f"Command saved to: {command_file}")
        print()
    except Exception as e:
        print(f"Note: Could not save command to file: {e}")
        print()
    
    # Ask to run or exit
    action = get_choice("What would you like to do?", 
                       ["Run this command now", "Just show the command (don't run)", "Go back to modify settings"],
                       allow_exit=True)
    
    if action == 'EXIT':
        print("Exiting...")
        return
    
    if action == "Go back to modify settings":
        return guideme()
    
    if action == "Run this command now":
        print_header("Running Metadata Extraction")
        print(f"Executing: {command_str}\n")
        
        try:
            # Build arguments
            directory = Path(img_dir)
            extractor = MetadataExtractor()

            geocoder = None
            if use_geocoding:
                cache_path = Path(geocode_cache) if geocode_cache else None
                geocoder = NominatimGeocoder(
                    user_agent=geocode_user_agent,
                    delay_seconds=geocode_delay,
                    cache_path=cache_path
                )
                if not geocoder._requests_available:
                    print("WARNING: requests not installed; install with 'pip install requests' to enable geocoding.")

            csv_path = Path(csv_out) if csv_out else None

            extractor.process_directory(
                directory,
                recursive=recursive,
                show_meta_suffix=show_meta_suffix,
                geocoder=geocoder,
                csv_out=csv_path,
            )
                
        except Exception as e:
            print(f"\nError running metadata extraction: {e}")
            print("\nYou can manually run the command shown above.")
    
    elif action == "Just show the command (don't run)":
        print("\nCopy and paste this command to run it:\n")
        print(f"  {command_str}\n")
        
        # Ask if they want to go back or exit
        next_action = get_choice("What next?", ["Go back to modify settings", "Exit"], allow_exit=True)
        if next_action == "Go back to modify settings":
            return guideme()
        print("Exiting...")
        return


if __name__ == '__main__':
    # Check if --guideme flag is present
    if '--guideme' in sys.argv:
        try:
            guideme()
        except KeyboardInterrupt:
            print("\n\nCancelled by user. Exiting...")
            sys.exit(0)
        except Exception as e:
            print(f"\nError: {e}")
            sys.exit(1)
    else:
        main()
