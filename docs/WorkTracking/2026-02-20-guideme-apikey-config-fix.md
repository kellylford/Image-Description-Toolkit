# Session Summary: API Key Management Improvements

**Date:** 2026-02-20  
**Branch:** MacApp  
**Agent:** Claude Sonnet 4.5

## Overview

Comprehensive update to API key handling across the toolkit to properly support configuration file-based API keys, not just file-based keys. This allows users to configure API keys once via the ImageDescriber GUI and use them everywhere without command-line arguments.

## Issues Fixed

### 1. `idt guideme` Not Recognizing Configured API Keys

**Problem:**  
When running `idt guideme` with Claude or OpenAI already configured in `image_describer_config.json` (via Tools → Configure Settings), the wizard still prompted users to enter API key information manually. It only checked for `.txt` files, not configuration-stored keys.

**Root Cause:**  
The `setup_api_key()` function in [scripts/guided_workflow.py](../../scripts/guided_workflow.py) only checked for API key `.txt` files (e.g., `claude.txt`, `openai.txt`), but did not check the `api_keys` section of `image_describer_config.json`.

**Solution:**  
Added `check_api_key_in_config()` function that:
- Uses `load_json_config()` to find the config file (handles frozen exe path resolution)
- Checks `api_keys.Claude` / `api_keys.OpenAI` (with case variations)
- Returns `True` if a key exists in the config

Modified `setup_api_key()` to:
1. **First** check for API key in config file (highest priority)
2. If found, offer option: "Yes, use configured key" / "No, specify a different source"
3. If user selects "Yes", return special marker `"USE_CONFIG_KEY"`
4. Updated 3 locations where `api_key_file` is used to skip adding `--api-key-file` argument when value is `"USE_CONFIG_KEY"`

This allows the workflow/image_describer to load the API key from its normal config resolution path.

### 2. Deprecated Claude Model as Default

**Problem:**  
Multiple dialog components in ImageDescriber GUI were hardcoding `"claude-3-5-sonnet-20241022"` as the default Claude model selection. This model was deprecated by Anthropic and removed from `models/claude_models.py` in February 2026. When the code tried to `SetStringSelection()` to a model not in the list, it could:
- Not select anything (appearing blank)
- Cause unexpected behavior

**Root Cause:**  
Three files had hardcoded references to the deprecated model:
- [imagedescriber/dialogs_wx.py](../../imagedescriber/dialogs_wx.py) - Line 677 in `ProcessingOptionsDialog`
- [imagedescriber/chat_window_wx.py](../../imagedescriber/chat_window_wx.py) - Lines 178 and 198

**Solution:**  
Changed all default selections to use the **first model** from `DEV_CLAUDE_MODELS` list, which is ordered by recommendation (currently `claude-opus-4-6`). Used `SetSelection(0)` instead of `SetStringSelection()` to avoid dependency on specific model names.

**Files Modified:**
- [scripts/guided_workflow.py](../../scripts/guided_workflow.py) - Added API key config checking
- [scripts/image_describer.py](../../scripts/image_describer.py) - Allow config-based keys, updated error messages
- [scripts/workflow.py](../../scripts/workflow.py) - Updated help text and examples
- [imagedescriber/dialogs_wx.py](../../imagedescriber/dialogs_wx.py) - Fixed Claude default in ProcessingOptionsDialog
- [imagedescriber/chat_window_wx.py](../../imagedescriber/chat_window_wx.py) - Fixed Claude default in 2 locations
- [docs/CLI_REFERENCE.md](../../docs/CLI_REFERENCE.md) - Added comprehensive API key documentation

### 3. CLI Commands Required `--api-key-file` Even When Config Had API Key

**Problem:**  
Commands like `idt workflow` and direct calls to `image_describer.py` would exit with an error if `--api-key-file` was not provided, even though the user had configured an API key in `image_describer_config.json` via the ImageDescriber GUI.

**Root Cause:**  
In [scripts/image_describer.py](../../scripts/image_describer.py) lines 2258-2270, the script would:
1. Check for `--api-key-file` argument
2. Check for environment variable (OPENAI_API_KEY / ANTHROPIC_API_KEY)
3. **Exit with error** if neither found

This happened BEFORE the provider was initialized. The provider constructors already had logic to check config files, but they never got a chance to run.

