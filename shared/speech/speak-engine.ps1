# speak-engine.ps1
# Speaks a text file through whichever route speak-config.json selects.
#
# Drop-in replacement for speak-onecore.ps1 — same -Path signature — so switching is a
# one-word edit in speak-response.ps1. Configure it with the `voice-setup` skill rather than
# by hand.
#
# Routes:
#   jaws     FreedomSci.JawsApi COM. Uses the user's own voice, rate and punctuation
#            settings, and their normal silence key interrupts it. Rate here is ignored,
#            deliberately: overriding a screen-reader user's configured rate would be a
#            defect, not a feature.
#   nvda     nvdaControllerClient64.dll. Same reasoning. The DLL is NOT installed with NVDA;
#            it comes from NV Access's controller-client package.
#   onecore  Windows WinRT voices. Cleaner than the SAPI set. Rate 0.5-6.0.
#   sapi     Older SAPI 5 "Desktop" voices. Rate -10..10.
#   auto     A running screen reader if there is one, else onecore.
#
# Never throws: a speech failure must not disrupt the session.

param(
    [Parameter(Mandatory = $true)][string]$Path,
    [string]$ConfigPath = (Join-Path $env:USERPROFILE '.claude\speak-config.json')
)

$ErrorActionPreference = 'SilentlyContinue'

$text = [System.IO.File]::ReadAllText($Path)
if ([string]::IsNullOrWhiteSpace($text)) { exit 0 }

$cfg = $null
if (Test-Path -LiteralPath $ConfigPath) {
    try { $cfg = Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json } catch { }
}
if (-not $cfg) { $cfg = [pscustomobject]@{ engine = 'auto' } }

function Get-Setting($name, $default) {
    if ($cfg.PSObject.Properties.Name -contains $name -and $null -ne $cfg.$name) { return $cfg.$name }
    return $default
}

$engine    = [string](Get-Setting 'engine' 'auto')
$voice     = [string](Get-Setting 'voice' '')
$rate      = Get-Setting 'rate' $null
$nvdaDll   = [string](Get-Setting 'nvdaClientDll' '')
$interrupt = [bool](Get-Setting 'interrupt' $true)

# ---------------------------------------------------------------------------- routes

function Try-Jaws($text, $interrupt) {
    if (-not (Get-Process jfw -ErrorAction SilentlyContinue)) { return $false }
    try {
        $j = New-Object -ComObject FreedomSci.JawsApi -ErrorAction Stop
        $ok = $j.SayString($text, $interrupt)
        [System.Runtime.InteropServices.Marshal]::ReleaseComObject($j) | Out-Null
        return [bool]$ok
    } catch { return $false }
}

# PE machine type. The DLL must match the architecture of THIS process, not of NVDA, and the
# filename cannot be trusted: NV Access shipped the ARM64 build as nvdaControllerClient32.dll
# for a while, and their arm64ec build reports x64 in its header.
function Get-PeArch([string]$p) {
    try {
        $fs = [IO.File]::OpenRead($p); $br = New-Object IO.BinaryReader($fs)
        $fs.Position = 0x3C; $o = $br.ReadInt32(); $fs.Position = $o + 4; $m = $br.ReadUInt16()
        $br.Close(); $fs.Close()
        switch ($m) { 0x8664 { 'x64' } 0x014c { 'x86' } 0xAA64 { 'ARM64' } default { 'unknown' } }
    } catch { 'unreadable' }
}

