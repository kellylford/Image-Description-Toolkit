# Session Summary: October 31, 2025

## Status: 3.5-beta Branch Restored to Working State

After extensive debugging and fixing configuration system bugs, the system is back to a working state.

---

## What Works Now ✅

### Direct Workflow Commands
```bash
# Basic workflow (no custom config) - WORKS
idt workflow \\ford\home\photos\mobilebackup\iphone\2025\09

# Workflow with custom config - WORKS
idt workflow \\ford\home\photos\mobilebackup\iphone\2025\09 \
  --config scripts\kelly.json \
  --prompt-style orientation
```

**Confirmed working runs:**
- `C:\idt\Descriptions\wf_2025_09_ollama_moondream_narrative_20251031_105851` - Default config
- Network paths work correctly (UNC paths like `\\ford\...`)
- Custom prompts ("orientation") are recognized and applied
- File discovery works for both HEIC and regular images

### Configuration System
- ✅ Custom `image_describer_config.json` files can be specified via `--config`
- ✅ Custom prompt styles are loaded from custom configs
- ✅ `idt prompt-list --config C:/idt/scripts/kelly.json` shows custom prompts
- ✅ Model settings, metadata settings, geocoding all customizable

---

## Known Issues ⚠️

### Guided Workflow with Custom Config
```bash
# This path has issues (workflow created but may not process files correctly)
idt guideme --config scripts\kelly.json
```

**Status:** Needs more testing to confirm if Bug #9 fix resolved this completely.

**Workaround:** Use direct `idt workflow` commands with `--config` and `--prompt-style` arguments instead of `guideme`.

---

## Bugs Fixed This Session (9 Total)

### Bug #1: guided_workflow.py ignored --config flag
- **Commit:** be2f1e8
- **Fix:** Added --config/-c argument parsing and config_loader.py usage

### Bug #2: workflow.py didn't pass --config to image_describer
- **Commit:** ab07750
- **Fix:** Store and pass config_file through subprocess chain

### Bug #3: list_prompts.py no --config support
- **Commit:** ef7721a
- **Fix:** Added --config/-c argument, replaced hardcoded paths

### Bug #4: guided_workflow.py wrong load_json_config parameters
- **Commit:** aacf4ce
- **Fix:** Pass filename + explicit path separately, not full path as filename
- **Severity:** CRITICAL - caused config to be ignored silently

### Bug #5: list_prompts.py wrong load_json_config parameters
- **Commit:** 9c02340
- **Fix:** Same as Bug #4
- **Severity:** CRITICAL

### Bug #6: workflow.py missing --config argument definition
- **Commit:** ff0d9a1
- **Fix:** Added parser.add_argument("--config")
- **Note:** Initially created duplicate argument, fixed in Bug #7

### Bug #7: workflow.py duplicate --config arguments + KeyError crash
- **Commit:** 4c96a14
- **Fix:** Removed duplicate, added check for 'workflow' key before updating config

### Bug #8: workflow.py --config missing default value
- **Commit:** 3b7b2d0
- **Fix:** Added default="workflow_config.json"
- **Symptom:** "Could not load workflow config: NoneType" warnings

### Bug #9: workflow.py --config used for wrong config file
- **Commit:** fdc2ef8
- **Fix:** WorkflowOrchestrator always uses "workflow_config.json", not args.config
- **Severity:** CRITICAL - caused file discovery failure with custom configs
- **Root Cause:** image_describer_config.json passed as workflow_config.json

---

## Architecture Clarifications

### Three Separate Config Files
IDT workflow system uses **three different config files**:

1. **workflow_config.json** - Workflow orchestration
   - Steps configuration
   - Directory structure
   - File patterns

2. **image_describer_config.json** - AI and metadata
   - Prompt templates and variations
   - Model settings (temperature, tokens, etc.)
   - Metadata extraction and geocoding
   - **This is what users typically customize**

3. **video_frame_extractor_config.json** - Video extraction
   - FPS settings
   - Quality settings
   - Filters

