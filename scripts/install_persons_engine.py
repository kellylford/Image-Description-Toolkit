"""
Install Persons Engine — installs the optional facenet-pytorch + scikit-learn
dependencies so the face recognition feature works.

Frozen-exe strategy
-------------------
PyInstaller frozen exes can only import packages bundled at build time via
_MEIPASS.  torch and facenet-pytorch are far too large to bundle, so we
install them to a ``face_engine_packages/`` directory located next to the
frozen exe (e.g. ``C:\\idt\\face_engine_packages\\``).  ``face_engine.py``
injects that directory into ``sys.path`` at import time, making the packages
importable.

Dev-mode strategy
-----------------
Packages are installed normally into the active virtual environment with
``pip install``.

Called from:
  - CLI: idt persons install-engine
  - GUI: Tools → Install Face Recognition Engine

Progress is reported via a callback:  progress_cb(message: str, pct: int)
"""

import logging
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Packages to install (order matters: torch before facenet-pytorch)
_PACKAGES = [
    "torch",
    "torchvision",
    "facenet-pytorch",
    "scikit-learn",
    "numpy",
    "Pillow",  # usually already present, harmless to ensure
]

_DEFAULT_PROGRESS_CB = lambda msg, pct: print(f"[{pct:3d}%] {msg}")  # noqa: E731


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def get_packages_dir() -> Path:
    """Return the directory where face-engine packages are (or will be) installed.

    Frozen mode : ``<exe_dir>/face_engine_packages/``
    Dev mode    : not used — packages go into the active venv normally.
    """
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent / "face_engine_packages"
    # Dev mode: return a dummy path (install_engine won't use --target in dev mode)
    return Path(sys.prefix) / "face_engine_packages_unused"


def ensure_packages_on_path() -> None:
    """In frozen mode, prepend the face_engine_packages dir to sys.path.

    Called by face_engine.py and is_engine_available() before any torch import.
    Safe to call multiple times — only inserts once.
    """
    if not getattr(sys, 'frozen', False):
        return
    pkg_dir = str(get_packages_dir())
    if pkg_dir not in sys.path:
        sys.path.insert(0, pkg_dir)


