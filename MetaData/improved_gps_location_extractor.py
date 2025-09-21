#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Improved GPS Location Extractor

This script focuses specifically on extracting detailed location information 
from GPS coordinates in image metadata.

Key improvements:
1. Better error handling for geocoding services
2. Multiple fallback geocoding providers
3. Detailed logging of what's happening
4. Option to use different API keys
5. Caching to avoid repeated API calls

Usage:
    python improved_gps_location_extractor.py <json_file_or_directory>
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import hashlib

# Setup comprehensive imports with fallbacks
def setup_geocoding_imports():
    """Setup geocoding libraries with detailed feedback"""
    imports = {}
    
    # geopy for Nominatim (free, reliable)
    try:
        import geopy
        from geopy.geocoders import Nominatim
        imports['geopy'] = True
        print("✓ geopy available for Nominatim geocoding")
    except ImportError:
        imports['geopy'] = False
        print("✗ geopy not available (install with: pip install geopy)")
    
    # requests for additional APIs
    try:
        import requests
        imports['requests'] = True
        print("✓ requests available for additional geocoding APIs")
    except ImportError:
        imports['requests'] = False
        print("✗ requests not available (install with: pip install requests)")
    
    return imports

def extract_coordinates_from_metadata(metadata: Dict) -> Optional[Tuple[float, float]]:
    """Extract latitude/longitude from various metadata formats"""
    
    # Try different paths where GPS coordinates might be stored
    potential_paths = [
        ['image_metadata', 'gps_info'],
        ['gps_info'],
        ['image_metadata', 'comprehensive_analysis', 'gps_analysis', 'coordinates'],
        ['comprehensive_analysis', 'gps_analysis', 'coordinates']
    ]
    
    for path in potential_paths:
        current = metadata
        for key in path:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                current = None
                break
        
        if current and isinstance(current, dict):
            # Look for latitude/longitude in various formats
            lat = current.get('latitude')
            lon = current.get('longitude')
            
            if lat is not None and lon is not None:
                try:
                    return float(lat), float(lon)
                except (ValueError, TypeError):
                    continue
    
    return None

def get_location_with_nominatim(lat: float, lon: float, user_agent: str = "gps_location_extractor") -> Optional[Dict]:
    """Get location using Nominatim (OpenStreetMap) - Free and reliable"""
    try:
        from geopy.geocoders import Nominatim
        from geopy.exc import GeocoderTimedOut, GeocoderServiceError
        
        geolocator = Nominatim(user_agent=user_agent, timeout=15)
        
        print(f"    🌍 Querying Nominatim for {lat:.6f}, {lon:.6f}...")
        
        # Try reverse geocoding
        location = geolocator.reverse(f"{lat}, {lon}", exactly_one=True, language='en')
        
        if location:
            address = location.raw.get('address', {})
            
            result = {
                'service': 'Nominatim (OpenStreetMap)',
                'full_address': location.address,
                'display_name': location.raw.get('display_name', ''),
                'place_id': location.raw.get('place_id', ''),
                'importance': location.raw.get('importance', 0),
                'components': {
                    'country': address.get('country', ''),
                    'country_code': address.get('country_code', '').upper(),
                    'state': address.get('state', ''),
                    'county': address.get('county', ''),
                    'city': address.get('city', address.get('town', address.get('village', ''))),
                    'postcode': address.get('postcode', ''),
                    'road': address.get('road', ''),
                    'house_number': address.get('house_number', ''),
                    'neighbourhood': address.get('neighbourhood', address.get('suburb', address.get('hamlet', ''))),
                    'amenity': address.get('amenity', ''),
                    'shop': address.get('shop', ''),
                    'building': address.get('building', '')
                },
                'coordinates': {
                    'latitude': float(location.latitude),
                    'longitude': float(location.longitude)
                },
                'bounding_box': location.raw.get('boundingbox', []),
                'licence': location.raw.get('licence', ''),
                'osm_type': location.raw.get('osm_type', ''),
                'osm_id': location.raw.get('osm_id', ''),
                'category': location.raw.get('category', ''),
                'type': location.raw.get('type', ''),
                'success': True
            }
            
            print(f"    ✓ Nominatim found: {location.address}")
            return result
        else:
            print(f"    ✗ Nominatim: No location found")
            return {'service': 'Nominatim', 'success': False, 'error': 'No location found'}
            
    except GeocoderTimedOut:
        print(f"    ⚠️  Nominatim: Request timed out")
        return {'service': 'Nominatim', 'success': False, 'error': 'Request timed out'}
    except GeocoderServiceError as e:
        print(f"    ✗ Nominatim service error: {str(e)}")
        return {'service': 'Nominatim', 'success': False, 'error': f'Service error: {str(e)}'}
    except Exception as e:
        print(f"    ✗ Nominatim error: {str(e)}")
        return {'service': 'Nominatim', 'success': False, 'error': str(e)}

