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
  the package's identity. Started as `IdtWindowsAI.exe` from its folder, it has no identity; it
  notices and starts itself again through `idt-windows-ai`.

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

## The protocol

`--serve` reads one request per line and answers each in order, one line per answer. It exits
when its input closes, so it ends with IDT however IDT ends.

```
{"id": 7, "kind": "accessible", "mime": "image/jpeg", "image": "<base64>"}
{"id": 7, "ok": true,  "kind": "accessible", "text": "...", "seconds": 2.41}
{"id": 7, "ok": false, "code": "content_filtered", "message": "..."}
```

`mime` is one of image/jpeg, png, bmp, gif or tiff; IDT converts anything else to JPEG first. The
failure codes are the contract with IDT, which decides what each means for a batch:

| Code | Meaning |
|---|---|
| `content_filtered` | Windows' content filter declined the picture, its text, or the description |
| `too_much_text` | The picture is mostly text; OCR suits it better |
| `blocked_by_policy` | A policy on this PC blocks the feature |
| `not_supported` | Not a Copilot+ PC, or Windows is too old |
| `disabled_by_user` | Windows' AI features are turned off in Settings |
| `not_ready` | The model couldn't be made ready (often still downloading) |
| `unsupported_format`, `decode_failed` | The picture's type isn't accepted, or its bytes aren't a picture of that type |
| `bad_request` | The request itself was malformed: not JSON, an unknown kind, bad base64 |
| `internal_error` | Anything else Windows or the helper reports |

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

## Files

- `IdtWindowsAI\Protocol.cs`: requests, responses, failure codes and messages. Plain C#, tested.
- `IdtWindowsAI\Describer.cs`: the only code that calls Windows' AI API.
- `IdtWindowsAI\Program.cs`: the command-line modes, and restarting with identity.
- `IdtWindowsAI\AppxManifest.xml`: the package manifest, with placeholders the build fills.
- `IdtWindowsAI.Tests\`: protocol tests, run in CI by `.github/workflows/windows-ai-helper.yml`.

## Measured on a Copilot+ PC

Snapdragon X Elite, Hexagon NPU, Windows build 26340, 10/6/2026:

- `--check`: 0.7 s.
- Describing, in one `--serve` process: typically 2.4 s a picture, with occasional 9 to 12 s
  outliers when Windows is using the NPU for something else.
- **On photos the descriptions were accurate and detailed.** A waterfall in Hawaii got the
  rainforest, the cliff, the pool and the canopy right.
- **On screenshots it reads the text and guesses the rest.** It called Notepad "a Windows Command
  Prompt", and it invented buttons that weren't there. Photos are what IDT describes.
