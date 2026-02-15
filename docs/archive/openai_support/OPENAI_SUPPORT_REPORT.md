# OpenAI API Issue Report: gpt-5-nano Returns Empty Descriptions in ~28% of Batch Requests

**Date**: February 15, 2026  
**API Key ID**: key_T7xE57pK4Tu54dhL  
**Model**: gpt-5-nano-2025-08-07  
**Issue**: Consistent 28% empty response rate during batch image description processing

---

## Executive Summary

We are experiencing a reproducible issue where the gpt-5-nano model returns HTTP 200 success responses with **empty text content** for approximately **28% of vision API requests** during batch processing. This occurs consistently across multiple days and is costing us significant API fees for non-functional responses.

**Impact**: 
- ~900 empty responses out of 3,236 total requests
- Estimated cost: ~2 million wasted input tokens (images sent but no description returned)
- 28% failure rate is consistent across different batches and time periods

---

## Technical Details

### API Usage Pattern
- **Application**: Batch image description tool using OpenAI Python SDK  
- **Production Request Rate**: ~5-7 requests per minute during batch processing (~0.1 requests/second)
- **Terminal Test Rate**: ~7-9 seconds per request (similar to production)
- **Request Size**: Average 2,200 input tokens per image (base64-encoded)
- **Expected Response**: Text descriptions of images (typically 50-150 tokens)
- **Actual Behavior**: 28-40% of responses contain empty string in `choices[0].message.content`
- **Note**: Production batches show 28% empty rate, terminal tests show 40-100% empty rate (unknown why)

### Code Sample
```python
# Simplified version of our API call
client = OpenAI(api_key=api_key)
response = client.chat.completions.create(
    model="gpt-5-nano-2025-08-07",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
        ]
    }],
    max_tokens=1000,
    temperature=0.7
)

# This returns "" for 28% of requests:
description = response.choices[0].message.content
```

### Request Characteristics
- **Status Code**: Always HTTP 200 (success)
- **Response Time**: 7-9 seconds (normal, not timeouts)
- **Token Usage**: Input tokens charged (image was processed), output tokens minimal
- **Error Logs**: No exceptions, no rate limit errors (429), no content moderation flags

---

## Reproduction Evidence

### Dataset Statistics (Two Separate Batches)

**Batch 1** - February 14, 2026 (7:11 PM - 11:30 PM):
- Total requests: 1,807
- Empty responses: 500
- Failure rate: 27.7%

**Batch 2** - February 15, 2026 (12:50 AM - 5:24 AM):
- Total requests: 1,429
- Empty responses: 400
- Failure rate: 28.0%

**Combined**: 3,236 requests → 900 empty (27.8% average)

### OpenAI Dashboard Confirmation
Your usage dashboard shows:
- Feb 14: 2 logged requests
- Feb 15: 3,169 logged requests
- Total: 3,171 requests (98% match with our count)

Token usage logged:
- Input tokens: 6,972,809
- Output tokens: 2,635,114

**This confirms we are being billed for empty responses.**

---

## Failure Pattern Analysis

### 1. Content-Specific Failures (Concerning)
**159 images consistently fail across multiple attempts:**
- Example: `IMG_3140.PNG` failed 3 times
- Example: `IMG_3137.PNG` failed 2 times (but succeeded with gpt-4o)
- Example: `photo-10587_singular_display_fullPicture.heic` failed 2 times

**However**: Manual testing shows these same images **succeed** when sent individually outside of batch processing. This suggests the issue is not purely content-based.

### 2. Intermittent Failures (More Concerning)
**275 images show random behavior:**
- Same image fails in Batch 1, succeeds in Batch 2
- Same image succeeds in Batch 1, fails in Batch 2
- No consistent pattern

### 3. File Type Correlation
| Type  | Failed | Total | Failure Rate |
|-------|--------|-------|--------------|
| .png  | 13     | 22    | **59.1%**    |
| .heic | 579    | 2,049 | **28.3%**    |
| .jpg  | 308    | 1,163 | **26.5%**    |
| .jpeg | 0      | 2     | 0.0%         |

PNG files show significantly higher failure rate, but all formats are affected.

### 4. File Size Analysis
- Average failed image: Similar size to successful images
- No correlation found between file size and failure

---

## Comparison with Other Models

### gpt-4o-2024-08-06 (Control Test)
- Same images processed with gpt-4o: **0% empty response rate**
- Example: `IMG_3137.PNG` failed 2x with gpt-5-nano, succeeded with gpt-4o
- Processing time: 4-5 seconds (faster than gpt-5-nano)
- Cost: Higher per token, but 100% success rate

