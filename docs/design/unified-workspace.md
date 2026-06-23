# Unified Workspace (`.idtw`) — Design Reference

**Status:** v4.5 — in development
**Audience:** developers working on `idt` (CLI) and ImageDescriber (GUI), plus advanced users who want to understand where their files live.

---

## 1. Why this exists

Before v4.5 the toolkit had **four** incompatible ways of storing work:

| Surface | Descriptions stored as | Files land in | Originals |
|---|---|---|---|
| Old CLI (`workflow.py`) | flat `image_descriptions.txt` | `Descriptions/wf_*/` in CWD | copied to `temp_combined_images/` |
| New CLI engine (`idt_core` projects) | per-image JSON sidecars | sibling `Name.idt/` next to images | referenced in place |
| GUI (`.idw`) | one monolithic `.idw` JSON | `~/Documents/.../Workspaces/` + `WorkspaceFiles/` | referenced in place |
| GUI↔CLI bridge | manual conversion | — | — |

A description made in the GUI and the same image described by the CLI landed in different places, in different formats, with no way for a user to know where anything was.

**v4.5 replaces all of this with one thing: the workspace bundle (`.idtw`).**

A workspace is a single, self-contained directory named by the user. It holds everything: copies of the images, their descriptions, chat sessions, and any derived files (video frames, HEIC conversions, web downloads). Both tools open and write the *same* bundle. The user's original files are never moved or modified.

### Design decision: self-contained, duplicating bundle

The bundle **copies images into itself**. This duplicates pixel data (a 2 GB photo folder produces a ~2 GB bundle), and that is an accepted trade-off for v4.5. The payoff is that a workspace is one movable, shareable, unambiguous thing — there is exactly one place a user's work lives, and "where are my descriptions?" has one answer: *in the workspace*.

> A future release may add a **reference mode** (link to originals instead of copying) for very large libraries. The format below reserves room for it (`storage: "copy" | "reference"` per item). It is not implemented in v4.5.

**Originals are never modified.** Copy in; never move, never write back to the source. Embedding descriptions into image metadata (`idt embed` / GUI Embed) operates on the bundle's copies, or on a separate export folder — never the user's originals unless they explicitly opt into in-place embed.

---

## 2. Bundle layout

```
MyTrip.idtw/                    <- the workspace. A directory. The user names it.
  manifest.json                 <- workspace-level metadata (see §3)
  images/                       <- copies of source images, collision-safe names
    beach.jpg
    sunset.jpg
    Day2__beach.jpg             <- renamed copy (collision with another beach.jpg)
  descriptions/                 <- one sidecar per image, keyed by bundle image name
    beach.jpg.json
    sunset.jpg.json
    Day2__beach.jpg.json
  chats/                        <- chat sessions not tied to a single image
    chat_1718900000000.json
  derived/                      <- generated artifacts
    frames/                     <- extracted video frames
      clip1/clip1_000123.jpg
    converted/                  <- HEIC->JPEG conversions used for AI
      IMG_4421.jpg
  logs/                         <- optional run logs
    2026-06-20_describe.log
```

Rules:

- **`images/` filenames are the workspace's internal keys.** A sidecar `descriptions/X.json` describes `images/X`. The original source path is recorded *inside* the sidecar (`source_path`) for provenance, but it is never the key.
- **Collision-safe naming.** When two source files share a name (`Day1/beach.jpg`, `Day2/beach.jpg`), the second is stored as `Day2__beach.jpg` (subfolder prefix, `/`→`__`). The mapping is recorded in the sidecar (`source_path`, `subfolder`).
- **Nothing is written outside the bundle** during normal operation. Exports (HTML gallery, CSV, embedded-copy folders) are written wherever the user asks, outside the bundle.
- The `.idtw` extension marks the directory as a workspace for both tools and the OS. Internally it is an ordinary folder — no zipping, so it stays inspectable and crash-safe.

---

## 3. `manifest.json` schema

