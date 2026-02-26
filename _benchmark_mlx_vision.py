#!/usr/bin/env python3
"""
MLX vs Ollama Vision Benchmark
================================
Compares Apple Metal (MLX) vs Ollama for image description speed and quality.
Supports multiple prompt styles per run (narrative, colorful, etc.) loaded
directly from scripts/image_describer_config.json.

One-time setup (in the project venv):
    pip install mlx-vlm torch torchvision   # MLX/Metal side
    # pillow-heif is already installed (HEIC support)

Usage:
    # Default: testimages/, narrative prompt
    python3 _benchmark_mlx_vision.py

    # 5 real iPhone photos, narrative + colorful prompts
    python3 _benchmark_mlx_vision.py --pick 5 --prompts narrative colorful \\
        /Users/kellyford/Pictures/09

    # Ollama-only (skip Metal/MLX)
    python3 _benchmark_mlx_vision.py --no-mlx --prompts narrative colorful \\
        /Users/kellyford/Pictures/09

Models tested (defaults):
    Ollama:  moondream:latest            (fast baseline, 1.7 GB)
             granite3.2-vision:latest    (quality reference, 2.4 GB)
    MLX:     mlx-community/Qwen2-VL-2B-Instruct-4bit  (~1.5 GB, Metal GPU)
"""

import argparse
import base64
import io
import json
import sys
import tempfile
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent
DEFAULT_IMAGE_DIR = SCRIPT_DIR / "testimages"
CONFIG_PATH = SCRIPT_DIR / "scripts" / "image_describer_config.json"

# Fallback prompt texts (mirrors image_describer_config.json built-ins)
BUILTIN_PROMPTS: dict[str, str] = {
    "narrative": (
        "Provide a narrative description including objects, colors and detail. "
        "Avoid interpretation, just describe."
    ),
    "colorful": (
        "Give me a rich, vivid description emphasizing colors, lighting, and visual "
        "atmosphere. Focus on the palette, color relationships, and how colors "
        "contribute to the mood and composition."
    ),
    "concise": (
        "Describe this image concisely, including the main subjects, setting, "
        "key colors and lighting, and any notable activities or composition."
    ),
    "detailed": (
        "Describe this image in detail, including:\n"
        "- Main subjects/objects\n"
        "- Setting/environment\n"
        "- Key colors and lighting\n"
        "- Notable activities or composition\n"
        "Keep it comprehensive and informative for metadata."
    ),
    "artistic": (
        "Analyze this image from an artistic perspective, describing:\n"
        "- Visual composition and framing\n"
        "- Color palette and lighting mood\n"
        "- Artistic style or technique\n"
        "- Emotional tone or atmosphere\n"
        "- Subject matter and symbolism"
    ),
}

# Image optimisation matching image_describer.py: 1024px max, JPEG q85
MAX_DIMENSION = 1024
JPEG_QUALITY = 85

# Speedup verdict thresholds
THRESHOLD_WORTH_IT = 1.8
THRESHOLD_MARGINAL = 1.25

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".tiff", ".tif", ".webp"}


# ---------------------------------------------------------------------------
# Prompt loading
# ---------------------------------------------------------------------------

def load_prompts_from_config() -> dict[str, str]:
    """Return prompt_variations dict from scripts/image_describer_config.json."""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                cfg = json.load(f)
            return cfg.get("prompt_variations", {})
        except Exception:
            pass
    return {}


def resolve_prompt(name: str, config_prompts: dict[str, str]) -> str:
    """Return prompt text for `name` from config, built-ins, or treat as literal."""
    return config_prompts.get(name) or BUILTIN_PROMPTS.get(name) or name


# ---------------------------------------------------------------------------
# Image helpers
# ---------------------------------------------------------------------------

def _register_heic() -> None:
    """Register pillow-heif so PIL.Image.open() handles .HEIC/.HEIF files."""
    try:
        import pillow_heif
        pillow_heif.register_heif_opener()
    except ImportError:
        pass


def optimise_and_encode(image_path: Path) -> str:
    """Open image (incl. HEIC), resize to MAX_DIMENSION, return base64 JPEG string."""
    _register_heic()
    try:
        from PIL import Image
    except ImportError:
        sys.exit("ERROR: Pillow not installed.  pip install Pillow")

    with Image.open(image_path) as img:
        img = img.convert("RGB")
        w, h = img.size
        if max(w, h) > MAX_DIMENSION:
            scale = MAX_DIMENSION / max(w, h)
            img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=JPEG_QUALITY)
        return base64.b64encode(buf.getvalue()).decode("utf-8")


