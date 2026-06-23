# IDT CLI Inventory: main vs v4.5 — Tested Results

**Last Updated:** 2026-06-23  
**Testing method:** Live execution against `BuildAndRelease\WinBuilds\dist_all\bin\idt.exe`  
**Test data:** `C:\Users\kelly\Documents\idt\09.idtw` (222/1804 described), `test_cli\` (5 PNGs)  
**Branch:** v4.5

---

## Agent Quick-Start

If you are an AI agent picking this up cold, read this section before touching any code.

### Repo Layout (what matters)

```
cli/
  main.py           ← THE active CLI entry point. All 14 commands live here.
  guide.py          ← guideme wizard

idt_core/
  workspace.py      ← Workspace class — the .idtw bundle model
  project.py        ← Project class — the legacy .idt/ sidecar model
  pipeline.py       ← WorkspacePipeline (for .idtw), Pipeline (for .idt/)
  providers/        ← claude.py, ollama.py, openai_provider.py, florence.py
  embedder.py       ← embed_image_file()
  exporter.py       ← export_workspace_html/csv/txt(), export_html/csv/txt()
  config.py         ← UserConfig, BUILT_IN_PROMPTS

idt/
  idt_cli.py        ← DEAD CODE in the build. Not used by the binary.
  idt.spec          ← PyInstaller spec — entry point is ../cli/main.py

scripts/
  workflow.py       ← Legacy workflow engine (main branch). Not called by new CLI.

BuildAndRelease/WinBuilds/dist_all/bin/
  idt.exe           ← The built binary to test against
```

### Two Data Models — Know Which One You're In

The codebase has two data models. Bugs often come from mixing them up.

**Workspace (`.idtw`) — new model, used by `describe`, `status`, `show`, `embed`, `export`, `stats`, `combine`:**
- A self-contained directory bundle: `MyTrip.idtw/images/`, `descriptions/`, `logs/`, `manifest.json`
- Created by `idt describe <source_dir>`; auto-placed under `~/Documents/idt/` by default
- `Workspace` class in `idt_core/workspace.py`
- Per-image state lives in `descriptions/<imagename>.json` sidecars (one per image)
- Resume = run `describe` again; already-described images skipped automatically

**Project (`.idt/`) — legacy model, used by `download`, `video`, `watch`, and stdin mode:**
- Mirror directory created NEXT TO the source folder: `Photos/2025/09.idt/`
- `Project` class in `idt_core/project.py`
- Per-image state in `idt_dir/<relpath>.json` sidecars

Most of the P0/P1 bugs are in `cli/main.py`. Changes there are self-contained; no other file needs editing for the encoding and show-lookup fixes.

### How to Test

```powershell
# The built binary
$IDT = "C:\Users\kelly\GitHub\Image-Description-Toolkit\BuildAndRelease\WinBuilds\dist_all\bin\idt.exe"

# Existing workspace with 222 described images — safe to run read commands against
$WKSP = "C:\Users\kelly\Documents\idt\09.idtw"

# Quick smoke tests (no AI calls, instant)
& $IDT status $WKSP
& $IDT show $WKSP | Select-Object -First 10
& $IDT combine "C:\Users\kelly\Documents\idt" --output test_out.csv   # this currently crashes
& $IDT export $WKSP --format html
& $IDT stats $WKSP
& $IDT models
& $IDT prompts
```

To rebuild after changing `cli/main.py` (no PyInstaller needed for dev testing):
```powershell
# Run directly from source — same code path as the binary
cd C:\Users\kelly\GitHub\Image-Description-Toolkit
python cli/main.py status "C:\Users\kelly\Documents\idt\09.idtw"
python cli/main.py combine "C:\Users\kelly\Documents\idt" --output test_out.csv
```

To rebuild the binary after changes:
```batch
cd idt
call .winenv\Scripts\activate.bat
pyinstaller --clean --noconfirm idt.spec
```

---

## Critical Finding: Two Completely Different CLI Systems

The v4.5 branch contains **two CLI codebases**. The built binary uses only the new one:

| Codebase | Entry Point | Commands | Status |
|----------|-------------|----------|--------|
| **Legacy** | `idt/idt_cli.py` → `scripts/workflow.py` | `workflow`, `redescribe`, `stats`, `contentreview`, etc. | Source only — NOT in built binary |
| **New (idt_core)** | `cli/main.py` → `idt_core/` | `describe`, `status`, `show`, `embed`, `export`, `combine`, `models`, `watch`, `prompts`, `stats`, `config`, `guideme` | **This is what ships** |

---

## Noise Issue Affecting Every Command

Every single command emits an INFO line to stderr:

```
INFO: Using config from IDT_CONFIG_DIR environment variable
      Location: C:\idt\scripts\image_describer_config.json
      To change: Windows: setx IDT_CONFIG_DIR ""
