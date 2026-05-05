"""Unit tests for scripts/gallery_exporter.py.

Tests cover HTML generation correctness, WCAG structural requirements,
image path handling, and the image copy utility.

These tests do NOT require wx, a display, or actual image files for
the HTML generation tests (mock ImageItem/ImageDescription objects are used).
The _copy_images tests use a real temp directory.
"""

import sys
import tempfile
import shutil
import pytest
from pathlib import Path
from unittest.mock import MagicMock

# Add scripts directory to path
scripts_path = Path(__file__).parent.parent.parent / 'scripts'
sys.path.insert(0, str(scripts_path))

import gallery_exporter as ge


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def make_description(text='A scenic mountain landscape.', provider='openai',
                     model='gpt-4o', prompt_style='narrative', metadata=None):
    """Return a minimal mock ImageDescription."""
    desc = MagicMock()
    desc.text = text
    desc.provider = provider
    desc.model = model
    desc.prompt_style = prompt_style
    desc.created = '2026-05-05T12:00:00'
    desc.metadata = metadata or {}
    return desc


def make_item(file_path='images/photo.jpg', description_text='A test description.'):
    """Return a minimal mock ImageItem with one description."""
    item = MagicMock()
    item.file_path = file_path
    item.descriptions = [make_description(text=description_text)]
    return item


def make_workspace_items(*paths_and_descriptions):
    """Return a dict of {file_path: ImageItem} as workspace.items would look."""
    result = {}
    for path, desc_text in paths_and_descriptions:
        result[path] = make_item(file_path=path, description_text=desc_text)
    return result


STYLE_NAMES = ['card_grid', 'photo_essay', 'lightbox_grid', 'simple_list']


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_esc_escapes_html_chars(self):
        assert ge._esc('<script>') == '&lt;script&gt;'
        assert ge._esc('"quoted"') == '&quot;quoted&quot;'
        assert ge._esc("O'Reilly") == "O&#x27;Reilly"

    def test_get_alt_text_returns_full_filename(self):
        assert ge._get_alt_text('/path/to/beach_sunset.jpg') == 'beach_sunset.jpg'
        assert ge._get_alt_text('images/photo.PNG') == 'photo.PNG'

    def test_get_primary_description_returns_last(self):
        item = MagicMock()
        item.descriptions = [
            make_description(text='First description'),
            make_description(text='Second description'),
        ]
        assert ge._get_primary_description(item) == 'Second description'

    def test_get_primary_description_empty_when_no_descriptions(self):
        item = MagicMock()
        item.descriptions = []
        assert ge._get_primary_description(item) == ''

    def test_get_metadata_html_disabled(self):
        item = make_item()
        result = ge._get_metadata_html(item, include_metadata=False)
        assert result == ''

    def test_get_metadata_html_no_metadata(self):
        item = make_item()
        item.descriptions[0].metadata = {}
        result = ge._get_metadata_html(item, include_metadata=True)
        assert result == ''

    def test_get_metadata_html_with_date(self):
        item = make_item()
        item.descriptions[0].metadata = {'datetime_str': '2026-03-15 10:30:00'}
        html = ge._get_metadata_html(item, include_metadata=True)
        assert '<dl' in html
        assert 'Photo Date' in html
        assert '2026-03-15 10:30:00' in html

    def test_get_metadata_html_with_location(self):
        item = make_item()
        item.descriptions[0].metadata = {
            'location': {'city': 'Seattle', 'state': 'WA', 'country': 'USA'}
        }
        html = ge._get_metadata_html(item, include_metadata=True)
        assert 'Location' in html
        assert 'Seattle' in html

    def test_get_metadata_html_with_camera(self):
        item = make_item()
        item.descriptions[0].metadata = {
            'camera': {'make': 'Canon', 'model': 'EOS R5', 'lens': '24-70mm f/2.8L'}
        }
        html = ge._get_metadata_html(item, include_metadata=True)
        assert 'Camera' in html
        assert 'Canon EOS R5' in html

    def test_js_str_escapes_backticks(self):
        result = ge._js_str('say `hello`')
        assert '\\`' in result

    def test_js_str_prevents_script_injection(self):
        result = ge._js_str('</script><script>alert(1)</script>')
        # < and > must be Unicode-escaped so the HTML parser won't close the script tag
        assert '</script>' not in result
        assert '\\u003c/script\\u003e' in result or '\\u003c' in result

    def test_js_str_escapes_template_literal_dollar(self):
        result = ge._js_str('${evil}')
        # The $ must be escaped as \$ to prevent template literal interpolation in JS
        assert '\\$' in result, "Dollar sign must be backslash-escaped in JS template literal"

    def test_js_str_escapes_backslash(self):
        result = ge._js_str('path\\to\\file')
        assert '\\\\' in result


