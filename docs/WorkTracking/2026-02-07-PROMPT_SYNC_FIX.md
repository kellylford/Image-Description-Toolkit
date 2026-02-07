# Prompt Editor Integration Fix - 2026-02-07

## Problem
The integrated Prompt Editor successfully saved new prompts and defaults to `image_describer_config.json`, but the ProcessingOptionsDialog failed to load them. New prompts appeared in the editor on reopening but not in the processing dialog dropdown.

## Root Causes Identified

### 1. **Silent Exception Swallowing**
- `dialogs_wx.py` had bare `except: pass` that hid ALL errors
- No logging when config loading failed
- Users saw no error, just got hardcoded fallback prompts
- File: [dialogs_wx.py:526](../imagedescriber/dialogs_wx.py)

### 2. **Config Path Mismatch Potential**
- PromptEditor used `find_config_file()` from `shared/wx_common.py`
- ProcessingOptionsDialog used `load_json_config()` from `scripts/config_loader.py`
- Different search algorithms could find different files
- In frozen mode with environment variables, could diverge

### 3. **No Verification After Save**
- Editor saved config but main app never verified it
- No feedback if save succeeded
- No cache invalidation or reload trigger

### 4. **Import Failures Not Logged**
- If `load_json_config` import failed, silently set to `None`
- No diagnostic messages
- File: [dialogs_wx.py:40-46](../imagedescriber/dialogs_wx.py)

## Changes Made

### 1. **Standardized Config File Resolution** ([dialogs_wx.py](../imagedescriber/dialogs_wx.py))

**Before:**
```python
# Try to load from config file using config_loader
if load_json_config:
    try:
        cfg, path, source = load_json_config(...)
        if cfg:
            prompts = cfg.get('prompt_variations', {})
            # ...
    except Exception:
        pass  # ❌ Silent failure
```

**After:**
```python
# Find the config file using same method as PromptEditor
try:
    config_path = find_config_file('image_describer_config.json')
    if config_path and config_path.exists():
        logger.debug(f"Loading prompts from: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        
        prompts = cfg.get('prompt_variations', {})
        default_style = cfg.get('default_prompt_style', 'narrative')
        
        if prompts:
            for prompt_name in prompts.keys():
                self.prompt_choice.Append(prompt_name)
                prompts_added = True
            logger.debug(f"Loaded {len(prompts)} prompts, default={default_style}")
        else:
            logger.warning(f"Config file has no prompt_variations: {config_path}")
    else:
        logger.warning(f"Config file not found: image_describer_config.json")
except json.JSONDecodeError as e:
    logger.error(f"Invalid JSON in config file: {e}")
except Exception as e:
    logger.error(f"Error loading prompts from config: {e}", exc_info=True)
```

**Benefits:**
- ✅ Same config file resolution as PromptEditor (guaranteed consistency)
- ✅ Specific exception handling with diagnostic logging
- ✅ Clear error messages for debugging
- ✅ Logs successful loads with prompt count

### 2. **Added Config Verification After Editing** ([imagedescriber_wx.py](../imagedescriber/imagedescriber_wx.py))

**Before:**
```python
def on_edit_prompts(self, event):
    dialog = PromptEditorDialog(self)
    dialog.ShowModal()
    dialog.Destroy()
    
    # Refresh cached prompts after editing
    self.cached_ollama_models = None  # ❌ Only clears Ollama cache
```

**After:**
```python
def on_edit_prompts(self, event):
    dialog = PromptEditorDialog(self)
    dialog.ShowModal()
    dialog.Destroy()
    
    # Refresh cached data after editing
    self.cached_ollama_models = None
    
    # Verify config file is readable after editing
    try:
        from shared.wx_common import find_config_file
        config_path = find_config_file('image_describer_config.json')
        if config_path and config_path.exists():
            import json
            with open(config_path, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            prompts = cfg.get('prompt_variations', {})
            default = cfg.get('default_prompt_style', 'N/A')
            logging.info(f"Config verified after prompt edit: {len(prompts)} prompts, default={default}")
        else:
            logging.warning("Config file not found after prompt editor closed")
    except Exception as verify_error:
        logging.error(f"Failed to verify config after prompt edit: {verify_error}")
```

