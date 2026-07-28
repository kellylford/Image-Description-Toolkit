"""Folder scoping for the Process menu commands.

The P key scoped batch processing to the selected folder via
_get_file_paths_under_node(); the Process menu never read the tree selection at
all and always iterated self.workspace.items. So with focus on
iphone/2026/07, "Process Undescribed Images" processed all of iphone.

Rather than make the menu silently start honouring selection (which would
change behaviour for anyone relying on the old semantics), the menu now has
both: explicit folder-scoped commands and explicit "Entire Workspace" ones.

imagedescriber_wx.py is a ~8500-line wx module at 0% coverage and cannot be
imported headlessly here, so these tests exercise the scoping contract against
the real functions bound to the class, with a minimal stand-in for the wx tree.
"""

import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_SRC = (_ROOT / "imagedescriber" / "imagedescriber_wx.py").read_text(
    encoding="utf-8", errors="replace"
)


# --------------------------------------------------------------------------- #
# Scope resolution                                                             #
# --------------------------------------------------------------------------- #

class _Node:
    """Stand-in for a wx.TreeItemId."""

    def __init__(self, label, data=None, children=None, ok=True):
        self.label = label
        self.data = data                    # None => folder node
        self.children = children or []
        self._ok = ok

    def IsOk(self):
        return self._ok


class _FakeTree:
    """Minimal stand-in for the wx.TreeCtrl API used by the scoping helpers."""

    def __init__(self, selection):
        self._selection = selection

    def GetSelection(self):
        return self._selection

    def GetItemData(self, node):
        return node.data

    def GetItemText(self, node):
        return node.label

    def ItemHasChildren(self, node):
        return bool(node.children)

    def GetFirstChild(self, node):
        if not node.children:
            return _Node("", ok=False), 0
        return node.children[0], 0

    def GetNextChild(self, node, cookie):
        nxt = cookie + 1
        if nxt >= len(node.children):
            return _Node("", ok=False), nxt
        return node.children[nxt], nxt


class _App:
    """Binds the real methods under test onto a minimal host object."""

    def __init__(self, tree):
        self.image_list = tree

    # Real implementations, imported by source extraction below.
    _get_file_paths_under_node = None
    _selected_folder_scope = None


def _bind_real_methods():
    """Exec just the two scoping methods from the module onto _App.

    The module imports wx at top level and builds an 8500-line frame class, so
    it cannot be imported in a headless test run. Extracting the two functions
    keeps the test honest -- it runs the shipped source, not a copy.
    """
    ns = {"logger": type("L", (), {"info": staticmethod(lambda *a, **k: None)})()}
    for name in ("_get_file_paths_under_node", "_selected_folder_scope"):
        m = re.search(
            rf"^    def {name}\(self.*?(?=^    def )", _SRC, re.MULTILINE | re.DOTALL
        )
        assert m, f"could not locate {name} in imagedescriber_wx.py"
        body = "\n".join(line[4:] if line.startswith("    ") else line
                         for line in m.group(0).splitlines())
        exec(compile(body, "imagedescriber_wx.py", "exec"), ns)
        setattr(_App, name, ns[name])


_bind_real_methods()


def _tree():
    """iphone/{2025/{01},2026/{07}} with two images in each leaf folder."""
    f_2026_07 = _Node("07", None, [
        _Node("a.jpg", "/w/iphone/2026/07/a.jpg"),
        _Node("b.jpg", "/w/iphone/2026/07/b.jpg"),
    ])
    f_2026 = _Node("2026", None, [f_2026_07])
    f_2025_01 = _Node("01", None, [
        _Node("c.jpg", "/w/iphone/2025/01/c.jpg"),
    ])
    f_2025 = _Node("2025", None, [f_2025_01])
    iphone = _Node("iphone", None, [f_2025, f_2026])
    return iphone, f_2026, f_2026_07


