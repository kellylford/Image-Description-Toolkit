# CI Workflows

What GitHub Actions runs for this project, when each workflow fires, and what
has to be configured for signing and releases to work.

All workflows live in `.github/workflows/` and target the `main` branch.

**No secret values appear in this document** — only secret names and
configuration that is already committed to the workflow files.

---

## At a glance

| Workflow | File | Runs on | Trigger | Duration |
|---|---|---|---|---|
| Build Windows Executables | `build-windows.yml` | `windows-latest` | push/PR to `main` (skips docs), manual, called by Release | ~4 min |
| Build macOS Applications | `build-macos.yml` | `macos-latest` (arm64) | push/PR to `main` (skips docs), manual, called by Release | ~13 min, ~20 with notarization |
| Release | `release.yml` | mixed | push of a `v*` tag | ~20 min |
| CLI Validation | `cli-validation.yml` | `windows-latest` | push to `main` (path-filtered), all PRs, manual | ~2 min |
| Integration Test: Windows | `integration-test-windows.yml` | `windows-latest` | push to `main` (skips docs), manual | varies |
| CodeQL Security Scan | `codeql.yml` | `ubuntu-latest` | push/PR to `main`, Mondays 08:00 UTC | ~5 min |
| Publish Documentation | `publish-docs.yml` | `ubuntu-latest` | push to `main` (path-filtered), manual | ~2 min |

---

## Build Windows Executables

Builds both applications, signs everything, and produces the installer.

1. Build `idt.exe` and `ImageDescriber.exe` via `builditall_wx.bat`
2. **Sign both** with Azure Trusted Signing
3. `package_all_windows.bat` copies them into `dist_all/bin`
4. Inno Setup builds the installer
5. **Sign the installer**
6. Verify every signature with `Get-AuthenticodeSignature`

**Signing happens before packaging on purpose.** The copies inside the
installer and the standalone `idt-windows` / `imagedescriber-windows` artifacts
all descend from `idt/dist` and `imagedescriber/dist`. Signing after packaging
would sign only the installer and leave the standalone artifacts unsigned. The
installer is then signed separately, because signatures on files inside an
installer do not cover the installer itself. That final step is non-recursive
so the already-signed copies in `bin/` are not re-signed for nothing.

The verify step **fails the build** if anything is not `Valid`, so an unsigned
release cannot ship silently.

Signing is skipped on `pull_request` (fork PRs cannot read secrets) and skips
entirely if the Azure secrets are absent.

**Artifacts:** `idt-installer-windows`, `idt-windows`, `imagedescriber-windows`

---

## Build macOS Applications

`macos-latest` is Apple Silicon, so `mlx-vlm` installs and the conditional MLX
bundling in `idt.spec` is exercised. This is why the timeout is generous.

1. Create both virtual environments (`.venv` and `imagedescriber/.venv` — the
   build scripts hard-require those exact paths)
2. `compileall` over `idt_core`, `cli`, `shared`, `imagedescriber`
3. Unit tests, then smoke tests (non-fatal)
4. `builditall_macos.sh` — the same script used locally
5. Smoke-test the frozen CLI: `version`, `--help`, and `--help` for all 12 subcommands
6. Verify the `.app` bundle structure and Info.plist
7. **Import the Developer ID certificate** into a throwaway keychain
8. **Sign** the standalone CLI and the `.app`
9. Build the DMG, sign it, **notarize and staple**
10. Gatekeeper assessment (`spctl` + `stapler validate`)
11. Verify the DMG mounts and contains both apps
12. **Delete the keychain** in an `always()` step

The certificate never touches the login keychain. `security set-key-partition-list`
is required — without it `codesign` raises a GUI authorization prompt that
nothing can answer on a headless runner, and the job hangs.

Standalone artifacts are signed as well as the DMG contents, for the same
reason as on Windows: the uploaded CLI tarball comes from `idt/dist`.

**Artifacts:** `idt-macos-arm64-dmg`, `idt-macos-arm64-cli`

### DMG appearance in CI