**Conclusion**: This appears specific to gpt-5-nano model.

---

## User Impact

### Financial
- Paying for ~900 failed requests
- Input tokens charged even when response is empty
- Estimated waste: ~2 million input tokens × pricing

### Operational
- 28% of batch jobs require reprocessing
- Manual intervention needed to identify and retry failures
- Cannot trust batch completion status

### Data Quality
- Empty descriptions saved as "completed" 
- Users unaware of failures unless manually inspected
- Workflow results incomplete

---

## Questions for OpenAI Support

1. **Is this a known issue with gpt-5-nano?** 
   - Are there rate limits or batch processing constraints not documented?
   - Is gpt-5-nano stable enough for production use?

2. **Why do responses return HTTP 200 with empty content?**
   - Shouldn't failed requests return proper error codes?
   - What does `finish_reason` indicate for these responses?

3. **Why do the same images fail intermittently?**
   - 275 images succeed sometimes, fail other times
   - Manual retries succeed - suggests timing/load issue

4. **Is there internal throttling causing empty responses?**
   - Instead of 429 errors, are you returning empty content?
   - Should we add delays between requests?

5. **Are we being refunded for empty responses?**
   - Input tokens charged even when output is empty
   - Should we receive credits for non-functional responses?

6. **What's the recommended approach?**
   - Should we implement automatic retry logic?
   - Should we switch to gpt-4o for batch processing?
   - Are there batch API endpoints that handle this better?

---

## Temporary Workarounds Implemented

1. **Empty response detection**: Checking for `content.strip() == ''`
2. **Manual reprocessing**: Identifying failed items and re-running
3. **Model switching**: Some users switching to gpt-4o (more expensive but reliable)

---

## Request for Assistance

We need guidance on:
1. Root cause of 28% empty response rate
2. Whether this is expected behavior or a bug
3. Best practices for batch image processing with gpt-5-nano
4. Potential credits/refunds for failed API calls
5. Recommended solution (retry logic, delays, different model, etc.)

---

## Supporting Data Available

We can provide (if helpful):
- Raw workspace files with all request/response data
- Specific image files that consistently fail
- Detailed timestamps of all 3,236 requests
- API response logs
- Additional testing results

---

## Contact Information

[Your name/email will go here when you send this]

---

## Addendum: Analysis from OpenAI ChatGPT Support Assistant

After creating this report, we consulted OpenAI's ChatGPT support assistant. Their analysis and our evaluation follows:

### ChatGPT's Assessment

**Probable Root Cause** (65% confidence):
> "Internal nano-tier inference guardrail - silent internal generation abort"

**Failure Pattern Interpretation**:
- HTTP 200 responses with empty content suggest **inference generation starts but aborts early**
- Likely behavior: Vision encoder processes image (billing input tokens), but decoder produces no text
- Returns `finish_reason: "stop"` with `completion_tokens: 0` instead of proper error code
- This is characteristic of internal load shedding or compute reservation limits

**Why gpt-5-nano Specifically**:
> "Nano models often use smaller decoder heads, more aggressive early-stop heuristics, and heavier load balancing"

**PNG Files 59% Failure Rate Explained**:
> "PNG images are lossless, have larger encoded token footprint, and may exceed internal soft compute thresholds even if total tokens are allowed"

### Recommended Immediate Actions

**ChatGPT's Tier 1 Recommendations**:
1. ✅ **Add logging for diagnostic data** - Currently missing:
   - `response.choices[0].finish_reason`
   - `response.usage.completion_tokens`  
   - `response.id`
   - `response.model`

2. ✅ **Reduce max_tokens from 1000 → 300**
   - Theory: Large max_tokens reserves more compute, potentially triggering nano-tier scheduling aborts
   - Our responses average 50-150 tokens, so 1000 is excessive

3. ❌ **Lower temperature from 0.7 → 0.2** - **FAILED**
   - Quote: "Nano models can sometimes collapse at higher temps under load"
   - **ACTUAL RESULT**: gpt-5-nano returns 400 error:
     ```
     Unsupported value: 'temperature' does not support 0.2 with this model. 
     Only the default (1) value is supported.
     ```
   - **Model constraint**: gpt-5-nano has FIXED temperature=1 (cannot be customized)
   - **ChatGPT error**: Support assistant recommended invalid parameter

4. ✅ **Convert PNG → JPEG before sending**
   - Targets the 59% PNG failure rate
   - 85-90% JPEG quality, max 1600px dimension
   - Reduces token footprint significantly

