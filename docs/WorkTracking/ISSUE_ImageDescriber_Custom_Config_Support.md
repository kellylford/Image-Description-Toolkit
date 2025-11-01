# GitHub Issue: ImageDescriber GUI Needs Custom Config File Support

## Summary

The ImageDescriber GUI app currently cannot use custom `image_describer_config.json` files that users create for custom prompts. It only loads from hardcoded paths, unlike the CLI tools which use `config_loader.py` for flexible resolution.

## Current Behavior

### What Works (CLI)
```bash
# CLI workflow with custom config
idt workflow photos --config-id scripts/kelly.json --prompt-style orientation

# Environment variable support
set IDT_IMAGE_DESCRIBER_CONFIG=C:\my_prompts.json
python scripts/image_describer.py photos
```

### What Doesn't Work (GUI)
- ❌ No command-line argument support (`imagedescriber.exe --config my_prompts.json`)
- ❌ No environment variable support (`IDT_IMAGE_DESCRIBER_CONFIG`)
- ❌ No GUI file picker to select custom config
- ❌ Doesn't use `config_loader.py` for layered resolution

### Current GUI Config Loading Logic

The GUI has **hardcoded path checks** in three places:

1. **Main app** (`imagedescriber/imagedescriber.py` ~line 2419):
   - Checks: `<exe_dir>/../scripts/image_describer_config.json`
   - Fallback: `<_MEIPASS>/scripts/image_describer_config.json` (bundled)

2. **Processing dialog** (`imagedescriber/imagedescriber.py` ~line 693):
   - Same hardcoded logic

3. **Worker threads** (`imagedescriber/worker_threads.py` ~line 81):
   - Only checks bundled location (doesn't check external)

### Current Workaround
Users must place custom config at:
- `C:\idt\scripts\image_describer_config.json` (if exe is in `C:\idt\`)
- This overwrites/replaces the default config

## Problem

When users create custom prompt variations (like "orientation", "technical-detailed", etc.), they want to use them in **both**:
1. CLI workflows (`idt workflow` with `--config-id`) ✅ Works
2. GUI batch processing (ImageDescriber app) ❌ Doesn't work

This inconsistency forces users to either:
- Modify the default config file (loses original prompts)
- Manually copy custom config to the exe location
- Maintain multiple installations with different configs

## Proposed Solutions

### Option A: Environment Variable Support (Minimal)
- Replace hardcoded logic with `config_loader.py`
- Respects `IDT_IMAGE_DESCRIBER_CONFIG` env var
- Consistent with CLI behavior
- **Pros:** Simple, aligns with existing patterns
- **Cons:** Requires users to know about env vars

### Option B: GUI File Picker (User-Friendly)
- Add "File → Load Custom Config..." menu item
- Browse and select config file at runtime
- Save selection to preferences
- Show active config path in status bar
- **Pros:** Discoverable, visual feedback
- **Cons:** GUI changes required

### Option C: Both Environment Variable + File Picker
- Automatic detection via env vars
- Manual override via GUI picker
- Display which config is active
- **Pros:** Best of both worlds
- **Cons:** Most work

### Option D: Command-Line Argument (Recommended) ⭐
- Add `--config` command-line argument support
- Works for scripting and shortcuts
- Can be combined with environment variable support
- **Pros:** Easy to implement, scriptable, discoverable
- **Cons:** Requires launching from command line or shortcut

**Example usage:**
```bash
# Launch with custom config
imagedescriber.exe --config C:\my_custom_prompts.json
imagedescriber.exe --config scripts\kelly.json

# Create desktop shortcut with custom config
Target: C:\idt\imagedescriber.exe --config C:\work\project_prompts.json
```

## Technical Details

### Config Files Used by ImageDescriber GUI

| Operation | Config File Used | Notes |
|-----------|-----------------|-------|
| **Image Description** | `image_describer_config.json` | Contains prompts, AI settings, metadata/geocoding |
| **Video Extraction** | None (hardcoded in GUI) | GUI has built-in OpenCV extraction, doesn't use `video_frame_extractor_config.json` |
| **HEIC Conversion** | None | Uses `ConvertImage.py` |

**Key Finding:** GUI only needs `image_describer_config.json` for custom prompts. It doesn't use `video_frame_extractor_config.json` at all (has its own extraction code).

### Implementation Sketch for Option D

**Current main() entry point:**
```python
def main():
    app = QApplication(sys.argv)
    window = ImageDescriberGUI()
    window.show()
    return app.exec()
```

**Proposed with --config support:**
```python
def main():
    import argparse
    parser = argparse.ArgumentParser(description="ImageDescriber - AI Image Description GUI")
    parser.add_argument('--config', type=str, help='Path to custom image_describer_config.json')
    args, unknown = parser.parse_known_args()  # Let Qt handle unknown args
    
    app = QApplication(sys.argv)
    window = ImageDescriberGUI(config_file=args.config)  # Pass to constructor
    window.show()
    return app.exec()
```

**Files to update:**
1. `imagedescriber/imagedescriber.py`:
   - Update `main()` to parse `--config` argument
   - Update `ImageDescriberGUI.__init__()` to accept `config_file` parameter
   - Update `load_config()` to use `config_loader.py` (lines ~2419-2427)
   - Update `ProcessingDialog.load_prompt_config()` (lines ~693-701)

2. `imagedescriber/worker_threads.py`:
   - Update `ProcessingWorker.load_prompt_config()` (lines ~81-83)
   - Pass config path from dialog to worker

3. Optional: Add "Help → Show Active Config" menu item to display which config is loaded

### Layered Resolution (if using config_loader.py)

Priority order (first found wins):
1. `--config` command-line argument (explicit)
2. `IDT_IMAGE_DESCRIBER_CONFIG` environment variable
3. `IDT_CONFIG_DIR/image_describer_config.json`
4. `<exe_dir>/scripts/image_describer_config.json` (external)
5. `<exe_dir>/image_describer_config.json`
6. Current working directory
7. Bundled `scripts/image_describer_config.json` (fallback)

## User Impact

**Who benefits:**
- Users with custom prompt variations for different projects
- Power users managing multiple workflow configurations
- Teams sharing standardized prompt templates
- Users switching between different AI providers with provider-specific prompts

**Use cases:**
```bash
# Project-specific prompts
imagedescriber.exe --config C:\work\project_A\prompts.json

# Client-specific configurations
imagedescriber.exe --config \\server\templates\client_prompts.json

# Desktop shortcuts for different tasks
"Artistic Analysis" → imagedescriber.exe --config artistic.json
"Technical Review" → imagedescriber.exe --config technical.json
```

## Related Context

- **Feature branch:** `feature/explicit-config-arguments` (currently implementing `--config-workflow`, `--config-id`, etc. for CLI)
- **Recent changes:** CLI now supports explicit config arguments; GUI should follow same pattern
- **Config loader:** `scripts/config_loader.py` provides layered resolution already used by CLI
- **Consistency goal:** All IDT apps should support custom configs uniformly

## Recommendation

**Implement Option D (command-line argument) first**, optionally combined with Option A (environment variable via config_loader.py). This provides:
- Immediate solution for power users
- Consistency with CLI behavior
- Foundation for future GUI file picker (Option B)
- Minimal code changes
- Easy testing and validation

Option B (GUI file picker) can be added later as a quality-of-life enhancement without changing the underlying mechanism.

## Labels
- `enhancement`
- `gui`
- `imagedescriber`
- `config-system`
- `user-experience`

## Priority
Medium - Workaround exists (place config at exe location), but inconsistent with CLI behavior and reduces flexibility for power users.
