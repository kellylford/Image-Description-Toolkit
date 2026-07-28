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


def _batch_files():
    for p in sorted(_ROOT.rglob("*.bat")):
        rel = p.relative_to(_ROOT)
        parts = set(rel.parts)
        if ".claude" in parts or ".winenv" in parts or "winenv" in parts:
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
