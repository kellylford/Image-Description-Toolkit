# 2026-07-28 — Issue #228: close the test-coverage gaps

Closes the gap enumerated in issue #228: two defects (the Ollama retry bug and
the silent build failure) shipped and survived for months under a fully green
suite, and the conditions that allowed it were still largely in place.

## Result

| | Before | After |
|---|---|---|
| Tests | 434 passed, 13 skipped | 852 passed, 13 skipped |
| Total coverage | 13.48% (and 0% via project config) | 20.12%, floor enforced at 19% |
| `imagedescriber/ai_providers.py` | 37.32% | 64.16%, floor 62% |
| GUI modules | 0.00% each | 5.7%–11.7% each |
| Per-file floors | none | 9, enforced in CI |

## Bugs found and fixed while doing this

Two were found by the new tests on their first run, not by inspection.

### 1. `exit /b N` from a doubly-nested block is discarded by cmd (release-blocking)

`builditall_wx.bat` still reported success when a sub-build exited 0 without
producing an executable — the exact defect 1488bb5 was meant to close. The
guards added in that commit printed `✗ ImageDescriber.exe NOT FOUND` and then
ran `exit /b 1`, but cmd throws that exit code away when it comes from an
`if` block nested inside another `if` block. One level works; two does not:

```
if "%E%"=="0" ( if not exist x ( exit /b 1 ) )    -> caller sees 0
if "%E%"=="0" ( exit /b 1 )                       -> caller sees 1
```

Reduced and verified independently of the project. Six occurrences across two
release-gating scripts:

* `BuildAndRelease/WinBuilds/builditall_wx.bat` — 4 sites, all the
  missing-artifact and copy-failure guards. Rewritten with flat `goto` control
  flow so every failing `exit /b` is at top level.
* `imagedescriber/build_imagedescriber_wx.bat` — 2 sites, the
  "failed to install PyInstaller/wxPython" guards. Same fix, smaller.

`build_installer.bat`'s exits are at depth 1 and were never affected.

A scanner covering every `.bat` in the repo, present and future, is now in
`test_batch_script_syntax.py`, alongside a self-test proving it fires.

### 2. `_is_retryable_error` let the word "timeout" outrank an HTTP status

`"Invalid request - upstream timeout (status code: 400)"` classified as
retryable, so a permanently malformed request was re-sent four times per image.
The numeric status now decides; the bare "timeout" substring is only a fallback
for errors carrying no status at all. Found by the exhaustive
kind × status matrix in the new formatter test.

### 3. Crash logs could be destroyed by the thing they were logging

`imagedescriber_wx.py` wrote `crash_log.txt` and `chat_import_error.log` with
no `encoding=`, inside a bare `except: pass`. A traceback containing one
non-ASCII character raises `UnicodeEncodeError` under cp1252, gets swallowed,
and the diagnostic is lost at exactly the moment it is needed. Fixed, along
with three API-key file reads.

### 4. Dead PyQt6 left over from the wxPython migration

`imagedescriber/ui_components.py` imported PyQt6, which is not a dependency of
this project. It survived the migration to wxPython and simply never ran
again — invisible precisely because nothing imported it and nothing measured
it. Found by the new import smoke test on its first run.

A sweep for the rest of it turned up:

* `viewer/viewer.spec` — orphaned PyInstaller spec for the standalone Viewer,
  an app removed in c424acd. It points at a `viewer.py` that no longer exists
  and at `../scripts` for data. `viewer/` contained nothing else.
* Five docs stating PyQt6 as current fact, not history. `imagedescriber/README.md`
  told users to run `pip install PyQt6` to fix a startup failure, named PyQt6
  as the architecture, and claimed Python 3.8+ (`requires-python` is >=3.11).
  Also `.github/copilot-instructions.md` ("GUI Development (PyQt6)"),
  `BuildAndRelease/MacBuilds/README_MACOS.md` (accessibility "via PyQt6"),
  `tools/GITHUB_ACTIONS_BUILD.md`, and `docs/packaging/TURN_KEY_PACKAGING.md`
  (which also listed three module names that no longer exist).

