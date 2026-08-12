"""The chat engine, driven through a fake provider. No network, no API key, no wx.

The engine exists to own the things that were previously spread across four
near-duplicate ``_chat_with_*`` methods in a wx worker thread: history
assembly, the system prompt, the token budget, retry, persistence and
cancellation. Each of those had a specific defect, and the tests below are
named after the defect rather than the method.

The most important assertions here are the ones about *what survives failure*.
The old implementation lost a response if you closed the window mid-stream,
never retried a 429, and never sent a system prompt at all. A turn that fails
or is cancelled must still leave a record of what was asked and whatever text
arrived -- otherwise the user is left with a question and no answer and no
explanation.
"""

import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from idt_core.chat import (  # noqa: E402
    Attachment,
    ChatBusyError,
    ChatCancelled,
    ChatDelta,
    ChatEngine,
    ChatFailed,
    ChatFinished,
    ChatMessage,
    ChatOptions,
    ChatRetrying,
    ChatSession,
    ChatStarted,
    ChatUsage,
    DirectoryChatStore,
    estimate_tokens,
)
from idt_core.chat import tokens as token_tools  # noqa: E402
from idt_core.chat.errors import ErrorKind, classify  # noqa: E402
from idt_core.providers.base import ChatDelta as ProviderDelta  # noqa: E402
from idt_core.providers.base import ChatProvider  # noqa: E402
from idt_core.providers.base import ChatUsage as ProviderUsage  # noqa: E402


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeChatProvider(ChatProvider):
    """Yields scripted chunks, and records exactly what it was asked to send."""

    def __init__(self, chunks=("Hello", " there"), usage=(11, 3),
                 fail_with=None, fail_times=0, model="fake-1"):
        self._chunks = list(chunks)
        self._usage = usage
        self._fail_with = fail_with
        self._fail_times = fail_times
        self._model = model
        self.requests = []
        self.calls = 0
        self.closed = 0

    @property
    def provider_name(self):
        return "fake"

    @property
    def model_name(self):
        return self._model

    def chat(self, request):
        self.calls += 1
        self.requests.append(request)
        if self._fail_with is not None and self.calls <= self._fail_times:
            raise self._fail_with
        try:
            for chunk in self._chunks:
                yield ProviderDelta(chunk)
            if self._usage:
                yield ProviderUsage(input_tokens=self._usage[0],
                                    output_tokens=self._usage[1])
        finally:
            self.closed += 1


class ExplodingProvider(ChatProvider):
    """Fails partway through, after some text has already been delivered."""

    def __init__(self, before=("partial ",), exc=None):
        self._before = list(before)
        self._exc = exc or RuntimeError("stream died")

    @property
    def provider_name(self):
        return "fake"

    @property
    def model_name(self):
        return "fake-1"

    def chat(self, request):
        for chunk in self._before:
            yield ProviderDelta(chunk)
        raise self._exc


def drain(engine, *args, **kwargs):
    return list(engine.send(*args, **kwargs))


def text_of(events):
    return "".join(e.text for e in events if isinstance(e, ChatDelta))


def kinds(events):
    return [type(e).__name__ for e in events]


# ---------------------------------------------------------------------------
# The happy path
# ---------------------------------------------------------------------------


def test_a_turn_produces_started_deltas_usage_finished():
    engine = ChatEngine(ChatSession(), FakeChatProvider())
    events = drain(engine, "hi")

    assert kinds(events) == [
        "ChatStarted", "ChatDelta", "ChatDelta", "ChatUsage", "ChatFinished"
    ]
    assert text_of(events) == "Hello there"
    assert isinstance(events[-1], ChatFinished)
    assert events[-1].message.content == "Hello there"


def test_history_accumulates_both_roles():
    engine = ChatEngine(ChatSession(), FakeChatProvider())
    drain(engine, "first")
    drain(engine, "second")

    roles = [m.role for m in engine.session.messages]
    assert roles == ["user", "assistant", "user", "assistant"]


def test_full_history_is_resent_each_turn():
    """Multi-turn context: turn two must carry turn one, or the model forgets."""
    provider = FakeChatProvider()
    engine = ChatEngine(ChatSession(), provider)
    drain(engine, "first")
    drain(engine, "second")

    first_request, second_request = provider.requests
    assert len(first_request.messages) == 1
    assert [m.content for m in second_request.messages] == [
        "first", "Hello there", "second"
    ]


