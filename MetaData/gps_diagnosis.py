#!/usr/bin/env python3
"""
GPS Location Diagnosis Tool

This script diagnoses why GPS location extraction might not be working
and tests the geocoding services.
"""

import json
import sys
from pathlib import Path

def test_imports():
    """Test if required libraries are available"""
    print("🔧 Testing required libraries:")
    print()
    
    results = {}
    
    # Test geopy
    try:
        import geopy
        from geopy.geocoders import Nominatim
        results['geopy'] = True
        print("✓ geopy (Nominatim geocoding) - Available")
    except ImportError:
        results['geopy'] = False
        print("✗ geopy - NOT AVAILABLE")
        print("  Install with: pip install geopy")
    
    # Test requests
    try:
        import requests
        results['requests'] = True
        print("✓ requests (Additional geocoding APIs) - Available")
    except ImportError:
        results['requests'] = False
        print("✗ requests - NOT AVAILABLE")
        print("  Install with: pip install requests")
    
    print()
    return results

def test_geocoding_services(lat=40.7128, lon=-74.0060):  # New York City coordinates
    """Test geocoding services with known coordinates"""
    print(f"🌍 Testing geocoding services with coordinates: {lat}, {lon} (NYC)")
    print()
    
    imports = test_imports()
    
    # Test Nominatim
    if imports.get('geopy'):
        try:
            from geopy.geocoders import Nominatim
            geolocator = Nominatim(user_agent="gps_test")
            location = geolocator.reverse(f"{lat}, {lon}", timeout=10)
            if location:
                print(f"✓ Nominatim working: {location.address}")
            else:
                print("✗ Nominatim: No result returned")
        except Exception as e:
            print(f"✗ Nominatim error: {str(e)}")
    
    # Test BigDataCloud
    if imports.get('requests'):
        try:
            import requests
            response = requests.get(
                "https://api.bigdatacloud.net/data/reverse-geocode-client",
                params={'latitude': lat, 'longitude': lon, 'localityLanguage': 'en'},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                locality = data.get('locality', 'Unknown')
                print(f"✓ BigDataCloud working: {locality}")
            else:
                print(f"✗ BigDataCloud HTTP error: {response.status_code}")
        except Exception as e:
            print(f"✗ BigDataCloud error: {str(e)}")
    
    print()

def analyze_json_file(json_path):
    """Analyze a JSON file to see what GPS data is present"""
    print(f"📄 Analyzing JSON file: {json_path}")
    print()
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error reading JSON: {str(e)}")
        return
    
    # Check structure
    detailed_results = data.get('detailed_results', {})
    if not detailed_results:
        print("❌ No 'detailed_results' found in JSON file")
        return
    
    print(f"📊 Found {len(detailed_results)} files in JSON")
    print()
    
    files_with_gps = 0
    gps_examples = []
    
    for file_path, file_data in detailed_results.items():
        # Look for GPS data in various locations
        gps_found = False
        gps_info = None
        
        # Check different possible paths for GPS data
        paths_to_check = [
            ['image_metadata', 'gps_info'],
            ['gps_info'],
            ['image_metadata', 'comprehensive_analysis', 'gps_analysis'],
        ]
        
        for path in paths_to_check:
            current = file_data
            for key in path:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    current = None
                    break
            
            if current and isinstance(current, dict) and len(current) > 1:
                gps_info = current
                gps_found = True
                break
        
        if gps_found:
            files_with_gps += 1
            
            # Look for actual coordinates
            has_coords = False
            lat = gps_info.get('latitude')
            lon = gps_info.get('longitude')
            
            if lat is not None and lon is not None:
                has_coords = True
                if len(gps_examples) < 3:  # Store first 3 examples
                    gps_examples.append({
                        'file': file_path,
                        'lat': lat,
                        'lon': lon,
                        'gps_data': gps_info
                    })
            
            print(f"📍 {Path(file_path).name}")
            print(f"    GPS data found: {len(gps_info)} fields")
            if has_coords:
                print(f"    Coordinates: {lat}, {lon}")
            else:
                print(f"    Raw GPS fields: {list(gps_info.keys())}")
                # Try to extract coordinates from raw data
                raw_lat = gps_info.get('gpslatitude', gps_info.get('GPSLatitude'))
                raw_lon = gps_info.get('gpslongitude', gps_info.get('GPSLongitude'))
                if raw_lat or raw_lon:
                    print(f"    Raw coordinates found but not parsed: lat={raw_lat}, lon={raw_lon}")
            print()
    
    print(f"📊 Summary:")
    print(f"   Total files: {len(detailed_results)}")
    print(f"   Files with GPS data: {files_with_gps}")
    print(f"   Files with parsed coordinates: {len(gps_examples)}")
    
    if gps_examples:
        print(f"\n🧪 Testing geocoding with found coordinates:")
        for example in gps_examples[:1]:  # Test with first example
            print(f"   File: {Path(example['file']).name}")
            test_geocoding_services(example['lat'], example['lon'])
    elif files_with_gps > 0:
        print(f"\n⚠️  GPS data found but coordinates not properly parsed!")
        print(f"This is likely why location names weren't extracted.")
        print(f"The GPS coordinate parsing in your script may need fixing.")
    else:
        print(f"\n❌ No GPS data found in any files.")
        print(f"This means your images don't have GPS information embedded.")

def main():
    print("=" * 70)
    print("GPS LOCATION DIAGNOSIS TOOL")
    print("=" * 70)
    print()
    
    # Test basic setup
    print("🔍 STEP 1: Testing basic setup")
    imports = test_imports()
    
    if not imports.get('geopy') and not imports.get('requests'):
        print("❌ No geocoding libraries available!")
        print("Install required libraries with:")
        print("   python install_gps_requirements.py")
        print("or manually:")
        print("   pip install geopy requests")
        return
    
    print("🌐 STEP 2: Testing geocoding services")
    test_geocoding_services()
    
    # Analyze JSON file if provided
    if len(sys.argv) > 1:
        json_path = Path(sys.argv[1])
        if json_path.exists():
            print("📋 STEP 3: Analyzing your JSON file")
            analyze_json_file(json_path)
        else:
            print(f"❌ JSON file not found: {json_path}")
    else:
        print("💡 To analyze your JSON file, run:")
        print("   python gps_diagnosis.py your_metadata_file.json")
    
    print()
    print("=" * 70)
    print("DIAGNOSIS COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    main()