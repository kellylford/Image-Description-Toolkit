"""
Unit tests for scripts/video_describer.py

Tests cover: class instantiation, default config, frame diff calculation,
save_descriptions output format, and CLI arg parsing.
These tests do NOT require a running AI provider or ffmpeg.
"""
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# Ensure scripts/ is importable regardless of working directory
_repo_root = Path(__file__).parents[2]
_scripts_dir = _repo_root / "scripts"
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))


# ---------------------------------------------------------------------------
# Import with graceful fallback for CV2 / other optional dependencies
# ---------------------------------------------------------------------------
try:
    from video_describer import VideoDescriber
    _import_ok = True
except ImportError as e:
    _import_ok = False
    _import_error = str(e)

skip_if_no_import = pytest.mark.skipif(
    not _import_ok,
    reason=f"video_describer could not be imported: {_import_error if not _import_ok else ''}",
)


# ---------------------------------------------------------------------------
# Instantiation
# ---------------------------------------------------------------------------
class TestVideoDescriberInit:
    @skip_if_no_import
    def test_instantiation_no_args(self):
        """VideoDescriber can be instantiated without any arguments."""
        vd = VideoDescriber()
        assert vd is not None

    @skip_if_no_import
    def test_instantiation_with_config(self):
        """VideoDescriber accepts a config dict and stores it."""
        cfg = {"provider": "openai", "model": "gpt-4o", "num_frames": 3}
        vd = VideoDescriber(config=cfg)
        assert vd.config["provider"] == "openai"
        assert vd.config["model"] == "gpt-4o"
        assert vd.config["num_frames"] == 3

    @skip_if_no_import
    def test_supported_formats_not_empty(self):
        """Supported video formats set is populated."""
        vd = VideoDescriber()
        assert len(vd.supported_formats) > 0
        # Check key formats are present
        assert ".mp4" in vd.supported_formats
        assert ".mov" in vd.supported_formats

    @skip_if_no_import
    def test_statistics_initialized(self):
        """Statistics dict is set up at init with correct keys."""
        vd = VideoDescriber()
        assert "total_videos" in vd.statistics
        assert "processed" in vd.statistics
        assert "failed" in vd.statistics
        assert vd.statistics["total_videos"] == 0
        assert vd.statistics["failed"] == 0


# ---------------------------------------------------------------------------
# Default config
# ---------------------------------------------------------------------------
class TestDefaultConfig:
    @skip_if_no_import
    def test_default_config_has_required_keys(self):
        """get_default_config() returns a dict with all expected keys."""
        vd = VideoDescriber()
        cfg = vd.get_default_config()
        required = [
            "frame_selection_mode",
            "num_frames",
            "time_interval_seconds",
            "scene_change_threshold",
            "provider",
            "model",
        ]
        for key in required:
            assert key in cfg, f"Missing key in default config: {key}"

    @skip_if_no_import
    def test_default_num_frames_reasonable(self):
        """Default num_frames should be between 1 and 30."""
        vd = VideoDescriber()
        assert 1 <= vd.config["num_frames"] <= 30

    @skip_if_no_import
    def test_default_provider_is_string(self):
        """Default provider must be a non-empty string."""
        vd = VideoDescriber()
        assert isinstance(vd.config["provider"], str)
        assert len(vd.config["provider"]) > 0


# ---------------------------------------------------------------------------
# Frame difference calculation
# ---------------------------------------------------------------------------
class TestFrameDiff:
    @skip_if_no_import
    def test_identical_frames_zero_diff(self):
        """Identical frames should have zero (or near-zero) difference."""
        vd = VideoDescriber()
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        diff = vd._calculate_frame_diff(frame, frame)
        assert diff == pytest.approx(0.0, abs=0.1)

    @skip_if_no_import
    def test_opposite_frames_high_diff(self):
        """Black vs white frames should produce maximum difference."""
        vd = VideoDescriber()
        black = np.zeros((240, 320, 3), dtype=np.uint8)
        white = np.full((240, 320, 3), 255, dtype=np.uint8)
        diff = vd._calculate_frame_diff(black, white)
        # Gray-scale diff of 0 vs 255 = 255 on every pixel
        assert diff > 200

    @skip_if_no_import
    def test_partial_change_mid_range(self):
        """Half-black, half-white frame diff should be mid-range."""
        vd = VideoDescriber()
        frame_a = np.zeros((240, 320, 3), dtype=np.uint8)
        frame_b = np.zeros((240, 320, 3), dtype=np.uint8)
        # Make left half of frame_b white
        frame_b[:, :160, :] = 255
        diff = vd._calculate_frame_diff(frame_a, frame_b)
        assert 60 < diff < 200

    @skip_if_no_import
    def test_diff_is_symmetric(self):
        """frame_diff(A, B) should equal frame_diff(B, A)."""
        vd = VideoDescriber()
        rng = np.random.default_rng(42)
        a = rng.integers(0, 256, (100, 100, 3), dtype=np.uint8)
        b = rng.integers(0, 256, (100, 100, 3), dtype=np.uint8)
        assert vd._calculate_frame_diff(a, b) == pytest.approx(
            vd._calculate_frame_diff(b, a), abs=0.01
        )


