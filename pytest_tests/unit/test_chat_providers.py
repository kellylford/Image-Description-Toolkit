"""Wire formats for each chat provider.

The network call is a thin wrapper; the part that is easy to get quietly wrong
is the *shape* of what gets sent — where the system prompt goes, how an image
becomes a content block, which turns are included at all. Those are pure
functions here precisely so they can be tested without an API key, and this
file is why they were separated out.

The sharpest assertion is
:func:`test_claude_takes_the_system_prompt_as_a_parameter_not_a_message`.
Anthropic rejects a ``role: "system"`` entry in the messages array — it must be
a top-level ``system`` argument. OpenAI and Ollama are the opposite. Getting
that backwards fails at request time against a live API, which is the most
expensive place to find out.
"""

import base64
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from idt_core.chat.messages import Attachment, ChatMessage  # noqa: E402
from idt_core.chat.providers import (  # noqa: E402
    ClaudeChatProvider,
    OllamaChatProvider,
    create_chat_provider,
    encode_attachment_claude,
    encode_image_ollama,
    format_for_claude,
    format_for_ollama,
    format_for_openai,
)
from idt_core.providers.base import ChatRequest  # noqa: E402

PNG = Attachment("image/png", data=b"\x89PNG-not-really", name="shot.png")
PDF = Attachment("application/pdf", data=b"%PDF-1.4 fake", name="doc.pdf")


def _conversation():
    return [
        ChatMessage(role="user", content="first question"),
        ChatMessage(role="assistant", content="first answer"),
        ChatMessage(role="user", content="second question"),
    ]


# ---------------------------------------------------------------------------
# System prompt placement
# ---------------------------------------------------------------------------


def test_claude_takes_the_system_prompt_as_a_parameter_not_a_message():
    system, messages = format_for_claude(_conversation(), "Be terse.")

    assert system == "Be terse."
    assert all(m["role"] != "system" for m in messages), (
        "Anthropic rejects a system entry inside the messages array"
    )


def test_openai_takes_the_system_prompt_as_a_leading_message():
    messages = format_for_openai(_conversation(), "Be terse.")

    assert messages[0] == {"role": "system", "content": "Be terse."}
    assert messages[1]["role"] == "user"


def test_ollama_takes_the_system_prompt_as_a_leading_message():
    messages = format_for_ollama(_conversation(), "Be terse.")

    assert messages[0] == {"role": "system", "content": "Be terse."}


@pytest.mark.parametrize("formatter", [format_for_openai, format_for_ollama])
def test_no_system_message_when_there_is_no_system_prompt(formatter):
    assert all(m["role"] != "system" for m in formatter(_conversation(), ""))


# ---------------------------------------------------------------------------
# Turn selection
# ---------------------------------------------------------------------------


def test_all_conversation_turns_are_sent_in_order():
    messages = format_for_ollama(_conversation())
    assert [m["role"] for m in messages] == ["user", "assistant", "user"]
    assert messages[0]["content"] == "first question"


def test_empty_turns_are_dropped():
    """A failed turn that produced no text must not be sent as an empty message.

    Some providers reject an empty assistant turn and fail the whole request,
    which would make one failed turn poison every turn after it.
    """
    history = [
        ChatMessage(role="user", content="q"),
        ChatMessage(role="assistant", content="", error="Cancelled"),
        ChatMessage(role="user", content="q2"),
    ]
    for formatter in (format_for_ollama, format_for_openai):
        assert [m["role"] for m in formatter(history)] == ["user", "user"]
    _, claude = format_for_claude(history)
    assert [m["role"] for m in claude] == ["user", "user"]


def test_a_cancelled_turn_that_has_text_is_still_sent():
    history = [
        ChatMessage(role="user", content="q"),
        ChatMessage(role="assistant", content="partial", error="Cancelled"),
    ]
    assert len(format_for_ollama(history)) == 2


def test_system_role_turns_are_not_replayed_as_conversation():
    """v1 compact_summary markers load as role=system; they are not turns."""
    history = [
        ChatMessage(role="system", content="summary of earlier"),
        ChatMessage(role="user", content="q"),
    ]
    assert [m["role"] for m in format_for_ollama(history)] == ["user"]


# ---------------------------------------------------------------------------
# Attachments
# ---------------------------------------------------------------------------


def test_ollama_puts_images_in_a_separate_list():
    history = [ChatMessage(role="user", content="what is this", attachments=[PNG])]
    entry = format_for_ollama(history)[0]

    assert entry["content"] == "what is this"
    assert entry["images"] == [base64.b64encode(PNG.data).decode()]


