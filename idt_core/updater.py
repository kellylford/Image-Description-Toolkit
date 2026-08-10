"""In-app update check via the GitHub Releases API.

Reads the repository's releases, compares the newest ``v<semver>`` tag to the
running version and — when newer — hands the caller the download URL for this
platform's installer asset.

One update covers everything. Both the Windows installer and the macOS DMG carry
``idt`` and ``ImageDescriber`` together, so a user who updates from either app
gets both. Callers must say so in their user-facing text.

Platform behaviour differs on purpose:

* Windows — download ``ImageDescriptionToolkitSetup-<v>-windows.exe`` to temp and
  launch it. The caller exits immediately so Setup can replace the running
  executables.
* macOS — download ``IDT-<v>-macos-arm64.dmg`` to ~/Downloads and reveal it in
  Finder. A DMG cannot install itself over a running app, so the last step stays
  manual for now (see the macOS update-experience issue).

Only meaningful for a frozen (PyInstaller) build; running from source there is
nothing for an installer to replace, so callers gate the automatic check on
``is_frozen()``. A manual check still works from source and reports honestly by
sending the user to the releases page.

Set ``IDT_UPDATE_FEED`` to a URL (or a ``file://`` URL of a JSON fixture shaped
like the GitHub releases array) to test the flow without publishing a release.
"""

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

import requests

GITHUB_REPO = "kellylford/Image-Description-Toolkit"
DEFAULT_RELEASES_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases?per_page=30"
RELEASES_PAGE = f"https://github.com/{GITHUB_REPO}/releases/latest"

# Releases are tagged v<semver> (e.g. v4.5.0).
TAG_PREFIX = "v"



def current_version():
    """The running version, or None if it cannot be determined.

    Deliberately ``idt_core.__version__`` and not ``shared.wx_common.get_app_version()``:
    the latter hunts for the VERSION file on disk and falls back to "1.0.0" when
    it cannot find it, which would tell the user they are three major versions
    behind. ``__version__`` is compiled into both frozen binaries.

    Returns None rather than a low sentinel on failure. A sentinel like "0.0.0"
    would make every release look newer, so a user whose version lookup broke
    would be nagged to reinstall on every single launch, forever. Not knowing our
    own version is a reason to stay quiet, not a reason to always fire.
    """
    try:
        from idt_core import __version__
        return __version__ or None
    except Exception:
        return None


def _headers() -> dict:
    return {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"IDT/{current_version() or 'unknown'}",
    }


def releases_url() -> str:
    """The feed to read. IDT_UPDATE_FEED overrides it for testing."""
    return os.environ.get("IDT_UPDATE_FEED") or DEFAULT_RELEASES_URL


def is_frozen() -> bool:
    """True when running from the PyInstaller build rather than from source."""
    return getattr(sys, "frozen", False)


def _version_tuple(v):
    return tuple(int(x) for x in re.findall(r"\d+", v or "")) or (0,)


def is_newer(latest, current) -> bool:
    """True if `latest` is a higher version than `current`."""
    a, b = _version_tuple(latest), _version_tuple(current)
    n = max(len(a), len(b))
    a += (0,) * (n - len(a))  # zero-pad so 4.5 and 4.5.0 compare equal
    b += (0,) * (n - len(b))
    return a > b


def _release_version(tag):
    """Return the version from a `v<numeric semver>` tag, else None.

    The remainder must be purely numeric dotted digits. Merely requiring a digit
    after the `v` is not enough here: this repo's history contains `v4beta2` and
    `v4.0.0Beta3`, which would otherwise parse as releases 4.2 and 4.0.0.3. A
    stable-channel checker should not offer a beta at all.
    """
    if tag and tag.startswith(TAG_PREFIX):
        rest = tag[len(TAG_PREFIX):]
        if re.fullmatch(r"\d+(?:\.\d+)*", rest):
            return rest
    return None


def _asset_url(release, predicate):
    for asset in release.get("assets") or []:
        name = (asset.get("name") or "").lower()
        if predicate(name):
            return asset.get("browser_download_url")
    return None


def checksums_for(release):
    """URL of the release's SHA256SUMS.txt, or None (see release.yml)."""
    return _asset_url(release, lambda n: n == "sha256sums.txt")


def asset_for_platform(release):
    """URL of this platform's installer asset in `release`, or None.

    Returning None matters: it lets the caller fall back to opening the releases
    page rather than offering a Windows user a .dmg. Matching is by shape rather
    than exact name so a locally built `ImageDescriptionToolkitSetup_4.5.0.exe`
    is recognised alongside CI's `ImageDescriptionToolkitSetup-4.5.0-windows.exe`.
    """
    for asset in release.get("assets") or []:
        name = (asset.get("name") or "").lower()
        if sys.platform == "darwin":
            if name.startswith("idt-") and name.endswith(".dmg"):
                return asset.get("browser_download_url")
        elif sys.platform.startswith("win"):
            if name.startswith("imagedescriptiontoolkitsetup") and name.endswith(".exe"):
                return asset.get("browser_download_url")
    return None


def _fetch_releases():
    """The releases array. Reads a file:// URL directly so a local fixture works."""
    url = releases_url()
    if url.startswith("file://"):
        path = url2pathname(urlparse(url).path)
        return json.loads(Path(path).read_text(encoding="utf-8")) or []
    resp = requests.get(url, headers=_headers(), timeout=15)
    resp.raise_for_status()
    return resp.json() or []