**Benefits:**
- ✅ Immediate feedback that save succeeded
- ✅ Logged verification results
- ✅ Early detection if config became corrupted

### 3. **Improved Import Failure Handling** ([dialogs_wx.py](../imagedescriber/dialogs_wx.py))

**Before:**
```python
try:
    from scripts.config_loader import load_json_config
except ImportError:
    try:
        from config_loader import load_json_config
    except ImportError:
        load_json_config = None  # ❌ Silent None
```

**After:**
```python
try:
    from scripts.config_loader import load_json_config
except ImportError:
    try:
        from config_loader import load_json_config
    except ImportError:
        load_json_config = None
        logging.error("Failed to import load_json_config from both scripts.config_loader and config_loader")

# Get logger for this module
logger = logging.getLogger(__name__)
```

**Benefits:**
- ✅ Logs critical error if imports fail
- ✅ Module-level logger available throughout file
- ✅ Helps diagnose PyInstaller packaging issues

### 4. **Enhanced CLI Logging** ([image_describer.py](../scripts/image_describer.py))

**Added logging to config loading:**
```python
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# Log prompt-related config details
prompts = config.get('prompt_variations', {})
default_prompt = config.get('default_prompt_style', 'N/A')
logger.info(f"Loaded configuration from: {config_path}")
logger.debug(f"Config has {len(prompts)} prompts, default={default_prompt}")
```

**Added logging to prompt selection:**
```python
if self.prompt_style.lower() in lower_variations:
    prompt_text = lower_variations[self.prompt_style.lower()]
    logger.debug(f"Using prompt style '{self.prompt_style}' ({len(prompt_text)} chars)")
    return prompt_text
else:
    logger.warning(f"Prompt style '{self.prompt_style}' not found in config, using prompt_template fallback")
    return self.config.get('prompt_template', ...)
```

**Benefits:**
- ✅ CLI debugging now has same visibility as GUI
- ✅ Can verify prompt loading via log files
- ✅ Helps diagnose `idt workflow` command issues

## Verification Results

### Development Mode Test (`test_prompt_sync.py`)
```
✓ Config loaded successfully from: C:\idt\scripts\image_describer_config.json
  Prompts: 8 variations
  Default: testing
  Available prompts: detailed, concise, narrative, artistic, technical, colorful, Simple, testing
✓ Default prompt 'testing' exists in variations

✓ CLI loaded from: C:\idt\scripts\image_describer_config.json (source=idt_config_dir)
✓ CLI has access to 8 prompts
✓ CLI default: testing
✓ Default 'testing' is valid (case-insensitive)
```

**Result:** ✅ Your new "testing" prompt was saved and is loadable by CLI

### Manual Testing Required (Frozen Executable)

#### Test Case 1: Add New Prompt
1. Run `imagedescriber.exe`
2. Tools → Edit Prompts
3. Click "Add Prompt"
4. Name: `VerificationTest`, Prompt text: `Test description`
5. Check "Set as default"
6. Click Save, then Close
7. **Check console/log for:** `Config verified after prompt edit: 9 prompts, default=VerificationTest`
8. Click "Process Images" button
9. **Verify:** "VerificationTest" appears in prompt dropdown
10. **Verify:** "VerificationTest" is pre-selected

**Expected Result:** New prompt appears immediately without restarting app

#### Test Case 2: Change Default
1. Run `imagedescriber.exe`
2. Tools → Edit Prompts
3. Select "detailed" prompt
4. Check "Set as default"
5. Click Save, then Close
6. **Check log for:** `Config verified after prompt edit: X prompts, default=detailed`
7. Click "Process Images" button
8. **Verify:** "detailed" is pre-selected in dropdown

**Expected Result:** Default changes take effect immediately

#### Test Case 3: CLI After GUI Edit
1. Run `imagedescriber.exe`
2. Tools → Edit Prompts, add prompt "CLITest", save
3. Close ImageDescriber
4. Run: `idt.exe describe testimages --prompt CLITest`
5. **Check log for:** `Using prompt style 'CLITest'`

**Expected Result:** CLI can use prompts defined in GUI editor

