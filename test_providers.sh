#!/bin/bash
# Test script to verify all provider batch files work correctly
# This script tests each provider with a sample image

set -e  # Exit on error

PROJECT_ROOT="/c/Users/kelly/GitHub/idt"
TEST_IMAGE="$PROJECT_ROOT/tests/test_files/images/blue_landscape.jpg"

cd "$PROJECT_ROOT"

echo "============================================================================"
echo "Testing AI Provider Batch Files"
echo "============================================================================"
echo ""
echo "Test image: $TEST_IMAGE"
echo ""

# Test 1: ONNX (most likely to work without external dependencies)
echo "============================================================================"
echo "Test 1: ONNX Provider (florence-2-large)"
echo "============================================================================"
python scripts/workflow.py "$TEST_IMAGE" \
  --steps describe \
  --provider onnx \
  --model florence-2-large \
  --prompt-style narrative

if [ $? -eq 0 ]; then
    echo "✓ ONNX test PASSED"
    # Check if description was created
    LATEST_WF=$(ls -td wf_onnx_* 2>/dev/null | head -1)
    if [ -n "$LATEST_WF" ] && [ -f "$LATEST_WF/descriptions/descriptions.txt" ]; then
        echo "✓ Description file created: $LATEST_WF/descriptions/descriptions.txt"
        echo "  Content preview:"
        head -5 "$LATEST_WF/descriptions/descriptions.txt" | sed 's/^/    /'
    else
        echo "⚠ Warning: Description file not found"
    fi
else
    echo "✗ ONNX test FAILED"
fi

echo ""
echo "============================================================================"
echo "Test Summary"
echo "============================================================================"
echo ""
echo "ONNX Provider: Tested"
echo ""
echo "Note: Other providers (Ollama, OpenAI, HuggingFace, Copilot) require:"
echo "  - Ollama: Local installation and models"
echo "  - OpenAI: API key file"
echo "  - HuggingFace: API token file"
echo "  - Copilot: GitHub Copilot subscription and GitHub CLI"
echo ""
echo "To test these, set up the provider and run:"
echo "  python scripts/workflow.py \"<image>\" --provider <provider> --model <model> --prompt-style narrative"
echo ""
