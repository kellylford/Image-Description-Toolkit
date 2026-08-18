"""Alt mnemonics must not collide -- the Windows half of the shortcut story.

``test_menu_shortcuts.py`` covers accelerators (``Ctrl+`` chords) and the
macOS trap where a "&" in a *button* label becomes a Command key equivalent.
Neither check looks at what a "&" does on **Windows**, which is where these
two failures live:

* **A control outranks the menu bar.** wx runs a frame's child panel through
  ``IsDialogMessage`` before the frame handles WM_SYSCHAR, so a mnemonic on a
  panel control answers Alt+letter first and the menu never opens. That is how
  ``Atta&chments`` took Alt+C from the ``&Chat`` menu in IDT Chat, and
  ``Conversation &history`` took Alt+H from ``&Help``.
* **Two items on one letter do not both work.** Within one menu, or one
  dialog, a repeated mnemonic stops being a shortcut: the letter cycles the
  highlight between the candidates and needs Enter to commit. ImageDescriber
  had ``&Cut``/``&Copy`` on C, and four such pairs in the Process menu alone.

Source-level for the same reason as the accelerator tests: this has to run
without a display, and the mistake is one you cannot see on a Mac at all,
because macOS has no Alt mnemonics.
"""

import ast
import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]

#: app key -> (source file, frame class, the method that builds the menu bar)
FRAMES = {
    "chat": (_ROOT / "chatapp" / "chat_app_wx.py", "ChatFrame", "_build_menu"),
    "imagedescriber": (_ROOT / "imagedescriber" / "imagedescriber_wx.py",
                       "ImageDescriberFrame", "create_menu_bar"),
}

#: Files whose wx.Dialog subclasses get the same "no repeats" check.
DIALOG_FILES = [
    _ROOT / "chatapp" / "chat_app_wx.py",
    _ROOT / "imagedescriber" / "dialogs_wx.py",
    _ROOT / "imagedescriber" / "download_dialog.py",
]

_MNEMONIC = re.compile(r"&([A-Za-z0-9])")
_LABEL_WIDGETS = ("StaticText", "Button", "CheckBox", "RadioButton",
                  "ToggleButton", "StaticBox")


# ---------------------------------------------------------------------------
# Reading labels out of the source
# ---------------------------------------------------------------------------