def test_ollama_omits_the_images_key_when_there_are_none():
    entry = format_for_ollama([ChatMessage(role="user", content="hi")])[0]
    assert "images" not in entry


def test_openai_turns_with_images_become_a_content_array():
    history = [ChatMessage(role="user", content="what is this", attachments=[PNG])]
    entry = format_for_openai(history)[0]

    assert isinstance(entry["content"], list)
    assert entry["content"][0] == {"type": "text", "text": "what is this"}
    assert entry["content"][1]["type"] == "image_url"
    assert entry["content"][1]["image_url"]["url"].startswith("data:image/jpeg;base64,")


def test_openai_plain_turns_stay_strings():
    """Sending a one-element array for every turn bloats the payload."""
    entry = format_for_openai([ChatMessage(role="user", content="hi")])[0]
    assert entry["content"] == "hi"


def test_claude_puts_attachments_before_the_text():
    history = [ChatMessage(role="user", content="what is this", attachments=[PNG])]
    _, messages = format_for_claude(history)
    blocks = messages[0]["content"]

    assert blocks[0]["type"] == "image"
    assert blocks[-1] == {"type": "text", "text": "what is this"}


def test_claude_encodes_pdfs_as_documents_not_images():
    block = encode_attachment_claude(PDF)

    assert block["type"] == "document"
    assert block["source"]["media_type"] == "application/pdf"
    assert block["source"]["data"] == base64.b64encode(PDF.data).decode()


def test_claude_encodes_images_with_their_real_media_type():
    block = encode_attachment_claude(PNG)

    assert block["type"] == "image"
    assert block["source"]["media_type"] == "image/png"


def test_ollama_never_sends_a_pdf_as_an_image():
    """Ollama's API has no PDF slot; a PDF must not ride the images list."""
    history = [ChatMessage(role="user", content="read this", attachments=[PDF])]
    entry = format_for_ollama(history)[0]

    assert "images" not in entry
    assert entry["content"] == "read this"


def test_openai_encodes_pdfs_as_file_content_parts():
    history = [ChatMessage(role="user", content="read this", attachments=[PDF])]
    entry = format_for_openai(history)[0]

    assert isinstance(entry["content"], list)
    assert entry["content"][0] == {"type": "text", "text": "read this"}
    block = entry["content"][1]
    assert block["type"] == "file"
    assert block["file"]["filename"] == "doc.pdf"
    assert block["file"]["file_data"].startswith("data:application/pdf;base64,")


def test_openai_model_limits_are_recorded_now():
    """The registry's documented gap — (None, None) for every OpenAI model —
    is closed; the budgeter and gauge get real figures."""
    from idt_core.providers.registry import model_limits

    context, max_output = model_limits("openai", "gpt-4o")
    assert (context, max_output) == (128_000, 16_384)
    context, _ = model_limits("openai", "gpt-5.2")
    assert context == 400_000


def test_attachment_bytes_are_read_from_disk_when_not_held_in_memory(tmp_path):
    path = tmp_path / "photo.png"
    path.write_bytes(b"on-disk-bytes")
    att = Attachment("image/png", path=str(path))

    assert att.name == "photo.png"
    assert encode_image_ollama(att) == base64.b64encode(b"on-disk-bytes").decode()


def test_attachment_bytes_are_read_from_disk_only_once(tmp_path):
    """History replays every turn; without caching, a 1 MB attached log
    would be re-read from disk on every send for the whole conversation."""
    path = tmp_path / "notes.txt"
    path.write_text("cached content", encoding="utf-8")
    att = Attachment("text/plain", path=str(path))

    first = att.read_bytes()
    path.unlink()  # a second disk read would now fail loudly

    assert att.read_bytes() == first


def test_cached_attachment_bytes_never_reach_the_saved_session(tmp_path):
    path = tmp_path / "notes.txt"
    path.write_text("secret-ish content", encoding="utf-8")
    att = Attachment("text/plain", path=str(path))
    att.read_bytes()

    assert "data" not in att.to_dict(), "only the path is ever serialised"


# ---------------------------------------------------------------------------
# max_tokens -- the hard-coded 2048
# ---------------------------------------------------------------------------


def test_claude_max_output_comes_from_model_metadata_not_a_constant():
    """The old worker sent max_tokens=2048 for every Claude model."""
    provider = ClaudeChatProvider("claude-opus-5")
    request = ChatRequest(messages=[], model="claude-opus-5")

    assert provider._max_output(request) == 128_000


