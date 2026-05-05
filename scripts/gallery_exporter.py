"""HTML gallery exporter for ImageDescriber.

Exports images and their descriptions as a self-contained, web-publishable
HTML gallery folder:

    <output_dir>/index.html
    <output_dir>/images/<filename>.*

All CSS and JavaScript are embedded inline so the result is a single folder
that can be zipped and published to a web server without modification.

WCAG 2.2 AA conformance requirements met in every gallery style:
  - lang="en", explicit <title>, skip link, <main> landmark, heading hierarchy
  - All images carry alt text (filename with extension, per project decision)
  - Colour contrast >= 4.5:1 for normal text, >= 3:1 for UI components
  - :focus-visible outlines on all interactive elements
  - rem/em-based font sizes; no layout loss at 200 % zoom
  - Keyboard-accessible lightbox (focus trap, Esc, arrow keys)
  - Truncation is visual-only — full text remains in the DOM for screen readers
"""

import html as _html
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def export_gallery(items: dict, options: dict) -> dict:
    """Export workspace images + descriptions as an HTML gallery folder.

    Args:
        items:   workspace.items — Dict[str, ImageItem]
        options: {
            'output_dir':       str   — destination folder (created if needed)
            'title':            str   — gallery <h1> and <title>
            'style':            str   — 'card_grid' | 'photo_essay' |
                                        'lightbox_grid' | 'simple_list'
            'include_metadata': bool  — show photo date / camera / location
        }

    Returns:
        {
            'images_copied':          int,
            'images_skipped':         int,
            'descriptions_included':  int,
            'output_file':            str,   — absolute path to index.html
            'warnings':               List[str],
        }

    Raises:
        ValueError: if no described images are found or none could be copied.
    """
    output_dir = Path(options['output_dir'])
    title = (options.get('title') or 'Image Gallery').strip() or 'Image Gallery'
    style = options.get('style', 'card_grid')
    include_metadata = bool(options.get('include_metadata', False))
    description_selection = options.get('description_selection', 'newest')

    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir = output_dir / 'images'
    images_dir.mkdir(exist_ok=True)

    # Sort all items by filename; keep only those with descriptions
    described_sorted: List[Tuple[str, object]] = sorted(
        [(fp, item) for fp, item in items.items() if item.descriptions],
        key=lambda x: Path(x[0]).name.lower(),
    )

    if not described_sorted:
        raise ValueError(
            "No images with descriptions were found. "
            "Process your images first, then export the gallery."
        )

    # Copy images, build path mapping
    image_paths, images_copied, images_skipped, warnings = _copy_images(
        described_sorted, images_dir
    )

    # Keep only items whose image was successfully copied
    described_items = [
        (fp, item) for fp, item in described_sorted if fp in image_paths
    ]

    if not described_items:
        raise ValueError(
            "No images could be copied. "
            "Check that the source files exist and are accessible."
        )

    generators = {
        'card_grid':     _generate_card_grid,
        'photo_essay':   _generate_photo_essay,
        'lightbox_grid': _generate_lightbox_grid,
        'simple_list':   _generate_simple_list,
    }
    generator = generators.get(style, _generate_card_grid)
    html_content = generator(described_items, image_paths, title, include_metadata, description_selection)

    index_path = output_dir / 'index.html'
    index_path.write_text(html_content, encoding='utf-8')

    return {
        'images_copied':         images_copied,
        'images_skipped':        images_skipped,
        'descriptions_included': len(described_items),
        'output_file':           str(index_path),
        'warnings':              warnings,
    }


# ---------------------------------------------------------------------------
# Image copying
# ---------------------------------------------------------------------------

