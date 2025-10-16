# Session Summary: October 15, 2025 - Prompt Style Bug Fix

## Overview

Major debugging session that uncovered and fixed a critical bug where all workflows with explicit `--prompt-style` arguments were incorrectly using "detailed" instead of the requested prompt style.

## Issues Discovered

### 1. Combined Descriptions CSV - Empty Descriptions
**Symptom:** Combined descriptions CSV showed mostly empty descriptions with just "**Image Description for Metadata**" header.

**Root Cause:** The description parser treated `---` markdown separators within detailed prompt descriptions as end-of-description markers.

**Fix:** Modified `analysis/combine_workflow_descriptions.py` to continue reading until next "File:" marker, ignoring `---` within descriptions.

**Commit:** `4c217c6` - Fix description parser to handle markdown separators within descriptions

### 2. Critical Bug - Prompt Style Override to "detailed"
**Symptom:** All 7 PromptBaseline workflows showed "detailed" in directory names despite batch file specifying 7 different prompts (Simple, artistic, colorful, concise, detailed, narrative, technical).

**Investigation Process:**
1. Discovered Archive2021 workflow (using same executable) correctly used "narrative" prompt
2. Found key difference: Archive2021 didn't specify `--prompt-style` (used default)
3. PromptBaseline workflows all specified explicit `--prompt-style` arguments
4. Workflow logs showed contradiction:
   - Log: "Using override prompt style for resume: Simple"
   - Command: "--prompt-style detailed"
   - This proved `validate_prompt_style("Simple")` was returning "detailed"

**Root Cause:** The `validate_prompt_style()` function in `scripts/workflow.py` used hardcoded relative paths to find `image_describer_config.json`:
- `image_describer_config.json`
- `scripts/image_describer_config.json`

In a PyInstaller frozen executable, these paths don't exist (config is at `sys._MEIPASS/scripts/image_describer_config.json`). When all `open()` calls failed, the function fell through to the fallback: `return "detailed"`.

**Fix:** Updated `validate_prompt_style()` to use the `config_loader` module which has PyInstaller-compatible path resolution. Added graceful degradation to pass through the style if config can't be loaded.

**Commit:** `653052e` - Fix: validate_prompt_style() now works in frozen executable

**Testing:**
- Tested from `/tmp` directory (no external config files) with `--prompt-style Simple`
- Result: ✅ Created directory `wf_test_final_fix_ollama_qwen3-vl_235b-cloud_Simple_*`
- Verified all 7 prompt styles work correctly in production

### 3. Batch File Output Directory Issue
**Symptom:** `run_all_prompts_cloudqwen.bat` was creating output in `c:\idt\bat\Descriptions` instead of `c:\idt\Descriptions`.

**Root Cause:** The batch file didn't change to parent directory or specify output directory.

**Fix:** Updated `/c/idt/bat/run_all_prompts_cloudqwen.bat` to:
- Change to parent directory: `cd /d "%~dp0\.."` 
- Specify output: `--output-dir Descriptions`
- Save original directory: `--original-cwd "%ORIGINAL_CWD%"`

**Note:** This was only in the external install, not the repository version.

## Documentation Created

1. **docs/PROMPT_WRITING_GUIDE.md** (970 lines)
   - Comprehensive guide covering all 7 built-in prompt styles
   - Model-specific recommendations for 14 models
   - Cost estimators and token usage guidance
   - Custom prompt creation techniques
   - Side-by-side examples and decision trees
   - **Commit:** `430165f`

2. **docs/BUG_FIX_PROMPT_STYLE_OVERRIDE.md**
   - Detailed documentation of the prompt style bug
   - Root cause analysis with code examples
   - Fix implementation details
   - Testing verification steps
   - Prevention recommendations
   - **Commit:** `653052e`

## Results

### Before Fix
- All 7 PromptBaseline workflows used "detailed" prompt
- Directory names: `wf_promptbaseline_*_detailed_*`
- All descriptions followed same detailed format