def test_an_explicit_max_output_wins():
    provider = ClaudeChatProvider("claude-opus-5")
    request = ChatRequest(messages=[], model="claude-opus-5", max_output_tokens=500)

    assert provider._max_output(request) == 500


def test_unknown_claude_model_falls_back_rather_than_crashing():
    provider = ClaudeChatProvider("claude-not-a-real-model")
    request = ChatRequest(messages=[], model="claude-not-a-real-model")

    assert provider._max_output(request) == ClaudeChatProvider.FALLBACK_MAX_OUTPUT


# ---------------------------------------------------------------------------
# Text attachments -- inlined into the message text on every provider
# ---------------------------------------------------------------------------


@pytest.fixture
def text_file(tmp_path):
    path = tmp_path / "notes.txt"
    path.write_text("line one\nline two", encoding="utf-8")
    return Attachment("text/plain", path=str(path))


def _text_turn(att):
    return [ChatMessage(role="user", content="summarize this", attachments=[att])]


def test_text_attachments_are_inlined_for_ollama(text_file):
    entry = format_for_ollama(_text_turn(text_file))[0]

    assert "summarize this" in entry["content"]
    assert "notes.txt" in entry["content"]
    assert "line one" in entry["content"]
    assert "images" not in entry, "a text file must never ride the images list"


def test_text_attachments_are_inlined_for_openai(text_file):
    entry = format_for_openai(_text_turn(text_file))[0]

    assert isinstance(entry["content"], str)
    assert "line one" in entry["content"]


def test_text_attachments_are_inlined_for_claude_not_encoded(text_file):
    """Encoding a .txt as an image block would be an API error."""
    _, messages = format_for_claude(_text_turn(text_file))
    entry = messages[0]

    assert isinstance(entry["content"], str)
    assert "line one" in entry["content"]


def test_text_and_image_together_keep_both_channels(text_file):
    history = [ChatMessage(role="user", content="compare",
                           attachments=[text_file, PNG])]
    entry = format_for_ollama(history)[0]

    assert "line one" in entry["content"]
    assert entry["images"] == [base64.b64encode(PNG.data).decode()]

    _, claude = format_for_claude(history)
    blocks = claude[0]["content"]
    assert blocks[0]["type"] == "image"
    assert "line one" in blocks[-1]["text"]


def test_a_deleted_text_file_becomes_a_note_not_a_failed_turn(tmp_path):
    """History replays long after the file may have been deleted."""
    gone = Attachment("text/plain", path=str(tmp_path / "gone.txt"))
    entry = format_for_ollama(_text_turn(gone))[0]

    assert "gone.txt" in entry["content"]
    assert "no longer available" in entry["content"]


def test_text_attachment_content_counts_toward_the_token_estimate(tmp_path):
    from idt_core.chat.tokens import estimate_tokens

    path = tmp_path / "big.txt"
    path.write_text("x" * 40_000, encoding="utf-8")
    with_file = [ChatMessage(role="user", content="hi",
                             attachments=[Attachment("text/plain", path=str(path))])]
    without = [ChatMessage(role="user", content="hi")]

    assert estimate_tokens(with_file) >= estimate_tokens(without) + 40_000 // 4


# ---------------------------------------------------------------------------
# Ollama request options -- temperature and max_tokens used to be silently
# dropped, and num_ctx was never sent so the server truncated at its default.
# ---------------------------------------------------------------------------


@pytest.fixture
def _no_context_probe(monkeypatch):
    """Keep option-building off the network; individual tests override."""
    from idt_core.providers import ollama as ollama_mod

    monkeypatch.setattr(ollama_mod, "model_context_length", lambda *a, **k: None)


def _ollama_request(**kwargs):
    provider = OllamaChatProvider("llama3.2")
    request = ChatRequest(
        messages=kwargs.pop("messages", [ChatMessage(role="user", content="hi")]),
        model="llama3.2",
        **kwargs,
    )
    return provider, request


def test_ollama_temperature_is_sent(_no_context_probe):
    provider, request = _ollama_request(temperature=0.2)
    assert provider._request_options(request)["temperature"] == 0.2


def test_ollama_temperature_zero_is_still_sent(_no_context_probe):
    provider, request = _ollama_request(temperature=0.0)
    assert provider._request_options(request)["temperature"] == 0.0


def test_ollama_omits_temperature_when_unset(_no_context_probe):
    provider, request = _ollama_request()
    assert "temperature" not in provider._request_options(request)


