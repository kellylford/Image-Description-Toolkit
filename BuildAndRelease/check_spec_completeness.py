#!/usr/bin/env python3
"""
PyInstaller spec completeness check.

Catches the failure mode CLAUDE.md documents and this repo keeps hitting: a
first-party module is reachable only through a lazy import, the spec never
names it, and it fails solely in the frozen executable -- the hardest place to
notice it.

    ModuleNotFoundError: No module named 'idt_core.chat.engine'

What is reported, and what is not
---------------------------------
Only imports that are **lazy and unguarded**:

* **lazy** -- inside a function body. PyInstaller walks module-level imports
  itself and bundles what it finds; it cannot see one that runs only when the
  function is called. Those are what ``hiddenimports`` exists for.
* **unguarded** -- not inside a ``try``. An import wrapped in try/except is
  already declared optional by the code that handles its absence. Demanding a
  hidden import for it would be wrong: ``idt_core/chat/mlx.py`` imports
  ``imagedescriber.ai_providers`` that way precisely because the chat app does
  not bundle it.

An earlier draft of this rewrite flagged every transitive module-level import
and produced pages of findings that were all fine. That is worth stating,
because a checker nobody reads is exactly how the previous one stayed dead.

What it replaced
----------------
The previous version checked that every ``.py`` file in ``scripts/`` appeared
in ``final_working.spec``. Both had ceased to exist: the spec was renamed, and
``scripts/`` was emptied of Python in 2a32e6d and now holds only JSON. It
exited immediately with "Spec file not found". Repointing it alone would have
been worse than leaving it broken -- it would have iterated over zero modules
and reported success every time.

Usage
-----
    python BuildAndRelease/check_spec_completeness.py

Exit status is 0 when every spec is complete, 1 otherwise, so it can gate a
build.
"""
from __future__ import annotations

import ast
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parent.parent

#: Import roots that live in this repo. Third-party packages are PyInstaller's
#: problem, not ours -- its hooks handle those.
FIRST_PARTY = ("idt_core", "cli", "shared", "imagedescriber", "chatapp")


@dataclass
class App:
    name: str
    spec: Path
    entry: Path
    #: Directories whose modules may be imported "flat" -- ``from data_models
    #: import ...`` rather than ``from imagedescriber.data_models import ...``.
    #: Mandatory in frozen mode, which is why the specs list both spellings.
    flat_dirs: List[Path] = field(default_factory=list)


APPS = [
    App("idt (CLI)", ROOT / "idt" / "idt.spec", ROOT / "cli" / "main.py"),
    App(
        "ImageDescriber",
        ROOT / "imagedescriber" / "imagedescriber_wx.spec",
        ROOT / "imagedescriber" / "imagedescriber_wx.py",
        flat_dirs=[ROOT / "imagedescriber"],
    ),
    App(
        "IDT Chat",
        ROOT / "chatapp" / "chatapp.spec",
        ROOT / "chatapp" / "chat_app_wx.py",
        flat_dirs=[ROOT / "chatapp"],
    ),
]


# ---------------------------------------------------------------------------
# Import discovery
# ---------------------------------------------------------------------------

#: (dotted name, is_lazy, is_guarded)
Found = Tuple[str, bool, bool]


class _ImportScanner(ast.NodeVisitor):
    """Records every import with enough context to judge whether it matters."""

    def __init__(self, module_package: str):
        self.module_package = module_package
        self.found: List[Found] = []
        self._in_function = 0
        self._in_try = 0

    def visit_FunctionDef(self, node):  # noqa: N802 - ast API naming
        self._in_function += 1
        self.generic_visit(node)
        self._in_function -= 1

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Try(self, node):  # noqa: N802 - ast API naming
        self._in_try += 1
        self.generic_visit(node)
        self._in_try -= 1

    def _record(self, dotted: str) -> None:
        if dotted:
            self.found.append((dotted, self._in_function > 0, self._in_try > 0))

    def visit_Import(self, node):  # noqa: N802 - ast API naming
        for alias in node.names:
            self._record(alias.name)

    def visit_ImportFrom(self, node):  # noqa: N802 - ast API naming
        if node.level:
            bits = self.module_package.split(".")
            if node.level > 1:
                bits = bits[: -(node.level - 1)] or bits
            base = ".".join(bits)
            self._record(f"{base}.{node.module}" if node.module else base)
        else:
            self._record(node.module or "")


def _module_path(dotted: str) -> Optional[Path]:
    """Locate a first-party module on disk, whether package or single file."""
    parts = dotted.split(".")
    as_module = ROOT.joinpath(*parts).with_suffix(".py")
    if as_module.is_file():
        return as_module
    as_package = ROOT.joinpath(*parts, "__init__.py")
    if as_package.is_file():
        return as_package
    return None


def _resolve_flat(name: str, flat_dirs: List[Path]) -> Optional[str]:
    """Map a flat import to its dotted form: data_models -> imagedescriber.data_models."""
    for directory in flat_dirs:
        if (directory / f"{name}.py").is_file():
            return f"{directory.name}.{name}"
    return None


def _normalise(dotted: str, flat_dirs: List[Path]) -> Optional[str]:
    """Return the first-party dotted name, or None if this is third-party."""
    if not dotted:
        return None
    root = dotted.split(".")[0]
    if root in FIRST_PARTY:
        return dotted
    return _resolve_flat(root, flat_dirs)