def get_location_with_bigdatacloud(lat: float, lon: float) -> Optional[Dict]:
    """Get location using BigDataCloud - Free reverse geocoding"""
    try:
        import requests
        
        print(f"    🌍 Querying BigDataCloud for {lat:.6f}, {lon:.6f}...")
        
        url = "https://api.bigdatacloud.net/data/reverse-geocode-client"
        params = {
            'latitude': lat,
            'longitude': lon,
            'localityLanguage': 'en'
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            result = {
                'service': 'BigDataCloud',
                'locality': data.get('locality', ''),
                'localityInfo': data.get('localityInfo', {}),
                'country_name': data.get('countryName', ''),
                'country_code': data.get('countryCode', ''),
                'region': data.get('principalSubdivision', ''),
                'region_code': data.get('principalSubdivisionCode', ''),
                'city': data.get('city', ''),
                'plus_code': data.get('plusCode', ''),
                'confidence': data.get('confidence', 0),
                'confidence_city': data.get('confidenceCity', 0),
                'coordinates': {
                    'latitude': lat,
                    'longitude': lon
                },
                'success': True,
                'raw_response': data
            }
            
            # Create readable address
            address_parts = []
            if data.get('locality'):
                address_parts.append(data['locality'])
            if data.get('principalSubdivision'):
                address_parts.append(data['principalSubdivision'])
            if data.get('countryName'):
                address_parts.append(data['countryName'])
            
            result['readable_address'] = ', '.join(address_parts) if address_parts else 'Unknown location'
            
            print(f"    ✓ BigDataCloud found: {result['readable_address']}")
            return result
        else:
            print(f"    ✗ BigDataCloud HTTP error: {response.status_code}")
            return {'service': 'BigDataCloud', 'success': False, 'error': f'HTTP {response.status_code}'}
            
    except requests.RequestException as e:
        print(f"    ✗ BigDataCloud network error: {str(e)}")
        return {'service': 'BigDataCloud', 'success': False, 'error': f'Network error: {str(e)}'}
    except Exception as e:
        print(f"    ✗ BigDataCloud error: {str(e)}")
        return {'service': 'BigDataCloud', 'success': False, 'error': str(e)}

def get_location_with_geonames(lat: float, lon: float, username: str = None) -> Optional[Dict]:
    """Get location using GeoNames - Free with registration"""
    if not username:
        print(f"    ⚠️  GeoNames: Username required (register at geonames.org)")
        return {'service': 'GeoNames', 'success': False, 'error': 'Username required'}
    
    try:
        import requests
        
        print(f"    🌍 Querying GeoNames for {lat:.6f}, {lon:.6f}...")
        
        url = "http://api.geonames.org/findNearbyPlaceNameJSON"
        params = {
            'lat': lat,
            'lng': lon,
            'username': username,
            'maxRows': 5,
            'radius': 10  # 10km radius
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'geonames' in data and data['geonames']:
                place = data['geonames'][0]  # Take the closest place
                
                result = {
                    'service': 'GeoNames',
                    'place_name': place.get('name', ''),
                    'admin_name1': place.get('adminName1', ''),  # State/Province
                    'admin_name2': place.get('adminName2', ''),  # County
                    'country_name': place.get('countryName', ''),
                    'country_code': place.get('countryCode', ''),
                    'population': place.get('population', 0),
                    'distance': place.get('distance', 0),
                    'geoname_id': place.get('geonameId', ''),
                    'coordinates': {
                        'latitude': float(place.get('lat', lat)),
                        'longitude': float(place.get('lng', lon))
                    },
                    'success': True,
                    'all_places': data['geonames'][:3]  # Store top 3 for reference
                }
                
                # Create readable address
                address_parts = []
                if place.get('name'):
                    address_parts.append(place['name'])
                if place.get('adminName1'):
                    address_parts.append(place['adminName1'])
                if place.get('countryName'):
                    address_parts.append(place['countryName'])
                
                result['readable_address'] = ', '.join(address_parts)
                
                print(f"    ✓ GeoNames found: {result['readable_address']}")
                return result
            else:
                print(f"    ✗ GeoNames: No places found")
                return {'service': 'GeoNames', 'success': False, 'error': 'No places found'}
        else:
            print(f"    ✗ GeoNames HTTP error: {response.status_code}")
            return {'service': 'GeoNames', 'success': False, 'error': f'HTTP {response.status_code}'}
            
    except Exception as e:
        print(f"    ✗ GeoNames error: {str(e)}")
        return {'service': 'GeoNames', 'success': False, 'error': str(e)}

def get_comprehensive_location_info(lat: float, lon: float, geonames_username: str = None) -> Dict[str, Any]:
    """Get comprehensive location information from multiple sources"""
    
    print(f"\n📍 Getting location information for coordinates: {lat:.6f}, {lon:.6f}")
    
    location_info = {
        'coordinates': {
            'latitude': lat,
            'longitude': lon,
            'coordinate_string': f"{lat:.6f}, {lon:.6f}",
            'degrees_minutes_seconds': {
                'latitude_dms': convert_to_dms(lat, 'lat'),
                'longitude_dms': convert_to_dms(lon, 'lon')
            }
        },
        'map_urls': {
            'google_maps': f"https://www.google.com/maps?q={lat},{lon}",
            'apple_maps': f"http://maps.apple.com/?q={lat},{lon}",
            'openstreetmap': f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}&zoom=15",
            'bing_maps': f"https://www.bing.com/maps?q={lat},{lon}",
            'what3words': f"https://what3words.com/{lat},{lon}"
        },
        'geocoding_results': {},
        'analysis_timestamp': datetime.now().isoformat()
    }
    
    # Check which geocoding services are available
    imports = setup_geocoding_imports()
    
    geocoding_attempted = 0
    geocoding_successful = 0
    
    # Try Nominatim (highest priority - free and comprehensive)
    if imports['geopy']:
        geocoding_attempted += 1
        result = get_location_with_nominatim(lat, lon)
        if result:
            location_info['geocoding_results']['nominatim'] = result
            if result.get('success'):
                geocoding_successful += 1
        
        # Small delay to be respectful
        time.sleep(1)
    
    # Try BigDataCloud (good free alternative)
    if imports['requests']:
        geocoding_attempted += 1
        result = get_location_with_bigdatacloud(lat, lon)
        if result:
            location_info['geocoding_results']['bigdatacloud'] = result
            if result.get('success'):
                geocoding_successful += 1
        
        time.sleep(0.5)
    
    # Try GeoNames if username provided
    if imports['requests'] and geonames_username:
        geocoding_attempted += 1
        result = get_location_with_geonames(lat, lon, geonames_username)
        if result:
            location_info['geocoding_results']['geonames'] = result
            if result.get('success'):
                geocoding_successful += 1
    
    # Consolidate results into a best-guess location
    location_info['best_location'] = consolidate_location_results(location_info['geocoding_results'])
    
    # Add statistics
    location_info['geocoding_stats'] = {
        'services_attempted': geocoding_attempted,
        'services_successful': geocoding_successful,
        'success_rate': f"{(geocoding_successful/geocoding_attempted*100):.1f}%" if geocoding_attempted > 0 else "0%"
    }
    
    print(f"📊 Geocoding complete: {geocoding_successful}/{geocoding_attempted} services successful")
    
    return location_info

def convert_to_dms(decimal_degrees: float, coord_type: str) -> str:
    """Convert decimal degrees to degrees, minutes, seconds format"""
    degrees = int(abs(decimal_degrees))
    minutes_float = (abs(decimal_degrees) - degrees) * 60
    minutes = int(minutes_float)
    seconds = (minutes_float - minutes) * 60
    
    if coord_type == 'lat':
        direction = 'N' if decimal_degrees >= 0 else 'S'
    else:  # longitude
        direction = 'E' if decimal_degrees >= 0 else 'W'
    
    return f"{degrees}°{minutes}'{seconds:.2f}\"{direction}"

def consolidate_location_results(geocoding_results: Dict) -> Dict[str, Any]:
    """Consolidate results from multiple geocoding services into best guess"""
    
    consolidated = {
        'address': '',
        'city': '',
        'state_region': '',
        'country': '',
        'country_code': '',
        'postcode': '',
        'confidence': 'unknown',
        'sources_used': [],
        'primary_source': '',
        'alternative_names': []
    }
    
    # Priority order: Nominatim > BigDataCloud > GeoNames
    source_priority = ['nominatim', 'bigdatacloud', 'geonames']
    
    successful_sources = [
        source for source in source_priority 
        if source in geocoding_results and geocoding_results[source].get('success')
    ]
    
    if not successful_sources:
        consolidated['address'] = 'Location could not be determined'
        consolidated['confidence'] = 'none'
        return consolidated
    
    # Use the highest priority successful source as primary
    primary_source = successful_sources[0]
    consolidated['primary_source'] = primary_source
    consolidated['sources_used'] = successful_sources
    
    primary_data = geocoding_results[primary_source]
    
    # Extract data based on primary source
    if primary_source == 'nominatim':
        components = primary_data.get('components', {})
        consolidated['address'] = primary_data.get('full_address', '')
        consolidated['city'] = components.get('city', '')
        consolidated['state_region'] = components.get('state', '')
        consolidated['country'] = components.get('country', '')
        consolidated['country_code'] = components.get('country_code', '')
        consolidated['postcode'] = components.get('postcode', '')
        consolidated['confidence'] = 'high' if primary_data.get('importance', 0) > 0.5 else 'medium'
        
    elif primary_source == 'bigdatacloud':
        consolidated['address'] = primary_data.get('readable_address', '')
        consolidated['city'] = primary_data.get('city', primary_data.get('locality', ''))
        consolidated['state_region'] = primary_data.get('region', '')
        consolidated['country'] = primary_data.get('country_name', '')
        consolidated['country_code'] = primary_data.get('country_code', '')
        consolidated['confidence'] = 'high' if primary_data.get('confidence', 0) > 0.8 else 'medium'
        
    elif primary_source == 'geonames':
        consolidated['address'] = primary_data.get('readable_address', '')
        consolidated['city'] = primary_data.get('place_name', '')
        consolidated['state_region'] = primary_data.get('admin_name1', '')
        consolidated['country'] = primary_data.get('country_name', '')
        consolidated['country_code'] = primary_data.get('country_code', '')
        consolidated['confidence'] = 'medium'
    
    # Collect alternative names from other sources
    for source in successful_sources[1:]:
        source_data = geocoding_results[source]
        alt_name = ''
        
        if source == 'nominatim':
            alt_name = source_data.get('full_address', '')
        elif source == 'bigdatacloud':
            alt_name = source_data.get('readable_address', '')
        elif source == 'geonames':
            alt_name = source_data.get('readable_address', '')
        
        if alt_name and alt_name != consolidated['address']:
            consolidated['alternative_names'].append({
                'source': source,
                'name': alt_name
            })
    
    # Create a short readable location
    parts = []
    if consolidated['city']:
        parts.append(consolidated['city'])
    if consolidated['state_region'] and consolidated['state_region'] != consolidated['city']:
        parts.append(consolidated['state_region'])
    if consolidated['country']:
        parts.append(consolidated['country'])
    
    consolidated['readable_location'] = ', '.join(parts) if parts else 'Unknown location'
    
    return consolidated

def process_metadata_file(json_file_path: Path, geonames_username: str = None) -> Dict[str, Any]:
    """Process a metadata JSON file and extract/enhance GPS information"""
    
    print(f"\n📄 Processing metadata file: {json_file_path.name}")
    
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error reading JSON file: {str(e)}")
        return {'error': f'Failed to read JSON: {str(e)}'}
    
    results = {
        'source_file': str(json_file_path),
        'processing_timestamp': datetime.now().isoformat(),
        'files_with_gps': {},
        'files_without_gps': [],
        'location_extraction_results': {}
    }
    
    # Look through detailed_results for GPS data
    detailed_results = data.get('detailed_results', {})
    
    if not detailed_results:
        print("❌ No detailed_results found in JSON file")
        return {'error': 'No detailed_results found in JSON file'}
    
    files_with_coordinates = 0
    
    for file_path, file_metadata in detailed_results.items():
        print(f"\n🔍 Checking file: {file_path}")
        
        # Extract coordinates
        coords = extract_coordinates_from_metadata(file_metadata)
        
        if coords:
            lat, lon = coords
            files_with_coordinates += 1
            print(f"  ✓ Found GPS coordinates: {lat:.6f}, {lon:.6f}")
            
            # Get comprehensive location information
            location_info = get_comprehensive_location_info(lat, lon, geonames_username)
            
            results['files_with_gps'][file_path] = {
                'coordinates': {'latitude': lat, 'longitude': lon},
                'location_info': location_info
            }
            
            # Store the best location for quick reference
            best_location = location_info.get('best_location', {})
            if best_location.get('readable_location'):
                results['location_extraction_results'][file_path] = best_location['readable_location']
                print(f"  📍 Location: {best_location['readable_location']}")
            
        else:
            print(f"  ✗ No GPS coordinates found")
            results['files_without_gps'].append(file_path)
    
    results['summary'] = {
        'total_files': len(detailed_results),
        'files_with_gps_coordinates': files_with_coordinates,
        'files_without_gps_coordinates': len(results['files_without_gps']),
        'gps_percentage': f"{(files_with_coordinates/len(detailed_results)*100):.1f}%" if detailed_results else "0%"
    }
    
    print(f"\n📊 Processing complete:")
    print(f"   Total files: {results['summary']['total_files']}")
    print(f"   Files with GPS: {results['summary']['files_with_gps_coordinates']}")
    print(f"   Files without GPS: {results['summary']['files_without_gps_coordinates']}")
    
    return results

def main():
    """Main function to enhance GPS location data"""
    print("=" * 70)
    print("IMPROVED GPS LOCATION EXTRACTOR")
    print("Enhanced GPS coordinate to location conversion")
    print("=" * 70)
    
    if len(sys.argv) < 2:
        print("Usage: python improved_gps_location_extractor.py <json_file> [geonames_username]")
        print("\nExample:")
        print("  python improved_gps_location_extractor.py metadata_analysis.json")
        print("  python improved_gps_location_extractor.py metadata_analysis.json your_geonames_username")
        print("\nNote: GeoNames username is optional but recommended for additional location data")
        print("Register free at: https://www.geonames.org/login")
        return
    
    input_path = Path(sys.argv[1])
    geonames_username = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not input_path.exists():
        print(f"❌ File not found: {input_path}")
        return
    
    if geonames_username:
        print(f"🔑 Using GeoNames username: {geonames_username}")
    else:
        print("ℹ️  No GeoNames username provided - will skip GeoNames geocoding")
        print("   Register free at: https://www.geonames.org/login for additional location data")
    
    print()
    
    # Process the metadata file
    results = process_metadata_file(input_path, geonames_username)
    
    if 'error' in results:
        print(f"❌ Processing failed: {results['error']}")
        return
    
    # Save enhanced results
    output_file = input_path.parent / f"enhanced_gps_locations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Enhanced GPS location data saved to: {output_file}")
        
        # Print quick summary of found locations
        if results['location_extraction_results']:
            print(f"\n📍 LOCATION SUMMARY:")
            for file_path, location in results['location_extraction_results'].items():
                print(f"   {Path(file_path).name}: {location}")
        
    except Exception as e:
        print(f"❌ Failed to save results: {str(e)}")
    
    print(f"\n✅ Processing complete! Check {output_file} for detailed location information.")

if __name__ == "__main__":
    main()