All deleted or corrected. Genuine historical references are deliberately kept:
`BUILD_SYSTEM_REFERENCE.md`'s "Migration from PyQt6" section, the migration
note in `copilot-instructions.md`, and `CHANGELOG.md` are accurate records.

`test_gui_smoke.py::test_no_gui_module_imports_a_qt_binding` now guards it, and
`UNIMPORTABLE` is empty — every GUI module is covered with no exclusions.

## Changes

### P0

* **`pyproject.toml`** — `[tool.coverage.run] source` was `["scripts"]`, a
  directory emptied of Python in 2a32e6d. Every `--cov` run using the project
  config measured zero files and reported success. Now
  `["idt_core", "imagedescriber", "cli"]`.
* **Coverage ratchet** — global `fail_under = 19` (measured 20.12), plus nine
  per-file floors in `[tool.idt.coverage-floors]` enforced by
  `tools/check_coverage_floors.py`. Floors are the point: a global percentage
  is satisfied by covering anything at all. `addopts` deliberately still does
  not pass `--cov`, so targeted runs like cli-validation's single-file job are
  unaffected.
* **`.github/workflows/coverage.yml`** — runs the full suite with coverage and
  applies both gates. Installs wxPython and asserts it imports, because an
  `importorskip` that always skips is indistinguishable from a pass.
* **`pytest_tests/unit/test_provider_contract.py`** (92 tests) — replaces the
  literal-scanning approach. Enumerates `AIProvider.__subclasses__()` and
  requires each to register a fault-injection driver, then drives every one
  through 200 / 429 / 500 / 502 / 503 / 401 / 400 / timeout / malformed.
  **Verified against the issue's own reproduction:** adding a `GeminiProvider`
  returning `"Error: upstream returned HTTP 503 - retry later"` now fails the
  suite by name. Under the old test it left 404 passed.

  The strongest assertion is `500 → 200 returns a description`: it fails if the
  wording drifts, if `@retry_on_api_error` is missing, or if a delegating
  provider stops delegating.

### P1

* **Structured provider errors** in `ai_providers.py` — `ProviderError` with a
  `status_code` field, `classify_provider_exception()` (one copy, replacing
  byte-identical duplicates in OpenAIProvider and ClaudeProvider), and
  `format_provider_error()` as the single place a failure becomes English. All
  five providers route through it. A static test forbids any `(status code:
  ...)` literal outside the formatter, and a kind × status matrix asserts the
  formatter and `_is_retryable_error` can never disagree.

  **Not done:** providers still *return* strings rather than raising. The issue
  favoured the exception; that changes the contract with `workers_wx.py` and
  every other caller, and is better done as its own change now that these tests
  exist to protect it. `ProviderError` is in place and ready for it.
* **`pytest_tests/integration/test_provider_against_failing_server.py`** —
  a real `ThreadingHTTPServer` scripted to return 500 then 200. CI only ever
  ran a local model, which never returns 5xx, so the path the bug lived in was
  unreachable there.

### P2

* **`pytest_tests/unit/test_gui_smoke.py`** (213 tests, 2.7s) — every GUI
  module imports under a headless `wx.App`; every handler named in a `Bind()`
  call exists on its class (196 call sites); an AST check that `logger` is
  bound wherever it is read, which is the CLAUDE.md eight-hour incident as an
  assertion; and a ban on Qt imports. Includes a self-test proving the logger
  detector fires on the incident and stays quiet on the local-assignment shape
  `ai_providers.py` uses.
* **`pytest_tests/unit/test_build_orchestrators.py`** (18 tests) — scaffolds a
  throwaway tree with stubbed sub-builds and runs the real orchestrators.
  Four scenarios each for Windows and macOS: success, build fails, exits 0 with
  no artifact, and stale artifact present. This is what found bug 1.

### P3

* Deleted `imagedescriber/fix_chat_window.py` — a one-off repair script with a
  hardcoded absolute path, executing file I/O at import, referenced nowhere.
