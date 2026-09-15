# 2026-09-14 — Dependabot dependency sweep

## What happened

Dependabot opened 13 PRs (#302–#319) across five pip packages. As in the
[8/25 sweep](2026-08-25-session-summary-dependabot.md), they overlapped heavily:
nine were strict subsets of four supersets. All 13 were green on all seven CI
checks.

No bump broke anything this time. The sweep did surface a **manifest coverage
gap** that merging the PRs as-opened would have written into the repo.

## The overlap

| Superset PR | Bump | Files | Subsets superseded |
|----|------|-------|-----|
| #310 | anthropic 1.0.0 → 1.4.0 | root, chatapp, idt, imagedescriber, pyproject.toml | #313, #319 |
| #318 | openai 3.3.1 → 3.8.0 | root, chatapp, idt, imagedescriber, pyproject.toml | #309, #317 |
| #316 | torch 2.13.0 → 2.14.0 | root, imagedescriber | #315 |
| #302 | mlx-vlm 0.6.15 → 0.6.17 | root, imagedescriber | #305 |
| — | pillow-heif 1.5.0 → 1.6.0 | **no superset** — see below | #311, #312, #314 |

## pillow-heif: Dependabot covered three manifests out of six

The pillow-heif bump arrived as three disjoint PRs with no superset:

- #314 → `tools/show_metadata/requirements.txt`
- #312 → `imagedescriber/requirements.txt`
- #311 → `idt/requirements.txt` (two lines)

It opened nothing for `requirements.txt` (two lines), `chatapp/requirements.txt`,
or `pyproject.toml`. Merging the three as-opened would have left the same package
pinned at **three different floors** in one repo: 1.6.0 in idt/imagedescriber/tools,
1.5.0 in root/chatapp, and 1.4.0 in `pyproject.toml` — which was already one
release behind the rest of the tree before this sweep.

All six manifests were brought to `>=1.6.0` instead, the same reapply-consistently
approach #299 used in the 8/25 sweep.

## The floors are cosmetic — audit against what actually installs

Every constraint in this repo is `>=`, so a floor bump does not change what a
fresh install resolves to. Installing these five requirements today gives:

| Package | PR floor | Actually installs |
|---|---|---|
| anthropic | 1.4.0 | **1.5.0** |
| openai | 3.8.0 | **3.14.0** |
| pillow-heif | 1.6.0 | **1.7.0** |

The audit below was run against those resolved versions, not the floors. This is
the lesson from 8/25: the anthropic crash found then was already live on `main`
because `>=0.122.0` already resolved to 1.0.0, and the floor bump only made the
constraint honest.

## Audit — every SDK surface this repo uses

Checked against a real `anthropic==1.5.0` / `openai==3.14.0` / `pillow-heif==1.7.0`
install in an isolated venv, by calling the surfaces rather than reading changelogs.

**anthropic — all pass.** All four client constructor shapes used in the repo
(`api_key`, bare, `+timeout`, `+timeout+max_retries`); `messages.create` and
`messages.stream` accept `model`/`max_tokens`/`messages`/`system`; `models.list`
still accepts `limit`; `AuthenticationError`/`APIError`/`RateLimitError`/
`APIStatusError` all still exist.

`temperature`/`top_p`/`top_k` remain **absent** from both method signatures at
1.5.0 — the 1.0.0 removal was not reverted, so the #298 fix is still load-bearing.
Verified the live path: `ClaudeChatProvider._request_kwargs()` with
`temperature=0.2` still yields only `{max_tokens, messages, model, system}`, and
those kwargs reach the API (401 on a fake key) rather than raising `TypeError`.

**openai — all pass.** `OpenAI(api_key=)`, `+timeout+max_retries`, and
`http_client=`; `chat.completions.create` accepts `model`, `messages`, `stream`,
`stream_options`, `max_completion_tokens`, `temperature`, `max_tokens`; both
`client.with_raw_response` and `chat.completions.with_raw_response` still exist;
the four exception classes the tools catch still exist.

**pillow-heif — passes on real data.** `register_heif_opener()` exists and runs.
Ran the actual converter against the repo's real HEIC (`test_data/IMG_3136.HEIC`):
`_heic_to_jpeg_bytes()` → 3,030,027 bytes, and `convert_heic_to_jpg()` → a valid
3024×4032 RGB JPEG with its 2,972 EXIF bytes preserved.

**Describe/chat call shapes.** The four inline kwargs dicts at the
`describe()` / chat call sites (`idt_core/providers/claude.py`,
`idt_core/providers/openai_provider.py`, `imagedescriber/ai_providers.py`,
`idt_core/chat/providers.py`) were each sent to the installed SDK. All four reach
the API instead of raising `TypeError`.

## Testing

Full suite against the upgraded SDKs: **1724 passed, 41 skipped**, in line with
the 8/25 baseline of 1722/43.

A first run showed `test_imagedescriber_launches` failing and 287 skips. That was
the test venv, not a regression: root `requirements.txt` does not list wxPython
(it lives in `imagedescriber/requirements.txt`), so ImageDescriber exited 1 on
`ModuleNotFoundError: No module named 'wx'`. With wxPython 4.3.1 installed the
suite is fully green.

## Pre-existing issue found, not caused by this sweep

`tools/capture_raw_response.py` and `tools/capture_empty_response_loop.py` both
`import httpx`, which **is not declared in any manifest** — it was relied on as a
transitive dependency of `openai`. The openai SDK now depends on `httpx2`, not
`httpx`, so a fresh install leaves those two scripts raising `ImportError`.

This is not from these PRs: openai **3.3.1**, the floor already on `main` before
this sweep, already required `httpx2<3,>=2.7.0`. The 8/25 note that those scripts
go to an `OpenAI(http_client=...)` "which still uses `httpx`" is out of date.

Left alone deliberately — both are one-off capture scripts written for a closed
OpenAI support case (05757486), referenced by nothing in the tree, and not built
or tested. (Passing an `httpx.Client()` into `OpenAI(http_client=)` does still
work when httpx happens to be installed; the breakage is the bare import.)

## What was NOT tested

- **torch 2.14.0** and **mlx-vlm 0.6.17** are gated to `darwin` + `arm64` and
  cannot be installed on this Windows machine. Left to the Apple Silicon CI job,
  which passed on #316 and #302.
- No live API calls against either provider beyond unauthenticated 401s — the
  audit proves the request shape is accepted and dispatched, not that a real
  completion comes back. No billing.
- No exe build; these are manifest-only changes that touch no file in any
  `.spec` `hiddenimports`.

## Environment gotcha

Building the audit venv under the session scratchpad failed with a confusing
`ModuleNotFoundError: No module named 'anthropic.types.code_execution_tool_result_block_content'`
on a file that was present on disk. The path was 263 characters — over Windows'
260-char `MAX_PATH`. Rebuilding at a short path fixed it. Worth remembering for
any future venv under the long worktree/scratchpad paths.

---

## Follow-up: automating this (same session)

After #320 merged, all 13 Dependabot PRs were closed as superseded and two
config changes landed to stop this sweep shape from recurring.

### Dependabot now opens one grouped PR per ecosystem

`.github/dependabot.yml` moved from `directory` (singular, one entry per app) to
`directories` (plural) plus a `groups` block matching `*`. Every Python manifest
now updates in a single weekly PR, so a package moves everywhere at once or not
at all — which is exactly the failure this sweep hit, where pillow-heif was
opened for three manifests and skipped in three others.

**`/chatapp` was missing from `dependabot.yml` entirely** and has been added. Its
`openai`, `anthropic`, `pillow-heif` and `wxPython` pins had never been tracked
by Dependabot at all. That is part of why the pillow-heif coverage was uneven.

### Auto-merge waits for checks itself, and does not touch branch protection

`.github/workflows/dependabot-auto-merge.yml` merges a Dependabot PR once every
check on it has passed.

It deliberately does **not** use GitHub's native auto-merge. Native auto-merge
waits only for checks branch protection marks *required*, and `main` currently
requires none — so turning it on as-is would merge Dependabot PRs instantly,
without waiting for CI at all. Making the seven checks required is not an option
either: `build-windows.yml` and `build-macos.yml` carry `paths-ignore` for
`docs/**` and `**.md`, so they never run on a docs-only PR. A required check that
never runs leaves the PR waiting on a status that will never report — which would
have deadlocked every session-summary PR, including #300 and this file.

So the wait lives in the workflow, where it applies to Dependabot PRs only.
Branch protection is unchanged.

The workflow uses `pull_request_target` because Dependabot-authored events get a
read-only `GITHUB_TOKEN`. It never checks out the PR's code — the only untrusted
input is the PR number — so the usual `pull_request_target` hazard does not apply.

Two details that would otherwise bite:

- It filters its own check out of the rollup by `workflowName`. Without that it
  waits on itself and never merges.
- An empty rollup means "checks have not registered yet", not "everything
  passed". It waits rather than merging into a vacuum.

Decision logic was tested against 13 rollup states (green, queued, in-progress,
failure, cancelled, timed-out, skipped, legacy `StatusContext` entries, self-only,
and empty) — all produced the intended merge/wait/abort verdict. The jq
expressions were also run through `gh`'s gojq against the real #320 rollup.

### Known risk, accepted

"All seven checks green" has twice failed to mean "good" in this repo: the 8/25
anthropic bump was green and still shipped a `TypeError`, and merging the 9/14
pillow-heif PRs as-opened would have written three inconsistent floors. Both
would now auto-merge. The grouping change removes the second failure mode; the
first is a real residual risk, accepted deliberately in exchange for not hand-
reviewing a dozen PRs a week. The weekly grouped PR is the place to look.
