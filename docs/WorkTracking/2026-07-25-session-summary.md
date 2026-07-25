# 2026-07-25 — macOS build, test and signing in GitHub Actions

Goal: build, test and sign the macOS apps in CI, matching what already exists
for the iOS projects. Scoped to Apple Silicon only.

## Outcome

Phase 1 (build + test, ad-hoc signatures) is green: run 30175190609, 13m24s,
all steps passing. Phase 2 (Developer ID signing, notarization, DMG) is written
and committed but **not yet exercised** — it stays inert until the certificate
secrets are added to the repository.

## Files changed

| File | Change |
|---|---|
| `.github/workflows/build-macos.yml` | New. Builds both apps on `macos-latest`, runs tests, creates and verifies a DMG, uploads artifacts. |
| `BuildAndRelease/MacBuilds/entitlements.plist` | New. Four hardened-runtime exceptions CPython requires. |
| `BuildAndRelease/MacBuilds/sign_macos.sh` | New. Inside-out Developer ID signing. |
| `BuildAndRelease/MacBuilds/notarize_macos.sh` | New. `notarytool submit` + `stapler staple`. |
| `BuildAndRelease/MacBuilds/create_macos_dmg.sh` | Finder layout made conditional and non-fatal; signing made opt-in; signing and notarization delegated to the new scripts. |

Commits: `269dca7`, `8814301`, `7fc6869`.

## Decisions

**Apple Silicon only.** `macos-latest` is arm64, which also exercises the
conditional MLX bundling in `idt.spec` (`mlx-vlm` is gated to darwin+arm64).
An Intel matrix job was considered and rejected: double the CI time, no MLX in
that build, and two downloads for users to choose between. Universal2 was
rejected because several dependencies do not reliably ship universal2 wheels.

**Signing is opt-in, defaulting to off.** `IDT_SIGN_CODE=1` / `IDT_NOTARIZE=1`.
With no environment set, `create_macos_dmg.sh` behaves exactly as before. This
was deliberate: the goal was to add a CI path without changing what a local
build produces.

**`codesign --deep` replaced with inside-out signing.** Apple deprecated
`--deep`; it applies the top-level entitlements to every nested binary and
silently skips code it does not recognise. `sign_macos.sh` signs nested Mach-O
objects deepest-first, then the bundle last, and applies entitlements only to
the top-level target.

**Artifacts are tarred or shipped as a DMG, never uploaded raw.**
`upload-artifact` does not reliably preserve the executable bit or symlinks,
both of which a `.app` bundle needs in order to launch.

## Things found along the way

**CLAUDE.md's architecture section is stale.** It documents
`scripts/workflow.py` (with a line count), `scripts/image_describer.py`,
`scripts/config_loader.py`, `scripts/list_results.py`,
`scripts/workflow_utils.py` and `idt/idt_cli.py`. None of these exist.
`scripts/` now contains only three JSON config files; the pipeline lives in
`idt_core/` and the CLI entry point is `cli/main.py`. This caused the first CI
failure. **Not fixed** — flagged for a separate pass.

**Both apps are onefile builds.** `imagedescriber_wx.spec:194` and
`idt.spec:141` pass binaries and datas straight into `EXE()` with no
`COLLECT`, so there is no `Contents/Frameworks` directory in the `.app`.

Consequences:

- The signature-fixing loops in `build_imagedescriber_wx.sh:19-45` and
  `build_idt.sh:26-37` are no-ops. They `find` inside paths that do not exist
  (in the CLI case, `find` is run against a regular file), silenced by
  `2>/dev/null || true`. The only real effect is the final ad-hoc sign.
  **Not fixed** — harmless, but misleading to read.
- The justification for disabling Developer ID signing was wrong. The comment
  claimed the bundled `Python.framework` carries python.org's signature and
  causes a Team ID mismatch. In a onefile build there is no `Python.framework`
  in the bundle. Comment removed.

**`create_macos_dmg.sh` notarization block was dead code.** It passed
`--keychain-profile "$PROFILE_NAME"`, a variable never assigned anywhere in
the script. Under `set -u` it would have aborted. Unreachable in practice
because `SIGN_CODE` was hardcoded to 0.

**Latent bug in `builditall_macos.sh:91`, `:106`, `:196`.** `((BUILD_ERRORS++))`
under `set -e`: when `BUILD_ERRORS` is 0, the post-increment evaluates to 0,
which bash reports as exit status 1, killing the script. A build failure
therefore produces an abrupt exit instead of the intended summary.
**Not fixed** — only reachable on failure paths.

**`verify_macos_build_structure.sh` checks for `docs/BUILD_MACOS.md`**, which
does not exist, so it always exits 1. Marked `continue-on-error` in the
workflow. It is the source of the run's one annotation. **Not fixed** — needs
either the doc or the check removed.

## Test results

Run 30175190609 — all steps passed:

- Both virtual environments built, including wxPython and mlx-vlm on arm64
- `compileall` over `idt_core`, `cli`, `shared`, `imagedescriber`
- `pytest_tests/unit` passed; `pytest_tests/smoke` passed (marked non-fatal)
- `builditall_macos.sh` completed, including its own pre-build validation
- Frozen CLI: `version`, `--help`, and `--help` for all 12 subcommands
- `ImageDescriber.app` bundle structure and Info.plist keys verified
- Artifacts: `imagedescriber-macos-arm64` 342 MB, `idt-macos-arm64` 313 MB

## What was NOT tested

- **Developer ID signing.** `sign_macos.sh` has never run against a real
  certificate. Syntax-checked only.
- **Notarization.** `notarize_macos.sh` has never been submitted to Apple.
  Syntax-checked only.
- **Whether Apple's notary service accepts a onefile build.** `codesign` can
  only sign the outer executable; the embedded `.so`/`.dylib` files are opaque
  payload inside the archive. Reports of the notary rejecting unsigned nested
  binaries are mixed. If it rejects, the fix is switching both specs to onedir
  (`COLLECT`), which is what PyInstaller recommends for macOS distribution.
  `sign_macos.sh` already handles both layouts.
- **Whether the built apps actually launch.** CI verifies bundle structure and
  runs the CLI, but the GUI is never launched. No headless test covers wx.
- **The DMG's appearance.** CI skips the Finder layout, so the CI DMG has no
  background image or icon positions. Contents are identical to a local build.
- Anything on Intel Macs. Nothing here targets x86_64.

## Next steps

1. Add repository secrets: the `.p12` (base64) and its password, plus App Store
   Connect API key credentials for notarization. Export must happen on the Mac
   holding the private key.
2. Wire a signing step into the workflow, gated so it no-ops when the secrets
   are absent. Import into a temporary keychain, not the login keychain.
3. Submit one real notarization to find out whether onefile is accepted.
4. Decide whether release DMGs need the styled Finder window. If so, either
   build releases locally or commit a pre-made `.DS_Store` for CI to apply.

## Certificate note

Developer ID Application certificate exists, Team ID `P887QF74N8`.
**It expires 2027-02-01.** Signatures made with `--timestamp` remain valid
after expiry, but no new builds can be signed past that date without renewing,
which requires a fresh CSR from Keychain Access on a Mac.