# ---------------------------------------------------------------------------
# Shared HTML structural requirements (WCAG 2.2 AA)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('style', STYLE_NAMES)
class TestWcagStructure:
    """Every gallery style must satisfy these structural WCAG requirements."""

    def _get_html(self, style):
        items = make_workspace_items(
            ('img/photo1.jpg', 'A red barn in a snowy field.'),
            ('img/photo2.jpg', 'A sunset over the ocean.'),
        )
        # Use fake relative paths (copy step is bypassed by setting image_paths directly)
        image_paths = {fp: f'images/{Path(fp).name}' for fp in items}
        described_items = [(fp, item) for fp, item in items.items()]

        generators = {
            'card_grid':     ge._generate_card_grid,
            'photo_essay':   ge._generate_photo_essay,
            'lightbox_grid': ge._generate_lightbox_grid,
            'simple_list':   ge._generate_simple_list,
        }
        return generators[style](described_items, image_paths, 'Test Gallery', False)

    def test_doctype_html(self, style):
        html = self._get_html(style)
        assert html.startswith('<!DOCTYPE html>'), "Must start with <!DOCTYPE html>"

    def test_lang_en(self, style):
        html = self._get_html(style)
        assert 'lang="en"' in html, "html element must have lang='en'"

    def test_title_element(self, style):
        html = self._get_html(style)
        assert '<title>' in html and 'Test Gallery' in html

    def test_skip_link_present(self, style):
        html = self._get_html(style)
        assert 'href="#main-content"' in html, "Skip link must target #main-content"
        assert 'Skip to main content' in html

    def test_main_landmark(self, style):
        html = self._get_html(style)
        assert 'id="main-content"' in html, "Must have <main id='main-content'>"
        assert '<main' in html

    def test_h1_heading(self, style):
        html = self._get_html(style)
        assert '<h1>' in html or '<h1 ' in html, "Must have an h1 heading"

    def test_h2_headings_present(self, style):
        html = self._get_html(style)
        if style == 'lightbox_grid':
            # Lightbox grid renders image names dynamically in the lightbox dialog.
            # Each thumbnail button uses aria-label for its accessible name instead.
            # Verify at least one h2 exists (the lightbox caption heading).
            assert '<h2' in html, "Lightbox grid must have at least one h2 (in lightbox dialog)"
            # Verify thumbnail buttons have accessible labels
            import re
            buttons = re.findall(r'<button[^>]+aria-label="View [^"]+"', html)
            assert len(buttons) >= 2, "Each thumbnail must have aria-label='View <filename>'"
        else:
            assert html.count('<h2') >= 2, "Should have an h2 per image"

    def test_all_images_have_alt(self, style):
        """All <img> elements must have non-empty alt attributes."""
        import re
        html = self._get_html(style)
        # Find all img tags
        img_tags = re.findall(r'<img[^>]+>', html)
        for tag in img_tags:
            # Skip the lightbox empty placeholder img (alt="" is set intentionally
            # and updated dynamically via JS — structural/functional img)
            if 'id="lb-img"' in tag:
                continue
            assert 'alt="' in tag, f"Image tag missing alt attribute: {tag}"
            # Check alt is not empty
            alt_match = re.search(r'alt="([^"]*)"', tag)
            if alt_match:
                assert alt_match.group(1) != '', f"alt should not be empty: {tag}"

    def test_focus_visible_css_present(self, style):
        html = self._get_html(style)
        assert ':focus-visible' in html, "CSS must include :focus-visible rules"

    def test_no_fixed_pixel_fonts(self, style):
        """Font sizes must use rem or em, not px, to support browser zoom."""
        import re
        html = self._get_html(style)
        # Extract only the <style> block(s)
        style_blocks = re.findall(r'<style>(.*?)</style>', html, re.DOTALL)
        style_text = '\n'.join(style_blocks)
        # Look for font-size with pixel values (excluding things like 2px border)
        bad_sizes = re.findall(r'font-size\s*:\s*\d+px', style_text)
        assert not bad_sizes, f"font-size must not use px units: {bad_sizes}"


