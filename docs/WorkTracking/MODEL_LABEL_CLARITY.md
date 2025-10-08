# Model Label Clarity - Implementation Summary

**Created:** October 6, 2025  
**Issue:** With 27 AI models being tested, generic labels like "Claude Haiku" and "Ollama LLaVA" are ambiguous and make quality comparison impossible.

## Problem

When running multiple similar models (e.g., LLaVA 7B, 13B, 34B, or Claude Haiku 3 vs 3.5), the analysis tools showed ambiguous labels:

**Before Fix:**
```
Image Name@Claude Haiku@Claude Haiku@Claude Haiku@Ollama LLaVA@Ollama LLaVA@Ollama LLaVA@...
```

Users couldn't tell which "Claude Haiku" was version 3 or 3.5, or which "Ollama LLaVA" was 7B, 13B, or 34B.

## Solution

Created a comprehensive `get_workflow_label()` function that extracts version/size information from workflow directory names and converts them to **unique, human-readable labels**.

### Label Mapping

| Raw Workflow Directory | Improved Label |
|------------------------|----------------|
| `wf_claude_claude-3-haiku-20240307_...` | **Claude Haiku 3** |
| `wf_claude_claude-3-5-haiku-20241022_...` | **Claude Haiku 3.5** |
| `wf_claude_claude-sonnet-3-7-20250219_...` | **Claude Sonnet 3.7** |
| `wf_claude_claude-sonnet-4-20250514_...` | **Claude Sonnet 4** |
| `wf_claude_claude-sonnet-4-5-20250929_...` | **Claude Sonnet 4.5** |
| `wf_claude_claude-opus-4-20250514_...` | **Claude Opus 4** |
| `wf_claude_claude-opus-4-1-20250805_...` | **Claude Opus 4.1** |
| `wf_ollama_llava_7b_...` | **Ollama LLaVA 7B** |
| `wf_ollama_llava_13b_...` | **Ollama LLaVA 13B** |
| `wf_ollama_llava_34b_...` | **Ollama LLaVA 34B** |
| `wf_ollama_llava_latest_...` | **Ollama LLaVA** |
| `wf_ollama_llava-phi3_latest_...` | **Ollama LLaVA-Phi3** |
| `wf_ollama_llava-llama3_latest_...` | **Ollama LLaVA-Llama3** |
| `wf_ollama_llama3.2-vision_11b_...` | **Ollama Llama3.2-Vision 11B** |
| `wf_ollama_llama3.2-vision_90b_...` | **Ollama Llama3.2-Vision 90B** |
| `wf_ollama_llama3.2-vision_latest_...` | **Ollama Llama3.2-Vision** |
| `wf_ollama_moondream_latest_...` | **Ollama Moondream** |
| `wf_ollama_bakllava_latest_...` | **Ollama BakLLaVA** |
| `wf_ollama_minicpm-v_8b_...` | **Ollama MiniCPM-V 8B** |
| `wf_ollama_minicpm-v_latest_...` | **Ollama MiniCPM-V** |
| `wf_ollama_cogvlm2_latest_...` | **Ollama CogVLM2** |
| `wf_ollama_internvl_latest_...` | **Ollama InternVL** |
| `wf_ollama_gemma3_latest_...` | **Ollama Gemma3** |
| `wf_ollama_mistral-small3.1_latest_...` | **Ollama Mistral-Small 3.1** |
| `wf_openai_gpt-4o_...` | **OpenAI GPT-4o** |
| `wf_openai_gpt-4o-mini_...` | **OpenAI GPT-4o-mini** |
| `wf_openai_gpt-5_...` | **OpenAI GPT-5** |

## Files Updated

### 1. `LocalDoNotSubmit/combine_workflow_descriptions.py`
**Purpose:** Combines descriptions from multiple workflows into a CSV for quality comparison

**Impact:** CSV header now shows clear labels:
```
Image Name@Claude Haiku 3.5@Claude Sonnet 3.7@Ollama LLaVA 7B@Ollama LLaVA 13B@OpenAI GPT-4o@...
```

**Lines Changed:** 88-220 (replaced `get_workflow_label` function)

### 2. `LocalDoNotSubmit/analyze_workflow_stats.py`
**Purpose:** Analyzes timing/performance statistics across workflow runs

**Impact:** 
- Console output shows clear labels when printing statistics
- CSV export has distinguishable "Workflow" column values
- Users can identify which model performed better/worse

