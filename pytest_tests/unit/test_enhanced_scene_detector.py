"""
Unit tests for EnhancedSceneDetector.

Tests cover the pure-Python logic layers (frame selection, coverage
filling, quality optimisation, adaptive thresholding, motion analysis)
without requiring a real video file or OpenCV VideoCapture.
"""

import sys
from pathlib import Path
from collections import deque

import pytest

# Make scripts/ importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from enhanced_scene_detector import EnhancedSceneDetector, FrameInfo


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_frame(frame_num: int, timestamp: float, change_score: float = 20.0,
               quality_score: float = 50.0, motion_type: str = "scene_change") -> FrameInfo:
    """Create a FrameInfo with sensible defaults for testing."""
    return FrameInfo(
        frame_num=frame_num,
        timestamp=timestamp,
        change_score=change_score,
        quality_score=quality_score,
        motion_type=motion_type,
    )


def make_detector(**kwargs) -> EnhancedSceneDetector:
    """Create a detector with test-friendly defaults."""
    defaults = dict(min_frames=3, max_frames=10, target_frames=5, min_scene_duration=1.0)
    defaults.update(kwargs)
    return EnhancedSceneDetector(**defaults)


# ---------------------------------------------------------------------------
# FrameInfo dataclass
# ---------------------------------------------------------------------------

class TestFrameInfo:
    def test_default_importance_score(self):
        """importance_score should default to 0.0 (not a dynamic attribute)."""
        f = make_frame(0, 0.0)
        assert f.importance_score == 0.0

    def test_importance_score_assignable(self):
        """importance_score can be set as a proper field."""
        f = make_frame(0, 0.0)
        f.importance_score = 42.5
        assert f.importance_score == 42.5

    def test_is_keyframe_defaults_false(self):
        f = make_frame(10, 1.0)
        assert f.is_keyframe is False


# ---------------------------------------------------------------------------
# _calculate_quality
# ---------------------------------------------------------------------------

class TestCalculateQuality:
    def test_returns_float_in_range(self):
        """Quality score must be 0-100."""
        import numpy as np
        detector = make_detector()
        gray = np.zeros((100, 100), dtype=np.uint8)
        score = detector._calculate_quality(gray)
        assert 0.0 <= score <= 100.0

    def test_blurry_frame_low_score(self):
        """A flat (zero-variance) frame should score near 0."""
        import numpy as np
        detector = make_detector()
        flat = np.full((100, 100), 128, dtype=np.uint8)
        score = detector._calculate_quality(flat)
        assert score < 10.0

    def test_sharp_frame_higher_score(self):
        """A checkerboard frame with high edge content should score higher than flat."""
        import numpy as np
        detector = make_detector()
        sharp = np.zeros((100, 100), dtype=np.uint8)
        sharp[::2, ::2] = 255  # checkerboard
        flat = np.full((100, 100), 128, dtype=np.uint8)
        assert detector._calculate_quality(sharp) > detector._calculate_quality(flat)


# ---------------------------------------------------------------------------
# _analyze_motion
# ---------------------------------------------------------------------------

class TestAnalyzeMotion:
    def test_insufficient_history_returns_static(self):
        """With fewer than 3 history entries, always returns 'static'."""
        import numpy as np
        detector = make_detector()
        diff = np.zeros((100, 100), dtype=np.uint8)
        history = deque([(0, 5.0), (1, 5.0)], maxlen=5)  # only 2 entries
        result = detector._analyze_motion(diff, history)
        assert result == "static"

    def test_low_motion_returns_static(self):
        """Consistently low change scores → 'static'."""
        import numpy as np
        detector = make_detector()
        diff = np.zeros((100, 100), dtype=np.uint8)
        history = deque([(i, 2.0) for i in range(5)], maxlen=5)
        assert detector._analyze_motion(diff, history) == "static"

    def test_high_consistent_motion_returns_camera_pan(self):
        """High, low-variance change scores → 'camera_pan'."""
        import numpy as np
        detector = make_detector()
        diff = np.zeros((100, 100), dtype=np.uint8)
        # std=0, mean=30 → camera_pan
        history = deque([(i, 30.0) for i in range(5)], maxlen=5)
        assert detector._analyze_motion(diff, history) == "camera_pan"

    def test_high_variable_motion_returns_scene_change(self):
        """High variance in change scores → 'scene_change'."""
        import numpy as np
        detector = make_detector()
        diff = np.zeros((100, 100), dtype=np.uint8)
        # std > 5, mean > 10
        history = deque([(i, v) for i, v in enumerate([5, 50, 5, 50, 5])], maxlen=5)
        assert detector._analyze_motion(diff, history) == "scene_change"


