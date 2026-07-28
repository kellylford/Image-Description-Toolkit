"""The cheapest possible floor under ~10,000 statements of wxPython.

Issue #228, P2. The GUI is the highest-risk area in the repo and had 0.00%
coverage: wxPython swallows every exception raised inside an event handler, so
a broken handler is not a traceback, it is a button that does nothing.

CLAUDE.md records the canonical incident. A commit moved

    logger = logging.getLogger(__name__)

from module scope into main(). Every event handler that called logger.info(...)
then raised NameError, silently. on_close, on_process_single and every other
handler stopped working; Alt+F4 was dead. Eight hours to find, one line to fix.

Nothing here tries to cover the GUI's behaviour. Three checks, the whole file
running in under three seconds, each of which would have caught that incident:

  1. every module imports cleanly under a headless wx.App
  2. every handler named in a Bind() call actually exists on its class
  3. `logger` is bound in every scope that reads it

(2) is what catches the rename that leaves a dead binding -- the failure mode wx
is least able to report. (3) is the incident itself, as an assertion.
"""

import ast
import importlib
import os
import re
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_GUI_DIR = _ROOT / "imagedescriber"

# Flat imports ("from ai_providers import ...") are mandatory for PyInstaller
# frozen mode, so the package directory itself has to be importable.
for _p in (str(_ROOT), str(_GUI_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)


#: Set by every CI job that is supposed to exercise the GUI. When set, a
#: missing wxPython or an unusable wx.App is a FAILURE rather than a skip.
#:
#: This exists because the plain `pytest.importorskip("wx")` below hid all 213
#: tests in this file on every macOS run for as long as the file existed. The
#: root .venv there had no wxPython, so the whole module vanished at collection
#: and reported as nothing louder than "collected 605 items / 1 skipped"
#: (issue #230). A skip that nobody can see is indistinguishable from a pass.
#:
#: Unset locally, so a contributor without the GUI extras still gets a clean
#: run rather than a wall of red.
REQUIRE_WX = os.environ.get("IDT_REQUIRE_WX") == "1"

try:
    import wx
except ImportError as _exc:                                  # pragma: no cover
    if REQUIRE_WX:
        raise RuntimeError(
            "IDT_REQUIRE_WX=1 but wxPython is not importable, so the GUI smoke "
            f"tests cannot run: {_exc}. Install wxPython into the interpreter "
            "running pytest, or unset IDT_REQUIRE_WX if this job is not meant "
            "to cover the GUI."
        ) from _exc
    wx = None

pytestmark = pytest.mark.skipif(
    wx is None, reason="wxPython not installed in this environment")


#: Modules that genuinely cannot be imported, each with the reason.
#: An entry here is a claim someone has to defend in review -- it is not a
#: place to park a module that merely fails today.
#:
#: Currently empty, and worth keeping that way: every GUI module is covered.
#: (ui_components.py lived here briefly -- it imported PyQt6, left over from
#: the pre-wx UI, and was deleted rather than excluded.)
UNIMPORTABLE: dict[str, str] = {}


def _gui_modules():
    for path in sorted(_GUI_DIR.glob("*.py")):
        if path.name == "__init__.py":
            continue
        yield path.stem


ALL_MODULES = list(_gui_modules())
MODULES = [m for m in ALL_MODULES if m not in UNIMPORTABLE]


@pytest.fixture(scope="module")
def wx_app():
    """A real wx.App. Some modules build wx objects at import time.

    Importing wx and being able to construct an App are different things. On
    macOS an App needs a framework build of Python and a window server, so a
    job can have wxPython installed and still be unable to run any of this.
    That distinction has to be visible, not swallowed.
    """
    try:
        app = wx.App.Get() or wx.App(False)
    except Exception as exc:                                 # pragma: no cover
        if REQUIRE_WX:
            pytest.fail(
                f"wxPython imports but wx.App() failed: {exc}\n"
                "On macOS this usually means the interpreter is not a framework "
                "build, or the job has no window server. Fix the runner, or stop "
                "setting IDT_REQUIRE_WX for this job and record why -- but do "
                "not let these tests skip silently."
            )
        pytest.skip(f"no usable display for wxPython: {exc}")
    yield app


def test_wx_is_present_when_the_job_says_it_must_be():
    """Makes the environment's own expectation checkable.

    Without this, "IDT_REQUIRE_WX is set but wx is missing" would be caught at
    import time only, and a job that quietly stopped setting the variable would
    go back to skipping everything with nothing to notice.
    """
    if not REQUIRE_WX:
        pytest.skip("IDT_REQUIRE_WX not set; GUI coverage is optional here")
    assert wx is not None, "wxPython missing in a job that requires it"


# ---------------------------------------------------------------------------
# 1. Import smoke
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("module_name", MODULES)
def test_gui_module_imports(module_name, wx_app):
    """A NameError at module scope must fail here, not silently at runtime."""
    try:
        importlib.import_module(module_name)
    except Exception as exc:  # noqa: BLE001 - the failure IS the finding
        pytest.fail(
            f"imagedescriber/{module_name}.py failed to import: "
            f"{type(exc).__name__}: {exc}\n"
            "wx swallows exceptions inside event handlers, so this would "
            "surface to the user as controls that do nothing."
        )


def test_the_module_list_is_not_empty():
    """Guard the guard: a bad glob would make every test above vacuous."""
    assert len(MODULES) >= 10, f"only found {MODULES} -- did the glob break?"


def test_no_gui_module_imports_a_qt_binding():
    """This project is wxPython. Qt here means dead or unrunnable code.

    The GUI migrated off PyQt6 well before this test existed, but
    ui_components.py survived the migration importing QtWidgets and simply
    never ran again -- invisible because nothing imported it and nothing
    measured it. Anything that reaches for Qt now is either a leftover or a
    module that cannot start.
    """
    offenders = []
    for module_name in ALL_MODULES:
        source = (_GUI_DIR / f"{module_name}.py").read_text(encoding="utf-8")
        for lineno, line in enumerate(source.splitlines(), start=1):
            if re.match(r"\s*(from|import)\s+(PyQt\d|PySide\d|qtpy)\b", line):
                offenders.append(f"  {module_name}.py:{lineno}: {line.strip()}")

    assert not offenders, (
        "Qt imports in the wxPython GUI. Neither PyQt nor PySide is a "
        "dependency of this project, so these modules cannot be imported at "
        "all:\n" + "\n".join(offenders)
    )


def test_exclusions_are_justified_and_still_necessary():
    """An excluded module needs a reason, and must still actually be broken.

    Without the second half, UNIMPORTABLE becomes a place modules go to die
    quietly -- which is how the GUI reached 0% coverage in the first place.
    """
    for name, reason in UNIMPORTABLE.items():
        assert (_GUI_DIR / f"{name}.py").exists(), (
            f"{name} is excluded but no longer exists -- drop the entry."
        )
        assert len(reason.strip()) > 40, (
            f"{name} is excluded without a real explanation."
        )
        try:
            importlib.import_module(name)
        except Exception:
            continue
        pytest.fail(
            f"imagedescriber/{name}.py now imports cleanly. Remove it from "
            "UNIMPORTABLE so it is covered like every other module."
        )


# ---------------------------------------------------------------------------
# 2. Every bound handler exists
# ---------------------------------------------------------------------------

def _bindings_in(path: Path):
    """Yield (class_name, handler_name, lineno) for `X.Bind(EVT, self.name)`.

    Only handlers written as `self.something` are checked; lambdas, functools
    partials and free functions are someone else's problem.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    for class_node in tree.body:
        if not isinstance(class_node, ast.ClassDef):
            continue  # classes defined inside functions are not importable
        for node in ast.walk(class_node):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (isinstance(func, ast.Attribute) and func.attr == "Bind"):
                continue
            if len(node.args) < 2:
                continue
            handler = node.args[1]
            if (isinstance(handler, ast.Attribute)
                    and isinstance(handler.value, ast.Name)
                    and handler.value.id == "self"):
                yield class_node.name, handler.attr, node.lineno


def _collect_bindings():
    out = []
    for path in sorted(_GUI_DIR.glob("*.py")):
        if path.name == "__init__.py":
            continue
        for class_name, handler, lineno in _bindings_in(path):
            out.append((path.stem, class_name, handler, lineno))
    return out


BINDINGS = _collect_bindings()


def test_bindings_were_actually_found():
    """If the AST walk silently found nothing, the test below proves nothing."""
    assert len(BINDINGS) > 100, (
        f"only {len(BINDINGS)} Bind() call sites found across the GUI -- the "
        "AST walk has probably stopped matching."
    )


@pytest.mark.parametrize(
    "module_name,class_name,handler,lineno",
    BINDINGS,
    ids=[f"{m}.{c}.{h}" for m, c, h, _ in BINDINGS],
)
def test_bound_handler_exists(module_name, class_name, handler, lineno, wx_app):
    """A Bind() naming a method that no longer exists is a dead control.

    wx raises the AttributeError inside its own event dispatch and discards it,
    so the menu item or button simply stops responding with nothing in the log.
    """
    module = importlib.import_module(module_name)
    cls = getattr(module, class_name, None)
    if cls is None:
        pytest.skip(f"{class_name} is not exported from {module_name}")

    assert hasattr(cls, handler), (
        f"imagedescriber/{module_name}.py:{lineno} binds an event to "
        f"self.{handler}, but {class_name} has no such attribute. "
        "wx will swallow the AttributeError and the control will silently do "
        "nothing."
    )


def _assigned_names(node):
    """Every name bound anywhere inside a function body."""
    names = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
            names.add(child.id)
        elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if child is not node:
                names.add(child.name)
            names.update(a.arg for a in child.args.args)
            names.update(a.arg for a in child.args.kwonlyargs)
            if child.args.vararg:
                names.add(child.args.vararg.arg)
            if child.args.kwarg:
                names.add(child.args.kwarg.arg)
        elif isinstance(child, ast.Global):
            names.update(child.names)
        elif isinstance(child, (ast.Import, ast.ImportFrom)):
            for alias in child.names:
                names.add((alias.asname or alias.name).split(".")[0])
    return names


def _functions_using_an_unbound_logger(path: Path):
    return _unbound_logger_uses(path.read_text(encoding="utf-8"), str(path))


def _unbound_logger_uses(source: str, filename: str = "<source>"):
    """Functions that read `logger` without it existing in any reachable scope.

    Reproduces the CLAUDE.md incident exactly: `logger` present at module scope
    made every handler work; moved inside main(), every handler raised
    NameError with nothing printed, because wx discards handler exceptions.
    """
    tree = ast.parse(source, filename=filename)

    module_names = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            module_names.update(
                t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                module_names.add((alias.asname or alias.name).split(".")[0])
        elif isinstance(node, ast.Try):
            for sub in ast.walk(node):
                if isinstance(sub, ast.Assign):
                    module_names.update(
                        t.id for t in sub.targets if isinstance(t, ast.Name))
                elif isinstance(sub, (ast.Import, ast.ImportFrom)):
                    for alias in sub.names:
                        module_names.add(
                            (alias.asname or alias.name).split(".")[0])

    if "logger" in module_names:
        return []

    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        reads = any(
            isinstance(c, ast.Name) and c.id == "logger"
            and isinstance(c.ctx, ast.Load)
            for c in ast.walk(node)
        )
        if reads and "logger" not in _assigned_names(node):
            offenders.append((node.name, node.lineno))
    return offenders


_INCIDENT = '''
import logging

class Frame:
    def on_close(self, event):
        logger.info("closing")     # NameError -- swallowed by wx

def main():
    logger = logging.getLogger(__name__)   # moved here by the bad commit
    logger.info("starting")
'''

_FIXED = '''
import logging
logger = logging.getLogger(__name__)

class Frame:
    def on_close(self, event):
        logger.info("closing")
'''

_LOCAL_ONLY = '''
import logging

class Frame:
    def on_close(self, event):
        logger = logging.getLogger(__name__)
        logger.info("closing")
'''


def test_the_logger_detector_detects_the_incident():
    """A detector nobody has seen fail is not evidence of anything."""
    found = _unbound_logger_uses(_INCIDENT)
    assert [name for name, _ in found] == ["on_close"], found

    assert _unbound_logger_uses(_FIXED) == [], (
        "module-level logger wrongly reported as unbound"
    )
    assert _unbound_logger_uses(_LOCAL_ONLY) == [], (
        "a local logger assignment wrongly reported as unbound -- this is the "
        "shape ai_providers.py uses"
    )


@pytest.mark.parametrize("module_name", MODULES)
def test_logger_is_bound_wherever_it_is_used(module_name):
    """The exact eight-hour incident from CLAUDE.md, as an assertion.

    `logger = logging.getLogger(__name__)` was moved from module scope into
    main(). Every handler calling logger.info(...) then raised NameError --
    invisibly, because wx eats exceptions raised inside event handlers.
    on_close, on_process_single and the rest simply stopped responding.
    """
    offenders = _functions_using_an_unbound_logger(_GUI_DIR / f"{module_name}.py")
    assert not offenders, (
        f"imagedescriber/{module_name}.py reads `logger` in functions where "
        "it is neither a local nor a module-level name, so each call raises "
        "NameError. wx swallows that and the control silently does nothing:\n"
        + "\n".join(f"  line {line}: {name}()" for name, line in offenders)
    )