def test_ollama_max_output_tokens_becomes_num_predict(_no_context_probe):
    provider, request = _ollama_request(max_output_tokens=500)
    assert provider._request_options(request)["num_predict"] == 500


def test_ollama_num_ctx_floors_at_the_server_default(_no_context_probe):
    """A short chat should not request less than the server would give anyway."""
    provider, request = _ollama_request()
    assert provider._request_options(request)["num_ctx"] == 4096


def test_ollama_num_ctx_grows_with_the_conversation(_no_context_probe):
    long_history = [ChatMessage(role="user", content="x" * 40_000)]
    provider, request = _ollama_request(messages=long_history)
    num_ctx = provider._request_options(request)["num_ctx"]

    # ~10k estimated prompt tokens + reply headroom, rounded up -- the exact
    # figure matters less than being far above the 4,096 server default.
    assert num_ctx > 10_000
    assert num_ctx % OllamaChatProvider.NUM_CTX_STEP == 0


def test_ollama_num_ctx_caps_at_the_models_trained_length(monkeypatch):
    from idt_core.providers import ollama as ollama_mod

    monkeypatch.setattr(ollama_mod, "model_context_length", lambda *a, **k: 8192)
    long_history = [ChatMessage(role="user", content="x" * 400_000)]
    provider, request = _ollama_request(messages=long_history)

    assert provider._request_options(request)["num_ctx"] == 8192


def test_ollama_num_ctx_caps_at_32k_when_the_model_is_unknown(_no_context_probe):
    long_history = [ChatMessage(role="user", content="x" * 400_000)]
    provider, request = _ollama_request(messages=long_history)

    assert provider._request_options(request)["num_ctx"] == 32_768


def test_ollama_a_tiny_trained_length_wins_over_the_floor(monkeypatch):
    """min 4,096 is a request floor, never permission to exceed the model."""
    from idt_core.providers import ollama as ollama_mod

    monkeypatch.setattr(ollama_mod, "model_context_length", lambda *a, **k: 2048)
    provider, request = _ollama_request()

    assert provider._request_options(request)["num_ctx"] == 2048


def test_ollama_chat_call_carries_the_options_dict(monkeypatch, _no_context_probe):
    """End to end through chat(): the options dict must reach client.chat."""
    import types

    sent = {}

    class _FakeStream:
        def __iter__(self):
            return iter(
                [{"message": {"content": "hello"}, "done": True,
                  "prompt_eval_count": 3, "eval_count": 2}]
            )

        def close(self):
            pass

    def fake_chat(**kwargs):
        sent.update(kwargs)
        return _FakeStream()

    monkeypatch.setitem(sys.modules, "ollama", types.SimpleNamespace(chat=fake_chat))

    provider, request = _ollama_request(temperature=0.3, max_output_tokens=256)
    events = list(provider.chat(request))

    assert sent["options"] == {"num_ctx": 4096, "temperature": 0.3, "num_predict": 256}
    assert any(getattr(e, "text", None) == "hello" for e in events)


# ---------------------------------------------------------------------------
# Thinking -- reasoning models' scratch work stays out of the answer
# ---------------------------------------------------------------------------


def _scripted_ollama(monkeypatch, chunks):
    import types

    calls = []

    class _Stream:
        def __iter__(self):
            return iter(chunks)

        def close(self):
            pass

    def fake_chat(**kwargs):
        calls.append(kwargs)
        return _Stream()

    monkeypatch.setitem(sys.modules, "ollama", types.SimpleNamespace(chat=fake_chat))
    return calls


def _caps(monkeypatch, caps):
    from idt_core.providers import ollama as ollama_mod

    monkeypatch.setattr(ollama_mod, "model_capabilities", lambda *a, **k: caps)


def test_thinking_streams_separately_and_stays_out_of_the_text(
        monkeypatch, _no_context_probe):
    from idt_core.providers.base import ChatThinking as ProviderThinking

    _caps(monkeypatch, ["completion", "thinking"])
    _scripted_ollama(monkeypatch, [
        {"message": {"thinking": "let me reason"}, "done": False},
        {"message": {"content": "the answer"}, "done": True},
    ])

    provider, request = _ollama_request()
    yields = list(provider.chat(request))

    thinking = [y for y in yields if isinstance(y, ProviderThinking)]
    from idt_core.providers.base import ChatDelta as Delta
    deltas = [y.text for y in yields if isinstance(y, Delta)]

    assert [t.text for t in thinking] == ["let me reason"]
    assert deltas == ["the answer"], "thinking must never join the answer text"


