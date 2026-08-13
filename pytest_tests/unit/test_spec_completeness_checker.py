"""The spec checker itself, and the two ways it can quietly stop working.

BuildAndRelease/check_spec_completeness.py guards a failure this repo keeps
hitting: a first-party module reachable only through a lazy import, absent from
a PyInstaller spec, working perfectly in development and failing solely in the
frozen build.

It had been dead for months before this file existed. It pointed at
``final_working.spec``, renamed long ago, and scanned ``scripts/`` for Python
that had been removed in 2a32e6d -- so it exited on a missing file, and had it
merely been repointed it would have iterated over zero modules and reported
success forever.

That is the shape of the risk, so the tests are about the checker's *ability to
fail*, not only its verdict:

* :func:`test_it_catches_a_removed_hidden_import` deletes a real entry from a
  real spec in a temporary copy and demands a non-zero exit. Without it, the
  lenient name matching that shipped in the first draft -- where the unrelated
  third-party ``'ollama'`` entry satisfied ``idt_core.providers.ollama`` --
  would have gone unnoticed and the checker would have been decorative.
* :func:`test_it_examines_a_meaningful_number_of_modules` fails if the walk
  collapses to nothing, which is exactly how the old one would have "passed".
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_CHECKER = _ROOT / "BuildAndRelease" / "check_spec_completeness.py"

sys.path.insert(0, str(_CHECKER.parent))
import check_spec_completeness as checker  # noqa: E402


def _run(cwd=None):
    return subprocess.run(
        [sys.executable, str(_CHECKER)],
        cwd=str(cwd or _ROOT),
        capture_output=True, text=True, errors="replace", timeout=120,
    )


# ---------------------------------------------------------------------------
# It runs, and it is not vacuous
# ---------------------------------------------------------------------------

def test_the_checker_exists_and_runs():
    """It was hard-coded to a file that no longer existed and exited at once."""
    proc = _run()
    assert "Spec file not found" not in proc.stdout
    assert "PYINSTALLER SPEC COMPLETENESS CHECK" in proc.stdout


def test_specs_are_currently_complete():
    proc = _run()
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "All specs complete." in proc.stdout


@pytest.mark.parametrize("app", checker.APPS, ids=lambda a: a.name)
def test_every_app_has_a_real_spec_and_entry_point(app):
    assert app.spec.is_file(), f"{app.name}: spec missing at {app.spec}"
    assert app.entry.is_file(), f"{app.name}: entry point missing at {app.entry}"


@pytest.mark.parametrize("app", checker.APPS, ids=lambda a: a.name)
def test_it_examines_a_meaningful_number_of_modules(app):
    """A walk that finds nothing would report success on any spec at all.

    This is the precise way the previous checker would have failed after a
    repoint: zero modules to iterate, so the loop body never ran.
    """
    everything, _ = checker.walk_imports(app)
    assert len(everything) >= 10, (
        f"{app.name}: only {len(everything)} first-party modules reached -- "
        "the import walk has probably broken"
    )


def test_all_three_apps_are_covered():
    names = {app.spec.name for app in checker.APPS}
    assert names == {"idt.spec", "imagedescriber_wx.spec", "chatapp.spec"}


# ---------------------------------------------------------------------------
# It can actually fail
# ---------------------------------------------------------------------------

def _lazy_declared_entry(app):
    """A module the spec declares *and* that is only reached lazily."""
    _, must_declare = checker.walk_imports(app)
    spec_text = app.spec.read_text(encoding="utf-8")
    for dotted in sorted(must_declare):
        if f"'{dotted}'" in spec_text:
            return dotted
    return None


def test_it_catches_a_removed_hidden_import(tmp_path):
    """Delete a real entry from a copy of the tree; the check must fail.

    Copies only what the checker reads, so the working tree is never touched.
    """
    app = next(a for a in checker.APPS if a.spec.name == "chatapp.spec")
    victim = _lazy_declared_entry(app)
    assert victim, "no lazily-imported declared module found to remove"

    import shutil

    sandbox = tmp_path / "repo"
    for part in ("BuildAndRelease", "chatapp", "idt_core", "shared", "cli",
                 "imagedescriber", "idt"):
        source = _ROOT / part
        if source.is_dir():
            shutil.copytree(source, sandbox / part,
                            ignore=shutil.ignore_patterns(
                                "__pycache__", "dist", "build", ".venv",
                                ".winenv", "*.exe", "*.app"))

    spec = sandbox / "chatapp" / "chatapp.spec"
    text = spec.read_text(encoding="utf-8")
    trimmed = re.sub(rf"^\s*'{re.escape(victim)}',\n", "", text, flags=re.MULTILINE)
    assert trimmed != text, f"could not remove {victim} from the spec copy"
    spec.write_text(trimmed, encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, str(sandbox / "BuildAndRelease" / "check_spec_completeness.py")],
        capture_output=True, text=True, errors="replace", timeout=120,
    )

    assert proc.returncode == 1, (
        f"removing {victim} from chatapp.spec did not fail the check:\n"
        + proc.stdout
    )
    assert victim in proc.stdout, "the report should name the missing module"


def test_an_unrelated_entry_does_not_satisfy_a_dotted_name():
    """'ollama' must not count as declaring 'idt_core.providers.ollama'.

    The first draft accepted any trailing component, so a spec listing the
    third-party SDK appeared to declare our module of the same leaf name. That
    made the check unable to fail on the very omission it exists to catch.
    """
    spec_text = "hiddenimports=['ollama', 'anthropic']"
    assert not checker.spec_declares(spec_text, "idt_core.providers.ollama", [])


def test_the_flat_spelling_is_still_accepted():
    """imagedescriber imports flat ('from data_models import ...') in frozen mode."""
    app = next(a for a in checker.APPS if a.spec.name == "imagedescriber_wx.spec")
    spec_text = "hiddenimports=['data_models']"
    assert checker.spec_declares(
        spec_text, "imagedescriber.data_models", app.flat_dirs)


# ---------------------------------------------------------------------------
# Classification rules
# ---------------------------------------------------------------------------

def test_a_guarded_optional_import_is_not_demanded(tmp_path):
    """try/except means the code already handles absence.

    idt_core/chat/mlx.py imports imagedescriber.ai_providers exactly this way,
    because the chat app deliberately does not bundle it.
    """
    module = tmp_path / "sample.py"
    module.write_text(
        "def go():\n"
        "    try:\n"
        "        from idt_core.chat import engine\n"
        "    except ImportError:\n"
        "        engine = None\n",
        encoding="utf-8",
    )
    found = checker._scan(module, [])
    assert found, "the import should still be discovered"
    assert all(guarded for _, _, guarded in found)


def test_a_module_level_import_is_not_demanded(tmp_path):
    """PyInstaller finds those itself; demanding them is noise."""
    module = tmp_path / "sample.py"
    module.write_text("from idt_core.chat import engine\n", encoding="utf-8")
    found = checker._scan(module, [])
    assert found
    assert all(not lazy for _, lazy, _ in found)


def test_a_lazy_unguarded_import_is_flagged(tmp_path):
    module = tmp_path / "sample.py"
    module.write_text(
        "def go():\n    from idt_core.chat import engine\n", encoding="utf-8")
    found = checker._scan(module, [])
    assert ("idt_core.chat", True, False) in found


def test_third_party_imports_are_ignored(tmp_path):
    module = tmp_path / "sample.py"
    module.write_text(
        "import wx\ndef go():\n    import anthropic\n", encoding="utf-8")
    assert checker._scan(module, []) == []