def to_jpeg_tempfile(image_path: Path) -> Path:
    """
    Write a resized JPEG of any supported image (incl. HEIC/PNG) to a temp
    file and return its Path.  MLX needs a real FS path, not base64.
    Caller must delete the file when done.
    """
    _register_heic()
    try:
        from PIL import Image
    except ImportError:
        sys.exit("ERROR: Pillow not installed.  pip install Pillow")

    with Image.open(image_path) as img:
        img = img.convert("RGB")
        w, h = img.size
        if max(w, h) > MAX_DIMENSION:
            scale = MAX_DIMENSION / max(w, h)
            img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        tmp = tempfile.NamedTemporaryFile(
            suffix=".jpg", delete=False, prefix="mlx_bench_"
        )
        img.save(tmp, format="JPEG", quality=JPEG_QUALITY)
        tmp.close()
        return Path(tmp.name)


# ---------------------------------------------------------------------------
# Image file discovery
# ---------------------------------------------------------------------------

def discover_images(paths: list[str], pick: int | None = None) -> list[Path]:
    """
    Resolve paths to a flat list of image files.  Directories are scanned
    (non-recursively).  If `pick` is set, take that many at even intervals.
    """
    found: list[Path] = []
    for p in paths:
        pp = Path(p)
        if pp.is_dir():
            for f in sorted(pp.iterdir()):
                if f.suffix.lower() in IMAGE_EXTENSIONS and f.is_file():
                    found.append(f)
        elif pp.is_file() and pp.suffix.lower() in IMAGE_EXTENSIONS:
            found.append(pp)
        else:
            print(f"  Warning: {p!r} not a recognised image file/directory — skipped")
    if pick and pick < len(found):
        step = len(found) / pick
        found = [found[int(i * step)] for i in range(pick)]
    return found


# ---------------------------------------------------------------------------
# Ollama runner
# ---------------------------------------------------------------------------

def run_ollama(model: str, image_b64: str, prompt: str) -> dict:
    """
    Returns:
        dict with keys: description, elapsed_s, tokens_out, tokens_per_s, error
    """
    try:
        import ollama as _ollama
    except ImportError:
        return _error_result("ollama package not installed. pip install ollama")

    t0 = time.perf_counter()
    try:
        response = _ollama.chat(
            model=model,
            messages=[{
                "role": "user",
                "content": prompt,
                "images": [image_b64],
            }],
        )
    except Exception as exc:
        return _error_result(str(exc))

    elapsed = time.perf_counter() - t0

    # ollama Python client returns an object; fall back to dict access
    try:
        msg = response.message.content
    except AttributeError:
        msg = response["message"]["content"]

    try:
        tokens_out = response.eval_count
    except AttributeError:
        tokens_out = response.get("eval_count", 0)

    tok_per_s = tokens_out / elapsed if elapsed > 0 else 0
    return {
        "description": (msg or "").strip(),
        "elapsed_s": elapsed,
        "tokens_out": tokens_out,
        "tokens_per_s": tok_per_s,
        "error": None,
    }


# ---------------------------------------------------------------------------
# MLX runner
# ---------------------------------------------------------------------------

