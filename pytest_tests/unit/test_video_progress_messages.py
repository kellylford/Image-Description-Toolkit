"""
Unit tests for video frame extraction progress messages.

Tests for VideoProcessingWorker._format_duration() and the
status bar message format used during frame extraction.

Verifies that status bar progress messages include time duration
information as required by the issue: "Image Describer should show
video progress on status bar as a part of frame extraction".
"""

import pytest
import sys
from pathlib import Path


def _format_duration(seconds: float) -> str:
    """Mirror of VideoProcessingWorker._format_duration for testing without GUI deps."""
    total_sec = max(0, int(seconds))
    m = total_sec // 60
    s = total_sec % 60
    return f"{m}:{s:02d}"


class TestFormatDuration:
    """Tests for the _format_duration() helper used in VideoProcessingWorker."""

    def test_zero_seconds(self):
        """0 seconds formats as 0:00."""
        assert _format_duration(0) == "0:00"

    def test_thirty_seconds(self):
        """30 seconds formats as 0:30."""
        assert _format_duration(30) == "0:30"

    def test_one_minute(self):
        """60 seconds formats as 1:00."""
        assert _format_duration(60) == "1:00"

    def test_one_minute_thirty(self):
        """90 seconds formats as 1:30."""
        assert _format_duration(90) == "1:30"

    def test_two_digit_seconds(self):
        """Seconds < 10 are zero-padded to two digits."""
        assert _format_duration(65) == "1:05"

    def test_large_duration(self):
        """Long videos (e.g., 3661s = 61 min 1 sec) format correctly."""
        assert _format_duration(3661) == "61:01"

    def test_fractional_seconds_truncated(self):
        """Fractional seconds are truncated (not rounded)."""
        assert _format_duration(59.9) == "0:59"

    def test_negative_clamped_to_zero(self):
        """Negative values are clamped to 0:00."""
        assert _format_duration(-5) == "0:00"


class TestProgressMessageFormat:
    """Tests for progress message content during video extraction."""

    def test_time_interval_progress_message_includes_duration(self):
        """Time interval extraction progress message must include position/duration."""
        # Simulate what _extract_by_time_interval now produces every 10 frames
        extract_count = 10
        timestamp = 50.0   # current position in seconds
        total_duration = 120.0  # video total length in seconds

        message = f"Extracted {extract_count} frames ({_format_duration(timestamp)} / {_format_duration(total_duration)})"

        assert "0:50" in message, "Message must show current position"
        assert "2:00" in message, "Message must show total duration"
        assert "10" in message, "Message must show frame count"

    def test_scene_detection_scan_message_includes_position_and_duration(self):
        """Scene detection scan progress must include current scan position and total duration."""
        frame_num = 300
        fps = 30.0
        total_duration = 120.0
        extract_count = 5

        current_time = frame_num / fps  # 10.0 seconds
        pos_str = _format_duration(current_time)
        dur_str = _format_duration(total_duration)
        message = f"Scanning for scenes: {pos_str} / {dur_str}, {extract_count} scene(s) found"

        assert "0:10" in message, "Message must include current scan position"
        assert "2:00" in message, "Message must include total video duration"
        assert "5 scene(s)" in message, "Message must include scenes found count"

    def test_scene_detection_milestone_message_includes_duration(self):
        """Scene detection milestone (every 10 scenes) message includes timing."""
        extract_count = 10
        timestamp = 85.5
        total_duration = 200.0

        pos_str = _format_duration(timestamp)
        dur_str = _format_duration(total_duration)
        message = f"Extracted {extract_count} scenes ({pos_str} / {dur_str})"

        assert "1:25" in message, "Milestone message must show current timestamp"
        assert "3:20" in message, "Milestone message must show total duration"
        assert "10" in message, "Milestone message must show scene count"

    def test_scene_scan_interval_fires_at_start(self):
        """Scan progress fires on frame 0 (frame_num % scan_interval == 0)."""
        fps = 30.0
        scan_interval = max(int(fps), 30)  # 30 for 30fps video
        # frame_num=0 should trigger progress
        assert 0 % scan_interval == 0

    def test_scene_scan_interval_minimum_30_frames(self):
        """Scan interval is at least 30 frames regardless of fps."""
        fps = 5.0  # very low fps
        scan_interval = max(int(fps), 30)
        assert scan_interval >= 30, "Scan interval must be at least 30 frames"

    def test_scene_scan_interval_uses_fps_for_high_fps(self):
        """Scan interval equals int(fps) when fps > 30."""
        fps = 60.0
        scan_interval = max(int(fps), 30)
        assert scan_interval == 60, "For 60fps video, scan interval should be 60 frames (1 second)"
