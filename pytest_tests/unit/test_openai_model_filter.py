"""Reducing OpenAI's `/v1/models` response to what belongs in a picker.

The endpoint returns roughly eighty entries for a normal account: embeddings,
speech, images, moderation, and a dated snapshot beside nearly every base id.
The filter that trims it is the part of issue #267 most likely to be *wrong in
the direction that hides something*, so it is a pure function with a table test
rather than logic buried in a client call.

Two failure directions, and they are not symmetric:

* Hiding a real chat model is the bad one. It reproduces exactly the complaint
  the issue was filed about -- a model the user can call that IDT will not
  offer -- and it is invisible, because nothing reports what was filtered out.
* Showing something extra is mildly annoying: the request fails with a clear
  API error and the user picks something else.

So the tests lean hard on "these must survive".
"""

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from idt_core.providers.openai_provider import (  # noqa: E402
    OPENAI_MODELS,
    filter_chat_model_ids,
)

pytestmark = pytest.mark.unit


#: A realistic account listing, in the shape and disorder the API returns it.
_RAW = [
    # Current chat models, base ids
    "gpt-5.2", "gpt-5.1", "gpt-5", "gpt-5-mini", "gpt-5-nano",
    "o4-mini", "o3",
    "gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano", "o1",
    # Dated snapshots whose base is present -- these collapse
    "gpt-4o-2024-08-06", "gpt-4o-2024-05-13", "gpt-4o-mini-2024-07-18",
    "gpt-4.1-2025-04-14", "o3-2025-04-16",
    # Legacy MMDD snapshots whose base is present
    "gpt-4-0613", "gpt-3.5-turbo-0125",
    # A base id for those legacy snapshots
    "gpt-4", "gpt-3.5-turbo",
    # A family that exists ONLY as snapshots -- newest must survive
    "gpt-6-preview-2026-08-01", "gpt-6-preview-2026-06-15",
    # Not chat models
    "text-embedding-3-large", "text-embedding-3-small", "text-embedding-ada-002",
    "tts-1", "tts-1-hd", "whisper-1",
    "dall-e-3", "dall-e-2", "gpt-image-1",
    "omni-moderation-latest", "text-moderation-stable",
    "gpt-4o-audio-preview", "gpt-4o-realtime-preview", "gpt-4o-transcribe",
    "gpt-3.5-turbo-instruct", "davinci-002", "babbage-002",
    "sora-2", "sora-2-pro", "chatgpt-image-latest", "gpt-live-transcribe",
    # Chat models that LOOK like they might not be, and must survive
    "gpt-4o-search-preview", "gpt-5.3-codex", "gpt-5-pro",
    "gpt-5-chat-latest", "o4-mini-deep-research",
    # A fine-tune
    "ft:gpt-4o-2024-08-06:acme:custom:abc123",
]


@pytest.fixture
def filtered():
    return filter_chat_model_ids(_RAW, curated=OPENAI_MODELS)


# ---------------------------------------------------------------------------
# What must survive
# ---------------------------------------------------------------------------

def test_every_curated_model_survives(filtered):
    """Rule one: whatever the patterns decide, a model we ship metadata for is
    never removed by them."""
    for model_id in OPENAI_MODELS:
        if model_id in _RAW:
            assert model_id in filtered, f"{model_id} was filtered out"


@pytest.mark.parametrize(
    "model_id",
    ["gpt-5.2", "gpt-5-nano", "o3", "o1", "gpt-4o", "gpt-4.1-nano", "gpt-3.5-turbo"],
)
def test_chat_models_survive(filtered, model_id):
    assert model_id in filtered


def test_a_version_number_is_not_mistaken_for_a_date(filtered):
    """`gpt-4.1-nano` must not be read as a snapshot of `gpt-4.1`."""
    assert "gpt-4.1-nano" in filtered


def test_a_snapshot_only_family_keeps_its_newest_member(filtered):
    """The failure mode most likely to bite: a model offered only as a pinned
    snapshot must not vanish because its base id does not exist."""
    assert "gpt-6-preview-2026-08-01" in filtered
    assert "gpt-6-preview-2026-06-15" not in filtered


def test_fine_tunes_survive_and_sort_last(filtered):
    """A fine-tune of a vision model is a perfectly good chat model."""
    ft = "ft:gpt-4o-2024-08-06:acme:custom:abc123"
    assert ft in filtered
    assert filtered[-1] == ft


