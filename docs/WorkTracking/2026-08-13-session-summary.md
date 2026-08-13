# 2026-08-13 — Build and setup script audit

## Starting question

"Were the build and packaging scripts updated for the new chat client?"

They were. `builditall_wx.bat`, `package_all_windows.bat`, `installer.iss`, the
macOS scripts and all CI workflows already handled IDT Chat. The stale banner at
the top of `builditall_wx.bat` ("This script builds ImageDescriber.") is what
made it look otherwise.

The real problem was that `builditall_wx.bat` had stopped working locally.

## Root causes

### 1. `imagedescriber/.winenv` was an empty virtualenv (machine state)

Created 2026-06-01, containing only `pip`. `winsetup.bat`'s
`pip install -r requirements.txt` had failed at some point; the script prints one
`ERROR:` line, increments a counter, and continues, so the failure scrolled past
and the venv looked complete. Every later build failed with a message blaming
something else.

### 2. VIRTUAL_ENV leaked between sub-builds (repo bug, all developers)

`builditall_wx.bat` calls the three sub-builds from a **single cmd session** and
none of them deactivate. `build_idt.bat` runs first and leaves `idt\.winenv`
active. Each sub-build then guarded activation with `if not defined VIRTUAL_ENV`,
so:

| Step | Effect |
|---|---|
| `build_idt.bat` | activates `idt\.winenv` (PyInstaller, no wx) |
| `build_imagedescriber_wx.bat` | guard false → activation **skipped** |
| `build_chatapp.bat` | guard false → activation **skipped** |

Both wxPython apps built against the CLI environment. The `import wx` check then
failed and pip installed wxPython **into `idt\.winenv`**, polluting the CLI
environment while `imagedescriber\.winenv` stayed untouched.

**Why CI never caught it:** a fresh runner has no `.winenv` at all, so the
`if exist` branch is false and everything builds against system Python, which has
the full `requirements.txt`. The buggy branch is never executed in CI. The defect
only reproduces on a developer machine.

Fix: drop the guard. Re-activation is safe — `activate.bat` does
`if defined _OLD_VIRTUAL_PATH set PATH=%_OLD_VIRTUAL_PATH%` before prepending, so
activations replace rather than stack.

## Files changed

### Build scripts
- `idt/build_idt.bat`, `imagedescriber/build_imagedescriber_wx.bat`,
  `chatapp/build_chatapp.bat` — activate own env unconditionally
- `imagedescriber/build_imagedescriber_wx.sh` — venv existence check + early
  `import wx` check (macOS had no leak, but this script lacked the guards
  `build_chatapp.sh` already had)
- `BuildAndRelease/WinBuilds/build_installer.bat` — `IDTChat.exe` pre-flight +
  summary line
- `BuildAndRelease/WinBuilds/builditall_wx.bat` — corrected stale banner

### Setup scripts
- `winsetup.bat` — verifies `import wx` / `import PyInstaller` after install
  rather than trusting pip's exit code; names the failed app in a `FAILED:` line;
  tells the user not to run the build yet
- `macsetup.command` — was a byte-identical copy of `macsetup.sh`; now a thin
  `exec` wrapper matching the `builditall_macos.command` pattern
- `macsetup.sh` / `winsetup.bat` — document that IDT Chat shares ImageDescriber's
  environment (its requirements are a verified strict subset)
- `tools/environmentsetup.bat` — replaced with a shim to `winsetup.bat`
- `tools/bootstrap.bat` — corrected stale next-steps

### Deleted (dead build system)
`BuildAndRelease/`: `builditall.bat`, `build_release.bat`,
`build-test-deploy.bat`, `recommended-build-test-deploy.bat`, plus the duplicate
`build_installer.bat`, `installer.iss` and `package_all_windows.bat` that sat
beside the live `WinBuilds/` copies.

These referenced `viewer/`, `idtconfigure/` and `prompt_editor/` (all removed) and
called `packageitall.bat` / `releaseitall.bat`, which never existed in this
repository. The duplicate `installer.iss` had **0** IDT Chat references against 3
in the live one. Nothing live entered the cluster.

### CI and tests
- `.github/workflows/integration-test-windows.yml` — verify `IDTChat.exe`, launch
  smoke test, artifact upload
- `pytest_tests/unit/test_build_env_activation.py` — **new**, pins the fix

### Docs
`BUILD_SYSTEM_REFERENCE.md`, `BuildAndRelease/README.md`, `tools/INVENTORY.md`,
`tools/README_TESTING.md`, `tools/GITHUB_ACTIONS_BUILD.md`,
`tools/run_all_tests.bat`, `tools/test_automation.bat`.

`tools/run_all_tests.bat` deserves a note: its "build scripts validation" checked
five files that had *all* been absent for months, so it had been reporting
missing infrastructure indefinitely while never validating the real build system.

## Verification

- Full `builditall_wx.bat`: all three exes built and packaged
  (idt 8.2 MB, ImageDescriber 108.1 MB, IDTChat 48.8 MB)
- `build_installer.bat`: `ImageDescriptionToolkitSetup_4.5.0.exe`, 166 MB,
  compiled clean with all three apps
- `check_spec_completeness.py`: all specs complete
- pytest: **1232 passed, 14 skipped**
  (down from 1244 purely because 6 deleted `.bat` files left the parametrized
  batch-syntax scan — 6 × 2 tests)
- New regression test mutation-tested: reintroducing the VIRTUAL_ENV guard in
  `build_idt.bat` makes it fail; restoring makes it pass

## Not tested

- **All macOS changes.** `macsetup.command`, `macsetup.sh` and
  `build_imagedescriber_wx.sh` were verified by `bash -n` and inspection only.
  No macOS machine was available. `build_imagedescriber_wx.sh` in particular has
  new control flow that has never been executed.
- `tools/environmentsetup.bat`, `tools/bootstrap.bat`, `tools/test_automation.bat`
  — edited and syntax-checked, not run.
- `winsetup.bat`'s new failure paths — the success path was exercised indirectly
  by rebuilding the venv manually, but the `FAILED:` reporting was not triggered.
- The built installer was **not installed**.

## Follow-ups

- `tools/INVENTORY.md` is stale well beyond the deleted files (documents a
  four-app layout with `viewer` and `prompt_editor`). A correction notice was
  added at the file-locations section; the rest was left as history rather than
  rewritten.
- `tools/test_idt2_creation.bat` tests "Phase 3 of releaseitall.bat" and looks for
  `releases\*.zip` — obsolete, left in place.
- The venv is Python 3.12.10 while CI uses 3.13.