```json
{
  "format": "idtw",
  "version": "1.0",
  "name": "MyTrip",
  "created": "2026-06-20T14:30:00Z",
  "modified": "2026-06-20T15:10:00Z",

  "sources": [
    { "path": "/Users/kelly/Pictures/Vacation", "recursive": true,  "added": "2026-06-20T14:30:00Z" },
    { "path": "/Users/kelly/Pictures/Trip2",    "recursive": false, "added": "2026-06-20T14:40:00Z" }
  ],

  "defaults": {
    "provider": "anthropic",
    "model": "claude-opus-4-6",
    "prompt_name": "detailed",
    "prompt_text": ""
  },

  "batch_state": null,

  "cached_ollama_models": null,

  "geocode_enabled": false
}
```

| Field | Purpose |
|---|---|
| `format` / `version` | Identify and version the bundle. `format` is always `"idtw"`. |
| `name` | Display name. Defaults to the directory stem. |
| `sources[]` | Provenance: which folders/URLs images came from, and whether the scan was recursive. Drives "Refresh from disk". |
| `defaults` | Default provider/model/prompt for new runs (replaces `idt_core` `ProjectConfig` and GUI config-per-workspace). |
| `batch_state` | Pause/resume state for an interrupted batch (provider, model, prompt, queue position, geocode flag). `null` when idle. |
| `cached_ollama_models` | GUI optimization: cached model list so the options dialog opens instantly. |
| `geocode_enabled` | Whether GPS→city/state geocoding is on for this workspace. |

The manifest is the union of `idt_core` `ProjectConfig` and the GUI `ImageWorkspace` top-level fields. Both tools read/write the same file.

---

## 4. Per-image sidecar schema (`descriptions/<imagename>.json`)

This is the **unified item schema** — a superset of `idt_core.image_item.ImageItem` and `imagedescriber.data_models.ImageItem`. Both tools map to and from it.

```json
{
  "image": "Day2__beach.jpg",
  "source_path": "/Users/kelly/Pictures/Vacation/Day2/beach.jpg",
  "storage": "copy",
  "item_type": "image",
  "subfolder": "Day2",

  "converted": "derived/converted/beach.jpg",
  "parent_video": null,
  "video_metadata": null,

  "download_url": null,
  "download_timestamp": null,
  "alt_text": null,

  "metadata": { "datetime": "2025-09-12T08:03:00", "gps": [47.6, -122.3], "camera": "Apple iPhone 15" },
  "exif_datetime": "2025-09-12T08:03:00",
  "file_mtime": 1757664180.0,

  "active_description_id": "uuid-or-millis",
  "embedded_at": null,
  "tags": [],
  "notes": "",
  "is_missing": false,

  "descriptions": [ { /* see §4.1 */ } ]
}
```

### 4.1 Description schema

The unified `Description` reconciles the two prior shapes:

```json
{
  "id": "b1c2...",
  "text": "A wide sandy beach at low tide...",
  "provider": "anthropic",
  "model": "claude-opus-4-6",

  "prompt_name": "detailed",
  "prompt_text": "Describe this image in detail...",

  "created": "2026-06-20T15:09:30Z",

  "input_tokens": 1847,
  "output_tokens": 312,

  "metadata_context": "Seattle, Washington  Sep 12, 2025",
  "detection_data": [],

  "finish_reason": "stop",
  "response_id": "msg_01ABC"
}
```

Field reconciliation between the two legacy models:

| Unified field | `idt_core.Description` | GUI `ImageDescription` |
|---|---|---|
| `id` | `id` (uuid) | `id` (millis string) |
| `text` | `text` | `text` |
| `provider` | `provider` | `provider` |
| `model` | `model` | `model` |
| `prompt_name` | `prompt_name` | `prompt_style` |
| `prompt_text` | `prompt_text` | `custom_prompt` |
| `created` | `timestamp` | `created` |
| `input_tokens` | `input_tokens` | `token_usage.prompt_tokens` |
| `output_tokens` | `output_tokens` | `token_usage.completion_tokens` / `completion_tokens` |
| `metadata_context` | `metadata_context` | (was folded into `metadata`) |
| `detection_data` | — | `detection_data` |
| `finish_reason` | — | `finish_reason` |
| `response_id` | — | `response_id` |

