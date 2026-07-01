# Image Handling & Lifecycle — Design Reference

**Status:** v4.5 — proposed (supersedes the copy-by-default decision in
[`unified-workspace.md`](unified-workspace.md) §1 and §2)
**Audience:** developers working on `idt` (CLI) and ImageDescriber (GUI); advanced
users who want to know exactly where their files go.
**Date:** 2026-06-30

> **Scope.** This document covers what the toolkit does with a user's images from
> the moment they hand us a directory until they are done. It is a *lifecycle*
> document, not an implementation spec. It deliberately defers two things —
> cleanup of copied files and portable-bundle export — to "Open items" (§8).
> Nothing here applies to pre-4.5 behavior; we are not migrating old workflows.

---

## 1. The one rule that never changes

**We never move, rename, delete, or write to the user's original files.** Every
other decision below is negotiable; this one is not. The source directory the
user points us at is read-only as far as the toolkit is concerned.

Embedding descriptions into image metadata (`idt embed` / GUI Embed) is *not* an
exception: it writes into **copies**, never the originals — unless the user
explicitly opts into in-place embed on files they nominate.

---

## 2. The mental model: three folders, mirrored structure

Everything we produce for a workspace lives inside its `.idtw` directory, in one
of three places. Each mirrors the **original source directory structure** —
subfolders and all — unless there is a specific reason not to.

