#!/usr/bin/env python3
"""Send USER_GUIDE.md to an Ollama model for review and suggested updates."""
import json
import urllib.request
import sys
from pathlib import Path

GUIDE_PATH = Path(__file__).resolve().parent.parent / "docs" / "USER_GUIDE.md"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "docs" / "USER_GUIDE_REVIEW.md"
MODEL = "gemma4:31b-cloud"

PROMPT = """You are a senior technical writer and documentation reviewer.

You are reviewing the user guide for an open-source project called **Image Description Toolkit (IDT)** — a batch AI-powered tool for generating text descriptions of images and video frames. It has two applications: a CLI tool (`idt`) and a desktop GUI (`ImageDescriber`).

Please carefully review the user guide below and provide a structured review with these sections:

## 1. Summary
Brief summary of what the guide covers.

## 2. Strengths
What the guide does well — organization, clarity, completeness, etc.

## 3. Issues Found
List specific issues you found, organized by category:
- **Missing content** — important topics not covered
- **Outdated or inaccurate information** — anything that seems wrong or stale
- **Inconsistencies** — contradictions within the guide
- **Clarity problems** — unclear explanations, jargon without definition
- **Formatting issues** — broken tables, heading hierarchy, etc.
- **Accessibility gaps** — since this project targets WCAG 2.2 AA

For each issue, cite the section name and quote the relevant text if possible.

## 4. Recommended Updates
A prioritized list of specific changes to make, ranked by importance.

---

Here is the user guide to review:

"""


def main():
    guide_text = GUIDE_PATH.read_text(encoding="utf-8")
    print(f"Loaded user guide: {len(guide_text)} chars, {guide_text.count(chr(10))} lines")

    full_prompt = PROMPT + guide_text + "\n\n---\n\nPlease provide your review now."
    print(f"Prompt size: {len(full_prompt)} chars")
    print(f"Sending to model: {MODEL} ...")

    data = json.dumps({
        "model": MODEL,
        "prompt": full_prompt,
        "stream": False,
        "options": {"temperature": 0.3, "num_ctx": 32768},
    }).encode("utf-8")

    req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=data,
        headers={"Content-Type": "application/json"},
    )

    try:
        resp = urllib.request.urlopen(req, timeout=600)
        result = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    review = result.get("response", "")
    if not review:
        print("ERROR: No response from model", file=sys.stderr)
        sys.exit(1)

    # Print to stdout
    print("\n" + "=" * 80)
    print("MODEL REVIEW")
    print("=" * 80 + "\n")
    print(review)

    # Save to file
    OUTPUT_PATH.write_text(
        f"<!-- AI-generated review of USER_GUIDE.md by {MODEL} on 2026-07-01 -->\n\n"
        f"{review}\n",
        encoding="utf-8",
    )
    print(f"\n\nReview saved to: {OUTPUT_PATH}")
    print(f"Eval count (output tokens): {result.get('eval_count', 'N/A')}")
    print(f"Prompt eval count (input tokens): {result.get('prompt_eval_count', 'N/A')}")


if __name__ == "__main__":
    main()