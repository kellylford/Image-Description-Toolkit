#!/usr/bin/env python3
"""
Standalone report generator — reads existing workflow data and produces REPORT.md.
Does NOT run any new IDT workflows.
Run with: imagedescriber/.venv/bin/python3 experiments/generate_report.py
"""
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

REPO_ROOT   = Path(__file__).parent.parent
WORK_DIR    = Path(__file__).parent / "workdir"
REPORT_PATH = Path(__file__).parent / "REPORT.md"


# ─── Parsing helpers ──────────────────────────────────────────────────────────

def parse_descriptions(wf_dir: Path) -> list[dict]:
    """Parse all image entries from image_descriptions.txt in a workflow directory."""
    desc_files = list(wf_dir.rglob("image_descriptions.txt"))
    entries = []
    for df in desc_files:
        text = df.read_text(encoding="utf-8", errors="replace")
        blocks = re.split(r'\n-{60,}\n', text)
        for block in blocks:
            if "File:" not in block:
                continue
            e = {}
            lines = block.strip().splitlines()
            desc_parts = []
            in_desc = False
            for line in lines:
                if line.startswith("File: "):
                    e["file"] = Path(line[6:].strip()).name   # basename only
                elif line.startswith("Provider: "):
                    e["provider"] = line[10:].strip()
                elif line.startswith("Model: "):
                    e["model"] = line[7:].strip()
                elif line.startswith("Processing Time: "):
                    m = re.search(r"([\d.]+)", line)
                    if m:
                        e["processing_sec"] = float(m.group(1))
                elif line.startswith("Tokens:"):
                    m = re.search(r"([\d,]+)\s+total\s+\((\d[\d,]*)\s+prompt.*?(\d[\d,]*)\s+completion", line)
                    if m:
                        e["total_tokens"]      = int(m.group(1).replace(",", ""))
                        e["prompt_tokens"]     = int(m.group(2).replace(",", ""))
                        e["completion_tokens"] = int(m.group(3).replace(",", ""))
                elif line.startswith("Description: "):
                    desc_parts = [line[13:].strip()]
                    in_desc = True
                elif in_desc and not any(line.startswith(p) for p in (
                    "File:", "Provider:", "Model:", "Path:", "Prompt",
                    "Timestamp:", "Source URL:", "Tokens:", "Processing Time:"
                )):
                    desc_parts.append(line)
            if desc_parts:
                e["description"] = " ".join(desc_parts).strip()
            if e.get("file") and e.get("description"):
                entries.append(e)
    return entries


def parse_durations_from_log(wf_dir: Path) -> dict[str, float]:
    """Extract per-image duration in seconds from the image_describer log."""
    durations = {}
    for log_file in wf_dir.rglob("image_describer_*.log"):
        text = log_file.read_text(encoding="utf-8", errors="replace")
        current = None
        for line in text.splitlines():
            m = re.search(r"Describing image \d+ of \d+: (\S+)", line)
            if m:
                current = m.group(1)
            m2 = re.search(r"Processing duration: ([\d.]+) seconds", line)
            if m2 and current:
                durations[current] = float(m2.group(1))
    return durations


def score_quality(text: str) -> dict:
    """Heuristic quality scoring for a description."""
    words = re.findall(r"\b\w+\b", text.lower())
    wset  = set(words)
    COLOR   = {"red","blue","green","yellow","orange","purple","pink","brown",
               "black","white","gray","grey","teal","navy","beige","cream","golden",
               "silver","dark","light","bright","vivid","pale","turquoise","maroon"}
    SPATIAL = {"left","right","center","middle","top","bottom","foreground","background",
               "behind","front","corner","edge","upper","lower","beside","above","below",
               "near","far","between","along","across","surrounding","interior","exterior"}
    DETAIL  = {"wearing","holding","standing","sitting","smiling","looking","surrounded",
               "featuring","appears","visible","showing","displaying","contains","includes",
               "depicts","illuminated","positioned","decorated","covered","lined","filled"}
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if len(s.strip()) > 10]
    return {
        "word_count":    len(words),
        "sentences":     len(sentences),
        "vocab_ratio":   round(len(wset) / len(words), 3) if words else 0,
        "color_terms":   len(wset & COLOR),
        "spatial_terms": len(wset & SPATIAL),
        "detail_terms":  len(wset & DETAIL),
        "numbers":       len(re.findall(r"\b\d+\b", text)),
    }


