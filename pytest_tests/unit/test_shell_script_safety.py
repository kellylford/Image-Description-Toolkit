"""Guard against silent-success failures in the macOS/shell build scripts.

The Windows counterpart (test_batch_script_syntax.py) covers cmd's parenthesis
trap. Shell scripts have their own way of reporting success after failing:

  * ((VAR++)) evaluates to the OLD value of VAR. When VAR is 0 the arithmetic
    result is 0, which bash reports as exit status 1. Under "set -e" that
    aborts the script mid-run. In builditall_macos.sh the first build failure
    killed the script before the second build ever started, and before the
    summary printed -- making the "ERRORS: N build failures" branch dead code.

  * A build step can exit 0 without emitting an artifact. builditall_macos.sh
    echoed "NOT FOUND" and then carried on to print "PACKAGING COMPLETE /
    Ready for DMG creation" and exit 0. Combined with never cleaning dist/,
    that shipped the previous run's binary in the DMG and called it a clean
    build -- the same defect the Windows script had.

Both were reproduced before being fixed.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_MACOS_ORCHESTRATOR = Path("BuildAndRelease/MacBuilds/builditall_macos.sh")


def _shell_scripts():
    for pattern in ("*.sh", "*.command"):
        for p in sorted(_ROOT.rglob(pattern)):
            rel = p.relative_to(_ROOT)
            parts = set(rel.parts)
            if ".claude" in parts or ".venv" in parts or ".winenv" in parts:
                continue
            yield rel


_SCRIPTS = list(_shell_scripts())

# ((VAR++)) / ((++VAR)) / ((VAR--))
_POST_INCREMENT = re.compile(r"\(\(\s*(?:\+\+|--)?[A-Za-z_]\w*\s*(?:\+\+|--)?\s*\)\)")
_SET_E = re.compile(r"^\s*set\s+-\w*e\w*\b", re.MULTILINE)


def _read(rel: Path) -> str:
    return (_ROOT / rel).read_text(encoding="utf-8", errors="replace")


@pytest.mark.parametrize("rel", _SCRIPTS, ids=str)
def test_no_bare_increment_under_set_e(rel):
    """((VAR++)) returns status 1 when VAR is 0, which `set -e` treats as fatal."""
    text = _read(rel)
    if not _SET_E.search(text):
        pytest.skip("script does not use set -e")

    offenders = [
        (i, line.strip())
        for i, line in enumerate(text.splitlines(), start=1)
        if _POST_INCREMENT.search(line) and not line.strip().startswith("#")
    ]
    assert not offenders, (
        f"{rel}: arithmetic increment under `set -e`. When the counter is 0 this "
        "returns exit status 1 and aborts the script. Use "
        "`VAR=$((VAR + 1))` instead.\n"
        + "\n".join(f"  line {n}: {t}" for n, t in offenders)
    )


@pytest.mark.parametrize("rel", _SCRIPTS, ids=str)
def test_shell_script_parses(rel):
    """A syntax error in a release script should fail here, not at release time."""
    bash = shutil.which("bash")
    if not bash:
        pytest.skip("bash not available")
    proc = subprocess.run(
        [bash, "-n", str(_ROOT / rel)],
        capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, f"{rel}: bash -n failed:\n{proc.stderr}"


def test_macos_orchestrator_clears_stale_artifacts_before_building():
    """Otherwise 'the artifact exists' proves nothing about THIS build."""
    text = _read(_MACOS_ORCHESTRATOR)
    assert 'rm -f  "idt/dist/idt"' in text or 'rm -f "idt/dist/idt"' in text, (
        "builditall_macos.sh must delete the previous idt binary before building"
    )
    assert 'rm -rf "imagedescriber/dist/ImageDescriber.app"' in text, (
        "builditall_macos.sh must delete the previous .app bundle before building"
    )


def test_macos_orchestrator_aborts_on_missing_artifact():
    """A build that emits nothing must not reach 'Ready for DMG creation'."""
    text = _read(_MACOS_ORCHESTRATOR)

    for probe in ('if [ ! -f "idt/dist/idt" ]',
                  'if [ ! -d "imagedescriber/dist/ImageDescriber.app" ]'):
        assert probe in text, f"builditall_macos.sh missing guard: {probe}"

    # The guards are only meaningful if they actually terminate the run.
    packaging = text.split("PACKAGING ALL APPLICATIONS", 1)[-1]
    assert packaging.count("exit 1") >= 2, (
        "expected both missing-artifact guards in the packaging block to exit 1"
    )


#: Every app the macOS DMG ships, as (build artifact path, staged name).
#: Adding an app means adding it here, and the tests below then insist the
#: whole macOS chain knows about it. The Windows equivalent lives in
#: test_batch_script_syntax.py; IDTChat was once added to one Windows
#: packaging script and missed in the other, which is the failure this
#: mirrors for macOS.
MACOS_APPS = [
    ("imagedescriber/dist/ImageDescriber.app", "ImageDescriber.app"),
    ("chatapp/dist/IDTChat.app", "IDTChat.app"),
]

_MACOS_DMG = Path("BuildAndRelease/MacBuilds/create_macos_dmg.sh")
_MACOS_VERIFY = Path("BuildAndRelease/MacBuilds/verify_macos_build_structure.sh")


@pytest.mark.parametrize("artifact,staged", MACOS_APPS, ids=lambda v: str(v))
def test_macos_orchestrator_builds_and_packages_every_app(artifact, staged):
    text = _read(_MACOS_ORCHESTRATOR)
    assert f'rm -rf "{artifact}"' in text, (
        f"builditall_macos.sh must clear the stale {staged} before building"
    )
    assert f'if [ ! -d "{artifact}" ]' in text, (
        f"builditall_macos.sh must abort when {staged} is missing"
    )
    assert staged in text, f"builditall_macos.sh never packages {staged}"


@pytest.mark.parametrize("artifact,staged", MACOS_APPS, ids=lambda v: str(v))
def test_dmg_stages_every_app(artifact, staged):
    """The DMG is the macOS deliverable: an app missing here does not ship."""
    text = _read(_MACOS_DMG)
    assert f'if [ ! -d "{artifact}" ]' in text, (
        f"create_macos_dmg.sh must check for {artifact}"
    )
    assert f'ditto "{artifact}"' in text, (
        f"create_macos_dmg.sh must ditto {staged} into the staging folder "
        "(ditto, not cp: it preserves code signatures)"
    )


def test_macos_structure_check_covers_the_chat_app():
    """verify_macos_build_structure.sh runs before the build; it must know the app."""
    text = _read(_MACOS_VERIFY)
    for probe in ("chatapp/chatapp.spec",
                  "chatapp/build_chatapp.sh",
                  "chatapp/chat_app_wx.py",
                  "chatapp/requirements.txt"):
        assert probe in text, f"verify_macos_build_structure.sh does not check {probe}"


def test_macos_orchestrator_still_reports_a_summary_after_a_failure():
    """The summary branch was unreachable while ((BUILD_ERRORS++)) aborted the run."""
    text = _read(_MACOS_ORCHESTRATOR)
    assert "count_error" in text, "expected the set -e-safe increment helper"
    assert "BUILD_ERRORS=$((BUILD_ERRORS + 1))" in text
    assert 'ERRORS: $BUILD_ERRORS build failures encountered' in text
