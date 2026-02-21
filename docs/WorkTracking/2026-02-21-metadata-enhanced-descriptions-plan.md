# Plan: Metadata-Enhanced AI Descriptions

**Status:** Planning / Approved for Implementation  
**Date:** 2026-02-21  
**GitHub Issue:** TBD (filed as part of this document)

---

## Summary

Currently, IDT sends only the prompt text to each AI provider; EXIF metadata (date, location) is extracted but only appended to the *output* text file after the AI call. This misses a significant quality opportunity.

**The experiment** (Hawaii waterfall, Claude Opus 4.6, Feb 21 2026):
- Without metadata: good color description, no geographic context
- With `"Context: This photo was taken on October 4, 2004 with a Sony Cybershot in Hawaii."` appended to the prompt:
  - Correctly identified **volcanic basalt**, **Hawaiian windward climate**
  - Named **Road to Hana** style geography
  - Noticed a **human figure** for scale (missed without context)
  - Token cost: +83 prompt tokens (~$0.0003 at Sonnet pricing) → meaningfully richer output

This plan adds an opt-in setting (`enhance_descriptions`) that injects a structured metadata context block into the prompt before the AI call, for **all chat-based providers** (Ollama, OpenAI, Claude). HuggingFace/Florence-2 is task-token-based and cannot use free-text context — it is explicitly skipped.

---

## What Already Exists (Do Not Duplicate)

| Feature | Where | What it does |
|---|---|---|
| `include_location_prefix` | `image_describer.py:1117`, config `metadata.include_location_prefix` | Prepends `"City, ST Date: "` to **output text** after AI call — does NOT affect what the AI sees |
| Full EXIF extraction | `scripts/metadata_extractor.py` → `extract_metadata()` | Already extracts date, GPS, camera, altitude |
| GPS reverse geocoding | `scripts/metadata_extractor.py` → `NominatimGeocoder` | Already produces city/state/country from lat/lon |
| Geocoding cache | `geocode_cache.json` | Already rate-limited and cached |
| `--no-geocode` CLI flag | `scripts/workflow.py` argparse | Already lets users disable geocoding |

The new feature is specifically about **injecting metadata into the prompt** before the API call — a fundamentally different code path from all of the above.

---

## Provider Applicability

| Provider | Benefits from context? | Notes |
|---|---|---|
| **Ollama** (llava, minicpm-v, moondream, bakllava) | ✅ YES | Sent as user message text; all local vision models accept free-text context |
| **OpenAI** GPT-4o / GPT-4-vision | ✅ YES | Excellent language understanding; location context most impactful here |
| **Claude** (all 9 supported models) | ✅ YES | Proven experimentally; all models tested working |
| **HuggingFace Florence-2** | ❌ SKIP | Task-token mapping (`<CAPTION>`, `<DETAILED_CAPTION>`) — free-text context is ignored or breaks task resolution. Must check provider type and skip. |

**Conclusion**: This feature benefits 3 of 4 providers and all cloud-based models. HuggingFace gets a graceful skip with a debug log message.

---

## New Config Keys

Add to `scripts/image_describer_config.json` under the `"metadata"` section:

```json
"metadata": {
    "enabled": true,
    "include_location_prefix": true,
    "enhance_descriptions": false,
    "context_fields": {
        "date": true,
        "location": true,
        "folder_hint": true
    },
    "geocoding": { ... }
}
```

| Key | Type | Default | Purpose |
|---|---|---|---|
| `metadata.enhance_descriptions` | bool | `false` | Master switch: inject context into AI prompt |
| `metadata.context_fields.date` | bool | `true` | Include photo date in context block |
| `metadata.context_fields.location` | bool | `true` | Include location (geocoded or folder hint) in context block |
| `metadata.context_fields.folder_hint` | bool | `true` | Use folder name as fallback location hint when no GPS |

**Default is `false`** — existing behavior unchanged for all users who don't opt in.

---

## Context Block Format

The context is appended to the end of the existing prompt text:

```
\n\nContext: This photo was taken on October 4, 2004 in Hawaii.
```

Or with more data:

```
\n\nContext: This photo was taken on September 9, 2025 in Madison, Wisconsin.
```

Folder hint only (no GPS):

```
\n\nContext: This photo was taken on June 15, 2023 in Grand Canyon National Park.
```
*(where folder is named `grand-canyon-national-park`)*

Date only (no location at all):

```
\n\nContext: This photo was taken on March 3, 2019.
```

If no date AND no location can be determined: **no context block is appended** — the prompt is sent unchanged.

---

## Folder Hint Logic

When GPS coordinates are absent (or geocoding is disabled), use the folder name as a location cue:

```python
def _get_folder_hint(image_path: Path) -> str | None:
    """
    Return a human-readable folder hint if the name looks like a place/event.
    Returns None for auto-generated names, date folders, and generic names.
    """
    name = image_path.parent.name
    skip_patterns = [
        r'^\d{4}',            # Year-based: 2024, 2024-03-15
        r'^wf_',              # IDT workflow outputs
        r'^input_',           # IDT temp folders
        r'^IMG',              # Camera roll: IMG_1234
        r'^DCIM',             # Camera roll folder
        r'^images?$',         # Generic
        r'^photos?$',         # Generic
        r'^pictures?$',       # Generic
        r'^temp_combined',    # IDT internal
    ]
    if any(re.match(p, name, re.IGNORECASE) for p in skip_patterns):
        return None
    # Clean up separators; title-case for readability
    readable = name.replace('_', ' ').replace('-', ' ').strip()
    if not readable or len(readable) < 3:
        return None
    return readable.title()
```

**Heuristic risk**: A folder named `Download` or `New Folder` could produce a bad hint. The skip list covers common auto-generated patterns. Folder hints are only used when GPS/geocoded data is absent — if the user has geocoding enabled and GPS data, the authoritative result is used instead.

---

## Implementation Touch Points

### 1. `scripts/image_describer.py` — Core change

**New method** (add near other metadata helpers):
```python
def build_metadata_context(self, metadata: dict, image_path: Path) -> str:
    """
    Build a natural-language context string from extracted metadata.
    Returns empty string if no useful context can be assembled.
    Only called when metadata.enhance_descriptions is True and provider
    supports free-text prompts (not HuggingFace/Florence-2).
    """
```

**Modified**: `get_image_description()` at line 777, after `prompt = self.get_prompt()`:
```python
prompt = self.get_prompt()

# Inject metadata context into prompt if enabled (not for task-based providers)
if (self.provider_name != 'huggingface'
        and self.config.get('metadata', {}).get('enhance_descriptions', False)
        and metadata):
    context = self.build_metadata_context(metadata, image_path)
    if context:
        prompt = prompt + context
        logger.debug(f"Prompt enhanced with metadata context ({len(context)} chars)")
```

The `metadata` dict is already extracted earlier in `get_image_description()` — no additional EXIF reading is needed.

### 2. `scripts/image_describer_config.json`

Add the two new keys (`enhance_descriptions`, `context_fields`) to the `"metadata"` section. Update the `"_comments"` section with documentation strings.

### 3. `imagedescriber/configure_dialog.py`

In the existing **Metadata** settings section, add:

- **Checkbox**: `[ ] Enhance AI descriptions with photo context (date and location)`
- **Help text**: `"Appends date and location from photo metadata to the AI prompt. Improves geographic and temporal specificity. Has no effect on local AI models that don't support context."`

The checkbox reads/writes `metadata.enhance_descriptions` in config via the existing config save/load pattern.

No additional `context_fields` sub-checkboxes needed in the initial release — keep the UI simple. Advanced users can edit the JSON config directly.

### 4. `scripts/workflow.py` — CLI flags

Add to argparse (following the pattern of `--no-geocode`):

```
--enhance-descriptions    Inject photo date/location context into AI prompts
                          (overrides metadata.enhance_descriptions in config)
--no-enhance-descriptions Disable prompt context injection
```

These get passed to the image describer config override system the same way `--no-geocode` and `--metadata`/`--no-metadata` work today.

### 5. `imagedescriber/dialogs_wx.py`

