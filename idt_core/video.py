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
