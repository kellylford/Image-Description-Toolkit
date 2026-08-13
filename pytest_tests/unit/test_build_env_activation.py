"""Guard the per-app virtualenv activation in the Windows build scripts.

builditall_wx.bat calls the three sub-builds from a SINGLE cmd session, and
none of them deactivate. venv's activate.bat sets VIRTUAL_ENV for the rest of
that session, so build_idt.bat -- which runs first -- leaves idt\\.winenv active
for everything after it.

Each sub-build therefore must NOT skip activation on the strength of
"if not defined VIRTUAL_ENV". That guard makes the first environment activated
win for the whole run:

    build_idt.bat                -> activates idt\\.winenv          (has PyInstaller, no wx)
    build_imagedescriber_wx.bat  -> guard false, activation SKIPPED (builds against idt's env)
    build_chatapp.bat            -> guard false, activation SKIPPED (builds against idt's env)

Both wxPython apps then built against the CLI environment. The "import wx"
check inside build_imagedescriber_wx.bat failed and pip installed wxPython into
idt\\.winenv, polluting the CLI environment while imagedescriber\\.winenv stayed
untouched.

CI never caught this: a fresh runner has no .winenv at all, so the "if exist"
branch is false there and every app builds against system Python, which has the
full requirements.txt installed. The bug only reproduces on a developer
machine, which is exactly where it is least likely to be noticed.

Re-activating over an already-active venv is safe -- activate.bat does
"if defined _OLD_VIRTUAL_PATH set PATH=%_OLD_VIRTUAL_PATH%" before prepending
its own Scripts directory, so activations replace rather than stack.

Diagnosed 2026-08-13.
"""

from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]

#: (script, the activate.bat it must call). The chat app deliberately has no
#: environment of its own: its requirements are a strict subset of
#: ImageDescriber's, so it borrows that environment rather than forcing a
#: second wxPython download.
_SUB_BUILDS = [
    (Path("idt/build_idt.bat"), r".winenv\Scripts\activate.bat"),
    (Path("imagedescriber/build_imagedescriber_wx.bat"), r".winenv\Scripts\activate.bat"),
    (Path("chatapp/build_chatapp.bat"), r"..\imagedescriber\.winenv\Scripts\activate.bat"),
]


def _read(rel: Path) -> str:
    raw = (_ROOT / rel).read_bytes()
    for encoding in ("utf-8", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _code(rel: Path) -> str:
    """Script text with REM and :: comment lines removed.

    These scripts carry long comments explaining why the VIRTUAL_ENV guard must
    not come back -- comments that necessarily quote the very pattern this
    module scans for. Matching raw text would flag the documentation as if it
    were the defect, and the obvious "fix" would be to delete the explanation.
    """
    kept = []
    for line in _read(rel).splitlines():
        stripped = line.lstrip()
        low = stripped.lower()
        if low.startswith("rem ") or low == "rem" or stripped.startswith("::"):
            continue
        kept.append(line)
    return "\n".join(kept)


@pytest.mark.parametrize("script,_activate", _SUB_BUILDS, ids=lambda v: getattr(v, "name", ""))
def test_activation_is_not_gated_on_virtual_env(script: Path, _activate: str) -> None:
    """No sub-build may skip activation because some OTHER venv is active."""
    text = _code(script).lower()
    assert "not defined virtual_env" not in text, (
        f"{script} gates venv activation on VIRTUAL_ENV being unset. "
        "builditall_wx.bat runs all three sub-builds in one cmd session and "
        "build_idt.bat leaves idt\\.winenv active, so this guard silently "
        "builds this app against the wrong interpreter. Activate "
        "unconditionally -- re-activation is safe."
    )


@pytest.mark.parametrize("script,activate", _SUB_BUILDS, ids=lambda v: getattr(v, "name", ""))
def test_sub_build_activates_its_own_env(script: Path, activate: str) -> None:
    """Each sub-build must still actually call its own activate.bat."""
    text = _code(script)
    assert f"call {activate}" in text, (
        f"{script} no longer calls '{activate}'. Each sub-build is responsible "
        "for selecting its own environment; builditall_wx.bat does not do it."
    )


def test_orchestrator_does_not_activate_for_children() -> None:
    """The orchestrator must not try to fix this by activating centrally.

    One environment cannot serve all three apps: the CLI env deliberately
    omits wxPython. Activation belongs in the sub-builds, where the correct
    environment is known.
    """
    text = _code(Path("BuildAndRelease/WinBuilds/builditall_wx.bat")).lower()
    assert "activate.bat" not in text, (
        "builditall_wx.bat activates a virtualenv. It must not: each sub-build "
        "selects its own, and a single shared activation reintroduces exactly "
        "the cross-contamination this test exists to prevent."
    )