def _copy_images(
    sorted_items: List[Tuple[str, object]],
    images_dir: Path,
) -> Tuple[Dict[str, str], int, int, List[str]]:
    """Copy source images into <output>/images/.

    Returns:
        (image_paths, copied_count, skipped_count, warnings)
        image_paths maps original_file_path -> 'images/<dest_filename>'
    """
    image_paths: Dict[str, str] = {}
    used_names: Set[str] = set()
    copied = 0
    skipped = 0
    warnings: List[str] = []

    for file_path, _item in sorted_items:
        src = Path(file_path)
        if not src.exists():
            warnings.append(f"Source file not found, skipped: {file_path}")
            skipped += 1
            continue

        # Resolve collision-free destination filename
        dest_name = src.name
        counter = 1
        while dest_name in used_names:
            dest_name = f"{src.stem}_{counter}{src.suffix}"
            counter += 1
        used_names.add(dest_name)

        dest_path = images_dir / dest_name
        try:
            shutil.copy2(src, dest_path)
            image_paths[file_path] = f"images/{dest_name}"
            copied += 1
        except Exception as exc:
            warnings.append(f"Failed to copy {src.name}: {exc}")
            skipped += 1

    return image_paths, copied, skipped, warnings


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _esc(text: str) -> str:
    """HTML-escape a string."""
    return _html.escape(str(text), quote=True)


def _get_alt_text(file_path: str) -> str:
    """Return the alt text for an image: filename with extension."""
    return Path(file_path).name


def _get_primary_description(item) -> str:
    """Return the text of the most-recently-added description, or ''."""
    if not item.descriptions:
        return ''
    return item.descriptions[-1].text


def _desc_label(desc) -> str:
    """Format a short attribution label: 'model · M/D/YYYY'."""
    parts = []
    model = getattr(desc, 'model', '')
    if model:
        parts.append(str(model))
    created = getattr(desc, 'created', '')
    if created:
        try:
            dt = datetime.fromisoformat(str(created))
            parts.append(f'{dt.month}/{dt.day}/{dt.year}')
        except (ValueError, TypeError):
            pass
    return ' \u00b7 '.join(parts)


def _get_descriptions(item, selection: str) -> List[dict]:
    """Return list of {'text': str, 'label': str} based on selection.

    selection: 'newest' | 'oldest' | 'all'
    """
    if not item.descriptions:
        return [{'text': '', 'label': ''}]
    if selection == 'oldest':
        d = item.descriptions[0]
        return [{'text': d.text, 'label': ''}]
    if selection == 'all':
        return [{'text': d.text, 'label': _desc_label(d)} for d in item.descriptions]
    # Default: newest
    d = item.descriptions[-1]
    return [{'text': d.text, 'label': ''}]


def _render_descriptions_html(descriptions: List[dict], text_class: str) -> str:
    """Render description block(s) to HTML.

    Single unlabeled description  → plain <p class=text_class>.
    Multiple or labelled           → <div class="desc-block"> wrappers with attribution.
    """
    if len(descriptions) == 1 and not descriptions[0]['label']:
        return f'<p class="{text_class}">{_esc(descriptions[0]["text"])}</p>'
    parts = []
    for d in descriptions:
        label_html = (
            f'<span class="desc-label">{_esc(d["label"])}</span>\n'
            if d['label'] else ''
        )
        parts.append(
            f'<div class="desc-block">'
            f'{label_html}'
            f'<p class="{text_class}">{_esc(d["text"])}</p>'
            f'</div>'
        )
    return '\n'.join(parts)


def _get_metadata_html(item, include_metadata: bool) -> str:
    """Return a <dl> metadata block or '' if disabled / unavailable."""
    if not include_metadata or not item.descriptions:
        return ''
    meta = item.descriptions[-1].metadata
    if not meta:
        return ''

    rows: List[Tuple[str, str]] = []

    # Photo date
    if 'datetime_str' in meta:
        rows.append(('Photo Date', str(meta['datetime_str'])))
    elif 'datetime' in meta:
        rows.append(('Photo Date', str(meta['datetime'])))

    # Location
    if 'location' in meta:
        loc = meta['location']
        parts = []
        city = loc.get('city') or loc.get('town')
        state = loc.get('state')
        country = loc.get('country')
        for part in (city, state, country):
            if part:
                parts.append(str(part))
        if parts:
            rows.append(('Location', ', '.join(parts)))

    # Camera
    if 'camera' in meta:
        cam = meta['camera']
        cam_parts = []
        if 'make' in cam and 'model' in cam:
            cam_parts.append(f"{cam['make']} {cam['model']}")
        if 'lens' in cam:
            cam_parts.append(str(cam['lens']))
        if cam_parts:
            rows.append(('Camera', ', '.join(cam_parts)))

    if not rows:
        return ''

    items_html = '\n'.join(
        f'<dt>{_esc(label)}</dt><dd>{_esc(value)}</dd>'
        for label, value in rows
    )
    return f'<dl class="img-meta">{items_html}</dl>\n'


