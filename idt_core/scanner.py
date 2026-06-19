"""
Directory scanner — finds all supported images and videos in a source tree.
Never looks inside .idt/ directories.
"""
from pathlib import Path
from typing import Iterator

IMAGE_EXTENSIONS: frozenset[str] = frozenset({
    ".jpg", ".jpeg",
    ".png",
    ".webp",
    ".tiff", ".tif",
    ".heic", ".heif",
    ".gif",
    ".bmp",
})

VIDEO_EXTENSIONS: frozenset[str] = frozenset({
    ".mp4", ".mov", ".avi", ".mkv", ".m4v", ".wmv", ".mts", ".m2ts",
})

ALL_MEDIA_EXTENSIONS: frozenset[str] = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS


def scan_images(directory: Path, include_videos: bool = False) -> Iterator[Path]:
    """
    Yield all supported image paths under directory, sorted by relative path.
    Skips .idt/ mirror directories and hidden directories.
    """
    extensions = IMAGE_EXTENSIONS | (VIDEO_EXTENSIONS if include_videos else set())
    paths = sorted(
        p for p in directory.rglob("*")
        if p.is_file()
        and p.suffix.lower() in extensions
        and not _is_excluded(p)
    )
    yield from paths


def _is_excluded(path: Path) -> bool:
    """True if the path is inside an .idt/ directory or a hidden directory."""
    return any(
        part.endswith(".idt") or (part.startswith(".") and part != ".")
        for part in path.parts
    )


def is_image(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_EXTENSIONS


def is_video(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXTENSIONS


def is_heic(path: Path) -> bool:
    return path.suffix.lower() in {".heic", ".heif"}
