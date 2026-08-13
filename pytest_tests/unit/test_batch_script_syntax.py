"""Guard against cmd.exe parenthesis parsing bugs in the build scripts.

cmd treats an unescaped ")" inside a parenthesized if/else block as CLOSING the
block, even when it appears in the middle of an echo argument. It does NOT
treat a "(" in argument position as opening one. So this line:

    if "%BUILD_ERRORS%"=="0" (
        ...
        echo   OK ImageDescriber.exe (with integrated Viewer Mode and tools)
    ) else (

silently terminates the block at that echo. Everything after it becomes a
top-level statement that runs unconditionally, and the "else" rebinds to the
wrong "if".

That is not hypothetical: it is why builditall_wx.bat printed "Ready for
distribution" and exited 0 after BOTH application builds had failed, packaging
a three-week-old idt.exe into the installer. A broken build looked like a good
one. The fix is to escape the parens as ^( and ^).
"""

import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]

# Scripts whose exit code gates a release. These must also fail loudly.
_RELEASE_SCRIPTS = [
    Path("BuildAndRelease/WinBuilds/builditall_wx.bat"),
    Path("BuildAndRelease/WinBuilds/build_installer.bat"),
]


#: The virtualenv name differs per platform -- `.winenv` on Windows, `.venv` on
#: macOS -- and pip ships .bat shims inside both. Excluding only one platform's
#: name means the scan reaches into installed packages on the other.
_NOT_OUR_SOURCE = {".claude", ".git", ".venv", ".winenv", "venv", "winenv",
                   "env", "site-packages", "node_modules"}


def _batch_files():
    for p in sorted(_ROOT.rglob("*.bat")):
        rel = p.relative_to(_ROOT)
        if _NOT_OUR_SOURCE & set(rel.parts):
            continue
        yield rel


def _read(path: Path) -> list[str]:
    raw = (_ROOT / path).read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("cp1252")
    return text.splitlines()


def _unescaped_paren_echoes(lines: list[str]) -> list[tuple[int, str]]:
    """Echo lines carrying an unescaped paren while inside a block."""
    depth = 0
    hits = []
    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        opens = 1 if re.search(r"\(\s*$", stripped) else 0
        closes = 1 if re.match(r"^\)", stripped) else 0
        if depth > 0 and re.match(r"(?i)^echo\b", stripped):
            body = stripped[4:]
            if re.search(r"(?<!\^)[()]", body):
                hits.append((i, stripped))
        depth = max(depth + opens - closes, 0)
    return hits


@pytest.mark.parametrize("rel", list(_batch_files()), ids=str)
def test_no_unescaped_parens_in_echo_inside_blocks(rel):
    hits = _unescaped_paren_echoes(_read(rel))
    assert not hits, (
        f"{rel}: echo with an unescaped ( or ) inside a parenthesized block. "
        "cmd will end the block early and silently change control flow. "
        "Escape them as ^( and ^).\n"
        + "\n".join(f"  line {n}: {t}" for n, t in hits)
    )


def _nested_nonzero_exits(lines: list[str]) -> list[tuple[int, str]]:
    """`exit /b N` (N != 0) issued from a block nested inside another block.

    cmd discards the exit code in that position. The script terminates and
    prints whatever it was about to print, but the caller is told it succeeded.
    One level of nesting is fine; two is not. Reduced case, verified 2026-07-28:

        if "%E%"=="0" ( if not exist x ( exit /b 1 ) )   -> caller sees 0
        if "%E%"=="0" ( exit /b 1 )                      -> caller sees 1
    """
    depth = 0
    hits = []
    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        if re.match(r"(?i)^(rem\b|::)", stripped):
            continue
        if depth >= 2 and re.match(r"(?i)^exit\s+/b\s+[1-9]", stripped):
            hits.append((i, stripped))
        if re.match(r"^\)\s*else\s*\(", stripped):
            pass                       # closes one and opens one: net zero
        elif stripped.startswith(")"):
            depth = max(depth - 1, 0)
        elif re.search(r"\(\s*$", stripped):
            depth += 1
    return hits


@pytest.mark.parametrize("rel", list(_batch_files()), ids=str)
def test_no_nonzero_exit_from_a_doubly_nested_block(rel):
    """A guard whose exit code cmd throws away is not a guard.

    This is how the missing-artifact checks added in 1488bb5 came to print
    "NOT FOUND" and still exit 0: each one sat inside `if not exist ... (`
    inside `if "%BUILD_ERRORS%"=="0" (`. Use flat control flow with goto and
    put every failing `exit /b` at top level.
    """
    hits = _nested_nonzero_exits(_read(rel))
    assert not hits, (
        f"{rel}: `exit /b N` inside a block nested in another block. cmd "
        "discards the exit code, so the caller sees success. Restructure with "
        "goto so the exit is at top level.\n"
        + "\n".join(f"  line {n}: {t}" for n, t in hits)
    )


