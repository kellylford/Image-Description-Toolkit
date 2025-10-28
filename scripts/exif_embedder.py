#!/usr/bin/env python3
"""
EXIF Embedder for Video Frames
Converts video metadata to EXIF format and embeds in extracted frame JPEGs
"""

import piexif
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from PIL import Image


class ExifEmbedder:
    """Embed metadata into JPEG frames extracted from videos"""
    
    def __init__(self):
        pass
    
    def embed_metadata(self, 
                      image_path: Path, 
                      metadata: Dict[str, Any],
                      frame_time: Optional[float] = None) -> bool:
        """
        Embed video metadata into a JPEG image as EXIF data.
        
        Args:
            image_path: Path to JPEG file to modify
            metadata: Dict from VideoMetadataExtractor containing:
                - gps: {latitude, longitude, altitude}
                - datetime: datetime object
                - camera: {make, model}
            frame_time: Optional time offset in seconds from video start
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Load existing EXIF (if any)
            try:
                exif_dict = piexif.load(str(image_path))
            except Exception:
                # Create new EXIF dict if none exists
                exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}}
            
            # Embed GPS data
            if 'gps' in metadata:
                gps_data = metadata['gps']
                gps_ifd = self._create_gps_ifd(gps_data)
                if gps_ifd:
                    exif_dict['GPS'] = gps_ifd
            
            # Embed datetime
            if 'datetime' in metadata:
                dt = metadata['datetime']
                # Add frame time offset if provided
                if frame_time is not None:
                    from datetime import timedelta
                    dt = dt + timedelta(seconds=frame_time)
                
                dt_str = dt.strftime('%Y:%m:%d %H:%M:%S')
                
                # Set datetime fields
                exif_dict['0th'][piexif.ImageIFD.DateTime] = dt_str
                exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal] = dt_str
                exif_dict['Exif'][piexif.ExifIFD.DateTimeDigitized] = dt_str
            
            # Embed camera info
            if 'camera' in metadata:
                camera = metadata['camera']
                if 'make' in camera:
                    exif_dict['0th'][piexif.ImageIFD.Make] = camera['make']
                if 'model' in camera:
                    exif_dict['0th'][piexif.ImageIFD.Model] = camera['model']
            
            # Add comment indicating source
            exif_dict['0th'][piexif.ImageIFD.ImageDescription] = b'Extracted from video'
            exif_dict['Exif'][piexif.ExifIFD.UserComment] = piexif.helper.UserComment.dump(
                'Frame extracted with metadata from source video'
            )
            
            # Convert to bytes and save
            exif_bytes = piexif.dump(exif_dict)
            
            # Re-save image with EXIF
            img = Image.open(image_path)
            img.save(image_path, 'JPEG', exif=exif_bytes, quality=95)
            
            return True
            
        except Exception as e:
            print(f"Warning: Could not embed EXIF in {image_path.name}: {e}")
            return False
    
    def _create_gps_ifd(self, gps_data: Dict[str, float]) -> Optional[Dict]:
        """
        Create GPS IFD dict from GPS data.
        
        Args:
            gps_data: Dict with latitude, longitude, optional altitude
        
        Returns:
            Dict suitable for piexif GPS IFD
        """
        try:
            gps_ifd = {}
            
            # Latitude
            if 'latitude' in gps_data:
                lat = gps_data['latitude']
                lat_ref = 'N' if lat >= 0 else 'S'
                lat_deg = self._decimal_to_dms(abs(lat))
                
                gps_ifd[piexif.GPSIFD.GPSLatitude] = lat_deg
                gps_ifd[piexif.GPSIFD.GPSLatitudeRef] = lat_ref
            
            # Longitude
            if 'longitude' in gps_data:
                lon = gps_data['longitude']
                lon_ref = 'E' if lon >= 0 else 'W'
                lon_deg = self._decimal_to_dms(abs(lon))
                
                gps_ifd[piexif.GPSIFD.GPSLongitude] = lon_deg
                gps_ifd[piexif.GPSIFD.GPSLongitudeRef] = lon_ref
            
            # Altitude
            if 'altitude' in gps_data:
                alt = gps_data['altitude']
                alt_ref = 0 if alt >= 0 else 1  # 0 = above sea level, 1 = below
                alt_rational = (int(abs(alt) * 100), 100)  # Store as rational number
                
                gps_ifd[piexif.GPSIFD.GPSAltitude] = alt_rational
                gps_ifd[piexif.GPSIFD.GPSAltitudeRef] = alt_ref
            
            return gps_ifd if gps_ifd else None
            
        except Exception:
            return None
    
    def _decimal_to_dms(self, decimal_degrees: float) -> tuple:
        """
        Convert decimal degrees to degrees, minutes, seconds for EXIF.
        
        Args:
            decimal_degrees: Decimal degree value (e.g., 37.7749)
        
        Returns:
            Tuple of three rationals: ((deg, 1), (min, 1), (sec, 100))
        """
        degrees = int(decimal_degrees)
        minutes_decimal = (decimal_degrees - degrees) * 60
        minutes = int(minutes_decimal)
        seconds = (minutes_decimal - minutes) * 60
        
        # Return as rational numbers (numerator, denominator)
        return (
            (degrees, 1),
            (minutes, 1),
            (int(seconds * 100), 100)  # Store seconds with 2 decimal places
        )


def main():
    """Test EXIF embedding"""
    import sys
    from datetime import datetime
    
    if len(sys.argv) < 2:
        print("Usage: python exif_embedder.py <image_file>")
        print("Embeds sample GPS/date metadata for testing")
        sys.exit(1)
    
    image_path = Path(sys.argv[1])
    
    if not image_path.exists():
        print(f"ERROR: File not found: {image_path}")
        sys.exit(1)
    
    # Create sample metadata
    metadata = {
        'gps': {
            'latitude': 37.7749,
            'longitude': -122.4194,
            'altitude': 10.5
        },
        'datetime': datetime(2025, 10, 28, 14, 30, 0),
        'camera': {
            'make': 'Apple',
            'model': 'iPhone 14 Pro'
        }
    }
    
    embedder = ExifEmbedder()
    
    print(f"Embedding metadata into: {image_path}")
    success = embedder.embed_metadata(image_path, metadata)
    
    if success:
        print("✓ Metadata embedded successfully")
    else:
        print("✗ Failed to embed metadata")


if __name__ == '__main__':
    main()
