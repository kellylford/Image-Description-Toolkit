"""The coverage ratchet, and whether it can actually fail.

Issue #228, P0 item 2. Before this work pyproject pointed coverage at
`scripts/`, a directory emptied of Python in 2a32e6d. Every --cov run measured
zero files and reported success. A coverage gate that cannot fail is worse than
none, because it is quoted as evidence.

So the gate gets tested like anything else: the floors must name files that
exist, the checker must reject a report below a floor, and it must refuse to
pass when a floor matches nothing at all.
"""

import json
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_CHECKER = _ROOT / "tools" / "check_coverage_floors.py"

sys.path.insert(0, str(_ROOT / "tools"))
from check_coverage_floors import _resolve, load_floors  # noqa: E402


def _pyproject():
    with (_ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)


# ---------------------------------------------------------------------------
# The configuration itself
# ---------------------------------------------------------------------------

def test_coverage_source_points_at_directories_containing_python():
    """The original defect: source = ["scripts"], which holds no .py at all."""
    source = _pyproject()["tool"]["coverage"]["run"]["source"]
    assert source, "coverage has no source configured"

    for entry in source:
        directory = _ROOT / entry
        assert directory.is_dir(), f"coverage source {entry!r} is not a directory"
        modules = [p for p in directory.rglob("*.py")
                   if "__pycache__" not in p.parts and ".winenv" not in p.parts]
        assert modules, (
            f"coverage source {entry!r} contains no Python files, so measuring "
            "it produces a meaningless 0 -- exactly the state this repo was in."
        )


def test_a_global_floor_is_configured():
    report = _pyproject()["tool"]["coverage"]["report"]
    assert "fail_under" in report, (
        "without fail_under, code with zero tests cannot fail CI"
    )
    assert report["fail_under"] > 0


def test_addopts_does_not_force_coverage_on_every_run():
    """A global --cov would make targeted runs trip the floor.

    cli-validation.yml runs a single test file. If addopts turned coverage on
    unconditionally, that job would fail on fail_under for no useful reason and
    the floor would get deleted rather than raised.
    """
    addopts = _pyproject()["tool"]["pytest"]["ini_options"]["addopts"]
    assert "--cov=" not in addopts and "--cov " not in addopts


@pytest.mark.parametrize("path", sorted(load_floors()))
def test_every_floor_names_a_file_that_exists(path):
    """A floor whose path has drifted enforces nothing, silently."""
    assert (_ROOT / path).is_file(), (
        f"[tool.idt.coverage-floors] has an entry for {path!r}, which does not "
        "exist. Update the path or remove the entry -- as written it enforces "
        "nothing."
    )


def test_the_provider_layer_is_covered_by_a_floor():
    """The issue names these specifically: it is where the bug lived."""
    floors = load_floors()
    assert "imagedescriber/ai_providers.py" in floors
    provider_floors = [p for p in floors if p.startswith("idt_core/providers/")]
    assert len(provider_floors) >= 3, provider_floors


# ---------------------------------------------------------------------------
# The checker actually fails
# ---------------------------------------------------------------------------

def _write_report(tmp_path, files):
    report = {
        "files": {
            path: {"summary": {"percent_covered": pct}}
            for path, pct in files.items()
        }
    }
    path = tmp_path / "coverage.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    return path


def _run(report_path):
    return subprocess.run(
        [sys.executable, str(_CHECKER), str(report_path)],
        capture_output=True, text=True, timeout=60,
    )


def test_checker_passes_when_every_floor_is_met(tmp_path):
    floors = load_floors()
    report = _write_report(tmp_path, {p: v + 5 for p, v in floors.items()})

    proc = _run(report)

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "All" in proc.stdout


def test_checker_fails_when_one_file_drops_below_its_floor(tmp_path):
    floors = load_floors()
    values = {p: v + 5 for p, v in floors.items()}
    victim = "imagedescriber/ai_providers.py"
    values[victim] = floors[victim] - 0.5
    report = _write_report(tmp_path, values)

    proc = _run(report)

    assert proc.returncode == 1, (
        "the checker passed a file below its floor:\n" + proc.stdout
    )
    assert victim in proc.stderr


def test_checker_fails_when_a_floor_matches_no_measured_file(tmp_path):
    """The scripts/ failure mode: configured, matching nothing, reporting OK."""
    report = _write_report(tmp_path, {"some/other/module.py": 100.0})

    proc = _run(report)

    assert proc.returncode == 1, (
        "a floor that matched nothing was treated as satisfied:\n" + proc.stdout
    )
    assert "no coverage data" in proc.stderr


def test_checker_fails_on_a_missing_report(tmp_path):
    proc = _run(tmp_path / "does-not-exist.json")
    assert proc.returncode == 1
    assert "not found" in proc.stderr


def test_resolve_matches_paths_recorded_with_either_separator():
    """coverage.json records whatever separator the run produced."""
    measured = {"imagedescriber/ai_providers.py": 64.0}
    assert _resolve("imagedescriber/ai_providers.py", measured) == 64.0
    assert _resolve("ai_providers.py", measured) == 64.0
    assert _resolve("nope/absent.py", measured) is None


def test_resolve_refuses_an_ambiguous_suffix_match():
    """Two files with the same tail must not silently pick one."""
    measured = {"a/config.py": 10.0, "b/config.py": 90.0}
    assert _resolve("config.py", measured) is None
