<#
.SYNOPSIS
Sets up Windows AI for the person running it. IDT's installer runs this; it can also be run by hand.

.DESCRIPTION
Installs IDT's Windows AI helper package for the current user, first adding the Windows App
Runtime 1.8 it depends on if this PC doesn't have it (downloaded from Microsoft, about 100 MB).
Run as the person who will use IDT, not as an administrator elsewhere: packages are installed
per user.

Writes what it did to the log, and exits 0 when Windows AI is set up or this PC can't use it
(Windows older than 11 24H2), 1 when setting it up failed. IDT works without it either way.

.PARAMETER Package
The helper's .msix for this PC's architecture.

.PARAMETER Arch
x64 or arm64: this PC's architecture, for the runtime.

.PARAMETER Log
Where to write what happened.

.PARAMETER Remove
Remove the helper package instead.
#>
param(
    [string]$Package,
    [ValidateSet('x64', 'arm64')]
    [string]$Arch = 'x64',
    [string]$Log = (Join-Path $env:TEMP 'idt_windows_ai_setup.log'),
    [switch]$Remove
)
$ErrorActionPreference = 'Stop'

$PackageName = 'ImageDescriptionToolkit.WindowsAI'
$Runtime = 'Microsoft.WindowsAppRuntime.1.8'
# The runtime the helper is built against (IdtWindowsAI.csproj's Windows App SDK packages, and
# the MinVersion in its AppxManifest.xml). Pinned, so the download is the version tested.
$RuntimeMinVersion = [version]'8000.994.2142.0'
$RuntimeInstaller = "https://aka.ms/windowsappsdk/1.8/1.8.260921001/windowsappruntimeinstall-$Arch.exe"

function Say([string]$message) {
    try { Add-Content -LiteralPath $Log -Value ("{0:yyyy-MM-dd HH:mm:ss} {1}" -f (Get-Date), $message) -Encoding UTF8 } catch { }
}

try {
    if ($Remove) {
        $installed = Get-AppxPackage -Name $PackageName
        if ($installed) {
            $installed | Remove-AppxPackage
            Say "Removed $($installed.PackageFullName)."
        }
        exit 0
    }

    $build = [Environment]::OSVersion.Version.Build
    if ($build -lt 26100) {
        Say "Windows build $build. Windows AI needs Windows 11 24H2 (build 26100) or later; not set up."
        exit 0
    }
    if (-not $Package -or -not (Test-Path -LiteralPath $Package)) { throw "The helper package isn't at '$Package'." }

    $runtime = Get-AppxPackage -Name $Runtime | Where-Object {
        "$($_.Architecture)" -eq $Arch -and [version]$_.Version -ge $RuntimeMinVersion
    }
    if ($runtime) {
        Say "Windows App Runtime 1.8 is already installed ($($runtime[0].Version))."
    } else {
        Say "Windows App Runtime 1.8 isn't installed; downloading it from Microsoft."
        $setup = Join-Path $env:TEMP "WindowsAppRuntimeInstall-$Arch.exe"
        $ProgressPreference = 'SilentlyContinue'   # the progress bar slows the download a lot
        Invoke-WebRequest -Uri $RuntimeInstaller -OutFile $setup -UseBasicParsing
        $signature = Get-AuthenticodeSignature -LiteralPath $setup
        if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'O=Microsoft Corporation') {
            throw "The downloaded runtime installer isn't signed by Microsoft ($($signature.Status)); not run."
        }
        $run = Start-Process -FilePath $setup -ArgumentList '--quiet' -Wait -PassThru
        Remove-Item -LiteralPath $setup -Force -ErrorAction SilentlyContinue
        if ($run.ExitCode -ne 0) { throw "The Windows App Runtime installer failed (exit code $($run.ExitCode))." }
        Say 'Installed the Windows App Runtime 1.8.'
    }

    # ForceUpdateFromAnyVersion: an IDT downgrade or reinstall replaces the helper too.
    Add-AppxPackage -Path $Package -ForceUpdateFromAnyVersion -ForceApplicationShutdown
    $helper = Get-AppxPackage -Name $PackageName
    Say "Installed $($helper.PackageFullName)."
    exit 0
}
catch {
    Say "Windows AI wasn't set up: $($_.Exception.Message)"
    exit 1
}
