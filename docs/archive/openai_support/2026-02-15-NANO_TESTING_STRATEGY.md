# gpt-5-nano Empty Response Testing Strategy

**Date**: February 15, 2026  
**Issue**: #91 - gpt-5-nano 28% empty response rate  
**Status**: Systematic testing phase

---

## Problem Statement

We have a 28% empty response rate with gpt-5-nano across 3,236 requests. We need systematic testing to:
1. Validate the issue persists with current code
2. Test ChatGPT's recommendations (max_tokens, PNG conversion)
3. Validate all other OpenAI models work correctly
4. Gather diagnostic data for OpenAI support ticket

---

## Testing Approach: Terminal-Based API Testing

**Why terminal/script testing vs UI**:
- ✅ Faster iteration (no rebuild cycle)
- ✅ Controlled variables (same images, same parameters)
- ✅ Direct API access (no UI complexity)
- ✅ Better logging/debugging
- ✅ Reproducible results

**NOT testing**: UI performance issues (already diagnosed and fixed separately)

---

## Test Configuration

### Image Sample Selection
**Source**: Previous batch workspace files
- `/Users/kellyford/Documents/ImageDescriptionToolkit/workspaces/EuropeNano509_20260214.idw` (1,807 images)
- `/Users/kellyford/Documents/ImageDescriptionToolkit/workspaces/EuropeNano5.idw` (1,429 images)

**Selection Strategy**:
1. **100 random images for gpt-5-nano** (main diagnosis):
   - Mix of previously failed and successful images
   - Include PNG, HEIC, JPG file types
   - Ensure variety of content types

2. **3 test images for model validation**:
   - 1 image that previously failed with gpt-5-nano
   - 1 image that previously succeeded with gpt-5-nano
   - 1 PNG image (59% failure rate baseline)

### OpenAI Models to Test
From `models/manage_models.py`:
- `gpt-5-nano-2025-08-07` (primary issue)
- `gpt-4o` (baseline - 0% failure)
- `gpt-4o-mini` (cost-effective alternative)
- `gpt-4-turbo` (compatibility check)

### Test Parameters

**Baseline Test** (Original Configuration):
```python
max_tokens = 1000
temperature = (default - model doesn't support custom)
PNG conversion = OFF
```

**ChatGPT Recommendation Test**:
```python
max_tokens = 300
temperature = (default - model constraint)
PNG conversion = ON (JPEG 85%, max 1600px)
```

**Comparison Points**:
- Empty response rate
- finish_reason distribution
- completion_tokens vs actual content length
- Processing time
- File type correlation

---

## Test Implementation

### Test Script: `test_openai_models.py`

**Inputs**:
- API key from environment or `scripts/openai.txt`
- Image list (random sample from workspaces)
- Models to test
- Test parameters

**Outputs**:
- JSON results file with detailed response data
- Summary statistics (success/fail counts)
- Diagnostic logs (finish_reason, tokens, response_id)
- Comparison table

**Key Data to Capture**:
```python
{
  "image_path": "...",
  "model": "gpt-5-nano",
  "parameters": {"max_tokens": 300, "png_converted": true},
  "response": {
    "text": "...",
    "text_length": 0,
    "finish_reason": "length",
    "completion_tokens": 300,
    "prompt_tokens": 2200,
    "response_id": "chatcmpl-...",
    "processing_time": 7.2
  },
  "status": "empty" | "success" | "error"
}
```

---

## Test Execution Plan

### Phase 1: Model Validation (3 images × 4 models = 12 requests)
**Purpose**: Verify all OpenAI models work correctly  
**Duration**: ~5 minutes  
**Expected**: 0% failure for gpt-4o/4o-mini/4-turbo, possible failures for gpt-5-nano

### Phase 2: gpt-5-nano Baseline (100 images, original params)
**Purpose**: Replicate 28% failure rate with original configuration  
**Duration**: ~15 minutes (100 images × ~9 seconds)  
**Expected**: ~28 empty responses (validate consistency)

### Phase 3: gpt-5-nano with ChatGPT Recommendations (100 images, modified params)
**Purpose**: Test if max_tokens=300 + PNG conversion reduces failures  
**Duration**: ~15 minutes  
**Expected**: Lower failure rate (if ChatGPT theory is correct)

### Phase 4: Analysis
**Purpose**: Compare results, identify patterns  
**Output**: Updated support document with test results

---

## Success Criteria

### Phase 1 Success:
- ✅ gpt-4o: 3/3 success (0% failure)
- ✅ gpt-4o-mini: 3/3 success (0% failure)
- ✅ gpt-4-turbo: 3/3 success (0% failure)
- ⚠️ gpt-5-nano: Accept any result (baseline for comparison)

### Phase 2 Success:
- ✅ Failure rate 20-35% (validates issue is reproducible)
- ✅ Captures finish_reason, completion_tokens for all failures
- ✅ Identifies pattern (consistent vs intermittent failures)

### Phase 3 Success:
- ✅ Collects data for comparison with Phase 2
- ✅ Documents whether ChatGPT recommendations help

### Phase 4 Success:
- ✅ Clear go/no-go on ChatGPT recommendations
- ✅ Statistical analysis (file type, finish_reason distribution)
- ✅ Ready for OpenAI support submission

---

## Risk Mitigation

**API Cost Control**:
- Phase 1: 12 requests × ~2500 tokens = ~30k tokens ($0.03)
- Phase 2: 100 requests × ~2500 tokens = ~250k tokens ($0.25)
- Phase 3: 100 requests × ~2500 tokens = ~250k tokens ($0.25)
- **Total estimated cost**: ~$0.50

**Rate Limiting**:
- Add 1-second delay between requests
- Handle 429 errors with exponential backoff
- Total runtime: ~45 minutes for all phases

**Error Handling**:
- Log all exceptions with full traceback
- Continue on individual failures
- Save intermediate results

---

## Deliverables

1. **Test Script**: `test_openai_models.py`
2. **Results File**: `test_results_YYYYMMDD_HHMMSS.json`
3. **Summary Report**: Console output with statistics
4. **Updated Support Doc**: `OPENAI_SUPPORT_REPORT.md` with test findings
5. **Session Summary**: `docs/worktracking/2026-02-15-session-summary.md`

---

## Next Steps After Testing

**If Phase 3 shows improvement**:
- Document specific improvements (% reduction)
- Implement in production code
- Submit support ticket with "we found partial mitigation"

**If Phase 3 shows NO improvement**:
- Confirms ChatGPT hypothesis was incorrect
- Submit support ticket with "your recommendations didn't help"
- Include test data showing finish_reason="length" with empty content

**If Phase 1 shows other models fail**:
- STOP - broader API issue or code bug
- Debug before continuing with gpt-5-nano testing

---

## Test Data Preservation

**Keep for OpenAI**:
- All response_id values from failures
- Exact timestamps of requests
- Sample images that failed
- Full response objects (JSON)

**Track Across Tests**:
- Same image tested in multiple configurations
- Track if results are deterministic or random