`create_macos_dmg.sh` positions icons and sets a background by driving Finder
through AppleScript, which needs an Aqua session and Automation permission.
That step is skipped when `$CI` is set, so **CI DMGs have no window styling**.
Contents are identical to a local build; only the cosmetics differ. Override
with `IDT_DMG_SKIP_LAYOUT=0` or `1`.

---

## Release

The only workflow triggered by tags.

```bash
git tag v4.5.0
git push origin v4.5.0
```

| Job | Depends on | Does |
|---|---|---|
| `validate` | — | Enforces the two release rules below |
| `windows` | `validate` | Calls `build-windows.yml` via `workflow_call` |
| `macos` | `validate` | Calls `build-macos.yml` via `workflow_call` |
| `publish` | `windows`, `macos` | Creates the GitHub Release |

### Two rules, enforced before any build runs

1. **The tag must equal the `VERSION` file exactly.** `v4.5.0` ↔ `4.5.0`.
   A mismatch ships binaries that misreport their own version.
2. **`docs/release-notes-<tag>.md` must exist and be non-empty.**

Both are checked in `validate`, which finishes in seconds. A malformed release
fails immediately rather than after a 13-minute macOS build.

Prereleases are not exempt. A `v4.5.0Beta1` tag requires `VERSION` to read
`4.5.0Beta1` and a matching `docs/release-notes-v4.5.0Beta1.md`.

### Both platforms must pass

`publish` has `needs: [windows, macos]`. If either build fails, **no release is
created at all**. A release carrying a Windows installer but no DMG would be
worse than none.

### Assets

Renamed to platform-explicit names, since the raw artifacts would put a bare
`idt.exe` beside a macOS `idt` tarball.

- `ImageDescriptionToolkitSetup-<version>-windows.exe`
- `idt-<version>-windows-x64.exe`
- `ImageDescriber-<version>-windows-x64.exe`
- `IDT-<version>-macos-arm64.dmg`
- `idt-<version>-macos-arm64.tar.gz`
- `SHA256SUMS.txt`

`fail_on_unmatched_files: true` stops an incomplete release from publishing.

Release notes come from `docs/release-notes-<tag>.md` via `body_path`.
`softprops/action-gh-release` marks a release as a prerelease automatically
when the tag looks like one.

---

## CLI Validation

Path-filtered on push — only runs when `cli/**`, `idt_core/**`,
`pytest_tests/**`, or its own file changes. Runs on **all** PRs regardless,
which is required: `main`'s branch protection lists
`cli-validation / IDT CLI Validation` as a required status check, so it must
report on every PR or merges block.

Syntax-checks `cli/` and `idt_core/`, runs `idt <cmd> --help` for all 12
subcommands to confirm every command is reachable, runs `test_idt_core.py`,
then smoke tests non-fatally.

## Integration Test: Windows

Real Ollama with minicpm-v4.6. Push to `main` (documentation changes excluded)
or manual. The heaviest workflow here — it pulls and runs an actual model.

## CodeQL Security Scan

Push and PRs to `main`, plus a weekly scan Mondays at 08:00 UTC.

## Publish Documentation (WCAG 2.2 AA)

Path-filtered to `docs/**`. Two jobs: `build-docs` then `deploy`.

---

## Trigger overlap and path filtering

A push touching `cli/` or `idt_core/` deliberately fires five workflows: both
builds, CLI Validation, Integration Test, and CodeQL. That is the intended
coverage for a code change.

Documentation changes should not pay for that. Both platform builds and the
Integration Test carry:

```yaml
paths-ignore:
  - 'docs/**'
  - '**.md'
  - 'LICENSE'
  - '.github/ISSUE_TEMPLATE/**'
```

So a docs-only commit runs only Publish Documentation and CodeQL, instead of
two ~15-minute builds and a live Ollama model run.

Two deliberate exceptions:

- **CodeQL is not path-filtered.** It is a security scan and cheap
  (`ubuntu-latest`, ~5 min). Skipping security tooling to save minutes ages
  badly.
- **CLI Validation's `pull_request` trigger is not path-filtered**, and must
  not be. `main` has branch protection requiring the status check
  `cli-validation / IDT CLI Validation`. If a path filter skipped that check on
  a docs-only PR, the PR would wait forever on a check that never runs and
  could not be merged.

