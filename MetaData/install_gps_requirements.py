#!/usr/bin/env python3
"""
Install Required Libraries for GPS Location Extraction

This script installs the required Python libraries for enhanced GPS location extraction.
"""

import subprocess
import sys

def install_package(package):
    """Install a package using pip"""
    try:
        print(f"Installing {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✓ {package} installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install {package}: {str(e)}")
        return False

def main():
    print("=" * 60)
    print("INSTALLING REQUIRED LIBRARIES FOR GPS LOCATION EXTRACTION")
    print("=" * 60)
    
    # Required packages for enhanced GPS location extraction
    packages = [
        "geopy",      # For Nominatim (OpenStreetMap) geocoding
        "requests",   # For additional geocoding APIs
    ]
    
    # Optional packages that were mentioned in your original script
    optional_packages = [
        "pillow",     # For image metadata extraction
        "exifread",   # For enhanced EXIF parsing
        "opencv-python",  # For video metadata
    ]
    
    print("Installing required packages for GPS location extraction:")
    print()
    
    success_count = 0
    
    for package in packages:
        if install_package(package):
            success_count += 1
        print()
    
    print(f"Required packages: {success_count}/{len(packages)} installed successfully")
    
    # Ask about optional packages
    print("\nOptional packages for enhanced metadata extraction:")
    install_optional = input("Install optional packages? (y/n): ").lower().strip()
    
    if install_optional in ['y', 'yes']:
        print()
        for package in optional_packages:
            install_package(package)
            print()
    
    print("=" * 60)
    print("INSTALLATION COMPLETE")
    print("=" * 60)
    
    if success_count == len(packages):
        print("✅ All required packages installed successfully!")
        print("You can now run the improved GPS location extractor.")
    else:
        print("⚠️  Some packages failed to install. GPS location extraction may not work properly.")
    
    print("\nNext steps:")
    print("1. Run your original metadata extraction script on your images")
    print("2. Run the improved GPS location extractor on the JSON results")
    print("3. Optional: Register for free GeoNames account at https://www.geonames.org/login")

if __name__ == "__main__":
    main()