def _needs_osm(described_items: List[Tuple[str, object]]) -> bool:
    """Return True if any description has OSM attribution required."""
    for _fp, item in described_items:
        if item.descriptions:
            meta = item.descriptions[-1].metadata
            if meta and meta.get('osm_attribution_required'):
                return True
    return False


def _js_str(s: str) -> str:
    """Encode a Python string as a safe JS template literal.

    Unicode-escapes < and > to prevent </script> tag injection when the
    literal is embedded inside an HTML <script> block.
    """
    escaped = (
        str(s)
        .replace('\\', '\\\\')
        .replace('`', '\\`')
        .replace('$', '\\$')
        .replace('\r', '\\r')
        .replace('\n', '\\n')
        .replace('<', '\\u003c')
        .replace('>', '\\u003e')
    )
    return f'`{escaped}`'


# ---------------------------------------------------------------------------
# Shared CSS fragments
# ---------------------------------------------------------------------------

_SKIP_LINK_CSS = """\
.skip-link {
    position: absolute;
    left: -9999px;
    top: auto;
    width: 1px;
    height: 1px;
    overflow: hidden;
    z-index: 9999;
}
.skip-link:focus {
    position: fixed;
    top: 0;
    left: 0;
    width: auto;
    height: auto;
    padding: .5rem 1rem;
    background: #0d6efd;
    color: #fff;
    font-size: 1rem;
    font-weight: 600;
    text-decoration: none;
    border-radius: 0 0 .25rem 0;
    outline: 3px solid #fff;
    outline-offset: 2px;
}
"""

_BASE_CSS = """\
*, *::before, *::after { box-sizing: border-box; }
:root {
    --color-text:         #212529;
    --color-text-muted:   #6c757d;
    --color-bg:           #f8f9fa;
    --color-surface:      #ffffff;
    --color-border:       #dee2e6;
    --color-accent:       #0d6efd;
    --color-accent-hover: #0b5ed7;
    --focus-outline:      2px solid #0d6efd;
    --focus-offset:       2px;
    --radius:             .5rem;
}
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                 "Helvetica Neue", Arial, sans-serif;
    font-size: 1rem;
    line-height: 1.6;
    color: var(--color-text);
    background: var(--color-bg);
    margin: 0;
    padding: 0;
}
a { color: var(--color-accent); }
a:hover { color: var(--color-accent-hover); }
a:focus-visible, button:focus-visible {
    outline: var(--focus-outline);
    outline-offset: var(--focus-offset);
    border-radius: 2px;
}
.page-header {
    background: var(--color-surface);
    border-bottom: 1px solid var(--color-border);
    padding: 1.5rem 2rem;
}
.page-header h1 {
    margin: 0 0 .25rem 0;
    font-size: 1.75rem;
    color: var(--color-text);
}
.page-header .subtitle {
    color: var(--color-text-muted);
    font-size: .875rem;
    margin: 0;
}
main { padding: 1.5rem 2rem 3rem; }
.page-footer {
    border-top: 1px solid var(--color-border);
    padding: 1rem 2rem;
    font-size: .8rem;
    color: var(--color-text-muted);
    background: var(--color-surface);
}
.page-footer p { margin: .2rem 0; }
.toc {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    padding: 1rem 1.5rem;
    margin-bottom: 2rem;
    max-width: 40rem;
}
.toc h2 { margin: 0 0 .75rem 0; font-size: 1.1rem; }
.toc ol { margin: 0; padding-left: 1.25rem; }
.toc li { padding: .2rem 0; }
.img-meta {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: .2rem .75rem;
    font-size: .8rem;
    color: var(--color-text-muted);
    margin: .5rem 0 0 0;
}
.img-meta dt { font-weight: 600; white-space: nowrap; }
.img-meta dd { margin: 0; }
.desc-block { margin-bottom: .75rem; }
.desc-block:last-child { margin-bottom: 0; }
.desc-label {
    display: block;
    font-size: .75rem;
    font-weight: 600;
    color: var(--color-text-muted);
    text-transform: uppercase;
    letter-spacing: .05em;
    margin-bottom: .2rem;
}
"""


