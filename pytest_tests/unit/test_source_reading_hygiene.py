"""Reading a source file without naming an encoding is a Windows time bomb.

Issue #228, P3. Several tests called `read_text()` with no `encoding=`. On
Windows that resolves to the locale codepage -- cp1252 here -- not UTF-8.
Three were fixed during the retry-bug work; one had been failing outright and
the rest passed only by luck.

The luck is worth spelling out, because it explains why this kind of bug sits
undetected for months. cp1252 decodes 251 of 256 possible bytes. Only 0x81,
0x8d, 0x8f, 0x90 and 0x9d are undefined. A UTF-8 source file therefore decodes
without complaint under cp1252 almost always -- producing mojibake nobody
looks at -- and raises UnicodeDecodeError only when a multi-byte sequence
happens to contain one of those five bytes. Add an emoji or a box-drawing
character to a source file and a test that has passed for a year starts
failing, on Windows only, for no reason connected to the change.

So this is not a style rule. An unqualified read_text() is a test that will
fail later, on someone else's machine, for a reason that looks unrelated.
"""

import ast
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_TEST_DIR = _ROOT / "pytest_tests"

#: Path methods that read or write text. These names belong to pathlib alone,
#: so an attribute call is unambiguous.
_PATH_TEXT_METHODS = {"read_text", "write_text"}

#: Only the BUILT-IN open() is checked, never `something.open(...)`. The
#: codebase has Project.open() and Workspace.open(), which are domain
#: constructors with nothing to do with file encodings.
_BUILTIN_READERS = {"open"}

#: Directories that are not this project's source.
#:
#: The virtualenv name differs per platform -- `.winenv` on Windows (see
#: CLAUDE.md), `.venv` on macOS -- and both live INSIDE imagedescriber/, which
#: is a package this scan walks. Excluding only the local one passes locally
#: and fails on the other platform: an earlier version of this file did exactly
#: that and reported 895 offenders from transformers, typer and wx on the macOS
#: runner. site-packages is listed too, so an unexpected venv layout cannot
#: reintroduce it.
_NOT_OUR_SOURCE = {
    "__pycache__", ".git", ".claude",
    ".venv", ".winenv", "venv", "winenv", "env",
    "site-packages", "node_modules", "build", "dist",
}


def _is_project_source(path: Path) -> bool:
    """True when ``path`` is one of this project's own source files.

    Matched against the path **relative to the repo root**, not its absolute
    parts. Those are different whenever the repo itself lives inside a directory
    that shares a name with an exclusion, and one of them is routine: Claude
    Code checks worktrees out under ``.claude/worktrees/<branch>/``, so every
    absolute path contains ``.claude``, every file was excluded, and the scan
    below found zero modules and failed -- in a worktree only, for a reason
    nothing in the failure message pointed at.

    The vacuity guard in :func:`test_there_are_tests_to_scan` is what caught
    that, and it is why this function must never be "fixed" by removing it.
    """
    try:
        relative = path.relative_to(_ROOT)
    except ValueError:
        # Outside the repo entirely -- judge it on the full path, since there is
        # no root to make it relative to.
        relative = path
    return not (_NOT_OUR_SOURCE & set(relative.parts))


def _test_sources():
    for path in sorted(_TEST_DIR.rglob("*.py")):
        if not _is_project_source(path):
            continue
        yield path.relative_to(_ROOT)


_SOURCES = list(_test_sources())


def _is_binary_mode(call: ast.Call) -> bool:
    """True for open(p, 'rb') / open(p, 'wb') -- bytes need no encoding."""
    modes = [a for a in call.args[1:2] if isinstance(a, ast.Constant)]
    modes += [k.value for k in call.keywords
              if k.arg == "mode" and isinstance(k.value, ast.Constant)]
    return any(isinstance(m.value, str) and "b" in m.value for m in modes)


