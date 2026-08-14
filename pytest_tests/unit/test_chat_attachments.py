"""Preparing files for a provider: MIME, HEIC, limits, and partial failure.

This logic lives in the engine because three callers need it — ImageDescriber's
chat window, the standalone chat app, and `idt chat`. It previously existed only
inside `ChatWindow.on_attach_files`; copying it into the new app is exactly how
this repo ended up with three provider layers.

The behaviour worth pinning down is what happens when a *selection* is partly
bad. Someone attaching ten photos, one of which is over Claude's 5 MB limit,
should get nine attachments and one explanation — not an empty queue and a
dialog. `prepare_attachments` is written for that case and
`test_one_bad_file_does_not_discard_the_others` is the assertion that keeps it.
"""

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from idt_core.chat.attachments import (  # noqa: E402
    AttachmentError,
    infer_media_type,
    prepare_attachment,
    prepare_attachments,
)
from idt_core.providers.registry import capabilities_for  # noqa: E402

CLAUDE_IMAGE_LIMIT = 5 * 1024 * 1024
CLAUDE_PDF_LIMIT = 32 * 1024 * 1024


@pytest.fixture
def files(tmp_path):
    def make(name, size=64):
        path = tmp_path / name
        path.write_bytes(b"x" * size)
        return path
    return make


# ---------------------------------------------------------------------------
# MIME inference
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name,expected", [
    ("a.jpg", "image/jpeg"),
    ("a.JPEG", "image/jpeg"),
    ("a.png", "image/png"),
    ("a.gif", "image/gif"),
    ("a.webp", "image/webp"),
    ("a.pdf", "application/pdf"),
    ("a.unknown", "application/octet-stream"),
    ("noextension", "application/octet-stream"),
])
def test_media_type_from_extension(name, expected):
    assert infer_media_type(name) == expected


# ---------------------------------------------------------------------------
# Acceptance
# ---------------------------------------------------------------------------

def test_image_is_accepted_by_every_image_provider(files):
    image = files("photo.png")
    for provider in ("ollama", "openai", "claude"):
        attachment, converted = prepare_attachment(image, provider)
        assert attachment.media_type == "image/png"
        assert attachment.path == str(image)
        assert converted is None


def test_pdf_is_accepted_by_the_document_providers(files):
    """Claude takes PDFs as document blocks, OpenAI as file content parts.
    Ollama has no PDF slot in its API at all."""
    pdf = files("doc.pdf")

    for provider in ("claude", "openai"):
        attachment, _ = prepare_attachment(pdf, provider)
        assert attachment.media_type == "application/pdf"

    with pytest.raises(AttachmentError) as excinfo:
        prepare_attachment(pdf, "ollama")
    # The message must say what IS accepted, not just what failed.
    assert "accepts" in str(excinfo.value)


def test_unknown_file_type_is_rejected_with_its_name(files):
    odd = files("notes.xyz")
    with pytest.raises(AttachmentError) as excinfo:
        prepare_attachment(odd, "claude")
    assert "notes.xyz" in str(excinfo.value)


def test_missing_file_is_rejected(tmp_path):
    with pytest.raises(AttachmentError) as excinfo:
        prepare_attachment(tmp_path / "gone.png", "claude")
    assert "not found" in str(excinfo.value).lower()


def test_a_provider_taking_no_attachments_says_so(files):
    image = files("photo.png")
    with pytest.raises(AttachmentError) as excinfo:
        prepare_attachment(image, "ollama cloud")
    assert "does not accept attachments" in str(excinfo.value)


# ---------------------------------------------------------------------------
# Size limits
# ---------------------------------------------------------------------------

def test_claude_image_limit_is_enforced(files):
    big = files("big.png", CLAUDE_IMAGE_LIMIT + 1)
    with pytest.raises(AttachmentError) as excinfo:
        prepare_attachment(big, "claude")
    message = str(excinfo.value)
    assert "big.png" in message
    assert "MB" in message  # the limit is stated in units a person reads


def test_a_file_exactly_on_the_limit_is_allowed(files):
    exact = files("exact.png", CLAUDE_IMAGE_LIMIT)
    attachment, _ = prepare_attachment(exact, "claude")
    assert attachment.media_type == "image/png"


def test_pdfs_get_the_larger_document_limit(files):
    """A 6 MB PDF is fine for Claude even though a 6 MB image is not."""
    pdf = files("big.pdf", 6 * 1024 * 1024)
    attachment, _ = prepare_attachment(pdf, "claude")
    assert attachment.media_type == "application/pdf"


def test_providers_without_documented_limits_do_not_invent_one(files):
    """None means "no published limit", so let the API report the error."""
    assert capabilities_for("ollama").size_limit_for("image/png") is None
    huge = files("huge.png", 20 * 1024 * 1024)
    attachment, _ = prepare_attachment(huge, "ollama")
    assert attachment.media_type == "image/png"


