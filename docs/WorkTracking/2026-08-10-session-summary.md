# 2026-08-10 — In-app update checking (Windows + macOS)

## Goal

Let an installed copy of IDT learn that a newer release exists, before cutting
v4.5. Previously the only way to find out was to revisit the GitHub releases page.

## Approach and why

Four sibling repos already solve this two ways: Velopack silent self-update
(QuickMail, GHManage) and a GitHub Releases API checker that downloads and runs
the installer (Scores, FastWeather).

**Chose the Scores-style checker.** Velopack would mean replacing Inno Setup,
relocating the install from `C:\idt` to `%LocalAppData%`, and reimplementing the
installer's `IDT_CONFIG_DIR` registry write, PATH addition, and optional winget
Ollama install — plus a migration for existing 4.x installs. Not realistic before
4.5. Velopack is filed for 5.0.

## Files changed

| File | Change |
|---|---|
| `idt_core/updater.py` | **New.** Releases-API check, per-platform asset match, SHA256-verified streamed download, URL allowlist. |
| `idt_core/config.py` | `UserConfig`: `auto_check_updates`, `skipped_update_version`, `last_update_check`. |
| `imagedescriber/imagedescriber_wx.py` | Help menu items; manual + silent checks; update dialog; timer-driven download progress. |
| `cli/main.py` | `idt update` (notify-only); docstring + epilog. |
| `imagedescriber/imagedescriber_wx.spec` | `idt_core.updater` hiddenimport; fixed `.app` version regex. |
| `idt/idt.spec` | `idt_core.updater` hiddenimport. |
| `BuildAndRelease/WinBuilds/installer.iss` | `CloseApplications=yes`, `RestartApplications=no`. |
| `.github/workflows/release.yml` | Validate gate now checks all three version sources, not just `VERSION`. |
| `pytest_tests/test_updater.py` | **New.** 61 tests. |
| `docs/release-notes-v4.5.0.md`, `docs/USER_GUIDE.md`, `docs/packaging/DISTRIBUTION_CHECKLIST.md` | Documentation. |

## Decisions

- **Version source is `idt_core.__version__`, not `shared/wx_common.get_app_version()`.**
  The latter hunts for the `VERSION` file and falls back to `"1.0.0"`, which would
  tell users they are three major versions behind. Because the updater now depends
  on it, `release.yml` gained a gate asserting `VERSION`, `idt_core/__init__.py`,
  and `pyproject.toml` all match the tag.
- **`current_version()` returns `None` on failure, not a low sentinel.** A `"0.0.0"`
  fallback would make every release look newer — nagging forever. Unknown version
  suppresses the check.
- **Tag parsing is strictly numeric** (`v4.5.0`, not `v4beta2` / `v4.0.0Beta3`).
  A digit-after-`v` guard let this repo's own historical tags parse as releases.
  Caught by a test, not by review.
- **Notify-only CLI.** One installer updates both tools, so a CLI-only download
  path would be redundant.
- **macOS stops at "here is the DMG."** A DMG cannot install over a running app.
  Filed as a follow-up.

## Review findings fixed

An independent review found five defects, all fixed:

1. **Progress dialog `Destroy()` could nest inside `Update()`** — `wx.ProgressDialog.Update()`
   yields for UI events, so a `wx.CallAfter` completion callback could be dispatched
   from inside it and free the dialog mid-call. Replaced per-chunk `CallAfter` with
   worker-written counters polled by a `wx.Timer`, plus a re-entrancy guard.
2. **Silent installer-launch failure** — added a pre-flight existence check and a
   parentless `wx.MessageBox` fallback (the frame is already closing by then).
3. **`"0.0.0"` version fallback** — see above.
4. **No integrity check on a downloaded executable** — now verified against the
   release's `SHA256SUMS.txt`; HTTPS + GitHub-host allowlist on download URLs;
   response closed via `with`; partial file removed on any failure; split
   `(connect, read)` timeouts so a stalled server cannot freeze the modal dialog.
5. **Help menu accelerator collisions** (`&U` with User Guide, `&A` with About) —
   now `Up&dates` and `Chec&k`.

## Testing

**Done:**
- `pytest pytest_tests/` — 1011 passed, 14 skipped.
- 61 updater unit tests: version compare, tag parsing, asset selection per platform,
  draft/prerelease skipping, highest-not-first, network failure propagation,
  URL allowlist, checksum parse/mismatch, cancel and mid-stream-failure cleanup.
- GUI handler harness (real methods on a shown frame, stubbed modals): 7/7 —
  update found, skip persists, silent check honours skip, up-to-date, unreachable
  feed reports honestly, preference round-trip.
- Frozen mode: rebuilt both exes; `idt.exe version` and `idt.exe update` work
  against live GitHub and a `file://` fixture feed, confirming the hiddenimport.
- `installer.iss` compiles with the new directives.
- `release.yml` gate simulated: passes when synced, fails on mismatch, survives a
  no-match `sed` under `set -euo pipefail`.

**Verified against live releases.** v4.5.0 was published, then a v4.5.1 that was
identical apart from its version number, purely so 4.5.0 had something newer to
discover. With both live:

- The frozen 4.5.0 `idt.exe` discovered 4.5.1 from the real GitHub API and
  printed the correct asset URL.
- `download_asset` fetched the real 193 MB v4.5.1 installer and verified it
  against the published `SHA256SUMS.txt`.
- The GUI update prompt appeared and installed 4.5.1 successfully (confirmed by
  the user).
- The v4.5.0 installer and DMG in OneDrive match their published checksums; the
  Windows installer's Authenticode signature reports Valid.

**v4.5.1 was then deleted** — release and tag — and `main` reverted to 4.5.0, so
v4.5.0 is the current release. The 4.5.1 build was scaffolding for this test and
nothing depended on it. Re-testing later means publishing another throwaway patch
release the same way.

**NOT tested:**
- **The final `os.startfile` handoff to Setup**, and Setup replacing files under
  a running app. Everything up to that point is now exercised.
- **The GUI's download flow end to end** — the timer-driven progress dialog was
  stress-tested with a simulated stream, not a real 193 MB download.
- **Everything macOS.** Built and tested on Windows only. The DMG, the Finder
  reveal, and the `.app` `CFBundleShortVersionString` fix are unverified on a Mac.
- **The `Update()`/`Destroy()` crash was never reproduced naturally** — not by the
  reviewer in 22 attempts, nor by 25 rounds against the old code here. The
  mechanism was proven under forced conditions; the fix removes it structurally
  rather than fixing an observed field crash.
- Installer replace-in-place over a running copy.

## Follow-ups filed

1. Evaluate Velopack for 5.0 (silent background self-update).
2. macOS update experience — signed `.pkg` or in-place `.app` replacement.
3. README download names do not match the assets CI publishes.