def _scan(path: Path, flat_dirs: List[Path]) -> List[Found]:
    """First-party imports in one file, each tagged lazy/guarded."""
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except (OSError, SyntaxError):
        return []

    try:
        package = path.parent.relative_to(ROOT).as_posix().replace("/", ".")
    except ValueError:
        package = ""

    scanner = _ImportScanner(package)
    scanner.visit(tree)

    results: List[Found] = []
    for dotted, lazy, guarded in scanner.found:
        normalised = _normalise(dotted, flat_dirs)
        if normalised:
            results.append((normalised, lazy, guarded))
    return results


def walk_imports(app: App) -> Tuple[Set[str], Set[str]]:
    """Traverse the import graph from the entry point.

    Returns ``(all_modules, must_declare)``. A module lands in must_declare
    only when *every* route to it is lazy and unguarded. If anything in the
    graph imports it at module level, PyInstaller's static analysis finds it
    there and bundles it, so a hidden import would be redundant.

    That distinction is what makes this usable. Without it the check reported
    ``idt_core.scanner`` as missing from the chat app, when
    ``idt_core/__init__.py`` imports it at module scope on line 9 and it is
    bundled either way.
    """
    everything: Set[str] = set()
    lazy_unguarded: Set[str] = set()
    statically_reachable: Set[str] = set()
    queue: List[Path] = [app.entry]
    visited: Set[Path] = set()

    while queue:
        current = queue.pop()
        if current in visited or not current.is_file():
            continue
        visited.add(current)

        for dotted, lazy, guarded in _scan(current, app.flat_dirs):
            everything.add(dotted)
            if lazy and not guarded:
                lazy_unguarded.add(dotted)
            elif not lazy:
                statically_reachable.add(dotted)
            target = _module_path(dotted)
            if target is not None:
                queue.append(target)

    return everything, lazy_unguarded - statically_reachable


# ---------------------------------------------------------------------------
# Spec inspection
# ---------------------------------------------------------------------------


def spec_declares(spec_text: str, dotted: str, flat_dirs: List[Path]) -> bool:
    """True if the spec names this module, in a spelling that actually applies.

    The bare name counts only for modules that are genuinely flat-importable --
    those living in one of the app's own directories, where the specs list both
    ``'imagedescriber.data_models'`` and ``'data_models'`` because frozen mode
    needs the flat form.

    Accepting the bare name unconditionally made this check useless: deleting
    ``'idt_core.providers.ollama'`` from a spec still passed, because the
    unrelated third-party ``'ollama'`` entry matched its last component. A
    checker that cannot fail is the failure mode this file was rewritten to
    escape, so the short form is only honoured where it is real.
    """
    for quote in ("'", '"'):
        if f"{quote}{dotted}{quote}" in spec_text:
            return True

    short = dotted.split(".")[-1]
    if _resolve_flat(short, flat_dirs) == dotted:
        for quote in ("'", '"'):
            if f"{quote}{short}{quote}" in spec_text:
                return True
    return False


def check(app: App) -> Tuple[List[str], int]:
    """Return (missing hidden imports, total first-party modules seen)."""
    if not app.spec.is_file():
        raise FileNotFoundError(f"spec not found: {app.spec}")
    if not app.entry.is_file():
        raise FileNotFoundError(f"entry point not found: {app.entry}")

    spec_text = app.spec.read_text(encoding="utf-8")
    everything, must_declare = walk_imports(app)
    missing = sorted(
        d for d in must_declare
        if not spec_declares(spec_text, d, app.flat_dirs)
    )
    return missing, len(everything)


def main() -> int:
    print("=" * 72)
    print("PYINSTALLER SPEC COMPLETENESS CHECK")
    print("=" * 72)
    print()

    failures: Dict[str, List[str]] = {}
    broken = False

    for app in APPS:
        rel_spec = app.spec.relative_to(ROOT).as_posix()
        try:
            missing, total = check(app)
        except FileNotFoundError as exc:
            print(f"[FAIL] {app.name}: {exc}")
            broken = True
            continue

        if missing:
            print(f"[FAIL] {app.name}: {len(missing)} lazy import(s) not declared "
                  f"in {rel_spec}")
            failures[app.name] = missing
        else:
            print(f"[ OK ] {app.name}: {total} first-party modules reached, "
                  f"every lazy import declared in {rel_spec}")

    if not failures and not broken:
        print()
        print("All specs complete.")
        print()
        return 0

    if failures:
        print()
        print("=" * 72)
        print("MISSING HIDDEN IMPORTS")
        print("=" * 72)
        for name, missing in failures.items():
            app = next(a for a in APPS if a.name == name)
            print()
            print(f"{name} -- add to hiddenimports in "
                  f"{app.spec.relative_to(ROOT).as_posix()}:")
            print()
            for dotted in missing:
                print(f"        '{dotted}',")

        print()
        print("-" * 72)
        print("These are imported inside a function, so PyInstaller's static")
        print("analysis cannot see them. They import fine in development and")
        print("fail only in the frozen build. If one is genuinely optional,")
        print("wrap it in try/except and this check will stop asking.")
        print("See CLAUDE.md, 'PyInstaller Frozen Mode Imports'.")
        print("=" * 72)
        print()

    return 1


if __name__ == "__main__":
    sys.exit(main())
