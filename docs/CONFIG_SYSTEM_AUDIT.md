# Configuration System Comprehensive Audit
**Date:** October 31, 2025  
**Branch:** 3.5beta  
**Related Issue:** #62  
**Status:** ✅ ALL BUGS FIXED - 5 bugs found and fixed

## Critical Bug Summary

Found and fixed **5 critical bugs** in configuration system:

1. **guided_workflow.py** - Completely ignored `--config` flag (commit be2f1e8)
2. **workflow.py** - Didn't pass `--config` to image_describer (commit ab07750)
3. **list_prompts.py** - No `--config` support (commit ef7721a)
4. **guided_workflow.py** - Wrong parameters to load_json_config (commit aacf4ce) ⚠️ **CRITICAL**
5. **list_prompts.py** - Wrong parameters to load_json_config (commit 9c02340) ⚠️ **CRITICAL**

## Bugs #4 and #5: The Subtle load_json_config() Bug

### The Problem:
When user runs `idt guideme --config scripts\kelly.json`:
- ✅ Code converts to absolute: `c:\idt\scripts\kelly.json`
- ✅ Verifies file exists
- ✅ Shows "Using custom configuration" message
- ❌ **Then passes full path as filename parameter!**

**Wrong:**
```python
config, path, source = load_json_config('c:\idt\scripts\kelly.json')
```

This tells load_json_config to SEARCH for a file NAMED `c:\idt\scripts\kelly.json`, which obviously fails!

**Correct:**
```python
config, path, source = load_json_config('kelly.json', explicit='c:\idt\scripts\kelly.json')
```

This properly tells config_loader: "The filename is kelly.json, but use this explicit path."

### Comprehensive Audit of ALL load_json_config() Calls:

- ✅ **image_describer.py** line 1691 - CORRECT (uses explicit parameter properly)
- ✅ **workflow.py** line 151 - CORRECT (uses explicit parameter properly)
- ❌ **guided_workflow.py** line 282 - WRONG → FIXED (commit aacf4ce)
- ❌ **list_prompts.py** line 35 - WRONG → FIXED (commit 9c02340)
- ✅ **test files** - correct (test-specific usage)

**Result:** All config loading now uses load_json_config() correctly!

## Summary
Audited ALL IDT commands and scripts for `--config` flag support.

## ✅ FIXED - Full --config Support (3 scripts)

### 1. guided_workflow.py ✅
- **Command:** `idt guideme --config <file>`
- **Config Type:** image_describer_config.json
- **Status:** FIXED in commit be2f1e8
- **Changes:**
  - Added --config/-c argument parsing
  - Uses config_loader.py for resolution
  - Passes config to workflow subprocess
  - Shows debugging output

### 2. workflow.py ✅
- **Command:** `idt workflow --config <file>`
- **Config Type:** workflow_config.json OR image_describer_config.json
- **Status:** FIXED in commit ab07750
- **Changes:**
  - Stores user's config_file in orchestrator
  - Passes to image_describer with priority:
    1. User's --config (highest)
    2. step_config from workflow_config.json
    3. Default image_describer_config.json

### 3. list_prompts.py ✅
- **Command:** `idt prompt-list --config <file>`
- **Config Type:** image_describer_config.json
- **Status:** FIXED in commit ef7721a
- **Changes:**
  - Replaced hardcoded find_config_file()
  - Uses config_loader.py
  - Added --config/-c argument
  - Updated help text with examples

## ✅ ALREADY WORKING - Has --config Support (2 scripts)

### 4. image_describer.py ✅
- **Command:** `idt image_describer --config <file>`
- **Config Type:** image_describer_config.json
- **Status:** Already has full support
- **Line 1900:** `"--config"` argument defined
- **No changes needed**

### 5. video_frame_extractor.py ✅
- **Command:** `idt extract-frames --config <file>`
- **Config Type:** video_frame_extractor_config.json
- **Status:** Already has full support
- **Line 762:** `-c, --config` argument defined with default
- **No changes needed**

## ✅ NO CONFIG FILES USED (7 commands)

### 6. stats (stats_analysis.py) ✅
- **Command:** `idt stats <workflow_dir>`
- **Config:** None - reads workflow metadata files
- **No changes needed**

### 7. contentreview (content_analysis.py) ✅
- **Command:** `idt contentreview <workflow_dir>`
- **Config:** None - reads descriptions CSV
- **No changes needed**

### 8. combinedescriptions (combine_workflow_descriptions.py) ✅
- **Command:** `idt combinedescriptions <workflow_dirs...>`
- **Config:** None - reads descriptions and EXIF data
- **Note:** Has comment about prompt styles matching config, but doesn't load it
- **No changes needed**

### 9. descriptions-to-html (descriptions_to_html.py) ✅
- **Command:** `idt descriptions-to-html <csv_file>`
- **Config:** None - pure transformation script
- **No changes needed**

### 10. convert-images (ConvertImage.py) ✅
- **Command:** `idt convert-images <input_dir>`
- **Config:** None - simple HEIC to JPG conversion
- **No changes needed**

### 11. check-models (check_ollama_models.py) ✅
- **Command:** `idt check-models`
- **Config:** None - queries Ollama API
- **No changes needed**

### 12. results-list (list_results.py) ✅
- **Command:** `idt results-list`
- **Config:** None - scans filesystem for workflow directories
- **No changes needed**

## 🎯 Configuration System Complete!

### Before Today (3 CRITICAL BUGS):
- ❌ `guideme --config` completely ignored
- ❌ `workflow` didn't pass --config to image_describer
- ❌ `prompt-list --config` didn't work

### After Today (ALL WORKING):
- ✅ guideme → workflow → image_describer chain complete
- ✅ prompt-list can verify custom prompts
- ✅ All config-using scripts support --config
- ✅ Consistent use of config_loader.py

### Testing Workflow:
```bash
# 1. Create custom config
copy scripts\image_describer_config.json scripts\kelly.json
# Edit kelly.json to add "orientation" prompt

# 2. Verify prompts
idt prompt-list --config scripts\kelly.json
idt prompt-list --config scripts\kelly.json --verbose

# 3. Use in guided workflow
idt guideme --config scripts\kelly.json

# 4. Use directly in workflow
idt workflow photos --config scripts\kelly.json --provider ollama --model moondream

# 5. Use directly with image_describer
idt image_describer photos --config scripts\kelly.json --provider ollama --model moondream
```

### Configuration Resolution Order (via config_loader.py):
1. Explicit --config path
2. File-specific env var (IDT_IMAGE_DESCRIBER_CONFIG, etc.)
3. IDT_CONFIG_DIR + filename
4. Frozen exe /scripts/ directory
5. Frozen exe root directory
6. Current working directory
7. Bundled script directory (fallback)

## Architecture Summary

### Files Modified (3):
- `scripts/guided_workflow.py` - Added full --config support
- `scripts/workflow.py` - Pass user's --config to subprocesses
- `scripts/list_prompts.py` - Added --config support with config_loader

### Key Pattern Established:
All config-loading code should:
1. Accept `--config` command-line argument
2. Use `config_loader.py` for resolution (not hardcoded paths)
3. Pass config through subprocess chains
4. Show clear debugging info about which config is loaded

## Next Steps:
1. ✅ Rebuild idt.exe to include all fixes
2. ✅ Test custom config end-to-end
3. ✅ Update GitHub Issue #62 with audit results
4. ✅ Configuration system fully functional!
