"""
Video frame extraction for idt_core.

Extracts frames from video files and stores them in the .idt/frames/ directory
so they can be described by the pipeline like regular images.

Two extraction modes:
  - interval: one frame every N seconds (good for continuous footage)
  - scene: extract on scene changes using frame difference threshold (good for events)

Requires: pip install opencv-python

Usage:
    extractor = VideoExtractor(project)
    frame_paths = extractor.extract(video_path, mode="interval", interval=5)
    # frame_paths are image files in .idt/frames/<video_stem>/
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator, List, Optional

from .project import Project


@dataclass
class VideoExtractionOptions:
    mode: str = "interval"           # "interval" or "scene"
    interval_seconds: float = 5.0   # used when mode="interval"
    scene_threshold: float = 30.0   # used when mode="scene", 0-100 (lower=more sensitive)
    max_frames: Optional[int] = None
    on_progress: Optional[Callable[[int, str], None]] = None


@dataclass
class VideoExtractionResult:
    video_path: Path
    frames_dir: Path
    frame_paths: List[Path]
    duration_seconds: float = 0.0
    fps: float = 0.0


class VideoExtractor:
    """Extract frames from a video file into .idt/frames/<video_stem>/."""

    def __init__(self, project: Project):
        self.project = project

    def extract(
        self,
        video_path: Path,
        options: Optional[VideoExtractionOptions] = None,
    ) -> VideoExtractionResult:
        """
        Extract frames from video_path.
        Frames are written to .idt/frames/<video_stem>/ and named frame_0001.jpg, etc.
        Returns VideoExtractionResult.frames_dir for use as a scan directory.
        """
        try:
            import cv2
        except ImportError:
            raise ImportError(
                "opencv-python is required for video support: pip install opencv-python"
            )

        opts = options or VideoExtractionOptions()
        frames_dir = self.project.idt_dir / "frames" / video_path.stem
        frames_dir.mkdir(parents=True, exist_ok=True)

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps else 0.0

        frame_paths: List[Path] = []
        prev_gray = None
        frame_number = 0
        saved_count = 0
        interval_frames = max(1, int(fps * opts.interval_seconds))

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            should_save = False

            if opts.mode == "interval":
                should_save = (frame_number % interval_frames == 0)
            elif opts.mode == "scene":
                import numpy as np
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                if prev_gray is None:
                    should_save = True
                else:
                    diff = cv2.absdiff(gray, prev_gray)
                    score = float(np.mean(diff))
                    should_save = score > opts.scene_threshold
                prev_gray = gray

            if should_save:
                if opts.max_frames and saved_count >= opts.max_frames:
                    break
                filename = f"frame_{saved_count + 1:04d}.jpg"
                dest = frames_dir / filename
                cv2.imwrite(str(dest), frame)
                frame_paths.append(dest)
                saved_count += 1
                if opts.on_progress:
                    ts = frame_number / fps
                    opts.on_progress(saved_count, f"{ts:.1f}s")

            frame_number += 1

        cap.release()

        return VideoExtractionResult(
            video_path=video_path,
            frames_dir=frames_dir,
            frame_paths=frame_paths,
            duration_seconds=duration,
            fps=fps,
        )


def extract_frames_to_dir(
    video_path: Path,
    output_dir: Path,
    options: Optional[VideoExtractionOptions] = None,
) -> VideoExtractionResult:
    """
    Extract frames from video_path into output_dir.
    Standalone — does not require a Project object.
    Frames are named frame_0001.jpg, frame_0002.jpg, …
    """
    try:
        import cv2
    except ImportError:
        raise ImportError(
            "opencv-python is required for video support: pip install opencv-python"
        )

    opts = options or VideoExtractionOptions()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps else 0.0

    frame_paths: List[Path] = []
    prev_gray = None
    frame_number = 0
    saved_count = 0
    interval_frames = max(1, int(fps * opts.interval_seconds))

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        should_save = False

        if opts.mode == "interval":
            should_save = (frame_number % interval_frames == 0)
        elif opts.mode == "scene":
            import numpy as np
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if prev_gray is None:
                should_save = True
            else:
                diff = cv2.absdiff(gray, prev_gray)
                score = float(np.mean(diff))
                should_save = score > opts.scene_threshold
            prev_gray = gray

        if should_save:
            if opts.max_frames and saved_count >= opts.max_frames:
                break
            filename = f"frame_{saved_count + 1:04d}.jpg"
            dest = output_dir / filename
            cv2.imwrite(str(dest), frame)
            frame_paths.append(dest)
            saved_count += 1
            if opts.on_progress:
                ts = frame_number / fps
                opts.on_progress(saved_count, f"{ts:.1f}s")

        frame_number += 1

    cap.release()

    return VideoExtractionResult(
        video_path=video_path,
        frames_dir=output_dir,
        frame_paths=frame_paths,
        duration_seconds=duration,
        fps=fps,
    )


def scan_videos(directory: Path) -> Iterator[Path]:
    """Yield all video files under directory, excluding .idt/ and hidden dirs."""
    from .scanner import VIDEO_EXTENSIONS, _is_excluded
    paths = sorted(
        p for p in directory.rglob("*")
        if p.is_file()
        and p.suffix.lower() in VIDEO_EXTENSIONS
        and not _is_excluded(p)
    )
    yield from paths


# ---------------------------------------------------------------------------
# VideoMetadataExtractor — extract GPS/date/camera from video via ffprobe
# ---------------------------------------------------------------------------

import json as _json
import subprocess as _subprocess
import sys as _sys
from datetime import datetime as _datetime
from typing import Any, Dict

_SUBPROCESS_FLAGS = _subprocess.CREATE_NO_WINDOW if _sys.platform == "win32" else 0


class VideoMetadataExtractor:
    """Extract metadata from video files using ffprobe."""

    SUPPORTED_FORMATS = {
        ".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm",
        ".m4v", ".mpg", ".mpeg", ".3gp", ".3g2", ".mts", ".m2ts",
    }

    def __init__(self) -> None:
        self.ffprobe_available = self._check_ffprobe()

    def _check_ffprobe(self) -> bool:
        try:
            r = _subprocess.run(
                ["ffprobe", "-version"],
                capture_output=True, text=True, timeout=5,
                creationflags=_SUBPROCESS_FLAGS,
            )
            return r.returncode == 0
        except (OSError, _subprocess.SubprocessError):
            return False

    def is_supported_video(self, path: Path) -> bool:
        return path.suffix.lower() in self.SUPPORTED_FORMATS

    def extract_metadata(self, video_path: Path) -> Optional[Dict[str, Any]]:
        """Return dict with gps, datetime (ISO string), camera, format_info — or None."""
        if not self.ffprobe_available or not video_path.exists():
            return None
        if not self.is_supported_video(video_path):
            return None
        try:
            result = _subprocess.run(
                ["ffprobe", "-v", "quiet", "-print_format", "json",
                 "-show_format", "-show_streams", str(video_path)],
                capture_output=True, text=True, timeout=30,
                creationflags=_SUBPROCESS_FLAGS,
            )
            if result.returncode != 0:
                return None
            data = _json.loads(result.stdout)
        except (OSError, _subprocess.SubprocessError, _json.JSONDecodeError):
            return None

        fmt_tags = data.get("format", {}).get("tags", {})
        stream_tags: Dict[str, str] = {}
        for s in data.get("streams", []):
            stream_tags.update(s.get("tags", {}))
        all_tags = {**stream_tags, **fmt_tags}
        tags = {k.lower(): v for k, v in all_tags.items()}

        meta: Dict[str, Any] = {}
        gps = self._extract_gps(tags)
        if gps:
            meta["gps"] = gps
        dt = self._extract_datetime(tags)
        if dt:
            meta["datetime"] = dt.isoformat()
        cam = self._extract_camera(tags)
        if cam:
            meta["camera"] = cam
        fmt = data.get("format", {})
        if fmt:
            meta["format_info"] = {
                "duration": float(fmt.get("duration", 0)),
                "size": int(fmt.get("size", 0)),
                "format_name": fmt.get("format_name", "unknown"),
            }
        return meta or None

    def _extract_gps(self, tags: Dict[str, str]) -> Optional[Dict[str, float]]:
        for key in ("location", "com.apple.quicktime.location.iso6709", "gps"):
            if key in tags:
                coords = self._parse_iso6709(tags[key])
                if coords:
                    return coords
        result: Dict[str, float] = {}
        for k in ("latitude", "gps_latitude", "gpslatitude"):
            if k in tags:
                try:
                    result["latitude"] = float(tags[k])
                except (ValueError, TypeError):
                    pass
        for k in ("longitude", "gps_longitude", "gpslongitude"):
            if k in tags:
                try:
                    result["longitude"] = float(tags[k])
                except (ValueError, TypeError):
                    pass
        for k in ("altitude", "gps_altitude", "gpsaltitude"):
            if k in tags:
                try:
                    result["altitude"] = float(tags[k])
                except (ValueError, TypeError):
                    pass
        return result if "latitude" in result and "longitude" in result else None

    def _parse_iso6709(self, s: str) -> Optional[Dict[str, float]]:
        s = s.rstrip("/")
        try:
            i = 1
            while i < len(s) and s[i] not in ("+", "-"):
                i += 1
            lat = float(s[:i])
            rest = s[i:]
            j = 1
            while j < len(rest) and rest[j] not in ("+", "-"):
                j += 1
            lon = float(rest[:j])
            result: Dict[str, float] = {"latitude": lat, "longitude": lon}
            if j < len(rest):
                try:
                    result["altitude"] = float(rest[j:])
                except (ValueError, TypeError):
                    pass
            return result
        except (ValueError, IndexError):
            return None

    def _extract_datetime(self, tags: Dict[str, str]) -> Optional[_datetime]:
        for key in ("creation_time", "com.apple.quicktime.creationdate",
                    "date", "datetime", "datetimeoriginal"):
            if key in tags:
                dt = self._parse_dt(tags[key])
                if dt:
                    return dt
        return None

    def _parse_dt(self, s: str) -> Optional[_datetime]:
        for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ",
                    "%Y-%m-%d %H:%M:%S", "%Y:%m:%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return _datetime.strptime(s, fmt)
            except (ValueError, TypeError):
                pass
        return None

    def _extract_camera(self, tags: Dict[str, str]) -> Optional[Dict[str, str]]:
        cam: Dict[str, str] = {}
        for k in ("make", "manufacturer", "com.apple.quicktime.make"):
            if k in tags and tags[k]:
                cam["make"] = tags[k]
                break
        for k in ("model", "device", "com.apple.quicktime.model"):
            if k in tags and tags[k]:
                cam["model"] = tags[k]
                break
        return cam or None


# ---------------------------------------------------------------------------
# ExifEmbedder — embed GPS/date/camera metadata into JPEG frames from video
# ---------------------------------------------------------------------------

class ExifEmbedder:
    """Embed video-sourced metadata (GPS, datetime, camera) into JPEG frames."""

    def embed_metadata(
        self,
        image_path: Path,
        metadata: Dict[str, Any],
        frame_time: Optional[float] = None,
        source_video_path: Optional[Path] = None,
    ) -> bool:
        """Embed metadata dict into a JPEG's EXIF. Returns True on success."""
        try:
            import piexif
        except ImportError:
            return False

        if metadata is None:
            metadata = {}
        try:
            try:
                exif_dict = piexif.load(str(image_path))
            except Exception:
                exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}}

            if "gps" in metadata:
                gps_ifd = self._build_gps_ifd(metadata["gps"], piexif)
                if gps_ifd:
                    exif_dict["GPS"] = gps_ifd

            if "datetime" in metadata:
                dt = metadata["datetime"]
                if isinstance(dt, str):
                    try:
                        from datetime import datetime as _dt
                        dt = _dt.fromisoformat(dt)
                    except (ValueError, AttributeError):
                        dt = None
                if dt is not None and frame_time is not None:
                    from datetime import timedelta
                    dt = dt + timedelta(seconds=frame_time)
                if dt is not None:
                    dt_str = dt.strftime("%Y:%m:%d %H:%M:%S")
                    exif_dict["0th"][piexif.ImageIFD.DateTime] = dt_str
                    exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = dt_str
                    exif_dict["Exif"][piexif.ExifIFD.DateTimeDigitized] = dt_str

            if "camera" in metadata:
                cam = metadata["camera"]
                if "make" in cam:
                    exif_dict["0th"][piexif.ImageIFD.Make] = cam["make"]
                if "model" in cam:
                    exif_dict["0th"][piexif.ImageIFD.Model] = cam["model"]

            if source_video_path:
                src = f"Extracted from video: {source_video_path}"
                if frame_time is not None:
                    src += f" at {frame_time:.2f}s"
                exif_dict["0th"][piexif.ImageIFD.ImageDescription] = src.encode("utf-8")
                exif_dict["Exif"][piexif.ExifIFD.UserComment] = (
                    b"ASCII\x00\x00\x00" + src.encode("ascii", errors="replace")
                )

            from PIL import Image
            exif_bytes = piexif.dump(exif_dict)
            img = Image.open(image_path)
            img.save(image_path, "JPEG", exif=exif_bytes, quality=95)
            return True
        except Exception:
            return False

    def _build_gps_ifd(self, gps: Dict[str, float], piexif) -> Optional[Dict]:
        try:
            ifd: Dict = {}
            if "latitude" in gps:
                lat = gps["latitude"]
                ifd[piexif.GPSIFD.GPSLatitudeRef] = "N" if lat >= 0 else "S"
                ifd[piexif.GPSIFD.GPSLatitude] = self._dms(abs(lat))
            if "longitude" in gps:
                lon = gps["longitude"]
                ifd[piexif.GPSIFD.GPSLongitudeRef] = "E" if lon >= 0 else "W"
                ifd[piexif.GPSIFD.GPSLongitude] = self._dms(abs(lon))
            if "altitude" in gps:
                alt = gps["altitude"]
                ifd[piexif.GPSIFD.GPSAltitudeRef] = 0 if alt >= 0 else 1
                ifd[piexif.GPSIFD.GPSAltitude] = (int(abs(alt) * 100), 100)
            return ifd or None
        except Exception:
            return None

    def _dms(self, deg: float) -> tuple:
        d = int(deg)
        m_dec = (deg - d) * 60
        m = int(m_dec)
        s = (m_dec - m) * 60
        return ((d, 1), (m, 1), (int(s * 100), 100))
