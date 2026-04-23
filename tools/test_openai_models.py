"""
OpenAI Model Compatibility Test
================================
Tests all models listed in models/openai_models.py with 2 real images.
Uses the same API call pattern as OpenAIProvider.describe_image in ai_providers.py.

Usage:
  export OPENAI_API_KEY=sk-...
  python test_openai_models.py

Or pass key inline:
  OPENAI_API_KEY=sk-... python test_openai_models.py

Results are written to test_openai_results.txt alongside this file.
"""

import os
import sys
import base64
import time
import json
import traceback
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# Ensure project root is on the path so imports work
# ---------------------------------------------------------------------------
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    import openai
except ImportError:
    print("ERROR: openai package not installed.  pip install openai>=1.0.0")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Model list — single source of truth
# ---------------------------------------------------------------------------
try:
    from models.openai_models import OPENAI_MODELS
    print(f"Loaded {len(OPENAI_MODELS)} models from models/openai_models.py")
except ImportError as e:
    print(f"Could not import OPENAI_MODELS: {e}")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Test images — two real photos from the active workspace run
# ---------------------------------------------------------------------------
TEST_IMAGES = [
    Path("/Users/kellyford/Documents/ImageDescriptionToolkit/WorkspaceFiles/"
         "Europe_09_20260223/extracted_frames/IMG_4087/IMG_4087_0.00s.jpg"),
    Path("/Users/kellyford/Documents/ImageDescriptionToolkit/WorkspaceFiles/"
         "Europe_09_20260223/extracted_frames/"
         "mcp_video-17096_singular_display/mcp_video-17096_singular_display_0.00s.jpg"),
]

# Simple prompt — same style as the IDT "accessible" prompt style
TEST_PROMPT = (
    "Describe this image in 2-3 sentences suitable for a visually impaired person. "
    "Include key subjects, setting, and any text visible."
)

# ---------------------------------------------------------------------------
# API key resolution (mirrors OpenAIProvider.__init__)
# ---------------------------------------------------------------------------
def get_api_key() -> str:
    # 1. Env var
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if key:
        return key
    # 2. OneDrive key location
    onedrive_txt = Path("/Users/kellyford/Library/CloudStorage/OneDrive-Personal/idt/openai.txt")
    if onedrive_txt.exists():
        key = onedrive_txt.read_text().strip()
        if key:
            print(f"Using API key from {onedrive_txt}")
            return key
    # 3. openai.txt in project root
    txt = project_root / "openai.txt"
    if txt.exists():
        key = txt.read_text().strip()
        if key:
            print(f"Using API key from {txt}")
            return key
    # 3. scripts/image_describer_config.json
    cfg = project_root / "scripts" / "image_describer_config.json"
    if cfg.exists():
        try:
            data = json.loads(cfg.read_text())
            for k in ("OpenAI", "openai", "OPENAI"):
                v = data.get("api_keys", {}).get(k, "").strip()
                if v:
                    print("Using API key from image_describer_config.json")
                    return v
        except Exception:
            pass
    return ""

# ---------------------------------------------------------------------------
# Encode an image to base64 JPEG (same logic as OpenAIProvider.describe_image)
# ---------------------------------------------------------------------------
def encode_image(path: Path) -> str:
    """Return base64-encoded JPEG string for the given image path."""
    try:
        from PIL import Image
        import io
        img = Image.open(path)
        if img.mode in ("RGBA", "LA", "P"):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")
        max_dim = 1600
        if max(img.size) > max_dim:
            img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85, optimize=True)
        return base64.b64encode(buf.getvalue()).decode("utf-8")
    except ImportError:
        # No PIL — just send raw bytes
        return base64.b64encode(path.read_bytes()).decode("utf-8")