# ---------------------------------------------------------------------------
# Style-specific tests
# ---------------------------------------------------------------------------

class TestCardGrid:
    def _html(self, n_items=2):
        paths = [(f'img/photo{i}.jpg', f'Description {i}') for i in range(n_items)]
        items = make_workspace_items(*paths)
        image_paths = {fp: f'images/{Path(fp).name}' for fp in items}
        described = [(fp, item) for fp, item in items.items()]
        return ge._generate_card_grid(described, image_paths, 'Gallery', False)

    def test_uses_ul_list(self):
        assert '<ul' in self._html()

    def test_card_class_present(self):
        assert 'class="card' in self._html()

    def test_loading_lazy(self):
        assert 'loading="lazy"' in self._html()

    def test_truncation_css_visual_only(self):
        html = self._html()
        # CSS truncation must be present
        assert '-webkit-line-clamp' in html
        # But no aria-hidden on the text (full text accessible)
        assert 'aria-hidden' not in html


class TestPhotoEssay:
    def _html(self, n_items=3):
        paths = [(f'img/photo{i}.jpg', f'Description {i}') for i in range(n_items)]
        items = make_workspace_items(*paths)
        image_paths = {fp: f'images/{Path(fp).name}' for fp in items}
        described = [(fp, item) for fp, item in items.items()]
        return ge._generate_photo_essay(described, image_paths, 'Gallery', False)

    def test_uses_ol_list(self):
        assert '<ol' in self._html()

    def test_alternating_css_present(self):
        html = self._html()
        assert 'nth-child(even)' in html, "Photo essay must have alternating layout CSS"


class TestLightboxGrid:
    def _html(self, n_items=2):
        paths = [(f'img/photo{i}.jpg', f'Description {i}') for i in range(n_items)]
        items = make_workspace_items(*paths)
        image_paths = {fp: f'images/{Path(fp).name}' for fp in items}
        described = [(fp, item) for fp, item in items.items()]
        return ge._generate_lightbox_grid(described, image_paths, 'Gallery', False)

    def test_lightbox_dialog_role(self):
        html = self._html()
        assert 'role="dialog"' in html

    def test_aria_modal(self):
        html = self._html()
        assert 'aria-modal="true"' in html

    def test_close_button_aria_label(self):
        html = self._html()
        assert 'aria-label="Close gallery viewer"' in html

    def test_prev_next_aria_labels(self):
        html = self._html()
        assert 'aria-label="Previous image"' in html
        assert 'aria-label="Next image"' in html

    def test_aria_live_on_counter(self):
        html = self._html()
        assert 'aria-live="polite"' in html

    def test_thumbnail_buttons_have_aria_label(self):
        import re
        html = self._html()
        buttons = re.findall(r'<button[^>]+onclick="openLightbox[^>]+>', html)
        for btn in buttons:
            assert 'aria-label=' in btn, f"Lightbox trigger button missing aria-label: {btn}"

    def test_js_data_array_present(self):
        html = self._html()
        assert 'var GALLERY = [' in html

    def test_keyboard_handler_esc(self):
        html = self._html()
        assert "key === 'Escape'" in html or "key === \"Escape\"" in html

    def test_no_script_injection_in_js_data(self):
        """Descriptions containing </script> must not close the script tag."""
        paths = [('img/evil.jpg', 'Good description </script><script>alert(1)</script>')]
        items = make_workspace_items(*paths)
        image_paths = {fp: f'images/{Path(fp).name}' for fp in items}
        described = [(fp, item) for fp, item in items.items()]
        html = ge._generate_lightbox_grid(described, image_paths, 'Gallery', False)

        # Find the script block
        import re
        scripts = re.findall(r'<script>(.*?)</script>', html, re.DOTALL)
        # The evil </script> should not appear literally inside <script>
        for script in scripts:
            assert '</script>' not in script, \
                "Unescaped </script> found inside <script> block — injection vulnerability"


