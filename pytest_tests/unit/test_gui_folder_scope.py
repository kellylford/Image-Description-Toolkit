"""The folder node exists in the real GUI, and folder-scoped commands can use it.

A bundle made by `idt describe` opened in ImageDescriber with no top-level
folder node, so every folder-scoped command was dead: both Process commands
stopped at "Select a folder in the image tree first", P-on-a-folder had nothing
to act on, and "Refresh Folder from Disk" stayed permanently disabled. Cause was
four sites computing `subfolder` against two different anchors -- the CLI at the
source folder (yielding None), the GUI at its parent (yielding "05") -- fixed by
routing all five through source_relative_subfolder().

That fix was verified by *replicating* the tree builder's grouping against real
bundle data. What nobody had done was open the app: ImageDescriber.exe was built
but never launched, so "does selecting a folder node actually scope a Process
command" remained a manual step.

This closes that gap permanently rather than once. It drives the real
ImageDescriberFrame -- the real load_workspace(), the real refresh_image_list(),
the real wx.TreeCtrl -- and asks the real _selected_folder_scope() what a
selected folder node resolves to.

It matters that this is automated rather than clicked: wx swallows exceptions
raised inside event handlers, so a regression here produces a menu item that
silently does nothing, which is exactly the failure mode a human click-through
is worst at noticing and a test is best at.
"""

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(_ROOT), str(_ROOT / "imagedescriber")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from idt_core.workspace import Workspace  # noqa: E402

wx = pytest.importorskip("wx", reason="wxPython not installed in this environment")

import imagedescriber_wx  # noqa: E402


def _make_png(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + path.name.encode("utf-8"))


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App.Get() or wx.App(False)
    yield app


@pytest.fixture(scope="module")
def _dialog_log(wx_app):
    """Swallow modal dialogs and record them instead.

    load_workspace reports problems with show_error(). Left alone, a broken
    bundle opens a modal dialog and hangs the run forever on a headless CI
    machine. Recording the message and failing on it is strictly better.

    Module-scoped, so it must undo itself explicitly rather than relying on the
    function-scoped monkeypatch fixture -- leaving these patched would silence
    dialogs in every test module that ran afterwards.
    """
    from _pytest.monkeypatch import MonkeyPatch

    seen = []
    mp = MonkeyPatch()

    def _capture(kind):
        def _fn(_parent, message, *_a, **_k):
            seen.append((kind, message))
        return _fn

    for name in ("show_error", "show_warning", "show_info"):
        mp.setattr(imagedescriber_wx, name, _capture(name), raising=False)

    yield seen
    mp.undo()


@pytest.fixture
def no_dialogs(_dialog_log):
    """Per-test view of the dialog log, cleared between tests."""
    _dialog_log.clear()
    return _dialog_log


@pytest.fixture
def cli_style_bundle(tmp_path):
    """A bundle built exactly the way `idt describe` builds one.

    add_source_folder is the CLI's entry point, so this reproduces the artifact
    that failed to open with a folder node -- not a GUI-created bundle, which
    always worked.
    """
    source = tmp_path / "Pictures" / "2026" / "05"
    _make_png(source / "IMG_0001.jpg")
    _make_png(source / "IMG_0002.jpg")
    _make_png(source / "Day2" / "IMG_0003.jpg")

    ws = Workspace.create(tmp_path / "FromCLI")
    ws.add_source_folder(source, recursive=True)
    return ws.path, source


@pytest.fixture(scope="module")
def _frame(wx_app, _dialog_log):
    """One frame for the whole module.

    Constructing it is cheap; tearing it down is not -- Destroy() plus a
    SafeYield() to pump the pending destroy cost 4-18s each, which dominated
    the file. Every test calls the real load_workspace(), which replaces
    self.workspace wholesale, so reuse carries no state between them -- and
    opening several workspaces in one session is what the app actually does.
    """
    f = imagedescriber_wx.ImageDescriberFrame()
    yield f

    # Clear the tree before destroying it. These tests select nodes, and a
    # pending selection event delivered during Destroy() runs on_image_selected
    # against an already-freed TreeCtrl:
    #   RuntimeError: wrapped C/C++ object of type TreeCtrl has been deleted
    # Observed while checking that these tests fail against the old anchor.
    # Harmless there, but it is exactly the kind of teardown race that turns
    # into an intermittent CI failure nobody can reproduce.
    try:
        f.image_list.Unselect()
        f.image_list.DeleteAllItems()
    except Exception:
        pass
    f.Destroy()
    wx.SafeYield()


@pytest.fixture
def frame(_frame, no_dialogs):
    return _frame


# ---------------------------------------------------------------------------
# Tree walking helpers -- read the real control, do not reimplement grouping
# ---------------------------------------------------------------------------

def _top_level_nodes(tree):
    root = tree.GetRootItem()
    out = []
    node, cookie = tree.GetFirstChild(root)
    while node.IsOk():
        out.append(node)
        node, cookie = tree.GetNextSibling(node), cookie
    return out