# ---------------------------------------------------------------------------
# Shared page structure builders
# ---------------------------------------------------------------------------

def _build_toc(described_items: List[Tuple[str, object]]) -> str:
    """Return an accessible TOC block if there are more than 5 items."""
    if len(described_items) <= 5:
        return ''
    items_html = '\n'.join(
        f'<li><a href="#img-{i}">{_esc(Path(fp).name)}</a></li>'
        for i, (fp, _) in enumerate(described_items)
    )
    return (
        '<nav class="toc" aria-label="Gallery table of contents">\n'
        '  <h2>Contents</h2>\n'
        f'  <ol>\n{items_html}\n  </ol>\n'
        '</nav>\n'
    )


def _html_head(title: str, extra_css: str = '') -> str:
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    return (
        '<!DOCTYPE html>\n'
        '<html lang="en">\n'
        '<head>\n'
        '  <meta charset="UTF-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f'  <title>{_esc(title)}</title>\n'
        '  <style>\n'
        + _SKIP_LINK_CSS
        + _BASE_CSS
        + extra_css
        + '  </style>\n'
        '</head>\n'
        '<body>\n'
        '  <a href="#main-content" class="skip-link">Skip to main content</a>\n'
        '  <header class="page-header">\n'
        f'    <h1>{_esc(title)}</h1>\n'
        f'    <p class="subtitle">Generated {_esc(now)}</p>\n'
        '  </header>\n'
        '  <main id="main-content">\n'
    )


def _html_foot(osm_needed: bool = False) -> str:
    osm = ''
    if osm_needed:
        osm = (
            '    <p>Location data &copy; '
            '<a href="https://www.openstreetmap.org/copyright" rel="noopener">'
            'OpenStreetMap contributors</a></p>\n'
        )
    return (
        '  </main>\n'
        '  <footer class="page-footer">\n'
        + osm
        + '    <p>Exported with '
        '<a href="https://github.com/Dastari/image-description-toolkit" rel="noopener">'
        'Image Description Toolkit</a></p>\n'
        '  </footer>\n'
        '</body>\n'
        '</html>\n'
    )


# ---------------------------------------------------------------------------
# Style: Card Grid
# ---------------------------------------------------------------------------

_CARD_GRID_CSS = """\
.gallery-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 1.5rem;
    list-style: none;
    padding: 0;
    margin: 0;
}
.card {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    overflow: hidden;
    display: flex;
    flex-direction: column;
}
.card-img-wrap {
    aspect-ratio: 4 / 3;
    overflow: hidden;
    background: #e9ecef;
}
.card-img-wrap img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
}
.card-body {
    padding: 1rem;
    flex: 1;
    display: flex;
    flex-direction: column;
}
.card-title {
    font-size: .95rem;
    font-weight: 600;
    margin: 0 0 .5rem 0;
    word-break: break-word;
    color: var(--color-text);
}
.card-desc {
    font-size: .875rem;
    color: #343a40;
    line-height: 1.5;
    margin: 0;
    /* Visual-only truncation: full text stays in DOM for screen readers */
    display: -webkit-box;
    -webkit-line-clamp: 4;
    -webkit-box-orient: vertical;
    overflow: hidden;
}
.card-meta { margin-top: auto; padding-top: .5rem; }
"""