**ChatGPT's Tier 2 Recommendations (NOT IMPLEMENTED - Cost Concerns)**:
5. ⚠️ **Automatic retry with fallback to gpt-4o** - REJECTED
   - Would charge users for both nano + 4o attempts
   - User explicitly requested no automatic model switching

6. ❌ **Use `client.responses.create()` API** - CANNOT VERIFY
   - No documentation found for this endpoint in OpenAI Python SDK
   - May be future API or ChatGPT hallucination

### Our Evaluation

**Agree with ChatGPT**:
- ✅ Diagnostic logging is critical - need to see actual `finish_reason` and `completion_tokens`
- ✅ Parameter tuning (max_tokens, temperature) is low-risk, may help
- ✅ PNG → JPEG conversion targets highest failure rate (59%)
- ✅ This does NOT appear to be client-side misuse

**Disagree with ChatGP**:
- ❌ Automatic fallback to gpt-4o violates cost constraints
- ❌ Cannot verify `responses.create()` API exists

**Additional Findings - Failure Timing**:
After analyzing both batches:
- **First failure occurs at position #1** (very first request in both batches)
- **First 100 images**: 35-38% failure rate (HIGHER than 28% average)
- **First 200 images**: 29.5-35.5% failure rate
- **Stabilizes around 300**: 27.7-34.0% (converges to ~28% overall)

**Implication**: Failures are NOT related to cumulative load or sustained rate - they happen immediately from the start.

### Implementation Plan

**Implemented Changes**:
1. ✅ Added comprehensive logging (`finish_reason`, `completion_tokens`, `response.id`, `usage`)
2. ✅ Reduced `max_tokens` from 1000 → 300
3. ❌ ~~Lowered `temperature` from 0.7 → 0.2~~ - **FAILED** (model does not support custom temperature)
4. ✅ Added PNG → JPEG conversion (85% quality, max 1600px)

**Temperature Discovery**:
After implementing ChatGPT's recommendation #3, we discovered gpt-5-nano **rejects all requests** with 400 error:
> `"Unsupported value: 'temperature' does not support 0.2 with this model. Only the default (1) value is supported."`

This reveals:
- gpt-5-nano has a **fixed temperature of 1** (no user control)
- ChatGPT's support assistant provided **invalid recommendation**
- This may explain instability - users cannot tune temperature for consistency

**Test Plan**:
- Run batch of 200-300 images with new parameters
- Analyze `finish_reason` distribution in failed responses
- Compare failure rate with baseline (current 28%)
- Report findings to OpenAI with actual response metadata

### Test Results (February 15, 2026 - Systematic Terminal Testing)

We conducted comprehensive terminal-based testing to isolate the issue and validate ChatGPT's recommendations.

#### Phase 1: Model Validation (3 images × 4 models = 12 requests)

**Purpose**: Verify gpt-5-nano is the only problematic model

