"""Unit tests for idt_core.updater — the in-app update check.

Mirrors the coverage Scores/tests/unit/test_updater.py has for the same logic.
Nothing here touches the network: _fetch_releases is patched, or a file:// feed
fixture is used.
"""

import hashlib
import json
import sys
from pathlib import Path

import pytest

from idt_core import updater

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------- #
# Version comparison                                                #
# ---------------------------------------------------------------- #

@pytest.mark.parametrize("latest,current,expected", [
    ("4.5.1", "4.5.0", True),
    ("4.6.0", "4.5.9", True),
    ("5.0.0", "4.9.9", True),
    ("4.5.0", "4.5.0", False),
    ("4.5.0", "4.5.1", False),
    ("4.4.9", "4.5.0", False),
    # Zero-pad: 4.5 and 4.5.0 are the same version.
    ("4.5", "4.5.0", False),
    ("4.5.0", "4.5", False),
    ("4.5.1", "4.5", True),
    # Numeric, not lexicographic: 4.10 is above 4.9.
    ("4.10.0", "4.9.0", True),
])
def test_is_newer(latest, current, expected):
    assert updater.is_newer(latest, current) is expected


def test_is_newer_handles_unparseable_current():
    """A missing/garbage current version must not crash the check."""
    assert updater.is_newer("4.5.0", "") is True


# ---------------------------------------------------------------- #
# Tag parsing                                                       #
# ---------------------------------------------------------------- #

@pytest.mark.parametrize("tag,expected", [
    ("v4.5.0", "4.5.0"),
    ("v10.0.1", "10.0.1"),
    ("v5", "5"),
    # The remainder must be purely numeric, so none of these are stable releases.
    ("v4beta2", None),        # this repo's own old tag style
    ("v4.0.0Beta3", None),    # ditto — must not parse as 4.0.0.3
    ("v4.5.0-rc1", None),
    ("viewer-fix", None),
    ("4.5.0", None),          # no prefix
    ("", None),
    (None, None),
])
def test_release_version(tag, expected):
    assert updater._release_version(tag) == expected


# ---------------------------------------------------------------- #
# Asset selection                                                   #
# ---------------------------------------------------------------- #

def _release(*asset_names, tag="v4.9.0", **kw):
    rel = {
        "tag_name": tag,
        "body": "Notes.",
        "html_url": f"https://github.com/kellylford/Image-Description-Toolkit/releases/tag/{tag}",
        "assets": [
            {"name": n, "browser_download_url": f"https://example.invalid/{n}"}
            for n in asset_names
        ],
    }
    rel.update(kw)
    return rel


WIN_ASSET = "ImageDescriptionToolkitSetup-4.9.0-windows.exe"
MAC_ASSET = "IDT-4.9.0-macos-arm64.dmg"
OTHER_ASSETS = ["idt-4.9.0-windows-x64.exe", "ImageDescriber-4.9.0-windows-x64.exe",
                "idt-4.9.0-macos-arm64.tar.gz", "SHA256SUMS.txt"]