Notes:
- `id` accepts either a UUID (CLI) or a millis string (GUI). Both are opaque unique keys; neither tool parses them.
- Chat sessions are stored in `chats/`, not as image sidecars, but use the **same `Description` shape** for each message (with `prompt_name` = `"user_question"` / `"ai_response"`), matching the GUI's existing chat-as-item migration.

---

## 5. Chat session schema (`chats/<id>.json`)

```json
{
  "id": "chat_1718900000000",
  "name": "Chat: Claude claude-opus-4-6 6/20/2026 2:30P",
  "image": null,
  "provider": "anthropic",
  "model": "claude-opus-4-6",
  "created": "2026-06-20T14:30:00Z",
  "modified": "2026-06-20T14:45:00Z",
  "messages": [ { /* Description shape, §4.1 */ } ]
}
```

`image` is the bundle image name if the chat is about a specific image, else `null`.

---

## 6. How each tool maps to the bundle

### CLI (`cli/main.py` + `idt_core`)

- `idt describe <folder> [--workspace <name|path>]` opens or creates a bundle, copies the folder's images into `images/`, runs the pipeline, writes `descriptions/*.json`.
- Default bundle location when `--workspace` is omitted: `<folder>.idtw` next to the source folder (so the simple case still has an obvious home), **or** a configured default workspaces root. (Implementation picks one; document the choice in the CLI help.)
- `status` / `show` / `stats` / `export` / `embed` / `combine` operate on a bundle path.
- The old sibling `Name.idt/` is read for one release for migration, then dropped.

### GUI (ImageDescriber)

- `ImageWorkspace` becomes a thin in-memory view over a `Workspace` bundle.
- `File → New / Open / Save` operate on `.idtw` directories. The old `~/Documents/.../Workspaces/*.idw` + `WorkspaceFiles/` split is replaced by one `.idtw` bundle the user names and places.
- On opening a legacy `.idw`, the GUI migrates it into a `.idtw` bundle (non-destructive: the `.idw` is left in place, a new bundle is created next to it or at a chosen location).
- The bolted-on "Save as idt Project" / "Import from idt Project" actions are removed — both tools now natively share the bundle, so no conversion is needed.
- Derived artifacts (video frames, HEIC conversions, downloads) move from `WorkspaceFiles/<name>/` into `<bundle>/derived/`.

---

## 7. Invariants (enforce in code review)

1. **Originals are never moved, renamed, deleted, or written.** Copy in; the source path is provenance only.
2. **Everything for a workspace is inside its `.idtw` directory.** No sidecars next to originals, no central `~/Documents` store, no temp dirs left behind.
3. **One format, both tools.** Neither tool has a private on-disk format. A bundle written by the CLI opens unchanged in the GUI and vice-versa.
4. **The bundle is crash-safe and inspectable.** Plain folders and JSON; atomic writes (temp file + rename) for manifest and sidecars.
5. **The image name in `images/` is the key.** Sidecars and chats reference images by bundle name, never by absolute source path.

---

## 8. Migration

| From | To | Behavior |
|---|---|---|
| `.idw` workspace | `.idtw` bundle | On open in GUI: build a bundle, copy referenced images in, convert items+chats to unified sidecars. Original `.idw` untouched. |
| sibling `Name.idt/` (early v4.5) | `.idtw` bundle | `idt` detects a legacy `.idt/` and offers/creates a bundle. Read-only support for one release. |
| `wf_*` workflow dirs (pre-4.5) | — | Not auto-migrated. Still viewable via the GUI Results Viewer. Documented in release notes. |

---

## 9. Open items / future

- **Reference (no-copy) storage mode** for large libraries — schema reserves `storage: "reference"`; not implemented in v4.5.
- **De-duplication** when the same source folder is added to two workspaces (currently each bundle gets its own copy — accepted).
- **Bundle compaction / zip-on-close** — deferred; plain folders for now.
