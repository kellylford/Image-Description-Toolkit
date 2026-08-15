"""One key resolver, replacing five near-identical ones.

Chat used to resolve API keys in five places, and which sources worked depended
on which code path you hit. The clearest symptom: ``ChatWindow`` checked the
environment, then a config file, then legacy text files — but its
``on_summarize_compact`` checked the config file *only*. So Summarize & Compact
failed with "no API key" for anyone whose key came from an environment
variable, while ordinary sending worked fine in the same window.

These tests pin the order and, just as importantly, pin that *every* caller
gets the same order.

Note the last test: a key must never reach a log or an error message. That is
not hypothetical either — commit 43a8248 removed debug prints that exposed API
key lookups.
"""

import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from idt_core import keys as key_module  # noqa: E402


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch, tmp_path):
    """No ambient keys, no ambient config, and a scratch working directory.

    The config source is neutralised at its real seam --
    ``idt_core.config_loader.load_json_config`` -- rather than by stubbing
    ``_from_config``. That way a test wanting to exercise the config path can
    simply patch the same seam again, instead of unwinding this fixture.
    """
    import idt_core.config_loader as loader

    for var in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(loader, "load_json_config", lambda *a, **k: {})
    # Neutralise the OS credential store too: once someone stores a real key
    # via the settings UI, these tests would otherwise start reading it.
    monkeypatch.setattr(key_module, "_from_store", lambda name: None)
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def config_keys(monkeypatch):
    """Set the api_keys block that image_describer_config.json would provide."""
    import idt_core.config_loader as loader

    def _set(mapping):
        monkeypatch.setattr(
            loader, "load_json_config", lambda *a, **k: {"api_keys": mapping}
        )

    return _set


# ---------------------------------------------------------------------------
# Providers that need no key
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("provider", ["ollama", "mlx"])
def test_local_providers_need_no_key(provider):
    assert key_module.requires_api_key(provider) is False
    assert key_module.resolve_api_key(provider) is None


@pytest.mark.parametrize("provider", ["claude", "openai", "anthropic"])
def test_cloud_providers_need_a_key(provider):
    assert key_module.requires_api_key(provider) is True


# ---------------------------------------------------------------------------
# Resolution order
# ---------------------------------------------------------------------------


