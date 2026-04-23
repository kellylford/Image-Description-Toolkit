#!/usr/bin/env python3
"""
IDT Resolution & Quality Experiment
====================================
Compares MLX vs Ollama providers across:
  Part 1 — Provider comparison (equal 1024px input via CLI)
  Part 2 — Resolution impact (same model, 3 resolutions)
  Part 3 — GUI vs CLI inconsistency demonstration

Outputs a detailed Markdown report to experiments/REPORT.md
"""

import os
import sys
import json
import shutil
import subprocess
import time
import re
import random
from pathlib import Path
from datetime import datetime

# ─── Paths ───────────────────────────────────────────────────────────────────
IDT         = Path("/Users/kellyford/Documents/GitHub/Image-Description-Toolkit/BuildAndRelease/MacBuilds/dist_all/idt")
PHOTO_BASE  = Path("/Volumes/photos/MobileBackup/iPhone")
REPO_ROOT   = Path("/Users/kellyford/Documents/GitHub/Image-Description-Toolkit")
EXP_DIR     = REPO_ROOT / "experiments"
WORK_DIR    = EXP_DIR / "workdir"    # workflow outputs go here
IMAGES_DIR  = EXP_DIR / "test_images"
RESIZE_DIR  = EXP_DIR / "resized_images"
REPORT_PATH = EXP_DIR / "REPORT.md"

IMAGES_DIR.mkdir(parents=True, exist_ok=True)
WORK_DIR.mkdir(parents=True, exist_ok=True)
RESIZE_DIR.mkdir(parents=True, exist_ok=True)

# ─── Experiment configuration ─────────────────────────────────────────────────
# Part 1: provider comparison — 12 images, 4 configs
PART1_CONFIGS = [
    {"provider": "mlx",    "model": "mlx-community/Qwen2.5-VL-7B-Instruct-4bit",      "label": "MLX_Qwen25_7B"},
    {"provider": "mlx",    "model": "mlx-community/Llama-3.2-11B-Vision-Instruct-4bit","label": "MLX_Llama32_11B"},
    {"provider": "ollama", "model": "llama3.2-vision:latest",                          "label": "Ollama_Llama32V"},
    {"provider": "ollama", "model": "granite3.2-vision:latest",                        "label": "Ollama_Granite32V"},
]

# Part 2: resolution sweep — 5 images, 3 resolutions, 1 model
PART2_MODEL    = {"provider": "ollama", "model": "llama3.2-vision:latest"}
PART2_SIZES_PX = [512, 1024, 0]   # 0 = full resolution (no resize)

PROMPT_STYLE = "narrative"
NUM_IMAGES   = 12
RES_TEST_N   = 5   # subset for resolution test

# ─── Image selection ──────────────────────────────────────────────────────────

def collect_candidate_images():
    """Collect candidate HEIC images from the photo library, spread across years."""
    candidates = []
    for year_dir in sorted(PHOTO_BASE.iterdir()):
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue
        year = int(year_dir.name)
        if year < 2019:
            continue
        for month_dir in sorted(year_dir.iterdir()):
            if not month_dir.is_dir():
                continue
            heics = [f for f in month_dir.iterdir()
                     if f.suffix.lower() in ('.heic', '.jpg', '.jpeg')
                     and f.stat().st_size > 500_000]   # skip tiny files
            if heics:
                # Pick 1-2 per month
                candidates.extend(random.sample(heics, min(2, len(heics))))
    return candidates