### Current --config Behavior (After Bug #9 Fix)
- `--config` in workflow.py is **ONLY for image_describer_config.json**
- Workflow orchestration **ALWAYS uses default workflow_config.json**
- This is a pragmatic fix but creates ambiguity
- **Future:** Need explicit `--config-workflow`, `--config-image-describer`, `--config-video`

---

## Additional Enhancements

### normalize_model_name() Function
- **Added:** Commit 3b7b2d0
- **Purpose:** Strip provider prefix from model names
- **Example:** `ollama:llama3.2-vision:11b` → `llama3.2-vision:11b`
- **Reason:** Ollama API expects model name without provider prefix

### Build Number System
- **Status:** Working correctly
- **Behavior:** Auto-increments bld001 → bld002 → bld003
- **Fix:** BUILD_TRACKER.json preserved during builds (commit fa44967)

---

## Testing Completed

### Manual Testing
- ✅ Workflow without --config finds files on network paths
- ✅ Workflow with --config and custom prompt style works
- ✅ prompt-list shows custom prompts from custom config
- ✅ Network UNC paths work (`\\ford\...`, `\\qnap\...`)
- ✅ Build number increments correctly

### Automated Testing
- ✅ 4 configuration system validation tests added
- ⏳ Comprehensive 30+ test suite pending (Issue #62)

---

## Next Steps (Future Work)

### Immediate (Stay on 3.5-beta)
1. ✅ Document current working state - DONE
2. 🔄 Create new branch for explicit config arguments work
3. Test guideme with custom config more thoroughly

### Future (New Branch: explicit-configs)
1. Implement `--config-workflow`, `--config-image-describer`, `--config-video`
2. Add short forms: `--config-wf`, `--config-id`, `--config-video`
3. Keep `--config` as deprecated alias with warning
4. Update all commands and documentation
5. Comprehensive testing before merge back to 3.5-beta

### Long Term
1. Comprehensive test suite (Issue #62)
2. CI/CD integration
3. Formal release process for v3.5.0

---

## Files Modified This Session

### Core Workflow Files
- `scripts/guided_workflow.py` - Config argument handling (Bugs #1, #4)
- `scripts/workflow.py` - Config passing, argument definition (Bugs #2, #6, #7, #8, #9)
- `scripts/list_prompts.py` - Config support (Bugs #3, #5)

### Build System
- `BuildAndRelease/build_idt.bat` - BUILD_TRACKER preservation
- `BuildAndRelease/builditall.bat` - cd command placement fix

### Documentation
- `docs/archive/CONFIG_SYSTEM_AUDIT.md` - Comprehensive audit
- `docs/archive/BUILD_NUMBER_SYSTEM.md` - Build versioning docs
- `docs/WorkTracking/ISSUE-explicit-config-arguments.md` - Future proposal
- `.github/copilot-instructions.md` - Rules #9 and #10 (testing requirements)

### Tests
- `pytest_tests/unit/test_configuration_system.py` - 4 validation tests

---

## Lessons Learned

### From AI Instructions Update (Rule #9)
**"Test Before Claiming Complete"**
- BUILD the executable if changes affect compiled code
- RUN with realistic test scenarios
- VERIFY end-to-end, not just syntax
- Don't ask user to test - agent tests first

### From This Session
1. Configuration system had grown organically without consistent design
2. Single `--config` argument for multiple config types creates ambiguity
3. Subtle API bugs (wrong parameters) can cause silent failures
4. Need comprehensive regression testing before major changes
5. Working state should be preserved before experimental work

---

## Quotes from Session

> "how can this be so broken. it was all working."

> "we are spending fucking hours on this bullshit and for all I know we are going in circles."

**Resolution:** Found and fixed root cause (Bug #9). System working again. Creating branch for future enhancements to avoid disrupting working state.

---

## Current Commit Status

**Branch:** 3.5-beta  
**Commits ahead of origin:** 15  
**Last commit:** fdc2ef8 (Bug #9 fix)  
**Status:** Working state restored, ready for new branch

**Recommendation:** Push 3.5-beta to origin before creating new branch to preserve this working state.