def _folder_nodes(tree, parent):
    """Folder nodes carry no item data; leaf nodes carry a file path."""
    out = []
    node, cookie = tree.GetFirstChild(parent)
    while node.IsOk():
        if tree.GetItemData(node) is None:
            out.append(node)
        node = tree.GetNextSibling(node)
    return out


def _leaf_count(tree, parent):
    n = 0
    node, cookie = tree.GetFirstChild(parent)
    while node.IsOk():
        if tree.GetItemData(node) is not None:
            n += 1
        node = tree.GetNextSibling(node)
    return n


# ---------------------------------------------------------------------------

def test_a_cli_bundle_opens_with_a_top_level_folder_node(
        frame, cli_style_bundle, no_dialogs):
    """The reported symptom, checked against the real tree control."""
    bundle_path, source = cli_style_bundle

    frame.load_workspace(str(bundle_path))

    assert not no_dialogs, f"load_workspace reported a problem: {no_dialogs}"

    tree = frame.image_list
    names = [tree.GetItemText(n) for n in _top_level_nodes(tree)]
    assert source.name in names, (
        f"no top-level node named {source.name!r}; tree top level is {names}. "
        "Every folder-scoped Process command has nothing to scope to."
    )


def test_nothing_is_stranded_at_the_tree_root(frame, cli_style_bundle):
    """Items with subfolder None hang off the invisible root and are unreachable."""
    bundle_path, _source = cli_style_bundle

    frame.load_workspace(str(bundle_path))

    tree = frame.image_list
    stranded = _leaf_count(tree, tree.GetRootItem())
    assert stranded == 0, (
        f"{stranded} image(s) sit directly at the tree root, so no folder node "
        "covers them"
    )


def test_selecting_the_folder_node_scopes_a_process_command(
        frame, cli_style_bundle):
    """The manual step nobody had performed: click the folder, get a scope.

    _selected_folder_scope() is what both folder-scoped Process commands and
    the P key resolve through. None means "Select a folder in the image tree
    first" -- the dead end originally reported.
    """
    bundle_path, source = cli_style_bundle

    frame.load_workspace(str(bundle_path))

    tree = frame.image_list
    node = next(n for n in _top_level_nodes(tree)
                if tree.GetItemText(n) == source.name)
    tree.SelectItem(node)

    scope = frame._selected_folder_scope()

    assert scope is not None, (
        "selecting the source folder node yielded no scope -- the Process "
        "commands would still say 'Select a folder in the image tree first'"
    )
    paths, label = scope
    assert label == source.name
    assert len(paths) == 3, (
        f"expected all 3 images under {source.name!r}, got {len(paths)}: {paths}"
    )


def test_the_nested_subfolder_is_a_child_not_a_sibling(frame, cli_style_bundle):
    """Day2 belongs under 05, not beside it.

    Under the old CLI anchor the nested file got "Day2" and appeared as its own
    top-level node, detached from the folder it lives in.
    """
    bundle_path, source = cli_style_bundle

    frame.load_workspace(str(bundle_path))

    tree = frame.image_list
    top = {tree.GetItemText(n): n for n in _top_level_nodes(tree)}
    assert "Day2" not in top, (
        "Day2 appeared at the top level instead of nested under "
        f"{source.name!r}: {sorted(top)}"
    )

    children = [tree.GetItemText(n) for n in _folder_nodes(tree, top[source.name])]
    assert "Day2" in children, (
        f"Day2 is not a child of {source.name!r}; children are {children}"
    )


def test_scoping_the_nested_folder_selects_only_its_own_images(
        frame, cli_style_bundle):
    """Scope must be the subtree, not the whole workspace.

    "Process Undescribed Images" with focus on a nested folder used to process
    everything above it, which is the drift _selected_folder_scope() exists to
    prevent.
    """
    bundle_path, source = cli_style_bundle

    frame.load_workspace(str(bundle_path))

    tree = frame.image_list
    top = {tree.GetItemText(n): n for n in _top_level_nodes(tree)}
    day2 = next(n for n in _folder_nodes(tree, top[source.name])
                if tree.GetItemText(n) == "Day2")
    tree.SelectItem(day2)

    paths, label = frame._selected_folder_scope()

    assert label == "Day2"
    assert len(paths) == 1, (
        f"Day2 holds one image; scope returned {len(paths)}: {paths}"
    )


def test_selecting_an_image_gives_no_folder_scope(frame, cli_style_bundle):
    """A leaf must return None, not an accidental scope of its parent."""
    bundle_path, source = cli_style_bundle

    frame.load_workspace(str(bundle_path))

    tree = frame.image_list
    top = {tree.GetItemText(n): n for n in _top_level_nodes(tree)}
    node, _cookie = tree.GetFirstChild(top[source.name])
    while node.IsOk() and tree.GetItemData(node) is None:
        node = tree.GetNextSibling(node)
    assert node.IsOk(), "expected at least one image leaf under the folder"

    tree.SelectItem(node)
    assert frame._selected_folder_scope() is None
