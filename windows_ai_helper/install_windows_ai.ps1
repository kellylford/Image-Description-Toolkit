<#
.SYNOPSIS
Sets up Windows AI for the person running it. IDT's installer runs this; it can also be run by hand.

.DESCRIPTION
On a PC with an NPU, installs IDT's Windows AI helper package for the current user, first adding
the Windows App Runtime 1.8 it depends on if this PC doesn't have it (downloaded from Microsoft,
about 100 MB). Run as the person who will use IDT: packages are installed per user.

Writes what it did to the log, and exits 0 when Windows AI is set up or this PC can't use it
(Windows older than 11 24H2, or no NPU), 1 when setting it up failed. IDT works without it.

.PARAMETER Package
The helper's .msix for this PC's architecture.

.PARAMETER Arch
x64 or arm64: this PC's architecture, for the runtime.

.PARAMETER Log
Where to write what happened.

.PARAMETER Force
Set it up even if no NPU is found, for a Copilot+ PC whose NPU Windows doesn't list as a
compute accelerator.

.PARAMETER Remove
Remove the installed helper package, for every user (needs an administrator, as the uninstaller
is). A development registration (build_helper.ps1 -Register, unsigned) is left alone.
#>
param(
    [string]$Package,
    [ValidateSet('x64', 'arm64')]
    [string]$Arch = 'x64',
    [string]$Log = (Join-Path $env:TEMP 'idt_windows_ai_setup.log'),
    [switch]$Force,
    [switch]$Remove
)
$ErrorActionPreference = 'Stop'

$PackageName = 'ImageDescriptionToolkit.WindowsAI'
$Runtime = 'Microsoft.WindowsAppRuntime.1.8'
# The runtime the helper is built against (IdtWindowsAI.csproj's Windows App SDK packages, and
# the MinVersion in its AppxManifest.xml). Pinned, so the download is the version tested.
$RuntimeMinVersion = [version]'8000.994.2142.0'
$RuntimeInstaller = "https://aka.ms/windowsappsdk/1.8/1.8.260921001/windowsappruntimeinstall-$Arch.exe"
# Add-AppxPackage's "already installed, and reinstallation was blocked": the same version with
# different contents, as a rebuild of one IDT version is. Windows gives the code only in the
# message; the exception's own HResult is a generic one.
$ReinstallBlocked = '0x80073CFB'

function Say([string]$message) {
    try { Add-Content -LiteralPath $Log -Value ("{0:yyyy-MM-dd HH:mm:ss} {1}" -f (Get-Date), $message) -Encoding UTF8 } catch { }
}

# Signed releases only: a development registration of the same name is unsigned.
function Get-Helper([switch]$AllUsers) {
    Get-AppxPackage -Name $PackageName -AllUsers:$AllUsers | Where-Object { "$($_.SignatureKind)" -ne 'None' }
}

try {
    if ($Remove) {
        foreach ($installed in @(Get-Helper -AllUsers)) {
            Remove-AppxPackage -Package $installed.PackageFullName -AllUsers
            Say "Removed $($installed.PackageFullName)."
        }
        exit 0
    }

    $build = [Environment]::OSVersion.Version.Build
    if ($build -lt 26100) {
        Say "Windows build $build. Windows AI needs Windows 11 24H2 (build 26100) or later; not set up."
        exit 0
    }
    # Windows' model runs only on a Copilot+ PC's NPU, which Windows lists as a compute
    # accelerator. Without one, setting up would download the runtime for nothing.
    $npu = @(Get-PnpDevice -Class ComputeAccelerator -PresentOnly -ErrorAction SilentlyContinue)
    if ($npu.Count -eq 0 -and -not $Force) {
        Say 'No NPU found. Windows AI needs a Copilot+ PC; not set up. (-Force sets it up anyway.)'
        exit 0
    }
    Say $(if ($npu.Count) { "NPU: $($npu[0].FriendlyName)." } else { 'No NPU found; setting up anyway (-Force).' })
    if (-not $Package -or -not (Test-Path -LiteralPath $Package)) { throw "The helper package isn't at '$Package'." }

    $runtime = Get-AppxPackage -Name $Runtime | Where-Object {
        "$($_.Architecture)" -eq $Arch -and [version]$_.Version -ge $RuntimeMinVersion
    }
    if ($runtime) {
        Say "Windows App Runtime 1.8 is already installed ($($runtime[0].Version))."
    } else {
        Say "Windows App Runtime 1.8 isn't installed; downloading it from Microsoft."
        $setup = Join-Path $env:TEMP ("WindowsAppRuntimeInstall-{0}-{1}.exe" -f $Arch, [guid]::NewGuid().ToString('N'))
        try {
            $ProgressPreference = 'SilentlyContinue'   # the progress bar slows the download a lot
            Invoke-WebRequest -Uri $RuntimeInstaller -OutFile $setup -UseBasicParsing -TimeoutSec 600
            $signature = Get-AuthenticodeSignature -LiteralPath $setup
            if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'O=Microsoft Corporation') {
                throw "The downloaded runtime installer isn't signed by Microsoft ($($signature.Status)); not run."
            }
            $run = Start-Process -FilePath $setup -ArgumentList '--quiet' -Wait -PassThru
            if ($run.ExitCode -ne 0) { throw "The Windows App Runtime installer failed (exit code $($run.ExitCode))." }
        }
        finally {
            Remove-Item -LiteralPath $setup -Force -ErrorAction SilentlyContinue
        }
        Say 'Installed the Windows App Runtime 1.8.'
    }

    try {
        # ForceUpdateFromAnyVersion: an older IDT's helper installs over a newer one too.
        Add-AppxPackage -Path $Package -ForceUpdateFromAnyVersion -ForceApplicationShutdown
    }
    catch {
        if ($_.Exception.Message -notmatch $ReinstallBlocked) { throw }
        # The same version with different contents. Windows won't replace it in place, so
        # remove it and add this one.
        Say 'The same version is installed with different contents; replacing it.'
        Get-Helper | ForEach-Object { Remove-AppxPackage -Package $_.PackageFullName }
        Add-AppxPackage -Path $Package -ForceApplicationShutdown
    }
    Say "Installed $((Get-Helper | Select-Object -First 1).PackageFullName)."
    exit 0
}
catch {
    Say "Windows AI wasn't set up: $($_.Exception.Message)"
    exit 1
}
