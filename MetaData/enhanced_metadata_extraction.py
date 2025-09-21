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
    
    # pyexiv2 for comprehensive metadata
    try:
        import pyexiv2
        imports['pyexiv2'] = True
        print("✓ pyexiv2 available for comprehensive metadata")
    except ImportError:
        imports['pyexiv2'] = False
        print("✗ pyexiv2 not available (install with: pip install pyexiv2)")
    
    # Raw binary EXIF reading
    try:
        import struct
        imports['struct'] = True
        print("✓ struct available for binary EXIF parsing")
    except ImportError:
        imports['struct'] = False
        print("✗ struct not available")
    
    # Location services for geocoding
    try:
        import requests
        imports['requests'] = True
        print("✓ requests available for geocoding services")
    except ImportError:
        imports['requests'] = False
        print("✗ requests not available (install with: pip install requests)")
    
    try:
        import geopy
        from geopy.geocoders import Nominatim
        imports['geopy'] = True
        print("✓ geopy available for advanced geocoding")
    except ImportError:
        imports['geopy'] = False
        print("✗ geopy not available (install with: pip install geopy)")
    
    return imports

def extract_exif_with_exifread(file_path: Path, imports: Dict) -> Dict[str, Any]:
    """Extract EXIF data using exifread library as fallback"""
    if not imports['exifread']:
        return {"error": "exifread not available"}
    
    try:
        import exifread
        
        exif_data = {}
        camera_info = {}
        gps_info = {}
        technical_settings = {}
        
        with open(file_path, 'rb') as f:
            tags = exifread.process_file(f, details=True)
            
            for tag_name, tag_value in tags.items():
                try:
                    # Skip thumbnail data
                    if 'thumbnail' in tag_name.lower():
                        continue
                    
                    # Convert tag value to string
                    value_str = str(tag_value)
                    
                    # Camera information
                    if tag_name in ['Image Make', 'Image Model', 'Image Software', 
                                  'EXIF LensModel', 'EXIF LensMake']:
                        key = tag_name.replace('Image ', '').replace('EXIF ', '').lower()
                        camera_info[key] = value_str
                    
                    # Technical settings
                    elif tag_name in ['EXIF ISOSpeedRatings', 'EXIF ExposureTime', 'EXIF FNumber', 
                                    'EXIF FocalLength', 'EXIF Flash', 'EXIF WhiteBalance']:
                        key = tag_name.replace('EXIF ', '').lower()
                        technical_settings[key] = value_str
                    
                    # GPS information
                    elif tag_name.startswith('GPS'):
                        gps_key = tag_name.replace('GPS ', '').lower()
                        gps_info[gps_key] = value_str
                    
                    # Datetime information
                    elif 'datetime' in tag_name.lower():
                        exif_data[tag_name.lower()] = value_str
                    
                    # Store all other tags
                    else:
                        exif_data[tag_name] = value_str
                        
                except Exception as e:
                    exif_data[f"{tag_name}_error"] = str(e)
        
        # Parse GPS coordinates from exifread format
        if gps_info:
            parsed_gps = parse_exifread_gps(gps_info)
            if parsed_gps:
                gps_info.update(parsed_gps)
        
        return {
            "exif": exif_data,
            "camera_info": camera_info,
            "gps_info": gps_info,
            "technical_settings": technical_settings,
            "extraction_method": "exifread"
        }
        
    except Exception as e:
        return {"error": f"exifread extraction failed: {str(e)}"}

def parse_exifread_gps(gps_data: Dict) -> Optional[Dict[str, Any]]:
    """Parse GPS coordinates from exifread format"""
    try:
        parsed = {}
        
        # Parse latitude
        if 'gpslatitude' in gps_data and 'gpslatituderef' in gps_data:
            lat_str = gps_data['gpslatitude']
            lat_ref = gps_data['gpslatituderef']
            
            # Parse degrees, minutes, seconds format
            if '[' in lat_str and ']' in lat_str:
                # Format: [deg, min, sec]
                coords = lat_str.strip('[]').split(', ')
                if len(coords) >= 3:
                    try:
                        deg = float(coords[0])
                        min_val = float(coords[1])
                        sec = float(coords[2])
                        decimal_lat = deg + (min_val / 60.0) + (sec / 3600.0)
                        
                        if lat_ref.upper() in ['S', 'SOUTH']:
                            decimal_lat = -decimal_lat
                            
                        parsed['latitude'] = decimal_lat
                        parsed['latitude_ref'] = lat_ref
                    except ValueError:
                        pass
        
        # Parse longitude
        if 'gpslongitude' in gps_data and 'gpslongituderef' in gps_data:
            lon_str = gps_data['gpslongitude']
            lon_ref = gps_data['gpslongituderef']
            
            if '[' in lon_str and ']' in lon_str:
                coords = lon_str.strip('[]').split(', ')
                if len(coords) >= 3:
                    try:
                        deg = float(coords[0])
                        min_val = float(coords[1])
                        sec = float(coords[2])
                        decimal_lon = deg + (min_val / 60.0) + (sec / 3600.0)
                        
                        if lon_ref.upper() in ['W', 'WEST']:
                            decimal_lon = -decimal_lon
                            
                        parsed['longitude'] = decimal_lon
                        parsed['longitude_ref'] = lon_ref
                    except ValueError:
                        pass
        
        # Parse altitude
        if 'gpsaltitude' in gps_data:
            alt_str = gps_data['gpsaltitude']
            try:
                altitude = float(alt_str)
                parsed['altitude'] = altitude
                if 'gpsaltituderef' in gps_data:
                    parsed['altitude_ref'] = gps_data['gpsaltituderef']
            except ValueError:
                pass
        
        return parsed if parsed else None
        
    except Exception:
        return None

