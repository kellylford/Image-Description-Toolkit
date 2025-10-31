# Configuration System Comprehensive Analysis
**Date**: 2025-10-31  
**Purpose**: Verify defaults work seamlessly, custom configs propagate properly

---

## Scenario 1: Default Workflow (Zero Config)

### Command
```bash
idt workflow C:\Photos
```

### Expected Behavior
- Uses default workflow_config.json from scripts/
- Uses default image_describer_config.json from scripts/
- Uses default video_frame_extractor_config.json from scripts/
- Default prompt style: "narrative"
- Default provider: "ollama"
- Everything works without user configuration

### Code Path Analysis

**workflow.py main()**:
- Line 2665: `workflow_config = args.config_workflow if args.config_workflow else "workflow_config.json"`
  - ✅ args.config_workflow defaults to "workflow_config.json" (line 2295)
  - ✅ Fallback to default if None
  
- Line 2666: `image_describer_config = args.config_image_describer  # Can be None`
  - ✅ None is OK - image_describer will use its own defaults
  
- Line 2667: `video_config = args.config_video  # Can be None`
  - ✅ None is OK - video extractor will use its own defaults

**workflow.py → image_describer subprocess**:
- Line 1335-1346: Config selection logic
  ```python
  if self.image_describer_config:
      config_to_use = self.image_describer_config  # Custom from user
  elif "config_file" in step_config:
      config_to_use = step_config["config_file"]  # From workflow config
  else:
      config_to_use = str(Path(__file__).parent / "image_describer_config.json")  # Default
  ```
  - ✅ Falls back to scripts/image_describer_config.json
  - Line 1346: `cmd.extend(["--config", config_to_use])`
  - ✅ Passes config to subprocess

**image_describer.py config loading**:
- Lines 1793-1807: Load config for argparse setup
  - Uses `load_json_config('image_describer_config.json', explicit=None)`
  - ✅ Will find scripts/image_describer_config.json via config_loader resolution
  
- Line 1948: `args = parser.parse_args()`
- Line 1997: `config_file=args.config`
  - ✅ Will be scripts/image_describer_config.json (default)

**video_frame_extractor.py config loading**:
- Need to check video extractor subprocess call

---

## Scenario 2: Custom Image Describer Config

### Command
```bash
idt workflow C:\Photos --config-id scripts/kelly.json
```

### Expected Behavior
- Uses default workflow_config.json
- Uses custom scripts/kelly.json for image_describer
- Custom prompt styles available (e.g., "orientation")
- Default video_frame_extractor_config.json

### Code Path Analysis

**workflow.py main()**:
- Line 2666: `image_describer_config = args.config_image_describer`
  - ✅ Will be "scripts/kelly.json"
  
**workflow.py → image_describer subprocess**:
- Line 1335: `if self.image_describer_config:`
  - ✅ True - uses custom config
- Line 1338: `config_to_use = self.image_describer_config`
- Line 1346: `cmd.extend(["--config", config_to_use])`
  - ✅ Passes "scripts/kelly.json" to subprocess

**image_describer.py with custom config**:
- Lines 1793-1807: Initial load for argparse
  - ❌ **PROBLEM**: Loads default config to get prompt choices
  - This caused the bug we just fixed (prompt-style validation)
  
- Lines 1948-1968: Validation after parsing (FIX APPLIED)
  - ✅ Now reloads config if args.config specified
  - ✅ Validates prompt-style against custom config
  
- Line 1997: `config_file=args.config`
  - ✅ Will be "scripts/kelly.json"
  - ImageDescriber class loads this config

---

## Scenario 3: Multiple Custom Configs

### Command
```bash
idt workflow C:\Photos --config-wf prod.json --config-id kelly.json --config-video highq.json
```

### Expected Behavior
- Uses prod.json for workflow orchestration
- Uses kelly.json for image_describer
- Uses highq.json for video_frame_extractor

### Code Path Analysis

**workflow.py main()**:
- Line 2665: `workflow_config = args.config_workflow`
  - ✅ Will be "prod.json"
- Line 2666: `image_describer_config = args.config_image_describer`
  - ✅ Will be "kelly.json"
- Line 2667: `video_config = args.config_video`
  - ✅ Will be "highq.json"

**workflow.py → video extractor subprocess**:
- Need to check if video_config is passed to subprocess

---

## Scenario 4: Guided Workflow (Interactive)

### Command
```bash
idt guideme
```

### Expected Behavior
- Prompts user for all choices
- Uses defaults for everything user doesn't customize
- If user provides custom config, loads and uses it

### Code Path Analysis

**guided_workflow.py**:
- Line 282: Custom config loading
  ```python
  config, path, source = load_json_config(config_filename, explicit=custom_config_path)
  ```
