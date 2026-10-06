<#
.SYNOPSIS
Builds IDT's Windows AI helper for one architecture and lays out its package.

.DESCRIPTION
Publishes IdtWindowsAI self-contained into out\<arch>, then writes AppxManifest.xml there with
the architecture, version and publisher filled in, beside the logos. That folder is a complete
package layout:
  - in Developer Mode, -Register installs it straight from the folder, for development;
  - for release, the build packs and signs it into an .msix (see the Windows build workflow).

.PARAMETER Arch
x64 or arm64. Defaults to this PC's architecture.

.PARAMETER Publisher
The package publisher. For a signed release it must equal the signing certificate's subject
exactly. The default is for unsigned development builds.

.PARAMETER Register
Install the built layout for the current user (needs Developer Mode).

.EXAMPLE
.\build_helper.ps1 -Register
idt-windows-ai --check
#>
param(
    [ValidateSet('x64', 'arm64')]
    [string]$Arch = $(if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64') { 'arm64' } else { 'x64' }),
    [string]$Publisher = 'CN=Image Description Toolkit Development',
    [string]$Configuration = 'Release',
    [switch]$Register
)
$ErrorActionPreference = 'Stop'

$project = Join-Path $PSScriptRoot 'IdtWindowsAI\IdtWindowsAI.csproj'
$out = Join-Path $PSScriptRoot "out\$Arch"
[xml]$csproj = Get-Content -LiteralPath $project
$version = ($csproj.Project.PropertyGroup | Where-Object { $_.Version } | Select-Object -First 1).Version
# A package version has four parts.
$packageVersion = "$version.0"

if (Test-Path -LiteralPath $out) { Remove-Item -LiteralPath $out -Recurse -Force }
dotnet publish $project -c $Configuration -r "win-$Arch" -o $out --nologo
if ($LASTEXITCODE -ne 0) { throw "dotnet publish failed for $Arch." }

$manifest = (Get-Content -LiteralPath (Join-Path $PSScriptRoot 'IdtWindowsAI\AppxManifest.xml') -Raw).
    Replace('$ARCH$', $Arch).
    Replace('$VERSION$', $packageVersion).
    Replace('$PUBLISHER$', [Security.SecurityElement]::Escape($Publisher))
Set-Content -LiteralPath (Join-Path $out 'AppxManifest.xml') -Value $manifest -Encoding UTF8
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'IdtWindowsAI\Assets') -Destination (Join-Path $out 'Assets') -Recurse -Force

Write-Host "Built the Windows AI helper $packageVersion for $Arch in $out"

if ($Register) {
    Add-AppxPackage -Register (Join-Path $out 'AppxManifest.xml') -ForceUpdateFromAnyVersion
    Write-Host 'Registered for this user. Try: idt-windows-ai --check'
}
