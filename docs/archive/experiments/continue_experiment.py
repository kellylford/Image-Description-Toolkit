#!/usr/bin/env python3
"""
Continuation script: runs ResTest_1024px and ResTest_full_res, 
then generates the full report from all 7 workflow results.
"""
import sys
from pathlib import Path

# Add the parent so we can import everything from run_experiment
sys.path.insert(0, str(Path(__file__).parent))

from run_experiment import (
    WORK_DIR, RESIZE_DIR, REPORT_PATH, EXP_DIR, IMAGES_DIR,
    PART1_CONFIGS, PART2_MODEL, PART2_SIZES_PX,
    PROMPT_STYLE, NUM_IMAGES,
    run_idt_workflow, parse_descriptions_file, parse_log_for_tokens,
    score_description_quality, write_report, select_diverse_images,
)
from datetime import datetime
import json

def main():
    print(f"\n{'='*60}")
    print("IDT Experiment — Continuation (1024px + full_res + report)")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    # ── Reload Part 1 results from existing workflow dirs ─────────────────────
    print("Loading Part 1 results from existing workflow dirs...")
    part1_results = []
    for cfg in PART1_CONFIGS:
        label    = cfg["label"]
        provider = cfg["provider"]
        model    = cfg["model"]
        # Find matching workflow dir (newest matching label + provider + narrative)
        matches = sorted(
            [d for d in WORK_DIR.iterdir()
             if d.is_dir() and label in d.name and "narrative" in d.name],
            key=lambda p: p.stat().st_mtime, reverse=True
        )
        if matches:
            wf_dir = matches[0]
            entries   = parse_descriptions_file(wf_dir)
            tok_data  = parse_log_for_tokens(wf_dir)
            print(f"  {label}: {len(entries)} descriptions from {wf_dir.name}")
        else:
            wf_dir    = None
            entries   = []
            tok_data  = {}
            print(f"  WARNING: no workflow dir found for {label}")
        # Estimate elapsed from log timestamps (best effort)
        elapsed = 0.0
        if wf_dir:
            wf_log = list(wf_dir.rglob("workflow_*.log"))
            if wf_log:
                import re
                text = wf_log[0].read_text(errors="replace")
                ts_matches = re.findall(r'\((\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),', text)
                if len(ts_matches) >= 2:
                    from datetime import datetime as dt
                    t0 = dt.strptime(ts_matches[0], "%Y-%m-%d %H:%M:%S")
                    t1 = dt.strptime(ts_matches[-1], "%Y-%m-%d %H:%M:%S")
                    elapsed = (t1 - t0).total_seconds()
        part1_results.append({
            "label":    label,
            "provider": provider,
            "model":    model,
            "elapsed_s": elapsed,
            "wf_dir":   str(wf_dir) if wf_dir else "NOT FOUND",
            "entries":  entries,
            "token_log": tok_data,
        })

    # ── Reload 512px Part 2 result ────────────────────────────────────────────
    print("\nLoading Part 2 ResTest_512px result...")
    part2_results = []
    match_512 = sorted(
        [d for d in WORK_DIR.iterdir()
         if d.is_dir() and "ResTest_512px" in d.name],
        key=lambda p: p.stat().st_mtime, reverse=True
    )
    if match_512:
        wf = match_512[0]
        part2_results.append({
            "size_label": "512px",
            "size_px":    512,
            "provider":   PART2_MODEL["provider"],
            "model":      PART2_MODEL["model"],
            "elapsed_s":  0.0,
            "wf_dir":     str(wf),
            "entries":    parse_descriptions_file(wf),
            "token_log":  parse_log_for_tokens(wf),
        })
        print(f"  ResTest_512px: {len(part2_results[0]['entries'])} descriptions")
    else:
        print("  WARNING: ResTest_512px not found")

    # ── Run ResTest_1024px ────────────────────────────────────────────────────
    print("\nRunning ResTest_1024px...")
    input_1024 = RESIZE_DIR / "1024px"
    if input_1024.exists() and list(input_1024.glob("*.jpg")):
        wf_dir, elapsed = run_idt_workflow(
            input_1024, PART2_MODEL["provider"], PART2_MODEL["model"],
            "ResTest_1024px", steps="describe"
        )
        if wf_dir and wf_dir.exists():
            entries  = parse_descriptions_file(wf_dir)
            tok_data = parse_log_for_tokens(wf_dir)
            print(f"  ResTest_1024px: {len(entries)} descriptions")
        else:
            entries, tok_data = [], {}
            print("  WARNING: no workflow dir for ResTest_1024px")
        part2_results.append({
            "size_label": "1024px",
            "size_px":    1024,
            "provider":   PART2_MODEL["provider"],
            "model":      PART2_MODEL["model"],
            "elapsed_s":  elapsed,
            "wf_dir":     str(wf_dir) if wf_dir else "NOT FOUND",
            "entries":    entries,
            "token_log":  tok_data,
        })
    else:
        print("  WARNING: no 1024px images found, skipping")

    # ── Run ResTest_full_res ──────────────────────────────────────────────────
    print("\nRunning ResTest_full_res...")
    input_full = RESIZE_DIR / "full"
    if input_full.exists() and list(input_full.glob("*.jpg")):
        wf_dir, elapsed = run_idt_workflow(
            input_full, PART2_MODEL["provider"], PART2_MODEL["model"],
            "ResTest_full_res", steps="describe"
        )
        if wf_dir and wf_dir.exists():
            entries  = parse_descriptions_file(wf_dir)
            tok_data = parse_log_for_tokens(wf_dir)
            print(f"  ResTest_full_res: {len(entries)} descriptions")
        else:
            entries, tok_data = [], {}
            print("  WARNING: no workflow dir for ResTest_full_res")
        part2_results.append({
            "size_label": "full_res",
            "size_px":    0,
            "provider":   PART2_MODEL["provider"],
            "model":      PART2_MODEL["model"],
            "elapsed_s":  elapsed,
            "wf_dir":     str(wf_dir) if wf_dir else "NOT FOUND",
            "entries":    entries,
            "token_log":  tok_data,
        })
    else:
        print("  WARNING: no full images found, skipping")

    # ── Load the original selected images list for the report header ──────────
    selected = select_diverse_images(NUM_IMAGES)

    # ── Generate report ───────────────────────────────────────────────────────
    print("\nGenerating report...")
    write_report(part1_results, part2_results, selected)
    print(f"\n✅ Done! Report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
