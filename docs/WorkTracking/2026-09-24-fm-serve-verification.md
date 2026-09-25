# Verification: `fm serve` image description on macOS 27.2 (release)

**Date:** 9/24/2026
**Author:** Claude (dev lead) + Kelly
**Status:** Findings only — no repo code changed this session.
**Machine tested:** macOS 27.2 (build `26B5086k` — **release**, not a beta seed), Apple Silicon,
Python 3.13 (system `python3`), Pillow 12.2.0.
**Follows:** `docs/WorkTracking/2026-07-08-macos27-ondevice-image-research.md` (7/8/2026, run on the
27.0 beta seed `26A5378j`), and issue #324 §2 "Apple on-device model with image input".

---

## TL;DR

The `fm serve` route recommended in July **works on the release build of macOS 27**. Image
descriptions come back in roughly 4–6 seconds on this machine, with real token counts, and the
quality is usable alt text rather than a one-sentence caption.

But the endpoint is **not** a drop-in for IDT's existing `OpenAIProvider`. Four behaviours diverge
from the OpenAI API, two of them silently. The provider needs its own thin client; pointing the
OpenAI SDK at a different `base_url` fails on the first request.

---

## New since the July research

- **A machine-wide license gate.** Every `fm` subcommand — including `available`, `serve` and even
  `--help` — refuses until an admin runs `sudo fm license` once. It applies to every user on the
  machine and cannot be automated by IDT. Kelly accepted it on this machine on 9/24/2026; all
  results below are post-acceptance.
- **`fm available` is deprecated**, renamed to `fm models`. The old spelling still works but warns.
- **`fm serve --socket <path>`** now exists, and the help text calls Unix domain sockets
  "recommended for local Python bindings". This is the better transport for an auto-spawned server
  than a TCP port — no port allocation, no collision handling.
- **`pcc` (Private Cloud Compute) is unavailable to us.** `fm models` and `/health` both report
  "Private Cloud Compute is not available in this context. Please use the Terminal app." On-device
  `system` is unaffected. **Unverified** whether this is an entitlement or a parent-process check;
  either way, plan for `system` only.

---

## What was tested (empirical)

Server: `fm serve --port 11987`, healthy ~1s after launch. `GET /health` and `GET /v1/models` both
respond as documented. `/v1/models` lists `system` and `pcc`, owned_by `Apple`.

| # | Test | Result |
|---|------|--------|
| 1 | `coffee_desk.jpg` (640×480), narrative prompt | ✅ 5.0s, 309 prompt / 91 completion tokens |
| 2 | `outdoor_scene.jpg` (640×480), narrative prompt | ✅ 4.5s, 123 completion tokens |
| 3 | Same, with a `system` role message | ✅ 4.2s — accepted, output shifts |
| 4 | 4032×3024 JPEG (0.6 MB base64) | ✅ 6.0s |
| 5 | 9000×6750 JPEG q95 (3.7 MB base64) | ✅ 6.3s |
| 6 | PNG data URL instead of JPEG | ✅ 6.5s |
| 7 | Two images in one user message | ✅ 3.0s, 450 prompt tokens |
| 8 | `stream: true` with an image | ✅ 10 content chunks, first at 3.8s, 6.7s total |
| 9 | Two concurrent requests | ⚠️ serialized — 11.2s wall |
| 10 | `max_tokens` | ❌ ignored |
| 11 | `max_completion_tokens` | ✅ honoured exactly |
| 12 | `temperature: 0.2` | ✅ accepted |

Sample output (test 2, `outdoor_scene.jpg`):

> The image displays a landscape scene with a central tree, a path, and a fence. The foreground
> consists of a narrow, light brown path that extends from the bottom center toward the middle. To
> the left and right of the path, green grass covers the ground. The middle ground features a
> round, green tree with a brown trunk positioned at the path's end. Above the tree, a light brown
> fence runs horizontally across the image, supported by evenly spaced wooden posts. The background
> includes a bright blue sky with two white clouds and a yellow sun in the upper right corner.

