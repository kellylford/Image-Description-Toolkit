"""Read chat responses aloud through the user's screen reader or a system voice.

The actual speech routing is ClaudeSpeak's (TheWorkBench repo), bundled
verbatim: ``shared/speech/speak-engine.ps1`` routes JAWS → NVDA → OneCore →
SAPI on Windows, ``shared/speech/speak-engine.sh`` routes VoiceOver → say on
macOS. Both were verified on real hardware there; this module is only the
harness around them — settings, engine/voice enumeration, the detached
speaker process, and interruption by killing the previous speaker before
starting the next (the same process model ClaudeSpeak uses for its Claude
Code hook).

Design rules inherited from that investigation, kept on purpose:

* **Screen-reader routes never set voice or rate.** The user already chose
  those in JAWS/NVDA/VoiceOver; overriding them is an accessibility defect,
  not a feature.
* **Speech never blocks and never raises.** The speaker is a detached hidden
  process; a failure leaves at most ``last-route.log`` in the temp dir.
* **A clean exit only proves something spoke.** The engine scripts log which
  route actually ran, because a broken route falling back to a system voice
  is indistinguishable by ear.

No wx imports here: the module is used by the wx app but testable without it.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional

__all__ = [
    "SpeechOption",
    "SpeechSettings",
    "Speaker",
    "RATE_PRESETS",
    "default_options",
    "list_speech_options",
    "strip_for_speech",
    "speaker",
]

DEFAULT_SETTINGS_PATH = Path.home() / ".idt" / "chat_speech.json"

#: Preset -> per-engine rate value. Scales differ per engine (OneCore 0.5–6,
#: SAPI -10..10, `say` words per minute), so presets are the shared language
#: and the number is resolved at speak time. "default" means "let the engine
#: decide", and screen-reader routes ignore rate entirely.
RATE_PRESETS = {
    "onecore": {"slow": 1.0, "normal": 3.0, "fast": 4.5, "fastest": 6.0},
    "sapi": {"slow": -5, "normal": 0, "fast": 5, "fastest": 10},
    "say": {"slow": 120, "normal": 175, "fast": 300, "fastest": 450},
}

RATE_PRESET_LABELS = ["default", "slow", "normal", "fast", "fastest"]

_SCREEN_READER_ENGINES = {"auto", "jaws", "nvda", "voiceover"}


@dataclass
class SpeechOption:
    """One selectable entry for the Speech settings tab."""

    engine: str  # auto | jaws | nvda | onecore | sapi | voiceover | say
    voice: str  # match string for voice engines, "" otherwise
    label: str  # what the picker shows

    @property
    def is_screen_reader(self) -> bool:
        return self.engine in _SCREEN_READER_ENGINES

    @property
    def has_rate(self) -> bool:
        return self.engine in RATE_PRESETS


@dataclass
class SpeechSettings:
    """What the user chose. Persisted as one small JSON file."""

    enabled: bool = False
    engine: str = "auto"
    voice: str = ""
    rate_preset: str = "default"

    def resolved_rate(self):
        """The engine-scale rate number, or None for "engine default"."""
        return RATE_PRESETS.get(self.engine, {}).get(self.rate_preset)

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "SpeechSettings":
        path = path or DEFAULT_SETTINGS_PATH
        try:
            raw = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception:
            return cls()
        if not isinstance(raw, dict):
            return cls()
        settings = cls()
        settings.enabled = bool(raw.get("enabled", False))
        settings.engine = str(raw.get("engine", "auto")) or "auto"
        settings.voice = str(raw.get("voice", ""))
        preset = str(raw.get("rate_preset", "default"))
        settings.rate_preset = preset if preset in RATE_PRESET_LABELS else "default"
        return settings

    def save(self, path: Optional[Path] = None) -> None:
        path = Path(path or DEFAULT_SETTINGS_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Bundled script location
# ---------------------------------------------------------------------------


def _script_dir() -> Path:
    if getattr(sys, "frozen", False):
        # `Path(x) or fallback` never reaches the fallback: Path("") is
        # Path("."), which is truthy, so a missing _MEIPASS resolved the
        # scripts against the current working directory. Test the string.
        meipass = getattr(sys, "_MEIPASS", "")
        base = Path(meipass) if meipass else Path(sys.executable).parent
        return base / "shared" / "speech"
    return Path(__file__).resolve().parent / "speech"


# ---------------------------------------------------------------------------
# Enumeration
# ---------------------------------------------------------------------------


def default_options() -> List[SpeechOption]:
    """What the picker offers when probing fails or has not finished.

    "Automatic" always works — the engine scripts fall through to a system
    voice on their own — so a failed probe degrades to fewer choices, never
    to a broken feature.
    """
    options = [
        SpeechOption("auto", "", "Automatic (screen reader first, then a system voice)")
    ]
    if sys.platform == "win32":
        options += [
            SpeechOption("jaws", "", "JAWS screen reader"),
            SpeechOption("nvda", "", "NVDA screen reader"),
        ]
    elif sys.platform == "darwin":
        options += [
            SpeechOption("voiceover", "", "VoiceOver"),
            SpeechOption("say", "", "macOS system voice (default)"),
        ]
    return options


def _parse_windows_probe(raw: str) -> List[SpeechOption]:
    data = json.loads(raw)
    options = [
        SpeechOption("auto", "", "Automatic (screen reader first, then a system voice)")
    ]

    def _as_list(value):
        # PowerShell 5.1 serialises a one-element array as a bare object.
        if isinstance(value, dict):
            return [value]
        return value or []

    for reader in _as_list(data.get("screenReaders")):
        if not reader.get("available"):
            continue
        name = reader.get("name") or reader.get("engine", "").upper()
        suffix = "" if reader.get("running") else " (not running right now)"
        options.append(
            SpeechOption(reader.get("engine", ""), "", f"{name} screen reader{suffix}")
        )

    for voice in _as_list(data.get("systemVoices")):
        engine = voice.get("engine", "")
        if engine not in ("onecore", "sapi"):
            continue
        display = voice.get("displayName", "") or voice.get("match", "")
        kind = "OneCore" if engine == "onecore" else "SAPI"
        options.append(
            SpeechOption(engine, voice.get("match", display),
                         f"{display} — Windows voice ({kind})")
        )
    return options


def _parse_mac_voices(raw: str) -> List[SpeechOption]:
    """Voices out of ``say -v '?'`` lines, English only (there are 400+)."""
    options: List[SpeechOption] = []
    for line in raw.splitlines():
        match = re.match(r"^(.*?)\s{2,}([a-z]{2}[_-][A-Z]{2})\s+#", line)
        if not match:
            continue
        name, locale = match.group(1).strip(), match.group(2)
        if not locale.startswith("en"):
            continue
        options.append(SpeechOption("say", name, f"{name} ({locale}) — macOS voice"))
    return options


def list_speech_options(timeout: float = 25.0) -> List[SpeechOption]:
    """Probe this machine for speech routes. Falls back to defaults on error.

    Windows runs the bundled ClaudeSpeak probe (JAWS COM registration, NVDA
    controller DLL with a PE-architecture check, OneCore and SAPI voice
    lists). macOS asks ``say`` directly and checks for VoiceOver — no shell
    probe, so there is no jq dependency for enumeration.
    """
    try:
        if sys.platform == "win32":
            probe = _script_dir() / "speak-voices.ps1"
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                 "-File", str(probe)],
                capture_output=True, text=True, timeout=timeout,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if result.returncode == 0 and result.stdout.strip():
                return _parse_windows_probe(result.stdout)
        elif sys.platform == "darwin":
            options = [
                SpeechOption("auto", "",
                             "Automatic (VoiceOver if running, else a system voice)"),
                SpeechOption("voiceover", "", "VoiceOver"),
            ]
            result = subprocess.run(
                ["/usr/bin/say", "-v", "?"],
                capture_output=True, text=True, timeout=timeout,
            )
            if result.returncode == 0:
                options.extend(_parse_mac_voices(result.stdout))
            return options
    except Exception:
        # A failed probe (no PowerShell, timeout, malformed JSON) must
        # degrade to the static defaults below, never break the settings UI.
        pass
    return default_options()


# ---------------------------------------------------------------------------
# Speaking
# ---------------------------------------------------------------------------

_FENCED_CODE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE = re.compile(r"`([^`\n]+)`")
_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_HEADING = re.compile(r"^#{1,6}\s*", re.MULTILINE)
_EMPHASIS = re.compile(r"(\*{1,3})(\S(?:.*?\S)?)\1")
# Underscores only count as emphasis at a word boundary. Without the
# lookarounds this ate the internal underscores of snake_case identifiers:
# "MAX_TOOL_ROUNDS" was spoken as "MAXTOOLROUNDS" and "some_var_name" as
# "somevarname" — names that do not exist in the code being discussed.
_EMPHASIS_UNDERSCORE = re.compile(r"(?<!\w)(_{1,3})(\S(?:.*?\S)?)\1(?!\w)")


def strip_for_speech(text: str) -> str:
    """Markdown → something worth hearing.

    Code blocks become a short note instead of minutes of punctuation
    soup; links keep their text and lose their URL; heading and emphasis
    markers vanish. Deliberately light-handed — the goal is listenable, not
    a full renderer.
    """
    text = _FENCED_CODE.sub(" Code block omitted. ", text or "")
    text = _INLINE_CODE.sub(r"\1", text)
    text = _LINK.sub(r"\1", text)
    text = _HEADING.sub("", text)
    text = _EMPHASIS.sub(r"\2", text)
    text = _EMPHASIS_UNDERSCORE.sub(r"\2", text)
    text = text.replace("|", " ")
    return text.strip()


class Speaker:
    """Runs the bundled engine script as a detached process.

    One speaker at a time: starting a new utterance kills the previous
    process first (ClaudeSpeak's pid-file model, held in-process here). For
    screen-reader routes the interrupt also happens at the API level —
    ``SayString(text, true)`` / ``nvdaController_cancelSpeech()`` — because
    killing our process cannot silence speech the reader already queued.
    """

    def __init__(self):
        self._process: Optional[subprocess.Popen] = None

    @property
    def workdir(self) -> Path:
        path = Path(tempfile.gettempdir()) / "idt-speak"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _command(self, text_file: Path, config_file: Path) -> Optional[list]:
        script_dir = _script_dir()
        if sys.platform == "win32":
            return [
                "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                "-File", str(script_dir / "speak-engine.ps1"),
                "-Path", str(text_file), "-ConfigPath", str(config_file),
            ]
        if sys.platform == "darwin":
            return [
                "/bin/bash", str(script_dir / "speak-engine.sh"),
                "--path", str(text_file), "--config", str(config_file),
            ]
        return None

    def speak(self, text: str, settings: SpeechSettings) -> bool:
        """Start speaking ``text``; returns False when speech is unavailable.

        Never raises and never blocks: all the work happens in the detached
        engine process.
        """
        spoken = strip_for_speech(text)
        if not spoken:
            return False

        self.stop()
        try:
            text_file = self.workdir / "response.txt"
            config_file = self.workdir / "speak-config.json"
            # UTF-8 without BOM on purpose: the engine scripts read UTF-8,
            # and a BOM breaks ConvertFrom-Json in Windows PowerShell.
            text_file.write_text(spoken, encoding="utf-8")
            config_file.write_text(
                json.dumps(
                    {
                        "engine": settings.engine,
                        "voice": settings.voice,
                        "rate": settings.resolved_rate(),
                        "interrupt": True,
                        "nvdaClientDll": "",
                    }
                ),
                encoding="utf-8",
            )

            command = self._command(text_file, config_file)
            if command is None:
                return False
            kwargs = {}
            if sys.platform == "win32":
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            self._process = subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                **kwargs,
            )
            return True
        except Exception:
            self._process = None
            return False

    def stop(self) -> None:
        """Kill the current speaker process, if any. Never raises.

        Stops system-voice audio immediately (the synthesizer lives in that
        process). Speech already queued inside JAWS/NVDA/VoiceOver keeps
        their own silence key as the off switch — same behaviour as
        ClaudeSpeak.
        """
        process, self._process = self._process, None
        if process is None:
            return
        try:
            if process.poll() is None:
                process.kill()
        except Exception:
            # The process may have exited between poll and kill, or the OS
            # may refuse; either way there is nothing further to stop, and
            # raising from stop() would break every caller's cleanup path.
            pass


#: Module-level speaker shared by the app — one voice at a time is the point.
speaker = Speaker()
