"""
Web image downloader for idt_core.

Downloads images from a URL into a .idtw workspace's derived/downloads/ directory,
capturing alt text alongside each image so the describer can use it as context.

Requires: pip install requests beautifulsoup4
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

_IMAGE_EXTENSIONS = frozenset(
    {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif"}
)

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def normalize_url(url: str) -> str:
    """
    Accept bare domains like 'www.nytimes.com' by defaulting to https://.

    requests raises 'No scheme supplied' for a URL with no scheme, so we
    prepend https:// when the user didn't type one. A leading '//' is treated
    as scheme-relative and also gets https.
    """
    url = (url or "").strip()
    if not url:
        return url
    parsed = urlparse(url)
    if not parsed.scheme:
        return "https://" + url.lstrip("/")
    return url


@dataclass
class WorkspaceDownloadResult:
    workspace: object                # the Workspace images were added to
    subfolder: str                   # bundle-relative subfolder, e.g. "downloads/<site> - <title> - <ts>"
    downloaded: int = 0
    skipped: int = 0
    failed: int = 0
    items: list = field(default_factory=list)   # list[WorkspaceItem], in download order


def download_into_workspace(
    workspace,
    url: str,
    min_width: int = 0,
    min_height: int = 0,
    timeout: int = 30,
    max_images: Optional[int] = None,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
) -> WorkspaceDownloadResult:
    """
    Download images from url straight into workspace's derived/downloads/ folder
    and register each as a WorkspaceItem (item_type="downloaded_image"), so the
    workspace's own describe pipeline can pick them up like any other image.
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

    from datetime import datetime, timezone

    url = normalize_url(url)

    session = requests.Session()
    session.headers["User-Agent"] = _UA

    resp = session.get(url, timeout=timeout)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    subfolder_name = _subfolder_name(url, soup)
    bundle_subfolder = f"downloads/{subfolder_name}"
    dl_dir = workspace.derived_dir("downloads") / subfolder_name
    dl_dir.mkdir(parents=True, exist_ok=True)

    entries = _extract_image_entries(resp.text, url)
    total = len(entries)

    result = WorkspaceDownloadResult(workspace=workspace, subfolder=bundle_subfolder)
    seen_hashes: set = set()
    now = datetime.now(timezone.utc).isoformat()

    for i, (img_url, alt) in enumerate(entries, 1):
        if max_images and result.downloaded >= max_images:
            break
        if on_progress:
            on_progress(i, total, img_url[:60])

        path = _download_one(
            session, img_url, i, dl_dir, seen_hashes,
            min_width, min_height, timeout, _PILImage
        )
        if path is None:
            result.skipped += 1
            continue
        result.downloaded += 1

        # copy=False: the file already lives in the bundle's derived/downloads/
        # folder, so reference it there rather than duplicating it into images/.
        item = workspace.add_image(path, subfolder=bundle_subfolder, copy=False)
        item.item_type = "downloaded_image"
        item.download_url = img_url
        item.download_timestamp = now
        item.alt_text = alt.strip() if alt else None
        workspace.save_item(item)
        result.items.append(item)

        if i < total:
            time.sleep(0.3)

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
                tokens = part.strip().split()
                if not tokens:
                    continue
                u = tokens[0]
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


def domain_name(url: str) -> str:
    """Filesystem-safe bare domain for a URL, e.g. 'www.nytimes.com' -> 'nytimes.com'."""
    parsed = urlparse(url)
    domain = re.sub(r"^www\.", "", parsed.netloc).split(":")[0]
    return re.sub(r"[^\w.\-]", "_", domain).strip("_")


def _subfolder_name(url: str, soup) -> str:
    domain = domain_name(url)
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


# ---------------------------------------------------------------------------
# WebImageDownloader — standalone URL scraper used by the ImageDescriber GUI
# ---------------------------------------------------------------------------