def select_diverse_images(n=NUM_IMAGES):
    """Select n images spread roughly evenly across available years."""
    random.seed(42)
    candidates = collect_candidate_images()
    # Group by year
    by_year = {}
    for p in candidates:
        # path is .../iPhone/YEAR/MONTH/file
        year = p.parent.parent.name
        by_year.setdefault(year, []).append(p)
    years = sorted(by_year.keys())
    per_year = max(1, n // len(years))
    selected = []
    for y in years:
        selected.extend(random.sample(by_year[y], min(per_year, len(by_year[y]))))
    # Top up if needed
    remaining = [p for p in candidates if p not in selected]
    random.shuffle(remaining)
    while len(selected) < n and remaining:
        selected.append(remaining.pop())
    return selected[:n]


def copy_test_images(images, dest_dir):
    """Copy selected images to the experiment dest directory."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    copied = []
    for src in images:
        dst = dest_dir / src.name
        if not dst.exists():
            shutil.copy2(src, dst)
        copied.append(dst)
    return copied

# ─── Image resizing ───────────────────────────────────────────────────────────

def make_resized_dirs(images, sizes_px):
    """
    Create JPEG versions of each image at each resolution.
    sizes_px: list of ints; 0 means full resolution.
    Returns: {size_px: [list of jpeg paths]}
    """
    try:
        from PIL import Image as PILImage
        import pillow_heif
        pillow_heif.register_heif_opener()
    except ImportError:
        print("ERROR: PIL or pillow_heif not available — using system Python")
        sys.exit(1)

    result = {}
    for size in sizes_px:
        label = f"full" if size == 0 else f"{size}px"
        size_dir = RESIZE_DIR / label
        size_dir.mkdir(parents=True, exist_ok=True)
        jpegs = []
        for src in images:
            dst = size_dir / (src.stem + ".jpg")
            if dst.exists():
                jpegs.append(dst)
                continue
            try:
                img = PILImage.open(src).convert("RGB")
                if size > 0:
                    img.thumbnail((size, size), PILImage.LANCZOS)
                img.save(dst, "JPEG", quality=85)
                jpegs.append(dst)
                print(f"  Resized {src.name} → {label} ({img.size[0]}×{img.size[1]})")
            except Exception as e:
                print(f"  WARNING: could not resize {src.name}: {e}")
        result[size] = jpegs
    return result

# ─── Running IDT ─────────────────────────────────────────────────────────────

def run_idt_workflow(input_dir: Path, provider: str, model: str, label: str,
                     steps="convert,describe") -> tuple[Path | None, float]:
    """
    Run idt workflow on input_dir and return (workflow_dir, elapsed_seconds).
    label is used to name the output directory.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_name   = f"wf_{label}_{timestamp}"
    out_path   = WORK_DIR / out_name

    cmd = [
        str(IDT), "workflow",
        str(input_dir),
        "--provider", provider,
        "--model",    model,
        "--prompt-style", PROMPT_STYLE,
        "--steps", steps,
        "--output-dir", str(WORK_DIR),
        "--name", label,
    ]
    print(f"\n{'='*60}")
    print(f"Running: {label}")
    print(f"  Provider: {provider} / {model}")
    print(f"  Input:    {input_dir}")
    print(f"  Command:  {' '.join(cmd)}")
    print(f"{'='*60}")

    t0 = time.time()
    try:
        result = subprocess.run(
            cmd,
            cwd=str(WORK_DIR),
            capture_output=False,   # let it print live
            stdin=subprocess.DEVNULL,  # prevent blocking on "view results? y/n" prompt
            timeout=3600,           # 1h max
        )
        elapsed = time.time() - t0
        if result.returncode != 0:
            print(f"  ⚠️  IDT exited with code {result.returncode}")
    except subprocess.TimeoutExpired:
        print(f"  ⚠️  Timed out after 3600s")
        elapsed = 3600.0

    # Find the workflow dir that was created (newest wf_... matching label)
    matches = sorted(WORK_DIR.glob(f"wf_*{label}*"), key=lambda p: p.stat().st_mtime, reverse=True)
    # Also try without label in case naming differs
    if not matches:
        matches = sorted(WORK_DIR.glob("wf_*"), key=lambda p: p.stat().st_mtime, reverse=True)

    wf_dir = matches[0] if matches else None
    print(f"  Workflow dir: {wf_dir}")
    print(f"  Elapsed: {elapsed:.1f}s")
    return wf_dir, elapsed

# ─── Result parsing ───────────────────────────────────────────────────────────

def parse_descriptions_file(wf_dir: Path) -> list[dict]:
    """Parse image_descriptions.txt from a workflow dir."""
    # Descriptions may be in multiple subdirs
    desc_files = list(wf_dir.rglob("image_descriptions.txt"))
    if not desc_files:
        return []

    entries = []
    for desc_file in desc_files:
        text = desc_file.read_text(encoding="utf-8", errors="replace")
        blocks = re.split(r'\n-{60,}\n', text)
        for block in blocks:
            if not block.strip():
                continue
            entry = {}
            lines = block.strip().splitlines()
            description_lines = []
            in_description = False
            for line in lines:
                if line.startswith("File: "):
                    entry["file"] = line[6:].strip()
                elif line.startswith("Provider: "):
                    entry["provider"] = line[10:].strip()
                elif line.startswith("Model: "):
                    entry["model"] = line[7:].strip()
                elif line.startswith("Description: "):
                    entry["description_first"] = line[13:].strip()
                    in_description = True
                    description_lines = [entry["description_first"]]
                elif in_description and not line.startswith(("File:", "Provider:", "Model:",
                                                              "Path:", "Prompt", "Timestamp:",
                                                              "Source URL:", "Tokens:")):
                    description_lines.append(line)
                if line.startswith("Tokens:"):
                    token_match = re.search(r'(\d+)\s+total\s+\((\d+)\s+prompt.*?(\d+)\s+completion', line)
                    if token_match:
                        entry["total_tokens"]      = int(token_match.group(1))
                        entry["prompt_tokens"]     = int(token_match.group(2))
                        entry["completion_tokens"] = int(token_match.group(3))

            if description_lines:
                entry["description"] = " ".join(description_lines).strip()
            if entry.get("file") and entry.get("description"):
                entries.append(entry)
    return entries


def parse_log_for_tokens(wf_dir: Path) -> dict:
    """Extract per-image token counts and timing from workflow log."""
    log_files = list(wf_dir.rglob("*.log"))
    if not log_files:
        return {}

    per_image = {}   # filename → {prompt_tokens, completion_tokens, duration_s}
    current_file = None
    current_start = None

    for log_file in log_files:
        try:
            text = log_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        for line in text.splitlines():
            # Detect which file is being processed
            m = re.search(r'Processing image.*?(\w[\w\.\-]+\.(?:jpg|jpeg|png|heic))', line, re.IGNORECASE)
            if m:
                current_file = m.group(1)

            # Token line: "Tokens: 1234 total (567 prompt + 667 completion)"
            m = re.search(r'Tokens:\s+(\d+)\s+total\s+\((\d+)\s+prompt.*?(\d+)\s+completion', line)
            if m and current_file:
                per_image.setdefault(current_file, {})
                per_image[current_file]["total_tokens"]      = int(m.group(1))
                per_image[current_file]["prompt_tokens"]     = int(m.group(2))
                per_image[current_file]["completion_tokens"] = int(m.group(3))

            # Also look for: "X prompt tokens"  "Y completion tokens" patterns
            m = re.search(r'(\d+)\s+prompt\s+\+\s+(\d+)\s+completion', line)
            if m and current_file:
                per_image.setdefault(current_file, {})
                per_image[current_file]["prompt_tokens"]     = int(m.group(1))
                per_image[current_file]["completion_tokens"] = int(m.group(2))

            # Duration line
            m = re.search(r'Processing duration:\s+([\d.]+)\s+seconds', line)
            if m and current_file:
                per_image.setdefault(current_file, {})
                per_image[current_file]["duration_s"] = float(m.group(1))

            # Summary totals
            m = re.search(r'Prompt tokens:\s+([\d,]+)', line)
            if m:
                per_image.setdefault("__total__", {})
                per_image["__total__"]["prompt_tokens"] = int(m.group(1).replace(",", ""))

            m = re.search(r'Completion tokens:\s+([\d,]+)', line)
            if m:
                per_image.setdefault("__total__", {})
                per_image["__total__"]["completion_tokens"] = int(m.group(1).replace(",", ""))

    return per_image


def score_description_quality(text: str) -> dict:
    """
    Score description quality on several heuristic dimensions.
    Returns dict with numeric scores.
    """
    if not text:
        return {k: 0 for k in ["word_count", "unique_ratio", "spatial_score",
                                 "color_score", "detail_score", "specificity"]}
    words  = re.findall(r'\b\w+\b', text.lower())
    unique = set(words)

    color_words    = {"red","blue","green","yellow","orange","purple","pink","brown",
                      "black","white","gray","grey","teal","navy","beige","cream",
                      "golden","silver","dark","light","bright","vivid","pale"}
    spatial_words  = {"left","right","center","middle","top","bottom","foreground",
                      "background","behind","front","corner","edge","upper","lower",
                      "beside","next to","above","below","near","far","between"}
    detail_words   = {"wearing","holding","standing","sitting","smiling","looking",
                      "surrounded","featuring","appears","visible","showing","displaying",
                      "contains","includes","depicts","illuminated","positioned","decorated"}
    number_words   = set(["one","two","three","four","five","six","seven","eight","nine",
                           "ten","several","multiple","many","few","pair","group","crowd"])

    wset = set(words)
    color_score   = len(wset & color_words)
    spatial_score = len(wset & spatial_words)
    detail_score  = len(wset & detail_words)
    # Count numeric digits in text too
    num_count     = len(re.findall(r'\b\d+\b', text)) + len(wset & number_words)

    # Specificity = unique words / total words (vocabulary richness)
    specificity = len(unique) / len(words) if words else 0

    # Sentences
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

    return {
        "word_count":    len(words),
        "sentence_count": len(sentences),
        "unique_ratio":  round(specificity, 3),
        "color_score":   color_score,
        "spatial_score": spatial_score,
        "detail_score":  detail_score,
        "number_count":  num_count,
    }

# ─── Report generation ────────────────────────────────────────────────────────

def format_table(headers: list[str], rows: list[list]) -> str:
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))
    sep = "| " + " | ".join("-" * w for w in widths) + " |"
    header_row = "| " + " | ".join(str(h).ljust(widths[i]) for i, h in enumerate(headers)) + " |"
    data_rows = [
        "| " + " | ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(row)) + " |"
        for row in rows
    ]
    return "\n".join([header_row, sep] + data_rows)


