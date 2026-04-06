"""
Unit tests for stats_analysis.parse_workflow_log - video frame extraction parsing.

Regression test for the bug where idt stats reported 0 frames extracted because
parse_workflow_log only scanned the main workflow log, but the video frame extractor
writes its "Total frames extracted:" and "Total video files found:" summary lines
exclusively to its own frame_extractor_*.log file.

Fix: stats_analysis.parse_workflow_log now also globs for frame_extractor_*.log and
reads those two summary lines from the largest matching file.
"""

import sys
from pathlib import Path
import pytest

# Add project root so we can import analysis/
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "analysis"))

from stats_analysis import parse_workflow_log


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_workflow_dir(tmp_path: Path, wf_name: str = "wf_Test_ollama_moondream_narrative_20260405_120000") -> Path:
    """Create a minimal workflow directory structure."""
    wf_dir = tmp_path / wf_name
    logs_dir = wf_dir / "logs"
    logs_dir.mkdir(parents=True)
    (wf_dir / "descriptions").mkdir()
    return wf_dir


def _write_workflow_log(logs_dir: Path, name: str = "workflow_20260405_120000.log", extra: str = "") -> Path:
    """Write a minimal workflow log file."""
    content = (
        "2026-04-05 12:00:00,001 - workflow_orchestrator - INFO - Start time: 2026-04-05 12:00:00\n"
        "2026-04-05 12:30:00,001 - workflow_orchestrator - INFO - End time: 2026-04-05 12:30:00\n"
        "2026-04-05 12:30:00,002 - workflow_orchestrator - INFO - Total execution time: 1800.0 seconds (30.0 minutes)\n"
        "2026-04-05 12:30:00,003 - workflow_orchestrator - INFO - Total files processed: 5\n"
        + extra
    )
    log_path = logs_dir / name
    log_path.write_text(content, encoding="utf-8")
    return log_path


def _write_frame_extractor_log(logs_dir: Path, name: str, videos: int, frames: int) -> Path:
    """Write a frame_extractor log file that contains the FINAL PROCESSING SUMMARY block."""
    content = (
        f"INFO - Video Frame Extractor started - (2026-04-05 23:30:45,827)\n"
        f"INFO - Total video files found: {videos} - (2026-04-05 23:30:46,492)\n"
        f"INFO - Extraction mode: time_interval - (2026-04-05 23:30:45,830)\n"
        f"INFO - ============================================================\n"
        f"INFO - FINAL PROCESSING SUMMARY\n"
        f"INFO - ============================================================\n"
        f"INFO - Videos processed: {videos} - (2026-04-05 23:51:15,253)\n"
        f"INFO - Total frames extracted: {frames} - (2026-04-05 23:51:15,253)\n"
        f"INFO - Total frames saved: {frames} - (2026-04-05 23:51:15,253)\n"
        f"INFO - Total processing time: 1229.11 seconds - (2026-04-05 23:51:15,253)\n"
    )
    log_path = logs_dir / name
    log_path.write_text(content, encoding="utf-8")
    return log_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestParseWorkflowLogFrames:
    """Tests that parse_workflow_log correctly reads frame/video counts from frame_extractor logs."""

    def test_frames_extracted_from_frame_extractor_log(self, tmp_path):
        """
        The primary regression test: frames_extracted must come from frame_extractor_*.log,
        not from the workflow log (which never contains that summary line).
        """
        wf_dir = _make_workflow_dir(tmp_path)
        logs_dir = wf_dir / "logs"
        log_path = _write_workflow_log(logs_dir)
        _write_frame_extractor_log(logs_dir, "frame_extractor_20260405_233046.log",
                                   videos=50, frames=300)

        stats = parse_workflow_log(log_path)

        assert stats["frames_extracted"] == 300, (
            "Expected 300 frames from frame_extractor log; "
            f"got {stats['frames_extracted']}. "
            "The fix should read 'Total frames extracted:' from frame_extractor_*.log."
        )

    def test_videos_found_from_frame_extractor_log(self, tmp_path):
        """videos_found must also come from the frame_extractor log."""
        wf_dir = _make_workflow_dir(tmp_path)
        logs_dir = wf_dir / "logs"
        log_path = _write_workflow_log(logs_dir)
        _write_frame_extractor_log(logs_dir, "frame_extractor_20260405_233046.log",
                                   videos=42, frames=210)

        stats = parse_workflow_log(log_path)

        assert stats["videos_found"] == 42, (
            f"Expected 42 videos_found; got {stats['videos_found']}."
        )

    def test_zero_frames_when_no_frame_extractor_log(self, tmp_path):
        """Workflow with no video step should still report 0 frames (no crash, no change)."""
        wf_dir = _make_workflow_dir(tmp_path)
        logs_dir = wf_dir / "logs"
        log_path = _write_workflow_log(logs_dir)
        # No frame_extractor log written intentionally

        stats = parse_workflow_log(log_path)

        assert stats["frames_extracted"] == 0
        assert stats["videos_found"] == 0

    def test_largest_log_used_when_multiple_frame_extractor_logs(self, tmp_path):
        """
        When two frame_extractor logs exist (the 10-line stub + the real one),
        the largest file should be used.
        """
        wf_dir = _make_workflow_dir(tmp_path)
        logs_dir = wf_dir / "logs"
        log_path = _write_workflow_log(logs_dir)

        # Stub log (no summary, very small)
        stub = logs_dir / "frame_extractor_20260405_233045.log"
        stub.write_text(
            "INFO - Video Frame Extractor started - (2026-04-05 23:30:45,827)\n"
            "INFO - Log file: frame_extractor.log\n",
            encoding="utf-8",
        )

        # Real log (has summary, larger)
        _write_frame_extractor_log(logs_dir, "frame_extractor_20260405_233046.log",
                                   videos=1227, frames=4482)

        stats = parse_workflow_log(log_path)

        assert stats["frames_extracted"] == 4482, (
            "Should use the larger frame_extractor log (the real run), "
            f"but got {stats['frames_extracted']}."
        )
        assert stats["videos_found"] == 1227

    def test_frames_not_overwritten_by_workflow_log_lines(self, tmp_path):
        """
        Even if the workflow log has a stale/zero-valued frames line,
        the frame_extractor log's values take precedence (it is parsed after).
        """
        wf_dir = _make_workflow_dir(tmp_path)
        logs_dir = wf_dir / "logs"
        # Workflow log contains a zero-valued frames line (legacy / wrong)
        log_path = _write_workflow_log(
            logs_dir,
            extra="2026-04-05 12:01:00,000 - INFO - Total frames extracted: 0\n",
        )
        _write_frame_extractor_log(logs_dir, "frame_extractor_20260405_233046.log",
                                   videos=10, frames=99)

        stats = parse_workflow_log(log_path)

        # The frame_extractor log is parsed after the workflow log, so its value wins
        assert stats["frames_extracted"] == 99, (
            "frame_extractor log should overwrite any stale value from workflow log."
        )