```

This fires on every command including `idt models`, `idt prompts`, `idt config`. It is a cosmetic defect — commands still succeed — but it is confusing and pollutes scripted output.

---

## Command-by-Command Test Results

### New Commands (v4.5 only)

| Command | Test Run | Result | Notes |
|---------|----------|--------|-------|
| `describe <dir>` | `idt describe test_cli/ --provider ollama --no-export` | ✅ PASS | Auto-creates `test_cli.idtw` under workspace root; skips already-described images (implicit resume) |
| `describe --redescribe` | Code-inspected | ✅ PASS (by inspection) | Re-describes all items even if already described |
| `describe --limit N` | Code-inspected | ✅ PASS (by inspection) | Stops after N images |
| `describe --embed` | Code-inspected | ✅ PASS (by inspection) | Embeds after describing |
| `describe --show-descriptions` | Code-inspected | ✅ PASS (by inspection) | Prints each description to console |
| `describe --geocode` | Code-inspected | ✅ PASS (by inspection) | Reverse geocodes GPS |
| `describe --no-metadata` | Code-inspected | ✅ PASS (by inspection) | Skips EXIF extraction |
| `describe --no-export` | Tested (used in test run) | ✅ PASS | Suppresses auto-HTML |
| `describe --no-video` | Code-inspected | ✅ PASS (by inspection) | Skips video frame extraction |
| `describe --workspace NAME` | Code-inspected | ✅ PASS (by inspection) | Uses named workspace |
| `status <workspace.idtw>` | `idt status 09.idtw` | ✅ PASS | Shows 222/1804, sources, commands run |
| `status <source-dir>` | `idt status test_cli` | ✅ PASS | Finds sibling `.idtw` via mirror lookup |
| `status --all <dir>` | `idt status ~/Documents/idt --all` | ✅ PASS | Lists all workspaces: 01.idtw 100%, 09.idtw 12% |
| `status --json` | Code-inspected | ✅ PASS (by inspection) | JSON output |
| `show <workspace.idtw>` | `idt show 09.idtw` | ✅ PASS | Prints all described images with model/context/text |
| `show <source-dir>` | `idt show test_cli/` | ⚠️ PARTIAL | Works but some descriptions trigger charmap Unicode error (see Bugs) |
| `show <source-file>` | `idt show test_cli/IMG_3137.PNG` | ✅ PASS | Finds sibling `.idtw` and looks up by source_path |
| `show <file-inside-workspace-images/>` | `idt show 09.idtw/images/849...jpeg` | ❌ FAIL | "No description found" — walk-up logic doesn't recognize files inside a bundle |
| `show --json` | Tested as part of `show 09.idtw --json` | ✅ PASS | Streams one JSON object per line |
| `embed <workspace.idtw>` | `idt embed 09.idtw` | ✅ PASS | Embedded 222 images to `09.idtw/embedded/` |
| `embed --dry-run` | `idt embed 09.idtw --dry-run` | ✅ PASS | Reported "Would embed 222 images" |
| `embed --force` | Code-inspected | ✅ PASS (by inspection) | Re-embeds already-embedded |
| `export --format html` | `idt export 09.idtw --format html` | ✅ PASS | Created `09.idtw/reports/descriptions.html` |
| `export --format csv` | `idt export 09.idtw --format csv` | ✅ PASS | Created `09.idtw/reports/descriptions.csv` |
| `export --format txt` | `idt export 09.idtw --format txt` | ✅ PASS | Created `09.idtw/reports/descriptions.txt` |
| `combine <dir>` (stdout) | `idt combine ~/Documents/idt` | ✅ PASS | Outputs CSV header + rows; found both workspaces |
| `combine --output file` | `idt combine ~/Documents/idt --output out.csv` | ❌ FAIL | **Bug:** `'charmap' codec can't encode character '→'` — Windows default file encoding |
| `combine --format tsv --output file` | Tested | ❌ FAIL | Same charmap bug |
| `stats <workspace.idtw>` | `idt stats 09.idtw` | ✅ PASS | Shows 222 images / ollama / no token data (local model) |
| `stats --all <dir>` | `idt stats ~/Documents/idt --all` | ✅ PASS | Aggregates both workspaces |
| `stats --json` | Code-inspected | ✅ PASS (by inspection) | JSON output |
| `models` (all) | `idt models` | ✅ PASS | Lists 9 Ollama models; reports no API keys for Anthropic/OpenAI |
| `models --provider ollama` | Code-inspected | ✅ PASS (by inspection) | Filters to ollama |
| `models --json` | Code-inspected | ✅ PASS (by inspection) | JSON output |
| `prompts` | `idt prompts` | ✅ PASS | Lists 12 prompts with previews |
| `prompts --json` | Code-inspected | ✅ PASS (by inspection) | JSON output |
| `config` (view) | `idt config` | ✅ PASS | Shows provider/model/prompt/workspace_root |
| `config --set key=value` | Code-inspected | ✅ PASS (by inspection) | Sets config value |
| `download <url>` | Not tested (requires network) | — | Uses legacy `.idt/` project model, not workspace |
| `download --describe` | Not tested | — | Describes after download |
| `video <source>` | Not tested (no video files available) | — | Uses legacy `.idt/` project model |
| `video --describe` | Not tested | — | Describes extracted frames |
| `watch <dir>` | Not tested (blocking/long-running) | — | Uses legacy `.idt/` project model |
| `guideme` | Not tested (interactive wizard) | — | Code inspected; calls `cli.guide.run_guide()` |