# ---------------------------------------------------------------------------
# Call a single model with one image
# ---------------------------------------------------------------------------
def test_model_image(client: openai.OpenAI, model: str, image_b64: str, image_label: str) -> dict:
    """
    Returns a result dict:
      status: "ok" | "error" | "empty"
      description: str (first 120 chars)
      full_description: str
      elapsed: float (seconds)
      tokens_in: int
      tokens_out: int
      finish_reason: str
      error: str (if status == "error")
    """
    result = {
        "model": model,
        "image": image_label,
        "status": "error",
        "description": "",
        "full_description": "",
        "elapsed": 0.0,
        "tokens_in": 0,
        "tokens_out": 0,
        "finish_reason": "",
        "error": "",
    }

    # Build request params (mirrors OpenAIProvider.describe_image exactly)
    params = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": TEST_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                    },
                ],
            }
        ],
    }

    # max_tokens vs max_completion_tokens split (same as production code)
    # Reasoning / newer models use max_completion_tokens; older GPT-4x use max_tokens
    if (model.startswith("gpt-5") or model.startswith("o1") or
            model.startswith("o3") or model.startswith("o4")):
        params["max_completion_tokens"] = 300
    else:
        params["max_tokens"] = 300

    t0 = time.time()
    try:
        response = client.chat.completions.create(**params)
        result["elapsed"] = time.time() - t0

        content = (response.choices[0].message.content or "").strip()
        result["finish_reason"] = response.choices[0].finish_reason or ""
        result["tokens_in"] = response.usage.prompt_tokens if response.usage else 0
        result["tokens_out"] = response.usage.completion_tokens if response.usage else 0
        result["full_description"] = content

        if content:
            result["status"] = "ok"
            result["description"] = content[:120].replace("\n", " ")
        else:
            result["status"] = "empty"
            result["description"] = "(empty response)"

    except openai.NotFoundError:
        result["elapsed"] = time.time() - t0
        result["error"] = "Model not found (404) — model ID may not exist"
        result["status"] = "error"
    except openai.AuthenticationError:
        result["elapsed"] = time.time() - t0
        result["error"] = "Authentication failed — check API key"
        result["status"] = "error"
    except openai.BadRequestError as e:
        result["elapsed"] = time.time() - t0
        result["error"] = f"Bad request: {e}"
        result["status"] = "error"
    except openai.RateLimitError as e:
        result["elapsed"] = time.time() - t0
        result["error"] = f"Rate limit: {e}"
        result["status"] = "error"
    except Exception as e:
        result["elapsed"] = time.time() - t0
        result["error"] = f"{type(e).__name__}: {e}"
        result["status"] = "error"

    return result

