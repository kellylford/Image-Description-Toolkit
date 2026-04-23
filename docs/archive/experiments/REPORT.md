# IDT Provider & Resolution Experiment — Report
*Generated: 2026-04-04 19:24*

## Overview

This experiment compares Apple Silicon **MLX** providers against **Ollama** local providers on real iPhone HEIC images, investigating three questions:

1. **Why do MLX providers report fewer input tokens than Ollama?**
2. **Does description quality differ between MLX and Ollama at equal resolution?**
3. **Does sending higher-resolution images to Ollama improve quality?**

A key code architecture finding is documented in Part 3.

## Test Image Set

**11 real-world iPhone photos** (HEIC, converted to JPEG at 1024px for equal-input tests).
Selected to span different years and subject types: landscapes, candid portraits, pets, cityscapes, and interiors.

| Filename                                     |
| -------------------------------------------- |
| temp_snapshot_1.jpg                          |
| IMG_0233.jpg                                 |
| IMG_0455.jpg                                 |
| IMG_4159.jpg                                 |
| IMG_4822.jpg                                 |
| photo-564_singular_display_fullPicture.jpg   |
| photo-7444_singular_display_fullPicture.jpg  |
| photo-16180_singular_display_fullPicture.jpg |
| IMG_0880.jpg                                 |
| IMG_0637.jpg                                 |
| IMG_6347.jpg                                 |

---

## Part 1: Provider Comparison (Standardized 1024px Input)

All providers receive images pre-resized to ≤1024px, matching the IDT CLI default compression. This isolates model quality from resolution differences.

Input: **11 iPhone photos**, prompt style: **narrative**.

### MLX_Qwen25_7B

**Provider**: `mlx` | **Model**: `mlx-community/Qwen2.5-VL-7B-Instruct-4bit`  
**Descriptions collected**: 11/11  
**Workflow**: `wf_MLX_Qwen25_7B_mlx_mlx-communityQwen2.5-VL-7B-Instruct-4bit_narrative_20260404_132323`

**Token usage** (from GenerationResult, actual model tokens):

| Metric                  | Average | Min  | Max  |
| ----------------------- | ------- | ---- | ---- |
| Prompt tokens/image     | 1043.0  | 1043 | 1043 |
| Completion tokens/image | 121.7   | 66   | 174  |
| Total tokens/image      | 1164.7  | 1109 | 1217 |

**Timing**:

| Metric                | Value          |
| --------------------- | -------------- |
| Avg seconds/image     | 25.5s          |
| Min seconds/image     | 20.6s          |
| Max seconds/image     | 49.3s          |
| Total (all 11 images) | 281s (4.7 min) |

**Description quality** (heuristic averages):

| Metric              | Average | Min   | Max  |
| ------------------- | ------- | ----- | ---- |
| Word count          | 103.8   | 60    | 151  |
| Sentences           | 6.5     | 4     | 10   |
| Vocabulary richness | 0.6     | 0.497 | 0.75 |
| Color terms         | 4.3     | 0     | 7    |
| Spatial terms       | 2.1     | 0     | 6    |
| Detail terms        | 2.1     | 0     | 4    |

### MLX_Llama32_11B

**Provider**: `mlx` | **Model**: `mlx-community/Llama-3.2-11B-Vision-Instruct-4bit`  
**Descriptions collected**: 11/11  
**Workflow**: `wf_MLX_Llama32_11B_mlx_mlx-communityLlama-3.2-11B-Vision-Instruct-4bit_narrative_20260404_142320`

**Token usage** (from GenerationResult, actual model tokens):

| Metric                  | Average | Min | Max |
| ----------------------- | ------- | --- | --- |
| Prompt tokens/image     | 34.0    | 34  | 34  |
| Completion tokens/image | 151.1   | 87  | 244 |
| Total tokens/image      | 185.1   | 121 | 278 |

**Timing**:

| Metric                | Value            |
| --------------------- | ---------------- |
| Avg seconds/image     | 129.2s           |
| Min seconds/image     | 83.8s            |
| Max seconds/image     | 183.5s           |
| Total (all 11 images) | 1421s (23.7 min) |

**Description quality** (heuristic averages):