def extract_metadata_with_pyexiv2(file_path: Path, imports: Dict) -> Dict[str, Any]:
    """Extract metadata using pyexiv2 for comprehensive coverage"""
    if not imports['pyexiv2']:
        return {"error": "pyexiv2 not available"}
    
    try:
        import pyexiv2
        
        with pyexiv2.Image(str(file_path)) as img:
            exif_data = {}
            camera_info = {}
            gps_info = {}
            technical_settings = {}
            xmp_data = {}
            iptc_data = {}
            
            # Extract EXIF
            try:
                exif_dict = img.read_exif()
                for key, value in exif_dict.items():
                    # Categorize EXIF data
                    if key in ['Exif.Image.Make', 'Exif.Image.Model', 'Exif.Image.Software']:
                        camera_key = key.split('.')[-1].lower()
                        camera_info[camera_key] = value
                    elif key.startswith('Exif.GPSInfo'):
                        gps_key = key.split('.')[-1].lower()
                        gps_info[gps_key] = value
                    elif key in ['Exif.Photo.ISOSpeedRatings', 'Exif.Photo.ExposureTime', 
                               'Exif.Photo.FNumber', 'Exif.Photo.FocalLength']:
                        tech_key = key.split('.')[-1].lower()
                        technical_settings[tech_key] = value
                    else:
                        exif_data[key] = value
            except Exception as e:
                exif_data['pyexiv2_exif_error'] = str(e)
            
            # Extract XMP
            try:
                xmp_dict = img.read_xmp()
                xmp_data = xmp_dict
            except Exception as e:
                xmp_data['pyexiv2_xmp_error'] = str(e)
            
            # Extract IPTC
            try:
                iptc_dict = img.read_iptc()
                iptc_data = iptc_dict
            except Exception as e:
                iptc_data['pyexiv2_iptc_error'] = str(e)
        
        return {
            "exif": exif_data,
            "camera_info": camera_info,
            "gps_info": gps_info,
            "technical_settings": technical_settings,
            "xmp": xmp_data,
            "iptc": iptc_data,
            "extraction_method": "pyexiv2"
        }
        
    except Exception as e:
        return {"error": f"pyexiv2 extraction failed: {str(e)}"}

