# 2026-08-16 — Issue #267: live Claude/OpenAI model lists

Replaced the hardcoded `CLAUDE_MODELS` / `OPENAI_MODELS` lists with a live
listing from each provider's `/v1/models` endpoint, merged against the curated
metadata we already had. All three surfaces (CLI, IDT Chat, ImageDescriber)
now show what the account can actually use.

## The problem

Both lists were annotated "sourced from the SDK, updated July 2026" and
maintained by hand. A model released after that date was invisible until
someone edited a file and cut a build; a retired one stayed in every picker and
failed at request time with an API error. Ollama had been dynamic all along.

Neither API reports context window, max output, cost, or capability flags — so
the fix is a hybrid, not a straight swap.

## Design

**The live list decides what exists; the curated tables decide what we know.**
A live listing contributes existence, a display name, and a creation timestamp
for ordering — never limits. That invariant is load-bearing: if a fetched entry
could blank a recorded `context_window`, the chat token budgeter would silently
drop to a flat guess with nothing anywhere to notice.

Unrecognised models still appear, labelled "new — details unknown", with
`context_window`/`max_output` left `None` so they flow through each caller's
documented fallback rather than an invented number.

Three new seams, split on testability:

| File | Role |
|---|---|
| `idt_core/providers/model_cache.py` (new) | Pure disk. One file per provider under `~/.idt/models/`, keyed by a hash of the API key. |
| `idt_core/providers/catalog.py` (new) | `ModelEntry`, merge, ordering, `cached_models`, `model_entry`, `refresh_models`. Zero filesystem in its merge tests. |
| `claude.list_models_live()` / `openai_provider.list_models_live()` | The per-SDK fetchers, with injectable clients. |

Read-path cost, cheapest first: `model_entry()` does no I/O at all (it runs on
every chat turn via `registry.model_limits`); `cached_models()` reads disk once
per process and is safe on the UI thread; `refresh_models()` blocks and is for
worker threads only.

### Decisions

- **24h TTL**, cache-first paint, background refresh. `idt models --refresh` forces.
- **`keep=`** on every list-producing call. Every filter can remove the model the
  user has selected; without this a picker silently falls back to index 0 and
  changes their model with no message.
- **Retirement** only when a fetch succeeded and returned ≥3 ids. An empty or
  implausibly short response is treated as failure, so it can neither empty a
  picker nor cache that emptiness for a day.
- **`supports_vision` is tri-state** (`None` = unknown). Claiming `True` for an
  unknown OpenAI model would put a text-only model in the describe picker — the
  same shape as issue #227.
- **OpenAI filter**: whole-token denylist (never substring — that would hide a
  future `gpt-6-audio-native`) plus dated-snapshot collapsing. Verified against a
  real account: **126 ids in, 45 out.**

## Files changed

**New:** `idt_core/providers/catalog.py`, `idt_core/providers/model_cache.py`,
plus 7 test files.

**Core:** `registry.model_limits` delegates to the catalog (signature and `None`
contract unchanged); `claude.py` / `openai_provider.py` gained live fetchers and
the OpenAI filter; `project.py` stopped hardcoding `claude-opus-4-6`.

**CLI:** `cmd_models` rewritten (now `--refresh` and `--all`);
`_chat_default_model` falls back when the module default has been retired;
`guide.py` shows display names.

**IDT Chat:** `_populate_models` paints from cache, then refreshes on a worker
with the existing generation-token guard.

**ImageDescriber:** `ai_providers.py` gained `list_models` / `model_info` /
`refresh_models_from_apis` as the choke point; four pickers, the description
hint, and the context-window fetch now route through them; the startup refresh
moved off the UI thread.

**Config:** two new `hiddenimports` entries in all three specs, three coverage
floors added/raised, and an autouse cache-isolation fixture in `conftest.py`.

**Release 4.5.1 opened.** Version bumped in all three files the CI validate job
gates on (`VERSION`, `idt_core/__init__.py`, `pyproject.toml`) — verified by
running CI's own comparison locally. `docs/release-notes-v4.5.1.md` written for a
first-time reader per the established style, with asset filenames checked against
what `release.yml` actually publishes.

**Docs:** the user guide's `idt models` reference and both cloud provider
sections now describe live listing; `docs/README.md` was rewritten — it dated
from v3.5.0-beta and pointed at `CLI_REFERENCE.md`, `PROMPT_WRITING_GUIDE.md` and
`WHATS_NEW_v3.5.0.md`, none of which exist. `CLI_INVENTORY.md` was deliberately
left alone: it is a dated audit of live test runs, not a living reference, and
editing its recorded results would misrepresent when they were taken.

## Bugs found and fixed along the way

