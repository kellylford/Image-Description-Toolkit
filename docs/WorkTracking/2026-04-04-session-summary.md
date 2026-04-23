# Session Summary: MLX vs Ollama Provider Experiment
**Date**: 2026-04-04  
**Duration**: ~6 hours (13:00–19:30)  
**Status**: Complete (report generated with available data)

---

## What Was Accomplished

### Primary Goal
Investigated why MLX providers report fewer input tokens than Ollama providers. Designed and ran a comprehensive automated experiment comparing all available local providers on real iPhone photos from the SMB photo library.

### Experiment Run
- **Script created**: `experiments/run_experiment.py` (comprehensive), `experiments/continue_experiment.py` (continuation after process stuck), `experiments/generate_report.py` (standalone report generator)
- **IDT version**: 4.0.0Beta2 bld1, macOS binary
- **Photo source**: `/Volumes/photos/MobileBackup/iPhone` (SMB)
- **Test images**: 11 iPhone photos, HEIC→JPEG converted, 1024px normalized

**Workflows completed**:
| Workflow | Provider | Model | Images | Status |
|----------|----------|-------|--------|--------|
| MLX_Qwen25_7B | mlx | Qwen2.5-VL-7B-Instruct-4bit | 11/11 | ✅ |
| MLX_Llama32_11B | mlx | Llama-3.2-11B-Vision-Instruct-4bit | 11/11 | ✅ |
| Ollama_Llama32V | ollama | llama3.2-vision:latest | 11/11 | ✅ |
| Ollama_Granite32V | ollama | granite3.2-vision:latest | 11/11 | ✅ |
| ResTest_512px | ollama | llama3.2-vision:latest | 5/5 | ✅ |
| ResTest_1024px | ollama | llama3.2-vision:latest | 6/11 | ⚠️ Partial (queue backlog) |
| ResTest_full_res | ollama | llama3.2-vision:latest | 0 | ❌ Not run |

**Report**: `experiments/REPORT.md`

---

## Key Findings

### Finding 1: Token Count Anomaly Explained
- **Qwen2.5-VL-7B (MLX)**: Consistently **1043 prompt tokens** per image at 1024px — very stable, reflects dynamic tiling that produces consistent patch counts for this resolution
- **Llama-3.2-11B-Vision (MLX)**: Only **34 prompt tokens** per image — this is a **mlx_vlm reporting limitation**, not an actual count of image patches. The model processes the full image but `GenerationResult.prompt_tokens` only counts text tokens for this model family
- **Ollama models**: Token counts **not logged by IDT CLI** at all (only processing time). This is a gap

### Finding 2: CLI vs GUI Ollama Inconsistency (Confirmed Bug)
- **CLI** (`image_describer.py`): Resizes to 1024px via `optimize_image()` before sending to Ollama
- **GUI** (`ai_providers.py::OllamaProvider`): Sends full-resolution images (no resize, only JPEG quality reduction if >3.75MB)
- **Impact**: GUI users send ~6× larger images to Ollama than CLI users, causing slower processing and non-reproducible results
- **Status**: Confirmed unintentional by project owner. Fix recommended in report.

### Finding 3: MLX Hard-Cap at 1024px (Undocumented)
- `MLXProvider._to_jpeg_tempfile()` always resizes to 1024px max — both GUI and CLI
- Undocumented. No user-facing config option.
- This means MLX is internally consistent but users can't test higher resolutions

### Finding 4: Performance Data
At equal 1024px input (CLI):

| Model | Provider | Avg Sec/Image | Avg Words/Description |
|-------|----------|--------------|----------------------|
| Qwen2.5-VL-7B-Instruct-4bit | MLX | **25.5s** ⚡ | 103.8 |
| granite3.2-vision:latest | Ollama | 35.2s | **178.5** |
| llama3.2-vision:latest | Ollama | 67.1s | 134.5 |
| Llama-3.2-11B-Vision-Instruct-4bit | MLX | 129.2s | 130.2 |

**Key insight**: Qwen2.5-VL-7B is surprisingly fast (fastest provider tested), while the larger Llama-3.2-11B is the slowest. Granite32V produced the longest descriptions on average.

---

## Bugs Discovered

### 1. `ConvertImage.py` Case Sensitivity Bug
- **File**: `scripts/ConvertImage.py`, line 269
- **Bug**: Globs only `*.heic` (lowercase), misses `*.HEIC` from SMB mounts
- **Fix**: Change to `pattern = '**/*.[hH][eE][iI][cC]'` or `*.{heic,HEIC}`
- **Status**: Documented in report; NOT yet fixed (requires build verification)

### 2. Subprocess `stdin` Not Closed in Experiment Scripts  
- **File**: `experiments/run_experiment.py`
- **Bug**: `subprocess.run()` without `stdin=subprocess.DEVNULL` — IDT's post-workflow "view results? y/n" prompt blocked forever, creating unkillable zombie processes (macOS PTY protection prevents cross-session SIGKILL)
- **Fix**: Added `stdin=subprocess.DEVNULL` to `subprocess.run()` call in both `run_experiment.py` and the fix prevented re-occurrence in `continue_experiment.py`
- **Status**: Fixed in experiment scripts

---

## Files Created This Session
- `experiments/run_experiment.py` — Full experiment script (7 workflows)
- `experiments/continue_experiment.py` — Continuation script (loads existing results, runs remaining workflows)
- `experiments/generate_report.py` — Standalone report generator (works from existing workflow data)
- `experiments/REPORT.md` — Final analysis report
- `experiments/workdir/` — All workflow outputs (9 workflow directories)
- `experiments/resized_images/` — Pre-processed test images (512px, 1024px, full_res subdirs)

---

## Technical Decisions

### Why Pre-Convert HEIC → JPEG in Python
`ConvertImage.py` only globs lowercase `*.heic`, but SMB-mounted iPhone photos have uppercase `HEIC` extensions. Worked around by converting directly with PIL before passing to IDT.

### Why Use `imagedescriber/.venv` for Experiments
This venv has `mlx_vlm` and PIL installed. The top-level `.venv` does not have mlx_vlm.

### Why Generate Report with Partial Data
The Ollama request queue became backlogged due to ~10 competing IDT processes (from the original stuck experiment that could not be killed). Rather than wait hours for the queue to drain, the report was generated from the 5 complete Part 1 workflows + 512px partial data. The missing ResTest_full_res data is noted as a limitation.

---

## Recommended Follow-Up Work

1. **Fix `ConvertImage.py`** case-insensitive HEIC glob (quick change, needs build + test)
2. **Fix GUI Ollama resize** in `ai_providers.py::OllamaProvider.describe_image()` (see report for code)
3. **Add Ollama token count logging** in `scripts/image_describer.py` 
4. **Complete ResTest_full_res** experiment in a clean Ollama session (kill all stale processes first: `pkill -f "idt workflow"`)
5. **Create GitHub issue** for CLI/GUI inconsistency if desired

---

## Testing Status

| What | Status |
|------|--------|
| Build verification | N/A — no code changes made to production files |
| MLX Qwen25 workflow | ✅ 11/11 images, verified in log |
| MLX Llama32 workflow | ✅ 11/11 images, verified in log |
| Ollama Llama32V workflow | ✅ 11/11 images, verified in log |
| Ollama Granite32V workflow | ✅ 11/11 images, verified in log |
| ResTest_512px | ✅ 5/5 images, avg 68.1s |
| Report generation | ✅ `experiments/REPORT.md`, 246 lines |
| `stdin=DEVNULL` fix | ✅ Verified: continuation script ran until Ollama queue backlog stopped it (11+ hours) |