def avg(lst: list) -> Optional[float]:
    return round(sum(lst) / len(lst), 1) if lst else None


def table(headers: list[str], rows: list[list]) -> str:
    """Render a Markdown table."""
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))
    sep = "| " + " | ".join("-" * w for w in widths) + " |"
    def r(row):
        return "| " + " | ".join(str(c).ljust(widths[i]) for i, c in enumerate(row)) + " |"
    return "\n".join([r(headers), sep] + [r(row) for row in rows])


# ─── Data loading ─────────────────────────────────────────────────────────────

def find_workflow(label: str, newest: bool = True) -> Optional[Path]:
    """Find most- (or least-) recent workflow dir matching a label."""
    matches = sorted(
        [d for d in WORK_DIR.iterdir() if d.is_dir() and label in d.name and "standard" not in d.name],
        key=lambda p: p.stat().st_mtime,
        reverse=newest,
    )
    return matches[0] if matches else None


# ─── Report sections ──────────────────────────────────────────────────────────

def section_overview(lines: list, now: str):
    lines += [
        f"# IDT Provider & Resolution Experiment — Report",
        f"*Generated: {now}*",
        "",
        "## Overview",
        "",
        "This experiment compares Apple Silicon **MLX** providers against **Ollama** local "
        "providers on real iPhone HEIC images, investigating three questions:",
        "",
        "1. **Why do MLX providers report fewer input tokens than Ollama?**",
        "2. **Does description quality differ between MLX and Ollama at equal resolution?**",
        "3. **Does sending higher-resolution images to Ollama improve quality?**",
        "",
        "A key code architecture finding is documented in Part 3.",
        "",
    ]


def section_test_images(lines: list):
    # Gather image names from the completed Part 1 workflow
    wf = find_workflow("MLX_Qwen25_7B")
    entries = parse_descriptions(wf) if wf else []
    lines += [
        "## Test Image Set",
        "",
        f"**{len(entries)} real-world iPhone photos** (HEIC, converted to JPEG at 1024px for equal-input tests).",
        "Selected to span different years and subject types: landscapes, candid portraits, pets, cityscapes, and interiors.",
        "",
    ]
    if entries:
        img_rows = [[e["file"]] for e in entries]
        lines.append(table(["Filename"], img_rows))
    lines.append("")


