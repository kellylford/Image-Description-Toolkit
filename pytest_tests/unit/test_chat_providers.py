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


def test_non_image_attachments_are_skipped_by_image_only_providers():
    """Ollama and OpenAI take images only; a PDF must not be sent as one."""
    history = [ChatMessage(role="user", content="read this", attachments=[PDF])]

    assert "images" not in format_for_ollama(history)[0]
    assert format_for_openai(history)[0]["content"] == "read this"


def test_attachment_bytes_are_read_from_disk_when_not_held_in_memory(tmp_path):
    path = tmp_path / "photo.png"
    path.write_bytes(b"on-disk-bytes")
    att = Attachment("image/png", path=str(path))

    assert att.name == "photo.png"
    assert encode_image_ollama(att) == base64.b64encode(b"on-disk-bytes").decode()


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