def test_the_nested_exit_scanner_actually_detects_the_shape():
    """Guard the guard -- a scanner nobody has seen fire proves nothing."""
    broken = [
        'if "%E%"=="0" (',
        '    if not exist "x" (',
        '        exit /b 1',
        '    )',
        ')',
    ]
    assert [n for n, _ in _nested_nonzero_exits(broken)] == [3]

    ok_one_level = [
        'if "%E%"=="0" (',
        '    exit /b 1',
        ')',
    ]
    assert _nested_nonzero_exits(ok_one_level) == []

    ok_flat = [
        'if not exist "x" goto :missing',
        'exit /b 0',
        ':missing',
        'exit /b 1',
    ]
    assert _nested_nonzero_exits(ok_flat) == []

    # exit /b 0 in the same position is harmless -- success is the default.
    assert _nested_nonzero_exits([
        'if "%E%"=="0" (', '    if x (', '        exit /b 0', '    )', ')',
    ]) == []


@pytest.mark.parametrize("rel", _RELEASE_SCRIPTS, ids=str)
def test_release_scripts_exist(rel):
    assert (_ROOT / rel).is_file(), f"missing release script: {rel}"


def test_builditall_refuses_to_package_a_missing_executable():
    """A build that produces no exe must abort, not ship the previous one."""
    lines = _read(Path("BuildAndRelease/WinBuilds/builditall_wx.bat"))
    text = "\n".join(lines)

    for exe in ("idt\\dist\\idt.exe", "imagedescriber\\dist\\ImageDescriber.exe"):
        assert f'if not exist "{exe}"' in text, (
            f"builditall_wx.bat must check for {exe} and abort when it is absent"
        )

    # The guard is only meaningful if it actually exits non-zero.
    assert text.count("exit /b 1") >= 3, (
        "expected the missing-exe and copy-failure guards to exit /b 1"
    )


def test_builditall_clears_stale_executables_before_building():
    """Otherwise 'the exe exists' proves nothing about THIS build."""
    text = "\n".join(_read(Path("BuildAndRelease/WinBuilds/builditall_wx.bat")))
    assert 'del /Q "idt\\dist\\idt.exe"' in text
    assert 'del /Q "imagedescriber\\dist\\ImageDescriber.exe"' in text


def test_installer_success_message_names_the_real_artifact():
    """build_installer.bat announced a filename Inno Setup never produces."""
    iss = (_ROOT / "BuildAndRelease/WinBuilds/installer.iss").read_text(
        encoding="utf-8", errors="replace")
    m = re.search(r"^OutputBaseFilename=(.+)$", iss, re.MULTILINE)
    assert m, "installer.iss must define OutputBaseFilename"

    # Turn "ImageDescriptionToolkitSetup_{#MyFileVersion}" into a literal stem.
    stem = re.sub(r"\{#\w+\}", "", m.group(1)).strip()

    bat = "\n".join(_read(Path("BuildAndRelease/WinBuilds/build_installer.bat")))
    assert stem in bat, (
        f"build_installer.bat should report the real output name starting {stem!r}; "
        "otherwise its success message points at a file that does not exist"
    )


def test_builditall_calls_subscripts_with_explicit_relative_path():
    """Bare `call foo.bat` fails when NoDefaultCurrentDirectoryInExePath is set."""
    text = "\n".join(_read(Path("BuildAndRelease/WinBuilds/builditall_wx.bat")))
    assert "call .\\build_idt.bat" in text
    assert "call .\\build_imagedescriber_wx.bat" in text
    assert "call .\\build_chatapp.bat" in text


#: Every executable the installer ships. Adding an app means adding it here,
#: and the tests below then insist the whole chain knows about it.
SHIPPED_EXES = ["idt.exe", "ImageDescriber.exe", "IDTChat.exe"]


@pytest.mark.parametrize("exe", SHIPPED_EXES, ids=str)
def test_every_shipped_exe_is_built_and_packaged(exe):
    """Both packaging paths must copy every app.

    There are two: builditall_wx.bat packages inline for local builds, and
    package_all_windows.bat is what CI calls. IDTChat.exe was added to the
    first and missed in the second, which would have failed the CI installer
    build at Inno Setup -- installer.iss lists the file, so a missing copy is
    fatal rather than merely incomplete.
    """
    for script in ("builditall_wx.bat", "package_all_windows.bat"):
        text = "\n".join(_read(Path("BuildAndRelease/WinBuilds") / script))
        assert exe in text, f"{script} never mentions {exe}"


@pytest.mark.parametrize("exe", SHIPPED_EXES, ids=str)
def test_installer_ships_every_exe(exe):
    iss = (_ROOT / "BuildAndRelease/WinBuilds/installer.iss").read_text(
        encoding="utf-8", errors="replace")
    assert f"dist_all\\bin\\{exe}" in iss, (
        f"installer.iss has no [Files] entry for {exe}")


@pytest.mark.parametrize("exe", ["ImageDescriber.exe", "IDTChat.exe"], ids=str)
def test_gui_apps_get_a_start_menu_icon(exe):
    """A GUI app the user cannot find is a GUI app they do not have.

    idt.exe is excluded on purpose: it is a CLI and its Start menu entry opens
    a console rather than the exe directly.
    """
    iss = (_ROOT / "BuildAndRelease/WinBuilds/installer.iss").read_text(
        encoding="utf-8", errors="replace")
    group_icons = [ln for ln in iss.splitlines()
                   if ln.startswith('Name: "{group}\\') and exe in ln]
    assert group_icons, f"installer.iss has no Start menu icon for {exe}"