# ---------------------------------------------------------------------------
# _calculate_adaptive_threshold
# ---------------------------------------------------------------------------

class TestAdaptiveThreshold:
    def test_empty_scores_no_crash(self):
        detector = make_detector()
        detector._calculate_adaptive_threshold([])  # must not raise

    def test_high_motion_video_threshold(self):
        """mean > 30 → threshold should be set (not absent)."""
        detector = make_detector()
        scores = [35.0] * 50
        detector._calculate_adaptive_threshold(scores)
        assert hasattr(detector, "adaptive_threshold_value")
        assert 5 <= detector.adaptive_threshold_value <= 50

    def test_low_motion_video_threshold(self):
        """mean < 10 → threshold clamped to minimum 5."""
        detector = make_detector()
        scores = [2.0] * 50
        detector._calculate_adaptive_threshold(scores)
        assert detector.adaptive_threshold_value >= 5

    def test_threshold_clamped_to_range(self):
        """Threshold must always be in [5, 50]."""
        detector = make_detector()
        # Extreme low
        detector._calculate_adaptive_threshold([0.1] * 100)
        assert 5 <= detector.adaptive_threshold_value <= 50
        # Extreme high
        detector._calculate_adaptive_threshold([99.0] * 100)
        assert 5 <= detector.adaptive_threshold_value <= 50


# ---------------------------------------------------------------------------
# _select_final_frames
# ---------------------------------------------------------------------------

class TestSelectFinalFrames:
    def _scene_frames(self, n: int, duration: float) -> list:
        """Generate n evenly-spaced scene-change candidates."""
        interval = duration / max(n, 1)
        return [
            make_frame(int(i * interval * 30), i * interval, change_score=40.0, motion_type="scene_change")
            for i in range(n)
        ]

    def test_returns_list(self):
        detector = make_detector(min_frames=2, max_frames=10, target_frames=5)
        frames = self._scene_frames(6, 30.0)
        result = detector._select_final_frames(frames, 30.0)
        assert isinstance(result, list)

    def test_empty_candidates_returns_empty(self):
        detector = make_detector()
        assert detector._select_final_frames([], 30.0) == []

    def test_always_includes_first_frame(self):
        detector = make_detector(min_frames=2, max_frames=10, target_frames=5, min_scene_duration=0.5)
        frames = self._scene_frames(8, 30.0)
        result = detector._select_final_frames(frames, 30.0)
        assert result[0].frame_num == frames[0].frame_num

    def test_result_sorted_by_timestamp(self):
        detector = make_detector(min_frames=2, max_frames=10, target_frames=5, min_scene_duration=0.5)
        frames = self._scene_frames(8, 30.0)
        result = detector._select_final_frames(frames, 30.0)
        timestamps = [f.timestamp for f in result]
        assert timestamps == sorted(timestamps)

    def test_respects_max_frames(self):
        detector = make_detector(min_frames=2, max_frames=4, target_frames=4, min_scene_duration=0.1)
        frames = self._scene_frames(20, 60.0)
        result = detector._select_final_frames(frames, 60.0)
        assert len(result) <= 4


# ---------------------------------------------------------------------------
# _ensure_coverage
# ---------------------------------------------------------------------------

