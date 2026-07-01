# The GUI as a Layer on the CLI — Design Reference

**Status:** v4.5+ — proposed. Move 1 (the launcher) is being implemented now;
Move 2 (engine unification) is the larger follow-up this document scopes.
**Audience:** developers working on `idt` (CLI) and ImageDescriber (GUI).
**Date:** 2026-06-30
**Related:** [`unified-workspace.md`](unified-workspace.md),
[`image-handling-lifecycle.md`](image-handling-lifecycle.md)

---

## 1. The idea

> The GUI is not a window *into* the CLI. It is *part of* the CLI when you invite
> it in with `--showgui`. Once invited, the two are one thing — closing the GUI
> ends the invocation, exactly as closing the CLI would.

The user runs a single command:

```
idt describe <directory> --showgui [--provider ... --model ... --prompt ...]
```

and gets the graphical experience — live progress, the viewer, chat, prompt
editing — driven by the same run they asked for on the command line. There is no
"the GUI app" and "the CLI app" as separate products in this mode. There is one
invocation that happens to render graphically.

This has a concrete consequence for lifecycle: **the GUI process is the
invocation.** When the window closes, the command returns. We do not daemonize,
we do not leave a background run going. Invite it in, work, close it, done.

---

## 2. Where we are today (two engines, one format)

As of this session the *data layer* is unified — one `.idtw` bundle, consistent
copy/reference semantics, mirrored structure, read and written by both surfaces.
What is **not** unified is execution:

| Concern | CLI | GUI |
|---|---|---|
| Workspace model | `idt_core.Workspace` (sidecars on disk) | `data_models.ImageWorkspace` (in-memory) — translated by `gui_bridge` |
| Describe engine | `idt_core.WorkspacePipeline` → `WorkspaceEvent` stream | `workers_wx.BatchProcessingWorker` calling `provider.describe_image(...)` directly |
| Progress surface | `idt_core.Progress` (console) | `BatchProgressDialog` (wx) |

`gui_bridge` exists *because* the two workspace models diverged. So "the GUI is a
layer on the CLI" is precisely the statement: **retire the GUI's parallel engine
and model, and have the GUI drive the CLI's.**

---

## 3. Two moves

### Move 1 — the launcher (near-term, implemented now)

`idt describe <dir> --showgui` hands the run to the GUI instead of processing in
the console. Mechanically:

1. The CLI resolves the same run parameters it always does (provider, model,
   prompt, geocode, copy-originals, workspace path).
2. Instead of running `WorkspacePipeline`, it **launches the GUI** on the source
   directory (or the resolved bundle), passing those parameters plus an
   auto-start signal.
3. The GUI loads, immediately begins the batch using its normal processing path,
   and shows `BatchProgressDialog` — indistinguishable from the user having
   clicked "Describe All" themselves.
4. The CLI process either waits on the GUI (so the invocation is truly one
   process-lifetime) or execs it — see §4.

In Move 1 the *engine underneath is still the GUI's own worker.* That is
acceptable: the point of Move 1 is the seam and the UX, not yet the single
engine. It ships value immediately and is low-risk.

### Move 2 — one engine (the real unification)

Make the GUI drive `idt_core.WorkspacePipeline`:

1. **Route GUI batches through the pipeline.** Replace the describe loop inside
   `BatchProcessingWorker` with a thread that runs
   `for event in WorkspacePipeline(ws, provider).run(options)` and marshals each
   `WorkspaceEvent` onto the UI thread (`wx.CallAfter`) to update
   `BatchProgressDialog`. The pipeline is already a generator, so this is an
   adapter, not a rewrite of the batch UI.
2. **Operate on `idt_core.Workspace` directly.** Retire `ImageWorkspace` +
   `gui_bridge` in favour of the bundle model the CLI uses. This is the larger
   part — the in-memory model is woven through the wx frame — and should be
   staged (read path first, then write path, then delete the bridge).
3. **Open `.idtw` bundles natively.** Once the GUI operates on
   `idt_core.Workspace`, opening a `.idtw` bundle is intrinsic — File → Open, the
   positional launch path, and `--showgui` all accept a bundle directly, not just
   a source directory. Today the GUI loader handles `.idt` and directories but
   **not** `.idtw` (a `.idtw` passed as a directory would be mis-scanned), which
   is why Move 1's `--showgui` deliberately requires a source directory. Native
   `.idtw` opening lands here, in Move 2, rather than as a bolt-on before it.
