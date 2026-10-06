# Windows AI helper

A small C# program that lets IDT describe pictures with Windows' own on-device model on a
Copilot+ PC (`Microsoft.Windows.AI.Imaging.ImageDescriptionGenerator`). It runs on the PC's NPU:
no account, no key, no network, no cost. IDT's Windows AI provider starts it and talks to it;
people normally never run it directly. Tracked in issue #360.

## Why a separate program

Windows only lets a **packaged** app use the model. Run as an ordinary exe, the very first call
fails with `UnauthorizedAccessException`, 0x80070005, "Access is denied", however correct the
code. Python can't be given a package identity, so IDT runs this helper, which is packaged.

What the package needs, found by trying each on a Copilot+ PC:

- **Package identity**, which comes from installing it as an MSIX package. In development,
  registering the build folder in Developer Mode gives the same.
- **The `systemAIModels` capability** in its manifest.
- **`MaxVersionTested` of 10.0.26226.0 or later.** Older values give "Not declared by app".
- **Windows App Runtime 1.8**, which the manifest depends on. Many PCs have it already; IDT's
  installer is to add it where it's missing.
- **To be started as `idt-windows-ai`**, the command the package adds, so Windows runs it with
  the package's identity. IDT always starts it that way. Started as `IdtWindowsAI.exe` from its
  folder, as a person might, it has no identity; it notices and starts itself again through
  `idt-windows-ai`, inside a Windows job that ends the second copy whenever the first ends, so
  killing the first never leaves the second running.

## Using it

```
idt-windows-ai --check                          readiness, as one line of JSON
idt-windows-ai --prepare                        get the model ready, downloading it if needed
idt-windows-ai --describe <picture> [kind ...]  describe a picture, for people
idt-windows-ai --serve                          IDT's mode: JSON lines on stdin and stdout
idt-windows-ai --version
```

The kinds are **accessible** (the default: a long description meant for people who are blind or
have low vision), **detailed**, **brief** and **diagram**. The model takes no prompt; the kind is
the only choice. In IDT the kinds are the provider's models.

`--check` reports `state` as Windows does: `Ready`, `NotReady` (the model can be prepared or
downloaded), `NotSupportedOnCurrentSystem` (not a Copilot+ PC, or Windows too old) or
`DisabledByUser`. `NoIdentity` means the helper isn't installed as a package.

**From Git Bash, describing fails.** Started directly from Git Bash, `--describe` and `--serve`
answer every picture with `internal_error` ("InternalError"), reproducibly; from cmd, PowerShell
or Python (which is how IDT starts it) the same picture is described. The cause isn't known. Test
from cmd or PowerShell.

## The protocol

`--serve` reads one request per line and answers each in order, one line per answer, each
ending in a line feed alone (no carriage return). Blank lines get no answer. It exits when its input closes, so it ends
with IDT however IDT ends; a describe already running finishes first, so IDT also has its own
timeout. There is no handshake: IDT runs `--check` first, which reports the `protocol` version.

```
{"id": 7, "kind": "accessible", "mime": "image/jpeg", "image": "<base64>"}
{"id": 7, "ok": true,  "kind": "accessible", "text": "...", "seconds": 2.41}
{"id": 7, "ok": false, "code": "content_filtered", "message": "..."}
```

`mime` is one of image/jpeg, png, bmp, gif or tiff; IDT converts anything else to JPEG first.
`id` must be a whole number and is echoed in the answer; it is 0 in an answer to a request whose
id couldn't be read (not JSON, a repeated key, an id that isn't a whole number, or a line too
long to read). A picture can be at most 20 MB; IDT sends at most about 4 MB. The failure codes
are the contract with IDT, which decides what each means for a batch:

| Code | Meaning |
|---|---|
| `content_filtered` | Windows' content filter declined the picture, its text, or the description |
| `too_much_text` | The picture is mostly text; OCR suits it better |
| `blocked_by_policy` | A policy on this PC blocks the feature |
| `not_supported` | Not a Copilot+ PC, or Windows is too old |
| `disabled_by_user` | Windows' AI features are turned off in Settings |
| `not_ready` | The model couldn't be made ready (often still downloading) |
| `unsupported_format`, `decode_failed` | The picture's type isn't accepted, or its bytes aren't a picture of that type |
| `too_large` | The picture, or the whole request line, is over the 20 MB limit |
| `bad_request` | The request itself was malformed: not JSON, a repeated key, an id that isn't a whole number, a field of the wrong type, an unknown kind, bad base64 |
| `internal_error` | Anything else Windows or the helper reports. The helper then drops the model and starts it afresh for the next picture |

## Building

Needs the .NET 10 SDK. From this folder:

```
.\build_helper.ps1                  # this PC's architecture, into out\<arch>
.\build_helper.ps1 -Arch x64        # or arm64
.\build_helper.ps1 -Register        # and install it for this user (needs Developer Mode)
dotnet test IdtWindowsAI.Tests      # the protocol tests: run anywhere, no NPU needed
```

`out\<arch>` is a complete package layout, with the architecture, version and publisher filled
in to `AppxManifest.xml`. For a signed release, the publisher must equal the signing
certificate's subject exactly.

`-Register` installs the folder *in place*: the registered helper runs from `out\<arch>`, so
the next build replaces the installed files. Rebuild with `-Register` again, and not while the
helper is running.

**Size.** The build is self-contained (nothing to install first) and trimmed: about 48 MB per
architecture rather than 116. Trimming must leave the Windows Runtime projections whole; trimmed,
every description fails with `internal_error` ("InternalError"), because the model is reached by
Windows Runtime activation the trimmer can't follow. They are listed as `TrimmerRootAssembly` in
the project. A trimming change needs re-testing on a Copilot+ PC: CI can't catch this.

## Files

- `IdtWindowsAI\Protocol.cs`: requests, responses, limits, failure codes and messages. Plain C#, tested.
- `IdtWindowsAI\Server.cs`: the `--serve` loop and its capped line reader. Plain C#, tested.
- `IdtWindowsAI\Describer.cs`: the only code that calls Windows' AI API.
- `IdtWindowsAI\Program.cs`: the command-line modes, and restarting with identity.
- `IdtWindowsAI\KillOnCloseJob.cs`: the Windows job that ties a restarted copy to its starter.
- `IdtWindowsAI\AppxManifest.xml`: the package manifest, with placeholders the build fills.
- `IdtWindowsAI.Tests\`: protocol and serve-loop tests, run in CI by `.github/workflows/windows-ai-helper.yml`.

## Measured on a Copilot+ PC

Snapdragon X Elite, Hexagon NPU, Windows build 26340, 10/6/2026:

- `--check`: 0.7 s.
- Describing, in one `--serve` process: typically 2.4 s a picture, with occasional 9 to 12 s
  outliers when Windows is using the NPU for something else.
- **On photos the descriptions were accurate and detailed.** A waterfall in Hawaii got the
  rainforest, the cliff, the pool and the canopy right.
- **On screenshots it reads the text and guesses the rest.** It called Notepad "a Windows Command
  Prompt", and it invented buttons that weren't there. Photos are what IDT describes.
