# Claude Vision API Best Practices Audit

**Date**: February 21, 2026  
**Reviewer**: GitHub Copilot (Claude Sonnet 4.6)  
**Sources Reviewed**:
- [Claude Vision docs](https://platform.claude.com/docs/en/build-with-claude/vision)
- [Best Practices Cookbook](https://platform.claude.com/cookbook/multimodal-best-practices-for-vision)
- [API Overview – Request Size Limits](https://platform.claude.com/docs/en/api/overview#request-size-limits)

**Project Code Reviewed**:
- `imagedescriber/ai_providers.py`
- `scripts/image_describer.py`
- `scripts/ConvertImage.py`
- `models/claude_models.py`

---

## What the Project Does Well

| Practice | Status |
|---|---|
| Image block placed **before** text block in content array | ✅ Followed — docs and cookbook confirm image-then-text is preferred |
| Correct formats sent (JPEG, PNG, GIF, WebP) for known extensions | ✅ For supported types |
| SDK-level retry (`max_retries=3`) | ✅ Uses official SDK retry behavior |
| Token usage tracked per call | ✅ Reads `message.usage` and accumulates session totals |
| Detailed error handling per HTTP status code | ✅ Covers 401, 429, 400, 5xx, timeout |
| Images sent as base64 | ✅ Valid method per docs |

---

## Issues and Gaps

### 1. `max_tokens=1024` Is Too Low — **High Priority**

**What the docs say**: Cookbook examples consistently use `max_tokens=2048`. Claude 4.x models support up to 64K–128K output tokens.

**What the project does**: `imagedescriber/ai_providers.py` (approximately line 793) hardcodes `max_tokens=1024`.

**Impact**: Detailed image descriptions — especially for the "detailed," "accessibility," or "technical" prompt styles — will be silently truncated mid-sentence whenever the response exceeds 1024 tokens. The stop reason will be `max_tokens` rather than `end_turn`, and the project does not currently warn the user or log a truncation event.

**Recommendation**: Make `max_tokens` configurable in `image_describer_config.json` with a default of at least 4096. Log a warning when `stop_reason == "max_tokens"`.

---

### 2. Image Resize Targets File Size, Not Pixel Dimensions — **High Priority**

**What the docs say**:
> For optimal performance, resize images before uploading if they are too large. If your image's long edge is more than **1568 pixels**, or your image is more than **~1,600 tokens**, it will first be scaled down… To improve time-to-first-token, consider resizing images to no more than **1.15 megapixels** (and within **1568 pixels in both dimensions**).

The API will **reject** images larger than **8000×8000 px**. When more than 20 images are sent in one request, the cap drops to **2000×2000 px**.

**What the project does**: `scripts/ConvertImage.py` targets `TARGET_MAX_SIZE = 3.75 MB` (a file-size limit). The pixel-dimension rejection wall in `scripts/image_describer.py` is set at 10,000 px / 50 megapixels — significantly above both the API's hard limits and the optimal performance threshold.

**Impact**:
- Images between 1568–8000 px long edge are sent unresized. Claude will internally downscale them, increasing latency (time-to-first-token) with no quality benefit.
- Images between 8000–10,000 px will be API-rejected but the project's local validation lets them through.

**Recommendation**: Add pixel-dimension optimization targeting ≤1568 px long edge and ≤1.15 megapixels as the primary resize target, independent of file-size checks. Update the local rejection threshold from 10,000 px to 8,000 px to match the API's documented hard limit.

---

### 3. BMP and TIFF Sent With Wrong MIME Type — **High Priority**

**What the docs say**: Only JPEG, PNG, GIF, and WebP are supported image formats.

**What the project does**: `scripts/image_describer.py` includes `.bmp` and `.tiff` in `supported_formats`. The `media_type_map` in `imagedescriber/ai_providers.py` falls back to `image/jpeg` for unknown extensions, so BMP and TIFF files are submitted to the API with `media_type: image/jpeg` despite not being JPEG data.

**Impact**: The Claude API will return an error (likely 400 `invalid_request`) for any BMP or TIFF file. The error may not be clearly actionable from the user's perspective.

**Recommendation**: Either remove `.bmp` and `.tiff` from Claude's supported format list (they can be converted to JPEG first via the existing `ConvertImage.py` pipeline), or add explicit pre-conversion before sending to Claude.

---

### 4. Cost Tracking Broken for All Current Models — **Medium Priority**

**What the docs say**: Token costs are calculable; actual usage is returned in `message.usage`.

**What the project does**: `scripts/image_describer.py` uses partial string matching on keys like `"claude-sonnet-4"`, `"claude-opus-4"`, `"claude-3-5-haiku"` to look up per-token costs. The actual model IDs in use are versioned strings like `claude-sonnet-4-5-20250929` and `claude-haiku-4-5-20251001`.

**Impact**: Cost estimates never fire for any current model. The `idt stats` command shows $0 cost for all Claude runs.

**Recommendation**: Update the cost lookup to use the versioned model IDs from `models/claude_models.py`, or switch to prefix-based matching that accounts for the date suffix pattern (e.g., `startswith("claude-sonnet-4")`).

---

### 5. No System Prompt Used — **Medium Priority**

**What the docs say**: The cookbook example "Multiple images with a system prompt" demonstrates that system prompts improve consistency and accuracy. Role assignment is explicitly called out as a technique to reduce hallucinations — assigning Claude a role like "You are an expert image analyst with perfect attention to detail" improves counting and spatial reasoning tasks.

**What the project does**: All Claude calls send a single `user` turn with no `system` parameter. The entire instruction is embedded in the user message text.

**Impact**: Descriptions may be less consistent across a batch. For the accessibility prompt style in particular, a system prompt establishing Claude's role as an accessibility description expert could meaningfully improve output quality.

**Recommendation**: Add an optional `system` parameter to `ClaudeProvider.describe_image()` and wire it to a configurable `system_prompt` field in `image_describer_config.json`.

---

### 6. Files API Not Used for Repeated Batch Processing — **Medium Priority**

**What the docs say**: The **Files API** (currently in beta) allows uploading an image once and referencing it by `file_id` in multiple API calls, "when you want to avoid encoding overhead."

**What the project does**: Every call re-reads and re-base64-encodes the image file, even if the same image appears in multiple workflow runs or is re-described with a different prompt.

**Impact**: In "re-describe with different prompt/model" scenarios, the same image is encoded and transmitted multiple times. This adds unnecessary latency and bandwidth overhead.

**Recommendation**: Lower priority given the Files API is in beta, but worth tracking as a future enhancement — particularly for the workflow command path where the same image directory is frequently re-processed.

---

### 7. Double Retry Layers May Over-Retry on Rate Limits — **Low Priority**

**What the project does**: `imagedescriber/ai_providers.py` sets `anthropic.Anthropic(max_retries=3)` (SDK-level), AND the `@retry_on_api_error` decorator adds another 3 retries with exponential backoff. Both layers independently retry 429, 5xx, and timeout errors.

**Impact**: A rate limit error (429) could trigger up to ~9 total API attempts (3 SDK retries × 3 decorator retries). This can make rate limit situations worse by continuing to send requests while already throttled.

**Recommendation**: Set `max_retries=0` on the Anthropic client to disable SDK retries, relying solely on the custom decorator which provides better logging and jitter control. Or vice versa — standardize on one retry layer and remove the other.

---

### 8. Token Counting API Not Used for Pre-Flight Estimation — **Low Priority**

**What the docs say**: A dedicated **Token Counting API** (`POST /v1/messages/count_tokens`) is available in GA to count tokens before sending a request, enabling cost management and rate limit planning.

**What the project does**: Token usage is read after the fact from `message.usage`. No pre-flight token estimation is performed.

**Recommendation**: Worth documenting as a future enhancement, particularly for the `idt stats` cost projection feature.

---

### 9. Message Batches API Not Used — **Low Priority / Future Enhancement**

**What the docs say**: The **Message Batches API** processes large volumes of requests asynchronously at a **50% cost reduction** (`POST /v1/messages/batches`).

**What the project does**: All Claude calls are synchronous single-image requests, processed sequentially.

**Impact**: For large batch workflow runs (dozens to hundreds of images), the project pays full per-token pricing and processes sequentially. The Batches API would require an async response pattern (poll for results), which is a meaningful architectural change.

**Recommendation**: Evaluate as a phase-2 enhancement for the `workflow` command path. Cost savings would be significant for power users.

---

## Summary

| # | Issue | Priority | Estimated Effort |
|---|---|---|---|
| 1 | `max_tokens=1024` truncates descriptions | High | Low — make configurable |
| 2 | Resize targets file size, not pixel dimensions (1568px/1.15MP threshold missed) | High | Medium — update resize logic |
| 3 | BMP/TIFF sent with wrong MIME type, will fail at API | High | Low — remove or convert |
| 4 | Cost tracking broken for all current model IDs | Medium | Low — fix string matching |
| 5 | No system prompt — consistency and quality opportunity | Medium | Low — add optional system param |
| 6 | Files API not used for batch re-processing efficiency | Medium | High — beta feature, architectural change |
| 7 | Double retry layers may over-retry 429s | Low | Low — disable one layer |
| 8 | Token Counting API not used for pre-flight estimation | Low | Medium |
| 9 | Message Batches API not used (50% cost saving opportunity) | Low | High — architectural change |
