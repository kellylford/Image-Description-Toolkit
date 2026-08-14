# speak-voices.ps1
# Reports every speech route available on this machine, as JSON.
#
# Used by the `voice-setup` skill so Claude can offer real choices instead of guessing at
# what is installed. Safe to run at any time; changes nothing.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File speak-voices.ps1

$ErrorActionPreference = 'SilentlyContinue'

$result = [ordered]@{
    screenReaders = @()
    systemVoices  = @()
    notes         = @()
}

# --- JAWS -------------------------------------------------------------------------------
# Speaking through JAWS means the user's own voice, rate, and punctuation settings apply,
# and their normal silence key interrupts it. Nothing here can or should override that.
$jawsRunning = [bool](Get-Process jfw -ErrorAction SilentlyContinue)
$jawsCom = $false
try {
    $j = New-Object -ComObject FreedomSci.JawsApi -ErrorAction Stop
    $jawsCom = $true
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($j) | Out-Null
} catch { }

if ($jawsCom) {
    $result.screenReaders += [ordered]@{
        engine    = 'jaws'
        name      = 'JAWS'
        available = $true
        running   = $jawsRunning
        rateControlledByApp = $false
        detail    = if ($jawsRunning) { 'FreedomSci.JawsApi registered, JAWS running' }
                    else { 'FreedomSci.JawsApi registered, but JAWS is not running right now' }
    }
}

# --- NVDA -------------------------------------------------------------------------------
# NVDA speech goes through the controller client DLL, which is NOT installed with NVDA — it
# ships separately in NV Access's controller client package. Report NVDA whenever it is
# *installed*, not only when running: an earlier version of this script keyed off the running
# process and reported NVDA absent on a machine where it was installed and used daily.
#
# The DLL must match the architecture of the calling process, not of NVDA. On ARM64 Windows
# an ARM64 PowerShell cannot load the x64 build at all — it throws BadImageFormatException.
$nvdaRunning = [bool](Get-Process nvda -ErrorAction SilentlyContinue)

$nvdaInstalled = $false
$nvdaVersion = $null
foreach ($k in @('HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
                 'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*',
                 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*')) {
    $e = Get-ItemProperty $k -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -match 'NVDA' } | Select-Object -First 1
    if ($e) { $nvdaInstalled = $true; $nvdaVersion = $e.DisplayName; break }
}
if (-not $nvdaInstalled) {
    foreach ($p in @("$env:ProgramFiles\NVDA", "${env:ProgramFiles(x86)}\NVDA", "$env:LOCALAPPDATA\Programs\NVDA")) {
        if (Test-Path $p) { $nvdaInstalled = $true; break }
    }
}

# PE machine type, so an unusable DLL is reported as unusable rather than as "found".
function Get-PeArch([string]$path) {
    try {
        $fs = [System.IO.File]::OpenRead($path)
        $br = New-Object System.IO.BinaryReader($fs)
        $fs.Position = 0x3C
        $peOffset = $br.ReadInt32()
        $fs.Position = $peOffset + 4
        $machine = $br.ReadUInt16()
        $br.Close(); $fs.Close()
        switch ($machine) {
            0x8664  { 'x64' }
            0x014c  { 'x86' }
            0xAA64  { 'ARM64' }
            default { ('unknown 0x{0:X4}' -f $machine) }
        }
    } catch { 'unreadable' }
}

$procArch = $env:PROCESSOR_ARCHITECTURE
$nvdaDll = $null
$nvdaDllArch = $null
$rejected = @()
$searchRoots = @(
    "$env:USERPROFILE\.claude",
    "$env:ProgramFiles\NVDA",
    "${env:ProgramFiles(x86)}\NVDA",
    "$env:LOCALAPPDATA\Programs\NVDA",
    "$env:USERPROFILE\Downloads"
)
foreach ($root in $searchRoots) {
    if (-not (Test-Path $root)) { continue }
    foreach ($hit in (Get-ChildItem $root -Recurse -Filter 'nvdaControllerClient*.dll' -Depth 4 -ErrorAction SilentlyContinue)) {
        $arch = Get-PeArch $hit.FullName
        if ($arch -eq $procArch -or ($arch -eq 'x64' -and $procArch -eq 'AMD64')) {
            $nvdaDll = $hit.FullName; $nvdaDllArch = $arch; break
        }
        $rejected += "$($hit.FullName) is $arch"
    }
    if ($nvdaDll) { break }
}

if ($nvdaInstalled -or $nvdaRunning -or $nvdaDll) {
    $detail = if ($nvdaDll) {
        "controller client ($nvdaDllArch) at $nvdaDll"
    } elseif ($rejected.Count) {
        "found a controller client, but the wrong architecture for this $procArch process. Need an $procArch build. Rejected: " + ($rejected -join '; ')
    } else {
        "no controller client DLL found. It does NOT ship with NVDA - get the $procArch build from NV Access's controller client package and put it in %USERPROFILE%\.claude"
    }
    $result.screenReaders += [ordered]@{
        engine       = 'nvda'
        name         = 'NVDA'
        installed    = $nvdaInstalled
        version      = $nvdaVersion
        available    = [bool]$nvdaDll      # available means "we can actually call it"
        running      = $nvdaRunning
        rateControlledByApp = $false
        processArch  = $procArch
        dllPath      = $nvdaDll
        dllArch      = $nvdaDllArch
        detail       = $detail
    }
}

# --- OneCore voices (WinRT) -------------------------------------------------------------
try {
    [Windows.Media.SpeechSynthesis.SpeechSynthesizer, Windows.Media, ContentType = WindowsRuntime] | Out-Null
    foreach ($v in [Windows.Media.SpeechSynthesis.SpeechSynthesizer]::AllVoices) {
        $result.systemVoices += [ordered]@{
            engine      = 'onecore'
            id          = $v.Id
            displayName = $v.DisplayName
            language    = $v.Language
            gender      = [string]$v.Gender
            # The substring speak-engine.ps1 matches on.
            match       = ($v.Id -split '\\')[-1]
            rateRange   = '0.5 to 6.0 (6 = fastest)'
        }
    }
} catch {
    $result.notes += "OneCore voices unavailable: $($_.Exception.Message)"
}

# --- SAPI 5 "Desktop" voices ------------------------------------------------------------
try {
    Add-Type -AssemblyName System.Speech
    $s = New-Object System.Speech.Synthesis.SpeechSynthesizer
    foreach ($v in $s.GetInstalledVoices()) {
        if (-not $v.Enabled) { continue }
        $result.systemVoices += [ordered]@{
            engine      = 'sapi'
            id          = $v.VoiceInfo.Id
            displayName = $v.VoiceInfo.Name
            language    = [string]$v.VoiceInfo.Culture
            gender      = [string]$v.VoiceInfo.Gender
            match       = $v.VoiceInfo.Name
            rateRange   = '-10 to 10 (10 = fastest)'
        }
    }
    $s.Dispose()
} catch {
    $result.notes += "SAPI voices unavailable: $($_.Exception.Message)"
}

if (-not $result.screenReaders) {
    $result.notes += 'No screen reader speech API detected. System voices only.'
}
$result.notes += 'OneCore and SAPI are separate sets. A name appearing in both (e.g. Zira) is two different voices; OneCore generally sounds cleaner.'

$result | ConvertTo-Json -Depth 6