def check_for_update(current=None):
    """Return details of the newest release if it is newer than the running one.

    Returns ``{'version', 'url', 'notes', 'page_url'}`` — where ``url`` is None
    when the release has no asset for this platform — or None when already up to
    date.

    Raises on network/API failure so a manual check can report "couldn't check"
    rather than silently claiming the app is up to date.
    """
    current = current or current_version()
    if not current:
        # We do not know what we are running; anything we said would be a guess.
        return None
    releases = _fetch_releases()

    best, best_ver = None, None
    for r in releases:
        if r.get("draft") or r.get("prerelease"):
            continue
        ver = _release_version(r.get("tag_name") or "")
        if not ver:
            continue
        if best is None or _version_tuple(ver) > _version_tuple(best_ver):
            best, best_ver = r, ver

    if best is None or not is_newer(best_ver, current):
        return None

    return {
        "version": best_ver,
        "url": asset_for_platform(best),
        "checksums_url": checksums_for(best),
        "notes": best.get("body") or "",
        "page_url": best.get("html_url") or RELEASES_PAGE,
    }


def download_dir() -> Path:
    """Where the downloaded asset lands.

    Windows puts the installer in temp — it runs once and is never seen again.
    macOS puts the DMG in ~/Downloads, because the user has to open it by hand.
    """
    if sys.platform == "darwin":
        target = Path.home() / "Downloads"
        if target.is_dir():
            return target
    return Path(tempfile.gettempdir())


def _validate_download_url(url):
    """Refuse to download anything that is not an HTTPS GitHub release asset.

    We hand the result to os.startfile, so this is the one place to be strict.
    IDT_UPDATE_FEED lets a feed be redirected for testing; without this check
    that would also be a way to make IDT fetch and run an arbitrary binary.
    """
    parts = urlparse(url or "")
    host = (parts.hostname or "").lower()
    if parts.scheme != "https" or not (
        host == "github.com" or host.endswith(".github.com")
        or host.endswith(".githubusercontent.com")
    ):
        raise ValueError(f"Refusing to download update from untrusted URL: {url}")
    return url


def expected_sha256(checksums_url, filename):
    """Look up `filename` in a SHA256SUMS.txt, or None if absent/unreadable."""
    if not checksums_url:
        return None
    try:
        resp = requests.get(_validate_download_url(checksums_url),
                            headers=_headers(), timeout=(10, 30))
        resp.raise_for_status()
        for line in resp.text.splitlines():
            parts = line.split()
            # "<hex>  <name>" — the name may carry a leading * for binary mode.
            if len(parts) >= 2 and parts[-1].lstrip("*") == filename:
                return parts[0].lower()
    except Exception:
        return None
    return None


def download_asset(url, progress=None, should_cancel=None, checksums_url=None):
    """Download `url` and return the local path, or None if cancelled.

    ``progress`` (optional) is called with (downloaded_bytes, total_bytes); total
    is 0 when the server sends no Content-Length, which callers should render as
    an indeterminate bar rather than a percentage that lies.
    ``should_cancel`` (optional) is polled between chunks; when it returns True
    the partial file is deleted and None is returned.
    ``checksums_url`` (optional) points at the release's SHA256SUMS.txt; when the
    file is listed there the download must match or a ValueError is raised and
    the file is deleted. We are about to execute this thing.

    Any failure removes the partial file rather than leaving a half-downloaded
    installer sitting in temp for someone to run later.
    """
    _validate_download_url(url)
    name = os.path.basename(urlparse(url).path) or "IDT-Update"
    path = download_dir() / name
    digest = hashlib.sha256()
    done = 0
    try:
        # (connect, read) — a stalled server must not hold the UI for minutes.
        with requests.get(url, stream=True, timeout=(15, 60)) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("Content-Length") or 0)
            with open(path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    if should_cancel and should_cancel():
                        raise _Cancelled()
                    if chunk:
                        f.write(chunk)
                        digest.update(chunk)
                        done += len(chunk)
                        if progress:
                            progress(done, total)

        want = expected_sha256(checksums_url, name)
        if want and digest.hexdigest().lower() != want:
            raise ValueError(
                f"Downloaded {name} does not match the published checksum. "
                "The file was discarded; try again, or download it from the "
                "releases page."
            )
    except _Cancelled:
        _remove_quietly(path)
        return None
    except BaseException:
        _remove_quietly(path)
        raise
    return str(path)


class _Cancelled(Exception):
    """Internal: the user aborted the download."""


def _remove_quietly(path):
    try:
        os.remove(path)
    except OSError:
        # Already gone, or locked by a scanner. This only ever runs on a path we
        # are abandoning anyway, so a leftover temp file is not worth surfacing.
        pass


def launch_installer(path) -> bool:
    """Hand the downloaded file off to the OS.

    Windows starts the installer. The caller must ALREADY have closed the app —
    Setup replaces the running executables, and starting it while a save prompt
    is still on screen leaves the two racing. macOS reveals the DMG in Finder and
    the app keeps running; mounting and copying over a running .app is the
    user's move.

    Returns True on the platforms where an installer was actually started.
    """
    if sys.platform == "darwin":
        subprocess.run(["open", "-R", str(path)], check=False)
        return False
    os.startfile(str(path))  # noqa: S606 - a file this process just downloaded
    return True
