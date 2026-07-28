#!/usr/bin/env python3
"""Enforce per-file coverage floors declared in pyproject.toml.

Issue #228. coverage.py can fail a run on a *global* percentage, but a global
number is satisfied by covering anything at all -- it says nothing about the
files where a gap has actually shipped a bug. The nine-month Ollama retry
defect lived in imagedescriber/ai_providers.py while the suite was fully green,
because exactly one test file imported that module and it only touched
_model_has_vision.

Floors live in [tool.idt.coverage-floors] in pyproject.toml, keyed by
repo-relative POSIX path.

Usage:
    pytest pytest_tests/ --cov --cov-report=json:coverage.json
    python tools/check_coverage_floors.py coverage.json

Exit status is 0 when every floor is met, 1 otherwise.
"""

from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_PYPROJECT = _ROOT / "pyproject.toml"

#: How far above its floor a file must rise before we ask you to raise the
#: floor. Wide enough that ordinary churn does not nag.
_SLACK = 8.0


def load_floors() -> dict[str, float]:
    with _PYPROJECT.open("rb") as handle:
        config = tomllib.load(handle)
    floors = config.get("tool", {}).get("idt", {}).get("coverage-floors", {})
    return {k: float(v) for k, v in floors.items()}


def load_measured(report_path: Path) -> dict[str, float]:
    with report_path.open(encoding="utf-8") as handle:
        report = json.load(handle)

    measured = {}
    for raw_path, data in report.get("files", {}).items():
        key = Path(raw_path).as_posix()
        measured[key] = data["summary"]["percent_covered"]
    return measured


def _resolve(path: str, measured: dict[str, float]):
    """Match a floor key against coverage.json's paths.

    coverage.json keys are whatever paths coverage saw, which differ between
    a run from the repo root and one from elsewhere. Match on suffix so the
    check does not silently pass because a key stopped matching.
    """
    if path in measured:
        return measured[path]
    candidates = [v for k, v in measured.items() if k.endswith(path)]
    if len(candidates) == 1:
        return candidates[0]
    return None


def main(argv: list[str]) -> int:
    report_path = Path(argv[1] if len(argv) > 1 else "coverage.json")
    if not report_path.exists():
        print(f"ERROR: {report_path} not found. Run pytest with "
              f"--cov-report=json:{report_path} first.", file=sys.stderr)
        return 1

    floors = load_floors()
    if not floors:
        print("ERROR: no [tool.idt.coverage-floors] in pyproject.toml",
              file=sys.stderr)
        return 1

    measured = load_measured(report_path)

    failures: list[str] = []
    missing: list[str] = []
    raise_me: list[str] = []
    ok: list[str] = []

    for path, floor in sorted(floors.items()):
        actual = _resolve(path, measured)
        if actual is None:
            missing.append(path)
            continue
        if actual + 1e-9 < floor:
            failures.append(f"  {path}: {actual:.2f}% < floor {floor:.2f}%")
        else:
            ok.append(f"  {path}: {actual:.2f}% (floor {floor:.2f}%)")
            if actual - floor > _SLACK:
                raise_me.append(
                    f"  {path}: {actual:.2f}% is {actual - floor:.1f} points "
                    f"above its {floor:.2f}% floor")

    print("Per-file coverage floors")
    print("=" * 72)
    for line in ok:
        print(f"PASS{line}")

    if raise_me:
        print("\nFloors worth raising (coverage has moved well past them):")
        for line in raise_me:
            print(line)

    if missing:
        print("\nERROR: these files have a floor but no coverage data.",
              file=sys.stderr)
        print("A floor that matches nothing enforces nothing -- fix the path "
              "or drop the entry.", file=sys.stderr)
        for path in missing:
            print(f"  {path}", file=sys.stderr)

    if failures:
        print("\nERROR: coverage fell below the floor:", file=sys.stderr)
        for line in failures:
            print(line, file=sys.stderr)
        print("\nAdd tests, or -- if the drop is deliberate -- lower the floor "
              "in pyproject.toml and say why in the commit message.",
              file=sys.stderr)

    if failures or missing:
        return 1

    print(f"\nAll {len(ok)} floors met.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