def test_a_hypothetical_future_flagship_is_not_caught_by_a_substring():
    """Whole-token matching, not substring. A substring test for "audio" would
    hide this, which is the exact class of bug the issue is about."""
    out = filter_chat_model_ids(["gpt-6-audionative", "gpt-6-imagen"])
    assert out == ["gpt-6-audionative", "gpt-6-imagen"]


def test_an_unrecognised_new_family_survives():
    """The whole point: a model released today, visible today."""
    out = filter_chat_model_ids(["gpt-7", "zeta-1"])
    assert out == ["gpt-7", "zeta-1"]


# ---------------------------------------------------------------------------
# What must go
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "model_id",
    [
        "text-embedding-3-large", "text-embedding-ada-002",
        "tts-1-hd", "whisper-1",
        "dall-e-3", "gpt-image-1",
        "omni-moderation-latest", "text-moderation-stable",
        "gpt-4o-audio-preview", "gpt-4o-realtime-preview", "gpt-4o-transcribe",
        "gpt-3.5-turbo-instruct", "davinci-002", "babbage-002",
        # Video generation, and an image model whose family name is "chatgpt".
        "sora-2", "sora-2-pro", "chatgpt-image-latest", "gpt-live-transcribe",
    ],
)
def test_non_chat_models_are_dropped(filtered, model_id):
    assert model_id not in filtered


@pytest.mark.parametrize(
    "model_id",
    ["gpt-4o-search-preview", "gpt-5.3-codex", "gpt-5-pro",
     "gpt-5-chat-latest", "o4-mini-deep-research"],
)
def test_chat_models_with_misleading_names_survive(filtered, model_id):
    """Every one of these answers chat completions, and every one would be easy
    to deny by accident. Taken from a real account listing rather than invented:
    each is a model the user can call that IDT would then not have offered."""
    assert model_id in filtered


@pytest.mark.parametrize(
    "model_id",
    ["gpt-4o-2024-08-06", "gpt-4o-2024-05-13", "gpt-4o-mini-2024-07-18",
     "gpt-4.1-2025-04-14", "o3-2025-04-16"],
)
def test_dated_snapshots_collapse_behind_their_base(filtered, model_id):
    assert model_id not in filtered


@pytest.mark.parametrize("model_id", ["gpt-4-0613", "gpt-3.5-turbo-0125"])
def test_legacy_mmdd_snapshots_collapse_behind_their_base(filtered, model_id):
    assert model_id not in filtered


def test_a_short_suffix_survives_when_no_base_exists():
    """Four digits are ambiguous, so that form only ever collapses into an
    existing base -- it never removes a model on its own."""
    assert filter_chat_model_ids(["gpt-5-1000"]) == ["gpt-5-1000"]


def test_the_result_is_much_smaller_than_the_input(filtered):
    assert len(filtered) < len(_RAW) / 2


# ---------------------------------------------------------------------------
# keep=: the user's own selection
# ---------------------------------------------------------------------------

def test_keep_rescues_a_model_the_filter_would_drop():
    """Someone pinned to an older snapshot keeps it. Without this their picker
    silently falls back to a different model."""
    out = filter_chat_model_ids(_RAW, curated=OPENAI_MODELS,
                                keep=["gpt-4o-2024-05-13"])
    assert "gpt-4o-2024-05-13" in out


def test_keep_rescues_a_non_chat_id_if_that_is_what_is_selected():
    out = filter_chat_model_ids(["tts-1", "gpt-5.2"], keep=["tts-1"])
    assert "tts-1" in out


# ---------------------------------------------------------------------------
# Degenerate input
# ---------------------------------------------------------------------------

def test_empty_input_gives_empty_output():
    """The caller reads this as a failed fetch, not as 'no models'."""
    assert filter_chat_model_ids([]) == []


def test_blank_and_none_entries_are_skipped():
    assert filter_chat_model_ids(["", None, "gpt-5.2"]) == ["gpt-5.2"]


def test_input_order_is_preserved_for_survivors():
    out = filter_chat_model_ids(["o3", "gpt-5.2", "gpt-4o"])
    assert out == ["o3", "gpt-5.2", "gpt-4o"]


def test_the_filter_does_not_mutate_its_input():
    original = list(_RAW)
    filter_chat_model_ids(_RAW, curated=OPENAI_MODELS)
    assert _RAW == original