| Folder | Holds | When it gets content |
|---|---|---|
| `images/` | Copies of the user's originals, byte-for-byte | Only if the user opts into copying (see §4) |
| `derived/` | Anything we generate *from* an image: extracted video frames, HEIC→JPEG conversions | Whenever a step needs a different file than the original (e.g. AI can't read HEIC) |
| `embedded/` | Copies with descriptions written into their metadata | Only when the user runs embed |

The guiding principle the user asked for, stated plainly:

> **Images, and anything we derive or embed, mirror the original source layout
> unless there is a good reason not to.**

So a source tree like:

```
Vacation/
  Day1/beach.jpg
  Day2/beach.jpg
  clips/sunset.mov
```

produces (when copying is on, after frame extraction and embed):

```
Vacation.idtw/
  images/
    Day1/beach.jpg
    Day2/beach.jpg            <- no flattening, no "Day2__beach.jpg" rename needed
    clips/sunset.mov
  derived/
    frames/clips/sunset/sunset_000123.jpg
  embedded/
    Day1/beach.jpg
    Day2/beach.jpg
  descriptions/
    Day1/beach.jpg.json
    Day2/beach.jpg.json
    clips/sunset.mov.json
```

Mirroring the structure removes the need for the collision-safe flat naming
(`Day2__beach.jpg`) the bundle uses today: `descriptions/` already mirrors source
subfolders (as of the v4.5 fix), and `images/`/`derived/`/`embedded/` should do
the same so the same relative path identifies a file in every folder.

### Why this changes the earlier decision

[`unified-workspace.md`](unified-workspace.md) declared "self-contained,
duplicating bundle — copies images by default." In practice that never became
true uniformly: the **CLI always copies**, the **GUI never copies** (it passes
`copy_images=False` and records items as `storage="reference"`). The result is
inconsistent and surprising. This document resolves the inconsistency by making
the behavior **explicit and identical across both tools**, and by changing the
default — see §4.

---

## 3. The lifecycle: directory in, descriptions out

What happens, step by step, from the user handing us a directory to being done.

### Step 0 — User points us at a source directory

CLI: `idt describe <directory>`. GUI: load a folder. At this point **nothing is
copied and nothing is processed.** We:

1. Open or create the `.idtw` workspace (named by the user, or derived from the
   source folder name).
2. Set up the empty skeleton: `manifest.json`, `descriptions/`, `images/`,
   `chats/`, `derived/`, `logs/`.
3. Scan the source recursively, recording each image as a workspace item with its
   `source_path`, `subfolder`, and `file_mtime` — but **no pixels copied yet**.

This is the cheap, instant step. A 3,800-image folder becomes a browsable
workspace immediately, which is how the GUI already behaves and what we want the
CLI to feel like too.

### Step 1 — User chooses options and starts processing

Before the run, the user (or a config default) has decided:

- **Copy originals into the workspace?** (the new option — see §4)
- Provider / model / prompt.
- Whether to extract video frames, geocode, embed, export.

### Step 2 — Copy (optional)

If copying is on, each original is copied into `images/<mirrored-path>` with
`shutil.copy2` (preserves mtime; original untouched). The item's `storage` flips
from `"reference"` to `"copy"` and its working path points at the bundle copy.

If copying is off, `images/` stays empty and every item stays
`storage="reference"`; the working path is the original on disk.

Either way, the *rest of the pipeline does not care* — it asks the item for "the
path I should read," and gets either the bundle copy or the original.

### Step 3 — Derive what the pipeline needs

Some images can't be fed to the AI as-is:

- **HEIC** → converted to JPEG in `derived/converted/<mirrored-path>`.
- **Videos** → frames extracted to `derived/frames/<stem>/...`.

Derived files always live in the bundle regardless of the copy setting, because
they are *our* artifacts, not the user's originals. They mirror source structure
too.

### Step 4 — Describe

The AI reads the working path (original, copy, or derived file) and we write a
per-image sidecar to `descriptions/<mirrored-path>.json`. This is the durable
output and the one thing that always exists.

### Step 5 — Embed (optional)

If the user embeds, we copy the image (original or bundle copy) into
`embedded/<mirrored-path>` and write the description into that copy's metadata.
The sidecar records `embedded_at` and `embedded_path`. Originals are untouched.

### Step 6 — Export (optional)

HTML galleries, CSVs, combined description files are written **wherever the user
asks, outside the bundle.** They are products, not workspace state.

### Step 7 — Done

The workspace is a self-describing folder. What it contains depends on the
options chosen:

- Always: `manifest.json`, `descriptions/`, possibly `derived/`.
- If copy was on: `images/` populated.
- If embed was run: `embedded/` populated.

---

## 4. The copy option (new)

**Default: do not copy.** There is no compelling reason for the CLI or GUI to
duplicate a user's entire photo library by default, and copying a large folder
up front hurts the "instant workspace" feel. Copying becomes a deliberate choice
the user makes when they want a self-contained, movable workspace.

The option appears in three places, with the same meaning everywhere:

| Surface | Where | Default |
|---|---|---|
| **CLI** | `idt describe ... [--copy-originals / --no-copy-originals]` | no copy |
| **GUI processing dialog** | A checkbox: "Copy original images into the workspace" | follows config default |
| **GUI config / settings dialog** | A persistent default for the above | no copy |
| **Config file** (`~/.idt/config.json`) | `"copy_originals": false` | no copy |

Precedence: explicit CLI flag or GUI dialog checkbox for *this run* > workspace
manifest setting (if we record one) > user config default > built-in default
(no copy).

Whatever the choice, **the no-modify-originals rule (§1) still holds.** "Copy"
vs "reference" only decides whether a duplicate lives in the bundle; it never
licenses writing to the source.

### Consequence to design around

A reference-mode workspace is **not portable and not self-contained** — it points
at originals that may move or vanish. That is fine and expected; portability is
explicitly opt-in via copying. We should surface this honestly (e.g. a workspace
that references missing originals marks those items `is_missing=True`, which the
schema already supports).

---

## 5. What each storage mode means for "where do I read the image?"

The pipeline never branches on copy/reference directly. It asks the item for its
working path, resolved in this order:

1. **Derived file** if one exists (HEIC→JPEG conversion, the frame itself) —
   because that's what the AI can actually read.
2. **Bundle copy** in `images/` if `storage == "copy"`.
3. **Original `source_path`** if `storage == "reference"`.

If a reference-mode original is gone, the item is `is_missing` and is skipped
(or shown greyed-out in the GUI), never an error that halts a batch.

---

## 6. Invariants (enforce in code review)

1. **Originals are never moved, renamed, deleted, or written.** (§1)
2. **Copying is off by default** and is a user-visible option in CLI, GUI dialog,
   GUI config, and config file — with identical meaning. (§4)
3. **`images/`, `derived/`, and `embedded/` mirror the source subfolder
   structure**, matching `descriptions/`. The same relative path identifies a
   file across all four. (§2)
4. **Derived and embedded artifacts always live inside the bundle**, regardless
   of the copy setting — they are ours, not the user's. (§3)
5. **The CLI and GUI behave identically** for a given copy setting. No tool has a
   private rule. (§2, §4)
6. **The bundle is crash-safe and inspectable** — plain folders, JSON, atomic
   writes.

---

## 7. What changes from today

| Area | Today | Proposed |
|---|---|---|
| CLI copy behavior | Always copies | Off by default; `--copy-originals` to opt in |
| GUI copy behavior | Never copies (`copy_images=False`) | Off by default; checkbox + config to opt in |
| `images/` naming | Flat, collision-safe (`Day2__beach.jpg`) | Mirrors source structure (`Day2/beach.jpg`) |
| `derived/` naming | Partly mirrored | Fully mirrors source structure |
| `embedded/` naming | Mirrors source (recent fix) | Unchanged — keep mirroring |
| Copy timing | Up front, unconditional (CLI) | Only when opted in, at process start |
| Consistency | CLI ≠ GUI | CLI = GUI |

The collision-safe flat-naming machinery (`_bundle_name_for`) becomes unnecessary
once `images/` mirrors structure — paths can't collide if they carry their
subfolder. That code can be retired as part of the change.

---

## 8. Open items (deferred — named so we don't forget)

These are **out of scope** for this document but will land as follow-ups:

- **Cleanup / the duplication bug.** When copying is on, the bundle duplicates
  pixel data, and we currently have no defined path for reclaiming space or
  removing stale copies (e.g. after an item is deleted, or a source is removed).
  Needs its own design pass. *This is the known bug referenced in discussion.*
- **Portable bundle export.** A future `idt package` / GUI "Export portable
  workspace" that guarantees a fully self-contained `.idtw` (forces copy, pulls
  in any referenced originals, verifies nothing is `is_missing`) so a user can
  move a complete run to another machine. The copy option here is the foundation
  for it, but the command itself is deferred.
- **Per-workspace copy setting in the manifest.** Whether a workspace remembers
  its own copy preference (vs. only the global config + per-run choice). TBD.
- **Reference→copy upgrade in place.** Letting a user "make this workspace
  self-contained" after the fact, copying in originals for an existing
  reference-mode bundle.

---

## 9. Review checklist before we implement

- [ ] Confirm default-no-copy is what we want for **both** CLI and GUI.
- [ ] Confirm `images/` should mirror structure (retire flat collision naming).
- [ ] Decide whether the copy setting is also stored per-workspace in the
      manifest, or only config + per-run.
- [ ] Decide GUI copy timing/UX (background copy + progress for large folders).
- [ ] Decide how reference-mode missing originals surface in CLI output and GUI.
- [ ] Sketch (not build) the cleanup model so we don't paint ourselves into a
      corner with the copy layout.
