"""Web search via tool calling: the executor, the Ollama tool loop, the engine.

The feature has three seams, each tested without a network:

1. ``idt_core.chat.tools`` — schemas and the executor. A tool failure returns
   its error AS the result string (the model can still answer; the user sees
   why the search did not happen). A missing ollama.com key is a message that
   tells the person how to get one, not an exception.
2. ``OllamaChatProvider.chat`` — the tool loop. Tool calls are executed, fed
   back as role=tool messages, and the loop is bounded so a model stuck
   re-searching cannot run forever on the user's API quota.
3. ``ChatEngine`` — offers the tools only for Ollama and only when asked, and
   forwards tool activity as events so a UI can say why the reply is slow.
"""

import json
import sys
import types
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from idt_core.chat import (  # noqa: E402
    ChatEngine,
    ChatOptions,
    ChatSession,
)
from idt_core.chat import tools as web_tools  # noqa: E402
from idt_core.chat.events import ChatToolCall as ToolCallEvent  # noqa: E402
from idt_core.chat.events import ChatToolResult as ToolResultEvent  # noqa: E402
from idt_core.chat.messages import ChatMessage  # noqa: E402
from idt_core.chat.providers import OllamaChatProvider  # noqa: E402
from idt_core.providers.base import ChatDelta as ProviderDelta  # noqa: E402
from idt_core.providers.base import ChatProvider, ChatRequest  # noqa: E402
from idt_core.providers.base import ChatToolCall as ProviderToolCall  # noqa: E402
from idt_core.providers.base import ChatToolResult as ProviderToolResult  # noqa: E402


# ---------------------------------------------------------------------------
# The executor
# ---------------------------------------------------------------------------


class TestExecutor:
    def test_missing_key_returns_instructions_not_an_exception(self, monkeypatch):
        monkeypatch.setattr(web_tools, "_api_key", lambda: None)
        result = web_tools.execute_web_tool("web_search", {"query": "idt"})
        # The exact signup URL, not a substring: the message must send the
        # user somewhere actionable.
        assert "https://ollama.com/settings/keys" in result
        assert "OLLAMA_API_KEY" in result

    def test_search_results_are_formatted_and_truncated(self, monkeypatch):
        monkeypatch.setattr(web_tools, "_api_key", lambda: "key")
        sent = {}

        def fake_api(endpoint, payload, key):
            sent.update(endpoint=endpoint, payload=payload)
            return {"results": [
                {"title": "T", "url": "https://x", "content": "c" * 10_000},
            ]}

        monkeypatch.setattr(web_tools, "_call_api", fake_api)
        result = web_tools.execute_web_tool("web_search", {"query": "idt"})

        assert sent["endpoint"] == "web_search"
        assert sent["payload"] == {"query": "idt", "max_results": 5}
        parsed = json.loads(result)
        content = parsed["results"][0]["content"]
        assert len(content) < 10_000
        assert content.endswith("…[truncated]")

    def test_max_results_is_clamped_to_the_api_limit(self, monkeypatch):
        monkeypatch.setattr(web_tools, "_api_key", lambda: "key")
        sent = {}
        monkeypatch.setattr(
            web_tools, "_call_api",
            lambda e, p, k: sent.update(p) or {"results": []})

        web_tools.execute_web_tool("web_search", {"query": "q", "max_results": 99})
        assert sent["max_results"] == web_tools.MAX_SEARCH_RESULTS

    def test_an_api_failure_is_a_result_string_not_a_raise(self, monkeypatch):
        monkeypatch.setattr(web_tools, "_api_key", lambda: "key")

        def boom(endpoint, payload, key):
            raise OSError("network down")

        monkeypatch.setattr(web_tools, "_call_api", boom)
        result = web_tools.execute_web_tool("web_search", {"query": "q"})
        assert "failed" in result
        assert "network down" in result

    def test_unknown_tool_names_are_reported_not_executed(self, monkeypatch):
        monkeypatch.setattr(web_tools, "_api_key", lambda: "key")
        assert "Unknown tool" in web_tools.execute_web_tool("rm_rf", {})

    def test_definitions_cover_exactly_the_advertised_tools(self):
        names = [d["function"]["name"] for d in web_tools.web_tool_definitions()]
        assert names == list(web_tools.WEB_TOOL_NAMES)