def _find_python_for_install() -> Optional[Tuple[List[str], bool]]:
    """Return (base_command, uses_target) for running pip installs.

    Frozen mode: looks for a real Python interpreter on PATH that matches the
        version the frozen exe was built with, so that installed native
        extensions (numpy, torch) will load correctly.
        Command: ``python -m pip install --target <pkg_dir> <package>``
    Dev mode: uses the active venv pip / current interpreter
        ``pip install <package>``

    Returns (cmd_list, use_target) or None if no suitable interpreter found.
    """
    if getattr(sys, 'frozen', False):
        # The frozen exe was built with a specific Python version.
        # We MUST use the same version so compiled extensions (numpy, torch)
        # match the runtime ABI.
        required = sys.version_info[:2]  # e.g. (3, 12)
        maj, min_ = required

        # 1. Try Windows Python Launcher (py.exe) — most reliable way to get
        #    an exact version match without needing python3.12 on PATH.
        py_launcher = shutil.which("py")
        if py_launcher:
            try:
                r = subprocess.run(  # nosec B603
                    [py_launcher, f"-{maj}.{min_}", "-c", "print('ok')"],
                    capture_output=True, text=True, timeout=10, check=False,
                )
                if r.returncode == 0:
                    logger.info(
                        "_find_python_for_install: using py.exe launcher for Python %d.%d",
                        maj, min_,
                    )
                    return ([py_launcher, f"-{maj}.{min_}", "-m", "pip", "install"], True)
            except Exception:
                pass

        # 2. Try version-specific names first, then fall back to generic names.
        candidates = [
            f"python{maj}.{min_}",
            f"python{maj}",
            "python3",
            "python",
        ]

        # Collect all found interpreters, prefer exact version match
        best = None
        for name in candidates:
            found = shutil.which(name)
            if not found:
                continue
            found_path = Path(found).resolve()
            if found_path == Path(sys.executable).resolve():
                continue
            try:
                r = subprocess.run(  # nosec B603
                    [str(found_path), "-c",
                     "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
                    capture_output=True, text=True, timeout=10, check=False,
                )
                if r.returncode != 0:
                    continue
                found_ver = tuple(int(x) for x in r.stdout.strip().split("."))
                if found_ver == required:
                    # Exact match — use this interpreter
                    return ([str(found_path), "-m", "pip", "install"], True)
                if best is None:
                    # Keep as fallback only
                    best = (str(found_path), found_ver)
            except Exception:
                continue

        if best is not None:
            path, ver = best
            logger.warning(
                "No Python %d.%d found on PATH; falling back to Python %d.%d at %s. "
                "This may cause import errors if native extension versions differ.",
                maj, min_, ver[0], ver[1], path,
            )
            return ([path, "-m", "pip", "install"], True)

        return None

    # Dev mode: venv pip or current interpreter
    if sys.prefix != sys.base_prefix:
        # Inside a venv
        for subdir in ("Scripts", "bin"):
            for name in ("pip.exe", "pip"):
                candidate = Path(sys.prefix) / subdir / name
                if candidate.exists():
                    return ([str(candidate), "install", "--quiet"], False)

    # Dev: look for imagedescriber venv from project root
    project_root = Path(__file__).parent.parent
    for venv_name in (".winenv", "venv", ".venv"):
        for subdir in ("Scripts", "bin"):
            for pip_name in ("pip.exe", "pip"):
                candidate = project_root / "imagedescriber" / venv_name / subdir / pip_name
                if candidate.exists():
                    return ([str(candidate), "install", "--quiet"], False)

    # Dev fallback: python -m pip with current interpreter
    return ([sys.executable, "-m", "pip", "install", "--quiet"], False)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def is_engine_available() -> bool:
    """Return True if facenet-pytorch is importable.

    In frozen mode this injects the face_engine_packages dir into sys.path
    first, so the check reflects the actual post-install state.
    """
    ensure_packages_on_path()
    try:
        import facenet_pytorch  # noqa: F401
        import sklearn  # noqa: F401
        return True
    except Exception as exc:
        logger.debug("is_engine_available: %s: %s", type(exc).__name__, exc)
        return False


def install_engine(
    progress_cb: Optional[Callable[[str, int], None]] = None,
    reinstall: bool = False,
) -> bool:
    """Install facenet-pytorch and dependencies.

    In frozen mode, packages are installed to ``<exe_dir>/face_engine_packages/``
    using a system Python found on PATH.  In dev mode, packages are installed
    normally into the active virtual environment.

    Args:
        progress_cb: Called with (message, percent) throughout the install.
        reinstall: If True, re-download even if already installed.

    Returns:
        True on success, False if any package install failed.
    """
    if progress_cb is None:
        progress_cb = _DEFAULT_PROGRESS_CB

    if is_engine_available() and not reinstall:
        progress_cb("Face recognition engine already installed.", 100)
        return True

    result_tuple = _find_python_for_install()
    if result_tuple is None:
        progress_cb(
            "ERROR: No Python interpreter found on PATH. "
            "Install Python from python.org and ensure it is on your PATH, then retry.",
            100,
        )
        logger.error("install_engine: no Python interpreter found")
        return False

    base_cmd, use_target = result_tuple

    # In frozen mode, install into face_engine_packages/ next to the exe
    if use_target:
        pkg_dir = get_packages_dir()
        try:
            pkg_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            progress_cb(f"ERROR: Cannot create packages directory: {exc}", 100)
            logger.error("install_engine: mkdir failed: %s", exc)
            return False
        base_cmd = base_cmd + ["--target", str(pkg_dir)]
        logger.info("install_engine: using interpreter %s, target dir %s",
                    base_cmd[0], pkg_dir)

    if reinstall:
        base_cmd = base_cmd + ["--force-reinstall"]

    n = len(_PACKAGES)
    success = True

    for i, package in enumerate(_PACKAGES):
        pct_start = int(i / n * 90)
        pct_end = int((i + 1) / n * 90)
        progress_cb(f"Installing {package}...", pct_start)

        cmd = base_cmd + [package]
        try:
            result = subprocess.run(  # nosec B603 — intentional pip install
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )
            if result.returncode != 0:
                err = (result.stderr.strip() or result.stdout.strip() or
                       "(no output — try running pip manually to see the error)")
                progress_cb(f"ERROR installing {package}: {err[:300]}", pct_end)
                logger.error("pip install %s failed (exit %d):\nSTDERR: %s\nSTDOUT: %s",
                             package, result.returncode,
                             result.stderr.strip()[:500], result.stdout.strip()[:500])
                success = False
            else:
                progress_cb(f"{package} installed.", pct_end)
        except subprocess.TimeoutExpired:
            progress_cb(f"TIMEOUT installing {package} (>5 min)", pct_end)
            logger.error("pip install %s timed out", package)
            success = False
        except OSError as exc:
            progress_cb(f"ERROR running pip: {exc}", pct_end)
            logger.error("Could not run pip: %s", exc)
            success = False

    if success:
        progress_cb("Face recognition engine installation complete.", 100)
        logger.info("Face recognition engine installed successfully.")
    else:
        progress_cb(
            "Installation completed with errors. Check the application log for details.",
            100,
        )

    return success


def uninstall_engine(
    progress_cb: Optional[Callable[[str, int], None]] = None,
) -> bool:
    """Uninstall face recognition packages to reclaim disk space.

    In frozen mode, deletes the ``face_engine_packages/`` directory entirely.
    In dev mode, uses pip to uninstall facenet-pytorch and scikit-learn.
    """
    if progress_cb is None:
        progress_cb = _DEFAULT_PROGRESS_CB

    # Frozen mode: just remove the packages directory
    if getattr(sys, 'frozen', False):
        pkg_dir = get_packages_dir()
        if pkg_dir.exists():
            import shutil as _shutil
            try:
                _shutil.rmtree(pkg_dir)
                progress_cb("Face recognition packages removed.", 100)
                logger.info("Removed face_engine_packages dir: %s", pkg_dir)
            except OSError as exc:
                progress_cb(f"ERROR removing packages: {exc}", 100)
                logger.error("uninstall_engine: rmtree failed: %s", exc)
                return False
        else:
            progress_cb("Face recognition engine is not installed.", 100)
        return True

    # Dev mode: pip uninstall
    _packages_to_remove = ["facenet-pytorch", "scikit-learn"]
    result_tuple = _find_python_for_install()
    if result_tuple is None:
        progress_cb("ERROR: No Python interpreter found. Cannot uninstall.", 100)
        return False

    base_cmd, _ = result_tuple
    # Convert install base_cmd to uninstall form:
    # Replace "install --quiet" with "uninstall -y --quiet"
    if "install" in base_cmd:
        idx = base_cmd.index("install")
        base_cmd = base_cmd[:idx] + ["uninstall", "-y", "--quiet"]
    else:
        base_cmd = base_cmd + ["uninstall", "-y", "--quiet"]
    # Remove --target if present
    base_cmd = [x for x in base_cmd if not x.startswith("--target")]

    success = True
    n = len(_packages_to_remove)
    for i, package in enumerate(_packages_to_remove):
        pct = int((i + 1) / n * 100)
        progress_cb(f"Removing {package}...", pct)
        try:
            result = subprocess.run(  # nosec B603
                base_cmd + [package],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            if result.returncode != 0:
                logger.warning("pip uninstall %s: %s", package, result.stderr.strip())
        except Exception as exc:
            progress_cb(f"Error removing {package}: {exc}", pct)
            success = False

    progress_cb("Done." if success else "Finished with errors.", 100)
    return success


def get_installation_status() -> dict:
    """Return a dict describing what is/isn't installed."""
    ensure_packages_on_path()
    status = {}
    packages = {
        "torch": "torch",
        "torchvision": "torchvision",
        "facenet_pytorch": "facenet-pytorch",
        "sklearn": "scikit-learn",
        "numpy": "numpy",
        "PIL": "Pillow",
    }
    for import_name, pip_name in packages.items():
        try:
            mod = __import__(import_name)
            version = getattr(mod, "__version__", "?")
            status[pip_name] = {"installed": True, "version": version}
        except Exception as exc:
            logger.warning("Import check failed for %s: %s: %s",
                           import_name, type(exc).__name__, exc)
            status[pip_name] = {"installed": False, "version": None}
    return status


if __name__ == "__main__":
    # Allow running directly: python install_persons_engine.py
    import argparse

    parser = argparse.ArgumentParser(description="Install IDT face recognition engine")
    parser.add_argument("--reinstall", action="store_true", help="Force reinstall")
    parser.add_argument("--status", action="store_true", help="Show install status")
    parser.add_argument("--uninstall", action="store_true", help="Uninstall engine")
    args = parser.parse_args()

    if args.status:
        for pkg, info in get_installation_status().items():
            mark = "✓" if info["installed"] else "✗"
            ver = f" v{info['version']}" if info["version"] else ""
            print(f"  {mark} {pkg}{ver}")
    elif args.uninstall:
        uninstall_engine()
    else:
        install_engine(reinstall=args.reinstall)
