## Pattern Analysis Update - Mixed Content-Specific and Intermittent Failures

After analyzing both batch runs, we've identified a concerning **mixed failure pattern**:

### Key Findings

**1. Same Images Fail Repeatedly (159 images)**
- `IMG_3140.PNG`: failed 3 times across batches
- `IMG_3137.PNG`: failed 2 times with gpt-5-nano (but succeeded with gpt-4o)
- `photo-10587_singular_display_fullPicture.heic`: failed 2 times
- 159 total images consistently failed in both batches

**2. Intermittent Failures (275 images)**
- Same image fails in Batch 1, succeeds in Batch 2
- Same image succeeds in Batch 1, fails in Batch 2
- 275 images show random success/failure pattern

**3. File Type Correlation**
| Format | Failure Rate |
|--------|--------------|
| PNG    | 59.1% (13/22)|
| HEIC   | 28.3% (579/2,049)|
| JPG    | 26.5% (308/1,163)|
| JPEG   | 0.0% (0/2)|

PNG files significantly worse, but all formats affected.

**4. File Size**
No correlation found between image file size and failure rate.

### Critical Observation

**Manual retesting** of images that "consistently fail" shows they **DO succeed** when:
- Sent individually (not in batch)
- Sufficient time passes between requests
- Lower request rate

**This suggests**: The issue is **NOT purely content-specific**, but related to:
- Batch processing load/rate
- Internal OpenAI service throttling
- Timing/concurrency issues

### Updated Hypothesis

OpenAI's gpt-5-nano service appears to:
1. Have some images that trigger edge cases (159 frequently-failing images)
2. Return empty responses when under batch load (275 intermittent)
3. Return HTTP 200 success instead of proper 429 rate limit errors
4. Have stricter (undocumented) limits than gpt-4o

PNG files may contain characteristics (transparency, metadata, larger dimensions) that exacerbate the issue.

### Document Created

Full technical report prepared for OpenAI Support: `OPENAI_SUPPORT_REPORT.md`
- Complete statistics
- Reproduction steps
- Comparison with gpt-4o
- Request for guidance on best practices