Check whether the workflow settings dialog exposes the metadata enhance flag; add it if missing (low priority — the configure dialog covers 90% of usage).

---

## New Method: `build_metadata_context()`

Full design:

```python
def build_metadata_context(self, metadata: dict, image_path: Path) -> str:
    context_fields = self.config.get('metadata', {}).get('context_fields', {})
    include_date = context_fields.get('date', True)
    include_location = context_fields.get('location', True)
    include_folder = context_fields.get('folder_hint', True)

    parts = []

    # --- Date ---
    if include_date:
        datetime_str = metadata.get('datetime_str') or metadata.get('date_short')
        if datetime_str:
            parts.append(f"taken on {datetime_str}")

    # --- Location ---
    location_str = None
    if include_location:
        loc = metadata.get('location', {}) if isinstance(metadata, dict) else {}
        city = loc.get('city', '').strip()
        state = loc.get('state', '').strip()
        country = loc.get('country', '').strip()

        if city and state:
            location_str = f"{city}, {state}"
        elif city and country:
            location_str = f"{city}, {country}"
        elif state and country:
            location_str = f"{state}, {country}"
        elif country:
            location_str = country
        elif city:
            location_str = city

        # Folder hint fallback
        if not location_str and include_folder:
            location_str = self._get_folder_hint(image_path)

        if location_str:
            parts.append(f"in {location_str}")

    if not parts:
        return ""

    return "\n\nContext: This photo was " + ", ".join(parts) + "."
```

---

## Testing Plan

### Unit Tests (new file: `pytest_tests/test_metadata_context.py`)

1. `test_context_full_geocoded()` — date + city + state → correct string
2. `test_context_date_only()` — no location data → date-only string
3. `test_context_folder_hint()` — no GPS, folder = "hawaii" → uses folder
4. `test_folder_hint_skipped_generic()` — folder = "images" → returns None
5. `test_folder_hint_skipped_date()` — folder = "2024-06-15" → returns None
6. `test_no_context_no_data()` — empty metadata → returns empty string
7. `test_huggingface_skipped()` — provider = huggingface → prompt unchanged
8. `test_disabled_by_default()` — `enhance_descriptions: false` → prompt unchanged

### Integration Test

Run `idt workflow testimages --provider claude --enhance-descriptions --api-key-file <keyfile>` and verify:
- Output description contains geographic/temporal language reflecting the metadata
- Token count in log shows higher prompt tokens than without flag
- Without flag, behavior is identical to current behavior

### Backward Compatibility

- Default `enhance_descriptions: false` → zero behavior change for all existing users
- Existing `include_location_prefix` (output prefix) is independent and continues to work

---

## Effort Estimate

| Component | Complexity | Notes |
|---|---|---|
| `build_metadata_context()` in image_describer.py | Low | ~50 lines; pure string building |
| `_get_folder_hint()` helper | Low | ~20 lines; regex skip list |
| Provider skip guard (HuggingFace) | Trivial | One `if` check |
| CLI flags in workflow.py argparse | Low | Follow existing `--no-geocode` pattern |
| Config JSON new keys | Trivial | 2 new keys + comments |
| configure_dialog.py checkbox | Low | Follow existing checkbox pattern |
| Unit tests | Medium | 8 test cases |
| Integration test | Low | Reuse test script pattern |

**Total estimate**: 1–2 focused sessions. No architectural changes required — this slots cleanly between the existing `get_prompt()` call and the provider `describe_image()` call.

---

## Open Questions / Future Extensions

- **System prompt**: Claude and OpenAI both support a `system=` parameter. A future enhancement could move stable context (camera owner, use case) to the system prompt and keep per-image metadata in the user message. Out of scope for this issue.
- **Camera info**: Deliberately excluded per user preference. Could be added as a `context_fields.camera` option later.
- **Manual location override**: A `--location "Maui, Hawaii"` CLI flag could let users supply context when EXIF is absent. Out of scope.
- **Batch API compatibility**: When Claude Batch API is implemented, the enhanced prompt (with metadata appended) must be serialized to each JSONL entry. The `build_metadata_context()` method should be called per-image at batch submission time, not once globally.