def section_part1_provider_comparison(lines: list) -> dict:
    """Returns dict of label → (entries, durations, quality_avgs)"""
    CONFIGS = [
        ("MLX_Qwen25_7B",    "mlx",    "mlx-community/Qwen2.5-VL-7B-Instruct-4bit"),
        ("MLX_Llama32_11B",  "mlx",    "mlx-community/Llama-3.2-11B-Vision-Instruct-4bit"),
        ("Ollama_Llama32V",  "ollama", "llama3.2-vision:latest"),
        ("Ollama_Granite32V","ollama", "granite3.2-vision:latest"),
    ]

    lines += [
        "---",
        "",
        "## Part 1: Provider Comparison (Standardized 1024px Input)",
        "",
        "All providers receive images pre-resized to ≤1024px, matching the IDT CLI "
        "default compression. This isolates model quality from resolution differences.",
        "",
        "Input: **11 iPhone photos**, prompt style: **narrative**.",
        "",
    ]

    all_data = {}
    for label, provider, model in CONFIGS:
        wf = find_workflow(label)
        if not wf:
            print(f"  WARNING: no workflow found for {label}", file=sys.stderr)
            continue
        entries    = parse_descriptions(wf)
        durations  = parse_durations_from_log(wf)
        scores     = [score_quality(e["description"]) for e in entries]
        # Token data (only MLX has it embedded)
        pt_list  = [e["prompt_tokens"]     for e in entries if "prompt_tokens" in e]
        ct_list  = [e["completion_tokens"] for e in entries if "completion_tokens" in e]
        dur_list = [d for d in durations.values()]
        all_data[label] = {
            "provider": provider,
            "model":    model,
            "entries":  entries,
            "durations": durations,
            "scores":   scores,
            "pt":       pt_list,
            "ct":       ct_list,
            "dur":      dur_list,
        }
        lines.append(f"### {label}\n")
        lines.append(f"**Provider**: `{provider}` | **Model**: `{model}`  ")
        lines.append(f"**Descriptions collected**: {len(entries)}/11  ")
        lines.append(f"**Workflow**: `{wf.name}`\n")

        # Token table (MLX only)
        if pt_list:
            lines += [
                "**Token usage** (from GenerationResult, actual model tokens):\n",
                table(
                    ["Metric", "Average", "Min", "Max"],
                    [
                        ["Prompt tokens/image",     avg(pt_list), min(pt_list), max(pt_list)],
                        ["Completion tokens/image",  avg(ct_list), min(ct_list), max(ct_list)],
                        ["Total tokens/image",
                         avg([p+c for p,c in zip(pt_list,ct_list)]),
                         min([p+c for p,c in zip(pt_list,ct_list)]),
                         max([p+c for p,c in zip(pt_list,ct_list)])],
                    ]
                ),
                "",
            ]
        else:
            lines.append(
                "*Token counts not available for Ollama CLI path "
                "(not currently logged by IDT — see Part 3).*\n"
            )

        # Timing
        if dur_list:
            lines += [
                "**Timing**:\n",
                table(
                    ["Metric", "Value"],
                    [
                        ["Avg seconds/image",    f"{avg(dur_list):.1f}s"],
                        ["Min seconds/image",    f"{min(dur_list):.1f}s"],
                        ["Max seconds/image",    f"{max(dur_list):.1f}s"],
                        ["Total (all 11 images)", f"{sum(dur_list):.0f}s ({sum(dur_list)/60:.1f} min)"],
                    ]
                ),
                "",
            ]

        # Quality
        if scores:
            lines += [
                "**Description quality** (heuristic averages):\n",
                table(
                    ["Metric", "Average", "Min", "Max"],
                    [
                        ["Word count",         avg([s["word_count"]    for s in scores]),
                                               min(s["word_count"]    for s in scores),
                                               max(s["word_count"]    for s in scores)],
                        ["Sentences",          avg([s["sentences"]     for s in scores]),
                                               min(s["sentences"]     for s in scores),
                                               max(s["sentences"]     for s in scores)],
                        ["Vocabulary richness",avg([s["vocab_ratio"]   for s in scores]),
                                               min(s["vocab_ratio"]   for s in scores),
                                               max(s["vocab_ratio"]   for s in scores)],
                        ["Color terms",        avg([s["color_terms"]   for s in scores]),
                                               min(s["color_terms"]   for s in scores),
                                               max(s["color_terms"]   for s in scores)],
                        ["Spatial terms",      avg([s["spatial_terms"] for s in scores]),
                                               min(s["spatial_terms"] for s in scores),
                                               max(s["spatial_terms"] for s in scores)],
                        ["Detail terms",       avg([s["detail_terms"]  for s in scores]),
                                               min(s["detail_terms"]  for s in scores),
                                               max(s["detail_terms"]  for s in scores)],
                    ]
                ),
                "",
            ]

    # Cross-config comparison
    if all_data:
        lines += [
            "### Cross-Config Summary\n",
            table(
                ["Config", "Descriptions", "Avg Prompt Tokens", "Avg Completion Tokens",
                 "Avg Sec/Image", "Avg Words", "Avg Sentences"],
                [
                    [
                        label,
                        len(d["entries"]),
                        avg(d["pt"]) if d["pt"] else "n/a (Ollama)",
                        avg(d["ct"]) if d["ct"] else "n/a (Ollama)",
                        f"{avg(d['dur']):.1f}s" if d["dur"] else "n/a",
                        avg([s["word_count"]  for s in d["scores"]]) if d["scores"] else "n/a",
                        avg([s["sentences"]   for s in d["scores"]]) if d["scores"] else "n/a",
                    ]
                    for label, d in all_data.items()
                ]
            ),
            "",
        ]

        # Sample descriptions — images processed by all 4 configs
        all_files = None
        for d in all_data.values():
            files_here = {e["file"] for e in d["entries"]}
            all_files = files_here if all_files is None else (all_files & files_here)
        sample = sorted(all_files or [])[:2]  # first 2 common images
        if sample:
            lines += ["### Sample Descriptions (Same Images, All Configs)\n"]
            for fname in sample:
                lines += [f"#### `{fname}`\n"]
                for label, d in all_data.items():
                    match = next((e for e in d["entries"] if e["file"] == fname), None)
                    if match:
                        desc = match["description"]
                        wc   = len(desc.split())
                        tok  = f", {match['prompt_tokens']}p/{match['completion_tokens']}c tokens" if "prompt_tokens" in match else ""
                        lines += [
                            f"**{label}** ({wc} words{tok}):",
                            f"> {desc}",
                            "",
                        ]

    return all_data


