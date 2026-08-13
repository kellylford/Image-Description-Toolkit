"""
AI provider implementations and the capability registry.

This file was 0 bytes for a long time, and that emptiness is part of why three
parallel provider layers grew up unremarked (``idt_core/providers``,
``imagedescriber/ai_providers.py``, and inline SDK calls in ``workers_wx.py``).
Re-exporting the registry here gives callers one obvious import to reach for.

Only the registry is re-exported eagerly — it has no third-party dependencies.
The concrete providers are deliberately *not* imported here: each pulls in a
vendor SDK (``anthropic``, ``openai``, ``ollama``) and importing them all would
make ``idt_core.providers`` fail whenever any one SDK is absent. Import those
from their own modules, e.g. ``from idt_core.providers.claude import
ClaudeProvider``.
"""
from .base import BaseProvider, DescriptionResult
from .registry import (
    ProviderCapabilities,
    attachment_wildcard,
    capabilities_for,
    list_providers,
    model_limits,
    supported_attachments,
    supports_attachments,
)

__all__ = [
    "BaseProvider",
    "DescriptionResult",
    "ProviderCapabilities",
    "attachment_wildcard",
    "capabilities_for",
    "list_providers",
    "model_limits",
    "supported_attachments",
    "supports_attachments",
]