**Results**:
- gpt-5-nano: 0 empty responses  
- gpt-4o: 0 empty responses
- gpt-4o-mini: 0 empty responses
- gpt-4-turbo: 3 errors (model doesn't support vision API)
- HEIC format: 3 errors (API rejected HEIC files)

**Conclusion**: Could NOT reproduce empty response issue with small sample (3 images). Suggests issue is batch-size or duration dependent.

---

#### Phase 2: gpt-5-nano Baseline (100 images, original parameters)

**Parameters**: 
- Model: gpt-5-nano-2025-08-07
- max_tokens: 1000
- PNG conversion: OFF (baseline behavior)

**Results**:
- Total requests: 100
- ✅ Success: 2 (2%)
- ⚠️ **Empty: 39 (39%)**
- ❌ Errors: 59 (59% - HEIC/MOV format rejected)

**Empty Response Pattern**:
- ALL 39 empty responses: `finish_reason="length"` + `completion_tokens=1000`
- Model generates FULL 1000 tokens but `message.content=""` 
- We're being billed for 1000 completion tokens per failed request

**Failure by File Type**:
- JPG: 39/41 empty (**95.1% failure rate!**)
- HEIC/MOV: API format errors (not counted as empty)

**Critical Discovery - ChatGPT's Hypothesis is COMPLETELY WRONG**:

ChatGPT predicted empty responses would show:
- finish_reason: "stop" (inference abort)
- completion_tokens: 0 (no output generated)

**Actual data from ALL 39 empty responses**:
```json
{
  "text": "",
  "finish_reason": "length",           // ← Hit max_tokens limit!
  "completion_tokens": 1000,            // ← Generated FULL 1000 tokens!
  "prompt_tokens": 2242,                // ← Charged for input
  "total_tokens": 3242,                 // ← Charged for 1000 output tokens
  "response_id": "chatcmpl-D9Y5KwHs5DWQ7NduxWFPYdLCm4pFR"
}
```

**Implication**: The model IS generating tokens and hitting the max_tokens limit, but:
- finish_reason="length" indicates successful generation (not abort)
- completion_tokens matches max_tokens exactly (model generated full output)
- BUT `choices[0].message.content` is empty string
- This suggests the output is being **generated but lost/corrupted**, NOT aborted during inference

---

#### Phase 3: gpt-5-nano Optimized (100 images, ChatGPT recommendations)

**Parameters**: 
- Model: gpt-5-nano-2025-08-07
- **max_tokens: 300** (reduced from 1000)
- **PNG→JPEG conversion: ON** (85% quality, 1600px max)
- Temperature: NOT changed (gpt-5-nano rejects custom values, fixed at 1)

**Results**:
- Total requests: 100
- ✅ Success: 0 (0%)
- ⚠️ **Empty: 40 (40%)**
- ❌ Errors: 60 (60% - HEIC/MOV format rejected)

**Empty Response Pattern**:
- ALL 40 empty responses: `finish_reason="length"` + `completion_tokens=300`
- Same behavior as Phase 2, just with 300 tokens instead of 1000

**Failure by File Type**:
- JPG: 39/39 empty (**100% failure rate!**)
- PNG: 1/1 empty (**100% failure rate!**)
- HEIC/MOV: API format errors (conversion function didn't handle these)

**Conclusion: ChatGPT's Recommendations DID NOT HELP**:
- Empty rate: 40% (Phase 3) vs 39% (Phase 2) - NO IMPROVEMENT
- ALL JPG/PNG files returned empty responses (100% failure!)
- Reducing max_tokens from 1000→300 made NO DIFFERENCE
- PNG→JPEG conversion made NO DIFFERENCE
- The issue is NOT related to parameter tuning

---

### Critical Findings Summary

1. **ChatGPT's hypothesis was completely wrong**: Model IS generating tokens (finish_reason="length", completion_tokens matches requested max_tokens exactly), not aborting early.

2. **We're being billed for empty responses**: Each empty response charges for FULL completion_tokens (1000 or 300 depending on request) even though content is empty.

3. **ChatGPT's recommendations failed**:
   - Reducing max_tokens: No effect (still 40% empty)
   - PNG→JPEG conversion: No effect (still 100% failure on images)
   - Temperature tuning: Rejected by model (fixed at 1)

4. **Terminal testing shows WORSE behavior** (95-100% empty rate on JPG/PNG) than production batches (28%). Unknown why test environment differs from production.

5. **Batch size dependency**: Small test (3 images) showed 0% empty rate, but 100-image tests show 40% empty rate. Suggests issue may be cumulative or requires sustained load.

**Updated Questions for OpenAI**:
1. **Why do responses with `finish_reason="length"` and `completion_tokens=1000/300` have empty `message.content`?**
2. **Is there a known bug in gpt-5-nano where generated tokens don't populate the content field?**
3. **Why does the model hit max_tokens limit but return empty content?** This suggests output is generated then lost/corrupted.
4. **Are completion_tokens being counted correctly?** Or is this a metering bug charging for tokens that weren't actually generated?
5. **Why do smaller batches (3 images) work fine but larger batches (100+ images) show 40-100% failure?**
6. **Should we receive refunds for completion_tokens charged on empty responses?** We paid for 39,000+ tokens (39×1000 + 40×300) that contain no content.

---

## Appendix: Sample Empty Response Entry

```json
{
  "filename": "IMG_3137.PNG",
  "descriptions": [
    {
      "id": "1771118634822",
      "text": "",
      "model": "gpt-5-nano",
      "created": "2026-02-14T19:23:54",
      "processing_time_seconds": 7.72,
      "prompt_style": "detailed"
    }
  ]
}
```

This same image succeeded with gpt-4o:
```json
{
  "id": "1771135354546",
  "text": "This image is a flight map showing a transatlantic flight path from Chicago O'Hare International Airport (ORD) to London Heathrow Airport (LHR)...",
  "model": "gpt-4o",
  "created": "2026-02-15T00:02:34",
  "processing_time_seconds": 4.6,
  "tokens_used": 98
}
```
