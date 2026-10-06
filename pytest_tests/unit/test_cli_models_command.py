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

import json
import sys
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


def _run(args, capsys) -> str:
    """Run ``cmd_models`` and return what it printed.

    Uses pytest's own capture rather than ``redirect_stdout``. The two do not
    compose: ``redirect_stdout`` swaps ``sys.stdout`` and restores it on exit,
    while pytest's capture manager owns that attribute and re-asserts it at
    points this code does not control. When that happened mid-call, every print
    went to the console and the buffer came back empty -- so the test failed
    saying the command printed nothing, while the captured output directly
    below the failure showed the entire list. It reproduced only in CI, on two
    jobs out of three, which is the most expensive kind of test bug there is.

    capsys alone did not end it: a garbage-collected wx.App from an earlier
    test file was rebinding sys.stdout too. pytest_tests/conftest.py stops that.
    """
    cli_main.cmd_models(args)
    return capsys.readouterr().out


# ---------------------------------------------------------------------------
# The key-lookup fix
# ---------------------------------------------------------------------------

def test_a_key_outside_the_environment_is_found(monkeypatch, capsys):
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

    out = _run(_Args(provider="anthropic"), capsys)
    assert "no API key" not in out
    assert "claude-opus-5" in out


def test_no_key_anywhere_says_so_and_names_the_variable(monkeypatch, capsys):
    monkeypatch.setattr(cli_main_keys(), "resolve_api_key", lambda provider: None)

    out = _run(_Args(provider="anthropic"), capsys)
    assert "no API key" in out
    assert "ANTHROPIC_API_KEY" in out


def cli_main_keys():
    """The keys module `cmd_models` imports at call time."""
    import idt_core.keys

    return idt_core.keys


# ---------------------------------------------------------------------------
# Offline behaviour
# ---------------------------------------------------------------------------

def test_with_a_key_but_no_network_the_curated_list_still_prints(monkeypatch, capsys):
    """The fallback that makes this safe to ship: a failing fetch degrades to
    the list the command printed before any of this existed."""
    monkeypatch.setattr(cli_main_keys(), "resolve_api_key", lambda p: "some-key")
    monkeypatch.setattr(cli_main_keys(), "key_source", lambda p: "environment")
    monkeypatch.setattr(
        catalog, "_fetch",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("offline")),
    )

    out = _run(_Args(provider="anthropic"), capsys)
    for model_id in CLAUDE_MODELS:
        assert model_id in out


def test_a_provider_error_does_not_take_down_the_whole_command(monkeypatch, capsys):
    """One provider failing must not hide the others."""
    def boom(provider, args):
        raise RuntimeError("something unexpected")

    monkeypatch.setattr(cli_main, "_api_model_results", boom)
    out = _run(_Args(provider="anthropic"), capsys)
    assert "error" in out.lower()


# ---------------------------------------------------------------------------
# Output shape
# ---------------------------------------------------------------------------

def test_json_models_is_still_a_list_of_plain_ids(monkeypatch, capsys):
    monkeypatch.setattr(cli_main_keys(), "resolve_api_key", lambda p: "some-key")
    monkeypatch.setattr(cli_main_keys(), "key_source", lambda p: "environment")

    payload = json.loads(_run(_Args(provider="anthropic", json_out=True), capsys))
    models = payload["anthropic"]["models"]
    assert isinstance(models, list)
    assert all(isinstance(m, str) for m in models)
    assert models == list(CLAUDE_MODELS)


def test_json_details_carry_the_richer_information(monkeypatch, capsys):
    monkeypatch.setattr(cli_main_keys(), "resolve_api_key", lambda p: "some-key")
    monkeypatch.setattr(cli_main_keys(), "key_source", lambda p: "environment")

    payload = json.loads(_run(_Args(provider="anthropic", json_out=True), capsys))
    detail = payload["anthropic"]["details"][0]
    assert detail["id"] == CLAUDE_MODELS[0]
    assert detail["context_window"] == 200_000
    assert detail["source"] == "curated"


def test_no_key_json_reports_the_variable_to_set(monkeypatch, capsys):
    monkeypatch.setattr(cli_main_keys(), "resolve_api_key", lambda p: None)

    payload = json.loads(_run(_Args(provider="anthropic", json_out=True), capsys))
    assert payload["anthropic"]["status"] == "no_key"
    assert payload["anthropic"]["env_var"] == "ANTHROPIC_API_KEY"