### After Fix
- All 7 PromptBaseline workflows use correct prompt styles
- Directory names show distinct styles:
  - `wf_promptbaseline_*_Simple_*`
  - `wf_promptbaseline_*_artistic_*`
  - `wf_promptbaseline_*_colorful_*`
  - `wf_promptbaseline_*_concise_*`
  - `wf_promptbaseline_*_detailed_*`
  - `wf_promptbaseline_*_narrative_*`
  - `wf_promptbaseline_*_technical_*`
- Descriptions show clear differences in style and approach

### Sample Comparison (Same Image)

**Simple Prompt:**
> "This is a cheerful, close-up selfie of an older woman with a vibrant, rainbow-colored haircut, taken in what appears to be a hair salon..."

**Artistic Prompt:**
> "This image presents a vibrant, intimate portrait that blends documentary realism with expressive personal artistry. Here's an artistic analysis:
> 
> **Visual Composition and Framing**
> The photograph is a close-up, slightly high-angle selfie..."

**Concise Prompt:**
> "A cheerful older woman with vibrant rainbow-colored hair (blue, green, yellow, orange, purple) and glasses smiles at the camera in a selfie. She's wearing a black salon cape over a dark shirt..."

Clear differences demonstrate that prompt style has significant impact on description quality and format!

## Key Learnings

1. **PyInstaller Path Issues:** Config file access in frozen executables requires special handling via `config_loader` module
2. **Testing Frozen Executables:** Must test separately from Python scripts, from different working directories
3. **Fallback Behavior:** Silent failures in `try/except` blocks can hide critical bugs
4. **Graceful Degradation:** When validation fails, trust the caller's input rather than forcing a default

## Files Modified

### Code Changes
- `scripts/workflow.py` - Fixed `validate_prompt_style()` function
- `analysis/combine_workflow_descriptions.py` - Fixed description parser

### Documentation Added
- `docs/PROMPT_WRITING_GUIDE.md` - Comprehensive prompt writing guide
- `docs/BUG_FIX_PROMPT_STYLE_OVERRIDE.md` - Bug fix documentation
- `docs/worktracking/SESSION_OCT15_2025_PROMPT_BUG_FIX.md` - This file

### External Files (Not in Repo)
- `/c/idt/idt_fixed.exe` - Fixed executable (deployed)
- `/c/idt/bat/run_all_prompts_cloudqwen.bat` - Fixed batch file

## Git Commits

1. `4c217c6` - Fix description parser to handle markdown separators within descriptions
2. `430165f` - Add comprehensive Prompt Writing Guide  
3. `653052e` - Fix: validate_prompt_style() now works in frozen executable

**Branch:** ImageDescriber  
**Status:** 3 commits ahead of origin/ImageDescriber (ready to push)

## Next Steps

1. ✅ Archive2021 workflow still running (272/729 images as of session end)
2. ✅ PromptBaseline workflows completed successfully with correct prompt styles
3. ✅ Fixed executable deployed and verified
4. Push commits to GitHub: `git push origin ImageDescriber`
5. Wait for Archive2021 to complete
6. Generate combined descriptions CSV from all completed workflows
7. Analyze differences between prompt styles for research/documentation

## Impact Assessment

**Severity:** High - Affected all workflows with explicit `--prompt-style` arguments  
**Duration:** October 9 (config_loader introduction) to October 15 (fix)  
**Workflows Affected:** Any workflow run with frozen executable specifying `--prompt-style`  
**Data Integrity:** Workflows completed successfully but used wrong prompt style  
**User Impact:** Confusion about why all prompts produced same style, wasted compute time

## Conclusion

This was a challenging debugging session that uncovered a fundamental bug in how the frozen executable handled prompt style validation. The fix ensures that users can reliably specify different prompt styles and get the expected results. The investigation also produced valuable documentation (970-line prompt writing guide) and demonstrated the significant impact that prompt engineering can have on AI-generated descriptions.

The power of changing prompts is now clearly visible in the PromptBaseline results, showing how the same model responds very differently to different prompt styles even with a simple set of test images.