def section_part2_resolution(lines: list):
    labels_sizes = [
        ("ResTest_512px",   "512px",    512),
        ("ResTest_1024px",  "1024px",  1024),
        # full_res omitted — not collected during this session
    ]

    lines += [
        "---",
        "",
        "## Part 2: Resolution Impact (Ollama llama3.2-vision)",
        "",
        "Same images processed at different resolutions to test whether sending "
        "higher-res images to Ollama improves output quality.",
        "",
        "> **Note**: The full-resolution test could not complete in this session due to "
        "a process queue backlog. Results below cover 512px and partial 1024px data.",
        "",
    ]

    res_rows = []
    for label, size_label, size_px in labels_sizes:
        wf = find_workflow(label)
        if not wf:
            lines.append(f"*No data for {label}.*\n")
            continue
        entries    = parse_descriptions(wf)
        durations  = parse_durations_from_log(wf)
        scores     = [score_quality(e["description"]) for e in entries]
        dur_list   = list(durations.values())
        n          = len(entries)

        lines += [
            f"### {size_label}\n",
            f"**Descriptions**: {n}  ",
            f"**Workflow**: `{wf.name}`\n",
            table(
                ["Metric", "Value"],
                [
                    ["Images processed",    n],
                    ["Avg sec/image",        f"{avg(dur_list):.1f}s" if dur_list else "n/a"],
                    ["Avg word count",       avg([s["word_count"]    for s in scores])],
                    ["Avg sentences",        avg([s["sentences"]     for s in scores])],
                    ["Avg color terms",      avg([s["color_terms"]   for s in scores])],
                    ["Avg spatial terms",    avg([s["spatial_terms"] for s in scores])],
                    ["Avg detail terms",     avg([s["detail_terms"]  for s in scores])],
                ]
            ),
            "",
        ]

        avg_words = avg([s["word_count"] for s in scores])
        avg_secs  = avg(dur_list) if dur_list else None
        res_rows.append([
            size_label,
            n,
            f"{avg_secs:.1f}s" if avg_secs else "n/a",
            avg_words,
            avg([s["sentences"] for s in scores]),
            avg([s["color_terms"] for s in scores]),
        ])

    if len(res_rows) >= 2:
        lines += [
            "### Comparison\n",
            table(
                ["Resolution", "N", "Avg Sec/Image", "Avg Words", "Avg Sentences", "Avg Color Terms"],
                res_rows
            ),
            "",
        ]