def get_location_info(latitude: float, longitude: float, imports: Dict) -> Dict[str, Any]:
    """Get comprehensive location information from GPS coordinates"""
    location_info = {
        'coordinates': {
            'latitude': latitude,
            'longitude': longitude,
            'coordinate_string': f"{latitude:.6f}, {longitude:.6f}"
        },
        'map_urls': {
            'google_maps': f"https://www.google.com/maps?q={latitude},{longitude}",
            'openstreetmap': f"https://www.openstreetmap.org/?mlat={latitude}&mlon={longitude}&zoom=15",
            'apple_maps': f"http://maps.apple.com/?q={latitude},{longitude}",
            'bing_maps': f"https://www.bing.com/maps?q={latitude},{longitude}"
        }
    }
    
    # Try multiple geocoding services for maximum location info
    location_info['geocoding_results'] = {}
    
    # Try Nominatim (OpenStreetMap) - Free and reliable
    if imports.get('geopy'):
        try:
            from geopy.geocoders import Nominatim
            geolocator = Nominatim(user_agent="image_metadata_extractor")
            location = geolocator.reverse(f"{latitude}, {longitude}", exactly_one=True, timeout=10)
            
            if location:
                address = location.raw.get('address', {})
                location_info['geocoding_results']['nominatim'] = {
                    'full_address': location.address,
                    'country': address.get('country', ''),
                    'country_code': address.get('country_code', ''),
                    'state': address.get('state', ''),
                    'city': address.get('city', address.get('town', address.get('village', ''))),
                    'postcode': address.get('postcode', ''),
                    'road': address.get('road', ''),
                    'house_number': address.get('house_number', ''),
                    'neighbourhood': address.get('neighbourhood', address.get('suburb', '')),
                    'place_type': location.raw.get('type', ''),
                    'importance': location.raw.get('importance', 0),
                    'display_name': location.raw.get('display_name', ''),
                    'boundingbox': location.raw.get('boundingbox', [])
                }
        except Exception as e:
            location_info['geocoding_results']['nominatim'] = {'error': str(e)}
    
    # Try multiple free geocoding APIs
    if imports.get('requests'):
        try:
            import requests
            
            # LocationIQ (free tier available)
            try:
                response = requests.get(
                    f"https://us1.locationiq.com/v1/reverse.php",
                    params={
                        'key': 'demo',  # Demo key - limited usage
                        'lat': latitude,
                        'lon': longitude,
                        'format': 'json'
                    },
                    timeout=5
                )
                if response.status_code == 200:
                    data = response.json()
                    location_info['geocoding_results']['locationiq'] = {
                        'display_name': data.get('display_name', ''),
                        'address': data.get('address', {}),
                        'place_id': data.get('place_id', ''),
                        'licence': data.get('licence', '')
                    }
            except Exception as e:
                location_info['geocoding_results']['locationiq'] = {'error': str(e)}
            
            # BigDataCloud (free reverse geocoding)
            try:
                response = requests.get(
                    f"https://api.bigdatacloud.net/data/reverse-geocode-client",
                    params={
                        'latitude': latitude,
                        'longitude': longitude,
                        'localityLanguage': 'en'
                    },
                    timeout=5
                )
                if response.status_code == 200:
                    data = response.json()
                    location_info['geocoding_results']['bigdatacloud'] = {
                        'locality': data.get('locality', ''),
                        'city': data.get('city', ''),
                        'country_name': data.get('countryName', ''),
                        'country_code': data.get('countryCode', ''),
                        'region': data.get('principalSubdivision', ''),
                        'plus_code': data.get('plusCode', ''),
                        'confidence': data.get('confidence', 0)
                    }
            except Exception as e:
                location_info['geocoding_results']['bigdatacloud'] = {'error': str(e)}
        
        except ImportError:
            pass
    
    # Create a consolidated location summary
    location_info['location_summary'] = consolidate_location_data(location_info['geocoding_results'])
    
    return location_info

def consolidate_location_data(geocoding_results: Dict) -> Dict[str, Any]:
    """Consolidate location data from multiple geocoding sources"""
    consolidated = {
        'country': '',
        'country_code': '',
        'state_region': '',
        'city': '',
        'address': '',
        'postcode': '',
        'confidence': 'unknown',
        'sources_used': []
    }
    
    # Priority order for data sources
    source_priority = ['nominatim', 'bigdatacloud', 'locationiq']
    
    for source in source_priority:
        if source in geocoding_results and 'error' not in geocoding_results[source]:
            data = geocoding_results[source]
            consolidated['sources_used'].append(source)
            
            # Extract country info
            if not consolidated['country']:
                if source == 'nominatim':
                    consolidated['country'] = data.get('country', '')
                    consolidated['country_code'] = data.get('country_code', '')
                elif source == 'bigdatacloud':
                    consolidated['country'] = data.get('country_name', '')
                    consolidated['country_code'] = data.get('country_code', '')
            
            # Extract state/region
            if not consolidated['state_region']:
                if source == 'nominatim':
                    consolidated['state_region'] = data.get('state', '')
                elif source == 'bigdatacloud':
                    consolidated['state_region'] = data.get('region', '')
            
            # Extract city
            if not consolidated['city']:
                if source == 'nominatim':
                    consolidated['city'] = data.get('city', '')
                elif source == 'bigdatacloud':
                    consolidated['city'] = data.get('city', data.get('locality', ''))
            
            # Extract address
            if not consolidated['address']:
                if source == 'nominatim':
                    consolidated['address'] = data.get('full_address', data.get('display_name', ''))
                elif source == 'locationiq':
                    consolidated['address'] = data.get('display_name', '')
            
            # Extract postcode
            if not consolidated['postcode']:
                if source == 'nominatim':
                    consolidated['postcode'] = data.get('postcode', '')
            
            # Set confidence
            if consolidated['confidence'] == 'unknown':
                if source == 'nominatim' and data.get('importance', 0) > 0.5:
                    consolidated['confidence'] = 'high'
                elif source == 'bigdatacloud' and data.get('confidence', 0) > 0.8:
                    consolidated['confidence'] = 'high'
                else:
                    consolidated['confidence'] = 'medium'
    
    # Create readable location string
    location_parts = []
    if consolidated['city']:
        location_parts.append(consolidated['city'])
    if consolidated['state_region'] and consolidated['state_region'] != consolidated['city']:
        location_parts.append(consolidated['state_region'])
    if consolidated['country']:
        location_parts.append(consolidated['country'])
    
    consolidated['readable_location'] = ', '.join(location_parts) if location_parts else 'Location not found'
    
    return consolidated