def test_scope_is_the_selected_subfolder_only():
    """The reported bug: focus on iphone/2026/07 must mean only 07."""
    _iphone, _f2026, f07 = _tree()
    app = _App(_FakeTree(f07))

    paths, label = app._selected_folder_scope()

    assert label == "07"
    assert sorted(paths) == [
        "/w/iphone/2026/07/a.jpg",
        "/w/iphone/2026/07/b.jpg",
    ]
    assert not any("2025" in p for p in paths), "sibling year leaked into scope"


def test_scope_of_intermediate_folder_includes_its_descendants():
    _iphone, f2026, _f07 = _tree()
    app = _App(_FakeTree(f2026))

    paths, label = app._selected_folder_scope()

    assert label == "2026"
    assert len(paths) == 2
    assert all("/2026/" in p for p in paths)


def test_scope_of_root_folder_is_everything_under_it():
    iphone, _f2026, _f07 = _tree()
    app = _App(_FakeTree(iphone))

    paths, label = app._selected_folder_scope()

    assert label == "iphone"
    assert len(paths) == 3


def test_no_scope_when_a_leaf_image_is_selected():
    """A file node is not a folder; callers must not treat it as empty scope."""
    leaf = _Node("a.jpg", "/w/iphone/2026/07/a.jpg")
    app = _App(_FakeTree(leaf))
    assert app._selected_folder_scope() is None


def test_no_scope_when_nothing_is_selected():
    app = _App(_FakeTree(_Node("", ok=False)))
    assert app._selected_folder_scope() is None


def test_no_scope_when_tree_is_absent():
    app = _App(None)
    assert app._selected_folder_scope() is None


def test_empty_folder_yields_empty_scope_not_none():
    """Distinct from None: the caller reports 'no images' rather than falling
    back to processing the entire workspace."""
    empty = _Node("08", None, [])
    app = _App(_FakeTree(empty))
    result = app._selected_folder_scope()
    assert result is not None
    paths, label = result
    assert paths == []
    assert label == "08"


# --------------------------------------------------------------------------- #
# Menu wiring — the surprise this change exists to remove                      #
# --------------------------------------------------------------------------- #

def test_workspace_wide_menu_items_say_entire_workspace():
    """The old labels gave no hint that they ignore the selected folder."""
    for label in ("Process &Undescribed Images (Entire Workspace)",
                  "&Redescribe All Images (Entire Workspace)"):
        assert label in _SRC, f"missing explicit workspace-wide label: {label}"


def test_folder_scoped_menu_items_exist():
    for label in ("Process Undescribed in Selected &Folder",
                  "Redescribe All in Selected Fo&lder"):
        assert label in _SRC, f"missing folder-scoped menu item: {label}"


def test_folder_scoped_handlers_pass_scope_paths():
    """A scoped handler that forgot scope_paths would silently process all."""
    m = re.search(
        r"def _process_selected_folder\(self.*?(?=\n    def )", _SRC, re.DOTALL
    )
    assert m, "expected a shared _process_selected_folder entry point"
    body = m.group(0)
    assert "scope_paths=paths" in body
    assert "_selected_folder_scope()" in body


def test_on_process_all_defaults_to_whole_workspace():
    """The CLI autostart path and the workspace-wide commands rely on this."""
    m = re.search(r"def on_process_all\(self.*?\n(?=\s+\"\"\")", _SRC, re.DOTALL)
    assert m, "could not find on_process_all signature"
    assert "scope_paths: Optional[list] = None" in m.group(0)


def test_scoped_run_filters_workspace_items():
    """on_process_all must narrow the scan, not just log a label."""
    m = re.search(
        r"if scope_paths is None:.*?for item in items_to_scan:", _SRC, re.DOTALL
    )
    assert m, "on_process_all should resolve items_to_scan from scope_paths"
    body = m.group(0)
    assert "wanted = set(scope_paths)" in body
    assert "if p in wanted" in body


def test_redescribe_confirmation_states_the_scope():
    """Saying 'ALL images' during a one-folder run is the same ambiguity."""
    assert 'target = "ALL images in the entire workspace"' in _SRC
    assert 'image(s) in \\"{scope_label}\\"' in _SRC or "scope_label" in _SRC