**Solution:**  
1. **Removed early exit** - Let the script continue even without `--api-key-file` or env var
2. **Changed provider initialization** - Pass `api_key=None` and let provider check config/files
3. **Improved error messages** - Now show all 4 methods to provide API key:
   ```
   OpenAI provider requires an API key. Provide via:
     1. Config file: image_describer_config.json → api_keys.OpenAI
     2. Command line: --api-key-file /path/to/openai.txt
     3. Environment: export OPENAI_API_KEY=sk-...
     4. Text file: openai.txt in current directory
   ```
4. **Updated help text** - Both `--api-key-file` arguments now mention config as alternative
5. **Updated examples** - Show both explicit `--api-key-file` and config-based usage

**Files Modified:**
- [scripts/guided_workflow.py](../../scripts/guided_workflow.py) - Added API key config checking
- [scripts/image_describer.py](../../scripts/image_describer.py) - Removed early exit, improved messages
- [scripts/workflow.py](../../scripts/workflow.py) - Updated help text and examples  
- [docs/CLI_REFERENCE.md](../../docs/CLI_REFERENCE.md) - Added comprehensive API key documentation
- [imagedescriber/dialogs_wx.py](../../imagedescriber/dialogs_wx.py) - Fixed Claude default in ProcessingOptionsDialog
- [imagedescriber/chat_window_wx.py](../../imagedescriber/chat_window_wx.py) - Fixed Claude default in 2 locations

## Technical Details

### Complete API Key Resolution Order

**For all commands** (`idt workflow`, `idt guideme`, direct `image_describer.py` calls):

1. ✅ **Command-line file** (`--api-key-file /path/to/key.txt`) - Highest priority when specified
2. ✅ **Environment variable** (`OPENAI_API_KEY` / `ANTHROPIC_API_KEY`)
3. ✅ **Config file** (`image_describer_config.json` → `api_keys.OpenAI` / `api_keys.Claude`)
4. ✅ **Text file in CWD** (`openai.txt` / `claude.txt` in current directory) - Lowest priority

**Key changes:**
- **Before:** Commands would exit if #1 or #2 not found, never checking #3 or #4
- **After:** Commands pass `api_key=None` to provider, which checks all 4 sources

This matches the provider's built-in resolution logic:
```python
self.api_key = (
    api_key or                          # 1. Explicit parameter (from --api-key-file or env)
    self._load_api_key_from_config() or # 2. Config file (NOW WORKS IN CLI!)
    os.getenv('ANTHROPIC_API_KEY') or   # 3. Environment variable (redundant but safe)
    self._load_api_key_from_file()      # 4. Text file in CWD
)
```

### `idt guideme` Wizard Flow

For `idt guideme` with Claude/OpenAI, the wizard now prompts:
1. ✅ **"Found API key in config"** → Use it? (NEW!)
2. ✅ **"Found API key file"** → Use it?
3. ✅ **Prompt for new key** → Save to file or specify path

When user selects "Use configured key", returns `"USE_CONFIG_KEY"` marker so workflow command doesn't add `--api-key-file` argument.

### Claude Model Defaults

**Before:**
```python
self.model_combo.SetStringSelection("claude-3-5-sonnet-20241022")  # ❌ Deprecated
```

**After:**
```python
if self.model_combo.GetCount() > 0:
    self.model_combo.SetSelection(0)  # ✅ First model (claude-opus-4-6)
```

The `DEV_CLAUDE_MODELS` list (from `models/claude_models.py`) is maintained in recommendation order:
1. `claude-opus-4-6` - Most intelligent (RECOMMENDED)
2. `claude-sonnet-4-5-20250929` - Best balance
3. `claude-haiku-4-5-20251001` - Fastest
4. _(legacy models)_

## Testing Recommendations

**Before declaring complete**, test the following scenarios:

### CLI Testing (`idt guideme`)
```bash
# Prerequisites: Configure API key via ImageDescriber
1. Launch ImageDescriber.exe
2. Tools → Configure Settings → API Keys tab
3. Enter Claude API key, save & close

# Test guideme recognition
cd c:\idt
idt.exe guideme
# Select "claude" as provider
# VERIFY: Shows "✓ Found API key for CLAUDE in configuration: C:\idt\image_describer_config.json"
# VERIFY: Offers option "Yes, use configured key"
# Select "Yes, use configured key"
# VERIFY: Workflow command does NOT include --api-key-file argument
# VERIFY: Workflow runs successfully using config key
```

