# Apple On-Device AI — Research & Roadmap

**Last updated:** 2026-03-01  
**Status:** MLX (Apple Metal) provider complete in `metal` branch — awaiting merge to `MacApp`

---

## Executive Summary

"Apple Intelligence" is **text-only** and **Swift-only** — it cannot describe images and has no Python API. However, Apple Silicon Macs already have a fully working path for **on-device image descriptions** via **MLX** (Apple's open-source ML framework) and vision models from Hugging Face. This capability is **fully implemented** in the `metal` branch and just needs to be merged.

---

## What Apple Intelligence Actually Offers

### Foundation Models Framework (macOS 26+)

Apple's official on-device LLM developer API, announced at WWDC 2025.

| Property | Detail |
|---|---|
| Minimum OS | macOS 26.0 (Tahoe) — NOT macOS 15 |
| Hardware | Apple Silicon only (M1+). Intel Macs: not supported |
| Language | **Swift only** — no Python bindings, no CLI, no REST API |
| Context window | 4,096 tokens |
| Image input | ❌ None. Text-in, text-out only |

**Key Swift types:** `SystemLanguageModel`, `LanguageModelSession`, `Instructions`, `@Generable` macro, `Tool` protocol

**What it can do:**
- Summarization, entity extraction, text understanding
- Text refinement/rewriting, classification, creative writing  
- Guided generation (structured output via Swift macros)
- Tool calling (model can invoke Swift code you write)
- Custom LoRA adapter fine-tuning (offline Python/PyTorch, deployed as `.fmadapter`)

**What it CANNOT do:**
- Accept image input (no multimodal API exposed)
- Be called from Python at inference time
- Run without Apple Intelligence + macOS 26

**Apple's image features that are system-internal only (no public API):**
- Photos natural language search
- Visual Intelligence (camera/screen context)
- Image Playground / Genmoji generation
- Photos Clean Up (inpainting)

### WritingTools API (macOS 15.2+)

`NSWritingToolsCoordinator` allows custom text views to integrate with Writing Tools UI (summarize, rewrite, proofread). Text-in, text-out only. Not useful for image description.

### Vision Framework (macOS 15+)

Separate from Apple Intelligence — classic CV framework, not an LLM.

**Can do:**
- OCR / text recognition (26 languages) via `RecognizeTextRequest`
- Face detection, object classification (predefined categories)
- Barcode/QR detection, subject segmentation, pose estimation

**Cannot do:**
- Free-form scene description (only structured typed observations)
- Python calls (Swift/ObjC only)

**Potential supplementary use:** A Swift CLI bridge could extract text visible in an image via OCR and prepend it to the prompt sent to a vision model — useful for screenshots, signs, documents.

---

## What We Actually Have: MLX Provider (Complete)

### Status: Done in `metal` Branch

The `metal` branch contains a **production-ready MLX provider** using Apple's [MLX framework](https://github.com/ml-explore/mlx) with vision models served locally via `mlx-vlm`. This IS on-device image description on Apple Silicon — Apple's own ML compute stack, just with open-source vision models instead of Apple Intelligence's closed model.

### What's Implemented

**`imagedescriber/ai_providers.py` — `MLXProvider` class (line 1532)**
- Subclasses `AIProvider`, implements all abstract methods
- Detects Apple Silicon via `platform.system() == "Darwin"` + `HAS_MLX_VLM` flag
- Keeps model weights hot in Metal unified memory between calls via `_ensure_model_loaded()`
- Converts every input to a temp JPEG capped at 1024px before inference (mlx-vlm requirement)
- Tracks `prompt_tokens`, `completion_tokens`, `elapsed_s`, `tokens_per_s` for stats
- Graceful import fallback pattern — safe in PyInstaller frozen mode

**7 supported models (all `mlx-community` Hugging Face repos):**

| Model ID | Size | Notes |
|---|---|---|
| `mlx-community/Qwen2-VL-2B-Instruct-4bit` | ~1.5 GB | Fastest Qwen, good quality |
| `mlx-community/Qwen2.5-VL-3B-Instruct-4bit` | ~2.0 GB | |
| `mlx-community/Qwen2.5-VL-7B-Instruct-4bit` | ~4.5 GB | Best Qwen quality |
| `mlx-community/gemma-3-4b-it-qat-4bit` | ~2.5 GB | QAT quantization, strong English |
| `mlx-community/phi-3.5-vision-instruct-4bit` | ~2.5 GB | Good at text/detail in images |
| `mlx-community/SmolVLM-Instruct-4bit` | ~0.5 GB | Fastest, shorter descriptions |
| `mlx-community/Llama-3.2-11B-Vision-Instruct-4bit` | ~6.5 GB | Slow on 16 GB RAM (~1-2 tok/s) |

**Supporting files updated in `metal` branch:**

| File | Change |
|---|---|
| `scripts/image_describer.py` | `MLXProvider` import added; `elif self.provider_name == "mlx":` branch in `_initialize_provider()`; `"mlx"` added to CLI `--provider` choices |
| `models/provider_configs.py` | `"MLX"` entry in `PROVIDER_CAPABILITIES` — no API key, not cloud, all prompt styles, case-insensitive lookup |
| `idt/idt.spec` | Conditional `collect_all('mlx_vlm')` + `collect_all('mlx')` + full `hiddenimports` for all 7 model architectures |
| `imagedescriber/imagedescriber_wx.spec` | Same as above — both executables support MLX |
| `imagedescriber/requirements.txt` | `mlx-vlm` added |

### How to Merge

```bash
git checkout MacApp
git merge metal
# Resolve any conflicts (likely in ai_providers.py if MacApp has parallel changes)
# Then rebuild:
cd idt && ./build_idt.sh
cd ../imagedescriber && ./build_imagedescriber_wx.sh
```

### Testing After Merge

```bash
# Install mlx-vlm if not present
pip install mlx-vlm

# CLI smoke test
./dist/idt describe --provider mlx \
  --model mlx-community/Qwen2-VL-2B-Instruct-4bit \
  testimages/

# Verify output
ls Descriptions/wf_*/image_descriptions.txt

# GUI test
# Launch ImageDescriber.app → MLX should appear in provider dropdown
# No API key field should appear
# All prompt styles should be available
```

---

## Future Possibilities

### 1. Foundation Models Text Refinement Bridge (macOS 26+ only)

**Concept:** After a vision model generates a description, pipe the text through Apple Intelligence for local refinement (grammar, tone, accessibility language) at zero API cost.

**Implementation sketch:**
1. Write a small Swift CLI tool in `tools/apple_refine/` that:
   - Accepts text on stdin
   - Creates a `LanguageModelSession` with a refinement instruction
   - Streams output to stdout
2. Add `--apple-refine` flag to `idt describe` and `image_describer.py`
3. Gate behind `sw_vers -productVersion` ≥ 26.0 check
4. Call via `subprocess.run(["tools/apple_refine/refine"], input=description, capture_output=True)`

**Limitations:**
- Requires macOS 26 on the target machine
- 4,096 token context limits use to descriptions under ~3,000 words
- Swift toolchain required at build time
- Cannot run in PyInstaller frozen exe without bundling the Swift binary separately

### 2. Vision Framework OCR Pre-processing (requires Swift bridge)

**Concept:** Before sending an image to a vision model, extract any text present in the image via Apple's `RecognizeTextRequest` (26 languages, no internet needed) and prepend it to the prompt:

```
"This image contains the following visible text: [OCR results]

Describe this image..."
```

This improves descriptions of screenshots, documents, signs, whiteboards, menus, and other text-heavy images — the vision model knows what text is present and doesn't have to guess.

**Implementation sketch:**
1. Write a Swift CLI tool `tools/apple_ocr/extract_text` that accepts an image path and returns JSON `{"text": "...", "confidence": 0.95}`
2. Add a `--ocr-preprocess` flag, enabled by default on macOS with the tool available
3. Prepend OCR text to prompt in `image_describer.py` before calling provider

**Limitations:** Swift CLI bridge required; macOS-only; adds latency per image

### 3. `.fmadapter` Fine-Tuning for Accessibility Language (speculative)

Apple's Foundation Models framework supports loading custom LoRA adapters trained with their Python/PyTorch toolkit. A fine-tuned adapter that specializes in accessibility-focused image descriptions (alt text style, WCAG patterns) could be trained and distributed as part of IDT.

**Blockers:** Requires macOS 26, Swift integration, training data curation, adapter packaging. Very speculative — not recommended for near-term roadmap.

---

## Summary Decision Table

| Capability | Available Now? | What's Needed |
|---|---|---|
| On-device image descriptions (MLX) | ✅ Done in `metal` branch | Merge `metal` → `MacApp` |
| Apple Intelligence text refinement | ⏳ Future | Swift bridge, macOS 26+ |
| OCR text pre-processing | ⏳ Future | Swift bridge, any macOS |
| Apple Intelligence image description | ❌ Not possible | No public API exists |
| Python access to Foundation Models LLM | ❌ Not possible | Swift-only, no Python |

**Recommended immediate action:** Merge `metal` into `MacApp`. Everything else is future work.
