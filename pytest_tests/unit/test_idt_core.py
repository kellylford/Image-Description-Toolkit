"""
Unit tests for idt_core — no AI API calls, no network, no disk side effects
beyond tmp_path (pytest fixture that auto-cleans up).
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def _make_tiny_jpeg() -> bytes:
    """Return a minimal valid JPEG (1x1 white pixel, no EXIF)."""
    # SOI + APP0 JFIF + quantization + huffman + SOF + SOS + EOI
    # This is the smallest valid JPEG that piexif and Pillow can process.
    return bytes([
        0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00,
        0x01, 0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB,
        0x00, 0x43, 0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07,
        0x07, 0x07, 0x09, 0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B,
        0x0B, 0x0C, 0x19, 0x12, 0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E,
        0x1D, 0x1A, 0x1C, 0x1C, 0x20, 0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C,
        0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29, 0x2C, 0x30, 0x31, 0x34, 0x34,
        0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32, 0x3C, 0x2E, 0x33, 0x34,
        0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01, 0x00, 0x01, 0x01,
        0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x1F, 0x00, 0x00, 0x01, 0x05,
        0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
        0x09, 0x0A, 0x0B, 0xFF, 0xC4, 0x00, 0xB5, 0x10, 0x00, 0x02, 0x01,
        0x03, 0x03, 0x02, 0x04, 0x03, 0x05, 0x05, 0x04, 0x04, 0x00, 0x00,
        0x01, 0x7D, 0x01, 0x02, 0x03, 0x00, 0x04, 0x11, 0x05, 0x12, 0x21,
        0x31, 0x41, 0x06, 0x13, 0x51, 0x61, 0x07, 0x22, 0x71, 0x14, 0x32,
        0x81, 0x91, 0xA1, 0x08, 0x23, 0x42, 0xB1, 0xC1, 0x15, 0x52, 0xD1,
        0xF0, 0x24, 0x33, 0x62, 0x72, 0x82, 0x09, 0x0A, 0x16, 0x17, 0x18,
        0x19, 0x1A, 0x25, 0x26, 0x27, 0x28, 0x29, 0x2A, 0x34, 0x35, 0x36,
        0x37, 0x38, 0x39, 0x3A, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48, 0x49,
        0x4A, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59, 0x5A, 0x63, 0x64,
        0x65, 0x66, 0x67, 0x68, 0x69, 0x6A, 0x73, 0x74, 0x75, 0x76, 0x77,
        0x78, 0x79, 0x7A, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89, 0x8A,
        0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98, 0x99, 0x9A, 0xA2, 0xA3,
        0xA4, 0xA5, 0xA6, 0xA7, 0xA8, 0xA9, 0xAA, 0xB2, 0xB3, 0xB4, 0xB5,
        0xB6, 0xB7, 0xB8, 0xB9, 0xBA, 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7,
        0xC8, 0xC9, 0xCA, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9,
        0xDA, 0xE1, 0xE2, 0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9, 0xEA,
        0xF1, 0xF2, 0xF3, 0xF4, 0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0xFA, 0xFF,
        0xDA, 0x00, 0x08, 0x01, 0x01, 0x00, 0x00, 0x3F, 0x00, 0xFB, 0xD2,
        0x8A, 0x28, 0x03, 0xFF, 0xD9,
    ])


def _make_source_tree(tmp_path: Path) -> tuple[Path, list[Path]]:
    """Create a fake source directory with a few JPEG images."""
    src = tmp_path / "Photos"
    (src / "Day1").mkdir(parents=True)
    (src / "Day2").mkdir(parents=True)

    images = [
        src / "Day1" / "morning.jpg",
        src / "Day1" / "afternoon.jpg",
        src / "Day2" / "sunset.jpg",
    ]
    for img in images:
        img.write_bytes(_make_tiny_jpeg())

    return src, images


# ------------------------------------------------------------------ #
# Scanner tests                                                        #
# ------------------------------------------------------------------ #

class TestScanner:
    def test_finds_images(self, tmp_path):
        from idt_core.scanner import scan_images
        src, images = _make_source_tree(tmp_path)
        found = list(scan_images(src))
        assert len(found) == 3
        assert all(p.suffix.lower() == ".jpg" for p in found)

    def test_skips_idt_dir(self, tmp_path):
        from idt_core.scanner import scan_images
        src, _ = _make_source_tree(tmp_path)
        idt = tmp_path / "Photos.idt"
        (idt / "Day1").mkdir(parents=True)
        (idt / "Day1" / "decoy.jpg").write_bytes(_make_tiny_jpeg())

        found = list(scan_images(src))
        assert all(".idt" not in str(p) for p in found)

    def test_skips_hidden_dirs(self, tmp_path):
        from idt_core.scanner import scan_images
        src, _ = _make_source_tree(tmp_path)
        (src / ".Trash").mkdir()
        (src / ".Trash" / "hidden.jpg").write_bytes(_make_tiny_jpeg())
        found = list(scan_images(src))
        assert all(".Trash" not in str(p) for p in found)

    def test_sorted_output(self, tmp_path):
        from idt_core.scanner import scan_images
        src, images = _make_source_tree(tmp_path)
        found = list(scan_images(src))
        assert found == sorted(found)


# ------------------------------------------------------------------ #
# Project tests                                                        #
# ------------------------------------------------------------------ #

class TestProject:
    def test_open_creates_idt_dir(self, tmp_path):
        from idt_core.project import Project
        src, _ = _make_source_tree(tmp_path)
        project = Project.open(src)
        assert project.idt_dir.exists()
        assert (project.idt_dir / "project.json").exists()

    def test_idt_dir_is_sibling_not_child(self, tmp_path):
        from idt_core.project import Project
        src, _ = _make_source_tree(tmp_path)
        project = Project.open(src)
        assert project.idt_dir.parent == src.parent
        assert project.idt_dir.name == "Photos.idt"

    def test_project_json_content(self, tmp_path):
        from idt_core.project import Project
        src, _ = _make_source_tree(tmp_path)
        project = Project.open(src)
        data = json.loads((project.idt_dir / "project.json").read_text())
        assert data["version"] == "1.0"
        assert Path(data["source"]) == src

    def test_reopen_loads_existing(self, tmp_path):
        from idt_core.project import Project
        src, _ = _make_source_tree(tmp_path)
        p1 = Project.open(src)
        p1.config.default_model = "my-test-model"
        p1.save()

        p2 = Project.open(src)
        assert p2.config.default_model == "my-test-model"

    def test_sidecar_path(self, tmp_path):
        from idt_core.project import Project
        src, images = _make_source_tree(tmp_path)
        project = Project.open(src)
        sidecar = project.sidecar_path(images[0])
        assert sidecar.parent.name == "Day1"
        assert sidecar.name == "morning.jpg.json"
        assert str(project.idt_dir) in str(sidecar)

    def test_status_all_undescribed(self, tmp_path):
        from idt_core.project import Project
        src, _ = _make_source_tree(tmp_path)
        project = Project.open(src)
        st = project.status()
        assert st["total"] == 3
        assert st["described"] == 0
        assert st["undescribed"] == 3

    def test_not_a_directory_raises(self, tmp_path):
        from idt_core.project import Project
        fake = tmp_path / "nonexistent"
        with pytest.raises(NotADirectoryError):
            Project.open(fake)


# ------------------------------------------------------------------ #
# ImageItem tests                                                      #
# ------------------------------------------------------------------ #

class TestImageItem:
    def test_round_trip(self, tmp_path):
        from idt_core.image_item import ImageItem, Description

        src = tmp_path / "photo.jpg"
        src.write_bytes(_make_tiny_jpeg())
        sidecar = tmp_path / "photo.jpg.json"

        item = ImageItem(source_path=src, sidecar_path=sidecar)
        desc = Description.create(
            text="A sunny beach scene.",
            model="claude-opus-4-6",
            provider="anthropic",
            prompt_name="detailed",
            prompt_text="Describe this image.",
        )
        item.add_description(desc)
        item.save()

        loaded = ImageItem.load(sidecar)
        assert loaded.described
        assert loaded.active_description.text == "A sunny beach scene."
        assert loaded.active_description.model == "claude-opus-4-6"

    def test_active_description_is_latest(self, tmp_path):
        from idt_core.image_item import ImageItem, Description

        src = tmp_path / "photo.jpg"
        src.write_bytes(_make_tiny_jpeg())
        sidecar = tmp_path / "photo.jpg.json"
        item = ImageItem(source_path=src, sidecar_path=sidecar)

        d1 = Description.create("First description.", "m1", "p1", "brief", "")
        d2 = Description.create("Second description.", "m2", "p2", "detailed", "")
        item.add_description(d1)
        item.add_description(d2)
        item.save()

        loaded = ImageItem.load(sidecar)
        assert loaded.active_description.text == "Second description."
        assert len(loaded.descriptions) == 2

    def test_new_description_clears_embedded_at(self, tmp_path):
        from idt_core.image_item import ImageItem, Description

        src = tmp_path / "photo.jpg"
        src.write_bytes(_make_tiny_jpeg())
        sidecar = tmp_path / "photo.jpg.json"
        item = ImageItem(source_path=src, sidecar_path=sidecar)
        item.embedded_at = "2026-06-19T00:00:00Z"

        desc = Description.create("New description.", "m1", "p1", "detailed", "")
        item.add_description(desc)
        assert item.embedded_at is None

    def test_processable_path_uses_converted_when_set(self, tmp_path):
        from idt_core.image_item import ImageItem

        src = tmp_path / "photo.heic"
        src.write_bytes(b"fake heic")
        converted = tmp_path / "photo.jpg"
        converted.write_bytes(_make_tiny_jpeg())
        sidecar = tmp_path / "photo.heic.json"

        item = ImageItem(source_path=src, sidecar_path=sidecar, converted_path=converted)
        assert item.processable_path == converted


# ------------------------------------------------------------------ #
# Config tests                                                         #
# ------------------------------------------------------------------ #

class TestConfig:
    def test_built_in_prompts_exist(self):
        from idt_core.config import BUILT_IN_PROMPTS
        for name in ("detailed", "brief", "technical", "social", "document", "news"):
            assert name in BUILT_IN_PROMPTS
            assert len(BUILT_IN_PROMPTS[name]) > 20

    def test_get_prompt_text_returns_builtin(self):
        from idt_core.config import UserConfig
        cfg = UserConfig()
        text = cfg.get_prompt_text("detailed")
        assert text is not None
        assert "cannot see" in text.lower()

    def test_custom_prompt_overrides_builtin(self):
        from idt_core.config import UserConfig
        cfg = UserConfig()
        cfg.custom_prompts["detailed"] = "My custom detailed prompt."
        assert cfg.get_prompt_text("detailed") == "My custom detailed prompt."

    def test_unknown_prompt_returns_none(self):
        from idt_core.config import UserConfig
        cfg = UserConfig()
        assert cfg.get_prompt_text("does_not_exist") is None


# ------------------------------------------------------------------ #
# Pipeline tests (mock provider)                                       #
# ------------------------------------------------------------------ #

class MockProvider:
    provider_name = "mock"
    model_name = "mock-model"

    def describe(self, image_bytes, mime_type, prompt):
        from idt_core.providers.base import DescriptionResult
        return DescriptionResult(
            text=f"Mock description for {len(image_bytes)} byte image.",
            model="mock-model",
            provider="mock",
            input_tokens=10,
            output_tokens=8,
        )


class TestPipeline:
    def test_describes_all_images(self, tmp_path):
        from idt_core.project import Project
        from idt_core.pipeline import Pipeline, RunOptions

        src, images = _make_source_tree(tmp_path)
        project = Project.open(src)
        pipeline = Pipeline(project, MockProvider())
        options = RunOptions(prompt_name="brief", prompt_text="Describe this.")

        events = list(pipeline.run(options))
        assert len(events) == 3
        assert all(e.success for e in events)

    def test_skips_already_described(self, tmp_path):
        from idt_core.project import Project
        from idt_core.pipeline import Pipeline, RunOptions
        from idt_core.image_item import ImageItem, Description

        src, images = _make_source_tree(tmp_path)
        project = Project.open(src)

        # Pre-describe one image
        sidecar = project.sidecar_path(images[0])
        item = ImageItem(source_path=images[0], sidecar_path=sidecar)
        item.add_description(Description.create("Pre-existing.", "m", "p", "n", "t"))
        item.save()

        pipeline = Pipeline(project, MockProvider())
        events = list(pipeline.run(RunOptions(prompt_text="x")))
        assert len(events) == 2

    def test_redescribe_processes_all(self, tmp_path):
        from idt_core.project import Project
        from idt_core.pipeline import Pipeline, RunOptions
        from idt_core.image_item import ImageItem, Description

        src, images = _make_source_tree(tmp_path)
        project = Project.open(src)

        # Pre-describe all
        for img in images:
            sidecar = project.sidecar_path(img)
            item = ImageItem(source_path=img, sidecar_path=sidecar)
            item.add_description(Description.create("Old.", "m", "p", "n", "t"))
            item.save()

        pipeline = Pipeline(project, MockProvider())
        events = list(pipeline.run(RunOptions(prompt_text="x", redescribe=True)))
        assert len(events) == 3

    def test_limit_option(self, tmp_path):
        from idt_core.project import Project
        from idt_core.pipeline import Pipeline, RunOptions

        src, _ = _make_source_tree(tmp_path)
        project = Project.open(src)
        pipeline = Pipeline(project, MockProvider())
        events = list(pipeline.run(RunOptions(prompt_text="x", limit=1)))
        assert len(events) == 1

    def test_description_saved_to_sidecar(self, tmp_path):
        from idt_core.project import Project
        from idt_core.pipeline import Pipeline, RunOptions
        from idt_core.image_item import ImageItem

        src, _ = _make_source_tree(tmp_path)
        project = Project.open(src)
        # Get the first event to know which image was processed first
        event = next(Pipeline(project, MockProvider()).run(RunOptions(prompt_text="Describe.")))
        assert event.success

        # Reload from disk and verify the sidecar was written
        item = ImageItem.load(event.item.sidecar_path)
        assert item.described
        assert "Mock description" in item.active_description.text

    def test_error_event_on_provider_failure(self, tmp_path):
        from idt_core.project import Project
        from idt_core.pipeline import Pipeline, RunOptions

        class FailingProvider:
            provider_name = "mock"
            model_name = "mock"
            def describe(self, *a, **kw):
                raise RuntimeError("API unavailable")

        src, _ = _make_source_tree(tmp_path)
        project = Project.open(src)
        events = list(Pipeline(project, FailingProvider()).run(RunOptions(prompt_text="x")))
        assert all(not e.success for e in events)
        assert all("API unavailable" in e.error for e in events)


# ------------------------------------------------------------------ #
# Exporter tests                                                       #
# ------------------------------------------------------------------ #

class TestExporter:
    def _setup_described_project(self, tmp_path):
        from idt_core.project import Project
        from idt_core.pipeline import Pipeline, RunOptions

        src, _ = _make_source_tree(tmp_path)
        project = Project.open(src)
        list(Pipeline(project, MockProvider()).run(RunOptions(prompt_text="Describe.")))
        return project

    def test_html_export_creates_file(self, tmp_path):
        from idt_core.exporter import export_html
        project = self._setup_described_project(tmp_path)
        out = export_html(project)
        assert out.exists()
        assert out.suffix == ".html"

    def test_html_has_skip_nav(self, tmp_path):
        from idt_core.exporter import export_html
        project = self._setup_described_project(tmp_path)
        content = export_html(project).read_text(encoding="utf-8")
        assert "skip-link" in content
        assert "Skip to image descriptions" in content

    def test_html_has_landmark_regions(self, tmp_path):
        from idt_core.exporter import export_html
        project = self._setup_described_project(tmp_path)
        content = export_html(project).read_text(encoding="utf-8")
        assert "<main" in content
        assert "<nav" in content
        assert "<header" in content

    def test_html_description_in_alt_and_figcaption(self, tmp_path):
        from idt_core.exporter import export_html
        project = self._setup_described_project(tmp_path)
        content = export_html(project).read_text(encoding="utf-8")
        assert "Mock description" in content
        assert 'alt="Mock description' in content

    def test_csv_export_creates_file(self, tmp_path):
        from idt_core.exporter import export_csv
        project = self._setup_described_project(tmp_path)
        out = export_csv(project)
        assert out.exists()

    def test_csv_has_header_and_rows(self, tmp_path):
        import csv as _csv
        from idt_core.exporter import export_csv
        project = self._setup_described_project(tmp_path)
        out = export_csv(project)
        rows = list(_csv.DictReader(out.open(encoding="utf-8")))
        assert len(rows) == 3
        assert all(r["description"].startswith("Mock description") for r in rows)
        assert all(r["model"] == "mock-model" for r in rows)

    def test_txt_export_creates_file(self, tmp_path):
        from idt_core.exporter import export_txt
        project = self._setup_described_project(tmp_path)
        out = export_txt(project)
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "morning.jpg" in content
        assert "Mock description" in content

    def test_export_raises_on_empty_project(self, tmp_path):
        from idt_core.project import Project
        from idt_core.exporter import export_html
        src, _ = _make_source_tree(tmp_path)
        project = Project.open(src)
        with pytest.raises(ValueError, match="No described"):
            export_html(project)


# ------------------------------------------------------------------ #
# Embedder tests                                                       #
# ------------------------------------------------------------------ #

class TestEmbedder:
    def _setup_described_project(self, tmp_path):
        from idt_core.project import Project
        from idt_core.pipeline import Pipeline, RunOptions

        src, _ = _make_source_tree(tmp_path)
        project = Project.open(src)
        list(Pipeline(project, MockProvider()).run(RunOptions(prompt_text="Describe.")))
        return project

    def test_dry_run_creates_no_files(self, tmp_path):
        from idt_core.embedder import Embedder
        project = self._setup_described_project(tmp_path)
        result = Embedder(project).embed_all(dry_run=True)
        assert len(result.embedded) == 3
        embedded_dir = project.idt_dir / "embedded"
        assert not embedded_dir.exists()

    def test_embed_creates_copies(self, tmp_path):
        from idt_core.embedder import Embedder
        project = self._setup_described_project(tmp_path)
        result = Embedder(project).embed_all()
        assert len(result.embedded) == 3
        assert all(p.exists() for p in result.embedded)
        # Copies are inside .idt/embedded/, not the source
        for p in result.embedded:
            assert str(project.idt_dir) in str(p)

    def test_originals_not_modified(self, tmp_path):
        from idt_core.embedder import Embedder
        project = self._setup_described_project(tmp_path)
        # Record original mtimes
        originals = list(project.source_dir.rglob("*.jpg"))
        mtimes_before = {p: p.stat().st_mtime for p in originals}
        Embedder(project).embed_all()
        for p, mtime in mtimes_before.items():
            assert p.stat().st_mtime == mtime, f"{p.name} was modified"

    def test_mirrors_source_structure(self, tmp_path):
        from idt_core.embedder import Embedder
        project = self._setup_described_project(tmp_path)
        result = Embedder(project).embed_all()
        embedded_paths = {p.relative_to(project.idt_dir / "embedded") for p in result.embedded}
        source_paths = {
            img.relative_to(project.source_dir)
            for img in project.source_dir.rglob("*.jpg")
        }
        assert embedded_paths == source_paths

    def test_embed_sets_embedded_at(self, tmp_path):
        from idt_core.embedder import Embedder
        from idt_core.image_item import ImageItem
        project = self._setup_described_project(tmp_path)
        Embedder(project).embed_all()
        for item in project.described():
            assert item.embedded_at is not None

    def test_skip_already_embedded(self, tmp_path):
        from idt_core.embedder import Embedder
        project = self._setup_described_project(tmp_path)
        e = Embedder(project)
        e.embed_all()  # first run
        result2 = e.embed_all()  # second run — should skip all
        assert len(result2.embedded) == 0
        assert len(result2.skipped) == 3

    def test_force_re_embeds(self, tmp_path):
        from idt_core.embedder import Embedder
        project = self._setup_described_project(tmp_path)
        e = Embedder(project)
        e.embed_all()
        result2 = e.embed_all(force=True)
        assert len(result2.embedded) == 3


# ------------------------------------------------------------------ #
# XMP injection tests                                                  #
# ------------------------------------------------------------------ #

class TestXmpInjection:
    def test_build_minimal_xmp_contains_description(self):
        from idt_core.embedder import _build_minimal_xmp
        xmp = _build_minimal_xmp("A sunny beach.")
        assert "A sunny beach." in xmp
        assert "dc:description" in xmp
        assert "x-default" in xmp

    def test_build_minimal_xmp_escapes_html_chars(self):
        from idt_core.embedder import _build_minimal_xmp
        xmp = _build_minimal_xmp('Image of <Tom> & "Jerry"')
        assert "<Tom>" not in xmp
        assert "&amp;" in xmp or "&lt;" in xmp

    def test_inject_xmp_into_jpeg_roundtrip(self):
        from idt_core.embedder import _inject_xmp_into_jpeg, _extract_xmp_from_jpeg, _build_minimal_xmp
        jpeg = _make_tiny_jpeg()
        xmp_str = _build_minimal_xmp("Test description for roundtrip.")
        modified = _inject_xmp_into_jpeg(jpeg, xmp_str)
        assert modified[:2] == b"\xff\xd8"  # still a valid JPEG SOI
        extracted = _extract_xmp_from_jpeg(modified)
        assert extracted is not None
        assert b"Test description for roundtrip." in extracted

    def test_inject_replaces_existing_xmp(self):
        from idt_core.embedder import _inject_xmp_into_jpeg, _extract_xmp_from_jpeg, _build_minimal_xmp
        jpeg = _make_tiny_jpeg()
        first = _inject_xmp_into_jpeg(jpeg, _build_minimal_xmp("First."))
        second = _inject_xmp_into_jpeg(first, _build_minimal_xmp("Second."))
        extracted = _extract_xmp_from_jpeg(second)
        assert b"Second." in extracted
        assert b"First." not in extracted

    def test_update_xmp_description_on_existing_xmp(self):
        from idt_core.embedder import _update_xmp_description, _build_minimal_xmp
        original_xmp = _build_minimal_xmp("Original description.")
        updated = _update_xmp_description(original_xmp.encode("utf-8"), "Updated description.")
        assert "Updated description." in updated
        assert "Original description." not in updated

    def test_update_xmp_preserves_existing_fields(self):
        from idt_core.embedder import _update_xmp_description
        # Simulate iPhone-style XMP with tiff metadata
        iphone_xmp = (
            '<?xpacket begin="\xef\xbb\xbf" id="W5M0MpCehiHzreSzNTczkc9d"?>'
            '<x:xmpmeta xmlns:x="adobe:ns:meta/">'
            '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
            '<rdf:Description rdf:about="" '
            'xmlns:tiff="http://ns.adobe.com/tiff/1.0/">'
            '<tiff:Make>Apple</tiff:Make>'
            '<tiff:Model>iPhone 15 Pro</tiff:Model>'
            '</rdf:Description>'
            '</rdf:RDF></x:xmpmeta>'
            '<?xpacket end="w"?>'
        )
        updated = _update_xmp_description(iphone_xmp.encode("utf-8"), "A great photo.")
        assert "A great photo." in updated
        assert "Apple" in updated       # tiff:Make preserved
        assert "iPhone 15 Pro" in updated  # tiff:Model preserved
