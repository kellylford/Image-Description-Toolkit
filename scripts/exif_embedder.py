#!/usr/bin/env python3
"""
EXIF Embedder
Embeds metadata (video provenance and AI-generated descriptions) into image files.
"""

import piexif
import piexif.helper
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from PIL import Image, PngImagePlugin


class UnsupportedFormatError(Exception):
    """Raised when the image format does not support metadata embedding."""
    pass


class ExifEmbedder:
    """Embed metadata into JPEG frames extracted from videos"""
    
    def __init__(self):
        pass
    
    def embed_metadata(self, 
                      image_path: Path, 
                      metadata: Dict[str, Any],
                      frame_time: Optional[float] = None,
                      source_video_path: Optional[Path] = None) -> bool:
        """
        Embed video metadata into a JPEG image as EXIF data.
        
        Args:
            image_path: Path to JPEG file to modify
            metadata: Dict from VideoMetadataExtractor containing:
                - gps: {latitude, longitude, altitude}
                - datetime: datetime object
                - camera: {make, model}
            frame_time: Optional time offset in seconds from video start
            source_video_path: Optional path to source video file
        
        Returns:
            True if successful, False otherwise
        """
        if metadata is None:
            metadata = {}

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
                # VideoMetadataExtractor stores datetime as an ISO string; convert if needed
                if isinstance(dt, str):
                    try:
                        from datetime import datetime as _dt
                        dt = _dt.fromisoformat(dt)
                    except (ValueError, AttributeError):
                        dt = None
                # Add frame time offset if provided
                if dt is not None and frame_time is not None:
                    from datetime import timedelta
                    dt = dt + timedelta(seconds=frame_time)

                if dt is not None:
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
            
            # Add source video path and extraction info
            if source_video_path:
                # Store source video path in ImageDescription
                source_info = f'Extracted from video: {source_video_path}'
                if frame_time is not None:
                    source_info += f' at {frame_time:.2f}s'
                exif_dict['0th'][piexif.ImageIFD.ImageDescription] = source_info.encode('utf-8')

                # Store in UserComment (EXIF requires 8-byte character code prefix for ASCII)
                user_comment = b'ASCII\x00\x00\x00' + source_info.encode('ascii', errors='replace')
                exif_dict['Exif'][piexif.ExifIFD.UserComment] = user_comment
            else:
                # Fallback if no source path provided
                exif_dict['0th'][piexif.ImageIFD.ImageDescription] = b'Extracted from video'
                exif_dict['Exif'][piexif.ExifIFD.UserComment] = b'ASCII\x00\x00\x00Frame extracted with metadata from source video'
            
            # Convert to bytes and save
            exif_bytes = piexif.dump(exif_dict)
            
            # Re-save image with EXIF
            img = Image.open(image_path)
            img.save(image_path, 'JPEG', exif=exif_bytes, quality=95)
            
            return True
            
        except Exception as e:
            print(f"Warning: Could not embed EXIF in {Path(image_path).name}: {e}")
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

    def embed_ai_description(self, image_path: Path, description: str,
                             model: Optional[str] = None,
                             timestamp: Optional[str] = None) -> bool:
        """
        Embed an AI-generated description into image file metadata.

        Writes to EXIF ImageDescription (JPEG/TIFF), PNG tEXt chunk, or WebP EXIF.
        All existing metadata is preserved. For JPEG/TIFF uses lossless EXIF insertion
        (no image re-encoding). For HEIC/HEIF raises UnsupportedFormatError — caller
        should convert to JPEG first.

        Args:
            image_path: Path to the image file to modify.
            description: AI-generated description text to embed.
            model: AI model name used for generating the description (attribution).
            timestamp: Timestamp string for attribution.

        Returns:
            True on success.

        Raises:
            UnsupportedFormatError: Format cannot accept embedded metadata.
            RuntimeError: Write failed for a supported format.
        """
        image_path = Path(image_path)
        suffix = image_path.suffix.lower()

        parts = ['IDT']
        if model:
            parts.append(model)
        if timestamp:
            parts.append(timestamp)
        attribution = ' | '.join(parts)

        if suffix in ('.jpg', '.jpeg', '.tiff', '.tif'):
            return self._embed_jpeg_tiff(image_path, description, attribution)
        elif suffix == '.png':
            return self._embed_png(image_path, description)
        elif suffix == '.webp':
            return self._embed_webp(image_path, description, attribution)
        elif suffix in ('.heic', '.heif'):
            raise UnsupportedFormatError(
                f"{image_path.name}: HEIC/HEIF cannot be written to directly. "
                "Convert to JPEG first, then embed."
            )
        else:
            raise UnsupportedFormatError(
                f"{image_path.name}: format {suffix!r} is not supported for embedding."
            )

    def _embed_jpeg_tiff(self, image_path: Path, description: str, attribution: str) -> bool:
        """Lossless EXIF update for JPEG/TIFF using piexif.insert (no image re-encoding)."""
        try:
            try:
                exif_dict = piexif.load(str(image_path))
            except Exception:
                exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}}

            exif_dict['0th'][piexif.ImageIFD.ImageDescription] = description.encode('utf-8')
            exif_dict['Exif'][piexif.ExifIFD.UserComment] = piexif.helper.UserComment.dump(
                attribution, encoding='unicode'
            )

            exif_bytes = piexif.dump(exif_dict)

            with open(image_path, 'rb') as f:
                image_data = f.read()
            new_image_data = piexif.insert(exif_bytes, image_data)
            with open(image_path, 'wb') as f:
                f.write(new_image_data)

            return True
        except Exception as e:
            raise RuntimeError(f"Failed to embed description in {image_path.name}: {e}") from e

    def _embed_png(self, image_path: Path, description: str) -> bool:
        """Embed description into PNG tEXt metadata chunk, preserving existing text chunks."""
        try:
            img = Image.open(image_path)
            meta = PngImagePlugin.PngInfo()

            existing_text = getattr(img, 'text', {}) or {}
            for key, val in existing_text.items():
                if key != 'Description':
                    try:
                        meta.add_text(key, val)
                    except Exception:
                        pass

            meta.add_text('Description', description)
            img.save(image_path, 'PNG', pnginfo=meta)
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to embed description in {image_path.name}: {e}") from e

    def _embed_webp(self, image_path: Path, description: str, attribution: str) -> bool:
        """Embed description into WebP via EXIF blob (requires re-save at high quality)."""
        try:
            try:
                exif_dict = piexif.load(str(image_path))
            except Exception:
                exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}}

            exif_dict['0th'][piexif.ImageIFD.ImageDescription] = description.encode('utf-8')
            exif_dict['Exif'][piexif.ExifIFD.UserComment] = piexif.helper.UserComment.dump(
                attribution, encoding='unicode'
            )

            exif_bytes = piexif.dump(exif_dict)

            img = Image.open(image_path)
            lossless = img.info.get('lossless', False)
            save_kwargs: Dict[str, Any] = {'exif': exif_bytes}
            if lossless:
                save_kwargs['lossless'] = True
            else:
                save_kwargs['quality'] = 95
            img.save(image_path, 'WEBP', **save_kwargs)
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to embed description in {image_path.name}: {e}") from e


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
