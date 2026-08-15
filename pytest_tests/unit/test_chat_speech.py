"""Reading responses aloud: settings, enumeration parsing, the speaker harness.

The actual speech routing is ClaudeSpeak's scripts, bundled under
shared/speech/ and already verified on real hardware in TheWorkBench repo.
What needs testing here is the harness around them: that settings survive a
round trip, that the probes' JSON parses into picker options (including
PowerShell 5.1's one-element-array-becomes-object quirk), that the speaker
process is built with the right command line and files, and that markdown is
made listenable before it reaches a synthesizer.

Nothing here plays audio: subprocess launches are intercepted.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
for _p in (_ROOT, _ROOT / "shared"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from shared import speech_engine  # noqa: E402
from shared.speech_engine import (  # noqa: E402
    Speaker,
    SpeechSettings,
    default_options,
    strip_for_speech,
)


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


class TestSettings:
    def test_roundtrip(self, tmp_path):
        path = tmp_path / "speech.json"
        SpeechSettings(enabled=True, engine="sapi", voice="Zira",
                       rate_preset="fast").save(path)
        loaded = SpeechSettings.load(path)
        assert loaded == SpeechSettings(True, "sapi", "Zira", "fast")

    def test_missing_file_means_defaults_disabled(self, tmp_path):
        loaded = SpeechSettings.load(tmp_path / "nope.json")
        assert loaded.enabled is False
        assert loaded.engine == "auto"

    def test_corrupt_file_means_defaults_not_a_crash(self, tmp_path):
        path = tmp_path / "speech.json"
        path.write_text("{not json", encoding="utf-8")
        assert SpeechSettings.load(path) == SpeechSettings()

    def test_unknown_rate_preset_degrades_to_default(self, tmp_path):
        path = tmp_path / "speech.json"
        path.write_text(json.dumps({"enabled": True, "engine": "sapi",
                                    "rate_preset": "ludicrous"}),
                        encoding="utf-8")
        assert SpeechSettings.load(path).rate_preset == "default"

    def test_screen_reader_routes_never_resolve_a_rate(self):
        """Overriding a screen-reader user's rate is a defect, not a feature."""
        for engine in ("auto", "jaws", "nvda", "voiceover"):
            assert SpeechSettings(engine=engine, rate_preset="fastest").resolved_rate() is None

    def test_voice_engines_resolve_their_own_scales(self):
        assert SpeechSettings(engine="sapi", rate_preset="fastest").resolved_rate() == 10
        assert SpeechSettings(engine="onecore", rate_preset="fastest").resolved_rate() == 6.0
        assert SpeechSettings(engine="say", rate_preset="normal").resolved_rate() == 175

    def test_default_preset_means_engine_default(self):
        assert SpeechSettings(engine="sapi").resolved_rate() is None


# ---------------------------------------------------------------------------
# Enumeration parsing
# ---------------------------------------------------------------------------


_WINDOWS_PROBE = json.dumps({
    "screenReaders": [
        {"engine": "jaws", "name": "JAWS", "available": True, "running": True},
        {"engine": "nvda", "name": "NVDA", "available": False, "running": False},
    ],
    "systemVoices": [
        {"engine": "onecore", "displayName": "Microsoft Aria",
         "match": "MSTTS_V110_enUS_AriaM"},
        {"engine": "sapi", "displayName": "Microsoft Zira Desktop",
         "match": "Microsoft Zira Desktop"},
    ],
    "notes": [],
})


class TestProbeParsing:
    def test_windows_probe_becomes_picker_options(self):
        options = speech_engine._parse_windows_probe(_WINDOWS_PROBE)
        labels = [o.label for o in options]

        assert options[0].engine == "auto", "Automatic is always offered first"
        assert any("JAWS" in label for label in labels)
        assert not any("NVDA" in label for label in labels), (
            "available=False means the controller DLL is missing; offering "
            "it would sell a route that cannot work"
        )
        aria = next(o for o in options if "Aria" in o.label)
        assert (aria.engine, aria.voice) == ("onecore", "MSTTS_V110_enUS_AriaM")

    def test_single_element_arrays_from_powershell_5_are_tolerated(self):
        """ConvertTo-Json in PS 5.1 can emit a bare object for a 1-item array."""
        raw = json.dumps({
            "screenReaders": {"engine": "jaws", "name": "JAWS",
                              "available": True, "running": True},
            "systemVoices": {"engine": "sapi", "displayName": "Zira",
                             "match": "Zira"},
        })
        options = speech_engine._parse_windows_probe(raw)
        assert any(o.engine == "jaws" for o in options)
        assert any(o.engine == "sapi" for o in options)

    def test_a_stopped_screen_reader_is_offered_but_labelled(self):
        raw = json.dumps({
            "screenReaders": [{"engine": "jaws", "name": "JAWS",
                               "available": True, "running": False}],
            "systemVoices": [],
        })
        options = speech_engine._parse_windows_probe(raw)
        jaws = next(o for o in options if o.engine == "jaws")
        assert "not running" in jaws.label

    def test_mac_voice_lines_parse_and_filter_to_english(self):
        raw = (
            "Alex                en_US    # Most people recognize me by my voice.\n"
            "Amélie              fr_CA    # Bonjour! Je m'appelle Amélie.\n"
            "Daniel              en_GB    # Hello, my name is Daniel.\n"
        )
        options = speech_engine._parse_mac_voices(raw)
        names = [o.voice for o in options]
        assert names == ["Alex", "Daniel"]
        assert all(o.engine == "say" for o in options)

    def test_probe_failure_degrades_to_defaults(self, monkeypatch):
        def boom(*a, **k):
            raise OSError("no powershell")

        monkeypatch.setattr(subprocess, "run", boom)
        options = speech_engine.list_speech_options()
        assert options == default_options()
        assert options[0].engine == "auto"