def _generate_card_grid(
    described_items: List[Tuple[str, object]],
    image_paths: Dict[str, str],
    title: str,
    include_metadata: bool,
    description_selection: str = 'newest',
) -> str:
    toc = _build_toc(described_items)
    cards = []
    for i, (fp, item) in enumerate(described_items):
        rel = _esc(image_paths.get(fp, ''))
        alt = _esc(_get_alt_text(fp))
        filename = _esc(Path(fp).name)
        descs_html = _render_descriptions_html(
            _get_descriptions(item, description_selection), 'card-desc'
        )
        meta_html = _get_metadata_html(item, include_metadata)
        cards.append(
            f'<li>\n'
            f'  <article class="card" id="img-{i}">\n'
            f'    <div class="card-img-wrap">\n'
            f'      <img src="{rel}" alt="{alt}" loading="lazy">\n'
            f'    </div>\n'
            f'    <div class="card-body">\n'
            f'      <h2 class="card-title">{filename}</h2>\n'
            f'      {descs_html}\n'
            f'      <div class="card-meta">{meta_html}</div>\n'
            f'    </div>\n'
            f'  </article>\n'
            f'</li>'
        )
    cards_html = '\n'.join(cards)
    return (
        _html_head(title, _CARD_GRID_CSS)
        + toc
        + '<ul class="gallery-grid" aria-label="Image gallery">\n'
        + cards_html + '\n'
        + '</ul>\n'
        + _html_foot(_needs_osm(described_items))
    )


# ---------------------------------------------------------------------------
# Style: Photo Essay
# ---------------------------------------------------------------------------

_PHOTO_ESSAY_CSS = """\
.essay-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 3rem;
}
.essay-entry {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    overflow: hidden;
}
.essay-inner {
    display: grid;
    grid-template-columns: 1fr 1fr;
    min-height: 320px;
}
/* Alternate image side for even entries using CSS order — DOM order unchanged */
.essay-entry:nth-child(even) .essay-img-wrap { order: 2; }
.essay-entry:nth-child(even) .essay-text    { order: 1; }
.essay-img-wrap {
    overflow: hidden;
    background: #e9ecef;
}
.essay-img-wrap img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
}
.essay-text {
    padding: 2rem;
    display: flex;
    flex-direction: column;
    justify-content: center;
}
.essay-title {
    font-size: 1.1rem;
    font-weight: 600;
    margin: 0 0 1rem 0;
    word-break: break-word;
    color: var(--color-text);
}
.essay-desc {
    font-size: 1rem;
    color: #343a40;
    line-height: 1.7;
    margin: 0;
}
.essay-meta { margin-top: 1rem; }
@media (max-width: 640px) {
    .essay-inner {
        grid-template-columns: 1fr;
    }
    .essay-entry:nth-child(even) .essay-img-wrap { order: unset; }
    .essay-entry:nth-child(even) .essay-text    { order: unset; }
    .essay-img-wrap { min-height: 220px; }
}
"""


def _generate_photo_essay(
    described_items: List[Tuple[str, object]],
    image_paths: Dict[str, str],
    title: str,
    include_metadata: bool,
    description_selection: str = 'newest',
) -> str:
    toc = _build_toc(described_items)
    entries = []
    for i, (fp, item) in enumerate(described_items):
        rel = _esc(image_paths.get(fp, ''))
        alt = _esc(_get_alt_text(fp))
        filename = _esc(Path(fp).name)
        descs_html = _render_descriptions_html(
            _get_descriptions(item, description_selection), 'essay-desc'
        )
        meta_html = _get_metadata_html(item, include_metadata)
        entries.append(
            f'<li>\n'
            f'  <article class="essay-entry" id="img-{i}">\n'
            f'    <div class="essay-inner">\n'
            f'      <div class="essay-img-wrap">\n'
            f'        <img src="{rel}" alt="{alt}" loading="lazy">\n'
            f'      </div>\n'
            f'      <div class="essay-text">\n'
            f'        <h2 class="essay-title">{filename}</h2>\n'
            f'        {descs_html}\n'
            f'        <div class="essay-meta">{meta_html}</div>\n'
            f'      </div>\n'
            f'    </div>\n'
            f'  </article>\n'
            f'</li>'
        )
    entries_html = '\n'.join(entries)
    return (
        _html_head(title, _PHOTO_ESSAY_CSS)
        + toc
        + '<ol class="essay-list" aria-label="Image gallery">\n'
        + entries_html + '\n'
        + '</ol>\n'
        + _html_foot(_needs_osm(described_items))
    )