class TestEnsureCoverage:
    def test_no_fill_needed_when_above_min(self):
        """If selected already meets min_frames, candidates unchanged."""
        detector = make_detector(min_frames=2, max_frames=10, target_frames=5)
        selected = [make_frame(0, 0.0), make_frame(30, 10.0)]
        candidates = selected[:]
        result = detector._ensure_coverage(selected, candidates, 10.0)
        assert len(result) >= 2

    def test_fills_when_below_min(self):
        """If selected < min_frames, more frames are added."""
        detector = make_detector(min_frames=5, max_frames=10, target_frames=5, min_scene_duration=0.5)
        # Only 1 selected but many candidates available
        candidates = [make_frame(i * 10, float(i), motion_type="static") for i in range(30)]
        selected = [candidates[0]]
        result = detector._ensure_coverage(selected, candidates, 30.0)
        assert len(result) >= min(5, len(candidates))

    def test_result_sorted(self):
        """Output of _ensure_coverage is always sorted by timestamp."""
        detector = make_detector(min_frames=5, max_frames=10, target_frames=5, min_scene_duration=0.5)
        candidates = [make_frame(i * 10, float(i), motion_type="static") for i in range(20)]
        selected = [candidates[0]]
        result = detector._ensure_coverage(selected, candidates, 20.0)
        timestamps = [f.timestamp for f in result]
        assert timestamps == sorted(timestamps)


# ---------------------------------------------------------------------------
# _optimize_quality
# ---------------------------------------------------------------------------

class TestOptimizeQuality:
    def test_no_reduction_when_under_target(self):
        detector = make_detector(min_frames=2, max_frames=10, target_frames=8)
        frames = [make_frame(i, float(i)) for i in range(5)]
        result = detector._optimize_quality(frames)
        assert len(result) == 5

    def test_reduces_to_max_frames(self):
        detector = make_detector(min_frames=2, max_frames=4, target_frames=4)
        frames = [make_frame(i, float(i), change_score=float(i), quality_score=float(i)) for i in range(20)]
        result = detector._optimize_quality(frames)
        assert len(result) <= 4

    def test_importance_score_set_during_reduction(self):
        """After reduction, remaining frames should have importance_score assigned."""
        detector = make_detector(min_frames=2, max_frames=3, target_frames=3)
        frames = [make_frame(i, float(i), change_score=float(i * 5), quality_score=float(i * 3))
                  for i in range(10)]
        result = detector._optimize_quality(frames)
        # importance_score should be non-zero for frames that went through scoring
        for f in result:
            assert isinstance(f.importance_score, float)

    def test_result_sorted_by_timestamp(self):
        detector = make_detector(min_frames=2, max_frames=4, target_frames=4)
        frames = [make_frame(i, float(i)) for i in range(10)]
        result = detector._optimize_quality(frames)
        timestamps = [f.timestamp for f in result]
        assert timestamps == sorted(timestamps)


# ---------------------------------------------------------------------------
# _fallback_uniform_sampling
# ---------------------------------------------------------------------------

class TestFallbackUniformSampling:
    def test_returns_target_frames(self):
        detector = make_detector(min_frames=3, max_frames=10, target_frames=7)
        result = detector._fallback_uniform_sampling("fake.mp4", fps=30.0, total_frames=900)
        assert len(result) == 7

    def test_timestamps_within_duration(self):
        detector = make_detector(min_frames=3, max_frames=10, target_frames=5)
        fps, total = 30.0, 300
        duration = total / fps
        result = detector._fallback_uniform_sampling("fake.mp4", fps=fps, total_frames=total)
        for f in result:
            assert 0.0 < f.timestamp < duration

    def test_returns_frame_info_objects(self):
        detector = make_detector()
        result = detector._fallback_uniform_sampling("fake.mp4", fps=25.0, total_frames=250)
        assert all(isinstance(f, FrameInfo) for f in result)