Spatial relationships, foreground/background ordering and colour are all correct.

---

## The four divergences from the OpenAI API

**1. `stream` defaults to `true`.** This is backwards from the OpenAI spec. A request with no
`stream` key returns `Content-Type: text/event-stream`, not JSON. The first three image attempts in
this session failed with an empty-body JSON parse error for exactly this reason. IDT's
`OpenAIProvider.describe_image` builds its request without a `stream` param
(`imagedescriber/ai_providers.py` ~1056) and would break here. **The describe path must send
`"stream": false` explicitly.**

**2. `max_tokens` is silently ignored; `max_completion_tokens` is honoured.** `max_tokens: 10`
returned 39 completion tokens with `finish_reason: stop`; `max_completion_tokens: 40` returned
exactly 40. IDT sends `max_tokens: 300` on its non-GPT-5 branch
(`imagedescriber/ai_providers.py` ~1095), which this endpoint discards without error. Description
length would be whatever the model felt like.

**3. Requests serialize.** Two concurrent describes took 11.2s wall against ~4–6s each in
isolation — the second queued behind the first. Batch processing should stay strictly sequential;
there is no throughput to win from a worker pool, and an auto-spawned server needs only one
process.

**4. `pcc` is unavailable** in a non-Terminal context (see above).

---

## What this changes about the recommended design

The July recommendation — talk to `fm serve` like we talk to Ollama, reusing the OpenAI-compatible
payload — still holds for the **payload shape**: the base64 `image_url` content part is exactly
what IDT already emits, and that part needs no new code.

What it does *not* support is reusing the OpenAI **client**. Divergences 1 and 2 are both silent
failures, so the provider needs its own thin HTTP client with `stream` and `max_completion_tokens`
set deliberately. That is a small amount of code, but it must be written rather than inherited.

Two things got easier than expected:

- **No downscaling logic.** `prompt_tokens` stayed ~206 whether the image was 640×480 or
  9000×6750, so the server downscales internally. None of the ~3.7 MB size handling the
  `claude-code` provider needed (#325) applies here.
- **No format conversion.** PNG data URLs work, so the JPEG round-trip is optional.

And one got harder:

- **The license gate.** The provider must detect the un-agreed state and tell the user to run
  `sudo fm license`, rather than surfacing an opaque refusal. Likely pattern: hide from pickers
  when `fm` is unusable (as `claude-code` does when its CLI is absent) but explain why in
  `idt models`.

---

## What was NOT tested

- **Sustained batch load.** The longest run here was two concurrent requests. Throughput, thermal
  behaviour and memory over a 100-image batch are unknown. The `claude-code` measurement (103
  images) is the natural comparison to run.
- **Description quality against IDT's real prompts and real photos.** Both test images are small
  synthetic illustrations, not 12 MP photographs. Quality versus the current MLX default
  (`Qwen3-VL-4B-Instruct-4bit`) has not been compared, and that comparison should gate the decision
  to ship this as a headline provider rather than a fallback.
- **`--socket` mode.** Only TCP was exercised.
- **Server lifecycle under failure** — what happens if `fm serve` dies mid-batch, or if a stale
  server from a previous run is already bound.
- **`fm quota-usage`** and whether on-device use is metered at all.
- **`apple-fm-sdk`** on the release build. The July segfault was not re-tested; the `fm serve` path
  makes it unnecessary.
- **Non-Apple-Silicon and non-27 machines** — availability detection was not exercised on a machine
  where `fm` is absent.

## Environment changes made this session

- `sudo fm license` accepted by Kelly (machine-wide, persistent, not reverted — it is a
  prerequisite for any further work here).
- `fm serve` started on port 11987 and **stopped** at the end of the session; no process left
  running.
- Test scripts were written to the session scratchpad, not the repo. No repo files modified other
  than this document.