def extract_all_gps_data(metadata: Dict) -> Dict[str, Any]:
    """Extract and enhance all available GPS data from metadata"""
    gps_data = {}
    
    # Get raw GPS info from metadata
    raw_gps = metadata.get('gps_info', {})
    if not raw_gps:
        return {'status': 'no_gps_data'}
    
    gps_data['raw_gps'] = raw_gps
    
    # Parse coordinates
    try:
        # Handle different GPS coordinate formats
        lat_str = str(raw_gps.get('gpslatitude', ''))
        lon_str = str(raw_gps.get('gpslongitude', ''))
        lat_ref = raw_gps.get('gpslatituderef', '')
        lon_ref = raw_gps.get('gpslongituderef', '')
        
        if lat_str and lon_str:
            lat_parts = []
            lon_parts = []
            
            # Handle pyexiv2 format: "33/1 29/1 3074/100"
            if ' ' in lat_str and '/' in lat_str:
                # Split by spaces first, then parse fractions
                for part in lat_str.split():
                    if '/' in part:
                        num, denom = part.split('/')
                        lat_parts.append(float(num) / float(denom))
                    else:
                        lat_parts.append(float(part))
                        
                for part in lon_str.split():
                    if '/' in part:
                        num, denom = part.split('/')
                        lon_parts.append(float(num) / float(denom))
                    else:
                        lon_parts.append(float(part))
            
            # Handle format like "[33, 29, 1537/50]"
            elif '[' in lat_str:
                lat_str = lat_str.replace('[', '').replace(']', '').replace(' ', '')
                lon_str = lon_str.replace('[', '').replace(']', '').replace(' ', '')
                
                for part in lat_str.split(','):
                    if '/' in part:
                        num, denom = part.split('/')
                        lat_parts.append(float(num) / float(denom))
                    else:
                        lat_parts.append(float(part))
                
                for part in lon_str.split(','):
                    if '/' in part:
                        num, denom = part.split('/')
                        lon_parts.append(float(num) / float(denom))
                    else:
                        lon_parts.append(float(part))
            
            # Handle comma-separated format
            elif ',' in lat_str:
                for part in lat_str.split(','):
                    part = part.strip()
                    if '/' in part:
                        num, denom = part.split('/')
                        lat_parts.append(float(num) / float(denom))
                    else:
                        lat_parts.append(float(part))
                
                for part in lon_str.split(','):
                    part = part.strip()
                    if '/' in part:
                        num, denom = part.split('/')
                        lon_parts.append(float(num) / float(denom))
                    else:
                        lon_parts.append(float(part))
            
            if len(lat_parts) >= 3 and len(lon_parts) >= 3:
                # Convert DMS to decimal
                latitude = lat_parts[0] + lat_parts[1]/60 + lat_parts[2]/3600
                longitude = lon_parts[0] + lon_parts[1]/60 + lon_parts[2]/3600
                
                # Apply hemisphere corrections
                if lat_ref.upper() == 'S':
                    latitude = -latitude
                if lon_ref.upper() == 'W':
                    longitude = -longitude
                
                gps_data['coordinates'] = {
                    'latitude': latitude,
                    'longitude': longitude,
                    'latitude_dms': f"{lat_ref} {lat_parts[0]}°{lat_parts[1]}'{lat_parts[2]:.2f}\"",
                    'longitude_dms': f"{lon_ref} {lon_parts[0]}°{lon_parts[1]}'{lon_parts[2]:.2f}\"",
                    'latitude_ref': lat_ref,
                    'longitude_ref': lon_ref
                }
                
                gps_data['status'] = 'coordinates_extracted'
                
    except Exception as e:
        gps_data['coordinate_parsing_error'] = str(e)
        gps_data['status'] = 'parsing_failed'
    
    # Extract additional GPS metadata
    additional_gps = {}
    
    # Altitude
    if 'gpsaltitude' in raw_gps:
        try:
            alt_str = str(raw_gps['gpsaltitude'])
            if '/' in alt_str:
                num, denom = alt_str.split('/')
                altitude = float(num) / float(denom)
            else:
                altitude = float(alt_str)
            
            alt_ref = raw_gps.get('gpsaltituderef', 0)
            if alt_ref == 1:  # Below sea level
                altitude = -altitude
            
            additional_gps['altitude_meters'] = altitude
            additional_gps['altitude_feet'] = altitude * 3.28084
        except:
            pass
    
    # GPS timestamp
    if 'gpstimestamp' in raw_gps and 'gpsdatestamp' in raw_gps:
        try:
            time_str = str(raw_gps['gpstimestamp'])
            date_str = str(raw_gps['gpsdatestamp'])
            additional_gps['gps_timestamp'] = f"{date_str} {time_str}"
        except:
            pass
    
    # Speed and direction
    if 'gpsspeed' in raw_gps:
        try:
            speed = float(raw_gps['gpsspeed'])
            additional_gps['speed_kmh'] = speed
            additional_gps['speed_mph'] = speed * 0.621371
        except:
            pass
    
    if 'gpsimgdirection' in raw_gps:
        try:
            direction = float(raw_gps['gpsimgdirection'])
            additional_gps['image_direction_degrees'] = direction
            # Convert to compass direction
            directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
                         'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
            compass_dir = directions[int((direction + 11.25) / 22.5) % 16]
            additional_gps['image_direction_compass'] = compass_dir
        except:
            pass
    
    if additional_gps:
        gps_data['additional_info'] = additional_gps
    
    return gps_data