def test_environment_variable_is_used(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-from-env")
    assert key_module.resolve_api_key("claude") == "sk-from-env"


def test_openai_reads_its_own_variable(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
    assert key_module.resolve_api_key("openai") == "sk-openai"
    assert key_module.resolve_api_key("claude") is None


def test_config_alone_resolves(config_keys):
    config_keys({"claude": "sk-from-config"})
    assert key_module.resolve_api_key("claude") == "sk-from-config"


def test_environment_beats_config(monkeypatch, config_keys):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-from-env")
    config_keys({"claude": "sk-from-config"})
    assert key_module.resolve_api_key("claude") == "sk-from-env"


def test_config_beats_legacy_file(config_keys, clean_environment):
    (clean_environment / "claude.txt").write_text("sk-from-file", encoding="utf-8")
    config_keys({"claude": "sk-from-config"})
    assert key_module.resolve_api_key("claude") == "sk-from-config"


def test_legacy_file_is_the_last_resort(clean_environment):
    (clean_environment / "claude.txt").write_text("sk-from-file\n", encoding="utf-8")
    assert key_module.resolve_api_key("claude") == "sk-from-file"


def test_anthropic_txt_is_also_accepted(clean_environment):
    (clean_environment / "anthropic.txt").write_text("sk-alt", encoding="utf-8")
    assert key_module.resolve_api_key("claude") == "sk-alt"


def test_claude_txt_wins_over_anthropic_txt(clean_environment):
    (clean_environment / "claude.txt").write_text("sk-first", encoding="utf-8")
    (clean_environment / "anthropic.txt").write_text("sk-second", encoding="utf-8")
    assert key_module.resolve_api_key("claude") == "sk-first"


def test_nothing_configured_returns_none():
    assert key_module.resolve_api_key("claude") is None


# ---------------------------------------------------------------------------
# Robustness
# ---------------------------------------------------------------------------


def test_blank_values_do_not_count_as_configured(monkeypatch, clean_environment):
    """An empty variable must fall through, not resolve to an unusable ''."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "   ")
    (clean_environment / "claude.txt").write_text("sk-real", encoding="utf-8")
    assert key_module.resolve_api_key("claude") == "sk-real"


def test_an_empty_legacy_file_is_ignored(clean_environment):
    (clean_environment / "claude.txt").write_text("\n  \n", encoding="utf-8")
    assert key_module.resolve_api_key("claude") is None


def test_surrounding_whitespace_is_stripped(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "  sk-padded\n")
    assert key_module.resolve_api_key("openai") == "sk-padded"


@pytest.mark.parametrize("spelling", ["claude", "Claude", "CLAUDE", "anthropic"])
def test_provider_spelling_does_not_matter(monkeypatch, spelling):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-x")
    assert key_module.resolve_api_key(spelling) == "sk-x"


@pytest.mark.parametrize("written_as", ["claude", "Claude", "AnThRoPiC", "anthropic"])
def test_config_key_capitalisation_does_not_matter(config_keys, written_as):
    """The GUI has written 'Claude', 'claude' and 'Anthropic' at various times."""
    config_keys({written_as: "sk-odd-caps"})
    assert key_module.resolve_api_key("claude") == "sk-odd-caps"


def test_a_blank_config_value_is_not_a_key(config_keys, clean_environment):
    config_keys({"claude": "   "})
    (clean_environment / "claude.txt").write_text("sk-real", encoding="utf-8")
    assert key_module.resolve_api_key("claude") == "sk-real"


def test_a_non_dict_api_keys_block_is_ignored(config_keys):
    config_keys("not-a-dict")
    assert key_module.resolve_api_key("claude") is None


def test_an_unreadable_config_does_not_raise(monkeypatch):
    """A corrupt config must mean "no key", not a crash inside a wx handler."""
    import idt_core.config_loader as loader

    def boom(*_args, **_kwargs):
        raise json.JSONDecodeError("bad", "", 0)

    monkeypatch.setattr(loader, "load_json_config", boom)
    assert key_module.resolve_api_key("claude") is None


# ---------------------------------------------------------------------------
# The message shown when there is no key
# ---------------------------------------------------------------------------


def test_missing_key_message_names_the_variable_to_set():
    message = key_module.missing_key_message("claude")
    assert "ANTHROPIC_API_KEY" in message

    message = key_module.missing_key_message("openai")
    assert "OPENAI_API_KEY" in message


def test_missing_key_message_never_contains_a_key(monkeypatch):
    """Error text gets pasted into issues; it must not carry a secret."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-supersecret-value")
    message = key_module.missing_key_message("claude")
    assert "supersecret" not in message
    assert "sk-ant" not in message


# ---------------------------------------------------------------------------
# The config loader's real return shape
# ---------------------------------------------------------------------------


def test_config_keys_survive_the_loaders_tuple_return_shape(monkeypatch):
    """idt_core.config_loader.load_json_config returns (config, path, source).

    _from_config assumed a bare dict, so anyone whose key existed ONLY in the
    config file crashed resolution with "'tuple' object has no attribute
    'get'" — masked in every other test because the fixture stubs the loader
    with a dict. This test feeds the real shape.
    """
    import idt_core.config_loader as loader

    monkeypatch.setattr(
        loader, "load_json_config",
        lambda *a, **k: ({"api_keys": {"claude": "sk-from-config"}},
                         Path("fake.json"), "bundled"),
    )
    assert key_module.resolve_api_key("claude") == "sk-from-config"


# ---------------------------------------------------------------------------
# The ollama.com web-search key (not a chat provider)
# ---------------------------------------------------------------------------


def test_ollama_com_key_resolves_from_the_environment(monkeypatch):
    monkeypatch.setenv("OLLAMA_API_KEY", "web-search-key")
    assert key_module.resolve_api_key("ollama.com") == "web-search-key"


def test_ollama_com_key_resolves_from_config(config_keys):
    config_keys({"ollama.com": "config-key"})
    assert key_module.resolve_api_key("ollama.com") == "config-key"


def test_plain_ollama_still_needs_no_key(monkeypatch):
    """The web-search credential must not leak onto the chat provider."""
    monkeypatch.setenv("OLLAMA_API_KEY", "web-search-key")
    assert key_module.resolve_api_key("ollama") is None
    assert key_module.requires_api_key("ollama.com") is False


# ---------------------------------------------------------------------------
# The OS credential store
# ---------------------------------------------------------------------------

# Captured at import time, before the autouse fixture swaps it for a stub —
# reading key_module._from_store inside a fixture would recover the stub.
_REAL_FROM_STORE = key_module._from_store


@pytest.fixture
def scratch_store(monkeypatch):
    """Point the store at a scratch service name so no real key is touched."""
    import uuid

    monkeypatch.setattr(key_module, "_CRED_SERVICE", f"IDT-Test-{uuid.uuid4().hex[:8]}")
    # Undo the autouse neutralisation for tests that exercise the store.
    monkeypatch.setattr(key_module, "_from_store", _REAL_FROM_STORE)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows Credential Manager")
class TestWindowsCredentialStore:
    def test_roundtrip_write_read_delete(self, scratch_store):
        assert key_module.set_api_key("claude", "sk-test-roundtrip") is True
        try:
            assert key_module.resolve_api_key("claude") == "sk-test-roundtrip"
            assert key_module.key_source("claude") == "credential store"
        finally:
            assert key_module.delete_api_key("claude") is True
        assert key_module.resolve_api_key("claude") is None

    def test_overwrite_replaces_the_stored_key(self, scratch_store):
        key_module.set_api_key("openai", "first")
        key_module.set_api_key("openai", "second")
        try:
            assert key_module.resolve_api_key("openai") == "second"
        finally:
            key_module.delete_api_key("openai")

    def test_ollama_com_lives_in_the_store_too(self, scratch_store):
        assert key_module.set_api_key("ollama.com", "web-key") is True
        try:
            assert key_module.resolve_api_key("ollama.com") == "web-key"
        finally:
            key_module.delete_api_key("ollama.com")

    def test_utf16_blobs_from_other_tools_are_readable(self, scratch_store):
        """cmdkey and PowerShell write UTF-16LE blobs; so do we. The NUL
        heuristic must pick the right decoding."""
        key_module.set_api_key("claude", "interop-key")
        try:
            assert key_module._win_read("claude") == "interop-key"
        finally:
            key_module.delete_api_key("claude")


class TestStoreResolutionOrder:
    def test_environment_beats_the_store(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "from-env")
        monkeypatch.setattr(key_module, "_from_store", lambda name: "from-store")
        assert key_module.resolve_api_key("claude") == "from-env"
        assert key_module.key_source("claude") == "environment"

    def test_store_beats_the_config_file(self, monkeypatch, config_keys):
        config_keys({"claude": "from-config"})
        monkeypatch.setattr(key_module, "_from_store", lambda name: "from-store")
        assert key_module.resolve_api_key("claude") == "from-store"
        assert key_module.key_source("claude") == "credential store"

    def test_a_broken_store_degrades_to_config(self, monkeypatch, config_keys):
        config_keys({"claude": "from-config"})

        def broken(name):
            raise OSError("store unavailable")

        if sys.platform == "win32":
            monkeypatch.setattr(key_module, "_win_read", broken)
        else:
            monkeypatch.setattr(key_module, "_mac_read", broken)
        monkeypatch.setattr(key_module, "_from_store", _REAL_FROM_STORE)
        assert key_module.resolve_api_key("claude") == "from-config"

    def test_set_api_key_rejects_empty_values(self):
        assert key_module.set_api_key("claude", "") is False
        assert key_module.set_api_key("claude", "   ") is False
        assert key_module.set_api_key("", "value") is False

    def test_set_api_key_canonicalises_aliases(self, monkeypatch):
        written = {}
        if sys.platform == "win32":
            monkeypatch.setattr(key_module, "_win_write",
                                lambda name, value: written.update({name: value}) or True)
        else:
            monkeypatch.setattr(key_module, "_mac_write",
                                lambda name, value: written.update({name: value}) or True)
        key_module.set_api_key("Anthropic", "sk-x")
        assert list(written) == ["claude"]


class TestMacKeychainCommands:
    """The macOS path shells out to `security`; pin the exact commands."""

    @pytest.fixture
    def recorded(self, monkeypatch):
        calls = []

        class _Result:
            returncode = 0
            stdout = "the-secret\n"

        def fake_run(args, **kwargs):
            calls.append(args)
            return _Result()

        import subprocess

        monkeypatch.setattr(subprocess, "run", fake_run)
        return calls

    def test_read_uses_find_generic_password(self, recorded):
        assert key_module._mac_read("claude") == "the-secret"
        assert recorded[0][:2] == ["security", "find-generic-password"]
        assert "-w" in recorded[0]

    def test_write_uses_add_generic_password_with_update(self, recorded):
        assert key_module._mac_write("claude", "the-secret") is True
        assert recorded[0][:2] == ["security", "add-generic-password"]
        assert "-U" in recorded[0], "-U updates an existing item instead of failing"

    def test_delete_uses_delete_generic_password(self, recorded):
        assert key_module._mac_delete("claude") is True
        assert recorded[0][:2] == ["security", "delete-generic-password"]


# ---------------------------------------------------------------------------
# store_api_key -- the store-then-config fallback both key dialogs share
# ---------------------------------------------------------------------------


class TestStoreApiKeyFallback:
    def test_prefers_the_credential_store(self, monkeypatch):
        monkeypatch.setattr(key_module, "credential_store_name", lambda: "Fake Store")
        monkeypatch.setattr(key_module, "set_api_key", lambda p, v: True)
        assert key_module.store_api_key("claude", "sk-x") == "credential store"

    def test_falls_back_to_the_config_file_without_a_store(self, monkeypatch, tmp_path):
        """A settings dialog that can only refuse to save is worse than the
        plaintext config the app has always supported."""
        import json

        import idt_core.config_loader as loader

        config_path = tmp_path / "image_describer_config.json"
        monkeypatch.setattr(key_module, "credential_store_name", lambda: "")
        monkeypatch.setattr(
            loader, "load_json_config",
            lambda *a, **k: ({"api_keys": {}}, config_path, "test"))

        assert key_module.store_api_key("Anthropic", "sk-x") == "config file"
        written = json.loads(config_path.read_text(encoding="utf-8"))
        assert written["api_keys"]["claude"] == "sk-x", "canonical name, not the alias"

    def test_returns_empty_when_both_destinations_fail(self, monkeypatch):
        import idt_core.config_loader as loader

        monkeypatch.setattr(key_module, "credential_store_name", lambda: "")

        def boom(*a, **k):
            raise OSError("no config")

        monkeypatch.setattr(loader, "load_json_config", boom)
        assert key_module.store_api_key("claude", "sk-x") == ""

    def test_rejects_blank_input_before_touching_anything(self, monkeypatch):
        def do_not_call(*a, **k):  # pragma: no cover
            raise AssertionError("blank input must not reach a store")

        monkeypatch.setattr(key_module, "set_api_key", do_not_call)
        assert key_module.store_api_key("claude", "   ") == ""
        assert key_module.store_api_key("", "value") == ""


# ---------------------------------------------------------------------------
# key_source ladder, deletion, and per-platform naming
# ---------------------------------------------------------------------------


class TestKeySourceLadder:
    def test_config_and_legacy_and_absent_sources(self, config_keys, clean_environment):
        config_keys({"claude": "sk-config"})
        assert key_module.key_source("claude") == "config file"

    def test_legacy_file_source(self, clean_environment):
        (clean_environment / "claude.txt").write_text("sk-file", encoding="utf-8")
        assert key_module.key_source("claude") == "legacy file"

    def test_no_key_anywhere_is_none(self):
        assert key_module.key_source("claude") is None

    def test_keyless_providers_have_no_source(self):
        assert key_module.key_source("ollama") is None

    def test_from_env_without_a_variable_mapping(self):
        assert key_module._from_env("ollama") is None

    def test_a_non_dict_config_payload_is_no_key(self, monkeypatch, tmp_path):
        import idt_core.config_loader as loader

        monkeypatch.setattr(loader, "load_json_config",
                            lambda *a, **k: (["not", "a", "dict"], tmp_path / "c.json", "t"))
        assert key_module._from_config("claude") is None

    def test_an_unreadable_legacy_file_is_skipped(self, clean_environment):
        # A directory named like the key file: read_text raises OSError.
        (clean_environment / "claude.txt").mkdir()
        assert key_module.resolve_api_key("claude") is None


class TestDeleteAndPlatforms:
    def test_delete_returns_true_when_the_store_deletes(self, monkeypatch):
        if sys.platform == "win32":
            monkeypatch.setattr(key_module, "_win_delete", lambda name: True)
        else:
            monkeypatch.setattr(key_module, "_mac_delete", lambda name: True)
        assert key_module.delete_api_key("claude") is True

    def test_delete_swallows_store_errors(self, monkeypatch):
        def boom(name):
            raise OSError("store broke")

        if sys.platform == "win32":
            monkeypatch.setattr(key_module, "_win_delete", boom)
        else:
            monkeypatch.setattr(key_module, "_mac_delete", boom)
        assert key_module.delete_api_key("claude") is False

    def test_set_api_key_swallows_store_errors(self, monkeypatch):
        def boom(name, value):
            raise OSError("store broke")

        if sys.platform == "win32":
            monkeypatch.setattr(key_module, "_win_write", boom)
        else:
            monkeypatch.setattr(key_module, "_mac_write", boom)
        assert key_module.set_api_key("claude", "sk-x") is False

    @pytest.mark.parametrize("platform,expected", [
        ("win32", "Windows Credential Manager"),
        ("darwin", "macOS Keychain"),
        ("linux", ""),
    ])
    def test_store_name_per_platform(self, monkeypatch, platform, expected):
        monkeypatch.setattr(key_module.sys, "platform", platform)
        assert key_module.credential_store_name() == expected

    def test_platforms_without_a_store_resolve_and_delete_to_nothing(self, monkeypatch):
        monkeypatch.setattr(key_module.sys, "platform", "linux")
        assert key_module._from_store("claude") is None
        assert key_module.delete_api_key("claude") is False
        assert key_module.set_api_key("claude", "sk-x") is False

    def test_store_api_key_repairs_a_non_dict_config(self, monkeypatch, tmp_path):
        """A corrupt config payload becomes a fresh dict, not a crash."""
        import json as json_mod

        import idt_core.config_loader as loader

        config_path = tmp_path / "image_describer_config.json"
        monkeypatch.setattr(key_module, "credential_store_name", lambda: "")
        monkeypatch.setattr(loader, "load_json_config",
                            lambda *a, **k: ("not-a-dict", config_path, "t"))

        assert key_module.store_api_key("claude", "sk-x") == "config file"
        written = json_mod.loads(config_path.read_text(encoding="utf-8"))
        assert written == {"api_keys": {"claude": "sk-x"}}
