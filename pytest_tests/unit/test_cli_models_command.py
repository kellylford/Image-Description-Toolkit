"""`idt models` after issue #267.

Two things worth locking down here, for different reasons.

The **key lookup** is a bug fix with no other test: this command checked
``os.environ["ANTHROPIC_API_KEY"]`` directly, so anyone whose key lived in the
Windows Credential Manager or in image_describer_config.json -- both of which
IDT's own settings dialogs write to -- was told they had no key at all, while
every other part of the app worked fine for them.

The **JSON shape** is a contract. ``models`` has always been a list of plain id
strings and scripts may be reading it; the richer per-model information added
here goes in a parallel ``details`` key rather than changing that.

No network: the catalog's fetch seam is patched, the same way test_updater.py
patches ``_fetch_releases`` rather than reaching for a real feed.
"""

import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from cli import main as cli_main  # noqa: E402
from idt_core.providers import catalog  # noqa: E402
from idt_core.providers.claude import CLAUDE_MODELS  # noqa: E402

pytestmark = pytest.mark.unit


class _Args:
    """Stand-in for the argparse namespace `cmd_models` receives."""

    def __init__(self, **kwargs):
        self.provider = None
        self.ollama_host = "http://localhost:11434"
        self.json_out = False
        self.refresh = False
        self.all_models = False
        for key, value in kwargs.items():
            setattr(self, key, value)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Nothing in this file may reach a provider.

    The stand-in raises a plain ``RuntimeError`` -- i.e. it behaves like an
    offline machine -- rather than calling ``pytest.fail``. ``pytest.fail``
    raises a ``BaseException``, which travels straight through the production
    code's ``except Exception`` and lands somewhere unrelated, so a test that
    tripped it reported a confusing failure two tests later instead of its own.
    (It did find a real bug that way -- see
    ``test_model_refresh.test_a_baseexception_does_not_wedge_the_provider`` --
    but as a default it obscures more than it catches.)
    """
    monkeypatch.setattr(
        catalog, "_fetch",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no network in tests")),
    )
    catalog.invalidate()
    yield
    catalog.invalidate()


def _run(args) -> str:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        cli_main.cmd_models(args)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# The key-lookup fix
# ---------------------------------------------------------------------------

def test_a_key_outside_the_environment_is_found(monkeypatch):
    """The regression: a key in the credential store used to report "no key".

    Patched at ``keys.resolve_api_key`` -- the seam the whole app resolves
    through -- rather than by setting an environment variable, because setting
    the variable is precisely the case that already worked.
    """
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(cli_main_keys(), "resolve_api_key",
                        lambda provider: "key-from-the-credential-store")
    monkeypatch.setattr(cli_main_keys(), "key_source",
                        lambda provider: "credential store")

    out = _run(_Args(provider="anthropic"))
    assert "no API key" not in out
    assert "claude-opus-5" in out


def test_no_key_anywhere_says_so_and_names_the_variable(monkeypatch):
    monkeypatch.setattr(cli_main_keys(), "resolve_api_key", lambda provider: None)

    out = _run(_Args(provider="anthropic"))
    assert "no API key" in out
    assert "ANTHROPIC_API_KEY" in out


def cli_main_keys():
    """The keys module `cmd_models` imports at call time."""
    import idt_core.keys

    return idt_core.keys


# ---------------------------------------------------------------------------
# Offline behaviour
# ---------------------------------------------------------------------------

def test_with_a_key_but_no_network_the_curated_list_still_prints(monkeypatch):
    """The fallback that makes this safe to ship: a failing fetch degrades to
    the list the command printed before any of this existed."""
    monkeypatch.setattr(cli_main_keys(), "resolve_api_key", lambda p: "some-key")
    monkeypatch.setattr(cli_main_keys(), "key_source", lambda p: "environment")
    monkeypatch.setattr(
        catalog, "_fetch",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("offline")),
    )

    out = _run(_Args(provider="anthropic"))
    for model_id in CLAUDE_MODELS:
        assert model_id in out


def test_a_provider_error_does_not_take_down_the_whole_command(monkeypatch):
    """One provider failing must not hide the others."""
    def boom(provider, args):
        raise RuntimeError("something unexpected")

    monkeypatch.setattr(cli_main, "_api_model_results", boom)
    out = _run(_Args(provider="anthropic"))
    assert "error" in out.lower()


# ---------------------------------------------------------------------------
# Output shape
# ---------------------------------------------------------------------------

def test_json_models_is_still_a_list_of_plain_ids(monkeypatch):
    monkeypatch.setattr(cli_main_keys(), "resolve_api_key", lambda p: "some-key")
    monkeypatch.setattr(cli_main_keys(), "key_source", lambda p: "environment")

    payload = json.loads(_run(_Args(provider="anthropic", json_out=True)))
    models = payload["anthropic"]["models"]
    assert isinstance(models, list)
    assert all(isinstance(m, str) for m in models)
    assert models == list(CLAUDE_MODELS)


def test_json_details_carry_the_richer_information(monkeypatch):
    monkeypatch.setattr(cli_main_keys(), "resolve_api_key", lambda p: "some-key")
    monkeypatch.setattr(cli_main_keys(), "key_source", lambda p: "environment")

    payload = json.loads(_run(_Args(provider="anthropic", json_out=True)))
    detail = payload["anthropic"]["details"][0]
    assert detail["id"] == CLAUDE_MODELS[0]
    assert detail["context_window"] == 200_000
    assert detail["source"] == "curated"


def test_no_key_json_reports_the_variable_to_set(monkeypatch):
    monkeypatch.setattr(cli_main_keys(), "resolve_api_key", lambda p: None)

    payload = json.loads(_run(_Args(provider="anthropic", json_out=True)))
    assert payload["anthropic"]["status"] == "no_key"
    assert payload["anthropic"]["env_var"] == "ANTHROPIC_API_KEY"


def test_a_new_model_is_marked_in_the_text_output(monkeypatch):
    """A model we have no metadata for must not look like one we vouch for."""
    monkeypatch.setattr(cli_main_keys(), "resolve_api_key", lambda p: "some-key")
    monkeypatch.setattr(cli_main_keys(), "key_source", lambda p: "environment")
    monkeypatch.setattr(
        catalog, "_fetch",
        lambda *a, **k: [{"id": i, "name": "", "created": n}
                         for n, i in enumerate(
                             ["claude-opus-5", "claude-sonnet-5", "claude-opus-9"])],
    )

    out = _run(_Args(provider="anthropic", refresh=True))
    assert "claude-opus-9" in out
    assert catalog.NEW_MODEL_NOTE in out


# ---------------------------------------------------------------------------
# Default model selection
# ---------------------------------------------------------------------------

def test_the_default_model_is_used_when_the_account_still_has_it():
    from idt_core.providers.claude import DEFAULT_MODEL

    assert cli_main._chat_default_model("claude") == DEFAULT_MODEL


def test_a_retired_default_falls_back_to_a_recommended_model(monkeypatch):
    """The exact failure issue #267 describes: a hardcoded default the provider
    has since withdrawn looks fine until the first request errors."""
    from idt_core.providers.claude import DEFAULT_MODEL

    survivors = [e for e in catalog.curated_models("claude") if e.id != DEFAULT_MODEL]
    monkeypatch.setattr(catalog, "cached_models", lambda *a, **k: survivors)

    chosen = cli_main._chat_default_model("claude")
    assert chosen != DEFAULT_MODEL
    assert any(e.id == chosen and e.recommended for e in survivors)


def test_default_model_selection_survives_a_broken_catalog(monkeypatch):
    """The catalog improves this choice; it must never be required for one."""
    from idt_core.providers.claude import DEFAULT_MODEL

    monkeypatch.setattr(
        catalog, "cached_models",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("catalog is unhappy")),
    )
    assert cli_main._chat_default_model("claude") == DEFAULT_MODEL
