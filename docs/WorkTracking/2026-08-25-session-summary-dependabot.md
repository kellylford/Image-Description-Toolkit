# 2026-08-25 — Dependabot dependency sweep

## What happened

Dependabot opened 11 PRs (#287–#297), all pip requirement bumps across four
packages. As in the [8/18 sweep](2026-08-18-session-summary-dependabot.md), they
overlapped: seven were strict subsets of the other four.

All 11 were green on all seven CI checks. One of them was still broken.

## The overlap

| Superset PR | Bump | Files | Subsets superseded |
|----|------|-------|-----|
| #297 | openai 3.1.0 → 3.3.1 | root, chatapp, idt, imagedescriber, pyproject.toml | #288, #292 |
| #296 | anthropic 0.122.0 → 1.0.0 | root, chatapp, idt, imagedescriber, pyproject.toml | #289, #294 |
| #290 | pyinstaller 6.22.0 → 6.22.2 | root, chatapp, idt, imagedescriber | #291, #295 |
| #293 | mlx-vlm 0.6.13 → 0.6.15 | root, imagedescriber | #287 |

## anthropic 0.x → 1.0.0 broke `idt chat --provider claude --temperature`

The one bump needing real scrutiny, and the one that found a live bug.

anthropic 1.0.0 removed `temperature` / `top_p` / `top_k`. They are not rejected
server-side — they are gone from the method signatures, so passing one raises
before any request is sent:

```
TypeError: Messages.stream() got an unexpected keyword argument 'temperature'
```

`ClaudeChatProvider.chat()` forwarded `request.temperature` straight into
`client.messages.stream()`.

**This was already live.** Every constraint in this repo is `>=`, so
`anthropic>=0.122.0` already resolved to 1.0.0 on any fresh install. The floor
bump did not introduce the crash; it only made the floor honest. CI stayed green
because no test exercises the Claude provider against a real SDK — the unit tests
cover `format_for_claude` and `_max_output`, never the kwargs dict.

Fixed in #298: kwargs now build in `ClaudeChatProvider._request_kwargs()`, which
omits the sampling parameters and gives the regression a seam to test without a
client. `idt chat` warns when `--temperature` is passed for Claude, following the
existing `--web-search` precedent, rather than dropping it silently. The flag
still works for Ollama and OpenAI.

### Rest of the 1.x breaking-change list — checked, none applied

- `requires-python` is already `>=3.11` (1.x needs ≥3.10).
- No Text Completions (`completions.create` / `HUMAN_PROMPT` / `AI_PROMPT`). The
  `chat.completions.create` hits are all OpenAI.
- No `.with_raw_response` on an Anthropic client. Those hits in `tools/` are the
  OpenAI client.
- No `httpx` objects crossing the SDK boundary. The `httpx.Client()` instances in
  `tools/capture_raw_response.py` and `tools/capture_empty_response_loop.py` go
  to `OpenAI(http_client=...)`, which still uses `httpx`.
- No Bedrock or Vertex clients, no `BetaBase64PDFBlockParam`, no `READ_MAX_BYTES`,
  no `compaction_control`, no `parse(stream=)`, no raw `output_format={...}`.
- The other two Anthropic call sites — `idt_core/providers/claude.py` and
  `imagedescriber/ai_providers.py` — send no sampling parameters.
- The `temperature` / `top_k` / `top_p` in `model_settings` are Ollama options
  and never reach Claude.

Client constructions (`api_key=`, `timeout=`, `max_retries=`) and
`models.list(limit=)` are unchanged in 1.x.

## Testing

Full suite on the fix: **1722 passed, 43 skipped.**

Verified against a real `anthropic==1.0.0` install in an isolated venv, not from
the changelog:

- `temperature` is absent from the `messages.create` / `messages.stream`
  signatures, and passing it raises `TypeError`.
- Both client constructor shapes this repo uses still work.
- End-to-end: `ClaudeChatProvider.chat()` with `temperature=0.2` on the fixed
  code reaches the API (`AuthenticationError` on a fake key) instead of raising
  `TypeError`.

## Merge order

#298 (the fix) first, then #297, #290, #293. #296 then conflicted with #297 on
the same lines, so it was reapplied across all five manifests as #299, which also
realigned the comment columns the shorter version string had knocked out.

## What was NOT tested

- **mlx-vlm 0.6.15** is gated to `darwin` + `arm64` and cannot be installed on
  this Windows machine. Left to the macOS Apple Silicon CI job.
- **pyinstaller 6.22.2** — patch bump, not separately exercised beyond the
  `build-windows` and Apple Silicon CI builds.
- **openai 3.1.0 → 3.3.1** — minor bump within the major already in use since the
  8/18 sweep; call surface not re-audited.
- No live API calls against either provider (no billing).