1. **`cmd_models` read `os.environ` directly**, so anyone whose key lived in the
   Windows Credential Manager or the config file was told they had no key. Hit
   this live during verification.
2. **OpenAI's `get_available_models` intersected the live response with the
   hardcoded list** — a live query that can only subtract can never surface a new
   model, which is the one thing listing exists to do. It looked like it was
   already doing the right thing.
3. **"Claude doesn't have a models endpoint"** — a comment that had outlived the
   fact.
4. **`refresh_models` could wedge a provider permanently.** The in-flight marker
   was released in an `except Exception` and in a `finally` on an *inner* block,
   so a `BaseException` (Ctrl+C at the CLI, `SystemExit`) skipped both and every
   later refresh returned `None` silently. Found by accident via `pytest.fail`;
   now has an intentional test.
5. **Cross-provider model leakage in three GUI pickers.** My own bug, introduced
   with `keep=`: the value passed was the *configured* model, which belongs to
   whichever provider is configured. Switching to Claude listed and selected
   "gpt-5.2"; the prompt editor put the Ollama default into both cloud lists.
   Only visible by opening the dialogs and switching provider.
6. **Hardcoded `SetStringSelection("gpt-4o")`** in two dialogs, quietly starting
   every batch and chat on a legacy model.
7. **`get_claude_api_id_from_display`** would have returned a *display string* as
   an API id for any live-only model. No callers; deleted rather than left as a
   trap that works until it doesn't.
8. **`_fetch_context_window_bg`** reimplemented the registry's fallback chain
   inline with its own `200_000`/`128_000`/`32_768`, so the token gauge could
   disagree with the budgeter that actually drops turns. Now one call to
   `tokens.context_window_for`.

## Testing

**1583 passed, 15 skipped, 0 failed** — 169 of them new here, and another 62
restored by the hygiene fix below. Coverage 30.59% → 35.35%. New floors: `catalog.py` 90 (measures ~95),
`model_cache.py` 95 (98.57); raised `claude.py` 45→70, `openai_provider.py`
52→76.

Verified live against real APIs: Anthropic returned 10 of the 13 curated models
(three the account cannot reach were retired automatically); OpenAI 126 → 45,
and `--all` confirms all 126 are still reachable. Cold run 6.7s, warm 0.37s.

**Frozen build verified**, which is the check that matters for the two new
modules: built `idt.exe` and ran `models --provider openai`,
`--provider anthropic --refresh`, `--all` and `--json` against it. No
`ModuleNotFoundError`, both the cached and live paths work packaged.

`model_limits` measured at 10,000 lookups in 0.047s with the cache directory
pointed at a nonexistent drive — the hot path really is free of I/O.

All four ImageDescriber pickers and the IDT Chat dialog were driven headlessly
through provider round-trips; that is how bug 5 below was found.

### Not tested

- **macOS.** Windows only this session.
- **The ImageDescriber and IDT Chat frozen builds.** Only `idt.exe` was built;
  the other two specs got the same two-line `hiddenimports` addition and the
  static spec-completeness checker passes for all three, but neither app was
  packaged and launched.
- **The GUI as a running application.** Dialogs were constructed and driven
  headlessly under a real `wx.App`, which is what caught the cross-provider
  leak, but nobody clicked through the actual window.
- **The 24h TTL expiring in real time** — tested by manipulating the stored
  timestamp, not by waiting.
- **Genuine multi-process cache contention.** The unique-temp-name fix makes it
  safe; the test is 8 threads, which is the honest bar, and the test says so.
- **A real newly-released model appearing.** The "new — details unknown" path is
  tested with synthetic ids; it will get its real trial when a provider next
  ships something.

### Also fixed: a test that was silently not running

`test_source_reading_hygiene.py` excluded `.claude` from its scan by matching
against *absolute* path parts. Checked out under `.claude/worktrees/` — which is
where Claude Code puts worktrees — every file in the repo matched the exclusion,
so the scan found nothing and `test_there_are_tests_to_scan` failed. Confirmed
identical on the unmodified base commit (`baa04b4`).

Now matched against the repo-relative path. The count tells the story: the file
went from **1 collected test to 64**. The other 63 were parametrised over an
empty scan, so they had been passing vacuously in every worktree. They pass for
real now, which also confirms the new files here use `encoding=` properly.

Its "is this scan vacuous" guard is the only reason this was visible at all.

### On the ai_providers.py coverage floor

It measures 61.80% locally on the *unmodified* base commit against a 66.0 floor,
while CI passes on main. The difference is environmental: this machine has Ollama
running and both API keys resolvable, so the success branches execute, while CI
has neither and covers the file's many fallback branches instead. Not a
regression — after this work it measures 66.12% locally.