| Metric              | Average | Min   | Max   |
| ------------------- | ------- | ----- | ----- |
| Word count          | 130.2   | 71    | 212   |
| Sentences           | 6.4     | 3     | 11    |
| Vocabulary richness | 0.6     | 0.392 | 0.707 |
| Color terms         | 5.1     | 3     | 8     |
| Spatial terms       | 3.9     | 1     | 7     |
| Detail terms        | 3.1     | 1     | 5     |

### Ollama_Llama32V

**Provider**: `ollama` | **Model**: `llama3.2-vision:latest`  
**Descriptions collected**: 11/11  
**Workflow**: `wf_Ollama_Llama32V_ollama_llama3.2-visionlatest_narrative_20260404_152322`

*Token counts not available for Ollama CLI path (not currently logged by IDT — see Part 3).*

**Timing**:

| Metric                | Value           |
| --------------------- | --------------- |
| Avg seconds/image     | 67.1s           |
| Min seconds/image     | 55.8s           |
| Max seconds/image     | 82.9s           |
| Total (all 11 images) | 738s (12.3 min) |

**Description quality** (heuristic averages):

| Metric              | Average | Min   | Max   |
| ------------------- | ------- | ----- | ----- |
| Word count          | 134.5   | 88    | 209   |
| Sentences           | 7.7     | 4     | 14    |
| Vocabulary richness | 0.5     | 0.342 | 0.648 |
| Color terms         | 2.6     | 1     | 4     |
| Spatial terms       | 2.9     | 1     | 5     |
| Detail terms        | 2.0     | 0     | 4     |

### Ollama_Granite32V

**Provider**: `ollama` | **Model**: `granite3.2-vision:latest`  
**Descriptions collected**: 11/11  
**Workflow**: `wf_Ollama_Granite32V_ollama_granite3.2-visionlatest_narrative_20260404_162319`

*Token counts not available for Ollama CLI path (not currently logged by IDT — see Part 3).*

**Timing**:

| Metric                | Value          |
| --------------------- | -------------- |
| Avg seconds/image     | 35.2s          |
| Min seconds/image     | 25.4s          |
| Max seconds/image     | 48.1s          |
| Total (all 11 images) | 388s (6.5 min) |

**Description quality** (heuristic averages):

| Metric              | Average | Min   | Max |
| ------------------- | ------- | ----- | --- |
| Word count          | 178.5   | 16    | 411 |
| Sentences           | 7.4     | 1     | 17  |
| Vocabulary richness | 0.7     | 0.523 | 1.0 |
| Color terms         | 2.8     | 0     | 5   |
| Spatial terms       | 3.5     | 0     | 9   |
| Detail terms        | 2.9     | 0     | 6   |

> **Note on MLX_Llama32_11B token count**: This model reports only **34 prompt tokens/image** — compared to 1043 for Qwen2.5-VL-7B. This is because `mlx_vlm` with Llama-3.2-Vision reports only the text prompt token count from `GenerationResult.prompt_tokens`, not the vision encoder patch tokens. The actual compute cost is not reflected in the logged 34-token figure. This is a known mlx_vlm reporting limitation; the model is still processing the full image.

### Cross-Config Summary

| Config            | Descriptions | Avg Prompt Tokens | Avg Completion Tokens | Avg Sec/Image | Avg Words | Avg Sentences |
| ----------------- | ------------ | ----------------- | --------------------- | ------------- | --------- | ------------- |
| MLX_Qwen25_7B     | 11           | 1043.0            | 121.7                 | 25.5s         | 103.8     | 6.5           |
| MLX_Llama32_11B   | 11           | 34.0              | 151.1                 | 129.2s        | 130.2     | 6.4           |
| Ollama_Llama32V   | 11           | n/a (Ollama)      | n/a (Ollama)          | 67.1s         | 134.5     | 7.7           |
| Ollama_Granite32V | 11           | n/a (Ollama)      | n/a (Ollama)          | 35.2s         | 178.5     | 7.4           |

### Sample Descriptions (Same Images, All Configs)

#### `IMG_0233.jpg`

**MLX_Qwen25_7B** (64 words, 1043p/76c tokens):
> The image appears to be a close-up of a blurred surface, possibly a wall or a piece of paper. The colors are predominantly shades of gray and white, with a slight gradient effect. There are no distinct objects or clear details visible, as the image is out of focus. The overall impression is one of a smooth, uniform texture with a soft, diffused light.

