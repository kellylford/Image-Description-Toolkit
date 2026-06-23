"""
Image metadata extraction and geocoding for idt_core.

Extracts EXIF date, GPS, camera info from images (including HEIC) and optionally
reverse-geocodes GPS coordinates to city/state/country via OpenStreetMap Nominatim.

The extracted metadata feeds directly into AI prompt context so descriptions
include when and where the photo was taken — critical for accessibility.

Usage:
    extractor = MetadataExtractor()
    meta = extractor.extract(path)
    context = meta.prompt_context()   # "Munich, Germany  Sep 12, 2025  iPhone 14 Pro"
    geocoder = NominatimGeocoder(cache_path=~/.idt/geocode_cache.json)
    meta = geocoder.enrich(meta)
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from PIL import Image
    from PIL.ExifTags import TAGS, GPSTAGS
except ImportError:
    raise ImportError("Pillow is required: pip install Pillow")

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    _HEIC_SUPPORT = True
except ImportError:
    _HEIC_SUPPORT = False


@dataclass
class ImageMetadata:
    """Structured metadata extracted from an image file."""
    # Date/time (ISO 8601 string, or None)
    datetime_iso: Optional[str] = None
    # Human-readable date "Sep 12, 2025"
    date_short: Optional[str] = None
    # Camera info
    camera_make: Optional[str] = None
    camera_model: Optional[str] = None
    camera_lens: Optional[str] = None
    # GPS raw
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None
    # Geocoded
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    # Source (for video frames)
    source_video: Optional[str] = None
    source_timestamp: Optional[str] = None
    # Whether date came from EXIF or file mtime
    date_from_exif: bool = False

    def prompt_context(self) -> str:
        """
        One-line context string to prepend to AI prompts.
        Example: "Munich, Germany  Sep 12, 2025  iPhone 14 Pro"
        Returns empty string when nothing useful is available.
        """
        parts: list[str] = []

        # Location
        if self.city and self.state:
            parts.append(f"{self.city}, {self.state}")
        elif self.city and self.country:
            parts.append(f"{self.city}, {self.country}")
        elif self.state:
            parts.append(self.state)
        elif self.country:
            parts.append(self.country)

        # Date
        if self.date_short:
            parts.append(self.date_short)

        # Camera — collapse "Apple iPhone 14 Pro" → "iPhone 14 Pro"
        camera = self._camera_display()
        if camera:
            parts.append(camera)

        return "  ".join(parts)

    def _camera_display(self) -> Optional[str]:
        if not self.camera_model:
            return None
        make = (self.camera_make or "").strip()
        model = self.camera_model.strip()
        if make and not model.lower().startswith(make.lower()):
            return f"{make} {model}"
        return model

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}

    @classmethod
    def from_dict(cls, d: dict) -> "ImageMetadata":
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in d.items() if k in known})


class MetadataExtractor:
    """Extract EXIF metadata from image files."""

    def extract(self, path: Path) -> ImageMetadata:
        """
        Extract all available metadata from an image file.
        Never raises — returns an empty ImageMetadata on any failure.
        Falls back to file mtime when no EXIF date is present.
        """
        meta = ImageMetadata()

        try:
            with Image.open(path) as img:
                raw_exif = img.getexif()
                if raw_exif:
                    exif: dict = {}
                    for tag_id, value in raw_exif.items():
                        tag = TAGS.get(tag_id, tag_id)
                        exif[tag] = value
                    # GPS lives in a sub-IFD
                    try:
                        gps_ifd = raw_exif.get_ifd(0x8825)
                        if gps_ifd:
                            gps: dict = {}
                            for tid, val in gps_ifd.items():
                                gps[GPSTAGS.get(tid, tid)] = val
                            exif["GPSInfo"] = gps
                    except (KeyError, AttributeError):
                        pass

                    self._fill_datetime(meta, exif)
                    self._fill_location(meta, exif)
                    self._fill_camera(meta, exif)
                    self._fill_source(meta, exif)
        except Exception:
            pass

        # Fallback date from mtime when EXIF had none
        if not meta.datetime_iso:
            try:
                mtime = datetime.fromtimestamp(path.stat().st_mtime)
                meta.datetime_iso = mtime.isoformat()
                meta.date_short = _fmt_short(mtime)
                meta.date_from_exif = False
            except Exception:
                pass

        return meta

    # ------------------------------------------------------------------ #

    def _fill_datetime(self, meta: ImageMetadata, exif: dict) -> None:
        for field in ("DateTimeOriginal", "DateTimeDigitized", "DateTime"):
            raw = exif.get(field)
            if not raw:
                continue
            dt = _parse_exif_dt(str(raw))
            if dt:
                meta.datetime_iso = dt.isoformat()
                meta.date_short = _fmt_short(dt)
                meta.date_from_exif = True
                return

    def _fill_location(self, meta: ImageMetadata, exif: dict) -> None:
        gps = exif.get("GPSInfo")
        if gps and isinstance(gps, dict):
            if "GPSLatitude" in gps and "GPSLatitudeRef" in gps:
                lat = _gps_to_decimal(gps["GPSLatitude"])
                if gps["GPSLatitudeRef"] == "S":
                    lat = -lat
                meta.latitude = lat
            if "GPSLongitude" in gps and "GPSLongitudeRef" in gps:
                lon = _gps_to_decimal(gps["GPSLongitude"])
                if gps["GPSLongitudeRef"] == "W":
                    lon = -lon
                meta.longitude = lon
            if "GPSAltitude" in gps:
                alt = float(gps["GPSAltitude"])
                if gps.get("GPSAltitudeRef") == 1:
                    alt = -alt
                meta.altitude = alt

        # Text location fields (some XMP-embedded photos have these)
        for key, attr in (
            ("City", "city"), ("State", "state"), ("Province", "state"),
            ("Country", "country"), ("CountryName", "country"),
        ):
            val = exif.get(key)
            if val:
                setattr(meta, attr, str(val))

    def _fill_camera(self, meta: ImageMetadata, exif: dict) -> None:
        if "Make" in exif:
            meta.camera_make = str(exif["Make"]).strip("\x00").strip()
        if "Model" in exif:
            meta.camera_model = str(exif["Model"]).strip("\x00").strip()
        if "LensModel" in exif:
            meta.camera_lens = str(exif["LensModel"]).strip("\x00").strip()

    def _fill_source(self, meta: ImageMetadata, exif: dict) -> None:
        desc = exif.get("ImageDescription")
        if isinstance(desc, bytes):
            desc = desc.decode("utf-8", errors="ignore")
        if desc and "Extracted from video:" in desc:
            parts = desc.replace("Extracted from video:", "").strip().split(" at ")
            meta.source_video = parts[0].strip()
            if len(parts) > 1:
                meta.source_timestamp = parts[1].strip()


# ------------------------------------------------------------------ #
# Geocoder                                                             #
# ------------------------------------------------------------------ #

class NominatimGeocoder:
    """
    Reverse geocode GPS coordinates → city/state/country using OSM Nominatim.

    Rate-limited to 1 req/s per Nominatim policy. Results cached on disk so
    repeated runs don't re-query the same coordinates.

    Requires: pip install requests
    """

    _USER_AGENT = "IDT/4.5 (+https://github.com/kellylford/Image-Description-Toolkit)"

    def __init__(
        self,
        cache_path: Optional[Path] = None,
        delay_seconds: float = 1.1,
    ):
        self.cache_path = cache_path
        self.delay_seconds = max(delay_seconds, 1.0)
        self._last_request: float = 0.0
        self._cache: dict = {}
        self._requests_ok = False

        try:
            import requests as _r
            self._requests = _r
            self._requests_ok = True
        except ImportError:
            pass

        if self.cache_path and self.cache_path.exists():
            try:
                self._cache = json.loads(self.cache_path.read_text(encoding="utf-8"))
            except Exception:
                pass

    def enrich(self, meta: ImageMetadata) -> ImageMetadata:
        """Add city/state/country to meta if GPS coordinates are present."""
        if meta.latitude is None or meta.longitude is None:
            return meta
        result = self._geocode(meta.latitude, meta.longitude)
        if result:
            meta.city = result.get("city") or meta.city
            meta.state = result.get("state") or meta.state
            meta.country = result.get("country") or meta.country
        return meta

    def _geocode(self, lat: float, lon: float) -> Optional[dict]:
        key = f"{lat:.6f},{lon:.6f}"
        if key in self._cache:
            return self._cache[key]

        if not self._requests_ok:
            return None

        # Rate limit
        elapsed = time.monotonic() - self._last_request
        if elapsed < self.delay_seconds:
            time.sleep(self.delay_seconds - elapsed)
        self._last_request = time.monotonic()

        try:
            resp = self._requests.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={"lat": lat, "lon": lon, "format": "json",
                        "addressdetails": 1, "accept-language": "en"},
                headers={"User-Agent": self._USER_AGENT},
                timeout=10,
            )
            resp.raise_for_status()
            addr = resp.json().get("address", {})
            result = {
                "city": addr.get("city") or addr.get("town") or addr.get("village"),
                "state": addr.get("state"),
                "country": addr.get("country"),
            }
            result = {k: v for k, v in result.items() if v}
            self._cache[key] = result
            self._save_cache()
            return result
        except Exception:
            return None

    def _save_cache(self) -> None:
        if not self.cache_path:
            return
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(
                json.dumps(self._cache, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def _parse_exif_dt(s: str) -> Optional[datetime]:
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _fmt_short(dt: datetime) -> str:
    """'Sep 9, 2025' — no leading zero, cross-platform."""
    return dt.strftime("%b %d, %Y").replace(" 0", " ")


def _gps_to_decimal(coord) -> float:
    def _v(x) -> float:
        if isinstance(x, (tuple, list)) and len(x) == 2:
            n, d = x
            return float(n) / float(d) if float(d) else 0.0
        return float(x)
    try:
        return _v(coord[0]) + _v(coord[1]) / 60.0 + _v(coord[2]) / 3600.0
    except Exception:
        return 0.0