def _unqualified_reads(source: str, filename: str):
    """Yield (lineno, snippet) for text reads with no encoding= argument."""
    tree = ast.parse(source, filename=filename)
    lines = source.splitlines()

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        if isinstance(node.func, ast.Attribute):
            if node.func.attr not in _PATH_TEXT_METHODS:
                continue
        elif isinstance(node.func, ast.Name):
            if node.func.id not in _BUILTIN_READERS:
                continue
            if _is_binary_mode(node):
                continue
        else:
            continue

        # read_bytes / write_bytes never reach here -- they are not listed.
        if any(k.arg == "encoding" for k in node.keywords):
            continue

        yield node.lineno, lines[node.lineno - 1].strip()


@pytest.mark.parametrize("rel", _SOURCES, ids=str)
def test_test_sources_name_an_encoding(rel):
    """Every text read/write in the suite must say what encoding it means."""
    path = _ROOT / rel
    offenders = list(_unqualified_reads(
        path.read_text(encoding="utf-8"), str(rel)))

    assert not offenders, (
        f"{rel}: text file access without encoding=. On Windows this uses the "
        "locale codepage (cp1252), which mis-decodes UTF-8 sources silently "
        "and raises only when the bytes 0x81/0x8d/0x8f/0x90/0x9d appear. Pass "
        "encoding='utf-8' explicitly.\n"
        + "\n".join(f"  line {n}: {t}" for n, t in offenders)
    )


def test_the_scanner_detects_and_exonerates_correctly():
    """Guard the guard."""
    bad = "from pathlib import Path\nPath('x').read_text()\n"
    assert [n for n, _ in _unqualified_reads(bad, "<bad>")] == [2]

    good = "from pathlib import Path\nPath('x').read_text(encoding='utf-8')\n"
    assert list(_unqualified_reads(good, "<good>")) == []

    binary = "open('x', 'rb').read()\n"
    assert list(_unqualified_reads(binary, "<binary>")) == []

    read_bytes = "from pathlib import Path\nPath('x').read_bytes()\n"
    assert list(_unqualified_reads(read_bytes, "<bytes>")) == []

    # Domain constructors named open() are not file access.
    domain = "Project.open(src)\nWorkspace.open(p)\n"
    assert list(_unqualified_reads(domain, "<domain>")) == []

    written = "from pathlib import Path\nPath('x').write_text('hi')\n"
    assert [n for n, _ in _unqualified_reads(written, "<write>")] == [2]


def test_there_are_tests_to_scan():
    assert len(_SOURCES) > 20, f"only found {len(_SOURCES)} test modules"


# ---------------------------------------------------------------------------
# The same trap in shipped code
# ---------------------------------------------------------------------------

_SHIPPED = ["idt_core", "imagedescriber", "cli"]


def test_shipped_code_names_an_encoding_too():
    """Shipped code had five, all now fixed, so the budget is zero.

    Two of the five were the worst possible case: writing a crash log and a
    chat-import traceback, each inside a bare `except: pass`. A traceback
    carrying one non-ASCII character would raise UnicodeEncodeError during the
    write, get swallowed, and destroy the diagnostic at exactly the moment it
    mattered. The other three read API-key files.
    """
    BUDGET = 0

    counts = {}
    scanned = []
    for package in _SHIPPED:
        for path in sorted((_ROOT / package).rglob("*.py")):
            if not _is_project_source(path):
                continue
            try:
                source = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            try:
                found = list(_unqualified_reads(source, str(path)))
            except SyntaxError:
                continue
            scanned.append(path)
            if found:
                counts[str(path.relative_to(_ROOT))] = len(found)

    strays = [p for p in scanned if "site-packages" in p.parts]
    assert not strays, (
        "the scan walked into installed packages, not this project's source: "
        f"{strays[:3]}. Add the directory to _NOT_OUR_SOURCE."
    )

    total = sum(counts.values())
    assert total <= BUDGET, (
        f"unqualified text reads in shipped code rose to {total} (budget "
        f"{BUDGET}). New code must pass encoding='utf-8'.\n"
        + "\n".join(f"  {f}: {n}" for f, n in sorted(counts.items()))
    )