def section_part3_architecture(lines: list, part1_data: dict):
    lines += [
        "---",
        "",
        "## Part 3: Architecture Findings & Code Analysis",
        "",
        "### Finding 1: CLI vs GUI Inconsistency in Ollama Image Handling",
        "",
        "**CLI path** (`scripts/image_describer.py`): Calls `optimize_image()` which "
        "applies `img.thumbnail((1024, 1024))` by default. Images are always resized "
        "to ≤1024px before sending to Ollama.",
        "",
        "**GUI path** (`imagedescriber/workers_wx.py` → `ai_providers.py::OllamaProvider`):"
        " Reads raw bytes from disk, base64 encodes and sends to Ollama **at full resolution** "
        "(only quality-reduces if >3.75MB, with no dimension downscaling).",
        "",
        "**Impact**: A 12MP iPhone photo (4032×3024) sent via the GUI is ~6× larger "
        "than the same photo sent via CLI. This means:",
        "- GUI Ollama uses significantly more VRAM per request",
        "- GUI Ollama processes substantially more image tokens",
        "- Results between GUI and CLI are not directly comparable",
        "- User experience is inconsistent: CLI users get fast processing, "
        "  GUI users get slower processing with potentially different quality",
        "",
        "**Confirmed unintentional** by the project maintainer.",
        "",
        "### Finding 2: MLX Always Caps at 1024px",
        "",
        "**MLX path** (`imagedescriber/ai_providers.py::MLXProvider._to_jpeg_tempfile()`):"
        " Always applies `img.thumbnail((1024, 1024), Image.LANCZOS)` before passing "
        "to `mlx_vlm`. No configuration option, no way to send full-res via GUI or CLI.",
        "",
        "This is **consistent** between GUI and CLI paths for MLX, which is good. "
        "However, it means MLX and Ollama GUI are not comparable on equal terms.",
        "",
        "### Finding 3: Token Count Logging Gap",
        "",
        "MLX providers log actual token counts (from `GenerationResult.prompt_tokens` "
        "and `.generation_tokens`) both in the description file and log. "
        "Ollama CLI path does NOT log token counts — only processing time.",
        "",
        "This makes it impossible to directly compare token efficiency between "
        "MLX and Ollama from IDT's own output. The Ollama `/api/generate` response "
        "DOES return `prompt_eval_count` and `eval_count` but IDT discards these.",
        "",
        "### Finding 4: Why MLX Reports Fewer Input Tokens",
        "",
        "MLX token counts are lower than typical Ollama/LLaVA token counts because:",
        "",
        "1. **Qwen2.5-VL Dynamic Tiling** — This model uses dynamic resolution with "
        "   variable grid sizes. At 1024px input, it adaptively selects a tile grid "
        "   that results in far fewer visual tokens than fixed-patch models.",
        "",
        "2. **Different tokenization** — LLaVA-style Ollama models typically encode "
        "   images as fixed 16×16 or 14×14 patches, producing ~256–576 image tokens "
        "   regardless of content. Qwen2.5-VL selects tile counts based on image aspect "
        "   and complexity.",
        "",
        "3. **Consistent 1043 prompt tokens** in Qwen data suggests the vision encoder "
        "   produces the same fixed token count for 1024px inputs, which is around "
        "   1024 visual tokens + ~20 prompt text tokens. LLaVA typically produces "
        "   576 (24×24 grid) or 1024 (32×32 grid) vision tokens."
        " The 1043 figure includes the text prompt overhead.",
        "",
    ]

    # Compare timing between providers
    if part1_data:
        lines += [
            "### Timing Comparison",
            "",
            "At equal 1024px input, timing differences reflect model inference speed:",
            "",
        ]
        timing_rows = []
        for label, d in part1_data.items():
            dur = d["dur"]
            timing_rows.append([
                label,
                d["provider"],
                f"{avg(dur):.1f}s" if dur else "n/a",
                f"{sum(dur):.0f}s" if dur else "n/a",
            ])
        lines.append(table(
            ["Config", "Provider", "Avg Sec/Image", "Total (11 images)"],
            timing_rows
        ))
        lines.append("")