def try_binary_exif_extraction(file_path: Path, imports: Dict) -> Dict[str, Any]:
    """Attempt direct binary EXIF extraction for stubborn files"""
    if not imports['struct']:
        return {"error": "struct not available for binary parsing"}
    
    try:
        import struct
        
        with open(file_path, 'rb') as f:
            # Look for EXIF marker in JPEG files
            data = f.read(65536)  # Read first 64KB
            
            # Find EXIF marker
            exif_pos = data.find(b'Exif\x00\x00')
            if exif_pos == -1:
                return {"error": "No EXIF marker found"}
            
            # This is a simplified binary parser - real implementation would be much more complex
            return {
                "exif_marker_found": True,
                "exif_position": exif_pos,
                "extraction_method": "binary_fallback",
                "note": "Binary EXIF parsing is limited - consider using specialized tools"
            }
            
    except Exception as e:
        return {"error": f"Binary extraction failed: {str(e)}"}

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
    """Extract comprehensive and properly parsed image metadata using multiple methods"""
    metadata = {
        "extraction_attempts": [],
        "extraction_success": False
    }
    
    if not imports['PIL']:
        metadata['error'] = "PIL not available for image metadata"
        # Add comprehensive analysis
        metadata['comprehensive_analysis'] = analyze_image_comprehensively(metadata, file_path)
        
        return metadata
    
    # Try multiple extraction methods in order of preference
    extraction_methods = []
    
    # Method 1: Try pyexiv2 first (most comprehensive)
    if imports['pyexiv2']:
        try:
            print(f"    Trying pyexiv2 extraction...")
            pyexiv2_result = extract_metadata_with_pyexiv2(file_path, imports)
            if 'error' not in pyexiv2_result:
                metadata.update(pyexiv2_result)
                metadata['extraction_success'] = True
                metadata['primary_extraction_method'] = 'pyexiv2'
                extraction_methods.append(("pyexiv2", "success"))
                print(f"    ✓ pyexiv2 extraction successful")
            else:
                extraction_methods.append(("pyexiv2", pyexiv2_result['error']))
                print(f"    ✗ pyexiv2 failed: {pyexiv2_result['error']}")
        except Exception as e:
            extraction_methods.append(("pyexiv2", f"Exception: {str(e)}"))
            print(f"    ✗ pyexiv2 exception: {str(e)}")
    
    # Method 2: Try PIL extraction (fallback)
    if not metadata.get('extraction_success'):
        try:
            print(f"    Trying PIL extraction...")
            pil_result = extract_pil_metadata(file_path, imports)
            if pil_result.get('exif') or pil_result.get('camera_info') or pil_result.get('gps_info'):
                # Merge results
                for key, value in pil_result.items():
                    if key not in metadata or not metadata[key]:
                        metadata[key] = value
                metadata['extraction_success'] = True
                if 'primary_extraction_method' not in metadata:
                    metadata['primary_extraction_method'] = 'PIL'
                extraction_methods.append(("PIL", "success"))
                print(f"    ✓ PIL extraction successful")
            else:
                extraction_methods.append(("PIL", "No EXIF data found"))
                print(f"    ✗ PIL found no EXIF data")
        except Exception as e:
            extraction_methods.append(("PIL", f"Exception: {str(e)}"))
            print(f"    ✗ PIL exception: {str(e)}")
    
    # Method 3: Try exifread extraction (secondary fallback)
    if imports['exifread'] and (not metadata.get('extraction_success') or 
                               not metadata.get('gps_info') or not metadata.get('camera_info')):
        try:
            print(f"    Trying exifread extraction...")
            exifread_result = extract_exif_with_exifread(file_path, imports)
            if 'error' not in exifread_result:
                # Merge results, don't overwrite existing good data
                for key, value in exifread_result.items():
                    if key == 'extraction_method':
                        continue
                    if key not in metadata or not metadata[key]:
                        metadata[key] = value
                    elif isinstance(metadata[key], dict) and isinstance(value, dict):
                        # Merge dictionaries
                        for subkey, subvalue in value.items():
                            if subkey not in metadata[key] or not metadata[key][subkey]:
                                metadata[key][subkey] = subvalue
                
                metadata['extraction_success'] = True
                if 'primary_extraction_method' not in metadata:
                    metadata['primary_extraction_method'] = 'exifread'
                metadata['exifread_supplemented'] = True
                extraction_methods.append(("exifread", "success"))
                print(f"    ✓ exifread extraction successful")
            else:
                extraction_methods.append(("exifread", exifread_result['error']))
                print(f"    ✗ exifread failed: {exifread_result['error']}")
        except Exception as e:
            extraction_methods.append(("exifread", f"Exception: {str(e)}"))
            print(f"    ✗ exifread exception: {str(e)}")
    
    # Method 4: Binary fallback for desperate cases
    if not metadata.get('extraction_success'):
        try:
            print(f"    Trying binary EXIF extraction...")
            binary_result = try_binary_exif_extraction(file_path, imports)
            if 'error' not in binary_result:
                metadata.update(binary_result)
                extraction_methods.append(("binary", "success"))
                print(f"    ✓ Binary extraction found EXIF marker")
            else:
                extraction_methods.append(("binary", binary_result['error']))
                print(f"    ✗ Binary extraction failed: {binary_result['error']}")
        except Exception as e:
            extraction_methods.append(("binary", f"Exception: {str(e)}"))
            print(f"    ✗ Binary extraction exception: {str(e)}")
    
    # Ensure we have the basic structure even if extraction failed
    if 'exif' not in metadata:
        metadata['exif'] = {}
    if 'camera_info' not in metadata:
        metadata['camera_info'] = {}
    if 'gps_info' not in metadata:
        metadata['gps_info'] = {}
    if 'technical_settings' not in metadata:
        metadata['technical_settings'] = {}
    
    # Add basic image info using PIL
    try:
        from PIL import Image
        with Image.open(file_path) as image:
            metadata['basic_info'] = {
                "format": image.format,
                "mode": image.mode,
                "size_pixels": image.size,
                "width": image.width,
                "height": image.height,
                "megapixels": round((image.width * image.height) / 1000000, 2),
                "has_transparency": image.mode in ('RGBA', 'LA') or 'transparency' in image.info
            }
            
            # Try to get color profile
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
        metadata['basic_info_error'] = str(e)
    
    # Record extraction attempts for debugging
    metadata['extraction_attempts'] = extraction_methods
    
    # Enhanced device detection
    metadata['device_info'] = detect_device_info(metadata.get('camera_info', {}), 
                                                metadata.get('exif', {}), file_path)
    
    # Final success assessment
    if not metadata.get('extraction_success'):
        metadata['extraction_success'] = bool(metadata.get('exif') or 
                                            metadata.get('camera_info') or 
                                            metadata.get('gps_info'))
    
    return metadata

