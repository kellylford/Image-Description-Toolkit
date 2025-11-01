# Issue: Replace Ambiguous --config with Explicit Config Arguments

**Created**: October 31, 2025  
**Priority**: High  
**Target**: v3.5-beta or v3.6  
**Status**: Proposed (No Code Changes Yet)

---

## Problem Statement

The current `--config` argument is ambiguous because IDT workflow system uses **three different config files** for different purposes:

1. **workflow_config.json** - Workflow orchestration settings (steps, directories, file patterns)
2. **image_describer_config.json** - AI prompts, models, metadata, geocoding settings
3. **video_frame_extractor_config.json** - Video extraction settings (fps, quality, filters)

### Current Behavior (Broken/Confusing)

When user runs:
```bash
idt workflow path/ --config C:/idt/scripts/kelly.json
```

**What happens:**
1. `workflow.py` receives `--config` and treats it as `workflow_config.json`
2. `workflow.py` passes same `--config` to `image_describer.py`
3. `image_describer.py` treats it as `image_describer_config.json`
4. **Result:** Same file interpreted as TWO different config types!

### User's Actual Intent

Most users (including primary developer) want to customize:
- ✅ AI prompts (in `image_describer_config.json`)
- ✅ Model settings (in `image_describer_config.json`)
- ✅ Metadata/geocoding (in `image_describer_config.json`)
- ❌ NOT workflow orchestration settings (rarely changed)

But the current system forces them to use a single `--config` that's misinterpreted.

---

## Proposed Solution

### Replace Single --config with Three Explicit Arguments

**New Arguments:**
```bash
idt workflow path/ \
  --config-workflow workflow.json \
  --config-image-describer kelly.json \
  --config-video video.json
```

**Short Forms:**
```bash
--config-wf          # Workflow orchestration
--config-id          # Image describer (prompts, AI, metadata)
--config-video       # Video frame extraction
```

**Backward Compatibility:**
Keep `--config` as alias for `--config-image-describer` (most common use case) with deprecation warning:
```bash
idt workflow path/ --config kelly.json
# WARNING: --config is deprecated, use --config-image-describer instead
```

---

## Benefits

### 1. Clarity
✅ Users know exactly which config file controls what  
✅ No more ambiguity about which config is being used  
✅ Matches actual architecture (3 separate config systems)

### 2. Flexibility
✅ Can mix different config files:
```bash
idt workflow path/ \
  --config-wf production.json \
  --config-id artistic-prompts.json \
  --config-video high-quality.json
```

✅ Can override just one config while using defaults for others

### 3. Debugging
✅ Clear error messages: "Custom workflow config not found: production.json"  
✅ Logs show exactly which config file was loaded for which purpose  
✅ No confusion in troubleshooting

---

## Implementation Plan

### Phase 1: Add New Arguments (No Breaking Changes)
1. Add `--config-workflow`, `--config-image-describer`, `--config-video` to `workflow.py`
2. Add short forms: `--config-wf`, `--config-id`, `--config-video`
3. Keep `--config` working as alias for `--config-image-describer`
4. Add deprecation warning when `--config` is used

### Phase 2: Update All Commands
Commands that need updates:
- [x] `workflow.py` - Add all three config arguments
- [ ] `guided_workflow.py` - Ask which config types to customize
- [ ] `list_prompts.py` - Use `--config-image-describer` explicitly
- [ ] Documentation - Update all examples

### Phase 3: Update Config Passing to Subprocesses
Current subprocess calls pass single `--config`, need to pass specific ones:
```python
# Current (ambiguous)
cmd.extend(["--config", config_file])

# New (explicit)
if workflow_config:
    cmd.extend(["--config-workflow", workflow_config])
if image_describer_config:
    cmd.extend(["--config-image-describer", image_describer_config])
if video_config:
    cmd.extend(["--config-video", video_config])
```