def test_user_turn_is_saved_before_the_request_goes_out():
    """A failed call must still leave a record of what was asked."""
    class Boom(ChatProvider):
        provider_name = "fake"
        model_name = "fake-1"

        def chat(self, request):
            raise RuntimeError("nope")
            yield  # pragma: no cover - unreachable, makes this a generator

    session = ChatSession()
    engine = ChatEngine(session, Boom())
    drain(engine, "did this survive?")

    assert session.messages[0].role == "user"
    assert session.messages[0].content == "did this survive?"


# ---------------------------------------------------------------------------
# System prompt -- previously never sent at all
# ---------------------------------------------------------------------------


def test_session_system_prompt_reaches_the_provider():
    provider = FakeChatProvider()
    engine = ChatEngine(ChatSession(system_prompt="Be terse."), provider)
    drain(engine, "hi")

    assert provider.requests[0].system_prompt == "Be terse."


def test_options_system_prompt_overrides_the_session_for_one_turn():
    provider = FakeChatProvider()
    session = ChatSession(system_prompt="Session voice.")
    engine = ChatEngine(session, provider)

    drain(engine, "one", options=ChatOptions(system_prompt="Turn voice."))
    drain(engine, "two")

    assert provider.requests[0].system_prompt == "Turn voice."
    assert provider.requests[1].system_prompt == "Session voice."
    assert session.system_prompt == "Session voice."


def test_empty_string_system_prompt_is_honoured_not_ignored():
    """'' must mean "no system prompt", distinct from None meaning "inherit"."""
    provider = FakeChatProvider()
    engine = ChatEngine(ChatSession(system_prompt="Inherited."), provider)
    drain(engine, "hi", options=ChatOptions(system_prompt=""))

    assert provider.requests[0].system_prompt == ""


# ---------------------------------------------------------------------------
# Cancellation -- the response must survive
# ---------------------------------------------------------------------------


def test_request_stop_keeps_the_partial_response():
    provider = FakeChatProvider(chunks=["one ", "two ", "three"])
    session = ChatSession()
    engine = ChatEngine(session, provider)

    events = []
    for event in engine.send("hi"):
        events.append(event)
        if isinstance(event, ChatDelta):
            engine.request_stop()

    assert isinstance(events[-1], ChatCancelled)
    assert session.messages[-1].content == "one "
    assert session.messages[-1].error == "Cancelled"
    assert session.messages[-1].is_partial


def test_closing_the_generator_still_persists_what_arrived():
    """gen.close() cannot yield an event, but must not lose the text."""
    provider = FakeChatProvider(chunks=["kept ", "more"])
    session = ChatSession()
    engine = ChatEngine(session, provider)

    gen = engine.send("hi")
    next(gen)   # ChatStarted
    next(gen)   # first ChatDelta
    gen.close()

    assert session.messages[-1].role == "assistant"
    assert session.messages[-1].content == "kept "
    assert session.messages[-1].error == "Cancelled"


def test_cancellation_closes_the_provider_stream():
    """A stopped turn must not leak the HTTP connection."""
    provider = FakeChatProvider(chunks=["a", "b", "c"])
    engine = ChatEngine(ChatSession(), provider)

    gen = engine.send("hi")
    next(gen)
    next(gen)
    gen.close()

    assert provider.closed == 1


def test_engine_is_not_busy_after_cancellation():
    provider = FakeChatProvider(chunks=["a", "b"])
    engine = ChatEngine(ChatSession(), provider)

    gen = engine.send("hi")
    next(gen)
    gen.close()

    assert engine.is_busy is False
    drain(engine, "next one works")  # must not raise ChatBusyError


# ---------------------------------------------------------------------------
# Concurrency guard
# ---------------------------------------------------------------------------


def test_overlapping_turns_raise_instead_of_interleaving():
    engine = ChatEngine(ChatSession(), FakeChatProvider())
    first = engine.send("one")
    next(first)
    try:
        with pytest.raises(ChatBusyError):
            list(engine.send("two"))
    finally:
        first.close()


# ---------------------------------------------------------------------------
# Retry
# ---------------------------------------------------------------------------


class _Status429(Exception):
    status_code = 429


class _Status401(Exception):
    status_code = 401