def test_a_new_model_is_marked_in_the_text_output(monkeypatch, capsys):
    """A model we have no metadata for must not look like one we vouch for."""
    monkeypatch.setattr(cli_main_keys(), "resolve_api_key", lambda p: "some-key")
    monkeypatch.setattr(cli_main_keys(), "key_source", lambda p: "environment")
    monkeypatch.setattr(
        catalog, "_fetch",
        lambda *a, **k: [{"id": i, "name": "", "created": n}
                         for n, i in enumerate(
                             ["claude-opus-5", "claude-sonnet-5", "claude-opus-9"])],
    )

    out = _run(_Args(provider="anthropic", refresh=True), capsys)
    assert "claude-opus-9" in out
    assert catalog.NEW_MODEL_NOTE in out


# ---------------------------------------------------------------------------
# Default model selection
# ---------------------------------------------------------------------------

def test_the_default_model_is_used_when_the_account_still_has_it(capsys):
    from idt_core.providers.claude import DEFAULT_MODEL

    assert cli_main._chat_default_model("claude") == DEFAULT_MODEL


def test_a_retired_default_falls_back_to_a_recommended_model(monkeypatch, capsys):
    """The exact failure issue #267 describes: a hardcoded default the provider
    has since withdrawn looks fine until the first request errors."""
    from idt_core.providers.claude import DEFAULT_MODEL

    survivors = [e for e in catalog.curated_models("claude") if e.id != DEFAULT_MODEL]
    monkeypatch.setattr(catalog, "cached_models", lambda *a, **k: survivors)

    chosen = cli_main._chat_default_model("claude")
    assert chosen != DEFAULT_MODEL
    assert any(e.id == chosen and e.recommended for e in survivors)


def test_default_model_selection_survives_a_broken_catalog(monkeypatch, capsys):
    """The catalog improves this choice; it must never be required for one."""
    from idt_core.providers.claude import DEFAULT_MODEL

    monkeypatch.setattr(
        catalog, "cached_models",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("catalog is unhappy")),
    )
    assert cli_main._chat_default_model("claude") == DEFAULT_MODEL


# ---------------------------------------------------------------------------
# Per-provider model resolution
#
# `default_model` is global while `--provider` is per-run, so a configured
# default belonging to another provider used to be sent verbatim. With
# `--provider apple` that meant an Ollama model name reaching Apple
# Intelligence and an HTTP 400 on every image in the run.
# ---------------------------------------------------------------------------

def test_a_foreign_default_model_does_not_reach_apple(capsys):
    """The bug, stated directly: default_model=moondream, --provider apple."""
    from cli.main import _resolve_model
    from idt_core.providers.apple import DEFAULT_MODEL

    assert _resolve_model("apple", "moondream") == DEFAULT_MODEL


def test_apples_own_model_is_left_alone(capsys):
    from cli.main import _resolve_model

    assert _resolve_model("apple", "system") == "system"


def test_no_model_resolves_to_the_providers_default(capsys):
    from cli.main import _resolve_model
    from idt_core.providers.apple import DEFAULT_MODEL

    assert _resolve_model("apple", None) == DEFAULT_MODEL


def test_other_providers_are_not_second_guessed(capsys):
    """Deliberately narrow. A Claude or Ollama model name we do not recognise
    may still be real -- only a fixed single-model provider can be sure."""
    from cli.main import _resolve_model

    for provider in ("ollama", "anthropic", "openai", "claude-code"):
        assert _resolve_model(provider, "something-unfamiliar") == "something-unfamiliar"


def test_a_foreign_model_warns_for_claude_code_but_is_still_sent(capsys):
    """Claude Code gets a warning, not a substitution.

    Its three names are tier aliases, but the CLI also accepts full model ids
    and new ones as Anthropic ships them, so a name IDT does not recognise may
    still be valid. Swapping it would silently run a cheaper model than the
    user asked for. Warning once beats both that and the status quo, which was
    the CLI refusing every image with a message about model catalogs.
    """
    from cli.main import _resolve_model

    assert _resolve_model("claude-code", "moondream") == "moondream"
    err = capsys.readouterr().err
    assert "moondream" in err
    assert "default_model" in err, "the warning must name where it came from"


def test_a_known_claude_code_alias_is_silent(capsys):
    from cli.main import _resolve_model

    for alias in ("haiku", "sonnet", "opus"):
        assert _resolve_model("claude-code", alias) == alias
    assert capsys.readouterr().err == ""


def test_no_model_for_claude_code_does_not_warn(capsys):
    """Nothing configured is not a mismatch; the provider picks its default."""
    from cli.main import _resolve_model

    assert _resolve_model("claude-code", None) is None
    assert capsys.readouterr().err == ""


