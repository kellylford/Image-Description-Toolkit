"""A video in the source folder belongs to that folder, like the photos beside it.

Reported against a real CLI bundle: the source folder appeared in the tree but
held only part of itself. 195 photos carried subfolder="07"; the 29 videos in
the same folder carried None and hung off the tree root instead.

Two things combined to cause it:

  * add_source_folder() defaults to include_videos=False, so it never touched
    the videos at all -- they are registered separately by the extraction path.
  * that path is the ONE place a WorkspaceItem is constructed by hand rather
    than through add_image(), so it was missed when the four inline subfolder
    computations were unified on source_relative_subfolder().

Nothing assigned a subfolder to a video, and no test noticed because every
existing fixture contained images only. The GUI's own scan
(on_files_discovered) anchors every discovered file including videos, so the
same folder opened as two different shapes depending on which side created the
workspace.

These tests work on the item the CLI actually registers, without invoking
opencv or extracting anything.
"""

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from idt_core.workspace import (  # noqa: E402
    Workspace,
    WorkspaceItem,
    source_relative_subfolder,
)


@pytest.fixture
def source(tmp_path):
    """A source folder holding both photos and a video, as a phone dump does."""
    root = tmp_path / "Photos" / "2026" / "07"
    root.mkdir(parents=True)
    (root / "IMG_0001.jpg").write_bytes(b"\xff\xd8\xff\xe0jpeg")
    (root / "IMG_0002.jpg").write_bytes(b"\xff\xd8\xff\xe0jpeg")
    (root / "clip.mov").write_bytes(b"\x00\x00\x00\x18ftypqt  ")
    return root


def _register_video_like_the_cli(ws, video, source_root):
    """Mirror _extract_one_video_into_workspace's registration step.

    Duplicated rather than imported because the real function also runs opencv
    frame extraction. The subfolder assignment is what matters here, and
    test_the_cli_registration_site_passes_a_source_root below pins that the
    real call site still supplies the argument this depends on.
    """
    subfolder = source_relative_subfolder(video, source_root) if source_root else None
    item = WorkspaceItem(
        image=video.name,
        source_path=str(video),
        storage="reference",
        item_type="video",
        subfolder=subfolder,
        is_missing=False,
    )
    ws.save_item(item)
    return item


def test_a_video_gets_the_same_subfolder_as_the_photos_beside_it(tmp_path, source):
    ws = Workspace.create(tmp_path / "WS")
    ws.add_source_folder(source, recursive=True)

    photo_subfolders = {i.subfolder for i in ws.items() if i.item_type != "video"}
    assert photo_subfolders == {"07"}, photo_subfolders

    video = _register_video_like_the_cli(ws, source / "clip.mov", source)

    assert video.subfolder == "07", (
        f"the video got subfolder={video.subfolder!r} while the photos in the "
        "same folder got '07'. It will hang off the tree root, so the folder "
        "node holds only part of the folder."
    )


def test_without_a_source_root_the_video_is_unanchored(tmp_path, source):
    """Documents the fallback rather than pretending it cannot happen.

    Callers that genuinely have no source folder still get None, which is the
    old behaviour -- so the guarantee above depends entirely on the source root
    reaching this code, which the next test checks.
    """
    ws = Workspace.create(tmp_path / "WS")
    video = _register_video_like_the_cli(ws, source / "clip.mov", None)
    assert video.subfolder is None


def test_add_source_folder_still_excludes_videos(tmp_path, source):
    """Pins the reason the video needs registering separately at all.

    If this ever flips to including videos, the extraction path would register
    them twice; the assumption is worth failing loudly on rather than drifting.
    """
    ws = Workspace.create(tmp_path / "WS")
    added = ws.add_source_folder(source, recursive=True)
    assert all(i.item_type != "video" for i in added)
    assert len(added) == 2, [i.image for i in added]


def test_the_cli_registration_site_passes_a_source_root():
    """The fix is only live if the call sites actually supply the root.

    _extract_one_video_into_workspace takes source_root as an optional
    argument, so forgetting it at a call site silently restores the bug --
    every video back to subfolder=None with nothing raised.
    """
    src = (_ROOT / "cli" / "main.py").read_text(encoding="utf-8")

    assert "def _extract_one_video_into_workspace(ws, video: Path, opts," in src, (
        "signature changed; update this test with it"
    )

    calls = [line.strip() for line in src.splitlines()
             if "_extract_one_video_into_workspace(ws" in line
             and not line.strip().startswith("def ")]
    assert calls, "no call sites found"
    for call in calls:
        assert call.rstrip().endswith("opts, source)"), (
            f"call site does not pass the source root: {call!r}. Without it "
            "every video reverts to subfolder=None."
        )


def test_the_video_and_its_photos_share_one_tree_group(tmp_path, source):
    """The user-visible property: one folder node covering the whole folder."""
    ws = Workspace.create(tmp_path / "WS")
    ws.add_source_folder(source, recursive=True)
    _register_video_like_the_cli(ws, source / "clip.mov", source)

    groups = {}
    for item in ws.items():
        groups.setdefault(item.subfolder, []).append(item.image)

    assert set(groups) == {"07"}, (
        f"expected every item under one '07' group, got {sorted(groups)} -- "
        "anything under None renders at the tree root, outside the folder"
    )
    assert len(groups["07"]) == 3
