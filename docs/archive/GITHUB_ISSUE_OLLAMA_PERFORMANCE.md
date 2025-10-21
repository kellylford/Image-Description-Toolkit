# GitHub Issue: Ollama Cloud Performance Issues - 20-40 Minute Processing Times

## Summary
Ollama cloud models (qwen3-vl:235b-cloud) are experiencing severe performance issues with 20-40 minute processing times for 25 images compared to Claude's 3-5 minutes. The root cause appears to be frequent HTTP 500 errors requiring extensive retry cycles.

## Problem Details

### Performance Comparison
| Provider | Model | Time Range | Avg Time/Image | Success Rate | Retries Needed |
|----------|-------|------------|----------------|--------------|----------------|
| Claude Haiku | claude-3-haiku-20240307 | 2m 51s | 5.09s | 24/25 (96%) | 0 |
| Claude Haiku 3.5 | claude-3-5-haiku-20241022 | 5m 7s | 10.61s | 24/25 (96%) | 0 |
| Ollama Cloud | qwen3-vl:235b-cloud | 29-40m | 69-95s | 24-25/25 (96-100%) | Extensive |

### Specific Ollama Issues

**1. Extreme Processing Time Variability:**
- Successful requests: 8.86s - 11.45s per image
- Failed requests requiring retries: 137s - 520s per image
- 60x difference between fastest and slowest processing times

**2. Frequent HTTP 500 Errors:**
```
ResponseError: unmarshal: invalid character 'I' looking for beginning of value (status code: 500)
```
- Pattern: Most images require 1-3 retry attempts
- Some images fail all 4 retry attempts completely
- Error appears to be server-side JSON parsing issues

**3. Retry Overhead:**
- Current exponential backoff: 2s, 4s, 8s delays
- Each retry attempt includes full processing time (2+ minutes)
- Total overhead per failed image: 2-8 minutes of delays + 4-12 minutes of reprocessing

**4. Complete Failures:**
- IMG_4284.jpg failed all 4 attempts in one workflow (518s total)
- Same image processed successfully in other workflows
- Indicates server instability rather than image-specific issues

## Root Cause Analysis

### Server Instability Pattern
The "unmarshal: invalid character 'I'" error suggests:
1. **Incomplete JSON responses** from Ollama cloud servers
2. **Server overload** causing truncated responses
3. **Network timeout** issues during response transmission
4. **Server-side processing failures** returning HTML error pages instead of JSON

### Current Retry Logic Issues
1. **Exponential backoff too aggressive** for server errors (should be faster)
2. **No circuit breaker** to detect widespread server issues
3. **No timeout management** allowing 8+ minute individual requests
4. **No request optimization** to reduce server load

## Test Data Summary

**Ollama Workflows Analyzed (Pre-optimization):**
- `wf_cottage_ollama_qwen3-vl_235b-cloud_artistic_20251021_063206` (33m 43s)
- `wf_cottage_ollama_qwen3-vl_235b-cloud_narrative_20251021_064730` (29m 31s) 
- `wf_cottage_ollama_qwen3-vl_235b-cloud_Simple_20251021_071007` (40m 18s)

**Post-Optimization Test (October 21, 2025 10:00 AM):**
- `wf_cottage_ollama_qwen3-vl_235b-cloud_artistic_20251021_100122`
- **Performance Observations:**
  - Successful images: ~9-10 seconds processing (consistent with pre-optimization)
  - Timeout at 90 seconds triggers fast retry (0.6s delay)
  - Example recovery: Image 1 failed at 90s timeout, succeeded immediately on 2nd attempt (total: ~100s)
  - **Key finding:** When working, 5-10 second processing time. When failing, now 90s timeout + fast retry vs. previous unbounded waits

**Retry Patterns Observed (Pre-optimization):**
- IMG_4276: Failed attempt 1, succeeded attempt 2 (138s total)
- IMG_4279: Failed attempts 1-2, succeeded attempt 3 (270s total)
- IMG_4284: Failed all 4 attempts (518s total)
- IMG_4295: Failed attempts 1-3, succeeded attempt 4 (406s total)
- IMG_4300: Failed attempt 1, succeeded attempt 2 (137s total)

## Proposed Solutions (Short-term)

### 1. Aggressive Retry Optimization (Priority 1) ✅ **IMPLEMENTED**
```python
# Previous: [2s, 4s, 8s] - too slow for server errors
# Implemented: [0.5, 1.0, 2.0] - faster recovery for transient issues
retry_delays = [0.5, 1.0, 2.0]  # scripts/image_describer.py line 505
```
**Status:** Working as of October 21, 2025 10:00 AM
- Fast retry delays with minimal jitter (0.1-0.3x base)
- Retries triggered on HTTP 500, timeouts, unmarshal errors
- Max 4 attempts total (initial + 3 retries)

### 2. Request Timeout Management (Priority 1) ✅ **IMPLEMENTED**
```python
# Implemented with 90-second timeout using threading
# See: scripts/image_describer.py lines 510-555
OLLAMA_REQUEST_TIMEOUT = 90  # seconds (actual implementation)
```
**Status:** Working as of October 21, 2025 10:00 AM
- Timeout triggers correctly after 90 seconds
- Captured as TimeoutError and retried with fast delays
- Example: `photo-20825_singular_display_fullPicture.jpg` timed out at 90s, succeeded on retry after 0.6s delay

### 3. Circuit Breaker Pattern (Priority 2)
```python
# After 3 consecutive 500 errors, pause processing for 30s
# Detect server instability and provide user feedback
```

### 4. Parallel Processing (Priority 2)
- Process 2-3 images simultaneously
- Could reduce 40min → 15-20min immediately
- Requires threading implementation in CLI path

### 5. Request Optimization (Priority 3)
- Reduce image resolution from 768x1024 to 512x768
- Test if smaller payloads reduce server errors
- Implement progressive image quality (start small, retry larger)

## Expected Impact

| Optimization | Time Reduction | Reliability Improvement |
|-------------|----------------|------------------------|
| Faster retries | 40min → 25min | Same failure rate, faster recovery |
| Request timeout | Prevents 8+min hangs | Fail faster, retry sooner |
| Circuit breaker | +monitoring | Better user experience during outages |
| Parallel processing | 25min → 12min | Same per-image time, concurrent processing |

**Combined Result**: 40min → **8-15min** processing time

## Implementation Priority

**Phase 1 (COMPLETED):**
1. ✅ Reduce retry delays to [0.5s, 1s, 2s] - **IMPLEMENTED** in `scripts/image_describer.py` line 505
2. ✅ Add 90s request timeout (threading-based) - **IMPLEMENTED** in `scripts/image_describer.py` lines 510-555
3. ✅ Enhanced error logging for pattern analysis - **IMPLEMENTED**

**Phase 2 (This week - 4 hours):**
4. 🔄 Implement parallel processing (2-image concurrent)
5. 🔄 Add circuit breaker for server monitoring
6. 🔄 Request optimization testing

## Notes

- **Hybrid Claude fallback rejected** due to complexity of dual API key management and unexpected cost implications
- **Focus on Ollama optimization** rather than provider switching
- **Root cause appears to be Ollama cloud server instability** rather than model or request issues
- **Same images process successfully in different runs**, confirming server-side problems

## Test Environment
- Model: qwen3-vl:235b-cloud
- Image count: 25 HEIC files (converted to JPG)
- Image resolution: 768x1024 (resized)
- Test date: October 21, 2025
- Location: C:\idt\Descriptions\analysis\results\