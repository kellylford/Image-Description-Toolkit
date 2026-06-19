"""
Web image downloader for idt_core.

Downloads images from a URL into the .idt/downloads/ directory of a project,
capturing alt text alongside each image so the describer can use it as context.

Requires: pip install requests beautifulsoup4

Usage:
    dl = Downloader(project)
    result = dl.download("https://www.nytimes.com/", max_images=20)
    # result.download_dir is now a directory of images ready to describe
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Callable, Iterator, Optional
from urllib.parse import urljoin, urlparse

from .project import Project

_IMAGE_EXTENSIONS = frozenset(
    {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif"}
)

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


@dataclass
class DownloadResult:
    download_dir: Path              # where images landed (.idt/downloads/<subfolder>/)
    downloaded: int = 0
    skipped: int = 0                # duplicates or size-filtered
    failed: int = 0
    alt_texts: dict = field(default_factory=dict)   # filename → alt text


class Downloader:
    """
    Download images from a URL into a project's .idt/downloads/ directory.
    Each download run gets its own timestamped subfolder.
    """

    def __init__(
        self,
        project: Project,
        min_width: int = 0,
        min_height: int = 0,
        timeout: int = 30,
        on_progress: Optional[Callable[[int, int, str], None]] = None,
    ):
        self.project = project
        self.min_width = min_width
        self.min_height = min_height
        self.timeout = timeout
        self.on_progress = on_progress

    def download(
        self,
        url: str,
        max_images: Optional[int] = None,
    ) -> DownloadResult:
        """
        Download images from url into .idt/downloads/.

        Returns a DownloadResult whose .download_dir can be opened as a
        new Project (or passed to Pipeline directly) for description.
        """
        try:
            import requests
        except ImportError:
            raise ImportError("requests is required: pip install requests")
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            raise ImportError("beautifulsoup4 is required: pip install beautifulsoup4")
        try:
            from PIL import Image as _PILImage
        except ImportError:
            raise ImportError("Pillow is required: pip install Pillow")

        session = requests.Session()
        session.headers["User-Agent"] = _UA

        resp = session.get(url, timeout=self.timeout)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        subfolder_name = _subfolder_name(url, soup)
        dl_dir = self.project.idt_dir / "downloads" / subfolder_name
        dl_dir.mkdir(parents=True, exist_ok=True)

        entries = _extract_image_entries(resp.text, url)
        total = len(entries)

        result = DownloadResult(download_dir=dl_dir)
        seen_hashes: set = set()

        for i, (img_url, alt) in enumerate(entries, 1):
            if max_images and result.downloaded >= max_images:
                break
            if self.on_progress:
                self.on_progress(i, total, img_url[:60])

            path = _download_one(
                session, img_url, i, dl_dir, seen_hashes,
                self.min_width, self.min_height, self.timeout, _PILImage
            )
            if path is None:
                result.skipped += 1
                continue
            result.downloaded += 1
            if alt:
                result.alt_texts[path.name] = alt
            # Small delay to be respectful
            if i < total:
                time.sleep(0.3)

        # Persist alt text mapping alongside images
        if result.alt_texts:
            alt_file = dl_dir / "alt_text_mapping.json"
            alt_file.write_text(
                json.dumps(result.alt_texts, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

        return result


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def _extract_image_entries(html: str, base_url: str) -> list[tuple[str, str]]:
    """Return (absolute_url, alt_text) for all images found in html."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    seen: set = set()
    entries: list[tuple[str, str]] = []

    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
        if src:
            abs_url = urljoin(base_url, src)
            if _is_image_url(abs_url) and abs_url not in seen:
                seen.add(abs_url)
                entries.append((abs_url, (img.get("alt") or "").strip()))

    for picture in soup.find_all("picture"):
        for source in picture.find_all("source"):
            srcset = source.get("srcset", "")
            for part in srcset.split(","):
                u = part.strip().split()[0]
                abs_url = urljoin(base_url, u)
                if _is_image_url(abs_url) and abs_url not in seen:
                    seen.add(abs_url)
                    entries.append((abs_url, ""))

    for a in soup.find_all("a", href=True):
        abs_url = urljoin(base_url, a["href"])
        if _is_image_url(abs_url) and abs_url not in seen:
            seen.add(abs_url)
            entries.append((abs_url, ""))

    return entries


def _is_image_url(url: str) -> bool:
    return Path(urlparse(url.lower()).path).suffix in _IMAGE_EXTENSIONS


def _subfolder_name(url: str, soup) -> str:
    parsed = urlparse(url)
    domain = re.sub(r"^www\.", "", parsed.netloc).split(":")[0]
    domain = re.sub(r"[^\w.\-]", "_", domain).strip("_")
    title_tag = soup.find("title")
    title = ""
    if title_tag:
        t = re.sub(r"\s+", " ", title_tag.get_text(separator=" ")).strip()
        if len(t) > 60:
            last_space = t[:60].rfind(" ")
            t = t[:last_space] if last_space > 0 else t[:60]
        safe = re.sub(r"[^\w\s\-]", " ", t).strip()
        safe = re.sub(r"\s+", "_", safe)
        if safe:
            title = f" - {safe}"
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{domain}{title} - {ts}"


def _download_one(
    session, img_url: str, index: int, out_dir: Path,
    seen_hashes: set, min_w: int, min_h: int, timeout: int, PILImage
) -> Optional[Path]:
    try:
        resp = session.get(img_url, timeout=timeout, stream=True)
        resp.raise_for_status()
        data = resp.content

        img_hash = hashlib.md5(data).hexdigest()
        if img_hash in seen_hashes:
            return None
        seen_hashes.add(img_hash)

        img = PILImage.open(BytesIO(data))
        w, h = img.size
        if min_w and w < min_w:
            return None
        if min_h and h < min_h:
            return None

        filename = Path(urlparse(img_url).path).name or f"image_{index:04d}.jpg"
        filename = re.sub(r"[^\w.\-]", "_", filename)
        if not any(filename.lower().endswith(ext) for ext in _IMAGE_EXTENSIONS):
            filename = f"image_{index:04d}.jpg"

        dest = out_dir / filename
        counter = 1
        while dest.exists():
            stem, sfx = dest.stem, dest.suffix
            dest = out_dir / f"{stem}_{counter}{sfx}"
            counter += 1

        dest.write_bytes(data)
        return dest

    except Exception:
        return None