class TestResultSummaries:
    def test_a_successful_fetch_says_page_retrieved(self):
        summary = web_tools.tool_result_summary("web_fetch", '{"url": "x", "content": "y"}')
        assert summary == "Page retrieved"

    def test_a_failed_fetch_shows_the_error_not_page_retrieved(self):
        """This lied once: a keyless fetch was summarised as "Page retrieved"."""
        summary = web_tools.tool_result_summary("web_fetch", "web_fetch failed: HTTP 401 from ollama.com.")
        assert "Page retrieved" not in summary
        assert "401" in summary

    def test_the_missing_key_message_reaches_the_status_line(self):
        summary = web_tools.tool_result_summary("web_search", web_tools.missing_web_key_message())
        assert summary.startswith("Web search needs an ollama.com API key")

    def test_search_summaries_count_results(self):
        summary = web_tools.tool_result_summary("web_search", '{"results": [1, 2, 3]}')
        assert summary == "Found 3 result(s)"


# ---------------------------------------------------------------------------
# The Ollama tool loop
# ---------------------------------------------------------------------------


class _Stream:
    """One scripted response stream, closable like the SDK's."""

    def __init__(self, chunks):
        self._chunks = chunks

    def __iter__(self):
        return iter(self._chunks)

    def close(self):
        pass


class _Script:
    """A fake ollama module whose chat() plays scripted rounds."""

    def __init__(self, rounds):
        self._rounds = list(rounds)
        self.calls = []  # kwargs of every chat() invocation

    def chat(self, **kwargs):
        self.calls.append(kwargs)
        round_chunks = self._rounds.pop(0) if self._rounds else [
            {"message": {"content": "fallback"}, "done": True}]
        return _Stream(round_chunks)


def _tool_call(name, arguments):
    return {"function": {"name": name, "arguments": arguments}}


@pytest.fixture
def no_context_probe(monkeypatch):
    from idt_core.providers import ollama as ollama_mod

    monkeypatch.setattr(ollama_mod, "model_context_length", lambda *a, **k: None)


def _run(monkeypatch, script, executor):
    monkeypatch.setitem(sys.modules, "ollama", types.SimpleNamespace(chat=script.chat))
    provider = OllamaChatProvider("qwen3")
    request = ChatRequest(
        messages=[ChatMessage(role="user", content="what's new?")],
        model="qwen3",
        tools=web_tools.web_tool_definitions(),
        execute_tool=executor,
    )
    return list(provider.chat(request))


def test_tool_calls_are_executed_and_fed_back(monkeypatch, no_context_probe):
    script = _Script([
        # Round 1: the model asks to search.
        [{"message": {"tool_calls": [_tool_call("web_search", {"query": "idt"})]},
          "done": True, "prompt_eval_count": 10, "eval_count": 2}],
        # Round 2: it answers from the results.
        [{"message": {"content": "Here is what I found."},
          "done": True, "prompt_eval_count": 30, "eval_count": 8}],
    ])
    executed = []

    def executor(name, arguments):
        executed.append((name, arguments))
        return '{"results": [{"title": "hit"}]}'

    yields = _run(monkeypatch, script, executor)

    assert executed == [("web_search", {"query": "idt"})]

    # The second round must carry the tool exchange back to the model.
    round2 = script.calls[1]["messages"]
    assert round2[-2]["role"] == "assistant"
    assert round2[-2]["tool_calls"]
    assert round2[-1] == {
        "role": "tool",
        "content": '{"results": [{"title": "hit"}]}',
        "tool_name": "web_search",
    }

    kinds = [type(y).__name__ for y in yields]
    assert kinds == ["ChatToolCall", "ChatToolResult", "ChatDelta", "ChatUsage"]

    usage = yields[-1]
    assert (usage.input_tokens, usage.output_tokens) == (40, 10), (
        "each round is a separate model call; usage must be summed"
    )


def test_a_failing_executor_becomes_a_tool_result(monkeypatch, no_context_probe):
    script = _Script([
        [{"message": {"tool_calls": [_tool_call("web_search", {"query": "x"})]},
          "done": True}],
        [{"message": {"content": "answered anyway"}, "done": True}],
    ])

    def executor(name, arguments):
        raise RuntimeError("executor bug")

    yields = _run(monkeypatch, script, executor)

    assert "executor bug" in script.calls[1]["messages"][-1]["content"]
    assert any(isinstance(y, ProviderDelta) for y in yields)


