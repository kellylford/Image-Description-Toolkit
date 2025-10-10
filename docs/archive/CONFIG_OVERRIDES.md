# Configuration Overrides & Prompt Styles

This toolkit supports layered configuration so you can change prompt styles, defaults,
and model settings **without rebuilding the executable**.

## Why This Matters

When you distribute the PyInstaller-built `ImageDescriptionToolkit.exe`, all JSON
configs are frozen inside. Previously, changing a prompt or default required a
rebuild. Now you can drop an external config file and it will override the bundled
one automatically.

## Supported Config (Current Scope)

| File | Purpose |
|------|---------|
| `image_describer_config.json` | Prompt styles, default prompt style, model defaults |

Workflow and other configs may be layered later using the same mechanism.

### Relationship to Distribution Package

The distribution ZIP (created by `create_distribution.bat`) already ships editable
copies of the JSON files under `scripts/`. Those shipped files naturally sit in
layer positions (4) and (5) of the resolution order below when placed next to
the executable. That means in a standard extracted package:

```
Deployment/
  ImageDescriptionToolkit.exe
  scripts/
    image_describer_config.json   <-- This is layer (5) "exe scripts" and will be used
```

If you ALSO drop a copy directly beside the EXE (without the `scripts/` folder):

```
Deployment/
  ImageDescriptionToolkit.exe
  image_describer_config.json     <-- This outranks scripts/ version (layer 4 vs 5)
  scripts/image_describer_config.json
```

Only one will be used (first in precedence). This lets you ship a stable baseline
inside `scripts/` while providing a higher-priority override for quick hotfixes.

## Resolution Order (First Existing File Wins)

For `image_describer_config.json`:

1. Explicit path passed to `image_describer.py` via `--config path.json`
2. Direct file env var: `IDT_IMAGE_DESCRIBER_CONFIG=C:\path\custom.json`
3. Directory env var: `IDT_CONFIG_DIR=C:\configs` (expects file inside)
4. Frozen exe directory: `ImageDescriptionToolkit\image_describer_config.json`
5. Frozen exe `scripts` subdirectory: `ImageDescriptionToolkit\scripts\image_describer_config.json`
6. Current working directory
7. Bundled copy inside the executable (fallback)

The first matching file short‑circuits the search.

## Prompt Style Precedence

1. `--prompt-style <name>` flag (per run)
2. `default_prompt_style` inside the resolved config file
3. Fallback hardcoded default (`detailed` if config missing or invalid)

Case is normalized—`Artistic`, `artistic`, `ARTISTIC` all match.

## Minimal Example

```jsonc
// custom_image_describer_config.json
{
  "model_settings": { "model": "llava:7b", "temperature": 0.2 },
  "default_prompt_style": "narrative",
  "prompt_variations": {
    "narrative": "Provide a factual narrative describing objects, colors, and composition.",
    "artistic": "Describe artistic elements: composition, palette, mood, style.",
    "technical": "Give camera/lighting/composition technical analysis.",
    "color_focus": "Emphasize color relationships, light quality, and atmosphere."
  }
}
```

Place it next to the EXE as `image_describer_config.json` or set:

```powershell
set IDT_IMAGE_DESCRIBER_CONFIG=C:\deploy\custom_image_describer_config.json
```

Then run:

```powershell
ImageDescriptionToolkit.exe workflow C:\images
```

Descriptions will use `narrative` unless you override with `--prompt-style`.

## Verifying the Override Worked

1. Run without `--prompt-style`.
2. Open `workflow_output_*/descriptions/image_descriptions.txt`.
3. Confirm header line: `Prompt style: narrative` (or your custom default).
4. Re-run with `--prompt-style artistic` to confirm per-run override.

## Environment Variable Tips

| Variable | Example | Effect |
|----------|---------|--------|
| `IDT_IMAGE_DESCRIBER_CONFIG` | `C:\cfg\special.json` | Directly use that file |
| `IDT_CONFIG_DIR` | `D:\shared_configs` | Use `D:\shared_configs\image_describer_config.json` if present |

You can combine: direct file var wins over directory var.

## Distribution Pattern

Recommended tree for shipping updates without rebuilds:

```
dist/Deployment/
  ImageDescriptionToolkit.exe
  image_describer_config.json         # Editable by ops/content team
  README_RUNTIME.txt                  # Short how-to for end users
  configs/ (optional future expansion)
```

## Failure & Fallback Behavior

| Situation | Outcome |
|-----------|---------|
| Missing external file | Bundled config used silently |
| Invalid JSON (parse error) | Falls back to bundled; style becomes bundled default |
| `default_prompt_style` not in `prompt_variations` | Warns (source run) and falls back to first valid style or `detailed` |

## Future Extensions (Planned)

* Layered overrides for `workflow_config.json` and `video_frame_extractor_config.json`.
* Logging of resolved config path at INFO level (currently implicit—can be enabled if desired).
* Signed config bundles for locked-down enterprise deployments.

---
Need something else? Open an issue or discussion with the tag `config-override`.