# ---------------------------------------------------------------------------
# save_descriptions — text format
# ---------------------------------------------------------------------------
class TestSaveDescriptions:
    @skip_if_no_import
    def test_save_text_format(self, tmp_path):
        """save_descriptions writes a readable text file."""
        vd = VideoDescriber()
        results = [
            {
                "video_name": "clip.mp4",
                "video_path": "/tmp/clip.mp4",
                "provider": "ollama",
                "model": "moondream",
                "num_frames_used": 3,
                "processing_time": 1.5,
                "description": "A short test video showing a cat.",
            }
        ]
        out = tmp_path / "out.txt"
        vd.save_descriptions(results, str(out))
        content = out.read_text(encoding="utf-8")
        assert "clip.mp4" in content
        assert "A short test video" in content
        assert "ollama" in content

    @skip_if_no_import
    def test_save_json_format(self, tmp_path):
        """save_descriptions writes valid JSON when .json extension used."""
        vd = VideoDescriber()
        results = [{"video_path": "/tmp/a.mp4", "description": "test"}]
        out = tmp_path / "out.json"
        vd.save_descriptions(results, str(out))
        data = json.loads(out.read_text(encoding="utf-8"))
        assert isinstance(data, list)
        assert data[0]["description"] == "test"

    @skip_if_no_import
    def test_save_error_result(self, tmp_path):
        """save_descriptions handles error results without crashing."""
        vd = VideoDescriber()
        results = [{"video_path": "/tmp/bad.mp4", "error": "File not found"}]
        out = tmp_path / "errors.txt"
        vd.save_descriptions(results, str(out))
        content = out.read_text(encoding="utf-8")
        assert "bad.mp4" in content
        assert "File not found" in content

    @skip_if_no_import
    def test_save_multiple_results(self, tmp_path):
        """save_descriptions handles multiple entries."""
        vd = VideoDescriber()
        results = [
            {
                "video_name": f"video{i}.mp4",
                "video_path": f"/tmp/video{i}.mp4",
                "provider": "ollama",
                "model": "llava",
                "num_frames_used": 2,
                "processing_time": 0.5,
                "description": f"Description {i}",
            }
            for i in range(3)
        ]
        out = tmp_path / "multi.txt"
        vd.save_descriptions(results, str(out))
        content = out.read_text(encoding="utf-8")
        assert "video0.mp4" in content
        assert "video2.mp4" in content


# ---------------------------------------------------------------------------
# extract_key_frames — with real test video (if available)
# ---------------------------------------------------------------------------
class TestExtractKeyFrames:
    @skip_if_no_import
    def test_extract_from_test_video(self):
        """extract_key_frames returns frames from the committed test video."""
        test_video = _repo_root / "testimages" / "test_video.mp4"
        if not test_video.exists():
            pytest.skip("testimages/test_video.mp4 not available")

        vd = VideoDescriber()
        vd.config["frame_selection_mode"] = "uniform"
        vd.config["num_frames"] = 3

        frames = vd.extract_key_frames(str(test_video))
        assert len(frames) >= 1
        # Each entry should be (ndarray, float)
        for frame, ts in frames:
            assert isinstance(frame, np.ndarray)
            assert isinstance(ts, float)
            assert ts >= 0.0

    @skip_if_no_import
    def test_extract_returns_numpy_arrays(self):
        """Each extracted frame is a valid 3-channel numpy array."""
        test_video = _repo_root / "testimages" / "test_video.mp4"
        if not test_video.exists():
            pytest.skip("testimages/test_video.mp4 not available")

        vd = VideoDescriber()
        vd.config["frame_selection_mode"] = "key_frames"
        vd.config["num_frames"] = 5

        frames = vd.extract_key_frames(str(test_video))
        for frame, _ in frames:
            assert frame.ndim == 3
            assert frame.shape[2] == 3  # BGR channels

    @skip_if_no_import
    def test_extract_nonexistent_video_raises(self):
        """extract_key_frames raises on a path that doesn't exist."""
        vd = VideoDescriber()
        with pytest.raises(Exception):
            vd.extract_key_frames("/nonexistent/path/video.mp4")


# ---------------------------------------------------------------------------
# CLI main() — argument parsing via subprocess (no API calls)
# ---------------------------------------------------------------------------
class TestMainCLI:
    @skip_if_no_import
    def test_main_help_exits_zero(self):
        """python video_describer.py --help exits 0 and prints usage."""
        import subprocess
        result = subprocess.run(
            [sys.executable, str(_scripts_dir / "video_describer.py"), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "usage" in result.stdout.lower() or "video" in result.stdout.lower()

    @skip_if_no_import
    def test_main_missing_video_exits_nonzero(self):
        """python video_describer.py with nonexistent video should fail."""
        import subprocess
        result = subprocess.run(
            [
                sys.executable,
                str(_scripts_dir / "video_describer.py"),
                "/nonexistent/video.mp4",
                "--provider",
                "ollama",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        # Should exit non-zero (either argparse error or file-not-found)
        assert result.returncode != 0
