# Image Description Toolkit v4.5 Release Notes

## Download

| Download | When to use |
|----------|-------------|
| **`idt.exe`** — command-line tool | Terminal/PowerShell use. No installation; copy it anywhere and run. |
| **`ImageDescriber.exe`** — graphical app | Full GUI for describing, viewing, chatting, and managing descriptions. |

Standalone executables — no Python install required.

---

## The Headline: One Workspace, Shared by Both Tools

v4.5 is not a pile of new commands. The old toolkit was already full-featured on
both the CLI and the GUI. The problem v4.5 fixes is **where your work lived and how
the two tools disagreed about it.**

Before v4.5 there were four different ways your descriptions could be stored:

- the CLI wrote `wf_…` folders into your current directory (and copied images into
  a `temp_combined_images` scratch folder),
- a newer CLI engine wrote a `.idt` folder,
- the GUI wrote a `.idw` file plus a separate `WorkspaceFiles` folder buried in
  `Documents`,
- and a bridge tried to convert between them.

A description you made in the GUI and the same image described from the command line
ended up in **different places, in different formats**, and there was no reliable way
to know where anything was.

**v4.5 replaces all of that with one thing: the workspace bundle (`.idtw`).**

A workspace is a single folder you name — `MyTrip.idtw` — and it holds *everything*:
copies of your images, their descriptions, any chat sessions, and any generated files
(video frames, HEIC conversions, downloads). Both `idt` and ImageDescriber open and
save the **same** bundle.

```
MyTrip.idtw/                <- this folder IS your workspace
  manifest.json
  images/                   <- copies of your images
  descriptions/             <- one record per image
  chats/
  derived/                  <- frames, conversions, downloads
  reports/                  <- exported HTML/CSV
```

**Your original photos are never moved or modified.** The bundle copies them in, so
your work travels as one self-contained, shareable folder. (Copying does duplicate
the image data — a deliberate trade for v4.5 so there is exactly one, unambiguous
place your work lives. A no-copy mode for very large libraries is planned.)

### What this gets you

- **No more "where did my descriptions go?"** Everything is in the bundle you named.
- **The two tools finally agree.** Describe a folder with `idt`, then open the same
  `.idtw` bundle in ImageDescriber to view, chat, or keep working — no import/convert
  step. Do it in the other direction too.
- **No mess left behind.** No scratch folders in your working directory, no hidden
  store in `Documents`, no `wf_…` clutter.

### Using it

**CLI:**
```
idt describe ~/Pictures/Vacation/          # creates Vacation.idtw next to the folder
idt describe ~/Pictures/Vacation/ --workspace MyTrip   # name it yourself
idt status   ~/Pictures/Vacation/          # or:  idt status MyTrip.idtw
idt show     MyTrip.idtw
idt export   MyTrip.idtw --format html
```

**GUI:**
- **File → Save as Workspace Bundle (.idtw)…** writes a bundle.
- **File → Open Workspace Bundle (.idtw)…** opens one — including bundles created by
  the CLI.

---

## Under the Hood: A Shared Engine (`idt_core`)

The reason the two tools can finally share a workspace is that they now share an
engine. v4.5 introduces `idt_core`, a single library that does the describing, the
metadata extraction, the embedding, and the workspace storage. The CLI is a thin
layer over it; the GUI calls into it for the same operations. One behavior, one
format, two front ends.

This is the real substance of the release. Most CLI commands you already know are
still here (some renamed or streamlined); a few are genuinely new because the shared
engine made them easy:

| Command | Status in v4.5 |
|---|---|
| `describe` | Core command (was `workflow`/`describe`). Now writes a `.idtw` bundle. Adds stdin mode: `... | idt describe -`. |
| `status` | **New** — progress for a workspace; `--all` summarizes every workspace under a folder. |
| `show` | **New** — print descriptions for an image or workspace (also `--json`). |
| `watch` | **New** — monitor a folder and describe images as they arrive. |
| `config` | **New** — set default provider/model/prompt. |
| `embed` | Writes descriptions into image copies (now EXIF **and** XMP — see below). |
| `export` | HTML/CSV/TXT (broadened from the old `descriptions-to-html`). |
| `combine` | Merge descriptions across workspaces (was `combinedescriptions`). |
| `stats` | Token usage + cost estimates (now spans bundles; `--all`, `--json`). |
| `download` | Fetch images from a web page (`--describe` to describe them). |
| `video` | Extract frames and optionally describe them. |
| `models` / `prompts` / `guide` | Check models / list prompts / interactive wizard. |
| `version` | Print the installed version, Python version, and binary path. |
| `update` | **New** — check whether a newer release is available. |

---

## Descriptions Embedded in Image Files (now EXIF **+** XMP)