function Try-Nvda($text, $interrupt, $dllPath) {
    if (-not (Get-Process nvda -ErrorAction SilentlyContinue)) { return $false }

    $want = $env:PROCESSOR_ARCHITECTURE
    if ($want -eq 'AMD64') { $want = 'x64' }

    if ($dllPath -and (Test-Path -LiteralPath $dllPath)) {
        if ((Get-PeArch $dllPath) -ne $want) { $dllPath = $null }
    } else { $dllPath = $null }

    if (-not $dllPath) {
        foreach ($root in @("$env:USERPROFILE\.claude", "$env:ProgramFiles\NVDA",
                            "${env:ProgramFiles(x86)}\NVDA", "$env:LOCALAPPDATA\Programs\NVDA")) {
            if (-not (Test-Path $root)) { continue }
            foreach ($hit in (Get-ChildItem $root -Recurse -Filter 'nvdaControllerClient*.dll' -Depth 4 -ErrorAction SilentlyContinue)) {
                if ((Get-PeArch $hit.FullName) -eq $want) { $dllPath = $hit.FullName; break }
            }
            if ($dllPath) { break }
        }
    }
    if (-not $dllPath) { return $false }

    # DllImport binds a fixed filename, but NV Access has used both nvdaControllerClient.dll
    # (current) and nvdaControllerClient64.dll (older). Stage whatever was found under the
    # canonical name so either package works.
    $stage = Join-Path $env:TEMP 'claude-speak-nvda'
    if (-not (Test-Path $stage)) { New-Item -ItemType Directory -Path $stage -Force | Out-Null }
    $canonical = Join-Path $stage 'nvdaControllerClient.dll'
    if ((-not (Test-Path $canonical)) -or
        ((Get-Item $canonical).Length -ne (Get-Item $dllPath).Length)) {
        Copy-Item $dllPath $canonical -Force -ErrorAction SilentlyContinue
    }

    try {
        if (-not ('NvdaClient' -as [type])) {
            Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class NvdaClient {
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    public static extern bool SetDllDirectory(string path);
    [DllImport("nvdaControllerClient.dll", CharSet = CharSet.Unicode)]
    public static extern int nvdaController_testIfRunning();
    [DllImport("nvdaControllerClient.dll", CharSet = CharSet.Unicode)]
    public static extern int nvdaController_speakText(string text);
    [DllImport("nvdaControllerClient.dll", CharSet = CharSet.Unicode)]
    public static extern int nvdaController_cancelSpeech();
}
'@
        }
        # The DllImport name is unqualified, so the directory must be on the search path
        # before the first call binds it.
        [NvdaClient]::SetDllDirectory($stage) | Out-Null
        if ([NvdaClient]::nvdaController_testIfRunning() -ne 0) { return $false }
        if ($interrupt) { [NvdaClient]::nvdaController_cancelSpeech() | Out-Null }
        return ([NvdaClient]::nvdaController_speakText($text) -eq 0)
    } catch { return $false }
}

# PowerShell 5.1 has no await, so unwrap IAsyncOperation<T> by hand via AsTask. Hoisted to
# script scope rather than nested inside Try-OneCore, so it does not depend on a caller's
# locals being visible.
$script:AsTaskGeneric = $null
function Await($operation, $resultType) {
    if (-not $script:AsTaskGeneric) {
        $script:AsTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
            $_.Name -eq 'AsTask' -and
            $_.GetParameters().Count -eq 1 -and
            $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
        })[0]
    }
    $task = $script:AsTaskGeneric.MakeGenericMethod($resultType).Invoke($null, @($operation))
    $task.Wait(-1) | Out-Null
    $task.Result
}

