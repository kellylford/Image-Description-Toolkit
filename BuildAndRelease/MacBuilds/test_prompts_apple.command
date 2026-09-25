#!/bin/bash
# ============================================================================
# Run every built-in prompt against one image with the Apple Intelligence
# provider, using the built CLI in dist_all.
# ============================================================================
# Why this exists: Apple's on-device model refuses some images, and which
# prompt it refuses is not predictable from the prompt's meaning. This runs all
# twelve and prints which were described and which were declined.
#
# Usage:
#   ./test_prompts_apple.command                  # the taxidermy photo
#   ./test_prompts_apple.command /path/to/pic.jpg # any image
#
# Each run starts the frozen CLI from scratch (~20s of that is unpacking the
# onefile binary and starting `fm serve`), so the whole sweep takes 4-5 minutes.
# ============================================================================

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IDT="$SCRIPT_DIR/dist_all/idt"
IMAGE="${1:-/Users/kellyford/Documents/September/Alaska and More - 239 of 402.jpeg}"

PROMPTS=(narrative detailed concise artistic technical colorful
         simple accessibility comparison mood functional aialttext)

if [ ! -x "$IDT" ]; then
    echo "ERROR: no built CLI at $IDT"
    echo "Build it first, or point this script at another dist_all."
    exit 1
fi
if [ ! -f "$IMAGE" ]; then
    echo "ERROR: no such image: $IMAGE"
    exit 1
fi

WORK="$(mktemp -d "${TMPDIR:-/tmp}/idt-prompt-sweep-XXXXXX")"
# One folder holding just this image: `idt describe` takes a directory.
mkdir -p "$WORK/img"
cp "$IMAGE" "$WORK/img/"
trap 'rm -rf "$WORK"' EXIT

echo "Image:    $(basename "$IMAGE")"
echo "CLI:      $IDT"
echo "Provider: apple (on-device)"
echo
printf '%-16s %-10s %s\n' "PROMPT" "RESULT" "SECONDS"
printf '%-16s %-10s %s\n' "----------------" "----------" "-------"

described=0
refused=0
other=0

for prompt in "${PROMPTS[@]}"; do
    start=$(date +%s)
    output=$("$IDT" describe "$WORK/img" \
        --provider apple --prompt "$prompt" \
        --workspace "$WORK/ws_$prompt" 2>&1)
    elapsed=$(( $(date +%s) - start ))

    # ": done" is what the per-image progress line prints on success. The
    # refusal is matched on the provider's own wording, so a different failure
    # (no licence, Apple Intelligence off) is reported as OTHER rather than
    # being silently counted as a refusal.
    if grep -q ': done' <<<"$output"; then
        result="described"; described=$((described + 1))
    elif grep -qi 'guardrail\|declined to describe' <<<"$output"; then
        result="REFUSED"; refused=$((refused + 1))
    else
        result="OTHER"; other=$((other + 1))
    fi

    printf '%-16s %-10s %ss\n' "$prompt" "$result" "$elapsed"
    if [ "$result" = "OTHER" ]; then
        grep -E 'Error|error:' <<<"$output" | head -2 | sed 's/^/                 /'
    fi
done

echo
echo "described=$described  refused=$refused  other=$other  (of ${#PROMPTS[@]})"
echo
echo "A refusal is stable for an exact prompt string but does not track meaning:"
echo "the same image can be refused under one style and described under another."
echo "See docs/apple-intelligence-safety-refusals.md"