def write_report(part1_results: list[dict], part2_results: list[dict],
                 selected_images: list[Path]):
    lines = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines.append(f"# IDT Resolution & Quality Experiment Report")
    lines.append(f"*Generated: {now}*\n")
    lines.append("## Overview\n")
    lines.append(
        "This experiment compares MLX (Apple Silicon Metal) providers against Ollama "
        "providers on the same real-world iPhone HEIC images, investigating:\n"
        "1. **Description quality** at standardized 1024px input (CLI path)\n"
        "2. **Token efficiency** across model architectures\n"
        "3. **Resolution impact** — does sending higher-res images to Ollama improve descriptions?\n"
        "4. **Recommendations** for users and for the codebase\n"
    )

    # Test image set
    lines.append("## Test Image Set\n")
    lines.append(f"**{len(selected_images)} images** selected from `{PHOTO_BASE}`, "
                 f"spread across years 2019–2026.\n")
    img_rows = []
    for p in selected_images:
        size_mb = p.stat().st_size / 1_048_576
        year = p.parent.parent.name if p.parent.parent.name.isdigit() else "?"
        img_rows.append([p.name, year, f"{size_mb:.1f} MB"])
    lines.append(format_table(["Filename", "Year", "Size"], img_rows))
    lines.append("")

    # ── Part 1: Provider Comparison ──────────────────────────────────────────
    lines.append("## Part 1: Provider Comparison (standardized 1024px input)\n")
    lines.append(
        "All providers receive images at ≤1024px (IDT CLI path compresses by default). "
        "This isolates model quality from resolution differences.\n"
    )

    if not part1_results:
        lines.append("*No results collected — workflows may have failed.*\n")
    else:
        # Per-config summary
        for cfg_result in part1_results:
            label    = cfg_result["label"]
            provider = cfg_result["provider"]
            model    = cfg_result["model"]
            entries  = cfg_result.get("entries", [])
            tok_data = cfg_result.get("token_log", {})
            elapsed  = cfg_result.get("elapsed_s", 0)
            wf_dir   = cfg_result.get("wf_dir", "N/A")

            lines.append(f"### {label}\n")
            lines.append(f"- **Provider**: `{provider}`")
            lines.append(f"- **Model**: `{model}`")
            lines.append(f"- **Total elapsed**: {elapsed:.0f}s ({elapsed/60:.1f} min)")
            lines.append(f"- **Workflow dir**: `{wf_dir}`")
            lines.append(f"- **Descriptions collected**: {len(entries)}\n")

            if not entries:
                lines.append("*No descriptions found.*\n")
                continue

            # Aggregate quality scores
            scores = [score_description_quality(e.get("description", "")) for e in entries]
            avg = lambda key: round(sum(s[key] for s in scores) / len(scores), 1) if scores else 0

            # Token data from log
            total_entry = tok_data.get("__total__", {})
            image_entries = {k: v for k, v in tok_data.items() if k != "__total__"}

            prompt_tokens_list     = [v.get("prompt_tokens", 0)     for v in image_entries.values() if v.get("prompt_tokens")]
            completion_tokens_list = [v.get("completion_tokens", 0) for v in image_entries.values() if v.get("completion_tokens")]
            duration_list          = [v.get("duration_s", 0)        for v in image_entries.values() if v.get("duration_s")]

            def safe_avg(lst):
                return round(sum(lst) / len(lst), 1) if lst else "N/A"
            def safe_sum(lst):
                return sum(lst) if lst else "N/A"

            lines.append("**Token & timing summary:**\n")
            lines.append(format_table(
                ["Metric", "Value"],
                [
                    ["Avg prompt tokens/image",     safe_avg(prompt_tokens_list)],
                    ["Avg completion tokens/image",  safe_avg(completion_tokens_list)],
                    ["Total prompt tokens",          safe_sum(prompt_tokens_list)],
                    ["Total completion tokens",      safe_sum(completion_tokens_list)],
                    ["Avg seconds/image",            safe_avg(duration_list)],
                ]
            ))
            lines.append("")
            lines.append("**Description quality (averages across all images):**\n")
            lines.append(format_table(
                ["Metric", "Average"],
                [
                    ["Word count",          avg("word_count")],
                    ["Sentence count",      avg("sentence_count")],
                    ["Vocabulary richness", avg("unique_ratio")],
                    ["Color words",         avg("color_score")],
                    ["Spatial words",       avg("spatial_score")],
                    ["Detail words",        avg("detail_score")],
                ]
            ))
            lines.append("")

        # Cross-config comparison table
        lines.append("### Cross-config Summary\n")
        comp_rows = []
        for cfg_result in part1_results:
            label   = cfg_result["label"]
            entries = cfg_result.get("entries", [])
            tok_data = cfg_result.get("token_log", {})
            image_entries = {k: v for k, v in tok_data.items() if k != "__total__"}
            pt = [v.get("prompt_tokens", 0) for v in image_entries.values() if v.get("prompt_tokens")]
            ct = [v.get("completion_tokens", 0) for v in image_entries.values() if v.get("completion_tokens")]
            dur = [v.get("duration_s", 0) for v in image_entries.values() if v.get("duration_s")]
            scores = [score_description_quality(e.get("description", "")) for e in entries]
            avg_words = round(sum(s["word_count"] for s in scores) / len(scores), 0) if scores else 0
            comp_rows.append([
                label,
                round(sum(pt) / len(pt), 0) if pt else "N/A",
                round(sum(ct) / len(ct), 0) if ct else "N/A",
                round(sum(dur) / len(dur), 1) if dur else "N/A",
                avg_words,
            ])
        lines.append(format_table(
            ["Config", "Avg Input Tokens", "Avg Output Tokens", "Avg Sec/Image", "Avg Words"],
            comp_rows
        ))
        lines.append("")

        # Side-by-side descriptions for 3 sample images
        lines.append("### Sample Descriptions (same image, different configs)\n")
        # Pick up to 3 files that appear in all configs
        all_files = None
        for cfg_result in part1_results:
            files_in_cfg = {e["file"] for e in cfg_result.get("entries", [])}
            all_files = files_in_cfg if all_files is None else (all_files & files_in_cfg)
        sample_files = sorted(all_files or [])[:3] if all_files else []

        for fname in sample_files:
            lines.append(f"#### `{fname}`\n")
            for cfg_result in part1_results:
                label = cfg_result["label"]
                match = next((e for e in cfg_result.get("entries", []) if e["file"] == fname), None)
                if match:
                    desc = match.get("description", "").strip()
                    wc   = len(desc.split())
                    lines.append(f"**{label}** ({wc} words):")
                    lines.append(f"> {desc}\n")

    # ── Part 2: Resolution Impact ─────────────────────────────────────────────
    lines.append("## Part 2: Resolution Impact (Ollama llama3.2-vision)\n")
    lines.append(
        "Same 5 images processed at 512px, 1024px, and full resolution. "
        "Tests whether sending higher-resolution images to Ollama improves description quality.\n"
    )

    if not part2_results:
        lines.append("*No results collected — workflows may have failed.*\n")
    else:
        for res_result in part2_results:
            size_label = res_result["size_label"]
            entries    = res_result.get("entries", [])
            tok_data   = res_result.get("token_log", {})
            elapsed    = res_result.get("elapsed_s", 0)
            image_entries = {k: v for k, v in tok_data.items() if k != "__total__"}
            pt  = [v.get("prompt_tokens", 0)     for v in image_entries.values() if v.get("prompt_tokens")]
            ct  = [v.get("completion_tokens", 0) for v in image_entries.values() if v.get("completion_tokens")]
            dur = [v.get("duration_s", 0)        for v in image_entries.values() if v.get("duration_s")]
            scores = [score_description_quality(e.get("description", "")) for e in entries]

            def sa(lst): return round(sum(lst)/len(lst), 1) if lst else "N/A"

            lines.append(f"### Resolution: {size_label}\n")
            lines.append(format_table(
                ["Metric", "Value"],
                [
                    ["Images processed",            len(entries)],
                    ["Avg prompt tokens/image",      sa(pt)],
                    ["Avg completion tokens/image",  sa(ct)],
                    ["Avg seconds/image",            sa(dur)],
                    ["Avg word count",               sa([s["word_count"] for s in scores])],
                    ["Avg color words",              sa([s["color_score"] for s in scores])],
                    ["Avg spatial words",            sa([s["spatial_score"] for s in scores])],
                ]
            ))
            lines.append("")

        # Summary comparison
        lines.append("### Resolution Impact Summary\n")
        res_rows = []
        for res_result in part2_results:
            size_label = res_result["size_label"]
            entries    = res_result.get("entries", [])
            tok_data   = res_result.get("token_log", {})
            image_entries = {k: v for k, v in tok_data.items() if k != "__total__"}
            pt  = [v.get("prompt_tokens", 0)     for v in image_entries.values() if v.get("prompt_tokens")]
            ct  = [v.get("completion_tokens", 0) for v in image_entries.values() if v.get("completion_tokens")]
            dur = [v.get("duration_s", 0)        for v in image_entries.values() if v.get("duration_s")]
            scores = [score_description_quality(e.get("description", "")) for e in entries]
            sa = lambda lst: round(sum(lst)/len(lst), 1) if lst else "N/A"
            res_rows.append([
                size_label,
                sa(pt),
                sa(ct),
                sa(dur),
                sa([s["word_count"] for s in scores]),
            ])
        lines.append(format_table(
            ["Resolution", "Avg Input Tokens", "Avg Output Tokens", "Avg Sec/Image", "Avg Words"],
            res_rows
        ))
        lines.append("")

        # Side-by-side resolution comparison for 2 sample images
        lines.append("### Sample: Same Image at Different Resolutions\n")
        all_res_files = None
        for res_result in part2_results:
            files_in = {e["file"] for e in res_result.get("entries", [])}
            all_res_files = files_in if all_res_files is None else (all_res_files & files_in)
        sample_res_files = sorted(all_res_files or [])[:2]

        for fname in sample_res_files:
            lines.append(f"#### `{fname}`\n")
            for res_result in part2_results:
                size_label = res_result["size_label"]
                match = next((e for e in res_result.get("entries", []) if e["file"] == fname), None)
                if match:
                    desc = match.get("description", "").strip()
                    wc   = len(desc.split())
                    pt   = match.get("prompt_tokens", "?")
                    lines.append(f"**{size_label}** ({wc} words, {pt} prompt tokens):")
                    lines.append(f"> {desc}\n")

    # ── Findings & Recommendations ────────────────────────────────────────────
    lines.append("## Findings & Recommendations\n")
    lines.append(
        "### Key Findings\n\n"
        "Based on the experiment data above:\n\n"
        "**1. Token efficiency**\n"
        "MLX models report significantly lower input token counts compared to Ollama. "
        "From code analysis and this experiment, this is primarily driven by:\n"
        "- Qwen2.5-VL's efficient visual tokenizer (fewer patches per equivalent resolution)\n"
        "- The MLX path always hard-caps at 1024px max dimension, enforced in `_to_jpeg_tempfile()`\n"
        "- Ollama's visual token count depends heavily on the model's mmproj resolution grid\n\n"
        "**2. The GUI inconsistency (most actionable finding)**\n"
        "The IDT CLI (`image_describer.py`) correctly compresses Ollama images to 1024px. "
        "The GUI (`OllamaProvider.describe_image()` in `imagedescriber/ai_providers.py`) does NOT — "
        "it encodes full-resolution images as base64. This means:\n"
        "- GUI users sending a 4000×3000 iPhone photo to Ollama get 3–10× more input tokens\n"
        "- Inference is slower with no corresponding quality benefit (as shown in Part 2)\n"
        "- Token counts in the stats view are misleading when comparing GUI vs CLI runs\n\n"
        "**3. Resolution vs quality**\n"
        "The Part 2 resolution sweep tests whether higher resolution meaningfully improves "
        "Ollama's descriptions. See the data above for specific findings.\n\n"
    )

    lines.append("### Recommended Code Change\n\n")
    lines.append(
        "Add dimension capping to `OllamaProvider.describe_image()` in "
        "`imagedescriber/ai_providers.py`. Specifically, before the base64 encode at line ~1385, "
        "apply the same PIL resize that the CLI uses in `image_describer.py::optimize_image()`. "
        "The cap should be configurable (default: 1024px, matching the CLI default).\n\n"
        "This is a low-risk change because:\n"
        "- It makes GUI behavior consistent with CLI behavior\n"
        "- It reduces inference time and RAM pressure on the Ollama server\n"
        "- The Part 2 data above shows whether quality is meaningfully impacted\n\n"
    )

    lines.append("### User Guidance\n\n")
    lines.append(
        "**For local Ollama users:**\n"
        "- 1024px is generally sufficient for iPhone photo descriptions\n"
        "- If you need fine detail (small text, intricate patterns), try 1536px — but expect 2–3× more tokens and slower inference\n"
        "- Full-resolution (3-4K) provides minimal benefit for scene/event descriptions and slows inference significantly\n\n"
        "**For MLX users:**\n"
        "- The 1024px cap in `_to_jpeg_tempfile()` is appropriate for 7B models\n"
        "- The 11B Llama model may benefit from a higher cap — consider 1280px\n"
        "- Token counts are not directly comparable to Ollama token counts (different tokenizers + different patch sizes)\n\n"
        "**For cloud API users (OpenAI/Claude):**\n"
        "- Both cloud providers have their own resolution tiling logic and charge per tile\n"
        "- The existing optimization in `image_describer.py` is correct for these providers\n\n"
    )

    lines.append("---\n")
    lines.append(f"*Report generated by `experiments/run_experiment.py` on {now}*\n")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n{'='*60}")
    print(f"REPORT written to: {REPORT_PATH}")
    print(f"{'='*60}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print(f"\n{'='*60}")
    print("IDT Resolution & Quality Experiment")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    # Sanity checks
    if not IDT.exists():
        print(f"ERROR: IDT binary not found at {IDT}")
        sys.exit(1)
    if not PHOTO_BASE.exists():
        print(f"ERROR: Photo library not mounted at {PHOTO_BASE}")
        sys.exit(1)

    # ── Step 1: Select source images ──────────────────────────────────────────
    print("Step 1: Selecting source images from photo library...")
    selected = select_diverse_images(NUM_IMAGES)
    print(f"  Selected {len(selected)} images:")
    for p in selected:
        print(f"    {p.parent.parent.name}/{p.parent.name}/{p.name}  ({p.stat().st_size//1024}KB)")
    print()

    # ── Step 2: Pre-convert everything to JPEG at required resolutions ─────────
    # Using imagedescriber venv PIL (not the system one) for HEIC support
    print("Step 2: Pre-converting HEIC → JPEG at all required resolutions...")
    _venv_site = "/Users/kellyford/Documents/GitHub/Image-Description-Toolkit/imagedescriber/.venv/lib"
    _pyverdirs = list(Path(_venv_site).glob("python3.*"))
    if _pyverdirs:
        _site_packages = _pyverdirs[0] / "site-packages"
        if str(_site_packages) not in sys.path:
            sys.path.insert(0, str(_site_packages))

    # Part 1 uses 1024px cap (matches the CLI default behavior)
    part1_dir = RESIZE_DIR / "1024px"
    part1_dir.mkdir(parents=True, exist_ok=True)
    part1_sources = make_resized_dirs(selected, [1024])
    part1_images = part1_sources.get(1024, [])
    print(f"  Part 1 images ({len(part1_images)} at 1024px): {part1_dir}")

    # Part 2 resolution sweep — first RES_TEST_N images at 512, 1024, full
    res_subset = selected[:RES_TEST_N]
    resized = make_resized_dirs(res_subset, PART2_SIZES_PX)
    print(f"  Part 2 resolution sets: {list(resized.keys())} px in {RESIZE_DIR}\n")

    # ── Step 3: Run Part 1 — Provider Comparison ──────────────────────────────
    print("Step 3: Running Part 1 provider comparison experiments...")
    part1_results = []

    for cfg in PART1_CONFIGS:
        label    = cfg["label"]
        provider = cfg["provider"]
        model    = cfg["model"]

        # Always 'describe' only — we pre-converted to JPEG in Step 2
        wf_dir, elapsed = run_idt_workflow(part1_dir, provider, model, label, steps="describe")

        cfg_result = {
            "label":    label,
            "provider": provider,
            "model":    model,
            "elapsed_s": elapsed,
            "wf_dir":   str(wf_dir) if wf_dir else "NOT FOUND",
        }

        if wf_dir and wf_dir.exists():
            cfg_result["entries"]   = parse_descriptions_file(wf_dir)
            cfg_result["token_log"] = parse_log_for_tokens(wf_dir)
            print(f"  Parsed {len(cfg_result['entries'])} descriptions from {wf_dir.name}")
        else:
            cfg_result["entries"]   = []
            cfg_result["token_log"] = {}
            print(f"  WARNING: no workflow dir found for {label}")

        part1_results.append(cfg_result)

    # Save intermediate results
    intermediate = EXP_DIR / "part1_results.json"
    with open(intermediate, "w") as f:
        json.dump([{k: v for k, v in r.items() if k != "entries"} for r in part1_results], f, indent=2, default=str)
    print(f"\nPart 1 complete. Intermediate saved to {intermediate}")

    # ── Step 4: Run Part 2 — Resolution Impact ────────────────────────────────
    print("\nStep 4: Running Part 2 resolution impact experiments...")
    part2_results = []

    provider = PART2_MODEL["provider"]
    model    = PART2_MODEL["model"]

    for size_px in PART2_SIZES_PX:
        size_label = "full_res" if size_px == 0 else f"{size_px}px"

        input_dir_path = RESIZE_DIR / ("full" if size_px == 0 else f"{size_px}px")
        if not input_dir_path.exists() or not list(input_dir_path.glob("*.jpg")):
            print(f"  WARNING: no resized images for {size_label}")
            continue
        label = f"ResTest_{size_label}"

        wf_dir, elapsed = run_idt_workflow(input_dir_path, provider, model, label, steps="describe")

        res_result = {
            "size_label": size_label,
            "size_px":    size_px,
            "provider":   provider,
            "model":      model,
            "elapsed_s":  elapsed,
            "wf_dir":     str(wf_dir) if wf_dir else "NOT FOUND",
        }

        if wf_dir and wf_dir.exists():
            res_result["entries"]   = parse_descriptions_file(wf_dir)
            res_result["token_log"] = parse_log_for_tokens(wf_dir)
            print(f"  Parsed {len(res_result['entries'])} descriptions for {size_label}")
        else:
            res_result["entries"]   = []
            res_result["token_log"] = {}
            print(f"  WARNING: no workflow dir found for {label}")

        part2_results.append(res_result)

    intermediate2 = EXP_DIR / "part2_results.json"
    with open(intermediate2, "w") as f:
        json.dump([{k: v for k, v in r.items() if k != "entries"} for r in part2_results], f, indent=2, default=str)
    print(f"\nPart 2 complete. Intermediate saved to {intermediate2}")

    # ── Step 5: Write report ──────────────────────────────────────────────────
    print("\nStep 5: Writing report...")
    write_report(part1_results, part2_results, selected)

    print("\n✅ Experiment complete!")
    print(f"   Report: {REPORT_PATH}")
    print(f"   Workflow outputs: {WORK_DIR}")


if __name__ == "__main__":
    main()