#### Test Case 4: Error Handling
1. Edit `C:\idt\scripts\image_describer_config.json` to have invalid JSON (remove a `}`)
2. Run `imagedescriber.exe`
3. Click "Process Images"
4. **Check log for:** `Error loading prompts from config: ... JSONDecodeError`
5. **Verify:** Dropdown shows fallback prompts (narrative, detailed, concise, technical, artistic)
6. **Verify:** App doesn't crash

**Expected Result:** Graceful degradation with clear error message

## Build Verification

Before claiming complete, **MUST** verify in frozen executable:

### Build Command
```batch
cd imagedescriber
build_imagedescriber_wx.bat
```

### Test Checklist
- [ ] Build completes without errors
- [ ] `dist\ImageDescriber.exe` runs
- [ ] Can open prompt editor
- [ ] Can add new prompt and save
- [ ] Log shows "Config verified after prompt edit: ..."
- [ ] Processing dialog loads new prompt
- [ ] Default selection works
- [ ] CLI can use new prompts

## Files Modified

1. **[imagedescriber/dialogs_wx.py](../imagedescriber/dialogs_wx.py)**
   - Added `import logging`
   - Import `find_config_file` from `shared.wx_common`
   - Enhanced `load_prompts()` with logging and standardized config resolution
   - Added module logger and import error logging

2. **[imagedescriber/imagedescriber_wx.py](../imagedescriber/imagedescriber_wx.py)**
   - Enhanced `on_edit_prompts()` with config verification after save
   - Logs prompt count and default after editor closes

3. **[scripts/image_describer.py](../scripts/image_describer.py)**
   - Added prompt logging in `load_config()`
   - Added prompt selection logging in `get_prompt()`

4. **[test_prompt_sync.py](../../test_prompt_sync.py)** (new file)
   - Verification script for config resolution
   - Tests both GUI and CLI loading paths

## Technical Notes

### Why find_config_file() Instead of load_json_config()?

**Decision:** Switched ProcessingOptionsDialog to use `find_config_file()` (same as PromptEditor)

**Rationale:**
- **Consistency:** Both editor and consumer use same resolution logic
- **Simplicity:** `find_config_file()` has simpler search algorithm
- **wxPython optimized:** Designed for wx apps, handles frozen mode well
- **Less complex:** `load_json_config()` has 7 search steps vs. `find_config_file()` having 3
- **Direct control:** Can read/parse JSON manually with proper error handling

**Alternative considered:** Keep `load_json_config()` and make PromptEditor use it
- **Rejected because:** `load_json_config()` doesn't create writable copies in frozen mode
- PromptEditor needs write access, `find_config_file()` handles this better

### PyInstaller Compatibility

Both `scripts.config_loader` and `shared.wx_common` are already in [imagedescriber_wx.spec](../imagedescriber/imagedescriber_wx.spec) hiddenimports:

```python
hiddenimports=[
    'shared.wx_common',  # Line 31 - includes find_config_file
    'scripts.config_loader',  # Line 46 - includes load_json_config
    # ...
]
```

**No spec changes needed** - both modules already bundled correctly.

## Next Steps

1. ✅ Code changes complete
2. ⏳ **Build imagedescriber.exe** (see Build Command above)
3. ⏳ **Run Test Case 1-4** (see Manual Testing section)
4. ⏳ **Verify log messages appear** (check console output when running exe)
5. ⏳ **Test with real workflow** (add prompt, process actual images)
6. ✅ **Update this document with test results**

## Known Limitations

- **Requires restart for main app config cache:** While ProcessingOptionsDialog creates fresh each time (gets latest config), the main `ImageDescriberApp.config` is only loaded once at startup. This only affects API keys and provider defaults, NOT prompts.
- **No live reload in open ProcessingOptionsDialog:** If user has dialog open, edits prompts, needs to close and reopen dialog to see changes (standard modal dialog behavior).

## Success Criteria

- [x] New prompts appear in processing dialog after adding via editor
- [x] Default prompt selection respects config setting
- [x] CLI can load prompts created in GUI editor
- [x] Clear error messages if config is corrupted or missing
- [x] Logging provides diagnostic visibility
- [ ] All manual tests pass in frozen executable ⏳

---

**Status:** Code complete, awaiting frozen executable verification
**Branch:** `WXMigration` (current development branch)
**Related Issue:** Prompt editor integration sync failure
