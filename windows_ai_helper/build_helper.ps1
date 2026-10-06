<#
.SYNOPSIS
Builds IDT's Windows AI helper for one architecture and lays out its package.

.DESCRIPTION
Publishes IdtWindowsAI self-contained into out\<arch>, then writes AppxManifest.xml there with
the architecture, version and publisher filled in, beside the logos. That folder is a complete
package layout:
  - in Developer Mode, -Register installs it straight from the folder, for development;
  - -Pack packs it into dist\IdtWindowsAI_<arch>.msix, which the Windows build signs and IDT's
    installer installs.

.PARAMETER Arch
x64 or arm64. Defaults to this PC's architecture.

.PARAMETER Publisher
The package publisher. For a signed release it must equal the signing certificate's subject
exactly. The default is for unsigned development builds.

.PARAMETER Version
The version, as up to three numbers (IDT's own version, for a release; "4.8" means 4.8.0, and
a suffix such as " beta" is dropped). Defaults to the project's <Version>.

.PARAMETER Revision
The package version's fourth number. Windows won't install a package over one of the same
version with different contents, and every build's contents differ (the build stamps its
commit into them), so a release build passes a number unique to the build (the workflow's run
number). 0 to 65535.

.PARAMETER Register
Install the built layout for the current user (needs Developer Mode).

.PARAMETER Pack
Also pack the layout into dist\IdtWindowsAI_<arch>.msix.

.EXAMPLE
.\build_helper.ps1 -Register
idt-windows-ai --check
#>
param(
    [ValidateSet('x64', 'arm64')]
    [string]$Arch = $(if ((Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Environment').PROCESSOR_ARCHITECTURE -eq 'ARM64') { 'arm64' } else { 'x64' }),
    [string]$Publisher = 'CN=Image Description Toolkit Development',
    [string]$Version,
    [ValidateRange(0, 65535)]
    [int]$Revision = 0,
    [string]$Configuration = 'Release',
    [switch]$Register,
    [switch]$Pack
)
$ErrorActionPreference = 'Stop'

$project = Join-Path $PSScriptRoot 'IdtWindowsAI\IdtWindowsAI.csproj'
$out = Join-Path $PSScriptRoot "out\$Arch"
if (-not $Version) {
    [xml]$csproj = Get-Content -LiteralPath $project
    $Version = ($csproj.Project.PropertyGroup | Where-Object { $_.Version } | Select-Object -First 1).Version
    if (-not $Version) { throw "IdtWindowsAI.csproj has no <Version>; the package needs one." }
}
# IDT's VERSION can carry a suffix ("4.8.0 beta") or have two parts ("4.0"); a package
# version is four numbers.
if ($Version -notmatch '^\s*(\d+)(?:\.(\d+))?(?:\.(\d+))?') { throw "Version '$Version' doesn't start with a number." }
$numbers = @($Matches[1], $(if ($Matches[2]) { $Matches[2] } else { '0' }), $(if ($Matches[3]) { $Matches[3] } else { '0' }))
$assemblyVersion = $numbers -join '.'
$packageVersion = "$assemblyVersion.$Revision"

if (Test-Path -LiteralPath $out) { Remove-Item -LiteralPath $out -Recurse -Force }
dotnet publish $project -c $Configuration -r "win-$Arch" -o $out --nologo "-p:Version=$assemblyVersion"
if ($LASTEXITCODE -ne 0) { throw "dotnet publish failed for $Arch." }

$manifest = (Get-Content -LiteralPath (Join-Path $PSScriptRoot 'IdtWindowsAI\AppxManifest.xml') -Raw).
    Replace('$ARCH$', $Arch).
    Replace('$VERSION$', $packageVersion).
    Replace('$PUBLISHER$', [Security.SecurityElement]::Escape($Publisher))
Set-Content -LiteralPath (Join-Path $out 'AppxManifest.xml') -Value $manifest -Encoding UTF8
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'IdtWindowsAI\Assets') -Destination (Join-Path $out 'Assets') -Recurse -Force
# Debug symbols are for development, not for every installed copy.
Get-ChildItem -LiteralPath $out -Filter *.pdb | Remove-Item -Force

Write-Host "Built the Windows AI helper $packageVersion for $Arch in $out"

if ($Pack) {
    # makeappx comes with the Windows SDK build tools package, which restoring the project has
    # just put in the NuGet cache, so it is there on any machine that got this far, CI included.
    $packages = if ($env:NUGET_PACKAGES) { $env:NUGET_PACKAGES } else { Join-Path $env:USERPROFILE '.nuget\packages' }
    # This process's own architecture, so the makeappx it starts runs natively or emulated alike.
    $hostArch = if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64') { 'arm64' } else { 'x64' }
    $makeappx = Get-ChildItem (Join-Path $packages 'microsoft.windows.sdk.buildtools') -Recurse -Filter makeappx.exe -ErrorAction SilentlyContinue |
        Where-Object { $_.Directory.Name -eq $hostArch } | Sort-Object FullName -Descending | Select-Object -First 1
    if (-not $makeappx) { throw "makeappx.exe isn't in the NuGet cache ($packages); restore the project first." }
    $dist = Join-Path $PSScriptRoot 'dist'
    New-Item -ItemType Directory -Force -Path $dist | Out-Null
    $msix = Join-Path $dist "IdtWindowsAI_$Arch.msix"
    # makeappx lists every file it packs; only worth showing when it fails.
    $packLog = & $makeappx.FullName pack /d $out /p $msix /o /nv 2>&1
    if ($LASTEXITCODE -ne 0) { $packLog | Write-Host; throw "makeappx couldn't pack $out." }
    Write-Host "Packed $msix (unsigned: the Windows build signs it)"
}

if ($Register) {
    Add-AppxPackage -Register (Join-Path $out 'AppxManifest.xml') -ForceUpdateFromAnyVersion
    Write-Host 'Registered for this user. Try: idt-windows-ai --check'
}