def test_asset_picks_windows_installer(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    url = updater.asset_for_platform(_release(*OTHER_ASSETS, WIN_ASSET, MAC_ASSET))
    assert url.endswith(WIN_ASSET)


def test_asset_picks_macos_dmg(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    url = updater.asset_for_platform(_release(*OTHER_ASSETS, WIN_ASSET, MAC_ASSET))
    assert url.endswith(MAC_ASSET)


def test_asset_accepts_locally_built_installer_name(monkeypatch):
    """builditall_wx.bat produces an underscore name; CI produces a hyphen one."""
    monkeypatch.setattr(sys, "platform", "win32")
    url = updater.asset_for_platform(_release("ImageDescriptionToolkitSetup_4.9.0.exe"))
    assert url.endswith("ImageDescriptionToolkitSetup_4.9.0.exe")


def test_asset_none_when_only_other_platform(monkeypatch):
    """Never offer a Windows user a .dmg — the caller falls back to the web page."""
    monkeypatch.setattr(sys, "platform", "win32")
    assert updater.asset_for_platform(_release(MAC_ASSET, *OTHER_ASSETS)) is None

    monkeypatch.setattr(sys, "platform", "darwin")
    assert updater.asset_for_platform(_release(WIN_ASSET, *OTHER_ASSETS)) is None


def test_asset_none_when_no_assets(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    assert updater.asset_for_platform({"tag_name": "v4.9.0"}) is None


# ---------------------------------------------------------------- #
# check_for_update                                                  #
# ---------------------------------------------------------------- #

@pytest.fixture
def feed(monkeypatch):
    """Replace the network fetch with a list the test controls."""
    releases = []

    def _fetch():
        return releases

    monkeypatch.setattr(updater, "_fetch_releases", _fetch)
    monkeypatch.setattr(sys, "platform", "win32")
    return releases


def test_finds_newer_release(feed):
    feed.append(_release(WIN_ASSET, tag="v4.9.0"))
    info = updater.check_for_update(current="4.5.0")
    assert info["version"] == "4.9.0"
    assert info["url"].endswith(WIN_ASSET)
    assert info["notes"] == "Notes."
    assert info["page_url"].endswith("v4.9.0")


def test_none_when_up_to_date(feed):
    feed.append(_release(WIN_ASSET, tag="v4.5.0"))
    assert updater.check_for_update(current="4.5.0") is None


def test_none_when_running_ahead_of_latest(feed):
    """A dev build past the last release must not be told to downgrade."""
    feed.append(_release(WIN_ASSET, tag="v4.5.0"))
    assert updater.check_for_update(current="4.6.0") is None


def test_skips_drafts_and_prereleases(feed):
    feed.extend([
        _release(WIN_ASSET, tag="v4.9.0", draft=True),
        _release(WIN_ASSET, tag="v4.8.0", prerelease=True),
        _release(WIN_ASSET, tag="v4.7.0"),
    ])
    info = updater.check_for_update(current="4.5.0")
    assert info["version"] == "4.7.0"


def test_skips_non_release_tags(feed):
    feed.extend([
        _release(WIN_ASSET, tag="v4beta2"),
        _release(WIN_ASSET, tag="viewer-fix"),
        _release(WIN_ASSET, tag="v4.6.0"),
    ])
    info = updater.check_for_update(current="4.5.0")
    assert info["version"] == "4.6.0"


def test_picks_highest_not_first(feed):
    """GitHub's ordering is not guaranteed to put the highest version first."""
    feed.extend([
        _release(WIN_ASSET, tag="v4.6.0"),
        _release(WIN_ASSET, tag="v4.10.0"),
        _release(WIN_ASSET, tag="v4.9.0"),
    ])
    assert updater.check_for_update(current="4.5.0")["version"] == "4.10.0"


def test_url_is_none_when_platform_asset_missing(feed):
    """Still reports the update — the caller sends the user to the web page."""
    feed.append(_release(MAC_ASSET, tag="v4.9.0"))
    info = updater.check_for_update(current="4.5.0")
    assert info["version"] == "4.9.0"
    assert info["url"] is None


def test_none_when_feed_empty(feed):
    assert updater.check_for_update(current="4.5.0") is None


def test_network_failure_propagates(monkeypatch):
    """Must raise, so a manual check says 'couldn't check' rather than 'up to date'."""
    def _boom():
        raise ConnectionError("no route to host")

    monkeypatch.setattr(updater, "_fetch_releases", _boom)
    with pytest.raises(ConnectionError):
        updater.check_for_update(current="4.5.0")


# ---------------------------------------------------------------- #
# Feed override                                                     #
# ---------------------------------------------------------------- #

def test_releases_url_default(monkeypatch):
    monkeypatch.delenv("IDT_UPDATE_FEED", raising=False)
    assert updater.releases_url() == updater.DEFAULT_RELEASES_URL


def test_file_feed_override(tmp_path, monkeypatch):
    """IDT_UPDATE_FEED with a file:// URL drives the whole flow offline."""
    monkeypatch.setattr(sys, "platform", "win32")
    fixture = tmp_path / "releases.json"
    fixture.write_text(json.dumps([_release(WIN_ASSET, tag="v4.9.0")]), encoding="utf-8")
    monkeypatch.setenv("IDT_UPDATE_FEED", fixture.as_uri())

    info = updater.check_for_update(current="4.5.0")
    assert info["version"] == "4.9.0"


# ---------------------------------------------------------------- #
# Version source                                                    #
# ---------------------------------------------------------------- #

def test_current_version_matches_package():
    """The checker must compare against idt_core.__version__, not a file lookup."""
    from idt_core import __version__
    assert updater.current_version() == __version__
    assert updater.current_version() != "1.0.0"  # wx_common's bad fallback


def test_unknown_current_version_suppresses_check(feed, monkeypatch):
    """Not knowing our version must stay quiet, not report a phantom update.

    A "0.0.0" style fallback would make every release look newer, nagging the
    user to reinstall on every launch forever.
    """
    feed.append(_release(WIN_ASSET, tag="v4.9.0"))
    monkeypatch.setattr(updater, "current_version", lambda: None)
    assert updater.check_for_update() is None


# ---------------------------------------------------------------- #
# Download URL trust                                                #
# ---------------------------------------------------------------- #

@pytest.mark.parametrize("url", [
    "https://github.com/kellylford/Image-Description-Toolkit/releases/download/v1/a.exe",
    "https://objects.githubusercontent.com/x/a.exe",
    "https://github-releases.githubusercontent.com/x/a.dmg",
])
def test_download_url_allowed(url):
    assert updater._validate_download_url(url) == url


@pytest.mark.parametrize("url", [
    "http://github.com/x/a.exe",             # not https
    "https://evil.invalid/a.exe",
    "https://github.com.evil.invalid/a.exe",  # suffix trick
    "https://notgithub.com/a.exe",
    "file:///C:/Windows/System32/calc.exe",
    "",
    None,
])
def test_download_url_rejected(url):
    """IDT_UPDATE_FEED must not become a way to fetch and run an arbitrary binary."""
    with pytest.raises(ValueError):
        updater._validate_download_url(url)


# ---------------------------------------------------------------- #
# Checksums                                                         #
# ---------------------------------------------------------------- #

def test_checksums_for_finds_asset():
    rel = _release(WIN_ASSET, "SHA256SUMS.txt")
    assert updater.checksums_for(rel).endswith("SHA256SUMS.txt")


def test_checksums_for_absent():
    assert updater.checksums_for(_release(WIN_ASSET)) is None


def test_check_for_update_exposes_checksums(feed):
    feed.append(_release(WIN_ASSET, "SHA256SUMS.txt", tag="v4.9.0"))
    info = updater.check_for_update(current="4.5.0")
    assert info["checksums_url"].endswith("SHA256SUMS.txt")


class _Resp:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        pass


def test_expected_sha256_parses(monkeypatch):
    body = (
        "aaaa1111  ImageDescriber-4.9.0-windows-x64.exe\n"
        "bbbb2222  ImageDescriptionToolkitSetup-4.9.0-windows.exe\n"
        "cccc3333 *IDT-4.9.0-macos-arm64.dmg\n"
    )
    monkeypatch.setattr(updater.requests, "get", lambda *a, **k: _Resp(body))
    url = "https://github.com/x/SHA256SUMS.txt"
    assert updater.expected_sha256(url, "ImageDescriptionToolkitSetup-4.9.0-windows.exe") == "bbbb2222"
    # sha256sum's binary-mode "*" prefix must not defeat the match.
    assert updater.expected_sha256(url, "IDT-4.9.0-macos-arm64.dmg") == "cccc3333"
    assert updater.expected_sha256(url, "not-listed.exe") is None


def test_expected_sha256_none_without_url():
    assert updater.expected_sha256(None, "anything.exe") is None


# ---------------------------------------------------------------- #
# download_asset                                                    #
# ---------------------------------------------------------------- #

GOOD_URL = "https://github.com/kellylford/Image-Description-Toolkit/releases/download/v4.9.0/Setup.exe"
PAYLOAD = b"x" * (65536 * 3 + 17)


class _Stream:
    """Minimal stand-in for a streamed requests response."""

    def __init__(self, payload, length=True):
        self._payload = payload
        self.headers = {"Content-Length": str(len(payload))} if length else {}

    def raise_for_status(self):
        pass

    def iter_content(self, chunk_size=65536):
        for i in range(0, len(self._payload), chunk_size):
            yield self._payload[i:i + chunk_size]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def dl(tmp_path, monkeypatch):
    monkeypatch.setattr(updater, "download_dir", lambda: tmp_path)
    monkeypatch.setattr(updater.requests, "get",
                        lambda *a, **k: _Stream(PAYLOAD))
    return tmp_path


def test_download_writes_file_and_reports_progress(dl):
    seen = []
    path = updater.download_asset(GOOD_URL, progress=lambda d, t: seen.append((d, t)))
    assert Path(path).read_bytes() == PAYLOAD
    assert seen[-1] == (len(PAYLOAD), len(PAYLOAD))


def test_download_verifies_checksum(dl, monkeypatch):
    good = hashlib.sha256(PAYLOAD).hexdigest()
    monkeypatch.setattr(updater, "expected_sha256", lambda u, n: good)
    path = updater.download_asset(GOOD_URL, checksums_url="https://github.com/x/S.txt")
    assert Path(path).exists()


def test_download_rejects_bad_checksum_and_deletes(dl, monkeypatch):
    """We are about to execute this file, so a mismatch must not survive on disk."""
    monkeypatch.setattr(updater, "expected_sha256", lambda u, n: "deadbeef")
    with pytest.raises(ValueError, match="checksum"):
        updater.download_asset(GOOD_URL, checksums_url="https://github.com/x/S.txt")
    assert list(dl.iterdir()) == []


def test_download_cancel_deletes_partial(dl):
    path = updater.download_asset(GOOD_URL, should_cancel=lambda: True)
    assert path is None
    assert list(dl.iterdir()) == []


def test_download_error_deletes_partial(dl, monkeypatch):
    """A mid-stream failure must not leave a half-installer in temp."""
    class _Boom(_Stream):
        def iter_content(self, chunk_size=65536):
            yield b"x" * chunk_size
            raise ConnectionError("dropped")

    monkeypatch.setattr(updater.requests, "get", lambda *a, **k: _Boom(PAYLOAD))
    with pytest.raises(ConnectionError):
        updater.download_asset(GOOD_URL)
    assert list(dl.iterdir()) == []


def test_download_refuses_untrusted_url(dl):
    with pytest.raises(ValueError):
        updater.download_asset("https://evil.invalid/Setup.exe")
    assert list(dl.iterdir()) == []


def test_version_file_agrees_with_package():
    """VERSION, idt_core.__version__ and pyproject.toml are hand-synced.

    release.yml enforces this at tag time; catching drift here means a developer
    sees it before pushing rather than after a failed release.
    """
    from pathlib import Path
    root = Path(__file__).parent.parent
    assert (root / "VERSION").read_text(encoding="utf-8").strip() == updater.current_version()