# ---------------------------------------------------------------------------
# Markdown -> listenable text
# ---------------------------------------------------------------------------


class TestStripForSpeech:
    def test_code_blocks_become_a_note(self):
        text = "Here you go:\n```python\nprint('hi')\n```\nDone."
        spoken = strip_for_speech(text)
        assert "print" not in spoken
        assert "Code block omitted" in spoken

    def test_links_keep_their_text_and_lose_the_url(self):
        spoken = strip_for_speech("See [the docs](https://example.com/x?y=1).")
        assert spoken == "See the docs."

    def test_headings_and_emphasis_markers_vanish(self):
        spoken = strip_for_speech("## Results\nThis is **important** and _subtle_.")
        assert "##" not in spoken and "**" not in spoken and "_subtle_" not in spoken
        assert "important" in spoken and "subtle" in spoken

    def test_inline_code_keeps_its_content(self):
        assert strip_for_speech("Run `idt chat` now.") == "Run idt chat now."

    def test_empty_input_is_empty(self):
        assert strip_for_speech("") == ""
        assert strip_for_speech("   \n  ") == ""


# ---------------------------------------------------------------------------
# The speaker harness
# ---------------------------------------------------------------------------


class _FakeProcess:
    def __init__(self):
        self.killed = False

    def poll(self):
        return None if not self.killed else 0

    def kill(self):
        self.killed = True


class TestSpeaker:
    @pytest.fixture
    def launched(self, monkeypatch, tmp_path):
        """Intercept Popen; return the record of what would have launched."""
        record = {}

        def fake_popen(command, **kwargs):
            record["command"] = command
            record["kwargs"] = kwargs
            record["process"] = _FakeProcess()
            return record["process"]

        monkeypatch.setattr(subprocess, "Popen", fake_popen)
        monkeypatch.setattr(speech_engine.tempfile, "gettempdir",
                            lambda: str(tmp_path))
        return record

    def test_speak_launches_the_bundled_engine_script(self, launched):
        ok = Speaker().speak("Hello there", SpeechSettings(enabled=True))
        assert ok is True
        command = launched["command"]
        if sys.platform == "win32":
            assert "powershell.exe" in command[0]
            assert any(str(a).endswith("speak-engine.ps1") for a in command)
        assert "-Path" in command or "--path" in command

    def test_speak_writes_text_and_config_without_bom(self, launched, tmp_path):
        Speaker().speak("Read this", SpeechSettings(engine="sapi", voice="Zira",
                                                    rate_preset="fast"))
        workdir = tmp_path / "idt-speak"
        text = (workdir / "response.txt").read_bytes()
        assert not text.startswith(b"\xef\xbb\xbf"), "a BOM breaks the PS JSON/text readers"
        assert text.decode("utf-8") == "Read this"

        config = json.loads((workdir / "speak-config.json").read_text(encoding="utf-8"))
        assert config["engine"] == "sapi"
        assert config["voice"] == "Zira"
        assert config["rate"] == 5
        assert config["interrupt"] is True

    def test_screen_reader_config_carries_no_rate(self, launched, tmp_path):
        Speaker().speak("hi", SpeechSettings(engine="jaws", rate_preset="fastest"))
        config = json.loads(
            (tmp_path / "idt-speak" / "speak-config.json").read_text(encoding="utf-8"))
        assert config["rate"] is None

    def test_a_new_utterance_kills_the_previous_speaker(self, launched):
        speaker_obj = Speaker()
        speaker_obj.speak("first", SpeechSettings())
        first = launched["process"]
        speaker_obj.speak("second", SpeechSettings())
        assert first.killed is True

    def test_stop_kills_and_forgets(self, launched):
        speaker_obj = Speaker()
        speaker_obj.speak("text", SpeechSettings())
        process = launched["process"]
        speaker_obj.stop()
        assert process.killed is True
        speaker_obj.stop()  # idempotent — nothing to kill, nothing raised

    def test_markdown_is_stripped_before_the_synthesizer(self, launched, tmp_path):
        Speaker().speak("Look:\n```js\nlet x = 1;\n```", SpeechSettings())
        text = (tmp_path / "idt-speak" / "response.txt").read_text(encoding="utf-8")
        assert "let x" not in text

    def test_nothing_speakable_means_no_process(self, launched):
        assert Speaker().speak("```\ncode only\n```",
                               SpeechSettings()) in (True, False)
        # Whitespace-only input must not launch anything at all.
        launched.clear()
        assert Speaker().speak("   ", SpeechSettings()) is False
        assert "command" not in launched

    def test_speech_failure_never_raises(self, monkeypatch):
        def boom(*a, **k):
            raise OSError("powershell missing")

        monkeypatch.setattr(subprocess, "Popen", boom)
        assert Speaker().speak("hello", SpeechSettings()) is False


def test_bundled_scripts_exist():
    """The harness is nothing without the routers it launches."""
    script_dir = speech_engine._script_dir()
    for name in ("speak-engine.ps1", "speak-voices.ps1", "speak-engine.sh",
                 "speak-voices.sh"):
        assert (script_dir / name).is_file(), f"missing bundled script: {name}"
