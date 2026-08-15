"""Regressions for the findings raised after PR #266 merged.

Each test here pins one defect that shipped in #266 and was fixed on top of it.
Grouped by the thing that was wrong rather than by module, because several of
the fixes span files (the Ollama probe rework touches the provider, the
budgeter and the chat provider at once).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
for _p in (_ROOT, _ROOT / "shared"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from idt_core.providers import ollama as ollama_mod  # noqa: E402
from shared import speech_engine  # noqa: E402


# ---------------------------------------------------------------------------
# Speech: markdown cleanup must not eat code identifiers
# ---------------------------------------------------------------------------


class TestSpeechIdentifiers:
    """`_EMPHASIS` treated every underscore as markdown emphasis, so a chat
    client whose answers are full of snake_case spoke names that do not exist.
    """

    @pytest.mark.parametrize("text", [
        "use MAX_TOOL_ROUNDS and _CAPS_CACHE now",
        "call some_var_name first",
        "set num_ctx via _num_ctx()",
        "the field is max_output_tokens",
    ])
    def test_snake_case_survives(self, text):
        assert speech_engine.strip_for_speech(text) == text

    def test_real_emphasis_is_still_stripped(self):
        spoken = speech_engine.strip_for_speech(
            "This is **important** and _subtle_.")
        assert spoken == "This is important and subtle."
        assert "*" not in spoken and "_" not in spoken

    def test_underscore_emphasis_at_word_boundaries_still_works(self):
        assert speech_engine.strip_for_speech("a __bold__ start") == "a bold start"


class TestScriptDirFallback:
    """`Path(x) or fallback` never reached the fallback: Path("") is Path("."),
    which is truthy, so a frozen build without _MEIPASS looked for the speech
    scripts relative to the working directory."""

    def test_missing_meipass_resolves_next_to_the_executable(self, monkeypatch, tmp_path):
        exe_dir = tmp_path / "install"
        exe_dir.mkdir()
        monkeypatch.setattr(speech_engine.sys, "frozen", True, raising=False)
        monkeypatch.delattr(speech_engine.sys, "_MEIPASS", raising=False)
        monkeypatch.setattr(speech_engine.sys, "executable",
                            str(exe_dir / "idt.exe"), raising=False)

        resolved = speech_engine._script_dir()

        assert resolved == exe_dir / "shared" / "speech"
        assert resolved != Path("shared") / "speech", "must not be cwd-relative"

    def test_meipass_is_used_when_present(self, monkeypatch, tmp_path):
        monkeypatch.setattr(speech_engine.sys, "frozen", True, raising=False)
        monkeypatch.setattr(speech_engine.sys, "_MEIPASS", str(tmp_path), raising=False)

        assert speech_engine._script_dir() == tmp_path / "shared" / "speech"


# ---------------------------------------------------------------------------
# Ollama probes: one cached, host-keyed /api/show
# ---------------------------------------------------------------------------


class _FakeInfo:
    def __init__(self, model_info=None, parameters=None, capabilities=None):
        self.model_info = model_info
        self.parameters = parameters
        self.capabilities = capabilities


class _CountingClient:
    def __init__(self, info):
        self._info = info
        self.calls = []

    def show(self, name):
        self.calls.append(name)
        return self._info


@pytest.fixture(autouse=True)
def _clear_show_cache():
    ollama_mod._SHOW_CACHE.clear()
    ollama_mod._NEGATIVE_AT.clear()
    yield
    ollama_mod._SHOW_CACHE.clear()
    ollama_mod._NEGATIVE_AT.clear()


class TestOneProbePerModel:
    def test_capabilities_and_context_share_one_show_call(self):
        """Both were probed independently, so every chat turn issued two
        round trips to the same endpoint before the first token."""
        client = _CountingClient(_FakeInfo(
            model_info={"qwen3.context_length": 40960},
            capabilities=["completion", "thinking"],
        ))

        caps = ollama_mod.model_capabilities("qwen3", client=client)
        size = ollama_mod.model_context_length("qwen3", client=client)
        vision = ollama_mod.model_has_vision("qwen3", client=client)

        assert caps == ["completion", "thinking"]
        assert size == 40960
        assert vision is False
        assert client.calls == ["qwen3"], "one /api/show serves all three"


class TestRestFallbackTrigger:
    """The SDK drops `model_info` in some releases while still returning
    `capabilities`. The fallback must key off that field specifically — a
    check for "the whole response was empty" never fires on a real server,
    which is precisely where the fallback is needed. Caught live: context
    discovery returned None for gemma4, which reports 262,144 over REST.
    """

    def test_rest_fallback_fires_when_only_model_info_is_missing(self, monkeypatch):
        monkeypatch.setattr(
            ollama_mod, "_show_via_rest",
            lambda name, host: {"model_info": {"gemma4.context_length": 262144}},
        )

        class _SdkDropsModelInfo:
            def show(self, name):
                return _FakeInfo(model_info=None, capabilities=["completion"])

        import types
        monkeypatch.setitem(
            sys.modules, "ollama",
            types.SimpleNamespace(Client=lambda host=None: _SdkDropsModelInfo()),
        )

        assert ollama_mod.model_context_length("gemma4") == 262144
        # and the capabilities the SDK *did* return are preserved
        assert ollama_mod.model_capabilities("gemma4") == ["completion"]


class TestHostIsolation:
    def test_probes_honour_ollama_host_when_none_is_given(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_HOST", "box:11434")
        assert ollama_mod._resolve_host(None) == "http://box:11434"

    def test_explicit_host_wins_over_the_environment(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_HOST", "box:11434")
        assert ollama_mod._resolve_host("http://other:1") == "http://other:1"

    def test_default_is_localhost_without_the_variable(self, monkeypatch):
        monkeypatch.delenv("OLLAMA_HOST", raising=False)
        assert ollama_mod._resolve_host(None) == ollama_mod.DEFAULT_HOST

    def test_one_hosts_answer_is_never_served_for_another(self):
        local = _CountingClient(_FakeInfo(model_info={"llama.context_length": 4096}))
        remote = _CountingClient(_FakeInfo(model_info={"llama.context_length": 262144}))

        assert ollama_mod.model_context_length(
            "same-name", host="http://localhost:11434", client=local) == 4096
        assert ollama_mod.model_context_length(
            "same-name", host="http://box:11434", client=remote) == 262144


# ---------------------------------------------------------------------------
# num_ctx must not ask for a KV cache the machine cannot hold
# ---------------------------------------------------------------------------


class TestNumCtxCeiling:
    def _request(self, messages):
        from idt_core.chat.messages import ChatMessage
        from idt_core.providers.base import ChatRequest

        return ChatRequest(messages=messages, model="nemotron")

    def test_a_million_token_window_is_capped(self, monkeypatch):
        """Discovery reports 1,048,576 for nemotron. The budgeter will fill a
        window that size and num_ctx then asks Ollama to allocate it."""
        from idt_core.chat.messages import ChatMessage
        from idt_core.chat.providers import OllamaChatProvider

        monkeypatch.setattr(ollama_mod, "model_context_length",
                            lambda *a, **k: 1_048_576)
        provider = OllamaChatProvider("nemotron")
        request = self._request([ChatMessage(role="user", content="x" * 4_000_000)])

        num_ctx = provider._request_options(request)["num_ctx"]

        assert num_ctx == OllamaChatProvider.DEFAULT_NUM_CTX_CEILING
        assert num_ctx < 1_048_576

    def test_the_ceiling_is_overridable(self, monkeypatch):
        from idt_core.chat.messages import ChatMessage
        from idt_core.chat.providers import OllamaChatProvider

        monkeypatch.setattr(ollama_mod, "model_context_length",
                            lambda *a, **k: 1_048_576)
        monkeypatch.setenv("IDT_MAX_NUM_CTX", "262144")
        provider = OllamaChatProvider("nemotron")
        request = self._request([ChatMessage(role="user", content="x" * 4_000_000)])

        assert provider._request_options(request)["num_ctx"] == 262_144

    def test_a_small_trained_window_still_wins(self, monkeypatch):
        """The ceiling is a cap, never a licence to exceed the model."""
        from idt_core.chat.messages import ChatMessage
        from idt_core.chat.providers import OllamaChatProvider

        monkeypatch.setattr(ollama_mod, "model_context_length", lambda *a, **k: 8192)
        provider = OllamaChatProvider("small")
        request = self._request([ChatMessage(role="user", content="x" * 400_000)])

        assert provider._request_options(request)["num_ctx"] == 8192


# ---------------------------------------------------------------------------
# MLX must inline text attachments like every other formatter
# ---------------------------------------------------------------------------


def test_mlx_formatter_inlines_text_attachments(tmp_path):
    """MLX accepts images only, so nothing text-shaped can be attached while
    on MLX — but history is provider-agnostic, and a .txt attached under
    Ollama replays through the MLX formatter. It used to vanish silently."""
    import inspect

    from idt_core.chat import mlx as mlx_mod

    source = inspect.getsource(mlx_mod)
    assert "merge_text_attachments" in source, (
        "the MLX formatter must inline text attachments, not read msg.content"
    )
    assert source.count("merge_text_attachments(msg)") >= 1


def test_text_attachment_reaches_the_mlx_prompt(tmp_path):
    from idt_core.chat.messages import Attachment, ChatMessage
    from idt_core.chat.providers import merge_text_attachments

    path = tmp_path / "notes.txt"
    path.write_text("PELICAN", encoding="utf-8")
    msg = ChatMessage(role="user", content="what is in the file?",
                      attachments=[Attachment("text/plain", path=str(path))])

    merged = merge_text_attachments(msg)

    assert "PELICAN" in merged
    assert "what is in the file?" in merged
