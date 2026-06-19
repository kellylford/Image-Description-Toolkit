"""
Exporter — generates HTML reports and CSV files from project descriptions.

Output goes to <project>.idt/reports/.

HTML design priorities:
  - Screen reader first: logical heading hierarchy, skip-nav, landmark regions,
    every image has alt text that IS the AI description
  - Works without JavaScript or network access
  - Image src attributes use relative paths back to source directory
  - Readable by sighted users too: clean minimal CSS, high contrast

CSV: one row per image, suitable for spreadsheets and downstream scripts.
"""
from __future__ import annotations

import csv
import html as _html
from datetime import datetime, timezone
from pathlib import Path

from .project import Project

# ------------------------------------------------------------------ #
# HTML export                                                          #
# ------------------------------------------------------------------ #

_HTML_STYLE = """
:root {
  --bg: #ffffff;
  --fg: #1a1a1a;
  --accent: #0057b7;
  --border: #d0d0d0;
  --meta-fg: #555555;
  --max-width: 860px;
}
*, *::before, *::after { box-sizing: border-box; }
body {
  font-family: system-ui, -apple-system, sans-serif;
  font-size: 1.0625rem;
  line-height: 1.6;
  color: var(--fg);
  background: var(--bg);
  margin: 0;
  padding: 1rem;
}
.skip-link {
  position: absolute; top: -100%; left: 0;
  padding: 0.5rem 1rem;
  background: var(--accent); color: #fff;
  text-decoration: none;
  font-weight: bold;
}
.skip-link:focus { top: 0; }
header { max-width: var(--max-width); margin: 0 auto 2rem; }
h1 { font-size: 1.75rem; margin: 0 0 0.25rem; }
.meta { color: var(--meta-fg); font-size: 0.9375rem; margin: 0; }
nav { max-width: var(--max-width); margin: 0 auto 2rem; }
nav h2 { font-size: 1rem; margin: 0 0 0.5rem; }
nav ol { margin: 0; padding-left: 1.5rem; columns: 2; column-gap: 2rem; }
nav li { margin-bottom: 0.2rem; break-inside: avoid; }
nav a { color: var(--accent); }
main { max-width: var(--max-width); margin: 0 auto; }
article {
  border-top: 1px solid var(--border);
  padding: 2rem 0;
}
article:first-child { border-top: none; }
h2 { font-size: 1.2rem; margin: 0 0 1rem; word-break: break-all; }
figure { margin: 0 0 1.25rem; }
figure img {
  max-width: 100%;
  height: auto;
  display: block;
  border: 1px solid var(--border);
  border-radius: 4px;
}
figcaption {
  margin-top: 0.75rem;
  font-size: 0.9375rem;
  line-height: 1.65;
}
.image-meta {
  font-size: 0.875rem;
  color: var(--meta-fg);
  margin-top: 0.5rem;
}
.image-meta span + span::before { content: "  ·  "; }
footer {
  max-width: var(--max-width);
  margin: 3rem auto 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border);
  font-size: 0.875rem;
  color: var(--meta-fg);
}
@media (max-width: 600px) {
  nav ol { columns: 1; }
}
"""