4. **Keep GUI-only concerns above the shared engine.** Chat, the viewer, the
   prompt editor, workspace stats — these layer *on top of* the shared
   `Workspace`, they do not need their own copy of it.

When Move 2 lands, `--showgui` stops being "launch a sibling app" and becomes
"render this pipeline run graphically," which is the true form of the idea in §1.

---

## 4. Process model for `--showgui`

Because the GUI *is* the invocation, the CLI should not fork-and-forget. Options,
in order of preference:

1. **Launch and wait (recommended).** The CLI spawns the GUI as a child process
   and blocks until it exits, propagating the child's exit code. Closing the GUI
   returns control to the shell — "closing the GUI is like closing the CLI." The
   console stays attached, so GUI stderr (and the wx silent-failure traps) are
   visible to a developer who launched from a terminal.
2. **Exec/replace.** Replace the CLI process image with the GUI. Cleanest
   conceptually (there is literally one process) but awkward on Windows and loses
   the chance for the CLI to print a closing summary. Not preferred.

We take option 1. The CLI's job after launching is nothing — it waits. It does
**not** also run a headless pipeline; that would be two runs.

### Locating the GUI

- **Frozen (PyInstaller):** the GUI is a sibling executable next to `idt.exe`
  (e.g. `ImageDescriber.exe` / `ImageDescriber` on macOS). Detect with
  `getattr(sys, 'frozen', False)` and resolve relative to the `idt` executable's
  directory. If the sibling is absent, fail with a clear message rather than
  silently degrading to console mode.
- **Development:** run `imagedescriber/imagedescriber_wx.py` with the *same*
  Python interpreter (`sys.executable`).

Both cases go through one helper so callers do not special-case frozen vs dev.

### Parameters passed to the GUI

`--showgui` forwards the run parameters as GUI command-line args:

| CLI | GUI arg | Meaning |
|---|---|---|
| `<directory>` | positional `path` | what to load. **Move 1: directory only** — passing a `.idtw` bundle to `--showgui` is rejected until the GUI opens bundles natively (Move 2, §3). |
| `--provider` | `--provider` | AI provider for the auto-started run |
| `--model` | `--model` | model name |
| `--prompt` | `--prompt` | prompt name/style |
| `--geocode` | `--geocode` | enable GPS→place enrichment |
| `--copy-originals` | `--copy-originals` | copy vs reference for the workspace |
| (implicit) | `--autostart` | begin the batch immediately on load |

The GUI already parses a positional `path`; Move 1 adds `--autostart` plus the
option pass-through, and wires "after the frame is ready, if `--autostart`, run
the batch with these options."

---

## 5. Invariants

1. **One invocation, one process lifetime.** `--showgui` launches the GUI and
   waits; when the GUI closes, the command returns. No orphaned background run.
2. **No double execution.** In `--showgui` the CLI does not also run a headless
   pipeline. The GUI performs the run.
3. **Same result on disk regardless of surface.** A run done via `--showgui`
   produces the same `.idtw` bundle a console run or a hand-started GUI run
   would. (Move 2 makes this true *by construction*; Move 1 relies on the shared
   bundle format.)
4. **Fail loud if the GUI is unavailable.** If `--showgui` is requested and the
   GUI cannot be located/launched, error out — do not silently fall back to
   console mode, which would surprise the user who asked for the GUI.

---

## 6. Open items

- **Exit-code propagation** from the GUI back to the CLI (so `--showgui` runs are
  scriptable in the degenerate "run once and close" case).
- **Headless CI** cannot test `--showgui` end to end; Move 1 needs a launch-path
  unit test that stops at "the correct command/exe would be spawned" plus manual
  dev-mode verification.
- **Move 2 sequencing doc** — once we start engine unification, the workspace-model
  migration (retire `ImageWorkspace`/`gui_bridge`) deserves its own staged plan.
  Native `.idtw` opening (§3, item 3) is part of that migration, not a separate
  task — the GUI can open a bundle the moment it operates on `idt_core.Workspace`.
- **macOS app-bundle launch** — locating `ImageDescriber.app` vs a bare binary in
  the frozen case needs platform-specific resolution.