# ---------------------------------------------------------------------------
# Style: Lightbox Grid
# ---------------------------------------------------------------------------

_LIGHTBOX_GRID_CSS = """\
.thumb-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 1rem;
    list-style: none;
    padding: 0;
    margin: 0;
}
.thumb-item button {
    width: 100%;
    padding: 0;
    border: 2px solid var(--color-border);
    border-radius: var(--radius);
    background: #e9ecef;
    cursor: pointer;
    overflow: hidden;
    display: block;
}
.thumb-item button:hover {
    border-color: var(--color-accent);
}
.thumb-item button:focus-visible {
    outline: var(--focus-outline);
    outline-offset: var(--focus-offset);
    border-color: var(--color-accent);
}
.thumb-item img {
    width: 100%;
    aspect-ratio: 1;
    object-fit: cover;
    display: block;
}
/* ---- Lightbox overlay ---- */
#lightbox {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, .85);
    z-index: 1000;
    align-items: center;
    justify-content: center;
}
#lightbox.open { display: flex; }
#lightbox-dialog {
    background: var(--color-surface);
    border-radius: var(--radius);
    max-width: min(92vw, 1000px);
    max-height: 90vh;
    width: 100%;
    overflow-y: auto;
    position: relative;
    display: flex;
    flex-direction: column;
}
#lightbox-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: .75rem 1rem;
    border-bottom: 1px solid var(--color-border);
    gap: .5rem;
    flex-wrap: wrap;
    flex-shrink: 0;
}
#lightbox-counter {
    font-size: .875rem;
    color: var(--color-text-muted);
    flex: 1;
}
#lightbox-nav { display: flex; gap: .5rem; }
.lb-btn {
    background: transparent;
    border: 1px solid var(--color-border);
    border-radius: .375rem;
    padding: .4rem .75rem;
    font-size: .9rem;
    cursor: pointer;
    color: var(--color-text);
    min-width: 44px;
    min-height: 44px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
}
.lb-btn:hover { background: #f0f0f0; border-color: #adb5bd; }
.lb-btn:disabled { opacity: .4; cursor: not-allowed; }
.lb-btn:focus-visible {
    outline: var(--focus-outline);
    outline-offset: var(--focus-offset);
}
#lightbox-body {
    padding: 1.5rem;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.5rem;
    align-items: start;
    overflow-y: auto;
}
#lightbox-img-wrap img {
    width: 100%;
    height: auto;
    border-radius: 4px;
    display: block;
}
#lightbox-caption-area h2 {
    font-size: 1rem;
    margin: 0 0 .75rem 0;
    word-break: break-word;
}
#lb-desc {
    font-size: .9rem;
    line-height: 1.6;
    color: #343a40;
    margin: 0;
}
#lb-desc .lb-desc-text {
    margin: 0;
    white-space: pre-wrap;
}
#lightbox-meta { margin-top: .75rem; }
@media (max-width: 640px) {
    #lightbox-body { grid-template-columns: 1fr; }
}
"""