def test_think_is_sent_only_to_models_reporting_the_capability(
        monkeypatch, _no_context_probe):
    _caps(monkeypatch, ["completion", "thinking"])
    calls = _scripted_ollama(monkeypatch, [{"message": {"content": "x"}, "done": True}])
    provider, request = _ollama_request()
    list(provider.chat(request))
    assert calls[0]["think"] is True


def test_think_is_omitted_for_models_without_the_capability(
        monkeypatch, _no_context_probe):
    """Sending think to a model without it is an API error, so auto mode
    fails CLOSED — unlike the picker probes."""
    _caps(monkeypatch, ["completion"])
    calls = _scripted_ollama(monkeypatch, [{"message": {"content": "x"}, "done": True}])
    provider, request = _ollama_request()
    list(provider.chat(request))
    assert "think" not in calls[0]


def test_think_is_omitted_when_the_probe_fails(monkeypatch, _no_context_probe):
    _caps(monkeypatch, None)
    calls = _scripted_ollama(monkeypatch, [{"message": {"content": "x"}, "done": True}])
    provider, request = _ollama_request()
    list(provider.chat(request))
    assert "think" not in calls[0]


def test_an_explicit_think_on_skips_the_probe(monkeypatch, _no_context_probe):
    """The user asked for thinking; if the model cannot, the API error saying
    so is the honest answer — no probe second-guessing."""
    from idt_core.providers import ollama as ollama_mod

    def boom(*a, **k):  # pragma: no cover - the assertion is that it never runs
        raise AssertionError("explicit think=True must not probe capabilities")

    monkeypatch.setattr(ollama_mod, "model_capabilities", boom)
    calls = _scripted_ollama(monkeypatch, [{"message": {"content": "x"}, "done": True}])
    provider, request = _ollama_request(think=True)
    list(provider.chat(request))
    assert calls[0]["think"] is True


def test_no_think_is_sent_to_thinking_models(monkeypatch, _no_context_probe):
    _caps(monkeypatch, ["completion", "thinking"])
    calls = _scripted_ollama(monkeypatch, [{"message": {"content": "x"}, "done": True}])
    provider, request = _ollama_request(think=False)
    list(provider.chat(request))
    assert calls[0]["think"] is False


def test_no_think_is_dropped_for_models_without_the_capability(
        monkeypatch, _no_context_probe):
    """--no-think on a plain model is already satisfied; sending the field
    would fail the very turn the flag exists to speed up."""
    _caps(monkeypatch, ["completion"])
    calls = _scripted_ollama(monkeypatch, [{"message": {"content": "x"}, "done": True}])
    provider, request = _ollama_request(think=False)
    list(provider.chat(request))
    assert "think" not in calls[0]


def test_engine_forwards_thinking_and_never_saves_it():
    from idt_core.chat import ChatEngine, ChatOptions, ChatSession
    from idt_core.chat.events import ChatThinking as ThinkingEvent
    from idt_core.providers.base import ChatDelta as ProviderDelta
    from idt_core.providers.base import ChatProvider
    from idt_core.providers.base import ChatThinking as ProviderThinking

    class _Thinker(ChatProvider):
        @property
        def provider_name(self):
            return "ollama"

        @property
        def model_name(self):
            return "fake"

        def chat(self, request):
            yield ProviderThinking("hmm")
            yield ProviderDelta("clean answer")

    session = ChatSession()
    events = list(ChatEngine(session, _Thinker()).send("q", options=ChatOptions()))

    assert any(isinstance(e, ThinkingEvent) and e.text == "hmm" for e in events)
    assert session.messages[-1].content == "clean answer"


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name,expected", [
    ("ollama", "ollama"),
    ("Claude", "claude"),
    ("anthropic", "claude"),
    ("OpenAI", "openai"),
])
def test_factory_resolves_aliases_and_case(name, expected):
    provider = create_chat_provider(name, "some-model", "key")
    assert provider.provider_name == expected
    assert provider.model_name == "some-model"


def test_factory_rejects_an_unknown_provider_by_name():
    with pytest.raises(ValueError) as excinfo:
        create_chat_provider("hal9000", "model")
    assert "hal9000" in str(excinfo.value)


def test_local_providers_are_not_handed_an_api_key():
    """Ollama takes a host, not a key; passing one would be a TypeError."""
    provider = create_chat_provider("ollama", "llava", "should-be-ignored")
    assert provider.provider_name == "ollama"