`idt embed` (and the GUI's embed action) write a description into a **copy** of each
image so it travels with the file. v4.5 writes both the EXIF `ImageDescription` field
**and** XMP `dc:description` for JPEGs — the field that Windows Explorer's
"Description" column, Adobe Lightroom/Bridge, and Apple Photos actually read.

| Format | Written |
|--------|---------|
| JPEG, TIFF | EXIF `ImageDescription` + XMP `dc:description` |
| PNG | `tEXt` chunk, key `Description` |
| WebP | EXIF `ImageDescription` |
| HEIC | a JPEG copy with the description embedded |

JPEG embedding is lossless. Copies go to `<bundle>/embedded/`; your originals are not
touched unless you explicitly choose in-place embedding.

---

## GPS Context in Prompts (CLI and GUI)

When an image has GPS coordinates, IDT can tell the AI where the photo was taken,
which noticeably improves descriptions.

- **Always, no internet:** camera, date taken, and raw GPS coordinates from EXIF are
  added to the prompt when present. The GUI shows this under "AI context:".
- **Optional geocoding (internet):** turn on **Geocode GPS** (GUI processing dialog)
  or pass `--geocode` (CLI) to add the city/state/country. Off by default.

---

## IDT Now Tells You When There's an Update

Until now the only way to learn about a new version was to go back to the GitHub
releases page and look. v4.5 adds an update check to both tools.

**ImageDescriber** gains two items in the **Help** menu:

- **Check for Updates...** — asks right now, and tells you either that you're up to
  date or that a newer version exists.
- **Automatically Check for Updates** — on by default. Once a day at most, shortly
  after launch, IDT quietly checks. If there's nothing new it says nothing at all;
  it only speaks up when there's an update.

When an update is found you get three choices: **Download**, **Skip This Version**
(never asked about that particular version again), or **Later**.

**Windows:** choosing Download fetches the installer, closes ImageDescriber, and
runs it. Windows will ask for administrator permission, because IDT installs to the
root of your system drive. Your settings, workspaces, and descriptions are left
alone.

**macOS:** choosing Download saves the disk image to your Downloads folder and shows
it in Finder. Quit ImageDescriber, then drag the new ImageDescriber to Applications.
(Making this as automatic as Windows is on the list.)

**Command line:**

```
idt update
```

reports your installed version, whether a newer one exists, and where to get it.

**One update covers both tools.** The Windows installer and the macOS disk image each
contain `idt` *and* ImageDescriber, so updating from either one updates both. You
never have to update them separately.

The check reads the public GitHub releases list and nothing else — no account, no
telemetry, no data sent. Turn it off any time with the Help menu item; **Check for
Updates** still works on demand when it's off.

---

## Bug Fixes

- **UTF-8 BOM in stdin mode on Windows.** Reading image paths from stdin in PowerShell
  could mangle the first path because of a byte-order mark. The BOM is now stripped.

---

## Known Issues

- **The GUI reads and writes bundles, but does not yet fully retire the old `.idw`
  format.** ImageDescriber can open and save `.idtw` bundles (File menu), and Save
  routes back to a bundle when you opened one. But the classic `.idw` save path and
  its `Documents/…/WorkspaceFiles` folder still exist for now. Making the bundle the
  GUI's sole format (and migrating old `.idw` files automatically on open) is the next
  step.
- **CLI `watch` and `video` still use the older per-folder storage**, not the bundle.
  They will be brought onto bundles next.
- **Old `wf_…` workflow folders are not auto-imported.** Descriptions from pre-v4.5
  CLI runs aren't visible to the new commands. View them with the GUI's Results
  Viewer.
- **`idt guide` needs an interactive terminal.** If it hangs in a non-interactive
  environment, press Ctrl+C and use `idt describe` directly.
- **`idt update` is notify-only.** It tells you a new version exists and where to get
  it, but does not download or install anything. Use the installer (or
  ImageDescriber's Help > Check for Updates) to actually update.
- **No automated tests yet for the CLI command layer** (`cli/main.py`). The engine,
  the workspace bundle, the describe pipeline, and the GUI⇄bundle bridge are unit
  tested; the thin CLI argument layer is exercised manually.

---

## For Developers

- **`docs/design/unified-workspace.md`** is the authoritative format reference: bundle
  layout, `manifest.json` schema, the unified per-image description schema (which
  reconciles the CLI's and GUI's previously different shapes), chat schema, and
  invariants.
- **`idt_core/workspace.py`** — the bundle (`Workspace`, `WorkspaceItem`,
  `WorkspaceDescription`).
- **`idt_core/gui_bridge.py`** — lossless conversion between the GUI's workspace
  document and a bundle; tested against the real GUI data model.
- **`idt_core/pipeline.py`** — `WorkspacePipeline` runs describe over a bundle.
- Tests: `pytest_tests/unit/test_workspace_bundle.py`,
  `test_workspace_pipeline.py`, `test_gui_bridge.py`, plus the existing
  `test_idt_core.py`.

---

## Providers (updated July 2026)

| Provider | Key required | Notes |
|----------|-------------|-------|
| Ollama | No | Local; Ollama must be installed/running. |
| Claude (Anthropic) | `ANTHROPIC_API_KEY` | claude-opus-5, claude-sonnet-5, claude-opus-4-8, claude-haiku-4-5 |
| OpenAI | `OPENAI_API_KEY` | gpt-5.2, gpt-5.1, gpt-5-mini, gpt-5-nano, o4-mini, o3 |
