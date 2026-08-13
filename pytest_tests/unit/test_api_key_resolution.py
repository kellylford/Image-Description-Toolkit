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

    for var in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(loader, "load_json_config", lambda *a, **k: {})
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
