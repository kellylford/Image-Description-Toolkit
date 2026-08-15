"""One place to resolve an API key.

Chat previously resolved keys in five different places, each slightly
different: ``ChatWindow._get_api_key_for_provider``, a second variant inside
``ChatWindow.on_summarize_compact`` (config-only, so Compact failed for anyone
whose key came from the environment), and three more in ``workers_wx.py`` and
``ai_providers.py``. Which sources worked depended on which code path you hit.

Resolution order, first hit wins:

1. Environment variable — ``ANTHROPIC_API_KEY``, ``OPENAI_API_KEY``,
   ``OLLAMA_API_KEY``
2. The operating system's credential store — Windows Credential Manager or
   the macOS Keychain — which is where :func:`set_api_key` writes
3. ``image_describer_config.json`` → ``api_keys`` (what the GUI's
   Tools → Configure Settings used to write), matched case-insensitively
4. Legacy plain-text files — ``claude.txt``, ``anthropic.txt``,
   ``openai_api_key.txt``, ``openai.txt`` — searched in the working directory
   and next to a frozen executable

Providers needing no key (Ollama, MLX) return None, and that is not an error.

The credential store uses only the standard library on purpose: ctypes over
advapi32 on Windows, the ``security`` command on macOS. A ``keyring``
dependency would be another package to carry through three PyInstaller specs
and another way for a frozen build to differ from a dev run.

Nothing here logs or prints a key, or any prefix of one.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List, Optional

__all__ = [
    "resolve_api_key",
    "requires_api_key",
    "missing_key_message",
    "set_api_key",
    "store_api_key",
    "delete_api_key",
    "key_source",
    "credential_store_name",
    "ENV_VARS",
]

#: Canonical provider name -> environment variable.
#: "ollama.com" is not a chat provider: it is the hosted web-search API used
#: by the chat tools, kept distinct from "ollama" (which needs no key at all).
ENV_VARS = {
    "claude": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "ollama.com": "OLLAMA_API_KEY",
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
    "ollama.com": ("ollama.com", "ollama_com", "ollama cloud", "ollama_cloud"),
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

        loaded = load_json_config("image_describer_config.json")
    except Exception:
        return None

    # idt_core.config_loader returns (config, path, source); the older
    # scripts/ loader returns just the dict. Accept both — assuming the dict
    # shape made every config-file-only key crash resolution with
    # "'tuple' object has no attribute 'get'".
    config = loaded[0] if isinstance(loaded, tuple) else loaded
    if not isinstance(config, dict):
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


# ---------------------------------------------------------------------------
# OS credential store
# ---------------------------------------------------------------------------

#: Prefix for entries in the OS store. Tests point this at a scratch name so
#: they never touch a real stored key.
_CRED_SERVICE = "Image Description Toolkit"


def _cred_target(name: str) -> str:
    return f"{_CRED_SERVICE}/{name}"


def credential_store_name() -> str:
    """Human name of the OS store, or "" when this platform has none."""
    if sys.platform == "win32":
        return "Windows Credential Manager"
    if sys.platform == "darwin":
        return "macOS Keychain"
    return ""


def _win_credential():
    """(ctypes, advapi32, CREDENTIAL struct type) — shared by read/write/delete.

    Takes no target: it only builds the struct type. It used to accept a
    ``target`` it never read, which invited callers to assume the returned
    struct was bound to that credential.
    """
    import ctypes
    import ctypes.wintypes as wintypes

    class CREDENTIAL(ctypes.Structure):
        _fields_ = [
            ("Flags", wintypes.DWORD),
            ("Type", wintypes.DWORD),
            ("TargetName", wintypes.LPWSTR),
            ("Comment", wintypes.LPWSTR),
            ("LastWritten", wintypes.FILETIME),
            ("CredentialBlobSize", wintypes.DWORD),
            ("CredentialBlob", ctypes.POINTER(ctypes.c_byte)),
            ("Persist", wintypes.DWORD),
            ("AttributeCount", wintypes.DWORD),
            ("Attributes", ctypes.c_void_p),
            ("TargetAlias", wintypes.LPWSTR),
            ("UserName", wintypes.LPWSTR),
        ]

    return ctypes, ctypes.windll.advapi32, CREDENTIAL


_CRED_TYPE_GENERIC = 1
_CRED_PERSIST_LOCAL_MACHINE = 2


def _win_read(name: str) -> Optional[str]:
    ctypes, advapi, CREDENTIAL = _win_credential()
    pointer = ctypes.POINTER(CREDENTIAL)()
    if not advapi.CredReadW(_cred_target(name), _CRED_TYPE_GENERIC, 0,
                            ctypes.byref(pointer)):
        return None
    try:
        cred = pointer.contents
        blob = ctypes.string_at(cred.CredentialBlob, cred.CredentialBlobSize)
    finally:
        advapi.CredFree(pointer)
    # We write UTF-16LE (the cmdkey/PowerShell convention). A key added by
    # hand with some other tool may be UTF-8; ASCII secrets make the two easy
    # to tell apart because UTF-16LE carries interleaved NULs.
    encoding = "utf-16-le" if b"\x00" in blob else "utf-8"
    return blob.decode(encoding, errors="ignore").strip() or None


def _win_write(name: str, secret: str) -> bool:
    ctypes, advapi, CREDENTIAL = _win_credential()
    blob = secret.encode("utf-16-le")
    buffer = ctypes.create_string_buffer(blob, len(blob))

    cred = CREDENTIAL()
    cred.Type = _CRED_TYPE_GENERIC
    cred.TargetName = _cred_target(name)
    cred.CredentialBlobSize = len(blob)
    cred.CredentialBlob = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte))
    cred.Persist = _CRED_PERSIST_LOCAL_MACHINE
    cred.UserName = "idt"
    return bool(advapi.CredWriteW(ctypes.byref(cred), 0))


def _win_delete(name: str) -> bool:
    ctypes, advapi, _ = _win_credential()
    return bool(advapi.CredDeleteW(_cred_target(name), _CRED_TYPE_GENERIC, 0))


def _mac_security(*args: str):
    import subprocess

    return subprocess.run(
        ["security", *args], capture_output=True, text=True, timeout=15
    )


def _mac_read(name: str) -> Optional[str]:
    result = _mac_security(
        "find-generic-password", "-s", _CRED_SERVICE, "-a", name, "-w"
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _mac_write(name: str, secret: str) -> bool:
    # -U updates an existing item instead of failing on it.
    result = _mac_security(
        "add-generic-password", "-U", "-s", _CRED_SERVICE, "-a", name,
        "-w", secret,
    )
    return result.returncode == 0


def _mac_delete(name: str) -> bool:
    result = _mac_security(
        "delete-generic-password", "-s", _CRED_SERVICE, "-a", name
    )
    return result.returncode == 0


def _from_store(name: str) -> Optional[str]:
    try:
        if sys.platform == "win32":
            return _win_read(name)
        if sys.platform == "darwin":
            return _mac_read(name)
    except Exception:
        # The store must never break resolution; the remaining sources
        # (config, legacy files) still get their chance.
        return None
    return None


def set_api_key(provider: str, value: str) -> bool:
    """Store ``value`` in the OS credential store under ``provider``.

    Returns False when this platform has no store or the write failed —
    callers decide whether to fall back to the config file. Never logs the
    value.
    """
    name = _canonical(provider)
    value = (value or "").strip()
    if not name or not value:
        return False
    try:
        if sys.platform == "win32":
            return _win_write(name, value)
        if sys.platform == "darwin":
            return _mac_write(name, value)
    except Exception:
        return False
    return False


def delete_api_key(provider: str) -> bool:
    """Remove ``provider``'s key from the OS credential store."""
    name = _canonical(provider)
    try:
        if sys.platform == "win32":
            return _win_delete(name)
        if sys.platform == "darwin":
            return _mac_delete(name)
    except Exception:
        return False
    return False