### Phase 4: Deprecation (Future Release)
1. In v3.6: Add deprecation warnings for `--config`
2. In v4.0: Remove `--config` entirely

---

## Config File Detection

### Current System (config_loader.py)
Searches in this order:
1. Explicit path passed by caller
2. File environment variable (e.g., `IDT_IMAGE_DESCRIBER_CONFIG`)
3. `IDT_CONFIG_DIR` env var + filename
4. Frozen exe dir `/scripts/<filename>`
5. Frozen exe dir `/<filename>`
6. Current working directory
7. Bundled script directory (fallback)

### New System Enhancement
With explicit arguments, detection becomes clearer:

**When user specifies:**
```bash
--config-id C:/idt/scripts/kelly.json
```

**System should:**
1. ✅ Try exact path: `C:/idt/scripts/kelly.json`
2. ✅ If not found, try relative to cwd: `./C:/idt/scripts/kelly.json`
3. ✅ If not found, try `$IDT_CONFIG_DIR/kelly.json`
4. ❌ ERROR with clear message: "Image describer config not found: C:/idt/scripts/kelly.json"

**When user doesn't specify:**
1. Use environment variable: `$IDT_IMAGE_DESCRIBER_CONFIG`
2. Use `$IDT_CONFIG_DIR/image_describer_config.json`
3. Use frozen exe bundled copy
4. Use development mode `scripts/image_describer_config.json`

---

## Testing Requirements

### Unit Tests
- [ ] Test each config argument independently
- [ ] Test mixing config arguments
- [ ] Test backward compatibility with `--config`
- [ ] Test error messages for missing configs
- [ ] Test config resolution order

### Integration Tests
- [ ] Full workflow with custom workflow config
- [ ] Full workflow with custom image describer config
- [ ] Full workflow with custom video config
- [ ] Full workflow with all three custom configs
- [ ] Guided workflow with custom configs

### Regression Tests
- [ ] Existing batch files still work
- [ ] Existing commands with `--config` still work (with deprecation warning)
- [ ] Resume functionality with custom configs

---

## Related Issues

- #62 - Configuration System Comprehensive Testing (30+ tests needed)
- CONFIG_SYSTEM_AUDIT.md - Documents all 8 config bugs found and fixed
- Bug #8 - `--config` missing default value (FIXED Oct 31, 2025)

---

## Current Status

**Decision:** NO CODE CHANGES YET - System must be stable first

**Priority Actions:**
1. ✅ Fix all critical config bugs (Bugs #1-8) - COMPLETE
2. ✅ Get system working reliably - IN PROGRESS
3. ⏳ Create comprehensive tests (Issue #62)
4. ⏳ Then implement this enhancement

**Timeline:**
- **Oct 31, 2025**: Issue documented
- **Target**: v3.6 or later (after v3.5-beta is stable)

---

## Examples of New Usage

### Simple Case (Most Common)
```bash
# User just wants custom prompts
idt workflow photos/ --config-id artistic-prompts.json

# Or with short form
idt workflow photos/ --config-id artistic.json
```

### Complex Case
```bash
# Production workflow with custom settings for everything
idt workflow media/ \
  --config-wf production-workflow.json \
  --config-id high-quality-prompts.json \
  --config-video high-fps-extraction.json \
  --steps video,convert,describe,html
```

### Backward Compatible
```bash
# Old way (still works with deprecation warning)
idt workflow photos/ --config kelly.json
# WARNING: --config is deprecated, use --config-image-describer instead
```

### Guided Workflow
```bash
idt guideme
# Wizard asks: "Which configs do you want to customize?"
#   [ ] Workflow settings (advanced)
#   [x] Image describer (prompts, AI, metadata)
#   [ ] Video extraction (advanced)
```

---

## Notes

- This enhancement was proposed after fixing Bug #8 (missing default value)
- User quote: "how can this be so broken. it was all working."
- Root cause: Config system grew organically, never had consistent design
- This proposal brings architectural clarity to match actual usage patterns