_LIGHTBOX_JS = """\
(function () {
    'use strict';

    var currentIndex = 0;
    var triggerElement = null;

    function openLightbox(index, trigger) {
        currentIndex = index;
        triggerElement = trigger;
        renderLightbox();
        var lb = document.getElementById('lightbox');
        lb.classList.add('open');
        document.body.style.overflow = 'hidden';
        document.getElementById('lb-close').focus();
    }

    function closeLightbox() {
        var lb = document.getElementById('lightbox');
        lb.classList.remove('open');
        document.body.style.overflow = '';
        if (triggerElement) { triggerElement.focus(); }
    }

    function renderLightbox() {
        var item = GALLERY[currentIndex];
        document.getElementById('lb-img').src = item.src;
        document.getElementById('lb-img').alt = item.alt;
        document.getElementById('lb-filename').textContent = item.filename;
        document.getElementById('lb-desc').innerHTML = item.desc;
        document.getElementById('lb-meta').innerHTML = item.meta;
        document.getElementById('lightbox-counter').textContent =
            (currentIndex + 1) + ' of ' + GALLERY.length;
        document.getElementById('lb-prev').disabled = (currentIndex === 0);
        document.getElementById('lb-next').disabled = (currentIndex === GALLERY.length - 1);
    }

    function prevImage() {
        if (currentIndex > 0) { currentIndex--; renderLightbox(); }
    }

    function nextImage() {
        if (currentIndex < GALLERY.length - 1) { currentIndex++; renderLightbox(); }
    }

    function trapFocus(e) {
        var dialog = document.getElementById('lightbox-dialog');
        if (!dialog) { return; }
        var focusable = Array.prototype.slice.call(
            dialog.querySelectorAll('button:not([disabled]),a[href],[tabindex]:not([tabindex="-1"])')
        );
        if (!focusable.length) { return; }
        var first = focusable[0];
        var last = focusable[focusable.length - 1];
        if (e.key === 'Tab') {
            if (e.shiftKey && document.activeElement === first) {
                e.preventDefault();
                last.focus();
            } else if (!e.shiftKey && document.activeElement === last) {
                e.preventDefault();
                first.focus();
            }
        }
    }

    document.addEventListener('keydown', function (e) {
        var lb = document.getElementById('lightbox');
        if (!lb || !lb.classList.contains('open')) { return; }
        if (e.key === 'Escape') { closeLightbox(); }
        else if (e.key === 'ArrowLeft') { prevImage(); }
        else if (e.key === 'ArrowRight') { nextImage(); }
        else { trapFocus(e); }
    });

    document.getElementById('lightbox').addEventListener('click', function (e) {
        if (e.target === this) { closeLightbox(); }
    });

    // Expose for inline onclick handlers
    window.openLightbox  = openLightbox;
    window.closeLightbox = closeLightbox;
    window.prevImage     = prevImage;
    window.nextImage     = nextImage;
}());
"""


def _generate_lightbox_grid(
    described_items: List[Tuple[str, object]],
    image_paths: Dict[str, str],
    title: str,
    include_metadata: bool,
    description_selection: str = 'newest',
) -> str:
    # Build JS data array
    js_entries = []
    for fp, item in described_items:
        rel = image_paths.get(fp, '')
        descs_html = _render_descriptions_html(
            _get_descriptions(item, description_selection), 'lb-desc-text'
        )
        js_entries.append(
            '{'
            f'src:{_js_str(rel)},'
            f'alt:{_js_str(_get_alt_text(fp))},'
            f'filename:{_js_str(Path(fp).name)},'
            f'desc:{_js_str(descs_html)},'
            f'meta:{_js_str(_get_metadata_html(item, include_metadata))}'
            '}'
        )
    js_data = 'var GALLERY = [\n' + ',\n'.join(js_entries) + '\n];'

    # Build thumbnail grid
    thumbs = []
    for i, (fp, item) in enumerate(described_items):
        rel = _esc(image_paths.get(fp, ''))
        alt = _esc(_get_alt_text(fp))
        aria = _esc(f'View {Path(fp).name}')
        thumbs.append(
            f'<li class="thumb-item">\n'
            f'  <button aria-label="{aria}" onclick="openLightbox({i}, this)">\n'
            f'    <img src="{rel}" alt="{alt}" loading="lazy">\n'
            f'  </button>\n'
            f'</li>'
        )
    thumbs_html = '\n'.join(thumbs)

    lightbox_html = (
        '<div id="lightbox" role="dialog" aria-modal="true" aria-label="Image viewer">\n'
        '  <div id="lightbox-dialog">\n'
        '    <div id="lightbox-toolbar">\n'
        '      <span id="lightbox-counter" aria-live="polite" aria-atomic="true"></span>\n'
        '      <div id="lightbox-nav" role="group" aria-label="Image navigation">\n'
        '        <button id="lb-prev" class="lb-btn" aria-label="Previous image"\n'
        '                onclick="prevImage()">&#8592;</button>\n'
        '        <button id="lb-next" class="lb-btn" aria-label="Next image"\n'
        '                onclick="nextImage()">&#8594;</button>\n'
        '        <button id="lb-close" class="lb-btn" aria-label="Close gallery viewer"\n'
        '                onclick="closeLightbox()">&#10005;</button>\n'
        '      </div>\n'
        '    </div>\n'
        '    <div id="lightbox-body">\n'
        '      <div id="lightbox-img-wrap">\n'
        '        <img id="lb-img" src="" alt="">\n'
        '      </div>\n'
        '      <div id="lightbox-caption-area" aria-live="polite" aria-atomic="true">\n'
        '        <h2 id="lb-filename"></h2>\n'
        '        <div id="lb-desc"></div>\n'
        '        <div id="lb-meta"></div>\n'
        '      </div>\n'
        '    </div>\n'
        '  </div>\n'
        '</div>\n'
    )

    return (
        _html_head(title, _LIGHTBOX_GRID_CSS)
        + '<ul class="thumb-grid" aria-label="Image gallery thumbnails">\n'
        + thumbs_html + '\n'
        + '</ul>\n'
        + lightbox_html
        + f'<script>\n{js_data}\n{_LIGHTBOX_JS}\n</script>\n'
        + _html_foot(_needs_osm(described_items))
    )


