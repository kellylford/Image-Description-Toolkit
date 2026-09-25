# Session summary: Apple Intelligence provider (`apple`)

**Date:** 9/24/2026
**Issue:** #324 §2 "Apple on-device model with image input (macOS 27)"
**Precursors:** `2026-07-08-macos27-ondevice-image-research.md` (design),
`2026-09-24-fm-serve-verification.md` (measurements this is built on)
**Status:** Implemented and exercised on macOS 27.2. Not built as a frozen app, not run on
Windows or on a Mac without the license accepted.

---

## What was built

A fifth provider, keyed `apple` and shown as **Apple Intelligence**, running Apple's on-device
model through the macOS 27 `fm serve` endpoint. No API key, no account, no network, no cost.

It reaches every surface, matching how `claude-code` shipped in #325: `idt describe` /
`download` / `video` / `watch`, `idt chat`, `idt models`, `idt guideme`, ImageDescriber
(describe, follow-up, chat, prompt editor, settings) and the standalone IDT Chat app.

## Decisions

**Own HTTP client, not the OpenAI SDK with a `base_url`.** The endpoint is OpenAI-shaped but
three behaviours differ, two silently (measured 9/24, full table in the verification doc):

| Divergence | Consequence if ignored |
|---|---|
| `stream` defaults to **true** | A request without the field returns `text/event-stream`; a JSON parse fails on an empty body |
| `max_tokens` ignored, `max_completion_tokens` honoured | No length control at all, and no error |
| Requests serialize server-side | A worker pool adds latency, never throughput |

Each is asserted directly in `test_apple_provider.py`, because none of them would be caught by a
test that only checks a description came back.