def test_the_tool_loop_is_bounded(monkeypatch, no_context_probe):
    """A model that searches forever gets cut off and made to answer."""
    always_searching = [
        [{"message": {"tool_calls": [_tool_call("web_search", {"query": "again"})]},
          "done": True}]
        for _ in range(OllamaChatProvider.MAX_TOOL_ROUNDS + 5)
    ]
    script = _Script(always_searching)

    _run(monkeypatch, script, lambda n, a: "result")

    assert len(script.calls) == OllamaChatProvider.MAX_TOOL_ROUNDS + 1
    assert "tools" not in script.calls[-1], (
        "the final round must withhold the tools so the model answers"
    )


def test_no_tools_are_sent_without_an_executor(monkeypatch, no_context_probe):
    script = _Script([[{"message": {"content": "hi"}, "done": True}]])
    monkeypatch.setitem(sys.modules, "ollama", types.SimpleNamespace(chat=script.chat))

    provider = OllamaChatProvider("qwen3")
    request = ChatRequest(
        messages=[ChatMessage(role="user", content="hello")],
        model="qwen3",
        tools=web_tools.web_tool_definitions(),  # definitions but no executor
    )
    list(provider.chat(request))

    assert "tools" not in script.calls[0]


def test_num_ctx_is_floored_at_32k_when_tools_are_offered(no_context_probe):
    provider = OllamaChatProvider("qwen3")
    request = ChatRequest(
        messages=[ChatMessage(role="user", content="hi")],
        model="qwen3",
        tools=web_tools.web_tool_definitions(),
        execute_tool=lambda n, a: "",
    )
    assert provider._request_options(request)["num_ctx"] == 32_768


def test_string_arguments_are_parsed_as_json():
    name, arguments = OllamaChatProvider._tool_call_fields(
        {"function": {"name": "web_search", "arguments": '{"query": "idt"}'}}
    )
    assert (name, arguments) == ("web_search", {"query": "idt"})


# ---------------------------------------------------------------------------
# The engine
# ---------------------------------------------------------------------------


class _RecordingProvider(ChatProvider):
    """Pretends to be Ollama; records the request, plays scripted yields."""

    def __init__(self, name="ollama", yields=()):
        self._name = name
        self._yields = list(yields) or [ProviderDelta("hi")]
        self.requests = []

    @property
    def provider_name(self):
        return self._name

    @property
    def model_name(self):
        return "fake-model"

    def chat(self, request):
        self.requests.append(request)
        yield from self._yields


def test_engine_offers_web_tools_only_when_asked():
    provider = _RecordingProvider()
    engine = ChatEngine(ChatSession(), provider)

    list(engine.send("hello", options=ChatOptions()))
    assert provider.requests[0].tools == ()
    assert provider.requests[0].execute_tool is None

    list(engine.send("again", options=ChatOptions(web_search=True)))
    assert len(provider.requests[1].tools) == 2
    assert provider.requests[1].execute_tool is web_tools.execute_web_tool


def test_engine_ignores_web_search_for_providers_without_tool_support():
    """The flag must degrade to a normal turn, not fail one the user could have."""
    provider = _RecordingProvider(name="claude")
    engine = ChatEngine(ChatSession(), provider)

    list(engine.send("hello", options=ChatOptions(web_search=True)))
    assert provider.requests[0].tools == ()


def test_engine_forwards_tool_activity_as_events():
    provider = _RecordingProvider(yields=[
        ProviderToolCall("web_search", {"query": "idt"}),
        ProviderToolResult("web_search", "Found 3 result(s)"),
        ProviderDelta("the answer"),
    ])
    engine = ChatEngine(ChatSession(), provider)

    events = list(engine.send("question", options=ChatOptions(web_search=True)))

    calls = [e for e in events if isinstance(e, ToolCallEvent)]
    results = [e for e in events if isinstance(e, ToolResultEvent)]
    assert len(calls) == 1 and calls[0].arguments == {"query": "idt"}
    assert len(results) == 1 and results[0].summary == "Found 3 result(s)"
    assert calls[0].describe() == "Searching the web: idt"


def test_tool_events_do_not_leak_into_the_saved_message():
    provider = _RecordingProvider(yields=[
        ProviderToolCall("web_search", {"query": "idt"}),
        ProviderToolResult("web_search", "Found 1 result(s)"),
        ProviderDelta("clean answer"),
    ])
    session = ChatSession()
    engine = ChatEngine(session, provider)

    list(engine.send("question", options=ChatOptions(web_search=True)))

    assert session.messages[-1].content == "clean answer"
