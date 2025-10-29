#!/usr/bin/env python3
"""
Versioning utilities for Image Description Toolkit.

Provides a single source of truth for composed version strings like:
    "3.5beta bld007"

Rules:
- Base version comes from the top-level VERSION file (or env IDT_BUILD_BASE)
- Build number comes from:
  1) Env IDT_BUILD_NUMBER (if set)
  2) CI: GITHUB_RUN_NUMBER (if set)
  3) Local counter at build/BUILD_TRACKER.json (per base version)

Also provides a logging banner to write at the start of any log we create.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

TRACKER_REL_PATH = Path("build") / "BUILD_TRACKER.json"


def _repo_root_from_scripts() -> Path:
    """Return repository root assuming this file is scripts/versioning.py."""
    here = Path(__file__).resolve()
    return here.parent.parent


def _exe_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return _repo_root_from_scripts()


def get_base_version() -> str:
    """Read base version (e.g., '3.5beta') from VERSION or env override."""
    # Env override takes precedence
    env_base = os.environ.get("IDT_BUILD_BASE")
    if env_base:
        return env_base.strip()

    # Try reading VERSION file (packaged in dist and present in repo)
    candidates = []
    if getattr(sys, 'frozen', False):
        # In PyInstaller onefile, data may be in _MEIPASS or beside the exe
        meipass = Path(getattr(sys, '_MEIPASS', _exe_dir()))
        candidates.extend([_exe_dir() / 'VERSION', meipass / 'VERSION'])
    else:
        # In dev, VERSION is at repo root
        candidates.append(_repo_root_from_scripts() / 'VERSION')

    for p in candidates:
        try:
            if p.exists():
                return p.read_text(encoding='utf-8').strip()
        except Exception:
            continue

    return "0.0.0dev"


def _load_tracker(path: Path) -> dict:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding='utf-8') or '{}')
    except Exception:
        pass
    return {}


def _save_tracker(path: Path, data: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding='utf-8')
    except Exception:
        # Non-fatal in dev; caller can still continue
        pass


def _coerce_int(value: str) -> Optional[int]:
    try:
        return int(str(value).strip())
    except Exception:
        return None


def get_build_number(base_version: Optional[str] = None, persist_local: bool = True) -> int:
    """Return the build number as an integer.

    Precedence:
    - IDT_BUILD_NUMBER env var
    - GITHUB_RUN_NUMBER (CI)
    - Local counter in build/BUILD_TRACKER.json (per base)
    """
    base = base_version or get_base_version()

    # Explicit override
    env_num = os.environ.get('IDT_BUILD_NUMBER')
    n = _coerce_int(env_num) if env_num else None
    if n is not None:
        return n

    # CI run number
    ci_num = os.environ.get('GITHUB_RUN_NUMBER')
    n = _coerce_int(ci_num) if ci_num else None
    if n is not None:
        return n

    # Local tracker
    tracker_path = _repo_root_from_scripts() / TRACKER_REL_PATH
    data = _load_tracker(tracker_path)
    current = _coerce_int(data.get(base, 0)) or 0
    current += 1
    if persist_local:
        data[base] = current
        _save_tracker(tracker_path, data)
    return current


def format_build(n: int) -> str:
    return f"bld{n:03d}"


def get_full_version() -> str:
    base = get_base_version()
    num = get_build_number(base)
    return f"{base} {format_build(num)}"


def get_git_info() -> Tuple[Optional[str], bool]:
    """Return (short_sha, is_dirty). None if git not available."""
    try:
        import subprocess
        root = _repo_root_from_scripts()
        sha = subprocess.check_output(
            ['git', 'rev-parse', '--short', 'HEAD'], cwd=str(root), stderr=subprocess.DEVNULL
        ).decode('utf-8', 'replace').strip()
        dirty = False
        try:
            status = subprocess.check_output(
                ['git', 'status', '--porcelain'], cwd=str(root), stderr=subprocess.DEVNULL
            ).decode('utf-8', 'replace')
            dirty = bool(status.strip())
        except Exception:
            pass
        return sha or None, dirty
    except Exception:
        return None, False


def is_frozen() -> bool:
    return bool(getattr(sys, 'frozen', False))


def log_build_banner(logger=None, stream=None) -> None:
    """Log a standardized build banner.

    If logger is provided, logs at INFO. Otherwise prints to stream or stdout.
    """
    base = get_base_version()
    # Do not increment counter for logging-only calls; display next number without persisting
    # Use env/GH number if set; else peek at tracker without increment
    num = None
    env_num = os.environ.get('IDT_BUILD_NUMBER') or os.environ.get('GITHUB_RUN_NUMBER')
    n = _coerce_int(env_num) if env_num else None
    if n is not None:
        num = n
    else:
        # Peek current value without bump (read tracker and +1 only for display)
        tracker_path = _repo_root_from_scripts() / TRACKER_REL_PATH
        data = _load_tracker(tracker_path)
        current = _coerce_int(data.get(base, 0)) or 0
        num = current + 1

    full = f"{base} {format_build(num)}"
    sha, dirty = get_git_info()
    mode = 'Frozen' if is_frozen() else 'Dev'
    ts = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%SZ')

    lines = [
        "Image Description Toolkit",
        f"Version: {full}",
        f"Commit: {sha or 'unknown'}{' (dirty)' if dirty else ''}",
        f"Mode: {mode}",
        f"Start: {ts} UTC",
    ]

    msg = "\n".join(lines)
    if logger is not None:
        try:
            logger.info(msg)
        except Exception:
            pass
    else:
        out = stream or sys.stdout
        try:
            out.write(msg + "\n")
            out.flush()
        except Exception:
            pass