**Auto-spawned server on a Unix socket** (Kelly's call, offered against "user runs `fm serve`").
One `FmServer` per process, started lazily on first use, health-checked at `/health`, killed by
`atexit`. A socket rather than a TCP port: the CLI's own help recommends it for local bindings,
and it needs no port allocation or firewall prompt. The socket lives under `/tmp`, not the
default temp dir — macOS caps a socket path near 104 bytes and the per-user `/var/folders` path
eats most of that. There is a test for the length.

**`system` only.** `fm` also lists `pcc` (Private Cloud Compute), but it reports "not available
in this context. Please use the Terminal app." for any process that is not Terminal — so it would
be a picker entry that can never work.

**No downscaling and no format conversion beyond GIF/WebP.** The server resizes internally: a
640×480 and a 9000×6750 JPEG both reported ~206 prompt tokens. This is the one provider that
needs none of the size handling `claude-code` required.

**The license gate is reported, never automated.** `sudo fm license` is machine-wide and needs an
administrator. `check_ready()` detects it and returns the exact command; pickers hide the
provider on machines that cannot run it at all (wrong OS or no `fm`), which is the existing
`_GATED_PROVIDERS` rule MLX and Claude Code already use.

## Two bugs found while building

1. **`fm models` exits non-zero on a correctly licensed Mac**, because `pcc` is always
   unavailable to us. A first cut gated on the exit code and reported this very machine as
   unlicensed. The check now reads the output. Regression test:
   `test_licensed_mac_is_recognised_despite_a_nonzero_exit`.
2. **`default_model` is global while `--provider` is per-run.** `idt describe --provider apple`
   on a machine whose default is an Ollama model sent `moondream` and got an HTTP 400 per image.
   Added `_resolve_model()` in `cli/main.py`, applied at all five call sites, which falls back to
   the provider's own default for a fixed single-model provider.
   **`claude-code` has the same latent bug and was deliberately left alone** — coercing a model
   name there is a behaviour change outside this task, and Kelly may prefer a warning.

## Review round (commit aa84546)

An independent high-effort review of the first commit found seven issues, all confirmed and fixed.
Full write-up in the PR comment; the ones worth remembering:

1. **`context_window` was invented at 65,536; the real window is 4,096** — measured by probing the
   server (4,060 tokens accepted, 5,060 refused). The chat budgeter trims against it, so the wrong
   number meant conversations growing to sixteen times what the model can hold. This also broke
   `catalog.py`'s own rule that an unknown value stays `None` rather than becoming a guess.
2. **A too-long conversation arrives as HTTP 500**, which `chat/errors.py` classifies as a
   retryable server error — and the retry resends the same oversized transcript. Now rewritten as a
   permanent error naming the fix.
3. **Socket timeouts escaped as bare `OSError`**, past every `except AppleFMError`, so
   `describe_image` raised an unclassified exception instead of a `ProviderError`.
4. **A force-quit orphaned `fm serve`** — reproduced with SIGKILL. `atexit` cannot run and the
   child has its own session, so every crash left one holding the model in memory. Runs now record
   their pid and reap dead owners' directories; only directories this user owns are trusted,
   because `/tmp` is world-writable.
5. **An unavailable model left its server running**, so the second image got a raw HTTP error
   instead of "turn on Apple Intelligence".
6. **`describe()` had no output cap** unlike every other provider; now 600 tokens.
7. **`_resolve_model` shipped untested.**

## Files

New: `idt_core/providers/apple.py`, `idt_core/chat/apple.py`,
`pytest_tests/unit/test_apple_provider.py`, this file, and the verification doc.

Changed: `idt_core/providers/{registry,catalog}.py`, `idt_core/chat/{providers,tokens}.py`,
`cli/{main,guide}.py`, `imagedescriber/{ai_providers,dialogs_wx,chat_window_wx,prompt_editor_dialog,configure_dialog,imagedescriber_wx,workers_wx}.py`,
`chatapp/chat_app_wx.py`, all three `.spec` files, `CLAUDE.md`, `README.md`,
`docs/USER_GUIDE.md`, `docs/DEVELOPER_GUIDE.md`, and three existing test files.

## Test results

- `pytest pytest_tests/` in the wx environment (`imagedescriber/.venv`, `IDT_REQUIRE_WX=1`):
  **1821 passed, 49 skipped** after the review round (1805 before it). Includes the ImageDescriber
  launch smoke test. The suite caught one of its own during that round:
  `test_source_reading_hygiene` flagged three `write_text` calls with no encoding.
- Same suite in `.venv` (no wx): 1431 passed, 303 skipped, 1 failed —
  `test_imagedescriber_launches`, which **fails identically on a clean tree** because that venv
  has no wxPython. Verified by stashing.
- `BuildAndRelease/check_spec_completeness.py`: all three specs complete.
- New tests: 29 in `test_apple_provider.py`, 5 chat-format tests, 1 picker-gating test, and an
  `_AppleDriver` in the provider contract suite (which fails by name if a provider ships without
  one).
- One existing test updated: `test_a_broken_availability_check_shows_too_much_not_too_little`
  pinned the full picker list literally; it now derives it from `_PICKER_PROVIDERS`.

Measured on this machine (macOS 27.2, Apple Silicon):

| Path | Result |
|---|---|
| `idt describe` over 2 images | 12.2s total including server start |
| Warm describe, same process | 1.0–1.2s per image |
| Cold describe (server start + model page-in) | ~5s |
| `idt chat --provider apple --message ...` | answered correctly |
| `ChatEngine` + `AppleChatProvider` | ChatStarted → ChatDelta → ChatUsage → ChatFinished, tokens recorded |
| Server reuse across 3 provider instances | one socket, no respawn |
| ImageDescriber dialogs (Processing Options, Follow-up, Chat) | Apple selected, model listed, `provider`/`model` round-trip as `apple`/`system` |
| IDT Chat `ProviderDialog` | offered, model listed, status line correct |
| GUI `describe_image()` | 3.2s, usage recorded |

## What was NOT tested

- ~~**Frozen builds.**~~ **Closed 9/25/2026:** Kelly ran the signed build and reported
  it working, after a hardened-runtime test here (a copy signed with the real Developer
  ID, `fm serve` spawning from it, a description returned). The notarized artifact from
  the v4.6.0 release was then run successfully too, which was the last unverified link.
- **Originally:** nothing was built with PyInstaller. The spec entries are present and
  `check_spec_completeness.py` passes, but no `.app`/`.exe` was produced or run.
- **Windows and Intel Macs.** The gating is unit-tested by monkeypatching `platform`, not by
  running there. On those machines the provider should simply be absent.
- **An unlicensed Mac.** The terms were accepted on this machine before the code existed, so the
  `sudo fm license` path is covered by fakes only — the real refusal banner was captured before
  acceptance and is reproduced verbatim in the test.
- **Apple Intelligence switched off**, or its model still downloading. `_check_model_available`
  handles the shape the server reports, tested with a synthetic payload.
- **A long batch.** The longest real run was 2 images. Throughput, thermals and memory over 100+
  images are unknown — the natural comparison is the 103-image `claude-code` measurement.
- **Description quality on real photographs.** Both test images are small synthetic
  illustrations. No comparison has been made against the MLX default
  (`mlx-community/Qwen3-VL-4B-Instruct-4bit`), and that comparison should decide whether this is
  presented as a headline provider or a fallback. The USER_GUIDE text deliberately claims speed
  and privacy, not quality.
- **A server dying mid-batch.** `ensure_running` re-spawns on the next request by design, but
  that path was not forced.
- **HEIC end to end through this provider.** `load_for_api` converts before the provider sees
  the bytes, and that conversion is covered elsewhere, but no HEIC file was run through `apple`.

## Environment changes

- `pytest`, `pytest-mock` and `pytest-cov` were installed into `imagedescriber/.venv` so the
  wx-dependent tests could actually run. Nothing else in that environment changed.
- `sudo fm license` was accepted on this Mac earlier in the day (machine-wide, persistent).