def extract_pil_metadata(file_path: Path, imports: Dict) -> Dict[str, Any]:
    """Extract metadata using PIL (original method, now separated)"""
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS, GPSTAGS
        
        with Image.open(file_path) as image:
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
            
            return {
                'exif': exif_data,
                'camera_info': camera_info,
                'gps_info': gps_info,
                'technical_settings': technical_settings,
                'xmp_parsed': xmp_data,
                'extraction_method': 'PIL'
            }
            
    except Exception as e:
        return {'error': f"PIL extraction failed: {str(e)}"}

def analyze_image_comprehensively(metadata: Dict, file_path: Path) -> Dict[str, Any]:
    """Provide comprehensive analysis of the image metadata"""
    analysis = {}
    
    # Enhanced GPS Analysis with location services
    if metadata.get('gps_info'):
        print("    🌍 Analyzing GPS and location data...")
        
        # Extract all GPS data
        gps_analysis = extract_all_gps_data(metadata)
        
        # If we have coordinates, get location information
        if gps_analysis.get('coordinates'):
            coords = gps_analysis['coordinates']
            imports = setup_location_imports()
            
            if imports['requests'] or imports['geopy']:
                print("    📍 Getting location information from geocoding services...")
                location_info = get_location_info(
                    coords['latitude'], 
                    coords['longitude'], 
                    imports
                )
                gps_analysis['location_info'] = location_info
            else:
                print("    ⚠️  Install 'requests' and/or 'geopy' for location names")
        
        analysis['gps_analysis'] = gps_analysis
    else:
        analysis['gps_analysis'] = {'status': 'no_gps_data'}
    
    # Technical Quality Assessment
    tech_analysis = {}
    basic_info = metadata.get('basic_info', {})
    technical_settings = metadata.get('technical_settings', {})
    
    # Resolution assessment
    if basic_info.get('width') and basic_info.get('height'):
        width, height = basic_info['width'], basic_info['height']
        megapixels = basic_info.get('megapixels', 0)
        
        if megapixels > 20:
            tech_analysis['resolution_quality'] = 'High (>20MP)'
        elif megapixels > 10:
            tech_analysis['resolution_quality'] = 'Medium-High (10-20MP)'
        elif megapixels > 5:
            tech_analysis['resolution_quality'] = 'Medium (5-10MP)'
        else:
            tech_analysis['resolution_quality'] = 'Low (<5MP)'
        
        # Aspect ratio
        aspect_ratio = width / height
        common_ratios = {
            (4/3): '4:3 (Standard)',
            (3/2): '3:2 (DSLR)',
            (16/9): '16:9 (Widescreen)',
            (1/1): '1:1 (Square)',
            (21/9): '21:9 (Ultra-wide)'
        }
        
        closest_ratio = min(common_ratios.keys(), key=lambda x: abs(x - aspect_ratio))
        if abs(closest_ratio - aspect_ratio) < 0.1:
            tech_analysis['aspect_ratio'] = common_ratios[closest_ratio]
        else:
            tech_analysis['aspect_ratio'] = f'{aspect_ratio:.2f}:1 (Custom)'
    
    # Camera settings analysis
    if technical_settings:
        settings_analysis = {}
        
        # ISO analysis
        if 'isospeedratings' in technical_settings:
            try:
                iso = int(technical_settings['isospeedratings'])
                if iso <= 100:
                    settings_analysis['iso_assessment'] = 'Excellent light (ISO ≤100)'
                elif iso <= 400:
                    settings_analysis['iso_assessment'] = 'Good light (ISO 100-400)'
                elif iso <= 1600:
                    settings_analysis['iso_assessment'] = 'Moderate light (ISO 400-1600)'
                elif iso <= 6400:
                    settings_analysis['iso_assessment'] = 'Low light (ISO 1600-6400)'
                else:
                    settings_analysis['iso_assessment'] = 'Very low light (ISO >6400)'
                settings_analysis['iso_value'] = iso
            except:
                pass
        
        # Aperture analysis
        if 'fnumber' in technical_settings:
            try:
                f_str = technical_settings['fnumber']
                if '/' in f_str:
                    num, denom = f_str.split('/')
                    f_number = float(num) / float(denom)
                else:
                    f_number = float(f_str)
                
                if f_number <= 1.4:
                    settings_analysis['aperture_assessment'] = 'Very wide aperture (f/≤1.4) - Shallow DOF'
                elif f_number <= 2.8:
                    settings_analysis['aperture_assessment'] = 'Wide aperture (f/1.4-2.8) - Portrait/Low light'
                elif f_number <= 5.6:
                    settings_analysis['aperture_assessment'] = 'Medium aperture (f/2.8-5.6) - General use'
                elif f_number <= 11:
                    settings_analysis['aperture_assessment'] = 'Narrow aperture (f/5.6-11) - Landscape'
                else:
                    settings_analysis['aperture_assessment'] = 'Very narrow aperture (f/>11) - Deep DOF'
                settings_analysis['f_number'] = f_number
            except:
                pass
        
        # Shutter speed analysis
        if 'exposuretime' in technical_settings:
            try:
                exp_str = technical_settings['exposuretime']
                if '/' in exp_str:
                    num, denom = exp_str.split('/')
                    shutter_speed = float(num) / float(denom)
                else:
                    shutter_speed = float(exp_str)
                
                if shutter_speed >= 1:
                    settings_analysis['shutter_assessment'] = f'Long exposure ({shutter_speed}s) - Creative/Night'
                elif shutter_speed >= 1/30:
                    settings_analysis['shutter_assessment'] = f'Slow shutter (1/{int(1/shutter_speed)}) - Motion blur risk'
                elif shutter_speed >= 1/250:
                    settings_analysis['shutter_assessment'] = f'Normal shutter (1/{int(1/shutter_speed)}) - General use'
                elif shutter_speed >= 1/1000:
                    settings_analysis['shutter_assessment'] = f'Fast shutter (1/{int(1/shutter_speed)}) - Action'
                else:
                    settings_analysis['shutter_assessment'] = f'Very fast shutter (1/{int(1/shutter_speed)}) - Sports/Wildlife'
                settings_analysis['shutter_speed_seconds'] = shutter_speed
            except:
                pass
        
        tech_analysis['camera_settings_analysis'] = settings_analysis
    
    # Device capability assessment
    device_analysis = {}
    device_info = metadata.get('device_info', {})
    camera_info = metadata.get('camera_info', {})
    
    if device_info.get('category'):
        category = device_info['category']
        if category == 'smart_glasses':
            device_analysis['device_capabilities'] = {
                'primary_use': 'Hands-free recording, POV content',
                'typical_scenarios': 'Social media, documentation, AR experiences',
                'strengths': 'Convenience, unique perspective, always available',
                'limitations': 'Fixed focal length, limited manual controls'
            }
        elif category == 'smartphone':
            device_analysis['device_capabilities'] = {
                'primary_use': 'General photography, social media',
                'typical_scenarios': 'Daily life, travel, social sharing',
                'strengths': 'Computational photography, convenience, editing',
                'limitations': 'Small sensor, limited optical zoom'
            }
        elif category == 'dslr_mirrorless':
            device_analysis['device_capabilities'] = {
                'primary_use': 'Professional/enthusiast photography',
                'typical_scenarios': 'Portraits, landscapes, professional work',
                'strengths': 'Large sensor, manual controls, lens variety',
                'limitations': 'Size, weight, complexity'
            }
    
    analysis['technical_analysis'] = tech_analysis
    analysis['device_analysis'] = device_analysis
    
    # File format and quality assessment
    format_analysis = {}
    if basic_info.get('format'):
        format_type = basic_info['format'].upper()
        
        format_info = {
            'JPEG': {
                'type': 'Lossy compression',
                'best_for': 'General photography, web use, sharing',
                'characteristics': 'Smaller files, good compatibility'
            },
            'HEIC': {
                'type': 'Modern efficient compression',
                'best_for': 'Apple devices, high quality with small files',
                'characteristics': 'Better compression than JPEG, newer format'
            },
            'HEIF': {
                'type': 'Modern efficient compression',
                'best_for': 'Apple devices, high quality with small files',
                'characteristics': 'Better compression than JPEG, newer format'
            },
            'PNG': {
                'type': 'Lossless compression',
                'best_for': 'Screenshots, graphics with transparency',
                'characteristics': 'Larger files, perfect quality'
            },
            'TIFF': {
                'type': 'Uncompressed or lossless',
                'best_for': 'Professional archival, editing',
                'characteristics': 'Very large files, perfect quality'
            }
        }
        
        if format_type in format_info:
            format_analysis['format_assessment'] = format_info[format_type]
        
        format_analysis['format'] = format_type
    
    analysis['format_analysis'] = format_analysis
    
    return analysis