def run_mlx(model_id: str, jpeg_path: Path, prompt: str,
            _cache: dict | None = None) -> dict:
    """
    Apple Metal inference via mlx-vlm.

    `jpeg_path` must be a JPEG on disk — use to_jpeg_tempfile() for HEIC/PNG.
    `_cache` is a mutable dict; pass the same one for every call so the model
    loads once and stays in unified memory (mirrors Ollama's behaviour).
    Returns same shape dict as run_ollama.
    """
    try:
        import mlx_vlm                              # noqa: F401
        from mlx_vlm import load, generate
        from mlx_vlm.prompt_utils import apply_chat_template
        from mlx_vlm.utils import load_config
    except ImportError:
        return _error_result(
            "mlx-vlm not installed.\n"
            "  To enable: pip install mlx-vlm\n"
            "  Then re-run this script."
        )

    # Transformers 5.x has a bug in video_processing_auto when PyTorch is
    # absent: video_processor_class_from_name() receives extractors=None and
    # then does `if class_name in extractors` which raises TypeError. Patch it
    # out so the fallback slow processor path continues normally.
    try:
        import transformers.models.auto.video_processing_auto as _vpa
        _orig_vpf = _vpa.video_processor_class_from_name
        def _safe_vpf(class_name):          # noqa: E306
            try:
                return _orig_vpf(class_name)
            except TypeError:
                return None
        _vpa.video_processor_class_from_name = _safe_vpf
    except Exception:
        pass  # Patch failed — proceed anyway; load() will surface any real error

    try:
        if _cache is not None and "model" in _cache:
            model = _cache["model"]
            processor = _cache["processor"]
            config = _cache["config"]
        else:
            print(f"\n    ↳ Loading MLX model into Metal (downloads ~1.5 GB on first run) …")
            t_load = time.perf_counter()
            model, processor = load(model_id)
            config = load_config(model_id)
            dt = time.perf_counter() - t_load
            print(f"    ↳ Loaded in {dt:.1f}s  (one-time cost — stays in Metal memory)")
            if _cache is not None:
                _cache.update(model=model, processor=processor, config=config)

        formatted_prompt = apply_chat_template(
            processor, config, prompt, num_images=1
        )

        t0 = time.perf_counter()
        output = generate(
            model,
            processor,
            formatted_prompt,
            image=[str(jpeg_path)],
            max_tokens=300,
            verbose=False,
        )
        elapsed = time.perf_counter() - t0

        # GenerationResult exposes proper token counts and tps
        description = (output.text or "").strip()
        tokens_out = output.generation_tokens
        tok_per_s = output.generation_tps

        return {
            "description": description,
            "elapsed_s": elapsed,
            "tokens_out": tokens_out,
            "tokens_per_s": tok_per_s,
            "error": None,
        }

    except Exception as exc:
        return _error_result(f"{type(exc).__name__}: {exc}")


def _error_result(msg: str) -> dict:
    return {
        "description": "",
        "elapsed_s": 0.0,
        "tokens_out": 0,
        "tokens_per_s": 0.0,
        "error": msg,
    }


# ---------------------------------------------------------------------------
# Check Ollama is running
# ---------------------------------------------------------------------------

def check_ollama_running() -> bool:
    try:
        import urllib.request
        urllib.request.urlopen("http://127.0.0.1:11434/", timeout=3)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

WIDE  = "═" * 72
DIVID = "─" * 72


def fmt_timing_row(label: str, result: dict) -> str:
    if result["error"]:
        return f"  {label:<30}  ERROR"
    return (
        f"  {label:<30}  "
        f"{result['elapsed_s']:>6.1f}s  "
        f"{result['tokens_out']:>5} tok  "
        f"{result['tokens_per_s']:>6.1f} tok/s"
    )


def print_description_block(label: str, result: dict, width: int = 72) -> None:
    prefix = f"  [{label}]  "
    indent = " " * len(prefix)
    if result["error"]:
        print(f"{prefix}ERROR: {result['error'][:100]}")
        return
    words = result["description"].split()
    lines: list[str] = []
    current: list[str] = []
    for w in words:
        trial = " ".join(current + [w])
        if current and len(indent + trial) > width:
            lines.append(" ".join(current))
            current = [w]
        else:
            current.append(w)
    if current:
        lines.append(" ".join(current))
    if not lines:
        return
    print(prefix + lines[0])
    for ln in lines[1:]:
        print(indent + ln)


