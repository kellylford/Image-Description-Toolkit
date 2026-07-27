"""
gallery_exporter — HTML gallery export.

Covers the progress callback the GUI uses to drive its "Exporting gallery"
stage. The per-image copy loop dominates export time, so a miscount would
leave the progress bar stuck short of the end.
"""
import sys
from pathlib import Path

import pytest

from idt_core import gallery_exporter

# The GUI data model lives in imagedescriber/
_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "imagedescriber"))


def _make_jpeg(path: Path, color=(90, 140, 210)):
    from PIL import Image
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (16, 16), color).save(path, "JPEG")


@pytest.fixture
def described_items(tmp_path):
    """Three images, each carrying one description."""
    from data_models import ImageItem, ImageDescription

    src = tmp_path / "Photos"
    items = {}
    for n in range(3):
        p = src / f"img{n}.jpg"
        _make_jpeg(p)
        item = ImageItem(str(p))
        item.add_description(ImageDescription(
            text=f"Description {n}.", model="gpt-4o",
            prompt_style="detailed", provider="openai",
        ))
        items[str(p)] = item
    return items


def test_progress_callback_fires_per_image(described_items, tmp_path):
    calls = []
    result = gallery_exporter.export_gallery(
        described_items,
        {"output_dir": str(tmp_path / "out"), "title": "T"},
        progress=lambda done, total, name: calls.append((done, total, name)),
    )

    assert result["images_copied"] == 3
    assert [c[0] for c in calls] == [1, 2, 3]
    assert {c[1] for c in calls} == {3}
    assert calls[-1][0] == calls[-1][1]      # ends on an exact count
    assert all(c[2].endswith(".jpg") for c in calls)


def test_progress_callback_is_optional(described_items, tmp_path):
    """Omitting progress leaves behaviour unchanged."""
    result = gallery_exporter.export_gallery(
        described_items, {"output_dir": str(tmp_path / "out2"), "title": "T"}
    )
    assert result["images_copied"] == 3
    assert Path(result["output_file"]).exists()


def test_progress_counts_missing_sources_too(described_items, tmp_path):
    """A skipped (missing) file still advances the counter.

    Otherwise the bar would stall short of the total whenever a source file
    had been moved or deleted.
    """
    missing = next(iter(described_items))
    Path(missing).unlink()

    calls = []
    result = gallery_exporter.export_gallery(
        described_items,
        {"output_dir": str(tmp_path / "out3"), "title": "T"},
        progress=lambda done, total, name: calls.append(done),
    )

    assert result["images_skipped"] == 1
    assert result["images_copied"] == 2
    assert calls == [1, 2, 3]                # counter reached the total anyway