def test_transient_failure_is_retried_then_succeeds():
    provider = FakeChatProvider(fail_with=_Status429("slow down"), fail_times=1)
    engine = ChatEngine(ChatSession(), provider)

    events = drain(engine, "hi", options=ChatOptions(retry_base_delay=0))

    assert any(isinstance(e, ChatRetrying) for e in events)
    assert isinstance(events[-1], ChatFinished)
    assert provider.calls == 2


def test_auth_failure_is_not_retried():
    provider = FakeChatProvider(fail_with=_Status401("bad key"), fail_times=99)
    engine = ChatEngine(ChatSession(), provider)

    events = drain(engine, "hi", options=ChatOptions(retry_base_delay=0))

    assert not any(isinstance(e, ChatRetrying) for e in events)
    assert isinstance(events[-1], ChatFailed)
    assert events[-1].retryable is False
    assert provider.calls == 1


def test_retry_stops_at_max_and_reports_failure():
    provider = FakeChatProvider(fail_with=_Status429("still busy"), fail_times=99)
    engine = ChatEngine(ChatSession(), provider)

    events = drain(engine, "hi",
                   options=ChatOptions(max_retries=2, retry_base_delay=0))

    assert isinstance(events[-1], ChatFailed)
    assert events[-1].attempts == 3
    assert provider.calls == 3


def test_a_partly_delivered_answer_is_never_retried():
    """Replaying would duplicate text the user has already seen."""
    engine = ChatEngine(ChatSession(), ExplodingProvider(exc=_Status429("mid-stream")))
    events = drain(engine, "hi", options=ChatOptions(retry_base_delay=0))

    assert not any(isinstance(e, ChatRetrying) for e in events)
    assert isinstance(events[-1], ChatFailed)


def test_failed_turn_keeps_partial_text_and_the_reason():
    session = ChatSession()
    engine = ChatEngine(session, ExplodingProvider(before=["half an answer"]))
    drain(engine, "hi", options=ChatOptions(retry_base_delay=0))

    assistant = session.messages[-1]
    assert assistant.content == "half an answer"
    assert "stream died" in assistant.error


# ---------------------------------------------------------------------------
# Token accounting -- the quadratic over-count
# ---------------------------------------------------------------------------


def test_context_tokens_is_the_last_turn_not_a_running_sum():
    session = ChatSession()
    session.add(ChatMessage(role="user", content="a"))
    session.add(ChatMessage(role="assistant", content="b",
                            input_tokens=100, output_tokens=10))
    session.add(ChatMessage(role="user", content="c"))
    session.add(ChatMessage(role="assistant", content="d",
                            input_tokens=140, output_tokens=5))

    # The naive sum -- what the old chat window displayed -- is 255.
    assert session.context_tokens == 145
    assert session.billed_tokens == 255


def test_context_tokens_is_zero_before_any_reply():
    session = ChatSession()
    session.add(ChatMessage(role="user", content="unanswered"))
    assert session.context_tokens == 0


# ---------------------------------------------------------------------------
# Budget truncation -- previously silent
# ---------------------------------------------------------------------------


def _long_turn(role, size=4000):
    return ChatMessage(role=role, content="x" * size)


def test_truncation_is_reported_not_just_performed():
    messages = [_long_turn("user" if i % 2 == 0 else "assistant") for i in range(40)]
    _, result = token_tools.prepare_history(messages, "ollama", "")

    assert result.was_truncated
    assert result.dropped > 0
    assert "context window" in result.describe()


def test_engine_reports_dropped_turns_on_started():
    session = ChatSession()
    for i in range(40):
        session.messages.append(_long_turn("user" if i % 2 == 0 else "assistant"))

    engine = ChatEngine(session, FakeChatProvider())
    events = drain(engine, "and now this")
    started = events[0]

    assert isinstance(started, ChatStarted)
    assert started.dropped_messages > 0
    assert started.sent_messages < len(session.messages)


def test_the_newest_turn_is_never_dropped():
    messages = [_long_turn("user", 200_000) for _ in range(5)]
    messages.append(ChatMessage(role="user", content="the actual question"))
    kept, _ = token_tools.prepare_history(messages, "ollama", "")

    assert kept[-1].content == "the actual question"


def test_short_conversations_are_left_alone():
    messages = [ChatMessage(role="user", content="hi"),
                ChatMessage(role="assistant", content="hello")]
    kept, result = token_tools.prepare_history(messages, "claude", "claude-opus-5")

    assert result.was_truncated is False
    assert len(kept) == 2
    assert result.describe() == ""