def speedup_tag(ratio: float) -> str:
    if ratio >= THRESHOLD_WORTH_IT:
        return "✅ worth integrating"
    if ratio >= THRESHOLD_MARGINAL:
        return "⚠️  marginal"
    return "❌ no benefit vs Ollama"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="MLX (Metal) vs Ollama vision benchmark with prompt comparison",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "images",
        nargs="*",
        metavar="IMAGE_OR_DIR",
        help="Image files or a directory to scan.  Defaults to testimages/ if omitted.",
    )
    parser.add_argument(
        "--pick",
        type=int,
        default=None,
        metavar="N",
        help="Pick N images at evenly-spaced intervals from the set found.",
    )
    parser.add_argument(
        "--prompts",
        nargs="+",
        default=["narrative"],
        metavar="STYLE",
        help=(
            "Prompt style name(s) from image_describer_config.json "
            "(e.g. 'narrative colorful').  Default: narrative."
        ),
    )
    parser.add_argument(
        "--no-mlx",
        action="store_true",
        help="Skip MLX/Metal tests — run Ollama models only.",
    )
    parser.add_argument(
        "--ollama-models",
        nargs="+",
        default=["moondream:latest", "granite3.2-vision:latest"],
        metavar="MODEL",
        help="Ollama model tag(s) to test.",
    )
    parser.add_argument(
        "--mlx-model",
        default="mlx-community/Qwen2-VL-2B-Instruct-4bit",
        metavar="HF_REPO",
        help="HuggingFace repo ID for the MLX/Metal model.",
    )
    args = parser.parse_args()

    # ---------- resolve images ----------
    raw_paths = args.images if args.images else [str(DEFAULT_IMAGE_DIR)]
    images = discover_images(raw_paths, pick=args.pick)
    if not images and not args.images:
        images = discover_images([str(DEFAULT_IMAGE_DIR)])
    if not images:
        sys.exit(
            "No images found.  Pass image paths or a directory.\n"
            f"  Example: python3 {Path(__file__).name} --pick 5 --prompts narrative colorful "
            "/Users/kellyford/Pictures/09"
        )
    # Auto-limit only when using the default testimages dir with no explicit args
    if not args.images and not args.pick and len(images) > 3:
        images = images[:3]

    # ---------- resolve prompts ----------
    config_prompts = load_prompts_from_config()
    prompt_map: dict[str, str] = {}
    for name in args.prompts:
        prompt_map[name] = resolve_prompt(name, config_prompts)

    # ---------- preflight ----------
    print()
    print(WIDE)
    print("  MLX (Apple Metal) vs Ollama Vision Benchmark")
    print(WIDE)

    if not check_ollama_running():
        sys.exit(
            "\nERROR: Ollama is not running.\n"
            "  ollama serve\n"
            "  ollama pull moondream && ollama pull granite3.2-vision"
        )

    print(f"  Ollama:  running ✓")
    print(f"  Images:  {len(images)}")
    for img in images:
        print(f"           {img.name}  ({img.suffix.upper()})")
    print(f"  Prompts: {', '.join(prompt_map)}")
    print(f"  Ollama models: {', '.join(m.replace(':latest','') for m in args.ollama_models)}")
    if not args.no_mlx:
        print(f"  MLX model: {args.mlx_model}")
    print()

    # ---------- shared state ----------
    mlx_cache: dict = {}             # model stays in Metal memory across all calls
    perf: dict[str, dict] = {}       # key -> {elapsed: [], tps: []} for summary

    def _accum(key: str, r: dict) -> None:
        if r["error"]:
            return
        if key not in perf:
            perf[key] = {"elapsed": [], "tps": []}
        perf[key]["elapsed"].append(r["elapsed_s"])
        perf[key]["tps"].append(r["tokens_per_s"])

    mlx_short = args.mlx_model.split("/")[-1]
    speed_key   = f"Ollama/{args.ollama_models[0].replace(':latest','')}"
    quality_key = f"Ollama/{args.ollama_models[-1].replace(':latest','')}"
    mlx_key     = f"MLX/{mlx_short}"

    # ---------- main loop ----------
    for image_path in images:
        print(WIDE)
        print(f"  IMAGE: {image_path.name}")
        print(WIDE)

        try:
            image_b64 = optimise_and_encode(image_path)
        except Exception as exc:
            print(f"  Could not open {image_path.name}: {exc}  — skipped")
            continue

        jpeg_path: Path | None = None
        if not args.no_mlx:
            try:
                jpeg_path = to_jpeg_tempfile(image_path)
            except Exception as exc:
                print(f"  HEIC→JPEG conversion failed: {exc}  — MLX skipped this image")

        for prompt_name, prompt_text in prompt_map.items():
            print()
            print(f"  PROMPT STYLE: {prompt_name.upper()}")
            preview = prompt_text[:90]
            if len(prompt_text) > 90:
                preview += "…"
            print(f"  \"{preview}\"")
            print(DIVID)

            image_results: dict[str, dict] = {}

            # Ollama models
            for model in args.ollama_models:
                short = model.replace(":latest", "")
                key = f"Ollama/{short}"
                print(f"  {key:<37} …", end="", flush=True)
                r = run_ollama(model, image_b64, prompt_text)
                image_results[key] = r
                _accum(key, r)
                suffix = f"{r['elapsed_s']:.1f}s" if not r["error"] else "ERROR"
                print(f"\r  {key:<37} {suffix}")

            # MLX / Metal
            if not args.no_mlx and jpeg_path is not None:
                print(f"  {mlx_key:<37} …", end="", flush=True)
                r = run_mlx(args.mlx_model, jpeg_path, prompt_text, _cache=mlx_cache)
                image_results[mlx_key] = r
                _accum(mlx_key, r)
                suffix = f"{r['elapsed_s']:.1f}s" if not r["error"] else "ERROR"
                print(f"\r  {mlx_key:<37} {suffix}")
                if r["error"]:
                    print(f"    {r['error'][:110]}")

            # Timing table
            print()
            print(f"  {'Backend':<30}  {'Time':>7}  {'Tokens':>6}  {'Tok/s':>8}")
            print(f"  {'─'*30}  {'─'*7}  {'─'*6}  {'─'*8}")
            for key, r in image_results.items():
                print(fmt_timing_row(key, r))

            # Speedup notes
            if not args.no_mlx and mlx_key in image_results:
                mlx_r  = image_results[mlx_key]
                sp_r   = image_results.get(speed_key)
                qt_r   = image_results.get(quality_key)
                if not mlx_r["error"]:
                    if sp_r and not sp_r["error"] and sp_r["tokens_per_s"] > 0:
                        tps_ratio = mlx_r["tokens_per_s"] / sp_r["tokens_per_s"]
                        print(f"\n  Throughput vs {args.ollama_models[0].replace(':latest','')}: "
                              f"{tps_ratio:.1f}× more tok/s  (Metal GPU)")
                    if qt_r and not qt_r["error"] and qt_r["elapsed_s"] > 0:
                        wall_ratio = qt_r["elapsed_s"] / mlx_r["elapsed_s"]
                        print(f"  Wall-clock vs {args.ollama_models[-1].replace(':latest','')}: "
                              f"{wall_ratio:.1f}×  →  {speedup_tag(wall_ratio)}")

            # Descriptions (the whole point!)
            print()
            print("  ── Descriptions ──")
            for key, r in image_results.items():
                print()
                print_description_block(key, r)

        # Clean up temp JPEG
        if jpeg_path and jpeg_path.exists():
            try:
                jpeg_path.unlink()
            except Exception:
                pass

        print()

    # ===========================================================================
    # Summary
    # ===========================================================================
    print(WIDE)
    print("  SUMMARY  (averaged across all images and prompts)")
    print(WIDE)
    print(f"  {'Model':<34}  {'Avg time':>9}  {'Avg tok/s':>10}  {'Runs':>5}")
    print(f"  {'─'*34}  {'─'*9}  {'─'*10}  {'─'*5}")

    for key in sorted(perf):
        data = perf[key]
        n = len(data["elapsed"])
        avg_t   = sum(data["elapsed"]) / n
        avg_tps = sum(data["tps"]) / n
        print(f"  {key:<34}  {avg_t:>8.1f}s  {avg_tps:>10.1f}  {n:>5}")

    print()

    if mlx_key in perf and quality_key in perf:
        mlx_avg  = sum(perf[mlx_key]["elapsed"]) / len(perf[mlx_key]["elapsed"])
        qual_avg = sum(perf[quality_key]["elapsed"]) / len(perf[quality_key]["elapsed"])
        wall_ratio = qual_avg / mlx_avg
        print(f"  Quality-tier speedup (MLX vs {args.ollama_models[-1].replace(':latest','')})")
        print(f"    {wall_ratio:.2f}×  →  {speedup_tag(wall_ratio)}")

    if mlx_key in perf and speed_key in perf:
        mlx_tps  = sum(perf[mlx_key]["tps"]) / len(perf[mlx_key]["tps"])
        base_tps = sum(perf[speed_key]["tps"]) / len(perf[speed_key]["tps"])
        tps_ratio = mlx_tps / base_tps if base_tps > 0 else 0
        print(f"\n  Throughput (MLX vs {args.ollama_models[0].replace(':latest','')})")
        print(f"    {tps_ratio:.1f}× more tok/s — all inference on Metal GPU")
        print()
        print("  NOTE: MLX/Qwen2-VL produces more tokens per image than moondream.")
        print("  The tok/s rate is the fair apples-to-apples speed metric.")

    print()


if __name__ == "__main__":
    main()