# ---------------------------------------------------------------------------
# Windows AI: its models are four fixed kinds of description, and it takes no
# prompt. A wrong model name can only mean the default kind; a prompt can't be
# used, so it is recorded as "none" and must not change a workspace's own.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("given,expected", [
    ("accessible", "accessible"), ("Brief", "brief"), (" DIAGRAM ", "diagram"), (None, "accessible"),
])
def test_windows_ai_takes_its_kinds_whatever_their_case(capsys, given, expected):
    from cli.main import _resolve_model

    assert _resolve_model("windows-ai", given) == expected
    assert capsys.readouterr().err == ""


def test_an_inherited_model_quietly_becomes_windows_ais_default(capsys):
    """default_model is shared by every provider, so an Ollama name there is no mistake."""
    from cli.main import _resolve_model

    assert _resolve_model("windows-ai", "moondream") == "accessible"
    assert capsys.readouterr().err == ""


def test_a_model_asked_for_that_isnt_a_kind_stops_before_the_run(capsys):
    """A typo in --model must not run a whole batch as some other kind."""
    from cli.main import _resolve_model

    with pytest.raises(SystemExit) as caught:
        _resolve_model("windows-ai", "detailled", explicit="detailled")
    assert caught.value.code == 2
    err = capsys.readouterr().err
    assert "detailled" in err and "accessible, detailed, brief, diagram" in err


def test_a_kind_inherited_by_another_provider_gives_way_to_its_default(capsys):
    """A workspace last described with Windows AI, rerun with --provider ollama."""
    from cli.main import _resolve_model

    assert _resolve_model("ollama", "accessible") is None
    assert _resolve_model("apple", "brief") == "system"
    assert _resolve_model("ollama", "brief", explicit="brief") == "brief", "asked for, so sent"


def test_windows_ai_ignores_a_prompt_and_says_so(capsys):
    from cli.main import _resolve_prompt

    args = _Args(prompt="narrative", prompt_text=None)
    assert _resolve_prompt(args, None, "windows-ai") == ("none", "")
    assert "takes no prompt" in capsys.readouterr().err


def test_windows_ai_without_a_prompt_asked_for_is_silent(capsys):
    from cli.main import _resolve_prompt

    assert _resolve_prompt(_Args(prompt=None, prompt_text=None), None, "windows-ai") == ("none", "")
    assert capsys.readouterr().err == ""


def test_only_windows_ai_skips_the_prompt():
    from cli.main import _prompt_label, _uses_prompt

    assert not _uses_prompt("windows-ai")
    assert all(_uses_prompt(p) for p in ("ollama", "claude", "openai", "apple", "claude-code", None))
    assert _prompt_label("windows-ai", "brief", "none") == "not used (Windows AI describes with its brief kind)"
    assert _prompt_label("ollama", "moondream", "narrative") == "narrative"


def _windows_ai_pc(monkeypatch, available=True, report=None, error=None):
    from idt_core.providers import windows_ai

    def check_ready(force=False):
        if error:
            raise error
        return report or {"state": "Ready"}

    monkeypatch.setattr(windows_ai, "is_available", lambda: available)
    monkeypatch.setattr(windows_ai, "check_ready", check_ready)


def test_models_lists_the_kinds_on_a_ready_pc(monkeypatch, capsys):
    _windows_ai_pc(monkeypatch)
    out = _run(_Args(provider="windows-ai"), capsys)
    for kind in ("accessible", "detailed", "brief", "diagram"):
        assert kind in out
    assert "first use" not in out


def test_models_notes_a_model_not_yet_downloaded(monkeypatch, capsys):
    _windows_ai_pc(monkeypatch, report={"state": "NotReady"})
    out = _run(_Args(provider="windows-ai"), capsys)
    assert "accessible" in out and "first use" in out


def test_models_json_for_windows_ai_keeps_the_plain_id_list(monkeypatch, capsys):
    _windows_ai_pc(monkeypatch, report={"state": "NotReady"})
    data = json.loads(_run(_Args(provider="windows-ai", json_out=True), capsys))
    assert data["windows-ai"]["models"] == ["accessible", "detailed", "brief", "diagram"]
    assert data["windows-ai"]["status"] == "ok"


def test_models_says_why_windows_ai_is_unavailable(monkeypatch, capsys):
    from idt_core.providers.windows_ai import WindowsAIError

    _windows_ai_pc(monkeypatch, available=False)
    assert "Copilot+ PC" in _run(_Args(provider="windows-ai"), capsys)
    _windows_ai_pc(monkeypatch, error=WindowsAIError("Windows' AI features are turned off", setup=True))
    assert "turned off" in _run(_Args(provider="windows-ai"), capsys)