function Try-OneCore($text, $voiceMatch, $rate) {
    try {
        Add-Type -AssemblyName System.Runtime.WindowsRuntime
        [Windows.Media.SpeechSynthesis.SpeechSynthesizer, Windows.Media, ContentType = WindowsRuntime] | Out-Null
        [Windows.Storage.Streams.DataReader, Windows.Storage.Streams, ContentType = WindowsRuntime] | Out-Null

        $synth = New-Object Windows.Media.SpeechSynthesis.SpeechSynthesizer
        if ($voiceMatch) {
            $v = [Windows.Media.SpeechSynthesis.SpeechSynthesizer]::AllVoices |
                 Where-Object { $_.Id -like "*$voiceMatch*" -or $_.DisplayName -eq $voiceMatch } |
                 Select-Object -First 1
            if ($v) { $synth.Voice = $v }
        }
        if ($null -ne $rate) { $synth.Options.SpeakingRate = [double]$rate }

        $stream = Await $synth.SynthesizeTextToStreamAsync($text) ([Windows.Media.SpeechSynthesis.SpeechSynthesisStream])
        $reader = New-Object Windows.Storage.Streams.DataReader($stream.GetInputStreamAt(0))
        Await $reader.LoadAsync([uint32]$stream.Size) ([uint32]) | Out-Null
        $bytes = New-Object byte[] $stream.Size
        $reader.ReadBytes($bytes)

        $wav = [System.IO.Path]::Combine($env:TEMP, "claude-speak-$PID.wav")
        [System.IO.File]::WriteAllBytes($wav, $bytes)
        $player = New-Object System.Media.SoundPlayer $wav
        $player.PlaySync()
        $player.Dispose()
        $synth.Dispose()
        Remove-Item -LiteralPath $wav -Force -ErrorAction SilentlyContinue
        return $true
    } catch { return $false }
}

function Try-Sapi($text, $voiceMatch, $rate) {
    try {
        Add-Type -AssemblyName System.Speech
        $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
        if ($voiceMatch) {
            $v = $synth.GetInstalledVoices() |
                 Where-Object { $_.Enabled -and ($_.VoiceInfo.Name -like "*$voiceMatch*") } |
                 Select-Object -First 1
            if ($v) { $synth.SelectVoice($v.VoiceInfo.Name) }
        }
        if ($null -ne $rate) { $synth.Rate = [int][Math]::Max(-10, [Math]::Min(10, $rate)) }
        $synth.Speak($text)
        $synth.Dispose()
        return $true
    } catch { return $false }
}

# ---------------------------------------------------------------------------- dispatch

# Configured engine first, then every other route. A machine that loses its screen reader,
# or a config naming a voice that has been uninstalled, should still speak.
$order = switch ($engine) {
    'jaws'    { @('jaws', 'nvda', 'onecore', 'sapi') }
    'nvda'    { @('nvda', 'jaws', 'onecore', 'sapi') }
    'onecore' { @('onecore', 'sapi') }
    'sapi'    { @('sapi', 'onecore') }
    default   { @('jaws', 'nvda', 'onecore', 'sapi') }   # auto
}

# Rates are per-engine scales, so resolve defaults separately rather than inline (PowerShell
# 5.1 has no `if` expression).
$oneCoreRate = 6.0
$sapiRate    = 5
if ($null -ne $rate) {
    $oneCoreRate = [double]$rate
    $sapiRate    = [int]$rate
}

# Record which route actually spoke. Falling through silently is worse than failing: a
# configured route can break and the fallback still sounds fine, so you conclude the route
# works when it never ran. That exact thing happened while this was being built — an NVDA
# config fell through to a Windows voice and was mistaken for NVDA speaking.
$logDir = Join-Path $env:TEMP 'claude-speak'
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
$logFile = Join-Path $logDir 'last-route.log'
$log = @("configured engine: $engine", "process arch: $env:PROCESSOR_ARCHITECTURE")

foreach ($route in $order) {
    $spoke = $false
    switch ($route) {
        'jaws'    { $spoke = Try-Jaws    $text $interrupt }
        'nvda'    { $spoke = Try-Nvda    $text $interrupt $nvdaDll }
        'onecore' { $spoke = Try-OneCore $text $voice $oneCoreRate }
        'sapi'    { $spoke = Try-Sapi    $text $voice $sapiRate }
    }
    if ($spoke) {
        $log += "SPOKE VIA: $route"
        if ($route -ne $engine -and $engine -ne 'auto') {
            $log += "WARNING: fell back from '$engine' to '$route' - the configured route did not work"
        }
        [System.IO.File]::WriteAllText($logFile, ($log -join "`r`n"))
        exit 0
    }
    $log += "failed: $route"
}

$log += 'NOTHING SPOKE - every route failed'
[System.IO.File]::WriteAllText($logFile, ($log -join "`r`n"))
exit 0