# ---------------------------------------------------------------------------
# Style: Simple List
# ---------------------------------------------------------------------------

_SIMPLE_LIST_CSS = """\
.image-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 3rem;
}
.image-entry {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    overflow: hidden;
}
.image-entry img {
    width: 100%;
    height: auto;
    max-height: 520px;
    object-fit: contain;
    background: #e9ecef;
    display: block;
}
.entry-body { padding: 1.5rem; }
.entry-title {
    font-size: 1.15rem;
    font-weight: 600;
    margin: 0 0 1rem 0;
    word-break: break-word;
    color: var(--color-text);
}
.entry-desc-heading {
    font-size: .875rem;
    font-weight: 700;
    color: var(--color-text-muted);
    margin: 0 0 .4rem 0;
    text-transform: uppercase;
    letter-spacing: .06em;
}
.entry-desc {
    font-size: 1rem;
    color: #343a40;
    line-height: 1.7;
    margin: 0;
    white-space: pre-wrap;
}
.entry-meta { margin-top: 1rem; }
"""


def _generate_simple_list(
    described_items: List[Tuple[str, object]],
    image_paths: Dict[str, str],
    title: str,
    include_metadata: bool,
    description_selection: str = 'newest',
) -> str:
    toc = _build_toc(described_items)
    entries = []
    for i, (fp, item) in enumerate(described_items):
        rel = _esc(image_paths.get(fp, ''))
        alt = _esc(_get_alt_text(fp))
        filename = _esc(Path(fp).name)
        descs_html = _render_descriptions_html(
            _get_descriptions(item, description_selection), 'entry-desc'
        )
        meta_html = _get_metadata_html(item, include_metadata)
        entries.append(
            f'<li>\n'
            f'  <article class="image-entry" id="img-{i}">\n'
            f'    <img src="{rel}" alt="{alt}" loading="lazy">\n'
            f'    <div class="entry-body">\n'
            f'      <h2 class="entry-title">{filename}</h2>\n'
            f'      <h3 class="entry-desc-heading">Description</h3>\n'
            f'      {descs_html}\n'
            f'      <div class="entry-meta">{meta_html}</div>\n'
            f'    </div>\n'
            f'  </article>\n'
            f'</li>'
        )
    entries_html = '\n'.join(entries)
    return (
        _html_head(title, _SIMPLE_LIST_CSS)
        + toc
        + '<ol class="image-list" aria-label="Image gallery">\n'
        + entries_html + '\n'
        + '</ol>\n'
        + _html_foot(_needs_osm(described_items))
    )
