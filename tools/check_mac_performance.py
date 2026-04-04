#!/usr/bin/env python3
"""
check_mac_performance.py
Run this on each Mac to diagnose performance differences with cloud AI models.
Usage: python3 tools/check_mac_performance.py
"""

import sys
import platform
import subprocess
import time
import base64
import os
from pathlib import Path


def section(title):
    print(f"\n{'='*50}")
    print(f"  {title}")
    print('='*50)


def is_apple_silicon_mac():
    """Return True if the physical hardware is Apple Silicon."""
    try:
        result = subprocess.run(
            ["sysctl", "-n", "hw.optional.arm64"],
            capture_output=True, text=True
        )
        return result.stdout.strip() == "1"
    except Exception:
        return False


def check_architecture():
    section("Python & Architecture")
    print(f"  Python version : {sys.version}")
    print(f"  platform.machine: {platform.machine()}")
    print(f"  platform.processor: {platform.processor()}")

    machine = platform.machine()
    apple_silicon = is_apple_silicon_mac()
    print(f"  Apple Silicon hardware: {'Yes' if apple_silicon else 'No (Intel)'}")

    if machine == "arm64":
        print("  ✓ Running NATIVELY on Apple Silicon (arm64)")
    elif machine == "x86_64" and apple_silicon:
        print("  ✗ Running under ROSETTA 2 (x86_64 on Apple Silicon) — this adds overhead!")
        print("    Fix: reinstall Python as arm64 and rebuild your venv.")
    elif machine == "x86_64":
        print("  ✓ Running natively on Intel Mac (x86_64)")
    else:
        print(f"  ? Unknown architecture: {machine}")


def check_python_binary():
    section("Python Binary")
    py = sys.executable
    print(f"  Executable: {py}")
    try:
        result = subprocess.run(["file", py], capture_output=True, text=True)
        print(f"  file output: {result.stdout.strip()}")
    except FileNotFoundError:
        print("  (file command not available)")


def check_system_info():
    section("System Info")
    try:
        result = subprocess.run(
            ["system_profiler", "SPHardwareDataType"],
            capture_output=True, text=True, timeout=10
        )
        for line in result.stdout.splitlines():
            line = line.strip()
            if any(k in line for k in ("Model Name", "Model Identifier", "Chip", "Processor Name",
                                        "Processor Speed", "Total Number of Cores", "Memory")):
                print(f"  {line}")
    except Exception as e:
        print(f"  Could not read system profile: {e}")


def get_so_arch(package_dir):
    """Find a compiled .so extension in a package dir and check its architecture."""
    so_files = list(Path(package_dir).rglob("*.so"))
    if not so_files:
        return "pure Python (no compiled extensions)"
    # Check the first .so found
    try:
        result = subprocess.run(
            ["file", str(so_files[0])],
            capture_output=True, text=True
        )
        out = result.stdout
        if "arm64" in out and "x86_64" in out:
            return "universal (arm64 + x86_64)"
        elif "arm64" in out:
            return "arm64 (native Apple Silicon)"
        elif "x86_64" in out:
            return "x86_64"
    except Exception:
        pass
    return "unknown"


def check_key_packages():
    section("Key Package Architectures")
    apple_silicon = is_apple_silicon_mac()
    packages = ["PIL", "numpy", "ollama", "anthropic", "openai", "requests"]
    for pkg in packages:
        try:
            mod = __import__(pkg)
            pkg_dir = getattr(mod, "__file__", None)
            if pkg_dir:
                pkg_dir = str(Path(pkg_dir).parent)
                arch = get_so_arch(pkg_dir)
                # Flag x86_64 only as a problem on Apple Silicon
                if "x86_64" in arch and "arm64" not in arch and apple_silicon:
                    arch += "  ← Rosetta overhead!"
            else:
                arch = "built-in"
            print(f"  {pkg:<12} {arch}")
        except ImportError:
            print(f"  {pkg:<12} NOT INSTALLED")


def check_network_speed():
    section("Network Speed (small HTTPS fetch)")
    try:
        import urllib.request
        url = "https://httpbin.org/bytes/102400"  # 100 KB
        start = time.time()
        with urllib.request.urlopen(url, timeout=15) as r:
            data = r.read()
        elapsed = time.time() - start
        kb = len(data) / 1024
        print(f"  Downloaded {kb:.0f} KB in {elapsed:.2f}s  ({kb/elapsed:.0f} KB/s)")
    except Exception as e:
        print(f"  Network test failed: {e}")


def check_image_encode_speed():
    section("Image Base64 Encode Speed (simulates pre-send work)")
    # Simulate encoding a ~2MB image worth of bytes
    sample = os.urandom(2 * 1024 * 1024)
    start = time.time()
    for _ in range(10):
        base64.b64encode(sample)
    elapsed = time.time() - start
    print(f"  10x 2MB base64 encodes: {elapsed:.3f}s  ({elapsed/10*1000:.1f}ms each)")
    if elapsed / 10 > 0.05:
        print("  (slow — may indicate Rosetta overhead or memory pressure)")
    else:
        print("  (fast — looks good)")


def check_pil_decode_speed():
    section("PIL Image Decode Speed")
    try:
        from PIL import Image
        import io
        # Find any JPEG in testimages or current dir
        search_dirs = [
            Path(__file__).parent.parent / "testimages",
            Path(__file__).parent.parent,
            Path.cwd(),
        ]
        test_image = None
        for d in search_dirs:
            jpegs = list(d.glob("*.jpg")) + list(d.glob("*.jpeg")) + list(d.glob("*.JPG"))
            if jpegs:
                test_image = jpegs[0]
                break

        if test_image:
            data = test_image.read_bytes()
            start = time.time()
            for _ in range(20):
                img = Image.open(io.BytesIO(data))
                img.load()
            elapsed = time.time() - start
            print(f"  20x decode of {test_image.name}: {elapsed:.3f}s  ({elapsed/20*1000:.1f}ms each)")
        else:
            print("  No test JPEG found — skipping")
    except ImportError:
        print("  PIL not installed — skipping")


if __name__ == "__main__":
    print("\nMac Performance Diagnostic")
    print(f"Run time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    check_architecture()
    check_python_binary()
    check_system_info()
    check_key_packages()
    check_network_speed()
    check_image_encode_speed()
    check_pil_decode_speed()
    print("\n" + "="*50)
    print("  Done. Share this output to compare machines.")
    print("="*50 + "\n")