### GUI Testing (ImageDescriber)
```bash
# Test ProcessingOptionsDialog
1. Launch ImageDescriber.exe
2. Load images
3. Click "Process Images"
4. In dialog, select "Claude" provider
5. VERIFY: Model dropdown shows "claude-opus-4-6" as first item
6. VERIFY: "claude-opus-4-6" is auto-selected (not blank)
7. VERIFY: Can submit and process successfully

# Test Chat Window
1. Load image with description
2. Right-click → Ask Follow-up Question
3. Select "claude" provider
4. VERIFY: Model dropdown shows "claude-opus-4-6" as first item  
5. VERIFY: "claude-opus-4-6" is auto-selected (not blank)
```

### CLI Testing (Config-based API Keys - NEW)
```bash
# Prerequisites: Configure API key via ImageDescriber
1. Launch ImageDescriber.exe
2. Tools → Configure Settings → API Keys tab
3. Enter Claude API key, save & close

# Test workflow command WITHOUT --api-key-file
cd c:\idt
idt.exe workflow testimages --provider claude --model claude-opus-4-6
# VERIFY: Does NOT error about missing API key
# VERIFY: Workflow runs and completes successfully
# VERIFY: In logs, shows "Using API key from config file" or similar

# Test with OpenAI
idt.exe workflow testimages --provider openai --model gpt-4o-mini
# VERIFY: Works without --api-key-file argument

# Test explicit override still works
idt.exe workflow testimages --provider claude --api-key-file C:\other-key.txt
# VERIFY: Uses specified file, not config
```

### Frozen Executable Build Test
```bash
cd BuildAndRelease\WinBuilds
builditall_wx.bat
# VERIFY: All 3 apps build successfully
# Test dist\idt.exe guideme (per above)
# Test dist\ImageDescriber.exe (per above)
```

## Known Limitations

- **Blank model issue**: While we fixed the deprecated model default, if users still see a blank first item in the Claude model list, it may indicate:
  - Import failure of `DEV_CLAUDE_MODELS` in frozen executable (check PyInstaller `hiddenimports`)
  - Config file at `C:\idt\image_describer_config.json` has corrupted/empty model list
  - wxPython `wx.Choice` widget initialization issue (rare)

  To debug: Add logging to `dialogs_wx.py` line 674:
  ```python
  print(f"DEBUG: DEV_CLAUDE_MODELS = {DEV_CLAUDE_MODELS}")
  print(f"DEBUG: Model combo count after populate = {self.model_combo.GetCount()}")
  ```

## Related Files

**Modified:**
- [scripts/guided_workflow.py](../../scripts/guided_workflow.py) - Added `check_api_key_in_config()`, updated wizard prompts
- [scripts/image_describer.py](../../scripts/image_describer.py) - Removed early exit, updated error messages/help
- [scripts/workflow.py](../../scripts/workflow.py) - Updated help text and examples
- [scripts/config_loader.py](../../scripts/config_loader.py) - Used for config file resolution
- [imagedescriber/ai_providers.py](../../imagedescriber/ai_providers.py) - AI provider abstraction with config loading
- [imagedescriber/dialogs_wx.py](../../imagedescriber/dialogs_wx.py) - Fixed ProcessingOptionsDialog Claude default
- [imagedescriber/chat_window_wx.py](../../imagedescriber/chat_window_wx.py) - Fixed chat window Claude defaults
- [models/claude_models.py](../../models/claude_models.py) - Single source of truth for Claude models (reference)
- [docs/CLI_REFERENCE.md](../../docs/CLI_REFERENCE.md) - Added comprehensive API key documentation

**Documentation Updates:**
- Added "API Keys" section with 4-tier resolution priority
- Added examples showing config-based usage (without `--api-key-file`)
- Updated all cloud provider examples to show both methods
- Added tip about configuring keys once via GUI

## Accessibility Notes

All changes maintain WCAG 2.2 AA compliance:
- No changes to focus management
- No changes to keyboard navigation  
- Model selection still single-tab-stop `wx.Choice` widget (not multi-column list)