def store_api_key(provider: str, value: str) -> str:
    """Store a key preferring the OS store, falling back to the config file.

    Returns where the key landed — ``"credential store"`` or ``"config
    file"`` — or ``""`` when both destinations failed. The fallback exists
    for platforms with no supported store (Linux dev mode): a settings
    dialog that can only refuse to save is worse than the plaintext config
    the app has always supported. Both GUI key dialogs go through here so
    the two surfaces cannot drift apart.
    """
    name = _canonical(provider)
    value = (value or "").strip()
    if not name or not value:
        return ""

    if credential_store_name() and set_api_key(name, value):
        return "credential store"

    try:
        import json

        from .config_loader import load_json_config

        loaded = load_json_config("image_describer_config.json")
        if isinstance(loaded, tuple):
            config, path = loaded[0], loaded[1]
        else:  # pragma: no cover - older loader shape
            return ""
        if not isinstance(config, dict):
            config = {}
        config.setdefault("api_keys", {})[name] = value
        Path(path).write_text(json.dumps(config, indent=2), encoding="utf-8")
        return "config file"
    except Exception:
        return ""


def key_source(provider: str) -> Optional[str]:
    """Where the resolved key comes from, for settings UIs.

    One of "environment", "credential store", "config file", "legacy file",
    or None when no key is found. Mirrors :func:`resolve_api_key` exactly —
    a UI showing a different answer than resolution uses would be worse than
    no answer.
    """
    name = _canonical(provider)
    if name not in ENV_VARS:
        return None
    if _from_env(name):
        return "environment"
    if _from_store(name):
        return "credential store"
    if _from_config(name):
        return "config file"
    if _from_legacy_file(name):
        return "legacy file"
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
    return (
        _from_env(name)
        or _from_store(name)
        or _from_config(name)
        or _from_legacy_file(name)
    )


def missing_key_message(provider: str) -> str:
    """An error message that names the variable to set."""
    name = _canonical(provider)
    var = ENV_VARS.get(name, "the provider's API key")
    return (
        f"No API key found for {provider}. Set the {var} environment variable, "
        f"or add it under Tools -> Configure Settings in ImageDescriber."
    )
