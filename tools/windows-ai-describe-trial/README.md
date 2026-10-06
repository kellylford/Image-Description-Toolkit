# Windows AI image description trial

A test for [#360](https://github.com/kellylford/Image-Description-Toolkit/issues/360): can an app
on a Copilot+ PC describe a picture with Windows' own on-device model
(`Microsoft.Windows.AI.Imaging.ImageDescriptionGenerator`)? It is a small C# console app, kept
apart from IDT's Python code. If the descriptions are good enough, IDT could call a packaged
helper like this one as a provider. The same idea for Hyper-V Manage's screenshots is
[kellylford/TheWorkBench#165](https://github.com/kellylford/TheWorkBench/issues/165).

## What's been found

| Run | Result |
|---|---|
| Unpackaged (`-p:WindowsPackageType=None`), as an ordinary exe | Refused at the first call: `UnauthorizedAccessException`, 0x80070005, "Access is denied". Without package identity the API won't run, however correct the code. |
| Packaged, with the `systemAIModels` capability and `MaxVersionTested` 10.0.26226.0, registered in Developer Mode | **Works.** Package identity in place, `GetReadyState` NotReady, then `EnsureReadyAsync` Success (Windows readied the model on first use), then descriptions in 2.5 to 6 seconds on the Snapdragon X Elite NPU. |

How good the descriptions are, on two 1024 by 768 screenshots of a Windows VM (2026-10-06):

- **Hyper-V Manage's viewer showing a fallback picture.** The Accessible description caught the gist from the
  on-screen text: Windows 11, Remote Desktop, a sign-in that wasn't accepted, Copy, Save and Close
  buttons. It invented a "Hyper-V window manager interface" and, in Detailed, "retry" and "search"
  options. It said nothing of the blue picture or the white window in it.
- **A desktop with Notepad open on a beach wallpaper.** The Accessible description called Notepad "a Windows
  Command Prompt", read its text, and missed the wallpaper, taskbar and window layout.

So on screenshots it leans on the text in the picture and guesses at the rest. On a photo it did
well: a waterfall in Hawaii (960 by 1280) got, in 4.5 seconds, an Accessible description of a
rainforest, the waterfall down a rocky cliff into a pool, and the green canopy, all accurate.
Photos are what IDT describes, so the next step is IDT's own test images, against its other
providers.

## Trying it

Needs a Copilot+ PC, Windows App Runtime 1.8 (installed with Windows here), and Developer Mode:
Settings, System, For developers, Developer Mode on. That lets Windows register the package
from the build folder without signing it.

```
dotnet build -c Release
powershell Add-AppxPackage -Register (Resolve-Path bin\Release\net10.0-windows10.0.26100.0\win-arm64\AppxManifest.xml)
describe-trial C:\path\to\picture.png Accessible Brief Detailed
```

Run it as `describe-trial`, the command the package adds, or run `DescribeTrial.exe` from its
folder: started without the package's identity, it restarts itself through `describe-trial`.
It prints the package identity, whether the model is ready (the first time, Windows may
download it), and each description with how long it took. To remove it:

```
powershell "Get-AppxPackage TheWorkBench.DescribeTrial | Remove-AppxPackage"
```

## Files

- `Program.cs`: the trial, one step at a time so a failure says where.
- `AppxManifest.xml`: the package identity, the `systemAIModels` capability, the
  `MaxVersionTested` the docs require, the Windows App Runtime 1.8 dependency, and the
  `describe-trial` command.
- `Assets\`: the plain logos a package must have.
