#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for alt text support in image_describer.py

Tests cover:
  - _load_alt_text_mapping: explicit path, auto-detect, quality filter, disabled flag
  - write_description_to_file: Alt Text field placement and suppression
"""

import json
import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add scripts directory to path
scripts_dir = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

# image_describer.py runs logging.basicConfig() at module-level when first imported.
# With pytest's default fd-level capture on Windows, basicConfig installs a StreamHandler
# pointing at pytest's capture tmpfile, which gets closed between tests → "underlying
# buffer has been detached".  Pre-adding a NullHandler makes basicConfig a no-op
# (it never touches handlers if the root logger already has one).
logging.root.addHandler(logging.NullHandler())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_describer(tmp_path, include_alt_text=True, alt_text_mapping_file=None):
    """
    Create an ImageDescriber with the AI provider mocked out so that
    __init__ does not require Ollama/OpenAI to be available.

    Import happens inside the function (not at module level) to avoid
    logging.basicConfig() conflicts with pytest stream capture.
    """
    from image_describer import ImageDescriber  # noqa: PLC0415

    with patch.object(ImageDescriber, "_initialize_provider", return_value=MagicMock()):
        describer = ImageDescriber(
            provider="ollama",
            output_dir=str(tmp_path),
            include_alt_text=include_alt_text,
            alt_text_mapping_file=alt_text_mapping_file,
        )
    return describer


# ---------------------------------------------------------------------------
# _load_alt_text_mapping
# ---------------------------------------------------------------------------

class TestLoadAltTextMapping:

    def test_returns_empty_when_disabled(self, tmp_path):
        """include_alt_text=False always returns empty dict regardless of file."""
        mapping = {"photo.jpg": "A beautiful sunset over the mountains"}
        (tmp_path / "alt_text_mapping.json").write_text(json.dumps(mapping), encoding="utf-8")

        describer = _make_describer(tmp_path, include_alt_text=False)
        result = describer._load_alt_text_mapping(tmp_path)

        assert result == {}

    def test_auto_detects_mapping_in_image_dir(self, tmp_path):
        """Without an explicit path, mapping is auto-detected from the image directory."""
        mapping = {"photo.jpg": "A beautiful sunset over the mountains"}
        (tmp_path / "alt_text_mapping.json").write_text(json.dumps(mapping), encoding="utf-8")

        describer = _make_describer(tmp_path)
        result = describer._load_alt_text_mapping(tmp_path)

        assert result == {"photo.jpg": "A beautiful sunset over the mountains"}

    def test_loads_from_explicit_path(self, tmp_path):
        """When alt_text_mapping_file is set, that explicit path takes precedence."""
        other_dir = tmp_path / "other"
        other_dir.mkdir()
        mapping = {"img001.jpg": "Panoramic view of the city skyline at dusk"}
        explicit_file = other_dir / "alt_text_mapping.json"
        explicit_file.write_text(json.dumps(mapping), encoding="utf-8")

        describer = _make_describer(tmp_path, alt_text_mapping_file=str(explicit_file))
        result = describer._load_alt_text_mapping(tmp_path)

        assert result == {"img001.jpg": "Panoramic view of the city skyline at dusk"}

    def test_returns_empty_when_file_not_found(self, tmp_path):
        """Returns empty dict gracefully when no mapping file exists."""
        describer = _make_describer(tmp_path)
        result = describer._load_alt_text_mapping(tmp_path)

        assert result == {}

    def test_quality_filter_rejects_short_text(self, tmp_path):
        """Alt text shorter than 10 characters is excluded."""
        mapping = {"logo.png": "Logo"}
        (tmp_path / "alt_text_mapping.json").write_text(json.dumps(mapping), encoding="utf-8")

        describer = _make_describer(tmp_path)
        result = describer._load_alt_text_mapping(tmp_path)

        assert result == {}

    def test_quality_filter_rejects_text_without_space(self, tmp_path):
        """Alt text without a space (e.g. a bare filename) is excluded."""
        mapping = {"image.jpg": "IMG_01234567"}
        (tmp_path / "alt_text_mapping.json").write_text(json.dumps(mapping), encoding="utf-8")

        describer = _make_describer(tmp_path)
        result = describer._load_alt_text_mapping(tmp_path)

        assert result == {}

    def test_quality_filter_accepts_valid_alt_text(self, tmp_path):
        """Alt text that passes both filters (>=10 chars and contains space) is kept."""
        mapping = {
            "pass.jpg": "A scenic mountain vista at sunset",
            "fail_short.jpg": "Short",
            "fail_nospace.jpg": "NoSpaceHere123",
        }
        (tmp_path / "alt_text_mapping.json").write_text(json.dumps(mapping), encoding="utf-8")

        describer = _make_describer(tmp_path)
        result = describer._load_alt_text_mapping(tmp_path)

        assert list(result.keys()) == ["pass.jpg"]
        assert result["pass.jpg"] == "A scenic mountain vista at sunset"

    def test_strips_internal_newlines(self, tmp_path):
        """Newlines and extra whitespace in alt text are collapsed to a single space."""
        raw_text = "A beautiful\nsunset\n  over the mountains"
        mapping = {"photo.jpg": raw_text}
        (tmp_path / "alt_text_mapping.json").write_text(json.dumps(mapping), encoding="utf-8")

        describer = _make_describer(tmp_path)
        result = describer._load_alt_text_mapping(tmp_path)

        assert "\n" not in result["photo.jpg"]
        assert result["photo.jpg"] == "A beautiful sunset over the mountains"

    def test_handles_malformed_json(self, tmp_path):
        """Returns empty dict gracefully when the mapping file is invalid JSON."""
        (tmp_path / "alt_text_mapping.json").write_text("{ not valid json }", encoding="utf-8")

        describer = _make_describer(tmp_path)
        result = describer._load_alt_text_mapping(tmp_path)

        assert result == {}

    def test_ignores_non_string_values(self, tmp_path):
        """Non-string values in the mapping are silently skipped."""
        mapping = {"photo.jpg": 12345, "other.jpg": "A valid description here"}
        (tmp_path / "alt_text_mapping.json").write_text(json.dumps(mapping), encoding="utf-8")

        describer = _make_describer(tmp_path)
        result = describer._load_alt_text_mapping(tmp_path)

        assert "photo.jpg" not in result
        assert result["other.jpg"] == "A valid description here"


# ---------------------------------------------------------------------------
# write_description_to_file — Alt Text field
# ---------------------------------------------------------------------------

class TestWriteDescriptionAltText:
    """Tests for alt_text parameter in write_description_to_file."""

    def _read_output(self, output_file: Path) -> str:
        return output_file.read_text(encoding="utf-8")

    def test_alt_text_written_before_description(self, tmp_path):
        """Alt Text: line appears immediately before Description: line."""
        describer = _make_describer(tmp_path)
        output_file = tmp_path / "image_descriptions.txt"
        image_path = tmp_path / "photo.jpg"
        image_path.write_bytes(b"")  # empty placeholder

        describer.write_description_to_file(
            image_path=image_path,
            description="The AI-generated description of the image.",
            output_file=output_file,
            alt_text="A beautiful sunset over the mountains",
        )

        content = self._read_output(output_file)
        alt_idx = content.find("Alt Text:")
        desc_idx = content.find("Description:")

        assert alt_idx != -1, "Alt Text: field missing"
        assert desc_idx != -1, "Description: field missing"
        assert alt_idx < desc_idx, "Alt Text: must appear before Description:"

    def test_alt_text_line_content(self, tmp_path):
        """Alt Text: line contains the exact provided alt text."""
        describer = _make_describer(tmp_path)
        output_file = tmp_path / "image_descriptions.txt"
        image_path = tmp_path / "photo.jpg"
        image_path.write_bytes(b"")

        alt = "Panoramic view of the city skyline at night"
        describer.write_description_to_file(
            image_path=image_path,
            description="AI description here.",
            output_file=output_file,
            alt_text=alt,
        )

        content = self._read_output(output_file)
        assert f"Alt Text: {alt}" in content

    def test_no_alt_text_field_when_none(self, tmp_path):
        """When alt_text is None (default), the Alt Text: line is not written."""
        describer = _make_describer(tmp_path)
        output_file = tmp_path / "image_descriptions.txt"
        image_path = tmp_path / "photo.jpg"
        image_path.write_bytes(b"")

        describer.write_description_to_file(
            image_path=image_path,
            description="AI description without alt text.",
            output_file=output_file,
        )

        content = self._read_output(output_file)
        assert "Alt Text:" not in content

    def test_description_still_present_with_alt_text(self, tmp_path):
        """Description: field is always written even when alt text is provided."""
        describer = _make_describer(tmp_path)
        output_file = tmp_path / "image_descriptions.txt"
        image_path = tmp_path / "photo.jpg"
        image_path.write_bytes(b"")

        ai_desc = "The AI-generated description text."
        describer.write_description_to_file(
            image_path=image_path,
            description=ai_desc,
            output_file=output_file,
            alt_text="A scenic landscape photo",
        )

        content = self._read_output(output_file)
        assert f"Description: {ai_desc}" in content

    def test_multiple_entries_each_have_alt_text(self, tmp_path):
        """Writing two entries to the same file gives each its own Alt Text: line."""
        describer = _make_describer(tmp_path)
        output_file = tmp_path / "image_descriptions.txt"

        for i in range(2):
            image_path = tmp_path / f"photo{i}.jpg"
            image_path.write_bytes(b"")
            describer.write_description_to_file(
                image_path=image_path,
                description=f"Description {i}",
                output_file=output_file,
                alt_text=f"Alt text for image number {i}",
            )

        content = self._read_output(output_file)
        assert content.count("Alt Text:") == 2
        assert content.count("Description:") == 2
