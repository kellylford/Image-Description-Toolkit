# OpenAI Support Case 05757486 - gpt-5-nano Empty Response Issue

**Date**: February 14-15, 2026  
**Case Number**: 05757486  
**Issue**: gpt-5-nano-2025-08-07 returns HTTP 200 with empty content in ~28-40% of batch requests

---

## Overview

This directory contains all documentation, analysis scripts, test results, and support materials related to the OpenAI API issue where gpt-5-nano model returns empty responses while billing for full completion tokens.

**Key Finding**: Model completes successfully with `finish_reason="length"` and charges for full `completion_tokens` (1000 or 300), but `message.content` is empty string (length 0). This indicates generated output is lost/corrupted, not aborted during inference.

---

## Files in This Archive

### Primary Documentation

- **OPENAI_SUPPORT_REPORT.md** - Comprehensive bug report submitted to OpenAI support
  - Production data: 3,236 requests, 900 empty (27.8%)
  - Terminal testing: Phase 1, 2, 3 results
  - ChatGPT support analysis (hypothesis proven wrong)
  - Updated questions for OpenAI engineering

- **TEST_RESULTS_SUMMARY.md** - Executive summary of systematic testing
  - Phase 1: Model validation (12 requests)
  - Phase 2: Baseline test (100 requests, 39% empty)
  - Phase 3: Optimized test (100 requests, 40% empty)
  - Conclusion: ChatGPT recommendations failed, parameter tuning had no effect

- **openai_support_case_data.txt** - Formatted diagnostic data for case 05757486
  - Org ID, response IDs, full JSON responses
  - Ready to copy/paste into support ticket reply

### Testing Infrastructure

- **test_openai_models.py** - Terminal-based systematic testing script
  - Phase 1: 3 images × 4 models (validation)
  - Phase 2: 100 images, max_tokens=1000, no conversion (baseline)
  - Phase 3: 100 images, max_tokens=300, PNG→JPEG conversion (optimized)
  - Comprehensive logging of finish_reason, completion_tokens, response_id

- **extract_support_data.py** - Script to extract diagnostic data from test results
  - Formats response IDs, usage stats, full JSON for OpenAI support
  - Generates openai_support_case_data.txt

### Analysis Scripts

- **analyze_workspace.py** - Analyzes production workspace files
  - Identifies empty vs successful responses
  - Extracts failure patterns by file type, size, content

- **analyze_both_batches.py** - Compares Batch 1 and Batch 2
  - Identifies consistently failing images (159 total)
  - Identifies intermittently failing images (275 total)
  - File type correlation analysis

- **analyze_empty_patterns.py** - Pattern analysis across failures
  - PNG: 59.1% failure rate
  - HEIC: 28.3% failure rate
  - JPG: 26.5% failure rate

- **analyze_failure_timing.py** - Temporal analysis of failures
  - First failure at position #1 (not cumulative)
  - First 100: 35-38% failure rate
  - Stabilizes at ~28% around 300 images

- **diagnose_performance.py** - UI performance monitoring (related issue)
  - Used to diagnose UI freezing during batch processing
  - Led to discovery of refresh_image_list() bottleneck

### Test Results (test_results/)

- **phase1_model_validation_20260215_090851.json** - 12 requests
  - gpt-5-nano: 0 empty (small batch works fine)
  - gpt-4o, gpt-4o-mini: 0 empty (control)
  - gpt-4-turbo: 3 errors (doesn't support vision)

- **phase2_nano_baseline_20260215_092037.json** - 100 requests
  - Success: 2 (2%)
  - Empty: 39 (39%)
  - Errors: 59 (HEIC/MOV format rejected)
  - ALL empty: finish_reason="length" + completion_tokens=1000 + content=""

- **phase3_nano_optimized_20260215_092821.json** - 100 requests
  - Success: 0 (0%)
  - Empty: 40 (40%)
  - Errors: 60 (HEIC/MOV format rejected)
  - ChatGPT recommendations had NO EFFECT

- **test_run.log** - Complete test execution log
  - Timestamps, request details, response metadata
  - Finish reason distribution, token counts

### Planning Documents

- **2026-02-15-NANO_TESTING_STRATEGY.md** - Systematic test plan
  - 4-phase approach (validation → baseline → optimized → extended)
  - Cost estimates, expected outcomes, deliverables
  - Created after user identified "random mode" problem

- **MODEL_PARAMETER_CONSTRAINTS_PROPOSAL.md** - Architecture proposal
  - GitHub issue #92 content
  - Proposes model-specific parameter validation
  - Prevents invalid parameters like temperature=0.2 for gpt-5-nano

---

## Key Evidence

### Production Impact

- **3,236 total requests** across 2 batches (Feb 14-15, 2026)
- **900 empty responses** (27.8% failure rate)
- **~450,000 wasted completion tokens** (~$0.45+ cost for no content)
- OpenAI billing confirmed: 3,171 logged requests (98% match)

### Testing Impact

- **Phase 2**: 39/100 (39%) - ALL with finish_reason="length" + 1000 tokens + empty content
- **Phase 3**: 40/100 (40%) - Same pattern with 300 tokens
- **Phase 1**: 0/12 (0%) - Small batches work fine

### Critical Pattern

```json
// FAILED REQUEST (typical)
{
  "finish_reason": "length",           // Model hit max_tokens limit
  "completion_tokens": 1000,            // Generated FULL 1000 tokens
  "message.content": ""                 // BUT content is EMPTY
}

// SUCCESSFUL REQUEST (comparison)  
{
  "finish_reason": "stop",             // Normal completion
  "completion_tokens": 952,             // Actual token count
  "message.content": "The image..."    // Content present
}
```

**Conclusion**: Model successfully completes generation and hits token limit, but generated text is lost/corrupted in response. This is NOT early abort (ChatGPT was wrong), NOT parameter misconfiguration, and NOT content-dependent (same images succeed in small batches).

---

## OpenAI Support Status

- **Case Number**: 05757486
- **Contact**: support@openai.com
- **Submitted**: February 15, 2026
- **Status**: Awaiting engineering investigation
- **Response IDs provided**:
  - `chatcmpl-D9Y5KwHs5DWQ7NduxWFPYdLCm4pFR` (failed)
  - `chatcmpl-D9Y5W0fKBerCdOJKmjDdhWL8UG3xj` (failed)
  - `chatcmpl-D9Y9nHyeJTzlACLuXuFrMp4Vmty8S` (success)

---

## Next Steps

1. ⏳ **Wait for OpenAI response** - Engineering investigation required
2. ⏳ **Request credits/refunds** - ~450K wasted tokens
3. ⏳ **Reprocess 900 failed images** - After OpenAI fix or with gpt-4o
4. ⏳ **Update ImageDescriber** - Deploy diagnostic logging to production

---

## Related GitHub Issues

- **#91**: Empty response bug report
- **#92**: Model parameter constraints architecture proposal

---

## Lessons Learned

1. **ChatGPT support assistant can be wrong** - Hypothesis about early abort was disproven
2. **finish_reason="length" + empty content** - Indicates data corruption, not inference failure
3. **Small batches hide batch-dependent bugs** - 3 images = 0% empty, 100 images = 40% empty
4. **HTTP 200 doesn't mean success** - Need to check response content, not just status code
5. **Parameter tuning won't fix model bugs** - max_tokens, PNG conversion had zero effect
6. **Model constraints are undocumented** - gpt-5-nano temperature fixed at 1, ChatGPT recommended invalid value
7. **Systematic testing is critical** - User correctly identified "random mode" and demanded structured approach

---

## Archive Date

February 15, 2026
