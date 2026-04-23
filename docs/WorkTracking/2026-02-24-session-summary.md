# Session Summary — 2026-02-24

## Overview

This session resolved two bugs:
1. `'NoneType' object has no attribute 'get'` crash on workspace open
2. OpenAI provider failing with "SDK not installed / API expired" error despite a valid key configured via Configure Settings

The root cause of bug 2 was a config loading path mismatch in the frozen exe — the main window was reading from the read-only bundled template instead of the user's AppData config where the API key was saved.

---

## Completed Work

### 1. Workspace Open NoneType Crash ✅
**File**: `imagedescriber/imagedescriber_wx.py` (line ~1309)  
**Root cause**: `video_metadata` is `Optional[dict]` initialized to `None`. `hasattr()` always returns `True` (the attribute exists). Calling `.get()` on `None` throws `AttributeError`.  
**Fix**: Added `and image_item.video_metadata` null guard alongside the existing `hasattr()` check.  
**Behavior before fix**: Error dialog appeared on every workspace open when first image was a video; workspace still loaded after dismissal.

**Commit**: `ab0ac90` "Support explicit API keys and safer provider lookup"

---

### 2. OpenAI "SDK not installed / API expired" Error ✅
**Root cause (primary)**: `wx_common.find_config_file()` in a PyInstaller onefile frozen build returns `_MEIPASS/scripts/image_describer_config.json` (bundled read-only template, no API keys). The configure dialog saves API keys to `%APPDATA%\IDT\image_describer_config.json`, but the main window's `load_config()` was calling `find_config_file()` which finds `_MEIPASS/scripts/` first — AppData is never checked.

**Config loading search order comparison**:
| Function | Searches AppData? | Finds first |
|---|---|---|
| `wx_common.find_config_file()` | ❌ No | `_MEIPASS/scripts/` (bundled, no keys) |
| `config_loader.load_json_config()` | ✅ Yes (step 6) | AppData (user's keys) |

**Root cause (secondary)**: Provider singletons (`_openai_provider = OpenAIProvider()`) are created at module import time. If no key is found then, `is_available()` returns `False` permanently. The worker uses `get_available_providers()` which filters by `is_available()`, so the provider is silently excluded.

**Fixes applied in `imagedescriber/imagedescriber_wx.py`**:
- `load_config()`: Replaced `find_config_file()` + manual `json.load()` with `config_loader.load_json_config('image_describer_config.json')` which correctly finds AppData before `_MEIPASS`. Added `self.config_file = None` fallback in exception branch.
- `prompt_config_path` (two locations — resume processing and video frame batch): Replaced `find_config_file('image_describer_config.json')` with `self.config_file` (already correctly resolved by `load_config()` at startup). Removes redundant re-resolution and ensures custom prompts saved to AppData are found.
- Removed `find_config_file` from the top-level wx_common import block (no longer used).

**Fixes applied in `imagedescriber/workers_wx.py`** (committed as `ab0ac90`):
- `_process_with_ai()`: Changed to use `get_all_providers()` (includes unavailable providers) for lookup, then inject key via `provider.reload_api_key(explicit_key=api_key)`. Previously used `get_available_providers()` which excluded keyless providers.

**Fixes applied in `imagedescriber/ai_providers.py`** (committed as `ab0ac90`):
- `OpenAIProvider.reload_api_key(self, explicit_key=None)`: When `explicit_key` is provided, use it directly without re-reading the config (prevents a keyless config from overwriting the injected key).
- `ClaudeProvider.reload_api_key(self, explicit_key=None)`: Same fix.

---

## Files Modified

| File | Change |
|------|--------|
| `imagedescriber/imagedescriber_wx.py` | NoneType null guard (committed); `load_config()` → use `config_loader.load_json_config()`; two `prompt_config_path` references use `self.config_file`; removed `find_config_file` import |
| `imagedescriber/workers_wx.py` | `get_all_providers()` lookup + `explicit_key` injection (committed `ab0ac90`) |
| `imagedescriber/ai_providers.py` | `explicit_key=None` on both `reload_api_key()` methods (committed `ab0ac90`) |

---

## Technical Notes

### Why `wx_common.find_config_file()` was wrong for frozen builds
In a PyInstaller onefile build, `_MEIPASS/scripts/` always exists (it's where bundled data files are extracted). `wx_common.find_scripts_directory()` returns `_MEIPASS/scripts/` before checking AppData because it scans `[exe_dir/scripts, exe_dir.parent/scripts, _MEIPASS/scripts]` in order. Since `_MEIPASS/scripts/` always exists, `find_config_file()` always finds the bundled copy — the user's AppData config is never reached.

`config_loader.resolve_config()` follows: `[IDT_CONFIG_DIR, file_env_var, exe_dir/scripts, exe_dir, AppData, _MEIPASS/scripts, cwd, script_dir]`. AppData comes **before** `_MEIPASS`, so user-configured settings (including API keys) take priority.

### Configure dialog path is correct
`configure_dialog.find_scripts_directory()` in frozen mode correctly uses `get_user_config_dir()` → AppData. It seeds AppData on first run by copying bundled JSON defaults (without overwriting existing user copies). This was working — the issue was only on the read side in the main window.

### Provider cache consideration
`ProcessingWorker._provider_cache` is keyed by `f"{provider}_{model}_{api_key or ''}"`. The explicit-key injection fix ensures the api_key from AppData (non-empty string) is used as the cache key, so the keyless provider singleton from import time is not reused.

---

## Testing Status

**Build verification**: NOT YET — user is building a new version. Today's `load_config()` fixes are uncommitted; prior fixes (`ab0ac90`) are in the build being tested.

**Runtime testing**: NOT YET — pending user build + test.

**What was NOT tested** (requires frozen exe build):
- `load_config()` reading from AppData in production exe
- End-to-end OpenAI description flow in frozen exe
- Verify `self.config_file` is a valid Path in `prompt_config_path` contexts

**Dev-mode verification**: `config_loader.load_json_config()` round-trip confirmed working; API key injection (`explicit_key`) confirmed working with direct `OpenAIProvider` test.