def _text(node):
    """The literal text of a str or f-string node, or None.

    f-strings keep their literal parts, since a mnemonic can only live in one
    of those: ``f"Attachme&nts: {count} files"``.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(v.value for v in node.values
                       if isinstance(v, ast.Constant) and isinstance(v.value, str))
    return None


def _mnemonic(label):
    """The Alt letter a label claims, upper-cased, or None. "&&" is a literal."""
    if not label:
        return None
    match = _MNEMONIC.search(label.replace("&&", ""))
    return match.group(1).upper() if match else None


def _parse(path):
    return ast.parse(path.read_text(encoding="utf-8"))


def _class_node(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    return None


def _method_node(class_node, name):
    for node in class_node.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _looped_calls(scope):
    """ids of every Call inside a loop in `scope`.

    One ``wx.Button(label="&Remove")`` in a ``for`` body is not one button.
    The API keys dialog builds one per provider, so a single source line put
    three live Alt+R buttons in one dialog -- invisible to a check that counts
    source strings.
    """
    inside = set()
    for node in ast.walk(scope):
        if isinstance(node, (ast.For, ast.AsyncFor, ast.While,
                             ast.ListComp, ast.comprehension)):
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    inside.add(id(child))
    return inside


def _control_labels(scope):
    """(label, lineno, repeats) for every label in `scope`.

    `repeats` is True when the widget is built in a loop, so the one label
    claims the letter more than once by itself.

    ``SetLabel`` counts: the attachments label is rewritten on every refresh,
    so the mnemonic that shipped was the one in ``_refresh_attachments``, not
    the one in the constructor. So do notebook page titles -- ``AddPage``
    passes a "&" straight to the native tab control, and that tab shares the
    dialog's one namespace with the controls on the page behind it.
    """
    looped = _looped_calls(scope)
    found = []

    def add(label, node):
        if label:
            found.append((label, node.lineno, id(node) in looped))

    for node in ast.walk(scope):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        is_widget = (isinstance(func, ast.Attribute)
                     and func.attr in _LABEL_WIDGETS
                     and isinstance(func.value, ast.Name) and func.value.id == "wx")
        if is_widget:
            for kw in node.keywords:
                if kw.arg == "label":
                    add(_text(kw.value), node)
            for arg in node.args:                     # positional label
                if "&" in (_text(arg) or ""):
                    add(_text(arg), node)
        elif isinstance(func, ast.Attribute) and func.attr == "SetLabel":
            for arg in node.args:
                add(_text(arg), node)
        elif isinstance(func, ast.Attribute) and func.attr in ("AddPage",
                                                               "InsertPage"):
            for arg in node.args:
                if "&" in (_text(arg) or ""):
                    add(_text(arg), node)
    return [entry for entry in found if _mnemonic(entry[0])]


def _menus(method):
    """Menu-bar titles and menu items, grouped by the menu they belong to.

    Returns ``(titles, items)`` where `titles` is ``{letter: title}`` for the
    bar itself and `items` is ``{menu_variable: [(label, lineno), ...]}``.

    Both shapes in the codebase are covered: ``menu.Append(id, "&Label")`` and
    the ``self._menu_item(menu, "&Label", handler)`` helper.
    """
    titles, items = {}, {}
    for node in ast.walk(method):
        if not isinstance(node, ast.Call):
            continue
        func = node.func

        # bar.Append(file_menu, "&File") -- a menu bar title.
        if (isinstance(func, ast.Attribute) and func.attr == "Append"
                and len(node.args) >= 2
                and isinstance(node.args[0], ast.Name)
                and node.args[0].id.endswith("menu")
                and _text(node.args[1])):
            letter = _mnemonic(_text(node.args[1]))
            if letter:
                titles.setdefault(letter, []).append(_text(node.args[1]))
            continue

        # file_menu.Append(wx.ID_NEW, "&New...") / .AppendCheckItem / ...
        menu_var = label = None
        if (isinstance(func, ast.Attribute)
                and func.attr.startswith("Append")
                and isinstance(func.value, ast.Name)
                and func.value.id.endswith("menu")):
            menu_var = func.value.id
            label = next((_text(a) for a in node.args if _text(a)), None)
        # self._menu_item(chat_menu, "&Send Message\tCtrl+Return", handler)
        elif (isinstance(func, ast.Attribute) and func.attr == "_menu_item"
              and node.args and isinstance(node.args[0], ast.Name)
              and node.args[0].id.endswith("menu")):
            menu_var = node.args[0].id
            label = _text(node.args[1]) if len(node.args) > 1 else None

        if menu_var and label and _mnemonic(label):
            items.setdefault(menu_var, []).append((label, node.lineno))
    return titles, items


def _identity(label):
    """What makes two labels the *same* control rather than two of them.

    The label with its varying tail removed: everything after a tab (the
    accelerator) or the first colon (the state). One control can be spelled
    several ways -- ``Attachme&nts: none`` / ``: 1 file`` / ``: {count}
    files`` are three states of one label, and ``E&xit`` / ``E&xit\\tCtrl+Q``
    are two platform branches of one menu item.

    Matching on a shorter prefix is not enough: ``&General`` and ``&Geocode
    GPS coordinates...`` share every character a prefix rule would compare,
    and they are a real collision -- a notebook tab and a checkbox on the page
    behind it, both answering Alt+G.
    """
    return label.split("\t")[0].split(":")[0].strip()


def _duplicates(labelled):
    """{letter: [labels]} for every Alt letter claimed by two controls.

    Entries carry a `repeats` flag when they are built in a loop; one of those
    conflicts with itself, so it is reported without needing a second label.
    """
    claims = {}
    for entry in labelled:
        label, repeats = entry[0], (len(entry) > 2 and entry[2])
        by_control = claims.setdefault(_mnemonic(label), {})
        by_control[_identity(label)] = label
        if repeats:
            by_control[f"{_identity(label)} (again, built in a loop)"] = (
                f"{label} (one per loop iteration)")
    return {letter: sorted(by_control.values())
            for letter, by_control in claims.items() if len(by_control) > 1}


every_frame = pytest.mark.parametrize("app", sorted(FRAMES))


# ---------------------------------------------------------------------------
# The bug that was reported: a control eating a menu's Alt key
# ---------------------------------------------------------------------------

@every_frame
def test_no_control_takes_a_menu_bar_letter(app):
    """The panel answers Alt first, so a shared letter means the menu is gone.

    Reported from Windows: Alt+C in IDT Chat moved focus to the attachments
    list instead of opening the Chat menu.
    """
    path, class_name, menu_method = FRAMES[app]
    tree = _parse(path)
    frame = _class_node(tree, class_name)
    assert frame is not None, f"{class_name} not found in {path.name}"

    titles, _items = _menus(_method_node(frame, menu_method))
    assert titles, f"no menu bar titles found in {class_name}.{menu_method}"

    stolen = []
    for label, line, _repeats in _control_labels(frame):
        letter = _mnemonic(label)
        if letter in titles:
            stolen.append(f"{path.name}:{line} {label!r} takes Alt+{letter} "
                          f"from the {titles[letter][0]!r} menu")
    assert not stolen, "\n".join(stolen)


@every_frame
def test_no_two_controls_share_an_alt_letter(app):
    """One letter, two controls: Alt+letter cycles instead of acting."""
    path, class_name, _menu_method = FRAMES[app]
    frame = _class_node(_parse(path), class_name)
    clashes = _duplicates(_control_labels(frame))
    assert not clashes, f"{path.name}: controls sharing an Alt letter: {clashes}"


# ---------------------------------------------------------------------------
# Within one menu, and within one dialog
# ---------------------------------------------------------------------------

@every_frame
def test_menu_bar_titles_are_unique(app):
    path, class_name, menu_method = FRAMES[app]
    frame = _class_node(_parse(path), class_name)
    titles, _items = _menus(_method_node(frame, menu_method))
    repeated = {letter: names for letter, names in titles.items()
                if len(set(names)) > 1}
    assert not repeated, f"{path.name}: menu bar titles sharing a letter: {repeated}"


@every_frame
def test_no_menu_repeats_a_mnemonic(app):
    """Inside an open menu the letter should run the command, not cycle.

    Platform-conditional items are the reason this compares by label rather
    than by count: ``&Preferences...`` (macOS) and ``&Configure Settings...``
    (Windows) are two branches of one item, never both present at once.
    """
    path, class_name, menu_method = FRAMES[app]
    frame = _class_node(_parse(path), class_name)
    _titles, items = _menus(_method_node(frame, menu_method))
    assert items, f"no menu items found in {class_name}.{menu_method}"

    problems = {}
    for menu_var, labelled in items.items():
        clashes = _duplicates(labelled)
        if clashes:
            problems[menu_var] = clashes
    assert not problems, f"{path.name}: repeated mnemonics: {problems}"


def _dialog_classes():
    for path in DIALOG_FILES:
        tree = _parse(path)
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            bases = {getattr(b, "attr", getattr(b, "id", "")) for b in node.bases}
            if "Dialog" in bases:
                yield pytest.param(path, node.name,
                                   id=f"{path.stem}::{node.name}")


@pytest.mark.parametrize("path,class_name", list(_dialog_classes()))
def test_no_dialog_repeats_a_mnemonic(path, class_name):
    """A dialog has no menu bar, so its controls are the whole namespace."""
    dialog = _class_node(_parse(path), class_name)
    clashes = _duplicates(_control_labels(dialog))
    assert not clashes, (
        f"{path.name}::{class_name} has controls sharing an Alt letter: "
        f"{clashes}")