class TestSimpleList:
    def _html(self, n_items=2):
        paths = [(f'img/photo{i}.jpg', f'Description {i}') for i in range(n_items)]
        items = make_workspace_items(*paths)
        image_paths = {fp: f'images/{Path(fp).name}' for fp in items}
        described = [(fp, item) for fp, item in items.items()]
        return ge._generate_simple_list(described, image_paths, 'Gallery', False)

    def test_uses_ol_list(self):
        assert '<ol' in self._html()

    def test_no_script_tag(self):
        """Simple list must not include any JavaScript."""
        assert '<script' not in self._html()

    def test_h3_description_heading(self):
        html = self._html()
        assert '<h3' in html, "Simple list should have h3 Description headings"

    def test_toc_shown_for_more_than_5_items(self):
        paths = [(f'img/photo{i}.jpg', f'Description {i}') for i in range(6)]
        items = make_workspace_items(*paths)
        image_paths = {fp: f'images/{Path(fp).name}' for fp in items}
        described = [(fp, item) for fp, item in items.items()]
        html = ge._generate_simple_list(described, image_paths, 'Gallery', False)
        assert '<nav' in html and 'Contents' in html

    def test_no_toc_for_5_or_fewer_items(self):
        html = self._html(n_items=5)
        # TOC should not appear for 5 items
        assert 'Contents' not in html


# ---------------------------------------------------------------------------
# _copy_images tests (real filesystem)
# ---------------------------------------------------------------------------

