# Session Summary — 2026-06-17

**Branch:** `v4.5`
**Topic:** Refresh local (on-device) vision models for the Mac / MLX provider — add Qwen3-VL, move the Mac default off Moondream.

## Motivation

Research into the 2026 local-VLM landscape (focus: Apple Silicon) found the MLX
known-good list was one generation behind. Qwen3-VL had shipped and is the current
consensus best-quality on-device captioner (PhotoPrism's 2026 head-to-head;
mlx-vlm now supports it). The toolkit's MLX default effectively led with older
Qwen2.x models, and the global default model was still Moondream — whose
description quality is now outdated versus newer models. Owner wants to move away
from Moondream on Mac specifically.

## Changes

### New models (MLX provider)
- Added `mlx-community/Qwen3-VL-4B-Instruct-4bit` (~3.1 GB) as the **first** entry in
  `MLXProvider.KNOWN_MODELS` — making it the de-facto MLX default (used when the
  configured `default_model` is not an MLX repo ID). This is the recommended Mac default.
- Added `mlx-community/Qwen3-VL-8B-Instruct-4bit` (~5.8 GB) for higher quality on 16 GB+ Macs.
- Kept Qwen2.x / Gemma / Phi / SmolVLM / Llama entries for back-compat (re-grouped as "previous generation").

### Dependency floor
- Bumped `mlx-vlm>=0.3.0` → `mlx-vlm>=0.6.3` in both `requirements.txt` and
  `imagedescriber/requirements.txt`. **This is a hard requirement, not cosmetic** — see test results.

### Files touched
| File | Change |
|------|--------|
| `imagedescriber/ai_providers.py` | `KNOWN_MODELS` reordered + 2 Qwen3-VL entries; docstring/comments updated (Qwen2-VL → Qwen3-VL) |
| `imagedescriber/imagedescriber_wx.py` | `_SIZE_ESTIMATES` dict: added Qwen3-VL-4B (~3.1 GB), Qwen3-VL-8B (~5.8 GB) |
| `imagedescriber/dialogs_wx.py` | MLX tooltip metadata: added Qwen3-VL-4B (★ recommended) + 8B; refreshed stale import-failure fallback list (dropped removed `llava-1.5-7b`, led with Qwen3-VL) |
| `requirements.txt`, `imagedescriber/requirements.txt` | mlx-vlm floor → 0.6.3 with explanatory comment |

All other code paths (CLI `scripts/guided_workflow.py`, `scripts/workflow.py`, dialog
population) read `MLXProvider.KNOWN_MODELS` dynamically, so they pick up the new
default automatically — no edits needed.

## Test results (real, on this Apple Silicon Mac)

Verified end-to-end against `testimages/coffee_desk.jpg`, not just syntax.

1. **`py_compile`** of all three edited Python files — passed.
2. **Import check** — `MLXProvider.KNOWN_MODELS[0]` == Qwen3-VL-4B; provider `is_available()` True.
3. **Live inference, first attempt (mlx-vlm 0.4.4):** ❌ **FAILED** —
   `ValueError: Unrecognized video processor` from transformers 5.5.0 when loading the
   Qwen3-VL processor. The provider's existing `_patch_transformers_video_bug()` does
   not cover this path (it patches a different `TypeError`). **This is why the floor
   bump matters** — the model downloads fine but cannot load on 0.4.x.
4. **Upgraded venv to mlx-vlm 0.6.3** (transformers stayed 5.5.0). **Live inference: ✅ PASS** —
   load 2.0s, 307 tokens @ 22 tok/s (~18s), high-quality detailed description.
5. **Regression check on 0.6.3:** Qwen2-VL-2B ✅ and gemma-3-4b-it-qat ✅ still load and
   describe correctly — upgrading does not break existing models.

### Initial mistake, corrected by testing
The HuggingFace model cards say Qwen3-VL was "converted with mlx-vlm 0.3.4," so the
floor was first set to `>=0.3.4`. The live run proved that's the *converter* version,
not the *runtime* version — 0.4.4 fails to load it. Floor corrected to `>=0.6.3`
(the version verified to load it here). Lesson: converter version ≠ runtime-capable version.

## NOT tested / follow-ups
- **Not** built into a PyInstaller exe and smoke-tested (`dist/idt`). The change is a
  data/list + requirements change with no new code paths, but per project rules a
  frozen-mode build + `idt workflow testimages` run should be done before release.
- **Not** verified in the wxPython GUI interactively (model dropdown / tooltip / download
  prompt rendering). Underlying data verified; GUI rendering of the new entries unverified.
- Existing users with a pre-existing venv must `pip install -U mlx-vlm` (>=0.6.3) — the
  floor only governs fresh installs. Worth a release-note callout. `macsetup.sh` installs
  from requirements, so fresh Mac setups are covered.
- Qwen3-VL-8B (~5.8 GB) not individually run here; only the 4B was exercised end-to-end.
- Did not add Moondream3 / Gemma 4-small MLX entries — intentionally, per owner's
  preference to move away from Moondream on Mac and to keep this change focused.
