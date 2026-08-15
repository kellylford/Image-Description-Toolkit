"""
Ollama models without vision must never be offered for description.

Ollama accepts an attached image for a text-only model and silently discards it,
so the model writes a confident description from the prompt alone. A photo of
boats at a dock came back as "a woman standing next to a white Porsche 911"
(issue #227). Silent fabrication is the worst failure mode for an accessibility
tool: fluent, wrong, and nothing signals it.

Both provider paths are covered — idt_core (CLI) and imagedescriber (GUI).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "imagedescriber"))


# --------------------------------------------------------------------------- #
# idt_core path                                                                #
# --------------------------------------------------------------------------- #

class _FakeInfo:
    def __init__(self, caps):
        self.capabilities = caps


class _FakeClient:
    """Stands in for ollama.Client; `caps` maps model name -> capability list."""
    def __init__(self, caps, raise_on=None):
        self._caps = caps
        self._raise_on = raise_on or set()

    def show(self, name):
        if name in self._raise_on:
            raise RuntimeError("api unreachable")
        return _FakeInfo(self._caps[name])


@pytest.fixture(autouse=True)
def _clear_cache():
    from idt_core.providers import ollama as mod
    mod._SHOW_CACHE.clear()
    mod._NEGATIVE_AT.clear()
    yield
    mod._SHOW_CACHE.clear()
    mod._NEGATIVE_AT.clear()


class TestIdtCoreVisionCheck:
    def test_vision_model_accepted(self):
        from idt_core.providers.ollama import model_has_vision
        c = _FakeClient({"minicpm-v4.6": ["tools", "completion", "vision"]})
        assert model_has_vision("minicpm-v4.6", client=c) is True

    def test_text_only_model_rejected(self):
        """The exact capability set reported for gemma4:12b-mlx."""
        from idt_core.providers.ollama import model_has_vision
        c = _FakeClient({"gemma4:12b-mlx": ["completion", "tools", "thinking"]})
        assert model_has_vision("gemma4:12b-mlx", client=c) is False

    def test_capability_case_is_ignored(self):
        from idt_core.providers.ollama import model_has_vision
        c = _FakeClient({"m": ["Completion", "VISION"]})
        assert model_has_vision("m", client=c) is True

    def test_fails_open_when_query_errors(self):
        """A transient API failure must not hide a working model."""
        from idt_core.providers.ollama import model_has_vision
        c = _FakeClient({}, raise_on={"m"})
        assert model_has_vision("m", client=c) is True

    def test_fails_open_when_capabilities_absent(self):
        """Older Ollama builds may not report capabilities at all."""
        from idt_core.providers.ollama import model_has_vision
        c = _FakeClient({"m": None})
        assert model_has_vision("m", client=c) is True

    def test_result_is_cached(self):
        from idt_core.providers.ollama import model_has_vision
        calls = []

        class Counting(_FakeClient):
            def show(self, name):
                calls.append(name)
                return super().show(name)

        c = Counting({"m": ["completion", "vision"]})
        assert model_has_vision("m", client=c) is True
        assert model_has_vision("m", client=c) is True
        assert calls == ["m"], "capabilities should be queried once per model"


# --------------------------------------------------------------------------- #
# Chat listing — the OPPOSITE filter                                           #
# --------------------------------------------------------------------------- #

class TestChatCapableFilter:
    """The chat picker filters on `completion`, not `vision`.

    Applying the vision filter to chat hid every text-only model — often the
    strongest chat models a user has installed (issue #265).
    """

    def _provider_with(self, monkeypatch, caps, raise_on=None):
        import types

        from idt_core.providers.ollama import OllamaProvider

        inner = _FakeClient(caps, raise_on=raise_on)

        class _Model:
            def __init__(self, name):
                self.model = name

        class _Listing:
            def __init__(self, names):
                self.models = [_Model(n) for n in names]

        class _Client:
            def __init__(self, host=None):
                pass

            def list(self):
                return _Listing(list(caps) + sorted(raise_on or []))

            def show(self, name):
                return inner.show(name)

        import sys
        monkeypatch.setitem(sys.modules, "ollama", types.SimpleNamespace(Client=_Client))
        return OllamaProvider(model="whatever")

    def test_text_only_models_are_offered_for_chat(self, monkeypatch):
        p = self._provider_with(monkeypatch, {
            "qwen3:8b": ["completion", "tools", "thinking"],
            "minicpm-v4.6": ["completion", "vision"],
        })
        models = p.list_chat_models()
        assert "qwen3:8b" in models
        assert "minicpm-v4.6" in models

    def test_embedding_only_models_are_not_offered_for_chat(self, monkeypatch):
        """/api/tags lists embedding models; /api/chat rejects them."""
        p = self._provider_with(monkeypatch, {
            "nomic-embed-text": ["embedding"],
            "qwen3:8b": ["completion"],
        })
        assert p.list_chat_models() == ["qwen3:8b"]

    def test_chat_listing_fails_open_when_the_probe_errors(self, monkeypatch):
        p = self._provider_with(monkeypatch, {}, raise_on={"mystery-model"})
        assert p.list_chat_models() == ["mystery-model"]

    def test_the_describe_listing_still_requires_vision(self, monkeypatch):
        """The two filters must not converge: describe keeps vision (issue #227)."""
        p = self._provider_with(monkeypatch, {
            "qwen3:8b": ["completion", "tools"],
            "minicpm-v4.6": ["completion", "vision"],
        })
        assert p.list_models() == ["minicpm-v4.6"]


# --------------------------------------------------------------------------- #
# GUI path                                                                     #
# --------------------------------------------------------------------------- #

class _Resp:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def json(self):
        return self._payload


class TestGuiVisionFilter:
    def _provider(self, monkeypatch, caps, tags=None, show_status=200):
        import ai_providers as ap
        tags = tags if tags is not None else list(caps)

        def fake_get(url, **kw):
            return _Resp({"models": [{"name": n} for n in tags]})

        def fake_post(url, json=None, **kw):
            name = (json or {}).get("model")
            return _Resp({"capabilities": caps.get(name)}, status=show_status)

        monkeypatch.setattr(ap.requests, "get", fake_get)
        monkeypatch.setattr(ap.requests, "post", fake_post)
        p = ap.OllamaProvider()
        p._models_cache = None
        return p

    def test_text_only_model_not_offered(self, monkeypatch):
        p = self._provider(monkeypatch, {
            "gemma4:12b-mlx": ["completion", "tools", "thinking"],
            "minicpm-v4.6:latest": ["completion", "vision"],
        })
        models = p.get_available_models()
        assert "gemma4:12b-mlx" not in models
        assert "minicpm-v4.6:latest" in models

    def test_all_text_only_yields_empty_list(self, monkeypatch):
        p = self._provider(monkeypatch, {"a": ["completion"], "b": ["tools"]})
        assert p.get_available_models() == []

    def test_fails_open_on_show_error(self, monkeypatch):
        """If /api/show is unavailable, keep the models rather than hide them."""
        p = self._provider(monkeypatch, {"a": None, "b": None}, show_status=500)
        assert sorted(p.get_available_models()) == ["a", "b"]

    def test_cloud_vision_models_are_offered(self, monkeypatch):
        """Regression: code once assumed no cloud model had vision."""
        p = self._provider(monkeypatch, {
            "gemma4:31b-cloud": ["completion", "thinking", "tools", "vision"],
        })
        assert p.get_available_models() == ["gemma4:31b-cloud"]


class TestNoStaleCloudRefusal:
    def test_cloud_provider_does_not_hard_refuse_vision(self):
        """OllamaCloudProvider used to return a canned 'vision not supported'
        string for every image, which is wrong now that cloud models report
        vision. It must delegate rather than refuse."""
        src = (_ROOT / "imagedescriber" / "ai_providers.py").read_text(encoding="utf-8")
        assert "doesn't support vision capabilities yet" not in src
        assert "vision support is coming soon" not in src