* **`pytest_tests/unit/test_source_reading_hygiene.py`** — forbids text
  read/write without `encoding=`. The suite is clean; shipped code had five,
  all fixed, budget pinned at 0.

## Testing

* Full suite: **852 passed, 13 skipped**, 0 failures.
* Global coverage gate and all 9 per-file floors pass.
* Rogue-provider injection confirmed to fail the suite, then reverted.
* Both build-script fixes verified by the new harness actually executing them.
* `python -m py_compile` on every changed Python file.
* ImageDescriber.exe rebuilt after the `ai_providers.py` / `workers_wx.py`
  changes (both are in the spec's `hiddenimports`).

## What CI proved (PR #229, all six checks green)

Two caveats from the original draft of this document are now retired:

* **macOS is verified.** `Build + Test (Apple Silicon)` ran all ten
  `test_macos_*` orchestrator tests on real macOS with real bash and real
  `python3` — not the Git Bash and stubbed `python3` they were written under.
  The full macOS build completed and its post-build validation passed 4/4.
* **`coverage.yml` works.** wxPython 4.2.5 installed and imported on
  `windows-latest`, 852 tests ran, `fail_under=19` was applied against 20.28%,
  and all nine per-file floors were enforced with real numbers printed.

CI also caught a defect local runs structurally could not — see bug 5 below.

## What was NOT tested

* **The GUI smoke test does not run on macOS.** `build-macos.yml` runs
  `pytest_tests/unit` with the ROOT `.venv`, which has no wxPython — it is
  installed only in the ImageDescriber venv. So `pytest.importorskip("wx")`
  drops all 213 tests at collection time, reported as nothing louder than
  "collected 605 items / 1 skipped". That is the same silent-skip failure mode
  `coverage.yml` guards against with its explicit "Verify wxPython is
  importable" step; `build-macos.yml` has no such guard. The tests do run in
  full on Windows. Worth either installing wxPython into the macOS root venv or
  pointing that step at the ImageDescriber venv — deliberately left alone here
  as a workflow change beyond this issue.
* **macOS runs only `pytest_tests/unit`**, so the stub-HTTP-server integration
  test is Windows-only in CI.
* **MLX provider**: driven only through a fully mocked `mlx_vlm`. Never
  executed on Apple Silicon.
* **Real API calls**: no test hits OpenAI, Anthropic or a live Ollama. All
  provider tests use injected transports or a local stub server.
* **GUI behaviour**: import and binding integrity only. No dialog is opened, no
  handler is invoked, nothing is clicked.
* **The exception refactor** (issue item 5) is deliberately not done — see
  above.

## 5. A macOS-only blind spot in this work's own tests

Worth recording because it is the same shape as the bugs this issue is about.

The first CI run failed with `assert 895 <= 0`: the new encoding scanner walked
into `imagedescriber/.venv/lib/python3.13/site-packages` and reported offenders
from transformers, typer and wx.

The virtualenv name differs per platform — `.winenv` on Windows, `.venv` on
macOS — and both live *inside* `imagedescriber/`, a directory the scan treats
as one of its packages. Excluding only the locally visible name passes locally
and can fail only on the other platform.

Fixed by excluding both names plus `site-packages`, and by asserting the scan
never reached installed packages. Verified by planting a `.py` with two
unqualified reads and a `.bat` with a doubly-nested `exit /b 1` inside a
macOS-style `.venv`, confirming each would trip its scanner if seen and that
both are skipped. `test_batch_script_syntax.py` had the identical latent bug;
`test_coverage_floors.py` counted venv modules toward "this directory contains
Python". `test_shell_script_safety.py` already excluded both.

CodeQL additionally raised six alerts, all in new code, all fixed rather than
dismissed: two `py/overly-permissive-file` (high) from `chmod 0o755` on stub
build scripts only the current user executes, now `0o700`; a genuinely
redundant `400 <= status < 500` after `status >= 500` had returned; an unused
import; and two `import-and-import-from`, resolved by using monkeypatch's
dotted-string form as `test_retry_contract.py` already does.