---

## Commands Removed from main (Not in v4.5 Built Binary)

### Commands Fully Removed — No Equivalent

| Old Command | Status | Impact |
|-------------|--------|--------|
| `version` / `--version` | ❌ REMOVED | No way to check binary version from CLI |
| `contentreview` | ❌ REMOVED | AI description quality/content analysis — no replacement |
| `manage-models install <model>` | ❌ REMOVED | Cannot install Ollama models through IDT; must use `ollama pull` directly |
| `manage-models remove <model>` | ❌ REMOVED | Cannot remove Ollama models through IDT |
| `manage-models info <model>` | ❌ REMOVED | Cannot get model details through IDT |
| `manage-models recommend` | ❌ REMOVED | No model recommendations; `idt models` just lists installed |
| `convert-images` | ❌ REMOVED | HEIC→JPEG conversion now happens internally during `describe`; no standalone command |

### Commands Replaced or Renamed

| Old Command | New Command | Status | Differences |
|-------------|-------------|--------|-------------|
| `workflow <dir>` | `describe <dir>` | ⚠️ REPLACED | See workflow options table below |
| `describe` (was alias for `workflow`) | `describe` | ✅ SAME NAME | Now the primary command |
| `redescribe <wf_dir>` | `describe <source_dir> --redescribe` | ⚠️ CHANGED | Must pass source dir, not workspace path |
| `results-list` | `status --all <dir>` | ⚠️ REPLACED | Different format; no CSV output; no sort-by option |
| `check-models` | `models` | ⚠️ REPLACED | Same info; no `--verbose`; Anthropic/OpenAI report key-present vs key-absent |
| `manage-models list` | `models` | ⚠️ REPLACED | `models` lists; no `--installed` filter; no `--provider` filter for huggingface |
| `prompt-list` | `prompts` | ⚠️ REPLACED | Same info; no `--config-image-describer` override |
| `extract-frames <video>` | `video <source>` | ⚠️ REPLACED | Different path: creates `.idt/frames/` in a legacy project, not workspace |
| `describe-video <video>` | `video <source> --describe` | ⚠️ REPLACED | Same caveat as above |
| `descriptions-to-html <file>` | `export --format html` | ⚠️ REPLACED | Now operates on workspace, not a raw `.txt` descriptions file |
| `combinedescriptions` | `combine <dir>` | ⚠️ REPLACED | Works; different column names; `atsv` format gone; no `analysis/results/` default output |
| `stats` (workflow timing/performance) | `stats` (token cost) | ❌ INCOMPATIBLE REPLACEMENT | **Completely different purpose.** Old: per-step timing, images/hour, duration. New: token counts and API cost estimates per model. No overlap. |