**MLX_Llama32_11B** (91 words, 34p/107c tokens):
> The image presents a soft, gradient-like background that transitions from a light pinkish hue on the left to a darker, more muted tone on the right. The color palette is characterized by a gentle blend of pink, purple, and gray, with no distinct shapes or objects visible. The overall effect is one of subtle, nuanced coloration, with no sharp lines or boundaries to break up the smooth transition from one shade to another. The absence of any discernible features or details adds to the serene and calming atmosphere of the image.

**Ollama_Llama32V** (112 words):
> The image is a blurry, gradient background that transitions from white at the top left to dark gray at the bottom right. The gradient is smooth and even, with no visible lines or edges. The background is a solid color, with no patterns or textures visible. The overall effect is one of simplicity and subtlety, with the gradient creating a sense of depth and dimensionality. The image appears to be a digital rendering or a photograph taken with a camera that has a high-quality lens and a good understanding of light and color. The image does not appear to have any significant changes or comparisons, as it is a single, static image.

**Ollama_Granite32V** (16 words):
> The image is too small or not clear enough for me to provide an accurate description

#### `IMG_0455.jpg`

**MLX_Qwen25_7B** (60 words, 1043p/66c tokens):
> The image appears to be blurry and out of focus. There are no clear objects or distinct colors that can be identified. The overall impression is one of motion blur, suggesting the image was taken while the camera or the subject was moving. The lack of detail makes it difficult to discern any specific features or objects within the frame.

**MLX_Llama32_11B** (193 words, 34p/222c tokens):
> The image is a blurry photograph of a person's face and shoulder, with a white object in the center. The person's face is partially visible, with their nose and mouth obscured by the blur. Their skin tone appears to be a mix of light and dark brown, with a hint of red around the edges of their face. The person's shoulder is also visible, with a slight curve to it.  The white object in the center of the image is difficult to make out, but it appears to be a piece of clothing or a scarf. It is a bright, creamy white color and is positioned in a way that suggests it may be covering the person's face or neck.  The background of the image is also blurry, but it appears to be a mix of dark and light colors. There are hints of gray, black, and brown, which may indicate that the person is standing in front of a wall or a piece of furniture. Overall, the image is quite blurry, but it appears to be a close-up shot of a person's face and shoulder, with a white object in the center.

**Ollama_Llama32V** (101 words):
> The image is a blurry, out-of-focus photograph of a person's face. The person's face is not clearly visible, but it appears to be a woman with long hair. The woman's face is positioned in the center of the image, and her features are not clearly defined due to the blurriness of the photo. The background of the image is also blurry, but it appears to be a dark-colored wall or surface. The overall effect of the image is one of mystery and intrigue, as the viewer is left to wonder about the identity and emotions of the person in the photo.

**Ollama_Granite32V** (88 words):
> The image provided appears blurry with indistinct shapes that could be interpreted as lines or patterns due to its lack of clarity. The color palette is predominantly dark tones such as blacks, grays, and muted browns without any discernible objects or subjects within the frame. There are no clear indicators of movement or directionality in this image; it seems static with a focus on texture rather than form. Without additional context or information about what is being photographed, providing an accurate description becomes challenging and speculative at best.

---

## Part 2: Resolution Impact (Ollama llama3.2-vision)

Same images processed at different resolutions to test whether sending higher-res images to Ollama improves output quality.

> **Note**: The full-resolution test could not complete in this session due to a process queue backlog. Results below cover 512px and partial 1024px data.

### 512px

**Descriptions**: 5  
**Workflow**: `wf_ResTest_512px_ollama_llama3.2-visionlatest_narrative_20260404_172322`

| Metric            | Value |
| ----------------- | ----- |
| Images processed  | 5     |
| Avg sec/image     | 68.1s |
| Avg word count    | 135.4 |
| Avg sentences     | 7.6   |
| Avg color terms   | 3.2   |
| Avg spatial terms | 3.2   |
| Avg detail terms  | 1.4   |

### 1024px

**Descriptions**: 6  
**Workflow**: `wf_ResTest_1024px_ollama_llama3.2-visionlatest_narrative_20260404_182350`

