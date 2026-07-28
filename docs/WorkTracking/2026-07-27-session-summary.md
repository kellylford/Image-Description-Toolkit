# 2026-07-27 — Ollama cloud 502s, retry contract, and the silent build failure

## Why this session happened

Ollama cloud models started returning 502/500 for every image. The investigation
found the upstream failure was real but that IDT turned a recoverable blip into a
hard failure — and then found that the Windows build could report success after
failing outright.

## Root causes

### 1. Ollama 5xx never retried (latent since 2025-10-07)

`OllamaProvider.describe_image` returned `"Error: HTTP 500 - (ts)"`, but
`retry_on_api_error` only retried strings matching `"status code: 5"` /
`"status code: 429"` — the convention OpenAI and Claude use.

The two halves were written two weeks apart by unrelated commits:

- `f99e8e1` (2025-10-07) wrote the Ollama wording.
- `607d160` (2025-10-21) added the decorator and its string matching.

Neither commit is wrong alone; the contract between them was implicit and
invisible in review. Measured against ollama.com: cloud **text** requests always
succeed, cloud **vision** requests fail ~50% of the time with
`500 Internal Server Error (ref: <uuid>)`. Local models never fail. Both
`/api/generate` and `/api/chat` fail at the same rate, so it is not endpoint
specific — the upstream backend is genuinely flaky, and this is new. The missing
retry is nine months old.

### 2. OpenAI/Claude 429 and 5xx never retried either

The decorator additionally required `result.startswith("Error:")`. Most
OpenAI/Claude failures read `"Rate limit exceeded (status code: 429) - ..."` or
`"Server error from OpenAI API (status code: 500) - ..."`, which do not. Same
class of defect, wider blast radius.

### 3. `retry_on_api_error` was defined twice

Lines 141 and 220 of `ai_providers.py`, identical apart from a trailing blank
line. The second silently shadowed the first.

### 4. builditall_wx.bat exited 0 after a completely failed build

cmd treats an unescaped `)` inside a parenthesized block as CLOSING the block,
even mid-`echo`, while `(` in argument position does not open one. So:

    echo   ✓ ImageDescriber.exe (with integrated Viewer Mode and tools)

terminated the enclosing `if "%BUILD_ERRORS%"=="0" (` block early. The following
`) else (` rebound to the outer `if`, everything after became top-level, and the
script ran into `exit /b 0`.

Observed: both application builds failed, and the script printed
"Ready for distribution" and exited 0, packaging a three-week-old `idt.exe`.
A broken build was indistinguishable from a good one.

Confirmed by isolating the mechanism: escaping just that one line's parens flips
the script to `exit /b 1` with the correct failure branch. The same pattern was
present in 9 batch files.

## Why the tests did not catch any of this

`pytest_tests/` had exactly one file importing `ai_providers`
(`test_ollama_vision_filter.py`), covering only `_model_has_vision`. **Zero tests
touched `describe_image` or the retry decorator.** 311 green tests said nothing
about a nine-month-old bug because nothing asked the question.

## Changes

### Behaviour

- `imagedescriber/ai_providers.py`
  - Ollama HTTP errors now use the shared `(status code: NNN)` convention.
  - New `_is_retryable_error()` — one place that decides retryability, parsing the
    status code rather than substring-matching. 5xx/429/timeout retry; 4xx do not.
  - Removed the duplicate `retry_on_api_error` definition.
  - Dropped the `startswith("Error:")` guard.
  - `import re` moved to module level (it was function-local at line 127; the new
    helper needed it and failed at runtime until this was fixed).

### Build

- `BuildAndRelease/WinBuilds/builditall_wx.bat`
  - Escaped the parens that broke block parsing.
  - Deletes both target exes before building, so "the exe exists" proves *this*
    build produced it rather than the previous one.
  - Missing exe or failed copy now aborts with `exit /b 1` instead of echoing a
    warning and continuing. Written as immediate-exit checks rather than an error
    counter, because reading a counter set inside the same block would require
    delayed expansion — the same family of trap.
  - `call .\build_idt.bat` (explicit relative path) so it resolves when
    `NoDefaultCurrentDirectoryInExePath` is set.
- Escaped parens in 8 further batch files carrying the same latent defect.
- `build_installer.bat` success message named a file Inno Setup never produces
  (`ImageDescriptionToolkit_Setup_v4.5.0.exe` vs the real
  `ImageDescriptionToolkitSetup_4.5.0.exe`).
- Corrected the same wrong filename in `README.md`,
  `BuildAndRelease/README.md`, and `BuildAndRelease/WinBuilds/README.md`.
  Verified against the actual GitHub release assets, which use
  `ImageDescriptionToolkitSetup_<version>.exe`. References under the *legacy*
  `BuildAndRelease/installer.iss` path were left alone — that spec really does
  emit `ImageDescriptionToolkit_Setup_v*.exe` into `releases/`.

### Tests (new)

- `pytest_tests/unit/test_retry_contract.py` (25 tests) — classification table,
  decorator retry/give-up/no-retry behaviour, the real Ollama 500 path with a
  mocked transport, a static scan asserting no provider invents its own wording,
  and a guard that the decorator is defined exactly once.
- `pytest_tests/unit/test_batch_script_syntax.py` (35 tests) — scans every `.bat`
  for unescaped parens in `echo` inside blocks, and pins the fail-fast structure
  of `builditall_wx.bat`.

Both were verified to FAIL against the original defects before being kept:
reintroducing the Ollama wording fails 3 tests; reintroducing the `startswith`
guard fails 4; unescaping the batch parens fails 1.

### Test fixes

- `test_idt_core.py` and `test_ollama_vision_filter.py` called `read_text()`
  without an encoding on sources containing non-ASCII. One was already failing on
  Windows cp1252; the others passed only by luck, since cp1252 chokes on just a
  few byte values (0x81, 0x8d, 0x8f, 0x90, 0x9d).

## Results

- Suite: **375 passed, 3 skipped** (was 311 passed / 1 failed).
- Rebuilt both exes through the fixed `builditall_wx.bat` — succeeded, exit 0.
- Verified the fix is in the shipped binary by extracting the PyInstaller PYZ and
  inspecting the bundled `ai_providers` constants. (Plain `grep` on a onefile exe
  proves nothing — sources are zlib-compressed `.pyc` inside the archive.)
- Live check against `gemma4:31b-cloud`: 3/3 images succeeded, recovering on
  retry attempts 2–3 where they previously hard-failed.
- Installer rebuilt and deployed to
  `C:\Users\kelly\OneDrive\idt\idt-bd1b966-ollamafix\`, SHA256 verified.

## NOT tested / still open

- **The GUI was not launched.** All provider verification was done by calling
  `OllamaProvider.describe_image` directly and by inspecting the packaged binary.
  The installer itself was not installed and run.
- **OpenAI and Claude retry paths were not exercised against the live APIs.**
  Their fix is covered by unit tests using their exact error wording, not by real
  429/5xx responses.
- **The upstream ollama.com failures are not fixed and are not ours.** Retrying
  masks them; batches against cloud vision models will be slower until Ollama
  fixes their backend.
- macOS build scripts (`BuildAndRelease/MacBuilds/`) were not audited for the
  equivalent shell-quoting issues.
- Changes are **uncommitted** on `main`.

## Branch note

Local `main` was stale — it still pointed at the pre-rename main, now
`origin/archive`. Reset to `origin/main` after confirming the old tip was
contained in `origin/archive` and that local `v4.5`'s tip was already in
`origin/main`. The stash held only an untracked 200 MB installer exe.