def test_per_model_context_window_beats_the_provider_default():
    """The old code used a flat 200k for every Claude model, ignoring metadata."""
    assert token_tools.context_window_for("claude", "claude-opus-5") == 200_000
    assert token_tools.context_window_for("ollama", "") == 32_768
    assert token_tools.context_window_for("nonsense", "") == 32_768


def test_images_dominate_the_estimate():
    text_only = [ChatMessage(role="user", content="hi")]
    with_image = [ChatMessage(role="user", content="hi",
                              attachments=[Attachment("image/png", data=b"x")])]
    assert estimate_tokens(with_image) > estimate_tokens(text_only) + 900


# ---------------------------------------------------------------------------
# Attachment de-duplication
# ---------------------------------------------------------------------------


def test_an_image_is_sent_once_not_on_every_later_turn():
    photo = Attachment("image/png", path="/tmp/photo.png")
    messages = [
        ChatMessage(role="user", content="what is this", attachments=[photo]),
        ChatMessage(role="assistant", content="a cat"),
        ChatMessage(role="user", content="and now", attachments=[photo]),
    ]
    deduped = token_tools.dedupe_attachments(messages)

    assert len(deduped[0].attachments) == 1
    assert deduped[2].attachments == []
    assert deduped[2].content == "and now"  # text is preserved


def test_dedupe_does_not_mutate_the_callers_history():
    photo = Attachment("image/png", path="/tmp/photo.png")
    messages = [
        ChatMessage(role="user", content="a", attachments=[photo]),
        ChatMessage(role="user", content="b", attachments=[photo]),
    ]
    token_tools.dedupe_attachments(messages)

    assert len(messages[1].attachments) == 1


def test_distinct_images_are_all_kept():
    messages = [
        ChatMessage(role="user", content="a",
                    attachments=[Attachment("image/png", path="/tmp/1.png")]),
        ChatMessage(role="user", content="b",
                    attachments=[Attachment("image/png", path="/tmp/2.png")]),
    ]
    deduped = token_tools.dedupe_attachments(messages)
    assert [len(m.attachments) for m in deduped] == [1, 1]


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def test_store_round_trip(tmp_path):
    store = DirectoryChatStore(tmp_path)
    session = ChatSession(title="Kept", system_prompt="Be brief.")
    engine = ChatEngine(session, FakeChatProvider(), store)
    drain(engine, "hi")

    reloaded = store.load(session.id)
    assert reloaded is not None
    assert reloaded.title == "Kept"
    assert reloaded.system_prompt == "Be brief."
    assert [m.content for m in reloaded.messages] == ["hi", "Hello there"]


def test_every_turn_is_persisted_not_just_the_last(tmp_path):
    """A lost close handler must not be able to lose the conversation."""
    store = DirectoryChatStore(tmp_path)
    session = ChatSession()
    engine = ChatEngine(session, FakeChatProvider(), store)

    gen = engine.send("hi")
    next(gen)  # ChatStarted -- the user turn is already committed

    on_disk = store.load(session.id)
    assert on_disk is not None
    assert on_disk.messages[0].content == "hi"
    gen.close()


def test_listing_is_newest_first(tmp_path):
    store = DirectoryChatStore(tmp_path)
    for name in ("one", "two", "three"):
        session = ChatSession(title=name)
        session.modified = {"one": "2026-01-01", "two": "2026-06-01",
                            "three": "2026-08-01"}[name]
        store.save(session)

    # save() touches modified, so re-write the intended values directly.
    for path in tmp_path.glob("*.json"):
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["modified"] = {"one": "2026-01-01", "two": "2026-06-01",
                           "three": "2026-08-01"}[raw["title"]]
        path.write_text(json.dumps(raw), encoding="utf-8")

    assert [s.title for s in store.list_sessions()] == ["three", "two", "one"]