# ---------------------------------------------------------------------------
# Text files -- inlined into the prompt, so every chat provider takes them
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name,expected", [
    ("notes.txt", "text/plain"),
    ("run.log", "text/plain"),
    ("readme.md", "text/markdown"),
    ("data.csv", "text/csv"),
    ("script.py", "text/x-python"),
    ("config.json", "application/json"),
    ("stack.yml", "application/yaml"),
])
def test_text_media_types_from_extension(name, expected):
    assert infer_media_type(name) == expected


def test_text_files_are_accepted_by_every_chat_provider(files):
    notes = files("notes.txt")
    for provider in ("ollama", "openai", "claude"):
        attachment, converted = prepare_attachment(notes, provider)
        assert attachment.media_type == "text/plain"
        assert attachment.is_text
        assert converted is None


def test_mlx_still_takes_images_only(files):
    """MLX is a one-image vision path; text would be silently ignored there."""
    with pytest.raises(AttachmentError):
        prepare_attachment(files("notes.txt"), "mlx")


def test_oversized_text_is_rejected_at_attach_time(files):
    """~1 MB of text is more prompt than any model here can take; say so now
    rather than as an API error mid-conversation."""
    from idt_core.providers.registry import DEFAULT_MAX_TEXT_BYTES

    big = files("huge.log", DEFAULT_MAX_TEXT_BYTES + 1)
    with pytest.raises(AttachmentError) as excinfo:
        prepare_attachment(big, "ollama")
    assert "huge.log" in str(excinfo.value)


def test_rejection_message_lists_extensions_not_mime_subtypes(files):
    """".jpg, .txt" reads better than "jpeg, plain, x-python"."""
    odd = files("thing.xyz")
    with pytest.raises(AttachmentError) as excinfo:
        prepare_attachment(odd, "ollama")
    message = str(excinfo.value)
    assert ".jpg" in message
    assert ".txt" in message


# ---------------------------------------------------------------------------
# HEIC conversion
# ---------------------------------------------------------------------------

def test_heic_is_converted_to_jpeg(tmp_path, monkeypatch):
    """No provider decodes HEIC, so it must be converted on the way in."""
    import idt_core.converter as converter

    source = tmp_path / "IMG_1234.heic"
    source.write_bytes(b"fake-heic")

    converted_calls = []

    def fake_convert(src, dst):
        converted_calls.append((src, dst))
        Path(dst).write_bytes(b"jpeg-bytes")

    monkeypatch.setattr(converter, "convert_heic_to_jpg", fake_convert)

    workdir = tmp_path / "work"
    attachment, converted = prepare_attachment(source, "claude", workdir)

    assert converted_calls, "conversion was never attempted"
    assert attachment.media_type == "image/jpeg"
    assert attachment.path.endswith(".jpg")
    assert converted is not None and converted.exists()
    # Caller owns cleanup, so the temp path must be reported back.
    assert converted.parent == workdir


def test_a_failed_heic_conversion_names_the_file(tmp_path, monkeypatch):
    import idt_core.converter as converter

    source = tmp_path / "broken.heic"
    source.write_bytes(b"not really heic")

    def boom(_src, _dst):
        raise ValueError("no decoder")

    monkeypatch.setattr(converter, "convert_heic_to_jpg", boom)

    with pytest.raises(AttachmentError) as excinfo:
        prepare_attachment(source, "claude", tmp_path / "work")
    assert "broken.heic" in str(excinfo.value)


# ---------------------------------------------------------------------------
# Batch behaviour
# ---------------------------------------------------------------------------

def test_one_bad_file_does_not_discard_the_others(files):
    """Nine good photos and one oversized should attach nine."""
    good = [files(f"ok{i}.png") for i in range(9)]
    bad = files("toobig.png", CLAUDE_IMAGE_LIMIT + 1)

    attachments, converted, errors = prepare_attachments(
        good + [bad], "claude")

    assert len(attachments) == 9
    assert len(errors) == 1
    assert "toobig.png" in errors[0]
    assert converted == []


def test_batch_reports_every_problem(files):
    pdf = files("doc.pdf")
    odd = files("thing.xyz")
    image = files("fine.png")

    attachments, _converted, errors = prepare_attachments(
        [pdf, odd, image], "ollama")

    assert [a.name for a in attachments] == ["fine.png"]
    assert len(errors) == 2


def test_empty_selection_is_not_an_error():
    attachments, converted, errors = prepare_attachments([], "claude")
    assert (attachments, converted, errors) == ([], [], [])


def test_attachment_name_defaults_to_the_filename(files):
    attachment, _ = prepare_attachment(files("holiday.png"), "claude")
    assert attachment.name == "holiday.png"
