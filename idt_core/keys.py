"""One place to resolve an API key.

Chat previously resolved keys in five different places, each slightly
different: ``ChatWindow._get_api_key_for_provider``, a second variant inside
``ChatWindow.on_summarize_compact`` (config-only, so Compact failed for anyone
whose key came from the environment), and three more in ``workers_wx.py`` and
``ai_providers.py``. Which sources worked depended on which code path you hit.

Resolution order, first hit wins:

1. Environment variable — ``ANTHROPIC_API_KEY``, ``OPENAI_API_KEY``
2. ``image_describer_config.json`` → ``api_keys`` (what the GUI's
   Tools → Configure Settings writes), matched case-insensitively
3. Legacy plain-text files — ``claude.txt``, ``anthropic.txt``,
   ``openai_api_key.txt``, ``openai.txt`` — searched in the working directory
   and next to a frozen executable

Providers needing no key (Ollama, MLX) return None, and that is not an error.

Nothing here logs or prints a key, or any prefix of one.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List, Optional

__all__ = ["resolve_api_key", "requires_api_key", "missing_key_message", "ENV_VARS"]

#: Canonical provider name -> environment variable.
ENV_VARS = {
    "claude": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
}

#: Canonical provider name -> legacy plain-text filenames, in priority order.
_LEGACY_FILES = {
    "claude": ("claude.txt", "anthropic.txt"),
    "openai": ("openai_api_key.txt", "openai.txt"),
}

#: Spellings that have appeared as keys in image_describer_config.json.
_CONFIG_ALIASES = {
    "claude": ("claude", "anthropic", "Claude", "Anthropic", "ANTHROPIC"),
    "openai": ("openai", "OpenAI", "OPENAI", "open_ai"),
}


def _canonical(provider: str) -> str:
    try:
        from .providers.registry import capabilities_for

        name = capabilities_for(provider).provider
        if name != "unknown":
            return name
    except ImportError:  # pragma: no cover
        pass
    return (provider or "").strip().lower()


def requires_api_key(provider: str) -> bool:
    """True if this provider cannot work without a key."""
    try:
        from .providers.registry import capabilities_for

        return capabilities_for(provider).requires_api_key
    except ImportError:  # pragma: no cover
        return _canonical(provider) in ENV_VARS


def _search_dirs() -> List[Path]:
    dirs = [Path.cwd()]
    if getattr(sys, "frozen", False):
        dirs.append(Path(sys.executable).parent)
    return dirs


def _from_env(name: str) -> Optional[str]:
    var = ENV_VARS.get(name)
    if not var:
        return None
    return (os.environ.get(var) or "").strip() or None


def _from_config(name: str) -> Optional[str]:
    try:
        from .config_loader import load_json_config

        config = load_json_config("image_describer_config.json") or {}
    except Exception:
        return None

    keys = config.get("api_keys") or {}
    if not isinstance(keys, dict):
        return None

    for alias in _CONFIG_ALIASES.get(name, (name,)):
        value = keys.get(alias)
        if isinstance(value, str) and value.strip():
            return value.strip()

    # Last resort: case-insensitive scan, so an unanticipated capitalisation
    # does not silently behave as "no key configured".
    lowered = {str(k).lower(): v for k, v in keys.items()}
    for alias in _CONFIG_ALIASES.get(name, (name,)):
        value = lowered.get(alias.lower())
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _from_legacy_file(name: str) -> Optional[str]:
    for directory in _search_dirs():
        for filename in _LEGACY_FILES.get(name, ()):
            path = directory / filename
            try:
                if path.is_file():
                    value = path.read_text(encoding="utf-8").strip()
                    if value:
                        return value
            except OSError:
                continue
    return None


def resolve_api_key(provider: str) -> Optional[str]:
    """Return the API key for ``provider``, or None if there is none to find.

    None is the correct answer for Ollama and MLX. For providers that do need a
    key, None means the caller should fail with :func:`missing_key_message`
    rather than letting the SDK raise something less actionable.
    """
    name = _canonical(provider)
    if name not in ENV_VARS:
        return None
    return _from_env(name) or _from_config(name) or _from_legacy_file(name)


def missing_key_message(provider: str) -> str:
    """An error message that names the variable to set."""
    name = _canonical(provider)
    var = ENV_VARS.get(name, "the provider's API key")
    return (
        f"No API key found for {provider}. Set the {var} environment variable, "
        f"or add it under Tools -> Configure Settings in ImageDescriber."
    )