---

## Workflow/Describe Options: main vs v4.5

### Options That Work the Same

| Option | v4.5 form | Notes |
|--------|-----------|-------|
| Input directory | positional `source` | Same |
| Provider selection | `--provider {anthropic,ollama,openai,florence}` | `huggingface` renamed to `florence`; `mlx` removed from choices |
| Model selection | `--model NAME` | Same |
| Prompt | `--prompt NAME` / `--prompt-text TEXT` | Same concept; old: `--prompt-style`; new: `--prompt` |
| Re-describe | `--redescribe` | Same flag, same meaning |
| Show descriptions | `--show-descriptions` | Same |
| Geocoding | `--geocode` | Same; cache fixed at `~/.idt/geocode_cache.json` |
| Metadata | `--no-metadata` | Same; enabled by default |
| Limit | `--limit N` | Same |
| Quiet mode | `--quiet` / `-q` | Replaces `--batch` |
| Embed | `--embed` | Now a flag on `describe`; was standalone command only |

### Options Removed in v4.5

| Old Option | Status | Workaround / Notes |
|------------|--------|-------------------|
| `--resume <wf_dir>` / `-r` | ❌ REMOVED | **Implicit resume:** run `describe <source_dir>` again; already-described images are skipped automatically. BUT: you must know the original source directory, not the workspace path. No way to say `idt describe 09.idtw` to resume. |
| `--output-dir <dir>` / `-o` | ❌ REMOVED | Workspace auto-placed under `~/Documents/idt/` (configurable via `idt config --set workspace_root=…`) |
| `--steps <list>` | ❌ REMOVED | No step control; describe always runs the full pipeline (video extract → copy → describe → export). Use `--no-video` and `--no-export` to suppress some steps. |
| `--api-key-file <file>` | ❌ REMOVED | API keys must be in environment variables (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`) — no file-based key support |
| `--timeout <seconds>` | ❌ REMOVED | No per-request timeout override |
| `--name <name>` | ❌ REMOVED | Workspace named from source folder leaf; use `--workspace NAME` to override |
| `--download` / `-d` / `--url` | ❌ REMOVED | Replaced by `idt download <url>` command |
| `--min-size <size>` | ❌ REMOVED | Available as `idt download --min-size WxH` |
| `--max-images <n>` | ❌ REMOVED | Available as `idt download --max N` |
| `--no-alt-text` | ❌ REMOVED | No equivalent |
| `--preserve-descriptions` | ❌ REMOVED | Not needed: already-described images automatically skipped |
| `--link-images` | ❌ REMOVED | Workspaces always copy images; linking not supported |
| `--force-copy` | ❌ REMOVED | No equivalent |
| `--batch` | ❌ REMOVED | Use `--quiet` |
| `--progress-status` | ❌ REMOVED | Progress shown by default |
| `--view-results` | ❌ REMOVED | No equivalent |
| `--dry-run` (on describe) | ❌ REMOVED | No dry-run for describe; `--dry-run` exists only on `embed` |
| `--config-workflow` / `--config-wf` | ❌ REMOVED | No per-invocation config overrides |
| `--config-image-describer` / `--config-id` | ❌ REMOVED | Prompts come from `~/.idt/config.json` |
| `--config-video` | ❌ REMOVED | No video extraction config override |
| `--geocode-cache <file>` | ❌ REMOVED | Cache fixed at `~/.idt/geocode_cache.json` |

### Options New in v4.5

| New Option | Command | Purpose |
|------------|---------|---------|
| `--workspace NAME\|PATH` | `describe` | Explicit workspace name or path |
| `--stdin` / `-` | `describe` | Read image paths from stdin (pipe mode) |
| `--project DIR` | `describe` | Project root when reading from stdin |
| `--no-video` | `describe` | Skip video frame extraction |
| `--video-interval SECONDS` | `describe` | Control frame extraction interval |
| `--no-export` | `describe` | Skip auto-HTML report |
| `--set KEY=VALUE` | `config` | Set persistent config values |
| `--interval SECONDS` | `watch` | Polling interval |
| `--min-size WxH` | `download` | Image size filter |
| `--max N` | `download` | Max download count |
| `--force` | `embed` | Re-embed already-embedded images |
| `--scene THRESHOLD` | `video` | Scene-change detection mode |
| `--max-frames N` | `video` | Limit frames per video |
| `--all` | `status`, `stats` | Scan entire directory tree |

---

## Real Bugs Found During Testing

### Bug 1: `combine --output <file>` Encoding Crash (Critical)
**Command:** `idt combine ~/Documents/idt --output out.csv`  
**Error:** `'charmap' codec can't encode character '→' in position 26: character maps to <undefined>`  
**Root cause:** `cmd_combine` in [`cli/main.py:1184`](../cli/main.py) opens the output file without specifying `encoding="utf-8"`, defaulting to Windows cp1252 which cannot encode Unicode characters (→, emoji, curly quotes, etc.) commonly found in AI-generated descriptions.

```python
# cli/main.py line 1184 — current (broken):
with open(out_path, "w", newline="", encoding="utf-8") as f:  # ← encoding missing, add utf-8
```

The exact line to change:
```python
# BEFORE (line ~1184):
        with open(out_path, "w", newline="") as f:
# AFTER:
        with open(out_path, "w", newline="", encoding="utf-8") as f:
```

**Workaround:** Pipe to stdout and redirect: `idt combine ~/Documents/idt > out.csv` (stdout is UTF-8 in most environments).  
**Verify fix:** `idt combine "C:\Users\kelly\Documents\idt" --output test.csv` — must not raise charmap error; `09.idtw` descriptions contain `→` characters.

### Bug 2: `show <file-inside-workspace-images/>` Fails
**Command:** `idt show 09.idtw/images/849...jpeg`  
**Error:** `No description found for: 849adfa4fe72c4fd8f6482ecfde0a4a1.jpeg`  
**Root cause:** `_show_file()` at [`cli/main.py:870`](../cli/main.py) walks up the directory tree looking for a sibling `.idtw` bundle (`candidate.parent / (candidate.name + ".idtw")`). When the file is INSIDE the bundle (`09.idtw/images/`), the walk-up checks for `09.idtw.idtw` (doesn't exist) and misses the bundle entirely. The function never checks whether an ancestor IS a bundle itself.

```python
# cli/main.py _show_file — the walk-up loop (lines ~879-897):
candidate = target.parent
while True:
    sibling = candidate.parent / (candidate.name + ".idtw")   # only checks sibling
    if Workspace.is_bundle(sibling): ...                       # misses self-as-bundle
    ...
    candidate = candidate.parent
```

**Fix:** Add a `Workspace.is_bundle(candidate)` check inside the loop — if `candidate` itself is a bundle, search its items for the file.

**Workaround:** Pass the workspace directory: `idt show 09.idtw` (lists all).  
**Verify fix:** `idt show "C:\Users\kelly\Documents\idt\09.idtw\images\849adfa4fe72c4fd8f6482ecfde0a4a1.jpeg"` — must print the description, not "No description found".

### Bug 3: `show <source-file>` Fails When Workspace Is in Mirrored Location
**Confirmed by code inspection** (source files at `\\ford\home\...` unavailable for live test).  
**Root cause:** `_show_file()` at [`cli/main.py:870`](../cli/main.py) only checks for sibling bundles (`Photos\2025\09.idtw` next to `Photos\2025\09\`). When the workspace was placed in the mirrored location (`~/Documents/idt/09.idtw`), the sibling check finds nothing and the function returns "No description found."

The mirror-lookup logic already exists in `_find_workspace()` at [`cli/main.py:185`](../cli/main.py) — it checks `~/Documents/idt/<foldername>.idtw` — but `_show_file()` never calls it.

```python
# _find_workspace() already handles mirrored lookup (line ~185):
root = UserConfig.load().workspace_root_path()
mirrored = _mirror_source_path(p, root)
candidate = mirrored.with_name(mirrored.name + ".idtw")
if Workspace.is_bundle(candidate):
    return Workspace.open(candidate)

# _show_file() does NOT call _find_workspace() — it only walks siblings
```

**Fix:** At the end of `_show_file()`'s walk-up loop (after the `break`), call `_find_workspace(str(target.parent))` as a last-resort lookup, then search that workspace's items for the target filename.  
**Workaround:** Pass workspace directly: `idt show 09.idtw`.

### Bug 4: `show <dir>` Unicode Encoding Error on Console (Non-Fatal but Exits 1)
**Command:** `idt show test_cli/`  
**Error:** `Error: 'charmap' codec can't encode characters in position 1050-1051: character maps to <undefined>` — command exits 1, partial output already printed  
**Root cause:** AI descriptions contain characters outside Windows cp1252 (→, em dash, smart quotes). `_print_item()` at [`cli/main.py:942`](../cli/main.py) calls `print(desc.text)` which goes to `sys.stdout`. On Windows, `sys.stdout.encoding` defaults to cp1252 when writing to a console, raising `UnicodeEncodeError`. The exception propagates to `main()`'s outer try/except at [`cli/main.py:1867`](../cli/main.py), which prints the error and exits 1 — cutting off any remaining items.

**Fix:** Add this near the top of `main()` in `cli/main.py` (before `args = parser.parse_args()`):
```python
import sys, io
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
```

This applies to `show`, `combine` stdout output, and any other command that prints descriptions.  
**Workaround:** `idt show 09.idtw --json | Out-File -Encoding utf8 out.json`

### Bug 5: INFO Noise on Every Command (Cosmetic)
**All commands** emit `INFO: Using config from IDT_CONFIG_DIR environment variable` to stderr before any output.  
**Root cause:** The `IDT_CONFIG_DIR` environment variable is set on the test machine (`C:\idt\scripts\`). The legacy `scripts/config_loader.py` logs this at INFO level when imported. The new `idt_core/config.py` imports or triggers `config_loader` as part of prompt-loading, so it fires on every command including `idt models` and `idt prompts`.  
**Find it:** `grep -n "IDT_CONFIG_DIR\|INFO.*config" scripts/config_loader.py`  
**Impact:** Pollutes all scripted output; confuses users who see log noise before command output.  
**Fix:** Change the log call in `scripts/config_loader.py` from `logging.info(...)` to `logging.debug(...)` for the `IDT_CONFIG_DIR` message, or suppress it entirely when called from `idt_core` context.

### Bug 6: `stats` Has No Replacement for Old Workflow Performance Metrics
**Not a crash** — both old and new `stats` commands run successfully — but they measure completely different things:
- **Old `idt stats`** (`analysis/stats_analysis.py`): Workflow run timing, images-per-hour throughput, per-step duration (video extraction, conversion, AI description, HTML generation). Wrote CSV/JSON/text to `analysis/results/`.  
- **New `idt stats`** (`cli/main.py:1346`, `cmd_stats`): Token counts and estimated API cost per provider/model. Shows "n/a" for all local models (Ollama, Florence) since they don't report tokens.  
**Impact:** Operations/performance monitoring is gone. API cost tracking is new. No overlap in purpose. `analysis/stats_analysis.py` still exists in source but is not reachable from the CLI.

### Architecture Gap: Resume Requires Source Directory, Not Workspace Path
**`idt describe --resume 09.idtw` → error: unrecognized arguments: --resume**  
The `--resume` flag is gone. The design intent is that `describe <source_dir>` implicitly resumes (already-described items are skipped). But this requires knowing the original source directory. The workspace's `manifest.json` records it under `sources[].path`, but there's no CLI path that reads from the workspace and continues without requiring the user to re-specify the source.

The relevant code flow:
- `cmd_describe` in `cli/main.py:220` — requires `args.source` to be a real directory (`source.is_dir()` check at line 232)
- `_open_or_create_workspace()` at line 163 — resolves the workspace from source path  
- Queue filtering at line 293: `queue = [i for i in all_items if not i.described]` — skips described already

**Fix path:** Add a mode where `source` can be a `.idtw` bundle path. If `Workspace.is_bundle(source_path)`, open it directly and iterate `ws.items()` with the existing filtering. The `sources` in `manifest.json` can be displayed for reference but aren't needed for the run since all images are already copied into the bundle.

---

## Architecture Gaps (Design-Level Issues)

### Resume UX Gap
**Symptom:** `idt describe --resume 09.idtw` fails; `--resume` flag does not exist.  
**Design intent:** Resume is implicit — run `describe <source_dir>` again; already-described images are skipped.  
**Actual gap:** Users must remember the original source directory path. The workspace knows its sources (in `manifest.json`), but there is no `idt describe --workspace 09.idtw` invocation that would load the source from the manifest and continue.  
**Workaround:** Check `idt status 09.idtw` to see the source path, then run `idt describe <that-path>`.  
**Fix:** Add `idt describe --workspace 09.idtw` (or `idt resume 09.idtw`) that reads sources from manifest and describes remaining items without requiring the user to specify a source directory.

### `download` and `video` and `watch` Use Legacy `.idt/` Model
The `download`, `video`, and `watch` commands create `.idt/` sidecar directories next to the source folder — the old project model, not the new `.idtw` workspace bundle. This means:
- Files described via `download` or `video --describe` are NOT in a workspace and cannot be managed by `status`, `show`, `embed`, or `export` unless the user also points these commands at the `.idt/` project (which works via the legacy fallback path).
- Results from `video` and `download` workflows are not consolidated in `status --all` unless a `.idt/` sibling dir is present.

### `manage-models` Install/Remove Capability Gone
The old CLI included `manage-models install <model>` (via `ollama pull`), `manage-models remove`, and `manage-models recommend` to help users get set up with Ollama. These are completely gone. New users must know to use `ollama pull <model>` directly, with no IDT guidance.

### `contentreview` Gone with No Replacement
The old `contentreview` command (via `analysis/content_analysis.py`) analyzed description quality — checking for vagueness, completeness, and consistency. There is no equivalent in v4.5. This was used for post-processing quality audits.

### `api-key-file` Gone — Env Vars Only
The old `--api-key-file <file>` option allowed passing API keys via a file (useful for scripts, automation, and keeping keys out of shell history). The new CLI requires `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` environment variables only.

---

## Summary Scorecard

| Category | Count |
|----------|-------|
| Commands confirmed working ✅ | 14 |
| Commands with bugs or partial failures ⚠️ | 3 |
| Commands confirmed broken ❌ | 2 (show bugs) |
| Old commands fully removed — no equivalent | 7 |
| Old commands replaced with breaking changes | 8 |
| Old options removed from describe/workflow | 17 |
| New options added in v4.5 | 14 |
| Bugs confirmed by live testing | 4 |
| Architecture gaps (design-level) | 4 |

---

## Recommended Fix Priority

| Priority | Item | Effort |
|----------|------|--------|
| P0 | `combine --output file` encoding crash | 1 line — add `encoding="utf-8"` |
| P0 | `show` / `combine` stdout Unicode crash | 1–2 lines — add `errors='replace'` or reconfigure stdout |
| P0 | Resume UX: `idt describe --workspace <bundle>` | Medium — add workspace-only mode to `describe` |
| P1 | `show <file-inside-workspace>` fails | Small — fix walk-up to detect self-bundle |
| P1 | `show <original-source-file>` fails for mirrored workspaces | Small — call `_find_workspace` in `_show_file` |
| P1 | INFO noise on every command | Small — suppress or downgrade log level |
| P2 | `manage-models install/remove` gone | Medium — wire `ollama pull/rm` |
| P2 | `stats` lost performance/timing capability | Medium — restore old analysis or add `idt perf` |
| P2 | `version` command gone | Trivial — add `idt version` to `cli/main.py` |
| P2 | `contentreview` gone | Large — restore or defer |
| P3 | `download`/`video`/`watch` use legacy `.idt/` not workspace | Large architectural change |
| P3 | `--api-key-file` gone | Small — re-add as option |

---

*Document based on live execution testing of `BuildAndRelease\WinBuilds\dist_all\bin\idt.exe` on 2026-06-23.*