`paths-ignore` applies only to the event it is attached to. It has no effect on
`workflow_call`, so **Release always builds both platforms** regardless of what
the tagged commit touched.

---

## Secrets

Secret names only. Values are set in Settings → Secrets and variables → Actions.

### Windows signing — all three required

- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`

### macOS signing — both required

- `MACOS_CERTIFICATE_P12` — base64 of the exported `.p12`
- `MACOS_CERTIFICATE_PASSWORD`
- `MACOS_SIGNING_IDENTITY` — optional; falls back to the identity in the workflow

### macOS notarization — all three, **plus** the two above

- `NOTARY_KEY_P8` — base64 of the App Store Connect API `.p8`
- `NOTARY_KEY_ID`
- `NOTARY_ISSUER_ID`

### How the gates work

Each feature is enabled only when its **complete** set of secrets exists, via a
job-level `env` expression:

```yaml
SIGNING_ENABLED: ${{ secrets.A != '' && secrets.B != '' && secrets.C != '' }}
```

Steps then use `if: env.SIGNING_ENABLED == 'true'`. Missing secrets mean the
steps skip and the build stays green — never a failure on credentials that were
never configured.

**Gate on the whole set, not one member.** An earlier version checked only
`AZURE_CLIENT_ID`; a partially-configured repo would have enabled signing and
then failed at `azure/login`.

The `secrets` context is not available in step-level `if`, which is why the
gate is computed into `env` at job level.

---

## Configuration outside the repo

### GitHub

- Environment **`azure-signing`** must exist. The OIDC subject includes the
  environment name, so the Azure federated credential will not match without it.

### Azure

- App registration **`github-artifact-signing`** holds two federated
  credentials for this repository:
  - plain subject — `repo:OWNER/REPO:environment:azure-signing`
  - immutable subject — uses numeric owner and repo IDs

  Both are registered because GitHub may issue either claim form. The signing
  account and certificate profile names are visible in `build-windows.yml`.
- The certificate is Azure-managed and renews without manual work.

### Apple

- Developer ID Application certificate, Team ID `P887QF74N8`.
- **Expires 2027-02-01.** Signatures made with `--timestamp` stay valid past
  expiry, but no new build can be signed after that date without renewing —
  which needs a fresh CSR from Keychain Access on a Mac and a re-export of the
  `.p12`.
- The App Store Connect API key used for notarization is separate from the
  signing certificate. Its `.p8` is downloadable only once; if lost, generate a
  new key rather than trying to recover it.

---

## Verifying a signature by hand

Windows:

```powershell
Get-AuthenticodeSignature .\ImageDescriptionToolkitSetup-4.5.0-windows.exe |
    Format-List Status, SignerCertificate
```

Expect `Status: Valid`.

macOS:

```bash
codesign --verify --strict --verbose=2 /Applications/ImageDescriber.app
spctl --assess --type open --context context:primary-signature -v IDT-4.5.0-macos-arm64.dmg
xcrun stapler validate IDT-4.5.0-macos-arm64.dmg
```

Expect `accepted` and `source=Notarized Developer ID`.

Before notarization, `spctl` reports `rejected` with
`source=Unnotarized Developer ID`. That means the signature is valid and
trusted and Apple simply has not blessed it yet — an expected intermediate
state, not a failure.

---

## Branch layout

- **`main`** — the default branch, all active development. Formerly `v4.5`.
- **`archive`** — the previous `main`, kept for history. Not built by any
  workflow.

Workflows are only visible in the Actions sidebar and dispatchable by name when
their file exists on the **default branch**. Before the rename,
`build-macos.yml` and `release.yml` lived only on `v4.5`, so neither appeared
in the sidebar nor could be triggered by name.

---

## Related

- `docs/WorkTracking/2026-07-25-session-summary.md` — how this was built, and
  what was not tested
- Issue #224 — tracking issue with current status and open items
- `BuildAndRelease/MacBuilds/` — `sign_macos.sh`, `notarize_macos.sh`,
  `entitlements.plist`, `create_macos_dmg.sh`