**Lines Changed:** 145-280 (replaced `get_workflow_label` function)

### 3. `imagedescriber/imagedescriber.py` ✨ NEW
**Purpose:** Main ImageDescriber GUI application

**Impact:**
- Description list now shows **middle-ground format**: `LLaVA 7B narrative: Description...` instead of `llava:7b narrative: Description...`
- Chat interface uses same friendly names
- Consistent labeling across entire GUI

**Changes Made:**
- Added module-level `get_short_model_name()` utility function (lines 323-423)
- Updated `load_descriptions_for_image()` to use friendly model names (line 6910)
- Updated all chat-related displays to use shared function
- Removed duplicate `get_short_model_name()` method from `ChatDialog` class

**Examples of GUI Display:**
```
Before: llava:7b narrative: The image depicts...
After:  LLaVA 7B narrative: The image depicts...

Before: claude-3-5-haiku-20241022 narrative: This photograph shows...
After:  Claude Haiku 3.5 narrative: This photograph shows...

Before: gpt-4o-mini narrative: A stadium filled with...
After:  GPT-4o-mini narrative: A stadium filled with...
```

## Where Users See Model Names

| Location | Status | What Users See |
|----------|--------|----------------|
| **Workflow directory names** | Unchanged | `wf_ollama_llava_7b_narrative_20251006_175147` (machine-readable, OK) |
| **Workflow log files** | Unchanged | `Using override model for resume: llava:7b` (technical names, OK for logs) |
| **combineddescriptions.txt CSV** | ✅ **FIXED** | `Claude Haiku 3.5`, `Ollama LLaVA 7B` (human-readable) |
| **analyze_workflow_stats.py output** | ✅ **FIXED** | `Claude Haiku 3.5`, `Ollama LLaVA 7B` (human-readable) |
| **ImageDescriber GUI - Description List** | ✅ **FIXED** | `LLaVA 7B narrative: ...`, `Claude Haiku 3.5 narrative: ...` (middle-ground format) |
| **ImageDescriber GUI - Chat Interface** | ✅ **FIXED** | Same friendly names as description list (consistent) |

## Testing

### Test Case 1: Combined Descriptions CSV
```bash
cd LocalDoNotSubmit
python combine_workflow_descriptions.py
head -1 combineddescriptions.txt
```

**Expected:** CSV header with unique labels like:
```
Image Name@Claude Haiku 3.5@Claude Sonnet 3.7@Ollama LLaVA 7B@Ollama LLaVA 13B@...
```

### Test Case 2: Workflow Statistics Analysis
```bash
cd LocalDoNotSubmit
python analyze_workflow_stats.py
```

**Expected:** Console output showing clear model names:
```
Ollama LLaVA 7B
--------------------------------------------------------------------------------
  Start Time:              2025-10-06 17:51:47
  Total Duration:          2m 32s
  Average Time/Image:      5.23s

Claude Haiku 3.5
--------------------------------------------------------------------------------
  Start Time:              2025-10-06 18:15:47
  Total Duration:          45s
  Average Time/Image:      2.15s
```

## Benefits

1. **Quality Comparison:** Users can now clearly distinguish which model produced which description
2. **Performance Analysis:** Easy to identify fastest/slowest models by name
3. **Decision Making:** Clear labels enable informed decisions about which models to use
4. **Consistency:** Same labeling logic used across all analysis tools
5. **Future-Proof:** Function handles new model versions automatically

## Future Enhancements

If needed, could also:
1. Create a shared utility module for label generation (avoid duplication)
2. Add labels to workflow log files (currently show raw model names)
3. Add model comparison dashboard in ImageDescriber GUI
4. Export labels to summary reports or HTML viewer

## Code Location

The model labeling logic is now centralized for consistency:

### Shared Utility Function
- **`imagedescriber/imagedescriber.py`** - Module-level `get_short_model_name()` function (lines 323-423)
  - Used by main GUI description list
  - Used by chat interface
  - Single source of truth for model name formatting

### Analysis Scripts
- **`LocalDoNotSubmit/combine_workflow_descriptions.py`** - `get_workflow_label()` function (lines 88-220)
  - Parses workflow directory names
  - Converts to human-readable labels for CSV output
  
- **`LocalDoNotSubmit/analyze_workflow_stats.py`** - `get_workflow_label()` function (lines 145-280)
  - Same logic as combine script
  - Ensures consistent labeling in performance analysis

All implementations handle the **same 27 models** with identical labeling rules.