- Lines 603, 670, 703: Build workflow command
  - Currently uses `--config-image-describer` (updated in our changes)
  - ✅ Will pass custom config if provided

---

## Scenario 5: Deprecated --config Argument

### Command
```bash
idt workflow C:\Photos --config scripts/kelly.json
```

### Expected Behavior
- Shows deprecation warning
- Treats as --config-image-describer
- Works identically to explicit --config-id

### Code Path Analysis

**workflow.py argument parsing**:
- Line 2310: `--config` defined with `dest="_deprecated_config"`
- Lines 2429-2434: Deprecation handler
  ```python
  if hasattr(args, '_deprecated_config') and args._deprecated_config:
      print("WARNING: --config is deprecated...")
      if not args.config_image_describer:
          args.config_image_describer = args._deprecated_config
  ```
  - ✅ Properly maps to config_image_describer
  - ✅ Shows warning

---

## Issues Found

### ✅ FIXED: Prompt Style Validation with Custom Config
**Problem**: image_describer loaded default config before parsing args, rejecting custom prompts
**Fix**: Validate prompt-style after parsing args with custom config (commit 8ac0465)
**Status**: Fixed in code, needs rebuild

### ✅ VERIFIED: Video Config Propagation
**Status**: Working correctly
- workflow.py line 769-775: Uses self.video_config if provided, else defaults
- workflow.py line 790: Passes --config to extract-frames subprocess
- ✅ Custom video configs work

### ✅ VERIFIED: Image Describer Config Propagation  
**Status**: Working correctly
- workflow.py line 1335-1346: Uses self.image_describer_config if provided, else defaults
- workflow.py line 1346: Passes --config to image_describer subprocess
- ✅ Custom image describer configs work

### ✅ VERIFIED: Workflow Config Usage
**Status**: Working correctly
- workflow.py line 444: WorkflowConfig(config_file) loads and uses custom workflow config
- ✅ Custom workflow configs work

### ❌ BUG FOUND: Resume Doesn't Preserve Custom Config Paths
**Problem**: Workflow metadata (lines 2733-2743) doesn't include config paths
**Impact**: If user runs workflow with custom configs and resumes, the resume will use defaults
**Example**:
```bash
# Initial run with custom config
idt workflow photos --config-id kelly.json --prompt-style orientation
# ... workflow fails midway ...

# Resume (LOSES custom config!)
idt workflow --resume wf_photos_...
# This will use default config, not kelly.json
```

**Root Cause**: Lines 2733-2743 don't save:
- args.config_workflow
- args.config_image_describer  
- args.config_video

**Fix Needed**: Add config paths to metadata dict

### ❌ BUG FOUND: Help Text Shows Wrong Arguments (idt_cli.py)
**Problem**: `idt help` doesn't show new explicit config arguments
**Status**: Fixed in commit c707960, needs rebuild

---

## Summary

### ✅ Default Case (Zero Config) - WORKS
```bash
idt workflow C:\Photos
```
- Uses all defaults from scripts/ directory
- No user configuration needed
- ✅ Verified working

### ✅ Custom Config Case - MOSTLY WORKS
```bash
idt workflow C:\Photos --config-id kelly.json --prompt-style orientation
```
- Custom configs propagate through subprocess chain
- ✅ Workflow config works
- ✅ Image describer config works  
- ✅ Video config works
- ❌ **BUT**: Resume doesn't preserve custom configs

### ❌ Resume with Custom Configs - BROKEN
```bash
idt workflow --resume wf_photos_...
```
- Does NOT restore custom config paths
- Falls back to defaults
- **Needs fix**: Save config paths in workflow_metadata

---

## Recommended Fixes

### Priority 1: Resume Custom Config Preservation
**File**: scripts/workflow.py lines 2733-2743
**Change**: Add to metadata dict:
```python
metadata = {
    "workflow_name": workflow_name_display,
    "input_directory": str(input_dir),
    "provider": provider_name,
    "model": model_name,
    "prompt_style": prompt_style,
    "timestamp": timestamp,
    "steps": steps,
    "user_provided_name": bool(args.name),
    # NEW: Save custom config paths for resume
    "config_workflow": args.config_workflow if args.config_workflow != "workflow_config.json" else None,
    "config_image_describer": args.config_image_describer,
    "config_video": args.config_video
}
```

Then in resume code (line 2518), restore these:
```python
if workflow_state.get("config_workflow"):
    args.config_workflow = workflow_state["config_workflow"]
if workflow_state.get("config_image_describer"):
    args.config_image_describer = workflow_state["config_image_describer"]  
if workflow_state.get("config_video"):
    args.config_video = workflow_state["config_video"]
```

### Priority 2: Build with Fixes
- idt_cli.py help text (already committed)
- image_describer.py prompt validation (already committed)
- Resume config preservation (needs implementation)
