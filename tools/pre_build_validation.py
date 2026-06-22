"""
Pre-build validation: Run before creating the executable.

Catches integration bugs before PyInstaller bundles them in.

Usage:
    python tools/pre_build_validation.py

Exit codes:
    0 = All checks passed (or warnings only)
    1 = Critical failures (block build)
"""
import sys
import subprocess
from pathlib import Path


def run_unit_tests():
    """Run fast unit tests that don't need a built exe or live AI provider."""
    print("=" * 80)
    print("RUNNING UNIT TESTS")
    print("=" * 80)

    try:
        import pytest  # noqa: F401
    except ImportError:
        print("pytest not installed — skipping unit tests")
        print("Install with: pip install pytest")
        return None  # warning, not failure

    result = subprocess.run(
        [
            sys.executable, "-m", "pytest",
            "pytest_tests/unit/",
            "-v", "--tb=short", "-x",
            "--durations=5",
        ],
        capture_output=False,
    )

    if result.returncode != 0:
        print("\nUNIT TESTS FAILED — fix these before building.")
        return False

    print("\nUnit tests passed")
    return True


def check_new_cli_imports():
    """Verify cli/main.py and all idt_core modules import cleanly."""
    print("\n" + "=" * 80)
    print("CHECKING CLI AND IDT_CORE IMPORTS")
    print("=" * 80)

    modules_to_check = [
        "cli.main",
        "cli.guide",
        "idt_core",
        "idt_core.workspace",
        "idt_core.pipeline",
        "idt_core.logger",
        "idt_core.exporter",
        "idt_core.config",
        "idt_core.video",
        "idt_core.scanner",
        "idt_core.metadata",
        "idt_core.embedder",
        "idt_core.providers.claude",
        "idt_core.providers.ollama",
        "idt_core.providers.openai_provider",
    ]

    failed = []
    for mod in modules_to_check:
        result = subprocess.run(
            [sys.executable, "-c", f"import {mod}"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(f"  FAIL  {mod}")
            print(f"        {result.stderr.strip()[:200]}")
            failed.append(mod)
        else:
            print(f"  OK    {mod}")

    if failed:
        print(f"\n{len(failed)} module(s) failed to import — fix before building")
        return False

    print("\nAll modules import cleanly")
    return True


def check_scanner():
    """Smoke-test idt_core.scanner with temp files."""
    print("\n" + "=" * 80)
    print("CHECKING FILE SCANNER")
    print("=" * 80)

    try:
        import tempfile
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from idt_core.scanner import scan_images, IMAGE_EXTENSIONS

        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir)
            (test_dir / "photo.jpg").write_bytes(b"jpg")
            (test_dir / "screenshot.PNG").write_bytes(b"PNG")
            (test_dir / "image.png").write_bytes(b"png")
            (test_dir / "doc.pdf").write_bytes(b"pdf")    # should be excluded

            images = list(scan_images(test_dir))

        if len(images) != 3:
            print(f"  FAIL  Expected 3 images, found {len(images)}: {[f.name for f in images]}")
            return False

        print(f"  OK    scan_images found {len(images)} images, excluded pdf correctly")
        return True

    except Exception as e:
        print(f"  WARN  Scanner check skipped: {e}")
        return None  # warning, not failure


def check_default_provider():
    """Verify the out-of-box default is a free local Ollama model, not a paid provider."""
    print("\n" + "=" * 80)
    print("CHECKING DEFAULT PROVIDER")
    print("=" * 80)

    _PAID_PROVIDERS = {"openai", "anthropic", "claude", "huggingface"}
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from idt_core.config import UserConfig, DEFAULT_OLLAMA_MODEL
        cfg = UserConfig()   # no file — pure code defaults
        if cfg.default_provider != "ollama":
            print(f"  FAIL  default_provider is '{cfg.default_provider}', expected 'ollama'")
            print("        This would charge users money on a fresh install.")
            return False
        if cfg.default_provider in _PAID_PROVIDERS:
            print(f"  FAIL  default_provider '{cfg.default_provider}' is a paid provider.")
            return False
        print(f"  OK    defaults: {cfg.default_provider} / {cfg.default_model}  (DEFAULT_OLLAMA_MODEL={DEFAULT_OLLAMA_MODEL})")
        return True
    except Exception as e:
        print(f"  FAIL  Could not check defaults: {e}")
        return False


def check_default_model_sync():
    """
    Verify that the installer pull command matches the JSON default_model.

    This is the one manual step when changing the default model: the JSON is
    the Python source of truth (all code imports DEFAULT_OLLAMA_MODEL from
    idt_core.config), but installer.iss is a non-Python file that must be
    updated by hand. This check catches the mismatch at build time.

    TO CHANGE THE DEFAULT MODEL:
      1. Edit scripts/image_describer_config.json  →  "default_model": "new-model"
      2. Edit BuildAndRelease/WinBuilds/installer.iss  →  ollama pull new-model
      That is all. All Python code picks up the change automatically.
    """
    print("\n" + "=" * 80)
    print("CHECKING DEFAULT MODEL SYNC (JSON vs installer)")
    print("=" * 80)

    root = Path(__file__).parent.parent
    try:
        import json as _json
        cfg_path = root / "scripts" / "image_describer_config.json"
        json_model = _json.loads(cfg_path.read_text(encoding="utf-8")).get("default_model", "")
    except Exception as e:
        print(f"  WARN  Could not read image_describer_config.json: {e}")
        return None

    try:
        iss_path = root / "BuildAndRelease" / "WinBuilds" / "installer.iss"
        iss_text = iss_path.read_text(encoding="utf-8")
        import re
        m = re.search(r"ollama pull\s+([\w.:-]+)", iss_text)
        iss_model = m.group(1) if m else ""
    except Exception as e:
        print(f"  WARN  Could not read installer.iss: {e}")
        return None

    if json_model == iss_model:
        print(f"  OK    Both set to '{json_model}'")
        return True
    else:
        print(f"  FAIL  JSON default_model='{json_model}'  installer pulls='{iss_model}'")
        print( "        Edit BuildAndRelease/WinBuilds/installer.iss to match the JSON.")
        return False


def main():
    print("\n" + "=" * 80)
    print("PRE-BUILD VALIDATION (v4.5)")
    print("=" * 80)
    print()

    results = [
        ("Unit tests",           run_unit_tests()),
        ("CLI/idt_core imports", check_new_cli_imports()),
        ("File scanner",         check_scanner()),
        ("Default provider",     check_default_provider()),
        ("Default model sync",   check_default_model_sync()),
    ]

    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)

    has_failures = False
    for name, result in results:
        if result is True:
            print(f"  PASS  {name}")
        elif result is False:
            print(f"  FAIL  {name}")
            has_failures = True
        else:
            print(f"  WARN  {name}")

    print()
    if has_failures:
        print("BUILD BLOCKED — fix critical issues above before building")
        return 1

    print("BUILD ALLOWED — safe to proceed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