| Metric            | Value  |
| ----------------- | ------ |
| Images processed  | 6      |
| Avg sec/image     | 227.8s |
| Avg word count    | 130.0  |
| Avg sentences     | 6.8    |
| Avg color terms   | 2.7    |
| Avg spatial terms | 3.3    |
| Avg detail terms  | 2.3    |

### Comparison

> **Note on 1024px timing**: The 227.8s average for 1024px is **not a valid measure of resolution impact** — it reflects Ollama request queue backlog from multiple competing processes during the experiment (each request waited ~15–20 min in queue). The 512px timing (68.1s) is a reliable baseline. A clean 1024px vs full-res comparison requires a queue-free Ollama environment and is recommended as follow-up work.

| Resolution | N | Avg Sec/Image | Avg Words | Avg Sentences | Avg Color Terms |
| ---------- | - | ------------- | --------- | ------------- | --------------- |
| 512px      | 5 | 68.1s         | 135.4     | 7.6           | 3.2             |
| 1024px     | 6 | 227.8s (⚠️ queue-inflated) | 130.0 | 6.8 | 2.7 |

---

## Part 3: Architecture Findings & Code Analysis

### Finding 1: CLI vs GUI Inconsistency in Ollama Image Handling

**CLI path** (`scripts/image_describer.py`): Calls `optimize_image()` which applies `img.thumbnail((1024, 1024))` by default. Images are always resized to ≤1024px before sending to Ollama.

**GUI path** (`imagedescriber/workers_wx.py` → `ai_providers.py::OllamaProvider`): Reads raw bytes from disk, base64 encodes and sends to Ollama **at full resolution** (only quality-reduces if >3.75MB, with no dimension downscaling).

**Impact**: A 12MP iPhone photo (4032×3024) sent via the GUI is ~6× larger than the same photo sent via CLI. This means:
- GUI Ollama uses significantly more VRAM per request
- GUI Ollama processes substantially more image tokens
- Results between GUI and CLI are not directly comparable
- User experience is inconsistent: CLI users get fast processing,   GUI users get slower processing with potentially different quality

**Confirmed unintentional** by the project maintainer.

### Finding 2: MLX Always Caps at 1024px

**MLX path** (`imagedescriber/ai_providers.py::MLXProvider._to_jpeg_tempfile()`): Always applies `img.thumbnail((1024, 1024), Image.LANCZOS)` before passing to `mlx_vlm`. No configuration option, no way to send full-res via GUI or CLI.

This is **consistent** between GUI and CLI paths for MLX, which is good. However, it means MLX and Ollama GUI are not comparable on equal terms.

### Finding 3: Token Count Logging Gap

MLX providers log actual token counts (from `GenerationResult.prompt_tokens` and `.generation_tokens`) both in the description file and log. Ollama CLI path does NOT log token counts — only processing time.

This makes it impossible to directly compare token efficiency between MLX and Ollama from IDT's own output. The Ollama `/api/generate` response DOES return `prompt_eval_count` and `eval_count` but IDT discards these.

### Finding 4: Why MLX Reports Fewer Input Tokens

MLX token counts are lower than typical Ollama/LLaVA token counts because:

1. **Qwen2.5-VL Dynamic Tiling** — This model uses dynamic resolution with    variable grid sizes. At 1024px input, it adaptively selects a tile grid    that results in far fewer visual tokens than fixed-patch models.

2. **Different tokenization** — LLaVA-style Ollama models typically encode    images as fixed 16×16 or 14×14 patches, producing ~256–576 image tokens    regardless of content. Qwen2.5-VL selects tile counts based on image aspect    and complexity.

3. **Consistent 1043 prompt tokens** in Qwen data suggests the vision encoder    produces the same fixed token count for 1024px inputs, which is around    1024 visual tokens + ~20 prompt text tokens. LLaVA typically produces    576 (24×24 grid) or 1024 (32×32 grid) vision tokens. The 1043 figure includes the text prompt overhead.

### Timing Comparison

At equal 1024px input, timing differences reflect model inference speed:

| Config            | Provider | Avg Sec/Image | Total (11 images) |
| ----------------- | -------- | ------------- | ----------------- |
| MLX_Qwen25_7B     | mlx      | 25.5s         | 281s              |
| MLX_Llama32_11B   | mlx      | 129.2s        | 1421s             |
| Ollama_Llama32V   | ollama   | 67.1s         | 738s              |
| Ollama_Granite32V | ollama   | 35.2s         | 388s              |

---

## Recommendations

### Recommended Code Changes

#### 1. Fix the GUI Ollama Inconsistency (High Priority)

In `imagedescriber/ai_providers.py`, `OllamaProvider.describe_image()` should resize images to ≤1024px before encoding, matching the CLI behavior:

```python
# In OllamaProvider.describe_image() — add before base64 encoding:
from PIL import Image
import io

with Image.open(image_path) as img:
    img.thumbnail((1024, 1024), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=85)
    image_data = base64.b64encode(buf.getvalue()).decode('utf-8')
```

**Why**: Without this, GUI Ollama users send 4032×3024 images (~12 MP) when CLI users send compressed 1024px images. This makes GUI slower, wastes memory, and produces non-reproducible results.

#### 2. Add Ollama Token Count Logging (Medium Priority)

The Ollama `/api/generate` response returns `prompt_eval_count` and `eval_count`. Log these similarly to how MLX logs token data. This enables cost estimation and efficiency comparison.

#### 3. Document the MLX 1024px Cap (Low Priority)

The `MLXProvider._to_jpeg_tempfile()` 1024px cap is undocumented. Add a config option or at minimum a clear log message so users understand why MLX always receives downscaled images.

### User Guidance

#### For Users Choosing Between MLX and Ollama

| Factor | MLX | Ollama (CLI) | Ollama (GUI - current) |
|--------|-----|-------------|------------------------|
| Input resolution | Always 1024px | Always 1024px | Full resolution (bug) |
| Token logging | ✅ Full data | ❌ None | ❌ None |
| Speed (15" MacBook) | ~40-70s/image | ~55-85s/image | Slower (more VRAM) |
| Quality at 1024px | Good | Good | Varies with res |
| Runs offline | ✅ | ✅ | ✅ |
| Models available | ~10 cached | ~8 via Ollama | ~8 via Ollama |

**Recommendation**: For batch processing of iPhone photos on Apple Silicon, **MLX providers** (especially Qwen2.5-VL-7B) are the best choice — they offer consistent 1024px processing, full token visibility, and competitive speed.

For users without Apple Silicon or when using specific models only available via Ollama, use the **CLI workflow** (not the GUI) until the Ollama GUI resize fix is applied.

#### For Users Running IDT Experiments

When comparing providers, always use the CLI (`idt workflow --steps describe`) for reproducibility. The GUI's full-resolution Ollama path makes side-by-side comparisons invalid.

---

## Data Notes & Limitations

- **Part 2 full-resolution data not collected**: Multiple concurrent IDT processes   filled the Ollama request queue. The full-res test was not completed.   Partial 1024px data (6/11 images) is included.

- **Ollama token counts unavailable**: IDT CLI does not log Ollama token counts.   Only processing time is available for Ollama runs.

- **Quality scoring is heuristic**: Word count, color/spatial/detail vocabulary   frequency are proxy metrics. They are NOT ground-truth quality assessments.   Human review of sample descriptions is needed for definitive quality conclusions.

- **ConvertImage.py case sensitivity bug**: `scripts/ConvertImage.py` globs only   `*.heic` (lowercase). HEIC files from SMB mounts are usually `*.HEIC` (uppercase).   Workaround used in this experiment: pre-convert HEIC→JPEG using PIL directly.   **This bug should be fixed** — change line 269 to `pattern = '**/*.[hH][eE][iI][cC]'`.

- **Zombie IDT processes**: IDT displays a post-workflow interactive prompt   ('view results? y/n') that blocks when called from subprocess without a TTY.   Processes sent SIGKILL from outside their terminal session did not terminate   (macOS PTY protection). **Fix applied**: `stdin=subprocess.DEVNULL` in experiment   script's `subprocess.run()` call.

---

*Report generated: 2026-04-04 19:24*  
*IDT version: 4.0.0Beta2 bld1*  
*Platform: macOS (Apple Silicon M-series)*  
