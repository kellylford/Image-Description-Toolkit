"""
Provider capability registry — the single source of truth for what each
provider can do.

This replaces ``models/provider_configs.py``, which was deleted in commit
16e089b when the legacy ``models/`` tree was removed.  Its loss was silent:
callers imported it inside a ``try/except ImportError`` and fell back to stubs
that reported "no capabilities", which is why the chat window's Attach Files
button disappeared on every provider.

Capabilities come in two flavours:

* **Provider-level** — streaming, system-prompt support, attachment MIME types,
  whether an API key is needed.  Answered by :func:`capabilities_for`.
* **Model-level** — context window and max output tokens.  These vary per model,
  so they are read from the per-provider ``*_MODEL_METADATA`` dicts by
  :func:`model_limits`.  **Unknown values are returned as ``None``, never as a
  guess** — callers decide their own fallback.

Provider names are matched case-insensitively, so ``"claude"``, ``"Claude"``
and ``"CLAUDE"`` all resolve to the same entry.  The GUI lowercases provider
names (``ChatDialog.get_selections``) while the old config keyed them by
display name; case-insensitivity is what made that work, so it is preserved.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

__all__ = [
    "ProviderCapabilities",
    "capabilities_for",
    "list_providers",
    "supports_attachments",
    "supported_attachments",
    "attachment_wildcard",
    "model_limits",
]


@dataclass(frozen=True)
class ProviderCapabilities:
    """What a provider supports, independent of which model is selected."""

    provider: str
    streaming: bool = False
    system_prompt: bool = False
    requires_api_key: bool = False
    is_local: bool = False
    attachment_mime_types: Tuple[str, ...] = ()
    #: Published per-file upload limits, in bytes. ``None`` means "no limit
    #: documented", not "unlimited" -- callers should let the API report the
    #: error rather than inventing a threshold.
    max_image_bytes: Optional[int] = None
    max_document_bytes: Optional[int] = None

    def size_limit_for(self, media_type: str) -> Optional[int]:
        """Upload limit for a MIME type, or None if none is documented."""
        if media_type.startswith("image/"):
            return self.max_image_bytes
        return self.max_document_bytes

    def accepts(self, media_type: str) -> bool:
        return media_type in self.attachment_mime_types

    @property
    def supports_attachments(self) -> bool:
        return bool(self.attachment_mime_types)

    @property
    def supports_images(self) -> bool:
        return any(m.startswith("image/") for m in self.attachment_mime_types)

    @property
    def supports_documents(self) -> bool:
        return any(not m.startswith("image/") for m in self.attachment_mime_types)


_IMAGE_MIMES: Tuple[str, ...] = (
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
)

# Attachment lists carried over verbatim from the deleted provider_configs.py
# so this is a restoration, not a redesign.  Entries for providers that no
# longer exist (HuggingFace/Florence-2, Object Detection, Grounding DINO,
# Copilot+ PC, Enhanced Ollama) were dropped — those subsystems were removed
# in commits 3026be1 and 16e089b.
_REGISTRY: Dict[str, ProviderCapabilities] = {
    "ollama": ProviderCapabilities(
        provider="ollama",
        streaming=True,
        system_prompt=True,
        requires_api_key=False,
        is_local=True,
        attachment_mime_types=_IMAGE_MIMES,
    ),
    "ollama cloud": ProviderCapabilities(
        provider="ollama cloud",
        streaming=True,
        system_prompt=True,
        # Authenticates via Ollama Cloud login rather than an API key field.
        requires_api_key=False,
        is_local=False,
        # Empty in the original config, annotated "no vision support".
        # Preserved rather than re-derived; revisit with a capability probe.
        attachment_mime_types=(),
    ),
    "openai": ProviderCapabilities(
        provider="openai",
        streaming=True,
        system_prompt=True,
        requires_api_key=True,
        is_local=False,
        attachment_mime_types=_IMAGE_MIMES,
    ),
    "claude": ProviderCapabilities(
        provider="claude",
        streaming=True,
        system_prompt=True,
        requires_api_key=True,
        is_local=False,
        # Claude accepts PDFs as native document blocks.
        attachment_mime_types=_IMAGE_MIMES + ("application/pdf",),
        # Anthropic's published per-file limits.
        max_image_bytes=5 * 1024 * 1024,
        max_document_bytes=32 * 1024 * 1024,
    ),
    "mlx": ProviderCapabilities(
        provider="mlx",
        # MLX generates in one shot; the chat engine adapts it by yielding a
        # single delta so consumers cannot tell the difference.
        streaming=False,
        # Depends on the individual model's chat template. True for every
        # model currently in MLXProvider.KNOWN_MODELS.
        system_prompt=True,
        requires_api_key=False,
        is_local=True,
        attachment_mime_types=_IMAGE_MIMES,
    ),
}

# Aliases for names the GUI and config files use for the same provider.
_ALIASES: Dict[str, str] = {
    "anthropic": "claude",
    "ollama_cloud": "ollama cloud",
    "ollamacloud": "ollama cloud",
    "open ai": "openai",
}

_UNKNOWN = ProviderCapabilities(provider="unknown")


def _canonical(provider_name: str) -> str:
    key = (provider_name or "").strip().lower()
    return _ALIASES.get(key, key)


def capabilities_for(provider_name: str) -> ProviderCapabilities:
    """Return capabilities for ``provider_name``.

    Unknown providers get a conservative all-False record rather than raising,
    so a new or misspelled provider degrades to "no extras" instead of
    crashing a GUI event handler (where wx would swallow the traceback).
    """
    return _REGISTRY.get(_canonical(provider_name), _UNKNOWN)


def list_providers() -> List[str]:
    """Canonical names of every registered provider."""
    return sorted(_REGISTRY)


def supported_attachments(provider_name: str) -> List[str]:
    """MIME types this provider accepts as chat attachments."""
    return list(capabilities_for(provider_name).attachment_mime_types)


def supports_attachments(provider_name: str) -> bool:
    """True if this provider accepts any file attachments in chat."""
    return capabilities_for(provider_name).supports_attachments


# MIME type -> file extension globs for wx.FileDialog wildcards.
_MIME_TO_EXTENSIONS: Dict[str, str] = {
    "image/jpeg": "*.jpg;*.jpeg",
    "image/png": "*.png",
    "image/gif": "*.gif",
    "image/webp": "*.webp",
    "image/bmp": "*.bmp",
    "image/tiff": "*.tif;*.tiff",
    "application/pdf": "*.pdf",
}


def attachment_wildcard(provider_name: str) -> str:
    """Build a ``wx.FileDialog`` wildcard string for this provider.

    Produces an "All supported" group first, then per-kind groups, then
    all-files.  Falls back to a plain all-files wildcard when the provider
    accepts no attachments.

    Contains no wx import — it only formats the string wx expects.
    """
    mimes = supported_attachments(provider_name)
    if not mimes:
        return "All files (*.*)|*.*"

    image_exts: List[str] = []
    doc_exts: List[str] = []
    for mime in mimes:
        exts = _MIME_TO_EXTENSIONS.get(mime)
        if not exts:
            continue
        (image_exts if mime.startswith("image/") else doc_exts).append(exts)

    groups: List[str] = []
    all_exts = ";".join(image_exts + doc_exts)
    if all_exts:
        groups.append(f"All supported ({all_exts})|{all_exts}")
    if image_exts:
        joined = ";".join(image_exts)
        groups.append(f"Images ({joined})|{joined}")
    if doc_exts:
        joined = ";".join(doc_exts)
        groups.append(f"Documents ({joined})|{joined}")
    groups.append("All files (*.*)|*.*")
    return "|".join(groups)


def model_limits(provider_name: str, model: str) -> Tuple[Optional[int], Optional[int]]:
    """Return ``(context_window, max_output_tokens)`` for a specific model.

    Either element is ``None`` when the value is not recorded. Callers must
    supply their own fallback rather than relying on a guess from this module.

    Known gap: ``OPENAI_MODEL_METADATA`` currently records no ``context_window``
    or ``max_output`` for any model, so OpenAI returns ``(None, None)``.
    """
    key = _canonical(provider_name)
    meta: dict = {}
    try:
        if key == "claude":
            from .claude import CLAUDE_MODEL_METADATA

            meta = CLAUDE_MODEL_METADATA.get(model, {})
        elif key == "openai":
            from .openai_provider import OPENAI_MODEL_METADATA

            meta = OPENAI_MODEL_METADATA.get(model, {})
    except ImportError:
        return (None, None)

    context = meta.get("context_window")
    max_output = meta.get("max_output")
    return (
        int(context) if context else None,
        int(max_output) if max_output else None,
    )