# ---------------------------------------------------------------------------
# Main test runner
# ---------------------------------------------------------------------------
def run_tests():
    api_key = get_api_key()
    if not api_key:
        print("\nERROR: No OpenAI API key found.")
        print("Set OPENAI_API_KEY environment variable or create openai.txt")
        sys.exit(1)

    masked = api_key[:8] + "..." + api_key[-4:]
    print(f"\nAPI key: {masked}")
    print(f"Models to test: {len(OPENAI_MODELS)}")
    print(f"Images per model: {len(TEST_IMAGES)}")
    print(f"Total API calls: {len(OPENAI_MODELS) * len(TEST_IMAGES)}\n")

    # Verify test images exist
    for img in TEST_IMAGES:
        if not img.exists():
            print(f"ERROR: Test image not found: {img}")
            sys.exit(1)
    print(f"Test images found:")
    for img in TEST_IMAGES:
        size_kb = img.stat().st_size // 1024
        print(f"  {img.name} ({size_kb} KB)")

    # Pre-encode images (do this once, not per model)
    print("\nEncoding test images...")
    t_enc = time.time()
    encoded_images = [encode_image(img) for img in TEST_IMAGES]
    print(f"Encoding done in {time.time()-t_enc:.1f}s  "
          f"(sizes: {', '.join(str(len(e)//1024)+' KB' for e in encoded_images)})\n")

    # Initialize client (no retries — we want raw errors for testing)
    client = openai.OpenAI(api_key=api_key, timeout=60, max_retries=0)

    # Run tests
    all_results = []
    banner = "=" * 70

    for i, model in enumerate(OPENAI_MODELS, 1):
        print(f"\n[{i}/{len(OPENAI_MODELS)}] {model}")
        print("-" * 50)

        model_results = []
        for j, (img_path, img_b64) in enumerate(zip(TEST_IMAGES, encoded_images), 1):
            label = img_path.name
            print(f"  Image {j}: {label} ... ", end="", flush=True)

            result = test_model_image(client, model, img_b64, label)
            model_results.append(result)
            all_results.append(result)

            # Single-line status
            if result["status"] == "ok":
                print(f"OK  {result['elapsed']:.1f}s  {result['tokens_out']} out-tokens")
                print(f"    \"{result['description']}\"")
            elif result["status"] == "empty":
                print(f"EMPTY  {result['elapsed']:.1f}s  finish={result['finish_reason']}")
            else:
                print(f"FAIL  {result['elapsed']:.1f}s  {result['error']}")

            # Small pause between calls to be polite to the API
            if not (i == len(OPENAI_MODELS) and j == len(TEST_IMAGES)):
                time.sleep(0.5)

    # ---------------------------------------------------------------------------
    # Summary table
    # ---------------------------------------------------------------------------
    print(f"\n\n{banner}")
    print("SUMMARY")
    print(banner)
    print(f"{'Model':<30} {'Img1':<8} {'Img2':<8} {'Verdict':<12} Notes")
    print("-" * 70)

    model_summaries = {}
    for result in all_results:
        m = result["model"]
        if m not in model_summaries:
            model_summaries[m] = []
        model_summaries[m].append(result)

    working = []
    broken = []
    missing = []

    for model in OPENAI_MODELS:
        results = model_summaries.get(model, [])
        statuses = [r["status"] for r in results]
        errors = [r.get("error", "") for r in results]

        s1 = statuses[0] if len(statuses) > 0 else "?"
        s2 = statuses[1] if len(statuses) > 1 else "?"

        icon1 = "✓" if s1 == "ok" else ("∅" if s1 == "empty" else "✗")
        icon2 = "✓" if s2 == "ok" else ("∅" if s2 == "empty" else "✗")

        all_ok = all(s == "ok" for s in statuses)
        any_ok = any(s == "ok" for s in statuses)
        all_missing = all("not found" in e.lower() or "404" in e for e in errors if e)
        all_empty = all(s == "empty" for s in statuses)

        if all_ok:
            verdict = "WORKING"
            working.append(model)
        elif any_ok:
            verdict = "PARTIAL"
            working.append(model)
        elif all_missing:
            verdict = "NOT FOUND"
            missing.append(model)
        elif all_empty:
            verdict = "EMPTY RSP"
            broken.append(model)
        else:
            verdict = "BROKEN"
            broken.append(model)

        # First unique error (truncated)
        note = ""
        for e in errors:
            if e:
                note = e[:45]
                break

        print(f"{model:<30} {icon1:<8} {icon2:<8} {verdict:<12} {note}")

    print(f"\n{'='*70}")
    print(f"WORKING ({len(working)}): {', '.join(working)}")
    print(f"NOT FOUND ({len(missing)}): {', '.join(missing)}")
    print(f"BROKEN/EMPTY ({len(broken)}): {', '.join(broken)}")
    print(f"{'='*70}")

    # ---------------------------------------------------------------------------
    # Write full results to file
    # ---------------------------------------------------------------------------
    output_file = project_root / "test_openai_results.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"OpenAI Model Test Results\n")
        f.write(f"Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Models tested: {len(OPENAI_MODELS)}\n\n")

        f.write(f"{'Model':<30} {'Img':<45} {'Status':<8} {'Sec':>5} {'Out':>5}  Description\n")
        f.write("-" * 120 + "\n")
        for r in all_results:
            desc = r["description"][:60].replace("\n", " ")
            err = r["error"][:60] if r["error"] else desc
            f.write(
                f"{r['model']:<30} {r['image']:<45} {r['status']:<8} "
                f"{r['elapsed']:>5.1f} {r['tokens_out']:>5}  {err}\n"
            )

        f.write(f"\n{'='*70}\n")
        f.write(f"WORKING: {', '.join(working)}\n")
        f.write(f"NOT FOUND: {', '.join(missing)}\n")
        f.write(f"BROKEN/EMPTY: {', '.join(broken)}\n")

    print(f"\nFull results written to: {output_file}\n")


if __name__ == "__main__":
    run_tests()
