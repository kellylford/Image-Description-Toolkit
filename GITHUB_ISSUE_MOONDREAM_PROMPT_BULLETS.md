# Moondream Failing with Prompts Containing Bulleted Lists

## Summary
Moondream model consistently fails to generate descriptions when using prompts that contain bullet-point formatting with dashes and newlines, while working perfectly with single-paragraph prompts.

## Environment
- **Date**: October 24, 2025
- **Model**: `moondream:latest` via Ollama
- **Tested on**: Multiple machines (consistent failure)
- **IDT Version**: Current main branch

## Problem Description

### Working Prompts ✅
**Narrative Prompt** (single paragraph):
```
"Provide a narrative description including objects, colors and detail. Avoid interpretation, just describe."
```
- **Result**: 25/25 successful descriptions

**Colorful Prompt** (single paragraph):
```
"Give me a rich, vivid description emphasizing colors, lighting, and visual atmosphere. Focus on the palette, color relationships, and how colors contribute to the mood and composition."
```
- **Result**: 25/25 successful descriptions (263 lines of output)

### Failing Prompts ❌
**Technical Prompt** (bulleted):
```
"Provide a technical analysis of this image:
- Camera settings and photographic technique
- Lighting conditions and quality
- Composition and framing
- Image quality and clarity
- Technical strengths or weaknesses"
```
- **Result**: 0/25 successful descriptions (10 lines of output)

**Detailed Prompt** (bulleted):
```
"Describe this image in detail, including:
- Main subjects/objects
- Setting/environment
- Key colors and lighting
- Notable activities or composition
Keep it comprehensive and informative for metadata."
```
- **Result**: Expected to fail similarly (untested due to consistent technical failures)

## Technical Evidence

### Log Analysis
From `image_describer_20251024_053953.log`:
```
INFO - Generated description for photo-20825_singular_display_fullPicture.jpg (Provider: ollama, Model: moondream) - (2025-10-24 05:40:05,969)
ERROR - Failed to generate description for: photo-20825_singular_display_fullPicture.jpg - No description generated - (2025-10-24 05:40:05,998)
```

**Pattern observed:**
1. Moondream processes images normally (9-12 seconds per image)
2. Log shows "Generated description" message
3. But actual description content is empty
4. Results in "No description generated" error

### Failure Rate
- **Technical prompt**: 0/25 images successful
- **Multiple machines**: Consistent failure across different environments
- **Same model**: Works perfectly with single-paragraph prompts

## Root Cause Analysis
Moondream appears to have issues processing prompts containing:
- Newline characters (`\n`)
- Bullet points with dashes (`- item`)
- Multi-line structured formatting

## Impact
- Blocks completion of comprehensive model testing matrix
- Currently at 38/40 configurations (missing 2 moondream prompts)
- Affects technical and detailed prompt analysis workflows

## Potential Solutions

### Option 1: Rewrite Prompts (Non-Bulleted)
```json
"technical": "Provide a technical analysis of this image covering camera settings, photographic technique, lighting conditions, composition, framing, image quality, and any technical strengths or weaknesses."

"detailed": "Describe this image in detail covering the main subjects and objects, setting and environment, key colors and lighting, and notable activities or composition. Keep it comprehensive and informative for metadata."
```

### Option 2: Model-Specific Prompt Handling
Implement conditional prompt formatting based on model capabilities.

### Option 3: Alternative Models
Use different models for structured prompts that require bullet-point formatting.

## Data Location
Failed workflow: `wf_25imagetest_ollama_moondream_technical_20251024_053914`
Successful comparison: `wf_25imagetest_ollama_moondream_latest_colorful_20251023_184952`

## Configuration Files
- Main config: `scripts/image_describer_config.json`
- Web gallery: `tools/ImageGallery/index.html` (PROMPT_TEXTS)

## Priority
Medium - Affects model testing completeness but workarounds available.

## Labels
- bug
- ollama
- model-compatibility
- prompts