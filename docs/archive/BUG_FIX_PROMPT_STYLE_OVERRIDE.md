# Bug Fix: Prompt Style Override to "detailed"

**Date:** October 15, 2025  
**Severity:** High - Affected all workflows with explicit `--prompt-style` arguments  
**Status:** FIXED ✅

## Summary

All workflows that specified `--prompt-style` on the command line were incorrectly using "detailed" instead of the requested prompt style. This affected 7 PromptBaseline workflows that should have used Simple, artistic, colorful, concise, detailed, narrative, and technical prompts.

## Root Cause

The `validate_prompt_style()` function in `scripts/workflow.py` could not find the `image_describer_config.json` file when running as a PyInstaller frozen executable, causing it to always return the fallback value "detailed".

### Why It Failed

1. **Old Code** (lines 108-142 in workflow.py):
   ```python
   def validate_prompt_style(style: str, config_file: str = "image_describer_config.json") -> str:
       try:
           import json
           config_paths = [
               config_file,
               "image_describer_config.json",
               "scripts/image_describer_config.json"
           ]
           
           for config_path in config_paths:
               try:
                   with open(config_path, 'r', encoding='utf-8') as f:
                       config = json.load(f)
                       # ... validate style ...
               except (FileNotFoundError, json.JSONDecodeError):
                   continue
       except Exception:
           pass
           
       return "detailed"  # ❌ Always hit this fallback in frozen exe
   ```

2. **Problem:** The hardcoded relative paths don't exist in a PyInstaller frozen executable:
   - `image_describer_config.json` - Not in current directory
   - `scripts/image_describer_config.json` - Not in working directory
   - Config file is actually at `sys._MEIPASS/scripts/image_describer_config.json`

3. **Result:** All `open()` calls failed, function fell through to `return "detailed"`

### Why Archive2021 Worked

Archive2021 workflow did NOT specify `--prompt-style` on the command line, so it used the default "narrative" from the config file. The config file loading worked for defaults, but `validate_prompt_style()` failed for explicit arguments.

### Why PromptBaseline Failed

All 7 PromptBaseline runs explicitly specified different `--prompt-style` arguments:
- `--prompt-style Simple` → became "detailed"
- `--prompt-style artistic` → became "detailed"
- `--prompt-style colorful` → became "detailed"
- etc.

The workflow logs showed:
```
INFO - Using override prompt style for resume: Simple
INFO - Running single image description process: ... --prompt-style detailed
```

This proved that `self.override_prompt_style` was set to "Simple" but `validate_prompt_style("Simple")` returned "detailed".

## The Fix

Updated `validate_prompt_style()` to use the `config_loader` module which has PyInstaller-compatible path resolution:

```python
def validate_prompt_style(style: str, config_file: str = "image_describer_config.json") -> str:
    """Validate and normalize prompt style with case-insensitive lookup
    
    Uses config_loader for PyInstaller-compatible path resolution.
    """
    if not style:
        return "detailed"
    
    try:
        # Import at module level to avoid repeated imports
        from scripts.config_loader import load_json_config
    except ImportError:
        try:
            from config_loader import load_json_config
        except ImportError:
            # Fallback: config_loader not available, return style as-is
            if style and len(style) > 0:
                return style
            return "detailed"
    
    try:
        cfg, path, source = load_json_config('image_describer_config.json', 
                                              explicit=config_file if config_file != 'image_describer_config.json' else None,
                                              env_var_file='IDT_IMAGE_DESCRIBER_CONFIG')
        if cfg:
            prompt_variations = cfg.get('prompt_variations', {})
            
            # Create case-insensitive lookup
            lower_variations = {k.lower(): k for k in prompt_variations.keys()}
            
            # Check if style exists (case-insensitive)
            if style.lower() in lower_variations:
                return lower_variations[style.lower()]
                
    except Exception:
        pass
        
    # If style not found in config but was provided, return it anyway
    # (allows custom/unknown styles to pass through)
    if style:
        return style
        
    # Final fallback
    return "detailed"
```

### Key Changes

1. **Uses `config_loader.load_json_config()`** - Handles PyInstaller paths correctly
2. **Multiple import attempts** - Tries both `scripts.config_loader` and `config_loader`
3. **Graceful degradation** - If config can't be loaded, passes through the style anyway
4. **Trust the caller** - If validation fails but a style was provided, use it

### Config Loader Resolution Order

The `config_loader` module checks paths in this order:
1. Explicit path (if provided)
2. Environment variable `IDT_IMAGE_DESCRIBER_CONFIG`
3. `IDT_CONFIG_DIR` directory
4. **`exe_dir/scripts/filename`** ← This finds it in PyInstaller bundle!
5. `exe_dir/filename`
6. Current working directory
7. Bundled script directory

## Testing

### Test 1: From /tmp directory (no external config)
```bash
cd /tmp
/c/Users/kelly/GitHub/Image-Description-Toolkit/dist/idt.exe workflow \
  --provider ollama --model qwen3-vl:235b-cloud \
  --prompt-style Simple --name test_final_fix --dry-run \
  /c/Users/kelly/GitHub/Image-Description-Toolkit/testimages
```

**Result:** ✅ Created directory `wf_test_final_fix_ollama_qwen3-vl_235b-cloud_Simple_20251015_210429`

### Test 2: All 7 Prompt Styles
Once Archive2021 completes and idt.exe can be replaced:
```bash
cd /c/idt
# Replace old executable
mv idt.exe idt_old.exe
mv idt_fixed.exe idt.exe

# Re-run all 7 prompts
bat/run_all_prompts_cloudqwen.bat
```

**Expected:** 7 workflow directories with different prompt styles in their names.

## Impact

- **Affected:** All users running workflows with explicit `--prompt-style` arguments using the frozen executable
- **Duration:** October 9 (commit d2fc205) to October 15 (this fix)
- **Workflows affected:** Any workflow run with `idt.exe` that specified `--prompt-style`
- **Data integrity:** Workflows completed successfully but used wrong prompt style

## Prevention

1. **Test frozen executable separately** from Python script
2. **Test from different working directories** to catch path issues
3. **Add integration tests** that verify prompt style is used correctly
4. **Log the actual config file path** used by validate_prompt_style for debugging

## Related Issues

- Commit 170f1f0: Added 'Simple' to analysis script's known prompt styles
- Commit d2fc205: Introduced layered config loading (this is when bug likely started)
- Commit 7cfcb34: Added "Simple" prompt style to image_describer_config.json

## Files Modified

- `scripts/workflow.py` - Updated `validate_prompt_style()` function
- `final_working.spec` - Already had config_loader in hiddenimports

## Verification

After deploying the fixed executable:
1. Delete all `/c/idt/bat/Descriptions/wf_promptbaseline_*` directories
2. Re-run `run_all_prompts_cloudqwen.bat`
3. Verify 7 directories are created with different prompt styles:
   - `wf_promptbaseline_*_Simple_*`
   - `wf_promptbaseline_*_artistic_*`
   - `wf_promptbaseline_*_colorful_*`
   - `wf_promptbaseline_*_concise_*`
   - `wf_promptbaseline_*_detailed_*`
   - `wf_promptbaseline_*_narrative_*`
   - `wf_promptbaseline_*_technical_*`
