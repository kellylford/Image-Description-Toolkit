# 2026-08-18 — Dependabot dependency sweep

## What happened

Dependabot opened 12 PRs (#273–#284), all pip requirement bumps. They overlapped
heavily — six were strict subsets of the other six, and several touched the exact
same lines of the same files, so merging them individually would have produced a
cascade of rebases and conflicts. Applied the union as a single commit instead.

## The overlap

Superset PRs (everything is covered by these six):

| PR | Bump | Files |
|----|------|-------|
| #279 | openai 2.53.0 → 3.1.0 | root, chatapp, idt, imagedescriber, pyproject.toml |
| #281 | anthropic 0.121.0 → 0.122.0 | root, chatapp, idt, imagedescriber, pyproject.toml |
| #282 | torch 2.12.1 / 2.0.0 → 2.13.0 | root, imagedescriber |
| #283 | mlx-vlm 0.6.4 → 0.6.13 | root, imagedescriber |
| #274 | pillow-heif 1.4.0 → 1.5.0 | idt (2 occurrences) |
| #278 | numpy 2.5.0 → 2.5.2 | imagedescriber |

Strict subsets, superseded: #273 and #275 (openai) ⊂ #279; #276 and #280
(anthropic) ⊂ #281; #277 (mlx-vlm) ⊂ #283; #284 (torch) ⊂ #282.

Net change: 17 lines across 5 files.

## The openai 2.x → 3.x major bump

The only change needing real scrutiny. Every constraint in this repo is `>=`, so
CI already resolved openai 3.2.0 before these PRs existed — all six CI checks were
green on all 12 PRs, meaning 3.x was already being exercised.

Verified the call surface directly against openai 3.2.0. The code touches only:

- `OpenAI(api_key=..., timeout=...)`
- `client.models.list()`
- `client.chat.completions.create(model=, messages=, stream=, stream_options=,
  max_completion_tokens=, temperature=, max_tokens=)`
- exceptions `NotFoundError`, `AuthenticationError`, `BadRequestError`,
  `RateLimitError` (in `tools/test_openai_models.py`)

All present and unchanged in 3.2.0. Same check on anthropic 0.122.0 for
`messages.create`, `messages.stream`, `models.list`.

## Testing

Ran the full suite against openai 3.2.0 + anthropic 0.122.0 (installed into an
isolated venv layered onto the ambient interpreter via `PYTHONPATH`, so the
global environment was left alone):

**1649 passed, 32 skipped, 1 failed.**

Also smoke-tested `idt version` (4.5.1) and constructed `OpenAIProvider` against
the new SDK.

## What was NOT tested

- **torch 2.13.0 and mlx-vlm 0.6.13** are gated to `darwin` + `arm64` and cannot
  be installed on this Windows machine. Left to the macOS Apple Silicon CI job,
  which installs `requirements.txt` on a real M-series runner.
- No live API calls to OpenAI or Anthropic — surface checks and mocked tests only.
- No PyInstaller build run locally; relied on the CI Windows and macOS build jobs.

## Pre-existing failure found (NOT caused by this work)

`pytest_tests/unit/test_chat_app_smoke.py::test_streaming_does_not_announce_each_chunk`

Fails deterministically on clean `main` (f68eb79) with the dependency changes
stashed, and fails identically with the new SDKs absent. It uses a `_FakeProvider`
and never touches openai or anthropic.

The test asserts that a streaming turn produces exactly one screen reader
announcement carrying the whole reply; it currently produces zero. Given the
recent commits around announcements and the Cmd+A work (d5ac975, 5af6b55,
f68eb79), this looks like a real accessibility regression rather than a stale
test — per-chunk or missing announcements are exactly what this test exists to
catch. Tracked separately; deliberately not fixed in a dependency PR.

Note that CI's "Test coverage floors" job is green, so this failure is not being
caught in CI — worth understanding why the wx smoke tests pass there.