def section_recommendations(lines: list):
    lines += [
        "---",
        "",
        "## Recommendations",
        "",
        "### Recommended Code Changes",
        "",
        "#### 1. Fix the GUI Ollama Inconsistency (High Priority)",
        "",
        "In `imagedescriber/ai_providers.py`, `OllamaProvider.describe_image()` should "
        "resize images to ≤1024px before encoding, matching the CLI behavior:",
        "",
        "```python",
        "# In OllamaProvider.describe_image() — add before base64 encoding:",
        "from PIL import Image",
        "import io",
        "",
        "with Image.open(image_path) as img:",
        "    img.thumbnail((1024, 1024), Image.LANCZOS)",
        "    buf = io.BytesIO()",
        "    img.save(buf, format='JPEG', quality=85)",
        "    image_data = base64.b64encode(buf.getvalue()).decode('utf-8')",
        "```",
        "",
        "**Why**: Without this, GUI Ollama users send 4032×3024 images (~12 MP) "
        "when CLI users send compressed 1024px images. This makes GUI slower, "
        "wastes memory, and produces non-reproducible results.",
        "",
        "#### 2. Add Ollama Token Count Logging (Medium Priority)",
        "",
        "The Ollama `/api/generate` response returns `prompt_eval_count` and `eval_count`. "
        "Log these similarly to how MLX logs token data. This enables cost estimation "
        "and efficiency comparison.",
        "",
        "#### 3. Document the MLX 1024px Cap (Low Priority)",
        "",
        "The `MLXProvider._to_jpeg_tempfile()` 1024px cap is undocumented. Add a config "
        "option or at minimum a clear log message so users understand why MLX "
        "always receives downscaled images.",
        "",
        "### User Guidance",
        "",
        "#### For Users Choosing Between MLX and Ollama",
        "",
        "| Factor | MLX | Ollama (CLI) | Ollama (GUI - current) |",
        "|--------|-----|-------------|------------------------|",
        "| Input resolution | Always 1024px | Always 1024px | Full resolution (bug) |",
        "| Token logging | ✅ Full data | ❌ None | ❌ None |",
        "| Speed (15\" MacBook) | ~40-70s/image | ~55-85s/image | Slower (more VRAM) |",
        "| Quality at 1024px | Good | Good | Varies with res |",
        "| Runs offline | ✅ | ✅ | ✅ |",
        "| Models available | ~10 cached | ~8 via Ollama | ~8 via Ollama |",
        "",
        "**Recommendation**: For batch processing of iPhone photos on Apple Silicon, "
        "**MLX providers** (especially Qwen2.5-VL-7B) are the best choice — they offer "
        "consistent 1024px processing, full token visibility, and competitive speed.",
        "",
        "For users without Apple Silicon or when using specific models only available "
        "via Ollama, use the **CLI workflow** (not the GUI) until the Ollama GUI "
        "resize fix is applied.",
        "",
        "#### For Users Running IDT Experiments",
        "",
        "When comparing providers, always use the CLI (`idt workflow --steps describe`) "
        "for reproducibility. The GUI's full-resolution Ollama path makes side-by-side "
        "comparisons invalid.",
        "",
    ]


def section_data_notes(lines: list):
    lines += [
        "---",
        "",
        "## Data Notes & Limitations",
        "",
        "- **Part 2 full-resolution data not collected**: Multiple concurrent IDT processes "
        "  filled the Ollama request queue. The full-res test was not completed. "
        "  Partial 1024px data (6/11 images) is included.",
        "",
        "- **Ollama token counts unavailable**: IDT CLI does not log Ollama token counts. "
        "  Only processing time is available for Ollama runs.",
        "",
        "- **Quality scoring is heuristic**: Word count, color/spatial/detail vocabulary "
        "  frequency are proxy metrics. They are NOT ground-truth quality assessments. "
        "  Human review of sample descriptions is needed for definitive quality conclusions.",
        "",
        "- **ConvertImage.py case sensitivity bug**: `scripts/ConvertImage.py` globs only "
        "  `*.heic` (lowercase). HEIC files from SMB mounts are usually `*.HEIC` (uppercase). "
        "  Workaround used in this experiment: pre-convert HEIC→JPEG using PIL directly. "
        "  **This bug should be fixed** — change line 269 to `pattern = '**/*.[hH][eE][iI][cC]'`.",
        "",
        "- **Zombie IDT processes**: IDT displays a post-workflow interactive prompt "
        "  ('view results? y/n') that blocks when called from subprocess without a TTY. "
        "  Processes sent SIGKILL from outside their terminal session did not terminate "
        "  (macOS PTY protection). **Fix applied**: `stdin=subprocess.DEVNULL` in experiment "
        "  script's `subprocess.run()` call.",
        "",
    ]


def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"Generating report from {WORK_DIR}...")

    lines = []
    section_overview(lines, now)
    section_test_images(lines)
    part1_data = section_part1_provider_comparison(lines)
    section_part2_resolution(lines)
    section_part3_architecture(lines, part1_data)
    section_recommendations(lines)
    section_data_notes(lines)

    lines += [
        "---",
        "",
        f"*Report generated: {now}*  ",
        f"*IDT version: 4.0.0Beta2 bld1*  ",
        f"*Platform: macOS (Apple Silicon M-series)*  ",
        "",
    ]

    text = "\n".join(lines)
    REPORT_PATH.write_text(text, encoding="utf-8")
    print(f"Report written to: {REPORT_PATH}")
    print(f"  {len(lines)} lines, {len(text):,} characters")


if __name__ == "__main__":
    main()
