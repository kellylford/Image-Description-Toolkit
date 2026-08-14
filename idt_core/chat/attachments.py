"""Turning a file path into something a provider will accept.

Everything that has to happen between "the user picked a file" and "the engine
can send it" lives here: working out the MIME type, converting HEIC (which no
provider reads), checking the provider actually accepts that kind of file, and
enforcing published size limits.

It is in the engine rather than in a window because three callers need it --
ImageDescriber's chat window, the standalone chat app, and ``idt chat``. The
same logic previously existed only inside ``ChatWindow.on_attach_files``; a
second copy in the new app is exactly how this repo ended up with three
provider layers.

No wx, no UI. Failures raise :class:`AttachmentError` carrying a message
already written for a person to read, so each caller decides only *how* to show
it -- a dialog, a status line, or stderr.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from ..providers.registry import capabilities_for
from .messages import Attachment

__all__ = [
    "AttachmentError",
    "EXTENSION_MIME_TYPES",
    "HEIC_EXTENSIONS",
    "infer_media_type",
    "prepare_attachment",
    "prepare_attachments",
]


class AttachmentError(Exception):
    """A file cannot be attached. The message is safe to show to a user."""


EXTENSION_MIME_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".pdf": "application/pdf",
    # Text-shaped files are inlined into the prompt by the chat formatters,
    # so they work on every provider. Keep this in step with
    # registry.TEXT_ATTACHMENT_MIME_TYPES and registry._MIME_TO_EXTENSIONS.
    ".txt": "text/plain",
    ".log": "text/plain",
    ".md": "text/markdown",
    ".csv": "text/csv",
    ".html": "text/html",
    ".htm": "text/html",
    ".css": "text/css",
    ".js": "text/javascript",
    ".py": "text/x-python",
    ".json": "application/json",
    ".xml": "application/xml",
    ".yaml": "application/yaml",
    ".yml": "application/yaml",
}

#: Converted to JPEG before sending: no provider decodes HEIC.
HEIC_EXTENSIONS = {".heic", ".heif"}


def infer_media_type(path) -> str:
    """MIME type from the file extension.

    Extension-based on purpose. Sniffing content would be more accurate but
    the providers key off the declared type anyway, and a wrong guess from
    sniffing is harder to explain to a user than a wrong extension.
    """
    return EXTENSION_MIME_TYPES.get(Path(path).suffix.lower(),
                                    "application/octet-stream")


def _human_size(num_bytes: int) -> str:
    megabytes = num_bytes / (1024 * 1024)
    if megabytes >= 1:
        return f"{megabytes:.1f} MB"
    return f"{num_bytes / 1024:.0f} KB"


def _convert_heic(path: Path, workdir: Path) -> Path:
    try:
        from ..converter import convert_heic_to_jpg
    except ImportError as exc:  # pragma: no cover - converter always ships
        raise AttachmentError(
            f"Cannot attach {path.name}: HEIC support is unavailable in this build."
        ) from exc

    workdir.mkdir(parents=True, exist_ok=True)
    target = workdir / f"{path.stem}.jpg"
    try:
        convert_heic_to_jpg(str(path), str(target))
    except Exception as exc:
        raise AttachmentError(
            f"Could not convert {path.name} from HEIC to JPEG: {exc}"
        ) from exc
    return target


def prepare_attachment(
    path,
    provider: str,
    workdir: Optional[Path] = None,
) -> Tuple[Attachment, Optional[Path]]:
    """Validate and normalise one file for ``provider``.

    Returns ``(attachment, converted_path)``. ``converted_path`` is the
    temporary JPEG produced for a HEIC input, or None -- callers that created
    the ``workdir`` are responsible for deleting it.

    Raises :class:`AttachmentError` with a user-facing message when the file is
    missing, of a kind the provider will not take, or over a published limit.
    """
    source = Path(path)
    if not source.is_file():
        raise AttachmentError(f"File not found: {source.name}")

    capabilities = capabilities_for(provider)
    if not capabilities.attachment_mime_types:
        raise AttachmentError(
            f"{provider} does not accept attachments."
        )

    converted: Optional[Path] = None
    if source.suffix.lower() in HEIC_EXTENSIONS:
        workdir = workdir or Path(tempfile.mkdtemp(prefix="idt_chat_"))
        converted = _convert_heic(source, workdir)
        source = converted

    media_type = infer_media_type(source)
    if not capabilities.accepts(media_type):
        from ..providers.registry import accepted_extensions

        accepted = ", ".join(accepted_extensions(provider)) or "no attachments"
        raise AttachmentError(
            f"{provider} cannot read {source.name} ({media_type}). "
            f"It accepts: {accepted}."
        )

    limit = capabilities.size_limit_for(media_type)
    if limit is not None:
        size = source.stat().st_size
        if size > limit:
            kind = "Image" if media_type.startswith("image/") else "File"
            raise AttachmentError(
                f"{kind} exceeds {provider}'s {_human_size(limit)} limit: "
                f"{source.name} is {_human_size(size)}."
            )

    return Attachment(media_type=media_type, path=str(source)), converted


def prepare_attachments(
    paths: Sequence,
    provider: str,
    workdir: Optional[Path] = None,
) -> Tuple[List[Attachment], List[Path], List[str]]:
    """Prepare several files, keeping the good ones.

    Returns ``(attachments, converted_paths, errors)``. One unusable file does
    not discard the rest: its message goes into ``errors`` and the others are
    still attached. Rejecting the whole selection because of a single oversized
    image would be worse behaviour for someone who picked ten files.
    """
    attachments: List[Attachment] = []
    converted: List[Path] = []
    errors: List[str] = []

    for path in paths:
        try:
            attachment, temp_path = prepare_attachment(path, provider, workdir)
        except AttachmentError as exc:
            errors.append(str(exc))
            continue
        attachments.append(attachment)
        if temp_path is not None:
            converted.append(temp_path)

    return attachments, converted, errors