def test_a_corrupt_file_does_not_break_the_list(tmp_path):
    store = DirectoryChatStore(tmp_path)
    store.save(ChatSession(title="good"))
    (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")

    assert [s.title for s in store.list_sessions()] == ["good"]


def test_delete_reports_whether_anything_was_removed(tmp_path):
    store = DirectoryChatStore(tmp_path)
    session = ChatSession()
    store.save(session)

    assert store.delete(session.id) is True
    assert store.delete(session.id) is False


def test_session_id_cannot_escape_the_store_directory(tmp_path):
    store = DirectoryChatStore(tmp_path)
    with pytest.raises(ValueError):
        store.load("../../etc/passwd")


# ---------------------------------------------------------------------------
# Schema migration -- v1 chats must not lose history
# ---------------------------------------------------------------------------


def test_v1_session_loads_with_all_three_prompt_styles():
    """compact_summary is easy to forget and drops history when it is."""
    raw = {
        "id": "chat_old",
        "name": "Legacy",
        "provider": "claude",
        "model": "claude-opus-5",
        "descriptions": [
            {"prompt_style": "user_question", "text": "q1"},
            {"prompt_style": "ai_response", "text": "a1",
             "token_usage": {"input_tokens": 7, "output_tokens": 2}},
            {"prompt_style": "compact_summary", "text": "summary so far"},
            {"prompt_style": "user_question", "text": "q2"},
        ],
    }
    session = ChatSession.from_dict(raw)

    assert session.title == "Legacy"
    assert [m.role for m in session.messages] == [
        "user", "assistant", "system", "user"
    ]
    assert session.messages[1].input_tokens == 7


def test_v1_ignores_unknown_prompt_styles():
    raw = {"id": "c", "descriptions": [
        {"prompt_style": "detailed", "text": "an image description"},
        {"prompt_style": "user_question", "text": "real turn"},
    ]}
    session = ChatSession.from_dict(raw)
    assert [m.content for m in session.messages] == ["real turn"]


def test_v2_round_trips_exactly():
    session = ChatSession(title="T", system_prompt="S", provider="claude",
                          model="claude-opus-5")
    session.add(ChatMessage(role="user", content="q",
                            attachments=[Attachment("image/png", path="/tmp/a.png")]))
    session.add(ChatMessage(role="assistant", content="a",
                            input_tokens=5, output_tokens=6))

    restored = ChatSession.from_dict(session.to_dict())

    assert restored.title == "T"
    assert restored.system_prompt == "S"
    assert restored.messages[0].attachments[0].path == "/tmp/a.png"
    assert restored.messages[1].output_tokens == 6


# ---------------------------------------------------------------------------
# Error classification
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("status,expected", [
    (429, ErrorKind.RATE_LIMIT),
    (500, ErrorKind.SERVER),
    (503, ErrorKind.SERVER),
    (401, ErrorKind.AUTH),
    (403, ErrorKind.AUTH),
    (404, ErrorKind.NOT_FOUND),
    (400, ErrorKind.BAD_REQUEST),
])
def test_status_code_drives_classification(status, expected):
    exc = type("E", (Exception,), {"status_code": status})("boom")
    assert classify(exc).kind is expected


def test_the_ollama_wording_that_went_unrecognised_for_nine_months():
    """"Error: HTTP 500" contains no "status code" -- issue #228's defect."""
    assert classify(Exception("Error: HTTP 500")).kind is ErrorKind.SERVER


def test_only_transient_kinds_are_retryable():
    assert classify(Exception("Error: HTTP 503")).retryable is True
    exc = type("E", (Exception,), {"status_code": 401})("no")
    assert classify(exc).retryable is False


def test_timeout_beats_connection_when_both_words_appear():
    assert classify(OSError("connection timed out")).kind is ErrorKind.TIMEOUT


# ---------------------------------------------------------------------------
# Regenerate
# ---------------------------------------------------------------------------


def test_regenerate_replaces_the_last_answer_only():
    provider = FakeChatProvider(chunks=["first answer"])
    session = ChatSession()
    engine = ChatEngine(session, provider)
    drain(engine, "the question")

    provider._chunks = ["second answer"]
    list(engine.regenerate())

    assert [m.content for m in session.messages] == [
        "the question", "second answer"
    ]


def test_regenerate_without_a_question_raises():
    engine = ChatEngine(ChatSession(), FakeChatProvider())
    with pytest.raises(ValueError):
        list(engine.regenerate())


# ---------------------------------------------------------------------------
# Provider switching
# ---------------------------------------------------------------------------


def test_switching_provider_keeps_history_and_updates_the_session():
    session = ChatSession()
    engine = ChatEngine(session, FakeChatProvider(model="fake-1"))
    drain(engine, "hi")

    engine.switch_provider(FakeChatProvider(model="fake-2"))
    drain(engine, "still there?")

    assert session.model == "fake-2"
    assert len(session.messages) == 4
    assert session.messages[0].model == "fake-1"
    assert session.messages[-1].model == "fake-2"