class TestCopyImages:
    def setup_method(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _make_real_image(self, name: str) -> Path:
        """Create a tiny valid file in a source directory."""
        src_dir = self.tmpdir / 'src'
        src_dir.mkdir(exist_ok=True)
        p = src_dir / name
        p.write_bytes(b'\xff\xd8\xff\xe0' + b'\x00' * 16)  # minimal JPEG-like bytes
        return p

    def test_copies_existing_file(self):
        src = self._make_real_image('photo.jpg')
        item = make_item(file_path=str(src))
        images_dir = self.tmpdir / 'images'
        images_dir.mkdir()

        image_paths, copied, skipped, warnings = ge._copy_images(
            [(str(src), item)], images_dir
        )

        assert copied == 1
        assert skipped == 0
        assert not warnings
        assert str(src) in image_paths
        assert (images_dir / 'photo.jpg').exists()

    def test_skips_missing_file(self):
        item = make_item(file_path='/nonexistent/ghost.jpg')
        images_dir = self.tmpdir / 'images'
        images_dir.mkdir()

        image_paths, copied, skipped, warnings = ge._copy_images(
            [('/nonexistent/ghost.jpg', item)], images_dir
        )

        assert copied == 0
        assert skipped == 1
        assert len(warnings) == 1
        assert 'ghost.jpg' in warnings[0]

    def test_handles_filename_collision(self):
        src1 = self._make_real_image('photo.jpg')
        src_dir2 = self.tmpdir / 'src2'
        src_dir2.mkdir()
        src2 = src_dir2 / 'photo.jpg'
        src2.write_bytes(b'\xff\xd8\xff\xe0' + b'\x00' * 16)

        item1 = make_item(file_path=str(src1))
        item2 = make_item(file_path=str(src2))
        images_dir = self.tmpdir / 'images'
        images_dir.mkdir()

        image_paths, copied, skipped, warnings = ge._copy_images(
            [(str(src1), item1), (str(src2), item2)], images_dir
        )

        assert copied == 2
        assert skipped == 0
        # Both should have unique dest names
        dest_names = list(image_paths.values())
        assert len(set(dest_names)) == 2, "Destination filenames must be unique"


# ---------------------------------------------------------------------------
# export_gallery end-to-end tests
# ---------------------------------------------------------------------------

class TestExportGallery:
    def setup_method(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _make_workspace_with_real_files(self, n=2):
        items = {}
        for i in range(n):
            src = self.tmpdir / f'photo{i}.jpg'
            src.write_bytes(b'\xff\xd8\xff\xe0' + b'\x00' * 16)
            items[str(src)] = make_item(
                file_path=str(src),
                description_text=f'Description for photo {i}.'
            )
        return items

    @pytest.mark.parametrize('style', STYLE_NAMES)
    def test_creates_index_html(self, style):
        items = self._make_workspace_with_real_files(2)
        output_dir = self.tmpdir / 'gallery'
        options = {
            'output_dir': str(output_dir),
            'title': 'My Test Gallery',
            'style': style,
            'include_metadata': False,
        }
        result = ge.export_gallery(items, options)
        assert Path(result['output_file']).exists()
        assert Path(result['output_file']).name == 'index.html'

    @pytest.mark.parametrize('style', STYLE_NAMES)
    def test_creates_images_subfolder(self, style):
        items = self._make_workspace_with_real_files(2)
        output_dir = self.tmpdir / f'gallery_{style}'
        options = {
            'output_dir': str(output_dir),
            'title': 'Gallery',
            'style': style,
            'include_metadata': False,
        }
        ge.export_gallery(items, options)
        assert (output_dir / 'images').is_dir()

    def test_raises_when_no_descriptions(self):
        item = make_item()
        item.descriptions = []  # no descriptions
        items = {'/path/photo.jpg': item}
        with pytest.raises(ValueError, match='No images with descriptions'):
            ge.export_gallery(items, {
                'output_dir': str(self.tmpdir / 'empty'),
                'title': 'Gallery',
                'style': 'card_grid',
                'include_metadata': False,
            })

    def test_result_counts(self):
        items = self._make_workspace_with_real_files(3)
        output_dir = self.tmpdir / 'gallery_count'
        result = ge.export_gallery(items, {
            'output_dir': str(output_dir),
            'title': 'Gallery',
            'style': 'simple_list',
            'include_metadata': False,
        })
        assert result['images_copied'] == 3
        assert result['descriptions_included'] == 3
        assert result['images_skipped'] == 0

    def test_skips_items_without_source_file(self):
        items = self._make_workspace_with_real_files(2)
        # Add a ghost item
        ghost = make_item(file_path='/nonexistent/ghost.jpg',
                          description_text='Ghost description')
        items['/nonexistent/ghost.jpg'] = ghost

        output_dir = self.tmpdir / 'gallery_skip'
        result = ge.export_gallery(items, {
            'output_dir': str(output_dir),
            'title': 'Gallery',
            'style': 'card_grid',
            'include_metadata': False,
        })
        assert result['images_copied'] == 2
        assert result['images_skipped'] == 1
        assert any('ghost.jpg' in w for w in result['warnings'])

    def test_title_appears_in_html(self):
        items = self._make_workspace_with_real_files(1)
        output_dir = self.tmpdir / 'gallery_title'
        ge.export_gallery(items, {
            'output_dir': str(output_dir),
            'title': 'My Unique Gallery Title XYZ',
            'style': 'card_grid',
            'include_metadata': False,
        })
        content = (output_dir / 'index.html').read_text(encoding='utf-8')
        assert 'My Unique Gallery Title XYZ' in content