def setup_location_imports() -> Dict[str, bool]:
    """Setup location-specific imports"""
    imports = {}
    
    try:
        import requests
        imports['requests'] = True
    except ImportError:
        imports['requests'] = False
    
    try:
        import geopy
        imports['geopy'] = True
    except ImportError:
        imports['geopy'] = False
    
    return imports

def detect_device_info(camera_info: Dict, exif_data: Dict, file_path: Path) -> Dict[str, Any]:
    """Enhanced device detection with multiple data sources"""
    device_info = {}
    
    # Get device information from camera_info or exif_data
    make = camera_info.get('make') or exif_data.get('Image.Make') or exif_data.get('make', '')
    model = camera_info.get('model') or exif_data.get('Image.Model') or exif_data.get('model', '')
    
    if make and model:
        device_info['device_type'] = 'camera'
        device_info['full_name'] = f"{make} {model}"
        
        # Identify device categories
        make_lower = make.lower()
        model_lower = model.lower()
        
        if 'iphone' in model_lower:
            device_info['category'] = 'smartphone'
            device_info['brand'] = 'Apple'
        elif 'meta' in make_lower or 'ray-ban' in model_lower:
            device_info['category'] = 'smart_glasses'
            device_info['brand'] = 'Meta/Ray-Ban'
        elif any(brand in make_lower for brand in ['canon', 'nikon', 'sony', 'fuji']):
            device_info['category'] = 'dslr_mirrorless'
            device_info['brand'] = make
        else:
            device_info['category'] = 'unknown_camera'
            device_info['brand'] = make
    
    # Detect screenshots (typically have no camera info but specific dimensions)
    elif not camera_info and file_path.suffix.upper() == '.PNG':
        device_info['device_type'] = 'screenshot'
        device_info['category'] = 'screenshot'
        
        # Would need basic_info for dimensions - placeholder for now
        device_info['likely_source'] = 'Unknown screenshot'
    
    return device_info

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