"""Ollama context-length discovery (`model_context_length`).

Ollama's server applies its own default num_ctx (4,096 on current builds)
unless the request says otherwise, while the chat token budgeter used to
assume a flat 32,768 — so long conversations were silently truncated
server-side. Discovery reads the real figure from /api/show so both the
budgeter (`context_window_for`) and ImageDescriber's token gauge agree with
the server. One implementation, tested here.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from idt_core.providers import ollama as ollama_mod  # noqa: E402
from idt_core.providers.ollama import model_context_length  # noqa: E402


class _FakeInfo:
    def __init__(self, model_info=None, parameters=None):
        self.model_info = model_info
        self.parameters = parameters


class _FakeClient:
    def __init__(self, info, raise_on=None):
        self._info = info
        self._raise_on = raise_on or set()
        self.calls = []

    def show(self, name):
        self.calls.append(name)
        if name in self._raise_on:
            raise RuntimeError("api unreachable")
        return self._info


@pytest.fixture(autouse=True)
def _clear_cache():
    ollama_mod._SHOW_CACHE.clear()
    ollama_mod._NEGATIVE_AT.clear()
    yield
    ollama_mod._SHOW_CACHE.clear()
    ollama_mod._NEGATIVE_AT.clear()


class TestModelContextLength:
    def test_reads_architecture_prefixed_model_info_key(self):
        c = _FakeClient(_FakeInfo(model_info={"llama.context_length": 131072}))
        assert model_context_length("llama3.1", client=c) == 131072

    def test_falls_back_to_num_ctx_in_the_parameters_string(self):
        """Older Ollama builds report num_ctx in `parameters` only."""
        c = _FakeClient(_FakeInfo(parameters="stop <|end|>\nnum_ctx 8192\n"))
        assert model_context_length("old-model", client=c) == 8192

    def test_model_info_wins_over_parameters(self):
        c = _FakeClient(
            _FakeInfo(
                model_info={"qwen3.context_length": 40960},
                parameters="num_ctx 4096",
            )
        )
        assert model_context_length("qwen3", client=c) == 40960

    def test_dict_shaped_responses_are_read_too(self):
        """The SDK has returned both objects and plain dicts across versions."""
        c = _FakeClient({"model_info": {"gemma.context_length": 8192}})
        assert model_context_length("gemma", client=c) == 8192

    def test_none_when_nothing_is_reported(self):
        c = _FakeClient(_FakeInfo())
        assert model_context_length("m", client=c) is None

    def test_none_when_the_query_errors(self):
        c = _FakeClient(_FakeInfo(), raise_on={"m"})
        assert model_context_length("m", client=c) is None

    def test_unparseable_values_are_skipped_not_fatal(self):
        c = _FakeClient(
            _FakeInfo(
                model_info={"x.context_length": "not-a-number"},
                parameters="num_ctx oops",
            )
        )
        assert model_context_length("m", client=c) is None

    def test_success_is_cached_per_model(self):
        c = _FakeClient(_FakeInfo(model_info={"llama.context_length": 8192}))
        assert model_context_length("m", client=c) == 8192
        assert model_context_length("m", client=c) == 8192
        assert c.calls == ["m"], "should query /api/show once per model"

    def test_failure_is_cached_only_briefly(self, monkeypatch):
        """A failed probe must not be repeated on every turn — an unreachable
        daemon would then cost a full timeout per message — but it must not be
        remembered forever either, because Ollama may simply not be running
        yet. So: cached for _NEGATIVE_TTL_SECONDS, retried after that.
        """
        clock = {"now": 1000.0}
        monkeypatch.setattr(ollama_mod.time, "monotonic", lambda: clock["now"])

        c = _FakeClient(_FakeInfo(), raise_on={"m"})
        assert model_context_length("m", client=c) is None
        assert model_context_length("m", client=c) is None
        assert c.calls == ["m"], "a second probe inside the TTL is wasted work"

        clock["now"] += ollama_mod._NEGATIVE_TTL_SECONDS + 1
        assert model_context_length("m", client=c) is None
        assert c.calls == ["m", "m"], "after the TTL the daemon is tried again"

    def test_a_recovered_daemon_is_picked_up_after_the_ttl(self, monkeypatch):
        """The whole point of expiring the negative entry."""
        clock = {"now": 500.0}
        monkeypatch.setattr(ollama_mod.time, "monotonic", lambda: clock["now"])

        c = _FakeClient(_FakeInfo(), raise_on={"m"})
        assert model_context_length("m", client=c) is None

        c._raise_on = set()
        c._info = _FakeInfo(model_info={"llama.context_length": 8192})
        clock["now"] += ollama_mod._NEGATIVE_TTL_SECONDS + 1
        assert model_context_length("m", client=c) == 8192

    def test_the_same_model_on_two_hosts_is_not_confused(self):
        """A cached answer from one server must never be served for another."""
        local = _FakeClient(_FakeInfo(model_info={"llama.context_length": 4096}))
        remote = _FakeClient(_FakeInfo(model_info={"llama.context_length": 262144}))

        assert model_context_length("m", host="http://localhost:11434",
                                    client=local) == 4096
        assert model_context_length("m", host="http://box:11434",
                                    client=remote) == 262144


class TestBudgeterIntegration:
    def test_context_window_for_uses_the_discovered_length(self, monkeypatch):
        from idt_core.chat import tokens as token_tools

        monkeypatch.setattr(ollama_mod, "model_context_length", lambda *a, **k: 8192)
        assert token_tools.context_window_for("ollama", "some-model") == 8192

    def test_context_window_for_falls_back_when_discovery_fails(self, monkeypatch):
        from idt_core.chat import tokens as token_tools

        monkeypatch.setattr(ollama_mod, "model_context_length", lambda *a, **k: None)
        assert token_tools.context_window_for("ollama", "some-model") == 32_768

    def test_empty_model_name_never_probes(self, monkeypatch):
        """Tests and callers without a model must stay off the network."""
        from idt_core.chat import tokens as token_tools

        def _boom(*a, **k):  # pragma: no cover - the assertion is that it never runs
            raise AssertionError("probe should not run without a model name")

        monkeypatch.setattr(ollama_mod, "model_context_length", _boom)
        assert token_tools.context_window_for("ollama", "") == 32_768