class WebImageDownloader:
    """Download images from a web page into a timestamped subdirectory.

    Unlike Downloader (which writes into a Project), this class is standalone
    and is used by the ImageDescriber GUI's URL-download workflow.
    """

    _IMAGE_EXTS = frozenset(
        {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif"}
    )

    def __init__(
        self,
        url: str,
        output_dir: Path,
        min_width: int = 0,
        min_height: int = 0,
        max_images: Optional[int] = None,
        user_agent: Optional[str] = None,
        timeout: int = 30,
        verbose: bool = False,
        progress_callback: Optional[Callable] = None,
    ) -> None:
        import logging
        self.url = url
        self.output_dir = Path(output_dir)
        self.min_width = min_width
        self.min_height = min_height
        self.max_images = max_images
        self.timeout = timeout
        self.verbose = verbose
        self.progress_callback = progress_callback
        self.actual_output_dir = self.output_dir
        self._seen_hashes: set = set()
        self.logger = logging.getLogger(__name__)

        import requests
        self._session = requests.Session()
        ua = user_agent or _UA
        self._session.headers["User-Agent"] = ua

    def download(self) -> tuple[int, int]:
        """Fetch images from self.url. Returns (downloaded, failed)."""
        import json as _json
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            raise ImportError("beautifulsoup4 is required: pip install beautifulsoup4")
        try:
            from PIL import Image as _PILImage
        except ImportError:
            raise ImportError("Pillow is required: pip install Pillow")

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.actual_output_dir = self.output_dir

        try:
            resp = self._session.get(self.url, timeout=self.timeout)
            resp.raise_for_status()
        except Exception as exc:
            self.logger.error(f"Failed to fetch {self.url}: {exc}")
            return 0, 0

        soup = BeautifulSoup(resp.text, "html.parser")
        page_title = self._page_title(soup)
        subfolder = self._subfolder_name(self.url, page_title)
        self.actual_output_dir = self.output_dir / subfolder
        self.actual_output_dir.mkdir(parents=True, exist_ok=True)

        entries = self._extract_image_urls(resp.text)
        url_map: dict = {}
        alt_map: dict = {}
        ok = fail = 0

        for i, (img_url, alt) in enumerate(entries, 1):
            if self.max_images and ok >= self.max_images:
                break
            if self.progress_callback:
                try:
                    self.progress_callback(i - 1, len(entries),
                                           f"Downloading {i}/{len(entries)}: {img_url[:60]}...")
                except Exception:
                    pass

            dest = _download_one(
                self._session, img_url, i, self.actual_output_dir,
                self._seen_hashes, self.min_width, self.min_height,
                self.timeout, _PILImage,
            )
            if dest:
                ok += 1
                url_map[dest.name] = img_url
                if alt:
                    alt_map[dest.name] = alt
            else:
                fail += 1

            if self.progress_callback:
                try:
                    self.progress_callback(i, len(entries),
                                           f"Downloaded {ok}, skipped {fail}")
                except Exception:
                    pass
            if i < len(entries):
                time.sleep(0.5)

        if url_map:
            try:
                (self.actual_output_dir / "url_mapping.json").write_text(
                    _json.dumps(url_map, indent=2, ensure_ascii=False), encoding="utf-8"
                )
            except Exception:
                pass
        if alt_map:
            try:
                (self.actual_output_dir / "alt_text_mapping.json").write_text(
                    _json.dumps(alt_map, indent=2, ensure_ascii=False), encoding="utf-8"
                )
            except Exception:
                pass

        return ok, fail

    def _page_title(self, soup) -> Optional[str]:
        tag = soup.find("title")
        if not tag:
            return None
        title = re.sub(r"\s+", " ", tag.get_text(separator=" ")).strip()
        if not title:
            return None
        if len(title) > 60:
            cut = title[:60]
            sp = cut.rfind(" ")
            title = cut[:sp] if sp > 0 else cut
        return title

    def _subfolder_name(self, url: str, title: Optional[str]) -> str:
        import time as _time
        from datetime import datetime as _dt
        parsed = urlparse(url)
        netloc = parsed.netloc or parsed.path
        domain = re.sub(r"^www\.", "", netloc).split(":")[0]
        domain = re.sub(r"[^\w.\-]", "_", domain).strip("_")
        ts = _dt.now().strftime("%Y%m%d_%H%M%S")
        if title:
            safe = re.sub(r"[^\w\s\-]", " ", title)
            safe = re.sub(r"\s+", " ", safe).strip()
            if safe:
                return f"{domain} - {safe} - {ts}"
        return f"{domain} - {ts}"

    def _extract_image_urls(self, html: str) -> list[tuple[str, str]]:
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return []
        soup = BeautifulSoup(html, "html.parser")
        seen: set = set()
        result: list = []

        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
            if src:
                abs_url = urljoin(self.url, src)
                if self._is_img(abs_url) and abs_url not in seen:
                    seen.add(abs_url)
                    result.append((abs_url, (img.get("alt") or "").strip()))

        for picture in soup.find_all("picture"):
            for source in picture.find_all("source"):
                srcset = source.get("srcset", "")
                for part in srcset.split(","):
                    url = part.strip().split()[0] if part.strip() else ""
                    if url:
                        abs_url = urljoin(self.url, url)
                        if self._is_img(abs_url) and abs_url not in seen:
                            seen.add(abs_url)
                            result.append((abs_url, ""))

        for a in soup.find_all("a"):
            href = a.get("href", "")
            if href and self._is_img(href):
                abs_url = urljoin(self.url, href)
                if abs_url not in seen:
                    seen.add(abs_url)
                    result.append((abs_url, ""))

        return result

    def _is_img(self, url: str) -> bool:
        return any(urlparse(url.lower()).path.endswith(ext)
                   for ext in self._IMAGE_EXTS)