def export_html(project: Project, filename: str = "descriptions.html") -> Path:
    """
    Generate an accessible HTML report for all described images.
    Returns the path to the created file.
    """
    reports_dir = project.idt_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    out_path = reports_dir / filename

    items = list(project.described())
    if not items:
        raise ValueError("No described images to export.")

    folder_name = project.source_dir.name
    generated = _format_datetime(datetime.now())
    n = len(items)
    models_used = sorted({i.active_description.model for i in items if i.active_description})

    lines: list[str] = []
    a = lines.append

    a("<!DOCTYPE html>")
    a('<html lang="en">')
    a("<head>")
    a('  <meta charset="utf-8">')
    a('  <meta name="viewport" content="width=device-width, initial-scale=1">')
    title_esc = _h(f"Image Descriptions — {folder_name}")
    a(f"  <title>{title_esc}</title>")
    a(f"  <style>{_HTML_STYLE}</style>")
    a("</head>")
    a("<body>")

    a('  <a href="#main-content" class="skip-link">Skip to image descriptions</a>')

    a("  <header>")
    a(f"    <h1>Image Descriptions: {_h(folder_name)}</h1>")
    model_str = ", ".join(models_used) if models_used else "unknown"
    a(f'    <p class="meta">Generated {_h(generated)} &nbsp;·&nbsp; '
      f'{n} image{"s" if n != 1 else ""} &nbsp;·&nbsp; {_h(model_str)}</p>')
    a("  </header>")

    # Navigation list
    a('  <nav aria-label="Image list">')
    a("    <h2>Images in this report</h2>")
    a("    <ol>")
    for i, item in enumerate(items, 1):
        slug = f"img-{i:04d}"
        a(f'      <li><a href="#{slug}">{_h(item.display_name)}</a></li>')
    a("    </ol>")
    a("  </nav>")

    a('  <main id="main-content">')

    for i, item in enumerate(items, 1):
        slug = f"img-{i:04d}"
        desc = item.active_description
        text = desc.text if desc else "(no description)"

        # Relative path from reports/ to the source image
        rel = item.source_path.relative_to(project.source_dir)
        img_src = Path("../..") / project.source_dir.name / rel
        # Use forward slashes for HTML
        img_src_str = img_src.as_posix()

        a(f'    <article id="{slug}">')
        a(f"      <h2>{_h(item.display_name)}</h2>")
        a("      <figure>")
        a(f'        <img src="{_h(img_src_str)}" alt="{_h(text)}" loading="lazy">')
        a(f"        <figcaption>{_h(text)}</figcaption>")
        a("      </figure>")

        if desc:
            date_str = desc.timestamp[:10]
            tokens_str = f"{desc.output_tokens} tokens" if desc.output_tokens else ""
            a('      <p class="image-meta">')
            a(f'        <span>Model: {_h(desc.model)}</span>')
            a(f'        <span>Prompt: {_h(desc.prompt_name)}</span>')
            a(f'        <span>Date: {date_str}</span>')
            if tokens_str:
                a(f'        <span>{tokens_str}</span>')
            a("      </p>")

        a("    </article>")

    a("  </main>")
    a("  <footer>")
    a(f"    <p>Generated by Image Description Toolkit &nbsp;·&nbsp; {_h(generated)}</p>")
    a("  </footer>")
    a("</body>")
    a("</html>")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


# ------------------------------------------------------------------ #
# CSV export                                                           #
# ------------------------------------------------------------------ #

def export_csv(project: Project, filename: str = "descriptions.csv") -> Path:
    """
    Generate a CSV of all described images.
    Returns the path to the created file.
    """
    reports_dir = project.idt_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    out_path = reports_dir / filename

    items = list(project.described())
    if not items:
        raise ValueError("No described images to export.")

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "file", "relative_path", "source_path",
            "description", "model", "provider",
            "prompt_name", "timestamp",
            "input_tokens", "output_tokens",
            "description_count",
        ])
        for item in items:
            desc = item.active_description
            rel = item.source_path.relative_to(project.source_dir)
            writer.writerow([
                item.display_name,
                str(rel),
                str(item.source_path),
                desc.text if desc else "",
                desc.model if desc else "",
                desc.provider if desc else "",
                desc.prompt_name if desc else "",
                desc.timestamp if desc else "",
                desc.input_tokens if desc else "",
                desc.output_tokens if desc else "",
                len(item.descriptions),
            ])

    return out_path


# ------------------------------------------------------------------ #
# Plain text export (accessibility-focused, pipe-friendly)            #
# ------------------------------------------------------------------ #

def export_txt(project: Project, filename: str = "descriptions.txt") -> Path:
    """
    Generate a plain text file: one block per image, easy for screen readers
    and downstream text processing.
    """
    reports_dir = project.idt_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    out_path = reports_dir / filename

    items = list(project.described())
    if not items:
        raise ValueError("No described images to export.")

    separator = "-" * 72
    blocks: list[str] = []
    for item in items:
        desc = item.active_description
        rel = item.source_path.relative_to(project.source_dir)
        block_lines = [
            separator,
            f"File: {rel}",
        ]
        if desc:
            block_lines += [
                f"Model: {desc.model}  ({desc.provider})",
                f"Date: {desc.timestamp[:10]}",
                "",
                desc.text,
            ]
        else:
            block_lines.append("(no description)")
        blocks.append("\n".join(block_lines))

    out_path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
    return out_path


# ------------------------------------------------------------------ #
# Helper                                                               #
# ------------------------------------------------------------------ #

def _h(text: str) -> str:
    """HTML-escape a string."""
    return _html.escape(str(text), quote=True)


def _format_datetime(dt: datetime) -> str:
    """Format a datetime as M/D/YYYY H:MMA/P — no leading zeros, cross-platform."""
    hour = dt.hour % 12 or 12
    ampm = "A" if dt.hour < 12 else "P"
    return f"{dt.month}/{dt.day}/{dt.year} {hour}:{dt.minute:02d}{ampm}"
