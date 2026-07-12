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
    Skips .idt/ mirror directories and hidden directories *within* the tree.

    Exclusions are evaluated relative to `directory`, not on the absolute path:
    a scan root that itself lives under a hidden directory (e.g. a git worktree
    under ``.claude/`` or images under ``~/.local/share``) must not exclude
    everything just because an *ancestor* of the root is hidden.
    """
    directory = Path(directory)
    extensions = IMAGE_EXTENSIONS | (VIDEO_EXTENSIONS if include_videos else set())
    matches: list[Path] = []
    for p in directory.rglob("*"):
        if not (p.is_file() and p.suffix.lower() in extensions):
            continue
        try:
            rel = p.relative_to(directory)
        except ValueError:
            rel = p
        if _is_excluded(rel):
            continue
        matches.append(p)
    yield from sorted(matches)


def _is_excluded(path: Path) -> bool:
    """True if the path descends through an .idt/ directory or a hidden directory.

    Expects a path *relative* to the scan root so that hidden ancestors above
    the root are not considered.
    """
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
